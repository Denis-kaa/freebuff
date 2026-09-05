"""tests_09/test_capability_gap_llm_auditor.py — CapabilityGapLlmExecutor (LLM-variant, ADR-016).

Per code-reviewer guidance (thinker round): детерминированный variant зелёный (22 passed
в test_capability_gap_auditor.py), LLM-variant должен быть ADDITIVE — никаких изменений
в deterministic-коде. Парсер должен быть fail-safe per ADR-016 (1 bad item не валит batch).

Pattern follows tests_09/test_capability_gap_auditor.py (DI через _FakeGateway style).
"""

from __future__ import annotations

import json
import subprocess
import sys
***REMOVED***
from typing import Any, Dict, List, Optional

import pytest

from core_02.capability_gap_auditor import (
    LLM_REPORT_FILE,
    LLM_ROLE_ID,
    LLM_SYSTEM_PROMPT,
    LLM_USER_PROMPT_TEMPLATE,
    _CORPUS_CONTEXT_TOP_K,
    CapabilityGapAuditorExecutor,
    CapabilityGapLlmExecutor,
    CapabilityGapReporter,
    _parse_llm_response,
    capability_audit_llm_executor_registry,
)
from core_02.missing_registry import MissingRegistry
from core_02.workspace import Project


# ─── FakeGateway (DI ModelGateway подделка для тестов) ───────────────────────


class _FakeModelResponse:
    """Имитация ModelResponse из scripts_01/model_gateway.py."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeGateway:
    """Fake ModelGateway: возвращает заранее заданный content для любого вызова.

    В production вызовов нет: тесты полностью self-contained (нет сети).
    """

    def __init__(self, content: str = "", raise_on_call: Optional[Exception***REMOVED*** = None) -> None:
        self._content = content
        self._raise = raise_on_call
        self.calls: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***

    def generate_by_capabilities(
        self, capabilities: List[str***REMOVED***, messages: List[Dict[str, Any***REMOVED******REMOVED***,
    ) -> _FakeModelResponse:
        self.calls.append({"capabilities": list(capabilities), "messages": list(messages)***REMOVED***)
        if self._raise is not None:
            raise self._raise
        return _FakeModelResponse(self._content)


def _make_fake_gateway_response(entries: List[Dict[str, Any***REMOVED******REMOVED***) -> str:
    """Генерирует JSON-in-markdown fenced block (как отвечает реальный LLM)."""
    payload = json.dumps(entries, ensure_ascii=False, indent=2)
    return f"```json\n{payload***REMOVED***\n```"


# ─── fixtures (mirror tests_09/test_capability_gap_auditor.py) ────────────────


@pytest.fixture
def project(tmp_path) -> Project:
    p = tmp_path / "llm_auditor_test_project"
    p.mkdir()
    (p / "project.yaml").write_text(
        "name: llm_auditor_test_project\ntype: script\n", encoding="utf-8",
    )
    return Project.load(p)


@pytest.fixture
def empty_registry(tmp_path) -> MissingRegistry:
    return MissingRegistry(tmp_path / "missing_registry.yaml")


@pytest.fixture
def seed_registry(empty_registry: MissingRegistry) -> MissingRegistry:
    """Реестр с реализованным research_web + несколькими registered.

    Mypy: explicit `empty_registry: MissingRegistry` annotation propagates
    type into fixture body (avoids 'Returning Any' error on return).
    """
    from core_02.missing_registry import IMPLEMENTED, REGISTERED

    empty_registry.register_missing(
        "research_web", kind="tool", factory="research",
        description="Web research (уже реализован)", status=IMPLEMENTED,
        implementation="scripts_01/research_web.py", backfill=True,
    )
    empty_registry.register_missing(
        "lisa_estimator", kind="tool", factory="research",
        description="Estimation (в реестре, не реализован)", status=REGISTERED,
    )
    return empty_registry


# ─── autouse hermetic guard (added после CRITICAL review v5.189.57) ────────
#
# существующие тесты в TestCapabilityGapLlmExecutor / TestCapabilityGapLlmExecutorQuality
# / TestCapabilityGapLlmExecutorNoSideEffects / TestDeterministicVariantUnaffected
# НЕ monkeypatch-или lookup_by_source → иначе делали бы real DEFAULT_CORPUS_DIR lookup
# → test pollution в dev среде где corpus может быть accumulated
# (post-v5.189.56 research_web persists все fetch-url в DEFAULT_CORPUS_DIR).
#
# Tests, которым нужен custom corpus: явно `monkeypatch.setattr(cp_mod, "lookup_by_source", ...)`
# В этом случае autouse stub overridden (pytest порядок: autouse first, named fixtures second,
# test-body monkeypatch ещё позже — поэтому Финальный cp_mod.lookup_by_source = test's lambda).


@pytest.fixture(autouse=True)
def _no_corpus_side_effects(monkeypatch):
    """Stub corpus_persistence.lookup_by_source по default → [***REMOVED***.
    Защищает существующие тесты от real-disk lookups в DEFAULT_CORPUS_DIR.
    """
    from scripts_01 import corpus_persistence as cp_mod

    def _stub_lookup_by_source(source, *, root=None):
        # Default: empty corpus, no real disk read.
        return [***REMOVED***

    monkeypatch.setattr(cp_mod, "lookup_by_source", _stub_lookup_by_source)


# ─── тот же VOCAL_TASK_FRAGMENT, что в test_capability_gap_auditor.py ────
# ──── (mirror для cross-variant comparison) ────


VOCAL_TASK_FRAGMENT = (
    "# Задача: рынок вокала\n\n"
    "## 1. Контекст\n"
    "Какая-то preamble-секция про репутацию в StarMaker.\n\n"
    "## 2. Изучить web-ресурсы и URL\n"
    "Использовать web research для изучения внешних источников.\n\n"
    "## 3. Прочитать отзывы и qualitative analysis\n"
    "Провести анализ отзывов и pain-points учеников.\n\n"
    "## 4. Конкурентный анализ (competitor matrix)\n"
    "Построить карту конкурентов и матрицу.\n\n"
    "## 5. Unit economics и калибровка\n"
    "Посчитать teacher time / $ и contribution margin.\n\n"
    "## 6. Прайс-скан pricing enumerator\n"
    "Найти реальные цены, не «примерно 10-20 тыс.».\n\n"
    "## 7. Anti-pattern mining\n"
    "Найти заброшенные курсы и закрытые школы.\n\n"
    "## 8. MVP и предпродажа\n"
    "Запустить предпродажу на pilot группе.\n\n"
    "## 9. Бизнес-модель: 14 полей конструкции\n"
    "Построить конструктор бизнес-моделей с 14 полями.\n\n"
    "## 10. Hypothesis ledger и kill-criteria\n"
    "Зафиксировать гипотезы и статусы.\n\n"
    "## 11. Devil's advocate: kill-questions\n"
    "Написать опровержение и 3 kill-questions.\n\n"
    "## 12. Claim source tracker [fact***REMOVED*** vs [observation***REMOVED*** vs [hypothesis***REMOVED***\n"
    "Каждое утверждение пометить тегом.\n\n"
    "## 13. Vanity metric filter (лайк не успех)\n"
    "Не считать лайки/подписчиков успехом.\n\n"
    "## 14. Weighted scoring: 8 критериев × веса\n"
    "Построить взвешенный рейтинг моделей.\n\n"
    "## 15. Corpus persistence (источники между сессий)\n"
    "Сохранять URL между сессиями.\n\n"
    "## 16. Persona funnel: фан↔ученик\n"
    "Анализ конверсии фан → ученик.\n\n"
    "## 17. Качество и disclaimers\n"
    "Ничего capability-bearing.\n"
)


# ─── TestParseLlmResponse ─────────────────────────────────────────────────────


class TestParseLlmResponse:
    """Парсер LLM-ответа: fenced ```json → fallback greedy [..***REMOVED*** → fail-safe."""

    def test_parses_fenced_json_block(self):
        caps = [
            {"item_id": "research_web", "kind": "tool", "factory": "research",
             "description": "Web research", "confidence": 0.9, "explicit": True***REMOVED***,
            {"item_id": "claim_tracker", "kind": "module", "factory": "docs_10",
             "description": "Claim tracker", "confidence": 0.7, "explicit": False***REMOVED***,
        ***REMOVED***
        content = (
            "Вот JSON: \n```json\n"
            + json.dumps(caps, ensure_ascii=False)
            + "\n```\nГотово."
        )
        out = _parse_llm_response(content)
        assert len(out) == 2
        assert out[0***REMOVED***["item_id"***REMOVED*** == "research_web"
        assert out[0***REMOVED***["explicit"***REMOVED*** is True
        assert out[1***REMOVED***["confidence"***REMOVED*** == 0.7

    def test_fallback_to_greedy_brackets(self):
        # Нет fenced-блока, но есть `[...***REMOVED***` в произвольном месте.
        caps = [{"item_id": "x", "kind": "tool", "factory": "nil",
                 "description": "Some tool", "confidence": 0.5, "explicit": True***REMOVED******REMOVED***
        content = "Some preamble text " + json.dumps(caps) + " trailing words"
        out = _parse_llm_response(content)
        assert len(out) == 1
        assert out[0***REMOVED***["item_id"***REMOVED*** == "x"

    def test_empty_string_returns_empty(self):
        assert _parse_llm_response("") == [***REMOVED***
        assert _parse_llm_response("   ") == [***REMOVED***

    def test_unparseable_json_returns_empty(self):
        # Есть скобки, но внутри не JSON.
        content = "```json\n{not a valid json:::\n```"
        assert _parse_llm_response(content) == [***REMOVED***

    def test_json_object_not_array_returns_empty(self):
        # Найден `{...***REMOVED***` или `[...***REMOVED***`, но это dict не list — per spec нужен массив.
        content = "```json\n{\"key\": \"value\"***REMOVED***\n```"
        assert _parse_llm_response(content) == [***REMOVED***

    def test_drops_items_missing_required_fields(self):
        # ADR-016 fail-safe: 1 bad item не валит batch.
        caps = [
            {"item_id": "good_one", "kind": "tool", "factory": "research",
             "description": "OK tool", "confidence": 0.8, "explicit": True***REMOVED***,
            {"item_id": "missing_kind", "factory": "research",  # kind missing
             "description": "Bad entry", "confidence": 0.5***REMOVED***,
            {"kind": "tool", "factory": "research",  # item_id missing
             "description": "Also bad", "confidence": 0.5***REMOVED***,
            {"item_id": "missing_desc", "kind": "tool",  # description missing
             "factory": "research", "confidence": 0.5***REMOVED***,
            {"item_id": "", "kind": "tool",  # empty item_id
             "factory": "research", "description": "x"***REMOVED***,
        ***REMOVED***
        content = "```json\n" + json.dumps(caps) + "\n```"
        out = _parse_llm_response(content)
        assert len(out) == 1
        assert out[0***REMOVED***["item_id"***REMOVED*** == "good_one"

    def test_uses_default_confidence_when_missing(self):
        caps = [{"item_id": "no_conf", "kind": "tool", "factory": "research",
                 "description": "no confidence attribute", "explicit": True***REMOVED******REMOVED***
        out = _parse_llm_response("```json\n" + json.dumps(caps) + "\n```")
        assert out[0***REMOVED***["confidence"***REMOVED*** == 0.5

    def test_uses_default_explicit_false_when_missing(self):
        caps = [{"item_id": "no_explicit", "kind": "tool", "factory": "research",
                 "description": "no explicit attr", "confidence": 0.5***REMOVED******REMOVED***
        out = _parse_llm_response("```json\n" + json.dumps(caps) + "\n```")
        assert out[0***REMOVED***["explicit"***REMOVED*** is False

    def test_non_dict_items_dropped_silently(self):
        # Если LLM вернул массив со скалярами или списками — drop, не crash.
        caps = [
            "just a string",
            ["nested", "list"***REMOVED***,
            42,
            None,
            {"item_id": "ok", "kind": "tool", "factory": "research",
             "description": "good", "confidence": 0.5, "explicit": False***REMOVED***,
        ***REMOVED***
        content = "```json\n" + json.dumps(caps) + "\n```"
        out = _parse_llm_response(content)
        assert len(out) == 1
        assert out[0***REMOVED***["item_id"***REMOVED*** == "ok"

    def test_handles_markdown_block_without_newline_inside(self):
        # Edge case: ```json[***REMOVED***``` (без внутренних \n).
        caps = [{"item_id": "tight", "kind": "tool", "factory": "nil",
                 "description": "tight block", "confidence": 0.5, "explicit": True***REMOVED******REMOVED***
        content = "```json" + json.dumps(caps) + "```"
        out = _parse_llm_response(content)
        assert len(out) == 1
        assert out[0***REMOVED***["item_id"***REMOVED*** == "tight"

    def test_drops_items_with_unknown_kind(self):
        """ANTI-6b vocabulary defense: kind вне _KINDS тихо отбрасываются (silent reject).

        Per код-ревью v5.189.55: LLM_SYSTEM_PROMPT объявляет kind в закрытом множестве
        ``{tool, module, role, engine***REMOVED***`` (MissingRegistry.KINDS), но парсер должен
        валидировать и тихо отбрасывать нарушителей, иначе — silent drift в registry
        cross-check (kind="service"/"agent"/"skill" никогда не зарегистрированы).
        """
        caps = [
            {"item_id": "good_tool", "kind": "tool", "factory": "research",
             "description": "valid tool", "confidence": 0.5, "explicit": True***REMOVED***,
            {"item_id": "good_module", "kind": "module", "factory": "docs_10",
             "description": "valid module", "confidence": 0.5, "explicit": False***REMOVED***,
            {"item_id": "bad_service", "kind": "service",  # not in _KINDS
             "factory": "research", "description": "service kind rejected", "confidence": 0.5***REMOVED***,
            {"item_id": "bad_agent", "kind": "agent",  # not in _KINDS
             "factory": "research", "description": "agent kind rejected", "confidence": 0.5***REMOVED***,
            {"item_id": "bad_skill", "kind": "skill",  # not in _KINDS
             "factory": "research", "description": "skill kind rejected", "confidence": 0.5***REMOVED***,
        ***REMOVED***
        content = "```json\n" + json.dumps(caps) + "\n```"
        out = _parse_llm_response(content)
        assert len(out) == 2
        assert {item["item_id"***REMOVED*** for item in out***REMOVED*** == {"good_tool", "good_module"***REMOVED***


# ─── TestCapabilityGapReporterLLM (reused Reporter с pre_extracted_entries) ───


class TestCapabilityGapReporterLLM:
    """Reporter должен работать в LLM-пути через pre_extracted_entries."""

    def test_llm_path_skips_per_section_extraction(self):
        entries = {
            "research_web": ("tool", "research", "Web research"),
            "corpus_persistence": ("tool", "nil", "Corpus persistence"),
        ***REMOVED***
        reporter = CapabilityGapReporter(registry=None, pre_extracted_entries=entries)
        md = reporter.render([("(section A)", "web research"), ("(section B)", "corpus")***REMOVED***)
        assert "`research_web`" in md
        assert "`corpus_persistence`" in md
        summary_line = [l for l in md.splitlines() if "Уникальных требуемых" in l***REMOVED***[0***REMOVED***
        assert "**Уникальных требуемых capabilities:** 2" in summary_line

    def test_llm_path_treats_existing_registry(self, seed_registry):
        entries = {
            "research_web": ("tool", "research", "Web research"),  # implemented
            "lisa_estimator": ("tool", "research", "Lisa estimator"),  # registered
        ***REMOVED***
        reporter = CapabilityGapReporter(
            registry=seed_registry, pre_extracted_entries=entries,
        )
        md = reporter.render([("(LLM-extracted)", "web research lisa")***REMOVED***)
        # summary table reflects cross-check against seed_registry.
        assert "`implemented`" in md
        assert "`registered`" in md

    def test_no_extraction_when_pre_extracted_passed(self):
        # text содержит keyword match для taxonomy (research_web),
        # но pre_extracted_entries передаёт ДРУГОЙ item_id. Reporter не должен
        # добавить research_web автоматически (LLM-mode игнорирует keyword extraction).
        reporter = CapabilityGapReporter(
            registry=None,
            pre_extracted_entries={"only_llm_cap": ("tool", "nil", "only LLM")***REMOVED***,
        )
        md = reporter.render([("(section)", "web research URL")***REMOVED***)
        assert "`only_llm_cap`" in md
        assert "`research_web`" not in md

    def test_empty_pre_extracted_still_renders_empty_table(self):
        reporter = CapabilityGapReporter(registry=None, pre_extracted_entries={***REMOVED***)
        md = reporter.render([("(section)", "some text")***REMOVED***)
        assert "**Уникальных требуемых capabilities:** 0" in md
        # При пустом списке — сообщение «всё реализовано» (first-slice empty).
        assert "Все блокеры закрыты" in md or "Регистрация не требуется" in md

    def test_llm_path_renders_flat_list_not_per_section(self):
        """BLOCKER regression guard (per code-reviewer v5.189.55).

        LLM-path должен рендерить ``## 2. LLM-extracted capabilities (flat list)``,
        а НЕ ``## 2. Детализация по секциям`` с пустыми per-section (старый баг:
        для всех 17 секций VOCAL_TASK_FRAGMENT печаталось «Не требует новой capability»,
        дискредитируя весь отчёт).

        Без этого теста будущий «cleanup» может вернуть per-section rendering для LLM-path
        и все существующие тесты останутся зелёными — регресс не будет пойман.
        """
        entries = {
            "research_web": ("tool", "research", "Web research"),
            "corpus_persistence": ("tool", "nil", "Corpus persistence"),
        ***REMOVED***
        reporter = CapabilityGapReporter(registry=None, pre_extracted_entries=entries)
        md = reporter.render([("(section A)", "web research"), ("(section B)", "corpus")***REMOVED***)
        # Утверждение 1: flat-list header присутствует.
        assert "## 2. LLM-extracted capabilities (flat list)" in md
        # Утверждение 2: старое per-section поведение НЕ должно появляться.
        assert "## 2. Детализация по секциям" not in md
        assert "Не требует новой capability" not in md
        # Утверждение 3: оба item_id всё равно видны (через flat-list, не per-section).
        assert "`research_web`" in md
        assert "`corpus_persistence`" in md


# ─── TestCapabilityGapLlmExecutor (integration с FakeGateway) ────────────────


class TestCapabilityGapLlmExecutor:
    def test_executor_role_id_is_correct(self):
        assert CapabilityGapLlmExecutor.role_id == LLM_ROLE_ID == "capability_gap_auditor_llm"

    def test_executor_writes_report_on_valid_response(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": f"c{i***REMOVED***", "kind": "tool", "factory": "research",
             "description": f"cap-{i***REMOVED***", "confidence": 0.5, "explicit": i % 2 == 0***REMOVED***
            for i in range(20)
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [LLM_REPORT_FILE***REMOVED***
        assert (project.root / LLM_REPORT_FILE).is_file()
        # Gateway был вызван с правильными capability-тэгами.
        assert len(gateway.calls) == 1
        assert "plan" in gateway.calls[0***REMOVED***["capabilities"***REMOVED***
        # System prompt + user prompt содержат task.
        messages = gateway.calls[0***REMOVED***["messages"***REMOVED***
        assert any("expert платформенный" in m["content"***REMOVED*** for m in messages if m["role"***REMOVED*** == "system")
        assert any("VOCAL" in m["content"***REMOVED*** or "рынок вокала" in m["content"***REMOVED*** for m in messages if m["role"***REMOVED*** == "user")

    def test_executor_no_gateway_returns_empty(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        executor = CapabilityGapLlmExecutor(gateway=None, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [***REMOVED***
        assert not (project.root / LLM_REPORT_FILE).exists()

    def test_executor_short_text_returns_empty(self, project, empty_registry):
        (project.root / "задача.md").write_text("короткий текст", encoding="utf-8")
        gateway = _FakeGateway(content="```json\n[***REMOVED***\n```")
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [***REMOVED***

    def test_executor_no_task_file_returns_empty(self, project, empty_registry):
        executor = CapabilityGapLlmExecutor(
            gateway=_FakeGateway(content="..."), registry=empty_registry,
        )
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [***REMOVED***

    def test_executor_gateway_raises_returns_empty(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        gateway = _FakeGateway(raise_on_call=RuntimeError("simulated gateway crash"))
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [***REMOVED***  # ADR-016 fail-safe
        assert not (project.root / LLM_REPORT_FILE).exists()

    def test_executor_unparseable_response_returns_empty(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        gateway = _FakeGateway(content="No JSON here, just plain text response.")
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [***REMOVED***

    def test_executor_partial_corruption_drops_bad_keeps_good(
        self, project, empty_registry,
    ):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        # 3 валидных + 2 невалидных.
        mixed = [
            {"item_id": "good_1", "kind": "tool", "factory": "nil",
             "description": "ok-1", "confidence": 0.5, "explicit": True***REMOVED***,
            {"kind": "tool", "factory": "nil", "description": "no item_id"***REMOVED***,  # bad
            {"item_id": "good_2", "kind": "module", "factory": "docs_10",
             "description": "ok-2", "confidence": 0.7, "explicit": False***REMOVED***,
            None,  # bad
            {"item_id": "good_3", "kind": "role", "factory": "governance",
             "description": "ok-3", "confidence": 0.9, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(mixed))
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=empty_registry)
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [LLM_REPORT_FILE***REMOVED***
        content = (project.root / LLM_REPORT_FILE).read_text(encoding="utf-8")
        assert "`good_1`" in content
        assert "`good_2`" in content
        assert "`good_3`" in content
        assert "**Уникальных требуемых capabilities:** 3" in content


class TestCapabilityGapLlmExecutorQuality:
    """Качественный баръер per user: тот же VOCAL_TASK_FRAGMENT должен дать ≥18 capabilities."""

    def test_vocal_fragment_yields_ge_18_capabilities_pre_extracted_entries(self):
        """Тест на pre_extracted_entries (reused Reporter path)."""
        # Симулируем LLM, который нашёл 22 capabilities (15 курируемых + 7 INFERRED meta).
        curated_15 = [
            "research_web", "lisa_estimator", "qualitative_review_analyzer",
            "competitor_matrix_builder", "pricing_enumerator",
            "anti_pattern_miner", "mvp_design_wizard",
            "business_model_constructor", "hypothesis_ledger",
            "devil_advocate_pass", "claim_source_tracker",
            "vanity_metric_filter", "weighted_scoring_engine",
            "corpus_persistence", "persona_funnel_analyzer",
        ***REMOVED***
        inferred_meta_7 = [
            "execution_log",         # runtime logging (meta-infra)
            "model_benchmark",       # capability benchmark framework
            "experiment_tracker",    # A/B hypothesis tracking
            "dependency_resolver",   # capability graph DAG analysis
            "output_archiver",       # report archival across sessions
            "schema_validator",      # LLM JSON schema validation
            "cost_estimator",        # per-call credit budget tracking
        ***REMOVED***
        all_caps = curated_15 + inferred_meta_7
        assert len(all_caps) == 22

        entries = {
            cap: ("tool", "research", f"Capability {cap***REMOVED*** (inferred by fake LLM)")
            for cap in all_caps
        ***REMOVED***

        from core_02.capability_gap_auditor import _split_sections
        sections = _split_sections(VOCAL_TASK_FRAGMENT)
        reporter = CapabilityGapReporter(registry=None, pre_extracted_entries=entries)
        md = reporter.render(sections)

        # Считаем строки в таблице.
        table_section = md.split("## 1. Сводная таблица", 1)[1***REMOVED***.split("## 2.", 1)[0***REMOVED***
        rows = [l for l in table_section.splitlines() if l.startswith("| `")***REMOVED***
        assert len(rows) == 22, f"expected 22 capabilities; got {len(rows)***REMOVED***"
        # Качественный баръер: ≥18 (на 20%+ больше детерминированного).
        assert len(rows) >= 18, f"quality bar: LLM should give ≥18 caps vs deterministic 15"


class TestCapabilityAuditLlmRegistry:
    def test_factory_contains_llm_executor(self, empty_registry):
        reg = capability_audit_llm_executor_registry(
            gateway=_FakeGateway(content="..."), registry=empty_registry,
        )
        assert LLM_ROLE_ID in reg
        ex = reg.get(LLM_ROLE_ID)
        assert isinstance(ex, CapabilityGapLlmExecutor)
        assert ex._registry is empty_registry
        assert isinstance(ex._gateway, _FakeGateway)
        assert len(reg) == 1


# ─── No-mutation test (важно: executor НЕ мутирует registry) ────────────────


class TestCapabilityGapLlmExecutorNoSideEffects:
    def test_does_not_mutate_registry(self, seed_registry, project):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        before = sorted(seed_registry.list_all(), key=lambda i: i.item_id)
        caps = [{"item_id": f"c{i***REMOVED***", "kind": "tool", "factory": "research",
                 "description": f"cap {i***REMOVED***", "confidence": 0.5, "explicit": True***REMOVED***
                for i in range(20)***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))
        executor = CapabilityGapLlmExecutor(gateway=gateway, registry=seed_registry)
        executor.execute(project, LLM_ROLE_ID)
        after = sorted(seed_registry.list_all(), key=lambda i: i.item_id)
        assert [i.item_id for i in before***REMOVED*** == [i.item_id for i in after***REMOVED***


# ─── Reuse deterministic (regression: deterministic variant не сломан) ────────


class TestDeterministicVariantUnaffected:
    def test_deterministic_executor_still_works(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        ex = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = ex.execute(project, "capability_gap_auditor")
        assert created == ["capability_gap_report.md"***REMOVED***


# ─── Corpus context integration (v5.189.57) ────
#
# CapabilityGapLlmExecutor получает top-5 most-recent URLs из
# corpus_persistence.lookup_by_source(role_id) и инжектит их в user message
# as memory hint перед LLM-вызовом. ADR-016 fail-safe: empty / lookup-error /
# disabled → silently omit context block (no exceptions, no prompt noise).


class TestCorpusContextIntegration:
    """corpus_persistence → top-5 URLs injected into user message (memory hint)."""

    def test_corpus_context_injected_when_populated(
        self, monkeypatch, project, empty_registry,
    ):
        """5 entries в corpus → context block with all 5 URLs (newest first)."""
        from scripts_01 import corpus_persistence as cp_mod
        # 5 fake entries: timestamps so i=1 is newest, i=5 oldest.
        fake_entries = [
            cp_mod.CorpusEntry(
                url=f"https://prior{i***REMOVED***.example.com/",
                source=LLM_ROLE_ID,
                timestamp=f"2026-08-{20 - i:02d***REMOVED***T00:00:00Z",
                title=f"Prior Source {i***REMOVED***",
            )
            for i in range(1, 6)
        ***REMOVED***
        monkeypatch.setattr(
            cp_mod, "lookup_by_source",
            lambda source, *, root=None: fake_entries,
        )

        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": f"c{i***REMOVED***", "kind": "tool", "factory": "research",
             "description": f"cap {i***REMOVED***", "confidence": 0.5, "explicit": True***REMOVED***
            for i in range(20)
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
        )
        created = executor.execute(project, LLM_ROLE_ID)
        assert created == [LLM_REPORT_FILE***REMOVED***

        assert len(gateway.calls) == 1
        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***
        # Context header injected.
        assert "PRIOR CORPUS CONTEXT" in user_message
        # All 5 URLs listed.
        for i in range(1, 6):
            assert f"https://prior{i***REMOVED***.example.com/" in user_message
        # Order: newest first → prior1 before prior5.
        idx_1 = user_message.index("https://prior1.example.com/")
        idx_5 = user_message.index("https://prior5.example.com/")
        assert idx_1 < idx_5, (
            f"expected newest (prior1) before oldest (prior5); got idx_1={idx_1***REMOVED***, idx_5={idx_5***REMOVED***"
        )
        # Anti-anchoring framing present (defends against LLM over-anchoring).
        # Per code-reviewer v5.189.57 commit: STRONGER framing than "memory, NOT a constraint"
        # — production uses IMPERATIVE ("IGNORE these URLs… extract independently") which is
        # more robust against LLM over-anchoring. Tests pinned to production wording.
        assert "historical memory ONLY" in user_message
        assert "IGNORE these URLs" in user_message
        assert "extract capabilities independently" in user_message

    def test_corpus_context_omitted_when_empty(
        self, monkeypatch, project, empty_registry,
    ):
        """Empty corpus → NO context block; user message = LLM_USER_PROMPT + task only."""
        from scripts_01 import corpus_persistence as cp_mod
        monkeypatch.setattr(
            cp_mod, "lookup_by_source",
            lambda source, *, root=None: [***REMOVED***,
        )

        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": "c1", "kind": "tool", "factory": "research",
             "description": "x", "confidence": 0.5, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
        )
        executor.execute(project, LLM_ROLE_ID)

        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***
        # NO context block.
        assert "PRIOR CORPUS CONTEXT" not in user_message
        # Normal user prompt + task fragment still present.
        assert "рынок вокала" in user_message

    def test_corpus_context_omitted_on_lookup_failure(
        self, monkeypatch, project, empty_registry,
    ):
        """lookup_by_source raises → ADR-016 fail-safe: no exception, no context."""
        from scripts_01 import corpus_persistence as cp_mod

        def _boom(source, **kwargs):
            raise OSError("simulated disk failure")

        monkeypatch.setattr(cp_mod, "lookup_by_source", _boom)
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": "c1", "kind": "tool", "factory": "research",
             "description": "x", "confidence": 0.5, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
        )
        created = executor.execute(project, LLM_ROLE_ID)  # Must NOT raise
        # Research completed successfully despite corpus lookup failure.
        assert created == [LLM_REPORT_FILE***REMOVED***
        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***
        # Context block silently omitted; normal task prompt still present.
        assert "PRIOR CORPUS CONTEXT" not in user_message
        assert "рынок вокала" in user_message

    def test_corpus_context_disabled_in_init(
        self, monkeypatch, project, empty_registry,
    ):
        """corpus_context_enabled=False → lookup NOT called, no context block."""
        from scripts_01 import corpus_persistence as cp_mod

        lookup_calls: list = [***REMOVED***

        def _tracker(source, **kwargs):
            lookup_calls.append({"called": True***REMOVED***)
            return [***REMOVED***

        monkeypatch.setattr(cp_mod, "lookup_by_source", _tracker)

        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": "c1", "kind": "tool", "factory": "research",
             "description": "x", "confidence": 0.5, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
            corpus_context_enabled=False,
        )
        executor.execute(project, LLM_ROLE_ID)

        # Explicit opt-out: lookup NOT called.
        assert lookup_calls == [***REMOVED***
        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***
        assert "PRIOR CORPUS CONTEXT" not in user_message
        assert "рынок вокала" in user_message

    def test_corpus_context_dedup_by_url_newest_wins(
        self, monkeypatch, project, empty_registry,
    ):
        """URL dedup: 4 entries, 2 unique URLs → только 2 distinct URL в context, newest of each wins.

        Защита от регрессии dedup-логики: если future edit удалит dedup → прежние 6 тестов
        останутся зелёными (т.к. используют unique URLs). Этот тест гарантирует, что если
        entries содержит [url_A_old, url_A_new, url_B, url_A_old2***REMOVED***, итог = [url_A_new, url_B***REMOVED***
        (newest wins per URL).
        """
        from scripts_01 import corpus_persistence as cp_mod
        # 4 entries: 2 unique URLs (A и B), 2 старых варианта A.
        fake_entries = [
            cp_mod.CorpusEntry(
                url="https://url-a.example.com/v1",
                source=LLM_ROLE_ID,
                timestamp="2026-08-10T00:00:00Z",
                title="URL A v1 (oldest)",
            ),
            cp_mod.CorpusEntry(
                url="https://url-b.example.com/v1",
                source=LLM_ROLE_ID,
                timestamp="2026-08-15T00:00:00Z",
                title="URL B v1",
            ),
            cp_mod.CorpusEntry(
                url="https://url-a.example.com/v1",
                source=LLM_ROLE_ID,
                timestamp="2026-08-18T00:00:00Z",  # newest A wins
                title="URL A v1 (newest)",
            ),
            cp_mod.CorpusEntry(
                url="https://url-a.example.com/v1",
                source=LLM_ROLE_ID,
                timestamp="2026-08-12T00:00:00Z",  # middle A — should be dropped
                title="URL A v1 (middle)",
            ),
        ***REMOVED***
        monkeypatch.setattr(
            cp_mod, "lookup_by_source",
            lambda source, *, root=None: fake_entries,
        )

        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": "c1", "kind": "tool", "factory": "research",
             "description": "x", "confidence": 0.5, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
        )
        executor.execute(project, LLM_ROLE_ID)
        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***

        # Counts: exactly 2 distinct URLs (A и B).
        url_a_count = user_message.count("https://url-a.example.com/v1")
        url_b_count = user_message.count("https://url-b.example.com/v1")
        # А появляется ровно 1 раз (newest), В — 1 раз. Дубликаты A (oldest, middle) — dropped.
        assert url_a_count == 1, (
            f"expected URL A exactly once (newest); got {url_a_count***REMOVED*** occurrences. "
            f"Dedup broken."
        )
        assert url_b_count == 1, f"expected URL B once; got {url_b_count***REMOVED***"
        # Newest A wins. URL A v1 (newest) присутствует, остальные — нет.
        assert "URL A v1 (newest)" in user_message
        assert "URL A v1 (oldest)" not in user_message
        assert "URL A v1 (middle)" not in user_message
        # B appears once.
        assert "URL B v1" in user_message
        # Anti-anchoring framing присутствует (regression guard).
        # Pinned to production's stronger wording (v5.189.57 code-reviewer финал).
        assert "historical memory ONLY" in user_message
        assert "IGNORE these URLs" in user_message
        assert "extract capabilities independently" in user_message
        # Post-dedup order assertion (newest first): URL A v1 (newest) precedes URL B.
        idx_a = user_message.index("URL A v1 (newest)")
        idx_b = user_message.index("URL B v1")
        assert idx_a < idx_b, (
            f"expected newest URL A before URL B; got idx_a={idx_a***REMOVED***, idx_b={idx_b***REMOVED***"
        )

    def test_corpus_context_limits_to_top_5(
        self, monkeypatch, project, empty_registry,
    ):
        """If corpus has > 5 entries → only top-5 (newest) included; rest omitted."""
        from scripts_01 import corpus_persistence as cp_mod
        # Couple fakes с _CORPUS_CONTEXT_TOP_K: total = TOP_K + 5 (чтобы verify tail truncation).
        # Если constant → N, нужно N TOP_K entries + 5 extras dropped.
        total = _CORPUS_CONTEXT_TOP_K + 5
        fake_entries = [
            cp_mod.CorpusEntry(
                url=f"https://cap{i***REMOVED***.example.com/",
                source=LLM_ROLE_ID,
                timestamp=f"2026-08-{20 - i:02d***REMOVED***T00:00:00Z",
                title=f"Cap {i***REMOVED***",
            )
            for i in range(1, total + 1)
        ***REMOVED***
        monkeypatch.setattr(
            cp_mod, "lookup_by_source",
            lambda source, *, root=None: fake_entries,
        )

        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": f"c{i***REMOVED***", "kind": "tool", "factory": "research",
             "description": f"cap {i***REMOVED***", "confidence": 0.5, "explicit": True***REMOVED***
            for i in range(20)
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
        )
        executor.execute(project, LLM_ROLE_ID)
        user_message = gateway.calls[0***REMOVED***["messages"***REMOVED***[1***REMOVED***["content"***REMOVED***
        # Top-_CORPUS_CONTEXT_TOP_K (newest first): cap1..capTOP_K included.
        for i in range(1, _CORPUS_CONTEXT_TOP_K + 1):
            assert f"https://cap{i***REMOVED***.example.com/" in user_message, (
                f"expected cap{i***REMOVED*** (top-{_CORPUS_CONTEXT_TOP_K***REMOVED***) in user_message"
            )
        # capTOP_K+1..total — omitted.
        for i in range(_CORPUS_CONTEXT_TOP_K + 1, total + 1):
            assert f"https://cap{i***REMOVED***.example.com/" not in user_message, (
                f"cap{i***REMOVED*** (beyond TOP_K={_CORPUS_CONTEXT_TOP_K***REMOVED***) should be truncated"
            )

    def test_corpus_root_propagated_to_lookup(self, monkeypatch, project, tmp_path):
        """corpus_root=tmp_path → lookup_by_source получает root=tmp_path (DI)."""
        from scripts_01 import corpus_persistence as cp_mod

        captured_roots: list = [***REMOVED***
        fake_entry = cp_mod.CorpusEntry(
            url="https://custom-root.example.com/",
            source=LLM_ROLE_ID,
            timestamp="2026-08-19T00:00:00Z",
            title="Custom Root",
        )

        def _capture_root(source, *, root=None):
            captured_roots.append(root)
            return [fake_entry***REMOVED***

        monkeypatch.setattr(cp_mod, "lookup_by_source", _capture_root)
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        caps = [
            {"item_id": "c1", "kind": "tool", "factory": "research",
             "description": "x", "confidence": 0.5, "explicit": True***REMOVED***,
        ***REMOVED***
        gateway = _FakeGateway(content=_make_fake_gateway_response(caps))

        executor = CapabilityGapLlmExecutor(
            gateway=gateway, registry=empty_registry,
            corpus_root=tmp_path,
        )
        executor.execute(project, LLM_ROLE_ID)

        # lookup получил root=tmp_path (НЕ None / НЕ default DEFAULT_CORPUS_DIR).
        assert len(captured_roots) == 1
        assert captured_roots[0***REMOVED*** == tmp_path
