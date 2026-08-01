"""Tests for scripts_01/notification.py."""

from __future__ import annotations

import os
import tempfile
***REMOVED***
from unittest import mock

import pytest

# Ensure no real notifications fire during tests.
os.environ["FREEBUFF_NO_NOTIFY"***REMOVED*** = "1"

from scripts_01.event_bus import Event, EventBus
from scripts_01.notification import (
    NotificationConfig,
    NotificationManager,
    ProgressTracker,
    register_notification_subscribers,
    notify,
)


@pytest.fixture(autouse=True)
def _clear_no_notify_env():
    """Unset FREEBUFF_NO_NOTIFY so notification functions execute normally.

    Tests explicitly mock the underlying channels.
    """
    original = os.environ.pop("FREEBUFF_NO_NOTIFY", None)
    yield
    if original is not None:
        os.environ["FREEBUFF_NO_NOTIFY"***REMOVED*** = original
    else:
        os.environ.pop("FREEBUFF_NO_NOTIFY", None)


@pytest.fixture
def bus(tmp_path: Path) -> EventBus:
    """Fresh EventBus backed by a temporary database."""
    return EventBus(db_path=tmp_path / "events.db")


class TestNotificationManager:
    """Tests for NotificationManager EventBus integration."""

    def test_register_subscribes_to_all_events(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        assert len(manager._subscriptions) == 15

    def test_task_started_sends_notification(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("task.started", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            mock_notify.assert_called_once()
            assert "Test task" in mock_notify.call_args[1***REMOVED***["content"***REMOVED***

    def test_task_completed_sends_completion_notification(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify_task_complete") as mock_complete:
            bus.publish(Event("task.completed", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            mock_complete.assert_called_once()
            assert mock_complete.call_args[1***REMOVED***["task_name"***REMOVED*** == "Test task"

    def test_task_failed_sends_error_notification(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify_error") as mock_error:
            bus.publish(Event("task.failed", {"task_id": "t1", "task_name": "Test task", "error": "boom"***REMOVED***))
            mock_error.assert_called_once()
            assert mock_error.call_args[1***REMOVED***["error"***REMOVED*** == "boom"

    def test_quiet_mode_suppresses_start_and_progress(self, bus: EventBus) -> None:
        config = NotificationConfig(quiet=True)
        manager = NotificationManager(config=config)
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("task.started", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            bus.publish(Event("task.progress", {"task_id": "t1", "task_name": "Test task", "percent": 50***REMOVED***))
            mock_notify.assert_not_called()

    def test_completion_only_suppresses_start(self, bus: EventBus) -> None:
        config = NotificationConfig(completion_only=True)
        manager = NotificationManager(config=config)
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify, \
             mock.patch("scripts_01.notification.notify_task_complete") as mock_complete:
            bus.publish(Event("task.started", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            mock_notify.assert_not_called()
            bus.publish(Event("task.completed", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            mock_complete.assert_called_once()

    def test_progress_rate_limiting(self, bus: EventBus) -> None:
        config = NotificationConfig(progress_interval_seconds=0.5)
        manager = NotificationManager(config=config)
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("task.progress", {"task_id": "t1", "task_name": "Test task", "percent": 10***REMOVED***))
            bus.publish(Event("task.progress", {"task_id": "t1", "task_name": "Test task", "percent": 20***REMOVED***))
            # Two events for same task within interval should result in one notification.
            assert mock_notify.call_count == 1

        # After a different task, a new notification should be allowed.
        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("task.progress", {"task_id": "t2", "task_name": "Other task", "percent": 10***REMOVED***))
            assert mock_notify.call_count == 1

    def test_workflow_progress_calculates_percent(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("workflow.progress", {"workflow_id": "wf1", "completed_steps": 2, "total_steps": 4***REMOVED***))
            assert mock_notify.call_count == 1
            assert "50%" in mock_notify.call_args[1***REMOVED***["content"***REMOVED***

    def test_disabled_manager_does_nothing(self, bus: EventBus) -> None:
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config=config)
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("task.started", {"task_id": "t1", "task_name": "Test task"***REMOVED***))
            mock_notify.assert_not_called()

    def test_step_started_and_completed_do_not_notify(self, bus: EventBus) -> None:
        manager = NotificationManager()
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("step.started", {"step_id": "s1", "step_name": "Step 1"***REMOVED***))
            bus.publish(Event("step.completed", {"step_id": "s1", "step_name": "Step 1"***REMOVED***))
            mock_notify.assert_not_called()

    def test_step_retrying_is_rate_limited(self, bus: EventBus) -> None:
        config = NotificationConfig(progress_interval_seconds=0.5)
        manager = NotificationManager(config=config)
        manager.register(bus)

        with mock.patch("scripts_01.notification.notify") as mock_notify:
            bus.publish(Event("step.retrying", {"step_id": "s1", "step_name": "Step 1", "retry_count": 1, "max_retries": 3***REMOVED***))
            bus.publish(Event("step.retrying", {"step_id": "s1", "step_name": "Step 1", "retry_count": 2, "max_retries": 3***REMOVED***))
            assert mock_notify.call_count == 1

    def test_env_vars_configure_notification_config(self, bus: EventBus) -> None:
        import scripts_01.notification as notification_module

        with mock.patch.dict(os.environ, {
            "FREEBUFF_NOTIFY_QUIET": "1",
            "FREEBUFF_NOTIFY_PROGRESS_INTERVAL": "10",
        ***REMOVED***, clear=False):
            config = notification_module.NotificationConfig.from_env()
            assert config.quiet is True
            assert config.progress_interval_seconds == 10.0

    def test_invalid_progress_interval_env_falls_back_to_default(self, bus: EventBus) -> None:
        import scripts_01.notification as notification_module

        with mock.patch.dict(os.environ, {
            "FREEBUFF_NOTIFY_PROGRESS_INTERVAL": "not-a-number",
        ***REMOVED***, clear=False):
            config = notification_module.NotificationConfig.from_env()
            assert config.progress_interval_seconds == 30.0


class TestProgressTracker:
    """Tests for ProgressTracker helper."""

    def test_tracker_emits_task_started_and_completed(self, bus: EventBus) -> None:
        tracker = ProgressTracker("Test task", event_bus=bus, task_id="t1")
        tracker.start()
        tracker.complete(status="Успешно", details="done")

        events = bus.get_events(event_type="task.started", limit=10)
        assert len(events) == 1
        assert "Test task" in events[0***REMOVED***.data_json

        events = bus.get_events(event_type="task.completed", limit=10)
        assert len(events) == 1
        data = events[0***REMOVED***.data_json
        assert "Успешно" in data

    def test_tracker_emits_stage_changed(self, bus: EventBus) -> None:
        tracker = ProgressTracker("Test task", event_bus=bus, task_id="t1")
        tracker.set_stage("Analysis")

        events = bus.get_events(event_type="task.stage_changed", limit=10)
        assert len(events) == 1
        assert "Analysis" in events[0***REMOVED***.data_json

    def test_tracker_emits_progress(self, bus: EventBus) -> None:
        tracker = ProgressTracker("Test task", event_bus=bus, task_id="t1")
        tracker.update_progress(42, "almost there")

        events = bus.get_events(event_type="task.progress", limit=10)
        assert len(events) == 1
        data = events[0***REMOVED***.data_json
        assert "42" in data
        assert "almost there" in data

    def test_tracker_emits_failure(self, bus: EventBus) -> None:
        tracker = ProgressTracker("Test task", event_bus=bus, task_id="t1")
        tracker.fail("something went wrong", stage="execution")

        events = bus.get_events(event_type="task.failed", limit=10)
        assert len(events) == 1
        data = events[0***REMOVED***.data_json
        assert "something went wrong" in data

    def test_tracker_context_manager(self, bus: EventBus) -> None:
        with ProgressTracker("CM task", event_bus=bus, task_id="cm1") as tracker:
            tracker.update_progress(50)

        events = bus.get_events(event_type="task.completed", limit=10)
        assert len(events) == 1
        assert "CM task" in events[0***REMOVED***.data_json

    def test_tracker_context_manager_fails_on_exception(self, bus: EventBus) -> None:
        try:
            with ProgressTracker("CM task", event_bus=bus, task_id="cm1") as tracker:
                tracker.update_progress(50)
                raise ValueError("oops")
        except ValueError:
            pass

        events = bus.get_events(event_type="task.failed", limit=10)
        assert len(events) == 1
        assert "oops" in events[0***REMOVED***.data_json

    def test_tracker_no_event_bus_is_noop(self) -> None:
        tracker = ProgressTracker("No bus task", event_bus=None, task_id="nb1")
        tracker.start()
        tracker.update_progress(50)
        tracker.complete()
        # No exception and no events emitted (event_bus is None)
        assert tracker.event_bus is None


class TestRegisterNotificationSubscribers:
    """Tests for the public registration helper."""

    def test_register_helper_returns_manager(self, bus: EventBus) -> None:
        manager = register_notification_subscribers(bus)
        assert isinstance(manager, NotificationManager)
        assert len(manager._subscriptions) == 15


class TestLegacyNotify:
    """Tests for the original notify() fallback behavior."""

    def test_notify_returns_true_when_suppressed(self, bus: EventBus) -> None:
        os.environ["FREEBUFF_NO_NOTIFY"***REMOVED*** = "1"
        assert notify("title", "body") is True

    def test_notify_logs_when_no_termux(self, bus: EventBus) -> None:
        os.environ.pop("FREEBUFF_NO_NOTIFY", None)
        with mock.patch("scripts_01.notification.is_available", return_value=False), \
             mock.patch("scripts_01.notification._try_toast_channel", return_value=False), \
             mock.patch("scripts_01.notification._try_log_channel", return_value=True) as mock_log:
            assert notify("title", "body") is True
            mock_log.assert_called_once()
