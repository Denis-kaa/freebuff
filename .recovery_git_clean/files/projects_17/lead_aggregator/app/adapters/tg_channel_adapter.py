"""tg_channel_adapter.py — адаптер TG-каналов с заказами.

Вектор из PHASE1_RESEARCH.md §2.1 №1: `t.me/s/<channel>` — публичное web-превью
без авторизации, не вызывает FLOOD_WAIT. Каналы: @freelance_tg, @proger_orders и т.п.
"""
from __future__ import annotations

import logging
***REMOVED***
from html import unescape

from app.adapters.base import AdapterError, BaseAdapter
from app.core.tls_client import TLSClient
from app.models import Lead
from app.processors.intent_classifier import Normalizer

logger = logging.getLogger(__name__)

# блок сообщения: от data-post="..." до следующего блока/конца (толерантно к числу </div>)
# ВАЖНО (Фаза 4, live-verify 2026-08-10): класс на живом t.me/s может содержать
# дополнительные токены, напр. `tgme_widget_message text_not_supported_wrap
# service_message js-widget_message`. Паттерн `tgme_widget_message(?:\s[^"***REMOVED****)?`
# требует ПОСЛЕ базового имени пробел (доп. классы) или закрывающую кавычку —
# и НЕ матчит внутренние div'ы (`tgme_widget_message_user/_text/_wrap` и т.п.),
# иначе lookahead обрывает блок до текста и лиды теряются.
_MSG_BLOCK_RE = re.compile(
    r'<div class="tgme_widget_message(?:\s[^"***REMOVED****)?"[^>***REMOVED****data-post="([^"***REMOVED***+)"(.*?)'
    r'(?=<div class="tgme_widget_message(?:\s[^"***REMOVED****)?"|</body>|</html>|$)',
    re.DOTALL,
)
_TEXT_RE = re.compile(
    r'<div class="tgme_widget_message_text[^"***REMOVED****"[^>***REMOVED****>(.*?)</div>', re.DOTALL
)


class TGChannelAdapter(BaseAdapter):
    """Чтение публичных каналов заказов через t.me/s/<channel>.

    Args:
        client: TLSClient.
        channel: имя канала без @ (напр. "freelance_tg").
    """

    name = "tg_channel"
    ordered = True  # t.me/s отдаёт новые посты первыми, post_id числовые

    def __init__(self, client: TLSClient, channel: str) -> None:
        self.client = client
        self.channel = channel.strip().lstrip("@")

    def _parse(self, html: str) -> list[Lead***REMOVED***:
        leads: list[Lead***REMOVED*** = [***REMOVED***
        for block in _MSG_BLOCK_RE.finditer(html):
            post_ref, body = block.group(1), block.group(2)
            text_match = _TEXT_RE.search(body)
            text = ""
            if text_match:
                text = unescape(re.sub(r"<[^>***REMOVED***+>", " ", text_match.group(1)))
                text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            # post_ref уже вида "channel/post_id" (data-post) → id уникален в канале
            leads.append(
                Lead(
                    source=self.name,
                    source_id=post_ref,
                    text=Normalizer.normalize(text),
                    url=f"https://t.me/{self.channel***REMOVED***/{post_ref.split('/')[-1***REMOVED******REMOVED***",
                )
            )
        return leads

    async def fetch(self, limit: int = 50) -> list[Lead***REMOVED***:
        try:
            html = await self.client.get(f"https://t.me/s/{self.channel***REMOVED***")
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"tg_channel {self.channel***REMOVED*** fetch failed: {exc***REMOVED***") from exc
        leads = self._parse(html)[:limit***REMOVED***
        logger.info("tg_channel %s: parsed %d leads", self.channel, len(leads))
        return leads
