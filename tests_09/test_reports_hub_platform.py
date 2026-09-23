#!/usr/bin/env python3
"""Tests for platform report (спека §7.3, H5): секции, метрики, деградация.

Синтетический корень платформы (TASK.md / CHANGELOG.md / missing_registry /
docs_10) → ожидаемые секции и плитки; отсутствующие источники → «источник
отсутствует» (правило §11); рендер содержит прогресс-бар; --platform через
generate_site пишет platform/index.html.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.extract.registry import read_registry_summary
from services_08.reports_hub.report.generate import generate_site
from services_08.reports_hub.report.platform_report import build_platform_report
from services_08.reports_hub.report.render import render_platform_page


def _make_platform_root(root: Path) -> Path:
    """Синтетический корень платформы: TASK, CHANGELOG, реестр, docs_10."""
    (root / "data_13").mkdir(parents=True, exist_ok=True)
    (root / "docs_10" / "decisions").mkdir(parents=True, exist_ok=True)
    (root / "docs_10" / "audits").mkdir(parents=True, exist_ok=True)
    (root / "TASK.md").write_text(
        "# TASK\n\n## 5.1 Flutter\n- [ ] сделать приложение\n- [ ] вторая задача\n"
        "- [x] закрытая задача (не считается)\n",
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [5.189.88] — 2026-09-16\n\n- H1 каркас\n\n"
        "## [5.189.67] — 2026-08-20\n\n- версия-sync\n",
        encoding="utf-8",
    )
    (root / "data_13" / "missing_registry.yaml").write_text(
        "schema_version: 1\nitems:\n  - slug: a\n    status: implemented\n"
        "  - slug: b\n    status: implemented\n  - slug: c\n    status: registered\n",
        encoding="utf-8",
    )
    (root / "docs_10" / "decisions" / "ADR-010-remote-sync.md").write_text("# ADR", encoding="utf-8")
    (root / "docs_10" / "audits" / "AUDIT_2026-07-29.md").write_text("# audit", encoding="utf-8")
    return root


class TestPlatformReport:
    def test_sections_and_metrics(self, tmp_path: Path) -> None:
        root = _make_platform_root(tmp_path)
        model, registry = build_platform_report(root, generated_at="2026-09-16", python_exe=sys.executable)
        names = {section.name for section in model.sections}
        assert {"tasks", "releases", "registry", "docs10"} <= names
        tasks = next(s for s in model.sections if s.name == "tasks")
        assert len(tasks.items) == 2  # только открытые чекбоксы
        releases = next(s for s in model.sections if s.name == "releases")
        assert releases.items[0].startswith("5.189.88")
        registry_section = next(s for s in model.sections if s.name == "registry")
        assert "implemented: 2" in registry_section.items
        assert registry.total == 3
        assert registry.by_status["implemented"] == 2
        labels = {tile.label for tile in model.metrics}
        assert "тесты (collect-only)" in labels
        assert "реестр возможностей" in labels
        assert any(tile.label.startswith("docs_10") for tile in model.metrics)

    def test_missing_sources_degrade_honestly(self, tmp_path: Path) -> None:
        model, registry = build_platform_report(tmp_path, generated_at="x", python_exe=sys.executable)
        assert not registry.available
        assert any("MissingRegistry недоступен" in d for d in model.diagnostics)
        tasks = next(s for s in model.sections if s.name == "tasks")
        assert tasks.items == ["источник отсутствует"]
        releases = next(s for s in model.sections if s.name == "releases")
        assert releases.items == ["источник отсутствует"]
        # Метрики остаются (§11) — плитки не пустые.
        assert model.metrics

    def test_render_platform_page_progress_bar(self, tmp_path: Path) -> None:
        root = _make_platform_root(tmp_path)
        model, registry = build_platform_report(root, generated_at="2026-09-16", python_exe=sys.executable)
        page = render_platform_page(model, registry)
        assert "progress-bar" in page
        assert "2/3" in page
        assert "Платформа Workspace OS" in page
        assert "Открытые задачи" in page
        assert "Лента релизов" in page

    def test_render_without_registry_no_progress(self, tmp_path: Path) -> None:
        model, _ = build_platform_report(tmp_path, generated_at="x", python_exe=sys.executable)
        page = render_platform_page(model)
        # CSS-класс есть на каждой странице (inline CSS), но блока прогресса быть не должно.
        assert '<div class="progress-bar"' not in page

    def test_registry_summary_direct(self, tmp_path: Path) -> None:
        root = _make_platform_root(tmp_path)
        summary = read_registry_summary(root / "data_13" / "missing_registry.yaml")
        assert summary.available
        assert summary.total == 3


class TestPlatformThroughGenerate:
    def test_generate_platform_flag_writes_page(self, tmp_path: Path) -> None:
        root = _make_platform_root(tmp_path)
        (root / "projects_17" / "demo").mkdir(parents=True)
        (root / "projects_17" / "demo" / "reports_hub.yaml").write_text(
            "title: Demo\n"
            'docs:\n  - "PROJECT_STATUS_REPORT.md"\n'
            'timeline_sources:\n  - "PROJECT_STATUS_REPORT.md"\n',
            encoding="utf-8",
        )
        (root / "projects_17" / "demo" / "PROJECT_STATUS_REPORT.md").write_text(
            "# S\n\n> Дата: 2026-09-16 · Состояние: **249 тестов зелёные**\n",
            encoding="utf-8",
        )
        result = generate_site(
            root / "projects_17",
            tmp_path / "site",
            include_platform=True,
        )
        platform_page = tmp_path / "site" / "platform" / "index.html"
        assert platform_page.exists()
        html_text = platform_page.read_text(encoding="utf-8")
        assert "Платформа Workspace OS" in html_text
        assert result.projects == 1

    def test_generate_without_platform_no_page(self, tmp_path: Path) -> None:
        root = _make_platform_root(tmp_path)
        (root / "projects_17" / "demo").mkdir(parents=True)
        (root / "projects_17" / "demo" / "reports_hub.yaml").write_text(
            "title: Demo\ndocs:\n  - \"PROJECT_STATUS_REPORT.md\"\ntimeline_sources:\n  - \"PROJECT_STATUS_REPORT.md\"\n",
            encoding="utf-8",
        )
        (root / "projects_17" / "demo" / "PROJECT_STATUS_REPORT.md").write_text(
            "# S\n\n> Дата: 2026-09-16 · Состояние: **1 тест зелёный**\n",
            encoding="utf-8",
        )
        generate_site(root / "projects_17", tmp_path / "site")
        assert not (tmp_path / "site" / "platform" / "index.html").exists()
