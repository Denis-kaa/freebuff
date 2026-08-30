"""services/orders.py — стейт-машина заказа.

Переходы:
   (нет) ──create_order_for_product──▶ PENDING ──mark_paid──▶ PAID ──deliver──▶ DELIVERED
                                        │
                                        └──TTL expire (с закрытием payment) ──▶ CANCELLED
                                        └──payment fail──────────────▶ FAILED

Защиты (применены после архитектурного ревью thinker'а):
  * `reserve_key_for_order` использует UPDATE+подзапрос (атомарно).
  * `cancel` ЗАПРЕЩАЕТ отмену PAID/DELIVERED — refund-флоу делается отдельно.
  * `mark_paid` идемпотентен: повторный вызов на PAID/DELIVERED — no-op,
    чтобы Telegram не зацикливал вебхуки.
  * `expire_overdue` параллельно фейлит связанный `payment` (если был создан),
    чтобы у заказа не висел «повисший» PENDING платёж.
  * `recover_paid_orphans` — авто-восстановление при старте бота: ищет PAID
    заказы без выдачи (если процесс упал в `mark_paid → DeliveryService.publish`).
  * `_release_unfinished_keys` сделан одним SQL вместо вложенного цикла.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from ..db.repository import Repository
from ..models import Order, OrderItem, OrderStatus

if TYPE_CHECKING:  # избегаем циклического импорта в рантайме
    from .payments import PaymentService


class OrderError(Exception):
    """Базовая ошибка заказа."""


class OutOfStockError(OrderError):
    """Все ключи проданы — заказ не может быть оформлен."""


class InvalidOrderStateError(OrderError):
    """Попытка перевести заказ в недопустимое состояние."""


class OrderService:
    def __init__(
        self,
        repo: Repository,
        payment_service: Optional["PaymentService"] = None,
    ) -> None:
        self._repo = repo
        self._payment_service = payment_service

    # ── Создание ────────────────────────────────────────────────────────────

    def create_order_for_product(
        self, user_id: int, product_id: int
    ) -> tuple[Order, OrderItem]:
        """Создать pending-заказ на 1 товар с атомарным резервом ключа.

        Возвращает (Order, OrderItem). Если ключа в стоке нет — OutOfStockError,
        а заказ переводится в FAILED (без платежа, без выдачи).
        """
        product = self._repo.get_product(product_id)
        if product is None or not product.is_active:
            raise InvalidOrderStateError(f"Товар #{product_id} недоступен.")
        if product.seller_id == user_id:
            raise InvalidOrderStateError("Нельзя купить собственный товар.")

        order = self._repo.create_order(
            user_id=user_id,
            total_stars=product.price_stars,
            status=OrderStatus.PENDING,
        )
        item = self._repo.add_order_item(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            price_stars=product.price_stars,
        )
        key = self._repo.reserve_key_for_order(product.id, order.id)
        if key is None:
            self._repo.set_order_status(order.id, OrderStatus.FAILED, cancelled=True)
            raise OutOfStockError(
                f"Товар #{product.id} ({product.name!r}) закончился."
            )
        return order, item

    # ── Запросы ─────────────────────────────────────────────────────────────

    def get(self, order_id: int) -> Optional[Order]:
        return self._repo.get_order(order_id)

    def get_detail(self, order_id: int) -> Optional[tuple[Order, list[OrderItem]]]:
        order = self._repo.get_order(order_id)
        if order is None:
            return None
        return order, self._repo.get_order_items(order_id)

    def user_history(self, user_id: int, limit: int = 20) -> List[Order]:
        return self._repo.list_user_orders(user_id, limit=limit)

    # ── Переходы стейт-машины ──────────────────────────────────────────────

    def mark_paid(
        self, order_id: int, payment_external_id: Optional[str] = None
    ) -> Order:
        """Перевести заказ в PAID. Идемпотентен.

        Повторный вызов на PAID/DELIVERED возвращает заказ без ошибки — это
        критично для Telegram Stars, который ретраит `SuccessfulPayment`
        до подтверждения на стороне бота.
        """
        order = self._repo.get_order(order_id)
        if order is None:
            raise InvalidOrderStateError(f"Заказ #{order_id} не найден.")
        if order.status in (OrderStatus.PAID, OrderStatus.DELIVERED):
            return order  # idempotent no-op
        if order.status != OrderStatus.PENDING:
            raise InvalidOrderStateError(
                f"Нельзя оплатить заказ в статусе {order.status.value}."
            )
        self._repo.set_order_status(
            order_id,
            OrderStatus.PAID,
            payment_external_id=payment_external_id,
            paid=True,
        )
        updated = self._repo.get_order(order_id)
        assert updated is not None
        return updated

    def cancel(self, order_id: int, reason: str = "manual") -> Order:
        """Отменить PENDING-заказ.

        PAID/DELIVERED/FAILED/CANCELLED — InvalidOrderStateError. Refund-флоу
        для PAID реализуется отдельно (вне MVP).
        """
        order = self._repo.get_order(order_id)
        if order is None:
            raise InvalidOrderStateError(f"Заказ #{order_id} не найден.")
        if order.status != OrderStatus.PENDING:
            raise InvalidOrderStateError(
                f"Нельзя отменить заказ в статусе {order.status.value}. "
                "Для оплаченных заказов нужен refund; доставленные не отменяются."
            )
        self._release_unfinished_keys(order_id)
        self._repo.set_order_status(order_id, OrderStatus.CANCELLED, cancelled=True)
        if self._payment_service is not None:
            payment = self._repo.get_payment_by_order(order_id)
            if payment is not None and payment.status.value == "pending":
                self._payment_service.fail(payment, reason=reason)
        updated = self._repo.get_order(order_id)
        assert updated is not None
        return updated

    def mark_failed(self, order_id: int, reason: str = "payment_failed") -> Order:
        order = self._repo.get_order(order_id)
        if order is None:
            raise InvalidOrderStateError(f"Заказ #{order_id} не найден.")
        if order.status != OrderStatus.PENDING:
            raise InvalidOrderStateError(
                f"Нельзя перевести в failed из {order.status.value}."
            )
        self._release_unfinished_keys(order_id)
        if self._payment_service is not None:
            payment = self._repo.get_payment_by_order(order_id)
            if payment is not None and payment.status.value == "pending":
                self._payment_service.fail(payment, reason=reason)
        # ВАЖНО (фикс ревью #4): FAILED ≠ CANCELLED, не выставляем cancelled_at.
        # cancelled_at в схеме кодирует именно CANCELLED (см. SCHEMA.md не написан,
        # но в set_order_status есть отдельный флаг `cancelled`).
        self._repo.set_order_status(order_id, OrderStatus.FAILED)
        updated = self._repo.get_order(order_id)
        assert updated is not None
        return updated

    def _release_unfinished_keys(self, order_id: int) -> int:
        """Освободить все зарезервированные (но не доставленные) ключи заказа.

        Возвращает количество освобождённых ключей. Один SQL вместо вложенного
        цикла — раньше делался запрос внутри цикла по позициям.
        """
        rows = self._repo.raw_conn.execute(
            "SELECT id, status FROM product_keys WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        released = 0
        for r in rows:
            if r["status"] == "reserved":
                self._repo.release_reserved_key(r["id"])
                released += 1
        return released

    # ── TTL-сборка ──────────────────────────────────────────────────────────

    def expire_overdue(self, ttl_seconds: int) -> List[int]:
        """Перевести просроченные pending-заказы → CANCELLED. Возвращает ID.

        Параллельно фейлит связанный `payment` (если был создан) — иначе
        платёжная попытка висела бы в pending, и провайдер мог удерживать
        деньги. Возвращает список отменённых order_id.
        """
        pending = self._repo.list_pending_orders_older_than(ttl_seconds)
        cancelled: List[int] = []
        for o in pending:
            try:
                self.cancel(o.id, reason="ttl_expired")
                cancelled.append(o.id)
            except InvalidOrderStateError:
                continue
        return cancelled

    # ── Recovery ────────────────────────────────────────────────────────────

    def find_paid_orphans(self) -> List[int]:
        """Найти PAID-заказы без выдачи — кандидаты на восстановление.

        Вызывается из `bot/main.py` при старте и в background-таске.
        Восстановление (`DeliveryService.publish`) выполняется на стороне
        main, потому что для этого нужен NotificationService и операторы
        I/O вне БД.
        """
        rows = self._repo.raw_conn.execute(
            "SELECT id FROM orders WHERE status = 'paid'"
        ).fetchall()
        return [
            r["id"] for r in rows
            if self._repo.get_delivery_for_order(r["id"]) is None
        ]
