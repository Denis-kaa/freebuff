from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.user import User, UserProfile, UserSkill
from app.schemas.user import UserCreate, UserProfileCreate, UserProfileUpdate, UserSkillCreate
from app.core.security import get_password_hash


class CRUDUser(CRUDBase[User, UserCreate, UserCreate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            password_hash=get_password_hash(obj_in.password),
            name=obj_in.name,
            phone=obj_in.phone,
            age=obj_in.age,
            role=obj_in.role,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        from app.core.security import verify_password
        if not verify_password(password, user.password_hash):
            return None
        return user


class CRUDUserProfile(CRUDBase[UserProfile, UserProfileCreate, UserProfileUpdate]):
    def get_by_user_id(self, db: Session, *, user_id: int) -> Optional[UserProfile]:
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def create_for_user(self, db: Session, *, user_id: int, obj_in: UserProfileCreate) -> UserProfile:
        db_obj = UserProfile(user_id=user_id, **obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDUserSkill(CRUDBase[UserSkill, UserSkillCreate, UserSkillCreate]):
    def get_by_user_id(self, db: Session, *, user_id: int):
        return db.query(UserSkill).filter(UserSkill.user_id == user_id).all()

    def create_for_user(self, db: Session, *, user_id: int, skill_name: str) -> UserSkill:
        db_obj = UserSkill(user_id=user_id, skill_name=skill_name)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_by_user_and_skill(self, db: Session, *, user_id: int, skill_name: str):
        db_obj = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_name == skill_name
        ).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()
        return db_obj


user = CRUDUser(User)
user_profile = CRUDUserProfile(UserProfile)
user_skill = CRUDUserSkill(UserSkill)
