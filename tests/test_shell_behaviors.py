from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

try:
    from smartsh.shell import SmartShell
except ModuleNotFoundError:
    SmartShell = None


@unittest.skipIf(SmartShell is None, "prompt_toolkit not installed")
class ShellBehaviorTests(unittest.TestCase):
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

    def test_sensitive_guard_first_attempt_blocks(self) -> None:
        shell = SmartShell()
        blocked = shell._handle_sensitive_guard("echo token=abc123")
        self.assertFalse(blocked)
        self.assertEqual(shell.pending_sensitive_confirmation, "echo token=abc123")


if __name__ == "__main__":
    unittest.main()
