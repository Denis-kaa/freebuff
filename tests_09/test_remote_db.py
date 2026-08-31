"""Hermetic tests for RemoteDB — shared database adapter for Cowork mode.

Tests cover:
- Local-only mode (no remote_url)
- SQL interpolation + escaping
- Schema executescript
- execute/fetchall/fetchone
- Remote mock (urllib monkeypatch)
- Fallback on remote failure
- Health endpoint
- Context manager protocol
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core_02.remote_db import RemoteDB, RemoteDBError, _FakeRow


# ── fixtures ─────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def local_db(tmp_db: Path) -> RemoteDB:
    """RemoteDB in local-only mode."""
    return RemoteDB(remote_url=None, local_path=tmp_db)


# ── _FakeRow ─────────────────────────────────────────────────────────

class TestFakeRow:
    def test_getitem_str(self) -> None:
        row = _FakeRow(["id", "name"], [1, "alice"])
        assert row["id"] == 1
        assert row["name"] == "alice"

    def test_getitem_int(self) -> None:
        row = _FakeRow(["id", "name"], [1, "alice"])
        assert row[0] == 1
        assert row[1] == "alice"

    def test_dict_inherited(self) -> None:
        row = _FakeRow(["id"], [42])
        assert dict(row) == {"id": 42}


# ── escape ───────────────────────────────────────────────────────────

class TestEscape:
    def test_none(self) -> None:
        assert RemoteDB._escape(None) == "NULL"

    def test_int(self) -> None:
        assert RemoteDB._escape(42) == "42"

    def test_float(self) -> None:
        assert RemoteDB._escape(3.14) == "3.14"

    def test_bool(self) -> None:
        assert RemoteDB._escape(True) == "1"
        assert RemoteDB._escape(False) == "0"

    def test_string(self) -> None:
        assert RemoteDB._escape("hello") == "'hello'"

    def test_string_with_quotes(self) -> None:
        assert RemoteDB._escape("it's") == "'it''s'"

    def test_interpolate(self) -> None:
        sql = RemoteDB._interpolate("SELECT * FROM t WHERE id = ? AND name = ?", (1, "bob"))
        assert sql == "SELECT * FROM t WHERE id = 1 AND name = 'bob'"

    def test_interpolate_no_params(self) -> None:
        assert RemoteDB._interpolate("SELECT 1", ()) == "SELECT 1"


# ── local-only mode ──────────────────────────────────────────────────

class TestLocalMode:
    def test_creates_db_file(self, tmp_db: Path) -> None:
        RemoteDB(remote_url=None, local_path=tmp_db)
        assert tmp_db.exists()

    def test_executescript(self, local_db: RemoteDB) -> None:
        local_db.executescript(SCHEMA)
        # Table should exist
        rows = local_db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='kv'")
        assert len(rows) == 1

    def test_execute_insert_and_select(self, local_db: RemoteDB) -> None:
        local_db.executescript(SCHEMA)
        local_db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("k1", "v1"))
        rows = local_db.fetchall("SELECT * FROM kv WHERE key = ?", ("k1",))
        assert len(rows) == 1
        assert rows[0]["key"] == "k1"
        assert rows[0]["value"] == "v1"

    def test_fetchone(self, local_db: RemoteDB) -> None:
        local_db.executescript(SCHEMA)
        local_db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("k1", "v1"))
        row = local_db.fetchone("SELECT * FROM kv WHERE key = ?", ("k1",))
        assert row is not None
        assert row["value"] == "v1"

    def test_fetchone_empty(self, local_db: RemoteDB) -> None:
        local_db.executescript(SCHEMA)
        row = local_db.fetchone("SELECT * FROM kv WHERE key = ?", ("missing",))
        assert row is None

    def test_execute_returns_rows_for_select(self, local_db: RemoteDB) -> None:
        local_db.executescript(SCHEMA)
        local_db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("a", "1"))
        local_db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("b", "2"))
        rows = local_db.fetchall("SELECT * FROM kv ORDER BY key")
        assert len(rows) == 2
        assert rows[0]["key"] == "a"
        assert rows[1]["key"] == "b"

    def test_context_manager(self, tmp_db: Path) -> None:
        with RemoteDB(remote_url=None, local_path=tmp_db) as db:
            db.executescript(SCHEMA)
            db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("k", "v"))
        # After close, connection should be None
        assert db._local_conn is None


# ── remote mode (mocked) ─────────────────────────────────────────────

def _mock_urlopen(request: Any, timeout: float = 5.0) -> Any:
    """Mock urllib.request.urlopen for rqlite responses."""
    url = request.full_url if hasattr(request, "full_url") else str(request)
    body = request.data.decode() if hasattr(request, "data") and request.data else None

    class FakeResp:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *a: Any) -> None:
            pass

    if "/status" in url:
        return FakeResp(b"{)")
    if "/db/query" in url:
        # rqlite v10: GET /db/query?q=...
        return FakeResp(json.dumps({
            "results": [{"columns": ["key", "value"], "types": ["text", "text"],
                         "values": [["mock_key", "mock_value"]]}]
        }).encode())
    if "/db/execute" in url and body:
        return FakeResp(json.dumps({"results": [{"last_insert_id": 1, "rows_affected": 1}]}).encode())
    return FakeResp(b"{)")


class TestRemoteMode:
    def test_remote_execute_select(self, tmp_db: Path) -> None:
        db = RemoteDB(remote_url="http://fake-rqlite:4001", local_path=tmp_db, timeout=1.0)
        with patch("core_02.remote_db.urllib.request.urlopen", side_effect=_mock_urlopen):
            rows = db.fetchall("SELECT * FROM kv")
            assert len(rows) == 1
            assert rows[0]["key"] == "mock_key"

    def test_remote_execute_insert(self, tmp_db: Path) -> None:
        db = RemoteDB(remote_url="http://fake-rqlite:4001", local_path=tmp_db, timeout=1.0)
        with patch("core_02.remote_db.urllib.request.urlopen", side_effect=_mock_urlopen):
            result = db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("k1", "v1"))
            # INSERT returns empty rows
            assert result == []

    def test_remote_is_remote(self, tmp_db: Path) -> None:
        db = RemoteDB(remote_url="http://fake-rqlite:4001", local_path=tmp_db, timeout=1.0)
        with patch("core_02.remote_db.urllib.request.urlopen", side_effect=_mock_urlopen):
            db.fetchall("SELECT 1")
            assert db.is_remote is True
            assert db.is_local is False


# ── fallback on remote failure ───────────────────────────────────────

class TestFallback:
    def test_fallback_on_connection_error(self, tmp_db: Path) -> None:
        db = RemoteDB(remote_url="http://unreachable:4001", local_path=tmp_db, timeout=0.1)
        with patch("core_02.remote_db.urllib.request.urlopen", side_effect=urllib.error.URLError("fail")):
            # Should fall back to local
            db.executescript(SCHEMA)
            db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", ("k1", "v1"))
            rows = db.fetchall("SELECT * FROM kv")
            assert len(rows) == 1
            assert db.is_local is True

    def test_health_local_only(self, local_db: RemoteDB) -> None:
        info = local_db.health()
        assert info["mode"] == "local"
        assert info["remote_url"] is None

    def test_health_remote(self, tmp_db: Path) -> None:
        db = RemoteDB(remote_url="http://fake-rqlite:4001", local_path=tmp_db, timeout=1.0)
        with patch("core_02.remote_db.urllib.request.urlopen", side_effect=_mock_urlopen):
            info = db.health()
            assert info["remote_ready"] is True


# ── integration: RemoteDB replacing MemoryStore locally ───────────────

class TestMemoryStoreCompat:
    """Verify RemoteDB in local mode works as drop-in for MemoryStore."""

    def test_schema_and_crud(self, tmp_db: Path) -> None:
        with RemoteDB(remote_url=None, local_path=tmp_db) as db:
            db.executescript(SCHEMA)
            # Insert multiple
            for i in range(5):
                db.execute("INSERT INTO kv(key, value) VALUES (?, ?)", (f"k{i}", f"v{i}"))
            # Select all
            rows = db.fetchall("SELECT * FROM kv ORDER BY key")
            assert len(rows) == 5
            assert rows[0]["key"] == "k0"
            assert rows[4]["key"] == "k4"
            # Update
            db.execute("UPDATE kv SET value = ? WHERE key = ?", ("updated", "k2"))
            row = db.fetchone("SELECT * FROM kv WHERE key = ?", ("k2",))
            assert row is not None
            assert row["value"] == "updated"
            # Delete
            db.execute("DELETE FROM kv WHERE key = ?", ("k2",))
            rows = db.fetchall("SELECT * FROM kv")
            assert len(rows) == 4
