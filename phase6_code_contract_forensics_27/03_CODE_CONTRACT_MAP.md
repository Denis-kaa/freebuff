# 03_CODE_CONTRACT_MAP — Карта CODE ↔ CONTRACT

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §5 (TRACEABILITY MODEL) + §6 (ДОКУМЕНТАЦИЯ ↔ КОД)
> **Метод:** каждый контракт → реальный модуль/класс/функция с evidence (path::symbol). Статусы: CONFIRMED / PARTIAL / DOCUMENTED_ONLY / CODE_ONLY / CONFLICT / DEAD_CODE / UNVERIFIED / MISSING.

---

## 1. Traceability-модель (пример: Opportunity)

```
Opportunity
  ↓ DOCUMENT        INTELLIGENCE_FACTORY_CONTRACT_V1.md §E
  ↓ CONTRACT        opportunity.schema (CONTRACT_REGISTRY_V1.md #15)
  ↓ MODULE          scripts_01/opportunity_engine.py
  ↓ CLASS           Opportunity (dataclass, 24 поля) + OpportunityStore
  ↓ FUNCTION        discover_candidates() / rank_candidates() / propose() / execute() / accumulate()
  ↓ CALLER          _cli_discover / _cli_run (CLI) → discover_candidates / execute
  ↓ ENTRYPOINT      opportunity_engine discover|run (CLI)
  ↓ EVENT           opportunity.* (planned §J — НЕ публикуются, см. 06_EVENT_TRACEABILITY)
  ↓ STORAGE         data_13/opportunities.yaml + MemoryStore (KO kind=candidate)
  ↓ TEST            tests_09/test_opportunity_engine.py + test_opportunity_ranking.py + test_intelligence_loop_phase5.py
```

## 2. Таблица документация ↔ код (Architecture Claim Matrix)

| Architecture Claim | Documentation | Code Evidence | Test Evidence | Status |
|---|---|---|---|---|
| Event Bus publish/subscribe | EVENT_PLATFORM_SPECIFICATION.md | `scripts_01/event_bus.py::EventBus.publish/subscribe/get_events` | `tests_09/test_event_bus.py` | ✅ CONFIRMED |
| Plugin API registry | core/PLUGIN_API docs | `scripts_01/plugin_api.py::PluginRegistry/BasePlugin/PluginLoader` | `tests_09/test_plugin_api.py` | ✅ CONFIRMED |
| Plugin Contract validation | plugin_contract.py docstring | `scripts_01/plugin_contract.py::validate_manifest/validate_plugin_entry` | `tests_09/test_plugin_contract.py` | ✅ CONFIRMED |
| Scenario Registry (SELECT) | SCENARIO_ENGINE_DESIGN_V1.md §3.1 | `core_02/scenario_registry.py::ScenarioRegistry` (list_scenarios/get/find_role/propose_roles) | `tests_09/test_scenario_registry.py` | ✅ CONFIRMED |
| Scenario Engine (оркестратор) | SCENARIO_ENGINE_DESIGN_V1.md §7-§9 | **нет кода** (только ScenarioRegistry — реестр, не оркестратор) | — | ⚠️ DOCUMENTED_ONLY (`scenario_engine` design_ready в missing_registry) |
| Factory Registry | FACTORY_FORGE_ARCHITECTURE_V1.md §3/§20 row #20 | `core_02/factory_registry.py::FactoryRegistry` (get_factory/select_forge/find_factories_by_capability) + `factory_passport.py::FactoryPassport` | `tests_09/test_factory_registry.py` + `test_factory_passport.py` | ✅ CONFIRMED (v5.189.21) |
| Forge Facade (EXECUTE мост) | RFC_BUFFY_FORGE_V1.md §7.3 | `core_02/forge_facade.py::ForgeFacade.run_chain/initiate_forge` | `tests_09/test_forge_facade.py` | ✅ CONFIRMED |
| Forge Pipeline (CI) | forge_pipeline.py docstring | `core_02/forge_pipeline.py::ForgePipeline` (stage_forge/check/build/test/deploy/report/run) | `tests_09/test_forge_pipeline.py` | ✅ CONFIRMED |
| Forge Registry (lifecycle) | PLATFORM_CODE_MAP_V1.md §A.1 | `core_02/forge_registry.py::ForgeRegistry` (register_project/promote_status/record_run) | `tests_09/test_forge_registry.py` | ✅ CONFIRMED |
| Opportunity Engine | INTELLIGENCE_FACTORY_CONTRACT_V1.md §E | `scripts_01/opportunity_engine.py::Opportunity/discover_candidates/rank_candidates/execute/accumulate` | `tests_09/test_opportunity_engine.py` + `test_opportunity_ranking.py` | ✅ CONFIRMED |
| Whim Capture | FACTORY_FORGE_ARCHITECTURE_V1.md §17.1 | `scripts_01/whim_capture.py::Whim/WhimStore/capture/triage/promote/defer` | `tests_09/test_whim_capture.py` | ✅ CONFIRMED |
| Memory Store | RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md | `core_02/memory_store.py::MemoryStore` (write/search/store_knowledge) | `tests_09/test_memory_store.py` | ✅ CONFIRMED |
| Knowledge Engine | knowledge_engine.py docstring | `scripts_01/knowledge_engine.py::KnowledgeEngine` (FTS5+TF-IDF+SVD) | `tests_09/test_knowledge_engine.py` | ✅ CONFIRMED |
| Learning Loop | RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md | `core_02/learning_loop.py::LearningLoop` (capture/record_feedback) | `tests_09/test_learning_loop.py` | ✅ CONFIRMED |
| Semantic Layer | semantic_layer.py docstring | `core_02/semantic_layer.py::SemanticLayer` (semantic_search/find_similar_patterns) | `tests_09/test_semantic_layer.py` | ✅ CONFIRMED |
| Graph Index | PLATFORM_CODE_MAP_V1.md §A.3 | `scripts_01/graph_index.py::GraphIndex` (add_node/add_edge) | `tests_09/test_graph_index.py` | ✅ CONFIRMED |
| Project Pulse | project_pulse.py docstring | `scripts_01/project_pulse.py::ProjectPulse` (add_entry/list) | `tests_09/test_project_pulse.py` | ✅ CONFIRMED |
| Workspace | PLATFORM_CODE_MAP_V1.md §A.3 | `core_02/workspace.py::Workspace/Project` + `workspace_registry.py` | `tests_09/test_workspace.py` + `test_workspace_registry.py` | ✅ CONFIRMED |
| Scheduler | — (не описан в каноне) | **нет кода** (grep 0) | — | ❌ MISSING |
| Agent Runtime | distributed_agents.py (исполнители) | `scripts_01/distributed_agents.py::AgentNode/AgentTask` | `tests_09/test_distributed_agents.py` | ✅ CONFIRMED (но НЕ runtime — планировщик отсутствует) |
| Content Intelligence | content_factory/concept*.md | **нет отдельного кода** — реализован как `opportunity_engine` (Intelligence-слой CI) | `test_intelligence_loop_phase5.py` | ⚠️ PARTIAL (generic infra есть, content-specific нет) |
| Concept Evolution | RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md + P3_IDEA_EXPLORER | **нет кода** (grep 0: concept_evolution/evolution_memory/concept_genome) | — | ⚠️ DOCUMENTED_ONLY |

## 3. CODE_ONLY компоненты (есть в коде, нет в архитектурной документации)

- `core_02/doc_code_verify.py` — doc↔code verifier (реализован v5.189.4, зарегистрирован в missing_registry, но не входит в 25 @entity PLATFORM_CODE_MAP).
- `core_02/anchors_resolver.py` — 19-namespace anchor resolver (v5.189.4).
- `core_02/factory_passport.py` — FactoryPassport (v5.189.21).
- `scripts_01/research_web.py`, `scripts_01/lisa_estimator.py` — внешние инструменты (зарегистрированы, реализованы).

## 4. DEAD_CODE / UNVERIFIED кандидаты

- `core_02/xlsx_builder.py`, `scripts_01/excel_eval.py` — используются vkusvill_demo сценарием (не dead, но узко-доменные).
- `scripts_01/overlay_server.py` / `overlay_client.py` — overlay UI, runtime-путь не верифицирован в этой сессии (UNVERIFIED).
- `scripts_01/stream_session.py` / `stream_bridge.py` — стриминг, тесты есть (не dead).

---

_Конец 03_CODE_CONTRACT_MAP. Переход к 04_DOCUMENTATION_CODE_TRACEABILITY._
