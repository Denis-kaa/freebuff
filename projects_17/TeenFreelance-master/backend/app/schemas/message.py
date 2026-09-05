from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.message import MessageType


class MessageBase(BaseModel):
    message_type: MessageType
    title: str
    content: Optional[str] = None
    offer_id: Optional[int] = None
    order_id: Optional[int] = None


class MessageCreate(MessageBase):
    to_user_id: int


class MessageUpdate(BaseModel):
    is_read: Optional[bool] = None


class MessageResponse(MessageBase):
    id: int
    from_user_id: int
    to_user_id: int
    is_read: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageWithUsers(MessageResponse):
    from_user_name: str
    to_user_name: str
    offer_data: Optional[dict] = None
    order_data: Optional[dict] = None
