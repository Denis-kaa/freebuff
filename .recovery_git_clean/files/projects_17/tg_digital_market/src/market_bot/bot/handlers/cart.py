"""cart.py — оформление заказа, оплата, доставка.

Два варианта оплаты:
1. Mock (developer-mode) — пользователь нажимает inline-кнопку;
   `finalize` вызывается синхронно из callback.
2. Telegram Stars — `Bot.create_invoice_link`, бот ждёт pre_checkout_query
   и successful_payment.

Общий принцип: вся работа с БД вызывается через asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from ..keyboards import CartAction, confirm_purchase_kb
from ..models import NotificationKind
from ..services.payments import IncomingPayment

router = Router(name="cart")
logger = logging.getLogger(__name__)


# ─── Шаг 1: confirm → создать order + payment ──────────────────────────────


@router.callback_query(CartAction.filter(F.action == "confirm"))
async def cb_confirm(call: CallbackQuery, callback_data: CartAction, services) -> None:
    user_id = call.from_user.id
    try:
        order, item = await asyncio.to_thread(
            services.orders.create_order_for_product, user_id, callback_data.product_id
        )
    except Exception as exc:
        await call.answer(f"⛔ Не удалось оформить: {exc!s***REMOVED***", show_alert=True)
        return
    payment = await asyncio.to_thread(services.payments.attach_to_order, order)
    is_mock = services.config.payment_provider == "mock"
    if is_mock:
        text = (
            f"🧾 <b>Заказ #{order.id***REMOVED***</b>\n"
            f"Товар: {item.product_name***REMOVED*** · ⭐{item.price_stars***REMOVED***\n\n"
            f"Платёж #{payment.id***REMOVED*** создан (mock).\n"
            f"Нажмите «Подтверждаю», чтобы симулировать оплату."
        )
        await call.message.edit_text(
            text, reply_markup=confirm_purchase_kb(callback_data.product_id, order.id, payment.id, is_mock=True)
        )
        await services.notifications.notify_admins(
            admin_ids=sorted(services.config.admin_ids),
            kind=NotificationKind.ADMIN_ALERT,
            text=f"🆕 Заказ #{order.id***REMOVED*** · mock payment #{payment.id***REMOVED***",
        )
    else:
        # Telegram Stars: отправим invoice сообщением.
        await _send_invoice(call.message, services, order, item)
    await call.answer()


@router.callback_query(CartAction.filter(F.action == "pay_mock"))
async def cb_pay_mock(call: CallbackQuery, callback_data: CartAction, services) -> None:
    payment_id = callback_data.payment_id
    order_id = callback_data.order_id
    payment = await asyncio.to_thread(services.repo.get_payment, payment_id)
    if payment is None or payment.status.value != "pending":
        await call.answer("Платёж уже финализирован.", show_alert=True)
        return
    incoming = IncomingPayment(
        external_id=f"mock://{payment.id***REMOVED***",
        expected_amount=payment.amount_stars,
    )
    try:
        await asyncio.to_thread(services.payments.finalize, payment, incoming)
        await asyncio.to_thread(services.delivery.publish, order_id)
    except Exception as exc:
        await call.answer(f"❌ Ошибка: {exc!s***REMOVED***", show_alert=True)
        logger.exception("pay_mock failed")
        return
    code = await asyncio.to_thread(services.delivery.code_for_order, order_id)
    user = await asyncio.to_thread(services.repo.get_user, call.from_user.id)
    user_id = user.id if user else call.from_user.id
    await services.notifications.notify_user(
        user_id=user_id,
        kind=NotificationKind.ORDER_DELIVERED,
        text=f"✅ Оплата прошла! Заказ #{order_id***REMOVED***.\n\nВаш код:\n<code>{code or '(код не найден)'***REMOVED***</code>",
    )
    await call.message.edit_text(
        f"✅ Оплата прошла! Заказ #{order_id***REMOVED*** доставлен.\n\n"
        f"Ваш код:\n<code>{code or '(код не найден)'***REMOVED***</code>"
    )
    await call.answer()


@router.callback_query(CartAction.filter(F.action == "cancel"))
async def cb_cancel(call: CallbackQuery, callback_data: CartAction, services) -> None:
    order_id = callback_data.order_id
    try:
        await asyncio.to_thread(services.orders.cancel, order_id, reason="user_cancel")
    except Exception as exc:
        await call.answer(f"❌ Не отменён: {exc!s***REMOVED***", show_alert=True)
        return
    await services.notifications.notify_user(
        user_id=call.from_user.id,
        kind=NotificationKind.ORDER_CANCELLED,
        text=f"❌ Заказ #{order_id***REMOVED*** отменён.",
    )
    await call.message.edit_text(f"❌ Заказ #{order_id***REMOVED*** отменён.")
    await call.answer()


# ─── Telegram Stars: создание инвойса ──────────────────────────────────────


async def _send_invoice(target_message: Message, services, order, item) -> None:
    """Отправить invoice-link в Telegram (Telegram Stars)."""
    bot: Bot = target_message.bot
    cfg = services.config
    if not cfg.payment_provider_token:
        await target_message.edit_text("❌ Не задан PAYMENT_PROVIDER_TOKEN (см. .env.example).")
        return
    try:
        prices = [LabeledPrice(label=item.product_name[:32***REMOVED***, amount=order.total_stars)***REMOVED***
        payload = json.dumps({"order_id": order.id***REMOVED***)
        link = await bot.create_invoice_link(
            title=item.product_name[:64***REMOVED***,
            description=item.product_name[:254***REMOVED***,
            payload=payload,
            provider_token=cfg.payment_provider_token,
            currency="XTR",
            prices=prices,
        )
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить", url=link)***REMOVED******REMOVED***
        )
        await target_message.edit_text(
            f"🧾 <b>Заказ #{order.id***REMOVED***</b>\n"
            f"Товар: {item.product_name***REMOVED*** · ⭐{order.total_stars***REMOVED***\n\n"
            f"Нажмите кнопку ниже для оплаты Telegram Stars.",
            reply_markup=kb,
        )
    except Exception as exc:
        await target_message.edit_text(f"❌ Не удалось создать инвойс: {exc!s***REMOVED***")
        logger.exception("create_invoice_link failed")


# ─── Telegram Stars: pre_checkout_query и successful_payment ──────────────


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery, services) -> Any:
    """Ответить на pre_checkout_query в течение 10 сек: да/нет."""
    try:
        payload = json.loads(query.invoice_payload or "{***REMOVED***")
        order_id = int(payload["order_id"***REMOVED***)
    except Exception:
        await query.answer(ok=False, error_message_payload="Invalid payload.")
        return
    order = await asyncio.to_thread(services.orders.get, order_id)
    if order is None or order.status.value != "pending":
        await query.answer(ok=False, error_message_payload="Order unavailable.")
        return
    if order.total_stars != query.total_amount:
        await query.answer(ok=False, error_message_payload="Amount mismatch.")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, services) -> Any:
    """Обработка SuccessfulPayment от Telegram."""
    sp = message.successful_payment
    if sp is None:
        return
    try:
        payload = json.loads(sp.invoice_payload or "{***REMOVED***")
        order_id = int(payload["order_id"***REMOVED***)
    except Exception:
        logger.exception("bad payload in successful_payment")
        return
    order = await asyncio.to_thread(services.orders.get, order_id)
    if order is None:
        logger.error("successful_payment for missing order %s", order_id)
        return
    payment = await asyncio.to_thread(services.payments.attach_to_order, order)
    incoming = IncomingPayment(
        external_id=sp.telegram_payment_charge_id,
        expected_amount=sp.total_amount,
        currency=sp.currency or "XTR",
    )
    try:
        await asyncio.to_thread(services.payments.finalize, payment, incoming)
        await asyncio.to_thread(services.delivery.publish, order_id)
    except Exception:
        logger.exception("successful_payment finalize failed")
        return
    code = await asyncio.to_thread(services.delivery.code_for_order, order_id)
    await services.notifications.notify_user(
        user_id=message.from_user.id,
        kind=NotificationKind.ORDER_DELIVERED,
        text=f"✅ Оплата прошла! Заказ #{order_id***REMOVED***.\n\nВаш код:\n<code>{code or '(код не найден)'***REMOVED***</code>",
    )
    await message.answer(
        f"✅ Оплата прошла! Заказ #{order_id***REMOVED***.\n\n"
        f"Ваш код:\n<code>{code or '(код не найден)'***REMOVED***</code>"
    )
