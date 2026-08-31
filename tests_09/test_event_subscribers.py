#!/usr/bin/env python3
"""
Tests for event_subscribers.py — auto-indexing and logging hooks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.event_bus import EventBus, Event
from scripts_01.event_subscribers import gister_all
from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType
from scripts_01.knowledge_engine import KnowledgeEngine


@pytest.fixture
def bus(tmp_path: Path) -> EventBus:
    """EventBus with auto-index subscriber registered."""
    event_bus = EventBus(db_path=tmp_path / "events.db")
    register_all(event_bus, workspace_root=str(tmp_path))
    return event_bus


class TestAutoIndex:
    def test_memory_stored_is_auto_indexed(self, bus: EventBus, tmp_path: Path):
        """memory.stored event triggers KnowledgeEngine indexing."""
        me = MemoryEngine(workspace_root=str(tmp_path), event_bus=bus)
        ke = KnowledgeEngine(workspace_root=str(tmp_path))

        me.store(
            MemoryLevel.KNOWLEDGE,
            "router_doc",
            "capability based router with scoring model",
            content_type=ContentType.TEXT,
            summary="router knowledge",
        )

        results = ke.search("capability router", mode="hybrid", top_k=5)
        assert any("router_doc" in r.doc_id for r in results), \
            f"Expected auto-indexed router_doc, got: {[r.doc_id for r in results]}"

    def test_personal_memory_not_auto_indexed(self, bus: EventBus, tmp_path: Path):
        """personal level should not be indexed into public knowledge."""
        me = MemoryEngine(workspace_root=str(tmp_path), event_bus=bus)
        ke = KnowledgeEngine(workspace_root=str(tmp_path))

        me.store(
            MemoryLevel.PERSONAL,
            "private_note",
            "secret router password scoring model",
            content_type=ContentType.TEXT,
            summary="private",
        )

        results = ke.search("secret router password", mode="hybrid", top_k=5)
        assert not any("private_note" in r.doc_id for r in results), \
            "Personal memory should not be auto-indexed"

    def test_archive_memory_not_auto_indexed(self, bus: EventBus, tmp_path: Path):
        """archive level should not be indexed into public knowledge."""
        me = MemoryEngine(workspace_root=str(tmp_path), event_bus=bus)
        ke = KnowledgeEngine(workspace_root=str(tmp_path))

        me.store(
            MemoryLevel.ARCHIVE,
            "old_router_doc",
            "old capability router scoring",
            content_type=ContentType.TEXT,
            summary="archived",
        )

        results = ke.search("old capability router", mode="hybrid", top_k=5)
        assert not any("old_router_doc" in r.doc_id for r in results), \
            "Archive memory should not be auto-indexed"


class TestCheckpointLogger:
    def test_checkpoint_logger_does_not_crash(self, bus: EventBus, tmp_path: Path):
        """checkpoint.created subscriber runs without error."""
        event = Event(
            type="checkpoint.created",
            data={
                "checkpoint_type": "post_step",
                "summary": "Test checkpoint summary",
            },
        )
        # Should not raise
        delivered = bus.publish(event)
        assert delivered >= 1


class TestEMAutoTriggers:
    """Tests for Engineering Memory auto-trigger subscribers."""

    def test_task_completed_long_duration_creates_retrospective(self, bus: EventBus, tmp_path: Path):
        """task.completed with duration >= 10 min creates a retrospective draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="task.completed",
            data={
                "task_id": "t1",
                "task_name": "Long task",
                "duration_seconds": 900,
                "details": "done",
            },
        )
        delivered = bus.publish(event)
        assert delivered >= 1

        drafts = em.list_drafts()
        assert any(d["type"] == "task_retrospective" for d in drafts)

    def test_task_completed_short_duration_does_not_create_retrospective(self, bus: EventBus, tmp_path: Path):
        """task.completed with short duration does not create a retrospective draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="task.completed",
            data={
                "task_id": "t2",
                "task_name": "Short task",
                "duration_seconds": 5,
                "details": "done",
            },
        )
        bus.publish(event)

        drafts = em.list_drafts()
        assert not any(d["type"] == "task_retrospective" for d in drafts)

    def test_task_failed_creates_incident(self, bus: EventBus, tmp_path: Path):
        """task.failed creates an incident draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="task.failed",
            data={
                "task_id": "t3",
                "task_name": "Failing task",
                "error": "something went wrong",
            },
        )
        bus.publish(event)

        drafts = em.list_drafts()
        assert any(d["type"] == "incident_report" for d in drafts)

    def test_git_merge_creates_retrospective(self, bus: EventBus, tmp_path: Path):
        """git.merge creates a retrospective draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="git.merge",
            data={
                "branch": "feature-42",
                "commit": "abc123",
            },
        )
        bus.publish(event)

        drafts = em.list_drafts()
        assert any(d["type"] == "task_retrospective" and "feature-42" in d["title"] for d in drafts)

    def test_system_error_creates_incident(self, bus: EventBus, tmp_path: Path):
        """system.error creates an incident draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="system.error",
            data={
                "error_id": "db-conn",
                "component": "database",
                "summary": "DB connection lost",
            },
        )
        bus.publish(event)

        drafts = em.list_drafts()
        assert any(d["type"] == "incident_report" for d in drafts)

    def test_duplicate_task_event_is_idempotent(self, bus: EventBus, tmp_path: Path):
        """Publishing the same task event twice creates only one EM draft."""
        from scripts_01.engineering_memory import EMEngine

        em = EMEngine(workspace_root=str(tmp_path))

        event = Event(
            type="task.completed",
            data={
                "task_id": "t4",
                "task_name": "Long task",
                "duration_seconds": 900,
            },
        )
        bus.publish(event)
        bus.publish(event)

        drafts = em.list_drafts()
        assert len([d for d in drafts if d["type"] == "task_retrospective"]) == 1
