"""Timeline Logger — записывает task-события в EventStore + Pulse feed.

Используется TaskWatcherPlugin для логирования всех task.* событий
в timeline проекта.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from plugins_04.event.types import EventEntry, PulseEntry

# ── Иконки для типов задач ──────────────────────────────────

TASK_EVENT_ICONS: Dict[str, str] = {
    "task.created": "📋",
    "task.started": "🚀",
    "task.completed": "✅",
    "task.failed": "❌",
}

TASK_SEVERITY: Dict[str, str] = {
    "task.created": "info",
    "task.started": "info",
    "task.completed": "success",
    "task.failed": "error",
}


class TimelineLogger:
    """Логирует task-события в EventStore и формирует PulseEntry."""

    def __init__(self, event_store: Any = None):
        """
        Args:
            event_store: экземпляр EventStore (plugins_04.event.store).
                         Если None — логирование в timeline отключено.
        """
        self._event_store = event_store
        self._log: list[Dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "task_watcher",
        correlation_id: str = "",
        session_id: str = "",
        project: str = "",
        user: str = "",
    ) -> Optional[str]:
        """Записать событие в EventStore и вернуть event_id.

        Args:
            event_type: тип события (task.created, task.started, task.completed, task.failed)
            data: данные события
            source: источник события
            correlation_id: ID цепочки событий
            session_id: ID сессии
            project: имя проекта
            user: пользователь

        Returns:
            event_id если записано, None если EventStore недоступен
        """
        now = datetime.now(timezone.utc).isoformat()

        # Локальный лог (всегда работает)
        entry = {
            "event_type": event_type,
            "data": data,
            "source": source,
            "timestamp": now,
        }
        self._log.append(entry)

        # В EventStore (если доступен)
        if self._event_store is not None:
            try:
                event_id = self._event_store.store(
                    event_type=event_type,
                    source=source,
                    data=data,
                    correlation_id=correlation_id,
                    session_id=session_id,
                    project=project,
                    user=user,
                    timestamp=now,
                )
                return event_id
            except Exception:
                pass

        return None

    def to_pulse_entry(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_id: str = "",
    ) -> PulseEntry:
        """Преобразовать task-событие в PulseEntry для ленты.

        Args:
            event_type: тип события
            data: данные события
            event_id: ID события

        Returns:
            PulseEntry готовый для отображения
        """
        icon = TASK_EVENT_ICONS.get(event_type, "📌")
        severity = TASK_SEVERITY.get(event_type, "info")
        now = datetime.now(timezone.utc).isoformat()

        task_name = data.get("task_name", data.get("name", "Unknown"))
        task_id = data.get("task_id", data.get("id", ""))

        title = f"{icon} {event_type.replace('task.', '').title()}: {task_name}"
        description = self._build_description(event_type, data)

        return PulseEntry(
            icon=icon,
            title=title,
            description=description,
            timestamp=now,
            severity=severity,
            event_type=event_type,
            event_id=event_id,
        )

    def get_log(self) -> list[Dict[str, Any]]:
        """Вернуть локальный лог событий."""
        return list(self._log)

    def clear_log(self) -> None:
        """Очистить локальный лог."""
        self._log.clear()

    # ── Приватные ────────────────────────────────────────────

    def _build_description(self, event_type: str, data: Dict[str, Any]) -> str:
        """Построить текстовое описание события."""
        task_id = data.get("task_id", data.get("id", ""))
        error = data.get("error", "")
        duration = data.get("duration_seconds", data.get("duration", ""))

        parts: list[str] = []
        if task_id:
            parts.append(f"ID: {task_id}")
        if duration:
            parts.append(f"Duration: {duration}s")
        if error:
            parts.append(f"Error: {error}")

        return " | ".join(parts) if parts else ""
