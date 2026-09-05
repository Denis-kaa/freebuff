"""common.py — общие хэндлеры: /start, /help, /mock_pay (admin-only).

`/mock_pay <payment_id>` — это команда для финализации mock-платежа.
Используется в тестах и в проде разработчиком для ручного прохождения
оплаты, если бот работает в режиме `PAYMENT_PROVIDER=mock`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards import main_menu_kb
from ..services_container import Services

router = Router(name="common")
logger = logging.getLogger(__name__)


def _ensure_user(services: Services, telegram_id: int, username: str | None, full_name: str):
    """Sync-обёртка: блокирующий DB upsert в отдельном потоке."""
    return asyncio.to_thread(
        services.repo.upsert_user, telegram_id, username, full_name
    )


@router.message(Command("start"))
async def cmd_start(message: Message, services: Services) -> None:
    user = await _ensure_user(
        services,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    role = services.config.role_for_user_id(user.id)
    if role.value != user.role.value:
        await asyncio.to_thread(services.repo.set_role, user.id, role)
    await message.answer(
        f"👋 Привет, {user.full_name***REMOVED***!\n"
        f"Это маркетплейс цифровых товаров.\n"
        f"Выберите действие в меню ниже.\n\n"
        f"Ваша роль: {role.value***REMOVED***",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🛍 <b>Каталог</b> — список товаров по категориям.\n"
        "👤 <b>Кабинет</b> — ваша роль и кнопка истории.\n"
        "📜 <b>История</b> — последние заказы.\n\n"
        "<b>Админ-команды:</b>\n"
        "/admin — открыть админ-панель (нужна роль admin).\n"
        "/mock_pay &lt;payment_id&gt; — финализировать mock-платёж.\n\n"
        "<b>Продавец:</b>\n"
        "/seller — кабинет продавца (нужна роль seller).",
    )


@router.message(F.text == "ℹ️ Помощь")
async def reply_help(message: Message) -> None:
    await cmd_help(message)


@router.message(F.text == "🛍 Каталог")
async def reply_catalog(message: Message, services: Services) -> None:
    """Прямой вход в категории из reply-кнопки."""
    categories = await asyncio.to_thread(services.catalog.list_categories)
    from .catalog import _render_categories
    await message.answer("📂 Категории:", reply_markup=_render_categories(categories))


@router.message(F.text == "👤 Кабинет")
async def reply_account(message: Message, services: Services) -> None:
    """Прямой вход в кабинет."""
    from .account import _show_account
    await _show_account(message, services)


@router.message(F.text == "📜 История")
async def reply_history(message: Message, services: Services) -> None:
    """Прямой вход в историю заказов."""
    from .account import _show_history
    await _show_history(message, services)


# ─── Admin: финализация mock-платежа ────────────────────────────────────────


@router.message(Command("mock_pay"))
async def cmd_mock_pay(message: Message, services: Services) -> Any:
    """Завершить pending-платёж (только для admin, только для mock)."""
    if not services.config.admin_ids or message.from_user.id not in services.config.admin_ids:
        await message.answer("🚫 Команда доступна только админам.")
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1***REMOVED***.isdigit():
        await message.answer("Использование: /mock_pay <payment_id>")
        return
    payment_id = int(parts[1***REMOVED***)
    payment = await asyncio.to_thread(services.repo.get_payment, payment_id)
    if payment is None:
        await message.answer(f"Платёж #{payment_id***REMOVED*** не найден.")
        return
    if payment.status.value != "pending":
        await message.answer(f"Платёж уже финализирован: {payment.status.value***REMOVED***.")
        return
    from ..services.payments import IncomingPayment
    incoming = IncomingPayment(
        external_id=f"mock://{payment.id***REMOVED***",
        expected_amount=payment.amount_stars,
    )
    try:
        await asyncio.to_thread(services.payments.finalize, payment, incoming)
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc!r***REMOVED***")
        logger.exception("mock_pay finalize failed")
        return
    # Финализируем оплату и сразу публикуем доставку.
    order_id = payment.order_id
    await asyncio.to_thread(services.orders.mark_paid, order_id, payment.external_id)
    await asyncio.to_thread(services.delivery.publish, order_id)
    code = await asyncio.to_thread(services.delivery.code_for_order, order_id)
    user_id = await asyncio.to_thread(
        lambda: services.repo.get_order(order_id).user_id
    )
    await services.notifications.notify_user(
        user_id=user_id,
        kind=_kind("order_delivered"),
        text=f"✅ Оплата прошла! Ваш код:\n\n<code>{code or '(код не найден)'***REMOVED***</code>",
    )
    await asyncio.to_thread(services.orders._release_unfinished_keys, order_id)  # noqa: SLF001
    await message.answer(
        f"✅ Платёж #{payment_id***REMOVED*** финализирован, ключ выдан.\n"
        f"Заказ #{order_id***REMOVED*** → DELIVERED."
    )


def _kind(name: str):
    # импорт ради короткого алиаса
    from ...models import NotificationKind
    return NotificationKind(name)
