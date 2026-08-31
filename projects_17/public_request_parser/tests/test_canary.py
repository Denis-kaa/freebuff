"""Hermetic tests: canary module (P10 controlled live runs)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.canary import CanaryReport, build_source_adapter, run_canary
from app.domain import SearchProfile, SourcePolicy, SourcePolicyStatus
from app.storage import SqliteCheckpointStore, SqliteStorage

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _policy(source_id: str) -> SourcePolicy:
    return SourcePolicy(
        source_id=source_id,
        status=SourcePolicyStatus.ALLOWED,
        access_mode="open_data_api",
        endpoint=f"https://opendata.trudvsem.ru/api/v1/vacancies",
        checked_at=NOW,
        evidence_urls=("https://trudvsem.ru/opendata",),
        can_poll=True,
    )


def _profile() -> SearchProfile:
    return SearchProfile(
        profile_id="canary-test",
        owner_scope="operator",
        version=1,
        service_name="Python backend",
        required_terms=("python",),
        intent_terms=("need", "looking"),
    )


async def _fake_http(url: str) -> bytes:
    if "trudvsem" in url:
        return (FIXTURES / "trudvsem/vacancies_page.json").read_bytes()
    return (FIXTURES / "hh/vacancies_page.json").read_bytes()


@pytest.mark.asyncio
async def test_canary_trudvsem_fetches(tmp_path: Path) -> None:
    db = tmp_path / "canary.db"
    storage = SqliteStorage(str(db))
    checkpoint = SqliteCheckpointStore(storage)
    from app.delivery import TelegramDelivery

    delivery = TelegramDelivery(storage=storage, dry_run=True)

    report = await run_canary(
        source_id="trudvsem",
        policy=_policy("trudvsem"),
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        limit=10,
        http_get=_fake_http,
    )

    assert isinstance(report, CanaryReport)
    assert report.source_id == "trudvsem"
    assert report.fetched == 2
    assert report.source_status == "allowed"
    assert report.error is None
    storage.close()


@pytest.mark.asyncio
async def test_canary_headhunter_fetches(tmp_path: Path) -> None:
    db = tmp_path / "canary-hh.db"
    storage = SqliteStorage(str(db))
    checkpoint = SqliteCheckpointStore(storage)
    from app.delivery import TelegramDelivery

    delivery = TelegramDelivery(storage=storage, dry_run=True)

    report = await run_canary(
        source_id="headhunter",
        policy=_policy("headhunter"),
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        limit=10,
        http_get=_fake_http,
    )

    assert report.source_id == "headhunter"
    assert report.fetched == 2
    assert report.error is None
    storage.close()


@pytest.mark.asyncio
async def test_canary_reports_error_without_crash(tmp_path: Path) -> None:
    db = tmp_path / "canary-err.db"
    storage = SqliteStorage(str(db))
    checkpoint = SqliteCheckpointStore(storage)
    from app.delivery import TelegramDelivery

    delivery = TelegramDelivery(storage=storage, dry_run=True)

    async def bad_http(url: str) -> bytes:
        raise OSError("network down")

    report = await run_canary(
        source_id="trudvsem",
        policy=_policy("trudvsem"),
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        limit=3,
        http_get=bad_http,
    )

    assert report.error is not None
    assert "network down" in report.error
    assert report.fetched == 0
    storage.close()


def test_build_adapter_unknown_source() -> None:
    with pytest.raises(ValueError, match="unknown live source"):
        build_source_adapter(source_id="nope", policy=_policy("nope"))


def test_summary_format() -> None:
    report = CanaryReport(
        source_id="trudvsem",
        source_status="allowed",
        fetched=2,
        new_publications=2,
        accepted=1,
        pending=0,
        rejected=1,
        delivered=1,
        checkpoint="prp-fixture-0002",
        ran_at=NOW,
    )
    text = report.summary()
    assert "canary trudvsem" in text
    assert "fetched=2" in text
    assert "accepted=1" in text