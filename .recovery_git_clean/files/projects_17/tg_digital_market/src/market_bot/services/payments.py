"""services/payments.py — порт `PaymentProvider` и адаптеры.

Зачем порт: заказчик требует «подключить платёжную систему», но без реального
тогена/провайдера она непроверяема в test/sandbox. Поэтому вводим абстракцию:
  - `MockPaymentProvider` — сразу помечает платёж «готово к подтверждению»,
    финальный succeeded выставляется admin-командой или тестом.
  - `TelegramStarsVerifyProvider` — verify-only в режиме sandbox; реальная отправка
    инвойса остаётся в aiogram-слое (handlers/cart.py — `Bot.create_invoice_link`),
    здесь только проверка суммы/валюты XTR.

`PaymentService` управляет жизненным циклом: pending → succeeded/failed,
с реакцией на finalize (вызов `orders.mark_paid(...)` + `delivery.publish(...)`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from ..db.repository import Repository
from ..models import Order, OrderStatus, Payment, PaymentStatus


# ─── Исключения ─────────────────────────────────────────────────────────────


class PaymentError(Exception):
    """Базовая ошибка платежа."""


class PaymentAlreadyProcessedError(PaymentError):
    """Платёж уже в succeeded/failed — повторный финал недопустим."""


class PaymentVerificationError(PaymentError):
    """Сумма или валюта платежа не совпадают — попытка мошенничества."""


# ─── Порт ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IncomingPayment:
    """Сырые данные от платёжной системы для проверки."""
    external_id: str
    expected_amount: int         # в звёздах/минимальных единицах
    currency: Optional[str***REMOVED*** = None   # если есть (например "XTR")


class PaymentProvider(Protocol):
    """Минимальный контракт платёжного провайдера.

    Реализации:
      - MockPaymentProvider            : для dev/test
      - TelegramStarsVerifyProvider    : для прод (verify only; отправку делает aiogram)
    """
    name: str

    def verify(self, incoming: IncomingPayment) -> None:
        """Подтвердить, что платёж валиден. Бросает PaymentVerificationError."""
        ...


# ─── Адаптеры ────────────────────────────────────────────────────────────────


class MockPaymentProvider:
    """Mock-провайдер: всегда проходит verify; succeeded выставляется извне."""

    name = "mock"

    def verify(self, incoming: IncomingPayment) -> None:
        # В mock-режиме проверка отсутствует — все суммы принимаются.
        # Контроль суммы остаётся в OrderService (сверяется с `total_stars`).
        if incoming.expected_amount <= 0:
            raise PaymentVerificationError(
                f"Сумма должна быть > 0 (received {incoming.expected_amount***REMOVED***)"
            )


class TelegramStarsVerifyProvider:
    """Verify-адаптер для Telegram Stars (XTR в Telegram API)."""

    name = "telegram_stars"

    def verify(self, incoming: IncomingPayment) -> None:
        if incoming.expected_amount <= 0:
            raise PaymentVerificationError(
                f"Сумма должна быть > 0 (received {incoming.expected_amount***REMOVED***)"
            )
        if incoming.currency is not None and incoming.currency != "XTR":
            raise PaymentVerificationError(
                f"Неверная валюта: ожидаем XTR, пришло {incoming.currency!r***REMOVED***"
            )


def get_provider(name: str) -> PaymentProvider:
    """Фабрика провайдера по имени (env-переменная)."""
    name = name.strip().lower()
    if name == "mock":
        return MockPaymentProvider()
    if name in ("telegram_stars", "stars", "telegram-stars"):
        return TelegramStarsVerifyProvider()
    raise PaymentError(f"Неизвестный платёжный провайдер: {name!r***REMOVED***")


# ─── Сервис ──────────────────────────────────────────────────────────────────


class PaymentService:
    """Высокоуровневый сервис: создать платёж, финализировать по verify."""

    def __init__(self, repo: Repository, provider: PaymentProvider) -> None:
        self._repo = repo
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def attach_to_order(self, order: Order) -> Payment:
        """Создать платёжную попытку для существующего заказа. Идемпотентен.

        На этот шаг можно наступить повторно (Telegram ретраит successful_payment,
        или процесс перезапустился между create_order и инвойсом). Семантика:
          * existing=None → создаём новый payment;
          * existing=PENDING → возвращаем его (повтор использовать);
          * existing=SUCCEEDED → нельзя «повторно привязать», ошибка;
          * existing=FAILED → тоже ошибка (заказ должен быть уже терминальным).
        ВАЖНО: payments.order_id имеет UNIQUE — нельзя пытаться создать второй.
        """
        if order.status not in (OrderStatus.PENDING,):
            raise PaymentError(
                f"К платежу можно привязать только pending-заказ; текущий: {order.status.value***REMOVED***"
            )
        existing = self._repo.get_payment_by_order(order.id)
        if existing is not None:
            if existing.status in (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
                raise PaymentAlreadyProcessedError(
                    f"Заказ #{order.id***REMOVED*** уже финализирован "
                    f"(payment #{existing.id***REMOVED***, {existing.status.value***REMOVED***)"
                )
            # PENDING → идемпотентно возвращаем тот же.
            return existing
        return self._repo.create_payment(
            order_id=order.id,
            provider=self._provider.name,
            amount_stars=order.total_stars,
            payload=None,
        )

    def finalize(self, payment: Payment, incoming: IncomingPayment) -> tuple[Payment, bool***REMOVED***:
        """Проверить платёж через провайдер и обновить статус. Идемпотентен.

        Защиты:
          1. payment.status != PENDING → PaymentAlreadyProcessedError.
          2. order.status in (PAID, DELIVERED) → no-op по заказу;
             помечаем только payment как SUCCEEDED.
             Это предотвращает ревёрт DELIVERED обратно в PAID при
             ретрае Telegram successful_payment.
        """
        if payment.status != PaymentStatus.PENDING:
            raise PaymentAlreadyProcessedError(
                f"Платёж #{payment.id***REMOVED*** уже финализирован: {payment.status.value***REMOVED***"
            )
        order = self._repo.get_order(payment.order_id)
        if order is None:
            raise PaymentError(f"Заказ #{payment.order_id***REMOVED*** не найден.")
        self._provider.verify(incoming)
        self._repo.set_payment_status(
            payment.id,
            PaymentStatus.SUCCEEDED,
            external_id=incoming.external_id,
        )
        if order.status not in (OrderStatus.PAID, OrderStatus.DELIVERED):
            self._repo.set_order_status(
                order.id,
                OrderStatus.PAID,
                payment_provider=payment.provider,
                payment_external_id=incoming.external_id,
                paid=True,
            )
        updated = self._repo.get_payment(payment.id)
        assert updated is not None
        return updated, True

    def fail(self, payment: Payment, reason: str) -> Payment:
        """Перевести платёж в failed (timeout, ручной отказ, ошибка).

        ВАЖНО (фикс ревью #3d): НЕ трогаем status заказа — order-стейтом
        управляет OrderService. Раньше здесь был бажный
        `set_order_status(FAILED, cancelled=True)`, который из expire_overdue
        превращал заказ в FAILED вместо ожидаемого CANCELLED.
        """
        if payment.status != PaymentStatus.PENDING:
            raise PaymentAlreadyProcessedError(
                f"Платёж #{payment.id***REMOVED*** уже финализирован: {payment.status.value***REMOVED***"
            )
        self._repo.set_payment_status(
            payment.id,
            PaymentStatus.FAILED,
            payload=reason,
        )
        updated = self._repo.get_payment(payment.id)
        assert updated is not None
        return updated
