# NEXT_PHASE_RECOMMENDATION.md — Phase 9 Recommendation (§23)

> Phase 8 (promt 91) §23. Дата: 2026-08-17. Версия: v5.189.25.

---

## 1. Принцип

Phase 8 построила **универсальное ядро** Scenario Intelligence. Оно domain-neutral
и не привязано ни к контенту, ни к коду, ни к медиа. Следующая фаза должна
добавить **первый доменный vertical slice** через универсальный контракт Factory —
БЕЗ изменения универсальных контрактов Phase 8.

## 2. Рекомендация: первый доменный Factory

Выбор конкретного домена НЕ меняет универсальные контракты Phase 8. Рекомендованные
кандидаты (по готовности инфраструктуры):

| Домен | Factory | Capability-токены (уже в KNOWN_CAPABILITIES) | Готовность |
|-------|---------|---------------------------------------------|-----------|
| **CONTENT** | Content Factory | article_generation, report_generation, book_generation | 🟡 высокая (есть blueprint_v3, whims, books_out_23) |
| **CODE** | Code Factory | api_implementation, code_generation, refactoring | 🟡 средняя (есть projects_17, forge) |
| **RESEARCH** | Research Factory | market_research, research_synthesis | 🟡 средняя (есть research_web) |

**Рекомендация: Content Factory** — первый vertical slice, потому что:
1. `blueprint_v3` сценарий уже активен (единственный инстанцируемый);
2. `books_out_23/` и `whims` дают реальные Opportunity-источники;
3. `articles_factory`/`article_forge` capability-путь уже резолвится в тестах Phase 8.

## 3. Что должна сделать Phase 9

1. Добавить первый доменный Factory + ForgePassport (зарегистрировать в
   `runtime_05/factories/<factory_id>/` + `KNOWN_CAPABILITIES`).
2. Доказать полный путь: Opportunity → ScenarioIntelligence (Phase 8) →
   capability → Factory → Forge → Artifact → Feedback (Phase 8 feedback_v0).
3. НЕ менять универсальные контракты Phase 8 (ScenarioCandidate /
   ScenarioDecision / CapabilityRequirement / EVAL_WEIGHTS / события).
4. Register-first: зафиксировать Factory в `missing_registry` + §20 карта.

## 4. Что НЕ входит в Phase 9

- Новый универсальный decision layer (Phase 8 уже есть);
- второй Scenario Intelligence / второй registry;
- перепроектирование ForgeFacade / MemoryStore / EventBus.

## 5. Ожидаемый результат

- Первый доменный vertical slice поверх универсального ядра;
- Доказательство, что конкретный Factory — это подключаемый производственный
  домен, а не часть ядра;
- Готовность платформы к добавлению следующих доменов (CODE/MEDIA/RESEARCH/…)
  БЕЗ изменения Phase 8.

---
_Recommendation: Phase 9 = Content Factory (первый доменный vertical slice)._
