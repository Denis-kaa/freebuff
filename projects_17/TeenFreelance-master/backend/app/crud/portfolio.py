from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.portfolio import PortfolioItem, PortfolioFile
from app.schemas.portfolio import PortfolioItemCreate, PortfolioItemUpdate


class CRUDPortfolioItem(CRUDBase[PortfolioItem, PortfolioItemCreate, PortfolioItemUpdate]):
    def create_with_files(
        self,
        db: Session,
        *,
        obj_in: PortfolioItemCreate,
        user_id: int
    ) -> PortfolioItem:
        # Создаем элемент портфолио
        item_data = obj_in.dict(exclude={"files"})
        item_data["user_id"] = user_id
        db_obj = PortfolioItem(**item_data)
        db.add(db_obj)
        db.flush()

        # Добавляем файлы
        if obj_in.files:
            for idx, file_path in enumerate(obj_in.files):
                file = PortfolioFile(
                    portfolio_id=db_obj.id,
                    file_path=file_path,
                    file_name=file_path.split("/")[-1],
                    file_type=None,
                    file_size=None
                )
                db.add(file)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user_id(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100):
        return db.query(PortfolioItem).filter(
            PortfolioItem.user_id == user_id
        ).offset(skip).limit(limit).all()

    def update_with_files(
        self,
        db: Session,
        *,
        db_obj: PortfolioItem,
        obj_in: PortfolioItemUpdate
    ) -> PortfolioItem:
        # Обновляем элемент
        update_data = obj_in.dict(exclude_unset=True, exclude={"files"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Обновляем файлы если они переданы
        if obj_in.files is not None:
            # Удаляем старые файлы
            db.query(PortfolioFile).filter(PortfolioFile.portfolio_id == db_obj.id).delete()
            # Добавляем новые
            for file_path in obj_in.files:
                file = PortfolioFile(
                    portfolio_id=db_obj.id,
                    file_path=file_path,
                    file_name=file_path.split("/")[-1]
                )
                db.add(file)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


portfolio_item = CRUDPortfolioItem(PortfolioItem)
