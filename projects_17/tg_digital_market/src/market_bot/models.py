"""models.py — доменные сущности `tg_digital_market`.

Используются во всех слоях: репозиторий возвращает/принимает эти dataclass'ы,
сервисы оперируют ими, aiogram-слой получает их для рендеринга.
Анти-OWASP: сущности frozen, чтобы случайно не мутировать объект вне транзакции.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ─── Роли пользователей ─────────────────────────────────────────────────────


class UserRole(str, Enum):
    USER = "user"
    SELLER = "seller"
    ADMIN = "admin"


# ─── Статусы и типы ─────────────────────────────────────────────────────────


class OrderStatus(str, Enum):
    PENDING = "pending"           # создан, ждёт оплаты
    PAID = "paid"                 # оплачен, доставляется
    DELIVERED = "delivered"       # ключ выдан пользователю
    CANCELLED = "cancelled"       # отменён (TTL истёк или вручную)
    FAILED = "failed"             # ошибка оплаты


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class KeyStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    DELIVERED = "delivered"


class NotificationKind(str, Enum):
    ORDER_CREATED = "order_created"
    ORDER_PAID = "order_paid"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    ADMIN_ALERT = "admin_alert"
    SELLER_NEW_SALE = "seller_new_sale"


# ─── Сущности ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class User:
    """Telegram-пользователь. `id` — это telegram_id."""
    id: int
    username: Optional[str***REMOVED***
    full_name: str
    role: UserRole
    created_at: datetime


@dataclass(frozen=True)
class Product:
    """Товар в каталоге."""
    id: int
    seller_id: int
    name: str
    description: str
    category: str
    price_stars: int           # цена в звёздах (целое, минимальная единица)
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class ProductKey:
    """Цифровой код (ключ) конкретного товара."""
    id: int
    product_id: int
    code: str
    status: KeyStatus
    order_id: Optional[int***REMOVED***


@dataclass(frozen=True)
class Order:
    """Заказ. MVP: один товар, один ключ."""
    id: int
    user_id: int
    total_stars: int
    status: OrderStatus
    payment_provider: Optional[str***REMOVED***
    payment_external_id: Optional[str***REMOVED***
    created_at: datetime
    paid_at: Optional[datetime***REMOVED*** = None
    delivered_at: Optional[datetime***REMOVED*** = None
    cancelled_at: Optional[datetime***REMOVED*** = None


@dataclass(frozen=True)
class OrderItem:
    """Позиция в заказе (снимок имени и цены на момент покупки)."""
    id: int
    order_id: int
    product_id: int
    product_name: str
    price_stars: int


@dataclass(frozen=True)
class Payment:
    """Платёжная транзакция."""
    id: int
    order_id: int
    provider: str
    external_id: Optional[str***REMOVED***
    amount_stars: int
    status: PaymentStatus
    payload: Optional[str***REMOVED***
    created_at: datetime
    finished_at: Optional[datetime***REMOVED*** = None


@dataclass(frozen=True)
class Delivery:
    """Выдача ключа пользователю в рамках заказа."""
    id: int
    order_id: int
    product_key_id: int
    product_id: int
    delivered_at: datetime


@dataclass(frozen=True)
class Notification:
    """Лог уведомления, отправленного пользователю или админам."""
    id: int
    user_id: Optional[int***REMOVED***
    broadcast_to_admins: bool
    kind: NotificationKind
    text: str
    payload: Optional[str***REMOVED***
    created_at: datetime
