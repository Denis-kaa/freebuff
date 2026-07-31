# ARCHITECTURE MANIFEST — Единый архитектурный закон Buffy Project

> **Версия:** 1.0.0
> **Дата:** 2026-07-31
> **Статус:** 🟢 КАНОНИЧЕСКИЙ — главный архитектурный закон проекта
> **Миссия:** Этап 3 консолидации (`pompts/promt32.md`)
> **Компаньоны:** [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md) (поведение агента), [CODE_QUALITY_STANDARD.md***REMOVED***(CODE_QUALITY_STANDARD.md) (качество кода)
> **Источники синтеза:** [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md)

---

## 1. Миссия платформы

**Buffy — это AI Infrastructure Layer.** Не агент. Не фреймворк. Не IDE.

Buffy — инфраструктурный слой, который работает **под, над и между** любыми AI-инструментами
(Claude Code, Cursor, OpenClaw, Codex, Codebuff и др.), усиливая их, а не заменяя.

```
Local AI Agent → Agent Framework → Agent Platform → Companion Platform → AI Infrastructure Layer
     v1.x            v2.x               v3.x              v4.x                  v5.0+
```

Платформа:
- **Усиливает** существующие AI-агенты (долговременный контекст, документация, знания, синхронизация, коллаборация);
- **Работает автономно** как freebuff агент;
- **Поддерживает любой Runtime** через Runtime Abstraction Layer;
- **Не зависит** от конкретной модели, провайдера или агентного фреймворка;
- **Остаётся актуальной** через 5–10 лет независимо от эволюции LLM.

**Главный принцип: Buffy — инфраструктура, которую подключают к Claude/Cursor/Codebuff, чтобы они стали умнее, памятливее и команднее.**

---

## 2. Главные архитектурные принципы

| # | Принцип | Содержание | Источник |
|---|---------|-----------|----------|
| 1 | **Infrastructure Plugin** | Buffy расширяет существующие Runtime, не заменяя их. Удаление Buffy не ломает Runtime. Buffy не является точкой отказа. | ARCHITECTURE_PRINCIPLES §1–2.1 |
| 2 | **Android First** | Основная платформа — Android + Termux. Невозможное на Android → альтернатива. Linux/macOS/Windows — расширение, не цель. | ARCHITECTURE_PRINCIPLES §2.2 |
| 3 | **Loosely Coupled** | Компоненты общаются через EventBus, не прямыми вызовами. Ядро↔Плагин только через `__init__.py` / `bridge.py`. | ARCHITECTURE_PRINCIPLES §2.3 |
| 4 | **Runtime Agnostic** | Никакой привязки к конкретному Runtime. Все подключаются через Adapter Layer. Новый Runtime не требует изменения ядра. | ARCHITECTURE_PRINCIPLES §2.4 |
| 5 | **Deterministic First** | LLM только там, где нужен интеллект. Всё остальное — детерминированные алгоритмы (FTS5, SQLite, TF-IDF, BFS). | ARCHITECTURE_PRINCIPLES §2.5 |
| 6 | **Event Driven** | Вся система на событиях. Publish/subscribe, никаких прямых вызовов между слоями. | ARCHITECTURE_PRINCIPLES §2.6 |
| 7 | **Marketplace-Ready** | `runtime/providers/` (YAML), `runtime/plugins/` (Python), `runtime/recipes/`. No core change, auto-discovery, capability-first. | ARCHITECTURE_PRINCIPLES §2.7 |
| 8 | **Single Source of Truth** | Никаких вторых вариантов истины. Код ↔ документация ↔ промты согласованы. | promt32 |
| 9 | **Documentation First** | Архитектура изменилась → документация изменилась. Принято решение → ADR. | promt32 |
| 10 | **Project State First** | Состояние всегда на диске, устойчивость к OOM-kill. | BUFFY.md |
| 11 | **Engineering Memory** | Опыт проекта фиксируется (EMEngine, ADR, ретроспективы, инциденты). | promt32 |
| 12 | **Backward Compatibility** | Evolution over Revolution. Миграции автоматические и обратно совместимые. Deprecation за мажорный релиз. | ARCHITECTURE_PRINCIPLES §7 |
| 13 | **Reuse First** | Переиспользовать существующие движки. Extend Second. Create Last. | promt31 |

---

## 3. Основные правила (обязательные)

### 3.1 Границы слоёв

```
┌─────────────────────────────────────────────────────────────┐
│  CORE — минимальное ядро (обязательно для любого режима)      │
│  Project State · Session Platform · Memory Engine ·          │
│  Event Platform · Policy Engine · Knowledge Platform ·       │
│  Graph Index · Workflow Engine · Bootstrap Engine             │
├─────────────────────────────────────────────────────────────┤
│  EXTENSIONS — опциональные сервисы (по профилю)              │
│  MCP Server · Bridge Layer · Runtime Abstraction ·           │
│  Runtime Installer · Scenario Engine · Provider/Key/Model     │
│  Pool · ACP Protocol · OOM Protection · Capability Registry   │
├─────────────────────────────────────────────────────────────┤
│  LABS — экспериментальные (могут измениться)                 │
│  Presence · RAG 2.0 · Live Collaboration · Team Mode ·       │
│  Plugin SDK · Workflow SDK · Policy Packs · Distributed Bus   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Границы ядро ↔ плагин

- Ядро → Плагин: **только** через `freebuff_plugin/__init__.py`, с `try/except` graceful degradation.
- Плагин → Ядро: **только** через `freebuff_plugin/bridge.py`.
- Никаких жёстких путей. Контракт: `freebuff_plugin/INTEGRATION_CONTRACT.md`.

### 3.3 Три режима работы (масштабирование)

```
Single → Cowork → Teamwork → Organization → Community
```

| Уровень | Пользователей | Агентов | Статус |
|---------|--------------|---------|--------|
| Single | 1 | 1–2 | ✅ Готово |
| Cowork | 1 | 2–5 | 🟡 Connectivity готово, orchestration — нет |
| Teamwork | 2–10 | 3–10 | 🟡 ACP/Bridge готовы, остальное — план |
| Organization | 10–100 | 5–20 | 🔵 Концепт |
| Community | 100+ | 20+ | 🔵 Концепт |

Каждый уровень надстраивается над предыдущим без разрушения.

### 3.4 Модель памяти (границы движков)

| Движок | Слой | Ответственность | Хранение |
|--------|------|-----------------|----------|
| `MemoryEngine` | Core | Сессионная/рабочая память (краткосрочная) | SQLite, 6 уровней |
| `KnowledgeEngine` | Core | Индексированные факты и документы (средняя/долгая) | FTS5 + TF-IDF |
| `EMEngine` | Core | Нарративные записи: решения, инциденты, уроки (долгая) | Markdown + frontmatter |
| `RAGEngine` | Ext | Семантический поиск — **целевое состояние:** фича KnowledgeEngine (см. KMS-решение promt31), сейчас отдельный движок | — |
| `GraphIndex` | Core | Связи между сущностями | SQLite + BFS |

> Правило KMS: MemoryEngine = краткосрочная, KnowledgeEngine = канонический индексатор,
> Engineering Memory = человекочитаемые записи. RAG/Vector = фичи KnowledgeEngine.

---

## 4. Карта компонентов (текущее состояние, ~55+)

Полный каталог: [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md). Долги и расхождения: [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md).

### 4.1 Реестр движков (`scripts/`)

| Движок | Файл | Статус |
|--------|------|--------|
| `MemoryEngine` | `scripts/memory_engine.py` | ✅ Production |
| `KnowledgeEngine` | `scripts/knowledge_engine.py` | ✅ Production |
| `GraphIndex` | `scripts/graph_index.py` | ✅ Production |
| `EMEngine` | `scripts/engineering_memory.py` | ✅ Production |
| `RAGEngine` | `scripts/rag_engine.py` | ✅ Production (целевое состояние: фича KnowledgeEngine, см. §3.4) |
| `CollaborationEngine` | `scripts/collaboration.py` | ✅ Production |
| `PresenceEngine` | `scripts/presence.py` | ✅ Production |
| `RoleEngine` | `scripts/roles.py` | ✅ Production |
| `MetricsEngine` | `scripts/metrics.py` | ✅ Production |

Сервисы состояния проекта (не `*Engine`-классы): `ProjectPulse` (`scripts/project_pulse.py`), `drift_check.py`.

### 4.2 Инфраструктурные слои

| Компонент | Файл/Путь | Статус |
|-----------|-----------|--------|
| EventBus | `scripts/event_bus.py` | ✅ Production |
| Orchestrator | `scripts/orchestrator.py` | 🟡 MVP (DAG, parallel) |
| ContextManager | `scripts/context_manager.py` | ✅ Production |
| ToolRuntime | `scripts/tool_runtime.py` | ✅ Production |
| PluginAPI | `scripts/plugin_api.py` | ✅ Production |
| MCP Server | `scripts/mcp_server.py` | ✅ Production |
| Bridge Layer | `freebuff_plugin/bridge_layer.py` | ✅ Production |
| Runtime Abstraction | `freebuff_plugin/runtime/` | ✅ Production |
| Scenario Engine | `freebuff_plugin/scenario_engine.py` | ✅ Production |
| Notification | `scripts/notification.py` | ✅ Production |
| Drift Check | `scripts/drift_check.py` | ✅ Production |

---

## 5. Жизненный цикл компонента

Ни один компонент не существует без описанного жизненного цикла:

```
Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление
```

Правила:
1. **Создание:** новый модуль = одна задача (Single Responsibility) + тесты + регистрация в `SYSTEM_INVENTORY.md`.
2. **Инициализация:** lazy init (`__getattr__`, accessor'ы), graceful degradation при недоступности зависимостей.
3. **Работа:** EventBus для всех значимых операций, идемпотентность, состояние на диске.
4. **Обновление:** обратно совместимые миграции, deprecation за мажорный релиз.
5. **Завершение:** корректный shutdown, освобождение ресурсов, финальный чекпоинт.
6. **Архивация:** устаревшее → `scripts/archive/` или `docs/task_archive/`, история сохраняется.
7. **Удаление:** только после архивации и актуализации всех ссылок.

---

## 6. Правила решений и эволюции

- **ADR обязательны** для архитектурных решений: `docs/engineering-memory/decisions/ADR_NNN_*.md`, индекс — `docs/decisions/DECISIONS.md`.
- **Evolution over Revolution** — никаких rewrite ради красоты.
- **IDEAS.md хранится вечно** — идеи не удаляются, меняется только статус.
- **Runtime-поддержка** заявляется только после практической валидации (Level 3+, [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md)).
- **Лицензии** — интеграция только через публичные API: CLI, MCP, ACP, официальные механизмы.
- **Code review обязателен** для каждого изменения кода.

---

## 7. Анти-паттерны (запрещено)

| ❌ Запрещено | Вместо этого |
|-------------|--------------|
| Новый storage engine | Переиспользовать KnowledgeEngine / MemoryEngine |
| Второй Project Book | Расширять `PROJECT_BOOK.md` |
| Дублирование Decision Log | `DECISIONS.md` индекс + ADR в EM |
| Новые интеграции до реестра | Сначала `INTEGRATION_REGISTRY.md`, потом интеграция |
| Автодокументирование каждого события | Threshold-подход (шум = баг) |
| Прямые вызовы между слоями | EventBus publish/subscribe |
| Хардкод путей/секретов | env/config, `.env` / `.keys/` |
| Новая фича во время консолидации | Mission lock (`promt32.md`) |

---

## 8. Критерий согласованности

Система самосогласована, когда:
- [ ***REMOVED*** код, документация и промты не противоречат друг другу;
- [ ***REMOVED*** новый модуль зарегистрирован в `SYSTEM_INVENTORY.md`;
- [ ***REMOVED*** удалённый компонент не оставил ссылок;
- [ ***REMOVED*** `drift_check.py` не находит расхождений;
- [ ***REMOVED*** архитектурные решения зафиксированы в ADR.

---

## 9. Статус документа

Этот документ — **канонический архитектурный закон**. При конфликте с другими документами
приоритет имеет: **Manifest > ARCHITECTURE_PRINCIPLES > конкретные спецификации**.
Изменения в этот документ требуют ADR.

---

_Связанные документы: [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md), [CODE_QUALITY_STANDARD.md***REMOVED***(CODE_QUALITY_STANDARD.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
