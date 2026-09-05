"""Роутер /projects.

Спецификация 2.md §22-24:
GET/POST /projects, GET/PATCH/DELETE /projects/{id},
POST /projects/bulk-update, POST /projects/{id}/archive,
GET /projects/filters/options.
"""
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..automation_engine import create_event, execute_event
from ..database import get_db
from ..models import CustomFieldValue, Project
from ..rbac import (
    DEMO_WORKSPACE_ID,
    UserContext,
    check_workspace_access,
    get_current_user,
    mask_finance_fields,
    mask_finance_fields_bulk,
    require_permission,
)
from ..schemas import (
    BulkUpdateRequest,
    CustomFieldValueUpdate,
    FilterCondition,
    ProjectCreate,
    ProjectListQuery,
    ProjectListResponse,
    ProjectRead,
    ProjectUpdate,
)
from ..services import (
    add_audit,
    apply_filters,
    apply_multi_sorting,
    apply_sorting,
    get_custom_fields_map,
    load_custom_values,
    next_display_id,
    resolve_user_name,
    save_custom_values,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _project_or_404(
    session: AsyncSession, project_id: uuid.UUID, ctx: Optional[UserContext] = None
) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    if ctx is not None:
        check_workspace_access(ctx, project.workspace_id)
    return project


def _to_read(
    project: Project,
    custom_values: Optional[dict[str, Any]] = None,
    ctx: Optional[UserContext] = None,
) -> ProjectRead:
    data = {
        "id": project.id,
        "display_id": project.display_id,
        "title": project.title,
        "client_legal_name": project.client_legal_name,
        "manager_id": project.manager_id,
        "manager_name": project.manager_name,
        "stage": project.stage,
        "deadline": project.deadline,
        "risk_level": project.risk_level,
        "risk_reason": project.risk_reason,
        "payment_percent": project.payment_percent,
        "currency": project.currency,
        "advance_date": project.advance_date,
        "final_payment_date": project.final_payment_date,
        "delivery_address": project.delivery_address,
        "delivery_paid": project.delivery_paid,
        "next_action": project.next_action,
        "next_action_date": project.next_action_date,
        "comment": project.comment,
        "archived_at": project.archived_at,
        "version": project.version,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "custom_values": custom_values or {},
    }
    if ctx is not None:
        data = mask_finance_fields(ctx, data)
    return ProjectRead(**data)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: Optional[str] = "deadline",
    sort_dir: str = "asc",
    sorting: Optional[str] = None,
    include_archived: bool = False,
    # Структурированные фильтры передаём как JSON-строку (демо-простота) —
    # полноценная валидация через Pydantic ниже.
    filters: Optional[str] = Query(None),
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    query = ProjectListQuery(
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        include_archived=include_archived,
    )
    stmt = select(Project).where(Project.workspace_id == ctx.workspace_id)

    if not query.include_archived:
        stmt = stmt.where(Project.archived_at.is_(None))

    # Глобальный поиск (спец. 2.md §17): название, ID, юр.лицо, менеджер,
    # а также значения пользовательских TEXT-полей.
    if query.search:
        s = query.search.strip()
        from sqlalchemy import String, exists as _exists

        from ..models import CustomField as _CF

        text_cf_ids = (
            await db.scalars(
                select(_CF.id).where(
                    _CF.workspace_id == ctx.workspace_id,
                    _CF.field_type.in_(["TEXT", "LONG_TEXT"]),
                )
            )
        ).all()
        custom_search = _exists(
            select(CustomFieldValue.id).where(
                CustomFieldValue.project_id == Project.id,
                CustomFieldValue.custom_field_id.in_(text_cf_ids),
                CustomFieldValue.value.cast(String).ilike(f"%{s}%"),
            )
        )
        stmt = stmt.where(
            or_(
                Project.title.ilike(f"%{s}%"),
                Project.display_id.ilike(f"%{s}%"),
                Project.client_legal_name.ilike(f"%{s}%"),
                Project.manager_name.ilike(f"%{s}%"),
                custom_search,
            )
        )

    # Пользовательские поля — для фильтрации по ним
    cf_map = await get_custom_fields_map(db, ctx.workspace_id)

    # Структурированные фильтры
    import json as _json

    if filters:
        try:
            parsed = _json.loads(filters)
            conds = [FilterCondition(**c) for c in parsed]
            query.filters = conds
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат filters")

    stmt = apply_filters(stmt, query.filters, cf_map)
    if sorting:
        # Мульти-сортировка: [{field: ..., direction: ...}, ...] (спец. §16)
        try:
            parsed_sort = _json.loads(sorting)
            stmt = apply_multi_sorting(stmt, parsed_sort)
        except Exception:
            stmt = apply_sorting(stmt, query.sort_by, query.sort_dir)
    else:
        stmt = apply_sorting(stmt, query.sort_by, query.sort_dir)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for p in rows:
        cv = await load_custom_values(db, ctx.workspace_id, p)
        items.append(_to_read(p, cv, ctx))

    return ProjectListResponse(
        items=items,
        total=total or 0,
        page=query.page,
        page_size=query.page_size,
    )


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    ctx: UserContext = Depends(require_permission("project.create")),
    db: AsyncSession = Depends(get_db),
):
    display_id = await next_display_id(db, ctx.workspace_id)
    data = payload.model_dump(exclude_unset=True)
    manager_id = data.pop("manager_id", None)
    if manager_id is not None:
        # RBAC §39: manager_name резолвится из пользователя workspace
        data["manager_name"] = await resolve_user_name(db, ctx.workspace_id, manager_id)
    project = Project(
        workspace_id=ctx.workspace_id,
        display_id=display_id,
        **data,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    event = await create_event(db, ctx.workspace_id, "project.created", "project", project.id, {"title": project.title})
    await execute_event(db, event)
    await db.commit()
    return _to_read(project)


@router.get("/filters/options")
async def filter_options(db: AsyncSession = Depends(get_db)):
    """Опции для фильтров: этапы, менеджеры, риски, валюты, оплаты."""
    opts: dict[str, list[str]] = {}
    for column, key in (
        (Project.stage, "stages"),
        (Project.manager_name, "managers"),
        (Project.risk_level, "risks"),
        (Project.currency, "currencies"),
        (Project.payment_percent, "payments"),
    ):
        rows = (
            await db.execute(select(column).where(column.isnot(None)).distinct().order_by(column))
        ).scalars().all()
        opts[key] = [str(r) for r in rows]
    return opts


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    project = await _project_or_404(db, project_id, ctx)
    cv = await load_custom_values(db, ctx.workspace_id, project)
    return _to_read(project, cv, ctx)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    ctx: UserContext = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
):
    project = await _project_or_404(db, project_id, ctx)
    # optimistic locking (3.md §25): клиент передаёт ожидаемую версию
    if payload.version is not None and payload.version != project.version:
        raise HTTPException(
            status_code=409,
            detail="Проект был изменён другим пользователем. Обновите данные перед сохранением.",
        )
    changes = payload.model_dump(exclude_unset=True)
    manager_id = changes.pop("manager_id", None)
    if manager_id is not None:
        # RBAC §39: manager_name резолвится из пользователя workspace
        resolved = await resolve_user_name(db, ctx.workspace_id, manager_id)
        changes["manager_name"] = resolved
        project.manager_id = manager_id
    for field, value in changes.items():
        if field == "version":
            continue
        setattr(project, field, value)
    project.version += 1
    await add_audit(db, ctx.workspace_id, "Менеджер", "update", "project", project.id,
                    new_value=changes)
    await db.commit()
    await db.refresh(project)
    event_type = "project.status_changed" if "stage" in changes else "project.updated"
    event = await create_event(db, ctx.workspace_id, event_type, "project", project.id, {"changes": changes})
    await execute_event(db, event)
    await db.commit()
    cv = await load_custom_values(db, ctx.workspace_id, project)
    return _to_read(project, cv, ctx)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.delete")),
    db: AsyncSession = Depends(get_db),
):
    project = await _project_or_404(db, project_id, ctx)
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/archive", response_model=ProjectRead)
async def archive_project(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: archived_at (спец. 2.md §20)."""
    from datetime import datetime, timezone

    project = await _project_or_404(db, project_id, ctx)
    project.archived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)
    return _to_read(project, ctx=ctx)


@router.post("/{project_id}/unarchive", response_model=ProjectRead)
async def unarchive_project(
    project_id: uuid.UUID,
    ctx: UserContext = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
):
    project = await _project_or_404(db, project_id, ctx)
    project.archived_at = None
    await db.commit()
    await db.refresh(project)
    return _to_read(project, ctx=ctx)


@router.post("/bulk-update")
async def bulk_update(
    payload: BulkUpdateRequest,
    ctx: UserContext = Depends(require_permission("project.bulk_update")),
    db: AsyncSession = Depends(get_db),
):
    """Массовое обновление: этап/менеджер/риск (спец. 2.md §19)."""
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Список ids пуст")
    rows = (
        await db.execute(select(Project).where(Project.id.in_(payload.ids)))
    ).scalars().all()
    for p in rows:
        if payload.stage is not None:
            p.stage = payload.stage
        if payload.manager_name is not None:
            p.manager_name = payload.manager_name
        if payload.risk_level is not None:
            p.risk_level = payload.risk_level
    await db.commit()
    return {"updated": len(rows)}


@router.put("/{project_id}/custom-values")
async def update_custom_values(
    project_id: uuid.UUID,
    payload: CustomFieldValueUpdate,
    ctx: UserContext = Depends(require_permission("project.update")),
    db: AsyncSession = Depends(get_db),
):
    """Сохранение значений пользовательских полей (спец. 2.md §10)."""
    await _project_or_404(db, project_id, ctx)
    await save_custom_values(db, ctx.workspace_id, project_id, payload.values)
    await db.commit()
    return {"saved": list(payload.values.keys())}
