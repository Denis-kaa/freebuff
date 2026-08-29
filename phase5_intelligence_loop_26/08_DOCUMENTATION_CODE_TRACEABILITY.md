# PHASE5 DOCUMENTATION ↔ CODE TRACEABILITY — v5.189.16

> §21: каждый architectural claim имеет связь DOCUMENT → ANCHOR → CODE SYMBOL → TEST.
> AnchorResolver (19 namespace) — существующая traceability, новая НЕ создана.

---

## Таблица traceability

| Claim (документ) | Anchor | Code Symbol | Test |
|---|---|---|---|
| «DISCOVER использует реальные источники» (промт 085 §7) | `opportunity_engine.discover_candidates` | `discover_candidates()` + `_SOURCE_DEFAULTS` | `test_1_real_whim_source_discover_candidate` |
| «Provenance у каждого candidate» (§8) | `opportunity_engine.provenance` | `source/source_id/reason/evidence/confidence` в кандидате | `test_1_real_whim_source_discover_candidate` (assert поля) |
| «Stub не production path» (§7) | `opportunity_engine.stub_fallback` | `_stub_fallback(..., stub=True)` — только явный fallback | `test_1b_no_stub_when_sources_empty` |
| «Dedup §18» | `opportunity_engine.find_by_provenance` | `OpportunityStore.find_by_provenance` в discover | `test_8_repeated_source_no_duplicate` |
| «ACCUMULATE: Artifact → Memory» (§9) | `opportunity_engine.accumulate` | `accumulate()` → `MemoryStore.store_knowledge(kind="candidate")` | `test_4_5_execution_accumulates` |
| «Lineage Opportunity→Artifact→Memory» (§10) | `opportunity_engine.memory_knowledge_id` | `opp.provenance["memory_knowledge_id"***REMOVED***` | `test_4_5_execution_accumulates` (assert lineage) |
| «Learning получает результат» (§11) | `memory_store.record_learning_event` | `record_learning_event(kind="opportunity")` + `LearningLoop.record_feedback` | `test_6_7_memory_to_learning` |
| «Forge только через ForgeFacade» (§16) | `opportunity_engine.forge_facade` | `_lazy_import("core_02.forge_facade", "ForgeFacade")` → `run_chain` | `test_10_failure_not_false_completed` (fake module в sys.modules) |
| «DEFERRED ≠ DELETED» (§13) | `opportunity_engine.advance` | lifecycle states без изменений; DEFERRED → REACTIVATED | `test_9_deferred_remains_recoverable` |
| «Ошибки не маскируются как COMPLETED» (§17) | `opportunity_engine.execute` | FAILED-ветка + `provenance["accumulate_error"***REMOVED***` | `test_10_failure_not_false_completed`, `test_10c` |
| «Retry» (§17) | `opportunity_engine.execute` | READY-normalization до run_chain | `test_10b`, `test_10c` |
| «CAN-16: KNOWLEDGE_KINDS не изменён» | `memory_store.KNOWLEDGE_KINDS` | kind="candidate" + tag="opportunity" | `test_memory_store.py::test_all_kinds_known` (len==10 не тронут) |
| «Opportunity Contract 16 полей» | `contract_registry.opportunity` (#15) | `Opportunity` dataclass | `test_2_candidate_to_opportunity` |
| «Whim Contract §17.1» | `contract_registry.whim` (#16) | `WhimStore` читается в `_discover_from_whims` | `test_1_real_whim_source_discover_candidate` |
| «Цикл замкнут: Memory → следующий DISCOVER» (§5) | `opportunity_engine.discover_from_knowledge` | `_discover_from_knowledge` читает MemoryStore (context.db) | E2E: discover → ... → memory → (источник для след. цикла) |

## Обновлённая документация (только изменившаяся)

| Документ | Изменение |
|---|---|
| `phase5_intelligence_loop_26/*` (11 файлов + README + MANIFEST) | полный evaluation-пакет §27 |
| `data_13/missing_registry.yaml` | `intelligence_integration`: prompt_written → implemented |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | §20 row #17: промт на реализацию → implemented |
| `CHANGELOG.md` | запись v5.189.16 |
| `scripts_01/opportunity_engine.py` module docstring | ACCUMULATE описание: kind=candidate (fix drift) |

## Документы, сознательно НЕ тронутые

`WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1`, `RFC_BUFFY_FORGE_V1`, `PLATFORM.md`, `BUFFY.md`, `TASK.md`, `CONTRACT_REGISTRY_V1` (контракты #15/#16 уже были) — их содержимое не изменилось в результате этой фазы.
