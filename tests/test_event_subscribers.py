#!/usr/bin/env python3
"""
Tests for event_subscribers.py — auto-indexing and logging hooks.
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.event_bus import EventBus, Event
from scripts.event_subscribers ***REMOVED***gister_all
from scripts.memory_engine import MemoryEngine, MemoryLevel, ContentType
from scripts.knowledge_engine import KnowledgeEngine


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
            f"Expected auto-indexed router_doc, got: {[r.doc_id for r in results***REMOVED******REMOVED***"

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
            ***REMOVED***,
        )
        # Should not raise
        delivered = bus.publish(event)
        assert delivered >= 1
