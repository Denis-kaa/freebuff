from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
from pathlib import Path
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User

router = APIRouter()

# Создаем директорию для загрузки файлов
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    return Path(filename).suffix.lower()


def is_allowed_file_type(content_type: str) -> bool:
    """Проверка типа файла"""
    return content_type in settings.ALLOWED_FILE_TYPES


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Загрузка файла"""
    # Проверка размера файла
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
        )
    
    # Проверка типа файла
    if not is_allowed_file_type(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} is not allowed"
        )
    
    # Генерируем уникальное имя файла
    file_extension = get_file_extension(file.filename)
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Сохраняем файл
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Возвращаем информацию о файле
    return {
        "file_path": str(file_path),
        "file_name": file.filename,
        "file_size": file_size,
        "file_type": file.content_type,
        "url": f"/api/v1/files/{unique_filename}"
    }


@router.get("/{filename}")
async def get_file(filename: str):
    """Получение файла по имени"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """Удаление файла"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # В будущем можно добавить проверку прав доступа
    os.remove(file_path)
    return None
