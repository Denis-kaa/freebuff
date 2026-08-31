"""storage/models.py — SQLAlchemy models for parsed real-estate objects.

Tables (04_ARCHITECTURE.md §Модель данных):
- property        — актуальное состояние объекта (natural key: source+external_id)
- property_event  — история изменений (created / price_changed / removed / updated)
- run_log         — результат каждого прогона (для /stats и /errors в боте)
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# SQLite only autoincrements plain INTEGER primary keys — use a dialect variant
# so the same model works on both PostgreSQL (BIGINT) and SQLite (INTEGER).
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class Property(Base):
    __tablename__ = "property"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_property_source_extid"),
        Index("ix_property_url_hash", "source", "url_hash"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    area_m2: Mapped[float | None] = mapped_column(Numeric(8, 2))
    rooms: Mapped[float | None] = mapped_column(Numeric(3, 1))
    address: Mapped[str | None] = mapped_column(Text)
    property_type: Mapped[str | None] = mapped_column(String(32))
    raw: Mapped[str | None] = mapped_column(Text)  # JSON
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PropertyEvent(Base):
    __tablename__ = "property_event"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(BigIntPk, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # created|price_changed|removed|updated
    old_value: Mapped[str | None] = mapped_column(Text)  # JSON
    new_value: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunLog(Base):
    __tablename__ = "run_log"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")  # running|ok|failed
