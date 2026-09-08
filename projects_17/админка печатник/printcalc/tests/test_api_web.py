"""Интеграционные тесты FastAPI printcalc_web (ASGI-клиент + изолированная БД).

Примечание: среда имеет starlette 0.27 + httpx 0.28, где штатный
fastapi.testclient.TestClient падает (kwarg `app=` удалён в httpx 0.28).
Используем собственный минимальный ASGI-клиент (tests/asgi_client.py) —
без сокетов и зависимости от версий starlette/httpx.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "api.db"))


def test_price_item_crud_and_similar(client: ASGITestClient) -> None:
    created = client.post(
        "/api/price-list", json={"name": "Ламинация А4", "price": 15.0}
    ).json()
    assert created["unverified"] is True

    similar = client.get("/api/price-list/similar", params={"q": "ламинация"}).json()
    assert similar["items"][0]["id"] == created["id"]

    patched = client.patch(
        f"/api/price-list/{created['id']}", json={"unverified": False, "category": "пост-обработка"}
    ).json()
    assert patched["unverified"] is False

    listed = client.get("/api/price-list", params={"unverified": True}).json()
    assert listed["items"] == []


def test_price_list_import_and_csv_export(client: ASGITestClient) -> None:
    result = client.post(
        "/api/price-list/import", json={"text": "Копия ч/б - 5\nФото на документы — 200"}
    ).json()
    assert result["created"] == 2

    response = client.get("/api/price-list/export.csv")
    assert response.status_code == 200
    assert "Копия ч/б" in response.text and "200.0" in response.text
    assert "attachment" in response.headers["content-disposition"]


def test_calculate_endpoint_golden(client: ASGITestClient) -> None:
    response = client.post(
        "/api/calculate",
        json={
            "calculator_id": "riso",
            "params": {"format": "A4", "qty": 1000, "originals": 1, "color": "ч/б",
                       "paper": "Офсетная 80 г/м²", "markup_percent": 25.0},
        },
    )
    assert response.status_code == 200
    assert response.json()["price"] == pytest.approx(485.37234042553195)


def test_calculate_endpoint_validation_error(client: ASGITestClient) -> None:
    response = client.post(
        "/api/calculate",
        json={"calculator_id": "riso", "params": {"format": "A4", "qty": 0, "originals": 1,
                                                  "color": "ч/б", "paper": "Офсетная 80 г/м²"}},
    )
    assert response.status_code == 400
    assert "qty" in str(response.json()["detail"])


def test_calculators_endpoint_lists_riso(client: ASGITestClient) -> None:
    data = client.get("/api/calculators").json()
    ids = [spec["id"] for spec in data["calculators"]]
    assert ids == ["riso"]
    fields = {field["name"]: field for field in data["calculators"][0]["fields"]}
    assert set(fields["format"]["options"]) == {"A4", "A5", "A6", "A3"}


def test_order_flow_end_to_end(client: ASGITestClient) -> None:
    """Р5б целиком: прайс-позиция + ручная + калькулятор → заказ → статус → экспорт."""
    price_item = client.post("/api/price-list", json={"name": "Печать документа", "price": 10.0}).json()
    order = client.post(
        "/api/orders",
        json={
            "status": "новый",
            "payment_method": "наличные",
            "items": [
                {"kind": "price_list", "price_list_item_id": price_item["id"], "qty": 10},
                {"kind": "manual", "name": "Фото на документы", "price": 200.0, "save_to_catalog": True},
            ],
        },
    ).json()
    assert order["total"] == pytest.approx(300.0)
    assert order["items"][1]["kind"] == "price_list"  # идея №2: ручная → каталог

    # Смена статуса по Р2.
    updated = client.patch(f"/api/orders/{order['id']}", json={"status": "в работе"}).json()
    assert updated["status"] == "в работе"

    # Фильтр списка заказов.
    filtered = client.get("/api/orders", params={"status": "в работе"}).json()
    assert [o["id"] for o in filtered["orders"]] == [order["id"]]

    # OrderExport (Р1): текст для ручного переноса в WF.
    export_response = client.get(f"/api/orders/{order['id']}/export.txt")
    text = export_response.text
    assert "Печать документа × 10" in text
    assert "Фото на документы" in text
    assert "Итого: 300.00" in text


def test_parse_endpoint_dictionary_flow(client: ASGITestClient) -> None:
    """Р6 ступень 1: известные слова → позиции; неизвестные → unknown (без fallback)."""
    client.post("/api/price-list", json={"name": "Печать документов", "price": 10.0})
    client.post("/api/price-list/1/synonyms", json={"word": "распечатать"})

    parsed = client.post("/api/parse", json={"text": "распечатать 10, риза 500"}).json()
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["name"] == "Печать документов"
    assert parsed["items"][0]["qty"] == 10.0
    assert "риза" in parsed["unknown"]  # жаргон пока не словаре → уточнение, не гадание


def test_off_catalog_report_endpoint(client: ASGITestClient) -> None:
    client.post(
        "/api/orders",
        json={
            "status": "новый",
            "payment_method": "наличные",
            "items": [{"kind": "manual", "name": "Мимо каталога", "price": 5, "save_to_catalog": False}],
        },
    )
    report = client.get("/api/report/off-catalog").json()
    assert len(report["items"]) == 1
    assert report["items"][0]["name"] == "Мимо каталога"


def test_payment_methods_settings_roundtrip(client: ASGITestClient) -> None:
    default = client.get("/api/settings/payment-methods").json()
    assert default["methods"] == ["наличные", "карта", "перевод"]

    updated = client.put("/api/settings/payment-methods", json={"methods": ["наличные", "QR"]}).json()
    assert updated["methods"] == ["наличные", "QR"]

    empty = client.put("/api/settings/payment-methods", json={"methods": ["  "]})
    assert empty.status_code == 400


def test_constructor_crud_reorder_and_order_sections(client: ASGITestClient) -> None:
    """Конструктор: сид, CRUD, reorder; заказ с пожеланиями и значениями разделов."""
    seeded = client.get("/api/sections").json()["sections"]
    assert [s["title"] for s in seeded] == ["Пожелания заказчика", "Срочность", "Доставка"]
    wishes_id = seeded[0]["id"]

    created = client.post(
        "/api/sections", json={"title": "Номер машины", "kind": "text", "required": False}
    ).json()
    assert created["kind"] == "text"

    bad_kind = client.post("/api/sections", json={"title": "X", "kind": "dropdown"})
    assert bad_kind.status_code == 400

    patched = client.patch(
        f"/api/sections/{created['id']}", json={"title": "Авто на доставку", "required": True}
    ).json()
    assert patched["required"] is True

    ids = [s["id"] for s in client.get("/api/sections").json()["sections"]]
    reordered = client.post("/api/sections/reorder", json={"ids": list(reversed(ids))}).json()
    assert [s["id"] for s in reordered["sections"]] == list(reversed(ids))

    # Заказ с пожеланиями (свободная форма) + значения разделов.
    price_item = client.post("/api/price-list", json={"name": "Печать", "price": 10.0}).json()
    order = client.post(
        "/api/orders",
        json={
            "status": "новый",
            "payment_method": "наличные",
            "items": [{"kind": "price_list", "price_list_item_id": price_item["id"]}],
            "wishes": "Позвонить за час до готовности",
            "section_values": {str(wishes_id): "Без полей — свободная форма"},
        },
    ).json()
    assert order["wishes"] == "Позвонить за час до готовности"

    values = client.get(f"/api/orders/{order['id']}/sections").json()["sections"]
    by_id = {s["section_id"]: s for s in values}
    assert by_id[wishes_id]["value"] == "Без полей — свободная форма"

    # PATCH пожеланий отдельно.
    updated = client.patch(f"/api/orders/{order['id']}", json={"wishes": "Обновили пожелание"}).json()
    assert updated["wishes"] == "Обновили пожелание"

    # export.txt содержит блок пожеланий.
    export_text = client.get(f"/api/orders/{order['id']}/export.txt").text
    assert "Пожелания заказчика:" in export_text
    assert "Обновили пожелание" in export_text

    # Обязательный раздел без значения → 400.
    req = client.post("/api/sections", json={"title": "Контакт", "kind": "text", "required": True}).json()
    order2 = client.post(
        "/api/orders",
        json={
            "status": "новый",
            "payment_method": "наличные",
            "items": [{"kind": "price_list", "price_list_item_id": price_item["id"]}],
            "section_values": {str(req["id"]): ""},
        },
    )
    assert order2.status_code == 400

    # Конструкторская страница отдаётся.
    page = client.get("/constructor")
    assert page.status_code == 200
    assert "Конструктор" in page.text
