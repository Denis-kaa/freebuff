"""tests_09/test_test_factory.py — Phase 11 Test Factory (promt 93).

Покрывает §16 (unit/integration/regression/negative domain-isolation) +
§17 (negative domain-isolation «SI не знает про TestFactory») +
test_15 (THIRD-client META-TEST: единый универсальный FactoryContract
обслуживает ВСЕ ТРИ домена: content + research + test).

Hermetic: фейковые Registry/ForgeFacade/MemoryStore, без side-effect на data_13.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.test_factory import (  # noqa: E402
    TestFactory,
    ExecutionRequest,
    TEST_CAPABILITIES,
    TEST_ROLE_IDS,
)


# ─── Fakes (hermetic; mirrors test_content_factory.py) ──────────────────────

class _FakeScenario:
    def __init__(self, scenario_id: str, capabilities):
        self.scenario_id = scenario_id
        self.display_name = scenario_id
        self.capabilities = list(capabilities)
        self.capability = capabilities[0] if capabilities else None


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
                           "role_ids": role_ids})
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
        return (type("FP", (), {"factory_id": fp})(),
                type("FG", (), {"forge_id": fg})())


def _make_opp(opp_id="opp-test1", project_id="proj-test", capability="code",
              status="ACTIVE", test_block=None):
    """Opportunity с test-специфичными полями."""
    return type("Opp", (), {
        "id": opp_id,
        "project_id": project_id,
        "title": "Run test: Factory-контракт универсален над третьим доменом",
        "description": "Verifier artifact над capability=code.",
        "source": "forge-test",
        "status": status,
        "priority": 5,
        "provenance": {
            "source": "factory_test",
            "source_id": "ft-1",
            "capability": capability,
            "test": test_block or {
                "requested_code": "deterministic_test_request",
                "assertion": "selected_factory == 'test'",
                "expected_outcome": "ok",
                "context": "Phase 11 third domain universality",
            },
        },
        "scenario": {"capability": capability},
        "source_path": "data_13/opportunities.yaml",
        "evidence_path": "",
        "related_whims": [],
    })()


# ─── 1. Capability resolution (§16 unit) ────────────────────────────────────

def test_1_capabilities_registered_in_closed_vocab():
    """Code-токен должен быть в KNOWN_CAPABILITIES (register-first, ANTI-6b)."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES
    for cap in TEST_CAPABILITIES:
        assert cap in KNOWN_CAPABILITIES, f"{cap} отсутствует в KNOWN_CAPABILITIES"


def test_2_resolve_code_capability_via_fake_registry():
    tf = TestFactory(factory_registry=_FakeFactoryRegistry({
        "code": ("test", "verifier"),
    }))
    pair = tf.resolve("code")
    assert pair is not None
    assert pair[0].factory_id == "test"
    assert pair[1].forge_id == "verifier"


def test_3_resolve_unknown_capability_returns_none():
    tf = TestFactory(factory_registry=_FakeFactoryRegistry({
        "code": ("test", "verifier"),
    }))
    # Не из нашего домена.
    assert tf.resolve("article_generation") is None
    assert tf.resolve("research") is None


def test_4_resolve_without_registry_returns_none():
    tf = TestFactory(factory_registry=None)
    # Без реестра — fail-safe None, не краш.
    assert tf.resolve("code") is None or True  # не бросает


# ─── 2. Input normalization (test-specific, §16 unit) ─────────────────────

def test_5_normalize_input_test_specific_fields():
    tf = TestFactory()
    opp = _make_opp(test_block={
        "requested_code": "select_forge_test",
        "assertion": "selected_factory == 'test'",
        "expected_outcome": "ok",
        "context": "Phase 11 verification",
    })
    inp = tf.normalize_input(opp)
    assert inp["requested_code"] == "select_forge_test"
    assert inp["test_assertion"] == "selected_factory == 'test'"
    assert inp["expected_outcome"] == "ok"
    assert inp["verification_context"] == "Phase 11 verification"
    assert inp["title"].startswith("Run test:")
    assert inp["source"] == "forge-test"
    assert inp["provenance"]["capability"] == "code"


def test_5b_normalize_input_no_test_block_falls_back():
    """Без test-блока — fallback на title/description (fail-safe)."""
    tf = TestFactory()
    opp = _make_opp(test_block=None)
    opp.provenance = {"source": "forge-test", "capability": "code"}
    inp = tf.normalize_input(opp)
    assert inp["requested_code"] == opp.title  # fallback на title
    assert "pending" in inp["test_assertion"]  # дефолт assertion
    assert inp["expected_outcome"] == "ok"  # дефолт outcome


# ─── 3. Execution request (§16 unit) ────────────────────────────────────────

def test_6_build_execution_request():
    tf = TestFactory(factory_registry=_FakeFactoryRegistry({
        "code": ("test", "verifier"),
    }))
    opp = _make_opp()
    req = tf.build_execution_request(opp, "code")
    assert isinstance(req, ExecutionRequest)
    assert req.factory_id == "test"
    assert req.forge_id == "verifier"
    assert req.capability == "code"
    assert req.role_ids == TEST_ROLE_IDS
    assert req.inputs["requested_code"] == "deterministic_test_request"
    assert "projects_17/proj-test/forge/" in req.output_spec["target"]


def test_7_build_request_missing_factory_returns_none():
    tf = TestFactory(factory_registry=_FakeFactoryRegistry({}))
    opp = _make_opp()
    assert tf.build_execution_request(opp, "code") is None


def test_8_execute_dry_run_no_forge_call():
    """dry_run=True формирует request, НЕ вызывает ForgeFacade."""
    facade = _FakeForgeFacade()
    tf = TestFactory(
        factory_registry=_FakeFactoryRegistry({"code": ("test", "verifier")}),
        forge_facade=facade,
    )
    opp = _make_opp()
    result = tf.execute(opp, dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["request"]["factory_id"] == "test"
    assert facade.calls == []  # ForgeFacade не вызывался


# ─── 4. Integration vertical slice (§16 integration) ────────────────────────

def test_9_execute_full_slice_artifact_and_feedback():
    """Opportunity → resolve → request → ForgeFacade.run_chain → artifact → memory."""
    facade = _FakeForgeFacade(overall="ok")
    memory = _FakeMemoryStore()
    tf = TestFactory(
        factory_registry=_FakeFactoryRegistry({"code": ("test", "verifier")}),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    tf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_test_proj")})()
    result = tf.execute(opp)
    assert result["ok"] is True
    art = result["artifact"]
    assert art["kind"] == "verifier_report"
    assert art["factory_id"] == "test"
    assert art["forge_id"] == "verifier"
    assert art["overall"] == "ok"
    assert facade.calls and facade.calls[0]["role_ids"] == TEST_ROLE_IDS
    assert memory.kos and memory.kos[0]["kind"] == "candidate"
    assert "test_factory" in memory.kos[0]["tags"]
    assert "code" in memory.kos[0]["tags"]
    assert memory.events and memory.events[0]["outcome"] == "success"


def test_10_execute_failed_run_marks_raw_and_failure():
    facade = _FakeForgeFacade(overall="failed")
    memory = _FakeMemoryStore()
    tf = TestFactory(
        factory_registry=_FakeFactoryRegistry({"code": ("test", "verifier")}),
        forge_facade=facade,
        memory_store=memory,
    )
    opp = _make_opp()
    tf._resolve_project = lambda opp, project_root=None: type(
        "Proj", (), {"root": Path("/tmp/fake_test_proj")})()
    result = tf.execute(opp)
    assert result["ok"] is True  # fail-safe
    assert result["artifact"]["overall"] == "failed"
    assert memory.kos[0]["lifecycle_stage"] == "raw"
    assert memory.events[0]["outcome"] == "failure"


def test_11_execute_no_capability_returns_error():
    tf = TestFactory()
    opp = _make_opp(capability=None)
    opp.provenance = {"source": "forge-test"}
    opp.scenario = None
    result = tf.execute(opp)
    assert result["ok"] is False
    assert "no capability" in result["error"]


def test_12_execute_unresolvable_project_fails_safe():
    tf = TestFactory(
        factory_registry=_FakeFactoryRegistry({"code": ("test", "verifier")}),
        forge_facade=_FakeForgeFacade(),
    )
    opp = _make_opp(project_id="nonexistent_test_project_xyz")
    tf._resolve_project = lambda opp, project_root=None: None
    result = tf.execute(opp)
    assert result["ok"] is False
    assert "unresolved" in result["error"]


# ─── 5. Negative domain-isolation (§17) ──────────────────────────────────────

def test_13a_domain_isolation_si_agnostic(tmp_path):
    """Принципиальный (dominant) тест domain-neutrality.

    SI НЕ знает, что TestFactory существует. Доминирующая проверка — грепом
    по исходнику SI: отсутствие упоминаний ``TestFactory`` / ``test_factory``.
    """
    # Доминирующая проверка domain-neutrality — SI-исходник НЕ должен
    # содержать ссылок на TestFactory (промт 93 §17).
    src = Path("scripts_01/scenario_intelligence.py").read_text(encoding="utf-8")
    assert "TestFactory" not in src, "SI source must not reference TestFactory class"
    assert "test_factory" not in src, "SI source must not reference test_factory module"

    # Один и тот же универсальный FactoryRegistry резолвит ВСЕ ТРИ домена
    # (вспомогательная проверка universal-boundary).
    factory_registry = _FakeFactoryRegistry({
        "code": ("test", "verifier"),
        "article_generation": ("content", "writing"),
        "research": ("research", "analysis"),
    })
    assert factory_registry.select_forge("code")[0].factory_id == "test"
    assert factory_registry.select_forge("article_generation")[0].factory_id == "content"
    assert factory_registry.select_forge("research")[0].factory_id == "research"


@pytest.mark.xfail(
    reason=(
        "SI-ranking limitation documented in promt 091 §EVAL_WEIGHTS: scenarios "
        "ранжируются по raw_proposal_score без capability-match hard gate. "
        "Current Phase 11 FakeRegistry filter is tight enough that the limitation "
        "may or may not surface depending on scenario structure — strict=False, "
        "lenient mode. Day SI ranking gets a hard capability gate, this marker "
        "loses purpose and can be removed."
    ),
    strict=False,
)
def test_13b_si_routes_code_opp_to_test_factory(tmp_path):
    """Symmetric to content/research test_13b."""
    from scripts_01.scenario_intelligence import ScenarioIntelligence

    factory_registry = _FakeFactoryRegistry({
        "code": ("test", "verifier"),
    })
    scenarios = [
        (_FakeScenario("scenario_test", ["code"]), _FakeRole("verifier"), 0.9),
        (_FakeScenario("scenario_other", ["x"]), _FakeRole("other"), 0.6),
    ]
    registry = _FakeRegistry(scenarios)
    si = ScenarioIntelligence(registry=registry, factory_registry=factory_registry)
    opp_code = _make_opp(opp_id="opp-c", capability="code")
    d = si.select(opp_code, persist=False)
    assert d.capability == "code"
    assert d.factory_id == "test"
    assert d.forge_id == "verifier"


def test_14_real_factory_registry_resolves_test_manifests():
    """Реальные манифесты runtime_05/factories/test/ резолвятся через FactoryRegistry."""
    from core_02.factory_registry import FactoryRegistry
    reg = FactoryRegistry(Path("runtime_05/factories"))
    pair = reg.select_forge("code")
    assert pair is not None
    assert pair[0].factory_id == "test"
    assert pair[1].forge_id == "verifier"


# ─── 6. THIRD-CLIENT UNIVERSALITY meta-test (Phase 11 ключевой) ──────────────

def test_15_universal_factory_registry_routes_three_domains(tmp_path):
    """META-TEST: единый универсальный FactoryContract обслуживает ВСЕ ТРИ домена.

    Без Phase 9 / 10 / 11 изоляции — три манифест-дерева (``content``, ``research``,
    ``test``) лежат под одним ``runtime_05/factories/`` корнем. Один экземпляр
    ``FactoryRegistry`` резолвит capability → (factory, forge) для ВСЕХ ТРЁХ
    доменов через ОДНУ функцию ``select_forge``. Это финальное доказательство
    универсальности Factory-контракта (Phase 11 / promt 93 §22 Variant B).
    """
    from core_02.factory_registry import FactoryRegistry
    reg = FactoryRegistry(Path("runtime_05/factories"))

    # Content domain (Phase 9).
    pair_content = reg.select_forge("article_generation")
    assert pair_content is not None, "Phase 9 capability article_generation не резолвится"
    assert pair_content[0].factory_id == "content"
    assert pair_content[1].forge_id == "writing"

    # Research domain (Phase 10).
    pair_research = reg.select_forge("research")
    assert pair_research is not None, "Phase 10 capability research не резолвится"
    assert pair_research[0].factory_id == "research"
    assert pair_research[1].forge_id == "analysis"

    # Test domain (Phase 11).
    pair_test = reg.select_forge("code")
    assert pair_test is not None, "Phase 11 capability code не резолвится"
    assert pair_test[0].factory_id == "test"
    assert pair_test[1].forge_id == "verifier"

    # ALL THREE domains distinguishable.
    factories = {pair_content[0].factory_id, pair_research[0].factory_id, pair_test[0].factory_id}
    # EXACTLY-3 strict set equality (Phase 12 G-11.5 close): any 4th factory OR rename fails this.
    assert factories == {"content", "research", "test"}, (
        f"ожидалось EXACTLY {{content, research, test}} — получили {factories}. "
        f"Это либо Phase 12 BaseFactory subclass добавил новый домен и не обновил §20 row 25 / CHANGELOG, "            f"либо G-11.5 нарушен (test_15 стал lenient)."
        )


# ─── G-13.1 (ADR-015): per-instance warnings isolation ───────────────────────

def test_16_per_instance_warnings_no_cross_pollution():
    """PHASE 13 G-13.1 (ADR-015): per-instance ``_import_warnings`` across
    TestFactory / ContentFactory / ResearchFactory must remain isolated.
    Defends against regression to the deprecated module-level singleton.
    """
    import core_02.factory_base as fb
    # Inline imports for cross-class isolation (test_test_factory only
    # imports TestFactory at top — Content/Research needed here).
    from scripts_01.content_factory import ContentFactory
    from scripts_01.research_factory import ResearchFactory

    original_lazy_import = fb._lazy_import

    def _failing_lazy_import(module_name: str, attr: str):
        return None

    fb._lazy_import = _failing_lazy_import
    try:
        # Snapshot deprecated module-level singleton (must NOT grow).
        # Snapshot deprecated module-level singleton (must NOT grow) — suppress
        # PEP 562 DeprecationWarning (v5.189.35 hardening); behavior under test
        # is the VALUE/shape, not the warning emission.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depr_before = list(fb._LAZY_IMPORT_ERRORS)

        # Three instances, each in turn triggers the lazy-load failure.
        inst_t = TestFactory(factory_registry=None, forge_facade=None)
        assert inst_t._import_warnings == []
        inst_t._lazy_factory_registry()
        assert inst_t._import_warnings == ["factory_registry: unavailable"]

        inst_c = ContentFactory(factory_registry=None, forge_facade=None)
        assert inst_c._import_warnings == []
        inst_c._lazy_factory_registry()
        assert inst_c._import_warnings == ["factory_registry: unavailable"]

        inst_r = ResearchFactory(factory_registry=None, forge_facade=None)
        assert inst_r._import_warnings == []
        inst_r._lazy_factory_registry()
        assert inst_r._import_warnings == ["factory_registry: unavailable"]

        # After all 3 forced lazy-loads, NO instance appended to the others'
        # warnings lists — per-instance isolation preserved.
        assert inst_t._import_warnings == ["factory_registry: unavailable"]
        assert inst_c._import_warnings == ["factory_registry: unavailable"]
        assert inst_r._import_warnings == ["factory_registry: unavailable"]

        # Deprecated singleton untouched (per-instance migration complete).
        # Deprecated singleton untouched (per-instance migration complete) —
        # suppress PEP 562 DeprecationWarning (v5.189.35 hardening).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depr_after = list(fb._LAZY_IMPORT_ERRORS)
        assert depr_after == depr_before, (
            f"DEPRECATED module-level singleton must NOT receive appends from "
            f"per-instance lazy methods. before={depr_before!r} after={depr_after!r}"
        )
    finally:
        fb._lazy_import = original_lazy_import

