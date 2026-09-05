from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.crud.base import CRUDBase
from app.models.message import Message, MessageType
from app.schemas.message import MessageCreate, MessageUpdate


class CRUDMessage(CRUDBase[Message, MessageCreate, MessageUpdate]):
    def get_user_messages(
        self,
        db: Session,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Получение всех сообщений пользователя (входящие и исходящие)"""
        return (
            db.query(Message)
            .filter(
                or_(
                    Message.from_user_id == user_id,
                    Message.to_user_id == user_id
                )
            )
            .order_by(Message.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_conversation(
        self,
        db: Session,
        *,
        user1_id: int,
        user2_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Получение переписки между двумя пользователями"""
        return (
            db.query(Message)
            .filter(
                or_(
                    and_(
                        Message.from_user_id == user1_id,
                        Message.to_user_id == user2_id
                    ),
                    and_(
                        Message.from_user_id == user2_id,
                        Message.to_user_id == user1_id
                    )
                )
            )
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_unread_count(
        self,
        db: Session,
        *,
        user_id: int
    ) -> int:
        """Получение количества непрочитанных сообщений"""
        return (
            db.query(Message)
            .filter(
                and_(
                    Message.to_user_id == user_id,
                    Message.is_read == False
                )
            )
            .count()
        )

    def mark_as_read(
        self,
        db: Session,
        *,
        message_id: int,
        user_id: int
    ) -> Message:
        """Отметить сообщение как прочитанное"""
        message = self.get(db, id=message_id)
        if message and message.to_user_id == user_id:
            message.is_read = True
            db.add(message)
            db.commit()
            db.refresh(message)
        return message


message = CRUDMessage(Message)
