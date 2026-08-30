"""tests_09/test_scenario_intelligence.py — Phase 8: Universal Scenario Intelligence.

Реализация промта ``pompts_11/091_19_phase8_universal_scenario_intelligence.md`` §18 — обязательный набор тестов:

  1 candidate discovery
  2 multiple scenarios
  3 ranking
  4 selection
  5 provenance
  6 capability resolution
  7 Factory routing
  8 Forge boundary
  9 feedback
 10 EventBus
 11 persistence
 12 backward compatibility
 13 unavailable scenario
 14 deferred opportunity
 15 re-selection after new evidence

+ главный integration test: Opportunity → multiple candidates → evaluation →
  ranking → selected → capability → FactoryRegistry → ForgeFacade → Artifact
  → feedback → Memory.

Domain-neutrality (§1/§4/§20): никакого hardcoded "content". Fake-сценарии
используют нейтральные capability-токены (article_generation / api_implementation),
которые резолвятся через FactoryRegistry — код их не зашивает.
"""
from __future__ import annotations

import sys
import types
}
from typing import Any, Dict, List, Optional, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts_01"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT))

from scripts_01.scenario_intelligence import (  # noqa: E402
    CapabilityRequirement,
    DecisionHistoryStore,
    ScenarioCandidate,
    ScenarioDecision,
    ScenarioIntelligence,
    EVAL_WEIGHTS,
)
from scripts_01.opportunity_engine import Opportunity, propose  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_opp(scenario_cap: Optional[str] = None, **kwargs: Any) -> Opportunity:
    """Минимальный Opportunity (domain-neutral: любой проект)."""
    opp = Opportunity(
        id="opp-si-001",
        project_id="proj-si",
        title="Universal scenario test opportunity",
        description="Domain-neutral vertical slice",
        source="hand",
        status="ACTIVE",
    )
    if scenario_cap:
        opp.scenario = {"scenario_id": "scenario_a", "capability": scenario_cap}
    for k, v in kwargs.items():
        setattr(opp, k, v)
    return opp


class _FakeRole:
    def __init__(self, role_id: str, routing_hint: Optional[list] = None) -> None:
        self.role_id = role_id
        self.title = role_id.replace("_", " ").title()
        self.routing_hint = routing_hint or []


class _FakeScenario:
    def __init__(self, scenario_id: str, capabilities: Optional[list] = None) -> None:
        self.scenario_id = scenario_id
        self.display_name = scenario_id.replace("_", " ").title()
        self.capabilities = capabilities or []


class _FakeScenarioRegistry:
    """Fake ScenarioRegistry: propose_roles + list_scenarios (каталог)."""

    def __init__(self, proposals: Optional[List[Tuple[Any, Any, float]]] = None) -> None:
        self._proposals = proposals or []
        self._catalog = [s for (s, _r, _sc) in self._proposals]

    def propose_roles(self, text: str, top_n: int = 3) -> List[Tuple[Any, Any, float]]:
        return self._proposals[:top_n]

    def list_scenarios(self) -> List[Any]:
        return self._catalog


class _FakeFactoryPassport:
    def __init__(self, factory_id: str) -> None:
        self.factory_id = factory_id


class _FakeForgePassport:
    def __init__(self, forge_id: str) -> None:
        self.forge_id = forge_id


class _FakeFactoryRegistry:
    """Fake FactoryRegistry: capability_catalog + select_forge (+ find_by_capability)."""

    def __init__(self, catalog: Optional[Dict[str, list]] = None) -> None:
        # capability → [(factory_id, forge_id)]
        self._pairs: Dict[str, list] = catalog or {
            "article_generation": [("articles_factory", "article_forge")],
            "api_implementation": [("code_factory", "api_forge")],
        }

    def capability_catalog(self) -> Dict[str, list]:
        return {cap: [f for f, _g in pairs] for cap, pairs in self._pairs.items()}

    def select_forge(self, capability: str) -> Optional[Tuple[Any, Any]]:
        pairs = self._pairs.get(capability)
        if not pairs:
            return None
        f_id, g_id = pairs[0]
        return (_FakeFactoryPassport(f_id), _FakeForgePassport(g_id))

    def find_factories_by_capability(self, capability: str) -> list:
        return [_FakeFactoryPassport(f) for f, _g in self._pairs.get(capability, [])]


def _make_si(
    tmp_path: Path,
    *,
    proposals: Optional[List[Tuple[Any, Any, float]]] = None,
    catalog: Optional[Dict[str, list]] = None,
    memory_store: Any = None,
) -> ScenarioIntelligence:
    """ScenarioIntelligence с инъектированными фейками + tmp history store (hermetic).

    По умолчанию инъектирует ПУСТОЙ MemoryStore на tmp-пути — ни один тест не
    трогает реальный data_13/context.db (иначе _lazy_memory_store() открыл бы его
    при существующем файле; history=neutral детерминирован).
    """
    from core_02.memory_store import MemoryStore

    if memory_store is None:
        # tmp_path уникален на тест — фиксированное имя достаточно (hash() не нужен).
        memory_store = MemoryStore(tmp_path / "mem_si.db")
    return ScenarioIntelligence(
        registry=_FakeScenarioRegistry(proposals or []),
        factory_registry=_FakeFactoryRegistry(catalog or {}),
        memory_store=memory_store,
        history_store=DecisionHistoryStore(tmp_path / "history.yaml"),
    )


def _mock_forge_facade(monkeypatch: pytest.MonkeyPatch, result: Any) -> List[str]:
    """Подмена core_02.forge_facade на фейк с run_chain (как в test_intelligence_loop_phase5)."""
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
    fake_module.ForgeFacade = _FakeForgeFacade
    monkeypatch.setitem(sys.modules, "core_02.forge_facade", fake_module)
    return calls


class _FakeChainRun:
    def __init__(self, overall: str = "ok") -> None:
        self.overall = overall
        self.stage_count = 2

    def to_dict(self) -> Dict[str, Any]:
        return {"overall": self.overall, "stage_count": self.stage_count}


# ═════════════════════════════════════════════════════════════════════════
# 1 — candidate discovery
# ═════════════════════════════════════════════════════════════════════════

def test_1_candidate_discovery(tmp_path: Path):
    """§18 #1: ScenarioRegistry (каталог) → кандидаты; НЕ второй registry."""
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer", ["article_generation"]), 0.9),
        ],
    )
    opp = _make_opp()
    cands = si.discover(opp, top_n=5)
    assert len(cands) == 1
    assert cands[0].scenario_id == "scenario_a"
    assert cands[0].capability == "article_generation"  # из scenario.capabilities[0]
    assert cands[0].score == pytest.approx(0.9)  # raw fuzzy match


# ═════════════════════════════════════════════════════════════════════════
# 2 — multiple scenarios (one opportunity → many candidates)
# ═════════════════════════════════════════════════════════════════════════

def test_2_multiple_scenarios(tmp_path: Path):
    """§18 #2: одна Opportunity → несколько кандидатов (любой домен)."""
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
            (_FakeScenario("scenario_b", ["api_implementation"]), _FakeRole("engineer"), 0.7),
            (_FakeScenario("scenario_c", []), _FakeRole("designer"), 0.5),
        ],
    )
    cands = si.discover(_make_opp(), top_n=5)
    assert len(cands) == 3
    assert {c.scenario_id for c in cands} == {"scenario_a", "scenario_b", "scenario_c"}


# ═════════════════════════════════════════════════════════════════════════
# 3 — ranking
# ═════════════════════════════════════════════════════════════════════════

def test_3_ranking(tmp_path: Path):
    """§18 #3: rank() сортирует по composite score (desc), tie-break стабилен."""
    si = _make_si(tmp_path, proposals=[])
    opp = _make_opp()
    cands = [
        ScenarioCandidate(scenario_id="low", display_name="Low", score=0.4),
        ScenarioCandidate(scenario_id="high", display_name="High", score=0.9),
        ScenarioCandidate(scenario_id="mid", display_name="Mid", score=0.7),
    ]
    ranked = si.rank(cands)
    assert [c.scenario_id for c in ranked] == ["high", "mid", "low"]


# ═════════════════════════════════════════════════════════════════════════
# 4 — selection (best candidate wins)
# ═════════════════════════════════════════════════════════════════════════

def test_4_selection(tmp_path: Path):
    """§18 #4: select() = discover → evaluate → rank → best."""
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
            (_FakeScenario("scenario_b", ["api_implementation"]), _FakeRole("engineer"), 0.7),
        ],
        # Герметичность: _make_si уже инъектирует пустой MemoryStore (history=neutral).
    )
    opp = _make_opp()
    decision = si.select(opp, top_n=5, persist=True)
    assert decision.selected_scenario_id == "scenario_a"
    assert decision.status == "selected"
    assert decision.score is not None and 0.0 <= decision.score <= 1.0
    # composite score = 0.9·0.35 + 1.0·0.25 + 0.5·0.20 + 1.0·0.20 (capability available)
    assert decision.score == pytest.approx(0.315 + 0.25 + 0.10 + 0.20)


# ═════════════════════════════════════════════════════════════════════════
# 5 — provenance (explainable decision)
# ═════════════════════════════════════════════════════════════════════════

def test_5_provenance(tmp_path: Path):
    """§18 #5: решение объяснимо — reasons + evidence + capability + factory/forge."""
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    decision = si.select(_make_opp(), top_n=5, persist=True)
    assert decision.reasons, "reasons must be non-empty (explainable)"
    assert any("relevance" in r for r in decision.reasons)
    assert any("capability" in r for r in decision.reasons)
    assert decision.evidence.get("capability") == "article_generation"
    assert decision.evidence.get("all_candidates"), "evidence must list ranked candidates"
    assert decision.capability == "article_generation"
    assert decision.factory_id == "articles_factory"
    assert decision.forge_id == "article_forge"


# ═════════════════════════════════════════════════════════════════════════
# 6 — capability resolution (domain-neutral)
# ═════════════════════════════════════════════════════════════════════════

def test_6_capability_resolution(tmp_path: Path):
    """§18 #6: CapabilityRequirement → FactoryRegistry.select_forge → (factory, forge)."""
    si = _make_si(tmp_path)
    req = CapabilityRequirement(
        capability="api_implementation",
        scenario_id="scenario_b",
        role_id="engineer",
    )
    factory_id, forge_id = si.resolve_capability(req)
    assert factory_id == "code_factory"
    assert forge_id == "api_forge"


# ═════════════════════════════════════════════════════════════════════════
# 7 — Factory routing (decision carries factory/forge)
# ═════════════════════════════════════════════════════════════════════════

def test_7_factory_routing(tmp_path: Path):
    """§18 #7: выбранный сценарий → capability → factory/forge в decision."""
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    decision = si.select(_make_opp(), top_n=5, persist=True)
    assert decision.capability == "article_generation"
    assert decision.factory_id == "articles_factory"
    assert decision.forge_id == "article_forge"


# ═════════════════════════════════════════════════════════════════════════
# 8 — Forge boundary (ScenarioIntelligence does NOT call ForgeFacade)
# ═════════════════════════════════════════════════════════════════════════

def test_8_forge_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """§18 #8: select()/resolve_capability() не импортируют ForgeFacade (нет run_chain)."""
    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    decision = si.select(_make_opp(), top_n=5, persist=True)
    assert calls == [], f"ScenarioIntelligence must not call ForgeFacade: {calls}"
    assert decision.factory_id == "articles_factory"
    assert decision.forge_id == "article_forge"


# ═════════════════════════════════════════════════════════════════════════
# 9 — feedback v0 (transparent, no ML)
# ═════════════════════════════════════════════════════════════════════════

def test_9_feedback(tmp_path: Path):
    """§18 #9: feedback_v0 → MemoryStore kind=scenario_decision + learning event."""
    from core_02.memory_store import MemoryStore

    mem = MemoryStore(tmp_path / "mem_fb.db")
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
        memory_store=mem,
    )
    decision = si.select(_make_opp(), top_n=5, persist=True)
    result = si.feedback_v0(decision, "success", memory_store=mem)
    assert result["recorded"] is True
    assert result["knowledge_id"]
    assert result["learning_event_id"]
    # KO kind=candidate (существующий KNOWLEDGE_KINDS) + tag scenario_decision
    kos = mem.query_by_type("candidate", limit=10)
    assert any(k["id"] == result["knowledge_id"] for k in kos)
    ko = mem.get_knowledge(result["knowledge_id"])
    assert ko is not None
    assert "scenario_decision" in (ko.get("tags") or [])
    events = mem.list_learning_events(limit=10)
    assert any(e["id"] == result["learning_event_id"] for e in events)


# ═════════════════════════════════════════════════════════════════════════
# 10 — EventBus
# ═════════════════════════════════════════════════════════════════════════

def test_10_eventbus(tmp_path: Path):
    """§18 #10: события scenario.candidates.generated / evaluated / selected публикуются."""
    from scripts_01.event_bus import EventBus

    bus = EventBus(db_path=tmp_path / "events.db")
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    si.select(_make_opp(), top_n=5, persist=True, event_bus=bus)
    events = bus.get_events(limit=50)
    types = {e.event_type for e in events}
    assert "scenario.candidates.generated" in types
    assert "scenario.evaluated" in types
    assert "scenario.selected" in types


# ═════════════════════════════════════════════════════════════════════════
# 11 — persistence (DecisionHistoryStore, no new DB)
# ═════════════════════════════════════════════════════════════════════════

def test_11_persistence(tmp_path: Path):
    """§18 #11: decision history персистится в YAML (НЕ новая БД) и переживает roundtrip."""
    history_path = tmp_path / "history.yaml"
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    # Переопределяем history store на явный tmp-путь (после создания si)
    si._history_store = DecisionHistoryStore(history_path)
    decision = si.select(_make_opp(), top_n=5, persist=True)
    assert history_path.exists()
    # Новый store читает тот же файл
    store2 = DecisionHistoryStore(history_path)
    recs = store2.by_opportunity(decision.opportunity_id)
    assert len(recs) == 1
    assert recs[0]["selected_scenario_id"] == "scenario_a"


# ═════════════════════════════════════════════════════════════════════════
# 12 — backward compatibility (propose falls back when SI unavailable)
# ═════════════════════════════════════════════════════════════════════════

def test_12_backward_compat_legacy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """§18 #12: propose() падает на legacy ScenarioRegistry, если SI недоступен."""
    # Убираем модуль scenario_intelligence из sys.modules + блокируем импорт
    saved = sys.modules.pop("scripts_01.scenario_intelligence", None)
    real_import = __import__

    def _blocked(name, *args, **kwargs):
        # Блокируем и полное имя, и bare-name fallback (_lazy_)tries
        # top-level "scenario_intelligence", который иначе пере-импортируется
        # из scripts_01/ в sys.path).
        if name in ("scripts_01.scenario_intelligence", "scenario_intelligence"):
            raise ImportError("blocked for BC test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocked)

    class _FakeRole:
        role_id = "novella_struct"
        title = "Novella Struct"

    class _FakeScenario:
        scenario_id = "blueprint_v3"

    class _FakeRegistry:
        def propose_roles(self, text: str, top_n: int = 3) -> List[Tuple[Any, Any, float]]:
            return [(_FakeScenario(), _FakeRole(), 0.9)]

    fake_module = types.ModuleType("core_02.scenario_registry")
    fake_module.ScenarioRegistry = _FakeRegistry
    monkeypatch.setitem(sys.modules, "core_02.scenario_registry", fake_module)

    try:
        opp = _make_opp()
        opp = propose(opp)
        assert opp.scenario is not None
        assert opp.scenario["scenario_id"] == "blueprint_v3"
        assert opp.scenario["score"] == 0.9  # legacy raw score
    finally:
        if saved is not None:
            sys.modules["scripts_01.scenario_intelligence"] = saved


def test_12b_backward_compat_si_unavailable_decision(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """§18 #12: SI доступен, но вернул 'unavailable' → legacy fallback (BC)."""
    # SI возвращает decision с selected_scenario_id=None (no candidates)
    class _UnavailableSI:
        def select(self, *args: Any, **kwargs: Any) -> ScenarioDecision:
            return ScenarioDecision(
                opportunity_id="opp-si-001",
                project_id="proj-si",
                selected_scenario_id=None,
                status="unavailable",
            )

    fake_module = types.ModuleType("scripts_01.scenario_intelligence")
    fake_module.ScenarioIntelligence = _UnavailableSI
    monkeypatch.setitem(sys.modules, "scripts_01.scenario_intelligence", fake_module)

    class _FakeRole:
        role_id = "novella_struct"
        title = "Novella Struct"

    class _FakeScenario:
        scenario_id = "blueprint_v3"

    class _FakeRegistry:
        def propose_roles(self, text: str, top_n: int = 3) -> List[Tuple[Any, Any, float]]:
            return [(_FakeScenario(), _FakeRole(), 0.9)]

    fake_reg = types.ModuleType("core_02.scenario_registry")
    fake_reg.ScenarioRegistry = _FakeRegistry
    monkeypatch.setitem(sys.modules, "core_02.scenario_registry", fake_reg)

    opp = _make_opp()
    opp = propose(opp)
    assert opp.scenario is not None
    assert opp.scenario["scenario_id"] == "blueprint_v3"  # legacy path сработал


# ═════════════════════════════════════════════════════════════════════════
# 13 — unavailable scenario
# ═════════════════════════════════════════════════════════════════════════

def test_13_unavailable_scenario(tmp_path: Path):
    """§18 #13: нет кандидатов → decision status='unavailable' (не краш)."""
    si = _make_si(tmp_path, proposals=[])
    decision = si.select(_make_opp(), top_n=5, persist=True)
    assert decision.selected_scenario_id is None
    assert decision.status == "unavailable"
    assert decision.reasons


def test_13b_unavailable_infeasible(tmp_path: Path):
    """§18 #13: все кандидаты infeasible (capability не в FactoryRegistry) → unavailable."""
    si = _make_si(
        tmp_path,
        proposals=[
            # capability "image_generation" НЕ в каталоге фейка → cap_avail=0 → feas=0.3 → infeasible
            (_FakeScenario("scenario_x", ["image_generation"]), _FakeRole("artist"), 0.9),
        ],
    )
    decision = si.select(_make_opp(), top_n=5, persist=True, available_only=True)
    assert decision.selected_scenario_id is None
    assert decision.status == "unavailable"


# ═════════════════════════════════════════════════════════════════════════
# 14 — deferred opportunity (lifecycle preserved)
# ═════════════════════════════════════════════════════════════════════════

def test_14_deferred_opportunity(tmp_path: Path):
    """§18 #14: DEFERRED opportunity остаётся recoverable; select() не трогает статус."""
    from scripts_01.opportunity_engine import advance

    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
        ],
    )
    opp = _make_opp()
    opp = advance(opp, "DEFERRED", reason="не сейчас")
    assert opp.status == "DEFERRED"
    # select() — read-only по lifecycle: не меняет статус Opportunity
    decision = si.select(opp, top_n=5, persist=True)
    assert decision.selected_scenario_id == "scenario_a"
    assert opp.status == "DEFERRED"  # Scenario Intelligence не трогает lifecycle
    # recoverable: REACTIVATED → ACTIVE (существующая семантика Phase 5)
    opp = advance(opp, "REACTIVATED")
    assert opp.status == "ACTIVE"


# ═════════════════════════════════════════════════════════════════════════
# 15 — re-selection after new evidence
# ═════════════════════════════════════════════════════════════════════════

def test_15_reselection_after_new_evidence(tmp_path: Path):
    """§18 #15: новый evidence → другой сценарий → superseded; повторный → reselected."""
    history_path = tmp_path / "history.yaml"
    si = _make_si(tmp_path, proposals=[])
    si._history_store = DecisionHistoryStore(history_path)

    # Первый выбор: scenario_a (0.9)
    si._registry = _FakeScenarioRegistry([
        (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
    ])
    d1 = si.select(_make_opp(), top_n=5, persist=True)
    assert d1.selected_scenario_id == "scenario_a"
    assert d1.status == "selected"

    # Новый evidence: scenario_b теперь сильнее (1.0) → superseded
    si._registry = _FakeScenarioRegistry([
        (_FakeScenario("scenario_b", ["api_implementation"]), _FakeRole("engineer"), 1.0),
        (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
    ])
    d2 = si.select(_make_opp(), top_n=5, persist=True)
    assert d2.selected_scenario_id == "scenario_b"
    assert d2.status == "superseded"

    # Повторный выбор scenario_b (prev status=superseded) → reselected
    d3 = si.select(_make_opp(), top_n=5, persist=True)
    assert d3.selected_scenario_id == "scenario_b"
    assert d3.status == "reselected"


# ═════════════════════════════════════════════════════════════════════════
# MAIN INTEGRATION TEST — Opportunity → candidates → eval → rank → select →
# capability → FactoryRegistry → ForgeFacade → Artifact → feedback → Memory
# ═════════════════════════════════════════════════════════════════════════

def test_main_integration_vertical_slice(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """§18 главный integration test: полный домен-нейтральный путь Phase 8."""
    from core_02.memory_store import MemoryStore

    # 1. Opportunity (domain-neutral)
    opp = _make_opp()

    # 2-4. Scenario Intelligence: discover → evaluate → rank → select
    si = _make_si(
        tmp_path,
        proposals=[
            (_FakeScenario("scenario_a", ["article_generation"]), _FakeRole("writer"), 0.9),
            (_FakeScenario("scenario_b", ["api_implementation"]), _FakeRole("engineer"), 0.7),
            (_FakeScenario("scenario_c", []), _FakeRole("designer"), 0.5),
        ],
        memory_store=MemoryStore(tmp_path / "mem_int.db"),
    )
    decision = si.select(opp, top_n=5, persist=True)
    assert decision.selected_scenario_id == "scenario_a"  # best composite
    assert decision.capability == "article_generation"
    assert decision.factory_id == "articles_factory"
    assert decision.forge_id == "article_forge"
    assert decision.status == "selected"
    assert decision.reasons and decision.evidence

    # 5. propose() интеграция: opp.scenario + provenance['scenario_decision']
    # (через SI — здесь проверяем прямое делегирование в opportunity_engine)
    from scripts_01.opportunity_engine import propose as _propose

    # Мокаем SI-модуль, чтобы propose() использовал НАШ decision (hermetic)
    class _StubSI:
        def select(self, *args: Any, **kwargs: Any) -> ScenarioDecision:
            return decision

    fake_si_mod = types.ModuleType("scripts_01.scenario_intelligence")
    fake_si_mod.ScenarioIntelligence = _StubSI
    monkeypatch.setitem(sys.modules, "scripts_01.scenario_intelligence", fake_si_mod)

    opp2 = _make_opp()
    opp2 = _propose(opp2)
    assert opp2.scenario is not None
    assert opp2.scenario["scenario_id"] == "scenario_a"
    assert opp2.scenario["capability"] == "article_generation"
    assert opp2.provenance.get("scenario_decision", {}).get("selected_scenario_id") == "scenario_a"

    # 6-7. EXECUTION: ForgeFacade (мок) → artifact
    calls = _mock_forge_facade(monkeypatch, _FakeChainRun(overall="ok"))
    opp2.roles = [{"role_id": "r1"}, {"role_id": "r2"}]
    from scripts_01.opportunity_engine import execute

    mem = MemoryStore(tmp_path / "mem_int2.db")
    opp2 = execute(opp2, dry_run=False, memory_store=mem)
    assert calls == ["run_chain"]
    assert opp2.status == "COMPLETED"
    assert opp2.artifacts

    # 8. FEEDBACK v0 → Memory (kind=candidate, tag=scenario_decision)
    si2 = _make_si(tmp_path, proposals=[], memory_store=mem)
    fb = si2.feedback_v0(decision, "success", memory_store=mem)
    assert fb["recorded"] is True
    kos = mem.query_by_type("candidate", limit=10)
    assert any(k["id"] == fb["knowledge_id"] for k in kos)

    # 9. History persisted (no new DB — YAML store)
    assert (tmp_path / "history.yaml").exists()
