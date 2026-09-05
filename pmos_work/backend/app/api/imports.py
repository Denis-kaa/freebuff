"""Import API (6.md §51, §14-17, §36-38).

POST /imports/excel|csv        — загрузка (не импорт сразу!)
POST /imports/{id}/mapping     — ручной mapping + пере-валидация (dry run)
POST /imports/{id}/save-mapping— сохранить mapping (§9)
GET  /imports/{id}             — статус job
GET  /imports/{id}/preview     — предпросмотр (§13, §44 dry run)
POST /imports/{id}/confirm     — подтверждение и импорт (транзакция §15)
POST /imports/{id}/cancel      — отмена
GET  /imports/history          — история (§36-37)
GET  /imports/{id}/errors      — лог ошибок (§38)
GET  /imports/templates        — шаблон Excel (§41-42)
"""
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..export_service import build_import_template
from ..import_service import (
    ImportPreview,
    MAX_ROWS,
    auto_mapping,
    build_preview,
    load_manager_cache,
    parse_csv,
    parse_excel,
    run_import,
)
from ..models import ImportJob, ImportMapping, Project
from ..rbac import UserContext, check_workspace_access, require_permission
from ..services import add_audit

router = APIRouter(prefix="/imports", tags=["imports"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
IMPORT_DIR = "/var/www/pm_os/imports"

ALLOWED_EXT = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB (§48)


async def _job_or_404(db, job_id: uuid.UUID, ctx: Optional[UserContext] = None) -> ImportJob:
    job = await db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Импорт не найден")
    if ctx is not None:
        check_workspace_access(ctx, job.workspace_id)
    elif job.workspace_id != DEMO_WORKSPACE_ID:
        raise HTTPException(status_code=404, detail="Импорт не найден")
    return job


def _job_dict(job: ImportJob) -> dict:
    return {
        "id": str(job.id), "source_type": job.source_type, "file_name": job.file_name,
        "sheet_name": job.sheet_name, "status": job.status,
        "duplicate_mode": job.duplicate_mode, "partial": job.partial,
        "created_count": job.created_count, "updated_count": job.updated_count,
        "skipped_count": job.skipped_count, "error_count": job.error_count,
        "warning_count": job.warning_count, "preview": job.preview,
        "errors": job.errors, "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


async def _save_upload(file: UploadFile, job_id: uuid.UUID) -> str:
    """Сохраняет файл на диск с проверкой типа/размера (6.md §48)."""
    os.makedirs(IMPORT_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=422, detail="Поддерживаются только .xlsx, .xls, .csv")
    # MIME-проверка (не доверяем имени файла)
    content_type = file.content_type or ""
    if content_type and not any(m in content_type for m in ("spreadsheet", "excel", "csv", "octet-stream", "text")):
        raise HTTPException(status_code=422, detail="Недопустимый тип файла")
    dest = os.path.join(IMPORT_DIR, f"{job_id}{ext}")
    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                await file.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail="Файл слишком большой (лимит 20 МБ)")
            f.write(chunk)
    return dest


async def _prepare_preview(db, job: ImportJob, path: str, mapping: Optional[dict] = None) -> ImportPreview:
    """Parse + авто/ручной mapping + валидация (dry run, без изменений БД)."""
    from ..import_service import detect_table_kind

    kind = detect_table_kind(path, [])
    tables = parse_csv(path) if kind == "csv" else parse_excel(path)
    if not tables:
        raise HTTPException(status_code=422, detail="Файл пуст или не содержит таблицы")
    table = tables[0]
    if job.sheet_name:
        for t in tables:
            if t.sheet_name == job.sheet_name:
                table = t
                break
    if len(table.rows) > MAX_ROWS:
        raise HTTPException(status_code=422, detail=f"Слишком много строк ({len(table.rows)}). Лимит: {MAX_ROWS}")

    await load_manager_cache(db, job.workspace_id)
    known_ids = set((await db.execute(
        select(Project.display_id).where(Project.workspace_id == job.workspace_id)
    )).scalars().all())

    if mapping:
        # применяем ручной mapping (ключи = заголовки Excel)
        auto = auto_mapping(table.headers)
        auto.update({k: v for k, v in mapping.items() if v})
        mapping = auto
    else:
        mapping = auto_mapping(table.headers)

    preview = build_preview(table, mapping, known_ids)
    preview_d = {
        "total": preview.total, "ok": preview.ok, "errors": preview.errors,
        "warnings": preview.warnings, "will_create": preview.will_create,
        "will_update": preview.will_update, "mapping": preview.mapping,
        "unmapped": preview.unmapped, "legacy_notes": preview.legacy_notes,
        "issues": [{"row": i.row, "field": i.field, "value": i.value, "error": i.error, "level": i.level}
                   for i in preview.issues],
        "headers": table.headers,
    }
    job.preview = preview_d
    job.errors = preview_d["issues"]
    job.error_count = preview.errors
    job.warning_count = preview.warnings
    job.status = "VALIDATING"
    return preview_d


@router.post("/excel")
async def import_excel(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    ctx: UserContext = Depends(require_permission("project.import")),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка Excel: только парсинг + предпросмотр (§3, §14)."""
    return await _handle_upload(file, sheet_name, "excel", db, ctx)


@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    ctx: UserContext = Depends(require_permission("project.import")),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_upload(file, None, "csv", db, ctx)


async def _handle_upload(file, sheet_name, source_type, db, ctx: UserContext):
    job = ImportJob(workspace_id=ctx.workspace_id, source_type=source_type,
                    file_name=file.filename, sheet_name=sheet_name, status="PENDING",
                    created_by="Менеджер", started_at=datetime.now(timezone.utc))
    db.add(job)
    await db.commit()
    await db.refresh(job)
    try:
        path = await _save_upload(file, job.id)
        preview = await _prepare_preview(db, job, path, None)
        await db.commit()
        await db.refresh(job)
        return {"job": _job_dict(job), "preview": preview}
    except HTTPException:
        job.status = "FAILED"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise


@router.post("/{job_id}/mapping")
async def update_mapping(
    job_id: uuid.UUID,
    payload: dict,
    ctx: UserContext = Depends(require_permission("project.import")),
    db: AsyncSession = Depends(get_db),
):
    """Ручной mapping + повторная валидация (dry run, §7-8, §44)."""
    job = await _job_or_404(db, job_id, ctx)
    mapping = payload.get("mapping") or {}
    ext = os.path.splitext(job.file_name or "")[1].lower()
    path = os.path.join(IMPORT_DIR, f"{job_id}{ext}")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл импорта не найден")
    preview = await _prepare_preview(db, job, path, mapping)
    await db.commit()
    await db.refresh(job)
    return {"job": _job_dict(job), "preview": preview}


@router.post("/{job_id}/save-mapping")
async def save_mapping(job_id: uuid.UUID, payload: dict, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    """Сохранить сопоставление (6.md §9)."""
    job = await _job_or_404(db, job_id, ctx)
    name = (payload.get("name") or "").strip()
    mapping = payload.get("mapping") or {}
    if not name:
        raise HTTPException(status_code=422, detail="Укажите название сопоставления")
    existing = await db.scalar(select(ImportMapping).where(
        ImportMapping.workspace_id == ctx.workspace_id, ImportMapping.name == name
    ))
    if existing:
        existing.mapping_config = mapping
        existing.source_type = job.source_type
    else:
        db.add(ImportMapping(workspace_id=ctx.workspace_id, name=name,
                             source_type=job.source_type, mapping_config=mapping,
                             created_by=ctx.display_name))
    await db.commit()
    return {"ok": True, "name": name}


@router.get("/history")
async def history(limit: int = Query(30, ge=1, le=200), ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ImportJob).where(ImportJob.workspace_id == ctx.workspace_id)
        .order_by(ImportJob.created_at.desc()).limit(limit)
    )).scalars().all()
    return [_job_dict(j) for j in rows]


@router.get("/templates")
async def templates(
    kind: str = Query("projects", description="projects|projects_items"),
    ctx: UserContext = Depends(require_permission("project.import")),
):
    """Скачать шаблон Excel (6.md §41-42). Должен быть ДО /{job_id} (маршруты)."""
    os.makedirs(IMPORT_DIR, exist_ok=True)
    path = os.path.join(IMPORT_DIR, f"PROJECT_IMPORT_TEMPLATE_{kind}.xlsx")
    build_import_template(path, kind)
    from fastapi.responses import FileResponse

    return FileResponse(path, filename=f"PROJECT_IMPORT_TEMPLATE_{kind}.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/{job_id}")
async def get_job(job_id: uuid.UUID, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    return _job_dict(await _job_or_404(db, job_id, ctx))


@router.get("/{job_id}/preview")
async def get_preview(job_id: uuid.UUID, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    job = await _job_or_404(db, job_id, ctx)
    if not job.preview:
        raise HTTPException(status_code=409, detail="Предпросмотр не готов")
    return {"job": _job_dict(job), "preview": job.preview}


@router.get("/{job_id}/errors")
async def get_errors(job_id: uuid.UUID, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    job = await _job_or_404(db, job_id, ctx)
    return {"errors": job.errors or [], "error_count": job.error_count, "warning_count": job.warning_count}


@router.post("/{job_id}/confirm")
async def confirm_import(job_id: uuid.UUID, payload: dict, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    """Подтверждение и импорт. Транзакция (§15), дубликаты (§18), partial (§16)."""
    job = await _job_or_404(db, job_id, ctx)
    if job.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(status_code=409, detail=f"Импорт уже завершён ({job.status})")

    ext = os.path.splitext(job.file_name or "")[1].lower()
    path = os.path.join(IMPORT_DIR, f"{job_id}{ext}")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл импорта не найден")

    mapping = payload.get("mapping") or (job.preview or {}).get("mapping") or {}
    duplicate_mode = payload.get("duplicate_mode") or job.duplicate_mode or "update"
    partial = bool(payload.get("partial", job.partial))
    if duplicate_mode not in ("update", "skip", "copy"):
        raise HTTPException(status_code=422, detail="duplicate_mode: update|skip|copy")

    from ..import_service import detect_table_kind

    kind = detect_table_kind(path, [])
    tables = parse_csv(path) if kind == "csv" else parse_excel(path)
    table = tables[0]
    if job.sheet_name:
        for t in tables:
            if t.sheet_name == job.sheet_name:
                table = t
                break

    result = {"created": 0, "updated": 0, "skipped": 0, "issues": []}
    try:
        # транзакция (§15): либо всё, либо rollback (событие НЕ создаётся частично)
        job.status = "IMPORTING"
        result = await run_import(db, ctx.workspace_id, table, mapping,
                                  duplicate_mode=duplicate_mode, partial=partial)
        job.created_count = result["created"]
        job.updated_count = result["updated"]
        job.skipped_count = result["skipped"]
        job.errors = result["issues"]
        job.error_count = sum(1 for i in result["issues"] if i["level"] == "ERROR")
        job.warning_count = sum(1 for i in result["issues"] if i["level"] == "WARNING")
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        await add_audit(db, ctx.workspace_id, ctx.display_name, "import", "import_job", job.id,
                        new_value={"file": job.file_name, "created": result["created"],
                                   "updated": result["updated"], "skipped": result["skipped"]})
        await db.commit()

        # сохранить mapping по запросу (§9)
        save_name = (payload.get("save_mapping_name") or "").strip()
        if save_name and mapping:
            existing = await db.scalar(select(ImportMapping).where(
                ImportMapping.workspace_id == DEMO_WORKSPACE_ID, ImportMapping.name == save_name
            ))
            if existing:
                existing.mapping_config = mapping
            else:
                db.add(ImportMapping(workspace_id=DEMO_WORKSPACE_ID, name=save_name,
                                     source_type=job.source_type, mapping_config=mapping,
                                     created_by="Менеджер"))
            await db.commit()
        await db.refresh(job)
        return {"job": _job_dict(job), "result": result}
    except Exception as e:  # noqa: BLE001 — rollback транзакции (§15)
        await db.rollback()
        # перечитываем свежим: НИЧЕГО из частичного импорта не должно остаться
        fresh = await db.get(ImportJob, job_id)
        fresh.status = "FAILED"
        fresh.completed_at = datetime.now(timezone.utc)
        errs = list(fresh.errors or [])
        errs.append({"row": 0, "field": None, "value": None,
                     "error": f"Импорт отменён (rollback): {str(e)[:300]}", "level": "ERROR"})
        fresh.errors = errs
        fresh.error_count = sum(1 for x in errs if x["level"] == "ERROR")
        await db.commit()
        return {"job": _job_dict(fresh), "result": {"created": 0, "updated": 0, "skipped": 0},
                "rolled_back": True}


@router.post("/{job_id}/cancel")
async def cancel_import(job_id: uuid.UUID, ctx: UserContext = Depends(require_permission("project.import")), db: AsyncSession = Depends(get_db)):
    job = await _job_or_404(db, job_id, ctx)
    if job.status in ("COMPLETED", "FAILED"):
        raise HTTPException(status_code=409, detail="Импорт уже завершён")
    job.status = "CANCELLED"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return _job_dict(job)