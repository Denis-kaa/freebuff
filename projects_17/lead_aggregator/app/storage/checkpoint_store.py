"""checkpoint_store.py — state persistence (требование промта 69 п.3).

Сохраняет `last_processed_id`/timestamp по каждому источнику, чтобы после
рестарта парсер продолжал с места остановки. SQLite + WAL (паттерн
`core_02/workspace_registry.py`). Контракт расширяем на PG/Redis (W-3).
"""
from __future__ import annotations

import sqlite3
import time
***REMOVED***


class CheckpointStore:
    """Атомарные checkpoint'ы по источнику (source → last_id).

    API: get_last(source), set_last(source, last_id), close().
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                source      TEXT PRIMARY KEY,
                last_id     TEXT NOT NULL,
                updated_at  REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get_last(self, source: str) -> str | None:
        row = self._conn.execute(
            "SELECT last_id FROM checkpoints WHERE source = ?", (source,)
        ).fetchone()
        return row["last_id"***REMOVED*** if row else None

    def set_last(self, source: str, last_id: str) -> None:
        self._conn.execute(
            """
            INSERT INTO checkpoints (source, last_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET last_id = excluded.last_id,
                                              updated_at = excluded.updated_at
            """,
            (source, last_id, time.time()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "CheckpointStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
