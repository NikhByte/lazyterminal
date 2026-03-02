#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "${ROOT}/smartsh/"*.py
PYTHONPATH="${ROOT}" python3 -m unittest discover -s "${ROOT}/tests" -p "test_*.py" -q
PYTHONPATH="${ROOT}" python3 - <<'PY'
from smartsh.autocorrect import maybe_autocorrect
from smartsh.defaults import DEFAULT_TYPO_MAP
from smartsh.personalization import PersonalizationStore
from pathlib import Path
import tempfile

cmds = ["git", "ls", "python", "docker", "npm"]
corrected, reason = maybe_autocorrect("gti status", DEFAULT_TYPO_MAP, cmds, 0.78)
assert corrected == "git status", (corrected, reason)

corrected_cd, reason_cd = maybe_autocorrect("cdd BotControl", DEFAULT_TYPO_MAP, cmds, 0.78)
assert corrected_cd == "cd BotControl", (corrected_cd, reason_cd)

with tempfile.TemporaryDirectory() as tmp:
	store = PersonalizationStore(Path(tmp) / "learning.json", decay_days=30)
	for _ in range(3):
		store.record_success("git status", "/tmp/repo", None)
	store.record_success("git stash", "/tmp/repo", None)

	ranked = store.rank(
		query="git",
		candidates=["git status", "git stash", "git pull"],
		cwd="/tmp/repo",
		previous_base=None,
		top_n=3,
	)
	assert ranked[0] == "git status", ranked

print("smoke test passed")
PY
