#!/usr/bin/env python3
"""Tests for Reports Hub render smoke (спека §12, тест 6: test_render_smoke).

Генерация сайта во tmp: index + проект + док существуют, HTML валиден
(`<title>`, токены темы), file://-совместимость (нет абсолютных ссылок).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.report.generate import generate_site
from services_08.reports_hub.report.render import render_index
from services_08.reports_hub.report.summaries import slugify


def _make_project(root: Path, name: str, files: dict[str, str]) -> Path:
    """Создать каталог проекта с файлами."""
    project_dir = root / name
    project_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        target = project_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return project_dir


STATUS_DOC = """# PROJECT_STATUS_REPORT.md — статус

> Дата: 2026-09-16 · Состояние: **249 тестов зелёные, mypy clean (50 файлов)**

---

## 1. Сводка «что сделано» (13 этапов)

| # | Этап | Коммит | Дата | Ядро результата |
|---|------|--------|------|-----------------|
| 0 | Аудит реализации | `1badef4` | 09-08 | IMPLEMENTATION_AUDIT_REPORT по 15 пунктам ТЗ |
| 1 | Клиенты + материалы | `2a85211` | 09-08 | clients/contacts/materials, matching, реестр |

## 2. Открытые вопросы

- TG-токен ждёт активации.
"""

ROADMAP_DOC = """# ROADMAP.md

> Статус: ACTIVE

## Этапы

| Этап | Статус | Дата |
|---|---|---|
| H1 каркас | ✅ завершён | 2026-09-16 |
| H2 extract | 🔲 не начат | — |

- [ ] H3 рендер
"""


class TestRenderSmoke:
    def test_site_files_created(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        _make_project(
            projects_root,
            "demo",
            {
                "PROJECT_STATUS_REPORT.md": STATUS_DOC,
                "ROADMAP.md": ROADMAP_DOC,
                "reports_hub.yaml": (
                    "title: Demo Project\n"
                    "docs:\n"
                    "  - \"PROJECT_STATUS_REPORT.md\"\n"
                    "  - \"ROADMAP.md\"\n"
                    "timeline_sources:\n"
                    "  - \"PROJECT_STATUS_REPORT.md\"\n"
                    "roadmap: \"ROADMAP.md\"\n"
                    "blockers: \"PROJECT_STATUS_REPORT.md\"\n"
                ),
            },
        )
        site_root = tmp_path / "site"
        result = generate_site(projects_root, site_root)
        assert result.projects == 1
        assert result.docs_rendered == 2
        assert (site_root / "index.html").exists()
        assert (site_root / "manifest.json").exists()
        slug = slugify("demo")
        assert (site_root / "projects" / slug / "index.html").exists()
        assert (site_root / "projects" / slug / "docs" / "project-status-report.html").exists()

    def test_html_valid_and_theme_tokens(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        _make_project(projects_root, "demo", {"PROJECT_STATUS_REPORT.md": STATUS_DOC})
        site_root = tmp_path / "site"
        generate_site(projects_root, site_root)
        index = (site_root / "index.html").read_text(encoding="utf-8")
        assert "<title>" in index
        assert "--accent" in index
        assert "prefers-color-scheme" in index
        project_page = (site_root / "projects" / slugify("demo") / "index.html").read_text(encoding="utf-8")
        assert '<button class="theme-btn" id="theme-btn"' in project_page
        assert "249 passed" in project_page

    def test_no_absolute_links(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        _make_project(projects_root, "demo", {"PROJECT_STATUS_REPORT.md": STATUS_DOC})
        site_root = tmp_path / "site"
        generate_site(projects_root, site_root)
        for page in site_root.rglob("*.html"):
            html_text = page.read_text(encoding="utf-8")
            hrefs = re.findall(r'(?:href|src)="([^"]+)"', html_text)
            assert hrefs, f"нет ссылок в {page}"
            for href in hrefs:
                assert not href.startswith(("/", "http://", "https://", "file://")), f"абсолютная ссылка {href} в {page}"

    def test_manifest_contract(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        _make_project(projects_root, "demo", {"PROJECT_STATUS_REPORT.md": STATUS_DOC})
        _make_project(projects_root, "nodocs", {"README.md": "# пусто"})
        site_root = tmp_path / "site"
        generate_site(projects_root, site_root)
        manifest = json.loads((site_root / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["generated_at"]
        assert [item["slug"] for item in manifest["projects"]] == ["demo"]
        assert any(item["slug"] == "nodocs" for item in manifest["no_data"])

    def test_no_data_card_on_index(self, tmp_path: Path) -> None:
        projects_root = tmp_path / "projects_17"
        _make_project(projects_root, "nodocs", {"README.md": "# пусто"})
        site_root = tmp_path / "site"
        generate_site(projects_root, site_root)
        index = (site_root / "index.html").read_text(encoding="utf-8")
        assert "нет данных" in index
        assert "Без отчётных данных" in index

    def test_index_escapes_html(self) -> None:
        from services_08.reports_hub.report.model import ReportModel

        model = ReportModel(slug="x", title="<script>alert(1)</script>", exec_summary="ok")
        page = render_index(type("S", (), {"generated_at": "now", "projects": [model], "no_data": ()})())
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page