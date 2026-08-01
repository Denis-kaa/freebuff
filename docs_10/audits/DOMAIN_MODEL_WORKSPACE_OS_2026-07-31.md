# Архитектурное исследование №2: Доменная модель Workspace OS

**Дата:** 2026-07-31
**Источник задачи:** `pompts_11/024_02_domain_model_workspace_os.md`
**Роль:** Principal Software Architect + Enterprise Architect + DDD Researcher
**Принцип:** «Максимально использовать уже существующую архитектуру. Новые сущности допускаются только тогда, когда доказано, что аналогов в текущей системе действительно нет.»
**Метод:** сверка полной кодовой базы (все 7 потерянных модулей восстановлены: `753e3f4`, `3be0bf5`) с доменной моделью Workspace OS. Каждое утверждение — с путём к файлу, классом/функцией и местом интеграции.

---

## 0. КОНТЕКСТ: чем №2 отличается от №1

Исследование №1 (`docs_10/audits/ARCHITECTURE_WORKSPACE_OS_2026-07-31.md`, promt23) проводилось на **неполной** кодовой базе: 7 модулей CoWork/Roles/RAG/Pulse/Notification + metrics были утеряны в инциденте `git stash drop` и помечались статусом 🔶 УТЕРЯН.

Исследование №2 (promt24) выполняется **после Этапа 0** — полного восстановления:

| Было (№1) | Стало (№2) |
|---|---|
| 7 модулей 🔶 утеряны | ✅ восстановлены из тест-байткода (`753e3f4`) |
| MCP-интеграция сломана (`distributed_*`/`pulse_*`/`roles_*` registered but unavailable) | ✅ 27 инструментов работают (51 всего в `scripts_01/mcp_server.py`) |
| metrics без тестов | ✅ восстановлен (`4f91c29`), 57/57 тестов |
| 385/385 pyc-тестов — план | ✅ 385/385 PASS (evidence: `docs_10/audits/evidence/RECOVERY_7_MODULES_TEST_RUN_2026-07-31.txt`) |

**Новое открытие №2 (в ходе сверки):** 3 плагина (`knowledge_sync`, `system_monitor`, `tg_messenger`) **тоже утеряны** в том же инциденте — на диске только `hello_world/` (единственный закоммиченный), остальные существуют только как pyc в `plugins_04/*/__pycache__/__init__.cpython-314.pyc` (проверено: загружаются, экспортируют `KnowledgeSyncPlugin`, `SystemMonitorPlugin`, `TelegramMessengerPlugin`). Восстановимы той же методологией. Также: `_main_with_notification()` из CHANGELOG v5.24.0 в `freebuff_cli.py` **отсутствует** (grep → 0) — интеграция Notification ↔ CLI потеряна. Это учтено в разделах 3, 5, 8.

**Фокус №2 — не «что реализовано» (это сделано в №1), а ДОМЕННАЯ МОДЕЛЬ:** какие сущности существуют, какие связи между ними уже проведены, каких связей нет, где дубли, как минимумом изменений превратить FreeBuff в Workspace OS.

---

## 1. Executive Summary

### 1.1. Главный вывод

**FreeBuff уже реализует ~80% доменной модели Workspace OS по сущностям, но ~40% связей между ними не проведены.** Сущности существуют и работают: Workspace-подобные слои (Workspace meta), Project, Scenario, Task, Knowledge, Memory, Resource (Runtime), Plugins, Events, Verification. Отсутствуют как *доменные сущности*: **Work Area**, **Business Process**, **Resource как первичная сущность**, **Team/User**; как *связи*: многие связи «сущность ↔ сущность» реализованы только через EventBus (развязано), но не через явные foreign keys или граф.

### 1.2. Ключевые цифры полной базы

- `scripts_01/` — 44 файла, 25 541 строка; `freebuff_plugin_03/` — bootstrap/event/policy/runtime_05/scenarios + api/bridge/router/wrapper; `core_02/` — interfaces + router; `plugins_04/` — 1 на диске (hello_world) + 3 pyc-only (knowledge_sync/system_monitor/tg_messenger).
- 7 SQLite БД в `data_13/`: context, verifier, metrics, roles, presence, collaboration, project_pulse.
- 2 MCP-сервера (`scripts_01/mcp_server.py` — 51 инструмент; `freebuff_plugin_03/mcp_server.py` — event/scenario tools), 1 HTTP-слой (`mcp_fastapi.py`), 1 REST API (`freebuff_plugin_03/api.py`).
- 25+ событий EventBus; 29 промпт-файлов; 12 сценариев; 3 runtime-провайдера.

### 1.3. Что уже является фундаментом (входит без изменений)

EventBus, EventStore/Replay/Timeline/Audit, ContextManager, MemoryEngine (5 уровней), KnowledgeEngine (FTS5+TF-IDF+LSA), GraphIndex, Verifier, MetricsEngine, ScenarioEngine, PluginAPI (+ hello_world на диске; 3 плагина — pyc-only), RuntimeRegistry + Adapters, ModelGateway + SmartRouter, PolicyEngine, Orchestrator, восстановленные RoleEngine/PresenceEngine/CollaborationEngine/DistributedCoordinator/RAGEngine/ProjectPulse/notification.

### 1.4. Что действительно отсутствует (по факту кода)

1. **Work Area** — доменной сущности нет; единственный след — `category` в `scan_projects.py`.
2. **Business Process** — долгоживущие процессы реализованы только shell-скриптами, не сущностью.
3. **Resource как доменная сущность** — сейчас это RuntimeRegistry + provider YAML + ModelGateway; нет единой сущности «ресурс», привязываемой к проектам/work areas.
4. **User/Team/Invite** — ни одного объекта пользователя.
5. **RBAC/ACL** — PolicyEngine — capability-политики, не RBAC.

---

## 2. Каноническая доменная модель Workspace OS (проверена против кода)

```
Workspace (корень) — 🟡 нет класса Workspace, есть WORKSPACE-константы в модулях;
                     ближайшее: freebuff_cli + bootstrap + data_13/*.db (единая точка — workspace root)
│
├── Work Areas        — 🔴 нет сущности; category в scan_projects (leviathan/telegram/ai/web/tool/infra/personal)
│
├── Projects          — 🟡 scan_projects.py (таблица projects в context.db: name/path/language/git_remote/category/status)
│
├── Resources         — 🟡 RuntimeRegistry + providers YAML (freebuff/claude_code/openclaw) + ModelGateway;
│                        нет единой Resource-сущности с FK на проекты
│
├── Business Processes— 🔴 нет движка; shell-скрипты (cron_conspect.sh, doc_reminder.sh, tg_popup.sh, oom_protect.sh)
│
├── Scenarios         — ✅ ScenarioEngine (12 .md сценариев, REST+MCP+TG)
│
├── Tasks             — ✅ Orchestrator (Workflow/Step/DefaultPlanner/ToolExecutor) + DistributedCoordinator
│
├── Knowledge         — ✅ KnowledgeEngine + SemanticIndex + GraphIndex + RAGEngine (восстановлен)
│
├── Memory            — ✅ MemoryEngine (5 уровней) + ContextManager (session/checkpoint)
│
├── Documentation     — ✅ docs_10/ (20+ core-спецификаций, audits, ops, plugin, vision) + pompts_11/ (29 файлов)
│
├── Connectors        — 🟡 Telegram (3 реализации), MCP (client/server/bridge/ACP), REST;
│                        GitHub/Email/Drive/CRM/ERP/n8n/Make — 🔴
│
├── AI Runtime        — ✅ ModelGateway (deepseek/gemini/ollama/qwen) + SmartRouter + PolicyEngine
│
├── Plugins           — 🟡 PluginAPI ✅; 1 плагин на диске (hello_world), 3 pyc-only (восстановимы)
│
├── Event System      — ✅ EventBus (in-process) + EventStore/Replay/Timeline/Audit/Pulse (persistent)
│
├── Verification      — ✅ Verifier (6 типов проверок) + MetricsEngine (VCR/SRG/CpVO/RRR/TTD) + PolicyEngine
│
└── Security          — 🟡 Vault-Bearer auth (mcp_fastapi), secret-scanner, verifier shell-guard;
                         RBAC/ACL/Encryption/Plugin Trust — 🔴
```

**Уточнение модели:** концептуальная модель promt24 почти полностью подтверждается. Единственное расхождение — **Scenario ↔ Business Process** не образуют жёсткой иерархии в коде (нет ни того, ни другого уровня для сравнения); **Resources** в коде распылены на 3 слоя (RuntimeRegistry, ModelGateway, provider YAML) — в модели они должны стать единой сущностью.

---

## 3. Карта существующих сущностей

### 3.1. Доменные сущности (существующие)

| Сущность | Реализация | Класс/функция | Доказательство | Статус |
|---|---|---|---|---|
| **Session** | `scripts_01/context_manager.py` | `ContextManager`, `SessionSnapshot`, `SessionStatus`, `CheckpointType` | сессии/сообщения/чекпоинты, auto-checkpoint | ✅ |
| **MemoryEntry** | `scripts_01/memory_engine.py` | `MemoryEntry`, `MemoryLevel` (5), `ContentType` | build_context, токен-бюджет | ✅ |
| **KnowledgeDocument** | `scripts_01/knowledge_engine.py` | `Document`, `FtsIndex`, `TfidfIndex`, `SemanticIndex` | FTS5+TF-IDF+LSA | ✅ |
| **GraphNode/Edge** | `scripts_01/graph_index.py` | `Node`, `Edge`, `PathResult`, `GraphStats` | auto_discover | ✅ |
| **RAGResult/Report** | `scripts_01/rag_engine.py` | `RAGResult`, `RAGReport`, `FeatureVector`, `RAGEngine` | rrf_merge, rerank, 5 режимов поиска | ✅ (восстановлен) |
| **Project** | `scripts_01/scan_projects.py` | `scan_projects()`, `detect_git_remote()`, `detect_language()` | таблица projects в context.db | 🟡 |
| **Scenario** | `freebuff_plugin_03/scenario_engine.py` | `Scenario`, `ScenarioEngine` | 12 сценариев, load/search/apply | ✅ |
| **Task/Workflow/Step** | `scripts_01/orchestrator.py` | `Workflow`, `Step`, `DefaultPlanner`, `ToolExecutor` | DAG, retry, параллельность | ✅ |
| **VerificationRule/Result** | `scripts_01/verifier.py` | `VerificationRule`, `VerificationResult`, `Verifier` | 6 типов проверок, DEFAULT_RULES | ✅ |
| **MetricResult/Report** | `scripts_01/metrics.py` | `MetricResult`, `MetricsReport`, `MetricsEngine` | VCR/SRG/CpVO/RRR/TTD, Health Score | ✅ (восстановлен) |
| **Runtime** | `freebuff_plugin_03/runtime/` | `RuntimeAdapter(ABC)`, `StdioMCPAdapter`, `HTTPMCPAdapter`, `RuntimeRegistry` | providers YAML | ✅ |
| **Model** | `scripts_01/model_gateway.py` | `ModelGateway`, `BaseProvider`, `OpenAICompatibleProvider`, `GeminiProvider`, `OllamaProvider` | capability-роутинг | ✅ |
| **Plugin** | `scripts_01/plugin_api.py` | `PluginManifest`, `PluginRegistry`, `BasePlugin` | 1 плагин на диске (`hello_world`); 3 плагина 🔶 утеряны (pyc: `KnowledgeSyncPlugin`, `SystemMonitorPlugin`, `TelegramMessengerPlugin` — загружаются) | 🟡 (API ✅, 3/4 плагина 🔶) |
| **Event** | `scripts_01/event_bus.py` | `Event`, `EventBus`, `Subscription` | 25+ типов | ✅ |
| **EventEntry/Timeline/Audit** | `freebuff_plugin_03/event/` | `EventStore`, `EventReplay`, `TimelineEngine`, `AuditEngine`, `PulseEngine` | schema.sql, replay | ✅ |
| **Role** | `scripts_01/roles.py` | `RoleDefinition`, `AgentRole`, `RoleEngine` | 6 стандартных ролей | ✅ (восстановлен) |
| **AgentPresence** | `scripts_01/presence.py` | `AgentPresence`, `PresenceHistoryEntry`, `PresenceEngine` | heartbeat, prune | ✅ (восстановлен) |
| **CollabSession/Message** | `scripts_01/collaboration.py` | `CollaborationSession`, `CollabMessage`, `Participant`, `CollaborationEngine` | 6 типов сообщений (text/system/task/file/decision/code) | ✅ (восстановлен) |
| **AgentNode/AgentTask** | `scripts_01/distributed_agents.py` | `AgentNode`, `AgentTask`, `AgentMesh`, `TaskDistributor`, `DistributedCoordinator` | 3 стратегии, DAG-workflow | ✅ (восстановлен) |
| **PulseEntry** | `scripts_01/project_pulse.py` | `PulseEntry`, `ProjectPulse` | 15+ типов событий, git-scan | ✅ (восстановлен) |
| **Notification** | `scripts_01/notification.py` | `notify()`, `notify_task_complete()`, `notify_error()` | 3-канальный каскад; ⚠ потребителей вне тестов нет, CLI-обёртка `_main_with_notification` потеряна | 🟡 (модуль ✅, интеграция 🔴) |

### 3.2. Доменные сущности (отсутствующие)

| Сущность | Доказательство отсутствия | Ближайший аналог |
|---|---|---|
| **Workspace (сущность)** | `grep class Workspace` → 0; есть только `WORKSPACE = Path(__file__).parent.parent` константы | workspace root как неявный контейнер |
| **Work Area** | `grep WorkArea` → 0 | `category` в scan_projects |
| **User** | `grep class User` в scripts_01/freebuff_plugin → 0 | нет (только участники collab-сессий) |
| **Team/Invite** | нет | участники collab + присутствие |
| **Business Process** | `grep business_process` → 0 | shell-скрипты + Orchestrator |
| **Resource (единая)** | нет класса Resource | RuntimeRegistry + ModelGateway |

---

## 4. Карта существующих связей

### 4.1. Явные связи (imports / интеграции)

| Связь | Как реализована | Файл:строка |
|---|---|---|
| **Session ↔ Memory** | `ContextBuilder` собирает memory в контекст | `context_builder.py:31` |
| **Session ↔ Stream** | `StreamBridge` создаёт сессию, `buffy_stream_logger` логирует | `stream_bridge.py:41-58` |
| **Project ↔ Knowledge+Memory** | `scan_projects` пишет в KnowledgeEngine + MemoryEngine | `scan_projects.py:241,288` |
| **Knowledge ↔ Graph** | `knowledge_engine` вызывает `GraphIndex.auto_discover` | `knowledge_engine.py:48` |
| **Knowledge ↔ RAG** | `rag_engine` импортирует `KnowledgeEngine` (semantic mode) | `rag_engine.py:172` |
| **Memory ↔ Knowledge** | плагин `knowledge_sync` на событие `memory.stored` (исходник 🔶 pyc-only — плагин утерян, см. 8.6) | `plugins_04/knowledge_sync/__pycache__/__init__.cpython-314.pyc` |
| **Task ↔ Memory/Knowledge** | `Orchestrator` подключает MemoryEngine + KnowledgeEngine | `orchestrator.py:244,271` |
| **Task ↔ Verifier** | `Orchestrator._verify_step()` + подписка `task.claimed` | `orchestrator.py`, `verifier.py:955` |
| **Task ↔ Distributed** | `DistributedCoordinator` исполняет задачи, `execute_agent_task()` | `distributed_agents.py:483+` |
| **Runtime ↔ Policy** | `RuntimeCapabilityRegistry` грузит scores из provider manifests, `PolicyEngine` выбирает | `runtime_05/registry.py:657`, `policy/engine.py` |
| **Runtime ↔ MCP** | 5 MCP tools: runtime_list/connect/disconnect/select/generate | `mcp_server.py:357` |
| **Scenario ↔ REST/MCP/TG** | `api.py` /scenarios*, `mcp_server.py` apply_scenario, `tgbot.py` /scenarios | `freebuff_plugin_03/api.py:224` |
| **EventBus ↔ 10+ модулей** | memory/knowledge/orchestrator/verifier/metrics/mcp_server/plugin_api/context_manager/collaboration/presence/distributed | событие `Event` импортируется в каждом |
| **Collab ↔ Presence** | `collaboration.py` интегрируется с PresenceEngine (роли → metadata) | `collaboration.py:32+` |
| **Roles ↔ Presence/Collab** | роли синхронизируются в metadata агента; project-роли → collab-роли | `roles.py`, `collaboration.py` |
| **Distributed ↔ Bridge (мониторинг)** | `DistributedCoordinator._monitor_loop` проверяет статус агентов **через Bridge Layer**, а не через presence (CHANGELOG v5.14.0) | `distributed_agents.py` |
| **Pulse ↔ EventBus+Git** | `ProjectPulse` подписан на `*`, сканирует git commit/file | `project_pulse.py:118+` |
| **Metrics ↔ Context+Verifier DB** | `MetricsEngine` читает action_verifications + verification_results | `metrics.py:124+` |
| **MCP Server ↔ все движки** | 51 инструмент через lazy accessors (`_get_*_engine`) | `mcp_server.py:409-473` |

### 4.2. Связи через EventBus (развязанные)

| Событие | Издатель | Подписчики |
|---|---|---|
| `memory.stored` | MemoryEngine | knowledge_sync plugin, event_subscribers |
| `task.claimed/verified` | Orchestrator/Verifier | event_subscribers, metrics |
| `workflow.*`, `step.*` | Orchestrator | mcp_server, event store |
| `collab.created/joined/message` | CollaborationEngine | mcp_server, presence |
| `presence.online/offline/heartbeat` | PresenceEngine | collaboration (интеграция с PresenceEngine по CHANGELOG v5.18.0; механизм — вне подписки на эти события) |
| `distributed.agent_*`, `distributed.task_*` | DistributedCoordinator | mcp_server |
| `session.*`, `checkpoint.created` | ContextManager | mcp_server, bootstrap |
| `metrics.report` | MetricsEngine | event store, dashboard |

### 4.3. Связи через БД (SQLite)

| Связь | Таблицы | Файл |
|---|---|---|
| Session → messages/checkpoints | `sessions`, `messages`, `checkpoints` | `context.db` |
| Session → decisions/invariants | `arch_decisions`, `invariants` | `context.db` |
| Session → verifications | `action_verifications` | `context.db` |
| Project → sessions | `projects` | `context.db` |
| Verifier → results | `verification_rules`, `verification_results` | `verifier.db` |
| Metrics → snapshots/reports | `metric_snapshots`, `reports` | `metrics.db` |
| Roles → assignments | `roles`, `role_assignments` | `roles.db` |
| Presence → history | `presence`, `presence_history` | `presence.db` |
| Collab → sessions_15/messages/participants | `collab_sessions`, `collab_messages`, `collab_participants` | `collaboration.db` |
| Pulse → entries | `pulse_entries` | `project_pulse.db` |

---

## 5. Карта отсутствующих связей

| Связь | Текущее состояние | Что нужно (минимум) |
|---|---|---|
| **Workspace → всё** | нет сущности Workspace; модули знают только workspace root | WorkspaceManager (метаданные + фабрика прокси) |
| **Work Area → Project** | category в projects, но не FK, нет таблицы work_areas | таблица `work_areas` + FK `projects.work_area_id` |
| **Project → Resource** | runtime-провайдеры не привязаны к проектам | таблица `project_resources` (project_id ↔ resource_id) |
| **Project ↔ Scenario** | сценарии глобальны, не привязаны к проектам | поле `project_id` в сценарии / категория |
| **Scenario ↔ Business Process** | нет ни уровня процессов, ни связи | ProcessEngine, вызывающий ScenarioEngine |
| **User → Role → Permission** | roles есть (агентские), users нет; RBAC нет | таблицы `users`, `acl` в workspace.db |
| **Plugin ↔ Permission** | плагины грузятся без проверки прав | Plugin Trust: подпись manifest, проверка при load |
| **Knowledge ↔ Project (явная)** | только через префикс `project:*` в памяти | FK или метаданные проекта в Document |
| **Event ↔ Audit (полный)** | EventStore есть, но не все модули пишут в него | событийный адаптер: EventBus → EventStore мост |
| **Notification ↔ CLI** | `_main_with_notification()` из CHANGELOG v5.24.0 отсутствует в `freebuff_cli.py` (grep → 0) — уведомления не доходят при реальных задачах | восстановить обёртку CLI (по CHANGELOG) |
| **Notification ↔ потребители** | `notify_task_complete()`/`notify_error()` нигде вне тестов не вызываются | подключить в CLI/оркестратор/башер-обёртки |
| **Plugins (3 шт.) ↔ диск** | knowledge_sync/system_monitor/tg_messenger только в pyc | восстановить из байткода (методология Этапа 0) |

---

## 6. Карта архитектурных дублирований (обновлено после восстановления)

| Дубль | Участники | Рекомендация |
|---|---|---|
| **Роутеры (3)** | `core_02/router.py` (SmartRouter), `freebuff_plugin_03/router.py` (IntentRouter), `scripts_01/sdk_bridge.py` (SmartRouterAdapter) | единый `core_02/Router`; остальные — адаптеры |
| **Telegram (3)** | `scripts_01/telegram_bot.py`, `freebuff_plugin_03/tgbot.py`, `plugins_04/tg_messenger/` | один канонический TelegramConnector |
| **MCP-точки входа (3)** | `scripts_01/mcp_server.py`, `freebuff_plugin_03/mcp_server.py`, `scripts_01/mcp_fastapi.py` | зафиксировать единый ToolRegistry; разграничить ответственность |
| **Event-ленты (2)** | `freebuff_plugin_03/event/pulse.py` (PulseEngine) vs `scripts_01/project_pulse.py` (ProjectPulse) | объединить: ProjectPulse — доменная лента, PulseEngine — подписчик |
| **Project-данные (3 хранилища)** | SQLite `projects` + Knowledge `project:*` + Memory `PROJECT` | `context.db:projects` = source of truth, остальные — производные индексы |
| **Verification-слой (3)** | Verifier / PolicyEngine / MetricsEngine | НЕ дубль — 3 разных домена (проверка, политика, метрики). Оставить |

---

## 7. Горизонтальные подсистемы

### 7.1. Security

| Механизм | Реализация | Статус |
|---|---|---|
| Auth (Bearer) | `scripts_01/mcp_fastapi.py` — `verify_bearer_token`, hmac.compare_digest, Vault-first, TTL-кеш | ✅ |
| Secrets Vault | hvac client, `FREEBUFF_VAULT_ADDR/TOKEN/KEY`, VaultClient в diet_platform | 🟡 |
| Secret Scanner | `scripts_01/scanner.py` — credentials/token/vault-паттерны | ✅ |
| Shell-guard | `verifier.py` v5.25.0 — `_check_pytest` argv без shell=True | ✅ |
| RBAC/ACL | нет | 🔴 |
| Encryption | нет (только Fernet в projects_17/realtor_automation) | 🔴 |
| Plugin Trust | нет | 🔴 |
| Prompt Injection Protection | частично (verifier shell-guard, capability-политики) | 🟡 |

### 7.2. Events

| Компонент | Реализация | Статус |
|---|---|---|
| EventBus (in-process) | `scripts_01/event_bus.py` — publish/subscribe/unsubscribe, wildcard, Event/Subscription | ✅ |
| EventStore (persistent) | `freebuff_plugin_03/event/store.py` — schema.sql | ✅ |
| Replay | `freebuff_plugin_03/event/replay.py` — EventReplay | ✅ |
| Timeline | `freebuff_plugin_03/event/timeline.py` — TimelineEngine | ✅ |
| Audit | `freebuff_plugin_03/event/audit.py` — AuditEngine (actions/decisions/config) | ✅ |
| Pulse (persistent) | `freebuff_plugin_03/event/pulse.py` — PulseEngine | ✅ |
| Domain Pulse | `scripts_01/project_pulse.py` — ProjectPulse (git+file+events) | ✅ (восстановлен) |
| MCP event tools | `freebuff_plugin_03/mcp_server.py` — event_audit/replay/timeline/search/pulse | ✅ |

### 7.3. Memory

| Уровень | Реализация | Статус |
|---|---|---|
| WORKING/PROJECT/KNOWLEDGE/PERSONAL/ARCHIVE | `memory_engine.py` `MemoryLevel` | ✅ |
| Context/Session/Checkpoint | `context_manager.py` | ✅ |
| Knowledge (FTS5+TF-IDF+LSA) | `knowledge_engine.py` | ✅ |
| Graph | `graph_index.py` | ✅ |
| RAG 2.0 (RRF + rerank) | `rag_engine.py` | ✅ (восстановлен) |
| VECTOR (chromadb) | **отсутствует** — `grep VECTOR memory_engine.py` → 0 | 🔴 (потерян при инциденте, реализовать заново по v5.12.0 CHANGELOG) |

### 7.4. Verification

| Компонент | Реализация | Статус |
|---|---|---|
| Verifier (6 типов проверок) | `verifier.py` | ✅ |
| PolicyEngine (capability) | `freebuff_plugin_03/policy/engine.py` | ✅ |
| Metrics (VCR/SRG/CpVO/RRR/TTD) | `metrics.py` | ✅ (восстановлен) |
| Roles (capability mapping) | `roles.py` — роль → capabilities | ✅ (восстановлен) |

---

## 8. Вертикальные подсистемы

### 8.1. Projects

- **Project Registry** 🟡: `scan_projects.py` (name/path/language/git_remote/category/status, upsert, `--rebuild`, `--status`).
- **Project Discovery** ✅: `scan_projects()`, `detect_git_remote()`, `detect_language()`.
- Нет: lifecycle (create/close/archive), Work Area FK, связей Project↔Resource.

### 8.2. Work Areas

- 🔴 НЕТ. Ближайшее — `category` (leviathan/telegram/ai/web/tool/infra/personal) в `scan_projects.py`.

### 8.3. Resources

- 🟡 3 слоя: `RuntimeRegistry` (runtimes), `ModelGateway` (модели), provider YAML (freebuff/claude_code/openclaw). Единой Resource-сущности нет.

### 8.4. Business Processes

- 🔴 НЕТ движка. Shell-скрипты: `cron_conspect.sh`, `doc_reminder.sh`, `tg_popup.sh`, `oom_protect.sh`, `overlay_float.sh`. Ближайший код — Orchestrator (не долгоживущий) и `bootstrap/engine.py` (императивная установка).

### 8.5. Scenarios

- ✅ `freebuff_plugin_03/scenario_engine.py` — 12 сценариев (9 freelance + agent_setup + task_framework + telegram_health_monitor), категории freelancing/agent/templates, REST + MCP + TG.

### 8.6. Plugins

- ✅ `scripts_01/plugin_api.py` — PluginManifest/Registry/Loader/lifecycle/EventBus — API работает.
- 🟡 Плагины: на диске **1 из 4** (`hello_world`); `tg_messenger`, `system_monitor`, `knowledge_sync` 🔶 утеряны (pyc загружаются: `TelegramMessengerPlugin`, `SystemMonitorPlugin`, `KnowledgeSyncPlugin` — восстановимы).

### 8.7. Skills & Prompts

- **Skills** 🔴: нет реестра (`grep class Skill` → 0).
- **Prompt Library** 🟡: `pompts_11/` — 29 файлов без метаданных; MCP prompts: context_resume, knowledge_search, task_start.

### 8.8. Connectors

- **Telegram** ⚠ 3 реализации (см. дубли).
- **MCP** ✅ клиент (`mcp_client.py`) + сервер (2 шт.) + Bridge (`bridge_layer.py`) + ACP (`acp_protocol.py`).
- **GitHub/Email/Drive/CRM/ERP/n8n/Make** 🔴.

---

## 9. План минимальной эволюции в Workspace OS

### Этап 0 — 🟡 ЧАСТИЧНО (восстановление целостности)
7 модулей + metrics + 27 MCP-инструментов восстановлены; 385/385 pyc-тестов; on-disk 236 passed / 2 pre-existing bootstrap фейла (вне scope).
**Остаток Этапа 0:** 3 плагина (knowledge_sync/system_monitor/tg_messenger) — восстановить из pyc той же методологией; `_main_with_notification()` — вернуть в `freebuff_cli.py` по CHANGELOG v5.24.0.

### Этап 1 — Workspace-контейнер (1 новая сущность)
`WorkspaceManager` — лёгкий слой поверх существующих движков:
- метаданные workspace в `data_13/workspace.db` (имя, настройки, users, roles, connected resources);
- фабрика/прокси к ContextManager, MemoryEngine, KnowledgeEngine, EventBus, ModelGateway;
- `workspace.yaml` как конфиг-источник истины (паттерн provider manifests).

### Этап 2 — Work Area (1 новая сущность, эволюция)
`WorkAreaRegistry`: `category` из scan_projects → таблица `work_areas` в context.db; FK `projects.work_area_id`; MCP tools `workarea_list/create/assign`.

### Этап 3 — Консолидация дублей (0 новых сущностей)
- единый `core_02/Router` (IntentRouter/SmartRouterAdapter — адаптеры);
- канонизация Telegram: один канон, два — обёртки;
- source-of-truth для проектов (context.db), Memory/Knowledge — производные;
- объединение двух pulse-лент (ProjectPulse доменная + PulseEngine подписчик).

### Этап 4 — Security-слой (2 сущности)
- **RBAC**: поверх восстановленного RoleEngine (роль→capabilities) — ACL (субъект→объект→действие), таблицы `users`+`acl` в workspace.db;
- **SecretsVaultService**: обёртка над hvac для всех модулей (сейчас только mcp_fastapi + diet_platform);
- Plugin Trust: подпись manifest.json, проверка при load.

### Этап 5 — Business Process Engine (1 новая сущность)
`ProcessEngine`: EventBus (триггеры) + ScenarioEngine (шаги) + Orchestrator (tasks); cron-подобный планировщик поверх shell-скриптов; таблица `processes`; MCP tools `process_start/list/stop`.

### Этап 6 — Connector-каркас (1 новая сущность)
`ConnectorRegistry` (по образцу PluginRegistry): единый интерфейс `Connector(manifest, connect, disconnect, send)`; адаптеры: Telegram (канон), GitHub, Email, Drive, n8n/Make (webhook).

### Этап 7 — Skills + Prompt Library (1 новая сущность)
`SkillRegistry` (manifest: triggers, uses_scenarios, uses_verifier); Prompt Library = структурированная версия `pompts_11/` с MCP tools `prompt_get/search`.

### Этап 8 — RAG 2.0 + VECTOR (восстановление + интеграция)
- восстановленный RAGEngine подключить к KnowledgeEngine как слой ранжирования (частично уже: `rag_engine.py:172`);
- VECTOR-уровень (chromadb VectorBackend) реализовать заново по CHANGELOG v5.12.0.

---

## 10. Заключение

**Насколько текущая кодовая база уже является фундаментом Workspace OS?**

**~80% сущностей и ~60% связей уже существуют.** После Этапа 0 (7 модулей + metrics) работают Context/Session/Memory/Knowledge/Graph/RAG, Orchestrator/Tasks, Scenario Engine, Verifier/Metrics/Policy, EventBus+EventStore, Runtime Adapter Layer + ModelGateway, Plugin API и восстановленные CoWork-модули (Presence/Collab/Distributed/Roles/Pulse/Notification) с 27 MCP-инструментами. **Остаток Этапа 0:** 3 плагина pyc-only + потерянная CLI-обёртка Notification — не влияют на карту домена, но учитываются при плане.

**Минимальный эволюционный путь — 8 этапов, из которых только 6 вводят новые сущности, и каждая опирается на существующий код:**

1. `WorkspaceManager` (контейнер) — поверх существующих движков;
2. `WorkAreaRegistry` — эволюция `category` из scan_projects;
3. консолидация 4 дублей — 0 новых сущностей;
4. RBAC + SecretsVault — поверх восстановленного RoleEngine и hvac;
5. `ProcessEngine` — композиция EventBus + ScenarioEngine + Orchestrator;
6. `ConnectorRegistry` — по образцу PluginRegistry;
7. `SkillRegistry` + Prompt Library — структурирование pompts_11/;
8. RAG 2.0 интеграция + VECTOR-уровень.

**Главный архитектурный вывод:** FreeBuff — это не «заготовка под платформу», а **платформа с неполной обвязкой доменных связей**. Код, который войдёт в Workspace OS практически без изменений — это ядро (EventBus, Context, Memory, Knowledge, Orchestrator, Scenario, Verifier, Runtime, Plugins, MCP). Новые сущности (Workspace, Work Area, Resource-единая, Process, RBAC) — это тонкие слои, а не переписывание. Превращение в целостную Workspace OS достижимо **без переписывания существующей архитектуры**, только добавлением ~6 лёгких доменных слоёв и консолидацией дублей.

---

*Отчёт сформирован по фактам полной кодовой базы на 2026-07-31 (HEAD `3be0bf5`). В отличие от исследования №1, все 7 восстановленных модулей проверены на диске (классы, API, интеграции). Доказательства — пути файлов, классы, строки интеграций — в разделах 3-8.*
