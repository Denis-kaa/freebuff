"""retry_policy.py — экспоненциальный backoff + jitter + circuit breaker.

Требование промта 69 п.4: "Circuit Breaker & Retry with Jitter".
Паттерн переиспользован из `scripts_01/notification.py` (RETRY_BASE_DELAY/2.0),
но вынесен в изолированный модуль с jitter.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Awaitable, Callable


class CircuitOpenError(Exception):
    """Поднято, когда circuit breaker разомкнут (слишком много сбоев подряд)."""


class RetryPolicy:
    """Повторная попытка с экспоненциальным backoff и случайным jitter.

    Args:
        max_attempts: максимум попыток (включая первую).
        base_delay: базовая задержка, сек.
        backoff: множитель экспоненты (2.0 = удвоение).
        jitter: доля случайного сдвига от задержки (0.0..1.0).
        max_delay: потолок задержки, сек.
        failure_threshold: сколько сбоев подряд размыкает circuit breaker.
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
        """Независимая копия с теми же параметрами (для per-adapter изоляции)."""
        return RetryPolicy(
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            backoff=self.backoff,
            jitter=self.jitter,
            max_delay=self.max_delay,
            failure_threshold=self.failure_threshold,
            cooldown_s=self.cooldown_s,
        )

    # ── задержка ────────────────────────────────────────────────────
    def next_delay(self, attempt: int) -> float:
        """Задержка перед попыткой `attempt` (attempt с 0).

        delay = base * backoff^attempt, сдвинутый на ±jitter%.
        """
        exponential = min(self.base_delay * (self.backoff ** attempt), self.max_delay)
        spread = exponential * self.jitter
        return max(0.0, exponential + random.uniform(-spread, spread))

    # ── circuit breaker ─────────────────────────────────────────────
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

    # ── исполнение ──────────────────────────────────────────────────
    async def run(self, fn: Callable[..., Awaitable[Any***REMOVED******REMOVED***, *args: Any, **kwargs: Any) -> Any:
        """Выполняет async-функцию с ретраями.

        Raises:
            CircuitOpenError: если circuit breaker разомкнут.
            Exception: последняя ошибка после исчерпания попыток.
        """
        if self.is_open:
            # Recovery (cooldown): после паузы разрешаем probe-попытку (полу-открыт).
            if self._opened_at is not None and (time.monotonic() - self._opened_at) >= self.cooldown_s:
                self._consecutive_failures = 0
                self._opened_at = None
            else:
                raise CircuitOpenError(
                    f"circuit open after {self._consecutive_failures***REMOVED*** consecutive failures"
                )
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                result = await fn(*args, **kwargs)
                self.record_success()
                return result
            except Exception as exc:  # noqa: BLE001 — ретраим любые сбои сети
                last_error = exc
                self.record_failure()
                if self.is_open:
                    raise CircuitOpenError(str(exc)) from exc
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.next_delay(attempt))
        assert last_error is not None
        raise last_error
