"""
services — unified namespace for core Freebuff services.

This package re-exports modules from ``scripts_01/`` during the ongoing
restructure.  Imports are lazy so that ``import services`` stays light
and does not pull in the entire dependency graph.
"""

from __future__ import annotations

import sys
from typing import Any

# Map of public names -> (module_path, attribute_name)
_IMPORT_MAP: dict[str, tuple[str, str]] = {
    "AgentContextBridge": ("scripts.agent_context_bridge", "AgentContextBridge"),
    "get_context_bridge": ("scripts.agent_context_bridge", "get_context_bridge"),
    "auto_conspect": ("scripts.auto_conspect", "auto_conspect"),
    "ContextBuilder": ("scripts.context_builder", "ContextBuilder"),
    "CheckpointType": ("scripts.context_manager", "CheckpointType"),
    "ContextManager": ("scripts.context_manager", "ContextManager"),
    "SessionStatus": ("scripts.context_manager", "SessionStatus"),
    "EventBus": ("scripts.event_bus", "EventBus"),
    "get_default_event_bus": ("scripts.event_bus", "get_default_event_bus"),
    "GraphIndex": ("scripts.graph_index", "GraphIndex"),
    "KnowledgeEngine": ("scripts.knowledge_engine", "KnowledgeEngine"),
    "MemoryEngine": ("scripts.memory_engine", "MemoryEngine"),
    "ModelGateway": ("scripts.model_gateway", "ModelGateway"),
    "Orchestrator": ("scripts.orchestrator", "Orchestrator"),
    "BasePlugin": ("scripts.plugin_api", "BasePlugin"),
    "PluginLoader": ("scripts.plugin_api", "PluginLoader"),
    "PluginManifest": ("scripts.plugin_api", "PluginManifest"),
    "PluginMeta": ("scripts.plugin_api", "PluginMeta"),
    "PluginRegistry": ("scripts.plugin_api", "PluginRegistry"),
    "PluginResult": ("scripts.plugin_api", "PluginResult"),
    "PluginState": ("scripts.plugin_api", "PluginState"),
    "seed_knowledge": ("scripts.seed_knowledge", "seed"),
    "health_check": ("services.system.monitor", "health_check"),
    "ToolRegistry": ("scripts.tool_runtime", "ToolRegistry"),
}

__all__ = list(_IMPORT_MAP.keys())


def __getattr__(name: str) -> Any:
    if name not in _IMPORT_MAP:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = _IMPORT_MAP[name]
    module = __import__(module_path, fromlist=[attr_name])
    attr = getattr(module, attr_name)
    # Cache the attribute on the module so repeated lookups are cheap.
    setattr(sys.modules[__name__], name, attr)
    return attr


def __dir__() -> list[str]:
    return list(__all__)
