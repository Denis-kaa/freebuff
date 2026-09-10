"""Тесты кассовых услуг P0: сид, прайс-шаблон round-trip, парсер-синонимы."""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import parser, store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "p0.db")
    store.seed_sections(connection)
    yield connection
    connection.close()


# ---------- сид P0 ----------


def test_seed_creates_sections_and_synonyms(conn: sqlite3.Connection) -> None:
    result = store.seed_p0_services(conn)
    assert result["created"] > 0
    assert result["skipped"] == 0

    items = {item["name"]: item for item in store.list_price_items(conn)}
    assert "Ксерокопия ч/б А4" in items
    assert items["Ксерокопия ч/б А4"]["category"] == "1. КОПИРОВАНИЕ"
    assert items["Ксерокопия ч/б А4"]["price"] == pytest.approx(15.0)
    assert items["Ксерокопия ч/б А4"]["unverified"] is False
    assert "ксерокс" in items["Ксерокопия ч/б А4"]["synonyms"]
    assert "Фото 10×15" in items  # кавычка-× из реальных формулировок


def test_seed_is_idempotent(conn: sqlite3.Connection) -> None:
    first = store.seed_p0_services(conn)
    second = store.seed_p0_services(conn)
    assert first["created"] > 0
    assert second == {"created": 0, "skipped": first["created"]}
    assert len(store.list_price_items(conn)) == first["created"]


def test_seed_does_not_overwrite_edited_price(conn: sqlite3.Connection) -> None:
    """Владелец поправил цену до сида → сид не трогает её, но досыпает синонимы."""
    item = store.add_price_item(conn, name="Ксерокопия ч/б А4", price=25.0)
    store.update_price_item(conn, item["id"], {"unverified": True})

    store.seed_p0_services(conn)

    assert store.get_price_item(conn, item["id"])["price"] == pytest.approx(25.0)
    # Синонимы из сида добавлены даже к существующей позиции.
    assert "ксерокс" in store.get_price_item(conn, item["id"])["synonyms"]


# ---------- прайс-шаблон round-trip ----------


def test_template_csv_has_sections_and_roundtrip(conn: sqlite3.Connection) -> None:
    store.seed_p0_services(conn)

    template = store.price_template_csv(conn)
    assert "# 1. КОПИРОВАНИЕ" in template
    assert "Название;Цена;Ед;Синонимы" in template
    # Цена «15.0» сериализуется без хвостовых нулей.
    assert "Ксерокопия ч/б А4;15;" in template
    assert "ксерокс" in template

    # Round-trip: меняем цену и добавляем новую позицию.
    edited = template.replace("Ксерокопия ч/б А4;15;", "Ксерокопия ч/б А4;20;")
    edited += "Бейдж;5;шт;бейджик\n"
    result = store.import_price_template(conn, edited)

    assert result["updated"] >= 1
    assert result["created"] == 1
    items = {item["name"]: item for item in store.list_price_items(conn)}
    assert items["Ксерокопия ч/б А4"]["price"] == pytest.approx(20.0)
    assert items["Бейдж"]["price"] == pytest.approx(5.0)
    assert items["Бейдж"]["synonyms"] == ["бейджик"]


def test_template_import_ignores_comments_and_header(conn: sqlite3.Connection) -> None:
    text = (
        "# комментарий\n"
        "Название;Цена;Ед;Синонимы\n"
        "Ламинация документа;80;шт;ламинация\n"
    )
    result = store.import_price_template(conn, text)
    assert result == {"created": 1, "updated": 0, "skipped": []}
    assert store.get_price_item(conn, 1)["price"] == pytest.approx(80.0)


def test_template_import_bad_lines_skipped(conn: sqlite3.Connection) -> None:
    result = store.import_price_template(conn, "мусор без разделителя\nЕщё;не число\n")
    assert result["created"] == 0 and result["updated"] == 0


# ---------- парсер находит P0 по синонимам ----------


def test_parser_matches_p0_synonyms(conn: sqlite3.Connection) -> None:
    store.seed_p0_services(conn)

    parsed = parser.parse(conn, "нужно 2 ксерокса")
    assert parsed["items"] == [
        {
            "type": "price",
            "price_list_item_id": 1,
            "name": "Ксерокопия ч/б А4",
            "price": 15.0,
            "qty": 2.0,
            "segment_id": 0,
        }
    ]

    parsed = parser.parse(conn, "фото на паспорт и заламинировать")
    names = [item["name"] for item in parsed["items"]]
    assert "Фото на документы (4 шт)" in names
    assert "Ламинация документа" in names


def test_parser_r10_needs_operator(conn: sqlite3.Connection) -> None:
    """R10 (RESEARCH_ADOPTION_PLAN §5-Б.3): reasons — НЕ молча."""
    store.seed_p0_services(conn)

    # unknown-токены → нужно оператору
    parsed = parser.parse(conn, "ксерокс и что-то непонятное штрих")
    assert parsed["needs_operator"] is True
    assert any("не распознано" in r for r in parsed["reasons"])

    # чистый запрос → оператор не нужен
    parsed = parser.parse(conn, "ксерокс 5")
    assert parsed["needs_operator"] is False
    assert parsed["reasons"] == []

    # упомянут файл/макет → приём файлов пока ручной
    parsed = parser.parse(conn, "ксерокс, макет прикрепил")
    assert parsed["needs_operator"] is True
    assert any("файл" in r for r in parsed["reasons"])


def test_calculator_hints_r5() -> None:
    """R5 (RESEARCH_ADOPTION_PLAN §5-Б.2): min_order из конфига в спеке."""
    from printcalc_web.calculators import list_calculators

    specs = {spec["id"]: spec for spec in list_calculators()}
    assert specs["digital"]["hints"] == ["Минимальная сумма заказа: 500 ₽"]
    assert specs["riso"]["hints"] == ["Минимальный тираж: 500 шт"]
    # калькуляторы без порога — пусто, не выдумываем
    assert specs["wide"]["hints"] == []
