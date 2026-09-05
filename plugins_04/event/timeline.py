"""TimelineEngine — человекочитаемая временная шкала событий (спека §7)."""

from __future__ import annotations

from typing import Optional

from plugins_04.event.store import EventStore
from plugins_04.event.types import EventEntry, EventQuery, Timeline, TimelineEntry

# Иконки: точное совпадение важнее wildcard (тест: task.unknown → 📌,
# т.к. task.* отсутствует в таблице).
EVENT_ICONS = {
    "system.startup": "🚀",
    "system.shutdown": "🛑",
    "system.error": "❌",
    "session.created": "📋",
    "session.completed": "✅",
    "task.created": "📋",
    "task.started": "▶️",
    "task.completed": "✅",
    "task.failed": "❌",
    "step.started": "▶️",
    "step.completed": "✅",
    "memory.stored": "💾",
    "knowledge.indexed": "📚",
    "audit.decision": "🧭",
    "audit.action": "⚡",
    "audit.config_change": "⚙️",
}

_WILDCARD_ICONS = {
    "error": "❌",
    "completed": "✅",
}


def get_event_icon(event_type: str) -> str:
    """Иконка события: точное совпадение → wildcard-суффикс → 📌."""
    if event_type in EVENT_ICONS:
        return EVENT_ICONS[event_type]
    for suffix, icon in _WILDCARD_ICONS.items():
        if event_type.endswith("." + suffix):
            return icon
    return "📌"


def _describe(event: EventEntry) -> tuple[str, str]:
    """(title, description) по типу события."""
    data = event.data or {}
    etype = event.event_type.rsplit(".", 1)[-1].replace("_", " ")
    title = f"{etype.capitalize()} [{event.source}]" if event.source else etype.capitalize()
    parts = []
    for key in ("description", "topic", "step_id", "task_id", "key", "doc_id", "error", "version"):
        value = data.get(key)
        if isinstance(value, (str, int, float)) and value != "":
            parts.append(f"{key}: {value}")
    if not parts and data:
        for key, value in list(data.items())[:2]:
            if isinstance(value, (str, int, float)) and key != "_pulse":
                parts.append(f"{key}: {value}")
    return title, "; ".join(parts)


class TimelineEngine:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    @staticmethod
    def _build(events: list[EventEntry]) -> Timeline:
        entries = []
        for e in events:
            title, description = _describe(e)
            entries.append(
                TimelineEntry(
                    timestamp=e.timestamp,
                    event_type=e.event_type,
                    icon=get_event_icon(e.event_type),
                    title=title,
                    description=description,
                    session_id=e.session_id,
                    project=e.project,
                    event_id=e.event_id,
                )
            )
        return Timeline(entries=entries, total=len(entries))

    def get_timeline(self, limit: int = 50, project: str = "") -> Timeline:
        q = EventQuery(limit=100000, project=project or None)
        result = self._build(self.store.query(q))
        result.entries = result.entries[:limit]
        return result

    def _get_timeline_all(self, limit: int = 50) -> Timeline:
        events = self.store.query(EventQuery(limit=limit))
        result = self._build(events)
        result.total = self.store.get_stats()["total_events"]
        # total — полное число событий в Store; entries — окно limit
        result.entries = result.entries[:limit]
        return result

    def get_timeline_by_session(self, session_id: str, limit: int = 50) -> Timeline:
        events = self.store.query(EventQuery(session_id=session_id, limit=limit))
        result = self._build(events)
        result.total = len(self.store.query(EventQuery(session_id=session_id, limit=100000)))
        result.entries = result.entries[:limit]
        return result

    def get_timeline_by_user(self, user: str, limit: int = 50) -> Timeline:
        events = self.store.query(EventQuery(user=user, limit=limit))
        result = self._build(events)
        result.total = len(self.store.query(EventQuery(user=user, limit=100000)))
        result.entries = result.entries[:limit]
        return result

    def search_timeline(self, text: str, limit: int = 50) -> Timeline:
        return self._build(self.store.query(EventQuery(data_search=text, limit=limit)))

    @staticmethod
    def format_timeline_text(timeline: Timeline) -> str:
        if not timeline.entries:
            return "📭 Нет событий"
        lines = []
        for entry in timeline.entries:
            line = f"{entry.icon} {entry.title}"
            if entry.description:
                line += f" — {entry.description}"
            if entry.timestamp:
                line += f"  ({entry.timestamp})"
            lines.append(line)
        return "\n".join(lines)
