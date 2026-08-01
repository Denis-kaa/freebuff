# Архитектурное исследование: FreeBuff → Workspace OS

**Дата:** 2026-07-31
**Источник задачи:** `pompts_11/023_02_kanonicheskaya_model_workspace_os.md`
**Роль:** Principal Software Architect + независимый исследователь
**Принцип:** эволюция существующей архитектуры, а не её замена. Никаких новых сущностей, пока не доказано, что аналога нет.
**Метод:** сверка кодовой базы (диск + git + bytecode) с концептуальной моделью Workspace OS. Каждое утверждение — с путём к файлу и именем класса/функции.

---

## 0. КРИТИЧЕСКИЙ КОНТЕКСТ: состояние кодовой базы на момент исследования

Перед самим исследованием проведена ревизия целостности репозитория. Результат обязателен для честного чтения любой карты соответствия ниже.

### 0.1. Потерянные модули (не в git, не на диске, восстановимы из байткода)

В инциденте с `git stash drop` (2026-07-31) утерян не только `scripts_01/metrics.py`, а **целые модули с их тестами**. Доказательства:

- `git log --all --oneline -- scripts_01/roles.py` → **пусто** (никогда не были в git)
- `git check-ignore scripts_01/roles.py` → **NOT_IGNORED** (не gitignore, а именно потеря)
- Байткод `scripts_01/__pycache__/*.cpython-314.pyc` **загружается** и содержит полные классы (проверено импортом)
- SQLite-файлы `data_13/*.db` (roles.db, presence.db, collaboration.db, project_pulse.db) существуют → модули реально работали

| Модуль (заявлен в CHANGELOG) | Версия | Классы в pyc (проверено импортом) | Тест (потерян) |
|---|---|---|---|
| `scripts_01/roles.py` | v5.22.0 | `RoleEngine`, `RoleDefinition`, `STANDARD_ROLES`, `AgentRole` | `tests_09/test_roles.py` |
| `scripts_01/presence.py` | v5.17.0 | `PresenceEngine`, `AgentPresence`, `PresenceHistoryEntry`, `DEFAULT_HEARTBEAT_INTERVAL` | `tests_09/test_presence.py` |
| `scripts_01/collaboration.py` | v5.18.0 | `CollaborationEngine`, `CollaborationSession`, `CollabMessage`, `Participant`, `ParticipantRole` | `tests_09/test_collaboration.py` |
| `scripts_01/distributed_agents.py` | v5.14.0 | `AgentMesh`, `TaskDistributor`, `DistributedCoordinator`, `DistributedWorkflowPlan`, `DistributedWorkflowStep`, `AgentTask` | `tests_09/test_distributed_agents.py` |
| `scripts_01/rag_engine.py` | v5.23.0 | `RAGEngine`, `RAGReport`, `FeatureVector`, `MAX_RERANK_CANDIDATES` | `tests_09/test_rag_engine.py` |
| `scripts_01/project_pulse.py` | v5.21.0 | `ProjectPulse`, `PulseEntry`, `PULSE_TYPES`, `PULSE_DB` | `tests_09/test_project_pulse.py` |
| `scripts_01/notification.py` | v5.24.x | модуль каскада уведомлений (`notify()`) | `tests_09/test_notification.py` |

Потерянные тесты (13 шт.): `test_context_phase_a.py`, `test_action_verifications.py`, `test_metrics.py`, `test_vector_memory.py`, `test_cli_ctx.py`, `test_distributed_agents.py`, `test_presence.py`, `test_collaboration.py`, `test_plugins_phase4.py`, `test_project_pulse.py`, `test_roles.py`, `test_rag_engine.py`, `test_notification.py`.

> ⚠️ **Важно про `test_metrics.py`:** `scripts_01/metrics.py` восстановлен (коммит `4f91c29`) и верифицирован через 57 тестов `test_mcp_fastapi.py`, но его **профильный тест-файл `tests_09/test_metrics.py` потерян** — у восстановленного модуля нет собственных тестов. Реконструировать из `tests_09/__pycache__/test_metrics.cpython-314-pytest-9.1.1.pyc` (загружается, классы/функции интроспектируемы) в рамках Этапа 0.

**Побочный ущерб:** `MemoryLevel.VECTOR` (6-й уровень, v5.12.0, chromadb VectorBackend) отсутствует в текущем `scripts_01/memory_engine.py` (на диске 5 уровней: WORKING/PROJECT/KNOWLEDGE/PERSONAL/ARCHIVE) — VECTOR-код и `tests_09/test_vector_memory.py` также потеряны.

### 0.2. Что это значит для исследования

Все разделы ниже помечают эти домены статусом **🔶 УТЕРЯН (восстановим из pyc)** — они были реализованы и протестированы (CHANGELOG + .db + .pyc), но физически отсутствуют в кодовой базе на момент исследования. Восстановление по методологии `metrics.py` (дизассемблер + поведенческие пробы + сверка с БД) — отдельная задача, подтверждённо выполнимая (7/7 pyc загружаются).

---

## 1. Executive Summary

### 1.1. Главный вывод

**FreeBuff уже является фундаментом Workspace OS на ~60%.** Существуют и работают: Event System, Context, Memory (5 уровней), Knowledge (FTS5 + TF-IDF + LSA), Verifier + PolicyEngine, MetricsEngine, Orchestrator, Scenario Engine, Plugin API (4 плагина), Runtime Adapter Layer, MCP (3 серверных точки входа), Telegram, Model Gateway + SmartRouter, Project Discovery, Documentation (полная core-спецификация).

**Ключевые блокеры превращения в Workspace OS:**
1. **Нет контейнера `Workspace`** — нет сущности, объединяющей пользователей, Work Areas, проекты, настройки, роли, безопасность.
2. **Нет `Work Area`** — единственный след — категории в `scan_projects.py` (leviathan/telegram/ai/web/tool/infra/personal).
3. **Нет Team/RBAC/ACL** — `PolicyEngine` управляет выбором runtime по capabilities, но это не RBAC.
4. **7 модулей потеряны** (CoWork: presence/collaboration/distributed, roles, rag_engine, project_pulse, notification) — восстановимы из pyc.
5. **4 архитектурных дубля:** роутеры (3 шт.), Telegram (3 реализации), MCP-серверы (3 шт.), event-слои (in-process EventBus + persistent EventStore).
6. **Нет Business Process Engine** — долгоживущие процессы реализованы только shell-скриптами (`cron_conspect.sh`, `doc_reminder.sh`, `tg_popup.sh`, `oom_protect.sh`).

### 1.2. Что войдёт в Workspace OS без изменений

| Компонент | Почему |
|---|---|
| **EventBus** (`scripts_01/event_bus.py`) | интеграция в 10+ модулей, publish/subscribe/unsubscribe, wildcard |
| **ContextManager** (`scripts_01/context_manager.py`) | сессии/чекпоинты/сообщения, SQLite, auto-checkpoint, EventBus-события |
| **MemoryEngine** (`scripts_01/memory_engine.py`) | 5 уровней, build_context, токен-бюджет, EventBus |
| **KnowledgeEngine + SemanticIndex + GraphIndex** | FTS5 + TF-IDF + LSA, auto_discover, граф связей |
| **Verifier** (`scripts_01/verifier.py`) | VerificationRule (6 типов проверок), VerifierStorage, DEFAULT_RULES, EventBus, shell-защита (v5.25.0) |
| **ScenarioEngine** (`freebuff_plugin_03/scenario_engine.py`) | 7+ сценариев, интеграция REST + MCP + Telegram |
| **Runtime Adapter Layer** (`freebuff_plugin_03/runtime/`) | RuntimeAdapter ABC, StdioMCPAdapter, HTTPMCPAdapter, RuntimeRegistry, provider YAML |
| **ModelGateway + SmartRouter** | провайдеры deepseek/gemini/ollama, capability-роутинг |
| **PluginAPI** (`scripts_01/plugin_api.py`) | PluginManifest, PluginRegistry, discover, lifecycle, EventBus |
| **MCP Server** (`scripts_01/mcp_server.py`) | 20 tools, prompts, resources (stdio; Vault-Bearer auth — отдельно на HTTP-слое `mcp_fastapi.py`) ⚠️ часть tools (`distributed_*`/`pulse_*`/`roles_*`) зарегистрирована, но **недоступна** — бэкенды утеряны (см. 0.1) |

### 1.3. Что придётся разработать с нуля

1. **Workspace-контейнер** (сущность + метаданные + настройки).
2. **Work Area** (как слой между Workspace и Project; можно эволюционно из категорий scan_projects).
3. **Team/RBAC/ACL** (roles-модуль восстановить, затем построить ACL поверх).
4. **Business Process Engine** (планировщик поверх EventBus + ScenarioEngine).
5. **Skills-реестр** и **структурированная Prompt Library** (сейчас pompts_11/ — набор файлов, не библиотека).
6. **Connector-каркас** (GitHub/Email/Drive/CRM/ERP/n8n/Make — единый ConnectorRegistry; сейчас только Telegram + MCP).

---

## 2. Каноническая архитектурная модель Workspace OS (уточнённая)

Модель из 023_02_kanonicheskaya_model_workspace_os.md проверена против кодовой базы. Уточнения отмечены `(уточнено)`.

```
Workspace  ← 🔴 НЕТ как сущности (нужен WorkspaceManager поверх существующих движков)
│
├── Work Areas  ← 🔴 НЕТ (уточнено: эволюция из category в scan_projects.py)
│
├── Projects  ← 🟡 scan_projects.py (SQLite projects) + MemoryLevel.PROJECT + KnowledgeEngine project:*
│
├── Resources  ← 🟡 runtime_05/providers/*.yaml (freebuff, claude_code, openclaw) + RuntimeRegistry
│                (уточнено: Resources = единый реестр runtime-провайдеров, моделей, сервисов)
│
├── Business Processes  ← 🔴 НЕТ (shell-скрипты не являются сущностью процесса)
│
├── Scenarios  ← ✅ ScenarioEngine (7+ сценариев, REST + MCP + TG)
│
├── Tasks  ← ✅ Orchestrator (Workflow/Step/ToolExecutor/StepValidator/DefaultPlanner)
│
├── Knowledge  ← ✅ KnowledgeEngine + SemanticIndex + GraphIndex (RAG 2.0 — 🔶 утерян)
│
├── Memory  ← ✅ MemoryEngine (5 уровней; VECTOR — 🔶 утерян)
│
├── Documentation  ← ✅ docs_10/ (core_02/plugin/vision/audits) + README + SPEC.md + BUFFY.md
│
├── Connectors  ← 🟡 Telegram (3 реализации!), MCP (client/server/bridge/ACP);
│                 GitHub/Email/Drive/CRM/ERP/n8n/Make — 🔴
│
├── AI Runtime  ← ✅ ModelGateway + SmartRouter (capability-роутинг) + PolicyEngine (выбор)
│
├── Plugins  ← ✅ PluginAPI + 4 плагина (hello_world, tg_messenger, system_monitor, knowledge_sync)
│
├── Event System  ← ✅ EventBus (in-process) + EventStore/Replay/Timeline/Audit (persistent)
│
├── Verification  ← ✅ Verifier (6 типов проверок) + PolicyEngine + MetricsEngine (VCR/SRG/CpVO/RRR/TTD)
│
└── Security  ← 🟡 Vault-Bearer auth (mcp_fastapi) + secret-scanner + verifier shell-guard;
                RBAC/ACL/Encryption/Plugin Trust — 🔴
```

### 2.1. Роль и связи ключевых сущностей

| Сущность | Роль в платформе | Текущая реализация |
|---|---|---|
| **Workspace** | корневой контейнер: пользователи, глобальные настройки, роли, безопасность, общая память, подключённые модели/сервисы | 🔴 нет (нужен `WorkspaceManager`) |
| **Work Area** | логическая область деятельности, группирует проекты/процессы/ресурсы | 🔴 нет (есть category в scan_projects) |
| **Project** | конкретная цель/продукт | 🟡 таблица `projects` в context.db + Memory + Knowledge |
| **Resource** | внешняя/внутренняя сущность, используемая проектами (модели, CLI-агенты, сервисы) | 🟡 RuntimeRegistry + providers YAML + ModelGateway |
| **Scenario** | переиспользуемая интеллектуальная последовательность действий | ✅ ScenarioEngine (md-файлы) |
| **Business Process** | долгоживущий автоматизированный процесс (публикации, отчёты, мониторинг) | 🔴 нет движка |
| **Task** | единица работы внутри процесса/сценария | ✅ Orchestrator Workflow/Step |
| **Knowledge** | любая база знаний, независимо от реализации | ✅ KnowledgeEngine (FTS5+TF-IDF+LSA) + GraphIndex |
| **Memory** | кратко/долговременная память системы | ✅ MemoryEngine (5 уровней) |
| **Connector** | адаптер к внешним системам | 🟡 Telegram + MCP (единого каркаса нет) |
| **AI Runtime** | подключаемый ресурс LLM | ✅ ModelGateway + SmartRouter + PolicyEngine |
| **Plugin** | переиспользуемый пакет возможностей | ✅ PluginAPI + PluginRegistry |
| **Event System** | шина событий + персистентный сторадж + replay | ✅ EventBus + EventStore/Replay/Timeline/Audit |
| **Verification** | объективная проверка результата (критерии, не мнение) | ✅ Verifier + MetricsEngine |
| **Security** | системный слой: secrets, RBAC, ACL, auth, audit, encryption | 🟡 Vault auth + scanner; остальное 🔴 |

---

## 3. Карта соответствия (реализация × готовность)

Статусы: ✅ полностью / 🟡 частично / 🔶 альтернативно или утеряно / 🔴 отсутствует / ⚠ дублируется

### 3.1. Workspace & Work Area & Project

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Workspace (сущность)** | 🔴 | нет класса | `grep class Workspace` → 0 | — | есть только константа `WORKSPACE` в модулях |
| **Work Area** | 🔴 | нет | `grep WorkArea` → 0 | — | ближайшее: категории в `scan_projects.py` (category: leviathan/telegram/ai/web/tool/infra/personal) |
| **Project Registry** | 🟡 | `scripts_01/scan_projects.py` | таблица `projects` в `data_13/context.db` (name/path/language/git_remote/category/status), upsert, `--rebuild`, `--status` | CLI + KnowledgeEngine + MemoryEngine | нет lifecycle (create/close/archive), нет связей с Work Area |
| **Project Discovery** | ✅ | `scan_projects()` + `detect_git_remote()` + `detect_language()` | `scripts_01/scan_projects.py:114` | запускается вручную | автоматическое сканирование есть, но не демонизировано |
| **Team (users/members/invites)** | 🔴 | нет | `grep invite/member` → только роли сообщений | — | нет ни одного объекта пользователя |
| **Permissions (RBAC/ACL)** | 🔴 | нет RBAC | `freebuff_plugin_03/policy/engine.py` — PolicyEngine (выбор runtime по capabilities, не RBAC) | PolicyEngine используется runtime-выбором | роли (roles.py) потеряны; после восстановления — фундамент для RBAC |

### 3.2. Runtime & AI

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Runtime Adapter Layer** | ✅ | `freebuff_plugin_03/runtime/adapter.py` | `RuntimeAdapter(ABC)`, `StdioMCPAdapter`, `HTTPMCPAdapter`; `registry.py`: `RuntimeRegistry`, `RuntimeCapabilityRegistry`, `discover()` | MCP tools `runtime_list/connect/disconnect/select/generate` в `scripts_01/mcp_server.py` | провайдеры: `runtime_05/providers/{freebuff,claude_code,openclaw***REMOVED***.yaml` |
| **AI Runtime (Model Gateway)** | ✅ | `scripts_01/model_gateway.py` | `ModelGateway` (deepseek/gemini/ollama/qwen, 30+ моделей, EventBus publish) | orchestrator, sdk_bridge, CLI | + `core_02/router.py`: `ModelCatalog`, `SmartRouter` (capability-роутинг) |
| **Runtime Permissions** | 🟡 | `freebuff_plugin_03/policy/engine.py` + `policy/rules.py` | `PolicyEngine`, `RuleEvaluator` (+MaxLatency/Exclude/RequiredFlags/MinConfidence), `freebuff_plugin_03/policy/config.py` | RuntimeCapabilityRegistry загружает scores из provider manifests | это capability-политики, не RBAC/ACL |

### 3.3. Context & Memory & Knowledge

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Context Manager** | ✅ | `scripts_01/context_manager.py` | `ContextManager`, `CheckpointType`, сессии/сообщения/чекпоинты SQLite, auto-checkpoint по сообщениям и токенам, EventBus `session.*/checkpoint.*` | freebuff_cli, stream_bridge, integrate_agent, auto_conspect, api.py | |
| **Context Builder** | ✅ | `scripts_01/context_builder.py` | `ContextBuilder` (токен-бюджет, включение памяти/задачи/changelog/сессии) | freebuff_cli (`builder = ContextBuilder(max_tokens=6000)`) | |
| **StreamBridge / Session** | ✅ | `scripts_01/stream_bridge.py`, `scripts_01/stream_session.py`, `scripts_01/session_utils.py`, `scripts_01/agent_context_bridge.py` | сессии, checkpoints, resume, auto-checkpoint каждые 10 сообщений | freebuff_cli `cmd_buffy()` | |
| **Memory Engine** | 🟡 | `scripts_01/memory_engine.py` | `MemoryEngine`, `MemoryLevel` (5 уровней: WORKING/PROJECT/KNOWLEDGE/PERSONAL/ARCHIVE), `ContentType`, `build_context` | scan_projects, seed_knowledge, graph_index, knowledge_engine, orchestrator, mcp_server | **VECTOR (6-й уровень) потерян** — `grep VECTOR` → 0; VectorBackend/chromadb отсутствует |
| **Knowledge Engine** | ✅ | `scripts_01/knowledge_engine.py` | `KnowledgeEngine` (FTS5 + TF-IDF + `SemanticIndex` LSA), `KnowledgeEngineStats`, EventBus `knowledge.*` | mcp_server (`knowledge_search`), seed_knowledge, scan_projects | |
| **Graph Index** | ✅ | `scripts_01/graph_index.py` | `GraphIndex`, `auto_discover()`, `auto_discover_from_memory()` | knowledge_engine (`graph_auto_discover`) | |
| **RAG 2.0** | 🔶 УТЕРЯН | `scripts_01/rag_engine.py` | pyc: `RAGEngine`, `RAGReport`, `FeatureVector`, `MAX_RERANK_CANDIDATES`, `rrf_merge` | был 3 MCP tools (`rag_search/rag_hybrid/rag_rerank`) | восстановим из pyc |
| **Knowledge Sync Plugin** | ✅ | `plugins_04/knowledge_sync/` | manifest.json + `__init__.py` (Memory→Knowledge sync, force_reindex) | EventBus `memory.stored` | |

### 3.4. Scenario & Process & Task

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Scenario Engine** | ✅ | `freebuff_plugin_03/scenario_engine.py` | `ScenarioEngine` (load/search/apply, 7+ .md сценариев в `freebuff_plugin_03/scenarios/`) | REST `/scenarios*` (api.py), MCP tools (freebuff_plugin_03/mcp_server.py), Telegram (tgbot.py) | категории: freelancing/agent/templates |
| **Business Process Engine** | 🔴 | нет класса | `grep business_process` → 0 | — | есть только shell-скрипты: `cron_conspect.sh`, `doc_reminder.sh`, `tg_popup.sh`, `oom_protect.sh`, `overlay_float.sh` |
| **Orchestrator (Tasks)** | ✅ | `scripts_01/orchestrator.py` | `Orchestrator`, `Workflow`, `Step`, `StepValidator`, `DefaultPlanner`, `ToolExecutor`, retry, EventBus `workflow.*/step.*` | MCP tools, CLI | параллельное выполнение шагов, DAG-зависимости |

### 3.5. Plugins & Skills & Prompts

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Plugin API** | ✅ | `scripts_01/plugin_api.py` | `PluginManifest`, `PluginRegistry`, `discover()`, lifecycle (load/enable/disable/unload), EventBus | 4 плагина: `plugins_04/{hello_world,tg_messenger,system_monitor,knowledge_sync***REMOVED***` | каждый с manifest.json |
| **Skills** | 🔴 | нет реестра | `grep class Skill` → 0 | — | ближайшее: сценарии (интеллектуальные последовательности) |
| **Prompt Library** | 🟡 | `pompts_11/*.md` (27 файлов) + `scripts_01/mcp_server.py` `_register_prompts()` | MCP prompts: `context_resume`, `knowledge_search`, `task_start` | mcp_server | набор файлов, не структурированная библиотека с метаданными |

### 3.6. Connectors & MCP

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Telegram** | ⚠ дубль | `scripts_01/telegram_bot.py` + `freebuff_plugin_03/tgbot.py` + `plugins_04/tg_messenger/` | 3 реализации: session-бот, scenario-бот, plugin | run скрипты `start_telegram_bot.sh`/`start_tgbot.sh` | нужна канонизация |
| **MCP Client** | ✅ | `freebuff_plugin_03/mcp_client.py` | `MCPClientBase`, `list_prompts()`, `_send_request` | bridge | |
| **MCP Server (stdio)** | ⚠ частично | `scripts_01/mcp_server.py` | 20 tools (memory/knowledge/context_12/task/runtime_05/bridge/bootstrap + `distributed_*`/`pulse_*`/`roles_*`), prompts, resources, EventBus `_publish` | основной инструментальный сервер | **`distributed_*`/`pulse_*`/`roles_*` — registered but unavailable:** lazy-аксессоры (`_get_distributed_coordinator()` и аналоги) вернут ошибку/None при отсутствии потерянных бэкендов (roles.py/project_pulse.py/distributed_agents.py) — до Этапа 0 |
| **MCP Server (plugin)** | ✅ | `freebuff_plugin_03/mcp_server.py` | `MCPServer` (scenario tools) | bootstrap extensions | |
| **MCP HTTP (FastAPI)** | ✅ | `scripts_01/mcp_fastapi.py` | REST endpoints + metrics dashboard + **Vault-Bearer auth** | HTTP-клиенты | auth: `_get_active_token()`, hvac, TTL cache, hmac.compare_digest |
| **Bridge Layer (MCP↔ACP)** | ✅ | `freebuff_plugin_03/bridge_layer.py` | `BridgeLayer`, stdio/http connect, RPC | mcp_server (bridge.*) | |
| **ACP Protocol** | ✅ | `freebuff_plugin_03/acp_protocol.py` | `ACP_DISCOVER`, discover/request/response | distributed (утрачен), bridge | |
| **GitHub/Email/Drive/CRM/ERP/n8n/Make** | 🔴 | нет | — | — | git remote только как метаданные в scan_projects |

### 3.7. Verification & Quality

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **Verifier** | ✅ | `scripts_01/verifier.py` | `VerificationRule` (6 типов: file_exists/content_match/pytest/shell/sqlite/http), `VerifierStorage`, `DEFAULT_RULES`, EventBus, подписка `task.claimed` | MCP tools, CLI `verify/rules` | **v5.25.0:** произвольный shell-исполнение закрыт (pytest через argv без shell=True) |
| **Policy Engine** | ✅ | `freebuff_plugin_03/policy/engine.py` | `PolicyEngine` (capability-based выбор runtime) | RuntimeCapabilityRegistry | не путать с RBAC |
| **Metrics Engine** | ✅ (восстановлен) | `scripts_01/metrics.py` | `MetricsEngine` (VCR/SRG/CpVO/RRR/TTD + Health Score), `MetricsReport`, `MetricResult`, EventBus `metrics.report` | HTTP `/metrics/*`, dashboard | восстановлен из pyc, 57/57 тестов mcp_fastapi |
| **Audit Log** | 🟡 | `freebuff_plugin_03/event/audit.py` | событийный аудит | event-слой | не полноценный Quality Gate pipeline |

### 3.8. Events & Security & Docs

| Компонент | Статус | Реализация | Доказательства | Используется | Замечания |
|---|---|---|---|---|---|
| **EventBus** | ✅ | `scripts_01/event_bus.py` | `EventBus` (publish/subscribe/unsubscribe, wildcard `*`), `Event`, `Subscription` | интегрирован в 10+ модулей (memory, knowledge, orchestrator, verifier, metrics, mcp_server, plugin_api, context_manager) | |
| **EventStore / Replay / Timeline** | ✅ | `freebuff_plugin_03/event/` | `store.py`: `EventStore` (SQLite schema.sql); `replay.py`: `ReplayEngine`; `timeline.py`: `TimelineEngine`; `pulse.py` | event-слой | |
| **Secrets (Vault)** | 🟡 | `scripts_01/mcp_fastapi.py` + `projects_17/diet_platform/building_blocks/vault_integration.py` | hvac client, `FREEBUFF_VAULT_ADDR/TOKEN/KEY`, TTL-кеш токена; VaultClient в diet_platform (127.0.0.1:8400) | HTTP auth | встроенного vault-хранилища нет — внешняя интеграция |
| **Auth (Bearer)** | ✅ | `scripts_01/mcp_fastapi.py` | `auth_middleware` с `hmac.compare_digest`, Vault→env fallback | /mcp endpoints | |
| **Secret Scanner** | ✅ | `scripts_01/scanner.py` | сканирует credentials/token/vault-паттерны | CLI | |
| **Encryption** | 🔴 | нет в платформе | (есть Fernet только в `projects_17/realtor_automation/.../security.py`) | — | |
| **Prompt Injection Protection** | 🟡 | `scripts_01/verifier.py` + `freebuff_plugin_03/policy/` | shell-guard (v5.25.0), capability-политики | verifier | системного PII-фильтра нет |
| **Plugin Trust** | 🔴 | нет | — | — | манифесты не подписываются |
| **Documentation** | ✅ | `docs_10/` (core: 20+ спецификаций, plugin, vision, audits) + README + SPEC.md + BUFFY.md + BUFFY_PROJECT.md + CHANGELOG | docs_10/core/*_SPECIFICATION.md (EventBus, Memory, Context, Knowledge, Graph, Orchestrator, ModelGateway, PluginAPI, ToolRuntime, NodeMesh, SessionMesh...) | — | |
| **CoWork (Presence/Collab/Distributed)** | 🔶 УТЕРЯН | pyc: presence/collaboration/distributed_agents | `PresenceEngine` (heartbeat, prune), `CollaborationEngine` (sessions_15/messages/participants), `AgentMesh`/`TaskDistributor`/`DistributedCoordinator` | БД presence.db/collaboration.db существуют | восстановить из pyc — фундамент CoWork-платформы |

---

## 4. Карта архитектурных дублирований

### 4.1. Роутеры (3 шт.) — ОБЪЕДИНИТЬ

| Файл | Класс | Роль |
|---|---|---|
| `core_02/router.py` | `SmartRouter`, `ModelCatalog` | capability-выбор модели |
| `freebuff_plugin_03/router.py` | `IntentRouter` | маршрут «простое→local, сложное→freebuff» |
| `scripts_01/sdk_bridge.py` | `SmartRouterAdapter` | адаптер роутинга для SDK |

**Рекомендация:** единый `Router` в `core_02/`, где IntentRouter и SmartRouterAdapter — тонкие адаптеры. Дублируется сама идея «выбери, что выполнит запрос».

### 4.2. Telegram (3 реализации) — КАНОНИЗИРОВАТЬ

- `scripts_01/telegram_bot.py` — session-бот (ContextManager, чекпоинты).
- `freebuff_plugin_03/tgbot.py` — scenario-бот (inline keyboards, /scenarios).
- `plugins_04/tg_messenger/` — plugin (форвардинг событий, очередь).

**Рекомендация:** один канонический `TelegramConnector`; остальные два — тонкие сценарии поверх него (или обратно: plugin-реализация становится каноном, а скрипты — обёртками).

### 4.3. MCP-серверы (3 точки входа) — РАЗГРАНИЧИТЬ

- `scripts_01/mcp_server.py` — основной инструментальный сервер (stdio, 20 tools; часть — с потерянными бэкендами до Этапа 0).
- `freebuff_plugin_03/mcp_server.py` — plugin-сервер сценариев.
- `scripts_01/mcp_fastapi.py` — HTTP-слой (с auth).

**Рекомендация:** оставить как есть по ответственности (инструменты vs сценарии vs HTTP), но зафиксировать единый ToolRegistry, чтобы наборы tools не расходились.

### 4.4. Event-слои (in-process + persistent) — ОСТАВИТЬ, задокументировать

- `scripts_01/event_bus.py` — in-process шина.
- `freebuff_plugin_03/event/store.py` — персистентный EventStore + Replay + Timeline.

Это layering, а не дубль: шина — транспорт, store — история. Но `freebuff_plugin_03/event/pulse.py` (существующий) и `scripts_01/project_pulse.py` (утерянный) пересекаются по концепции ленты событий — **объединить при восстановлении**.

### 4.5. Memory/PROJECT vs Knowledge vs Context (данные) — РАЗГРАНИЧИТЬ

`scan_projects.py` пишет один и тот же проект в 3 хранилища: SQLite `projects` + KnowledgeEngine `project:*` + MemoryEngine `PROJECT`. Это не дубль кода, но **дубль данных без единого источника истины**. Рекомендация: `projects` в context.db = source of truth, Memory/Knowledge — производные индексы.

### 4.6. Верификация (Verifier + PolicyEngine + Metrics) — РАЗНЫЕ ЦЕЛИ, оставить

- Verifier — объективная проверка результата (критерии).
- PolicyEngine — выбор runtime по capabilities.
- MetricsEngine — метрики качества (VCR/SRG/CpVO/RRR/TTD).

Пересечение минимально; это 3 разных домена. Оставить независимыми.

---

## 5. Карта пробелов (по факту кода, не предположительно)

| Пробел | Доказательство | Приоритет |
|---|---|---|
| **Workspace-контейнер** | нет класса Workspace, нет глобальных настроек/ролей/безопасности | P0 |
| **Work Area** | нет; category в scan_projects — единственный след | P0 |
| **Team (users/members/invites)** | grep → 0 объектов пользователя | P1 |
| **RBAC/ACL** | PolicyEngine — capability-политики, не RBAC | P1 |
| **Business Process Engine** | нет; только shell-скрипты | P1 |
| **Skills-реестр** | grep class Skill → 0 | P2 |
| **Структурированная Prompt Library** | pompts_11/ — файлы без метаданных/версий | P2 |
| **Connectors: GitHub/Email/Drive/CRM/ERP/n8n/Make** | нет файлов | P2 |
| **Encryption (платформенный)** | только в projects_17/realtor_automation | P1 |
| **Plugin Trust (подпись манифестов)** | нет | P2 |
| **Prompt Injection Protection (системный)** | частично verifier shell-guard | P1 |
| **VECTOR-уровень памяти + VectorBackend** | `grep VECTOR memory_engine.py` → 0 (потерян) | P1 (восстановление) |
| **7 модулей CoWork/Roles/RAG/Pulse/Notification** | pyc есть, исходников нет | P0 (восстановление) |
| **13 тест-файлов** | на диске отсутствуют | P0 (восстановление) |

---

## 6. План эволюции (без переписывания, с максимальным реюзом)

### Этап 0 — Восстановление целостности (предусловие) · 0 новых сущностей

Восстановить 7 модулей + 13 тестов из байткода по проверенной методологии metrics.py:
1. Интроспекция pyc (сигнатуры, константы, dis-дамп).
2. Поведенческие пробы на живых БД (roles.db/presence.db/collaboration.db/project_pulse.db).
3. Реконструкция исходника, py_compile, поведенческое сравнение pyc↔новый модуль.
4. Восстановление тестов, прогон, коммит.
5. Вернуть `MemoryLevel.VECTOR` + VectorBackend: **если** в `scripts_01/__pycache__/` найдётся устаревший pyc memory_engine с VECTOR (текущий файл на диске — 5 уровней; pyc мог быть скомпилирован уже после потери) — реконструировать из него; **иначе** — реализовать заново по CHANGELOG v5.12.0 (chromadb, `vector_search`), это признано пробелом P1.

**Результат:** кодовое состояние снова соответствует CHANGELOG v5.24.

### Этап 1 — Workspace-контейнер (1 новая сущность)

`WorkspaceManager` — лёгкий слой поверх существующих движков:
- метаданные workspace в `data_13/workspace.db` (имя, настройки, users, roles, connected resources),
- фабрика/прокси к ContextManager, MemoryEngine, KnowledgeEngine, EventBus, ModelGateway,
- `workspace.yaml` как конфиг-источник истины (переиспользовать паттерн provider manifests).

### Этап 2 — Work Area (1 новая сущность, эволюция)

`WorkAreaRegistry`:
- эволюция `category` из scan_projects → таблица `work_areas` в context.db,
- FK: projects.work_area_id → work_areas.id,
- MCP tools: `workarea_list/create/assign`.

### Этап 3 — Консолидация дублей (0 новых сущностей)

- Единый Router в core_02/ (IntentRouter/SmartRouterAdapter — адаптеры).
- Канонизация Telegram: один канон, два — обёртки.
- source-of-truth для проектов (context.db), Memory/Knowledge — производные.

### Этап 4 — Security-слой (2 сущности)

- **RBAC**: поверх восстановленного RoleEngine (роль→capabilities) добавить ACL (субъект→объект→действие) — таблицы `acl` в workspace.db.
- **SecretsVaultService**: обёртка над hvac (Vault) как единый интерфейс для всех модулей (сейчас только mcp_fastapi + diet_platform).
- Plugin Trust: подпись manifest.json (ключ workspace, проверка при load).

### Этап 5 — Business Process Engine (1 новая сущность)

`ProcessEngine`:
- переиспользует EventBus (триггеры), ScenarioEngine (шаги), Orchestrator (tasks),
- cron-подобный планировщик поверх существующих shell-скриптов (cron_conspect/doc_reminder/tg_popup),
- таблица `processes` в context.db, MCP tools `process_start/list/stop`.

### Этап 6 — Connector-каркас (1 новая сущность)

`ConnectorRegistry` (по образцу PluginRegistry):
- адаптеры: Telegram (канон), GitHub, Email, Drive, n8n/Make (webhook),
- единый интерфейс `Connector(manifest, connect, disconnect, send)`.

### Этап 7 — Skills + Prompt Library (1 новая сущность)

- `SkillRegistry` по образцу PluginRegistry (manifest: triggers, uses_scenarios, uses_verifier),
- Prompt Library = структурированная версия `pompts_11/` (метаданные, версии, категории) с MCP tools `prompt_get/search`.

### Этап 8 — RAG 2.0 + VECTOR (восстановление + интеграция)

- восстановленный RAGEngine (RRF, rerank) подключить к KnowledgeEngine как слой ранжирования,
- восстановленный VECTOR-уровень (chromadb VectorBackend) как 6-й уровень памяти.

---

## 7. Итоговая матрица «реальность»

| Состояние | Компоненты |
|---|---|
| ✅ Войдут в Workspace OS без изменений | EventBus, ContextManager, ContextBuilder, MemoryEngine, KnowledgeEngine, SemanticIndex, GraphIndex, Verifier, MetricsEngine, ScenarioEngine, PluginAPI, RuntimeRegistry/Adapters, ModelGateway, SmartRouter, Orchestrator, EventStore/Replay/Timeline, Vault-Bearer auth, Documentation |
| ⚠️ Войдут после Этапа 0 (восстановление бэкендов) | MCP Server (`distributed_*`/`pulse_*`/`roles_*` tools сломаны) |
| 🟡 Потребуют объединения/доработки | роутеры (3), Telegram (3), MCP-точки входа (3), scan_projects→ProjectRegistry, prompt-библиотека, PolicyEngine→permissions |
| 🔶 Восстановить из pyc (существовали, утеряны) | RoleEngine, PresenceEngine, CollaborationEngine, DistributedCoordinator, RAGEngine, ProjectPulse, notification, MemoryLevel.VECTOR (восстановить/реализовать заново) + 13 тестов |
| 🔴 Разработать с нуля | Workspace-контейнер, Work Area, Team/RBAC/ACL, Business Process Engine, Skills-реестр, ConnectorRegistry (GitHub/Email/Drive/...), Encryption, Plugin Trust |

---

*Отчёт сформирован по фактам кодовой базы на 2026-07-31 (HEAD `4f91c29`). Полные доказательства по каждому домену: пути файлов, классы, строки — в разделе 3. Все утверждения о «существует» проверены на диске; все утверждения о «потеряно» проверены через `git log --all`, `git check-ignore` и загрузку pyc.*
