"""
Tests for scripts_01/memory_engine.py — Memory Engine.
"""

import os
import json
import sys
import pytest
}

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts_01.memory_engine import (
    MemoryEngine, MemoryLevel, ContentType, MemoryEntry,
)


@pytest.fixture
def engine(tmp_path):
    """MemoryEngine с временной директорией."""
    return MemoryEngine(workspace_root=tmp_path)


class TestMemoryLevel:
    """Тесты enum и типов."""

    def test_memory_level_values(self):
        assert MemoryLevel.WORKING.value == "working"
        assert MemoryLevel.PROJECT.value == "project"
        assert MemoryLevel.KNOWLEDGE.value == "knowledge"
        assert MemoryLevel.PERSONAL.value == "personal"
        assert MemoryLevel.ARCHIVE.value == "archive"

    def test_memory_level_count(self):
        assert len(list(MemoryLevel)) == 5

    def test_content_type_values(self):
        assert ContentType.TEXT.value == "text"
        assert ContentType.MARKDOWN.value == "markdown"
        assert ContentType.JSON.value == "json"


class TestMemoryEngineStore:
    """Тесты сохранения записей."""

    def test_store_working_memory(self, engine):
        entry = engine.store(MemoryLevel.WORKING, "current_task", "Рефакторинг TUI")
        assert entry.key == "current_task"
        assert entry.content == "Рефакторинг TUI"
        assert entry.level == MemoryLevel.WORKING
        assert entry.id

    def test_store_with_summary_and_metadata(self, engine):
        entry = engine.store(
            MemoryLevel.PROJECT, "architecture_v2",
            "Проект переведён на 5-слойную архитектуру",
            content_type=ContentType.MARKDOWN,
            summary="Архитектурное решение v2",
            metadata={"importance": "high", "tags": ["architecture", "v2"]},
        )
        assert entry.summary == "Архитектурное решение v2"
        assert entry.metadata["importance"] == "high"
        assert "v2" in entry.metadata["tags"]

    def test_store_overwrite_false(self, engine):
        engine.store(MemoryLevel.WORKING, "test_key", "original", overwrite=True)
        with pytest.raises(FileExistsError):
            engine.store(MemoryLevel.WORKING, "test_key", "new", overwrite=False)

    def test_store_overwrite_true_updates_content(self, engine):
        e1 = engine.store(MemoryLevel.WORKING, "key", "original")
        e2 = engine.store(MemoryLevel.WORKING, "key", "updated", overwrite=True)
        assert e2.content == "updated"
        assert e2.id == e1.id  # ID сохраняется

    def test_store_multiple_levels(self, engine):
        engine.store(MemoryLevel.WORKING, "task", "Do X")
        engine.store(MemoryLevel.PROJECT, "doc", "Documentation")
        engine.store(MemoryLevel.PERSONAL, "style", "python")
        assert engine.count_entries() == 3


class TestMemoryEngineRetrieve:
    """Тесты чтения записей."""

    def test_retrieve_existing(self, engine):
        engine.store(MemoryLevel.KNOWLEDGE, "python_patterns", "Factory, Singleton")
        entry = engine.retrieve(MemoryLevel.KNOWLEDGE, "python_patterns")
        assert entry is not None
        assert entry.content == "Factory, Singleton"

    def test_retrieve_nonexistent(self, engine):
        entry = engine.retrieve(MemoryLevel.WORKING, "nonexistent_key")
        assert entry is None

    def test_retrieve_from_different_level(self, engine):
        engine.store(MemoryLevel.ARCHIVE, "old_project", "Legacy")
        e1 = engine.retrieve(MemoryLevel.ARCHIVE, "old_project")
        e2 = engine.retrieve(MemoryLevel.WORKING, "old_project")
        assert e1 is not None
        assert e2 is None  # не пересекаются

    def test_retrieve_preserves_all_fields(self, engine):
        engine.store(
            MemoryLevel.PERSONAL, "prefs",
            "Предпочитаю Python",
            summary="Языки",
            metadata={"since": 2020},
        )
        entry = engine.retrieve(MemoryLevel.PERSONAL, "prefs")
        assert entry.key == "prefs"
        assert entry.summary == "Языки"
        assert entry.metadata["since"] == 2020
        assert entry.content_type == ContentType.TEXT


class TestMemoryEngineDelete:
    """Тесты удаления."""

    def test_delete_existing(self, engine):
        engine.store(MemoryLevel.WORKING, "to_delete", "data_13")
        assert engine.retrieve(MemoryLevel.WORKING, "to_delete") is not None
        assert engine.delete(MemoryLevel.WORKING, "to_delete") is True
        assert engine.retrieve(MemoryLevel.WORKING, "to_delete") is None

    def test_delete_nonexistent(self, engine):
        assert engine.delete(MemoryLevel.WORKING, "no_such_key") is False

    def test_delete_wrong_level(self, engine):
        engine.store(MemoryLevel.PROJECT, "shared_key", "data_13")
        assert engine.delete(MemoryLevel.WORKING, "shared_key") is False
        assert engine.retrieve(MemoryLevel.PROJECT, "shared_key") is not None


class TestMemoryEngineList:
    """Тесты списка записей."""

    def test_list_all_levels(self, engine):
        engine.store(MemoryLevel.WORKING, "a", "1")
        engine.store(MemoryLevel.PROJECT, "b", "2")
        assert len(engine.list_entries()) == 2

    def test_list_specific_level(self, engine):
        engine.store(MemoryLevel.WORKING, "w1", "1")
        engine.store(MemoryLevel.WORKING, "w2", "2")
        engine.store(MemoryLevel.PROJECT, "p1", "3")
        entries = engine.list_entries(level=MemoryLevel.WORKING)
        assert len(entries) == 2
        assert all(e.level == MemoryLevel.WORKING for e in entries)

    def test_list_empty(self, engine):
        assert engine.list_entries() == []

    def test_list_filter_by_metadata(self, engine):
        engine.store(
            MemoryLevel.PROJECT, "high_priority",
            "Important",
            metadata={"priority": "high"},
        )
        engine.store(
            MemoryLevel.PROJECT, "low_priority",
            "Not important",
            metadata={"priority": "low"},
        )
        high = engine.list_entries(
            level=MemoryLevel.PROJECT,
            filter_metadata={"priority": "high"},
        )
        assert len(high) == 1
        assert high[0].key == "high_priority"

    def test_list_sorted_by_updated(self, engine):
        e1 = engine.store(MemoryLevel.WORKING, "first", "old")
        import time
        time.sleep(0.01)
        e2 = engine.store(MemoryLevel.WORKING, "second", "new")
        entries = engine.list_entries(level=MemoryLevel.WORKING)
        assert entries[0].key == "second"  # new first


class TestMemoryEngineSearch:
    """Тесты поиска."""

    def test_search_by_keyword(self, engine):
        engine.store(MemoryLevel.WORKING, "refactor_tui", "Нужно переписать TUI")
        engine.store(MemoryLevel.PROJECT, "architecture", "5 слоёв")
        results = engine.search("TUI")
        assert len(results) == 1
        assert results[0].key == "refactor_tui"

    def test_search_case_insensitive(self, engine):
        engine.store(MemoryLevel.WORKING, "test", "Hello World")
        results = engine.search("hello")
        assert len(results) == 1

    def test_search_in_summary(self, engine):
        engine.store(
            MemoryLevel.KNOWLEDGE, "patterns",
            "Design patterns in Python",
            summary="Паттерны проектирования",
        )
        results = engine.search("Паттерны")
        assert len(results) == 1

    def test_search_by_level(self, engine):
        engine.store(MemoryLevel.WORKING, "task", "code task")
        engine.store(MemoryLevel.PROJECT, "task", "project task")
        results = engine.search("task", level=MemoryLevel.WORKING)
        assert len(results) == 1


class TestMemoryEngineContext:
    """Тесты build_context()."""

    def test_build_context_empty(self, engine):
        ctx = engine.build_context()
        assert ctx == ""

    def test_build_context_with_working_memory(self, engine):
        engine.store(MemoryLevel.WORKING, "task", "Рефакторинг TUI")
        engine.store(MemoryLevel.WORKING, "status", "В процессе")
        ctx = engine.build_context(levels=[MemoryLevel.WORKING])
        assert "WORKING MEMORY" in ctx
        assert "Рефакторинг TUI" in ctx
        assert "В процессе" in ctx

    def test_build_context_excludes_archive_by_default(self, engine):
        engine.store(MemoryLevel.ARCHIVE, "old", "Legacy data")
        ctx = engine.build_context()
        assert "Legacy data" not in ctx

    def test_build_context_summary_only(self, engine):
        engine.store(
            MemoryLevel.PROJECT, "arch",
            "Длинное описание архитектуры... " * 50,
            summary="Кратко: архитектура v2",
        )
        ctx = engine.build_context(
            levels=[MemoryLevel.PROJECT],
            include_summary_only=True,
        )
        assert "Кратко: архитектура v2" in ctx
        # Full content не должен быть включён в summary-only режиме

    def test_build_context_multiple_levels(self, engine):
        engine.store(MemoryLevel.WORKING, "task", "Fix bug")
        engine.store(MemoryLevel.PROJECT, "doc", "README update")
        engine.store(MemoryLevel.PERSONAL, "style", "PEP8")
        ctx = engine.build_context(
            levels=[MemoryLevel.WORKING, MemoryLevel.PROJECT, MemoryLevel.PERSONAL],
        )
        assert "WORKING MEMORY" in ctx
        assert "PROJECT MEMORY" in ctx
        assert "PERSONAL MEMORY" in ctx
        assert "Fix bug" in ctx
        assert "README update" in ctx
        assert "PEP8" in ctx

    def test_build_context_respects_max_tokens(self, engine):
        # Добавляем много контента
        for i in range(5):
            engine.store(
                MemoryLevel.WORKING, f"long_entry_{i}",
                "X" * 5000,  # ~1250 токенов каждый
            )
        ctx = engine.build_context(max_tokens=1000)
        # Должен быть обрезан (1000 токенов * 4 символа ≈ 4000 + структура)
        assert len(ctx) < 8000


class TestMemoryEngineStats:
    """Тесты статистики."""

    def test_get_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats["total"] == 0

    def test_get_stats_with_data(self, engine):
        engine.store(MemoryLevel.WORKING, "a", "1")
        engine.store(MemoryLevel.PROJECT, "b", "2")
        stats = engine.get_stats()
        assert stats["total"] == 2
        assert stats["working"]["count"] == 1
        assert stats["project"]["count"] == 1

    def test_count_entries(self, engine):
        assert engine.count_entries() == 0
        engine.store(MemoryLevel.WORKING, "x", "data_13")
        assert engine.count_entries() == 1
        assert engine.count_entries(level=MemoryLevel.WORKING) == 1
        assert engine.count_entries(level=MemoryLevel.PROJECT) == 0


class TestMemoryEngineWipe:
    """Тесты очистки уровней."""

    def test_wipe_level(self, engine):
        engine.store(MemoryLevel.WORKING, "w1", "1")
        engine.store(MemoryLevel.WORKING, "w2", "2")
        engine.store(MemoryLevel.PROJECT, "p1", "3")
        assert engine.wipe_level(MemoryLevel.WORKING) == 2
        assert engine.count_entries(level=MemoryLevel.WORKING) == 0
        assert engine.count_entries(level=MemoryLevel.PROJECT) == 1
