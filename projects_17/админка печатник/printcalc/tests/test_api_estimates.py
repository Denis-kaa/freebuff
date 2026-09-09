"""Интеграционные тесты API смет (Этап 2 роадмапа v6).

Полный цикл §60 (фрагмент): смета → принятие (snapshot §49) → заказ без
ручного ввода (§9). Гвардейские правила (статусы, дубликаты) на уровне HTTP.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "api_estimates.db"))


def test_estimate_full_cycle_to_order(client: ASGITestClient) -> None:
    client.post("/api/clients", json={"name": "ИП Петров"})
    client_id = client.get("/api/clients").json()["clients"][0]["id"]

    created = client.post(
        "/api/estimates",
        json={
            "items": [
                {"kind": "manual", "name": "Баннер 3x1", "price": 900, "qty": 2},
            ],
            "client_id": client_id,
            "note": "баннер на фасад",
            "valid_until": "2026-10-01",
        },
    )
    assert created.status_code == 201, created.text
    est = created.json()
    assert est["status"] == "draft"
    assert est["total"] == 1800.0
    assert est["client_name"] == "ИП Петров"

    # список с фильтром по статусу
    listed = client.get("/api/estimates", params={"status": "draft"}).json()["estimates"]
    assert [e["id"] for e in listed] == [est["id"]]

    # правка до accept — ок
    patched = client.patch(f"/api/estimates/{est['id']}", json={"note": "уточнили"})
    assert patched.status_code == 200 and patched.json()["note"] == "уточнили"

    # sent -> accept
    assert client.post(f"/api/estimates/{est['id']}/status", json={"status": "sent"}).status_code == 200
    accepted = client.post(f"/api/estimates/{est['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    snap = accepted.json()["snapshot"]
    assert snap["engine_version"] and len(snap["catalog_checksum"]) == 64

    # правка после accept — 400 (§49)
    assert client.patch(f"/api/estimates/{est['id']}", json={"note": "позже"}).status_code == 400

    # заказ из сметы
    order = client.post(f"/api/estimates/{est['id']}/order", json={"payment_method": "карта"})
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["total"] == 1800.0
    assert body["estimate_id"] == est["id"]
    assert body["client_id"] == client_id

    # заказ читается через обычный эндпоинт заказов со ссылкой на смету
    fetched = client.get(f"/api/orders/{body['id']}").json()
    assert fetched["estimate_id"] == est["id"]

    # повторный заказ из той же сметы — 400
    dup = client.post(f"/api/estimates/{est['id']}/order", json={"payment_method": "карта"})
    assert dup.status_code == 400


def test_estimate_transition_rules_over_http(client: ASGITestClient) -> None:
    created = client.post(
        "/api/estimates",
        json={"items": [{"kind": "manual", "name": "x", "price": 5, "qty": 1}]},
    )
    est_id = created.json()["id"]

    # draft -> viewed запрещён (§24)
    bad = client.post(f"/api/estimates/{est_id}/status", json={"status": "viewed"})
    assert bad.status_code == 400

    # заказ из draft — запрещён (§9)
    early = client.post(f"/api/estimates/{est_id}/order", json={"payment_method": "карта"})
    assert early.status_code == 400

    # reject — терминальный статус работает
    assert client.post(f"/api/estimates/{est_id}/status", json={"status": "rejected"}).status_code == 200
    assert client.get(f"/api/estimates/{est_id}").json()["status"] == "rejected"


def test_estimate_accept_is_idempotent_over_http(client: ASGITestClient) -> None:
    est_id = client.post(
        "/api/estimates",
        json={"items": [{"kind": "manual", "name": "x", "price": 5, "qty": 1}]},
    ).json()["id"]
    first = client.post(f"/api/estimates/{est_id}/accept").json()
    second = client.post(f"/api/estimates/{est_id}/accept").json()
    assert second["snapshot"]["created_at"] == first["snapshot"]["created_at"]


def test_estimate_validation_errors(client: ASGITestClient) -> None:
    # пустой список позиций — 422 (pydantic min_length=1)
    empty = client.post("/api/estimates", json={"items": []})
    assert empty.status_code == 422
    # несуществующий клиент — 400
    bad_client = client.post(
        "/api/estimates",
        json={"items": [{"kind": "manual", "name": "x", "price": 1}], "client_id": 4242},
    )
    assert bad_client.status_code == 400
    # несуществующая смета — 400
    assert client.get("/api/estimates/999").status_code == 400
