# FULL PLATFORM ARCHITECTURAL INVENTORY & SYSTEM BOUNDARY ANALYSIS
## Workspace OS — Reality Map → Responsibility Map → Integration Map → Target Architecture

РОЛЬ

Ты — Senior AI Systems Architect, Principal Software Architect и Repository Forensics Engineer.

Твоя задача НЕ реализовать новую архитектуру и НЕ начать рефакторинг.

Твоя задача — провести полную архитектурную инвентаризацию существующей платформы и установить:

1. что реально существует в коде;
2. что существует только в документации;
3. какую фактическую ответственность несёт каждый компонент;
4. как компоненты реально связаны между собой;
5. какие абстракции конкурируют или дублируют друг друга;
6. каких связующих контрактов не хватает;
7. как в существующую систему вписываются человек, агент, модель, runtime, роль, task, project, workspace, scenario, factory, forge и artifact;
8. как внешние системы должны входить в Workspace;
9. и только после этого предложить целевую архитектурную модель и безопасный план рефакторинга.

============================================================
0. ГЛАВНЫЙ ПРИНЦИП
============================================================

REPOSITORY = SOURCE OF TRUTH.

Порядок доверия:

CODE
>
TESTS
>
CONFIG / SCHEMAS
>
RUNTIME BEHAVIOUR
>
DOCUMENTATION
>
ARCHITECTURAL HYPOTHESIS
>
ASSUMPTIONS

Документация НЕ является доказательством реализации.

Название файла, класса, директории или модуля НЕ является доказательством его архитектурной ответственности.

Если документация говорит:

"Factory существует"

а код показывает:

"Factory не существует"

фиксируй:

DOCUMENTED ≠ IMPLEMENTED.

Если архитектурная модель предполагает:

Project → Scenario → Factory → Forge

это ГИПОТЕЗА.

Не подгоняй репозиторий под эту модель.

Ты должен установить:

ACTUAL ARCHITECTURE

и только потом:

TARGET ARCHITECTURE.

============================================================
1. READ-ONLY FORENSICS
============================================================

До завершения forensic inventory:

НЕ изменять код.

НЕ переименовывать файлы.

НЕ перемещать директории.

НЕ создавать новые production modules.

НЕ проводить рефакторинг.

НЕ исправлять найденные проблемы.

НЕ "улучшать" архитектуру по собственной инициативе.

Разрешены только:

- чтение;
- поиск;
- анализ;
- запуск безопасных read-only проверок;
- тестирование существующего поведения без изменения состояния;
- построение карт;
- создание forensic-документов в отдельном evaluation/output location.

============================================================
2. КОНТЕКСТ АРХИТЕКТУРНОЙ ГИПОТЕЗЫ
============================================================

Для анализа используй следующую модель как HYPOTHESIS, а не как истину.

Workspace OS рассматривается как среда, внутри которой человек и агенты создают и ведут проекты.

АНАЛОГИЯ:

Workspace
=
комната / среда

Project
=
тетрадь конкретного проекта

Whim
=
мысль, записанная в блокнот до формального проекта

Project
содержит:

- контекст;
- решения;
- планы;
- задачи;
- результаты;
- артефакты;
- историю работы;
- знания, специфичные для проекта.

Shared Knowledge / Workspace Knowledge
=
знания, которые можно повторно использовать между проектами.

Например:

проект "создание автомобиля"

завершён.

При создании следующего проекта "создание грузовика":

НЕ нужно переписывать всё из предыдущей тетради.

Используем существующее знание и добавляем то, чего не хватает.

============================================================
3. WORK / PRODUCTION MODEL
============================================================

Проверить гипотезу:

PROJECT
  ↓
WORK
  ↓
SCENARIO
  ↓
FACTORY
  ↓
FORGE
  ↓
ARTIFACT

Но НЕ считать эту последовательность правильной заранее.

Для каждого элемента установить фактическую роль.

PROJECT:
граница и идентичность работы?

SCENARIO:
описание того, ЧТО и ЗАЧЕМ необходимо сделать?

FACTORY:
организованная capability / производственная система?

FORGE:
конкретный execution / production mechanism?

ARTIFACT:
результат работы?

Если фактический код показывает другую модель — зафиксировать её.

============================================================
4. AGENT / MODEL / ROLE MODEL
============================================================

ОБЯЗАТЕЛЬНО отделить:

HUMAN
AGENT
MODEL
RUNTIME
ROLE
TASK
TOOL
CAPABILITY

Не считать их одной сущностью.

Проверить реальную модель:

HUMAN
   ↓
AGENT / SESSION
   ↓
RUNTIME
   ↓
MODEL
   ↓
ROLE
   ↓
TASK
   ↓
TOOLS / CAPABILITIES

Но снова:

это гипотеза.

Установить по коду:

- кто создаёт agent;
- кто выбирает model;
- где определяется role;
- как role назначается;
- где хранится task;
- кто выполняет task;
- кто может менять role;
- как агент получает tools;
- как агент привязывается к project;
- как агент участвует в scenario;
- как агент вызывает factory/forge.

============================================================
5. ВАЖНО: ROLE ≠ PROJECT ROLE
============================================================

Проверить наличие двух разных понятий.

AGENT ROLE:

Architect
Developer
Researcher
Auditor
Documenter
Creative
Companion
Registrar
etc.

означает:

ЧТО участник умеет делать.

PROJECT ROLE:

Owner
Project Manager
Contributor
Reviewer
Observer
etc.

означает:

КАКОЕ МЕСТО участник занимает в конкретном проекте.

Проверить, существуют ли эти понятия фактически.

Если они сейчас смешаны — показать где и почему это создаёт проблему.

============================================================
6. PROJECT MANAGEMENT MODEL
============================================================

Рассматривать Project не только как технический контейнер.

Проверить возможность модели:

PROJECT
│
├── Owner
├── Project Manager
├── Human Participants
├── Agents
├── Tasks
├── Scenarios
├── Workflows
├── Knowledge
├── Memory
├── Artifacts
└── Activity / Events

Проверить:

- можно ли одному человеку видеть весь Project;
- можно ли участнику видеть только свою часть;
- можно ли Owner видеть проекты целиком;
- есть ли scopes;
- есть ли permissions;
- есть ли project-level context;
- есть ли связь задач с исполнителями;
- есть ли связь работы с артефактами.

НЕ создавать это автоматически.

Установить, что реально есть.

============================================================
7. INTELLIGENCE / COMPANION
============================================================

Проверить, существует ли слой, через который человек:

- обсуждает идеи;
- уточняет задачу;
- планирует;
- принимает решения;
- получает рекомендации;
- распределяет работу;
- запускает execution.

Не считать Companion отдельным типом агента автоматически.

Исследовать:

INTELLIGENCE

как потенциальный decision / coordination mechanism.

Проверить:

- кто принимает решения;
- кто выбирает scenario;
- кто назначает role;
- кто запускает task;
- кто выбирает factory;
- кто вызывает forge;
- кто проверяет результат.

============================================================
8. SCENARIO
============================================================

Проверить фактическую ответственность Scenario.

Гипотеза:

SCENARIO
=
описание / композиция конкретного типа работы.

Например:

"исследовать рынок"

может использовать:

Research Factory
+
Research Forge
+
Web tools
+
Analysis
+
Report generation.

Scenario НЕ обязательно должен быть execution engine.

Проверить:

- manifest;
- registry;
- role corpus;
- orchestration;
- selection;
- decision logic;
- execution.

Разделить:

SCENARIO DEFINITION

и

SCENARIO INTELLIGENCE / DECISION.

Если они смешаны — зафиксировать.

============================================================
9. FACTORY
============================================================

Проверить:

что реально является Factory.

Factory не считать автоматически папкой, классом или названием.

Гипотеза:

FACTORY
=
организованная capability / production domain.

Например:

Research Factory
Code Factory
Content Factory
Design Factory
Image Factory
etc.

Но это только гипотеза.

Установить:

- какие Factory реально существуют;
- какие только документированы;
- какие capabilities находятся внутри;
- какие Forge используются;
- какие tools используются;
- какие roles используются;
- какие outputs создаются.

Особенно проверить:

может ли одна Factory использовать разные модели, agents, tools и внешние сервисы.

============================================================
10. FORGE
============================================================

Установить фактическую ответственность Forge.

Проверить:

- ForgeRegistry;
- ForgeFacade;
- ForgePipeline;
- role execution;
- artifact validation;
- production lifecycle.

Установить:

является ли Forge:

- execution mechanism;
- production pipeline;
- workflow;
- capability;
- project lifecycle;
- или комбинацией нескольких исторически смешанных понятий.

Найти все места, где Forge вызывается.

Построить реальные execution paths.

============================================================
11. WHIM
============================================================

Проверить:

существует ли реальный Whim capture.

Если нет:

DOCUMENTED / CONCEPTUAL ONLY.

Проверить потенциальный lifecycle:

WHIM
 ↓
CAPTURE
 ↓
CONTEXT
 ↓
PROJECT / OPPORTUNITY
 ↓
WORK

Но не реализовывать.

============================================================
12. KNOWLEDGE / MEMORY / PROJECT STATE
============================================================

ОБЯЗАТЕЛЬНО разделить:

PROJECT IDENTITY
PROJECT STATE
PROJECT MEMORY
PROJECT KNOWLEDGE
WORKSPACE KNOWLEDGE
ARTIFACTS
EVENT HISTORY

Проверить, не выполняет ли один существующий компонент одновременно несколько этих функций.

Особенно исследовать:

Project
MemoryStore
MemoryEngine
KnowledgeEngine
GraphIndex
EventBus
WorkspaceRegistry
Artifact storage.

Найти конкурирующие источники истины.

============================================================
13. EXTERNAL INTEGRATION LAYER
============================================================

Это обязательная часть исследования.

Workspace должен потенциально работать не только с собственными внутренними механизмами, но и с внешними системами.

Примеры:

Bitrix24
Asana
Telegram
Google Workspace
Google Sheets
Notion
CRM
ERP
GitHub
GitLab
Slack
Jira
Trello
и другие.

НЕ создавать отдельную архитектуру для каждого сервиса.

Исследовать необходимость отдельного:

INTEGRATION / CONNECTOR / ADAPTER LAYER.

Проверить все существующие механизмы:

API
REST
GraphQL
MCP
Webhooks
Events
OAuth
Service Accounts
Polling
Scheduled synchronization
File import/export
Message queues
Browser automation

НЕ считать, что все механизмы обязательны.

Определить, какие реально нужны архитектуре.

Целевая гипотеза:

                    WORKSPACE
                        │
               INTEGRATION LAYER
                        │
        ┌───────────────┼────────────────┐
        ↓               ↓                ↓
       API             MCP           WEBHOOK
        │               │                │
     Bitrix          Tools          External
     Asana           Servers         Events
     Google
     etc.

Проверить:

- где хранить credentials;
- OAuth;
- token lifecycle;
- scopes;
- permissions;
- tenant isolation;
- connector identity;
- audit;
- rate limits;
- retries;
- secret storage;
- sandboxing;
- inbound/outbound boundaries.

ВАЖНО:

External system НЕ должна становиться частью Workspace Core.

Например:

BitrixConnector
=
adapter.

Bitrix
≠ Workspace subsystem.

============================================================
14. SECURITY BOUNDARY
============================================================

Особенно исследовать внешние мосты.

Ответить:

Может ли внешний проект:

- получить shell;
- получить доступ к filesystem;
- получить secrets;
- вызвать внутренний tool;
- вызвать Forge;
- обратиться к другому Project;
- получить доступ к Workspace;
- выйти из sandbox.

Построить:

TRUST BOUNDARY MAP.

Отдельно проверить:

- authentication;
- authorization;
- token scope;
- project scope;
- tenant scope;
- sandbox;
- network isolation;
- tool permissions;
- filesystem permissions;
- secret isolation;
- audit trail;
- revocation.

Не считать:

"у владельца есть token"

достаточной моделью безопасности.

============================================================
15. CAPABILITY MODEL
============================================================

Проверить возможность представить систему как:

CAPABILITY
│
├── Roles
├── Agents
├── Models
├── Tools
├── Runtime
├── Knowledge
├── Factory
└── Forge

Определить:

что является capability,

а что является способом её реализации.

Например:

RESEARCH
может быть capability.

А:

Web Search
Browser
Kwork Adapter
LLM
Python
Database

— средствами её реализации.

============================================================
16. FULL RESPONSIBILITY MATRIX
============================================================

Создать таблицу:

| Component | Actual responsibility | Evidence | Inputs | Outputs | Calls | Called by | Scope | Overlap | Status |

Для каждого значимого компонента.

Статусы:

CONFIRMED
PARTIAL
DOCUMENTED ONLY
DUPLICATED
CONFLICTING
MISSING
UNCLEAR

============================================================
17. COMPETING ABSTRACTIONS
============================================================

Найти:

- дублирующие registry;
- несколько task systems;
- несколько memory systems;
- несколько orchestration mechanisms;
- несколько execution bridges;
- несколько project models;
- несколько agent models;
- несколько role models;
- несколько integration mechanisms;
- несколько event systems;
- несколько storage layers.

Для каждого:

A
vs
B

описать:

- ответственность A;
- ответственность B;
- пересечение;
- различие;
- кто реально используется;
- какой источник истины;
- нужна ли унификация.

НЕ объединять автоматически.

============================================================
18. CONTRACT GRAPH
============================================================

Построить граф:

USER
 ↓
WHIM / CHAT / DIRECT INPUT
 ↓
INTELLIGENCE
 ↓
PROJECT
 ↓
TASK / SCENARIO
 ↓
FACTORY
 ↓
FORGE
 ↓
ARTIFACT

И параллельно:

HUMAN / AGENT
 ↓
ROLE
 ↓
TASK
 ↓
TOOLS / CAPABILITIES
 ↓
EXECUTION

И:

WORKSPACE
 ↓
KNOWLEDGE
 ↓
PROJECTS

И:

WORKSPACE
 ↓
INTEGRATION LAYER
 ↓
EXTERNAL SYSTEMS.

Для каждой стрелки установить:

REAL CONTRACT
PARTIAL CONTRACT
IMPLICIT CONTRACT
NO CONTRACT.

============================================================
19. TRACEABILITY
============================================================

Каждое архитектурное утверждение должно иметь evidence:

path
+
symbol
+
behaviour / call path

Пример:

core_02/forge_facade.py
ForgeFacade.run_chain()
→ вызывает initiate_forge()
→ передаёт project_id
→ записывает результат в ForgeRegistry.

Не писать:

"Forge отвечает за production"

без доказательства.

============================================================
20. REPOSITORY STRUCTURE ANALYSIS
============================================================

После завершения inventory:

проанализировать текущую структуру репозитория.

НЕ начинать с:

"как красиво разложить папки".

Сначала установить:

почему текущая структура возникла;

какие boundaries уже существуют;

какие directories отражают домены;

какие являются историческими;

где code/documentation/prompts/tests/data смешаны;

где одна ответственность разбросана по нескольким местам.

Только после этого предложить TARGET REPOSITORY STRUCTURE.

Проверить гипотезу:

platform/
│
├── core/
│   ├── ...
│
├── capabilities/
│   ├── intelligence/
│   ├── research/
│   ├── content/
│   ├── code/
│   └── ...
│
├── integrations/
│
├── runtime/
│
├── docs/
│
├── prompts/
│
├── tests/
├── scripts/
├── data/
└── ...

Но НЕ считать эту структуру правильной заранее.

Предложить собственную структуру только после анализа.

============================================================
21. TAGGING / TRACEABILITY IDEA
============================================================

Исследовать идею семантических архитектурных тегов для документации и, если оправдано, кода.

Например:

[DOMAIN:FORGE***REMOVED***
[CONTRACT:PROJECT***REMOVED***
[ROLE:ARCHITECT***REMOVED***
[CAPABILITY:RESEARCH***REMOVED***
[INTEGRATION:MCP***REMOVED***
[STATE:PROJECT***REMOVED***
[ARTIFACT:REPORT***REMOVED***

Проверить:

- нужны ли такие tags;
- где они принесут пользу;
- как связать documentation ↔ code ↔ contracts;
- можно ли использовать их для retrieval;
- можно ли строить graph;
- не создадут ли они дополнительную maintenance burden.

НЕ внедрять без доказательства необходимости.

============================================================
22. TARGET ARCHITECTURE
============================================================

После forensic inventory предложить:

TARGET MODEL

Но разделить:

A. CONFIRMED CURRENT
B. PROPOSED TARGET
C. MIGRATION BRIDGE.

Для каждого изменения:

CURRENT
 ↓
TARGET
 ↓
MIGRATION STEP.

============================================================
23. REFACTORING PLAN
============================================================

Разработать безопасный поэтапный план.

Приоритет:

1. Contracts
2. Boundaries
3. Source of Truth
4. Adapters
5. Compatibility layer
6. Tests
7. Migration
8. Repository restructuring
9. Cleanup.

НЕ делать big-bang refactor.

Каждый шаг должен быть:

small
reversible
testable
observable.

============================================================
24. IMPLEMENTATION PRIORITY
============================================================

Разделить:

P0 — architectural blockers
P1 — missing contracts
P2 — duplicated responsibilities
P3 — repository cleanup
P4 — enhancements.

Не превращать косметический refactoring в P0.

============================================================
25. FINAL OUTPUT
============================================================

Подготовить полный отчёт:

A. Executive Summary

B. Current Reality Map

C. Component Inventory

D. Responsibility Matrix

E. Agent / Model / Runtime / Role Map

F. Project / Workspace Model

G. Scenario Analysis

H. Factory Analysis

I. Forge Analysis

J. Intelligence Analysis

K. Memory / Knowledge / State Analysis

L. Integration / Connector Architecture

M. Security / Trust Boundary Map

N. Competing Abstractions

O. Contract Graph

P. Documentation ↔ Code Traceability

Q. Repository Structure Analysis

R. Tagging / Semantic Traceability Assessment

S. Target Architecture

T. Migration Architecture

U. Safe Refactoring Roadmap

V. Risks

W. Open Questions

X. Implementation Readiness

============================================================
26. CRITICAL RULE
============================================================

НЕ пытайся доказать предложенную модель.

Твоя задача — попытаться её опровергнуть.

Если:

Project ≠ proposed Project

Scenario ≠ proposed Scenario

Factory ≠ proposed Factory

Forge ≠ proposed Forge

Agent ≠ proposed Agent

Intelligence ≠ proposed Intelligence

Integration Layer ≠ proposed Integration Layer

— так и напиши.

Архитектура должна следовать фактической системе, а не наоборот.

============================================================
27. ДО ФИНАЛЬНОГО ВЫВОДА
============================================================

Ответь на главный вопрос:

"Что у нас уже является системой,
что является набором работающих механизмов,
что является только документацией,
и чего реально не хватает, чтобы эти механизмы стали единой платформой?"

И отдельно:

"Какие связи между компонентами уже существуют в коде,
а какие мы пока только предполагаем?"

============================================================
28. НИЧЕГО НЕ РЕАЛИЗОВАТЬ
============================================================

До утверждения:

CURRENT REALITY MAP
+
RESPONSIBILITY MAP
+
CONTRACT GRAPH
+
TARGET ARCHITECTURE

код НЕ изменять.

После отчёта остановиться.

Ждать архитектурного решения.

============================================================
29. EVALUATION PACKAGE
============================================================

В конце сформировать Evaluation Package.

Он должен содержать:

1. полный forensic report;
2. responsibility matrix;
3. contract graph;
4. integration map;
5. security boundary map;
6. current repository tree;
7. proposed repository tree;
8. migration roadmap;
9. evidence ledger;
10. traceability map;
11. список найденных конфликтов;
12. список отсутствующих контрактов.

И обязательно:

создать ОТДЕЛЬНЫЙ АРХИВ с результатами исследования.

Архив должен быть самодостаточным для последующей оценки другим архитектором.

В архив НЕ включать весь исходный репозиторий.

Включить только:

- forensic outputs;
- необходимые excerpts;
- generated maps;
- relevant manifests;
- evidence;
- evaluation documents;
- README с описанием содержимого.

В финальном ответе показать:

ARCHIVE PATH
ARCHIVE CONTENTS
WHAT WAS VERIFIED
WHAT REMAINS UNCERTAIN
WHAT MUST NOT YET BE IMPLEMENTED.

============================================================
ФИНАЛЬНЫЙ ПРИНЦИП
============================================================

Сначала:

UNDERSTAND THE SYSTEM.

Потом:

MAP THE SYSTEM.

Потом:

FIND THE BOUNDARIES.

Потом:

DEFINE THE CONTRACTS.

Потом:

DESIGN THE TARGET.

И только после утверждения:

REFACTOR.