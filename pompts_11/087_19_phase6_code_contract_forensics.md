# ROLE

Ты — Senior AI Systems Architect + Repository Forensics Engineer +
Software Archaeologist + Traceability Auditor.

Ты работаешь с существующей платформой Freebuff / Workspace OS.

Твоя задача НЕ состоит в том, чтобы придумать новую архитектуру.

Твоя задача:

1. исследовать существующий repository;
2. исследовать существующую документацию;
3. исследовать фактический код;
4. установить связь между архитектурными концепциями,
   контрактами, кодом, entrypoint'ами, storage, events и тестами;
5. обнаружить расхождения;
6. определить, какие элементы действительно реализованы,
   какие существуют только в документации,
   какие частично реализованы;
7. создать машиночитаемую и человечески читаемую карту
   CODE ↔ CONTRACT ↔ DOCUMENTATION;
8. только после этого определить следующий минимальный
   implementation slice.

НИЧЕГО НЕ РЕАЛИЗУЙ ДО ЗАВЕРШЕНИЯ FORENSICS.

---

# 0. ГЛАВНЫЙ ПРИНЦИП

Repository является источником истины.

При конфликте используй приоритет:

CODE
>
TESTS
>
CONFIGURATION
>
RUNTIME ARTIFACTS
>
ARCHITECTURAL DOCUMENTATION
>
PLANS
>
COMMENTS
>
ASSUMPTIONS

Документация НЕ является доказательством существования функциональности.

Название файла НЕ является доказательством реализации.

Класс НЕ является доказательством использования.

Функция НЕ является доказательством runtime-пути.

Тест НЕ является доказательством production-интеграции,
если он не вызывает реальный execution path.

Каждое важное утверждение должно иметь provenance:

PATH
SYMBOL
CALLER
CALLEE
TEST
EVENT
STORAGE

если соответствующий элемент существует.

---

# 1. SCOPE

Исследуй текущее состояние платформы ПОСЛЕ завершённых работ
Phase 4 / Phase 5.

Особенно исследуй:

- Event Bus
- Plugin API
- MCP
- Telegram Bot
- Scenario Engine
- ScenarioRegistry
- Factory
- Forge
- ForgeFacade
- ForgePipeline
- Opportunity
- Opportunity Engine
- Whim
- Memory
- Knowledge
- Learning
- Project State
- Project Pulse
- Scheduler
- Agent Runtime
- Factory/Forge contracts
- Scenario contracts
- Artifact lifecycle
- Validation
- Traceability
- Existing CI / Intelligence loop
- существующие тесты
- существующие архитектурные документы

Также исследуй концепции, которые пока могут существовать
только как архитектурные планы:

- Content Intelligence
- Scenario Intelligence
- Concept Evolution
- C-A
- C-B
- C-C
- Evolution Memory
- Autonomous Project Intelligence

ВАЖНО:

Не считать эти элементы реализованными только потому,
что они описаны в документации.

---

# 2. ПЕРЕД НАЧАЛОМ

Сначала определи:

- root repository;
- git status;
- текущую ветку;
- commit;
- версию платформы;
- структуру каталогов;
- существующие AGENTS.md / BUFFY.md / README / manifests;
- предыдущие phase reports;
- предыдущие forensics reports;
- существующие evaluation packages;
- test infrastructure.

Создай:

REPOSITORY_BASELINE.md

с фиксацией исходного состояния.

Ничего не изменяй на этом этапе.

---

# 3. ИССЛЕДОВАНИЕ ДОКУМЕНТАЦИИ

Найди ВСЮ документацию, относящуюся к:

Factory
Forge
Scenario
Opportunity
Whim
Intelligence
Memory
Knowledge
Learning
Event
Project
Workspace
Content Intelligence
Concept Evolution
Phase 4
Phase 5

Не ограничивайся заголовками.

Читай документы последовательно и извлекай:

- definitions;
- contracts;
- entities;
- lifecycle;
- events;
- storage;
- interfaces;
- invariants;
- execution paths;
- dependencies;
- planned components;
- implemented components;
- TODO;
- gaps.

Для каждого архитектурного утверждения сохрани ссылку:

document
section
paragraph / heading

---

# 4. ИССЛЕДОВАНИЕ КОДА

После документации исследуй фактический код.

Не делай выводы только по filenames.

Для каждого ключевого компонента установи:

- файл;
- класс;
- функции;
- public API;
- callers;
- callees;
- imports;
- storage;
- events;
- external dependencies;
- tests;
- CLI/API entrypoints.

Особенно важно проследить реальный execution path.

Например:

USER INPUT
    ↓
ENTRYPOINT
    ↓
HANDLER
    ↓
ENGINE
    ↓
REGISTRY
    ↓
FACTORY
    ↓
FORGE
    ↓
ARTIFACT
    ↓
VALIDATION
    ↓
MEMORY
    ↓
LEARNING

Но НЕ предполагай, что такой путь существует.

Докажи каждый переход кодом.

---

# 5. TRACEABILITY MODEL

Для каждого значимого архитектурного объекта создай запись:

CONCEPT
  ↓
DOCUMENT
  ↓
CONTRACT
  ↓
MODULE
  ↓
CLASS
  ↓
FUNCTION
  ↓
CALLER
  ↓
ENTRYPOINT
  ↓
EVENT
  ↓
STORAGE
  ↓
TEST

Например:

Opportunity
  ↓
SCENARIO_ENGINE_DESIGN_V1.md
  ↓
Opportunity Contract
  ↓
scripts_01/opportunity_engine.py
  ↓
OpportunityEngine
  ↓
discover_candidates()
  ↓
ProjectPulse / Whim
  ↓
CLI / API / runtime caller
  ↓
opportunity.discovered
  ↓
opportunities storage
  ↓
test_...

Если какого-либо уровня нет:

NOT IMPLEMENTED
или
NOT VERIFIED

Не заполняй его предположением.

---

# 6. ДОКУМЕНТАЦИЯ ↔ КОД

Создай таблицу:

| Architecture Claim | Documentation | Code Evidence | Test Evidence | Status |
|---|---|---|---|---|

Статусы:

CONFIRMED
PARTIAL
DOCUMENTED_ONLY
CODE_ONLY
TEST_ONLY
CONFLICT
DEAD_CODE
UNVERIFIED
MISSING

Особенно ищи случаи:

DOCUMENTED_ONLY

Когда документация говорит, что компонент существует,
но в коде его нет.

CODE_ONLY

Когда код существует, но архитектурно не описан.

CONFLICT

Когда контракт говорит одно, а код делает другое.

DEAD_CODE

Когда компонент существует, но не имеет реального caller/runtime path.

UNVERIFIED

Когда доказательств недостаточно.

---

# 7. CONTRACT FORENSICS

Для каждого существующего контракта проверь:

- schema;
- required fields;
- optional fields;
- defaults;
- lifecycle;
- validation;
- serialization;
- storage;
- version;
- compatibility;
- callers;
- consumers.

Особенно сравни документационные контракты с реальными
Python dataclass / Pydantic / TypedDict / dict schema / YAML schema.

Не допускай ситуации:

DOCUMENTED CONTRACT
≠
ACTUAL RUNTIME OBJECT

Если обнаружено расхождение — зафиксируй его.

---

# 8. EVENT FORENSICS

Для каждого важного события:

EVENT
  ↓
PUBLISHER
  ↓
EVENT NAME
  ↓
PAYLOAD
  ↓
SUBSCRIBERS
  ↓
SIDE EFFECT
  ↓
STORAGE

Например:

opportunity.discovered

Проверь:

- кто публикует;
- кто слушает;
- какая payload schema;
- действительно ли subscriber существует;
- что происходит после события;
- есть ли тест.

Отдельно выяви события, которые:

- описаны, но не публикуются;
- публикуются, но никто не слушает;
- имеют разные payload schemas;
- имеют разные имена в разных местах.

---

# 9. ENTRYPOINT FORENSICS

Особенно важно связать архитектуру с реальными действиями пользователя.

Построй карту:

USER ACTION
    ↓
BUTTON / CLI / API / TELEGRAM / MCP
    ↓
HANDLER
    ↓
FUNCTION
    ↓
ENGINE
    ↓
EVENT
    ↓
STORAGE
    ↓
RESULT

Если UI ещё не существует:

UI = NOT IMPLEMENTED

Не создавать фиктивную кнопку.

Например:

"создать Opportunity"

должно быть связано с конкретным:

CLI command
или
API endpoint
или
Telegram handler
или
Python public function.

---

# 10. TAGGING / SEMANTIC ANCHORS

Исследуй возможность введения семантических тегов
в архитектурную документацию.

Цель:

документ должен стать не просто текстом,
а навигационным слоем над repository.

Предложи минимальную систему тегов.

Например:

@concept:
@contract:
@module:
@symbol:
@entrypoint:
@event:
@storage:
@test:
@decision:
@invariant:
@depends:
@implements:
@verified-by:

Но:

НЕ внедряй систему автоматически.

Сначала исследуй существующую документацию и предложи:

1. какие теги действительно нужны;
2. где они дадут пользу;
3. какие можно индексировать;
4. как их можно использовать для Graph Index;
5. как их можно использовать для semantic search;
6. как избежать превращения документации в мусор из тегов.

Отдельно предложи:

DOCUMENT
      ↓
SEMANTIC ANCHOR
      ↓
CODE SYMBOL
      ↓
GRAPH EDGE

модель.

---

# 11. GRAPH MODEL

Исследуй существующий GraphIndex.

Не создавай новый graph engine.

Определи:

какие отношения уже можно представить существующим GraphIndex:

DOCUMENT --implements--> CONTRACT
CONTRACT --implemented_by--> MODULE
MODULE --calls--> MODULE
EVENT --published_by--> MODULE
EVENT --consumed_by--> MODULE
TEST --verifies--> CONTRACT
ENTRYPOINT --invokes--> FUNCTION
CONCEPT --evolves_to--> CONCEPT

Определи минимальный набор новых edge types,
если они действительно необходимы.

---

# 12. CURRENT ARCHITECTURE MAP

Построй фактическую карту:

                    PROJECT
                       │
            ┌──────────┴──────────┐
            ↓                     ↓
        MATERIALS               GOALS
            │                     │
            └──────────┬──────────┘
                       ↓
                 INTELLIGENCE
                       │
            ┌──────────┼──────────┐
            ↓          ↓          ↓
        SIGNALS     STATE    OPPORTUNITIES
                                  │
                                  ↓
                              SCENARIO
                                  │
                                  ↓
                               FACTORY
                                  │
                                  ↓
                                FORGE
                                  │
                                  ↓
                               ARTIFACT
                                  │
                                  ↓
                               MEMORY
                                  │
                                  ↓
                              LEARNING
                                  │
                                  └──────→ INTELLIGENCE

Но каждый элемент схемы должен получить статус:

IMPLEMENTED
PARTIAL
PLANNED
MISSING

---

# 13. CONTENT INTELLIGENCE

Отдельно проверь:

что из Content Intelligence уже существует фактически;

что существует как generic infrastructure;

что существует как content-specific implementation;

что только концептуально описано.

Не смешивай:

GENERIC PLATFORM
CONTENT FACTORY
CONTENT INTELLIGENCE
CONCEPT EVOLUTION

Это разные уровни.

---

# 14. CONCEPT EVOLUTION

Отдельно исследуй статус:

IDEA EXPLORER
C-A
C-B
C-C
Evolution Memory
Concept Genome
Population
Species
Environment
Pressure
Operator
Fitness
Generation
Lineage
Experiment
Strategy
Hypothesis
Evidence

Для каждого:

IMPLEMENTED
PARTIAL
DESIGNED
DOCUMENTED_ONLY
ABSENT

Никакой реализации этих элементов на этом этапе.

Нужно установить фактическую точку старта.

---

# 15. CRITICAL ARCHITECTURAL QUESTION

Ответь на главный вопрос:

Где заканчивается существующий execution layer
и где действительно начинается Intelligence layer?

Нужно определить границу:

INTELLIGENCE
    │
    │ decision / intent
    ↓
SCENARIO
    │
    │ composition
    ↓
FACTORY
    │
    │ production
    ↓
FORGE
    │
    │ execution
    ↓
ARTIFACT

Проверь, действительно ли код соответствует этой модели.

Если нет — показать фактическую модель.

---

# 16. НЕ ПЕРЕДЕЛЫВАТЬ ТО, ЧТО УЖЕ РАБОТАЕТ

Если существующий Phase 5 vertical slice работает:

НЕ переписывать его.

НЕ менять API без необходимости.

НЕ переименовывать сущности только ради красоты.

НЕ создавать вторую Opportunity Engine.

НЕ создавать второй ScenarioRegistry.

НЕ создавать второй Memory layer.

НЕ создавать второй EventBus.

НЕ создавать второй Graph engine.

Любое изменение существующего компонента должно иметь
конкретное доказанное основание.

---

# 17. FIND NEXT SLICE

Только после полного исследования определить:

WHAT IS THE NEXT MINIMAL IMPLEMENTATION SLICE?

Не roadmap на 100 файлов.

Не "построить Content Intelligence".

Не "реализовать Autonomous Intelligence".

Нужен один минимальный vertical slice.

Он должен содержать:

INPUT
→
DECISION
→
EXECUTION
→
ARTIFACT
→
MEMORY
→
FEEDBACK

Количество новых файлов должно быть минимальным.

Для каждого нового файла:

WHY
OWNER
DEPENDENCIES
INTERFACE
TEST
REMOVAL CONDITION

---

# 18. STOP CONDITIONS

Если обнаружено, что текущая архитектура недостаточно ясна:

STOP.

Не реализовывать.

Если обнаружен конфликт контрактов:

STOP.

Сначала создать reconciliation proposal.

Если существует две конкурирующие реализации:

STOP.

Определить canonical implementation.

Если документация противоречит коду:

STOP.

Зафиксировать conflict.

Если отсутствует runtime path:

НЕ считать функцию реализованной.

---

# 19. OUTPUT PACKAGE

После исследования создай:

01_REPOSITORY_BASELINE.md

02_ARCHITECTURE_REALITY_MAP.md

03_CODE_CONTRACT_MAP.md

04_DOCUMENTATION_CODE_TRACEABILITY.md

05_CONTRACT_FORENSICS.md

06_EVENT_TRACEABILITY.md

07_ENTRYPOINT_TRACEABILITY.md

08_GRAPH_RELATIONSHIP_MAP.md

09_DOCUMENT_TAGGING_PROPOSAL.md

10_CONTENT_INTELLIGENCE_STATUS.md

11_CONCEPT_EVOLUTION_STATUS.md

12_ARCHITECTURAL_CONFLICTS.md

13_DEAD_CODE_AND_UNVERIFIED.md

14_NEXT_VERTICAL_SLICE.md

15_EXECUTIVE_SUMMARY.md

---

# 20. MACHINE-READABLE OUTPUT

Создай также:

traceability.json

формат:

{
  "concept": "...",
  "documentation": [***REMOVED***,
  "contracts": [***REMOVED***,
  "modules": [***REMOVED***,
  "symbols": [***REMOVED***,
  "entrypoints": [***REMOVED***,
  "events": [***REMOVED***,
  "storage": [***REMOVED***,
  "tests": [***REMOVED***,
  "status": "CONFIRMED"
***REMOVED***

Также:

architecture_graph.json

где каждая вершина и связь имеют provenance.

---

# 21. EVIDENCE LEDGER

Создай:

EVIDENCE_LEDGER.md

Каждая существенная архитектурная гипотеза должна иметь:

ID
CLAIM
EVIDENCE
PATH
SYMBOL
TEST
STATUS
CONFIDENCE

Никаких утверждений:

"вероятно"
"скорее всего"
"должно быть"

без явного маркирования:

ASSUMPTION
или
HYPOTHESIS.

---

# 22. TEST VERIFICATION

Запусти существующие тесты.

Не ограничивайся targeted tests.

Зафиксируй:

- какие тесты запускались;
- command;
- количество;
- pass;
- fail;
- skipped;
- duration;
- environment.

Если тест не запускается — это тоже evidence.

Не исправляй тесты только ради зелёного результата.

---

# 23. POST-FORENSICS

После завершения анализа повторно проверь:

1. не пропущены ли ключевые модули;
2. все ли архитектурные claims имеют evidence;
3. нет ли DOCUMENTED_ONLY компонентов,
   ошибочно названных IMPLEMENTED;
4. нет ли CODE_ONLY компонентов;
5. нет ли duplicate implementations;
6. совпадают ли contracts и runtime schemas;
7. совпадают ли event names;
8. существует ли реальный execution path;
9. не создаётся ли второй parallel architecture.

Создай:

POST_FORENSICS_CHECK.md

---

# 24. IMPLEMENTATION RULE

На этом этапе разрешена реализация ТОЛЬКО если
она необходима для:

- исправления явного traceability defect;
- добавления отсутствующего теста для уже существующего поведения;
- добавления machine-readable metadata, если это не меняет runtime;
- исправления документационного расхождения.

НЕ реализовывать следующий Intelligence feature.

Главная задача этого этапа:

UNDERSTAND
→
TRACE
→
RECONCILE
→
PLAN

а не:

DESIGN
→
CODE EVERYTHING.

---

# 25. FINAL DECISION

В конце дай однозначный вывод:

A — READY FOR NEXT IMPLEMENTATION SLICE

B — READY AFTER CONTRACT RECONCILIATION

C — ARCHITECTURAL CONFLICT REQUIRES DECISION

D — FORENSICS INCOMPLETE

И если A/B:

укажи ОДИН следующий slice.

Не список из десяти задач.

---

# 26. ОБЯЗАТЕЛЬНЫЙ ARCHIVE

После завершения всей работы создай evaluation archive.

Имя:

PHASE6_CODE_CONTRACT_FORENSICS_<VERSION>.tar.gz

В архив обязательно включить:

- все 15 markdown reports;
- traceability.json;
- architecture_graph.json;
- Evidence Ledger;
- Post-Forensics;
- все созданные/изменённые тесты;
- все созданные/изменённые machine-readable manifests;
- git diff;
- git status snapshot;
- test results;
- README_EVALUATION.md.

README_EVALUATION.md должен содержать:

1. что было исследовано;
2. что реально найдено;
3. что подтверждено кодом;
4. что оказалось только документацией;
5. какие конфликты найдены;
6. какие файлы изменены;
7. какие файлы НЕ изменялись;
8. какие тесты запускались;
9. результаты тестов;
10. какой следующий slice рекомендован;
11. почему именно он;
12. что намеренно НЕ реализовывалось.

ОБЯЗАТЕЛЬНО выведи абсолютный путь к архиву.

---

# 27. НЕ ОСТАНАВЛИВАЙСЯ НА ВОПРОСАХ

Если информации достаточно — принимай решение сам.

Не задавай пользователю вопросы о том,
что можно установить исследованием repository.

Не проси подтвердить очевидные технические решения.

Если обнаружено неоднозначное архитектурное решение,
зафиксируй его как:

DECISION REQUIRED

и продолжай forensic analysis остальных частей.

---

# FINAL RESPONSE

В конце выведи краткий отчёт:

FORENSICS STATUS
REPOSITORY VERSION
FILES ANALYZED
DOCUMENTS ANALYZED
TESTS RUN
CONFIRMED COMPONENTS
PARTIAL COMPONENTS
DOCUMENTED-ONLY COMPONENTS
CODE-ONLY COMPONENTS
ARCHITECTURAL CONFLICTS
TRACEABILITY COVERAGE
NEXT IMPLEMENTATION SLICE
ARCHIVE PATH

После этого укажи:

"IMPLEMENTATION OF NEXT SLICE NOT STARTED."

если следующий slice не был реализован.