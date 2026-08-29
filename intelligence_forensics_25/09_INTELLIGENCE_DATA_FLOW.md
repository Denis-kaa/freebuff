# 09 — INTELLIGENCE DATA FLOW

> Проекция этапов Project Intelligence Model (промт §10) на существующие primitives.

## F1. Цепочка с классификацией

| Этап | Классификация | Существующий primitive / evidence |
|------|---------------|-----------------------------------|
| OBSERVE | EXISTING | `ProjectPulse` (git/file/event), `EventBus` |
| COLLECT | EXISTING | `WhimStore.capture` (whims.yaml) |
| UNDERSTAND | EXISTING | `SemanticLayer.search` (hybrid) + `LearningLoop.analyze` |
| CONNECT | EXISTING | `MemoryStore.find_related` / `shortest_path` |
| DISCOVER | **ADAPTER NEEDED** | `discover_candidates` (STUB) → реальные pulls (GAP-1) |
| OPPORTUNITY | EXISTING | `OpportunityEngine` (lifecycle) |
| SCENARIO | EXISTING | `ScenarioRegistry.propose_roles` |
| FACTORY | EXISTING | `FactoryRegistry.find_by_capability` |
| FORGE | EXISTING | `ForgeFacade.run_chain` |
| ARTIFACT | EXISTING | `RoleArtifactValidator` |
| MEMORY | **ADAPTER NEEDED** | `MemoryStore.store_knowledge` (GAP-2: execute() не пишет) |
| LEARNING | EXISTING | `LearningLoop.capture/record_feedback` |

## F2. Два реальных data-flow (сегодня)

### Flow A — существующий (STUB DISCOVER, без ACCUMULATE)
```
capture(whim) → triage(PROMOTE_CANDIDATE) → promote → Opportunity(READY)
   → propose(ScenarioRegistry) → execute(ForgeFacade.run_chain)
   → advance(COMPLETED)  [→ НЕТ записи в MemoryStore***REMOVED***
```

### Flow B — целевой (после GAP-1 + GAP-2)
```
OBSERVE (ProjectPulse) ─┐
COLLECT (Whim) ─────────┼→ DISCOVER (реальные pulls) → Opportunity
   → propose → execute(ForgeFacade.run_chain)
   → VALIDATE (RoleArtifactValidator)
   → ACCUMULATE (MemoryStore KO kind=opportunity)
   → LEARN (LearningLoop.record_feedback)
```

## F3. Whim→Opportunity (промт §12: «Whim ≠ автоматически Opportunity»)

**FACT:** `whim_capture.triage()` — только классификация (KEEP/DISCARD/PROMOTE_CANDIDATE), НЕ создаёт Opportunity.
**FACT:** `whim_capture.promote()` — ЯВНЫЙ шаг, требует `classification == "PROMOTE_CANDIDATE"`; иначе `ValueError`.
**FACT:** Связь `WHIM → CLASSIFICATION/ANALYSIS → POSSIBLE OPPORTUNITY` соблюдена: только PROMOTE_CANDIDATE + явный promote() создаёт Opportunity.
**DECISION:** Контракт §12 (Whim не авто-превращается) УЖЕ выполнен в коде — НЕ менять.

## F4. DEFERRED ≠ DELETED (промт §11)

**FACT:** Opportunity: `DEFERRED → REACTIVATED` (audit-trail label, коллапсирует в ACTIVE) — идея не теряется.
**FACT:** Whim: `DEFERRED → TRIAGED | DISCARDED | FAILED` — record сохраняется.
**FACT:** DISCARDED = terminal, но record ПРЕСЕРВИРОВАН (не удалён) — «audit trail preserved».
**DECISION:** Семантика DEFERRED ≠ DELETED реализована в обоих движках — НЕ менять.
