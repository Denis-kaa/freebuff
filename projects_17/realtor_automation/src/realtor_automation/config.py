"""Configuration loader for realtor_automation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or is invalid."""

    pass


def _default_project_root() -> Path:
    """Return project root relative to this module (projects/realtor_automation)."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load ``config.json`` and override with environment variables.

    Args:
        project_root: Optional explicit project root. Defaults to the directory
            containing this package.

    Returns:
        Merged configuration dictionary.

    Raises:
        ConfigError: If the configuration file is missing or malformed.
    """
    root = project_root or _default_project_root()
    config_path = root / "config.json"

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Failed to parse {config_path}: {exc}") from exc

    # Resolve relative paths against project root.
    for key in ("data", "knowledge", "documents", "logs"):
        if key in config.get("paths", {}):
            config["paths"][key] = str(root / config["paths"][key])

    # Apply environment overrides.
    if os.environ.get("LOG_LEVEL"):
        config.setdefault("app", {})["log_level"] = os.environ["LOG_LEVEL"]
    if os.environ.get("OLLAMA_URL"):
        config.setdefault("llm", {})["url"] = os.environ["OLLAMA_URL"]
    if os.environ.get("LLM_MODEL"):
        config.setdefault("llm", {})["model"] = os.environ["LLM_MODEL"]

    return config
