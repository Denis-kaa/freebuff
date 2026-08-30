"""tests_09/test_capability_gap_auditor.py — CapabilityGapAuditorExecutor (ADR-016 style).

Per code-reviewer guidance (thinker round): deterministic + DI testability +
no-side-effects. Без сети, без LLM — keyword/regex-матч по курируемой таксономии
+ cross-check против in-memory MissingRegistry.

Pattern follows tests_09/test_role_executor.py (DI через _FakeGateway style).
"""

from __future__ import annotations

}
import subprocess
import sys
}

import pytest

from core_02.capability_gap_auditor import (
    REPORT_FILE,
    CapabilityGapAuditorExecutor,
    CapabilityGapReporter,
    _extract_capabilities_from_text,
    _split_sections,
    capability_audit_executor_registry,
)
from core_02.missing_registry import (
    IMPLEMENTED,
    REGISTERED,
    MissingRegistry,
)
from core_02.workspace import Project


# ─── helpers ────────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path) -> Project:
    """Минимальный Project с project.yaml и без task-файла (для negative-tests)."""
    p = tmp_path / "auditor_test_project"
    p.mkdir()
    (p / "project.yaml").write_text(
        "name: auditor_test_project\ntype: script\n", encoding="utf-8"
    )
    return Project.load(p)


@pytest.fixture
def empty_registry(tmp_path) -> MissingRegistry:
    return MissingRegistry(tmp_path / "missing_registry.yaml")


@pytest.fixture
def seed_registry(empty_registry) -> MissingRegistry:
    """Реестр с 3 элементами в разных статусах (для cross-check тестов)."""
    empty_registry.register_missing(
        "research_web", kind="tool", factory="research",
        description="Web research (уже реализован)",
        status=IMPLEMENTED,
        implementation="scripts_01/research_web.py",
        backfill=True,
    )
    empty_registry.register_missing(
        "lisa_estimator", kind="tool", factory="research",
        description="Estimation (в реестре, не реализован)",
        status=REGISTERED,
    )
    empty_registry.register_missing(
        "hypothesis_ledger", kind="module", factory="docs_10",
        description="Hypothesis ledger",
        status="prompt_written",
        prompt_path="pompts_11/077_19_hypothesis_ledger.md",
    )
    return empty_registry


# Sample task fragments per "observation" requirements.
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
    "## 12. Claim source tracker [fact] vs [observation] vs [hypothesis]\n"
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


# ─── _split_sections ─────────────────────────────────────────────────────────


class TestSplitSections:
    def test_no_headings_returns_single_section(self):
        text = (
            "Просто текст без заголовков. Достаточно длинный для пробелов и слов, "
            "чтобы _MIN_BODY_LEN не отсеял его и _split_sections сработал чисто."
        )
        out = _split_sections(text)
        assert len(out) == 1
        assert out[0][1].strip() == text.strip()

    def test_h2_numbered_sections(self):
        out = _split_sections(VOCAL_TASK_FRAGMENT)
        # Минимум 12 секций (preamble + 17 numbered).
        assert len(out) >= 12
        # Проверяем, что ключевые секции распознались.
        bodies = " ".join(body for _, body in out)
        assert "Контекст" in bodies
        assert "Unit economics" in bodies or "калибровка" in bodies

    def test_various_marker_styles(self):
        text = (
            "## 1. Section\nFoo.\n\n"
            "## 2) Section\nBar.\n\n"
            "# 3. Section\nBaz.\n\n"
            "# IV. Section\nQux.\n\n"
            "## (5) Section\nQuux.\n"
        )
        out = _split_sections(text)
        assert len(out) == 5


# ─── _extract_capabilities_from_text ─────────────────────────────────────────


class TestExtractCapabilities:
    def test_vocal_fragment_extracts_expected_set(self):
        found = [item_id for item_id, *_ in _extract_capabilities_from_text(VOCAL_TASK_FRAGMENT)]
        expected_subset = {
            "research_web",
            "lisa_estimator",
            "qualitative_review_analyzer",
            "competitor_matrix_builder",
            "pricing_enumerator",
            "anti_pattern_miner",
            "mvp_design_wizard",
            "business_model_constructor",
            "hypothesis_ledger",
            "devil_advocate_pass",
            "claim_source_tracker",
            "vanity_metric_filter",
            "weighted_scoring_engine",
            "corpus_persistence",
            "persona_funnel_analyzer",
        }
        found_set = set(found)
        missing = expected_subset - found_set
        assert not missing, f"expected to extract {missing}, but found {found_set}"

    def test_unrelated_text_extracts_nothing_critical(self):
        text = (
            "Сегодня хорошая погода. Сходил в магазин за молоком и хлебом. "
            "Никаких специальных терминов из таксономии здесь нет, длинный текст для body."
        )
        found_ids = {x[0] for x in _extract_capabilities_from_text(text)}
        block = {"research_web", "claim_source_tracker", "corpus_persistence"}
        assert not (found_ids & block), (
            f"unexpected block-cap hit on unrelated text: {found_ids & block}"
        )

    def test_claim_source_tracker_new_phrasings(self):
        """Каждое существенное утверждение подкреплять источником / не выдавать предположение за факт --- new regex branches added (v5.189.61)."""
        text = (
            "## Инструкция по фактчеку\n"
            "Важно каждое существенное утверждение подкреплять источником.\n"
            "Кроме того, старайся не выдавать предположение за факт.\n"
            "Остальной текст не содержит других capabilities."
        )
        found_ids = {x[0] for x in _extract_capabilities_from_text(text)}
        assert found_ids == {"claim_source_tracker"}

    def test_dedupe_by_item_id(self):
        text = "см. также web research. web page. URL и web research ещё раз."
        found = _extract_capabilities_from_text(text)
        ids = [x[0] for x in found]
        assert len(ids) == len(set(ids))


# ─── CapabilityGapReporter ──────────────────────────────────────────────────


def _strip_bash_comments(bash: str) -> str:
    """Helper: strip '# ...' comment lines."""
    return "\n".join(
        line for line in bash.splitlines() if not line.lstrip().startswith("#")
    )


def _extract_first_slice(md: str) -> list:
    """Извлекает только numbered first-slice items из rendered-report."""
    section = md.split("## 4.", 1)[1].split("## 5.", 1)[0]
    return re.findall(r"^\d+\.\s+`(\w+)`", section, re.MULTILINE)


class TestCapabilityGapReporter:
    def test_renders_summary_table_with_status_columns(self, seed_registry):
        reporter = CapabilityGapReporter(registry=seed_registry)
        sections = [
            ("Web Research", "web research URL"),
            ("Unit economics", "calibration teacher time"),
            ("Hypothesis tracking", "hypothesis ledger kill-criteria"),
        ]
        md = reporter.render(sections)
        assert "## 1. Сводная таблица" in md
        assert "| `research_web`" in md
        assert "`implemented`" in md
        assert "`registered`" in md
        assert "`prompt_written`" in md

    def test_uses_first_slice_blocker_priority(self, seed_registry):
        reporter = CapabilityGapReporter(registry=seed_registry)
        sections = [
            ("web", "web research url"),
            ("est", "calibration teacher time"),
            ("hyp", "hypothesis ledger kill-criteria"),
            ("anti", "anti-pattern mining заброшенные школы"),
        ]
        md = reporter.render(sections)
        first_slice_items = _extract_first_slice(md)
        assert first_slice_items, "first-slice list missing"
        # Первым по приоритету — anti_pattern_miner (absent, P0).
        assert first_slice_items[0] == "anti_pattern_miner"
        # research_web (implemented) НЕ попадает в first-slice.
        assert "research_web" not in first_slice_items
        # Блокеры в правильном порядке: absent → registered → prompt_written.
        assert "lisa_estimator" in first_slice_items
        assert "hypothesis_ledger" in first_slice_items
        assert len(first_slice_items) <= 3

    def test_paste_friendly_commands_use_registry_cli(self, seed_registry):
        reporter = CapabilityGapReporter(registry=seed_registry)
        # Берём только absent-кап, чтобы получить детерминированную команду.
        sections = [("anti", "anti-pattern mining заброшенные школы")]
        md = reporter.render(sections)
        assert "```bash" in md
        bash = md.split("```bash\n", 1)[1].split("```", 1)[0]
        assert "python -m core_02.missing_registry register" in bash
        assert "anti_pattern_miner" in bash
        assert "--kind tool" in bash
        assert "--factory research" in bash
        assert "--description" in bash

    def test_implemented_capabs_skipped_in_register_block(self, seed_registry):
        reporter = CapabilityGapReporter(registry=seed_registry)
        sections = [("web", "web research url")]
        md = reporter.render(sections)
        if "```bash" in md:
            bash = md.split("```bash\n", 1)[1].split("```", 1)[0]
            non_comment = _strip_bash_comments(bash)
            assert "register research_web" not in non_comment
        else:
            assert "Регистрация не требуется" in md

    def test_no_side_effects_on_injected_registry(self, seed_registry):
        reporter = CapabilityGapReporter(registry=seed_registry)
        before = sorted(seed_registry.list_all(), key=lambda i: i.item_id)
        for _ in range(3):
            reporter.render([("web", "web research url")])
        after = sorted(seed_registry.list_all(), key=lambda i: i.item_id)
        assert [i.item_id for i in before] == [i.item_id for i in after]
        assert [i.status for i in before] == [i.status for i in after]

    def test_handles_registry_none_gracefully(self):
        reporter = CapabilityGapReporter(registry=None)
        md = reporter.render([("web", "web research url")])
        assert "(registry=None)" in md or "registry=None" in md


# ─── CapabilityGapAuditorExecutor ───────────────────────────────────────────


class TestCapabilityGapAuditorExecutor:
    def test_execute_writes_report_for_real_task(self, project, empty_registry):
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == [REPORT_FILE]
        out = project.root / REPORT_FILE
        assert out.is_file()
        content = out.read_text(encoding="utf-8")
        assert "## 1." in content
        assert "## 4." in content
        assert "python -m core_02.missing_registry register" in content
        # research_web — НЕ implemented в empty_registry → register-команда для него есть.
        assert "register research_web" in content

    def test_execute_marks_implemented_correctly(self, project, seed_registry):
        (project.root / "brief.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=seed_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == [REPORT_FILE]
        content = (project.root / REPORT_FILE).read_text(encoding="utf-8")
        bash_block_match = re.search(r"```bash\n(.*?)```", content, re.DOTALL)
        assert bash_block_match, "expected bash block in report"
        bash = bash_block_match.group(1)
        bash_no_comments = _strip_bash_comments(bash)
        # research_web (implemented) → НЕ должно быть register-команды.
        assert "register research_web" not in bash_no_comments
        # А вот anti_pattern_miner (absent) — должна быть.
        assert "register anti_pattern_miner" in bash_no_comments

    def test_execute_fail_safe_on_missing_input(self, project, empty_registry):
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == []
        assert not (project.root / REPORT_FILE).exists()

    def test_execute_fail_safe_on_short_input(self, project, empty_registry):
        (project.root / "brief.md").write_text("короткий текст", encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == []

    def test_execute_at_min_length_returns_report(self, project, empty_registry):
        # Текст РОВНО на границе _MIN_BODY_LEN (=60). Длина рассчитывается из длины
        # префикса программно, чтобы избежать off-by-one при редактировании.
        prefix = "Min body length на границе "  # 27 chars (вычислено ниже через len)
        exactly_min = prefix + "a" * (60 - len(prefix))
        assert len(exactly_min) == 60, (
            f"Фикстура должна быть строго 60 chars, got {len(exactly_min)}"
        )
        (project.root / "задача.md").write_text(exactly_min, encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == [REPORT_FILE]
        assert (project.root / REPORT_FILE).is_file()

    def test_execute_below_min_length_returns_empty(self, project, empty_registry):
        # 59 chars (на 1 ниже _MIN_BODY_LEN=60) → execute fail-safe → [].
        below_min = "a" * 59
        assert len(below_min.strip()) == 59
        (project.root / "задача.md").write_text(below_min, encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == []
        assert not (project.root / REPORT_FILE).exists()

    def test_executor_returns_relative_path_only(self, project, empty_registry):
        # ADR-016 контракт: execute() → ["filename"] relative к project.root.
        (project.root / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        executor = CapabilityGapAuditorExecutor(registry=empty_registry)
        created = executor.execute(project, "capability_gap_auditor")
        assert created == [REPORT_FILE]
        # Никаких абсолютных путей или path-traversal.
        for path_str in created:
            assert "/" not in path_str and "\\" not in path_str, (
                f"ADR-016: возвращаемый путь должен быть relative, got {path_str!r}"
            )

    def test_executor_role_id_is_correct(self):
        assert CapabilityGapAuditorExecutor.role_id == "capability_gap_auditor"

    def test_capability_audit_executor_registry_contains_executor(self, empty_registry):
        reg = capability_audit_executor_registry(registry=empty_registry)
        assert "capability_gap_auditor" in reg
        ex = reg.get("capability_gap_auditor")
        assert isinstance(ex, CapabilityGapAuditorExecutor)
        assert ex._registry is empty_registry  # DI сохранён
        assert len(reg) == 1


# ─── CLI (subprocess smoke) ─────────────────────────────────────────────────


class TestCLI:
    def test_cli_audit_writes_report(self, tmp_path, empty_registry):
        project_dir = tmp_path / "cli_project"
        project_dir.mkdir()
        (project_dir / "project.yaml").write_text(
            "name: cli_project\ntype: script\n", encoding="utf-8"
        )
        (project_dir / "задача.md").write_text(VOCAL_TASK_FRAGMENT, encoding="utf-8")
        cmd = [
            sys.executable, "-m", "core_02.capability_gap_auditor",
            "audit", str(project_dir),
            "--registry", str(empty_registry.path),
            "--no-write",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0, f"CLI stderr: {result.stderr}"
        assert "Capability Gap Audit Report" in result.stdout
        assert "```bash" in result.stdout
