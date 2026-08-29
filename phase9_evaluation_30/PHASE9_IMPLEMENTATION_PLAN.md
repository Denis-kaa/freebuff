# PHASE9_IMPLEMENTATION_PLAN.md — Phase 9 Universal Factory Vertical Slice (§13)

> **Статус:** ПЛАН (после forensics §4 + contract audit §6). **Дата:** 2026-08-17.
> **Метод:** минимальный · последовательный · проверяемый · evidence-based · register-first.
> **Пакет:** `phase9_evaluation_30/`.

---

## 0. Принципы (из Reality Map / Contract Audit)

1. **Universal core (Phase 8) НЕ трогаем:** `scenario_intelligence.py` — без content-branching; расширение только через registry.
2. **Content Factory — только в пределах существующих возможностей:** `article_generation` / `book_generation` / `report_generation` сейчас **НЕ production-ready** (нет манифестов, нет токенов в закрытом словаре). Честно фиксируем: полный content-движок — **DEFERRED**; Phase 9 доказывает **универсальный контракт**, а не строит движок.
3. **Factory ≠ Forge:** ContentFactory = input normalization + execution request + output normalization; исполнение — ТОЛЬКО через `ForgeFacade.run_chain` (единственный boundary).
4. **Register-first:** токены → `KNOWN_CAPABILITIES` + `ModelCatalog` (drift-тест `test_wizard.py:354`) + `missing_registry` ДО манифестов.
5. **Второй Factory Contract НЕ создаём:** используем `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §G as-is.
6. **Domain isolation:** negative-тест «SI не знает про ContentFactory» через TEST_FACTORY (вторая capability в том же FactoryRegistry).

---

## 1. Шаги (STEP ID / PURPOSE / FILES / CHANGES / DEPENDENCIES / TEST / ACCEPTANCE / ROLLBACK)

### STEP-1 — Register-first: контент-токены в закрытый словарь
- **PURPOSE:** зарегистрировать `article_generation` / `book_generation` / `report_generation` в `KNOWN_CAPABILITIES` + зеркало в `ModelCatalog` (иначе drift-тест падает и FactoryPassport.validate() отклоняет манифест).
- **FILES:** `core_02/blueprint_v3.py` (KNOWN_CAPABILITIES), `core_02/router.py` (ModelCatalog: deepseek-v4-pro + gemini-2.5-flash capabilities).
- **CHANGES:** += контент-токены в frozenset и в capabilities 2 облачных моделей.
- **DEPENDENCIES:** —.
- **TEST:** `python -m pytest tests_09/test_wizard.py -q` (drift-тесты `test_known_capabilities_subset_of_actual_catalog` / `test_capabilities_override_now_routing_safe`).
- **ACCEPTANCE:** drift-тесты зелёные; `KNOWN_CAPABILITIES` содержит контент-токены.
- **ROLLBACK:** revert blueprint_v3.py + router.py.

### STEP-2 — Register-first: missing_registry + §20 карта
- **PURPOSE:** зафиксировать `content_factory` capability (kind=capability, factory=content) в MissingRegistry по lifecycle registered → prompt_written → implemented.
- **FILES:** `data_13/missing_registry.yaml` (через CLI), `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` (§20 row #22).
- **CHANGES:** `python -m core_02.missing_registry register content_factory --kind capability --factory content` → `mark-prompt-written` → (после STEP-4) `mark-implemented`.
- **TEST:** `python -m core_02.missing_registry check` (exit 0).
- **ACCEPTANCE:** реестр валиден, `content_factory` lifecycle = implemented (после STEP-4).
- **ROLLBACK:** `missing_registry` CLI reset.

### STEP-3 — Манифесты Content Factory
- **PURPOSE:** реальные паспорта в `runtime_05/factories/content/` (по образцу architecture/).
- **FILES:** `runtime_05/factories/content/factory.yaml` (FactoryPassport: capabilities ⊆ KNOWN_CAPABILITIES), `runtime_05/factories/content/writing.yaml` (ForgePassport).
- **CHANGES:** factory_id=content, status=production; forge_id=writing, status=material; capabilities = контент-токены; inputs/outputs/artifacts/quality_gates.
- **DEPENDENCIES:** STEP-1 (закрытый словарь).
- **TEST:** `python -m pytest tests_09/test_factory_registry.py tests_09/test_factory_passport.py -q` (валидация паспортов, ANTI-6b guard).
- **ACCEPTANCE:** `FactoryRegistry().select_forge("article_generation")` → (content, writing); `factory.yaml` валиден (B10/R-127).
- **ROLLBACK:** удалить `runtime_05/factories/content/`.

### STEP-4 — ContentFactory adapter (минимальный, additive)
- **PURPOSE:** первый доменный Factory-adapter: normalize_input → build_execution_request → execute (ForgeFacade.run_chain) → normalize_output → ACCUMULATE/feedback. НЕ дублирует ForgePipeline.
- **FILES:** `scripts_01/content_factory.py` (NEW), `tests_09/test_content_factory.py` (NEW).
- **CHANGES:** `ContentFactory` класс + `ExecutionRequest` dataclass + CLI `content_factory run <opp_id> [--dry-run***REMOVED*** [--json***REMOVED***`.
  - `resolve(capability)` → FactoryRegistry.select_forge (universal contract);
  - `normalize_input(opp)` → domain input (title/description/sources/target);
  - `build_execution_request(opp, capability)` → ExecutionRequest (project, role_ids=CONTENT_ROLE_IDS, inputs, output_spec) — НЕ исполняет;
  - `execute(opp, dry_run, project_root, event_bus)` → resolve → normalize → request → `ForgeFacade.run_chain` → normalize_output → artifact → MemoryStore store_knowledge + record_learning_event;
  - CLI + exit-коды (0/1/2), fail-safe.
- **DEPENDENCIES:** STEP-1/2/3.
- **TEST:** unit (resolution, invalid capability, missing factory, input/output normalization, invalid input) + integration (Opportunity → SI.select → capability → ContentFactory → ForgeFacade → artifact → memory) + negative domain-isolation (TEST_FACTORY).
- **ACCEPTANCE:** 100% тестов; mypy 0; AST OK.
- **ROLLBACK:** удалить content_factory.py + тесты.

### STEP-5 — Negative domain-isolation тест
- **PURPOSE:** доказать «SI не знает, что это Content Factory» (промт §17).
- **FILES:** `tests_09/test_content_factory.py::test_domain_isolation_si_agnostic`.
- **CHANGES:** второй fake-factory (TEST_FACTORY, capability `api_implementation`) в том же FactoryRegistry; `ScenarioIntelligence.select` резолвит ОБЕ capability одинаково (content + test) без изменения кода SI.
- **TEST:** trigger через `scenario_intelligence.py` (НЕ content_factory).
- **ACCEPTANCE:** обе capability резолвятся через универсальный путь; SI не содержит content-строк (grep-assert).
- **ROLLBACK:** —.

### STEP-6 — Валидация + ревью
- **PURPOSE:** полный gate.
- **TEST:** `pytest tests_09/test_content_factory.py tests_09/test_factory_registry.py tests_09/test_scenario_intelligence.py tests_09/test_opportunity_engine.py -q` + `mypy scripts_01/content_factory.py` + `consistency_check` + `missing_registry check` + code-reviewer-glm.
- **ACCEPTANCE:** все зелёные, consistency TOTAL 0.

### STEP-7 — Eval-пакет (12 документов §23) + архив
- **PURPOSE:** обязательный Evaluation Package + Handoff Archive.
- **FILES:** `phase9_evaluation_30/01..12_*.md` (см. §23 промта) + `PHASE9_FACTORY_VERTICAL_SLICE_<VERSION>.tar.gz` + `PHASE9_ARCHIVE_MANIFEST.sha256`.
- **TEST:** `tar -tzf` + `sha256sum -c`.
- **ACCEPTANCE:** архив полный, sha256 верифицирован.

---

## 2. DEFERRED (НЕ входит в Phase 9, §20/§21 — с причинами)

| Идея | Почему не сейчас | Что нужно перед реализацией | Будущая фаза |
|------|------------------|-----------------------------|--------------|
| Полный Content Production Engine (писать статьи/книги) | Нет content-движка в репо (DOCUMENTED_ONLY); Phase 9 доказывает контракт, не строит движок | Content-движок + реальный content forge с артефактами | Phase 10+ |
| Code/Research/Media Factory | Только 1 домен за раз (ANTI-5 scope discipline) | Content vertical slice принят | Phase 10+ |
| Concept Evolution System (C-A/C-B/C-C) | Другой слой (промт §12) | Отдельный дизайн | — |
| Whim UI / Workspace widgets | Вне scope | UI-слой | — |
| Новые БД / event system / LLM-фреймворки | §20 запрещает | — | никогда (используем существующие) |

---

## 3. Риски и митигации (из Reality Map §M)

- **R1 (drift словаря):** content-токены в KNOWN_CAPABILITIES БЕЗ ModelCatalog → drift-тест падает. Митигация: STEP-1 синхронизирует оба.
- **R2 (content выдан за production):** честно фиксируем DEFERRED в eval-пакете.
- **R3 (Factory → исполнитель):** execute() вызывает ТОЛЬКО ForgeFacade.run_chain.
- **R4 (SI content-branching):** negative-тест + grep-assert.

---
_Источник: promt 92 §13. Дата: 2026-08-17._
