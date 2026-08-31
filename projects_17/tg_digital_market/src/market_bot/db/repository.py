"""repository.py — единая точка доступа к БД.

Repository инкапсулирует SQL и преобразование строк в dataclass-сущности. Сервисы
работают с типизированными моделями и не должны знать про схему таблиц.
Вызовы синхронные; в aiogram хэндлеры заворачиваются в `asyncio.to_thread`.

Атомарность: `reserve_key_for_order` работает внутри транзакции
+ проверка в UPDATE гарантирует «никто не выдаст дважды» даже при гонке.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence, Mapping, Callable
from typing import Iterable, Optional, Sequence

from ..models import (
    Delivery,
    KeyStatus,
    Notification,
    NotificationKind,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    ProductKey,
    User,
    UserRole,
)
from .database import Database


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


# ─── Repository ──────────────────────────────────────────────────────────────


class Repository:
    """Репозиторий над `Database`. Идемпотентный и потокобезопасный (sync)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def raw_conn(self):
        """Прямой доступ к SQLite-коннекшну из БД-слоя.

        Использовать осторожно: для нестандартных SELECT/UPDATE без доменной
        логики (миграции, тесты, пакетные операции вне репозитория).
        """
        return self._db.raw_conn

    # ─── users ──────────────────────────────────────────────────────────────

    @staticmethod
    def _user_from_row(row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            role=UserRole(row["role"]),
            created_at=_parse_iso(row["created_at"]) or _now(),
        )

    def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str],
        full_name: str,
    ) -> User:
        """Вставить пользователя, если нет, и вернуть актуальное состояние."""
        now = _iso(_now())
        self._db.execute(
            """
            INSERT INTO users (id, username, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                full_name = excluded.full_name
            """,
            (telegram_id, username, full_name, UserRole.USER.value, now),
        )
        row = self._db.query_one("SELECT * FROM users WHERE id = ?", (telegram_id,))
        assert row is not None
        return self._user_from_row(row)

    def get_user(self, user_id: int) -> Optional[User]:
        row = self._db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return self._user_from_row(row) if row else None

    def list_admins(self) -> list[User]:
        rows = self._db.query(
            "SELECT * FROM users WHERE role = ? ORDER BY id", (UserRole.ADMIN.value,)
        )
        return [self._user_from_row(r) for r in rows]

    def set_role(self, user_id: int, role: UserRole) -> None:
        self._db.execute(
            "UPDATE users SET role = ? WHERE id = ?", (role.value, user_id)
        )

    def list_sellers(self) -> list[User]:
        rows = self._db.query(
            "SELECT * FROM users WHERE role = ? ORDER BY id", (UserRole.SELLER.value,)
        )
        return [self._user_from_row(r) for r in rows]

    # ─── products ───────────────────────────────────────────────────────────

    @staticmethod
    def _product_from_row(row) -> Product:
        return Product(
            id=row["id"],
            seller_id=row["seller_id"],
            name=row["name"],
            description=row["description"],
            category=row["category"],
            price_stars=row["price_stars"],
            is_active=bool(row["is_active"]),
            created_at=_parse_iso(row["created_at"]) or _now(),
        )

    def create_product(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: str,
        price_stars: int,
    ) -> Product:
        now = _iso(_now())
        cur = self._db.query_one(
            """
            INSERT INTO products (seller_id, name, description, category, price_stars, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?) RETURNING *
            """,
            (seller_id, name, description, category, price_stars, now),
        )
        assert cur is not None
        return self._product_from_row(cur)

    def get_product(self, product_id: int) -> Optional[Product]:
        row = self._db.query_one("SELECT * FROM products WHERE id = ?", (product_id,))
        return self._product_from_row(row) if row else None

    def update_product(
        self,
        product_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        price_stars: Optional[int] = None,
    ) -> Optional[Product]:
        sets: list[str] = []
        params: list = []
        if name is not None:
            sets.append("name = ?"); params.append(name)
        if description is not None:
            sets.append("description = ?"); params.append(description)
        if category is not None:
            sets.append("category = ?"); params.append(category)
        if price_stars is not None:
            sets.append("price_stars = ?"); params.append(price_stars)
        if not sets:
            return self.get_product(product_id)
        params.append(product_id)
        self._db.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", params)
        return self.get_product(product_id)

    def set_product_active(self, product_id: int, is_active: bool) -> None:
        self._db.execute(
            "UPDATE products SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, product_id),
        )

    def list_products(
        self,
        *,
        active_only: bool = True,
        category: Optional[str] = None,
        seller_id: Optional[int] = None,
    ) -> list[Product]:
        sql = "SELECT * FROM products"
        clauses: list[str] = []
        params: list = []
        if active_only:
            clauses.append("is_active = 1")
        if category:
            clauses.append("category = ?"); params.append(category)
        if seller_id is not None:
            clauses.append("seller_id = ?"); params.append(seller_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"
        return [self._product_from_row(r) for r in self._db.query(sql, params)]

    def list_distinct_categories(self) -> list[str]:
        rows = self._db.query(
            "SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category"
        )
        return [r["category"] for r in rows]

    # ─── keys ───────────────────────────────────────────────────────────────

    def add_keys(self, product_id: int, codes: Iterable[str]) -> int:
        """Добавить набор ключей к товару. Возвращает количество вставленных."""
        codes = [c.strip() for c in codes if c and c.strip()]
        if not codes:
            return 0
        with self._db.transaction() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO product_keys (product_id, code, status) VALUES (?, ?, 'available')",
                [(product_id, c) for c in codes],
            )
            cnt = conn.execute(
                "SELECT COUNT(*) FROM product_keys WHERE product_id = ? AND status = 'available'",
                (product_id,),
            ).fetchone()[0]
        return cnt

    def count_available_keys(self, product_id: int) -> int:
        return int(
            self._db.scalar(
                "SELECT COUNT(*) FROM product_keys WHERE product_id = ? AND status = 'available'",
                (product_id,),
            )
            or 0
        )

    @staticmethod
    def _key_from_row(row) -> ProductKey:
        return ProductKey(
            id=row["id"],
            product_id=row["product_id"],
            code=row["code"],
            status=KeyStatus(row["status"]),
            order_id=row["order_id"],
        )

    def reserve_key_for_order(
        self, product_id: int, order_id: int
    ) -> Optional[ProductKey]:
        """Атомарно зарезервировать один доступный ключ под заказ.

        Один UPDATE с подзапросом (атомарно по построению — см. STEPS.md шаг 5):
          UPDATE product_keys
          SET status='reserved', order_id=?, reserved_at=?
          WHERE id = (SELECT id FROM product_keys
                      WHERE product_id=? AND status='available' LIMIT 1)
          RETURNING *;
        SQLite сериализует писателей; подзапрос и UPDATE под общей
        блокировкой одной транзакции. Если ключей нет — UPDATE меняет
        0 строк → rowcount=0 → None.
        Гарантия: один и тот же ключ нельзя выдать дважды.
        """
        now = _iso(_now())
        with self._db.transaction() as conn:
            cur = conn.execute(
                """
                UPDATE product_keys
                SET status = 'reserved', order_id = ?, reserved_at = ?
                WHERE id = (
                    SELECT id FROM product_keys
                    WHERE product_id = ? AND status = 'available'
                    LIMIT 1
                )
                RETURNING *
                """,
                (order_id, now, product_id),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._key_from_row(row)

    def get_key(self, key_id: int) -> Optional[ProductKey]:
        row = self._db.query_one("SELECT * FROM product_keys WHERE id = ?", (key_id,))
        return self._key_from_row(row) if row else None

    def mark_key_delivered(self, key_id: int) -> None:
        now = _iso(_now())
        self._db.execute(
            "UPDATE product_keys SET status = 'delivered' WHERE id = ?", (key_id,)
        )
        _ = now  # only used for audit (kept for future row extension)

    def release_reserved_key(self, key_id: int) -> None:
        """Откатить резервирование ключа (например, после таймаута оплаты)."""
        self._db.execute(
            "UPDATE product_keys SET status = 'available', order_id = NULL, reserved_at = NULL "
            "WHERE id = ? AND status = 'reserved'",
            (key_id,),
        )

    # ─── orders ─────────────────────────────────────────────────────────────

    @staticmethod
    def _order_from_row(row) -> Order:
        return Order(
            id=row["id"],
            user_id=row["user_id"],
            total_stars=row["total_stars"],
            status=OrderStatus(row["status"]),
            payment_provider=row["payment_provider"],
            payment_external_id=row["payment_external_id"],
            created_at=_parse_iso(row["created_at"]) or _now(),
            paid_at=_parse_iso(row["paid_at"]),
            delivered_at=_parse_iso(row["delivered_at"]),
            cancelled_at=_parse_iso(row["cancelled_at"]),
        )

    def create_order(
        self,
        user_id: int,
        total_stars: int,
        status: OrderStatus = OrderStatus.PENDING,
    ) -> Order:
        now = _iso(_now())
        cur = self._db.query_one(
            "INSERT INTO orders (user_id, total_stars, status, created_at) VALUES (?,?,?,?) RETURNING *",
            (user_id, total_stars, status.value, now),
        )
        assert cur is not None
        return self._order_from_row(cur)

    def get_order(self, order_id: int) -> Optional[Order]:
        row = self._db.query_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        return self._order_from_row(row) if row else None

    def set_order_status(
        self,
        order_id: int,
        status: OrderStatus,
        *,
        payment_provider: Optional[str] = None,
        payment_external_id: Optional[str] = None,
        paid: bool = False,
        delivered: bool = False,
        cancelled: bool = False,
    ) -> None:
        sets = ["status = ?"]
        params: list = [status.value]
        if payment_provider is not None:
            sets.append("payment_provider = ?"); params.append(payment_provider)
        if payment_external_id is not None:
            sets.append("payment_external_id = ?"); params.append(payment_external_id)
        if paid:
            sets.append("paid_at = ?"); params.append(_iso(_now()))
        if delivered:
            sets.append("delivered_at = ?"); params.append(_iso(_now()))
        if cancelled:
            sets.append("cancelled_at = ?"); params.append(_iso(_now()))
        params.append(order_id)
        self._db.execute(f"UPDATE orders SET {', '.join(sets)} WHERE id = ?", params)

    def list_user_orders(self, user_id: int, limit: int = 20) -> list[Order]:
        rows = self._db.query(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [self._order_from_row(r) for r in rows]

    def list_pending_orders_older_than(self, ttl_seconds: int) -> list[Order]:
        """Заказы в статусе pending, у которых TTL истёк."""
        cutoff = _iso(
            datetime.fromtimestamp(_now().timestamp() - ttl_seconds, tz=timezone.utc)
        )
        rows = self._db.query(
            "SELECT * FROM orders WHERE status = 'pending' AND created_at < ? ORDER BY created_at",
            (cutoff,),
        )
        return [self._order_from_row(r) for r in rows]

    def list_all_orders_for_admin(self, limit: int = 50) -> list[Order]:
        rows = self._db.query(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [self._order_from_row(r) for r in rows]

    # ─── order items ────────────────────────────────────────────────────────

    def add_order_item(
        self, order_id: int, product_id: int, product_name: str, price_stars: int
    ) -> OrderItem:
        cur = self._db.query_one(
            "INSERT INTO order_items (order_id, product_id, product_name, price_stars) "
            "VALUES (?,?,?,?) RETURNING *",
            (order_id, product_id, product_name, price_stars),
        )
        assert cur is not None
        return OrderItem(
            id=cur["id"],
            order_id=cur["order_id"],
            product_id=cur["product_id"],
            product_name=cur["product_name"],
            price_stars=cur["price_stars"],
        )

    def get_order_items(self, order_id: int) -> list[OrderItem]:
        rows = self._db.query(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
        )
        return [
            OrderItem(
                id=r["id"],
                order_id=r["order_id"],
                product_id=r["product_id"],
                product_name=r["product_name"],
                price_stars=r["price_stars"],
            )
            for r in rows
        ]

    # ─── payments ───────────────────────────────────────────────────────────

    @staticmethod
    def _payment_from_row(row) -> Payment:
        return Payment(
            id=row["id"],
            order_id=row["order_id"],
            provider=row["provider"],
            external_id=row["external_id"],
            amount_stars=row["amount_stars"],
            status=PaymentStatus(row["status"]),
            payload=row["payload"],
            created_at=_parse_iso(row["created_at"]) or _now(),
            finished_at=_parse_iso(row["finished_at"]),
        )

    def create_payment(
        self, order_id: int, provider: str, amount_stars: int, payload: Optional[str] = None
    ) -> Payment:
        now = _iso(_now())
        cur = self._db.query_one(
            "INSERT INTO payments (order_id, provider, amount_stars, status, payload, created_at) "
            "VALUES (?,?,?,?,?,?) RETURNING *",
            (order_id, provider, amount_stars, PaymentStatus.PENDING.value, payload, now),
        )
        assert cur is not None
        return self._payment_from_row(cur)

    def get_payment_by_order(self, order_id: int) -> Optional[Payment]:
        row = self._db.query_one(
            "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (order_id,),
        )
        return self._payment_from_row(row) if row else None

    def get_payment(self, payment_id: int) -> Optional[Payment]:
        row = self._db.query_one("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return self._payment_from_row(row) if row else None

    def set_payment_status(
        self,
        payment_id: int,
        status: PaymentStatus,
        *,
        external_id: Optional[str] = None,
        payload: Optional[str] = None,
    ) -> None:
        sets = ["status = ?", "finished_at = ?"]
        params: list = [status.value, _iso(_now())]
        if external_id is not None:
            sets.append("external_id = ?"); params.append(external_id)
        if payload is not None:
            sets.append("payload = ?"); params.append(payload)
        params.append(payment_id)
        self._db.execute(f"UPDATE payments SET {', '.join(sets)} WHERE id = ?", params)

    # ─── deliveries ─────────────────────────────────────────────────────────

    def create_delivery(
        self, order_id: int, product_id: int, product_key_id: int
    ) -> Delivery:
        cur = self._db.query_one(
            "INSERT INTO deliveries (order_id, product_id, product_key_id, delivered_at) "
            "VALUES (?,?,?,?) RETURNING *",
            (order_id, product_id, product_key_id, _iso(_now())),
        )
        assert cur is not None
        return Delivery(
            id=cur["id"],
            order_id=cur["order_id"],
            product_id=cur["product_id"],
            product_key_id=cur["product_key_id"],
            delivered_at=_parse_iso(cur["delivered_at"]) or _now(),
        )

    def get_delivery_for_order(self, order_id: int) -> Optional[Delivery]:
        row = self._db.query_one(
            "SELECT * FROM deliveries WHERE order_id = ?", (order_id,)
        )
        if not row:
            return None
        return Delivery(
            id=row["id"],
            order_id=row["order_id"],
            product_id=row["product_id"],
            product_key_id=row["product_key_id"],
            delivered_at=_parse_iso(row["delivered_at"]) or _now(),
        )

    # ─── notifications ──────────────────────────────────────────────────────

    def add_notification(
        self,
        text: str,
        kind: NotificationKind,
        *,
        user_id: Optional[int] = None,
        broadcast_to_admins: bool = False,
        payload: Optional[str] = None,
    ) -> Notification:
        now = _iso(_now())
        cur = self._db.query_one(
            "INSERT INTO notifications (user_id, broadcast_to_admins, kind, text, payload, created_at) "
            "VALUES (?,?,?,?,?,?) RETURNING *",
            (user_id, 1 if broadcast_to_admins else 0, kind.value, text, payload, now),
        )
        assert cur is not None
        return Notification(
            id=cur["id"],
            user_id=cur["user_id"],
            broadcast_to_admins=bool(cur["broadcast_to_admins"]),
            kind=NotificationKind(cur["kind"]),
            text=cur["text"],
            payload=cur["payload"],
            created_at=_parse_iso(cur["created_at"]) or _now(),
        )

    def list_notifications_for_user(self, user_id: int, limit: int = 20) -> list[Notification]:
        rows = self._db.query(
            "SELECT * FROM notifications WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [
            Notification(
                id=r["id"],
                user_id=r["user_id"],
                broadcast_to_admins=bool(r["broadcast_to_admins"]),
                kind=NotificationKind(r["kind"]),
                text=r["text"],
                payload=r["payload"],
                created_at=_parse_iso(r["created_at"]) or _now(),
            )
            for r in rows
        ]

    # ─── статистика для админки ─────────────────────────────────────────────

    def stats_summary(self) -> dict:
        users_total = int(self._db.scalar("SELECT COUNT(*) FROM users") or 0)
        products_total = int(self._db.scalar("SELECT COUNT(*) FROM products") or 0)
        orders_total = int(self._db.scalar("SELECT COUNT(*) FROM orders") or 0)
        orders_delivered = int(
            self._db.scalar("SELECT COUNT(*) FROM orders WHERE status = 'delivered'") or 0
        )
        revenue_stars = int(
            self._db.scalar(
                "SELECT COALESCE(SUM(total_stars),0) FROM orders WHERE status IN ('paid','delivered')"
            )
            or 0
        )
        keys_available = int(
            self._db.scalar("SELECT COUNT(*) FROM product_keys WHERE status = 'available'") or 0
        )
        return {
            "users_total": users_total,
            "products_total": products_total,
            "orders_total": orders_total,
            "orders_delivered": orders_delivered,
            "revenue_stars": revenue_stars,
            "keys_available": keys_available,
        }
