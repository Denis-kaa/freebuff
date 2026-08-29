# PHASE7_CHANGE_MANIFEST.md — Change Manifest

> Phase 7 §22. Формат: ADDED / MODIFIED / DELETED · path · reason · architectural purpose · tests.

## ADDED

| Path | Reason | Architectural purpose | Tests |
|------|--------|------------------------|-------|
| `tests_09/test_phase7_factory_event.py` | §13 targeted integration tests | Доказать integration: schema / factory selection / events / lifecycle / persistence / backward compat | 26 tests (self) |
| `phase7_evaluation_28/` (01–10 + json + manifest + next-phase) | §20–§28 output files | Independent evaluation package | — |

## MODIFIED

| Path | Reason | Architectural purpose | Tests |
|------|--------|------------------------|-------|
| `scripts_01/opportunity_engine.py` | GAP A (Factory selection + Project resolution) + GAP B (EventBus emission) | Opportunity → Factory → ForgeFacade canonical path; observability §J | `test_phase7_factory_event.py` (26) + baseline (111) |
| `scripts_01/whim_capture.py` | GAP B (whim.* events) | Лёгкий вход фиксируется событиями (наблюдаемость) | `test_whim_capture_emits_*` (3) |
| `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` | GAP C (Task A): §E reconciled | Canonical schema = implementation; одна схема | `test_opportunity_schema_*` (2) |
| `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | GAP C: drift #5 CLOSED + events-статусы | Contract registry актуален коду | — |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | GAP C: §20 #10 16→24 поля | §20 карта актуальна | — |
| `CHANGELOG.md` | v5.189.24 entry | Release history | — |
| `BUFFY.md` / `BUFFY_PROJECT.md` / `TASK.md` | version-anchor sync (R1) | Convention | — |

## DELETED

Нет.

---
_Все изменения аддитивные (CAN-16). Ни один существующий модуль не переписан._
