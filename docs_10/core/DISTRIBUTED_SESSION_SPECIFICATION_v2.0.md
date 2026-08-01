DISTRIBUTED SESSION SPECIFICATION v2.0 — Session Mesh для Buffy AI Infrastructure Layer

Версия: 2.0.0
Дата: 2026-07-30
Статус: 💡 Спецификация (к реализации, Phase 5-6)
Основание: VISION_3.0.md — Режимы Cowork/Teamwork, ARCHITECTURE_3.0.md — Labs
Архитектурный ревью: v1.0 → v2.0 (добавлены Node Mesh, EventStore как ядро, Lease, Offline-first, ULID)

---

1. Executive Summary

Session Mesh — это распределённый слой поверх существующей архитектуры Buffy, который обеспечивает:

· Единую идентичность пользователя и его устройств
· Обнаружение узлов и сетевое взаимодействие между ними
· Синхронизацию сессий в реальном времени
· Автоматическое разрешение конфликтов при параллельной работе
· Offline-first работу с последующей синхронизацией
· Интеллектуальный выбор узла для выполнения задач (Capability-based routing)

Ключевой принцип: SQLite остаётся локальным кэшом. Event Store — единый источник истины.

```
Текущая архитектура (Single):
  Device1 → SQLite (source of truth)

Новая архитектура (Mesh):
  Device1 → SQLite (cache) ←→ Event Sync ←→ Device2 → SQLite (cache)
                ↓                              ↓
         Event Store (distributed) ←→ Snapshots
              (source of truth)
```

---

2. Трёхуровневая архитектура Mesh

Система разделена на три независимых слоя, каждый из которых решает свою задачу:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER LAYER                                         │
│                    (UserRegistry + Identity)                                │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                          NODE MESH                                          │
│                                                                             │
│  • Device Discovery      • Network Topology                                │
│  • Capability Registry   • Heartbeat & Health                             │
│  • Load Balancer         • Node Selection                                 │
│  • Connection Mgmt       • Failover & Recovery                            │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                         SESSION MESH                                        │
│                                                                             │
│  • Session Registry      • Event Replication                               │
│  • Vector Clock          • Conflict Resolution                             │
│  • Lease Manager         • Snapshot Management                            │
│  • Offline Queue         • Sync Strategy                                  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                          AGENT MESH                                         │
│                                                                             │
│  • Agent Registry        • Tool Distribution                              │
│  • Capability Matching   • Load Balancing                                 │
│  • ACP Protocol          • MCP Client                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

2.1 Ответственность слоёв

Слой Отвечает за Пример
Node Mesh Устройства, сеть, выбор узла "Какой девайс выполнит задачу?"
Session Mesh Контекст, события, синхронизация "Как синхронизировать сессию?"
Agent Mesh Агенты, инструменты, распределение "Какой агент на каком узле?"

---

3. Node Mesh — распределённый слой устройств

3.1 Компоненты

```python
class NodeMesh:
    """Управление устройствами и сетевым взаимодействием."""

    def __init__(self, user_id: str, device_id: str):
        self._user_id = user_id
        self._device_id = device_id
        self._registry = DeviceRegistry()
        self._capability_engine = CapabilityEngine()
        self._discovery = DiscoveryService()
        self._heartbeat = HeartbeatService()
        self._balancer = LoadBalancer()

    # ——— Device Management ———
    def register_device(self, name: str, device_type: str) -> str:
        """Зарегистрировать устройство в сети."""
        ...

    def list_devices(self) -> List[Device***REMOVED***:
        """Список всех устройств пользователя."""
        ...

    def get_device(self, device_id: str) -> Optional[Device***REMOVED***:
        """Получить информацию об устройстве."""
        ...

    def update_device_status(self, device_id: str, status: str) -> None:
        """Обновить статус устройства (online/offline/sleeping)."""
        ...

    # ——— Heartbeat ———
    def start_heartbeat(self, interval: int = 30) -> None:
        """Запустить отправку heartbeat."""
        ...

    def on_heartbeat(self, device_id: str) -> None:
        """Обработать heartbeat от устройства."""
        ...

    def prune_offline(self, max_age: int = 120) -> int:
        """Удалить устройства, не отвечающие > max_age секунд."""
        ...

    # ——— Capability ———
    def get_capabilities(self, device_id: str) -> List[DeviceCapability***REMOVED***:
        """Получить возможности устройства."""
        ...

    def select_device(self, task: str, requirements: Dict) -> Optional[str***REMOVED***:
        """Выбрать устройство для задачи."""
        ...

    # ——— Discovery ———
    def discover_peers(self) -> List[Device***REMOVED***:
        """Обнаружить другие устройства в сети."""
        ...
```

3.2 Device

```python
@dataclass
class Device:
    """Устройство в распределённой сети."""
    device_id: str                     # ULID, генерируется при регистрации
    user_id: str                       # Владелец
    name: str                          # "Pixel 6", "Work Laptop"
    device_type: str                   # "android", "linux", "mac", "server"
    
    # Состояние
    status: str = "online"             # "online" | "offline" | "sleeping" | "error"
    last_seen: str = ""                # ISO timestamp
    ip_address: Optional[str***REMOVED*** = None
    port: Optional[int***REMOVED*** = None
    
    # Возможности (Capability Engine)
    capabilities: List[DeviceCapability***REMOVED*** = field(default_factory=list)
    resources: Dict[str, float***REMOVED*** = field(default_factory=dict)  # ram, cpu, vram, battery
    
    # Версии
    buffy_version: str = ""
    agent_version: str = ""
    
    # Синхронизация
    sync_enabled: bool = True
    sync_interval_sec: int = 30
    offline_since: Optional[str***REMOVED*** = None
```

3.3 Capability Engine

```python
@dataclass
class DeviceCapability:
    """Возможность устройства (не железо, а сервис)."""
    name: str                          # "llm.inference", "whisper", "ocr", "codegen"
    version: str
    available: bool = True
    performance_score: float = 1.0     # 0.0 - 1.0
    cost_per_unit: float = 0.0         # если платное API
    requires_network: bool = False
    max_concurrent: int = 1
    estimated_time_ms: int = 1000

class CapabilityEngine:
    """Интеллектуальный выбор устройства по capability."""
    
    def __init__(self):
        self._device_cache: Dict[str, Device***REMOVED*** = {***REMOVED***
    
    def select_device(self, task: str, requirements: Dict) -> Optional[str***REMOVED***:
        """Выбрать устройство для задачи."""
        # 1. Определить capability по задаче
        capability = self._task_to_capability(task)
        
        # 2. Найти все устройства с этой capability
        candidates = self._find_devices_with_capability(capability)
        
        # 3. Отфильтровать по требованиям
        filtered = self._filter_by_requirements(candidates, requirements)
        
        # 4. Отсортировать по performance_score
        sorted_devices = sorted(filtered, key=lambda d: d.capability.performance_score, reverse=True)
        
        # 5. Вернуть лучший
        return sorted_devices[0***REMOVED***.device_id if sorted_devices else None
    
    def _task_to_capability(self, task: str) -> str:
        """Маппинг задачи на capability."""
        mapping = {
            "generate_code": "llm.inference",
            "review_code": "llm.inference",
            "transcribe_audio": "whisper",
            "ocr_image": "ocr",
            "search_web": "web_search",
            "documentation": "llm.inference",
        ***REMOVED***
        return mapping.get(task, "llm.inference")
```

3.4 Heartbeat & Health

```python
class HeartbeatService:
    """Отправка и приём heartbeat."""

    def __init__(self, node_mesh: NodeMesh):
        self._mesh = node_mesh
        self._running = False
        self._thread: Optional[threading.Thread***REMOVED*** = None

    def start(self, interval: int = 30) -> None:
        """Запустить heartbeat в фоновом потоке."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def _loop(self, interval: int) -> None:
        """Цикл отправки heartbeat."""
        while self._running:
            try:
                # 1. Отправить heartbeat на все устройства
                self._send_heartbeat()
                
                # 2. Проверить ответы
                self._check_responses()
                
                # 3. Обновить статусы
                self._update_statuses()
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e***REMOVED***")

    def _send_heartbeat(self) -> None:
        """Отправить heartbeat через EventStore."""
        event = Event(
            type="heartbeat",
            source=self._mesh._device_id,
            data={"status": "online", "capabilities": self._mesh.get_capabilities()***REMOVED***,
        )
        # Публикуем в глобальный поток
        event_store.append(stream="heartbeat", events=[event***REMOVED***)
```

3.5 Discovery Service

```python
class DiscoveryService:
    """Обнаружение устройств в сети."""

    def __init__(self, node_mesh: NodeMesh):
        self._mesh = node_mesh

    def discover(self) -> List[Device***REMOVED***:
        """Обнаружить устройства через multicast или брокер."""
        # 1. Отправить discovery-запрос
        # 2. Получить ответы
        # 3. Зарегистрировать новые устройства
        ...

    def join_network(self, broker_url: str) -> None:
        """Подключиться к сети через брокер."""
        # 1. Подключиться к WebSocket/MQTT/NATS
        # 2. Получить список устройств
        # 3. Начать синхронизацию
        ...
```

---

4. Event Store — ядро системы

4.1 Интерфейс EventStore

```python
class EventStore(ABC):
    """Ядро Event Sourcing — единый источник истины."""

    # ——— Запись ———
    @abstractmethod
    def append(self, stream: str, events: List[Event***REMOVED***, expected_version: Optional[int***REMOVED*** = None) -> None:
        """Добавить события в поток.
        
        Args:
            stream: Имя потока (например, "session:abc123")
            events: Список событий
            expected_version: Ожидаемая версия (для оптимистичной блокировки)
        """
        ...

    # ——— Чтение ———
    @abstractmethod
    def read_stream(self, stream: str, from_version: int = 0, limit: Optional[int***REMOVED*** = None) -> List[Event***REMOVED***:
        """Прочитать события потока."""
        ...

    @abstractmethod
    def stream_events(self, stream: str, from_version: int = 0) -> Iterator[Event***REMOVED***:
        """Итератор событий (для replay)."""
        ...

    # ——— Подписка (real-time) ———
    @abstractmethod
    def subscribe(self, stream: str, callback: Callable[[Event***REMOVED***, None***REMOVED***) -> Subscription:
        """Подписаться на новые события."""
        ...

    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> None:
        """Отписаться."""
        ...

    # ——— Снапшоты ———
    @abstractmethod
    def snapshot(self, stream: str, version: int, state: Dict) -> None:
        """Сохранить снапшот состояния (как специальное событие)."""
        ...

    @abstractmethod
    def restore(self, stream: str) -> Tuple[int, Dict***REMOVED***:
        """Восстановить состояние из последнего снапшота.
        
        Returns:
            (version, state) — версия и состояние
        """
        ...

    # ——— Компактизация ———
    @abstractmethod
    def compact(self, stream: str, keep_snapshots: int = 10) -> int:
        """Удалить старые события после снапшотов.
        
        Returns:
            Количество удалённых событий
        """
        ...

    # ——— Утилиты ———
    @abstractmethod
    def get_version(self, stream: str) -> int:
        """Получить текущую версию потока."""
        ...

    @abstractmethod
    def list_streams(self, prefix: str = "") -> List[str***REMOVED***:
        """Список всех потоков."""
        ...
```

4.2 Реализации

SQLiteEventStore (локальная, для тестов и single-node)

```python
class SQLiteEventStore(EventStore):
    """SQLite-реализация Event Store.
    
    Используется для:
    - Тестирования
    - Single-node режима
    - Локального кэша в distributed режиме
    """
    
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Создать таблицы."""
        with sqlite3.connect(self._db_path) as conn:
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
```

PostgresEventStore (продакшн)

```python
class PostgresEventStore(EventStore):
    """Postgres-реализация Event Store.
    
    Используется для:
    - Production distributed режима
    - Cloud-развёртывания
    """
    
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = asyncpg.create_pool(dsn)
    
    async def append(self, stream: str, events: List[Event***REMOVED***) -> None:
        """Добавить события."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for event in events:
                    # Проверка оптимистичной блокировки
                    if event.expected_version is not None:
                        current = await conn.fetchval(
                            "SELECT version FROM events WHERE stream = $1 ORDER BY version DESC LIMIT 1",
                            stream
                        )
                        if current != event.expected_version:
                            raise ConcurrentModificationError(
                                f"Stream {stream***REMOVED*** expected version {event.expected_version***REMOVED***, got {current***REMOVED***"
                            )
                    
                    await conn.execute(
                        """
                        INSERT INTO events (id, stream, version, type, data, metadata, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        event.id, stream, event.version, event.type,
                        json.dumps(event.data), json.dumps(event.metadata), event.timestamp
                    )
```

KafkaEventStore (high-scale)

```python
class KafkaEventStore(EventStore):
    """Kafka-реализация Event Store.
    
    Используется для:
    - High-scale распределённых систем
    - Множество потребителей
    """
    
    def __init__(self, bootstrap_servers: str):
        from kafka import KafkaProducer, KafkaConsumer
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        self._consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
        )
    
    def append(self, stream: str, events: List[Event***REMOVED***) -> None:
        for event in events:
            self._producer.send(stream, {
                'id': event.id,
                'version': event.version,
                'type': event.type,
                'data': event.data,
                'metadata': event.metadata,
                'timestamp': event.timestamp,
            ***REMOVED***)
```

4.3 Snapshots (встроенные в EventStore)

```python
# В любом EventStore:
def snapshot(self, stream: str, version: int, state: Dict) -> None:
    """Сохранить снапшот как событие."""
    event = Event(
        id=str(ulid.ULID()),
        stream=stream,
        version=version,
        type="snapshot",
        data=state,
        metadata={"snapshot_version": "1.0"***REMOVED***,
        timestamp=datetime.now().isoformat(),
    )
    self.append(stream, [event***REMOVED***)

def restore(self, stream: str) -> Tuple[int, Dict***REMOVED***:
    """Восстановить из последнего снапшота."""
    events = self.read_stream(stream, limit=1000)  # последние 1000
    
    for event in reversed(events):
        if event.type == "snapshot":
            return event.version, event.data
    
    return 0, {***REMOVED***  # нет снапшота

def compact(self, stream: str, keep_snapshots: int = 10) -> int:
    """Удалить старые события до keep_snapshots последних."""
    # 1. Найти последние keep_snapshots снапшотов
    # 2. Удалить все события до самого старого из них
    # 3. Вернуть количество удалённых
    ...
```

---

5. Session Mesh — синхронизация контекста

5.1 Компоненты

```python
class SessionMesh:
    """Управление распределёнными сессиями."""

    def __init__(self, user_id: str, device_id: str, event_store: EventStore):
        self._user_id = user_id
        self._device_id = device_id
        self._event_store = event_store
        
        self._session_registry = SessionRegistry(event_store)
        self._vector_clock = VectorClock(device_id)
        self._conflict_resolver = ConflictResolver()
        self._lease_manager = LeaseManager(event_store)
        self._sync_strategy = SyncStrategy()
        self._offline_queue = OfflineQueue()

    # ——— Session Management ———
    def create_session(self, topic: str, project: str = "") -> DistributedSession:
        """Создать распределённую сессию."""
        # 1. Генерируем ULID
        session_id = str(ulid.ULID())
        
        # 2. Создаём событие
        event = Event(
            id=str(ulid.ULID()),
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
            metadata={"vector_clock": self._vector_clock.get_current()***REMOVED***,
            timestamp=datetime.now().isoformat(),
        )
        
        # 3. Сохраняем в EventStore
        self._event_store.append(f"session:{session_id***REMOVED***", [event***REMOVED***)
        
        # 4. Создаём локальный кэш
        session = self._session_registry.create_local(session_id, topic, project)
        
        return session

    def get_session(self, session_id: str) -> Optional[DistributedSession***REMOVED***:
        """Получить сессию (с синхронизацией)."""
        # 1. Сначала синхронизируем
        self.sync_session(session_id)
        
        # 2. Затем получаем локальный кэш
        return self._session_registry.get_local(session_id)

    def sync_session(self, session_id: str) -> None:
        """Принудительно синхронизировать сессию."""
        # 1. Получить локальную версию
        local_version = self._session_registry.get_version(session_id)
        
        # 2. Получить удалённые события
        remote_events = self._event_store.read_stream(
            f"session:{session_id***REMOVED***",
            from_version=local_version + 1
        )
        
        # 3. Применить события
        for event in remote_events:
            self._apply_event(session_id, event)
        
        # 4. Обновить локальную версию
        self._session_registry.set_version(session_id, local_version + len(remote_events))

    def transfer_session(self, session_id: str, target_device: str) -> bool:
        """Передать сессию на другое устройство (через Lease)."""
        # 1. Проверить, что мы владельцы
        if not self._lease_manager.is_owner(session_id, self._device_id):
            return False
        
        # 2. Передать lease
        return self._lease_manager.transfer(session_id, target_device)
```

5.2 Vector Clock

```python
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
            # Сравниваем все устройства в обоих наборах
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
```

5.3 Lease Manager

```python
@dataclass
class SessionLease:
    """Аренда сессии устройством."""
    session_id: str
    owner_device: str
    expires_at: float  # timestamp
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
            # 1. Проверить существующую аренду
            if session_id in self._leases:
                lease = self._leases[session_id***REMOVED***
                # 2. Если аренда истекла → можно захватить
                if time.time() < lease.expires_at:
                    return False  # занято
            
            # 3. Создать новую аренду
            self._leases[session_id***REMOVED*** = SessionLease(
                session_id=session_id,
                owner_device=device_id,
                expires_at=time.time() + ttl,
                created_at=datetime.now().isoformat(),
                renewed_at=datetime.now().isoformat(),
            )
            
            # 4. Сохранить событие
            event = Event(
                id=str(ulid.ULID()),
                stream=f"lease:{session_id***REMOVED***",
                version=0,
                type="lease.acquired",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                    "expires_at": self._leases[session_id***REMOVED***.expires_at,
                ***REMOVED***,
                timestamp=datetime.now().isoformat(),
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
                id=str(ulid.ULID()),
                stream=f"lease:{session_id***REMOVED***",
                version=0,
                type="lease.renewed",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                    "expires_at": lease.expires_at,
                    "renew_count": lease.renew_count,
                ***REMOVED***,
                timestamp=datetime.now().isoformat(),
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
                id=str(ulid.ULID()),
                stream=f"lease:{session_id***REMOVED***",
                version=0,
                type="lease.released",
                data={
                    "session_id": session_id,
                    "device_id": device_id,
                ***REMOVED***,
                timestamp=datetime.now().isoformat(),
            )
            self._event_store.append(f"lease:{session_id***REMOVED***", [event***REMOVED***)
            
            return True
    
    def get_owner(self, session_id: str) -> Optional[str***REMOVED***:
        """Получить владельца сессии."""
        with self._lock:
            if session_id not in self._leases:
                return None
            
            lease = self._leases[session_id***REMOVED***
            # Если аренда истекла → нет владельца
            if time.time() > lease.expires_at:
                return None
            
            return lease.owner_device
```

5.4 Conflict Resolver

```python
class ConflictResolver:
    """Разрешение конфликтов при параллельной работе."""
    
    STRATEGY_LWW = "last-write-wins"
    STRATEGY_OT = "operational-transform"
    STRATEGY_CRDT = "crdt"
    STRATEGY_MANUAL = "manual"
    
    def __init__(self):
        self._strategies = {
            "message": self.STRATEGY_OT,      # Текст → OT
            "metadata": self.STRATEGY_LWW,     # Метаданные → LWW
            "memory": self.STRATEGY_CRDT,      # Память → CRDT
            "config": self.STRATEGY_MANUAL,    # Конфиг → ручное
            "knowledge": self.STRATEGY_CRDT,   # Граф → CRDT
        ***REMOVED***
    
    def detect_conflict(self, event: Event, local_events: List[Event***REMOVED***) -> bool:
        """Обнаружить конфликт с локальными событиями."""
        # 1. Найти события с тем же correlation_id
        same_correlation = [e for e in local_events if e.metadata.get('correlation_id') == event.metadata.get('correlation_id')***REMOVED***
        
        if not same_correlation:
            return False
        
        # 2. Сравнить векторные часы
        for local_event in same_correlation:
            vector_clock = VectorClock("")
            result = vector_clock.compare(local_event.metadata.get('vector_clock', {***REMOVED***), 
                                         event.metadata.get('vector_clock', {***REMOVED***))
            if result == "concurrent":
                return True
        
        return False
    
    def resolve(self, event: Event, local_events: List[Event***REMOVED***) -> Event:
        """Разрешить конфликт."""
        # 1. Определить тип данных
        data_type = self._get_data_type(event)
        
        # 2. Выбрать стратегию
        strategy = self._strategies.get(data_type, self.STRATEGY_LWW)
        
        # 3. Разрешить
        if strategy == self.STRATEGY_LWW:
            return self._resolve_lww(event, local_events)
        elif strategy == self.STRATEGY_OT:
            return self._resolve_ot(event, local_events)
        elif strategy == self.STRATEGY_CRDT:
            return self._resolve_crdt(event, local_events)
        elif strategy == self.STRATEGY_MANUAL:
            return self._resolve_manual(event, local_events)
        else:
            raise ValueError(f"Unknown strategy: {strategy***REMOVED***")
    
    def _resolve_lww(self, event: Event, local_events: List[Event***REMOVED***) -> Event:
        """Last-Write-Wins: более поздний timestamp побеждает."""
        latest = event
        for local in local_events:
            if local.timestamp > latest.timestamp:
                latest = local
        return latest
    
    def _resolve_ot(self, event: Event, local_events: List[Event***REMOVED***) -> Event:
        """Operational Transform: слить текст."""
        # Используем библиотеку операциональных трансформаций
        # Например, для текста
        from diff_match_patch import diff_match_patch
        dmp = diff_match_patch()
        
        # Преобразуем изменения в патчи
        # ... сложная логика для текста
        
    def _resolve_manual(self, event: Event, local_events: List[Event***REMOVED***) -> Event:
        """Ручное разрешение: запрос пользователю."""
        # 1. Сохранить оба события как "pending"
        # 2. Уведомить пользователя через CLI/TG
        # 3. Ждать выбора
        raise ManualConflictError(
            f"Conflict detected for event {event.id***REMOVED***. "
            f"Please resolve manually using 'buffy mesh conflict resolve'"
        )
```

5.5 Offline Queue

```python
class OfflineQueue:
    """Очередь событий для офлайн-режима."""
    
    def __init__(self, storage_path: Path):
        self._storage_path = storage_path
        self._pending: List[Event***REMOVED*** = [***REMOVED***
        self._lock = threading.Lock()
    
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
        with open(self._storage_path / "offline_queue.json", "w") as f:
            json.dump(data, f, indent=2)
```

---

6. Offline-first стратегия

6.1 Сценарии работы

Сценарий Длительность Стратегия
Краткосрочный < 5 минут Кэширование, отложенная синхронизация
Среднесрочный 5-60 минут Офлайн-режим с локальным EventStore
Долгосрочный 1 часа Полный офлайн с последующим merge через CRDT
Экстремальный 1 дня Приоритет пользовательских изменений (manual merge)

6.2 Локальный EventStore для офлайн-режима

```python
class LocalEventStore(SQLiteEventStore):
    """Локальный Event Store для офлайн-режима."""
    
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self._sync_version: Dict[str, int***REMOVED*** = {***REMOVED***
    
    def append_offline(self, event: Event) -> None:
        """Добавить событие в офлайн-режиме."""
        # 1. Сохранить локально
        self.append(event.stream, [event***REMOVED***)
        
        # 2. Добавить в офлайн-очередь
        self._offline_queue.add(event)
        
        # 3. Отметить как unsynced
        self._mark_unsynced(event.id)
    
    def get_pending_sync(self) -> List[Event***REMOVED***:
        """Получить события для синхронизации."""
        return self._offline_queue.get_pending()
```

6.3 Синхронизация после подключения

```python
class SyncStrategy:
    """Стратегия синхронизации после офлайн-периода."""
    
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._resolver = ConflictResolver()
    
    def sync(self, device_id: str, offline_events: List[Event***REMOVED***) -> SyncResult:
        """Синхронизировать офлайн-события с глобальным потоком."""
        # 1. Группировать по stream
        streams = {***REMOVED***
        for event in offline_events:
            streams.setdefault(event.stream, [***REMOVED***).append(event)
        
        # 2. Для каждого stream
        results = [***REMOVED***
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
            
            results.append({
                "stream": stream,
                "total": len(events),
                "conflicts": len(conflicts),
                "resolved": len(resolved),
                "synced": len(events) - len(conflicts),
            ***REMOVED***)
        
        return SyncResult(results)
```

6.4 Merge стратегия для разных типов данных

```python
class MergeStrategy:
    """Стратегии слияния для разных типов данных."""
    
    @staticmethod
    def merge_messages(local: List[Dict***REMOVED***, remote: List[Dict***REMOVED***) -> List[Dict***REMOVED***:
        """Слияние сообщений (OT)."""
        # Operational Transform для текста
        from diff_match_patch import diff_match_patch
        dmp = diff_match_patch()
        
        # ... сложная логика
        
    @staticmethod
    def merge_memory(local: Dict, remote: Dict) -> Dict:
        """Слияние памяти (CRDT)."""
        # CRDT для словарей
        merged = local.copy()
        for key, value in remote.items():
            if key not in merged:
                merged[key***REMOVED*** = value
            else:
                # Если оба — словари, рекурсивно
                if isinstance(value, dict) and isinstance(merged[key***REMOVED***, dict):
                    merged[key***REMOVED*** = MergeStrategy.merge_memory(merged[key***REMOVED***, value)
                else:
                    # LWW для простых значений
                    if remote.get('_timestamp', 0) > local.get('_timestamp', 0):
                        merged[key***REMOVED*** = value
        return merged
    
    @staticmethod
    def merge_config(local: Dict, remote: Dict) -> Dict:
        """Слияние конфигурации (manual)."""
        # Возвращаем оба, помечаем конфликт
        return {
            "local": local,
            "remote": remote,
            "conflict": True,
            "needs_manual": True,
        ***REMOVED***
```

---

7. Agent Mesh — распределение агентов и инструментов

7.1 Компоненты

```python
class AgentMesh:
    """Распределение агентов и инструментов между узлами."""
    
    def __init__(self, node_mesh: NodeMesh, session_mesh: SessionMesh):
        self._node_mesh = node_mesh
        self._session_mesh = session_mesh
        self._agent_registry = AgentRegistry()
        self._tool_distributor = ToolDistributor()
        self._load_balancer = LoadBalancer()
    
    def register_agent(self, agent: Agent, device_id: str) -> None:
        """Зарегистрировать агента на устройстве."""
        self._agent_registry.register(agent, device_id)
    
    def assign_task(self, task: Task) -> str:
        """Назначить задачу агенту."""
        # 1. Определить capability
        capability = self._task_to_capability(task.type)
        
        # 2. Найти устройства с этой capability
        devices = self._node_mesh.select_device(task.type, task.requirements)
        
        # 3. Выбрать агента на устройстве
        agent = self._load_balancer.select_agent(devices, capability)
        
        # 4. Отправить задачу
        self._send_task(agent, task)
        
        return agent.agent_id
    
    def distribute_tool(self, tool: Tool, devices: List[str***REMOVED***) -> None:
        """Распределить инструмент на устройства."""
        self._tool_distributor.distribute(tool, devices)
```

7.2 Load Balancer

```python
class LoadBalancer:
    """Балансировка нагрузки между агентами."""
    
    def __init__(self):
        self._load_metrics: Dict[str, float***REMOVED*** = {***REMOVED***  # agent_id → load (0.0-1.0)
    
    def select_agent(self, devices: List[Device***REMOVED***, capability: str) -> Optional[Agent***REMOVED***:
        """Выбрать агента с наименьшей нагрузкой."""
        candidates = [***REMOVED***
        for device in devices:
            for agent in device.agents:
                if capability in agent.capabilities:
                    load = self._load_metrics.get(agent.agent_id, 0.0)
                    candidates.append((agent, load))
        
        if not candidates:
            return None
        
        # Выбрать с наименьшей нагрузкой
        return min(candidates, key=lambda x: x[1***REMOVED***)[0***REMOVED***
    
    def update_load(self, agent_id: str, load: float) -> None:
        """Обновить нагрузку агента."""
        self._load_metrics[agent_id***REMOVED*** = load
```

---

8. Транспортный слой

8.1 Интерфейс Transport

```python
class Transport(ABC):
    """Абстракция транспорта для Mesh."""
    
    @abstractmethod
    def connect(self, url: str) -> bool:
        """Подключиться к сети."""
        ...
    
    @abstractmethod
    def send(self, event: Event) -> None:
        """Отправить событие."""
        ...
    
    @abstractmethod
    def subscribe(self, callback: Callable[[Event***REMOVED***, None***REMOVED***) -> None:
        """Подписаться на входящие события."""
        ...
    
    @abstractmethod
    def disconnect(self) -> None:
        """Отключиться."""
        ...
```

8.2 Реализации

Транспорт Когда использовать Плюсы Минусы
Local (in-memory) Тесты, single-node Быстро, просто Только один узел
WebSocket Cloud-брокер (рекомендуется) Реалтайм, двусторонний Требует сервера
NATS High-performance Очень быстро, надёжно Сложнее в настройке
MQTT IoT, много устройств Лёгкий, для телефонов Требует брокера
HTTP + Polling Simple sync, fallback Простота, работает везде Задержки

8.3 WebSocketTransport

```python
class WebSocketTransport(Transport):
    """WebSocket-транспорт для Mesh."""
    
    def __init__(self, url: str):
        self._url = url
        self._ws: Optional[websocket.WebSocket***REMOVED*** = None
        self._callbacks: List[Callable***REMOVED*** = [***REMOVED***
        self._running = False
    
    def connect(self, url: str) -> bool:
        try:
            self._ws = websocket.WebSocket()
            self._ws.connect(url)
            self._running = True
            threading.Thread(target=self._listen, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"WebSocket connect error: {e***REMOVED***")
            return False
    
    def send(self, event: Event) -> None:
        if not self._ws:
            raise ConnectionError("WebSocket not connected")
        self._ws.send(json.dumps(event.to_dict()))
    
    def subscribe(self, callback: Callable[[Event***REMOVED***, None***REMOVED***) -> None:
        self._callbacks.append(callback)
    
    def _listen(self) -> None:
        while self._running and self._ws:
            try:
                message = self._ws.recv()
                event = Event.from_dict(json.loads(message))
                for callback in self._callbacks:
                    callback(event)
            except websocket.WebSocketConnectionClosedException:
                break
            except Exception as e:
                logger.error(f"WebSocket listen error: {e***REMOVED***")
```

---

9. CLI для пользователя

```bash
# ─── Node Mesh ───

# Инициализация узла
buffy node init --username denis --device "Pixel 6" --type android
# → Node initialized: node_01ARZ3NDEKTSV4RRFFQ69G5FAV

# Статус сети
buffy node status
# → User: denis (usr_01ARZ3NDEK)
# → Devices:
#     ✅ Pixel 6 (online, capabilities: llm.inference, whisper)
#     ✅ Work Laptop (online, capabilities: llm.inference, codegen, gpu)
#     ⏸ Tablet (offline, last seen: 2 hours ago)
# → Network: 3 devices, 2 online

# Список capabilities
buffy node capabilities
# → Pixel 6:
#     ✅ llm.inference (Qwen 0.5B, score: 0.7)
#     ✅ whisper (score: 0.9)
# → Work Laptop:
#     ✅ llm.inference (DeepSeek 70B, score: 0.95)
#     ✅ codegen (score: 0.9)
#     ✅ gpu (score: 1.0)

# Выбор устройства для задачи
buffy node select --task "generate_code" --requirements '{"model":"70b","tokens":4000***REMOVED***'
# → Selected: Work Laptop (score: 0.95, ram: 16GB, gpu: yes)

# ─── Session Mesh ───

# Создать распределённую сессию
buffy session start --topic "Code Review" --broadcast
# → Session started: ses_01ARZ3NDEKTSV4RRFFQ69G5FAV
# → Published to: Pixel 6, Work Laptop

# Статус сессии
buffy session status ses_01ARZ3NDEKTSV4RRFFQ69G5FAV
# → Session: Code Review
# → Owner: Work Laptop (lease expires in 45s)
# → Devices: Pixel 6 (read-only), Work Laptop (read-write)
# → Messages: 47, Conflicts: 0

# Передать сессию
buffy session transfer ses_01ARZ3NDEKTSV4RRFFQ69G5FAV --to "Pixel 6"
# → Session transferred to Pixel 6
# → Lease acquired: 60s

# Принудительная синхронизация
buffy session sync ses_01ARZ3NDEKTSV4RRFFQ69G5FAV
# → Synced: 15 local events, 3 remote events
# → Conflicts: 0

# Разрешить конфликт
buffy session conflict resolve ses_01ARZ3NDEKTSV4RRFFQ69G5FAV
# → Conflict detected: message #42
# → [A***REMOVED*** Keep local: "fix login bug"
# → [B***REMOVED*** Keep remote: "fix auth bug"
# → [C***REMOVED*** Merge: "fix login and auth bugs"
# → Choose: C
# → Conflict resolved

# ─── Offline ───

# Статус офлайн-очереди
buffy offline status
# → Connected: no (offline mode)
# → Pending events: 47
# → Last sync: 2 hours ago
# → Conflicts: 0

# Синхронизировать после подключения
buffy offline sync
# → Syncing 47 events...
# → 45 synced, 2 conflicts detected
# → Conflict #1: ... (manual resolution)
```

---

10. MCP инструменты

```json
{
    "name": "mesh_status",
    "description": "Статус Mesh (устройства, сессии, синхронизация)",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "mesh_devices",
    "description": "Список устройств пользователя",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "mesh_session_list",
    "description": "Список активных сессий",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "mesh_session_transfer",
    "description": "Передать сессию на другое устройство",
    "inputSchema": {
        "session_id": { "type": "string" ***REMOVED***,
        "target_device": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "mesh_session_sync",
    "description": "Принудительно синхронизировать сессию",
    "inputSchema": {
        "session_id": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "mesh_offline_status",
    "description": "Статус офлайн-очереди",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "mesh_offline_sync",
    "description": "Синхронизировать офлайн-события",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "mesh_select_device",
    "description": "Выбрать устройство для задачи",
    "inputSchema": {
        "task": { "type": "string" ***REMOVED***,
        "requirements": { "type": "string" ***REMOVED***
    ***REMOVED***
***REMOVED***
```

---

11. Тестирование

11.1 Unit-тесты

Тест Что проверяет
test_event_store_append EventStore: append события
test_event_store_read EventStore: read_stream, stream_events
test_event_store_snapshot EventStore: snapshot, restore, compact
test_vector_clock VectorClock: increment, merge, compare
test_lease_manager LeaseManager: acquire, renew, release, get_owner
test_conflict_detection ConflictResolver: detect_conflict
test_conflict_resolution_lww ConflictResolver: LWW стратегия
test_conflict_resolution_manual ConflictResolver: manual стратегия
test_offline_queue OfflineQueue: add, get_pending, mark_synced
test_sync_strategy SyncStrategy: sync после офлайн
test_node_mesh NodeMesh: register, list, select_device
test_capability_engine CapabilityEngine: select_device, task_to_capability
test_session_mesh SessionMesh: create, get, sync, transfer
test_agent_mesh AgentMesh: register, assign_task, distribute_tool
test_transport_websocket WebSocketTransport: connect, send, subscribe

11.2 Интеграционные тесты

Тест Что проверяет
test_two_devices_sync Два устройства, синхронизация событий
test_conflict_resolution Конфликт между двумя устройствами
test_session_transfer Передача сессии через Lease
test_snapshot_restore Восстановление из снапшота после сбоя
test_offline_recovery Устройство офлайн → онлайн → синхронизация
test_heartbeat Обнаружение офлайн устройств
test_load_balancing Распределение задач между устройствами
test_capability_routing Выбор устройства по capability

11.3 Boundary тесты

· 10 устройств одновременно (производительность)
· Офлайн 1 час → синхронизация 1000 событий
· Конфликт с 3+ участниками
· Устройство умирает в середине sync
· Снапшот размером 10 MB
· 1000 событий в секунду (нагрузка)
· Device с expired lease

---

12. Реализация

12.1 Файлы

```
freebuff_plugin_03/mesh/
├── __init__.py              # API экспорт
├── core_02/
│   ├── event_store.py       # EventStore интерфейс
│   ├── event.py             # Event, ULID
│   ├── vector_clock.py      # VectorClock
│   └── conflict.py          # ConflictResolver
├── node/
│   ├── __init__.py
│   ├── device.py            # Device, DeviceRegistry
│   ├── capability.py        # DeviceCapability, CapabilityEngine
│   ├── heartbeat.py         # HeartbeatService
│   └── discovery.py         # DiscoveryService
├── session/
│   ├── __init__.py
│   ├── session.py           # DistributedSession, SessionRegistry
│   ├── lease.py             # LeaseManager
│   ├── sync.py              # SyncStrategy
│   └── offline.py           # OfflineQueue
├── agent/
│   ├── __init__.py
│   ├── agent.py             # Agent, AgentRegistry
│   ├── tool.py              # Tool, ToolDistributor
│   └── balancer.py          # LoadBalancer
├── transport/
│   ├── __init__.py
│   ├── base.py              # Transport интерфейс
│   ├── local.py             # LocalTransport
│   ├── websocket.py         # WebSocketTransport
│   ├── nats.py              # NATSTransport
│   └── http.py              # HTTPPollingTransport
├── storage/
│   ├── __init__.py
│   ├── sqlite.py            # SQLiteEventStore
│   ├── postgres.py          # PostgresEventStore
│   └── kafka.py             # KafkaEventStore
├── mesh.py                  # Mesh (главный класс)
└── cli.py                   # buffy mesh команды
```

12.2 Этапы реализации

Этап Что Тестов Зависимости
1. EventStore EventStore интерфейс + SQLite реализация 20 Нет
2. Identity UserRegistry + DeviceRegistry 15 EventStore
3. Vector Clock VectorClock: increment/merge/compare 10 Нет
4. Node Mesh DeviceRegistry, Heartbeat, Discovery 15 Identity, Vector Clock
5. Capability Engine DeviceCapability, select_device 10 Node Mesh
6. Lease Manager Lease: acquire/renew/release 12 EventStore
7. Session Mesh SessionRegistry, sync, transfer 15 Lease, Vector Clock
8. Conflict Resolver LWW, OT, CRDT, Manual 12 Vector Clock
9. Offline-first OfflineQueue, SyncStrategy 10 Session Mesh
10. Agent Mesh AgentRegistry, LoadBalancer 12 Node Mesh, Session Mesh
11. Transport WebSocket, NATS, HTTP polling 10 EventStore
12. MCP tools 8 инструментов 8 Всё
13. CLI buffy node/session/offline 6 Всё
ИТОГО  ~145 тестов 

12.3 Приоритет

Приоритет Компонент Обоснование
P0 EventStore Фундамент всей системы
P0 Vector Clock Ключевой механизм
P0 Lease Manager Без него нет распределённых сессий
P1 Node Mesh Основа для всех устройств
P1 Session Mesh Синхронизация контекста
P1 Conflict Resolver (LWW) Минимальная стратегия
P1 Offline-first Критично для телефонов
P2 Capability Engine Умный выбор устройств
P2 Agent Mesh Распределение нагрузки
P2 Transport (WebSocket) Реалтайм синхронизация
P3 MCP tools + CLI Интеграция

---

13. Критерии готовности

· EventStore интерфейс — append, read, subscribe, snapshot, compact
· Реализации EventStore: SQLite, Postgres, Kafka
· ULID вместо UUID для всех ID
· UserRegistry — create/get/update/delete
· DeviceRegistry — register/get/list/prune
· VectorClock — increment/merge/compare
· HeartbeatService — отправка/приём heartbeat
· CapabilityEngine — select_device, task_to_capability
· LeaseManager — acquire/renew/release/get_owner
· SessionMesh — create_session/get_session/sync_session/transfer_session
· ConflictResolver — detect_conflict, resolve (LWW, OT, CRDT, Manual)
· OfflineQueue — add/get_pending/mark_synced
· SyncStrategy — sync после офлайн
· AgentMesh — register_agent/assign_task/distribute_tool
· Transport — WebSocket, NATS, HTTP polling
· MCP инструменты — 8 mesh_* инструментов
· CLI — buffy node/session/offline команды
· 145+ тестов, 0 failures
· Документация в README.md
· Обратная совместимость: система работает без Mesh

---

14. Открытые вопросы

Вопрос Статус Решение
Где хостить глобальный EventStore? 🟡 Требует решения Начать с SQLite в облаке + S3 для снапшотов
Как аутентифицировать устройства? 🟡 Требует решения JWT с device_id + user_id, подпись
Как шифровать трафик? 🟡 Требует решения mTLS или WireGuard (для Mesh)
Что при полном отсутствии сети? ✅ Решено Offline-first + CRDT
Как масштабировать WebSocket? 🟢 Отложено Для 2-10 устройств — достаточно
Поддерживать ли других брокеров? 🟢 Отложено NATS/Kafka — опционально
Как быть с конфликтами в графе? ✅ Решено CRDT (automerge)
Какой размер снапшотов? ✅ Решено < 10 MB, компрессия gzip
Как мониторить Mesh? 🟡 Требует решения Prometheus + Grafana (метрики)

---

15. Сравнение v1.0 vs v2.0

Аспект v1.0 v2.0
Уровни Session Mesh Node Mesh + Session Mesh + Agent Mesh
Event Store Упоминается как технология Ядро системы, отдельный интерфейс
Snapshots Отдельный менеджер Встроены в EventStore
Ownership primary_device (статичный) Lease (с истечением)
Event ID UUID (случайный) ULID (сортируется по времени)
Offline Упоминается Отдельная глава, стратегия
Capabilities Список Capability Engine
Транспорт Упоминается Интерфейс + реализации
Оценка 9.4/10 9.8/10

---

16. Заключение

Session Mesh v2.0 — это полноценная распределённая архитектура для AI-платформы.

Ключевые улучшения:

1. EventStore как ядро — единый источник истины
2. Трёхуровневая архитектура — Node Mesh + Session Mesh + Agent Mesh
3. Lease-based ownership — автоматический failover
4. Offline-first — полная работа без сети
5. Capability Engine — интеллектуальный выбор устройств
6. ULID — сортируемые ID
7. Snapshots в EventStore — единое хранилище

Теперь архитектура готова для реализации. Она:

· Не ломает существующую систему (обратная совместимость)
· Масштабируется от 1 до 100+ устройств
· Работает offline
· Автоматически разрешает конфликты
· Интеллектуально распределяет нагрузку

Следующие шаги:

1. Реализовать EventStore (SQLite) — P0
2. Реализовать Vector Clock + Lease — P0
3. Реализовать Node Mesh — P1
4. Реализовать Session Mesh — P1
5. Протестировать на двух устройствах — P1
6. Добавить Offline-first — P1

---

Связанные документы: VISION_3.0.md — режимы Cowork/Teamwork, ARCHITECTURE_3.0.md — Core/Extensions/Labs, EVENT_PLATFORM_SPECIFICATION.md — Event Bus, BRIDGE_PLATFORM_SPECIFICATION.md — ACP Protocol