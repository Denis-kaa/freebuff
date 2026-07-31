"""
Tests for scripts/engineering_memory.py — Engineering Memory Engine.
"""

import os
import shutil
import sys
***REMOVED***

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.engineering_memory import EMEngine, DraftNotFoundError
from scripts.memory_engine import MemoryEngine, MemoryLevel


@pytest.fixture
def em(tmp_path):
    """EMEngine с временной директорией и реальными шаблонами."""
    project_root = Path(__file__).resolve().parent.parent
    templates_dir = project_root / "docs" / "engineering-memory" / "templates"
    return EMEngine(workspace_root=tmp_path, templates_dir=templates_dir)


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


class TestEMTemplates:
    """Тесты рендеринга шаблонов."""

    def test_list_templates_includes_core_templates(self, em):
        templates = em.list_templates()
        assert "decision_journal.md" in templates
        assert "incident_report.md" in templates
        assert "task_retrospective.md" in templates
        assert "lessons_learned.md" in templates

    def test_render_decision_journal_template(self, em):
        rendered = em.render_template(
            "decision_journal.md",
            title="Use SQLite",
            context="Need durable state",
            options="SQLite, LevelDB",
            decision="SQLite",
            rationale="Zero setup",
            consequences="Single-node only",
            authors="Buffy",
            date="2026-07-31",
        )
        assert "Use SQLite" in rendered
        assert "Need durable state" in rendered
        assert "## Context" in rendered
        assert "## Decision" in rendered

    def test_render_template_missing_placeholders_left_as_is(self, em):
        rendered = em.render_template(
            "lessons_learned.md",
            title="Avoid shell=True",
            lesson="Never use shell=True with user input",
        )
        assert "Avoid shell=True" in rendered
        assert "Never use shell=True with user input" in rendered
        # unreplaced placeholders remain as {placeholder***REMOVED***
        assert "{context***REMOVED***" in rendered

    def test_create_draft_from_template(self, em):
        draft_id = em.create_draft_from_template(
            "decision_journal.md",
            title="Use SQLite",
            context="Need durable state",
            options="SQLite, LevelDB",
            decision="SQLite",
            rationale="Zero setup",
            consequences="Single-node only",
            authors="Buffy",
        )
        entry = em._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        assert entry is not None
        assert entry.metadata["type"***REMOVED*** == "decision_journal"
        assert entry.metadata["title"***REMOVED*** == "Use SQLite"
        assert "## Context" in entry.content

    def test_finalize_draft_from_template_has_single_frontmatter(self, em):
        draft_id = em.create_draft_from_template(
            "decision_journal.md",
            title="Use SQLite",
            context="Need durable state",
            options="SQLite, LevelDB",
            decision="SQLite",
            rationale="Zero setup",
            consequences="Single-node only",
            authors=["Buffy"***REMOVED***,
        )
        path = em.finalize_draft(draft_id)
        content = path.read_text(encoding="utf-8")

        # Count YAML frontmatter blocks: should be exactly one
        assert content.startswith("---")
        delimiter_count = content.count("\n---")
        assert delimiter_count == 1, "Finalized doc should contain exactly one frontmatter block"

        # The body should come from the template, not have a wrapper '## Content'
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Content" not in content

    def test_template_renderer_unknown_template_raises(self, em):
        with pytest.raises(FileNotFoundError):
            em.render_template("nonexistent.md")


class TestEMDecisionIndex:
    """Тесты авто-обновления индекса архитектурных решений."""

    def test_finalize_decision_updates_index(self, em):
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        path = em.finalize_draft(draft_id)

        index_path = em._root / "docs" / "decisions" / "DECISIONS.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "Use SQLite" in content
        assert "engineering-memory/decisions" in content
        assert "ADR-" in content

    def test_em_generated_adr_gets_assigned_id(self, em):
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        path = em.finalize_draft(draft_id)
        content = path.read_text(encoding="utf-8")
        assert "adr_id:" in content
        assert '"ADR-' in content

    def test_index_contains_existing_and_new_adrs(self, em):
        # Ручной ADR
        decisions_dir = em._root / "docs" / "engineering-memory" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        manual_adr = decisions_dir / "ADR_001_Test.md"
        manual_adr.write_text(
            "# ADR-001: Test Decision\\n\\n"
            "**Дата:** 2026-07-28\\n"
            "**Статус:** ✅ Принято\\n\\n"
            "## Context\\n\\nTest.\\n",
            encoding="utf-8",
        )

        # EM-generated ADR
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        em.finalize_draft(draft_id)

        index_path = em._root / "docs" / "decisions" / "DECISIONS.md"
        content = index_path.read_text(encoding="utf-8")
        assert "Test Decision" in content
        assert "Use SQLite" in content
        assert "ADR-001" in content
        assert "ADR-002" in content

    def test_regenerate_decision_index_no_decisions_dir(self, em):
        # Убедимся, что finalize создаёт директорию и индекс с нуля
        draft_id = em.record_decision(
            title="Use SQLite",
            decision="SQLite",
            rationale="Zero setup",
        )
        em.finalize_draft(draft_id)

        index_path = em._root / "docs" / "decisions" / "DECISIONS.md"
        assert index_path.exists()
        assert "Use SQLite" in index_path.read_text(encoding="utf-8")
