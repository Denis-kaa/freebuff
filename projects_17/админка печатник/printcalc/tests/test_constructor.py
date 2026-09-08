"""Тесты конструктора разделов и пожеланий заказчика (2026-09-08)."""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "ctor.db")
    store.seed_sections(connection)
    yield connection
    connection.close()


# ---------- конструктор разделов ----------


def test_seed_sections_idempotent_with_wishes_default(conn: sqlite3.Connection) -> None:
    first = store.list_sections(conn)
    assert [s["title"] for s in first] == ["Пожелания заказчика", "Срочность", "Доставка"]
    wishes = first[0]
    assert wishes["kind"] == "textarea"  # свободная форма
    assert wishes["required"] is False
    store.seed_sections(conn)  # повторный вызов ничего не добавляет
    assert len(store.list_sections(conn)) == 3


def test_add_section_kinds_and_validation(conn: sqlite3.Connection) -> None:
    section = store.add_section(conn, title="Номер машины", kind="text")
    assert section["kind"] == "text" and section["required"] is False

    select = store.add_section(
        conn, title="Цвет", kind="select", options=["красный", "синий"]
    )
    assert select["options"] == ["красный", "синий"]

    with pytest.raises(store.StoreError):
        store.add_section(conn, title="  ", kind="text")
    with pytest.raises(store.StoreError):
        store.add_section(conn, title="X", kind="dropdown")  # вне закрытого словаря
    with pytest.raises(store.StoreError):
        store.add_section(conn, title="X", kind="select", options=[" ", ""])


def test_update_and_archive_section(conn: sqlite3.Connection) -> None:
    section = store.add_section(conn, title="Макет", kind="checkbox")
    updated = store.update_section(
        conn, section["id"], title="Макет готов", required=True
    )
    assert updated["title"] == "Макет готов" and updated["required"] is True

    archived = store.update_section(conn, section["id"], archived=True)
    assert archived["archived"] is True
    assert all(s["id"] != section["id"] for s in store.list_sections(conn))
    restored = store.update_section(conn, section["id"], archived=False)
    assert restored["archived"] is False


def test_reorder_sections_full_list_required(conn: sqlite3.Connection) -> None:
    ids = [s["id"] for s in store.list_sections(conn)]
    reordered = store.reorder_sections(conn, list(reversed(ids)))
    assert [s["id"] for s in reordered] == list(reversed(ids))
    with pytest.raises(store.StoreError):
        store.reorder_sections(conn, ids[:2])  # не все активные id


def test_order_wishes_free_form_and_sections(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Баннер", price=300.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 2}],
        wishes="Точно к пятнице, края укрепить",
        section_values={"2": "к завтрашнему дню", "3": "доставка"},
    )
    assert order["wishes"] == "Точно к пятнице, края укрепить"
    values = {s["section_id"]: s["value"] for s in store.get_order_sections(conn, order["id"])}
    assert values[2] == "к завтрашнему дню"  # Срочность
    assert values[3] == "доставка"  # Доставка
    assert values[1] == ""  # Пожелания — незаполненный раздел → пусто, не None


def test_required_section_enforced_and_unknown_rejected(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Печать", price=10.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"]}],
    )
    required = store.add_section(conn, title="Контакт", kind="text", required=True)
    with pytest.raises(store.StoreError, match="обязателен"):
        store.set_order_sections(conn, order["id"], {str(required["id"]): ""})
    with pytest.raises(store.StoreError, match="неизвестный раздел"):
        store.set_order_sections(conn, order["id"], {"999": "x"})
    select_section = store.add_section(conn, title="Сложность", kind="select", options=["низкая"])
    with pytest.raises(store.StoreError, match="не входит в варианты"):
        store.set_order_sections(conn, order["id"], {str(select_section["id"]): "высокая"})


def test_update_order_wishes_only(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Копия", price=5.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="карта",
        items=[{"kind": "price_list", "price_list_item_id": item["id"]}],
        wishes="черновик",
    )
    updated = store.update_order(conn, order["id"], wishes="финальный текст пожеланий")
    assert updated["wishes"] == "финальный текст пожеланий"
    # wishes="" — легальная очистка (не None).
    cleared = store.update_order(conn, order["id"], wishes="  ")
    assert cleared["wishes"] == ""


def test_export_text_contains_wishes_and_sections(conn: sqlite3.Connection) -> None:
    from printcalc_web import export

    item = store.add_price_item(conn, name="Визитки", price=3.0)
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 500}],
        wishes="Логотип на обороте",
        section_values={"2": "срочно"},
    )
    text = export.order_to_text(order, store.get_order_sections(conn, order["id"]))
    assert "Пожелания заказчика:" in text and "Логотип на обороте" in text
    assert "Срочность: срочно" in text
