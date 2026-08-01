#!/usr/bin/env python3
"""
context_builder.py — Unified Context для Buffy.

Собирает динамический контекст из всех источников перед каждым запросом:
  Memory Engine (все уровни, кроме ARCHIVE)
  + TASK.md, CHANGELOG.md, ADR index (docs_10/decisions/DECISIONS.md)
  + StreamBridge (последний конспект сессии)

Результат → Unified Context → инжект в промпт модели.

Использование:
    python scripts_01/context_builder.py                 # полный контекст в stdout
    python scripts_01/context_builder.py --levels working,project  # только указанные уровни
    python scripts_01/context_builder.py --save unified_context.md  # сохранить в файл
    python scripts_01/context_builder.py --status       # статистика контекста
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
***REMOVED***
from typing import Dict, List, Optional, Any

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.memory_engine import MemoryEngine, MemoryLevel
from scripts_01.stream_bridge import StreamBridge


# ═══════════════════════════════════════════════════════════════
# Context Builder
# ═══════════════════════════════════════════════════════════════

class ContextBuilder:
    """Собирает Unified Context для инжекта в промпт Buffy.

    Источники (в порядке приоритета):
    1. Working Memory — текущая задача (Memory Engine)
    2. Project Memory — ADR, доки, TASK (Memory Engine)
    3. Knowledge Memory — RAG, знания (Memory Engine)
    4. Personal Memory — предпочтения пользователя (Memory Engine)
    5. TASK.md — текущая задача
    6. CHANGELOG.md — последние изменения
    7. StreamBridge — последний конспект сессии
    """

    def __init__(self, max_tokens: int = 6000, workspace_root: Path | str | None = None):
        ws = Path(workspace_root) if workspace_root else WORKSPACE
        self._workspace = ws
        self._memory = MemoryEngine(workspace_root=str(ws))
        self._max_tokens = max_tokens
        self._bridge: Optional[StreamBridge***REMOVED*** = None

    @property
    def bridge(self) -> Optional[StreamBridge***REMOVED***:
        if self._bridge is None:
            try:
                self._bridge = StreamBridge(auto_bootstrap=True, run_gc=False)
            except Exception:
                self._bridge = None
        return self._bridge

    # ── Сбор контекста ─────────────────────────────────────

    def build(
        self,
        levels: Optional[List[str***REMOVED******REMOVED*** = None,
        include_task: bool = True,
        include_changelog: bool = True,
        include_session: bool = True,
    ) -> str:
        """Собирает Unified Context из всех источников.

        Args:
            levels: какие уровни Memory Engine включить
                (по умолчанию: working, project, knowledge, personal)
            include_task: включить TASK.md
            include_changelog: включить CHANGELOG.md
            include_session: включить последний конспект сессии

        Returns:
            Unified Context — строка для инжекта в начало промпта.
        """
        sections: List[str***REMOVED*** = [***REMOVED***
        estimated_tokens = 0
        budget = self._max_tokens

        # 1-4. Memory Engine
        mem_levels = self._parse_levels(levels)
        mem_context = self._memory.build_context(
            levels=mem_levels,
            max_tokens=budget,
            include_summary_only=False,
        )
        if mem_context:
            sections.append(mem_context)
            estimated_tokens += len(mem_context) // 4

        # 5. TASK.md
        if include_task and estimated_tokens < budget:
            task_section = self._read_task_file()
            if task_section:
                task_tokens = len(task_section) // 4
                if estimated_tokens + task_tokens <= budget:
                    sections.append(task_section)
                    estimated_tokens += task_tokens

        # 6. CHANGELOG.md (последние 3 записи)
        if include_changelog and estimated_tokens < budget:
            changelog_section = self._read_changelog()
            if changelog_section:
                cl_tokens = len(changelog_section) // 4
                if estimated_tokens + cl_tokens <= budget:
                    sections.append(changelog_section)
                    estimated_tokens += cl_tokens

        # 7. Session конспект (StreamBridge)
        if include_session and estimated_tokens < budget:
            session_section = self._read_session_conspect()
            if session_section:
                ss_tokens = len(session_section) // 4
                if estimated_tokens + ss_tokens <= budget:
                    sections.append(session_section)

        if not sections:
            return ""

        # Склеиваем
        header = (
            "╔══════════════════════════════════════════════════════╗\n"
            "║          UNIFIED CONTEXT — BUFFY PROJECT           ║\n"
            f"║  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'):>37***REMOVED*** ║\n"
            "╚══════════════════════════════════════════════════════╝\n\n"
        )

        return header + "\n\n---\n\n".join(sections)

    # ── Источники ───────────────────────────────────────────

    def _parse_levels(
        self, levels: Optional[List[str***REMOVED******REMOVED***
    ) -> List[MemoryLevel***REMOVED***:
        if levels:
            return [MemoryLevel(l) for l in levels***REMOVED***
        return [
            MemoryLevel.WORKING,
            MemoryLevel.PROJECT,
            MemoryLevel.KNOWLEDGE,
            MemoryLevel.PERSONAL,
        ***REMOVED***

    def _read_file(self, path: Path, max_lines: int = 100) -> str:
        """Читает файл и возвращает содержимое (первые max_lines строк)."""
        if not path.exists():
            return ""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            return "\n".join(lines[:max_lines***REMOVED***)
        except Exception:
            return ""

    def _read_task_file(self) -> str:
        """Читает TASK.md."""
        task_path = self._workspace / "TASK.md"
        if not task_path.exists():
            return ""
        content = self._read_file(task_path, max_lines=80)
        if not content:
            return ""
        return (
            "## 📋 TASK — текущая задача\n\n"
            f"{content***REMOVED***\n"
        )

    def _read_changelog(self) -> str:
        """Читает последние 3 версии из CHANGELOG.md."""
        changelog_path = self._workspace / "CHANGELOG.md"
        if not changelog_path.exists():
            return ""
        try:
            content = changelog_path.read_text(encoding="utf-8")
            # Берём последние 3 версии (разделитель ---)
            versions = content.split("\n\n---\n\n")
            last_three = versions[-3:***REMOVED*** if len(versions) >= 3 else versions
            result = "\n\n---\n\n".join(last_three)
            if len(result) > 4000:
                result = result[:4000***REMOVED*** + "\n\n... (truncated)"
            return (
                "## 📝 CHANGELOG — последние изменения\n\n"
                f"{result***REMOVED***\n"
            )
        except Exception:
            return ""

    def _read_session_conspect(self) -> str:
        """Читает последний конспект сессии из StreamBridge."""
        try:
            conspect = self.bridge.get_context_resume()
            if conspect and len(conspect) > 50:
                if len(conspect) > 2000:
                    conspect = conspect[:2000***REMOVED*** + "\n\n... (truncated)"
                return (
                    "## 📡 SESSION CONTEXT — последняя сессия\n\n"
                    f"{conspect***REMOVED***\n"
                )
        except Exception:
            return ""
        return ""

    # ── Статус ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any***REMOVED***:
        """Статистика контекста."""
        mem_stats = self._memory.get_stats()
        task_exists = (self._workspace / "TASK.md").exists()
        changelog_exists = (self._workspace / "CHANGELOG.md").exists()

        return {
            "memory": mem_stats,
            "task_exists": task_exists,
            "changelog_exists": changelog_exists,
            "sources": {
                "memory_levels": [l.value for l in self._parse_levels(None)***REMOVED***,
                "task": "TASK.md" if task_exists else None,
                "changelog": "CHANGELOG.md" if changelog_exists else None,
                "session": "StreamBridge" if self._bridge else None,
            ***REMOVED***,
        ***REMOVED***


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Context Builder — сбор Unified Context для Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/context_builder.py                          # полный контекст
  python scripts_01/context_builder.py --levels working,project # только память
  python scripts_01/context_builder.py --save ctx.md            # сохранить в файл
  python scripts_01/context_builder.py --status                 # статистика
  python scripts_01/context_builder.py --no-session             # без сессии
        """,
    )
    parser.add_argument(
        "--levels", default="",
        help="Memory Engine уровни через запятую (working,project,knowledge,personal,archive)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=6000,
        help="Максимум токенов в результате",
    )
    parser.add_argument(
        "--save", default="",
        help="Сохранить контекст в файл (по умолчанию stdout)",
    )
    parser.add_argument(
        "--no-task", action="store_true",
        help="Не включать TASK.md",
    )
    parser.add_argument(
        "--no-changelog", action="store_true",
        help="Не включать CHANGELOG.md",
    )
    parser.add_argument(
        "--no-session", action="store_true",
        help="Не включать конспект сессии",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Показать статистику вместо контекста",
    )

    args = parser.parse_args()

    builder = ContextBuilder(max_tokens=args.max_tokens)

    if args.status:
        status = builder.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return

    # Парсим уровни
    levels = None
    if args.levels:
        levels = [l.strip() for l in args.levels.split(",") if l.strip()***REMOVED***

    # Собираем контекст
    ctx = builder.build(
        levels=levels,
        include_task=not args.no_task,
        include_changelog=not args.no_changelog,
        include_session=not args.no_session,
    )

    if not ctx:
        print("(empty context)")
        return

    # Вывод
    if args.save:
        save_path = Path(args.save)
        save_path.write_text(ctx, encoding="utf-8")
        tokens = len(ctx) // 4
        print(f"✅ Unified Context saved: {save_path***REMOVED***")
        print(f"   Size: {len(ctx)***REMOVED*** chars, ~{tokens***REMOVED*** tokens")
    else:
        print(ctx)


if __name__ == "__main__":
    main()
