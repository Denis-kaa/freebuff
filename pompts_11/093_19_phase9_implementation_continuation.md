Да. Теперь промт должен быть продолжением текущей Phase 9, а не запускать forensics заново. Главная задача — перейти от трёх документов к реальному связующему коду, но не объявить несуществующий Content Production Engine production-ready.

# PHASE 9 — IMPLEMENTATION CONTINUATION
## Factory Execution Boundary → Adapter → End-to-End Vertical Slice

Ты продолжаешь работу над PHASE 9 существующей платформы Freebuff / Workspace OS.

ВАЖНО:

Это НЕ новый проект.
Это НЕ новый этап архитектурного проектирования с нуля.
Repository Forensics и Factory Contract Audit уже выполнены.

В предыдущем прогоне были созданы:

- PHASE9_REPOSITORY_REALITY_MAP.md
- PHASE9_FACTORY_CONTRACT_AUDIT.md
- PHASE9_IMPLEMENTATION_PLAN.md

Твоя задача сейчас — перейти от анализа и проектирования к РЕАЛЬНОЙ РЕАЛИЗАЦИИ.

---

# 1. ГЛАВНАЯ ЦЕЛЬ

Нам необходимо устранить обнаруженный в Phase 9 архитектурный разрыв:

Сейчас существует путь примерно такого типа:

Opportunity
    ↓
Scenario Intelligence
    ↓
Capability
    ↓
ForgeFacade / Forge

Но полноценной реальной Factory Execution Boundary между Capability и Forge ещё нет.

Нам нужно построить этот связующий слой.

Целевая модель:

Opportunity
    ↓
Scenario Intelligence
    ↓
Scenario
    ↓
Capability
    ↓
FactoryRegistry
    ↓
Factory
    ├── validate input
    ├── normalize input
    ├── prepare context
    ├── build execution request
    ├── invoke authorized Forge boundary
    ├── normalize output
    └── return Artifact
             ↓
        ForgeFacade
             ↓
           Forge
             ↓
          Artifact
             ↓
      Validation / Memory / Feedback


---

# 2. КРИТИЧЕСКОЕ ПРАВИЛО

НЕ считай Factory реализованной только потому, что существует:

- FactoryRegistry;
- Factory passport;
- YAML;
- capability declaration;
- documentation.

Factory существует как production implementation только тогда, когда существует реальный исполняемый код, который:

1. получает вход;
2. валидирует его;
3. подготавливает execution request;
4. вызывает разрешённый execution boundary;
5. получает результат;
6. нормализует результат;
7. возвращает его вызывающему слою;
8. имеет тесты, подтверждающие поведение.

Документация ≠ implementation.

Registry ≠ Factory.

Passport ≠ Factory.

Capability ≠ Factory.

Forge ≠ Factory.

---

# 3. НЕ ПОВТОРЯЙ FORENSICS БЕЗ НЕОБХОДИМОСТИ

У тебя уже есть:

PHASE9_REPOSITORY_REALITY_MAP.md
PHASE9_FACTORY_CONTRACT_AUDIT.md
PHASE9_IMPLEMENTATION_PLAN.md

Сначала ПРОЧИТАЙ ИХ ПОЛНОСТЬЮ.

После этого:

- проверь только те утверждения, которые непосредственно влияют на реализацию;
- если обнаружишь противоречие с repository — repository имеет приоритет;
- зафиксируй найденное расхождение;
- не начинай новый многосотстрочный forensic report.

Мы уже прошли этап исследования.

Сейчас:

FORENSICS
    ↓
CONTRACT
    ↓
IMPLEMENTATION


---

# 4. ПЕРЕД ИЗМЕНЕНИЕМ КОДА

Сделай короткую implementation preflight-проверку.

Создай:

PHASE9_IMPLEMENTATION_PREFLIGHT.md

В ней укажи:

1. Какие утверждения предыдущего Implementation Plan подтверждены кодом.
2. Какие требуют корректировки.
3. Какие файлы реально будут изменены.
4. Какие новые файлы будут созданы.
5. Какой существующий execution boundary будет использоваться.
6. Как будет обеспечена domain neutrality.
7. Что НЕ будет реализовано из-за отсутствия production capability.

После этого переходи к реализации.

---

# 5. FACTORY CONTRACT

Реализуй Factory как исполняемую границу домена.

Минимальная ответственность Factory:

```text
Factory.execute(request)

или эквивалентный API, соответствующий существующему repository contract.

Factory должен:

INPUT ↓ VALIDATE ↓ NORMALIZE ↓ PREPARE ↓ EXECUTE ↓ NORMALIZE OUTPUT ↓ RETURN

Не копируй этот API вслепую.

Сначала проверь существующий стиль repository:

- interfaces;
- protocols;
- dataclasses;
- registries;
- adapters;
- service classes;
- execution requests.

Используй существующую архитектурную конвенцию.

НЕ создавай второй несовместимый паттерн.

---

# 6. FACTORY НЕ ДОЛЖЕН СТАТЬ FORGE

Factory НЕ должен содержать:

- собственный ForgePipeline;
- дублирование ForgeFacade;
- собственную систему стадий FORGE/CHECK/BUILD/TEST/DEPLOY;
- собственный scheduler;
- собственный EventBus;
- собственную память;
- собственный агентный runtime.

Factory только подготавливает и маршрутизирует domain-specific execution.

Фактическое производство остаётся за существующим Forge execution boundary.

---

# 7. FORGE BOUNDARY

Используй существующий санкционированный путь вызова Forge.

Если repository определяет:

ForgeFacade

как единственную разрешённую границу:

Factory
    ↓
ForgeFacade
    ↓
Forge

НЕЛЬЗЯ:

Factory
    ↓
ForgePipeline напрямую

если это нарушает существующее правило архитектуры.

НЕЛЬЗЯ обходить существующие governance / validation механизмы.

---

# 8. CONTENT FACTORY

Content Factory является первым конкретным Factory Domain.

НО:

Content Factory НЕ означает:

"построить весь Content Intelligence".

НЕ создавать сейчас:

- новый Content Intelligence Engine;
- новую систему поиска идей;
- новую память;
- новый Knowledge Engine;
- новый Opportunity Engine;
- новый Scenario Engine;
- новую систему агентов;
- новую оркестрацию.

Используй существующие:

Opportunity Engine
ScenarioIntelligence
ScenarioRegistry
FactoryRegistry
ForgeFacade
ForgePipeline
Memory
Knowledge
EventBus

где они уже предусмотрены.

---

# 9. ОСОБОЕ ПРАВИЛО ПРО CONTENT CAPABILITIES

Предыдущий аудит обнаружил важное состояние:

Некоторые Content capabilities существуют в документации / registry / design,
но это НЕ означает наличие production implementation.

Например, если:

article_generation
book_generation
report_generation

объявлены как capability,

это ещё не означает, что соответствующий production Forge существует.

Поэтому:

НЕ ставь:

status: production

только потому, что capability зарегистрирована.

НЕ создавай фиктивный production implementation.

НЕ подменяй отсутствие реального production execution красивым YAML.

---

# 10. ЕСЛИ REAL CONTENT FORGE СУЩЕСТВУЕТ

Если repository действительно содержит production-ready execution path для конкретного Content capability:

используй его.

Тогда реализуй:

Opportunity
    ↓
ScenarioIntelligence
    ↓
Capability
    ↓
ContentFactory
    ↓
ForgeFacade
    ↓
Forge
    ↓
Artifact

И докажи это реальным execution test.

---

# 11. ЕСЛИ REAL CONTENT FORGE НЕ СУЩЕСТВУЕТ

НЕ изобретай его.

В этом случае Phase 9 должна реализовать:

1. Universal Factory execution boundary.
2. Content Factory adapter.
3. Capability resolution.
4. Input/output contracts.
5. Integration с существующим execution boundary.
6. Test Factory / controlled test implementation для доказательства универсальности.

А Content Factory production status должен остаться:

NOT PRODUCTION READY

с точной причиной:

MISSING PRODUCTION EXECUTION CAPABILITY.

Это не failure.

Это корректный архитектурный результат.

---

# 12. TEST FACTORY

Для проверки универсальности, если repository позволяет, создай минимальный Test Factory.

Например:

TestFactory

Он нужен НЕ для production.

Он нужен для доказательства:

Capability
    ↓
FactoryRegistry
    ↓
Factory
    ↓
Execution Boundary

работает независимо от Content Domain.

Test Factory может возвращать deterministic artifact.

Например:

input
→ normalized request
→ deterministic result

Это позволит проверить контракт без создания искусственного Content Forge.

Если существующая архитектура не допускает Test Factory — не ломай архитектуру.

Зафиксируй ограничение.

---

# 13. DOMAIN NEUTRALITY — ОБЯЗАТЕЛЬНО

Проверь код ScenarioIntelligence.

В нём НЕ должно появиться:

```python
if capability == "article_generation":

или:

if factory == "content":

или:

ContentFactory(...)

ScenarioIntelligence должен работать через абстрактный:

Capability FactoryRegistry Factory Contract

Пример:

ScenarioIntelligence ↓ capability = "X" ↓ FactoryRegistry.resolve("X") ↓ Factory ↓ execute()

То, какой это домен, должно быть свойством Factory/Capability registration, а не Intelligence Core.


---

14. НЕ СОЗДАВАЙ ЛИШНИЕ СЛОИ

Перед созданием нового класса / модуля ответь:

1. Почему существующий класс не может выполнить эту ответственность?


2. Где находится аналогичный паттерн в repository?


3. Почему новый объект необходим?


4. Как он связан с существующим контрактом?



Если новый слой не нужен — не создавай его.

Цель:

MINIMAL ADDITIVE IMPLEMENTATION.


---

15. IMPLEMENTATION STEPS

Работай последовательно.

STEP 1

Подтвердить preflight.

STEP 2

Реализовать / завершить Factory execution contract.

STEP 3

Подключить Factory к FactoryRegistry.

STEP 4

Реализовать Factory input normalization.

STEP 5

Реализовать execution request.

STEP 6

Подключить разрешённый Forge boundary.

STEP 7

Реализовать output normalization.

STEP 8

Подключить validation / artifact handling существующей системы.

STEP 9

Подключить Content Factory adapter.

STEP 10

Добавить Test Factory, если необходимо для domain-neutrality.

STEP 11

Добавить unit tests.

STEP 12

Добавить integration tests.

STEP 13

Запустить весь relevant regression suite.

После каждого шага:

IMPLEMENT → TEST → VERIFY → CONTINUE


---

16. TRACEABILITY

Каждый новый execution path должен быть связан:

Capability ↓ Factory ↓ FactoryRegistry ↓ Execution Request ↓ ForgeFacade ↓ Forge ↓ Artifact

Создай или обнови traceability так, чтобы другой разработчик мог по capability найти:

Factory;

factory registration;

execution method;

Forge boundary;

tests.


Не допускай:

"документ говорит, что существует, но найти код невозможно."


---

17. ТЕСТЫ

Минимально нужны:

Factory unit tests

valid request;

invalid request;

missing input;

normalization;

unsupported capability;

unknown factory;

malformed output;

execution failure.


Registry tests

register;

resolve;

unknown capability;

duplicate registration;

invalid passport/metadata.


Integration

Capability
    ↓
FactoryRegistry
    ↓
Factory
    ↓
ForgeFacade

Full vertical slice

Если реальный Content Forge существует:

Opportunity
→ ScenarioIntelligence
→ Scenario
→ Capability
→ ContentFactory
→ ForgeFacade
→ Forge
→ Artifact

Если не существует:

Capability
→ ContentFactory
→ controlled execution/test boundary
→ Artifact

с явным статусом:

NOT PRODUCTION.


---

18. REGRESSION

После реализации обязательно запусти:

Phase 8 tests;

Factory tests;

Scenario Intelligence tests;

Opportunity tests;

Forge tests;

integration tests.


Если какой-либо существующий тест сломан:

НЕ маскируй failure.

Определи:

REGRESSION или EXPECTED CONTRACT CHANGE.

Если contract change действительно необходим:

зафиксируй ADR / architecture decision.


---

19. ДОКУМЕНТАЦИЯ

После реализации обнови только документацию, которая реально изменилась.

Минимум:

PHASE9_IMPLEMENTATION_REPORT.md

Он должен содержать:

что было;

что обнаружено;

что изменено;

какие файлы;

почему;

execution path;

тесты;

ограничения.


Обнови:

PHASE9_TRACEABILITY.md

и:

PHASE9_GAP_MAP.md

если их нет — создай.


---

20. EVIDENCE LEDGER

Создай:

PHASE9_EVIDENCE_LEDGER.md

Для каждого ключевого утверждения:

ID CLAIM PATH SYMBOL OBSERVED BEHAVIOR TEST STATUS

Например:

FACT-001 "FactoryRegistry resolves capability" core_02/... FactoryRegistry.resolve(...) test_... CONFIRMED

Не использовать:

"по архитектуре должно быть"

как evidence.


---

21. DEFERRED

Создай:

PHASE9_DEFERRED.md

Отдельно сохрани:

отсутствующие Content Forges;

будущие Code Factory;

Research Factory;

Image Factory;

Video Factory;

Audio Factory;

Book Factory;

Concept Evolution;

Continuous Intelligence;

Workspace integration.


Ничего из этого не удалять.

Статус:

DEFERRED

а не:

DROP.


---

22. АРХИТЕКТУРНЫЙ РЕЗУЛЬТАТ

В конце должно быть понятно, какой из двух вариантов фактически достигнут.

ВАРИАНТ A — FULL VERTICAL SLICE

Opportunity
    ↓
ScenarioIntelligence
    ↓
Scenario
    ↓
Capability
    ↓
FactoryRegistry
    ↓
ContentFactory
    ↓
ForgeFacade
    ↓
Forge
    ↓
Artifact

STATUS:

PHASE 9 COMPLETE

или:

PASS WITH WARNINGS

если остаются ограничения.


---

ВАРИАНТ B — UNIVERSAL FACTORY BOUNDARY COMPLETE

Если production Content Forge отсутствует:

ScenarioIntelligence
        ↓
Capability
        ↓
FactoryRegistry
        ↓
Factory
        ↓
Execution Boundary

доказан через Test Factory.

Content Factory:

REGISTERED + CONTRACTED + ADAPTER IMPLEMENTED

но:

NOT PRODUCTION READY

до появления реального Content execution capability.

Это также допустимый результат.


---

23. НЕ ПОДГОНЯТЬ РЕАЛЬНОСТЬ ПОД ROADMAP

Если repository показывает, что наш первоначальный план ошибочен:

НЕ заставляй код соответствовать плану.

Используй:

Repository Reality ↓ Architectural Decision ↓ Implementation

а не:

Plan ↓ Force repository to match plan.

Если обнаружено противоречие:

STOP → RECORD → DECIDE → CONTINUE.


---

24. ФИНАЛЬНЫЙ EVALUATION PACKAGE

После завершения реализации создай полноценный пакет:

01_PHASE9_REPOSITORY_REALITY_MAP.md 02_PHASE9_FACTORY_CONTRACT_AUDIT.md 03_PHASE9_IMPLEMENTATION_PREFLIGHT.md 04_PHASE9_IMPLEMENTATION_PLAN.md 05_PHASE9_IMPLEMENTATION_REPORT.md 06_PHASE9_TRACEABILITY.md 07_PHASE9_EVIDENCE_LEDGER.md 08_PHASE9_TEST_REPORT.md 09_PHASE9_ARCHITECTURE_DECISIONS.md 10_PHASE9_GAP_MAP.md 11_PHASE9_DEFERRED.md 12_PHASE9_FINAL_EVALUATION.md 13_PHASE9_HANDOFF.md

Используй существующие документы из предыдущего прогона, не дублируй их бессмысленно.

Если файл уже существует — обнови его.


---

25. АРХИВ

ОБЯЗАТЕЛЬНО создай Evaluation Archive.

НЕ архивируй весь repository.

В архив должны войти:

CODE

все изменённые файлы;

TESTS

все новые / изменённые тесты;

DOCUMENTATION

релевантная обновлённая документация;

EVALUATION

весь Evaluation Package;

MANIFEST

список всех файлов;

CHECKSUMS

SHA-256 для файлов архива / manifest.

Название:

PHASE9_FACTORY_IMPLEMENTATION_<VERSION>.tar.gz

И:

PHASE9_FACTORY_IMPLEMENTATION_MANIFEST.sha256

Архив должен быть самодостаточным для внешнего архитектурного review.


---

26. НЕ ПОДМЕНЯТЬ АРХИВ ОТЧЁТОМ

Предыдущий архив содержал только:

Repository Reality Map;

Factory Contract Audit;

Implementation Plan.


ЭТО НЕ ЯВЛЯЕТСЯ ФИНАЛЬНЫМ РЕЗУЛЬТАТОМ PHASE 9.

Теперь нужен:

DOCUMENTATION + CODE + TESTS + EVIDENCE + EVALUATION + ARCHIVE.


---

27. ФИНАЛЬНЫЙ HANDOFF

В конце выведи:

PHASE 9 STATUS: PASS / PASS WITH WARNINGS / BLOCKED

FACTORY CONTRACT: IMPLEMENTED / PARTIAL

FACTORY EXECUTION BOUNDARY: IMPLEMENTED / PARTIAL

CONTENT FACTORY: PRODUCTION / NOT PRODUCTION READY / BLOCKED

DOMAIN NEUTRALITY: CONFIRMED / PARTIAL / FAILED

REGRESSION: PASS / FAIL

TESTS: <количество и результат>

FILES CHANGED: <список>

FILES CREATED: <список>

DEFERRED: <список>

NEXT PHASE: <конкретный следующий шаг>

ARCHIVE: <точный путь>

SHA256: <checksum>


---

ГЛАВНЫЙ ПРИНЦИП

Мы сейчас не пытаемся доказать, что "Content Factory уже существует".

Мы строим реальную архитектурную границу:

INTELLIGENCE
                     ↓
                CAPABILITY
                     ↓
              FACTORY REGISTRY
                     ↓
                   FACTORY
                     ↓
             EXECUTION BOUNDARY
                     ↓
                   FORGE
                     ↓
                 ARTIFACT

Content Factory — первый клиент этой границы.

В будущем:

INTELLIGENCE
                     ↓
                CAPABILITY
                     ↓
              FACTORY REGISTRY
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
 CONTENT            CODE           RESEARCH
 FACTORY           FACTORY          FACTORY
    ↓                ↓                ↓
  FORGE             FORGE            FORGE

НЕ изменяя Intelligence Core.

Именно это является главным архитектурным доказательством Phase 9.