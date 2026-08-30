"""
freebuff/core_02/interfaces.py — Unified contracts for all AI agents.
Based on LEVIATHAN IAgent + FREELANCE_SYSTEM BaseAgent patterns.

Usage:
    from freebuff.core_02.interfaces import IAgent, AgentResult, TaskStatus
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Standardized task result status."""
    OK = "ok"
    WARN = "warn"
    ERROR = "error"


@dataclass
class AgentResult:
    """Uniform response format for all agents."""
    status: TaskStatus
    agent: str
    task: str
    data: Any = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == TaskStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "agent": self.agent,
            "task": self.task, "data": self.data,
            "warnings": self.warnings,
            "errors": self.errors,
            "meta": self.meta,
        }


class IAgent(ABC):
    """Interface that all agents must implement.

    Subclasses must define:
        name: str       — unique agent identifier
        version: str    — semantic version
        run(**kwargs)   — main execution method
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    async def run(self, **kwargs) -> AgentResult: ...

    def ok(self, task: str, data: Any = None, **meta) -> AgentResult:
        return AgentResult(
            status=TaskStatus.OK,
            agent=self.name,
            task=task,
            data=data,
            meta=meta,
        )

    def err(self, task: str, errors: List[str], data: Any = None, **meta) -> AgentResult:
        return AgentResult(
            status=TaskStatus.ERROR,
            agent=self.name,
            task=task,
            data=data,
            errors=errors,
            meta=meta,
        )

    def warn(self, task: str, warnings: List[str], data: Any = None, **meta) -> AgentResult:
        return AgentResult(
            status=TaskStatus.WARN,
            agent=self.name,
            task=task,
            data=data,
            warnings=warnings,
            meta=meta,
        )
