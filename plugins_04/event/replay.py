"""EventReplay — воспроизведение событий и rebuild состояния (спека §6)."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from plugins_04.event.store import EventStore
from plugins_04.event.types import EventEntry, EventQuery, RebuildResult, ReplayResult


class EventReplay:
    """Replay событий из Store через произвольный handler."""

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def _run(
        self,
        events: list[EventEntry],
        handler: Optional[Callable[[EventEntry], Any]] = None,
        start: float = 0.0,
    ) -> ReplayResult:
        delivered = 0
        errors = 0
        for event in events:
            if handler is None:
                continue
            try:
                handler(event)
                delivered += 1
            except Exception:  # noqa: BLE001
                errors += 1
        return ReplayResult(
            total_events=len(events),
            delivered=delivered,
            errors=errors,
            duration_ms=round((time.monotonic() - start) * 1000, 2),
        )

    def replay(
        self,
        query: EventQuery,
        handler: Optional[Callable[[EventEntry], Any]] = None,
        speed: str = "instant",
    ) -> ReplayResult:
        start = time.monotonic()
        events = self.store.query(query)
        return self._run(events, handler, start)

    def replay_session(
        self,
        session_id: str,
        handler: Optional[Callable[[EventEntry], Any]] = None,
    ) -> ReplayResult:
        return self.replay(EventQuery(session_id=session_id, limit=10000), handler)

    def replay_workflow(
        self,
        correlation_id: str,
        handler: Optional[Callable[[EventEntry], Any]] = None,
    ) -> ReplayResult:
        return self.replay(EventQuery(correlation_id=correlation_id, limit=10000), handler)

    def rebuild(
        self,
        target: str,
        process_func: Optional[Callable[[EventEntry], Any]] = None,
        clear_func: Optional[Callable[[], None]] = None,
        event_filter: Optional[Callable[[EventEntry], bool]] = None,
    ) -> RebuildResult:
        events = [
            e
            for e in self.store.query(EventQuery(source=target, limit=100000))
            if event_filter is None or event_filter(e)
        ]
        if clear_func is not None:
            try:
                clear_func()
            except Exception:  # noqa: BLE001
                pass
        errors = 0
        for event in events:
            if process_func is not None:
                try:
                    process_func(event)
                except Exception:  # noqa: BLE001
                    errors += 1
        return RebuildResult(target=target, events_processed=len(events), errors=errors)
