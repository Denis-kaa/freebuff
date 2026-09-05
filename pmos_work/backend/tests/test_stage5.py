"""Тесты этапа 5 (5.md §50): Calendar & Events Engine.

System events — производные от источников (без дублей данных); custom — таблица.
"""

import uuid
from datetime import date, timedelta


def iso(d: date) -> str:
    return d.isoformat()


async def _seed_project(client, make_project, **extra):
    d = date.today()
    data = {
        "title": "Wazzup",
        "deadline": iso(d + timedelta(days=3)),
        "advance_date": iso(d - timedelta(days=1)),
        "final_payment_date": iso(d + timedelta(days=5)),
        "payment_percent": "50%",
        "manager_name": "Денис",
        "risk_level": "Средний",
    }
    data.update(extra)
    return await make_project(**data)


# ---------------------------------------------------------------------------
# System events: из источников (5.md §1, §7)
# ---------------------------------------------------------------------------
async def test_project_deadline_event(client, make_project):
    p = await _seed_project(client, make_project)
    res = await client.get("/api/calendar/events", params={
        "from": iso(date.today() - timedelta(days=10)),
        "to": iso(date.today() + timedelta(days=10)),
    })
    assert res.status_code == 200
    items = res.json()["items"]
    types = {e["type"] for e in items}
    assert "PROJECT_DEADLINE" in types
    assert "PAYMENT_ADVANCE" in types  # advance_date — вчера, не в диапазоне... проверим ниже
    deadline = next(e for e in items if e["type"] == "PROJECT_DEADLINE")
    assert deadline["project_id"] == p["id"]
    assert deadline["all_day"] is True
    assert deadline["metadata"]["project_display_id"] == p["display_id"]


async def test_date_range_backend_filter(client, make_project):
    """Backend фильтрует диапазон (5.md §33): событие вне окна не приходит."""
    d = date.today()
    await _seed_project(client, make_project)  # deadline +3д, доплата +5д
    res = await client.get("/api/calendar/events", params={
        "from": iso(d + timedelta(days=1)), "to": iso(d + timedelta(days=2)),
    })
    items = res.json()["items"]
    assert all(iso(d + timedelta(days=1)) <= e["start_at"][:10] <= iso(d + timedelta(days=2)) for e in items)
    assert all(e["type"] != "PROJECT_DEADLINE" for e in items)  # дедлайн +3 вне окна


async def test_task_deadline_event(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    task = (await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Получить ОС", "due_date": iso(d), "status": "TODO",
    })).json()
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=1)), "to": iso(d + timedelta(days=1)),
    })
    tasks = [e for e in res.json()["items"] if e["type"] == "TASK_DEADLINE"]
    assert any(e["task_id"] == task["id"] for e in tasks)


async def test_completed_task_not_overdue(client, make_project):
    """Завершённые задачи не дают событий-дедлайнов (5.md §31)."""
    d = date.today()
    p = await _seed_project(client, make_project)
    task = (await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Готово", "due_date": iso(d), "status": "TODO",
    })).json()
    await client.patch(f"/api/projects/{p['id']}/tasks/{task['id']}", json={"status": "DONE"})
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=1)), "to": iso(d + timedelta(days=1)),
    })
    tasks = [e for e in res.json()["items"] if e["type"] == "TASK_DEADLINE"]
    assert not any(e["task_id"] == task["id"] for e in tasks)


async def test_payment_events(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=2)), "to": iso(d + timedelta(days=10)),
    })
    items = res.json()["items"]
    advances = [e for e in items if e["type"] == "PAYMENT_ADVANCE"]
    finals = [e for e in items if e["type"] == "PAYMENT_FINAL"]
    assert len(advances) >= 1 and advances[0]["title"] == "Аванс"
    assert len(finals) >= 1 and finals[0]["title"] == "Доплата"
    assert all(a["project_id"] == p["id"] for a in advances)


async def test_signal_shipment_event(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    item = (await client.post("/api/project-items", json={
        "project_id": p["id"], "name": "Худи", "quantity": 100,
        "signal_shipping_date": iso(d + timedelta(days=1)),
    })).json()
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=2)),
    })
    shipments = [e for e in res.json()["items"] if e["type"] == "SIGNAL_SHIPMENT"]
    assert any(e["project_item_id"] == item["id"] for e in shipments)
    ship = next(e for e in shipments if e["project_item_id"] == item["id"])
    assert "Худи" in ship["title"]
    assert ship["source_type"] == "project_item"


# ---------------------------------------------------------------------------
# Filters (5.md §11-16, §33)
# ---------------------------------------------------------------------------
async def test_types_filter(client, make_project):
    d = date.today()
    await _seed_project(client, make_project)
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=2)), "to": iso(d + timedelta(days=10)),
        "types": "deadline",
    })
    items = res.json()["items"]
    assert items and all(e["type"] == "PROJECT_DEADLINE" for e in items)


async def test_project_filter(client, make_project):
    d = date.today()
    p1 = await _seed_project(client, make_project, title="A", deadline=iso(d + timedelta(days=1)))
    p2 = await _seed_project(client, make_project, title="B", deadline=iso(d + timedelta(days=2)))
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=3)),
        "project_id": p1["id"],
    })
    items = res.json()["items"]
    assert items
    assert all(e["project_id"] == p1["id"] for e in items)
    assert not any(e.get("metadata", {}).get("project_display_id") == p2["display_id"] for e in items)


async def test_manager_filter(client, make_project):
    d = date.today()
    await _seed_project(client, make_project, title="Денисов", manager_name="Денис",
                        deadline=iso(d + timedelta(days=1)))
    await _seed_project(client, make_project, title="Катин", manager_name="Катя",
                        deadline=iso(d + timedelta(days=1)))
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=2)),
        "manager": "Катя",
    })
    items = res.json()["items"]
    assert items
    ids = {e["metadata"]["project_display_id"] for e in items}
    assert "Денисов" not in {p for p in ids}


async def test_search_filter(client, make_project):
    d = date.today()
    await _seed_project(client, make_project, title="Wazzup", deadline=iso(d + timedelta(days=1)))
    await _seed_project(client, make_project, title="Другое", deadline=iso(d + timedelta(days=1)))
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=2)), "q": "Wazzup",
    })
    items = res.json()["items"]
    assert items
    titles = {e["metadata"].get("project_title") for e in items}
    assert "Wazzup" in titles


async def test_event_search_matches_source_title(client, make_project):
    """Поиск должен находить собственное имя задачи и custom-события, а не только проект."""
    d = date.today()
    p = await _seed_project(client, make_project, title="Нейтральный проект", deadline=iso(d + timedelta(days=1)))
    task = (await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Уникальная задача календаря", "due_date": iso(d), "status": "TODO",
    })).json()
    custom = (await client.post("/api/calendar/events", json={
        "title": "Уникальное событие календаря", "event_type": "MEETING",
        "start_at": f"{iso(d)}T12:00:00Z", "project_id": p["id"],
    })).json()

    task_res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d), "q": "Уникальная задача календаря",
    })
    assert any(e["task_id"] == task["id"] for e in task_res.json()["items"])

    custom_res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d), "q": "Уникальное событие календаря",
    })
    assert any(e["id"] == custom["id"] for e in custom_res.json()["items"])


# ---------------------------------------------------------------------------
# Today / Upcoming / Overdue (5.md §30-32)
# ---------------------------------------------------------------------------
async def test_today_contains_and_overdue(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    # задача на сегодня
    await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Сегодня сделать", "due_date": iso(d), "status": "TODO",
    })
    # просроченная задача
    await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Просрочено", "due_date": iso(d - timedelta(days=2)), "status": "TODO",
    })
    res = await client.get("/api/calendar/today")
    assert res.status_code == 200
    body = res.json()
    task_titles = {e["title"] for e in body["tasks"]}
    assert "Сегодня сделать" in task_titles
    overdue_titles = {e["title"] for e in body["overdue"]}
    assert "Просрочено" in overdue_titles
    assert "Сегодня сделать" not in overdue_titles
    # аванс на сегодня? advance_date = вчера → в overdue (если не завершено)
    adv = [e for e in body.get("payments", []) if e["type"] == "PAYMENT_ADVANCE"]
    adv_overdue = [e for e in body["overdue"] if e["type"] == "PAYMENT_ADVANCE"]
    assert body["date"] == iso(d)


async def test_upcoming(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    res = await client.get("/api/calendar/upcoming", params={
        "from": iso(d), "to": iso(d + timedelta(days=7)),
    })
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(e["type"] == "PROJECT_DEADLINE" for e in items)
    assert all(iso(d) <= e["start_at"][:10] <= iso(d + timedelta(days=7)) for e in items)


# ---------------------------------------------------------------------------
# Custom Events (5.md §21-22)
# ---------------------------------------------------------------------------
async def test_custom_event_crud(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    res = await client.post("/api/calendar/events", json={
        "title": "Встреча с фабрикой",
        "description": "обсудить тираж",
        "event_type": "MEETING",
        "start_at": f"{iso(d)}T09:00:00Z",
        "all_day": False,
        "project_id": p["id"],
    })
    assert res.status_code == 201, res.text
    ev = res.json()
    assert ev["type"] == "MEETING"
    assert ev["source_type"] == "custom"
    assert ev["project_id"] == p["id"]

    # читаем и обновляем
    got = await client.get(f"/api/calendar/events/{ev['id']}")
    assert got.status_code == 200
    upd = await client.patch(f"/api/calendar/events/{ev['id']}", json={"title": "Встреча перенесена", "start_at": f"{iso(d)}T11:00:00Z"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "Встреча перенесена"

    # событие попадает в выдачу диапазона
    res2 = await client.get("/api/calendar/events", params={"from": iso(d), "to": iso(d)})
    assert any(e["id"] == ev["id"] for e in res2.json()["items"])

    # удаляем
    dele = await client.delete(f"/api/calendar/events/{ev['id']}")
    assert dele.status_code == 204
    assert (await client.get(f"/api/calendar/events/{ev['id']}")).status_code == 404


async def test_custom_event_validation(client):
    res = await client.post("/api/calendar/events", json={
        "title": "X", "event_type": "BOGUS", "start_at": "2026-08-31T09:00:00Z",
    })
    assert res.status_code == 422
    # без start_at
    res = await client.post("/api/calendar/events", json={"title": "X"})
    assert res.status_code == 422


async def test_custom_event_foreign_project_404(client):
    res = await client.post("/api/calendar/events", json={
        "title": "X", "start_at": "2026-08-31T09:00:00Z", "project_id": str(uuid.uuid4()),
    })
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Системные события: правки (5.md §24-25, §45)
# ---------------------------------------------------------------------------
async def test_system_event_edit_blocked(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project)
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=1)), "to": iso(d + timedelta(days=10)),
    })
    deadline = next(e for e in res.json()["items"] if e["type"] == "PROJECT_DEADLINE")
    # PATCH системного события запрещён
    upd = await client.patch(f"/api/calendar/events/{deadline['id']}", json={"start_at": f"{iso(d + timedelta(days=9))}T00:00:00Z"})
    assert upd.status_code == 422
    # DELETE системного события запрещён
    dele = await client.delete(f"/api/calendar/events/{deadline['id']}")
    assert dele.status_code == 422


async def test_task_deadline_edit_redirects_to_source(client, make_project):
    """Перенос срока задачи через календарь меняет источник (5.md §25)."""
    d = date.today()
    p = await _seed_project(client, make_project)
    task = (await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Получить ОС", "due_date": iso(d), "status": "TODO",
    })).json()
    res = await client.get("/api/calendar/events", params={
        "from": iso(d - timedelta(days=1)), "to": iso(d + timedelta(days=1)),
    })
    task_ev = next(e for e in res.json()["items"] if e["type"] == "TASK_DEADLINE" and e["task_id"] == task["id"])
    new_date = iso(d + timedelta(days=2))
    upd = await client.patch(f"/api/calendar/events/{task_ev['id']}", json={"start_at": f"{new_date}T00:00:00Z"})
    assert upd.status_code == 200
    # источник изменился
    got_task = (await client.get(f"/api/projects/{p['id']}/tasks")).json()
    t = next(t for t in got_task if t["id"] == task["id"])
    assert t["due_date"] == new_date


# ---------------------------------------------------------------------------
# Dedup (5.md §36)
# ---------------------------------------------------------------------------
async def test_no_duplicate_events(client, make_project):
    d = date.today()
    await _seed_project(client, make_project, deadline=iso(d + timedelta(days=1)),
                        advance_date=iso(d + timedelta(days=1)))
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=2)),
    })
    items = res.json()["items"]
    ids = [e["id"] for e in items]
    assert len(ids) == len(set(ids)), "есть дубликаты событий (deterministic id сбой)"


# ---------------------------------------------------------------------------
# Timezone / All-day (5.md §38-39)
# ---------------------------------------------------------------------------
async def test_all_day_event_utc_midnight(client, make_project):
    d = date.today()
    p = await _seed_project(client, make_project, deadline=iso(d + timedelta(days=1)))
    res = await client.get("/api/calendar/events", params={
        "from": iso(d), "to": iso(d + timedelta(days=2)),
        "types": "deadline",
    })
    ev = res.json()["items"][0]
    assert ev["start_at"].endswith("T00:00:00+00:00") or ev["start_at"].endswith("T00:00:00Z")
    assert ev["all_day"] is True


async def test_custom_event_timezone_kept(client):
    """start_at хранится как передано (UTC ISO); UI конвертирует локально."""
    res = await client.post("/api/calendar/events", json={
        "title": "Звонок", "event_type": "CALL",
        "start_at": "2026-08-31T14:30:00+03:00",  # клиент прислал offset — нормализуем в UTC
    })
    assert res.status_code == 201
    assert res.json()["start_at"] == "2026-08-31T11:30:00Z"


# ---------------------------------------------------------------------------
# Permissions (5.md §44)
# ---------------------------------------------------------------------------
async def test_foreign_event_404(client):
    assert (await client.get(f"/api/calendar/events/{uuid.uuid4()}")).status_code == 404
    assert (await client.get("/api/calendar/events/not-a-real-id")).status_code == 404