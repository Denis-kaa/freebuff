"""События проекта и история активности (3.md §18-20)."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AuditLog, Project, ProjectEvent, ProjectItem
from ..schemas import (
    ActivityItemRead,
    ProductionTimelineRead,
    ProductionTimelineStage,
    ProjectActivityResponse,
    ProjectEventRead,
    ProjectSummaryRead,
)
from ..services import (
    compute_project_health,
    derive_events,
    production_timeline,
)
from ..services import NextActionService

router = APIRouter(prefix="/projects", tags=["events"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _project_or_404(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@router.get("/{project_id}/events", response_model=list[ProjectEventRead])
async def list_events(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Производные события (из дат Project/Item, §19) + ручные (таблица project_events)."""
    project = await _project_or_404(db, project_id)

    # Производные события — из дат, без дублирования данных
    items = (await db.execute(select(ProjectItem).where(ProjectItem.project_id == project_id))).scalars().all()
    derived = derive_events(project, list(items))

    # Ручные события
    manual_rows = (
        await db.execute(
            select(ProjectEvent)
            .where(ProjectEvent.project_id == project_id)
            .order_by(ProjectEvent.event_date)
        )
    ).scalars().all()

    combined: list[dict] = []
    for d in derived:
        combined.append({**d, "id": None, "source": "derived"})
    for m in manual_rows:
        combined.append({
            "id": m.id,
            "event_type": m.event_type,
            "event_date": m.event_date,
            "title": m.title,
            "description": m.description,
            "project_item_id": m.project_item_id,
            "source": m.source or "manual",
        })
    combined.sort(key=lambda e: (e.get("event_date") is None, e.get("event_date") or ""))
    return combined


@router.post("/{project_id}/events", response_model=ProjectEventRead, status_code=201)
async def create_event(
    project_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Ручное событие (например CUSTOM)."""
    await _project_or_404(db, project_id)
    from datetime import date as _date

    event = ProjectEvent(
        workspace_id=DEMO_WORKSPACE_ID,
        project_id=project_id,
        project_item_id=payload.get("project_item_id"),
        event_type=payload.get("event_type", "CUSTOM"),
        event_date=payload.get("event_date"),
        title=payload.get("title"),
        description=payload.get("description"),
        source="manual",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{project_id}/timeline", response_model=ProductionTimelineRead)
async def get_timeline(
    project_id: uuid.UUID, item_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db)
):
    """Timeline конкретной позиции (3.md §9). Вычисляется, не хранится."""
    await _project_or_404(db, project_id)
    if item_id is None:
        raise HTTPException(status_code=422, detail="Укажите item_id")
    item = await db.get(ProjectItem, item_id)
    if item is None or item.project_id != project_id:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    stages = production_timeline(item)
    return ProductionTimelineRead(
        stages=[ProductionTimelineStage(**s) for s in stages]
    )


@router.get("/{project_id}/summary", response_model=ProjectSummaryRead)
async def project_summary(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Резюме для Drawer: health, счётчики, предложенное следующее действие (3.md §21-22)."""
    from sqlalchemy import func as _func, or_

    from ..models import Task as _Task

    project = await _project_or_404(db, project_id)

    items = (await db.execute(select(ProjectItem).where(ProjectItem.project_id == project_id))).scalars().all()
    items_list = list(items)
    open_tasks = await db.scalar(
        select(_func.count(_Task.id)).where(
            _Task.project_id == project_id,
            _Task.status.notin_(["DONE", "CANCELLED"]),
        )
    )
    health, reasons = await compute_project_health(db, project, items_list, open_tasks or 0)
    suggested = NextActionService.suggest(items_list, project.next_action)
    return ProjectSummaryRead(
        project_id=project.id,
        display_id=project.display_id,
        title=project.title,
        risk_level=project.risk_level,
        deadline=project.deadline,
        payment_percent=project.payment_percent,
        currency=project.currency,
        next_action=project.next_action,
        suggested_next_action=suggested,
        items_count=len(items_list),
        open_tasks_count=open_tasks or 0,
        health=health,
        health_reasons=reasons,
    )


@router.get("/{project_id}/activity", response_model=ProjectActivityResponse)
async def project_activity(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """История — из единого AuditLog (3.md §20, НЕ вторая система)."""
    await _project_or_404(db, project_id)

    rows = (
        await db.execute(
            select(AuditLog)
            .where(or_(AuditLog.entity_id == project_id, AuditLog.entity_type == "project"))
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return ProjectActivityResponse(items=[ActivityItemRead.model_validate(r) for r in rows])