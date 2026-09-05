from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.security import get_current_active_user, verify_token
from app.models.user import User
from typing import Union
from app.crud import community as crud_community
from app.schemas.community import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    CommentCreate,
    CommentResponse
)

router = APIRouter()

# Опциональная авторизация: возвращает пользователя если токен есть, иначе None
_optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False   # ← не бросать 401 если токен отсутствует
)


def get_optional_user(
    token: Optional[str] = Depends(_optional_oauth2),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Возвращает текущего пользователя если токен валиден, иначе — None."""
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    return db.query(User).filter(User.email == email, User.is_active == True).first()


@router.get("/posts", response_model=PostListResponse)
def read_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Получение списка постов"""
    items, total = crud_community.post.get_multi_with_counts(
        db, skip=skip, limit=limit, user_id=user_id
    )
    
    # Добавляем информацию о лайках с проверкой авторизации
    posts_with_likes = []
    for post in items:
        is_liked = False
        if current_user:
            is_liked = crud_community.post_like.is_liked(
                db, post_id=post.id, user_id=current_user.id
            )

        post_dict = {
            "id": post.id,
            "user_id": post.user_id,
            "user_name": post.user.name,
            "text": post.text,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "images": post.images,
            "comments_count": len(post.comments),
            "likes_count": crud_community.post_like.count_likes(db, post_id=post.id),
            "is_liked": is_liked
        }
        posts_with_likes.append(post_dict)
        
    
    return PostListResponse(
        items=posts_with_likes,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/posts/{post_id}", response_model=PostResponse)
def read_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Получение поста по ID"""
    post = crud_community.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return {
        "id": post.id,
        "user_id": post.user_id,
        "user_name": post.user.name,
        "text": post.text,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "images": post.images,
        "comments_count": len(post.comments),
        "likes_count": crud_community.post_like.count_likes(db, post_id=post.id),
        "is_liked": False  # Будет обновлено на фронтенде
    }


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание поста"""
    post = crud_community.post.create_with_images(
        db, obj_in=post_in, user_id=current_user.id
    )
    
    # Возвращаем данные в формате, соответствующем PostResponse
    # post.user должен быть загружен через joinedload в CRUD
    return {
        "id": post.id,
        "user_id": post.user_id,
        "user_name": post.user.name if post.user else current_user.name,
        "text": post.text,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "images": post.images if hasattr(post, 'images') and post.images else [],
        "comments_count": 0,
        "likes_count": 0,
        "is_liked": False
    }


@router.put("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Обновление поста"""
    post = crud_community.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    updated_post = crud_community.post.update_with_images(db, db_obj=post, obj_in=post_in)
    
    # Возвращаем данные в формате, соответствующем PostResponse
    return {
        "id": updated_post.id,
        "user_id": updated_post.user_id,
        "user_name": updated_post.user.name if updated_post.user else current_user.name,
        "text": updated_post.text,
        "created_at": updated_post.created_at,
        "updated_at": updated_post.updated_at,
        "images": updated_post.images if hasattr(updated_post, 'images') else [],
        "comments_count": len(updated_post.comments) if hasattr(updated_post, 'comments') else 0,
        "likes_count": crud_community.post_like.count_likes(db, post_id=updated_post.id),
        "is_liked": False  # Будет обновлено на фронтенде
    }


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Удаление поста"""
    post = crud_community.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    crud_community.post.remove(db, id=post_id)
    return None


@router.post("/posts/{post_id}/like", status_code=status.HTTP_200_OK)
def toggle_post_like(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Переключение лайка на посте"""
    post = crud_community.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    is_liked = crud_community.post_like.toggle_like(
        db, post_id=post_id, user_id=current_user.id
    )
    return {"is_liked": is_liked, "likes_count": crud_community.post_like.count_likes(db, post_id=post_id)}


@router.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
def read_post_comments(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Получение комментариев к посту"""
    comments = crud_community.comment.get_by_post_id(db, post_id=post_id)
    return [
        {
            "id": c.id,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "user_name": c.user.name,
            "text": c.text,
            "created_at": c.created_at
        }
        for c in comments
    ]


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Создание комментария к посту"""
    post = crud_community.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    comment = crud_community.comment.create_for_post(
        db, obj_in=comment_in, post_id=post_id, user_id=current_user.id
    )
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "user_name": comment.user.name,
        "text": comment.text,
        "created_at": comment.created_at
    }
