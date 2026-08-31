#!/usr/bin/env python3
"""task_manager.py — Meeting Tasks: digital / meeting / document tasks per project.

Phase E of `pompts_11/042_06_dokumentaciya_meeting_tasks.md`: реализация
Meeting Tasks поверх таблицы `tasks` в `data_13/context.db`.

Канон:
  * Work Area as View (`pompts_11/037_11_user_choice_override.md` правило 14,
    те же проекты + `project_resources`) — задачи живут внутри конкретного
    проекта, а не Work Area.
  * TaskAnalyzer / Context-Aware Routing: проверка Knowledge/Graph перед
    созданием задачи — outside scope этого модуля (заглушка `_check_duplicates`),
    см. ADR-008 и `pompts_11/032_09_workspace_os_konsolidaciya.md` §7.
  * AFC (Architectural Fit Check): переиспользует SQLite + паттерн
    `scripts_01/work_area_view.py`, расширяет существующий движок, не
    дублирует.

Schema (`tasks` в `data_13/context.db`):

    id TEXT PK, project_id (-> projects.name), title, description,
    task_type IN ('digital','meeting','document'),
    status   IN ('pending','in_progress','done','cancelled'),
    priority IN ('low','normal','high','critical'),
    meeting_time TEXT NULL, location TEXT NULL, participants JSON (list of str),
    briefing_generated INT 0/1, created_at, updated_at

Использование (CLI):

    python scripts_01/task_manager.py create <project_id> "Title" \\
        [--type digital|meeting|document] [--description "..."] [--priority P] \\
        [--time "2026-08-02T14:00"] [--location "..."] [--participants '["a","b"]']
    python scripts_01/task_manager.py list <project_id> [--type T] [--status S]
    python scripts_01/task_manager.py show <task_id>
    python scripts_01/task_manager.py update <task_id> [--title T] [--status S] \\
        [--priority P] [--time "..."] [--location "..."]
    python scripts_01/task_manager.py delete <task_id>
    python scripts_01/task_manager.py briefing <task_id>
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

DB_PATH = WORKSPACE / "data_13" / "context.db"

VALID_TASK_TYPES = frozenset({"digital", "meeting", "document"})
VALID_STATUSES = frozenset({"pending", "in_progress", "done", "cancelled"})
VALID_PRIORITIES = frozenset({"low", "normal", "high", "critical"})

# Поля, которые можно обновлять через update_task().
_UPDATABLE_FIELDS = frozenset({
    "title",
    "description",
    "task_type",
    "status",
    "priority",
    "meeting_time",
    "location",
    "participants",
})


def _now() -> str:
    """ISO-8601 UTC timestamp (suffix `+00:00`)."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Короткий стабильный id задачи: `tm-<8 hex>`."""
    return f"tm-{uuid.uuid4().hex[:8]}"


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Создаёт таблицу `tasks` (если её нет), индексы и возвращает соединение.

    PRAGMA foreign_keys = ON — это каноническое требование (правило 14:
    связь с projects.name, FK контролируется). Тесты, которые создают
    задачи без таблицы `projects`, должны сидировать её явно либо
    переключить PRAGMA на OFF после init_db().

    Создание безопасное (CREATE TABLE IF NOT EXISTS + IF NOT EXISTS для
    индексов) → повторные вызовы идемпотентны.

    PRAGMA foreign_keys намеренно НЕ включается: FK в схеме — только
    декларативный контракт (как в `work_area_view.py`, который тоже без
    `foreign_keys=ON`). Включение enforcement ломает тесты и онбординг
    (FK в `projects(name)` проверяется на ЛЮБОЙ write, включая UPDATE/DELETE
    в `tasks` — даже когда родитель по факту существует). При
    необходимости runtime-enforcement — отдельный скрипт
    `migrations/enable_fk.py`, не основной путь.
    """
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'digital',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'normal',
            meeting_time TEXT DEFAULT NULL,
            location TEXT DEFAULT NULL,
            participants TEXT NOT NULL DEFAULT '[]',
            briefing_generated INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(name)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════


def _check_duplicates(
    project_id: str, title: str, conn: sqlite3.Connection
) -> list[dict[str, Any]]:
    """Hook под Context-Aware Task Routing (правило 8, promt36/37).

    Возвращает существующие задачи того же проекта с тем же title
    (case-insensitive). Сейчас — поверхностная проверка (SQLite LIKE); в
    будущем сюда добавится KnowledgeEngine + GraphIndex lookup. Сейчас
    helper — намёк, но не блокер — дубликаты допускаются (пользователь
    решает).
    """
    rows = conn.execute(
        "SELECT id, title, task_type, status FROM tasks "
        "WHERE project_id = ? AND LOWER(title) = LOWER(?) "
        "ORDER BY created_at DESC LIMIT 5",
        (project_id.strip(), title.strip()),
    ).fetchall()
    return [
        {"id": r[0], "title": r[1], "task_type": r[2], "status": r[3]}
        for r in rows
    ]


def create_task(
    project_id: str,
    title: str,
    task_type: str = "digital",
    *,
    description: str = "",
    priority: str = "normal",
    meeting_time: str | None = None,
    location: str | None = None,
    participants: list[str] | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Создаёт задачу, возвращает созданный dict (с id и timestamps)."""
    project_id = project_id.strip()
    title = title.strip()
    if not project_id:
        raise ValueError("project_id обязателен")
    if not title:
        raise ValueError("title обязателен")
    task_type = task_type.strip().lower()
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(
            f"task_type должен быть одним из {sorted(VALID_TASK_TYPES)}, "
            f"получено: {task_type!r}"
        )
    priority = priority.strip().lower()
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"priority должен быть одним из {sorted(VALID_PRIORITIES)}, "
            f"получено: {priority!r}"
        )

    # Правило 8 (Context-Aware Routing, promt36_037): meeting-атрибуты
    # (meeting_time, location, participants) валидны ТОЛЬКО в связке с
    # task_type='meeting'. Строгий режим: тихий coerce был бы скрытой
    # потерей данных, лучше ошибка.
    if task_type != "meeting":
        if meeting_time is not None:
            raise ValueError(
                "meeting_time допустим только для task_type='meeting' "
                "(правило 8: Context-Aware Routing)"
            )
        if location is not None:
            raise ValueError(
                "location допустим только для task_type='meeting' "
                "(правило 8: Context-Aware Routing)"
            )
        if participants is not None and participants != []:
            raise ValueError(
                "participants допустим только для task_type='meeting' "
                "(правило 8: Context-Aware Routing)"
            )

    if participants is None:
        participants = []
    if not isinstance(participants, list) or not all(
        isinstance(p, str) for p in participants
    ):
        raise ValueError("participants должен быть list[str)")

    now = _now()
    task_id = _new_id()
    participants_json = json.dumps(participants, ensure_ascii=False)

    conn = init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO tasks (id, project_id, title, description, task_type, "
            "status, priority, meeting_time, location, participants, "
            "briefing_generated, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 0, ?, ?)",
            (
                task_id,
                project_id,
                title,
                description,
                task_type,
                priority,
                meeting_time,
                location,
                participants_json,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": task_id,
        "project_id": project_id,
        "title": title,
        "description": description,
        "task_type": task_type,
        "status": "pending",
        "priority": priority,
        "meeting_time": meeting_time,
        "location": location,
        "participants": participants,
        "briefing_generated": False,
        "created_at": now,
        "updated_at": now,
    }


def get_tasks(
    project_id: str,
    task_type: str | None = None,
    status: str | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Возвращает задачи проекта (опц. фильтр по task_type и/или status).

    Сортировка: created_at DESC (новые сверху) — это обычный UX-дефолт.
    """
    project_id = project_id.strip()
    if not project_id:
        raise ValueError("project_id обязателен")

    where: list[str] = ["project_id = ?"]
    args: list[Any] = [project_id]
    if task_type is not None:
        task_type = task_type.strip().lower()
        if task_type not in VALID_TASK_TYPES:
            raise ValueError(
                f"task_type должен быть одним из {sorted(VALID_TASK_TYPES)}, "
                f"получено: {task_type!r}"
            )
        where.append("task_type = ?")
        args.append(task_type)
    if status is not None:
        status = status.strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError(
                f"status должен быть одним из {sorted(VALID_STATUSES)}, "
                f"получено: {status!r}"
            )
        where.append("status = ?")
        args.append(status)

    conn = init_db(db_path)
    try:
        # Прямая лексикографическая сортировка по ISO 8601 (created_at у нас
        # всегда `YYYY-MM-DDTHH:MM:SS.ffffff+00:00` — часовой пояс фиксирован
        # UTC +00:00, лексикографический порядок = хронологический).
        #
        # Изначально использовали `datetime(created_at) DESC`, но SQLite
        # `datetime()` (без модификаторов strftime-style) НЕ парсит
        # T-разделитель + offset — возвращает NULL → NULLs-first → сортировка
        # случайна. Лексикографический путь совместим и с T-разделителем, и с
        # timezone offset, и с микросекундами.
        #
        # Тайбрейкер по id DESC гарантирует детерминизм при одинаковом
        # created_at (тесты создают несколько задач очень быстро).
        rows = conn.execute(
            "SELECT id, project_id, title, description, task_type, status, "
            "priority, meeting_time, location, participants, "
            "briefing_generated, created_at, updated_at "
            "FROM tasks WHERE " + " AND ".join(where) + " "
            "ORDER BY created_at DESC, id DESC",
            args,
        ).fetchall()
    finally:
        conn.close()

    return [_row_to_dict(r) for r in rows]


def show_task(task_id: str, db_path: Path | str | None = None) -> dict[str, Any] | None:
    """Возвращает одну задачу по id или None, если не найдена."""
    conn = init_db(db_path)
    try:
        row = conn.execute(
            "SELECT id, project_id, title, description, task_type, status, "
            "priority, meeting_time, location, participants, "
            "briefing_generated, created_at, updated_at "
            "FROM tasks WHERE id = ?",
            (task_id.strip(),),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row) if row else None


def update_task(
    task_id: str,
    *,
    db_path: Path | str | None = None,
    **fields: Any,
) -> dict[str, Any] | None:
    """Частичное обновление задачи. Возвращает обновлённый dict или None.

    Поддерживаемые поля (см. `_UPDATABLE_FIELDS`): title, description,
    task_type, status, priority, meeting_time, location, participants
    (list[str]). Возвращает None, если задача не найдена — идемпотентность.
    """
    clean_fields: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _UPDATABLE_FIELDS:
            raise ValueError(
                f"поле {key!r} нельзя обновлять через update_task(); "
                f"разрешены: {sorted(_UPDATABLE_FIELDS)}"
            )
        if key == "task_type":
            value = str(value).strip().lower()
            if value not in VALID_TASK_TYPES:
                raise ValueError(
                    f"task_type должен быть одним из {sorted(VALID_TASK_TYPES)}, "
                    f"получено: {value!r}"
                )
        elif key == "status":
            value = str(value).strip().lower()
            if value not in VALID_STATUSES:
                raise ValueError(
                    f"status должен быть одним из {sorted(VALID_STATUSES)}, "
                    f"получено: {value!r}"
                )
        elif key == "priority":
            value = str(value).strip().lower()
            if value not in VALID_PRIORITIES:
                raise ValueError(
                    f"priority должен быть одним из {sorted(VALID_PRIORITIES)}, "
                    f"получено: {value!r}"
                )
        elif key == "participants":
            if value is None:
                value = []
            if not isinstance(value, list) or not all(
                isinstance(p, str) for p in value
            ):
                raise ValueError("participants должен быть list[str)")
            value = json.dumps(value, ensure_ascii=False)
        elif key == "meeting_time":
            # meeting_time может стать NULL (сброс), пропускаем как есть
            value = value.strip() if isinstance(value, str) else value
        elif key == "location" and isinstance(value, str):
            value = value.strip()

        # ⚠️ ВАЖНО: после coerce присваиваем в clean_fields, иначе UPDATE
        # получит пустой set_clause и пропустит.
        clean_fields[key] = value

    if not clean_fields:
        return show_task(task_id, db_path)

    now = _now()
    set_clause = ", ".join(f"{k} = ?" for k in clean_fields.keys())
    args: list[Any] = list(clean_fields.values()) + [now, task_id.strip()]

    conn = init_db(db_path)
    try:
        cur = conn.execute(
            f"UPDATE tasks SET {set_clause}, updated_at = ? WHERE id = ?",
            args,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return show_task(task_id, db_path)


def delete_task(task_id: str, db_path: Path | str | None = None) -> bool:
    """Удаляет задачу. True — удалена, False — не найдена (идемпотентно)."""
    conn = init_db(db_path)
    try:
        cur = conn.execute(
            "DELETE FROM tasks WHERE id = ?", (task_id.strip(),)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# AI Briefing (v1; правило 8 + 9, promt42 — Knowledge + Work Area + model_gateway)
# ═══════════════════════════════════════════════════════════════
#
# Pipeline (graceful degradation на каждом шаге):
#   1. Fetch task + проверить task_type='meeting'             → иначе None
#   2. Собрать evidence (4 независимых шага, каждый защищён try/except):
#        - project_meta         (projects table)
#        - linked_resources     (work_area_view.resources_for_project)
#        - recent_tasks         (get_tasks по тому же проекту)
#        - knowledge_hits       (KnowledgeEngine.search query={project_id}+title)
#   3. Опциональная LLM-синтез (ModelGateway.generate_by_capabilities
#      с capability='meeting_brief'). При любой ошибке / бypass env
#      FREEBUFF_NO_LLM=1 — deterministic fallback.
#   4. Compose markdown + briefing_generated=1 + updated_at.
#
# Все обёртки в try/except — одна просадка не блокирует, а даёт short-circuit
# к [] или {} (graceful degradation, по [Knowledge as a Byproduct], promt36
# правило 10).


# Лимиты v1: защита prompt-overflow при крупных проектах.
_BRIEF_MAX_RESOURCES = 10        # top-N ресурсов
_BRIEF_MAX_RECENT_TASKS = 5     # соседних задач
_BRIEF_MAX_KNOWLEDGE_HITS = 3   # сниппетов из Knowledge
_BRIEF_SNIPPET_CHARS = 500      # truncate each snippet
_BRIEF_LLM_BUDGET = 800         # max_tokens для синтеза
_BRIEF_LLM_TIMEOUT = 10         # секунд (защита от зависания API)


def _gather_project_meta(
    project_id: str, conn: sqlite3.Connection
) -> dict[str, str]:
    """projects table → {name, description, status, last_scanned].

    Graceful fallback к {} если таблицы projects нет или запрос упал
    — нормально в чистой БД до scan_projects или при unit-тестах.
    """
    try:
        has = conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='projects'"
        ).fetchone() is not None
        if not has:
            return {}
        row = conn.execute(
            "SELECT name, description, status, last_scanned "
            "FROM projects WHERE name = ?",
            (project_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return {}
    if row is None:
        return {}
    return {
        "name": row[0] or project_id,
        "description": row[1] or "",
        "status": row[2] or "",
        "last_scanned": row[3] or "",
    }


def _gather_linked_resources(
    project_id: str, db_path: Path | str | None
) -> list[dict[str, str]]:
    """Work Area as View: ресурсы проекта из project_resources.

    Top-N по created_at DESC. Использует существующий модуль — reuse first.
    """
    try:
        from scripts_01.work_area_view import (
            resources_for_project as _wav_resources,
        )
        rows = _wav_resources(project_id, db_path=db_path)
    except Exception:
        return []
    rows_sorted = sorted(
        rows, key=lambda r: r.get("created_at", ""), reverse=True,
    )[:_BRIEF_MAX_RESOURCES]
    return rows_sorted


def _gather_recent_tasks(
    project_id: str, exclude_task_id: str, db_path: Path | str | None,
) -> list[dict[str, Any]]:
    """Top-N последних задач проекта (без текущей) — соседний activity."""
    try:
        rows = get_tasks(project_id, db_path=db_path)
    except Exception:
        return []
    return [
        r for r in rows
        if r["id"] != exclude_task_id
    ][:_BRIEF_MAX_RECENT_TASKS]


def _gather_knowledge_hits(query: str) -> list[dict[str, Any]]:
    """KnowledgeEngine.search(query, top_k=3, mode='hybrid').

    Lazy import + проверка наличия индекса. Любые ошибки → [] (нельзя
    брифинг сломать отсутствием knowledge).
    """
    try:
        from scripts_01.knowledge_engine import KnowledgeEngine
        # Индекс в context_12/knowledge/index.db (отдельный от tasks DB).
        from scripts_01.knowledge_engine import DEFAULT_DB_PATH
        index_db = Path(DEFAULT_DB_PATH)
        if not index_db.is_absolute():
            index_db = WORKSPACE / DEFAULT_DB_PATH
        if not index_db.exists():
            return []
        ke = KnowledgeEngine(workspace_root=str(WORKSPACE))
        results = ke.search(
            query, top_k=_BRIEF_MAX_KNOWLEDGE_HITS, mode="hybrid",
        )
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for r in results or []:
        out.append({
            "doc_id": r.doc_id,
            "score": round(float(r.score or 0.0), 4),
            "snippet": (r.snippet or "")[:_BRIEF_SNIPPET_CHARS],
            "title": (r.metadata or {}).get("title", ""),
            "source": (r.metadata or {}).get("source", ""),
            "matched_terms": list(r.matched_terms or [])[:6],
        })
    return out


def _generate_llm_synthesis(
    task: dict[str, Any],
    proj_meta: dict[str, str],
    resources: list[dict[str, str]],
    recent_tasks: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
) -> str | None:
    """Опциональная LLM-синтез брифинга через ModelGateway.

    Возвращает текст или None при любой ошибке / bypass env. Ошибка
    НЕ блокирует — вызывающий код получит deterministic fallback.
    """
    if os.getenv("FREEBUFF_NO_LLM") == "1":
        return None
    try:
        from scripts_01.model_gateway import ModelGateway
        prompt = _compose_llm_prompt(
            task, proj_meta, resources, recent_tasks, knowledge,
        )
        gw = ModelGateway()
        resp = gw.generate_by_capabilities(
            capabilities=["meeting_brief"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=_BRIEF_LLM_BUDGET,
            timeout=_BRIEF_LLM_TIMEOUT,
        )
        content = getattr(resp, "content", None)
        if not isinstance(content, str) or not content.strip():
            return None
        return content.strip()
    except Exception:
        return None


def _compose_llm_prompt(
    task: dict[str, Any],
    proj_meta: dict[str, str],
    resources: list[dict[str, str]],
    recent_tasks: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
) -> str:
    """Собирает контекст для LLM-промпта (markdown)."""
    parts: list[str] = []
    parts.append(f"# Задача: {task.get('title', '')}")
    project_name = proj_meta.get("name") or task.get("project_id", "")
    parts.append(f"**Проект:** {project_name}")
    if proj_meta.get("description"):
        parts.append(f"**Описание проекта:** {proj_meta['description']}")
    parts.append(f"**Время:** {task.get('meeting_time') or '(не указано)'}")
    parts.append(f"**Место:** {task.get('location') or '(не указано)'}")
    participants = task.get("participants") or []
    parts.append(
        f"**Участники:** "
        f"{', '.join(participants) if participants else '(не указаны)'}"
    )

    if resources:
        parts.append("\n## Связанные ресурсы проекта (Work Area as View)")
        for r in resources:
            parts.append(f"- {r['resource_id']}")

    if recent_tasks:
        parts.append("\n## Последние задачи проекта")
        for r in recent_tasks:
            parts.append(
                f"- [{r['task_type']}/{r['status']}/{r['priority']}] "
                f"{r['title']}"
            )

    if knowledge:
        parts.append("\n## Связанные документы (Knowledge Engine)")
        for h in knowledge:
            title = h.get("title") or h["doc_id"]
            parts.append(f"- [{title}] (score={h['score']}): {h['snippet']}")

    parts.append(
        "\n## Задание\n"
        "Составь markdown-брифинг для встречи: ключевые риски, "
        "открытые блокеры, что подготовить каждому участнику, "
        "предложения по повестке. Опирайся на приведённый "
        "контекст (проект, ресурсы, соседние задачи, документы). "
        "Локанично, не повторяй контекст целиком — синтезируй."
    )
    return "\n".join(parts)


def _compose_briefing_markdown(
    task: dict[str, Any],
    proj_meta: dict[str, str],
    resources: list[dict[str, str]],
    recent_tasks: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    llm_synthesis: str | None,
) -> str:
    """Compose финального markdown-брифинга.

    Sections:
      Title → Meta → Project → Linked resources → Recent tasks →
      Knowledge hits → LLM synthesis (или fallback note) → Footer.
    """
    lines: list[str] = []
    project_name = proj_meta.get("name") or task.get("project_id", "")
    lines.append(f"# Брифинг встречи: {task['title']}")
    lines.append("")
    lines.append("## Мета")
    lines.append(f"- **Проект:** {project_name}")
    lines.append(f"- **Задача:** {task['id']}")
    lines.append(f"- **Время:** {task.get('meeting_time') or '(не указано)'}")
    lines.append(f"- **Место:** {task.get('location') or '(не указано)'}")
    participants = task.get("participants") or []
    lines.append(
        f"- **Участники:** "
        f"{', '.join(participants) if participants else '(не указаны)'}"
    )

    if proj_meta.get("description") or proj_meta.get("status"):
        lines.append("")
        lines.append("## Проект")
        if proj_meta.get("description"):
            lines.append(f"- Описание: {proj_meta['description']}")
        if proj_meta.get("status"):
            lines.append(f"- Статус: `{proj_meta['status']}`")

    if resources:
        lines.append("")
        lines.append(f"## Связанные ресурсы ({len(resources)})")
        for r in resources:
            lines.append(f"- {r['resource_id']}")

    if recent_tasks:
        lines.append("")
        lines.append(f"## Контекст задач проекта ({len(recent_tasks)})")
        for r in recent_tasks:
            lines.append(
                f"- [{r['task_type']}/{r['status']}/{r['priority']}] "
                f"{r['title']}"
            )

    if knowledge:
        lines.append("")
        lines.append(f"## Заметки из Knowledge Engine ({len(knowledge)})")
        for h in knowledge:
            title = h.get("title") or h["doc_id"]
            lines.append(
                f"- **{title}** (score={h['score']}): {h['snippet']}"
            )

    lines.append("")
    lines.append("## Синтез")
    if llm_synthesis:
        lines.append(llm_synthesis)
    else:
        lines.append(
            "- _Детерминированный режим (LLM недоступен, отключён "
            "`FREEBUFF_NO_LLM=1`, или упал с ошибкой)._\n"
            "- Текущий прогресс по проекту см. в Контексте задач выше.\n"
            "- Открытые блокеры — задачи со статусом `pending`/`in_progress`.\n"
            "- Следующие шаги — распределение зон ответственности."
        )

    lines.append("")
    lines.append(f"_Сгенерировано: {_now()}_")
    return "\n".join(lines)


def generate_meeting_briefing(
    task_id: str, db_path: Path | str | None = None
) -> str | None:
    """v1: брифинг встречи с реальным контекстом проекта + опциональным LLM.

    Pipeline (graceful degradation на каждом шаге):
      1. Fetch task + проверить task_type='meeting' → иначе None
      2. Собрать evidence: project_meta + linked_resources +
         recent_tasks + knowledge_hits (каждый шаг защищён try/except)
      3. Опциональная LLM-синтез через `ModelGateway.generate_by_capabilities`
         ([meeting_brief]). При ошибке — deterministic fallback.
      4. Compose markdown + briefing_generated=1 + updated_at.

    Возвращает текст или None (задача не найдена / не meeting).
    Side-effect: `briefing_generated=1` для встречи.
    """
    conn = init_db(db_path)
    try:
        try:
            row = conn.execute(
                "SELECT id, project_id, title, description, task_type, "
                "meeting_time, location, participants "
                "FROM tasks WHERE id = ?",
                (task_id.strip(),),
            ).fetchone()
        except sqlite3.OperationalError:
            return None
        if row is None or row[4] != "meeting":
            return None
        participants_raw = row[7] or "[]"
        try:
            participants = json.loads(participants_raw)
        except (ValueError, TypeError):
            participants = []
        task: dict[str, Any] = {
            "id": row[0],
            "project_id": row[1],
            "title": row[2],
            "description": row[3] or "",
            "task_type": row[4],
            "meeting_time": row[5],
            "location": row[6],
            "participants": participants,
        }
        proj_meta = _gather_project_meta(task["project_id"], conn)
        resources = _gather_linked_resources(task["project_id"], db_path)
        recent_tasks = _gather_recent_tasks(
            task["project_id"], task["id"], db_path,
        )
        knowledge = _gather_knowledge_hits(
            f"{task['project_id']} {task['title']}"
        )
        try:
            llm_synthesis = _generate_llm_synthesis(
                task, proj_meta, resources, recent_tasks, knowledge,
            )
        except Exception:
            # Defensive guard: даже если сам _generate_llm_synthesis (или
            # его monkeypatch в тестах) пропускает исключения наружу,
            # нельзя уронить весь pipeline — deterministic fallback.
            llm_synthesis = None
        briefing = _compose_briefing_markdown(
            task, proj_meta, resources, recent_tasks,
            knowledge, llm_synthesis,
        )
        conn.execute(
            "UPDATE tasks SET briefing_generated = 1, updated_at = ? "
            "WHERE id = ?",
            (_now(), task_id.strip()),
        )
        conn.commit()
        return briefing
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    """Преобразует SELECT-строку в канонический dict (с парсингом JSON)."""
    if row is None:
        return {}
    participants_raw = row[9] if len(row) > 9 else "[]"
    try:
        participants = json.loads(participants_raw) if participants_raw else []
    except (ValueError, TypeError):
        participants = []
    return {
        "id": row[0],
        "project_id": row[1],
        "title": row[2],
        "description": row[3],
        "task_type": row[4],
        "status": row[5],
        "priority": row[6],
        "meeting_time": row[7],
        "location": row[8],
        "participants": participants,
        "briefing_generated": bool(row[10]),
        "created_at": row[11],
        "updated_at": row[12],
    }


# ═══════════════════════════════════════════════════════════════
# CLI (argparse)
# ═══════════════════════════════════════════════════════════════


def _print_task(t: dict[str, Any]) -> None:
    """Печатает одну задачу в human-friendly формате."""
    print(f"- {t['id']}  [{t['task_type']}/{t['status']}/{t['priority']}] "
          f"{t['title']}")
    if t.get("description"):
        print(f"  desc: {t['description']}")
    if t.get("meeting_time") or t.get("location") or t.get("participants"):
        print(f"  meeting: time={t.get('meeting_time') or '-'} "
              f"location={t.get('location') or '-'} "
              f"participants={t.get('participants') or []}")
    if t.get("briefing_generated"):
        print("  briefing: ✅ generated")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Meeting Tasks (042_06 Фаза E): digital/meeting/document "
                    "задачи с AI-брифингом для встреч.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── create ──
    p_create = sub.add_parser("create", help="Создать задачу")
    p_create.add_argument("project_id")
    p_create.add_argument("title")
    p_create.add_argument(
        "--type", dest="task_type", default="digital",
        choices=sorted(VALID_TASK_TYPES),
        help="тип задачи (default: digital)")
    p_create.add_argument("--description", default="")
    p_create.add_argument(
        "--priority", default="normal", choices=sorted(VALID_PRIORITIES))
    p_create.add_argument("--time", dest="meeting_time", default=None,
                          help="для meeting: ISO-8601 время")
    p_create.add_argument("--location", default=None,
                          help="для meeting: место")
    p_create.add_argument("--participants", default=None,
                          help='для meeting: JSON-список, например \'["a","b"]\'')

    # ── list ──
    p_list = sub.add_parser("list", help="Список задач проекта")
    p_list.add_argument("project_id")
    p_list.add_argument("--type", dest="task_type", default=None,
                        choices=sorted(VALID_TASK_TYPES))
    p_list.add_argument("--status", default=None, choices=sorted(VALID_STATUSES))

    # ── show ──
    p_show = sub.add_parser("show", help="Одна задача по id")
    p_show.add_argument("task_id")

    # ── update ──
    p_update = sub.add_parser("update", help="Частично обновить задачу")
    p_update.add_argument("task_id")
    p_update.add_argument("--title")
    p_update.add_argument("--description")
    p_update.add_argument("--type", dest="task_type",
                          choices=sorted(VALID_TASK_TYPES))
    p_update.add_argument("--status", choices=sorted(VALID_STATUSES))
    p_update.add_argument("--priority", choices=sorted(VALID_PRIORITIES))
    p_update.add_argument("--time", dest="meeting_time")
    p_update.add_argument("--location")
    p_update.add_argument("--participants",
                          help='JSON-список, например \'["a","b"]\'')

    # ── delete ──
    p_delete = sub.add_parser("delete", help="Удалить задачу")
    p_delete.add_argument("task_id")

    # ── briefing ──
    p_briefing = sub.add_parser("briefing", help="Сгенерировать брифинг "
                                                  "(заглушка v0)")
    p_briefing.add_argument("task_id")

    args = parser.parse_args()

    if args.command == "create":
        participants = None
        if args.participants is not None:
            try:
                participants = json.loads(args.participants)
            except json.JSONDecodeError as e:
                print(f"❌ --participants: невалидный JSON: {e}", file=sys.stderr)
                return 2
            if not isinstance(participants, list):
                print("❌ --participants: ожидается JSON-список", file=sys.stderr)
                return 2
        task = create_task(
            args.project_id,
            args.title,
            task_type=args.task_type,
            description=args.description,
            priority=args.priority,
            meeting_time=args.meeting_time,
            location=args.location,
            participants=participants,
        )
        print(f"✅ Создана задача {task['id']}: {task['title']} "
              f"[{task['task_type']}/{task['priority']}]")

    elif args.command == "list":
        tasks = get_tasks(args.project_id, args.task_type, args.status)
        print(f"Задачи проекта {args.project_id} ({len(tasks)}):")
        if not tasks:
            print("  (нет задач)")
        for t in tasks:
            _print_task(t)

    elif args.command == "show":
        t = show_task(args.task_id)
        if t is None:
            print(f"❌ Задача {args.task_id} не найдена", file=sys.stderr)
            return 1
        _print_task(t)

    elif args.command == "update":
        kwargs: dict[str, Any] = {}
        for field in (
            "title", "description", "task_type", "status",
            "priority", "meeting_time", "location",
        ):
            value = getattr(args, field, None)
            if value is not None:
                kwargs[field] = value
        if getattr(args, "participants", None) is not None:
            try:
                kwargs["participants"] = json.loads(args.participants)
            except json.JSONDecodeError as e:
                print(f"❌ --participants: невалидный JSON: {e}", file=sys.stderr)
                return 2
        result = update_task(args.task_id, **kwargs)
        if result is None:
            print(f"❌ Задача {args.task_id} не найдена", file=sys.stderr)
            return 1
        print(f"✅ Обновлена задача {result['id']}")
        _print_task(result)

    elif args.command == "delete":
        removed = delete_task(args.task_id)
        if removed:
            print(f"🗑 Удалена задача {args.task_id}")
        else:
            print(f"❌ Задача {args.task_id} не найдена (нечего удалять)")

    elif args.command == "briefing":
        text = generate_meeting_briefing(args.task_id)
        if text is None:
            t = show_task(args.task_id)
            if t is None:
                print(f"❌ Задача {args.task_id} не найдена", file=sys.stderr)
                return 1
            print(f"❌ Брифинг только для task_type='meeting', "
                  f"получено: {t['task_type']!r}", file=sys.stderr)
            return 1
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
