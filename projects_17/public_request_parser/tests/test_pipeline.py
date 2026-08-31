"""Hermetic tests P8 offline pipeline + CLI surface."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.delivery import TelegramDelivery
from app.domain import MatchOutcome, Publication, SearchProfile
from app.pipeline import format_report, run_offline_slice
from app.rss_atom import FixtureFeedAdapter
from app.storage import SqliteCheckpointStore, SqliteStorage

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def _profile() -> SearchProfile:
    return SearchProfile(
        profile_id="profile-python",
        owner_scope="operator",
        version=1,
        service_name="Python разработка",
        required_terms=("python",),
        optional_terms=("backend",),
        intent_terms=("need", "looking", "нужен"),
    )


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage]:
    db = SqliteStorage(tmp_path / "pipeline.db")
    yield db
    db.close()


@pytest.mark.asyncio
async def test_offline_slice_runs_end_to_end(storage: SqliteStorage) -> None:
    """Fixture-feed → normalize → store → match → deliver: полный путь."""
    adapter = FixtureFeedAdapter("rss-fixture", (FIXTURES / "rss/sample_rss.xml").read_bytes())
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    result = await run_offline_slice(
        adapter=adapter,
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert result.fetched == 2
    assert result.new_publications == 2
    assert result.stored_decisions == 2
    assert result.accepted == 1
    assert result.rejected == 1
    assert result.pending == 0
    assert result.delivered == 1
    assert result.checkpoint is not None

    # Checkpoint упёрся в последний item.
    stored = await checkpoint.get("rss-fixture")
    assert stored == result.checkpoint
    # Доставка записана в storage (dry-run → SKIPPED).
    assert storage.count_publications() == 2


@pytest.mark.asyncio
async def test_pipeline_repeat_is_idempotent(storage: SqliteStorage) -> None:
    """Второй прогон не создаёт публикации/дубликаты доставки."""
    adapter = FixtureFeedAdapter("rss-fixture", (FIXTURES / "rss/sample_rss.xml").read_bytes())
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    first = await run_offline_slice(
        adapter=adapter,
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )
    second = await run_offline_slice(
        adapter=adapter,
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )

    assert first.new_publications == 2
    assert second.fetched == 0  # checkpoint-resume: новые items отсутствуют
    assert storage.count_publications() == 2


@pytest.mark.asyncio
async def test_ttl_expiry_after_pipeline_keeps_cards(
    storage: SqliteStorage,
) -> None:
    """После TTL словарь публикаций остаётся, но content очищен."""
    adapter = FixtureFeedAdapter("rss-fixture", (FIXTURES / "rss/sample_rss.xml").read_bytes())
    checkpoint = SqliteCheckpointStore(storage)
    delivery = TelegramDelivery(storage=storage, dry_run=True)

    await run_offline_slice(
        adapter=adapter,
        profile=_profile(),
        storage=storage,
        checkpoint=checkpoint,
        delivery=delivery,
        owner_scope="operator",
        fetched_at=NOW,
    )
    # TTL в pipeline = 7 дней: через день контент ещё не истёк.
    assert storage.expire_full_text(NOW + timedelta(days=1)) == 0
    # Через 8 дней контент исчезает, строки остаются.
    assert storage.expire_full_text(NOW + timedelta(days=8)) == 2
    pubs = storage.list_publications(source_id="rss-fixture")
    assert len(pubs) == 2
    assert all(pub.content is None for pub in pubs)
    assert all(pub.title for pub in pubs)


def test_backup_creates_usable_db(tmp_path: Path, storage: SqliteStorage) -> None:
    """backup_to создаёт валидную копию с теми же данными."""
    storage.save_publication(
        Publication(
            source_id="s", item_id="i", canonical_url="https://x.test/i",
            title="t", fetched_at=NOW,
        )
    )
    backup_path = storage.backup_to(tmp_path / "backup.db")

    restored = SqliteStorage(backup_path)
    assert restored.get_publication("s:i") is not None
    restored.close()