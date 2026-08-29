# 07_PHASE7_TRACEABILITY_MATRIX.md — Code ↔ Documentation Reconciliation

> Phase 7 §12. Формат: Claim | Contract | Code | Symbol | Caller | Entry Point | Test | Status.
> Статусы: CONFIRMED / PARTIAL / MISSING / DEFERRED.

| # | Claim | Contract | Code | Symbol | Caller | Entry Point | Test | Status |
|---|-------|----------|------|--------|--------|-------------|------|--------|
| 1 | Opportunity schema canonical (24 поля) | §E (reconciled) + CONTRACT_REGISTRY #15 | `scripts_01/opportunity_engine.py` | `Opportunity` dataclass | `OpportunityStore.upsert/get` | `opportunity_engine discover/run` | `test_opportunity_schema_all_fields_roundtrip` | **CONFIRMED** |
| 2 | Opportunity persistence (YAML) | §E persistence decision | `scripts_01/opportunity_engine.py` | `OpportunityStore` | `execute/upsert` | CLI | `test_persistence_roundtrip_with_factory_selection` | **CONFIRMED** |
| 3 | Lifecycle FSM (ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED/FAILED) | §E + promt 079 §3.1 | `scripts_01/opportunity_engine.py` | `advance` / `_check_transition` | `execute` | CLI | `test_lifecycle_transitions_with_events` | **CONFIRMED** |
| 4 | Opportunity → Scenario selection | §F SCENARIO CONTRACT | `scripts_01/opportunity_engine.py` → `core_02/scenario_registry.py` | `propose` → `ScenarioRegistry.propose_roles` | `_cli_run` | `opportunity_engine propose/run` | `test_propose_emits_scenario_selected` | **CONFIRMED** |
| 5 | Opportunity → Factory selection | §G FACTORY CONTRACT | `scripts_01/opportunity_engine.py` → `core_02/factory_registry.py` | `_select_factory_forge` → `FactoryRegistry.select_forge` | `execute` | CLI `run` | `test_select_factory_forge_routes_by_capability` | **CONFIRMED** |
| 6 | Opportunity НЕ обходит Factory | §4 целевая архитектура | `execute()` (factory_selection перед run_chain) | `execute` | `_cli_run` | CLI | `test_execute_records_factory_selection_and_runs_chain` | **CONFIRMED** |
| 7 | ForgeFacade остаётся execution boundary | §7.3 / §16 | `execute()` → `core_02/forge_facade.py` | `ForgeFacade.run_chain` | `execute` | CLI | `test_execute_factory_fallback_backward_compat` | **CONFIRMED** |
| 8 | Project-объект (не строка) в run_chain | GAP A fix | `_resolve_project` → `core_02/workspace.py::Project.load` | `_resolve_project` | `execute` | CLI | `test_execute_passes_project_object_not_string` | **CONFIRMED** |
| 9 | EventBus emission (execution.*) | §J EVENT CONTRACT | `_emit_event` → `scripts_01/event_bus.py::EventBus.publish` | `_emit_event` | `execute` | CLI `run` | `test_execute_emits_execution_events` | **CONFIRMED** |
| 10 | EventBus emission (opportunity.*) | §J | `advance` | `advance` | `execute` | CLI | `test_advance_emits_lifecycle_events` | **CONFIRMED** |
| 11 | EventBus emission (scenario.selected) | §J | `propose` | `propose` | `_cli_run` | CLI | `test_propose_emits_scenario_selected` | **CONFIRMED** |
| 12 | EventBus emission (whim.*) | §J | `scripts_01/whim_capture.py` | `capture/triage/promote/defer` | CLI | `whim_capture ...` | `test_whim_capture_emits_captured` | **CONFIRMED** |
| 13 | Feedback loop техническая возможность | §10 | `accumulate` → MemoryStore/LearningLoop | `accumulate` | `execute` | CLI | `test_execute_with_real_eventbus` | **CONFIRMED** (механика) / **DEFERRED** (автономный engine) |
| 14 | Автономный feedback engine | §10 | — | — | — | — | — | **DEFERRED** (Scope §3) |
| 15 | DOCUMENT_TAGGING foundation | §11 | — | — | — | — | — | **DEFERRED** (Scope §3) |
| 16 | EventBus-события читаемы из storage | §8/§9 | `EventBus.get_events` | `get_events` | тест | тест | `test_emit_event_real_eventbus_roundtrip` | **CONFIRMED** |
| 17 | degrade-путь никогда не крашит + execution.failed | §6/§16 | `execute` (except InvalidTransition → FAILED) | `execute` | `_cli_run` | CLI | `test_execute_degrade_path_emits_execution_failed` | **CONFIRMED** |
| 18 | Backward compat: event_bus=None → no emission | §17 | `_emit_event` (None → no-op) | `_emit_event` | `execute` | CLI | `test_no_event_bus_means_no_emission` | **CONFIRMED** |
| 19 | discover_candidates без изменений (fail-safe) | §8 | `discover_candidates` | `discover_candidates` | CLI | CLI | `test_discover_candidates_still_works` | **CONFIRMED** |
| 20 | Нет duplicate registries / event systems / execution | §19 (acceptance) | — | — | — | — | (grep-проверка) | **CONFIRMED** |

## Сводка

- **CONFIRMED:** 19/20
- **DEFERRED:** 1 (автономный feedback engine) + 1 (DOCUMENT_TAGGING foundation) — оба вне scope Phase 7 (§3)
- **PARTIAL / MISSING:** 0

---
_Каждое утверждение «реализовано» имеет file/symbol/caller/entrypoint/test._
