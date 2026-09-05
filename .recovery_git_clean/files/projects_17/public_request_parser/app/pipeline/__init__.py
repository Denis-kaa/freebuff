"""Offline single-tenant pipeline (P8).

Срезает весь конвейер на fixtures без сети:

    adapter (SourceItem) → normalize → SQLite → matcher → dry-run delivery

- checkpoint commit после каждого обработанного item (идемпотентный повтор);
- публикации сохраняются с TTL хранилища; decisions и delivery attempts
  дедуплицируются storage'ом;
- ошибка АНТИЦИПА: AdapterError всплывает, checkpoint не коммитится;
- owner_scope жёстко ограничивает доставку (owner-гейт P7).

Модуль не выполняет сетевых вызовов, не содержит credentials и не
импортирует платформенный код.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.domain import (
    DeliveryAttempt,
    DeliveryStatus,
    MatchDecision,
    MatchOutcome,
    Publication,
    SearchProfile,
    SourceItem,
)
from app.matcher import RuleMatcher
from app.rss_atom import normalize_source_item
from app.storage import SqliteStorage


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Сводка одного офлайн-прогона pipeline."""

    source_id: str
    fetched: int
    new_publications: int
    stored_decisions: int
    accepted: int
    pending: int
    rejected: int
    delivered: int
    checkpoint: str | None


class FeedAdapter(Protocol):
    """Асинхронный источник элементов (SourceAdapter порт P3).

    Реализации — async-генераторы: вызов `fetch()` возвращает
    `AsyncIterator[SourceItem***REMOVED***` без дополнительного `await`.
    """

    source_id: str

    def fetch(
        self, *, limit: int = 50, checkpoint: str | None = None
    ) -> AsyncIterator[SourceItem***REMOVED***:
        """Итератор SourceItem (асинхронный)."""
        ...


class Checkpoint(Protocol):
    async def get(self, source_id: str) -> str | None: ...

    async def commit(self, source_id: str, item_id: str) -> None: ...


class DeliveryPort(Protocol):
    async def deliver(
        self,
        publication: Publication,
        decision: MatchDecision,
        *,
        owner_scope: str,
    ) -> DeliveryAttempt: ...


def _savable(pub: Publication, storage: SqliteStorage) -> bool:
    """Сохранить публикацию с дефолтными retention-параметрами."""
    return storage.save_publication(
        pub,
        text_ttl=timedelta(days=7),
        max_text_chars=20_000,
        allow_full_text=True,
    )


async def run_offline_slice(
    *,
    adapter: FeedAdapter,
    profile: SearchProfile,
    storage: SqliteStorage,
    checkpoint: Checkpoint,
    delivery: DeliveryPort,
    owner_scope: str,
    limit: int = 50,
    fetched_at: datetime | None = None,
) -> PipelineResult:
    """Прогнать один срез: fetch → normalize → store → match → deliver.

    Публикации, уже существующие в storage, не создаются (INSERT OR IGNORE),
    но всё равно прогоняются через matcher (для консистентности decisions)
    и checkpoint коммитится после обработки.
    """
    when = fetched_at or datetime.now(timezone.utc)
    last_checkpoint = await checkpoint.get(adapter.source_id)
    items = [item async for item in adapter.fetch(limit=limit, checkpoint=last_checkpoint)***REMOVED***

    matcher = RuleMatcher(profile)
    new_publications = 0
    stored_decisions = 0
    accepted = pending = rejected = delivered = 0
    last_item_id: str | None = last_checkpoint

    for item in items:
        publication = normalize_source_item(
            adapter.source_id, item, fetched_at=when
        )
        if storage.get_publication(publication.item_key) is None:
            _savable_publication = _savable(publication, storage)
            if _savable_publication:
                new_publications += 1

        decision = matcher.match(publication, decided_at=when)
        if storage.save_decision(decision):
            stored_decisions += 1

        if decision.outcome is MatchOutcome.ACCEPT:
            accepted += 1
        elif decision.outcome is MatchOutcome.PENDING:
            pending += 1
        else:
            rejected += 1

        if decision.outcome in (MatchOutcome.ACCEPT, MatchOutcome.PENDING):
            attempt = await delivery.deliver(
                publication,
                decision,
                owner_scope=owner_scope,
            )
            if attempt.status in (DeliveryStatus.SENT, DeliveryStatus.SKIPPED):
                delivered += 1

        last_item_id = item.item_id
        await checkpoint.commit(adapter.source_id, item.item_id)

    return PipelineResult(
        source_id=adapter.source_id,
        fetched=len(items),
        new_publications=new_publications,
        stored_decisions=stored_decisions,
        accepted=accepted,
        pending=pending,
        rejected=rejected,
        delivered=delivered,
        checkpoint=last_item_id,
    )


def format_report(result: PipelineResult) -> str:
    """Компактный JSON-подобный отчёт CLI."""
    return (
        f"source={result.source_id***REMOVED*** fetched={result.fetched***REMOVED*** "
        f"new={result.new_publications***REMOVED*** decisions={result.stored_decisions***REMOVED*** "
        f"accepted={result.accepted***REMOVED*** pending={result.pending***REMOVED*** "
        f"rejected={result.rejected***REMOVED*** delivered={result.delivered***REMOVED*** "
        f"checkpoint={result.checkpoint!r***REMOVED***"
    )


__all__ = [
    "Checkpoint",
    "DeliveryPort",
    "FeedAdapter",
    "PipelineResult",
    "format_report",
    "run_offline_slice",
***REMOVED***