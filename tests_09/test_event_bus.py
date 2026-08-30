#!/usr/bin/env python3
"""Tests for Event Bus (scripts_01/event_bus.py)."""

from __future__ import annotations

import json
import sys
import threading
import time
}
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.event_bus import (
    EventBus, Event, Subscription,
    EventLogEntry,
    task_event, step_event, memory_event, context_event,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def event_bus(tmp_path: Path) -> EventBus:
    """Создаёт EventBus с временной БД."""
    db_path = tmp_path / "events.db"
    return EventBus(db_path=db_path)


# ═══════════════════════════════════════════════════════════════
# Event
# ═══════════════════════════════════════════════════════════════

class TestEvent:
    def test_create_minimal(self):
        e = Event(type="test.event")
        assert e.type == "test.event"
        assert e.data == {}
        assert e.source == "system"
        assert e.id is not None
        assert len(e.id) == 12

    def test_create_full(self):
        e = Event(
            type="task.completed",
            data={"task_id": "wf1", "status": "ok"},
            source="orchestrator",
            metadata={"priority": "high"},
        )
        assert e.type == "task.completed"
        assert e.data["task_id"] == "wf1"
        assert e.source == "orchestrator"
        assert e.metadata["priority"] == "high"

    def test_unique_ids(self):
        ids = {Event(type="test").id for _ in range(100)}
        assert len(ids) == 100  # все уникальны

    def test_timestamp_format(self):
        e = Event(type="test")
        assert "T" in e.timestamp  # ISO format


# ═══════════════════════════════════════════════════════════════
# Publish / Subscribe
# ═══════════════════════════════════════════════════════════════

class TestPublishSubscribe:
    def test_publish_delivers_to_subscriber(self, event_bus: EventBus):
        received: List[Event] = []

        def handler(event: Event):
            received.append(event)

        event_bus.subscribe("test.event", handler)
        event = Event(type="test.event", data={"msg": "hello"})
        delivered = event_bus.publish(event)

        assert delivered == 1
        assert len(received) == 1
        assert received[0].type == "test.event"
        assert received[0].data["msg"] == "hello"

    def test_publish_no_subscribers(self, event_bus: EventBus):
        delivered = event_bus.publish(Event(type="lonely.event"))
        assert delivered == 0

    def test_multiple_subscribers(self, event_bus: EventBus):
        count = [0]

        def h1(e: Event):
            count[0] += 1

        def h2(e: Event):
            count[0] += 1

        event_bus.subscribe("multi.event", h1)
        event_bus.subscribe("multi.event", h2)
        delivered = event_bus.publish(Event(type="multi.event"))

        assert delivered == 2
        assert count[0] == 2

    def test_subscribe_multiple_types(self, event_bus: EventBus):
        events: List[str] = []

        def handler(e: Event):
            events.append(e.type)

        event_bus.subscribe("type.a", handler)
        event_bus.subscribe("type.b", handler)
        event_bus.publish(Event(type="type.a"))
        event_bus.publish(Event(type="type.b"))

        assert len(events) == 2
        assert "type.a" in events
        assert "type.b" in events

    def test_unsubscribe(self, event_bus: EventBus):
        received: List[Event] = []

        def handler(e: Event):
            received.append(e)

        sub = event_bus.subscribe("temp.event", handler)
        event_bus.publish(Event(type="temp.event"))
        assert len(received) == 1

        event_bus.unsubscribe(sub)
        event_bus.publish(Event(type="temp.event"))
        assert len(received) == 1  # не увеличилось

    def test_unsubscribe_nonexistent(self, event_bus: EventBus):
        sub = Subscription(id="fake", event_type="*", handler=lambda e: None)
        result = event_bus.unsubscribe(sub)
        assert result is False

    def test_handler_error_does_not_crash_bus(self, event_bus: EventBus):
        def bad_handler(e: Event):
            raise RuntimeError("KABOOM")

        event_bus.subscribe("danger.event", bad_handler)
        # Не должно падать
        delivered = event_bus.publish(Event(type="danger.event"))
        assert delivered == 0  # подписчик был, но упал


# ═══════════════════════════════════════════════════════════════
# Wildcard Matching
# ═══════════════════════════════════════════════════════════════

class TestWildcardMatching:
    def test_wildcard_star(self, event_bus: EventBus):
        received: List[str] = []

        def handler(e: Event):
            received.append(e.type)

        event_bus.subscribe("*", handler)
        event_bus.publish(Event(type="anything.here"))
        event_bus.publish(Event(type="task.completed"))

        assert len(received) == 2

    def test_wildcard_prefix(self, event_bus: EventBus):
        received: List[str] = []

        def handler(e: Event):
            received.append(e.type)

        event_bus.subscribe("task.*", handler)
        event_bus.publish(Event(type="task.completed"))
        event_bus.publish(Event(type="task.failed"))
        event_bus.publish(Event(type="memory.updated"))  # не должно поймать

        assert len(received) == 2
        assert "task.completed" in received
        assert "task.failed" in received

    def test_wildcard_and_exact(self, event_bus: EventBus):
        """Подписка на task.* + task.completed не дублирует доставку."""
        received: List[str] = []

        def h1(e: Event):
            received.append(f"wildcard:{e.type}")

        def h2(e: Event):
            received.append(f"exact:{e.type}")

        event_bus.subscribe("task.*", h1)
        event_bus.subscribe("task.completed", h2)
        event_bus.publish(Event(type="task.completed"))

        assert len(received) == 2


# ═══════════════════════════════════════════════════════════════
# Filter Functions
# ═══════════════════════════════════════════════════════════════

class TestFilterFunctions:
    def test_filter_accept(self, event_bus: EventBus):
        received: List[Event] = []

        def handler(e: Event):
            received.append(e)

        event_bus.subscribe(
            "task.*", handler,
            filter_fn=lambda e: e.data.get("priority") == "high",
        )
        event_bus.publish(Event(type="task.completed", data={"priority": "high"}))
        event_bus.publish(Event(type="task.completed", data={"priority": "low"}))

        assert len(received) == 1
        assert received[0].data["priority"] == "high"

    def test_filter_reject_all(self, event_bus: EventBus):
        received: List[Event] = []

        def handler(e: Event):
            received.append(e)

        event_bus.subscribe(
            "*", handler,
            filter_fn=lambda e: False,
        )
        event_bus.publish(Event(type="anything"))
        assert len(received) == 0


# ═══════════════════════════════════════════════════════════════
# Event Log (SQLite)
# ═══════════════════════════════════════════════════════════════

class TestEventLog:
    def test_event_logged(self, event_bus: EventBus):
        event = Event(type="test.logged", source="pytest")
        event_bus.publish(event)

        entries = event_bus.get_events()
        assert len(entries) >= 1
        logged = entries[0]
        assert logged.event_type == "test.logged"
        assert logged.source == "pytest"
        assert logged.delivered_to >= 0

    def test_get_events_by_type(self, event_bus: EventBus):
        event_bus.publish(Event(type="task.completed"))
        event_bus.publish(Event(type="memory.updated"))

        task_events = event_bus.get_events(event_type="task.completed")
        assert len(task_events) == 1
        assert task_events[0].event_type == "task.completed"

    def test_get_events_limit(self, event_bus: EventBus):
        for i in range(10):
            event_bus.publish(Event(type="bench.event"))
        entries = event_bus.get_events(limit=3)
        assert len(entries) == 3

    def test_get_events_empty(self, event_bus: EventBus):
        entries = event_bus.get_events()
        assert len(entries) == 0

    def test_log_survives_restart(self, tmp_path: Path):
        db_path = tmp_path / "persist.db"
        bus1 = EventBus(db_path=db_path)
        bus1.publish(Event(type="persisted.event"))
        bus1.publish(Event(type="another.event"))

        bus2 = EventBus(db_path=db_path)
        entries = bus2.get_events()
        assert len(entries) == 2


# ═══════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════

class TestStats:
    def test_stats_empty(self, event_bus: EventBus):
        stats = event_bus.get_stats()
        assert stats["total_events"] == 0
        assert stats["active_subscribers"] == 0

    def test_stats_with_events(self, event_bus: EventBus):
        event_bus.publish(Event(type="task.completed"))
        event_bus.publish(Event(type="task.failed"))
        event_bus.publish(Event(type="task.completed"))

        stats = event_bus.get_stats()
        assert stats["total_events"] == 3
        assert stats["event_types"]["task.completed"] == 2
        assert stats["event_types"]["task.failed"] == 1

    def test_stats_with_subscribers(self, event_bus: EventBus):
        event_bus.subscribe("task.*", lambda e: None)
        event_bus.subscribe("memory.*", lambda e: None)

        stats = event_bus.get_stats()
        assert stats["active_subscribers"] == 2


# ═══════════════════════════════════════════════════════════════
# Clear
# ═══════════════════════════════════════════════════════════════

class TestClear:
    def test_clear_log(self, event_bus: EventBus):
        event_bus.publish(Event(type="temp"))
        assert len(event_bus.get_events()) >= 1
        event_bus.clear()
        assert len(event_bus.get_events()) == 0

    def test_clear_subscribers(self, event_bus: EventBus):
        received: List[Event] = []

        def handler(e: Event):
            received.append(e)

        event_bus.subscribe("test", handler)
        event_bus.clear()
        event_bus.publish(Event(type="test"))
        assert len(received) == 0


# ═══════════════════════════════════════════════════════════════
# Thread Safety
# ═══════════════════════════════════════════════════════════════

class TestThreadSafety:
    def test_parallel_publishes(self, event_bus: EventBus):
        """Множественные публикации из разных потоков."""
        count = [0]

        def handler(e: Event):
            count[0] += 1

        event_bus.subscribe("thread.*", handler)

        def publisher():
            for _ in range(50):
                event_bus.publish(Event(type="thread.test"))

        threads = [threading.Thread(target=publisher) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert count[0] == 250

    def test_subscribe_during_publish(self, event_bus: EventBus):
        """Подписка во время публикации не ломает шину."""
        def late_subscriber(e: Event):
            if e.type == "trigger":
                event_bus.subscribe("late.event", lambda x: None)

        event_bus.subscribe("trigger", late_subscriber)
        event_bus.publish(Event(type="trigger"))  # не должно упасть


# ═══════════════════════════════════════════════════════════════
# Factory Functions
# ═══════════════════════════════════════════════════════════════

class TestFactories:
    def test_task_event(self):
        e = task_event("completed", "wf1", status="ok")
        assert e.type == "task.completed"
        assert e.source == "orchestrator"
        assert e.data["task_id"] == "wf1"
        assert e.data["status"] == "ok"

    def test_step_event(self):
        e = step_event("started", "s1", "wf1", tool="shell")
        assert e.type == "step.started"
        assert e.data["step_id"] == "s1"
        assert e.data["task_id"] == "wf1"
        assert e.data["tool"] == "shell"

    def test_memory_event(self):
        e = memory_event("stored", "working", "doc1", size=1024)
        assert e.type == "memory.stored"
        assert e.data["level"] == "working"
        assert e.data["key"] == "doc1"

    def test_context_event(self):
        e = context_event("built", tokens=5000, sources=3)
        assert e.type == "context.built"
        assert e.source == "context_builder"
        assert e.data["tokens"] == 5000


# ═══════════════════════════════════════════════════════════════
# Integration: EventBus + Orchestrator
# ═══════════════════════════════════════════════════════════════

class TestOrchestratorIntegration:
    def test_orchestrator_publishes_events(self):
        """Orchestrator публикует события при запуске workflow (если event_bus передан)."""
        from scripts_01.orchestrator import Orchestrator, Workflow

        events: List[str] = []

        def collector(e: Event):
            events.append(e.type)

        bus = EventBus(db_path=Path("/tmp") / f"test_events_{id(1)}.db")
        bus.subscribe("workflow.*", collector)
        bus.subscribe("step.*", collector)

        orch = Orchestrator(event_bus=bus)
        result = orch.run_workflow("Test event publishing")

        # Должны быть события workflow.created и workflow.*
        workflow_events = [t for t in events if t.startswith("workflow.")]
        assert len(workflow_events) >= 2, f"Got: {workflow_events}"
        assert any("created" in e for e in workflow_events), f"Missing created: {workflow_events}"
        assert any("completed" in e or "failed" in e for e in workflow_events)

    def test_orchestrator_publishes_step_events(self):
        """Orchestrator публикует step.started и step.completed/failed."""
        from scripts_01.orchestrator import Orchestrator

        events: List[str] = []

        def collector(e: Event):
            events.append(e.type)

        bus = EventBus(db_path=Path("/tmp") / f"test_events_{id(2)}.db")
        bus.subscribe("step.*", collector)

        orch = Orchestrator(event_bus=bus)
        orch.run_workflow("Test step events")

        step_events = [t for t in events if t.startswith("step.")]
        assert len(step_events) >= 1

    def test_orchestrator_events_have_data(self):
        """События от Orchestrator содержат task_id/step_id."""
        from scripts_01.orchestrator import Orchestrator

        events: List[Event] = []

        def collector(e: Event):
            events.append(e)

        bus = EventBus(db_path=Path("/tmp") / f"test_events_{id(3)}.db")
        bus.subscribe("*", collector)

        orch = Orchestrator(event_bus=bus)
        orch.run_workflow("Test event data")

        workflow_events = [e for e in events if e.type.startswith("workflow.")]
        for e in workflow_events:
            assert "task_id" in e.data or "workflow_id" in e.data, f"Missing id in {e.type}: {e.data}"

    def test_orchestrator_works_without_event_bus(self):
        """Orchestrator работает без EventBus (обратная совместимость)."""
        from scripts_01.orchestrator import Orchestrator, WorkflowStatus

        orch = Orchestrator()  # без event_bus
        result = orch.run_workflow("Test backward compat")
        assert result.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
