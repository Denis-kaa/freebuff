# INTELLIGENCE_FACTORY_CONTRACT_V1.md — Intelligence ↔ Factory Architectural Contract

| Поле | Значение |
|------|----------|
| **Документ** | INTELLIGENCE_FACTORY_CONTRACT_V1.md |
| **Статус** | 📋 ARCHITECTURAL CONTRACT — §E reconciled to runtime (2026-08-17, promt 090 Task A); implementation active (opportunity_engine/whim_capture implemented) |
| **Версия** | 1.0 |
| **Дата** | 2026-08-12 |
| **Источник задания** | `projects_17/content_factory/promts/2.md` (MISSION: INTELLIGENCE ↔ FACTORY ARCHITECTURAL CONTRACT) |
| **Метод** | Repository-first: только фактические API (path + symbol), evidence из кода; отчёт Forensics — вторичен, repository приоритетнее |
| **Прецеденты** | FORENSICS_CI_REPORT_V1.md (G0–G4), FORENSICS_CI_GAP_MAP_V1.md, FORENSICS_CI_FOLLOWUP_V1.md, ARB-REV-004 |
| **Главное правило** | MINIMUM NEW CODE + MAXIMUM REUSE (§17). Не создавать второй оркестратор/память/знание/event bus/Forge/Scenario Registry. |

---

## A. REPOSITORY REALITY — что реально существует (подтверждено кодом)

Все пути проверены в repository (2026-08-12). Ни одно название не взято из документации без кода.

| Модуль | Подтверждено кодом | Ключевые символы |
|--------|--------------------|------------------|
| `core_02/workspace.py` | ✅ `Workspace.load/list_projects/get_project/validate` · `Project.load/get_requirements/append_step/get_steps_stats/run_env_doctor/get_agents_md/to_dict` | Workspace = контейнер проектов; Project = объект работы |
| `core_02/workspace_registry.py` | ✅ `WorkspaceRegistry.create_workspace/add_project/list_workspaces/list_projects/find_workspace_for_project/assert_path_privacy` · `Workspace`/`Project` dataclasses · `PrivacyViolationError` | SQLite-реестр workspace↔project (B1-boundary) |
| `core_02/scenario_registry.py` | ✅ `ScenarioRegistry.list_scenarios/get/find_role/all_roles/propose_roles/validate_all` + auto-discovery `runtime_05/scenarios/*.yaml` ($FREEBUFF_SCENARIOS_DIR) | Единственный реестр сценариев (7: не плодить второй) |
| `core_02/forge_facade.py` | ✅ `ForgeFacade.initiate_forge(project, requested_by_role, hooks, skip, project_read_only) -> ForgeFacadeResult` · `run_chain(project, role_ids, ..., project_read_only) -> ChainRun` · `validate_role_artifacts` · `RoleArtifactValidator` · `PIPELINE_CHAIN` (14 ролей) · `ForgeFacadeResult{project_id, requested_by_role, status_before, status_after, overall, stages, initiated_explicitly, project_read_only***REMOVED***` | **Единственный санкционированный мост к Forge (§7.3)** |
| `core_02/forge_pipeline.py` | ✅ `ForgePipeline.stage_forge/check/build/test/deploy/report/run(skip)` · `PipelineRun` · `StageResult` · `_run_cmd` (argv-list, shell=False) | CI-подобный конвейер (по сути сценарий Code Factory) |
| `core_02/forge_registry.py` | ✅ `ForgeRegistry.register_project/get_project_status/record_run/list_projects_by_status/validate_schema` · `STATUSES = (UNFORGED, CHECKING, BUILDING, TESTING, DEPLOYED, FAILED)` | Статус-реестр проектов (B2-boundary) |
| `core_02/memory_store.py` | ✅ `MemoryStore.store_knowledge(kind, content, title, summary, tags, sources, references, lifecycle_stage, status, confidence_score, source_event_id, knowledge_id, superseded_by) -> knowledge_id` · `update_knowledge/get_knowledge/query_by_type/query_all` | SQLite knowledge objects + связи + события обучения |
| `core_02/semantic_layer.py` | ✅ `SemanticLayer.index_knowledge/semantic_search/search_related/find_similar_patterns/remove/reindex_all` | TF-IDF/semantic поиск по knowledge |
| `core_02/learning_loop.py` | ✅ `LearningLoop.capture(situation, title, summary, content, tags, sources, notify_tg)` (analyze→formalize→codify + record_learning_event) · `analyze/formalize/codify/record_feedback` | Уроки CON/CAN/ANTI в память |
| `scripts_01/knowledge_engine.py` | ✅ `KnowledgeEngine.index/search/remove` (FTS5 + TF-IDF + SVD hybrid) | Полнотекстовый поиск |
| `scripts_01/graph_index.py` | ✅ `GraphIndex.add_node/remove_node/get_node/add_edge` · `Edge`/`Node`/`PathResult`/`GraphStats` | Граф знаний |
| `scripts_01/event_bus.py` | ✅ `EventBus.publish(event) -> int` (кол-во доставок) · `subscribe` · `Event`/`Subscription`/`EventLogEntry` · `get_default_event_bus` | Событийная шина |
| `scripts_01/project_pulse.py` | ✅ `ProjectPulse.add_entry/get/list/list_json/clear` · `PulseEntry` | Лента изменений проектов |
| `scripts_01/distributed_agents.py` | ✅ `AgentNode/AgentTask/AgentTaskResult/DistributedWorkflowStep/DistributedWorkflowPlan` (to_dict) | Multi-agent слой (исполнители, НЕ Intelligence) |
| `scripts_01/tool_runtime.py` | ✅ `BaseTool.execute(params, context) -> ToolResult` · `ToolMeta`/`ParamSchema` · `GitTool/SQLiteTool/HTTPTool/FileTool` | Инструменты-исполнители |
| `runtime_05/scenarios/` | ✅ `blueprint_v3.yaml`, `vkusvill_demo.yaml` (id/type/display_name/root/enabled/capabilities) | YAML-сценарии, авто-дискавери |
| `data_13/` | ✅ `forge_registry.yaml`, `missing_registry.yaml`, SQLite db | Реестры-данные |

**Factory в коде НЕ существует** (только дизайн `FACTORY_FORGE_ARCHITECTURE_V1.md` v1.1, G2). `missing_registry.yaml`: `factory_registry` = design_ready, `opportunity_engine` = prompt_written (промт 079_19), `whim_capture` = registered.

---

## B. EXISTING REUSABLE COMPONENTS — что переиспользуем (максимум)

| Компонент | Роль в контракте | Переиспользуем как |
|-----------|------------------|--------------------|
| `ScenarioRegistry` | источник доступных сценариев | SELECT (7: не создавать второй реестр) |
| `ForgeFacade.run_chain` / `initiate_forge` | исполнение | EXECUTE (единственный мост) |
| `RoleArtifactValidator` | валидация артефактов | VALIDATE |
| `MemoryStore.store_knowledge` | накопление | ACCUMULATE (opportunities/artifacts как knowledge objects) |
| `SemanticLayer` / `KnowledgeEngine` | поиск | related knowledge, дедупликация сигналов |
| `GraphIndex` | связи | artifact relationships, opportunity→knowledge |
| `EventBus` | события | event contract (§15) — уже существует |
| `ProjectPulse` | наблюдение за проектом | источник сигналов (observation layer) |
| `ForgeRegistry` | статусы проектов | project status (B2) |
| `WorkspaceRegistry` | workspace↔project | project_id resolution |
| `LearningLoop.capture` | уроки | lessons после execution |
| `ToolRuntime` | инструменты | tool execution (research_web/lisa_estimator и т.п.) |

---

## C. INTELLIGENCE BOUNDARY — что относится к Intelligence, чего он НЕ делает

**Intelligence = decision/composition layer** над существующим стеком. НЕ исполняет, НЕ хранит, НЕ ищет сам — решает.

| Intelligence ДЕЛАЕТ (отвечает WHAT/WHY) | Intelligence НЕ делает |
|-----------------------------------------|------------------------|
| Signal → Observation → Hypothesis → Opportunity (§6) | ❌ не является Agent (не исполняет операции) |
| Выбор/рекомендация Scenario (§7) | ❌ не является Factory (не производит) |
| Оценка: стоит ли делать, когда, что приоритетно | ❌ не является Scenario (не композирует сам — выбирает готовый) |
| Переоценка состояния проекта после артефакта | ❌ не является Forge (не исполняет forge) |
| DECISION-provenance (decision/actor/timestamp/context) | ❌ не является Chat |
| DEFERRED ≠ DELETED семантика | ❌ не является Memory (не хранит — использует MemoryStore) |
| | ❌ не создаёт второй Scenario Registry / второй Forge / вторую память |

**Место Intelligence:** над ScenarioRegistry/ForgeFacade/Memory — вызывающий слой, единственная новая «голова» (§I форензики: opportunity_engine + whim_capture).

---

## D. CONTRACT MAP — Boundary | Existing API | Input | Output | Owner | Gap

| Boundary | Existing API | Input | Output | Owner | Gap |
|----------|-------------|-------|--------|-------|-----|
| **Signal → Observation** | `ProjectPulse.add_entry` / `EventBus.publish` | сигнал (whim/pulse/event) | PulseEntry / event | ProjectPulse | НЕТ (G0) — whim_capture = лёгкий вход |
| **Observation → Opportunity** | `MemoryStore.store_knowledge(kind=...)` + `SemanticLayer.find_similar_patterns` | observation | knowledge_id (opportunity как KO) | MemoryStore | **ДА** — нет выделенной opportunity-модели (lifecycle ACTIVE/DEFERRED/…) → **opportunity_engine** (G3, Missing #8) |
| **Intelligence → ScenarioRegistry** | `ScenarioRegistry.list_scenarios` / `propose_roles` | opportunity text | список сценариев + score | ScenarioRegistry | НЕТ (G0) |
| **Opportunity → Scenario (SELECT)** | `ScenarioRegistry.get(scenario_id)` | выбранный scenario_id | Scenario | ScenarioRegistry | НЕТ — SELECT на G0; `opportunity_engine` добавляет `selected scenario` в opportunity |
| **Scenario → Factory** | (Factory нет в коде) | — | — | Factory (G2) | **ДА** — FactoryRegistry (Missing #1, design_ready) — декларативный registry-level слой |
| **Scenario/Factory → ForgeFacade** | `ForgeFacade.run_chain(project, role_ids) -> ChainRun` / `initiate_forge(...) -> ForgeFacadeResult` | Project + role_ids | ChainRun / ForgeFacadeResult | ForgeFacade | НЕТ (G0) — единственный мост |
| **Forge → Artifact** | `RoleArtifactValidator` + `ForgeRegistry.record_run` | ChainRun | ValidationResult + артефакты на диске | ForgeFacade | НЕТ (G0) |
| **Artifact → Intelligence** | `MemoryStore.store_knowledge(kind=...)` + `LearningLoop.capture` | artifact | knowledge_id + lesson | MemoryStore | НЕТ (G0) — ACCUMULATE |
| **Project State** | `MemoryStore` + `GraphIndex` + `ForgeRegistry` | opportunity/artifact | KO + edges + статусы | MemoryStore | **ДА (частично)** — opportunity state = новый kind KO; ничего нового системного |

---

## E. OPPORTUNITY CONTRACT — минимальная схема

Наследует существующую модель **knowledge object** (`MemoryStore.store_knowledge` поля) — НЕ новый datastore.

**Решение по персистентности (устраняет двусмысленность §E↔FORENSICS_CI_FOLLOWUP):**
- **lifecycle-статус** (ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED) → `data_13/opportunities.yaml` (машиночитаемый, как в промте 079_19/плане FOLLOWUP);
- **knowledge-накопление** (контент, связи, related_knowledge) → `MemoryStore` KO kind=`opportunity` (поиск через SemanticLayer).

> **RECONCILED (2026-08-17, promt 090 Task A):** canonical schema = **runtime implementation** (24 поля, `scripts_01/opportunity_engine.py::Opportunity`). Design-поля ниже маппятся на runtime через таблицу §E.1. Drift #5 (CONTRACT_REGISTRY §C.6) CLOSED.

```python
Opportunity (kind="opportunity", lifecycle в data_13/opportunities.yaml + контент как MemoryStore KO):
  id                : str          # opp-<hex> (uuid4 hex[:10***REMOVED***) — machine-readable id
  project_id        : str          # из WorkspaceRegistry
  title             : str          # заголовок (исходный сигнал/гипотеза свернуты сюда)
  description       : str          # расширенное описание
  source            : str          # whim | project_pulse | event_bus | knowledge | hand
  status            : str          # ACTIVE | DEFERRED | READY | REACTIVATED | COMPLETED | FAILED  (DEFERRED ≠ DELETED)
  priority          : int          # 1-10 (default 5)
  created_at        : str          # ISO
  updated_at        : str          # ISO
  provenance        : dict[str, Any***REMOVED***  # цепочка Signal→Observation→Hypothesis (K) + rank-поля (promt 086) + DISCOVER/ACCUMULATE ключи
  scenario          : dict | None  # выбранный scenario (scenario_id внутри)
  roles             : list[dict***REMOVED***   # выбранные роли
  artifacts         : list[dict***REMOVED***   # артефакты после run_chain (resulting_artifact)
  source_path       : str          # путь источника (whims.yaml / pulse.db / events.db / context.db)
  evidence_path     : str          # путь evidence
  deferred_at       : str | None   # ISO
  deferred_reason   : str | None
  previous_status   : str | None   # audit-trail (advance фиксирует до перехода)
  reactivated_at    : str | None   # ISO
  completed_at      : str | None   # ISO
  failed_at         : str | None   # ISO
  failure_reason    : str | None
  related_decisions : list[str***REMOVED***    # id KO kind=`decision` (USER DECLINED NOW ≠ REJECTED FOREVER, §14)
  related_whims     : list[str***REMOVED***    # id связанных whims (dedup по whim)
```

### §E.1 — Design → Runtime mapping (v1.0 → canonical)

| Design (§E v1.0) | Runtime (canonical 24f) | Mapping |
|------------------|--------------------------|---------|
| `id` | `id` | same (knowledge_id → opp-<hex>)
| `project_id` | `project_id` | same |
| `source` | `source` | same (расширен `hand`) |
| `signal` | `title` | исходный сигнал становится заголовком |
| `hypothesis` | `title`/`description` | гипотеза свёрнута в title/description |
| `description` | `description` | same |
| `rationale` | `provenance` | rationale живёт в provenance (DISCOVER-ключи) |
| `status` | `status` | same (+ `FAILED` retry-allowed) |
| `provenance` | `provenance` | same + rank-поля (`rank_score`/`rank_factors`, promt 086) + ACCUMULATE-ключи |
| `created_at` | `created_at` | same |
| `updated_at` | `updated_at` | same |
| `related_knowledge` | `provenance.memory_knowledge_id` + `related_whims` | знания через ACCUMULATE-ключи; whim-связи отдельным полем |
| `selected_scenario` | `scenario` | str → dict (scenario_id внутри) |
| `resulting_artifact` | `artifacts` | str → list[dict***REMOVED*** |
| `related_decisions` | `related_decisions` | same |
| — (нет в дизайне) | `priority`, `roles`, `source_path`, `evidence_path`, `deferred_at`, `deferred_reason`, `previous_status`, `reactivated_at`, `completed_at`, `failed_at`, `failure_reason` | lifecycle audit-поля + priority (промт 086) |

**Минимальность (§5):** поля добавлены только с доказанной необходимостью (lifecycle требует status/provenance; связность требует related_knowledge/selected_scenario/resulting_artifact; §14 требует decision-provenance → `related_decisions`). Без `owner`, `assignee`, `due_date`, `tags[***REMOVED***` (есть через KO tags), `priority` (оценка Intelligence, не поле хранения).

**Rank-поля (promt 086 Advanced Opportunity Ranking):** при `rank_candidates()` в `provenance` дописываются два traceability-поля:
- `rank_score` — композитный score ∈ [0,1***REMOVED*** = `confidence·0.5 + source·0.2 + recency·0.2 + priority·0.1`, где `source` = надёжность источника (`SOURCE_WEIGHTS`: whim/hand=1.0, knowledge=0.8, project_pulse=0.6, event_bus=0.5); веса `RANK_WEIGHTS`, сумма = 1.0;
- `rank_factors` — breakdown: `{confidence, source, source_weight, recency, priority_norm***REMOVED***` (каждая компонента до ранжирования).

Базовые ключи `provenance` (DISCOVER, §8): `source`, `source_id`, `reason`, `evidence`, `confidence`, `stub`. ACCUMULATE-ключи (§10): `memory_knowledge_id`, `learning_event_id`, `accumulate`, `accumulate_error` (partial failure без маскировки, §17).

**User decision provenance (§14):** решения пользователя хранятся как KO kind=`decision` (поля `decision`/`actor`/`timestamp`/`context`/`reason` — reason опциональна, §14 не требует обязательного объяснения) и связываются с opportunity через `related_decisions`; `USER DECLINED NOW` ≠ `USER REJECTED FOREVER` — статус остаётся DEFERRED (переоцениваемая), не REJECTED/удаление.

---

## F. SCENARIO CONTRACT — Opportunity → Scenario

- **Opportunity ≠ Scenario.** Одна Opportunity → несколько возможных сценариев (пример §7: книга → 3 пути).
- **Источник сценариев — `ScenarioRegistry`** (существующий, G0). НЕ создавать второй реестр внутри Intelligence.
- Контракт выбора:
  ```
  opportunity.text → ScenarioRegistry.list_scenarios() → кандидаты
                   → Intelligence (score/ранжирование) → рекомендованный scenario_id
                   → Opportunity.selected_scenario = scenario_id  (после подтверждения)
  ```
- **DESIRED CONTRACT:** `opportunity_engine.propose(opportunity_id) -> list[ScenarioCandidate{scenario_id, score, reason***REMOVED******REMOVED***` через `ScenarioRegistry.list_scenarios` + `propose_roles` (fuzzy match существует).
- **CURRENT IMPLEMENTATION:** ScenarioRegistry есть (list_scenarios/propose_roles — G0). Процесс «opportunity→выбор» — новый код в `opportunity_engine` (промт 079_19), но без дублирования реестра.

---

## G. FACTORY CONTRACT — минимальный, без реализации

Forensics: **Factory = G2**. В коде Factory нет. НЕ создавать production engine (§12/§17).

**Factory = декларативный/registry-level слой** над существующими capabilities:

```python
FactoryCapability:
  capability_id : str            # токен из закрытого словаря (ANTI-6b)
  factory       : str            # Research | Architecture | Code | Content
  forge         : str | None     # Forge (если есть) — иначе capability-шаг
  input         : list[str***REMOVED***      # типы входов (artifact types)
  output        : list[str***REMOVED***      # типы выходов
  execution     : str            # механизм: forge_facade.run_chain | tool | engine
  validation    : str            # RoleArtifactValidator | drift_check | ...
  status        : str            # design_ready | implemented
  provenance    : str            # источник (паспорт/промт)
```

- Реализация = **FactoryRegistry** (Missing #1, `design_ready`, промт 078_19 на диске) — машиночитаемые паспорта по образцу `ScenarioRegistry` + YAML `runtime_05/factories/`.
- **DESIRED CONTRACT:** FactoryRegistry.resolve(capability_id) → FactoryCapability.
- **CURRENT IMPLEMENTATION:** отсутствует (G2). В контракте — только декларативный слой, НЕ новый исполнитель.

---

## H. EXECUTION CONTRACT — Scenario → Factory → ForgeFacade → Artifact

Единственный санкционированный путь (подтверждён кодом `core_02/forge_facade.py` + §7.3 карты):

```
Scenario → (capability ref) → ForgeFacade.run_chain(project, role_ids=PIPELINE_CHAIN, project_read_only=True) -> ChainRun
                              ForgeFacade.initiate_forge(project, requested_by_role) -> ForgeFacadeResult
```

- **Vertical Slice нужен минимальный вызов:** `ForgeFacade.run_chain(project, role_ids)` — цепочка 14 ролей, возвращает `ChainRun` (chain + overall). 
- `ForgeFacadeResult` переиспользуем для явного запуска (initiate_forge).
- `RoleArtifactValidator` — уже в run_chain (compose_artifact_check=True default).
- **НЕ создавать новый Result Object** — ChainRun/ForgeFacadeResult/StageResult существуют.

---

## I. PROJECT STATE CONTRACT — состояние Intelligence

**НЕ создавать новую parallel memory system (§11/§17).** Использовать существующее:

| Что храним | Где (existing) | kind/форма |
|------------|----------------|------------|
| active opportunities | `data_13/opportunities.yaml` (lifecycle) + `MemoryStore` (контент) | статус ACTIVE в YAML + KO kind=`opportunity` (поиск/контент) |
| deferred opportunities | `data_13/opportunities.yaml` (lifecycle) + `MemoryStore` | статус DEFERRED в YAML (**≠ DELETED**, остаётся в состоянии) + KO контент |
| completed opportunities | `data_13/opportunities.yaml` (lifecycle) + `MemoryStore` | статус COMPLETED в YAML + KO + resulting_artifact |
| signals / whims | `MemoryStore` + `data_13/whims.yaml` | KO kind=`whim` / YAML (лёгкий вход) |
| observations | `MemoryStore` | KO kind=`observation` (source_event_id→event) |
| decisions | `MemoryStore` + ADR | KO kind=`decision` + `decisions/DECISIONS.md` (project-local ADR по PROJECT_RULES) |
| scenario history | `ForgeRegistry.record_run` + EventBus | история execution в event_log |
| artifact relationships | `GraphIndex` | Edge(artifact→opportunity→scenario→knowledge) |

---

## J. EVENT CONTRACT — только необходимые события

`EventBus` существует (`publish(event) -> int`). Добавляем только то, что нужно Vertical Slice (§15):

| Событие | Нужно? | Обоснование |
|---------|:------:|-------------|
| `opportunity.created` | ✅ | создание opportunity из signal |
| `opportunity.updated` | ✅ | смена статуса/полей |
| `opportunity.deferred` | ✅ | DEFERRED-переход (наблюдаемость) |
| `opportunity.reactivated` | ✅ | REACTIVATED-переход |
| `scenario.selected` | ✅ | фиксация выбора (provenance) |
| `execution.started` | ✅ | до run_chain |
| `execution.completed` | ✅ | после run_chain ok |
| `execution.failed` | ✅ | после run_chain failed |
| `artifact.created` | ✅ | артефакт готов |
| `artifact.validated` | ✅ | прошёл RoleArtifactValidator |
| `whim.created` | ✅ | лёгкий вход зафиксирован (не превращается в задачу автоматически) |

**Не добавляем** события «на будущее» (scheduler.ticked, model.routed, knowledge.synced и т.п.) — нет потребности Vertical Slice.

---

## K. PROVENANCE CONTRACT — происхождение

Полная цепочка сохраняется без новой системы — через поля существующих KO + события EventBus:

```
Signal → Observation → Hypothesis → Opportunity → Decision → Scenario → Execution → Artifact
```
| Шаг | Provenance (existing) |
|-----|------------------------|
| Signal | `source_event_id` / source (whim | project_pulse | event_bus) |
| Observation | KO kind=`observation`, sources=[{signal***REMOVED******REMOVED*** |
| Hypothesis | KO kind=`hypothesis`, sources=[{observation***REMOVED******REMOVED*** |
| Opportunity | KO kind=`opportunity`, provenance-цепочка в `sources` (list[dict***REMOVED***) |
| Decision | `decision` KO + ADR (project-local, PROJECT_RULES §3.1); actor/timestamp/context/reason — поля |
| Scenario | `scenario.selected` event + `Opportunity.selected_scenario` |
| Execution | `execution.*` события + `ForgeRegistry.record_run` |
| Artifact | `artifact.created` event + `resulting_artifact` + `GraphIndex` edge |

`MemoryStore.store_knowledge(sources=[...***REMOVED***, references=[...***REMOVED***, source_event_id=...)` — уже поддерживает цепочку.

---

## L. MINIMUM NEW COMPONENTS — только то, чего реально нет

| name | responsibility | reason | integration point | est. scope |
|------|----------------|--------|-------------------|-----------|
| **`whim_capture`** (module, G3) | лёгкий вход мысли (save/delete/merge/defer/send-to-Intelligence), `DEFERRED ≠ DELETED`, НЕ авто-задача | нет в коде (grep=0) | `data_13/whims.yaml` + EventBus (`whim.created`) → opportunity_engine | ~150–200 LOC + тесты |
| **`opportunity_engine`** (engine, G3) | DISCOVER→LIFECYCLE→PROPOSE→SELECT→EXECUTE→VALIDATE→ACCUMULATE; единственная «голова» CI | нет в коде (grep=0) | ScenarioRegistry (SELECT) + ForgeFacade.run_chain (EXECUTE) + MemoryStore (ACCUMULATE) + EventBus | ~300–400 LOC + тесты (промт 079_19) |
| **`factory_registry`** (registry, G2) | машиночитаемые паспорта Factory/Forge (declarative, НЕ production engine) | Factory отсутствует в коде (G2) | YAML `runtime_05/factories/` + ScenarioRegistry-паттерн | ~200–300 LOC + тесты (промт 078_19) |
| **`opportunities` persistence** | lifecycle-состояния opportunities | нет | `data_13/opportunities.yaml` (или kind KO) | в составе opportunity_engine |

**НЕ создаём:** новый orchestration framework · новую memory/knowledge/event систему · новый Forge · новый Scenario Registry · новый Workspace abstraction · LangGraph · новые domain entities сверх минимума (§17 gate).

---

## M. VERTICAL SLICE PLAN — Whim → Opportunity → Scenario → Forge → Artifact → Memory

Минимальный путь (совместим с §J форензики и промтом 079_19):

| Шаг | Компонент | Что происходит | Existing/Gap |
|-----|-----------|----------------|--------------|
| 1 | `whim_capture` | зафиксировали мысль → `whim.created` | **NEW (G3)** |
| 2 | `opportunity_engine.discover` | whim/сигнал → observation → hypothesis → opportunity (kind KO) | **NEW (G3)** |
| 3 | `opportunity_engine.propose` | `ScenarioRegistry.list_scenarios` + `propose_roles` → кандидаты | G0 + NEW резолвер |
| 4 | `opportunity_engine.select` | `selected_scenario = scenario_id` + `scenario.selected` event | G0 + NEW поле |
| 5 | `opportunity_engine.execute` | `ForgeFacade.run_chain(project, role_ids, project_read_only=True)` | **G0 (мост §7.3)** |
| 6 | `validate` | `RoleArtifactValidator` (внутри run_chain) → `artifact.validated` | G0 |
| 7 | `accumulate` | `MemoryStore.store_knowledge` (artifact) + `LearningLoop.capture` + GraphIndex edge | G0 |
| 8 | feedback | `execution.completed` event → Intelligence переоценивает → opportunity COMPLETED | G0 + NEW статус |

**Gaps по шагам:** шаги 1–2 (whim_capture, opportunity_engine) — единственные новые; 3–4 — тонкая обёртка над G0; 5–8 — чистый G0.

---

## N. IMPLEMENTATION BOUNDARY — что сейчас, что потом

**Сейчас (Фаза 1, по FORENSICS_CI_FOLLOWUP):**
- ✅ `opportunity_engine` (промт 079_19 — prompt_written) — ядро Vertical Slice;
- ✅ `whim_capture` (промт 080_19 — написать) — лёгкий вход;
- ✅ SELECT через существующий ScenarioRegistry (без Factory);
- ✅ EXECUTE через ForgeFacade.run_chain (G0, без FactoryRegistry);
- ✅ память через MemoryStore/SemanticLayer/GraphIndex/EventBus (без новых систем).

**Следующий этап:**
- ⏸ `factory_registry` (Missing #1, design_ready) — декларативный Factory-слой (паспорта кузен);
- ⏸ `scenario_engine` (Missing #2, design_ready) — оркестратор, заменит прямой вызов ScenarioRegistry (за интерфейсом `select_scenario()`);
- ⏸ полноценная Intelligence-оценка (LLM-синтез hypothesis/рационала — v1 детерминированные эвристики).

---

## O. RISKS — только реальные, подтверждённые repository

| Risk | Evidence | Mitigation |
|------|----------|------------|
| R1: закрытый словарь — токены opportunity/whim вне `KNOWN_CAPABILITIES` | ANTI-6b/CON-8: silent fallback на qwen2.5:1.5b при drift | `opportunity_engine` — Engine (kind: engine), НЕ в KNOWN_CAPABILITIES; drift-тест `test_known_capabilities_subset_of_actual_catalog` остаётся зелёным |
| R2: дублирование реестра сценариев | §7 запрещает второй Scenario Registry | SELECT только через существующий `ScenarioRegistry` |
| R3: второй исполнительный механизм | §9/§17: ForgeFacade — единственный мост | EXECUTE только через `ForgeFacade.run_chain`/`initiate_forge` |
| R4: Factory выдан за существующий production-код | Forensics: Factory=G2, в коде нет | `factory_registry` — только декларативный registry-level (промт 078_19) |
| R5: project state размазан по нескольким системам | MemoryStore/SemanticLayer/GraphIndex/ForgeRegistry | единый kind-контракт (opportunity как KO) + EventBus для наблюдаемости |
| R6: DEFERRED семантика потеряна | `DEFERRED ≠ DELETED` | lifecycle-машина в opportunity_engine, статусы персистентны (YAML/KO) |
| R7: 14-ролевой run_chain дорогой (реальный прогон) | FORGE_CHAIN_RUNBOOK: vkusvill 7.49s / interior 14.83s | `--dry-run` + project_read_only=True + сегментированные role_ids |

---

## P. FINAL ARCHITECTURE

```
PROJECT
   │
   ├── SIGNALS / WHIMS (whim_capture, G3)  ── ProjectPulse / EventBus / data_13/whims.yaml
   │
   ▼
INTELLIGENCE  (opportunity_engine, G3 — decision/composition layer)
   │   WHAT / WHY → Observation → Hypothesis → Opportunity
   ▼
OPPORTUNITY  (kind=opportunity KO, lifecycle ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED)
   │   DEFERRED ≠ DELETED
   ▼
SCENARIO  (ScenarioRegistry — существующий, G0; НЕ дублируется)
   │   SELECT: list_scenarios + propose_roles → recommended scenario_id
   ▼
FACTORY  (factory_registry, G2 — ДЕКЛАРАТИВНЫЙ registry-level слой, НЕ production engine)
   │
   ▼
FORGE FACADE  (ForgeFacade.run_chain / initiate_forge — ЕДИНСТВЕННЫЙ мост, G0)
   ▼
ARTIFACT
   ├── VALIDATION  (RoleArtifactValidator, G0)
   ├── MEMORY      (MemoryStore.store_knowledge, G0)
   └── KNOWLEDGE   (SemanticLayer / KnowledgeEngine / GraphIndex, G0)
           │
           └──────→ INTELLIGENCE  (переоценка: execution.completed → COMPLETED / next opportunity)
```

**Финал (гейт §20):** все 15 пунктов пройдены — repository исследован (evidence path+symbol выше), существующие компоненты не дублируются (переиспользованы ScenarioRegistry/ForgeFacade/MemoryStore/EventBus/SemanticLayer/GraphIndex), Factory не выдана за production-код (G2, декларативная), Intelligence ≠ Agent/Scenario/Factory/Forge/Chat/Memory, DEFERRED ≠ DELETED, Whim ≠ Opportunity, Opportunity допускает несколько сценариев, Forge вызывается только через ForgeFacade, Project State на существующей инфраструктуре, контракт совместим с First Vertical Slice (M), новые сущности минимальны (3: whim_capture, opportunity_engine, factory_registry).

> **Repository verified. Intelligence ↔ Factory contract defined. Implementation not started.**
