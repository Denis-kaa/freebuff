"""Global search API (7.md §49)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..search_service import search_all

router = APIRouter(prefix="/search", tags=["search"])
DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("")
async def global_search(
    q: str = Query("", max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Search all supported entity types, ranked by relevance."""
    if not q.strip():
        return {"query": q, "results": {"projects": [], "tasks": [], "items": [], "clients": [], "documents": []}}
    return {"query": q, "results": await search_all(db, DEMO_WORKSPACE_ID, q)}
