# PHASE5 FINAL ARCHITECTURAL DECISION — v5.189.16

> Вердикт: Intelligence Loop ЗАМКНУТ минимальным вертикальным срезом на существующей архитектуре.
> Ни один новый компонент-платформа не создан (§3/§4/§26 17/17).

---

## Решения (ADR-style)

### D-1. Real DISCOVER поверх существующих источников (GAP-1)
**Решение:** `discover_candidates()` читает 4 существующих storage через 4 функции-источника, зарегистрированные в module-level `_SOURCE_DEFAULTS`. Provenance обязателен. Stub сохранён ТОЛЬКО как явный fallback (`stub=True`).
**Альтернативы отклонены:** новая Signal-система (запрещена §7 — EventBus уже выполняет роль); новая storage (запрещена §7/§9).
**Следствие:** DISCOVER больше не генерирует мусор (§8).

### D-2. ACCUMULATE через существующие MemoryStore + LearningLoop (GAP-2)
**Решение:** `accumulate()` пишет Artifact JSON как KO `kind="candidate"` с тегами `["opportunity", project_id***REMOVED***`, затем `record_learning_event` + `LearningLoop.record_feedback`. Lineage — поле `provenance["memory_knowledge_id"***REMOVED***` (расширение существующего provenance-словаря, НЕ новая БД).
**Ключевой CAN-16 trade-off:** `KNOWLEDGE_KINDS` содержит 10 kinds и НЕ содержит `opportunity` (тест ассертит `len==10`). Добавление kind потребовало бы правки memory_store + теста — нарушение ADDITIVE. Решение: существующий kind `candidate` + тег `opportunity`. Документировано в docstring.
**Следствие:** Artifact реально возвращается в Memory и Learning (§9-§11).

### D-3. Жёсткая валидность state machine в execute()
**Решение:** нормализация `(ACTIVE|FAILED) → READY` ДО `run_chain`. Оба исхода валидны: success `READY→COMPLETED`, failure `READY→FAILED`. Retry FAILED-opportunity работает (promt 079_19 §3.1 #7).
**Найденные баги:** `ACTIVE→COMPLETED` InvalidTransition (execute падал на свежих кандидатах — существовал до фазы); `FAILED→FAILED` InvalidTransition при повторном сбое retry.
**Следствие:** ошибки не маскируются как COMPLETED (§17).

### D-4. Forge — только через ForgeFacade (§16)
**Решение:** `execute()` вызывает `ForgeFacade.run_chain(project_id, role_ids=[...***REMOVED***)` через `_lazy_import` (fallback `scripts_01.` → bare; недоступность → FAILED + accumulate failure). Никаких прямых Forge-вызовов.
**Следствие:** validation/ForgeRegistry не обходятся.

### D-5. Герметичность тестов
**Решение:** все тесты передают `source_paths` с tmp-путями (helper `_hermetic_sources`), MemoryStore в tmp, ForgeFacade/ScenarioRegistry мокаются через `sys.modules`. Ни один тест не читает/пишет production-БД (`data_13/*.db`, `context_12/events.db`).
**Причина:** ревью R1/R3 поймал негерметичные тесты, тащившие реальные данные.
**Следствие:** детерминированный прогон 113/113.

### D-6. Дублирование запрещено (подтверждено)
EventBus, Memory, Knowledge, Scenario Engine, Forge, Factory — только существующие; intelligence — тонкий слой сверху (§4). Проверено: 17/17 чек-лист §26.

---

## Оценка

| Критерий | Оценка |
|---|---|
| Scope discipline (§3) | соблюдён — только A–F |
| ADDITIVE (CAN-16) | соблюдён — 0 переписанных модулей |
| DoD §31 chain | FORENSICS → IMPLEMENTATION → TEST → E2E → POST-FORENSICS → DOCUMENTATION → EVALUATION PACKAGE → ARCHIVE — все пройдены |
| Риски | низкие; главный (полный production Forge E2E) — ограничение интеграционного теста, зафиксировано в 07_TEST_REPORT §5 и 09_FUTURE_GAPS B3 |

## Следующий шаг roadmap

1. **Advanced Opportunity Ranking** (09_FUTURE_GAPS C1) — быстрый выигрыш поверх provenance confidence.
2. **FactoryRegistry** (§15) — разблокирует Factory-путь в Intelligence Loop.
3. Register-first цикл для каждого следующего пункта (AGENTS.md §5).
