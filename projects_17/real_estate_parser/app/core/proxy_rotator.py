"""core/proxy_rotator.py — round-robin proxy rotation with health tracking.

Provider-agnostic: takes a list of proxy URLs from config. A proxy that
produces 403/429/connection errors gets a cooldown before reuse.
"""
from __future__ import annotations

import itertools
import logging
import time

logger = logging.getLogger(__name__)


class ProxyRotator:
    """Round-robin proxy rotation with cooldown for failing proxies."""

    def __init__(self, proxies: list[str], cooldown_s: float = 60.0) -> None:
        self._proxies = list(proxies)
        self._cooldown_s = cooldown_s
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None
        self._cooldown_until: dict[str, float] = {}
        self._lock_index = 0

    def __len__(self) -> int:
        return len(self._proxies)

    @property
    def proxies(self) -> list[str]:
        return list(self._proxies)

    def next(self) -> str | None:
        """Return next healthy proxy, or None if all are cooling down / list empty."""
        if not self._cycle:
            return None
        n = len(self._proxies)
        now = time.monotonic()
        for _ in range(n):
            proxy = next(self._cycle)
            until = self._cooldown_until.get(proxy, 0.0)
            if now >= until:
                return proxy
        logger.debug("all %d proxies cooling down", n)
        return None

    def report_failure(self, proxy: str, status_code: int | None = None) -> None:
        """Put a proxy into cooldown after a failure (403/429/conn error)."""
        penalty = self._cooldown_s
        if status_code in (403, 429):
            penalty *= 2
        self._cooldown_until[proxy] = time.monotonic() + penalty
        logger.warning("proxy %s failed (status=%s), cooldown %.0fs", proxy, status_code, penalty)

    def report_success(self, proxy: str) -> None:
        self._cooldown_until.pop(proxy, None)

    def healthy(self) -> list[str]:
        now = time.monotonic()
        return [p for p in self._proxies if self._cooldown_until.get(p, 0.0) <= now]
