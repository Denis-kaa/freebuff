"""Telegram web-preview fixture adapter (P9).

P9 — технический adapter-only путь для Telegram web-preview:

- `TelegramPreviewParser` — разбор fixture HTML (публичные сообщения каналов)
  на `SourceItem` без полей автора;
- `TelegramWebPreviewAdapter` — SourceAdapter-порт: fixture-only; `policy`
  со статусом `ALLOWED` намеренно запрещён (live требует отдельного approval);
- без live-credentials, без global indexing, без outbound к авторам.

Модуль не выполняет сетевых вызовов и не импортирует платформенный код.
"""

from __future__ import annotations

import re
from typing import AsyncIterator
from urllib.parse import urljoin, urlparse

from app.domain import (
    AdapterError,
    SourceItem,
    SourcePolicy,
    SourcePolicyStatus,
)

_LINK_RE = re.compile(r"<a\s+[^>)*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_BLOCK_RE = re.compile(
    r'class="tgme_widget_message_text"[^>]*>(.*?)</div>', re.IGNORECASE | re.DOTALL
)
_TAG_RE = re.compile(r"<[^>)+>")


def _clean(value: str) -> str:
    """Убрать теги и схлопнуть пробелы."""
    return " ".join(_TAG_RE.sub(" ", value).split())


class TelegramPreviewParser:
    """Разобрать fixture-документ web-preview в нормализованные SourceItems."""

    def __init__(self, source_id: str, *, base_url: str | None = None) -> None:
        if not source_id.strip():
            raise AdapterError("source_id must be non-empty")
        self.source_id = source_id.strip()
        self.base_url = base_url

    def parse(self, document: str) -> tuple[SourceItem, ...]:
        """Извлечь элементы из блоков `tgme_widget_message_text`.

        Каждый блок сообщения содержит ссылку; title/summary — весь текст
        сообщения (без author-полей). Ссылки без http(s) пропускаются.
        """
        blocks = _BLOCK_RE.findall(document) or [document]
        items: list[SourceItem] = []
        for block in blocks:
            link_match = _LINK_RE.search(block)
            if link_match is None:
                continue
            raw_href = link_match.group(1).strip()
            candidate = urljoin(self.base_url or "", raw_href)
            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            text = _clean(block)
            if not text:
                continue
            items.append(
                SourceItem(
                    item_id=f"tg-{len(items)}",
                    canonical_url=candidate,
                    title=text[:140],
                    summary=text[:300],
                    metadata={
                        "feed_format": "telegram_web_preview",
                        "channel": _channel_name(self.base_url, candidate),
                    },
                )
            )
        return tuple(items)


def raw_doc(document: str) -> str:
    """Весь документ без тегов (fixture-упрощение)."""
    return _clean(document)


def _channel_name(base_url: str | None, candidate: str) -> str:
    """Имя канала из base_url (t.me/...), иначе пусто."""
    if base_url:
        return base_url.rstrip("/").split("/")[-1]
    return ""


class TelegramWebPreviewAdapter:
    """SourceAdapter для fixture web-preview; live-policy запрещена."""

    def __init__(
        self,
        source_id: str,
        document: str,
        *,
        policy: SourcePolicy | None = None,
        base_url: str | None = None,
    ) -> None:
        if policy is not None and policy.status is SourcePolicyStatus.ALLOWED:
            raise AdapterError(
                "Telegram web-preview adapter cannot be used as allowed live transport"
            )
        self.source_id = source_id
        self._document = document
        self._policy = policy
        self._parser = TelegramPreviewParser(source_id, base_url=base_url)

    async def fetch(
        self,
        *,
        limit: int = 50,
        checkpoint: str | None = None,
    ) -> AsyncIterator[SourceItem]:
        """Bounded items после checkpoint; никакой сети."""
        if limit < 1:
            raise AdapterError("limit must be >= 1")
        if self._policy is not None and self._policy.status is SourcePolicyStatus.ALLOWED:
            raise AdapterError(
                "Telegram web-preview adapter cannot be used as live allowed transport"
            )
        items = self._parser.parse(self._document)
        start = 0
        if checkpoint is not None:
            for index, item in enumerate(items):
                if item.item_id == checkpoint:
                    start = index + 1
                    break
        for item in items[start : start + limit]:
            yield item

    async def health(self) -> bool:
        """Parseability fixture; не является live-здоровьем канала."""
        try:
            self._parser.parse(self._document)
        except AdapterError:
            return False
        return True


__all__ = [
    "TelegramPreviewParser",
    "TelegramWebPreviewAdapter",
    "raw_doc",
]