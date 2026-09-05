"""Calendar & Events API (5.md §45).

GET    /calendar/events          — события диапазона (фильтрация на бэкенде, §33)
GET    /calendar/today           — что сегодня + просроченное (§30-31)
GET    /calendar/upcoming        — предстоящие события (§32)
POST   /calendar/events          — ручное событие (§21)
GET    /calendar/events/{id}     — одно событие (custom или системное)
PATCH  /calendar/events/{id}     — custom; для системных — redirect в источник (§24-25)
DELETE /calendar/events/{id}     — custom; системные не удаляются

Права (5.md §44): каждая выборка скоуплена на workspace; подставить чужой
project_id нельзя — событие просто не попадёт в выдачу (фильтры адаптеров).
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..calendar_service import (
    CalendarEventModel,
    decode_deterministic,
    service as calendar,
)
from ..database import get_db
from ..models import Project, ProjectItem, Task
from ..schemas import (
    CalendarEventRead,
    CalendarEventsResponse,
    CalendarTodayRead,
    CustomEventCreate,
    CustomEventUpdate,
)
from ..services import add_audit

router = APIRouter(prefix="/calendar", tags=["calendar"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

CUSTOM_TYPES = {"REMINDER", "MEETING", "CALL", "OTHER", "CUSTOM"}


def _parse_dt(value: str, default: Optional[datetime] = None) -> datetime:
    raw = value.strip()
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        try:
            if len(raw) == 10:
                dt = datetime.combine(date.fromisoformat(raw), datetime.min.time())
            else:
                raise ValueError
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Неверная дата: {value}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_end(value: str, default: Optional[datetime] = None) -> datetime:
    """Конец диапазона: date-only -> конец дня (иначе событие в 09:00 потеряется,
    потому что to=2026-09-01 парсится как полночь)."""
    raw = value.strip()
    dt = _parse_dt(raw, default)
    if len(raw) == 10:  # YYYY-MM-DD без времени
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


async def _custom_event_or_404(db: AsyncSession, event_id: str):
    """Custom-событие по id (принимает как uuid, так и 'custom:{uuid}')."""
    raw = event_id
    dec = decode_deterministic(event_id)
    if dec and dec[0] == "custom":
        raw = str(dec[1])
    try:
        uid = uuid.UUID(raw)
    except ValueError:
        return None
    ev = await db.get(CalendarEventModel, uid)
    if ev is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    return ev


async def _system_event(db: AsyncSession, event_id: str):
    """Системное событие по deterministic id (5.md §36)."""
    return await calendar.event_by_id(db, DEMO_WORKSPACE_ID, event_id)


@router.get("/events", response_model=CalendarEventsResponse)
async def list_events(
    from_: Optional[str] = Query(None, alias="from", description="YYYY-MM-DD / ISO"),
    to: Optional[str] = Query(None, alias="to"),
    types: Optional[str] = Query(None, description="deadline,task,payment,shipment,document,custom..."),
    project_id: Optional[str] = None,
    manager: Optional[str] = None,
    risk_only: bool = False,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """События диапазона. Backend фильтрует диапазон — не грузим всю историю (§33)."""
    today = date.today()
    frm = _parse_dt(from_) if from_ else datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    to_dt = _parse_end(to) if to else (datetime(today.year, today.month + 1, 1, tzinfo=timezone.utc) if today.month < 12 else datetime(today.year + 1, 1, 1, tzinfo=timezone.utc))
    type_list = [t.strip().lower() for t in (types or "").split(",") if t.strip()] or None
    items = await calendar.get_events(
        db, DEMO_WORKSPACE_ID, frm, to_dt,
        types=type_list,
        project_id=project_id or None,
        manager=manager or None,
        risk_only=risk_only,
        q=q or None,
    )
    return CalendarEventsResponse(
        items=[CalendarEventRead(**e) for e in items],
        total=len(items),
        from_=frm.date().isoformat(),
        to=to_dt.date().isoformat(),
    )


@router.get("/today", response_model=CalendarTodayRead)
async def today_events(db: AsyncSession = Depends(get_db)):
    """Что сегодня (5.md §30) + просроченное (§31)."""
    data = await calendar.today(db, DEMO_WORKSPACE_ID)
    result = {k: v for k, v in data.items()}
    for key in ("overdue", "events", "tasks", "deadlines", "payments", "production", "documents", "custom"):
        result[key] = [CalendarEventRead(**e) for e in result[key]]
    return CalendarTodayRead(**result)


@router.get("/upcoming", response_model=CalendarEventsResponse)
async def upcoming_events(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None, alias="to", description="по умолчанию +30 дней"),
    types: Optional[str] = None,
    manager: Optional[str] = None,
    project: Optional[str] = Query(None, alias="project_id"),
    db: AsyncSession = Depends(get_db),
):
    """Предстоящие события (5.md §32)."""
    today = date.today()
    from datetime import timedelta
    frm = _parse_dt(from_) if from_ else datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    to_dt = _parse_end(to) if to else frm + timedelta(days=30)
    type_list = [t.strip().lower() for t in (types or "").split(",") if t.strip()] or None
    items = await calendar.upcoming(
        db, DEMO_WORKSPACE_ID, frm, to_dt, types=type_list, project_id=project or None, manager=manager or None
    )
    return CalendarEventsResponse(
        items=[CalendarEventRead(**e) for e in items],
        total=len(items),
        from_=frm.date().isoformat(),
        to=to_dt.date().isoformat(),
    )


@router.post("/events", response_model=CalendarEventRead, status_code=201)
async def create_event(payload: CustomEventCreate, db: AsyncSession = Depends(get_db)):
    """Ручное событие (5.md §21-22). Системные события тут не создаются."""
    if payload.event_type not in CUSTOM_TYPES:
        raise HTTPException(status_code=422, detail=f"Тип события должен быть одним из: {', '.join(sorted(CUSTOM_TYPES))}")
    # проекты/позиции/задачи должны существовать (права §44)
    if payload.project_id and not await db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Проект не найден")
    if payload.project_item_id and not await db.get(ProjectItem, payload.project_item_id):
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    if payload.task_id and not await db.get(Task, payload.task_id):
        raise HTTPException(status_code=404, detail="Задача не найдена")

    ev = CalendarEventModel(
        workspace_id=DEMO_WORKSPACE_ID,
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        start_at=payload.start_at,
        end_at=payload.end_at,
        all_day=payload.all_day,
        project_id=payload.project_id,
        project_item_id=payload.project_item_id,
        task_id=payload.task_id,
        created_by="Менеджер",
        recurrence_rule=payload.recurrence_rule,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "create", "calendar_event", ev.id, new_value={"title": ev.title})
    await db.commit()
    events = await calendar.get_events(
        db, DEMO_WORKSPACE_ID,
        ev.start_at.replace(hour=0, minute=0, second=0, microsecond=0),
        ev.start_at.replace(hour=23, minute=59, second=59, microsecond=999999),
    )
    # адаптер отдаёт id "custom:{uuid}" — сравниваем по source_id (uuid без префикса)
    item = next((e for e in events if e.get("source_id") == str(ev.id)), None)
    if item is None:
        item = {
            "id": str(ev.id), "type": ev.event_type, "title": ev.title,
            "description": ev.description, "start_at": ev.start_at.isoformat(),
            "end_at": ev.end_at.isoformat() if ev.end_at else None,
            "all_day": ev.all_day, "project_id": ev.project_id, "project_item_id": ev.project_item_id,
            "task_id": ev.task_id, "document_id": None, "source_type": "custom",
            "source_id": str(ev.id), "status": "custom", "priority": None, "metadata": {},
        }
    return CalendarEventRead(**item)


@router.get("/events/{event_id}", response_model=CalendarEventRead)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    custom = await _custom_event_or_404(db, event_id)
    if custom is not None:
        events = await calendar.get_events(
            db, DEMO_WORKSPACE_ID,
            custom.start_at.replace(hour=0, minute=0, second=0, microsecond=0),
            custom.start_at.replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        raw_id = event_id.rsplit(":", 1)[-1]  # "custom:{uuid}" | "{uuid}" -> uuid
        item = next((e for e in events if e.get("source_id") == raw_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        return CalendarEventRead(**item)
    system = await _system_event(db, event_id)
    if system is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    return CalendarEventRead(**system)


@router.patch("/events/{event_id}", response_model=CalendarEventRead)
async def update_event(event_id: str, payload: CustomEventUpdate, db: AsyncSession = Depends(get_db)):
    """Custom — обычное обновление. Системные — через источник (5.md §24-25)."""
    custom = await _custom_event_or_404(db, event_id)
    if custom is not None:
        for field in ("title", "description", "event_type", "start_at", "end_at", "all_day",
                      "project_id", "project_item_id", "task_id"):
            val = getattr(payload, field)
            if val is not None:
                if field in ("project_id", "project_item_id", "task_id") and val:
                    ref = await db.get({"project_id": Project, "project_item_id": ProjectItem, "task_id": Task}[field], val)
                    if ref is None:
                        raise HTTPException(status_code=404, detail="Связанная сущность не найдена")
                setattr(custom, field, val)
        await db.commit()
        await db.refresh(custom)
        await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "update", "calendar_event", custom.id, new_value={"title": custom.title})
        await db.commit()
        return await get_event(event_id, db)

    # Системное событие: перенаправляем изменение в источник (5.md §24-25)
    dec = decode_deterministic(event_id)
    if dec is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    kind, obj_id = dec
    if kind == "task" and payload.start_at:
        task = await db.get(Task, obj_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        task.due_date = payload.start_at.date()  # источник истины (5.md §25)
        await db.commit()
        await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "update", "task", task.id, new_value={"due_date": task.due_date.isoformat()})
        await db.commit()
        return await get_event(event_id, db)
    raise HTTPException(
        status_code=422,
        detail="Системное событие нельзя редактировать в календаре. Измените источник (проект/задачу).",
    )


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db)):
    custom = await _custom_event_or_404(db, event_id)
    if custom is None:
        raise HTTPException(
            status_code=422,
            detail="Системные события не удаляются через календарь — измените источник.",
        )
    await db.delete(custom)
    await db.commit()
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "delete", "calendar_event", custom.id)
    await db.commit()