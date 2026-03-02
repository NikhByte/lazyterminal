#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "${ROOT}/smartsh/"*.py
PYTHONPATH="${ROOT}" python3 - <<'PY'
from smartsh.autocorrect import maybe_autocorrect
from smartsh.defaults import DEFAULT_TYPO_MAP

cmds = ["git", "ls", "python", "docker", "npm"]
corrected, reason = maybe_autocorrect("gti status", DEFAULT_TYPO_MAP, cmds, 0.78)
assert corrected == "git status", (corrected, reason)
print("smoke test passed")
PY
