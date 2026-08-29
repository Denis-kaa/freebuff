"""tests_09/test_intelligence_loop_phase5.py — Phase 5: Close the Intelligence Loop.

Реализация промта ``pompts_11/085_19_close_intelligence_loop.md``:
GAP-1 (REAL DISCOVER) + GAP-2 (ACCUMULATE в MemoryStore → LearningLoop).

§19 — обязательный минимальный набор тестов (TEST 1–10):
  TEST 1  real source → discover candidate
  TEST 2  candidate → opportunity
  TEST 3  opportunity → scenario
  TEST 4  scenario → existing execution path
  TEST 5  execution → artifact
  TEST 6  artifact → memory
  TEST 7  memory → learning
  TEST 8  same source repeated → no uncontrolled duplicate opportunity
  TEST 9  DEFERRED opportunity remains recoverable
  TEST 10 failure does not become false COMPLETED

§20 — один реальный E2E vertical slice (мок только внешних ресурсов:
ForgeFacade/ScenarioRegistry — их реальные прогоны тяжелы; WhimStore/
OpportunityStore/MemoryStore/LearningLoop — реальные, на tmp-путях).
"""
from __future__ import annotations

import sys
import types
***REMOVED***
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1***REMOVED***
SCRIPTS_DIR = REPO_ROOT / "scripts_01"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT))

from opportunity_engine import (  # noqa: E402
    Opportunity,
    OpportunityStore,
    advance,
    accumulate,
    discover_candidates,
    execute,
    propose,
)
from scripts_01.whim_capture import WhimStore, capture, triage  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_opp(project_id: str = "proj-e2e", **kwargs: Any) -> Opportunity:
    opp = Opportunity(
        id="opp-phase5-001",
        project_id=project_id,
        title="Phase 5 test opportunity",
        description="Vertical slice test",
        source="hand",
        status="ACTIVE",
    )
    for k, v in kwargs.items():
        setattr(opp, k, v)
    return opp


def _seed_whim(tmp_path: Path, project_id: str, body: str = "Написать книгу про архитектуру") -> tuple[WhimStore, Path, str***REMOVED***:
    """Seed реального whim-источника (WhimStore на tmp-пути). Возвращает (store, path, whim_id)."""
    whims_yaml = tmp_path / "whims.yaml"
    wstore = WhimStore(whims_yaml)
    w = capture(body, project_id=project_id, source="cli", store=wstore)
    triage(w, classification="PROMOTE_CANDIDATE", reason="book keyword")
    wstore.upsert(w)
    return wstore, whims_yaml, w.id


def _hermetic_sources(tmp_path: Path, whims_yaml: Path | None = None) -> Dict[str, Path***REMOVED***:
    """Герметичный source_paths: whims (если задан) + НЕСУЩЕСТВУЮЩИЕ tmp-пути
    для pulse/events/memory. Без этого остальные источники читают РЕАЛЬНЫЕ
    data_13/project_pulse.db / context_12/events.db / data_13/context.db
    и тесты зависят от состояния репозитория (reviewer nit round 2).
    """
    return {
        "whims": whims_yaml if whims_yaml is not None else tmp_path / "missing_whims.yaml",
        "pulse": tmp_path / "missing_pulse.db",
        "events": tmp_path / "missing_events.db",
        "memory": tmp_path / "missing_memory.db",
    ***REMOVED***


def _mock_forge_facade(monkeypatch: pytest.MonkeyPatch, result: Any) -> List[str***REMOVED***:
    """Подмена core_02.forge_facade на фейк с run_chain (как в test_opportunity_engine)."""
    calls: List[str***REMOVED*** = [***REMOVED***

    class _FakeForgeFacade:
        PIPELINE_CHAIN = ["r1", "r2"***REMOVED***

        @staticmethod
        def run_chain(*args: Any, **kwargs: Any) -> Any:
            calls.append("run_chain")
            if isinstance(result, Exception):
                raise result
            return result

    fake_module = types.ModuleType("core_02.forge_facade")
    fake_module.ForgeFacade = _FakeForgeFacade
    monkeypatch.setitem(sys.modules, "core_02.forge_facade", fake_module)
    return calls


class _FakeChainRun:
    """Минимальный результат run_chain с to_dict (как у ChainRun)."""

    def __init__(self, overall: str = "ok") -> None:
        self.overall = overall
        self.stage_count = 2

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {"overall": self.overall, "stage_count": self.stage_count***REMOVED***


# ═════════════════════════════════════════════════════════════════════════
# TEST 1 — real source → discover candidate
# ═════════════════════════════════════════════════════════════════════════

def test_1_real_whim_source_discover_candidate(tmp_path: Path):
    """GAP-1: реальный whim-источник даёт кандидата с provenance (§7-§8)."""
    _wstore, whims_yaml, whim_id = _seed_whim(tmp_path, "proj-1")

    cands = discover_candidates("proj-1", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml))
    assert cands, "real whim source must produce ≥1 candidate"
    c = cands[0***REMOVED***
    assert c.source == "whim"
    assert c.project_id == "proj-1"
    assert c.provenance["source_id"***REMOVED*** == whim_id
    assert c.provenance["stub"***REMOVED*** is False
    assert c.provenance["confidence"***REMOVED*** >= 0.5
    assert c.provenance["evidence"***REMOVED***  # тело whim как evidence


def test_1b_no_stub_when_sources_empty(tmp_path: Path):
    """§8: пустые источники → НЕ «Stub signal», а честный пустой список."""
    cands = discover_candidates(
        "proj-empty",
        max_results=5,
        source_paths={
            "whims": tmp_path / "missing_whims.yaml",
            "pulse": tmp_path / "missing_pulse.db",
            "events": tmp_path / "missing_events.db",
            "memory": tmp_path / "missing_memory.db",
        ***REMOVED***,
    )
    assert cands == [***REMOVED***
    titles = [c.title for c in cands***REMOVED***
    assert not any("Stub" in t for t in titles)


# ═════════════════════════════════════════════════════════════════════════
# TEST 2 — candidate → opportunity (store roundtrip)
# ═════════════════════════════════════════════════════════════════════════

def test_2_candidate_to_opportunity_store(tmp_path: Path):
    """Кандидат из discover — это Opportunity; upsert в store переживает roundtrip."""
    _wstore, whims_yaml, _ = _seed_whim(tmp_path, "proj-2")
    cands = discover_candidates("proj-2", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml))
    assert cands

    store = OpportunityStore(tmp_path / "opps.yaml")
    store.upsert(cands[0***REMOVED***)
    loaded = store.get(cands[0***REMOVED***.id)
    assert loaded is not None
    assert loaded.source == "whim"
    assert loaded.provenance.get("source_id") == cands[0***REMOVED***.provenance["source_id"***REMOVED***


# ═════════════════════════════════════════════════════════════════════════
# TEST 3 — opportunity → scenario (propose via ScenarioRegistry adapter)
# ═════════════════════════════════════════════════════════════════════════

def test_3_opportunity_to_scenario(monkeypatch: pytest.MonkeyPatch):
    """PROPOSE: ScenarioRegistry.propose_roles → opp.scenario заполняется."""
    class _FakeRole:
        role_id = "novella_struct"
        title = "Novella Struct"

    class _FakeScenario:
        scenario_id = "blueprint_v3"

    class _FakeRegistry:
        def propose_roles(self, text: str, top_n: int = 3) -> List[tuple[Any, Any, float***REMOVED******REMOVED***:
            return [(_FakeScenario(), _FakeRole(), 0.9)***REMOVED***

    fake_module = types.ModuleType("core_02.scenario_registry")
    fake_module.ScenarioRegistry = _FakeRegistry
    monkeypatch.setitem(sys.modules, "core_02.scenario_registry", fake_module)

    opp = _make_opp()
    opp = propose(opp)
    assert opp.scenario is not None
    assert opp.scenario["scenario_id"***REMOVED*** == "blueprint_v3"
    assert opp.scenario["role_id"***REMOVED*** == "novella_struct"
    # Phase 8 (promt 91): propose() делегирует в ScenarioIntelligence.select() →
    # composite score (relevance·0.35 + capability·0.25 + history·0.20 + feasibility·0.20).
    # Fake scenario без capabilities → capability=neutral 0.5, history=neutral 0.5,
    # feasibility=1.0: 0.9·0.35 + 0.5·0.25 + 0.5·0.20 + 1.0·0.20 = 0.74.
    assert opp.scenario["score"***REMOVED*** == pytest.approx(0.74)


# ═════════════════════════════════════════════════════════════════════════
# TEST 4+5 — scenario → execution → artifact
# ═════════════════════════════════════════════════════════════════════════

def test_4_5_scenario_to_execution_to_artifact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """EXECUTE через ForgeFacade (мок) → COMPLETED + artifacts непустой."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"***REMOVED***, {"role_id": "r2"***REMOVED******REMOVED***
    # memory_store инъектируется: ACCUMULATE не должен писать в реальную БД
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem45.db"))
    assert calls == ["run_chain"***REMOVED***
    assert opp.status == "COMPLETED"
    assert opp.artifacts, "TEST 5: execution → artifact"
    assert opp.artifacts[0***REMOVED***["raw"***REMOVED***["overall"***REMOVED*** == "ok"


# ═════════════════════════════════════════════════════════════════════════
# TEST 6+7 — artifact → memory → learning (ACCUMULATE)
# ═════════════════════════════════════════════════════════════════════════

def test_6_7_artifact_to_memory_to_learning(tmp_path: Path):
    """ACCUMULATE: KO kind=candidate в MemoryStore + learning event + feedback confidence."""
    from core_02.learning_loop import LearningLoop
    from core_02.memory_store import MemoryStore

    mem = MemoryStore(tmp_path / "mem.db")
    opp = _make_opp()
    opp.artifacts = [{"raw": {"overall": "ok", "stage_count": 2***REMOVED******REMOVED******REMOVED***
    # Lifecycle: ACTIVE → READY → COMPLETED (state machine)
    opp = advance(opp, "READY", reason="execution started")
    opp = advance(opp, "COMPLETED", reason="forge chain finished")

    loop = LearningLoop(mem)
    result = accumulate(opp, memory_store=mem, learning_loop=loop)

    assert result["accumulated"***REMOVED*** is True
    assert result["knowledge_id"***REMOVED***
    assert result["learning_event_id"***REMOVED***
    assert result["outcome"***REMOVED*** == "success"

    # KO kind=candidate с тегом opportunity (CAN-16: существующий kind)
    kos = mem.query_by_type("candidate", limit=10)
    assert any(k["id"***REMOVED*** == result["knowledge_id"***REMOVED*** for k in kos)
    ko = mem.get_knowledge(result["knowledge_id"***REMOVED***)
    assert ko is not None
    tags = ko.get("tags") or [***REMOVED***
    assert "opportunity" in tags, f"KO tags missing 'opportunity': {tags***REMOVED***"
    assert opp.provenance.get("memory_knowledge_id") == result["knowledge_id"***REMOVED***

    # learning event зафиксирован
    events = mem.list_learning_events(limit=10)
    assert any(e["id"***REMOVED*** == result["learning_event_id"***REMOVED*** for e in events)
    # feedback → confidence пересчитан (success/(success+failure))
    assert result["confidence"***REMOVED*** is not None
    assert result["confidence"***REMOVED*** > 0


# ═════════════════════════════════════════════════════════════════════════
# TEST 8 — same source repeated → no uncontrolled duplicate
# ═════════════════════════════════════════════════════════════════════════

def test_8_repeated_source_no_duplicate(tmp_path: Path):
    """§18: повторный discover того же сигнала не плодит дубли."""
    _wstore, whims_yaml, _ = _seed_whim(tmp_path, "proj-8")
    store = OpportunityStore(tmp_path / "opps.yaml")

    first = discover_candidates("proj-8", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), store=store)
    for c in first:
        store.upsert(c)
    assert store.count() == len(first) > 0

    second = discover_candidates("proj-8", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), store=store)
    assert second == [***REMOVED***, "повторный discover не должен создавать uncontrolled duplicates"


# ═════════════════════════════════════════════════════════════════════════
# TEST 9 — DEFERRED opportunity remains recoverable
# ═════════════════════════════════════════════════════════════════════════

def test_9_deferred_remains_recoverable():
    """§13: DEFERRED ≠ DELETED — REACTIVATED возвращает к ACTIVE с сохранением аудит-следа."""
    opp = _make_opp()
    opp = advance(opp, "DEFERRED", reason="не сейчас")
    assert opp.status == "DEFERRED"
    assert opp.deferred_at
    opp = advance(opp, "REACTIVATED")
    assert opp.status == "ACTIVE"
    assert opp.reactivated_at
    assert opp.previous_status == "DEFERRED"
    assert opp.deferred_reason == "не сейчас"  # аудит-след сохранён


# ═════════════════════════════════════════════════════════════════════════
# TEST 10 — failure does not become false COMPLETED
# ═════════════════════════════════════════════════════════════════════════

def test_10_failure_not_false_completed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """§17: run_chain raise → FAILED (не COMPLETED); ACCUMULATE фиксирует failure."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, RuntimeError("forge boom"))
    mem = MemoryStore(tmp_path / "mem_fail.db")
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"***REMOVED******REMOVED***
    opp = execute(opp, dry_run=False, memory_store=mem)

    assert calls == ["run_chain"***REMOVED***
    assert opp.status == "FAILED", "ошибка не должна маскироваться как COMPLETED"
    assert opp.failed_at
    assert "forge boom" in (opp.failure_reason or "")
    # ACCUMULATE отработал с outcome=failure (Learning получает результат)
    acc = opp.provenance.get("accumulate") or {***REMOVED***
    assert acc.get("outcome") == "failure"
    events = mem.list_learning_events(limit=10)
    assert any(e["outcome"***REMOVED*** == "failure" for e in events)


# ═════════════════════════════════════════════════════════════════════════
# TEST 10b/10c — retry-пути (FAILED → повторный execute) — регрессия раунда 4
# (баг FAILED→FAILED InvalidTransition закрыт нормализацией (ACTIVE|FAILED)→READY)
# ═════════════════════════════════════════════════════════════════════════

def test_10b_failed_retry_success_completes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """FAILED-opportunity при retry: execute success → COMPLETED (FAILED→READY→COMPLETED)."""
    from core_02.memory_store import MemoryStore

    # Первый запуск — сбой
    calls = _mock_forge_facade(monkeypatch, RuntimeError("first boom"))
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"***REMOVED******REMOVED***
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem10b.db"))
    assert calls == ["run_chain"***REMOVED***  # симметрия с test_10c (reviewer nit)
    assert opp.status == "FAILED"

    # Retry: run_chain теперь успешен (новый фейк возвращает результат)
    calls2 = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp2 = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem10b2.db"))
    assert calls2 == ["run_chain"***REMOVED***
    assert opp2.status == "COMPLETED"
    assert opp2.artifacts
    assert opp2.previous_status == "READY"  # нормализация ACTIVE/FAILED→READY перед COMPLETED


def test_10c_failed_retry_failure_stays_failed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """FAILED-opportunity при retry: повторный сбой → остаётся FAILED (не InvalidTransition)."""
    from core_02.memory_store import MemoryStore

    calls = _mock_forge_facade(monkeypatch, RuntimeError("boom again"))
    opp = _make_opp()
    opp.roles = [{"role_id": "r1"***REMOVED******REMOVED***
    opp = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem10c.db"))
    assert opp.status == "FAILED"

    # Retry: снова сбой — раньше бросало InvalidTransition (FAILED→FAILED);
    # теперь нормализация (ACTIVE|FAILED)→READY, затем READY→FAILED (валидно).
    opp2 = execute(opp, dry_run=False, memory_store=MemoryStore(tmp_path / "mem10c2.db"))
    assert calls == ["run_chain", "run_chain"***REMOVED***
    assert opp2.status == "FAILED"
    assert "boom again" in (opp2.failure_reason or "")
    acc = opp2.provenance.get("accumulate") or {***REMOVED***
    assert acc.get("outcome") == "failure"


# ═════════════════════════════════════════════════════════════════════════
# E2E — вертикальный срез (§20): реальный позвоночник
# ═════════════════════════════════════════════════════════════════════════

def test_e2e_vertical_slice(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Полный путь: Whim → DISCOVER → OPPORTUNITY → SCENARIO → EXECUTION → ARTIFACT → MEMORY → LEARNING.

    Mock'атся только внешние тяжёлые ресурсы (ScenarioRegistry, ForgeFacade);
    WhimStore/OpportunityStore/MemoryStore/LearningLoop — реальные, на tmp-путях.
    """
    from core_02.learning_loop import LearningLoop
    from core_02.memory_store import MemoryStore

    # 1. OBSERVATION: реальный whim (whim_capture)
    _wstore, whims_yaml, whim_id = _seed_whim(tmp_path, "proj-e2e", body="Создать книгу по Workspace OS")

    # 2-3. DISCOVER: реальный источник → кандидат → opportunity в store
    opp_store = OpportunityStore(tmp_path / "opps.yaml")
    cands = discover_candidates("proj-e2e", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), store=opp_store)
    assert cands
    opp = cands[0***REMOVED***
    opp_store.upsert(opp)

    # 4. SCENARIO: propose (мок ScenarioRegistry — внешний тяжёлый ресурс)
    class _FakeRole:
        role_id = "novella_struct"
        title = "Novella Struct"

    class _FakeScenario:
        scenario_id = "blueprint_v3"

    class _FakeRegistry:
        def propose_roles(self, text: str, top_n: int = 3) -> List[tuple[Any, Any, float***REMOVED******REMOVED***:
            return [(_FakeScenario(), _FakeRole(), 0.9)***REMOVED***

    fake_scn = types.ModuleType("core_02.scenario_registry")
    fake_scn.ScenarioRegistry = _FakeRegistry
    monkeypatch.setitem(sys.modules, "core_02.scenario_registry", fake_scn)

    opp = propose(opp)
    assert opp.scenario and opp.scenario["scenario_id"***REMOVED*** == "blueprint_v3"
    opp_store.upsert(opp)

    # 5-6. EXECUTION: ForgeFacade (мок) → artifact.
    # memory_store инъектируется СРАЗУ в execute() — ACCUMULATE пишет в tmp-БД,
    # реальная data_13/context.db не затрагивается.
    mem = MemoryStore(tmp_path / "mem_e2e.db")
    _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp = execute(opp, dry_run=False, memory_store=mem)
    assert opp.status == "COMPLETED"
    assert opp.artifacts
    opp_store.upsert(opp)

    # 7. ACCUMULATE вызван из execute() → Memory + Learning на tmp-сторе
    acc = opp.provenance.get("accumulate") or {***REMOVED***
    assert acc.get("accumulated") is True, f"accumulate missing: {opp.provenance***REMOVED***"
    assert acc["outcome"***REMOVED*** == "success"
    assert acc.get("knowledge_id")
    assert opp.provenance.get("memory_knowledge_id") == acc["knowledge_id"***REMOVED***
    kos = mem.query_by_type("candidate", limit=10)
    assert any(k["id"***REMOVED*** == acc["knowledge_id"***REMOVED*** for k in kos)
    events = mem.list_learning_events(limit=10)
    assert any(e["id"***REMOVED*** == acc.get("learning_event_id") for e in events)
    assert acc.get("confidence") is not None and acc["confidence"***REMOVED*** > 0

    # 8. IDEMPOTENCY: повторный discover не создаёт дублей
    again = discover_candidates("proj-e2e", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), store=opp_store)
    assert again == [***REMOVED***
