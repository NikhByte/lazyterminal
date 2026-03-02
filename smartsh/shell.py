"""Interactive smart shell with completion menus and autocorrect."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import confirm

from .autocorrect import maybe_autocorrect
from .config import CONFIG_PATH, ensure_config, load_config
from .defaults import BUILTINS, DANGEROUS_PREFIXES

HISTORY_PATH = Path.home() / ".local" / "share" / "smartsh" / "history"


class SmartShell:
    def __init__(self) -> None:
        self.cfg = ensure_config()
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.command_cache = self._build_command_cache()
        self.session = PromptSession(
            history=FileHistory(str(HISTORY_PATH)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self._build_completer(),
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
        path_bins = os.environ.get("PATH", "").split(":")
        for bin_dir in path_bins:
            p = Path(bin_dir)
            if p.is_dir():
                for item in p.iterdir():
                    if os.access(item, os.X_OK) and item.is_file():
                        commands.add(item.name)
        return sorted(commands)

    def _build_completer(self) -> NestedCompleter:
        nested = {cmd: None for cmd in self.command_cache}
        nested["smartsh"] = {"config": None, "reload": None}
        nested["help"] = None
        return NestedCompleter.from_nested_dict(nested)

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
            self.command_cache = self._build_command_cache()
            self.session.completer = self._build_completer()
            print("Reloaded config and command cache.")
            return True
        return False

    def _run_external(self, line: str) -> None:
        parts = shlex.split(line)
        if not parts:
            return

        if parts[0] == "cd":
            target = parts[1] if len(parts) > 1 else str(Path.home())
            try:
                os.chdir(os.path.expanduser(target))
            except OSError as exc:
                print(f"cd: {exc}")
            return

        shell = os.environ.get("SHELL", "/bin/bash")
        subprocess.run([shell, "-lc", line], check=False)

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

            if self._run_builtin(line):
                continue

            self._run_external(line)


def main() -> int:
    shell = SmartShell()
    return shell.run()


if __name__ == "__main__":
    raise SystemExit(main())
