"""Тесты S3: POST /api/order/analyze (РОАДМАП_v7 §4, промт_6 PHASE R3).

DoD §4: живой смоук-фраза «Наклейка 50×30, 149 шт + резка по контуру» →
вердикт с предложением «Плоттерная резка» и вопросом про макет. Здесь
та же фраза закреплена интеграционным тестом через ASGI-клиент.

Ручной ввод идёт через ТОТ ЖЕ endpoint (§4): parse_result опционален —
без него API сам вызывает parser v2 (источник qty/unknown, контракт R1).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient

#: Эталонная фраза интервью §4.1 / DoD РОАДМАП_v7 §4.
GOLDEN_STICKER = "Наклейка 50×30, 149 шт + резка по контуру"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "analyze.db"))


# --- DoD РОАДМАП_v7 §4 -----------------------------------------------------


def test_golden_sticker_contour_verdict(client: ASGITestClient) -> None:
    """DoD: наклейка + контур → OP-22 «Плоттерная резка» + вопрос про макет."""
    verdict = client.post("/api/order/analyze", json={"text": GOLDEN_STICKER}).json()

    assert verdict["matched_pack"] == "sticker"
    ops = [p["operation_token"] for p in verdict["proposed_operations"]]
    assert "OP-22" in ops
    by_token = {p["operation_token"]: p for p in verdict["proposed_operations"]}
    assert by_token["OP-22"]["label"] == "Плоттерная резка"
    assert by_token["OP-22"]["auto"] is False, "ничего не применяется без сотрудника (§1 промт_6)"

    # Вопрос про макет: unblocking missing + подсказка с макетом
    missing_fields = [m["field"] for m in verdict["missing"]]
    assert "layout_with_cut_contour" in missing_fields
    assert all(not m["blocking"] for m in verdict["missing"]), "qty и размер распознаны"
    assert any("Макет" in s["label"] for s in verdict["suggestions"])

    assert verdict["ready_for_calculator"] is True
    assert verdict["size_mm"] == [500.0, 300.0]
    assert verdict["quantity"] == 149


def test_manual_input_same_endpoint(client: ASGITestClient) -> None:
    """Ручной ввод (§4): без parse_result — нормализатор читает текст напрямую."""
    verdict = client.post(
        "/api/order/analyze", json={"text": "Баннер 3×6 + люверсы 30 см"}
    ).json()
    assert verdict["matched_pack"] == "banner"
    assert any(p["operation_token"] == "OP-13" for p in verdict["proposed_operations"])


# --- Блокировки и неизвестное ---------------------------------------------


def test_backlit_without_qty_blocks(client: ASGITestClient) -> None:
    """Бэклит без количества → ready_for_calculator=False (DoD S2 через API)."""
    verdict = client.post(
        "/api/order/analyze", json={"text": "Бэклит 80×60, 1440 dpi, резка по контуру"}
    ).json()
    assert verdict["matched_pack"] == "backlit"
    blocking = [m["field"] for m in verdict["missing"] if m["blocking"]]
    assert "quantity" in blocking
    assert verdict["ready_for_calculator"] is False


def test_unknown_product_no_proposals(client: ASGITestClient) -> None:
    """Продукт вне паков → вердикт без правил, unknown не теряется (не молчим)."""
    verdict = client.post(
        "/api/order/analyze", json={"text": "Открытки 10×15, 50 шт"}
    ).json()
    assert verdict["matched_pack"] == ""
    assert verdict["proposed_operations"] == []
    assert verdict["ready_for_calculator"] is True, "тираж и размер есть"
    assert any("открытки" in w.lower() for w in verdict["unknown_words"])


# --- Контракт parse_result (связка с parser v2) ----------------------------


def test_parse_result_chain_from_parse_endpoint(client: ASGITestClient) -> None:
    """parse_result из /api/parse принимается: unknown парсера проходит в вердикт."""
    parsed = client.post("/api/parse", json={"text": GOLDEN_STICKER}).json()
    verdict = client.post(
        "/api/order/analyze",
        json={"text": GOLDEN_STICKER, "parse_result": parsed},
    ).json()
    assert verdict["matched_pack"] == "sticker"
    assert "OP-22" in [p["operation_token"] for p in verdict["proposed_operations"]]


def test_parse_result_unknown_passthrough(client: ASGITestClient) -> None:
    """Явный parse_result: unknown из парсера сохраняется в вердикте (R1-контракт)."""
    verdict = client.post(
        "/api/order/analyze",
        json={
            "text": GOLDEN_STICKER,
            "parse_result": {"items": [], "unknown": ["фольга"], "needs_operator": False},
        },
    ).json()
    assert "фольга" in verdict["unknown_words"]


# --- Детерминизм и валидация ------------------------------------------------


def test_analyze_idempotent(client: ASGITestClient) -> None:
    """Повторный вызов с тем же текстом — байт-в-байт тот же вердикт."""
    first = client.post("/api/order/analyze", json={"text": GOLDEN_STICKER})
    second = client.post("/api/order/analyze", json={"text": GOLDEN_STICKER})
    assert first.json() == second.json()


def test_empty_text_rejected(client: ASGITestClient) -> None:
    """Пустой текст — 422 (Field min_length=1), а не вердикт-заглушка."""
    response = client.post("/api/order/analyze", json={"text": ""})
    assert response.status_code == 422


def test_all_proposals_auto_false(client: ASGITestClient) -> None:
    """Контракт §1 промт_6 через API: auto=False у КАЖДОГО предложения."""
    for text in (
        GOLDEN_STICKER,
        "Наклейка 20×30, 40 шт, с монтажной, порезать поштучно",
        "Баннер 3×6 + люверсы 30 см",
    ):
        verdict = client.post("/api/order/analyze", json={"text": text}).json()
        assert all(p["auto"] is False for p in verdict["proposed_operations"])
