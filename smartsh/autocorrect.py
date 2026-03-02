"""Autocorrect helpers for smartsh command inputs."""

from __future__ import annotations

import difflib
from shutil import which
from typing import Iterable


def _is_executable(cmd: str) -> bool:
    return which(cmd) is not None


def suggest_command(first_token: str, candidates: Iterable[str], threshold: float) -> str | None:
    options = [c for c in candidates if c]
    matches = difflib.get_close_matches(first_token, options, n=1, cutoff=threshold)
    return matches[0] if matches else None


def maybe_autocorrect(line: str, typo_map: dict, command_cache: list[str], threshold: float) -> tuple[str, str | None]:
    stripped = line.strip()
    if not stripped:
        return line, None

    parts = stripped.split()
    head = parts[0]

    mapped = typo_map.get(head)
    if mapped:
        corrected = " ".join([mapped, *parts[1:]]).strip()
        return corrected, f"mapped '{head}' -> '{mapped}'"

    if _is_executable(head):
        return line, None

    suggestion = suggest_command(head, command_cache, threshold)
    if suggestion and suggestion != head:
        corrected = " ".join([suggestion, *parts[1:]]).strip()
        return corrected, f"fuzzy '{head}' -> '{suggestion}'"

    return line, None
