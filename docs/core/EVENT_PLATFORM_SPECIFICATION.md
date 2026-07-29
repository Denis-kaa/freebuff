# EVENT PLATFORM SPECIFICATION — Event Store, Replay, Timeline, Audit

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** 🟡 Production (Event Bus) + План (Event Store, Replay, Timeline, Audit)  
> **Основание:** [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [promt14.md***REMOVED***(../pompts/promt14.md) (концепция #14)  

---

## Содержание

1. [Executive Summary***REMOVED***(#1-executive-summary)
2. [Текущий Event Bus***REMOVED***(#2-текущий-event-bus)
3. [Event Store***REMOVED***(#3-event-store)
4. [Event Replay***REMOVED***(#4-event-replay)
5. [Timeline***REMOVED***(#5-timeline)
6. [Audit***REMOVED***(#6-audit)
7. [Project Pulse***REMOVED***(#7-project-pulse)
8. [Интеграция с архитектурой***REMOVED***(#8-интеграция-с-архитектурой)
9. [MCP инструменты***REMOVED***(#9-mcp-инструменты)
10. [CLI***REMOVED***(#10-cli)
11. [Тестирование***REMOVED***(#11-тестирование)
12. [Реализация***REMOVED***(#12-реализация)
13. [Миграция данных***REMOVED***(#13-миграция-данных)
14. [Критерии готовности***REMOVED***(#14-критерии-готовности)

---

## 1. Executive Summary

**Event Platform** — это компонент Core, построенный на существующем Event Bus,
который добавляет постоянное хранение, воспроизведение, временную шкалу и аудит событий.

**Текущий статус:**
- Event Bus (scripts/event_bus.py) — ✅ Production, publish/subscribe, ~20 тестов
- Event Subscribers (scripts/event_subscribers.py) — ✅ Production, 4 теста
- Event Log (SQLite `context/events.db`) — ✅ Production, логирование всех событий

**Что добавляется:**
- **Event Store** — структурированное долговременное хранение с категоризацией
- **Event Replay** — воспроизведение событий для восстановления состояния
- **Timeline** — временная шкала изменений проекта
- **Audit** — аудит всех решений и действий
- **Project Pulse** — лента событий для пользователя

```
Поток событий:
  Компоненты → Event Bus (publish/subscribe)
                   │
                   ├──→ Event Log (SQLite)        ← текущий
                   ├──→ Event Store (SQLite v2)   ← план
                   ├──→ Subscribers (реакция)      ← текущий
                   └──→ Timeline / Audit / Pulse   ← план
```

---

## 2. Текущий Event Bus

### 2.1 События по категориям

| Категория | Типы | Источник |
|-----------|------|----------|
| `system.*` | startup, shutdown, error | EventBus |
| `session.*` | created, completed, checkpoint | ContextManager |
| `task.*` | created, completed, failed | Orchestrator |
| `step.*` | started, completed, failed, retrying | Orchestrator |
| `memory.*` | stored, deleted, cleared | MemoryEngine |
| `knowledge.*` | indexed, searched, rebuilt | KnowledgeEngine |
| `mcp.*` | server.initialized, tool.called, bridge.* | MCP Server, Bridge |
| `plugin.*` | enabled, disabled | Plugin API |

### 2.2 Структура Event

```python
@dataclass
class Event:
    type: str                    # "task.completed"
    data: Dict[str, Any***REMOVED***
    source: str                  # "orchestrator", "memory_engine"
    id: str                      # uuid4 hex[:12***REMOVED***
    timestamp: str               # ISO 8601
    metadata: Dict[str, Any***REMOVED***     # correlation_id, session_id, user_id
```

### 2.3 Текущие подписчики

```python
# event_subscribers.py
memory.stored     → KnowledgeEngine.index()  # авто-индексация
checkpoint.created → консольный лог
memory.cleared    → уведомление о перестройке индекса
```

### 2.4 Ограничения текущей реализации

| Аспект | Текущее | Нужно |
|--------|---------|-------|
| **Хранение** | `INSERT OR IGNORE` в один лог | Структурированный Event Store с категориями |
| **Поиск** | Только по event_type + timestamp | Полнотекстовый поиск по data, фильтры |
| **Replay** | Нет | Воспроизведение событий для восстановления |
| **Timeline** | Нет | Временная шкала по проекту |
| **Audit** | Нет | Кто, когда, какое решение принял |
| **Pulse** | Нет | Лента для пользователя |

---

## 3. Event Store

### 3.1 Архитектура

```python
class EventStore:
    """Структурированное хранилище событий.

    Расширяет Event Log с категоризацией, поиском и агрегацией.
    """

    def __init__(self, db_path: Optional[Path***REMOVED*** = None):
        self._db_path = db_path or Path("context/events.db")

    # ——— Запись ———
    def store(self, event: Event) -> str:
        """Сохранить событие в Event Store. Возвращает event_id."""
        ...

    def store_batch(self, events: List[Event***REMOVED***) -> int:
        """Batch-сохранение для производительности."""
        ...

    # ——— Поиск ———
    def query(self, query: EventQuery) -> List[EventEntry***REMOVED***:
        """Поиск событий с фильтрацией."""
        ...

    def get_by_id(self, event_id: str) -> Optional[EventEntry***REMOVED***:
        """Получить событие по ID."""
        ...

    def get_by_correlation_id(self, correlation_id: str) -> List[EventEntry***REMOVED***:
        """Получить все события в цепочке (task → step → result)."""
        ...

    def get_by_session_id(self, session_id: str) -> List[EventEntry***REMOVED***:
        """Получить все события сессии."""
        ...

    # ——— Wildcard resolution ———
    @staticmethod
    def _resolve_wildcard(pattern: str) -> str:
        """Преобразует wildcard паттерн (task.*) в SQL LIKE."""
        return pattern.replace(".*", ".%").replace("*", "%")

    # ——— Агрегация ———
    def count_by_type(self, since: str) -> Dict[str, int***REMOVED***:
        """Количество событий каждого типа за период."""
        ...

    def get_timeline(self, project: str, limit: int = 50) -> List[EventEntry***REMOVED***:
        """Временная шкала проекта."""
        ...
```

### 3.2 EventQuery

```python
@dataclass
class EventQuery:
    """Запрос к Event Store."""

    event_type: Optional[str***REMOVED*** = None    # точное совпадение или wildcard "task.*" → LIKE 'task.%'
    source: Optional[str***REMOVED*** = None        # "orchestrator", "memory_engine"
    correlation_id: Optional[str***REMOVED*** = None
    session_id: Optional[str***REMOVED*** = None
    project: Optional[str***REMOVED*** = None
    user_id: Optional[str***REMOVED*** = None

    # Временной диапазон
    since: Optional[str***REMOVED*** = None         # ISO timestamp
    until: Optional[str***REMOVED*** = None

    # Поиск по данным
    data_search: Optional[str***REMOVED*** = None   # полнотекстовый поиск в data_json

    # Пагинация
    limit: int = 50
    offset: int = 0
    order: str = "desc"                 # asc / desc
```

### 3.3 SQLite схема

```sql
-- Event Store: расширенная schema для event_log
CREATE TABLE IF NOT EXISTS event_store (
    event_id        TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    source          TEXT DEFAULT '',
    correlation_id  TEXT DEFAULT '',
    session_id      TEXT DEFAULT '',
    project         TEXT DEFAULT '',
    user_id         TEXT DEFAULT '',
    data_json       TEXT DEFAULT '{***REMOVED***',
    metadata_json   TEXT DEFAULT '{***REMOVED***',
    timestamp       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_es_type ON event_store(event_type);
CREATE INDEX IF NOT EXISTS idx_es_correlation ON event_store(correlation_id);
CREATE INDEX IF NOT EXISTS idx_es_session ON event_store(session_id);
CREATE INDEX IF NOT EXISTS idx_es_project ON event_store(project);
CREATE INDEX IF NOT EXISTS idx_es_timestamp ON event_store(timestamp);

-- FTS5 для полнотекстового поиска
-- Используется external content FTS: индекс хранится отдельно,
-- данные берутся из event_store автоматически по rowid.
-- Триггеры ниже поддерживают синхронизацию индекса.
CREATE VIRTUAL TABLE IF NOT EXISTS event_fts USING fts5(
    event_id, event_type, data_json,
    content='event_store',
    content_rowid='rowid'
);

-- Триггеры синхронизации FTS5
-- Без них полнотекстовый поиск вернёт пустой результат.
CREATE TRIGGER IF NOT EXISTS event_fts_ai AFTER INSERT ON event_store BEGIN
    INSERT INTO event_fts(rowid, event_id, event_type, data_json)
    VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
END;

CREATE TRIGGER IF NOT EXISTS event_fts_ad AFTER DELETE ON event_store BEGIN
    INSERT INTO event_fts(event_fts, rowid, event_id, event_type, data_json)
    VALUES ('delete', old.rowid, old.event_id, old.event_type, old.data_json);
END;

CREATE TRIGGER IF NOT EXISTS event_fts_au AFTER UPDATE ON event_store BEGIN
    INSERT INTO event_fts(event_fts, rowid, event_id, event_type, data_json)
    VALUES ('delete', old.rowid, old.event_id, old.event_type, old.data_json);
    INSERT INTO event_fts(rowid, event_id, event_type, data_json)
    VALUES (new.rowid, new.event_id, new.event_type, new.data_json);
END;
```

> **Альтернатива:** Если триггеры нежелательны (например, для batch-вставок),
> синхронизацию можно делать на уровне приложения — после `store()`/`store_batch()`
> вызывать `INSERT INTO event_fts(...) VALUES (...)` явно.

### 3.4 EventEntry

```python
@dataclass
class EventEntry:
    """Запись в Event Store."""

    event_id: str
    event_type: str
    source: str
    correlation_id: str
    session_id: str
    project: str
    user_id: str
    data: Dict[str, Any***REMOVED***
    metadata: Dict[str, Any***REMOVED***
    timestamp: str
```

### 3.5 Примеры использования

```python
# Сохранить событие
store.store(Event(
    type="task.completed",
    source="orchestrator",
    data={"task_id": "wf-001", "status": "success", "duration_ms": 1200***REMOVED***,
    metadata={"correlation_id": "corr-abc", "session_id": "session-123"***REMOVED***,
))

# Найти все события сессии
entries = store.get_by_session_id("session-123")

# Найти все ошибки за последний час
from datetime import datetime, timezone, timedelta
hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
errors = store.query(EventQuery(
    event_type="*.failed",
    since=hour_ago,
    limit=100,
))
```

---

## 4. Event Replay

### 4.1 Концепция

Event Replay позволяет **воспроизвести** последовательность событий
для восстановления состояния системы или повторной обработки.

### 4.2 Сценарии использования

| Сценарий | Описание |
|----------|----------|
| **После сбоя** | Восстановить состояние после OOM или перезагрузки |
| **Отладка** | Повторить шаги для поиска ошибки |
| **Миграция данных** | Перестроить индекс на основе событий |
| **Тестирование** | Симулировать нагрузку реальными событиями |

### 4.3 EventReplay

```python
class EventReplay:
    """Воспроизведение событий из Event Store."""

    def __init__(self, store: EventStore, bus: EventBus):
        self._store = store
        self._bus = bus

    def replay(
        self,
        query: EventQuery,
        target_subscriber: Optional[str***REMOVED*** = None,
        speed: str = "realtime",  # "instant", "realtime", "slow"
    ) -> ReplayResult:
        """Воспроизвести события, соответствующие запросу.

        Args:
            query: запрос к Event Store
            target_subscriber: если указан, доставить только этому подписчику
            speed: скорость воспроизведения

        Returns:
            ReplayResult с статистикой
        """
        ...

    def replay_session(self, session_id: str) -> ReplayResult:
        """Воспроизвести все события сессии."""
        ...

    def replay_workflow(self, correlation_id: str) -> ReplayResult:
        """Воспроизвести все события workflow (task + steps)."""
        ...

    def rebuild(self, target: str) -> RebuildResult:
        """Перестроить состояние компонента из событий.

        Например: перестроить KnowledgeEngine.index из memory.stored событий.
        """
        ...


@dataclass
class ReplayResult:
    """Результат воспроизведения."""
    total_events: int = 0
    delivered: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    errors_list: List[str***REMOVED*** = field(default_factory=list)


@dataclass
class RebuildResult:
    """Результат перестройки состояния."""
    target: str = ""
    events_processed: int = 0
    items_created: int = 0
    duration_ms: float = 0.0
```

### 4.4 Rebuild — механизм перестройки

`rebuild(target)` восстанавливает состояние компонента, проигрывая
релевантные события из Event Store. Алгоритм:

1. **Snapshot-поиск** — проверяет, есть ли сохранённый snapshot компонента
   (например, `data/knowledge_index.v2.snapshot`). Если snapshot есть
   и его timestamp совпадает с последним обработанным событием —
   загружается из snapshot (incremental recovery).
2. **Очистка** — существующий индекс/состояние удаляется (если нет snapshot).
3. **Воспроизведение** — все события target-типа проигрываются через
   оригинальный subscriber (или симуляцию).
4. **Snapshot** — после успешного rebuild создаётся новый snapshot
   для будущего incremental recovery.

**Идемпотентность:** rebuild должен быть идемпотентным — повторный запуск
с теми же событиями даёт тот же результат. Subscriber'ы должны быть
подготовлены к повторной доставке (dedup по event_id).

**Пример:**

```python
# Восстановить KnowledgeEngine после сбоя
replay = EventReplay(store, bus)
result = replay.rebuild("knowledge_engine")
# 1. Ищет snapshot data/knowledge_index.v2.snapshot
# 2. Если нет → очищает FTS5 индекс
# 3. Проигрывает все memory.stored события
# 4. Вызывает KnowledgeEngine.index() для каждого
# 5. Сохраняет snapshot
```

---

## 5. Timeline

### 5.1 Концепция

Timeline — временная шкала изменений проекта, которая показывает
вchronological порядке все события, связанные с проектом.

### 5.2 TimelineEngine

```python
class TimelineEngine:
    """Временная шкала проекта.

    Агрегирует события из Event Store в хронологическом порядке.
    """

    def __init__(self, store: EventStore):
        self._store = store

    def get_timeline(
        self,
        project: str = "",
        limit: int = 50,
        event_types: Optional[List[str***REMOVED******REMOVED*** = None,
    ) -> Timeline:
        """Получить временную шкалу."""
        ...

    def get_timeline_by_session(self, session_id: str) -> Timeline:
        """Шкала для конкретной сессии."""
        ...

    def get_timeline_by_user(self, user_id: str, limit: int = 50) -> Timeline:
        """Шкала действий пользователя."""
        ...

    def search_timeline(
        self,
        query: str,
        project: str = "",
    ) -> Timeline:
        """Поиск по временной шкале."""
        ...


@dataclass
class Timeline:
    """Временная шкала."""
    entries: List[TimelineEntry***REMOVED***
    total: int
    project: str = ""
    since: str = ""
    until: str = ""


@dataclass
class TimelineEntry:
    """Одна запись временной шкалы.

    Отформатирована для показа пользователю.
    """

    timestamp: str                   # "2026-07-29 12:34:56"
    event_type: str                  # "session.created"
    icon: str                        # "▶️" "✅" "❌" "📌"
    title: str                       # "Сессия начата: Code Review"
    description: str                 # "Пользователь начал новую сессию"
    data: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    correlation_id: str = ""
    session_id: str = ""
```

### 5.3 Timeline icons

```python
EVENT_ICONS = {
    "system.startup": "🚀",
    "system.shutdown": "🛑",
    "system.error": "❌",
    "session.created": "▶️",
    "session.completed": "✅",
    "session.checkpoint": "📌",
    "task.created": "📋",
    "task.completed": "✅",
    "task.failed": "❌",
    "step.started": "🔄",
    "step.completed": "✅",
    "step.failed": "❌",
    "memory.stored": "💾",
    "memory.deleted": "🗑",
    "knowledge.indexed": "📚",
    "knowledge.searched": "🔍",
    "mcp.server.initialized": "🔗",
    "mcp.tool.called": "🔧",
    "bridge.connected": "🌉",
    "policy.evaluated": "⚖️",
***REMOVED***
```

### 5.4 Пример ленты

```
🚀 12:00:00 — System startup: Buffy v4.6.0
▶️ 12:01:00 — Session started: Code Review PR #42
📋 12:01:30 — Task created: review pr#42
🔄 12:01:35 — Step started: fetch PR diff
✅ 12:01:40 — Step completed (0.5s)
🔄 12:01:40 — Step started: analyze changes
⚖️ 12:01:41 — Policy evaluated: review-default → claude-code
📌 12:02:00 — Checkpoint: analysis complete
✅ 12:02:10 — Task completed (duration: 40s)
📌 12:02:15 — Checkpoint: PR reviewed
✅ 12:02:20 — Session completed
```

---

## 6. Audit

### 6.1 Концепция

Audit — система аудита, которая фиксирует **все решения**,
принятые Policy Engine, и действия пользователей/агентов.

### 6.2 AuditEngine

```python
class AuditEngine:
    """Система аудита.

    Фиксирует:
    - Какие политики были применены
    - Какие Runtime/Provider/Model были выбраны
    - Кто (пользователь/агент) что сделал
    - Когда были изменения конфигурации
    """

    def __init__(self, store: EventStore):
        self._store = store

    # ——— Запись ———
    def log_decision(self, decision: AuditDecision) -> str:
        """Зафиксировать решение Policy Engine."""
        ...

    def log_action(self, action: AuditAction) -> str:
        """Зафиксировать действие пользователя/агента."""
        ...

    def log_config_change(self, change: AuditConfigChange) -> str:
        """Зафиксировать изменение конфигурации."""
        ...

    # ——— Поиск ———
    def get_audit_trail(
        self,
        target_type: str = "",       # "policy", "runtime", "config"
        target_id: str = "",
        limit: int = 50,
    ) -> List[AuditEntry***REMOVED***:
        """Получить аудит-трейл для объекта."""
        ...

    def search_audit(self, query: str) -> List[AuditEntry***REMOVED***:
        """Поиск по аудит-логу."""
        ...
```

### 6.3 Audit Types

```python
@dataclass
class AuditDecision:
    """Решение Policy Engine."""
    policy_name: str
    capability: str
    runtime_selected: str
    provider_selected: str
    model_selected: str
    fallback_used: bool = False
    cost_estimate: float = 0.0
    context: Dict[str, Any***REMOVED*** = field(default_factory=dict)


@dataclass
class AuditAction:
    """Действие пользователя или агента."""
    actor: str                       # "user", "agent:claude-code"
    action: str                      # "policy.override", "runtime.switch"
    target: str                      # что было изменено
    before: Optional[str***REMOVED*** = None    # предыдущее значение
    after: Optional[str***REMOVED*** = None     # новое значение
    reason: str = ""


@dataclass
class AuditConfigChange:
    """Изменение конфигурации."""
    component: str                   # "policy engine", "event bus"
    setting: str                     # "default_runtime"
    old_value: str = ""
    new_value: str = ""
    changed_by: str = ""
    version: int = 1


@dataclass
class AuditEntry:
    """Запись аудита."""
    id: str
    type: str                        # "decision", "action", "config_change"
    timestamp: str
    data: Dict[str, Any***REMOVED***
```

### 6.4 Пример аудит-лога

```
=== AUDIT: 2026-07-29 ===

[12:01:41***REMOVED*** DECISION: task.review
  Policy: review-default (pack: solo-developer)
  Capability: review → Runtime: claude-code → Model: claude-3.5-sonnet
  Provider: anthropic
  Cost estimate: $0.02
  Fallback: NO

[12:05:00***REMOVED*** ACTION: user.override
  User set preferred_runtime=freebuff for capability testing
  Previous: claude-code → New: freebuff

[12:10:00***REMOVED*** CONFIG: policy_engine.default_runtime
  Old: "claude-code"
  New: "freebuff"
  Changed by: user
```

---

## 6.5 Audit — маппинг на Event Store

AuditEngine использует EventStore, но с фиксированными `event_type`
для разделения типов аудита. Маппинг:

| Тип аудита | event_type | data_json содержит |
|-----------|------------|-------------------|
| **Decision** | `audit.decision` | `AuditDecision` → JSON |
| **Action** | `audit.action` | `AuditAction` → JSON |
| **Config Change** | `audit.config_change` | `AuditConfigChange` → JSON |

**Реализация `log_decision`:**

```python
def log_decision(self, decision: AuditDecision) -> str:
    """Зафиксировать решение как событие audit.decision."""
    event = Event(
        type="audit.decision",
        source="policy_engine",
        data=asdict(decision),
        metadata={
            "correlation_id": decision.context.get("correlation_id", ""),
            "session_id": decision.context.get("session_id", ""),
        ***REMOVED***,
    )
    return self._store.store(event)
```

Поиск аудита через EventStore.query с фильтром `event_type`:

```python
# Найти все решения за сегодня
decisions = store.query(EventQuery(
    event_type="audit.decision",
    since="2026-07-29T00:00:00",
    limit=100,
))
```

---

## 7. Project Pulse

### 7.1 Концепция

Project Pulse — лента событий в реальном времени для пользователя.
Отображает что происходит в проекте: кто, что, когда сделал.

### 7.2 PulseEngine

```python
class PulseEngine:
    """Project Pulse — лента событий пользователя."""

    def __init__(self, bus: EventBus, store: EventStore):
        self._bus = bus
        self._store = store

    def start(self) -> None:
        """Подписаться на события и начать формировать Pulse."""
        self._bus.subscribe("*", self._on_event)

    def _on_event(self, event: Event) -> None:
        """Обработать событие: отформатировать и сохранить в Pulse."""
        ...

    def get_pulse(
        self,
        project: str = "",
        limit: int = 20,
        event_types: Optional[List[str***REMOVED******REMOVED*** = None,
    ) -> List[PulseEntry***REMOVED***:
        """Получить ленту Pulse."""
        ...


@dataclass
class PulseEntry:
    """Запись Pulse — отформатирована для UI."""
    icon: str
    title: str
    description: str
    timestamp: str
    severity: str = "info"  # "info", "warning", "error", "success"
    actionable: bool = False
    action_label: str = ""
    action_data: Dict[str, Any***REMOVED*** = field(default_factory=dict)
```

### 7.3 Пример Pulse

```
📋 12:01 — Task started: review PR #42
🔄 12:01 — Claude Code анализирует изменения...
⚠️ 12:02 — Обнаружена потенциальная уязвимость в auth.py
✅ 12:02 — Claude Code завершил анализ
📌 12:02 — Чекпоинт: review готов (3 замечания)
🔍 12:03 — User запросил детали уязвимости
💾 12:03 — Результат сохранён в Memory (level=project)
```

---

## 8. Интеграция с архитектурой

### 8.1 Связи

```
Event Platform
  │
  ├── Event Bus → publish/subscribe (Core)
  ├── Event Store → SQLite долговременное хранение (Core)
  ├── Event Replay → восстановление состояния (Core)
  ├── Timeline → UI / CLI (Core)
  ├── Audit → Policy Engine (Core)
  ├── Project Pulse → UI / Telegram Bot (Core)
  │
  ├── MCP Server → event инструменты
  │     ├── event_search
  │     ├── event_timeline
  │     ├── event_replay
  │     └── event_audit
  │
  ├── Policy Engine → audit решений
  ├── Orchestrator → task/step события
  ├── ContextManager → session события
  ├── MemoryEngine → memory события
  ├── KnowledgeEngine → knowledge события
  └── Bridge Layer → bridge события
```

### 8.2 MCP регистрация

```python
def _get_event_store(self) -> EventStore:
    if self._event_store is None:
        from scripts.event_store import EventStore
        self._event_store = EventStore()
    return self._event_store

def _register_tools(self):
    self.tool("event_search")(self._handle_event_search)
    self.tool("event_timeline")(self._handle_event_timeline)
    self.tool("event_replay")(self._handle_event_replay)
    self.tool("event_audit")(self._handle_event_audit)
    self.tool("event_pulse")(self._handle_event_pulse)
```

---

## 9. MCP инструменты

```json
{
    "name": "event_search",
    "description": "Поиск событий в Event Store",
    "inputSchema": {
        "event_type": { "type": "string", "optional": true ***REMOVED***,
        "session_id": { "type": "string", "optional": true ***REMOVED***,
        "data_search": { "type": "string", "optional": true ***REMOVED***,
        "limit": { "type": "number", "default": 20 ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "event_timeline",
    "description": "Временная шкала проекта",
    "inputSchema": {
        "project": { "type": "string", "optional": true ***REMOVED***,
        "limit": { "type": "number", "default": 30 ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "event_replay",
    "description": "Воспроизвести события",
    "inputSchema": {
        "session_id": { "type": "string", "optional": true ***REMOVED***,
        "event_type": { "type": "string", "optional": true ***REMOVED***,
        "speed": { "type": "string", "enum": ["instant", "realtime"***REMOVED***, "default": "instant" ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "event_audit",
    "description": "Аудит решений и действий",
    "inputSchema": {
        "target_type": { "type": "string", "enum": ["policy", "runtime", "config"***REMOVED*** ***REMOVED***,
        "limit": { "type": "number", "default": 20 ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "event_pulse",
    "description": "Лента событий проекта",
    "inputSchema": {
        "project": { "type": "string", "optional": true ***REMOVED***,
        "limit": { "type": "number", "default": 10 ***REMOVED***
    ***REMOVED***
***REMOVED***
```

---

## 10. CLI

```bash
# Поиск событий
buffy event search --type task.completed --limit 10
buffy event search --session session-123
buffy event search "уязвимость"

# Временная шкала
buffy event timeline
buffy event timeline --project my-app --limit 20

# Воспроизведение
buffy event replay --session session-123
buffy event replay --type memory.stored --rebuild knowledge_engine

# Аудит
buffy event audit
buffy event audit --target-type policy --limit 10

# Pulse
buffy event pulse
buffy event pulse --project my-app
```

---

## 11. Тестирование

### 11.1 Unit-тесты

| Тест | Что проверяет |
|------|--------------|
| `test_store_crud` | EventStore: store, get_by_id, query |
| `test_store_query` | EventStore: фильтры (type, source, session, project, timerange) |
| `test_store_batch` | EventStore: batch store |
| `test_store_correlation` | EventStore: get_by_correlation_id |
| `test_store_search` | EventStore: полнотекстовый поиск (FTS5) |
| `test_replay_basic` | EventReplay: replay по session_id |
| `test_replay_speed` | EventReplay: instant vs realtime |
| `test_replay_rebuild` | EventReplay: rebuild компонента |
| `test_timeline_basic` | Timeline: get_timeline |
| `test_timeline_format` | Timeline: форматирование entry (icon, title) |
| `test_timeline_search` | Timeline: поиск |
| `test_audit_decision` | Audit: log_decision |
| `test_audit_action` | Audit: log_action |
| `test_audit_trail` | Audit: get_audit_trail |
| `test_pulse_basic` | Pulse: подписка и форматирование |
| `test_integration_store_bus` | EventStore + EventBus: событие → хранение |

### 11.2 Boundary тесты

- EventStore с 10,000 записей (производительность)
- FTS5 поиск по большому data_json
- Replay с 0 событиями
- Replay с таймаутом (зависший subscriber)
- Audit с полем before=None
- Pulse с пустым проектом

---

## 12. Реализация

### 12.1 Файлы

```
freebuff_plugin/event/
├── __init__.py              # EventStore, EventQuery типы
├── store.py                 # EventStore (SQLite + FTS5)
├── replay.py                # EventReplay
├── timeline.py              # TimelineEngine
├── audit.py                 # AuditEngine
├── pulse.py                 # PulseEngine
└── schema.sql               # SQLite schema + индексы
```

### 12.2 Этапы реализации

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **1. Event Store** | EventStore CRUD, SQLite + FTS5, query | 15 | Event Bus |
| **2. Event Replay** | EventReplay: session, correlation_id, rebuild | 10 | Event Store |
| **3. Timeline** | TimelineEngine: get, format, search | 8 | Event Store |
| **4. Audit** | AuditEngine: decision, action, config_change | 8 | Event Store |
| **5. Pulse** | PulseEngine: подписка + форматирование | 6 | Event Bus, Event Store |
| **6. MCP tools** | 5 инструментов (search, timeline, replay, audit, pulse) | 8 | Всё |
| **7. CLI** | buffy event search/timeline/replay/audit/pulse | 5 | Всё |
| **ИТОГО** | | **~60 тестов** | |

### 12.3 Приоритет

| Приоритет | Компонент | Обоснование |
|-----------|-----------|-------------|
| P0 | Event Store | Фундамент для всего |
| P1 | Event Replay | Восстановление после сбоя |
| P1 | Audit | Безопасность (особенно enterprise) |
| P2 | Timeline | UX |
| P2 | Pulse | UX |
| P3 | MCP tools + CLI | После стабилизации Core |

---

## 13. Миграция данных

### 13.1 Из событийного лога

Существующий `event_log` (старая таблица) содержит исторические события.
Миграция в `event_store`:

```python
def migrate_from_event_log(event_store: EventStore) -> int:
    """Перенести данные из event_log в event_store.

    Вызывается однократно при первом старте EventStore.
    """
    old_events = event_log.execute("SELECT * FROM events").fetchall()
    for row in old_events:
        event_store.store(Event(
            id=row["event_id"***REMOVED***,
            type=row["event_type"***REMOVED***,
            source=row.get("source", "legacy"),
            data=json.loads(row.get("data", "{***REMOVED***")),
            timestamp=row["timestamp"***REMOVED***,
            metadata={"correlation_id": row.get("correlation_id", "")***REMOVED***,
        ))
    return len(old_events)
```

**Правила миграции:**
- Миграция **идемпотентна** — повторный запуск не создаёт дубликатов
  (проверка по `event_id`).
- Старый `event_log` **не удаляется** — остаётся как read-only fallback.
- Если `event_store` уже содержит данные — миграция пропускается.
- FTS5 индекс перестраивается после миграции через `INSERT INTO event_fts(...)`.

### 13.2 Из других источников

| Источник | Что мигрировать | Период |
|----------|----------------|--------|
| Stream session логи | checkpoint events | При первой загрузке |
| Memory Engine логи | memory.stored | При первой загрузке |
| ContextManager логи | session.created/completed | При первой загрузке |

---

## 14. Критерии готовности

- [x***REMOVED*** Event Bus — publish/subscribe, wildcard, filters, stats
- [x***REMOVED*** Event Log — SQLite лог всех событий
- [x***REMOVED*** Event Subscribers — memory.stored → knowledge index, checkpoint log

### План

- [ ***REMOVED*** **Event Store** — SQLite v2: event_store таблица + FTS5 + индексы
- [ ***REMOVED*** **Event Store** — CRUD: store, query, get_by_id, get_by_correlation_id
- [ ***REMOVED*** **Event Store** — Batch store для производительности
- [ ***REMOVED*** **Event Replay** — replay по session_id, event_type, rebuild
- [ ***REMOVED*** **Timeline** — get_timeline с форматированием (icon, title)
- [ ***REMOVED*** **Audit** — log_decision, log_action, log_config_change, get_audit_trail
- [ ***REMOVED*** **Pulse** — подписка на все события, форматирование для UI
- [ ***REMOVED*** **MCP tools** — event_search, event_timeline, event_replay, event_audit, event_pulse
- [ ***REMOVED*** **CLI** — buffy event search/timeline/replay/audit/pulse
- [ ***REMOVED*** **60+ тестов**, 0 failures

---

*Связанные документы: [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(POLICY_ENGINE_SPECIFICATION.md), [scripts/event_bus.py***REMOVED***(../scripts/event_bus.py), [scripts/event_subscribers.py***REMOVED***(../scripts/event_subscribers.py)*
