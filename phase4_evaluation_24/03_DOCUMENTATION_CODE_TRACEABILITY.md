# 03_DOCUMENTATION_CODE_TRACEABILITY — Phase 4

> Протокол pomt83 §3/§6: «не позволяй документации существовать как архитектуре в воздухе».
> Формат: Concept → Contract → Implementation → Entry Point → Test → Runtime Evidence.

Каждый концепт из документации Phase 4 прослежен до исполняемого кода. Итог —
**цепочки не разорваны** (gap отсутствует для Phase 4: фаза закрыта).

---

## Матрица документация → код

| Concept | Documentation | Contract | Implementation | Entry Point | Test | Status |
|---|---|---|---|---|---|---|
| Plugin API / Registry | `docs_10/core/FINAL_STRUCTURE.md` | plugin registry contract | `scripts_01/plugin_api.py` | `PluginRegistry` | `test_plugin_api.py` | CONFIRMED |
| Event Bus | `docs_10/…` | event contract (wildcard) | `scripts_01/event_bus.py` | `EventBus` + `get_default_event_bus()` (40 subscribers) | `test_event_bus.py` | CONFIRMED |
| MCP Server | `docs_10/plugin/FREEBUFF_PLUGIN_QUICKSTART.md` | JSON-RPC 2.0 / SSE / DELETE session | `scripts_01/mcp_server.py` (3228 LoC: dispatch + StdIO/HTTP transport) | `BuffyMcpServer`, `McpSessionManager`, `McpHttpServer`, `McpHTTPRequestHandler` | `test_mcp_server.py` (127) | CONFIRMED |
| Telegram Bot | `docs_10/…` | TG `/task` contract | `scripts_01/telegram_bot.py` | `TelegramFreebuffBot` | `test_telegram_bot.py` (39) | CONFIRMED |
| Scenario Engine | `docs_10/…` | scenario YAML front-matter | `freebuff_plugin_03/scenario_engine.py` + `core_02/scenario_registry.py` | `ScenarioEngine`, `ScenarioRegistry` | `test_scenario_engine.py` (83) | CONFIRMED |
| Factory Registry | `docs_10/engineering-memory/…` | factory contract | `core_02/factory_registry.py` | `FactoryRegistry` | `test_factory_registry.py` (51) | CONFIRMED |
| Forge Facade / Pipeline | `RFC_BUFFY_FORGE_V1.md` | B2 boundary | `core_02/forge_facade.py` + `forge_pipeline.py` + `forge_passport.py` | `ForgeFacade`, `ForgePipeline`, `ForgePassport` | `test_forge_facade.py` + `test_forge_pipeline.py` + `test_forge_passport.py` | CONFIRMED |
| Memory Engine | `docs_10/…` | memory.stored/cleared events | `scripts_01/memory_engine.py` | `MemoryEngine` (5 levels) | `test_memory_engine.py` | CONFIRMED |
| Knowledge Engine | `docs_10/…` | auto_index_subscriber | `scripts_01/knowledge_engine.py` (1438 LoC full-read) | `KnowledgeEngine`, `FtsIndex`, `TfidfIndex`, `SemanticIndex` | `test_knowledge_engine.py` | CONFIRMED |
| Event Subscribers | `docs_10/…` | read-only subscribers | `scripts_01/event_subscribers.py` | `auto_index_subscriber`, `register_notification_subscribers` | `test_event_subscribers.py` | CONFIRMED |
| Distributed Agents | `docs_10/…` | agent mesh contract | `scripts_01/distributed_agents.py` | `DistributedCoordinator`, `AgentMesh` | `test_distributed_agents.py` | PARTIAL (ast-only) |
| Project/Workspace model | `docs_10/core/PROJECT_RULES.md` | B1 boundary (privacy invariant) | `core_02/workspace.py` + `core_02/workspace_registry.py` | `Project`, `Workspace`, `WorkspaceRegistry`, `PrivacyViolationError` | `test_workspace.py`, `test_workspace_registry.py` | CONFIRMED |

## Поля статуса

- **CONFIRMED** — full-read исходника + тест есть + runtime evidence (VSLICE или subprocess).
- **PARTIAL (ast-only)** — структура подтверждена AST, полный read не выполнялся.
- **DESIGN_ONLY** — заявлен в доке, кода нет (для Phase 4: НЕ обнаружено).
- **UNIMPLEMENTED** — концепция существует только в документации (для Phase 4: НЕТ).

## Разорванные цепочки (gap)

**Нет разрывов для Phase 4.** Единственные «разрывы» носят не-Phase-4 характер:
- ~~`forge_registry.record_run` маппит `degraded` → FAILED~~ — **ЗАКРЫТО v5.189.10** (degraded сохраняет текущий статус; UNFORGED не персистится).
- 84 UNVERIFIED анкора в docs (soft-namespace, advisory §J.4) — не блокируют CI, hard=0.

## Метод верификации

- Резолвер анкоров: `python -m core_02.anchors_resolver . --json` →
  `runtime_05/anchors_resolver_report.json` (208 docs, 1098 anchors: 925 CURRENT,
  85 LESSON, 3 DESIGN_ONLY, 1 STALE, 84 UNVERIFIED).
- Cross-import grep: Plugin ↔ EventBus ↔ Memory ↔ Knowledge ↔ MCP ↔ Telegram.
- Реальные subprocess-прогоны: `test_forge_chain_real_integration.py` (7 passed).
