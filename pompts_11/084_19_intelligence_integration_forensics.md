# PROMPT: INTELLIGENCE INTEGRATION FORENSICS & ARCHITECTURE MAPPING v1.0

## РОЛЬ

Ты — Senior AI Systems Architect + Repository Forensics Engineer.

Твоя задача — не писать новую архитектуру с нуля и не начинать реализацию.

Ты должен исследовать фактически существующую платформу после завершения Phase 4 и определить, каким образом будущий Intelligence Layer должен быть интегрирован с уже существующим кодом, контрактами, реестрами, событиями, памятью, Knowledge, Scenario, Factory и Forge.

КЛЮЧЕВОЕ ПРАВИЛО:

> REPOSITORY = SOURCE OF TRUTH.

Код важнее документации.
Тесты важнее декларативных описаний.
Runtime-поведение важнее названия класса.
Документация используется для контекста, но не может подтверждать существование механизма, если его нет в коде.

НЕ ПРИДУМЫВАЙ существующие компоненты.

НЕ СОЗДАВАЙ параллельные механизмы только потому, что они удобнее для новой архитектуры.

Если нужная функция уже существует — найди её и определи, как Intelligence должен её использовать.

Если функции нет — зафиксируй GAP.

--------------------------------------------------
## 1. ИСХОДНЫЙ КОНТЕКСТ
--------------------------------------------------

Phase 4 считается завершённой.

Она сформировала инфраструктурный фундамент платформы, включающий, среди прочего:

- Event Bus
- Plugin API
- MCP
- Telegram Bot
- Scenario Engine
- Factory / Forge механизмы
- Memory
- Knowledge
- Project / Workspace
- Scheduler
- Monitoring
- Agents
- Tool Runtime
- существующие Registry и Contracts

Однако НЕ ПРЕДПОЛАГАЙ, что перечисленное выше действительно существует именно в таком виде.

Каждый пункт необходимо подтвердить по repository.

В распоряжении имеется архив с результатами Phase 4.

Используй его как исходный material set.

Если в архиве отсутствует часть repository и невозможно подтвердить утверждение — явно укажи:

NOT VERIFIED — REPOSITORY EVIDENCE MISSING.

--------------------------------------------------
## 2. ГЛАВНАЯ ЦЕЛЬ
--------------------------------------------------

Построить:

# INTELLIGENCE INTEGRATION MAP

То есть не абстрактную архитектуру Intelligence, а карту:

EXISTING PLATFORM
        ↓
EXISTING PRIMITIVES
        ↓
INTEGRATION CONTRACTS
        ↓
INTELLIGENCE CAPABILITIES
        ↓
REAL GAPS
        ↓
MINIMAL IMPLEMENTATION PATH

Нужно установить:

1. Что уже существует.
2. Что реально работает.
3. Что можно переиспользовать.
4. Где существуют существующие точки интеграции.
5. Какие контракты уже есть.
6. Какие контракты отсутствуют.
7. Какие адаптеры необходимы.
8. Какие новые сущности действительно нужны.
9. Что НЕ нужно создавать.
10. Как построить первый Intelligence Vertical Slice поверх существующей платформы.

--------------------------------------------------
## 3. ЗАПРЕТ НА ПРЕЖДЕВРЕМЕННУЮ РЕАЛИЗАЦИЮ
--------------------------------------------------

На этом этапе:

НЕ изменяй production code.

НЕ создавай новые модули.

НЕ переписывай существующие компоненты.

НЕ создавай новые Registry, EventBus, Memory, Knowledge или Scenario Engine без доказательства, что существующий механизм не подходит.

НЕ реализуй Opportunity Engine.

НЕ реализуй Evolution System.

НЕ реализуй Whim UI.

НЕ реализуй Workspace UI.

НЕ начинай Content Intelligence implementation.

НЕ начинай Concept Evolution implementation.

Сейчас только:

FORENSICS → MAPPING → CONTRACT DISCOVERY → GAP ANALYSIS → IMPLEMENTATION PLAN.

--------------------------------------------------
## 4. ИССЛЕДОВАНИЕ REPOSITORY
--------------------------------------------------

Исследование должно быть глубоким.

Нельзя ограничиваться:

- названиями файлов;
- README;
- заголовками;
- grep по имени;
- документацией без проверки кода.

Для каждого важного компонента:

1. Найди файл.
2. Прочитай реализацию.
3. Определи public API.
4. Определи входы.
5. Определи выходы.
6. Определи состояние.
7. Определи storage.
8. Определи зависимости.
9. Найди вызывающий код.
10. Найди тесты.
11. Если возможно — проследи реальный execution path.
12. Зафиксируй evidence.

Особенно исследовать:

core/
runtime/
scripts/
projects/
tests/
data/
contracts/
registries/
plugins/
MCP/
event system/
memory/
knowledge/
scenario/
factory/
forge/
agent runtime/

Используй фактическую структуру repository, а не предполагаемую.

--------------------------------------------------
## 5. TRACEABILITY
--------------------------------------------------

Каждое архитектурно значимое утверждение должно иметь provenance.

Минимальный формат:

FACT
  → source path
  → symbol/class/function
  → behaviour

Пример:

FACT:
ForgeFacade является точкой запуска Forge.

EVIDENCE:
core_02/forge_facade.py
ForgeFacade.initiate_forge()
ForgeFacade.run_chain()

BEHAVIOUR:
Scenario/role execution передаётся через ForgeFacade.

Не допускается:

"скорее всего".

"предположительно".

"архитектура должна использовать".

Если это inference:

INFERENCE

Если это предположение:

ASSUMPTION

Если это решение:

DECISION

Если это гипотеза:

HYPOTHESIS

--------------------------------------------------
## 6. ПОСТРОЙ EXISTING PLATFORM MAP
--------------------------------------------------

Сначала восстанови реальную архитектуру Phase 4.

Построй карту:

PROJECT
   ↓
WORKSPACE
   ↓
AGENT / RUNTIME
   ↓
SCENARIO
   ↓
FACTORY
   ↓
FORGE
   ↓
ARTIFACT
   ↓
MEMORY / KNOWLEDGE
   ↓
EVENTS

Но не утверждай наличие любого звена без repository evidence.

Для каждого звена укажи:

- существование;
- location;
- ответственность;
- API;
- storage;
- dependencies;
- runtime path;
- tests;
- статус.

--------------------------------------------------
## 7. ИССЛЕДОВАТЬ FACTORY / FORGE / SCENARIO ОСОБЕННО ГЛУБОКО
--------------------------------------------------

Нужно окончательно установить реальные границы:

FACTORY
vs
FORGE
vs
SCENARIO

Не переименовывай существующие сущности.

Не пытайся привести repository к заранее придуманной терминологии.

Ответь:

### FACTORY

Что является Factory в реальном коде?

Где registry?

Где passport?

Какие capabilities описываются?

Как Factory связывается с Forge?

### FORGE

Что реально выполняет Forge?

Какая точка входа?

Какой lifecycle?

Какие validation mechanisms?

### SCENARIO

Что такое Scenario?

Как он хранится?

Как обнаруживается?

Как выбирается?

Как запускается?

Есть ли distinction:

Scenario selection
vs
Scenario execution?

--------------------------------------------------
## 8. ИССЛЕДОВАТЬ MEMORY И KNOWLEDGE
--------------------------------------------------

Нужно понять, что Intelligence может использовать уже сейчас.

Исследовать:

MemoryStore
MemoryEngine
KnowledgeEngine
GraphIndex
SemanticLayer
LearningLoop
knowledge_objects
knowledge_links
events

Ответить:

Что система уже умеет:

- хранить;
- искать;
- связывать;
- классифицировать;
- обновлять;
- обучаться на feedback;
- восстанавливать context.

И главное:

можно ли поверх этого построить Intelligence State без создания новой memory system?

--------------------------------------------------
## 9. ИССЛЕДОВАТЬ EVENT / OBSERVATION LAYER
--------------------------------------------------

Исследовать:

EventBus
ProjectPulse
Scheduler
Monitoring
Git/file observers
Task events
Agent events
Plugin events
MCP events

Нужно определить:

какие события уже доступны Intelligence;

какие события отсутствуют;

какие события можно преобразовать в Signals;

нужен ли новый Signal abstraction или существующий Event достаточно выразителен.

НЕ создавать Signal abstraction только ради красивой архитектуры.

--------------------------------------------------
## 10. PROJECT INTELLIGENCE MODEL
--------------------------------------------------

После forensic analysis определить, какие реальные primitives уже позволяют построить:

PROJECT INTELLIGENCE

Минимальная концептуальная цепочка:

OBSERVE
   ↓
COLLECT
   ↓
UNDERSTAND
   ↓
CONNECT
   ↓
DISCOVER
   ↓
OPPORTUNITY
   ↓
SCENARIO
   ↓
FACTORY
   ↓
FORGE
   ↓
ARTIFACT
   ↓
MEMORY
   ↓
LEARNING

Для каждого этапа определить:

EXISTING
ADAPTER NEEDED
NEW COMPONENT NEEDED
NOT NEEDED

--------------------------------------------------
## 11. OPPORTUNITY
--------------------------------------------------

Пока Opportunity Engine не реализовывать.

Нужно только определить его минимальный контракт.

Исследовать:

какие существующие механизмы могут быть его входами;

какие данные ему доступны;

где должен храниться Opportunity;

как связать Opportunity с Project;

как связать Opportunity с Scenario;

как сохранить lineage;

как реализовать:

ACTIVE
DEFERRED
READY
COMPLETED
DORMANT / REACTIVATABLE

Особое правило:

DEFERRED ≠ DELETED.

Если пользователь сейчас не выбирает идею, это не означает, что система должна забыть её.

Не придумывай lifecycle окончательно без evidence и architectural reasoning.

Разделяй:

FACT
PROPOSED CONTRACT
DECISION.

--------------------------------------------------
## 12. WHIM
--------------------------------------------------

Whim рассматривать как отдельный lightweight input mechanism.

Исследовать:

существуют ли уже аналоги;

quick capture;

notes;

events;

user input;

Telegram capture;

chat input;

task input.

Если существующего механизма достаточно — предложить adapter.

Если нет — описать минимальный новый primitive.

Whim не должен автоматически превращаться в Opportunity.

Связь:

WHIM
 ↓
CLASSIFICATION / ANALYSIS
 ↓
POSSIBLE OPPORTUNITY

--------------------------------------------------
## 13. CONCEPT EVOLUTION НЕ РЕАЛИЗОВАТЬ
--------------------------------------------------

Concept Evolution System является отдельным будущим intelligence capability.

Не смешивать его с Project Intelligence.

Зафиксировать только потенциальную интеграционную точку:

IDEA EXPLORER
      ↓
CONCEPT EVOLUTION SYSTEM
      ↓
MATURE CONCEPT
      ↓
PROMPT ARCHITECT
      ↓
SCENARIO / FACTORY

C-A:

Concept Evolution Lab

C-B:

Adaptive Concept Evolution

C-C:

Meta-Evolution

Evolution Memory:

shared evolutionary memory.

Но НЕ создавать код.

НЕ создавать отдельную parallel platform.

--------------------------------------------------
## 14. КОНТРАКТНЫЙ СЛОЙ
--------------------------------------------------

На основании forensic analysis определить существующие контракты:

Project Contract
Agent Contract
Runtime Contract
Scenario Contract
Factory Contract
Forge Contract
Artifact Contract
Memory Contract
Knowledge Contract
Event Contract
Plugin Contract
MCP Contract

Для каждого:

EXISTS
PARTIAL
MISSING
UNKNOWN

Если контракт существует:

указать реальный файл и API.

Если контракт отсутствует:

описать только минимальный required contract.

--------------------------------------------------
## 15. INTEGRATION MATRIX
--------------------------------------------------

Создать таблицу:

| Intelligence Capability | Existing Primitive | Evidence | Adapter | New Code | Risk |
|---|---|---|---|---|---|

Минимальные capability:

OBSERVE
COLLECT
UNDERSTAND
CONNECT
DISCOVER
OPPORTUNITY
SELECT SCENARIO
EXECUTE
VALIDATE
ACCUMULATE
LEARN
REACTIVATE
TRACE
PROVENANCE

--------------------------------------------------
## 16. НЕ СОЗДАВАТЬ ДУБЛИКАТЫ
--------------------------------------------------

Создай отдельный раздел:

# DO NOT BUILD

В него помести всё, что уже существует.

Например:

DO NOT BUILD:
- second EventBus
- second Memory system
- second Knowledge engine
- second Scenario Registry
- second Forge executor
- second Agent runtime
- second scheduler
- second plugin system
- second MCP layer

Но каждое утверждение должно быть подтверждено repository.

--------------------------------------------------
## 17. GAPS
--------------------------------------------------

Создай Gap Map:

G0 = already exists
G1 = adapter / integration
G2 = contract extension
G3 = genuinely new primitive
G4 = architectural conflict

Для каждого GAP:

- description
- evidence
- why existing mechanism insufficient
- minimal solution
- dependencies
- risk.

--------------------------------------------------
## 18. FIRST VERTICAL SLICE
--------------------------------------------------

После исследования предложи ОДИН минимальный vertical slice.

Не больше одного.

Цель:

проверить реальную цепочку:

INPUT
 ↓
INTELLIGENCE
 ↓
OPPORTUNITY
 ↓
SCENARIO
 ↓
FACTORY
 ↓
FORGE
 ↓
ARTIFACT
 ↓
MEMORY

Но состав цепочки должен быть адаптирован к фактическому repository.

Если какой-то элемент уже существует — использовать его.

Если отсутствует — добавить минимальный adapter/primitive.

Не создавать полноценный Intelligence Engine.

Критерий:

ONE REAL END-TO-END FLOW.

--------------------------------------------------
## 19. DOCUMENTATION ↔ CODE CONSISTENCY
--------------------------------------------------

Обязательно провести отдельный аудит:

DOCUMENTATION
       ↕
      CODE

Найти:

- documentation describing missing code;
- code missing from documentation;
- obsolete architecture;
- duplicated terminology;
- outdated contracts;
- contradictory lifecycle definitions;
- claims without evidence.

Для каждого:

DOC CLAIM
CODE REALITY
STATUS
ACTION

--------------------------------------------------
## 20. TRACEABILITY GRAPH
--------------------------------------------------

Если в repository уже существует механизм anchors/tags/traceability — исследовать его.

Если нет:

предложить минимальную модель.

Идея:

DOCUMENT
  ↓
SECTION
  ↓
PARAGRAPH
  ↓
ANCHOR / TAG
  ↓
CODE SYMBOL
  ↓
TEST
  ↓
RUNTIME PATH

Цель:

позволить определить:

"какой конкретный код реализует этот абзац документа?"

и наоборот:

"какой документ объясняет этот конкретный код?"

НЕ внедрять систему автоматически.

Только исследовать существующее состояние и предложить минимальный контракт.

--------------------------------------------------
## 21. TAGGING
--------------------------------------------------

Исследовать возможность семантических тегов для документации.

Например:

@concept
@contract
@decision
@requirement
@implementation
@evidence
@invariant
@gap
@runtime
@test

Но не добавлять теги механически.

Нужно определить:

- нужны ли они;
- где;
- какой формат;
- как они будут связаны с graph;
- как использовать их для retrieval;
- как избежать semantic noise.

--------------------------------------------------
## 22. FINAL ARCHITECTURAL DECISION
--------------------------------------------------

В конце дай однозначный вывод.

Не задавай пользователю вопрос:

"что выбрать?"

Ты должен сам сделать архитектурную рекомендацию на основании forensic evidence.

Формат:

DECISION

Мы должны:

...

Потому что:

...

Мы НЕ должны:

...

Следующий шаг:

...

--------------------------------------------------
## 23. REQUIRED OUTPUT
--------------------------------------------------

Создай полный набор артефактов:

01_REPOSITORY_REALITY_MAP.md

02_PHASE4_COMPONENT_MAP.md

03_INTELLIGENCE_INTEGRATION_MAP.md

04_CONTRACT_MATRIX.md

05_EXISTING_REUSE_MAP.md

06_GAP_MAP.md

07_DOCUMENTATION_CODE_DRIFT.md

08_TRACEABILITY_MAP.md

09_INTELLIGENCE_DATA_FLOW.md

10_FIRST_VERTICAL_SLICE.md

11_DO_NOT_BUILD.md

12_ARCHITECTURAL_DECISION.md

13_EVIDENCE_LEDGER.md

14_EVALUATION_REPORT.md

Если какие-то документы действительно не нужны — объясни почему.

--------------------------------------------------
## 24. EVIDENCE LEDGER
--------------------------------------------------

Для каждого важного вывода:

ID
CLAIM
TYPE
SOURCE
SYMBOL
EVIDENCE
CONFIDENCE
DEPENDENCIES

Тип:

FACT
INFERENCE
ASSUMPTION
HYPOTHESIS
DECISION

--------------------------------------------------
## 25. EVALUATION GATE
--------------------------------------------------

Перед завершением проведи self-review.

Проверить:

[ ***REMOVED*** Repository реально исследован.
[ ***REMOVED*** Код прочитан, а не только filenames.
[ ***REMOVED*** Runtime paths проверены.
[ ***REMOVED*** Tests исследованы.
[ ***REMOVED*** Документация сопоставлена с кодом.
[ ***REMOVED*** Existing primitives не продублированы.
[ ***REMOVED*** Factory / Forge / Scenario разведены.
[ ***REMOVED*** Memory / Knowledge разведены.
[ ***REMOVED*** Event / Observation разведены.
[ ***REMOVED*** Intelligence не смешан с Factory.
[ ***REMOVED*** Concept Evolution не смешан с Project Intelligence.
[ ***REMOVED*** Opportunity не реализован преждевременно.
[ ***REMOVED*** First Vertical Slice существует.
[ ***REMOVED*** Каждый архитектурный вывод имеет evidence.
[ ***REMOVED*** Unknown явно обозначены.
[ ***REMOVED*** G0–G4 назначены обоснованно.
[ ***REMOVED*** Есть однозначная следующая задача.

--------------------------------------------------
## 26. ABSOLUTE ANTI-HALLUCINATION RULE
--------------------------------------------------

Если ты не нашёл реализацию:

не пиши:

"существует".

Пиши:

NOT VERIFIED.

Если нашёл только документацию:

DOCUMENTED ONLY.

Если нашёл код, но не нашёл вызывающий путь:

IMPLEMENTED / RUNTIME UNVERIFIED.

Если код вызывается и тестируется:

IMPLEMENTED / VERIFIED.

Если только тест существует:

TESTED / IMPLEMENTATION STATUS REQUIRES REVIEW.

--------------------------------------------------
## 27. НЕ ПЕРЕХОДИТЬ К IMPLEMENTATION
--------------------------------------------------

После завершения forensic work:

STOP.

Не начинай писать код.

Не изменяй repository.

Не создавай PR.

Не мигрируй database.

Не создавай новые файлы production-кода.

Твоя задача закончена после подготовки архитектурной карты и implementation plan.

--------------------------------------------------
## 28. ФИНАЛЬНЫЙ ОТЧЁТ
--------------------------------------------------

В финальном ответе предоставь:

1. Краткий Executive Summary.
2. Что Phase 4 реально создала.
3. Что из этого напрямую пригодно для Intelligence.
4. Что уже существует, но было ошибочно принято за отсутствующее.
5. Реальные gaps.
6. Главные architectural risks.
7. Integration Map.
8. Первый Vertical Slice.
9. Что НЕ нужно строить.
10. Следующий конкретный промт для implementation agent.

--------------------------------------------------
## 29. АРХИВ
--------------------------------------------------

После завершения работы обязательно создай Evaluation Package.

В архив должны войти:

- все созданные .md артефакты;
- Evidence Ledger;
- Evaluation Report;
- список исследованных файлов;
- список исследованных символов;
- список тестов, которые были использованы как evidence;
- README.md с описанием результатов;
- MANIFEST.md с SHA-256 для каждого файла.

Название архива:

INTELLIGENCE_INTEGRATION_FORENSICS_<VERSION>.tar.gz

Архив должен содержать ТОЛЬКО материалы, необходимые для оценки именно этой работы.

НЕ включай весь repository.

НЕ включай node_modules, .git, caches, virtualenv, generated binaries и прочий мусор.

--------------------------------------------------
## 30. ФИНАЛЬНЫЙ CRITERION
--------------------------------------------------

Работа считается завершённой только если другой Senior Architect, не участвовавший в исследовании, сможет взять Evaluation Package и ответить:

1. Что реально существует в Phase 4?
2. Как устроен фактический execution path?
3. Где Intelligence может подключиться?
4. Что нужно переиспользовать?
5. Что действительно нужно построить?
6. Почему именно это?
7. Как выглядит первый end-to-end slice?
8. Какие утверждения подтверждены кодом?
9. Какие являются inference?
10. Какой следующий implementation task?

Если на любой вопрос невозможно ответить из Evaluation Package — forensic work считается неполным.

# END OF PROMPT