"""pipeline.py — run_once + run_forever orchestration.

Sources → fetch → parse → normalize → validate → dedup → DB upsert → run_log.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.core.config import Config
from app.core.rate_limit import HostRateLimiter
from app.core.retry_policy import RetryPolicy
from app.sources.base import Listing, SourceAdapter
from app.storage.repository import PropertyRepository

logger = logging.getLogger(__name__)


class PropertyPipeline:
    """Один прогон: fetch → parse → normalize → validate → dedup → DB upsert → run_log."""

    def __init__(
        self,
        config: Config,
        sources: list[SourceAdapter],
        repository: PropertyRepository,
        retry_policy: RetryPolicy | None = None,
        concurrency: int = 6,
    ) -> None:
        self.config = config
        self.sources = sources
        self.repository = repository
        self.retry = retry_policy or RetryPolicy()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.rate_limiter = HostRateLimiter(min_interval=config.request_delay)
        self._stop = asyncio.Event()

    def stop(self) -> None:
        """Мягкая остановка (ставит флаг, пайплайн проверяет между задачами)."""
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    async def run_once(self) -> dict[str, int]:
        """Один прогон: fetch → parse → normalize → validate → dedup → DB upsert → run_log."""
        started = time.monotonic()
        totals = {"fetched": 0, "created": 0, "updated": 0, "removed": 0, "errors": 0}
        for source in self.sources:
            if self.stopped:
                break
            stats = await self._run_source(source)
            for k, v in stats.items():
                totals[k] = totals.get(k, 0) + v
        status = "stopped" if self.stopped else "ok"
        await self._log_run(totals, started, status)
        return {**totals, "status": 1 if status == "ok" else 0}

    async def _run_source(self, source: SourceAdapter) -> dict[str, int]:
        """Прогон одного источника с bounded concurrency."""
        stats = {"fetched": 0, "created": 0, "updated": 0, "removed": 0, "errors": 0}
        try:
            listings = await self.retry.run(source.fetch, limit=self.config.batch_size)
        except Exception as exc:  # noqa: BLE001
            logger.exception("real_estate_parser: source %s failed: %s", source.name, exc)
            stats["errors"] += 1
            return stats

        stats["fetched"] = len(listings)
        sem = self.semaphore

        async def _handle(item: Listing) -> None:
            async with sem:
                if self.stopped:
                    return
                try:
                    outcome = await self.repository.upsert_listing(item)
                    stats[outcome] = stats.get(outcome, 0) + 1
                except Exception as exc:  # noqa: BLE001
                    logger.exception("real_estate_parser: upsert failed: %s", exc)
                    stats["errors"] += 1

        await asyncio.gather(*(_handle(item) for item in listings))
        return stats

    async def _log_run(self, totals: dict[str, int], started: float, status: str) -> None:
        finished = datetime.now(timezone.utc)
        duration = time.monotonic() - started
        logger.info(
            "real_estate_parser: run finished in %.1fs — %s",
            duration,
            {**totals, "status": status, "duration_s": round(duration, 1)},
        )

    async def run_forever(self, interval_s: float) -> None:
        """Бесконечный цикл с паузой между прогонами."""
        while not self.stopped:
            await self.run_once()
            try:
                await asyncio.sleep(interval_s)
            except asyncio.CancelledError:
                break
