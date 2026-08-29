# PHASE 9 — UNIVERSAL FACTORY VERTICAL SLICE
## Repository Forensics → Contract Verification → Domain Factory → Integration → Validation

Ты — Senior AI Systems Architect + Repository Forensics Engineer + Senior Python Developer.

Твоя задача — продолжить развитие существующей платформы Freebuff / Workspace OS после завершения Phase 8.

ВАЖНО:

Мы НЕ строим новую платформу.
Мы НЕ переписываем существующее ядро.
Мы НЕ создаём отдельную Content Intelligence Platform.

Мы продолжаем существующую архитектуру и реализуем первый конкретный Factory Domain, одновременно проверяя, что существующий Intelligence Core действительно является универсальным.

---

# 0. КОНТЕКСТ АРХИТЕКТУРЫ

В системе уже существует универсальная цепочка:

PROJECT
    ↓
OPPORTUNITY
    ↓
SCENARIO INTELLIGENCE
    ↓
SCENARIO
    ↓
CAPABILITY
    ↓
FACTORY
    ↓
FORGE
    ↓
ARTIFACT
    ↓
MEMORY / FEEDBACK
    ↓
INTELLIGENCE

Ключевое архитектурное разделение:

WHAT?
→ Opportunity

HOW?
→ Scenario

WITH WHAT CAPABILITY?
→ Factory

HOW IS IT EXECUTED?
→ Forge

Intelligence принимает решения.
Factory предоставляет domain capability.
Forge выполняет производство.

---

# 1. КРИТИЧЕСКОЕ АРХИТЕКТУРНОЕ ПРАВИЛО

Content Factory — НЕ является центром платформы.

Это только ПЕРВЫЙ конкретный Factory Domain.

В будущем система должна поддерживать, например:

ContentFactory
CodeFactory
ResearchFactory
ImageFactory
VideoFactory
AudioFactory
BookFactory
DataFactory
и другие.

Поэтому:

SCENARIO INTELLIGENCE
НЕ ДОЛЖЕН
знать о ContentFactory напрямую.

Scenario Intelligence должен работать с:

Capability
Factory Registry
Factory Contract

а не с конкретным доменом.

Нельзя создавать:

if capability == "article":
    ...
if capability == "code":
    ...
if capability == "image":
    ...

если для этого нет уже существующего архитектурного контракта.

---

# 2. ГЛАВНОЕ ПРАВИЛО РАБОТЫ

REPOSITORY = SOURCE OF TRUTH.

Документация важна, но она НЕ является доказательством существования реализации.

При конфликте:

CODE
>
TESTS
>
CONFIG / REGISTRY
>
DOCUMENTATION
>
ASSUMPTION

Не принимай архитектурные решения только потому, что они описаны в документации.

Каждое существенное утверждение должно иметь evidence:

path
symbol / function / class
поведение
при необходимости тест или execution evidence.

---

# 3. PHASE 9 НЕ НАЧИНАЕТСЯ С КОДА

ПЕРВЫЙ ЭТАП — ПОЛНЫЙ REPOSITORY FORENSICS.

До изменения любого файла:

1. Изучи структуру repository.
2. Изучи AGENTS.md / BUFFY.md и другие governing documents.
3. Найди результаты Phase 8.
4. Найди:
   - ScenarioIntelligence
   - ScenarioRegistry
   - FactoryRegistry
   - ForgeFacade
   - ForgePipeline
   - ForgeRegistry
   - Opportunity
   - MemoryStore
   - KnowledgeEngine
   - EventBus
   - существующие scenario manifests
   - существующие factory/capability contracts
5. Прочитай релевантный код полностью, а не только определения.
6. Изучи связанные тесты.
7. Изучи configuration / YAML manifests.
8. Проследи реальный execution path.
9. Найди существующие integration points.
10. Определи, что реально реализовано, а что существует только в документации.

НЕ ПЕРЕПИСЫВАЙ КОД НА ОСНОВАНИИ ДОКУМЕНТА,
НЕ ПРОВЕРИВ ЕГО ПРОТИВ REPOSITORY.

---

# 4. ОБЯЗАТЕЛЬНЫЙ FORENSICS OUTPUT

До реализации создай:

PHASE9_REPOSITORY_REALITY_MAP.md

Он должен содержать:

A. Repository structure

B. Existing Intelligence components

C. Existing Scenario components

D. Existing Factory components

E. Existing Forge components

F. Existing capability resolution

G. Existing registry mechanisms

H. Existing Content-related artifacts

I. Existing tests

J. Existing execution paths

K. Existing integration contracts

L. Gaps

M. Architectural risks

N. Exact files that will be modified

O. Exact files that must NOT be modified

---

# 5. ОСОБЕННО ПРОВЕРЬ FACTORY

В Phase 8 FactoryRegistry / Factory Contract уже рассматривался как архитектурный элемент.

Твоя задача:

НЕ предполагать, что он реализован.

Проверить:

- существует ли FactoryRegistry;
- какие у него реальные API;
- какие capability он умеет разрешать;
- существует ли factory passport;
- как capability связывается с Factory;
- как Factory связывается со Scenario;
- как Factory передаёт выполнение Forge;
- какие части являются production-ready;
- какие являются только дизайном.

Раздели результаты:

CONFIRMED
PARTIAL
DESIGN-ONLY
MISSING

---

# 6. ПОСЛЕ FORENSICS — CONTRACT VERIFICATION

До реализации сформируй:

PHASE9_FACTORY_CONTRACT_AUDIT.md

Проверь существующий контракт:

Opportunity
    ↓
ScenarioIntelligence
    ↓
Scenario
    ↓
Capability
    ↓
Factory
    ↓
Forge

Ответь evidence-based:

1. Где именно возникает capability?
2. Кто её выбирает?
3. Кто её разрешает?
4. Кто находит Factory?
5. Как Factory получает вход?
6. Как Factory формирует execution request?
7. Кто вызывает Forge?
8. Кто валидирует результат?
9. Где сохраняется Artifact?
10. Как результат возвращается в Intelligence?
11. Где находится feedback?
12. Можно ли заменить ContentFactory другим Factory без изменения Intelligence Core?

Если контракт уже существует — используй его.

Если контракт неполный — ДОБАВЬ только минимально необходимое расширение.

НЕ СОЗДАВАЙ ВТОРОЙ ПАРАЛЛЕЛЬНЫЙ КОНТРАКТ.

---

# 7. DOMAIN-NEUTRALITY TEST

Это один из главных критериев Phase 9.

Нужно доказать:

Scenario Intelligence
НЕ зависит от конкретного Factory Domain.

Минимальная модель:

Opportunity
    ↓
ScenarioIntelligence
    ↓
CapabilityToken
    ↓
FactoryRegistry
    ↓
FactoryAdapter
    ↓
ForgeFacade
    ↓
Artifact

Content — только один adapter/domain.

---

# 8. CONTENT FACTORY — ПЕРВЫЙ DOMAIN

После проверки архитектуры реализуй первый конкретный Factory:

CONTENT FACTORY

Но только в пределах уже существующих возможностей repository.

НЕ изобретай огромную Content Intelligence систему.

НЕ создавай:

- новый Knowledge Engine;
- новый Memory Engine;
- новый Opportunity Engine;
- новый Scenario Engine;
- новую систему агентов;
- новую оркестрацию;
- новую EventBus;
- новую Forge систему.

Используй существующие компоненты.

---

# 9. CONTENT FACTORY ЗАДАЧА

Content Factory должен доказать один реальный vertical slice.

Например:

OPPORTUNITY
    ↓
SCENARIO
    ↓
content capability
    ↓
ContentFactory
    ↓
existing Forge
    ↓
ARTIFACT
    ↓
VALIDATION
    ↓
MEMORY / FEEDBACK

Конкретный capability выбери на основании repository evidence.

НЕ выбирай capability потому, что он кажется красивым.

Если в repository уже существует:

article_generation
book_generation
или другой production-ready content capability,

используй существующий.

Если capability только документирован, явно зафиксируй это и не выдавай его за production-ready.

---

# 10. НЕ ДЕЛАТЬ ПОДМЕНУ FACTORY FORGE

Factory НЕ должен сам становиться Forge.

Factory отвечает за:

- domain capability;
- input normalization;
- domain-specific preparation;
- формирование execution request;
- выбор/подготовку нужного Forge capability;
- output normalization;
- domain metadata.

Forge отвечает за фактическое производство.

Не дублируй ForgePipeline.

Не вызывай внутренние Forge-механизмы напрямую, если существующий контракт требует ForgeFacade.

---

# 11. ОДНА OPPORTUNITY → НЕСКОЛЬКО SCENARIOS

Сохрани уже существующий принцип Phase 8:

одна Opportunity может иметь несколько ScenarioCandidate.

Например:

Opportunity:
"Создать материал на основе накопленных исследований"

может иметь:

Scenario A
Scenario B
Scenario C

Scenario Intelligence:

DISCOVER
→ EVALUATE
→ RANK
→ SELECT

Factory НЕ выбирает Scenario.

Factory получает уже выбранный capability / execution intent.

---

# 12. НЕ ПУТАТЬ CONCEPT EVOLUTION И FACTORY

В будущем будет:

IDEA EXPLORER
    ↓
CONCEPT EVOLUTION SYSTEM
    ├── C-A
    ├── C-B
    ├── C-C
    └── Evolution Memory
    ↓
STABLE CONCEPT
    ↓
PROMPT ARCHITECT

Это другой слой.

Phase 9 НЕ должна реализовывать Concept Evolution.

Не смешивай:

Concept
Opportunity
Scenario
Factory
Forge

Они имеют разные ответственности.

---

# 13. IMPLEMENTATION STRATEGY

После forensics и contract audit сформируй:

PHASE9_IMPLEMENTATION_PLAN.md

План должен быть:

- минимальным;
- последовательным;
- проверяемым;
- основанным на реальном коде;
- с точным списком файлов;
- с критериями успеха каждого шага.

Для каждого шага:

STEP ID
PURPOSE
FILES
CHANGES
DEPENDENCIES
TEST
ACCEPTANCE CRITERIA
ROLLBACK

---

# 14. IMPLEMENTATION

Только после завершения:

FORENSICS
+
CONTRACT AUDIT
+
IMPLEMENTATION PLAN

начинай кодирование.

Работай пошагово.

После каждого логического шага:

1. изменяй код;
2. запускай соответствующие тесты;
3. проверяй regression;
4. фиксируй evidence;
5. только после успеха переходи дальше.

Не делай большой batch изменений без промежуточной проверки.

---

# 15. REGISTER-FIRST

Если в repository существует MissingRegistry / register-first механизм:

используй его.

Для каждого нового capability / module / contract:

REGISTER
→ PROMPT / PLAN
→ IMPLEMENT
→ TEST
→ MARK IMPLEMENTED

Не создавай скрытые незарегистрированные архитектурные элементы.

---

# 16. TESTING

Обязательно проверить:

### Unit

- Factory resolution
- capability resolution
- input normalization
- output normalization
- invalid capability
- missing Factory
- invalid Scenario
- invalid input

### Integration

Opportunity
→ ScenarioIntelligence
→ Scenario
→ Capability
→ Factory
→ Forge
→ Artifact

### Regression

Все существующие Phase 8 тесты должны продолжать проходить.

### Domain isolation

Проверь, что ScenarioIntelligence не содержит Content-specific logic.

---

# 17. ОБЯЗАТЕЛЬНЫЙ NEGATIVE TEST

Нужно доказать не только:

"Content Factory работает",

но и:

"Scenario Intelligence не знает, что это Content Factory".

Создай тест/проверку, демонстрирующую domain isolation.

Если возможно без чрезмерного scope:

создай mock / minimal second Factory capability только для теста contract resolution.

Например:

TEST_FACTORY

Он не обязан реально производить артефакт.

Его задача:

доказать:

Capability B
→ FactoryRegistry
→ Factory B

без изменения ScenarioIntelligence.

Если такой тест противоречит существующей архитектуре — НЕ изобретай новый механизм. Зафиксируй ограничение.

---

# 18. DOCUMENTATION ↔ CODE TRACEABILITY

Очень важное требование.

После реализации документация не должна существовать отдельно от кода.

Для каждого ключевого архитектурного элемента укажи:

CONCEPT
→ DOCUMENT
→ FILE
→ SYMBOL
→ TEST
→ EXECUTION PATH

Например:

Factory Contract
→ PHASE9_FACTORY_CONTRACT...
→ core_02/...
→ FactoryRegistry.resolve(...)
→ tests/...
→ actual execution path

Если документация говорит, что что-то существует, но код это не подтверждает:

DOCUMENTATION DRIFT

Если код содержит архитектурный элемент, который нигде не описан:

UNDOCUMENTED IMPLEMENTATION

Оба случая должны быть отмечены.

---

# 19. ТЕГИ / TRACEABILITY

Если в repository уже есть механизм тегирования / metadata — используй его.

Если такого механизма нет, НЕ вводи массовую систему тегов только ради этой фазы.

Но исследуй возможность архитектурно связать:

Document
Paragraph / Section
Concept
Opportunity
Scenario
Capability
Factory
Forge
Artifact
Evidence

Если tags действительно дадут существенную пользу для:

- retrieval;
- semantic search;
- graph construction;
- provenance;
- traceability;

сделай отдельную рекомендацию:

PHASE9_TAGGING_PROPOSAL.md

Но не превращай это в обязательную реализацию Phase 9 без evidence.

---

# 20. НЕЛЬЗЯ РАСШИРЯТЬ SCOPE

НЕ реализовывать сейчас:

- Autonomous Project Intelligence целиком;
- Continuous Intelligence;
- Cron-driven Opportunity Engine;
- Whim UI;
- Workspace widgets;
- Concept Evolution System;
- C-A/C-B/C-C;
- Content Intelligence Monster;
- все будущие Factory;
- новую архитектуру памяти;
- новую графовую БД;
- новую event system.

Phase 9 должна доказать:

UNIVERSAL INTELLIGENCE CORE
+
ONE REAL FACTORY DOMAIN

---

# 21. DEFERRED ≠ DROP

Если во время работы обнаружена архитектурно полезная идея, которая не входит в Phase 9:

НЕ УДАЛЯЙ ЕЁ.

Запиши:

DEFERRED

с причиной:

- почему сейчас не реализуется;
- что должно произойти перед её реализацией;
- к какой будущей фазе относится;
- какие существующие компоненты уже могут её поддержать.

Это особенно важно для будущих Factory и Intelligence возможностей.

---

# 22. ACCEPTANCE CRITERIA

Phase 9 считается успешной только если:

[ ***REMOVED*** Repository был исследован ДО изменения кода.

[ ***REMOVED*** Forensics подтверждает реальное состояние Phase 8.

[ ***REMOVED*** Factory Contract сверён с реальным кодом.

[ ***REMOVED*** Нет второго параллельного Factory Contract.

[ ***REMOVED*** Content Factory подключён через существующий универсальный механизм.

[ ***REMOVED*** ScenarioIntelligence не содержит Content-specific branching.

[ ***REMOVED*** Capability → Factory resolution работает.

[ ***REMOVED*** Factory → Forge интеграция работает.

[ ***REMOVED*** Один реальный Content vertical slice проходит end-to-end.

[ ***REMOVED*** Artifact создаётся и валидируется.

[ ***REMOVED*** Результат возвращается в существующий state/memory механизм.

[ ***REMOVED*** Phase 8 regression tests проходят.

[ ***REMOVED*** Domain isolation подтверждён тестом или execution evidence.

[ ***REMOVED*** Documentation ↔ Code traceability обновлена.

[ ***REMOVED*** Все новые архитектурные элементы зарегистрированы.

[ ***REMOVED*** Нет ненужного переписывания существующего ядра.

[ ***REMOVED*** Все deferred идеи сохранены.

---

# 23. ФИНАЛЬНЫЙ EVALUATION PACKAGE

Это ОБЯЗАТЕЛЬНАЯ часть задачи.

После завершения работы создай отдельный evaluation package.

Минимальный состав:

01_PHASE9_REPOSITORY_REALITY_MAP.md
02_PHASE9_FACTORY_CONTRACT_AUDIT.md
03_PHASE9_IMPLEMENTATION_PLAN.md
04_PHASE9_IMPLEMENTATION_REPORT.md
05_PHASE9_TRACEABILITY.md
06_PHASE9_EVIDENCE_LEDGER.md
07_PHASE9_TEST_REPORT.md
08_PHASE9_ARCHITECTURE_DECISIONS.md
09_PHASE9_GAP_MAP.md
10_PHASE9_DEFERRED.md
11_PHASE9_FINAL_EVALUATION.md
12_PHASE9_HANDOFF.md

Если существующая структура Evaluation Package использует другие канонические имена — СНАЧАЛА используй её структуру и не создавай конфликтующую.

---

# 24. EVIDENCE LEDGER

Каждое существенное утверждение должно иметь:

ID
CLAIM
SOURCE TYPE
PATH
SYMBOL / SECTION
OBSERVED BEHAVIOR
STATUS
CONFIDENCE

Статусы:

CONFIRMED
PARTIAL
DESIGN-ONLY
INFERRED
UNKNOWN

Не превращай предположение в факт.

---

# 25. FINAL REPORT

В конце дай краткий executive summary:

1. Что было найдено.
2. Что уже существовало.
3. Что отсутствовало.
4. Что изменено.
5. Какие контракты подтверждены.
6. Как Content Factory подключается к универсальному ядру.
7. Как доказана domain neutrality.
8. Какие тесты прошли.
9. Какие проблемы остались.
10. Что является следующим шагом Phase 10.

---

# 26. АРХИВ — ОБЯЗАТЕЛЬНО

В конце ОБЯЗАТЕЛЬНО собери архив для внешней оценки.

Архив должен содержать:

A. Все изменённые файлы кода.

B. Новые тесты.

C. Обновлённую документацию, относящуюся к Phase 9.

D. Полный Evaluation Package.

E. Evidence Ledger.

F. Test results.

G. Manifest файлов.

H. SHA-256 checksums.

ВАЖНО:

Не архивируй весь repository.

Нам нужен Evaluation / Handoff Archive именно этой фазы.

Архив должен позволять другому архитектору:

1. понять, что было сделано;
2. проверить изменения;
3. увидеть evidence;
4. воспроизвести тесты;
5. оценить архитектурные решения;
6. сравнить код с документацией.

Название:

PHASE9_FACTORY_VERTICAL_SLICE_<VERSION>.tar.gz

Дополнительно создай:

PHASE9_ARCHIVE_MANIFEST.sha256

---

# 27. FINAL HANDOFF

Финальный ответ должен содержать:

PHASE 9 STATUS:
PASS / PASS WITH WARNINGS / BLOCKED

IMPLEMENTED:
...

TESTS:
...

REGRESSIONS:
...

ARCHITECTURAL FINDINGS:
...

DEFERRED:
...

NEXT PHASE:
...

ARCHIVE:
<точный путь к архиву>

SHA256:
<checksum>

НЕ ПИШИ "готово", если acceptance criteria не выполнены.

Если что-то не удалось реализовать — честно укажи BLOCKED / PARTIAL и причину.

---

# ГЛАВНАЯ ФОРМУЛА PHASE 9

НЕ:

"Построить Content Intelligence."

А:

"Доказать, что существующий Intelligence Core способен подключать различные Factory Domains через универсальный контракт, реализовав Content Factory как первый реальный vertical slice."

Итоговая архитектура должна оставаться:

                PROJECT INTELLIGENCE
                         │
                    OPPORTUNITY
                         │
                  SCENARIO INTELLIGENCE
                         │
                     SCENARIO
                         │
                    CAPABILITY
                         │
                  FACTORY REGISTRY
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
      CONTENT          CODE          RESEARCH
      FACTORY         FACTORY         FACTORY
          │              │              │
          ↓              ↓              ↓
        FORGE          FORGE          FORGE
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                      ARTIFACT
                         ↓
                  MEMORY / FEEDBACK
                         ↓
                    INTELLIGENCE

Content — первый домен.

НЕ конечная архитектура.

Factory — расширяемая производственная граница.

Intelligence — универсальный слой принятия решений.

Forge — существующий исполнительный механизм.

Repository — источник истины.

Evidence — обязательное основание решений.

Implementation — только после forensics.

Evaluation archive — обязательная часть результата.