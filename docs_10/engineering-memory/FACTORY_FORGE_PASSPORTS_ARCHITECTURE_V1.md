# FORGE PASSPORTS — Architecture Factory (v1.1)

| Поле | Значение |
|------|----------|
| **Документ** | FACTORY_FORGE_PASSPORTS_ARCHITECTURE_V1.md |
| **Статус** | 🏗 ARCHITECTURAL DESIGN DOCUMENT (паспорта кузен — контракты; реализация — отдельный этап) |
| **Версия** | 1.1 (переписаны под упрощённую структуру Forge по ревью промта 73) |
| **Дата** | 2026-08-11 |
| **Базируется на** | FACTORY_FORGE_ARCHITECTURE_V1.md (**v1.1** — карта 6 блоков Factory + структура Forge), промт 72 (§7 — внутреннее устройство кузен), промт 73 (ревью: карта не спускается ниже Engine), ARB Constitution (054_17), AG Constitution (055_18), ARB-REV-003 |
| **Шаблон** | 9 полей карты Forge v1.1: Mission, Input, Production Workflow, Engines, Quality Gates, Output, Artifacts, Interfaces, Memory/Knowledge |
| **Правило v1.1** | Skills / Prompts / Tools / Agents — **внутри Engines**, НЕ на карте кузни. Prompt вообще не появляется на карте Factory (внутренняя реализация Agent/Skill/Module). |

---

## 0. Как читать паспорта

Паспорт кузни — это **контракт** в терминах производственной карты v1.1: зачем кузня существует (Mission), что принимает (Input), как производит (Production Workflow), какие механизмы использует (Engines), что проверяет перед выдачей (Quality Gates), что производит (Output), какие артефакты создаёт (Artifacts), с чем связана (Interfaces), что читает и пишет в память (Memory/Knowledge).

**Уровни НЕ смешиваются:**

```
FORGE (карта v1.1)
├── Engines
│   └── Modules
│       └── Skills / Tools / Agents / Models   ← сюда спустились детали
```

Порядок документирования — по ARB-REV-003 (Required Actions 1): **сначала Architecture Review Forge** (материальная база: ARB + DIS + `dis_engine.py`), затем Governance Forge (AG + drift_check + consistency_check + B17), затем остальные пять.

---

# 1. Architecture Review Forge

## MISSION

Проверить архитектурное решение: **«Можно ли принимать это архитектурное решение?»** Превращает архитектурное предложение (Draft RFC / Design) в **проверенный вердикт** — допустить в платформу, вернуть на доработку, отклонить, отложить или потребовать эксперимент.

Это **первая материальная кузня**: всё необходимое уже существует (ARB Constitution, DIS RFC, `dis_engine.py`), реализация = связать существующие компоненты в единый workflow.

## INPUT

- Draft RFC / Architectural Proposal (проблема + предлагаемое решение);
- Архитектурный контекст: существующие компоненты, принципы Buffy;
- Constraints и Relevant Decisions;
- Organizational Memory: прошлые решения, уроки, ADR, паттерны.

## PRODUCTION WORKFLOW

```
Draft RFC / Proposal
   │
   ▼
1. Problem Validation          (существует ли проблема, правильно ли сформулирована)
2. Context Analysis            (где подсистема, какие компоненты есть)
3. Impact Analysis             (влияние на архитектуру/данные/API/память)
4. Dependency Analysis         (новые/скрытые/циклические зависимости)
5. Evolution Analysis          (что будет через 1/3/5 лет)
6. Debt Analysis               (что станет техдолгом)
7. Alternatives                (минимум 3 варианта)
8. Principle Compliance        (10 принципов Buffy)
9. Risk Assessment             (вероятность ошибки, стоимость отката)
10. Platform Intelligence      (станет ли платформа умнее)
   ▼
Verdict Generation (один из 6)
   ▼
Report Generation (12-частный отчёт + Required Actions)
   ▼
вердикт → Architecture Decision Forge (ADR) или возврат автору
```

Производственный поток, а не жёсткий pipeline: при CHANGES REQUIRED кузня может быть вызвана повторно.

## ENGINES

```
ARCHITECTURE REVIEW FORGE
└── Review Engine
      ├── Analysis        (Problem Validator, Context Analyzer, Impact Analyzer,
      │                    Dependency Analyzer, Evolution Analyzer, Debt Predictor,
      │                    Alternative Generator, Principle Checker, Risk Assessor,
      │                    Platform Intelligence Assessor — Modules шагов 1–10)
      ├── DIS             (Decision Intelligence: ARE, CAE, TDA, PC, EP, RFC Reviewer)
      └── ARB             (Architecture Review Board — механизм вердикта, 6 решений)
```

> ARB — **внутренний механизм внутри Review Engine**, а не соседняя сущность с Forge (промт 73).
> Skills / Prompts / Tools / Agents — внутри Modules (уровень Engine), на карте кузни не показываются.

## QUALITY GATES

Перед выдачей результата проверено:

- [ ***REMOVED*** Evidence Complete — все 10 шагов анализа выполнены (ни один не пропущен);
- [ ***REMOVED*** Context Complete — архитектурный контекст учтён;
- [ ***REMOVED*** Alternatives Considered — минимум 3 альтернативы рассмотрены;
- [ ***REMOVED*** Risks Assessed — риски оценены;
- [ ***REMOVED*** Вынесен ровно один вердикт из 6;
- [ ***REMOVED*** Отчёт в едином 12-частном формате;
- [ ***REMOVED*** Required Actions конкретны.

## OUTPUT

- **Architecture Review Verdict** (один из 6): APPROVED, APPROVED WITH RECOMMENDATIONS, CHANGES REQUIRED, SPIKE REQUIRED, DEFERRED, REJECTED;
- **ARB Review Report** (12-частный формат: Executive Summary → Required Actions);
- **Required Actions** (перечень действий перед следующей стадией);
- (при APPROVED) сигнал для Architecture Decision Forge → генерация ADR.

## ARTIFACTS

- `docs_10/engineering-memory/ARB_REVIEW_<DOCUMENT>.md` (эталон: ARB_REVIEW_FACTORY_FORGE_MANIFEST_V1.md);
- Findings (найденные проблемы);
- Risks;
- Recommendations;
- Verdict + Required Actions.

## INTERFACES

- **receives:** Architectural Problem, Architecture, Models, Constraints, Relevant Decisions;
- **produces:** Review Result (Verdict + Report);
- **Decision Forge** — приёмник вердикта при APPROVED;
- **Governance Forge** — источник REQUIRES ARB REVIEW (повторный вход);
- **ARB Constitution** (`pompts_11/054_17_arb_architecture_review_board.md`) — методология;
- **DIS** (`core_02/dis_engine.py`, RFC_DIS_V1) — аналитика;
- **Human:** финальное утверждение вердикта (владелец/рецензент).

## MEMORY / KNOWLEDGE

- **Читает:** прошлые ARB-вердикты (прецеденты), ADR, LESSONS (CON/ANTI), паттерны (Knowledge Graph), контекст проекта;
- **Пишет (Feedback):** вердикт + rationale (DecisionTrace), выявленные риски и техдолг, уроки о типичных ошибках, прецедент в ARB Review Registry / LESSONS.

## Evolution (заметка)

От ручного процесса → к автоматизированному DIS-ускорению (RFC Reviewer pre-screening) → к частично автоматическому вердикту с человеческим финалом. Расширение: ревью новых типов документов (Event Model, API Design, Security Architecture).

---

# 2. Architecture Governance Forge

## MISSION

Контролировать соответствие реализации утверждённой архитектуре: **«Реализовали ли мы именно ту архитектуру, которую утвердили?»** (не «хорошая ли архитектура?» — это Review).

Это **вторая материальная кузня**: база — AG Constitution + `drift_check.py` + `consistency_check.py` + B17 (Governance Layer).

## INPUT

- Approved Architecture (RFC + ADR) как Architecture Baseline;
- Implementation (код, документация, структуры данных, процессы);
- Governance Rules (принципы Buffy, правила).

## PRODUCTION WORKFLOW

```
APPROVED ARCHITECTURE (RFC + ADR)
   ▼
IMPLEMENTATION (код/доки/структуры)
   ▼
CONFORMANCE CHECK
   ├── Baseline Check
   ├── Drift Detection (Architecture + Documentation + Dependency)
   ├── Contract Check
   ├── Exception Analysis
   └── Organizational Memory Compliance
   ▼
DRIFT?
   ├── NO  → COMPLIANT (архитектура остаётся валидной)
   └── YES → Exception / Correction → Architecture Update
              └── серьёзные расхождения → REQUIRES ARB REVIEW → Review Forge
```

## ENGINES

```
ARCHITECTURE GOVERNANCE FORGE
└── Governance Engine
      ├── Baseline Checker        (Module: эталонная архитектура)
      ├── Conformance Analyzer    (Module: RFC/ADR/доки ↔ реализация)
      ├── Drift Detector          (Module: Architecture/Документация/Dependency drift)
      ├── Contract Checker        (Module: контракты/зависимости)
      ├── Exception Analyzer      (Module: исключения и workarounds)
      └── Verdict Generator       (Module: один из 5 вердиктов)
```

## QUALITY GATES

- [ ***REMOVED*** Baseline фиксирован (утверждённая архитектура доступна);
- [ ***REMOVED*** Все виды drift проверены (Architecture, Documentation, Dependency);
- [ ***REMOVED*** Вердикт — один из 5;
- [ ***REMOVED*** Required Corrections конкретны;
- [ ***REMOVED*** При REQUIRES ARB REVIEW — переход в Review Forge зафиксирован.

## OUTPUT

- **Conformance Result** (один из 5): COMPLIANT, MINOR DRIFT, MAJOR DRIFT, GOVERNANCE VIOLATION, REQUIRES ARB REVIEW;
- **Governance Report** (10-частный формат AG);
- **Required Corrections** (при отклонениях).

## ARTIFACTS

- Governance Report (10-частный формат AG);
- Conformance Records (история проверок);
- Drift Report (отклонения);
- Required Corrections.

## INTERFACES

- **receives:** Approved Architecture (RFC + ADR) + Implementation;
- **produces:** Conformance Result, Governance Report;
- **при REQUIRES ARB REVIEW →** Review Forge;
- **AG Constitution** (`pompts_11/055_18_ag_architecture_governance.md`) — методология;
- **Drift Detection** (`scripts_01/drift_check.py`), **Consistency** (`scripts_01/consistency_check.py`), **Doctor** (`scripts_01/doctor.py`) — Verifiers;
- **B17 Governance Layer** (`core_02/boundaries_v17.py`) — принуждение границ;
- **Human:** финальное утверждение MAJOR DRIFT / VIOLATION.

## MEMORY / KNOWLEDGE

- **Читает:** APPROVED RFC + ADR (Baseline), DECISIONS (`docs_10/decisions/DECISIONS.md`), принципы Buffy (AG Constitution, AGENTS.md), контекст проекта;
- **Пишет (Feedback):** вердикт + rationale, выявленные drift-паттерны (уроки для Knowledge), Conformance Records, триггер REQUIRES ARB REVIEW в Review Forge.

## Evolution (заметка)

От ручной проверки (drift_check + consistency_check как утилиты) → к машиночитаемому Conformance checker для реализаций (ARB-REV-003, Missing Capability #3); автоматический мониторинг при каждом прогоне ForgePipeline; интеграция с Evolution Forge.

---

# 3. Architecture Discovery Forge

## MISSION

Произвести **понимание того, что нужно строить** (Architectural Problem), работая ДО проектирования. Превращает сырую идею/проблему в формализованный вход для Design Forge. Не проектирует решение.

## INPUT

- Идея / проблема / запрос пользователя;
- Существующая система (если есть);
- Заинтересованные стороны (stakeholders);
- Контекст домена.

## PRODUCTION WORKFLOW

```
Problem → Discovery → Context → Requirements → Constraints → Architectural Problem
```

## ENGINES

```
ARCHITECTURE DISCOVERY FORGE
└── Discovery Engine
      ├── Problem Analysis            (Module)
      ├── Requirement Analysis        (Module)
      ├── Constraint Analysis         (Module)
      ├── Existing System Analysis    (Module)
      ├── Stakeholder Analysis        (Module)
      ├── Domain Boundary Discovery   (Module)
      ├── Existing Architecture Discovery (Module)
      └── Report Generator            (Module)
```

## QUALITY GATES

- [ ***REMOVED*** Проблема проверена (реальна, правильно сформулирована);
- [ ***REMOVED*** Требования и ограничения собраны;
- [ ***REMOVED*** Существующая система проанализирована (если есть);
- [ ***REMOVED*** Architectural Problem формализован.

## OUTPUT

- **Architectural Problem** (формализованная проблема);
- REQUIREMENTS, CONSTRAINTS;
- CURRENT STATE / TARGET STATE;
- ARCHITECTURAL CONTEXT;
- Discovery Report.

## ARTIFACTS

- Architectural Problem;
- Requirements / Constraints list;
- Current/Target State;
- Discovery Report.

## INTERFACES

- **receives:** идея/проблема + контекст домена;
- **produces:** Architectural Problem → Design Forge;
- **Knowledge Engine** (`core_02/knowledge_engine.py`, `graph_index.py`) — поиск по существующим системам;
- **Research Factory** — входные данные (похожие идеи, архитектуры);
- **Human:** подтверждение требований и ограничений.

## MEMORY / KNOWLEDGE

- **Читает:** Project memory (цели, контекст), Organizational Memory (похожие задачи);
- **Пишет (Feedback):** выявленные требования/ограничения как факты проекта.

## Evolution (заметка)

От ручного анализа → к полуавтоматическому Discovery (поиск похожих систем через knowledge_engine); автоматическое извлечение требований из задачи.

---

# 4. Architecture Design Forge

## MISSION

Произвести **архитектуру** (Architecture / Architectural Blueprint) из формализованной проблемы. Центральная производственная линия: решение «как строить».

## INPUT

- Architectural Problem (из Discovery Forge);
- Requirements, Constraints;
- Контекст и знания (паттерны, ADR, похожие архитектуры).

## PRODUCTION WORKFLOW

```
Architectural Problem → Design → Architecture / Blueprint
```

## ENGINES

```
ARCHITECTURE DESIGN FORGE
└── Design Engine
      ├── System Decomposition      (Module)
      ├── Component Design          (Module)
      ├── Boundary Design           (Module)
      ├── Responsibility Allocation (Module)
      ├── Interaction Design        (Module)
      ├── Dependency Design         (Module)
      ├── Interface Design          (Module)
      ├── Extensibility Design      (Module)
      └── Blueprint Generator       (Module)
```

## QUALITY GATES

- [ ***REMOVED*** Все компоненты выделены;
- [ ***REMOVED*** Границы и ответственность распределены;
- [ ***REMOVED*** Зависимости и интерфейсы определены;
- [ ***REMOVED*** Blueprint полный (не черновик без критичных решений).

## OUTPUT

- **System Architecture**;
- COMPONENT MODEL (компоненты и границы);
- BOUNDARIES, DEPENDENCIES, INTERACTIONS, INTERFACES;
- **ARCHITECTURAL BLUEPRINT**.

## ARTIFACTS

- Architecture Blueprint;
- Component Model;
- Interfaces & Dependencies.

## INTERFACES

- **receives:** Architectural Problem (из Discovery Forge);
- **produces:** Architecture → Modeling Forge / Review Forge;
- **Discovery Forge** (вход);
- **Review Forge** (проверка);
- **Modeling Forge** (формальное описание);
- **Knowledge** (паттерны, похожие архитектуры);
- **Human:** подтверждение ключевых архитектурных решений (декомпозиция, границы).

## MEMORY / KNOWLEDGE

- **Читает:** паттерны, ADR, похожие архитектуры (knowledge_engine, graph_index);
- **Пишет (Feedback):** проектные решения как Draft для Review Forge.

## Evolution (заметка)

От ручного проектирования → к assisted-режиму (поиск похожих архитектур); шаблоны Blueprint по типам проектов.

---

# 5. Architecture Modeling Forge

## MISSION

Произвести **формальное описание архитектуры** (Architecture Representation): модели, диаграммы, схемы, API-контракты, документация. Отделена от Design, потому что «придумать архитектуру» и «формально описать архитектуру» — разные производственные задачи.

## INPUT

- Architecture (из Design Forge);
- Решения о моделях (что моделировать).

## PRODUCTION WORKFLOW

```
Architecture → Modeling → Architecture Representation
```

## ENGINES

```
ARCHITECTURE MODELING FORGE
└── Modeling Engine
      ├── System Modeler         (Module)
      ├── Component Modeler      (Module)
      ├── Dependency Modeler     (Module)
      ├── Data Modeler           (Module)
      ├── Event Modeler          (Module)
      ├── API Modeler            (Module)
      ├── Knowledge Modeler      (Module)
      ├── Flow Modeler           (Module)
      └── Documentation Generator (Module)
```

## QUALITY GATES

- [ ***REMOVED*** Ключевые модели построены (система, компоненты, зависимости);
- [ ***REMOVED*** Диаграммы/схемы соответствуют Design;
- [ ***REMOVED*** API-контракты зафиксированы (если нужны).

## OUTPUT

- SYSTEM MODEL, COMPONENT MODEL, DEPENDENCY MODEL;
- DATA / EVENT / API / KNOWLEDGE MODEL;
- SEQUENCE / FLOW MODEL;
- DIAGRAMS, SCHEMAS, DEPENDENCY MAPS, DATA/EVENT FLOWS;
- API CONTRACTS;
- ARCHITECTURE DOCUMENTATION.

## ARTIFACTS

- Модели, диаграммы, схемы;
- API contracts;
- Architecture Documentation.

## INTERFACES

- **receives:** Architecture (из Design Forge);
- **produces:** Architecture Representation → Review Forge / Documentation;
- **Design Forge** (вход);
- **Mermaid/диаграммы** (`docs_10/visual/diagrams/`) — инструменты;
- **Human:** валидация полноты моделей.

## MEMORY / KNOWLEDGE

- **Читает:** Design, ADR, существующие модели;
- **Пишет (Feedback):** модели как каноническое описание архитектуры проекта.

## Evolution (заметка)

От ручного рисования → к автогенерации диаграмм из Blueprint (Missing Capability #1 ARB-REV-003); интеграция с Modeling-стандартами.

---

# 6. Architecture Decision Forge

## MISSION

Решить: **«Решение принято. Как его зафиксировать как часть архитектуры?»** Производит **ADR / Decision Record** — формальную фиксацию решений и их последствий.

## INPUT

- Review Verdict (из Review Forge);
- Рассмотренные альтернативы;
- Rationale (обоснование).

## PRODUCTION WORKFLOW

```
Review → Decision → ADR → Architecture Record
```

## ENGINES

```
ARCHITECTURE DECISION FORGE
└── Decision Engine
      ├── Decision Capture        (Module)
      ├── ADR Generator           (Module)
      ├── Rationale Recorder      (Module)
      ├── Alternatives Recorder   (Module)
      ├── Consequences Recorder   (Module)
      ├── Decision Linker         (Module)
      ├── Supersession Tracker    (Module)
      └── Registry Manager        (Module)
```

## QUALITY GATES

- [ ***REMOVED*** ADR сгенерирован по каноническому шаблону;
- [ ***REMOVED*** Rationale, Alternatives, Consequences зафиксированы;
- [ ***REMOVED*** Решение связано с контекстом (RFC, компоненты);
- [ ***REMOVED*** Supersession обновлён.

## OUTPUT

- **ADR** (Architecture Decision Record) — каноническая фиксация;
- DECISION REGISTRY (реестр решений);
- SUPERSESSION tracking (какие решения заменены).

## ARTIFACTS

- ADR (`docs_10/engineering-memory/decisions/ADR_*.md`);
- Decision Registry;
- Decision Graph (связи решений).

## INTERFACES

- **receives:** Review Verdict (из Review Forge);
- **produces:** ADR → Organizational Memory / Governance (Baseline);
- **Review Forge** (вход — вердикт);
- **Decision Registry** (Missing Capability #2: реестр как структура данных — будущее);
- **Human:** подтверждение финальной формулировки ADR.

## MEMORY / KNOWLEDGE

- **Читает:** вердикт, альтернативы, существующие ADR (для связей и supersession);
- **Пишет (Feedback):** ADR, связи решений, supersession — в Organizational Memory.

## Evolution (заметка)

От файлов-ADR → к Decision Registry как структуре данных (Missing Capability #2); автоматическое связывание решений (Decision Graph).

---

# 7. Architecture Evolution Forge

## MISSION

Решить: **«Не устарела ли сама архитектура?»** Производит **Evolution / Migration Plan** — анализ здоровья архитектуры и план перехода к будущей архитектуре. Не про соответствие текущей системе (это Governance), а про будущее.

## INPUT

- CURRENT ARCHITECTURE;
- Governance Reports (состояние соответствия);
- Метрики/аналитика использования;
- Горизонты 1/3/5 лет.

## PRODUCTION WORKFLOW

```
CURRENT ARCHITECTURE → EVOLUTION ANALYSIS → FUTURE ARCHITECTURE
```

## ENGINES

```
ARCHITECTURE EVOLUTION FORGE
└── Evolution Engine
      ├── Health Analyzer          (Module: здоровье архитектуры)
      ├── Evolution Analyzer       (Module: тренды, 1/3/5 лет)
      ├── Debt Tracker             (Module: техдолг)
      ├── Deprecation Analyzer     (Module: устаревание)
      ├── Scalability Analyzer     (Module: масштабируемость)
      ├── Refactoring Planner      (Module)
      ├── Migration Planner        (Module)
      ├── Version Transitioner     (Module)
      └── Future Architect         (Module)
```

## QUALITY GATES

- [ ***REMOVED*** Здоровье архитектуры оценено;
- [ ***REMOVED*** Техдолг отслежен с приоритетами;
- [ ***REMOVED*** Deprecation определён;
- [ ***REMOVED*** Migration Plan имеет горизонты;
- [ ***REMOVED*** Future Architecture описана.

## OUTPUT

- **EVOLUTION ANALYSIS** (здоровье архитектуры);
- TECHNICAL DEBT TRACKING;
- DEPRECATION ANALYSIS;
- SCALABILITY ANALYSIS;
- **MIGRATION PLAN**;
- FUTURE ARCHITECTURE (целевое состояние).

## ARTIFACTS

- Evolution Analysis;
- Technical Debt Register;
- Migration Plan;
- Future Architecture.

## INTERFACES

- **receives:** Current Architecture + Governance Reports;
- **produces:** Evolution Plan / Future Architecture;
- **Governance Forge** (вход — состояние соответствия);
- **Analytics** (метрики — `scripts_01/metrics.py`, event_log);
- **Review Forge** (новые решения по эволюции);
- **Human:** утверждение горизонтов и приоритетов миграции.

## MEMORY / KNOWLEDGE

- **Читает:** Governance Reports, метрики, историю изменений (CHANGELOG), техдолг (ARCHITECTURAL_DEBT.md);
- **Пишет (Feedback):** тренды, выявленный техдолг, паттерны устаревания → Knowledge / Idea (новый цикл).

## Evolution (заметка)

От ручного анализа → к автоматическим метрикам здоровья архитектуры; интеграция с горизонтами 1/3/5 лет; автоматический вход в новый цикл Idea → Research (замкнутый цикл).

---

## 8. Сводная таблица кузен Architecture Factory

| # | Кузня | INPUT | OUTPUT | Приоритет (ARB-REV-003) |
|---|-------|-------|--------|--------------------------|
| 1 | Architecture Review Forge | Draft RFC / Proposal | Verdict + Review Report | 🥇 1-я материальная |
| 2 | Architecture Governance Forge | APPROVED RFC + Implementation | Conformance Result + 5 вердиктов | 🥈 2-я материальная |
| 3 | Architecture Discovery Forge | Идея / Проблема | Architectural Problem | 🥉 при каркасе Factory |
| 4 | Architecture Design Forge | Architectural Problem | Architecture / Blueprint | 🥉 при каркасе Factory |
| 5 | Architecture Modeling Forge | Architecture | Models / Diagrams / Docs | после Design |
| 6 | Architecture Decision Forge | Review Verdict | ADR / Decision Record | после Review |
| 7 | Architecture Evolution Forge | Current Architecture + Governance | Evolution / Migration Plan | последний этап |

---

## 9. Открытые вопросы

1. **Паспорт ↔ код:** как паспорт кузни будет представлен в коде (dataclass `ForgePassport`? YAML-манифест в `runtime_05/factories/`?) — решение на этапе реализации.
2. **Хранение паспортов:** рядом с документами (`docs_10/`) или как machine-readable контракт (реестр Factory/Forge из ARB-REV-003 Required Action 4)?
3. **Роли Blueprint v3 ↔ кузни:** каждая роль (developer, architect…) станет Engine/Module какой кузни? (Матрица «роль → Engine/Module/Forge» — Required Action 3 ARB-REV-003, отдельный документ.)
4. **Глубина паспортов:** достаточно ли 9 полей карты v1.1, или для материальных кузен (Review, Governance) нужны доп. разделы на уровне Engines (примеры входных/выходных JSON)?

---

*Документ переписан под упрощённую структуру Forge v1.1 (по ревью промта 73): 9 полей карты (Mission, Input, Production Workflow, Engines, Quality Gates, Output, Artifacts, Interfaces, Memory/Knowledge), Skills/Prompts/Tools — уровень Engine, не карта кузни. Базируется на FACTORY_FORGE_ARCHITECTURE_V1.md v1.1, ARB-REV-003, конституциях ARB/AG. Статус: ARCHITECTURAL DESIGN DOCUMENT — паспорта являются контрактами, реализация — отдельный этап.*
