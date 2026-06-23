"""Simple global config for trip-cli.

Config is stored in ~/.trip-cli/config.json
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".trip-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Sensible defaults
DEFAULTS: Dict[str, Any] = {
    "currency": "HKD",
    "region": "hk",
}


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load config, merging with defaults."""
    _ensure_config_dir()
    if not CONFIG_FILE.exists():
        return DEFAULTS.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        # Merge: defaults first, then user overrides
        config = {**DEFAULTS, **(user_config or {})}
        return config
    except Exception:
        # Corrupt or unreadable config — fall back to defaults
        return DEFAULTS.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save config to disk (overwrites)."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value, falling back to defaults."""
    config = load_config()
    if key in config:
        return config[key]
    return DEFAULTS.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """Set a config value and persist it."""
    config = load_config()
    config[key] = value
    save_config(config)


def unset_config_value(key: str) -> None:
    """Remove a key from user config."""
    config = load_config()
    if key in config:
        del config[key]
    save_config(config)


def list_config() -> Dict[str, Any]:
    """Return the full merged config."""
    return load_config()


def get_trip_domain() -> str:
    """Return the Trip.com regional domain based on config (e.g. hk.trip.com)."""
    region = str(get_config_value("region", "hk")).strip().lower()
    if not region or region in {"global", "www", "com"}:
        return "www.trip.com"
    # Allow user to set full domain like "hk.trip.com" or just "hk"
    if "." in region:
        return region
    return f"{region}.trip.com"
