"""Роутер /custom-fields (спец. 2.md §22, §9)."""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..formula_engine import FormulaError, compile_formula
from ..models import CustomField
from ..schemas import CustomFieldCreate, CustomFieldRead, CustomFieldUpdate

router = APIRouter(prefix="/custom-fields", tags=["custom-fields"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

FIELD_TYPES = {
    "TEXT", "LONG_TEXT", "NUMBER", "DATE", "DATETIME", "BOOLEAN",
    "SELECT", "MULTI_SELECT", "PERCENT", "CURRENCY", "URL", "FORMULA",
}


_TRANSLIT = {
    ord("а"): "a", ord("б"): "b", ord("в"): "v", ord("г"): "g", ord("д"): "d",
    ord("е"): "e", ord("ё"): "e", ord("ж"): "zh", ord("з"): "z", ord("и"): "i",
    ord("й"): "i", ord("к"): "k", ord("л"): "l", ord("м"): "m", ord("н"): "n",
    ord("о"): "o", ord("п"): "p", ord("р"): "r", ord("с"): "s", ord("т"): "t",
    ord("у"): "u", ord("ф"): "f", ord("х"): "kh", ord("ц"): "ts", ord("ч"): "ch",
    ord("ш"): "sh", ord("щ"): "sch", ord("ъ"): "", ord("ы"): "y", ord("ь"): "",
    ord("э"): "e", ord("ю"): "iu", ord("я"): "ia",
}


def _slugify(name: str) -> str:
    translit = name.strip().lower().translate(_TRANSLIT)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", translit).strip("_")
    if not slug:
        slug = "field"
    return slug


async def _field_or_404(session: AsyncSession, field_id: uuid.UUID) -> CustomField:
    cf = await session.get(CustomField, field_id)
    if cf is None:
        raise HTTPException(status_code=404, detail="Поле не найдено")
    return cf


@router.get("", response_model=list[CustomFieldRead])
async def list_custom_fields(
    entity_type: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CustomField).where(CustomField.workspace_id == DEMO_WORKSPACE_ID)
    if entity_type:
        stmt = stmt.where(CustomField.entity_type == entity_type)
    if not include_inactive:
        stmt = stmt.where(CustomField.is_active.is_(True))
    stmt = stmt.order_by(CustomField.position, CustomField.created_at)
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=CustomFieldRead, status_code=201)
async def create_custom_field(payload: CustomFieldCreate, db: AsyncSession = Depends(get_db)):
    if payload.field_type not in FIELD_TYPES:
        raise HTTPException(status_code=422, detail=f"Неизвестный тип поля: {payload.field_type}")
    if payload.field_type == "FORMULA" and payload.formula:
        try:
            compile_formula(payload.formula)
        except FormulaError as exc:
            raise HTTPException(status_code=422, detail=f"Невалидная формула: {exc}") from exc
    slug = _slugify(payload.name)
    # Уникальный slug: если занят, добавляем суффикс
    base = slug
    counter = 1
    while True:
        exists = await db.scalar(
            select(CustomField.id).where(
                CustomField.workspace_id == DEMO_WORKSPACE_ID,
                CustomField.entity_type == payload.entity_type,
                CustomField.slug == slug,
            )
        )
        if exists is None:
            break
        slug = f"{base}_{counter}"
        counter += 1
    cf = CustomField(
        workspace_id=DEMO_WORKSPACE_ID,
        slug=slug,
        **payload.model_dump(exclude_unset=True),
    )
    db.add(cf)
    await db.commit()
    await db.refresh(cf)
    return cf


@router.patch("/{field_id}", response_model=CustomFieldRead)
async def update_custom_field(
    field_id: uuid.UUID, payload: CustomFieldUpdate, db: AsyncSession = Depends(get_db)
):
    cf = await _field_or_404(db, field_id)
    changes = payload.model_dump(exclude_unset=True)
    formula = changes.get("formula", cf.formula)
    field_type = changes.get("field_type", cf.field_type)
    if field_type == "FORMULA" and formula:
        try:
            compile_formula(formula)
        except FormulaError as exc:
            raise HTTPException(status_code=422, detail=f"Невалидная формула: {exc}") from exc
    for field, value in changes.items():
        setattr(cf, field, value)
    await db.commit()
    await db.refresh(cf)
    return cf


@router.delete("/{field_id}", status_code=204)
async def delete_custom_field(field_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cf = await _field_or_404(db, field_id)
    await db.delete(cf)
    await db.commit()
