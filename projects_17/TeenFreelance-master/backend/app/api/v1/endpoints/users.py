from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from pathlib import Path
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.crud import user as crud_user
from app.schemas.user import (
    UserResponse,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    UserSkillCreate,
    UserSkillResponse
)

router = APIRouter()

# Директория для загрузки аватаров (используем ту же, что и в files.py)
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение текущего пользователя с вычисляемыми полями"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from app.models.order import Order, OrderStatus
    from app.models.offer import Offer, OfferStatus

    # Подсчёт закрытых заказов за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)

    user_role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).lower()

    if user_role_val == 'executor':
        # Для исполнителя — принятые офферы с завершёнными заказами за неделю
        closed_week = db.query(Offer).join(Order, Offer.order_id == Order.id).filter(
            Offer.executor_id == current_user.id,
            Offer.status == OfferStatus.accepted,
            Order.status == OrderStatus.completed,
            Order.updated_at >= week_ago
        ).count()
    else:
        # Для заказчика — завершённые заказы за неделю
        closed_week = db.query(Order).filter(
            Order.customer_id == current_user.id,
            Order.status == OrderStatus.completed,
            Order.updated_at >= week_ago
        ).count()

    # Рейтинговая позиция: считаем пользователей с более высоким рейтингом + 1
    higher_rated = db.query(func.count(User.id)).filter(
        User.rating > current_user.rating,
        User.is_active == True
    ).scalar() or 0
    rating_position = higher_rated + 1

    # Собираем ответ как dict и добавляем вычисляемые поля
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "phone": current_user.phone,
        "age": current_user.age,
        "avatar_url": current_user.avatar_url,
        "role": current_user.role,
        "rating": current_user.rating,
        "is_active": current_user.is_active,
        "verification_status": current_user.verification_status,
        "balance": float(getattr(current_user, 'balance', 0) or 0),
        "tf_coins": int(getattr(current_user, 'tf_coins', 0) or 0),
        "rating_position": rating_position,
        "closed_orders_week": closed_week,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }
    return user_data


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    name: str = Form(...),
    avatar: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление данных текущего пользователя (имя, аватар)"""
    current_user.name = name
    
    if avatar:
        # Проверка типа файла
        if avatar.content_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {avatar.content_type} is not allowed"
            )
            
        # Генерируем уникальное имя файла
        file_extension = Path(avatar.filename).suffix.lower()
        unique_filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Читаем и сохраняем файл
        contents = await avatar.read()
        if len(contents) > settings.MAX_FILE_SIZE:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large"
            )
            
        with open(file_path, "wb") as f:
            f.write(contents)
            
        # Обновляем URL аватара
        current_user.avatar_url = f"/api/v1/files/{unique_filename}"
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/transactions")
def read_user_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    История транзакций пользователя.
    Формируется на основе завершённых заказов (доходы исполнителя / расходы заказчика).
    """
    from app.models.order import Order, OrderStatus
    from app.models.offer import Offer, OfferStatus

    transactions = []
    user_role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

    if user_role_val == 'executor':
        # Исполнитель: принятые офферы с завершёнными заказами = доход
        accepted_offers = (
            db.query(Offer, Order)
            .join(Order, Offer.order_id == Order.id)
            .filter(
                Offer.executor_id == current_user.id,
                Offer.status == OfferStatus.accepted,
                Order.status == OrderStatus.completed,
            )
            .order_by(Order.updated_at.desc())
            .limit(50)
            .all()
        )
        for offer, order in accepted_offers:
            amount = float(offer.total_price or order.budget_to or 0)
            # Вычитаем комиссию 7%
            net_amount = round(amount * 0.93, 2)
            transactions.append({
                "id": offer.id,
                "type": "income",
                "title": f"Оплата за заказ «{order.title}»",
                "amount": net_amount,
                "status": "completed",
                "created_at": order.updated_at or order.created_at,
            })
    else:
        # Заказчик: завершённые заказы = расход
        completed_orders = (
            db.query(Order)
            .filter(
                Order.customer_id == current_user.id,
                Order.status == OrderStatus.completed,
            )
            .order_by(Order.updated_at.desc())
            .limit(50)
            .all()
        )
        for order in completed_orders:
            amount = float(order.budget_to or order.budget_from or 0)
            transactions.append({
                "id": order.id,
                "type": "expense",
                "title": f"Оплата заказа «{order.title}»",
                "amount": amount,
                "status": "completed",
                "created_at": order.updated_at or order.created_at,
            })

    return transactions


@router.get("/me/profile", response_model=UserProfileResponse)
def read_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение профиля текущего пользователя"""
    profile = crud_user.user_profile.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.post("/me/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def create_user_profile(
    profile_in: UserProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание профиля пользователя"""
    existing = crud_user.user_profile.get_by_user_id(db, user_id=current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )
    return crud_user.user_profile.create_for_user(db, user_id=current_user.id, obj_in=profile_in)


@router.put("/me/profile", response_model=UserProfileResponse)
def update_user_profile(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление профиля пользователя"""
    profile = crud_user.user_profile.get_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return crud_user.user_profile.update(db, db_obj=profile, obj_in=profile_in)


@router.get("/me/skills", response_model=List[UserSkillResponse])
def read_user_skills(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение навыков пользователя"""
    return crud_user.user_skill.get_by_user_id(db, user_id=current_user.id)


@router.post("/me/skills", response_model=UserSkillResponse, status_code=status.HTTP_201_CREATED)
def create_user_skill(
    skill_in: UserSkillCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Добавление навыка пользователю"""
    return crud_user.user_skill.create_for_user(
        db, user_id=current_user.id, skill_name=skill_in.skill_name
    )


@router.delete("/me/skills/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_skill(
    skill_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление навыка пользователя"""
    crud_user.user_skill.remove_by_user_and_skill(
        db, user_id=current_user.id, skill_name=skill_name
    )
    return None
