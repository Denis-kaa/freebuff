"""EventStore — SQLite-хранилище событий с FTS5-поиском (спека §3–5)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins_04.event.types import EventEntry, EventQuery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id       TEXT PRIMARY KEY,
    event_type     TEXT NOT NULL,
    source         TEXT DEFAULT '',
    data_json      TEXT DEFAULT '{}',
    correlation_id TEXT DEFAULT '',
    session_id     TEXT DEFAULT '',
    project        TEXT DEFAULT '',
    user           TEXT DEFAULT '',
    timestamp      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _like_pattern(value: str) -> str:
    """Экранирование LIKE-спецсимволов + wildcard * → %."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return escaped.replace("*", "%")


class EventStore:
    """Персистентное хранилище событий: CRUD + query + FTS + агрегация."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else Path("data_13") / "events.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = True
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._init_fts()
        self._conn.commit()

    # ── инициализация ───────────────────────────────────────

    def _init_fts(self) -> None:
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS events_fts "
                "USING fts5(event_id UNINDEXED, data_json)"
            )
            self._conn.execute(
                "CREATE TRIGGER IF NOT EXISTS events_fts_insert "
                "AFTER INSERT ON events BEGIN "
                " INSERT INTO events_fts(event_id, data_json) "
                " VALUES (new.event_id, new.data_json); END"
            )
            self._conn.execute(
                "CREATE TRIGGER IF NOT EXISTS events_fts_delete "
                "AFTER DELETE ON events BEGIN "
                " DELETE FROM events_fts WHERE event_id = old.event_id; END"
            )
        except sqlite3.OperationalError:  # сборка SQLite без FTS5
            self._fts_enabled = False

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    # ── CRUD ────────────────────────────────────────────────

    def store(
        self,
        event_type: str,
        source: str = "",
        data: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        correlation_id: str = "",
        session_id: str = "",
        project: str = "",
        user: str = "",
        timestamp: str = "",
    ) -> str:
        eid = event_id or uuid.uuid4().hex[:12]
        self._conn.execute(
            "INSERT OR IGNORE INTO events "
            "(event_id, event_type, source, data_json, correlation_id, session_id,"
            " project, user, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                eid, event_type, source,
                json.dumps(data or {}, ensure_ascii=False),
                correlation_id, session_id, project, user,
                timestamp or _utc_now_iso(),
            ),
        )
        self._conn.commit()
        return eid

    def store_batch(self, events: List[Dict[str, Any]]) -> int:
        if not events:
            return 0
        count = 0
        for ev in events:
            self.store(**ev)
            count += 1
        return count

    def get_by_id(self, event_id: str) -> Optional[EventEntry]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    # ── query ───────────────────────────────────────────────

    def query(self, q: EventQuery) -> List[EventEntry]:
        where: List[str] = []
        params: List[Any] = []

        if q.event_type:
            if "*" in q.event_type:
                where.append("event_type LIKE ? ESCAPE '\\'")
                params.append(_like_pattern(q.event_type))
            else:
                where.append("event_type = ?")
                params.append(q.event_type)
        for column, value in (
            ("source", q.source),
            ("session_id", q.session_id),
            ("correlation_id", q.correlation_id),
            ("project", q.project),
            ("user", q.user),
        ):
            if value:
                where.append(f"{column} = ?")
                params.append(value)
        if q.since:
            where.append("timestamp >= ?")
            params.append(q.since)
        if q.until:
            where.append("timestamp <= ?")
            params.append(q.until)

        joins = ""
        if q.data_search:
            if self._fts_enabled:
                joins = (
                    " JOIN events_fts ON events.event_id = events_fts.event_id "
                    "AND events_fts.data_json MATCH ?"
                )
                params.insert(0, f'"{q.data_search}"' if " " in q.data_search else q.data_search)
            else:
                where.append("data_json LIKE ? ESCAPE '\\'")
                params.append(f"%{_like_pattern(q.data_search)}%")

        sql = "SELECT * FROM events" + joins
        if where:
            sql += " WHERE " + " AND ".join(where)
        direction = "ASC" if (q.order or "").lower() == "asc" else "DESC"
        sql += f" ORDER BY events.timestamp {direction}, events.rowid {direction}"
        sql += " LIMIT ? OFFSET ?"
        params.extend([max(0, q.limit), max(0, q.offset)])

        rows = self._conn.execute(sql, params).fetchall()
        return [e for e in (self._row_to_entry(r) for r in rows) if e]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> Optional[EventEntry]:
        try:
            data = json.loads(row["data_json"] or "{}")
        except Exception:  # noqa: BLE001
            data = {}
        return EventEntry(
            event_id=row["event_id"],
            event_type=row["event_type"],
            source=row["source"] or "",
            data=data if isinstance(data, dict) else {},
            correlation_id=row["correlation_id"] or "",
            session_id=row["session_id"] or "",
            project=row["project"] or "",
            user=row["user"] or "",
            timestamp=row["timestamp"] or "",
        )

    # ── агрегация / статистика ──────────────────────────────

    def count_by_type(self, since: str = "") -> Dict[str, int]:
        sql = "SELECT event_type, COUNT(*) AS n FROM events"
        params: List[Any] = []
        if since:
            sql += " WHERE timestamp >= ?"
            params.append(since)
        sql += " GROUP BY event_type"
        rows = self._conn.execute(sql, params).fetchall()
        return {r["event_type"]: r["n"] for r in rows}

    def get_stats(self) -> Dict[str, int]:
        total = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        unique = self._conn.execute(
            "SELECT COUNT(DISTINCT event_type) FROM events"
        ).fetchone()[0]
        if self._fts_enabled:
            try:
                indexed = self._conn.execute(
                    "SELECT COUNT(*) FROM events_fts"
                ).fetchone()[0]
            except sqlite3.OperationalError:
                indexed = 0
        else:
            indexed = 0
        return {
            "total_events": total,
            "unique_types": unique,
            "fts_indexed": indexed,
            "fts_enabled": int(self._fts_enabled),
        }

    def clear(self) -> int:
        cursor = self._conn.execute("DELETE FROM events")
        if self._fts_enabled:
            self._conn.execute("DELETE FROM events_fts")
        self._conn.commit()
        return cursor.rowcount

    # ── миграция из легаси event_log ────────────────────────

    def migrate_from_event_log(self, old_db_path: Path) -> int:
        path = Path(old_db_path)
        if not path.exists():
            return 0
        migrated = 0
        try:
            old_conn = sqlite3.connect(str(path))
            old_conn.row_factory = sqlite3.Row
            rows = old_conn.execute(
                "SELECT event_id, event_type, source, data_json, timestamp "
                "FROM event_log"
            ).fetchall()
        except sqlite3.Error:
            return 0
        finally:
            try:
                old_conn.close()  # type: ignore[possibly-undefined]
            except Exception:  # noqa: BLE001
                pass
        for r in rows:
            before = self.get_stats()["total_events"]
            self.store(
                event_type=r["event_type"],
                source=r["source"] or "",
                event_id=r["event_id"],
                timestamp=r["timestamp"] or _utc_now_iso(),
                **({"data": json.loads(r["data_json"])} if r["data_json"] else {}),
            )
            if self.get_stats()["total_events"] > before:
                migrated += 1
        return migrated
