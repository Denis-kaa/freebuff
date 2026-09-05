from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.crud import note as crud_note, order as crud_order
from app.schemas.note import OrderNoteCreate, OrderNoteUpdate, OrderNoteResponse

router = APIRouter()


@router.get("/orders/{order_id}/notes", response_model=List[OrderNoteResponse])
def read_order_notes(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение заметок к заказу"""
    # Проверяем существование заказа
    order = crud_order.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return crud_note.order_note.get_by_order_id(db, order_id=order_id, user_id=current_user.id)


@router.post("/orders/{order_id}/notes", response_model=OrderNoteResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_order_note(
    order_id: int,
    note_in: OrderNoteCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание или обновление заметки к заказу"""
    # Проверяем существование заказа
    order = crud_order.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return crud_note.order_note.create_or_update(
        db, obj_in=note_in, order_id=order_id, user_id=current_user.id
    )


@router.put("/notes/{note_id}", response_model=OrderNoteResponse)
def update_order_note(
    note_id: int,
    note_in: OrderNoteUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление заметки"""
    note = crud_note.order_note.get(db, id=note_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    if note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return crud_note.order_note.update(db, db_obj=note, obj_in=note_in)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order_note(
    note_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление заметки"""
    note = crud_note.order_note.get(db, id=note_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    if note.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    crud_note.order_note.remove(db, id=note_id)
    return None
