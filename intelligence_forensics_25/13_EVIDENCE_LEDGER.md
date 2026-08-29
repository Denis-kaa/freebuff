# 13 — EVIDENCE LEDGER

> Каждый важный вывод: ID / CLAIM / TYPE / SOURCE / SYMBOL / EVIDENCE / CONFIDENCE / DEPENDENCIES.
> TYPE: FACT / INFERENCE / ASSUMPTION / HYPOTHESIS / DECISION.

| ID | CLAIM | TYPE | SOURCE | SYMBOL | EVIDENCE | CONFIDENCE |
|----|-------|------|--------|--------|----------|------------|
| E-01 | Opportunity Engine реализован | FACT | scripts_01/opportunity_engine.py | `Opportunity`, `OpportunityStore`, `advance`, `discover_candidates`, `propose`, `execute` | полный исходник + 68 tests passed | HIGH |
| E-02 | Whim Capture реализован | FACT | scripts_01/whim_capture.py | `Whim`, `WhimStore`, `capture`, `triage`, `promote` | полный исходник + 68 tests | HIGH |
| E-03 | Concept Evolution отсутствует | FACT | grep repo | `concept_evolution`/`ConceptEvolution` → 0 matches | grep 0 | HIGH |
| E-04 | Forge вызывается только через ForgeFacade | FACT | core_02/forge_facade.py | `ForgeFacade.initiate_forge` docstring «ForgePipeline инстанцируется ТОЛЬКО здесь» | docstring + gate `can_initiate` | HIGH |
| E-05 | Direct Forge call из Scenario запрещён (§7.3) | FACT | core_02/forge_facade.py | `REFERENCE_ROLES`, `can_initiate` | gate code | HIGH |
| E-06 | UNFORGED ≠ UNTESTED (B10/R-127) | FACT | core_02/forge_registry.py | `validate_schema` | machine invariants | HIGH |
| E-07 | DISCOVER — STUB-источники | FACT | scripts_01/opportunity_engine.py | `discover_candidates` → `provenance={"stub": True***REMOVED***` | code | HIGH |
| E-08 | ACCUMULATE не реализован (drift) | FACT | scripts_01/opportunity_engine.py | header «ACCUMULATE…» vs `execute` без `store_knowledge` | code diff | HIGH |
| E-09 | Whim→Opportunity не автоматический | FACT | scripts_01/whim_capture.py | `promote` требует `classification=="PROMOTE_CANDIDATE"` | code | HIGH |
| E-10 | DEFERRED ≠ DELETED реализовано | FACT | opportunity_engine.py + whim_capture.py | `DEFERRED→REACTIVATED`, «audit trail preserved» | code | HIGH |
| E-11 | Memory/Knowledge пригодны для Intelligence State | INFERENCE | core_02/memory_store.py + semantic_layer.py + learning_loop.py | 10 KO kinds, граф, AFC, hybrid search | code + 38 tests | HIGH |
| E-12 | Signal abstraction не нужен | DECISION | scripts_01/event_bus.py + project_pulse.py | EventBus wildcard + Pulse покрывают OBSERVE | analysis | MEDIUM-HIGH |
| E-13 | Минимальный path = GAP-1+GAP-2+GAP-4/5 | DECISION | 06_GAP_MAP.md | G1×2 + G2×2 | analysis | HIGH |
| E-14 | Traceability для Intelligence готова | FACT | core_02/anchors_resolver.py | `@opportunity`/`@whim` → YAML-store | code + 177 tests | HIGH |
| E-15 | Opportunity/Whim контракты не в реестре | FACT | docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md (не содержит §E Opportunity/§17.1 Whim) | code vs doc | grep | HIGH |
| E-16 | Scheduler как имя отсутствует | FACT | repo grep | нет `class Scheduler`; есть task_manager/prompt_queue/dispatcher | grep | HIGH |
| E-17 | 14 pipeline-ролей в run_chain | FACT | core_02/forge_facade.py | `PIPELINE_CHAIN` (14) + LIGHT/HEAVY/CONDITIONAL | code | HIGH |
| E-18 | Opportunity lifecycle forward-only, COMPLETED terminal | FACT | scripts_01/opportunity_engine.py | `TERMINAL_STATUSES=("COMPLETED",)` | code | HIGH |

---

## Canonical anchors (self-verifying)

Пакет самопроверяется: `python -m core_02.anchors_resolver intelligence_forensics_25 --workspace .` должен резолвить все анкоры ниже в `CURRENT`.

- @module scripts_01.opportunity_engine
- @module scripts_01.whim_capture
- @module core_02.forge_facade
- @module core_02.anchors_resolver
- @symbol Opportunity.to_dict
- @symbol OpportunityStore.upsert
- @symbol Whim.to_dict
- @symbol WhimStore.upsert
- @symbol ForgeFacade.run_chain
- @symbol ForgeFacade.initiate_forge
- @symbol RoleArtifactValidator.validate
- @symbol MemoryStore.store_knowledge
- @symbol SemanticLayer.semantic_search
- @symbol LearningLoop.capture
- @symbol EventBus.publish
- @symbol ProjectPulse.list
- @symbol AnchorResolver.resolve
- @symbol ScenarioRegistry.propose_roles
- @symbol FactoryRegistry.find_by_capability
- @symbol ForgeRegistry.record_run
- @symbol ForgePassport.validate
- @symbol Workspace.load
- @symbol Project.load
- @symbol WorkspaceRegistry.create_workspace
