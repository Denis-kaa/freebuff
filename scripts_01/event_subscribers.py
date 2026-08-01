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
    from scripts_01.event_subscribers ***REMOVED***gister_all

    bus = EventBus()
    register_all(bus, workspace_root=".")
    # Теперь MemoryEngine → KnowledgeEngine автоматически
"""

from __future__ import annotations

***REMOVED***
from typing import Any, Dict

from scripts_01.notification ***REMOVED***gister_notification_subscribers


# ═══════════════════════════════════════════════════════════════
# Cached KnowledgeEngine instances per workspace
# ═══════════════════════════════════════════════════════════════

_KE_CACHE: Dict[str, Any***REMOVED*** = {***REMOVED***

# ═══════════════════════════════════════════════════════════════
# Cached EMEngine instances per workspace
# ═══════════════════════════════════════════════════════════════

_EM_ENGINE_CACHE: Dict[str, Any***REMOVED*** = {***REMOVED***


def _get_em_engine(workspace_root: str) -> "EMEngine":
    """Возвращает кэшированный EMEngine для workspace."""
    from scripts_01.engineering_memory import EMEngine

    key = str(Path(workspace_root).resolve())
    if key not in _EM_ENGINE_CACHE:
        _EM_ENGINE_CACHE[key***REMOVED*** = EMEngine(workspace_root=key)
    return _EM_ENGINE_CACHE[key***REMOVED***


def _should_create_retrospective(data: Dict[str, Any***REMOVED***) -> bool:
    """Определяет, достаточно ли задача значима для автоматического ретроспективы."""
    # Проваленные задачи всегда значимы
    if data.get("status") in ("failed", "error", "Ошибка"):
        return True
    # Длительность > 10 минут
    try:
        duration_seconds = float(data.get("duration_seconds", 0) or 0)
    except (TypeError, ValueError):
        duration_seconds = 0.0
    if duration_seconds >= 600:
        return True
    # LOC > 100
    try:
        loc = int(data.get("loc") or data.get("lines_changed") or 0)
    except (TypeError, ValueError):
        loc = 0
    if loc > 100:
        return True
    return False


def _get_knowledge_engine(workspace_root: str) -> Any:
    """Возвращает кэшированный KnowledgeEngine для workspace."""
    from scripts_01.knowledge_engine import KnowledgeEngine

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

    # Engineering Memory: draft created / finalized / discarded
    def _on_em_draft_created(event):
        try:
            data = event.data
            draft_id = data.get("draft_id", "unknown")
            doc_type = data.get("type", "record")
            title = data.get("title", "")
            print(f"📝 EM draft created: [{doc_type***REMOVED******REMOVED*** {title***REMOVED*** ({draft_id***REMOVED***)")
        except Exception:
            pass

    def _on_em_document_finalized(event):
        try:
            data = event.data
            doc_id = data.get("doc_id", "unknown")
            doc_type = data.get("type", "record")
            title = data.get("title", "")
            path = data.get("path", "")
            print(f"✅ EM document finalized: [{doc_type***REMOVED******REMOVED*** {title***REMOVED*** ({doc_id***REMOVED***) -> {path***REMOVED***")
        except Exception:
            pass

    event_bus.subscribe("em.draft_created", _on_em_draft_created)
    event_bus.subscribe("em.document_finalized", _on_em_document_finalized)

    # Notification system: task/workflow progress, stages, completion, errors
    register_notification_subscribers(event_bus)

    # Engineering Memory auto-triggers: task completed/failed, git.merge, system.error
    _register_em_auto_triggers(event_bus, workspace_root)


def _register_em_auto_triggers(event_bus: Any, workspace_root: str | Path | None) -> None:
    """Регистрирует подписчиков, которые автоматически создают EM-драфты."""
    if not workspace_root:
        return

    root = str(workspace_root)

    def _on_task_completed(event: Any) -> None:
        try:
            if not hasattr(event, "data"):
                return
            data = event.data
            if not _should_create_retrospective(data):
                return

            em = _get_em_engine(root)
            task_id = str(data.get("task_id") or data.get("task_name") or "unknown")
            ref = f"task_completed_{task_id***REMOVED***"
            if em.has_auto_trigger(ref):
                return

            draft_id = em.record_task_retrospective(
                title=f"Ретроспектива: {data.get('task_name', task_id)***REMOVED***",
                intent=data.get("intent") or data.get("goal") or "(авто-триггер)",
                reality=data.get("details") or data.get("result") or "(завершено)",
                friction=data.get("friction", ""),
                discoveries=data.get("discoveries", ""),
                follow_ups=data.get("follow_ups", ""),
                tags=["auto-trigger", "retrospective", "task"***REMOVED***,
                related_tasks=[task_id***REMOVED***,
            )
            em.set_auto_trigger(ref)
            print(f" Auto EM draft created: task retrospective ({draft_id***REMOVED***)")
        except Exception as exc:
            print(f"⚠️ EM auto-trigger task.completed: {exc***REMOVED***")

    def _on_task_failed(event: Any) -> None:
        try:
            if not hasattr(event, "data"):
                return
            data = event.data
            em = _get_em_engine(root)
            task_id = str(data.get("task_id") or data.get("task_name") or "unknown")
            ref = f"task_failed_{task_id***REMOVED***"
            if em.has_auto_trigger(ref):
                return

            draft_id = em.record_incident(
                title=f"Инцидент: {data.get('task_name', task_id)***REMOVED***",
                summary=f"Задача {task_id***REMOVED*** завершилась ошибкой",
                root_cause=data.get("error") or data.get("root_cause") or "(неизвестно)",
                resolution=data.get("resolution") or "(требует анализа)",
                prevention=data.get("prevention", ""),
                tags=["auto-trigger", "incident", "task"***REMOVED***,
                related_tasks=[task_id***REMOVED***,
            )
            em.set_auto_trigger(ref)
            print(f" Auto EM draft created: incident from task failure ({draft_id***REMOVED***)")
        except Exception as exc:
            print(f"⚠️ EM auto-trigger task.failed: {exc***REMOVED***")

    def _on_git_merge(event: Any) -> None:
        try:
            if not hasattr(event, "data"):
                return
            data = event.data
            em = _get_em_engine(root)
            branch = str(data.get("branch") or data.get("ref") or "unknown")
            ref = f"git_merge_{branch***REMOVED***"
            if em.has_auto_trigger(ref):
                return

            draft_id = em.record_task_retrospective(
                title=f"Merge: {branch***REMOVED***",
                intent=data.get("intent") or f"Объединить ветку {branch***REMOVED***",
                reality=data.get("details") or f"Merge завершён: {branch***REMOVED***",
                friction=data.get("friction", ""),
                discoveries=data.get("discoveries", ""),
                follow_ups=data.get("follow_ups", ""),
                tags=["auto-trigger", "git", "merge"***REMOVED***,
                related_commits=[data.get("commit", "")***REMOVED*** if data.get("commit") else [***REMOVED***,
            )
            em.set_auto_trigger(ref)
            print(f"📝 Auto EM draft created: merge retrospective ({draft_id***REMOVED***)")
        except Exception as exc:
            print(f"⚠️ EM auto-trigger git.merge: {exc***REMOVED***")

    def _on_system_error(event: Any) -> None:
        try:
            if not hasattr(event, "data"):
                return
            data = event.data
            em = _get_em_engine(root)
            error_id = str(data.get("error_id") or data.get("component") or "system")
            ref = f"system_error_{error_id***REMOVED***"
            if em.has_auto_trigger(ref):
                return

            draft_id = em.record_incident(
                title=f"Системная ошибка: {error_id***REMOVED***",
                summary=data.get("summary") or data.get("message") or "(авто-триггер)",
                root_cause=data.get("root_cause") or data.get("error") or "(неизвестно)",
                resolution=data.get("resolution") or "(требует анализа)",
                impact=data.get("impact", ""),
                tags=["auto-trigger", "incident", "system"***REMOVED***,
                related_components=[error_id***REMOVED***,
            )
            em.set_auto_trigger(ref)
            print(f"📝 Auto EM draft created: system error incident ({draft_id***REMOVED***)")
        except Exception as exc:
            print(f"⚠️ EM auto-trigger system.error: {exc***REMOVED***")

    event_bus.subscribe("task.completed", _on_task_completed)
    event_bus.subscribe("task.failed", _on_task_failed)
    event_bus.subscribe("git.merge", _on_git_merge)
    event_bus.subscribe("system.error", _on_system_error)
