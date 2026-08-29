# SCENARIO ENGINE DESIGN v1 — композитор capabilities

| Поле | Значение |
|------|----------|
| **Документ** | SCENARIO_ENGINE_DESIGN_V1.md |
| **Статус** | 🏗 ARCHITECTURAL DESIGN DOCUMENT (проект Scenario Engine — НЕ реализация) |
| **Версия** | 1.0 (2026-08-11) |
| **Базируется на** | FACTORY_FORGE_ARCHITECTURE_V1.md (**v1.1** — Scenario = композитор, §2/§14), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (паспорта кузен), 073_19_factory_forge_dokumentaciya/074_19_arhitekturnaya_refleksiya_factory_forge, RFC_BUFFY_FORGE_V1 (B1–B14), ARB Constitution (054_17), AG Constitution (055_18) |
| **Закрывает** | Missing Capability #2 (§20 карты v1.1) + Open Question 2 (§22 карты) + Шаг 5 Recommended Architecture (§21 карты) |
| **Материальная база в коде** | `core_02/scenario.py` (Scenario ABC), `core_02/scenario_registry.py` (ScenarioRegistry), `core_02/forge_facade.py` (PIPELINE_CHAIN · LIGHT/HEAVY/CONDITIONAL · run_chain · initiate_forge), `core_02/blueprint_v3.py` (BlueprintScenario, 14 ролей), `scripts_01/forge.py` (cmd_chain), `core_02/forge_pipeline.py` (FORGE→…→REPORT), `core_02/workspace.py` (Project) |

---

## 1. Executive Summary

**Scenario Engine** — исполняемый слой Workspace OS, который реализует ключевую сущность карты v1.1: **Scenario = композитор**. Он собирает производственные процессы из **capabilities разных Factory** (а не из одного жёсткого конвейера), передаёт артефакты между шагами, проверяет качество на стыках и отслеживает состояние прогона.

**Главный принцип проектирования — аддитивность (CAN-16):** Scenario Engine **не переписывает** существующее. Он ложится поверх того, что уже работает:

- **`ScenarioRegistry`** (реестр сценариев, fuzzy-поиск ролей, манифесты) — становится регистрационным слоем;
- **`forge chain` (14 ролей)** — становится *первым материальным сценарием-композитором*, а не моделью для всех сценариев;
- **`ForgeFacade`** (единственный санкционированный мост роль → Forge, B2 R-124) — остаётся единственным способом запуска тяжёлых производственных шагов;
- **`RoleArtifactValidator` / `drift_check` / `consistency_check`** — становятся Quality Gates между шагами.

**Новое в проекте — три вещи:**
1. **Сценарий как граф шагов** (не линейный pipeline): условия, ветвления, повторные вызовы (Review → CHANGES REQUIRED → Design), sub-сценарии.
2. **Capability contract** — унифицированная ссылка «какая способность какой Factory нужна», которую Scenario Engine разрешает в конкретного исполнителя (Forge / Engine / Tool / роль).
3. **ScenarioRun state machine** — статусы прогона, артефакты между шагами, resume (развитие существующего `--resume` из `cmd_chain`).

**Вердикт:** проект аддитивен, реализуем поверх существующего кода без параллельной системы; первая материальная реализация — **«Scenario: forge chain»** (14 ролей как граф), затем — кросс-фабричные сценарии.

---

## 2. Позиция в Workspace OS (карта v1.1)

Scenario Engine находится **вне Factory** — он на уровне Workspace, над производственным парком:

```
WORKSPACE
├── PROJECTS                — объекты работы
├── RESOURCES / MEMORY
└── SCENARIOS               ← Scenario Engine (этот документ)
        ├── Scenario: «forge chain» (14 ролей)   [первый материальный***REMOVED***
        ├── Scenario: «Создать продукт»          [кросс-фабричный***REMOVED***
        └── Scenario: «Отклик на вакансию»       [кросс-фабричный***REMOVED***

FACTORIES                   — парк мощностей (capabilities)
├── Research Factory
├── Architecture Factory    (7 Forge: Discovery…Evolution)
├── Code Factory
└── Content Factory
```

**Ключевые утверждения карты v1.1, которые этот проект реализует:**

| Утверждение v1.1 (§14) | Реализация в Scenario Engine |
|------------------------|------------------------------|
| Scenario — не находится внутри Factory | Модуль на уровне Workspace; Factory не знают о сценариях |
| Scenario вызывает capability A → Artifact A → capability B | Граф шагов с артефактной шиной (Artifact Bus) |
| Производственный поток — не жёсткий pipeline (§15) | Граф с условиями и повторными вызовами; `forge chain` — частный случай (линейный граф) |
| Factory не образуют конвейер (§13) | Сценарий сам решает, какие capabilities и в каком порядке подключать |
| Scenario — единственный, кто комбинирует Factory (§15.1) | Scenario Engine — единственный слой, который вызывает разные Factory |

---

## 3. Что уже есть сегодня (материальная база)

### 3.1 ScenarioRegistry (`core_02/scenario_registry.py`)

Уже реализовано:

- **Манифесты сценариев** — YAML-файлы из `runtime_05/scenarios/` (или `$FREEBUFF_SCENARIOS_DIR`);
- **Dispatch table** `_SCENARIO_TYPES`: `scenario_type` → класс (сегодня один: `blueprint_v3` → `BlueprintScenario` = `BlueprintCorpus`);
- **Scenario ABC** (`core_02/scenario.py`): `scenario_id`, `display_name`, `role_objects()`, `load_role_text()`, `routing_hint()`, `validate()`;
- **Кросс-сценарный поиск**: `find_role()`, `all_roles()`, `propose_roles()` (fuzzy через `wizard_lib.score_role_match`);
- **Валидация**: `validate_all()` (ошибки сценариев + кросс-сценарные дубли role_id).

**Сегодняшняя роль ScenarioRegistry — «реестр корпусов ролей»:** он отвечает на вопрос «какая роль подходит под задачу», а не «как выполнить производственный процесс».

### 3.2 forge chain (14 ролей, `core_02/forge_facade.py` + `scripts_01/forge.py`)

Уже реализовано:

- **`PIPELINE_CHAIN`** — 14 производственных ролей в каноническом порядке:
  `explainer → lisa → risk → decomposer → architect → auditor → developer → frontend → devops → tester → fixer → acceptance → documenter → retrospective`;
- **Классификация ролей**:
  - `LIGHT_ROLES` (8): explainer, lisa, risk, decomposer, architect, auditor, documenter, retrospective — **CHECK-only** (проверка существования артефактов через RoleArtifactValidator);
  - `HEAVY_ROLES` (4): developer, tester, fixer, acceptance — **full_cycle** (полный ForgePipeline через `initiate_forge`);
  - `CONDITIONAL`: frontend (только если `project.type == "web"`), devops (always → full_cycle);
  - `REFERENCE_ROLES` (orchestrator, context_keeper) — вне Facade-scope (gate → ValueError).
- **`run_chain()`** — ChainRunner: pre-flight `RoleArtifactValidator` → per-role `ChainStage` (mode: `check_only` / `full_cycle` / `conditional_skip`) → агрегированный `ChainRun.overall` (`ok` / `partial` / `failed` / `degraded`);
- **`initiate_forge()`** — **единственный санкционированный мост** роль → ForgePipeline (B2 R-124: `project_read_only` — Forge не мутирует Project без явного разрешения);
- **`cmd_chain` CLI** (`scripts_01/forge.py`): `--roles`, `--skip-stages`, `--full-cycle`, `--resume`, `--json`, `--no-compose`, `--no-tg`, `--dry-run`;
- **`--resume`** — восстановление с последней успешной роли из `last_pipeline['chain'***REMOVED***` (уже есть! см. §9).

**Сегодняшняя роль forge chain — «линейный сценарий Code Factory»:** одна цепочка, один порядок, конвейерно-линейная. Это частный случай графовой модели, которую вводит этот проект.

### 3.3 Маппинг «роль → выходные артефакты»

`DEFAULT_ROLE_OUTPUTS` в `forge_facade.py` уже фиксирует артефакты каждой роли (например: architect → `architecture.md`, `adr/*.md`, `contracts.yaml`; developer → `src/**/*.py`, `tests/**/*.py`; retrospective → `retrospective_report.md`, `LESSONS.md`). Это — готовая основа для артефактной шины (§7).

---

## 4. Разрыв: что Scenario Engine добавляет поверх

| Аспект | Сегодня | Scenario Engine |
|--------|---------|-----------------|
| **Форма сценария** | Линейная цепочка ролей (`PIPELINE_CHAIN`) | **Граф шагов** (DAG): условия, ветвления, повторные вызовы, sub-сценарии |
| **Источник capabilities** | Только роли Blueprint v3 (одна «фабрика») | **Разные Factory**: Research / Architecture / Code / Content |
| **Вызов Forge** | `initiate_forge` только из роли | `initiate_forge` из любого шага сценария (гейт остаётся) |
| **Состояние** | `ChainRun` + `last_pipeline['chain'***REMOVED***` | `ScenarioRun` (шаги + артефакты + gates) — развитие существующего |
| **Качество между шагами** | RoleArtifactValidator (existence) | Quality Gates: валидатор + drift_check + consistency_check + паспортные gates кузен |
| **Повторные вызовы** | Нет (линейно, `--resume` — с точки останова) | Да: `Review → CHANGES REQUIRED → Design → Review` — цикл внутри одного прогона |
| **Тип сценария в реестре** | `blueprint_v3` (корпус ролей) | + `graph` (композитор: шаги + capability refs) — **аддитивный** тип |

**Принцип:** Scenario Engine — это **эволюция**, а не замена. `ScenarioRegistry` остаётся реестром; `forge chain` остаётся рабочим сценарием; добавляется слой графовой композиции и разрешения capabilities.

---

## 5. Модель: Scenario = граф шагов

### 5.1 Базовая структура

```
SCENARIO (манифест, YAML)
├── id, display_name
├── input_contracts        — что сценарий принимает (project, user_query, …)
├── output_contracts       — что сценарий производит (final artifacts)
└── steps: [Step, ...***REMOVED***     — вершины графа
        Step
        ├── step_id
        ├── capability     — ссылка на способность (CapabilityRef, §6)
        ├── inputs         — [artifact refs***REMOVED***  (что ждёт)
        ├── outputs        — [artifact refs***REMOVED***  (что производит)
        ├── condition      — необязательное условие (напр. project.type == "web")
        ├── gates          — [quality gate refs***REMOVED*** (§8)
        └── on_failure     — "abort" | "skip" | "retry_n(3)" | "goto(step)"
```

Рёбра графа — **артефактные зависимости**: шаг B может начаться, когда шаг A произвёл артефакт, который B ждёт на входе. Порядок исполнения — топологический, не захардкоженный.

### 5.2 Не жёсткий pipeline (v1.1 §15)

```
Scenario «Создать архитектуру»
   Design ──► Review ──► APPROVED ──► Decision ──► ADR
      ▲         │
      └── CHANGES REQUIRED ──┘        ← повторный вызов Design (цикл)
```

Повторный вызов выражается через `on_failure: "goto(design)"` на шаге Review. Сценарий **не обязан** проходить каждый шаг один раз — это фича графовой модели, отсутствующая в линейном chain.

### 5.3 Условия и ветвления

```
Step: frontend
  condition: project.type == "web"   ← существующая логика run_chain (frontend → conditional_skip)
  on_false: skip                     ← «условная ветвь» без жёсткого pipeline
```

Условия уже существуют в `run_chain` (frontend), этот проект их обобщает на любой шаг.

---

## 6. Capability contract и разрешение

### 6.1 CapabilityRef — унифицированная ссылка на способность

Единый формат, который Scenario Engine понимает на входе шага:

```yaml
capability:
  kind: forge | engine | tool | role | sub_scenario
  factory: "code"           # какая Factory (для forge/engine)
  forge: "generation"       # какая Forge внутри Factory (для forge)
  engine: "developer"       # какой Engine/роль (для engine/role)
  tool: "drift_check"       # какой Tool (для tool)
  sub: "job_application"    # какой sub-сценарий (для sub_scenario)
```

> Примечание: разграничение «Engine vs роль» (пример `engine: developer`) фиксируется на этапе проектирования паспортов (см. §15, вопрос о роли↔Engine).

### 6.2 Разрешение (Resolver)

```
CapabilityRef ──► ScenarioEngine.resolve()
                    │  ├── kind=forge/engine → Factory Registry (паспорта кузен)
  │        └── исполнитель: ForgeFacade.initiate_forge (роль в PIPELINE_ROLES)
  │                       ИЛИ run_chain(subset) ИЛИ паспортная реализация кузни
  ├── kind=role         → ScenarioRegistry.find_role / role_objects
  │        └── исполнитель: инжекция role_text в вызов модели (как wizard)
  ├── kind=tool         → Tool Registry (scripts_01/…: drift_check,
  │        └── consistency_check, doctor, metrics, research_web, lisa_estimator …)
  └── kind=sub_scenario → вложенный ScenarioRun (композиция сценариев)
```

> ⚠️ **Принцип Missing Capability (поправка):** если capability нужна сценарию, но её ещё нет в коде — это **НЕ «несуществующий токен»**, а **недостающая способность, которую нужно построить**. Процедура: (1) зафиксировать в §20 карты v1.1 (Missing Capabilities) + реестре; (2) написать промт на реализацию (например, `research_web` → зарегистрирован как Missing Capability #6, промт `pompts_11/075_04_research_web_capability.md`); (3) после реализации — пополнить закрытый словарь (`KNOWN_CAPABILITIES` + Tool Registry). Токен, которого нет в словаре И нет в реестре недостающих способностей — ошибка компиляции; токен из реестра недостающих — валиден как намерение, с указанием промта.

**Правило §7.3 / B2 R-124 (не нарушается):** любой путь к ForgePipeline идёт **только через `ForgeFacade`** (initiate_forge / run_chain). Scenario Engine — ещё один вызывающий, но мост остаётся единственным. Grep-инвариант `ForgePipeline(` вне forge_facade.py сохраняется.

### 6.3 Vocabulary (закрытое множество)

Имена `factory` / `forge` / `engine` / `tool` в CapabilityRef — **закрытый словарь** (урок ANTI-6b / CON-8): каждый токен ДОЛЖЕН существовать в реестре Factory/Forge, в `KNOWN_CAPABILITIES` (`blueprint_v3.py`) **или быть зарегистрирован в реестре недостающих способностей** (§20 карты v1.1 + промт на реализацию — принцип Missing Capability, §6.2). Неизвестный токен (нет ни в словаре, ни в реестре недостающих) → громкая ошибка при компиляции сценария, НЕ silent fallback. Это же правило уже защищает `CAPABILITIES_OVERRIDE` (ValueError при drift).

---

## 7. Внутреннее устройство Scenario Engine

Следуя карте v1.1 — **не спускаемся ниже Engine** на карте; Skills/Tools/Agents — внутри Modules.

```
SCENARIO ENGINE
├── Scenario Registry        — реестр сценариев (эволюция ScenarioRegistry)
│       └── типы: blueprint_v3 (корпус) + graph (композитор) — аддитивно
├── Scenario Compiler        — манифест графа → исполняемый план
│       ├── Topo Sorter          (порядок шагов по артефактным зависимостям)
│       ├── Condition Evaluator  (условия шагов: project.type, наличие артефакта)
│       └── Vocabulary Validator (CapabilityRef ⊆ закрытый словарь; ValueError при drift)
├── Capability Resolver      — CapabilityRef → конкретный исполнитель (§6)
├── Step Executor            — исполняет один шаг
│       ├── Forge Invoker        (ForgeFacade.initiate_forge / run_chain subset)
│       ├── Role Invoker         (ScenarioRegistry → role_text → модель)
│       ├── Tool Invoker         (drift_check, consistency_check, doctor, research_web, lisa_estimator, …)
│       └── SubScenario Invoker  (вложенный ScenarioRun)
├── Artifact Bus             — артефакты между шагами
│       ├── Artifact Store        (project root: role outputs, см. DEFAULT_ROLE_OUTPUTS)
│       ├── Contract Checker      (входы/выходы шага соответствуют объявленным)
│       └── Trace Logger          (каждый переход — в event_log, Observability)
├── Quality Gate Runner      — проверки на стыках шагов (§8)
├── State Machine            — ScenarioRun: статусы + resume (§9)
└── Scenario CLI / API       — cmd_chain-подобный интерфейс (scripts_01/forge.py: chain)
```

### Каждый шаг исполняется в одном из режимов

| Режим шага | Исполнитель | Пример |
|------------|-------------|--------|
| `check_only` | RoleArtifactValidator (existence) | explainer, architect, auditor (LIGHT) |
| `full_cycle` | ForgeFacade.initiate_forge (ForgePipeline) | developer, tester, fixer, acceptance (HEAVY) |
| `conditional_skip` | Условие не выполнено → пропуск | frontend для не-web проекта |
| `tool` | Прямой вызов Tool | drift_check после реализации |
| `agent` | Роль/Engine через модель (role_text) | будущие интеллектуальные шаги |
| `sub_scenario` | Вложенный ScenarioRun | «Отклик на вакансию» = sub-сценарий внутри «Создать продукт» |

---

## 8. Quality Gates между шагами

Каждый шаг может объявить gates — проверки, которые должны пройти **до** того, как его артефакты будут переданы следующему шагу:

```yaml
gates:
  - kind: artifacts        # RoleArtifactValidator: все outputs шага материализованы
  - kind: drift            # scripts_01/drift_check.py
  - kind: consistency      # scripts_01/consistency_check.py
  - kind: passport         # паспортные Quality Gates кузни (FACTORY_FORGE_PASSPORTS…)
  - kind: governance       # AG Constitution (055_18): conformance вердикт
```

**Связь с паспортами кузен:** каждая Forge уже описывает свои Quality Gates (например, Review Forge: Evidence Complete · Context Complete · Alternatives Considered · Risks Assessed). Scenario Engine исполняет эти gates на стыке «шаг A → шаг B», где A произвёл артефакт для B.

**Экзистенциальный базовый слой — уже есть:** `run_chain` выполняет pre-flight `RoleArtifactValidator` для всех ролей. Scenario Engine расширяет это до per-step gates (drift/consistency/governance).

---

## 9. State Machine: ScenarioRun + resume

### 9.1 Статусы

```
ScenarioRun
├── queued      — скомпилирован, ждёт исполнения
├── running     — исполняются шаги (с текущим active_step)
├── partial     — часть шагов завершена, часть failed/skipped (как ChainRun.overall)
├── ok          — все обязательные шаги завершены успешно
├── failed      — критический шаг упал без обработки on_failure
└── degraded    — registry unavailable, но прогон выполнился (как ChainRun.overall)
```

### 9.2 Per-step статусы (развитие ChainStage)

```
StepRun
├── pending / running
├── ok / run_ok            (check_only / full_cycle)
├── partial / missing      (existence-проверки)
├── skipped                (conditional_skip)
├── run_failed             (ForgePipeline вернул failed)
└── init_error             (исключение на запуске — soft-failure, chain продолжается)
```

### 9.3 Resume — уже существует в cmd_chain

`--resume` в `cmd_chain` читает `registry.get_project_status(...).last_pipeline['chain'***REMOVED***`, ищет последний stage со status в `{"ok", "run_ok"***REMOVED***` и продолжает с next-after. **ScenarioRun сериализуется в тот же `last_pipeline['chain'***REMOVED***`-механизм** (через `ForgeFacade.record_run`) — resume для графовых сценариев = тот же паттерн, расширенный на граф (resume с последнего успешного шага по топологии).

---

## 10. Маппинг: 14 ролей → capabilities

Этот маппинг — **первая материальная реализация** сценария: «Scenario: forge chain» = граф из 14 шагов, где каждый шаг — CapabilityRef на роль/Engine. Сегодняшние классификации становятся декларацией в манифесте, а не кодом в run_chain.

| Роль | Kind (v1.1) | Factory | Режим сегодня (run_chain) | Outputs (DEFAULT_ROLE_OUTPUTS) |
|------|-------------|---------|---------------------------|--------------------------------|
| explainer | engine/role | Architecture (Discovery) | LIGHT · check_only | brief.md, parsed_requirements.md |
| lisa | engine/role | Research (будущая) | LIGHT · check_only | lisa_report.md |
| risk | engine/role | Architecture (Review) | LIGHT · check_only | risk_matrix.md |
| decomposer | engine/role | Architecture (Design) | LIGHT · check_only | decomposition.md, module_list.md, integration_topology.md |
| architect | engine/role | Architecture (Design) | LIGHT · check_only | architecture.md, adr/*.md, contracts.yaml |
| auditor | engine/role | Architecture (Review) | LIGHT · check_only | audit_report.md |
| developer | forge/engine | Code (Generation) | HEAVY · full_cycle | src/**/*.py, tests/**/*.py, migrations/*.py |
| frontend | forge/engine | Code (Generation) | CONDITIONAL (web) | frontend/**/*.tsx, **/*.css, **/*.html |
| devops | forge/engine | Code (Release/Infra) | CONDITIONAL (always) | Dockerfile, docker-compose.yml, .github/workflows/*.yml |
| tester | forge/engine | Code (Testing) | HEAVY · full_cycle | tests/**/*.py, mutation_test_results.md |
| fixer | forge/engine | Code (Debugging) | HEAVY · full_cycle | bug_fixes.md, regression_tests.py |
| acceptance | forge/engine | Code (Review) | HEAVY · full_cycle | acceptance_report.md, validation.md |
| documenter | engine/role | Content (Documentation) | LIGHT · check_only | README.md, PORTFOLIO_CASE.md, TG_POST.md |
| retrospective | engine/role | Governance/Evolution (Feedback) | LIGHT · check_only | retrospective_report.md, LESSONS.md, lisa_calibration.yaml |

**Наблюдение (обновлено по ROLE_FORGE_MATRIX_V1.md):** 14 ролей — это **не 14 Forge**, а Engine/роли внутри ~6 Forge разных Factory (§6 критериев карты v1.1: Forge = собственный производственный результат; роль без собственного результата — Engine). Маппинг «роль → Engine/Forge какой Factory» зафиксирован в **ROLE_FORGE_MATRIX_V1.md** (закрывает Open Question 3 ARB-REV-003). Аналитические роли уточнены по материальным модулям кузен: **explainer → Architecture (Discovery Forge, Requirement Analysis), risk → Architecture (Review Forge, Risk Assessor), decomposer → Architecture (Design Forge, System Decomposition)**; lisa → Research Factory (будущая Estimation Engine); documenter — открытый вопрос (Content vs Code Documentation Forge, Q1). «Разведка» в §17.1 — lifecycle-группировка, а не Factory-принадлежность. «Scenario: forge chain» остаётся **одним сценарием**, который комбинирует эти Engine-капабилити — ровно как это делает сценарий «Создать продукт» для кузен Architecture Factory.

---

## 11. Эволюция ScenarioRegistry (манифесты v2)

### 11.1 Аддитивный тип `graph`

`_SCENARIO_TYPES` получает второй тип (сегодня только `blueprint_v3`):

```python
_SCENARIO_TYPES: dict[str, type[Scenario***REMOVED******REMOVED*** = {
    "blueprint_v3": BlueprintScenario,   # существующее — НЕ трогаем
    "graph": GraphScenario,               # новый: композитор (этот документ)
***REMOVED***
```

`GraphScenario` реализует тот же Scenario ABC (`scenario_id`, `display_name`, `role_objects`, `load_role_text`, `routing_hint`, `validate`) — **реестр принимает его полиморфно без изменений**. `role_objects()` для graph-сценария возвращает capabilities, объявленные в его шагах (как «роли» для поиска/валидации).

### 11.2 Манифест graph-сценария (расширение ScenarioManifest)

```yaml
id: create_product
type: graph
display_name: Создать продукт
root: runtime_05/scenarios/create_product.yaml
capabilities: [research, architecture, code***REMOVED***     # существующее поле manifest
metadata:
  input_contracts: [project_root, user_query***REMOVED***
  output_contracts: [final_product***REMOVED***
steps:
  - step_id: research
    capability: {kind: tool, tool: research_web***REMOVED***
    outputs: [research_report.md***REMOVED***
  - step_id: estimate
    capability: {kind: tool, tool: lisa_estimator***REMOVED***
    inputs: [research_report.md***REMOVED***
    outputs: [lisa_report.md***REMOVED***
  - step_id: discover
    capability: {kind: role, role: decomposer***REMOVED***
    inputs: [research_report.md, lisa_report.md***REMOVED***
    outputs: [architectural_problem.md***REMOVED***
  - step_id: review
    capability: {kind: role, role: auditor***REMOVED***
    on_failure: {goto: discover***REMOVED***
```

### 11.3 Реестры: два уровня, без параллельной системы

| Реестр | Сегодня | Роль в Scenario Engine |
|--------|---------|------------------------|
| **ScenarioRegistry** | сценарии (корпуса ролей) | + graph-сценарии (композиторы) |
| **ForgeRegistry** (`forge_registry.py`) | проекты + статусы прогонов | статусы `ScenarioRun` (last_pipeline.chain уже там) |
| **Factory Registry** (Missing Capability #1, карта v1.1 §20) | — | будущее: паспорта кузен, разрешение `CapabilityRef` (§6.2) |

---

## 12. Интеграция с существующим кодом (additive)

| Слой | Существующий код | Роль в Scenario Engine |
|------|------------------|------------------------|
| Реестр сценариев | `core_02/scenario_registry.py` | Реестр + graph-тип (аддитивно) |
| ABC сценария | `core_02/scenario.py` (Role, Scenario, ScenarioManifest) | База; GraphScenario реализует ABC |
| Мост к Forge | `core_02/forge_facade.py` (initiate_forge, run_chain) | **Единственный** исполнитель full_cycle/check_only |
| Роли | `core_02/blueprint_v3.py` (BlueprintScenario, CAPABILITIES_OVERRIDE) | Источник role-capabilities |
| Pipeline | `core_02/forge_pipeline.py` (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT) | Исполняется через ForgeFacade, НЕ напрямую |
| Проверки | `RoleArtifactValidator`, `drift_check.py`, `consistency_check.py`, `doctor.py` | Quality Gates (§8) |
| Память | `memory_store.py` (record_learning_event), `LESSONS.md` | Feedback после ScenarioRun |
| Статусы | `forge_registry.record_run` (last_pipeline.chain) | Персистентность ScenarioRun + resume |
| CLI | `scripts_01/forge.py cmd_chain` (--roles, --resume, --json, --full-cycle) | Модель для Scenario CLI |

**Ограничения (не нарушаются):**
- `ForgePipeline(` инстанцируется **только** в `forge_facade.py` (grep-инвариант §7.3);
- Каждый токен CapabilityRef ⊆ закрытый словарь (ANTI-6b / CON-8);
- Изменения — аддитивные (новые файлы: `core_02/scenario_graph.py`/`scenario_engine.py`; расширение dispatch table).

---

## 13. Примеры сценариев

### 13.1 «Scenario: forge chain» (первый материальный)

**Цель:** доказать механику без нового функционала. Граф из 14 шагов = ровно текущее поведение `run_chain`, но объявленное декларативно (LIGHT/HEAVY/CONDITIONAL становятся `mode` шага, а не if-ветки в коде). Resume, JSON, full-cycle — уже работают.

### 13.2 «Создать продукт» (кросс-фабричный, карта v1.1 §14)

```
steps:
  - research       (Research Factory → research_web, Missing Capability #6) → research_report.md
  - estimate       (Research Factory → lisa_estimator, Missing Capability #7) → lisa_report.md
  - discover       (Architecture/Design → role: decomposer)     → architectural_problem.md
  - design         (Architecture → role: architect)             → architecture.md
  - review         (Architecture → forge: review, паспорт)      → verdict
       on_failure: {goto: design***REMOVED***        ← цикл до APPROVED
  - decide         (Architecture → forge: decision)             → adr/*.md
  - implement      (Code → role: developer, full_cycle)         → src/**
  - test           (Code → role: tester, full_cycle)            → tests/**
  - conform        (Governance → tool: drift_check + AG)        → conformance
```

> Примечание: шаги `research` и `estimate` используют capabilities **`research_web`** (Missing Capability #6) и **`lisa_estimator`** (Missing Capability #7) — обе ✅ **реализованы** (§20 карты v1.1: `scripts_01/research_web.py` по промту `pompts_11/075_04_research_web_capability.md`, `scripts_01/lisa_estimator.py` по промту `pompts_11/076_13_lisa_estimator_capability.md`). Токены вошли в закрытый словарь (`research`/`estimation` в KNOWN_CAPABILITIES + ModelCatalog) и Tool Registry — сценарий работает без изменений манифеста. `lisa_report.md` (оценка сложности LISA-3) передаётся на шаг `discover` как вход для Architecture/Design (risk-aware декомпозиция).

Factory не знают о сценарии — они просто предоставляют capabilities (Research Forge, Architecture Review Forge, Code Generation…). Scenario их комбинирует.

### 13.3 «Отклик на вакансию» (карта v1.1 §14 — компактный пример)

```
Company Research (Research) → Opportunity Analysis
Solution Design (Architecture/Code) → Demo
Writing (Content) → Application
Interview Prep (sub_scenario: research → simulation → preparation)
```

---

## 14. Внедрение (additive, по шагам)

1. **Шаг 0 (материализация графа):** переписать `run_chain`-механику на декларативный манифест «Scenario: forge chain» — 14 шагов, режимы LIGHT/HEAVY/CONDITIONAL. Поведение идентично, регрессия = существующие тесты `test_forge_chain_cli.py`, `test_forge_chain_real_integration.py`, `test_run_chain.py`.
2. **Шаг 1 (GraphScenario):** новый класс `graph` в `_SCENARIO_TYPES`; компилятор (topo-sort, vocabulary validat), манифест v2 (§11.2).
3. **Шаг 2 (Capability Resolver):** `CapabilityRef → ForgeFacade | Role | Tool | sub_scenario`; гейт vocabulary.
4. **Шаг 3 (State Machine + gates):** `ScenarioRun` (статусы §9.1), персистентность через `ForgeFacade.record_run`, per-step Quality Gates (§8).
5. **Шаг 4 (кросс-фабричный сценарий):** «Создать продукт» (§13.2) — первый реальный кросс-фабричный граф.
6. **Шаг 5 (Factory Registry):** паспорта кузен как машиночитаемый индекс для Resolver (Missing Capability #1).

---

## 15. Открытые вопросы

1. **Где живёт Scenario Engine в коде:** новый `core_02/scenario_engine.py` + `core_02/scenario_graph.py`, или эволюция `scenario_registry.py`? (Рекомендация: новые модули + аддитивный тип в registry.)
2. **Параллельность шагов:** допускает ли Artifact Bus параллельное исполнение независимых ветвей графа? (v1: нет — топологический порядок; параллель — будущее.)
3. **Человек в цикле:** где сценарий должен останавливаться для утверждения (Human in the loop)? (Маппинг на паспорта кузен — Human Involvement.)
4. **Формат манифеста:** YAML (как ScenarioManifest) vs JSON (как ChainRun.to_dict)? (Рекомендация: YAML для манифеста, JSON для состояния прогона.)
5. **Связь с диспетчером задач:** prompt_queue/prompt_dispatcher (внешние задачи) — вызывают сценарии или сценарии вызывают их?
6. **Scenario vs Factory Registry:** статусы сценариев в ForgeRegistry (last_pipeline) vs отдельный Scenario Registry — консолидировать или параллелить?

---

## 16. Вердикт

**Scenario Engine (композитор) — аддитивный слой поверх существующего кода, не параллельная система.**

- ✅ **Модель:** Scenario = граф шагов (не pipeline), CapabilityRef как унифицированная ссылка на способности любой Factory, ScenarioRun state machine + resume.
- ✅ **Материальная база:** ScenarioRegistry (реестр + ABC) и forge chain (14 ролей, ForgeFacade-мост, RoleArtifactValidator, --resume) уже реализуют 70% механики — остаётся графовая композиция и разрешение capabilities.
- ✅ **Границы v1.1 соблюдены:** Scenario вне Factory; единственный комбинатор Factory; ForgeFacade — единственный мост к Forge (B2 R-124); карта не спускается ниже Engine.
- ✅ **Аддитивность:** `blueprint_v3` тип не трогаем; добавляется `graph` тип; `forge chain` остаётся рабочим сценарием.
- 🟡 **Зависимости:** полный Resolver опирается на Factory Registry (Missing Capability #1) — может быть отложен; «Scenario: forge chain» реализуем без него.

**Следующий шаг после утверждения:** Шаг 0 — «Scenario: forge chain» как первый материальный граф (регрессия по существующим chain-тестам), затем GraphScenario (§11.1).

---

*Документ спроектирован на базе: FACTORY_FORGE_ARCHITECTURE_V1.md (v1.1, Scenario = композитор), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (паспорта кузен, Quality Gates), реального кода — core_02/{scenario,scenario_registry,forge_facade,blueprint_v3,forge_pipeline,forge_registry,workspace***REMOVED***.py и scripts_01/forge.py (cmd_chain). Статус: ARCHITECTURAL DESIGN DOCUMENT — проектирование, не реализация.*
