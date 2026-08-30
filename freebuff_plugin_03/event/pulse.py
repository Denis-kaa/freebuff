"""
Project Pulse — лента событий в реальном времени для пользователя.

Основание: docs_10/core/EVENT_PLATFORM_SPECIFICATION.md §7
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from freebuff_plugin_03.event import (
    EventEntry,
    EventQuery,
    PulseEntry,
    get_event_icon,
)


class PulseEngine:
    """Project Pulse — лента событий пользователя.

    Подписывается на EventBus, форматирует события и сохраняет
    в EventStore для последующего показа.

    Использование:
        pulse = PulseEngine(bus, store)
        pulse.start()
        feed = pulse.get_pulse(limit=10)
    """

    def __init__(self, bus: Any, store: Any):
        self._bus = bus
        self._store = store
        self._subscription = None
        self._handler: Optional[Callable] = None
        self._running = False

        # Категории для фильтрации
        self._pulse_categories = [
            "task.",
            "step.",
            "session.",
            "memory.",
            "knowledge.",
            "checkpoint.",
            "audit.",
            "bridge.",
            "mcp.",
        ]

    def start(self, custom_handler: Optional[Callable] = None) -> None:
        """Подписаться на события и начать формировать Pulse.

        Args:
            custom_handler: кастомный обработчик вместо _on_event
        """
        if self._running:
            return

        self._handler = custom_handler or self._on_event

        if self._bus:
            self._subscription = self._bus.subscribe("*", self._handler)
            self._running = True

    def stop(self) -> None:
        """Отписаться от событий."""
        if self._running and self._bus and self._subscription:
            self._bus.unsubscribe(self._subscription)
        self._running = False
        self._subscription = None

    def _on_event(self, event: Any) -> None:
        """Обработать событие: отформатировать и сохранить в Pulse.

        Сохраняет только события из pulse_categories.
        """
        if not hasattr(event, "type"):
            return

        event_type = event.type

        # Фильтр: только релевантные категории
        if not any(event_type.startswith(cat) for cat in self._pulse_categories):
            return

        # Сохраняем как pulse событие с метаданными
        metadata = dict(getattr(event, "metadata", {}))
        metadata["pulse"] = "true"

        # Добавляем маркер _pulse в data, чтобы FTS5 мог найти событие
        data = dict(getattr(event, "data", {}))
        data["_pulse"] = True

        self._store.store(
            event_type=event_type,
            source=getattr(event, "source", "pulse"),
            data=data,
            correlation_id=metadata.get("correlation_id", ""),
            session_id=metadata.get("session_id", ""),
            metadata=metadata,
            event_id=getattr(event, "id", None),
            timestamp=getattr(event, "timestamp", None),
        )

    def get_pulse(
        self,
        project: str = "",
        limit: int = 20,
        event_types: Optional[List[str]] = None,
    ) -> List[PulseEntry]:
        """Получить ленту Pulse.

        Args:
            project: фильтр по проекту
            limit: максимальное количество записей
            event_types: фильтр по типам событий

        Returns:
            список PulseEntry отформатированных для UI
        """
        query = EventQuery(
            project=project or None,
            limit=limit,
            order="desc",
            data_search="pulse",  # Ищем pulse события (через FTS5)
        )
        entries = self._store.query(query)

        # Если FTS5 не сработал — fallback: ищем по категориям
        if not entries:
            for cat in self._pulse_categories:
                cat_entries = self._store.query(
                    EventQuery(
                        event_type=cat.rstrip(".") + ".*",
                        limit=limit // len(self._pulse_categories) + 1,
                        order="desc",
                    )
                )
                entries.extend(cat_entries)
            # Сортируем по времени и ограничиваем
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            entries = entries[:limit]

        # Применяем фильтр по event_types
        if event_types:
            entries = [
                e for e in entries
                if any(e.event_type.startswith(et) for et in event_types)
            ]

        return [self._format_pulse_entry(e) for e in entries]

    @staticmethod
    def _format_pulse_entry(event: EventEntry) -> PulseEntry:
        """Форматирует EventEntry в PulseEntry для UI."""
        icon = get_event_icon(event.event_type)

        # Определяем severity по типу события
        severity = "info"
        if "error" in event.event_type or "failed" in event.event_type:
            severity = "error"
        elif "warning" in event.event_type:
            severity = "warning"
        elif "completed" in event.event_type or "stored" in event.event_type:
            severity = "success"

        # Формируем заголовок
        title = _pulse_title(event)
        description = _pulse_description(event)

        return PulseEntry(
            icon=icon,
            title=title,
            description=description,
            timestamp=event.timestamp[:19],
            severity=severity,
        )


# ═══════════════════════════════════════════════════════════════
# Pulse Formatters
# ═══════════════════════════════════════════════════════════════


def _pulse_title(event: EventEntry) -> str:
    """Формирует заголовок для Pulse."""
    data = event.data

    if event.event_type.startswith("task."):
        task_id = data.get("task_id", "")
        if event.event_type == "task.created":
            return f"Task started: {task_id}"
        elif event.event_type == "task.completed":
            return f"Task done: {task_id}"
        elif event.event_type == "task.failed":
            return f"Task failed: {task_id}"
        return f"Task: {task_id}"

    if event.event_type.startswith("step."):
        step_id = data.get("step_id", "")
        return f"Step: {step_id}"

    if event.event_type.startswith("session."):
        topic = data.get("topic", data.get("summary", ""))
        if event.event_type == "session.created":
            return f"Session: {topic}"
        return f"Session: {topic[:40]}"

    if event.event_type.startswith("memory."):
        key = data.get("key", "")
        level = data.get("level", "")
        return f"Memory ({level}): {key[:30]}"

    if event.event_type.startswith("knowledge."):
        doc_id = data.get("doc_id", "")[:30]
        return f"Knowledge: {doc_id}"

    if event.event_type.startswith("checkpoint"):
        summary = data.get("summary", "")[:40]
        return f"Checkpoint: {summary}"

    if event.event_type.startswith("audit."):
        if event.event_type == "audit.decision":
            return f"Decision: {data.get('capability', '?')} → {data.get('runtime_selected', '?')}"
        return f"Audit: {event.event_type}"

    if event.event_type.startswith("bridge."):
        server = data.get("server", "")
        return f"Bridge: {server}"

    if event.event_type.startswith("mcp."):
        tool = data.get("tool", "")
        return f"MCP: {tool}"

    return f"Event: {event.event_type}"


def _pulse_description(event: EventEntry) -> str:
    """Формирует описание для Pulse."""
    data = event.data

    if event.event_type == "task.completed":
        duration = data.get("duration_ms", "")
        if duration:
            return f"Completed in {duration}ms"
        return ""

    if event.event_type == "step.started":
        return data.get("description", "")

    if event.event_type == "audit.decision":
        return f"Policy: {data.get('policy_name', '?')}, Cost: ${data.get('cost_estimate', 0):.2f}"

    return ""
