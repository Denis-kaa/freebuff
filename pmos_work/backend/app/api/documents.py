"""Роутер документов (3.md §15-16).

Файлы НЕ хранятся в PostgreSQL — только метаданные (storage_key).
Файловое хранилище абстрагируется классом FileStorage.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Document, Project, ProjectItem
from ..schemas import DocumentCreate, DocumentRead, DocumentUpdate
from ..services import add_audit

router = APIRouter(prefix="/projects", tags=["documents"])

DEMO_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

DOCUMENT_TYPES = {"MOCKUP", "SIGNAL", "BATCH", "UNIFIED"}
DOCUMENT_STATUSES = {"NOT_READY", "PREPARED", "SENT", "SIGNED"}


class FileStorage:
    """Абстракция хранилища файлов (3.md §16).

    В демо — локальная папка. Позже: S3 / MinIO / Telegram storage.
    """

    BASE_DIR = "/var/www/pm_os/storage/documents"

    @classmethod
    def put(cls, file_name: str, storage_key: str) -> str:
        import os
        from pathlib import Path

        Path(cls.BASE_DIR).mkdir(parents=True, exist_ok=True)
        # В демо просто резервируем путь; реальная загрузка — этап файлов.
        return f"{cls.BASE_DIR}/{storage_key}"


async def _project_or_404(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


async def _doc_or_404(session: AsyncSession, doc_id: uuid.UUID) -> Document:
    doc = await session.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return doc


@router.get("/{project_id}/documents", response_model=list[DocumentRead])
async def list_documents(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _project_or_404(db, project_id)
    stmt = select(Document).where(Document.project_id == project_id).order_by(Document.created_at)
    return (await db.execute(stmt)).scalars().all()


@router.post("/{project_id}/documents", response_model=DocumentRead, status_code=201)
async def create_document(
    project_id: uuid.UUID, payload: DocumentCreate, db: AsyncSession = Depends(get_db)
):
    await _project_or_404(db, project_id)
    if payload.document_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=422, detail="Неизвестный тип документа")
    if payload.status not in DOCUMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Неизвестный статус документа")
    if payload.project_item_id is not None:
        item = await db.get(ProjectItem, payload.project_item_id)
        if item is None or item.project_id != project_id:
            raise HTTPException(status_code=422, detail="Позиция не принадлежит проекту")

    storage_key = None
    if payload.file_name:
        storage_key = FileStorage.put(payload.file_name, f"{project_id}/{uuid.uuid4()}")
    doc = Document(
        workspace_id=DEMO_WORKSPACE_ID,
        project_id=project_id,
        **payload.model_dump(exclude_unset=True),
        storage_key=storage_key,
    )
    db.add(doc)
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "create", "document", doc.id,
                    new_value={"type": payload.document_type, "status": payload.status})
    await db.commit()
    await db.refresh(doc)
    return doc


@router.patch("/{project_id}/documents/{doc_id}", response_model=DocumentRead)
async def update_document(
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    await _project_or_404(db, project_id)
    doc = await _doc_or_404(db, doc_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    await add_audit(db, DEMO_WORKSPACE_ID, "Менеджер", "update", "document", doc.id,
                    new_value=payload.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{project_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    project_id: uuid.UUID, doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    doc = await _doc_or_404(db, doc_id)
    await db.delete(doc)
    await db.commit()