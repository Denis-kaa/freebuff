"""
knowledge_sync — Knowledge Sync Plugin для Buffy.

Функции:
  - sync: синхронизация MemoryEngine → KnowledgeEngine
  - stats: статистика синхронизации
  - force_reindex: полная перестройка индекса знаний
  - status: статус плагина
  - Авто-синхронизация при memory.stored / memory.deleted событиях
"""

import json
import threading
import time
***REMOVED***

from scripts_01.plugin_api import BasePlugin, PluginMeta, PluginResult

try:
    from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType

    _has_memory = True
except ImportError:
    _has_memory = False

try:
    from scripts_01.knowledge_engine import KnowledgeEngine

    _has_knowledge = True
except ImportError:
    _has_knowledge = False


class KnowledgeSyncPlugin(BasePlugin):
    """Синхронизация между Memory Engine и Knowledge Engine."""

    def __init__(self):
        super().__init__(
            name="knowledge_sync",
            version="1.0.0",
            description="Knowledge Sync — синхронизация между Memory Engine и Knowledge Engine",
        )
        self._memory_engine = None
        self._knowledge_engine = None
        self._sync_lock = threading.Lock()
        self._sync_stats = {
            "total_synced": 0,
            "errors": 0,
            "last_sync": None,
            "synced_levels": [***REMOVED***,
        ***REMOVED***

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name=self._name,
            version=self._version,
            description=self._description,
            events_subscribed=self.events_subscribed,
        )

    @property
    def events_subscribed(self):
        return ["memory.stored", "memory.deleted", "knowledge.*"***REMOVED***

    # ── Lifecycle ───────────────────────────────────────────

    def on_load(self):
        print(
            f"🧠 knowledge_sync: loaded (memory={_has_memory***REMOVED***, knowledge={_has_knowledge***REMOVED***)"
        )

    def on_unload(self):
        self._memory_engine = None
        self._knowledge_engine = None

    # ── Accessors (lazy init) ──────────────────────────────

    def _get_memory(self):
        """Lazy init MemoryEngine."""
        if self._memory_engine is None and _has_memory:
            try:
                self._memory_engine = MemoryEngine()
            except Exception as e:
                print(f"🧠 knowledge_sync: MemoryEngine init failed: {e***REMOVED***")
        return self._memory_engine

    def _get_knowledge(self):
        """Lazy init KnowledgeEngine."""
        if self._knowledge_engine is None and _has_knowledge:
            try:
                self._knowledge_engine = KnowledgeEngine()
            except Exception as e:
                print(f"📚 knowledge_sync: KnowledgeEngine init failed: {e***REMOVED***")
        return self._knowledge_engine

    # ── Действия ───────────────────────────────────────────

    def do_sync(self, levels: str = "all") -> dict:
        """Синхронизирует Memory Engine → Knowledge Engine.

        Args:
            levels: какие уровни синхронизировать (через запятую) или 'all'

        Returns:
            dict с success и количеством синхронизированных записей
        """
        mem = self._get_memory()
        knw = self._get_knowledge()
        missing = [***REMOVED***
        if mem is None:
            missing.append("MemoryEngine")
        if knw is None:
            missing.append("KnowledgeEngine")
        if missing:
            return {
                "success": False,
                "error": "Required engines not available: " + ", ".join(missing),
            ***REMOVED***

        try:
            if levels == "all":
                target_levels = [l for l in MemoryLevel***REMOVED***
            else:
                level_names = [n.strip() for n in levels.split(",")***REMOVED***
                target_levels = [***REMOVED***
                for name in level_names:
                    try:
                        target_levels.append(MemoryLevel(name))
                    except ValueError:
                        return {
                            "success": False,
                            "error": f"Unknown level: {name***REMOVED***",
                        ***REMOVED***

            results = {***REMOVED***
            total = 0
            errors = 0
            synced_levels = [***REMOVED***
            for level in target_levels:
                try:
                    entries = mem.list_entries(level=level)
                    synced = 0
                    for entry in entries:
                        try:
                            doc_id = f"{entry.key***REMOVED***:{level.value***REMOVED***"
                            metadata = {
                                "source": "memory_engine",
                                "level": level.value,
                                "key": entry.key,
                                "summary": getattr(entry, "summary", ""),
                                "content_type": (
                                    entry.content_type.value
                                    if hasattr(entry, "content_type")
                                    and hasattr(entry.content_type, "value")
                                    else str(getattr(entry, "content_type", ""))
                                ),
                            ***REMOVED***
                            knw.add_document(
                                doc_id=doc_id,
                                content=entry.content,
                                metadata=metadata,
                            )
                            synced += 1
                        except Exception:
                            errors += 1
                    results[level.value***REMOVED*** = {"total": len(entries), "synced": synced, "errors": errors***REMOVED***
                    total += synced
                    synced_levels.append(level.value)
                except Exception:
                    errors += 1

            try:
                knw.rebuild_index()
            except Exception as e:
                return {"success": False, "error": f"Index rebuild failed: {e***REMOVED***"***REMOVED***

            with self._sync_lock:
                self._sync_stats["total_synced"***REMOVED*** += total
                self._sync_stats["last_sync"***REMOVED*** = str(__import__("datetime").datetime.now())
                self._sync_stats["errors"***REMOVED*** += errors
                self._sync_stats["synced_levels"***REMOVED*** = synced_levels

            return {
                "success": True, "data_13": {
                    "total_synced": total,
                    "errors": errors,
                    "levels": results,
                ***REMOVED***,
            ***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_stats(self) -> dict:
        """Детальная статистика синхронизации."""
        return {
            "success": True, "data_13": {
                "memory_levels": self._get_memory_levels_stats(),
                **self._sync_stats,
            ***REMOVED***,
        ***REMOVED***

    def do_force_reindex(self) -> dict:
        """Полная перестройка индекса знаний.

        Удаляет все документы из KnowledgeEngine и переиндексирует
        их заново из MemoryEngine.
        """
        knw = self._get_knowledge()
        if knw is None:
            return {"success": False, "error": "KnowledgeEngine not available"***REMOVED***
        try:
            knw.rebuild_index()
            return {"success": True, "data_13": "Knowledge index rebuilt"***REMOVED***
        except Exception as e:
            return {"success": False, "error": str(e)***REMOVED***

    def do_status(self) -> dict:
        """Статус плагина и статистика синхронизации."""
        mem = self._get_memory()
        knw = self._get_knowledge()
        status = {
            "name": self._name,
            "enabled": self._enabled,
            "memory_available": mem is not None,
            "knowledge_available": knw is not None,
            "sync_stats": self._sync_stats,
        ***REMOVED***
        level_counts = {***REMOVED***
        if mem is not None:
            try:
                for level in MemoryLevel:
                    entries = mem.list_entries(level=level)
                    level_counts[level.value***REMOVED*** = len(entries)
            except Exception:
                pass
        return {"success": True, "data_13": {**status, "memory_levels": level_counts***REMOVED******REMOVED***

    # ── Внутреннее ─────────────────────────────────────────

    def _get_memory_levels_stats(self) -> dict:
        """Возвращает количество записей по уровням памяти."""
        mem = self._get_memory()
        if mem is None:
            return {***REMOVED***
        counts = {***REMOVED***
        try:
            for level in MemoryLevel:
                counts[level.value***REMOVED*** = len(mem.list_entries(level=level))
        except Exception:
            return {***REMOVED***
        return counts

    def _sync_single_entry(self, level: str, key: str):
        """Синхронизирует одну запись памяти в KnowledgeEngine."""
        try:
            mem = self._get_memory()
            knw = self._get_knowledge()
            if mem is None or knw is None:
                return
            mem_level = MemoryLevel(level)
            entry = mem.retrieve(key=key, level=mem_level)
            if entry is None:
                return
            doc_id = f"{key***REMOVED***:{level***REMOVED***"
            knw.add_document(
                doc_id=doc_id,
                content=entry.content,
                metadata={
                    "source": "memory_engine",
                    "level": level,
                    "key": key,
                    "summary": getattr(entry, "summary", ""),
                ***REMOVED***,
            )
            with self._sync_lock:
                self._sync_stats["total_synced"***REMOVED*** += 1
        except Exception:
            with self._sync_lock:
                self._sync_stats["errors"***REMOVED*** += 1

    def on_event(self, event):
        """Авто-синхронизация при событиях памяти."""
        try:
            event_type = getattr(event, "type", "")
            event_data = getattr(event, "data_13", {***REMOVED***) or {***REMOVED***
            if event_type == "memory.stored":
                level = event_data.get("level", "")
                key = event_data.get("key", "")
                self._sync_single_entry(level, key)
            elif event_type == "memory.deleted":
                key = event_data.get("key", "")
                knw = self._get_knowledge()
                if knw is not None:
                    try:
                        knw.delete_document(key)
                    except Exception:
                        pass
        except Exception:
            pass


# Экземпляр плагина (обнаруживается PluginLoader по переменной `plugin`)
plugin = KnowledgeSyncPlugin()
