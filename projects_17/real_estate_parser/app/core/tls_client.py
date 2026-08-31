"""core/tls_client.py — async HTTP client with optional TLS impersonation.

Default transport is `httpx.AsyncClient`. If `curl_cffi` is installed,
it is used (via executor) for TLS-fingerprint-sensitive targets.
"""
from __future__ import annotations

import asyncio
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}


class TLSClient:
    """Async HTTP client.

    Args:
        impersonate: browser profile for curl_cffi ("chrome130"/None).
        proxy: proxy URL (http/socks5).
        timeout: request timeout, sec.
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
        """GET and return text (HTML/JSON as string)."""
        if self.using_impersonation:
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
        """GET and return JSON object."""
        client = await self._client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        if self._httpx is not None:
            await self._httpx.aclose()
            self._httpx = None
