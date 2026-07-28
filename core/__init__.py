"""
freebuff/core — Unified SDK for AI agent ecosystem.

Exports:
    IAgent, AgentResult, TaskStatus  — agent contracts
    SmartRouter, ModelCatalog        — LLM routing
"""

from freebuff.core.interfaces import IAgent, AgentResult, TaskStatus
from freebuff.core.router import SmartRouter, ModelCatalog, ModelEntry, Provider, RouteDecision

__all__ = [
    "IAgent", "AgentResult", "TaskStatus",
    "SmartRouter", "ModelCatalog", "ModelEntry", "Provider", "RouteDecision",
***REMOVED***
