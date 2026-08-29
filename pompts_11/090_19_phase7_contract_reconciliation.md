# PHASE 7 — CONTRACT RECONCILIATION + FACTORY / EVENT CLOSURE
## Implementation Protocol v1.0

ROLE

Ты — Senior AI Systems Architect + Repository Forensics Engineer +
Integration Engineer.

Ты работаешь НЕ с чистого листа.

Перед тобой существует уже работающая платформа Freebuff / Workspace OS,
в которой предыдущими фазами был построен значительный фундамент
Intelligence / Factory / Scenario / Forge.

Твоя задача НЕ состоит в том, чтобы заново спроектировать эту систему.

Твоя задача:

1. исследовать фактическое состояние repository;
2. сопоставить его с Phase 6 forensic package;
3. подтвердить реальные разрывы;
4. устранить ТОЛЬКО подтверждённые integration gaps;
5. замкнуть существующий execution path;
6. покрыть изменения тестами;
7. обновить документацию там, где она расходится с кодом;
8. предоставить полный evaluation package и архив изменённого среза.

============================================================
0. SOURCE OF TRUTH
============================================================

Приоритет источников:

1. работающий код;
2. тесты;
3. runtime/configuration;
4. machine-readable manifests/contracts;
5. архитектурная документация;
6. forensic reports;
7. предположения.

Документация НЕ является доказательством существования функциональности.

Если документ говорит:

"компонент существует"

ты обязан найти:

- файл;
- класс/функцию;
- caller;
- entrypoint;
- runtime path;
- storage;
- тест.

Если этого нет — компонент считается отсутствующим или partial.

НИКОГДА не реализуй систему только потому, что она описана в документации.

============================================================
1. ОБЯЗАТЕЛЬНОЕ ПРЕДВАРИТЕЛЬНОЕ ИССЛЕДОВАНИЕ
============================================================

ПЕРЕД ЛЮБЫМ ИЗМЕНЕНИЕМ КОДА:

полностью исследуй repository и Phase 6 package.

Не ограничивайся:

- README;
- заголовками;
- summary;
- названиями файлов.

Читай реальные исходники, относящиеся к задаче.

Особенно исследуй:

core_02/
scripts_01/
runtime_05/
data_13/
projects_17/
tests/
contracts/
documentation/
Phase 6 forensic package.

Обязательно проверь реальные реализации:

- FactoryRegistry;
- FactoryPassport;
- select_forge();
- Opportunity;
- OpportunityStore;
- OpportunityEngine;
- Opportunity.execute();
- ScenarioRegistry;
- ScenarioManifest;
- ForgeFacade;
- ForgePipeline;
- EventBus;
- MemoryStore;
- KnowledgeEngine;
- ProjectPulse;
- LearningLoop;
- существующие entrypoints;
- существующие тесты.

============================================================
2. PHASE 6 — BASELINE
============================================================

Phase 6 forensic package является baseline, а НЕ заменой проверки
repository.

Используй его как карту:

- что уже исследовано;
- какие claims были сделаны;
- какие integration gaps были обнаружены;
- какие contracts существуют;
- какие symbols были подтверждены;
- какие tests существуют.

Но каждое критическое утверждение Phase 6 повторно проверь
против текущего repository.

Особенно проверить два заявленных разрыва:

GAP A:
Opportunity → ForgeFacade напрямую,
минуя Factory selection.

GAP B:
Intelligence lifecycle не полностью интегрирован с EventBus.

Также проверь:

GAP C:
расхождение Opportunity contract/documentation/runtime schema.

Если какой-либо из этих gaps уже исправлен после Phase 6 —
НЕ исправляй его повторно.

============================================================
3. ЗАПРЕТ НА SCOPE CREEP
============================================================

В этой фазе ЗАПРЕЩЕНО строить:

- новый Content Intelligence;
- новый Opportunity Engine;
- новый Scenario Engine;
- Concept Evolution;
- C-A;
- C-B;
- C-C;
- Evolution Memory;
- Workspace UI;
- новый Knowledge Engine;
- новый Memory Engine;
- новую Factory architecture.

Эти системы относятся к следующим фазам.

Phase 7 занимается только:

CONTRACT RECONCILIATION
+
FACTORY INTEGRATION
+
EVENT INTEGRATION
+
TEST / TRACEABILITY CLOSURE.

Если обнаружишь проблему, которая не относится к этим задачам:

не реализуй её.

Зарегистрируй её в:

PHASE7_DEFERRED_ITEMS.md

с:

- problem;
- evidence;
- severity;
- recommended phase.

============================================================
4. ЦЕЛЕВАЯ АРХИТЕКТУРА
============================================================

После Phase 7 основной execution path должен соответствовать:

PROJECT
   ↓
SIGNAL / WHIM
   ↓
OPPORTUNITY
   ↓
SCENARIO
   ↓
FACTORY
   ↓
FACTORY SELECTION
   ↓
FORGE
   ↓
FORGE FACADE
   ↓
ARTIFACT
   ↓
VALIDATION
   ↓
MEMORY / KNOWLEDGE
   ↓
EVENTS
   ↓
INTELLIGENCE

Ключевое разделение:

INTELLIGENCE
= решает WHAT / WHY

SCENARIO
= определяет HOW

FACTORY
= выбирает production capability

FORGE
= выполняет production capability

AGENT
= исполнительный участник

ARTIFACT
= результат

MEMORY / KNOWLEDGE
= накопление результата и знаний

EVENT BUS
= сообщает системе, что произошло.

============================================================
5. TASK A — CONTRACT RECONCILIATION
============================================================

Исследуй реальный runtime schema Opportunity.

Сравни:

- dataclass/model;
- constructor;
- serialization;
- persistence;
- lifecycle transitions;
- callers;
- tests;
- документацию;
- machine-readable contract.

Особенно проверь заявленное Phase 6 расхождение:

documentation ≠ runtime schema.

Определи:

CANONICAL SCHEMA

После этого:

- либо обнови contract/documentation под фактический runtime;
- либо измени runtime, если документированный контракт является
  подтверждённым архитектурным источником истины.

Решение должно быть основано на evidence.

Не допускай двух разных schemas.

Добавь/обнови:

- schema contract;
- serialization contract;
- lifecycle contract;
- tests.

============================================================
6. TASK B — FACTORY CLOSURE
============================================================

Главная задача Phase 7.

Проверь текущий путь:

Opportunity.execute()

и выясни фактический call graph.

Если сейчас:

Opportunity
   ↓
ForgeFacade

то необходимо реализовать:

Opportunity
   ↓
Scenario
   ↓
FactoryRegistry
   ↓
select_forge()
   ↓
Forge
   ↓
ForgeFacade

НО:

НЕ создавай новый Forge execution mechanism.

НЕ вызывай Forge напрямую из нового слоя.

Сохрани существующий санкционированный bridge:

ForgeFacade

Factory должен отвечать за selection.

ForgeFacade должен оставаться execution boundary.

Проверь backward compatibility.

Если существующий execution path требует fallback:

реализуй его только при наличии evidence.

============================================================
7. FACTORY CONTRACT
============================================================

Factory integration должна быть machine-readable.

Минимально должны быть однозначно определены:

Factory
Factory ID
Factory capability
supported scenarios
supported forge
selection criteria
input contract
output contract
version
status

Не расширяй Factory Passport без необходимости.

Используй существующий FactoryRegistry / FactoryPassport,
если они действительно существуют в repository.

НЕ создавай параллельный registry.

============================================================
8. TASK C — EVENT CLOSURE
============================================================

Исследуй EventBus.

Определи:

- API publish;
- API subscribe;
- event storage;
- event schema;
- event naming;
- existing consumers;
- existing producers.

После этого интегрируй только необходимые Intelligence lifecycle events.

Минимально рассмотри:

whim.captured
whim.classified
whim.promoted

opportunity.created
opportunity.proposed
opportunity.advanced
opportunity.deferred
opportunity.reactivated
opportunity.executed
opportunity.completed
opportunity.failed

execution.started
execution.completed
execution.failed

НО:

не добавляй события автоматически только потому, что они перечислены
здесь.

Каждое событие должно иметь:

EVENT
SOURCE
PAYLOAD
CONSUMER
STORAGE
TEST

Если событие не нужно существующей архитектуре —
не добавляй его.

============================================================
9. EVENT CONTRACT
============================================================

Для каждого нового события определить:

event_name
event_version
event_id
timestamp
project_id
entity_id
entity_type
source
payload
correlation_id
causation_id

если эти поля соответствуют уже существующему EventBus contract.

НЕ создавай вторую event schema.

Используй существующий canonical EventBus contract.

============================================================
10. FEEDBACK LOOP
============================================================

После интеграции EventBus должна быть возможна цепочка:

OPPORTUNITY
    ↓
EXECUTION
    ↓
EVENT
    ↓
MEMORY / KNOWLEDGE
    ↓
INTELLIGENCE

Но:

НЕ реализовывай полноценный autonomous feedback engine.

Phase 7 только создаёт техническую возможность для него.

============================================================
11. TAGGING / TRACEABILITY
============================================================

Исследуй существующий:

DOCUMENT_TAGGING_PROPOSAL
и связанные Phase 6 материалы.

Не строй полноценную vector database / graph систему.

Сделай минимальный contract-level foundation,
если repository уже имеет для этого соответствующие механизмы.

Цель:

DOCUMENT PARAGRAPH
   ↓
TAG
   ↓
CONTRACT
   ↓
CODE SYMBOL
   ↓
TEST

Если реализация tagging выходит за scope Phase 7:

зафиксируй её как deferred item.

============================================================
12. CODE ↔ DOCUMENTATION RECONCILIATION
============================================================

После изменений повторно проверь документацию.

Каждое утверждение:

"X реализовано"

должно иметь:

FILE
SYMBOL
CALLER
ENTRYPOINT
TEST

Каждое утверждение:

"X является контрактом"

должно иметь:

CONTRACT
IMPLEMENTATION
VALIDATION

Создай:

PHASE7_TRACEABILITY_MATRIX.md

Формат:

| Claim | Contract | Code | Symbol | Caller | Entry Point | Test | Status |

Статусы:

CONFIRMED
PARTIAL
MISSING
DEFERRED

============================================================
13. TESTING
============================================================

Перед изменениями:

запусти baseline tests.

Зафиксируй:

- command;
- count;
- passed;
- failed;
- skipped.

После изменений:

запусти полный regression suite.

Кроме этого создай targeted tests для:

1. Opportunity schema;
2. Factory selection;
3. Opportunity → Factory;
4. Factory → ForgeFacade;
5. Event publishing;
6. Event payload;
7. lifecycle transitions;
8. persistence;
9. backward compatibility.

Критерий:

NO REGRESSION.

Если полный test suite падает:

НЕ маскируй проблему.

Исследуй причину.

============================================================
14. ОБЯЗАТЕЛЬНАЯ ПРОВЕРКА CALL GRAPH
============================================================

Для нового execution path создай:

PHASE7_CALL_GRAPH.md

Минимум:

Opportunity.execute()
    ↓
Scenario selection
    ↓
FactoryRegistry
    ↓
select_forge()
    ↓
ForgeFacade
    ↓
ForgePipeline
    ↓
Artifact
    ↓
Memory / EventBus

Для каждого перехода:

FILE
SYMBOL
CALLER
TEST

============================================================
15. OBSERVABILITY
============================================================

Для Factory selection и execution integration должны существовать
достаточные диагностические данные.

Минимум:

project_id
opportunity_id
scenario_id
factory_id
forge_id
execution_id
event_id

если эти identifiers уже существуют в платформе.

Не создавай новую observability system.

Используй существующую.

============================================================
16. SECURITY / BOUNDARY
============================================================

Не ослабляй существующие security boundaries.

Особенно:

- ForgeFacade остаётся execution boundary;
- не добавляй произвольный shell execution;
- не добавляй обход ToolRuntime;
- не позволяй Opportunity напрямую выполнять неизвестные commands;
- не добавляй network access без существующего contract.

Если обнаружишь security gap:

не расширяй scope молча.

Зарегистрируй его отдельно.

============================================================
17. IMPLEMENTATION RULE
============================================================

Минимальное изменение.

Prefer:

ADAPTER
CONTRACT FIX
INTEGRATION
TEST

over:

REWRITE
REFACTOR
NEW SUBSYSTEM.

Если существующий код можно переиспользовать —
переиспользуй.

Если существующий механизм делает 80% задачи —
не создавай второй механизм.

============================================================
18. ДОКУМЕНТАЦИЯ ПОСЛЕ КОДА
============================================================

Документация обновляется ПОСЛЕ фактической реализации.

Не наоборот.

Порядок:

REPOSITORY
 ↓
IMPLEMENTATION
 ↓
TEST
 ↓
TRACEABILITY
 ↓
DOCUMENTATION

Документ не должен описывать поведение,
которого нет в коде.

============================================================
19. ACCEPTANCE CRITERIA
============================================================

Phase 7 считается завершённой только если:

[ ***REMOVED*** Opportunity schema canonical
[ ***REMOVED*** Factory integration confirmed
[ ***REMOVED*** Opportunity does not bypass Factory
[ ***REMOVED*** ForgeFacade remains execution boundary
[ ***REMOVED*** EventBus integration confirmed
[ ***REMOVED*** Event contracts documented
[ ***REMOVED*** Event lifecycle tested
[ ***REMOVED*** Persistence verified
[ ***REMOVED*** Call graph documented
[ ***REMOVED*** Traceability matrix complete
[ ***REMOVED*** Full regression suite passes
[ ***REMOVED*** Targeted integration tests pass
[ ***REMOVED*** No duplicate registries
[ ***REMOVED*** No duplicate event systems
[ ***REMOVED*** No new parallel execution mechanism
[ ***REMOVED*** No unrelated architecture introduced
[ ***REMOVED*** Deferred work explicitly registered

============================================================
20. ОБЯЗАТЕЛЬНЫЕ OUTPUT FILES
============================================================

Создай:

01_PHASE7_BASELINE.md

02_PHASE7_REPOSITORY_FINDINGS.md

03_PHASE7_CONTRACT_RECONCILIATION.md

04_PHASE7_FACTORY_INTEGRATION.md

05_PHASE7_EVENT_INTEGRATION.md

06_PHASE7_CALL_GRAPH.md

07_PHASE7_TRACEABILITY_MATRIX.md

08_PHASE7_TEST_REPORT.md

09_PHASE7_DEFERRED_ITEMS.md

10_PHASE7_FINAL_REPORT.md

Если соответствующий существующий документ уже имеет canonical name,
не создавай duplicate — обнови существующий.

============================================================
21. MACHINE-READABLE REPORT
============================================================

Создай:

PHASE7_EVALUATION.json

Минимальная структура:

{
  "phase": "7",
  "status": "...",
  "baseline": {***REMOVED***,
  "repository_findings": [***REMOVED***,
  "contracts": [***REMOVED***,
  "factory_integration": {***REMOVED***,
  "event_integration": {***REMOVED***,
  "call_graph": [***REMOVED***,
  "tests": {***REMOVED***,
  "traceability": [***REMOVED***,
  "deferred": [***REMOVED***,
  "changed_files": [***REMOVED***,
  "risks": [***REMOVED***
***REMOVED***

Все claims должны ссылаться на реальные:

file
symbol
test

============================================================
22. CHANGE MANIFEST
============================================================

Создай:

PHASE7_CHANGE_MANIFEST.md

Список:

ADDED
MODIFIED
DELETED

Для каждого:

path
reason
architectural purpose
tests

============================================================
23. FINAL FORENSICS
============================================================

После реализации НЕ останавливайся на:

"tests passed".

Повтори forensic inspection.

Проверь:

DOCUMENTATION
      ↕
CONTRACT
      ↕
CODE
      ↕
CALL GRAPH
      ↕
ENTRYPOINT
      ↕
EVENT
      ↕
STORAGE
      ↕
TEST

Ищи:

- мёртвые contracts;
- unused symbols;
- bypass paths;
- duplicate registries;
- undocumented entrypoints;
- events без consumers;
- consumers без producers;
- документацию без implementation;
- implementation без documentation;
- tests, которые не проверяют реальный runtime path.

============================================================
24. НЕ ОСТАНАВЛИВАЙСЯ НА ВОПРОСАХ
============================================================

Не спрашивай пользователя:

"Что выбрать?"

если ответ можно получить из:

repository
contracts
Phase 6 package
tests
architecture rules.

При конфликте:

1. исследуй;
2. зафиксируй evidence;
3. выбери минимальное решение,
   соответствующее существующей архитектуре;
4. продолжай.

Останавливайся только при реальном blocker,
который невозможно разрешить из repository.

============================================================
25. ФИНАЛЬНЫЙ ОТЧЁТ
============================================================

В конце ответь:

1. Что было найдено?
2. Что было реально исправлено?
3. Какие файлы изменены?
4. Какие contracts стали canonical?
5. Как теперь проходит Opportunity → Factory → Forge?
6. Какие события реально публикуются?
7. Какие события потребляются?
8. Какие tests подтверждают integration?
9. Что осталось deferred?
10. Есть ли архитектурные расхождения?
11. Какой следующий шаг Phase 8?

Не писать:

"всё готово"

без evidence.

============================================================
26. ОБЯЗАТЕЛЬНЫЙ EVALUATION ARCHIVE
============================================================

После завершения работы ОБЯЗАТЕЛЬНО создай отдельный архив:

PHASE7_EVALUATION_<VERSION>.tar.gz

В архив должны попасть ТОЛЬКО материалы,
необходимые для последующей независимой оценки Phase 7.

Минимум:

/evaluation/
    Phase7 reports
    contracts
    traceability
    call graph
    test report
    machine-readable JSON
    change manifest

/relevant_code/
    только изменённые файлы
    и необходимые связанные файлы для проверки integration path

/relevant_tests/
    новые и изменённые тесты
    плюс необходимые существующие integration tests

/docs/
    обновлённая документация, непосредственно относящаяся к Phase 7

НЕ клади в evaluation archive:

- весь repository;
- .git;
- caches;
- virtual environments;
- node_modules;
- generated binaries;
- secrets;
- API keys;
- credentials;
- огромные unrelated datasets.

Архив должен быть достаточным для независимой проверки Phase 7,
но минимальным по размеру.

Также создай:

PHASE7_EVALUATION_<VERSION>.sha256

============================================================
27. ФИНАЛЬНЫЙ СТАТУС
============================================================

В финальном отчёте используй один из статусов:

COMPLETE
COMPLETE_WITH_DEFERRED
PARTIAL
BLOCKED

Не объявляй COMPLETE, если хотя бы один Acceptance Criterion
не подтверждён evidence.

============================================================
28. NEXT PHASE
============================================================

После завершения Phase 7 НЕ начинай Phase 8 автоматически.

Только подготовь:

NEXT_PHASE_RECOMMENDATION.md

где укажи:

- что Phase 7 теперь даёт следующей фазе;
- какие реальные интерфейсы готовы;
- какие ограничения существуют;
- какой минимальный следующий vertical slice рекомендуется.

Следующая фаза будет посвящена развитию:

SCENARIO INTELLIGENCE
и затем
CONTENT FACTORY.

Concept Evolution / C-A / C-B / C-C
в эту фазу НЕ входят.

============================================================
FINAL PRINCIPLE
============================================================

НЕ СТРОЙ НОВУЮ ПЛАТФОРМУ.

ЗАМКНИ УЖЕ СУЩЕСТВУЮЩУЮ.

Не:

DOCUMENT → CODE

а:

REPOSITORY
    ↓
FORENSICS
    ↓
CONTRACT
    ↓
IMPLEMENTATION
    ↓
TEST
    ↓
TRACEABILITY
    ↓
DOCUMENTATION

И конечный execution path должен быть доказан:

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
EVENT
    ↓
MEMORY / KNOWLEDGE
    ↓
INTELLIGENCE

Каждая стрелка должна иметь:

реальный код,
реальный symbol,
реальный caller,
реальный entrypoint,
и реальный тест.

Только после этого Phase 7 считается выполненной.