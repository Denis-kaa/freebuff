"""tests_09/test_agent_base.py — Hermetic тесты Agent base class (ADR-019).

Покрывает:
- Lifecycle DAG (ALLOWED_TRANSITIONS + idempotency + history)
- Capability validation (ANTI-6b: unknown token → ValueError)
- route_model (fake SmartRouter, capability-делегат, fail-safe)
- run_forge (fake ForgeFacade, role_ids-делегат, fail-safe)
- execute (абстрактный метод)
- to_dict / AgentResult serialisation
- 🚫 §7.3 grep-инвариант: Agent НЕ вызывает ForgePipeline напрямую
"""

from __future__ import annotations

}
from typing import Any, Dict, List
from uuid import uuid4

import pytest

from core_02.agent_base import (
    ALLOWED_TRANSITIONS,
    KNOWN_CAPABILITIES,
    Agent,
    AgentLifecycle,
    AgentResult,
)
from core_02.workspace import Project


# ═══════════════════════════════════════════════════════════════════════
# Fake / helper classes
# ═══════════════════════════════════════════════════════════════════════

class _FakeConcreteAgent(Agent):
    """Минимальная конкретная реализация Agent для тестов lifecycle и serialisation."""

    def execute(
        self,
        project: Project,
        task: Any,
        *,
        event_bus: Any = None,
    ) -> AgentResult:
        return self._ok(task=task, data={"executed": True})


class _FakeFailingAgent(Agent):
    """Агент, чей execute всегда возвращает ошибку."""

    def execute(
        self,
        project: Project,
        task: Any,
        *,
        event_bus: Any = None,
    ) -> AgentResult:
        return self._err(task=task, errors=["simulated failure"])


class _FakeRouteDecision:
    """Фейк RouteDecision для тестов route_model."""

    def __init__(self, model: str, provider: Any = None, reason: str = "", fallback_used: bool = False) -> None:
        self.model = model
        self.provider = provider
        self.reason = reason
        self.fallback_used = fallback_used


class _FakeChainRun:
    """Фейк ChainRun для тестов run_forge."""

    def __init__(self, chain_id: str = "chain-test", status: str = "ok") -> None:
        self.chain_id = chain_id
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {"chain_id": self.chain_id, "status": self.status}


class _FakeForgeFacade:
    """Фейк ForgeFacade для тестов run_forge."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def run_chain(self, project: Project, role_ids: List[str]) -> _FakeChainRun:
        self.calls.append({
            "project_name": project.name,
            "role_ids": list(role_ids),
        ])
        return _FakeChainRun(chain_id=f"chain-{len(self.calls)}")


class _FakeForgeFacadeRaising:
    """Фейк ForgeFacade, всегда бросающий исключение."""

    def run_chain(self, project: Project, role_ids: List[str]) -> None:  # type: ignore[return]
        raise RuntimeError("forge unavailable")


# ═══════════════════════════════════════════════════════════════════════
# Test: Lifecycle state machine
# ═══════════════════════════════════════════════════════════════════════

class TestAgentLifecycleDAG:
    """Forward-only lifecycle DAG per ADR-019."""

    def test_initial_lifecycle_is_created(self) -> None:
        agent = _FakeConcreteAgent()
        assert agent.lifecycle == AgentLifecycle.CREATED

    def test_valid_forward_transitions(self) -> None:
        transitions = [
            (AgentLifecycle.ACTIVE, "started"),
            (AgentLifecycle.PAUSED, "paused for maintenance"),
            (AgentLifecycle.ACTIVE, "resumed"),
            (AgentLifecycle.DONE, "completed"),
        ]
        agent = _FakeConcreteAgent()
        for target, reason in transitions:
            agent.transition(target, reason)
            assert agent.lifecycle == target

        # DONE is terminal
        with pytest.raises(ValueError, match="недопустимый переход"):
            agent.transition(AgentLifecycle.ACTIVE)

    def test_retry_from_failed_to_active(self) -> None:
        agent = _FakeConcreteAgent()
        agent.transition(AgentLifecycle.ACTIVE, "started")
        agent.transition(AgentLifecycle.FAILED, "crashed")
        agent.transition(AgentLifecycle.ACTIVE, "retry")  # единственный обратный переход
        assert agent.lifecycle == AgentLifecycle.ACTIVE

    def test_idempotent_transition_noop(self) -> None:
        agent = _FakeConcreteAgent()
        agent.transition(AgentLifecycle.ACTIVE, "first")
        # Повтор того же состояния — no-op (без ошибки)
        agent.transition(AgentLifecycle.ACTIVE, "second")
        assert agent.lifecycle == AgentLifecycle.ACTIVE
        # В истории только первый переход
        assert len(agent.lifecycle_history) == 1

    def test_invalid_transition_raises_with_allowed_list(self) -> None:
        agent = _FakeConcreteAgent()
        with pytest.raises(ValueError, match="недопустимый переход"):
            agent.transition(AgentLifecycle.DONE)  # CREATED → DONE запрещён

    def test_lifecycle_history_records_transitions(self) -> None:
        agent = _FakeConcreteAgent()
        agent.transition(AgentLifecycle.ACTIVE, "start work")
        agent.transition(AgentLifecycle.DONE, "finished")
        history = agent.lifecycle_history
        assert len(history) == 2
        assert history[0] == {"from": "created", "reason": "start work"}
        assert history[1] == {"from": "active", "reason": "finished"}

    def test_allowed_transitions_table_is_complete(self) -> None:
        """Каждое состояние имеет запись в ALLOWED_TRANSITIONS."""
        for state in AgentLifecycle:
            assert state in ALLOWED_TRANSITIONS, f"missing {state}"


# ═══════════════════════════════════════════════════════════════════════
# Test: Capability validation (ANTI-6b)
# ═══════════════════════════════════════════════════════════════════════

class TestCapabilityValidation:
    """ANTI-6b: capabilities — closed subset of KNOWN_CAPABILITIES."""

    def test_known_capabilities_accepted(self) -> None:
        agent = _FakeConcreteAgent(capabilities=frozenset({"code", "review", "summarize"}))
        assert agent.capabilities == frozenset({"code", "review", "summarize"})

    def test_empty_capabilities_accepted(self) -> None:
        agent = _FakeConcreteAgent()
        assert agent.capabilities == frozenset()

    def test_unknown_capability_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="KNOWN_CAPABILITIES"):
            _FakeConcreteAgent(capabilities=frozenset({"code", "fantasy_token_xyz"}))

    def test_error_message_lists_unknown_tokens(self) -> None:
        with pytest.raises(ValueError) as exc:
            _FakeConcreteAgent(capabilities=frozenset({"nonexistent_a", "nonexistent_b"}))
        msg = str(exc.value)
        assert "nonexistent_a" in msg
        assert "nonexistent_b" in msg


# ═══════════════════════════════════════════════════════════════════════
# Test: route_model
# ═══════════════════════════════════════════════════════════════════════

class TestRouteModel:
    """Capability → SmartRouter.route → model_id."""

    def test_route_model_returns_string(self) -> None:
        """Без возможностей — fallback на 'summarize', возвращает строку."""
        agent = _FakeConcreteAgent()
        model = agent.route_model()
        assert isinstance(model, str)
        assert len(model) > 0

    def test_route_model_uses_agent_capabilities(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Проверяет, что route_model передаёт capabilities в SmartRouter.route."""
        captured_caps: List[List[str]] = []

        class _FakeCatalog:
            @staticmethod
            def default() -> "_FakeCatalog":
                return _FakeCatalog()

        class _FakeRouter:
            def __init__(self, catalog: Any) -> None:
                self.catalog = catalog

            def route(self, required_capabilities: List[str] | None = None, **kwargs: Any) -> _FakeRouteDecision:
                captured_caps.append(list(required_capabilities or []))
                return _FakeRouteDecision(model="test-model")

        # lazy-import внутри route_model: from core_02.router import ...
        monkeypatch.setattr("core_02.router.SmartRouter", _FakeRouter)
        monkeypatch.setattr("core_02.router.ModelCatalog", _FakeCatalog)

        agent = _FakeConcreteAgent(capabilities=frozenset({"code", "review"}))
        result = agent.route_model()
        assert result == "test-model"
        assert len(captured_caps) == 1
        assert set(captured_caps[0]) == {"code", "review"}

    def test_route_model_fallback_on_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fail-safe: ошибка импорта → 'fallback'."""
        agent = _FakeConcreteAgent(capabilities=frozenset({"code"}))

        def _fail_import(*args: Any, **kwargs: Any) -> None:
            raise ImportError("no router")

        # Ломаем lazy-import внутри route_model
        monkeypatch.setattr(
            "core_02.agent_base.SmartRouter",
            property(lambda self: _fail_import),  # type: ignore[arg-type]
            raising=False,
        )
        # Напрямую monkeypatch-им _lazy часть...
        # Проще: monkeypatch модуль router
        import core_02.agent_base as ab

        original_import = __import__

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "core_02.router":
                raise ImportError("simulated router unavailable")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _fake_import)
        # Invalidate any cached import
        result = agent.route_model()
        assert result == "fallback"


# ═══════════════════════════════════════════════════════════════════════
# Test: run_forge
# ═══════════════════════════════════════════════════════════════════════

class TestRunForge:
    """ForgeFacade.run_chain — единственный санкционированный мост (§7.3)."""

    @pytest.fixture
    def tmp_project(self, tmp_path: Any) -> Project:
        """Герметичный проект во временной директории."""
        root = tmp_path / "test_proj_run_forge"
        root.mkdir()
        (root / "project.yaml").write_text("name: test_proj_run_forge\n")
        return Project.load(root)

    def test_run_forge_delegates_to_facade(self, tmp_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        """Проверяет, что run_forge вызывает ForgeFacade.run_chain."""
        agent = _FakeConcreteAgent(role_ids=("developer", "architect"))
        fake_facade = _FakeForgeFacade()

        # lazy-import внутри run_forge: from core_02.forge_facade import ForgeFacade
        monkeypatch.setattr(
            "core_02.forge_facade.ForgeFacade",
            lambda: fake_facade,
        )

        result = agent.run_forge(tmp_project)
        assert result["status"] == "ok"
        assert "chain_id" in result
        assert len(fake_facade.calls) == 1
        assert fake_facade.calls[0]["role_ids"] == ["developer", "architect"]

    def test_run_forge_passes_explicit_role_ids(self, tmp_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        """Явные role_ids переопределяют self.role_ids."""
        agent = _FakeConcreteAgent(role_ids=("developer",))
        fake_facade = _FakeForgeFacade()

        monkeypatch.setattr(
            "core_02.forge_facade.ForgeFacade",
            lambda: fake_facade,
        )

        agent.run_forge(tmp_project, role_ids=("architect", "lisa"))
        assert fake_facade.calls[0]["role_ids"] == ["architect", "lisa"]

    def test_run_forge_failsafe_on_error(self, tmp_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fail-safe: исключение в ForgeFacade → {"status": "error", ...]."""
        agent = _FakeConcreteAgent(role_ids=("developer",))

        monkeypatch.setattr(
            "core_02.forge_facade.ForgeFacade",
            lambda: _FakeForgeFacadeRaising(),
        )

        result = agent.run_forge(tmp_project)
        assert result["status"] == "error"
        assert "error" in result
        assert "forge unavailable" in result["error"]

    def test_run_forge_failsafe_on_import_error(self, tmp_project: Project, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fail-safe: ImportError → {"status": "error", ...]."""
        agent = _FakeConcreteAgent(role_ids=("developer",))

        original_import = __import__

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "core_02.forge_facade":
                raise ImportError("simulated forge_facade unavailable")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _fake_import)
        result = agent.run_forge(tmp_project)
        assert result["status"] == "error"


# ═══════════════════════════════════════════════════════════════════════
# Test: §7.3 grep-инвариант
# ═══════════════════════════════════════════════════════════════════════

class TestForgePipelineInvariant:
    """§7.3: Agent НЕ вызывает ForgePipeline напрямую — только ForgeFacade."""

    def test_agent_base_does_not_import_forge_pipeline(self) -> None:
        """Гарантия: в agent_base.py нет import ForgePipeline."""
        src = __import__("core_02.agent_base").agent_base.__file__
        assert src is not None
        text = open(src, encoding="utf-8").read()
        # Допустимы только упоминания в комментариях/докстрингах («не вызывает»)
        code_only = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
        code_only = re.sub(r"#.*", "", code_only)
        assert "ForgePipeline" not in code_only, (
            "§7.3 violation: Agent импортирует/использует ForgePipeline напрямую "
            "(допустим только ForgeFacade)"
        )

    def test_agent_base_only_delegates_to_forge_facade(self) -> None:
        """Гарантия: run_forge вызывает только ForgeFacade, не ForgePipeline."""
        import inspect
        src = inspect.getsource(Agent.run_forge)
        assert "ForgeFacade" in src
        assert "ForgePipeline" not in src


# ═══════════════════════════════════════════════════════════════════════
# Test: execute + AgentResult
# ═══════════════════════════════════════════════════════════════════════

class TestExecuteAndResult:
    """Абстрактный execute + AgentResult (ok/err сериализация)."""

    @pytest.fixture
    def tmp_project(self, tmp_path: Any) -> Project:
        root = tmp_path / "test_proj_exec"
        root.mkdir()
        (root / "project.yaml").write_text("name: test_proj_exec\n")
        return Project.load(root)

    def test_concrete_agent_execute_returns_ok(self, tmp_project: Project) -> None:
        agent = _FakeConcreteAgent(role_ids=("developer",))
        result = agent.execute(tmp_project, task="test task")
        assert result.ok is True
        assert result.status == "ok"
        assert result.agent_id == agent.agent_id
        assert result.data == {"executed": True}

    def test_failing_agent_execute_returns_error(self, tmp_project: Project) -> None:
        agent = _FakeFailingAgent()
        result = agent.execute(tmp_project, task="will fail")
        assert result.ok is False
        assert result.status == "error"
        assert "simulated failure" in result.errors

    def test_agent_result_to_dict(self) -> None:
        result = AgentResult(
            status="ok",
            agent_id="agent-001",
            task="build",
            data={"files": ["out.md"]},
            warnings=["slow"],
            meta={"elapsed": 1.5},
            model_used="deepseek-v4-flash",
        )
        d = result.to_dict()
        assert d["status"] == "ok"
        assert d["agent_id"] == "agent-001"
        assert d["data"] == {"files": ["out.md"]}
        assert d["warnings"] == ["slow"]
        assert d["model_used"] == "deepseek-v4-flash"
        assert "forge_result" not in d  # None не сериализуется

    def test_agent_result_with_forge_result(self) -> None:
        result = AgentResult(
            status="ok",
            agent_id="agent-002",
            task="forge task",
            forge_result={"chain_id": "abc", "status": "ok"},
        )
        d = result.to_dict()
        assert d["forge_result"] == {"chain_id": "abc", "status": "ok"}


# ═══════════════════════════════════════════════════════════════════════
# Test: to_dict / serialisation
# ═══════════════════════════════════════════════════════════════════════

class TestSerialisation:
    """Agent.to_dict() + __repr__."""

    def test_to_dict_includes_all_fields(self) -> None:
        agent_id = "agent-test-001"
        agent = _FakeConcreteAgent(
            agent_id=agent_id,
            role_ids=("developer", "reviewer"),
            capabilities=frozenset({"code", "review"}),
            runtime="local",
        )
        d = agent.to_dict()
        assert d["agent_id"] == agent_id
        assert d["role_ids"] == ["developer", "reviewer"]
        assert set(d["capabilities"]) == {"code", "review"}
        assert d["runtime"] == "local"
        assert d["lifecycle"] == "created"
        assert d["lifecycle_history"] == []

    def test_to_dict_includes_lifecycle_history(self) -> None:
        agent = _FakeConcreteAgent()
        agent.transition(AgentLifecycle.ACTIVE, "start")
        agent.transition(AgentLifecycle.DONE, "finish")
        d = agent.to_dict()
        assert d["lifecycle"] == "done"
        assert len(d["lifecycle_history"]) == 2

    def test_repr_includes_key_fields(self) -> None:
        agent = _FakeConcreteAgent(
            agent_id="rep-test",
            role_ids=("dev",),
            capabilities=frozenset({"code"}),
        )
        r = repr(agent)
        assert "rep-test" in r
        assert "created" in r
        assert "code" in r

    def test_agent_id_auto_generated_unique(self) -> None:
        a1 = _FakeConcreteAgent()
        a2 = _FakeConcreteAgent()
        assert a1.agent_id != a2.agent_id
        assert len(a1.agent_id) == 12


# ═══════════════════════════════════════════════════════════════════════
# Test: known_capabilities is consistent with blueprint_v3
# ═══════════════════════════════════════════════════════════════════════

class TestKnownCapabilitiesConsistency:
    """KNOWN_CAPABILITIES в agent_base.py синхронизирован с blueprint_v3.py."""

    def test_agent_base_known_capabilities_subset_of_blueprint_v3(self) -> None:
        """agent_base.KNOWN_CAPABILITIES ⊆ blueprint_v3.KNOWN_CAPABILITIES."""
        from core_02.blueprint_v3 import KNOWN_CAPABILITIES as BV3_CAPS
        from core_02.agent_base import KNOWN_CAPABILITIES as AB_CAPS

        extra = AB_CAPS - BV3_CAPS
        assert not extra, (
            f"agent_base.KNOWN_CAPABILITIES содержит токены вне blueprint_v3: {sorted(extra)}. "
            f"Синхронизируй оба словаря (ADR-019 §Decision пункт 2)."
        )