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

-- Конструктор разделов заказа (2026-09-08): пользователь сам добавляет/
-- меняет/сортирует разделы главного экрана. kinds — закрытый словарь
-- (ANTI-6b), проверяется в store.
CREATE TABLE IF NOT EXISTS ui_sections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL,
    required    INTEGER NOT NULL DEFAULT 0,
    options_json TEXT NOT NULL DEFAULT '[]',
    position    INTEGER NOT NULL DEFAULT 0,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_section_values (
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES ui_sections(id) ON DELETE CASCADE,
    value      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (order_id, section_id)
);

-- Клиенты и контакты (Этап 1 роадмапа v6, §6 промт_4): клиент ≠ контакт —
-- один клиент может иметь несколько контактов разных каналов.
CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'физлицо',
    note        TEXT NOT NULL DEFAULT '',
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    channel     TEXT NOT NULL,
    value       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE (channel, value)
);

-- Единый реестр материалов (Этап 1, §18 промт_4): один материал — одна
-- сущность с алиасами (BR-W1). roll/sheet размеры в мм (consumption engine).
CREATE TABLE IF NOT EXISTS materials (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE,
    aliases_json     TEXT NOT NULL DEFAULT '[]',
    category         TEXT NOT NULL DEFAULT 'general',
    consumption_mode TEXT NOT NULL DEFAULT 'AREA',
    base_unit        TEXT NOT NULL DEFAULT 'm2',
    purchase_unit    TEXT NOT NULL DEFAULT 'm2',
    purchase_cost    REAL NOT NULL DEFAULT 0,
    price_unit       TEXT NOT NULL DEFAULT 'm2',
    roll_width       REAL,
    roll_length      REAL,
    sheet_width      REAL,
    sheet_height     REAL,
    min_stock        REAL NOT NULL DEFAULT 0,
    supplier         TEXT,
    active           INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

-- Сметы (Этап 2 роадмапа v6, §22/§24/§49 промт_4): смета создаётся из
-- расчёта/черновика, статусы — закрытый словарь в store; ACCEPTED фиксирует
-- snapshot версий (неизменяемость задним числом).
CREATE TABLE IF NOT EXISTS estimates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    status      TEXT NOT NULL DEFAULT 'draft',
    total       REAL NOT NULL DEFAULT 0,
    client_id   INTEGER REFERENCES clients(id),
    note        TEXT NOT NULL DEFAULT '',
    valid_until TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estimate_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estimate_id   INTEGER NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    kind          TEXT NOT NULL CHECK (kind IN ('price_list', 'calculator', 'manual')),
    name          TEXT NOT NULL,
    price         REAL NOT NULL,
    qty           REAL NOT NULL DEFAULT 1,
    calculator_id TEXT,
    params_json   TEXT,
    price_list_item_id INTEGER REFERENCES price_list_items(id),
    position      INTEGER NOT NULL DEFAULT 0
);

-- Snapshot версий при ACCEPTED (§49): создаётся ровно один на смету,
-- после ACCEPTED не изменяется (неизменяемость проверяется тестом).
CREATE TABLE IF NOT EXISTS calc_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    estimate_id INTEGER NOT NULL UNIQUE REFERENCES estimates(id),
    engine_version     TEXT NOT NULL,
    registry_checksum  TEXT NOT NULL,
    catalog_checksum   TEXT NOT NULL,
    policy_version     TEXT NOT NULL DEFAULT 'v1',
    details_json       TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_price_items_name ON price_list_items(name);
CREATE INDEX IF NOT EXISTS idx_sections_position ON ui_sections(position);
CREATE INDEX IF NOT EXISTS idx_contacts_client ON contacts(client_id);
CREATE INDEX IF NOT EXISTS idx_contacts_value ON contacts(value);
CREATE INDEX IF NOT EXISTS idx_materials_name ON materials(name);
CREATE INDEX IF NOT EXISTS idx_estimates_status ON estimates(status);
CREATE INDEX IF NOT EXISTS idx_estimate_items_estimate ON estimate_items(estimate_id);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Аддитивные миграции (idемпотентно): wishes и client_id у orders."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if "wishes" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN wishes TEXT NOT NULL DEFAULT ''")
    if "client_id" not in columns:
        # Этап 1: заказ узнаёт клиента (nullable — старые заказы анонимны).
        conn.execute("ALTER TABLE orders ADD COLUMN client_id INTEGER REFERENCES clients(id)")
    if "estimate_id" not in columns:
        # Этап 2: заказ из сметы (§9 промт_4) — происхождение без ручного переноса.
        conn.execute("ALTER TABLE orders ADD COLUMN estimate_id INTEGER REFERENCES estimates(id)")

    item_columns = {row[1] for row in conn.execute("PRAGMA table_info(order_items)")}
    if "consumption_json" not in item_columns:
        # Этап 3: snapshot расхода материала позиции (расчёт движком при
        # сохранении заказа; неизменяем после сохранения — §49 дух).
        conn.execute("ALTER TABLE order_items ADD COLUMN consumption_json TEXT")


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
    _migrate(conn)
    return conn
