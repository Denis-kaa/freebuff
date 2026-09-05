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

from ..database import get_db
from ..models import CustomFieldValue, Project
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
    apply_filters,
    apply_multi_sorting,
    apply_sorting,
    get_custom_fields_map,
    load_custom_values,
    next_display_id,
    save_custom_values,
)

router = APIRouter(prefix="/projects", tags=["projects"])

# В демо-режиме один workspace на всё приложение.
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _project_or_404(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


def _to_read(project: Project, custom_values: Optional[dict[str, Any]] = None) -> ProjectRead:
    data = {
        "id": project.id,
        "display_id": project.display_id,
        "title": project.title,
        "client_legal_name": project.client_legal_name,
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
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "custom_values": custom_values or {},
    }
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
    stmt = select(Project).where(Project.workspace_id == DEMO_WORKSPACE_ID)

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
                    _CF.workspace_id == DEMO_WORKSPACE_ID,
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
    cf_map = await get_custom_fields_map(db, DEMO_WORKSPACE_ID)

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
        cv = await load_custom_values(db, DEMO_WORKSPACE_ID, p)
        items.append(_to_read(p, cv))

    return ProjectListResponse(
        items=items,
        total=total or 0,
        page=query.page,
        page_size=query.page_size,
    )


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    display_id = await next_display_id(db, DEMO_WORKSPACE_ID)
    project = Project(
        workspace_id=DEMO_WORKSPACE_ID,
        display_id=display_id,
        **payload.model_dump(exclude_unset=True),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
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
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    project = await _project_or_404(db, project_id)
    cv = await load_custom_values(db, DEMO_WORKSPACE_ID, project)
    return _to_read(project, cv)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    project = await _project_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    cv = await load_custom_values(db, DEMO_WORKSPACE_ID, project)
    return _to_read(project, cv)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    project = await _project_or_404(db, project_id)
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/archive", response_model=ProjectRead)
async def archive_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete: archived_at (спец. 2.md §20)."""
    from datetime import datetime, timezone

    project = await _project_or_404(db, project_id)
    project.archived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)
    return _to_read(project)


@router.post("/{project_id}/unarchive", response_model=ProjectRead)
async def unarchive_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    project = await _project_or_404(db, project_id)
    project.archived_at = None
    await db.commit()
    await db.refresh(project)
    return _to_read(project)


@router.post("/bulk-update")
async def bulk_update(payload: BulkUpdateRequest, db: AsyncSession = Depends(get_db)):
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
    db: AsyncSession = Depends(get_db),
):
    """Сохранение значений пользовательских полей (спец. 2.md §10)."""
    await _project_or_404(db, project_id)
    await save_custom_values(db, DEMO_WORKSPACE_ID, project_id, payload.values)
    await db.commit()
    return {"saved": list(payload.values.keys())}
