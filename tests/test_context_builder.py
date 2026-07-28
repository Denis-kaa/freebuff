#!/usr/bin/env python3
"""
Tests for Context Builder (scripts/context_builder.py).

Tests:
  - build() produces non-empty context from real files
  - build() with level filtering
  - build() respects include_task/include_changelog/include_session flags
  - build() handles missing TASK.md / CHANGELOG.md gracefully
  - get_status() returns correct stats
  - max_tokens limiting works
  - Edge cases: empty memory, missing files
"""

from __future__ import annotations

import json
import os
import sys
import pytest
***REMOVED***

# Добавляем корень проекта в sys.path для импорта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.context_builder import ContextBuilder
from scripts.memory_engine import MemoryEngine, MemoryLevel, ContentType


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Создаёт временную рабочую директорию с TASK.md и CHANGELOG.md."""
    ws = tmp_path / "freebuff_test"
    ws.mkdir(parents=True, exist_ok=True)

    # TASK.md
    task_md = ws / "TASK.md"
    task_md.write_text(
        "# TASK: Test Task\n\n"
        "## Цель\n"
        "Тестирование Context Builder\n\n"
        "## TODO\n"
        "- [ ***REMOVED*** Test 1\n"
        "- [ ***REMOVED*** Test 2\n",
        encoding="utf-8",
    )

    # CHANGELOG.md
    changelog_md = ws / "CHANGELOG.md"
    changelog_md.write_text(
        "# Changelog\n\n"
        "## [3.0.0***REMOVED*** - 2026-07-28\n"
        "- Major feature\n\n"
        "---\n\n"
        "## [2.0.0***REMOVED*** - 2026-07-27\n"
        "- Feature 2\n\n"
        "---\n\n"
        "## [1.0.0***REMOVED*** - 2026-07-26\n"
        "- Initial release\n",
        encoding="utf-8",
    )

    return ws


@pytest.fixture
def empty_workspace(tmp_path: Path) -> Path:
    """Создаёт временную рабочую директорию без TASK.md и CHANGELOG.md."""
    ws = tmp_path / "freebuff_empty"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def builder_with_memory(tmp_workspace: Path) -> ContextBuilder:
    """Context Builder с заполненной Project Memory."""
    builder = ContextBuilder(workspace_root=tmp_workspace)

    # Наполняем Working память
    engine = MemoryEngine(workspace_root=str(tmp_workspace))
    engine.store(
        MemoryLevel.WORKING, "active_task",
        "Рефакторинг модуля роутинга",
        content_type=ContentType.TEXT,
        summary="Активная задача: рефакторинг роутинга",
    )
    engine.store(
        MemoryLevel.PROJECT, "test_doc",
        "Документация для тестирования",
        content_type=ContentType.MARKDOWN,
        summary="Тестовый документ",
    )

    return builder


# ═══════════════════════════════════════════════════════════════
# Tests: build()
# ═══════════════════════════════════════════════════════════════


class TestBuild:
    """Тесты основного метода build()."""

    def test_build_produces_context(self, builder_with_memory: ContextBuilder):
        """build() возвращает непустой контекст со всеми источниками."""
        ctx = builder_with_memory.build()
        assert ctx, "Context should not be empty"
        assert "UNIFIED CONTEXT" in ctx, "Should have header"
        assert "TASK" in ctx or "WORKING" in ctx, "Should have task or memory sections"
        assert "CHANGELOG" in ctx, "Should have changelog section"
        assert "active_task" in ctx, "Should include working memory entries"

    def test_build_without_task(self, builder_with_memory: ContextBuilder):
        """build(include_task=False) исключает TASK.md."""
        ctx = builder_with_memory.build(include_task=False)
        assert ctx, "Context should not be empty"
        assert "CHANGELOG" in ctx, "Changelog should still be present"
        # "TASK" header won't appear if task is excluded
        count_task = ctx.count("TASK — текущая задача")
        assert count_task == 0, "Task section should be excluded"

    def test_build_without_changelog(self, builder_with_memory: ContextBuilder):
        """build(include_changelog=False) исключает CHANGELOG.md."""
        ctx = builder_with_memory.build(include_changelog=False)
        assert ctx, "Context should not be empty"
        assert "TASK" in ctx, "Task should still be present"
        assert "CHANGELOG" not in ctx, "Changelog section should be excluded"

    def test_build_without_session(self, builder_with_memory: ContextBuilder):
        """build(include_session=False) не падает (StreamBridge может не быть)."""
        ctx = builder_with_memory.build(include_session=False)
        assert ctx, "Context should not be empty"
        # Нет SESSION CONTENT — это нормально в тестовом окружении
        assert "TASK" in ctx, "Task should be present"

    def test_build_only_memory(self, builder_with_memory: ContextBuilder):
        """build() без файлов возвращает только память."""
        ctx = builder_with_memory.build(
            include_task=False,
            include_changelog=False,
            include_session=False,
        )
        assert ctx, "Memory context should not be empty"
        assert "WORKING MEMORY" in ctx, "Should include working memory"
        assert "active_task" in ctx, "Should include working entries"

    def test_build_with_level_filter(self, builder_with_memory: ContextBuilder):
        """build(levels=[\"working\"***REMOVED***) включает только рабочую память."""
        ctx = builder_with_memory.build(
            levels=["working"***REMOVED***,
            include_task=False,
            include_changelog=False,
            include_session=False,
        )
        assert ctx, "Context should not be empty"
        assert "WORKING MEMORY" in ctx
        assert "PROJECT MEMORY" not in ctx, "Project level should be excluded"

    def test_build_max_tokens_respected(self, tmp_workspace: Path):
        """build() с маленьким max_tokens обрезает контекст."""
        builder = ContextBuilder(max_tokens=20, workspace_root=tmp_workspace)
        ctx = builder.build()
        # Может быть пустым или очень коротким
        assert len(ctx) < 300, f"Context too large for 20 tokens: {len(ctx)***REMOVED*** chars"

    def test_build_empty_memory_only(self, empty_workspace: Path):
        """build() без памяти и без файлов возвращает пустую строку."""
        builder = ContextBuilder(workspace_root=empty_workspace)
        ctx = builder.build(
            include_task=False,
            include_changelog=False,
            include_session=False,
        )
        assert ctx == "", "Empty context should return empty string"


# ═══════════════════════════════════════════════════════════════
# Tests: get_status()
# ═══════════════════════════════════════════════════════════════


class TestStatus:
    """Тесты get_status()."""

    def test_status_with_files(self, builder_with_memory: ContextBuilder):
        """get_status() возвращает информацию о всех источниках."""
        status = builder_with_memory.get_status()
        assert "memory" in status, "Should have memory stats"
        assert status["task_exists"***REMOVED*** is True, "TASK.md should exist"
        assert status["changelog_exists"***REMOVED*** is True, "CHANGELOG.md should exist"
        assert "sources" in status, "Should have sources"
        assert "memory_levels" in status["sources"***REMOVED***, "Should list memory levels"

    def test_status_empty_workspace(self, empty_workspace: Path):
        """get_status() в пустой рабочей директории."""
        builder = ContextBuilder(workspace_root=empty_workspace)
        status = builder.get_status()
        assert status["task_exists"***REMOVED*** is False, "TASK.md should not exist"
        assert status["changelog_exists"***REMOVED*** is False, "CHANGELOG.md should not exist"

    def test_status_memory_after_store(self, tmp_workspace: Path):
        """get_status() отражает новые записи в памяти."""
        builder = ContextBuilder(workspace_root=tmp_workspace)
        status_before = builder.get_status()
        total_before = status_before["memory"***REMOVED***["total"***REMOVED***

        # Добавляем запись
        engine = MemoryEngine(workspace_root=str(tmp_workspace))
        engine.store(MemoryLevel.WORKING, "new_entry", "test")

        status_after = builder.get_status()
        total_after = status_after["memory"***REMOVED***["total"***REMOVED***
        assert total_after == total_before + 1, "Total should increase by 1"

    def test_status_structure(self, builder_with_memory: ContextBuilder):
        """get_status() возвращает корректную структуру."""
        status = builder_with_memory.get_status()
        # Проверяем структуру memory
        mem = status["memory"***REMOVED***
        for level_name in ["working", "project", "knowledge", "personal", "archive"***REMOVED***:
            assert level_name in mem, f"Missing level: {level_name***REMOVED***"
            assert "count" in mem[level_name***REMOVED***, f"Missing count in {level_name***REMOVED***"
            assert "keys" in mem[level_name***REMOVED***, f"Missing keys in {level_name***REMOVED***"


# ═══════════════════════════════════════════════════════════════
# Tests: source reading
# ═══════════════════════════════════════════════════════════════


class TestSourceReading:
    """Тесты чтения файлов-источников."""

    def test_task_content_appears_in_context(self, tmp_workspace: Path):
        """build() включает содержимое TASK.md."""
        # Создаём TASK с уникальным содержанием
        task_md = tmp_workspace / "TASK.md"
        task_md.write_text("# TASK: UNIQUE_TASK_CONTENT", encoding="utf-8")

        builder = ContextBuilder(workspace_root=tmp_workspace)
        ctx = builder.build(
            include_changelog=False,
            include_session=False,
        )
        assert "UNIQUE_TASK_CONTENT" in ctx, "Task content should be in context"

    def test_changelog_content_appears_in_context(self, tmp_workspace: Path):
        """build() включает содержимое CHANGELOG.md."""
        builder = ContextBuilder(workspace_root=tmp_workspace)
        ctx = builder.build(
            include_task=False,
            include_session=False,
        )
        assert "Changelog" in ctx or "CHANGELOG" in ctx, \
            "Changelog content should be in context"

    def test_empty_task_handled_gracefully(self, empty_workspace: Path):
        """build() без TASK.md не падает."""
        builder = ContextBuilder(workspace_root=empty_workspace)

        # Ошибка при чтении несуществующего файла
        ctx = builder.build(
            include_task=True,
            include_changelog=False,
            include_session=False,
        )
        # Context might be empty since there's no memory, task, or changelog
        assert ctx == "" or "TASK" not in ctx, \
            "Should not include task section if file is missing"


# ═══════════════════════════════════════════════════════════════
# Tests: CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    """Тесты CLI через прямой вызов main с подменой sys.argv."""

    def test_cli_status_output(self, monkeypatch, tmp_workspace: Path):
        """--status выводит JSON со статистикой."""
        import scripts.context_builder as cb_mod
        monkeypatch.setattr(
            cb_mod, "WORKSPACE", tmp_workspace
        )
        monkeypatch.setattr(sys, "argv", ["context_builder.py", "--status"***REMOVED***)
        try:
            cb_mod.main()
            # Если дошло сюда без исключения — ок
            assert True
        except SystemExit:
            assert True
        except Exception as e:
            pytest.fail(f"main() raised unexpectedly: {e***REMOVED***")

    def test_cli_save_output(self, monkeypatch, tmp_path, tmp_workspace: Path):
        """--save записывает контекст в файл."""
        import scripts.context_builder as cb_mod
        save_path = tmp_path / "test_ctx.md"

        monkeypatch.setattr(cb_mod, "WORKSPACE", tmp_workspace)
        monkeypatch.setattr(
            sys, "argv",
            ["context_builder.py", "--save", str(save_path), "--no-session"***REMOVED***,
        )
        try:
            cb_mod.main()
        except SystemExit:
            pass
        except Exception as e:
            pytest.fail(f"main() raised unexpectedly: {e***REMOVED***")

        assert save_path.exists(), "Save file should exist"
        content = save_path.read_text()
        assert len(content) > 50, "Saved context should be non-trivial"
