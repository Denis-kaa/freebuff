"""admin.py — админ-панель.

Только для пользователей из `Config.admin_ids`. MVP — статистика и
promote/demote через reply на next-steps.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..keyboards import AdminAction, admin_kb

router = Router(name="admin")


def _is_admin(services, telegram_id: int) -> bool:
    return telegram_id in services.config.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, services) -> None:
    if not _is_admin(services, message.from_user.id):
        await message.answer("🚫 Команда доступна только админам.")
        return
    await message.answer("🛠 Админ-панель:", reply_markup=admin_kb())


@router.callback_query(AdminAction.filter(F.action == "stats"))
async def cb_stats(call: CallbackQuery, services) -> None:
    if not _is_admin(services, call.from_user.id):
        await call.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    stats = await asyncio.to_thread(services.repo.stats_summary)
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{stats['users_total']}</b>\n"
        f"📦 Товаров: <b>{stats['products_total']}</b>\n"
        f"🧾 Заказов всего: <b>{stats['orders_total']}</b>\n"
        f"✅ Доставлено: <b>{stats['orders_delivered']}</b>\n"
        f"💰 Выручка (stars): <b>{stats['revenue_stars']}</b>\n"
        f"🗝 Свободных ключей: <b>{stats['keys_available']}</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_kb())
    await call.answer()
