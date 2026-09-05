from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    in_progress = "in_progress"
    review = "review"  # На проверке у заказчика
    completed = "completed"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(String, nullable=True)  # ID из ordersCategories.js
    subcategory_id = Column(String, nullable=True)
    subsubcategory_id = Column(String, nullable=True)
    budget_from = Column(Numeric(10, 2), nullable=True)
    budget_to = Column(Numeric(10, 2), nullable=True)
    allow_higher_price = Column(Boolean, default=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.open, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders_created")
    files = relationship("OrderFile", back_populates="order", cascade="all, delete-orphan")
    skills = relationship("OrderSkill", back_populates="order", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="order", cascade="all, delete-orphan")
    notes = relationship("OrderNote", back_populates="order", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="order")


class OrderFile(Base):
    __tablename__ = "order_files"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="files")


class OrderSkill(Base):
    __tablename__ = "order_skills"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    skill_name = Column(String, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="skills")
