"""db/database.py — sync-обёртка над sqlite3 для маркетплейса.

Использование:
    db = Database("data/market.sqlite")
    await db.init()                # отложенная инициализация в worker thread
    async with db.transaction() as tx:
        ...
    rows = await db.query("SELECT ...")

В aiogram-хэндлерах все вызовы оборачиваются в `asyncio.to_thread(...)` —
для упрощения зависимостей (aiosqlite добавлять не нужно): ядро чисто
stdlib + sync, и в sandbox это работает стабильно.

WAL включён для конкурентных readов, foreign_keys — для целостности.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
}
from typing import Iterable, Iterator, Optional, Sequence

logger = logging.getLogger(__name__)


class _TxCtx:
    """Контекст-менеджер транзакции с захватом RLock на всё тело + явный BEGIN.

    Поведение:
      * `__enter__` — захватывает RLock и выполняет `BEGIN IMMEDIATE`,
        который открывает именованную транзакцию SQLite (RESERVED lock).
        Это превращает «набор autocommit-statement'ов» в одну настоящую
        транзакцию — `commit()`/`rollback()` в __exit__ реально откатывают
        работу, выполненную между __enter__ и __exit__.
      * `__exit__` — при исключении rollback, при нормальном выходе commit.
        RLock отпускается в любом случае.
      RLock — re-entrant, чтобы `self._db.execute(...)`, вызванный внутри
      транзакции, не создавал deadlock.
      Фикс ревью №1 (autocommit fix): без `BEGIN IMMEDIATE` наш коннект
      работал в autocommit и `commit()` в __exit__ был no-op — теперь это
      реальная транзакция.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock) -> None:
        self._conn = conn
        self._lock = lock

    def __enter__(self) -> sqlite3.Connection:
        self._lock.acquire()
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except Exception:
            self._lock.release()
            raise
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self._conn.execute("COMMIT")
            else:
                self._conn.execute("ROLLBACK")
        except Exception:
            logger.warning("commit/rollback внутри _TxCtx провалилось: %r", exc, exc_info=True)
        finally:
            self._lock.release()


class Database:
    """Тонкая обёртка над sqlite3. Потокобезопасная через RLock."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        # RLock — re-entrant. Нужно, чтобы transaction() мог удерживать
        # лок на всё тело блока `with self._db.transaction() as conn:`
        # при этом внутри можно было бы вызывать db.execute (для других
        # операций) без deadlock. Также устраняет SQLite InterfaceError
        # при конкурентном использовании одного коннекшна из разных потоков.
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._schema_sql: Optional[str] = None

    # ── lifecycle ───────────────────────────────────────────────────────────

    def init(self) -> None:
        """Создать файл БД, применить миграции, настроить режимы."""
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = self._connect()
            if self._schema_sql:
                conn.executescript(self._schema_sql)
            conn.commit()
            self._conn = conn

    def set_schema(self, schema_sql: str) -> None:
        """Сохранить SQL-схему для применения при `init()`."""
        self._schema_sql = schema_sql

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # ── primitive ops ───────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = self._connect()
                    if self._schema_sql:
                        self._conn.executescript(self._schema_sql)
                        self._conn.commit()
        return self._conn

    def transaction(self) -> _TxCtx:
        """Контекстный менеджер транзакции. Держит RLock всё тело блока.

        Гарантирует сериализацию всех SQL-операций внутри транзакции и
        окружающего DB-кода. Использовать из `to_thread` в aiogram-хэндлерах.
        """
        return _TxCtx(self._get_conn(), self._lock)

    def execute(self, sql: str, params: Sequence | None = None) -> None:
        with self._lock:
            self._get_conn().execute(sql, params or [])

    def executemany(self, sql: str, seq: Iterable[Sequence]) -> None:
        with self._lock:
            self._get_conn().executemany(sql, seq)

    def query(self, sql: str, params: Sequence | None = None) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._get_conn().execute(sql, params or [])
            return cur.fetchall()

    def query_one(self, sql: str, params: Sequence | None = None) -> Optional[sqlite3.Row]:
        with self._lock:
            cur = self._get_conn().execute(sql, params or [])
            return cur.fetchone()

    def scalar(self, sql: str, params: Sequence | None = None):
        row = self.query_one(sql, params)
        return None if row is None else row[0]

    @property
    def raw_conn(self) -> sqlite3.Connection:
        """Прямой доступ к коннекшну (для сложных транзакций). Использовать осторожно."""
        return self._get_conn()
