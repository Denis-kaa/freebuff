"""Тесты Этапа 3 (роадмап v6): расход материала → API → заказы.

Правило владельца (2026-09-09): изделие, не влезающее в рулон по ширине,
разворачивается (ширина↔высота) и считается повёрнутым; ошибка — только
если не влезает ни так, ни эдак. Ручная ширина загруженного рулона
(roll_width_mm) перекрывает реестр — оператор знает фактический рулон.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "api_consumption.db"))


def _banner_id(client: ASGITestClient, name: str = "Баннер 440г") -> int:
    materials = client.get("/api/materials").json()["materials"]
    return next(m["id"] for m in materials if m["name"] == name)


# ---------- POST /api/consumption/calculate ----------


def test_consumption_calculate_roll_nesting(client: ASGITestClient) -> None:
    """Баннер 3×1 ×2 на рулоне 1 м: изделие разворачивается, расход = 6 м²."""
    res = client.post(
        "/api/consumption/calculate",
        json={"material_id": _banner_id(client), "width_cm": 300, "height_cm": 100, "quantity": 2},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["product_area_m2"] == pytest.approx(6.0)
    assert body["production_area_m2"] == pytest.approx(6.0)
    assert body["waste_percent"] == pytest.approx(0.0)
    assert body["orientation"] == "1000x3000"  # поворот применился
    assert any("повёрнутым" in w for w in body["warnings"])
    assert body["calculation_trace"]  # трассировка присутствует (§9 ТЗ промт_3)


def test_manual_roll_width_overrides_registry(client: ASGITestClient) -> None:
    """Ручной рулон 3 м (новый плоттер): 2 ряда × 1 м, те же 6 м², ориентация прямая."""
    res = client.post(
        "/api/consumption/calculate",
        json={
            "material_id": _banner_id(client),
            "width_cm": 300,
            "height_cm": 100,
            "quantity": 2,
            "roll_width_mm": 3000,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["orientation"] == "3000x1000"  # влезает прямо — поворот не нужен
    assert body["production_area_m2"] == pytest.approx(6.0)


def test_manual_roll_width_narrower(client: ASGITestClient) -> None:
    """Рулон 1.2 м: 1000 мм влезает прямо, 3000 нет → раскладка 1000×3000, 7.2 м²."""
    res = client.post(
        "/api/consumption/calculate",
        json={
            "material_id": _banner_id(client),
            "width_cm": 300,
            "height_cm": 100,
            "quantity": 2,
            "roll_width_mm": 1200,
        },
    )
    body = res.json()
    assert body["orientation"] == "1000x3000"
    assert body["production_area_m2"] == pytest.approx(7.2)  # 1.2 м × 6 м
    assert body["waste_percent"] > 0


def test_consumption_does_not_fit_either_way(client: ASGITestClient) -> None:
    """320×260 на рулон 1 м: ни прямо, ни поворотом — честная ошибка."""
    res = client.post(
        "/api/consumption/calculate",
        json={"material_id": _banner_id(client), "width_cm": 320, "height_cm": 260, "quantity": 1},
    )
    assert res.status_code == 400
    assert "PRODUCT_DOES_NOT_FIT" in res.json()["detail"]


def test_consumption_unknown_material(client: ASGITestClient) -> None:
    res = client.post(
        "/api/consumption/calculate",
        json={"material_id": 99999, "width_cm": 100, "height_cm": 100, "quantity": 1},
    )
    assert res.status_code == 400


# ---------- расход в заказе ----------


_WIDE_PARAMS = {
    "width": 300,
    "height": 100,
    "qty": 2,
    "material": "Баннер 440",
    "print": "Обычная печать",
    "mount": "Без монтажа",
    "delivery": False,
    "install": False,
}


def test_order_calculator_item_gets_consumption(client: ASGITestClient) -> None:
    """wide-позиция заказа автоматически получает snapshot расхода (§49 дух)."""
    order = client.post(
        "/api/orders",
        json={"status": "новый", "payment_method": "карта",
              "items": [{"kind": "calculator", "calculator_id": "wide", "params": dict(_WIDE_PARAMS)}]},
    ).json()
    consumption = order["items"][0]["consumption"]
    assert consumption is not None
    assert consumption["product_area_m2"] == pytest.approx(6.0)
    assert consumption["orientation"] == "1000x3000"


def test_order_calculator_item_without_material_has_no_consumption(client: ASGITestClient) -> None:
    """Неизвестное имя материала — расход не блокирует заказ (цена уже посчитана)."""
    order = client.post(
        "/api/orders",
        json={"status": "новый", "payment_method": "карта",
              "items": [{"kind": "calculator", "calculator_id": "wide",
                         "params": {**_WIDE_PARAMS, "material": "Несуществующий"}}]},
    ).json()
    assert order["items"][0]["consumption"] is None


def test_order_price_is_calculator_price(client: ASGITestClient) -> None:
    """Цена позиции — от калькулятора; расход цену не меняет (разделение движков §33)."""
    order = client.post(
        "/api/orders",
        json={"status": "новый", "payment_method": "карта",
              "items": [{"kind": "calculator", "calculator_id": "wide", "params": dict(_WIDE_PARAMS)}]},
    ).json()
    assert order["total"] == pytest.approx(1500.0)  # golden: паритет legacy
