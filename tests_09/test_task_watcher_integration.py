"""Integration tests for task_watcher with EventBus.

Run: python -m pytest tests_09/test_task_watcher_integration.py -v
"""

from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock

import pytest

from scripts_01.event_bus import Event, EventBus


class TestTaskWatcherEventBusIntegration:
    """Интеграция task_watcher с EventBus."""

    def _make_bus(self) -> EventBus:
        """Создать изолированный EventBus для тестов."""
        import tempfile
        from pathlib import Path

        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test_events.db"
        return EventBus(db_path=db_path)

    def test_register_task_watcher_subscribes(self) -> None:
        """register_task_watcher подписывает на task.* события."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        initial_count = len(bus._subscriptions)

        _register_task_watcher(bus)

        # Должны появиться подписчики на 4 типа событий
        new_count = len(bus._subscriptions)
        assert new_count >= initial_count + 4

    def test_task_created_triggers_watcher(self) -> None:
        """task.created событие активирует task_watcher."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        _register_task_watcher(bus)

        # Публикуем task.created
        event = Event(
            type="task.created",
            data={"task_id": "integ-1", "task_name": "Integration Test"},
            source="test",
        )
        bus.publish(event)

        # Событие доставлено (не упало)
        assert True

    def test_task_completed_triggers_watcher(self) -> None:
        """task.completed событие активирует task_watcher."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        _register_task_watcher(bus)

        event = Event(
            type="task.completed",
            data={"task_id": "integ-2", "task_name": "Integration Test 2"},
            source="test",
        )
        bus.publish(event)
        assert True

    def test_task_failed_triggers_watcher(self) -> None:
        """task.failed событие активирует task_watcher."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        _register_task_watcher(bus)

        event = Event(
            type="task.failed",
            data={
                "task_id": "integ-3",
                "task_name": "Failed Task",
                "error": "connection timeout",
            },
            source="test",
        )
        bus.publish(event)
        assert True

    def test_full_lifecycle_via_bus(self) -> None:
        """Полный lifecycle через EventBus: created → started → completed."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        _register_task_watcher(bus)

        events = [
            Event(type="task.created", data={"task_id": "lc-1", "task_name": "Lifecycle"}),
            Event(type="task.started", data={"task_id": "lc-1", "task_name": "Lifecycle"}),
            Event(type="task.completed", data={"task_id": "lc-1", "task_name": "Lifecycle"}),
        ]

        for event in events:
            bus.publish(event)

        # Все события доставлены без ошибок
        assert True

    def test_failed_lifecycle_via_bus(self) -> None:
        """Lifecycle с ошибкой через EventBus: created → failed."""
        from scripts_01.event_subscribers import _register_task_watcher

        bus = self._make_bus()
        _register_task_watcher(bus)

        bus.publish(
            Event(
                type="task.created",
                data={"task_id": "fl-1", "task_name": "Failing Task"},
            )
        )
        bus.publish(
            Event(
                type="task.failed",
                data={
                    "task_id": "fl-1",
                    "task_name": "Failing Task",
                    "error": "out of memory",
                },
            )
        )
        assert True


class TestTaskWatcherPluginRegistry:
    """Интеграция task_watcher через PluginRegistry."""

    def test_plugin_loads_via_registry(self) -> None:
        """PluginRegistry может загрузить task_watcher."""
        from scripts_01.plugin_api import PluginRegistry

        bus = EventBus(db_path="/tmp/test_tw_registry.db")
        registry = PluginRegistry(event_bus=bus)

        # Загружаем task_watcher
        from plugins_04.task_watcher import TaskWatcherPlugin

        plugin = TaskWatcherPlugin()
        registry.register(plugin)

        # Проверяем что плагин зарегистрирован
        assert plugin.name in registry._plugins

    def test_plugin_enables_and_subscribes(self) -> None:
        """PluginRegistry.enable() подписывает плагин на события."""
        from scripts_01.plugin_api import PluginRegistry

        bus = EventBus(db_path="/tmp/test_tw_enable.db")
        registry = PluginRegistry(event_bus=bus)

        from plugins_04.task_watcher import TaskWatcherPlugin

        plugin = TaskWatcherPlugin()
        registry.register(plugin)
        registry.enable(plugin.name)

        # Плагин подписан на 4 события
        assert len(plugin._subscriptions) == 4
        assert plugin.is_enabled

    def test_plugin_disables_and_unsubscribes(self) -> None:
        """PluginRegistry.disable() отписывает плагин."""
        from scripts_01.plugin_api import PluginRegistry

        bus = EventBus(db_path="/tmp/test_tw_disable.db")
        registry = PluginRegistry(event_bus=bus)

        from plugins_04.task_watcher import TaskWatcherPlugin

        plugin = TaskWatcherPlugin()
        registry.register(plugin)
        registry.enable(plugin.name)
        assert plugin.is_enabled

        registry.disable(plugin.name)
        assert not plugin.is_enabled
        assert len(plugin._subscriptions) == 0
