# 01_PRE_IMPLEMENTATION_AUDIT.md — Phase 5: Close the Intelligence Loop

**Промт:** `pompts_11/085_19_close_intelligence_loop.md` (PHASE 5 — CLOSE THE INTELLIGENCE LOOP v1.0)
**Дата:** 2026-08-16
**Версия платформы:** v5.189.16 (в работе)
**Forensics baseline:** `INTELLIGENCE_INTEGRATION_FORENSICS_V1` (пакет `intelligence_forensics_25/`)

> Этап 0 промта 085 (§6): до написания кода зафиксировать текущий статус GAP-1/2/4/5
> с фактическими файлами, symbols, call paths, тестами. Формат: FACT / EVIDENCE / DECISION.

---

## 1. GAP-1 — REAL DISCOVER (stub → реальные источники)

**FACT:** `scripts_01/opportunity_engine.py::discover_candidates()` (строки 266–296) генерирует
**5 stub-кандидатов** — по одному на каждый источник из `SOURCES`:
`title="Stub signal from {src***REMOVED***"`, `provenance={"source_scan": src, "stub": True***REMOVED***`.

**EVIDENCE:**
- `grep 'Stub signal'` → `opportunity_engine.py:280` — production-path на уровне стуба.
- Docstring функции сам признаёт: *"Real source hooks (whim_capture, project_pulse, event_bus, knowledge) will replace these stubs in Phase 1.x"*.
- Все 4 реальных источника **уже существуют** в репозитории:
  - `scripts_01/whim_capture.py::WhimStore` (YAML `data_13/whims.yaml`, 2 058 bytes) — API: `all()`, `by_status()`, `by_project()`, `get()`.
  - `scripts_01/project_pulse.py::ProjectPulse` (SQLite `data_13/project_pulse.db`) — API: `list(limit, event_type, source, since)` → `PulseEntry(id, event_type, title, description, source, ref, timestamp, metadata)`.
  - `scripts_01/event_bus.py::EventBus` (SQLite `context_12/events.db`) — API: `get_events(event_type, limit, since)` → `EventLogEntry(event_id, event_type, source, data_json, timestamp)`.
  - `core_02/memory_store.py::MemoryStore` (SQLite `data_13/context.db`, 2.5 MB) — API: `query_by_type(kind, limit)`, `query_all(limit)`, `store_knowledge(...)`.
- `tests_09/test_opportunity_engine.py` — 2 теста на discover: `test_discover_candidates_always_returns_list` (проверяет только поля, не содержимое — проходит и со стубами) и `test_discover_respects_max_results`.

**DECISION:** заменить стубы реальными пулами из 4 источников. Каждый кандидат получает
**provenance** (§8): `source`, `source_id`, `project_id`, `timestamp` (created_at), `reason`,
`evidence`, `confidence`. Источник «hand» остаётся в `SOURCES` (ручной ввод), но НЕ сканируется
(у него нет реального пула — не генерировать мусор). **Dedup (§18):** детерминированный identity
`(source, source_id)` — новый метод `OpportunityStore.find_by_provenance(source, source_id)`;
повторный discover того же сигнала не создаёт дубль. Отсутствующий/пустой источник →
0 кандидатов от него (не «Stub signal», а честный ноль — §8 «DISCOVER НЕ ДОЛЖЕН ГЕНЕРИРОВАТЬ МУСОР»).

---

## 2. GAP-2 — CLOSE ACCUMULATE (Artifact → Memory → Learning)

**FACT:** `execute()` (строки 350–372) после `ForgeFacade.run_chain` делает
`opp.artifacts = [{"raw": ...***REMOVED******REMOVED***` и `advance(opp, "COMPLETED")` — **и останавливается**.
Артефакты сохраняются только в YAML-сторе (`data_13/opportunities.yaml`), но **НЕ возвращаются
в MemoryStore / LearningLoop**. Docstring модуля обещает
*"ACCUMULATE (memory_store KO kind=opportunity + Learning Loop capture)"* — код этого не делает.

**EVIDENCE:**
- `opportunity_engine.py:371-372` — финальные строки `execute()`: artifacts + COMPLETED, без memory.
- `grep -n 'memory_store\|LearningLoop' scripts_01/opportunity_engine.py` → только docstring и `_LAZY_IMPORT_ERRORS` — ни одного вызова.
- `core_02/memory_store.py::MemoryStore` — реальные механизмы готовы: `store_knowledge(kind, content, title, summary, tags, lifecycle_stage, status, confidence_score, source_event_id)`, `record_learning_event(trigger_id, context_snapshot, outcome, lesson_id)`, `update_feedback(knowledge_id, outcome)`.
- `core_02/learning_loop.py::LearningLoop` — `record_feedback(knowledge_id, outcome)` → confidence (замыкание цикла §7).
- **Констрейнт CAN-16:** `KNOWLEDGE_KINDS = (adr, lesson, pattern, rule, observation, candidate, checklist, guideline, faq, workflow)` — kind `opportunity` ОТСУТСТВУЕТ, а `tests_09/test_memory_store.py::test_all_kinds_known` ассертит `len(KNOWLEDGE_KINDS) == 10` → **нельзя расширять** (сломал бы тест + нарушил бы ADDITIVE). Используем существующий kind **`candidate`** + тег `opportunity`.

**DECISION:** добавить `accumulate(opp, *, memory_store=None, learning_loop=None) -> dict`:
1. `MemoryStore.store_knowledge(kind="candidate", tags=["opportunity", opp.id, project_id, source***REMOVED***, lifecycle_stage="validated"|"raw", confidence_score=0.9|0.3)` — контент = JSON артефактов;
2. `MemoryStore.record_learning_event(trigger_id=f"opportunity:{opp.id***REMOVED***", outcome="success"|"failure", lesson_id=kid)`;
3. `LearningLoop.record_feedback(kid, "success")` — обновление confidence (замыкание обучения);
4. `opp.provenance["memory_knowledge_id"***REMOVED*** = kid` — lineage §10 (OPPORTUNITY→ARTIFACT→MEMORY ENTRY) в существующей модели, без новой БД.

**Failure-семантика (§17):** при недоступности Memory статус НЕ меняется (закрытый словарь статусов,
новые статусы запрещены) — ошибка фиксируется в `provenance["accumulate_error"***REMOVED***` (partial failure
без маскировки в COMPLETED). `execute()` вызывает `accumulate()` на обоих исходах: COMPLETED →
`outcome="success"`, FAILED → `outcome="failure"` (Learning получает и отрицательный результат).

---

## 3. GAP-4 — Opportunity Contract (§E)

**FACT:** контракт **#15 `opportunity.schema`** (24 поля `Opportunity` dataclass) зарегистрирован
в `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` (v5.189.15, закрытие GAP-4).

**EVIDENCE:** `CONTRACT_REGISTRY_V1.md` §C.2 row #15; пакет `intelligence_forensics_25/06_GAP_MAP.md` → GAP-4 CLOSED.

**DECISION:** **ALREADY RESOLVED** (§1 промта: «Если GAP уже устранён — НЕ реализуй повторно,
зафиксируй ALREADY RESOLVED»). Дополнительных действий в этой фазе не требуется.

---

## 4. GAP-5 — Whim Contract (§17.1)

**FACT:** контракт **#16 `whim.schema`** (21 поле `Whim` dataclass) зарегистрирован
в `CONTRACT_REGISTRY_V1.md` (v5.189.15, закрытие GAP-5).

**EVIDENCE:** `CONTRACT_REGISTRY_V1.md` §C.2 row #16; `intelligence_forensics_25/06_GAP_MAP.md` → GAP-5 CLOSED.

**DECISION:** **ALREADY RESOLVED** — повторной реализации нет. Контракт Whim (§12 промта:
лёгкий вход, Whim ≠ Opportunity) уже реализован (`whim_capture.py`, lifecycle NEW→TRIAGED→PROMOTED/DISCARDED).

---

## 5. Фактические call paths (до изменения)

```
CLI discover → discover_candidates() ──► 5 stub-кандидатов (по 1 на source) ──► OpportunityStore.upsert
CLI run → propose() [ScenarioRegistry.propose_roles***REMOVED*** → execute() [ForgeFacade.run_chain***REMOVED***
         ──► artifacts=[raw***REMOVED*** ──► advance(COMPLETED) ──► ✗ MEMORY/Learning НЕ вызываются
Whim promote → OpportunityStore.upsert (прямое создание, минуя DISCOVER)
```

## 6. Существующие тесты (релевантные)

| Файл | Тесты | Статус |
|---|---|---|
| `tests_09/test_opportunity_engine.py` | 23 (lifecycle, store, dry-run, discover-stub, CLI exit codes, vocab safety) | часть discover-тестов требует обновления под real sources |
| `tests_09/test_whim_capture.py` | ~45 (capture/triage/promote/defer/classify) | без изменений (контракт не трогаем) |
| `tests_09/test_memory_store.py` | ~50 (store/graph/learning) | без изменений (kind "candidate" уже валиден) |
| `tests_09/test_project_pulse.py`, `test_event_bus.py` | покрывают источники | без изменений |

## 7. Что конкретно будет изменено

1. `scripts_01/opportunity_engine.py` — `discover_candidates()`: real sources + provenance + dedup;
   `execute()`: вызов `accumulate()`; NEW `accumulate()`; NEW `OpportunityStore.find_by_provenance()`;
   CLI discover: флаги путей источников (`--whim-path/--pulse-db/--event-db/--memory-db`) для
   тестируемости и production-конфигурации.
2. `tests_09/test_opportunity_engine.py` — обновить `test_cli_discover_creates_records` (реальные данные
   вместо стубов) + при необходимости `test_discover_candidates_always_returns_list`.
3. NEW `tests_09/test_intelligence_loop_phase5.py` — TEST 1–10 (§19) + E2E vertical slice (§20).
4. Docs/анкоры/реестр — см. 02_IMPLEMENTATION_LOG.md.

**Правок вне scope НЕТ** (§3 промта): EventBus/Memory/Knowledge/Scenario/Forge/Registry не
модифицируются; новых state-машин нет; массового рефакторинга нет.
