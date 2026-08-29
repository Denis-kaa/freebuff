PROMPT — REPOSITORY ORGANIZATION & REFACTORING FORENSICS

РОЛЬ

Ты — Principal Software Architect + Repository Structure Architect + Refactoring Strategist.

Твоя задача — исследовать существующий repository и определить, как организовать его структуру так, чтобы код, документация, конфигурации, runtime-компоненты, проекты, эксперименты и архитектурные материалы имели чёткие границы и находились на своих местах.

Это НЕ задача немедленного рефакторинга.

Сначала:

> понять текущий хаос → восстановить принадлежность компонентов → определить границы → предложить целевую структуру → определить безопасный план миграции.




---

1. ГЛАВНАЯ ПРОБЛЕМА

Repository развивался органически.

Изначально возникали отдельные идеи и эксперименты.

Затем:

идея
 ↓
эксперимент
 ↓
прототип
 ↓
архитектурная концепция
 ↓
реализация
 ↓
новая идея
 ↓
новый компонент
 ↓
новая архитектура
 ↓
ещё одна реализация

В результате разные уровни системы могли оказаться перемешаны:

код
документация
архитектура
эксперименты
проекты
промпты
runtime
plugins
scripts
research
legacy
tests
data

Задача — не просто красиво разложить файлы, а понять архитектурную принадлежность каждого класса компонентов.


---

2. КЛЮЧЕВОЙ ПРИНЦИП

Не начинай с:

> «Мне нравится такая структура папок».



Начни с:

> «Что это за компонент, кому он принадлежит, какую ответственность имеет и с чем связан?»



Для каждого значимого компонента определить:

WHAT
  ↓
RESPONSIBILITY
  ↓
OWNER / DOMAIN
  ↓
DEPENDENCIES
  ↓
LIFECYCLE
  ↓
RUNTIME ROLE

Только после этого проектировать папки.


---

3. ИССЛЕДОВАТЬ ВЕСЬ REPOSITORY

Не ограничивайся верхними каталогами.

Обязательно исследовать:

Python-код;

scripts;

core;

runtime;

plugins;

projects;

tests;

configs;

YAML;

JSON;

databases;

documentation;

architecture documents;

ADR;

prompts;

research;

experiments;

prototypes;

legacy;

generated files;

operational scripts.


Если директория кажется «просто набором файлов» — выясни её происхождение и назначение.


---

4. ОСОБО ИССЛЕДОВАТЬ ДОКУМЕНТАЦИЮ

Нужно определить:

Какие документы являются:

CANONICAL ARCHITECTURE
ARCHITECTURAL DECISION
SPECIFICATION
CONTRACT
IMPLEMENTATION GUIDE
OPERATIONAL DOC
RESEARCH
EXPERIMENT
DESIGN DRAFT
PROMPT
AUDIT
HISTORICAL / LEGACY

Не смешивать их.

Например:

architecture/
    canonical/

adr/
contracts/
specs/
research/
experiments/
audits/
prompts/

Но это только пример.

Не копируй эту структуру автоматически.

Определи структуру исходя из реального repository.


---

5. КОД И ДОКУМЕНТАЦИЯ

Отдельно проверить:

> Где документация лежит рядом с кодом?



> Где она находится отдельно?



> Где это оправдано?



> Где это создаёт путаницу?



Нужно определить оптимальный принцип:

CODE
DOCUMENTATION
TESTS
CONFIG

должны ли быть:

Вариант A

module/
├── code
├── tests
└── docs

или:

Вариант B

src/
tests/
docs/

или:

Вариант C

гибридная модель.

Не выбирать заранее.

Определи по характеру проекта.


---

6. ОСОБО ПРОАНАЛИЗИРОВАТЬ PROJECTS

Это критически важно.

В repository есть:

projects_17/

и внутри реальные проекты.

Нужно определить:

> Что такое Project архитектурно?



И где должен находиться:

project
project configuration
project artifacts
project-specific agents
project-specific scenarios
project-specific prompts
project research
project documentation
project runtime
project data

Нельзя автоматически смешивать:

> код платформы



и

> код конкретного проекта пользователя.




---

7. PLATFORM VS PROJECT

Построить чёткую границу:

PLATFORM
│
├── Core
├── Intelligence
├── Agents
├── Runtime
├── Factories
├── Forge
├── Scenario
├── Memory
├── Knowledge
├── Plugins
└── ...

и:

PROJECT
│
├── Project State
├── Project Knowledge
├── Project Artifacts
├── Project Scenarios
├── Project Agents
├── Project Tasks
└── ...

Но опять же:

это гипотеза для проверки, а не готовая структура.


---

8. CORE VS SERVICES VS RUNTIME

Особенно тщательно разобрать существующие:

core_02/
scripts_01/
runtime_05/

Нужно понять:

почему они существуют;

почему именно так названы;

историческая это структура или архитектурная;

есть ли реальные границы;

какие зависимости между ними;

что является core;

что является service;

что является runtime;

что является CLI;

что является infrastructure.


Определить:

> Какие каталоги являются архитектурными слоями, а какие — историческими контейнерами?



Это очень важный вопрос.


---

9. FACTORY / FORGE / SCENARIO

Использовать результаты предыдущего forensic-прохода.

Проверить, где сейчас физически находятся:

Factory
Forge
Scenario
Agent
Skill
Tool

и определить:

> Должны ли они физически находиться рядом?



или:

factories/
forge/
scenarios/
agents/
skills/
tools/

или другая модель.

Особенно проверить:

> Не создаём ли мы физическую структуру, которая противоречит логической архитектуре?




---

10. INTELLIGENCE / BRAIN

Отдельно найти всё, что относится к:

Intelligence
Reasoning
Planning
Decision
Context
Memory
Knowledge
Learning
Agent collaboration
Orchestration

Даже если оно сейчас разбросано по разным папкам.

Создать карту:

CURRENT INTELLIGENCE COMPONENTS

и показать:

файл → функция → ответственность

После этого определить:

> Может ли это стать единым architectural domain?




---

11. AGENT ECOSYSTEM

Построить карту:

Agents
Agent roles
Agent runtimes
Agent prompts
Agent skills
Agent tools
Agent state
Agent memory
Agent orchestration
Agent communication

Проверить, что сейчас физически перемешано.

Особенно важно:

> Не превратился ли repository в ситуацию, когда Agent implementation находится в одном месте, prompt в другом, runtime в третьем, а configuration в четвёртом — без понятного контракта между ними?



Если да — показать.


---

12. PROMPTS

Отдельно провести аудит промптов.

Разделить:

SYSTEM PROMPTS
AGENT PROMPTS
ROLE PROMPTS
DEVELOPMENT PROMPTS
RESEARCH PROMPTS
ARCHITECTURE PROMPTS
EXPERIMENTAL PROMPTS
HISTORICAL PROMPTS

Определить:

> Какие из них являются runtime assets?



А какие:

> документацией процесса разработки?



Это принципиально разные вещи.


---

13. DATA / STORAGE

Исследовать:

data_13/
context_12/
*.db
*.yaml
*.json

Определить:

runtime state;

persistent application data;

registry;

cache;

test data;

fixtures;

project data;

generated artifacts;

temporary data.


Нельзя просто собрать всё в data/, если эти вещи имеют разные lifecycle и ownership.


---

14. EXPERIMENTS VS PRODUCTION

Найти:

prototype
demo
experimental
research
draft
legacy
deprecated

И определить:

> Что из этого всё ещё является production capability?



> Что является исследовательским материалом?



> Что можно удалить?



> Что нельзя удалять?



> Что нужно изолировать?




---

15. КРИТИЧЕСКИЙ АНАЛИЗ: ИСТОРИЧЕСКИЙ МУСОР VS АРХИТЕКТУРНАЯ ЦЕННОСТЬ

Не считать старым автоматически ненужным.

Для каждого подозрительного компонента:

ACTIVE
DEPRECATED
EXPERIMENTAL
HISTORICAL
DUPLICATE
ORPHANED
UNKNOWN

И только потом рекомендовать:

KEEP
MOVE
MERGE
DEPRECATE
ARCHIVE
DELETE


---

16. DUPLICATION ANALYSIS

Найти:

одинаковые функции;

дублирующие registry;

похожие managers;

повторяющиеся adapters;

несколько memory implementations;

несколько orchestration mechanisms;

несколько event systems;

несколько agent runners;

одинаковые concepts с разными названиями.


Но не объединять автоматически.

Определить:

> действительно ли это duplication или разные уровни abstraction.




---

17. DEPENDENCY ANALYSIS

Для каждого крупного домена определить:

WHO DEPENDS ON WHOM

Например:

UI
 ↓
API
 ↓
Application
 ↓
Domain
 ↓
Infrastructure

или фактическую модель.

Нужно обнаружить:

circular dependencies;

imports из project в core;

core зависимый от demo;

production код зависимый от research;

runtime зависимый от documentation;

scripts импортирующие внутренности напрямую.



---

18. ЦЕЛЕВАЯ СТРУКТУРА

После forensic analysis предложить:

TARGET REPOSITORY STRUCTURE

Например:

repository/
│
├── platform/
│   ├── core/
│   ├── intelligence/
│   ├── agents/
│   ├── factories/
│   ├── forge/
│   ├── scenarios/
│   ├── memory/
│   ├── knowledge/
│   ├── runtime/
│   └── plugins/
│
├── applications/
│
├── projects/
│
├── infrastructure/
│
├── tests/
│
├── docs/
│
├── research/
│
├── experiments/
│
└── tools/

НЕ КОПИРОВАТЬ ЭТУ СТРУКТУРУ.

Это лишь иллюстрация того, какого рода результат требуется.

Твоя задача — построить структуру, основанную на реальном repository.


---

19. ПРИНЦИП «ОДНА ОТВЕТСТВЕННОСТЬ — ОДНО МЕСТО»

Для каждого архитектурного понятия определить canonical home.

Например:

Scenario
→ одно canonical место

Factory
→ одно canonical место

Agent
→ одно canonical место

Skill
→ одно canonical место

Tool
→ одно canonical место

Если существуют несколько реализаций одного понятия:

объяснить почему.


---

20. CODE ↔ DOCUMENTATION BINDING

Это особенно важно с учётом нашего предыдущего разговора.

Предложить механизм связи:

Architecture concept
        ↓
Contract
        ↓
Implementation
        ↓
Test
        ↓
Evidence

И определить:

> Можно ли использовать metadata / tags / IDs для связывания документации и кода?



Например:

@domain: intelligence
@component: project_state
@contract: CI-PROJECT-STATE-001

или:

[ARCH:INTELLIGENCE***REMOVED***
[CONTRACT:CI-001***REMOVED***
[DOMAIN:PROJECT***REMOVED***

Но не внедрять это сейчас.

Нужно исследовать целесообразность.


---

21. ИДЕЯ ТЕГОВ ДЛЯ ДОКУМЕНТОВ

Отдельно оценить концепцию:

> Добавлять структурированные metadata/tags к разделам и абзацам документации, чтобы потом связывать их с кодом, контрактами, тестами и графом знаний.



Исследовать:

полезность;

стоимость;

где применять;

где НЕ применять;

насколько это совместимо с существующим Knowledge/Graph;

можно ли строить provenance graph.


Например:

DOC
 ↓
SECTION
 ↓
CONCEPT
 ↓
CONTRACT
 ↓
CODE SYMBOL
 ↓
TEST
 ↓
RUNTIME BEHAVIOR

Дать рекомендацию:

DO
DO WITH LIMITS
DON'T


---

22. MIGRATION PLAN

После проектирования структуры создать безопасный план миграции.

Не:

> «переместить 400 файлов».



А:

Phase 0 — Inventory
Phase 1 — Freeze boundaries
Phase 2 — Establish canonical locations
Phase 3 — Move documentation
Phase 4 — Move low-risk code
Phase 5 — Fix imports
Phase 6 — Tests
Phase 7 — Runtime validation
Phase 8 — Deprecate old paths
Phase 9 — Cleanup

Для каждого этапа:

что переносим;

почему;

dependencies;

risk;

rollback;

validation.



---

23. НИЧЕГО НЕ ЛОМАТЬ

На этом этапе:

НЕ выполнять массовый рефакторинг.

Сначала предоставить:

> Refactoring Blueprint



и только после отдельного утверждения начать migration.


---

24. REQUIRED OUTPUT

Создай:

REPOSITORY_ORGANIZATION_FORENSICS_V1.md

Со следующими разделами:

A. Executive Summary

B. Current Repository Map

C. Domain Map

D. Component Ownership Map

E. Code / Documentation Analysis

F. Platform vs Project Boundary

G. Core / Service / Runtime Analysis

H. Intelligence Domain

I. Agent Ecosystem

J. Factory / Forge / Scenario Placement

K. Prompt Organization

L. Data / Storage Organization

M. Experiments / Research / Legacy

N. Duplication Analysis

O. Dependency Analysis

P. Architectural Smells

Q. Proposed Canonical Repository Structure

R. File Migration Matrix

S. Documentation Organization

T. Code ↔ Documentation Traceability

U. Metadata / Tagging Proposal

V. Migration Strategy

W. Risk Register

X. Validation Strategy

Y. Final Recommendation


---

25. FILE MIGRATION MATRIX

Обязательно создать таблицу:

Current Path	Component	Responsibility	Target Path	Action	Risk	Dependencies



Actions:

KEEP
MOVE
MERGE
SPLIT
RENAME
DEPRECATE
ARCHIVE
DELETE
UNKNOWN


---

26. САМОЕ ВАЖНОЕ

В конце ответить на вопрос:

> «Если завтра новый разработчик откроет repository, сможет ли он за 5–10 минут понять, где находится платформа, где находятся проекты, где Intelligence, где Agents, где Factories, где Forge, где документация и где эксперименты?»



Если нет:

> показать, почему.




