# LIFECYCLE — Канонический реестр жизненных циклов компонентов Workspace OS

> **Версия:** 1.0.0
> **Дата:** 2026-07-31
> **Статус:** 🟢 КАНОНИЧЕСКИЙ — единый источник истины о жизненном цикле компонентов
> **Миссия:** Этап 8 консолидации (`pompts/promt32.md`)
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md) §5
> **Связанные:** [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [GLOSSARY.md***REMOVED***(GLOSSARY.md) (терминология)

---

## 1. Назначение и правила

**Зачем:** ни один компонент не существует без описанного жизненного цикла.
Этот документ фиксирует для каждого ключевого компонента, **как реализованы** 7 канонических стадий:

```
Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление
```

**Легенда статусов стадии:**
- ✅ реализовано в коде и проверено;
- 🟡 реализовано частично / имеет ограничения;
- 🔴 не реализовано (долг).

**Правила:**
1. Новый компонент обязан иметь описанные стадии до регистрации в `SYSTEM_INVENTORY.md`.
2. Стадия «Завершение» обязательна для компонентов с потоками/ресурсами (graceful shutdown).
3. Стадия «Обновление» обязательна для SQLite-хранилищ (миграции `PRAGMA user_version`).
4. «Архивация» — вместо удаления: история сохраняется (запрет на удаление истории).
5. Расхождение документа с кодом = долг в `ARCHITECTURAL_DEBT.md`.

---

## 2. Канонический контракт стадий

| Стадия | Требования (из ARCHITECTURE_MANIFEST §5) | Обязательный хук в коде |
|--------|-------------------------------------------|--------------------------|
| **Создание** | Одна задача (SRP), тесты, регистрация в реестре | `__init__()` + `_init_db()` |
| **Инициализация** | Lazy accessor'ы, graceful degradation, параметризация путей (`db_path`, `workspace_root`) | `_get_*()`, `db_path=` аргументы |
| **Работа** | EventBus для значимых операций, идемпотентность, состояние на диске | `publish()` / `subscribe()` |
| **Обновление** | Обратно совместимые миграции SQLite | `PRAGMA user_version`, `_migrate_*()` |
| **Завершение** | Корректный shutdown, освобождение ресурсов, финальный чекпоинт | `stop()`, `close()`, `unload()` |
| **Архивация** | Устаревшее → `scripts/archive/` / `docs/task_archive/`, история сохраняется | перенос, не удаление |
| **Удаление** | Только после архивации и актуализации всех ссылок | — |

---

## 3. Реестр: Core C1–C6 (ядро)

### C1 `MemoryEngine` — `scripts/memory_engine.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | Класс + `__init__(db_path=..., event_bus=...)`, 6 уровней памяти (short→long + vector) |
| Инициализация | ✅ | `_init_db()`, параметризуемый путь, graceful degradation без EventBus |
| Работа | ✅ | `store()`/`retrieve()`/`delete()`/`list()`, авто-индексация через EventBus (`memory.stored`) |
| Обновление | 🟡 | Миграции схемы — обратно совместимые изменения в рамках уровня; полный контракт — в будущем `PRAGMA user_version` |
| Завершение | 🟡 | Нет явного `stop()`; состояние на диске сохраняется на каждой записи (устойчивость к OOM-kill) |
| Архивация | 🟡 | `wipe_level()` — очистка уровня, файлы архивируются не автоматически |
| Удаление | ✅ | `wipe_level()` / удаление файлов уровня |

### C2 `KnowledgeEngine` — `scripts/knowledge_engine.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(workspace_root=...)` — канонический индексатор (FTS5 + TF-IDF + SemanticIndex) |
| Инициализация | ✅ | `_init_db()`, `workspace_root` параметризация, lazy index init |
| Работа | ✅ | `index()`/`search()` (keyword/semantic/hybrid), `rebuild()`, `stats()`; EventBus-события |
| Обновление | 🟡 | Переиндексация (`rebuild`) вместо миграций; схема FTS5 стабильна |
| Завершение | ✅ | `clear()` — полный сброс индекса; состояние на диске |
| Архивация | 🟡 | Экспорт индекса; автоматической архивации нет |
| Удаление | ✅ | `clear()` + удаление index.db |

### C3 `GraphIndex` — `scripts/graph_index.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(db_path=...)`, SQLite-хранилище связей |
| Инициализация | ✅ | `_init_db()`, параметризуемый путь |
| Работа | ✅ | BFS, subgraph, графовые запросы |
| Обновление | 🟡 | Схема стабильна; миграции не требуются |
| Завершение | ✅ | `clear()` — сброс графа |
| Архивация | 🟡 | Не автоматизирована |
| Удаление | ✅ | `clear()` + удаление БД |

### C4 `EMEngine` — `scripts/engineering_memory.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `create_draft_from_template()` — ADR/инциденты/ретроспективы/уроки |
| Инициализация | ✅ | `workspace_root`, чтение шаблонов из `docs/engineering-memory/templates/` |
| Работа | ✅ | `finalize_draft()`, `query_experience()` (только EM-документы), авто-обновление индекса DECISIONS |
| Обновление | ✅ | Авто-регенерация индекса при записи нового решения |
| Завершение | ✅ | `finalize_draft()` — финализация + frontmatter |
| Архивация | ✅ | Документы в `docs/engineering-memory/`; история сохраняется |
| Удаление | 🟡 | Только вручную, с актуализацией ссылок |

### C5 `EventBus` — `scripts/event_bus.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(db_path=...)`, SQLite-лог событий |
| Инициализация | ✅ | `_init_db()`, lazy |
| Работа | ✅ | `publish()`/`subscribe(pattern, handler)`/`unsubscribe()`, wildcard `*`, `get_events()` |
| Обновление | ✅ | Схема стабильна; лог в `context/events.db` |
| Завершение | 🟡 | Нет явного `stop()`; лог на диске (устойчивость к OOM-kill) |
| Архивация | 🟡 | `clear()` — очистка лога; авто-архивация не настроена |
| Удаление | ✅ | `clear()` + удаление БД |

### C6 `Orchestrator` — `scripts/orchestrator.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__`, FSM/DAG-планировщик |
| Инициализация | ✅ | Lazy, `save_workflow()` для персистентности воркфлоу |
| Работа | ✅ | DAG-выполнение, параллельные шаги, lifecycle-события (task.*, step.*) |
| Обновление | 🟡 | MVP-статус; миграции схемы воркфлоу не формализованы |
| Завершение | 🟡 | Остановка воркфлоу; явного `stop()` нет |
| Архивация | 🟡 | История задач в логах EventBus |
| Удаление | 🟡 | Удаление воркфлоу вручную |

---

## 4. Реестр: State & Knowledge Services S1–S7

### S1 `RAGEngine` — `scripts/rag_engine.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(knowledge_engine=..., workspace_root=...)` — поверх KnowledgeEngine (KMS-правило) |
| Инициализация | ✅ | Lazy: создаёт KnowledgeEngine при необходимости; graceful degradation при недоступности |
| Работа | ✅ | `search()` (5 режимов), `hybrid_search()`, `rerank()`, `expand_query()`, `rrf_merge()` |
| Обновление | 🟡 | Не имеет собственного хранилища — обновляется вместе с KnowledgeEngine |
| Завершение | ✅ | Не держит ресурсов (stateless поверх KE) |
| Архивация | 🟡 | — |
| Удаление | ✅ | Не имеет собственного состояния |

### S2 `CollaborationEngine` — `scripts/collaboration.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `create_session()` — сессия, участники, роли owner/editor/viewer |
| Инициализация | ✅ | `_init_db()` (`collab_sessions`/`participants`/`messages`), `db_path` параметризация |
| Работа | ✅ | `send_message()`, `get_history()`, join/leave, `update_participant_role()`, `sync_presence()`; события `collab.*` |
| Обновление | ✅ | `update_participant_role()`, статусы сессий; миграции схемы — при необходимости `PRAGMA user_version` |
| Завершение | ✅ | `close_session()` — статус CLOSED + `collab.closed`; `leave_session()` — участник is_present=0 |
| Архивация | 🟡 | `ARCHIVED` статус предусмотрен, но не используется автоматически |
| Удаление | 🟡 | Удаление сессий вручную |

### S3 `PresenceEngine` — `scripts/presence.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `register()` — регистрация агента + `presence.online` |
| Инициализация | ✅ | `_init_db()` (`presence`/`presence_history`), heartbeat-интервал/`prune_timeout` параметризуемы |
| Работа | ✅ | `update_status()`, `heartbeat()`, `list_agents()`, история; события `presence.*` |
| Обновление | ✅ | `update_status()` с metadata; статусы online/offline/busy/away/error |
| Завершение | ✅ | `stop()` — помечает всех ONLINE агентов OFFLINE + публикует `presence.offline` (эталон graceful shutdown) |
| Архивация | ✅ | История в `presence_history` (аудит изменений) |
| Удаление | ✅ | `unregister()` + `presence.offline` |

### S4 `RoleEngine` — `scripts/roles.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | 6 стандартных ролей + `add_role()` для кастомных |
| Инициализация | ✅ | `_init_db()` (`role_assignments`), `db_path`, DI (`presence_engine=`, `collaboration_engine=`) |
| Работа | ✅ | `assign_role()`/`unassign_role()`, `get_roles()`, capabilities-маппинг, `get_collab_role()` |
| Обновление | ✅ | `update` через пере-назначение; `sync_to_presence()`/`sync_to_collab_session()` |
| Завершение | ✅ | `unassign_all()` — отзыв всех ролей агента |
| Архивация | 🟡 | История назначений не хранится (assign/delete) |
| Удаление | ✅ | `unassign_role()` + `unassign_all()` |

### S5 `MetricsEngine` — `scripts/metrics.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(context_db, verifier_db, metrics_db)` — 3 БД-источника |
| Инициализация | ✅ | `setup_databases()` — диагностика источников; `_init_metrics_db()` |
| Работа | ✅ | `compute_vcr/srg/cpvo/rrr/ttd()`, `compute_report()`, `get_trend()`; событие `metrics.report` |
| Обновление | ✅ | `save_snapshot()` — снимки для трендов |
| Завершение | ✅ | Stateless поверх БД; graceful degradation при отсутствии источников |
| Архивация | ✅ | Снимки в `metrics.db` (история трендов) |
| Удаление | 🟡 | Очистка снимков вручную |

### S6 `ProjectPulse` — `scripts/project_pulse.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | `__init__(db_path, workspace, event_bus)` + `_init_db()` |
| Инициализация | ✅ | Параметризация путей, WAL |
| Работа | ✅ | `scan_git()`, `scan_files()`, `subscribe_eventbus()`, `add_entry()`, `full_scan()`; лента событий |
| Обновление | ✅ | Реф-дедупликация (`_exists_by_ref`); снимок файлов `.pulse_snapshot.json` |
| Завершение | ✅ | `unsubscribe_eventbus()` — отписка от шины |
| Архивация | ✅ | История записей в SQLite; `clear()` для полного сброса |
| Удаление | ✅ | `clear()` + удаление БД |

### S7 `DriftCheck` — `scripts/drift_check.py`

| Стадия | Статус | Как реализовано |
|--------|--------|-----------------|
| Создание | ✅ | CLI-инструмент самодиагностики |
| Инициализация | ✅ | `--force --report` — генерация отчёта `docs/DRIFT_REPORT.md` |
| Работа | ✅ | Проверки: дрейф документации, битые ссылки, ADR-расположение, структура каталогов |
| Обновление | ✅ | Регулярный перепрогон (cron/CI) |
| Завершение | ✅ | CLI, exit-коды |
| Архивация | ✅ | Отчёты в `docs/DRIFT_REPORT.md` (история прогонов) |
| Удаление | 🟡 | Не применимо |

---

## 5. Реестр: Инфраструктурные слои (Extensions)

| Компонент | Создание | Инициализация | Работа | Завершение | Ключевые хуки |
|-----------|----------|---------------|--------|------------|----------------|
| **ContextManager** | ✅ `__init__` | ✅ `_init_db()`, `SCHEMA_VERSION = 5` | ✅ сессии/сообщения/чекпоинты, CONTEXT_FULL (28K) | ✅ `prune_abandoned()`, `auto_abandon_stale()` GC | Миграции `PRAGMA user_version` v1→v5 |
| **ToolRuntime** | ✅ `BaseTool` | ✅ `validate_params()` (pre-execution) | ✅ `execute()` | ✅ валидация результатов | Контракт ToolResult |
| **PluginAPI** | ✅ `BasePlugin` | ✅ `on_load()` | ✅ `enable()`/`disable()` | ✅ `unload()` | Lifecycle-события плагина |
| **MCP Server** | ✅ `_get_*()` accessor'ы | ✅ `_get_tool_registry()`, lazy init | ✅ 51 инструмент (на 2026-07-31), STDIO+HTTP | ✅ тесты (101) | Реестр инструментов |
| **Bridge Layer** | ✅ | ✅ Lazy accessor | ✅ MCP↔ACP трансляция | ✅ | — |
| **Runtime Abstraction** | ✅ StdioMCPAdapter/HTTPMCPAdapter | ✅ RuntimeRegistry | ✅ generate/connect/disconnect/select | ✅ `runtime_disconnect` | Capability Registry |
| **Scenario Engine** | ✅ | ✅ 11+ сценариев | ✅ исполнение сценариев | ✅ | — |
| **Notification** | ✅ `notify()` | ✅ 4-канальный cascade (notification → toast → log → visual fallback, retry 1s/2s/4s) | ✅ notify/notify_task_complete/notify_error | ✅ FREEBUFF_NO_NOTIFY bypass | Возврат True при хоть одном канале |

---

## 6. Эталонные lifecycle-паттерны

**1. Graceful shutdown (эталон — PresenceEngine):**
```python
def stop(self):
    with self._lock:
        self._running = False
    for agent in self._load_all_agents():
        if agent.status == PresenceStatus.ONLINE:
            self.update_status(agent.agent_name, PresenceStatus.OFFLINE)  # + presence.offline
```

**2. Миграции SQLite (эталон — ContextManager):**
```python
# SCHEMA_VERSION = 5; sequential _migrate_v1_to_v2() ... to v5 via PRAGMA user_version
```

**3. Lazy init (эталон — MCP Server):**
```python
def _get_tool_registry(self):  # создаётся при первом обращении
```

**4. Graceful degradation (эталон — RAGEngine / MetricsEngine):**
```python
except Exception:
    return MetricResult(name=..., value=0.0, interpretation=f"Error: {e***REMOVED***")  # не падать
```

---

## 7. Критерий согласованности (Этап 8)

- [x***REMOVED*** Для каждого ключевого компонента Core C1–C6 описаны 7 стадий
- [x***REMOVED*** Для каждого State & Knowledge S1–S7 описаны 7 стадий
- [x***REMOVED*** Инфраструктурные слои (ContextManager, ToolRuntime, PluginAPI, MCP, Bridge, Runtime, Scenario, Notification) покрыты
- [x***REMOVED*** Эталонные паттерны (shutdown, миграции, lazy, degradation) зафиксированы
- [ ***REMOVED*** Компонент без описанного Lifecycle → запрещён к регистрации в SYSTEM_INVENTORY (правило)

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md) §5, [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) §5, [GLOSSARY.md***REMOVED***(GLOSSARY.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
