"""Фикстуры тестов: отдельная тестовая БД pmos_test, изоляция данных."""

import asyncio
import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://pmos:pmos_dev@127.0.0.1:5432/pmos_test"

import pytest
from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401 — регистрирует таблицы в Base.metadata

DEMO_WS = "00000000-0000-0000-0000-000000000001"


def _create_schema():
    """Создаём схему синхронно (отдельный loop, отдельный движок)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.database import Base

    url = "postgresql+asyncpg://pmos:pmos_dev@127.0.0.1:5432/pmos_test"

    async def _run():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())


_create_schema()


@pytest.fixture(autouse=True)
async def clean_tables():
    """Чистим таблицы между тестами и гарантируем workspace 1."""
    from sqlalchemy import text

    from app.database import engine

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE dashboard_widgets, dashboards, views, custom_field_values, custom_fields, tasks, project_items, projects, audit_log, users, workspaces CASCADE"))
        await conn.execute(
            text(
                "INSERT INTO workspaces (id, name, created_at, updated_at) "
                "VALUES (:id, 'test', now(), now()) ON CONFLICT (id) DO NOTHING"
            ),
            {"id": DEMO_WS},
        )
    await engine.dispose()


@pytest.fixture
async def client():
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
