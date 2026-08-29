

PROMPT — PLATFORM ARCHITECTURAL FORENSICS: WORKSPACE OS AS INTELLIGENT PROJECT ENVIRONMENT

РОЛЬ

Ты — Principal AI Systems Architect + Repository Forensics Engineer + Systems Reverse Engineer.

Твоя задача — не реализовывать новую архитектуру и не переписывать существующую систему.

Твоя задача — исследовать реальную платформу по коду и документации и восстановить её фактическую архитектурную модель.

Мы хотим проверить одну новую архитектурную гипотезу:

> Workspace OS — это интеллектуальная среда, в которой пользователь создаёт и развивает проекты, а Intelligence помогает ему превращать сырые мысли и намерения в реализованные результаты через Scenario → Factory → Forge → Agents/Tools → Artifacts.



Но это гипотеза, а не канон.

Ты обязан установить:

1. что из этой модели уже существует;


2. что существует, но называется иначе;


3. что существует частично;


4. что концептуально описано в документации, но не подтверждается кодом;


5. что в коде существует, но не отражено в документации;


6. где наша новая модель не соответствует реальной архитектуре;


7. какие важные части системы мы вообще сейчас не учитываем.




---

0. ГЛАВНОЕ ПРАВИЛО

НЕ ПОДГОНЯЙ РЕПОЗИТОРИЙ ПОД НАШУ МОДЕЛЬ

Наша модель:

WHIM
  ↓
WORKSPACE OS
  ↓
WORKSPACE
  ↓
PROJECT
  ↓
INTELLIGENCE
  ↓
SCENARIO
  ↓
FACTORY
  ↓
FORGE
  ↓
AGENTS / SKILLS / TOOLS
  ↓
ARTIFACT
  ↓
PROJECT
  ↓
INTELLIGENCE

— является исследовательской гипотезой.

Необходимо проверить её против repository reality.

Если реальная система устроена иначе — так и зафиксируй.

Не переименовывай существующие компоненты концептуально только ради красивого соответствия.


---

1. ОСНОВНОЙ ВОПРОС ИССЛЕДОВАНИЯ

Ответь на главный вопрос:

> «Что на самом деле представляет собой существующая платформа Freebuff / Workspace OS как система?»



Не:

> «Как её можно было бы построить».



А:

> «Как она реально построена сейчас?»



Исследование должно быть основано прежде всего на:

CODE
  >
TESTS
  >
CONFIG / MANIFESTS
  >
RUNTIME BEHAVIOR
  >
DOCUMENTATION
  >
COMMENTS
  >
ASSUMPTIONS


---

2. ИССЛЕДУЙ НЕ ТОЛЬКО FACTORY / FORGE

Особое требование.

Предыдущие исследования были сфокусированы преимущественно на:

Scenario
Factory
Forge
Opportunity
Content Intelligence

Это недостаточно.

Теперь исследование должно охватить всю систему, включая:

USER / HUMAN LAYER

Как человек взаимодействует с системой?

User
 ↓
Chat / UI / Telegram / CLI / Workspace
 ↓
Intent
 ↓
System

Что реально происходит после пользовательского действия?


---

INTELLIGENCE / BRAIN LAYER

Исследуй:

Intelligence;

reasoning;

planning;

decision making;

context;

project understanding;

recommendation;

orchestration;

memory;

knowledge;

learning;

feedback;

agent collaboration;

multi-agent interaction.


Особенно важно установить:

> Есть ли уже в системе отдельное понятие Intelligence / Brain или мы сейчас только концептуально его формируем?



Не предполагай.

Докажи кодом.


---

3. «ТОВАРИЩ» ПОЛЬЗОВАТЕЛЯ

Отдельно исследуй концепцию, которую мы сейчас называем условно:

> AI companion / AI collaborator / AI brain / товарищ



Пользователь не просто отдаёт системе команды.

В предполагаемой модели рядом с пользователем существует интеллектуальный слой, который может:

обсуждать
анализировать
задавать вопросы
предлагать
помнить
искать
критиковать
планировать
передавать задачи
контролировать исполнение
учиться

Установи:

Есть ли такое уже?

Если да:

где;

какие компоненты;

какие агенты;

кто принимает решения;

кто хранит контекст;

кто инициирует работу;

как агенты взаимодействуют;

как пользователь влияет на них.


Если нет:

зафиксируй как архитектурный gap, а не как ошибку.


---

4. AGENT LAYER

Не своди Agent к простому:

> «исполнитель промпта».



Исследуй всю модель агентов.

Нужно понять:

Agent
Agent Role
Agent Runtime
Agent Skill
Agent Tool
Agent Memory
Agent State
Agent Collaboration
Agent Orchestration
Agent Lifecycle

Ответь:

Агент:

исполнитель?

советник?

исследователь?

планировщик?

критик?

оркестратор?

постоянный участник проекта?

временный worker?

всё перечисленное в разных контекстах?


Есть ли:

Agent → Agent
Agent → Intelligence
Intelligence → Agent
Project → Agent
Agent → Project


---

5. WORKSPACE OS

Исследуй Workspace OS как самостоятельный уровень.

Установи реальные отношения:

Workspace OS
      │
Workspace
      │
Project

или другую фактическую иерархию.

Исследуй:

Workspace;

Project;

sessions;

tasks;

files;

memory;

knowledge;

artifacts;

users;

agents;

tools;

events;

plugins;

runtime;

permissions;

state.


Особенно важно:

> Что является границей проекта?



И:

> Что гарантированно принадлежит одному проекту, а что является глобальным ресурсом Workspace OS?




---

6. PROJECT

Исследуй Project не как папку.

Установи, является ли Project уже:

контейнером
контекстом
состоянием
историей
knowledge boundary
execution boundary
agent boundary
security boundary
artifact boundary

или пока только частью этого.

Покажи реальные связи.


---

7. WHIM → PROJECT

Исследуй путь:

RAW THOUGHT
    ↓
WHIM
    ↓
IDEA
    ↓
CONCEPT
    ↓
PROJECT

Проверь:

существует ли Whim;

существует ли capture;

есть ли быстрый вход мысли;

сохраняется ли provenance;

можно ли превратить мысль в проект;

существует ли lifecycle;

существует ли deferred state;

сохраняются ли «отложенные» идеи.


Если Whim отсутствует — не создавай его мысленно.


---

8. PROJECT → INTELLIGENCE

Исследуй:

> Как система понимает, что происходит внутри проекта?



Найди конкретный код.

Нужно восстановить:

Project State
      ↓
Context
      ↓
Knowledge
      ↓
Memory
      ↓
Observation
      ↓
Reasoning
      ↓
Decision

Если какой-либо переход отсутствует — указать.


---

9. INTELLIGENCE → SCENARIO

Исследуй:

> Кто решает, ЧТО нужно делать?



Не предполагай, что это Scenario Registry.

Найди реальный механизм.

Например:

User
 ↓
Agent
 ↓
Planner
 ↓
Scenario

или:

Intelligence
 ↓
Scenario Registry

или совершенно другую модель.

Зафиксируй фактический execution path.


---

10. SCENARIO

Исследуй Scenario как архитектурную сущность.

Установи:

что такое Scenario в коде;

что такое Scenario Manifest;

кто его создаёт;

кто выбирает Scenario;

кто его запускает;

может ли Scenario быть динамическим;

может ли Scenario вызывать Factory;

может ли Scenario вызывать Forge;

какие ограничения существуют.


Покажи:

USER / INTELLIGENCE
        ↓
      SCENARIO
        ↓
       ?


---

11. FACTORY

Теперь исследуй Factory без предположения, что существующий Forge = Factory.

Проверить:

> Есть ли реальная Factory abstraction?



Если есть:

где;

контракт;

registry;

lifecycle;

interface;

capabilities;

inputs;

outputs;

ownership.


Если нет:

> Factory = концептуальный gap.



Также исследуй возможность:

Research Factory
Content Factory
Software Factory
Design Factory
Image Factory
Video Factory
Analysis Factory

Но не проектируй их.

Только установи, позволяет ли существующая архитектура такое расширение.


---

12. FORGE

Исследуй Forge отдельно.

Нужно установить:

> Что фактически является Forge?



Не использовать заранее наше определение.

Найти:

ForgeFacade;

ForgePipeline;

ForgeRegistry;

forge lifecycle;

chain;

stages;

roles;

execution;

artifacts;

validation.


И ответить:

Forge — это:

A. capability?

B. production pipeline?

C. executor?

D. factory instance?

E. workflow?

F. другое?

Можно выбрать несколько уровней, если repository показывает, что термин используется неоднородно.


---

13. AGENT / SKILL / TOOL

Восстановить реальную производственную цепочку:

Factory
 ↓
Forge
 ↓
Agent
 ↓
Skill
 ↓
Tool

или фактический вариант.

Особенно важно понять:

> Кто отвечает за наличие способности выполнить действие?



Например:

если Research Forge должен исследовать сайт, а инструмента для этого нет:

Forge
 ↓
Agent
 ↓
Skill
 ↓
Tool

Кто обнаруживает отсутствие capability?

Кто создаёт/подключает её?

Кто принимает решение использовать внешний runtime?


---

14. ARTIFACT

Исследуй конечный результат.

Что в системе считается Artifact?

файл;

отчёт;

код;

изображение;

документ;

данные;

deployment;

другое?


Есть ли:

Artifact ID
Artifact lineage
Artifact provenance
Artifact validation
Artifact version
Artifact → Project
Artifact → Agent
Artifact → Scenario
Artifact → Forge


---

15. PROJECT MEMORY / KNOWLEDGE

Очень важно проверить нашу аналогию с тетрадью.

Нужно установить:

> Есть ли в платформе единое место, где сохраняется история развития проекта?



Или информация сейчас разложена:

Memory
Knowledge
Files
Events
Logs
Artifacts
Tasks
Databases

Если разложена — показать.

Особенно интересует:

> Можно ли восстановить путь:



Whim
 ↓
Idea
 ↓
Discussion
 ↓
Decision
 ↓
Scenario
 ↓
Execution
 ↓
Artifact
 ↓
Result
 ↓
Next Decision

Если нет — показать разрыв provenance.


---

16. FEEDBACK LOOP

Проверить:

Artifact
 ↓
Evaluation
 ↓
Observation
 ↓
Learning
 ↓
Project State
 ↓
Next Decision

Есть ли реальный feedback loop?

Или сейчас система преимущественно:

INPUT
 ↓
EXECUTION
 ↓
OUTPUT


---

17. PLUGINS / EXTERNAL CAPABILITIES

Исследовать:

Plugin
Runtime
MCP
External Tool
External Agent
External Project

и их границы.

Особенно важно:

> Может ли внешний capability быть подключён к Project, не получая доступ ко всему Workspace OS?



Это пригодится для будущего:

Project
 ↓
Gateway
 ↓
External Capability

Но без проектирования безопасности на этом этапе — только forensic-факт.


---

18. ПРОВЕРКА НАШЕЙ МЕТАФОРЫ АВТОМОБИЛЯ

После полного исследования отдельно сопоставь repository с моделью:

Человек
 ↓
Whim
 ↓
Workspace OS
 ↓
Workspace
 ↓
Project
 ↓
Intelligence / Companion
 ↓
Scenario
 ↓
Factory
 ↓
Forge
 ↓
Agents
 ↓
Skills
 ↓
Tools
 ↓
Artifacts
 ↓
Project
 ↓
Intelligence

Для КАЖДОГО элемента:

Element	Exists	Exact implementation	Partial	Concept only	Missing	Evidence



Но если фактическая архитектура отличается — предложи реальную схему вместо этой.


---

19. ОСОБЫЙ АНАЛИЗ: ЧТО МЫ НЕ ВИДИМ

Это обязательный раздел.

Ответь:

> Какие крупные подсистемы платформы мы сейчас вообще не учитываем, потому что смотрим на неё через призму Intelligence → Factory → Forge?



Например потенциально:

Identity
Security
Permissions
Gateway
Communication
Collaboration
Agent Mesh
Runtime
Plugin System
UI
Event System
Observability
Memory
Knowledge
Evolution
Research
Project Management
Task System
Billing
External Integrations

Но не утверждай их наличие заранее.

Найди реальные подсистемы.


---

20. TRACEABILITY RULE

Каждое существенное утверждение должно иметь evidence.

Формат:

CLAIM
↓
FILE
↓
SYMBOL / CLASS / FUNCTION
↓
BEHAVIOR

Например:

Claim:
Forge является исполнительным мостом.

Evidence:
core_02/forge_facade.py
ForgeFacade.initiate_forge()
ForgeFacade.run_chain()

Behavior:
...

Нельзя писать:

> «Платформа умеет X»



без указания, где именно это происходит.


---

21. НЕ ДОВЕРЯЙ ДОКУМЕНТАЦИИ БЕЗ ПРОВЕРКИ

Если документация говорит:

> «Phase 4 completed»



это НЕ означает автоматически, что Phase 4 действительно реализована.

Проверить код.

Состояния:

DOCUMENTED
IMPLEMENTED
TESTED
EXECUTABLE
OBSERVED

разделять.


---

22. НЕ ПИСАТЬ КОД

В рамках этого задания:

НЕ ИЗМЕНЯТЬ REPOSITORY.

Не создавать:

новые модули;

новые контракты;

новые Factory;

новые Intelligence;

Opportunity Engine;

Whim Engine;

adapters.


Это forensic + architecture reconstruction stage.


---

23. НЕ ПРИНИМАТЬ АРХИТЕКТУРНЫЕ РЕШЕНИЯ

Не писать:

> «Нужно сделать FactoryRegistry».



Вместо:

> «FactoryRegistry отсутствует; существующий механизм X частично выполняет похожую функцию».



Рекомендации можно дать только после полного forensic analysis и отдельно пометить:

FACT
INFERENCE
RECOMMENDATION


---

24. ФИНАЛЬНЫЙ ВОПРОС

После полного исследования ответь:

> Если забыть все наши предыдущие документы и посмотреть только на реальную платформу — какой архитектурой она является сегодня?



И отдельно:

> Насколько наша модель Workspace OS + Intelligence + Scenario + Factory + Forge соответствует реальности?



Оценка:

0% — практически не соответствует
25%
50%
75%
90%
100%

Но процент должен быть обоснован.


---

25. REQUIRED OUTPUT

Создай итоговый документ:

PLATFORM_ARCHITECTURE_FORENSICS_V2.md

Структура:

A. Executive Summary

B. Repository Reality Map

C. Current System Architecture

D. User → Workspace → Project Flow

E. Intelligence / Brain Analysis

F. Agent Architecture

G. Workspace / Project Model

H. Scenario Architecture

I. Factory Analysis

J. Forge Analysis

K. Agent / Skill / Tool Architecture

L. Artifact Architecture

M. Memory / Knowledge / Context

N. Event / Orchestration / Runtime

O. Plugin / MCP / External Integration

P. Feedback / Learning Loop

Q. Current Execution Paths

R. Architecture Hypothesis Validation

S. Missing / Partial / Conceptual Components

T. Architectural Blind Spots

U. Contradictions

V. Provenance / Traceability Gaps

W. Recommended Canonical Architecture
   (ТОЛЬКО ПОСЛЕ FORENSICS)

X. Roadmap Implications

Y. Evidence Ledger

Z. Final Verdict


---

26. ОСОБЕННО ВАЖНО — РАЗДЕЛ W

В конце, только после исследования, попробуй построить:

CURRENT REAL ARCHITECTURE

[как система реально устроена сейчас***REMOVED***

и отдельно:

TARGET ARCHITECTURAL MODEL

Whim
 ↓
Workspace
 ↓
Project
 ↓
Intelligence
 ↓
Scenario
 ↓
Factory
 ↓
Forge
 ↓
Agent / Skill / Tool
 ↓
Artifact
 ↓
Project State
 ↓
Intelligence

И показать:

CURRENT
   │
   ├── EXISTS
   ├── PARTIAL
   ├── MISSING
   └── MISALIGNED
          │
          ▼
TARGET

Не пытайся сразу “починить” CURRENT под TARGET.


---

27. ФИНАЛЬНАЯ ТАБЛИЦА

Обязательно создай:

Layer	Current Reality	Target Concept	Status	Evidence	Gap

Whim					
Workspace OS					
Workspace					
Project					
Intelligence					
Companion / AI Partner					
Agent					
Scenario					
Factory					
Forge					
Skill					
Tool					
Artifact					
Memory					
Knowledge					
Event					
Runtime					
Plugin					
Feedback					
Evolution					



---

28. EVALUATION PACKAGE

После завершения подготовь отдельный evaluation package:

architecture_forensics_v2/
│
├── PLATFORM_ARCHITECTURE_FORENSICS_V2.md
├── CURRENT_ARCHITECTURE.md
├── TARGET_MODEL_MAPPING.md
├── EXECUTION_PATHS.md
├── AGENT_ARCHITECTURE.md
├── INTELLIGENCE_ANALYSIS.md
├── FACTORY_FORGE_ANALYSIS.md
├── GAP_MAP.md
├── EVIDENCE_LEDGER.md
├── TRACEABILITY_MATRIX.md
└── README.md

Если какие-либо документы не нужны — не создавай пустышки, а объясни почему.


---

29. АРХИВ

После завершения работы обязательно собери отдельный архив только с результатами этого forensic-прохода.

Не архивируй весь repository.

Архив должен содержать:

architecture_forensics_v2_<version>.tar.gz

или .zip.

Внутри:

architecture_forensics_v2/
    ├── reports/
    ├── evidence/
    ├── mappings/
    └── README.md

Также добавь:

MANIFEST.md

с перечнем файлов и кратким описанием каждого.

Важно: архив предназначен для передачи другому архитектору на независимую оценку.


---

30. ФИНАЛЬНЫЙ ОТЧЁТ АГЕНТА

В конце не ограничивайся:

> «Forensics complete».



Дай короткое executive summary:

1. Где реально находится система сейчас?

2. Что уже является Workspace OS?

3. Что уже является Project?

4. Есть ли Intelligence?

5. Есть ли Companion / AI Brain?

6. Как реально взаимодействуют агенты?

7. Что такое Scenario в реальности?

8. Есть ли Factory?

9. Что реально является Forge?

10. Где находятся Skills / Tools?

11. Как появляется Artifact?

12. Как результат возвращается в Project?

13. Что из нашей модели автомобиля уже построено?

14. Что отсутствует?

15. Где мы ошибочно смешиваем разные уровни?

16. Какой следующий архитектурный шаг после этого forensic-прохода?


---

КРИТИЧЕСКОЕ ОГРАНИЧЕНИЕ

Не начинай с вопроса «как реализовать нашу модель».

Начни с вопроса:

> «Что уже построено?»



Затем:

> «Как оно реально связано?»



Затем:

> «Какую архитектуру фактически представляет собой система?»



И только после этого:

> «Насколько она совпадает с нашей новой моделью?»



И только в самом конце:

> «Что следует делать дальше?»



Работа считается завершённой только после полного чтения релевантного кода и документации, построения фактических execution paths, evidence ledger и создания evaluation archive.