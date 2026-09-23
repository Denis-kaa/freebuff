#!/usr/bin/env python3
"""Tests for Reports Hub discovery (спека §12, тест 5: test_discovery).

Tmp-дерево projects_17: проект с доками / без доков / с битым yaml / excluded.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.config import discover_projects


def _make_project(root: Path, name: str, files: dict[str, str]) -> Path:
    """Создать каталог проекта с файлами (возвращает путь)."""
    project_dir = root / name
    project_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (project_dir / filename).write_text(content, encoding="utf-8")
    return project_dir


class TestDiscovery:
    def test_project_with_docs_detected(self, tmp_path: Path) -> None:
        _make_project(tmp_path, "proj_docs", {"PROJECT_STATUS_REPORT.md": "# status\n"})
        profiles = discover_projects(tmp_path)
        by_slug = {p.slug: p for p in profiles}
        assert by_slug["proj_docs"].has_report_docs is True
        assert by_slug["proj_docs"].invalid_reason == ""
        assert by_slug["proj_docs"].excluded is False

    def test_project_without_docs_marked_no_data(self, tmp_path: Path) -> None:
        _make_project(tmp_path, "proj_empty", {"README.md": "# hi\n"})
        profiles = discover_projects(tmp_path)
        by_slug = {p.slug: p for p in profiles}
        assert by_slug["proj_empty"].has_report_docs is False
        assert by_slug["proj_empty"].invalid_reason == ""

    def test_broken_yaml_marks_invalid(self, tmp_path: Path) -> None:
        _make_project(
            tmp_path,
            "proj_broken",
            {"reports_hub.yaml": "title: [unclosed\n  bad: : :\n"},
        )
        profiles = discover_projects(tmp_path)
        by_slug = {p.slug: p for p in profiles}
        assert by_slug["proj_broken"].invalid_reason != ""

    def test_excluded_project_skipped(self, tmp_path: Path) -> None:
        _make_project(
            tmp_path,
            "proj_excluded",
            {
                "PROJECT_STATUS_REPORT.md": "# status\n",
                "reports_hub.yaml": "exclude: true\n",
            },
        )
        profiles = discover_projects(tmp_path)
        by_slug = {p.slug: p for p in profiles}
        assert by_slug["proj_excluded"].excluded is True

    def test_owner_title_used(self, tmp_path: Path) -> None:
        _make_project(
            tmp_path,
            "proj_titled",
            {
                "PROJECT_STATUS_REPORT.md": "# status\n",
                "reports_hub.yaml": "title: Мой проект\n",
            },
        )
        profiles = discover_projects(tmp_path)
        by_slug = {p.slug: p for p in profiles}
        assert by_slug["proj_titled"].title == "Мой проект"

    def test_service_dirs_excluded(self, tmp_path: Path) -> None:
        service_dir = tmp_path / ".freezer"
        service_dir.mkdir()
        (service_dir / "PROJECT_STATUS_REPORT.md").write_text("# x\n", encoding="utf-8")
        profiles = discover_projects(tmp_path)
        assert ".freezer" not in {p.slug for p in profiles}

    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        assert discover_projects(tmp_path / "no_such_dir") == []
