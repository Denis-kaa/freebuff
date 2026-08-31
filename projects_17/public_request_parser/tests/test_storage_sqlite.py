"""Hermetic tests SQLite/WAL storage P6."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.domain import (
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    MatchOutcome,
    Publication,
    PublicationStatus,
    SearchProfile,
)
from collections.abc import Iterator

from app.storage import SqliteCheckpointStore, SqliteStorage

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_publication(
    *,
    item_id: str = "item-1",
    title: str = "Need a python backend",
    content: str | None = "Full text body",
    source_id: str = "fixture-source",
) -> Publication:
    """Публикация для тестов storage."""
    return Publication(
        source_id=source_id,
        item_id=item_id,
        canonical_url=f"https://example.test/items/{item_id}",
        title=title,
        summary="Short summary",
        content=content,
        published_at=NOW,
        fetched_at=NOW,
        metadata={"feed_format": "rss", "categories": "python"},
    )


def make_decision(
    *,
    outcome: MatchOutcome = MatchOutcome.ACCEPT,
    profile_id: str = "profile-1",
    profile_version: int = 1,
) -> MatchDecision:
    """Decision с объяснением для storage."""
    return MatchDecision(
        publication_key="fixture-source:item-1",
        profile_id=profile_id,
        profile_version=profile_version,
        outcome=outcome,
        score=0.9,
        matched_terms=("python",),
        reasons=("required term matched: python",),
        rules_snapshot={"required_terms": ("python",)},
        decided_at=NOW,
    )


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage]:
    """Файловая SQLite-БД в tmp_path; WAL активен."""
    db = SqliteStorage(tmp_path / "test.db")
    yield db
    db.close()


def test_wal_mode_and_schema_version(storage: SqliteStorage, tmp_path: Path) -> None:
    """WAL включён, миграции доводят user_version до 2 и идемпотентны."""
    mode = storage._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    assert storage.schema_version() == 2

    reopened = SqliteStorage(tmp_path / "test.db")
    assert reopened.schema_version() == 2
    reopened.close()


def test_save_publication_is_idempotent_and_dedups_by_url(
    storage: SqliteStorage,
) -> None:
    """Один publication → одна строка; дубль по item_key или URL не создаётся."""
    assert storage.save_publication(make_publication()) is True
    assert storage.save_publication(make_publication()) is False
    assert storage.count_publications() == 1

    # Тот же canonical_url, другой item_id → тоже ignore (URL UNIQUE).
    duplicate_url = Publication(
        source_id="fixture-source",
        item_id="item-2",
        canonical_url="https://example.test/items/item-1",  # тот же URL
        title="Need a python backend",
        fetched_at=NOW,
    )
    assert storage.save_publication(duplicate_url) is False
    assert storage.count_publications() == 1


def test_publication_roundtrip_keeps_fields(storage: SqliteStorage) -> None:
    """Все поля и metadata сохраняются и возвращаются (кроме TTL-контента)."""
    publication = make_publication()
    storage.save_publication(publication)

    loaded = storage.get_publication(publication.item_key)

    assert loaded is not None
    assert loaded.title == publication.title
    assert loaded.content == publication.content
    assert loaded.source_id == "fixture-source"
    assert loaded.published_at == NOW
    assert loaded.fetched_at == NOW
    assert loaded.metadata == {"feed_format": "rss", "categories": "python"}
    assert loaded.status is PublicationStatus.NEW


def test_ttl_cleanup_removes_content_keeps_metadata(storage: SqliteStorage) -> None:
    """Истёкший TTL обнуляет content, но сохраняет строку и metadata."""
    storage.save_publication(make_publication(), text_ttl=timedelta(days=1))

    cleaned = storage.expire_full_text(NOW + timedelta(days=2))

    assert cleaned == 1
    loaded = storage.get_publication("fixture-source:item-1")
    assert loaded is not None
    assert loaded.content is None
    assert loaded.title == "Need a python backend"
    assert loaded.metadata == {"feed_format": "rss", "categories": "python"}
    # Повторный cleanup идемпотентен.
    assert storage.expire_full_text(NOW + timedelta(days=3)) == 0


def test_ttl_not_expired_keeps_content(storage: SqliteStorage) -> None:
    """Не истёкший TTL не трогается."""
    storage.save_publication(make_publication(), text_ttl=timedelta(days=7))

    assert storage.expire_full_text(NOW + timedelta(days=1)) == 0
    loaded = storage.get_publication("fixture-source:item-1")
    assert loaded is not None
    assert loaded.content == "Full text body"


def test_no_ttl_means_text_never_expires(storage: SqliteStorage) -> None:
    """Без TTL полный текст сохраняется без срока и не чистится."""
    storage.save_publication(make_publication(), text_ttl=None)

    assert storage.expire_full_text(NOW + timedelta(days=3650)) == 0
    loaded = storage.get_publication("fixture-source:item-1")
    assert loaded is not None
    assert loaded.content == "Full text body"


def test_full_text_disabled_never_stores_content(storage: SqliteStorage) -> None:
    """allow_full_text=False → контент не сохраняется даже при переданном."""
    storage.save_publication(
        make_publication(content="secret body"), allow_full_text=False
    )
    loaded = storage.get_publication("fixture-source:item-1")
    assert loaded is not None
    assert loaded.content is None


def test_max_text_chars_caps_stored_content(storage: SqliteStorage) -> None:
    """Кап применяется к полному тексту перед записью."""
    storage.save_publication(make_publication(content="a" * 500), max_text_chars=120)

    loaded = storage.get_publication("fixture-source:item-1")
    assert loaded is not None
    assert loaded.content is not None
    assert len(loaded.content) == 120


def test_checkpoint_roundtrip_and_upsert(storage: SqliteStorage) -> None:
    """Checkpoint сохраняется, переписывается и возвращается."""
    assert storage.get_checkpoint("source-1") is None

    storage.set_checkpoint("source-1", "item-1")
    assert storage.get_checkpoint("source-1") == "item-1"

    storage.set_checkpoint("source-1", "item-2")
    assert storage.get_checkpoint("source-1") == "item-2"
    assert storage.count_publications() == 0  # чекпоинт не создаёт публикации


def test_decision_roundtrip_and_idempotency(storage: SqliteStorage) -> None:
    """Decision сохраняется один раз и читается со всеми полями."""
    storage.save_publication(make_publication())
    decision = make_decision(outcome=MatchOutcome.ACCEPT)

    assert storage.save_decision(decision) is True
    assert storage.save_decision(decision) is False
    assert storage.count_decisions() == 1

    loaded = storage.get_decision("fixture-source:item-1", "profile-1", 1)

    assert loaded is not None
    assert loaded.outcome is MatchOutcome.ACCEPT
    assert loaded.matched_terms == ("python",)
    assert loaded.reasons == ("required term matched: python",)
    assert loaded.rules_snapshot == {"required_terms": ("python",)}
    assert loaded.score == 0.9
    assert loaded.profile_version == 1


def test_decision_cascade_deletes_with_publication(storage: SqliteStorage) -> None:
    """Удаление публикации каскадом убирает её decision."""
    publication = make_publication()
    storage.save_publication(publication)
    storage.save_decision(make_decision(outcome=MatchOutcome.ACCEPT))

    with storage._conn:
        storage._conn.execute("DELETE FROM publications WHERE item_key = ?", (publication.item_key,))

    assert storage.count_decisions() == 0


def test_delivery_attempt_idempotent(storage: SqliteStorage) -> None:
    """Доставка сохраняется один раз, повторная попытка игнорируется."""
    publication = make_publication()
    storage.save_publication(publication)
    attempt = DeliveryAttempt(
        delivery_key=f"{publication.item_key}:profile-1",
        status=DeliveryStatus.SENT,
        provider_message_id="tg-msg-1",
        attempted_at=NOW,
    )

    assert (
        storage.save_delivery_attempt(
            attempt,
            publication_key=publication.item_key,
            profile_id="profile-1",
            profile_version=1,
        )
        is True
    )
    assert (
        storage.save_delivery_attempt(
            attempt,
            publication_key=publication.item_key,
            profile_id="profile-1",
            profile_version=1,
        )
        is False
    )


@pytest.mark.asyncio
async def test_sqlite_checkpoint_store_async_contract(storage: SqliteStorage) -> None:
    """Async Store соответствует порту CheckpointStore из P3."""
    store = SqliteCheckpointStore(storage)

    assert await store.get("async-source") is None
    await store.commit("async-source", "item-9")
    assert await store.get("async-source") == "item-9"


def test_persistence_across_connections(
    tmp_path: Path,
) -> None:
    """Сохранённые данные видны новому соединению той же БД."""
    db_path = tmp_path / "persist.db"
    first = SqliteStorage(db_path)
    first.save_publication(make_publication())
    first.set_checkpoint("source-1", "item-1")
    first.close()

    second = SqliteStorage(db_path)
    assert second.get_publication("fixture-source:item-1") is not None
    assert second.get_checkpoint("source-1") == "item-1"
    second.close()