# PLATFORM ARCHITECTURAL INVENTORY V1 — Forensic Report (promt107)

> **Статус:** FORENSIC FACT (CODE-first, read-only)
> **Метод:** promt107 §0 (CODE > TESTS > CONFIG > RUNTIME > DOCS > HYPOTHESIS)
> **Версия:** v5.189.72 · **Дата:** 2026-08-22

---

## A. Executive Summary

Платформа Freebuff / Workspace OS — это **работающая система механизмов**, но НЕ единая
архитектурная платформа. Есть явный, стабильный Forge-слой (Workspace→Project→Pipeline→Registry),
есть слой intelligence (ScenarioIntelligence), factory-манифесты (декларативные), и три
параллельных «концептуальных рельса», которые в коде **НЕ соединены сквозным контрактом**:

1. **Buffy Forge** (L-1 Workspace, L-2 Project, L-3 Pipeline, L-4 Registry) — реализован, тестируется.
2. **Scenario → Factory → Forge** (declarative manifests + passports) — частично реализован
   (ScenarioRegistry, FactoryRegistry, ForgePassport), но Factory-path `opportunity → capability →
   factory → forge` сшит лишь частично (select_forge / resolve_by_policy есть, но execution через
   BaseFactory не связан с ForgeFacade сквозным контрактом).
3. **CoWork/Companion** (Presence, Collaboration, Roles, Project Pulse, RAG) — реализован как
   набор отдельных SQLite-движков, НЕ связан с Forge-жизненным циклом проекта.

**Главный вывод (§27):** система = «набор работающих механизмов с частично связанными границами».
Что уже система: Forge-слой (контейнеры + pipeline + registry + facade). Что набор механизмов:
memory/knowledge/graph (несколько конкурирующих движков), roles (две независимые модели),
task/orchestration (два независимых механизма). Что только документация: полная модель
`Project → Scenario → Factory → Forge → Artifact` как единый сквозной конвейер.

---

## B. Current Reality Map

### B.1 Подтверждённые механизмы (CODE + TESTS)

| Механизм | Evidence (path → symbol) | Статус |
|----------|--------------------------|--------|
| Workspace (L-1) контейнер | `core_02/workspace.py::Workspace` | CONFIRMED |
| Project (L-2) контейнер | `core_02/workspace.py::Project` | CONFIRMED |
| Workspace↔Project privacy isolation | `core_02/workspace_registry.py::WorkspaceRegistry` + `PrivacyViolationError` | CONFIRMED |
| Forge Pipeline (L-3) | `core_02/forge_pipeline.py::ForgePipeline` (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT) | CONFIRMED |
| Forge Registry (L-4) | `core_02/forge_registry.py::ForgeRegistry` (UNFORGED..DEPLOYED) | CONFIRMED |
| Forge Facade (role→Forge мост) | `core_02/forge_facade.py::ForgeFacade.initiate_forge/run_chain` | CONFIRMED |
| Role executor | `core_02/role_executor.py::RoleExecutorRegistry/LisaExecutor/LlmRoleExecutor` | CONFIRMED |
| Capability-based model routing | `core_02/router.py::SmartRouter/ModelCatalog` | CONFIRMED |
| Scenario registry | `core_02/scenario_registry.py::ScenarioRegistry` | CONFIRMED |
| Factory registry | `core_02/factory_registry.py::FactoryRegistry` | CONFIRMED |
| Scenario intelligence (decision) | `scripts_01/scenario_intelligence.py::ScenarioIntelligence` | CONFIRMED |
| Model gateway (providers) | `scripts_01/model_gateway.py::ModelGateway` | CONFIRMED |
| Tool runtime | `scripts_01/tool_runtime.py::ToolRegistry/BaseTool` (Git/SQLite/HTTP/File/Shell) | CONFIRMED |
| Whim capture | `scripts_01/whim_capture.py::WhimStore` | CONFIRMED |
| Opportunity engine | `scripts_01/opportunity_engine.py::OpportunityStore` | CONFIRMED |
| Event bus | `scripts_01/event_bus.py::EventBus` | CONFIRMED |
| Memory engine | `scripts_01/memory_engine.py::MemoryEngine` | CONFIRMED |
| Knowledge engine | `scripts_01/knowledge_engine.py::KnowledgeEngine` | CONFIRMED |
| Graph index | `scripts_01/graph_index.py::GraphIndex` | CONFIRMED |
| MCP server | `scripts_01/mcp_server.py::BuffyMcpServer` | CONFIRMED |
| Orchestrator | `scripts_01/orchestrator.py::Orchestrator` | CONFIRMED |
| Task manager | `scripts_01/task_manager.py` (DB tasks) | CONFIRMED |
| Collaboration roles | `scripts_01/roles.py::RoleEngine` | CONFIRMED |

### B.2 Только документация / концептуально (DOCUMENTED ONLY)

| Концепт | Где документирован | Где в коде | Статус |
|---------|--------------------|-----------|--------|
| `Project → Scenario → Factory → Forge → Artifact` сквозной конвейер | RFC_BUFFY_FORGE_V1, research V1 | разрозненно (нет одного orchestration entry-point) | DOCUMENTED ONLY |
| Отдельный Integration/Connector/Adapter слой | promt107 §13 | вшито в ядро (telegram_contract, mcp_server, phone_control_mcp) | DOCUMENTED ONLY |
| AGENT как класс с lifecycle | AGENT_ARCHITECTURE.md (forensics v2) | нет `Agent` base class | DOCUMENTED ONLY |
| PROJECT ROLE (Owner/PM/Contributor) отдельно от AGENT ROLE | promt107 §5 | `roles.py` смешивает (6 collab-ролей = agent-роли) | DOCUMENTED ONLY |

---

## C. Component Inventory (фактическая ответственность)

### C.1 Forge-слой (самый зрелый)

- **`core_02/workspace.py`** — `Workspace` (L-1: root, projects, steps_policy) и
  `Project` (L-2: name, root, type, stack, roles, contracts, requirements). Реальные
  dataclass-контейнеры, загружаются из YAML.
- **`core_02/workspace_registry.py`** — **вторая, отдельная** модель Workspace (SQLite
  `data_13/context.db`, slug + privacy guard). ⚠️ **ДУБЛИРУЕТ** `workspace.py` (YAML vs SQLite).
- **`core_02/forge_pipeline.py`** — 6 стадий. Исполняет `subprocess` для BUILD/TEST.
- **`core_02/forge_registry.py`** — YAML-реестр статусов проектов. `validate_schema()` (R-127/B10).
  State-drift guard v5.189.71 фильтрует ephemeral mock-записи.
- **`core_02/forge_facade.py`** — единственный санкционированный мост роль→Forge.
  `initiate_forge()` + `run_chain()` (14 pipeline-ролей: LIGHT/HEAVY/CONDITIONAL).

### C.2 Scenario / Factory слой (частично реализован)

- **`core_02/scenario.py`** — `Scenario` ABC (role corpus: `role_objects()`, `load_role_text()`,
  `routing_hint()`). Единственный concrete = `BlueprintCorpus`.
- **`core_02/scenario_registry.py`** — auto-discovery YAML manifests.
- **`core_02/factory_base.py`** — `BaseFactory` + `ExecutionRequest` (CLI-ориентированный,
  `main()`/`make_argparser()`). Фабрики = **CLI-точки входа**, не runtime-сервисы.
- **`core_02/factory_registry.py`** — auto-discovery `runtime_05/factories/*/factory.yaml` +
  `<forge>.yaml` passports. `select_forge()` / `resolve_by_policy()` — селекция.
- **Фактические фабрики** (runtime_05/factories/): `architecture` (governance, review),
  `content` (writing), `research` (analysis), `test` (verifier).

### C.3 Intelligence / Decision

- **`scripts_01/scenario_intelligence.py`** — `ScenarioIntelligence` + `ScenarioDecision` +
  `DecisionHistoryStore`. Веса EVAL_WEIGHTS (релевантность 35%, возможности 25%, история 20%,
  реализуемость 20%). Это **decision/coordination механизм**, НЕ companion-agent.

### C.4 Agent / Model / Role / Runtime / Task / Tool / Capability

| Сущность | Фактическая реализация | Где |
|----------|------------------------|-----|
| MODEL | `ModelGateway` (providers) + `SmartRouter/ModelCatalog` (selection) | scripts_01/model_gateway.py, core_02/router.py |
| ROLE | **две независимые модели**: (1) pipeline-роли Blueprint v3 (14-17), (2) collab-роли roles.py (6) | core_02/blueprint_v3.py, scripts_01/roles.py |
| AGENT | НЕТ класса Agent. Есть `AgentContextBridge` (мост контекста) | scripts_01/agent_context_bridge.py |
| RUNTIME | Runtime Abstraction Layer (freebuff_plugin_03/runtime) + ToolRegistry | freebuff_plugin_03/, scripts_01/tool_runtime.py |
| TASK | `task_manager.py` (SQLite) И `orchestrator.py` (Workflow/Step) — **два** механизма | scripts_01/ |
| TOOL | `tool_runtime.py` (5 tools) И `mcp_server.py` (McpTool) — **два** механизма | scripts_01/ |
| CAPABILITY | closed-set токены: `ModelCatalog.capabilities`, `KNOWN_CAPABILITIES`, passports | core_02/router.py, factory_passport.py |

---

## D. Responsibility Matrix → см. `RESPONSIBILITY_MATRIX.md`

## E. Agent/Model/Runtime/Role Map → см. `RESPONSIBILITY_MATRIX.md` §E

## F. Project/Workspace Model → см. `RESPONSIBILITY_MATRIX.md` §F

## G–K. Scenario/Factory/Forge/Intelligence/Memory → см. детали в EVIDENCE_LEDGER.md

---

## L. Integration / Connector Architecture

**Факт:** отдельного integration-слоя НЕТ. Внешние мосты вшиты в ядро/скрипты:

| Мост | Механизм | Файл |
|------|----------|------|
| Telegram | `telegram_contract.py` (wrapper), `telegram_bot.py` (бот) | core_02/, scripts_01/ |
| MCP | `mcp_server.py` (BuffyMcpServer), `mcp_fastapi.py` (HTTP + Bearer/Vault) | scripts_01/ |
| Phone | `phone_control_mcp.py` (send_sms/get_contacts/play_music) | scripts_01/ |
| Remote sync | `remote_sync.py` (RemoteSyncCoordinator) | core_02/ |
| Web research | `research_web.py` | scripts_01/ |

⚠️ Внешняя система **уже является частью Workspace Core** для TG/MCP (нет adapter-границы).

---

## M. Security / Trust Boundary → см. `SECURITY_TRUST_BOUNDARY_MAP.md`

---

## N. Competing Abstractions → см. `COMPETING_ABSTRACTIONS.md`

Ключевые дубли:
1. **Workspace** ×2 (YAML `workspace.py` vs SQLite `workspace_registry.py`)
2. **Role model** ×2 (Blueprint pipeline-роли vs collab-роли)
3. **Task system** ×2 (task_manager vs orchestrator)
4. **Tool system** ×2 (tool_runtime vs mcp_server)
5. **Memory/Knowledge** ×4 (memory_engine, knowledge_engine, graph_index, engineering_memory)
6. **Registry** ×6 (workspace, scenario, factory, forge, missing, tool + role_executor)

---

## O. Contract Graph → см. `CONTRACT_GRAPH.md`

## P. Documentation↔Code Traceability → см. `TRACEABILITY_MAP.md`

## Q. Repository Structure Analysis → см. `REPOSITORY_TREE.md`

## R. Tagging / Semantic Traceability Assessment

Идея семантических тегов `[DOMAIN:FORGE***REMOVED***` и т.п. **НЕ внедрена** в коде. Существует
`doc_code_verify.py` (`extract_claims`, `check_symbol_exists`) — машинная проверка
doc↔code, но теги не используются для retrieval. **Вывод:** теги НЕ обязательны сейчас;
прежде — закрыть дублирующие registry и явные contract-границы.

## S. Target Architecture → см. `TARGET_ARCHITECTURE.md`

## T. Migration Architecture → см. `TARGET_ARCHITECTURE.md`

## U. Safe Refactoring Roadmap → см. `TARGET_ARCHITECTURE.md` §P0-P4

## V. Risks → см. `TARGET_ARCHITECTURE.md` §Risks

## W. Open Questions

1. Связать ли `workspace.py` (YAML) и `workspace_registry.py` (SQLite) в единый источник?
2. Нужен ли сквозной Factory-execution (opportunity → factory → forge) или ForgeFacade достаточен?
3. AGENT ROLE vs PROJECT ROLE — разделять или оставить 6 collab-ролей?
4. Единый Task/Tool mechanism или оставить два?
5. Выносить ли внешние мосты (TG/MCP/phone) в отдельный integration-слой?

## X. Implementation Readiness

- **Forge-слой:** готов (тесты, registry, facade, chain-runner).
- **Factory-execution:** частично (манифесты + passports + select_forge есть; сквозной
  `BaseFactory.execute → ForgeFacade` контракт НЕ сшит).
- **Integration-слой:** НЕ готов (мосты вшиты, адаптерной границы нет).
- **Project-role model:** НЕ готов (roles.py = agent-роли, project-роли отсутствуют).
