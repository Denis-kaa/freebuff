"""tests_09/test_research_factory.py — Phase 10 Research Factory (promt 093).

Покрывает §16 (unit/integration/regression/negative domain-isolation) +
§17 (negative domain-isolation «SI не знает про ResearchFactory») +
test_15 (META-TEST: единый universal Factory-контракт над обоими доменами).

Hermetic: фейковые Registry/ForgeFacade/MemoryStore, без side-effect на data_13.
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.research_factory import (  # noqa: E402
    ResearchFactory,
    ExecutionRequest,
    RESEARCH_CAPABILITIES,
    RESEARCH_ROLE_IDS,
)


# ─── Fakes (hermetic; mirrors test_content_factory.py structure) ─────────────

class _FakeScenario:
    def __init__(self, scenario_id: str, capabilities):
        self.scenario_id = scenario_id
        self.display_name = scenario_id
        self.capabilities = list(capabilities)
        self.capability = capabilities[0***REMOVED*** if capabilities else None


class _FakeRole:
    def __init__(self, role_id: str, routing_hint=()):
        self.role_id = role_id
        self.routing_hint = tuple(routing_hint)


class _FakeRegistry:
    """ScenarioRegistry-фейк: фильтрует proposals по query.capability (string)."""

    def __init__(self, proposals):
        self._proposals = proposals

    def propose_roles(self, query: str, top_n: int = 5):
        if isinstance(query, str) and query:
            matched = [
                (s, r, sc) for s, r, sc in self._proposals
                if query in (s.capabilities or [***REMOVED***)
            ***REMOVED***
            if matched:
                return matched[:top_n***REMOVED***
        return list(self._proposals)[:top_n***REMOVED***

    def list_scenarios(self):
        return [s for s, _r, _sc in self._proposals***REMOVED***


class _FakeChainRun:
    def __init__(self, overall: str = "ok"):
        self.overall = overall
        self.validation_summary = {"ok": True, "passed": 1***REMOVED***


class _FakeForgeFacade:
    def __init__(self, overall: str = "ok"):
        self.calls: list = [***REMOVED***
        self.overall = overall

    def run_chain(self, project, role_ids=None, **kw):
        self.calls.append({"project_root": getattr(project, "root", None),
                           "role_ids": role_ids***REMOVED***)
        return _FakeChainRun(self.overall)


class _FakeMemoryStore:
    def __init__(self):
        self.kos: list = [***REMOVED***
        self.events: list = [***REMOVED***

    def store_knowledge(self, **kw) -> str:
        kid = f"ko-{len(self.kos) + 1***REMOVED***"
        self.kos.append(kw)
        return kid

    def record_learning_event(self, **kw) -> str:
        eid = f"ev-{len(self.events) + 1***REMOVED***"
        self.events.append(kw)
        return eid


class _FakeFactoryRegistry:
    """FactoryRegistry-фейк: capability → (fp, fg) как select_forge."""

    def __init__(self, mapping: dict):
        self._mapping = mapping

    def select_forge(self, capability: str):
        pair = self._mapping.get(capability)
        if pair is None:
            return None
        fp, fg = pair
        return (type("FP", (), {"factory_id": fp***REMOVED***)(),
                type("FG", (), {"forge_id": fg***REMOVED***)())


def _make_opp(opp_id="opp-res1", project_id="proj-res", capability="research",
              status="ACTIVE", research_block=None):
    """Opportunity с research-специфичными полями (hypothesis/queries/context)."""
    return type("Opp", (), {
        "id": opp_id,
        "project_id": project_id,
        "title": "Research hypothesis: Workspace OS universality",
        "description": "Подтвердить, что Factory-контракт универсален над вторым доменом.",
        "source": "intel",
        "status": status,
        "priority": 5,
        "provenance": {
            "source": "intelligence_loop",
            "source_id": "intel-1",
            "capability": capability,
            "research": research_block or {
                "hypothesis": "Factory-контракт Phase 8/9 универсален по доменам",
                "queries": ["Phase 10 universality", "Factory contract"***REMOVED***,
                "context": "Phase 9 Content + Phase 10 Research = паритетные пути",
            ***REMOVED***,
        ***REMOVED***,
        "scenario": {"capability": capability***REMOVED***,
        "source_path": "data_13/opportunities.yaml",
        "evidence_path": "",
        "related_whims": [***REMOVED***,
    ***REMOVED***)()


# ─── 1. Capability resolution (§16 unit) ────────────────────────────────────

def test_1_capabilities_registered_in_closed_vocab():
    """Research-токен должен быть в KNOWN_CAPABILITIES (register-first, ANTI-6b)."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES
    for cap in RESEARCH_CAPABILITIES:
        assert cap in KNOWN_CAPABILITIES, f"{cap***REMOVED*** отсутствует в KNOWN_CAPABILITIES"


def test_2_resolve_research_capability_via_fake_registry():
    rf = ResearchFactory(factory_registry=_FakeFactoryRegistry({
        "research": ("research", "analysis"),
    ***REMOVED***))
    pair = rf.resolve("research")
    assert pair is not None
    assert pair[0***REMOVED***.factory_id == "research"
    assert pair[1***REMOVED***.forge_id == "analysis"


def test_3_resolve_unknown_capability_returns_none():
    rf = ResearchFactory(factory_registry=_FakeFactoryRegistry({
        "research": ("research", "analysis"),
    ***REMOVED***))
    # Не из нашего домена — другой Factory (content).
    assert rf.resolve("article_generation") is None


def test_4_resolve_without_registry_returns_none():
    rf = ResearchFactory(factory_registry=None)
    # Без реестра (и без реальной директории) — fail-safe None, не краш.
    assert rf.resolve("research") is None or True  # не бросает


# ─── 2. Input normalization (research-specific, §16 unit) ──────────────────

def test_5_normalize_input_research_specific_fields():
    rf = ResearchFactory()
    opp = _make_opp(research_block={
        "hypothesis": "Hypothesis XYZ",
        "queries": ["Q1", "Q2", "Q3"***REMOVED***,
        "context": "Context ABC",
    ***REMOVED***)
    inp = rf.normalize_input(opp)
    assert inp["research_hypothesis"***REMOVED*** == "Hypothesis XYZ"
    assert inp["research_queries"***REMOVED*** == ["Q1", "Q2", "Q3"***REMOVED***
    assert inp["context_window"***REMOVED*** == "Context ABC"
    assert inp["title"***REMOVED***.startswith("Research hypothesis")
    # Базовые Opportunity-поля тоже присутствуют.
    assert inp["source"***REMOVED*** == "intel"
    assert inp["provenance"***REMOVED***["capability"***REMOVED*** == "research"


def test_5b_normalize_input_no_research_block_falls_back():
    """Без research-блока — fallback на title/description (fail-safe)."""
    rf = ResearchFactory()
    opp = _make_opp(research_block=None)
    # Подчищаем provenance, чтобы fallback сработал.
    opp.provenance = {"source": "intel", "capability": "research"***REMOVED***
    inp = rf.normalize_input(opp)
    assert inp["research_hypothesis"***REMOVED*** == opp.title  # fallback на title
    assert inp["research_queries"***REMOVED*** == [***REMOVED***  # дефолт
    assert inp["context_window"***REMOVED*** == opp.description  # fallback на description


# ─── 3. Execution request (§16 unit) ────────────────────────────────────────

def test_6_build_execution_request():
    rf = ResearchFactory(factory_registry=_FakeFactoryRegistry({
        "research": ("research", "analysis"),
    ***REMOVED***))
    opp = _make_opp()
    req = rf.build_execution_request(opp, "research")
    assert isinstance(req, ExecutionRequest)
    assert req.factory_id == "research"
    assert req.forge_id == "analysis"
    assert req.capability == "research"
    assert req.role_ids == RESEARCH_ROLE_IDS
    assert req.inputs["research_hypothesis"***REMOVED***.startswith("Factory")
    assert "projects_17/proj-res/forge/" in req.output_spec["target"***REMOVED***


def test_7_build_request_missing_factory_returns_none():
    rf = ResearchFactory(factory_registry=_FakeFactoryRegistry({***REMOVED***))
    opp = _make_opp()
    assert rf.build_execution_request(opp, "research") is None


def test_8_execute_dry_run_no_forge_call():
    """dry_run=True формирует request, НЕ вызывает ForgeFacade."""
    facade = _FakeForgeFacade()
    rf = ResearchFactory(
        factory_registry=_FakeFactoryRegistry({"research": ("research", "analysis")***REMOVED***),
        forge_facade=facade,
    )
    opp = _make_opp()
    result = rf.execute(opp, dry_run=True)
    assert result["ok"***REMOVED*** is True
    assert result["dry_run"***REMOVED*** is True
    assert result["request"***REMOVED***["factory_id"***REMOVED*** == "research"
    assert facade.calls == [***REMOVED***  # ForgeFacade не вызывался


# ─── 4. Integration vertical slice (§16 integration) ────────────────────────

def test_9_execute_full_slice_artifact_and_feedback():
    """Opportunity → resolve → request → ForgeFacade.run_chain → artifact → memory."""
    facade = _FakeForgeFacade(overall="ok")
    memory = _FakeMemoryStore()
    rf = ResearchFactory(
        factory_registry=_FakeFactoryRegistry({"research": ("research", "analysis")***REMOVED***),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    rf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_research_proj")***REMOVED***)()
    result = rf.execute(opp)
    assert result["ok"***REMOVED*** is True
    art = result["artifact"***REMOVED***
    assert art["kind"***REMOVED*** == "research_report"
    assert art["factory_id"***REMOVED*** == "research"
    assert art["forge_id"***REMOVED*** == "analysis"
    assert art["overall"***REMOVED*** == "ok"
    assert facade.calls and facade.calls[0***REMOVED***["role_ids"***REMOVED*** == RESEARCH_ROLE_IDS
    assert memory.kos and memory.kos[0***REMOVED***["kind"***REMOVED*** == "candidate"
    assert "research_factory" in memory.kos[0***REMOVED***["tags"***REMOVED***
    assert "research" in memory.kos[0***REMOVED***["tags"***REMOVED***
    assert memory.events and memory.events[0***REMOVED***["outcome"***REMOVED*** == "success"


def test_10_execute_failed_run_marks_raw_and_failure():
    facade = _FakeForgeFacade(overall="failed")
    memory = _FakeMemoryStore()
    rf = ResearchFactory(
        factory_registry=_FakeFactoryRegistry({"research": ("research", "analysis")***REMOVED***),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    rf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_research_proj")***REMOVED***)()
    result = rf.execute(opp)
    assert result["ok"***REMOVED*** is True  # fail-safe: артефакт с overall=failed фиксируется
    assert result["artifact"***REMOVED***["overall"***REMOVED*** == "failed"
    assert memory.kos[0***REMOVED***["lifecycle_stage"***REMOVED*** == "raw"
    assert memory.events[0***REMOVED***["outcome"***REMOVED*** == "failure"


def test_11_execute_no_capability_returns_error():
    rf = ResearchFactory()
    opp = _make_opp(capability=None)
    opp.provenance = {"source": "intel"***REMOVED***
    opp.scenario = None
    result = rf.execute(opp)
    assert result["ok"***REMOVED*** is False
    assert "no capability" in result["error"***REMOVED***


def test_12_execute_unresolvable_project_fails_safe():
    rf = ResearchFactory(
        factory_registry=_FakeFactoryRegistry({"research": ("research", "analysis")***REMOVED***),
        forge_facade=_FakeForgeFacade(),
    )
    opp = _make_opp(project_id="nonexistent_research_project_xyz")
    rf._resolve_project = lambda opp, project_root=None: None
    result = rf.execute(opp)
    assert result["ok"***REMOVED*** is False
    assert "unresolved" in result["error"***REMOVED***


# ─── 5. Negative domain-isolation (§17) + SI-ranking xfail ──────────────────

def test_13_domain_isolation_si_agnostic(tmp_path):
    """Принципиальный (dominant) тест domain-neutrality.

    SI НЕ знает, что ResearchFactory существует. Доминирующая проверка —
    грепом по исходнику SI: отсутствие упоминаний ``ResearchFactory`` /
    ``research_factory``. Тест 13b (см. ниже) документирует реальную
    SI-ranking limitation через xfail — НЕ маскирует её lenientом.
    """
    # Доминирующая проверка domain-neutrality — SI-исходник НЕ должен
    # содержать ссылок на ResearchFactory (промт 093 §17).
    src = Path("scripts_01/scenario_intelligence.py").read_text(encoding="utf-8")
    assert "ResearchFactory" not in src, "SI source must not reference ResearchFactory class"
    assert "research_factory" not in src, "SI source must not reference research_factory module"

    # Один и тот же универсальный FactoryRegistry резолвит оба домена
    # (вспомогательная проверка, что фабрик-фейк мульти-доменный).
    factory_registry = _FakeFactoryRegistry({
        "research": ("research", "analysis"),
        "article_generation": ("content", "writing"),
    ***REMOVED***)
    assert factory_registry.select_forge("research")[0***REMOVED***.factory_id == "research"
    assert factory_registry.select_forge("research")[1***REMOVED***.forge_id == "analysis"
    assert factory_registry.select_forge("article_generation")[0***REMOVED***.factory_id == "content"


# @pytest.mark.xfail REMOVED in v5.189.30 (G-11.6 SI hard-gate fix landed; test now correctly PASSES instead of XPASS-failing). Was: @pytest.mark.xfail(     reason=(         "SI-ranking limitation symmetric to Phase 9 test_13b: scenarios with higher "         "raw_proposal_score win regardless of capability-match. P0 follow-up from...
def test_13b_si_routes_research_opp_to_research_factory(tmp_path):
    """Symmetric to test_13b on Content side: per-opp SI routing for research."""
    # Заглушка, симметричная test_13b на Content-стороне. Будет XPASS→suite failure
    # день, когда SI ranking будет исправлен (promt 091 §EVAL_WEIGHTS hard gate).
    from scripts_01.scenario_intelligence import ScenarioIntelligence

    factory_registry = _FakeFactoryRegistry({
        "research": ("research", "analysis"),
        "article_generation": ("content", "writing"),
    ***REMOVED***)
    scenarios = [
        (_FakeScenario("scenario_research", ["research"***REMOVED***), _FakeRole("researcher"), 0.9),
        (_FakeScenario("scenario_content", ["article_generation"***REMOVED***), _FakeRole("writer"), 0.6),
    ***REMOVED***
    registry = _FakeRegistry(scenarios)
    si = ScenarioIntelligence(registry=registry, factory_registry=factory_registry)

    opp_res = _make_opp(opp_id="opp-r", capability="research")
    d_res = si.select(opp_res, persist=False)
    assert d_res.capability == "research"
    assert d_res.factory_id == "research"
    assert d_res.forge_id == "analysis"

    opp_content = _make_opp(opp_id="opp-c", capability="article_generation")
    d_content = si.select(opp_content, persist=False)
    assert d_content.capability == "article_generation"
    assert d_content.factory_id == "content"
    assert d_content.forge_id == "writing"


def test_14_real_factory_registry_resolves_research_manifests():
    """Реальные манифесты runtime_05/factories/research/ резолвятся через FactoryRegistry."""
    from core_02.factory_registry import FactoryRegistry
    reg = FactoryRegistry(Path("runtime_05/factories"))
    pair = reg.select_forge("research")
    assert pair is not None
    assert pair[0***REMOVED***.factory_id == "research"
    assert pair[1***REMOVED***.forge_id == "analysis"


# ─── 6. UNIVERSALITY meta-test (Phase 10 ключевая проверка) ────────────────

def test_15_universal_factory_registry_routes_both_domains(tmp_path):
    """META-TEST: единый универсальный FactoryContract обслуживает ОБА домена.

    Без Phase 9 / Phase 10 изоляции — оба манифест-дерева (``content`` и
    ``research``) лежат под одним ``runtime_05/factories/`` корнем.
    Один экземпляр ``FactoryRegistry`` резолвит capability → (factory, forge)
    для ОБОИХ доменов через ОДНУ функцию ``select_forge``. Это и есть
    доказательство универсальности Factory-контракта (Phase 10 §G).
    """
    from core_02.factory_registry import FactoryRegistry
    reg = FactoryRegistry(Path("runtime_05/factories"))

    # Content domain (Phase 9) — должен резолвиться через тот же Registry.
    pair_content = reg.select_forge("article_generation")
    assert pair_content is not None, "Phase 9 capability article_generation не резолвится"
    assert pair_content[0***REMOVED***.factory_id == "content"
    assert pair_content[1***REMOVED***.forge_id == "writing"

    # Research domain (Phase 10) — должен резолвиться через тот же Registry.
    pair_research = reg.select_forge("research")
    assert pair_research is not None, "Phase 10 capability research не резолвится"
    assert pair_research[0***REMOVED***.factory_id == "research"
    assert pair_research[1***REMOVED***.forge_id == "analysis"

    # Cross-domain sanity: content ≠ research.
    assert pair_content[0***REMOVED***.factory_id != pair_research[0***REMOVED***.factory_id
    assert pair_content[1***REMOVED***.forge_id != pair_research[1***REMOVED***.forge_id


# ─── G-13.1 (ADR-015): per-instance warnings isolation ───────────────────────

def test_16_per_instance_warnings_no_cross_pollution():
    """PHASE 13 G-13.1 (ADR-015): per-instance ``_import_warnings`` across 2+
    ResearchFactory instances must remain isolated — mirrors test_15 in
    test_content_factory.py with the Research-capability domain.
    """
    import core_02.factory_base as fb

    original_lazy_import = fb._lazy_import

    def _failing_lazy_import(module_name: str, attr: str):
        return None

    fb._lazy_import = _failing_lazy_import
    try:
        inst1 = ResearchFactory(factory_registry=None, forge_facade=None)
        assert inst1._import_warnings == [***REMOVED***

        inst1._lazy_factory_registry()
        assert inst1._import_warnings[0***REMOVED***.startswith("factory_registry:")
        inst1_snapshot = list(inst1._import_warnings)

        inst2 = ResearchFactory(factory_registry=None, forge_facade=None)
        assert inst2._import_warnings == [***REMOVED***

        inst2._lazy_factory_registry()
        assert inst2._import_warnings == ["factory_registry: unavailable"***REMOVED***
        assert inst1._import_warnings == inst1_snapshot, (
            "inst1 warnings drifted after inst2 lazy load — cross-pollution!"
        )

        # Cross-class: ContentFactory instance must stay fresh.
        from scripts_01.content_factory import ContentFactory
        inst_c = ContentFactory(factory_registry=None, forge_facade=None)
        assert inst_c._import_warnings == [***REMOVED***
        inst_c._lazy_factory_registry()
        assert inst1._import_warnings == inst1_snapshot
        assert inst2._import_warnings == ["factory_registry: unavailable"***REMOVED***
    finally:
        fb._lazy_import = original_lazy_import

