# PHASE9_REPOSITORY_REALITY_MAP.md — Repository Reality Map (Phase 9, promt 92)

> **Статус:** FORENSICS OUTPUT — до реализации (promt 92 §4). Repository = Source of Truth.
> **Дата:** 2026-08-17 · **Версия платформы:** v5.189.25+ · **Метод:** evidence path+symbol (CODE > TESTS > CONFIG > DOCUMENTATION > ASSUMPTION).
> **Пакет:** `phase9_evaluation_30/` (конвенция `phase<N>_<name>_<id>`, продолжение phase8_evaluation_29).

---

## A. Repository structure (актуальная карта)

```
freebuff/
├── core_02/                      # ядро: registry/engine/facade слои
│   ├── scenario_registry.py      # ScenarioRegistry (каталог сценариев)
│   ├── factory_registry.py       # FactoryRegistry (реестр фабрик, C-2 v5.189.21)
│   ├── factory_passport.py       # FactoryPassport (паспорт factory.yaml)
│   ├── forge_passport.py         # ForgePassport (паспорт forge.yaml)
│   ├── forge_facade.py           # ForgeFacade (ЕДИНСТВЕННЫЙ execution boundary)
│   ├── forge_pipeline.py         # ForgePipeline (CI-конвейер, 14 ролей)
│   ├── forge_registry.py         # ForgeRegistry (статусы проектов UNFORGED→DEPLOYED)
│   ├── memory_store.py           # MemoryStore (knowledge objects, kind=candidate)
│   ├── semantic_layer.py         # SemanticLayer (TF-IDF поиск)
│   ├── learning_loop.py          # LearningLoop (уроки CON/CAN/ANTI)
│   ├── missing_registry.py       # MissingRegistry (register-first, 21 запись)
│   └── blueprint_v3.py           # KNOWN_CAPABILITIES (закрытый словарь) + ModelCatalog
├── scripts_01/                   # исполняемые слои + CLI
│   ├── scenario_intelligence.py  # ScenarioIntelligence (Phase 8, domain-neutral)
│   ├── opportunity_engine.py     # Opportunity Engine (lifecycle + DISCOVER + propose)
│   ├── whim_capture.py           # Whim Capture (лёгкий вход)
│   ├── forge.py / forge_api.py   # CLI Forge / API
│   ├── event_bus.py              # EventBus
│   ├── knowledge_engine.py / graph_index.py / project_pulse.py
│   └── research_web.py / lisa_estimator.py
├── runtime_05/
│   ├── scenarios/                # blueprint_v3.yaml, vkusvill_demo.yaml, 19_remote_sync/
│   └── factories/                # ТОЛЬКО architecture/ (factory.yaml, governance.yaml, review.yaml)
├── data_13/                      # YAML-реестры + SQLite
│   ├── opportunities.yaml        # 1 запись: opp-07f05311ec «Создать книгу по Workspace OS» (READY)
│   ├── whims.yaml · scenario_decisions.yaml (seed) · forge_registry.yaml · missing_registry.yaml
├── projects_17/                  # проекты; content_factory/ = ТОЛЬКО концепты (concept*.md, promts/)
├── books_out_23/                 # материалы обучения (00..08_*.md) — контент-исходники
├── docs_10/engineering-memory/   # INTELLIGENCE_FACTORY_CONTRACT_V1.md, FACTORY_FORGE_ARCHITECTURE_V1.md,
│                                 # SCENARIO_ENGINE_DESIGN_V1.md (дизайн), CONTRACT_REGISTRY_V1.md
└── phase8_evaluation_29/         # Phase 8 eval-пакет + NEXT_PHASE_RECOMMENDATION (Content Factory)
```

---

## B. Existing Intelligence components (подтверждено кодом)

| Компонент | Файл · Символ | Evidence (API) | Статус |
|-----------|---------------|----------------|--------|
| **Universal Scenario Intelligence** | `scripts_01/scenario_intelligence.py` · `ScenarioIntelligence` | `discover()` · `evaluate()` · `rank()` · `select()` · `resolve_capability()` · `feedback_v0()`; `ScenarioCandidate` / `CapabilityRequirement` / `ScenarioDecision`; `DecisionHistoryStore` (YAML); CLI discover/select/evaluate/resolve/feedback/history | ✅ **CONFIRMED** (Phase 8, v5.189.25) |
| **Opportunity Engine** | `scripts_01/opportunity_engine.py` · `Opportunity` (24 поля) / `OpportunityStore` / `advance` / `discover_candidates` / `propose` / `execute` | lifecycle ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED/FAILED; rank_score/rank_candidates (promt 086); `propose()` делегирует в ScenarioIntelligence с **BC-fallback** | ✅ **CONFIRMED** (v5.187.7, promt 079_19) |
| **Whim Capture** | `scripts_01/whim_capture.py` · `WhimStore` / `capture` / `triage` / `promote` | FSM NEW→TRIAGED→PROMOTED_TO_OPPORTUNITY/DISCARDED/DEFERRED/FAILED | ✅ **CONFIRMED** (v5.187.8, promt 080_19) |
| **EventBus** | `scripts_01/event_bus.py` · `EventBus` / `publish` / `subscribe` | события scenario.*, opportunity.*, execution.*, whim.* | ✅ **CONFIRMED** |

**Ключевой инвариант:** `ScenarioIntelligence` — domain-neutral: `_candidate_capability()` берёт capability-токен из `scenario.capabilities[0***REMOVED***` или `role.routing_hint[0***REMOVED***` как **непрозрачный токен** (article_generation / api_implementation / image_generation / …). Никакого `if capability == "article"` в коде НЕТ (grep подтверждает).

---

## C. Existing Scenario components

| Компонент | Файл · Символ | Evidence | Статус |
|-----------|---------------|----------|--------|
| **ScenarioRegistry** | `core_02/scenario_registry.py` · `ScenarioRegistry` | `list_scenarios()` · `get(scenario_id)` · `find_role()` · `all_roles()` · `propose_roles(query, top_n)` · `validate_all()`; авто-дискавери `runtime_05/scenarios/*.yaml` | ✅ **CONFIRMED** |
| **Scenario manifests** | `runtime_05/scenarios/blueprint_v3.yaml` · `vkusvill_demo.yaml` · `19_remote_sync/` | blueprint_v3: capabilities `role-based-pipeline`, `xml-section-schema`, `yaml-manifest-registry`, `code-capable`, `architecture-capable`, `qa-capable`, `review-capable` | ✅ **CONFIRMED** (2 активных + 1 подпапка) |
| **Scenario Engine (оркестратор)** | `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` | дизайн-документ; в коде НЕТ (Missing #2, §20 карта: «дизайн готов») | ⚠️ **DESIGN-ONLY** |

**Вывод:** Scenario Intelligence НЕ создаёт второй registry — использует существующий `ScenarioRegistry` как каталог (Phase 8 инвариант подтверждён кодом).

---

## D. Existing Factory components (ГЛАВНЫЙ РАЗДЕЛ — forensics)

| Компонент | Файл · Символ | Evidence | Статус |
|-----------|---------------|----------|--------|
| **FactoryRegistry** | `core_02/factory_registry.py` · `FactoryRegistry` | `get_factory(factory_id)` · `factory_capabilities(factory_id)` (union factory.yaml + forge passports) · `find_factories_by_capability(capability)` · `select_forge(capability, prefer_status)` (status-priority production>material>design, tie-break) · `capability_catalog()` | ✅ **CONFIRMED** (v5.189.21, Missing #20 закрыт) |
| **FactoryPassport** | `core_02/factory_passport.py` · `FactoryPassport` | frozen dataclass (factory_id/display_name/version/status/description/capabilities/metadata); `from_yaml/to_yaml/to_dict/validate`; ANTI-6b vocab guard | ✅ **CONFIRMED** |
| **ForgePassport** | `core_02/forge_passport.py` · `ForgePassport` | паспорт кузен; `runtime_05/factories/*/*.yaml` | ✅ **CONFIRMED** |
| **Architecture Factory manifest** | `runtime_05/factories/architecture/factory.yaml` | `factory_id: architecture`, status=**production**, capabilities: `architecture`, `review`, `validate`, `report`, `explain` | ✅ **CONFIRMED** |
| **Architecture Governance Forge** | `runtime_05/factories/architecture/governance.yaml` | `forge_id: governance`, status=**material**, capabilities: `validate`, `report`, `explain`; inputs/outputs/artifacts/interfaces/memory/knowledge | ✅ **CONFIRMED** |
| **Architecture Review Forge** | `runtime_05/factories/architecture/review.yaml` | `forge_id: review`, capabilities: `review`, `architecture`, `explain`; workflow: problem_validation/context_analysis/impact_analysis/verdict_generation/report_generation; outputs review_verdict/review_report | ✅ **CONFIRMED** |
| **Content Factory manifest** | `runtime_05/factories/content/…` | **НЕ СУЩЕСТВУЕТ** (директории content/ нет — проверено ls) | ❌ **MISSING** |
| **Content Factory (движок)** | `projects_17/content_factory/concept*.md` | ТОЛЬКО концепты + promts/1-4.md; отдельного content-движка НЕТ (phase6 forensics: DOCUMENTED_ONLY) | ⚠️ **DOCUMENTED_ONLY** |

**Критическое forensics-открытие (дрейф NEXT_PHASE_RECOMMENDATION):**
`phase8_evaluation_29/NEXT_PHASE_RECOMMENDATION.md` §2 утверждает: «Capability-токены (уже в KNOWN_CAPABILITIES): article_generation, report_generation, book_generation». **Проверка кода опровергает:**

```
core_02/blueprint_v3.py:148-158  KNOWN_CAPABILITIES = {local, fast, code, summarize, router,
                                  classify, reasoning, plan, refactor, explain, deep, architecture,
                                  review, vision, tools, long_context, multimodal, instruct,
                                  diagnose, validate, report, research, estimation***REMOVED***
```
→ `article_generation` / `book_generation` / `report_generation` **ОТСУТСТВУЮТ** в закрытом словаре. Также:
- `articles_factory` / `article_forge` в тестах Phase 8 (`tests_09/test_scenario_intelligence.py:117`) — **только тестовые фейки** `_FakeFactoryRegistry`, НЕ реальные манифесты;
- `report_generation` встречается только как шаг production_workflow в review.yaml, НЕ как capability.

**Вывод:** путь «Content Factory» в проде НЕ разблокирован. Для Phase 9 обязателен register-first: токены → `KNOWN_CAPABILITIES` + реальные манифесты `runtime_05/factories/content/`.

---

## E. Existing Forge components

| Компонент | Файл · Символ | Evidence | Статус |
|-----------|---------------|----------|--------|
| **ForgeFacade** | `core_02/forge_facade.py` · `ForgeFacade` | `run_chain(project, role_ids, …, project_read_only=True) -> ChainRun` · `initiate_forge(project, requested_by_role) -> ForgeFacadeResult` · `validate_role_artifacts` · `RoleArtifactValidator` · `PIPELINE_CHAIN` (14 ролей) | ✅ **CONFIRMED** — **единственный санкционированный мост** (§7.3 B-rule) |
| **ForgePipeline** | `core_02/forge_pipeline.py` · `ForgePipeline` | `stage_forge/check/build/test/deploy/report/run(skip)` · `PipelineRun` · `StageResult` · `_run_cmd` (argv-list, shell=False) | ✅ **CONFIRMED** |
| **ForgeRegistry** | `core_02/forge_registry.py` · `ForgeRegistry` | `register_project` · `get_project_status` · `record_run` · `promote_status` · `list_projects_by_status`; STATUSES UNFORGED→CHECKING→BUILDING→TESTING→DEPLOYED, FAILED | ✅ **CONFIRMED** |
| **Project statuses** | `data_13/forge_registry.yaml` | interior-planner: DEPLOYED + run_ok (смешанные stage-статусы) | ✅ **CONFIRMED** |

**Инвариант:** Scenario/Factory НЕ вызывают ForgePipeline напрямую — только через ForgeFacade (подтверждено в `scenario_intelligence.py` — ForgeFacade не вызывается вообще; execution boundary соблюдён, test_8_forge_boundary).

---

## F. Existing capability resolution (цепочка)

```
ScenarioCandidate.capability            (непрозрачный токен)
   ↓  ScenarioIntelligence.evaluate()   — capability_available через FactoryRegistry.capability_catalog()
   ↓  ScenarioIntelligence.select()     — CapabilityRequirement{capability, scenario_id, role_id***REMOVED***
   ↓  ScenarioIntelligence.resolve_capability()  →  FactoryRegistry.select_forge(capability)
   ↓                                                          → (FactoryPassport, ForgePassport)
   (factory_id, forge_id)                — фиксируются в ScenarioDecision
```

- `resolve_capability` — `scripts_01/scenario_intelligence.py:594-622`: `hasattr(factory_registry, "select_forge")` → пара паспортов; fail-safe (None, None) при отсутствии.
- `opportunity_engine._derive_capability()` — токен из provenance/scenario; закрытый словарь (ANTI-6b).
- **GAP:** FactoryRegistry умеет резолвить ТОЛЬКО токены из capabilities существующих паспортов (architecture/review/validate/report/explain). Контент-токены не зарегистрированы → `select_forge("article_generation")` вернёт None в проде.

---

## G. Existing registry mechanisms

| Реестр | Файл | Назначение |
|--------|------|-----------|
| MissingRegistry | `core_02/missing_registry.py` + `data_13/missing_registry.yaml` | register-first lifecycle: registered → design_ready → prompt_written → implemented (21 запись, check OK) |
| ForgeRegistry | `data_13/forge_registry.yaml` | статусы проектов |
| FactoryRegistry | `runtime_05/factories/*/` | паспорта фабрик/кузен (ТОЛЬКО architecture) |
| ScenarioRegistry | `runtime_05/scenarios/*.yaml` | сценарии-манифесты |
| CONTRACT_REGISTRY_V1 | `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | 17 контрактов (16 CURRENT / 1 PARTIAL), 35 @event, 11 storage |

---

## H. Existing Content-related artifacts

| Артефакт | Path | Статус |
|----------|------|--------|
| Концепты Content Factory | `projects_17/content_factory/concept.md`, `concept_1.md`, `concept_2.md` | ⚠️ DOCUMENTED_ONLY (дизайн-тексты, НЕ код) |
| Промты контент-фабрики | `projects_17/content_factory/promts/1.md`–`4.md` | ⚠️ DOCUMENTED_ONLY (архитектурные задания) |
| Учебные материалы | `books_out_23/00..08_*.md` | ✅ данные (реальные контент-исходники) |
| Opportunity «Создать книгу по Workspace OS» | `data_13/opportunities.yaml` opp-07f05311ec | ✅ READY (создана из whim, source=whim:cli, priority 5) |
| Контракт Intelligence↔Factory | `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` | ✅ ACTIVE (§G Factory Contract — минимальный, декларативный) |
| §12 Content Factory (карта) | `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` §12 | ⚠️ DESIGN (структура PRODUCTION SYSTEM, в коде нет) |

**Вывод:** контент-данные ЕСТЬ (books_out_23, whims, opportunity), но производственный путь (content factory manifest → content forge → ForgeFacade) — отсутствует целиком.

---

## I. Existing tests (релевантные)

| Тест-файл | Покрытие | Статус |
|-----------|----------|--------|
| `tests_09/test_scenario_intelligence.py` | 18 тестов: discovery/multi/ranking/selection/provenance/capability/factory/forge/feedback/events/persistence/BC/unavailable/deferred/reselection + main integration | ✅ green (v5.189.25) |
| `tests_09/test_factory_registry.py` | FactoryRegistry C-2: get_factory/factory_capabilities/find_factories_by_capability/select_forge/capability_catalog | ✅ green |
| `tests_09/test_factory_passport.py` | FactoryPassport (9 тестов) | ✅ green |
| `tests_09/test_opportunity_engine.py` | 32 теста: state graph/DEFERRED/FAILED retry/dry-run/rank | ✅ green |
| `tests_09/test_whim_capture.py` | 39 тестов | ✅ green |
| `tests_09/test_intelligence_loop_phase5.py` | Phase 5 loop (score composite 0.74) | ✅ green |
| `tests_09/test_phase7_factory_event.py` | 26 тестов (события + factory selection) | ✅ green |

**Negative-тест domain isolation (Phase 8, §18):** `test_scenario_intelligence.py` использует `_FakeScenario("scenario_a", ["article_generation"***REMOVED***)` + `_FakeRole("writer", …)` — доказывает, что SI работает с любым токеном без content-branching. **Для Phase 9 потребуется реальный (не фейковый) TEST_FACTORY-манифест или реальный content manifest.**

---

## J. Existing execution paths

```
1. CLI: scripts_01/scenario_intelligence.py select <opp_id> --json
     → OpportunityStore.get → ScenarioIntelligence.select
     → discover → evaluate → rank → resolve_capability (FactoryRegistry.select_forge)
     → ScenarioDecision → DecisionHistoryStore.add → scenario.selected event

2. CLI: scripts_01/opportunity_engine.py run <opp_id>
     → propose (SI BC-fallback) → execute → ForgeFacade.run_chain(project, role_ids, project_read_only=True)
     → ChainRun → RoleArtifactValidator → opportunity.artifacts.append → ACCUMULATE (MemoryStore kind=candidate)

3. CLI: scripts_01/forge.py chain <slug>
     → ForgeFacade.run_chain → ForgeRegistry.record_run (проект-статусы)
```

**Полного vertical slice Opportunity→Factory→Forge→Artifact в проде НЕТ:** шаг «Factory формирует execution request» отсутствует (нет content adapter; opportunity.artifacts заполняется напрямую через run_chain без factory-нормализации).

---

## K. Existing integration contracts

| Контракт | Файл | Статус |
|----------|------|--------|
| Intelligence ↔ Factory ↔ Scenario ↔ Forge | `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` (A–P) | ✅ ACTIVE (canonical; §E reconciled к runtime 2026-08-17) |
| Factory/Forge архитектура | `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` (§12 Content Factory, §15 Production Flow, §20 карта 21 row, §21 Recommended Architecture) | ✅ ACTIVE |
| Contract Registry | `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` (#17 scenario.intelligence, 16 CURRENT/1 PARTIAL) | ✅ ACTIVE |
| Scenario Intelligence Contract | `phase8_evaluation_29/SCENARIO_INTELLIGENCE_CONTRACT_V1.md` | ✅ ACTIVE |
| Scenario Engine Design | `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` | ⚠️ DESIGN-ONLY |

**Инвариант §6 промта:** НЕ создавать второй параллельный Factory Contract — Phase 9 использует существующий INTELLIGENCE_FACTORY_CONTRACT_V1 §G + карту §12/§15.

---

## L. Gaps (evidence-based)

| # | Gap | Evidence | Severity |
|---|-----|----------|----------|
| **G1** | Контент-токены (article_generation/book_generation/report_generation) отсутствуют в `KNOWN_CAPABILITIES` | `core_02/blueprint_v3.py:148-158` vs NEXT_PHASE_RECOMMENDATION заявление | 🔴 HIGH (register-first, ANTI-6b) |
| **G2** | Нет манифеста Content Factory (`runtime_05/factories/content/`) и content forge-паспортов | `ls runtime_05/factories/` → только architecture/ | 🔴 HIGH |
| **G3** | Нет FactoryAdapter/content normalization (input/output normalization, execution request) | `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §G: «CURRENT IMPLEMENTATION: отсутствует (G2)» | 🔴 HIGH |
| **G4** | articles_factory/article_forge существуют только как тестовые фейки | `tests_09/test_scenario_intelligence.py:117` | 🟡 MEDIUM |
| **G5** | Vertical slice не проходит end-to-end (opportunity.artifacts без factory-шага) | execution paths §J | 🟡 MEDIUM |
| **G6** | SCENARIO_ENGINE_DESIGN_V1.md — дизайн без кода (Missing #2) | docs vs ls core_02 | 🟢 LOW (не блокер Phase 9) |
| **G7** | `data_13/scenario_decisions.yaml` — пустой seed (история решений пуста) | seed `{***REMOVED***` | 🟢 LOW (ожидаемо) |

---

## M. Architectural risks

| Risk | Evidence | Mitigation (Phase 9) |
|------|----------|---------------------|
| R1: drift «токены в KNOWN_CAPABILITIES» повторится | NEXT_PHASE_RECOMMENDATION утверждал несуществующее | register-first: токены → KNOWN_CAPABILITIES ДО кода; drift-guard уже активен: `tests_09/test_wizard.py:354` `test_known_capabilities_subset_of_actual_catalog` + `test_capabilities_override_now_routing_safe` (падёт, если токен добавлен без зеркала в ModelCatalog) |
| R2: Content Factory выдана за production-код | concept*.md ≠ код (phase6 DOCUMENTED_ONLY) | Phase 9 НЕ создаёт «движок» — только манифесты + adapter через существующие механизмы |
| R3: ScenarioIntelligence получит content-branching | инвариант §1 промта 92 | negative test: TEST_FACTORY (mock-домен) доказывает domain isolation |
| R4: Factory подменит Forge (Factory станет исполнителем) | §10 промта 92 | Factory = normalization + execution request; исполнение ТОЛЬКО через ForgeFacade |
| R5: второй параллельный Factory Contract | §6 промта 92 | использовать INTELLIGENCE_FACTORY_CONTRACT_V1 §G as-is |
| R6: scope creep (Concept Evolution, Whim UI, новые БД) | §20 промта 92 | deferred-реестр с причинами (§21) |

---

## N. Exact files that WILL be modified (Phase 9, предварительно — после плана)

| Файл | Изменение |
|------|-----------|
| `core_02/blueprint_v3.py` | += контент-токены в KNOWN_CAPABILITIES (register-first, с ModelCatalog-зеркалом) |
| `runtime_05/factories/content/factory.yaml` | НОВЫЙ манифест Content Factory (capabilities ⊆ KNOWN_CAPABILITIES) |
| `runtime_05/factories/content/<forge>.yaml` | НОВЫЙ content forge-паспорт (по образцу review.yaml/governance.yaml) |
| `data_13/missing_registry.yaml` | register-first: `content_factory` capability → implemented |
| `scripts_01/` или `core_02/` (adapter) | FactoryAdapter/ContentFactory — input/output normalization + execution request (минимальный, без дублирования ForgePipeline) |
| `tests_09/test_phase9_*.py` | unit + integration + negative domain-isolation тесты |
| `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` | §20 карта row #22 (content_factory) |
| `CHANGELOG.md` | версия v5.189.x+ |
| `phase9_evaluation_30/` | полный eval-пакет (12 документов §23) |

---

## O. Exact files that MUST NOT be modified (Phase 9)

| Файл | Причина |
|------|---------|
| `scripts_01/scenario_intelligence.py` | Phase 8 universal core — НЕ трогаем (domain-neutral инвариант; расширение только через registry) |
| `core_02/scenario_registry.py` | единственный каталог сценариев, НЕ дублируется |
| `core_02/forge_facade.py` / `forge_pipeline.py` | execution boundary — НЕ создаём второй исполнитель |
| `core_02/memory_store.py` / `semantic_layer.py` / `learning_loop.py` | существующая память, НЕ новая memory system |
| `scripts_01/event_bus.py` | существующая шина, НЕ новая event system |
| `core_02/factory_registry.py` / `factory_passport.py` | существующий реестр (v5.189.21) — используем as-is (допустимо минимальное расширение только через манифесты) |
| `projects_17/content_factory/concept*.md` | документы-концепты — НЕ переписываем (canonical-дизайн) |
| `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md` | канонический контракт — НЕ создаём второй (возможна только аддитивная заметка о статусе реализации) |
| `data_13/opportunities.yaml` / `whims.yaml` | живые данные, НЕ трогаем в тестах |

---

## Резюме forensics

1. **Universal core (Phase 8) — подтверждён:** ScenarioIntelligence domain-neutral, ForgeFacade — единственный execution boundary, FactoryRegistry умеет select_forge.
2. **Content Factory — НЕ существует в проде:** ни манифестов, ни токенов в закрытом словаре, ни adapter. Есть только концепты + тестовые фейки.
3. **Обязательный первый шаг Phase 9:** register-first (токены → KNOWN_CAPABILITIES + missing_registry) → манифесты → adapter → negative domain-isolation тест.
4. **Используем существующий контракт** INTELLIGENCE_FACTORY_CONTRACT_V1 §G — второй контракт НЕ создаём.

---
_Источник: promt 92 §4 (A–O). Дата: 2026-08-17. Следующий документ: PHASE9_FACTORY_CONTRACT_AUDIT.md (§6)._
