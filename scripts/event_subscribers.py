#!/usr/bin/env python3
"""
event_subscribers.py — Подписчики событий для Buffy EventBus.

Связывает компоненты через события, а не прямые вызовы:

  MemoryEngine.store() → pub(memory.stored)
    ↓
  auto_index_subscriber → KnowledgeEngine.index_document()

  ContextManager.save_checkpoint() → pub(checkpoint.created)
    ↓
  checkpoint_logger → логирование в файл

Использование:
    from scripts.event_subscribers ***REMOVED***gister_all

    bus = EventBus()
    register_all(bus, workspace_root=".")
    # Теперь MemoryEngine → KnowledgeEngine автоматически
"""

from __future__ import annotations

***REMOVED***
from typing import Any, Dict


# ═══════════════════════════════════════════════════════════════
# Cached KnowledgeEngine instances per workspace
# ═══════════════════════════════════════════════════════════════

_KE_CACHE: Dict[str, Any***REMOVED*** = {***REMOVED***


def _get_knowledge_engine(workspace_root: str) -> Any:
    """Возвращает кэшированный KnowledgeEngine для workspace."""
    from scripts.knowledge_engine import KnowledgeEngine

    key = str(Path(workspace_root).resolve())
    if key not in _KE_CACHE:
        _KE_CACHE[key***REMOVED*** = KnowledgeEngine(workspace_root=key)
    return _KE_CACHE[key***REMOVED***


def auto_index_subscriber(event: Any) -> None:
    """Подписчик: memory.stored → автоматическая индексация в KnowledgeEngine.

    При сохранении записи в MemoryEngine автоматически индексирует
    её содержимое в Knowledge Engine (FTS5 + TF-IDF).
    """
    try:
        if not hasattr(event, "data"):
            return

        data = event.data
        level = data.get("level", "")
        key = data.get("key", "")
        content_type = data.get("content_type", "text")
        content = data.get("content", "")
        workspace_root = data.get("workspace_root", "")

        # Пропускаем личные и архивные записи (они не для общего поиска)
        if level in ("personal", "archive"):
            return

        if not content or not workspace_root:
            return

        doc_id = f"mem_{level***REMOVED***_{key***REMOVED***"
        ke = _get_knowledge_engine(workspace_root)
        ke.index_document(
            doc_id=doc_id,
            content=content,
            metadata={
                "title": key,
                "source": f"memory/{level***REMOVED***/{key***REMOVED***",
                "doc_type": content_type,
            ***REMOVED***,
        )
    except Exception as e:
        print(f"⚠️ Auto-index: {e***REMOVED***")


def checkpoint_logger(event: Any) -> None:
    """Подписчик: checkpoint.created → запись в лог-файл."""
    try:
        if not hasattr(event, "data"):
            return
        data = event.data
        cp_type = data.get("checkpoint_type", "unknown")
        summary = data.get("summary", "")[:100***REMOVED***
        print(f"📝 Checkpoint [{cp_type***REMOVED******REMOVED***: {summary***REMOVED***...")
    except Exception:
        pass


# Глобальный workspace_root для подписчиков (опционально)
_WORKSPACE_ROOT: Path | None = None


def register_all(event_bus: Any, workspace_root: str | Path | None = None) -> None:
    """Регистрирует всех стандартных подписчиков.

    Args:
        event_bus: экземпляр EventBus
        workspace_root: корень workspace (для KnowledgeEngine)
    """
    global _WORKSPACE_ROOT
    if workspace_root:
        _WORKSPACE_ROOT = Path(workspace_root)

    # Auto-index: memory.stored → KnowledgeEngine
    event_bus.subscribe("memory.stored", auto_index_subscriber)

    # Checkpoint logger
    event_bus.subscribe("checkpoint.created", checkpoint_logger)

    # Memory cleared → knowledge rebuild hint
    def _on_memory_cleared(event):
        try:
            data = event.data
            level = data.get("level", "")
            if level in ("knowledge", "project"):
                print(f"📚 Memory '{level***REMOVED***' cleared — consider rebuilding knowledge index")
        except Exception:
            pass

    event_bus.subscribe("memory.cleared", _on_memory_cleared)
