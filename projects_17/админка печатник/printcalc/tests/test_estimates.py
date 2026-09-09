"""Тесты Этапа 2 (роадмап v6): сметы, статусы, snapshot §49, заказ из сметы.

Правила, которые проверяются здесь:
- закрытый словарь статусов и разрешённых переходов (ANTI-6b);
- snapshot создаётся ровно при accept и никогда не меняется (§49);
- заказ из сметы переносит все позиции/сумму/клиента БЕЗ ручного ввода (§9);
- одна смета — один заказ; из не-accepted сметы заказ невозможен.
"""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import store


@pytest.fixture()
def conn(tmp_path: __import__("pathlib").Path) -> object:
    from printcalc_web.db import connect

    connection = connect(tmp_path / "estimates.db")
    store.seed_sections(connection)
    yield connection
    connection.close()


def _client(conn: sqlite3.Connection) -> dict:
    client = store.create_client(conn, name="ООО Ромашка", kind="компания")
    store.add_contact(conn, client_id=client["id"], channel="telegram", value="@romashka")
    return client


def _estimate(conn: sqlite3.Connection, client_id: int | None = None) -> dict:
    return store.create_estimate(
        conn,
        items=[
            {"kind": "manual", "name": "Баннер 3x1", "price": 900, "qty": 2},
            {"kind": "manual", "name": "Люверсы", "price": 30, "qty": 8, "save_to_catalog": False},
        ],
        client_id=client_id,
        note="со скидкой",
        valid_until="2026-10-01",
    )


# ---------- создание ----------


def test_create_estimate_resolves_and_sums(conn: sqlite3.Connection) -> None:
    client = _client(conn)
    est = _estimate(conn, client_id=client["id"])
    assert est["status"] == "draft"
    assert est["total"] == pytest.approx(900 * 2 + 30 * 8)
    assert est["client_id"] == client["id"]
    assert est["client_name"] == "ООО Ромашка"
    assert est["snapshot"] is None  # snapshot только после accept (§49)
    assert len(est["items"]) == 2
    assert est["items"][1]["kind"] == "manual"  # save_to_catalog=False сохранён


def test_create_estimate_requires_items_and_valid_client(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError):
        store.create_estimate(conn, items=[])
    with pytest.raises(store.StoreError):
        store.create_estimate(
            conn, items=[{"kind": "manual", "name": "x", "price": 1}], client_id=999
        )
    with pytest.raises(store.StoreError):
        store.create_estimate(
            conn,
            items=[{"kind": "manual", "name": "x", "price": 1}],
            valid_until="не-дата",
        )


def test_price_list_position_is_resolved_from_catalog(conn: sqlite3.Connection) -> None:
    item = store.add_price_item(conn, name="Ламинация А4", price=15.0)
    est = store.create_estimate(
        conn, items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 3}]
    )
    # цена — с сервера из каталога, не «клиентская»
    assert est["items"][0]["price"] == 15.0
    assert est["items"][0]["price_list_item_id"] == item["id"]
    assert est["total"] == pytest.approx(45.0)


# ---------- переходы статусов (§24) ----------


def test_transition_guards(conn: sqlite3.Connection) -> None:
    est = _estimate(conn)
    with pytest.raises(store.StoreError):  # draft -> viewed запрещён
        store.transition_estimate(conn, est["id"], "viewed")
    with pytest.raises(store.StoreError):  # неизвестный статус
        store.transition_estimate(conn, est["id"], "deleted")
    moved = store.transition_estimate(conn, est["id"], "sent")
    assert moved["status"] == "sent"
    # терминальный статус не имеет исходящих переходов
    store.transition_estimate(conn, est["id"], "rejected")
    with pytest.raises(store.StoreError):
        store.transition_estimate(conn, est["id"], "draft")


def test_update_estimate_blocked_after_accept(conn: sqlite3.Connection) -> None:
    est = _estimate(conn)
    store.update_estimate(conn, est["id"], note="правка до accept")  # ок
    store.accept_estimate(conn, est["id"])
    with pytest.raises(store.StoreError):
        store.update_estimate(conn, est["id"], note="правка после accept")


# ---------- snapshot §49 ----------


def test_accept_creates_snapshot_once(conn: sqlite3.Connection) -> None:
    est = _estimate(conn)
    accepted = store.accept_estimate(conn, est["id"])
    assert accepted["status"] == "accepted"
    snap = accepted["snapshot"]
    assert snap is not None
    assert snap["engine_version"]
    assert len(snap["registry_checksum"]) == 64  # sha256 hex
    assert len(snap["catalog_checksum"]) == 64
    assert snap["policy_version"] == "v1"
    assert snap["details"]["total"] == pytest.approx(accept_total(conn, est["id"]))

    # идемпотентность: повторный accept не создаёт второй snapshot
    again = store.accept_estimate(conn, est["id"])
    assert again["snapshot"]["created_at"] == snap["created_at"]
    rows = conn.execute("SELECT COUNT(*) FROM calc_snapshots").fetchone()
    assert rows[0] == 1


def accept_total(conn: sqlite3.Connection, estimate_id: int) -> float:
    row = conn.execute("SELECT total FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
    return float(row["total"])


def test_catalog_checksum_changes_when_prices_change(conn: sqlite3.Connection) -> None:
    from printcalc_web.store import _catalog_checksum

    before = _catalog_checksum(conn)
    store.add_price_item(conn, name="Новая позиция", price=100.0)
    after = _catalog_checksum(conn)
    assert before != after
    # стабильность при неизменных данных
    assert after == _catalog_checksum(conn)


def test_frozen_prices_survive_catalog_change(conn: sqlite3.Connection) -> None:
    """§49 на практике: цена позиции в принятой смете не меняется от правки прайса."""
    item = store.add_price_item(conn, name="Ламинация А4", price=15.0)
    est = store.create_estimate(
        conn, items=[{"kind": "price_list", "price_list_item_id": item["id"], "qty": 1}]
    )
    store.accept_estimate(conn, est["id"])
    store.update_price_item(conn, item["id"], fields={"price": 999.0})  # владелец поднял цену
    frozen = store.get_estimate(conn, est["id"])
    assert frozen["items"][0]["price"] == 15.0  # snapshot/details хранят старую цену
    assert frozen["snapshot"]["details"]["items"][0]["price"] == 15.0


# ---------- заказ из сметы (§9) ----------


def test_order_from_estimate_carries_everything(conn: sqlite3.Connection) -> None:
    client = _client(conn)
    est = _estimate(conn, client_id=client["id"])
    store.accept_estimate(conn, est["id"])

    order = store.create_order_from_estimate(conn, est["id"], payment_method="карта")
    assert order["status"] == "новый"
    assert order["total"] == pytest.approx(est["total"])
    assert order["client_id"] == client["id"]
    assert order["estimate_id"] == est["id"]
    assert [i["name"] for i in order["items"]] == [i["name"] for i in est["items"]]
    assert order["items"][1]["saved_to_catalog"] == 0  # manual остался manual


def test_order_requires_accepted_and_is_unique(conn: sqlite3.Connection) -> None:
    est = _estimate(conn)
    with pytest.raises(store.StoreError):  # draft -> нельзя
        store.create_order_from_estimate(conn, est["id"], payment_method="карта")
    store.accept_estimate(conn, est["id"])
    store.create_order_from_estimate(conn, est["id"], payment_method="карта")
    with pytest.raises(store.StoreError):  # повторно — нельзя
        store.create_order_from_estimate(conn, est["id"], payment_method="наличные")


def test_list_estimates_filters(conn: sqlite3.Connection) -> None:
    client = _client(conn)
    est1 = _estimate(conn, client_id=client["id"])
    _estimate(conn)
    store.accept_estimate(conn, est1["id"])
    assert len(store.list_estimates(conn)) == 2
    accepted = store.list_estimates(conn, status="accepted")
    assert [e["id"] for e in accepted] == [est1["id"]]
    by_client = store.list_estimates(conn, client_id=client["id"])
    assert [e["id"] for e in by_client] == [est1["id"]]
    with pytest.raises(store.StoreError):
        store.list_estimates(conn, status="несуществующий")
