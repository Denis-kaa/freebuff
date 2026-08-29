# 10 — FIRST VERTICAL SLICE

> ОДИН минимальный end-to-end flow (промт §18). Состав адаптирован к фактическому repository.

## S1. Выбранный slice

**Цепочка:** `Whim → Opportunity (propose) → ForgeFacade.run_chain → RoleArtifactValidator → MemoryStore (KO kind=opportunity)`

**Почему этот slice:**
- Каждый элемент УЖЕ существует (см. 02/05), кроме 2 адаптеров (GAP-1, GAP-2).
- Он проверяет РЕАЛЬНУЮ цепочку INPUT→INTELLIGENCE→OPPORTUNITY→SCENARIO→FACTORY→FORGE→ARTIFACT→MEMORY без создания полноценного Intelligence Engine.

## S2. Поэтапно

| Шаг | Элемент | Статус | Файл |
|-----|---------|--------|------|
| 1. INPUT | `whim_capture capture "<body>" --project-id X` | EXISTING | scripts_01/whim_capture.py |
| 2. TRIAGE | `triage <id> --classification PROMOTE_CANDIDATE` | EXISTING | whim_capture.py |
| 3. OPPORTUNITY | `promote <id>` → Opportunity(READY) | EXISTING | whim_capture.py::promote |
| 4. SELECT | `propose(opp)` → ScenarioRegistry.propose_roles | EXISTING | opportunity_engine.py::propose |
| 5. EXECUTE | `execute(opp)` → ForgeFacade.run_chain | EXISTING | opportunity_engine.py::execute |
| 6. VALIDATE | RoleArtifactValidator (внутри run_chain) | EXISTING | forge_facade.py |
| 7. ACCUMULATE | `MemoryStore.store_knowledge(kind="opportunity")` | **GAP-2 (добавить)** | opportunity_engine.py |
| 8. LEARN | `LearningLoop.record_feedback` | EXISTING (подключить в шаг 7) | learning_loop.py |

## S3. Минимальные достройки (только 2)

1. **GAP-1** — `discover_candidates`: заменить STUB на реальные pulls (whims.yaml TRIAGED, ProjectPulse, MemoryStore observations).
2. **GAP-2** — `execute()`: после `advance(COMPLETED)` вызвать `MemoryStore.store_knowledge(kind="opportunity", ...)` + `LearningLoop.record_feedback`.

**FACT:** НЕ создавать полноценный Intelligence Engine (промт §18).
**FACT:** НЕ менять ForgeFacade/ScenarioRegistry/MemoryStore/LearningLoop (CAN-16 ADDITIVE — только opportunity_engine.py + whim_capture.py точечно).

## S4. Критерий готовности

**ONE REAL END-TO-END FLOW:** от `capture` до `COMPLETED` + KO в MemoryStore + learning event — воспроизводимо CLI-командами и покрыто тестом.
