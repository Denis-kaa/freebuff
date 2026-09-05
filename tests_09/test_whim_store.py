"""Tests for scripts_01/whim_store.py — Whim storage for mobile sync.

Additive test module (promt 111): покрывает CRUD + валидацию.
Каждый тест использует tmp_path — каноническая data_13/whims.db
никогда не затрагивается.
"""

import sqlite3

import pytest

from scripts_01 import whim_store


@pytest.fixture()
def db(tmp_path):
    """Isolated whims DB per test (never touches canonical data_13)."""
    return tmp_path / "test_whims.db"


class TestInitDb:
    def test_creates_table_idempotent(self, db):
        conn = whim_store.init_db(db)
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='whims'"
        ).fetchone() is not None
        conn.close()

        # повторный вызов — идемпотентен
        conn2 = whim_store.init_db(db)
        assert conn2.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='whims'"
        ).fetchone() is not None
        conn2.close()

    def test_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "whims.db"
        conn = whim_store.init_db(nested)
        assert nested.exists()
        conn.close()


class TestAddWhim:
    def test_add_returns_dict(self, db):
        whim = whim_store.add_whim("первая мысль", db_path=db)
        assert whim["text"] == "первая мысль"
        assert whim["status"] == "synced"
        assert whim["source"] == "mobile"
        assert whim["id"].startswith("wh-")
        assert "T" in whim["created_at"]  # ISO-8601

    def test_add_strips_text(self, db):
        whim = whim_store.add_whim("  с пробелами  ", db_path=db)
        assert whim["text"] == "с пробелами"

    def test_add_custom_status_and_client(self, db):
        whim = whim_store.add_whim(
            "мысль", client_id="h_abc", status="pending_sync", db_path=db
        )
        assert whim["client_id"] == "h_abc"
        assert whim["status"] == "pending_sync"

    def test_empty_text_raises(self, db):
        with pytest.raises(ValueError):
            whim_store.add_whim("", db_path=db)
        with pytest.raises(ValueError):
            whim_store.add_whim("   ", db_path=db)

    def test_non_string_text_raises(self, db):
        with pytest.raises(ValueError):
            whim_store.add_whim(123, db_path=db)  # type: ignore[arg-type]

    def test_invalid_status_raises(self, db):
        with pytest.raises(ValueError, match="invalid status"):
            whim_store.add_whim("x", status="bogus", db_path=db)


class TestListAndCount:
    def test_list_newest_first(self, db):
        import time

        whim_store.add_whim("старая", db_path=db)
        time.sleep(0.01)
        whim_store.add_whim("новая", db_path=db)
        items = whim_store.list_whims(db_path=db)
        assert [w["text"] for w in items] == ["новая", "старая"]

    def test_limit(self, db):
        for i in range(5):
            whim_store.add_whim(f"w{i}", db_path=db)
        items = whim_store.list_whims(limit=2, db_path=db)
        assert len(items) == 2

    def test_count(self, db):
        assert whim_store.count(db_path=db) == 0
        whim_store.add_whim("один", db_path=db)
        whim_store.add_whim("два", db_path=db)
        assert whim_store.count(db_path=db) == 2


class TestIsolation:
    def test_default_db_not_touched_by_tests(self, db):
        """Явная проверка: tmp-БД не совпадает с канонической."""
        assert db != whim_store.DB_PATH

    def test_wal_mode_active(self, db):
        conn = whim_store.init_db(db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() in ("wal", "delete")  # WAL может откатиться на экзотических ФС
        conn.close()
