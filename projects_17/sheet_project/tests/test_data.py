"""Тесты DATA-слоя (этап 2): `data/models.py` + `data/sample_data.py`."""

from dataclasses import FrozenInstanceError

import pytest

from data.models import DataValidationError, Project, Record, Task
from data.sample_data import get_collections, get_rows


# ── модели ──

def test_project_constructs():
    p = Project(id="p1", name="Сайт", status="in_progress", deadline="2026-09-15", owner="Алиса")
    assert p.id == "p1"
    assert p.name == "Сайт"
    assert p.deadline == "2026-09-15"


def test_task_constructs():
    t = Task(id="t1", project_id="p1", title="Дизайн", status="done")
    assert t.project_id == "p1"
    assert t.due_date is None


def test_record_is_base():
    p = Project(id="p1", name="Сайт", status="in_progress")
    assert isinstance(p, Record)


def test_empty_record_id_rejected():
    with pytest.raises(DataValidationError):
        Project(id="", name="Сайт", status="in_progress")


def test_empty_project_name_rejected():
    with pytest.raises(DataValidationError):
        Project(id="p1", name="", status="in_progress")


def test_empty_task_project_id_rejected():
    with pytest.raises(DataValidationError):
        Task(id="t1", project_id="", title="Дизайн", status="done")


def test_frozen_immutability():
    p = Project(id="p1", name="Сайт", status="in_progress")
    with pytest.raises(FrozenInstanceError):
        p.name = "Другое"  # type: ignore[misc]


# ── источник данных (sample_data) ──

def test_get_rows_returns_projects():
    rows = get_rows("projects")
    assert len(rows) >= 1
    assert all(isinstance(r, Project) for r in rows)


def test_get_rows_returns_tasks():
    rows = get_rows("tasks")
    assert len(rows) >= 1
    assert all(isinstance(r, Task) for r in rows)


def test_get_rows_unknown_collection_rejected():
    with pytest.raises(DataValidationError):
        get_rows("nonexistent")


def test_get_collections_has_expected_keys():
    assert set(get_collections()) == {"projects", "tasks"}


def test_sample_ids_unique():
    for name, rows in get_collections().items():
        ids = [r.id for r in rows]
        assert len(ids) == len(set(ids)), f"дубли id в коллекции '{name}'"


def test_tasks_reference_existing_projects():
    project_ids = {r.id for r in get_rows("projects")}
    for t in get_rows("tasks"):
        assert t.project_id in project_ids, (
            f"задача '{t.id}' ссылается на несуществующий проект '{t.project_id}'"
        )
