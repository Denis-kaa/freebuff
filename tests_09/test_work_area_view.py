#!/usr/bin/env python3
"""Tests for Work Area as View (scripts_01/work_area_view.py).

Канон promt36/37, правило 2: Work Area — НЕ сущность, а динамический список
проектов, связанных с конкретным Resource (таблица `project_resources`).

Tests:
  - init_db: таблица project_resources создаётся
  - link: создание связи project ↔ resource (идемпотентность)
  - unlink: удаление связи
  - projects_for_resource: список проектов для ресурса (View)
  - resources_for_project: список ресурсов для проекта
  - list_links: все связи
  - join с projects: описание проекта подтягивается
  - CLI: main() подкоманды link/projects/resources/list
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.work_area_view import (
    init_db,
    link,
    unlink,
    projects_for_resource,
    resources_for_project,
    list_links,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def db(tmp_path) -> Path:
    """Временная БД для теста."""
    return tmp_path / "data_13" / "context.db"


def _seed_project(db: Path, name: str, description: str = "", category: str = "") -> None:
    """Создаёт таблицу projects и добавляет проект (как scan_projects)."""
    conn = init_db(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            description TEXT DEFAULT '',
            language TEXT DEFAULT '',
            git_remote TEXT DEFAULT '',
            readme_preview TEXT DEFAULT '',
            has_requirements INTEGER DEFAULT 0,
            has_package_json INTEGER DEFAULT 0,
            has_dockerfile INTEGER DEFAULT 0,
            has_makefile INTEGER DEFAULT 0,
            has_pyproject INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            last_scanned TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO projects (name, path, description, category, status, last_scanned) "
        "VALUES (?, ?, ?, ?, 'active', '2026-08-01T00:00:00+00:00')",
        (name, f"/tmp/{name}", description, category),
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# init_db
# ═══════════════════════════════════════════════════════════════


class TestInitDB:
    def test_table_created(self, db: Path):
        conn = init_db(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_resources'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_table_schema(self, db: Path):
        conn = init_db(db)
        cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(project_resources)").fetchall()}
        conn.close()
        assert set(cols) == {"project_id", "resource_id", "created_at"}
        # PK по паре (project_id, resource_id)
        assert cols["project_id"].upper() == "TEXT"
        assert cols["resource_id"].upper() == "TEXT"

    def test_idempotent_init(self, db: Path):
        init_db(db)
        init_db(db)  # не должно падать


# ═══════════════════════════════════════════════════════════════
# link / unlink
# ═══════════════════════════════════════════════════════════════


class TestLink:
    def test_link_creates_relationship(self, db: Path):
        assert link("CRM", "Telegram", db) is True
        links = list_links(db)
        assert len(links) == 1
        assert links[0]["project_id"] == "CRM"
        assert links[0]["resource_id"] == "Telegram"
        assert links[0]["created_at"]

    def test_link_is_idempotent(self, db: Path):
        assert link("CRM", "Telegram", db) is True
        assert link("CRM", "Telegram", db) is False  # повтор — не создаёт дубль
        assert len(list_links(db)) == 1

    def test_link_multiple_resources(self, db: Path):
        link("CRM", "Telegram", db)
        link("CRM", "Git", db)
        link("ТСЖ", "Telegram", db)
        assert len(list_links(db)) == 3

    def test_link_strips_whitespace(self, db: Path):
        link("  CRM  ", "  Telegram  ", db)
        assert projects_for_resource("Telegram", db)[0]["project_id"] == "CRM"

    def test_link_requires_args(self, db: Path):
        with pytest.raises(ValueError):
            link("", "Telegram", db)
        with pytest.raises(ValueError):
            link("CRM", "", db)


class TestUnlink:
    def test_unlink_removes_relationship(self, db: Path):
        link("CRM", "Telegram", db)
        assert unlink("CRM", "Telegram", db) is True
        assert list_links(db) == []

    def test_unlink_missing_returns_false(self, db: Path):
        assert unlink("CRM", "Telegram", db) is False

    def test_unlink_keeps_other_links(self, db: Path):
        link("CRM", "Telegram", db)
        link("CRM", "Git", db)
        unlink("CRM", "Telegram", db)
        remaining = list_links(db)
        assert len(remaining) == 1
        assert remaining[0]["resource_id"] == "Git"


# ═══════════════════════════════════════════════════════════════
# Work Area as View: проекты по ресурсу
# ═══════════════════════════════════════════════════════════════


class TestProjectsForResource:
    def test_returns_projects_for_resource(self, db: Path):
        link("CRM", "Telegram", db)
        link("ТСЖ", "Telegram", db)
        link("Контент-завод", "Telegram", db)
        link("CRM", "Git", db)

        projects = projects_for_resource("Telegram", db)
        assert [p["project_id"] for p in projects] == ["CRM", "Контент-завод", "ТСЖ"]

    def test_ignores_other_resources(self, db: Path):
        link("CRM", "Telegram", db)
        projects = projects_for_resource("Git", db)
        assert projects == []

    def test_empty_resource(self, db: Path):
        assert projects_for_resource("NoSuchResource", db) == []

    def test_joins_projects_description(self, db: Path):
        _seed_project(db, "CRM", description="клиенты")
        _seed_project(db, "ТСЖ", description="уведомления")
        link("CRM", "Telegram", db)
        link("ТСЖ", "Telegram", db)

        projects = projects_for_resource("Telegram", db)
        by_name = {p["project_id"]: p for p in projects}
        assert by_name["CRM"]["description"] == "клиенты"
        assert by_name["ТСЖ"]["description"] == "уведомления"

    def test_join_handles_missing_projects_table(self, db: Path):
        # Таблицы projects нет — LEFT JOIN должен отработать с пустыми деталями
        link("CRM", "Telegram", db)
        projects = projects_for_resource("Telegram", db)
        assert projects[0]["project_id"] == "CRM"
        assert projects[0]["description"] == ""


# ═══════════════════════════════════════════════════════════════
# Ресурсы по проекту
# ═══════════════════════════════════════════════════════════════


class TestResourcesForProject:
    def test_returns_resources_for_project(self, db: Path):
        link("CRM", "Telegram", db)
        link("CRM", "Git", db)
        link("ТСЖ", "Telegram", db)

        resources = resources_for_project("CRM", db)
        assert [r["resource_id"] for r in resources] == ["Git", "Telegram"]
        assert all(r["created_at"] for r in resources)

    def test_empty_project(self, db: Path):
        assert resources_for_project("Ghost", db) == []


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_link(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "link", "CRM", "Telegram"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        out = capsys.readouterr().out
        assert "Связь создана" in out
        assert "CRM ↔ Telegram" in out

    def test_main_projects(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        link("CRM", "Telegram", db)
        link("ТСЖ", "Telegram", db)

        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "projects", "Telegram"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        out = capsys.readouterr().out
        assert "Проекты, связанные с Telegram" in out
        assert "- CRM" in out
        assert "- ТСЖ" in out

    def test_main_projects_empty(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "projects", "Telegram"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        out = capsys.readouterr().out
        assert "(нет связей)" in out

    def test_main_resources(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        link("CRM", "Telegram", db)
        link("CRM", "Git", db)

        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "resources", "CRM"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        out = capsys.readouterr().out
        assert "Ресурсы, связанные с CRM" in out
        assert "- Git" in out
        assert "- Telegram" in out

    def test_main_list(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        link("CRM", "Telegram", db)

        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "list"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        out = capsys.readouterr().out
        assert "CRM ↔ Telegram" in out

    def test_main_unlink(self, db: Path, monkeypatch, capsys):
        from scripts_01.work_area_view import main

        link("CRM", "Telegram", db)
        monkeypatch.setattr(sys, "argv", ["work_area_view.py", "unlink", "CRM", "Telegram"])
        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        assert main() == 0
        assert list_links(db) == []


# ═══════════════════════════════════════════════════════════════
# freebuff_cli.py: resource-команда
# ═══════════════════════════════════════════════════════════════


class TestFreebuffCLIResource:
    def test_freebuff_resource_projects(self, db: Path, monkeypatch, capsys):
        import freebuff_cli

        link("CRM", "Telegram", db)
        link("ТСЖ", "Telegram", db)

        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        freebuff_cli.cmd_resource("projects", "Telegram")
        out = capsys.readouterr().out
        assert "Проекты, связанные с Telegram" in out
        assert "- CRM" in out
        assert "- ТСЖ" in out

    def test_freebuff_resource_projects_unknown(self, db: Path, monkeypatch, capsys):
        import freebuff_cli

        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        freebuff_cli.cmd_resource("projects", "NoSuchResource")
        out = capsys.readouterr().out
        assert "(нет связей)" in out

    def test_freebuff_resource_link(self, db: Path, monkeypatch, capsys):
        import freebuff_cli

        monkeypatch.setattr("scripts_01.work_area_view.DB_PATH", db)
        freebuff_cli.cmd_resource("link", "CRM", "Telegram")
        assert list_links(db)[0]["project_id"] == "CRM"

    def test_freebuff_resource_missing_args(self, capsys):
        import freebuff_cli

        freebuff_cli.cmd_resource("projects")
        out = capsys.readouterr().out
        assert "Укажи ресурс" in out

    def test_freebuff_resource_unknown_action(self, capsys):
        import freebuff_cli

        freebuff_cli.cmd_resource("bogus")
        out = capsys.readouterr().out
        assert "Использование" in out
