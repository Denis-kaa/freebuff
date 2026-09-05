#!/usr/bin/env python3
"""whim_store.py — persistent storage for Whims (mobile client sync).

Additive module (promt 111 / mobile frontend v0.1): хранит Whims,
приходящие от mobile-клиента Workspace OS через REST `POST /api/v1/whims`
(scripts_01/mcp_fastapi.py). Отдельная БД `data_13/whims.db` — чтобы не
трогать канонический `context.db` (Additive Architecture, B1).

Contract:
    init_db(db_path) -> sqlite3.Connection   # идемпотентно
    add_whim(text, *, client_id="", source="mobile", status="synced",
             db_path=None) -> dict           # создаёт Whim
    list_whims(*, limit=100, db_path=None) -> list[dict]
    count(db_path=None) -> int

Usage:
    python scripts_01/whim_store.py add "мысль"     # CLI smoke
    python scripts_01/whim_store.py list [--limit N]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

DB_PATH = WORKSPACE / "data_13" / "whims.db"

VALID_STATUSES = frozenset({"local", "pending_sync", "synced", "conflict"})


def _now() -> str:
    """ISO-8601 UTC timestamp (suffix `+00:00`)."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Короткий стабильный id: `wh-<8 hex>`."""
    return f"wh-{uuid.uuid4().hex[:8]}"


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Создаёт таблицу `whims` (если её нет) и возвращает соединение.

    CREATE TABLE IF NOT EXISTS → повторные вызовы идемпотентны.
    WAL mode — как в каноническом context.db (DEBT-5.22 guard).
    """
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS whims (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            client_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'mobile',
            status TEXT NOT NULL DEFAULT 'synced',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_whims_created ON whims(created_at)"
    )
    conn.commit()
    return conn


def add_whim(
    text: str,
    *,
    client_id: str = "",
    source: str = "mobile",
    status: str = "synced",
    db_path: Path | str | None = None,
) -> dict[str, str]:
    """Создать Whim и вернуть его dict-representation.

    Raises:
        ValueError: пустой text или невалидный status.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text (non-empty string) required")
    if status not in VALID_STATUSES:
        raise ValueError(
            f"invalid status {status!r}: must be one of {sorted(VALID_STATUSES)}"
        )
    whim = {
        "id": _new_id(),
        "text": text.strip(),
        "client_id": client_id,
        "source": source,
        "status": status,
        "created_at": _now(),
    }
    conn = init_db(db_path)
    try:
        conn.execute(
            "INSERT INTO whims (id, text, client_id, source, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                whim["id"],
                whim["text"],
                whim["client_id"],
                whim["source"],
                whim["status"],
                whim["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return whim


def _row_to_dict(row: tuple) -> dict[str, str]:
    return {
        "id": row[0],
        "text": row[1],
        "client_id": row[2],
        "source": row[3],
        "status": row[4],
        "created_at": row[5],
    }


def list_whims(
    *, limit: int = 100, db_path: Path | str | None = None
) -> list[dict[str, str]]:
    """Последние Whims (новые сначала). Мягкий fallback: нет таблицы — [].
    """
    conn = init_db(db_path)
    try:
        has = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='whims'"
        ).fetchone() is not None
        if not has:
            return []
        rows = conn.execute(
            "SELECT id, text, client_id, source, status, created_at "
            "FROM whims ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def count(db_path: Path | str | None = None) -> int:
    """Число сохранённых Whims (0 если БД пуста)."""
    return len(list_whims(limit=10**9, db_path=db_path))


# ═══════════════════════════════════════════════════════════════
# CLI (smoke / inspection)
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    parser = argparse.ArgumentParser(description="Whim store CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="add a whim")
    p_add.add_argument("text")
    p_add.add_argument("--client-id", default="")
    p_add.add_argument("--db", default=None)

    p_list = sub.add_parser("list", help="list whims")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--db", default=None)

    args = parser.parse_args()

    if args.cmd == "add":
        whim = add_whim(args.text, client_id=args.client_id, db_path=args.db)
        print(json.dumps(whim, ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        items = list_whims(limit=args.limit, db_path=args.db)
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            for w in items:
                print(f"{w['created_at']}  [{w['status']}]  {w['text']}")


if __name__ == "__main__":
    main()
