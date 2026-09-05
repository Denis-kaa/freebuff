"""Роутер /project-items (спец. 3.md §5-7, §23, §29)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Project, ProjectItem
from ..schemas import (
    BulkItemsUpdateRequest,
    CustomFieldValueUpdate,
    ProjectItemCreate,
    ProjectItemProductionUpdate,
    ProjectItemRead,
    ProjectItemUpdate,
)
from ..services import (
    add_audit,
    load_custom_values,
    save_custom_values,
)

router = APIRouter(prefix="/project-items", tags=["project-items"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _item_or_404(session: AsyncSession, item_id: uuid.UUID) -> ProjectItem:
    item = await session.get(ProjectItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    return item


def _to_read(item: ProjectItem, custom_values: dict | None = None) -> ProjectItemRead:
    data = {
        "id": item.id,
        "project_id": item.project_id,
        "name": item.name,
        "quantity": item.quantity,
        "tech_specs": item.tech_specs,
        "mockup_status": item.mockup_status,
        "signal_required": item.signal_required,
        "signal_status": item.signal_status,
        "signal_shipping_date": item.signal_shipping_date,
        "signal_feedback": item.signal_feedback,
        "batch_status": item.batch_status,
        "batch_feedback": item.batch_feedback,
        "factory": item.factory,
        "version": item.version,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "custom_values": custom_values or {},
    }
    return ProjectItemRead(**data)


@router.get("", response_model=list[ProjectItemRead])
async def list_items(
    project_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)
):
    stmt = select(ProjectItem)
    if project_id:
        stmt = stmt.where(ProjectItem.project_id == project_id)
    rows = (await db.execute(stmt.order_by(ProjectItem.created_at))).scalars().all()
    result = []
    for it in rows:
        cv = await load_custom_values(db, DEMO_WORKSPACE_ID, it)
        result.append(_to_read(it, cv))
    return result


@router.get("/{item_id}", response_model=ProjectItemRead)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await _item_or_404(db, item_id)
    cv = await load_custom_values(db, DEMO_WORKSPACE_ID, item)
    return _to_read(item, cv)


@router.post("", response_model=ProjectItemRead, status_code=201)
async def create_item(payload: ProjectItemCreate, db: AsyncSession = Depends(get_db)):
    if payload.project_id is None:
        raise HTTPException(status_code=422, detail="project_id обязателен")
    project = await db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    item = ProjectItem(project_id=payload.project_id, **payload.model_dump(exclude={"project_id"}))
    db.add(item)
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "create", "project_item", item.id,
                    new_value={"name": payload.name})
    await db.commit()
    await db.refresh(item)
    return _to_read(item)


@router.patch("/{item_id}", response_model=ProjectItemRead)
async def update_item(
    item_id: uuid.UUID, payload: ProjectItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await _item_or_404(db, item_id)
    # optimistic locking (3.md §25)
    if payload.version is not None and payload.version != item.version:
        raise HTTPException(status_code=409, detail="Позиция была изменена другим пользователем. Обновите данные перед сохранением.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "version":
            continue
        setattr(item, field, value)
    item.version += 1
    await db.commit()
    await db.refresh(item)
    cv = await load_custom_values(db, DEMO_WORKSPACE_ID, item)
    return _to_read(item, cv)


@router.patch("/{item_id}/production", response_model=ProjectItemRead)
async def update_production(
    item_id: uuid.UUID,
    payload: ProjectItemProductionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновление производственных статусов (3.md §23, §7-8)."""
    item = await _item_or_404(db, item_id)
    if payload.version is not None and payload.version != item.version:
        raise HTTPException(status_code=409, detail="Позиция была изменена другим пользователем. Обновите данные перед сохранением.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "version":
            continue
        setattr(item, field, value)
    item.version += 1
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "production_update", "project_item", item.id,
                    new_value=payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(item)
    cv = await load_custom_values(db, DEMO_WORKSPACE_ID, item)
    return _to_read(item, cv)


@router.put("/{item_id}/custom-values")
async def update_item_custom_values(
    item_id: uuid.UUID,
    payload: CustomFieldValueUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Custom Fields для Project Item (3.md §26)."""
    await _item_or_404(db, item_id)
    await save_custom_values(db, DEMO_WORKSPACE_ID, item_id, payload.values, entity_type="PROJECT_ITEM")
    await db.commit()
    return {"saved": list(payload.values.keys())}


@router.post("/bulk-update")
async def bulk_update_items(payload: BulkItemsUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Массовое изменение позиций (3.md §29): статус/сигнал/фабрика."""
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Список ids пуст")
    rows = (await db.execute(select(ProjectItem).where(ProjectItem.id.in_(payload.ids)))).scalars().all()
    for it in rows:
        if payload.mockup_status is not None:
            it.mockup_status = payload.mockup_status
        if payload.signal_status is not None:
            it.signal_status = payload.signal_status
        if payload.factory is not None:
            it.factory = payload.factory
        it.version += 1
    await db.commit()
    return {"updated": len(rows)}


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await _item_or_404(db, item_id)
    await db.delete(item)
    await db.commit()