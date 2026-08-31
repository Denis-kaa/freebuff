"""
cli — command-line interface entry point for Freebuff.

This package provides the ``freebuff`` CLI.  The canonical entry point
remains ``freebuff_cli.py`` in the project root for backwards compatibility;
this module lazily re-exports the same public API so that both import
paths work during the restructure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so that ``freebuff_cli`` can be
# imported regardless of how this package is invoked.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Public names exposed by the cli package.
_CLI_NAMES = [
    "cmd_buffy",
    "cmd_checkpoint",
    "cmd_conspect",
    "cmd_list",
    "cmd_qwen_resume",
    "cmd_resume",
    "cmd_seed",
    "cmd_start",
    "cmd_status",
    "cmd_task_archive",
    "cmd_task_start",
    "main",
]

__all__ = list(_CLI_NAMES)


def __getattr__(name: str) -> Any:
    if name not in _CLI_NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import freebuff_cli  # noqa: F401
    attr = getattr(freebuff_cli, name)
    # Cache on the module for fast subsequent lookups.
    setattr(sys.modules[__name__], name, attr)
    return attr


def __dir__() -> list[str]:
    return list(__all__)


def run_cli() -> None:
    """Execute the root ``freebuff_cli.py`` as if it were run directly."""
    import runpy
    runpy.run_path(str(PROJECT_ROOT / "freebuff_cli.py"), run_name="__main__")
