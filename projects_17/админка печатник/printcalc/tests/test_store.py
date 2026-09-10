"""Тесты слоя данных printcalc_web (store): каталог, заказы, отчёт, настройки."""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import store


# ---------- прайс-каталог ----------


def test_add_price_item_defaults_unverified(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Ламинация А4", price=15.0)
    assert item["unverified"] is True  # идея №4: «на лету» = непроверено
    assert item["usage_count"] == 0
    assert item["synonyms"] == []


def test_add_price_item_rejects_empty_and_negative(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.add_price_item(conn, name="  ", price=1)
    with pytest.raises(store.StoreError):
        store.add_price_item(conn, name="X", price=-1)


def test_find_similar_substring(conn: sqlite3.Connection) -> None:
    store.add_price_item(conn, name="Ламинация А4", price=15.0)
    similar = store.find_similar(conn, "ламинация")
    assert len(similar) == 1
    assert similar[0]["name"] == "Ламинация А4"


def test_add_synonym_idempotent(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Ламинация А3", price=15.0)
    store.add_synonym(conn, item["id"], "ламинация")
    store.add_synonym(conn, item["id"], "ламинация")
    updated = store.get_price_item(conn, item["id"])
    assert updated["synonyms"] == ["ламинация"]  # идея №5: без дублей


def test_import_price_items(conn: sqlite3.Connection) -> None:
    result = store.import_price_items(
        conn, "Копия ч/б - 5\nФото на документы — 200\nЛаминация А4\t15\nмусор без цены"
    )
    assert result["created"] == 3
    assert len(result["skipped"]) == 1
    names = [item["name"] for item in store.list_price_items(conn)]
    assert "Копия ч/б" in names and "Фото на документы" in names


def test_usage_count_grows_on_order_save(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Копия ч/б", price=5.0)
    store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 3}],
    )
    updated = store.get_price_item(conn, item["id"])
    assert updated["usage_count"] == 1  # идея №3: счётчик растёт при сохранении заказа


# ---------- заказы ----------


def test_create_order_with_price_and_manual_items(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Печать документа", price=10.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="карта",
        items=[
            {"kind": "price_list", "price_list_item_id": item["id"], "qty": 10},
            {"kind": "manual", "name": "Срочность", "price": 100.0, "save_to_catalog": False},
        ],
    )
    assert order["total"] == pytest.approx(200.0)  # 10×10 + 100
    kinds = {entry["kind"] for entry in order["items"]}
    assert kinds == {"price_list", "manual"}


def test_manual_saved_to_catalog_becomes_price_item(conn: sqlite3.Connection) -> None:
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "manual", "name": "Скрепление", "price": 20.0, "save_to_catalog": True}],
    )
    assert order["items"][0]["kind"] == "price_list"
    assert order["items"][0]["price_list_item_id"] is not None


def test_calculator_item_price_from_engine(conn: sqlite3.Connection) -> None:
    """Цена расчётной позиции берётся с сервера (движок), не от клиента.

    Позиции заказа хранят деньги с точностью копейки (round 2) —
    поэтому ожидание 485.37, а не сырые 485.3723... из golden-теста.
    """
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {
                "kind": "calculator",
                "calculator_id": "riso",
                "params": {"format": "A4", "qty": 1000, "originals": 1, "color": "ч/б",
                           "paper": "Офсетная 80 г/м²", "markup_percent": 25.0},
            }
        ],
    )
    assert order["items"][0]["price"] == pytest.approx(485.37)
    assert order["total"] == pytest.approx(485.37)


def test_order_status_closed_vocabulary(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.create_order(conn, status="принят", payment_method="наличные",
                           items=[{"kind": "manual", "name": "X", "price": 1}])


def test_order_status_transitions(conn: sqlite3.Connection) -> None:
    order = store.create_order(
        conn, status="новый", payment_method="наличные",
        items=[{"kind": "manual", "name": "X", "price": 5}],
    )
    for status in ("в работе", "выполнен", "завершён"):
        updated = store.update_order(conn, order["id"], status=status)
        assert updated["status"] == status


def test_payment_method_validation(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.create_order(conn, status="новый", payment_method="бартер",
                           items=[{"kind": "manual", "name": "X", "price": 1}])
    store.set_payment_methods(conn, ["наличные", "карта", "перевод", "QR"])
    order = store.create_order(conn, status="новый", payment_method="QR",
                               items=[{"kind": "manual", "name": "X", "price": 1}])
    assert order["payment_method"] == "QR"


def test_list_orders_filter_by_status(conn: sqlite3.Connection) -> None:
    store.create_order(conn, status="новый", payment_method="наличные",
                       items=[{"kind": "manual", "name": "A", "price": 1}])
    created = store.create_order(conn, status="в работе", payment_method="наличные",
                                 items=[{"kind": "manual", "name": "B", "price": 2}])
    store.update_order(conn, created["id"], status="завершён")
    statuses = {order["status"] for order in store.list_orders(conn, status="завершён")}
    assert statuses == {"завершён"}


def test_off_catalog_report(conn: sqlite3.Connection) -> None:
    store.create_order(
        conn, status="новый", payment_method="наличные",
        items=[
            {"kind": "manual", "name": "Забыл сохранить", "price": 50, "save_to_catalog": False},
            {"kind": "manual", "name": "Сохранил", "price": 30, "save_to_catalog": True},
        ],
    )
    report = store.off_catalog_report(conn)
    assert len(report) == 1  # идея №10: только несохранённые
    assert report[0]["name"] == "Забыл сохранить"


# ---------- мультизаказ (парсер v2, segment_id) ----------


def test_order_items_keep_segment_id(conn: sqlite3.Connection) -> None:
    """Сегменты перечисления сохраняются: «ксерокс 5 и фото 20» → 2 группы."""
    a = store.add_price_item(conn, name="Ксерокопия ч/б А4", price=15.0)
    b = store.add_price_item(conn, name="Фото 10×15", price=25.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {"kind": "price_list", "price_list_item_id": a["id"], "qty": 5, "segment_id": 0},
            {"kind": "price_list", "price_list_item_id": b["id"], "qty": 20, "segment_id": 1},
        ],
    )
    segments = [item["segment_id"] for item in order["items"]]
    assert segments == [0, 1]


def test_order_items_without_segment_are_null(conn: sqlite3.Connection) -> None:
    """Позиции из прайса/расчёта без сегмента — NULL (обратная совместимость)."""
    item = store.add_price_item(conn, name="Скан", price=20.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 1}],
    )
    assert order["items"][0]["segment_id"] is None


def test_segment_id_out_of_range_is_dropped(conn: sqlite3.Connection) -> None:
    """Мусорный сегмент не сохраняется (guard в _segment_of)."""
    item = store.add_price_item(conn, name="Копия", price=15.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[
            {"kind": "price_list", "price_list_item_id": item["id"], "qty": 1, "segment_id": 5000}
        ],
    )
    assert order["items"][0]["segment_id"] is None
