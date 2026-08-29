# EVIDENCE_LEDGER_MERGED.md — Слитый журнал доказательств (104/105/106/107)

> Формат: CLAIM → FILE → SYMBOL → BEHAVIOR. Слито из EVIDENCE_LEDGER.md (104),
> 12_EVIDENCE_LEDGER.md (106), EVIDENCE_LEDGER.md (107). Источник каждого claim указан.

## Forge-слой

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| Workspace L-1 контейнер | core_02/workspace.py | `Workspace` | load() из workspace.yaml; validate() → WorkspaceHealth | 107 |
| Project L-2 контейнер | core_02/workspace.py | `Project` | load() из project.yaml; get_requirements() | 107 |
| ForgePipeline 6 стадий | core_02/forge_pipeline.py | `ForgePipeline` | run() → stage_forge/check/build/test/deploy/report | 107 |
| BUILD/TEST = subprocess | core_02/forge_pipeline.py | `_run_cmd` | subprocess.run(cmd, cwd=project.root, timeout) | 107 |
| ForgeRegistry статусы | core_02/forge_registry.py | `ForgeRegistry` | UNFORGED..DEPLOYED; record_run() | 107 |
| B10 schema validation | core_02/forge_registry.py | `validate_schema` | UNFORGED⇒no last_run; DEPLOYED/FAILED⇒last_run set | 107 |
| State-drift guard | core_02/forge_registry.py | `_is_ephemeral_leak` | _save() фильтрует mock /tmp-root записи | 107 |
| ForgeFacade gate | core_02/forge_facade.py | `can_initiate` | только role_id ∈ PIPELINE_ROLES | 107 |
| Chain-runner | core_02/forge_facade.py | `run_chain` | 14 ролей LIGHT/HEAVY/CONDITIONAL | 107 |
| Forge = production pipeline, не runtime | core_02/forge_* | — | Forge НЕ исполняет пользовательские запросы (RFC §12) | 104 |
| Pipeline-роли stateless | core_02/forge_facade.py | `PIPELINE_ROLES` | нет lifecycle created/ready/running | 104 |

## Scenario / Factory

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| Scenario = role corpus (ABC) | core_02/scenario.py | `Scenario` | role_objects/load_role_text/routing_hint | 107 |
| Scenario auto-discovery | core_02/scenario_registry.py | `ScenarioRegistry` | runtime_05/scenarios/*.yaml | 107 |
| Factory = CLI entry-point | core_02/factory_base.py | `BaseFactory` | main(), make_argparser(), _cli_run() | 107 |
| Factory auto-discovery | core_02/factory_registry.py | `FactoryRegistry` | runtime_05/factories/*/ | 107 |
| Factory forge-selection | core_02/factory_registry.py | `select_forge` | capability → (Factory, Forge) по status-rank | 107 |
| 4 реальные фабрики | runtime_05/factories/ | (dirs) | architecture, content, research, test | 107 |
| Factory→Forge execution СШИТ (Path B REAL) | scripts_01/opportunity_engine.py | `execute()` | `_select_factory_forge` → `select_forge(capability)` (запись `provenance['factory_selection'***REMOVED***`) → `facade.run_chain(project, role_ids)` (строка 941) | 107 §G + code-verif 2026-08-22 |
| Factory→Forge execution СШИТ (BaseFactory) | core_02/factory_base.py | `BaseFactory.execute()` | `resolve()` → `select_forge` → `build_execution_request` → `facade.run_chain(project, role_ids=request.role_ids, project_read_only=True)` (строка 361) | code-verif 2026-08-22 |
| Factory→Forge execution СШИТ (chain-CLI) | scripts_01/forge.py | `cmd_chain` | `facade.run_chain(...)` (строка 490) — третий независимый вызов | code-verif 2026-08-22 |
| forge_id адвизорный (не дыра) | scripts_01/opportunity_engine.py | `execute()` | исполнение идёт по role_ids сценария; forge_id из паспорта — traceability; в системе единый ForgeFacade/ForgePipeline | code-verif 2026-08-22 |

## Intelligence / Model / Role

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| Scenario decision | scripts_01/scenario_intelligence.py | `ScenarioIntelligence` | EVAL_WEIGHTS .35/.25/.20/.20 | 107 |
| Capability routing | core_02/router.py | `SmartRouter.route` | required_capabilities → best model | 107 |
| Model catalog | core_02/router.py | `ModelCatalog.default` | 6 моделей | 107 |
| Model execution | scripts_01/model_gateway.py | `ModelGateway` | OpenAICompatible/Gemini/Ollama | 107 |
| Role #1 (pipeline) | core_02/blueprint_v3.py | `BlueprintCorpus` | 14-17 ролей | 107 |
| Role #2 (collab) | scripts_01/roles.py | `RoleEngine` | 6 ролей, SQLite | 107 |
| ROLE ≠ PROJECT ROLE смешано | scripts_01/roles.py | `get_collab_role` | agent-роль → owner/editor/viewer | 107 §E |

## Task / Tool / Memory

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| Task #1 | scripts_01/task_manager.py | (CRUD) | SQLite tasks | 107 |
| Task #2 | scripts_01/orchestrator.py | `Orchestrator` | Workflow/Step/ToolExecutor | 107 |
| Tool #1 | scripts_01/tool_runtime.py | `ToolRegistry` | Git/SQLite/HTTP/File/Shell | 107 |
| Tool #2 | scripts_01/mcp_server.py | `BuffyMcpServer` | McpTool/McpResource/McpPrompt | 107 |
| ShellTool (риск) | scripts_01/tool_runtime.py | `ShellTool.run` | subprocess.run(cmd), без sandbox | 107 |
| Memory ×4 | scripts_01/{memory,knowledge***REMOVED***_engine.py, graph_index.py, engineering_memory.py | — | конкурирующие движки | 107 |

## Integration / Security

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| MCP HTTP auth (Vault) | scripts_01/mcp_fastapi.py | `_get_active_token` | Bearer + TTL + env fallback | 107 |
| MCP server без auth | scripts_01/mcp_server.py | `handle_tools_call` | диспатч без auth (stdio-local) | 107 |
| Privacy guard | core_02/workspace_registry.py | `assert_path_privacy` | PrivacyViolationError | 107 |
| Integration adapter boundary (РЕАЛИЗОВАН) | core_02/integration_base.py | `IntegrationAdapter` | ABC: AuthSpec (5 методов) + intent→capability (закрытый словарь) + call_platform (SmartRouter, §7.3) + log_event + нормализованный вход/выход; 33 hermetic теста | ADR-020 (v5.189.81) |
| Agent base class + lifecycle (РЕАЛИЗОВАН) | core_02/agent_base.py | `Agent` (ABC) + `AgentLifecycle` | CREATED→ACTIVE→PAUSED→DONE/FAILED forward-only DAG; KNOWN_CAPABILITIES closed set (ANTI-6b); route_model (SmartRouter) / run_forge (ForgeFacade) сервисы; AgentResult; 29 hermetic тестов | ADR-019 (v5.189.80) |
| Внешние мосты вшиты в ядро | core_02/telegram_contract.py, scripts_01/phone_control_mcp.py | — | нет adapter-границы | 107 §L |
| Концептуальная граница Platform/Project есть, физической нет | projects_17/*, core_02/* | — | импорты project→platform, общая память | 105 |

## Repository

| Claim | File | Symbol | Behavior | Source |
|-------|------|--------|----------|--------|
| Нумерация каталогов = историческая | (top-level) | dirs 01-33 | порядок появления, не слои | 105 |
| Домены размазаны | scripts_01/, core_02/, runtime_05/ | — | Intelligence/factories в нескольких местах | 105 |
| Code/docs/prompts/tests/data смешаны | корень | — | *.md в корне рядом с каталогами | 105/107 |
