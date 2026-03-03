from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from smartsh.shell import SmartShell
except ModuleNotFoundError:
    SmartShell = None


@unittest.skipIf(SmartShell is None, "prompt_toolkit not installed")
class ShellBehaviorTests(unittest.TestCase):
    def test_cd_single_match_autocorrects(self) -> None:
        shell = SmartShell()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "new").mkdir()
            current = Path.cwd()
            try:
                import os

                os.chdir(base)
                changed = shell._run_external("cd neww")
                self.assertTrue(changed)
                self.assertEqual(Path.cwd().name, "new")
            finally:
                os.chdir(current)

    def test_cd_suggestions_conflicts(self) -> None:
        shell = SmartShell()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "BotControl").mkdir()
            (base / "BotController").mkdir()
            current = Path.cwd()
            try:
                import os

                os.chdir(base)
                suggestions = shell._cd_suggestions("BotContol")
                self.assertIn("BotControl", suggestions)
                self.assertIn("BotController", suggestions)
            finally:
                os.chdir(current)

    def test_plain_english_error_for_command_not_found(self) -> None:
        shell = SmartShell()
        self.assertEqual(
            shell._plain_english_error("does-not-exist", 127),
            "Command not found. Check spelling or install it.",
        )

    def test_external_failure_prints_explain_line(self) -> None:
        shell = SmartShell()
        with patch("smartsh.shell.subprocess.run") as mock_run, patch("builtins.print") as mock_print:
            mock_run.return_value.returncode = 127
            shell._run_external("does-not-exist")
            printed = [" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list]
            self.assertTrue(any(line.startswith("explain:") for line in printed))

    def test_sensitive_guard_first_attempt_blocks(self) -> None:
        shell = SmartShell()
        blocked = shell._handle_sensitive_guard("echo token=abc123")
        self.assertFalse(blocked)
        self.assertEqual(shell.pending_sensitive_confirmation, "echo token=abc123")


if __name__ == "__main__":
    unittest.main()
