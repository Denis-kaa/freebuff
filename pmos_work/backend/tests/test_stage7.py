"""Этап 7: Search / Filters / Views Engine."""
import uuid
from datetime import date, timedelta

from app.formula_engine import FormulaError, evaluate


async def test_formula_engine_safe_and_date_diff():
    assert evaluate("DATE_DIFF(deadline, TODAY())", {"deadline": date.today() + timedelta(days=3)}) == 3
    assert evaluate("quantity * unit_price", {"quantity": 4, "unit_price": 25}) == 100
    assert evaluate("IF(quantity, 10, 0)", {"quantity": 1}) == 10
    try:
        evaluate("__import__('os')", {})
    except FormulaError:
        pass
    else:
        raise AssertionError("unsafe formula must be rejected")


async def test_default_views_are_regular_views(client):
    res = await client.get("/api/views?entity_type=projects")
    assert res.status_code == 200
    names = {v["name"] for v in res.json()}
    assert {"Все проекты", "Мои проекты", "Активные", "Завершённые", "Высокий риск", "Ближайшие дедлайны"} <= names
    assert all(v["entity_type"] == "projects" for v in res.json())


async def test_nested_and_or_query(client, make_project):
    p1 = await make_project(title="Urgent production", stage="Производство", risk_level="Высокий", deadline="2026-09-03")
    await make_project(title="Normal production", stage="Производство", risk_level="Нет", deadline="2026-09-03")
    await make_project(title="Urgent design", stage="Макет", risk_level="Критический", deadline="2026-09-03")
    views = (await client.get("/api/views?entity_type=projects")).json()
    view = next(v for v in views if v["name"] == "Все проекты")
    payload = {
        "filters": {
            "operator": "AND",
            "conditions": [{"field": "stage", "operator": "equals", "value": "Производство"}],
            "groups": [{"operator": "OR", "conditions": [
                {"field": "risk_level", "operator": "equals", "value": "Высокий"},
                {"field": "risk_level", "operator": "equals", "value": "Критический"},
            ]}],
        },
        "sorting": [{"field": "deadline", "direction": "asc"}],
    }
    res = await client.post(f"/api/views/{view['id']}/query", json=payload)
    assert res.status_code == 200, res.text
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["id"] == p1["id"]


async def test_view_lifecycle_duplicate_favorite_default(client):
    create = await client.post("/api/views", json={"name": "Срочное производство", "entity_type": "projects", "visibility": "workspace", "config": {"sorting": [{"field": "risk_level", "direction": "desc"}]}})
    assert create.status_code == 201, create.text
    view = create.json()
    fav = await client.post(f"/api/views/{view['id']}/favorite", json={"favorite": True})
    assert fav.json()["is_favorite"] is True
    default = await client.post(f"/api/views/{view['id']}/default")
    assert default.json()["is_default"] is True
    dup = await client.post(f"/api/views/{view['id']}/duplicate")
    assert dup.status_code == 200
    assert dup.json()["name"].endswith("— копия")
    assert dup.json()["config"] == view["config"]


async def test_global_search_returns_projects_tasks_items(client, make_project):
    p = await make_project(title="Wazzup Search", manager_name="Катя")
    item = await client.post("/api/project-items", json={"project_id": p["id"], "name": "Wazzup Hoodie", "quantity": 10})
    assert item.status_code == 201
    task = await client.post(f"/api/projects/{p['id']}/tasks", json={"title": "Позвонить Wazzup", "priority": "HIGH"})
    assert task.status_code == 201
    res = await client.get("/api/search?q=Wazzup")
    assert res.status_code == 200, res.text
    body = res.json()["results"]
    assert any(x["id"] == p["id"] for x in body["projects"])
    assert any(x["project_id"] == p["id"] for x in body["items"])
    assert any(x["project_id"] == p["id"] for x in body["tasks"])


async def test_formula_custom_field_validation(client):
    good = await client.post("/api/custom-fields", json={"name": "Осталось дней", "entity_type": "PROJECT", "field_type": "FORMULA", "formula": "DATE_DIFF(deadline, TODAY())"})
    assert good.status_code == 201, good.text
    bad = await client.post("/api/custom-fields", json={"name": "Опасная формула", "entity_type": "PROJECT", "field_type": "FORMULA", "formula": "eval(1)"})
    assert bad.status_code == 422
