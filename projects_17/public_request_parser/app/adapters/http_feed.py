"""Policy-gated HTTP feed transport (P12).

`HttpFeedAdapter` читает RSS/Atom по HTTP(S) и прогоняет через существующий
`RSSAtomParser`. Live-запрос разрешён ТОЛЬКО для `SourcePolicy` со статусом
`ALLOWED` (G2); `conditional`/`technical_candidate` и т.п. получают
`AdapterError` — no silent fallback.

Сетевой вызов инжектируется через `http_get` (по умолчанию httpx), чтобы
тесты оставались hermetic. Credentials и лимиты — отдельно, не здесь.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import AsyncIterator

from app.domain import AdapterError, SourceItem, SourcePolicy, SourcePolicyStatus
from app.rss_atom import RSSAtomParser

HttpGetter = Callable[[str***REMOVED***, Awaitable[bytes***REMOVED******REMOVED***


async def _default_http_get(url: str) -> bytes:
    """Реальный transport (используется только для allowed-источников)."""
    import httpx

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


class HttpFeedAdapter:
    """Live RSS/Atom транспорт, привязанный к allowed policy."""

    def __init__(
        self,
        source_id: str,
        *,
        policy: SourcePolicy,
        http_get: HttpGetter | None = None,
        base_url: str | None = None,
        user_agent: str = "public-request-parser/0.1 (read-only)",
    ) -> None:
        if not source_id.strip():
            raise AdapterError("source_id must be non-empty")
        self.source_id = source_id.strip()
        self._policy = policy
        self._http_get = http_get or _default_http_get
        self._parser = RSSAtomParser(source_id, base_url=base_url)
        self._user_agent = user_agent

    def _ensure_allowed_live(self) -> None:
        if self._policy.status is not SourcePolicyStatus.ALLOWED:
            raise AdapterError(
                f"live polling requires ALLOWED source policy, got {self._policy.status.value***REMOVED***"
            )
        if not self._policy.can_poll:
            raise AdapterError("live polling disabled by source policy (can_poll=False)")

    async def fetch(
        self,
        *,
        limit: int = 50,
        checkpoint: str | None = None,
    ) -> AsyncIterator[SourceItem***REMOVED***:
        """Загрузить фид и отдать bounded items после checkpoint."""
        if limit < 1:
            raise AdapterError("limit must be >= 1")
        self._ensure_allowed_live()
        payload = await self._http_get(self._policy.endpoint)
        result = self._parser.parse(payload)
        start = 0
        if checkpoint is not None:
            for index, item in enumerate(result.items):
                if item.item_id == checkpoint:
                    start = index + 1
                    break
        for item in result.items[start : start + limit***REMOVED***:
            yield item

    async def health(self) -> bool:
        """Техническая доступность источника; policy-гейт соблюдается."""
        self._ensure_allowed_live()
        try:
            payload = await self._http_get(self._policy.endpoint)
            self._parser.parse(payload)
        except Exception:
            return False
        return True


__all__ = ["HttpFeedAdapter", "HttpGetter"***REMOVED***