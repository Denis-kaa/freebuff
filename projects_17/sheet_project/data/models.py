"""Доменные модели DATA — `data/models.py` (этап 2, sheet_project D2).

Роль: DATA contract §2 (`contracts.yaml`) + `architecture.md` §2.2.
Нормализованные записи, source-agnostic. НЕ знает источник, НЕ знает layout листа,
НЕ зависит от `config/*` и openpyxl.

Именованные коллекции (audit H2): `projects` / `tasks`.
Общее поле всех записей — `id` (unique).

Примечание: формула-инъекция (`= + - @`) экранируется ПРИ ЗАПИСИ в GENERATOR
(R9), здесь DATA хранит сырые значения.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class DataValidationError(ValueError):
    """Невалидная запись DATA (fail-fast на входе)."""


def _require_nonempty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DataValidationError(f"{field_name}: пустое значение")


@dataclass(frozen=True)
class Record:
    """Базовая запись (общее поле `id`, unique)."""
    id: str

    def __post_init__(self) -> None:
        _require_nonempty("Record.id", self.id)


@dataclass(frozen=True)
class Project(Record):
    """Одна запись = один проект (коллекция `projects`)."""
    name: str
    status: str
    deadline: str | None = None  # ISO-8601 (YYYY-MM-DD)
    owner: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_nonempty("Project.name", self.name)


@dataclass(frozen=True)
class Task(Record):
    """Одна запись = одна задача (коллекция `tasks`); `project_id` связывает с проектом."""
    project_id: str
    title: str
    status: str
    due_date: str | None = None  # ISO-8601 (YYYY-MM-DD)

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_nonempty("Task.project_id", self.project_id)
        _require_nonempty("Task.title", self.title)


__all__ = ["DataValidationError", "Project", "Record", "Task"]
