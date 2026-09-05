from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrderNoteBase(BaseModel):
    note_text: str


class OrderNoteCreate(OrderNoteBase):
    pass


class OrderNoteUpdate(BaseModel):
    note_text: str


class OrderNoteResponse(OrderNoteBase):
    id: int
    user_id: int
    order_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
