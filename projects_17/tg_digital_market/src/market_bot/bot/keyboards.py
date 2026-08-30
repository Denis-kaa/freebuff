"""keyboards.py — фабрики клавиатур и CallbackData.

CallbackData — компактный тип-маркер для inline-кнопок. Удобен для диспетчинга
без if-elif цепочек в хэндлерах.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# ─── CallbackData ───────────────────────────────────────────────────────────


class MenuAction(CallbackData, prefix="menu"):
    action: str  # "catalog" | "account" | "history" | "seller" | "admin"
    page: int = 0


class CatalogAction(CallbackData, prefix="cat"):
    action: str     # "category" | "list" | "open" | "back"
    category: str = ""
    product_id: int = 0
    page: int = 0


class CartAction(CallbackData, prefix="cart"):
    action: str          # "buy" | "confirm" | "cancel" | "pay_mock"
    product_id: int = 0
    order_id: int = 0
    payment_id: int = 0


class AdminAction(CallbackData, prefix="adm"):
    action: str           # "stats" | "set_role" | "activate" | "deactivate"
    user_id: int = 0
    product_id: int = 0
    role: str = ""


class SellerAction(CallbackData, prefix="sell"):
    action: str           # "my" | "add" | "edit" | "add_keys"
    product_id: int = 0


# ─── Reply-клавиатуры ───────────────────────────────────────────────────────

MAIN_MENU_BTNS = [
    [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="👤 Кабинет")],
    [KeyboardButton(text="📜 История"), KeyboardButton(text="ℹ️ Помощь")],
]


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=MAIN_MENU_BTNS, resize_keyboard=True, one_time_keyboard=False
    )


# ─── Inline-клавиатуры ──────────────────────────────────────────────────────


def catalog_root_kb(categories: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📁 {c}", callback_data=CatalogAction(action="list", category=c, page=0).pack())]
        for c in categories
    ] or [[InlineKeyboardButton(text="Пусто", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_list_kb(products, category: str, page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    rows = []
    for p in products[page * page_size:(page + 1) * page_size]:
        rows.append([
            InlineKeyboardButton(
                text=f"{p.name} · ⭐{p.price_stars}",
                callback_data=CatalogAction(action="open", product_id=p.id).pack(),
            )
        ])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀", callback_data=CatalogAction(action="list", category=category, page=page - 1).pack()
        ))
    if (page + 1) * page_size < len(products):
        nav.append(InlineKeyboardButton(
            text="▶", callback_data=CatalogAction(action="list", category=category, page=page + 1).pack()
        ))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(
        text="⬅️ К категориям",
        callback_data=CatalogAction(action="category").pack(),
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_kb(product_id: int, in_stock: bool) -> InlineKeyboardMarkup:
    rows = []
    if in_stock:
        rows.append([InlineKeyboardButton(
            text="💳 Купить",
            callback_data=CartAction(action="confirm", product_id=product_id).pack(),
        )])
    else:
        rows.append([InlineKeyboardButton(text="⛔ Нет в наличии", callback_data="noop")])
    rows.append([InlineKeyboardButton(
        text="⬅️ К списку",
        callback_data=CatalogAction(action="back").pack(),
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_purchase_kb(product_id: int, order_id: int, payment_id: int, is_mock: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text="✅ Подтверждаю",
            callback_data=CartAction(action="pay_mock", order_id=order_id, payment_id=payment_id).pack(),
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=CartAction(action="cancel", order_id=order_id).pack(),
        )],
    ] if is_mock else [
        # Для Telegram Stars inline-кнопка "Оплатить" появится в reply-сообщении с invoice.
        [InlineKeyboardButton(
            text="❌ Отменить заказ",
            callback_data=CartAction(action="cancel", order_id=order_id).pack(),
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_kb(is_seller: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="📜 История заказов", callback_data=MenuAction(action="history").pack())]]
    if is_seller:
        rows.append([InlineKeyboardButton(text="🏪 Кабинет продавца", callback_data=MenuAction(action="seller").pack())])
    if is_admin:
        rows.append([InlineKeyboardButton(text="🛠 Админ-панель", callback_data=MenuAction(action="admin").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_kb() -> InlineKeyboardMarkup:
    """Админ-панель: только кнопка статистики (валидный callback).

    Динамическое перечисление товаров делается через message handler
    /admin_products (см. admin.py) — не пытаемся закодировать сложный
    список в callback_data (фикс ревью #2 против «слёжки» строк).
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data=AdminAction(action="stats").pack())],
    ])


def seller_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data=SellerAction(action="add").pack())],
    ])
