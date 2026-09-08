"""SQLite-слой printcalc_web: схема, соединения, путь БД.

Phase 1 (v3): Order/OrderItem/PriceListItem/Settings. Инициализация
идемпотентна (CREATE IF NOT EXISTS — CODE_QUALITY 3.7); путь БД
параметризован env PRINTCALC_WEB_DB (CODE_QUALITY 4.7). Статус заказа
хранится как TEXT (расширяемость Р2/CONFLICT-1); набор значений
валидруется в store (закрытый словарь в духе ANTI-6b).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_list_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    price       REAL NOT NULL,
    unit        TEXT,
    category    TEXT,
    synonyms    TEXT NOT NULL DEFAULT '[]',
    usage_count INTEGER NOT NULL DEFAULT 0,
    unverified  INTEGER NOT NULL DEFAULT 1,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    status         TEXT NOT NULL DEFAULT 'новый',
    payment_method TEXT NOT NULL,
    total          REAL NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id           INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    kind               TEXT NOT NULL CHECK (kind IN ('price_list', 'calculator', 'manual')),
    name               TEXT NOT NULL,
    price              REAL NOT NULL,
    qty                REAL NOT NULL DEFAULT 1,
    calculator_id      TEXT,
    params_json        TEXT,
    price_list_item_id INTEGER REFERENCES price_list_items(id),
    saved_to_catalog   INTEGER NOT NULL DEFAULT 1,
    position           INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_price_items_name ON price_list_items(name);
"""


def default_db_path() -> Path:
    """Возвращает путь БД: env PRINTCALC_WEB_DB или <корень printcalc>/data/printcalc.db."""
    env_path = os.environ.get("PRINTCALC_WEB_DB")
    if env_path:
        return Path(env_path)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / "printcalc.db"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Открывает соединение и гарантированно создаёт схему (идемпотентно)."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(_SCHEMA)
    return conn
