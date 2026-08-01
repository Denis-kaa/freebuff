"""
FreebuffAdapter — адаптер для freebuff (Codebuff) CLI.

RuntimeName: "freebuff"
Транспорт: MCP STDIO
Установка: npm install -g @freebuff/cli  или  pip install freebuff-cli

Спецификация: docs_10/core/RUNTIME_ABSTRACTION_SPECIFICATION.md §5.2
"""

from __future__ import annotations

import os
import shutil
import sys
***REMOVED***
from typing import List, Optional

from freebuff_plugin_03.runtime import (
    AdapterType,
    RuntimeCapability,
    RuntimeConfig,
)
from freebuff_plugin_03.runtime.adapter import StdioMCPAdapter


class FreebuffAdapter(StdioMCPAdapter):
    """Адаптер для freebuff (Codebuff) CLI.

    Автоматически находит freebuff в:
    1. PATH (which freebuff/codebuff)
    2. ~/.local/bin/freebuff (wrapper)
    3. Установка через pip (python -m freebuff_cli)

    Capabilities: coding, planning, architecture, testing, research
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig***REMOVED*** = None,
    ):
        cfg = config or RuntimeConfig()
        command, args = self._find_freebuff()
        super().__init__(
            config=cfg,
            command=command,
            args=args,
            runtime_name="freebuff",
            display_name="Freebuff CLI (Codebuff)",
        )
        self._capabilities = [
            RuntimeCapability("coding", "Code generation and refactoring", 0.85),
            RuntimeCapability("planning", "Task planning and architecture", 0.85),
            RuntimeCapability("architecture", "Architecture and design", 0.80),
            RuntimeCapability("testing", "Test generation and execution", 0.80),
            RuntimeCapability("research", "Codebase research", 0.70),
        ***REMOVED***

    @staticmethod
    def _find_freebuff() -> tuple:
        """Ищет freebuff в системе.

        Returns:
            (command, args) кортеж для запуска freebuff в MCP режиме.
        """
        # 1. which freebuff
        for name in ["freebuff", "codebuff"***REMOVED***:
            path = shutil.which(name)
            if path:
                return path, ["mcp"***REMOVED***

        # 2. ~/.local/bin/freebuff (wrapper)
        local_bin = Path.home() / ".local" / "bin" / "freebuff"
        if local_bin.exists():
            return str(local_bin), ["mcp"***REMOVED***

        # 3. Текущий Python как freebuff_cli
        for maybe_dir in [
            Path.cwd(),
            Path.cwd().parent,
        ***REMOVED***:
            cli = maybe_dir / "freebuff_cli.py"
            if cli.exists():
                return sys.executable, ["-m", "freebuff_cli"***REMOVED***

        # 4. Fallback: python -m freebuff_cli
        return sys.executable, ["-m", "freebuff_cli"***REMOVED***

    @staticmethod
    def is_installed() -> bool:
        """Проверяет, установлен ли freebuff."""
        for name in ["freebuff", "codebuff"***REMOVED***:
            if shutil.which(name):
                return True
        cli_path = Path.home() / ".local" / "bin" / "freebuff"
        if cli_path.exists():
            return True
        # Проверка через pip
        try:
            import freebuff_cli  # noqa
            return True
        except ImportError:
            pass
        return False

    @property
    def adapter_type(self) -> str:
        return AdapterType.STDIO_MCP.value
