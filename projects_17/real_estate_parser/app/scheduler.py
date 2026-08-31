"""scheduler.py — APScheduler : déclencheur quotidien + lancement manuel.

Le bot Telegram (app/bot/bot.py) partage la même instance de scheduler
pour que /run déclenche le même pipeline que le déclencheur cron.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Config

logger = logging.getLogger(__name__)


class RunScheduler:
    """Planificateur : déclencheur cron quotidien + lancement manuel."""

    def __init__(self, config: Config, run_coro_factory) -> None:
        """run_coro_factory: fonction async sans argument qui exécute un run complet."""
        self.config = config
        self.run_coro_factory = run_coro_factory
        self._scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        trigger = CronTrigger(
            hour=self.config.run_hour,
            minute=self.config.run_minute,
        )
        self._scheduler.add_job(
            self._daily_run,
            trigger,
            id="daily_parse",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "real_estate_parser: scheduler started (daily at %02d:%02d)",
            self.config.run_hour,
            self.config.run_minute,
        )

    async def _daily_run(self) -> None:
        if self._running:
            logger.warning("real_estate_parser: run déjà en cours, déclencheur ignoré")
            return
        await self.run_once()

    async def run_once(self) -> dict:
        """Lancement manuel ou planifié d'un run complet."""
        if self._running:
            raise RuntimeError("un run est déjà en cours")
        self._running = True
        started = datetime.now()
        try:
            totals = await self.run_coro_factory()
            totals["started_at"] = started.isoformat()
            totals["finished_at"] = datetime.now().isoformat()
            return totals
        finally:
            self._running = False

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
