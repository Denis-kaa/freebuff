# EVIDENCE LEDGER — promt107 forensic

> Формат: CLAIM → FILE → SYMBOL → BEHAVIOR. Каждое утверждение подтверждено кодом.

## Forge-слой

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| Workspace L-1 контейнер | core_02/workspace.py | `Workspace` | `load()` из workspace.yaml; `validate()` → WorkspaceHealth |
| Project L-2 контейнер | core_02/workspace.py | `Project` | `load()` из project.yaml; `get_requirements()`, `append_step()` |
| ForgePipeline 6 стадий | core_02/forge_pipeline.py | `ForgePipeline` | `run()` → stage_forge/check/build/test/deploy/report |
| BUILD/TEST = subprocess | core_02/forge_pipeline.py | `_run_cmd` | `subprocess.run(cmd, cwd=project.root, timeout)` |
| ForgeRegistry статусы | core_02/forge_registry.py | `ForgeRegistry` | `register_project`, `record_run`; статусы UNFORGED..DEPLOYED |
| B10 schema validation | core_02/forge_registry.py | `validate_schema` | UNFORGED⇒last_run_at None; DEPLOYED/FAILED⇒last_run_at set |
| State-drift guard | core_02/forge_registry.py | `_is_ephemeral_leak` | `_save()` фильтрует mock-записи с root под /tmp |
| ForgeFacade gate | core_02/forge_facade.py | `ForgeFacade.can_initiate` | только role_id ∈ PIPELINE_ROLES |
| Chain-runner | core_02/forge_facade.py | `run_chain` | 14 ролей: LIGHT (check_only) / HEAVY (full_cycle) / CONDITIONAL |

## Scenario / Factory

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| Scenario = role corpus (ABC) | core_02/scenario.py | `Scenario` | `role_objects()`, `load_role_text()`, `routing_hint()` |
| Scenario auto-discovery | core_02/scenario_registry.py | `ScenarioRegistry` | `_load_from_dir` из runtime_05/scenarios/*.yaml |
| Factory = CLI entry-point | core_02/factory_base.py | `BaseFactory` | `main()`, `make_argparser()`, `_cli_run()` |
| Factory auto-discovery | core_02/factory_registry.py | `FactoryRegistry` | `_reload` из runtime_05/factories/*/ |
| Factory forge-selection | core_02/factory_registry.py | `select_forge` | capability → (FactoryPassport, ForgePassport) по status-rank |
| 4 реальные фабрики | runtime_05/factories/ | (dirs) | architecture, content, research, test |

## Intelligence / Model / Role / Task / Tool

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| Scenario decision | scripts_01/scenario_intelligence.py | `ScenarioIntelligence` | EVAL_WEIGHTS: relevance .35, capability .25, history .20, feasibility .20 |
| Capability routing | core_02/router.py | `SmartRouter.route` | required_capabilities → best model; fallback_used flag |
| Model catalog | core_02/router.py | `ModelCatalog.default` | 6 моделей (qwen ×2, deepseek ×2, gemini, llama) |
| Model execution | scripts_01/model_gateway.py | `ModelGateway` | providers: OpenAICompatible/Gemini/Ollama |
| Role #1 (pipeline) | core_02/blueprint_v3.py | `BlueprintCorpus` | 14-17 pipeline-ролей, registry.yaml + role .md |
| Role #2 (collab) | scripts_01/roles.py | `RoleEngine` | 6 ролей (orchestrator/developer/reviewer/documenter/researcher/archiver), SQLite |
| Role execution | core_02/role_executor.py | `RoleExecutorRegistry` | LisaExecutor + LlmRoleExecutor |
| Task #1 | scripts_01/task_manager.py | (CRUD functions) | SQLite tasks + LLM-брифинг |
| Task #2 | scripts_01/orchestrator.py | `Orchestrator` | Workflow/Step/ToolExecutor/DefaultPlanner |
| Tool #1 | scripts_01/tool_runtime.py | `ToolRegistry` | Git/SQLite/HTTP/File/ShellTool |
| Tool #2 | scripts_01/mcp_server.py | `BuffyMcpServer` | McpTool/McpResource/McpPrompt |
| Shell tool | scripts_01/tool_runtime.py | `ShellTool.run` | `subprocess.run(cmd)` — риск, не sandbox |

## Memory / Knowledge / State

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| Memory #1 | scripts_01/memory_engine.py | `MemoryEngine` | MemoryLevel L1-L3 |
| Knowledge #2 | scripts_01/knowledge_engine.py | `KnowledgeEngine` | Fts/Tfidf/Semantic index |
| Graph #3 | scripts_01/graph_index.py | `GraphIndex` | Node/Edge/PathResult |
| Memory #4 | scripts_01/engineering_memory.py | (module) | engineering memory artifacts |
| Event bus | scripts_01/event_bus.py | `EventBus` | publish/subscribe + EventLogEntry |
| Whim | scripts_01/whim_capture.py | `WhimStore` | capture → whims.yaml |
| Opportunity | scripts_01/opportunity_engine.py | `OpportunityStore` | detect/rank/execute |

## Integration / Security

| Claim | File | Symbol | Behavior |
|-------|------|--------|----------|
| MCP HTTP auth | scripts_01/mcp_fastapi.py | `_get_active_token` | Vault approle login → Bearer; TTL cache; env fallback |
| MCP server (no auth) | scripts_01/mcp_server.py | `BuffyMcpServer.handle_tools_call` | диспатч tools без auth |
| TG wrapper | core_02/telegram_contract.py | (module) | send_to saved/litvinov |
| Remote sync | core_02/remote_sync.py | `RemoteSyncCoordinatorImpl` | push_state → TG |
| Phone MCP | scripts_01/phone_control_mcp.py | `SendSmsTool` | custom input_schema (НЕ pydantic) |
