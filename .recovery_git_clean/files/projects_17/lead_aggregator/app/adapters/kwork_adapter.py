"""kwork_adapter.py — адаптер Kwork (первый источник по roadmap, PHASE2 §8).

Парсит ленту заказов kwork.ru/projects через TLSClient. Kwork — маркетплейс
услуг; прямые заказы «клиент ищет исполнителя» = горячие лиды для Attract.

Примечание (W-2/W-4): для стабильного парсинга Kwork под Cloudflare нужен
`curl_cffi`; v1 использует httpx + заголовки браузера (TLSClient).
"""
from __future__ import annotations

import logging
***REMOVED***
import urllib.parse

from app.adapters.base import AdapterError, BaseAdapter
from app.core.tls_client import TLSClient
from app.models import Lead
from app.processors.intent_classifier import Normalizer

logger = logging.getLogger(__name__)

# URL вида /projects/<slug> или /projects/<slug>/<numeric-id>; numeric-id — уникален
_ORDER_RE = re.compile(
    r"https?://kwork\.ru/projects/([a-z0-9_-***REMOVED***+)(?:/(\d+))?", re.IGNORECASE
)

# W-16 (Фаза 4, live-verify 2026-08-10): kwork.ru/projects стал SPA — статичный HTML
# содержит только скелет с прелоадерами (js-wants-list-preloaders / wants-content),
# заказы грузятся JS. Без headless-браузера (playwright/curl_cffi, W-2) лента
# недоступна. Маркеры ниже — детектор «SPA-режима» для честной диагностики.
_SPA_SHELL_MARKERS = ("js-wants-list-preloaders", "wants-content")


class KworkAdapter(BaseAdapter):
    """Лента заказов Kwork.

    Args:
        client: TLSClient (httpx/curl_cffi).
        feed_url: URL ленты (default из Config).
        category: фильтр по ключевой фразе URL (опционально).
    """

    name = "kwork"

    def __init__(
        self,
        client: TLSClient,
        feed_url: str = "https://kwork.ru/projects",
        category: str | None = None,
    ) -> None:
        self.client = client
        self.feed_url = feed_url
        self.category = category

    def _parse_items(self, html: str) -> list[dict[str, str***REMOVED******REMOVED***:
        """Извлекает заказы из HTML ленты (best-effort, без bs4-жесткости).

        Стратегия: найти все ссылки вида kwork.ru/projects/<slug> и собрать
        пары (url, anchor-текст). Лимит дублей по URL.
        """
        items: list[dict[str, str***REMOVED******REMOVED*** = [***REMOVED***
        seen: set[str***REMOVED*** = set()
        for match in _ORDER_RE.finditer(html):
            slug, numeric_id = match.group(1), match.group(2)
            source_id = numeric_id or slug  # уникальный id заказа (число предпочтительнее)
            if source_id in seen:
                continue
            seen.add(source_id)
            # заголовок заказа — первый текст после ссылки (грубо, v1)
            snippet = html[match.end() : match.end() + 300***REMOVED***
            snippet = re.sub(r"<[^>***REMOVED***+>", " ", snippet)
            snippet = re.sub(r"\s+", " ", snippet).strip()[:200***REMOVED***
            items.append({"url": match.group(0), "text": snippet, "source_id": source_id***REMOVED***)
        return items

    def _looks_like_spa_shell(self, html: str) -> bool:
        """True — страница-скелет SPA без карточек заказов (W-16)."""
        if any(m in html for m in _SPA_SHELL_MARKERS) and not _ORDER_RE.search(html):
            logger.warning(
                "kwork: SPA-shell обнаружен (W-16) — лента грузится JS; "
                "нужен headless-браузер (playwright/curl_cffi, W-2)"
            )
            return True
        return False

    async def fetch(self, limit: int = 50) -> list[Lead***REMOVED***:
        try:
            url = self.feed_url
            if self.category:
                url = f"{url***REMOVED***?q={urllib.parse.quote(self.category)***REMOVED***"
            html = await self.client.get(url)
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"kwork fetch failed: {exc***REMOVED***") from exc

        if self._looks_like_spa_shell(html):
            # Не молчим про 0 лидов: SPA без headless — известное ограничение.
            return [***REMOVED***

        leads: list[Lead***REMOVED*** = [***REMOVED***
        for item in self._parse_items(html)[:limit***REMOVED***:
            leads.append(
                Lead(
                    source=self.name,
                    source_id=item["source_id"***REMOVED***,
                    text=Normalizer.normalize(item["text"***REMOVED***),
                    url=item["url"***REMOVED***,
                )
            )
        logger.info("kwork: parsed %d leads", len(leads))
        return leads
