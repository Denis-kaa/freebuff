"""Tests for task_watcher plugin — Timeline Logger, Notifier, Metrics, Automation, Plugin.

Run: python -m pytest tests_09/test_task_watcher.py -v
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from plugins_04.task_watcher import TaskWatcherPlugin
from plugins_04.task_watcher.automation import AutomationRule, TaskAutomation
from plugins_04.task_watcher.metrics import TaskMetrics
from plugins_04.task_watcher.notifier import Notifier
from plugins_04.task_watcher.timeline_logger import (
    TASK_EVENT_ICONS,
    TASK_SEVERITY,
    TimelineLogger,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


@dataclass
class FakeEvent:
    """Поддельное событие для тестов."""

    type: str = ""
    data: Dict[str, Any] = None  # type: ignore[assignment]
    id: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}


def _make_task_event(
    event_type: str = "task.created",
    task_id: str = "task-001",
    task_name: str = "Test Task",
    error: str = "",
    **kwargs: Any,
) -> FakeEvent:
    """Создать поддельное task-событие."""
    data: Dict[str, Any] = {"task_id": task_id, "task_name": task_name, **kwargs}
    if error:
        data["error"] = error
    return FakeEvent(
        type=event_type,
        data=data,
        id=f"evt-{task_id}",
        timestamp="2026-08-27T12:00:00+00:00",
        metadata={"session_id": "sess-001", "project": "test"},
    )


# ═══════════════════════════════════════════════════════════════
# TimelineLogger Tests
# ═══════════════════════════════════════════════════════════════


class TestTimelineLogger:
    """Тесты TimelineLogger."""

    def test_log_event_without_store(self) -> None:
        """Логирование без EventStore — работает локально."""
        logger = TimelineLogger(event_store=None)
        event_id = logger.log_event(
            event_type="task.created",
            data={"task_id": "t1", "task_name": "Test"},
        )
        assert event_id is None
        log = logger.get_log()
        assert len(log) == 1
        assert log[0]["event_type"] == "task.created"

    def test_log_event_with_store(self) -> None:
        """Логирование с EventStore — сохраняет и возвращает event_id."""
        mock_store = MagicMock()
        mock_store.store.return_value = "abc123"
        logger = TimelineLogger(event_store=mock_store)
        event_id = logger.log_event(
            event_type="task.completed",
            data={"task_id": "t1"},
        )
        assert event_id == "abc123"
        mock_store.store.assert_called_once()

    def test_to_pulse_entry(self) -> None:
        """Преобразование в PulseEntry."""
        logger = TimelineLogger()
        entry = logger.to_pulse_entry(
            event_type="task.failed",
            data={"task_id": "t1", "task_name": "Deploy", "error": "timeout"},
            event_id="evt-001",
        )
        assert entry.icon == "❌"
        assert "Failed" in entry.title
        assert entry.severity == "error"
        assert "timeout" in entry.description

    def test_clear_log(self) -> None:
        """Очистка лога."""
        logger = TimelineLogger()
        logger.log_event("task.created", {"task_id": "t1"})
        assert len(logger.get_log()) == 1
        logger.clear_log()
        assert len(logger.get_log()) == 0

    def test_task_event_icons_coverage(self) -> None:
        """Все task-события имеют иконки."""
        expected = {"task.created", "task.started", "task.completed", "task.failed"}
        assert set(TASK_EVENT_ICONS.keys()) == expected

    def test_task_severity_coverage(self) -> None:
        """Все task-события имеют severity."""
        expected = {"task.created", "task.started", "task.completed", "task.failed"}
        assert set(TASK_SEVERITY.keys()) == expected


# ═══════════════════════════════════════════════════════════════
# Notifier Tests
# ═══════════════════════════════════════════════════════════════


class TestNotifier:
    """Тесты Notifier."""

    def test_notify_without_tg(self) -> None:
        """Уведомление без TG-функции — TG не отправляется."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = Notifier(send_fn=None, log_dir=Path(tmpdir))
            from plugins_04.event.types import PulseEntry

            entry = PulseEntry(
                title="Test", severity="info", event_type="task.created"
            )
            result = notifier.notify(entry)
            assert result["tg"] is False
            assert result["pulse"] is True
            assert result["log_file"] is True

    def test_notify_with_tg(self) -> None:
        """Уведомление с TG-функцией — отправляется."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_send = MagicMock()
            notifier = Notifier(send_fn=mock_send, log_dir=Path(tmpdir))
            from plugins_04.event.types import PulseEntry

            entry = PulseEntry(
                title="Test Task", severity="success", event_type="task.completed"
            )
            result = notifier.notify(entry)
            assert result["tg"] is True
            mock_send.assert_called_once()

    def test_pulse_feed(self) -> None:
        """Pulse feed накапливает записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = Notifier(log_dir=Path(tmpdir))
            from plugins_04.event.types import PulseEntry

            for i in range(5):
                entry = PulseEntry(title=f"Event {i}", event_type="task.created")
                notifier.notify(entry)

            feed = notifier.get_pulse_feed(limit=3)
            assert len(feed) == 3

    def test_log_file_written(self) -> None:
        """Лог-файл записывается."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = Notifier(log_dir=Path(tmpdir))
            from plugins_04.event.types import PulseEntry

            entry = PulseEntry(
                title="Test",
                event_type="task.failed",
                description="Error occurred",
            )
            notifier.notify(entry, data={"task_id": "t1"})

            log_file = Path(tmpdir) / "task_watcher.log"
            assert log_file.exists()
            content = log_file.read_text()
            assert "task.failed" in content

    def test_stats(self) -> None:
        """Статистика уведомлений."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notifier = Notifier(log_dir=Path(tmpdir))
            from plugins_04.event.types import PulseEntry

            entry = PulseEntry(title="Test", event_type="task.created")
            notifier.notify(entry)
            stats = notifier.get_stats()
            assert stats["total_notifications"] == 1
            assert stats["pulse_entries"] == 1


# ═══════════════════════════════════════════════════════════════
# Metrics Tests
# ═══════════════════════════════════════════════════════════════


class TestTaskMetrics:
    """Тесты TaskMetrics."""

    def test_record_created_then_completed(self) -> None:
        """Запись created → completed считает duration."""
        m = TaskMetrics()
        m.record_event(
            "task.created",
            {"task_id": "t1"},
            timestamp="2026-08-27T12:00:00+00:00",
        )
        m.record_event(
            "task.completed",
            {"task_id": "t1"},
            timestamp="2026-08-27T12:00:10+00:00",
        )
        task = m.get_task("t1")
        assert task is not None
        assert task["status"] == "completed"
        assert task["duration"] is not None
        assert task["duration"] > 0

    def test_record_created_then_failed(self) -> None:
        """Запись created → failed считает failed."""
        m = TaskMetrics()
        m.record_event("task.created", {"task_id": "t2"})
        m.record_event(
            "task.failed",
            {"task_id": "t2"},
            timestamp="2026-08-27T12:00:05+00:00",
        )
        task = m.get_task("t2")
        assert task is not None
        assert task["status"] == "failed"

    def test_summary(self) -> None:
        """Сводка метрик."""
        m = TaskMetrics()
        # 2 completed, 1 failed
        for i in range(2):
            m.record_event("task.created", {"task_id": f"c{i}"})
            m.record_event("task.completed", {"task_id": f"c{i}"})
        m.record_event("task.created", {"task_id": "f1"})
        m.record_event("task.failed", {"task_id": "f1"})

        summary = m.get_summary()
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == pytest.approx(0.6667, abs=0.01)

    def test_top_tasks(self) -> None:
        """Топ задач по длительности."""
        m = TaskMetrics()
        for i in range(3):
            m.record_event("task.created", {"task_id": f"t{i}"})
            m.record_event(
                "task.completed",
                {"task_id": f"t{i}"},
                timestamp=f"2026-08-27T12:00:{10 + i * 10:02d}+00:00",
            )
        top = m.get_top_tasks(limit=2)
        assert len(top) == 2
        # Самая долгая — первая
        assert top[0]["duration"] >= top[1]["duration"]

    def test_reset(self) -> None:
        """Сброс метрик."""
        m = TaskMetrics()
        m.record_event("task.created", {"task_id": "t1"})
        m.reset()
        summary = m.get_summary()
        assert summary["total_tasks"] == 0

    def test_no_task_id_ignored(self) -> None:
        """Событие без task_id игнорируется."""
        m = TaskMetrics()
        m.record_event("task.created", {"something": "else"})
        assert m.get_summary()["total_tasks"] == 0


# ═══════════════════════════════════════════════════════════════
# Automation Tests
# ═══════════════════════════════════════════════════════════════


class TestTaskAutomation:
    """Тесты TaskAutomation."""

    def test_default_rules(self) -> None:
        """Два правила по умолчанию."""
        auto = TaskAutomation()
        rules = auto.get_rules()
        assert len(rules) == 2
        actions = {r["action"] for r in rules}
        assert "escalate" in actions
        assert "notify_complete" in actions

    def test_escalate_on_failed(self) -> None:
        """Escalate при task.failed."""
        auto = TaskAutomation()
        mock_notify = MagicMock()
        result = auto.process_event(
            "task.failed",
            {"task_id": "t1", "task_name": "Deploy", "error": "timeout"},
            notify_fn=mock_notify,
        )
        assert len(result) == 1
        assert result[0]["action"] == "escalate"
        assert result[0]["success"] is True
        mock_notify.assert_called_once()
        msg = mock_notify.call_args[0][0]
        assert "ESCALATE" in msg
        assert "timeout" in msg

    def test_notify_on_completed(self) -> None:
        """Notify при task.completed."""
        auto = TaskAutomation()
        mock_notify = MagicMock()
        result = auto.process_event(
            "task.completed",
            {"task_id": "t1", "task_name": "Build"},
            notify_fn=mock_notify,
        )
        assert len(result) == 1
        assert result[0]["action"] == "notify_complete"
        mock_notify.assert_called_once()

    def test_no_action_on_created(self) -> None:
        """Нет действий при task.created."""
        auto = TaskAutomation()
        result = auto.process_event(
            "task.created", {"task_id": "t1"}
        )
        assert len(result) == 0

    def test_custom_rule(self) -> None:
        """Кастомное правило."""
        auto = TaskAutomation()
        handler = MagicMock()
        auto.add_rule(
            AutomationRule(
                event_type="task.started",
                action="custom_action",
                handler=handler,
            )
        )
        result = auto.process_event("task.started", {"task_id": "t1"})
        assert len(result) == 1
        assert result[0]["action"] == "custom_action"
        handler.assert_called_once()

    def test_wildcard_rule(self) -> None:
        """Wildcard правило task.*."""
        auto = TaskAutomation()
        handler = MagicMock()
        auto.add_rule(
            AutomationRule(
                event_type="task.*",
                action="watch_all",
                handler=handler,
            )
        )
        result = auto.process_event("task.created", {"task_id": "t1"})
        assert len(result) == 1

    def test_disabled_rule(self) -> None:
        """Отключенное правило не срабатывает."""
        auto = TaskAutomation()
        auto.add_rule(
            AutomationRule(
                event_type="task.failed",
                action="disabled_action",
                enabled=False,
            )
        )
        result = auto.process_event("task.failed", {"task_id": "t1"})
        # Дефолтный escalate всё равно сработает
        escalate_results = [r for r in result if r["action"] == "escalate"]
        assert len(escalate_results) == 1

    def test_actions_log(self) -> None:
        """Лог действий накапливается."""
        auto = TaskAutomation()
        auto.process_event("task.failed", {"task_id": "t1"})
        log = auto.get_actions_log()
        assert len(log) == 1

    def test_stats(self) -> None:
        """Статистика автоматизации."""
        auto = TaskAutomation()
        auto.process_event("task.failed", {"task_id": "t1"})
        auto.process_event("task.completed", {"task_id": "t2"})
        stats = auto.get_stats()
        assert stats["total_actions_executed"] == 2


# ═══════════════════════════════════════════════════════════════
# TaskWatcherPlugin Tests
# ═══════════════════════════════════════════════════════════════


class TestTaskWatcherPlugin:
    """Тесты полного TaskWatcherPlugin."""

    def test_events_subscribed(self) -> None:
        """Плагин подписан на 4 типа событий."""
        plugin = TaskWatcherPlugin()
        assert len(plugin.events_subscribed) == 4
        assert "task.created" in plugin.events_subscribed
        assert "task.failed" in plugin.events_subscribed

    def test_meta(self) -> None:
        """Метаданные плагина."""
        plugin = TaskWatcherPlugin()
        meta = plugin.meta
        assert meta.name == "task_watcher"
        assert meta.version == "1.0.0"

    def test_on_event_coordinates_modules(self) -> None:
        """on_event оркестрирует все 4 модуля."""
        plugin = TaskWatcherPlugin()
        event = _make_task_event("task.created")
        plugin.on_event(event)

        # Timeline получил событие
        log = plugin._timeline.get_log()
        assert len(log) == 1

        # Metrics обновились
        summary = plugin._metrics.get_summary()
        assert summary["counts_by_type"].get("task.created", 0) == 1

    def test_do_status(self) -> None:
        """Команда status."""
        plugin = TaskWatcherPlugin()
        event = _make_task_event("task.completed")
        plugin.on_event(event)

        result = plugin.do_status()
        assert result["success"] is True
        assert result["data_13"]["metrics"]["completed"] == 1

    def test_do_metrics(self) -> None:
        """Команда metrics."""
        plugin = TaskWatcherPlugin()
        plugin.on_event(_make_task_event("task.created", task_id="t1"))
        plugin.on_event(_make_task_event("task.completed", task_id="t1"))

        result = plugin.do_metrics()
        assert result["success"] is True
        assert result["data_13"]["completed"] == 1

    def test_do_pulse(self) -> None:
        """Команда pulse."""
        plugin = TaskWatcherPlugin()
        plugin.on_event(_make_task_event("task.created"))
        result = plugin.do_pulse()
        assert result["success"] is True
        assert len(result["data_13"]) == 1

    def test_do_automation_log(self) -> None:
        """Команда automation_log."""
        plugin = TaskWatcherPlugin()
        plugin.on_event(_make_task_event("task.failed"))
        result = plugin.do_automation_log()
        assert result["success"] is True
        assert len(result["data_13"]) >= 1

    def test_do_rules(self) -> None:
        """Команда rules."""
        plugin = TaskWatcherPlugin()
        result = plugin.do_rules()
        assert result["success"] is True
        assert len(result["data_13"]) == 2

    def test_full_lifecycle(self) -> None:
        """Полный lifecycle: created → started → completed."""
        plugin = TaskWatcherPlugin()

        plugin.on_event(_make_task_event("task.created", task_id="lifecycle-1"))
        plugin.on_event(_make_task_event("task.started", task_id="lifecycle-1"))
        plugin.on_event(_make_task_event("task.completed", task_id="lifecycle-1"))

        summary = plugin._metrics.get_summary()
        assert summary["total_tasks"] == 1
        assert summary["completed"] == 1
        assert summary["success_rate"] == 1.0

    def test_failed_lifecycle(self) -> None:
        """Lifecycle с ошибкой: created → started → failed."""
        plugin = TaskWatcherPlugin()

        plugin.on_event(_make_task_event("task.created", task_id="fail-1"))
        plugin.on_event(_make_task_event("task.started", task_id="fail-1"))
        plugin.on_event(
            _make_task_event(
                "task.failed", task_id="fail-1", error="connection timeout"
            )
        )

        summary = plugin._metrics.get_summary()
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.0
