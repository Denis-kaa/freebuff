# SCENARIO_INTELLIGENCE_CONTRACT_V1.md — Universal Scenario Intelligence (Phase 8)

> Phase 8 (promt 91) §16. Domain-neutral contract. Дата: 2026-08-17.
> Версия платформы: v5.189.25. Реализация: `scripts_01/scenario_intelligence.py`
> (ядро) + `scripts_01/opportunity_engine.py::propose()` (adapter, BC-fallback).
> Тесты: `tests_09/test_scenario_intelligence.py` (§18, 18 тестов) + регрессия.

---

## 0. Принцип

Scenario Intelligence отвечает ТОЛЬКО на вопрос:

> «Какой способ реализации текущей Opportunity наиболее подходит в текущем
> контексте проекта?»

Он **не производит результат**. Производят Factory + Forge. Ни один контракт
Phase 8 не содержит жёсткой зависимости от "content" / текстов / кода / медиа
(§1/§4). Домены (CONTENT / CODE / MEDIA / RESEARCH / DOCUMENT / AUTOMATION /
DESIGN / STORY / будущие) — это **подключаемые Factory** поверх универсального
ядра.

## 1. Input

- `Opportunity` (существующая сущность `scripts_01/opportunity_engine.py`):
  `id`, `project_id`, `title`, `description`, `source`, `status`, `provenance`.
- Никаких доменно-специфичных полей. Если домен нужен — он уже есть в
  provenance/Factory-слое, Scenario Intelligence его не читает напрямую.

## 2. Context

- Используется существующий контекст проекта (project_id) и Opportunity
  (title+description как query для discovery).
- Никакого нового контекстного слоя.

## 3. Candidate Discovery (§5)

- Источник каталога — **существующий** `ScenarioRegistry` (`core_02/scenario_registry.py`).
  **Не создаётся второй registry.**
- `discover(opp, top_n=5)`:
  1. `ScenarioRegistry.propose_roles(query, top_n)` → fuzzy-матч (scenario, role, score);
  2. fallback: `ScenarioRegistry.list_scenarios()` (каталог) если нет role-match.
- Одна Opportunity → несколько кандидатов (`ScenarioCandidate`), любой домен.
- Каждый кандидат несёт domain-neutral capability-токен
  (`scenario.capabilities[0***REMOVED***` → `role.routing_hint[0***REMOVED***` → None).

## 4. Evaluation (§6)

Композитный score ∈ [0,1***REMOVED*** = Σ weightᵢ · componentᵢ. Веса документированы
(`EVAL_WEIGHTS`, сумма = 1.0):

| Компонент | Вес | Источник |
|-----------|-----|----------|
| relevance | 0.35 | `ScenarioRegistry.propose_roles` (fuzzy) |
| capability | 0.25 | `FactoryRegistry.capability_catalog()` (доступность) |
| history | 0.20 | `MemoryStore.query_by_type('candidate')` title-prefix `scenario:{id***REMOVED***` |
| feasibility | 0.20 | enabled + roles + capability resolvable |

Каждая компонента объяснима (reasons + evidence). Переиспользуются:
SemanticLayer (опционально), LearningLoop (feedback), MemoryStore (history),
GraphIndex (опционально). Никаких новых показателей без необходимости.

## 5. Ranking (§7)

- `rank(candidates)` — сортировка по composite score (desc), tie-break стабилен.
- Результат объясним: `score` + `reasons` + `evidence` (никогда black-box).

## 6. Selection (§7, §10)

- `select(opp, top_n=5, persist=True, available_only=True)`:
  discover → evaluate → rank → best.
- `available_only=True` фильтрует infeasible (capability не предлагается ни одной
  фабрикой → `available=False`).
- Lifecycle решения (существующая семантика, §10):
  - `selected` — первый выбор;
  - `superseded` — предыдущий выбор был ДРУГОГО сценария;
  - `reselected` — повторный выбор после `deferred`/`superseded`;
  - `unavailable` — кандидатов нет / все infeasible;
  - `deferred` — не выбранный сценарий НЕ удаляется (остаётся в каталоге).
- Не выбранный Scenario не удаляется автоматически.

## 7. Capability Resolution (§8)

- `CapabilityRequirement(capability, scenario_id, role_id)` — domain-neutral токен.
- `resolve_capability(req)` → `FactoryRegistry.select_forge(capability)` →
  `(FactoryPassport.factory_id, ForgePassport.forge_id)`.
- Capability — непрозрачный токен (article_generation / api_implementation /
  image_generation / market_research / screenplay_development / …). Phase 8
  **не зашивает** ни один из них в код.
- Закрытый словарь (ANTI-6b): токен ДОЛЖЕН быть в `KNOWN_CAPABILITIES`,
  иначе `select_forge` вернёт None (silent-fallback на слабую модель — запрещено).

## 8. Provenance (§7)

`ScenarioDecision` содержит полный provenance:
`opportunity_id`, `project_id`, `selected_scenario_id`, `score`, `reasons`,
`evidence` (relevance/capability/history/feasibility + all_candidates),
`capability`, `factory_id`, `forge_id`, `status`, `created_at`.
Интеграция в `propose()` сохраняет `provenance['scenario_decision'***REMOVED***`
(traceability §7).

## 9. Feedback (§9)

- `feedback_v0(decision, outcome)` — outcome ∈ {success, failure, neutral***REMOVED***.
- **Transparent, без ML/RL.** Сохраняет:
  - `MemoryStore.store_knowledge(kind='candidate', title='scenario:{id***REMOVED***',
    tags=['scenario_decision', ...***REMOVED***, lifecycle_stage='validated'|'raw')`;
  - `MemoryStore.record_learning_event(...)`;
  - `LearningLoop.record_feedback(kid, outcome)` (если доступен).
- Будущий ranking читает историю через `query_by_type('candidate')` +
  title-prefix (см. §4).

## 10. Persistence (§12)

- **НЕ создаётся новая БД.** Используются существующие механизмы:
  - MemoryStore (knowledge + learning events);
  - EventBus storage (события);
  - ForgeRegistry (паспорта кузен);
  - Opportunity persistence (`opportunities.yaml`).
- Decision history: лёгкий `DecisionHistoryStore` (YAML `data_13/scenario_decisions.yaml`,
  атомарный .tmp+replace) — по образцу существующих YAML-стора
  (opportunities.yaml / whims.yaml). Не новая БД-система.
- **§20 justification (anti-overengineering):** MemoryStore (`kind=candidate`)
  хранит знания, но у него НЕТ per-opportunity `latest()` query API (только
  `query_by_type(kind)` — без фильтра по opportunity_id и без «последней записи»).
  `DecisionHistoryStore` — минимальный YAML-слой (по образцу opportunities.yaml),
  дающий ровно `by_opportunity()`/`latest()` для семантики re-selection (§10/§18 #15).
  Никакой новой БД-системы — только лёгкий стор на существующем паттерне.

## 11. Events (§11)

Только реально необходимые события (проверено по Phase 7 event model):

| Событие | Producer | Payload |
|---------|----------|---------|
| `scenario.candidates.generated` | ScenarioIntelligence | opportunity_id, project_id, candidate_count, scenario_ids |
| `scenario.evaluated` | ScenarioIntelligence | opportunity_id, project_id, evaluated[{scenario_id, score***REMOVED******REMOVED*** |
| `scenario.selected` | ScenarioIntelligence | opportunity_id, project_id, scenario_id, role_id, score, capability, factory_id, forge_id, status |
| `scenario.reselected` | ScenarioIntelligence | (то же, status='reselected') |
| `scenario.feedback` | ScenarioIntelligence | opportunity_id, project_id, scenario_id, outcome, knowledge_id |

Каждое событие: producer + хранение (EventBus) + payload + тест (test_10_eventbus).

## 12. Factory Boundary

- Scenario Intelligence резолвит capability → factory/forge через
  `FactoryRegistry`. Он НЕ вызывает Factory напрямую для производства.
- Factory — подключаемый производственный домен поверх ядра.

## 13. Forge Boundary

- `ForgeFacade.run_chain` остаётся **единственным** execution boundary (§17).
- Scenario Intelligence НЕ вызывает ForgeFacade (проверено test_8_forge_boundary).

## 14. Fallback

- Если `ScenarioIntelligence` недоступен (ImportError) или вернул
  `selected_scenario_id=None` (unavailable) → `propose()` падает на **legacy**
  путь напрямую через `ScenarioRegistry.propose_roles` (прежнее поведение
  Phase 7). Никогда не бросает наружу (fail-safe).

## 15. Backward Compatibility

- `propose(opp)` сигнатура и семантика не изменены (возвращает opp с
  заполненным `scenario`).
- Регрессия Phase 5/7: `test_intelligence_loop_phase5.py` (12 тестов),
  `test_phase7_factory_event.py` (26 тестов) — зелёные.
- Существующие слои (ScenarioRegistry / FactoryRegistry / ForgeFacade /
  MemoryStore / EventBus) **не перепроектируются** (Additive Architecture).

### 15.1 Re-selection через integration-путь (важно)

`opportunity_engine.propose()` вызывает `ScenarioIntelligence.select(..., persist=False)`
— **read-only адаптер** (герметичный, без side-effect на `data_13/scenario_decisions.yaml`).
Следствие: семантика `superseded`/`reselected` (§10/§18 #15) НЕ триггерится через
`propose()`. Полный lifecycle с персистом доступен через:
- прямой вызов `ScenarioIntelligence.select(opp, persist=True)`;
- CLI `scenario_intelligence select <id>` / `resolve <id>` (persist).
Это осознанный дизайн-трейдофф: `propose()` не пишет на диск; решение со
lifecycle — через select/resolve-путь.

## 16. Anti-overengineering (§20)

НЕ создано: второй Scenario Registry, новый Factory engine, новый Forge,
новая Memory, новый EventBus, новая БД, новый LLM framework, доменно-специфичные
контракты. `DecisionHistoryStore` — лёгкий YAML-стор по существующему образцу
(обосновано в §10).

---
_Contract V1. Domain-neutral. Phase 8 complete per §21 DoD._
