"""storage/db.py — engine/session factory.

REP_DATABASE_URL picks the backend: postgresql+asyncpg://… on the server,
sqlite+aiosqlite:///… for local development (v1 fallback, 04_ARCHITECTURE.md).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


def make_engine(database_url: str):
    if not database_url:
        raise ValueError(
            "REP_DATABASE_URL is not set (postgresql+asyncpg:// or sqlite+aiosqlite:///)"
        )
    return create_async_engine(database_url, future=True)


def make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def migrate(factory: async_sessionmaker[AsyncSession]) -> None:
    """Create tables if missing (v1; PG deployments may prefer SQL migrations)."""
    engine = factory.kw["bind"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
