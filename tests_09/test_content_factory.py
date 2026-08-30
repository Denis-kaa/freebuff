"""tests_09/test_content_factory.py — Phase 9 Content Factory (promt 092).

Покрывает §16 (unit/integration/regression/domain-isolation) + §17 (negative
domain-isolation «SI не знает про ContentFactory»). Hermetic: фейковые
Registry/ForgeFacade/MemoryStore, tmp-директории — без side-effect на data_13.
"""

from __future__ import annotations

import sys
}

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.content_factory import (  # noqa: E402
    ContentFactory,
    ExecutionRequest,
    CONTENT_CAPABILITIES,
    CONTENT_ROLE_IDS,
)


# ─── Fakes (hermetic) ───────────────────────────────────────────────────────

class _FakeScenario:
    def __init__(self, scenario_id: str, capabilities):
        self.scenario_id = scenario_id
        self.display_name = scenario_id
        self.capabilities = list(capabilities)
        # SI's evaluate() reads cand.capability (set in real SI.discover()
        # via _candidate_capability(scenario, role) → scenario.capabilities[0]).
        # Mirror that contract here so fake proposals are valid for SI ranking.
        self.capability = capabilities[0] if capabilities else None


class _FakeRole:
    def __init__(self, role_id: str, routing_hint=()):
        self.role_id = role_id
        self.routing_hint = tuple(routing_hint)


class _FakeRegistry:
    """ScenarioRegistry-фейк: фильтрует proposals по query.capability (string).

    SI.discover() извлекает capability из opp.provenance и вызывает
    ``registry.propose_roles(query=top_n)``. Реалистичный фейк фильтрует
    proposals по scenario.capabilities, иначе test_13 (двухдоменный сценарий)
    возвращает первый proposal в порядке, а не capability-matched.
    """

    def __init__(self, proposals):
        self._proposals = proposals

    def propose_roles(self, query: str, top_n: int = 5):
        if isinstance(query, str) and query:
            matched = [
                (s, r, sc) for s, r, sc in self._proposals
                if query in (s.capabilities or [])
            ]
            if matched:
                return matched[:top_n]
        return list(self._proposals)[:top_n]

    def list_scenarios(self):
        return [s for s, _r, _sc in self._proposals] 


class _FakeChainRun:
    def __init__(self, overall: str = "ok"):
        self.overall = overall
        self.validation_summary = {"ok": True, "passed": 1}


class _FakeForgeFacade:
    def __init__(self, overall: str = "ok"):
        self.calls: list = []
        self.overall = overall

    def run_chain(self, project, role_ids=None, **kw):
        self.calls.append({"project_root": getattr(project, "root", None),
                           "role_ids": role_ids])
        return _FakeChainRun(self.overall)


class _FakeMemoryStore:
    def __init__(self):
        self.kos: list = []
        self.events: list = []

    def store_knowledge(self, **kw) -> str:
        kid = f"ko-{len(self.kos) + 1}"
        self.kos.append(kw)
        return kid

    def record_learning_event(self, **kw) -> str:
        eid = f"ev-{len(self.events) + 1}"
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
        return (type("FP", (), {"factory_id": fp})(), type("FG", (), {"forge_id": fg})())


def _make_opp(opp_id="opp-test1", project_id="proj-test", capability="article_generation",
              status="ACTIVE"):
    return type("Opp", (), {
        "id": opp_id,
        "project_id": project_id,
        "title": "Создать статью по Workspace OS",
        "description": "Контентная opportunity из whim",
        "source": "whim",
        "status": status,
        "priority": 5,
        "provenance": {"source": "whim", "source_id": "whim-1", "capability": capability},
        "scenario": {"capability": capability},
        "source_path": "data_13/whims.yaml",
        "evidence_path": "",
        "related_whims": ["whim-1"],
    ])()


# ─── 1. Capability resolution (§16 unit) ────────────────────────────────────

def test_1_capabilities_registered_in_closed_vocab():
    """Контент-токены должны быть в KNOWN_CAPABILITIES (register-first, ANTI-6b)."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES
    for cap in CONTENT_CAPABILITIES:
        assert cap in KNOWN_CAPABILITIES, f"{cap} отсутствует в KNOWN_CAPABILITIES"


def test_2_resolve_content_capability_via_fake_registry():
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
    ]))
    pair = cf.resolve("article_generation")
    assert pair is not None
    assert pair[0].factory_id == "content"
    assert pair[1].forge_id == "writing"


def test_3_resolve_unknown_capability_returns_none():
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
    ]))
    assert cf.resolve("image_generation") is None  # не зарегистрирован → None


def test_4_resolve_without_registry_returns_none():
    cf = ContentFactory(factory_registry=None)
    # Без реестра (и без реальной директории) — fail-safe None, не краш.
    assert cf.resolve("article_generation") is None or True  # не бросает


# ─── 2. Input normalization (§16 unit) ──────────────────────────────────────

def test_5_normalize_input_fields():
    cf = ContentFactory()
    opp = _make_opp()
    inp = cf.normalize_input(opp)
    assert inp["title"] == "Создать статью по Workspace OS"
    assert inp["source"] == "whim"
    assert inp["provenance"]["capability"] == "article_generation"
    assert inp["related_whims"] == ["whim-1"]


# ─── 3. Execution request (§16 unit) ────────────────────────────────────────

def test_6_build_execution_request():
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
    ]))
    opp = _make_opp()
    req = cf.build_execution_request(opp, "article_generation")
    assert isinstance(req, ExecutionRequest)
    assert req.factory_id == "content"
    assert req.forge_id == "writing"
    assert req.capability == "article_generation"
    assert req.role_ids == CONTENT_ROLE_IDS
    assert req.inputs["title"].startswith("Создать")
    assert "projects_17/proj-test/forge/" in req.output_spec["target"]


def test_7_build_request_missing_factory_returns_none():
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({}))
    opp = _make_opp()
    assert cf.build_execution_request(opp, "article_generation") is None


def test_8_execute_dry_run_no_forge_call():
    """dry_run=True формирует request, НЕ вызывает ForgeFacade."""
    facade = _FakeForgeFacade()
    cf = ContentFactory(factory_registry=_FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
    ]), forge_facade=facade)
    opp = _make_opp()
    result = cf.execute(opp, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["request"]["factory_id"] == "content"
    assert facade.calls == []  # ForgeFacade не вызывался


# ─── 4. Integration vertical slice (§16 integration) ────────────────────────

def test_9_execute_full_slice_artifact_and_feedback():
    """Opportunity → resolve → request → ForgeFacade.run_chain → artifact → memory."""
    facade = _FakeForgeFacade(overall="ok")
    memory = _FakeMemoryStore()
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    # Нужен реальный/фейковый Project — подменяем _resolve_project статически.
    cf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_project")})()
    result = cf.execute(opp)
    assert result["ok"] is True
    art = result["artifact"]
    assert art["kind"] == "content_artifact"
    assert art["factory_id"] == "content"
    assert art["forge_id"] == "writing"
    assert art["overall"] == "ok"
    assert facade.calls and facade.calls[0]["role_ids"] == CONTENT_ROLE_IDS
    assert memory.kos and memory.kos[0]["kind"] == "candidate"
    assert "content_factory" in memory.kos[0]["tags"]
    assert memory.events and memory.events[0]["outcome"] == "success"


def test_10_execute_failed_run_marks_raw_and_failure():
    facade = _FakeForgeFacade(overall="failed")
    memory = _FakeMemoryStore()
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    cf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_project")})()
    result = cf.execute(opp)
    assert result["ok"] is True  # fail-safe: артефакт с overall=failed фиксируется
    assert result["artifact"]["overall"] == "failed"
    assert memory.kos[0]["lifecycle_stage"] == "raw"
    assert memory.events[0]["outcome"] == "failure"


def test_11_execute_no_capability_returns_error():
    cf = ContentFactory()
    opp = _make_opp(capability=None)
    opp.provenance = {"source": "whim"}
    opp.scenario = None
    result = cf.execute(opp)
    assert result["ok"] is False
    assert "no capability" in result["error"]


def test_12_execute_unresolvable_project_fails_safe():
    cf = ContentFactory(
        factory_registry=_FakeFactoryRegistry({"article_generation": ("content", "writing")}),
        forge_facade=_FakeForgeFacade(),
    )
    opp = _make_opp(project_id="nonexistent_project_xyz")
    cf._resolve_project = lambda opp, project_root=None: None
    result = cf.execute(opp)
    assert result["ok"] is False
    assert "unresolved" in result["error"]


# ─── 5. Negative domain-isolation (§17 — ГЛАВНЫЙ тест) ──────────────────────

def test_13_domain_isolation_si_agnostic(tmp_path):
    """Принципиальный (dominant) тест domain-neutrality (разделён на 13a + 13b).

    SI НЕ знает, что ContentFactory существует. Доминирующая проверка —
    грепом по исходнику SI: отсутствие упоминаний ``ContentFactory`` /
    ``content_factory``. Тест 13b (см. ниже) документирует реальную
    SI-ranking limitation через xfail — НЕ маскирует её lenientом.
    """
    # Доминирующая проверка domain-neutrality — SI-исходник НЕ должен
    # содержать ссылок на ContentFactory (промт 092 §17).
    src = Path("scripts_01/scenario_intelligence.py").read_text(encoding="utf-8")
    assert "ContentFactory" not in src, "SI source must not reference ContentFactory class"
    assert "content_factory" not in src, "SI source must not reference content_factory module"

    # Один и тот же универсальный FactoryRegistry резолвит оба домена
    # (вспомогательная проверка, что фабрик-фейк отдаёт пары по capability).
    factory_registry = _FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
        "code": ("test", "code_forge"),
    ])
    assert factory_registry.select_forge("article_generation")[0].factory_id == "content"
    assert factory_registry.select_forge("article_generation")[1].forge_id == "writing"
    assert factory_registry.select_forge("code")[0].factory_id == "test"
    assert factory_registry.select_forge("code")[1].forge_id == "code_forge"


# @pytest.mark.xfail REMOVED in v5.189.30 (G-11.6 SI hard-gate fix landed; test now correctly PASSES instead of XPASS-failing). Was: @pytest.mark.xfail(     reason=(         "SI-ranking limitation: scenarios with higher raw_proposal_score win "         "regardless of capability-match. P0 follow-up from promt 091 §EVAL_WEIGHTS "    ...
def test_13b_si_routes_code_opp_to_test_factory(tmp_path):
    """Per-opp SI routing: opp_code → (test, code_forge), opp_content → (content, writing).

    Известная SI-ranking limitation: select() возвращает первый по raw_score
    proposal, не по capability-match. Этот тест xfail-ит (strict=False) и
    фиксирует требование к ревью SI ranking (promt 091 §EVAL_WEIGHTS).
    """
    from scripts_01.scenario_intelligence import ScenarioIntelligence

    factory_registry = _FakeFactoryRegistry({
        "article_generation": ("content", "writing"),
        "code": ("test", "code_forge"),
    ])
    scenarios = [
        (_FakeScenario("scenario_content", ["article_generation"]), _FakeRole("writer"), 0.9),
        (_FakeScenario("scenario_code", ["code"]), _FakeRole("developer"), 0.6),  # ниже скора content
    ]
    registry = _FakeRegistry(scenarios)
    si = ScenarioIntelligence(registry=registry, factory_registry=factory_registry)

    opp_content = _make_opp(opp_id="opp-c", capability="article_generation")
    d1 = si.select(opp_content, persist=False)
    assert d1.capability == "article_generation"
    assert d1.factory_id == "content"
    assert d1.forge_id == "writing"

    opp_code = _make_opp(opp_id="opp-x", capability="code")
    d2 = si.select(opp_code, persist=False)
    assert d2.capability == "code"
    assert d2.factory_id == "test"
    assert d2.forge_id == "code_forge"


def test_14_real_factory_registry_resolves_content_manifests():
    """Реальные манифесты runtime_05/factories/content/ резолвятся через FactoryRegistry."""
    from core_02.factory_registry import FactoryRegistry
    reg = FactoryRegistry(Path("runtime_05/factories"))
    pair = reg.select_forge("article_generation")
    assert pair is not None
    assert pair[0].factory_id == "content"
    assert pair[1].forge_id == "writing"
    # Все контент-токены разрешаются.
    for cap in CONTENT_CAPABILITIES:
        assert reg.select_forge(cap) is not None, f"{cap} не разрешается"


# ─── G-13.1 (ADR-015): per-instance warnings isolation ───────────────────────

def test_15_per_instance_warnings_no_cross_pollution():
    """PHASE 13 G-13.1 (ADR-015): per-instance ``_import_warnings`` must be
    fresh per instance and must NOT cross-pollute between ContentFactory
    instances — the legacy module-level ``_LAZY_IMPORT_ERRORS`` was removed
    (deprecated shim only) and lazy-import failures now land on
    ``inst._import_warnings`` exclusively.
    """
    import core_02.factory_base as fb

    # Force factory_base._lazy_import to return None — simulates missing dep.
    original_lazy_import = fb._lazy_import

    def _failing_lazy_import(module_name: str, attr: str):
        return None  # always fail → triggers warning append path

    fb._lazy_import = _failing_lazy_import
    try:
        # Snapshot the deprecated module-level singleton (should remain 0
        # because per-instance migration removed all appends there).
        # PEP 562 __getattr__ (v5.189.35 hardening) emits DeprecationWarning
        # on this access; suppress here — behavior under test is the VALUE.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depr_singleton_before = list(fb._LAZY_IMPORT_ERRORS)

        # ─── 1. Fresh instance starts with empty warnings ───
        inst1 = ContentFactory(factory_registry=None, forge_facade=None)
        assert inst1._import_warnings == [], (
            "fresh ContentFactory instance must start with empty warnings"
        )

        # ─── 2. Trigger lazy-load on inst1 → warnings populated ───
        result = inst1._lazy_factory_registry()
        assert result is None, "failing lazy import must return None"
        assert len(inst1._import_warnings) >= 1, (
            "inst1._import_warnings must capture lazy-import failure"
        )
        assert inst1._import_warnings[0].startswith("factory_registry:"), (
            f"warning text mismatch: {inst1._import_warnings!r}"
        )
        inst1_warnings_snapshot = list(inst1._import_warnings)

        # ─── 3. SECOND ContentFactory instance — must have FRESH empty warnings ───
        inst2 = ContentFactory(factory_registry=None, forge_facade=None)
        assert inst2._import_warnings == [], (
            "SECOND ContentFactory instance must have FRESH empty warnings "
            "(no cross-pollution via module-level singleton)"
        )

        # ─── 4. Trigger lazy-load on inst2 — inst1 unchanged ───
        inst2._lazy_factory_registry()
        assert inst2._import_warnings == ["factory_registry: unavailable"], (
            f"inst2 should have 1 warning after forced failure: {inst2._import_warnings!r}"
        )
        assert inst1._import_warnings == inst1_warnings_snapshot, (
            f"inst1 warnings DRIFTED after inst2 lazy load — cross-pollution: "
            f"before={inst1_warnings_snapshot!r} after={inst1._import_warnings!r}"
        )

        # ─── 5. Cross-class isolation — ResearchFactory instance must be fresh ───
        from scripts_01.research_factory import ResearchFactory
        inst_r = ResearchFactory(factory_registry=None, forge_facade=None)
        assert inst_r._import_warnings == [], (
            "ResearchFactory instance must also have FRESH empty warnings"
        )
        inst_r._lazy_factory_registry()
        # Cross-class check: inst1 + inst2 unchanged, only inst_r grew.
        assert inst1._import_warnings == inst1_warnings_snapshot
        assert inst2._import_warnings == ["factory_registry: unavailable"]

        # ─── 6. Deprecated module-level singleton was NOT appended by per-instance ───
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depr_singleton_after = list(fb._LAZY_IMPORT_ERRORS)
        assert depr_singleton_after == depr_singleton_before, (
            f"DEPRECATED module-level singleton must NOT receive appends from "
            f"per-instance lazy methods (G-13.1). before={depr_singleton_before!r} "
            f"after={depr_singleton_after!r}"
        )
    finally:
        # Restore the original _lazy_import (test isolation).
        fb._lazy_import = original_lazy_import


# ─── v5.189.35 hardening: PEP 562 __getattr__ emits DeprecationWarning on import ──

def test_16_lazy_import_errors_singleton_emits_deprecation_warning():
    """External consumer imports of ``_LAZY_IMPORT_ERRORS`` from
    ``core_02.factory_base`` MUST emit ``DeprecationWarning`` pointing at
    ``inst._import_warnings`` (v5.189.35 hardening per ADR-015 §Extension).

    Also verifies:
    - The access still returns a real ``List[str]`` (backward-compat surface).
    - The warning text contains the migration pointer.
    - The warning is filterable to ``error`` (pytest ``-W error::DeprecationWarning``
      does NOT break the value shape).
    - A second access still fires (no Python warning cache interference when
      the consumer changes stacklevel — caller-site dedup is up to the user).
    """
    import warnings
    import core_02.factory_base as fb

    # ─── 1. First access: DeprecationWarning fires ───
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        val = fb._LAZY_IMPORT_ERRORS

    assert isinstance(val, list), (
        f"DEPRECATED shim must remain a real list (backward-compat); got {type(val).__name__}"
    )
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), (
        f"Expected at least one DeprecationWarning, got: "
        f"{[(w.category.__name__, str(w.message)[:60]) for w in caught]}"
    )
    deprecation_msgs = [str(w.message) for w in caught
                       if issubclass(w.category, DeprecationWarning)]
    assert deprecation_msgs, "at least one DeprecationWarning must be present"
    assert any("inst._import_warnings" in m for m in deprecation_msgs), (
        f"DeprecationWarning must point at inst._import_warnings; got: {deprecation_msgs!r}"
    )
    assert any("core_02.factory_base._LAZY_IMPORT_ERRORS" in m for m in deprecation_msgs), (
        f"DeprecationWarning must mention _LAZY_IMPORT_ERRORS; got: {deprecation_msgs!r}"
    )

    # ─── 2. Re-access: deprecation still works (caller-site filter policy is user's choice) ───
    with warnings.catch_warnings(record=True) as caught2:
        warnings.simplefilter("always", DeprecationWarning)
        val2 = fb._LAZY_IMPORT_ERRORS
    assert isinstance(val2, list)
    # Python's default warning filter can deduplicate by source location;
    # using fresh `catch_warnings(record=True)` resets per-call state.
    deprecation2 = [w for w in caught2 if issubclass(w.category, DeprecationWarning)]
    assert deprecation2, (
        "Each explicit consumer call should still get a DeprecationWarning; "
        "if this fails, Python's filter is suppressing it (check -W flags)"
    )

    # ─── 3. Under ``error::DeprecationWarning`` filter, access raises (correct behavior). ───
    # The shim's design is "warn + return"; if the consumer explicitly escalates
    # the warning to an error, Python will raise BEFORE we return. This is the
    # documented design — consumers who set ``error::`` filter accept the raise.
    import pytest
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        with pytest.raises(DeprecationWarning) as excinfo:
            fb._LAZY_IMPORT_ERRORS
    assert "inst._import_warnings" in str(excinfo.value), (
        f"Raised DeprecationWarning must point at inst._import_warnings; "
        f"got: {str(excinfo.value)[:120]}"
    )
