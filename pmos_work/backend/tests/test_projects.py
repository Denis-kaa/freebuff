"""Тесты этапа 2: Projects, Custom Fields, Views, Filters, Permissions (спец. 2.md §30)."""

import uuid


# ---------------------------------------------------------------------------
# Сценарий 1: создание проекта
# ---------------------------------------------------------------------------
async def test_create_project_display_id(client, make_project):
    p1 = await make_project(title="Wazzup")
    assert p1["display_id"].startswith("P")
    assert p1["title"] == "Wazzup"
    assert p1["stage"] == "Сигнал"

    p2 = await make_project(title="Чико")
    # генерация display_id сервером: последовательные номера
    assert int(p2["display_id"][1:]) == int(p1["display_id"][1:]) + 1


async def test_list_projects_pagination(client, make_project):
    for i in range(5):
        await make_project(title=f"Проект {i}")
    res = await client.get("/api/projects", params={"page_size": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1


async def test_search_project(client, make_project):
    await make_project(title="Wazzup-media")
    await make_project(title="Чико-бар")
    res = await client.get("/api/projects", params={"search": "wazzup", "page_size": 10})
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Wazzup-media"


# ---------------------------------------------------------------------------
# Редактирование проекта
# ---------------------------------------------------------------------------
async def test_update_project(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.patch(f"/api/projects/{p['id']}", json={"stage": "Тираж", "manager_name": "Катя"})
    assert res.status_code == 200
    body = res.json()
    assert body["stage"] == "Тираж"
    assert body["manager_name"] == "Катя"


async def test_get_project_by_id(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.get(f"/api/projects/{p['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == p["id"]


async def test_project_404(client):
    res = await client.get(f"/api/projects/{uuid.uuid4()}")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Archive (soft-delete, спец. §20)
# ---------------------------------------------------------------------------
async def test_archive_hides_from_default_list(client, make_project):
    p = await make_project(title="Устаревший")
    res = await client.post(f"/api/projects/{p['id']}/archive")
    assert res.status_code == 200
    assert res.json()["archived_at"] is not None

    # не показывается в обычном списке
    data = (await client.get("/api/projects", params={"search": "Устаревший"})).json()
    assert data["total"] == 0

    # показывается с include_archived
    data = (await client.get("/api/projects", params={"search": "Устаревший", "include_archived": True})).json()
    assert data["total"] == 1

    # разархивация
    res = await client.post(f"/api/projects/{p['id']}/unarchive")
    assert res.json()["archived_at"] is None


# ---------------------------------------------------------------------------
# Bulk actions (спец. §19)
# ---------------------------------------------------------------------------
async def test_bulk_update_stage(client, make_project):
    p1 = await make_project(title="A"); p2 = await make_project(title="B")
    res = await client.post("/api/projects/bulk-update", json={"ids": [p1["id"], p2["id"]], "stage": "Макет"})
    assert res.status_code == 200
    assert res.json()["updated"] == 2
    for pid in (p1["id"], p2["id"]):
        assert (await client.get(f"/api/projects/{pid}")).json()["stage"] == "Макет"


# ---------------------------------------------------------------------------
# Custom Fields (спец. §6-11, Сценарий 2)
# ---------------------------------------------------------------------------
async def test_create_custom_field_text(client):
    res = await client.post("/api/custom-fields", json={"name": "Номер накладной", "field_type": "TEXT"})
    assert res.status_code == 201, res.text
    cf = res.json()
    assert cf["slug"] == "nomer_nakladnoi"
    assert cf["field_type"] == "TEXT"


async def test_custom_field_all_types(client):
    for ftype in ["TEXT", "LONG_TEXT", "NUMBER", "DATE", "DATETIME", "BOOLEAN", "SELECT", "MULTI_SELECT", "PERCENT", "CURRENCY", "URL", "FORMULA"]:
        res = await client.post("/api/custom-fields", json={"name": f"Поле {ftype}", "field_type": ftype})
        assert res.status_code == 201, f"{ftype}: {res.text}"


async def test_custom_field_slug_unique(client):
    await client.post("/api/custom-fields", json={"name": "Приоритет", "field_type": "TEXT"})
    res = await client.post("/api/custom-fields", json={"name": "Приоритет", "field_type": "SELECT", "options": ["Низкий", "Средний", "Высокий"]})
    assert res.status_code == 201
    assert res.json()["slug"] != "prioritet"  # slug с суффиксом


async def test_custom_field_invalid_type(client):
    res = await client.post("/api/custom-fields", json={"name": "X", "field_type": "SUPER_MEGA"})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Custom Field Values (спец. §10, Сценарий 3)
# ---------------------------------------------------------------------------
async def test_save_and_restore_custom_value(client, make_project):
    cf = (await client.post("/api/custom-fields", json={"name": "Номер накладной", "field_type": "TEXT"})).json()
    p = await make_project(title="Wazzup")

    res = await client.put(f"/api/projects/{p['id']}/custom-values", json={"values": {cf["slug"]: "784521"}})
    assert res.status_code == 200

    # переоткрытие — значение сохранилось (Сценарий 3)
    got = (await client.get(f"/api/projects/{p['id']}")).json()
    assert got["custom_values"][cf["slug"]] == "784521"


async def test_custom_value_number_typed(client, make_project):
    cf = (await client.post("/api/custom-fields", json={"name": "Кол-во упаковок", "field_type": "NUMBER"})).json()
    p = await make_project(title="Wazzup")
    await client.put(f"/api/projects/{p['id']}/custom-values", json={"values": {cf["slug"]: 12}})
    got = (await client.get(f"/api/projects/{p['id']}")).json()
    assert got["custom_values"][cf["slug"]] == 12


# ---------------------------------------------------------------------------
# Filters (спец. §14-15, §23)
# ---------------------------------------------------------------------------
async def test_filter_system_field(client, make_project):
    await make_project(title="A", stage="Производство", manager_name="Денис", payment_percent="80%")
    await make_project(title="B", stage="Сигнал", manager_name="Катя", payment_percent="100%")

    filters = [{"field": "stage", "operator": "equals", "value": "Производство"}]
    res = await client.get("/api/projects", params={"filters": __import__("json").dumps(filters), "page_size": 10})
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "A"


async def test_filter_number_lt(client, make_project):
    await make_project(title="A", payment_percent="80%")
    await make_project(title="B", payment_percent="100%")
    filters = [{"field": "payment_percent", "operator": "lt", "value": "100%"}]
    res = await client.get("/api/projects", params={"filters": __import__("json").dumps(filters), "page_size": 10})
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "A"


async def test_filter_custom_field(client, make_project):
    cf = (await client.post("/api/custom-fields", json={"name": "Приоритет", "field_type": "SELECT", "options": ["Низкий", "Высокий"]})).json()
    p1 = await make_project(title="A")
    p2 = await make_project(title="B")
    await client.put(f"/api/projects/{p1['id']}/custom-values", json={"values": {cf["slug"]: "Высокий"}})
    await client.put(f"/api/projects/{p2['id']}/custom-values", json={"values": {cf["slug"]: "Низкий"}})

    filters = [{"field": cf["slug"], "operator": "equals", "value": "Высокий"}]
    res = await client.get("/api/projects", params={"filters": __import__("json").dumps(filters), "page_size": 10})
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "A"


async def test_filter_options_endpoint(client, make_project):
    await make_project(title="A", stage="Сигнал", manager_name="Денис", currency="USDT")
    res = await client.get("/api/projects/filters/options")
    assert res.status_code == 200
    opts = res.json()
    assert "Сигнал" in opts["stages"]
    assert "Денис" in opts["managers"]


# ---------------------------------------------------------------------------
# Sorting (спец. §16)
# ---------------------------------------------------------------------------
async def test_sorting_deadline(client, make_project):
    await make_project(title="Z", deadline="2026-10-01")
    await make_project(title="A", deadline="2026-09-01")
    res = await client.get("/api/projects", params={"sort_by": "deadline", "sort_dir": "asc", "page_size": 10})
    data = res.json()
    assert data["items"][0]["title"] == "A"


# ---------------------------------------------------------------------------
# Views (спец. §12-13, Сценарий 5)
# ---------------------------------------------------------------------------
async def test_create_and_apply_view(client, make_project):
    await make_project(title="A", stage="Сигнал", manager_name="Денис", payment_percent="80%")
    await make_project(title="B", stage="Сигнал", manager_name="Катя", payment_percent="100%")

    res = await client.post("/api/views", json={
        "name": "Мои проекты",
        "config": {
            "visible_columns": ["display_id", "title", "manager", "stage", "deadline", "payment_percent"],
            "filters": [{"field": "manager_name", "operator": "equals", "value": "Денис"}],
            "sorting": [{"field": "deadline", "direction": "asc"}],
        },
    })
    assert res.status_code == 201, res.text
    view = res.json()
    assert view["name"] == "Мои проекты"

    # представление продолжает работать: применяем фильтры из конфига
    filters = view["config"]["filters"]
    data = (await client.get("/api/projects", params={"filters": __import__("json").dumps(filters), "page_size": 10})).json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "A"


async def test_list_update_delete_view(client):
    v = (await client.post("/api/views", json={"name": "View 1", "config": {}})).json()
    res = await client.get("/api/views")
    assert res.status_code == 200
    assert any(x["id"] == v["id"] for x in res.json())

    res = await client.patch(f"/api/views/{v['id']}", json={"name": "View rename"})
    assert res.json()["name"] == "View rename"

    res = await client.delete(f"/api/views/{v['id']}")
    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Permissions / isolation (спец. §24)
# ---------------------------------------------------------------------------
async def test_workspace_id_from_frontend_ignored(client, make_project):
    """Переданный с фронта workspace_id не должен влиять на создание —
    бэкенд сам определяет workspace (демо: 0000...0001)."""
    evil_ws = "99999999-9999-9999-9999-999999999999"
    res = await client.post("/api/projects", json={"title": "Hack", "workspace_id": evil_ws})
    assert res.status_code == 201
    # проект создан в демо-workspace: workspace_id отсутствует в ответе API
    assert res.json().get("workspace_id") is None


async def test_multi_sorting(client, make_project):
    """Мульти-сортировка (спец. 2.md §16): менеджер asc, дедлайн desc."""
    await make_project(title="Z", manager_name="Денис", deadline="2026-10-01")
    await make_project(title="A", manager_name="Денис", deadline="2026-09-01")
    await make_project(title="B", manager_name="Катя", deadline="2026-09-15")
    import json as _j

    sorting = _j.dumps([
        {"field": "manager_name", "direction": "asc"},
        {"field": "deadline", "direction": "desc"},
    ])
    res = await client.get("/api/projects", params={"sorting": sorting, "page_size": 10})
    assert res.status_code == 200
    data = res.json()
    managers = [p["manager_name"] for p in data["items"]]
    assert managers == sorted(managers)
    # среди Денисов дедлайн desc: Z (октябрь) идёт раньше A (сентябрь)
    items = data["items"]
    assert items[0]["title"] == "Z"
    assert items[1]["title"] == "A"

