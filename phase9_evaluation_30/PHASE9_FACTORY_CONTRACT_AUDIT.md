# PHASE9_FACTORY_CONTRACT_AUDIT.md — Factory Contract Audit (Phase 9, promt 92 §6)

> **Статус:** FORENSICS OUTPUT — до реализации. **Метод:** 12 evidence-based вопросов по цепочке
> Opportunity → ScenarioIntelligence → Scenario → Capability → Factory → Forge.
> **Правило:** CODE > TESTS > CONFIG > DOCUMENTATION > ASSUMPTION. Каждое утверждение — path+symbol.
> **Дата:** 2026-08-17 · **Пакет:** `phase9_evaluation_30/`

---

## Вопрос 1. Где именно возникает capability?

**Ответ (evidence):** capability возникает на **пересечении сценария и роли** — как непрозрачный токен, извлекаемый `ScenarioIntelligence._candidate_capability()`:

```
scripts_01/scenario_intelligence.py:347-355  _candidate_capability(scenario, role)
    caps = getattr(scenario, "capabilities", None) or ()
    if caps: return str(caps[0***REMOVED***)                    # scenario.capabilities[0***REMOVED***
    hint = getattr(role, "routing_hint", None) or ()
    if hint: return str(hint[0***REMOVED***)                    # role.routing_hint[0***REMOVED***
    return None
```

- Источник №1: `scenario.capabilities[0***REMOVED***` (поле Scenario-манифеста; напр. blueprint_v3.yaml: `role-based-pipeline`, `code-capable`, …).
- Источник №2: `role.routing_hint[0***REMOVED***` (fallback).
- Альтернативный путь (Opportunity Engine): `opportunity_engine._derive_capability()` — токен из `provenance.capability` → `scenario.capability` → None.

**Статус контракта:** ✅ контракт существует и реализован (Phase 8). Capability — закрытый словарь-токен (ANTI-6b).

---

## Вопрос 2. Кто её выбирает?

**Ответ (evidence):** **ScenarioIntelligence** — единственный «выбиратель» (decision layer), domain-neutral:

```
scripts_01/scenario_intelligence.py:494  select(opp, top_n, event_bus, persist, available_only)
    → discover()  — кандидаты из ScenarioRegistry (каталог, НЕ второй registry)
    → evaluate()  — composite score (relevance·0.35 + capability·0.25 + history·0.20 + feasibility·0.20)
    → rank()      — сортировка по score
    → best = ranked[0***REMOVED***
```

- `opportunity_engine.propose()` (`scripts_01/opportunity_engine.py:767`) **делегирует** в ScenarioIntelligence.select(persist=False) с **BC-fallback** на legacy-путь (ScenarioRegistry.propose_roles).
- **Factory НЕ выбирает сценарий** (промт 92 §11: Factory получает уже выбранный capability/execution intent) — подтверждено: FactoryRegistry не имеет select-scenario API.

**Статус контракта:** ✅ реализован. Selection ≠ Factory responsibility.

---

## Вопрос 3. Кто её разрешает (capability → исполнимый ресурс)?

**Ответ (evidence):** `ScenarioIntelligence.resolve_capability()` → **FactoryRegistry.select_forge()**:

```
scripts_01/scenario_intelligence.py:594  resolve_capability(requirement: CapabilityRequirement)
    → factory_registry.select_forge(requirement.capability)      # core_02/factory_registry.py:271
    → (FactoryPassport, ForgePassport) | None
    → возвращает (factory_id, forge_id) | (None, None)  # fail-safe

core_02/factory_registry.py:271  select_forge(capability, prefer_status=None)
    — status-priority: production(3) > material(2) > design(1) на factory затем forge
    — prefer_status: минимальный status-фильтр
    — детерминированный tie-break
```

- Результат фиксируется в `ScenarioDecision.factory_id / forge_id` (provenance, `scripts_01/scenario_intelligence.py:121-137`).
- **Ограничение:** `select_forge` ищет только по capabilities существующих паспортов (`runtime_05/factories/architecture/*`). Контент-токены (`article_generation` и т.п.) в проде вернут `None` — см. Reality Map G1/G2.

**Статус контракта:** ✅ механизм реализован; ⚠️ контент-словарь не зарегистрирован (G1).

---

## Вопрос 4. Кто находит Factory?

**Ответ (evidence):** **FactoryRegistry** — единственный реестр:

```
core_02/factory_registry.py:257  find_factories_by_capability(capability) -> list[FactoryPassport***REMOVED***
    — union factory.yaml capabilities + forge passports (factory_capabilities(), :244)
    — sorted, детерминированный порядок
core_02/factory_registry.py:240  get_factory(factory_id) -> Optional[FactoryPassport***REMOVED***
```

- Источник данных: `runtime_05/factories/*/factory.yaml` + forge-паспорты `runtime_05/factories/*/<forge>.yaml` (авто-дискавери в `__init__`, eager, `reload()` для hot-reload).
- Сейчас в проде существует ровно **1 фабрика** (architecture) и 2 кузни (governance, review).

**Статус контракта:** ✅ реализован (v5.189.21, Missing #20). Content Factory отсутствует в реестре (G2).

---

## Вопрос 5. Как Factory получает вход?

**Ответ (evidence):** **ЧАСТИЧНО — gap.**

- Паспорта декларируют входы: `governance.yaml inputs: [policy_set, current_architecture, review_verdict, governance_history***REMOVED***`; `review.yaml` — контекст анализа.
- Однако **FactoryAdapter/нормализации входа НЕТ в коде**: `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §G (canonical): *«CURRENT IMPLEMENTATION: отсутствует (G2)»*.
- Реальный вход текущего пути — `ForgeFacade.run_chain(project, role_ids)` — принимает `Project` + роли, а НЕ domain-нормализованный вход фабрики.

**Статус контракта:** ❌ GAP (G3 Reality Map). Phase 9 должна добавить минимальную input normalization в Factory-слой (без дублирования ForgePipeline).

---

## Вопрос 6. Как Factory формирует execution request?

**Ответ (evidence):** **ОТСУТСТВУЕТ — главный gap вертикали.**

- В `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §G FactoryCapability декларирует `execution: forge_facade.run_chain | tool | engine` — но это **дизайн-схема**, не runtime-код.
- Реальный execution request сегодня: `opportunity_engine.execute()` → `ForgeFacade.run_chain(project, role_ids, project_read_only=True)` (`core_02/forge_facade.py:475`) — напрямую, БЕЗ factory-слоя.
- Factory-слой (input normalization → domain preparation → execution request → output normalization) — **не реализован ни для одного домена**.

**Статус контракта:** ❌ GAP (G3/G5). Phase 9: Content Factory формирует execution request из domain-входа, передаёт в ForgeFacade.

---

## Вопрос 7. Кто вызывает Forge?

**Ответ (evidence):** **ТОЛЬКО ForgeFacade** — единственный санкционированный мост (§7.3 B-rule, ADR-009):

```
core_02/forge_facade.py:293  class ForgeFacade — «Единственная санкционированная точка входа: роль → Forge-прогон»
    :475 run_chain(project, role_ids=None, *, registry_path=None, compose_artifact_check=True,
                   project_read_only=True, skip_full_cycle_stages=None) -> ChainRun
    :~   initiate_forge(project, requested_by_role, hooks, skip, project_read_only) -> ForgeFacadeResult
```

- `ScenarioIntelligence` НЕ вызывает ForgeFacade (test_8_forge_boundary, `tests_09/test_scenario_intelligence.py`) — execution boundary соблюдён.
- `opportunity_engine.execute()` — вызывает run_chain (реальный путь).
- Запрет прямых вызовов ForgePipeline вне Facade — подтверждён grep-ом (forge_pipeline вызывается только из forge_facade/forge CLI).

**Статус контракта:** ✅ CONFIRMED, НЕ менять.

---

## Вопрос 8. Кто валидирует результат?

**Ответ (evidence):** **RoleArtifactValidator** — внутри `ForgeFacade.run_chain`:

```
core_02/forge_facade.py:194  ForgeFacadeResult / RoleArtifactValidator
    run_chain(..., compose_artifact_check=True) — валидация артефактов встроена (default ON)
```

- `opportunity_engine.execute()` после run_chain фиксирует результат → `opportunity.artifacts` (список dict) или FAILED + failure_reason.
- `ScenarioIntelligence.feedback_v0()` — валидация исхода на уровне решения (success/failure/neutral) → MemoryStore kind=candidate + LearningLoop.

**Статус контракта:** ✅ CONFIRMED (существующая валидация переиспользуется; новая НЕ создаётся).

---

## Вопрос 9. Где сохраняется Artifact?

**Ответ (evidence):** три уровня:

1. **Диск (forge-артефакты):** паспорта декларируют пути `projects_17/<slug>/forge/…` (review.yaml: `review_verdict.md`; governance.yaml: `governance_alignment.yaml`, `policy_violations.md`, `remediation_plan.md`).
2. **Opportunity:** `opportunity.artifacts: list[dict***REMOVED***` — resulting_artifact после run_chain (`data_13/opportunities.yaml`).
3. **Knowledge/Memory:** `MemoryStore.store_knowledge(kind="candidate", …)` — ACCUMULATE (GAP-2, promt 085), + `LearningLoop.capture/record_feedback` + GraphIndex edge (артефакт→opportunity→scenario→knowledge).

**Статус контракта:** ✅ CONFIRMED (существующие механизмы, НЕ новая система хранения).

---

## Вопрос 10. Как результат возвращается в Intelligence?

**Ответ (evidence):**

```
ForgeFacade.run_chain → ChainRun (chain + overall)          # scripts_01/opportunity_engine.execute
    → opportunity.artifacts.append(...)                      # data_13/opportunities.yaml
    → MemoryStore.store_knowledge(kind="candidate", tag=opportunity)   # ACCUMULATE
    → LearningLoop (уроки)                                   # record_feedback
    → ScenarioIntelligence.feedback_v0 (kind=candidate, tag=scenario_decision, lifecycle validated/raw)
    → события: execution.completed / scenario.feedback       # EventBus
```

- Обратная связь в ранжирование: `evaluate()` читает history из MemoryStore (`query_by_type("candidate", limit=500)`, title-префикс `scenario:<id>`) → history-компонента composite score.

**Статус контракта:** ✅ CONFIRMED (петля замкнута: execution → memory → re-evaluation).

---

## Вопрос 11. Где находится feedback?

**Ответ (evidence):** **ScenarioIntelligence.feedback_v0()** — единственная точка:

```
scripts_01/scenario_intelligence.py:623  feedback_v0(decision, outcome, memory_store, learning_loop, event_bus)
    → MemoryStore.store_knowledge(kind="candidate", title=f"scenario:{scenario_id***REMOVED***",
                                  tags=["scenario_decision", ...***REMOVED***, lifecycle_stage=validated|raw)
    → MemoryStore.record_learning_event(trigger_id, context_snapshot, outcome, lesson_id)
    → LearningLoop.record_feedback(kid, outcome)          # только success/failure
    → event scenario.feedback
```

- Также Opportunity-level: `advance(opp, "FAILED"/"COMPLETED")` + `execution.failed/completed` события.

**Статус контракта:** ✅ CONFIRMED (v0: прозрачный, без ML; НЕ новый feedback engine).

---

## Вопрос 12. Можно ли заменить ContentFactory другим Factory без изменения Intelligence Core?

**Ответ (evidence):** **ДА по архитектуре — с оговоркой по словарю.**

1. **Domain-neutrality подтверждена кодом:** `ScenarioIntelligence` не содержит ни одного content-specific токена/ветки; работает с `CapabilityRequirement` (непрозрачный токен) → `FactoryRegistry.select_forge` → пара паспортов. Смена домена = добавление паспортов в `runtime_05/factories/<domain>/`, а не правка ядра.
2. **Negative-тест уже существует как паттерн:** `tests_09/test_scenario_intelligence.py:117` использует фейковый маппинг `article_generation → articles_factory/article_forge` — доказывает contract resolution без content-branching.
3. **Оговорка (G1):** закрытый словарь `KNOWN_CAPABILITIES` (`core_02/blueprint_v3.py:148`) не содержит контент-токенов → в проде `select_forge("article_generation")` = None. *(Статус: INFERRED — хорошо поддержанный вывод: контент-манифестов в `runtime_05/factories/` нет, поэтому select_forge не найдёт пару; прямого прогона не выполнялось.)* Регистрация токенов — обязательный register-first шаг ДО реализации Content Factory (иначе ANTI-6b silent fallback на слабую модель).
4. **Phase 9 требование §17:** обязательный negative-тест «SI не знает, что это Content Factory» — возможен через mock TEST_FACTORY (вторая capability в тесте) без изменения SI; зафиксировать ограничение, если архитектура не позволяет.

**Статус контракта:** ✅ универсальность ядра подтверждена (Phase 8); ⚠️ контент-домен требует register-first регистрации.

---

## Сводная таблица аудита (12 вопросов)

| # | Вопрос | Статус | Evidence (path·symbol) |
|---|--------|--------|------------------------|
| 1 | Где возникает capability | ✅ | `scenario_intelligence.py::_candidate_capability` (scenario.capabilities[0***REMOVED*** / role.routing_hint[0***REMOVED***) |
| 2 | Кто выбирает | ✅ | `scenario_intelligence.py::select` + `opportunity_engine.py::propose` (BC-fallback) |
| 3 | Кто разрешает | ✅/⚠️ | `scenario_intelligence.py::resolve_capability` → `factory_registry.py::select_forge` (контент-словарь не зарегистрирован) |
| 4 | Кто находит Factory | ✅ | `factory_registry.py::find_factories_by_capability/get_factory` (только architecture в проде) |
| 5 | Как Factory получает вход | ❌ GAP | inputs декларируются в паспортах; input normalization отсутствует (§G контракта) |
| 6 | Как Factory формирует request | ❌ GAP | execution request напрямую через run_chain; factory-слой не реализован |
| 7 | Кто вызывает Forge | ✅ | `forge_facade.py::run_chain/initiate_forge` — единственный мост; SI не вызывает (test_8) |
| 8 | Кто валидирует | ✅ | `RoleArtifactValidator` (внутри run_chain, compose_artifact_check=True) |
| 9 | Где сохраняется Artifact | ✅ | `projects_17/<slug>/forge/` + `opportunity.artifacts` + MemoryStore kind=candidate |
| 10 | Возврат в Intelligence | ✅ | ChainRun → artifacts → MemoryStore ACCUMULATE → LearningLoop → feedback_v0 |
| 11 | Где feedback | ✅ | `scenario_intelligence.py::feedback_v0` + `opportunity_engine.py::advance` (FAILED/COMPLETED) |
| 12 | Замена домена без правки ядра | ✅/⚠️ | domain-neutral подтверждён; register-first словарь обязателен |

**Итог аудита:** 9/12 пунктов CONFIRMED (universal core + execution chain Phase 8), 2 GAP (вход/request Factory — пункты 5-6), 1 условный (пункт 12 — регистрация словаря). **Второй параллельный Factory Contract НЕ требуется** — используем `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §G as-is.

---
_Источник: promt 92 §6. Дата: 2026-08-17. Следующий шаг: PHASE9_IMPLEMENTATION_PLAN.md (после согласования forensics)._
