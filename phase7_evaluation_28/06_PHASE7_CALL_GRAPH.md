# 06_PHASE7_CALL_GRAPH.md — Call Graph (new execution path)

> Phase 7 §14 (ОБЯЗАТЕЛЬНАЯ ПРОВЕРКА CALL GRAPH).

## Полный путь: Whim → Opportunity → Scenario → Factory → Forge → Artifact → Memory/Event

```
whim_capture.capture()/triage()/promote()      [scripts_01/whim_capture.py***REMOVED***
   ↓ whim.created / whim.classified / whim.promoted (EventBus)
opportunity_engine.discover_candidates()       [scripts_01/opportunity_engine.py***REMOVED***
   ↓ (real sources: whims.yaml / project_pulse.db / events.db / context.db)
Opportunity (24-field schema, data_13/opportunities.yaml)
   ↓
opportunity_engine.propose()                   [scripts_01/opportunity_engine.py***REMOVED***
   ↓ ScenarioRegistry.propose_roles()          [core_02/scenario_registry.py***REMOVED***
   ↓ scenario.selected (EventBus)
Opportunity.scenario / roles
   ↓
opportunity_engine.execute()                   [scripts_01/opportunity_engine.py***REMOVED***
   ├─ _derive_capability() → capability
   ├─ _select_factory_forge() → FactoryRegistry.select_forge()   [core_02/factory_registry.py***REMOVED***
   │     └─ FactoryPassport / ForgePassport
   ├─ provenance['factory_selection'***REMOVED***
   ├─ _resolve_project() → Project            [core_02/workspace.py***REMOVED***
   ├─ execution.started (EventBus)
   ├─ ForgeFacade() → facade.run_chain(project, role_ids)   [core_02/forge_facade.py***REMOVED***
   │     └─ ForgePipeline / RoleArtifactValidator           [core_02/forge_pipeline.py***REMOVED***
   │     └─ ForgeRegistry.record_run                        [core_02/forge_registry.py***REMOVED***
   ├─ Artifact → opp.artifacts
   ├─ advance(COMPLETED|FAILED) → opportunity.* (EventBus)
   ├─ execution.completed|failed (EventBus)
   └─ _accumulate_best_effort() → accumulate()
         └─ MemoryStore.store_knowledge(kind=candidate)     [core_02/memory_store.py***REMOVED***
         └─ LearningLoop / record_feedback                  [core_02/learning_loop.py***REMOVED***
```

## Таблица переходов (FILE | SYMBOL | CALLER | TEST)

| Переход | FILE::SYMBOL | Caller | Test |
|---------|--------------|--------|------|
| Whim → Opportunity | `scripts_01/whim_capture.py::promote` | CLI `whim_capture promote` | `test_whim_promote_emits_promoted` |
| DISCOVER | `opportunity_engine.py::discover_candidates` | CLI `opportunity_engine discover` | `test_discover_candidates_still_works` |
| Scenario selection | `opportunity_engine.py::propose` → `scenario_registry.py::propose_roles` | CLI `opportunity_engine propose/run` | `test_propose_emits_scenario_selected` |
| Factory selection | `opportunity_engine.py::_select_factory_forge` → `factory_registry.py::FactoryRegistry.select_forge` | `execute()` | `test_select_factory_forge_routes_by_capability` |
| ForgeFacade | `opportunity_engine.py::execute` → `forge_facade.py::ForgeFacade.run_chain` | CLI `opportunity_engine run` | `test_execute_records_factory_selection_and_runs_chain` |
| Artifact → Memory | `opportunity_engine.py::accumulate` → `memory_store.py::store_knowledge` | `execute()` (post-run) | `test_persistence_roundtrip_with_factory_selection` |
| Events | `opportunity_engine.py::_emit_event` → `event_bus.py::EventBus.publish` | `execute/advance/propose` | `test_execute_with_real_eventbus` |

## Entrypoints

- `python -m scripts_01.opportunity_engine discover|propose|run|status|list|rank`
- `python -m scripts_01.whim_capture capture|list|status|triage|promote|defer|get`

---
_Каждая стрелка имеет реальный код, symbol, caller, entrypoint и тест._
