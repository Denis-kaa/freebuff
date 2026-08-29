# 08_PHASE7_TEST_REPORT.md — Testing / Regression Report

> Phase 7 §13 (TESTING).

## 1. Baseline (pre-change) — см. 01_PHASE7_BASELINE.md

111/111 green (5 affected files).

## 2. Targeted integration tests (NEW: tests_09/test_phase7_factory_event.py)

### Command

```bash
python -m pytest tests_09/test_phase7_factory_event.py -q --tb=short
```

### Result

| Metric | Value |
|--------|-------|
| **Collected** | 26 |
| **Passed** | 26 |
| **Failed** | 0 |
| **Skipped** | 0 |

### Coverage (по §13 списку)

1. **Opportunity schema** — `test_opportunity_schema_all_fields_roundtrip`, `test_opportunity_schema_canonical_field_set`
2. **Factory selection** — `test_derive_capability_*` (×3), `test_select_factory_forge_*` (×2)
3. **Opportunity → Factory** — `test_execute_records_factory_selection_and_runs_chain`
4. **Factory → ForgeFacade** — `test_execute_passes_project_object_not_string`
5. **Event publishing** — `test_execute_emits_execution_events`, `test_execute_emits_execution_failed_on_exception`, `test_advance_emits_lifecycle_events`, `test_propose_emits_scenario_selected`, `test_whim_*` (×3)
6. **Event payload** — assertions на data dict (opportunity_id/project_id/reason/source)
7. **Lifecycle transitions** — `test_lifecycle_transitions_with_events`, `test_execute_deferred_reactivates_and_completes`, `test_execute_completed_is_noop`, `test_execute_degrade_path_emits_execution_failed`
8. **Persistence** — `test_persistence_roundtrip_with_factory_selection`
9. **Backward compatibility** — `test_no_event_bus_means_no_emission`, `test_discover_candidates_still_works`
10. **Real EventBus** — `test_emit_event_real_eventbus_roundtrip`, `test_execute_with_real_eventbus`

## 3. Regression (affected files + Phase 7)

### Command

```bash
python -m pytest tests_09/test_phase7_factory_event.py \
                 tests_09/test_opportunity_engine.py \
                 tests_09/test_intelligence_loop_phase5.py \
                 tests_09/test_whim_capture.py \
                 tests_09/test_factory_registry.py -q --tb=short
```

### Result

| Metric | Value |
|--------|-------|
| **Collected** | 137 |
| **Passed** | 137 |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Exit code** | 0 |

## 4. mypy

```bash
python -m mypy scripts_01/opportunity_engine.py scripts_01/whim_capture.py \
              tests_09/test_phase7_factory_event.py --ignore-missing-imports
```

**Result:** 0 new errors (только 1 note «unchecked function body» в test file, не блокер).

## 5. Критерий NO REGRESSION

- Baseline 111 → regression 137 (111 baseline + 26 new): **все зелёные**.
- Существующие тесты не менялись (кроме добавления нового файла) — аддитивно (CAN-16).

---
_Phase 7: 137/137 green, mypy clean, NO REGRESSION._
