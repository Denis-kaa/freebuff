# ARCHITECTURE GAP MAP (Artifact G — Phase G Specification)

> **Source of Truth:** repository (Freebuff / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §9 (DOCUMENT ↔ CODE CONSISTENCY), §19-G, §21 (каждый CONFIRMED компонент имеет code evidence; каждый contract — implementation или DESIGN_ONLY).
> **Anchor inheritance:** consumes `@entity` + status from Artifact A `PLATFORM_CODE_MAP_V1.md` (§A.6 status taxonomy: CURRENT / PARTIAL / DESIGN_ONLY / UNVERIFIED / STALE / SUPERSEDED); mirrors CI-variant `FORENSICS_CI_GAP_MAP_V1.md` (G0–G4 for Content Intelligence) but on the **platform level**.
> **REPOSITORY = SOURCE OF TRUTH:** каждый gap подтверждён кодом/файлом/реестром, а не «дизайн-намерением». Anything unresolvable → status=UNVERIFIED.
> **Counterparts required:** Artifact A (25 `@entity` rows), Artifact C (CONTRACT_REGISTRY), Artifact H (CONSISTENCY_REPORT — это gap map в действии), `core_02/missing_registry.py` (register-first lifecycle), §20 `FACTORY_FORGE_ARCHITECTURE_V1.md` (Missing Capabilities).

---

## §G.1 — Gap Classification taxonomy (platform level)

Статус-модель для каждой строки карты. Аналог §9 промта 4 (CONFIRMED / PARTIALLY_CONFIRMED / DOCUMENT_ONLY / CODE_ONLY / CONTRADICTED / STALE / UNKNOWN), нормализованный к status taxonomy артефакта A (§A.6):

| Статус | Смысл | Промт-4 класс | Пример |
|--------|-------|---------------|--------|
| `CURRENT` | Код есть, тесты зелёные, документ актуален | CONFIRMED | `@entity forge.facade` |
| `PARTIAL` | Код есть, но покрытие/док неполны | PARTIALLY_CONFIRMED | `@entity forge.interactive` (runtime-deployed, нет unit-тестов) |
| `DESIGN_ONLY` | Только проектные решения, кода нет | DOCUMENT_ONLY | `@entity scenario.engine` (Phase 2) |
| `UNVERIFIED` | Нет ни кода, ни реестровой записи | UNKNOWN | любой токен без resolution |
| `STALE` | Исторически был код, теперь отсутствует | STALE | символ, удалённый при рефакторинге |
| `SUPERSEDED` | Заменён более новым решением | CONTRADICTED | `@decision ADR_001` → `ADR_007` |

**Ключевой принцип:** gap фиксируется ТОЛЬКО при наличии кодового эвиденса (grep/AST/`Path.exists()`). Анти-галлюцинация: «в документации написано, но кода нет» → DESIGN_ONLY, а не «сломанный CURRENT».

---

## §G.2 — Entity Gap Map (Artifact A ↔ repository, 25 @entity)

> Источник строк: `SEMANTIC_ANCHOR_SPEC_V1.md` §I.6 (25 подтверждённых `@entity`). Статус подтверждён `ls`/`ast`/`tests_09` (2026-08-12).

| `@entity` | Файл (эвиденс) | Статус | Gap (что отсутствует) | Тип gap |
|-----------|----------------|:------:|-----------------------|---------|
| `scenario.registry` | `core_02/scenario_registry.py` | CURRENT | — | — |
| `forge.registry` | `core_02/forge_registry.py` + `data_13/forge_registry.yaml` | CURRENT | — | — |
| `missing.registry` | `core_02/missing_registry.py` + `data_13/missing_registry.yaml` | CURRENT | — | — |
| `orchestrator.blueprint` | `core_02/blueprint_v3.py` | CURRENT | — | — |
| `forge.facade` | `core_02/forge_facade.py` (ForgeFacade, 29 тестов) | CURRENT | — | — |
| `role.validator` | `core_02/forge_facade.py`::RoleArtifactValidator | CURRENT | — | — |
| `forge.pipeline` | `core_02/forge_pipeline.py` | CURRENT | — | — |
| `workspace.core` | `core_02/workspace.py` (Project) | CURRENT | — | — |
| `wizard.lib` | `scripts_01/wizard.py` + `core_02/wizard_lib.py` | CURRENT | — | — |
| `memory.store` | `core_02/memory_store.py` (SQLite) | CURRENT | — | — |
| `knowledge.engine` | `scripts_01/knowledge_engine.py` (FTS5+TF-IDF+SVD) | CURRENT | — | — |
| `graph.index` | `scripts_01/graph_index.py` | CURRENT | — | — |
| `event.bus` | `scripts_01/event_bus.py` + `context_12/events.db` | CURRENT | — | — |
| `remote.sync` | `core_02/remote_sync.py` | CURRENT | — | — |
| `forge.cli` | `scripts_01/forge.py` (CLI) | CURRENT | — | — |
| `forge.api` | `scripts_01/forge_api.py` / `mcp_fastapi.py` (:8765) | CURRENT | — | — |
| `forge.interactive` | `scripts_01/forge_interactive_api.py` | PARTIAL | Нет unit-тестов (runtime-deployed) | Coverage |
| `opportunity.engine` | `scripts_01/opportunity_engine.py` (29 тестов) | CURRENT | — | — |
| `whim.capture` | `scripts_01/whim_capture.py` (39 тестов) | CURRENT | — | — |
| `consistency.check` | `scripts_01/consistency_check.py` (Stage 9) | CURRENT | — | — |
| `drift.check` | `scripts_01/drift_check.py` (link/структура) | CURRENT | — | — |
| `research.web` | `scripts_01/research_web.py` | CURRENT | — | — |
| `lisa.estimator` | `scripts_01/lisa_estimator.py` | CURRENT | — | — |
| `factory.registry` | `core_02/factory_registry.py` (v5.188.2, Missing Cap #1 closed) | CURRENT | — | — |
| `scenario.engine` | — (нет кода) | **DESIGN_ONLY** | Исполнение сценариев-композиторов; Missing Cap #2 `scenario_engine`, status=design_ready | Missing Capability |

**Итог §G.2: 23/25 CURRENT + 1 PARTIAL (`forge.interactive` — runtime-deployed без unit-тестов) + 1 DESIGN_ONLY (`scenario.engine`).** Критичных «забытых» компонентов нет; единственный платформенный gap — Scenario Engine (по-прежнему дизайн, не блокирует существующие цепочки — сценарии работают через `forge chain` и `ScenarioRegistry`).

---

## §G.3 — Contract Gap Map (Artifact C ↔ repository)

> Для каждого контракта из `CONTRACT_REGISTRY_V1.md` — есть ли implementation или DESIGN_ONLY.

| contract_id | Implementation | Статус | Gap |
|-------------|---------------|:------:|-----|
| `forge.execution` | `core_02/forge_facade.py::ForgeFacade.run_chain` | CURRENT | — |
| `scenario.selection` | `core_02/scenario_registry.py::find_role/propose_roles` | CURRENT | — |
| `project.state` | `core_02/workspace.py::Project` | CURRENT | — |
| `role.artifacts` | `core_02/forge_facade.py::RoleArtifactValidator.validate` | CURRENT | — |
| `missing.lifecycle` | `core_02/missing_registry.py::MissingRegistry` | CURRENT | — |
| `event.publish` | `scripts_01/event_bus.py::EventBus.publish` | CURRENT | — |
| (новые CI-контракты) | `INTELLIGENCE_FACTORY_CONTRACT_V1.md` | DESIGN_ONLY | opportunity/whim контракты реализованы (v5.187.7/8); scenario_engine — нет |

**Примечание:** все контракты, перечисленные в CONTRACT_REGISTRY_V1, имеют implementation (CURRENT); новых контрактов-«фантомов» не обнаружено.

---

## §G.4 — Capability Gap Map (по §20 карты v1.1 ↔ MissingRegistry)

> Сверка по `consistency_check.py` check 10 (missing_registry_sync). Полный список статусов — `python -m core_02.missing_registry list`.

| item_id | §20 карты | Реестр | Gap |
|---------|-----------|--------|-----|
| `factory_registry` | IMPLEMENTED (v5.188.2) | implemented | — |
| `scenario_engine` | design готов | design_ready | **Missing Cap #2** (единственный крупный) |
| `decision_registry` | Medium | registered | промт/реализация не написаны |
| `conformance_checker` | Medium | registered | промт/реализация не написаны |
| `model_diagram_autogen` | Low | registered | промт/реализация не написаны |
| `research_web` | ✅ реализовано | implemented | — |
| `lisa_estimator` | ✅ реализовано | implemented | — |
| `opportunity_engine` | ✅ реализовано | implemented | — |
| `whim_capture` | ✅ реализовано | implemented | — |
| `opportunities_yaml` | ✅ реализовано | implemented | — |
| `whims_yaml` | ✅ реализовано | implemented | — |
| `doc_code_verify` | **(отсутствует в §20 — находка H-5)** | prompt_written | **§20 карта не обновлена** (закрыто в рамках этого промта) |
| TODO-трекеры (4) | зарегистрировано | registered | след. шаг — промты/фиксы |

**Итог §G.4:** бэклог register-first полностью синхронизирован с §20 (после добавления строки `doc_code_verify`). Нереализованные элементы — осознанные DESIGN_ONLY (Decision Registry / Conformance Checker / Model Diagram Autogen / Scenario Engine).

---

## §G.5 — Storage / Events / Docs Gap Map

| Слой | Механизм | Статус | Примечание |
|------|----------|:------:|------------|
| STORAGE | `data_13/*.yaml + *.db`, `context_12/` | CURRENT | 10+ YAML/SQLite; `opportunities.yaml`/`whims.yaml` добавлены v5.187.7/8 |
| EVENTS | `event_bus.py` registered_events | CURRENT | MCP `event_*` 11 инструментов |
| DOCS | `docs_10/DOCUMENT_REGISTRY.md` | PARTIAL | 18/181 md-файлов в реестре (находка `PLATFORM_AUDIT_RECOMMENDATIONS_V1`); этот промт добавляет 5 артефактов → реестр пополняется |
| ANCHORS | `doc_code_verify.py` (Artifact J) | CURRENT | Реализован как код + 30 тестов; SPEC (J) создаётся в этом промте |
| NAVIGATION | Artifact F `AGENT_NAVIGATION_MAP_V1.md` | CURRENT | SPEC (K) создаётся в этом промте |
| PLAN | Artifact L `IMPLEMENTATION_PLAN_V1.md` | **(создаётся в этом промте)** | Фазы A–H §20 |

---

## §G.6 — Top gaps (приоритизировано)

| # | Gap | Тип | Приоритет | Действие |
|---|-----|-----|:---------:|----------|
| 1 | `scenario_engine` — единственный платформенный DESIGN_ONLY | Missing Cap #2 | 🟡 Medium | промт → реализация (после материальных кузен) |
| 2 | `doc_code_verify` не в §20 карте | Registry drift | 🟢 Low | **закрыто здесь** (строка #16) |
| 3 | Тест-счётчики 2742 → 2823 (CHANGELOG + CODE_QUALITY_STANDARD) | Doc drift | 🟢 Low | **закрыто здесь** |
| 4 | Naming: `promt81.md` + дубль-суффикс `prompts_11` | Naming drift | 🟢 Low | ✅ **ЗАКРЫТО (v5.189.3):** `promt81.md` → `081_19_model_dispatcher.md`; `prompts_11/` (сирота) удалён, файл → `pompts_11/082_19_doc_code_sync.md`; consistency_check naming 0 issues |
| 5 | Decision Registry / Conformance Checker / Model Diagram Autogen | registered (без промтов) | 🟢 Low | бэклог, по приоритету владельца |

---

*Artifact G closed. Эвиденс: grep/AST/ls по репозиторию 2026-08-12; сверка с Artifact A (§A.6), Artifact C, §20 FACTORY_FORGE_ARCHITECTURE_V1.md, `missing_registry list`. Следующий: Artifact H (DOCUMENTATION_CONSISTENCY_REPORT_V1.md) — реализация этого gap map через consistency_check + doc_code_verify.*
