"""Конкретные адаптеры известных runtime."""

from .freebuff import FreebuffAdapter
from .claude import ClaudeCodeAdapter

__all__ = ["FreebuffAdapter", "ClaudeCodeAdapter"]
