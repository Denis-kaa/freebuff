from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus


class OrderBase(BaseModel):
    title: str
    description: str
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    subsubcategory_id: Optional[str] = None
    budget_from: Optional[Decimal] = None
    budget_to: Optional[Decimal] = None
    allow_higher_price: bool = False
    deadline: Optional[datetime] = None
    skills: Optional[List[str]] = []


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    subsubcategory_id: Optional[str] = None
    budget_from: Optional[Decimal] = None
    budget_to: Optional[Decimal] = None
    allow_higher_price: Optional[bool] = None
    deadline: Optional[datetime] = None
    status: Optional[OrderStatus] = None
    skills: Optional[List[str]] = None


class OrderFileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    class Config:
        from_attributes = True


class OrderSkillResponse(BaseModel):
    id: int
    skill_name: str

    class Config:
        from_attributes = True


class OrderResponse(OrderBase):
    id: int
    customer_id: int
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    files: List[OrderFileResponse] = []
    skills: List[OrderSkillResponse] = []
    customer_name: Optional[str] = None
    customer_avatar_url: Optional[str] = None
    offers_count: int = 0
    customer_projects_count: int = 0
    customer_hired_percent: float = 0.0

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
