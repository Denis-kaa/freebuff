"""
Event Replay — воспроизведение событий из Event Store.

Основание: docs/core/EVENT_PLATFORM_SPECIFICATION.md §4
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from freebuff_plugin.event import EventEntry, EventQuery, ReplayResult, RebuildResult


class EventReplay:
    """Воспроизведение событий из Event Store.

    Позволяет:
    - Воспроизвести события для восстановления состояния
    - Перестроить индекс/компонент из событий
    - Протестировать обработчики на исторических данных
    """

    def __init__(self, store: Any, bus: Optional[Any***REMOVED*** = None):
        """Инициализация.

        Args:
            store: экземпляр EventStore
            bus: опциональный экземпляр EventBus (для реплая через шину)
        """
        self._store = store
        self._bus = bus

    def replay(
        self,
        query: EventQuery,
        handler: Optional[Callable[[EventEntry***REMOVED***, None***REMOVED******REMOVED*** = None,
        speed: str = "instant",
    ) -> ReplayResult:
        """Воспроизвести события, соответствующие запросу.

        Args:
            query: запрос к Event Store
            handler: функция обработчик (если не указан, используется EventBus)
            speed: скорость воспроизведения ("instant", "realtime")

        Returns:
            ReplayResult с статистикой
        """
        events = self._store.query(query)
        result = ReplayResult(total_events=len(events))
        t0 = time.time()

        for event in events:
            try:
                if handler:
                    handler(event)
                    result.delivered += 1
                elif self._bus:
                    # Публикуем через EventBus (конвертируем в Event)
                    from freebuff_plugin.bridge import create_event
                    bus_event = create_event(
                        event_type=event.event_type,
                        data=event.data,
                        source=event.source,
                        id=event.event_id,
                        timestamp=event.timestamp,
                        metadata=event.metadata,
                    )
                    self._bus.publish(bus_event)
                    result.delivered += 1

                if speed == "realtime":
                    time.sleep(0.1)  # Имитация реального времени

            except Exception as e:
                result.errors += 1
                result.errors_list.append(str(e))

        result.duration_ms = round((time.time() - t0) * 1000, 1)
        return result

    def replay_session(self, session_id: str, **kwargs) -> ReplayResult:
        """Воспроизвести все события сессии."""
        return self.replay(
            EventQuery(session_id=session_id, order="asc"),
            **kwargs,
        )

    def replay_workflow(self, correlation_id: str, **kwargs) -> ReplayResult:
        """Воспроизвести все события workflow (task + steps)."""
        return self.replay(
            EventQuery(correlation_id=correlation_id, order="asc"),
            **kwargs,
        )

    def rebuild(
        self,
        target: str,
        snapshot_path: Optional[str***REMOVED*** = None,
        clear_func: Optional[Callable[[***REMOVED***, None***REMOVED******REMOVED*** = None,
        process_func: Optional[Callable[[EventEntry***REMOVED***, None***REMOVED******REMOVED*** = None,
        event_filter: Optional[Callable[[EventEntry***REMOVED***, bool***REMOVED******REMOVED*** = None,
    ) -> RebuildResult:
        """Перестроить состояние компонента из событий.

        Алгоритм:
        1. Snapshot-поиск — проверяет, есть ли сохранённый snapshot
        2. Очистка — существующее состояние удаляется (если нет snapshot)
        3. Воспроизведение — все релевантные события проигрываются
        4. Snapshot — после успешного rebuild создаётся новый snapshot

        Args:
            target: название компонента ("knowledge_engine")
            snapshot_path: путь к файлу snapshot (проверка существования)
            clear_func: функция очистки состояния
            process_func: функция обработки события
            event_filter: фильтр событий (возвращает True если событие релевантно)

        Returns:
            RebuildResult с статистикой
        """
        import json
        import os

        t0 = time.time()
        result = RebuildResult(target=target)

        # 1. Определяем тип событий для target
        event_type_map = {
            "knowledge_engine": "memory.stored",
            "memory_engine": "memory.*",
            "event_bus": "system.*",
        ***REMOVED***
        target_event_type = event_type_map.get(target, f"{target***REMOVED***.*")

        # 2. Проверка snapshot
        snapshot_file = snapshot_path or f"data/{target***REMOVED***.snapshot"
        snapshot_path_obj = self._store._db_path.parent.parent / snapshot_file
        snapshot_loaded = False

        if snapshot_path_obj.exists():
            try:
                snapshot_data = json.loads(snapshot_path_obj.read_text())
                last_event_id = snapshot_data.get("last_event_id", "")
                if last_event_id:
                    # Проверяем, что событие существует
                    last_event = self._store.get_by_id(last_event_id)
                    if last_event:
                        snapshot_loaded = True
                        result.items_created = snapshot_data.get("items_count", 0)
            except Exception:
                pass

        # 3. Получаем события
        events = self._store.query(
            EventQuery(event_type=target_event_type, limit=10000, order="asc")
        )

        if not events:
            result.duration_ms = round((time.time() - t0) * 1000, 1)
            return result

        # 4. Если snapshot не загружен — очищаем и проигрываем все
        if not snapshot_loaded:
            if clear_func:
                try:
                    clear_func()
                except Exception:
                    pass

            processed = 0
            for event in events:
                if event_filter and not event_filter(event):
                    continue
                if process_func:
                    try:
                        process_func(event)
                        processed += 1
                    except Exception:
                        pass
                else:
                    processed += 1

            result.events_processed = len(events)
            result.items_created = processed
        else:
            # Snapshot загружен — инкрементальное восстановление
            result.events_processed = 0
            result.items_created = snapshot_data.get("items_count", 0)

        # 5. Сохраняем snapshot
        if result.events_processed > 0:
            try:
                snapshot_path_obj.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path_obj.write_text(
                    json.dumps({
                        "target": target,
                        "last_event_id": events[-1***REMOVED***.event_id if events else "",
                        "last_timestamp": events[-1***REMOVED***.timestamp if events else "",
                        "events_processed": result.events_processed,
                        "items_count": result.items_created,
                    ***REMOVED***, ensure_ascii=False, indent=2)
                )
            except Exception:
                pass

        result.duration_ms = round((time.time() - t0) * 1000, 1)
        return result
