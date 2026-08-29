# PHASE5 IMPLEMENTATION LOG — v5.189.16

> Промт: `pompts_11/085_19_close_intelligence_loop.md` (PHASE 5 — CLOSE THE INTELLIGENCE LOOP v1.0)
> Дата: 2026-08-16
> Принцип: ADDITIVE (CAN-16) — ни один существующий модуль не переписан, только аддитивные изменения внутри `opportunity_engine.py` + тесты.

---

## 1. scripts_01/opportunity_engine.py — `discover_candidates()` (GAP-1: REAL DISCOVER)

| Аспект | Значение |
|---|---|
| **FILE** | `scripts_01/opportunity_engine.py` |
| **SYMBOL** | `discover_candidates(project_id, max_results=10, source_paths=None)` |
| **OLD BEHAVIOUR** | Генерировал 5 stub-кандидатов на источник: `"Stub signal from {src***REMOVED***"` — production-path без реальных данных. Принимал `source_paths` бессвязно (ключи не совпадали с источниками). |
| **NEW BEHAVIOUR** | Реальный DISCOVER из 4 существующих источников: `_discover_from_whims` (WhimStore/whims.yaml), `_discover_from_pulse` (ProjectPulse/project_pulse.db), `_discover_from_events` (EventBus/event_log), `_discover_from_knowledge` (MemoryStore/context.db). Каждый кандидат несёт provenance: `source`, `source_id`, `project_id`, `timestamp`, `reason`, `evidence`, `confidence`, `stub=False`. `source_paths` — явный dict ключей `whims/pulse/events/memory` (совпадает с CLI-флагами). Stub-источник сохранён только как явный fallback с `stub=True` (НЕ production path по умолчанию). |
| **WHY** | §7: «ЗАПРЕЩЕНО оставлять production-path на уровне "Stub signal from ...", если соответствующий источник уже существует». Все 4 источника реально существуют (проверено в Этапе 0). |
| **TEST** | `test_1_real_whim_source_discover_candidate`, `test_1b_no_stub_when_sources_empty`, `test_2_candidate_to_opportunity`, `test_8_repeated_source_no_duplicate` |
| **EVIDENCE** | pytest 113/113 (5 файлов), provenance-поля ассертятся в тестах. |

## 2. scripts_01/opportunity_engine.py — `_SOURCE_DEFAULTS` (module-level)

| Аспект | Значение |
|---|---|
| **FILE** | `scripts_01/opportunity_engine.py` |
| **SYMBOL** | `_SOURCE_DEFAULTS: Tuple[Tuple[str, Callable, Path***REMOVED***, ...***REMOVED***` |
| **OLD** | отсутствовал; список источников собирался внутри функции каждый вызов |
| **NEW** | module-level кортеж `(ключ, функция-источник, дефолтный путь)` — единая точка регистрации источников; `discover_candidates` итерирует его, переопределяя пути из `source_paths` |
| **WHY** | ревью round-2 нит: единый источник истины для списка источников; DRY |
| **TEST** | тесты TEST 1-10 (непрямо — через discover) |
| **EVIDENCE** | mypy 0 ошибок по файлу |

## 3. scripts_01/opportunity_engine.py — `_lazy_import()` (helper)

| Аспект | Значение |
|---|---|
| **SYMBOL** | `_lazy_import(module_name, attr) -> Any` |
| **OLD** | top-level imports всех источников — падение при отсутствии модуля |
| **NEW** | ленивый импорт с fallback `scripts_01.X` → `X`; при недоступности возвращает `None` (источник пропускается, `_LAZY_IMPORT_ERRORS` фиксирует) |
| **WHY** | §17 error handling: недоступность источника не роняет DISCOVER целиком |
| **TEST** | `test_1b_no_stub_when_sources_empty` (пустые пути), тесты с фейковыми модулями |
| **EVIDENCE** | mypy clean; `_LAZY_IMPORT_ERRORS` в evidence-ledger |

## 4. scripts_01/opportunity_engine.py — dedup (idempotency §18)

| Аспект | Значение |
|---|---|
| **SYMBOL** | dedup-логика в `discover_candidates` через `OpportunityStore.find_by_provenance` |
| **OLD** | не было dedup; повторный discover создавал дубликаты |
| **NEW** | кандидаты с уже существующим provenance-ключом (source+source_id) пропускаются; dedup выполняется ДО финального `max_results`-среза (ревью round-1 фикс) |
| **WHY** | §18: «Один и тот же сигнал не должен бесконечно создавать одинаковые Opportunity» |
| **TEST** | `test_8_repeated_source_no_duplicate`, `test_discover_dedup_by_provenance` |
| **EVIDENCE** | тест 8: второй discover того же источника → 0 новых записей |

## 5. scripts_01/opportunity_engine.py — `accumulate()` (GAP-2: ACCUMULATE)

| Аспект | Значение |
|---|---|
| **SYMBOL** | `accumulate(opp, memory_store=None, learning_loop=None) -> Optional[str***REMOVED***` |
| **OLD** | отсутствовал (docstring обещал ACCUMULATE — код не делал) |
| **NEW** | Artifact → `MemoryStore.store_knowledge(kind="candidate", tags=["opportunity", opp.project_id***REMOVED***, content=JSON-artifact)` + `record_learning_event(kind="opportunity", outcome=...)` + `LearningLoop.record_feedback(knowledge_id, outcome)` (best-effort). Lineage: `opp.provenance["memory_knowledge_id"***REMOVED*** = knowledge_id`. Ошибки Memory/Learning НЕ меняют статус opportunity — пишутся в `provenance["accumulate_error"***REMOVED***` (§17 partial failure). |
| **WHY** | §9/§10/§11: результат execution обязан вернуться в Memory и Learning через существующие механизмы |
| **TEST** | `test_6_artifact_to_memory`, `test_7_memory_to_learning`, `test_4_5_execution_accumulates` |
| **EVIDENCE** | KO создаётся с kind=`candidate` (CAN-16: `KNOWLEDGE_KINDS` не содержит `opportunity`, тест ассертит `len==10` — НЕ трогали), тег `opportunity`; learning event записан |

## 6. scripts_01/opportunity_engine.py — `execute()` status normalization

| Аспект | Значение |
|---|---|
| **SYMBOL** | `execute(opp, *, dry_run=False, memory_store=None, learning_loop=None)` |
| **OLD** | `advance(opp, "COMPLETED")` напрямую — InvalidTransition из ACTIVE; retry FAILED → COMPLETED падал; повторный сбой retry → FAILED→FAILED InvalidTransition |
| **NEW** | нормализация ДО run_chain: `if opp.status in ("ACTIVE", "FAILED"): opp = advance(opp, "READY", reason="execution started")` → оба пути валидны: success READY→COMPLETED, failure READY→FAILED. Retry FAILED→READY→COMPLETED работает (§17 retry, promt 079_19 §3.1 #7). |
| **WHY** | ревью rounds 1/4: реальные баги state machine, всплывшие при тестах |
| **TEST** | `test_10b_failed_retry_success_completes`, `test_10c_failed_retry_failure_stays_failed` (регрессия фикса) |
| **EVIDENCE** | 10b: FAILED→execute→COMPLETED, `previous_status=="READY"`; 10c: повторный сбой остаётся FAILED, без InvalidTransition |

## 7. scripts_01/opportunity_engine.py — `_accumulate_best_effort()`

| Аспект | Значение |
|---|---|
| **SYMBOL** | `_accumulate_best_effort(opp, *, memory_store=None, learning_loop=None)` |
| **OLD** | отсутствовал |
| **NEW** | обёртка: вызывает `accumulate()` в try/except, ошибки → `provenance["accumulate_error"***REMOVED***`, статус не меняется; вызывается из `execute()` на обоих исходах (COMPLETED → outcome "success", FAILED → outcome "failure") |
| **WHY** | §17: Memory failure не должен ломать opportunity lifecycle |
| **TEST** | `test_4_5_execution_accumulates`, `test_e2e_vertical_slice` |
| **EVIDENCE** | E2E: после COMPLETED KO в MemoryStore, learning event записан |

## 8. scripts_01/opportunity_engine.py — CLI `discover` flags

| Аспект | Значение |
|---|---|
| **SYMBOL** | `_cli_discover` (argparse): `--whim-path`, `--pulse-db`, `--event-db`, `--memory-db` |
| **OLD** | CLI discover без флагов путей (stub-данные) |
| **NEW** | флаги маппятся в `source_paths` ключи `whims/pulse/events/memory` — совпадает с контрактом `discover_candidates` (ревью round-1 фикс рассинхрона "memory"/"knowledge") |
| **WHY** | герметичность CLI; пользователь может указать свои пути |
| **TEST** | `test_cli_discover_creates_records` |
| **EVIDENCE** | CLI с флагами создаёт записи из tmp-whims.yaml |

## 9. tests_09/test_intelligence_loop_phase5.py — НОВЫЙ (12 тестов)

| Аспект | Значение |
|---|---|
| **FILE** | `tests_09/test_intelligence_loop_phase5.py` (435 строк) |
| **OLD** | отсутствовал |
| **NEW** | TEST 1-10 (§19) + E2E vertical slice (§20) + регрессии 10b/10c; `_hermetic_sources()` helper — все 4 пути источников указывают на несуществующие tmp-файлы (герметичность, ревью rounds 2/3); ForgeFacade/ScenarioRegistry мокаются через `sys.modules`; MemoryStore — реальный tmp (не data_13/context.db) |
| **WHY** | §19 TEST-FIRST / §20 E2E; защита production-БД |
| **TEST** | 12/12 green |
| **EVIDENCE** | pytest: 113 passed (5 файлов) |

## 10. tests_09/test_opportunity_engine.py — герметичность старых тестов

| Аспект | Значение |
|---|---|
| **SYMBOL** | `test_discover_with_real_whim_source`, `test_discover_dedup_by_provenance`, `test_cli_discover_creates_records`, `test_discover_candidates_always_returns_list`, `test_discover_respects_max_results` |
| **OLD** | читали реальные `data_13/project_pulse.db`, `context_12/events.db`, `data_13/context.db` (негерметично, тащили реальные кандидаты) |
| **NEW** | передают полный dict путей на tmp/несуществующие файлы |
| **WHY** | ревью round-3: тесты не должны зависеть от состояния production-БД |
| **TEST** | 31/31 green |
| **EVIDENCE** | pytest: файл полностью зелёный |

---

## Сводка изменённых файлов

| Файл | Тип | Строк |
|---|---|---|
| `scripts_01/opportunity_engine.py` | изменён (аддитивно) | 951 |
| `tests_09/test_intelligence_loop_phase5.py` | создан | 435 |
| `tests_09/test_opportunity_engine.py` | изменён (герметичность) | 519 |
| `phase5_intelligence_loop_26/01_PRE_IMPLEMENTATION_AUDIT.md` | создан (Этап 0) | — |
| `phase5_intelligence_loop_26/*.md` (этот пакет) | созданы | — |
| `data_13/missing_registry.yaml` | `intelligence_integration` → implemented | — |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | §20 row #17 → implemented | — |
| `CHANGELOG.md` | v5.189.16 | — |
