"""
ClaudeCodeAdapter — адаптер для Claude Code CLI.

RuntimeName: "claude-code"
Транспорт: MCP STDIO
Установка: npm install -g @anthropic/claude-code

Спецификация: docs_10/core/RUNTIME_ABSTRACTION_SPECIFICATION.md §5.3
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from freebuff_plugin_03.runtime import (
    AdapterType,
    RuntimeCapability,
    RuntimeConfig,
)
from freebuff_plugin_03.runtime.adapter import StdioMCPAdapter


class ClaudeCodeAdapter(StdioMCPAdapter):
    """Адаптер для Claude Code CLI.

    Автоматически находит Claude Code в PATH.
    Требует: npm install -g @anthropic/claude-code

    Capabilities: coding, review, architecture, documentation, planning
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
    ):
        cfg = config or RuntimeConfig()
        command, args = self._find_claude()
        super().__init__(
            config=cfg,
            command=command,
            args=args,
            runtime_name="claude-code",
            display_name="Claude Code",
        )
        self._capabilities = [
            RuntimeCapability("coding", "Code generation and review", 0.95),
            RuntimeCapability("review", "Code review and analysis", 0.95),
            RuntimeCapability("architecture", "Architecture and design", 0.85),
            RuntimeCapability("documentation", "Documentation generation", 0.90),
            RuntimeCapability("planning", "Task planning", 0.80),
        ]

    @staticmethod
    def _find_claude() -> tuple:
        """Ищет Claude Code в системе.

        Returns:
            (command, args) кортеж для запуска Claude Code в MCP режиме.
        """
        # 1. which claude
        path = shutil.which("claude")
        if path:
            return path, ["mcp"]

        # 2. npm root -g
        npm_global = shutil.which("npm")
        if npm_global:
            import subprocess
            try:
                result = subprocess.run(
                    [npm_global, "root", "-g"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    global_dir = result.stdout.strip()
                    claude_path = Path(global_dir) / "@anthropic" / "claude-code" / "cli.js"
                    if claude_path.exists():
                        return "node", [str(claude_path), "mcp"]
            except Exception:
                pass

        # 3. Fallback
        return "claude", ["mcp"]

    @staticmethod
    def is_installed() -> bool:
        """Проверяет, установлен ли Claude Code."""
        if shutil.which("claude"):
            return True
        # Проверка через npm
        npm = shutil.which("npm")
        if npm:
            import subprocess
            try:
                result = subprocess.run(
                    [npm, "list", "-g", "@anthropic/claude-code"],
                    capture_output=True, text=True, timeout=10,
                )
                return result.returncode == 0
            except Exception:
                pass
        return False

    @property
    def adapter_type(self) -> str:
        return AdapterType.STDIO_MCP.value
