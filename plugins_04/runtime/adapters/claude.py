"""Адаптер Claude Code runtime."""

from __future__ import annotations

import shutil
import subprocess
from typing import List, Tuple

from plugins_04.runtime import RuntimeCapability, RuntimeConfig
from plugins_04.runtime.adapter import StdioMCPAdapter


class ClaudeCodeAdapter(StdioMCPAdapter):
    """Runtime-адаптер к MCP-серверу Claude Code (stdio)."""

    _CAPABILITIES = [
        RuntimeCapability(name="coding", description="Code generation", confidence=0.95),
        RuntimeCapability(name="review", description="Code review", confidence=0.95),
        RuntimeCapability(name="documentation", description="Documentation writing", confidence=0.90),
        RuntimeCapability(name="testing", description="Test generation", confidence=0.85),
    ]

    def __init__(self) -> None:
        command, args = self._find_claude()
        super().__init__(
            RuntimeConfig(command=command, args=args),
            command,
            args,
            "claude-code",
            "Claude Code",
        )

    @staticmethod
    def _find_claude() -> Tuple[str, List[str]]:
        """Поиск claude: PATH → проверка версии → default 'claude'."""
        found = shutil.which("claude")
        if found:
            return found, ["mcp"]
        # Проверка доступности бинарника напрямую
        try:
            proc = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0:
                return "claude", ["mcp"]
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "claude", ["mcp"]

    def list_capabilities(self) -> List[RuntimeCapability]:
        return list(self._CAPABILITIES)
