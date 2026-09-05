"""PulseEngine — лента важных событий для UI (спека §9)."""

from __future__ import annotations

from typing import Any, List, Optional

from plugins_04.event.store import EventStore
from plugins_04.event.types import EventEntry, EventQuery, PulseEntry

# Категории, попадающие в pulse-ленту (fallback-поиск).
PULSE_CATEGORIES = (
    "task.completed",
    "task.failed",
    "session.created",
    "session.completed",
    "system.error",
    "memory.stored",
    "audit.decision",
    "audit.action",
)

_SEVERITY = {
    "completed": "success",
    "stored": "info",
    "created": "info",
    "error": "error",
    "failed": "error",
}


def _severity(event_type: str) -> str:
    suffix = event_type.rsplit(".", 1)[-1]
    return _SEVERITY.get(suffix, "info")


class PulseEngine:
    """Лента событий: подписка на bus (_on_event) + fallback-поиск по Store."""

    def __init__(self, bus: Any = None, store: Optional[EventStore] = None) -> None:
        self.bus = bus
        self.store = store
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _on_event(self, event: EventEntry) -> None:
        """Хендлер bus: сохраняет событие с флагом _pulse."""
        if self.store is None:
            return
        data = dict(event.data or {})
        data["_pulse"] = True
        self.store.store(
            event_type=event.event_type,
            source=event.source,
            data=data,
            correlation_id=event.correlation_id,
            session_id=event.session_id,
        )

    def get_pulse(self, limit: int = 20, project: str = "") -> List[PulseEntry]:
        if self.store is None:
            return []
        feed: List[PulseEntry] = []
        seen = set()
        # 1) события с флагом _pulse, 2) fallback — категории из PULSE_CATEGORIES
        candidates: List[EventEntry] = []
        flagged = [
            e
            for e in self.store.query(EventQuery(limit=100000))
            if isinstance(e.data, dict) and e.data.get("_pulse")
        ]
        if flagged:
            candidates = flagged
        else:
            for etype in PULSE_CATEGORIES:
                candidates.extend(self.store.query(EventQuery(event_type=etype, limit=limit)))
            candidates.sort(key=lambda e: e.timestamp, reverse=True)
        if project:
            candidates = [e for e in candidates if e.project == project]
        for e in candidates[:limit]:
            key = (e.event_id,)
            if key in seen:
                continue
            seen.add(key)
            data = e.data or {}
            title = f"{e.event_type.rsplit('.', 1)[-1].replace('_', ' ').capitalize()}"
            description = ""
            for k in ("description", "topic", "key", "error"):
                v = data.get(k)
                if isinstance(v, (str, int, float)) and v != "":
                    description = f"{k}: {v}"
                    break
            feed.append(
                PulseEntry(
                    icon=_severity(e.event_type) == "error" and "❌"
                    or _severity(e.event_type) == "success" and "✅"
                    or "📌",
                    title=title,
                    description=description,
                    timestamp=e.timestamp,
                    severity=_severity(e.event_type),
                    event_type=e.event_type,
                    event_id=e.event_id,
                )
            )
        return feed
