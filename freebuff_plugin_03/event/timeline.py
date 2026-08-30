"""
Timeline Engine — временная шкала изменений проекта.

Основание: docs_10/core/EVENT_PLATFORM_SPECIFICATION.md §5
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from freebuff_plugin_03.event import (
    EventEntry,
    EventQuery,
    Timeline,
    TimelineEntry,
    get_event_icon,
)


class TimelineEngine:
    """Временная шкала проекта.

    Агрегирует события из Event Store в хронологическом порядке
    с форматированием для показа пользователю.
    """

    def __init__(self, store: Any):
        self._store = store

    def get_timeline(
        self,
        project: str = "",
        limit: int = 50,
        event_types: Optional[List[str]] = None,
    ) -> Timeline:
        """Получить временную шкалу."""
        query = EventQuery(
            project=project or None,
            limit=limit,
            order="desc",
        )
        entries = self._store.query(query)

        # Фильтр по типам (на уровне приложения для гибкости)
        if event_types:
            entries = [
                e for e in entries
                if any(e.event_type.startswith(et) for et in event_types)
            ]

        return Timeline(
            entries=[self._format_entry(e) for e in entries],
            total=len(entries),
            project=project,
        )

    def get_timeline_by_session(self, session_id: str) -> Timeline:
        """Шкала для конкретной сессии."""
        entries = self._store.get_by_session_id(session_id)
        return Timeline(
            entries=[self._format_entry(e) for e in entries],
            total=len(entries),
        )

    def get_timeline_by_user(
        self, user_id: str, limit: int = 50
    ) -> Timeline:
        """Шкала действий пользователя."""
        query = EventQuery(user_id=user_id, limit=limit, order="desc")
        entries = self._store.query(query)
        return Timeline(
            entries=[self._format_entry(e) for e in entries],
            total=len(entries),
        )

    def search_timeline(
        self,
        query_str: str,
        project: str = "",
        limit: int = 50,
    ) -> Timeline:
        """Поиск по временной шкале."""
        query = EventQuery(
            data_search=query_str,
            project=project or None,
            limit=limit,
            order="desc",
        )
        entries = self._store.query(query)
        return Timeline(
            entries=[self._format_entry(e) for e in entries],
            total=len(entries),
            project=project,
        )

    # ══════════════════════════════════════════════════════════
    # Formatting
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _format_entry(event: EventEntry) -> TimelineEntry:
        """Форматирует EventEntry в TimelineEntry для показа пользователю."""
        icon = get_event_icon(event.event_type)
        title = _default_title(event)
        description = _default_description(event)

        return TimelineEntry(
            timestamp=event.timestamp[:19],  # Обрезаем до секунд
            event_type=event.event_type,
            icon=icon,
            title=title,
            description=description,
            data=event.data,
            correlation_id=event.correlation_id,
            session_id=event.session_id,
        )

    def format_timeline_text(self, timeline: Timeline) -> str:
        """Форматирует Timeline в текст для CLI/UI."""
        lines = []
        for entry in timeline.entries:
            time_str = entry.timestamp[11:19]  # HH:MM:SS
            lines.append(
                f"{entry.icon} {time_str} — {entry.title}"
            )
            if entry.description:
                lines.append(f"   {entry.description}")

        if not lines:
            lines.append("📭 Нет событий в временной шкале.")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Default Formatters
# ═══════════════════════════════════════════════════════════════


def _default_title(event: EventEntry) -> str:
    """Формирует заголовок по типу события."""
    titles = {
        "system.startup": "System startup",
        "system.shutdown": "System shutdown",
        "system.error": f"System error: {event.data.get('error', 'unknown')}",
        "session.created": f"Session started: {event.data.get('topic', '')}",
        "session.completed": "Session completed",
        "session.checkpoint": f"Checkpoint: {event.data.get('summary', '')[:50]}",
        "task.created": f"Task created: {event.data.get('task_id', '')}",
        "task.completed": f"Task completed: {event.data.get('task_id', '')}",
        "task.failed": f"Task failed: {event.data.get('task_id', '')}",
        "step.started": f"Step started: {event.data.get('step_id', '')}",
        "step.completed": f"Step completed: {event.data.get('step_id', '')}",
        "step.failed": f"Step failed: {event.data.get('step_id', '')}",
        "memory.stored": f"Memory stored: {event.data.get('key', '')}",
        "memory.deleted": f"Memory deleted: {event.data.get('key', '')}",
        "knowledge.indexed": f"Knowledge indexed: {event.data.get('doc_id', '')[:30]}",
        "knowledge.searched": f"Search: {event.data.get('query', '')[:30]}",
        "mcp.server.initialized": f"MCP server: {event.data.get('name', '')}",
        "mcp.tool.called": f"MCP tool: {event.data.get('tool', '')}",
        "bridge.connected": f"Bridge connected: {event.data.get('server', '')}",
        "policy.evaluated": f"Policy: {event.data.get('policy_name', '')}",
        "audit.decision": f"Decision: {event.data.get('capability', '')} → {event.data.get('runtime_selected', '')}",
        "audit.action": f"Action: {event.data.get('actor', '')} → {event.data.get('action', '')}",
        "audit.config_change": f"Config: {event.data.get('setting', '')} changed",
        "checkpoint.created": f"Checkpoint: {event.data.get('summary', '')[:50]}",
    }

    title = titles.get(event.event_type)
    if title:
        return title

    # Wildcard fallback
    parts = event.event_type.split(".")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1]}: {event.event_type}"

    return f"Event: {event.event_type}"


def _default_description(event: EventEntry) -> str:
    """Формирует описание по данным события."""
    data = event.data
    if not data:
        return ""

    desc_fields = {
        "task.completed": f"Duration: {data.get('duration_ms', '?')}ms",
        "step.completed": f"Duration: {data.get('duration_ms', '?')}ms",
        "step.failed": f"Error: {data.get('error', 'unknown')}",
        "memory.stored": f"Level: {data.get('level', '?')}",
        "audit.decision": f"Policy: {data.get('policy_name', '?')}, Cost: ${data.get('cost_estimate', 0):.2f}",
        "audit.action": f"Target: {data.get('target', '?')}",
    }

    return desc_fields.get(event.event_type, "")
