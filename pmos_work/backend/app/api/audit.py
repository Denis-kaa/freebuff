"""Роутер /audit (спец. 1.md §28)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AuditLog
from ..schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("", response_model=list[AuditLogRead])
async def list_audit(
    limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.workspace_id == DEMO_WORKSPACE_ID)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()
