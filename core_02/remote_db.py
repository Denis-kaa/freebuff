"""RemoteDB — shared database adapter for Cowork mode.

Provides a sqlite3-compatible interface over rqlite HTTP API, enabling
multiple Buffy instances (Termux + VPS) to share one database.

Local SQLite fallback: if rqlite is unreachable, falls back to local file.

Usage::

    from core_02.remote_db import RemoteDB

    db = RemoteDB(
        remote_url="http://185.233.184.192:4001",
        local_path="data_13/context.db",
    )
    db.executescript(MemoryStore.SCHEMA)
    db.execute("INSERT INTO knowledge_objects(id, kind, title, ...) VALUES (?, ?, ?)", params)
    rows = db.fetchall("SELECT * FROM knowledge_objects WHERE kind = ?", ("lesson",))
    db.close()
"""

from __future__ import annotations

import json
import logging
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)


class RemoteDBError(Exception):
    """Domain error for RemoteDB operations."""


class _FakeRow(dict):
    """Dict that supports ``row["col"]`` and ``row[col_idx]`` like sqlite3.Row."""

    def __init__(self, columns: list[str], values: list[Any]) -> None:
        super().__init__(zip(columns, values))
        self._columns = columns
        self._values = values

    def __getitem__(self, key: int | str) -> Any:  # type: ignore[override]
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class RemoteDB:
    """Sqlite3-compatible interface over rqlite HTTP API with local fallback.

    Parameters
    ----------
    remote_url : str | None
        Base URL of rqlite (e.g. ``http://185.233.184.192:4001``).
        If *None*, local-only mode.
    local_path : str | Path
        Path to local SQLite file (fallback when remote is unreachable).
    timeout : float
        HTTP timeout in seconds.
    """

    def __init__(
        self,
        remote_url: str | None = None,
        local_path: str | Path = "data_13/context.db",
        timeout: float = 5.0,
    ) -> None:
        self.remote_url = remote_url.rstrip("/") if remote_url else None
        self.local_path = Path(local_path)
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._local_conn: sqlite3.Connection | None = None
        self._remote_ok: bool | None = None  # None = not tested yet

        # If no remote, start local immediately
        if not self.remote_url:
            self._ensure_local()

    # ── public interface (sqlite3-compatible) ─────────────────────────

    def executescript(self, script: str) -> None:
        """Execute multiple SQL statements (schema setup)."""
        if self._try_remote():
            # rqlite handles multiple statements via array
            stmts = [s.strip() for s in script.split(";") if s.strip()]
            self._remote_execute_batch(stmts)
        else:
            self._ensure_local()
            assert self._local_conn is not None
            self._local_conn.executescript(script)
            self._local_conn.commit()

    def execute(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[_FakeRow]:
        """Execute a SQL statement with parameters. Returns rows for SELECT."""
        if self._try_remote():
            return self._remote_execute(sql, params)
        else:
            self._ensure_local()
            assert self._local_conn is not None
            cur = self._local_conn.execute(sql, params)
            self._local_conn.commit()
            return [
                _FakeRow(
                    [d[0] for d in cur.description] if cur.description else [],
                    list(row),
                )
                for row in cur.fetchall()
            ]

    def fetchall(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[_FakeRow]:
        """Execute a SELECT and return all rows."""
        return self.execute(sql, params)

    def fetchone(
        self, sql: str, params: Sequence[Any] = ()
    ) -> _FakeRow | None:
        """Execute a SELECT and return one row or None."""
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None

    def commit(self) -> None:
        """Commit (no-op for rqlite, explicit for local)."""
        if self._local_conn:
            self._local_conn.commit()

    def close(self) -> None:
        """Close connections."""
        if self._local_conn:
            self._local_conn.close()
            self._local_conn = None

    def __enter__(self) -> "RemoteDB":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def is_remote(self) -> bool:
        """True if currently using remote rqlite."""
        return self._remote_ok is True

    @property
    def is_local(self) -> bool:
        """True if currently using local SQLite fallback."""
        return self._remote_ok is False or self.remote_url is None

    def health(self) -> dict[str, Any]:
        """Return health info about the connection."""
        info: dict[str, Any] = {
            "remote_url": self.remote_url,
            "local_path": str(self.local_path),
            "mode": "remote" if self.is_remote else "local",
        }
        if self.remote_url:
            try:
                req = urllib.request.Request(f"{self.remote_url}/status?pretty=false")
                urllib.request.urlopen(req, timeout=self.timeout)
                info["remote_ready"] = True
            except Exception:
                info["remote_ready"] = False
        return info

    # ── private: remote rqlite ───────────────────────────────────────

    def _try_remote(self) -> bool:
        """Try remote. Returns True if available, False for fallback."""
        if self.remote_url is None:
            return False
        # If we already know remote is down, don't retry every call
        if self._remote_ok is False:
            return False
        # Lazy test
        if self._remote_ok is None:
            try:
                req = urllib.request.Request(f"{self.remote_url}/status?pretty=false")
                urllib.request.urlopen(req, timeout=self.timeout)
                self._remote_ok = True
                logger.info("RemoteDB: connected to rqlite at %s", self.remote_url)
            except Exception as exc:
                self._remote_ok = False
                logger.warning("RemoteDB: rqlite unreachable (%s), falling back to local", exc)
        return self._remote_ok

    def _remote_execute(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[_FakeRow]:
        """Send SQL to rqlite via GET /db/query or POST /db/execute."""
        import urllib.parse

        is_select = sql.lstrip().upper().startswith("SELECT")
        full_sql = self._interpolate(sql, params)

        if is_select:
            # rqlite v10: GET /db/query?q=SELECT...
            qs = urllib.parse.urlencode({"q": full_sql})
            url = f"{self.remote_url}/db/query?{qs}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            result = json.loads(resp.read())
            res = result.get("results", [{}])
            if not res:
                return []
            columns = res[0].get("columns", [])
            values_list = res[0].get("values", [])
            return [_FakeRow(columns, list(v)) for v in values_list]
        else:
            # rqlite v10: POST /db/execute with JSON array
            data = json.dumps([full_sql]).encode()
            req = urllib.request.Request(
                f"{self.remote_url}/db/execute",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=self.timeout)
            return []

    def _remote_execute_batch(self, stmts: list[str]) -> None:
        """Send multiple statements as a batch."""
        data = json.dumps(stmts).encode()
        req = urllib.request.Request(
            f"{self.remote_url}/db/execute",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=self.timeout)

    @staticmethod
    def _interpolate(sql: str, params: Sequence[Any]) -> str:
        """Replace ``?`` placeholders with properly escaped values.

        This is needed because rqlite's array-of-strings format doesn't
        support positional parameters.
        """
        if not params:
            return sql

        parts: list[str] = []
        param_idx = 0
        i = 0
        while i < len(sql):
            if sql[i] == "?" and param_idx < len(params):
                parts.append(RemoteDB._escape(params[param_idx]))
                param_idx += 1
                i += 1
            else:
                parts.append(sql[i])
                i += 1
        return "".join(parts)

    @staticmethod
    def _escape(value: Any) -> str:
        """Escape a Python value for safe SQL interpolation."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        # String: single-quote escape
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    # ── private: local fallback ──────────────────────────────────────

    def _ensure_local(self) -> None:
        if self._local_conn is None:
            self._local_conn = sqlite3.connect(str(self.local_path))
            self._local_conn.row_factory = sqlite3.Row
            self._local_conn.execute("PRAGMA foreign_keys = ON")
            try:
                self._local_conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.Error:
                pass
            self._remote_ok = False
            logger.info("RemoteDB: using local SQLite at %s", self.local_path)
