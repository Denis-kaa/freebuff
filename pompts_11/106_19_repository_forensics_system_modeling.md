# РОЛЬ

Ты — Senior AI Systems Architect + Repository Forensics Engineer +
Software Architecture Refactoring Specialist.

Ты работаешь с существующей AI Workspace-платформой.

Твоя задача НЕ состоит в том, чтобы просто прочитать документацию
и подтвердить уже написанную архитектуру.

Твоя задача — восстановить реальную систему по КОДУ + ДОКУМЕНТАЦИИ,
понять, во что она фактически превратилась, сопоставить её с целевой
концептуальной моделью и предложить архитектурную и файловую
реорганизацию.

ВАЖНО:

REPOSITORY = SOURCE OF TRUTH.

При конфликте:

код
>
тесты
>
конфигурация
>
исполняемые контракты
>
документация
>
архитектурные предположения
>
идеи

Ничего не считать существующим только потому, что оно описано
в документации.

Ничего не считать отсутствующим только потому, что оно плохо
документировано.

Каждое существенное утверждение должно иметь evidence:
path + symbol / class / function / manifest / test.

------------------------------------------------------------
# 0. ГЛАВНЫЙ ВОПРОС ИССЛЕДОВАНИЯ
------------------------------------------------------------

Восстанови реальную модель платформы:

Что это за система на самом деле?

Как пользователь проходит путь:

IDEA / WHIM
        ↓
WORKSPACE
        ↓
PROJECT
        ↓
THINKING / COLLABORATION
        ↓
SCENARIO
        ↓
FACTORY
        ↓
FORGE
        ↓
TOOLS / SKILLS / AGENTS / RUNTIMES
        ↓
ARTIFACT
        ↓
PROJECT MEMORY / KNOWLEDGE / HISTORY

И главное:

ДЕЙСТВИТЕЛЬНО ЛИ СУЩЕСТВУЮЩАЯ ПЛАТФОРМА РАБОТАЕТ ПО ЭТОЙ МОДЕЛИ?

Или это только наше текущее концептуальное представление?

НЕ ПОДГОНЯЙ РЕПОЗИТОРИЙ ПОД ЭТУ МОДЕЛЬ.

ПРОВЕРЬ ЕЁ.

------------------------------------------------------------
# 1. КОНЦЕПТУАЛЬНАЯ МЕТАФОРА ДЛЯ ПРОВЕРКИ
------------------------------------------------------------

Используй следующую модель только как исследовательскую гипотезу.

Человек идёт по дороге.

У него возникает мысль:

«Я хочу создать автомобиль».

Он записывает её в блокнот.

Это WHIM.

Затем приходит в Workspace OS.

Внутри есть Workspace.

Он создаёт Project:

«Создание автомобиля».

Project становится рабочей тетрадью / историей проекта.

Внутри проекта:

- исходная идея;
- обсуждения;
- решения;
- гипотезы;
- исследования;
- планы;
- задания;
- результаты;
- документы;
- артефакты.

Пользователь вместе с агентом/агентами развивает идею.

Затем возникает необходимость выполнить определённую работу.

Например:

- исследовать рынок;
- исследовать ЦА;
- изучить конкурентов;
- спроектировать автомобиль;
- разработать двигатель;
- создать дизайн;
- провести расчёты;
- написать код;
- создать изображение;
- подготовить документ;
- построить сайт.

Это SCENARIO.

SCENARIO определяет:

ЧТО нужно получить
и
КАКОЙ тип работы необходимо выполнить.

Для выполнения Scenario используется соответствующая FACTORY.

Например:

Research Factory
Design Factory
Code Factory
Content Factory
Image Factory
Document Factory
и т.д.

FACTORY — не конкретная работа.

FACTORY — организационная/исполнительная capability,
способная производить определённый класс результатов.

Внутри Factory находятся FORGE.

FORGE — конкретная производственная способность / workflow /
production unit, который умеет выполнить определённый тип работы.

Например:

Research Factory

    ├── Market Research Forge
    ├── Audience Research Forge
    ├── Competitor Research Forge
    └── Pricing Research Forge

Code Factory

    ├── Web Development Forge
    ├── Backend Forge
    ├── Automation Forge
    └── Integration Forge

Forge использует:

- agents;
- skills;
- tools;
- runtimes;
- external services;
- knowledge;
- memory;
- other capabilities.

В результате появляется ARTIFACT.

Например:

- research report;
- architecture;
- source code;
- image;
- website;
- video;
- document;
- content;
- dataset;
- etc.

Artifact возвращается в Project.

Project сохраняет историю:

что было решено,
почему,
кто выполнял,
какие инструменты использовались,
какие результаты получены,
какие документы появились.

Это создаёт замкнутый цикл:

WHIM
 ↓
PROJECT
 ↓
THINK
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
PROJECT MEMORY
 ↓
NEXT DECISION

------------------------------------------------------------
# 2. ОСОБЕННО ВАЖНО: AGENT / COMPANION LAYER
------------------------------------------------------------

НЕ ИГНОРИРУЙ ЭТУ ЧАСТЬ.

Платформа — это не только производственные Factory.

В системе существует слой взаимодействия пользователя с
агентом/агентами.

У пользователя может быть:

- один основной AI companion;
- несколько специализированных агентов;
- агенты-исполнители;
- агенты-исследователи;
- агенты-аналитики;
- агенты-критики;
- агенты, участвующие в обсуждении;
- агенты, запускающие production workflows.

Исследуй:

1. Где в текущем коде находится этот слой?
2. Что такое Agent в реальной реализации?
3. Что такое Runtime?
4. Что такое Role?
5. Что такое Skill?
6. Что такое Tool?
7. Что такое Workflow?
8. Что такое Scenario?
9. Как они связаны?
10. Кто принимает решение о запуске Factory/Forge?
11. Может ли агент сам инициировать execution?
12. Через какой интерфейс?
13. Где находится контекст пользователя?
14. Где находится контекст Project?
15. Где находится память разговора?
16. Где находится knowledge?
17. Где находится execution state?

Не объединяй эти понятия только потому, что они похожи.

Восстанови реальные границы ответственности.

------------------------------------------------------------
# 3. ОСНОВНАЯ ЗАДАЧА №1 — FULL REPOSITORY FORENSICS
------------------------------------------------------------

Сначала НЕ РЕФАКТОРЬ.

Полностью исследуй:

### CODE

- core;
- runtime;
- scripts;
- services;
- agents;
- tools;
- skills;
- factories;
- forge;
- scenario;
- memory;
- knowledge;
- event;
- API;
- CLI;
- integrations;
- plugins;
- storage;
- project layer.

### DOCUMENTATION

Прочитай документацию не только по заголовкам.

Особенно:

- architecture;
- ADR;
- manifests;
- contracts;
- prompts;
- protocols;
- forensic reports;
- roadmap;
- design documents;
- README;
- AGENTS.md;
- BUFFY.md;
- changelog;
- implementation notes.

### TESTS

Проверь, какие утверждения подтверждаются тестами.

### CONFIGURATION

Проверь:

- YAML;
- JSON;
- TOML;
- env contracts;
- manifests;
- registries.

------------------------------------------------------------
# 4. СОЗДАЙ ACTUAL SYSTEM MAP
------------------------------------------------------------

Построй карту:

ACTUAL PLATFORM

        USER
          │
          ↓
      ENTRYPOINTS
          │
          ↓
       AGENTS
          │
          ↓
     WORKSPACE / PROJECT
          │
          ↓
       SCENARIO
          │
          ↓
       FACTORY?
          │
          ↓
        FORGE?
          │
          ↓
   SKILLS / TOOLS / RUNTIME
          │
          ↓
       ARTIFACT
          │
          ↓
 MEMORY / KNOWLEDGE / EVENTS

Но НЕ заполняй её предположениями.

Для каждого узла укажи:

STATUS:

CONFIRMED
PARTIAL
DESIGNED
CONCEPTUAL
ABSENT

и evidence.

------------------------------------------------------------
# 5. СРАВНИ С TARGET MODEL
------------------------------------------------------------

После восстановления ACTUAL MODEL сравни её с:

WHIM
 ↓
WORKSPACE
 ↓
PROJECT
 ↓
AGENT / COLLABORATION
 ↓
SCENARIO
 ↓
FACTORY
 ↓
FORGE
 ↓
SKILLS / TOOLS / RUNTIME
 ↓
ARTIFACT
 ↓
MEMORY / KNOWLEDGE

Создай таблицу:

| Concept | Target responsibility | Actual implementation | Status | Evidence | Gap |

Особенно внимательно исследуй:

WHIM
WORKSPACE
PROJECT
AGENT
SCENARIO
FACTORY
FORGE
ROLE
SKILL
TOOL
RUNTIME
WORKFLOW
ARTIFACT
MEMORY
KNOWLEDGE
EVENT
TASK

------------------------------------------------------------
# 6. ОПРЕДЕЛИ РЕАЛЬНУЮ ГРАНИЦУ FACTORY
------------------------------------------------------------

Это КРИТИЧЕСКИ ВАЖНО.

Не предполагай, что Content Factory является центром платформы.

Content Factory — только один возможный consumer/capability.

Проверь, как должна выглядеть универсальная модель:

FACTORY
│
├── Research
├── Code
├── Design
├── Content
├── Image
├── Video
├── Document
├── Data
└── ...

Но НЕ создавай эти Factory автоматически.

Определи:

какие Factory реально существуют;

какие только концептуальны;

какие являются Forge;

какие являются Scenario;

какие просто проекты;

какие вообще не должны быть Factory.

------------------------------------------------------------
# 7. ПРОВЕРЬ HIERARCHY
------------------------------------------------------------

Ответь на вопрос:

Что является родителем чего?

Например:

Workspace
  └── Project
       └── Scenario
            └── Factory
                 └── Forge
                      └── Agent
                           └── Skill
                                └── Tool

ИЛИ другая модель.

НЕ принимай предложенную иерархию заранее.

Определи её по repository.

Особенно важно понять:

Factory принадлежит Project?

Или Factory является глобальной capability?

Forge принадлежит Factory?

Или Forge является workflow?

Scenario вызывает Factory?

Или Scenario непосредственно вызывает Forge?

Agent вызывает Scenario?

Или Agent является частью Forge?

Ответ должен основываться на коде.

------------------------------------------------------------
# 8. РАЗБЕРИ СУЩЕСТВУЮЩУЮ "КАШУ"
------------------------------------------------------------

Определи, какие проблемы существуют в структуре repository:

- код и документация перемешаны;
- несколько источников истины;
- старые концепции рядом с новыми;
- исторические документы;
- experimental code;
- production code;
- project-specific code;
- platform-level code;
- prompts;
- protocols;
- architecture;
- tests;
- scripts;
- data;
- generated artifacts.

Определи:

что относится к PLATFORM;

что относится к PROJECT;

что относится к FACTORY;

что относится к FORGE;

что относится к SCENARIO;

что относится к AGENT;

что относится к KNOWLEDGE;

что относится к DOCUMENTATION;

что относится к EXPERIMENT;

что относится к LEGACY.

------------------------------------------------------------
# 9. ПРЕДЛОЖИ TARGET REPOSITORY STRUCTURE
------------------------------------------------------------

После анализа предложи новую структуру repository.

Например, исследуй вариант:

platform/
│
├── core/
│
├── capabilities/
│
├── factories/
│
├── scenarios/
│
├── agents/
│
├── skills/
│
├── tools/
│
├── runtimes/
│
├── memory/
│
├── knowledge/
│
├── interfaces/
│
├── storage/
│
├── tests/
│
├── docs/
│
├── prompts/
│
└── experiments/

НО:

это ТОЛЬКО ПРИМЕР.

Ты обязан предложить структуру, которая соответствует
РЕАЛЬНОЙ архитектуре после исследования.

Для каждого каталога объясни:

- ответственность;
- что туда попадает;
- что туда НЕ попадает;
- кто его потребитель;
- какие зависимости допустимы;
- какие зависимости запрещены.

------------------------------------------------------------
# 10. CODE / DOCUMENTATION SEPARATION
------------------------------------------------------------

Отдельно спроектируй принцип:

CODE
vs
DOCUMENTATION
vs
PROMPTS
vs
CONTRACTS
vs
CONFIGURATION
vs
PROJECT ARTIFACTS
vs
EXPERIMENTS

Не допускай автоматического правила:

"каждый модуль имеет рядом docs/prompts/scripts"

если это создаёт дублирование.

Определи, где должен находиться:

implementation;
architecture;
contract;
prompt;
test;
example;
ADR;
forensics;
experiment;
project-specific documentation.

------------------------------------------------------------
# 11. TRACEABILITY
------------------------------------------------------------

Очень важно сохранить связь:

DOCUMENT
      ↕
CONTRACT
      ↕
CODE
      ↕
TEST
      ↕
RUNTIME BEHAVIOR

Предложи механизм traceability.

Например:

document_id
component_id
contract_id
code_path
test_path
scenario_id
factory_id
forge_id

Но не ограничивайся этим вариантом.

Исследуй существующие механизмы traceability в repository.

------------------------------------------------------------
# 12. TAGGING / SEMANTIC STRUCTURE
------------------------------------------------------------

Исследуй мою гипотезу:

Добавлять структурные теги к документации и/или отдельным
абзацам.

Например:

[CONCEPT:FACTORY***REMOVED***
[COMPONENT:FORGE_FACADE***REMOVED***
[CONTRACT:EXECUTION***REMOVED***
[SCENARIO:RESEARCH***REMOVED***
[PROJECT:CONTENT_FACTORY***REMOVED***
[DECISION:ADR-015***REMOVED***
[EVIDENCE:core_02/forge_facade.py***REMOVED***
[STATUS:CONFIRMED***REMOVED***

Цель:

не просто красивее искать документы,

а обеспечить:

- semantic retrieval;
- vector search;
- graph construction;
- traceability;
- связь документации с кодом;
- связь решений с реализацией;
- быстрый context retrieval для AI agents.

Исследуй:

1. есть ли уже подобная система;
2. где она может быть полезна;
3. где она создаст шум;
4. какие сущности действительно стоит тегировать;
5. какие связи лучше хранить в graph/database, а не в тексте;
6. можно ли автоматически генерировать tags из repository metadata.

Не внедряй tags автоматически.

Сначала дай архитектурную оценку.

------------------------------------------------------------
# 13. REFACTORING STRATEGY
------------------------------------------------------------

Предложи НЕ "переписать всё".

Создай безопасную миграцию:

CURRENT
 ↓
TARGET

с промежуточными этапами.

Для каждого шага:

- что переносится;
- что переименовывается;
- что остаётся;
- что deprecated;
- что нельзя трогать;
- какие тесты должны пройти;
- как откатить изменение.

Приоритет:

1. architecture boundaries;
2. source-of-truth;
3. dependency boundaries;
4. filesystem organization;
5. naming;
6. documentation;
7. cleanup.

------------------------------------------------------------
# 14. НЕ ПИШИ КОД СРАЗУ
------------------------------------------------------------

ПЕРВАЯ ФАЗА:

FORENSICS ONLY.

Не изменяй repository.

Не создавай новую архитектуру на основании предположений.

Не выполняй массовый refactoring.

Сначала:

ANALYZE
→ MAP
→ COMPARE
→ IDENTIFY GAPS
→ PROPOSE TARGET
→ PLAN MIGRATION

И только после этого, если явно разрешено, можно переходить
к implementation.

------------------------------------------------------------
# 15. ОБЯЗАТЕЛЬНЫЙ OUTPUT
------------------------------------------------------------

Создай Evaluation / Architecture Package.

Минимально:

01_EXECUTIVE_FINDING.md
02_REPOSITORY_MAP.md
03_ACTUAL_SYSTEM_MODEL.md
04_TARGET_SYSTEM_MODEL.md
05_CONCEPT_TRACEABILITY.md
06_FACTORY_FORGE_SCENARIO_ANALYSIS.md
07_AGENT_RUNTIME_SKILL_TOOL_ANALYSIS.md
08_REPOSITORY_STRUCTURE_AUDIT.md
09_TARGET_REPOSITORY_STRUCTURE.md
10_REFACTORING_ROADMAP.md
11_TRACEABILITY_AND_TAGGING.md
12_EVIDENCE_LEDGER.md

Дополнительно:

13_DEPENDENCY_GRAPH.md
14_ARCHITECTURAL_GAPS.md
15_MIGRATION_RISK_REGISTER.md

------------------------------------------------------------
# 16. EVIDENCE LEDGER
------------------------------------------------------------

Для каждого существенного вывода:

ID
CLAIM
SOURCE
SYMBOL
STATUS
CONFIDENCE
NOTES

Пример:

EV-001
CLAIM:
ForgeFacade is the sanctioned execution bridge.

SOURCE:
core_02/forge_facade.py

SYMBOL:
ForgeFacade.initiate_forge

STATUS:
CONFIRMED

CONFIDENCE:
HIGH

------------------------------------------------------------
# 17. ОБЯЗАТЕЛЬНЫЕ ВЫВОДЫ
------------------------------------------------------------

В конце ты должен ответить на следующие вопросы:

1. Что платформа представляет собой СЕЙЧАС?

2. Как реально проходит путь от идеи до артефакта?

3. Где сейчас находится WHIM?

4. Где сейчас находится Workspace?

5. Что является Project?

6. Где находится слой взаимодействия с агентом/агентами?

7. Что реально является Scenario?

8. Что реально является Factory?

9. Что реально является Forge?

10. Где находятся Skills?

11. Где находятся Tools?

12. Где находятся Runtimes?

13. Что такое Artifact?

14. Где хранится история проекта?

15. Где хранится knowledge?

16. Что является глобальным capability, а что project-specific?

17. Какие части платформы сейчас физически перемешаны?

18. Какие части являются legacy?

19. Какие части являются только документацией?

20. Какие части реально работают?

21. Где архитектура расходится с документацией?

22. Какая структура repository будет логичной?

23. Как разделить Platform / Project / Factory / Forge / Scenario?

24. Как обеспечить связь CODE ↔ DOCS ↔ CONTRACTS ↔ TESTS?

25. Нужны ли semantic tags?

26. Если нужны — где и какие?

27. Какой минимальный безопасный refactoring сделать первым?

28. Что НЕЛЬЗЯ рефакторить сейчас?

------------------------------------------------------------
# 18. ГЛАВНЫЙ ПРИНЦИП
------------------------------------------------------------

НЕ ПЫТАЙСЯ ДОКАЗАТЬ, ЧТО НАША МОДЕЛЬ ПРАВИЛЬНА.

ПОПРОБУЙ ЕЁ ОПРОВЕРГНУТЬ.

Если repository показывает:

"мы думали, что Factory работает так,
но фактически она работает иначе"

— зафиксируй это.

Если обнаружишь:

"документация описывает архитектуру,
которой в коде нет"

— зафиксируй это.

Если обнаружишь:

"одна сущность выполняет ответственность
трёх разных архитектурных уровней"

— зафиксируй это.

Если обнаружишь:

"названия правильные, но filesystem structure
не отражает архитектуру"

— зафиксируй это.

------------------------------------------------------------
# 19. FINISH CONDITION
------------------------------------------------------------

Работа считается завершённой только когда:

[ ***REMOVED*** repository исследован не только по заголовкам;
[ ***REMOVED*** код прочитан;
[ ***REMOVED*** ключевые execution paths подтверждены;
[ ***REMOVED*** документация сопоставлена с кодом;
[ ***REMOVED*** ACTUAL MODEL построена;
[ ***REMOVED*** TARGET MODEL предложена;
[ ***REMOVED*** Factory / Forge / Scenario разграничены;
[ ***REMOVED*** Agent / Runtime / Skill / Tool разграничены;
[ ***REMOVED*** Project / Platform boundaries определены;
[ ***REMOVED*** filesystem structure проанализирована;
[ ***REMOVED*** target structure предложена;
[ ***REMOVED*** traceability предложена;
[ ***REMOVED*** tagging гипотеза исследована;
[ ***REMOVED*** migration roadmap создан;
[ ***REMOVED*** Evidence Ledger создан;
[ ***REMOVED*** repository НЕ изменён на forensic phase.

------------------------------------------------------------
# 20. ФИНАЛЬНЫЙ АРХИВ
------------------------------------------------------------

После завершения forensic phase создай отдельный архив:

PLATFORM_ARCHITECTURE_FORENSICS_<VERSION>.zip

В него должны войти:

- все 12–15 evaluation documents;
- evidence ledger;
- system maps;
- target repository structure;
- migration roadmap;
- dependency/architecture analysis;
- tagging analysis.

НЕ включай:

- .git;
- secrets;
- API keys;
- tokens;
- .env;
- credentials;
- private user data;
- node_modules;
- virtual environments;
- build caches;
- большие generated artifacts.

ВАЖНО:

В финальном отчёте отдельно укажи:

1. путь к созданному архиву;
2. список файлов внутри;
3. размер архива;
4. какие файлы repository были использованы
   как evidence;
5. что было ПРОЧИТАНО;
6. что было НЕ ПРОЧИТАНО и почему;
7. какие выводы CONFIRMED;
8. какие PARTIAL;
9. какие DESIGN ONLY;
10. какие являются только гипотезами.

НЕ УТВЕРЖДАЙ "FULL FORENSICS COMPLETE",
если реально не был выполнен полный анализ.

------------------------------------------------------------
# FINAL RULE

Твоя задача сейчас не построить новую систему.

Твоя задача:

ПОСМОТРЕТЬ НА СУЩЕСТВУЮЩУЮ СИСТЕМУ СВЕРХУ.

ПОНЯТЬ, ЧТО МЫ ФАКТИЧЕСКИ ПОСТРОИЛИ.

ПОКАЗАТЬ, ГДЕ МЫ СЕЙЧАС.

ПОКАЗАТЬ, КУДА МОЖНО ДВИГАТЬСЯ.

И ТОЛЬКО ПОСЛЕ ЭТОГО ПРЕДЛОЖИТЬ,
КАК ПРИВЕСТИ CODE + DOCS + PROMPTS + CONTRACTS
К ЕДИНОЙ АРХИТЕКТУРНОЙ СИСТЕМЕ.

НЕ ПУТАЙ:

ARCHITECTURE
с
DOCUMENTATION.

DOCUMENTATION должна описывать систему.

CODE должен реализовывать систему.

CONTRACTS должны связывать компоненты.

TESTS должны подтверждать поведение.

PROMPTS должны задавать поведение AI-компонентов.

А REPOSITORY STRUCTURE должна отражать эти границы,
а не историю того, как проект развивался.