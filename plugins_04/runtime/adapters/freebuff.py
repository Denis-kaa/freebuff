"""Адаптер Freebuff CLI runtime."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

from plugins_04.runtime import RuntimeCapability, RuntimeConfig
from plugins_04.runtime.adapter import StdioMCPAdapter


class FreebuffAdapter(StdioMCPAdapter):
    """Runtime-адаптер к MCP-серверу Freebuff CLI (stdio)."""

    _CAPABILITIES = [
        RuntimeCapability(name="coding", description="Code generation", confidence=0.85),
        RuntimeCapability(name="planning", description="Task planning", confidence=0.80),
        RuntimeCapability(name="research", description="Web research", confidence=0.75),
    ]

    def __init__(self) -> None:
        command, args = self._find_freebuff()
        super().__init__(
            RuntimeConfig(command=command, args=args),
            command,
            args,
            "freebuff",
            "Freebuff CLI",
        )

    @staticmethod
    def _find_freebuff() -> Tuple[str, List[str]]:
        """Поиск freebuff: PATH → python -m freebuff_cli."""
        found = shutil.which("freebuff")
        if found:
            return found, ["mcp"]
        # Fallback: модуль репозитория
        workspace_cli = Path(__file__).resolve().parent.parent.parent.parent / "freebuff_cli.py"
        if workspace_cli.exists():
            return sys.executable or "python3", ["-m", "freebuff_cli", "mcp"]
        return sys.executable or "python3", ["-m", "freebuff_cli", "mcp"]

    def list_capabilities(self) -> List[RuntimeCapability]:
        return list(self._CAPABILITIES)
