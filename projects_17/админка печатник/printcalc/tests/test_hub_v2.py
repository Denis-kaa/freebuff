"""Тесты Hub v2: email-приём (EmailAdapter §43), шаблоны R1/R2/R3,
email-fallback адресата ответа (RESEARCH_ADOPTION_PLAN §5-Б п.11).

Контракты:
- mail_poller: Message-ID → external_id (идемпотентность §55), парсер v2
  запускается автоматически (record_incoming_message), флаг Seen — только
  после успешной записи;
- reply_templates: закрытый словарь (ANTI-6b), детерминированная подстановка
  parsed-фактов, неизвестное → «…» (не молча, не выдумка);
- store._reply_recipient: email-сообщение → ответ на адрес отправителя.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from printcalc_web import mail_poller, reply_templates, store


@pytest.fixture()
def conn() -> Any:
    from printcalc_web.db import connect

    database = connect(":memory:")
    try:
        yield database
    finally:
        database.close()


# ---------- mail_poller: разбор письма ---------------------------------------


def _make_message(**headers: str) -> Any:
    from email.message import EmailMessage

    message = EmailMessage()
    for key, value in headers.items():
        message[key] = value
    message.set_content("Нужны наклейки 20 на 30, 20 штук")
    return message


class _FakeAdapter(mail_poller.ImapAdapter):
    """Подмена сети: fetch_unseen/mark_seen работают на статичный список."""

    def __init__(self, payloads: list[dict[str, str]]) -> None:
        self._payloads = payloads
        self.seen: list[str] = []

    def fetch_unseen(self, limit: int = 20) -> list[dict[str, str]]:  # noqa: ARG002
        return list(self._payloads)

    def mark_seen(self, uid: str) -> None:
        self.seen.append(uid)


def test_to_payload_extracts_fields() -> None:
    adapter = mail_poller.ImapAdapter(
        host="x", port=993, user="u", password="p", folder="INBOX"
    )
    payload = adapter._to_payload(
        _make_message(
            **{
                "Message-ID": "<abc@org>",
                "From": "Анна Смирнова <anna@example.com>",
                "Subject": "Заказ наклеек",
            }
        ),
        "12",
    )
    assert payload["external_id"] == "<abc@org>"
    assert payload["from_addr"] == "anna@example.com"
    assert payload["from_name"] == "Анна Смирнова"
    assert "Заказ наклеек" in payload["text"]
    assert "наклейки 20 на 30" in payload["text"]


def test_process_message_records_and_marks_seen(conn: Any) -> None:
    adapter = _FakeAdapter([])
    payload = {
        "external_id": "<m1@org>",
        "uid": "1",
        "from_name": "Анна",
        "from_addr": "anna@example.com",
        "text": "Нужны наклейки 20 на 30, 20 штук",
    }
    mail_poller.process_message(conn, adapter, payload)
    messages = store.list_inbox(conn)
    assert len(messages) == 1
    recorded = messages[0]
    assert recorded["channel"] == "email"
    assert recorded["sender_handle"] == "anna@example.com"
    # Парсер v2 запускается автоматически (контракт record_incoming_message)
    assert "наклейк" in str(recorded["parsed"]).lower()
    assert adapter.seen == ["1"]  # письмо успешно записано → отметка о прочтении


def test_process_message_duplicate_not_marked(conn: Any) -> None:
    adapter = _FakeAdapter([])
    payload = {
        "external_id": "<m1@org>",
        "uid": "1",
        "from_name": "Анна",
        "from_addr": "anna@example.com",
        "text": "Текст",
    }
    mail_poller.process_message(conn, adapter, payload)
    mail_poller.process_message(conn, adapter, payload)
    messages = store.list_inbox(conn)
    assert len(messages) == 1  # идемпотентность §55: дубликат не создаёт строку
    assert adapter.seen.count("1") == 1  # отметка один раз


# ---------- reply_templates: закрытый словарь --------------------------------


def test_templates_closed_vocabulary() -> None:
    assert set(reply_templates.TEMPLATE_IDS) == {
        "R1_GROUPED_QUESTION",
        "R2_PACKAGE_EXPLAIN",
        "R3_HOW_TO_ORDER",
    }


def test_render_unknown_template_raises() -> None:
    with pytest.raises(ValueError, match="неизвестный шаблон"):
        reply_templates.render("R99")


def test_render_r1_with_sizes() -> None:
    parsed = {"items": [{"name": "Наклейка А4 (самоклейка)", "qty": 1}], "sizes": ["20 на 30"]}
    text = reply_templates.render("R1_GROUPED_QUESTION", parsed=parsed)
    assert "20 × 30" in text  # «на» → «×» (нормализация нормализатора S1)
    assert "количество" in text


def test_render_r1_without_facts_places_dots() -> None:
    text = reply_templates.render("R1_GROUPED_QUESTION", parsed={})
    assert "…" in text  # не молча: placeholder виден оператору


def test_render_r2_package_parts() -> None:
    parsed = {"items": [{"name": "Фото на документы 2шт.", "qty": 4}]}
    text = reply_templates.render("R2_PACKAGE_EXPLAIN", parsed=parsed)
    assert "Фото" in text
    assert "печать" in text  # состав пакета из закрытого словаря


def test_render_r3_procedure_not_prices() -> None:
    text = reply_templates.render("R3_HOW_TO_ORDER", parsed={})
    assert "1." in text and "смету" in text  # процедура, не цены (R3)


# ---------- store: email-fallback адресата ответа -----------------------------


def _client_with_email(conn: Any, email: str) -> int:
    client = store.create_client(conn, name="Анна")
    store.add_contact(conn, client["id"], channel="email", value=email)
    return int(client["id"])


def test_reply_recipient_email_message(conn: Any) -> None:
    message, _ = store.record_incoming_message(
        conn,
        channel="email",
        external_id="<m2@org>",
        sender_name="Пётр",
        sender_handle="peter@example.com",
        text="Баннер 3х6",
    )
    inquiry = store.create_inquiry_from_message(conn, message["id"])
    channel, recipient = store._reply_recipient(conn, inquiry["id"])
    assert channel == "email"
    assert recipient == "peter@example.com"


def test_reply_recipient_email_via_client_contact(conn: Any) -> None:
    client_id = _client_with_email(conn, "anna@example.com")
    message, _ = store.record_incoming_message(
        conn, channel="telegram", external_id="777", chat_id="777",
        sender_name="Анна", sender_handle="anna", text="Визитки 100 шт",
    )
    inquiry = store.create_inquiry_from_message(conn, message["id"], client_id=client_id)
    channel, recipient = store._reply_recipient(conn, inquiry["id"])
    assert channel == "email"
    assert recipient == "anna@example.com"  # приоритет §45: контакт клиента


# ---------- API: endpoints шаблонов -------------------------------------------


def test_api_reply_templates_endpoints() -> None:
    from fastapi.testclient import TestClient

    from printcalc_web import create_app

    app = create_app(":memory:")
    client = TestClient(app)

    listing = client.get("/api/reply-templates")
    assert listing.status_code == 200
    ids = {t["template_id"] for t in listing.json()["templates"]}
    assert ids == set(reply_templates.TEMPLATE_IDS)

    rendered = client.post(
        "/api/reply-templates/R1_GROUPED_QUESTION/render",
        json={"message_id": None},
    )
    assert rendered.status_code == 200
    assert "…" in rendered.json()["text"]

    missing = client.post("/api/reply-templates/R99/render", json={})
    assert missing.status_code == 404
