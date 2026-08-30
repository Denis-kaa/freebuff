"""services/delivery.py — публикация доставки.

На этом этапе заказ уже PAID и ключ уже зарезервирован (OrderService сделал это
на этапе создания заказа). `publish` материализует выдачу: ключ становится
`delivered`, в БД появляется запись `deliveries`, заказ → DELIVERED.
"""

from __future__ import annotations

from typing import Optional

from ..db.repository import Repository
from ..models import Delivery, OrderStatus, ProductKey


class DeliveryError(Exception):
    """Базовая ошибка доставки."""


class DeliveryNotReadyError(DeliveryError):
    """Заказ ещё не оплачен или ключ не зарезервирован."""


class DeliveryService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def get_reserved_key_for_order(self, order_id: int) -> Optional[ProductKey]:
        """Найти зарезервированный ключ по order_id."""
        row = self._repo.raw_conn.execute(
            "SELECT * FROM product_keys WHERE order_id = ? AND status = 'reserved' LIMIT 1",
            (order_id,),
        ).fetchone()
        if not row:
            return None
        return Repository._key_from_row(row)

    def publish(self, order_id: int) -> Delivery:
        order = self._repo.get_order(order_id)
        if order is None:
            raise DeliveryError(f"Заказ #{order_id} не найден.")
        if order.status != OrderStatus.PAID:
            raise DeliveryNotReadyError(
                f"Заказ #{order_id} ещё не оплачен: статус {order.status.value}."
            )
        # Проверим, что доставка ещё не произошла.
        existing = self._repo.get_delivery_for_order(order_id)
        if existing is not None:
            return existing  # идемпотентно
        key = self.get_reserved_key_for_order(order_id)
        if key is None:
            raise DeliveryNotReadyError(
                f"Для заказа #{order_id} нет зарезервированного ключа."
            )
        items = self._repo.get_order_items(order_id)
        if not items:
            raise DeliveryError(f"Заказ #{order_id} без позиций.")
        product_id = items[0].product_id

        self._repo.mark_key_delivered(key.id)
        delivery = self._repo.create_delivery(
            order_id=order_id, product_id=product_id, product_key_id=key.id
        )
        self._repo.set_order_status(order_id, OrderStatus.DELIVERED, delivered=True)
        return delivery

    def code_for_order(self, order_id: int) -> Optional[str]:
        """Получить код для доставленного заказа (для UI/уведомления)."""
        delivery = self._repo.get_delivery_for_order(order_id)
        if delivery is None:
            return None
        key = self._repo.get_key(delivery.product_key_id)
        return key.code if key else None
