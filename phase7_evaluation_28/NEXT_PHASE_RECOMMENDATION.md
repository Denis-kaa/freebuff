# NEXT_PHASE_RECOMMENDATION.md — Phase 8 (Scenario Intelligence)

> Phase 7 §28. Phase 7 НЕ запускает Phase 8 автоматически — только готовит рекомендацию.

## Что Phase 7 теперь даёт следующей фазе

1. **Замкнутый execution path** с доказанными стрелками:
   `Opportunity → Scenario → Factory → ForgeFacade → Artifact → Memory/EventBus`
   (каждая стрелка имеет file/symbol/caller/entrypoint/test — см. 06/07).
2. **Каноническая Opportunity schema** (24 поля) — единый контракт для всех фаз.
3. **Factory selection** подключён к execute() (`FactoryRegistry.select_forge`) —
   Scenario Intelligence может опираться на capability-резолвинг.
4. **EventBus-наблюдаемость** — 12 реально публикуемых событий; подписчики Phase 8
   могут слушать `opportunity.*` / `execution.*` / `scenario.selected` / `whim.*`.
5. **Пакет evaluation** (`phase7_evaluation_28/`) — независимая проверка Phase 7.

## Реальные готовые интерфейсы

| Интерфейс | Готовность |
|-----------|------------|
| `opportunity_engine.discover/propose/execute/accumulate` | ✅ |
| `FactoryRegistry.select_forge(capability)` | ✅ (подключён) |
| `EventBus.publish/get_events` (canonical) | ✅ |
| `ScenarioRegistry.propose_roles` (существующий) | ✅ (как есть) |
| `ForgeFacade.run_chain(Project, role_ids)` | ✅ (execution boundary) |
| `MemoryStore.store_knowledge` / `LearningLoop` | ✅ (accumulate) |

## Ограничения

- `scenario.selection` PARTIAL: `find_role` возвращает None вместо raise (P1.4).
- Factory-путь использует capability-токены из закрытого словаря (ANTI-6b) —
  Scenario Intelligence должен генерировать токены из `KNOWN_CAPABILITIES`.
- Автономный feedback engine НЕ реализован (только техническая возможность §10).
- LLM-синтез hypothesis/rationale — детерминированные эвристики v1.

## Минимальный следующий vertical slice (Phase 8 — Scenario Intelligence)

1. **Интеллектуальный SELECT:** поверх `ScenarioRegistry.propose_roles` добавить
   score/ранжирование кандидатов сценария (по типу `rank_candidates` из promt 086),
   писать выбранный scenario в `Opportunity.scenario` (уже есть поле).
2. **Scenario → Factory routing:** использовать выбранный scenario.capability для
   `FactoryRegistry.select_forge` (уже есть `_derive_capability` fallback на scenario).
3. **Feedback loop v0:** подписка на `execution.completed/failed` → переоценка
   opportunity (COMPLETED/FAILED уже эмитятся) → следующий кандидат.
4. **Тесты:** scenario ranking + routing + feedback loop (по образцу test_phase7_factory_event.py).

## Порядок

1. Phase 8 = **SCENARIO INTELLIGENCE** (SELECT + routing + feedback v0).
2. Phase 9 = **CONTENT FACTORY** (полный Factory-путь поверх Scenario Intelligence).
3. Concept Evolution / C-A / C-B / C-C — НЕ входят (отдельный трек).

---
_Phase 7 COMPLETE. Следующий шаг: Phase 8 — Scenario Intelligence._
