"""Configuration loader for realtor_automation."""

from __future__ import annotations

import json
import os
***REMOVED***
from typing import Any


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or is invalid."""

    pass


def _default_project_root() -> Path:
    """Return project root relative to this module (projects/realtor_automation)."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(project_root: Path | None = None) -> dict[str, Any***REMOVED***:
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
        raise ConfigError(f"Configuration file not found: {config_path***REMOVED***")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config: dict[str, Any***REMOVED*** = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Failed to parse {config_path***REMOVED***: {exc***REMOVED***") from exc

    # Resolve relative paths against project root.
    for key in ("data", "knowledge", "documents", "logs"):
        if key in config.get("paths", {***REMOVED***):
            config["paths"***REMOVED***[key***REMOVED*** = str(root / config["paths"***REMOVED***[key***REMOVED***)

    # Apply environment overrides.
    if os.environ.get("LOG_LEVEL"):
        config.setdefault("app", {***REMOVED***)["log_level"***REMOVED*** = os.environ["LOG_LEVEL"***REMOVED***
    if os.environ.get("OLLAMA_URL"):
        config.setdefault("llm", {***REMOVED***)["url"***REMOVED*** = os.environ["OLLAMA_URL"***REMOVED***
    if os.environ.get("LLM_MODEL"):
        config.setdefault("llm", {***REMOVED***)["model"***REMOVED*** = os.environ["LLM_MODEL"***REMOVED***

    return config
