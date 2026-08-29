-- schema.sql — инициализация БД `tg_digital_market` (SQLite)
-- Идемпотентно: можно запускать многократно (CREATE IF NOT EXISTS).

PRAGMA foreign_keys = ON;

-- ─── Пользователи ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,            -- telegram id
    username        TEXT,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user',   -- user | seller | admin
    created_at      TEXT NOT NULL                   -- ISO-8601 UTC
);

-- ─── Товары ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id       INTEGER NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT 'other',
    price_stars     INTEGER NOT NULL CHECK (price_stars >= 1),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT NOT NULL,
    FOREIGN KEY (seller_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_products_active ON products (is_active);
CREATE INDEX IF NOT EXISTS idx_products_seller  ON products (seller_id);

-- ─── Цифровые ключи (стоки) товаров ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    code            TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'available'  -- available | reserved | delivered
                                CHECK (status IN ('available','reserved','delivered')),
    order_id        INTEGER,
    reserved_at     TEXT,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    FOREIGN KEY (order_id)   REFERENCES orders   (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pkeys_product_status ON product_keys (product_id, status);

-- ─── Заказы ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    total_stars         INTEGER NOT NULL CHECK (total_stars >= 1),
    status              TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','paid','delivered','cancelled','failed')),
    payment_provider    TEXT,
    payment_external_id TEXT,
    created_at          TEXT NOT NULL,
    paid_at             TEXT,
    delivered_at        TEXT,
    cancelled_at        TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders (created_at DESC);

-- ─── Позиции заказа (MVP: одна позиция) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    product_id      INTEGER NOT NULL,
    product_name    TEXT NOT NULL,           -- снимок имени на момент заказа
    price_stars     INTEGER NOT NULL CHECK (price_stars >= 1),
    FOREIGN KEY (order_id)   REFERENCES orders   (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_items_order ON order_items (order_id);

-- ─── Платежи ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL UNIQUE,         -- одна активная попытка на заказ
    provider        TEXT NOT NULL,                   -- 'mock' | 'telegram_stars'
    external_id     TEXT,                            -- id из платёжной системы
    amount_stars    INTEGER NOT NULL CHECK (amount_stars >= 1),
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','succeeded','failed')),
    payload         TEXT,                            -- JSON-провайдер-специфичные данные
    created_at      TEXT NOT NULL,
    finished_at     TEXT,
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status);

-- ─── Выдачи (deliveries) ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL UNIQUE,        -- одна выдача на заказ
    product_id      INTEGER NOT NULL,
    product_key_id  INTEGER NOT NULL UNIQUE,        -- ключ нельзя выдать дважды
    delivered_at    TEXT NOT NULL,
    FOREIGN KEY (order_id)       REFERENCES orders       (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id)     REFERENCES products     (id) ON DELETE RESTRICT,
    FOREIGN KEY (product_key_id) REFERENCES product_keys (id) ON DELETE RESTRICT
);

-- ─── Уведомления (журнал) ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER,                       -- NULL = broadcast
    broadcast_to_admins INTEGER NOT NULL DEFAULT 0
                            CHECK (broadcast_to_admins IN (0,1)),
    kind                TEXT NOT NULL,
    text                TEXT NOT NULL,
    payload             TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, created_at DESC);
