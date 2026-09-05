"""Calendar & Events Engine (5.md).

Единый движок для всех событий системы:
минимальный набор типов + архитектура адаптеров (5.md §3, §34-35):

    Projects / Tasks / Items / Payments / Production / Documents / Custom
        ↓ Event Adapters (Project, Task, Production, Payment, Document, Custom)
        ↓ CalendarService (агрегация + dedup)
        ↓ Unified CalendarEvents -> /calendar/*  (а также /dashboard-data/*)

Принцип (5.md §1): НЕ создаём копии данных ради календаря. Источник истины —
Project.deadline, Task.due_date и т.д. CalendarService строит унифицированное
представление (Unified Calendar Event, 5.md §2).

Deterministic event ID (5.md §36): системные события имеют стабильный id
"source_type:id:kind" — один и тот же source не может попасть дважды.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CalendarEvent as CalendarEventModel
from .models import Document, Project, ProjectItem, Task

UTC = timezone.utc

# Пользовательские группы типов для фильтров (5.md §11)
TYPE_GROUPS = {
    "deadline": ("PROJECT_DEADLINE",),
    "task": ("TASK_DEADLINE",),
    "payment": ("PAYMENT_ADVANCE", "PAYMENT_FINAL"),
    "production": ("PRODUCTION", "SIGNAL_FEEDBACK", "BATCH_READY", "BATCH_SHIPMENT"),
    "shipment": ("SIGNAL_SHIPMENT", "BATCH_SHIPMENT"),
    "document": ("DOCUMENT", "DOCUMENT_DEADLINE"),
    "custom": ("CUSTOM", "REMINDER", "MEETING", "CALL", "OTHER"),
    "meeting": ("MEETING", "CALL", "REMINDER"),
}

DONE_WORDS = ("сдан", "готов", "утвержд", "согласован", "отгружен", "принято")


def _utc(dt: datetime) -> datetime:
    """Нормализация в UTC (5.md §38): naive считаем UTC (по контракту API)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def deterministic_id(kind: str, obj_id: uuid.UUID) -> str:
    """Стабильный id системного события (5.md §36): task:UUID:deadline."""
    return f"{kind}:{obj_id}"


def decode_deterministic(event_id: str):
    """Разбирает deterministic id -> (kind, obj_id). None если не системный."""
    parts = event_id.split(":")
    if len(parts) != 2:
        return None
    kind, raw = parts
    try:
        return kind, uuid.UUID(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Unified Calendar Event
# ---------------------------------------------------------------------------
def make_event(
    kind: str,
    obj_id: uuid.UUID,
    event_type: str,
    start_at: datetime,
    title: str,
    source_type: str,
    source_id: str,
    *,
    all_day: bool = True,
    end_at: Optional[datetime] = None,
    description: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    project_item_id: Optional[uuid.UUID] = None,
    task_id: Optional[uuid.UUID] = None,
    document_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    metadata: Optional[dict] = None,
    project_display_id: Optional[str] = None,
    project_title: Optional[str] = None,
    manager_name: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> dict:
    """Строит унифицированное событие (5.md §2)."""
    return {
        "id": deterministic_id(kind, obj_id),
        "type": event_type,
        "title": title,
        "description": description,
        "start_at": _utc(start_at).isoformat(),
        "end_at": _utc(end_at).isoformat() if end_at else None,
        "all_day": all_day,
        "project_id": str(project_id) if project_id else None,
        "project_item_id": str(project_item_id) if project_item_id else None,
        "task_id": str(task_id) if task_id else None,
        "document_id": str(document_id) if document_id else None,
        "source_type": source_type,
        "source_id": source_id,
        "status": status,
        "priority": priority,
        "metadata": {**(metadata or {}), "project_display_id": project_display_id, "project_title": project_title,
                     "manager_name": manager_name, "risk_level": risk_level},
    }


# ---------------------------------------------------------------------------
# CalendarContext: общий фильтр для всех адаптеров (5.md §11-16)
# ---------------------------------------------------------------------------
class CalendarContext:
    def __init__(
        self,
        from_dt: datetime,
        to_dt: datetime,
        project_id: Optional[str] = None,
        manager: Optional[str] = None,
        risk_only: bool = False,
        q: Optional[str] = None,
    ):
        self.from_dt = from_dt
        self.to_dt = to_dt
        self.project_id = project_id
        self.manager = manager
        self.risk_only = risk_only
        self.q = (q or "").strip().lower()

    def in_range(self, d: Optional[date | datetime]) -> bool:
        if d is None:
            return False
        dt = d if isinstance(d, datetime) else _day_start(d)
        return self.from_dt <= _utc(dt) <= self.to_dt

    def matches_project(self, p: Optional[Project], *, search: bool = True) -> bool:
        if p is None:
            return self.project_id is None and self.manager is None and not self.risk_only and (not search or not self.q)
        if self.project_id and str(p.id) != self.project_id:
            return False
        if self.manager and (p.manager_name or "").lower() != self.manager.lower():
            return False
        if self.risk_only:
            risk = (p.risk_level or "").lower()
            if not any(w in risk for w in ("высок", "критич")):
                return False
        if search and self.q:
            hay = f"{p.display_id} {p.title} {p.client_legal_name or ''} {p.stage or ''}".lower()
            if self.q not in hay:
                return False
        return True

    def matches_text(self, *fields: Optional[str]) -> bool:
        if not self.q:
            return True
        return any(self.q in (f or "").lower() for f in fields)


# ---------------------------------------------------------------------------
# Adapters (5.md §34-35): EventAdapterInterface { get_events(session, ctx, workspace_id) }
# ---------------------------------------------------------------------------
class ProjectEventAdapter:
    """Дедлайны, авансы, доплаты (source = Project, 5.md §3, §7)."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        rows = (await db.execute(
            select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        )).scalars().all()
        out = []
        for p in rows:
            if not ctx.matches_project(p):
                continue
            if p.deadline and ctx.in_range(p.deadline):
                out.append(make_event(
                    "project", p.id, "PROJECT_DEADLINE", _day_start(p.deadline),
                    "Дедлайн проекта", "project", str(p.id),
                    project_id=p.id, status="deadline",
                    project_display_id=p.display_id, project_title=p.title,
                    manager_name=p.manager_name, risk_level=p.risk_level,
                    metadata={"payment_percent": p.payment_percent},
                ))
        return out


class PaymentEventAdapter:
    """Авансы и доплаты (5.md §3, §9, §19)."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        rows = (await db.execute(
            select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        )).scalars().all()
        out = []
        for p in rows:
            if not ctx.matches_project(p):
                continue
            if p.advance_date and ctx.in_range(p.advance_date):
                out.append(make_event(
                    "payment-advance", p.id, "PAYMENT_ADVANCE", _day_start(p.advance_date),
                    "Аванс", "payment", str(p.id),
                    project_id=p.id, priority="HIGH",
                    project_display_id=p.display_id, project_title=p.title,
                    manager_name=p.manager_name, risk_level=p.risk_level,
                    metadata={"payment_percent": p.payment_percent, "currency": p.currency},
                ))
            if p.final_payment_date and ctx.in_range(p.final_payment_date):
                out.append(make_event(
                    "payment-final", p.id, "PAYMENT_FINAL", _day_start(p.final_payment_date),
                    "Доплата", "payment", str(p.id),
                    project_id=p.id, priority="HIGH",
                    project_display_id=p.display_id, project_title=p.title,
                    manager_name=p.manager_name, risk_level=p.risk_level,
                    metadata={"payment_percent": p.payment_percent, "currency": p.currency},
                ))
        return out


class TaskEventAdapter:
    """Сроки задач (5.md §3, §18). Завершённые задачи НЕ дают событий-дедлайнов."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        projects = (await db.execute(
            select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        )).scalars().all()
        p_by_id = {p.id: p for p in projects}
        if not projects:
            return []
        rows = (await db.execute(
            select(Task).where(
                Task.project_id.in_([p.id for p in projects]),
                Task.status.notin_(["DONE", "CANCELLED"]),
                Task.due_date.isnot(None),
            )
        )).scalars().all()
        out = []
        for t in rows:
            p = p_by_id.get(t.project_id)
            if p and not ctx.matches_project(p, search=False):
                continue
            if not ctx.in_range(t.due_date):
                continue
            if ctx.q and not (ctx.matches_text(t.title, t.description) or ctx.matches_project(p, search=True)):
                continue
            it_name = None
            if t.project_item_id:
                item = await db.get(ProjectItem, t.project_item_id)
                it_name = item.name if item else None
            out.append(make_event(
                "task", t.id, "TASK_DEADLINE", _day_start(t.due_date),
                t.title, "task", str(t.id),
                all_day=True,
                project_id=t.project_id, task_id=t.id,
                project_item_id=t.project_item_id,
                status=t.status, priority=t.priority,
                project_display_id=p.display_id if p else None,
                project_title=p.title if p else None,
                manager_name=(t.assignee_name or (p.manager_name if p else None)),
                risk_level=p.risk_level if p else None,
                metadata={"assignee_name": t.assignee_name, "project_item_name": it_name},
            ))
        return out


class ProductionEventAdapter:
    """Отгрузки сигналов и производственные даты Project Items (5.md §3, §20)."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        projects = (await db.execute(
            select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        )).scalars().all()
        p_by_id = {p.id: p for p in projects}
        if not projects:
            return []
        rows = (await db.execute(
            select(ProjectItem).where(ProjectItem.project_id.in_([p.id for p in projects]))
        )).scalars().all()
        out = []
        for it in rows:
            p = p_by_id.get(it.project_id)
            if p and not ctx.matches_project(p, search=False):
                continue
            if ctx.q and not (ctx.matches_text(
                it.name, it.signal_status, it.mockup_status, it.batch_status
            ) or ctx.matches_project(p, search=True)):
                continue
            if it.signal_shipping_date and ctx.in_range(it.signal_shipping_date):
                out.append(make_event(
                    "production", it.id, "SIGNAL_SHIPMENT", _day_start(it.signal_shipping_date),
                    f"Отгрузка сигнала: {it.name}", "project_item", str(it.id),
                    all_day=True,
                    project_id=it.project_id, project_item_id=it.id,
                    project_display_id=p.display_id if p else None,
                    project_title=p.title if p else None,
                    risk_level=p.risk_level if p else None,
                    metadata={"item_name": it.name, "quantity": it.quantity,
                              "signal_status": it.signal_status, "mockup_status": it.mockup_status},
                ))
            # производственные события: макет/тираж в работе — по статусам, без даты не выводим
        return out


class DocumentEventAdapter:
    """Даты документооборота (5.md §3 DOCUMENT, §48)."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        projects = (await db.execute(
            select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        )).scalars().all()
        p_by_id = {p.id: p for p in projects}
        if not projects:
            return []
        rows = (await db.execute(
            select(Document).where(Document.project_id.in_([p.id for p in projects]), Document.doc_date.isnot(None))
        )).scalars().all()
        out = []
        for d in rows:
            p = p_by_id.get(d.project_id)
            if p and not ctx.matches_project(p, search=False):
                continue
            if ctx.q and not (ctx.matches_text(d.file_name, d.comment, d.document_type) or ctx.matches_project(p, search=True)):
                continue
            if not ctx.in_range(d.doc_date):
                continue
            out.append(make_event(
                "document", d.id, "DOCUMENT", _day_start(d.doc_date),
                d.file_name or f"Документ ({d.document_type})", "document", str(d.id),
                all_day=True,
                project_id=d.project_id, project_item_id=d.project_item_id, document_id=d.id,
                status=d.status, project_display_id=p.display_id if p else None,
                project_title=p.title if p else None, risk_level=p.risk_level if p else None,
                metadata={"document_type": d.document_type, "comment": d.comment},
            ))
        return out


class CustomEventAdapter:
    """Ручные события из таблицы calendar_events (5.md §21-22)."""

    async def get_events(self, db: AsyncSession, workspace_id: uuid.UUID, ctx: CalendarContext) -> list[dict]:
        stmt = select(CalendarEventModel).where(
            CalendarEventModel.workspace_id == workspace_id,
            CalendarEventModel.start_at >= ctx.from_dt,
            CalendarEventModel.start_at <= ctx.to_dt,
        )
        if ctx.project_id:
            stmt = stmt.where(CalendarEventModel.project_id == uuid.UUID(ctx.project_id))
        rows = (await db.execute(stmt)).scalars().all()
        out = []
        for e in rows:
            p = None
            if e.project_id:
                p = await db.get(Project, e.project_id)
                if p and not ctx.matches_project(p, search=False):
                    continue
            if ctx.q and not (ctx.matches_text(e.title, e.description) or ctx.matches_project(p, search=True)):
                continue
            out.append(make_event(
                "custom", e.id, e.event_type, e.start_at, e.title, "custom", str(e.id),
                all_day=e.all_day, end_at=e.end_at, description=e.description,
                project_id=e.project_id, project_item_id=e.project_item_id, task_id=e.task_id,
                status="custom", project_display_id=p.display_id if p else None,
                project_title=p.title if p else None, risk_level=p.risk_level if p else None,
                metadata={"created_by": e.created_by},
            ))
        return out


# ---------------------------------------------------------------------------
# CalendarService
# ---------------------------------------------------------------------------
class CalendarService:
    """Собирает события из всех источников в Unified CalendarEvents (5.md §34).

    Новый источник = новый Adapter (get_events), Service не переписывается (§35).
    """

    def __init__(self):
        self.adapters = [
            ProjectEventAdapter(),
            PaymentEventAdapter(),
            TaskEventAdapter(),
            ProductionEventAdapter(),
            DocumentEventAdapter(),
            CustomEventAdapter(),
        ]

    async def get_events(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        from_dt: datetime,
        to_dt: datetime,
        types: Optional[list[str]] = None,
        **ctx_kwargs,
    ) -> list[dict]:
        """Агрегирует события диапазона (5.md §33). Фильтрация — на бэкенде."""
        ctx = CalendarContext(_utc(from_dt), _utc(to_dt), **ctx_kwargs)
        allow = self._allowed_types(types)
        items: list[dict] = []
        for adapter in self.adapters:
            events = await adapter.get_events(db, workspace_id, ctx)
            if allow:
                events = [e for e in events if e["type"] in allow]
            items.extend(events)
        # dedup по deterministic id (5.md §36)
        seen: dict[str, dict] = {}
        for e in items:
            seen.setdefault(e["id"], e)
        result = list(seen.values())
        result.sort(key=lambda e: e["start_at"])
        return result

    @staticmethod
    def _allowed_types(types: Optional[list[str]]) -> Optional[set[str]]:
        if not types:
            return None
        allowed: set[str] = set()
        for t in types:
            if t in TYPE_GROUPS:
                allowed.update(TYPE_GROUPS[t])
            else:
                allowed.add(t.upper())
        return allowed

    @staticmethod
    def _type_pass(event_type: str, allowed: set[str]) -> bool:
        return event_type in allowed

    async def today(self, db: AsyncSession, workspace_id: uuid.UUID, **ctx_kwargs) -> dict:
        """Что сегодня + просроченное (5.md §30-31)."""
        today = date.today()
        start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        end = start + timedelta(days=1) - timedelta(microseconds=1)

        today_events = await self.get_events(db, workspace_id, start, end, **ctx_kwargs)
        overdue_start = start - timedelta(days=90)
        overdue_all = await self.get_events(
            db, workspace_id, overdue_start, end - timedelta(microseconds=1), **ctx_kwargs
        )
        # просрочено = началось раньше сегодня (и источник активен — адаптеры уже отфильтровали завершённые)
        overdue = [e for e in overdue_all if e["start_at"] < start.isoformat()]

        def group(ev_type: str) -> list[dict]:
            return [e for e in today_events if e["type"] == ev_type]

        return {
            "date": today.isoformat(),
            "overdue": overdue,
            "events": today_events,
            "tasks": [e for e in today_events if e["type"] == "TASK_DEADLINE"],
            "deadlines": group("PROJECT_DEADLINE"),
            "payments": [e for e in today_events if e["type"] in ("PAYMENT_ADVANCE", "PAYMENT_FINAL")],
            "production": [e for e in today_events if e["type"] in ("SIGNAL_SHIPMENT", "PRODUCTION", "BATCH_SHIPMENT")],
            "documents": [e for e in today_events if e["type"] == "DOCUMENT"],
            "custom": [e for e in today_events if e["type"] in TYPE_GROUPS["custom"]],
            "next_actions": await self._next_actions(db, workspace_id, project_id=ctx_kwargs.get("project_id")),
        }

    async def _next_actions(self, db, workspace_id, project_id=None) -> list[dict]:
        stmt = select(Project).where(Project.workspace_id == workspace_id, Project.archived_at.is_(None))
        if project_id:
            stmt = stmt.where(Project.id == uuid.UUID(project_id))
        rows = (await db.execute(stmt)).scalars().all()
        out = []
        for p in rows:
            if not (p.next_action or "").strip():
                continue
            out.append({
                "id": None, "title": p.next_action, "project_id": str(p.id),
                "project_display_id": p.display_id, "project_title": p.title,
                "due_date": p.next_action_date.isoformat() if p.next_action_date else None,
                "assignee_name": p.manager_name, "priority": "HIGH", "status": "NEXT_ACTION",
            })
        return out

    async def upcoming(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        from_dt: datetime,
        to_dt: datetime,
        types: Optional[list[str]] = None,
        **ctx_kwargs,
    ) -> list[dict]:
        return await self.get_events(db, workspace_id, from_dt, to_dt, types, **ctx_kwargs)

    async def event_by_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, event_id: str
    ) -> Optional[dict]:
        """Одно событие по id: custom — из таблицы, system — из источника (5.md §45)."""
        # custom
        try:
            uid = uuid.UUID(event_id)
        except ValueError:
            uid = None
        if uid is not None:
            ev = await db.get(CalendarEventModel, uid)
            if ev is not None and ev.workspace_id == workspace_id:
                p = await db.get(Project, ev.project_id) if ev.project_id else None
                return make_event(
                    "custom", ev.id, ev.event_type, ev.start_at, ev.title, "custom", str(ev.id),
                    all_day=ev.all_day, end_at=ev.end_at, description=ev.description,
                    project_id=ev.project_id, project_item_id=ev.project_item_id, task_id=ev.task_id,
                    status="custom",
                    project_display_id=p.display_id if p else None,
                    project_title=p.title if p else None,
                    risk_level=p.risk_level if p else None,
                    metadata={"created_by": ev.created_by},
                )
            return None

        # системное по deterministic id (5.md §36)
        dec = decode_deterministic(event_id)
        if dec is None:
            return None
        kind, obj_id = dec

        def project_meta(p: Optional[Project]) -> dict:
            return {"project_display_id": p.display_id if p else None,
                    "project_title": p.title if p else None,
                    "manager_name": p.manager_name if p else None,
                    "risk_level": p.risk_level if p else None}

        if kind in ("project", "payment-advance", "payment-final"):
            p = await db.get(Project, obj_id)
            if p is None or p.workspace_id != workspace_id or p.archived_at:
                return None
            field = {"project": "deadline", "payment-advance": "advance_date", "payment-final": "final_payment_date"}[kind]
            etype = {"project": "PROJECT_DEADLINE", "payment-advance": "PAYMENT_ADVANCE", "payment-final": "PAYMENT_FINAL"}[kind]
            title = {"project": "Дедлайн проекта", "payment-advance": "Аванс", "payment-final": "Доплата"}[kind]
            d = getattr(p, field)
            if not d:
                return None
            return make_event(
                kind, p.id, etype, _day_start(d), title,
                "payment" if kind.startswith("payment") else "project", str(p.id),
                project_id=p.id, priority="HIGH" if kind.startswith("payment") else None,
                **project_meta(p),
            )
        if kind == "task":
            t = await db.get(Task, obj_id)
            if t is None or t.status in ("DONE", "CANCELLED") or not t.due_date:
                return None
            p = await db.get(Project, t.project_id) if t.project_id else None
            return make_event(
                "task", t.id, "TASK_DEADLINE", _day_start(t.due_date), t.title,
                "task", str(t.id), project_id=t.project_id, task_id=t.id,
                project_item_id=t.project_item_id, status=t.status, priority=t.priority,
                **project_meta(p), metadata={"assignee_name": t.assignee_name},
            )
        if kind == "production":
            it = await db.get(ProjectItem, obj_id)
            if it is None or not it.signal_shipping_date:
                return None
            p = await db.get(Project, it.project_id)
            return make_event(
                "production", it.id, "SIGNAL_SHIPMENT", _day_start(it.signal_shipping_date),
                f"Отгрузка сигнала: {it.name}", "project_item", str(it.id),
                project_id=it.project_id, project_item_id=it.id,
                **project_meta(p), metadata={"item_name": it.name},
            )
        if kind == "document":
            d = await db.get(Document, obj_id)
            if d is None or d.doc_date is None:
                return None
            p = await db.get(Project, d.project_id)
            return make_event(
                "document", d.id, "DOCUMENT", _day_start(d.doc_date),
                d.file_name or f"Документ ({d.document_type})", "document", str(d.id),
                project_id=d.project_id, project_item_id=d.project_item_id, document_id=d.id,
                status=d.status, **project_meta(p),
            )
        return None


service = CalendarService()