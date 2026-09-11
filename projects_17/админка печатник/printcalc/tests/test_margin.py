"""Тесты сшивки Себестоимость ↔ прайс (margin): маршруты, gaps, материалы."""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import margin, store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "margin.db")
    store.seed_p0_services(connection)
    store.seed_materials(connection)
    yield connection
    connection.close()


# ---------- маршруты услуг ----------


def test_report_seeded_catalog(conn: sqlite3.Connection) -> None:
    """Каталог P0 (20 позиций): все либо с маршрутом, либо gap с причиной."""
    report = margin.margin_report(conn)
    total = report["summary"]["routed"] + report["summary"]["gaps"]
    assert total == 20
    for gap in report["service_gaps"]:
        assert gap["reason"], "gap без причины — «молча», запрещено"


def test_riso_batch_divides_master_cost(conn: sqlite3.Connection) -> None:
    """Себестоимость единицы Riso = партия 500 (мастер на задачу)."""
    item = next(i for i in store.list_price_items(conn) if i["name"] == "Ксерокопия ч/б А4")
    row = margin.margin_for_service(item)
    assert row["batch_qty"] == margin.RISO_BATCH_QTY
    # прайс 15 ₽/шт, себестоимость на партии 500 — маржа положительная
    assert row["cost_unit"] < row["price"]
    assert row["margin_pct"] is not None and row["margin_pct"] > 0


def test_banner_m2_route(conn: sqlite3.Connection) -> None:
    """Баннер: m2-база, партия 1, паритет с golden-тестом cost (2142.24·0.77)."""
    item = next(i for i in store.list_price_items(conn) if i["name"] == "Баннер (за м²)")
    row = margin.margin_for_service(item)
    assert row["batch_qty"] == 1.0
    assert row["below_markup"] is False  # прайс 300 > цена с наценкой 30% ≈ 214
    assert row["margin_pct"] is not None and 40 < row["margin_pct"] < 50


def test_known_golden_costs(conn: sqlite3.Connection) -> None:
    """Себестоимости единиц совпадают с движком (защита от дрейфа карты)."""
    for name, expected in (
        ("Цветная копия А4", 13.19),  # Xerox A4 лист
        ("Ламинация документа", 7.62),  # А4, плёнка 32 мкм
    ):
        item = next(i for i in store.list_price_items(conn) if i["name"] == name)
        row = margin.margin_for_service(item)
        assert row["cost_unit"] == pytest.approx(expected, abs=0.01), name


# ---------- материалы ----------


def test_material_word_matching(conn: sqlite3.Connection) -> None:
    """Сопоставление по словам: «Баннер 440г» ↔ «Баннер (обычный)» нет, алиасы есть."""
    report = margin.margin_report(conn)
    names = {m["name"] for m in report["materials"]}
    # Баннер 440г имеет алиас «Баннер (обычный)» — точное слово-совпадение
    assert "Баннер 440г" in names


def test_material_needs_fill_flag(conn: sqlite3.Connection) -> None:
    """Закупочная цена 0 → needs_fill (владельцу видно, что заполнить)."""
    material = {"id": 1, "name": "Холст", "aliases": ["Холст печатный"], "purchase_cost": 0.0}
    row = margin.material_margin(material)
    assert row is not None
    assert row["needs_fill"] is True
    assert row["config_cost_unit"] > 0


def test_unknown_material_is_gap(conn: sqlite3.Connection) -> None:
    material = {"id": 99, "name": "Нечто неизвестное", "aliases": [], "purchase_cost": 10.0}
    assert margin.material_margin(material) is None


# ---------- API ----------


def test_api_margin_report(tmp_path) -> None:
    """API-контракт отчёта (ASGI-клиент — httpx 0.28 несовместим с TestClient)."""
    import sys
    from pathlib import Path

    from printcalc_web import create_app

    sys.path.insert(0, str(Path(__file__).parent))
    from asgi_client import ASGITestClient

    client = ASGITestClient(create_app(db_path=tmp_path / "api_margin.db"))
    response = client.get("/api/margin/report")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"services", "service_gaps", "materials", "material_gaps", "summary"}
    # сид P0 выполняется на старте — маршруты обязаны найтись
    assert payload["summary"]["routed"] >= 8
    assert payload["summary"]["gaps"] >= 10
