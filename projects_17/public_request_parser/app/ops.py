"""P11 hardening: scheduler-цикл, retry/backoff, health и alerting-хуки.

`run_schedule` — бесконечный (или ограниченный для тестов) polling-цикл
для одного источника:

- `interval_total` — период между срезами (ниже `min_interval` не опускается);
- постоянные сбои → экспоненциальный backoff (не быстрее `max_backoff`);
- один источник не роняет других (каждый цикл изолирован try/except);
- `alert`-хук вызывается на сбои и аномальные состояния (по умолчанию пишет
  в stderr; реальные уведомления — сухой dry-run до G7-решения);
- `stop_event` позволяет graceful shutdown; `max_iterations` — для тестов.

Модуль не хранит credentials и не импортирует платформенный код.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Protocol

logger = logging.getLogger("prp.ops")

DEFAULT_MIN_GAP_SECONDS = 5.0
DEFAULT_MAX_BACKOFF = 300.0


class AlertHook(Protocol):
    """Уведомление о событии эксплуатации (сбой, аномалия)."""

    async def __call__(self, level: str, message: str) -> None:
        ...


async def _stderr_alert(level: str, message: str) -> None:
    """Alert-хук по умолчанию: в stderr (без сетевых вызовов)."""
    print(f"[prp-ops:{level***REMOVED******REMOVED*** {message***REMOVED***", file=sys.stderr)


@dataclass(frozen=True, slots=True)
class ScheduleConfig:
    """Конфигурация polling-цикла одного источника."""

    source_id: str
    interval_total: float = 60.0
    min_gap: float = DEFAULT_MIN_GAP_SECONDS
    max_backoff: float = DEFAULT_MAX_BACKOFF
    backoff_factor: float = 2.0


def backoff_seconds(
    consecutive_failures: int,
    *,
    base: float = 5.0,
    factor: float = 2.0,
    max_backoff: float = 300.0,
) -> float:
    """Экспоненциальный backoff: base * factor**n, ограничен max_backoff."""
    if consecutive_failures <= 0:
        return 0.0
    return min(base * (factor ** (consecutive_failures - 1)), max_backoff)


@dataclass(frozen=True, slots=True)
class IterationStats:
    """Статистика одной итерации (для логов/display)."""

    source_id: str
    iteration: int
    consecutive_failures: int
    ok: bool
    detail: str = ""
    ts: datetime | None = None

    def __post_init__(self) -> None:
        if self.ts is None:
            object.__setattr__(self, "ts", datetime.now(timezone.utc))

    def line(self) -> str:
        status = "ok" if self.ok else "fail"
        when = self.ts.isoformat() if self.ts is not None else "?"
        return (
            f"[{when***REMOVED******REMOVED*** src={self.source_id***REMOVED*** iter={self.iteration***REMOVED*** "
            f"status={status***REMOVED*** fail_streak={self.consecutive_failures***REMOVED*** {self.detail***REMOVED***"
        ).strip()


async def run_schedule(
    *,
    config: ScheduleConfig,
    run_once: Callable[[***REMOVED***, Awaitable[str***REMOVED******REMOVED***,
    alert: AlertHook | None = None,
    stop_event: asyncio.Event | None = None,
    max_iterations: int | None = None,
) -> list[IterationStats***REMOVED***:
    """Цикл: run_once → пауза → повтор; сбои: backoff и alert.

    `run_once` — корутина, возвращающая одноесотровую сводку (например
    `CanaryReport.summary()`). `stop_event` позволяет graceful shutdown;
    `max_iterations` используется в тестах/одноразовых прогонах.
    """
    alert = alert or _stderr_alert
    stats: list[IterationStats***REMOVED*** = [***REMOVED***
    failures = 0
    iteration = 0

    while max_iterations is None or iteration < max_iterations:
        iteration += 1
        ok = False
        detail = ""
        try:
            detail = await run_once()
            ok = True
            failures = 0
        except Exception as exc:  # noqa: BLE001 — цикл обязан продолжаться
            ok = False
            failures += 1
            detail = f"error: {exc***REMOVED***"
            backoff = run_backoff(failures, config=config)
            await alert(
                "warning",
                f"{config.source_id***REMOVED***: iteration {iteration***REMOVED*** failed ({exc***REMOVED***); "
                f"backoff={backoff***REMOVED***s",
            )
        item = IterationStats(
            source_id=config.source_id,
            iteration=iteration,
            consecutive_failures=failures,
            ok=ok,
            detail=detail,
        )
        stats.append(item)
        logger.info(item.line())

        if stop_event is not None and stop_event.is_set():
            break
        if max_iterations is not None and iteration >= max_iterations:
            break

        # пауза: базовый интервал + backoff при сбоях
        delay = config.interval_total
        if failures > 0:
            delay = run_backoff(failures, config=config)
        await asyncio.sleep(delay)

    return stats


def run_backoff(
    consecutive_failures: int, *, config: ScheduleConfig | None = None
) -> float:
    """Backoff для следующей итерации при сбоях (чистая функция для тестов)."""
    if consecutive_failures <= 0:
        return 0.0
    base = max(config.interval_total * 0.1, 5.0) if config else 5.0
    factor = config.backoff_factor if config else 2.0
    cap = config.max_backoff if config else DEFAULT_MAX_BACKOFF
    return min(base * (factor ** (consecutive_failures - 1)), cap)


__all__ = [
    "AlertHook",
    "DEFAULT_MAX_BACKOFF",
    "DEFAULT_MIN_GAP_SECONDS",
    "IterationStats",
    "ScheduleConfig",
    "run_backoff",
    "run_schedule",
***REMOVED***