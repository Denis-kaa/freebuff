# CONTRACT_GRAPH_V1.md — Фактический contract graph USER→WORKSPACE→PROJECT→TASK→SCENARIO→FACTORY→FORGE→ARTIFACT

> **Статус:** ANALYTICAL (forensic-only, промт 108 §1 — код не изменялся).
> **Дата:** 2026-08-22
> **Основание:** промт 108 §14 (Contract Graph) — статусы CONFIRMED / PARTIAL / IMPLICIT / MISSING / CONFLICTING.
> **Метод:** каждый переход — FROM/TO/CONTRACT/INPUT/OUTPUT/IMPLEMENTATION/EVIDENCE/STATUS (промт 108 §14).

---

## 0. Модель для проверки (промт 108 §14)

```
USER → WORKSPACE → PROJECT → TASK → SCENARIO → FACTORY → FORGE → AGENT/ROLE/TOOL → ARTIFACT → MEMORY/KNOWLEDGE
```

---

## 1. Таблица переходов

### G1. USER → WORKSPACE

| Поле | Значение |
|------|----------|
| FROM / TO | User → Workspace |
| CONTRACT | Пользователь входит в среду через один из входов (CLI / TG / MCP / HTTP) |
| INPUT | пользовательский запрос / команда / сообщение |
| OUTPUT | workspace-контекст (root, проекты, сессии) |
| IMPLEMENTATION | `scripts_01/mcp_server.py` (workspace_root), `scripts_01/telegram_bot.py`, `scripts_01/forge_api.py`, `freebuff_cli.py`, `scripts_01/mcp_fastapi.py` |
| EVIDENCE | `mcp_server.py:236-237` `__init__(workspace_root)` → `self.workspace = Path(workspace_root)`; `telegram_bot.py:57` импорт `WorkspaceRegistry`; `forge.py:62` импорт `WorkspaceRegistry` |
| STATUS | **CONFIRMED** (множественные реальные входы) |

### G2. WORKSPACE → PROJECT

| Поле | Значение |
|------|----------|
| FROM / TO | Workspace → Project |
| CONTRACT | Workspace перечисляет/резолвит проекты |
| INPUT | workspace root / имя проекта |
| OUTPUT | объект Project |
| IMPLEMENTATION | `core_02/workspace.py::Workspace.load/list_projects/get_project`; `core_02/workspace_registry.py::WorkspaceRegistry` (SQLite mapping) |
| EVIDENCE | `workspace.py:331 load`, `:365 list_projects`, `:368 get_project`, `:126 class Project`; `workspace_registry.py:93 class Project`; `telegram_bot.py:749` (регистрация проекта в SQLite) |
| STATUS | **PARTIAL** — ⚠️ **ДВЕ МОДЕЛИ Project**: `workspace.py:126` (файловый, YAML-конфиг) и `workspace_registry.py:93` (SQLite mapping). ADR-017 зафиксировал: SQLite = mapping/privacy, YAML = конфиг, sync-контракт. Дублирование осознанное, но контракт синхронизации двух моделей в коде не автоматизирован (проверено только в ADR). |

### G3. PROJECT → TASK

| Поле | Значение |
|------|----------|
| FROM / TO | Project → Task |
| CONTRACT | Задачи привязаны к проекту (FK) |
| INPUT | project_id |
| OUTPUT | задача (title/description/type/status) |
| IMPLEMENTATION | `scripts_01/task_manager.py::create_task/get_tasks` |
| EVIDENCE | `task_manager.py:122` `FOREIGN KEY (project_id) REFERENCES projects(name)`; `:161 def create_task`; `:267 def get_tasks` |
| STATUS | **CONFIRMED** (SQLite FK-контракт) |
| NOTE | Параллельный механизм: `scripts_01/orchestrator.py` (FSM/DAG) — второй task-контракт (baseline §2 Task ×2). |

### G4. TASK → SCENARIO

| Поле | Значение |
|------|----------|
| FROM / TO | Task → Scenario |
| CONTRACT | Задача/идея → подходящий сценарий (роли) |
| INPUT | текст (title+description) |
| OUTPUT | кандидаты сценариев / роли (proposals) |
| IMPLEMENTATION | `core_02/scenario_registry.py::ScenarioRegistry.propose_roles/find_role`; `scripts_01/opportunity_engine.py` (PROPOSE стадия); `scripts_01/scenario_intelligence.py` |
| EVIDENCE | `opportunity_engine.py:823` `proposals = registry.propose_roles(opp.title + " " + opp.description, top_n=3)`; `scenario_registry.py:202 def propose_roles`; `scenario_intelligence.py:339-341` (ScenarioRegistry as catalog, NO second registry) |
| STATUS | **PARTIAL** — реализовано через **Opportunity** (не Task): `opportunity_engine` предлагает роли по `opp.title+description`. Прямой мост Task(task_manager) → Scenario **отсутствует** (нет вызова ScenarioRegistry из task_manager.py). |
| NOTE | **Opportunity ≠ Task** (baseline: эфемерная Opportunity vs долгоживущий Task). В коде Opportunity несёт `roles` + lifecycle (ACTIVE/READY/DEFERRED/COMPLETED/FAILED) — это отдельная сущность, «задача-намерение», не task_manager-задача. |

### G5. SCENARIO → FACTORY

| Поле | Значение |
|------|----------|
| FROM / TO | Scenario → Factory |
| CONTRACT | Выбранная capability → подходящая (factory, forge) пара |
| INPUT | capability-токен (closed set) |
| OUTPUT | (FactoryPassport, ForgePassport) |
| IMPLEMENTATION | `core_02/factory_registry.py::FactoryRegistry.select_forge`; `core_02/factory_base.py::resolve`; `scripts_01/opportunity_engine.py::_select_factory_forge`; `scripts_01/scenario_intelligence.py` |
| EVIDENCE | `factory_registry.py:272 def select_forge`; `opportunity_engine.py:736` `pair = factory_registry.select_forge(capability)`; `factory_base.py:283` `pair = registry.select_forge(capability)`; `scenario_intelligence.py:286` (reuses ScenarioRegistry + FactoryRegistry) |
| STATUS | **CONFIRMED** (Path B, двусторонняя связь: сценарий-каталог → capability → фабрика) |

### G6. FACTORY → FORGE

| Поле | Значение |
|------|----------|
| FROM / TO | Factory → Forge |
| CONTRACT | Единственная санкционированная точка исполнения: `ForgeFacade.run_chain` (ADR-018 §3, §7.3) |
| INPUT | Project + role_ids (единственный управляющий вход) |
| OUTPUT | ChainRun (overall + validation_summary) |
| IMPLEMENTATION | `core_02/forge_facade.py::ForgeFacade.run_chain`; `core_02/factory_base.py::execute`; `scripts_01/opportunity_engine.py::execute`; `scripts_01/forge.py::cmd_chain` |
| EVIDENCE | `factory_base.py:368` `run = facade.run_chain(project, role_ids=request.role_ids, project_read_only=True)`; `opportunity_engine.py:949` `result = facade.run_chain(project, role_ids=role_ids)`; `scripts_01/forge.py:490` `run = facade.run_chain(`; `forge_facade.py:7` «ForgePipeline инстанцируется ТОЛЬКО здесь» |
| STATUS | **CONFIRMED** (мост сшит в 3 точках; forge_id адвизорный, исполнение по role_ids — ADR-018) |

### G7. FORGE → AGENT/ROLE/TOOL

| Поле | Значение |
|------|----------|
| FROM / TO | Forge → Agent/Role/Tool |
| CONTRACT | Роль исполняется либо RoleExecutor (ADR-016), либо полным циклом ForgePipeline (HEAVY) |
| INPUT | role_id, project |
| OUTPUT | созданные/проверенные артефакты |
| IMPLEMENTATION | `core_02/role_executor.py::RoleExecutorRegistry/BaseRoleExecutor/LlmRoleExecutor/LisaExecutor`; `core_02/forge_facade.py::run_chain` (light_mode="generate") |
| EVIDENCE | `role_executor.py:49 class BaseRoleExecutor`, `:61 def execute`, `:69 class RoleExecutorRegistry`; `forge_facade.py:567-570` (light_mode generate → `executor_registry.get(rid)`), `:679` `created = executor.execute(project, role_id)` |
| STATUS | **CONFIRMED** (ADR-016) |
| NOTE | Agent-как-отдельная-сущность: **IMPLICIT** — единого проектного Agent-класса нет; роли исполняются `BaseRoleExecutor`-ами (stateless) либо pipeline-ролями. См. baseline §3 «AGENT DOCUMENTED ONLY» + ADR-019 (Proposed). |

### G8. FORGE → ARTIFACT

| Поле | Значение |
|------|----------|
| FROM / TO | Forge → Artifact |
| CONTRACT | Forge производит артефакты в проекте (`projects_17/<id>/forge/`), Opportunity фиксирует raw-результат |
| INPUT | ChainRun / созданные файлы |
| OUTPUT | файлы-артефакты (RUNNABLE.md, CHECKLIST.md, src/…) + `opp.artifacts` (dict) |
| IMPLEMENTATION | `core_02/forge_pipeline.py::_ensure_artifacts/_missing_artifacts`; `core_02/factory_base.py::normalize_output`; `scripts_01/opportunity_engine.py::execute` (artifacts.append) |
| EVIDENCE | `forge_pipeline.py:259 _missing_artifacts`, `:267 _ensure_artifacts`, `:271-280` (write RUNNABLE/CHECKLIST); `factory_base.py:316` `"target": f"projects_17/{...***REMOVED***/forge/"`; `core_02/artifact.py`; `factory_base.py::normalize_output` |
| STATUS | **CONFIRMED** — `Artifact` канонизирует файл/dict/ChainRun; `to_dict()` сохраняет legacy-ключи, `to_chain_run_dict()` сохраняет полный ChainRun metadata, `resolve_files()` проверяет файловую проекцию. |

### G9. ARTIFACT → MEMORY/KNOWLEDGE

| Поле | Значение |
|------|----------|
| FROM / TO | Artifact → Memory/Knowledge |
| CONTRACT | Результат аккумулируется в Memory (kind=candidate) + LearningLoop (GAP-2, promt 085 §9) |
| INPUT | opp (с artifacts), run |
| OUTPUT | memory-запись (knowledge_id), learning_event_id, confidence, outcome |
| IMPLEMENTATION | `scripts_01/opportunity_engine.py::accumulate/_accumulate_best_effort`; `core_02/memory_store.py::MemoryStore`; `core_02/learning_loop.py` |
| EVIDENCE | `opportunity_engine.py:1000 def accumulate`, `:1078 _accumulate_best_effort`; вызовы на `:935/:956/:987/:995` (все исходы execute); `memory_store.py:92 class MemoryStore` |
| STATUS | **CONFIRMED** (сквозная связь Artifact→Memory→Learning на всех исходах) |
| NOTE | Knowledge/Graph — **PARTIAL**: `scripts_01/knowledge_engine.py` (FTS5+TF-IDF) и `scripts_01/graph_index.py` (графовая память) — отдельные механизмы; единого source-of-truth нет (baseline §2 Memory×4). |

---

## 2. Сводная диаграмма

```
USER ──CONFIRMED──▶ WORKSPACE ──PARTIAL──▶ PROJECT ──CONFIRMED──▶ TASK
                                            (Project ×2:                  │
                                             workspace.py vs              ▼
                                             workspace_registry.py)   SCENARIO (propose_roles)
                                            ▲                             │ CONFIRMED (via capability)
                                            │                             ▼
                                            │                          FACTORY (select_forge)
                                            │                             │ CONFIRMED
                                            │                             ▼
                                            │                          FORGE (run_chain)
                                            │                             │ CONFIRMED
                                            │                             ▼
                                            │                    AGENT/ROLE/TOOL (executor)
                                            │                             │ CONFIRMED (ADR-016)
                                            │                             ▼
                                            │                          ARTIFACT (PARTIAL — 3 модели)
                                            │                             │ CONFIRMED
                                            │                             ▼
                                            └── MEMORY/KNOWLEDGE (CONFIRMED/×4 PARTIAL)
```

---

## 3. Статусы по переходам

| Переход | Статус | Ключевой код |
|---------|--------|--------------|
| USER→WORKSPACE | ✅ CONFIRMED | mcp_server.py:236, telegram_bot.py:57 |
| WORKSPACE→PROJECT | ⚠️ **PARTIAL** (2 модели Project) | workspace.py:126 vs workspace_registry.py:93 |
| PROJECT→TASK | ✅ CONFIRMED | task_manager.py:122 (FK) |
| TASK→SCENARIO | ⚠️ **PARTIAL** (через Opportunity, не Task) | opportunity_engine.py:823 |
| SCENARIO→FACTORY | ✅ CONFIRMED | factory_registry.py:272 select_forge |
| FACTORY→FORGE | ✅ CONFIRMED | factory_base.py:368, opportunity_engine.py:949, forge.py:490 |
| FORGE→AGENT/ROLE/TOOL | ✅ CONFIRMED (Agent-сущность IMPLICIT) | role_executor.py:61, forge_facade.py:679 |
| FORGE→ARTIFACT | ✅ CONFIRMED (Artifact contract v5.189.78) | core_02/artifact.py, factory_base.py::normalize_output |
| ARTIFACT→MEMORY/KNOWLEDGE | ✅ CONFIRMED (Knowledge/Graph ×4 PARTIAL) | opportunity_engine.py:1000, memory_store.py:92 |

**Итого: 7 CONFIRMED · 2 PARTIAL · 0 MISSING · 0 CONFLICTING.**

---

## 4. Ключевые находки (промт 108 §14: где архитектура расходится с кодом)

1. **WORKSPACE→PROJECT — 2 модели Project** (workspace.py:126 файловый, workspace_registry.py:93 SQLite).
   ADR-017 осознанно зафиксировал разграничение, но runtime-синхронизация двух моделей в коде не
   автоматизирована — контракт на уровне доктрины (PARTIAL, не CONFLICTING).
2. **TASK→SCENARIO — разрыв в терминах**: промт 108 предполагает Task→Scenario напрямую; в коде
   сценарий выбирается через **Opportunity** (`propose_roles` по title+description), а task_manager-задачи
   со сценариями не связаны. Это MODEL PARTIAL (промт 108 §17): «Opportunity» — недостающее звено в
   модели пользователя (или лишнее в коде).
3. **FORGE→ARTIFACT — контракт реализован:** `core_02/artifact.py` объединяет файл + dict + ChainRun; `factory_base.normalize_output` использует адаптер без изменения сигнатуры. G8 переведён из PARTIAL в CONFIRMED.
4. **AGENT — IMPLICIT**: роли исполняются executor-ами; единого Agent-класса с lifecycle нет
   (ADR-019 Proposed — кандидат).
5. **USER→WORKSPACE входы множатся** (CLI/TG/MCP/HTTP/forge_api) без единого gateway-контракта —
   кандидат на Integration Boundary (ADR-020 Proposed).

---

## 5. Связь с ARCHITECTURAL_BASELINE_V1

- Path A (Project→ForgeFacade→ForgePipeline→ForgeRegistry→Artifact) — **CONFIRMED** (G6+G8).
- Path B (Opportunity→capability→select_forge→ForgeFacade.run_chain) — **CONFIRMED** (G4+G5+G6).
- «Сквозной Project→Scenario→Factory→Forge→Artifact как ОДИН конвейер — опровергнут» — подтверждается:
  реально 2 независимые ветки (Task→Opportunity→Scenario vs Project→Forge), соединённые только через
  `capability` (G5) и ForgeFacade (G6).
- §2 наборы механизмов (Memory×4, Task×2, Role×2, Tool×2, Registry×6, Workspace×2) — все пересечения
  видны в графе как PARTIAL (G2/G4); Knowledge/Graph остаются отдельными механизмами.

---

## 6. История

- **v1.0 (2026-08-22):** построен по промт 108 §14 на основе кода; перекрёстно верифицирован с
  `BASELINE_V1_CODE_VERIFICATION.md` (те же evidence-строки: opportunity_engine.py:949, factory_base.py:368,
  scripts_01/forge.py:490). Код НЕ изменялся.
