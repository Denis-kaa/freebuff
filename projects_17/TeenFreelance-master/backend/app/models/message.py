from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class MessageType(str, enum.Enum):
    offer_created = "offer_created"  # Исполнитель отправил отклик
    offer_accepted = "offer_accepted"  # Заказчик одобрил отклик
    offer_rejected = "offer_rejected"  # Заказчик отклонил отклик
    offer_withdrawn = "offer_withdrawn"  # Исполнитель отозвал отклик
    text = "text"  # Обычное текстовое сообщение


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)  # Связь с оффером
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Связь с заказом
    message_type = Column(Enum(MessageType, native_enum=False, length=50), nullable=False)
    title = Column(String, nullable=False)  # Заголовок уведомления
    content = Column(Text, nullable=True)  # Дополнительный текст
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="messages_sent")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="messages_received")
    offer = relationship("Offer", back_populates="messages")
    order = relationship("Order", back_populates="messages")
