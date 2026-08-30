"""seller.py — кабинет продавца.

Только для пользователей с role='seller'. Показывает свои товары,
позволяет добавлять новые (FSM) и пополнять сток ключей.
"""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from ..keyboards import SellerAction, seller_kb
from ..states import SellerFlow

router = Router(name="seller")


async def _is_seller(services, user_id: int) -> bool:
    user = await asyncio.to_thread(services.repo.get_user, user_id)
    return user is not None and user.role.value == "seller"


@router.message(Command("seller"))
async def cmd_seller(message: Message, services) -> None:
    if not await _is_seller(services, message.from_user.id):
        await message.answer("🚫 Команда доступна только продавцам.")
        return
    products = await asyncio.to_thread(
        services.repo.list_products, active_only=False, seller_id=message.from_user.id
    )
    if not products:
        await message.answer("🏪 У вас пока нет товаров.", reply_markup=seller_kb())
        return
    lines = ["🏪 <b>Ваши товары:</b>\n"]
    for p in products:
        stock = await asyncio.to_thread(services.catalog.available_stock, p.id)
        flag = "🟢" if p.is_active else "⚪"
        lines.append(f"{flag} #{p.id} · {p.name} · ⭐{p.price_stars} · сток {stock}")
    await message.answer("\n".join(lines), reply_markup=seller_kb())


@router.callback_query(SellerAction.filter(F.action == "add"))
async def cb_seller_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SellerFlow.adding_name)
    await call.message.edit_text("➕ Введите название товара:")
    await call.answer()


@router.message(SellerFlow.adding_name)
async def seller_add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(SellerFlow.adding_description)
    await message.answer("Введите описание (или «-» если нет):", reply_markup=ReplyKeyboardRemove())


@router.message(SellerFlow.adding_description)
async def seller_add_desc(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    await state.update_data(description="" if desc == "-" else desc)
    await state.set_state(SellerFlow.adding_category)
    await message.answer("Категория (например, steam / roblox / gift):")


@router.message(SellerFlow.adding_category)
async def seller_add_cat(message: Message, state: FSMContext) -> None:
    await state.update_data(category=message.text.strip() or "other")
    await state.set_state(SellerFlow.adding_price)
    await message.answer("Цена в звездах (целое число ≥ 1):")


@router.message(SellerFlow.adding_price)
async def seller_add_price(message: Message, state: FSMContext, services) -> None:
    raw = (message.text or "").strip()
    try:
        price = int(raw)
    except ValueError:
        await message.answer("Введите целое число ≥ 1.")
        return
    if price < 1:
        await message.answer("Цена должна быть ≥ 1.")
        return
    data = await state.get_data()
    try:
        product = await asyncio.to_thread(
            services.catalog.seller_create,
            seller_id=message.from_user.id,
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "other"),
            price_stars=price,
        )
    except Exception as exc:
        await message.answer(f"❌ Ошибка: {exc!s}")
        await state.clear()
        return
    await state.clear()
    await message.answer(
        f"✅ Товар #{product.id} создан. Теперь добавьте ключи (по одному в строке):",
    )
    await state.set_state(SellerFlow.adding_keys)
    await state.update_data(product_id=product.id)


@router.message(SellerFlow.adding_keys)
async def seller_add_keys(message: Message, state: FSMContext, services) -> None:
    data = await state.get_data()
    product_id = data.get("product_id")
    if product_id is None:
        await state.clear()
        return
    codes = [c.strip() for c in (message.text or "").splitlines() if c.strip()]
    if not codes:
        await message.answer("Нужно ≥ 1 строки с кодом. Попробуйте ещё раз или /cancel.")
        return
    added = await asyncio.to_thread(services.catalog.bulk_add_keys, product_id, codes)
    await state.clear()
    await message.answer(f"✅ Добавлено ключей: <b>{added}</b>.", reply_markup=seller_kb())
