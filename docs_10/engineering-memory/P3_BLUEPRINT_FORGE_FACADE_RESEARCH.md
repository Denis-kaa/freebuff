# P3 — Blueprint v3 → Forge Facade: Задача 0 (исследование)

> **Статус:** RESEARCH (Задача 0 из промт 70, Миссия 2 — Blueprint v3 → Forge Facade)
> **Дата:** 2026-08-10
> **Источник задачи:** `pompts_11/071_02_prompt_architect_1_7.md` Миссия 2 Задача 0
> **Следующий шаг:** Задача 1 (Facade design) — на основе этих находок

---

## 0. Explain-first: с чего начал и почему

Начал с **Направления А (внутренний аудит)** до Направления Б (аналоги), потому что:

1. промт 70 прямо требует: «есть ли уже прецедент такого паттерна внутри самой платформы, прежде чем искать внешние примеры» — внутренний аудит даёт ground truth, на котором проверяется релевантность внешних аналогов.
2. Основной вопрос Задачи 0 («роль = справочник или производственная стадия?») решается **только данными registry.yaml + реальными инстансами**, не мнением.
3. Объём данных мал (1 registry.yaml, 17 ролей, 3 provider-манифеста) — полный проход дёшев, частичный был бы ленивым.

---

## 1. Направление А — внутренний аудит 17 ролей Blueprint v3

### 1.1 Источник данных

- Канонический корпус: `/storage/emulated/0/PROJECTS/workstation/blueprints_v3/` (**вне** freebuff-репо, per DESIGN DECISION в `core_02/blueprint_v3.py:56` — `DEFAULT_BLUEPRINTS_DIR`).
- `registry.yaml` — декларативный реестр: секция `pipeline:` с 17 ролями + `project_types.*` + `complexity_routing.*` + `categories.*`.
- Код-читатель: `core_02/blueprint_v3.py` (BlueprintCorpus / BlueprintScenario), диспетчеризация через `core_02/scenario_registry.py` `_SCENARIO_TYPES` + Scenario ABC.

### 1.2 Роль-за-ролью: справочник vs производственная стадия

Критерий производственной стадии (из промт 70 §1046-1048): **есть явный вход/выход (outputs) и естественная передача следующей роли (dependencies)** — как в vkusvill_demo analyst→developer→reviewer (§7.5).

> **Уточнение критерия (важно для читателя):** `dependencies: [***REMOVED***` сам по себе НЕ дисквалифицирует роль — `explainer` (СТАДИЯ 1) тоже имеет `dependencies: [***REMOVED***`, но является **входной стадией линейной цепи** (её выход `brief.md`/`parsed_requirements.md` потребляет `lisa`). Реальный различающий признак — **принадлежность к линейной производственной цепи** (роль получает вход от предшественника И/ИЛИ её выход потребляется следующим): `context_keeper` (deps `[***REMOVED***`, выход `manifest.md` никем не потребляется как стадийный вход) — служебный кросскат, не стадия.

| # | role_id (file) | type | dependencies | outputs | Вердикт | Evidence (registry.yaml) |
|---|----------------|------|--------------|---------|---------|--------------------------|
| 1 | orchestrator (00) | management | — | — | **СПРАВОЧНИК** (диспетчер, entry_point, без артефакта) | `entry_point: true`, triggers /start/status/next, нет outputs |
| 2 | context_keeper (01) | management | [***REMOVED*** | manifest.md | **СПРАВОЧНИК** (служебный кросскат, 1 артефакт состояния) | `dependencies: [***REMOVED***`, `outputs: [manifest.md***REMOVED***` |
| 3 | explainer (02) | analysis | [***REMOVED*** | brief.md, parsed_requirements.md | **СТАДИЯ 1** ✅ | первый выход из «сырого ТЗ» |
| 4 | lisa (03) | estimation | explainer | lisa_report.md + metrics | **СТАДИЯ 2** ✅ | `dependencies: [explainer***REMOVED***` |
| 5 | risk (04) | estimation | lisa | risk_matrix.md + verdict GO/COND/NO-GO | **СТАДИЯ 3** ✅ | `dependencies: [lisa***REMOVED***` |
| 6 | decomposer (05) | architecture | risk | decomposition.md, module_list.md, integration_topology.md | **СТАДИЯ 4** ✅ | `dependencies: [risk***REMOVED***` |
| 7 | architect (06) | architecture | decomposer | architecture.md, adr/*.md, contracts.yaml | **СТАДИЯ 5** ✅ | `dependencies: [decomposer***REMOVED***` |
| 8 | auditor (07) | validation | architect | audit_report.md + verdict + `loop: until_ready, max_iterations: 3` | **СТАДИЯ 6 (quality gate)** ✅ | `dependencies: [architect***REMOVED***`, loop |
| 9 | response_writer (08) | communication | auditor | client_response.md | **СТАДИЯ 7a (presale-трек)** ✅ | `dependencies: [auditor***REMOVED***` |
| 10 | developer (09) | implementation | auditor | src/**/*.py, tests/**/*.py, migrations/*.py | **СТАДИЯ 7b (ядро)** ✅ | `dependencies: [auditor***REMOVED***` |
| 11 | frontend (10) | implementation | developer | frontend/**/*.tsx, *.css, *.html | **СТАДИЯ 8 (условная)** ✅ | `condition: project_type == "web"`, `dependencies: [developer***REMOVED***` |
| 12 | devops (11) | infrastructure | developer | Dockerfile, docker-compose.yml, workflows, terraform | **СТАДИЯ 8 (условная)** ✅ | `dependencies: [developer***REMOVED***` |
| 13 | tester (12) | validation | developer, frontend | tests/**/*.py, mutation_test_results.md | **СТАДИЯ 9** ✅ | `dependencies: [developer, frontend***REMOVED***` |
| 14 | fixer (13) | implementation | tester | bug_fixes.md, regression_tests.py + `loop: until_pass, max_iterations: 3` | **СТАДИЯ 10 (условная, loop)** ✅ | `condition: on_test_fail` |
| 15 | acceptance (14) | validation | tester, fixer | acceptance_report.md, validation.md + verdict ACCEPTED/REJECTED | **СТАДИЯ 11 (final QA)** ✅ | `dependencies: [tester, fixer***REMOVED***` |
| 16 | documenter (15) | delivery | acceptance | README.md, PORTFOLIO_CASE.md, TG_POST.md, API_DOCS.md, ARCHITECTURE.md | **СТАДИЯ 12** ✅ | `dependencies: [acceptance***REMOVED***` |
| 17 | retrospective (16) | evolution | documenter | retrospective_report.md, LESSONS.md, lisa_calibration.yaml | **СТАДИЯ 13 (эволюция → обратная связь в LISA)** ✅ | `dependencies: [documenter***REMOVED***` |

### 1.3 Итог аудита: 15/17 — производственные стадии, 2/17 — справочные

- **15 ролей (explainer→…→retrospective)** имеют `dependencies` + `outputs` и **уже образуют линейную производственную цепь**:

  ```
  explainer → lisa → risk → decomposer → architect → auditor
      ├─→ response_writer (presale-трек)
      └─→ developer → (frontend | devops) → tester → [fixer****REMOVED*** → acceptance → documenter → retrospective
        (* fixer: condition on_test_fail, loop until_pass ≤3)
  ```

- **2 роли справочные/служебные** (НЕ стадии): `orchestrator` (диспетчер, entry_point, нет артефакта) и `context_keeper` (состояние/manifest) — они остаются как есть, Facade их НЕ трогает (per промт 70 границы: «НЕ трогать роли, определённые как справочные»).
- **`response_writer` — особый случай:** у неё есть вход/выход (auditor → client_response.md), но это presale-трек (коммуникация), не runtime-артефакт проекта. Фаза 0 классифицирует как «стадия, но параллельного трека» — Facade-путь для неё опционален.

### 1.4 Критическая находка: цепочка декларативна, но НЕ ИСПОЛНЯЕТСЯ

- **`resolve_pipeline()`** (`core_02/blueprint_v3.py:417-434`) вычисляет порядок ролей по `project_types`/`complexity_routing`, но вызывается **только из тестов** (`tests_09/test_blueprint_v3.py:159-174`) — **ни один runtime-исполнитель его не использует** (grep: `scripts_01/wizard.py` → 0 вызовов).
- `wizard.py` выбирает **одну** роль (`force_role_id` / `propose_roles` fuzzy-match) — не проходит по всей цепочке.
- grep подтверждает границу §7.3 на уровне кода: `grep -rniE 'forge' core_02/scenario_registry.py core_02/wizard_lib.py` → **0 вхождений** (также зафиксировано в AUDIT_WS_OS_P65_§9_V1 C-Forge-10/12).
- **Вывод:** реестр — это «производственная линия на бумаге» (декларативный граф), но нет **Factory/исполнителя**, который бы вёл роли по цепочке и умел бы по явному запросу инициировать Forge-прогон. Это ровно gap из §7.6 п.2 («No direct Forge invocation») — и ровно то, что Facade должен закрыть.

### 1.5 Дополнительные факты (drift/риски)

- **`8a_ssa.md` существует на диске (13 788 байт), но НЕ зарегистрирован в registry.yaml** (`pipeline:` содержит только 17 записей) → registry drift (роль-файл без реестра). Тот же класс, что урок LA-3 (MANIFEST vs реальность) — проверять `ls`-ом.
- В корпусе есть `.bak`-файлы (`05_decomposer.md.bak`, `06_architect.md.bak`, `07_auditor.md.bak`, `09_developer.md.bak`, `10_frontend_dev.md.bak`) — артефакты backup-процесса, не путать с активными ролями.
- `registry.yaml metadata.total_blueprints: 17` — соответствует `pipeline:`, но файлов .md в каталоге 19 (17 + 8a_ssa.md + MANIFEST.md).
- `CAPABILITIES_OVERRIDE` (`blueprint_v3.py:120-145`) содержит **18 записей** (вкл. `environment_doctor` — нет в registry.yaml pipeline) → ещё один признак, что override-словарь жил отдельно от реестра (защищён CON-8 vocabulary-валидатором, это не баг, а эволюция).

---

## 2. Направление Б — аналоги: внутренний прецедент ПОДТВЕРЖДЁН

### 2.1 Прецедент №1: `runtime_05/providers/` YAML auto-discovery ✅

- **Архитектурный принцип** зафиксирован: ARCHITECTURE_MANIFEST принцип №7 **Marketplace-Ready** — «`runtime_05/providers/` (YAML), `runtime_05/plugins/` (Python), `runtime_05/recipes/`. No core change, auto-discovery, capability-first».
- **Реализация:** `freebuff_plugin_03/runtime/registry.py::load_providers_from_dir()` (строка 196) — скан `*.yaml`/`*.yml` из `runtime_05/providers/`, docstring: «Marketplace-ready: новый Runtime добавляется YAML-файлом, без изменения кода ядра»; `discover()` (строка 433) лениво триггерит загрузку.
- Манифесты на месте: `freebuff.yaml`, `claude_code.yaml`, `openclaw.yaml` (3 шт.), каждый — name/capabilities (с confidence 0.0-1.0)/platforms/install/requirements.

### 2.2 Прецедент №2: `runtime_05/scenarios/` auto-discovery ✅ (та же философия)

- `core_02/scenario_registry.py` — docstring прямо ссылается на паттерн: «Mirrors the runtime marketplace pattern in `freebuff_plugin_03/runtime/registry.py`. Same philosophy: no core change when a new scenario type appears — the YAML manifest + Python subclass (in the dispatch table) do all the work».
- `_load_from_dir()` (строка 99): `for yaml_path in sorted(d.glob("*.yaml"))` → manifest → `_SCENARIO_TYPES` dispatch → Scenario ABC.

### 2.3 Прецедент №3: `plugins_04/` discover (третий случай того же паттерна)

- `scripts_01/plugin_api.py::discover()` (строка 455) — скан каталога плагинов, lifecycle DISCOVERED→LOADED→ENABLED.

### 2.4 Вывод по Направлению Б

Паттерн **«декларативный YAML + auto-discovery + dispatch-table + capability-first»** уже реализован в платформе **3 раза** (providers / scenarios / plugins) и закреплён принципом №7 архитектурного манифеста. Это означает:

1. Facade для Blueprint v3 → Forge должен **следовать этому же паттерну** (не изобретать новый механизм).
2. Внешние аналоги (Kubernetes controllers/reconcile, GitHub Actions декларативные workflows + runner, Terraform provider registry, n8n) — подтверждают правильность подхода, но **не нужны как источник дизайна**: внутренний прецедент сильнее, поскольку уже совместим с платформой (Single Source of Truth, CON-40 capability-check).

---

## 3. Что это значит для Задачи 1 (Facade design) — forward-выводы

1. **Facade нужен, но узкий:** НЕ для всех 17 ролей — только для 15 стадий цепочки (промт 70 Задача 2: «пропорционально находке, не тотально»). **Явная граница scope:** в Фазу Facade входят `explainer→lisa→risk→decomposer→architect→auditor→developer→(frontend|devops)→tester→[fixer***REMOVED***→acceptance→documenter→retrospective` (**13 ядро + frontend + devops = 15**); `response_writer` — **вне основного Facade-scope** (presale-параллельный трек, Facade-путь опционален, решается в Задаче 2 отдельно); `orchestrator`/`context_keeper` — справочные, НЕ трогаем.
2. **Сохранить §7.3 boundary:** Scenario/роли НЕ получают прямой доступ к `ForgePipeline` — только через Facade, по **явному** запросу, с фиксацией в `forge_registry.record_run()` (реализовано: `core_02/forge_registry.py` + `scripts_01/forge.py:151`).
3. **UNFORGED-семантика не меняется:** Facade даёт путь изменить статус через явный вызов, а не автоматически.
4. **Оркестратор/context_keeper — справочные:** не трогать.
5. **`resolve_pipeline()` уже умеет вычислять цепочку** (project_type/complexity) — кандидат на вход Facade.
6. **Паттерн реализации:** YAML-manifest (как providers/scenarios) + dispatch — для обратной совместимости с `ScenarioRegistry`.

## 3a. Live-верификация центральных claims (2026-08-10, basher)

- `grep -rn 'resolve_pipeline' scripts_01/ core_02/ --include='*.py' | grep -v 'def resolve_pipeline'` → **пусто** (0 prod-вызовов; единственные вызовы — `tests_09/test_blueprint_v3.py:159-174`). Центральный claim «цепочка декларативна, но не исполняется» — **подтверждён живым grep-ом**, не только чтением кода.
- `grep -rniE 'forge' core_02/scenario_registry.py core_02/wizard_lib.py | wc -l` → **0** (§7.3 boundary подтверждена на уровне кода, live).
- `grep -n 'record_run' scripts_01/forge.py core_02/forge_registry.py` → `forge.py:151` + `forge_registry.py:150` (Facade сможет фиксировать результат — готово).
- `grep -c '8a_ssa' <blueprints_v3>/registry.yaml` → **0** (дрейф: файл на диске, в реестре нет — подтверждено).
- `grep -c 'environment_doctor' <blueprints_v3>/registry.yaml` → **0** (в pipeline реестра нет — есть только в `CAPABILITIES_OVERRIDE`, blueprint_v3.py:120-145).
- `ls runtime_05/providers/*.yaml | wc -l` → **3** (freebuff / claude_code / openclaw — манифесты auto-discovery на месте).

## 4. Evidence-индекс (файл:строка)

- `registry.yaml` (blueprints_v3): секции `pipeline:` (17 ролей), `project_types.*`, `complexity_routing.*`, `categories.*`, `metadata.total_blueprints: 17`.
- `core_02/blueprint_v3.py`:56 (DEFAULT_BLUEPRINTS_DIR), :120-145 (CAPABILITIES_OVERRIDE), :147-166 (KNOWN_CAPABILITIES), :417-434 (resolve_pipeline), :236-238 (registry.yaml guard).
- `core_02/scenario_registry.py`:7-11 (mirrors providers pattern), :99 (glob *.yaml), :105-110 (dispatch).
- `freebuff_plugin_03/runtime/registry.py`:196 (load_providers_from_dir), :433 (discover), :70-71 (marketplace comment).
- `scripts_01/plugin_api.py`:455 (discover).
- `docs_10/core/ARCHITECTURE_MANIFEST.md`:45 (принцип №7 Marketplace-Ready).
- `core_02/forge_registry.py`:38 (STATUSES), :70 (реестр), record_run; `scripts_01/forge.py`:151 (registry.record_run).
- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §7.3 (Wizard↔Forge boundary), §7.5 (vkusvill_demo chain), §7.6 (gap 2: No direct Forge invocation).
- `docs_10/engineering-memory/AUDIT_WS_OS_P65_§9_V1.md` C-Forge-10/12 (grep 0 forge hits).
- `tests_09/test_blueprint_v3.py`:159-174 (единственные вызовы resolve_pipeline — только тесты).

## 5. Cross-links

- `pompts_11/071_02_prompt_architect_1_7.md` Миссия 2 (Задача 0/1/2)
- `docs_10/ROADMAP_FORGE_RECONCILIATION.md` (FR-001 v1.4 CLOSED — §2a orthogonal-STATE)
- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §7/§8/§9
- `core_02/LESSONS.md` ANTI-5, ANTI-6b, CON-8, PB-16, ANTI-7b
