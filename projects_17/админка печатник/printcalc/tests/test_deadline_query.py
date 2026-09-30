"""Тесты дедлайн-вопросов помощника (ТЗ §26 второй части prompts/2.md).

match_deadline_query — закрытый словарь интентов (ANTI-6b);
execute_deadline_query — отчёт из СУЩЕСТВУЮЩЕГО Deadline-слоя (тот же
urgency/фильтры, что у списка /orders; «не создавать отдельный источник
данных»); POST /api/deadline/query — контракт помощник ↔ API.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from printcalc_web import create_app, deadline
from printcalc_web.store import StoreError

from asgi_client import ASGITestClient


@pytest.fixture()
def client(tmp_path):
    yield ASGITestClient(create_app(db_path=tmp_path / "dq.db"))


@pytest.fixture()
def conn(tmp_path):
    """Отдельный коннект к той же БД, что у client — для чистых функций."""
    from printcalc_web.db import connect

    c = connect(tmp_path / "dq.db")
    yield c
    c.close()


def _mkorder(client: ASGITestClient, status: str = "в работе") -> int:
    response = client.post(
        "/api/orders",
        json={
            "status": status,
            "payment_method": "наличные",
            "items": [{"kind": "price_list", "price_list_item_id": 1, "qty": 1}],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _set_deadline(client: ASGITestClient, order_id: int, iso: str) -> None:
    response = client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": iso},
    )
    assert response.status_code == 200


def _hours_ahead(hours: float) -> str:
    from datetime import datetime, timezone

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(
        timespec="seconds"
    )


# --- match_deadline_query: закрытый словарь (ANTI-6b, ТЗ §26) -----------------


@pytest.mark.parametrize(
    ("phrase", "expected_filter"),
    [
        ("Что просрочено?", "overdue"),
        ("Какие сегодня горят?", "today"),
        ("Что сегодня горит?", "today"),
        ("Какие заказы на завтра?", "tomorrow"),
        ("Что на этой неделе?", "week"),
        ("Что без дедлайна?", "no_deadline"),
        ("Покажи активные с дедлайном", "active"),
    ],
)
def test_match_known_intents(phrase: str, expected_filter: str) -> None:
    matched = deadline.match_deadline_query(phrase)
    assert matched is not None
    assert matched[0] == expected_filter


def test_match_is_case_and_yo_insensitive() -> None:
    assert deadline.match_deadline_query("ЧТО ПРОСРОЧЕНО?") is not None
    # «Что без дедлайна» — канон ТЗ §26; вариант с «дедлайн» тоже узнаётся.
    assert deadline.match_deadline_query("что без дедлайна?")[0] == "no_deadline"


def test_match_unknown_phrase_returns_none() -> None:
    # Не дедлайн-фраза → None (помощник уходит в обычный analyze, не выдумка).
    assert deadline.match_deadline_query("Баннер 3х6, 10 шт") is None
    assert deadline.match_deadline_query("") is None


# --- execute_deadline_query: отчёт из существующего Deadline-слоя --------------


def test_execute_overdue_report_rows(client: ASGITestClient, conn) -> None:
    overdue_id = _mkorder(client)
    _set_deadline(client, overdue_id, _hours_ahead(-2))
    fresh_id = _mkorder(client)
    _set_deadline(client, fresh_id, _hours_ahead(30))

    report = deadline.execute_deadline_query(conn, "Что просрочено?")
    assert report is not None
    assert report["intent"] == "overdue"
    ids = [row["id"] for row in report["orders"]]
    assert overdue_id in ids and fresh_id not in ids
    row = next(r for r in report["orders"] if r["id"] == overdue_id)
    assert row["urgency_status"] == "overdue"
    assert row["remaining"].startswith("Просрочен")


def test_execute_today_and_tomorrow_split(client: ASGITestClient, conn) -> None:
    soon_id = _mkorder(client)
    _set_deadline(client, soon_id, _hours_ahead(5))  # сегодня
    tomorrow_id = _mkorder(client)
    _set_deadline(client, tomorrow_id, _hours_ahead(24 + 6))  # ~завтра

    today = deadline.execute_deadline_query(conn, "что сегодня горит?")
    assert today is not None and [r["id"] for r in today["orders"]] == [soon_id]
    tmrw = deadline.execute_deadline_query(conn, "какие заказы на завтра?")
    assert tmrw is not None and [r["id"] for r in tmrw["orders"]] == [tomorrow_id]


def test_execute_counts_cover_all_orders(client: ASGITestClient, conn) -> None:
    with_deadline = _mkorder(client)
    _set_deadline(client, with_deadline, _hours_ahead(3))
    plain = _mkorder(client)

    report = deadline.execute_deadline_query(conn, "что горит?")
    assert report is not None
    total = sum(report["counts"].values())
    assert total >= 2
    assert report["counts"]["no_deadline"] >= 1


def test_execute_final_orders_not_reported(client: ASGITestClient, conn) -> None:
    done_id = _mkorder(client, status="выполнен")
    _set_deadline(client, done_id, _hours_ahead(-5))  # просрочен, но финальный

    report = deadline.execute_deadline_query(conn, "Что просрочено?")
    assert report is not None
    assert [r["id"] for r in report["orders"]] == []


def test_execute_unknown_phrase_returns_none(client: ASGITestClient, conn) -> None:
    assert deadline.execute_deadline_query(conn, "баннер 3х6") is None


# --- POST /api/deadline/query: контракт помощник ↔ API -------------------------


def test_api_deadline_query_report(client: ASGITestClient) -> None:
    order_id = _mkorder(client)
    _set_deadline(client, order_id, _hours_ahead(2))

    response = client.post("/api/deadline/query", json={"text": "что сегодня горит?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "today"
    assert any(row["id"] == order_id for row in body["orders"])
    assert "counts" in body and "title" in body


def test_api_deadline_query_not_a_deadline_question(client: ASGITestClient) -> None:
    response = client.post("/api/deadline/query", json={"text": "наклейка 50х30"})
    assert response.status_code == 404
    assert "не дедлайн-вопрос" in response.json()["detail"]


def test_api_deadline_query_requires_text(client: ASGITestClient) -> None:
    assert client.post("/api/deadline/query", json={"text": ""}).status_code == 422
