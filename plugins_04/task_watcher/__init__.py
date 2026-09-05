"""TaskWatcher Plugin — мониторинг task-событий.

Функции:
  - Timeline: логирование task-событий в EventStore + Pulse feed
  - Notify: уведомления в Telegram, Pulse, лог-файл
  - Metrics: duration, success_rate, counts by type
  - Automation: escalate при failed, notify при completed

Подписка: task.created, task.started, task.completed, task.failed
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts_01.plugin_api import BasePlugin, PluginMeta, PluginResult

from plugins_04.task_watcher.automation import TaskAutomation
from plugins_04.task_watcher.metrics import TaskMetrics
from plugins_04.task_watcher.notifier import Notifier
from plugins_04.task_watcher.timeline_logger import TimelineLogger


class TaskWatcherPlugin(BasePlugin):
    """Event plugin для мониторинга task-событий.

    Оркестрирует 4 модуля:
    - TimelineLogger: запись в EventStore + Pulse
    - Notifier: TG + pulse + log file
    - TaskMetrics: метрики задач
    - TaskAutomation: авто-действия
    """

    def __init__(
        self,
        event_store: Any = None,
        send_fn: Optional[Callable[[str], Any]] = None,
        log_dir: Optional[Path] = None,
    ):
        super().__init__(
            name="task_watcher",
            version="1.0.0",
            description="Task monitoring: timeline, notifications, metrics, automation",
        )
        self._event_store = event_store
        self._send_fn = send_fn

        # Модули
        self._timeline = TimelineLogger(event_store=event_store)
        self._notifier = Notifier(send_fn=send_fn, log_dir=log_dir)
        self._metrics = TaskMetrics()
        self._automation = TaskAutomation()

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            events_subscribed=self.events_subscribed,
        )

    @property
    def events_subscribed(self) -> List[str]:
        return [
            "task.created",
            "task.started",
            "task.completed",
            "task.failed",
        ]

    # ── Lifecycle ────────────────────────────────────────────

    def on_load(self) -> None:
        print(f"👁️ task_watcher: loaded (store={self._event_store is not None})")

    def on_unload(self) -> None:
        self._timeline.clear_log()
        self._metrics.reset()

    def on_event(self, event: Any) -> None:
        """Обработчик task-событий — оркестрирует все 4 модуля."""
        event_type = getattr(event, "type", "")
        event_data = getattr(event, "data", {}) or {}
        event_id = getattr(event, "id", "")
        correlation_id = getattr(event, "metadata", {}).get("correlation_id", "")
        session_id = getattr(event, "metadata", {}).get("session_id", "")
        project = getattr(event, "metadata", {}).get("project", "")
        user = getattr(event, "metadata", {}).get("user", "")
        timestamp = getattr(event, "timestamp", "")

        # 1. Timeline Logger
        stored_id = self._timeline.log_event(
            event_type=event_type,
            data=event_data,
            source="task_watcher",
            correlation_id=correlation_id,
            session_id=session_id,
            project=project,
            user=user,
        )

        # 2. Metrics
        self._metrics.record_event(
            event_type=event_type,
            data=event_data,
            timestamp=timestamp,
        )

        # 3. Pulse Entry
        pulse_entry = self._timeline.to_pulse_entry(
            event_type=event_type,
            data=event_data,
            event_id=stored_id or event_id,
        )

        # 4. Notifier
        self._notifier.notify(pulse_entry=pulse_entry, data=event_data)

        # 5. Automation
        self._automation.process_event(
            event_type=event_type,
            data=event_data,
            notify_fn=self._send_fn,
        )

    # ── Действия (CLI integration) ──────────────────────────

    def do_status(self) -> Dict[str, Any]:
        """Статус плагина."""
        return {
            "success": True,
            "data_13": {
                "name": self._name,
                "enabled": self._enabled,
                "metrics": self._metrics.get_summary(),
                "notifications": self._notifier.get_stats(),
                "automation": self._automation.get_stats(),
                "timeline_events": len(self._timeline.get_log()),
            },
        }

    def do_metrics(self) -> Dict[str, Any]:
        """Метрики задач."""
        return {
            "success": True,
            "data_13": self._metrics.get_summary(),
        }

    def do_top_tasks(self, limit: int = 10) -> Dict[str, Any]:
        """Топ задач по длительности."""
        return {
            "success": True,
            "data_13": self._metrics.get_top_tasks(limit=limit),
        }

    def do_pulse(self, limit: int = 20) -> Dict[str, Any]:
        """Pulse feed — лента событий."""
        feed = self._notifier.get_pulse_feed(limit=limit)
        return {
            "success": True,
            "data_13": [
                {
                    "icon": e.icon,
                    "title": e.title,
                    "description": e.description,
                    "severity": e.severity,
                    "timestamp": e.timestamp,
                }
                for e in feed
            ],
        }

    def do_automation_log(self, limit: int = 20) -> Dict[str, Any]:
        """Лог автоматизации."""
        return {
            "success": True,
            "data_13": self._automation.get_actions_log(limit=limit),
        }

    def do_rules(self) -> Dict[str, Any]:
        """Список правил автоматизации."""
        return {
            "success": True,
            "data_13": self._automation.get_rules(),
        }


# Экземпляр плагина (обнаруживается PluginLoader по переменной `plugin`)
plugin = TaskWatcherPlugin()
