# TRACEABILITY MAP — Documentation ↔ Code ↔ Tests (promt107 §19)

> Цель: DOCUMENTED → IMPLEMENTED → TESTED → EXECUTABLE связь. Статусы как в matrix.

| Компонент | Документация | Код | Тесты | Статус |
|-----------|-------------|-----|-------|--------|
| Workspace (L-1) | RFC_BUFFY_FORGE_V1 §2a | core_02/workspace.py | test_workspace.py | CONFIRMED |
| Project (L-2) | RFC_BUFFY_FORGE_V1 §2a | core_02/workspace.py | test_workspace.py | CONFIRMED |
| WorkspaceRegistry + privacy | Phase 5.4 spec | core_02/workspace_registry.py | test_workspace_registry.py | CONFIRMED |
| ForgePipeline | RFC §3 | core_02/forge_pipeline.py | test_forge_pipeline.py | CONFIRMED |
| ForgeRegistry | RFC §4 | core_02/forge_registry.py | test_forge_registry.py | CONFIRMED |
| ForgeFacade | promt70 P3 | core_02/forge_facade.py | test_forge_facade.py, test_forge_chain_* | CONFIRMED |
| Scenario ABC | CON-9 LESSONS | core_02/scenario.py | test_scenario_registry.py | CONFIRMED |
| ScenarioRegistry | promt32 | core_02/scenario_registry.py | test_scenario_registry.py | CONFIRMED |
| BlueprintCorpus | Blueprint v3 MANIFEST | core_02/blueprint_v3.py | test_blueprint_v3.py | CONFIRMED |
| FactoryRegistry | pomt078 §1 | core_02/factory_registry.py | test_factory_registry.py | CONFIRMED |
| FactoryPassport/ForgePassport | C-2 roadmap | core_02/factory_passport.py, forge_passport.py | test_factory_passport.py, test_forge_passport.py | CONFIRMED |
| BaseFactory | Phase 9 | core_02/factory_base.py | (косвенно через test_*_factory) | PARTIAL |
| ScenarioIntelligence | SCENARIO_INTELLIGENCE_CONTRACT_V1 | scripts_01/scenario_intelligence.py | test_scenario_intelligence*.py | CONFIRMED |
| SmartRouter/ModelCatalog | router docstring | core_02/router.py | test_model_gateway.py (косвенно) | CONFIRMED |
| ModelGateway | — | scripts_01/model_gateway.py | test_model_gateway.py | CONFIRMED |
| RoleEngine (collab) | IDEAS.md | scripts_01/roles.py | test_roles.py | CONFIRMED |
| RoleExecutor | ADR-016 | core_02/role_executor.py | test_role_executor.py | CONFIRMED |
| ToolRegistry/BaseTool | — | scripts_01/tool_runtime.py | test_tool_runtime.py | CONFIRMED |
| Orchestrator | — | scripts_01/orchestrator.py | test_orchestrator.py | CONFIRMED |
| TaskManager | — | scripts_01/task_manager.py | test_task_manager.py | CONFIRMED |
| MemoryEngine | — | scripts_01/memory_engine.py | test_memory_engine.py | CONFIRMED |
| KnowledgeEngine | — | scripts_01/knowledge_engine.py | test_knowledge_engine.py | CONFIRMED |
| GraphIndex | — | scripts_01/graph_index.py | test_graph_index*.py | CONFIRMED |
| EventBus | — | scripts_01/event_bus.py | test_event_bus.py | CONFIRMED |
| WhimStore | — | scripts_01/whim_capture.py | test_whim_capture.py | CONFIRMED |
| OpportunityStore | — | scripts_01/opportunity_engine.py | test_opportunity_engine.py | CONFIRMED |
| MCP server | — | scripts_01/mcp_server.py | test_mcp_server.py | CONFIRMED |
| MCP FastAPI + Vault auth | — | scripts_01/mcp_fastapi.py | test_mcp_fastapi.py | CONFIRMED |
| Phone MCP | pomt45_05 | scripts_01/phone_control_mcp.py | test_phone_control_mcp.py | CONFIRMED |
| AgentContextBridge | — | scripts_01/agent_context_bridge.py | test_agent_context_bridge.py | CONFIRMED |

## Doc-only (нет кода / частично)

| Концепт | Документация | Код | Статус |
|---------|-------------|-----|--------|
| Agent base class + lifecycle | AGENT_ARCHITECTURE.md (forensics v2) | — | DOCUMENTED ONLY |
| PROJECT ROLE ≠ AGENT ROLE | promt107 §5 | roles.py (смешано) | DOCUMENTED ONLY |
| Integration/Connector Layer | promt107 §13 | вшито в ядро | DOCUMENTED ONLY |
| Project→Scenario→Factory→Forge сквозной | RFC/research | разрозненно | DOCUMENTED ONLY |
| Sandbox / tenant isolation | promt107 §14 | — | MISSING |

## Тестовое покрытие (на 2026-08-22)

- 122 test-файла, ~3349 test-функций (AST-truth, consistency_check counter).
- Ключевые интеграционные: test_forge_chain_cli.py, test_forge_chain_real_integration.py,
  test_v0_1_boundaries.py, test_scenario_intelligence_isolation.py.
