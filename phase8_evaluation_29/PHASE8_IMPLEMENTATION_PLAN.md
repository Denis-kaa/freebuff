# PHASE8_IMPLEMENTATION_PLAN.md — Universal Scenario Intelligence (Phase 8)

> Phase 8 (promt 91). Дата: 2026-08-17. Версия: v5.189.25.
> Статус: ✅ ВЫПОЛНЕН (минимальный vertical slice по GAP_MAP §3).

---

## 1. Цель

Реализовать универсальный (domain-neutral) Scenario Intelligence — слой
принятия решений «какой способ реализации Opportunity подходит в текущем
контексте», поверх существующих ScenarioRegistry / FactoryRegistry / ForgeFacade /
MemoryStore / EventBus. Без перепроектирования Phase 7.

## 2. Объём (scope)

- **Ядро:** `scripts_01/scenario_intelligence.py` (новый модуль).
  - Entities: `ScenarioCandidate`, `CapabilityRequirement`, `ScenarioDecision`.
  - `ScenarioIntelligence`: discover → evaluate → rank → select →
    resolve_capability → feedback_v0.
  - `DecisionHistoryStore` (YAML, атомарный) — per-opportunity latest() для
    re-selection (оправдано §20, см. CONTRACT §10).
  - CLI: discover / select / evaluate / resolve / feedback / history.
- **Адаптер:** `scripts_01/opportunity_engine.py::propose()` — делегирует в
  ScenarioIntelligence с BC-fallback на legacy ScenarioRegistry.
- **Тесты:** `tests_09/test_scenario_intelligence.py` (§18, 18 тестов) +
  регрессия `test_intelligence_loop_phase5.py` (score 0.9 → composite 0.74).

## 3. НЕ входит (anti-overengineering §20 / §17)

- Content Factory / Code Factory / Media Factory (следующая фаза, §23);
- Concept Evolution, C-A/C-B/C-C, Workspace UI, новая orchestration system;
- второй Scenario Registry / Factory engine / Forge / Memory / EventBus / БД / LLM framework.

## 4. Этапы

| # | Этап | Артефакт | Статус |
|---|------|----------|--------|
| 1 | Forensics (repository-first §0/§13) | PHASE8_REALITY_MAP.md + PHASE8_GAP_MAP.md | ✅ |
| 2 | Контракт (domain-neutral §16) | SCENARIO_INTELLIGENCE_CONTRACT_V1.md | ✅ |
| 3 | Ядро (discover/evaluate/rank/select/resolve/feedback) | scripts_01/scenario_intelligence.py | ✅ |
| 4 | Интеграция (propose BC-fallback) | scripts_01/opportunity_engine.py | ✅ |
| 5 | Тесты (§18) | tests_09/test_scenario_intelligence.py | ✅ |
| 6 | Регрессия Phase 5/7 | test_intelligence_loop_phase5.py, test_phase7_factory_event.py | ✅ |
| 7 | Register-first closure | missing_registry mark-implemented + §20 карта | ✅ |
| 8 | CHANGELOG + version-anchor sync | CHANGELOG.md v5.189.25 + BUFFY/BUFFY_PROJECT/TASK/PLATFORM | ✅ |
| 9 | Traceability (§19) | PHASE8_TRACEABILITY.md | ✅ |
| 10 | Evaluation archive (§22) | PHASE8_EVALUATION_5.189.25.tar.gz + .sha256 | ✅ |

## 5. Ключевые решения

1. **kind=candidate + tag=scenario_decision** (не новый kind) — `scenario_decision`
   не входит в `KNOWLEDGE_KINDS` MemoryStore; §12 reuse существующего kind.
2. **lifecycle_stage=validated|raw** (не "applied") — "applied" нет в
   `LIFECYCLE_STAGES` → MemoryStoreError.
3. **DecisionHistoryStore YAML** — MemoryStore не имеет per-opportunity latest();
   минимальный YAML-слой по образцу opportunities.yaml (оправдание §20).
4. **propose() persist=False** — read-only адаптер (герметичный); полный
   lifecycle (superseded/reselected) через select/resolve CLI-путь (CONTRACT §15.1).
5. **history limit=500** — в загруженной БД opportunity-accumulate KO не
   вытесняют scenario-записи за срез (reviewer nit).

## 6. Валидация

- `pytest tests_09/test_scenario_intelligence.py` → 18 passed;
- `pytest tests_09/test_intelligence_loop_phase5.py test_phase7_factory_event.py
  test_opportunity_engine.py` → 70 passed (регрессия);
- `mypy scripts_01/scenario_intelligence.py scripts_01/opportunity_engine.py` → 0 errors;
- `consistency_check` → CONSISTENT (после sync).

---
_Plan complete. Phase 8 vertical slice реализован за 1 цикл register-first._
