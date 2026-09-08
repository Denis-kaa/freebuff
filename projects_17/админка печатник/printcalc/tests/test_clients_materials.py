"""Тесты клиентов, контактов и реестра материалов (Этап 1 роадмапа v6).

Покрывают §6 промт_4 (клиент ≠ контакт, client matching), §18 (реестр
с алиасами, BR-W1) и привязку клиента к заказу.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest

from printcalc_web import store
from printcalc_web.db import connect

from asgi_client import ASGITestClient


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / "core.db")
    yield connection
    connection.close()


# ---------- клиенты ----------


def test_client_crud_and_archive(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="ООО Ромашка", kind="компания", note="постоянный")
    assert client["name"] == "ООО Ромашка"
    assert client["kind"] == "компания"
    assert client["archived"] is False

    updated = store.update_client(conn, client["id"], note="прайс согласован")
    assert updated["note"] == "прайс согласован"

    archived = store.update_client(conn, client["id"], archived=True)
    assert archived["archived"] is True
    # архив не пропадает: get включает, list по умолчанию прячет
    assert store.get_client(conn, client["id"]) is not None
    assert store.list_clients(conn) == []
    assert len(store.list_clients(conn, include_archived=True)) == 1


def test_client_validation(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.create_client(conn, name="   ")
    with pytest.raises(store.StoreError):
        store.create_client(conn, name="Иван", kind="инопланетянин")
    with pytest.raises(store.StoreError):
        store.update_client(conn, 999, note="нет такого")


# ---------- контакты: клиент ≠ контакт (§6) ----------


def test_client_has_multiple_channel_contacts(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="Иван")
    store.add_contact(conn, client["id"], channel="phone", value="+7 900 000-11-22")
    store.add_contact(conn, client["id"], channel="telegram", value="@ivan")
    store.add_contact(conn, client["id"], channel="email", value="ivan@example.com")
    contacts = store.list_contacts(conn, client["id"])
    assert {c["channel"] for c in contacts} == {"phone", "telegram", "email"}


def test_contact_unique_across_clients(conn: sqlite3.Connection) -> None:
    """Один контакт не может принадлежать двум клиентам (совпадение — оператору, §45)."""
    a = store.create_client(conn, name="Иван")
    b = store.create_client(conn, name="Иван 2")
    store.add_contact(conn, a["id"], channel="telegram", value="@ivan")
    with pytest.raises(store.StoreError):
        store.add_contact(conn, b["id"], channel="telegram", value="@ivan")


def test_contact_channel_closed_vocabulary(conn: sqlite3.Connection) -> None:
    """Каналы — закрытый словарь (ANTI-6b): неизвестный канал отклоняется."""
    client = store.create_client(conn, name="Иван")
    with pytest.raises(store.StoreError):
        store.add_contact(conn, client["id"], channel="голубиная почта", value="ку-ку")
    with pytest.raises(store.StoreError):
        store.add_contact(conn, client["id"], channel="phone", value="  ")


def test_client_matching_by_contact(conn: sqlite3.Connection) -> None:
    """§45: сообщение из Telegram находит СУЩЕСТВУЮЩЕГО клиента, а не создаёт дубль."""
    client = store.create_client(conn, name="Сергей")
    store.add_contact(conn, client["id"], channel="max", value="sergey_max_id")

    found = store.find_client_by_contact(conn, channel="max", value="sergey_max_id")
    assert found is not None and found["id"] == client["id"]
    assert store.find_client_by_contact(conn, channel="max", value="неизвестный") is None


def test_contact_delete(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="Анна")
    contact = store.add_contact(conn, client["id"], channel="email", value="anna@ex.com")
    store.delete_contact(conn, contact["id"])
    assert store.list_contacts(conn, client["id"]) == []
    with pytest.raises(store.StoreError):
        store.delete_contact(conn, contact["id"])


def test_list_clients_search_by_contact_value(conn: sqlite3.Connection) -> None:
    """Глобальный поиск (§53): клиент находится по номеру телефона/значению."""
    client = store.create_client(conn, name="ООО Ромашка")
    store.add_contact(conn, client["id"], channel="phone", value="+7 900 123-45-67")
    hits = store.list_clients(conn, query="123-45-67")
    assert [c["id"] for c in hits] == [client["id"]]


# ---------- заказ ← клиент ----------


def test_assign_order_client(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="Иван")
    order = store.create_order(
        conn,
        status="новый",
        payment_method="наличные",
        items=[{"kind": "manual", "name": "Визитки", "price": 900, "qty": 1}],
    )
    updated = store.assign_order_client(conn, order["id"], client["id"])
    assert updated["client_id"] == client["id"]
    # отвязка
    updated = store.assign_order_client(conn, order["id"], None)
    assert updated["client_id"] is None
    with pytest.raises(store.StoreError):
        store.assign_order_client(conn, order["id"], 424242)


# ---------- реестр материалов (§18, BR-W1) ----------


def test_material_create_and_alias_lookup(conn: sqlite3.Connection) -> None:
    material = store.create_material(
        conn,
        fields={
            "name": "Баннер 440г",
            "aliases": ["Баннер 440", "Баннер (обычный)"],
            "consumption_mode": "ROLL_NESTING",
            "roll_width": 1000.0,
            "purchase_cost": 80.0,
            "base_unit": "m2",
        },
    )
    # поиск по точному имени
    assert store.find_material_by_name(conn, "Баннер 440г")["id"] == material["id"]
    # поиск по алиасу — защита от дрейфа написания (BR-W1)
    assert store.find_material_by_name(conn, "Баннер 440")["id"] == material["id"]
    assert store.find_material_by_name(conn, "Самоклейка") is None


def test_material_duplicate_name_rejected(conn: sqlite3.Connection) -> None:
    store.create_material(conn, fields={"name": "Холст"})
    with pytest.raises(store.StoreError):
        store.create_material(conn, fields={"name": "Холст"})


def test_material_roll_requires_width(conn: sqlite3.Connection) -> None:
    """ROLL_NESTING без ширины рулона — ошибка (consumption engine не сможет считать)."""
    with pytest.raises(store.StoreError):
        store.create_material(conn, fields={"name": "Плёнка", "consumption_mode": "ROLL_NESTING"})
    with pytest.raises(store.StoreError):
        store.create_material(
            conn, fields={"name": "Плёнка", "consumption_mode": "ROLL_NESTING", "roll_width": 0}
        )


def test_material_mode_and_unit_closed_vocabularies(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.create_material(conn, fields={"name": "Х", "consumption_mode": "МАГИЯ"})
    with pytest.raises(store.StoreError):
        store.create_material(conn, fields={"name": "Х", "base_unit": "кубометр"})


def test_material_update_patch_and_validation(conn: sqlite3.Connection) -> None:
    material = store.create_material(
        conn, fields={"name": "ПВХ 3 мм", "purchase_cost": 800.0}
    )
    updated = store.update_material(conn, material["id"], fields={"purchase_cost": 850.0})
    assert updated["purchase_cost"] == 850.0
    with pytest.raises(store.StoreError):
        store.update_material(conn, material["id"], fields={"consumption_mode": "NONSENSE"})
    with pytest.raises(store.StoreError):
        store.update_material(conn, material["id"], fields={"whatever": 1})
    # переключение в ROLL_NESTING без roll_width запрещено
    with pytest.raises(store.StoreError):
        store.update_material(conn, material["id"], fields={"consumption_mode": "ROLL_NESTING"})


# ---------- API ----------


@pytest.fixture()
def api(tmp_path: Path) -> Iterator[ASGITestClient]:
    from printcalc_web import create_app

    yield ASGITestClient(create_app(db_path=tmp_path / "api.db"))


def test_api_client_lifecycle(api: ASGITestClient) -> None:
    created = api.post("/api/clients", json={"name": "Иван", "kind": "физлицо"})
    assert created.status_code == 201
    client_id = created.json()["id"]

    contact = api.post(
        f"/api/clients/{client_id}/contacts", json={"channel": "phone", "value": "+7 900 000-00-00"}
    )
    assert contact.status_code == 201

    # lookup находит клиента по контакту
    found = api.get(
        "/api/clients/lookup", params={"channel": "phone", "value": "+7 900 000-00-00"}
    )
    assert found.status_code == 200
    assert found.json()["client"]["id"] == client_id

    # чтение с контактами
    detail = api.get(f"/api/clients/{client_id}")
    assert detail.status_code == 200
    assert len(detail.json()["contacts"]) == 1

    # дубль контакта — 400
    dup = api.post(
        f"/api/clients/{client_id}/contacts", json={"channel": "phone", "value": "+7 900 000-00-00"}
    )
    assert dup.status_code == 400

    # удаление контакта
    removed = api.delete(f"/api/clients/{client_id}/contacts/{contact.json()['id']}")
    assert removed.status_code == 204

    # архив
    patched = api.patch(f"/api/clients/{client_id}", json={"archived": True})
    assert patched.status_code == 200 and patched.json()["archived"] is True
    assert api.get("/api/clients").json()["clients"] == []

    # поиск по имени в списке (контакт удалён выше — ищем по имени)
    hit = api.get("/api/clients", params={"q": "Иван", "include_archived": True})
    assert len(hit.json()["clients"]) == 1


def test_api_material_lifecycle(api: ASGITestClient) -> None:
    created = api.post(
        "/api/materials",
        json={
            "name": "Баннер 440г",
            "aliases": ["Баннер 440"],
            "consumption_mode": "ROLL_NESTING",
            "roll_width": 1000,
            "purchase_cost": 80,
        },
    )
    assert created.status_code == 201
    material = created.json()
    assert material["purchase_unit"] == "m2"  # дефолт = base_unit

    # lookup по алиасу
    looked = api.get("/api/materials/lookup", params={"name": "Баннер 440"})
    assert looked.json()["material"]["id"] == material["id"]

    # дубль имени — 400
    dup = api.post("/api/materials", json={"name": "Баннер 440г"})
    assert dup.status_code == 400

    # патч цены
    patched = api.patch(f"/api/materials/{material['id']}", json={"purchase_cost": 85})
    assert patched.status_code == 200 and patched.json()["purchase_cost"] == 85

    # список
    listed = api.get("/api/materials", params={"active_only": True})
    assert [m["id"] for m in listed.json()["materials"]] == [material["id"]]

    # 404
    assert api.get("/api/materials/999").status_code == 404


def test_api_order_client_binding(api: ASGITestClient) -> None:
    client_id = api.post("/api/clients", json={"name": "Иван"}).json()["id"]
    order = api.post(
        "/api/orders",
        json={
            "payment_method": "наличные",
            "items": [{"kind": "manual", "name": "Визитки", "price": 900, "qty": 1}],
        },
    )
    assert order.status_code == 201
    order_id = order.json()["id"]

    bound = api.patch(f"/api/orders/{order_id}/client", json={"client_id": client_id})
    assert bound.status_code == 200 and bound.json()["client_id"] == client_id

    unbound = api.patch(f"/api/orders/{order_id}/client", json={"client_id": None})
    assert unbound.status_code == 200 and unbound.json()["client_id"] is None

    missing = api.patch(f"/api/orders/{order_id}/client", json={"client_id": 999})
    assert missing.status_code == 400
