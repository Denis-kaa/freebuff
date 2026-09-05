"""Global Search (7.md §11-14, §49).

GET /search?q=wazzup → результаты по типам: projects, tasks, items, clients,
documents. Ранжирование по релевантности (7.md §14):
- точное совпадение display_id/title > префикс > подстрока.

Используем ILIKE + явный подсчёт релевантности (без тяжёлого Elasticsearch —
архитектура позволяет позже подключить trigram/pg_trgm, если потребуется).
"""

import re
from typing import Any, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Document, Project, ProjectItem, Task

# Веса (7.md §14): точное совпадение выше подстроки
_ESCAPE_RE = re.compile(r"[%_\\]")
LIMIT_PER_TYPE = 8


def _like(term: str) -> str:
    return f"%{_ESCAPE_RE.sub(lambda m: '\\\\' + m.group(0), term)}%"


def _q_safe(term: str) -> str:
    """Санитизация для ILIKE (не raw пользовательский SQL)."""
    return _like(term)


async def search_all(session: AsyncSession, workspace_id, q: str) -> dict[str, list[dict]]:
    """Ищет по всем типам. q уже обрезан/непустой."""
    term = q.strip()
    pattern = _q_safe(term)
    exact = term  # точное совпадение для display_id/title

    results: dict[str, list[dict]] = {
        "projects": [], "tasks": [], "items": [], "clients": [], "documents": [],
    }

    # --- Проекты (7.md §11): ID, название, юр.лицо, менеджер, клиент ---
    if term:
        proj_stmt = (
            select(
                Project.id, Project.display_id, Project.title, Project.client_legal_name,
                Project.manager_name, Project.stage, Project.deadline,
            )
            .where(
                Project.workspace_id == workspace_id,
                Project.archived_at.is_(None),
                or_(
                    Project.title.ilike(pattern),
                    Project.display_id.ilike(pattern),
                    Project.client_legal_name.ilike(pattern),
                    Project.manager_name.ilike(pattern),
                ),
            )
            .limit(LIMIT_PER_TYPE)
        )
        proj_rows = (await session.execute(proj_stmt)).all()
        for r in proj_rows:
            rank = _rank(term, [r.display_id, r.title, r.client_legal_name or "", r.manager_name or ""])
            results["projects"].append({
                "id": str(r.id), "display_id": r.display_id, "title": r.title,
                "client_legal_name": r.client_legal_name, "manager_name": r.manager_name,
                "stage": r.stage, "deadline": r.deadline.isoformat() if r.deadline else None,
                "rank": rank,
            })
        results["projects"].sort(key=lambda x: -x["rank"])

    # --- Клиенты (уникальные по юр.лицу) ---
    if term:
        client_stmt = (
            select(Project.client_legal_name, func.count(Project.id))
            .where(
                Project.workspace_id == workspace_id,
                Project.client_legal_name.isnot(None),
                Project.client_legal_name.ilike(pattern),
            )
            .group_by(Project.client_legal_name)
            .limit(LIMIT_PER_TYPE)
        )
        for name, cnt in (await session.execute(client_stmt)).all():
            results["clients"].append({"name": name, "projects_count": cnt})

    # --- Задачи (7.md §13) ---
    if term:
        task_stmt = (
            select(Task.id, Task.title, Task.status, Task.priority, Task.project_id, Project.display_id)
            .outerjoin(Project, Project.id == Task.project_id)
            .where(
                Task.title.ilike(pattern),
                (Project.id.is_(None)) | (Project.workspace_id == workspace_id),
            )
            .limit(LIMIT_PER_TYPE)
        )
        for tid, title, status, priority, pid, pdisplay in (await session.execute(task_stmt)).all():
            results["tasks"].append({
                "id": str(tid), "title": title, "status": status,
                "priority": priority, "project_id": str(pid) if pid else None,
                "project_display_id": pdisplay,
            })

    # --- Позиции (7.md §13) ---
    if term:
        item_stmt = (
            select(ProjectItem.id, ProjectItem.name, ProjectItem.project_id, Project.display_id)
            .join(Project, Project.id == ProjectItem.project_id)
            .where(Project.workspace_id == workspace_id, ProjectItem.name.ilike(pattern))
            .limit(LIMIT_PER_TYPE)
        )
        for iid, name, pid, pdisplay in (await session.execute(item_stmt)).all():
            results["items"].append({
                "id": str(iid), "name": name, "project_id": str(pid),
                "project_display_id": pdisplay,
            })

    # --- Документы (7.md §13) ---
    if term:
        doc_stmt = (
            select(Document.id, Document.document_type, Document.project_id, Document.doc_date, Project.display_id)
            .join(Project, Project.id == Document.project_id)
            .where(
                Project.workspace_id == workspace_id,
                or_(
                    Document.file_name.ilike(pattern),
                    Document.document_type.ilike(pattern),
                    Document.comment.ilike(pattern),
                ),
            )
            .limit(LIMIT_PER_TYPE)
        )
        for did, dtype, pid, ddate, pdisplay in (await session.execute(doc_stmt)).all():
            results["documents"].append({
                "id": str(did), "document_type": dtype, "project_id": str(pid),
                "doc_date": ddate.isoformat() if ddate else None, "project_display_id": pdisplay,
            })

    return results


def _rank(term: str, candidates: list[str]) -> int:
    """Релевантность: точное 100 > префикс 60 > подстрока 30 (7.md §14)."""
    t = term.strip().lower()
    if not t:
        return 0
    for c in candidates:
        cl = (c or "").strip().lower()
        if not cl:
            continue
        if cl == t:
            return 100
        if cl.startswith(t):
            return 60
        if t in cl:
            return 30
    return 10