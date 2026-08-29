# 03 — INTELLIGENCE INTEGRATION MAP

> Целевая карта: EXISTING PLATFORM → PRIMITIVES → CONTRACTS → CAPABILITIES → GAPS → MINIMAL PATH.

## M1. Итоговая карта

```
EXISTING PLATFORM (Phase 4, v5.189.14)
      │
      ├─ OBSERVE   → ProjectPulse (git/file/event) + EventBus (pub/sub)        [G0***REMOVED***
      ├─ COLLECT   → Whim Capture (whims.yaml) + Opportunity DISCOVER (stub)   [G0/G1***REMOVED***
      ├─ UNDERSTAND→ SemanticLayer.hybrid_search + LearningLoop.analyze         [G0***REMOVED***
      ├─ CONNECT   → MemoryStore.find_related / shortest_path (graph)          [G0***REMOVED***
      ├─ DISCOVER  → OpportunityEngine.discover_candidates (STUB-источники)    [G1***REMOVED***
      ├─ OPPORTUNITY→ OpportunityEngine (lifecycle ACTIVE/DEFERRED/READY/…)     [G0***REMOVED***
      ├─ SCENARIO  → ScenarioRegistry.propose_roles (fuzzy-match)              [G0***REMOVED***
      ├─ FACTORY   → FactoryRegistry.find_by_capability                        [G0***REMOVED***
      ├─ FORGE     → ForgeFacade.run_chain (единственный мост §7.3)             [G0***REMOVED***
      ├─ ARTIFACT  → RoleArtifactValidator (existence)                         [G0***REMOVED***
      ├─ MEMORY    → MemoryStore KO (kind=…) + LearningLoop.codify             [G0/G1***REMOVED***
      └─ LEARNING  → LearningLoop.record_feedback (confidence)                 [G0***REMOVED***
```

## M2. Где Intelligence подключается (14 capabilities × existing primitive)

| Capability | Existing Primitive | Evidence | Adapter | New Code | Risk |
|-----------|-------------------|----------|---------|----------|------|
| OBSERVE | `ProjectPulse` + `EventBus` | scripts_01/project_pulse.py, event_bus.py | — | — | Низкий |
| COLLECT | `WhimStore.capture` | scripts_01/whim_capture.py | TG/MCP hook | — | Низкий |
| UNDERSTAND | `SemanticLayer.search` | core_02/semantic_layer.py | — | — | Низкий |
| CONNECT | `MemoryStore.find_related` | core_02/memory_store.py | — | — | Низкий |
| DISCOVER | `discover_candidates` (STUB) | scripts_01/opportunity_engine.py | **реальные pulls** | — | Средний |
| OPPORTUNITY | `Opportunity` + `advance` | scripts_01/opportunity_engine.py | — | — | Низкий |
| SELECT SCENARIO | `ScenarioRegistry.propose_roles` | core_02/scenario_registry.py | — | — | Низкий |
| EXECUTE | `ForgeFacade.run_chain` | core_02/forge_facade.py | — | — | Низкий |
| VALIDATE | `RoleArtifactValidator` | core_02/forge_facade.py | — | — | Низкий |
| ACCUMULATE | `MemoryStore.store_knowledge` | core_02/memory_store.py | **execute()→KO write** | — | Средний |
| LEARN | `LearningLoop.capture/record_feedback` | core_02/learning_loop.py | — | — | Низкий |
| REACTIVATE | `advance(DEFERRED→REACTIVATED)` | scripts_01/opportunity_engine.py | — | — | Низкий |
| TRACE | `AnchorResolver` (17 @-ns + doc.*) | core_02/anchors_resolver.py | — | — | Низкий |
| PROVENANCE | `Opportunity.provenance` / `Whim.provenance` | scripts_01/*.py | — | — | Низкий |

## M3. Ключевые точки интеграции (явные)

1. **Whim → Opportunity** — УЖЕ связан: `whim_capture.promote()` лениво создаёт `Opportunity` с `related_whims=[whim.id***REMOVED***`, `source="whim:..."`.
2. **Opportunity → Scenario** — УЖЕ связан: `opportunity_engine.propose()` → `ScenarioRegistry.propose_roles(...)`.
3. **Opportunity → Forge** — УЖЕ связан: `opportunity_engine.execute()` → `ForgeFacade.run_chain(...)` (соблюдает §7.3).
4. **Memory ← Opportunity** — ЧАСТИЧНО: docstring заявляет `ACCUMULATE (memory_store KO kind=opportunity + Learning Loop capture)`, но `execute()` НЕ пишет в MemoryStore. → **G1 adapter**.
5. **Event/Observation → Intelligence** — ЧАСТИЧНО: `Opportunity.SOURCES` включает `project_pulse`/`event_bus`/`knowledge`, но `discover_candidates` генерирует STUB-кандидатов, а не реальные pulls. → **G1 adapter**.

## M4. Что НЕ смешивать (анти-пересечение)

**FACT:** Intelligence ≠ Factory (промт §10: «Intelligence не смешан с Factory»).
**FACT:** Concept Evolution ≠ Project Intelligence (промт §13) — отдельная будущая capability.
**DECISION:** Intelligence State = состояние поверх MemoryStore/SemanticLayer/LearningLoop, НЕ отдельная memory system.
