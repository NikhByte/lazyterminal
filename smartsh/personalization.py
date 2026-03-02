"""Local personalization engine for smartsh command ranking."""

from __future__ import annotations

import difflib
import json
import math
import os
import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
LEARNING_PATH = Path.home() / ".local" / "share" / "smartsh" / "learning.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def default_learning_data() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": _to_iso(_utc_now()),
        "commands": {},
    }


def _extract_base_command(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    try:
        parts = shlex.split(stripped)
    except ValueError:
        parts = stripped.split()
    return parts[0] if parts else ""


def extract_base_command(line: str) -> str:
    return _extract_base_command(line)


def is_sensitive_command(line: str, denylist_patterns: Iterable[str]) -> bool:
    lowered = line.lower()
    for pattern in denylist_patterns:
        if not pattern:
            continue
        try:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in lowered:
                return True
    return False


@dataclass
class RankingWeights:
    match: float = 0.55
    frequency: float = 0.2
    recency: float = 0.2
    context: float = 0.05


class PersonalizationStore:
    def __init__(self, data_path: Path, decay_days: float = 30.0) -> None:
        self.data_path = data_path
        self.decay_days = max(decay_days, 1.0)
        self.data = self._load_or_reset()

    def _load_or_reset(self) -> dict:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            data = default_learning_data()
            self._write(data)
            return data

        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("learning data must be object")
            if raw.get("schema_version") != SCHEMA_VERSION or not isinstance(raw.get("commands"), dict):
                raise ValueError("unsupported schema")
            raw.setdefault("updated_at", _to_iso(_utc_now()))
            return raw
        except (OSError, json.JSONDecodeError, ValueError):
            data = default_learning_data()
            self._write(data)
            return data

    def _write(self, data: dict) -> None:
        data["updated_at"] = _to_iso(_utc_now())
        self.data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def save(self) -> None:
        self._write(self.data)

    def reset(self) -> None:
        self.data = default_learning_data()
        self.save()

    def record_success(self, line: str, cwd: str, previous_base: str | None) -> None:
        cmd = line.strip()
        if not cmd:
            return

        base = _extract_base_command(cmd)
        if not base:
            return

        commands = self.data.setdefault("commands", {})
        entry = commands.setdefault(
            cmd,
            {
                "base": base,
                "count": 0,
                "last_used": None,
                "cwd_counts": {},
                "prev_counts": {},
            },
        )

        entry["base"] = base
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["last_used"] = _to_iso(_utc_now())

        cwd_counts = entry.setdefault("cwd_counts", {})
        if cwd:
            cwd_counts[cwd] = int(cwd_counts.get(cwd, 0)) + 1

        prev_counts = entry.setdefault("prev_counts", {})
        if previous_base:
            prev_counts[previous_base] = int(prev_counts.get(previous_base, 0)) + 1

        self.save()

    def stats(self) -> dict:
        commands = self.data.get("commands", {})
        total_events = sum(int(v.get("count", 0)) for v in commands.values())
        return {
            "schema_version": self.data.get("schema_version", SCHEMA_VERSION),
            "entries": len(commands),
            "total_events": total_events,
            "path": str(self.data_path),
        }

    def rank(
        self,
        query: str,
        candidates: Iterable[str],
        cwd: str,
        previous_base: str | None,
        top_n: int,
        weights: RankingWeights | None = None,
    ) -> list[str]:
        clean_query = query.strip()
        weights = weights or RankingWeights()

        commands = self.data.get("commands", {})
        max_count = max((int(v.get("count", 0)) for v in commands.values()), default=0)
        max_count = max(max_count, 1)

        scored: list[tuple[float, str]] = []
        for candidate in set(candidates):
            match_score = self._match_score(clean_query, candidate)
            if clean_query and match_score <= 0.0:
                continue

            entry = commands.get(candidate, {})
            count = int(entry.get("count", 0))
            freq_score = math.log1p(count) / math.log1p(max_count) if count > 0 else 0.0

            recency_score = 0.0
            last_used = _from_iso(entry.get("last_used")) if entry else None
            if last_used is not None:
                age_days = max((_utc_now() - last_used).total_seconds() / 86400.0, 0.0)
                recency_score = math.exp(-age_days / self.decay_days)

            context_score = 0.0
            cwd_count = int(entry.get("cwd_counts", {}).get(cwd, 0)) if entry else 0
            prev_count = int(entry.get("prev_counts", {}).get(previous_base or "", 0)) if entry else 0
            if cwd_count > 0 or prev_count > 0:
                context_score = min(1.0, 0.7 * (cwd_count / max_count) + 0.3 * (prev_count / max_count))

            total = (
                weights.match * match_score
                + weights.frequency * freq_score
                + weights.recency * recency_score
                + weights.context * context_score
            )
            scored.append((total, candidate))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [cmd for _, cmd in scored[: max(top_n, 1)]]

    @staticmethod
    def _match_score(query: str, candidate: str) -> float:
        if not query:
            return 0.3

        q = query.lower()
        c = candidate.lower()
        if c.startswith(q):
            return 1.0
        if q in c:
            return 0.75

        base = _extract_base_command(candidate).lower()
        if base.startswith(q):
            return 0.9

        ratio = difflib.SequenceMatcher(None, q, c).ratio()
        if ratio < 0.45:
            return 0.0
        return 0.5 * ratio


def discover_path_commands() -> set[str]:
    commands: set[str] = set()
    for bin_dir in os.environ.get("PATH", "").split(":"):
        if not bin_dir:
            continue
        p = Path(bin_dir)
        if not p.is_dir():
            continue
        for item in p.iterdir():
            if item.is_file() and os.access(item, os.X_OK):
                commands.add(item.name)
    return commands
