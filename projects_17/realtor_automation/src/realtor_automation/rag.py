"""Local RAG (retrieval-augmented generation) using SQLite."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
}
from typing import Any


class RAGError(RuntimeError):
    """Raised when RAG operations fail."""

    pass


class KnowledgeBase:
    """SQLite-backed knowledge base with FTS5 search."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._has_fts5 = self._check_fts5()
        self._init_db()

    @staticmethod
    def _check_fts5() -> bool:
        """Check whether SQLite supports FTS5."""
        try:
            with sqlite3.connect(":memory:") as conn:
                conn.execute("CREATE VIRTUAL TABLE test USING fts5(content)")
            return True
        except sqlite3.Error:
            return False

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            if self._has_fts5:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        tag TEXT DEFAULT '',
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                try:
                    conn.execute(
                        "CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(source, tag, content)"
                    )
                except sqlite3.Error:
                    self._has_fts5 = False
            else:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        tag TEXT DEFAULT '',
                        content TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
            conn.commit()

    def ingest(self, source: str, content: str, tag: str = "") -> int:
        """Add a document to the knowledge base.

        Args:
            source: Document identifier or path.
            content: Document text.
            tag: Optional category tag.

        Returns:
            Number of rows inserted (0 or 1).
        """
        if not source or not content:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO documents (source, tag, content, created_at) VALUES (?, ?, ?, ?)",
                (source, tag, content, now),
            )
            if self._has_fts5:
                conn.execute(
                    "INSERT INTO fts_documents (source, tag, content) VALUES (?, ?, ?)",
                    (source, tag, content),
                )
            conn.commit()
            return int(cur.rowcount)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search documents for the given query.

        Falls back to a simple LIKE search if FTS5 is unavailable.
        """
        if self._has_fts5:
            return self._search_fts(query, limit)
        return self._search_like(query, limit)

    def _search_fts(self, query: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT d.id, d.source, d.tag, d.content, d.created_at
                FROM documents d
                JOIN fts_documents f ON d.source = f.source
                WHERE fts_documents MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def _search_like(self, query: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [dict(row) for row in rows]
