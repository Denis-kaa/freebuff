from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    executor = "executor"
    customer = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.executor, nullable=False)
    avatar_url = Column(String, nullable=True)
    rating = Column(Float, default=5.0)
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0, nullable=False)
    tf_coins = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    orders_created = relationship("Order", foreign_keys="Order.customer_id", back_populates="customer")
    offers = relationship("Offer", back_populates="executor")
    portfolio_items = relationship("PortfolioItem", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("OrderNote", back_populates="user", cascade="all, delete-orphan")
    messages_sent = relationship("Message", foreign_keys="Message.from_user_id", back_populates="from_user")
    messages_received = relationship("Message", foreign_keys="Message.to_user_id", back_populates="to_user")

    @property
    def verification_status(self) -> str:
        return self.profile.verification_status if self.profile else "unverified"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    about = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    work_schedule = Column(String, nullable=True)
    inn = Column(String, nullable=True)
    verification_status = Column(String, default="unverified")  # unverified, verified, rejected
    otp_email_verified = Column(Boolean, default=False)
    otp_phone_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_name = Column(String, nullable=False)

    # Relationships
    user = relationship("User", back_populates="skills")
