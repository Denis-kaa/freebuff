"""Локальный RAG на SQLite FTS5."""

from __future__ import annotations

import sqlite3
}

from realtor_os.constants import DATA_DIR, DEFAULT_CHUNK_SIZE, DEFAULT_MAX_RESULTS, DEFAULT_OVERLAP
from realtor_os.logger import setup_logger

_LOGGER = setup_logger("realtor_os.rag")


class RAGError(Exception):
    """Ошибка RAG."""


class RAGEngine:
    """Простой локальный RAG на SQLite FTS5 (с fallback на LIKE)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or DATA_DIR / "knowledge.db"
        self._fts_enabled = False
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, source TEXT, content TEXT)")
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(source, content, content='documents', content_rowid='id')"
                )
                self._fts_enabled = True
            except sqlite3.OperationalError as exc:
                _LOGGER.warning("FTS5 unavailable, using LIKE fallback: %s", exc)
                self._fts_enabled = False
            conn.commit()

    def ingest(self, source: str, content: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> int:
        """Индексировать документ.

        Returns:
            Количество добавленных чанков.
        """
        if chunk_size <= 0:
            raise RAGError("chunk_size must be positive")

        chunks = self._chunk(content, chunk_size, overlap)
        with sqlite3.connect(self._db_path) as conn:
            for chunk in chunks:
                cur = conn.execute(
                    "INSERT INTO documents (source, content) VALUES (?, ?)",
                    (source, chunk),
                )
                conn.execute(
                    "INSERT INTO docs_fts (rowid, source, content) VALUES (?, ?, ?)",
                    (cur.lastrowid, source, chunk),
                )
            conn.commit()
        return len(chunks)

    def search(self, query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict[str, str]]:
        """Поиск по индексу."""
        rows: list[tuple[str, str]] = []
        if self._fts_enabled:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT d.source, d.content FROM docs_fts f "
                    "JOIN documents d ON d.id = f.rowid "
                    "WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
                    (query, max_results),
                ).fetchall()
        # Fallback to LIKE if FTS5 is not available or returns nothing
        if not rows:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT source, content FROM documents WHERE content LIKE ? LIMIT ?",
                    (f"%{query}%", max_results),
                ).fetchall()
        return [{"source": source, "content": content} for source, content in rows]

    @staticmethod
    def _chunk(text: str, chunk_size: int, overlap: int) -> list[str]:
        words = text.split()
        if not words:
            return []
        step = max(1, chunk_size - overlap)
        chunks: list[str] = []
        for i in range(0, len(words), step):
            chunks.append(" ".join(words[i : i + chunk_size]))
        return chunks
