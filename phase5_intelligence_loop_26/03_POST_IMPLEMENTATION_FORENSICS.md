# PHASE5 POST-IMPLEMENTATION FORENSICS — v5.189.16

> §25 FINAL FORENSICS: повторное исследование изменённых участков после реализации.
> Метод: чтение итогового кода + свежие тестовые прогоны + ревью code-reviewer-glm (5 раундов, финал CHISTO).

---

## GAP-1 — REAL DISCOVER → **RESOLVED**

| | BEFORE | AFTER |
|---|---|---|
| **Источники** | `"Stub signal from whim_capture"` ×5 (stub-кандидаты) | 4 реальных источника: WhimStore (whims.yaml), ProjectPulse (project_pulse.db), EventBus (event_log), MemoryStore (context.db) |
| **Provenance** | нет | `source / source_id / project_id / timestamp / reason / evidence / confidence / stub=False` |
| **Пути** | `source_paths` рассинхронизирован (memory vs knowledge) | единый контракт ключей `whims/pulse/events/memory` = CLI-флаги |
| **Dedup** | нет | `OpportunityStore.find_by_provenance` до среза `max_results` |
| **FALLBACK** | stub был production path | stub только явный fallback (`stub=True`), путь по умолчанию — реальные источники |

**Проверка кодом:** `_SOURCE_DEFAULTS` содержит 4 реальных функции; ни одного `"Stub signal from"` в production-path (только явный fallback-бренч).

## GAP-2 — CLOSE ACCUMULATE → **RESOLVED**

| | BEFORE | AFTER |
|---|---|---|
| **execution → memory** | `execute()` заканчивался на `advance(opp, "COMPLETED")` — артефакт терялся | `_accumulate_best_effort()` на обоих исходах: Artifact JSON → `MemoryStore.store_knowledge(kind="candidate", tags=["opportunity", ...***REMOVED***)` |
| **lineage** | нет | `provenance["memory_knowledge_id"***REMOVED***` связывает Opportunity → Artifact → Memory entry |
| **learning** | нет | `record_learning_event(kind="opportunity", outcome=success/failure)` + `LearningLoop.record_feedback(knowledge_id, outcome)` |
| **failure path** | — | Memory/Learning ошибки → `provenance["accumulate_error"***REMOVED***`, статус opportunity не меняется (§17) |

**Проверка кодом:** `accumulate()` + вызовы в обоих бранчах `execute()` (COMPLETED/FAILED); E2E-тест проверяет KO и learning event в реальном MemoryStore.

## GAP-4 — Opportunity Contract (16 полей §E) → **ALREADY RESOLVED**

Зафиксировано в Этапе 0 (см. `01_PRE_IMPLEMENTATION_AUDIT.md`): контракт #15 зарегистрирован в `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` (v5.189.15). Повторная реализация НЕ выполнялась (промт §1: GAP устранён → ALREADY RESOLVED).

## GAP-5 — Whim Contract (§17.1) → **ALREADY RESOLVED**

Контракт #16 зарегистрирован в CONTRACT_REGISTRY_V1 (v5.189.15). WhimStore реально существует (`data_13/whims.yaml`), теперь используется как реальный DISCOVER-источник — интеграция подтверждена кодом, а не только контрактом.

---

## Попутно обнаруженные и исправленные дефекты (в scope GAP-1/2)

| Дефект | Где | Статус |
|---|---|---|
| `advance(ACTIVE→COMPLETED)` InvalidTransition — execute() падал на свежих кандидатах | `execute()` | FIXED (READY-промежуточный шаг) |
| Retry FAILED→COMPLETED падал; повторный сбой FAILED→FAILED InvalidTransition | `execute()` | FIXED (нормализация ДО run_chain) |
| `source_paths` ключ "memory" не находил источник "knowledge" | `discover_candidates` | FIXED (единый контракт ключей) |
| Тесты читали production-БД | `test_opportunity_engine.py`, `test_intelligence_loop_phase5.py` | FIXED (герметичные tmp-пути) |
| Docstring обещал kind=opportunity, код писал kind=candidate | module docstring | FIXED (документация = код, §21) |

## Вне scope (зафиксировано в 09_FUTURE_GAPS.md)

- Advanced Opportunity Ranking; Scenario Intelligence; Content Intelligence; Concept Evolution; C-A/C-B/C-C; Evolution Memory; Workspace UI; автономный Project Intelligence; полноценный FactoryRegistry.
