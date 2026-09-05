from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.community import Post, PostImage, Comment, PostLike
from app.schemas.community import PostCreate, PostUpdate, CommentCreate


class CRUDPost(CRUDBase[Post, PostCreate, PostUpdate]):
    def create_with_images(
        self,
        db: Session,
        *,
        obj_in: PostCreate,
        user_id: int
    ) -> Post:
        # Создаем пост
        post_data = obj_in.model_dump(exclude={"images"})
        post_data["user_id"] = user_id
        db_obj = Post(**post_data)
        db.add(db_obj)
        db.flush()

        # Добавляем изображения
        if obj_in.images:
            for idx, image_path in enumerate(obj_in.images):
                image = PostImage(
                    post_id=db_obj.id,
                    image_path=image_path,
                    order_num=idx
                )
                db.add(image)

        db.commit()
        db.refresh(db_obj)
        # Загружаем связанного пользователя через relationship
        from sqlalchemy.orm import joinedload
        db_obj = db.query(Post).options(joinedload(Post.user), joinedload(Post.images)).filter(Post.id == db_obj.id).first()
        return db_obj

    def get_multi_with_counts(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[int] = None
    ):
        from sqlalchemy.orm import joinedload
        query = db.query(Post).options(
            joinedload(Post.user),
            joinedload(Post.images),
            joinedload(Post.comments),
        )
        if user_id:
            query = query.filter(Post.user_id == user_id)

        total = query.count()
        items = query.order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def update_with_images(
        self,
        db: Session,
        *,
        db_obj: Post,
        obj_in: PostUpdate
    ) -> Post:
        # Обновляем пост
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"images"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Обновляем изображения если они переданы
        if obj_in.images is not None:
            # Удаляем старые изображения
            db.query(PostImage).filter(PostImage.post_id == db_obj.id).delete()
            # Добавляем новые
            for idx, image_path in enumerate(obj_in.images):
                image = PostImage(
                    post_id=db_obj.id,
                    image_path=image_path,
                    order_num=idx
                )
                db.add(image)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentCreate]):
    def create_for_post(
        self,
        db: Session,
        *,
        obj_in: CommentCreate,
        post_id: int,
        user_id: int
    ) -> Comment:
        db_obj = Comment(
            post_id=post_id,
            user_id=user_id,
            text=obj_in.text
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_post_id(self, db: Session, *, post_id: int):
        return db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at).all()


class CRUDPostLike:
    def toggle_like(self, db: Session, *, post_id: int, user_id: int) -> bool:
        """Переключает лайк. Возвращает True если лайк добавлен, False если удален"""
        existing = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            return False
        else:
            like = PostLike(post_id=post_id, user_id=user_id)
            db.add(like)
            db.commit()
            return True

    def is_liked(self, db: Session, *, post_id: int, user_id: int) -> bool:
        return db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first() is not None

    def count_likes(self, db: Session, *, post_id: int) -> int:
        return db.query(PostLike).filter(PostLike.post_id == post_id).count()


post = CRUDPost(Post)
comment = CRUDComment(Comment)
post_like = CRUDPostLike()
