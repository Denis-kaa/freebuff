#!/usr/bin/env python3
"""
event_bus.py — Event Bus для Buffy DAP.

Публично-подписная шина событий. Все компоненты общаются через события,
а не прямыми вызовами. Это фундамент для Distributed Agent Platform (DAP).

Архитектура:
  Publisher → EventBus → Subscribers
                │
                ▼
           Event Log (SQLite)

Стандартные типы событий:
  system.*         — системные (startup, shutdown, error)
  task.*           — жизненный цикл задач (created, completed, failed)
  step.*           — жизненный цикл шагов (started, completed, failed)
  memory.*         — изменения в памяти (stored, deleted)
  knowledge.*      — поиск/индексация знаний
  context.*        — сбор контекста
  agent.*          — подключение/отключение агентов
  checkpoint.*     — чекпоинты

Использование:
    from scripts_01.event_bus import EventBus, Event

    bus = EventBus()

    def on_task_completed(event: Event):
        print(f"Task done: {event.data}")

    sub = bus.subscribe("task.completed", on_task_completed)
    bus.publish(Event("task.completed", {"id": "wf1", "status": "ok"}))
    bus.unsubscribe(sub)
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = "context_12/events.db"

# ═══════════════════════════════════════════════════════════════
# Default EventBus singleton (lazy init)
# ═══════════════════════════════════════════════════════════════

_DEFAULT_BUSES: Dict[str, "EventBus"] = {}
_DEFAULT_BUS_LOCK = threading.Lock()


def get_default_event_bus(workspace_root: str | Path | None = None) -> "EventBus":
    """Возвращает дефолтный EventBus для workspace.

    Lazily initializes the bus and registers standard subscribers.
    Use this in application entry points (bootstrap, CLI) so that
    MemoryEngine auto-indexes into KnowledgeEngine.
    """
    if workspace_root is None:
        db_path = WORKSPACE / DEFAULT_DB_PATH
        key = str(WORKSPACE)
    else:
        ws = Path(workspace_root)
        db_path = ws / DEFAULT_DB_PATH
        key = str(ws)

    if key not in _DEFAULT_BUSES:
        with _DEFAULT_BUS_LOCK:
            if key not in _DEFAULT_BUSES:
                bus = EventBus(db_path=db_path)
                from scripts_01.event_subscribers import register_all
                register_all(bus, workspace_root)
                _DEFAULT_BUSES[key] = bus

    return _DEFAULT_BUSES[key]


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class Event:
    """Одно событие в шине."""
    type: str                        # "task.completed", "memory.updated"
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"            # кто опубликовал
    id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:12]
    )
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """Подписка на события."""
    id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:8]
    )
    event_type: str = ""              # полное имя или wildcard ("task.*")
    handler: Optional[Callable] = None
    filter_fn: Optional[Callable] = None  # доп. фильтр по Event


@dataclass
class EventLogEntry:
    """Запись в логе событий."""
    event_id: str
    event_type: str
    source: str
    data_json: str
    timestamp: str
    delivered_to: int = 0              # количество доставленных подписчиков


# ═══════════════════════════════════════════════════════════════
# EventBus
# ═══════════════════════════════════════════════════════════════


class EventBus:
    """Публично-подписная шина событий.

    Особенности:
      - Синхронная доставка (вызов handler в том же потоке)
      - Wildcard подписки ("task.*" ловит "task.completed", "task.failed")
      - Фильтр-функции для точной настройки
      - Логирование всех событий в SQLite
      - Thread-safe
      - Статистика
    """

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = Path(db_path) if db_path else WORKSPACE / DEFAULT_DB_PATH
        self._lock = threading.Lock()

        # Подписки: {id: Subscription}
        self._subscriptions: Dict[str, Subscription] = {}

        # Индекс: event_type → set(subscription_ids)
        # Для быстрого поиска по подпискам
        self._type_index: Dict[str, Set[str]] = defaultdict(set)

        self._init_db()

    def _init_db(self):
        """Создаёт таблицу для лога событий."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    data_json TEXT DEFAULT '{}',
                    timestamp TEXT NOT NULL,
                    delivered_to INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type
                ON event_log(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_time
                ON event_log(timestamp)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ── Публикация ─────────────────────────────────────────

    def publish(self, event: Event) -> int:
        """Публикует событие — доставляет подписчикам и логирует.

        Args:
            event: событие для публикации

        Returns:
            Количество подписчиков, которым доставлено.
        """
        # Находим подписчиков под блокировкой
        with self._lock:
            subscribers = self._find_subscribers(event)

        # Вызываем хендлеры БЕЗ блокировки (чтобы избежать deadlock,
        # если хендлер сам вызывает subscribe/unsubscribe)
        delivered = 0
        for sub in subscribers:
            try:
                if sub.handler:
                    sub.handler(event)
                    delivered += 1
            except Exception as e:
                # Не ломаем шину из-за ошибки в подписчике
                print(f"⚠️ EventBus: handler error for {event.type}: {e}")

        # Логируем под блокировкой
        self._log_event(event, delivered)

        return delivered

    def _find_subscribers(self, event: Event) -> List[Subscription]:
        """Находит подписчиков, которым нужно доставить событие.

        Учитывает:
          - Точное совпадение event_type
          - Wildcard ("task.*" → "task.completed")
          - Фильтр-функции
        """
        matched: List[Subscription] = []
        seen: Set[str] = set()

        # Разбиваем event_type на части для wildcard matching
        parts = event.type.split(".")
        # Возможные wildcard паттерны:
        # "task.completed" → ищем "task.completed" и "task.*" и "*"
        patterns = [event.type]
        if len(parts) > 1:
            patterns.append(f"{parts[0]}.*")
        patterns.append("*")

        for pattern in patterns:
            for sub_id in self._type_index.get(pattern, set()):
                if sub_id not in seen:
                    sub = self._subscriptions.get(sub_id)
                    if sub and sub.handler:
                        # Дополнительный фильтр
                        if sub.filter_fn and not sub.filter_fn(event):
                            continue
                        seen.add(sub_id)
                        matched.append(sub)

        return matched

    # ── Подписка ───────────────────────────────────────────

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
        filter_fn: Optional[Callable] = None,
    ) -> Subscription:
        """Подписывается на события.

        Args:
            event_type: тип события ("task.completed") или wildcard ("task.*", "*")
            handler: функция-обработчик, принимает Event
            filter_fn: опциональная функция-фильтр (Event → bool)

        Returns:
            Subscription (для отписки)
        """
        sub = Subscription(
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
        )

        with self._lock:
            self._subscriptions[sub.id] = sub
            self._type_index[event_type].add(sub.id)

        return sub

    def unsubscribe(self, subscription: Subscription) -> bool:
        """Отписывается от событий.

        Returns:
            True если подписка существовала.
        """
        with self._lock:
            if subscription.id not in self._subscriptions:
                return False

            del self._subscriptions[subscription.id]

            # Удаляем из индекса
            for event_type in list(self._type_index.keys()):
                self._type_index[event_type].discard(subscription.id)
                if not self._type_index[event_type]:
                    del self._type_index[event_type]

        return True

    # ── Логирование ────────────────────────────────────────

    def _log_event(self, event: Event, delivered: int):
        """Сохраняет событие в SQLite лог."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO event_log
                       (event_id, event_type, source, data_json, timestamp, delivered_to)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        event.id,
                        event.type,
                        event.source,
                        json.dumps(event.data, ensure_ascii=False),
                        event.timestamp,
                        delivered,
                    ),
                )
                conn.commit()
        except Exception:
            pass  # Лог не должен ломать шину

    # ── Запросы к логу ─────────────────────────────────────

    def get_events(
        self,
        event_type: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> List[EventLogEntry]:
        """Читает события из лога.

        Args:
            event_type: фильтр по типу
            limit: максимальное количество
            since: ISO timestamp — только события после этой даты

        Returns:
            Список EventLogEntry
        """
        with self._connect() as conn:
            query = "SELECT * FROM event_log"
            params: List[Any] = []
            conditions = []

            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            if since:
                conditions.append("timestamp >= ?")
                params.append(since)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [
                EventLogEntry(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    source=row["source"],
                    data_json=row["data_json"],
                    timestamp=row["timestamp"],
                    delivered_to=row["delivered_to"],
                )
                for row in rows
            ]

    # ── Статистика ─────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Статистика шины."""
        with self._connect() as conn:
            total_events = conn.execute(
                "SELECT COUNT(*) FROM event_log"
            ).fetchone()[0]

            # Типы событий
            type_counts = {}
            for row in conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM event_log GROUP BY event_type"
            ).fetchall():
                type_counts[row["event_type"]] = row["cnt"]

            # За последний час
            one_hour_ago = datetime.now(timezone.utc).isoformat()[:13]  # час
            recent = conn.execute(
                "SELECT COUNT(*) FROM event_log WHERE timestamp >= ?",
                (one_hour_ago,),
            ).fetchone()[0]

        return {
            "total_events": total_events,
            "active_subscribers": len(self._subscriptions),
            "event_types": type_counts,
            "events_last_hour": recent,
        }

    def clear(self):
        """Очищает лог и подписки."""
        with self._lock:
            self._subscriptions.clear()
            self._type_index.clear()

            with self._connect() as conn:
                conn.execute("DELETE FROM event_log")
                conn.commit()


# ═══════════════════════════════════════════════════════════════
# Удобные фабрики событий
# ═══════════════════════════════════════════════════════════════


def task_event(action: str, task_id: str, **data) -> Event:
    """Создаёт событие task.<action>."""
    return Event(
        type=f"task.{action}",
        source="orchestrator",
        data={"task_id": task_id, **data},
    )


def step_event(action: str, step_id: str, task_id: str, **data) -> Event:
    """Создаёт событие step.<action>."""
    return Event(
        type=f"step.{action}",
        source="orchestrator",
        data={"step_id": step_id, "task_id": task_id, **data},
    )


def memory_event(action: str, level: str, key: str, **data) -> Event:
    """Создаёт событие memory.<action>."""
    return Event(
        type=f"memory.{action}",
        source="memory_engine",
        data={"level": level, "key": key, **data},
    )


def context_event(action: str, **data) -> Event:
    """Создаёт событие context.<action>."""
    return Event(
        type=f"context.{action}",
        source="context_builder",
        data=data,
    )


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Event Bus — шина событий Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # publish
    p_pub = sub.add_parser("publish", help="Опубликовать событие")
    p_pub.add_argument("type", help="Тип события")
    p_pub.add_argument("--data", default="{)", help="JSON данные")
    p_pub.add_argument("--source", default="cli", help="Источник")

    # events
    p_events = sub.add_parser("events", help="Список событий из лога")
    p_events.add_argument("--type", dest="event_type", help="Фильтр по типу")
    p_events.add_argument("--limit", type=int, default=10)

    # stats
    sub.add_parser("stats", help="Статистика")

    # clear
    sub.add_parser("clear", help="Очистить лог")

    args = parser.parse_args()
    bus = EventBus()

    if args.command == "publish":
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            data = {}
        event = Event(type=args.type, data=data, source=args.source)
        delivered = bus.publish(event)
        print(f"📢 Published: {event.type} (id={event.id[:8]}, delivered={delivered})")

    elif args.command == "events":
        entries = bus.get_events(
            event_type=args.event_type,
            limit=args.limit,
        )
        if not entries:
            print("📭 No events")
            return
        print(f"📋 Events ({len(entries)}):")
        for e in entries:
            print(f"  {e.timestamp[:19]} | {e.event_type:25} | from={e.source} | delivered={e.delivered_to}")

    elif args.command == "stats":
        stats = bus.get_stats()
        print("📊 EVENT BUS STATS")
        print(f"   Total events:      {stats['total_events']}")
        print(f"   Active subscribers: {stats['active_subscribers']}")
        print(f"   Events last hour:  {stats['events_last_hour']}")
        if stats["event_types"]:
            print(f"   Event types:")
            for etype, count in sorted(stats["event_types"].items()):
                print(f"     {etype}: {count}")

    elif args.command == "clear":
        bus.clear()
        print("🗑 Event log cleared")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
