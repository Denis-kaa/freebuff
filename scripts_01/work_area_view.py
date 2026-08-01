#!/usr/bin/env python3
"""work_area_view.py — Work Area as View: связь проектов и ресурсов.

Каноническое правило 2 (promt36/37): **Work Area — это НЕ папка и НЕ сущность.**
Это динамический список проектов, связанных с конкретным Resource
(«нажал на Telegram → увидел все проекты с Telegram»).

Реализация (ADR-008): таблица `project_resources(project_id, resource_id, created_at)`
в `data_13/context.db` + CLI `freebuff resource projects <resource_name>`.

Использование:
    python scripts_01/work_area_view.py link <project> <resource>
    python scripts_01/work_area_view.py unlink <project> <resource>
    python scripts_01/work_area_view.py projects <resource>   # Work Area as View
    python scripts_01/work_area_view.py resources <project>
    python scripts_01/work_area_view.py list
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

DB_PATH = WORKSPACE / "data_13" / "context.db"


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Создаёт таблицу project_resources и возвращает соединение."""
    path = Path(db_path) if db_path else DB_PATH
    os.makedirs(path.parent, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_resources (
            project_id  TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            PRIMARY KEY (project_id, resource_id)
        )
    """)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def link(project_id: str, resource_id: str, db_path: Path | str | None = None) -> bool:
    """Связывает проект с ресурсом. Возвращает True, если связь создана.

    Повторный вызов (та же пара) — идемпотентен, возвращает False.
    """
    project_id = project_id.strip()
    resource_id = resource_id.strip()
    if not project_id or not resource_id:
        raise ValueError("project_id и resource_id обязательны")
    conn = init_db(db_path)
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO project_resources (project_id, resource_id, created_at) "
            "VALUES (?, ?, ?)",
            (project_id, resource_id, _now()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def unlink(project_id: str, resource_id: str, db_path: Path | str | None = None) -> bool:
    """Удаляет связь проекта с ресурсом. Возвращает True, если связь была удалена."""
    conn = init_db(db_path)
    try:
        cur = conn.execute(
            "DELETE FROM project_resources WHERE project_id = ? AND resource_id = ?",
            (project_id.strip(), resource_id.strip()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def projects_for_resource(resource_id: str, db_path: Path | str | None = None) -> list[dict[str, Any***REMOVED******REMOVED***:
    """Work Area as View: список проектов, связанных с ресурсом.

    Args:
        resource_id: имя ресурса (например, "Telegram").
        db_path: путь к БД (для тестов).

    Returns:
        Список проектов с деталями из таблицы projects (если она есть):
        [{"project_id", "description", "category", "status"***REMOVED******REMOVED***. Если таблицы
        projects в БД нет (scan_projects не запускался) — детали пустые.
    """
    conn = init_db(db_path)
    try:
        has_projects = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'"
        ).fetchone() is not None
        if has_projects:
            rows = conn.execute(
                """
                SELECT pr.project_id, COALESCE(p.description, ''),
                       COALESCE(p.category, ''), COALESCE(p.status, '')
                FROM project_resources pr
                LEFT JOIN projects p ON p.name = pr.project_id
                WHERE pr.resource_id = ?
                ORDER BY pr.project_id
                """,
                (resource_id.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT project_id, '', '', '' FROM project_resources "
                "WHERE resource_id = ? ORDER BY project_id",
                (resource_id.strip(),),
            ).fetchall()
    finally:
        conn.close()
    return [
        {"project_id": r[0***REMOVED***, "description": r[1***REMOVED***, "category": r[2***REMOVED***, "status": r[3***REMOVED******REMOVED***
        for r in rows
    ***REMOVED***


def resources_for_project(project_id: str, db_path: Path | str | None = None) -> list[dict[str, str***REMOVED******REMOVED***:
    """Список ресурсов, связанных с проектом."""
    conn = init_db(db_path)
    try:
        rows = conn.execute(
            "SELECT resource_id, created_at FROM project_resources "
            "WHERE project_id = ? ORDER BY resource_id",
            (project_id.strip(),),
        ).fetchall()
    finally:
        conn.close()
    return [{"resource_id": r[0***REMOVED***, "created_at": r[1***REMOVED******REMOVED*** for r in rows***REMOVED***


def list_links(db_path: Path | str | None = None) -> list[dict[str, str***REMOVED******REMOVED***:
    """Все связи проект ↔ ресурс."""
    conn = init_db(db_path)
    try:
        rows = conn.execute(
            "SELECT project_id, resource_id, created_at FROM project_resources "
            "ORDER BY project_id, resource_id"
        ).fetchall()
    finally:
        conn.close()
    return [{"project_id": r[0***REMOVED***, "resource_id": r[1***REMOVED***, "created_at": r[2***REMOVED******REMOVED*** for r in rows***REMOVED***


# ── CLI ───────────────────────────────────────────────────────

def print_projects(resource_id: str, db_path: Path | str | None = None) -> None:
    """Печатает список проектов для ресурса (Work Area as View).

    Используется и модульным CLI, и командой `freebuff resource projects`.
    """
    projects = projects_for_resource(resource_id, db_path)
    print(f"Проекты, связанные с {resource_id***REMOVED***:")
    if not projects:
        print("  (нет связей)")
        return
    for p in projects:
        suffix = f" ({p['description'***REMOVED******REMOVED***)" if p["description"***REMOVED*** else ""
        print(f"  - {p['project_id'***REMOVED******REMOVED***{suffix***REMOVED***")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Work Area as View: проекты, связанные с ресурсом (канон promt36/37)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_link = sub.add_parser("link", help="Связать проект с ресурсом")
    p_link.add_argument("project_id")
    p_link.add_argument("resource_id")

    p_unlink = sub.add_parser("unlink", help="Удалить связь проект ↔ ресурс")
    p_unlink.add_argument("project_id")
    p_unlink.add_argument("resource_id")

    p_projects = sub.add_parser("projects", help="Список проектов для ресурса (Work Area as View)")
    p_projects.add_argument("resource_id")

    p_resources = sub.add_parser("resources", help="Список ресурсов для проекта")
    p_resources.add_argument("project_id")

    sub.add_parser("list", help="Все связи проект ↔ ресурс")

    args = parser.parse_args()

    if args.command == "link":
        created = link(args.project_id, args.resource_id)
        print(f"🔗 {'Связь создана' if created else 'Связь уже существует'***REMOVED***: "
              f"{args.project_id***REMOVED*** ↔ {args.resource_id***REMOVED***")
    elif args.command == "unlink":
        removed = unlink(args.project_id, args.resource_id)
        print(f"🗑 {'Связь удалена' if removed else 'Связь не найдена'***REMOVED***: "
              f"{args.project_id***REMOVED*** ↔ {args.resource_id***REMOVED***")
    elif args.command == "projects":
        print_projects(args.resource_id)
    elif args.command == "resources":
        resources = resources_for_project(args.project_id)
        print(f"Ресурсы, связанные с {args.project_id***REMOVED***:")
        if not resources:
            print("  (нет связей)")
        for r in resources:
            print(f"  - {r['resource_id'***REMOVED******REMOVED***")
    elif args.command == "list":
        links = list_links()
        print(f"Связи проект ↔ ресурс ({len(links)***REMOVED***):")
        for l in links:
            print(f"  - {l['project_id'***REMOVED******REMOVED*** ↔ {l['resource_id'***REMOVED******REMOVED***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
