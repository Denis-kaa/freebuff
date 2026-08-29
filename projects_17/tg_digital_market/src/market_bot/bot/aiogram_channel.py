"""bot/aiogram_channel.py — адаптер NotificationChannel для aiogram.

Используется только в продакшен-сборке (bot/main.py). В тестах подменяется
на `FakeChannel`, поэтому этот модуль НЕ импортируется в core-тестах.
"""

from __future__ import annotations

import logging
from typing import Iterable

from aiogram import Bot

from ..services.notifications import NotificationChannel

logger = logging.getLogger(__name__)


class AiogramNotificationChannel:
    """Адаптер: NotificationChannel поверх aiogram.Bot."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, user_id: int, text: str) -> None:
        try:
            await self._bot.send_message(chat_id=user_id, text=text)
        except Exception as exc:
            logger.warning("Не удалось отправить сообщение user=%s: %r", user_id, exc)

    async def broadcast(self, user_ids: Iterable[int***REMOVED***, text: str) -> None:
        for uid in list(user_ids):
            try:
                await self._bot.send_message(chat_id=uid, text=text)
            except Exception as exc:
                logger.warning("Не удалось broadcast user=%s: %r", uid, exc)
