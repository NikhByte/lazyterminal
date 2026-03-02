"""Interactive smart shell with completion menus and autocorrect."""

from __future__ import annotations

import os
import shlex
import subprocess
import difflib
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import confirm

from .autocorrect import maybe_autocorrect
from .config import CONFIG_PATH, ensure_config, load_config
from .defaults import BUILTINS, DANGEROUS_PREFIXES
from .personalization import (
    LEARNING_PATH,
    PersonalizationStore,
    discover_path_commands,
    extract_base_command,
    is_sensitive_command,
)

HISTORY_PATH = Path.home() / ".local" / "share" / "smartsh" / "history"


class SmartCompleter(Completer):
    def __init__(self, shell: "SmartShell") -> None:
        self.shell = shell

    def get_completions(self, document, complete_event):
        query = document.text_before_cursor.strip()
        suggestions = self.shell.rank_candidates(query)
        replace_len = len(query)
        for suggestion in suggestions:
            yield Completion(suggestion, start_position=-replace_len)


class SmartShell:
    def __init__(self) -> None:
        self.cfg = ensure_config()
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.learning_store = PersonalizationStore(
            LEARNING_PATH,
            decay_days=float(self.cfg.get("learning_decay_days", 30)),
        )
        self.last_successful_base: str | None = None
        self.pending_sensitive_confirmation: str | None = None
        self.command_cache = self._build_command_cache()
        self.session = PromptSession(
            history=FileHistory(str(HISTORY_PATH)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=SmartCompleter(self),
            complete_while_typing=True,
            reserve_space_for_menu=10,
            key_bindings=self._key_bindings(),
        )

    def _key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("c-space")
        def _(event) -> None:
            event.app.current_buffer.start_completion(select_first=False)

        return kb

    def _build_command_cache(self) -> list[str]:
        commands = set(self.cfg.get("custom_commands", []))
        commands.update(discover_path_commands())
        commands.update(BUILTINS.keys())
        return sorted(commands)

    def rank_candidates(self, query: str) -> list[str]:
        if not self.cfg.get("learning_enabled", True):
            return [cmd for cmd in self.command_cache if not query or query in cmd][: int(self.cfg.get("learning_top_n", 12))]

        return self.learning_store.rank(
            query=query,
            candidates=self.command_cache,
            cwd=str(Path.cwd()),
            previous_base=self.last_successful_base,
            top_n=int(self.cfg.get("learning_top_n", 12)),
        )

    def _prompt(self) -> HTML:
        cwd = Path.cwd().name
        return HTML(f"<ansicyan>smartsh</ansicyan> <ansigreen>{cwd}</ansigreen> > ")

    def _is_dangerous(self, line: str) -> bool:
        lowered = line.strip().lower()
        return any(lowered.startswith(prefix) for prefix in DANGEROUS_PREFIXES)

    def _run_builtin(self, line: str) -> bool:
        if line == "help":
            print("smartsh built-ins:")
            for cmd, desc in BUILTINS.items():
                print(f"  {cmd:14} {desc}")
            return True
        if line == "smartsh config":
            print(str(CONFIG_PATH))
            return True
        if line == "smartsh reload":
            self.cfg = load_config()
            self.learning_store.decay_days = float(self.cfg.get("learning_decay_days", 30))
            self.command_cache = self._build_command_cache()
            self.session.completer = SmartCompleter(self)
            print("Reloaded config and command cache.")
            return True
        if line == "smartsh learning status":
            stats = self.learning_store.stats()
            print("smartsh learning status:")
            print(f"  enabled:      {self.cfg.get('learning_enabled', True)}")
            print(f"  top_n:        {self.cfg.get('learning_top_n', 12)}")
            print(f"  decay_days:   {self.cfg.get('learning_decay_days', 30)}")
            print(f"  schema:       {stats['schema_version']}")
            print(f"  entries:      {stats['entries']}")
            print(f"  total_events: {stats['total_events']}")
            print(f"  data_file:    {stats['path']}")
            return True
        if line == "smartsh learning reset":
            self.learning_store.reset()
            print("Reset learned command history.")
            return True
        return False

    def _should_learn(self, line: str) -> bool:
        if not self.cfg.get("learning_enabled", True):
            return False
        denylist_patterns = self.cfg.get("learning_denylist_patterns", [])
        if not isinstance(denylist_patterns, list):
            denylist_patterns = []
        return not is_sensitive_command(line, denylist_patterns)

    def _is_sensitive(self, line: str) -> bool:
        denylist_patterns = self.cfg.get("learning_denylist_patterns", [])
        if not isinstance(denylist_patterns, list):
            denylist_patterns = []
        return is_sensitive_command(line, denylist_patterns)

    def _handle_sensitive_guard(self, line: str) -> bool:
        if not self._is_sensitive(line):
            self.pending_sensitive_confirmation = None
            return True

        if self.pending_sensitive_confirmation == line:
            ok = confirm("Sensitive-looking command detected. Continue?", default=False)
            self.pending_sensitive_confirmation = None
            if ok:
                return True
            print("Command canceled.")
            return False

        print("Blocked sensitive command. Run the same command again to confirm.")
        self.pending_sensitive_confirmation = line
        return False

    def _record_learning(self, line: str) -> None:
        if not self._should_learn(line):
            return
        self.learning_store.record_success(
            line=line,
            cwd=str(Path.cwd()),
            previous_base=self.last_successful_base,
        )
        self.last_successful_base = extract_base_command(line)

    def _cd_suggestions(self, target: str) -> list[str]:
        expanded = os.path.expanduser(target)
        target_path = Path(expanded)

        if target_path.is_absolute():
            parent = target_path.parent
            needle = target_path.name
        else:
            relative = Path(expanded)
            parent = (Path.cwd() / relative).parent
            needle = relative.name

        if not parent.is_dir() or not needle:
            return []

        candidates = [entry.name for entry in parent.iterdir() if entry.is_dir()]
        return difflib.get_close_matches(needle, candidates, n=5, cutoff=0.5)

    def _run_external(self, line: str) -> bool:
        parts = shlex.split(line)
        if not parts:
            return False

        if parts[0] == "cd":
            target = parts[1] if len(parts) > 1 else str(Path.home())
            try:
                os.chdir(os.path.expanduser(target))
                self._record_learning(line)
                return True
            except OSError as exc:
                print(f"cd: {exc}")
                suggestions = self._cd_suggestions(target)
                if suggestions:
                    expanded = os.path.expanduser(target)
                    rel = Path(expanded)
                    parent = Path(expanded).parent if Path(expanded).is_absolute() else (Path.cwd() / rel).parent
                    if len(suggestions) == 1:
                        suggested_path = parent / suggestions[0]
                        if confirm(f"Did you mean '{suggested_path}'?", default=True):
                            try:
                                os.chdir(suggested_path)
                                corrected = f"cd {suggested_path}"
                                self._record_learning(corrected)
                                print(f"Changed directory to: {suggested_path}")
                                return True
                            except OSError as inner_exc:
                                print(f"cd: {inner_exc}")
                    else:
                        print("Possible directory matches:")
                        for idx, item in enumerate(suggestions, start=1):
                            print(f"  {idx}. {item}")
                return False

        shell = os.environ.get("SHELL", "/bin/bash")
        result = subprocess.run([shell, "-lc", line], check=False)
        if result.returncode == 0:
            self._record_learning(line)
            return True
        return False

    def run(self) -> int:
        print("smartsh: Ctrl-Space opens command menu, type 'help' for built-ins.")
        while True:
            try:
                line = self.session.prompt(self._prompt()).strip()
            except KeyboardInterrupt:
                print("Use 'exit' to quit.")
                continue
            except EOFError:
                print()
                return 0

            if not line:
                continue
            if line in {"exit", "quit"}:
                return 0

            if self.cfg.get("autocorrect_enabled", True):
                corrected, reason = maybe_autocorrect(
                    line,
                    self.cfg.get("typo_map", {}),
                    self.command_cache,
                    float(self.cfg.get("autocorrect_threshold", 0.78)),
                )
                if corrected != line:
                    print(f"autocorrect [{reason}]: {line} -> {corrected}")
                    line = corrected

            if self.cfg.get("confirm_dangerous", True) and self._is_dangerous(line):
                ok = confirm("Potentially dangerous command. Continue?", default=False)
                if not ok:
                    print("Command canceled.")
                    continue

            if not self._handle_sensitive_guard(line):
                continue

            if self._run_builtin(line):
                continue

            self._run_external(line)


def main() -> int:
    shell = SmartShell()
    return shell.run()


if __name__ == "__main__":
    raise SystemExit(main())
