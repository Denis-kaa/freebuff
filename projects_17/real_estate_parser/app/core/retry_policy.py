"""core/retry_policy.py — exponential backoff + jitter + circuit breaker.

Pattern reused from lead_aggregator/app/core/retry_policy.py.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open (too many consecutive failures)."""


class RetryPolicy:
    """Retry with exponential backoff, jitter, and circuit breaker.

    Args:
        max_attempts: maximum attempts (including the first).
        base_delay: base delay, sec.
        backoff: multiplier exponent (2.0 = doubling).
        jitter: fraction of random shift from delay (0.0..1.0).
        max_delay: ceiling of delay, sec.
        failure_threshold: consecutive failures to open the breaker.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff: float = 2.0,
        jitter: float = 0.2,
        max_delay: float = 60.0,
        failure_threshold: int = 5,
        cooldown_s: float = 300.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff = backoff
        self.jitter = jitter
        self.max_delay = max_delay
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def clone(self) -> "RetryPolicy":
        """Independent copy with same parameters (per-adapter isolation)."""
        return RetryPolicy(
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            backoff=self.backoff,
            jitter=self.jitter,
            max_delay=self.max_delay,
            failure_threshold=self.failure_threshold,
            cooldown_s=self.cooldown_s,
        )

    # ── delay ────────────────────────────────────────────────────
    def next_delay(self, attempt: int) -> float:
        """Delay before attempt `attempt` (attempt starts at 0)."""
        exponential = min(self.base_delay * (self.backoff ** attempt), self.max_delay)
        spread = exponential * self.jitter
        return max(0.0, exponential + random.uniform(-spread, spread))

    # ── circuit breaker ──────────────────────────────────────────
    @property
    def is_open(self) -> bool:
        return self._consecutive_failures >= self.failure_threshold

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self.is_open and self._opened_at is None:
            self._opened_at = time.monotonic()

    def _recover_if_cooled(self) -> None:
        """Half-open recovery: reset the breaker once the cooldown has passed."""
        if self._opened_at is not None and (time.monotonic() - self._opened_at) >= self.cooldown_s:
            self._consecutive_failures = 0
            self._opened_at = None

    # ── execution ────────────────────────────────────────────────
    async def run(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        """Executes async fn with retries."""
        if self.is_open:
            self._recover_if_cooled()
            if self.is_open:
                raise CircuitOpenError("circuit breaker is open")

        last_exc: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                result = await fn(*args, **kwargs)
                self.record_success()
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self.record_failure()
                if attempt + 1 < self.max_attempts:
                    await asyncio.sleep(self.next_delay(attempt))
        assert last_exc is not None
        raise last_exc
