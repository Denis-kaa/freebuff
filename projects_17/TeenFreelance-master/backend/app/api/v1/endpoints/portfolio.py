from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.crud import portfolio as crud_portfolio
from app.schemas.portfolio import PortfolioItemCreate, PortfolioItemUpdate, PortfolioItemResponse

router = APIRouter()


@router.get("", response_model=List[PortfolioItemResponse])
def read_portfolio(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: int = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Получение портфолио"""
    target_user_id = user_id if user_id else current_user.id
    return crud_portfolio.portfolio_item.get_by_user_id(
        db, user_id=target_user_id, skip=skip, limit=limit
    )


@router.get("/{item_id}", response_model=PortfolioItemResponse)
def read_portfolio_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Получение элемента портфолио по ID"""
    item = crud_portfolio.portfolio_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    return item


@router.post("", response_model=PortfolioItemResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio_item(
    item_in: PortfolioItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание элемента портфолио"""
    return crud_portfolio.portfolio_item.create_with_files(
        db, obj_in=item_in, user_id=current_user.id
    )


@router.put("/{item_id}", response_model=PortfolioItemResponse)
def update_portfolio_item(
    item_id: int,
    item_in: PortfolioItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление элемента портфолио"""
    item = crud_portfolio.portfolio_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    if item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return crud_portfolio.portfolio_item.update_with_files(db, db_obj=item, obj_in=item_in)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление элемента портфолио"""
    item = crud_portfolio.portfolio_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    if item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    crud_portfolio.portfolio_item.remove(db, id=item_id)
    return None
