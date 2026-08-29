"""telegram.py — Delivery Engine: мгновенная отправка лидов в Telegram.

Переиспользует паттерн notification.py платформы, но напрямую через Bot API
(httpx), без зависимости от цикла платформы (additive, W-10).
"""
from __future__ import annotations

import logging

import httpx

from app.models import Lead

logger = logging.getLogger(__name__)


class TelegramDelivery:
    """Отправка лида в Telegram-чат/бот.

    Args:
        bot_token: токен бота (пусто → логируем, не отправляем).
        chat_id: чат для отправки.
        api_base: базовый URL Bot API.
    """

    def __init__(
        self,
        bot_token: str = "",
        chat_id: str = "",
        api_base: str = "https://api.telegram.org",
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = api_base
        self._client = httpx.AsyncClient(timeout=15)

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def _format(self, lead: Lead) -> str:
        """Экранирование HTML (промт 69 п.5: экранируй HTML для TG-бота)."""
        import html as html_mod

        text = html_mod.escape(lead.text[:1000***REMOVED***)
        lines = [
            "🧲 <b>Найден потенциальный клиент</b>",
            f"Источник: {lead.source***REMOVED***",
            f"Интент: {lead.intent***REMOVED*** · Score: <b>{lead.score:.0f***REMOVED***</b>/100",
            f"<blockquote>{text***REMOVED***</blockquote>",
        ***REMOVED***
        if lead.url:
            lines.append(f"🔗 {html_mod.escape(lead.url)***REMOVED***")
        return "\n".join(lines)

    async def send(self, lead: Lead) -> bool:
        if not self.enabled:
            logger.info("delivery disabled; lead score=%.0f from %s", lead.score, lead.source)
            return False
        try:
            resp = await self._client.post(
                f"{self.api_base***REMOVED***/bot{self.bot_token***REMOVED***/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": self._format(lead),
                    "parse_mode": "HTML",
                ***REMOVED***,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("delivery failed: %s", exc)
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
