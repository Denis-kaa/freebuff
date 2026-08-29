# PHASE8_GAP_MAP.md — Gap Map (Universal Scenario Intelligence)

> Phase 8 (promt 91) §15. Проверяется поведение, а не названия.
> G0 — существует · G1 — adapter · G2 — design exists · G3 — implementation required · G4 — conflict.

## 1. Gap map

| # | Area | Current behavior | Phase 8 requirement | Classification | Evidence |
|---|------|------------------|---------------------|----------------|----------|
| G0-1 | Scenario catalog | `ScenarioRegistry.list_scenarios/get/find_role/all_roles` — работают, domain-neutral | каталог кандидатов (§5) | **G0** (переиспользовать) | `core_02/scenario_registry.py` (tests green) |
| G0-2 | Capability → factory/forge | `FactoryRegistry.select_forge(capability, prefer_status)` + `capability_catalog()` — работают | capability resolution (§8) | **G0** (переиспользовать) | `core_02/factory_registry.py` (C-2, v5.189.21) |
| G0-3 | Execution boundary | `ForgeFacade.run_chain(project, role_ids)` — единственный мост | ForgeFacade остаётся execution boundary | **G0** (не трогать) | `core_02/forge_facade.py` + Phase 7 tests |
| G0-4 | Feedback storage | `MemoryStore.store_knowledge/record_learning_event` + `LearningLoop.record_feedback` | transparent feedback v0 (§9) | **G0** (переиспользовать) | `core_02/memory_store.py`, `core_02/learning_loop.py` |
| G0-5 | Events | `EventBus.publish(Event)` canonical; Phase 7 events (execution.*, opportunity.*, scenario.selected, whim.*) | события §11 | **G0** (bus) / **G1** (новые типы) | `scripts_01/event_bus.py` || G1-1 | Scenario selection — топ-1 | `opportunity_engine.propose()` берёт `propose_roles[0***REMOVED***` без evaluation/ranking/reasons | multiple candidates → evaluation → ranking → selection (§5–§7) | **G1** (adapter: delegate к ScenarioIntelligence) | `scripts_01/opportunity_engine.py::propose` (строки 767–811) |
| G1-2 | Composite scoring | score = keyword overlap (propose_roles); нет capability/history/feasibility компонент | объяснимый score = Σ wᵢ·componentᵢ + reasons + evidence (§7) | **G1** (evaluation adapter поверх G0-1) | `core_02/wizard_lib.py::score_role_match` (fuzzy) |
| G1-3 | Capability от сценария | `_derive_capability` читает `scenario.capability`, но `propose()` его не заполняет (только scenario_id/role_id/score/title) | Scenario → CapabilityRequirement → FactoryRegistry (§8) | **G1** (заполнять capability при selection) | `opportunity_engine.propose()` opp.scenario dict |
| G1-4 | Event типы | нет `scenario.candidates.generated` / `scenario.evaluated` / `scenario.reselected` | только реально нужные события (§11) | **G1** (emitter в новом слое) | `scripts_01/event_bus.py` + Phase 7 events |
| G2-1 | `scenario_engine` (Missing #2) | design_ready (kind=system, prompt_path=SCENARIO_ENGINE_DESIGN_V1.md), impl=None | универсальный Scenario Intelligence | **G2** (design exists) → перекрывается Phase 8 `scenario_intelligence`; при имплементации Phase 8 запись `scenario_engine` должна быть сверена (superseded или оставлена design_ready) — не плодить дублирующий design-intent | `data_13/missing_registry.yaml` |
| G3-1 | Scenario Intelligence module | отсутствует (grep: нет `scenario_intelligence` до этой сессии) | domain-neutral decision layer | **G3** (implementation required) | — |
| G3-2 | Decision history (re-selection) | нет history выбранных сценариев (selected/superseded/reselected) | §10 lifecycle + §18 #15 re-selection после нового evidence | **G3** (лёгкий store / MemoryStore kind=scenario_decision) | `data_13/` нет scenario_decisions |
| G3-3 | Scenario-level feedback | feedback только на уровне opportunity (accumulate, kind=candidate) | §9 feedback v0: scenario outcome → будущий ranking | **G3** (kind=scenario_decision + learning event) | `MemoryStore.query_by_type('scenario_decision')` = пусто |
| G4-1 | Domain-neutrality | нет hardcoded "content" в opportunity/scenario/factory слоях | ни один контракт не зависит от домена (§1/§4) | **G0/проходит** (нет violation) | grep по opportunity_engine/scenario_registry/factory_registry |
| G4-2 | Дублирование registry | только один ScenarioRegistry / один FactoryRegistry | не создавать второй (§5/§20) | **G0/проходит** | grep |
| G4-3 | Закрытый словарь capability (ANTI-6b) | FactoryRegistry фильтрует по `capabilities ⊆ KNOWN_CAPABILITIES`; токен вне словаря → `select_forge` вернёт None | capability-токены Phase 8 ДОЛЖНЫ быть в `KNOWN_CAPABILITIES` (иначе silent-fallback на слабую модель при «зелёных» тестах) | **G0/проходит** (механизм есть) / **G1** (слой должен генерировать токены из закрытого словаря; G1-фасет отслеживается под G1-2/G1-3) | `core_02/factory_registry.py` + ANTI-6b/CON-8 (LESSONS) |

## 2. Вывод по GAP-классификации

| Class | Count | Items |
|-------|-------|-------|
| **G0** (существует, переиспользовать) | 7 | catalog, capability resolution, execution boundary, feedback storage, events bus, domain-neutrality, no-dup |
| **G1** (adapter) | 4 | selection-делегирование, composite scoring, capability-заполнение, event типы |
| **G2** (design exists) | 1 | `scenario_engine` (design_ready → перекрывается Phase 8) |
| **G3** (implementation required) | 3 | Scenario Intelligence module, decision history, scenario-level feedback |
| **G4** (conflict) | 0 | — |

## 3. Минимальный vertical slice (что закрывает G1+G3)

> ⚠️ Temporal note: forensics зафиксированы ДО завершения реализации; на момент
> документа реализация уже частично начата (scripts_01/scenario_intelligence.py
> создан, propose() делегирует с BC-fallback, реестр: scenario_intelligence =
> prompt_written). Slice ниже — целевой контракт, независимо от текущего прогресса.

```
opportunity_engine.propose()                 [G1-1 adapter***REMOVED***
  → ScenarioIntelligence.discover(opp)      [G3-1 module; G0-1 catalog***REMOVED***
  → ScenarioIntelligence.evaluate(...)      [G1-2 composite score; G0-4 history; G4-3: токены ⊆ KNOWN_CAPABILITIES***REMOVED***
  → ScenarioIntelligence.rank(...)          [объяснимо: score + reasons***REMOVED***
  → ScenarioIntelligence.select(...)        [G1-3 capability; G1-4 events; G3-2 history***REMOVED***
  → CapabilityRequirement → FactoryRegistry.select_forge [G0-2; G4-3 закрытый словарь***REMOVED***
  → ForgeFacade.run_chain                   [G0-3 EXECUTION BOUNDARY***REMOVED***
  → feedback_v0 → MemoryStore kind=scenario_decision [G3-3***REMOVED***
```

---
_Phase 8 Gap Map complete. 0 конфликтов; минимальный slice = 1 новый модуль + adapter в propose()._
