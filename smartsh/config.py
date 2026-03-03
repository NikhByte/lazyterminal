"""Configuration loading and persistence for smartsh."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .defaults import COMMON_COMMANDS, DEFAULT_SENSITIVE_PATTERNS, DEFAULT_TYPO_MAP

CONFIG_DIR = Path.home() / ".config" / "smartsh"
CONFIG_PATH = CONFIG_DIR / "config.json"


def default_config() -> dict:
    return {
        "autocorrect_enabled": True,
        "autocorrect_threshold": 0.78,
        "command_explain_enabled": True,
        "error_explain_enabled": True,
        "confirm_dangerous": True,
        "typo_map": DEFAULT_TYPO_MAP,
        "custom_commands": COMMON_COMMANDS,
        "learning_enabled": True,
        "learning_top_n": 12,
        "learning_decay_days": 30,
        "learning_denylist_patterns": DEFAULT_SENSITIVE_PATTERNS,
    }


def _merge_with_defaults(cfg: dict) -> dict:
    merged = deepcopy(default_config())
    for key, value in cfg.items():
        merged[key] = value

    default_typos = deepcopy(default_config()["typo_map"])
    loaded_typos = cfg.get("typo_map", {})
    if isinstance(loaded_typos, dict):
        default_typos.update(loaded_typos)
    merged["typo_map"] = default_typos

    default_patterns = list(default_config()["learning_denylist_patterns"])
    loaded_patterns = cfg.get("learning_denylist_patterns", [])
    if isinstance(loaded_patterns, list):
        seen = set(default_patterns)
        for pattern in loaded_patterns:
            if pattern not in seen:
                default_patterns.append(pattern)
                seen.add(pattern)
    merged["learning_denylist_patterns"] = default_patterns

    return merged


def ensure_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        cfg = default_config()
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return cfg
    return load_config()


def load_config() -> dict:
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise json.JSONDecodeError("config must be object", "", 0)
        merged = _merge_with_defaults(loaded)
        if merged != loaded:
            CONFIG_PATH.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        return merged
    except (json.JSONDecodeError, OSError):
        cfg = default_config()
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return cfg
