PROMPT: Внедрение Session Mesh v2.0 в экосистему Buffy

Версия: 1.0.0
Дата: 2026-07-30
Цель: Реализовать распределённый слой Session Mesh для Buffy AI Infrastructure Layer
Основание: DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md
Архитектор: Denis (пользователь)
Исполнитель: Buffy (AI-ассистент) + команда разработчиков (опционально)

---

📋 Контекст

Что у нас есть

1. Существующая архитектура — монолитная, модульная, Local First
   · ContextManager (SQLite сессии)
   · Event Bus (локальный, publish/subscribe)
   · Memory Engine, Knowledge Engine, Graph Index
   · MCP Server, Bridge Layer, ACP Protocol
   · 1143 тестов, 0 ошибок
2. Проблема — система завязана на single-node
   · Нет синхронизации между устройствами
   · Нет возможности работы в команде
   · Offline-режим неполный
3. Цель — реализовать распределённый слой без нарушения работы существующей системы
   · Обратная совместимость: система работает без Mesh
   · Постепенное внедрение: сначала Node Mesh, потом Session Mesh, потом Agent Mesh
   · Сохранение Local First: SQLite остаётся кэшем, Event Store — источник истины

Что мы строим

Session Mesh v2.0 — трёхуровневая распределённая архитектура:

```
Node Mesh (устройства + сеть)
    ↓
Session Mesh (контекст + синхронизация)
    ↓
Agent Mesh (агенты + инструменты)
```

Ключевые компоненты:

· EventStore (ядро системы, интерфейс + реализации)
· Vector Clock (обнаружение конфликтов)
· Lease Manager (аренда сессий)
· Offline Queue (работа без сети)
· Capability Engine (выбор устройств)

---

🎯 Задачи

Фаза 0: Подготовка (1 день)

Задача 0.1: Создать структуру директорий

```bash
freebuff_plugin_03/mesh/
├── __init__.py
├── core_02/
│   ├── __init__.py
│   ├── event_store.py
│   ├── event.py
│   ├── vector_clock.py
│   └── conflict.py
├── node/
│   ├── __init__.py
│   ├── device.py
│   ├── capability.py
│   ├── heartbeat.py
│   └── discovery.py
├── session/
│   ├── __init__.py
│   ├── session.py
│   ├── lease.py
│   ├── sync.py
│   └── offline.py
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   ├── tool.py
│   └── balancer.py
├── transport/
│   ├── __init__.py
│   ├── base.py
│   ├── local.py
│   ├── websocket.py
│   ├── nats.py
│   └── http.py
├── storage/
│   ├── __init__.py
│   ├── sqlite.py
│   ├── postgres.py
│   └── kafka.py
├── mesh.py
└── cli.py
```

Требования:

· Каждый файл содержит docstring на русском
· Все публичные функции имеют type hints
· Используется from __future__ import annotations

---

Задача 0.2: Обновить зависимости

```bash
# requirements.txt
pip install ulid-py>=1.0.0
pip install websocket-client>=1.5.0
pip install asyncpg>=0.28.0  # опционально, для Postgres
pip install kafka-python>=2.0.0  # опционально, для Kafka
pip install diff-match-patch>=2023.0.0  # для OT
pip install prometheus-client>=0.17.0  # для метрик
```

---

Задача 0.3: Написать тестовую инфраструктуру

```python
# tests_09/conftest.py — добавить фикстуры для Mesh

@pytest.fixture
def event_store():
    """SQLiteEventStore для тестов."""
    db_path = Path("/tmp/test_events.db")
    store = SQLiteEventStore(db_path)
    yield store
    db_path.unlink(missing_ok=True)

@pytest.fixture
def node_mesh(event_store):
    """Node Mesh для тестов."""
    return NodeMesh(
        user_id="test_user",
        device_id="test_device",
        event_store=event_store,
    )

@pytest.fixture
def session_mesh(event_store, node_mesh):
    """Session Mesh для тестов."""
    return SessionMesh(
        user_id="test_user",
        device_id="test_device",
        event_store=event_store,
        node_mesh=node_mesh,
    )
```

---

Фаза 1: EventStore (2-3 дня)

Задача 1.1: Реализовать Event (с ULID)

```python
# freebuff_plugin_03/mesh/core_02/event.py

import ulid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class Event:
    """Событие в Event Store."""
    id: str = field(default_factory=lambda: str(ulid.ULID()))
    stream: str = ""
    version: int = 0
    type: str = ""
    data: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any***REMOVED***:
        """Сериализовать в JSON."""
        return {
            "id": self.id,
            "stream": self.stream,
            "version": self.version,
            "type": self.type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        ***REMOVED***
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any***REMOVED***) -> "Event":
        """Десериализовать из JSON."""
        return cls(
            id=data["id"***REMOVED***,
            stream=data["stream"***REMOVED***,
            version=data["version"***REMOVED***,
            type=data["type"***REMOVED***,
            data=data.get("data", {***REMOVED***),
            metadata=data.get("metadata", {***REMOVED***),
            timestamp=data["timestamp"***REMOVED***,
        )
```

Тесты:

· test_event_ulid_generation — ULID генерируется
· test_event_ulid_sortable — ULID сортируется по времени
· test_event_to_from_dict — сериализация/десериализация

---

Задача 1.2: Реализовать EventStore интерфейс

```python
# freebuff_plugin_03/mesh/core_02/event_store.py

from abc import ABC, abstractmethod
from typing import List, Iterator, Callable, Optional, Tuple, Dict

class EventStore(ABC):
    """Ядро Event Sourcing — единый источник истины."""
    
    @abstractmethod
    def append(self, stream: str, events: List[Event***REMOVED***, expected_version: Optional[int***REMOVED*** = None) -> None:
        """Добавить события в поток."""
        ...
    
    @abstractmethod
    def read_stream(self, stream: str, from_version: int = 0, limit: Optional[int***REMOVED*** = None) -> List[Event***REMOVED***:
        """Прочитать события потока."""
        ...
    
    @abstractmethod
    def stream_events(self, stream: str, from_version: int = 0) -> Iterator[Event***REMOVED***:
        """Итератор событий (для replay)."""
        ...
    
    @abstractmethod
    def subscribe(self, stream: str, callback: Callable[[Event***REMOVED***, None***REMOVED***) -> str:
        """Подписаться на новые события."""
        ...
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Отписаться."""
        ...
    
    @abstractmethod
    def snapshot(self, stream: str, version: int, state: Dict) -> None:
        """Сохранить снапшот состояния."""
        ...
    
    @abstractmethod
    def restore(self, stream: str) -> Tuple[int, Dict***REMOVED***:
        """Восстановить состояние из последнего снапшота."""
        ...
    
    @abstractmethod
    def compact(self, stream: str, keep_snapshots: int = 10) -> int:
        """Удалить старые события после снапшотов."""
        ...
    
    @abstractmethod
    def get_version(self, stream: str) -> int:
        """Получить текущую версию потока."""
        ...
    
    @abstractmethod
    def list_streams(self, prefix: str = "") -> List[str***REMOVED***:
        """Список всех потоков."""
        ...
```

Тесты:

· test_event_store_append — append события
· test_event_store_read_stream — read_stream
· test_event_store_stream_events — stream_events (итератор)
· test_event_store_subscribe — подписка на события
· test_event_store_snapshot — snapshot + restore
· test_event_store_compact — compact
· test_event_store_optimistic_locking — оптимистичная блокировка
· test_event_store_concurrent — параллельная запись

---

Задача 1.3: Реализовать SQLiteEventStore

```python
# freebuff_plugin_03/mesh/storage/sqlite.py

import sqlite3
import json
***REMOVED***
from typing import List, Iterator, Callable, Optional, Tuple, Dict
import threading

class SQLiteEventStore(EventStore):
    """SQLite-реализация Event Store."""
    
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable***REMOVED******REMOVED*** = {***REMOVED***
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Создать таблицы."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    stream TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TEXT NOT NULL,
                    UNIQUE(stream, version)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stream ON events(stream)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_version ON events(version)")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Получить соединение с БД (thread-safe)."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def append(self, stream: str, events: List[Event***REMOVED***, expected_version: Optional[int***REMOVED*** = None) -> None:
        """Добавить события в поток."""
        with self._lock:
            with self._get_connection() as conn:
                # Проверка оптимистичной блокировки
                if expected_version is not None:
                    current = conn.execute(
                        "SELECT version FROM events WHERE stream = ? ORDER BY version DESC LIMIT 1",
                        (stream,)
                    ).fetchone()
                    current_version = current["version"***REMOVED*** if current else 0
                    
                    if current_version != expected_version:
                        raise ConcurrentModificationError(
                            f"Stream {stream***REMOVED*** expected version {expected_version***REMOVED***, got {current_version***REMOVED***"
                        )
                
                # Сохраняем события
                for i, event in enumerate(events):
                    version = event.version if event.version > 0 else self._get_next_version(stream)
                    conn.execute("""
                        INSERT INTO events (id, stream, version, type, data, metadata, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.id,
                        stream,
                        version,
                        event.type,
                        json.dumps(event.data),
                        json.dumps(event.metadata) if event.metadata else None,
                        event.timestamp,
                    ))
                
                # Уведомляем подписчиков
                for event in events:
                    self._notify_subscribers(stream, event)
    
    def read_stream(self, stream: str, from_version: int = 0, limit: Optional[int***REMOVED*** = None) -> List[Event***REMOVED***:
        """Прочитать события потока."""
        with self._get_connection() as conn:
            query = "SELECT * FROM events WHERE stream = ? AND version >= ? ORDER BY version ASC"
            params = [stream, from_version***REMOVED***
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_event(row) for row in rows***REMOVED***
    
    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Преобразовать строку БД в Event."""
        return Event(
            id=row["id"***REMOVED***,
            stream=row["stream"***REMOVED***,
            version=row["version"***REMOVED***,
            type=row["type"***REMOVED***,
            data=json.loads(row["data"***REMOVED***),
            metadata=json.loads(row["metadata"***REMOVED***) if row["metadata"***REMOVED*** else {***REMOVED***,
            timestamp=row["timestamp"***REMOVED***,
        )
```

Тесты:

· test_sqlite_append — сохранение событий
· test_sqlite_read_stream — чтение событий
· test_sqlite_optimistic_locking — оптимистичная блокировка
· test_sqlite_subscribe — подписка
· test_sqlite_concurrent — параллельная запись (thread-safe)
· test_sqlite_snapshot — snapshot + restore
· test_sqlite_compact — compact

---

Фаза 2: Vector Clock (1 день)

Задача 2.1: Реализовать VectorClock

```python
# freebuff_plugin_03/mesh/core_02/vector_clock.py

import threading
from typing import Dict

class VectorClock:
    """Векторные часы для обнаружения конфликтов."""
    
    def __init__(self, device_id: str):
        self._device_id = device_id
        self._clocks: Dict[str, int***REMOVED*** = {device_id: 0***REMOVED***
        self._lock = threading.Lock()
    
    def increment(self) -> Dict[str, int***REMOVED***:
        """Увеличить счётчик устройства."""
        with self._lock:
            self._clocks[self._device_id***REMOVED*** = self._clocks.get(self._device_id, 0) + 1
            return self._clocks.copy()
    
    def merge(self, other: Dict[str, int***REMOVED***) -> None:
        """Объединить часы (max)."""
        with self._lock:
            for device_id, counter in other.items():
                self._clocks[device_id***REMOVED*** = max(self._clocks.get(device_id, 0), counter)
    
    def compare(self, other: Dict[str, int***REMOVED***) -> str:
        """Сравнить два состояния часов.
        
        Returns:
            "before" — self < other
            "after"  — self > other
            "concurrent" — конфликт
            "equal" — идентичны
        """
        with self._lock:
            all_devices = set(self._clocks.keys()) | set(other.keys())
            
            before = False
            after = False
            
            for device_id in all_devices:
                self_val = self._clocks.get(device_id, 0)
                other_val = other.get(device_id, 0)
                
                if self_val < other_val:
                    before = True
                elif self_val > other_val:
                    after = True
            
            if before and after:
                return "concurrent"
            elif before:
                return "before"
            elif after:
                return "after"
            else:
                return "equal"
    
    def get_current(self) -> Dict[str, int***REMOVED***:
        """Получить текущее состояние часов."""
        with self._lock:
            return self._clocks.copy()
```

Тесты:

· test_vector_clock_increment — increment
· test_vector_clock_merge — merge (max)
· test_vector_clock_compare_before — compare: before
· test_vector_clock_compare_after — compare: after
· test_vector_clock_compare_concurrent — compare: concurrent
· test_vector_clock_compare_equal — compare: equal
· test_vector_clock_thread_safe — thread-safe

---

Фаза 3: Node Mesh (2-3 дня)

Задача 3.1: Реализовать Device и DeviceRegistry

```python
# freebuff_plugin_03/mesh/node/device.py

import ulid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class DeviceCapability:
    """Возможность устройства."""
    name: str                          # "llm.inference", "whisper", "ocr"
    version: str
    available: bool = True
    performance_score: float = 1.0     # 0.0 - 1.0
    cost_per_unit: float = 0.0
    requires_network: bool = False
    max_concurrent: int = 1

@dataclass
class Device:
    """Устройство в распределённой сети."""
    device_id: str = field(default_factory=lambda: str(ulid.ULID()))
    user_id: str = ""
    name: str = ""
    device_type: str = ""              # "android", "linux", "mac", "server"
    status: str = "online"             # "online", "offline", "sleeping", "error"
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    ip_address: Optional[str***REMOVED*** = None
    port: Optional[int***REMOVED*** = None
    capabilities: List[DeviceCapability***REMOVED*** = field(default_factory=list)
    resources: Dict[str, float***REMOVED*** = field(default_factory=dict)  # ram, cpu, vram, battery
    buffy_version: str = ""
    agent_version: str = ""
    sync_enabled: bool = True
    sync_interval_sec: int = 30

class DeviceRegistry:
    """Реестр устройств."""
    
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._devices: Dict[str, Device***REMOVED*** = {***REMOVED***
        self._lock = threading.Lock()
    
    def register(self, device: Device) -> str:
        """Зарегистрировать устройство."""
        with self._lock:
            self._devices[device.device_id***REMOVED*** = device
            
            event = Event(
                stream=f"device:{device.device_id***REMOVED***",
                type="device.registered",
                data=device.__dict__,
            )
            self._event_store.append(f"device:{device.device_id***REMOVED***", [event***REMOVED***)
            
            return device.device_id
    
    def get(self, device_id: str) -> Optional[Device***REMOVED***:
        """Получить устройство по ID."""
        with self._lock:
            return self._devices.get(device_id)
    
    def list(self, status: Optional[str***REMOVED*** = None) -> List[Device***REMOVED***:
        """Список устройств."""
        with self._lock:
            devices = list(self._devices.values())
            if status:
                devices = [d for d in devices if d.status == status***REMOVED***
            return devices
    
    def update_status(self, device_id: str, status: str) -> bool:
        """Обновить статус устройства."""
        with self._lock:
            if device_id not in self._devices:
                return False
            
            device = self._devices[device_id***REMOVED***
            device.status = status
            device.last_seen = datetime.now().isoformat()
            
            event = Event(
                stream=f"device:{device_id***REMOVED***",
                type="device.status_updated",
                data={"status": status***REMOVED***,
            )
            self._event_store.append(f"device:{device_id***REMOVED***", [event***REMOVED***)
            
            return True
    
    def prune_offline(self, max_age: int = 120) -> int:
        """Удалить устройства, не отвечающие > max_age секунд."""
        with self._lock:
            now = datetime.now()
            to_remove = [***REMOVED***
            for device_id, device in self._devices.items():
                if device.status == "offline":
                    last_seen = datetime.fromisoformat(device.last_seen)
                    if (now - last_seen).total_seconds() > max_age:
                        to_remove.append(device_id)
            
            for device_id in to_remove:
                del self._devices[device_id***REMOVED***
            
            return len(to_remove)
```

Тесты:

· test_device_registry_register — регистрация устройства
· test_device_registry_get — получение устройства
· test_device_registry_list — список устройств
· test_device_registry_update_status — обновление статуса
· test_device_registry_prune_offline — удаление офлайн-устройств
· test_device_events — события регистрации/обновления

---

Задача 3.2: Реализовать CapabilityEngine

```python
# freebuff_plugin_03/mesh/node/capability.py

from typing import Dict, List, Optional, Any

class CapabilityEngine:
    """Интеллектуальный выбор устройства по capability."""
    
    def __init__(self, device_registry: DeviceRegistry):
        self._registry = device_registry
        self._task_mapping = {
            "generate_code": "llm.inference",
            "review_code": "llm.inference",
            "transcribe_audio": "whisper",
            "ocr_image": "ocr",
            "search_web": "web_search",
            "documentation": "llm.inference",
            "planning": "llm.inference",
        ***REMOVED***
    
    def select_device(
        self,
        task: str,
        requirements: Optional[Dict[str, Any***REMOVED******REMOVED*** = None
    ) -> Optional[str***REMOVED***:
        """Выбрать устройство для задачи."""
        # 1. Определить capability
        capability = self._task_to_capability(task)
        
        # 2. Найти устройства с этой capability
        devices = self._registry.list(status="online")
        candidates = [***REMOVED***
        
        for device in devices:
            for cap in device.capabilities:
                if cap.name == capability and cap.available:
                    score = self._calculate_score(device, cap, requirements)
                    candidates.append((device.device_id, score))
        
        if not candidates:
            return None
        
        # 3. Выбрать с наивысшим score
        return max(candidates, key=lambda x: x[1***REMOVED***)[0***REMOVED***
    
    def _task_to_capability(self, task: str) -> str:
        """Маппинг задачи на capability."""
        return self._task_mapping.get(task, "llm.inference")
    
    def _calculate_score(
        self,
        device: Device,
        capability: DeviceCapability,
        requirements: Optional[Dict[str, Any***REMOVED******REMOVED*** = None
    ) -> float:
        """Рассчитать score устройства для задачи."""
        score = capability.performance_score
        
        # Учитываем ресурсы
        if requirements:
            if "min_ram" in requirements and device.resources.get("ram", 0) < requirements["min_ram"***REMOVED***:
                score *= 0.5
            if "min_vram" in requirements and device.resources.get("vram", 0) < requirements["min_vram"***REMOVED***:
                score *= 0.3
            if "requires_gpu" in requirements and not device.resources.get("gpu", False):
                score *= 0.2
        
        # Учитываем батарею (для телефонов)
        if device.device_type == "android" and device.resources.get("battery", 100) < 20:
            score *= 0.5
        
        return score
```

Тесты:

· test_capability_task_mapping — маппинг задач
· test_capability_select_device — выбор устройства
· test_capability_score_calculation — расчёт score
· test_capability_no_devices — нет подходящих устройств
· test_capability_battery_aware — учёт батареи

---

Фаза 4: Session Mesh (3-4 дня)

Задача 4.1: Реализовать LeaseManager

```python
# freebuff_plugin_03/mesh/session/lease.py

import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SessionLease:
    """Аренда сессии устройством."""
    session_id: str
    owner_device: str
    expires_at: float
    created_at: str
    renewed_at: str
    renew_count: int = 0

class LeaseManager:
    """Управление арендой сессий."""
    
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._leases: Dict[str, SessionLease***REMOVED*** = {***REMOVED***
        self._lock = threading.Lock()
    
    def acquire(self, session_id: str, device_id: str, ttl: int = 60) -> bool:
        """Захватить аренду сессии."""
        with self._lock:
            # Проверить существующую аренду
            if session_id in self._leases:
                lease = self._leases[session_id***REMOVED***
                if time.time() < lease.expires_at:
                    return False  # занято
            
            # Создать новую аренду
            self._leases[session_id***REMOVED*** = SessionLease(
                session_id=session_id,
                owner_device=device_id,
                expires_at=time.time() + ttl,
                created_at=datetime.now().isoformat(),
                renewed_at=datetime.now().isoformat(),
            )
            
            # Сохранить событие
            event = Event(
                stream=f"lease:{session_id***REMOVED***",
                type="lease.acquired",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                    "expires_at": self._leases[session_id***REMOVED***.expires_at,
                ***REMOVED***,
            )
            self._event_store.append(f"lease:{session_id***REMOVED***", [event***REMOVED***)
            
            return True
    
    def renew(self, session_id: str, device_id: str, ttl: int = 60) -> bool:
        """Продлить аренду."""
        with self._lock:
            if session_id not in self._leases:
                return False
            
            lease = self._leases[session_id***REMOVED***
            if lease.owner_device != device_id:
                return False
            
            # Продлеваем
            lease.expires_at = time.time() + ttl
            lease.renewed_at = datetime.now().isoformat()
            lease.renew_count += 1
            
            # Сохраняем событие
            event = Event(
                stream=f"lease:{session_id***REMOVED***",
                type="lease.renewed",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                    "expires_at": lease.expires_at,
                    "renew_count": lease.renew_count,
                ***REMOVED***,
            )
            self._event_store.append(f"lease:{session_id***REMOVED***", [event***REMOVED***)
            
            return True
    
    def release(self, session_id: str, device_id: str) -> bool:
        """Отпустить аренду."""
        with self._lock:
            if session_id not in self._leases:
                return False
            
            lease = self._leases[session_id***REMOVED***
            if lease.owner_device != device_id:
                return False
            
            del self._leases[session_id***REMOVED***
            
            # Сохраняем событие
            event = Event(
                stream=f"lease:{session_id***REMOVED***",
                type="lease.released",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                ***REMOVED***,
            )
            self._event_store.append(f"lease:{session_id***REMOVED***", [event***REMOVED***)
            
            return True
    
    def get_owner(self, session_id: str) -> Optional[str***REMOVED***:
        """Получить владельца сессии."""
        with self._lock:
            if session_id not in self._leases:
                return None
            
            lease = self._leases[session_id***REMOVED***
            if time.time() > lease.expires_at:
                return None  # аренда истекла
            
            return lease.owner_device
```

Тесты:

· test_lease_acquire — захват аренды
· test_lease_renew — продление аренды
· test_lease_release — отпускание аренды
· test_lease_expired — истечение аренды
· test_lease_double_acquire — двойной захват
· test_lease_events — события аренды

---

Задача 4.2: Реализовать SessionMesh

```python
# freebuff_plugin_03/mesh/session/session.py

import ulid
from typing import Optional, List, Dict

class SessionMesh:
    """Управление распределёнными сессиями."""
    
    def __init__(
        self,
        user_id: str,
        device_id: str,
        event_store: EventStore,
        node_mesh: NodeMesh,
    ):
        self._user_id = user_id
        self._device_id = device_id
        self._event_store = event_store
        self._node_mesh = node_mesh
        self._vector_clock = VectorClock(device_id)
        self._lease_manager = LeaseManager(event_store)
        self._session_cache: Dict[str, DistributedSession***REMOVED*** = {***REMOVED***
        self._lock = threading.Lock()
    
    def create_session(self, topic: str, project: str = "") -> DistributedSession:
        """Создать распределённую сессию."""
        session_id = str(ulid.ULID())
        
        # Создаём событие
        event = Event(
            stream=f"session:{session_id***REMOVED***",
            version=0,
            type="session.created",
            data={
                "session_id": session_id,
                "topic": topic,
                "project": project,
                "user_id": self._user_id,
                "device_id": self._device_id,
            ***REMOVED***,
            metadata={
                "vector_clock": self._vector_clock.increment(),
            ***REMOVED***,
        )
        self._event_store.append(f"session:{session_id***REMOVED***", [event***REMOVED***)
        
        # Создаём локальный кэш
        session = DistributedSession(
            session_id=session_id,
            topic=topic,
            project=project,
            user_id=self._user_id,
            device_id=self._device_id,
        )
        
        with self._lock:
            self._session_cache[session_id***REMOVED*** = session
        
        return session
    
    def get_session(self, session_id: str) -> Optional[DistributedSession***REMOVED***:
        """Получить сессию (с синхронизацией)."""
        # Сначала синхронизируем
        self._sync_session(session_id)
        
        # Затем возвращаем кэш
        with self._lock:
            return self._session_cache.get(session_id)
    
    def _sync_session(self, session_id: str) -> None:
        """Принудительно синхронизировать сессию."""
        with self._lock:
            # Получить локальную версию
            cache = self._session_cache.get(session_id)
            local_version = cache.version if cache else 0
            
            # Получить удалённые события
            remote_events = self._event_store.read_stream(
                f"session:{session_id***REMOVED***",
                from_version=local_version + 1
            )
            
            # Применить события
            for event in remote_events:
                self._apply_event(session_id, event)
    
    def _apply_event(self, session_id: str, event: Event) -> None:
        """Применить событие к сессии."""
        with self._lock:
            cache = self._session_cache.get(session_id)
            if not cache:
                cache = DistributedSession(session_id=session_id)
                self._session_cache[session_id***REMOVED*** = cache
            
            if event.type == "message.added":
                cache.messages.append(event.data)
                cache.message_count += 1
            elif event.type == "message.updated":
                # Найти и обновить
                for i, msg in enumerate(cache.messages):
                    if msg.get("id") == event.data["message_id"***REMOVED***:
                        cache.messages[i***REMOVED*** = event.data
                        break
            elif event.type == "session.ended":
                cache.status = "completed"
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Добавить сообщение в сессию."""
        # Проверить владельца
        owner = self._lease_manager.get_owner(session_id)
        if owner and owner != self._device_id:
            # Если аренда занята другим устройством — read-only
            return False
        
        # Создать событие
        event = Event(
            stream=f"session:{session_id***REMOVED***",
            type="message.added",
            data={
                "message_id": str(ulid.ULID()),
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            ***REMOVED***,
            metadata={
                "device_id": self._device_id,
                "vector_clock": self._vector_clock.increment(),
            ***REMOVED***,
        )
        
        self._event_store.append(f"session:{session_id***REMOVED***", [event***REMOVED***)
        return True
    
    def transfer_session(self, session_id: str, target_device: str) -> bool:
        """Передать сессию на другое устройство."""
        # Проверить, что мы владельцы
        owner = self._lease_manager.get_owner(session_id)
        if owner != self._device_id:
            return False
        
        # Передать lease
        return self._lease_manager.transfer(session_id, target_device)
```

Тесты:

· test_session_create — создание сессии
· test_session_get — получение сессии
· test_session_add_message — добавление сообщения
· test_session_sync — синхронизация
· test_session_transfer — передача сессии
· test_session_read_only — read-only режим
· test_session_events — события сессии

---

Фаза 5: Offline-first (2 дня)

Задача 5.1: Реализовать OfflineQueue

```python
# freebuff_plugin_03/mesh/session/offline.py

import json
import threading
***REMOVED***
from typing import List

class OfflineQueue:
    """Очередь событий для офлайн-режима."""
    
    def __init__(self, storage_path: Path):
        self._storage_path = storage_path / "offline_queue.json"
        self._pending: List[Event***REMOVED*** = [***REMOVED***
        self._lock = threading.Lock()
        self._load()
    
    def add(self, event: Event) -> None:
        """Добавить событие в офлайн-очередь."""
        with self._lock:
            self._pending.append(event)
            self._save()
    
    def get_pending(self) -> List[Event***REMOVED***:
        """Получить все ожидающие события."""
        with self._lock:
            return self._pending.copy()
    
    def mark_synced(self, event_ids: List[str***REMOVED***) -> None:
        """Отметить события как синхронизированные."""
        with self._lock:
            self._pending = [e for e in self._pending if e.id not in event_ids***REMOVED***
            self._save()
    
    def clear(self) -> None:
        """Очистить очередь."""
        with self._lock:
            self._pending = [***REMOVED***
            self._save()
    
    def _save(self) -> None:
        """Сохранить очередь на диск."""
        data = [e.to_dict() for e in self._pending***REMOVED***
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self) -> None:
        """Загрузить очередь с диска."""
        if not self._storage_path.exists():
            return
        
        with open(self._storage_path) as f:
            data = json.load(f)
            self._pending = [Event.from_dict(d) for d in data***REMOVED***
```

---

Задача 5.2: Реализовать SyncStrategy

```python
# freebuff_plugin_03/mesh/session/sync.py

from typing import List, Tuple

class SyncStrategy:
    """Стратегия синхронизации после офлайн-периода."""
    
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._resolver = ConflictResolver()
    
    def sync(
        self,
        device_id: str,
        offline_events: List[Event***REMOVED***
    ) -> Dict[str, Any***REMOVED***:
        """Синхронизировать офлайн-события с глобальным потоком."""
        # 1. Группировать по stream
        streams = {***REMOVED***
        for event in offline_events:
            streams.setdefault(event.stream, [***REMOVED***).append(event)
        
        # 2. Для каждого stream
        results = {
            "total": len(offline_events),
            "synced": 0,
            "conflicts": 0,
            "resolved": 0,
            "conflict_details": [***REMOVED***,
        ***REMOVED***
        
        for stream, events in streams.items():
            # a. Получить текущую версию
            current_version = self._event_store.get_version(stream)
            
            # b. Проверить конфликты
            remote_events = self._event_store.read_stream(stream, from_version=current_version)
            conflicts = [***REMOVED***
            
            for event in events:
                if self._resolver.detect_conflict(event, remote_events):
                    conflicts.append(event)
            
            # c. Разрешить конфликты
            resolved = [***REMOVED***
            for event in conflicts:
                resolved_event = self._resolver.resolve(event, remote_events)
                resolved.append(resolved_event)
            
            # d. Отправить разрешённые события
            for event in resolved:
                self._event_store.append(stream, [event***REMOVED***)
            
            results["synced"***REMOVED*** += len(events) - len(conflicts)
            results["conflicts"***REMOVED*** += len(conflicts)
            results["resolved"***REMOVED*** += len(resolved)
            
            if conflicts:
                results["conflict_details"***REMOVED***.append({
                    "stream": stream,
                    "conflicts": len(conflicts),
                ***REMOVED***)
        
        return results
```

Тесты:

· test_offline_queue_add — добавление в очередь
· test_offline_queue_get_pending — получение очереди
· test_offline_queue_mark_synced — отметка синхронизированных
· test_offline_queue_persistence — сохранение/загрузка
· test_sync_strategy_no_conflicts — синхронизация без конфликтов
· test_sync_strategy_with_conflicts — синхронизация с конфликтами

---

Фаза 6: MCP инструменты и CLI (2 дня)

Задача 6.1: MCP инструменты

```python
# freebuff_plugin_03/mesh/mcp.py

class MeshMCPTools:
    """MCP инструменты для Mesh."""
    
    def __init__(self, mesh: Mesh):
        self._mesh = mesh
    
    def register_tools(self, mcp_server):
        """Зарегистрировать инструменты в MCP сервере."""
        mcp_server.tool("mesh_status")(self._handle_mesh_status)
        mcp_server.tool("mesh_devices")(self._handle_mesh_devices)
        mcp_server.tool("mesh_session_list")(self._handle_mesh_session_list)
        mcp_server.tool("mesh_session_transfer")(self._handle_mesh_session_transfer)
        mcp_server.tool("mesh_session_sync")(self._handle_mesh_session_sync)
        mcp_server.tool("mesh_offline_status")(self._handle_mesh_offline_status)
        mcp_server.tool("mesh_offline_sync")(self._handle_mesh_offline_sync)
        mcp_server.tool("mesh_select_device")(self._handle_mesh_select_device)
    
    def _handle_mesh_status(self) -> Dict:
        """Статус Mesh."""
        devices = self._mesh._node_mesh.list_devices()
        sessions = self._mesh._session_mesh.list_sessions()
        
        return {
            "user_id": self._mesh._user_id,
            "device_id": self._mesh._device_id,
            "devices": [
                {
                    "id": d.device_id,
                    "name": d.name,
                    "status": d.status,
                    "last_seen": d.last_seen,
                ***REMOVED***
                for d in devices
            ***REMOVED***,
            "sessions": [
                {
                    "id": s.session_id,
                    "topic": s.topic,
                    "status": s.status,
                    "owner": self._mesh._session_mesh._lease_manager.get_owner(s.session_id),
                ***REMOVED***
                for s in sessions
            ***REMOVED***,
        ***REMOVED***
```

---

Задача 6.2: CLI

```python
# freebuff_plugin_03/mesh/cli.py

import argparse

def main():
    parser = argparse.ArgumentParser(description="Buffy Mesh CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    # node commands
    node_parser = subparsers.add_parser("node")
    node_subparsers = node_parser.add_subparsers(dest="node_command")
    
    node_init = node_subparsers.add_parser("init")
    node_init.add_argument("--username", required=True)
    node_init.add_argument("--device", required=True)
    node_init.add_argument("--type", choices=["android", "linux", "mac", "server"***REMOVED***)
    
    node_status = node_subparsers.add_parser("status")
    node_capabilities = node_subparsers.add_parser("capabilities")
    node_select = node_subparsers.add_parser("select")
    node_select.add_argument("--task", required=True)
    node_select.add_argument("--requirements", type=json.loads)
    
    # session commands
    session_parser = subparsers.add_parser("session")
    session_subparsers = session_parser.add_subparsers(dest="session_command")
    
    session_start = session_subparsers.add_parser("start")
    session_start.add_argument("--topic", required=True)
    session_start.add_argument("--project")
    session_start.add_argument("--broadcast", action="store_true")
    
    session_status = session_subparsers.add_parser("status")
    session_status.add_argument("session_id")
    
    session_transfer = session_subparsers.add_parser("transfer")
    session_transfer.add_argument("session_id")
    session_transfer.add_argument("--to", required=True)
    
    session_sync = session_subparsers.add_parser("sync")
    session_sync.add_argument("session_id")
    
    # offline commands
    offline_parser = subparsers.add_parser("offline")
    offline_subparsers = offline_parser.add_subparsers(dest="offline_command")
    
    offline_status = offline_subparsers.add_parser("status")
    offline_sync = offline_subparsers.add_parser("sync")
    
    args = parser.parse_args()
    
    # ... обработка команд
```

Тесты:

· test_mcp_tools_registration — регистрация MCP инструментов
· test_mcp_tools_mesh_status — mesh_status
· test_mcp_tools_session_transfer — session_transfer
· test_cli_node_init — node init
· test_cli_session_start — session start
· test_cli_offline_sync — offline sync

---

📊 Итоговый план

Фаза Дни Задачи Тестов Приоритет
0: Подготовка 1 Структура, зависимости, фикстуры 5 P0
1: EventStore 2-3 Event, интерфейс, SQLite 20 P0
2: Vector Clock 1 VectorClock 10 P0
3: Node Mesh 2-3 Device, Capability, Heartbeat 20 P1
4: Session Mesh 3-4 Lease, Session, Sync 25 P1
5: Offline-first 2 OfflineQueue, SyncStrategy 15 P1
6: Agent Mesh 2-3 Agent, Tool, LoadBalancer 20 P2
7: Transport 2 WebSocket, NATS, HTTP 15 P2
8: MCP + CLI 2 MCP tools, CLI 15 P3
ИТОГО 17-21 дней  ~145 тестов 

---

🎯 Критерии готовности

· Все 145+ тестов проходят
· EventStore интерфейс реализован
· SQLiteEventStore работает
· Vector Clock работает
· Node Mesh работает (обнаружение устройств)
· Session Mesh работает (синхронизация сессий)
· Lease Manager работает (аренда сессий)
· Offline-first работает (очередь + синхронизация)
· MCP инструменты зарегистрированы
· CLI команды работают
· Обратная совместимость: система работает без Mesh
· Документация обновлена
· CHANGELOG.md обновлён

---

🔧 Команды для внедрения

```bash
# 1. Создать структуру
mkdir -p freebuff_plugin_03/mesh/{core,node,session,agent,transport,storage***REMOVED***

# 2. Установить зависимости
pip install ulid-py websocket-client asyncpg kafka-python diff-match-patch prometheus-client

# 3. Начать реализацию
# Сначала EventStore (Фаза 1)
python -c "from freebuff_plugin.mesh.core.event import Event; print('OK')"

# 4. Запускать тесты после каждой фазы
pytest tests_09/test_mesh.py -v --tb=short

# 5. Проверять покрытие
pytest tests_09/test_mesh.py --cov=freebuff_plugin.mesh --cov-report=term

# 6. Проверять типы
mypy freebuff_plugin_03/mesh/ --strict

# 7. Обновлять документацию
python scripts_01/buffy_autodoc.py --cached --strict
```

---

📝 Changelog

```markdown
# CHANGELOG.md

## [5.0.0***REMOVED*** — 2026-08-XX

### Добавлено
- **Session Mesh v2.0** — распределённый слой для Buffy
  - EventStore как ядро системы (SQLite, Postgres, Kafka)
  - Node Mesh — управление устройствами и сетью
  - Session Mesh — синхронизация сессий и контекста
  - Agent Mesh — распределение агентов и инструментов
  - Vector Clock — обнаружение конфликтов
  - Lease Manager — аренда сессий с автоматическим failover
  - Offline-first — полная работа без сети
  - Capability Engine — интеллектуальный выбор устройств
  - MCP инструменты: mesh_status, mesh_devices, mesh_session_*
  - CLI: buffy node, buffy session, buffy offline
- 145+ тестов для Mesh

### Изменено
- ContextManager расширен для поддержки DistributedSession
- Event Bus теперь может быть распределённым
- ACP Protocol привязан к устройствам

### Исправлено
- Обратная совместимость: система работает без Mesh
```

---

Промт готов. Можно передавать исполнителю.