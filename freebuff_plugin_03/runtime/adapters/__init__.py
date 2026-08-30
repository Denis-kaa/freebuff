"""
Runtime Abstraction Layer — встроенные адаптеры Runtime.
"""

from freebuff_plugin_03.runtime.adapters.freebuff import FreebuffAdapter
from freebuff_plugin_03.runtime.adapters.claude import ClaudeCodeAdapter

__all__ = [
    "FreebuffAdapter",
    "ClaudeCodeAdapter",
]
