# 02 — PHASE 4 COMPONENT MAP

> Каждый архитектурный вывод — FACT с evidence (source → symbol → behaviour). Без «скорее всего».

## C1. Иерархия сущностей (промт §6: PROJECT→WORKSPACE→…→EVENTS)

| Звено | Существование | Location | Ответственность | Storage | Runtime path | Тесты |
|-------|--------------|----------|-----------------|---------|--------------|-------|
| Workspace (L-1) | ✅ | `core_02/workspace.py::Workspace` + `workspace_registry.py::Workspace`/`WorkspaceRegistry` | верхний контейнер, набор проектов, steps_policy | `workspace.yaml` + `data_13/workspace_profiles.yaml` | `Workspace.load(root)` | test_workspace.py |
| Project (L-2) | ✅ | `core_02/workspace.py::Project` | изолированный проект: config, roles, contracts, requirements, Env Doctor | `project.yaml` (root) + STEPS/RUNNABLE/CHECKLIST | `Project.load(root)` | test_workspace.py |
| Agent/Runtime | ✅ | `scripts_01/model_gateway.py::ModelGateway`, `distributed_agents.py`, `tool_runtime.py` | модели, инструменты, multi-agent | in-memory + config | ModelGateway.select/dispatch | test_* |
| Scenario | ✅ | `core_02/scenario.py::Scenario`/`Role` + `scenario_registry.py::ScenarioRegistry` | источник ролей; подбор по запросу | `runtime_05/scenarios/*.yaml` (manifest) | `ScenarioRegistry.propose_roles` | test_scenario_registry.py |
| Factory | ✅ | `core_02/factory_registry.py::FactoryRegistry` + `forge_passport.py::ForgePassport` | реестр фабрик/кузен (паспорта) | `runtime_05/factories/<factory>/factory.yaml` + `<forge>.yaml` | `FactoryRegistry.find_by_capability` | test_factory_registry.py |
| Forge | ✅ | `core_02/forge_facade.py::ForgeFacade` + `forge_pipeline.py::ForgePipeline` + `forge_registry.py::ForgeRegistry` | pipeline FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT; статусы | `data_13/forge_registry.yaml` | `ForgeFacade.run_chain` (единственный мост §7.3) | test_forge_facade.py |
| Artifact | ✅ | `forge_facade.py::RoleArtifactValidator` | existence-проверка outputs ролей | filesystem (`registry.yaml` patterns) | `validate_role_artifacts` | test_forge_facade.py |
| Memory/Knowledge | ✅ | `memory_store.py::MemoryStore` + `semantic_layer.py` + `learning_loop.py` + `knowledge_engine.py` | KO + граф + AFC-обучение + гибридный поиск | `data_13/context.db` (SQLite) | MemoryStore.store_knowledge → SemanticLayer.search | test_memory_store.py |
| Events | ✅ | `event_bus.py::EventBus` + `project_pulse.py::ProjectPulse` + `event_subscribers.py` | pub/sub + лента изменений | `context_12/events.db`, `data_13/project_pulse.db` | EventBus.publish → subscribers | test_event_bus.py |

## C2. Точка входа и execution path

**FACT:** Forge запускается ТОЛЬКО через `ForgeFacade`. Источник: `core_02/forge_facade.py::ForgeFacade.initiate_forge` — «ForgePipeline инстанцируется ТОЛЬКО здесь».
**FACT:** Прямой вызов Forge из Scenario запрещён (§7.3). Источник: `forge_facade.py` docstring, `REFERENCE_ROLES`, gate `can_initiate()`.
**FACT:** `run_chain` — chain-runner по 14 pipeline-ролям (LIGHT=check-only, HEAVY=full_cycle, CONDITIONAL=frontend/devops).
**FACT:** Статус UNFORGED ≠ UNTESTED (B10/R-127). Источник: `forge_registry.py::validate_schema`.

## C3. Внутренние границы (промт §7: FACTORY vs FORGE vs SCENARIO)

| Аспект | SCENARIO | FACTORY | FORGE |
|--------|----------|---------|-------|
| Что это в коде | `Scenario` ABC + `Role` dataclass; `ScenarioRegistry` | `FactoryRegistry` + `ForgePassport` (паспорт кузни) | `ForgeFacade` + `ForgePipeline` + `ForgeRegistry` |
| Registry | `scenario_registry.py` (auto-discovery YAML) | `factory_registry.py` (auto-discovery YAML) | `forge_registry.py` (статусы проектов) |
| Что описывает | роли (мощности) | capabilities кузен | lifecycle проекта (UNFORGED→DEPLOYED) |
| Связь с Forge | НЕ вызывает напрямую (§7.3) | описывает, не исполняет | исполняет pipeline |

**FACT:** `FactoryRegistry ≠ ForgeRegistry ≠ ScenarioRegistry` (B-Rule 4/5). Источник: `factory_registry.py` docstring.
**FACT:** `ScenarioRegistry.propose_roles` — fuzzy-match по keyword overlap (`wizard_lib.score_role_match`).
**FACT:** `FactoryRegistry.find_by_capability` — «Bridge to Scenario Engine §6.2 (CapabilityRef resolution)».

## C4. Storage-карта

| Хранилище | Файл/таблица | Владелец |
|-----------|-------------|----------|
| Knowledge Objects + граф | `data_13/context.db` (`knowledge_objects`, `knowledge_links`, `learning_events`, `experience_analytics`) | `core_02/memory_store.py::MemoryStore` |
| Events | `context_12/events.db` (`event_log`) | `scripts_01/event_bus.py::EventBus` |
| Pulse | `data_13/project_pulse.db` (`pulse_entries`) | `scripts_01/project_pulse.py::ProjectPulse` |
| Opportunities | `data_13/opportunities.yaml` | `scripts_01/opportunity_engine.py::OpportunityStore` |
| Whims | `data_13/whims.yaml` | `scripts_01/whim_capture.py::WhimStore` |
| Forge статусы | `data_13/forge_registry.yaml` | `core_02/forge_registry.py::ForgeRegistry` |
| Missing registry | `data_13/missing_registry.yaml` | `core_02/missing_registry.py` |
| Scenario manifests | `runtime_05/scenarios/*.yaml` | `core_02/scenario_registry.py` |
| Factory manifests | `runtime_05/factories/<factory>/*.yaml` | `core_02/factory_registry.py` |
