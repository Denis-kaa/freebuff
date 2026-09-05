"""Асинхронный движок SQLAlchemy и управление сессиями."""
import os
from collections.abc import AsyncGenerator

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()

engine_options = {
    "echo": False,
    "pool_pre_ping": True,
}
if os.getenv("PMOS_TESTING") == "1":
    # Tests run requests in multiple event loops; pooled asyncpg connections are loop-bound.
    engine_options["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **engine_options)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-зависимость: даёт сессию БД на время запроса."""
    async with SessionLocal() as session:
        yield session
