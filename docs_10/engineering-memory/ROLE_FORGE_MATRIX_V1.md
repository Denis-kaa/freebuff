# ROLE → FORGE MATRIX — роль Blueprint v3 → Engine/Module кузни

| Поле | Значение |
|------|----------|
| **Документ** | ROLE_FORGE_MATRIX_V1.md |
| **Статус** | 🏗 ARCHITECTURAL DESIGN DOCUMENT (матрица соответствия ролей — контракт для паспортов кузен) |
| **Версия** | 1.0 (2026-08-11) |
| **Закрывает** | **Required Action 3 ARB-REV-003** («матрица „роль Blueprint v3 → Engine/Module/Forge“ для всех 17+ ролей, критерии §6») + Open Question 3 паспортов + Open Question 4 карты v1.1 («Роль vs Forge») |
| **Базируется на** | FACTORY_FORGE_ARCHITECTURE_V1.md (v1.1: §6 критерии, §17.1 lifecycle, §10 Code Factory), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (v1.1: Engines/Modules 7 кузен), SCENARIO_ENGINE_DESIGN_V1.md (§10: 14 ролей → capabilities), ARB-REV-003 (RA3) |
| **Данные** | `blueprints_v3/registry.yaml` (18 ролей: id/type/condition/dependencies/outputs), `core_02/forge_facade.py` (LIGHT/HEAVY/CONDITIONAL/REFERENCE), `core_02/blueprint_v3.py` (CAPABILITIES_OVERRIDE, 18 ролей) |

---

## 1. Executive Summary

**Вопрос:** каждая роль Blueprint v3 (17+) — это Forge, Engine или Module какой кузни?

**Ответ (кратко):** **ни одна роль не является Forge сама по себе.** Все 18 ролей — **Engine или Module** внутри ~8 Forge двух материальных Factory (Architecture + Code) + 2 будущих (Research, Content) + платформенные сервисы. Это соответствует правилу v1.1 §6: Forge = способность с собственным производственным результатом; роль без собственного результата — Engine/Module.

**Ключевые решения:**

1. **6 ролей → Architecture Factory** (explainer→Discovery, risk→Review, decomposer/architect→Design, auditor→Review, retrospective→Evolution);
2. **6 ролей → Code Factory** (developer/frontend→Generation, devops→Release, tester→Testing, fixer→Debugging, acceptance→Code Review);
3. **documenter → Content Factory** (Writing → Documentation Engine);
4. **lisa → Research Factory** (будущая Estimation Engine — оценки нет в 7 кузен Architecture);
5. **orchestrator/context_keeper/environment_doctor → НЕ кузни** (Scenario Engine / Platform Memory / Platform Verifier).

**Вердикт:** матрица даёт машиночитаемое соответствие «роль → Forge/Engine/Module», которое ложится в паспорта кузен (поле Engines) и в Scenario Engine (CapabilityRef: `{kind: engine, factory, engine***REMOVED***`). Зафиксированы расхождения с v1.1 §17.1 (explainer, risk, decomposer — уточнены по материальным модулям; documenter — открытый вопрос) — см. §6. **SCENARIO_ENGINE_DESIGN §10 согласован с матрицей 2026-08-11** (строки explainer/risk/decomposer/lisa обновлены).

---

## 2. Исходные данные: 18 ролей Blueprint v3

Источник: `blueprints_v3/registry.yaml` + `CAPABILITIES_OVERRIDE` (`blueprint_v3.py`). Классификация Facade — из `forge_facade.py`.

| # | Роль | Тип (registry) | Condition | Зависит от | Outputs | Режим Facade |
|---|------|----------------|-----------|------------|---------|--------------|
| 1 | orchestrator | management | always | — | (entry) | REFERENCE |
| 2 | context_keeper | management | always | — | manifest.md | REFERENCE |
| 3 | explainer | analysis | always | — | brief.md, parsed_requirements.md | LIGHT |
| 4 | lisa | estimation | always | explainer | lisa_report.md | LIGHT |
| 5 | risk | estimation | always | lisa | risk_matrix.md | LIGHT |
| 6 | decomposer | architecture | always | risk | decomposition.md, module_list.md, integration_topology.md | LIGHT |
| 7 | architect | architecture | always | decomposer | architecture.md, adr/*.md, contracts.yaml | LIGHT |
| 8 | auditor | validation | always | architect | audit_report.md | LIGHT |
| 9 | response_writer | communication | always | auditor | client_response.md | (presale, вне Facade) |
| 10 | developer | implementation | always | auditor | src/**/*.py, tests/**/*.py, migrations/*.py | HEAVY |
| 11 | frontend | implementation | project_type == "web" | developer | frontend/**/*.tsx, *.css, *.html | CONDITIONAL |
| 12 | devops | infrastructure | always | developer | Dockerfile, docker-compose.yml, .github/workflows/*.yml, terraform/*.tf | CONDITIONAL (always) |
| 13 | tester | validation | always | developer, frontend | tests/**/*.py, mutation_test_results.md | HEAVY |
| 14 | fixer | implementation | on_test_fail | tester | bug_fixes.md, regression_tests.py | HEAVY |
| 15 | acceptance | validation | always | tester, fixer | acceptance_report.md, validation.md | HEAVY |
| 16 | documenter | delivery | always | acceptance | README.md, PORTFOLIO_CASE.md, TG_POST.md, API_DOCS.md, ARCHITECTURE.md | LIGHT |
| 17 | retrospective | evolution | always | documenter | retrospective_report.md, LESSONS.md, lisa_calibration.yaml | LIGHT |
| 18 | environment_doctor | (diagnose)¹ | — | — | (доктор-отчёт) | (вне Facade) |

> ¹ `environment_doctor` отсутствует в `registry.yaml` — он определён только в `CAPABILITIES_OVERRIDE` (`core_02/blueprint_v3.py`, capabilities: diagnose/validate/report). Его «тип» взят из capabilities, не из registry.

---

## 3. Критерии маппинга (v1.1 §6)

| Критерий | Решение |
|----------|---------|
| Роль = **Forge**? | **Нет.** Ни одна роль не имеет самостоятельного производственного результата уровня кузни — все являются шагами внутри кузен (правило «одна Forge = один результат», §5 карты v1.1) |
| Роль = **Engine**? | Да, если роль — целый производственный процесс внутри Forge (напр. developer = Generation Engine) |
| Роль = **Module**? | Да, если роль — отдельный шаг анализа Engine (напр. risk = Risk Assessor внутри Review Engine) |
| Роль **вне кузен**? | Управление/координация/память/диагностика: orchestrator, context_keeper, environment_doctor |

**Обобщённое правило маппинга:**

```
Роль → Factory (по классу работы)
     → Forge (кузня, внутри которой живёт)
     → Engine (производственный процесс роли)
     → Module (отдельные шаги процесса, если роль = подшаг)
```

---

## 4. МАТРИЦА: роль → Factory / Forge / Engine / Module

**Основная матрица (18 ролей):**

| # | Роль | Factory | Forge | Engine | Module (кандидат) | Обоснование |
|---|------|---------|-------|--------|-------------------|-------------|
| 1 | orchestrator | — (Scenario Engine) | — | — | — | Координация сценария = Scenario Engine (§14 карты v1.1), НЕ кузня |
| 2 | context_keeper | — (Platform: Memory) | — | Memory Engine | — | Сжатие контекста/manifest — Platform Service (Memory/Knowledge) |
| 3 | explainer | **Architecture** | **Discovery Forge** | Discovery Engine | **Requirement Analysis** | brief.md/parsed_requirements.md = разбор требований → Module Discovery Engine |
| 4 | lisa | **Research** (будущая) | Research Forge | Estimation Engine | LISA Estimator | Оценка сложности — нет в 7 кузен Architecture; будущая Research/Estimation |
| 5 | risk | **Architecture** | **Review Forge** | Review Engine | **Risk Assessor** (шаг 9 ARB) | risk_matrix.md = оценка рисков → Module ARB-шага 9 |
| 6 | decomposer | **Architecture** | **Design Forge** | Design Engine | **System Decomposition + Boundary Design** | decomposition.md/module_list/integration_topology = системная декомпозиция |
| 7 | architect | **Architecture** | **Design Forge** | Design Engine | **Blueprint Generator** (+ Component Design) | architecture.md/contracts.yaml = проектирование архитектуры |
| 8 | auditor | **Architecture** | **Review Forge** | Review Engine | **Analysis / Principle Checker** | audit_report.md = архитектурный аудит (шаги ARB 1–10) |
| 9 | response_writer | **Content** (будущая) | Writing Forge | Writing Engine | Response Writer | client_response.md = контент; presale-трек вне Facade |
| 10 | developer | **Code** | **Generation Forge** | Generation Engine | Code Generator | src/**/*.py = генерация кода |
| 11 | frontend | **Code** | **Generation Forge** | Generation Engine | Frontend Generator | frontend/**/*.tsx = генерация UI (условная: web) |
| 12 | devops | **Code** | **Release Forge** | Release Engine | Deploy / Infra Configurator | Dockerfile/workflows/terraform = деплой-инфраструктура |
| 13 | tester | **Code** | **Testing Forge** | Testing Engine | Test Runner (+ Mutation Analyzer) | tests/**/mutation = тестирование |
| 14 | fixer | **Code** | **Debugging Forge** | Debugging Engine | Bug Fixer | bug_fixes.md/regression = исправление багов (on_test_fail) |
| 15 | acceptance | **Code** | **Code Review Forge** | Code Review Engine | Acceptance Verifier | acceptance_report/validation = приёмочное ревью |
| 16 | documenter | **Content** (или Code) | Writing Forge (или Documentation Forge) | Documentation Engine | Doc Generator | README/API_DOCS = документация (расхождение — §6) |
| 17 | retrospective | **Architecture** | **Evolution Forge** | Evolution Engine | Health Analyzer / Feedback | LESSONS/lisa_calibration = обратная связь, эволюция |
| 18 | environment_doctor | — (Platform: Quality) | — | Verifier Engine | Env Doctor | Диагностика окружения = Platform Verifier (doctor.py) |

**Сводка по Factory:**

| Factory | Роли | Кол-во |
|---------|------|--------|
| **Architecture Factory** | explainer, risk, decomposer, architect, auditor, retrospective | 6 |
| **Code Factory** | developer, frontend, devops, tester, fixer, acceptance | 6 |
| **Content Factory** (будущая) | response_writer, documenter | 2 |
| **Research Factory** (будущая) | lisa | 1 |
| **Вне Factory (Platform/Scenario)** | orchestrator, context_keeper, environment_doctor | 3 |

---

## 5. Детальный разбор ключевых маппингов

### 5.1 Architecture Factory (6 ролей)

```
ARCHITECTURE FACTORY
├── Discovery Forge
│   └── Discovery Engine
│       └── Module: Requirement Analysis      ← explainer (brief.md, parsed_requirements.md)
├── Design Forge
│   └── Design Engine
│       ├── Module: System Decomposition + Boundary Design  ← decomposer
│       └── Module: Blueprint Generator       ← architect (architecture.md, contracts.yaml)
├── Review Forge
│   └── Review Engine (Analysis / DIS / ARB)
│       ├── Module: Risk Assessor (шаг 9)     ← risk (risk_matrix.md)
│       └── Module: Analysis / Principle Checker ← auditor (audit_report.md)
└── Evolution Forge
    └── Evolution Engine
        └── Module: Health Analyzer / Feedback ← retrospective (LESSONS.md)
```

**Обоснование:** модули Discovery/Design/Review/Evolution Engine берутся из паспортов v1.1 (FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md). Роли архитектурного трека (explainer→decomposer→architect→auditor) — это **линейная цепочка внутри одной Architecture Factory**, что совпадает с их registry-зависимостями (explainer→lisa→risk→decomposer→architect→auditor).

### 5.2 Code Factory (6 ролей)

```
CODE FACTORY (v1.1 §10)
├── Generation Forge → Generation Engine
│   ├── Module: Code Generator     ← developer (src/**/*.py)
│   └── Module: Frontend Generator ← frontend (условно: project_type == "web")
├── Release Forge → Release Engine
│   └── Module: Deploy/Infra       ← devops (Dockerfile, workflows, terraform)
├── Testing Forge → Testing Engine
│   └── Module: Test Runner        ← tester (tests/**, mutation)
├── Debugging Forge → Debugging Engine
│   └── Module: Bug Fixer          ← fixer (on_test_fail)
└── Code Review Forge → Code Review Engine
    └── Module: Acceptance Verifier ← acceptance (acceptance_report.md)
```

**Обоснование:** developer/frontend/devops/tester/fixer/acceptance — HEAVY-роли (полный цикл ForgePipeline через `initiate_forge`), их outputs — код/тесты/деплой. Это ядро Code Factory (v1.1 §10: Planning/Generation/Testing/Debugging/Code Review/Release/Documentation).

### 5.3 Будущие Factory (3 роли)

- **lisa → Research Factory → Estimation Engine** (будущее): оценка сложности проекта — производственный класс, которого нет в 7 кузен Architecture (там Discovery→Design→…→Evolution, без оценки). Research Factory из v1.1 §11 даёт «исследовать/оценить». **Материального дома сегодня нет.**
- **response_writer → Content Factory → Writing Engine** (будущее): client_response.md — контент, presale-трек, вне Facade-scope (REFERENCE-like). Content Factory из v1.1 §12 (Writing Forge).
- **documenter → Content Factory → Documentation Engine** (частично материален): README/API_DOCS/ARCHITECTURE — документация. Расхождение с Code Factory Documentation Forge — см. §6.

### 5.4 Роли вне кузен (3)

| Роль | Почему не кузня | Куда |
|------|-----------------|------|
| **orchestrator** | Координация производственного потока, не производство результата | **Scenario Engine** (композитор, SCENARIO_ENGINE_DESIGN_V1.md) — начало/статус/следующий шаг = исполнение сценария |
| **context_keeper** | Сжатие контекста, manifest — управление памятью | **Platform Service: Memory/Knowledge** (memory_store.py, context_manager.py) |
| **environment_doctor** | Диагностика окружения (диагноз, не производство) | **Platform Verifier** (doctor.py — уже Verifier в Quality System карты v1.1 §4) |

---

## 6. Расхождения с v1.1 §17.1 (SCENARIO_ENGINE_DESIGN §10 — согласован 2026-08-11)

Матрица (этот документ) уточняет предварительные группировки. Расхождения с §17.1 (lifecycle-группировка): зафиксированы 3 материальных уточнения (explainer, risk, decomposer) + 1 открытый вопрос (documenter). Строки 1–3 **уже согласованы** с SCENARIO_ENGINE_DESIGN §10 (обновлён 2026-08-11: explainer → Architecture (Discovery), risk → Architecture (Review), decomposer → Architecture (Design)); остаётся расхождение с самим §17.1 карты v1.1, где эти роли сгруппированы как «Research (разведка)».

| # | Роль | v1.1 §17.1 (lifecycle; §10 согласован 2026-08-11) | Эта матрица | Обоснование |
|---|------|------------------------------------------|-------------|-------------|
| 1 | **explainer** | Research (разведка) | **Architecture → Discovery Forge → Requirement Analysis** | brief.md/parsed_requirements.md = разбор ТЗ/требований = Module Requirement Analysis Discovery Engine. «Разведка» — lifecycle-группировка; материальный модуль — в Discovery Forge |
| 2 | **risk** | Research (разведка) | **Architecture → Review Forge → Risk Assessor** | risk_matrix.md = оценка рисков = Module шага 9 ARB (Review Engine). Это сильный материальный маппинг; «разведка» — слишком широко |
| 3 | **decomposer** | Research (разведка) | **Architecture → Design Forge → System Decomposition** | decomposition.md/module_list/integration_topology — это буквально модуль System Decomposition Design Engine |
| 4 | **documenter** | Content (Documentation) | **Content → Writing Forge → Documentation Engine** (или Code → Documentation Forge) | v1.1 §10 Code Factory перечисляет Documentation Forge; SCENARIO_ENGINE_DESIGN §10 — Content. **Требует решения** (см. §8 Q1) |

**Позиция матрицы:** маппинг должен опираться на **материальные модули кузен** (паспорта), а не на lifecycle-группировку §17.1. Для explainer/risk/decomposer материальные модули — в Architecture Factory (Discovery/Review/Design), поэтому матрица уточняет §17.1. ✅ **SCENARIO_ENGINE_DESIGN §10 обновлён по этой матрице 2026-08-11** (строки explainer/risk/decomposer/lisa) — расхождение между этими двумя документами закрыто; остаётся только расхождение матрицы с §17.1 (by design, lifecycle vs Factory).

---

## 7. Что даёт матрица

### 7.1 Для паспортов кузен (поле Engines)

Паспорт кузни v1.1 (9 полей) получает конкретизацию поля **Engines**:

```yaml
# runtime_05/factories/architecture/review.yaml (пример из FORGE_PASSPORT_CODE_REPRESENTATION)
forge_id: review
engines:
  - review_engine          # Modules: Risk Assessor ← роль risk; Analysis ← роль auditor
```

Матрица — источник «какие роли какая кузня исполняет» → Engine/Module наполнение паспортов.

### 7.2 Для Scenario Engine (CapabilityRef)

SCENARIO_ENGINE_DESIGN_V1.md §10 давал предварительную таблицу (14 ролей → Factory). Эта матрица — **полная и уточнённая** версия: добавляет response_writer, environment_doctor, orchestrator, context_keeper + уточняет risk/decomposer. CapabilityRef:

```yaml
capability:
  kind: engine
  factory: architecture
  forge: review
  engine: risk_assessor        # Module роли risk
```

### 7.3 Для классификации Facade

Режимы run_chain (LIGHT/HEAVY/CONDITIONAL) — **не про Factory**, а про способ исполнения:

| Режим | Значение | Роли |
|-------|----------|------|
| LIGHT (check_only) | Роль проверяется RoleArtifactValidator | explainer, lisa, risk, decomposer, architect, auditor, documenter, retrospective |
| HEAVY (full_cycle) | Полный ForgePipeline через initiate_forge | developer, tester, fixer, acceptance |
| CONDITIONAL | Условие (web / always) | frontend, devops |
| REFERENCE / вне | Не инициируют Forge | orchestrator, context_keeper, response_writer, environment_doctor |

**Вывод:** LIGHT-роли — аналитические (Architecture/Research/Content), HEAVY — производственные (Code). Режим определяется классом работы, а не фабрикой.

---

## 8. Открытые вопросы

1. **documenter — Content или Code?** v1.1 §10 Code Factory содержит Documentation Forge; SCENARIO_ENGINE_DESIGN §10 и v1.1 §17.1 — Content. **Рекомендация:** documenter → Content Factory (Writing → Documentation Engine), т.к. README/API_DOCS/портфолио — контентная документация; Code Factory Documentation Forge — для технической документации кода (интеграции). Решить при паспортах Content/Code Factory.
2. **lisa — новая кузня?** Если оценка сложности — самостоятельный производственный результат, Research Factory может получить Estimation Forge (а не Engine). Проверить при паспортах Research Factory (правило «7 кузен проверить» v1.1 §7.2). 📋 **Промежуточный шаг сделан:** `lisa_estimator` зарегистрирован как Missing Capability #7 (§20 карты) с промтом на реализацию `pompts_11/076_13_lisa_estimator_capability.md` (Estimation Engine → Tool; решение Forge/Engine — при паспортах).
3. **orchestrator vs Scenario Engine:** зафиксировать, что orchestrator-роль ≡ исполнение Scenario (начало/статус/next/rollback — методы ScenarioRun). Обновить SCENARIO_ENGINE_DESIGN §13 (примеры) ссылкой на эту матрицу.
4. **Дублирование ролей `roles.py` (Collab Roles Engine):** `scripts_01/roles.py` (STANDARD_ROLES: developer/reviewer/documenter/researcher/archiver/orchestrator) — это **роли участников**, НЕ Blueprint v3 производственные роли. Не смешивать: RoleEngine — коллаборация (кто что может), Blueprint v3 — производство (что выполняется).

---

## 9. Вердикт

**Матрица построена: 18 ролей Blueprint v3 → Engine/Module 8 кузен двух Factory + 2 будущих + 3 платформенных.**

- ✅ **Ни одна роль ≠ Forge** — правило v1.1 §6 соблюдено (роли — Engine/Module).
- ✅ **6 ролей → Architecture Factory** (Discovery/Design/Review/Evolution) с точными модулями паспортов.
- ✅ **6 ролей → Code Factory** (Generation/Release/Testing/Debugging/Code Review) — соответствие v1.1 §10.
- ✅ **3 роли → будущие Factory** (lisa→Research, response_writer/documenter→Content).
- ✅ **3 роли вне кузен** (orchestrator→Scenario Engine, context_keeper→Memory, environment_doctor→Verifier).
- 🟡 **Расхождения с §17.1 зафиксированы (§6):** explainer/risk/decomposer уточнены по материальным модулям (**✅ SCENARIO_ENGINE_DESIGN §10 согласован 2026-08-11**); documenter требует решения (§8 Q1).

**Следующий шаг:** внести маппинг в паспорта кузен (поле Engines, раздел «Роли → Engine/Module»); решить Q1 (documenter). SCENARIO_ENGINE_DESIGN §10 — ✅ уже согласован (2026-08-11).

---

*Документ построен на данных: blueprints_v3/registry.yaml (18 ролей), core_02/forge_facade.py (классификация), core_02/blueprint_v3.py (capabilities), FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md (Engines/Modules кузен), карта v1.1 (§6/§10/§17.1). Статус: ARCHITECTURAL DESIGN DOCUMENT — контракт для паспортов и Scenario Engine.*
