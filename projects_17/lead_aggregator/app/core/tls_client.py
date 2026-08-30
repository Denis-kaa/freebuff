"""tls_client.py — HTTP-клиент с опциональным TLS-impersonation.

Абстракция из PHASE2_ARCHITECTURE.md §3 (W-2/W-4): по умолчанию `httpx.AsyncClient`,
при наличии `curl_cffi` — impersonation под браузер (JA3/JA4) для бирж под Cloudflare.

В v1 (Фаза 3) реализован httpx-путь; curl_cffi подключается опционально, если
установлен в среде (см. W-2: отсутствует на Python 3.14.6/Termux).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

try:  # optional dependency (W-2)
    import curl_cffi.requests as cffi_requests  # type: ignore[import-not-found]
    HAS_CURL_CFFI = True
except Exception:  # noqa: BLE001
    cffi_requests = None  # type: ignore[assignment]
    HAS_CURL_CFFI = False

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}


class TLSClient:
    """Async HTTP-клиент.

    Args:
        impersonate: браузерный профиль для curl_cffi ("chrome130"/None).
        proxy: URL прокси (http/socks5). Stub-поддержка в v1.
        timeout: таймаут запроса, сек.
    """

    def __init__(
        self,
        impersonate: str | None = None,
        proxy: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.impersonate = impersonate
        self.proxy = proxy
        self.timeout = timeout
        self._httpx: httpx.AsyncClient | None = None

    @property
    def using_impersonation(self) -> bool:
        return bool(self.impersonate and HAS_CURL_CFFI)

    async def _client(self) -> httpx.AsyncClient:
        if self._httpx is None:
            kwargs: dict[str, Any] = {
                "headers": dict(DEFAULT_HEADERS),
                "timeout": self.timeout,
                "follow_redirects": True,
            }
            if self.proxy:
                kwargs["proxy"] = self.proxy
            self._httpx = httpx.AsyncClient(**kwargs)
        return self._httpx

    async def get(self, url: str, **params: Any) -> str:
        """GET и возврат текста (HTML/JSON как строка)."""
        if self.using_impersonation:
            # curl_cffi.requests — синхронный; выполняем в executor (v1 fallback).
            import asyncio

            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: cffi_requests.get(url, impersonate=self.impersonate, timeout=self.timeout).text,  # type: ignore[union-attr]
            )
        client = await self._client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text

    async def get_json(self, url: str, **params: Any) -> dict[str, Any]:
        """GET и возврат JSON-объекта."""
        client = await self._client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        if self._httpx is not None:
            await self._httpx.aclose()
            self._httpx = None
