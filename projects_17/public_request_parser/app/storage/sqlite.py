"""SQLite/WAL storage layer для Public Request Parser.

P6 реализует:

- WAL-режим, foreign keys, busy_timeout и миграции через `PRAGMA user_version`;
- таблицы `publications` (с dedup-индексами и `text_expires_at`), `checkpoints`,
  `decisions` и `delivery_attempts`;
- атомарные writes: идемпотентные INSERT (OR IGNORE) по item_key/URL,
  checkpoint upsert, decision upsert;
- TTL cleanup полного текста: `content` обнуляется после истечения,
  metadata/decision не удаляются; повторный cleanup идемпотентен;
- `SqliteCheckpointStore` — async-реализация port `CheckpointStore` из P3.

Модуль не импортирует платформенный код и не выполняет сетевых вызовов.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
***REMOVED***
from typing import Any

from app.domain import (
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    MatchOutcome,
    Publication,
    PublicationStatus,
    SearchProfile,
)

_SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS publications (
    item_key          TEXT PRIMARY KEY,
    source_id         TEXT NOT NULL,
    item_id           TEXT NOT NULL,
    canonical_url     TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    summary           TEXT NOT NULL DEFAULT '',
    content           TEXT,
    published_at      TEXT,
    fetched_at        TEXT NOT NULL,
    metadata_json     TEXT NOT NULL DEFAULT '{***REMOVED***',
    status            TEXT NOT NULL DEFAULT 'new',
    text_expires_at   TEXT,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_publications_source_fetched
    ON publications (source_id, fetched_at);

CREATE TABLE IF NOT EXISTS checkpoints (
    source_id     TEXT PRIMARY KEY,
    last_item_id  TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_key     TEXT NOT NULL REFERENCES publications(item_key) ON DELETE CASCADE,
    profile_id          TEXT NOT NULL,
    profile_version     INTEGER NOT NULL,
    outcome             TEXT NOT NULL,
    score               REAL NOT NULL,
    matched_terms_json  TEXT NOT NULL DEFAULT '[***REMOVED***',
    matched_synonyms_json TEXT NOT NULL DEFAULT '[***REMOVED***',
    rejected_terms_json TEXT NOT NULL DEFAULT '[***REMOVED***',
    reasons_json        TEXT NOT NULL DEFAULT '[***REMOVED***',
    rules_snapshot_json TEXT NOT NULL DEFAULT '{***REMOVED***',
    decided_at          TEXT NOT NULL,
    UNIQUE (publication_key, profile_id, profile_version)
);
CREATE INDEX IF NOT EXISTS idx_decisions_profile
    ON decisions (profile_id, profile_version, outcome);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    delivery_key        TEXT PRIMARY KEY,
    publication_key     TEXT NOT NULL REFERENCES publications(item_key) ON DELETE CASCADE,
    profile_id          TEXT NOT NULL,
    profile_version     INTEGER NOT NULL,
    status              TEXT NOT NULL,
    provider_message_id TEXT,
    error_code          TEXT,
    attempted_at        TEXT NOT NULL
);

-- v2: персональные профили (owner-scoped) и feedback (для P13/P14).
CREATE TABLE IF NOT EXISTS profiles (
    owner_scope   TEXT NOT NULL,
    profile_id    TEXT NOT NULL,
    version       INTEGER NOT NULL,
    service_name  TEXT NOT NULL,
    body_json     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (owner_scope, profile_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    delivery_key    TEXT PRIMARY KEY,
    owner_scope     TEXT NOT NULL,
    publication_key TEXT NOT NULL,
    action          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_owner
    ON feedback (owner_scope, action);
"""


def _to_iso(value: datetime | None) -> str | None:
    """Сериализовать timezone-aware datetime в ISO UTC."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _from_iso(value: str | None) -> datetime | None:
    """Разобрать ISO datetime, приведя к UTC."""
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _json_bytes(value: object) -> str:
    """Сериализовать значение таблицы JSON."""
    return json.dumps(value, ensure_ascii=False)


def _decision_to_row(
    decision: MatchDecision,
) -> dict[str, Any***REMOVED***:
    """Разложить decision в строку с JSON-колонками."""
    return {
        "publication_key": decision.publication_key,
        "profile_id": decision.profile_id,
        "profile_version": decision.profile_version,
        "outcome": decision.outcome.value,
        "score": decision.score,
        "matched_terms_json": _json_bytes(list(decision.matched_terms)),
        "matched_synonyms_json": _json_bytes(list(decision.matched_synonyms)),
        "rejected_terms_json": _json_bytes(list(decision.rejected_terms)),
        "reasons_json": _json_bytes(list(decision.reasons)),
        "rules_snapshot_json": _json_bytes(
            {key: list(value) for key, value in decision.rules_snapshot.items()***REMOVED***
        ),
        "decided_at": _to_iso(decision.decided_at),
    ***REMOVED***


def _row_to_decision(row: sqlite3.Row) -> MatchDecision:
    """Собрать MatchDecision из строки decisions."""
    data = dict(row)
    return MatchDecision(
        publication_key=data["publication_key"***REMOVED***,
        profile_id=data["profile_id"***REMOVED***,
        profile_version=data["profile_version"***REMOVED***,
        outcome=MatchOutcome(data["outcome"***REMOVED***),
        score=data["score"***REMOVED***,
        matched_terms=tuple(json.loads(data["matched_terms_json"***REMOVED***)),
        matched_synonyms=tuple(json.loads(data["matched_synonyms_json"***REMOVED***)),
        rejected_terms=tuple(json.loads(data["rejected_terms_json"***REMOVED***)),
        reasons=tuple(json.loads(data["reasons_json"***REMOVED***)),
        rules_snapshot={
            key: tuple(values)
            for key, values in json.loads(data["rules_snapshot_json"***REMOVED***).items()
        ***REMOVED***,
        decided_at=datetime.fromisoformat(data["decided_at"***REMOVED***).astimezone(timezone.utc),
    )


def _row_to_profile(row: sqlite3.Row) -> SearchProfile | None:
    """Собрать SearchProfile из строки profiles (JSON body)."""
    data = dict(row)
    try:
        body = json.loads(data["body_json"***REMOVED***)
    except (TypeError, ValueError):
        return None
    synonyms = tuple(
        (canonical, tuple(values))
        for canonical, values in body.get("synonyms", [***REMOVED***)
    )
    return SearchProfile(
        profile_id=data["profile_id"***REMOVED***,
        owner_scope=data["owner_scope"***REMOVED***,
        version=int(data["version"***REMOVED***),
        service_name=data["service_name"***REMOVED***,
        required_terms=tuple(body.get("required_terms", ())),
        optional_terms=tuple(body.get("optional_terms", ())),
        synonyms=synonyms,
        excluded_terms=tuple(body.get("excluded_terms", ())),
        intent_terms=tuple(body.get("intent_terms", ())),
        accept_threshold=float(body.get("accept_threshold", 0.8)),
        pending_threshold=float(body.get("pending_threshold", 0.5)),
        source_ids=tuple(body.get("source_ids", ())),
        rules_snapshot={
            key: tuple(values) for key, values in body.get("rules_snapshot", {***REMOVED***).items()
        ***REMOVED***,
    )


def _row_to_publication(row: sqlite3.Row) -> Publication:
    """Собрать Publication из строки (metadata остаётся даже после TTL)."""
    data = dict(row)
    return Publication(
        source_id=data["source_id"***REMOVED***,
        item_id=data["item_id"***REMOVED***,
        canonical_url=data["canonical_url"***REMOVED***,
        title=data["title"***REMOVED***,
        published_at=_from_iso(data["published_at"***REMOVED***),
        summary=data["summary"***REMOVED***,
        content=data["content"***REMOVED***,
        fetched_at=datetime.fromisoformat(data["fetched_at"***REMOVED***).astimezone(timezone.utc),
        metadata=json.loads(data["metadata_json"***REMOVED***),
        status=PublicationStatus(data["status"***REMOVED***),
    )


class SqliteStorage:
    """SQLite/WAL-хранилище публикаций, решений, чекпоинтов и доставок."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        """Поднять схему до `_SCHEMA_VERSION` (идемпотентно)."""
        version = self.schema_version()
        if version >= _SCHEMA_VERSION:
            return
        with self._conn:
            self._conn.executescript(_SCHEMA)
            # user_version не принимает параметры; число — константа схемы.
            self._conn.execute(f"PRAGMA user_version = {int(_SCHEMA_VERSION)***REMOVED***")

    def schema_version(self) -> int:
        """Текущая версия схемы (PRAGMA user_version)."""
        row = self._conn.execute("PRAGMA user_version").fetchone()
        return int(row[0***REMOVED***) if row else 0

    # ------------------------------------------------------------------
    # Publications
    # ------------------------------------------------------------------
    def save_publication(
        self,
        publication: Publication,
        *,
        text_ttl: timedelta | None = None,
        max_text_chars: int | None = None,
        allow_full_text: bool = True,
    ) -> bool:
        """Идемпотентно сохранить публикацию; True если строка создана.

        `text_ttl` задаёт срок полного текста с `fetched_at`; по истечении
        TTL cleanup обнулит `content`. `max_text_chars` дополнительно
        каппирует текст перед записью; `allow_full_text=False` запрещает
        хранение контента вообще (текст не сохраняется).
        """
        content = publication.content
        if not allow_full_text:
            content = None
        elif max_text_chars is not None:
            content = content[:max_text_chars***REMOVED*** if content else content

        text_expires_at = None
        if content is not None and text_ttl is not None:
            if text_ttl.total_seconds() < 0:
                raise ValueError("text_ttl must not be negative")
            text_expires_at = _to_iso(publication.fetched_at + text_ttl)

        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO publications (
                    item_key, source_id, item_id, canonical_url, title, summary,
                    content, published_at, fetched_at, metadata_json, status,
                    text_expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    publication.item_key,
                    publication.source_id,
                    publication.item_id,
                    publication.canonical_url,
                    publication.title,
                    publication.summary,
                    content,
                    _to_iso(publication.published_at),
                    _to_iso(publication.fetched_at),
                    _json_bytes(dict(publication.metadata)),
                    publication.status.value,
                    text_expires_at,
                    _to_iso(datetime.now(timezone.utc)),
                ),
            )
        return cursor.rowcount == 1

    def get_publication(self, item_key: str) -> Publication | None:
        """Прочитать публикацию по source-scoped ключу."""
        row = self._conn.execute(
            "SELECT * FROM publications WHERE item_key = ?", (item_key,)
        ).fetchone()
        return _row_to_publication(row) if row else None

    def list_publications(
        self, *, source_id: str | None = None, limit: int = 100
    ) -> list[Publication***REMOVED***:
        """Список публикаций (без полного текста из TTL-контента не выдаётся)."""
        if limit < 1:
            raise ValueError("limit must be >= 1")
        query = "SELECT * FROM publications"
        params: list[str***REMOVED*** = [***REMOVED***
        if source_id is not None:
            query += " WHERE source_id = ?"
            params.append(source_id)
        query += " ORDER BY fetched_at DESC LIMIT ?"
        params.append(str(limit))
        rows = self._conn.execute(query, tuple(params)).fetchall()
        return [_row_to_publication(row) for row in rows***REMOVED***

    def expire_full_text(self, now: datetime | None = None) -> int:
        """Обнулить истёкший полный текст; вернуть число изменённых строк.

        Строки и metadata/decision не удаляются — TTL трогает только
        временный контент. Идемпотентен: повторный вызов возвращает 0.
        """
        when = now or datetime.now(timezone.utc)
        with self._conn:
            cursor = self._conn.execute(
                """
                UPDATE publications
                   SET content = NULL, text_expires_at = NULL
                 WHERE text_expires_at IS NOT NULL
                   AND text_expires_at <= ?
                """,
                (_to_iso(when),),
            )
        return cursor.rowcount

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------
    def get_checkpoint(self, source_id: str) -> str | None:
        """Последний подтверждённый checkpoint источника."""
        row = self._conn.execute(
            "SELECT last_item_id FROM checkpoints WHERE source_id = ?", (source_id,)
        ).fetchone()
        return str(row["last_item_id"***REMOVED***) if row else None

    def set_checkpoint(self, source_id: str, item_id: str) -> None:
        """Атомарно подтвердить обработанный item (upsert)."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO checkpoints (source_id, last_item_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    last_item_id = excluded.last_item_id,
                    updated_at = excluded.updated_at
                """,
                (source_id, item_id, _to_iso(datetime.now(timezone.utc))),
            )

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------
    def save_decision(self, decision: MatchDecision) -> bool:
        """Идемпотентно сохранить decision; False если уже существовал."""
        row = _decision_to_row(decision)
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO decisions (
                    publication_key, profile_id, profile_version, outcome, score,
                    matched_terms_json, matched_synonyms_json, rejected_terms_json,
                    reasons_json, rules_snapshot_json, decided_at
                ) VALUES (
                    :publication_key, :profile_id, :profile_version, :outcome, :score,
                    :matched_terms_json, :matched_synonyms_json, :rejected_terms_json,
                    :reasons_json, :rules_snapshot_json, :decided_at
                )
                """,
                row,
            )
        return cursor.rowcount == 1

    def get_decision(
        self, publication_key: str, profile_id: str, profile_version: int
    ) -> MatchDecision | None:
        """Прочитать сохранённое decision по версии профиля."""
        row = self._conn.execute(
            """
            SELECT * FROM decisions
             WHERE publication_key = ? AND profile_id = ? AND profile_version = ?
            """,
            (publication_key, profile_id, profile_version),
        ).fetchone()
        return _row_to_decision(row) if row else None

    # ------------------------------------------------------------------
    # Delivery attempts
    # ------------------------------------------------------------------
    def save_delivery_attempt(
        self,
        attempt: DeliveryAttempt,
        *,
        publication_key: str,
        profile_id: str,
        profile_version: int,
        replace_failed: bool = True,
    ) -> bool:
        """Идемпотентно сохранить попытку доставки.

        True если строка создана (повторная успешная попытка по тому же ключу
        игнорируется). При `replace_failed=True` существующая `failed`-попытка
        заменяется (retry после сбоя на provider), но не `sent`/`skipped`.
        """
        with self._conn:
            if replace_failed:
                existing = self._conn.execute(
                    "SELECT status FROM delivery_attempts WHERE delivery_key = ?",
                    (attempt.delivery_key,),
                ).fetchone()
                if existing is not None and existing["status"***REMOVED*** == DeliveryStatus.FAILED.value:
                    self._conn.execute(
                        """
                        UPDATE delivery_attempts
                           SET status = ?, provider_message_id = ?, error_code = ?,
                               attempted_at = ?
                         WHERE delivery_key = ?
                        """,
                        (
                            attempt.status.value,
                            attempt.provider_message_id,
                            attempt.error_code,
                            _to_iso(attempt.attempted_at),
                            attempt.delivery_key,
                        ),
                    )
                    return True
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO delivery_attempts (
                    delivery_key, publication_key, profile_id, profile_version,
                    status, provider_message_id, error_code, attempted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.delivery_key,
                    publication_key,
                    profile_id,
                    profile_version,
                    attempt.status.value,
                    attempt.provider_message_id,
                    attempt.error_code,
                    _to_iso(attempt.attempted_at),
                ),
            )
        return cursor.rowcount == 1

    def get_delivery_attempt(self, delivery_key: str) -> DeliveryAttempt | None:
        """Прочитать последнюю попытку доставки."""
        row = self._conn.execute(
            "SELECT * FROM delivery_attempts WHERE delivery_key = ?",
            (delivery_key,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        return DeliveryAttempt(
            delivery_key=data["delivery_key"***REMOVED***,
            status=DeliveryStatus(data["status"***REMOVED***),
            attempted_at=datetime.fromisoformat(data["attempted_at"***REMOVED***).astimezone(timezone.utc),
            provider_message_id=data["provider_message_id"***REMOVED***,
            error_code=data["error_code"***REMOVED***,
        )

    def count_publications(self) -> int:
        """Число строк публикаций (для тестов/метрик)."""
        row = self._conn.execute("SELECT COUNT(*) AS c FROM publications").fetchone()
        return int(row["c"***REMOVED***)

    def count_decisions(self) -> int:
        """Число строк решений (для тестов/метрик)."""
        row = self._conn.execute("SELECT COUNT(*) AS c FROM decisions").fetchone()
        return int(row["c"***REMOVED***)

    def backup_to(self, dst_path: str | Path) -> str:
        """Сделать онлайн-бэкап базы через sqlite backup API."""
        dst_path = str(dst_path)
        dest = sqlite3.connect(dst_path)
        try:
            with dest:
                self._conn.backup(dest)
        finally:
            dest.close()
        return dst_path

    # ------------------------------------------------------------------
    # Profiles (owner-scoped, schema v2)
    # ------------------------------------------------------------------
    def save_profile(self, profile: SearchProfile) -> bool:
        """Сохранить или обновить версию профиля владельца."""
        body = {
            "service_name": profile.service_name,
            "required_terms": list(profile.required_terms),
            "optional_terms": list(profile.optional_terms),
            "synonyms": [[canonical, list(values)***REMOVED*** for canonical, values in profile.synonyms***REMOVED***,
            "excluded_terms": list(profile.excluded_terms),
            "intent_terms": list(profile.intent_terms),
            "accept_threshold": profile.accept_threshold,
            "pending_threshold": profile.pending_threshold,
            "source_ids": list(profile.source_ids),
            "rules_snapshot": {
                key: list(values) for key, values in profile.rules_snapshot.items()
            ***REMOVED***,
        ***REMOVED***
        now = _to_iso(datetime.now(timezone.utc))
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO profiles (owner_scope, profile_id, version, service_name,
                                      body_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_scope, profile_id) DO UPDATE SET
                    version = excluded.version,
                    service_name = excluded.service_name,
                    body_json = excluded.body_json,
                    updated_at = excluded.updated_at
                """,
                (profile.owner_scope, profile.profile_id, profile.version,
                 profile.service_name, _json_bytes(body), now, now),
            )
        return cursor.rowcount == 1

    def get_profile(self, owner_scope: str, profile_id: str) -> SearchProfile | None:
        """Прочитать профиль владельца (owner-isolated)."""
        row = self._conn.execute(
            "SELECT * FROM profiles WHERE owner_scope = ? AND profile_id = ?",
            (owner_scope, profile_id),
        ).fetchone()
        return _row_to_profile(row) if row else None

    def list_profiles(self, owner_scope: str) -> list[SearchProfile***REMOVED***:
        """Все профили конкретного владельца (изоляция по scope)."""
        rows = self._conn.execute(
            "SELECT * FROM profiles WHERE owner_scope = ? ORDER BY created_at",
            (owner_scope,),
        ).fetchall()
        profiles: list[SearchProfile***REMOVED*** = [***REMOVED***
        for row in rows:
            profile = _row_to_profile(row)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def delete_profile(self, owner_scope: str, profile_id: str) -> bool:
        """Удалить профиль; False если чужой/несуществующий."""
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM profiles WHERE owner_scope = ? AND profile_id = ?",
                (owner_scope, profile_id),
            )
        return cursor.rowcount == 1

    # ------------------------------------------------------------------
    # Feedback (P14)
    # ------------------------------------------------------------------
    def record_feedback(
        self,
        *,
        owner_scope: str,
        delivery_key: str,
        publication_key: str,
        action: str,
        created_at: datetime | None = None,
    ) -> bool:
        """Записать feedback (relevant/irrelevant) идемпотентно по ключу."""
        if action not in {"relevant", "irrelevant"***REMOVED***:
            raise ValueError("action must be relevant or irrelevant")
        when = created_at or datetime.now(timezone.utc)
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO feedback
                    (delivery_key, owner_scope, publication_key, action, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (delivery_key, owner_scope, publication_key, action, _to_iso(when)),
            )
        return cursor.rowcount == 1

    def feedback_stats(self, owner_scope: str) -> dict[str, int***REMOVED***:
        """Счётчики feedback владельца (для quality reports)."""
        rows = self._conn.execute(
            "SELECT action, COUNT(*) AS c FROM feedback WHERE owner_scope = ? GROUP BY action",
            (owner_scope,),
        ).fetchall()
        return {str(row["action"***REMOVED***): int(row["c"***REMOVED***) for row in rows***REMOVED***

    def list_feedback(self, owner_scope: str, *, limit: int = 100) -> list[dict[str, object***REMOVED******REMOVED***:
        """Итерация по feedback владельца для калибровки (P14)."""
        if limit < 1:
            raise ValueError("limit must be >= 1")
        rows = self._conn.execute(
            """
            SELECT delivery_key, publication_key, action, created_at
              FROM feedback
             WHERE owner_scope = ?
             ORDER BY created_at DESC
             LIMIT ?
            """,
            (owner_scope, limit),
        ).fetchall()
        return [dict(row) for row in rows***REMOVED***

    def close(self) -> None:
        """Закрыть соединение."""
        self._conn.close()

    def __enter__(self) -> SqliteStorage:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class SqliteCheckpointStore:
    """Async-реализация порта `CheckpointStore` поверх `SqliteStorage`."""

    def __init__(self, storage: SqliteStorage) -> None:
        self._storage = storage

    async def get(self, source_id: str) -> str | None:
        """Получить последний подтверждённый checkpoint (в потоке SQLite)."""
        return await asyncio.to_thread(self._storage.get_checkpoint, source_id)

    async def commit(self, source_id: str, item_id: str) -> None:
        """Атомарно подтвердить обработанный item."""
        await asyncio.to_thread(self._storage.set_checkpoint, source_id, item_id)


__all__ = [
    "SqliteCheckpointStore",
    "SqliteStorage",
***REMOVED***