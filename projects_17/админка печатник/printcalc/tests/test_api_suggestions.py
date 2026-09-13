"""Тесты S4: UI-поверхность подсказок (РОАДМАП_v7 §5, промт_6 PHASE R4).

Backend-часть поверхности: аудит решений сотрудников по подсказкам
(§5: «подтверждения логируются — кто/когда/что»). Frontend проверяется
живым смоуком DoD (§5: сценарий «порезать поштучно» без знания
терминологии) — HTML-страница отдаёт блок подсказок.

Контракты поведения (§6 анти-правила):
- НИЧЕГО не применяется сервером: endpoint только логирует решение;
- decision/kind — закрытые словари (ANTI-6b), неизвестное → 422;
- вердикт детерминирован (idемпотентность S3 сохраняется).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from printcalc_web import create_app

from asgi_client import ASGITestClient

#: Эталонная фраза сценария «порезать поштучно» (DoD §5 / интервью §4.2).
DOD_PIECEWISE = "Наклейка 20×30, 40 шт, с монтажной, порезать поштучно"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[ASGITestClient]:
    yield ASGITestClient(create_app(db_path=tmp_path / "s4.db"))


# --- Аудит решений: контракт endpoint --------------------------------------


def test_decision_accepted_logged(client: ASGITestClient) -> None:
    """✓ по операции: решение фиксируется (кто/когда/что)."""
    response = client.post(
        "/api/suggestions/decision",
        json={
            "decision": "accepted",
            "kind": "operation",
            "token": "OP-22",
            "source_text": DOD_PIECEWISE,
            "payload": {"label": "Плоттерная резка"},
            "operator": "Денис",
        },
    )
    assert response.status_code == 201
    record = response.json()
    assert record["decision"] == "accepted"
    assert record["kind"] == "operation"
    assert record["token"] == "OP-22"
    assert record["operator"] == "Денис"
    assert record["created_at"], "когда — обязательная часть аудита"
    assert record["payload"]["label"] == "Плоттерная резка"


def test_decision_closed_vocabulary_rejects_unknown(client: ASGITestClient) -> None:
    """ANTI-6b: неизвестное decision/kind не проходит (422, не молча)."""
    assert (
        client.post("/api/suggestions/decision", json={"decision": "maybe"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/suggestions/decision",
            json={"decision": "accepted", "kind": "magic"},
        ).status_code
        == 422
    )


def test_decision_question_deferred_and_list_filter(client: ASGITestClient) -> None:
    """«Уточнить позже» и «Нет» логируются; журнал фильтруется по заявке."""
    client.post(
        "/api/suggestions/decision",
        json={"decision": "deferred", "kind": "question", "field": "layout"},
    )
    client.post(
        "/api/suggestions/decision",
        json={"decision": "rejected", "kind": "question", "field": "layout"},
    )
    client.post(
        "/api/suggestions/decision",
        json={"decision": "accepted", "kind": "operation", "token": "OP-15"},
    )
    listed = client.get("/api/suggestions/decisions").json()["decisions"]
    assert {d["decision"] for d in listed} == {"deferred", "rejected", "accepted"}
    assert [d["decision"] for d in listed] == [
        "accepted",
        "rejected",
        "deferred",
    ], "новые сверху"


def test_decisions_endpoint_scoped_by_inquiry(client: ASGITestClient) -> None:
    """Фильтр по inquiry_id не подмешивает чужие решения."""
    # FK включён (db.connect): заявки создаём настоящими, не выдуманными id.
    first = client.post(
        "/api/inbox",
        json={"channel": "telegram", "text": "первая", "external_id": "t1"},
    ).json()["message"]
    second = client.post(
        "/api/inbox",
        json={"channel": "telegram", "text": "вторая", "external_id": "t2"},
    ).json()["message"]
    inquiry_a = client.post(f"/api/inbox/{first['id']}/inquiry", json={}).json()
    inquiry_b = client.post(f"/api/inbox/{second['id']}/inquiry", json={}).json()
    client.post(
        "/api/suggestions/decision",
        json={"decision": "accepted", "inquiry_id": inquiry_a["id"], "token": "OP-22"},
    )
    client.post(
        "/api/suggestions/decision",
        json={"decision": "deferred", "inquiry_id": inquiry_b["id"], "field": "layout"},
    )
    scoped = client.get(
        "/api/suggestions/decisions", params={"inquiry_id": inquiry_a["id"]}
    ).json()["decisions"]
    assert len(scoped) == 1
    assert scoped[0]["inquiry_id"] == inquiry_a["id"]


# --- DoD §5: сценарий «порезать поштучно» ----------------------------------


def test_dod_piecewise_scenario_walk(client: ASGITestClient) -> None:
    """DoD: вердикт даёт предложения и вопросы; решения оператора логируются.

    Сценарий проходится от ввода до зафиксированных решений без знания
    внутренней терминологии: сотрудник видит «Предложения» (✓/Изменить)
    и «Нужно уточнить» (Да/Нет/Уточнить позже) — и подтверждает.
    """
    verdict = client.post("/api/order/analyze", json={"text": DOD_PIECEWISE}).json()

    # Распознано: продукт, размер, тираж.
    assert verdict["matched_pack"] == "sticker"
    assert verdict["quantity"] == 40
    assert verdict["size_mm"] == [200.0, 300.0]

    # Предложения: резка + накатка, ни одно не auto (§1).
    tokens = [op["operation_token"] for op in verdict["proposed_operations"]]
    assert "OP-22" in tokens and "OP-15" in tokens
    assert all(op["auto"] is False for op in verdict["proposed_operations"])

    # Нужно уточнить: вопрос про контур макета — контекстный, не весь список.
    kinds = [s["kind"] for s in verdict["suggestions"]]
    assert "layout" in kinds

    # Оператор подтверждает резку и отвечает на вопрос про макет.
    client.post(
        "/api/suggestions/decision",
        json={
            "decision": "accepted",
            "kind": "operation",
            "token": "OP-22",
            "source_text": DOD_PIECEWISE,
            "operator": "Денис",
        },
    )
    client.post(
        "/api/suggestions/decision",
        json={
            "decision": "accepted",
            "kind": "question",
            "field": "layout",
            "source_text": DOD_PIECEWISE,
            "payload": {"answer": "Да, контуры есть"},
            "operator": "Денис",
        },
    )
    journal = client.get("/api/suggestions/decisions").json()["decisions"]
    assert len(journal) == 2
    assert all(d["operator"] == "Денис" for d in journal)
    assert all(d["created_at"] for d in journal)


def test_analyze_idempotent_with_suggestions_surface(client: ASGITestClient) -> None:
    """Повторный разбор той же фразы — байт-в-байт тот же вердикт (S3-контракт)."""
    first = client.post("/api/order/analyze", json={"text": DOD_PIECEWISE})
    second = client.post("/api/order/analyze", json={"text": DOD_PIECEWISE})
    assert first.json() == second.json()


def test_main_page_serves_suggestions_surface(client: ASGITestClient) -> None:
    """HTML главного экрана содержит блок подсказок и скрипт S4."""
    page = client.get("/").text
    assert 'id="suggest-box"' in page
    assert "/static/suggestions.js" in page
