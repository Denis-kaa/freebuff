"""Фикстуры тестов: отдельная тестовая БД pmos_test, изоляция данных."""

import asyncio
import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://pmos:pmos_dev@127.0.0.1:5432/pmos_test"
os.environ["PMOS_TESTING"] = "1"

import pytest
from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401 — регистрирует таблицы в Base.metadata
from app.main import app

DEMO_WS = "00000000-0000-0000-0000-000000000001"


def _create_schema():
    """Создаём схему синхронно (отдельный loop, отдельный движок)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.database import Base

    url = "postgresql+asyncpg://pmos:pmos_dev@127.0.0.1:5432/pmos_test"

    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.seed_rbac import backfill_memberships, seed_rbac

        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, class_=AsyncSession)
        async with Session() as session:
            await seed_rbac(session)
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


_create_schema()


@pytest.fixture(autouse=True)
async def clean_tables(anyio_backend):
    """Чистим таблицы между тестами и гарантируем workspace 1."""
    from sqlalchemy import text

    from app.database import SessionLocal, engine
    from app.seed_rbac import seed_rbac

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE workspace_members, team_members, field_permissions, workspace_invitations, dashboard_widgets, dashboards, views, custom_field_values, custom_fields, tasks, project_items, projects, audit_log, users, workspaces CASCADE"))
        await conn.execute(
            text(
                "INSERT INTO workspaces (id, name, created_at, updated_at, timezone, default_currency) "
                "VALUES (:id, 'test', now(), now(), 'UTC', 'RUB') ON CONFLICT (id) DO NOTHING"
            ),
            {"id": DEMO_WS},
        )
    # TRUNCATE workspaces CASCADE сносит и системные роли (FK) — пересоздаём
    async with SessionLocal() as session:
        await seed_rbac(session)
        await session.commit()



@pytest.fixture
async def client(anyio_backend):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def make_project(client, request):
    """Фабрика проектов: создаёт через API и возвращает объект."""

    async def _make(**overrides):
        data = {
            "title": "Тестовый проект",
            "client_legal_name": "ООО Тест",
            "manager_name": "Денис",
            "stage": "Сигнал",
            "deadline": "2026-09-10",
            "risk_level": "Высокий",
            "payment_percent": "80%",
            "currency": "RUB",
        }
        data.update(overrides)
        res = await client.post("/api/projects", json=data)
        assert res.status_code == 201, res.text
        return res.json()

    return _make
