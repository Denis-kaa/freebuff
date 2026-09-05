"""Widget Data Services (4.md §22, §24, §45).

Каждый виджет получает РОВНО свои данные — запросы фильтруются на стороне
бэкенда/БД, фронтенд ничего не фильтрует сам. Нет «endpoint, который возвращает
всё приложение» (§24). Widget UI не пишет SQL — только Widget Data Hook → API →
Service → Database.
"""
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog, Project, ProjectItem, Task
from .services import get_custom_fields_map

# Ключевые слова «статус завершён» для производственных стадий (совпадают с services.production_timeline)
DONE_WORDS = ("сдан", "готов", "утвержд", "согласован", "отгружен", "принято")
ACTIVE_WORDS = ("в работе", "правк", "производств")


def _is_done(value: Optional[str]) -> bool:
    return bool(value) and any(w in value.lower() for w in DONE_WORDS)


def _is_active(value: Optional[str]) -> bool:
    return bool(value) and any(w in value.lower() for w in ACTIVE_WORDS)


async def _non_archived_projects(db: AsyncSession, workspace_id: uuid.UUID):
    rows = await db.execute(
        select(Project).where(
            Project.workspace_id == workspace_id,
            Project.archived_at.is_(None),
        )
    )
    return rows.scalars().all()


# ---------------------------------------------------------------------------
# Calendar (4.md §25): дедлайны, задачи, оплаты, производство, next actions
# ---------------------------------------------------------------------------
async def calendar_data(
    db: AsyncSession, workspace_id: uuid.UUID, from_: date, to: date
) -> list[dict]:
    days: dict[date, list[dict]] = {}
    today = date.today()
    if from_ is None:
        from_ = today.replace(day=1)
    if to is None:
        nxt = (from_.replace(day=28) + timedelta(days=4)).replace(day=1)
        to = nxt - timedelta(days=1)
    if from_ > to:
        from_, to = to, from_

    def push(d: Optional[date], ev: dict):
        if not d or d < from_ or d > to:
            return
        days.setdefault(d, []).append(ev)

    projects = await _non_archived_projects(db, workspace_id)
    p_by_id = {p.id: p for p in projects}

    for p in projects:
        push(p.deadline, {
            "event_date": p.deadline, "event_type": "DEADLINE", "title": "Дедлайн проекта",
            "project_id": p.id, "project_display_id": p.display_id, "project_title": p.title,
        })
        push(p.advance_date, {
            "event_date": p.advance_date, "event_type": "PAYMENT_ADVANCE", "title": "Аванс",
            "project_id": p.id, "project_display_id": p.display_id, "project_title": p.title,
        })
        push(p.final_payment_date, {
            "event_date": p.final_payment_date, "event_type": "PAYMENT_FINAL", "title": "Доплата",
            "project_id": p.id, "project_display_id": p.display_id, "project_title": p.title,
        })
        push(p.next_action_date, {
            "event_date": p.next_action_date, "event_type": "NEXT_ACTION",
            "title": p.next_action or "Следующее действие",
            "project_id": p.id, "project_display_id": p.display_id, "project_title": p.title,
        })

    # задачи (открытые)
    task_rows = await db.execute(
        select(Task).where(
            Task.project_id.in_([p.id for p in projects]),
            Task.status.notin_(["DONE", "CANCELLED"]),
            Task.due_date.isnot(None),
        )
    )
    for t in task_rows.scalars().all():
        pp = p_by_id.get(t.project_id)
        push(t.due_date, {
            "event_date": t.due_date, "event_type": "TASK", "title": t.title,
            "project_id": t.project_id,
            "project_display_id": pp.display_id if pp else None,
            "project_title": pp.title if pp else None,
            "task_id": str(t.id),
        })

    # производственные события позиций (отгрузки сигналов)
    if projects:
        item_rows = await db.execute(
            select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
        )
        for it in item_rows.scalars().all():
            pp = p_by_id.get(it.project_id)
            push(it.signal_shipping_date, {
                "event_date": it.signal_shipping_date, "event_type": "SIGNAL_SHIPMENT",
                "title": f"Отгрузка сигнала: {it.name}",
                "project_id": it.project_id, "project_item_id": it.id,
                "project_display_id": pp.display_id if pp else None,
                "project_title": pp.title if pp else None,
            })

    return [{"date": d.isoformat(), "events": events} for d, events in sorted(days.items())]


# ---------------------------------------------------------------------------
# Today Tasks (4.md §12): просроченные + сегодня + next actions
# ---------------------------------------------------------------------------
async def today_tasks_data(
    db: AsyncSession, workspace_id: uuid.UUID, max_items: int, manager: Optional[str]
) -> dict:
    today = date.today()
    projects = await _non_archived_projects(db, workspace_id)
    p_by_id = {p.id: p for p in projects}

    stmt = select(Task).where(
        Task.project_id.in_([p.id for p in projects]),
        Task.status.notin_(["DONE", "CANCELLED"]),
        Task.due_date.isnot(None),
    )
    if manager:
        stmt = stmt.where(Task.assignee_name == manager)
    task_rows = (await db.execute(stmt)).scalars().all()

    overdue, today_list = [], []
    for t in task_rows:
        pp = p_by_id.get(t.project_id)
        base = {
            "id": t.id, "title": t.title, "project_id": t.project_id,
            "project_display_id": pp.display_id if pp else None,
            "project_title": pp.title if pp else None,
            "due_date": t.due_date, "assignee_name": t.assignee_name,
            "priority": t.priority, "status": t.status,
        }
        if t.due_date < today:
            overdue.append(base)
        elif t.due_date == today:
            today_list.append(base)
    overdue.sort(key=lambda t: t["due_date"] or today)
    today_list.sort(key=lambda t: t["priority"] or "")

    # Next Action проектов (4.md §12, §36)
    next_actions = []
    for p in projects:
        if not (p.next_action or "").strip():
            continue
        next_actions.append({
            "id": None, "title": p.next_action, "project_id": p.id,
            "project_display_id": p.display_id, "project_title": p.title,
            "due_date": p.next_action_date, "assignee_name": p.manager_name,
            "priority": "HIGH", "status": "NEXT_ACTION",
        })
    next_actions.sort(key=lambda x: (x["due_date"] is None, x["due_date"] or today))
    return {
        "overdue": overdue[:max_items],
        "today": today_list[:max_items],
        "next_actions": next_actions[:max_items],
    }


# ---------------------------------------------------------------------------
# Deadlines (4.md §13): проекты + позиции в пределах периода
# ---------------------------------------------------------------------------
async def deadlines_data(
    db: AsyncSession, workspace_id: uuid.UUID, period_days: int, include_items: bool = True
) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=period_days)
    projects = await _non_archived_projects(db, workspace_id)

    items_list: list[dict] = []
    for p in projects:
        if p.deadline and today <= p.deadline <= end:
            items_list.append({
                "id": p.id, "display_id": p.display_id, "title": p.title, "kind": "project",
                "date": p.deadline, "days_left": (p.deadline - today).days,
                "project_id": p.id, "risk_level": p.risk_level,
            })
    if include_items and projects:
        item_rows = await db.execute(
            select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
        )
        p_by_id = {p.id: p for p in projects}
        for it in item_rows.scalars().all():
            if it.signal_shipping_date and today <= it.signal_shipping_date <= end:
                pp = p_by_id[it.project_id]
                items_list.append({
                    "id": it.id, "display_id": pp.display_id,
                    "title": f"{it.name} — отгрузка сигнала", "kind": "item",
                    "date": it.signal_shipping_date, "days_left": (it.signal_shipping_date - today).days,
                    "project_id": it.project_id, "risk_level": pp.risk_level,
                })
    items_list.sort(key=lambda x: x["date"] or end)
    return items_list


# ---------------------------------------------------------------------------
# Risks (4.md §14): High/Critical, просроченные, проблемы производства
# ---------------------------------------------------------------------------
async def risks_data(
    db: AsyncSession, workspace_id: uuid.UUID, levels: list[str], show_overdue: bool, show_production: bool
) -> list[dict]:
    today = date.today()
    projects = await _non_archived_projects(db, workspace_id)
    risk_words = [w.lower() for w in (levels or ["Высокий", "Критический"])]

    out: list[dict] = []
    for p in projects:
        risk = (p.risk_level or "").lower()
        if any(w in risk for w in ("высок", "критич")):
            out.append({
                "id": p.id, "display_id": p.display_id, "title": p.title,
                "risk_level": p.risk_level, "risk_reason": p.risk_reason or "",
                "deadline": p.deadline, "kind": "risk", "reason": p.risk_reason or "Риск: " + (p.risk_level or ""),
            })
        elif show_overdue and p.deadline and p.deadline < today:
            out.append({
                "id": p.id, "display_id": p.display_id, "title": p.title,
                "risk_level": p.risk_level, "risk_reason": p.risk_reason or "",
                "deadline": p.deadline, "kind": "overdue",
                "reason": f"Дедлайн просрочен на {(today - p.deadline).days} дн.",
            })

    if show_production and projects:
        item_rows = await db.execute(
            select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
        )
        p_by_id = {p.id: p for p in projects}
        for it in item_rows.scalars().all():
            pp = p_by_id[it.project_id]
            reason = None
            if (it.signal_status or "").lower() and any(w in it.signal_status.lower() for w in ("отгружен", "производств")) and not (it.signal_feedback or "").strip():
                reason = f"{it.name}: нет ОС по сигналу"
            elif (it.mockup_status or "").lower() and "правк" in it.mockup_status.lower():
                reason = f"{it.name}: правки макета"
            elif (it.batch_status or "").lower() and any(w in it.batch_status.lower() for w in ("задерж", "стоп", "проблем")):
                reason = f"{it.name}: {it.batch_status}"
            if reason:
                out.append({
                    "id": pp.id, "display_id": pp.display_id, "title": pp.title,
                    "risk_level": pp.risk_level, "risk_reason": reason,
                    "deadline": pp.deadline, "kind": "production", "reason": reason,
                })
    return out


# ---------------------------------------------------------------------------
# Production (4.md §38): состояние Project Items по стадиям
# ---------------------------------------------------------------------------
async def production_data(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
    projects = await _non_archived_projects(db, workspace_id)
    if not projects:
        return {"items": [], "total_items": 0}
    item_rows = await db.execute(
        select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
    )
    items: list[ProjectItem] = item_rows.scalars().all()

    counts = {
        "mockups_in_work": 0, "signals_in_work": 0, "batch_in_work": 0,
        "shipments_pending": 0, "awaiting_feedback": 0, "mockup_revision": 0, "total": len(items),
    }
    for it in items:
        ms = it.mockup_status or ""
        ss = it.signal_status or ""
        bs = it.batch_status or ""
        if ms and not _is_done(ms):
            counts["mockups_in_work"] += 1
        if it.signal_required and ss and not _is_done(ss):
            counts["signals_in_work"] += 1
        if bs and _is_active(bs) and not _is_done(bs):
            counts["batch_in_work"] += 1
        if bs and any(w in bs.lower() for w in ("готов", "отгрузк", "собран")) and "отгруж" not in bs.lower():
            counts["shipments_pending"] += 1
        if ss and any(w in ss.lower() for w in ("отгружен", "производств")) and not (it.signal_feedback or "").strip():
            counts["awaiting_feedback"] += 1
        if "правк" in ms.lower():
            counts["mockup_revision"] += 1

    rows = [
        {"key": "mockups", "label": "Макеты в работе", "count": counts["mockups_in_work"], "status": "active"},
        {"key": "signals", "label": "Сигналы в работе", "count": counts["signals_in_work"], "status": "active"},
        {"key": "batch", "label": "Тираж в работе", "count": counts["batch_in_work"], "status": "active"},
        {"key": "shipments", "label": "Ожидают отгрузки", "count": counts["shipments_pending"], "status": "pending"},
        {"key": "feedback", "label": "Ожидают ОС", "count": counts["awaiting_feedback"], "status": "pending"},
        {"key": "revision", "label": "Правки макетов", "count": counts["mockup_revision"], "status": "active"},
    ]
    return {"items": [r for r in rows if r["count"] > 0] or rows[:1], "total_items": len(items)}


# ---------------------------------------------------------------------------
# Finance (4.md §12-widget): неоплаченные, авансы, доплаты, валюты
# ---------------------------------------------------------------------------
async def finance_data(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
    today = date.today()
    end7 = today + timedelta(days=7)
    projects = await _non_archived_projects(db, workspace_id)

    unpaid, advances, finals, currencies = [], [], [], {}
    for p in projects:
        pay = (p.payment_percent or "").replace("%", "").strip()
        if not pay:
            continue
        cur = p.currency or "RUB"
        item = {
            "id": p.id, "display_id": p.display_id, "title": p.title,
            "payment_percent": p.payment_percent, "currency": cur,
            "advance_date": p.advance_date, "final_payment_date": p.final_payment_date,
        }
        if pay != "100":
            unpaid.append(item)
            currencies[cur] = currencies.get(cur, 0) + 1
        if p.advance_date and today <= p.advance_date <= end7:
            advances.append(item)
        if p.final_payment_date and today <= p.final_payment_date <= end7:
            finals.append(item)

    unpaid.sort(key=lambda x: x["payment_percent"] or "0%")
    return {
        "unpaid": unpaid, "unpaid_count": len(unpaid),
        "advances_due": advances, "finals_due": finals,
        "currencies": currencies,
    }


# ---------------------------------------------------------------------------
# Activity (4.md §28-29): последние изменения из единого AuditLog
# ---------------------------------------------------------------------------
async def activity_data(db: AsyncSession, workspace_id: uuid.UUID, limit: int) -> list[dict]:
    rows = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc())
            .limit(max(1, min(limit or 20, 100)))
        )
    ).scalars().all()
    return [
        {
            "created_at": r.created_at.isoformat(), "user_name": r.user_name,
            "action": r.action, "entity_type": r.entity_type,
            "old_value": r.old_value, "new_value": r.new_value,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# KPI (4.md §40-widget): универсальный счётчик, источник настраивается
# ---------------------------------------------------------------------------
KPI_METRICS = {
    "active_projects": "Активные проекты",
    "open_tasks": "Открытые задачи",
    "deadlines_7d": "Дедлайны 7 дней",
    "overdue_projects": "Просроченные проекты",
    "unpaid_projects": "Не оплачены полностью",
    "no_payment": "Без оплаты",
    "signals_in_work": "Сигналы в работе",
    "batch_in_work": "Тираж в работе",
    "shipments_pending": "Ожидают отгрузки",
    "awaiting_feedback": "Ждут ОС",
    "mockup_revision": "Правки макетов",
    "advances_7d": "Авансы 7 дней",
    "finals_7d": "Доплаты 7 дней",
}


async def kpi_data(db: AsyncSession, workspace_id: uuid.UUID, metric: str) -> dict:
    today = date.today()
    end7 = today + timedelta(days=7)
    projects = await _non_archived_projects(db, workspace_id)

    def count_open_tasks() -> int:
        return 0  # заменяется ниже тяжёлым запросом

    if metric == "active_projects":
        value = len(projects)
    elif metric in ("open_tasks",):
        if projects:
            value = await db.scalar(
                select(func.count(Task.id)).where(
                    Task.project_id.in_([p.id for p in projects]),
                    Task.status.notin_(["DONE", "CANCELLED"]),
                )
            ) or 0
        else:
            value = 0
    elif metric == "deadlines_7d":
        value = sum(1 for p in projects if p.deadline and today <= p.deadline <= end7)
    elif metric == "overdue_projects":
        value = sum(1 for p in projects if p.deadline and p.deadline < today)
    elif metric == "unpaid_projects":
        value = sum(1 for p in projects if (p.payment_percent or "").replace("%", "").strip() not in ("", "100"))
    elif metric == "no_payment":
        value = sum(1 for p in projects if (p.payment_percent or "").replace("%", "").strip() in ("0", ""))
    elif metric in ("advances_7d", "finals_7d"):
        field = Project.advance_date if metric == "advances_7d" else Project.final_payment_date
        value = sum(1 for p in projects if getattr(p, field.name) and today <= getattr(p, field.name) <= end7)
    else:
        # production-метрики
        if not projects:
            value = 0
        else:
            item_rows = await db.execute(
                select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
            )
            items = item_rows.scalars().all()
            value = 0
            if metric == "signals_in_work":
                value = sum(1 for it in items if it.signal_required and (it.signal_status or "") and not _is_done(it.signal_status))
            elif metric == "batch_in_work":
                value = sum(1 for it in items if (it.batch_status or "") and _is_active(it.batch_status) and not _is_done(it.batch_status))
            elif metric == "shipments_pending":
                value = sum(1 for it in items if (it.batch_status or "") and any(w in it.batch_status.lower() for w in ("готов", "отгрузк", "собран")) and "отгруж" not in it.batch_status.lower())
            elif metric == "awaiting_feedback":
                value = sum(1 for it in items if (it.signal_status or "") and any(w in it.signal_status.lower() for w in ("отгружен", "производств")) and not (it.signal_feedback or "").strip())
            elif metric == "mockup_revision":
                value = sum(1 for it in items if "правк" in (it.mockup_status or "").lower())
    return {"metric": metric, "label": KPI_METRICS.get(metric, metric), "value": int(value)}


# ---------------------------------------------------------------------------
# Projects (compact) — 4.md §38-widget
# ---------------------------------------------------------------------------
async def compact_projects_data(db: AsyncSession, workspace_id: uuid.UUID, limit: int, view_id: Optional[uuid.UUID] = None) -> list[dict]:
    projects = await _non_archived_projects(db, workspace_id)
    if view_id:
        # View — универсальный источник виджета: применяем ту же серверную
        # конфигурацию фильтров/сортировки, что и /views/{id}/query.
        from .models import View
        from .query_builder import ENTITY_FIELDS, build_filter_tree, build_sorting
        view = await db.get(View, view_id)
        if view and view.workspace_id == workspace_id and view.entity_type == "projects":
            fields = ENTITY_FIELDS["projects"]
            cf_map = await get_custom_fields_map(db, workspace_id)
            cfg = view.config or {}
            expression = None
            tree = cfg.get("filters")
            if isinstance(tree, dict):
                from .schemas import FilterGroup
                tree = FilterGroup(**tree)
                expression = build_filter_tree(tree, fields, cf_map, Project.id)
                if expression is not None:
                    projects = [p for p in projects if p.id in (await db.scalars(select(Project.id).where(expression))).all()]
            order = build_sorting(cfg.get("sorting"), fields)
            if order:
                # Для компактного provider оставляем безопасный SQL order.
                stmt = select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None)).order_by(*order).limit(limit)
                if tree and expression is not None:
                    stmt = stmt.where(expression)
                projects = (await db.execute(stmt)).scalars().all()
    projects.sort(key=lambda p: (p.deadline is None, p.deadline or date.max))
    return [
        {
            "id": p.id, "display_id": p.display_id, "title": p.title,
            "stage": p.stage, "deadline": p.deadline, "risk_level": p.risk_level,
            "payment_percent": p.payment_percent, "manager_name": p.manager_name,
        }
        for p in projects[: max(1, min(limit or 10, 50))]
    ]