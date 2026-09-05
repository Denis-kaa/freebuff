"""Роутер /views (7.md §47-48).

GET    /views?entity_type=     — список
POST   /views                  — создать
GET    /views/{id}             — детали
PATCH  /views/{id}             — обновить (name/config/favorite/default/...)
DELETE /views/{id}             — удалить (конфигурация; данные НЕ удаляются §31)
POST   /views/{id}/duplicate   — копия (§29)
POST   /views/{id}/favorite    — закрепить (§27) {favorite: true|false}
POST   /views/{id}/default     — сделать по умолчанию (§28)
POST   /views/{id}/query       — Query Builder (§48): конфиг + temp filters → данные
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import CustomField, CustomFieldValue, Project, ProjectItem, Task, View
from ..query_builder import (
    ENTITY_FIELDS,
    build_filter_tree,
    apply_grouping,
    build_sorting,
)
from ..rbac import DEMO_WORKSPACE_ID, UserContext, check_workspace_access, require_permission
from ..schemas import FilterGroup, ViewCreate, ViewQueryRequest, ViewRead, ViewUpdate
from ..services import add_audit, get_custom_fields_map, load_custom_values

router = APIRouter(prefix="/views", tags=["views"])

CURRENT_USER = "Менеджер"

# Default Views (7.md §3): обычные View-строки, не зашиты во frontend.
DEFAULT_VIEWS: list[dict] = [
    {
        "name": "Все проекты",
        "entity_type": "projects",
        "view_type": "TABLE",
        "is_default": True,
        "config": {
            "visible_columns": ["display_id", "title", "client_legal_name", "manager_name",
                                "stage", "deadline", "payment_percent", "currency",
                                "risk_level", "next_action"],
            "sorting": [{"field": "deadline", "direction": "asc"}],
        },
    },
    {
        "name": "Мои проекты",
        "entity_type": "projects",
        "config": {
            "filters": FilterGroup(operator="AND", conditions=[
                {"field": "manager_name", "operator": "equals", "value": CURRENT_USER},
            ]).model_dump(),
            "visible_columns": ["display_id", "title", "manager_name", "stage", "deadline", "risk_level"],
        },
    },
    {
        "name": "Активные",
        "entity_type": "projects",
        "config": {
            "filters": FilterGroup(operator="AND", conditions=[
                {"field": "stage", "operator": "not_in", "value": ["Завершён", "Отменён"]},
            ]).model_dump(),
        },
    },
    {
        "name": "Завершённые",
        "entity_type": "projects",
        "config": {
            "filters": FilterGroup(operator="AND", conditions=[
                {"field": "stage", "operator": "equals", "value": "Завершён"},
            ]).model_dump(),
        },
    },
    {
        "name": "Высокий риск",
        "entity_type": "projects",
        "config": {
            "filters": FilterGroup(operator="AND", conditions=[
                {"field": "risk_level", "operator": "in", "value": ["Высокий", "Критический"]},
            ]).model_dump(),
            "sorting": [{"field": "deadline", "direction": "asc"}],
        },
    },
    {
        "name": "Ближайшие дедлайны",
        "entity_type": "projects",
        "config": {
            "filters": FilterGroup(operator="AND", conditions=[
                {"field": "deadline", "operator": "next_30_days"},
            ]).model_dump(),
            "sorting": [{"field": "deadline", "direction": "asc"}],
        },
    },
]


async def _view_or_404(
    session: AsyncSession, view_id: uuid.UUID, ctx: Optional[UserContext] = None
) -> View:
    view = await session.get(View, view_id)
    if view is None or view.workspace_id != DEMO_WORKSPACE_ID:
        raise HTTPException(status_code=404, detail="Представление не найдено")
    if ctx is not None:
        check_workspace_access(ctx, view.workspace_id)
    return view


def _to_read(v: View) -> dict:
    return {
        "id": str(v.id),
        "workspace_id": str(v.workspace_id),
        "name": v.name,
        "entity_type": v.entity_type,
        "view_type": v.view_type,
        "visibility": v.visibility,
        "is_default": v.is_default,
        "is_favorite": v.is_favorite,
        "created_by": v.created_by,
        "config": v.config or {},
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }


async def ensure_default_views(session: AsyncSession, workspace_id) -> None:
    """Создаёт стандартные View при первом обращении (7.md §3, идемпотентно)."""
    # Не выходим, если найден хотя бы один legacy-view: гарантируем наличие
    # каждого системного представления отдельно (идемпотентно).
    for spec in DEFAULT_VIEWS:
        cfg = dict(spec["config"])
        existing = await session.scalar(
            select(View).where(
                View.workspace_id == workspace_id,
                View.name == spec["name"],
            )
        )
        if existing:
            continue
        session.add(
            View(
                workspace_id=workspace_id,
                name=spec["name"],
                entity_type=spec["entity_type"],
                view_type=spec.get("view_type", "TABLE"),
                is_default=spec.get("is_default", False),
                config=cfg,
                created_by=None,
            )
        )
    await session.commit()


@router.get("")
async def list_views(
    entity_type: Optional[str] = Query(None),
    include_hidden: bool = Query(False),
    ctx: UserContext = Depends(require_permission("view.read")),
    db: AsyncSession = Depends(get_db),
):
    await ensure_default_views(db, DEMO_WORKSPACE_ID)
    stmt = select(View).where(View.workspace_id == DEMO_WORKSPACE_ID)
    if entity_type and entity_type != "all":
        stmt = stmt.where(View.entity_type == entity_type)
    stmt = stmt.order_by(View.is_favorite.desc(), View.is_default.desc(), View.created_at)
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_read(v) for v in rows]


@router.post("", response_model=ViewRead, status_code=201)
async def create_view(
    payload: ViewCreate,
    ctx: UserContext = Depends(require_permission("view.create")),
    db: AsyncSession = Depends(get_db),
):
    view = View(
        workspace_id=DEMO_WORKSPACE_ID,
        name=payload.name,
        entity_type=payload.entity_type,
        view_type=payload.view_type,
        visibility=payload.visibility,
        is_default=payload.is_default,
        is_favorite=payload.is_favorite,
        created_by=CURRENT_USER,
        config=payload.config,
    )
    db.add(view)
    await db.commit()
    await db.refresh(view)
    await add_audit(db, DEMO_WORKSPACE_ID, CURRENT_USER, "create", "view", view.id,
                    new_value={"name": view.name})
    await db.commit()
    return _to_read(view)


@router.get("/{view_id}")
async def get_view(
    view_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("view.read")),
    db: AsyncSession = Depends(get_db),
):
    return _to_read(await _view_or_404(db, view_id, ctx))


@router.patch("/{view_id}")
async def update_view(
    view_id: uuid.UUID,
    payload: ViewUpdate,
    ctx: UserContext = Depends(require_permission("view.update")),
    db: AsyncSession = Depends(get_db),
):
    view = await _view_or_404(db, view_id, ctx)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(view, field, value)
    await db.commit()
    await db.refresh(view)
    await add_audit(db, DEMO_WORKSPACE_ID, CURRENT_USER, "update", "view", view.id,
                    new_value={"field": list(changes.keys())})
    await db.commit()
    return _to_read(view)


@router.delete("/{view_id}", status_code=204)
async def delete_view(
    view_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("view.delete")),
    db: AsyncSession = Depends(get_db),
):
    view = await _view_or_404(db, view_id, ctx)
    await db.delete(view)
    await db.commit()
    await add_audit(db, DEMO_WORKSPACE_ID, CURRENT_USER, "delete", "view", view.id,
                    new_value={"name": view.name})
    await db.commit()


@router.post("/{view_id}/duplicate")
async def duplicate_view(
    view_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("view.create")),
    db: AsyncSession = Depends(get_db),
):
    """Копия представления (7.md §29). Новый id; данные не дублируются."""
    view = await _view_or_404(db, view_id, ctx)
    new_view = View(
        workspace_id=DEMO_WORKSPACE_ID,
        name=f"{view.name} — копия",
        entity_type=view.entity_type,
        view_type=view.view_type,
        visibility=view.visibility,
        created_by=CURRENT_USER,
        config=dict(view.config or {}),
    )
    db.add(new_view)
    await db.commit()
    await db.refresh(new_view)
    return _to_read(new_view)


@router.post("/{view_id}/favorite")
async def favorite_view(
    view_id: uuid.UUID,
    payload: dict,
    ctx: UserContext = Depends(require_permission("view.update")),
    db: AsyncSession = Depends(get_db),
):
    """Закрепить/открепить (7.md §27)."""
    view = await _view_or_404(db, view_id, ctx)
    view.is_favorite = bool(payload.get("favorite", True))
    await db.commit()
    await db.refresh(view)
    return _to_read(view)


@router.post("/{view_id}/default")
async def set_default_view(
    view_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("view.update")),
    db: AsyncSession = Depends(get_db),
):
    """Сделать представлением по умолчанию (7.md §28). Единственный default на entity_type."""
    view = await _view_or_404(db, view_id, ctx)
    current_defaults = (
        await db.execute(
            select(View).where(
                View.workspace_id == DEMO_WORKSPACE_ID,
                View.entity_type == view.entity_type,
                View.is_default.is_(True),
            )
        )
    ).scalars().all()
    for v in current_defaults:
        if v.id != view.id:
            v.is_default = False
    view.is_default = True
    await db.commit()
    await db.refresh(view)
    return _to_read(view)


# ---------------------------------------------------------------------------
# Query Builder (7.md §48): применение конфигурации + временных фильтров
# ---------------------------------------------------------------------------
@router.post("/{view_id}/query")
async def view_query(
    view_id: uuid.UUID,
    payload: Optional[ViewQueryRequest] = None,
    ctx: UserContext = Depends(require_permission("view.read")),
    db: AsyncSession = Depends(get_db),
):
    view = await _view_or_404(db, view_id, ctx)
    cfg = view.config or {}

    # temp filters поверх конфигурации (7.md §33)
    filters = payload.filters if (payload and payload.filters) else cfg.get("filters")
    if isinstance(filters, dict) and not isinstance(filters, FilterGroup):
        filters = FilterGroup(**filters)
    sorting = payload.sorting if (payload and payload.sorting is not None) else cfg.get("sorting")
    group_by = payload.group_by if (payload and payload.group_by) else cfg.get("group_by")
    search = payload.search if (payload and payload.search) else None
    page = payload.page if payload else 1
    page_size = payload.page_size if payload else 50

    return await _run_query(
        db, view.entity_type, filters, sorting, group_by, search,
        page, page_size,
    )


async def _run_query(
    db: AsyncSession,
    entity_type: str,
    filters,
    sorting,
    group_by: Optional[str],
    search: Optional[str],
    page: int,
    page_size: int,
) -> dict:
    fields = ENTITY_FIELDS.get(entity_type, ENTITY_FIELDS["projects"])
    cf_map = await get_custom_fields_map(db, DEMO_WORKSPACE_ID)  # PROJECT поля

    if entity_type == "projects":
        stmt = select(Project).where(Project.workspace_id == DEMO_WORKSPACE_ID)
        entity_id_col = Project.id
    elif entity_type == "tasks":
        stmt = select(Task).join(Project, Project.id == Task.project_id, isouter=True).where(
            (Project.id.is_(None)) | (Project.workspace_id == DEMO_WORKSPACE_ID)
        )
        entity_id_col = Task.id
        cf_map = await get_custom_fields_map(db, DEMO_WORKSPACE_ID, "TASK")
    elif entity_type == "production":
        entity_id_col = ProjectItem.id
        stmt = select(ProjectItem).join(Project, Project.id == ProjectItem.project_id).where(
            Project.workspace_id == DEMO_WORKSPACE_ID
        )
        cf_map = await get_custom_fields_map(db, DEMO_WORKSPACE_ID, "PROJECT_ITEM")
    else:
        raise HTTPException(status_code=422, detail=f"Неизвестный entity_type: {entity_type}")

    if not payload_is_archived(filters) and entity_type == "projects":
        stmt = stmt.where(Project.archived_at.is_(None))

    tree = build_filter_tree(filters, fields, cf_map, entity_id_col)
    if tree is not None:
        stmt = stmt.where(tree)

    if search:
        s = search.strip()
        if entity_type == "projects":
            stmt = stmt.where(
                (Project.title.ilike(f"%{s}%"))
                | (Project.display_id.ilike(f"%{s}%"))
                | (Project.manager_name.ilike(f"%{s}%"))
                | (Project.client_legal_name.ilike(f"%{s}%"))
            )
        elif entity_type == "tasks":
            stmt = stmt.where(Task.title.ilike(f"%{s}%"))
        elif entity_type == "production":
            stmt = stmt.where(ProjectItem.name.ilike(f"%{s}%"))

    stmt = apply_grouping(stmt, group_by, fields)
    order = build_sorting(sorting, fields)
    if not order:
        if entity_type == "projects":
            order = [Project.deadline.asc().nullslast()]
        elif entity_type == "tasks":
            order = [Task.due_date.asc().nullslast()]
        else:
            order = [ProjectItem.name.asc()]
    stmt = stmt.order_by(*order)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for row in rows:
        if entity_type == "projects":
            cv = await load_custom_values(db, DEMO_WORKSPACE_ID, row)
            items.append({
                "id": str(row.id), "display_id": row.display_id, "title": row.title,
                "client_legal_name": row.client_legal_name, "manager_name": row.manager_name,
                "stage": row.stage, "deadline": row.deadline.isoformat() if row.deadline else None,
                "risk_level": row.risk_level, "risk_reason": row.risk_reason,
                "payment_percent": row.payment_percent, "currency": row.currency,
                "next_action": row.next_action, "next_action_date": row.next_action_date.isoformat() if row.next_action_date else None,
                "advance_date": row.advance_date.isoformat() if row.advance_date else None,
                "final_payment_date": row.final_payment_date.isoformat() if row.final_payment_date else None,
                "delivery_address": row.delivery_address, "delivery_paid": row.delivery_paid,
                "archived_at": row.archived_at.isoformat() if row.archived_at else None,
                "custom_values": cv,
            })
        elif entity_type == "tasks":
            items.append({
                "id": str(row.id), "title": row.title, "status": row.status,
                "priority": row.priority, "assignee_name": row.assignee_name,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "project_id": str(row.project_id) if row.project_id else None,
                "project_item_id": str(row.project_item_id) if row.project_item_id else None,
            })
        else:  # production
            items.append({
                "id": str(row.id), "name": row.name, "quantity": row.quantity,
                "project_id": str(row.project_id), "mockup_status": row.mockup_status,
                "signal_status": row.signal_status, "batch_status": row.batch_status,
                "factory": row.factory, "signal_shipping_date": row.signal_shipping_date.isoformat() if row.signal_shipping_date else None,
            })

    return {"items": items, "total": total or 0, "page": page, "page_size": page_size, "group_by": group_by}


def payload_is_archived(filters) -> bool:
    """Проверка: временный фильтр включает архивированные? (7.md §33)."""
    if filters is None:
        return False
    for c in (filters.conditions or []):
        if isinstance(c, dict) and c.get("field") == "archived_at" and c.get("operator") == "not_empty":
            return True
    return False