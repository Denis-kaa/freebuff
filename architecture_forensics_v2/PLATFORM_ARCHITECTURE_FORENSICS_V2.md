# PLATFORM ARCHITECTURE FORENSICS V2

> **Дата:** 2026-08-21
> **Версия проекта:** v5.189.67
> **Методология:** promt103 (Forensic Engineering Reporter) — FACT · ANALYSIS · DECISION · CONSEQUENCE · INFERENCE · FUTURE TRIGGER
> **Промт:** 104_19_platform_architectural_forensics_v2 (Platform Architectural Forensics)
> **Статус:** FORENSIC ONLY — код не изменялся, решения не принимались

---

## A. Executive Summary

Платформа Freebuff / Workspace OS представляет собой **local-first агентную инженерную среду**, развившуюся из набора скриптов в структурированную многослойную систему. На момент v5.189.67 система содержит:

- **88 Python-модулей** в `scripts_01/` (runtime-слой)
- **33 модуля** в `core_02/` (канонический слой)
- **124 тестовых файла** (3342+ тестов)
- **18 проектов** в `projects_17/`
- **3 Factory** (content, research, test) с BaseFactory-адаптерами
- **14 pipeline-ролей** Blueprint v3 (12 ядро + frontend + devops)
- **6 провайдеров** LLM (DeepSeek, Gemini, OpenRouter, SambaNova, DashScope, Ollama)

Система **частично соответствует** гипотезе Workspace OS (Whim → Workspace → Project → Intelligence → Scenario → Factory → Forge → Agents → Artifacts), но реальная архитектура **сложнее и шире** предполагаемой модели. Ключевая находка: система уже имеет большинство элементов модели, но они связаны **иначе**, чем предполагает линейная цепочка.

---

## B. Repository Reality Map

### B.1 Структурная карта

```
freebuff/
├── core_02/                    # Канонический слой (33 модуля)
│   ├── workspace.py            # Workspace (L-1) + Project (L-2) контейнеры
│   ├── workspace_registry.py   # Workspace↔Project mapping + privacy isolation
│   ├── scenario.py             # Scenario ABC + ScenarioManifest
│   ├── scenario_registry.py    # Multi-scenario registry с auto-discovery
│   ├── blueprint_v3.py         # Blueprint v3 reader/creator (14 roles)
│   ├── forge_facade.py         # ForgeFacade — единственный мост к ForgePipeline
│   ├── forge_pipeline.py       # 6-stage pipeline: FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT
│   ├── forge_registry.py       # ForgeRegistry — статусы проектов (UNFORGED→DEPLOYED)
│   ├── factory_base.py         # BaseFactory — template для domain Factory
│   ├── factory_registry.py    # FactoryRegistry — auto-discovery YAML манифестов
│   ├── factory_passport.py     # FactoryPassport — типизированный паспорт фабрики
│   ├── forge_passport.py       # ForgePassport — паспорт кузни (capabilities)
│   ├── router.py               # SmartRouter — capability-based model routing
│   ├── memory_store.py         # MemoryStore — SQLite-backed knowledge persistence
│   ├── semantic_layer.py       # SemanticLayer — semantic search
│   ├── boundaries_v17.py       # 14 архитектурных границ (B1-B14)
│   ├── dis_engine.py           # Policy compliance (DIRS reviewer)
│   ├── role_executor.py        # RoleExecutorRegistry — ADR-016 executor
│   └── missing_registry.py     # MissingRegistry — register-first lifecycle
│
├── scripts_01/                 # Runtime слой (88 модулей)
│   ├── orchestrator.py         # FSM/DAG Orchestrator (Goal→Plan→Execute→Validate)
│   ├── model_gateway.py        # 6 LLM providers + fallback chain
│   ├── context_manager.py      # Session persistence + auto-summarization
│   ├── event_bus.py            # EventBus — pub/sub event system
│   ├── memory_engine.py        # MemoryEngine — multi-level memory
│   ├── knowledge_engine.py    # KnowledgeEngine — FTS + TF-IDF + graph
│   ├── tool_runtime.py         # ToolRegistry + 5 built-in tools
│   ├── plugin_api.py           # PluginRegistry + BasePlugin
│   ├── mcp_server.py           # MCP Server (JSON-RPC)
│   ├── telegram_bot.py         # Telegram Bot интерфейс
│   ├── presence.py             # PresenceEngine — agent presence tracking
│   ├── collaboration.py        # CollaborationEngine — live collaboration
│   ├── roles.py                # RoleEngine — role assignment
│   ├── whim_capture.py         # Whim capture + lifecycle (NEW→TRIAGED→PROMOTED)
│   ├── opportunity_engine.py   # Opportunity lifecycle
│   ├── scenario_intelligence.py # ScenarioIntelligence — decision layer
│   ├── research_factory.py     # ResearchFactory(BaseFactory)
│   ├── content_factory.py     # ContentFactory(BaseFactory)
│   ├── test_factory.py         # TestFactory(BaseFactory) [implied***REMOVED***
│   ├── forge.py                # CLI для forge operations
│   ├── forge_api.py            # FastAPI REST API
│   ├── rag_engine.py           # RAGEngine — retrieval-augmented generation
│   ├── graph_index.py          # GraphIndex — knowledge graph
│   ├── metrics.py              # MetricsEngine
│   ├── notification.py         # NotificationManager
│   ├── project_pulse.py        # ProjectPulse — change feed
│   └── ... (60+ more modules)
│
├── freebuff_plugin_03/         # Plugin слой
│   ├── api.py                  # Plugin REST API
│   ├── tgbot.py                # TG bot для scenario engine
│   ├── scenario_engine.py     # Plugin scenario engine
│   ├── mcp_server.py           # Plugin MCP server
│   ├── mcp_client.py           # MCP client
│   ├── acp_protocol.py         # ACP (Agent Communication Protocol)
│   ├── bridge.py / bridge_layer.py # Universal bridge (MCP↔ACP)
│   ├── policy/                 # PolicyEngine + rules
│   ├── runtime/                # RuntimeRegistry + adapters
│   ├── event/                  # EventStore + Pulse + Audit + Timeline
│   └── bootstrap/              # BootstrapEngine
│
├── projects_17/                # 18 проектов (L-2 контейнеры)
├── tests_09/                   # 124 тестовых файла (3342+ тестов)
├── docs_10/                    # Документация
├── pompts_11/                  # Промт-контракты (NNN_TT_name.md)
├── runtime_05/                 # Runtime assets (factories/, scenarios/)
├── data_13/                    # YAML/SQLite persistence
└── prototype_22/              # UI прототип (HTML/CSS/JS)
```

### B.2 Ключевые классы и их LOC

| Класс | Файл | Роль |
|-------|------|------|
| `Workspace` | core_02/workspace.py | L-1 контейнер верхнего уровня |
| `Project` | core_02/workspace.py | L-2 изолированный проект |
| `WorkspaceRegistry` | core_02/workspace_registry.py | Workspace↔Project + privacy guard |
| `Scenario` (ABC) | core_02/scenario.py | Базовая абстракция сценария |
| `ScenarioRegistry` | core_02/scenario_registry.py | Multi-scenario каталог |
| `BlueprintCorpus` | core_02/blueprint_v3.py | 14 pipeline-ролей |
| `ForgePipeline` | core_02/forge_pipeline.py | 6-stage build pipeline |
| `ForgeFacade` | core_02/forge_facade.py | Единственный мост к ForgePipeline |
| `ForgeRegistry` | core_02/forge_registry.py | Статусы проектов (UNFORGED→DEPLOYED) |
| `FactoryRegistry` | core_02/factory_registry.py | Auto-discovery YAML манифестов |
| `BaseFactory` | core_02/factory_base.py | Template для domain Factory |
| `Orchestrator` | scripts_01/orchestrator.py | FSM/DAG multi-step execution |
| `ModelGateway` | scripts_01/model_gateway.py | 6 LLM providers + fallback |
| `ContextManager` | scripts_01/context_manager.py | Session persistence + summarization |
| `EventBus` | scripts_01/event_bus.py | Pub/sub event system |
| `MemoryEngine` | scripts_01/memory_engine.py | Multi-level memory |
| `KnowledgeEngine` | scripts_01/knowledge_engine.py | FTS + TF-IDF + graph search |
| `ToolRegistry` | scripts_01/tool_runtime.py | 5 built-in tools |
| `PluginRegistry` | scripts_01/plugin_api.py | Plugin system |
| `McpSessionManager` | scripts_01/mcp_server.py | MCP JSON-RPC server |
| `PresenceEngine` | scripts_01/presence.py | Agent presence tracking |
| `CollaborationEngine` | scripts_01/collaboration.py | Live collaboration sessions |
| `RoleEngine` | scripts_01/roles.py | Role assignment + capabilities |
| `WhimStore` | scripts_01/whim_capture.py | Whim lifecycle store |
| `ScenarioIntelligence` | scripts_01/scenario_intelligence.py | Decision layer |

---

## C. Current System Architecture

### C.1 Фактическая архитектура (не модель, а реальность)

```
USER
  ↓
[CLI / Telegram Bot / MCP Server / REST API (forge_api)***REMOVED***
  ↓
Orchestrator (FSM/DAG) ←→ ContextManager ←→ EventBus
  ↓
ScenarioIntelligence (discovery → evaluation → selection)
  ↓
FactoryRegistry.select_forge(capability) → (FactoryPassport, ForgePassport)
  ↓
BaseFactory.execute(opp) → ForgeFacade.run_chain(project, role_ids)
  ↓
ForgePipeline (FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT)
  ↓
Artifact → MemoryStore (kind=candidate) → LearningLoop
  ↓
Feedback → ScenarioIntelligence (decision history)
```

### C.2 Параллельные подсистемы (не в основной цепочке)

- **Presence + Collaboration + Roles** — CoWork Platform (Phase 6)
- **RAGEngine + GraphIndex + SemanticLayer** — knowledge/retrieval layer
- **Plugin API + MCP Server** — external integration layer
- **PolicyEngine (freebuff_plugin_03/policy/)** — rule-based routing override
- **RuntimeRegistry (freebuff_plugin_03/runtime/)** — runtime abstraction
- **Metrics + Notification** — observability layer
- **WorkspaceRegistry** — privacy isolation (workspace↔project)

---

## D. User → Workspace → Project Flow

### D.1 Точки входа пользователя

| Интерфейс | Файл | Протокол |
|-----------|------|----------|
| CLI | scripts_01/forge.py, freebuff_cli.py | argparse subcommands |
| Telegram | scripts_01/telegram_bot.py, freebuff_plugin_03/tgbot.py | TG Bot API |
| MCP | scripts_01/mcp_server.py | JSON-RPC 2.0 over stdio |
| REST API | scripts_01/forge_api.py, scripts_01/forge_interactive_api.py | HTTP/JSON |
| File queue | pompts_11/ (NNN_TT_name.md) | filesystem polling |

### D.2 Реальный flow

```
User → TG /task <text>  ИЛИ  CLI command  ИЛИ  MCP tool call
  ↓
[Intent parsing — нет отдельного IntentRouter в коде; TG bot парсит /task***REMOVED***
  ↓
Orchestrator.run_workflow(goal)  ИЛИ  direct CLI command
  ↓
ContextManager.start_session(project=..., topic=...)
  ↓
[Workspace неявно — workspace_registry.py seed_defaults() создаёт 3 workspace***REMOVED***
```

**FACT:** Пользователь не взаимодействует с Workspace OS как с отдельной сущностью. Workspace — это файловая структура (`projects_17/`), а не интерфейс. Пользователь видит проекты напрямую.

---

## E. Intelligence / Brain Analysis

### E.1 Есть ли Intelligence?

**FACT:** В коде **нет** единого класса/модуля с именем `Intelligence` или `Brain`. 

**INFERENCE:** "Intelligence" в системе — это **emergent property** нескольких компонентов, а не отдельный слой:

| Компонент | Файл | Что делает |
|-----------|------|------------|
| Orchestrator | scripts_01/orchestrator.py | Планирование (DefaultPlanner), execution (DAG), validation |
| ScenarioIntelligence | scripts_01/scenario_intelligence.py | Decision: discovery → evaluation → ranking → selection |
| ContextManager | scripts_01/context_manager.py | Session context, checkpoints, auto-summarization |
| MemoryEngine | scripts_01/memory_engine.py | Multi-level memory (WORKING/EPISODIC/SEMANTIC) |
| KnowledgeEngine | scripts_01/knowledge_engine.py | FTS + TF-IDF + graph search |
| ModelGateway | scripts_01/model_gateway.py | 6 LLM providers, capability routing, fallback |
| SmartRouter | core_02/router.py | Capability→model routing |

### E.2 Companion / AI Partner

**FACT:** Концепция "AI companion / товарищ" **частично реализована** через:
- `ScenarioIntelligence` — задаёт вопросы "which approach fits?" и предлагает кандидатов
- `Orchestrator.check_existing_context()` — проверяет Knowledge на дубли перед созданием задачи
- `ContextManager` — помнит контекст сессии, создаёт checkpoints
- `MemoryEngine` — хранит историю (episodic + semantic memory)

**GAP:** Нет активного "советника", который инициирует обсуждение, критикует, предлагает альтернативы. ScenarioIntelligence — **reactive** (отвечает на запрос), а не **proactive** (не инициирует).

---

## F. Agent Architecture

### F.1 Что есть "Agent" в системе?

**FACT:** В коде **нет** абстракции `Agent` как самостоятельной сущности. "Агенты" в системе — это:

1. **Pipeline-роли** (14 штук в Blueprint v3): `explainer`, `lisa`, `risk`, `decomposer`, `architect`, `auditor`, `developer`, `frontend`, `devops`, `tester`, `fixer`, `acceptance`, `documenter`, `retrospective`
2. **Presence-агенты** (PresenceEngine): регистрируются с `agent_name`, имеют статус (online/offline/away)
3. **Collaboration-участники** (CollaborationEngine): `ParticipantRole` (OWNER/EDITOR/VIEWER)
4. **Role assignments** (RoleEngine): `RoleDefinition` с `capabilities` списком

### F.2 Agent Lifecycle

**FACT:** Явного agent lifecycle **нет**. Pipeline-роли не имеют lifecycle — они stateless functions. PresenceEngine имеет `register/unregister/heartbeat`, но это presence-tracking, а не agent lifecycle.

### F.3 Agent → Agent interaction

**FACT:** Agent-to-agent interaction **не реализован** как архитектурный паттерн. Pipeline-роли выполняются последовательно через `ForgeFacade.run_chain()` — каждая роль видит артефакты предыдущей, но **не общается** с ней.

---

## G. Workspace / Project Model

### G.1 Workspace (L-1)

**FACT:** `Workspace` (core_02/workspace.py) — это dataclass:
- `name`, `root`, `projects[***REMOVED***`, `default_environment`, `steps_policy` (optional|strict)
- Загружается из `workspace.yaml` (YAML)
- Имеет `validate()` → `WorkspaceHealth`

**FACT:** `WorkspaceRegistry` (core_02/workspace_registry.py) — SQLite-backed:
- 3 default workspace: Работа, Учёба, Хобби
- **Privacy invariant**: `workspace_projects.path` PRIMARY KEY → путь принадлежит ОДНОМУ workspace
- `PrivacyViolationError` при нарушении границы

### G.2 Project (L-2)

**FACT:** `Project` (core_02/workspace.py) — это dataclass:
- `name`, `root`, `type`, `stack[***REMOVED***`, `roles[***REMOVED***`, `contracts[***REMOVED***`
- `requirements_steps`: optional|required (per-project override)
- `get_requirements()` → README/RUNNABLE/CHECKLIST/STEPS presence
- `append_step()` → добавляет step в STEPS.md
- `run_env_doctor()` → диагностика окружения

### G.3 Граница проекта

**FACT:** Граница проекта = директория `projects_17/<name>/` с `project.yaml`. Проект **не является**:
- Knowledge boundary (KnowledgeEngine глобальный)
- Memory boundary (MemoryEngine глобальный, хотя ключи могут содержать project_id)
- Security boundary (нет per-project permissions)

**INFERENCE:** Проект — это **контейнер контекста** (MANIFEST, LESSONS, decisions, ROADMAP, STEPS), но **не изоляционная граница** для runtime-ресурсов.

---

## H. Scenario Architecture

### H.1 Что такое Scenario?

**FACT:** `Scenario` (core_02/scenario.py) — это **ABC** с методами:
- `scenario_id`, `display_name` (properties)
- `role_objects()` → list[Role***REMOVED***
- `load_role_text(role_id)` → str (fuzzy match)
- `routing_hint(role_id)` → list[str***REMOVED*** (capability tokens)
- `validate()` → list[str***REMOVED*** (errors)

### H.2 ScenarioRegistry

**FACT:** `ScenarioRegistry` (core_02/scenario_registry.py) — multi-scenario каталог:
- Auto-discovery YAML манифестов из `runtime_05/scenarios/`
- `_SCENARIO_TYPES` dispatch table: `{"blueprint_v3": BlueprintScenario***REMOVED***`
- `propose_roles(query, top_n)` — cross-scenario fuzzy match
- `find_role(role_id)` — cross-scenario lookup

### H.3 Scenario → Factory → Forge

**FACT:** `ScenarioIntelligence` (scripts_01/scenario_intelligence.py) реализует цепочку:
```
OPPORTUNITY → SCENARIO DISCOVERY → CANDIDATES → EVALUATION → RANKING → SELECTION
  → CAPABILITY (domain-neutral token) → FactoryRegistry.select_forge → ForgeFacade
```

**FACT:** Scenario **не вызывает** Forge напрямую (§7.3 boundary). Только через `ForgeFacade`.

---

## I. Factory Analysis

### I.1 Есть ли реальная Factory abstraction?

**FACT:** ДА. `BaseFactory` (core_02/factory_base.py) — template class:
- `resolve(capability)` → (FactoryPassport, ForgePassport) via FactoryRegistry
- `build_execution_request(opp, capability)` → ExecutionRequest
- `execute(opp)` → ForgeFacade.run_chain → artifact
- `normalize_output(run, opp, request)` → artifact dict
- `_accumulate(opp, artifact, run)` → MemoryStore + LearningLoop

### I.2 Конкретные Factory

**FACT:** 3 конкретные Factory (все верифицированы на диске):
- `ResearchFactory` (scripts_01/research_factory.py) — capabilities: research, research_web
- `ContentFactory` (scripts_01/content_factory.py) — capabilities: article_generation, book_generation, report_generation
- `TestFactory` (scripts_01/test_factory.py) — capability: code (canonical: test/verifier per G-11.6)

### I.3 FactoryRegistry

**FACT:** `FactoryRegistry` (core_02/factory_registry.py) — auto-discovery YAML:
- `runtime_05/factories/<factory_id>/` директории
- `factory.yaml` (metadata) + `<forge_id>.yaml` (ForgePassport)
- `select_forge(capability)` → лучшая (factory, forge) пара по status-priority
- `CODE_RESOLUTION_POLICY` — canonical routing table (G-11.6)

---

## J. Forge Analysis

### J.1 Что фактически является Forge?

**FACT:** Forge — это **production pipeline** (вариант B + C из промта). Реализован двумя классами:

1. **ForgePipeline** (core_02/forge_pipeline.py) — 6-stage pipeline:
   - `stage_forge()` — создание/проверка артефактов (RUNNABLE.md, CHECKLIST.md)
   - `stage_check()` — Env Doctor + requirements check
   - `stage_build()` — сборка (npm/pip/esbuild)
   - `stage_test()` — тесты (pytest/npm test)
   - `stage_deploy()` — проверка dist/
   - `stage_report()` — отчёт + TG уведомление

2. **ForgeFacade** (core_02/forge_facade.py) — единственный мост:
   - `initiate_forge(project, role_id)` — явный запуск от pipeline-роли
   - `run_chain(project, role_ids)` — выполнение цепочки из 14 ролей
   - `validate_role_artifacts(project)` — проверка existence артефактов
   - **§7.3 invariant**: Scenario/роли НЕ вызывают ForgePipeline напрямую

### J.2 ForgeRegistry

**FACT:** `ForgeRegistry` (core_02/forge_registry.py) — YAML-backed реестр:
- Статусы: UNFORGED → CHECKING → BUILDING → TESTING → DEPLOYED / FAILED
- **B10 invariant** (R-127): UNFORGED ≠ UNTESTED (машинно-проверяемая семантика)
- `record_run(project_id, run)` → обновляет статус + историю

---

## K. Agent / Skill / Tool Architecture

### K.1 ToolRegistry

**FACT:** `ToolRegistry` (scripts_01/tool_runtime.py) — 5 built-in tools:
- `GitTool` (status, diff, log, add, commit, branch, tag, checkout)
- `SQLiteTool` (query, execute)
- `HTTPTool` (GET, POST, PUT, DELETE, HEAD, PATCH)
- `FileTool` (read, write, list, delete, copy, move, exists, mkdir)
- `ShellTool` (shell commands with timeout)

### K.2 Skill

**FACT:** Концепция "Skill" **отсутствует** как отдельная сущность. Pipeline-роли Blueprint v3 — это ближайший аналог: каждая роль имеет `routing_hint` (capability tokens) и `DEFAULT_ROLE_OUTPUTS` (expected artifacts).

### K.3 Capability discovery

**FACT:** `FactoryRegistry.find_by_capability(capability)` и `select_forge(capability)` — механизм обнаружения отсутствующей capability. `MissingRegistry` (core_02/missing_registry.py) — register-first lifecycle для недостающих элементов.

---

## L. Artifact Architecture

### L.1 Что считается Artifact?

**FACT:** Artifact в системе — это **dict** (не типизированный класс), создаваемый в `BaseFactory.normalize_output()`:
```python
{
    "id": "art-<uuid>",
    "kind": "content_artifact" | "research_artifact" | "test_artifact",
    "opportunity_id": ...,
    "project_id": ...,
    "capability": ...,
    "factory_id": ...,
    "forge_id": ...,
    "target": "projects_17/<id>/forge/",
    "overall": "ok" | "failed" | "degraded",
    "validation": ValidationSummary.to_dict(),
    "created_at": ISO timestamp,
***REMOVED***
```

### L.2 Artifact lineage / provenance

**FACT:** Artifact имеет `opportunity_id`, `project_id`, `capability`, `factory_id`, `forge_id` — это **provenance chain**. Но нет единого Artifact Registry для трассировки lineage.

**FACT:** `_accumulate()` записывает artifact в `MemoryStore` (kind=candidate) с tags=[factory, capability, opportunity_id***REMOVED*** и `record_learning_event()`.

---

## M. Memory / Knowledge / Context

### M.1 Единое место истории проекта?

**FACT:** НЕТ. Информация разложена:

| Хранилище | Файл | Что хранит |
|-----------|------|------------|
| MemoryEngine | scripts_01/memory_engine.py | WORKING/EPISODIC/SEMANTIC memory entries |
| KnowledgeEngine | scripts_01/knowledge_engine.py | FTS + TF-IDF + graph index (SQLite) |
| ContextManager | scripts_01/context_manager.py | Sessions, checkpoints, messages |
| MemoryStore | core_02/memory_store.py | Knowledge objects + relationships (SQLite) |
| GraphIndex | scripts_01/graph_index.py | Knowledge graph (nodes + edges) |
| RAGEngine | scripts_01/rag_engine.py | Retrieval-augmented generation |
| SemanticLayer | core_02/semantic_layer.py | Semantic search |
| WorkspaceRegistry | core_02/workspace_registry.py | Workspace↔Project mapping (SQLite) |
| ForgeRegistry | core_02/forge_registry.py | Project statuses + pipeline history (YAML) |
| DecisionHistoryStore | scripts_01/scenario_intelligence.py | Scenario decisions (YAML) |

### M.2 Provenance path

**FACT:** Полный путь Whim → ... → Result **не сохраняется** в едином хранилище. Связи:
- `Whim.related_opportunity_id` → Opportunity (YAML cross-reference)
- `Opportunity.provenance` → dict с origin/source
- `Artifact.opportunity_id` → link back
- `DecisionHistoryStore` → scenario decisions per opportunity

**GAP:** Нет единого query, который восстановит полный путь: Whim → Idea → Discussion → Decision → Scenario → Execution → Artifact → Result → Next Decision.

---

## N. Event / Orchestration / Runtime

### N.1 EventBus

**FACT:** `EventBus` (scripts_01/event_bus.py) — pub/sub event system:
- `Event` dataclass: type, source, data, timestamp
- `publish(event)` → синхронные subscriber callbacks
- `subscribe(event_type, callback)` → registration
- `EventLogEntry` — persistent log

### N.2 Orchestrator

**FACT:** `Orchestrator` (scripts_01/orchestrator.py) — FSM/DAG:
- `DefaultPlanner.plan(goal)` → Step[***REMOVED*** (keyword-based heuristic)
- `ThreadPoolExecutor` для параллельного выполнения шагов
- DAG resolution: `_get_ready_steps()` — шаги с удовлетворёнными зависимостями
- `check_existing_context()` — Knowledge search перед созданием задачи
- `save_workflow()` → MemoryEngine

### N.3 Runtime Abstraction

**FACT:** `freebuff_plugin_03/runtime/` — Runtime Abstraction Layer:
- `RuntimeRegistry` — реестр runtime-сред
- `RuntimeCapabilityRegistry` — capabilities runtime
- `AdapterRegistry` — адаптеры для внешних runtime

---

## O. Plugin / MCP / External Integration

### O.1 Plugin System

**FACT:** `PluginRegistry` (scripts_01/plugin_api.py) + `BasePlugin` (ABC):
- `register(plugin)`, `load_plugin(name)`, `list_plugins()`
- 3 Phase-4 плагина: `tg_messenger`, `system_monitor`, `knowledge_sync`

### O.2 MCP Server

**FACT:** `McpSessionManager` (scripts_01/mcp_server.py) — JSON-RPC 2.0:
- `handle_initialize`, `handle_tools_list`, `handle_tools_call`
- `handle_resources_list`, `handle_resources_read`
- `handle_prompts_list`, `handle_prompts_get`
- Tools: runtime_list/connect/disconnect/select/generate

### O.3 External capability isolation

**FACT:** `WorkspaceRegistry.assert_path_privacy()` — **единственный** механизм, гарантирующий, что путь принадлежит одному workspace. Но это workspace-level, а не project-level isolation.

**GAP:** Нет gateway-механизма для подключения внешней capability к конкретному Project без доступа ко всему Workspace OS.

---

## P. Feedback / Learning Loop

### P.1 Есть ли реальный feedback loop?

**FACT:** Частично. `BaseFactory._accumulate()`:
1. Artifact → `MemoryStore.store_knowledge(kind=candidate)` с `lifecycle_stage` (validated/raw)
2. `MemoryStore.record_learning_event()` — trigger_id, context_snapshot, outcome (success/failure)
3. `LearningLoop.record_feedback(kid, outcome)` — если LearningLoop подключён

### P.2 Замыкается ли loop?

**FACT:** `ScenarioIntelligence` имеет `feedback(opportunity_id, outcome)` — записывает результат в `DecisionHistoryStore`. При следующем `evaluate()` для того же opportunity, `history` factor (weight=0.20) учитывает предыдущие выполнения.

**INFERENCE:** Feedback loop **существует**, но **узкий**: только scenario selection учитывает историю. Нет loop, который бы менял pipeline-роли, factory manifests, или capability tokens на основе feedback.

---

## Q. Current Execution Paths

### Q.1 Main execution path (Factory vertical slice)

```
User → CLI/TG/MCP
  ↓
Opportunity (from whim_capture.promote() OR manual)
  ↓
ScenarioIntelligence.discover(opportunity_id) → ScenarioCandidate[***REMOVED***
  ↓
ScenarioIntelligence.select(opportunity_id) → ScenarioDecision (with capability)
  ↓
BaseFactory.execute(opp):
  1. _derive_capability(opp) → capability token
  2. resolve(capability) → (FactoryPassport, ForgePassport) via FactoryRegistry
  3. build_execution_request(opp, capability) → ExecutionRequest
  4. _resolve_project(opp) → Project.load(projects_17/<id>)
  5. ForgeFacade.run_chain(project, role_ids) → ChainRun
  6. normalize_output(run, opp, request) → artifact dict
  7. _accumulate(opp, artifact, run) → MemoryStore + LearningLoop
  ↓
Artifact → MemoryStore
```

### Q.2 Direct forge path (CLI)

```
User → python scripts_01/forge.py forge <project>
  ↓
ForgeFacade.initiate_forge(project, role_id="developer")
  ↓
ForgePipeline.run() → PipelineRun (6 stages)
  ↓
ForgeRegistry.record_run(project_id, run) → status update
```

---

## R. Architecture Hypothesis Validation

### R.1 Модель vs Реальность

| Элемент модели | Существует? | Evidence |
|----------------|-------------|----------|
| Whim | ✅ ДА | scripts_01/whim_capture.py: Whim dataclass + WhimStore + lifecycle |
| Workspace OS | ⚠️ Частично | workspace.py + workspace_registry.py, но "Workspace OS" как платформа = весь репозиторий |
| Workspace | ✅ ДА | core_02/workspace.py: Workspace dataclass (L-1) |
| Project | ✅ ДА | core_02/workspace.py: Project dataclass (L-2) |
| Intelligence | ⚠️ Частично | Нет единого слоя; emergent из Orchestrator+ScenarioIntelligence+ContextManager+Memory+Knowledge |
| Companion / AI Partner | ⚠️ Частично | ScenarioIntelligence reactive; нет proactive companion |
| Agent | ⚠️ Partial | Pipeline-роли + Presence agents; нет Agent ABC |
| Scenario | ✅ ДА | core_02/scenario.py: Scenario ABC + ScenarioRegistry |
| Factory | ✅ ДА | core_02/factory_base.py: BaseFactory + 3 concrete + FactoryRegistry |
| Forge | ✅ ДА | core_02/forge_pipeline.py + forge_facade.py + forge_registry.py |
| Skill | ❌ НЕТ | Нет отдельной сущности; routing_hint — ближайший аналог |
| Tool | ✅ ДА | scripts_01/tool_runtime.py: ToolRegistry + 5 tools |
| Artifact | ⚠️ Partial | Dict в BaseFactory.normalize_output; нет Artifact Registry |
| Memory | ✅ ДА | scripts_01/memory_engine.py + core_02/memory_store.py |
| Knowledge | ✅ ДА | scripts_01/knowledge_engine.py (FTS+TF-IDF+graph) |
| Event | ✅ ДА | scripts_01/event_bus.py: EventBus (pub/sub) |
| Runtime | ✅ ДА | freebuff_plugin_03/runtime/: RuntimeRegistry + adapters |
| Plugin | ✅ ДА | scripts_01/plugin_api.py: PluginRegistry + BasePlugin |
| Feedback | ⚠️ Partial | _accumulate + LearningLoop; узкий (только scenario selection) |
| Evolution | ❌ НЕТ | Нет механизма самоэволюции системы |

### R.2 Оценка соответствия

**~60%** (полное соответствие) — модель Workspace OS + Intelligence + Scenario + Factory + Forge **частично соответствует** реальности. Если учитывать частичные соответствия как половину, соответствие = **~75%** (12 полных + 6 частичных / 20 элементов). Основные расхождения:

1. **Intelligence** — не отдельный слой, а emergent property
2. **Companion** — reactive, не proactive
3. **Agent** — нет Agent ABC; pipeline-роли не общаются друг с другом
4. **Skill** — отсутствует как сущность
5. **Artifact** — dict, не типизированный класс с lineage
6. **Feedback loop** — узкий, не замыкается на factory/forge evolution
7. **Evolution** — полностью отсутствует

НО: Workspace, Project, Scenario, Factory, Forge, Tool, Memory, Knowledge, Event, Runtime, Plugin — **реализованы и работают**.

---

## S. Missing / Partial / Conceptual Components

### S.1 Missing (не существует в коде)

| Компонент | Описание | Приоритет |
|-----------|----------|-----------|
| Agent ABC | Нет единой абстракции агента | High |
| Skill | Нет сущности Skill (между Role и Tool) | Medium |
| Artifact Registry | Нет единого реестра артефактов с lineage | Medium |
| Intelligence Layer (как единый модуль) | Нет единого слоя; размыт по модулям. Прим.: Intelligence как emergent-свойство частично реализован (см. §R.1) — разница между «единым модулем» (missing) и «emergent-свойством» (partial) | High |
| Proactive Companion | Нет активного советника/критика | Medium |
| Evolution Engine | Нет механизма самоэволюции | Low |
| Intent Router | Нет отдельного intent parsing (TG bot парсит inline) | Medium |

### S.2 Partial (существует частично)

| Компонент | Что есть | Чего нет |
|-----------|----------|----------|
| Feedback Loop | _accumulate + scenario history | Не меняет factory/forge manifests |
| Project Boundary | Контейнер контекста | Не security/knowledge/memory boundary |
| Artifact Provenance | opportunity_id + tags в MemoryStore | Нет единого query для lineage |
| Agent Lifecycle | Presence register/unregister | Нет lifecycle для pipeline-ролей |
| External Isolation | WorkspaceRegistry privacy | Нет project-level gateway |

### S.3 Concept only (описано в док. но не в коде)

| Компонент | Где описано | Статус в коде |
|-----------|-------------|---------------|
| "Workspace OS" | AGENTS.md §3, PLATFORM.md | Весь репозиторий = "Workspace OS" |
| "Intelligence" | промт104, docs | Emergent, не отдельный модуль |
| "Companion" | промт104 §3 | ScenarioIntelligence — ближайший |
| "Evolution" | BUFFY.md, VISION_3.0 | Нет кода |

---

## T. Architectural Blind Spots

Компоненты системы, которые **не входят** в модель (Whim→Workspace→Project→Intelligence→Scenario→Factory→Forge→Agent→Artifact), но **существуют** и **важны**:

| Подсистема | Файл(ы) | Важность |
|------------|---------|----------|
| **Security** | .keys/, Bearer auth | Критичная — но не в модели |
| **Policy Engine** | freebuff_plugin_03/policy/ | User-choice override routing |
| **Observability** | metrics.py, notification.py | Metrics + notifications |
| **Project Pulse** | scripts_01/project_pulse.py | Change feed для проектов |
| **ACP Protocol** | freebuff_plugin_03/acp_protocol.py | Agent Communication Protocol |
| **Bridge Layer** | freebuff_plugin_03/bridge*.py | Universal bridge MCP↔ACP |
| **Bootstrap** | freebuff_plugin_03/bootstrap/ | Engine initialization + doctor |
| **DIS Engine** | core_02/dis_engine.py | Policy compliance (DIRS reviewer) |
| **MissingRegistry** | core_02/missing_registry.py | Register-first lifecycle для недостающего |
| **Engineering Memory** | scripts_01/engineering_memory.py | External memory (drafts) |
| **Remote Sync** | core_02/remote_sync.py | Phase 5.3 distributed sync |
| **Phone Control MCP** | scripts_01/phone_control_mcp.py | Android phone control |
| **TG Terminal Messenger** | projects_17/tg_terminal_messenger/ | TG client project |
| **Flutter App** | projects_17/freebuff_flutter_app/ | Mobile app (не начат) |

---

## U. Contradictions

1. **"Workspace OS" = весь репозиторий**, но `Workspace` = dataclass с 3 полями. Модель предполагает Workspace OS как отдельный уровень, а реально это umbrella-term.
2. **Scenario ≠ Forge Pipeline** — Scenario это каталог ролей, а не execution pipeline. Forge Pipeline — это build pipeline (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT). Они ортогональны (§7.3), но в модели представлены как последовательность.
3. **Agent в модели = активный участник**, в коде = stateless pipeline-роль без communication.
4. **"Intelligence" в модели = отдельный слой**, в коде = emergent из 5+ модулей без единого интерфейса.

---

## V. Provenance / Traceability Gaps

| Gap | Описание |
|-----|----------|
| Whim → Project | Whim.promote() создаёт Opportunity, но Opportunity → Project link слабый (project_id строка, не FK) |
| Decision → Execution | ScenarioDecision сохраняется в YAML, но не linked to ChainRun |
| Artifact → Feedback | _accumulate записывает в MemoryStore, но нет query: "покажи все артефакты для этого opportunity" |
| Pipeline Run → Role | ChainRun содержит role_ids, но role execution details (кто, когда, какой prompt) не сохраняются |
| Session → Project | ContextManager sessions имеют project_id FK, но session → workflow → artifact path не трассируется |

---

## W. Recommended Canonical Architecture

### W.1 CURRENT REAL ARCHITECTURE

```
USER
  ↓ (CLI / TG / MCP / REST)
Orchestrator + ContextManager + EventBus
  ↓
ScenarioIntelligence (reactive decision)
  ↓
FactoryRegistry.select_forge(capability)
  ↓
BaseFactory.execute() → ForgeFacade.run_chain()
  ↓
ForgePipeline (6 stages)
  ↓
Artifact → MemoryStore
  ↓
[Partial Feedback → ScenarioIntelligence history***REMOVED***
```

### W.2 TARGET ARCHITECTURAL MODEL

```
Whim → [EXISTS***REMOVED***
  ↓
Workspace → [EXISTS but = filesystem, not OS-level***REMOVED***
  ↓
Project → [EXISTS but not isolation boundary***REMOVED***
  ↓
Intelligence → [MISSING: need unified layer***REMOVED***
  ↓
Scenario → [EXISTS***REMOVED***
  ↓
Factory → [EXISTS***REMOVED***
  ↓
Forge → [EXISTS***REMOVED***
  ↓
Agent/Skill/Tool → [PARTIAL: Tool EXISTS, Skill MISSING, Agent = pipeline-role***REMOVED***
  ↓
Artifact → [PARTIAL: dict, no registry***REMOVED***
  ↓
Project State → [PARTIAL: ForgeRegistry status only***REMOVED***
  ↓
Intelligence (feedback) → [PARTIAL: narrow loop***REMOVED***
```

### W.3 Gap Analysis: CURRENT → TARGET

| Layer | Status | Gap |
|-------|--------|-----|
| Whim | ✅ EXISTS | — |
| Workspace | ✅ EXISTS | Privacy guard работает; но workspace ≠ "OS" |
| Project | ⚠️ PARTIAL | Нужен project-level isolation (knowledge/memory boundary) |
| Intelligence | ❌ MISSING | Нужен unified Intelligence layer (proactive + reactive) |
| Companion | ❌ MISSING | Нужен proactive advisor/critic |
| Agent | ⚠️ PARTIAL | Нужен Agent ABC + lifecycle + A2A communication |
| Scenario | ✅ EXISTS | — |
| Factory | ✅ EXISTS | — |
| Forge | ✅ EXISTS | — |
| Skill | ❌ MISSING | Нужна Skill сущность (Role → Skill → Tool) |
| Tool | ✅ EXISTS | — |
| Artifact | ⚠️ PARTIAL | Нужен Artifact Registry с lineage |
| Memory | ✅ EXISTS | — |
| Knowledge | ✅ EXISTS | — |
| Event | ✅ EXISTS | — |
| Runtime | ✅ EXISTS | — |
| Plugin | ✅ EXISTS | — |
| Feedback | ⚠️ PARTIAL | Нужен wider loop (factory/forge evolution) |
| Evolution | ❌ MISSING | Нужен evolution engine |

---

## X. Roadmap Implications

Based on forensic analysis, recommended next steps (INFERENCE, not decisions):

1. **Agent ABC + lifecycle** — унифицировать pipeline-роли и presence-агенты под единый контракт
2. **Intelligence Layer** — выделить ScenarioIntelligence + Orchestrator + ContextManager в единый Intelligence module
3. **Proactive Companion** — добавить advisor, который инициирует discussion/critique
4. **Artifact Registry** — типизированный класс + SQLite registry с lineage query
5. **Project isolation** — per-project knowledge/memory boundary (не только workspace-level)
6. **Skill abstraction** — промежуточная сущность между Role и Tool
7. **Wider feedback loop** — feedback → factory/forge manifest evolution
8. **Evolution engine** — механизм самоэволюции системы

---

## Y. Evidence Ledger

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| Workspace is L-1 container | core_02/workspace.py | `Workspace` dataclass | load() from workspace.yaml, validate() → WorkspaceHealth |
| Project is L-2 container | core_02/workspace.py | `Project` dataclass | load() from project.yaml, get_requirements(), append_step() |
| Privacy invariant enforced | core_02/workspace_registry.py | `WorkspaceRegistry.assert_path_privacy()` | PRIMARY KEY on path, raises PrivacyViolationError |
| Scenario is ABC | core_02/scenario.py | `Scenario(ABC)` | role_objects(), load_role_text(), routing_hint(), validate() |
| ScenarioRegistry auto-discovers | core_02/scenario_registry.py | `ScenarioRegistry._load_from_dir()` | walks *.yaml, dispatches on scenario_type |
| ForgePipeline = 6 stages | core_02/forge_pipeline.py | `ForgePipeline.run()` | stage_forge→check→build→test→deploy→report |
| ForgeFacade = only bridge | core_02/forge_facade.py | `ForgeFacade.initiate_forge()` | gate: PIPELINE_ROLES check, §7.3 invariant |
| ForgeRegistry tracks status | core_02/forge_registry.py | `ForgeRegistry.record_run()` | UNFORGED→DEPLOYED/FAILED, B10/R-127 invariant |
| FactoryRegistry auto-discovers | core_02/factory_registry.py | `FactoryRegistry._reload()` | walks runtime_05/factories/<id>/ |
| BaseFactory = template | core_02/factory_base.py | `BaseFactory.execute()` | resolve→request→ForgeFacade→artifact→accumulate |
| Whim lifecycle exists | scripts_01/whim_capture.py | `Whim` + `advance()` | NEW→TRIAGED→PROMOTED→OPPORTUNITY |
| ScenarioIntelligence = decision | scripts_01/scenario_intelligence.py | `ScenarioIntelligence.select()` | discovery→evaluation→ranking→selection |
| Orchestrator = FSM/DAG | scripts_01/orchestrator.py | `Orchestrator.run_workflow()` | Plan→Execute(parallel)→Validate |
| EventBus = pub/sub | scripts_01/event_bus.py | `EventBus.publish()` | synchronous subscriber callbacks |
| ModelGateway = 6 providers | scripts_01/model_gateway.py | `ModelGateway.generate()` | deepseek/gemini/openrouter/sambanova/dashscope/ollama + fallback |
| ToolRegistry = 5 tools | scripts_01/tool_runtime.py | `ToolRegistry.execute()` | git/sqlite/http/file/shell |
| PluginRegistry exists | scripts_01/plugin_api.py | `PluginRegistry.register()` | BasePlugin ABC + 3 plugins |
| MCP Server = JSON-RPC | scripts_01/mcp_server.py | `McpSessionManager` | handle_initialize/tools_list/tools_call |
| PresenceEngine = tracking | scripts_01/presence.py | `PresenceEngine.register()` | agent_name, status, heartbeat |
| CollaborationEngine = live | scripts_01/collaboration.py | `CollaborationEngine.create_session()` | participants, messages, events |
| RoleEngine = assignment | scripts_01/roles.py | `RoleEngine.assign_role()` | RoleDefinition + capabilities |
| MemoryStore = SQLite | core_02/memory_store.py | `MemoryStore.store_knowledge()` | kind=candidate, lifecycle_stage, confidence_score |
| KnowledgeEngine = FTS+graph | scripts_01/knowledge_engine.py | `KnowledgeEngine.search()` | FTS + TF-IDF + graph (SQLite) |
| ContextManager = sessions | scripts_01/context_manager.py | `ContextManager.start_session()` | SQLite schema v5, checkpoints |
| MissingRegistry = lifecycle | core_02/missing_registry.py | `MissingRegistry` | registered→design_ready→prompt_written→implemented |

---

## Z. Final Verdict

### 16 ключевых вопросов (промт104 §30)

1. **Где реально находится система сейчас?** — Local-first агентная инженерная среда с 88+ модулями, 3342+ тестами, 18 проектами, 3 Factory, 6 LLM providers.
2. **Что уже является Workspace OS?** — Структура директорий + WorkspaceRegistry + privacy guard. Но "Workspace OS" = весь репозиторий, не отдельный модуль.
3. **Что уже является Project?** — Dataclass с YAML config, requirements check, STEPS.md tracking. Но не isolation boundary.
4. **Есть ли Intelligence?** — Нет как отдельный слой. Emergent из Orchestrator + ScenarioIntelligence + ContextManager + Memory + Knowledge + ModelGateway.
5. **Есть ли Companion / AI Brain?** — Частично. ScenarioIntelligence reactive (отвечает на запросы), но не proactive (не инициирует).
6. **Как реально взаимодействуют агенты?** — Pipeline-роли выполняются последовательно через ForgeFacade.run_chain(). Нет A2A communication. Presence/Collaboration — отдельная подсистема.
7. **Что такое Scenario в реальности?** — ABC с role_objects(), routing_hint(). Это каталог ролей, а не execution pipeline.
8. **Есть ли Factory?** — Да. BaseFactory + 3 concrete + FactoryRegistry с auto-discovery YAML.
9. **Что реально является Forge?** — Production pipeline (ForgePipeline: 6 stages) + ForgeFacade (единственный мост).
10. **Где находятся Skills / Tools?** — Tools: ToolRegistry с 5 built-in. Skills: отсутствуют как сущность.
11. **Как появляется Artifact?** — BaseFactory.normalize_output() создаёт dict, _accumulate() записывает в MemoryStore.
12. **Как результат возвращается в Project?** — ForgeRegistry.record_run() обновляет статус. Artifact → MemoryStore (kind=candidate). Но artifact → project file system link слабый.
13. **Что из модели уже построено?** — Workspace, Project, Scenario, Factory, Forge, Tool, Memory, Knowledge, Event, Runtime, Plugin (12 из 20 элементов).
14. **Что отсутствует?** — 6 элементов: (а) полностью отсутствуют 5 — Agent ABC, Skill, Artifact Registry, Proactive Companion, Evolution Engine; (б) частично — единый Intelligence Layer (как модуль) отсутствует, хотя Intelligence как emergent-свойство реализован; (в) Intent Router — отсутствует как отдельный модуль (TG-бот парсит inline). Все — см. §S.1.
15. **Где ошибочно смешиваем уровни?** — "Intelligence" и "Agent" в модели = отдельные уровни, в коде = размыты по модулям. "Workspace OS" = umbrella term, не отдельный слой.
16. **Следующий архитектурный шаг?** — Agent ABC + Intelligence Layer + Artifact Registry (по приоритету).

### Процент соответствия модели реальности

**~60%** (полное соответствие; ~75% с учётом частичных как половина)

Обоснование: 12 из 20 элементов модели полностью реализованы (60%): Whim, Workspace, Project, Scenario, Factory, Forge, Tool, Memory, Knowledge, Event, Runtime, Plugin. 6 частично (30%): Workspace OS, Intelligence, Companion, Agent, Artifact, Feedback. 2 отсутствуют (10%): Skill, Evolution. Но реальная система **ширше** модели — содержит 14+ подсистем, не учтённых в модели (Security, Policy, Observability, ACP, Bridge, Bootstrap, DIS, MissingRegistry, Engineering Memory, Remote Sync, Phone Control, Project Pulse, Metrics, Notification).

---

*Forensic analysis complete. Код не изменялся. Архитектурные решения не принимались.*
