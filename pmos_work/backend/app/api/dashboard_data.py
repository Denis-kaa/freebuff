"""Widget Data API (4.md §22, §24).

Отдельный endpoint на виджет — каждый получает ровно свои данные, фильтрация
на стороне сервера (§45). Архитектура масштабируется: новый виджет = новый
endpoint + Data Provider, Dashboard Engine не трогается.
"""
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..calendar_service import service as calendar_service
from ..database import get_db
from ..dashboard_services import (
    activity_data,
    compact_projects_data,
    deadlines_data,
    finance_data,
    kpi_data,
    production_data,
    risks_data,
    today_tasks_data,
)
from ..rbac import DEMO_WORKSPACE_ID, UserContext, require_permission
from ..services import get_custom_fields_map, load_custom_values
from ..schemas import (
    ActivityData,
    CalendarData,
    CalendarDay,
    CalendarEventItem,
    DeadlineItem,
    DeadlinesData,
    FinanceData,
    FinanceItem,
    KpiData,
    ProductionCountItem,
    ProductionData,
    RiskItem,
    RisksData,
    TodayTaskItem,
    TodayTasksData,
)

router = APIRouter(prefix="/dashboard-data", tags=["dashboard-data"])



@router.get("/calendar", response_model=CalendarData)
async def calendar(
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = None,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Календарь (4.md §25 + 5.md §28): ЕДИНЫЙ Calendar Engine.

    Один движок -> все представления: Dashboard Widget и страница /calendar
    используют один и тот же CalendarService (5.md §28).
    """
    from datetime import datetime, timedelta, timezone as _tz

    if from_ is None:
        from_ = date.today().replace(day=1)
    if to is None:
        nxt = (from_.replace(day=28) + timedelta(days=4)).replace(day=1)
        to = nxt - timedelta(days=1)
    frm_dt = datetime(from_.year, from_.month, from_.day, tzinfo=_tz.utc)
    to_dt = datetime(to.year, to.month, to.day, 23, 59, 59, tzinfo=_tz.utc)

    items = await calendar_service.get_events(db, ctx.workspace_id, frm_dt, to_dt)
    by_day: dict[str, list] = {}
    for e in items:
        day = e["start_at"][:10]
        by_day.setdefault(day, []).append({
            "event_date": day,
            "event_type": e["type"],
            "title": e["title"],
            "project_id": e["project_id"],
            "project_item_id": e["project_item_id"],
            "project_display_id": (e.get("metadata") or {}).get("project_display_id"),
            "project_title": (e.get("metadata") or {}).get("project_title"),
            "source": "custom" if e["source_type"] == "custom" else "derived",
        })
    parsed = [
        CalendarDay(date=d, events=[CalendarEventItem(**ev) for ev in events])
        for d, events in sorted(by_day.items())
    ]
    return CalendarData(from_=from_, to=to, days=parsed)


@router.get("/tasks", response_model=TodayTasksData)
async def tasks(
    max_items: int = Query(10, ge=1, le=100),
    manager: Optional[str] = None,
    ctx: UserContext = Depends(require_permission("task.read")),
    db: AsyncSession = Depends(get_db),
):
    """Что сделать сегодня (4.md §12): просроченные, сегодня, next actions."""
    data = await today_tasks_data(db, ctx.workspace_id, max_items, manager)
    return TodayTasksData(
        overdue=[TodayTaskItem(**t) for t in data["overdue"]],
        today=[TodayTaskItem(**t) for t in data["today"]],
        next_actions=[TodayTaskItem(**t) for t in data["next_actions"]],
    )


@router.get("/deadlines", response_model=DeadlinesData)
async def deadlines(
    days: int = Query(7, ge=1, le=90),
    include_items: bool = True,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Ближайшие дедлайны (4.md §13): проекты + отгрузки позиций."""
    items = await deadlines_data(db, ctx.workspace_id, days, include_items)
    return DeadlinesData(period_days=days, items=[DeadlineItem(**i) for i in items])


@router.get("/risks", response_model=RisksData)
async def risks(
    levels: str = Query("Высокий,Критический", description="Через запятую"),
    show_overdue: bool = True,
    show_production: bool = True,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Срочные риски (4.md §14)."""
    level_list = [w.strip() for w in levels.split(",") if w.strip()]
    items = await risks_data(db, ctx.workspace_id, level_list, show_overdue, show_production)
    return RisksData(items=[RiskItem(**i) for i in items])


@router.get("/production", response_model=ProductionData)
async def production(
    ctx: UserContext = Depends(require_permission("production.read")),
    db: AsyncSession = Depends(get_db),
):
    """Производство: счётчики Project Items по стадиям."""
    data = await production_data(db, ctx.workspace_id)
    return ProductionData(
        items=[ProductionCountItem(**i) for i in data["items"]],
        total_items=data["total_items"],
    )


@router.get("/finance", response_model=FinanceData)
async def finance(
    ctx: UserContext = Depends(require_permission("finance.read")),
    db: AsyncSession = Depends(get_db),
):
    """Финансы: неоплаченные, авансы, доплаты, валюты (RBAC §15)."""
    data = await finance_data(db, ctx.workspace_id)
    return FinanceData(
        unpaid=[FinanceItem(**i) for i in data["unpaid"]],
        unpaid_count=data["unpaid_count"],
        advances_due=[FinanceItem(**i) for i in data["advances_due"]],
        finals_due=[FinanceItem(**i) for i in data["finals_due"]],
        currencies=data["currencies"],
    )


@router.get("/activity", response_model=ActivityData)
async def activity(
    limit: int = Query(20, ge=1, le=100),
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Последние изменения (Audit Activity, единый лог)."""
    items = await activity_data(db, ctx.workspace_id, limit)
    return ActivityData(items=items)


@router.get("/kpi", response_model=KpiData)
async def kpi(
    metric: str = "active_projects",
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Универсальный счётчик (4.md §40-widget), источник настраивается."""
    return KpiData(**await kpi_data(db, ctx.workspace_id, metric))


@router.get("/projects")
async def projects(
    limit: int = Query(10, ge=1, le=50),
    view_id: Optional[uuid.UUID] = Query(None),
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """Компактный список проектов для Projects-виджета.

    view_id делает сохранённое View источником данных (7.md §45-46).
    """
    return await compact_projects_data(db, ctx.workspace_id, limit, view_id=view_id)


@router.get("/ai-summary")
async def ai_summary(
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """AI Widget (4.md §40): архитектура подготовлена.

    Сейчас Data Provider — детерминированная агрегация. Позже тот же endpoint
    сможет обращаться к AI-провайдеру, не меняя Dashboard Engine.
    """
    from datetime import date as _date

    today = _date.today()
    deadline_counts = await deadlines_data(db, ctx.workspace_id, 7, include_items=True)
    risks = await risks_data(db, ctx.workspace_id, ["Высокий", "Критический"], True, True)
    tomorrow = today + timedelta(days=1)
    tomorrow_deadlines = [d for d in deadline_counts if d["date"] == tomorrow]
    critical = [r for r in risks if (r["risk_level"] or "").lower().find("критич") >= 0]
    attention = len(risks)
    return {
        "summary": (
            f"{len(deadline_counts)} дедлайнов на ближайшие 7 дней. "
            f"{len(tomorrow_deadlines)} — завтра. "
            f"{len(critical)} проект(ов) с критическим риском, "
            f"{attention} требуют внимания."
        ),
        "today": today.isoformat(),
        "counts": {
            "deadlines_7d": len(deadline_counts),
            "deadlines_tomorrow": len(tomorrow_deadlines),
            "critical": len(critical),
            "attention": attention,
        },
    }