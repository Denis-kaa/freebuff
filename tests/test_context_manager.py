"""Tests for scripts/context_manager schema migrations.

Covers:
- fresh DB creation produces the full v5 schema with correct columns and indexes
- v3 -> v5 upgrade path creates v4/v5 tables and preserves existing data
- v4 -> v5 upgrade path creates v5 tables
- migrations are idempotent when run multiple times
- downgrades (DB version above supported SCHEMA_VERSION) are rejected
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from scripts.context_manager import ContextManager


class TestContextManagerMigrations:
    @staticmethod
    def _setup_db_at_version(db_path: str, version: int) -> None:
        """Create a database at the requested schema version.

        We start from the current v5 schema, drop the tables that do not
        exist at the target version, and set ``PRAGMA user_version``
        accordingly. This is safe because the core tables
        (sessions, messages, checkpoints, projects) have been unchanged
        since v3, so dropping only the newer tables faithfully simulates the
        requested historical state.
        """
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            ContextManager._create_schema_v5(conn)
            conn.commit()
            if version < 5:
                conn.executescript("DROP TABLE IF EXISTS action_verifications;")
            if version < 4:
                conn.executescript(
                    """
                    DROP TABLE IF EXISTS arch_decisions;
                    DROP TABLE IF EXISTS invariants;
                    """
                )
            conn.execute(f"PRAGMA user_version = {version***REMOVED***")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> set[str***REMOVED***:
        return {row[1***REMOVED*** for row in conn.execute(f"PRAGMA table_info({table***REMOVED***)")***REMOVED***

    @staticmethod
    def _table_indexes(conn: sqlite3.Connection, table: str) -> set[str***REMOVED***:
        return {row[1***REMOVED*** for row in conn.execute(f"PRAGMA index_list({table***REMOVED***)")***REMOVED***

    def test_fresh_db_has_full_v5_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cm = ContextManager(workspace_root=tmp)
            db_path = os.path.join(tmp, "data", "context.db")
            conn = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0***REMOVED***
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                ***REMOVED***
                version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***

                assert version == 5
                assert {
                    "sessions",
                    "messages",
                    "checkpoints",
                    "projects",
                    "arch_decisions",
                    "invariants",
                    "action_verifications",
                ***REMOVED*** <= tables

                # Verify shape of migrated/new tables
                assert "title" in self._table_columns(conn, "arch_decisions")
                assert "name" in self._table_columns(conn, "invariants")
                assert "claimed_status" in self._table_columns(conn, "action_verifications")

                # Verify at least one index per new table exists
                assert "idx_arch_decisions_session" in self._table_indexes(conn, "arch_decisions")
                assert "idx_invariants_enabled" in self._table_indexes(conn, "invariants")
                assert "idx_action_verifications_session" in self._table_indexes(conn, "action_verifications")
            finally:
                conn.close()

    def test_v3_to_v5_migration_creates_v4_and_v5_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "data", "context.db")
            self._setup_db_at_version(db_path, 3)

            # Seed some data that must survive the migration
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, status, created_at, updated_at)
                    VALUES ('s1', 'active', '2026-01-01', '2026-01-01')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            cm = ContextManager(workspace_root=tmp)

            conn = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0***REMOVED***
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                ***REMOVED***
                version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***
                session = conn.execute(
                    "SELECT session_id FROM sessions WHERE session_id = ?", ("s1",)
                ).fetchone()

                assert version == 5
                assert "arch_decisions" in tables
                assert "invariants" in tables
                assert "action_verifications" in tables
                assert session is not None
                assert session[0***REMOVED*** == "s1"

                # Indexes were created too
                assert "idx_arch_decisions_session" in self._table_indexes(conn, "arch_decisions")
                assert "idx_invariants_enabled" in self._table_indexes(conn, "invariants")
                assert "idx_action_verifications_session" in self._table_indexes(conn, "action_verifications")
            finally:
                conn.close()

    def test_v4_to_v5_migration_creates_v5_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "data", "context.db")
            self._setup_db_at_version(db_path, 4)

            cm = ContextManager(workspace_root=tmp)

            conn = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0***REMOVED***
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                ***REMOVED***
                version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***

                assert version == 5
                assert "action_verifications" in tables
                assert "claimed_status" in self._table_columns(conn, "action_verifications")
                assert "idx_action_verifications_session" in self._table_indexes(conn, "action_verifications")
            finally:
                conn.close()

    def test_init_db_migrations_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "data", "context.db")
            self._setup_db_at_version(db_path, 3)

            # First migration pass
            cm1 = ContextManager(workspace_root=tmp)

            # Simulate re-running migrations by resetting the version and
            # instantiating ContextManager again. IF NOT EXISTS should keep
            # everything intact and not raise errors.
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("PRAGMA user_version = 3")
                conn.commit()
            finally:
                conn.close()

            cm2 = ContextManager(workspace_root=tmp)

            conn = sqlite3.connect(db_path)
            try:
                version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***
                tables = {
                    row[0***REMOVED***
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                ***REMOVED***
            finally:
                conn.close()

            assert version == 5
            assert "action_verifications" in tables
            assert "arch_decisions" in tables
            assert "invariants" in tables

    def test_migration_steps_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "data", "context.db")
            self._setup_db_at_version(db_path, 3)

            conn = sqlite3.connect(db_path)
            try:
                # Calling the same migration step repeatedly should not fail
                ContextManager._migrate_v3_to_v4(conn)
                ContextManager._migrate_v3_to_v4(conn)
                ContextManager._migrate_v4_to_v5(conn)
                ContextManager._migrate_v4_to_v5(conn)

                version = conn.execute("PRAGMA user_version").fetchone()[0***REMOVED***
            finally:
                conn.close()

            assert version == 5

    def test_downgrade_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "data", "context.db")
            self._setup_db_at_version(db_path, 5)

            conn = sqlite3.connect(db_path)
            try:
                conn.execute("PRAGMA user_version = 99")
                conn.commit()
            finally:
                conn.close()

            with pytest.raises(RuntimeError, match="Schema version 99 > 5"):
                ContextManager(workspace_root=tmp)
