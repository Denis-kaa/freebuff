# MODULE CONSOLIDATION — Аудит пересечений и дублей модулей Workspace OS

> **Версия:** 1.0.0
> **Дата:** 2026-07-31
> **Статус:** 🟢 АКТУАЛЕН (отчёт, 2026-07-31) — результаты могут устареть после мерджа Telegram-ботов
> **Миссия:** Этап 6 консолидации (`pompts/promt32.md`)
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
| `MemoryEngine` | `scripts/memory_engine.py` | EventBus | `data/memory*` | ✅ |
| `KnowledgeEngine` | `scripts/knowledge_engine.py` | EventBus, MemoryEngine, GraphIndex | `context/knowledge/index.db` | ✅ |
| `GraphIndex` | `scripts/graph_index.py` | MemoryEngine | SQLite | ✅ |
| `EMEngine` | `scripts/engineering_memory.py` | EventBus, MemoryEngine, KnowledgeEngine | `docs/engineering-memory/` | ✅ |
| `RAGEngine` | `scripts/rag_engine.py` | KnowledgeEngine | — (поверх KE) | ✅ |
| `CollaborationEngine` | `scripts/collaboration.py` | EventBus, PresenceEngine | `data/collaboration.db` | ✅ |
| `PresenceEngine` | `scripts/presence.py` | EventBus | `data/presence.db` | ✅ |
| `RoleEngine` | `scripts/roles.py` | PresenceEngine, CollaborationEngine (DI) | `data/roles.db` | ✅ |
| `MetricsEngine` | `scripts/metrics.py` | EventBus (context.db, verifier.db) | `data/metrics.db` | ✅ |
| `ProjectPulse` | `scripts/project_pulse.py` | EventBus | SQLite | ✅ |

**Вывод по движкам:** пересечений ответственности нет. Границы соответствуют
KMS-правилу (Memory=краткосрочная, Knowledge=канонический индексатор, EM=нарративная,
RAG=фича KnowledgeEngine). Все 10 движков — **✅ NO DUP**.

---

## 3. Реестр дублей по областям (A–J)

### A. Router — 3 модуля, 2 пересечения 🟡

| Модуль | Класс | Роль |
|--------|-------|------|
| `core/router.py` | `ModelCatalog`, `SmartRouter` | Роутинг по сложности задачи (threshold 0.3/0.7) |
| `scripts/model_gateway.py` | `ModelGateway` | Провайдер-гейтвей: OpenAI/Gemini/Ollama, generate/generate_stream/generate_by_capabilities |
| `freebuff_plugin/router.py` | `IntentRouter` | Роутинг намерений (intent) |
| `scripts/sdk_bridge.py` | `SmartRouterAdapter` | Адаптер freebuff ↔ termux-ai-agent |

**Анализ:** `SmartRouter` (сложность-роутинг) и `ModelGateway` (провайдер-гейтвей) —
два уровня одного слоя: первый выбирает модель по сложности, второй исполняет через
провайдера. Функционального дубля нет (разные задачи), но API пересекается
(`generate*` есть у обоих). `IntentRouter` — отдельная область (намерения).

**Вердикт: 🟡 DOCUMENTED OVERLAP.** Причина: два слоя роутинга (выбор модели →
исполнение). Связываются через `sdk_bridge.SmartRouterAdapter`. Не объединять —
адаптер уже выполняет роль моста.

### B. Telegram — 2 бота 🔴

| Модуль | Класс | Роль |
|--------|-------|------|
| `scripts/telegram_bot.py` | `TelegramFreebuffBot` | Основной бот уведомлений/управления |
| `freebuff_plugin/tgbot.py` | `ScenarioTGBot` | Сценарный TG-бот (Scenario Engine) |

**Анализ:** два независимых Telegram-бота с пересечением функций
(отправка сообщений, обработка команд), каждый со своим тестовым файлом
(`tests/test_telegram_bot.py`, `tests/test_tgbot.py`). `scripts/start_telegram_bot.sh`
и `scripts/start_tgbot.sh` — два способа запуска.

**Вердикт: 🔴 DUPLICATE.** Действие (не в рамках этого этапа — требует изменения кода):
1. Определить общего предка `BaseTGBot` (отправка, команды, здоровье);
2. `TelegramFreebuffBot` и `ScenarioTGBot` → наследуют, остаются по слоям
   (scripts = уведомления, freebuff_plugin = сценарии);
3. ИЛИ зафиксировать как адаптеры с общей шиной сообщений (EventBus).
→ Перенесено в [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md).

### C. MCP — 4 модуля, комплементарны ✅

| Модуль | Роль |
|--------|------|
| `scripts/mcp_server.py` | MCP Server (STDIO + HTTP), 51 инструмент |
| `scripts/mcp_fastapi.py` | HTTP FastAPI-обёртка над MCP |
| `freebuff_plugin/mcp_server.py` | MCP-мост для плагинов |
| `freebuff_plugin/mcp_client.py` | MCP Client (stdio + HTTP transport) |

**Вердикт: ✅ NO DUP.** Сервер/обёртка/мост/клиент — четыре роли одного протокола.
`mcp_fastapi` расширяет `mcp_server` HTTP-эндпоинтами; `freebuff_plugin/mcp_*` —
граница ядро↔плагин (контракт INTEGRATION_CONTRACT).

### D. Memory — ContextManager vs MemoryEngine ✅

| Модуль | Роль |
|--------|------|
| `scripts/context_manager.py` | Сессии/сообщения/чекпоинты (`SCHEMA_VERSION=5`), CONTEXT_FULL |
| `scripts/memory_engine.py` | 6 уровней памяти (short→long+vector), store/retrieve/search |

**Вердикт: ✅ NO DUP.** ContextManager = состояние сессии; MemoryEngine = уровни
памяти. Разные таблицы, разные задачи. Граница зафиксирована в canonical §3.4.

### E. Knowledge — 3 индексатора, иерархия ✅

| Модуль | Роль |
|--------|------|
| `scripts/knowledge_engine.py` | FTS5 + TF-IDF + SemanticIndex (3 внутренних индекса + unified search) |
| `scripts/rag_engine.py` | RRF-слияние, re-ranking поверх KnowledgeEngine |
| `scripts/graph_index.py` | Граф связей (BFS, subgraph) |

**Вердикт: ✅ NO DUP.** RAG = фича KnowledgeEngine (KMS-решение promt31), не второй
индексатор. GraphIndex дополняет Knowledge (связи), не заменяет.

### F. Registry — 7+ реестров, фрагментация паттерна 🟡

| Реестр | Модуль | Регистрирует |
|--------|--------|--------------|
| `ModelCatalog` | `core/router.py` | Модели |
| `RuntimeRegistry` | `freebuff_plugin/runtime/registry.py` | Runtime-определения, провайдеры, адаптеры |
| `RuntimeCapabilityRegistry` | `freebuff_plugin/runtime/registry.py` | Capabilities Runtime |
| `AdapterRegistry` | `freebuff_plugin/runtime/adapter.py` | Runtime-адаптеры |
| `AgentRegistry` | `freebuff_plugin/acp_protocol.py` | ACP-агенты |
| `ToolRegistry` | `scripts/tool_runtime.py` | Инструменты |
| `PluginRegistry` | `scripts/plugin_api.py` | Плагины |
| `AgentMesh` | `scripts/distributed_agents.py` | Распределённые агенты |

**Анализ:** 8 реестров, каждый для своего типа сущностей — функциональных дублей нет
(регistrируются разные типы). Но паттерн «регистр + register()» повторён 8 раз —
фрагментация. Унификация в единый **Registry Contract** (Этап 9) позволит
переиспользовать общую логику и служить данными для авто-проверки.

**Вердикт: 🟡 DOCUMENTED OVERLAP** (паттерн-дубль, не функциональный). Действие:
Этап 9 — общий контракт реестра; существующие реестры остаются как специализации.

### G. Context — стриминг/сессии/конспекты ✅

| Модуль | Роль |
|--------|------|
| `scripts/stream_session.py` | Непрерывная запись сессии (BackgroundWriter) |
| `scripts/stream_bridge.py` | Мост log_user/log_assistant/start_session |
| `scripts/auto_conspect.py` | Автосуммаризация, чекпоинты |
| `scripts/bootstrap.py` | Восстановление при старте |

**Вердикт: ✅ NO DUP.** Комплементарные стадии lifecycle сессии: запись → мост →
суммаризация → восстановление.

### H. Tool Runtime — ядро vs плагины ✅

| Модуль | Роль |
|--------|------|
| `scripts/tool_runtime.py` | `BaseTool`, `validate_params()`, `execute()`, `ToolRegistry` |
| `plugins/*/__init__.py` | `do_*` действия плагинов |

**Вердикт: ✅ NO DUP.** ToolRuntime — исполнение инструментов ядра; `do_*` — действия
плагинов (граница ядро↔плагин через `freebuff_plugin/__init__.py`).

### I. Plugin API — два «plugin»-домена 🟡

| Модуль | Роль |
|--------|------|
| `scripts/plugin_api.py` | PluginLoader, PluginRegistry, BasePlugin (on_load/enable/disable/unload) |
| `plugins/*/` | Пользовательские плагины (hello_world, tg_messenger, system_monitor, knowledge_sync) |
| `freebuff_plugin/` | Внутренний пакет интеграции (bridge, runtime, scenarios, event) |

**Анализ:** два значения слова «plugin» — пользовательские плагины (`plugins/` через
PluginAPI) и внутренний пакет интеграции (`freebuff_plugin/`). Функционального дубля
нет, но терминологическое пересечение — риск путаницы.

**Вердикт: 🟡 DOCUMENTED OVERLAP** (терминология). Действие: глоссарий
([GLOSSARY.md***REMOVED***(GLOSSARY.md) §3 «Plugin») уже разграничивает; в новых документах —
уточнять «пользовательский плагин» vs «пакет интеграции».

### J. Event Bus — живая шина vs персистентность ✅

| Модуль | Роль |
|--------|------|
| `scripts/event_bus.py` | Живая шина: publish/subscribe/wildcard + SQLite-лог |
| `freebuff_plugin/event/` | EventStore, replay, timeline, audit, pulse (поверх шины) |

**Вердикт: ✅ NO DUP.** Шина (live) + хранилище/аудит (persistence) — два слоя
Event Platform, комплементарны.

---

## 4. Сводная таблица вердиктов

| Область | Вердикт | Действие |
|---------|---------|----------|
| Движки (10) | ✅ NO DUP | — |
| A. Router | 🟡 DOCUMENTED OVERLAP | Оставить (адаптер sdk_bridge уже связывает) |
| B. Telegram | 🔴 DUPLICATE | Мердж/общий предок → ARCHITECTURAL_DEBT |
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
- [ ***REMOVED*** Мердж Telegram-ботов (отдельная задача, вне миссии — требует изменения кода)

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), [GLOSSARY.md***REMOVED***(GLOSSARY.md), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md), [ARCHITECTURAL_DEBT.md***REMOVED***(ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
