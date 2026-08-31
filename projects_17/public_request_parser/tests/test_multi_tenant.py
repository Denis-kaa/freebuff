"""Hermetic tests P13 multi-tenant isolation + P14 feedback (schema v2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.domain import SearchProfile
from app.storage import SqliteStorage

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def make_profile(*, owner: str = "operator", profile_id: str = "profile-1", version: int = 1) -> SearchProfile:
    return SearchProfile(
        profile_id=profile_id,
        owner_scope=owner,
        version=version,
        service_name="Python",
        required_terms=("python",),
        optional_terms=("backend",),
    )


@pytest.fixture()
def storage(tmp_path: Path) -> Iterator[SqliteStorage]:
    db = SqliteStorage(tmp_path / "mt.db")
    yield db
    db.close()


def test_schema_v2_initialized(storage: SqliteStorage) -> None:
    """Схема поднята до v2, таблицы profiles/feedback существуют."""
    assert storage.schema_version() == 2
    tables = {
        str(row[0])
        for row in storage._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"profiles", "feedback"} <= tables


def test_profile_roundtrip_and_version_upsert(storage: SqliteStorage) -> None:
    """Профиль сохраняется, обновляется и читается с полными правилами."""
    assert storage.save_profile(make_profile(version=1)) is True
    loaded = storage.get_profile("operator", "profile-1")
    assert loaded is not None
    assert loaded.required_terms == ("python",)
    assert loaded.owner_scope == "operator"

    # Update version 2 перезаписывает ту же строку.
    assert storage.save_profile(make_profile(version=2)) is True
    loaded = storage.get_profile("operator", "profile-1")
    assert loaded is not None
    assert loaded.version == 2
    assert len(storage.list_profiles("operator")) == 1


def test_profile_isolation_between_owners(storage: SqliteStorage) -> None:
    """Чужой owner не видит и не удаляет профиль."""
    storage.save_profile(make_profile(owner="operator"))
    storage.save_profile(make_profile(owner="alice", profile_id="profile-2"))

    assert storage.get_profile("alice", "profile-1") is None
    assert [p.profile_id for p in storage.list_profiles("alice")] == ["profile-2"]
    assert storage.delete_profile("alice", "profile-1") is False
    assert storage.get_profile("operator", "profile-1") is not None


def test_feedback_record_and_stats(storage: SqliteStorage) -> None:
    """Feedback пишется идемпотентно и агрегируется по владельцу."""
    assert (
        storage.record_feedback(
            owner_scope="operator",
            delivery_key="operator:pub-1:p1",
            publication_key="s:1",
            action="relevant",
            created_at=NOW,
        )
        is True
    )
    # Повторный клик по тому же ключу игнорируется.
    assert (
        storage.record_feedback(
            owner_scope="operator",
            delivery_key="operator:pub-1:p1",
            publication_key="s:1",
            action="irrelevant",
            created_at=NOW,
        )
        is False
    )
    storage.record_feedback(
        owner_scope="anonymous",
        delivery_key="anonymous:pub-2:p1",
        publication_key="s:2",
        action="irrelevant",
        created_at=NOW,
    )

    assert storage.feedback_stats("operator") == {"relevant": 1}
    assert storage.feedback_stats("anonymous") == {"irrelevant": 1}


def test_feedback_rejects_unknown_action(storage: SqliteStorage) -> None:
    """Неизвестный action отбрасывается на уровне хранилища."""
    with pytest.raises(ValueError, match="relevant or irrelevant"):
        storage.record_feedback(
            owner_scope="operator",
            delivery_key="k",
            publication_key="s:1",
            action="maybe",
        )


def test_v1_database_migrates_to_v2_preserving_data(tmp_path: Path) -> None:
    """Открытие существующей v1-БД добавляет таблицы v2 без потери данных."""
    import sqlite3

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE publications (
            item_key TEXT PRIMARY KEY, source_id TEXT NOT NULL, item_id TEXT NOT NULL,
            canonical_url TEXT NOT NULL UNIQUE, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
            content TEXT, published_at TEXT, fetched_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'new',
            text_expires_at TEXT, created_at TEXT NOT NULL
        );
        INSERT INTO publications (item_key, source_id, item_id, canonical_url, title, fetched_at, created_at)
        VALUES ('s:1', 's', '1', 'https://x.test/1', 't', '2026-08-23T12:00:00+00:00', '2026-08-23T12:00:00+00:00');
        PRAGMA user_version = 1;
        """
    )
    conn.commit()
    conn.close()

    upgraded = SqliteStorage(db_path)

    assert upgraded.schema_version() == 2
    assert upgraded.get_publication("s:1") is not None
    assert upgraded.save_profile(make_profile()) is True
    upgraded.close()