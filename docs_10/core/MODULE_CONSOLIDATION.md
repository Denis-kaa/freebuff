# MODULE CONSOLIDATION — Аудит пересечений и дублей модулей Workspace OS

> **Версия:** 1.1.0
> **Дата:** 2026-07-31 (обновлено 2026-08-01)
> **Статус:** 🟢 АКТУАЛЕН — дубль Telegram закрыт (DEBT-007, 2026-08-01)
> **Миссия:** Этап 6 консолидации (`pompts_11/032_09_workspace_os_konsolidaciya.md`)
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md)
> **Связанные:** [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [GLOSSARY.md***REMOVED***(GLOSSARY.md) (терминология), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md)

---

## 1. Назначение и правила

**Зачем:** консолидация модулей — проверить, что в системе нет функциональных дублей
(два модуля, делающие одно и то же), а осознанные повторы (адаптеры, разные слои)
зафиксированы с обоснованием.

**Правила (mission lock):**
1. Запрещено объединять рабочий код «ради красоты» — только при явной пользе.
2. Дубль → решение: **объединить** / **оформить как адаптер** / **задокументировать причину**.
3. Все выводы проверены по коду (импорты, классы, методы) — 2026-07-31.
4. Новые реестры/унификация — только в рамках Этапов 6/9, не как отдельные фичи.

**Вердикты:**
- ✅ **NO DUP** — компоненты дополняют друг друга, границы зафиксированы;
- 🟡 **DOCUMENTED OVERLAP** — осознанное пересечение, причина зафиксирована;
- 🔴 **DUPLICATE** — реальный дубль, требуется действие (мердж/адаптер).

---

## 2. Матрица движков (проверено по импортам)

> Реестр и границы: [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) §3–4.

> **Примечание о покрытии:** запрошено «8 движков», но матрица покрывает полный канонический реестр
> (C1–C6 + S1–S7 из [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), включая GraphIndex и ProjectPulse) — 10 строк.

| Движок | Файл | Зависимости (импорты) | Хранилище | Вердикт |
|--------|------|----------------------|-----------|---------|
| `MemoryEngine` | `scripts_01/memory_engine.py` | EventBus | `data_13/memory*` | ✅ |
| `KnowledgeEngine` | `scripts_01/knowledge_engine.py` | EventBus, MemoryEngine, GraphIndex | `context_12/knowledge/index.db` | ✅ |
| `GraphIndex` | `scripts_01/graph_index.py` | MemoryEngine | SQLite | ✅ |
| `EMEngine` | `scripts_01/engineering_memory.py` | EventBus, MemoryEngine, KnowledgeEngine | `docs_10/engineering-memory/` | ✅ |
| `RAGEngine` | `scripts_01/rag_engine.py` | KnowledgeEngine | — (поверх KE) | ✅ |
| `CollaborationEngine` | `scripts_01/collaboration.py` | EventBus, PresenceEngine | `data_13/collaboration.db` | ✅ |
| `PresenceEngine` | `scripts_01/presence.py` | EventBus | `data_13/presence.db` | ✅ |
| `RoleEngine` | `scripts_01/roles.py` | PresenceEngine, CollaborationEngine (DI) | `data_13/roles.db` | ✅ |
| `MetricsEngine` | `scripts_01/metrics.py` | EventBus (context.db, verifier.db) | `data_13/metrics.db` | ✅ |
| `ProjectPulse` | `scripts_01/project_pulse.py` | EventBus | SQLite | ✅ |

**Вывод по движкам:** пересечений ответственности нет. Границы соответствуют
KMS-правилу (Memory=краткосрочная, Knowledge=канонический индексатор, EM=нарративная,
RAG=фича KnowledgeEngine). Все 10 движков — **✅ NO DUP**.

---

## 3. Реестр дублей по областям (A–J)

### A. Router — 3 модуля, 2 пересечения 🟡

| Модуль | Класс | Роль |
|--------|-------|------|
| `core_02/router.py` | `ModelCatalog`, `SmartRouter` | Роутинг по сложности задачи (threshold 0.3/0.7) |
| `scripts_01/model_gateway.py` | `ModelGateway` | Провайдер-гейтвей: OpenAI/Gemini/Ollama, generate/generate_stream/generate_by_capabilities |
| `freebuff_plugin_03/router.py` | `IntentRouter` | Роутинг намерений (intent) |
| `scripts_01/sdk_bridge.py` | `SmartRouterAdapter` | Адаптер freebuff ↔ termux-ai-agent |

**Анализ:** `SmartRouter` (сложность-роутинг) и `ModelGateway` (провайдер-гейтвей) —
два уровня одного слоя: первый выбирает модель по сложности, второй исполняет через
провайдера. Функционального дубля нет (разные задачи), но API пересекается
(`generate*` есть у обоих). `IntentRouter` — отдельная область (намерения).

**Вердикт: 🟡 DOCUMENTED OVERLAP.** Причина: два слоя роутинга (выбор модели →
исполнение). Связываются через `sdk_bridge.SmartRouterAdapter`. Не объединять —
адаптер уже выполняет роль моста.

### B. Telegram — 2 бота, общий предок ✅ (DEBT-007 resolved 2026-08-01)

| Модуль | Класс | Роль |
|--------|-------|------|
| `scripts_01/tgbot_base.py` | `BaseTGBot` | Общая инфраструктура: .env, токен, Application, polling, error handler |
| `scripts_01/telegram_bot.py` | `TelegramFreebuffBot` | Основной бот уведомлений/управления (наследует BaseTGBot) |
| `freebuff_plugin_03/tgbot.py` | `ScenarioTGBot` | Сценарный TG-бот (Scenario Engine) (наследует BaseTGBot) |

**Анализ (2026-08-01):** дубль закрыт по схеме из долга: общий предок
`BaseTGBot` (scripts_01/tgbot_base.py) — `load_dotenv`, `build_application`,
`run_polling`, `error_handler`. Оба бота наследуют и остаются в своих слоях
(scripts = уведомления, freebuff_plugin = сценарии); дублирующийся polling-цикл
и .env-загрузка удалены. Тесты: `tests_09/test_tgbot_base.py` (новый) +
существующие `test_telegram_bot.py`, `test_tgbot.py`.

**Вердикт: ✅ NO DUP** (общий слой вынесен, боты — специализации).
→ Подробности: [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md) §5.8.

### C. MCP — 4 модуля, комплементарны ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/mcp_server.py` | MCP Server (STDIO + HTTP), 51 инструмент |
| `scripts_01/mcp_fastapi.py` | HTTP FastAPI-обёртка над MCP |
| `freebuff_plugin_03/mcp_server.py` | MCP-мост для плагинов |
| `freebuff_plugin_03/mcp_client.py` | MCP Client (stdio + HTTP transport) |

**Вердикт: ✅ NO DUP.** Сервер/обёртка/мост/клиент — четыре роли одного протокола.
`mcp_fastapi` расширяет `mcp_server` HTTP-эндпоинтами; `freebuff_plugin_03/mcp_*` —
граница ядро↔плагин (контракт INTEGRATION_CONTRACT).

### D. Memory — ContextManager vs MemoryEngine ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/context_manager.py` | Сессии/сообщения/чекпоинты (`SCHEMA_VERSION=5`), CONTEXT_FULL |
| `scripts_01/memory_engine.py` | 6 уровней памяти (short→long+vector), store/retrieve/search |

**Вердикт: ✅ NO DUP.** ContextManager = состояние сессии; MemoryEngine = уровни
памяти. Разные таблицы, разные задачи. Граница зафиксирована в canonical §3.4.

### E. Knowledge — 3 индексатора, иерархия ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/knowledge_engine.py` | FTS5 + TF-IDF + SemanticIndex (3 внутренних индекса + unified search) |
| `scripts_01/rag_engine.py` | RRF-слияние, re-ranking поверх KnowledgeEngine |
| `scripts_01/graph_index.py` | Граф связей (BFS, subgraph) |

**Вердикт: ✅ NO DUP.** RAG = фича KnowledgeEngine (KMS-решение promt31), не второй
индексатор. GraphIndex дополняет Knowledge (связи), не заменяет.

### F. Registry — 7+ реестров, фрагментация паттерна 🟡

| Реестр | Модуль | Регистрирует |
|--------|--------|--------------|
| `ModelCatalog` | `core_02/router.py` | Модели |
| `RuntimeRegistry` | `freebuff_plugin_03/runtime/registry.py` | Runtime-определения, провайдеры, адаптеры |
| `RuntimeCapabilityRegistry` | `freebuff_plugin_03/runtime/registry.py` | Capabilities Runtime |
| `AdapterRegistry` | `freebuff_plugin_03/runtime/adapter.py` | Runtime-адаптеры |
| `AgentRegistry` | `freebuff_plugin_03/acp_protocol.py` | ACP-агенты |
| `ToolRegistry` | `scripts_01/tool_runtime.py` | Инструменты |
| `PluginRegistry` | `scripts_01/plugin_api.py` | Плагины |
| `AgentMesh` | `scripts_01/distributed_agents.py` | Распределённые агенты |

**Анализ:** 8 реестров, каждый для своего типа сущностей — функциональных дублей нет
(регistrируются разные типы). Но паттерн «регистр + register()» повторён 8 раз —
фрагментация. Унификация в единый **Registry Contract** (Этап 9) позволит
переиспользовать общую логику и служить данными для авто-проверки.

**Вердикт: 🟡 DOCUMENTED OVERLAP** (паттерн-дубль, не функциональный). Действие:
Этап 9 — общий контракт реестра; существующие реестры остаются как специализации.

### G. Context — стриминг/сессии/конспекты ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/stream_session.py` | Непрерывная запись сессии (BackgroundWriter) |
| `scripts_01/stream_bridge.py` | Мост log_user/log_assistant/start_session |
| `scripts_01/auto_conspect.py` | Автосуммаризация, чекпоинты |
| `scripts_01/bootstrap.py` | Восстановление при старте |

**Вердикт: ✅ NO DUP.** Комплементарные стадии lifecycle сессии: запись → мост →
суммаризация → восстановление.

### H. Tool Runtime — ядро vs плагины ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/tool_runtime.py` | `BaseTool`, `validate_params()`, `execute()`, `ToolRegistry` |
| `plugins_04/*/__init__.py` | `do_*` действия плагинов |

**Вердикт: ✅ NO DUP.** ToolRuntime — исполнение инструментов ядра; `do_*` — действия
плагинов (граница ядро↔плагин через `freebuff_plugin_03/__init__.py`).

### I. Plugin API — два «plugin»-домена 🟡

| Модуль | Роль |
|--------|------|
| `scripts_01/plugin_api.py` | PluginLoader, PluginRegistry, BasePlugin (on_load/enable/disable/unload) |
| `plugins_04/*/` | Пользовательские плагины (hello_world, tg_messenger, system_monitor, knowledge_sync) |
| `freebuff_plugin_03/` | Внутренний пакет интеграции (bridge, runtime, scenarios, event) |

**Анализ:** два значения слова «plugin» — пользовательские плагины (`plugins_04/` через
PluginAPI) и внутренний пакет интеграции (`freebuff_plugin_03/`). Функционального дубля
нет, но терминологическое пересечение — риск путаницы.

**Вердикт: 🟡 DOCUMENTED OVERLAP** (терминология). Действие: глоссарий
([GLOSSARY.md***REMOVED***(GLOSSARY.md) §3 «Plugin») уже разграничивает; в новых документах —
уточнять «пользовательский плагин» vs «пакет интеграции».

### J. Event Bus — живая шина vs персистентность ✅

| Модуль | Роль |
|--------|------|
| `scripts_01/event_bus.py` | Живая шина: publish/subscribe/wildcard + SQLite-лог |
| `freebuff_plugin_03/event/` | EventStore, replay, timeline, audit, pulse (поверх шины) |

**Вердикт: ✅ NO DUP.** Шина (live) + хранилище/аудит (persistence) — два слоя
Event Platform, комплементарны.

---

## 4. Сводная таблица вердиктов

| Область | Вердикт | Действие |
|---------|---------|----------|
| Движки (10) | ✅ NO DUP | — |
| A. Router | 🟡 DOCUMENTED OVERLAP | Оставить (адаптер sdk_bridge уже связывает) |
| B. Telegram | ✅ NO DUP (2026-08-01) | Общий предок `BaseTGBot` реализован → DEBT-007 resolved |
| C. MCP | ✅ NO DUP | — |
| D. Memory | ✅ NO DUP | — |
| E. Knowledge | ✅ NO DUP | — |
| F. Registry | 🟡 DOCUMENTED OVERLAP (паттерн) | Этап 9: единый Registry Contract |
| G. Context | ✅ NO DUP | — |
| H. Tool Runtime | ✅ NO DUP | — |
| I. Plugin API | 🟡 DOCUMENTED OVERLAP (терминология) | Глоссарий уже разграничил |
| J. Event Bus | ✅ NO DUP | — |

---

## 5. Критерий согласованности (Этап 6)

- [x***REMOVED*** Матрица 10 движков проверена по импортам — пересечений ответственности нет
- [x***REMOVED*** Области A–J проаудированы на дубли
- [x***REMOVED*** 1 реальный дубль найден (Telegram) → передан в ARCHITECTURAL_DEBT
- [x***REMOVED*** Осознанные повторы зафиксированы с причиной (Router-слои, Registry-паттерн, Plugin-терминология)
- [x***REMOVED*** Мердж Telegram-ботов выполнен (2026-08-01): `BaseTGBot` в `scripts_01/tgbot_base.py`, DEBT-007 resolved

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), [GLOSSARY.md***REMOVED***(GLOSSARY.md), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
