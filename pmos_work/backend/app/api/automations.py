"""Notifications and Automation Engine API (stage 8)."""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..automation_engine import create_event, execute_event, project_risk
from ..automation_templates import TEMPLATES
from ..scheduler import run_deadline_tick
from ..database import get_db
from ..models import Automation, AutomationRun, DomainEvent, Notification, NotificationPreference, Project, ProjectTag, Task
from ..rbac import DEMO_WORKSPACE_ID, UserContext, check_workspace_access, require_permission
from ..schemas import NotificationPreferenceUpdate
from ..schemas import AutomationCreate, AutomationRead, AutomationRunRead, AutomationUpdate, EventRead, NotificationRead

router = APIRouter(tags=["automations"])

@router.get("/automation-templates")
async def automation_templates():
    return TEMPLATES

@router.get("/automations", response_model=list[AutomationRead])
async def list_automations(
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    return (await db.execute(select(Automation).where(Automation.workspace_id == ctx.workspace_id).order_by(Automation.created_at.desc()))).scalars().all()

@router.post("/automations", response_model=AutomationRead, status_code=201)
async def create_automation(
    payload: AutomationCreate,
    ctx: UserContext = Depends(require_permission("automation.create")),
    db: AsyncSession = Depends(get_db),
):
    row = Automation(workspace_id=ctx.workspace_id, **payload.model_dump())
    db.add(row); await db.commit(); await db.refresh(row); return row

@router.get("/automations/{automation_id}", response_model=AutomationRead)
async def get_automation(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Automation, automation_id)
    if not row or row.workspace_id != ctx.workspace_id: raise HTTPException(404, "Automation not found")
    check_workspace_access(ctx, row.workspace_id)
    return row

@router.patch("/automations/{automation_id}", response_model=AutomationRead)
async def update_automation(
    automation_id: uuid.UUID,
    payload: AutomationUpdate,
    ctx: UserContext = Depends(require_permission("automation.update")),
    db: AsyncSession = Depends(get_db),
):
    row = await get_automation(automation_id, ctx, db)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); await db.refresh(row); return row

@router.delete("/automations/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.delete")),
    db: AsyncSession = Depends(get_db),
):
    row = await get_automation(automation_id, ctx, db); await db.delete(row); await db.commit()

@router.post("/automations/{automation_id}/enable", response_model=AutomationRead)
async def enable_automation(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.update")),
    db: AsyncSession = Depends(get_db),
):
    row = await get_automation(automation_id, ctx, db); row.enabled = True; await db.commit(); await db.refresh(row); return row

@router.post("/automations/{automation_id}/disable", response_model=AutomationRead)
async def disable_automation(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.update")),
    db: AsyncSession = Depends(get_db),
):
    row = await get_automation(automation_id, ctx, db); row.enabled = False; await db.commit(); await db.refresh(row); return row

@router.post("/automations/{automation_id}/test")
async def test_automation(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    row = await get_automation(automation_id, ctx, db)
    projects = (await db.execute(select(Project).where(Project.workspace_id == DEMO_WORKSPACE_ID, Project.archived_at.is_(None)))).scalars().all()
    matched = [p for p in projects if await _matches(p, row.conditions or {})]
    return {"matched": [{"id": p.id, "display_id": p.display_id, "title": p.title} for p in matched], "would_create_tasks": sum(1 for a in row.actions if a.get("type") == "create_task") * len(matched), "would_notify": sum(1 for a in row.actions if a.get("type") == "notification") * len(matched)}

async def _matches(project: Project, conditions: dict) -> bool:
    from ..automation_engine import _condition_matches
    return await _condition_matches(project, conditions)

@router.get("/automations/{automation_id}/runs", response_model=list[AutomationRunRead])
async def automation_runs(
    automation_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    await get_automation(automation_id, ctx, db)
    return (await db.execute(select(AutomationRun).where(AutomationRun.automation_id == automation_id).order_by(AutomationRun.started_at.desc()).limit(100))).scalars().all()

@router.get("/automation-runs/{run_id}", response_model=AutomationRunRead)
async def get_automation_run(
    run_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(AutomationRun, run_id)
    if not row: raise HTTPException(404, "Automation run not found")
    automation = await db.get(Automation, row.automation_id)
    if automation is not None:
        check_workspace_access(ctx, automation.workspace_id)
    return row

@router.get("/events/{event_id}/chain")
async def event_chain(
    event_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(DomainEvent, event_id)
    if not event or event.workspace_id != ctx.workspace_id: raise HTTPException(404, "Event not found")
    check_workspace_access(ctx, event.workspace_id)
    rows = (await db.execute(select(DomainEvent).where(DomainEvent.chain_id == event.chain_id).order_by(DomainEvent.created_at))).scalars().all()
    return [EventRead.model_validate(row) for row in rows]

@router.post("/events", response_model=EventRead, status_code=201)
async def ingest_event(
    payload: dict,
    ctx: UserContext = Depends(require_permission("automation.create")),
    db: AsyncSession = Depends(get_db),
):
    required = ("type", "entity_type")
    if any(not payload.get(k) for k in required): raise HTTPException(422, "type and entity_type are required")
    event = await create_event(db, ctx.workspace_id, payload["type"], payload["entity_type"], payload.get("entity_id"), payload.get("payload", {}), deduplication_key=payload.get("deduplication_key"))
    await execute_event(db, event); await db.commit(); await db.refresh(event); return event

@router.get("/tasks/overdue")
async def overdue_tasks(
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Task).join(Project, Project.id == Task.project_id).where(
            Project.workspace_id == ctx.workspace_id,
            Task.due_date < date.today(),
            Task.status.notin_(("DONE", "CANCELLED")),
        )
    )).scalars().all()
    return [{"id": row.id, "title": row.title, "project_id": row.project_id, "due_date": row.due_date} for row in rows]

@router.get("/events", response_model=list[EventRead])
async def list_events(
    limit: int = 100,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    return (await db.execute(select(DomainEvent).where(DomainEvent.workspace_id == ctx.workspace_id).order_by(DomainEvent.created_at.desc()).limit(min(limit, 500)))).scalars().all()

@router.get("/events/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("automation.read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(DomainEvent, event_id)
    if not row or row.workspace_id != ctx.workspace_id: raise HTTPException(404, "Event not found")
    return row

@router.get("/notifications/grouped")
async def grouped_notifications(
    limit: int = 100,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Notification).where(Notification.workspace_id == ctx.workspace_id).order_by(Notification.created_at.desc()).limit(min(limit, 500)))).scalars().all()
    grouped = {}
    for row in rows:
        key = str(row.entity_id or row.id)
        item = grouped.setdefault(key, {"entity_id": row.entity_id, "title": row.title, "items": [], "unread": 0, "latest_at": row.created_at})
        item["items"].append(NotificationRead.model_validate(row).model_dump(mode="json"))
        item["unread"] += int(not row.read)
        if row.created_at and row.created_at > item["latest_at"]: item["latest_at"] = row.created_at
    return list(grouped.values())

@router.get("/projects/{project_id}/tags")
async def project_tags(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.workspace_id != ctx.workspace_id: raise HTTPException(404, "Project not found")
    check_workspace_access(ctx, project.workspace_id)
    rows = (await db.execute(select(ProjectTag.tag).where(ProjectTag.project_id == project_id).order_by(ProjectTag.tag))).scalars().all()
    return {"project_id": project_id, "tags": list(rows)}

@router.get("/notifications", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.workspace_id == ctx.workspace_id)
    if unread_only: stmt = stmt.where(Notification.read.is_(False))
    return (await db.execute(stmt.order_by(Notification.created_at.desc()).limit(min(limit, 500)))).scalars().all()

@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Notification, notification_id)
    if not row or row.workspace_id != ctx.workspace_id: raise HTTPException(404, "Notification not found")
    row.read = True; await db.commit(); await db.refresh(row); return row

@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Notification).where(Notification.workspace_id == ctx.workspace_id, Notification.read.is_(False)))).scalars().all()
    for row in rows: row.read = True
    await db.commit(); return {"updated": len(rows)}

@router.get("/notification-preferences")
async def get_notification_preferences(
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(NotificationPreference).where(NotificationPreference.workspace_id == ctx.workspace_id))).scalars().all()
    return rows

@router.put("/notification-preferences")
async def set_notification_preferences(
    payload: NotificationPreferenceUpdate,
    ctx: UserContext = Depends(require_permission("task.update")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(select(NotificationPreference).where(
        NotificationPreference.workspace_id == ctx.workspace_id,
        NotificationPreference.user_id.is_(None),
        NotificationPreference.category == payload.category,
    ))
    if row is None:
        row = NotificationPreference(workspace_id=ctx.workspace_id, category=payload.category)
        db.add(row)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    await db.commit(); await db.refresh(row)
    return row

@router.post("/automations/tick")
async def automation_tick(
    ctx: UserContext = Depends(require_permission("automation.update")),
    db: AsyncSession = Depends(get_db),
):
    """Run one idempotent deadline scheduler tick."""
    return {"emitted": await run_deadline_tick(db)}

@router.post("/risk/refresh")
async def refresh_risks(
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    projects = (await db.execute(select(Project).where(Project.workspace_id == ctx.workspace_id, Project.archived_at.is_(None)))).scalars().all()
    return {"items": [{"project_id": p.id, "display_id": p.display_id, "risk_level": project_risk(p)[0], "reason": project_risk(p)[1]} for p in projects]}

@router.get("/risk/projects/{project_id}")
async def project_risk_endpoint(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.workspace_id != ctx.workspace_id: raise HTTPException(404, "Project not found")
    check_workspace_access(ctx, project.workspace_id)
    level, reason = project_risk(project)
    return {"project_id": project.id, "display_id": project.display_id, "risk_level": level, "reason": reason}
