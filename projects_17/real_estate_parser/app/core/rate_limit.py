"""core/rate_limit.py — per-host rate limiting + bounded concurrency.

Token-bucket-ish per-host limiter: min interval between requests to the same host.
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse


class HostRateLimiter:
    """Token-bucket-ish per-host limiter: min interval between requests to the same host."""

    def __init__(self, min_interval: float = 1.0) -> None:
        self.min_interval = min_interval
        self._last: dict[str, float] = {}

    async def wait(self, url: str) -> None:
        """Sleep just enough to keep `min_interval` between same-host requests."""
        host = urlparse(url).netloc
        now = time.monotonic()
        last = self._last.get(host)
        if last is not None:
            wait_for = self.min_interval - (now - last)
            if wait_for > 0:
                await asyncio.sleep(wait_for)
        self._last[host] = time.monotonic()
