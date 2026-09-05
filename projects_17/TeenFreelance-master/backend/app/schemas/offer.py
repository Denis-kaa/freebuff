from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.offer import PaymentType, OfferStatus


class OfferStageCreate(BaseModel):
    name: str
    price: Decimal
    order_num: int


class OfferStageResponse(BaseModel):
    id: int
    name: str
    price: Decimal
    order_num: int

    class Config:
        from_attributes = True


class OfferBase(BaseModel):
    description: str
    total_price: Decimal
    payment_type: PaymentType = PaymentType.full
    deadline: Optional[datetime] = None
    stages: Optional[List[OfferStageCreate]] = []


class OfferCreate(OfferBase):
    order_id: int


class OfferUpdate(BaseModel):
    description: Optional[str] = None
    total_price: Optional[Decimal] = None
    payment_type: Optional[PaymentType] = None
    deadline: Optional[datetime] = None
    status: Optional[OfferStatus] = None
    stages: Optional[List[OfferStageCreate]] = None


class OfferResponse(OfferBase):
    id: int
    order_id: int
    executor_id: int
    status: OfferStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    stages: List[OfferStageResponse] = []

    class Config:
        from_attributes = True
