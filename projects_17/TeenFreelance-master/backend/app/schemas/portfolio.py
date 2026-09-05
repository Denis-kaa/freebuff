from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PortfolioFileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    class Config:
        from_attributes = True


class PortfolioItemBase(BaseModel):
    title: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cover_image: Optional[str] = None


class PortfolioItemCreate(PortfolioItemBase):
    files: Optional[List[str]] = []  # Список путей к файлам


class PortfolioItemUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    cover_image: Optional[str] = None
    files: Optional[List[str]] = None


class PortfolioItemResponse(PortfolioItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    files: List[PortfolioFileResponse] = []

    class Config:
        from_attributes = True
