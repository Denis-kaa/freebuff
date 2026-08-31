"""
Кэш диалогов и сообщений в SQLite — офлайн-история (per SPEC: «Кеш чатов, сообщений»).

Использует aiosqlite, если он установлен (как в requirements.txt), иначе —
stdlib sqlite3 в отдельном потоке через asyncio.to_thread (без зависимостей).
Ни один вызов не блокирует event loop Textual.

Использование:
    cache = MessageCache(Path("tg_cache.db"))
    await cache.open()
    await cache.save_dialogs(dialogs)          # объекты с .id/.name/.unread_count
    await cache.save_messages(chat_id, rows)   # rows: (msg_id, sender, ts, text, media)
    dialogs = await cache.get_dialogs()
    messages = await cache.get_messages(chat_id, limit=30)
    await cache.close()
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable

try:
    import aiosqlite
    _HAS_AIOSQLITE = True
except ImportError:  # pragma: no cover — aiosqlite опционален
    _HAS_AIOSQLITE = False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dialogs (
    chat_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL DEFAULT '',
    unread  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    chat_id INTEGER NOT NULL,
    msg_id  INTEGER NOT NULL,
    sender  TEXT NOT NULL DEFAULT '',
    ts      REAL NOT NULL DEFAULT 0,
    text    TEXT NOT NULL DEFAULT '',
    media   TEXT,
    PRIMARY KEY (chat_id, msg_id)
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages(chat_id, ts);
"""


class _SQLite:
    """Единый async API поверх aiosqlite или sqlite3+to_thread."""

    def __init__(self, path: Path):
        self._path = str(path)
        self._use_aiosqlite = _HAS_AIOSQLITE
        self._conn: Any = None
        self._lock = threading.Lock()

    async def open(self) -> None:
        if self._use_aiosqlite:
            self._conn = await aiosqlite.connect(self._path)
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
        else:
            def _connect():
                c = sqlite3.connect(self._path, check_same_thread=False)
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("PRAGMA synchronous=NORMAL")
                return c

            self._conn = await asyncio.to_thread(_connect)

    async def executescript(self, script: str) -> None:
        if self._use_aiosqlite:
            await self._conn.executescript(script)
        else:
            def _run():
                with self._lock:
                    self._conn.executescript(script)

            await asyncio.to_thread(_run)

    async def execute(self, sql: str, params: tuple = ()) -> None:
        if self._use_aiosqlite:
            cur = await self._conn.execute(sql, params)
            await self._conn.commit()
            await cur.close()
        else:
            def _run():
                with self._lock:
                    self._conn.execute(sql, params)
                    self._conn.commit()

            await asyncio.to_thread(_run)

    async def executemany(self, sql: str, rows: list[tuple]) -> None:
        if not rows:
            return
        if self._use_aiosqlite:
            await self._conn.executemany(sql, rows)
            await self._conn.commit()
        else:
            def _run():
                with self._lock:
                    self._conn.executemany(sql, rows)
                    self._conn.commit()

            await asyncio.to_thread(_run)

    async def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        if self._use_aiosqlite:
            cur = await self._conn.execute(sql, params)
            rows = await cur.fetchall()
            await cur.close()
            return list(rows)

        def _run():
            with self._lock:
                return self._conn.execute(sql, params).fetchall()

        return await asyncio.to_thread(_run)

    async def close(self) -> None:
        if self._conn is None:
            return
        if self._use_aiosqlite:
            await self._conn.close()
        else:
            def _run():
                with self._lock:
                    self._conn.close()

            await asyncio.to_thread(_run)
        self._conn = None


class MessageCache:
    """Кэш диалогов и сообщений. Все методы асинхронные и неблокирующие."""

    def __init__(self, db_path: Path):
        self._db = _SQLite(db_path)

    async def open(self) -> None:
        await self._db.open()
        await self._db.executescript(_SCHEMA)

    async def close(self) -> None:
        await self._db.close()

    # ── диалоги ─────────────────────────────────────────────

    async def save_dialogs(self, dialogs: Iterable[Any]) -> None:
        """dialogs — любые объекты с .id/.name/.unread_count (Telethon Dialog и др.)."""
        rows = [
            (int(d.id), str(d.name or ""), int(d.unread_count or 0))
            for d in dialogs
        ]
        await self._db.executemany(
            "INSERT OR REPLACE INTO dialogs(chat_id, name, unread) VALUES(?,?,?)",
            rows,
        )

    async def get_dialogs(self, limit: int = 50) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT chat_id, name, unread FROM dialogs "
            "ORDER BY unread DESC, chat_id LIMIT ?",
            (int(limit),),
        )
        return [
            {"id": r[0], "name": r[1], "unread_count": r[2]} for r in rows
        ]

    # ── сообщения ───────────────────────────────────────────

    async def save_messages(self, chat_id: int, rows: Iterable[tuple], cap: int | None = None) -> None:
        """rows: (msg_id, sender, ts, text, media) — подготавливает вызывающий код.

        cap — лимит сообщений на чат в кэше (None — без лимита). После вставки
        самые старые строки сверх cap удаляются: кэш не растёт бесконечно, и
        открытие чата не тащит за собой всю историю.
        """
        data = [
            (
                int(chat_id),
                int(r[0]),
                str(r[1] or ""),
                float(r[2] or 0),
                str(r[3] or ""),
                (r[4] if len(r) > 4 else None),
            )
            for r in rows
        ]
        await self._db.executemany(
            "INSERT OR REPLACE INTO messages(chat_id, msg_id, sender, ts, text, media) "
            "VALUES(?,?,?,?,?,?)",
            data,
        )
        if cap is not None and int(cap) > 0:
            # Оставляем самые свежие cap строк (rowid существует: PK не INTEGER)
            await self._db.execute(
                "DELETE FROM messages WHERE chat_id=? AND rowid NOT IN ("
                "SELECT rowid FROM messages WHERE chat_id=? "
                "ORDER BY ts DESC, msg_id DESC LIMIT ?)",
                (int(chat_id), int(chat_id), int(cap)),
            )

    async def get_messages(self, chat_id: int, limit: int = 50) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT msg_id, sender, ts, text, media FROM messages "
            "WHERE chat_id=? ORDER BY ts DESC LIMIT ?",
            (int(chat_id), int(limit)),
        )
        # возвращаем в хронологическом порядке (старые сверху)
        return [
            {'msg_id': r[0], 'sender': r[1], 'ts': r[2], 'text': r[3], 'media': r[4]}
            for r in reversed(rows)
        ]

    async def prune_older_than(self, days: int) -> int:
        """Удалить сообщения старше days дней. Возвращает число удалённых строк.

        Второй лимит кэша поверх cache_cap: cache_cap ограничивает количество
        сообщений на чат, а это правило — срок хранения. Вызывается при старте
        приложения (см. _init_cache): старые записи не должны копиться вечно
        даже в чатах, куда давно не заходили. days <= 0 — ничего не удаляем.
        """
        if int(days) <= 0:
            return 0
        cutoff = time.time() - int(days) * 86400.0
        rows = await self._db.fetchall(
            "SELECT COUNT(*) FROM messages WHERE ts < ?", (cutoff,)
        )
        await self._db.execute(
            "DELETE FROM messages WHERE ts < ?", (cutoff,)
        )
        return int(rows[0][0]) if rows else 0

    async def get_messages_before(self, chat_id: int, before_ts: float, limit: int = 30) -> list[dict]:
        """Сообщения старше before_ts (для подгрузки истории скроллом вверх)."""
        rows = await self._db.fetchall(
            'SELECT msg_id, sender, ts, text, media FROM messages '
            'WHERE chat_id=? AND ts < ? ORDER BY ts DESC LIMIT ?',
            (int(chat_id), float(before_ts), int(limit)),
        )
        return [
            {'msg_id': r[0], 'sender': r[1], 'ts': r[2], 'text': r[3], 'media': r[4]}
            for r in reversed(rows)
        ]
