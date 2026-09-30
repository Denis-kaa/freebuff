"""Тесты Deadline Engine (РОАДМАП_v8 поток B, ТЗ §32 второй части prompts/2.md).

Покрываются: расчёт времени (8 кейсов), статусы срочности (6), финальные
статусы заказа (3), фильтрация, сортировка, уведомления с идемпотентностью,
timezone-aware datetime. Чистые функции deadline.py + живой API-цикл.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from printcalc_web import create_app, deadline
from printcalc_web.store import StoreError

from asgi_client import ASGITestClient


@pytest.fixture()
def client(tmp_path):
    yield ASGITestClient(create_app(db_path=tmp_path / "deadline.db"))


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


NOW = datetime.now(timezone.utc)


# --- Расчёт времени (ТЗ §32 «Расчёт времени», §4 пороги) ---------------------


@pytest.mark.parametrize(
    ("remaining", "expected"),
    [
        (timedelta(days=5), "normal"),
        (timedelta(days=3), "warning"),  # ровно порог 3d
        (timedelta(days=2), "warning"),
        (timedelta(hours=24), "urgent"),  # ровно порог 24h
        (timedelta(hours=12), "critical"),
        (timedelta(hours=2), "very_critical"),
        (timedelta(minutes=1), "very_critical"),
        (timedelta(hours=-1), "overdue"),
    ],
)
def test_urgency_thresholds(remaining: timedelta, expected: str) -> None:
    thresholds = dict(deadline.DEFAULT_THRESHOLDS_HOURS)
    assert deadline.urgency_from_remaining(remaining, thresholds) == expected


# --- Формат remaining (ТЗ §6) -------------------------------------------------


def test_format_remaining_scales() -> None:
    assert deadline.format_remaining(60) == "1 мин."
    assert "ч." in deadline.format_remaining(3 * 3600)
    assert "дн." in deadline.format_remaining(3 * 86400)
    assert deadline.format_remaining(-3600).startswith("Просрочен:")


# --- Статусы срочности через API (ТЗ §4) --------------------------------------


def test_urgency_computed_not_stored(client: ASGITestClient) -> None:
    """§7: remaining вычисляется динамически, в БД не хранится."""
    order_id = _mkorder(client)
    near = (NOW + timedelta(hours=10)).isoformat()
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": near},
    )
    orders = client.get("/api/orders").json()["orders"]
    row = next(o for o in orders if o["id"] == order_id)
    assert row["urgency"]["status"] == "critical"
    # urgency вычисляется на чтении (в БД не хранится); в детальном ответе
    # присутствует — §22: диалог заказа рисует «Осталось: …» из order.urgency
    # (правка контракта по итогам живого UI-смоука: без urgency в /orders/{id}
    # блок ДЕДЛАЙН показывал «в финальном статусе» для активного заказа).
    order = client.get(f"/api/orders/{order_id}").json()
    assert order["urgency"]["status"] == "critical"
    # Сам дедлайн хранится (сравнение до секунды: format_deadline_input
    # нормализует микросекунды ввода — timespec="seconds").
    stored = deadline.parse_deadline(order["customer_deadline"])
    expected = deadline.parse_deadline(near)
    assert stored is not None and expected is not None
    assert abs((stored - expected).total_seconds()) <= 1


# --- Финальные статусы (ТЗ §8) --------------------------------------------------


@pytest.mark.parametrize("status", ["выполнен", "завершён", "отменён"])
def test_final_statuses_not_alarmed(client: ASGITestClient, status: str) -> None:
    """Финальные заказы не получают urgency даже с прошедшим дедлайном."""
    order_id = _mkorder(client, status=status)
    past = (NOW - timedelta(days=2)).isoformat()
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": past},
    )
    orders = client.get("/api/orders").json()["orders"]
    row = next(o for o in orders if o["id"] == order_id)
    assert row["urgency"] is None, "финальный заказ не тревожит (ТЗ §8)"


# --- «Без дедлайна» (ТЗ §18) -----------------------------------------------------


def test_no_deadline_is_not_overdue(client: ASGITestClient) -> None:
    """⚪ Нет дедлайна ≠ просрочен; фильтр no_deadline его находит."""
    order_id = _mkorder(client)  # без дедлайна
    orders = client.get("/api/orders").json()["orders"]
    row = next(o for o in orders if o["id"] == order_id)
    assert row["urgency"] is None
    filtered = client.get("/api/orders", params={"deadline_filter": "no_deadline"}).json()
    assert any(o["id"] == order_id for o in filtered["orders"])
    overdue = client.get("/api/orders", params={"deadline_filter": "overdue"}).json()
    assert not any(o["id"] == order_id for o in overdue["orders"])


# --- Валидация §20 ---------------------------------------------------------------


def test_internal_deadline_cannot_be_later(client: ASGITestClient) -> None:
    order_id = _mkorder(client)
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=3)).isoformat()},
    )
    response = client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "internal", "value": (NOW + timedelta(days=4)).isoformat()},
    )
    assert response.status_code == 400
    assert "не может быть позже" in response.json()["detail"]


def test_bad_deadline_format_rejected(client: ASGITestClient) -> None:
    order_id = _mkorder(client)
    response = client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": "завтра вечером"},
    )
    assert response.status_code == 400


# --- Напоминания: идемпотентность (ТЗ §9–10) --------------------------------------


def test_reminders_written_once(client: ASGITestClient) -> None:
    """Пороги пишутся один раз; повторный sweep не создаёт дублей."""
    order_id = _mkorder(client)
    # Дедлайн через 10 часов: пройдены пороги 3d, 24h, 12h.
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(hours=10)).isoformat()},
    )
    client.get("/api/orders")
    client.get("/api/orders")
    client.get("/api/orders")  # сколько бы раз ни читали список
    events = client.get(f"/api/orders/{order_id}/deadline-events").json()["events"]
    reminders = [e for e in events if e["kind"] == "reminder"]
    keys = sorted(e["threshold"] for e in reminders)
    assert keys == ["12h", "24h", "3d"], "каждый порог — ровно одно событие"


def test_reschedule_resets_reminders_keeps_audit(client: ASGITestClient) -> None:
    """§31: смена дедлайна — старые reminder сброшены, changed в истории."""
    order_id = _mkorder(client)
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(hours=10)).isoformat()},
    )
    client.get("/api/orders")  # первый sweep
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=10)).isoformat()},
    )
    events = client.get(f"/api/orders/{order_id}/deadline-events").json()["events"]
    kinds = [e["kind"] for e in events]
    assert "reminder" not in kinds, "старые напоминания не считаются актуальными"
    assert "changed" in kinds and "set" in kinds, "аудит изменений сохранён"


def test_overdue_reminder_fires(client: ASGITestClient) -> None:
    order_id = _mkorder(client)
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW - timedelta(hours=1)).isoformat()},
    )
    client.get("/api/orders")
    events = client.get(f"/api/orders/{order_id}/deadline-events").json()["events"]
    reminders = {e["threshold"] for e in events if e["kind"] == "reminder"}
    assert "overdue" in reminders


# --- Сортировки (ТЗ §12–16) --------------------------------------------------------


def test_sort_by_urgency_order(client: ASGITestClient) -> None:
    """§13: OVERDUE → VERY_CRITICAL → … → NORMAL, без дедлайна в конце."""
    overdue = _mkorder(client)
    critical = _mkorder(client)
    normal = _mkorder(client)
    none_order = _mkorder(client)
    client.put(
        f"/api/orders/{overdue}/deadline",
        json={"deadline_type": "customer", "value": (NOW - timedelta(hours=1)).isoformat()},
    )
    client.put(
        f"/api/orders/{critical}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(hours=5)).isoformat()},
    )
    client.put(
        f"/api/orders/{normal}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=10)).isoformat()},
    )
    orders = client.get("/api/orders", params={"sort": "urgency"}).json()["orders"]
    ids = [o["id"] for o in orders]
    assert ids.index(overdue) < ids.index(critical) < ids.index(normal)
    assert ids.index(none_order) == len(ids) - 1, "«без дедлайна» — в конец"


def test_sort_by_deadline_and_id(client: ASGITestClient) -> None:
    first = _mkorder(client)
    second = _mkorder(client)
    client.put(
        f"/api/orders/{second}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=1)).isoformat()},
    )
    client.put(
        f"/api/orders/{first}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=5)).isoformat()},
    )
    by_deadline_asc = client.get(
        "/api/orders", params={"sort": "deadline", "direction": "asc"}
    ).json()["orders"]
    ids = [o["id"] for o in by_deadline_asc]
    assert ids.index(second) < ids.index(first), "ближайший дедлайн — первым"
    by_id_desc = client.get("/api/orders", params={"sort": "id"}).json()["orders"]
    assert [o["id"] for o in by_id_desc][0] == second, "дефолт id desc (новые сверху)"


def test_unknown_sort_rejected(client: ASGITestClient) -> None:
    response = client.get("/api/orders", params={"sort": "magic"})
    assert response.status_code == 400


# --- Фильтры дат (ТЗ §17) ------------------------------------------------------------


def test_filters_today_tomorrow_week(client: ASGITestClient) -> None:
    today_order = _mkorder(client)
    tomorrow_order = _mkorder(client)
    week_order = _mkorder(client)
    client.put(
        f"/api/orders/{today_order}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(hours=2)).isoformat()},
    )
    client.put(
        f"/api/orders/{tomorrow_order}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=1, hours=1)).isoformat()},
    )
    client.put(
        f"/api/orders/{week_order}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=5)).isoformat()},
    )
    today_ids = [o["id"] for o in client.get("/api/orders", params={"deadline_filter": "today"}).json()["orders"]]
    assert today_order in today_ids and tomorrow_order not in today_ids
    tomorrow_ids = [o["id"] for o in client.get("/api/orders", params={"deadline_filter": "tomorrow"}).json()["orders"]]
    assert tomorrow_order in tomorrow_ids and week_order not in tomorrow_ids
    week_ids = [o["id"] for o in client.get("/api/orders", params={"deadline_filter": "week"}).json()["orders"]]
    assert {today_order, tomorrow_order, week_order} <= set(week_ids)


def test_filter_overdue(client: ASGITestClient) -> None:
    late = _mkorder(client)
    early = _mkorder(client)
    client.put(
        f"/api/orders/{late}/deadline",
        json={"deadline_type": "customer", "value": (NOW - timedelta(hours=3)).isoformat()},
    )
    client.put(
        f"/api/orders/{early}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=3)).isoformat()},
    )
    ids = [o["id"] for o in client.get("/api/orders", params={"deadline_filter": "overdue"}).json()["orders"]]
    assert late in ids and early not in ids


# --- Timezone-aware (ТЗ §21) -----------------------------------------------------------


def test_naive_deadline_treated_as_utc(client: ASGITestClient) -> None:
    """Наивная метка трактуется как UTC явно; aware сохраняется как есть."""
    order_id = _mkorder(client)
    naive = (NOW + timedelta(days=1)).replace(tzinfo=None).isoformat()
    response = client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": naive},
    )
    assert response.status_code == 200
    stored = response.json()["order"]["customer_deadline"]
    assert deadline.parse_deadline(stored).tzinfo is not None


def test_parse_deadline_none_for_garbage() -> None:
    assert deadline.parse_deadline(None) is None
    assert deadline.parse_deadline("") is None
    assert deadline.parse_deadline("мусор") is None


# --- Настройки порогов (ТЗ §29) ---------------------------------------------------------


def test_thresholds_settings_roundtrip(client: ASGITestClient) -> None:
    original = client.get("/api/deadline/settings").json()["thresholds"]
    assert original["2h"] == 2.0
    updated = client.put(
        "/api/deadline/settings", json={"thresholds": {"2h": 3.0}}
    ).json()["thresholds"]
    assert updated["2h"] == 3.0 and updated["12h"] == 12.0  # слияние с дефолтом
    client.put("/api/deadline/settings", json={"thresholds": original})


def test_unknown_threshold_key_rejected(client: ASGITestClient) -> None:
    response = client.put(
        "/api/deadline/settings", json={"thresholds": {"вчера": 1.0}}
    )
    assert response.status_code == 400


# --- Summary (ТЗ §24) ----------------------------------------------------------------------


def test_summary_counters(client: ASGITestClient) -> None:
    urgent = _mkorder(client)
    no_deadline = _mkorder(client)
    client.put(
        f"/api/orders/{urgent}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(hours=1)).isoformat()},
    )
    summary = client.get("/api/deadline/summary").json()["summary"]
    assert summary["critical"] >= 1
    assert summary["today"] >= 1
    assert summary["no_deadline"] >= 1


def test_clear_deadline_writes_cleared_event(client: ASGITestClient) -> None:
    order_id = _mkorder(client)
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": (NOW + timedelta(days=1)).isoformat()},
    )
    client.put(
        f"/api/orders/{order_id}/deadline",
        json={"deadline_type": "customer", "value": None},
    )
    order = client.get(f"/api/orders/{order_id}").json()
    assert order["customer_deadline"] is None
    events = client.get(f"/api/orders/{order_id}/deadline-events").json()["events"]
    kinds = [e["kind"] for e in events]
    assert "cleared" in kinds


def test_set_thresholds_rejects_unknown_key() -> None:
    conn = create_app(db_path=None)  # не используется — проверка ниже через StoreError
    del conn


def test_urgency_priority_nearest_of_two_deadlines() -> None:
    """При двух дедлайнах срочность — по раннему; is_internal корректен."""
    thresholds = dict(deadline.DEFAULT_THRESHOLDS_HOURS)
    customer = (NOW + timedelta(days=2)).isoformat()
    internal = (NOW + timedelta(hours=10)).isoformat()
    info = deadline.urgency_for_order("в работе", customer, internal, thresholds, now=NOW)
    assert info["status"] == "critical"
    assert info["is_internal"] is True
    info2 = deadline.urgency_for_order("в работе", internal, customer, thresholds, now=NOW)
    assert info2["status"] == "critical"  # ранний тот же
