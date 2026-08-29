"""Пример данных первого шаблона — `data/sample_data.py` (этап 2).

Роль: use-case «пример данных» (architecture.md §2.2 application-слой).
Именованные коллекции (audit H2): `projects` / `tasks`.

`get_rows(source)` — публичный API DATA (contracts.yaml `data.interface`):
`source` выбирает коллекцию (это строка `DataSource.source`, извлекается вызывающим —
DATA не зависит от `config/*`). `field_map` применяется GENERATOR'ом, не здесь.
"""

from __future__ import annotations

from data.models import DataValidationError, Project, Record, Task

# Именованные коллекции (map[collection_name -> list[Record***REMOVED******REMOVED***).
# По конвенции не мутируются; сами записи — frozen dataclass.
COLLECTIONS: dict[str, list[Record***REMOVED******REMOVED*** = {
    "projects": [
        Project(id="p1", name="Сайт-витрина", status="in_progress", deadline="2026-09-15", owner="Алиса"),
        Project(id="p2", name="Мобильное приложение", status="planning", deadline="2026-10-01", owner="Борис"),
        Project(id="p3", name="Внутренний портал", status="done", deadline="2026-08-30", owner="Виктор"),
        Project(id="p4", name="Ребрендинг", status="blocked", deadline=None, owner="Алиса"),
    ***REMOVED***,
    "tasks": [
        Task(id="t1", project_id="p1", title="Дизайн главной", status="done", due_date="2026-08-20"),
        Task(id="t2", project_id="p1", title="Вёрстка", status="in_progress", due_date="2026-08-25"),
        Task(id="t3", project_id="p1", title="Интеграция оплаты", status="planning", due_date="2026-09-05"),
        Task(id="t4", project_id="p2", title="Прототип", status="planning", due_date="2026-09-01"),
        Task(id="t5", project_id="p2", title="Бэкенд-API", status="planning", due_date="2026-09-20"),
        Task(id="t6", project_id="p3", title="Деплой", status="done", due_date="2026-08-29"),
        Task(id="t7", project_id="p4", title="Новый логотип", status="blocked", due_date=None),
    ***REMOVED***,
***REMOVED***


def get_collections() -> dict[str, list[Record***REMOVED******REMOVED***:
    """Вернуть все именованные коллекции (записи неизменяемы по конвенции)."""
    return COLLECTIONS


def get_rows(source: str) -> list[Record***REMOVED***:
    """Вернуть записи коллекции по имени (audit H2; `source` = `DataSource.source`).

    - неизвестная коллекция → `DataValidationError` (fail-fast);
    - пустая коллекция → пустой список (лист только с заголовками, не ошибка).
    """
    if source not in COLLECTIONS:
        raise DataValidationError(f"Неизвестная коллекция '{source***REMOVED***'")
    return COLLECTIONS[source***REMOVED***


__all__ = ["COLLECTIONS", "get_collections", "get_rows"***REMOVED***
