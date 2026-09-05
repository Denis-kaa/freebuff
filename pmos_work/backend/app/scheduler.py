"""Cooperative scheduler for deadline automations.

Called by an external timer/systemd timer; it does not create a long-lived
worker inside the API process.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .automation_engine import create_event, execute_event
from .models import Automation, Project, Task

WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def run_deadline_tick(db: AsyncSession, workspace_id: uuid.UUID = WORKSPACE_ID, today: date | None = None) -> int:
    today = today or date.today()
    automations = (await db.execute(select(Automation).where(
        Automation.workspace_id == workspace_id,
        Automation.enabled.is_(True),
        Automation.trigger_type.in_(("project.deadline_approaching", "project.deadline_overdue", "task.overdue")),
    ))).scalars().all()
    if not automations:
        return 0
    projects = (await db.execute(select(Project).where(
        Project.workspace_id == workspace_id, Project.archived_at.is_(None), Project.deadline.is_not(None)
    ))).scalars().all()
    emitted = 0
    for task in (await db.execute(select(Task).join(Project, Task.project_id == Project.id).where(Task.due_date < today, Task.status.notin_(("DONE", "CANCELLED")), Project.workspace_id == workspace_id))).scalars().all():
        for automation in automations:
            if automation.trigger_type != "task.overdue": continue
            key = f"task-overdue:{automation.id}:{task.id}:{today.isoformat()}"
            event = await create_event(db, workspace_id, "task.overdue", "task", task.id, {"due_date": task.due_date.isoformat(), "project_id": str(task.project_id)}, deduplication_key=key)
            await execute_event(db, event); emitted += 1
    for project in projects:
        for automation in automations:
            config = automation.trigger_config or {}
            offset = int(config.get("days", 1))
            target = today + timedelta(days=offset)
            trigger = "project.deadline_approaching" if offset >= 0 else "project.deadline_overdue"
            if project.deadline != target or automation.trigger_type != trigger:
                continue
            key = f"deadline:{automation.id}:{project.id}:{today.isoformat()}"
            event = await create_event(db, workspace_id, trigger, "project", project.id,
                                       {"deadline": project.deadline.isoformat(), "offset_days": offset},
                                       deduplication_key=key)
            await execute_event(db, event)
            emitted += 1
    await db.commit()
    return emitted
