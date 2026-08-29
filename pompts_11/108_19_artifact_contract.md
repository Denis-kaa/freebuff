

PROMPT — ARCHITECTURE DECISION & BOUNDARY VALIDATION v1.0

РОЛЬ

Ты — Senior AI Systems Architect / Architecture Decision Engineer / Repository Forensics Auditor.

Ты работаешь с существующей платформой Freebuff / Workspace OS.

Твоя задача — не переписать архитектуру по памяти и не реализовать новую систему, а на основании уже проведённого forensic-исследования определить:

> какая архитектурная модель действительно соответствует существующему коду, документации и реальному способу работы пользователя, какие границы необходимо закрепить, какие абстракции конкурируют, какие связи отсутствуют, и что именно следует оставить, объединить, разделить или сделать адаптером.



КРИТИЧЕСКОЕ ПРАВИЛО

КОД И ФАКТИЧЕСКОЕ ПОВЕДЕНИЕ РЕПОЗИТОРИЯ — ИСТОЧНИК ИСТИНЫ.

Документация является архитектурной гипотезой / контрактом / историей решений, но не доказательством существования функциональности.

Не делай вывод:

> «это реализовано, потому что это описано в документации».



Сначала найди код и конкретный execution path.


---

0. ИСХОДНАЯ ТОЧКА

В репозитории уже проведены несколько forensic-проходов, в том числе:

FORENSICS 104;

FORENSICS 105;

FORENSICS 106;

FORENSICS 107;

Evidence Ledger;

Contract Graph;

Competing Abstractions;

System Model;

Audit Delta;

предыдущие архитектурные документы.


НЕ ПОВТОРЯЙ МЕХАНИЧЕСКИ ЭТУ РАБОТУ.

Используй её как входной материал.

Но:

> если предыдущий forensic-вывод противоречит фактическому коду — перепроверь код и зафиксируй расхождение.



Особенно внимательно проверь все места, где предыдущие документы сами изменяли свои выводы.


---

1. ЗАПРЕТ НА ИЗМЕНЕНИЕ КОДА

На всём этапе исследования:

КОД НЕ ИЗМЕНЯТЬ.

Запрещено:

рефакторить;

перемещать файлы;

переименовывать модули;

создавать compatibility wrappers;

менять API;

исправлять архитектуру;

добавлять новые capability;

удалять старые компоненты.


Допустимо создавать только аналитические документы, если это необходимо для результата.


---

2. ГЛАВНЫЙ ВОПРОС

Исследуй платформу через следующую рабочую модель.

Это не готовая архитектура, а гипотеза, которую ты обязан проверить.


---

3. МОДЕЛЬ, КОТОРУЮ НУЖНО ПРОВЕРИТЬ

Представь:

У пользователя появилась идея.

Например:

> «Я хочу создать автомобиль».



Он записывает её в блокнот.

Это:

WHIM

Лёгкая фиксация мысли до формального проекта.


---

Пользователь приходит в Workspace OS.

Это:

WORKSPACE OS

Среда, в которой пользователь работает.

Внутри неё находятся различные Workspace.

Workspace можно представить как:

> шкаф / рабочую среду / контейнер деятельности.




---

Пользователь создаёт:

PROJECT

Например:

> «Создание автомобиля».



Project — это не просто папка.

Это идентичность и граница конкретной работы.

Внутри Project находятся:

контекст;

цели;

решения;

задачи;

исследования;

обсуждения;

артефакты;

память;

документы;

исполнители;

история;

результаты.



---

4. ПОЛЬЗОВАТЕЛЬ И АГЕНТЫ

В проекте пользователь может выступать как:

owner;

project manager;

decision maker;

participant;

reviewer;

просто собеседник.


Кроме него в проекте могут участвовать:

люди;

AI-агенты;

специализированные модели;

инструменты;

внешние сервисы.


Один агент может иметь разные роли в разных ситуациях.

Например:

COMPANION
ARCHITECT
DEVELOPER
AUDITOR
RESEARCHER
DOCUMENTARIAN
CREATIVE
EXECUTOR
REGISTRAR

Но:

> ROLE ≠ AGENT ≠ MODEL ≠ CAPABILITY.



Это необходимо проверить по коду.


---

5. АНАЛОГИЯ КОМПАНИИ

Используй следующую аналогию как средство проверки модели.

Пользователь — условно владелец компании / руководитель проекта.

Project Manager видит весь проект.

Внутри проекта есть специалисты:

PROJECT
   │
   ├── Research
   ├── Design
   ├── Engineering
   ├── Marketing
   ├── Documentation
   └── QA

Они могут быть:

людьми;

AI-агентами;

Factory;

Forge;

внешними исполнителями;

комбинацией этих механизмов.


PM не обязан знать внутреннее устройство каждого отдела.

Он говорит:

> «Мне нужно исследовать рынок».



Система должна определить:

> какой capability / factory способен выполнить эту работу.




---

6. SCENARIO

Проверь гипотезу:

SCENARIO

это не обязательно «исполнитель».

Scenario может быть:

> описание / композиция / план того, как решить определённый класс задач.



Например:

Создание автомобиля
        ↓
исследовать рынок
        ↓
исследовать ЦА
        ↓
исследовать конкурентов
        ↓
определить требования
        ↓
разработать концепцию
        ↓
создать дизайн
        ↓
разработать техническую часть
        ↓
собрать
        ↓
протестировать

Но проверь:

> является ли существующий ScenarioRegistry именно таким механизмом?



Или в реальном коде Scenario выполняет совершенно другую функцию?


---

7. FACTORY

Проверь следующую гипотезу.

Factory — это организация capability.

Например:

RESEARCH FACTORY
│
├── Market Research
├── Customer Research
├── Competitor Research
└── Pricing Research

Factory получает задачу:

> «Исследовать рынок автомобиля».



Factory определяет:

> какие внутренние Forge / tools / agents / skills необходимы.




---

Другой пример:

DESIGN FACTORY
│
├── Concept Design Forge
├── UI Design Forge
└── Visual Generation Forge


---

8. FORGE

Проверь гипотезу:

Forge

это конкретный производственный механизм / execution capability.

Например:

Factory
   ↓
Forge
   ↓
Execution
   ↓
Artifact

Research Factory:

Research Factory
      ↓
Competitor Research Forge
      ↓
research_web
      ↓
dataset
      ↓
report

Design Factory:

Design Factory
      ↓
Design Forge
      ↓
agents + tools
      ↓
design artifact

Development Factory:

Development Factory
      ↓
Development Forge
      ↓
developer/tester/fixer
      ↓
code

Но не принимай эту модель автоматически.

Проверь существующие:

ForgeFacade;

ForgePipeline;

ForgeRegistry;

FactoryRegistry;

ScenarioRegistry;

AgentMesh;

ToolRuntime;

MCP;

role systems.


Определи их фактическую ответственность.


---

9. ARTIFACT

Проверь, существует ли в системе единая концепция:

INPUT
  ↓
CAPABILITY
  ↓
EXECUTION
  ↓
ARTIFACT

Artifact может быть:

код;

документ;

изображение;

исследование;

таблица;

отчёт;

дизайн;

конфигурация;

другой результат.


Не предполагай, что artifact обязательно файл.

Проверь фактическую модель.


---

10. PROJECT КАК ЦЕНТР КОНТЕКСТА

Особенно тщательно исследуй:

Project
Project State
Knowledge
Memory
Artifacts
Tasks
Events
Roles
Agents

Нужно определить:

> является ли Project действительно границей проекта, или сейчас разные подсистемы используют разные представления «проекта».



Проверь:

workspace.py;

workspace_registry.py;

task systems;

memory;

knowledge;

forge registry;

scenario;

events;

artifact storage.



---

11. MEMORY / KNOWLEDGE

Не объединяй автоматически:

Memory
Knowledge
Graph
Engineering Memory
Project State

Для каждого определить:

1. ответственность;


2. источник данных;


3. жизненный цикл;


4. API;


5. кто пишет;


6. кто читает;


7. является ли это persistence, semantic layer, index или domain model.



После этого определить:

> где действительно дублирование, а где разные уровни одной системы.




---

12. AGENT MODEL

Это отдельный обязательный раздел.

Исследуй:

Agent
Role
Model
Capability
Tool
Runtime
Task
Assignment
Team
Project Role

Нужно получить ответ:

Что такое Agent?

Что такое Role?

Что такое Model?

Что такое Capability?

Что такое Tool?

Что такое Runtime?

Что такое Assignment?

Что такое Project Role?

И особенно:

> может ли один Agent выполнять разные роли?



> может ли одна Role выполняться разными Agents?



> может ли один Model выполнять разные роли?



> где определяется, кто именно должен выполнить работу?




---

13. COMPETING ABSTRACTIONS

Для каждой обнаруженной конкурирующей сущности создай таблицу:

Абстракции	A отвечает за	B отвечает за	Дублирование	Различие	Решение



Минимально проверить:

Workspace
WorkspaceRegistry

Task
Orchestrator

Role
Project Role

Agent
Runtime

ToolRuntime
MCP Tool

Memory
Knowledge

Knowledge
Graph

Factory
Forge

Scenario
Scenario Intelligence

Project
Project State

Но не ограничивайся этим списком.


---

14. CONTRACT GRAPH

Построй фактический граф:

USER
 ↓
WORKSPACE
 ↓
PROJECT
 ↓
TASK
 ↓
SCENARIO
 ↓
FACTORY
 ↓
FORGE
 ↓
AGENT / ROLE / TOOL
 ↓
ARTIFACT
 ↓
MEMORY / KNOWLEDGE

Для каждого перехода определить:

FROM
TO
CONTRACT
INPUT
OUTPUT
IMPLEMENTATION
EVIDENCE
STATUS

Статусы:

CONFIRMED
PARTIAL
IMPLICIT
MISSING
CONFLICTING

Особенно важно найти:

> где архитектура говорит, что связь существует, но код её не реализует.



И наоборот:

> где код уже реализует связь, которая отсутствует в документации.




---

15. ВНЕШНИЕ СИСТЕМЫ

Отдельно проверить будущую модель:

External System
       ↓
Integration Gateway
       ↓
Adapter
       ↓
Workspace Capability
       ↓
Project

Примеры:

Bitrix;

Asana;

Google;

Telegram;

MCP;

API;

Webhooks;

другие внешние сервисы.


Определить:

1. где должен находиться Integration Layer;


2. где authentication;


3. где authorization;


4. где tenant/workspace isolation;


5. где policy;


6. где sandbox;


7. кто владелец credentials;


8. что разрешено внешней системе;


9. как внешний проект отображается во внутренний Project;


10. какие данные могут покидать sandbox.



Не реализовывать этот слой.

Только определить его архитектурную границу.


---

16. РЕАЛЬНЫЙ WORKSPACE FLOW

Восстанови фактический lifecycle:

WHIM
 ↓
PROJECT?
 ↓
DISCUSSION / COMPANION
 ↓
UNDERSTANDING
 ↓
SCENARIO
 ↓
FACTORY
 ↓
FORGE
 ↓
EXECUTION
 ↓
ARTIFACT
 ↓
PROJECT KNOWLEDGE
 ↓
NEXT ACTION

Для каждого перехода:

существует ли он;

где реализован;

какой код отвечает;

какой контракт;

что отсутствует.



---

17. НЕ ПОДГОНЯТЬ КОД ПОД АНАЛОГИЮ

Это принципиально.

Если фактическая архитектура отличается от автомобильной аналогии — зафиксируй отличие.

Возможны варианты:

MODEL MATCH

Код соответствует модели.

MODEL PARTIAL

Часть модели существует.

MODEL MISMATCH

Код устроен иначе.

MODEL MISSING

Концепция нужна, но реализации нет.

Не объявляй архитектуру правильной только потому, что она красиво выглядит.


---

18. РЕШЕНИЕ ПО КАЖДОЙ СУЩНОСТИ

Для каждого основного компонента вынести одно решение:

KEEP
MERGE
SPLIT
RENAME
WRAP
ADAPTER
DEPRECATE
NEW CONTRACT
NEW COMPONENT

Но:

> не менять код.



Это пока только Architecture Decision.


---

19. ЦЕЛЕВАЯ МОДЕЛЬ

После анализа предложи целевую модель:

WORKSPACE OS
│
├── WORKSPACES
│     │
│     └── PROJECT
│            │
│            ├── PEOPLE
│            ├── AGENTS
│            ├── ROLES
│            ├── TASKS
│            ├── KNOWLEDGE
│            ├── MEMORY
│            ├── ARTIFACTS
│            └── EVENTS
│
├── INTELLIGENCE
│
├── SCENARIOS
│
├── FACTORIES
│     │
│     ├── FORGES
│     ├── SKILLS
│     └── TOOLS
│
├── RUNTIMES
│
├── INTEGRATIONS
│
└── GOVERNANCE / POLICY

Но это только гипотеза.

Финальная структура должна появиться после forensic анализа.


---

20. REPOSITORY STRUCTURE

Только после принятия архитектурных решений предложи новую структуру репозитория.

Например, исследуй, оправдана ли структура:

platform/
│
├── core/
│   ├── workspace/
│   ├── project/
│   ├── intelligence/
│   ├── scenario/
│   ├── factory/
│   ├── forge/
│   ├── agent/
│   ├── task/
│   ├── memory/
│   ├── knowledge/
│   └── integration/
│
├── factories/
│   ├── research/
│   ├── development/
│   ├── content/
│   └── ...
│
├── runtimes/
│
├── integrations/
│
├── contracts/
│
├── docs/
│
├── prompts/
│
├── tests/
│
└── scripts/

Не принимать эту структуру как готовую.

Проверь её против реального кода.

Главный принцип:

> код конкретного домена должен находиться рядом с его контрактами, тестами и реализацией настолько, насколько это улучшает границы; глобальная документация платформы не должна смешиваться с runtime-кодом.




---

21. БЕЗОПАСНЫЙ REFACTOR PLAN

После архитектурного решения создать roadmap:

Phase 0

Architecture baseline.

Phase 1

Contracts.

Phase 2

Boundary adapters.

Phase 3

Move/organize modules.

Phase 4

Remove duplicated abstractions.

Phase 5

Implement missing links.

Phase 6

Integration layer.

Phase 7

UI.

Для каждого шага:

WHAT
WHY
FILES
DEPENDENCIES
RISKS
ROLLBACK
TESTS


---

22. ОСОБЫЙ ЗАПРЕТ

Не предлагай:

> «переписать всё с нуля».



Не предлагай:

> «создать новую архитектуру рядом со старой».



Не создавай:

NewWorkspace
NewProject
NewFactory
NewForge
NewAgentSystem

только потому, что текущие компоненты названы иначе.

Сначала выясни:

> можно ли существующую систему привести к модели через контракты и аккуратное разделение ответственности.




---

23. ОБЯЗАТЕЛЬНЫЙ ФИНАЛЬНЫЙ ВОПРОС

В конце ты должен дать однозначный ответ:

> «Если пользователь завтра создаёт проект "Создание автомобиля", какой реальный execution path проходит система от первой мысли до готового артефакта?»



Покажи одновременно:

КАК ДОЛЖНО БЫТЬ

и

КАК ЕСТЬ СЕЙЧАС

Например:

DESIRED

Whim
 ↓
Project
 ↓
Companion
 ↓
Scenario
 ↓
Factory
 ↓
Forge
 ↓
Agent
 ↓
Tool
 ↓
Artifact
 ↓
Knowledge


ACTUAL

Whim
 ↓
?
 ↓
Project
 ↓
ScenarioRegistry
 ↓
?
 ↓
ForgeFacade
 ↓
...

Каждый ? должен иметь объяснение.


---

24. REQUIRED OUTPUT

Создай:

A. EXECUTIVE ARCHITECTURE DECISION

Краткий ответ:

какая модель подтверждается;

какая нет;

что является главным архитектурным центром;

где главные конфликты.


B. DOMAIN RESPONSIBILITY MAP

Полная карта ответственности компонентов.

C. COMPETING ABSTRACTIONS MATRIX

Все конкурирующие сущности.

D. AGENT / ROLE / MODEL / CAPABILITY MODEL

Отдельная модель исполнителей.

E. WORKSPACE / PROJECT MODEL

Граница Workspace и Project.

F. SCENARIO / FACTORY / FORGE MODEL

Их реальные границы.

G. CONTRACT GRAPH

Фактические связи.

H. GAP MAP

Что отсутствует.

I. TARGET ARCHITECTURE

Целевая модель.

J. TARGET REPOSITORY STRUCTURE

Предлагаемая структура каталогов.

K. REFACTOR ROADMAP

Безопасная последовательность изменений.

L. MIGRATION RISKS

Что может сломаться.

M. ARCHITECTURE DECISION RECORDS

Каждое существенное решение оформить отдельно:

ADR-ID
Context
Evidence
Decision
Alternatives
Consequences
Migration impact


---

25. EVIDENCE RULE

Каждое утверждение вида:

> «X делает Y»



должно иметь evidence:

path
symbol/class/function
execution path

Не использовать:

> «по архитектуре предполагается».



Если доказательства нет:

UNCONFIRMED

Если документация говорит одно, а код другое:

DOC/CODE DIVERGENCE


---

26. FINAL VERDICT

В самом конце дать:

ARCHITECTURE STATUS

[ ***REMOVED*** MODEL CONFIRMED
[ ***REMOVED*** MODEL PARTIALLY CONFIRMED
[ ***REMOVED*** MODEL REQUIRES REVISION
[ ***REMOVED*** MAJOR BOUNDARY CONFLICTS

И отдельно:

TOP 10 ARCHITECTURAL DECISIONS

которые необходимо принять до начала рефакторинга.


---

27. ПОСЛЕДНЕЕ И САМОЕ ВАЖНОЕ

Ты не должен начинать реализацию.

Ты не должен «исправлять» найденные проблемы.

Ты не должен переписывать код.

Твоя задача сейчас:

> превратить результаты нескольких forensic-проходов в одну проверенную архитектурную baseline-модель, где каждая сущность имеет однозначную ответственность, каждая связь имеет контракт, а каждое архитектурное решение имеет доказательство из кода.



Только после утверждения этой baseline-модели будет разрешён следующий этап:

ARCHITECTURE BASELINE
        ↓
CONTRACTS
        ↓
REFACTOR
        ↓
IMPLEMENT
        ↓
TEST
        ↓
UI / INTEGRATIONS

До утверждения Architecture Baseline — CODE = READ ONLY.


---

И отдельно для агента

Не пытайся доказать, что моя модель правильная.

Твоя задача — проверить её на прочность.

Если после исследования ты придёшь к выводу, что:

> Factory и Forge у нас фактически одно и то же;



или:

> Scenario выполняет не ту функцию, которую мы ему приписываем;



или:

> Project не является настоящей границей контекста;



или:

> Agent/Role/Runtime сейчас концептуально смешаны;



или:

> наша модель Workspace OS требует ещё одного уровня;



— это не ошибка исследования. Это ценный результат.

Лучше обнаружить это сейчас, пока мы ещё можем спокойно изменить архитектурную модель, чем после появления UI и внешних интеграций.

Начни с чтения существующих forensic-артефактов, затем перейди к коду и только после этого формируй Architecture Decision.