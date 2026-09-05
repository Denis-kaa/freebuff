"""Export API (6.md §23-29, §40, §51).

POST /exports/excel|csv        — сформировать файл (scope/columns/filters)
GET  /exports/{id}             — метаданные
GET  /exports/{id}/download    — скачивание
GET|POST /exports/presets      — сохранённые настройки (§40)
"""
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..export_service import (
    EXPORT_DIR,
    build_calendar_export,
    build_export,
    fetch_items,
    fetch_projects,
    fetch_tasks,
)
from ..models import ExportPreset, Project
from ..rbac import DEMO_WORKSPACE_ID, FINANCE_FIELDS, UserContext, require_permission
from ..services import add_audit

router = APIRouter(prefix="/exports", tags=["exports"])

ALLOWED_SCOPES = {"current_view", "all_projects", "projects_items", "tasks", "calendar", "legacy"}


@router.post("/excel")
async def export_excel(
    payload: dict,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    return await _make_export(payload, "xlsx", db, ctx)


@router.post("/csv")
async def export_csv(
    payload: dict,
    ctx: UserContext = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    return await _make_export(payload, "csv", db, ctx)


async def _make_export(payload: dict, fmt: str, db: AsyncSession, ctx: UserContext):
    scope = payload.get("scope") or "all_projects"
    if scope not in ALLOWED_SCOPES:
        raise HTTPException(status_code=422, detail=f"scope: {', '.join(sorted(ALLOWED_SCOPES))}")
    columns = payload.get("columns") or None
    if columns is not None and not ctx.can_read_finance():
        # RBAC §47: экспорт не должен содержать финансовые поля без finance.read
        columns = [c for c in columns if c not in FINANCE_FIELDS]
    filters = payload.get("filters") or {}
    include_archived = bool(payload.get("include_archived"))

    projects = await fetch_projects(db, ctx.workspace_id, filters, include_archived)
    project_map = {p.id: p for p in projects}
    items = tasks = calendar_events = None

    if scope == "projects_items":
        items = await fetch_items(db, ctx.workspace_id, [p.id for p in projects])
    if scope == "tasks":
        tasks = await fetch_tasks(db, ctx.workspace_id, [p.id for p in projects])
    if scope == "calendar":
        from datetime import date as _d

        frm = filters.get("from") or (date.today() - timedelta(days=30)).isoformat()
        to = filters.get("to") or (date.today() + timedelta(days=90)).isoformat()
        calendar_events = await build_calendar_export(db, ctx.workspace_id,
                                                      _d.fromisoformat(frm), _d.fromisoformat(to))

    os.makedirs(EXPORT_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    ext = ".csv" if fmt == "csv" else ".xlsx"
    path = os.path.join(EXPORT_DIR, f"{file_id}{ext}")
    build_export(
        path, scope=scope, projects=projects, items=items, tasks=tasks,
        calendar_events=calendar_events, columns=columns, fmt=fmt, project_map=project_map,
        can_read_finance=ctx.can_read_finance(),
    )
    await add_audit(db, ctx.workspace_id, ctx.display_name, "export", "export_job", file_id,
                    new_value={"scope": scope, "rows": len(projects)})
    await db.commit()
    return {
        "id": str(file_id), "scope": scope, "format": fmt,
        "filename": os.path.basename(path), "rows": len(projects),
        "download_url": f"/api/exports/{file_id}/download",
    }


@router.get("/presets")
async def list_presets(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ExportPreset).where(ExportPreset.workspace_id == DEMO_WORKSPACE_ID)
        .order_by(ExportPreset.created_at)
    )).scalars().all()
    return [{"id": str(r.id), "name": r.name, "config": r.config} for r in rows]


@router.get("/{export_id}")
async def export_meta(export_id: uuid.UUID):
    ext = ".csv"
    path = os.path.join(EXPORT_DIR, f"{export_id}.xlsx")
    if not os.path.exists(path):
        path = os.path.join(EXPORT_DIR, f"{export_id}.csv")
        ext = ".csv"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Экспорт не найден")
    return {"id": str(export_id), "filename": os.path.basename(path), "size": os.path.getsize(path)}


@router.get("/{export_id}/download")
async def export_download(export_id: uuid.UUID):
    for ext in (".xlsx", ".csv"):
        path = os.path.join(EXPORT_DIR, f"{export_id}{ext}")
        if os.path.exists(path):
            media = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                     if ext == ".xlsx" else "text/csv; charset=utf-8")
            return FileResponse(path, filename=f"pm_os_export{ext}", media_type=media)
    raise HTTPException(status_code=404, detail="Экспорт не найден")


# ---------------------------------------------------------------------------
# Export Presets (6.md §40)
# ---------------------------------------------------------------------------
@router.post("/presets", status_code=201)
async def create_preset(payload: dict, db: AsyncSession = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    config = payload.get("config") or {}
    if not name:
        raise HTTPException(status_code=422, detail="Укажите название пресета")
    p = ExportPreset(workspace_id=DEMO_WORKSPACE_ID, name=name, config=config)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": str(p.id), "name": p.name, "config": p.config}


@router.delete("/presets/{preset_id}", status_code=204)
async def delete_preset(preset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    p = await db.get(ExportPreset, preset_id)
    if p is None or p.workspace_id != DEMO_WORKSPACE_ID:
        raise HTTPException(status_code=404, detail="Пресет не найден")
    await db.delete(p)
    await db.commit()