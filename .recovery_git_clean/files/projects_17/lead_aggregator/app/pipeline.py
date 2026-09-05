"""pipeline.py — асинхронный конвейер сбора и фильтрации лидов.

Поток: adapters → classify(L1/L2) → dedup → score(L3) → delivery → checkpoint.
Изоляция: падение одного адаптера не роняет конвейер (AdapterError перехват).
Resume: CheckpointStore хранит last_id по источнику (промт 69 п.3).
"""
from __future__ import annotations

import asyncio
import logging
***REMOVED***
from collections.abc import Iterable

from app.adapters.base import BaseAdapter
from app.adapters.kwork_adapter import KworkAdapter
from app.adapters.tg_channel_adapter import TGChannelAdapter
from app.core.config import Config
from app.core.retry_policy import RetryPolicy
from app.core.tls_client import TLSClient
from app.delivery.telegram import TelegramDelivery
from app.models import Lead
from app.processors.deduplicator import Deduplicator
from app.processors.intent_classifier import IntentClassifier
from app.processors.scorer import Scorer
from app.storage.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


_ID_NUM_RE = re.compile(r"(\d+)$")


def _id_key(source_id: str) -> tuple[int, int | str***REMOVED***:
    """Ключ для упорядоченного сравнения id источников.

    Числовой хвост (post_id, order_id) сравнивается как int — иначе
    строковое сравнение ломается на границе разрядности (99999 → 100000).
    """
    match = _ID_NUM_RE.search(source_id)
    if match:
        return (0, int(match.group(1)))
    return (1, source_id)


def _id_is_newer(source_id: str, last_id: str) -> bool:
    return _id_key(source_id) > _id_key(last_id)


class LeadPipeline:
    """Оркестратор конвейера Attract-модуля."""

    def __init__(
        self,
        config: Config,
        adapters: Iterable[BaseAdapter***REMOVED***,
        classifier: IntentClassifier | None = None,
        deduplicator: Deduplicator | None = None,
        scorer: Scorer | None = None,
        checkpoint: CheckpointStore | None = None,
        delivery: TelegramDelivery | None = None,
        retry: RetryPolicy | None = None,
    ) -> None:
        self.config = config
        self.adapters = list(adapters)
        self.classifier = classifier or IntentClassifier(
            stopwords=config.stopwords,
            client_markers=config.client_markers,
            seeker_markers=config.seeker_markers,
        )
        self.deduplicator = deduplicator or Deduplicator()
        self.scorer = scorer or Scorer(signals=config.competence_signals)
        self.checkpoint = checkpoint or CheckpointStore(config.checkpoint_db)
        self.delivery = delivery or TelegramDelivery(config.tg_bot_token, config.tg_chat_id)
        self._retry_template = retry or RetryPolicy()
        # per-adapter retry: изоляция (промт 69 п.2) — сбой одного источника
        # не должен размыкать circuit breaker для остальных.
        self._retries: dict[str, RetryPolicy***REMOVED*** = {***REMOVED***
        self._stats = {"fetched": 0, "new": 0, "delivered": 0, "errors": 0***REMOVED***

    def _retry_for(self, adapter: BaseAdapter) -> RetryPolicy:
        if adapter.name not in self._retries:
            self._retries[adapter.name***REMOVED*** = self._retry_template.clone()
        return self._retries[adapter.name***REMOVED***

    @property
    def stats(self) -> dict[str, int***REMOVED***:
        return dict(self._stats)

    # ── обработка одного лида ───────────────────────────────────────
    def _process_lead(self, lead: Lead) -> Lead | None:
        """L1→L2→dedup→score. Возвращает None, если лид отсеян."""
        legal_ok, intent = self.classifier.classify(lead.text)
        if not legal_ok:
            lead.intent = "spam"
            lead.legal_ok = False
            return None
        if self.deduplicator.is_duplicate(lead):
            return None
        lead.intent = intent
        lead.score = self.scorer.score(lead)
        if lead.score < self.config.lead_score_threshold:
            return None
        return lead

    # ── обработка одного источника ──────────────────────────────────
    async def _process_source(self, adapter: BaseAdapter) -> None:
        # per-adapter RetryPolicy: backoff+jitter+circuit breaker (промт 69 п.4)
        try:
            leads = await self._retry_for(adapter).run(adapter.fetch)
        except Exception as exc:  # noqa: BLE001 — изоляция адаптера (промт 69 п.2)
            self._stats["errors"***REMOVED*** += 1
            logger.warning("adapter %s error: %s", adapter.name, exc)
            return

        self._stats["fetched"***REMOVED*** += len(leads)
        last_id = self.checkpoint.get_last(adapter.name) if adapter.ordered else None
        new_ids: list[str***REMOVED*** = [***REMOVED***
        for lead in leads:
            # resume: только для упорядоченных фидов (промт 69 п.3);
            # неупорядоченные (Kwork) — через Deduplicator, без скипа по id
            if last_id is not None and not _id_is_newer(lead.source_id, last_id):
                continue
            processed = self._process_lead(lead)
            if processed is None:
                continue
            self._stats["new"***REMOVED*** += 1
            new_ids.append(processed.source_id)
            if await self.delivery.send(processed):
                self._stats["delivered"***REMOVED*** += 1

        if new_ids and adapter.ordered:
            # чекпоинт = самый новый виденный id (фид от новых к старым)
            self.checkpoint.set_last(adapter.name, new_ids[0***REMOVED***)

    # ── циклы ───────────────────────────────────────────────────────
    async def run_once(self) -> dict[str, int***REMOVED***:
        """Один проход по всем источникам."""
        for adapter in self.adapters:
            await self._process_source(adapter)
        return self.stats

    async def run_forever(self, interval: float | None = None) -> None:
        """Непрерывный сбор 24/7 (CORE DIRECTIVE промта 69).

        Гарантирует закрытие checkpoint и delivery при прерывании (try/finally).
        """
        interval = interval if interval is not None else self.config.poll_interval_s
        logger.info("pipeline started; %d sources, interval %.0fs", len(self.adapters), interval)
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(interval)
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        self.checkpoint.close()
        await self.delivery.aclose()


def build_default_adapters(config: Config, client: TLSClient) -> list[BaseAdapter***REMOVED***:
    """Фабрика адаптеров из конфига (kwork_enabled + tg_channels).

    Первый источник по roadmap — Kwork (рекомендация PHASE2 §8);
    затем TG-каналы из LA_TG_CHANNELS.
    """
    adapters: list[BaseAdapter***REMOVED*** = [***REMOVED***
    if config.kwork_enabled:
        adapters.append(KworkAdapter(client, feed_url=config.kwork_feed_url))
    for channel in config.tg_channels:
        adapters.append(TGChannelAdapter(client, channel))
    return adapters
