from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class PaymentType(str, enum.Enum):
    full = "full"
    stages = "stages"


class OfferStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    payment_type = Column(Enum(PaymentType), default=PaymentType.full, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(OfferStatus), default=OfferStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="offers")
    executor = relationship("User", back_populates="offers")
    stages = relationship("OfferStage", back_populates="offer", cascade="all, delete-orphan", order_by="OfferStage.order_num")
    messages = relationship("Message", back_populates="offer")


class OfferStage(Base):
    __tablename__ = "offer_stages"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    order_num = Column(Integer, nullable=False)  # Порядок этапа
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    offer = relationship("Offer", back_populates="stages")
