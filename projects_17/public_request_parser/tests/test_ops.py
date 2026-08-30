"""Hermetic tests: P11 ops scheduler/backoff/alerting."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.ops import IterationStats, ScheduleConfig, run_backoff, run_schedule


def test_backoff_is_exponential_and_capped() -> None:
    assert run_backoff(0) == 0.0
    assert run_backoff(1) == 5.0
    assert run_backoff(2) == 10.0
    assert run_backoff(3) == 20.0
    # cap
    config = ScheduleConfig(source_id="x", max_backoff=15.0)
    assert run_backoff(10, config=config) == 15.0


def test_iteration_stats_line() -> None:
    stats = IterationStats(
        source_id="trudvsem",
        iteration=1,
        consecutive_failures=2,
        ok=False,
        detail="error: boom",
        ts=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
    )
    line = stats.line()
    assert "src=trudvsem" in line
    assert "fail_streak=2" in line
    assert "boom" in line


@pytest.mark.asyncio
async def test_schedule_runs_max_iterations_and_records_stats() -> None:
    calls = 0

    async def run_once() -> str:
        nonlocal calls
        calls += 1
        return "ok 1 item"

    config = ScheduleConfig(source_id="x", interval_total=0.001)
    stats = await run_schedule(config=config, run_once=run_once, max_iterations=3)

    assert calls == 3
    assert len(stats) == 3
    assert all(s.ok for s in stats)
    assert stats[0].source_id == "x"


@pytest.mark.asyncio
async def test_schedule_backoff_and_alert_on_failure() -> None:
    alerts: list[tuple[str, str]] = []

    async def alert(level: str, message: str) -> None:
        alerts.append((level, message))

    async def run_once() -> str:
        raise RuntimeError("source down")

    config = ScheduleConfig(source_id="x", interval_total=0.001, max_backoff=0.01)
    stats = await run_schedule(
        config=config, run_once=run_once, alert=alert, max_iterations=3
    )

    assert len(alerts) == 3
    assert all(level == "warning" for level, _ in alerts)
    assert all(not s.ok for s in stats)
    assert stats[-1].consecutive_failures == 3


@pytest.mark.asyncio
async def test_schedule_stop_event() -> None:
    calls = 0

    async def run_once() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    stop = asyncio.Event()
    config = ScheduleConfig(source_id="x", interval_total=0.001)
    task = asyncio.create_task(
        run_schedule(config=config, run_once=run_once, stop_event=stop)
    )
    await asyncio.sleep(0.01)
    stop.set()
    await task

    assert calls >= 1  # цикл остановился по stop_event, а не по макс. итерациям


@pytest.mark.asyncio
async def test_schedule_isolates_source_failures() -> None:
    """Один сбой не убивает цикл; статистика честно отражает fail-стрейк."""
    attempts = 0

    async def run_once() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("network")
        return "recovered"

    config = ScheduleConfig(source_id="x", interval_total=0.001, max_backoff=0.01)
    stats = await run_schedule(config=config, run_once=run_once, max_iterations=2)

    assert stats[0].ok is False
    assert stats[1].ok is True
    assert stats[1].consecutive_failures == 0  # streak сброшен после успеха