# RESPONSIBILITY MATRIX — promt107 forensic

> Метод: CODE-first. Статусы: CONFIRMED / PARTIAL / DOCUMENTED ONLY / DUPLICATED / CONFLICTING / MISSING / UNCLEAR.

## Core responsibility matrix

| Component | Actual responsibility | Evidence (file → symbol) | Inputs | Outputs | Calls | Called by | Status |
|-----------|----------------------|--------------------------|--------|---------|-------|-----------|--------|
| Workspace (L-1) | YAML-контейнер верхнего уровня: root, projects, steps_policy | core_02/workspace.py::Workspace | workspace.yaml | list[Project***REMOVED*** | Project.load | Forge, CLI | CONFIRMED |
| Project (L-2) | Изолированный проект: конфиг, требования, env-doctor, STEPS | core_02/workspace.py::Project | project.yaml | ProjectRequirements, StepsStats | run_env_doctor | ForgePipeline, ForgeFacade | CONFIRMED |
| WorkspaceRegistry | SQLite workspace↔project + privacy guard | core_02/workspace_registry.py::WorkspaceRegistry | context.db | Workspace/Project rows | add_project | scan_projects | DUPLICATED (vs workspace.py) |
| ForgePipeline (L-3) | 6-стадийный build pipeline | core_02/forge_pipeline.py::ForgePipeline | Project | PipelineRun | stage_* | ForgeFacade, forge.py | CONFIRMED |
| ForgeRegistry (L-4) | YAML-реестр статусов проектов | core_02/forge_registry.py::ForgeRegistry | forge_registry.yaml | ForgeStatus | register_project, record_run | ForgeFacade, forge.py | CONFIRMED |
| ForgeFacade | Единственный мост роль→Forge | core_02/forge_facade.py::ForgeFacade | Project, role_id | ForgeFacadeResult, ChainRun | initiate_forge, run_chain | cmd_chain | CONFIRMED |
| RoleArtifactValidator | Проверка existence артефактов ролей | core_02/forge_facade.py::RoleArtifactValidator | Project | ValidationSummary | validate | ForgeFacade | CONFIRMED |
| Scenario (ABC) | Role corpus: role_objects/load_role_text/routing_hint | core_02/scenario.py::Scenario | YAML manifest | Role list | — | ScenarioRegistry | CONFIRMED |
| ScenarioRegistry | Auto-discovery + cross-scenario search | core_02/scenario_registry.py::ScenarioRegistry | runtime_05/scenarios/*.yaml | Scenarios | find_role, propose_roles | wizard | CONFIRMED |
| BlueprintCorpus | Конкретный role-corpus (Blueprint v3, 14-17 ролей) | core_02/blueprint_v3.py::BlueprintCorpus | registry.yaml + role .md | Role | roles(), routing_hint | ScenarioRegistry | CONFIRMED |
| FactoryRegistry | Auto-discovery factories + forge passports | core_02/factory_registry.py::FactoryRegistry | runtime_05/factories/* | FactoryPassport, ForgePassport | select_forge | (scenario bridge) | CONFIRMED |
| BaseFactory | CLI-ориентированная база фабрики | core_02/factory_base.py::BaseFactory | args | JSON/text | main(), _cli_run | research/content/test factory | PARTIAL (не runtime-сервис) |
| ScenarioIntelligence | Decision/coordination: выбор scenario по весам | scripts_01/scenario_intelligence.py::ScenarioIntelligence | candidates, history | ScenarioDecision | evaluate | (CLI, events) | CONFIRMED |
| SmartRouter / ModelCatalog | Capability-based выбор модели | core_02/router.py::SmartRouter | required_capabilities | RouteDecision | route | wizard, model_gateway | CONFIRMED |
| ModelGateway | Реальный вызов провайдеров | scripts_01/model_gateway.py::ModelGateway | prompt, model | ModelResponse | call | CLI, forge | CONFIRMED |
| RoleEngine | Collab-роли участников (SQLite) | scripts_01/roles.py::RoleEngine | roles.db | AgentRole | assign_role | MCP, CLI | DUPLICATED (vs pipeline-роли) |
| BaseRoleExecutor / Registry | Выполнение роли (LISA/LLM) | core_02/role_executor.py::RoleExecutorRegistry | role_id | files | execute | ForgeFacade | CONFIRMED |
| ToolRegistry / BaseTool | 5 tool'ов (Git/SQLite/HTTP/File/Shell) | scripts_01/tool_runtime.py::ToolRegistry | tool call | ToolResult | run | MCP? | DUPLICATED (vs mcp_server tools) |
| Orchestrator | Workflow/Step/ToolExecutor/Planner | scripts_01/orchestrator.py::Orchestrator | Workflow | WorkflowStatus | run | CLI | DUPLICATED (vs task_manager) |
| TaskManager | SQLite задачи + LLM-брифинг | scripts_01/task_manager.py | context.db | Task | CRUD | CLI, TG | DUPLICATED (vs orchestrator) |
| MemoryEngine | L1-L3 memory levels | scripts_01/memory_engine.py::MemoryEngine | memory.db | MemoryEntry | store/recall | — | DUPLICATED (×4) |
| KnowledgeEngine | FTS/TFIDF/Semantic index | scripts_01/knowledge_engine.py::KnowledgeEngine | docs | SearchResult | search | RAG | DUPLICATED (×4) |
| GraphIndex | Node/Edge graph | scripts_01/graph_index.py::GraphIndex | entities | PathResult | link | — | DUPLICATED (×4) |
| EventBus | Pub/sub событий | scripts_01/event_bus.py::EventBus | Event | subscribers | publish | scenario_intelligence | CONFIRMED |
| WhimStore | Захват мыслей до проекта | scripts_01/whim_capture.py::WhimStore | whims.yaml | Whim | capture | CLI | CONFIRMED |
| OpportunityStore | Обнаружение/ранжирование возможностей | scripts_01/opportunity_engine.py::OpportunityStore | opportunities.yaml | Opportunity | detect/rank | CLI | CONFIRMED |
| BuffyMcpServer | MCP server (tools/resources/prompts) | scripts_01/mcp_server.py::BuffyMcpServer | JSON-RPC | responses | handle_tools_call | external | CONFIRMED |
| AgentContextBridge | Мост контекста агента | scripts_01/agent_context_bridge.py::AgentContextBridge | — | context | get_context | — | PARTIAL |

## E. Agent / Model / Runtime / Role Map

```
HUMAN (CLI / TG / MCP)
   ↓
[НЕТ Agent-класса***REMOVED***  ← DOCUMENTED ONLY (AgentContextBridge — частичный мост)
   ↓
MODEL: ModelGateway (execution) + SmartRouter/ModelCatalog (selection)
   ↓
ROLE: (a) Blueprint pipeline-роли (14-17) — что умеет [AGENT ROLE***REMOVED***
        (b) roles.py collab-роли (6) — место в CoWork [СМЕШАНО с PROJECT ROLE***REMOVED***
   ↓
TASK: task_manager OR orchestrator (два механизма)
   ↓
TOOL: tool_runtime OR mcp_server (два механизма)
   ↓
CAPABILITY: closed-set токены (ModelCatalog.capabilities / passports / KNOWN_CAPABILITIES)
```

⚠️ **ROLE ≠ PROJECT ROLE НЕ разделено:** `roles.py` `get_collab_role()` маппит
agent-роль → collab-роль (orchestrator→owner, developer/reviewer→editor, иначе viewer) —
это смешение двух понятий в одном движке.

## F. Project / Workspace Model

- **Workspace** = 2 конкурирующие модели: YAML (`workspace.py`) и SQLite (`workspace_registry.py`).
- **Project** = YAML dataclass (L-2) + SQLite row (workspace_registry.py) — тоже дублируется.
- **Project Management (Owner/PM/Contributor/Reviewer/Observer)** — DOCUMENTED ONLY (promt107 §6),
  в коде только 6 collab-ролей roles.py + `owner_chat_id` в workspace_registry.
- **Scopes/permissions:** частично — `WorkspaceRegistry.assert_path_privacy` (path→workspace),
  `RoleEngine.get_collab_role` (role→editor/viewer/owner). Полной permission-модели НЕТ.
