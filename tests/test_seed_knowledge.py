#!/usr/bin/env python3
"""
Tests for scripts/seed_knowledge.py — seeding the Knowledge Memory layer.
"""

from __future__ import annotations

import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.seed_knowledge import seed, _safe_key, _collect_doc_sources
from scripts.memory_engine import MemoryEngine, MemoryLevel
from scripts.knowledge_engine import KnowledgeEngine


class TestSafeKey:
    def test_simple_name(self):
        assert _safe_key("README.md") == "readme_md"

    def test_mixed_case_and_spaces(self):
        assert _safe_key("My Cool Doc") == "my_cool_doc"


class TestSeedKnowledge:
    def test_seed_creates_memory_entries(self, tmp_path: Path):
        """seed() stores project docs as MemoryLevel.KNOWLEDGE entries."""
        # Minimal project docs
        (tmp_path / "README.md").write_text("# README\nProject overview.")
        (tmp_path / "BUFFY.md").write_text("# BUFFY\nAgent instructions.")

        # Ensure docs directory exists
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "AGENTS.md").write_text("# AGENTS\nAgent guide.")

        count = seed(workspace_root=str(tmp_path))
        assert count > 0

        me = MemoryEngine(workspace_root=str(tmp_path))
        entries = me.list_entries(level=MemoryLevel.KNOWLEDGE)
        assert len(entries) >= 2
        keys = {e.key for e in entries***REMOVED***
        assert "readme_md" in keys
        assert "buffy_md" in keys

    def test_seed_rebuilds_knowledge_index(self, tmp_path: Path):
        """After seeding, KnowledgeEngine can search the docs."""
        (tmp_path / "README.md").write_text(
            "# README\nCapability-based router with scoring and memory engine.",
        )

        seed(workspace_root=str(tmp_path))

        ke = KnowledgeEngine(workspace_root=str(tmp_path))
        results = ke.search("capability router", mode="hybrid", top_k=5)
        assert len(results) >= 1
        assert any("readme" in r.doc_id.lower() for r in results)

    def test_seed_skips_missing_files(self, tmp_path: Path):
        """seed() should not fail if some docs are missing."""
        (tmp_path / "README.md").write_text("# README\nOnly doc.")

        count = seed(workspace_root=str(tmp_path))
        # Should seed README + best-practice cards, but not missing files
        assert count > 0

        me = MemoryEngine(workspace_root=str(tmp_path))
        entries = me.list_entries(level=MemoryLevel.KNOWLEDGE)
        assert any(e.key == "readme_md" for e in entries)

    def test_seed_is_idempotent(self, tmp_path: Path):
        """Repeated seeding with unchanged docs should not create duplicates."""
        (tmp_path / "README.md").write_text("# README\nProject overview.")

        count1 = seed(workspace_root=str(tmp_path))
        assert count1 > 0

        count2 = seed(workspace_root=str(tmp_path))
        assert count2 == 0

        me = MemoryEngine(workspace_root=str(tmp_path))
        entries = me.list_entries(level=MemoryLevel.KNOWLEDGE)
        readme_entries = [e for e in entries if e.key == "readme_md"***REMOVED***
        assert len(readme_entries) == 1

    def test_seed_with_event_bus_avoids_rebuild(self, tmp_path: Path):
        """When an event_bus is supplied, seed skips the full rebuild by default."""
        (tmp_path / "README.md").write_text("# README\nProject overview.")

        class FakeBus:
            def __init__(self):
                self.events = [***REMOVED***

            def publish(self, event):
                self.events.append(event)

        bus = FakeBus()
        count = seed(workspace_root=str(tmp_path), event_bus=bus)
        # Should store docs but not call rebuild_index (no KnowledgeEngine needed)
        assert count > 0
        # MemoryEngine should have published memory.stored events
        assert any(e.type == "memory.stored" for e in bus.events)


class TestCollectDocSources:
    def test_core_manifests_plus_discovered_docs(self, tmp_path: Path):
        """_collect_doc_sources includes core manifests and docs/*.md."""
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "BUFFY.md").write_text("# BUFFY")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / "docs" / "RULES.md").write_text("# RULES")

        sources = _collect_doc_sources(tmp_path)
        assert "README.md" in sources
        assert "BUFFY.md" in sources
        assert "docs/AGENTS.md" in sources
        assert "docs/RULES.md" in sources

    def test_excluded_patterns_are_skipped(self, tmp_path: Path):
        """_collect_doc_sources skips AUDIT files and templates."""
        (tmp_path / "README.md").write_text("# README")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "AGENTS.md").write_text("# AGENTS")
        (tmp_path / "docs" / "AUDIT_2026-07-28.md").write_text("# AUDIT")
        (tmp_path / "docs" / "TASK_TEMPLATE.md").write_text("# TEMPLATE")

        sources = _collect_doc_sources(tmp_path)
        assert "docs/AGENTS.md" in sources
        assert "docs/AUDIT_2026-07-28.md" not in sources
        assert "docs/TASK_TEMPLATE.md" not in sources
