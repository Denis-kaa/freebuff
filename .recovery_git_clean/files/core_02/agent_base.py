"""core_02/agent_base.py — Единая сущность «Агент» (ADR-019).

ADR-019 (docs_10/engineering-memory/decisions/ADR_019_Agent_Base_Class.md):
закрывает P1-пробел baseline §3 («AGENT — DOCUMENTED ONLY») — вводит
официальный контракт Agent с lifecycle, связывающий:

    «кто я (role_ids) → какой model-capability мне нужен →
     какой runtime/tool у меня есть → какой у меня lifecycle»

Agent — композиция ролей, не замена им. НЕ вызывает ForgePipeline напрямую —
только ForgeFacade (§7.3 grep-инвариант). НЕ является runtime-платформой
(RFC §12: Forge — метасистема проектирования, не исполнения).

Дизайн:
- Agent — ABC: ``execute()`` абстрактный, ``route_model()`` и ``run_forge()`` —
  наследуемые сервисы (ленивые, fail-safe).
- Lifecycle: forward-only DAG (CREATED → ACTIVE → PAUSED → DONE/FAILED),
  с retry из FAILED → ACTIVE. Идемпотентный (тот же state = no-op).
- Capabilities: закрытое подмножество KNOWN_CAPABILITIES (ANTI-6b defense).
- Fail-safe: все сервисные методы ловят исключения и возвращают dict/строку,
  никогда не крашат вызывающий код (ADR-016 паттерн).

Совместимость:
- ``IAgent`` (core_02/interfaces.py) — LEVIATHAN-паттерн, остаётся.
- ``AgentNode``/``AgentMesh`` (distributed_agents.py) — сетевые сущности, остаются.
- ``BaseRoleExecutor`` (role_executor.py) — исполнение pipeline-роли, остаётся.
- ``AgentContextBridge`` (agent_context_bridge.py) — мост, остаётся.
- ``Agent`` — официальный интерфейс, мосты со временем адаптируются (additive).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import uuid4

if TYPE_CHECKING:
    from core_02.workspace import Project

__all__ = [
    "Agent",
    "AgentLifecycle",
    "AgentResult",
    "ALLOWED_TRANSITIONS",
    "KNOWN_CAPABILITIES",
***REMOVED***


# ═══════════════════════════════════════════════════════════════════════
# Vocabulary (mirrors core_02/blueprint_v3.py KNOWN_CAPABILITIES)
# ═══════════════════════════════════════════════════════════════════════

KNOWN_CAPABILITIES: frozenset[str***REMOVED*** = frozenset({
    "local", "fast",
    "code", "summarize", "router", "classify",
    "reasoning", "plan", "refactor", "explain",
    "deep", "architecture", "review",
    "vision", "tools", "long_context", "multimodal",
***REMOVED***)


# ═══════════════════════════════════════════════════════════════════════
# Lifecycle
# ═══════════════════════════════════════════════════════════════════════

class AgentLifecycle(str, Enum):
    """Forward-only lifecycle: CREATED → ACTIVE → PAUSED → DONE/FAILED."""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


# Valid transitions (forward-only DAG per ADR-019).
# FAILED → ACTIVE = retry (единственный обратный переход).
ALLOWED_TRANSITIONS: Dict[AgentLifecycle, frozenset[AgentLifecycle***REMOVED******REMOVED*** = {
    AgentLifecycle.CREATED: frozenset({AgentLifecycle.ACTIVE, AgentLifecycle.FAILED***REMOVED***),
    AgentLifecycle.ACTIVE: frozenset({AgentLifecycle.PAUSED, AgentLifecycle.DONE, AgentLifecycle.FAILED***REMOVED***),
    AgentLifecycle.PAUSED: frozenset({AgentLifecycle.ACTIVE, AgentLifecycle.FAILED***REMOVED***),
    AgentLifecycle.DONE: frozenset(),    # terminal
    AgentLifecycle.FAILED: frozenset({AgentLifecycle.ACTIVE***REMOVED***),  # retry
***REMOVED***


# ═══════════════════════════════════════════════════════════════════════
# AgentResult
# ═══════════════════════════════════════════════════════════════════════

class AgentResult:
    """Результат выполнения агента (ADR-019: dict-результат).

    Совместим с ``core_02/interfaces.py::AgentResult`` (статусы: ok/warn/error).
    """

    def __init__(
        self,
        status: str,
        agent_id: str,
        task: str,
        data: Any = None,
        warnings: Optional[List[str***REMOVED******REMOVED*** = None,
        errors: Optional[List[str***REMOVED******REMOVED*** = None,
        meta: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
        model_used: Optional[str***REMOVED*** = None,
        forge_result: Optional[Dict[str, Any***REMOVED******REMOVED*** = None,
    ) -> None:
        self.status = status
        self.agent_id = agent_id
        self.task = task
        self.data = data
        self.warnings = warnings or [***REMOVED***
        self.errors = errors or [***REMOVED***
        self.meta = meta or {***REMOVED***
        self.model_used = model_used
        self.forge_result = forge_result

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        d: Dict[str, Any***REMOVED*** = {
            "status": self.status,
            "agent_id": self.agent_id,
            "task": self.task,
            "data": self.data,
            "warnings": self.warnings,
            "errors": self.errors,
            "meta": self.meta,
        ***REMOVED***
        if self.model_used is not None:
            d["model_used"***REMOVED*** = self.model_used
        if self.forge_result is not None:
            d["forge_result"***REMOVED*** = self.forge_result
        return d


# ═══════════════════════════════════════════════════════════════════════
# Agent base class
# ═══════════════════════════════════════════════════════════════════════

class Agent(ABC):
    """Единая сущность «Агент» (ADR-019: design-only контракт).

    Связывает: «кто я (role_ids) → какой model-capability мне нужен →
    какой runtime/tool у меня есть → какой у меня lifecycle».

    Agent — **композиция ролей**, не замена им. Pipeline-роли остаются
    корпусом данных в blueprint_v3; collab-роли — в roles.py. Agent-слой
    поверх обоих — правильная граница (ADR-019 alternatives §б).

    **Правила:**
    1. Agent НЕ вызывает ForgePipeline напрямую — только ForgeFacade (§7.3).
    2. Agent использует capability-роутинг (не выбирает модель вручную).
    3. Capabilities — закрытое подмножество KNOWN_CAPABILITIES (ANTI-6b).
    4. Fail-safe: сервисные методы никогда не крашат вызывающий код.
    5. Lifecycle — forward-only DAG, идемпотентный (тот же state = no-op).

    **Подклассы** ДОЛЖНЫ реализовать ``execute()``.

    Удобные методы для подклассов (фабрики результата):
    - ``_ok(task, data, **meta)`` → AgentResult(status="ok", ...)
    - ``_err(task, errors, **meta)`` → AgentResult(status="error", ...)
    """

    def __init__(
        self,
        *,
        agent_id: Optional[str***REMOVED*** = None,
        role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
        capabilities: Optional[frozenset[str***REMOVED******REMOVED*** = None,
        model_capability: Optional[str***REMOVED*** = None,
        runtime: str = "local",
    ) -> None:
        # ── Identity ───────────────────────────────────────────────────
        self.agent_id = agent_id or uuid4().hex[:12***REMOVED***
        self.role_ids = tuple(role_ids or ())
        self.runtime = runtime  # "local" | "distributed"

        # ── Capabilities (closed vocabulary per ANTI-6b) ───────────────
        raw_caps = capabilities or frozenset()
        unknown = raw_caps - KNOWN_CAPABILITIES
        if unknown:
            raise ValueError(
                f"Agent {self.agent_id***REMOVED***: capabilities содержат токены вне "
                f"KNOWN_CAPABILITIES: {sorted(unknown)***REMOVED***. "
                f"Допустимые: {sorted(KNOWN_CAPABILITIES)***REMOVED***. "
                f"См. LESSONS.md ANTI-6b / ADR-019 §Decision пункт 2."
            )
        self.capabilities: frozenset[str***REMOVED*** = raw_caps

        # ── Model routing hint ─────────────────────────────────────────
        self.model_capability: Optional[str***REMOVED*** = model_capability

        # ── Lifecycle ──────────────────────────────────────────────────
        self._lifecycle: AgentLifecycle = AgentLifecycle.CREATED
        self._lifecycle_history: List[Tuple[AgentLifecycle, str***REMOVED******REMOVED*** = [***REMOVED***

    # ── Lifecycle ──────────────────────────────────────────────────────

    @property
    def lifecycle(self) -> AgentLifecycle:
        return self._lifecycle

    def transition(self, target: AgentLifecycle, reason: str = "") -> None:
        """Forward-only state transition.

        Идемпотентный: если ``target == текущее состояние`` — no-op.
        Иначе проверяет ALLOWED_TRANSITIONS и либо переходит, либо
        поднимает ValueError с перечнем разрешённых переходов.
        """
        if target == self._lifecycle:
            return  # idempotent no-op
        allowed = ALLOWED_TRANSITIONS.get(self._lifecycle, frozenset())
        if target not in allowed:
            raise ValueError(
                f"Agent {self.agent_id***REMOVED***: недопустимый переход "
                f"{self._lifecycle.value***REMOVED*** → {target.value***REMOVED***. "
                f"Разрешено: {[s.value for s in sorted(allowed, key=lambda x: x.value)***REMOVED******REMOVED***"
            )
        self._lifecycle_history.append((self._lifecycle, reason))
        self._lifecycle = target

    @property
    def lifecycle_history(self) -> List[Dict[str, str***REMOVED******REMOVED***:
        """История переходов: [{"from": "created", "reason": "..."***REMOVED***, ...***REMOVED***."""
        return [
            {"from": state.value, "reason": reason***REMOVED***
            for state, reason in self._lifecycle_history
        ***REMOVED***

    # ── Abstract execute ───────────────────────────────────────────────

    @abstractmethod
    def execute(
        self,
        project: "Project",
        task: Any,
        *,
        event_bus: Any = None,
    ) -> AgentResult:
        """Выполнить задачу агента на проекте.

        Подклассы ДОЛЖНЫ переопределить этот метод.

        Returns:
            AgentResult: результат со статусом ok/warn/error.
                Fail-safe: сбой → AgentResult(status="error", errors=[...***REMOVED***),
                НЕ exception наружу.
        """
        ...

    # ── Service: model routing ─────────────────────────────────────────

    def route_model(self) -> str:
        """Заррутить модель через SmartRouter по capabilities агента.

        Использует ``self.capabilities`` (закрытое подмножество
        KNOWN_CAPABILITIES). Fallback на "fallback" при любом сбое.

        Returns:
            model_id (str) — имя модели из ModelCatalog, или "fallback".
        """
        caps = list(self.capabilities) if self.capabilities else ["summarize"***REMOVED***
        try:
            from core_02.router import ModelCatalog, SmartRouter  # lazy import (fail-safe)

            catalog = ModelCatalog.default()  # type: ignore[attr-defined***REMOVED***
            router = SmartRouter(catalog)
            decision = router.route(required_capabilities=caps)
            return getattr(decision, "model", "fallback") or "fallback"
        except Exception:
            return "fallback"

    # ── Service: forge delegation ──────────────────────────────────────

    def run_forge(
        self,
        project: "Project",
        role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
    ) -> Dict[str, Any***REMOVED***:
        """Делегировать ForgeFacade.run_chain — единственный санкционированный мост к Forge (§7.3).

        Использует ``self.role_ids`` если ``role_ids`` не переданы явно.
        Fail-safe: возвращает ``{"status": "error", ...***REMOVED***`` при сбое,
        НЕ exception наружу.

        Returns:
            dict с ключами status/error/chain_id (зависит от ForgeFacade).
        """
        ids: tuple[str, ...***REMOVED*** = role_ids or self.role_ids
        try:
            from core_02.forge_facade import ForgeFacade  # lazy import (fail-safe)

            facade = ForgeFacade()
            result = facade.run_chain(project, role_ids=ids)
            if hasattr(result, "to_dict"):
                return result.to_dict()
            return {"status": "ok", "raw": str(result)***REMOVED***
        except Exception as exc:
            return {"status": "error", "error": str(exc)***REMOVED***

    # ── Serialisation ──────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "agent_id": self.agent_id,
            "role_ids": list(self.role_ids),
            "capabilities": sorted(self.capabilities),
            "model_capability": self.model_capability,
            "runtime": self.runtime,
            "lifecycle": self.lifecycle.value,
            "lifecycle_history": self.lifecycle_history,
        ***REMOVED***

    def __repr__(self) -> str:
        return (
            f"Agent(agent_id={self.agent_id!r***REMOVED***, "
            f"lifecycle={self.lifecycle.value***REMOVED***, "
            f"roles={list(self.role_ids)***REMOVED***, "
            f"caps={sorted(self.capabilities)***REMOVED***)"
        )

    # ── Helpers for subclasses ─────────────────────────────────────────

    def _ok(self, task: str, data: Any = None, **meta: Any) -> AgentResult:
        """Создать успешный AgentResult (status="ok")."""
        return AgentResult(
            status="ok",
            agent_id=self.agent_id,
            task=task,
            data=data,
            meta=meta,
        )

    def _err(self, task: str, errors: List[str***REMOVED***, data: Any = None, **meta: Any) -> AgentResult:
        """Создать ошибочный AgentResult (status="error")."""
        return AgentResult(
            status="error",
            agent_id=self.agent_id,
            task=task,
            data=data,
            errors=errors,
            meta=meta,
        )