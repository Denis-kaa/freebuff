PHASE 8 — UNIVERSAL SCENARIO INTELLIGENCE

Repository Forensics → Contract → Implementation → Validation

Роль

Ты — Senior AI Systems Architect, Repository Forensics Engineer и Implementation Engineer.

Ты работаешь над существующей платформой Freebuff / Workspace OS.

Твоя задача — реализовать Phase 8: Universal Scenario Intelligence.

Это универсальный слой принятия решений, а не Content Intelligence.

Он не должен быть привязан к:

- контенту;
- текстам;
- книгам;
- коду;
- изображениям;
- видео;
- исследованиям;
- конкретному типу проекта.

Главный архитектурный инвариант

Система должна быть способна работать с произвольным доменом.

Например:

- CONTENT
- CODE
- MEDIA
- RESEARCH
- DOCUMENT
- AUTOMATION
- DESIGN
- STORY
- и будущими доменами, которых ещё нет.

Ни один универсальный контракт Phase 8 не должен содержать жёсткой зависимости от "content".

---

0. Источник истины

Repository = Source of Truth.

Перед любой реализацией:

1. полностью исследуй текущий repository;
2. исследуй результаты Phase 7;
3. построй Current Reality Map;
4. подтверди реальные integration gaps;
5. только после этого проектируй и реализуй изменения.

Приоритет источников:

1. код;
2. тесты;
3. runtime/config;
4. machine-readable contracts;
5. документация;
6. forensic reports;
7. предположения.

---

1. Контекст

После Phase 7 существует подтверждённая цепочка:

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
FORGE
  ↓
ARTIFACT
  ↓
MEMORY
  ↓
EVENT BUS
  ↓
INTELLIGENCE

Phase 7 закрыла:

- Opportunity → Factory;
- Factory → ForgeFacade;
- Opportunity lifecycle;
- EventBus integration;
- traceability;
- integration tests.

Не перепроектируй эти слои.

---

2. Цель Phase 8

Создать универсальный слой:

OPPORTUNITY
   ↓
SCENARIO DISCOVERY
   ↓
CANDIDATE SCENARIOS
   ↓
EVALUATION
   ↓
RANKING
   ↓
SELECTION
   ↓
CAPABILITY
   ↓
FACTORY
   ↓
FORGE

Scenario Intelligence отвечает только на вопрос:

«Какой способ реализации текущей Opportunity наиболее подходит в текущем контексте проекта?»

Он не производит результат.

---

3. Разделение ответственности

Project Intelligence

Отвечает:

- что происходит;
- какие сигналы появились;
- какие возможности существуют;
- что имеет смысл делать.

Scenario Intelligence

Отвечает:

- какими способами можно реализовать Opportunity;
- какие сценарии доступны;
- какой сценарий лучше;
- почему он лучше;
- насколько решение уверенное.

Factory

Отвечает:

- какой производственный домен способен выполнить сценарий;
- какие capabilities доступны.

Forge

Отвечает:

- непосредственное выполнение.

Artifact

Отвечает:

- результат выполнения.

---

4. Универсальность

Не создавай:

- ContentScenario;
- ContentScenarioSelector;
- ContentOpportunity;
- ContentFactoryAdapter,

если архитектурно достаточно универсальных сущностей.

Предпочитай:

- ScenarioCandidate;
- ScenarioSelection;
- ScenarioDecision;
- CapabilityRequirement;
- Domain (если реально нужен).

Если в repository уже существует понятие домена — используй его.

Если нет, не вводи его без необходимости.

---

5. Candidate Discovery

Исследуй существующий:

- ScenarioRegistry;
- YAML manifests;
- "list_scenarios()";
- "get()";
- "find_role()";
- "propose_roles()";
- validation.

Scenario Intelligence должен использовать существующий ScenarioRegistry как каталог.

Не создавай второй registry.

Одна Opportunity может иметь несколько кандидатов.

Пример:

Opportunity
   ├── Scenario A
   ├── Scenario B
   ├── Scenario C
   └── Scenario D

Это справедливо для любого домена.

---

6. Оценка сценариев

Минимально исследуй возможность учитывать:

- relevance;
- project context;
- goals;
- constraints;
- capability availability;
- feasibility;
- previous executions;
- confidence;
- evidence.

Не вводи показатели автоматически.

Сначала проверь, какие механизмы уже существуют:

- SemanticLayer;
- LearningLoop;
- KnowledgeEngine;
- GraphIndex;
- ForgeRegistry;
- MemoryStore.

Переиспользуй их.

---

7. Ranking

Scenario Intelligence должен:

1. получить кандидатов;
2. оценить каждого;
3. ранжировать;
4. выбрать текущий лучший;
5. сохранить причины выбора.

Результат должен быть объясним.

Например:

Selected Scenario: scenario_x

Score: 0.84

Reasons:
- project goal match
- capability available
- previous successful execution
- constraints satisfied

Evidence:
- opportunity_id
- project context
- scenario manifest
- previous execution references

Никакого black-box решения без provenance.

---

8. Domain-neutral Capability Resolution

После выбора Scenario система должна определить требуемую capability.

Пример концептуально:

Scenario
   ↓
Capability Requirement
   ↓
FactoryRegistry
   ↓
ForgePassport
   ↓
ForgeFacade

Capability может относиться к любому домену.

Например:

- article_generation;
- api_implementation;
- image_generation;
- market_research;
- screenplay_development.

Но Phase 8 не должна зашивать эти примеры в код.

Они лишь демонстрируют универсальность.

---

9. Feedback Loop v0

После выполнения:

Artifact
   ↓
Execution Result
   ↓
Scenario Feedback
   ↓
Memory / Learning
   ↓
Future Scenario Ranking

Сохраняй возможность учитывать:

- success/failure;
- validation result;
- execution metadata;
- previous scenario outcome.

Не строить ML/RL.

Только прозрачный feedback v0.

---

10. Lifecycle

Не выбранный Scenario не удаляется автоматически.

Поддерживай существующую семантику:

- selected;
- deferred;
- superseded;
- unavailable;

только если она соответствует существующим контрактам.

Не изобретай lifecycle без необходимости.

---

11. EventBus

Исследуй события Phase 7.

Добавляй только реально необходимые события, например:

- "scenario.candidates.generated"
- "scenario.evaluated"
- "scenario.selected"
- "scenario.reselected"

Но только после проверки существующей event model.

Каждое событие должно иметь:

- producer;
- consumer или обоснованное хранение;
- payload;
- test.

---

12. Persistence

Не создавай новую БД.

Используй существующие механизмы:

- MemoryStore;
- EventBus storage;
- ForgeRegistry;
- Opportunity persistence,

если они подходят.

Decision history должна сохраняться через существующую инфраструктуру.

---

13. Forensics

Перед реализацией обязательно исследуй:

- "opportunity_engine.py"
- "whim_capture.py"
- "scenario_registry.py"
- "factory_registry.py"
- "forge_facade.py"
- "forge_pipeline.py"
- "memory_store.py"
- "semantic_layer.py"
- "learning_loop.py"
- "knowledge_engine.py"
- "graph_index.py"
- "event_bus.py"
- Workspace / Project
- Scenario YAML manifests
- Phase 7 evaluation package
- AGENTS.md
- BUFFY.md
- тесты.

Читай:

- код;
- callers;
- callees;
- тесты;
- конфиги;
- документацию.

---

14. Reality Map

Создай:

"PHASE8_REALITY_MAP.md"

Таблица:

| Component | Path | Symbol | Current Behavior | Reusable | Gap |

Отдельно зафиксируй:

- current scenario discovery;
- current scenario selection;
- current factory routing;
- current feedback path.

---

15. Gap Map

Создай:

"PHASE8_GAP_MAP.md"

Используй:

- G0 — существует;
- G1 — adapter;
- G2 — design exists;
- G3 — implementation required;
- G4 — conflict.

Проверяй поведение, а не названия.

---

16. Contract

Создай:

"SCENARIO_INTELLIGENCE_CONTRACT_V1.md"

Он должен быть domain-neutral и описывать:

- input;
- context;
- candidate discovery;
- evaluation;
- ranking;
- selection;
- capability resolution;
- provenance;
- feedback;
- persistence;
- events;
- Factory boundary;
- Forge boundary;
- fallback;
- backward compatibility.

---

17. Implementation

Реализуй минимальный vertical slice.

Не создавай:

- Content Factory;
- Code Factory;
- Media Factory;
- Concept Evolution;
- C-A/C-B/C-C;
- Workspace UI;
- новую orchestration system.

Phase 8 заканчивается на:

Opportunity
   ↓
Scenario Intelligence
   ↓
Factory
   ↓
Forge
   ↓
Artifact
   ↓
Feedback

---

18. Tests

Добавь тесты для:

1. candidate discovery;
2. multiple scenarios;
3. ranking;
4. selection;
5. provenance;
6. capability resolution;
7. Factory routing;
8. Forge boundary;
9. feedback;
10. EventBus;
11. persistence;
12. backward compatibility;
13. unavailable scenario;
14. deferred opportunity;
15. re-selection after new evidence.

Главный integration test:

Opportunity
 → multiple Scenario candidates
 → evaluation
 → ranking
 → selected Scenario
 → capability
 → FactoryRegistry
 → ForgeFacade
 → Artifact
 → feedback
 → Memory

---

19. Traceability

Создай:

"PHASE8_TRACEABILITY.md"

Цепочка:

Requirement
   ↓
Contract
   ↓
Code
   ↓
Test
   ↓
Evidence

---

20. Anti-overengineering

Перед завершением проверь, что не созданы:

- новый Scenario Registry;
- новый Factory engine;
- новый Forge;
- новая Memory;
- новый EventBus;
- новая БД;
- новый LLM framework;
- доменно-специфичные контракты без необходимости.

Если что-то из этого создано — обоснуй.

---

21. Definition of Done

Phase 8 COMPLETE только если:

- repository исследован;
- reality map создан;
- gap map создан;
- contract создан;
- Scenario Intelligence реализован;
- поддерживается несколько сценариев;
- есть evaluation;
- есть ranking;
- есть selection;
- есть provenance;
- capability resolution универсален;
- Factory boundary соблюдён;
- ForgeFacade остаётся execution boundary;
- feedback v0 работает;
- EventBus интегрирован;
- tests проходят;
- regression tests проходят;
- документация синхронизирована;
- traceability создана;
- evaluation archive создан.

---

22. Evaluation Archive

Обязательно создай:

"PHASE8_EVALUATION_<VERSION>.tar.gz"

Содержимое:

phase8_evaluation/
├── PHASE8_REALITY_MAP.md
├── PHASE8_GAP_MAP.md
├── SCENARIO_INTELLIGENCE_CONTRACT_V1.md
├── PHASE8_IMPLEMENTATION_PLAN.md
├── PHASE8_TRACEABILITY.md
├── PHASE8_EVALUATION_REPORT.md
├── changed_files/
├── tests/
├── evidence/
└── MANIFEST.md

Не включай весь repository, ".git", окружения, кэши, секреты.

---

23. Следующая фаза

После завершения Phase 8 не реализовывай конкретные Factory.

Подготовь:

"NEXT_PHASE_RECOMMENDATION.md"

Следующая архитектурная фаза должна использовать универсальный контракт Factory для добавления первого доменного vertical slice.

Это может быть:

- Content Factory;
- Code Factory;
- Research Factory;

но выбор конкретного домена не должен менять универсальные контракты Phase 8.

---

Финальный принцип

Строится не Content Intelligence.

Строится универсальный Scenario Intelligence, который способен выбирать способ реализации Opportunity независимо от того, относится ли проект к контенту, программированию, медиа, исследованиям или будущему домену.

Универсальное ядро должно оставаться domain-neutral.

Конкретные Factory — это подключаемые производственные домены поверх этого ядра.