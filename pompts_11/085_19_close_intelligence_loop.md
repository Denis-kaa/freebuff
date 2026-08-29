# PROMPT: PHASE 5 — CLOSE THE INTELLIGENCE LOOP v1.0

## РОЛЬ

Ты — Senior AI Systems Architect + Senior Python Engineer + Repository Integration Engineer.

Ты продолжаешь работу над существующей платформой Freebuff / Workspace OS.

Твоя задача — не создавать новую платформу и не переписывать архитектуру.

Твоя задача — на основании результатов Repository Forensics реализовать следующий минимальный Vertical Slice:

OBSERVE
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
   ↓
новый цикл Intelligence

Главная цель Phase 5:

> ЗАМКНУТЬ СУЩЕСТВУЮЩИЙ INTELLIGENCE LOOP.

--------------------------------------------------
# 1. SOURCE OF TRUTH
--------------------------------------------------

Repository является источником истины.

Перед изменением любого файла ОБЯЗАТЕЛЬНО:

1. Исследуй фактическое состояние repository.
2. Проверь результаты предыдущего Forensics.
3. Найди реальные реализации.
4. Проверь актуальные symbols/API.
5. Проверь тесты.
6. Проверь текущие execution paths.
7. Убедись, что описанный GAP всё ещё существует.

НЕ доверяй старому отчёту слепо.

Forensics report является ориентиром.

Код является источником истины.

Если GAP уже устранён:

НЕ реализуй его повторно.

Зафиксируй:

ALREADY RESOLVED.

--------------------------------------------------
# 2. ОСНОВНОЙ FORENSICS BASELINE
--------------------------------------------------

Используй результаты:

INTELLIGENCE_INTEGRATION_FORENSICS_V1

В частности:

- Repository Reality Map
- Intelligence Integration Map
- Contract Matrix
- Existing Reuse Map
- Gap Map
- Documentation/Code Drift
- Traceability Map
- Intelligence Data Flow
- First Vertical Slice
- Evidence Ledger
- Evaluation Report

Предыдущий forensic analysis определил следующие основные разрывы:

GAP-1:
DISCOVER использует stub-кандидатов вместо реальных источников.

GAP-2:
результат Opportunity → Execution не полностью возвращается в Memory / Learning.

GAP-4/GAP-5:
требуется завершить контрактную/интеграционную часть Opportunity/Whim согласно фактическому repository.

НО:

ПЕРЕД РЕАЛИЗАЦИЕЙ ПРОВЕРЬ КАЖДЫЙ GAP.

--------------------------------------------------
# 3. SCOPE
--------------------------------------------------

В этой фазе разрешено работать только над:

A. Реальным DISCOVER.

B. Реальным ACCUMULATE / LEARNING.

C. Необходимыми контрактами Opportunity / Whim.

D. Тестами этих механизмов.

E. Документацией, которая непосредственно описывает изменённое поведение.

F. Traceability/evidence для новой реализации.

НЕ делать:

- новый EventBus;
- новую Memory System;
- новый Knowledge Engine;
- новый Scenario Engine;
- новый Forge;
- новый Agent Runtime;
- новый Scheduler;
- новый MCP;
- новый Plugin System;
- новый Workspace UI;
- полноценный Content Intelligence;
- Concept Evolution System;
- C-A;
- C-B;
- C-C;
- Evolution Memory;
- автономный Project Intelligence;
- массовый рефакторинг.

--------------------------------------------------
# 4. АРХИТЕКТУРНЫЙ ПРИНЦИП
--------------------------------------------------

НЕ строить Intelligence как отдельную платформу.

Использовать существующие:

Project
Workspace
Whim
Opportunity
Memory
Knowledge
EventBus
ProjectPulse
ScenarioRegistry
Factory
ForgeFacade
ForgePipeline
RoleArtifactValidator
LearningLoop
Agent Runtime
Scheduler

если они действительно присутствуют.

Новые компоненты создавать только если forensic verification докажет, что без них невозможно закрыть конкретный GAP.

--------------------------------------------------
# 5. ЦЕЛЕВОЙ КОНТУР
--------------------------------------------------

После Phase 5 должен существовать реальный минимальный путь:

REAL INPUT
   ↓
OBSERVATION / WHIM
   ↓
DISCOVER
   ↓
OPPORTUNITY
   ↓
SCENARIO SELECTION
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

И самое главное:

MEMORY / LEARNING
        ↓
следующий DISCOVER

То есть результат одного цикла становится информацией для следующего.

--------------------------------------------------
# 6. ЭТАП 0 — PRE-IMPLEMENTATION FORENSICS
--------------------------------------------------

До написания кода создай:

PHASE5_PRE_IMPLEMENTATION_AUDIT.md

В нём зафиксируй:

1. Текущий статус GAP-1.
2. Текущий статус GAP-2.
3. Текущий статус GAP-4.
4. Текущий статус GAP-5.
5. Фактические файлы.
6. Фактические symbols.
7. Фактические call paths.
8. Существующие тесты.
9. Какие части уже реализованы.
10. Что конкретно требуется изменить.

Для каждого:

FACT
EVIDENCE
DECISION

Если обнаружено расхождение с предыдущим Forensics:

DOCUMENTATION ≠ CURRENT CODE

зафиксируй это отдельно.

После этого только переходи к реализации.

--------------------------------------------------
# 7. GAP-1 — REAL DISCOVER
--------------------------------------------------

Найди существующий:

OpportunityEngine.discover_candidates()

и весь путь вокруг него.

Определи все реальные источники:

- Whim;
- ProjectPulse;
- Memory;
- Knowledge;
- EventBus;
- Project state;
- другие существующие источники, если они реально есть.

ЗАПРЕЩЕНО оставлять production-path на уровне:

"Stub signal from ..."

если соответствующий источник уже существует.

Нужно построить минимальный реальный pipeline:

SOURCE
 ↓
OBSERVATION / SIGNAL
 ↓
DISCOVER
 ↓
CANDIDATE
 ↓
OPPORTUNITY

При этом:

НЕ создавать новую систему Signal, если существующий Event/Observation способен выполнить эту роль.

НЕ создавать новую storage system.

НЕ дублировать ProjectPulse.

НЕ дублировать Knowledge.

--------------------------------------------------
# 8. DISCOVER НЕ ДОЛЖЕН ГЕНЕРИРОВАТЬ МУСОР
--------------------------------------------------

Discovery должен иметь provenance.

Каждый candidate должен знать:

- source;
- source_id;
- project_id;
- timestamp;
- reason;
- evidence;
- confidence, если механизм уже поддерживает confidence.

Пример:

OpportunityCandidate

source:
project_pulse

evidence:
...

reason:
...

confidence:
...

Если конкретное поле невозможно поддержать существующим контрактом:

не выдумывать его молча.

Определить минимальное расширение контракта.

--------------------------------------------------
# 9. GAP-2 — CLOSE ACCUMULATE
--------------------------------------------------

Найди реальный execution path:

Opportunity
 ↓
Scenario
 ↓
Factory
 ↓
Forge
 ↓
Artifact

После успешного execution:

Artifact
 ↓
Opportunity result
 ↓
Memory
 ↓
Learning

должен стать реальным путём.

Проверь существующие:

MemoryStore
MemoryEngine
KnowledgeEngine
LearningLoop
EventBus

Используй существующие механизмы.

НЕ создавать второй механизм памяти.

--------------------------------------------------
# 10. RESULT PROVENANCE
--------------------------------------------------

После выполнения opportunity должна сохраняться связь:

OPPORTUNITY
    ↓
SCENARIO
    ↓
EXECUTION
    ↓
ARTIFACT
    ↓
MEMORY ENTRY

Если существующая модель позволяет хранить такую lineage — использовать её.

Если не позволяет:

создать минимальное расширение существующего контракта.

Не создавать отдельную database только для lineage.

--------------------------------------------------
# 11. LEARNING
--------------------------------------------------

Проверь существующий LearningLoop.

Определи:

что он принимает;

что он записывает;

как confidence обновляется;

какие observations/lessons уже поддерживаются.

Интегрируй результат Opportunity в существующий LearningLoop только если это соответствует его реальному контракту.

НЕ изобретай новую learning architecture.

--------------------------------------------------
# 12. WHIM CONTRACT
--------------------------------------------------

Если forensic verification подтверждает GAP:

привести Whim к минимальному устойчивому контракту.

Whim должен быть:

лёгким входом в систему.

Минимальная логика:

WHIM
 ↓
STORE / CAPTURE
 ↓
CLASSIFY / ANALYZE
 ↓
OPTIONAL OPPORTUNITY

ВАЖНО:

Whim ≠ Opportunity.

Каждый Whim не обязан становиться Opportunity.

--------------------------------------------------
# 13. DEFERRED ≠ DELETED
--------------------------------------------------

Это обязательное архитектурное правило.

Если пользователь отклонил Opportunity:

это НЕ означает:

DELETE.

Состояние должно сохранять возможность дальнейшего использования.

Например:

ACTIVE
DEFERRED
READY
COMPLETED

и/или существующие реальные lifecycle states, если repository уже определяет другие.

Не добавляй новые states без необходимости.

Семантика:

DEFERRED =
"не сейчас"

а не:

"никогда".

При появлении нового контекста Opportunity должна потенциально быть обнаружена/реактивирована снова.

--------------------------------------------------
# 14. SCENARIO
--------------------------------------------------

НЕ менять Scenario Engine без необходимости.

Использовать существующий:

ScenarioRegistry
Scenario manifests
scenario selection
existing adapters

Intelligence отвечает:

WHAT / WHY

Scenario отвечает:

HOW

Factory отвечает:

CAPABILITY / PRODUCTION DOMAIN

Forge отвечает:

EXECUTION

Это разделение не нарушать.

--------------------------------------------------
# 15. FACTORY
--------------------------------------------------

НЕ создавать Factory заново.

Исследуй фактический статус Factory.

Если FactoryRegistry / Passport всё ещё отсутствует:

не пытайся построить полноценную Factory System в этой фазе.

Используй существующий Forge/Scenario путь.

Factory Gap может быть отдельной следующей задачей, если без него невозможно закрыть текущий slice.

--------------------------------------------------
# 16. FORGE
--------------------------------------------------

Forge вызывается только через существующий санкционированный integration point.

Если repository подтверждает:

ForgeFacade

использовать именно его.

НЕ создавать прямые вызовы Forge из нового Intelligence-кода.

НЕ обходить validation.

НЕ обходить ForgeRegistry.

--------------------------------------------------
# 17. ERROR HANDLING
--------------------------------------------------

Продумать реальные failure paths:

DISCOVER failure
OPPORTUNITY validation failure
SCENARIO selection failure
FORGE failure
VALIDATION failure
MEMORY failure
LEARNING failure

Не скрывать ошибки.

Не переводить ошибочный execution в COMPLETED.

Если execution завершён, но Memory недоступна:

состояние должно отражать partial failure согласно существующему lifecycle.

НЕ придумывай новый distributed transaction механизм.

Используй существующие retry/event mechanisms, если они есть.

--------------------------------------------------
# 18. IDEMPOTENCY
--------------------------------------------------

Особенно проверить:

cron
ProjectPulse
EventBus
repeated discovery
retry
resume

Один и тот же сигнал не должен бесконечно создавать одинаковые Opportunity.

Если repository уже имеет deduplication mechanism:

использовать его.

Если нет:

создать минимальный deterministic identity / deduplication механизм.

--------------------------------------------------
# 19. TEST-FIRST / REGRESSION
--------------------------------------------------

До изменения production code:

изучи существующий тестовый набор.

Добавь тесты для нового поведения.

Минимальный набор:

TEST 1
real source → discover candidate

TEST 2
candidate → opportunity

TEST 3
opportunity → scenario

TEST 4
scenario → existing execution path

TEST 5
execution → artifact

TEST 6
artifact → memory

TEST 7
memory → learning

TEST 8
same source repeated → no uncontrolled duplicate opportunity

TEST 9
DEFERRED opportunity remains recoverable

TEST 10
failure does not become false COMPLETED

Если часть тестов невозможно сделать без полного production environment:

создай наиболее близкий integration test и явно укажи limitation.

--------------------------------------------------
# 20. END-TO-END TEST
--------------------------------------------------

Обязательно создать один реальный E2E vertical slice.

Пример:

TEST INPUT
 ↓
REAL DISCOVER SOURCE
 ↓
OPPORTUNITY
 ↓
SCENARIO
 ↓
EXISTING FACTORY/FORGE
 ↓
ARTIFACT
 ↓
MEMORY
 ↓
LEARNING

Не mock'ать весь pipeline.

Mock разрешён только там, где внешний ресурс действительно недоступен.

Цель:

доказать, что позвоночник работает.

--------------------------------------------------
# 21. DOCUMENTATION ↔ CODE
--------------------------------------------------

После реализации:

обновить только ту документацию, которая теперь фактически изменилась.

Каждый новый architectural claim должен иметь связь:

DOCUMENT
 ↓
ANCHOR
 ↓
CODE SYMBOL
 ↓
TEST

Если существующий AnchorResolver позволяет это сделать — использовать его.

НЕ создавать новую traceability system.

--------------------------------------------------
# 22. IMPLEMENTATION LOG
--------------------------------------------------

Создать:

PHASE5_IMPLEMENTATION_LOG.md

Для каждого изменения:

FILE
SYMBOL
OLD BEHAVIOUR
NEW BEHAVIOUR
WHY
TEST
EVIDENCE

--------------------------------------------------
# 23. НЕ РАСШИРЯТЬ SCOPE
--------------------------------------------------

Если во время работы обнаруживаются интересные проблемы:

не исправлять их автоматически.

Создать:

PHASE5_FUTURE_GAPS.md

Например:

- полноценный FactoryRegistry;
- Advanced Opportunity Ranking;
- Scenario Intelligence;
- Content Intelligence;
- Concept Evolution;
- C-A;
- C-B;
- C-C;
- Evolution Memory;
- Workspace UI;
- autonomous project intelligence.

Это будущие этапы.

Не смешивать их с текущей задачей.

--------------------------------------------------
# 24. VALIDATION GATE
--------------------------------------------------

После реализации выполнить:

1. Unit tests.
2. Integration tests.
3. E2E test.
4. Existing regression suite.
5. Static checks.
6. Import checks.
7. Contract validation.
8. Documentation consistency check.

Если какой-либо тест падает:

НЕ объявлять работу завершённой.

--------------------------------------------------
# 25. FINAL FORENSICS
--------------------------------------------------

После реализации повторно исследовать изменённые участки.

Создать:

PHASE5_POST_IMPLEMENTATION_FORENSICS.md

Сравнить:

BEFORE
vs
AFTER

Для каждого GAP:

GAP-1 → RESOLVED / PARTIAL / BLOCKED
GAP-2 → RESOLVED / PARTIAL / BLOCKED
GAP-4 → RESOLVED / PARTIAL / BLOCKED
GAP-5 → RESOLVED / PARTIAL / BLOCKED

--------------------------------------------------
# 26. ARCHITECTURAL VALIDATION
--------------------------------------------------

Проверить:

[ ***REMOVED*** Intelligence не стал отдельной платформой.
[ ***REMOVED*** EventBus не продублирован.
[ ***REMOVED*** Memory не продублирована.
[ ***REMOVED*** Knowledge не продублирована.
[ ***REMOVED*** Scenario Engine не продублирован.
[ ***REMOVED*** Forge не вызывается в обход ForgeFacade.
[ ***REMOVED*** Opportunity имеет provenance.
[ ***REMOVED*** Whim и Opportunity не смешаны.
[ ***REMOVED*** DEFERRED ≠ DELETED.
[ ***REMOVED*** Discovery использует реальные источники.
[ ***REMOVED*** Stub discovery не является production path.
[ ***REMOVED*** Artifact возвращается в Memory.
[ ***REMOVED*** Learning получает результат.
[ ***REMOVED*** Повторный сигнал не создаёт uncontrolled duplicates.
[ ***REMOVED*** Ошибки не маскируются как COMPLETED.
[ ***REMOVED*** Existing tests не сломаны.
[ ***REMOVED*** Documentation соответствует коду.

--------------------------------------------------
# 27. EVALUATION PACKAGE
--------------------------------------------------

После завершения НЕ просто напиши сообщение.

Создай отдельный Evaluation Package.

Он должен содержать:

01_PRE_IMPLEMENTATION_AUDIT.md
02_IMPLEMENTATION_LOG.md
03_POST_IMPLEMENTATION_FORENSICS.md
04_GAP_RESOLUTION_MATRIX.md
05_INTELLIGENCE_DATA_FLOW.md
06_CONTRACT_CHANGES.md
07_TEST_REPORT.md
08_DOCUMENTATION_CODE_TRACEABILITY.md
09_FUTURE_GAPS.md
10_FINAL_ARCHITECTURAL_DECISION.md
11_EVIDENCE_LEDGER.md
README.md
MANIFEST.md

В MANIFEST.md:

- файл;
- размер;
- SHA-256.

README должен объяснять:

что было;
что изменено;
почему;
какие GAP закрыты;
какие остались;
как проверить;
какой следующий шаг.

--------------------------------------------------
# 28. АРХИВ
--------------------------------------------------

Создать отдельный архив:

PHASE5_INTELLIGENCE_LOOP_<VERSION>.tar.gz

В архив включить:

- только изменённые/созданные файлы;
- Evaluation Package;
- необходимые tests;
- необходимые documentation changes;
- manifest;
- README.

НЕ включать:

.git
node_modules
__pycache__
venv
.cache
build artifacts
large generated files
секреты
API keys
tokens
credentials
полный repository.

ВАЖНО:

Архив должен быть пригоден для независимой оценки работы.

--------------------------------------------------
# 29. SECURITY CHECK
--------------------------------------------------

Перед созданием архива проверить:

grep / scan на:

API keys
tokens
passwords
private keys
.env
credentials
secrets

Если найден секрет:

НЕ включать его в архив.

--------------------------------------------------
# 30. FINAL RESPONSE
--------------------------------------------------

В финальном ответе сообщить:

1. Что было найдено перед реализацией.
2. Что реально изменено.
3. Какие GAP закрыты.
4. Какие GAP не закрыты.
5. Какие файлы изменены.
6. Какие тесты прошли.
7. Какой E2E flow доказан.
8. Какие архитектурные решения приняты.
9. Какие проблемы намеренно НЕ трогались.
10. Какой следующий шаг roadmap.

Обязательно указать путь к созданному архиву.

--------------------------------------------------
# 31. ABSOLUTE RULE
--------------------------------------------------

НЕ считать задачу завершённой только потому, что код написан.

Задача завершена только когда:

FORENSICS
   ↓
IMPLEMENTATION
   ↓
TEST
   ↓
E2E
   ↓
POST-FORENSICS
   ↓
DOCUMENTATION
   ↓
EVALUATION PACKAGE
   ↓
ARCHIVE

полностью пройдены.

# END OF PROMPT