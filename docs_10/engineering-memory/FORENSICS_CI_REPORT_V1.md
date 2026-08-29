# FORENSICS REPORT: Platform Forensics & CI Integration Discovery — Полный отчёт A–K

| Поле | Значение |
|------|----------|
| **Документ** | FORENSICS_CI_REPORT_V1.md |
| **Статус** | 📋 Repository Forensics — выход A–K промта 1 |
| **Дата** | 2026-08-12 |
| **Методология** | `projects_17/content_factory/promts/1.md` — PLATFORM FORENSICS & CONTENT INTELLIGENCE INTEGRATION DISCOVERY v1.0 (§19 Required Output A–K, §20 Evidence Rule, §16 G0–G4) |
| **Роль** | Senior AI Systems Architect / Repository Forensics Engineer |
| **ARB-прецедент** | ARB-REV-004 (APPROVED WITH RECOMMENDATIONS), FORENSICS_CI_GAP_MAP_V1.md (G0–G4 карта) |
| **Правило** | Repository = источник истины (код > тесты > конфиг > доки > предположения). Read-only: код НЕ изменялся |

---

## A. EXECUTIVE FINDING

Платформа Freebuff (Workspace OS) — **готова к интеграции Content Intelligence на ~70%**. Весь **исполняемый слой** CI-конвейера уже реализован и работает в production: Scenario Registry (`core_02/scenario_registry.py` + `runtime_05/scenarios/`) умеет находить сценарии и роли, `ForgeFacade.run_chain()` исполняет цепочку из 14 production-ролей через единственный санкционированный мост (`initiate_forge`, §7.3), `RoleArtifactValidator` валидирует артефакты, `ForgeRegistry`/`MissingRegistry` хранят состояние в YAML (`data_13/`), а память/знания/события покрыты `memory_store`/`knowledge_engine`/`event_bus`. Терминология Factory/Forge/Scenario **канонична** — дословно совпадает с картой v1.1 (ARB-REV-003), конфликта имён (ARB-REV-001) нет. Не хватает ровно **Intelligence-слоя**: Opportunity Engine (обнаружение возможностей + lifecycle ACTIVE/DEFERRED/READY) и Whim-захвата (лёгкий вход мыслей) — оба G3; Factory Registry (паспорта кузен) — G2 (дизайн готов). Первый Content vertical slice реализуем **read-only головой**: Whim/Opportunity → SELECT SCENARIO → ForgeFacade → валидация → память, используя только существующий исполняемый хвост.

---

## B. REPOSITORY MAP

### B.1 Entrypoints

| Entrypoint | Location | Purpose | Status |
|------------|----------|---------|--------|
| CLI `freebuff` | `freebuff_cli.py` | `start`/`status`/`resume`/`conspect`/`list`/`checkpoint`/`restore`/`task start` | ✅ Production |
| Forge CLI | `scripts_01/forge.py` | `forge` (FORGE→REPORT), `check`, `status`, `register`, `report`, `step`, `chain --json` (14 ролей) | ✅ Production |
| MCP FastAPI | `scripts_01/mcp_fastapi.py` | HTTP API :8765 (uvicorn), статика `prototype_22/` | ✅ Production |
| MCP Server | `scripts_01/mcp_server.py` | 52 MCP-инструмента (event/policy/runtime/knowledge/memory/roles/presence/collab/rag/pulse) | ✅ Production |
| Telegram Bot | `scripts_01/telegram_bot.py` | `/task <text>`, чат → очередь промтов | ✅ Production |
| Scenario wizard | `scripts_01/wizard.py` | `--scenario <id>` — фильтр реестра, role-match | ✅ Production |

### B.2 Ядро (core_02/) — реестры и фабрики

| Компонент | Location | Purpose | Status | Evidence |
|-----------|----------|---------|--------|----------|
| ForgeRegistry | `core_02/forge_registry.py` + `data_13/forge_registry.yaml` | Статусы проектов (UNFORGED→CHECKING→BUILDING→TESTING→DEPLOYED/FAILED), история pipeline | ✅ Production | `register_project`, `record_run`, `validate_schema` (B10/R-127) |
| ScenarioRegistry | `core_02/scenario_registry.py` + `runtime_05/scenarios/` | Авто-discovery YAML-манифестов, роли, cross-scenario поиск | ✅ Production | `list_scenarios`, `get`, `find_role`, `propose_roles`, `validate_all` |
| ForgeFacade | `core_02/forge_facade.py` | Единственный мост роль→Forge (§7.3), chain-runner 14 ролей | ✅ Production | `initiate_forge`, `run_chain`, `validate_role_artifacts`, `can_initiate` |
| MissingRegistry | `core_02/missing_registry.py` + `data_13/missing_registry.yaml` | Register-first реестр недостающих элементов (7 записей) | ✅ Production | `register_missing`, `mark_prompt_written`, `mark_implemented`, `check` |
| ForgePipeline | `core_02/forge_pipeline.py` | FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT | ✅ Production | `run`, `stage_check` |
| Workspace/Project | `core_02/workspace.py` + `workspace_registry.py` | L-2 контейнер проекта | ✅ Production | `Project.load`, `WorkspaceRegistry` |
| MemoryStore | `core_02/memory_store.py` | SQLite knowledge_objects (10 kinds, lifecycle) | ✅ Production | `store_knowledge` |
| SemanticLayer / LearningLoop | `core_02/semantic_layer.py`, `learning_loop.py` | Классификация observation/lesson, feedback→confidence | ✅ Production | `learning_loop` (kind=observation) |

### B.3 Сервисы (scripts_01/)

| Компонент | Location | Purpose | Status |
|-----------|----------|---------|--------|
| KnowledgeEngine | `knowledge_engine.py` | FTS5+TF-IDF+SVD hybrid search | ✅ Production |
| GraphIndex | `graph_index.py` | Граф связей (7+ типов, BFS, subgraph) | ✅ Production |
| EventBus | `event_bus.py` + `context_12/events.db` | publish/subscribe, event_log/event_store | ✅ Production |
| MemoryEngine | `memory_engine.py` | 5 уровней JSON-памяти | ✅ Production |
| ProjectPulse | `project_pulse.py` + `data_13/project_pulse.db` | scan_git/scan_files, subscribe_eventbus | ✅ Production |
| PromptDispatcher/Queue | `prompt_dispatcher.py`, `prompt_queue.py` | Очередь задач, cron-тика, multi-turn | ✅ Production |
| DriftCheck / ConsistencyCheck | `drift_check.py`, `consistency_check.py` | Сверка код↔доки, naming, счётчики тестов | ✅ Production |
| ToolRuntime | `tool_runtime.py` | Исполнение тулов | ✅ Production |
| **research_web** | `scripts_01/research_web.py` | Web Research (Missing #6) — implemented | ✅ Production |
| **lisa_estimator** | `scripts_01/lisa_estimator.py` | Estimation LISA-3 (Missing #7) — implemented | ✅ Production |
| DistributedAgents | `distributed_agents.py` | AgentMesh: register/register_agent/run_distributed_workflow | ✅ Production |

### B.4 Runtime marketplace (runtime_05/)

| Файл | Назначение |
|------|-----------|
| `providers/freebuff.yaml`, `claude_code.yaml`, `openclaw.yaml` | Runtime-провайдеры (YAML-плагины, без изменения ядра) |
| `scenarios/blueprint_v3.yaml`, `vkusvill_demo.yaml` | Манифесты сценариев (Kwork Arbitr v3, demo) |
| `plugins/README.md` | Marketplace плагинов |

### B.5 Storage (data_13/)

| Файл | Назначение |
|------|-----------|
| `forge_registry.yaml` (1519 строк) | Статусы проектов + pipeline history (interior-planner DEPLOYED и др.) |
| `missing_registry.yaml` (72 строки) | 7 записей register-first |
| `context.db`, `collaboration.db`, `metrics.db`, `presence.db`, `project_pulse.db`, `roles.db`, `verifier.db` | SQLite доменов |

### B.6 Проекты (projects_17/)

`content_factory` (концепты CI), `interior_planner` (реальный Forge-chain проект: RUNNABLE/CHECKLIST + roles/), `vkusvill_demo`, `vkusvill_research`, `lead_aggregator` (ADR-001…003), `diet_platform`, `tg_terminal_messenger`, `realtor_os` и др.

---

## C. REAL EXECUTION PATH

### C.1 Path 1 — Forge chain (production, ядро CI-конвейера)

```
PROJECT (projects_17/<slug>)
  ↓
ForgeFacade.run_chain(project)            core_02/forge_facade.py (14 ролей PIPELINE_CHAIN)
  ↓ Pre-flight: validate_role_artifacts() → RoleArtifactValidator.validate()
  ├─ LIGHT (explainer/lisa/risk/decomposer/architect/auditor/documenter/retrospective)
  │    └─ check_only (existence артефактов, registry.yaml → DEFAULT_ROLE_OUTPUTS fallback)
  ├─ HEAVY (developer/tester/fixer/acceptance) → initiate_forge() → ForgePipeline.run()
  │    └─ FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT (shell=False, argv-list)
  ├─ CONDITIONAL: frontend (project.type=="web") / devops (always)
  ↓
ChainRun (stage_count, overall, validation_summary)
  ↓
ForgeRegistry.record_run(project_id, run)  → status UNFORGED→DEPLOYED/FAILED, pipeline_history
  ↓
data_13/forge_registry.yaml
```

**Evidence:** `core_02/forge_facade.py::ForgeFacade.run_chain/initiate_forge`, `PIPELINE_CHAIN` (14 ролей), `RoleArtifactValidator.validate`, `forge_registry.record_run`. CLI: `scripts_01/forge.py chain <slug> --json`.

### C.2 Path 2 — Prompt dispatch (task queue, TG-вход)

```
telegram_bot.py /task <text>   → prompt_queue (user/*.md)
  ↓
prompt_dispatcher.dispatch_one/dispatch_all
  ↓ wrapper.launch_and_wait (phase-based, OOM-safe) → freebuff CLI сессия
  ↓ .freebuff_result → running/ → multi-turn (append_iteration, pending_task)
  ↓ cron-тика (*/5) → resumable
```

**Evidence:** `scripts_01/prompt_dispatcher.py::dispatch_one/dispatch_all`, `prompt_queue.py`, `telegram_bot.py`.

### C.3 Path 3 — MCP / HTTP (внешний API)

```
uvicorn mcp_fastapi :8765 → mcp_server (52 tools) / forge_interactive_api (/api/interactive/v1)
  ↓ POST /projects/{slug***REMOVED***/chain → forge.py chain --json (sync/async+SSE)
```

**Evidence:** `mcp_fastapi.py`, `mcp_server.py`, `forge_interactive_api.py`.

### C.4 Path 4 — Scenario discovery (SELECT SCENARIO)

```
ScenarioRegistry._load_from_dir(runtime_05/scenarios/*.yaml)
  → ScenarioManifest.from_yaml → BlueprintCorpus (BlueprintScenario)
  → find_role / propose_roles (fuzzy-match) → wizard.py --scenario
```

**Evidence:** `core_02/scenario_registry.py::_load_from_dir/_instantiate/find_role/propose_roles`.

---

## D. ARCHITECTURAL PRIMITIVES

| Concept | Status | Evidence | Actual implementation |
|---------|--------|----------|----------------------|
| AGENT | ✅ CONFIRMED | `scripts_01/distributed_agents.py::AgentMesh` (register/register_agent/run_distributed_workflow) | AgentMesh, distributed agents |
| RUNTIME | ✅ CONFIRMED | `runtime_05/providers/*.yaml` (freebuff/claude_code/openclaw) | Runtime marketplace (YAML-плагины) |
| WORKFLOW | ✅ CONFIRMED | `prompt_dispatcher.py`, `prompt_queue.py` | Очередь задач, cron, multi-turn |
| SCENARIO | ✅ CONFIRMED | `scenario_registry.py`, `runtime_05/scenarios/` | ScenarioRegistry + YAML-манифесты |
| FACTORY | 🟡 PARTIAL | `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` (дизайн FactoryRegistry, Missing #1) | Дизайн готов, кода НЕТ → **G2** |
| FORGE | ✅ CONFIRMED | `forge_facade.py`, `forge_pipeline.py`, `forge_registry.py` | ForgePipeline + 14 ролей chain |
| MEMORY | ✅ CONFIRMED | `memory_engine.py` (5 уровней JSON), `memory_store.py` (SQLite) | MemoryEngine/MemoryStore |
| KNOWLEDGE | ✅ CONFIRMED | `knowledge_engine.py` (FTS5+TF-IDF+SVD), `graph_index.py` | KnowledgeEngine/GraphIndex |
| EVENT | ✅ CONFIRMED | `event_bus.py`, `context_12/events.db` | EventBus (publish/subscribe) |
| TASK | ✅ CONFIRMED | `task_manager.py`, `prompt_queue.py` | Менеджер задач |
| PROJECT | ✅ CONFIRMED | `workspace.py::Project` | L-2 контейнер |
| WORKSPACE | ✅ CONFIRMED | `workspace_registry.py`, `data_13/context.db` | WorkspaceRegistry |
| STORAGE | ✅ CONFIRMED | `data_13/*.yaml + *.db`, `context_12/` | YAML+SQLite |
| OBSERVATION | 🟡 PARTIAL | `project_pulse.py`, `learning_loop.py` (kind=observation) | Наблюдение есть; «сигнал→opportunity» НЕТ |
| SCHEDULER | ✅ CONFIRMED | cron `prompt_dispatch.sh`, `auto_continue.sh`, `prompt_dispatcher.py --once` | Cron-тика |
| MONITORING | 🟡 PARTIAL | `project_pulse.py`, `system_monitor.py`, `presence.py` | Наблюдение за git/files, нет CI-анализа |
| TOOL | ✅ CONFIRMED | `tool_runtime.py`, `research_web.py`, `lisa_estimator.py` | Tool runtime + 2 implemented CI-tools |
| PLUGIN | ✅ CONFIRMED | `freebuff_plugin_03/`, `plugin_api.py` | Плагины |
| EXTENSION | 🟡 PARTIAL | `plugin_contract.py`, `freebuff_plugin_03/INTEGRATION_CONTRACT.md` | Контрактная интеграция |
| **WHIM / OPPORTUNITY** | ❌ **ABSENT** | grep: 0 совпадений в core_02/scripts_01; только концепты content_factory + дизайн SCENARIO_ENGINE_DESIGN | **→ G3** |

---

## E. FACTORY / FORGE / SCENARIO ANALYSIS

| Existing terminology | Actual responsibility | Possible conceptual mapping | Evidence |
|----------------------|----------------------|-----------------------------|----------|
| **ForgeRegistry / ForgePipeline / ForgeFacade** | Производство: статусы проектов, 6-стадийный pipeline, 14 ролей chain | **FORGE** (переиспользуемый capability с единственным результатом, карта v1.1 §5) | `forge_registry.py`, `forge_pipeline.py`, `forge_facade.py` |
| **ScenarioRegistry + wizard** | Каталог сценариев, роли, выбор по запросу | **SCENARIO** (композитор, v1.1 §14 — вне Factory) | `scenario_registry.py`, `runtime_05/scenarios/` |
| **FORGE_PASSPORT_CODE_REPRESENTATION_V1.md** (дизайн) | Машиночитаемые паспорта кузен + FactoryRegistry | **FACTORY** (6 блоков: Governance/Registry/Knowledge/Production/Quality/Interfaces, v1.1 §4) | Дизайн-документ; Missing Capability #1 |
| **research_web / lisa_estimator** | Веб-исследование, оценка сложности | **Capability-инструменты Research Factory** | `scripts_01/research_web.py`, `lisa_estimator.py` (Missing #6/#7) |

**Вывод E:** существующая архитектура НЕ требует переименования — терминология промта 1 (Factory/Forge/Scenario) дословно совпадает с канонической картой v1.1. Factory — единственная сущность, существующая только в дизайне (G2).

---

## F. CONTENT INTELLIGENCE COMPATIBILITY

Что УЖЕ можно использовать для CI (без изменений):

| CI-функция | Существующий механизм | Путь |
|-----------|----------------------|------|
| **OBSERVE** | `project_pulse.py` (scan_git/scan_files), `event_bus.py` | Импортировать/подписаться |
| **COLLECT** | `prompt_queue.py`, `memory_engine.py`, `knowledge_engine.py` | Импортировать |
| **UNDERSTAND** | `knowledge_engine.search` (hybrid), `semantic_layer.py`, `learning_loop.py` | Импортировать |
| **CONNECT** | `graph_index.py`, `memory_store.py` (knowledge_links) | Импортировать |
| **SELECT SCENARIO** | `scenario_registry.propose_roles/list_scenarios` | Импортировать + G1-адаптер |
| **EXECUTE** | `forge_facade.run_chain/initiate_forge` (14 ролей) | Импортировать (единственный мост) |
| **VALIDATE** | `RoleArtifactValidator`, `drift_check`, `consistency_check` | Импортировать |
| **ACCUMULATE** | `memory_store.store_knowledge`, `learning_loop` | Импортировать |
| **Register-first** | `missing_registry.py` (CLI+check) | Импортировать для G3 |

**Что НЕ существует (G3):** Opportunity Engine (DISCOVER+PROPOSE), Whim-захват.

---

## G. INTEGRATION GAPS (G0–G4)

| Capability | Existing | Evidence | Reusable | Gap |
|-----------|----------|----------|:--------:|:---:|
| Project context | ✅ | `workspace.py::Project`, `workspace_registry.py` | Да | G0 |
| Agent attachment | ✅ | `distributed_agents.py::AgentMesh`, `runtime_05/providers/` | Да | G0 |
| Chat | ✅ | `telegram_bot.py`, `core_02/telegram_contract.py` (chat_id, send_to_chat), `prompt_dispatcher` | Да | G0 |
| Memory | ✅ | `memory_engine.py` (5 уровней), `memory_store.py` (SQLite) | Да | G0 |
| **Whim-like capture** | ❌ | НЕТ (grep 0) | — | **G3** |
| Knowledge | ✅ | `knowledge_engine.py`, `graph_index.py`, `semantic_layer.py` | Да | G0 |
| Event system | ✅ | `event_bus.py`, `context_12/events.db` | Да | G0 |
| Scheduler | ✅ | cron `prompt_dispatch.sh`, `prompt_dispatcher.py --once` | Да | G0 |
| Monitoring | 🟡 | `project_pulse.py`, `system_monitor.py` | Да (расширить) | G1 |
| Scenario execution | ✅ | `scenario_registry.py` + `forge_facade.run_chain()` | Да | G0 |
| Factory | 🟡 | Дизайн `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md`; кода нет | Нет пока | **G2** |
| Forge | ✅ | `forge_pipeline.py`, `forge_facade.py`, `forge_registry.py` | Да | G0 |
| Storage | ✅ | `data_13/*.yaml + *.db`, `context_12/` | Да | G0 |
| **Opportunity tracking** | ❌ | НЕТ (только дизайн SCENARIO_ENGINE_DESIGN §Opportunity) | — | **G3** |

**Итог:** 10×G0, 1×G1, 1×G2, 2×G3, 0×G4. *(База счёта — таблица capabilities промта §14. Счёт по шагам модели CI §8 (7×G0 + SELECT G0/G1 + 2×G3 + G2) — см. FORENSICS_CI_GAP_MAP_V1.md §0.)*

---

## H. ARCHITECTURAL CONFLICTS

**G4 = 0.** Реальных конфликтов, подтверждённых repository, не обнаружено:

1. **Терминология канонична** — Factory/Forge/Scenario промта 1 дословно совпадают с картой v1.1 (ARB-REV-003); naming collision ARB-REV-001 не применим.
2. **`ForgeFacade` — единственный мост** (§7.3) — CI будет вызывать Forge только через `initiate_forge()`, «Direct Forge call из Scenario — НЕТ» сохранён.
3. **Новые сущности CI (Opportunity/Whim)** не пересекаются с B1–B14 границами и существующими реестрами.

---

## I. MINIMAL INTEGRATION MODEL

```
EXISTING PLATFORM (Registry/Scenario/Forge/Knowledge/Event — G0)
        +
MINIMAL CI LAYER (3 новые сущности, register-first)
        ├── Whim capture (G3, module)     — лёгкий вход мыслей, DEFERRED ≠ DELETED
        ├── Opportunity Engine (G3, engine) — DISCOVER (project_pulse/event_bus/knowledge) →
        │     Opportunity lifecycle (ACTIVE/DEFERRED/READY/REACTIVATED) → PROPOSE
        └── FactoryRegistry (G2, registry)  — машиночитаемые паспорта кузен (ForgePassport)
        +
EXISTING SELECT/EXECUTE/VALIDATE (ScenarioRegistry → ForgeFacade → RoleArtifactValidator → MemoryStore)
```

Принцип (§17 промта): НЕ создаём новую платформу внутри платформы. Intelligence-слой — композитор поверх существующих G0-механизмов, вызывающий Forge только через `ForgeFacade`.

---

## J. FIRST CONTENT VERTICAL SLICE

**Слайс:** «Контентная возможность → производство артефакта» (минимальная интеллектуальная голова + существующий хвост).

| Элемент | Детали |
|---------|--------|
| **Вход** | Один Whim/сигнал (текст мысли) ИЛИ обнаруженная тема из `project_pulse`/`knowledge_engine` |
| **Существующие компоненты** | `scenario_registry.py` (SELECT), `forge_facade.run_chain` (EXECUTE, 14 ролей), `RoleArtifactValidator` (VALIDATE), `memory_store` (ACCUMULATE), `missing_registry` (register-first) |
| **Новые компоненты** | `whim_capture` (module, G3) → `opportunity_engine` (engine, G3: lifecycle + DISCOVER + PROPOSE) |
| **Execution path** | `Whim → Opportunity Engine → SELECT SCENARIO (ScenarioRegistry) → EXECUTE (ForgeFacade.run_chain) → VALIDATE (RoleArtifactValidator) → ACCUMULATE (MemoryStore)` |
| **Результат** | Контентный артефакт (статья/пост/план) + запись в `memory_store` + статус opportunity (COMPLETED) |
| **Критерий успеха** | Полный цикл «сигнал → возможность → сценарий → артефакт → память» работает read-only на существующем хвосте; новый код — только 2 сущности головы |

---

## K. IMPLEMENTATION READINESS

### 🟢 READY WITH ADAPTER

**Обоснование:**
- Исполняемый слой CI (Scenario → ForgeFacade → валидация → память) **реализован и работает** — READY.
- Требуются адаптеры (G1): мониторинг→CI-сигналы (`project_pulse` → opportunity-вход), SELECT по opportunity (обёртка над `scenario_registry.propose_roles`).
- G3 (Opportunity Engine + Whim) и G2 (FactoryRegistry) — новые, но **небольшие** (2 сущности головы + 1 реестр), не затрагивают существующий код (аддитивно).

**Почему не NOT READY:** не нужен переписывать конвейер — он уже работает на реальных проектах (interior_planner DEPLOYED, vkusvill_demo).
**Почему не полный READY:** G3-примитивы (Opportunity/Whim) отсутствуют и должны быть построены (register-first → промт → mark-implemented).

---

*Forensics выполнена по методологии промта 1: repository = источник истины, evidence-правило §20 (каждое утверждение — path+symbol), G0–G4 §16, выход A–K §19. Прецеденты: ARB-REV-004, FORENSICS_CI_GAP_MAP_V1.md. Связанные документы: FACTORY_FORGE_ARCHITECTURE_V1.md (v1.1), SCENARIO_ENGINE_DESIGN_V1.md, FORGE_PASSPORT_CODE_REPRESENTATION_V1.md.*


**REPOSITORY FORENSICS COMPLETE — IMPLEMENTATION NOT STARTED.**
