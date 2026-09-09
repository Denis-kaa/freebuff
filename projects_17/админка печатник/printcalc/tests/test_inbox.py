"""Тесты Этапа 6: входящие сообщения, заявки, жизненный цикл, HTTP-цикл.

Правила проверяемые здесь:
- идемпотентность приёма §55: дубликат (channel, external_id) не создаёт строку;
- сообщение — факт: не редактируется, только статусы new → inquiry → archived;
- client matching §45: авто-привязка по telegram-контакту, ручная привязка;
- повторное «сообщение → заявка» возвращает ту же заявку (идемпотентно);
- парсер детерминированный: словарь из прайса, unknown честно возвращаются.
"""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "inbox.db")
    yield connection
    connection.close()


def _add_price(conn: sqlite3.Connection, name: str, price: float) -> int:
    item = store.add_price_item(conn, name=name, price=price)
    return int(item["id"])


# ---------- приём сообщений ----------


def test_record_message_parses_catalog_items(conn: sqlite3.Connection) -> None:
    _add_price(conn, "Баннер 440г", 300.0)
    message, created = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:100",
        sender_handle="ivan_p", text="баннер 440г, 2 штуки",
    )
    assert created is True
    assert message["status"] == "new"
    items = message["parsed"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Баннер 440г"
    assert items[0]["qty"] == 2.0
    assert "штуки" in message["parsed"]["unknown"]


def test_record_message_duplicate_is_idempotent(conn: sqlite3.Connection) -> None:
    first, created1 = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:7", text="визитки 100"
    )
    second, created2 = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:7", text="другой текст"
    )
    assert created1 and not created2
    assert first["id"] == second["id"]
    # Текст первого сохранён (сообщение — факт, перезапись запрещена).
    assert first["text"] == second["text"] == "визитки 100"


def test_record_message_unknown_channel_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError, match="неизвестный канал"):
        store.record_incoming_message(conn, channel="fax", external_id="x1")
    with pytest.raises(store.StoreError, match="external_id"):
        store.record_incoming_message(conn, channel="telegram", external_id="  ")


# ---------- заявки и matching ----------


def test_inquiry_from_message_is_idempotent(conn: sqlite3.Connection) -> None:
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:1", text="баннер 3х1"
    )
    inquiry1 = store.create_inquiry_from_message(conn, message["id"])
    assert inquiry1["status"] == "new"
    assert inquiry1["client_match"] == "none"
    inquiry2 = store.create_inquiry_from_message(conn, message["id"])
    assert inquiry2["id"] == inquiry1["id"]  # дубль сообщения → та же заявка
    # Статус сообщения перешёл в inquiry.
    refreshed = store.get_inbox_message(conn, message["id"])
    assert refreshed is not None and refreshed["status"] == "inquiry"


def test_inquiry_auto_matching_by_telegram_handle(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="Иван Петров")
    store.add_contact(conn, client["id"], channel="telegram", value="ivan_p")
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:2",
        sender_handle="@Ivan_P", text="нужны визитки",
    )
    inquiry = store.create_inquiry_from_message(conn, message["id"])
    # §45: авто-matching нормализует @ и регистр, дублей клиентов нет.
    assert inquiry["client_match"] == "auto"
    assert inquiry["client_id"] == client["id"]


def test_inquiry_manual_client_and_patch(conn: sqlite3.Connection) -> None:
    client = store.create_client(conn, name="ООО Ромашка")
    message, _ = store.record_incoming_message(
        conn, channel="manual", external_id="phone-note-1", text="таблички на дверь"
    )
    inquiry = store.create_inquiry_from_message(conn, message["id"], client_id=client["id"])
    assert inquiry["client_match"] == "manual"
    patched = store.update_inquiry(
        conn, inquiry["id"], summary="Таблички на дверь, 5 шт, ПВХ 3мм"
    )
    assert patched["summary"].startswith("Таблички на дверь")


def test_inquiry_estimate_link_lifecycle(conn: sqlite3.Connection) -> None:
    _add_price(conn, "Баннер 440г", 300.0)
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:3", text="баннер 440г"
    )
    inquiry = store.create_inquiry_from_message(conn, message["id"])
    estimate = store.create_estimate(
        conn, items=[{"kind": "price_list", "price_list_item_id": 1, "qty": 2}]
    )
    linked = store.attach_estimate_to_inquiry(conn, inquiry["id"], estimate["id"])
    assert linked["status"] == "estimated"
    assert linked["estimate_id"] == estimate["id"]
    # Идемпотентность: повторная привязка той же сметы — без ошибки.
    again = store.attach_estimate_to_inquiry(conn, inquiry["id"], estimate["id"])
    assert again["id"] == inquiry["id"]
    # Чужая смета — ошибка.
    with pytest.raises(store.StoreError, match="смета 999 не найдена"):
        store.attach_estimate_to_inquiry(conn, inquiry["id"], 999)


def test_archive_message(conn: sqlite3.Connection) -> None:
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:9", text="спам?"
    )
    archived = store.archive_inbox_message(conn, message["id"])
    assert archived["status"] == "archived"
    with pytest.raises(store.StoreError, match="не найдено"):
        store.archive_inbox_message(conn, 4242)


# ---------- HTTP-цикл §60 (MVP-цикл: сообщение → заявка → смета) ----------


def test_stage6_http_cycle(tmp_path) -> None:
    """MVP-цикл §60 (первая треть): сообщение → заявка → смета привязана."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from asgi_client import ASGITestClient

    from printcalc_web import create_app

    app = create_app(db_path=tmp_path / "inbox_api.db")
    client = ASGITestClient(app)

    # прайс-позиция
    item = client.post(
        "/api/price-list", json={"name": "Баннер 440г", "price": 300, "unit": "м2"}
    ).json()

    # 1. Telegram-сообщение (как его положил бы поллер)
    response = client.post(
        "/api/inbox",
        json={"channel": "telegram", "external_id": "tg:42", "chat_id": "100",
              "sender_handle": "ivan_p", "text": "баннер 440г, 2 штуки"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["created"] is True
    message = payload["message"]
    assert message["parsed"]["items"][0]["name"] == "Баннер 440г"

    # 2. Дубликат — идемпотентный ответ
    dup = client.post(
        "/api/inbox",
        json={"channel": "telegram", "external_id": "tg:42", "text": "повтор"},
    ).json()
    assert dup["created"] is False
    assert dup["message"]["id"] == message["id"]

    # 3. Сообщение → заявка
    inquiry = client.post(f"/api/inbox/{message['id']}/inquiry", json={}).json()
    assert inquiry["status"] == "new"

    # 4. Клиент привязывается вручную
    cl = client.post("/api/clients", json={"name": "Иван Петров"}).json()
    patched = client.patch(
        f"/api/inquiries/{inquiry['id']}", json={"client_id": cl["id"]}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["client_match"] == "manual"

    # 5. Смета → заявка (жизненный цикл new → estimated)
    estimate = client.post(
        "/api/estimates",
        json={"items": [{"kind": "price_list", "price_list_item_id": item["id"], "qty": 2}],
              "client_id": cl["id"]},
    ).json()
    linked = client.post(
        f"/api/inquiries/{inquiry['id']}/estimate",
        json={"estimate_id": estimate["id"]},
    ).json()
    assert linked["status"] == "estimated"

    # 6. Фильтры
    new_messages = client.get("/api/inbox", params={"status": "new"}).json()["messages"]
    assert all(m["status"] == "new" for m in new_messages)
    estimated = client.get(
        "/api/inquiries", params={"status": "estimated"}
    ).json()["inquiries"]
    assert len(estimated) == 1 and estimated[0]["id"] == inquiry["id"]

    # 7. Архив
    spam = client.post(
        "/api/inbox", json={"channel": "manual", "external_id": "m1", "text": "спам"}
    ).json()["message"]
    archived = client.post(f"/api/inbox/{spam['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["message"]["status"] == "archived"


# ---------- Telegram-адаптер (без сети) ----------


def test_telegram_update_parsing() -> None:
    from printcalc_web.telegram import _update_to_message

    update = {
        "update_id": 555,
        "message": {
            "message_id": 1,
            "text": "баннер 3х1",
            "from": {"first_name": "Иван", "last_name": "Петров", "username": "ivan_p"},
            "chat": {"id": 100500},
        },
    }
    payload = _update_to_message(update)
    assert payload is not None
    assert payload["external_id"] == "555"
    assert payload["chat_id"] == "100500"
    assert payload["sender_name"] == "Иван Петров"
    assert payload["sender_handle"] == "ivan_p"

    # нет текста → None (не создаём пустых сообщений)
    assert _update_to_message({"update_id": 556, "message": {"text": "  "}}) is None
    assert _update_to_message({"update_id": 557}) is None
