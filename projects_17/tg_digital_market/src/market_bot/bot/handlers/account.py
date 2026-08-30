"""account.py — личный кабинет и история заказов."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..keyboards import MenuAction, account_kb
from ..models import OrderStatus

router = Router(name="account")


async def _show_account(message: Message, services) -> None:
    user_id = message.from_user.id
    user = await asyncio.to_thread(services.repo.get_user, user_id)
    if user is None:
        await message.answer("Сначала нажмите /start.")
        return
    history = await asyncio.to_thread(services.orders.user_history, user_id, limit=5)
    delivered = sum(1 for o in history if o.status == OrderStatus.DELIVERED)
    is_admin = user_id in services.config.admin_ids
    is_seller = user.role.value == "seller"
    text = (
        f"👤 <b>{user.full_name}</b>\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"🎭 Роль: <b>{user.role.value}</b>\n\n"
        f"Всего заказов: <b>{len(history)}</b>\n"
        f"Доставлено: <b>{delivered}</b>"
    )
    await message.answer(text, reply_markup=account_kb(is_seller=is_seller, is_admin=is_admin))


async def _show_history(message: Message, services) -> None:
    user_id = message.from_user.id
    orders = await asyncio.to_thread(services.orders.user_history, user_id, limit=10)
    if not orders:
        await message.answer("📭 У вас пока нет заказов.")
        return
    lines = ["📜 <b>Ваши заказы:</b>\n"]
    for o in orders:
        emoji = {
            "pending": "🕒",
            "paid": "💳",
            "delivered": "✅",
            "cancelled": "❌",
            "failed": "⚠️",
        }.get(o.status.value, "·")
        lines.append(
            f"{emoji} #{o.id} · {o.status.value} · ⭐{o.total_stars} · "
            f"{o.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
    await message.answer("\n".join(lines))


@router.callback_query(MenuAction.filter(F.action == "account"))
async def cb_account(call: CallbackQuery, services) -> None:
    # Превращаем в сообщение: можно редактировать, но проще — закрыть и ответить.
    await call.message.delete()
    fake_message = call.message  # type: ignore[assignment]
    fake_message.from_user = call.from_user  # type: ignore[attr-defined]
    await _show_account(fake_message, services)
    await call.answer()


@router.callback_query(MenuAction.filter(F.action == "history"))
async def cb_history(call: CallbackQuery, services) -> None:
    await call.message.delete()
    fake_message = call.message  # type: ignore[assignment]
    fake_message.from_user = call.from_user  # type: ignore[attr-defined]
    await _show_history(fake_message, services)
    await call.answer()
