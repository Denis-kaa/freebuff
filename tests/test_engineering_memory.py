"""
Tests for scripts/engineering_memory.py — Engineering Memory Engine.
"""

import os
import sys
***REMOVED***

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.engineering_memory import EMEngine, DraftNotFoundError
from scripts.memory_engine import MemoryEngine, MemoryLevel


@pytest.fixture
def em(tmp_path):
    """EMEngine с временной директорией."""
    return EMEngine(workspace_root=tmp_path)


class TestEMRecordDraft:
    """Тесты создания драфтов."""

    def test_record_decision_creates_draft(self, em):
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
            context="Need durable state",
        )
        assert draft_id.startswith("em_draft_")

        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry is not None
        assert entry.metadata["type"***REMOVED*** == "decision_journal"
        assert entry.metadata["title"***REMOVED*** == "Use SQLite"
        assert "## Decision" in entry.content
        assert "SQLite" in entry.content

    def test_record_incident_creates_draft(self, em):
        draft_id = em.record_incident(
            title="Container crash",
            summary="Crash during test",
            root_cause="OOM",
            resolution="Reduced memory usage",
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry is not None
        assert entry.metadata["type"***REMOVED*** == "incident_report"
        assert "## Summary" in entry.content

    def test_record_lesson_creates_draft(self, em):
        draft_id = em.record_lesson(
            title="Avoid shell=True",
            lesson="Never use shell=True with user input",
            context="Security audit",
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry is not None
        assert entry.metadata["type"***REMOVED*** == "lessons_learned"
        assert entry.metadata["tags"***REMOVED*** == ["lesson"***REMOVED***

    def test_record_retrospective_creates_draft(self, em):
        draft_id = em.record_task_retrospective(
            title="Refactor CLI",
            intent="Simplify commands",
            reality="Had to keep backward compat",
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry is not None
        assert entry.metadata["type"***REMOVED*** == "task_retrospective"

    def test_draft_authors_default_to_buffy(self, em):
        draft_id = em.record_decision(
            title="T", decision="D", rationale="R"
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry.metadata["authors"***REMOVED*** == ["Buffy"***REMOVED***

    def test_draft_metadata_preserved(self, em):
        draft_id = em.record_decision(
            title="X",
            decision="Y",
            rationale="Z",
            authors=["Alice"***REMOVED***,
            tags=["arch"***REMOVED***,
            related_components=["core/router.py"***REMOVED***,
            related_tasks=["TASK-1"***REMOVED***,
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry.metadata["authors"***REMOVED*** == ["Alice"***REMOVED***
        assert entry.metadata["tags"***REMOVED*** == ["arch"***REMOVED***
        assert entry.metadata["related_components"***REMOVED*** == ["core/router.py"***REMOVED***
        assert entry.metadata["related_tasks"***REMOVED*** == ["TASK-1"***REMOVED***


class TestEMFinalize:
    """Тесты финализации драфтов."""

    def test_finalize_creates_markdown_file(self, em):
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        path = em.finalize_draft(draft_id)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "---" in content
        assert "type: \"decision_journal\"" in content
        assert "## Decision" in content
        assert "SQLite" in content

    def test_finalize_removes_draft_from_memory(self, em):
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        em.finalize_draft(draft_id)
        assert em._memory.retrieve(MemoryLevel.PROJECT, draft_id) is None

    def test_finalize_unknown_draft_raises(self, em):
        with pytest.raises(DraftNotFoundError):
            em.finalize_draft("em_draft_nonexistent")

    def test_finalize_creates_decision_subdir(self, em):
        draft_id = em.record_decision(
            title="Use SQLite", decision="SQLite", rationale="Zero setup"
        )
        path = em.finalize_draft(draft_id)
        assert "docs/engineering-memory/decisions" in str(path)

    def test_finalize_creates_incident_subdir(self, em):
        draft_id = em.record_incident(
            title="Crash",
            summary="Oops",
            root_cause="OOM",
            resolution="Fix",
        )
        path = em.finalize_draft(draft_id)
        assert "docs/engineering-memory/incidents" in str(path)

    def test_finalize_reviewer_added_to_frontmatter(self, em):
        draft_id = em.record_decision(
            title="Use SQLite", decision="SQLite", rationale="Zero setup"
        )
        path = em.finalize_draft(draft_id, reviewer="Alice")
        content = path.read_text(encoding="utf-8")
        assert "reviewer:" in content
        assert '"Alice"' in content


class TestEMDraftManagement:
    """Тесты управления драфтами."""

    def test_list_drafts(self, em):
        em.record_decision("D1", "A", "B")
        em.record_lesson("L1", "C")
        drafts = em.list_drafts()
        assert len(drafts) == 2
        assert all(d["draft_id"***REMOVED***.startswith("em_draft_") for d in drafts)

    def test_discard_draft(self, em):
        draft_id = em.record_decision("D", "A", "B")
        assert em.discard_draft(draft_id) is True
        assert em._memory.retrieve(MemoryLevel.PROJECT, draft_id) is None
        assert em.discard_draft(draft_id) is False

    def test_discard_non_em_key_fails(self, em):
        em._memory.store(MemoryLevel.PROJECT, "regular_key", "data")
        assert em.discard_draft("regular_key") is False


class TestEMQuery:
    """Тесты поиска по Engineering Memory."""

    def test_query_finds_finalized_document(self, em):
        draft_id = em.record_decision(
            title="Use SQLite for state",
            decision="SQLite",
            rationale="Zero setup durable storage",
        )
        em.finalize_draft(draft_id)

        results = em.query_experience("sqlite state")
        assert len(results) > 0
        assert any("sqlite" in r["doc_id"***REMOVED***.lower() or "sqlite" in r["snippet"***REMOVED***.lower() for r in results)

    def test_query_empty_when_no_matches(self, em):
        results = em.query_experience("nonexistent xyz")
        assert results == [***REMOVED***


class TestEMEvents:
    """Тесты публикации событий."""

    def test_finalize_publishes_document_finalized_event(self, em):
        from scripts.event_bus import Event

        published = [***REMOVED***

        class FakeBus:
            def publish(self, event):
                published.append(event)

        em._event_bus = FakeBus()
        draft_id = em.record_decision("T", "D", "R")
        em.finalize_draft(draft_id)

        finalized_events = [e for e in published if e.type == "em.document_finalized"***REMOVED***
        assert len(finalized_events) == 1
        assert finalized_events[0***REMOVED***.data["type"***REMOVED*** == "decision_journal"
