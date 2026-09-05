#!/usr/bin/env python3
"""
memory_engine.py — Многоуровневая память Buffy Project.

5 уровней памяти (от быстрой к постоянной):

┌──────────────────────────────────────────────┐
│        1. WORKING (текущая задача)           │
│  - последние сообщения, активный план        │
├──────────────────────────────────────────────┤
│        2. PROJECT (история проекта)          │
│  - ADR, документация, TASK, ROADMAP          │
├──────────────────────────────────────────────┤
│        3. KNOWLEDGE (знания)                 │
│  - RAG, книги, best practices, ссылки        │
├──────────────────────────────────────────────┤
│        4. PERSONAL (личное)                  │
│  - предпочтения пользователя, стиль кода     │
├──────────────────────────────────────────────┤
│        5. ARCHIVE (архив)                    │
│  - старые проекты, полные логи, чекпоинты    │
└──────────────────────────────────────────────┘

Каждый уровень хранится как JSON-файлы в context_12/memory/<level>/.
Это делает память прозрачной, редактируемой и бэкапируемой.

Использование:
    from scripts_01.memory_engine import MemoryEngine, MemoryLevel

    engine = MemoryEngine()
    engine.store(MemoryLevel.WORKING, "current_task", "Рефакторинг TUI")
    entry = engine.retrieve(MemoryLevel.WORKING, "current_task")
    ctx = engine.build_context(levels=[MemoryLevel.WORKING, MemoryLevel.PROJECT***REMOVED***)
    print(ctx)  # => строка для инжекта в промпт
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
***REMOVED***
from typing import Any, Dict, List, Optional

from scripts_01.event_bus import Event

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


class MemoryLevel(str, Enum):
    """Уровни памяти — от быстрой к постоянной."""
    WORKING = "working"       # текущая задача, краткосрочная
    PROJECT = "project"       # проект: ADR, доки, TASK
    KNOWLEDGE = "knowledge"   # база знаний: RAG, книги, best practices
    PERSONAL = "personal"     # личные предпочтения пользователя
    ARCHIVE = "archive"       # архив: старые проекты, логи


class ContentType(str, Enum):
    """Тип содержимого MemoryEntry."""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    CODE = "code"
    YAML = "yaml"


@dataclass
class MemoryEntry:
    """Одна запись в памяти."""
    level: MemoryLevel
    key: str
    content: str
    content_type: ContentType = ContentType.TEXT
    summary: str = ""                     # краткое описание (для build_context)
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12***REMOVED***)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        """Конвертирует строки в enum при десериализации из JSON."""
        if isinstance(self.level, str):
            self.level = MemoryLevel(self.level)
        if isinstance(self.content_type, str):
            self.content_type = ContentType(self.content_type)


# ═══════════════════════════════════════════════════════════════
# MemoryEngine
# ═══════════════════════════════════════════════════════════════


class MemoryEngine:
    """Многоуровневая память для Buffy Project.

    Каждый уровень хранится как JSON-файлы в:
        FREEBUFF_ROOT/context_12/memory/<level>/<key>.json

    Особенности:
    - Thread-safe через threading.Lock
    - Авто-создание директорий
    - build_context() собирает все уровни в промпт
    - Поиск по ключам и метаданным
    - EventBus: публикует memory.stored, memory.deleted, memory.cleared
    """

    def __init__(self, workspace_root: str | Path | None = None, event_bus: Any = None):
        if workspace_root is None:
            workspace_root = PROJECT_ROOT
        self._root = Path(workspace_root)
        self._memory_dir = self._root / "context_12" / "memory"

        # Создаём директории для всех уровней
        for level in MemoryLevel:
            (self._memory_dir / level.value).mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        # EventBus must be explicitly injected. We do NOT auto-create a default
        # bus here to avoid surprising side effects and resource leaks in tests.
        self._event_bus = event_bus  # Optional EventBus instance

    # ── Пути ──────────────────────────────────────────────────

    def _level_dir(self, level: MemoryLevel) -> Path:
        """Возвращает путь к директории уровня памяти."""
        return self._memory_dir / level.value

    def _entry_path(self, level: MemoryLevel, key: str) -> Path:
        """Возвращает путь к файлу записи."""
        return self._level_dir(level) / f"{key***REMOVED***.json"

    def _key_from_path(self, path: Path) -> str:
        """Извлекает key из пути к файлу."""
        return path.stem

    # ── CRUD ──────────────────────────────────────────────────

    def store(
        self,
        level: MemoryLevel,
        key: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        summary: str = "",
        metadata: Dict[str, Any***REMOVED*** | None = None,
        overwrite: bool = True,
    ) -> MemoryEntry:
        """Сохраняет запись в память.

        Args:
            level: уровень памяти
            key: уникальный ключ (латиница, цифры, подчёркивания)
            content: содержимое
            content_type: тип содержимого
            summary: краткое описание для build_context
            metadata: произвольные метаданные (теги, source, importance)
            overwrite: перезаписывать если существует

        Returns:
            MemoryEntry (созданная или обновлённая)
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            filepath = self._entry_path(level, key)
            existing = None

            if filepath.exists():
                try:
                    existing = json.loads(filepath.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass

                if not overwrite:
                    raise FileExistsError(
                        f"Entry already exists: {level.value***REMOVED***/{key***REMOVED***. "
                        "Use overwrite=True to replace."
                    )

            entry = MemoryEntry(
                level=level,
                key=key,
                content=content,
                content_type=content_type,
                summary=summary or content[:200***REMOVED***.replace("\n", " "),
                metadata=metadata or {***REMOVED***,
                id=existing["id"***REMOVED*** if existing else uuid.uuid4().hex[:12***REMOVED***,
                created_at=existing["created_at"***REMOVED*** if existing else now,
                updated_at=now,
            )

            filepath.write_text(
                json.dumps(asdict(entry), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        # Публикуем событие ВНЕ блокировки (handler может вызвать subscribe)
        if self._event_bus is not None:
            try:
                self._event_bus.publish(Event(
                    type="memory.stored",
                    source="memory_engine",
                    data={
                        "level": entry.level.value,
                        "key": entry.key,
                        "content_type": entry.content_type.value,
                        "content": entry.content,
                        "summary": entry.summary[:200***REMOVED***,
                        "is_update": existing is not None,
                        "workspace_root": str(self._root),
                    ***REMOVED***,
                ))
            except Exception:
                pass

        return entry

    def retrieve(self, level: MemoryLevel, key: str) -> MemoryEntry | None:
        """Читает запись из памяти.

        Args:
            level: уровень памяти
            key: ключ записи

        Returns:
            MemoryEntry или None если не найдено
        """
        filepath = self._entry_path(level, key)
        if not filepath.exists():
            return None

        with self._lock:
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                return MemoryEntry(**data)
            except (json.JSONDecodeError, OSError, KeyError):
                return None

    def delete(self, level: MemoryLevel, key: str) -> bool:
        """Удаляет запись из памяти.

        Returns:
            True если удалено, False если не найдено.
        """
        filepath = self._entry_path(level, key)
        if not filepath.exists():
            return False

        with self._lock:
            try:
                filepath.unlink()
                deleted = True
            except OSError:
                return False

        if deleted and self._event_bus is not None:
            try:
                self._event_bus.publish(Event(
                    type="memory.deleted",
                    source="memory_engine",
                    data={"level": level.value, "key": key***REMOVED***,
                ))
            except Exception:
                pass

        return True

    def list_entries(
        self,
        level: MemoryLevel | None = None,
        filter_metadata: Dict[str, Any***REMOVED*** | None = None,
    ) -> List[MemoryEntry***REMOVED***:
        """Список записей, опционально фильтрованных.

        Args:
            level: если указан — только этот уровень
            filter_metadata: фильтр по метаданным (например {"importance": "high"***REMOVED***)

        Returns:
            Список MemoryEntry, сортированный по updated_at (сначала новые).
        """
        levels = [level***REMOVED*** if level else list(MemoryLevel)
        entries: List[MemoryEntry***REMOVED*** = [***REMOVED***

        with self._lock:
            for lvl in levels:
                dirpath = self._level_dir(lvl)
                if not dirpath.exists():
                    continue
                for fpath in sorted(dirpath.iterdir()):
                    if fpath.suffix != ".json":
                        continue
                    try:
                        data = json.loads(fpath.read_text(encoding="utf-8"))
                        entry = MemoryEntry(**data)

                        # Фильтр по метаданным
                        if filter_metadata:
                            matches = all(
                                entry.metadata.get(k) == v
                                for k, v in filter_metadata.items()
                            )
                            if not matches:
                                continue

                        entries.append(entry)
                    except (json.JSONDecodeError, OSError, KeyError):
                        continue

        # Сортируем: сначала обновлённые
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries

    def search(
        self,
        query: str,
        level: MemoryLevel | None = None,
        case_sensitive: bool = False,
    ) -> List[MemoryEntry***REMOVED***:
        """Поиск по содержимому и ключам (простой substring match).

        Для полноценного FTS используйте Knowledge Engine (Phase 2).

        Args:
            query: строка поиска
            level: если указан — только этот уровень
            case_sensitive: учитывать регистр

        Returns:
            Список подходящих MemoryEntry.
        """
        entries = self.list_entries(level=level)

        if not case_sensitive:
            query = query.lower()

        results = [***REMOVED***
        for entry in entries:
            haystack = f"{entry.key***REMOVED*** {entry.content***REMOVED*** {entry.summary***REMOVED***"
            if not case_sensitive:
                haystack = haystack.lower()

            if query in haystack:
                results.append(entry)

        return results

    # ── Контекст для промпта ──────────────────────────────────

    def build_context(
        self,
        levels: List[MemoryLevel***REMOVED*** | None = None,
        max_tokens: int = 4000,
        include_summary_only: bool = False,
    ) -> str:
        """Собирает унифицированный контекст для инжекта в промпт.

        Args:
            levels: какие уровни включить (по умолчанию все, кроме ARCHIVE)
            max_tokens: максимальное количество токенов в результате
            include_summary_only: True = только summary, False = полный content

        Returns:
            Строка с контекстом для вставки в начало промпта.
        """
        if levels is None:
            levels = [
                MemoryLevel.WORKING,
                MemoryLevel.PROJECT,
                MemoryLevel.KNOWLEDGE,
                MemoryLevel.PERSONAL,
            ***REMOVED***

        sections: List[str***REMOVED*** = [***REMOVED***
        estimated_tokens = 0
        token_budget = max_tokens

        for level in levels:
            entries = self.list_entries(level=level)
            if not entries:
                continue

            level_lines: List[str***REMOVED*** = [***REMOVED***
            level_lines.append(f"## {level.value.upper()***REMOVED*** MEMORY")
            level_lines.append("")

            for entry in entries:
                if include_summary_only and entry.summary:
                    text = entry.summary
                else:
                    text = entry.content

                # Обрезаем очень длинные записи
                if len(text) > 2000:
                    text = text[:2000***REMOVED*** + "\n... (truncated)"

                level_lines.append(f"### {entry.key***REMOVED***")
                if entry.summary and not include_summary_only:
                    level_lines.append(f"_{entry.summary***REMOVED***_")
                level_lines.append("")
                level_lines.append(text)
                level_lines.append("")

            section = "\n".join(level_lines)
            section_tokens = len(section) // 4

            if estimated_tokens + section_tokens > token_budget:
                # Обрезаем секцию до остатка бюджета
                remaining_chars = (token_budget - estimated_tokens) * 4
                if remaining_chars > 100:
                    section = section[:remaining_chars***REMOVED*** + "\n... (context truncated)"
                    sections.append(section)
                break

            sections.append(section)
            estimated_tokens += section_tokens

        if not sections:
            return ""

        header = (
            "═══════════════════════════════════════════════\n"
            " CONTEXT: BUFFY MEMORY (auto-injected)\n"
            f" Levels: {', '.join(l.value for l in levels)***REMOVED***\n"
            "═══════════════════════════════════════════════\n\n"
        )

        return header + "\n".join(sections)

    # ── Утилиты ───────────────────────────────────────────────

    def wipe_level(self, level: MemoryLevel) -> int:
        """Очищает уровень памяти (удаляет все JSON-файлы).

        Returns:
            Количество удалённых файлов.
        """
        count = 0
        with self._lock:
            dirpath = self._level_dir(level)
            if dirpath.exists():
                for fpath in dirpath.iterdir():
                    if fpath.suffix == ".json":
                        try:
                            fpath.unlink()
                            count += 1
                        except OSError:
                            pass

        if count > 0 and self._event_bus is not None:
            try:
                self._event_bus.publish(Event(
                    type="memory.cleared",
                    source="memory_engine",
                    data={"level": level.value, "count": count***REMOVED***,
                ))
            except Exception:
                pass

        return count

    def count_entries(self, level: MemoryLevel | None = None) -> int:
        """Количество записей в указанном (или всех) уровне."""
        return len(self.list_entries(level=level))

    def get_stats(self) -> Dict[str, Any***REMOVED***:
        """Статистика по всем уровням памяти."""
        stats: Dict[str, Any***REMOVED*** = {***REMOVED***
        for level in MemoryLevel:
            entries = self.list_entries(level=level)
            total_chars = sum(len(e.content) for e in entries)
            stats[level.value***REMOVED*** = {
                "count": len(entries),
                "total_chars": total_chars,
                "keys": [e.key for e in entries***REMOVED***,
            ***REMOVED***
        stats["total"***REMOVED*** = sum(v["count"***REMOVED*** for v in stats.values())
        return stats


# ═══════════════════════════════════════════════════════════════
# CLI для тестирования
# ═══════════════════════════════════════════════════════════════

def main():
    """CLI для работы с Memory Engine."""
    import argparse

    parser = argparse.ArgumentParser(description="Memory Engine CLI")
    sub = parser.add_subparsers(dest="command")

    # store
    p_store = sub.add_parser("store", help="Сохранить запись")
    p_store.add_argument("level", choices=[l.value for l in MemoryLevel***REMOVED***)
    p_store.add_argument("key", help="Ключ записи")
    p_store.add_argument("content", help="Содержимое")
    p_store.add_argument("--summary", default="", help="Краткое описание")
    p_store.add_argument("--type", dest="content_type",
                         choices=[t.value for t in ContentType***REMOVED***, default="text")

    # retrieve
    p_get = sub.add_parser("get", help="Прочитать запись")
    p_get.add_argument("level", choices=[l.value for l in MemoryLevel***REMOVED***)
    p_get.add_argument("key", help="Ключ записи")

    # list
    p_list = sub.add_parser("list", help="Список записей")
    p_list.add_argument("--level", choices=[l.value for l in MemoryLevel***REMOVED***,
                        help="Фильтр по уровню")

    # search
    p_search = sub.add_parser("search", help="Поиск по содержимому")
    p_search.add_argument("query", help="Строка поиска")
    p_search.add_argument("--level", choices=[l.value for l in MemoryLevel***REMOVED***,
                          help="Фильтр по уровню")

    # delete
    p_del = sub.add_parser("delete", help="Удалить запись")
    p_del.add_argument("level", choices=[l.value for l in MemoryLevel***REMOVED***)
    p_del.add_argument("key", help="Ключ записи")

    # context
    p_ctx = sub.add_parser("context", help="Собрать контекст для промпта")
    p_ctx.add_argument("--levels", nargs="+",
                       choices=[l.value for l in MemoryLevel***REMOVED***,
                       default=[l.value for l in MemoryLevel if l != MemoryLevel.ARCHIVE***REMOVED***)

    # stats
    sub.add_parser("stats", help="Статистика памяти")

    args = parser.parse_args()

    engine = MemoryEngine()

    if args.command == "store":
        entry = engine.store(
            level=MemoryLevel(args.level),
            key=args.key,
            content=args.content,
            content_type=ContentType(args.content_type),
            summary=args.summary,
        )
        print(f"✅ Stored: {entry.level.value***REMOVED***/{entry.key***REMOVED*** (id={entry.id[:8***REMOVED******REMOVED***)")

    elif args.command == "get":
        entry = engine.retrieve(
            level=MemoryLevel(args.level),
            key=args.key,
        )
        if entry:
            print(f"📖 {entry.level.value***REMOVED***/{entry.key***REMOVED***")
            print(f"   ID: {entry.id***REMOVED***")
            print(f"   Type: {entry.content_type.value***REMOVED***")
            print(f"   Created: {entry.created_at[:19***REMOVED******REMOVED***")
            print(f"   Updated: {entry.updated_at[:19***REMOVED******REMOVED***")
            if entry.summary:
                print(f"   Summary: {entry.summary***REMOVED***")
            print(f"   Content ({len(entry.content)***REMOVED*** chars):")
            print(entry.content[:500***REMOVED***)
            if len(entry.content) > 500:
                print("   ... (truncated)")
        else:
            print(f"❌ Not found: {args.level***REMOVED***/{args.key***REMOVED***")

    elif args.command == "list":
        level = MemoryLevel(args.level) if args.level else None
        entries = engine.list_entries(level=level)
        if not entries:
            print("📭 No entries")
        else:
            print(f"📋 {len(entries)***REMOVED*** entries:")
            for e in entries:
                print(f"  [{e.level.value***REMOVED******REMOVED*** {e.key***REMOVED*** ({len(e.content)***REMOVED*** chars, "
                      f"{e.updated_at[:16***REMOVED******REMOVED***)")

    elif args.command == "search":
        level = MemoryLevel(args.level) if args.level else None
        results = engine.search(args.query, level=level)
        if not results:
            print("🔍 No results")
        else:
            print(f"🔍 {len(results)***REMOVED*** results for '{args.query***REMOVED***':")
            for e in results[:10***REMOVED***:
                print(f"  [{e.level.value***REMOVED******REMOVED*** {e.key***REMOVED***: {e.summary[:80***REMOVED******REMOVED***")

    elif args.command == "delete":
        ok = engine.delete(level=MemoryLevel(args.level), key=args.key)
        print(f"🗑 {'Deleted' if ok else 'Not found'***REMOVED***: {args.level***REMOVED***/{args.key***REMOVED***")

    elif args.command == "context":
        levels = [MemoryLevel(l) for l in args.levels***REMOVED***
        ctx = engine.build_context(levels=levels)
        print(ctx if ctx else "(empty context)")

    elif args.command == "stats":
        stats = engine.get_stats()
        print("📊 MEMORY STATS")
        print(f"   Total entries: {stats['total'***REMOVED******REMOVED***")
        for level_name, data in stats.items():
            if level_name == "total":
                continue
            print(f"   [{level_name***REMOVED******REMOVED*** {data['count'***REMOVED******REMOVED*** entries, "
                  f"{data['total_chars'***REMOVED******REMOVED*** chars")
            if data['keys'***REMOVED***:
                print(f"            keys: {', '.join(data['keys'***REMOVED***[:5***REMOVED***)***REMOVED***")


if __name__ == "__main__":
    main()
