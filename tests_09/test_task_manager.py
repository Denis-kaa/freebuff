#!/usr/bin/env python3
"""Tests for Meeting Tasks manager (scripts_01/task_manager.py).

Канон: pompts_11/042_06_dokumentaciya_meeting_tasks.md, Фаза E.
Задачи: digital / meeting / document; AI-брифинг — заглушка v0.

Tests structure mirrors tests_09/test_work_area_view.py (tmp_path fixture,
monkeypatch DB_PATH, idempotency, JSON-validation, CLI smoke tests).

Coverage:
  * TestInitDB: schema, indices, idempotent init
  * TestCreateTask: digital / meeting / document flows, validation,
    meeting-attr coercion for non-meeting types
  * TestGetTasks: filters by type + status, ordering (newest first),
    empty project
  * TestShowTask: by id, missing returns None
  * TestUpdateTask: partial, immutability of id/created_at, idempotency
  * TestDeleteTask: idempotency (False on rerun)
  * TestGenerateBriefing: meeting → text, non-meeting → None, missing → None,
    briefing_generated flag set
  * TestCLI: create / list / show / update / delete / briefing
"""
from __future__ import annotations

import json
import sys
import time
***REMOVED***
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.task_manager import (
    VALID_PRIORITIES,
    VALID_STATUSES,
    VALID_TASK_TYPES,
    create_task,
    delete_task,
    generate_meeting_briefing,
    get_tasks,
    init_db,
    show_task,
    update_task,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures / helpers
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def db(tmp_path: Path) -> Path:
    """Временная БД: data_13/context.db (как в production)."""
    p = tmp_path / "data_13" / "context.db"
    return p


def _seed_project(db: Path, name: str = "CRM") -> None:
    """Создаёт таблицу projects и сидирует проект.

    Нужно для FK-валидации (PRAGMA foreign_keys = ON). Без этого INSERT
    в tasks упадёт на чистой tmp-БД.
    """
    conn = init_db(db)
    conn.execute(
        """
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
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO projects "
        "(name, path, description, category, status, last_scanned) "
        "VALUES (?, ?, '', '', 'active', '2026-08-01T00:00:00+00:00')",
        (name, f"/tmp/{name***REMOVED***"),
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
# init_db / schema
# ═══════════════════════════════════════════════════════════════

class TestInitDB:
    def test_table_created(self, db: Path):
        conn = init_db(db)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0***REMOVED*** == "tasks"

    def test_columns_match_canonical_schema(self, db: Path):
        conn = init_db(db)
        cols = {r[1***REMOVED***: r[2***REMOVED*** for r in conn.execute("PRAGMA table_info(tasks)").fetchall()***REMOVED***
        conn.close()
        expected = {
            "id", "project_id", "title", "description",
            "task_type", "status", "priority",
            "meeting_time", "location", "participants",
            "briefing_generated", "created_at", "updated_at",
        ***REMOVED***
        assert set(cols) == expected

    def test_indices_created(self, db: Path):
        conn = init_db(db)
        idx = {r[0***REMOVED*** for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='tasks' AND name LIKE 'idx_%'"
        ).fetchall()***REMOVED***
        conn.close()
        assert {"idx_tasks_project", "idx_tasks_type", "idx_tasks_status"***REMOVED*** <= idx

    def test_idempotent_init(self, db: Path):
        # Повторный init не должен падать (CREATE TABLE IF NOT EXISTS).
        init_db(db)
        init_db(db)

    def test_journal_mode_wal(self, db: Path):
        conn = init_db(db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0***REMOVED***
        conn.close()
        assert mode.upper() == "WAL"

    def test_foreign_keys_NOT_enforced_by_default(self, db: Path):
        """FK в схеме — только декларативный контракт (как в work_area_view.py).

        PRAGMA foreign_keys намеренно НЕ включается: enforcement ломает
        тесты и онбординг (FK в projects(name) проверяется и на UPDATE/
        DELETE в tasks). Schema — FK declared. Runtime — unenforced.
        """
        conn = init_db(db)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0***REMOVED***
        conn.close()
        assert fk == 0


# ═══════════════════════════════════════════════════════════════
# create_task
# ═══════════════════════════════════════════════════════════════

class TestCreateTask:
    def test_creates_digital_task(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "написать API", db_path=db)
        assert t["project_id"***REMOVED*** == "CRM"
        assert t["title"***REMOVED*** == "написать API"
        assert t["task_type"***REMOVED*** == "digital"
        assert t["status"***REMOVED*** == "pending"
        assert t["priority"***REMOVED*** == "normal"
        assert t["participants"***REMOVED*** == [***REMOVED***
        assert t["meeting_time"***REMOVED*** is None
        assert t["location"***REMOVED*** is None
        assert t["briefing_generated"***REMOVED*** is False
        assert t["id"***REMOVED***.startswith("tm-")
        assert t["created_at"***REMOVED***
        assert t["updated_at"***REMOVED*** == t["created_at"***REMOVED***

    def test_creates_meeting_task_with_attrs(self, db: Path):
        _seed_project(db)
        t = create_task(
            "CRM", "Встреча с клиентом", task_type="meeting",
            meeting_time="2026-08-02T14:00",
            location="Офис",
            participants=["Алексей", "Иван"***REMOVED***,
            priority="high",
            db_path=db,
        )
        assert t["task_type"***REMOVED*** == "meeting"
        assert t["meeting_time"***REMOVED*** == "2026-08-02T14:00"
        assert t["location"***REMOVED*** == "Офис"
        assert t["participants"***REMOVED*** == ["Алексей", "Иван"***REMOVED***
        assert t["priority"***REMOVED*** == "high"

    def test_creates_document_task(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "ТЗ для подрядчика", task_type="document", db_path=db)
        assert t["task_type"***REMOVED*** == "document"

    def test_meeting_attrs_rejected_for_non_meeting_types(self, db: Path):
        """Правило 8 (Context-Aware Routing): meeting-атрибуты только с meeting.
        Строгий режим (без тихого шёпота coerce) — потеря данных была бугой.
        """
        _seed_project(db)
        with pytest.raises(ValueError, match="meeting_time"):
            create_task(
                "CRM", "code", task_type="digital",
                meeting_time="2026-08-01T14:00", db_path=db,
            )
        with pytest.raises(ValueError, match="location"):
            create_task(
                "CRM", "code", task_type="digital",
                location="X", db_path=db,
            )
        with pytest.raises(ValueError, match="participants"):
            create_task(
                "CRM", "code", task_type="digital",
                participants=["a"***REMOVED***, db_path=db,
            )
        # meeting сам разрешает любой набор:
        t = create_task(
            "CRM", "sync", task_type="meeting",
            meeting_time="2026-08-01T14:00", location="X",
            participants=["a"***REMOVED***, db_path=db,
        )
        assert t["meeting_time"***REMOVED*** == "2026-08-01T14:00"
        assert t["location"***REMOVED*** == "X"
        assert t["participants"***REMOVED*** == ["a"***REMOVED***

    def test_rejects_invalid_task_type(self, db: Path):
        _seed_project(db)
        with pytest.raises(ValueError, match="task_type"):
            create_task("CRM", "x", task_type="bogus", db_path=db)

    def test_rejects_invalid_priority(self, db: Path):
        _seed_project(db)
        with pytest.raises(ValueError, match="priority"):
            create_task("CRM", "x", priority="mega-urgent", db_path=db)

    def test_rejects_empty_title(self, db: Path):
        _seed_project(db)
        with pytest.raises(ValueError, match="title обяз"):
            create_task("CRM", "", db_path=db)
        with pytest.raises(ValueError, match="title обяз"):
            create_task("CRM", "   ", db_path=db)

    def test_rejects_empty_project_id(self, db: Path):
        with pytest.raises(ValueError, match="project_id обяз"):
            create_task("", "title", db_path=db)

    def test_participants_must_be_list_of_strings(self, db: Path):
        _seed_project(db)
        with pytest.raises(ValueError, match="list"):
            create_task(
                "CRM", "x", task_type="meeting",
                participants=["a", 42***REMOVED***, db_path=db,  # type: ignore[list-item***REMOVED***
            )

    def test_strips_whitespace(self, db: Path):
        _seed_project(db)
        t = create_task("  CRM  ", "  Title  ", db_path=db)
        assert t["project_id"***REMOVED*** == "CRM"
        assert t["title"***REMOVED*** == "Title"

    def test_id_is_unique(self, db: Path):
        _seed_project(db)
        ids = {create_task("CRM", f"task #{i***REMOVED***", db_path=db)["id"***REMOVED*** for i in range(20)***REMOVED***
        assert len(ids) == 20


# ═══════════════════════════════════════════════════════════════
# get_tasks
# ═══════════════════════════════════════════════════════════════

class TestGetTasks:
    def test_returns_empty_for_unknown_project(self, db: Path):
        assert get_tasks("ghost", db_path=db) == [***REMOVED***

    def test_returns_only_tasks_for_project(self, db: Path):
        _seed_project(db)
        _seed_project(db, "ТСЖ")
        create_task("CRM", "a", db_path=db)
        create_task("CRM", "b", db_path=db)
        create_task("ТСЖ", "c", db_path=db)
        assert len(get_tasks("CRM", db_path=db)) == 2
        assert len(get_tasks("ТСЖ", db_path=db)) == 1

    def test_filter_by_type(self, db: Path):
        _seed_project(db)
        create_task("CRM", "digital-1", task_type="digital", db_path=db)
        create_task("CRM", "meeting-1", task_type="meeting", db_path=db)
        create_task("CRM", "doc-1", task_type="document", db_path=db)
        digital = get_tasks("CRM", task_type="digital", db_path=db)
        assert len(digital) == 1 and digital[0***REMOVED***["task_type"***REMOVED*** == "digital"
        meeting = get_tasks("CRM", task_type="meeting", db_path=db)
        assert len(meeting) == 1 and meeting[0***REMOVED***["task_type"***REMOVED*** == "meeting"

    def test_filter_by_status(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "a", db_path=db)
        create_task("CRM", "b", db_path=db)
        update_task(t["id"***REMOVED***, status="in_progress", db_path=db)
        pending = get_tasks("CRM", status="pending", db_path=db)
        in_progress = get_tasks("CRM", status="in_progress", db_path=db)
        assert len(pending) == 1
        assert len(in_progress) == 1
        assert in_progress[0***REMOVED***["id"***REMOVED*** == t["id"***REMOVED***

    def test_rejects_invalid_type_filter(self, db: Path):
        with pytest.raises(ValueError):
            get_tasks("CRM", task_type="bogus", db_path=db)

    def test_rejects_invalid_status_filter(self, db: Path):
        with pytest.raises(ValueError):
            get_tasks("CRM", status="bogus", db_path=db)

    def test_sorted_newest_first(self, db: Path):
        _seed_project(db)
        t1 = create_task("CRM", "first", db_path=db)
        # Явный sleep детерминирует разницу created_at: иначе микросекундная
        # точность теряется на быстрых системах и тест флакает.
        time.sleep(0.1)
        t2 = create_task("CRM", "second", db_path=db)
        tasks = get_tasks("CRM", db_path=db)
        assert tasks[0***REMOVED***["id"***REMOVED*** == t2["id"***REMOVED***
        assert tasks[-1***REMOVED***["id"***REMOVED*** == t1["id"***REMOVED***     


# ═══════════════════════════════════════════════════════════════
# show_task
# ═══════════════════════════════════════════════════════════════

class TestShowTask:
    def test_returns_task_by_id(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        loaded = show_task(t["id"***REMOVED***, db_path=db)
        assert loaded is not None
        assert loaded["id"***REMOVED*** == t["id"***REMOVED***
        assert loaded["title"***REMOVED*** == "x"

    def test_missing_returns_none(self, db: Path):
        assert show_task("tm-bogus", db_path=db) is None


# ═══════════════════════════════════════════════════════════════
# update_task
# ═══════════════════════════════════════════════════════════════

class TestUpdateTask:
    def test_partial_update_of_status(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", priority="low", db_path=db)
        updated = update_task(t["id"***REMOVED***, status="in_progress", db_path=db)
        assert updated is not None
        assert updated["status"***REMOVED*** == "in_progress"
        assert updated["priority"***REMOVED*** == "low"  # не сбросилось
        assert updated["title"***REMOVED*** == "x"      # не сбросилось
        assert updated["updated_at"***REMOVED*** >= t["updated_at"***REMOVED***

    def test_update_meeting_attrs(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", task_type="meeting", db_path=db)
        updated = update_task(
            t["id"***REMOVED***, meeting_time="2026-09-01T15:00",
            location="Zoom", participants=["a", "b"***REMOVED***, db_path=db,
        )
        assert updated["meeting_time"***REMOVED*** == "2026-09-01T15:00"
        assert updated["location"***REMOVED*** == "Zoom"
        assert updated["participants"***REMOVED*** == ["a", "b"***REMOVED***

    def test_id_and_created_at_immutable(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        # Попытка перезаписать id/created_at должна быть отвергнута.
        with pytest.raises(ValueError, match="нельзя обновлять"):
            update_task(t["id"***REMOVED***, id="tm-hacked", db_path=db)
        with pytest.raises(ValueError, match="нельзя обновлять"):
            update_task(t["id"***REMOVED***, created_at="1999-01-01", db_path=db)
        with pytest.raises(ValueError, match="нельзя обновлять"):
            update_task(t["id"***REMOVED***, briefing_generated=True, db_path=db)

    def test_missing_returns_none(self, db: Path):
        assert update_task("tm-bogus", status="done", db_path=db) is None

    def test_empty_update_returns_current(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        loaded = update_task(t["id"***REMOVED***, db_path=db)
        assert loaded == show_task(t["id"***REMOVED***, db_path=db)

    def test_rejects_invalid_enum_value(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        with pytest.raises(ValueError):
            update_task(t["id"***REMOVED***, status="weird", db_path=db)

    def test_participants_roundtrip(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", task_type="meeting", db_path=db)
        update_task(t["id"***REMOVED***, participants=["X", "Y"***REMOVED***, db_path=db)
        loaded = show_task(t["id"***REMOVED***, db_path=db)
        assert loaded["participants"***REMOVED*** == ["X", "Y"***REMOVED***


# ═══════════════════════════════════════════════════════════════
# delete_task
# ═══════════════════════════════════════════════════════════════

class TestDeleteTask:
    def test_deletes_existing(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        assert delete_task(t["id"***REMOVED***, db_path=db) is True
        assert get_tasks("CRM", db_path=db) == [***REMOVED***

    def test_missing_returns_false_idempotent(self, db: Path):
        assert delete_task("tm-bogus", db_path=db) is False
        # Повтор — тоже False (идемпотентность).
        assert delete_task("tm-bogus", db_path=db) is False


# ═══════════════════════════════════════════════════════════════
# generate_meeting_briefing
# ═══════════════════════════════════════════════════════════════

class TestGenerateBriefing:
    def test_briefing_for_meeting(self, db: Path):
        _seed_project(db)
        t = create_task(
            "CRM", "Встреча", task_type="meeting",
            meeting_time="2026-08-02T14:00",
            location="Офис",
            participants=["Алексей", "Иван"***REMOVED***,
            db_path=db,
        )
        briefing = generate_meeting_briefing(t["id"***REMOVED***, db_path=db)
        assert briefing is not None
        assert "Брифинг встречи: Встреча" in briefing
        assert "CRM" in briefing
        assert "2026-08-02T14:00" in briefing
        assert "Офис" in briefing
        assert "Алексей" in briefing and "Иван" in briefing

        # В БД флаг выставлен.
        loaded = show_task(t["id"***REMOVED***, db_path=db)
        assert loaded["briefing_generated"***REMOVED*** is True
        # Поле `updated_at` обновлено.
        assert loaded["updated_at"***REMOVED*** >= t["created_at"***REMOVED***

    def test_no_briefing_for_digital(self, db: Path):
        _seed_project(db)
        t = create_task("CRM", "code", task_type="digital", db_path=db)
        assert generate_meeting_briefing(t["id"***REMOVED***, db_path=db) is None
        loaded = show_task(t["id"***REMOVED***, db_path=db)
        assert loaded["briefing_generated"***REMOVED*** is False

    def test_no_briefing_for_missing_task(self, db: Path):
        assert generate_meeting_briefing("tm-bogus", db_path=db) is None

    def test_handles_corrupted_participants_gracefully(self, db: Path):
        """Если JSON в participants мусорный — брифинг всё равно работает."""
        _seed_project(db)
        t = create_task("CRM", "x", task_type="meeting", db_path=db)
        # Подменяем JSON на мусор напрямую через БД.
        conn = init_db(db)
        conn.execute(
            "UPDATE tasks SET participants = ? WHERE id = ?",
            ("not-json", t["id"***REMOVED***),
        )
        conn.commit()
        conn.close()
        briefing = generate_meeting_briefing(t["id"***REMOVED***, db_path=db)
        assert briefing is not None
        assert "(не указаны)" in briefing


# ═══════════════════════════════════════════════════════════════
# CLI (argparse)
# ═══════════════════════════════════════════════════════════════

class TestCLI:
    def test_create_digital(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        rc = _run_cli(monkeypatch, capsys, db, "create", "CRM", "Написать код")
        assert rc == 0
        out = capsys.readouterr().out
        assert "Создана задача" in out
        assert "Написать код" in out

    def test_create_meeting_with_attrs(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        rc = _run_cli(
            monkeypatch, capsys, db,
            "create", "CRM", "Встреча", "--type", "meeting",
            "--time", "2026-08-02T14:00", "--location", "Zoom",
            "--participants", '["Алексей", "Иван"***REMOVED***',
        )
        assert rc == 0
        tasks = get_tasks("CRM", task_type="meeting", db_path=db)
        assert len(tasks) == 1
        assert tasks[0***REMOVED***["meeting_time"***REMOVED*** == "2026-08-02T14:00"
        assert tasks[0***REMOVED***["location"***REMOVED*** == "Zoom"
        assert tasks[0***REMOVED***["participants"***REMOVED*** == ["Алексей", "Иван"***REMOVED***

    def test_create_invalid_task_type_via_argparse(self, db: Path, monkeypatch, capsys):
        # argparse сам отвергает — SystemExit + exit code 2.
        from scripts_01.task_manager import main
        monkeypatch.setattr(sys, "argv",
            ["task_manager.py", "create", "CRM", "x", "--type", "bogus"***REMOVED***)
        monkeypatch.setattr("scripts_01.task_manager.DB_PATH", db)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_list_shows_tasks(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        create_task("CRM", "alpha", db_path=db)
        create_task("CRM", "beta", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "list", "CRM")
        assert rc == 0
        out = capsys.readouterr().out
        assert "Задачи проекта CRM" in out
        assert "(2):" in out
        # Булеты рендерятся как "- tm-<id>  [<type>/<status>/<priority>***REMOVED*** <title>".
        # Проверяем по полной сигнатуре, не по усечённому "-/<title>".
        assert "[digital/pending/normal***REMOVED*** alpha" in out
        assert "[digital/pending/normal***REMOVED*** beta" in out

    def test_list_empty_project(self, db: Path, monkeypatch, capsys):
        rc = _run_cli(monkeypatch, capsys, db, "list", "ghost")
        assert rc == 0
        out = capsys.readouterr().out
        assert "Задачи проекта ghost" in out
        assert "(нет задач)" in out

    def test_list_with_type_filter(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        create_task("CRM", "d_one", task_type="digital", db_path=db)
        create_task("CRM", "m_one", task_type="meeting", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "list", "CRM", "--type", "meeting")
        assert rc == 0
        out = capsys.readouterr().out
        assert "[meeting" in out
        assert "m_one" in out
        # digital задача НЕ показывается в фильтрованном листинге.
        assert "d_one" not in out

    def test_show_existing(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "show", t["id"***REMOVED***)
        assert rc == 0
        out = capsys.readouterr().out
        assert t["id"***REMOVED*** in out and "x" in out

    def test_show_missing_exits_nonzero(self, db: Path, monkeypatch, capsys):
        rc = _run_cli(monkeypatch, capsys, db, "show", "tm-bogus")
        assert rc == 1
        out_err = capsys.readouterr().err
        assert "не найдена" in out_err

    def test_update_partial(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "update", t["id"***REMOVED***,
                      "--status", "in_progress", "--priority", "high")
        assert rc == 0
        loaded = show_task(t["id"***REMOVED***, db_path=db)
        assert loaded["status"***REMOVED*** == "in_progress"
        assert loaded["priority"***REMOVED*** == "high"
        assert loaded["title"***REMOVED*** == "x"  # не сбросилось

    def test_update_missing_exits_nonzero(self, db: Path, monkeypatch, capsys):
        rc = _run_cli(monkeypatch, capsys, db, "update", "tm-bogus", "--status", "done")
        assert rc == 1

    def test_delete_existing(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        t = create_task("CRM", "x", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "delete", t["id"***REMOVED***)
        assert rc == 0
        assert get_tasks("CRM", db_path=db) == [***REMOVED***

    def test_delete_missing_is_idempotent(self, db: Path, monkeypatch, capsys):
        rc = _run_cli(monkeypatch, capsys, db, "delete", "tm-bogus")
        # Идемпотентно — печатает, что не найдено, exit 0.
        assert rc == 0
        out = capsys.readouterr().out
        assert "не найдена" in out

    def test_briefing_meeting(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        t = create_task("CRM", "Встреча", task_type="meeting", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "briefing", t["id"***REMOVED***)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Брифинг встречи: Встреча" in out

    def test_briefing_digital_exits_nonzero(self, db: Path, monkeypatch, capsys):
        _seed_project(db)
        t = create_task("CRM", "code", db_path=db)
        rc = _run_cli(monkeypatch, capsys, db, "briefing", t["id"***REMOVED***)
        assert rc == 1
        err = capsys.readouterr().err
        assert "только для task_type='meeting'" in err

    def test_briefing_missing_exits_nonzero(self, db: Path, monkeypatch, capsys):
        rc = _run_cli(monkeypatch, capsys, db, "briefing", "tm-bogus")
        assert rc == 1


# ═══════════════════════════════════════════════════════════════
# Module-level helpers for CLI tests
# ═══════════════════════════════════════════════════════════════


def _run_cli(monkeypatch, capsys, db_path: Path, *args: str) -> int:
    """Запускает task_manager.main() с подменой argv и DB_PATH."""
    from scripts_01.task_manager import main
    monkeypatch.setattr(sys, "argv", ["task_manager.py", *args***REMOVED***)
    monkeypatch.setattr("scripts_01.task_manager.DB_PATH", db_path)
    return main()


# ═══════════════════════════════════════════════════════════════
# Canonical invariants
# ═══════════════════════════════════════════════════════════════

class TestCanonicalInvariants:
    """Защита от дрейфа констант и сигнатур (которые завязаны на kanon)."""

    def test_valid_task_types_match_prompts_42(self):
        # pompts_11/042_06: digital, meeting, document. Не доб./не удалять.
        assert VALID_TASK_TYPES == frozenset({"digital", "meeting", "document"***REMOVED***)

    def test_valid_statuses_match_conventions(self):
        # pending → in_progress → done (+cancelled). Стандарт kanban.
        assert VALID_STATUSES == frozenset(
            {"pending", "in_progress", "done", "cancelled"***REMOVED***
        )

    def test_valid_priorities_match_dpe_3_levels_plus_low(self):
        # promt37 DPE priority: 1-Critical / 2-High / 3-Normal. low расширение.
        assert VALID_PRIORITIES == frozenset(
            {"low", "normal", "high", "critical"***REMOVED***
        )
