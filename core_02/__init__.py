"""
freebuff/core — Unified SDK for AI agent ecosystem.

Exports:
    IAgent, AgentResult, TaskStatus  — agent contracts
    SmartRouter, ModelCatalog        — LLM routing
"""

try:
    from freebuff.core_02.interfaces import IAgent, AgentResult, TaskStatus
    from freebuff.core_02.router import SmartRouter, ModelCatalog, ModelEntry, Provider, RouteDecision
except ImportError:
    # Локальный запуск (без установленного пакета freebuff) — core_02 как топ-модуль.
    from core_02.interfaces import IAgent, AgentResult, TaskStatus
    from core_02.router import SmartRouter, ModelCatalog, ModelEntry, Provider, RouteDecision

__all__ = [
    "IAgent", "AgentResult", "TaskStatus",
    "SmartRouter", "ModelCatalog", "ModelEntry", "Provider", "RouteDecision",
***REMOVED***
