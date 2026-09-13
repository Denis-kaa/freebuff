"""Тесты Этапа 6b: исходящие ответы (outbox), ответы из сметы, email-matching.

Правила проверяемые здесь:
- адресат ответа — детерминированный приоритет §45: email → telegram → chat_id;
- письмо из сметы ДЕТЕРМИНИРОВАННОЕ (§37: без AI) — данные сметы → текст;
- факт отправки честен: sent/failed + причина, «не молча»;
- идемпотентность mark_reply_sent: повторный ok не меняет факт;
- client matching: email-адрес регистронезависим (как telegram-хэндл).
"""

from __future__ import annotations

import sqlite3

import pytest

from printcalc_web import emailer, outbox, store


@pytest.fixture()
def conn(tmp_path):
    from printcalc_web.db import connect

    connection = connect(tmp_path / "outbox.db")
    yield connection
    connection.close()


def _client_with_contacts(
    conn: sqlite3.Connection, *, email: str | None = None, telegram: str | None = None
) -> int:
    client = store.create_client(conn, name="Тест Клиент")
    client_id = int(client["id"])
    if email:
        store.add_contact(conn, client_id, channel="email", value=email)
    if telegram:
        store.add_contact(conn, client_id, channel="telegram", value=telegram)
    return client_id


def _estimate(conn: sqlite3.Connection, client_id: int | None = None) -> dict:
    return store.create_estimate(
        conn,
        items=[{"kind": "price_list", "price_list_item_id": _price(conn), "qty": 2}],
        client_id=client_id,
        note="срочно",
        valid_until="2026-12-31",
    )


def _price(conn: sqlite3.Connection) -> int:
    item = store.add_price_item(conn, name="Баннер 440г", price=300.0)
    return int(item["id"])


# ---------- адресат ответа (§45) ----------


def test_reply_recipient_email_priority(conn: sqlite3.Connection) -> None:
    """email-контакт клиента приоритетнее telegram (§45)."""
    client_id = _client_with_contacts(
        conn, email="CLIENT@Mail.ru", telegram="ivan_p"
    )
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:1", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]), client_id=client_id)
    channel, recipient = store._reply_recipient(conn, int(inquiry["id"]))
    assert channel == "email"
    assert recipient == "client@mail.ru"  # нижний регистр (email-нормализация)


def test_reply_recipient_fallback_to_telegram(conn: sqlite3.Connection) -> None:
    client_id = _client_with_contacts(conn, telegram="ivan_p")
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:2", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]), client_id=client_id)
    channel, recipient = store._reply_recipient(conn, int(inquiry["id"]))
    assert (channel, recipient) == ("telegram", "ivan_p")


def test_reply_recipient_fallback_to_chat_id(conn: sqlite3.Connection) -> None:
    """Без контактов клиента — chat_id входящего telegram-сообщения."""
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:3", chat_id="424242", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]))
    channel, recipient = store._reply_recipient(conn, int(inquiry["id"]))
    assert (channel, recipient) == ("telegram", "424242")


def test_reply_recipient_none_without_target(conn: sqlite3.Connection) -> None:
    message, _ = store.record_incoming_message(
        conn, channel="manual", external_id="m:1", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]))
    channel, recipient = store._reply_recipient(conn, int(inquiry["id"]))
    assert channel is None and recipient is None


# ---------- create_reply / статусы ----------


def test_create_reply_validates_channel_and_body(conn: sqlite3.Connection) -> None:
    with pytest.raises(store.StoreError, match="неизвестный канал"):
        store.create_reply(
            conn, inquiry_id=None, channel="fax", recipient="x", body="текст"
        )
    with pytest.raises(store.StoreError, match="пустым"):
        store.create_reply(
            conn, inquiry_id=None, channel="manual", recipient="x", body="   "
        )


def test_create_reply_auto_channel_requires_recipient(conn: sqlite3.Connection) -> None:
    """Без адресата create_reply поднимает StoreError (не молча)."""
    message, _ = store.record_incoming_message(
        conn, channel="manual", external_id="m:9", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]))
    with pytest.raises(store.StoreError, match="не найден адресат"):
        store.create_reply(conn, inquiry_id=int(inquiry["id"]), body="ответ")


def test_mark_reply_sent_is_idempotent(conn: sqlite3.Connection) -> None:
    reply = store.create_reply(
        conn, channel="manual", recipient="оператор", subject="s", body="b"
    )
    sent = store.mark_reply_sent(conn, int(reply["id"]), ok=True)
    assert sent["status"] == "sent" and sent["sent_at"] is not None
    again = store.mark_reply_sent(conn, int(reply["id"]), ok=False, error="поздно")
    assert again["status"] == "sent"  # повторный вызов не меняет факт
    assert again["sent_at"] == sent["sent_at"]


def test_list_replies_filters_by_inquiry(conn: sqlite3.Connection) -> None:
    reply1 = store.create_reply(
        conn, channel="manual", recipient="a", subject="s", body="b"
    )
    assert store.list_replies(conn) != []
    assert store.list_replies(conn, inquiry_id=int(reply1["inquiry_id"] or 0)) == []


# ---------- письмо из сметы (детерминированное §37) ----------


def test_format_estimate_reply_is_deterministic(conn: sqlite3.Connection) -> None:
    estimate = _estimate(conn)
    subject1, body1 = outbox.format_estimate_reply(estimate)
    subject2, body2 = outbox.format_estimate_reply(estimate)
    assert subject1 == subject2 == f"Смета №{estimate['id']} — «Печатникъ»"
    assert body1 == body2
    assert "• Баннер 440г × 2 — 600.00 ₽" in body1
    assert "ИТОГО: 600.00 ₽" in body1
    assert "2026-12-31" in body1
    assert "срочно" in body1


def test_send_estimate_reply_records_failure_honestly(conn: sqlite3.Connection) -> None:
    """SMTP не настроен → failed-запись с причиной, а не исключение."""
    client_id = _client_with_contacts(conn, email="client@mail.ru")
    estimate = _estimate(conn, client_id=client_id)
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="tg:10", text="баннер 2"
    )
    inquiry = store.create_inquiry_from_message(conn, int(message["id"]), client_id=client_id)
    reply = outbox.send_estimate_reply(conn, estimate, inquiry_id=int(inquiry["id"]))
    assert reply["status"] == "failed"
    assert "SMTP" in (reply["error"] or "") or "не настроен" in (reply["error"] or "")
    # Запись сохранена в outbox — оператор видит попытку и причину.
    assert store.list_replies(conn, inquiry_id=int(inquiry["id"])) != []


# ---------- email matching (§45, дополнение Этапа 6b) ----------


def test_email_matching_is_case_insensitive(conn: sqlite3.Connection) -> None:
    store.create_client(conn, name="Иван")
    client = store.create_client(conn, name="Пётр")
    store.add_contact(conn, int(client["id"]), channel="email", value="Petr@Yandex.Ru")
    message, _ = store.record_incoming_message(
        conn, channel="email", external_id="em:1",
        sender_handle="PETR@yandex.ru", text="визитки 100",
    )
    matched = store.match_client_for_message(conn, message)
    assert matched is not None
    assert matched["id"] == client["id"]


def test_email_matching_no_false_positive_on_telegram(conn: sqlite3.Connection) -> None:
    message, _ = store.record_incoming_message(
        conn, channel="email", external_id="em:2",
        sender_handle="unknown@example.com", text="визитки 100",
    )
    assert store.match_client_for_message(conn, message) is None


# ---------- emailer.dispatch (закрытый словарь каналов §44) ----------


def test_dispatch_email_without_config_returns_false() -> None:
    import os

    old = os.environ.pop("PRINTCALC_SMTP_HOST", None)
    try:
        ok, error = emailer.dispatch("email", "a@b.c", "s", "b")
        assert ok is False
        assert "SMTP" in error or "настроен" in error
    finally:
        if old is not None:
            os.environ["PRINTCALC_SMTP_HOST"] = old


def test_dispatch_manual_is_noop() -> None:
    ok, error = emailer.dispatch("manual", "x", "s", "b")
    assert ok is False
    assert "manual" in error
