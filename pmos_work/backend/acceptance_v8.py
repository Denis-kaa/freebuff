"""Stage 8 live acceptance checks for the demo workspace."""
import asyncio
import uuid
from datetime import date, timedelta

import httpx

BASE = "http://127.0.0.1:8010/api"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        suffix = uuid.uuid4().hex[:8]
        project = await c.post("/projects", json={
            "title": f"Stage8 acceptance {suffix}",
            "stage": "Активный",
            "deadline": (date.today() + timedelta(days=1)).isoformat(),
            "payment_percent": "50%",
            "risk_level": "Нет",
        })
        assert project.status_code == 201, project.text
        p = project.json()
        pid = p["id"]

        automation = await c.post("/automations", json={
            "name": f"Stage8 deadline {suffix}",
            "trigger_type": "project.deadline_approaching",
            "conditions": {"conditions": [{"field": "stage", "operator": "not_equals", "value": "Завершён"}]},
            "actions": [
                {"type": "create_task", "title": f"Проверить дедлайн {suffix}"},
                {"type": "notification", "title": "Дедлайн близко", "message": p["title"], "priority": "HIGH"},
            ],
        })
        assert automation.status_code == 201, automation.text
        aid = automation.json()["id"]

        event_body = {"type": "project.deadline_approaching", "entity_type": "project", "entity_id": pid, "deduplication_key": f"stage8:{suffix}"}
        first = await c.post("/events", json=event_body)
        assert first.status_code == 201, first.text
        second = await c.post("/events", json=event_body)
        assert second.status_code == 201, second.text

        tasks = await c.get(f"/projects/{pid}/tasks")
        assert tasks.status_code == 200, tasks.text
        assert len([x for x in tasks.json() if x["title"] == f"Проверить дедлайн {suffix}"]) == 1, tasks.text

        notifications = await c.get("/notifications", params={"unread_only": "true"})
        assert notifications.status_code == 200, notifications.text
        matching = [x for x in notifications.json() if x["message"] == p["title"]]
        assert len(matching) == 1, notifications.text
        await c.post(f"/notifications/{matching[0]['id']}/read")

        risk = await c.get(f"/risk/projects/{pid}")
        assert risk.status_code == 200, risk.text
        assert risk.json()["risk_level"] in {"HIGH", "MEDIUM", "LOW"}, risk.text

        dry = await c.post(f"/automations/{aid}/test")
        assert dry.status_code == 200, dry.text
        assert "matched" in dry.json()

        failure = await c.post("/automations", json={
            "name": f"Stage8 failure {suffix}", "trigger_type": "project.deadline_approaching",
            "actions": [{"type": "unsupported_action"}],
        })
        assert failure.status_code == 201, failure.text
        failure_event = await c.post("/events", json={**event_body, "deduplication_key": f"stage8:failure:{suffix}"})
        assert failure_event.status_code == 201, failure_event.text
        runs = await c.get(f"/automations/{failure.json()['id']}/runs")
        assert runs.status_code == 200, runs.text
        assert runs.json()[0]["status"] == "FAILED", runs.text

        print("stage8 acceptance: 10 checks passed")


if __name__ == "__main__":
    asyncio.run(main())
