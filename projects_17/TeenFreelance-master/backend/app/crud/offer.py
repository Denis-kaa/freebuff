from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.offer import Offer, OfferStage, OfferStatus
from app.schemas.offer import OfferCreate, OfferUpdate, OfferStageCreate


class CRUDOffer(CRUDBase[Offer, OfferCreate, OfferUpdate]):
    def create_with_stages(
        self,
        db: Session,
        *,
        obj_in: OfferCreate,
        order_id: int = None,
        executor_id: int
    ) -> Offer:
        # Создаем предложение
        offer_data = obj_in.model_dump(exclude={"stages"})
        # Используем order_id из obj_in если он есть, иначе из параметра
        if not offer_data.get("order_id") and order_id:
            offer_data["order_id"] = order_id
        offer_data["executor_id"] = executor_id
        db_obj = Offer(**offer_data)
        db.add(db_obj)
        db.flush()

        # Добавляем этапы если payment_type == stages
        if obj_in.payment_type.value == "stages" and obj_in.stages:
            for stage_data in obj_in.stages:
                stage = OfferStage(
                    offer_id=db_obj.id,
                    name=stage_data.name,
                    price=stage_data.price,
                    order_num=stage_data.order_num
                )
                db.add(stage)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_order_id(self, db: Session, *, order_id: int):
        return db.query(Offer).filter(Offer.order_id == order_id).all()

    def get_by_executor_id(self, db: Session, *, executor_id: int, skip: int = 0, limit: int = 100):
        return db.query(Offer).filter(Offer.executor_id == executor_id).offset(skip).limit(limit).all()

    def update_with_stages(
        self,
        db: Session,
        *,
        db_obj: Offer,
        obj_in: OfferUpdate
    ) -> Offer:
        # Обновляем предложение
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"stages"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Обновляем этапы если они переданы
        if obj_in.stages is not None:
            # Удаляем старые этапы
            db.query(OfferStage).filter(OfferStage.offer_id == db_obj.id).delete()
            # Добавляем новые
            for stage_data in obj_in.stages:
                stage = OfferStage(
                    offer_id=db_obj.id,
                    name=stage_data.name,
                    price=stage_data.price,
                    order_num=stage_data.order_num
                )
                db.add(stage)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


offer = CRUDOffer(Offer)
