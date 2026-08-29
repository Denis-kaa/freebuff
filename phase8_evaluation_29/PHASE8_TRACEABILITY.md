# PHASE8_TRACEABILITY.md — Phase 8 Traceability (§19)

> Цепочка: Requirement → Contract → Code → Test → Evidence.
> Дата: 2026-08-17. Версия: v5.189.25.

---

## 1. Requirement → Contract → Code → Test → Evidence

| # | Requirement (promt 91) | Contract (SCENARIO_INTELLIGENCE_CONTRACT_V1.md) | Code | Test | Evidence |
|---|------------------------|--------------------------------------------------|------|------|----------|
| 1 | Candidate discovery (§5) | §3 | `ScenarioIntelligence.discover()` | test_1_candidate_discovery | 18 passed (pytest) |
| 2 | Multiple scenarios (§5) | §3 | `discover()` (propose_roles + list_scenarios) | test_2_multiple_scenarios | 18 passed |
| 3 | Evaluation (§6) | §4 | `evaluate()` (composite = Σ wᵢ·componentᵢ) | test_4_selection (score math) | 18 passed |
| 4 | Ranking (§7) | §5 | `rank()` (score desc, stable) | test_3_ranking | 18 passed |
| 5 | Selection (§7) | §6 | `select()` (discover→evaluate→rank→best) | test_4_selection | 18 passed |
| 6 | Provenance (§7) | §8 | `ScenarioDecision` (reasons/evidence/capability/factory/forge) | test_5_provenance | 18 passed |
| 7 | Capability resolution (§8) | §7 | `resolve_capability()` → FactoryRegistry.select_forge | test_6_capability_resolution | 18 passed |
| 8 | Factory routing (§8) | §7 | decision.capability → factory_id/forge_id | test_7_factory_routing | 18 passed |
| 9 | Forge boundary (§17) | §13 | ScenarioIntelligence НЕ вызывает ForgeFacade | test_8_forge_boundary | 18 passed |
| 10 | Feedback v0 (§9) | §9 | `feedback_v0()` → MemoryStore + LearningLoop | test_9_feedback | 18 passed |
| 11 | EventBus (§11) | §11 | `_emit_event()` (candidates/evaluated/selected/reselected/feedback) | test_10_eventbus | 18 passed |
| 12 | Persistence (§12) | §10 | `DecisionHistoryStore` (YAML atomic) | test_11_persistence | 18 passed |
| 13 | Backward compatibility (§21) | §15 | `propose()` BC-fallback (legacy ScenarioRegistry) | test_12/test_12b | 18 passed |
| 14 | Unavailable scenario (§18 #13) | §6 | select() → status='unavailable' | test_13/test_13b | 18 passed |
| 15 | Deferred opportunity (§18 #14) | §6 | select() read-only по lifecycle | test_14_deferred_opportunity | 18 passed |
| 16 | Re-selection after new evidence (§18 #15) | §6/§10 | select() → superseded/reselected | test_15_reselection_after_new_evidence | 18 passed |
| 17 | Главный integration test (§18) | §0–§15 | полный путь Opportunity→…→Memory | test_main_integration_vertical_slice | 18 passed |
| 18 | Domain-neutrality (§1/§4) | §0 | нет hardcoded "content"; capability — opaque tokens | (grep: scenario_intelligence.py) | code review |
| 19 | Регрессия Phase 5/7 (§21) | §15 | propose() сигнатура не изменена | test_intelligence_loop_phase5.py (12) + test_phase7_factory_event.py (26) + test_opportunity_engine.py (32) | 70 passed |

## 2. Files

| File | Role |
|------|------|
| `scripts_01/scenario_intelligence.py` | ядро Phase 8 (NEW) |
| `scripts_01/opportunity_engine.py` | адаптер propose() (изменён аддитивно) |
| `tests_09/test_scenario_intelligence.py` | тесты §18 (NEW, 18 тестов) |
| `tests_09/test_intelligence_loop_phase5.py` | регрессия (score fix) |
| `phase8_evaluation_29/` | forensics + contract + plan + traceability + eval report + next phase |

## 3. Anti-overengineering check (§20)

| Не создано | Проверка |
|------------|----------|
| второй Scenario Registry | `discover()` использует существующий ScenarioRegistry |
| новый Factory engine | `resolve_capability()` → FactoryRegistry |
| новый Forge | ForgeFacade остаётся execution boundary |
| новая Memory | feedback → MemoryStore (kind=candidate) |
| новый EventBus | `_emit_event()` → существующий EventBus |
| новая БД | DecisionHistoryStore = YAML (по образцу opportunities.yaml) |
| новый LLM framework | нет |
| доменно-специфичные контракты | нет (domain-neutral) |

---
_Traceability complete. 19/19 requirement rows CONFIRMED._
