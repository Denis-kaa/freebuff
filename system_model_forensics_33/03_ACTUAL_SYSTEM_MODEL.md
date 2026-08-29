# 03_ACTUAL_SYSTEM_MODEL.md — Фактическая модель по коду

> **Принцип (§4):** каждый узел — STATUS (CONFIRMED/PARTIAL/DESIGNED/CONCEPTUAL/ABSENT) + evidence.

---

## Actual platform map

```
USER (Termux-терминал / TG / HTTP / MCP)
  │
  ├─ ENTRYPOINTS (CONFIRMED)
  │    scripts_01/forge.py (CLI), forge_api.py+mcp_fastapi.py (HTTP/MCP),
  │    telegram_bot.py (TG), wizard.py (подбор ролей)
  │
  ├─ AGENT LAYER (PARTIAL — размазан)
  │    role_executor.py (RoleExecutorRegistry), distributed_agents.py,
  │    freebuff_plugin_03/runtime/registry.py (RuntimeRegistry),
  │    plugins_04/, roles.py + presence.py + collaboration.py
  │
  ├─ WORKSPACE / PROJECT (CONFIRMED — тонкие контейнеры)
  │    core_02/workspace.py::Workspace (L-1), Project (L-2)
  │
  ├─ INTELLIGENCE HEAD (CONFIRMED — НЕ в целевой модели)
  │    whim_capture.py (WHIM) → opportunity_engine.py (OPPORTUNITY)
  │    → scenario_intelligence.py (ScenarioDecision) → scenario_registry.py
  │
  ├─ FACTORY (CONFIRMED — глобальная capability)
  │    factory_registry.py + factory_base.py + runtime_05/factories/*/factory.yaml
  │
  ├─ FORGE (CONFIRMED — 4 смысла)
  │    forge_facade.py (chain-runner), forge_pipeline.py (CI),
  │    forge_passport.py (декларация), forge_registry.py (реестр)
  │
  ├─ SKILLS / TOOLS / RUNTIME
  │    SKILLS: ABSENT (capability-токены) · TOOLS: tool_runtime.py (CONFIRMED)
  │    RUNTIME: freebuff_plugin_03/runtime/ (PARTIAL)
  │
  ├─ ARTIFACT (CONFIRMED — файлы, не тип)
  │    роли пишут в project.root (brief.md/lisa_report.md/src/**)
  │
  └─ MEMORY / KNOWLEDGE / EVENTS (CONFIRMED)
       memory_store.py (KO SQLite), learning_loop.py, knowledge_engine.py,
       semantic_layer.py, rag_engine.py, graph_index.py, event_bus.py
```

---

## Узлы со статусом и evidence

| Узел | Status | Evidence (path → symbol) |
|------|--------|--------------------------|
| Entrypoint: CLI | CONFIRMED | `scripts_01/forge.py` → `build_parser()`, `cmd_chain()` |
| Entrypoint: HTTP | CONFIRMED | `scripts_01/forge_api.py` → `app = FastAPI(...)` |
| Entrypoint: MCP | CONFIRMED | `scripts_01/mcp_fastapi.py` / `mcp_server.py` |
| Entrypoint: TG | CONFIRMED | `scripts_01/telegram_bot.py` |
| WHIM | CONFIRMED | `scripts_01/whim_capture.py` → `Whim`, `WhimStore`, `capture/triage/promote` |
| OPPORTUNITY | CONFIRMED | `scripts_01/opportunity_engine.py` → `Opportunity`, `discover_candidates/propose/execute` |
| Scenario (corpus) | CONFIRMED | `core_02/scenario.py` → `Scenario` (ABC), `Role`, `ScenarioManifest` |
| Scenario (decision) | CONFIRMED | `scripts_01/scenario_intelligence.py` → `ScenarioIntelligence.select()` |
| Scenario Registry | CONFIRMED | `core_02/scenario_registry.py` → `ScenarioRegistry.propose_roles/find_role` |
| Factory | CONFIRMED | `core_02/factory_registry.py` → `FactoryRegistry.select_forge()` |
| Factory (adapter) | CONFIRMED | `core_02/factory_base.py` → `BaseFactory.execute()` |
| Factory (passport) | CONFIRMED | `core_02/factory_passport.py` → `FactoryPassport` |
| Forge (passport) | CONFIRMED | `core_02/forge_passport.py` → `ForgePassport` |
| Forge (chain) | CONFIRMED | `core_02/forge_facade.py` → `ForgeFacade.run_chain()` |
| Forge (CI) | CONFIRMED | `core_02/forge_pipeline.py` → `ForgePipeline.run()` |
| Forge (registry) | CONFIRMED | `core_02/forge_registry.py` → `ForgeRegistry.record_run()` |
| Role/Agent executor | CONFIRMED | `core_02/role_executor.py` → `RoleExecutorRegistry`, `LlmRoleExecutor` |
| Agent (stateful) | ABSENT | нет единой абстракции; только RoleExecutor + distributed_agents |
| Skill | ABSENT | нет `skill*.py`; capability-токены в `KNOWN_CAPABILITIES` |
| Tool | CONFIRMED | `scripts_01/tool_runtime.py` → `ToolRegistry`, `GitTool`…`ShellTool` |
| Runtime | PARTIAL | `freebuff_plugin_03/runtime/registry.py` → `RuntimeRegistry` |
| Model routing | CONFIRMED | `core_02/router.py` → `SmartRouter.route()` |
| Artifact | CONFIRMED | файлы в `project.root`; ChainRun.validation_summary перечисляет |
| Memory | CONFIRMED | `core_02/memory_store.py` → `MemoryStore.store_knowledge()` |
| Learning | CONFIRMED | `core_02/learning_loop.py` → `LearningLoop.record_feedback()` |
| Knowledge | CONFIRMED | `scripts_01/knowledge_engine.py` + `semantic_layer.py` + `rag_engine.py` |
| Events | CONFIRMED | `scripts_01/event_bus.py` → `EventBus.publish()` |
| Orchestrator | CONFIRMED | `scripts_01/orchestrator.py` → `Orchestrator.run_workflow()` (параллельный путь) |

---

## Ключевое наблюдение (refutation)

Целевая модель предполагает **линейную** цепочку WHIM→…→FORGE→…→ARTIFACT.

Фактический код содержит **два независимых execution-пути**:

1. **Forge-путь (production):** `forge.py chain` → `ForgeFacade.run_chain` → 14 ролей → `forge_registry.record_run`.
2. **Intelligence-путь (автономный):** `whim_capture` → `opportunity_engine` → `scenario_intelligence` → `factory_registry.select_forge` → `ForgeFacade.run_chain` → `memory_store`.

Эти пути **сходятся на ForgeFacade** (единственный execution boundary, §7.3), но
**не связаны на уровне Orchestrator** — `orchestrator.py` реализует третий
FSM/DAG-путь (Goal→Plan→Execute→Validate), который с ForgeFacade НЕ соединён.

Это значит: **«один линейный путь» — ложная модель; реальность = 3 конкурирующих
парадигмы, разделяющих только ForgeFacade как точку исполнения.**
