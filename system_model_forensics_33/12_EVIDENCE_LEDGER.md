# 12_EVIDENCE_LEDGER.md — Журнал доказательств

> **Формат (§16):** EV-ID | CLAIM | SOURCE | SYMBOL | STATUS | CONFIDENCE | NOTES

| EV-ID | CLAIM | SOURCE | SYMBOL | STATUS | CONFIDENCE | NOTES |
|-------|-------|--------|--------|--------|------------|-------|
| EV-001 | Whim — сырая мысль, intake-слой | scripts_01/whim_capture.py | `Whim`, `capture()`, `triage()`, `promote()` | CONFIRMED | HIGH | lifecycle NEW→TRIAGED→PROMOTED_TO_OPPORTUNITY |
| EV-002 | Opportunity — отдельный слой (нет в target) | scripts_01/opportunity_engine.py | `Opportunity`, `discover_candidates()`, `propose()`, `execute()` | CONFIRMED | HIGH | YAML data_13/opportunities.yaml |
| EV-003 | Workspace — L-1 контейнер | core_02/workspace.py | `Workspace.load()` | CONFIRMED | HIGH | workspace.yaml |
| EV-004 | Project — L-2 контейнер | core_02/workspace.py | `Project.load()`, `get_requirements()` | CONFIRMED | HIGH | project.yaml + README/RUNNABLE/CHECKLIST/STEPS |
| EV-005 | Scenario = корпус ролей (ABC) | core_02/scenario.py | `Scenario` (ABC), `Role`, `ScenarioManifest` | CONFIRMED | HIGH | BlueprintScenario = BlueprintCorpus |
| EV-006 | Scenario = decision-слой (второй смысл) | scripts_01/scenario_intelligence.py | `ScenarioIntelligence.select()` | CONFIRMED | HIGH | Opportunity→capability→factory/forge |
| EV-007 | Scenario Registry — auto-discovery | core_02/scenario_registry.py | `ScenarioRegistry`, `propose_roles()` | CONFIRMED | HIGH | runtime_05/scenarios/*.yaml |
| EV-008 | Factory — capability-каталог | core_02/factory_registry.py | `FactoryRegistry.select_forge()` | CONFIRMED | HIGH | runtime_05/factories/*/ |
| EV-009 | Factory — BaseFactory адаптер | core_02/factory_base.py | `BaseFactory.execute()` | CONFIRMED | HIGH | ADR-013 |
| EV-010 | Factory Passport — типизированный контракт | core_02/factory_passport.py | `FactoryPassport` | CONFIRMED | HIGH | factory.yaml |
| EV-011 | Forge Passport — декларация кузни | core_02/forge_passport.py | `ForgePassport.from_yaml()` | CONFIRMED | HIGH | <forge>.yaml |
| EV-012 | ForgeFacade — execution bridge | core_02/forge_facade.py | `ForgeFacade.run_chain()` | CONFIRMED | HIGH | 14 ролей PIPELINE_CHAIN |
| EV-013 | ForgeFacade — §7.3 boundary (Scenario не вызывает Forge напрямую) | core_02/forge_facade.py | `initiate_forge()` gate `can_initiate()` | CONFIRMED | HIGH | ValueError вне PIPELINE_ROLES |
| EV-014 | ForgePipeline — CI (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT) | core_02/forge_pipeline.py | `ForgePipeline.run()` | CONFIRMED | HIGH | L-3 |
| EV-015 | ForgeRegistry — реестр статусов | core_02/forge_registry.py | `ForgeRegistry.record_run()`, `validate_schema()` | CONFIRMED | HIGH | B10/R-127 |
| EV-016 | Role executor — автоисполнение LIGHT-ролей | core_02/role_executor.py | `RoleExecutorRegistry`, `LisaExecutor`, `LlmRoleExecutor` | CONFIRMED | HIGH | ADR-016 |
| EV-017 | Agent (stateful) — единой абстракции НЕТ | — | (role_executor + distributed_agents + runtime/registry + plugins) | ABSENT | HIGH | см. 07 |
| EV-018 | Skill — модуля НЕТ | — | KNOWN_CAPABILITIES + missing_registry | ABSENT | HIGH | capability-токены = замена |
| EV-019 | Tool — 5 инструментов | scripts_01/tool_runtime.py | `ToolRegistry`, `GitTool`…`ShellTool` | CONFIRMED | HIGH | изолирован от Forge |
| EV-020 | Runtime — реестр рантаймов | freebuff_plugin_03/runtime/registry.py | `RuntimeRegistry` | PARTIAL | MEDIUM | реестр, не слой |
| EV-021 | Model routing — capability-based | core_02/router.py | `SmartRouter.route()`, `ModelCatalog.default()` | CONFIRMED | HIGH | ANTI-6b closed vocab |
| EV-022 | Memory — Knowledge Objects (SQLite) | core_02/memory_store.py | `MemoryStore.store_knowledge()` | CONFIRMED | HIGH | context.db |
| EV-023 | Learning Loop — feedback | core_02/learning_loop.py | `LearningLoop.record_feedback()` | CONFIRMED | HIGH | |
| EV-024 | Knowledge — FTS/TF-IDF | scripts_01/knowledge_engine.py | `KnowledgeEngine.search()` | CONFIRMED | HIGH | |
| EV-025 | Semantic layer | core_02/semantic_layer.py | — | CONFIRMED | MEDIUM | |
| EV-026 | EventBus | scripts_01/event_bus.py | `EventBus.publish()`, `Event` | CONFIRMED | HIGH | context_12/events.db |
| EV-027 | Orchestrator — FSM/DAG (конкурирующий путь) | scripts_01/orchestrator.py | `Orchestrator.run_workflow()` | CONFIRMED | HIGH | Goal→Plan→Execute→Validate |
| EV-028 | Orchestrator НЕ соединён с ForgeFacade | scripts_01/orchestrator.py vs core_02/forge_facade.py | `StepType.MODEL` → SmartRouter (не ForgeFacade) | CONFIRMED | HIGH | R7 |
| EV-029 | Intelligence-путь сходится на ForgeFacade | scripts_01/opportunity_engine.py | `execute()` → `ForgeFacade.run_chain()` | CONFIRMED | HIGH | единственный boundary |
| EV-030 | Factory глобальна (не принадлежит Project) | core_02/factory_registry.py | `DEFAULT_FACTORIES_DIR = runtime_05/factories` | CONFIRMED | HIGH | НЕ projects_17/ |
| EV-031 | 4 фабрики (не 8+) | runtime_05/factories/* | architecture/content/research/test | CONFIRMED | HIGH | против target-модели §6 |
| EV-032 | code capability → (test, verifier) | core_02/factory_registry.py | `CODE_RESOLUTION_POLICY` | CONFIRMED | HIGH | Phase 13 G-11.6 |
| EV-033 | Дубль db (scripts_01/data vs data_13) | scripts_01/data/*.db + data_13/*.db | 5 db в обоих | CONFIRMED | HIGH | metrics/roles/presence/collaboration/project_pulse |
| EV-034 | Entrypoint CLI chain | scripts_01/forge.py | `cmd_chain()`, `build_parser()` | CONFIRMED | HIGH | |
| EV-035 | Prompts — конвенция NNN_TT | pompts_11/* | `106_19_repository_forensics_system_modeling.md` | CONFIRMED | HIGH | |
