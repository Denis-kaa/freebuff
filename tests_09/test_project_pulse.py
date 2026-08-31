#!/usr/bin/env python3
"""
Tests for Project Pulse Engine (scripts_01/project_pulse.py).

Tests:
  - PulseEntry serialization / icons
  - CRUD: add_entry, get, list, clear
  - list filters (event_type, source, since, limit)
  - scan_files with explicit paths
  - scan_git graceful degradation (non-git workspace)
  - EventBus: subscribe / _on_event / mapping
  - full_scan / get_stats
  - CLI commands
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.project_pulse import (
    ProjectPulse,
    PulseEntry,
    PULSE_TYPES,
    get_pulse_icon,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


class _StubEventBus:
    """Минимальный EventBus с подпиской."""

    def __init__(self):
        self.subscribed = []

    def subscribe(self, pattern, handler):
        self.subscribed.append((pattern, handler))
        return f"sub-{len(self.subscribed)}"

    def unsubscribe(self, token):
        return True


class _StubEvent:
    """Минимальный объект события EventBus."""

    def __init__(self, event_type: str, data: dict | None = None, event_id: str = ""):
        self.type = event_type
        self.event_type = event_type
        self.data = data or {}
        self.id = event_id


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Временный workspace (не git-репозиторий)."""
    ws = tmp_path / "pulse_ws"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def pulse(workspace: Path) -> ProjectPulse:
    return ProjectPulse(db_path=workspace / "pulse.db", workspace=workspace)


# ═══════════════════════════════════════════════════════════════
# PulseEntry / icons
# ═══════════════════════════════════════════════════════════════


class TestPulseEntry:
    def test_to_dict_includes_icon(self):
        e = PulseEntry(event_type="git.commit", title="Commit: abc")
        d = e.to_dict()
        assert d["event_type"] == "git.commit"
        assert d["icon"] == "💾"
        assert d["title"] == "Commit: abc"

    def test_icon_property(self):
        e = PulseEntry(event_type="file.created")
        assert e.icon == "📄"

    def test_unknown_icon(self):
        assert get_pulse_icon("mystery.type") == PULSE_TYPES["event.unknown"]

    def test_pulse_types_cover_known_categories(self):
        for key in ("git.commit", "git.branch", "file.created", "file.modified",
                    "file.deleted", "event.system", "event.task", "event.collab",
                    "event.memory", "event.plugin", "event.presence", "event.metrics"):
            assert key in PULSE_TYPES


# ═══════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════


class TestCRUD:
    def test_add_entry_returns_id(self, pulse: ProjectPulse):
        entry = PulseEntry(event_type="event.task", title="Task done")
        entry_id = pulse.add_entry(entry)
        assert entry_id == entry.id

    def test_get_entry_roundtrip(self, pulse: ProjectPulse):
        entry = PulseEntry(event_type="event.task", title="Task done", ref="ref-1")
        pulse.add_entry(entry)
        loaded = pulse.get(entry.id)
        assert loaded is not None
        assert loaded.title == "Task done"
        assert loaded.event_type == "event.task"

    def test_get_accepts_entry_object(self, pulse: ProjectPulse):
        entry = PulseEntry(event_type="event.task", title="T")
        pulse.add_entry(entry)
        loaded = pulse.get(entry)
        assert loaded is not None

    def test_get_missing(self, pulse: ProjectPulse):
        assert pulse.get("nope") is None

    def test_list_empty(self, pulse: ProjectPulse):
        assert pulse.list() == []

    def test_list_returns_entries(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A"))
        pulse.add_entry(PulseEntry(event_type="git.commit", title="B"))
        assert len(pulse.list()) == 2

    def test_clear(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A"))
        removed = pulse.clear()
        assert removed == 1
        assert pulse.list() == []

    def test_dedup_by_ref(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A", ref="same"))
        pulse.add_entry(PulseEntry(event_type="event.task", title="A", ref="same"))
        assert len(pulse.list()) == 1


# ═══════════════════════════════════════════════════════════════
# Filters
# ═══════════════════════════════════════════════════════════════


class TestFilters:
    def test_filter_by_event_type(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A"))
        pulse.add_entry(PulseEntry(event_type="git.commit", title="B"))
        entries = pulse.list(event_type="git.commit")
        assert [e.title for e in entries] == ["B"]

    def test_filter_by_source(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A", source="event"))
        pulse.add_entry(PulseEntry(event_type="git.commit", title="B", source="git"))
        entries = pulse.list(source="git")
        assert [e.title for e in entries] == ["B"]

    def test_filter_by_since(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="old", timestamp="2020-01-01T00:00:00+00:00"))
        pulse.add_entry(PulseEntry(event_type="event.task", title="new", timestamp="2026-01-01T00:00:00+00:00"))
        entries = pulse.list(since="2025-01-01T00:00:00+00:00")
        assert [e.title for e in entries] == ["new"]

    def test_limit_and_offset(self, pulse: ProjectPulse):
        for i in range(5):
            pulse.add_entry(PulseEntry(event_type="event.task", title=f"T{i}"))
        entries = pulse.list(limit=2)
        assert len(entries) == 2
        # ORDER BY timestamp DESC — последние добавленные сначала.
        assert entries[0].title == "T4"

    def test_list_json_shape(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A"))
        payload = pulse.list_json()
        assert payload["success"] is True
        assert payload["total"] == 1
        assert payload["data"]["total"] == 1
        assert payload["entries"][0]["icon"]


# ═══════════════════════════════════════════════════════════════
# scan_files / scan_git
# ═══════════════════════════════════════════════════════════════


class TestScans:
    def test_scan_files_creates_entries(self, pulse: ProjectPulse, workspace: Path):
        f1 = workspace / "a.py"
        f1.write_text("x = 1")
        added = pulse.scan_files(paths=[str(f1)])
        assert added == 1
        entries = pulse.list(source="file")
        assert entries[0].event_type == "file.created"

    def test_scan_files_second_run_no_duplicates(self, pulse: ProjectPulse, workspace: Path):
        f1 = workspace / "a.py"
        f1.write_text("x = 1")
        pulse.scan_files(paths=[str(f1)])
        assert pulse.scan_files(paths=[str(f1)]) == 0

    def test_scan_files_modified(self, pulse: ProjectPulse, workspace: Path):
        f1 = workspace / "a.py"
        f1.write_text("x = 1")
        pulse.scan_files(paths=[str(f1)])
        # Явное другое mtime (без sleep): гранularity ФС на Android может быть 1с+.
        old_mtime = f1.stat().st_mtime
        os.utime(f1, (old_mtime + 2, old_mtime + 2))
        f1.write_text("x = 2")
        added = pulse.scan_files(paths=[str(f1)])
        assert added == 1
        types = [e.event_type for e in pulse.list(source="file")]
        assert "file.modified" in types

    def test_scan_git_graceful_non_git(self, pulse: ProjectPulse):
        # Не-git workspace: не падает, возвращает 0.
        assert pulse.scan_git() == 0

    def test_full_scan_returns_counts(self, pulse: ProjectPulse, workspace: Path):
        (workspace / "b.py").write_text("y = 2")
        result = pulse.full_scan()
        assert "git" in result
        assert "file" in result
        assert "files" in result
        assert result["files"] == result["file"]
        assert result["file"] >= 1


# ═══════════════════════════════════════════════════════════════
# EventBus
# ═══════════════════════════════════════════════════════════════


class TestEventBus:
    def test_subscribe_eventbus(self, workspace: Path):
        bus = _StubEventBus()
        pulse = ProjectPulse(db_path=workspace / "p.db", workspace=workspace, event_bus=bus)
        assert pulse.subscribe_eventbus() is True
        assert len(bus.subscribed) == 1
        assert bus.subscribed[0][0] == "*"

    def test_subscribe_without_bus(self, pulse: ProjectPulse):
        assert pulse.subscribe_eventbus() is False

    def test_unsubscribe(self, workspace: Path):
        bus = _StubEventBus()
        pulse = ProjectPulse(db_path=workspace / "p.db", workspace=workspace, event_bus=bus)
        pulse.subscribe_eventbus()
        pulse.unsubscribe_eventbus()

    def test_on_event_creates_entry(self, pulse: ProjectPulse):
        pulse._on_event(_StubEvent("task.failed", {"task": "build"}, event_id="e1"))
        entries = pulse.list()
        assert len(entries) == 1
        assert entries[0].event_type == "event.task"
        assert entries[0].title == "build"
        assert entries[0].source == "event"

    def test_on_event_dedup(self, pulse: ProjectPulse):
        pulse._on_event(_StubEvent("task.failed", {}, event_id="e1"))
        pulse._on_event(_StubEvent("task.failed", {}, event_id="e1"))
        assert len(pulse.list()) == 1

    def test_map_event_type(self, pulse: ProjectPulse):
        assert pulse._map_event_type("task.started") == "event.task"
        assert pulse._map_event_type("collab.message") == "event.collab"
        assert pulse._map_event_type("presence.online") == "event.presence"
        assert pulse._map_event_type("metrics.report") == "event.metrics"
        assert pulse._map_event_type("system.boot") == "event.system"

    def test_map_event_type_unknown(self, pulse: ProjectPulse):
        assert pulse._map_event_type("mystery.type") == "event.unknown"
        assert pulse._map_event_type("") == "event.unknown"

    def test_map_event_type_already_mapped(self, pulse: ProjectPulse):
        assert pulse._map_event_type("event.task") == "event.task"


# ═══════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════


class TestStats:
    def test_get_stats_empty(self, pulse: ProjectPulse):
        stats = pulse.get_stats()
        assert stats["total_entries"] == 0
        assert stats["last_entry"] == "never"
        assert stats["type_counts"] == {}
        assert stats["source_counts"] == {}

    def test_get_stats_with_entries(self, pulse: ProjectPulse):
        pulse.add_entry(PulseEntry(event_type="event.task", title="A", source="event"))
        pulse.add_entry(PulseEntry(event_type="event.task", title="B", source="event"))
        pulse.add_entry(PulseEntry(event_type="git.commit", title="C", source="git"))
        stats = pulse.get_stats()
        assert stats["total_entries"] == 3
        assert stats["type_counts"]["event.task"] == 2
        assert stats["type_counts"]["git.commit"] == 1
        assert stats["source_counts"]["event"] == 2
        assert stats["source_counts"]["git"] == 1
        assert stats["last_entry"] != "never"
        assert stats["db_path"]


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts_01.project_pulse import main

        monkeypatch.setattr(sys, "argv", ["project_pulse.py", "--help"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_no_command(self, monkeypatch, capsys):
        from scripts_01.project_pulse import main

        monkeypatch.setattr(sys, "argv", ["project_pulse.py"])
        code = main()
        assert code == 1
