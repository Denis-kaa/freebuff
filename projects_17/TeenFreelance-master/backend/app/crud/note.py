from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.note import OrderNote
from app.schemas.note import OrderNoteCreate, OrderNoteUpdate


class CRUDOrderNote(CRUDBase[OrderNote, OrderNoteCreate, OrderNoteUpdate]):
    def get_by_order_and_user(
        self,
        db: Session,
        *,
        order_id: int,
        user_id: int
    ) -> Optional[OrderNote]:
        return db.query(OrderNote).filter(
            OrderNote.order_id == order_id,
            OrderNote.user_id == user_id
        ).first()

    def get_by_order_id(self, db: Session, *, order_id: int, user_id: int):
        return db.query(OrderNote).filter(
            OrderNote.order_id == order_id,
            OrderNote.user_id == user_id
        ).all()

    def create_or_update(
        self,
        db: Session,
        *,
        obj_in: OrderNoteCreate,
        order_id: int,
        user_id: int
    ) -> OrderNote:
        existing = self.get_by_order_and_user(db, order_id=order_id, user_id=user_id)
        if existing:
            return self.update(db, db_obj=existing, obj_in=OrderNoteUpdate(note_text=obj_in.note_text))
        else:
            db_obj = OrderNote(
                order_id=order_id,
                user_id=user_id,
                note_text=obj_in.note_text
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj


order_note = CRUDOrderNote(OrderNote)
