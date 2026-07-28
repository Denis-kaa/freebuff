# ROADMAP — Buffy Project

> **Версия:** 2.0.0
> **Актуально:** 2026-07-28
> **Основание:** [promt3.md***REMOVED***(../pompts/promt3.md) — конституция Buffy 2.0

---

## ✅ Phase 1: Project State + Context Builder + Streaming + Task System

**Статус:** ✅ ЗАВЕРШЕНА
**Фокус:** Фундамент — контекст, задачи, память

### ✅ Что сделано
- [x***REMOVED*** **ContextManager** — SQLite WAL, сессии, сообщения, чекпоинты
- [x***REMOVED*** **StreamSession** — непрерывная запись (files + SQLite), BackgroundWriter
- [x***REMOVED*** **StreamBridge** — мост Buffy ↔ stream_session
- [x***REMOVED*** **Auto-Conspect** — автосуммаризация при завершении
- [x***REMOVED*** **Context FULL** — триггер при 28K токенов + auto-rollup
- [x***REMOVED*** **Bootstrap** — восстановление сессии при старте
- [x***REMOVED*** **Task System** — TASK.md, CHANGELOG.md, TASK_TEMPLATE.md
- [x***REMOVED*** **GC** — очистка ABANDONED, стрим-директорий
- [x***REMOVED*** **Cron** — автосуммаризация каждые 30 минут
- [x***REMOVED*** **Capability Router** — core/router.py, data-driven scoring
- [x***REMOVED*** **Memory Engine** — 5 уровней памяти (Working/Project/Knowledge/Personal/Archive)
- [x***REMOVED*** **Context Builder** — scripts/context_builder.py
- [x***REMOVED*** **Unified Context** — freebuff_cli.py buffy команда
- [x***REMOVED*** **195 тестов** — 0 errors
- [x***REMOVED*** **Документация** — BUFFY.md, BUFFY_PROJECT.md, RULES.md, DECISIONS.md, SYSTEM_INVENTORY.md

---

## 🟡 Phase 2: Knowledge Engine + Memory Layers + RAG

**Статус:** 🟡 Memory Engine готов, Knowledge Engine — план
**Фокус:** Поиск знаний, долговременная память

### ✅ Есть
- [x***REMOVED*** Memory Engine (5 уровней, JSON-файлы, CRUD, search)
- [x***REMOVED*** MemoryEngine.build_context() — сбор контекста для промпта
- [x***REMOVED*** **Knowledge Engine** — scripts/knowledge_engine.py
  - SQLite FTS5 (keyword search с BM25 ранжированием)
  - TF-IDF vector index (семантический поиск через numpy)
  - Hybrid search (взвешенная комбинация FTS5 + TF-IDF)
  - Индексация из Memory Engine
  - Поиск capabilities по запросу
  - CLI для ручного поиска и индексации
- [x***REMOVED*** **42 теста** Knowledge Engine — 0 errors

### ✅ Сделано
- [x***REMOVED*** **Graph Search** — scripts/graph_index.py
  - SQLite граф с узлами и рёбрами
  - Типы связей: references, parent, child, depends, related, tagged, contains
  - BFS shortest path, subgraph, traverse, auto_discover
  - Интеграция в KnowledgeEngine (graph_search, add_graph_edge, graph_auto_discover)
- [x***REMOVED*** **42 теста** GraphIndex — 0 errors
- [x***REMOVED*** **Semantic Search** — LSA через torch SVD в SemanticIndex
  - Truncated SVD на TF-IDF матрице → плотные семантические эмбеддинги
  - torch.linalg.svd (fallback на numpy)
  - fit_semantic() / semantic_ml режим в search()
  - Авто-fit после rebuild_index()
  - CLI --mode semantic_ml
- [x***REMOVED*** **15 тестов** SemanticIndex — 0 errors

### ✅ Следующее (закрыто)
- [x***REMOVED*** Авто-индексация документов при сохранении в Memory Engine
- [x***REMOVED*** Наполнение Knowledge Memory (best practices, документация)

---

## 🟡 Phase 3: Capability Router + Orchestrator + Tool Runtime

**Статус:** 🟡 В РАБОТЕ (Router + Orchestrator готовы)
**Фокус:** Умный роутинг, планировщик, инструменты

### ✅ Есть
- [x***REMOVED*** Capability-based SmartRouter (core/router.py)
- [x***REMOVED*** ModelCatalog с 6 моделями + capability profiles
- [x***REMOVED*** SDK bridge (SmartRouterAdapter)
- [x***REMOVED*** Overlay Server/Client — IPC для инструментов
- [x***REMOVED*** **Orchestrator (FSM/DAG)** — scripts/orchestrator.py
  - Step lifecycle: PENDING → READY → RUNNING → SUCCESS/FAILED/SKIPPED
  - Workflow lifecycle: PENDING → PLANNING → RUNNING → COMPLETED/FAILED
  - DAG dependency resolution (depends_on)
  - Tool Executor: Shell, Python, File, Memory, Knowledge
  - Validator: not_empty, min_length, contains
  - Default Planner: код/рефакторинг, исследование, архитектура
  - Error handling с retry
  - CLI: run, list, get
- [x***REMOVED*** **37 тестов** Orchestrator — 0 errors

### ✅ Сделано
- [x***REMOVED*** **Model Gateway** — scripts/model_gateway.py
  - Единый OpenAI-совместимый API для DeepSeek, Gemini, Ollama, OpenRouter, SambaNova, DashScope
  - Graceful fallback: key rotation → модель fallback → error
  - Capability-based routing через SmartRouter
  - Key rotation через KeyPool
  - Подсчёт токенов (эвристика)
  - EventBus интеграция (model.called / model.fallback / model.cached)
  - Provider implementations: OpenAICompatibleProvider, GeminiProvider, OllamaProvider
  - CLI: generate, status, models
  - 27 тестов — 0 errors

### ✅ Сделано
- [x***REMOVED*** **Tool Runtime** — scripts/tool_runtime.py
  - BaseTool ABC + ToolMeta/ParamSchema/ToolResult types
  - GitTool: status, diff, log, add, commit, branch, tag, checkout, pull, push
  - SQLiteTool: SELECT/INSERT/UPDATE/CREATE с prepared statements
  - HTTPTool: GET/POST/PUT/DELETE/HEAD/PATCH через httpx
  - FileTool: read/write/list/delete/copy/move/exists/mkdir с path safety
  - ShellTool: shell-команды с timeout, cwd, env
  - ToolRegistry: register/get/list/execute/execute_multi + параметр валидация
  - EventBus интеграция (tool.executed / tool.failed)
  - Полная обратная совместимость Orchestrator (ToolExecutor.run() @staticmethod)
  - 50 тестов — 0 errors

### 🔴 План
- [ ***REMOVED*** Streaming — реализовать true streaming для всех провайдеров
- [ ***REMOVED*** Cost-aware routing — учёт стоимости при выборе модели
- [ ***REMOVED*** Локальный инференс — Qwen 2.5 через llama.cpp/Ollama

---

## 🔴 Phase 4: Plugin API + MCP + Local Models

**Статус:** 🟡 В РАБОТЕ (Event Bus + интеграция готовы)
**Фокус:** Событийно-ориентированная архитектура

### ✅ Сделано
- [x***REMOVED*** **Event Bus** — scripts/event_bus.py
  - Publish/subscribe шина с wildcard matching ("task.*" → "task.completed")
  - Фильтр-функции для точной настройки доставки
  - SQLite лог всех событий с запросами по типу/времени
  - Thread-safe (lock только на поиск подписчиков, хендлеры без блокировки)
  - Статистика (всего событий, по типам, за час)
  - Фабрики: task_event, step_event, memory_event, context_event
  - CLI: publish, events, stats, clear
- [x***REMOVED*** **EventBus + Orchestrator** — интеграция
  - workflow.created / workflow.planning / workflow.started / workflow.completed / workflow.failed
  - step.started / step.completed / step.failed / step.skipped
  - Обратная совместимость: Orchestrator() без event_bus не публикует события
- [x***REMOVED*** **EventBus + MemoryEngine** — интеграция
  - memory.stored / memory.deleted / memory.cleared
  - event_bus параметр в __init__ (опционально, обратная совместимость)
- [x***REMOVED*** **EventBus + KnowledgeEngine** — интеграция
  - knowledge.indexed / knowledge.searched / knowledge.rebuilt
  - event_bus параметр в __init__ (опционально)
- [x***REMOVED*** **EventBus + ContextManager** — интеграция
  - session.created / session.completed / checkpoint.created
  - event_bus параметр в __init__ (опционально)
- [x***REMOVED*** **Auto-index subscriber** — scripts/event_subscribers.py
  - memory.stored → автоматическая индексация в KnowledgeEngine
  - checkpoint.created → логирование в консоль
  - memory.cleared → уведомление о необходимости перестройки индекса
  - register_all() — единая точка регистрации всех подписчиков

### ✅ Сделано
- [x***REMOVED*** **Plugin API** — scripts/plugin_api.py
  - BasePlugin ABC с полным lifecycle: on_load / on_enable / on_disable / on_unload / on_event
  - PluginState enum: DISCOVERED → LOADED → ENABLED ↔ DISABLED, ERROR
  - PluginMeta, PluginManifest, PluginEntry, PluginResult types
  - PluginRegistry: register / enable / disable / unload / list / get / execute
  - PluginLoader: discover / load (importlib) / load_all из plugins/ директории
  - EventBus интеграция: subscribe на enable, unsubscribe на disable
  - ToolRegistry интеграция: регистрация инструментов плагина
  - Rollback подписок при ошибке on_enable()
  - CLI: list, enable, disable, execute, status, reload
  - create_plugin_registrar() — единая точка интеграции
- [x***REMOVED*** **Демо-плагины**
  - **hello_world** — plugins/hello_world/
    - Actions: hello, echo, status, log, reset
    - Подписка на system.* и plugin.* события
    - manifest.json с метаданными
- [x***REMOVED*** **65 тестов** — Plugin API, 0 errors
  - BasePlugin: lifecycle, execute, tools, error handling
  - PluginRegistry: register/enable/disable/unload, state machine, get_state
  - PluginLoader: discover, load, load_all, manifest чтение
  - EventBus интеграция: подписка, отписка, plugin.enabled/disabled события
  - PluginManifest: from_dict / to_dict
  - Edge cases: SilentPlugin, FailingPlugin, re-registration, temp plugins
  - Integration: create_plugin_registrar + ToolRegistry

### 🔴 План
- [ ***REMOVED*** MCP Server — интеграция с Claude, Gemini, OpenClaw
- [ ***REMOVED*** MCP Client — подключение внешних MCP-серверов
- [ ***REMOVED*** Плагины: tg_messenger, system_monitor, knowledge_sync
- [ ***REMOVED*** Distributed Agents — мульти-агентная оркестрация

---

## 🔴 Phase 5: Flutter UI + Android Service + Remote Sync

**Статус:** 🔴 ПЛАНИРОВАНИЕ
**Фокус:** UI, мобильность, синхронизация

### 🔴 План
- [ ***REMOVED*** Flutter-приложение
- [ ***REMOVED*** Foreground Service — решение Phantom Process Killer
- [ ***REMOVED*** WebView для дашборда
- [ ***REMOVED*** Встроенный терминал
- [ ***REMOVED*** Remote Sync — синхронизация контекста между устройствами

---

## 📊 Сводка

| Фаза | Статус | Готовность | Что уже есть |
|------|--------|-----------|-------------|
| **Phase 1** | ✅ Завершена | 100% | Streaming, Tasks, Router, Memory, Context Builder, Unified Context, 195 тестов |
| **Phase 2** | ✅ Завершена | 100% | Memory Engine + Knowledge Engine + Graph Search + Semantic Search + auto-index + seeded docs, 99+ тестов |
| **Phase 3** | 🟡 В РАБОТЕ | ~85% | Router + Orchestrator + ModelGateway + ToolRuntime, 114 тестов. ✅ Groq фикс (User-Agent), ✅ Git инициализирован |
| **Phase 4** | 🟡 В РАБОТЕ | ~60% | Event Bus + Plugin API + интеграции, 101 тест. ✅ EventBus активирован (17 типов, 55 событий), ✅ Knowledge Engine наполнен (27 док.) |
| **Phase 5** | 🔴 План | 0% | Ничего не начато |

---

## 🎯 Ближайшие шаги

1. ✅ **Phase 1** — Фундамент закрыт
2. 🟡 **Phase 2** — Knowledge Engine + Graph Search + Semantic Search
3. ✅ **Phase 3** — Router + Orchestrator + Model Gateway + Tool Runtime
4. 🟡 **Phase 4** — Plugin API ✅ → MCP Server → MCP Client → Distributed Agents
5. 🔴 **Phase 5** — Flutter UI / Android Service / Remote Sync

---

_Связанные файлы: [BUFFY_PROJECT.md***REMOVED***(../BUFFY_PROJECT.md), [TASK.md***REMOVED***(../TASK.md), [CHANGELOG.md***REMOVED***(../CHANGELOG.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md)_
