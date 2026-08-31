"""Hermetic pipeline tests: FakeSource (DI) + in-memory SQLite — no network."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent / "projects_17" / "real_estate_parser"
sys.path.insert(0, str(PROJECT))

from app.core.config import Config  # noqa: E402
from app.core.retry_policy import RetryPolicy  # noqa: E402
from app.pipeline import PropertyPipeline  # noqa: E402
from app.sources.base import Listing, SourceAdapter  # noqa: E402
from app.storage.db import make_engine, make_session_factory, migrate  # noqa: E402
from app.storage.models import Property  # noqa: E402
from app.storage.repository import PropertyRepository  # noqa: E402


class FakeSource(SourceAdapter):
    name = "fake"

    def __init__(self, listings: list[Listing], fail: bool = False):
        self._listings = listings
        self._fail = fail

    async def fetch(self, limit: int = 100) -> list[Listing]:
        if self._fail:
            raise RuntimeError("source down")
        return self._listings[:limit]


def make_listing(ext_id: str, price: float) -> Listing:
    return Listing(
        source="fake",
        external_id=ext_id,
        url=f"https://fake.example/p/{ext_id}",
        title=f"Object {ext_id}",
        price=price,
        currency="USD",
        area_m2=50.0,
        rooms=2.0,
    )


@pytest.fixture()
def repo_factory():
    async def _make():
        engine = make_engine("sqlite+aiosqlite:///:memory:")
        factory = make_session_factory(engine)
        await migrate(factory)
        return factory

    return _make


class TestRepositoryUpsert:
    def test_insert_then_no_duplicate(self, repo_factory):
        async def scenario():
            factory = await repo_factory()
            async with factory() as session:
                repo = PropertyRepository(session)
                _, first = await repo.upsert_listing(make_listing("1", 99.0))
                _, second = await repo.upsert_listing(make_listing("1", 99.0))
                await session.commit()
                total = await repo.count()
            return first, second, total

        outcome, outcome2, total = asyncio.run(scenario())
        assert outcome == "created"
        assert outcome2 == "unchanged"  # duplicate not re-inserted
        assert total == 1

    def test_price_change_recorded(self, repo_factory):
        async def scenario():
            factory = await repo_factory()
            async with factory() as session:
                repo = PropertyRepository(session)
                await repo.upsert_listing(make_listing("1", 99.0))
                _, outcome = await repo.upsert_listing(make_listing("1", 120.0))
                await session.commit()
            return outcome

        assert asyncio.run(scenario()) == "price_changed"


class TestPipeline:
    def test_run_once_processes_all_sources(self, repo_factory):
        async def scenario():
            factory = await repo_factory()
            async with factory() as session:
                repo = PropertyRepository(session)
                config = Config(sources=["fake"], request_delay=0.0, batch_size=10)
                pipeline = PropertyPipeline(
                    config=config,
                    sources=[FakeSource([make_listing("1", 10.0), make_listing("2", 20.0)])],
                    repository=repo,
                    concurrency=2,
                )
                totals = await pipeline.run_once()
            return totals

        totals = asyncio.run(scenario())
        assert totals["fetched"] == 2
        assert totals["created"] == 2
        assert totals["errors"] == 0

    def test_source_failure_does_not_crash_pipeline(self, repo_factory):
        async def scenario():
            factory = await repo_factory()
            async with factory() as session:
                repo = PropertyRepository(session)
                config = Config(sources=["bad"], request_delay=0.0, batch_size=10)
                pipeline = PropertyPipeline(
                    config=config,
                    sources=[FakeSource([], fail=True)],
                    repository=repo,
                    concurrency=2,
                )
                return await pipeline.run_once()

        totals = asyncio.run(scenario())
        assert totals["errors"] == 1

    def test_stop_flag_halts_processing(self, repo_factory):
        async def scenario():
            factory = await repo_factory()
            async with factory() as session:
                repo = PropertyRepository(session)
                config = Config(sources=["fake"], request_delay=0.0, batch_size=10)
                pipeline = PropertyPipeline(
                    config=config,
                    sources=[FakeSource([make_listing(str(i), i) for i in range(100)])],
                    repository=repo,
                    concurrency=1,
                )
                pipeline.stop()
                return await pipeline.run_once()

        totals = asyncio.run(scenario())
        assert totals["fetched"] == 0  # stopped before any work
