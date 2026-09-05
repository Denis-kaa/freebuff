from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PostImageResponse(BaseModel):
    id: int
    image_path: str
    order_num: int

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    user_name: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    text: str


class PostCreate(PostBase):
    images: Optional[List[str]] = []  # Список путей к изображениям


class PostUpdate(BaseModel):
    text: Optional[str] = None
    images: Optional[List[str]] = None


class PostResponse(PostBase):
    id: int
    user_id: int
    user_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    images: List[PostImageResponse] = []
    comments_count: int = 0
    likes_count: int = 0
    is_liked: bool = False

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    text: str


class PostListResponse(BaseModel):
    items: List[PostResponse]
    total: int
    page: int
    page_size: int
