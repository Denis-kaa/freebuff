# 01_PHASE7_BASELINE.md — Baseline (pre-change test state)

> Phase 7 (promt 090_19_phase7_contract_reconciliation.md) §13 TESTING.
> Baseline зафиксирован ДО внесения Phase 7 изменений (Tasks B+C).

## Command

```bash
python -m pytest tests_09/test_opportunity_engine.py \
                 tests_09/test_intelligence_loop_phase5.py \
                 tests_09/test_whim_capture.py \
                 tests_09/test_factory_registry.py -q --tb=short
```

## Result

| Metric | Value |
|--------|-------|
| **Command** | pytest (5 affected files) |
| **Collected** | 111 |
| **Passed** | 111 |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Exit code** | 0 |

## Affected files (baseline targets)

| File | Role in Phase 7 |
|------|-----------------|
| `tests_09/test_opportunity_engine.py` | Opportunity lifecycle / DISCOVER / RANK (GAP A/B/C regression net) |
| `tests_09/test_intelligence_loop_phase5.py` | Phase 5 intelligence loop (forge_facade mock pattern) |
| `tests_09/test_whim_capture.py` | Whim lifecycle / promote cross-store |
| `tests_09/test_factory_registry.py` | FactoryRegistry (GAP A selection source) |

## Baseline invariants (pre-change)

- `execute()` вызывал `ForgeFacade.run_chain(...)` по **строке** project_id (классовый вызов) — GAP A.
- `advance()`/`execute()`/`propose()`/`whim_capture.*` **НЕ** публиковали EventBus-события — GAP B.
- §E контракт (15 полей) расходился с runtime dataclass (24 поля) — GAP C.

Все три GAP подтверждены на baseline и закрыты в Phase 7 (см. 02/03/04/05).

---
_Phase 7 baseline: 111/111 green. NO pre-existing failures in the affected slice._
