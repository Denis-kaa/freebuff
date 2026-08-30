"""
Freebuff Plugin — public API for core integration.

Exports the minimal set of symbols needed by the core (scripts_01/mcp_server.py).
Uses lazy imports so the plugin can be safely imported even if some
dependencies are missing (graceful degradation).

INTEGRATION CONTRACT:
  - Core → Plugin: import ONLY from this __init__.py. No direct submodule imports.
  - Plugin → Core: all communication through bridge.py. No direct scripts.* imports.
  - See INTEGRATION_CONTRACT.md for full details.
"""

__all__ = [
    "BridgeLayer",
    "BootstrapEngine",
    "RuntimeRegistry",
    "RuntimeCapabilityRegistry",
]


def __getattr__(name: str):
    """Lazy import — symbols are loaded only when accessed.

    This keeps import-time dependencies minimal and allows
    graceful degradation when individual components are unavailable.
    """
    if name == "BridgeLayer":
        from freebuff_plugin_03.bridge_layer import BridgeLayer
        return BridgeLayer
    if name == "BootstrapEngine":
        from freebuff_plugin_03.bootstrap.engine import BootstrapEngine
        return BootstrapEngine
    if name == "RuntimeRegistry":
        from freebuff_plugin_03.runtime import RuntimeRegistry
        return RuntimeRegistry
    if name == "RuntimeCapabilityRegistry":
        from freebuff_plugin_03.runtime import RuntimeCapabilityRegistry
        return RuntimeCapabilityRegistry
    raise AttributeError(
        f"module 'freebuff_plugin' has no attribute '{name}'. "
        f"Available: {', '.join(__all__)}"
    )
