# ROADMAP — Buffy Project

> **Статус:** LEGACY — заменён на [ROADMAP_PROMT31_WORKSPACE_OS.md***REMOVED***(ROADMAP_PROMT31_WORKSPACE_OS.md) + [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(ROADMAP_PROMT32_CONSOLIDATION.md) (см. [DOCUMENT_REGISTRY.md***REMOVED***(../DOCUMENT_REGISTRY.md))
> **Версия:** 3.0.0
> **Актуально:** 2026-07-29
> **Основание:** [016_02_arhitektura_reorganizaciya.md***REMOVED***(../../pompts_11/016_02_arhitektura_reorganizaciya.md) — полный аудит и реструктуризация проекта

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
- [x***REMOVED*** **Capability Router** — core_02/router.py, data-driven scoring
- [x***REMOVED*** **Memory Engine** — 5 уровней памяти (Working/Project/Knowledge/Personal/Archive)
- [x***REMOVED*** **Context Builder** — scripts_01/context_builder.py
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
- [x***REMOVED*** **Knowledge Engine** — scripts_01/knowledge_engine.py
  - SQLite FTS5 (keyword search с BM25 ранжированием)
  - TF-IDF vector index (семантический поиск через numpy)
  - Hybrid search (взвешенная комбинация FTS5 + TF-IDF)
  - Индексация из Memory Engine
  - Поиск capabilities по запросу
  - CLI для ручного поиска и индексации
- [x***REMOVED*** **42 теста** Knowledge Engine — 0 errors

### ✅ Сделано
- [x***REMOVED*** **Graph Search** — scripts_01/graph_index.py
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
- [x***REMOVED*** Capability-based SmartRouter (core_02/router.py)
- [x***REMOVED*** ModelCatalog с 6 моделями + capability profiles
- [x***REMOVED*** SDK bridge (SmartRouterAdapter)
- [x***REMOVED*** Overlay Server/Client — IPC для инструментов
- [x***REMOVED*** **Orchestrator (FSM/DAG)** — scripts_01/orchestrator.py
  - Step lifecycle: PENDING → READY → RUNNING → SUCCESS/FAILED/SKIPPED
  - Workflow lifecycle: PENDING → PLANNING → RUNNING → COMPLETED/FAILED
  - DAG dependency resolution (depends_on)
  - Tool Executor: Shell, Python, File, Memory, Knowledge
  - Validator: not_empty, min_length, contains
  - Default Planner: код/рефакторинг, исследование, архитектура
  - Error handling с retry
  - CLI: run, list, get
- [x***REMOVED*** **51 тестов** Orchestrator — 0 errors (parallel execution + EventBus)
- [x***REMOVED*** **Параллельное выполнение шагов** — ThreadPoolExecutor(max_workers), thread-safe DAG
- [x***REMOVED*** **EventBus интеграция расширена** — step.retrying, workflow.progress

### ✅ Сделано
- [x***REMOVED*** **Model Gateway** — scripts_01/model_gateway.py
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
- [x***REMOVED*** **Tool Runtime** — scripts_01/tool_runtime.py
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
- [ ***REMOVED*** freebuff инференс — Qwen 2.5 через llama.cpp/Ollama

---

## 🟡 Phase 4: Plugin API + MCP + Event Platform + Runtime

**Статус:** 🟡 В РАБОТЕ (~93%)
**Фокус:** Событийно-ориентированная архитектура, мульти-агентность, абстракция Runtime

### ✅ Сделано
- [x***REMOVED*** **Event Bus** — scripts_01/event_bus.py
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
- [x***REMOVED*** **Auto-index subscriber** — scripts_01/event_subscribers.py
  - memory.stored → автоматическая индексация в KnowledgeEngine
  - checkpoint.created → логирование в консоль
  - memory.cleared → уведомление о необходимости перестройки индекса
  - register_all() — единая точка регистрации всех подписчиков

### ✅ Сделано
- [x***REMOVED*** **Plugin API** — scripts_01/plugin_api.py
  - BasePlugin ABC с полным lifecycle: on_load / on_enable / on_disable / on_unload / on_event
  - PluginState enum: DISCOVERED → LOADED → ENABLED ↔ DISABLED, ERROR
  - PluginMeta, PluginManifest, PluginEntry, PluginResult types
  - PluginRegistry: register / enable / disable / unload / list / get / execute
  - PluginLoader: discover / load (importlib) / load_all из plugins_04/ директории
  - EventBus интеграция: subscribe на enable, unsubscribe на disable
  - ToolRegistry интеграция: регистрация инструментов плагина
  - Rollback подписок при ошибке on_enable()
  - CLI: list, enable, disable, execute, status, reload
  - create_plugin_registrar() — единая точка интеграции
- [x***REMOVED*** **Демо-плагины**
  - **hello_world** — plugins_04/hello_world/
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

### ✅ Сделано
- [x***REMOVED*** **MCP Server** — scripts_01/mcp_server.py
  - Pure Python MCP server (JSON-RPC 2.0 over stdio, без внешних SDK)
  - 12 tools: ToolRegistry (git/file/shell/sqlite/http) + knowledge/memory/session/plugins
  - 9 resources: buffy://manifest, buffy://roadmap, buffy://knowledge, buffy://memory, ...
  - 3 prompts: context_resume, knowledge_search, task_start
  - Protocol 2025-03-26, lazy loading, EventBus integration, workspace-aware
  - **Streamable HTTP транспорт** (MCP 2025-03-26 spec): single endpoint /mcp
    - POST: JSON-RPC, GET: SSE stream, DELETE: session termination
    - Mcp-Session-Id header, Origin validation, thread-safe session manager
    - CLI: --http, --host, --port
  - **FastAPI обёртка**: SSE streaming, Cloudflare Tunnel, health check
  - 120 тестов, 0 errors (53 stdio + 10 session manager + 26 HTTP + 18 RAL + 12 bootstrap + 1 FastAPI)
- [x***REMOVED*** **MCP Client** — freebuff_plugin_03/mcp_client.py (v4.6.0)
  - Два транспорта: StdioMCPClient (подпроцесс + stdin/stdout) + HTTPMCPClient (Streamable HTTP)
  - Reader thread, очередь ответов с фильтрацией stale ID
  - Поддержка MCP 2025-03-26: initialize, tools/list, tools/call, resources/list, prompts/list, ping
- [x***REMOVED*** **Bridge Layer (MCP ↔ ACP)** — freebuff_plugin_03/bridge_layer.py (v4.6.0)
  - Трансляция MCP ↔ Agent Collaboration Protocol
  - connect_mcp_stdio / connect_mcp_http, автоматический reconnect
  - 4 MCP инструмента: bridge_connect, bridge_list, bridge_disconnect, bridge_rpc
  - 60 тестов
- [x***REMOVED*** **ACP Protocol** — freebuff_plugin_03/acp_protocol.py (v4.6.0)
  - AgentRegistry + ACPHandler + AgentInfo/AgentStatus/ACPTask/ACPResult
  - Heartbeat loop, авто-саморегистрация, фильтрация задач по target
- [x***REMOVED*** **Event Platform** — freebuff_plugin_03/event/ (v4.7.0)
  - EventStore (SQLite + FTS5, CRUD, batch, миграция, агрегация)
  - EventReplay (instant/realtime, rebuild из snapshot)
  - TimelineEngine, AuditEngine, PulseEngine
  - 5 MCP инструментов: event_search, event_timeline, event_replay, event_audit, event_pulse
  - 61 тест
- [x***REMOVED*** **Bootstrap Engine** — freebuff_plugin_03/bootstrap/ (v4.7.0)
  - 6 модулей: engine, checker, installer, doctor, state, profiles.yaml
  - 3 MCP инструмента: bootstrap_check, bootstrap_run, bootstrap_status
  - 61 тест
- [x***REMOVED*** **Runtime Abstraction Layer** — freebuff_plugin_03/runtime/ (v4.9.0)
  - RuntimeAdapter ABC + StdioMCPAdapter + HTTPMCPAdapter + AdapterRegistry
  - RuntimeRegistry (JSON persistence) + RuntimeCapabilityRegistry
  - FreebuffAdapter + ClaudeCodeAdapter
  - 5 MCP инструментов: runtime_list, runtime_connect, runtime_disconnect, runtime_select, runtime_generate
  - Provider auto-discovery: YAML-манифесты (freebuff, claude_code, openclaw)
  - Marketplace-ready: новый Runtime без изменения ядра
  - 69 тестов
- [x***REMOVED*** **Scenario Engine** — freebuff_plugin_03/scenario_engine.py (v4.5.0)
  - YAML front matter + markdown, 11 сценариев
  - 83 теста
- [x***REMOVED*** **Telegram Bot** — freebuff_plugin_03/tgbot.py + scripts_01/telegram_bot.py (v4.5.0)
  - /scenarios list/apply/search, inline keyboard, state management
  - 44 теста
- [x***REMOVED*** **doctor.py** — scripts_01/doctor.py (Task 2)
  - CLI-инструмент диагностики: --full, --check, --json
  - EventBus интеграция, проверка Python/SQLite/Git/Node/Disk/RAM/путей
- [x***REMOVED*** **INTEGRATION_CONTRACT.md** — freebuff_plugin_03/ (Task 2)
  - Контракт между ядром и плагином
- [x***REMOVED*** **CODE_QUALITY_STANDARD** — pompts_11/CODE_QUALITY_STANDARD.md
  - Интегрирован как обязательный production-ready регламент
- [x***REMOVED*** **Promt16.md full audit** — Tasks 0-6 полностью выполнены (v5.0.0)
  - Стратегический слой (ARCHITECTURE_PRINCIPLES, COMPATIBILITY_MATRIX, RUNTIME_VALIDATION_FRAMEWORK)
  - Реорганизация docs_10/ (45 файлов → 7 подпапок, INDEX.md)
  - Граница ядро↔плагин (imports через __init__.py, try/except, убраны жёсткие пути)
  - Унификация projects_17/ (README.md + MANIFEST.md для всех 4 проектов)
  - Чистка data_13/context.db (91→45 сессий)
  - Аудит scripts_01/ (4 мёртвых → archive/)
  - Smoke-test: 1152 passed, 1 skipped, 0 failures

### 🔴 План
- [ ***REMOVED*** Distributed Agents — мульти-агентная оркестрация
- [ ***REMOVED*** Плагины: tg_messenger, system_monitor, knowledge_sync (коннекторы)

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
| **Phase 3** | 🟡 В РАБОТЕ | ~93% | Router + Orchestrator (parallel DAG + EventBus) + ModelGateway + ToolRuntime, 150+ тестов. ✅ Groq фикс, ✅ Git, ✅ Streaming (SSE/Gemini/Ollama), ✅ Parallel execution, ✅ step.retrying/workflow.progress || **Phase 4** | 🟡 В РАБОТЕ | ~93% | Event Bus + Plugin API + MCP Server (stdio + HTTP + FastAPI + Cloudflare) + MCP Client + Bridge Layer (MCP↔ACP) + ACP Protocol + Event Platform + Bootstrap Engine + Runtime Abstraction Layer + Scenario Engine + Telegram Bot + doctor.py + Marketplace-ready + INTEGRATION_CONTRACT, 500+ тестов. ✅ Все 016_02_arhitektura_reorganizaciya.md tasks (0-6) | **Phase 5** | 🔴 План | 0% | Ничего не начато |
| **Всего** | — | — | **1152 тестов** (305s), 1 skipped, 0 failures |

---

## 🎯 Ближайшие шаги

1. ✅ **Phase 1** — Фундамент закрыт
2. 🟡 **Phase 2** — Knowledge Engine + Graph Search + Semantic Search
3. ✅ **Phase 3** — Router + Orchestrator + Model Gateway + Tool Runtime (~93%)
4. 🟢 **Phase 4** — Plugin API ✅ → MCP Server ✅ → MCP Client ✅ → Bridge Layer ✅ → ACP ✅ → Event Platform ✅ → Runtime Abstraction ✅ → Scenario Engine ✅ → Marketplace ✅ → Distributed Agents 🔜
5. 🔴 **Phase 5** — Flutter UI / Android Service / Remote Sync

---

_Связанные файлы: [BUFFY_PROJECT.md***REMOVED***(../../BUFFY_PROJECT.md), [TASK.md***REMOVED***(../../TASK.md), [CHANGELOG.md***REMOVED***(../../CHANGELOG.md), [SYSTEM_INVENTORY.md***REMOVED***(../core/SYSTEM_INVENTORY.md)_
