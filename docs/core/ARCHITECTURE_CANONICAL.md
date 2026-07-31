# ARCHITECTURE CANONICAL — Каноническая архитектура Workspace OS

> **Версия:** 1.0.0
> **Дата:** 2026-07-31
> **Статус:** 🟢 КАНОНИЧЕСКИЙ — фиксирует единую структуру Workspace OS и границы движков
> **Миссия:** Этап 2 консолидации (`pompts/promt32.md`)
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md)
> **Связанные:** [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md) (каталог), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md) (долги)

---

## 1. Цель документа

Зафиксировать **единственную каноническую структуру** Workspace OS:

- для каждого компонента: назначение, ответственность, зависимости, жизненный цикл, место в архитектуре, владелец;
- устранить неоднозначности между движками;
- зафиксировать факты (включая расхождения с CHANGELOG — они становятся архитектурным долгом).

Факты в этом документе проверены по кодовой базе (2026-07-31).

---

## 2. Каноническая структура Workspace OS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKSPACE OS (Buffy)                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  CORE (ядро — обязательно)                                           │  │
│  │  ContextManager · MemoryEngine · KnowledgeEngine · GraphIndex ·      │  │
│  │  EventBus · Orchestrator · EMEngine · Bootstrap Engine · Policy       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXTENSIONS (опционально, по профилю)                                │  │
│  │  MCP Server · Bridge Layer · Runtime Abstraction · Scenario Engine ·  │  │
│  │  ToolRuntime · Plugin API · Notification · Provider/Key Pools         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  STATE & KNOWLEDGE SERVICES                                          │  │
│  │  RAGEngine · CollaborationEngine · PresenceEngine · RoleEngine ·     │  │
│  │  MetricsEngine · ProjectPulse · DriftCheck                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  LABS (экспериментальные)                                            │  │
│  │  Session Mesh · Node Mesh · Agent Mesh · Distributed Agents           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Реестр движков — канонические границы

> Легенда статусов: ✅ тесты есть · 🔴 тестов нет (долг)

### 3.1 Core — ядро

> Примечание: C5 (EventBus) и C6 (Orchestrator) — инфраструктурные компоненты ядра, не `*Engine`-классы; включены для полноты карты (в [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md) §4.1 они вынесены в инфраструктурные слои).

| # | Движок | Файл | Назначение | Ответственность | Хранилище | Тесты |
|---|--------|------|-----------|-----------------|-----------|-------|
| C1 | `MemoryEngine` | `scripts/memory_engine.py` | Сессионная/рабочая память | 6 уровней памяти (short→long), VectorBackend, авто-индексация через EventBus | `data/memory*` | ✅ 34 |
| C2 | `KnowledgeEngine` | `scripts/knowledge_engine.py` | Канонический индексатор фактов и документов | FTS5 + TF-IDF + SemanticIndex, поиск, индексация | `context/knowledge/index.db` | ✅ 43 |
| C3 | `GraphIndex` | `scripts/graph_index.py` | Связи между сущностями | BFS, subgraph, графовые запросы | SQLite | 🟡 (опосредованно, через KnowledgeEngine) |
| C4 | `EMEngine` | `scripts/engineering_memory.py` | Нарративная память проекта | ADR, инциденты, ретроспективы, уроки, индекс решений | `docs/engineering-memory/` | ✅ 28 |
| C5 | `EventBus` | `scripts/event_bus.py` | Шина событий | publish/subscribe, wildcard, SQLite-лог | `context/events.db` | ✅ |
| C6 | `Orchestrator` | `scripts/orchestrator.py` | Планирование и исполнение | FSM/DAG, параллельное выполнение, lifecycle-события | — | ✅ |

### 3.2 State & Knowledge Services

| # | Движок | Файл | Назначение | Ответственность | Хранилище | Тесты |
|---|--------|------|-----------|-----------------|-----------|-------|
| S1 | `RAGEngine` | `scripts/rag_engine.py` | Семантический поиск с ранжированием | 5 режимов (keyword/semantic/hybrid/RRF), re-ranking | поверх `KnowledgeEngine` | 🔴 0 (файл отсутствует) |
| S2 | `CollaborationEngine` | `scripts/collaboration.py` | Коллаборативные сессии | сессии, участники, роли owner/editor/viewer, история | `data/collaboration.db` | 🔴 0 (файл отсутствует) |
| S3 | `PresenceEngine` | `scripts/presence.py` | Присутствие агентов | статусы online/offline/busy, heartbeat, prune | `data/presence.db` | 🔴 0 (файл отсутствует) |
| S4 | `RoleEngine` | `scripts/roles.py` | Роли и capabilities | 6 стандартных ролей, маппинг capabilities | `data/roles.db` | 🔴 0 (файл отсутствует) |
| S5 | `MetricsEngine` | `scripts/metrics.py` | Метрики качества разработки | VCR/SRG/CpVO/RRR/TTD, Health Score | `data/metrics.db` | 🔴 0 (файл отсутствует) |
| S6 | `ProjectPulse` | `scripts/project_pulse.py` | Лента изменений проекта | git-коммиты, файлы, события EventBus | SQLite | 🔴 0 (файл отсутствует) |
| S7 | `DriftCheck` | `scripts/drift_check.py` | Самодиагностика | дрейф документации, битые ссылки, ADR-расположение | `docs/DRIFT_REPORT.md` | ✅ |

> **Важно (факт 2026-07-31):** CHANGELOG декларирует 60+ тестов для S1–S6, но файлы `tests/test_rag_engine.py`, `tests/test_collaboration.py`, `tests/test_presence.py`, `tests/test_roles.py`, `tests/test_metrics.py`, `tests/test_project_pulse.py` **отсутствуют** в `tests/` и в git-истории. Это зафиксировано в [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md) как критический долг (код без тестов).

---

## 4. Канонические зависимости движков (проверено по импортам)

```
MemoryEngine ──► EventBus
KnowledgeEngine ──► EventBus, GraphIndex, MemoryEngine
EMEngine ──► EventBus, MemoryEngine, KnowledgeEngine
RAGEngine ──► KnowledgeEngine
CollaborationEngine ──► EventBus, PresenceEngine
PresenceEngine ──► EventBus
RoleEngine ──► PresenceEngine, CollaborationEngine
MetricsEngine ──► EventBus (context.db, verifier.db)
ProjectPulse ──► EventBus
```

**Правила границ:**
1. **Слой данных:** MemoryEngine и KnowledgeEngine — единственные владельцы персистентного хранения знаний. Остальные движки работают поверх них или со своими узкими БД (`data/*.db`).
2. **EventBus first:** движки общаются через события (Collaboration — 16 обращений, Presence — 11, Metrics — 7). `RoleEngine` — исключение (0 обращений, связан через DI конструктора).
3. **Нисходящие зависимости:** движки могут зависеть от Core, но не наоборот.
4. **RAG — фича KnowledgeEngine:** RAGEngine не имеет собственного хранилища — только переиспользует KnowledgeEngine (см. KMS-решение promt31).
5. **Роли и присутствие:** RoleEngine и PresenceEngine взаимосвязаны через DI (`presence_engine=` в конструкторе), но не через EventBus — допускается, задокументировано.

---

## 5. Жизненный цикл движка (канонический)

```
Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление
```

Требования к каждому движку:
1. **Создание:** одна задача (SRP), тесты, регистрация в `SYSTEM_INVENTORY.md`.
2. **Инициализация:** lazy accessor'ы (`_get_*()`), graceful degradation (`try/except ImportError`), параметризация путей (`db_path`, `workspace_root`).
3. **Работа:** EventBus-события для значимых операций, идемпотентность, состояние на диске.
4. **Обновление:** обратно совместимые миграции SQLite (`PRAGMA user_version`).
5. **Завершение:** корректный shutdown (PresenceEngine помечает агентов OFFLINE).
6. **Архивация:** устаревшее → `scripts/archive/`, история сохраняется.
7. **Удаление:** только после архивации и актуализации ссылок.

---

## 6. Владельцы компонентов

| Движок | Владелец | Уровень поддержки |
|--------|----------|-------------------|
| Core (C1–C6) | Buffy (я) | ✅ Production, полные тесты |
| RAGEngine | Buffy (я) | 🟡 Код есть, тестов нет |
| Collaboration/Presence/Roles | Buffy (я) | 🟡 Код есть, тестов нет |
| MetricsEngine | Buffy (я) | 🟡 Код восстановлен из байткода, тестов нет |
| ProjectPulse | Buffy (я) | 🟡 Код есть, тестов нет |
| DriftCheck | Buffy (я) | ✅ Production |

---

## 7. Неоднозначности, требующие решения

| # | Неоднозначность | Каноническое решение (пока) |
|---|----------------|------------------------------|
| 1 | RAGEngine отдельный vs фича KnowledgeEngine | **Фича KnowledgeEngine** (целевое состояние). Отдельный файл сохраняется, но без собственного хранилища. |
| 2 | MetricsEngine vs ProjectPulse vs DriftCheck | Metrics = метрики качества; Pulse = лента событий; DriftCheck = самодиагностика. Разные домены, не дублируют друг друга. |
| 3 | RoleEngine без EventBus | Оставить DI через конструктор; при необходимости перевести на события в v6. |
| 4 | Отсутствие тестов у 6 движков | **Критический долг** — восстановить тест-файлы (см. ARCHITECTURAL_DEBT). |

---

## 8. Критерий согласованности (Этап 2)

- [x***REMOVED*** Каноническая структура зафиксирована (раздел 2)
- [x***REMOVED*** Границы движков определены: Core C1–C6 + State & Knowledge S1–S7 (раздел 3)
- [x***REMOVED*** Зависимости проверены по коду (раздел 4)
- [x***REMOVED*** Жизненный цикл и владельцы определены (разделы 5–6)
- [x***REMOVED*** Неоднозначности зафиксированы (раздел 7)
- [ ***REMOVED*** Тесты восстановлены для S1–S6 (передано в ARCHITECTURAL_DEBT)

---

*Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)*
