"""tests_09/test_anchors_resolver.py — AnchorResolver (Artifact I §I.3, v5.189.4).

Покрывает 19-namespace резолвер core_02/anchors_resolver.py:
- extract_anchors: code fences, множественные namespace в строке, doc.* без @;
- resolve: entity (Artifact A + модуль-fallback + MissingRegistry), module, symbol
  (STALE при отсутствии), contract, event, storage (файл/каталог/shorthand),
  test (файл + AST-функция), decision, requirement/scenario (DESIGN_ONLY),
  factory/forge (enum), opportunity/whim (store-id), lesson (leading-zeros),
  doc (base-name);
- run(): hard-namespace unresolved == 0 на реальном проекте (реестры как данные).
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core_02.anchors_resolver import (  # noqa: E402
    CANONICAL_FACTORIES,
    CANONICAL_FORGES,
    Anchor,
    AnchorResolver,
    extract_anchors,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HARD_NAMESPACES = frozenset({
    "entity", "component", "module", "symbol", "test", "decision",
    "storage", "factory", "forge", "lesson", "opportunity", "whim",
***REMOVED***)


# ─── extract_anchors ───────────────────────────────────────────────

class TestExtractAnchors:
    def test_skips_code_fences(self):
        text = (
            "```python\n"
            "@entity forge.facade\n"
            "```\n"
            "Real anchor here: `@entity forge.facade`\n"
        )
        anchors = extract_anchors(text)
        assert len(anchors) == 1
        assert anchors[0***REMOVED***.namespace == "entity"
        assert anchors[0***REMOVED***.value == "forge.facade"

    def test_multiple_namespaces_same_line(self):
        text = "(@entity forge.facade) via (@symbol ForgeFacade.run_chain)"
        anchors = extract_anchors(text)
        namespaces = {a.namespace for a in anchors***REMOVED***
        assert namespaces == {"entity", "symbol"***REMOVED***

    def test_lesson_subtype(self):
        anchors = extract_anchors("(@lesson CON_017) binds (@lesson ANTI_06b)")
        values = {a.value for a in anchors***REMOVED***
        assert values == {"CON_017", "ANTI_06b"***REMOVED***

    def test_doc_anchor_no_at(self):
        anchors = extract_anchors("see `doc.factory_forge_arch#20.c4`")
        assert anchors and anchors[0***REMOVED***.namespace == "doc"
        assert anchors[0***REMOVED***.value == "doc.factory_forge_arch#20.c4"

    def test_empty_text(self):
        assert extract_anchors("") == [***REMOVED***
        assert extract_anchors("no anchors here") == [***REMOVED***


# ─── resolve: entity ───────────────────────────────────────────────

class TestResolveEntity:
    def test_artifact_a_entity(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@entity forge.facade")
        assert res["resolved"***REMOVED*** is True
        assert res["status"***REMOVED*** == "CURRENT"

    def test_module_file_fallback(self):
        # model.gateway → core_02/model_gateway.py (не в Artifact A, но модуль есть)
        res = AnchorResolver(PROJECT_ROOT).resolve("@entity model.gateway")
        assert res["resolved"***REMOVED*** is True, res

    def test_py_suffix_entity(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@entity scenario_registry.py")
        assert res["resolved"***REMOVED*** is True, res

    def test_missing_registry_design_only(self):
        # decision.registry — Missing Capability #3 (registered, не реализована)
        res = AnchorResolver(PROJECT_ROOT).resolve("@entity decision.registry")
        assert res["status"***REMOVED*** == "DESIGN_ONLY", res

    def test_unknown_entity(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@entity definitely.nonexistent_xyz")
        assert res["status"***REMOVED*** == "UNVERIFIED"


# ─── resolve: module / symbol ──────────────────────────────────────

class TestResolveModule:
    def test_scripts_module(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@module forge.cli")
        assert res["resolved"***REMOVED*** is True, res

    def test_core_module(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@module forge.facade")
        assert res["resolved"***REMOVED*** is True, res

    def test_missing_module(self):
        # first-segment fallback (`forge.cli` → forge.py, спец §I.1 row 3) —
        # поэтому используем заведомо отсутствующий домен.
        res = AnchorResolver(PROJECT_ROOT).resolve("@module zzz_nonexistent.qqq")
        assert res["status"***REMOVED*** == "UNVERIFIED"


class TestResolveSymbol:
    @pytest.mark.slow  # v5.189.10: real-project AST-скан (~5.6s)
    def test_class_method_found(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@symbol ScenarioRegistry.find_role")
        assert res["resolved"***REMOVED*** is True, res

    @pytest.mark.slow  # v5.189.10: real-project AST-скан (~10s)
    def test_absent_symbol_is_stale(self):
        # §I.7 anti-hallucination: отсутствующий символ → STALE, не UNVERIFIED.
        res = AnchorResolver(PROJECT_ROOT).resolve("@symbol StaleClass.old_method")
        assert res["status"***REMOVED*** == "STALE", res


# ─── resolve: contract / event / storage / test / decision ─────────

class TestResolveContract:
    def test_registered_contract(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@contract forge.execution")
        assert res["resolved"***REMOVED*** is True, res


class TestResolveStorage:
    def test_yaml_file(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@storage opportunities_yaml")
        assert res["resolved"***REMOVED*** is True, res

    def test_top_level_dir(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@storage data_13")
        assert res["resolved"***REMOVED*** is True, res

    def test_shorthand_owned_by_module(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@storage memory_dir_yaml")
        assert res["resolved"***REMOVED*** is True, res

    def test_missing_storage(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@storage definitely_missing_xyz")
        assert res["status"***REMOVED*** == "UNVERIFIED"


class TestResolveTest:
    def test_test_file(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@test test_scenario_registry")
        assert res["resolved"***REMOVED*** is True, res

    def test_test_function_in_file(self):
        # test_real_project_consistent — функция в test_consistency_check.py
        res = AnchorResolver(PROJECT_ROOT).resolve("@test test_real_project_consistent")
        assert res["resolved"***REMOVED*** is True, res

    def test_missing_test(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@test test_definitely_missing_xyz")
        assert res["status"***REMOVED*** == "UNVERIFIED"


class TestResolveDecision:
    def test_adr_file(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@decision ADR_010")
        assert res["resolved"***REMOVED*** is True, res

    def test_missing_adr(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@decision ADR_999")
        assert res["status"***REMOVED*** == "UNVERIFIED"


# ─── resolve: planned / enum / store-id / lesson / doc ─────────────

class TestResolvePlanned:
    def test_requirement_design_only(self):
        # REQ_REGISTRY_V1.md не существует → DESIGN_ONLY (planned, §I.9)
        res = AnchorResolver(PROJECT_ROOT).resolve("@requirement REQ-OBSERVABILITY-03")
        assert res["status"***REMOVED*** == "DESIGN_ONLY", res

    def test_scenario_manifest(self):
        # runtime_05/scenarios/ существует (blueprint_v3.yaml и др.)
        res = AnchorResolver(PROJECT_ROOT).resolve("@scenario blueprint_v3")
        assert res["status"***REMOVED*** in ("CURRENT", "DESIGN_ONLY"), res


class TestResolveEnums:
    def test_all_factories(self):
        resolver = AnchorResolver(PROJECT_ROOT)
        for factory in CANONICAL_FACTORIES:
            assert resolver.resolve(f"@factory {factory***REMOVED***")["resolved"***REMOVED*** is True

    def test_all_forges(self):
        resolver = AnchorResolver(PROJECT_ROOT)
        for forge in CANONICAL_FORGES:
            assert resolver.resolve(f"@forge {forge***REMOVED***")["resolved"***REMOVED*** is True

    def test_forge_unknown(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@forge forge_unknown")
        assert res["status"***REMOVED*** == "UNVERIFIED"


class TestResolveStoreIds:
    def test_opportunity_missing_id(self):
        # id нет в data_13/opportunities.yaml → UNVERIFIED (без исключения).
        res = AnchorResolver(PROJECT_ROOT).resolve("@opportunity opp-0000000000")
        assert res["status"***REMOVED*** == "UNVERIFIED", res

    def test_whim_missing_id(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@whim whim-0000000000")
        assert res["status"***REMOVED*** == "UNVERIFIED", res


class TestResolveLesson:
    def test_leading_zero_variant(self):
        # LESSONS.md содержит CON-17; доки пишут CON_017 → норм. по ведущим нулям.
        res = AnchorResolver(PROJECT_ROOT).resolve("@lesson CON_017")
        assert res["status"***REMOVED*** == "LESSON", res

    def test_hyphen_variant(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@lesson ANTI-6b")
        assert res["status"***REMOVED*** == "LESSON", res

    def test_unknown_lesson(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("@lesson CON_999")
        assert res["status"***REMOVED*** == "UNVERIFIED"


class TestResolveDoc:
    def test_full_claim(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("doc.factory_forge_arch#20.c4")
        assert res["status"***REMOVED*** == "CURRENT", res

    def test_base_name(self):
        res = AnchorResolver(PROJECT_ROOT).resolve("doc.factory_forge_arch#99.c9")
        assert res["status"***REMOVED*** == "CURRENT", res  # base-name fallback


# ─── run(): целостность на реальном проекте ───────────────────────

class TestRunRealProject:
    """Real-project anchor resolution — slow (AST-скан всего репозитория)."""

    pytestmark = pytest.mark.slow  # v5.189.10

    def test_hard_namespaces_zero_unresolved(self):
        """Реестры как данные: hard-namespace анкоры обязаны резолвиться."""
        resolver = AnchorResolver(PROJECT_ROOT)
        summary = resolver.run(
            roots=("docs_10/engineering-memory", "runtime_05", "CHANGELOG.md"),
            exclude=("SEMANTIC_ANCHOR_SPEC_V1.md",),
        )
        assert summary["total_anchors"***REMOVED*** > 500
        hard_unresolved = [
            u for u in summary["unresolved"***REMOVED*** if u.get("namespace") in HARD_NAMESPACES
        ***REMOVED***
        assert hard_unresolved == [***REMOVED***, f"hard unresolved: {hard_unresolved[:5***REMOVED******REMOVED***"
