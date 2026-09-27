"""Тесты A5/A6: чат-интерфейс помощника и режимы ответа (Assistant v2.0).

Проверяется ТЗ §33/§36/§41:
- страница /assistant рендерится, содержит селект 8 режимов (§18) и ленту;
- чат — интерфейс: сквозной сценарий DoD §41 идёт через СУЩЕСТВУЮЩИЕ
  /api/order/analyze → /api/suggestions/decision (аудит) → /api/order/bridge
  (цена только сервером) — без новых движков и без цен от помощника.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient

GOLDEN = "Наклейка 50 на 30 149 шт плюс резка по контуру"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "assistant_ui.db"))


# --- A5: страница чата -------------------------------------------------------


def test_assistant_page_renders_with_8_modes(client: ASGITestClient) -> None:
    """§18: селект содержит ровно 8 режимов, по умолчанию Рабочий."""
    response = client.get("/assistant")
    assert response.status_code == 200
    body = response.text
    assert "Локальный помощник" in body
    assert "assistant-feed" in body and "assistant-form" in body
    assert body.count("<option") == 8, "ТЗ §18: 8 режимов ответа"
    assert "<option value=\"work\" selected>Рабочий</option>" in body, "дефолт — Рабочий"
    for mode in ("quick", "detailed", "teach", "clarify", "production", "sales", "check"):
        assert f'value="{mode}"' in body


def test_assistant_in_navigation(client: ASGITestClient) -> None:
    """Пункт «Помощник» в навигации вместо заглушки «скоро»."""
    body = client.get("/orders").text
    assert 'href="/assistant"' in body
    assert "AI-помощник" not in body or "скоро" not in body.split('href="/assistant"')[0][-200:]


# --- §36: один pipeline — чат это интерфейс -----------------------------------


def test_chat_end_to_end_dod(client: ASGITestClient) -> None:
    """§41 DoD: фраза оператора → вердикт → аудит решения → расчёт мостом.

    Полная цепочка чата без единого нового endpoint: analyze (S3) →
    suggestion_decisions (аудит §28) → bridge (цена сервером §30).
    """
    # 1. Оператор пишет фразу — помощник зовёт существующий analyze.
    verdict = client.post("/api/order/analyze", json={"text": GOLDEN}).json()
    assert verdict["matched_pack"] == "sticker"
    assert verdict["ready_for_calculator"] is True
    assert verdict["proposed_operations"][0]["operation_token"] == "OP-22"

    # 2. Оператор жмёт [+ Плоттерная резка] → аудит существующим endpoint.
    recorded = client.post(
        "/api/suggestions/decision",
        json={
            "decision": "accepted",
            "kind": "operation",
            "token": "OP-22",
            "source_text": GOLDEN,
        },
    )
    assert recorded.status_code == 201

    # 3. [Рассчитать] → существующий мост: цена ТОЛЬКО от движка.
    bridge = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-22"]},
    )
    assert bridge.status_code == 200
    payload = bridge.json()
    assert payload["calculator_id"] == "wide"
    assert payload["result"]["price"] > 0, "цена посчитана калькулятором, не помощником"


def test_chat_no_price_without_required_data(client: ASGITestClient) -> None:
    """§30: не хватает данных → мост честно 400, «примерных цен» нет."""
    verdict = client.post(
        "/api/order/analyze", json={"text": "Бэклит 80 на 60 качество 1440 dpi"}
    ).json()
    assert verdict["ready_for_calculator"] is False
    response = client.post(
        "/api/order/bridge", json={"verdict": verdict, "accepted_operations": []}
    )
    assert response.status_code == 400


def test_suggestion_decisions_journal_grows(client: ASGITestClient) -> None:
    """§28: решения логируются в существующий журнал (без новой системы)."""
    before = client.get("/api/suggestions/decisions").json()["decisions"]
    client.post(
        "/api/suggestions/decision",
        json={"decision": "rejected", "kind": "operation", "token": "OP-22"},
    )
    after = client.get("/api/suggestions/decisions").json()["decisions"]
    assert len(after) == len(before) + 1
    assert after[0]["decision"] == "rejected"
