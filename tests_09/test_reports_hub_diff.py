#!/usr/bin/env python3
"""Tests for Reports Hub diff между генерациями (спека §12, тест 4: test_diff).

Синтетические две модели → ожидаемые бейджи и сводка; history round-trip
(save/load); сквозной diff через generate_site (две генерации подряд).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.report.diff import (
    ModelDiff,
    diff_models,
    history_path,
    load_history,
    save_history,
)
from services_08.reports_hub.report.generate import generate_site
from services_08.reports_hub.report.model import (
    DocCard,
    MetricTile,
    ReportModel,
    ReportSection,
    TimelineEntry,
)
from services_08.reports_hub.report.render import render_index, render_project_page
from services_08.reports_hub.report.summaries import slugify


def _model(
    *,
    stages: int,
    tests: str,
    docs: list[str],
    roadmap_items: list[str],
    generated_at: str = "2026-09-16",
) -> ReportModel:
    """Синтетическая модель с параметризованным наполнением."""
    return ReportModel(
        slug="demo",
        title="Demo",
        generated_at=generated_at,
        exec_summary="резюме",
        metrics=[MetricTile(label="тесты", value=tests, source="status.md:1")],
        timeline=[TimelineEntry(title=f"Этап {i}", result="ок") for i in range(stages)],
        sections=[ReportSection(name="roadmap", items=list(roadmap_items))],
        docs=[
            DocCard(filename=name, doc_type="status", summary="резюме дока")
            for name in docs
        ],
    )


class TestDiffModels:
    def test_first_generation(self) -> None:
        diff = diff_models(_model(stages=3, tests="249 passed", docs=["a.md"], roadmap_items=["x"]), None)
        assert diff.first_generation
        assert diff.summary() == "первая генерация"
        assert not diff.has_changes()

    def test_changes_detected(self) -> None:
        previous = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        current = _model(
            stages=4,
            tests="261 passed",
            docs=["a.md", "b.md"],
            roadmap_items=["H1", "H2", "H3"],
        )
        diff = diff_models(current, previous)
        assert diff.has_changes()
        assert diff.timeline_added == 2
        assert diff.docs_added == ["b.md"]
        assert diff.docs_removed == []
        changes = {change.label: (change.before, change.after) for change in diff.metric_changes}
        assert changes["тесты"] == ("249 passed", "261 passed")
        assert ("roadmap", 1, 3) in diff.item_deltas

    def test_summary_format(self) -> None:
        previous = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        current = _model(stages=4, tests="261 passed", docs=["a.md", "b.md"], roadmap_items=["H1"])
        diff = diff_models(current, previous)
        text = diff.summary()
        assert "+2 этапов" in text
        assert "тесты 249 passed→261 passed" in text
        assert "+1 новых доков" in text

    def test_removed_docs_and_sections(self) -> None:
        previous = _model(stages=1, tests="249 passed", docs=["a.md", "old.md"], roadmap_items=["H1", "H9"])
        current = _model(stages=1, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        diff = diff_models(current, previous)
        assert diff.docs_removed == ["old.md"]
        assert diff.removed_sections == []
        # Удаление — тоже содержательное изменение (спека §11: −N, осиротевшие).
        assert diff.has_changes()
        assert "−1 доков" in diff.summary()

    def test_no_changes_identical(self) -> None:
        model = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        diff = diff_models(model, model)
        assert not diff.has_changes()
        assert diff.summary() == "без изменений"

    def test_to_json_shape(self) -> None:
        diff = ModelDiff(slug="demo", timeline_added=1)
        payload = diff.to_json()
        assert payload["slug"] == "demo"
        assert payload["timeline_added"] == 1
        assert "summary" in payload


class TestHistoryPersistence:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        model = _model(stages=3, tests="249 passed", docs=["a.md"], roadmap_items=["x"])
        path = save_history(tmp_path, model)
        assert path == history_path(tmp_path, model.slug)
        restored = load_history(tmp_path, model.slug)
        assert restored == model

    def test_load_missing_or_broken(self, tmp_path: Path) -> None:
        assert load_history(tmp_path, "nope") is None
        path = history_path(tmp_path, "broken")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{не json", encoding="utf-8")
        assert load_history(tmp_path, "broken") is None

    def test_future_schema_version_rejected(self, tmp_path: Path) -> None:
        model = _model(stages=1, tests="x", docs=[], roadmap_items=[])
        path = history_path(tmp_path, model.slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = model.to_json()
        payload["schema_version"] = 999
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert load_history(tmp_path, model.slug) is None


class TestDiffRender:
    def test_project_page_diff_block(self) -> None:
        model = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        previous = _model(stages=1, tests="249 passed", docs=["a.md"], roadmap_items=["H1"], generated_at="2026-09-15")
        diff = diff_models(model, previous)
        page = render_project_page(model, diff)
        assert 'class="diff-block"' in page
        assert "badge-new" in page
        assert "+1 этапов" in page

    def test_project_page_without_diff(self) -> None:
        model = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        page = render_project_page(model)
        # CSS-класс есть на каждой странице (inline CSS), но блока diff быть не должно.
        assert '<div class="diff-block"' not in page

    def test_index_diff_note_and_badge(self) -> None:
        from services_08.reports_hub.report.render import SiteModel

        model = _model(stages=2, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        previous = _model(stages=1, tests="249 passed", docs=["a.md"], roadmap_items=["H1"])
        diff = diff_models(model, previous)
        site = SiteModel(generated_at="2026-09-16", projects=[model], diffs={model.slug: diff})
        index = render_index(site)
        assert "badge-new" in index
        assert "+1 этапов" in index

    def test_doc_card_added_not_marked(self) -> None:
        # Бейдж NEW на карточке дока — контракт _doc_grid: только docs_added подсвечены.
        model = _model(stages=1, tests="x", docs=["old.md", "new.md"], roadmap_items=[])
        previous = _model(stages=1, tests="x", docs=["old.md"], roadmap_items=[])
        diff = diff_models(model, previous)
        assert diff.docs_added == ["new.md"]
        page = render_project_page(model, diff)
        # Оба дока рендерятся (карточки не теряются)
        assert "old.md" in page and "new.md" in page


class TestDiffThroughGenerate:
    def test_two_generations_produce_diff(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        project_dir = projects_root / "demo"
        project_dir.mkdir(parents=True)
        (project_dir / "reports_hub.yaml").write_text(
            "title: Demo\n"
            'docs:\n  - "PROJECT_STATUS_REPORT.md"\n'
            'timeline_sources:\n  - "PROJECT_STATUS_REPORT.md"\n',
            encoding="utf-8",
        )
        status = (
            "# PROJECT_STATUS_REPORT\n\n"
            "> Дата: 2026-09-16 · Состояние: **249 тестов зелёные**\n\n"
            "## 1. Этапы\n\n"
            "| # | Этап | Коммит | Дата | Ядро |\n"
            "|---|---|---|---|---|\n"
            "| 1 | Первый | `aaa` | 09-16 | старт |\n"
        )
        (project_dir / "PROJECT_STATUS_REPORT.md").write_text(status, encoding="utf-8")

        site_root = tmp_path / "site"
        first = generate_site(projects_root, site_root)
        assert first.projects == 1
        first_diff = first.diffs[slugify("demo")]
        assert first_diff.first_generation

        # Вторая генерация: тот же контент → «без изменений».
        second = generate_site(projects_root, site_root)
        second_diff = second.diffs[slugify("demo")]
        assert not second_diff.first_generation
        assert not second_diff.has_changes()
        assert "без изменений" in second_diff.summary()

    def test_history_survives_regeneration(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        project_dir = projects_root / "demo"
        project_dir.mkdir(parents=True)
        (project_dir / "reports_hub.yaml").write_text(
            "title: Demo\n"
            'docs:\n  - "PROJECT_STATUS_REPORT.md"\n'
            'timeline_sources:\n  - "PROJECT_STATUS_REPORT.md"\n',
            encoding="utf-8",
        )
        (project_dir / "PROJECT_STATUS_REPORT.md").write_text(
            "# S\n\n> Дата: 2026-09-16 · Состояние: **1 тест зелёный**\n",
            encoding="utf-8",
        )
        site_root = tmp_path / "site"
        generate_site(projects_root, site_root)
        assert history_path(site_root, "demo").exists()
        assert load_history(site_root, "demo") is not None
