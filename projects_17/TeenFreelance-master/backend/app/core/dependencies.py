from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.models.user import User

# Зависимости для получения текущего пользователя
def get_current_user_dependency() -> User:
    """Зависимость для получения текущего пользователя"""
    return Depends(get_current_active_user)

# Зависимость для получения БД сессии
def get_db_dependency() -> Session:
    """Зависимость для получения сессии БД"""
    return Depends(get_db)
