# PHASE5 INTELLIGENCE DATA FLOW — v5.189.16

> Целевой контур §5: REAL INPUT → OBSERVATION/WHIM → DISCOVER → OPPORTUNITY → SCENARIO → FACTORY → FORGE → ARTIFACT → VALIDATION → MEMORY → LEARNING → **следующий DISCOVER** (замкнутый цикл).

---

## Полный путь (реальные символы)

```
REAL INPUT (whims.yaml / project_pulse.db / event_log / context.db)
   │
   ▼
OBSERVATION / WHIM
   │  WhimStore (data_13/whims.yaml) — лёгкий вход (Whim ≠ Opportunity, §12)
   ▼
DISCOVER  ── scripts_01/opportunity_engine.py::discover_candidates(project_id, source_paths)
   │         └─ _discover_from_whims / _discover_from_pulse / _discover_from_events / _discover_from_knowledge
   │         └─ provenance: source, source_id, project_id, timestamp, reason, evidence, confidence
   │         └─ dedup: OpportunityStore.find_by_provenance (повторный сигнал → 0 дублей, §18)
   ▼
OPPORTUNITY  ── Opportunity dataclass (16 полей §E, CONTRACT_REGISTRY #15)
   │            lifecycle: ACTIVE → DEFERRED → REACTIVATED → READY → COMPLETED/FAILED (§13, §17)
   │            propose() → scenario_id (ScenarioRegistry, §14: Scenario = HOW)
   ▼
SCENARIO  ── существующий ScenarioRegistry / Scenario manifests (НЕ изменён, §14)
   ▼
FACTORY  ── существующий Factory/Passport путь (FactoryRegistry, НЕ изменён, §15)
   ▼
FORGE  ── ForgeFacade.run_chain(project_id, role_ids=[...***REMOVED***) — ЕДИНСТВЕННЫЙ санкционированный
   │      integration point (§16: НЕ обходить ForgeFacade; lazy-import с fallback)
   ▼
ARTIFACT  ── result.to_dict() / __dict__ / str → opp.artifacts = [{"raw": raw***REMOVED******REMOVED***
   │
   ▼
VALIDATION  ── (внутри run_chain: RoleArtifactValidator / ForgePipeline stage_check — существующие)
   ▼
MEMORY  ── accumulate() → MemoryStore.store_knowledge(
   │         kind="candidate",              ← CAN-16: KNOWLEDGE_KINDS НЕ изменён (нет kind=opportunity)
   │         tags=["opportunity", project_id***REMOVED***,
   │         content=JSON(artifact))
   │         lineage: opp.provenance["memory_knowledge_id"***REMOVED*** = knowledge_id
   ▼
LEARNING  ── MemoryStore.record_learning_event(kind="opportunity", outcome="success"|"failure")
   │         + LearningLoop.record_feedback(knowledge_id, outcome) → confidence обновляется
   ▼
следующий DISCOVER  ── MemoryStore (context.db) теперь сам является источником для
                        _discover_from_knowledge → цикл замкнут: результат цикла N
                        становится информацией для цикла N+1 (§5)
```

---

## Ошибки и частичные сбои (§17)

| Точка | Поведение | Статус opportunity |
|---|---|---|
| Источник недоступен | `_lazy_import` → None; источник пропущен; `_LAZY_IMPORT_ERRORS` | не влияет (DISCOVER вернёт меньше кандидатов) |
| `discover_candidates` исключение | пробрасывается (не скрывается) | — |
| ForgeFacade недоступен | `execute()` → FAILED + accumulate(failure) | FAILED |
| run_chain исключение | FAILED + `failure_reason` + accumulate(failure) | FAILED (не COMPLETED!) |
| Memory/Learning сбой | `provenance["accumulate_error"***REMOVED***` | НЕ меняется (partial failure, §17) |
| Retry FAILED | нормализация FAILED→READY до run_chain | COMPLETED (успех) / FAILED (повторный сбой) |

## Idempotency (§18)

- Dedup по provenance (source + source_id) при DISCOVER.
- Accumulate idempotent: повторный вызов для того же opp перезапишет lineage-поле, но KO создаётся один раз на выполнение (проверено в тесте 8).

## Разделение ответственности (§14)

- **Intelligence (этот пакет):** WHAT / WHY (DISCOVER + PROPOSE + ACCUMULATE).
- **Scenario:** HOW (выбор сценария — существующий Registry).
- **Factory:** CAPABILITY / PRODUCTION DOMAIN (существующий).
- **Forge:** EXECUTION (только через ForgeFacade).
