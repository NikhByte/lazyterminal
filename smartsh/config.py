"""Configuration loading and persistence for smartsh."""

from __future__ import annotations

import json
from pathlib import Path

from .defaults import COMMON_COMMANDS, DEFAULT_TYPO_MAP

CONFIG_DIR = Path.home() / ".config" / "smartsh"
CONFIG_PATH = CONFIG_DIR / "config.json"


def default_config() -> dict:
    return {
        "autocorrect_enabled": True,
        "autocorrect_threshold": 0.78,
        "confirm_dangerous": True,
        "typo_map": DEFAULT_TYPO_MAP,
        "custom_commands": COMMON_COMMANDS,
    }


def ensure_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        cfg = default_config()
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return cfg
    return load_config()


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        cfg = default_config()
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return cfg
