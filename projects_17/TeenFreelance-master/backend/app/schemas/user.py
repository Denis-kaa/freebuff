from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    age: Optional[int] = Field(None, ge=14, le=18)
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.executor
    rating: float = 5.0


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    verification_status: str = "unverified"
    balance: float = 0.0
    tf_coins: int = 0
    rating_position: int = 0
    closed_orders_week: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileBase(BaseModel):
    about: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    work_schedule: Optional[str] = None
    inn: Optional[str] = None


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    verification_status: str
    otp_email_verified: bool
    otp_phone_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSkillCreate(BaseModel):
    skill_name: str


class UserSkillResponse(BaseModel):
    id: int
    user_id: int
    skill_name: str

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """История транзакций пользователя на основе завершённых заказов"""
    id: int
    type: str          # "income" | "expense"
    title: str
    amount: float
    status: str        # "completed" | "processing"
    created_at: datetime

    class Config:
        from_attributes = True
