"""
Event Store — структурированное хранилище событий.

Основание: docs_10/core/EVENT_PLATFORM_SPECIFICATION.md §3
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional, Tuple

from freebuff_plugin_03.event import EventEntry, EventQuery


WORKSPACE = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = "context_12/events.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class EventStore:
    """Структурированное хранилище событий.

    Расширяет Event Log с категоризацией, поиском, FTS5 и агрегацией.

    Использование:
        store = EventStore()
        store.store(Event(type="task.completed", source="orchestrator", data={...}))
        entries = store.query(EventQuery(event_type="task.*", limit=10))
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or (WORKSPACE / DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._init_db()

    # ══════════════════════════════════════════════════════════
    # Database Init
    # ══════════════════════════════════════════════════════════

    def _init_db(self) -> None:
        """Инициализирует БД: создаёт таблицы, индексы, FTS5, триггеры."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        if SCHEMA_PATH.exists():
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
        else:
            schema = self._builtin_schema()

        with self._connect() as conn:
            conn.executescript(schema)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _builtin_schema() -> str:
        """Встроенная схема на случай отсутствия schema.sql."""
        return """
        CREATE TABLE IF NOT EXISTS event_store (
            event_id        TEXT PRIMARY KEY,
            event_type      TEXT NOT NULL,
            source          TEXT DEFAULT '',
            correlation_id  TEXT DEFAULT '',
            session_id      TEXT DEFAULT '',
            project         TEXT DEFAULT '',
            user_id         TEXT DEFAULT '',
            data_json       TEXT DEFAULT '{}',
            metadata_json   TEXT DEFAULT '{}',
            timestamp       TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_es_type ON event_store(event_type);
        CREATE INDEX IF NOT EXISTS idx_es_correlation ON event_store(correlation_id);
        CREATE INDEX IF NOT EXISTS idx_es_session ON event_store(session_id);
        CREATE INDEX IF NOT EXISTS idx_es_project ON event_store(project);
        CREATE INDEX IF NOT EXISTS idx_es_timestamp ON event_store(timestamp);
        CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
            event_id, event_type, data_json,
            content='event_store',
            content_rowid='rowid'
        );
        CREATE TRIGGER IF NOT EXISTS event_fts_ai AFTER INSERT ON event_store BEGIN
            INSERT INTO event_fts(rowid, event_id, event_type, data_json)
            VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
        END;
        CREATE TRIGGER IF NOT EXISTS event_fts_ad AFTER DELETE ON event_store BEGIN
            INSERT INTO event_fts(event_fts, rowid) VALUES ('delete', old.rowid);
        END;
        CREATE TRIGGER IF NOT EXISTS event_fts_au AFTER UPDATE ON event_store BEGIN
            INSERT INTO event_fts(event_fts, rowid) VALUES ('delete', old.rowid);
            INSERT INTO event_fts(rowid, event_id, event_type, data_json)
            VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
        END;
        """

    # ══════════════════════════════════════════════════════════
    # Write Operations
    # ══════════════════════════════════════════════════════════

    def store(self, event_type: str, source: str = "",
              data: Optional[Dict[str, Any]] = None,
              correlation_id: str = "", session_id: str = "",
              project: str = "", user_id: str = "",
              metadata: Optional[Dict[str, Any]] = None,
              event_id: Optional[str] = None,
              timestamp: Optional[str] = None) -> str:
        """Сохранить событие в Event Store.

        Args:
            event_type: тип события (e.g. "task.completed")
            source: источник (e.g. "orchestrator")
            data: данные события
            correlation_id: ID цепочки событий
            session_id: ID сессии
            project: проект
            user_id: пользователь
            metadata: метаданные
            event_id: ID события (генерируется если не указан)
            timestamp: ISO timestamp (текущее время если не указан)

        Returns:
            event_id сохранённого события
        """
        eid = event_id or uuid.uuid4().hex[:12]
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        meta = metadata or {}
        correlation = meta.get("correlation_id", correlation_id)
        sess = meta.get("session_id", session_id)
        proj = meta.get("project", project)

        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO event_store
                   (event_id, event_type, source, correlation_id, session_id,
                    project, user_id, data_json, metadata_json, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    eid,
                    event_type,
                    source,
                    correlation,
                    sess,
                    proj,
                    user_id,
                    json.dumps(data or {}, ensure_ascii=False),
                    json.dumps(meta, ensure_ascii=False),
                    ts,
                ),
            )
            conn.commit()
        return eid

    def store_batch(
        self, events: List[Dict[str, Any]]
    ) -> int:
        """Batch-сохранение для производительности.

        Args:
            events: список словарей с ключами как у store()

        Returns:
            количество сохранённых событий
        """
        with self._lock, self._connect() as conn:
            count = 0
            for ev in events:
                eid = ev.get("event_id") or uuid.uuid4().hex[:12]
                ts = ev.get("timestamp") or datetime.now(timezone.utc).isoformat()
                meta = ev.get("metadata", {}) or {}
                data = ev.get("data", {}) or {}
                correlation = meta.get("correlation_id", ev.get("correlation_id", ""))
                sess = meta.get("session_id", ev.get("session_id", ""))
                proj = meta.get("project", ev.get("project", ""))

                conn.execute(
                    """INSERT OR IGNORE INTO event_store
                       (event_id, event_type, source, correlation_id, session_id,
                        project, user_id, data_json, metadata_json, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        eid,
                        ev.get("event_type", ""),
                        ev.get("source", ""),
                        correlation,
                        sess,
                        proj,
                        ev.get("user_id", ""),
                        json.dumps(data, ensure_ascii=False),
                        json.dumps(meta, ensure_ascii=False),
                        ts,
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    count += 1
            conn.commit()
        return count

    # ══════════════════════════════════════════════════════════
    # Read Operations
    # ══════════════════════════════════════════════════════════

    def get_by_id(self, event_id: str) -> Optional[EventEntry]:
        """Получить событие по ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM event_store WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def get_by_correlation_id(
        self, correlation_id: str
    ) -> List[EventEntry]:
        """Получить все события в цепочке (task → step → result)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM event_store WHERE correlation_id = ? ORDER BY timestamp ASC",
                (correlation_id,),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_by_session_id(self, session_id: str) -> List[EventEntry]:
        """Получить все события сессии."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM event_store WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def query(self, query: EventQuery) -> List[EventEntry]:
        """Поиск событий с фильтрацией.

        Поддерживает:
        - Фильтр по event_type (с wildcard: "task.*" → LIKE "task.%")
        - Фильтр по source, correlation_id, session_id, project, user_id
        - Временной диапазон (since, until)
        - Полнотекстовый поиск по data_json (через FTS5)
        - Пагинацию (limit, offset)
        - Сортировку (order: asc/desc)
        """
        # Если есть data_search — используем FTS5
        if query.data_search:
            return self._search_fts(query)

        sql = "SELECT * FROM event_store"
        conditions: List[str] = []
        params: List[Any] = []

        if query.event_type:
            if "*" in query.event_type or "%" in query.event_type:
                like_pattern = self._resolve_wildcard(query.event_type)
                conditions.append("event_type LIKE ?")
                params.append(like_pattern)
            else:
                conditions.append("event_type = ?")
                params.append(query.event_type)

        if query.source:
            conditions.append("source = ?")
            params.append(query.source)

        if query.correlation_id:
            conditions.append("correlation_id = ?")
            params.append(query.correlation_id)

        if query.session_id:
            conditions.append("session_id = ?")
            params.append(query.session_id)

        if query.project:
            conditions.append("project = ?")
            params.append(query.project)

        if query.user_id:
            conditions.append("user_id = ?")
            params.append(query.user_id)

        if query.since:
            conditions.append("timestamp >= ?")
            params.append(query.since)

        if query.until:
            conditions.append("timestamp <= ?")
            params.append(query.until)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        order = "DESC" if query.order.lower() == "desc" else "ASC"
        sql += f" ORDER BY timestamp {order}"

        sql += " LIMIT ? OFFSET ?"
        params.append(query.limit)
        params.append(query.offset)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def _search_fts(self, query: EventQuery) -> List[EventEntry]:
        """Полнотекстовый поиск через FTS5."""
        sql = """
            SELECT es.* FROM event_store es
            JOIN event_fts fts ON es.rowid = fts.rowid
            WHERE event_fts MATCH ?
        """
        params: List[Any] = [query.data_search]

        if query.event_type:
            if "*" in query.event_type:
                like_pattern = self._resolve_wildcard(query.event_type)
                sql += " AND es.event_type LIKE ?"
                params.append(like_pattern)
            else:
                sql += " AND es.event_type = ?"
                params.append(query.event_type)

        if query.source:
            sql += " AND es.source = ?"
            params.append(query.source)

        if query.session_id:
            sql += " AND es.session_id = ?"
            params.append(query.session_id)

        if query.project:
            sql += " AND es.project = ?"
            params.append(query.project)

        if query.since:
            sql += " AND es.timestamp >= ?"
            params.append(query.since)

        if query.until:
            sql += " AND es.timestamp <= ?"
            params.append(query.until)

        order = "DESC" if query.order.lower() == "desc" else "ASC"
        sql += f" ORDER BY es.timestamp {order}"
        sql += " LIMIT ? OFFSET ?"
        params.append(query.limit)
        params.append(query.offset)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._row_to_entry(r) for r in rows]

    # ══════════════════════════════════════════════════════════
    # Aggregation
    # ══════════════════════════════════════════════════════════

    def count_by_type(self, since: str = "") -> Dict[str, int]:
        """Количество событий каждого типа за период."""
        sql = "SELECT event_type, COUNT(*) as cnt FROM event_store"
        params: List[Any] = []

        if since:
            sql += " WHERE timestamp >= ?"
            params.append(since)

        sql += " GROUP BY event_type ORDER BY cnt DESC"

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {row["event_type"]: row["cnt"] for row in rows}

    def get_stats(self) -> Dict[str, Any]:
        """Статистика Event Store."""
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM event_store"
            ).fetchone()[0]

            # Типы
            type_counts = {}
            for row in conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM event_store GROUP BY event_type"
            ).fetchall():
                type_counts[row["event_type"]] = row["cnt"]

            # FTS5 статистика
            fts_count = conn.execute(
                "SELECT COUNT(*) FROM event_fts"
            ).fetchone()[0]

        return {
            "total_events": total,
            "event_types": type_counts,
            "unique_types": len(type_counts),
            "fts_indexed": fts_count,
        }

    # ══════════════════════════════════════════════════════════
    # Migration
    # ══════════════════════════════════════════════════════════

    def migrate_from_event_log(self, old_db_path: Optional[Path] = None) -> int:
        """Перенести данные из старого event_log в event_store.

        Идемпотентна — повторный запуск не создаёт дубликатов.

        Args:
            old_db_path: путь к старой БД с таблицей event_log

        Returns:
            количество перенесённых записей
        """
        old_path = old_db_path or self._db_path
        if not old_path.exists():
            return 0

        try:
            old_conn = sqlite3.connect(str(old_path))
            old_conn.row_factory = sqlite3.Row

            # Проверяем наличие таблицы event_log
            tables = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='event_log'"
            ).fetchall()
            if not tables:
                old_conn.close()
                return 0

            rows = old_conn.execute(
                "SELECT * FROM event_log ORDER BY timestamp ASC"
            ).fetchall()
            old_conn.close()

            migrated = 0
            for row in rows:
                r = dict(row)  # sqlite3.Row → dict (нет .get() на Android/Termux)
                data = {}
                try:
                    data = json.loads(r.get("data_json", "{)") or "{]")
                except (json.JSONDecodeError, TypeError):
                    pass

                eid = r.get("event_id") or uuid.uuid4().hex[:12]

                with self._lock, self._connect() as conn:
                    conn.execute(
                        """INSERT OR IGNORE INTO event_store
                           (event_id, event_type, source, correlation_id,
                            session_id, project, user_id,
                            data_json, metadata_json, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            eid,
                            r.get("event_type", ""),
                            r.get("source", "legacy"),
                            r.get("correlation_id", ""),
                            r.get("session_id", ""),
                            r.get("project", ""),
                            r.get("user_id", ""),
                            json.dumps(data, ensure_ascii=False),
                            "{]",
                            r.get("timestamp", ""),
                        ),
                    )
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        migrated += 1
                    conn.commit()

            return migrated

        except Exception:
            return 0

    # ══════════════════════════════════════════════════════════
    # Administrative
    # ══════════════════════════════════════════════════════════

    def clear(self) -> int:
        """Очищает все данные.

        Returns:
            количество удалённых записей
        """
        with self._lock, self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM event_store").fetchone()[0]
            conn.execute("DELETE FROM event_store")
            # FTS5 очищается триггером DELETE
            conn.commit()
        return count

    # ══════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _resolve_wildcard(pattern: str) -> str:
        """Преобразует wildcard паттерн (task.*) в SQL LIKE.

        Examples:
            "task.*"  → "task.%"
            "*.failed" → "%.failed"
            "task.completed" → "task.completed" (без wildcard — без изменений)
        """
        return pattern.replace(".*", ".%").replace("*", "%")

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> EventEntry:
        """Преобразует строку SQLite в EventEntry."""
        data = {}
        try:
            data = json.loads(row["data_json"] or "{)")
        except (json.JSONDecodeError, TypeError):
            pass

        metadata = {}
        try:
            metadata = json.loads(row["metadata_json"] or "{)")
        except (json.JSONDecodeError, TypeError):
            pass

        return EventEntry(
            event_id=row["event_id"],
            event_type=row["event_type"],
            source=row["source"],
            correlation_id=row["correlation_id"],
            session_id=row["session_id"],
            project=row["project"],
            user_id=row["user_id"],
            data=data,
            metadata=metadata,
            timestamp=row["timestamp"],
        )
