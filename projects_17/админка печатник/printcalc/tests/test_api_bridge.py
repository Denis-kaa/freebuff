"""Тесты S5: POST /api/order/bridge (РОАДМАП_v7 §6, промт_6 PHASE R5).

Контракты поведения:
- цена считается ТОЛЬКО на сервере движком; клиент не присылает цен;
- только ПОДТВЕРЖДЁННЫЕ операции (S4-аудит) → work-флаги цены;
- нет размера/тиража/пака → честный 400 с вопросом (дефолты GUI 200×100
  не подставляются — §6 «не молча»);
- work-флаги в params триггерят задания OP-* в существующем идемпотентном
  конвейере generate_production_plan (отдельного конвейера нет).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient

#: Эталонная фраза DoD (та же, что S3) — сквозной сценарий §6.
GOLDEN_STICKER = "Наклейка 50×30, 149 шт + резка по контуру"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "bridge.db"))


def _sticker_verdict(client: ASGITestClient) -> dict:
    return client.post("/api/order/analyze", json={"text": GOLDEN_STICKER}).json()


# --- основной мост ---------------------------------------------------------


def test_bridge_golden_sticker_with_accepted_op(client: ASGITestClient) -> None:
    """DoD: вердикт наклейки + подтверждённая OP-22 → wide-позиция с ценой."""
    verdict = _sticker_verdict(client)
    assert verdict["ready_for_calculator"] is True

    response = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": ["OP-22"],
        },
    )
    assert response.status_code == 200
    bridge = response.json()
    assert bridge["calculator_id"] == "wide"

    params = bridge["params"]
    assert params["width"] == 50.0, "мм → см (спека wide — legacy GUI)"
    assert params["height"] == 30.0
    assert params["qty"] == 149.0
    assert params["work_plotter_cut"] is True, "подтверждённая операция → work-флаг"

    result = bridge["result"]
    assert result["calculator_id"] == "wide"
    assert result["price"] > 0, "цена посчитана сервером движком"


def test_bridge_without_accepted_ops_no_work_flags(
    client: ASGITestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Предложенная, но не подтверждённая операция в цену НЕ попадает (§1)."""
    # Тест про ФЛАГ-контракт, а не про цены владельца: изолируемся от
    # machine-state (на whimco заполнен data/wide_prices.yaml 100/500 —
    # иначе дельта легитимна и тест зависел бы от машины). Пустой путь
    # → резолвер цен даёт канон 0/0.
    from printcalc_web import pricing

    monkeypatch.setenv(
        pricing.PRICES_ENV_VAR, str(tmp_path / "wide_prices_absent.yaml")
    )

    verdict = _sticker_verdict(client)
    bridge = client.post(
        "/api/order/bridge", json={"verdict": verdict, "accepted_operations": []}
    ).json()
    assert not bridge["params"].get("work_plotter_cut"), "дефолт спеки False = работа не включена"
    price_plain = bridge["result"]["price"]

    bridge_op = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-22"]},
    ).json()
    assert bridge_op["params"]["work_plotter_cut"] is True
    # Цена резки — НАСТРАИВАЕМЫЙ параметр (решение Дениса 2026-09-12,
    # РОАДМАП_v7 §10): при изолированном прайсе (канон 0/0) дельты нет.
    # Контракт моста — флаг в params (→ задание OP-22 и цена
    # из прайса владельца), а не конкретная дельта.
    assert bridge_op["result"]["price"] == pytest.approx(price_plain), (
        "дефолтная резка 0/0 — цена меняется только через прайс владельца"
    )
    assert bridge_op["result"]["price"] >= price_plain


# --- честные ошибки (не молча) ---------------------------------------------


def test_bridge_missing_size_returns_400(client: ASGITestClient) -> None:
    """Нет размера → 400 с вопросом; дефолт GUI 200×100 не подставляется."""
    verdict = _sticker_verdict(client)
    broken = dict(verdict, size_mm=None)
    response = client.post("/api/order/bridge", json={"verdict": broken})
    assert response.status_code == 400
    assert "размер" in response.json()["detail"].lower()


def test_bridge_missing_qty_returns_400(client: ASGITestClient) -> None:
    verdict = _sticker_verdict(client)
    broken = dict(verdict, quantity=None)
    response = client.post("/api/order/bridge", json={"verdict": broken})
    assert response.status_code == 400
    assert "тираж" in response.json()["detail"].lower()


def test_bridge_unknown_pack_returns_400(client: ASGITestClient) -> None:
    """Продукт вне паков → 400 с подсказкой «добавьте вручную» (не молча)."""
    verdict = _sticker_verdict(client)
    broken = dict(verdict, matched_pack="mug")
    response = client.post("/api/order/bridge", json={"verdict": broken})
    assert response.status_code == 400
    assert "вручную" in response.json()["detail"]


def test_bridge_idempotent_same_verdict_same_result(client: ASGITestClient) -> None:
    """Тот же вердикт → байт-в-байт тот же результат (детерминизм движка)."""
    verdict = _sticker_verdict(client)
    first = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-22"]},
    ).text
    second = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-22"]},
    ).text
    assert first == second


def test_bridge_unknown_operation_token_is_ignored(client: ASGITestClient) -> None:
    """Код вне OPS_TO_WORK_FLAGS не падает и не попадает в параметры (закрытый словарь)."""
    verdict = _sticker_verdict(client)
    bridge = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-99"]},
    ).json()
    assert bridge["result"]["price"] > 0
    assert not bridge["params"].get("work_plotter_cut"), "OP-99 вне закрытого маппинга — флаг остался False"


# --- S6: ответы на вопросы (layout) → позиции дизайна -----------------------


def test_s6_layout_no_with_op22_adds_design_position(client: ASGITestClient) -> None:
    """«Макета нет» + подтверждённая OP-22 → доп. позиция «Макет под плоттерную резку».

    Сотрудник явно ответил «no» на вопрос вердикта; позиция дизайна посчитана
    сервером (design-калькулятор) — nothing auto: без ответа позиция не возникает.
    """
    verdict = _sticker_verdict(client)
    assert any(m["field"] == "layout_with_cut_contour" for m in verdict["missing"]), "вердикт golden-фразы спрашивает про макет с контуром"
    bridge = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": ["OP-22"],
            "question_answers": {"layout_with_cut_contour": "no"},
        },
    ).json()
    extras = bridge["extra_positions"]
    assert len(extras) == 1, "ровно одна дизайн-позиция"
    extra = extras[0]
    assert extra["calculator_id"] == "design"
    assert extra["name"] == "Макет под плоттерную резку"
    assert extra["result"]["price"] > 0, "цена дизайна посчитана сервером"
    assert bridge["facts_applied"] == {"layout_with_cut_contour": "no"}


def test_s6_layout_yes_adds_nothing(client: ASGITestClient) -> None:
    """«Макет есть» → позиция НЕ добавляется (факт фиксируется в facts_applied)."""
    verdict = _sticker_verdict(client)
    bridge = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": ["OP-22"],
            "question_answers": {"layout_with_cut_contour": "yes"},
        },
    ).json()
    assert bridge["extra_positions"] == []
    assert bridge["facts_applied"] == {"layout_with_cut_contour": "yes"}


def test_s6_layout_no_without_accepted_op22_adds_nothing(client: ASGITestClient) -> None:
    """«Макета нет» БЕЗ подтверждённой OP-22 — позиция не создаётся (не молча)."""
    verdict = _sticker_verdict(client)
    bridge = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": [],
            "question_answers": {"layout_with_cut_contour": "no"},
        },
    ).json()
    assert bridge["extra_positions"] == [], "вопрос производства ≠ операция без подтверждения"


def test_s6_no_answer_no_extras_backward_compatible(client: ASGITestClient) -> None:
    """Без question_answers контракт S5 не изменился (extras пуст, facts_applied {})."""
    verdict = _sticker_verdict(client)
    bridge = client.post(
        "/api/order/bridge",
        json={"verdict": verdict, "accepted_operations": ["OP-22"]},
    ).json()
    assert bridge["extra_positions"] == []
    assert bridge["facts_applied"] == {}
    assert bridge["result"]["price"] > 0


def test_s6_unknown_question_field_is_400(client: ASGITestClient) -> None:
    """Поле вопроса вне закрытого набора — честный 400 (ANTI-6b, не молча)."""
    verdict = _sticker_verdict(client)
    response = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": ["OP-22"],
            "question_answers": {"mount_height": "no"},
        },
    )
    assert response.status_code == 400
    assert "не поддерживается" in response.json()["detail"]


def test_s6_unknown_answer_value_is_400(client: ASGITestClient) -> None:
    """Значение ответа вне {yes, no} — честный 400 (ANTI-6b)."""
    verdict = _sticker_verdict(client)
    response = client.post(
        "/api/order/bridge",
        json={
            "verdict": verdict,
            "accepted_operations": ["OP-22"],
            "question_answers": {"layout": "maybe"},
        },
    )
    assert response.status_code == 400
    assert "вне набора" in response.json()["detail"]
