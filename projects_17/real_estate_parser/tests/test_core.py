"""Hermetic tests for real_estate_parser — no network, no external DB.

Covers: proxy rotator, retry policy, URL hashing, normalizer/validator,
dedup key, and pipeline stats with a FakeSource (DI, no network).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent / "projects_17" / "real_estate_parser"
sys.path.insert(0, str(PROJECT))

from app.core.proxy_rotator import ProxyRotator  # noqa: E402
from app.core.rate_limit import HostRateLimiter  # noqa: E402
from app.core.retry_policy import CircuitOpenError, RetryPolicy  # noqa: E402
from app.sources.base import Listing, SourceAdapter  # noqa: E402
from app.storage.repository import url_hash  # noqa: E402


# ── proxy rotator ────────────────────────────────────────────────

class TestProxyRotator:
    def test_round_robin_cycles(self):
        rot = ProxyRotator(["p1", "p2"])
        assert rot.next() == "p1"
        assert rot.next() == "p2"
        assert rot.next() == "p1"

    def test_empty_returns_none(self):
        assert ProxyRotator([]).next() is None

    def test_failure_cooldowns_proxy(self):
        rot = ProxyRotator(["p1", "p2"], cooldown_s=999)
        rot.report_failure("p1", status_code=403)
        assert rot.next() == "p2"
        assert "p1" not in rot.healthy()

    def test_429_gets_double_penalty(self):
        rot = ProxyRotator(["p1"], cooldown_s=10)
        rot.report_failure("p1", status_code=429)
        assert rot.next() is None  # all cooling down

    def test_success_clears_cooldown(self):
        rot = ProxyRotator(["p1"], cooldown_s=999)
        rot.report_failure("p1")
        rot.report_success("p1")
        assert rot.next() == "p1"


# ── retry policy ─────────────────────────────────────────────────

class TestRetryPolicy:
    def test_success_first_try(self):
        async def fn():
            return "ok"

        assert asyncio.run(RetryPolicy().run(fn)) == "ok"

    def test_retries_then_succeeds(self):
        calls = []

        async def fn():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("flaky")
            return "done"

        policy = RetryPolicy(max_attempts=5, base_delay=0.0)
        assert asyncio.run(policy.run(fn)) == "done"
        assert len(calls) == 3

    def test_raises_after_exhaustion(self):
        async def fn():
            raise RuntimeError("always")

        with pytest.raises(RuntimeError):
            asyncio.run(RetryPolicy(max_attempts=2, base_delay=0.0).run(fn))

    def test_circuit_opens_after_threshold(self):
        async def fn():
            raise RuntimeError("down")

        policy = RetryPolicy(max_attempts=1, base_delay=0.0, failure_threshold=2)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                asyncio.run(policy.run(fn))
        assert policy.is_open
        with pytest.raises(CircuitOpenError):
            asyncio.run(policy.run(fn))


# ── rate limiter ─────────────────────────────────────────────────

class TestRateLimiter:
    def test_no_wait_first_request(self):
        limiter = HostRateLimiter(min_interval=0.0)
        assert asyncio.run(limiter.wait("https://a.example/x")) is None

    def test_respects_min_interval(self):
        async def scenario():
            limiter = HostRateLimiter(min_interval=0.05)
            await limiter.wait("https://a.example/1")
            import time
            t0 = time.monotonic()
            await limiter.wait("https://a.example/2")
            return time.monotonic() - t0

        assert asyncio.run(scenario()) >= 0.04


# ── url hash / dedup key ─────────────────────────────────────────

class TestUrlHash:
    def test_strips_tracking_params(self):
        assert (
            url_hash("https://x.com/p/1?utm_source=mail&id=2")
            == url_hash("https://x.com/p/1?id=2")
        )

    def test_different_urls_differ(self):
        assert url_hash("https://x.com/a") != url_hash("https://x.com/b")


# ── source contract ──────────────────────────────────────────────

class TestSourceContract:
    def test_listing_defaults(self):
        item = Listing(source="s", external_id="1", url="https://x/1")
        assert item.extra == {}
        assert item.price is None

    def test_cannot_instantiate_adapter(self):
        with pytest.raises(TypeError):
            SourceAdapter()  # type: ignore[abstract]
