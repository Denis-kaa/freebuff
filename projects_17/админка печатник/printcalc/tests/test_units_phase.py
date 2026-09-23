"""Тесты PHASE_UNITS (2026-09-21): единицы измерения + размерный ввод парсера.

Кейс владельца: «заказали 20 наклеек 20 на 30 — последние не нашло». До
PHASE_UNITS: (а) позиций-носителей наклеек в каталоге не было, (б) «20 на 30»
разбивалось перечислением («на» ∈ _ENUM_WORDS) — «20» съедалось тиражом,
«на 30» падало в unknown, (в) unit не доходил до order_items.

Закрытый словарь UNIT_CATALOG (ANTI-6b): normalize_unit либо канон, либо
StoreError — тихий фолбэк запрещён.
"""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import parser, store
from printcalc_web.store import StoreError


# ---------- normalize_unit: закрытый словарь ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("шт", "шт"),
        ("штука", "шт"),
        ("штук", "шт"),
        ("м²", "м²"),
        ("м2", "м²"),  # латиница/без надстрочного — частая опечатка Excel
        ("m2", "м²"),
        ("кв.м", "м²"),
        ("пог.м", "пог.м"),
        ("погонный метр", "пог.м"),
        ("п.м.", "пог.м"),
        ("пачка", "пачка"),
        ("комплект", "компл"),
        ("час", "час"),
    ],
)
def test_normalize_unit_canon_and_aliases(
    raw: str | None, expected: str | None
) -> None:
    assert store.normalize_unit(raw) == expected


def test_normalize_unit_unknown_is_loud() -> None:
    """Неизвестная единица → StoreError с перечнем допустимых (не молча)."""
    with pytest.raises(StoreError, match="сажень|ведро|неизвестная единица"):
        store.normalize_unit("ведро")


def test_normalize_unit_error_lists_allowed() -> None:
    with pytest.raises(StoreError) as excinfo:
        store.normalize_unit("ведро")
    assert "шт" in str(excinfo.value) and "м²" in str(excinfo.value)


def test_add_price_item_normalizes_and_validates(conn: sqlite3.Connection) -> None:
    created = store.add_price_item(conn, name="X", price=1.0, unit="штука")
    assert created["unit"] == "шт"
    with pytest.raises(StoreError):
        store.add_price_item(conn, name="Y", price=1.0, unit="сажень")


# ---------- парсер: размер ≠ тираж ----------


@pytest.fixture()
def seeded_conn(conn: sqlite3.Connection) -> sqlite3.Connection:
    store.seed_p0_services(conn)
    return conn


def test_parse_sticker_with_size(seeded_conn: sqlite3.Connection) -> None:
    """Кейс владельца: «наклейка 20 на 30» → позиция, qty=1, размер не мусор."""
    result = parser.parse(seeded_conn, "наклейка 20 на 30")
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["name"] == "Наклейка А4 (самоклейка)"
    assert item["qty"] == 1.0  # размер НЕ тираж
    assert item["unit"] == "шт"
    assert result["unknown"] == []  # «на» и «30» не потеряны
    assert result["sizes"] == ["20 на 30"]  # размер виден оператору


def test_parse_size_before_product(seeded_conn: sqlite3.Connection) -> None:
    """Порядок свободный: «20 на 30 наклейка» → та же позиция, qty=1."""
    result = parser.parse(seeded_conn, "20 на 30 наклейка")
    assert [i["name"] for i in result["items"]] == ["Наклейка А4 (самоклейка)"]
    assert result["items"][0]["qty"] == 1.0
    assert result["unknown"] == []


def test_parse_qty_with_qty_word(seeded_conn: sqlite3.Connection) -> None:
    """«наклейка А4 20 шт» → тираж 20 (слово-тираж квалифицирует число)."""
    result = parser.parse(seeded_conn, "наклейка А4 20 шт")
    assert result["items"][0]["qty"] == 20.0
    assert result["unknown"] == []


def test_parse_qty_word_alone_not_unknown(seeded_conn: sqlite3.Connection) -> None:
    """«баннер 440г, 2 штуки»: «штуки» поглощается, не поднимая эскалацию."""
    store.add_price_item(conn=seeded_conn, name="Баннер 440г", price=300.0)
    result = parser.parse(seeded_conn, "баннер 440г, 2 штуки")
    assert result["items"][0]["qty"] == 2.0
    assert "штуки" not in result["unknown"]


def test_parse_photo_size_alias(seeded_conn: sqlite3.Connection) -> None:
    """«фото 10 на 15» → «Фото 10×15» (размерный синоним, qty=1)."""
    result = parser.parse(seeded_conn, "фото 10 на 15")
    assert [i["name"] for i in result["items"]] == ["Фото 10×15"]
    assert result["items"][0]["qty"] == 1.0
    assert result["unknown"] == []


def test_parse_plain_qty_still_works(seeded_conn: sqlite3.Connection) -> None:
    """Регресс: «ксерокс 5 и фото 20» — тиражи после перечисления на месте."""
    result = parser.parse(seeded_conn, "ксерокс 5 и фото 20")
    assert [i["qty"] for i in result["items"]] == [5.0, 20.0]
    assert [i["segment_id"] for i in result["items"]] == [0, 1]


def test_parse_gluoed_size_not_qty(seeded_conn: sqlite3.Connection) -> None:
    """Склейка «20×30» — один токен: не тираж, не unknown, видна в sizes."""
    result = parser.parse(seeded_conn, "наклейка 20×30")
    assert result["items"][0]["qty"] == 1.0
    assert result["unknown"] == []
    assert result["sizes"] == ["20×30"]


# ---------- unit в заказе/смете ----------


def test_create_order_keeps_catalog_unit(conn: sqlite3.Connection) -> None:
    store.seed_p0_services(conn)
    item = next(
        i for i in store.list_price_items(conn) if i["name"] == "Наклейка А4 на м²"
    )
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 2.5}],
    )
    assert order["items"][0]["unit"] == "м²"
    assert order["items"][0]["qty"] == 2.5


def test_create_order_operator_unit_overrides_catalog(conn: sqlite3.Connection) -> None:
    """Явный выбор оператора сильнее каталога («шт» каталога → «м²»)."""
    store.seed_p0_services(conn)
    item = next(
        i for i in store.list_price_items(conn) if i["name"] == "Наклейка А4 (самоклейка)"
    )
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {
                "kind": "price_list",
                "price_list_item_id": item["id"],
                "qty": 1.0,
                "unit": "м2",  # алиас нормализуется
            }
        ],
    )
    assert order["items"][0]["unit"] == "м²"


def test_create_order_bad_unit_is_loud(conn: sqlite3.Connection) -> None:
    store.seed_p0_services(conn)
    item = next(i for i in store.list_price_items(conn) if i["name"] == "Листовка А4")
    with pytest.raises(StoreError, match="неизвестная единица"):
        store.create_order(
            conn,
            status="новый",
            payment_method="наличные",
            items=[
                {
                    "kind": "price_list",
                    "price_list_item_id": item["id"],
                    "qty": 1.0,
                    "unit": "сажень",
                }
            ],
        )


def test_create_order_manual_unit_saved(conn: sqlite3.Connection) -> None:
    """Ручная позиция: оператор выбирает единицу (кейс «цена вручную»)."""
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {
                "kind": "manual",
                "name": "Печать баннера вручную",
                "price": 350.0,
                "save_to_catalog": False,
                "unit": "м²",
            }
        ],
    )
    assert order["items"][0]["unit"] == "м²"


def test_manual_save_to_catalog_carries_unit(conn: sqlite3.Connection) -> None:
    """«Сохранить в прайс» из ручной позиции несёт единицу в каталог."""
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {
                "kind": "manual",
                "name": "Монтаж на клей",
                "price": 1200.0,
                "save_to_catalog": True,
                "unit": "час",
            }
        ],
    )
    assert order["items"][0]["unit"] == "час"
    catalog = next(
        i for i in store.list_price_items(conn) if i["name"] == "Монтаж на клей"
    )
    assert catalog["unit"] == "час"


def test_legacy_items_have_unit_none(conn: sqlite3.Connection) -> None:
    """Backward Compatibility: заказ без unit хранится, читается (NULL → «шт»)."""
    store.seed_p0_services(conn)
    item = next(i for i in store.list_price_items(conn) if i["name"] == "Листовка А4")
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 3.0}],
    )
    assert order["items"][0]["unit"] == "шт"  # из каталога, не NULL


def test_estimate_items_show_catalog_unit(conn: sqlite3.Connection) -> None:
    """Смета: единица видна в позициях (восстанавливается из каталога)."""
    store.seed_p0_services(conn)
    item = next(
        i for i in store.list_price_items(conn) if i["name"] == "Наклейка А4 на м²"
    )
    estimate = store.create_estimate(
        conn,
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 1.5}],
    )
    assert estimate["items"][0]["unit"] == "м²"
