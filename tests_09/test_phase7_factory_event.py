"""tests_09/test_phase7_factory_event.py — Phase 7 targeted integration tests.

Promt: pompts_11/090_19_phase7_contract_reconciliation.md §13 (TESTING).

Coverage (per §13 list):
  1. Opportunity schema (canonical 24-field round-trip);
  2. Factory selection (execute → FactoryRegistry.select_forge routing);
  3. Opportunity → Factory (provenance factory_selection);
  4. Factory → ForgeFacade (execute instantiates ForgeFacade, passes Project);
  5. Event publishing (opportunity.* / execution.* / scenario.selected / whim.*);
  6. Event payload (data dict shape);
  7. Lifecycle transitions (advance events);
  8. Persistence (OpportunityStore round-trip);
  9. Backward compatibility (no event_bus → no emission; fake ForgeFacade pattern).

Hermetic: event_bus=None → no emission; injected EventBus/mock → asserted publish.
ForgeFacade fake: @staticmethod run_chain (mirrors test_intelligence_loop_phase5).
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

import pytest

from scripts_01.opportunity_engine import (
    Opportunity,
    OpportunityStore,
    advance,
    execute,
    propose,
    discover_candidates,
    _select_factory_forge,
    _derive_capability,
)
from scripts_01.whim_capture import WhimStore, capture, triage, promote


# ─── Helpers ──────────────────────────────────────────────────────────────

def _make_opp(project_id: str = "proj-p7", **kwargs: Any) -> Opportunity:
    return Opportunity(
        id=kwargs.pop("id", "opp-p7-001"),
        project_id=project_id,
        title=kwargs.pop("title", "Phase 7 test opportunity"),
        description=kwargs.pop("description", "Factory + event closure test"),
        source=kwargs.pop("source", "hand"),
        **kwargs,
    )


def _mock_forge_facade(monkeypatch: pytest.MonkeyPatch, result: Any) -> List[str]:
    """Подмена core_02.forge_facade на фейк с @staticmethod run_chain (как в phase5)."""
    calls: List[str] = []

    class _FakeForgeFacade:
        PIPELINE_CHAIN = ["r1", "r2"]

        @staticmethod
        def run_chain(*args: Any, **kwargs: Any) -> Any:
            calls.append("run_chain")
            if isinstance(result, Exception):
                raise result
            return result

    fake_module = types.ModuleType("core_02.forge_facade")
    fake_module.ForgeFacade = _FakeForgeFacade  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core_02.forge_facade", fake_module)
    return calls


class _FakeChainRun:
    """Минимальный результат run_chain с to_dict (как у ChainRun)."""

    def __init__(self, overall: str = "ok") -> None:
        self.overall = overall
        self.stage_count = 2

    def to_dict(self) -> Dict[str, Any]:
        return {"overall": self.overall, "stage_count": self.stage_count}


class _RecordingBus:
    """Простой тестовый EventBus-дублёр: записывает (type, data, source)."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def publish(self, event: Any) -> int:
        self.events.append({
            "type": event.type,
            "data": dict(event.data),
            "source": event.source,
        })
        return 1


# ═════════════════════════════════════════════════════════════════════════
# 1. Opportunity schema — canonical 24-field round-trip (§5 Task A)
# ═════════════════════════════════════════════════════════════════════════

def test_opportunity_schema_all_fields_roundtrip(tmp_path: Path):
    """Canonical schema: все поля dataclass переживают store round-trip (24 поля)."""
    opp = _make_opp(
        priority=7,
        scenario={"scenario_id": "blueprint_v3", "role_id": "architect", "score": 0.9},
        roles=[{"role_id": "architect"}, {"role_id": "developer"}],
        artifacts=[{"raw": {"overall": "ok"}}],
        source_path="/tmp/x",
        evidence_path="/tmp/y",
        related_decisions=["d1"],
        related_whims=["w1"],
    )
    store = OpportunityStore(tmp_path / "opps.yaml")
    store.upsert(opp)
    loaded = store.get(opp.id)
    assert loaded is not None
    assert loaded.to_dict() == opp.to_dict()
    assert len(opp.to_dict()) >= 24, "canonical schema должен включать все 24 поля"


def test_opportunity_schema_canonical_field_set():
    """Canonical field set — §E reconciled: документированные поля + lifecycle audit."""
    fields = set(Opportunity.__dataclass_fields__)
    # §E дизайн-поля (reconciled → implementation canonical)
    for f in ("id", "project_id", "source", "description", "status", "provenance",
              "created_at", "updated_at", "related_decisions"):
        assert f in fields, f"canonical поле {f} отсутствует"
    # lifecycle audit + execution поля (реальные, из implementation)
    for f in ("priority", "scenario", "roles", "artifacts", "source_path",
              "evidence_path", "deferred_at", "deferred_reason", "previous_status",
              "reactivated_at", "completed_at", "failed_at", "failure_reason",
              "related_whims", "title"):
        assert f in fields, f"runtime поле {f} отсутствует"


# ═════════════════════════════════════════════════════════════════════════
# 2-4. Factory selection: Opportunity → Factory → ForgeFacade (§6 Task B)
# ═════════════════════════════════════════════════════════════════════════

class _FakeFactoryPassport:
    def __init__(self, factory_id: str) -> None:
        self.factory_id = factory_id


class _FakeForgePassport:
    def __init__(self, forge_id: str) -> None:
        self.forge_id = forge_id


class _FakeFactoryRegistry:
    """select_forge возвращает фиксированную (factory, forge) пару."""

    def __init__(self, pair: Any) -> None:
        self._pair = pair
        self.calls: List[str] = []

    def select_forge(self, capability: str, prefer_status: Any = None) -> Any:
        self.calls.append(capability)
        return self._pair


def test_derive_capability_from_provenance():
    """Capability берётся из provenance.capability (закрытый словарь ANTI-6b)."""
    opp = _make_opp()
    opp.provenance["capability"] = "review"
    assert _derive_capability(opp) == "review"


def test_derive_capability_from_scenario():
    """Capability из scenario.capability, если provenance пуст."""
    opp = _make_opp(scenario={"capability": "architecture"})
    assert _derive_capability(opp) == "architecture"


def test_derive_capability_none_when_absent():
    """Нет capability → None (caller использует pipeline fallback)."""
    opp = _make_opp()
    assert _derive_capability(opp) is None


def test_select_factory_forge_routes_by_capability():
    """Factory selection: select_forge(capability) вызывается с выведенным токеном."""
    pair = (_FakeFactoryPassport("architecture"), _FakeForgePassport("review"))
    reg = _FakeFactoryRegistry(pair)
    opp = _make_opp()
    opp.provenance["capability"] = "review"
    selected = _select_factory_forge(opp, factory_registry=reg)
    assert selected == pair
    assert reg.calls == ["review"]


def test_select_factory_forge_none_without_capability():
    """Без capability → None, FactoryRegistry НЕ инстанцируется (hermetic)."""
    opp = _make_opp()
    assert _select_factory_forge(opp, factory_registry=_FakeFactoryRegistry(None)) is None


def test_execute_records_factory_selection_and_runs_chain(monkeypatch, tmp_path):
    """execute(): select_forge найден → provenance factory_selection + run_chain вызван."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    pair = (_FakeFactoryPassport("architecture"), _FakeForgePassport("review"))
    reg = _FakeFactoryRegistry(pair)

    opp = _make_opp()
    opp.provenance["capability"] = "review"
    opp.roles = [{"role_id": "r1"}, {"role_id": "r2"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_fs.db"),
                  factory_registry=reg)

    assert calls == ["run_chain"]
    assert opp.status == "COMPLETED"
    sel = opp.provenance.get("factory_selection") or {}
    assert sel.get("factory_id") == "architecture"
    assert sel.get("forge_id") == "review"
    assert sel.get("capability") == "review"


def test_execute_factory_fallback_backward_compat(monkeypatch, tmp_path):
    """execute(): нет capability → fallback dict, run_chain всё равно вызван (backward compat)."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = _make_opp()  # без capability
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_fb.db"))

    assert calls == ["run_chain"]
    assert opp.status == "COMPLETED"
    sel = opp.provenance.get("factory_selection") or {}
    assert sel.get("fallback") is True


def test_execute_passes_project_object_not_string(monkeypatch, tmp_path):
    """GAP A fix: execute передаёт Project-объект (НЕ строку project_id) в run_chain."""
    from core_02.memory_store import MemoryStore
    from core_02.workspace import Project

    captured: Dict[str, Any] = {}

    class _CapturingFacade:
        @staticmethod
        def run_chain(*args: Any, **kwargs: Any) -> Any:
            captured["project"] = args[0] if args else None
            return _FakeChainRun(overall="ok")

    fake_module = types.ModuleType("core_02.forge_facade")
    fake_module.ForgeFacade = _CapturingFacade  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core_02.forge_facade", fake_module)

    # Реальный минимальный проект в tmp_path + project_root → Project объект.
    proj_root = tmp_path / "proj"
    proj_root.mkdir(parents=True, exist_ok=True)
    (proj_root / "project.yaml").write_text(
        "name: proj-p7\ntype: script\n", encoding="utf-8"
    )

    opp = _make_opp(project_id="proj-p7")
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_proj.db"),
                  project_root=proj_root)
    assert opp.status == "COMPLETED"
    # GAP A fix подтверждён: передаётся Project-объект (не строка project_id).
    assert isinstance(captured.get("project"), Project)
    assert captured["project"].root == proj_root


# ═════════════════════════════════════════════════════════════════════════
# 5-6. Event publishing: opportunity.* / execution.* / scenario.selected / whim.*
# ═════════════════════════════════════════════════════════════════════════

def test_execute_emits_execution_events(monkeypatch, tmp_path):
    """execute(): execution.started + execution.completed публикуются (payload корректен)."""
    from core_02.memory_store import MemoryStore

    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    bus = _RecordingBus()
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_ev.db"),
                  event_bus=bus)

    types_ = [e["type"] for e in bus.events]
    assert "execution.started" in types_
    assert "execution.completed" in types_
    started = next(e for e in bus.events if e["type"] == "execution.started")
    assert started["data"]["opportunity_id"] == opp.id
    assert started["data"]["project_id"] == "proj-p7"
    assert started["source"] == "opportunity_engine"


def test_execute_emits_execution_failed_on_exception(monkeypatch, tmp_path):
    """execute(): run_chain raise → execution.failed + opportunity.failed публикуются."""
    from core_02.memory_store import MemoryStore

    _mock_forge_facade(monkeypatch, RuntimeError("forge boom"))
    bus = _RecordingBus()
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_evf.db"),
                  event_bus=bus)

    types_ = [e["type"] for e in bus.events]
    assert "execution.failed" in types_
    assert "opportunity.failed" in types_
    failed = next(e for e in bus.events if e["type"] == "execution.failed")
    assert "forge boom" in failed["data"]["reason"]
    assert opp.status == "FAILED"


def test_advance_emits_lifecycle_events():
    """advance(): DEFERRED/REACTIVATED/COMPLETED/FAILED публикуют opportunity.* события."""
    bus = _RecordingBus()
    opp = _make_opp()

    advance(opp, "DEFERRED", reason="busy", event_bus=bus)
    assert any(e["type"] == "opportunity.deferred" for e in bus.events)
    deferred = next(e for e in bus.events if e["type"] == "opportunity.deferred")
    assert deferred["data"]["reason"] == "busy"
    assert deferred["data"]["previous_status"] == "ACTIVE"

    advance(opp, "REACTIVATED", event_bus=bus)
    assert any(e["type"] == "opportunity.reactivated" for e in bus.events)

    advance(opp, "READY", event_bus=bus)  # READY не эмитится (не в §J списке)
    advance(opp, "COMPLETED", reason="done", event_bus=bus)
    assert any(e["type"] == "opportunity.completed" for e in bus.events)


def test_propose_emits_scenario_selected(monkeypatch):
    """propose(): при найденном scenario публикует scenario.selected (реальный propose)."""
    # Hermetic: подменяем sys.modules['core_02.scenario_registry'] на фейк-модуль
    # (тот же паттерн, что _mock_forge_facade). Реальный ScenarioRegistry() грузит
    # манифесты с диска и может упасть на vkusvill_demo.yaml (unknown scenario_type
    # 'teamwork') → propose() вернул бы opp.scenario=None. Фейк детерминирован.
    class _FakeRole:
        role_id = "architect"
        title = "Architect"

    class _FakeScenario:
        scenario_id = "blueprint_v3"

    class _FakeScenarioRegistry:
        def __init__(self) -> None:
            pass

        def propose_roles(self, query: str, top_n: int = 3):
            return [(_FakeScenario(), _FakeRole(), 0.9)]

    fake_module = types.ModuleType("core_02.scenario_registry")
    fake_module.ScenarioRegistry = _FakeScenarioRegistry  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core_02.scenario_registry", fake_module)

    from scripts_01.opportunity_engine import propose as _propose
    bus = _RecordingBus()
    opp = _propose(_make_opp(), event_bus=bus)
    assert opp.scenario is not None
    assert any(e["type"] == "scenario.selected" for e in bus.events)
    ev = next(e for e in bus.events if e["type"] == "scenario.selected")
    assert ev["data"]["scenario_id"] == "blueprint_v3"
    assert ev["data"]["role_id"] == "architect"


def test_whim_capture_emits_captured(tmp_path):
    """whim_capture.capture(): публикует whim.captured."""
    bus = _RecordingBus()
    store = WhimStore(tmp_path / "whims.yaml")
    w = capture("Создать книгу", project_id="proj-p7", store=store, event_bus=bus)
    assert any(e["type"] == "whim.captured" for e in bus.events)
    ev = next(e for e in bus.events if e["type"] == "whim.captured")
    assert ev["data"]["whim_id"] == w.id
    assert ev["data"]["whim_source"] == "cli"


def test_whim_triage_emits_classified_single(tmp_path):
    """triage(): публикует РОВНО whim.classified (нет double-emit whim.triaged)."""
    bus = _RecordingBus()
    store = WhimStore(tmp_path / "whims.yaml")
    w = capture("Создать книгу по Workspace OS", project_id="proj-p7", store=store)
    w = triage(w, classification="PROMOTE_CANDIDATE", event_bus=bus)
    types_ = [e["type"] for e in bus.events]
    assert "whim.classified" in types_
    assert "whim.triaged" not in types_, "triage должен владеть whim.classified, не whim.triaged"


def test_whim_promote_emits_promoted(tmp_path, monkeypatch):
    """promote(): успех → whim.promoted с opportunity_id (hermetic — DEFAULT_DATA_PATH на tmp)."""
    import scripts_01.opportunity_engine as oe

    # Критично: promote() внутри создаёт OpportunityStore(DEFAULT_DATA_PATH) —
    # патчим на tmp, чтобы НЕ писать в реальный data_13/opportunities.yaml.
    monkeypatch.setattr(oe, "DEFAULT_DATA_PATH", tmp_path / "opps_promote.yaml")

    bus = _RecordingBus()
    store = WhimStore(tmp_path / "whims.yaml")
    w = capture("Создать книгу по Workspace OS", project_id="proj-p7", store=store)
    w = triage(w, classification="PROMOTE_CANDIDATE")
    w = promote(w, store=store, event_bus=bus)
    # opportunity_engine импортируем в этом окружении → детерминированный успех.
    assert w.status == "PROMOTED_TO_OPPORTUNITY"
    assert any(e["type"] == "whim.promoted" for e in bus.events)
    ev = next(e for e in bus.events if e["type"] == "whim.promoted")
    assert ev["data"]["opportunity_id"] == w.related_opportunity_id
    assert (tmp_path / "opps_promote.yaml").exists(), "promote должен писать в tmp (не real data_13)"


# ═════════════════════════════════════════════════════════════════════════
# 7. Lifecycle transitions
# ═════════════════════════════════════════════════════════════════════════

def test_lifecycle_transitions_with_events():
    """Полный lifecycle: ACTIVE→DEFERRED→REACTIVATED→READY→COMPLETED (события)."""
    bus = _RecordingBus()
    opp = _make_opp()
    advance(opp, "DEFERRED", event_bus=bus)
    assert opp.status == "DEFERRED"
    advance(opp, "REACTIVATED", event_bus=bus)
    assert opp.status == "ACTIVE"  # REACTIVATED collapse
    advance(opp, "READY", event_bus=bus)
    advance(opp, "COMPLETED", event_bus=bus)
    assert opp.status == "COMPLETED"
    types_ = {e["type"] for e in bus.events}
    assert {"opportunity.deferred", "opportunity.reactivated", "opportunity.completed"} <= types_


def test_execute_deferred_reactivates_and_completes(monkeypatch, tmp_path):
    """execute() на DEFERRED: реактивация по графу → COMPLETED (не краш, fail-safe)."""
    from core_02.memory_store import MemoryStore

    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"}]
    advance(opp, "DEFERRED", reason="busy")
    assert opp.status == "DEFERRED"
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_def.db"))
    assert opp.status == "COMPLETED"
    assert opp.reactivated_at is not None, "DEFERRED должен быть реактивирован перед run"


def test_execute_completed_is_noop(monkeypatch, tmp_path):
    """execute() на COMPLETED: терминальный статус не трогаем (no-op, без краша)."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = _make_opp()
    opp.status = "COMPLETED"
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_term.db"))
    assert opp.status == "COMPLETED"
    assert calls == [], "повторный execute на COMPLETED не должен запускать chain"


def test_execute_degrade_path_emits_execution_failed(monkeypatch, tmp_path):
    """execute() на REACTIVATED (не нормализуется): terminal advance → FAILED + execution.failed.

    Регрессия на reviewer-nit: degrade-путь должен эмитить execution.failed (НЕ
    execution.completed) и не крашить (never raises). REACTIVATED задан напрямую
    (advance(REACTIVATED) схлопывается в ACTIVE, поэтому в персистенции не встречается).
    """
    from core_02.memory_store import MemoryStore

    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    bus = _RecordingBus()
    opp = _make_opp()
    opp.status = "REACTIVATED"  # невалидный входной статус для execute
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_degrade.db"),
                  event_bus=bus)
    assert opp.status == "FAILED"
    types_ = [e["type"] for e in bus.events]
    assert "execution.failed" in types_
    assert "execution.completed" not in types_, \
        "degrade-путь не должен эмитить execution.completed"
    failed = next(e for e in bus.events if e["type"] == "execution.failed")
    assert "cannot complete from status" in failed["data"]["reason"]


# ── Real EventBus integration (закрывает риск silent no-op в _emit_event) ──

def test_emit_event_real_eventbus_roundtrip(tmp_path):
    """_emit_event с РЕАЛЬНЫМ EventBus (tmp db): publish → get_events читаемо.

    Если реальная сигнатура Event(type, source, data) разойдётся с _emit_event,
    этот тест упадёт, а не молча проглотит try/except (best-effort маскировка).
    """
    from scripts_01.event_bus import EventBus
    from scripts_01.opportunity_engine import _emit_event

    bus = EventBus(db_path=tmp_path / "events.db")
    _emit_event(bus, "execution.started", source="opportunity_engine",
                opportunity_id="opp-1", project_id="proj-p7", role_ids=["r1"])
    entries = bus.get_events(event_type="execution.started", limit=10)
    assert len(entries) == 1
    assert entries[0].source == "opportunity_engine"
    data = json.loads(entries[0].data_json)
    assert data["opportunity_id"] == "opp-1"
    assert data["project_id"] == "proj-p7"
    assert data["role_ids"] == ["r1"]


def test_execute_with_real_eventbus(tmp_path, monkeypatch):
    """execute() с реальным EventBus (tmp db): lifecycle-события читаемы из лога."""
    from core_02.memory_store import MemoryStore
    from scripts_01.event_bus import EventBus

    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    bus = EventBus(db_path=tmp_path / "events2.db")
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"}]
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_real.db"),
                  event_bus=bus)
    assert opp.status == "COMPLETED"
    types_ = {e.event_type for e in bus.get_events(limit=50)}
    assert {"execution.started", "execution.completed", "opportunity.completed"} <= types_


# ═════════════════════════════════════════════════════════════════════════
# 8. Persistence
# ═════════════════════════════════════════════════════════════════════════

def test_persistence_roundtrip_with_factory_selection(tmp_path):
    """Persistence: factory_selection provenance переживает store round-trip."""
    store = OpportunityStore(tmp_path / "opps_p.yaml")
    opp = _make_opp(priority=9)
    opp.provenance["factory_selection"] = {
        "factory_id": "architecture", "forge_id": "review", "capability": "review",
    }
    store.upsert(opp)
    loaded = store.get(opp.id)
    assert loaded is not None
    assert loaded.provenance["factory_selection"]["forge_id"] == "review"
    assert loaded.priority == 9


# ═════════════════════════════════════════════════════════════════════════
# 9. Backward compatibility
# ═════════════════════════════════════════════════════════════════════════

def test_no_event_bus_means_no_emission(monkeypatch, tmp_path):
    """Backward compat: event_bus=None (default) → НЕ публикуется (hermetic)."""
    from core_02.memory_store import MemoryStore

    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"}]
    # Без event_bus — execute не должен падать и не должен требовать bus.
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem_bc.db"))
    assert opp.status == "COMPLETED"


def test_discover_candidates_still_works(tmp_path):
    """Backward compat: discover_candidates без изменений (fail-safe, пустые источники)."""
    opp_store = OpportunityStore(tmp_path / "opps_d.yaml")
    cands = discover_candidates(
        "proj-p7", max_results=3, store=opp_store,
        source_paths={"whims": tmp_path / "no_whims.yaml",
                      "pulse": tmp_path / "no_pulse.db",
                      "events": tmp_path / "no_events.db",
                      "memory": tmp_path / "no_mem.db"},
    )
    assert cands == []
