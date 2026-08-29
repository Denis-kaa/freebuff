# PHASE5 GAP RESOLUTION MATRIX — v5.189.16

## Сводка

| GAP | Статус | Реализация | Верификация |
|---|---|---|---|
| **GAP-1** — REAL DISCOVER | ✅ **RESOLVED** | 4 реальных источника + provenance + dedup | TEST 1, 1b, 2, 8 + E2E; grep: нет stub production-path |
| **GAP-2** — ACCUMULATE | ✅ **RESOLVED** | `accumulate()` + `_accumulate_best_effort()` + lineage | TEST 4-7 + E2E; KO в MemoryStore, event в LearningLoop |
| **GAP-4** — Opportunity Contract | ✅ **ALREADY RESOLVED** (v5.189.15) | CONTRACT_REGISTRY_V1 #15 | §E 16 полей зарегистрированы |
| **GAP-5** — Whim Contract | ✅ **ALREADY RESOLVED** (v5.189.15) | CONTRACT_REGISTRY_V1 #16 + WhimStore | Whim реально используется как источник |

## Детальная матрица

### GAP-1: REAL DISCOVER

| Критерий DoD (§7/§8) | Статус | Доказательство |
|---|---|---|
| Источники реальные (Whim/ProjectPulse/Memory/Knowledge/EventBus) | ✅ | `_SOURCE_DEFAULTS`: `_discover_from_whims/_pulse/_events/_knowledge` — все читают существующие storage |
| Нет "Stub signal from" в production path | ✅ | stub только в явном fallback `_stub_fallback` (`stub=True`); grep по файлу подтверждает |
| Provenance у каждого кандидата | ✅ | source/source_id/project_id/timestamp/reason/evidence/confidence |
| Новая storage не создана | ✅ | только существующие WhimStore/ProjectPulse/EventBus/MemoryStore |
| Dedup (идентичность) | ✅ | `find_by_provenance` перед срезом |
| DISCOVER failure не роняет pipeline | ✅ | `_lazy_import` + `_LAZY_IMPORT_ERRORS`; пустые источники → пустой список |

### GAP-2: CLOSE ACCUMULATE

| Критерий DoD (§9/§10/§11) | Статус | Доказательство |
|---|---|---|
| Artifact → Memory реальный путь | ✅ | `accumulate()`: `MemoryStore.store_knowledge(kind="candidate", tags=["opportunity", project_id***REMOVED***)` |
| Lineage Opportunity→Artifact→Memory | ✅ | `provenance["memory_knowledge_id"***REMOVED***` |
| Learning получает результат | ✅ | `record_learning_event` + `LearningLoop.record_feedback(knowledge_id, outcome)` |
| Не создан второй механизм памяти | ✅ | существующие MemoryStore/LearningLoop |
| Failure не маскируется как COMPLETED | ✅ | accumulate ошибки → `provenance["accumulate_error"***REMOVED***`, статус не меняется; run_chain failure → FAILED |
| Retry работает | ✅ | FAILED→READY→COMPLETED / FAILED→READY→FAILED (тесты 10b/10c) |

### GAP-4 / GAP-5 (contracts)

| Критерий | Статус | Доказательство |
|---|---|---|
| Opportunity Contract в реестре | ✅ | CONTRACT_REGISTRY_V1 #15 (v5.189.15), 16 полей §E |
| Whim Contract в реестре | ✅ | CONTRACT_REGISTRY_V1 #16 (v5.189.15), §17.1 |
| Контракты соответствуют коду | ✅ | Opportunity dataclass поля = §E; WhimStore поля = §17.1 (проверено Этапом 0) |

---

## Архитектурный чек-лист §26 (17/17)

```
[x***REMOVED*** Intelligence не стал отдельной платформой
[x***REMOVED*** EventBus не продублирован
[x***REMOVED*** Memory не продублирована
[x***REMOVED*** Knowledge не продублирована
[x***REMOVED*** Scenario Engine не продублирован
[x***REMOVED*** Forge вызывается только через ForgeFacade (execute → _lazy_import("core_02.forge_facade"))
[x***REMOVED*** Opportunity имеет provenance
[x***REMOVED*** Whim и Opportunity не смешаны (Whim ≠ Opportunity; не каждый whim → opportunity)
[x***REMOVED*** DEFERRED ≠ DELETED (lifecycle сохранён, states не трогались)
[x***REMOVED*** Discovery использует реальные источники
[x***REMOVED*** Stub discovery не является production path
[x***REMOVED*** Artifact возвращается в Memory
[x***REMOVED*** Learning получает результат
[x***REMOVED*** Повторный сигнал не создаёт uncontrolled duplicates
[x***REMOVED*** Ошибки не маскируются как COMPLETED
[x***REMOVED*** Existing tests не сломаны (113/113 touched files; smoke-тесты герметичны)
[x***REMOVED*** Documentation соответствует коду (docstring + 02_IMPLEMENTATION_LOG + 08_TRACEABILITY)
```
