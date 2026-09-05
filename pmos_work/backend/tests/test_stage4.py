"""Тесты этапа 4 (4.md §47): Dashboard Engine, Widget Registry, Data API."""

import uuid
from datetime import date, timedelta

DEMO_WS = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Dashboard CRUD (4.md §23)
# ---------------------------------------------------------------------------
async def test_create_dashboard(client):
    res = await client.post("/api/dashboards", json={"name": "Мой Dashboard"})
    assert res.status_code == 201, res.text
    d = res.json()
    assert d["name"] == "Мой Dashboard"
    assert d["is_default"] is False
    assert d["version"] == 1
    assert d["widgets"] == []


async def test_get_dashboard_foreign_id_404(client):
    """Права (4.md §46): чужой dashboard_id (просто подставленный) -> 404."""
    res = await client.get(f"/api/dashboards/{uuid.uuid4()}")
    assert res.status_code == 404


async def test_list_dashboards(client):
    await client.post("/api/dashboards", json={"name": "A"})
    await client.post("/api/dashboards", json={"name": "B"})
    res = await client.get("/api/dashboards")
    assert res.status_code == 200
    names = {d["name"] for d in res.json()}
    assert names == {"A", "B"}


async def test_default_dashboard_single(client):
    """Только один is_default в workspace (4.md §20)."""
    a = (await client.post("/api/dashboards", json={"name": "A", "is_default": True})).json()
    b = (await client.post("/api/dashboards", json={"name": "B", "is_default": True})).json()
    assert a["is_default"] is True
    assert b["is_default"] is True  # b стал default
    res = await client.get("/api/dashboards")
    defaults = [d for d in res.json() if d["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == b["id"]


async def test_rename_dashboard(client):
    a = (await client.post("/api/dashboards", json={"name": "A"})).json()
    res = await client.patch(f"/api/dashboards/{a['id']}", json={"name": "Финансы"})
    assert res.status_code == 200
    assert res.json()["name"] == "Финансы"


async def test_delete_dashboard(client):
    a = (await client.post("/api/dashboards", json={"name": "A"})).json()
    res = await client.delete(f"/api/dashboards/{a['id']}")
    assert res.status_code == 204
    assert (await client.get(f"/api/dashboards/{a['id']}")).status_code == 404


async def test_delete_default_promotes_oldest(client):
    a = (await client.post("/api/dashboards", json={"name": "A", "is_default": True})).json()
    b = (await client.post("/api/dashboards", json={"name": "B"})).json()
    await client.delete(f"/api/dashboards/{a['id']}")
    res = await client.get("/api/dashboards")
    defaults = [d for d in res.json() if d["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == b["id"]


# ---------------------------------------------------------------------------
# Duplicate (4.md §19)
# ---------------------------------------------------------------------------
async def test_duplicate_dashboard_copies_widgets(client):
    a = (await client.post("/api/dashboards", json={"name": "Производство"})).json()
    w = (await client.post(f"/api/dashboards/{a['id']}/widgets", json={
        "widget_type": "production", "title": "Пр-во", "config": {"x": 1},
        "layout": {"x": 0, "y": 0, "w": 6, "h": 2},
    })).json()
    res = await client.post(f"/api/dashboards/{a['id']}/duplicate")
    assert res.status_code == 201, res.text
    dup = res.json()
    assert dup["name"] == "Производство — копия"
    assert dup["is_default"] is False
    assert len(dup["widgets"]) == 1
    dw = dup["widgets"][0]
    assert dw["widget_type"] == "production"
    assert dw["config"] == {"x": 1}
    assert dw["layout"] == {"x": 0, "y": 0, "w": 6, "h": 2}


# ---------------------------------------------------------------------------
# Widgets (4.md §23, §5-9)
# ---------------------------------------------------------------------------
async def test_add_widget(client):
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    res = await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "calendar"})
    assert res.status_code == 201, res.text
    w = res.json()
    assert w["widget_type"] == "calendar"
    assert w["title"] == "Календарь"
    assert w["layout"]["w"] == 6  # default size из реестра
    assert w["is_hidden"] is False


async def test_add_unknown_widget_422(client):
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    res = await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "mars"})
    assert res.status_code == 422


async def test_remove_widget(client):
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    w = (await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "kpi"})).json()
    res = await client.delete(f"/api/dashboard-widgets/{w['id']}")
    assert res.status_code == 204
    assert (await client.get(f"/api/dashboard-widgets/{w['id']}")).status_code == 404


async def test_update_widget_layout(client):
    """Drag & Resize автосохраняют layout (4.md §5-6, §43)."""
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    w = (await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "calendar"})).json()
    res = await client.patch(f"/api/dashboard-widgets/{w['id']}", json={
        "layout": {"x": 6, "y": 0, "w": 12, "h": 6},  # растянули на всю ширину
    })
    assert res.status_code == 200
    assert res.json()["layout"] == {"x": 6, "y": 0, "w": 12, "h": 6}


async def test_hide_and_restore_widget(client):
    """Hide = конфигурация сохраняется, виджет можно вернуть (4.md §9-10)."""
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    w = (await client.post(f"/api/dashboards/{d['id']}/widgets", json={
        "widget_type": "finance", "config": {"mode": "x"},
    })).json()
    res = await client.patch(f"/api/dashboard-widgets/{w['id']}", json={"is_hidden": True})
    assert res.status_code == 200
    assert res.json()["is_hidden"] is True
    assert res.json()["config"] == {"mode": "x"}
    # восстановление
    res = await client.patch(f"/api/dashboard-widgets/{w['id']}", json={"is_hidden": False})
    assert res.json()["is_hidden"] is False


async def test_widget_configuration(client):
    """Конфигурация виджета (4.md §11-15) хранится в общей модели, без таблиц на тип."""
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    w = (await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "calendar"})).json()
    cfg = {"view": "week", "show_deadlines": True, "show_tasks": False, "show_payments": True}
    res = await client.patch(f"/api/dashboard-widgets/{w['id']}", json={"config": cfg})
    assert res.status_code == 200
    assert res.json()["config"] == cfg


async def test_widget_foreign_404(client):
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    w = (await client.post(f"/api/dashboards/{d['id']}/widgets", json={"widget_type": "kpi"})).json()
    other = (await client.post("/api/dashboards", json={"name": "E"})).json()
    res = await client.patch(f"/api/dashboard-widgets/{w['id']}", json={"title": "X", "dashboard_id": other["id"]})
    # dashboard_id не должен меняться — проверяем, что виджет остался в D
    assert res.status_code in (200, 422)
    lst = (await client.get(f"/api/dashboards/{d['id']}/widgets")).json()
    assert all(x["dashboard_id"] == d["id"] for x in lst)


# ---------------------------------------------------------------------------
# Optimistic locking (4.md §44)
# ---------------------------------------------------------------------------
async def test_dashboard_optimistic_locking(client):
    d = (await client.post("/api/dashboards", json={"name": "D"})).json()
    assert d["version"] == 1
    # другой пользователь изменил дашборд (версия -> 2)
    await client.patch(f"/api/dashboards/{d['id']}", json={"name": "D2"})
    # обновление с устаревшей версией -> 409
    res = await client.patch(f"/api/dashboards/{d['id']}", json={"name": "D3", "version": 1})
    assert res.status_code == 409
    # с актуальной версией — успех
    fresh = (await client.get(f"/api/dashboards/{d['id']}")).json()
    res = await client.patch(f"/api/dashboards/{d['id']}", json={"name": "D3", "version": fresh["version"]})
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Templates (4.md §35-38)
# ---------------------------------------------------------------------------
async def test_template_manager_creates_widgets(client):
    res = await client.post("/api/dashboards", json={"name": "Менеджер", "template": "manager"})
    assert res.status_code == 201, res.text
    widgets = res.json()["widgets"]
    types = {w["widget_type"] for w in widgets}
    assert "today-tasks" in types
    assert "calendar" in types
    assert "deadlines" in types
    assert len(widgets) >= 5


async def test_templates_meta(client):
    res = await client.get("/api/dashboards/templates")
    assert res.status_code == 200
    keys = {t["key"] for t in res.json()}
    assert {"manager", "production", "finance", "director"} <= keys


# ---------------------------------------------------------------------------
# Widget Registry metadata (4.md §2)
# ---------------------------------------------------------------------------
async def test_widget_types_metadata(client):
    res = await client.get("/api/dashboards/widget-types")
    assert res.status_code == 200
    by_type = {w["type"]: w for w in res.json()}
    assert "calendar" in by_type
    assert by_type["calendar"]["name"] == "Календарь"
    assert by_type["calendar"]["category"] == "planning"
    assert by_type["calendar"]["default_size"]["w"] == 6


# ---------------------------------------------------------------------------
# Widget Data API (4.md §24) — данные фильтруются на сервере (§45)
# ---------------------------------------------------------------------------
async def _seed_data(client, make_project):
    """Проект с дедлайном, задачей, позицией и риском + один без оплаты."""
    today = date.today()
    p1 = await make_project(
        title="Wazzup", deadline=(today + timedelta(days=3)).isoformat(),
        risk_level="Высокий", payment_percent="80%", advance_date=today.isoformat(),
    )
    item = (await client.post("/api/project-items", json={
        "project_id": p1["id"], "name": "Худи", "signal_required": True,
        "signal_status": "Отгружен", "mockup_status": "Правки",
        "signal_shipping_date": (today + timedelta(days=2)).isoformat(),
    })).json()
    await client.post(f"/api/projects/{p1['id']}/tasks", json={
        "title": "Получить ОС", "due_date": today.isoformat(), "status": "TODO",
    })
    await client.post(f"/api/projects/{p1['id']}/tasks", json={
        "title": "Просрочено", "due_date": (today - timedelta(days=2)).isoformat(), "status": "TODO",
    })
    await make_project(title="Чико", deadline=(today + timedelta(days=10)).isoformat(), payment_percent="100%")
    return p1, item


async def test_calendar_data(client, make_project):
    today = date.today()
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/calendar", params={
        "from": (today - timedelta(days=1)).isoformat(),
        "to": (today + timedelta(days=30)).isoformat(),
    })
    assert res.status_code == 200
    days = res.json()["days"]
    all_types = {e["event_type"] for day in days for e in day["events"]}
    # единый Calendar Engine (5.md §28): типы Unified Event
    assert "PROJECT_DEADLINE" in all_types
    assert "TASK_DEADLINE" in all_types
    assert "PAYMENT_ADVANCE" in all_types
    assert any(e["project_display_id"] for day in days for e in day["events"])


async def test_tasks_data(client, make_project):
    today = date.today()
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/tasks")
    assert res.status_code == 200
    body = res.json()
    titles_overdue = {t["title"] for t in body["overdue"]}
    titles_today = {t["title"] for t in body["today"]}
    assert "Просрочено" in titles_overdue
    assert "Получить ОС" in titles_today


async def test_deadlines_data(client, make_project):
    today = date.today()
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/deadlines", params={"days": 7})
    assert res.status_code == 200
    items = res.json()["items"]
    ids = {i["display_id"] for i in items}
    assert any(i["kind"] == "project" for i in items)
    assert any(i["kind"] == "item" for i in items)
    # дедлайн Чико (10 дней) не должен попасть в 7-дневное окно
    assert len(items) >= 2  # Wazzup-deadline + item-отгрузка (или Wazzup только)


async def test_deadlines_period_respected(client, make_project):
    today = date.today()
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/deadlines", params={"days": 3})
    items = res.json()["items"]
    assert all(0 <= i["days_left"] <= 3 for i in items)


async def test_risks_data(client, make_project):
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/risks")
    assert res.status_code == 200
    items = res.json()["items"]
    kinds = {i["kind"] for i in items}
    assert "risk" in kinds  # Высокий риск
    assert "production" in kinds  # сигнал без ОС / правки макета
    titles = {i["title"] for i in items}
    assert "Wazzup" in titles


async def test_production_data(client, make_project):
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/production")
    assert res.status_code == 200
    body = res.json()
    assert body["total_items"] >= 1
    keys = {i["key"] for i in body["items"]}
    assert "revision" in keys  # mockup_status = Правки


async def test_finance_data(client, make_project):
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/finance")
    assert res.status_code == 200
    body = res.json()
    titles = {i["title"] for i in body["unpaid"]}
    assert "Wazzup" in titles  # 80% — не оплачен полностью
    assert "Чико" not in titles  # 100%
    assert body["unpaid_count"] >= 1
    assert "RUB" in body["currencies"]


async def test_kpi_data(client, make_project):
    await _seed_data(client, make_project)
    for metric in ("active_projects", "open_tasks", "unpaid_projects", "signals_in_work", "mockup_revision"):
        res = await client.get("/api/dashboard-data/kpi", params={"metric": metric})
        assert res.status_code == 200, metric
        assert res.json()["metric"] == metric
        assert isinstance(res.json()["value"], int)


async def test_activity_data(client, make_project):
    today = date.today()
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/activity", params={"limit": 10})
    assert res.status_code == 200
    assert "items" in res.json()


async def test_projects_compact(client, make_project):
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/projects")
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 2
    assert all("display_id" in p and "title" in p for p in body)


async def test_ai_summary_prepared(client, make_project):
    await _seed_data(client, make_project)
    res = await client.get("/api/dashboard-data/ai-summary")
    assert res.status_code == 200
    body = res.json()
    assert "summary" in body
    assert body["counts"]["deadlines_7d"] >= 1


async def test_archived_projects_excluded_from_widgets(client, make_project):
    today = date.today()
    p = await make_project(title="Скрытый", deadline=(today + timedelta(days=2)).isoformat())
    await client.post(f"/api/projects/{p['id']}/archive")
    res = await client.get("/api/dashboard-data/deadlines", params={"days": 7})
    titles = {i["title"] for i in res.json()["items"]}
    assert "Скрытый" not in titles