# 06_EVIDENCE_LEDGER — реестр доказательств

> Протокол pomt83 §16: для каждого утверждения — CLAIM / EVIDENCE / PATH / SYMBOL / TEST / STATUS.

| # | CLAIM | EVIDENCE | PATH | SYMBOL | TEST | STATUS |
|---|---|---|---|---|---|---|
| 1 | Plugin Registry существует и исполняем | класс + registry | `scripts_01/plugin_api.py` | `PluginRegistry` | `test_plugin_api.py` | CONFIRMED |
| 2 | EventBus публикует wildcard-события, 40 subscribers | runtime VSLICE-1 | `scripts_01/event_bus.py` | `EventBus`, `get_default_event_bus` | `test_event_bus.py` | CONFIRMED |
| 3 | MCP Server — JSON-RPC 2.0 + lazy движки + handlers/HTTP | full-read 3228 LoC (dispatch 2476–2619, transport 2701–2834, HTTP server 2869–3089) | `scripts_01/mcp_server.py` | `BuffyMcpServer`, `McpHttpServer`, `McpHTTPRequestHandler` | `test_mcp_server.py` (127) | CONFIRMED |
| 4 | Telegram Bot реализует `/task` | AST + test | `scripts_01/telegram_bot.py` | `TelegramFreebuffBot` | `test_telegram_bot.py` (39/39) | CONFIRMED |
| 5 | Scenario Engine — 2 пути реализации | full-read 619 LoC | `freebuff_plugin_03/scenario_engine.py`, `core_02/scenario_registry.py` | `ScenarioEngine`, `ScenarioRegistry` | `test_scenario_engine.py` (83) | CONFIRMED |
| 6 | Factory Registry с graceful-degrade | full-read (v5.188.2) | `core_02/factory_registry.py` | `FactoryRegistry` | `test_factory_registry.py` (51) | CONFIRMED |
| 7 | ForgeFacade — 14-рольная цепочка, B2 boundary | full-read 1752 LoC | `core_02/forge_facade.py`, `forge_pipeline.py`, `forge_passport.py` | `ForgeFacade`, `ForgePipeline`, `ForgePassport` | `test_forge_facade.py`, `test_forge_pipeline.py`, `test_forge_passport.py` | CONFIRMED |
| 8 | MemoryEngine — 5 уровней, thread-safe | full-read 625 LoC | `scripts_01/memory_engine.py` | `MemoryEngine`, `MemoryEntry` | `test_memory_engine.py` | CONFIRMED |
| 9 | KnowledgeEngine — 3-level search + auto-index subscriber | full-read 1438 LoC | `scripts_01/knowledge_engine.py`, `event_subscribers.py` | `KnowledgeEngine`, `FtsIndex`, `TfidfIndex`, `SemanticIndex`, `auto_index_subscriber` | `test_knowledge_engine.py`, `test_event_subscribers.py` | CONFIRMED |
| 10 | Distributed Agents | AST-only | `scripts_01/distributed_agents.py` | `DistributedCoordinator`, `AgentMesh` | `test_distributed_agents.py` | PARTIAL (ast-only) |
| 11 | Project/Workspace model (B1) — two-layer + privacy guard | full-read (workspace.py + workspace_registry.py) | `core_02/workspace.py`, `core_02/workspace_registry.py` | `Project`, `Workspace`, `WorkspaceRegistry`, `PrivacyViolationError` | `test_workspace.py`, `test_workspace_registry.py` | CONFIRMED |
| 12 | Bootstrap unknown-profile → minimal fallback | 12/12 green | `freebuff_plugin_03/bootstrap/engine.py` | `BootstrapEngine._load_profile` | `test_mcp_server.py::TestBootstrapTools` (12) | CONFIRMED |
| 13 | forge `--resume` partial continuation | 7 passed real integration | `scripts_01/forge.py`, `core_02/forge_facade.py` | `cmd_chain`, `_merge_chain_runs` | `test_forge_chain_real_integration.py` (7) | CONFIRMED |
| 14 | Anchor resolution (19 namespaces) | 208 docs / 1098 anchors, exit 0 | `core_02/anchors_resolver.py` | `AnchorResolver` | `test_anchors_resolver.py` | CONFIRMED |
| 15 | Полный pytest suite зелёный | full-suite (tmux, 12:42) | `tests_09/` | — | `pytest tests_09/ -q` → 2893 passed, 0 failed | CONFIRMED |

## Якоря §T (анкоровый индекс)

| Anchor | Namespace | Status |
|---|---|---|
| `@entity plugin.contract.violation.model` | @entity | resolvable |
| `@contract forge_facade.b2_boundary` | @contract | resolvable |
| `@decision phase4_archival_pending.v1` | @decision | resolvable |
| `@test consistency_check.diagnose_test_count` | @test | resolvable |
| `@event system.test.timeout` | @event | resolvable |
| `@doc.plate4_protocols.pomt83` | @doc.* | resolvable |
| `@storage forge.passport.yaml.v1` | @storage | resolvable |
| `@symbol forge_facade.chain_run` | @symbol | resolvable |
| `@lesson compact_ast_is_structural_only` | @lesson | resolvable |

> Все якоря перепроверены `python -m core_02.anchors_resolver .` (exit 0; hard=0).
