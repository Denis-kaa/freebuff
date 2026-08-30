"""catalog.py — категории и карточки товаров.

CallbackData parsing → формирование списка товаров / детальной карточки.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, List

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..keyboards import (
    CatalogAction,
    catalog_root_kb,
    product_detail_kb,
    products_list_kb,
)

router = Router(name="catalog")


def _render_categories(categories: Iterable[str]):
    return catalog_root_kb(list(categories))


@router.callback_query(CatalogAction.filter(F.action == "category"))
async def cb_categories(call: CallbackQuery, services) -> None:
    categories = await asyncio.to_thread(services.catalog.list_categories)
    if not categories:
        await call.message.edit_text(
            "📭 Категорий пока нет. Зайдите позже.",
            reply_markup=catalog_root_kb([]),
        )
        await call.answer()
        return
    await call.message.edit_text("📂 Выберите категорию:", reply_markup=categories and _render_categories(categories))
    await call.answer()


@router.callback_query(CatalogAction.filter(F.action == "list"))
async def cb_category(call: CallbackQuery, callback_data: CatalogAction, services) -> None:
    category = callback_data.category
    page = callback_data.page
    products = await asyncio.to_thread(services.catalog.list_active, category)
    if not products:
        await call.message.edit_text(
            f"В категории «{category}» пока пусто.",
            reply_markup=catalog_root_kb(await asyncio.to_thread(services.catalog.list_categories)),
        )
        await call.answer()
        return
    title = f"📁 {category} — {len(products)} шт."
    await call.message.edit_text(
        title, reply_markup=products_list_kb(products, category=category, page=page)
    )
    await call.answer()


@router.callback_query(CatalogAction.filter(F.action == "open"))
async def cb_product(call: CallbackQuery, callback_data: CatalogAction, services) -> None:
    product = await asyncio.to_thread(services.catalog.get, callback_data.product_id)
    if product is None or not product.is_active:
        await call.answer("⛔ Товар недоступен.", show_alert=True)
        return
    stock = await asyncio.to_thread(services.catalog.available_stock, product.id)
    text = (
        f"<b>{product.name}</b>\n\n"
        f"{product.description or '—'}\n\n"
        f"📂 Категория: {product.category}\n"
        f"💰 Цена: ⭐{product.price_stars}\n"
        f"📦 В наличии: {stock} шт."
    )
    await call.message.edit_text(text, reply_markup=product_detail_kb(product.id, in_stock=stock > 0))
    await call.answer()


@router.callback_query(CatalogAction.filter(F.action == "back"))
async def cb_back(call: CallbackQuery, services) -> None:
    categories = await asyncio.to_thread(services.catalog.list_categories)
    await call.message.edit_text("📂 Категории:", reply_markup=categories and _render_categories(categories))
    await call.answer()
