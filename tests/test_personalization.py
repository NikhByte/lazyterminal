from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from smartsh.personalization import PersonalizationStore, is_sensitive_command


class PersonalizationTests(unittest.TestCase):
    def _store(self, decay_days: float = 30.0) -> tuple[PersonalizationStore, Path]:
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "learning.json"
        store = PersonalizationStore(path, decay_days=decay_days)
        self.addCleanup(tmp.cleanup)
        return store, path

    def test_persistence_and_corrupt_recovery(self) -> None:
        store, path = self._store()
        store.record_success("git status", "/repo", None)

        again = PersonalizationStore(path)
        stats = again.stats()
        self.assertEqual(stats["entries"], 1)
        self.assertEqual(stats["total_events"], 1)

        path.write_text("{not-valid-json", encoding="utf-8")
        reset = PersonalizationStore(path)
        reset_stats = reset.stats()
        self.assertEqual(reset_stats["entries"], 0)
        self.assertEqual(reset_stats["total_events"], 0)

    def test_schema_migration_reset(self) -> None:
        store, path = self._store()
        data = {
            "schema_version": 999,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "commands": {"git status": {"count": 10}},
        }
        path.write_text(json.dumps(data), encoding="utf-8")

        reset = PersonalizationStore(path)
        stats = reset.stats()
        self.assertEqual(stats["entries"], 0)
        self.assertEqual(stats["schema_version"], 1)

    def test_rank_prefers_frequent_recent(self) -> None:
        store, _ = self._store(decay_days=7)
        for _ in range(5):
            store.record_success("git status", "/repo", None)
        store.record_success("git stash", "/repo", None)

        ranked = store.rank(
            query="git",
            candidates=["git status", "git stash", "git pull"],
            cwd="/repo",
            previous_base=None,
            top_n=3,
        )
        self.assertEqual(ranked[0], "git status")

    def test_rank_applies_decay(self) -> None:
        store, _ = self._store(decay_days=1)
        store.record_success("docker ps", "/repo", None)
        store.record_success("docker images", "/repo", None)

        stale = datetime.now(timezone.utc) - timedelta(days=20)
        store.data["commands"]["docker ps"]["last_used"] = stale.isoformat()
        store.save()

        ranked = store.rank(
            query="docker",
            candidates=["docker ps", "docker images"],
            cwd="/repo",
            previous_base=None,
            top_n=2,
        )
        self.assertEqual(ranked[0], "docker images")

    def test_sensitive_filters(self) -> None:
        patterns = [r"password", r"token", r"private\\s+key"]
        self.assertTrue(is_sensitive_command("curl https://x --header 'Authorization: token abc'", patterns))
        self.assertTrue(is_sensitive_command("echo password=secret", patterns))
        self.assertFalse(is_sensitive_command("git status", patterns))


if __name__ == "__main__":
    unittest.main()
