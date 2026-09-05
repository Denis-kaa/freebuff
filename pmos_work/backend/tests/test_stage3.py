"""Тесты этапа 3 (3.md §32): Project Items, Production, Tasks, Documents, Events, locking."""

import json as _json
import uuid


# ---------------------------------------------------------------------------
# Project Items (3.md §5-6)
# ---------------------------------------------------------------------------
async def test_create_project_item(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.post("/api/project-items", json={
        "project_id": p["id"], "name": "Худи", "quantity": 100,
        "tech_specs": "Шелкография, 300 гр/м2",
    })
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["name"] == "Худи"
    assert item["quantity"] == 100
    assert item["version"] == 1


async def test_list_items_by_project(client, make_project):
    p = await make_project(title="Wazzup")
    await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи", "quantity": 100})
    await client.post("/api/project-items", json={"project_id": p["id"], "name": "Кепка", "quantity": 50})
    res = await client.get("/api/project-items", params={"project_id": p["id"]})
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    names = {i["name"] for i in items}
    assert names == {"Худи", "Кепка"}


async def test_update_project_item(client, make_project):
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи", "quantity": 100})).json()
    res = await client.patch(f"/api/project-items/{item['id']}", json={"quantity": 150})
    assert res.status_code == 200
    assert res.json()["quantity"] == 150


async def test_delete_project_item(client, make_project):
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи"})).json()
    res = await client.delete(f"/api/project-items/{item['id']}")
    assert res.status_code == 204
    assert (await client.get(f"/api/project-items/{item['id']}")).status_code == 404


# ---------------------------------------------------------------------------
# Production statuses (3.md §7-8, §23)
# ---------------------------------------------------------------------------
async def test_production_update(client, make_project):
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={
        "project_id": p["id"], "name": "Худи", "signal_required": True,
        "mockup_status": "В работе",
    })).json()
    res = await client.patch(f"/api/project-items/{item['id']}/production", json={
        "mockup_status": "Сдан",
        "signal_status": "Отгружен",
        "signal_feedback": "Ожидается",
        "batch_status": "Производство",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["mockup_status"] == "Сдан"
    assert body["signal_status"] == "Отгружен"
    assert body["batch_status"] == "Производство"
    # версия инкрементировалась
    assert body["version"] == item["version"] + 1


# ---------------------------------------------------------------------------
# Production timeline (3.md §9)
# ---------------------------------------------------------------------------
async def test_timeline_derived(client, make_project):
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={
        "project_id": p["id"], "name": "Худи", "signal_required": True,
        "mockup_status": "Сдан", "signal_status": "Согласован", "batch_status": "Производство",
    })).json()
    res = await client.get(f"/api/projects/{p['id']}/timeline", params={"item_id": item["id"]})
    assert res.status_code == 200
    stages = res.json()["stages"]
    codes = [s["code"] for s in stages]
    assert codes == ["mockup", "signal", "signal_fb", "batch", "batch_fb", "shipment"]
    status_by_code = {s["code"]: s["status"] for s in stages}
    assert status_by_code["mockup"] in ("done", "active")
    assert status_by_code["batch"] in ("done", "active")


# ---------------------------------------------------------------------------
# Tasks (3.md §10-12)
# ---------------------------------------------------------------------------
async def test_create_task_with_item(client, make_project):
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи"})).json()
    res = await client.post(f"/api/projects/{p['id']}/tasks", json={
        "title": "Получить ОС по сигналу",
        "assignee_name": "Денис",
        "priority": "HIGH",
        "due_date": "2026-09-01",
        "project_item_id": item["id"],
        "status": "TODO",
    })
    assert res.status_code == 201, res.text
    task = res.json()
    assert task["title"] == "Получить ОС по сигналу"
    assert task["project_item_id"] == item["id"]
    assert task["assignee_name"] == "Денис"


async def test_task_item_must_belong_to_project(client, make_project):
    p1 = await make_project(title="A")
    p2 = await make_project(title="B")
    item_p2 = (await client.post("/api/project-items", json={"project_id": p2["id"], "name": "Худи"})).json()
    res = await client.post(f"/api/projects/{p1['id']}/tasks", json={
        "title": "X", "project_item_id": item_p2["id"],
    })
    assert res.status_code == 422


async def test_toggle_task_done(client, make_project):
    p = await make_project(title="Wazzup")
    task = (await client.post(f"/api/projects/{p['id']}/tasks", json={"title": "Сделать"})).json()
    res = await client.patch(f"/api/projects/{p['id']}/tasks/{task['id']}", json={"status": "DONE"})
    assert res.status_code == 200
    assert res.json()["status"] == "DONE"
    assert res.json()["completed_at"] is not None


# ---------------------------------------------------------------------------
# Documents (3.md §15-16)
# ---------------------------------------------------------------------------
async def test_create_document(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.post(f"/api/projects/{p['id']}/documents", json={
        "document_type": "SIGNAL", "status": "SENT",
        "file_name": "signal.pdf", "comment": "отправлен",
    })
    assert res.status_code == 201, res.text
    doc = res.json()
    assert doc["document_type"] == "SIGNAL"
    assert doc["status"] == "SENT"
    assert doc["file_name"] == "signal.pdf"


async def test_document_types_validation(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.post(f"/api/projects/{p['id']}/documents", json={
        "document_type": "BOGUS", "status": "SENT",
    })
    assert res.status_code == 422


async def test_update_document_status(client, make_project):
    p = await make_project(title="Wazzup")
    doc = (await client.post(f"/api/projects/{p['id']}/documents", json={
        "document_type": "BATCH", "status": "PREPARED",
    })).json()
    res = await client.patch(f"/api/projects/{p['id']}/documents/{doc['id']}", json={"status": "SIGNED"})
    assert res.status_code == 200
    assert res.json()["status"] == "SIGNED"


# ---------------------------------------------------------------------------
# Events (3.md §18-19)
# ---------------------------------------------------------------------------
async def test_derived_events(client, make_project):
    p = await make_project(title="Wazzup", deadline="2026-09-10", advance_date="2026-08-26")
    res = await client.get(f"/api/projects/{p['id']}/events")
    assert res.status_code == 200
    events = res.json()
    types = {e["event_type"] for e in events}
    assert "DEADLINE" in types
    assert "PAYMENT_ADVANCE" in types
    # производные события имеют source=derived и id=None
    derived = [e for e in events if e["source"] == "derived"]
    assert len(derived) >= 2


# ---------------------------------------------------------------------------
# Activity (3.md §20) — единый Audit Log
# ---------------------------------------------------------------------------
async def test_activity_records(client, make_project):
    p = await make_project(title="Wazzup")
    await client.patch(f"/api/projects/{p['id']}", json={"stage": "Тираж"})
    res = await client.get(f"/api/projects/{p['id']}/activity")
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(a["action"] in ("create", "update") for a in items)


# ---------------------------------------------------------------------------
# Custom Fields для Project Items (3.md §26)
# ---------------------------------------------------------------------------
async def test_item_custom_field_value(client, make_project):
    cf = (await client.post("/api/custom-fields", json={
        "name": "Плотность ткани", "field_type": "TEXT", "entity_type": "PROJECT_ITEM",
    })).json()
    p = await make_project(title="Wazzup")
    item = (await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи"})).json()
    res = await client.put(f"/api/project-items/{item['id']}/custom-values", json={
        "values": {cf["slug"]: "300 гр/м2"},
    })
    assert res.status_code == 200
    got = (await client.get(f"/api/project-items/{item['id']}")).json()
    assert got["custom_values"][cf["slug"]] == "300 гр/м2"


# ---------------------------------------------------------------------------
# Summary / Health (3.md §21-22)
# ---------------------------------------------------------------------------
async def test_project_summary(client, make_project):
    p = await make_project(title="Wazzup", deadline="2026-09-10", payment_percent="80%")
    await client.post("/api/project-items", json={"project_id": p["id"], "name": "Худи"})
    res = await client.get(f"/api/projects/{p['id']}/summary")
    assert res.status_code == 200
    s = res.json()
    assert s["display_id"] == p["display_id"]
    assert s["items_count"] == 1
    assert s["health"] in ("healthy", "attention", "at_risk", "critical")
    assert s["open_tasks_count"] >= 0


# ---------------------------------------------------------------------------
# Optimistic locking (3.md §25)
# ---------------------------------------------------------------------------
async def test_project_optimistic_locking(client, make_project):
    p = await make_project(title="Wazzup")
    # менеджер B обновил проект (версия -> 2)
    await client.patch(f"/api/projects/{p['id']}", json={"stage": "Сигнал"})
    # менеджер A сохраняет старую версию (1) -> 409
    res = await client.patch(f"/api/projects/{p['id']}", json={"stage": "Макет", "version": 1})
    assert res.status_code == 409
    # с актуальной версией — успех
    fresh = (await client.get(f"/api/projects/{p['id']}")).json()
    res = await client.patch(f"/api/projects/{p['id']}", json={"stage": "Макет", "version": fresh["version"]})
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Permissions / isolation (3.md §24)
# ---------------------------------------------------------------------------
async def test_item_foreign_project_rejected(client, make_project):
    p = await make_project(title="Wazzup")
    res = await client.post("/api/project-items", json={"project_id": str(uuid.uuid4()), "name": "X"})
    assert res.status_code == 404