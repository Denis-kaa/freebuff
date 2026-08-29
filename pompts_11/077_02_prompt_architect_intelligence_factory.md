Да. Тогда сейчас включаем Prompt Architect — но не для реализации всей системы, а для проектирования именно контракта Intelligence ↔ Factory.

Это правильная граница: IDEA EXPLORER уже исследовал концепцию, а Prompt Architect теперь превращает её в исполнимое техническое задание для агента-разработчика.

PROMPT ARCHITECT — Intelligence ↔ Factory Contract

ROLE

Ты — Senior AI Architect / System Integration Architect.

Твоя задача — спроектировать контракт взаимодействия между существующим Project Intelligence Engine и существующим Factory / Scenario / Forge Engine внутри уже работающей платформы.

Ты НЕ должен проектировать платформу с нуля.

Ты НЕ должен придумывать существующие модули, классы, API или архитектурные слои.

Перед любым проектированием сначала исследуй фактическую архитектуру repository.

---

1. CORE OBJECTIVE

Спроектировать минимальный, реалистичный и расширяемый контракт:

PROJECT INTELLIGENCE
        ↓
OPPORTUNITY / DECISION
        ↓
SCENARIO SELECTION
        ↓
FACTORY
        ↓
FORGE EXECUTION
        ↓
ARTIFACT
        ↓
INTELLIGENCE

Главная цель:

Intelligence определяет, ЧТО и ЗАЧЕМ следует делать.
Factory определяет, КАК это выполнить.

Эти ответственности не должны смешиваться.

---

2. FIRST PRINCIPLE

Перед проектированием выполни Repository Forensics.

Исследуй существующий код и документацию.

Определи фактически существующие:

- Factory;
- Forge;
- Scenario;
- Pipeline;
- Agent;
- Workflow;
- Artifact;
- Project;
- Memory;
- Event / EventBus;
- Registry;
- Storage;
- существующие integration points.

Для каждого найденного компонента укажи:

FACT
SOURCE
ROLE
CONFIDENCE

Если сущность не найдена — не создавай видимость, что она существует.

Используй:

UNKNOWN

или:

PROPOSED

---

3. DO NOT ASSUME ARCHITECTURE

Особенно запрещено автоматически предполагать наличие:

- LLMFactory;
- KeyPool;
- EventBus;
- CircuitBreaker;
- LangGraph;
- отдельного Agent Runtime;
- конкретной БД;
- конкретного message broker;
- конкретного API;
- конкретного orchestration layer.

Используй их только если они реально обнаружены в repository или явно предоставлены пользователем.

---

4. RESPONSIBILITY BOUNDARY

Зафиксируй границу ответственности.

PROJECT INTELLIGENCE

Intelligence отвечает за:

- понимание текущего состояния проекта;
- цели проекта;
- контекст;
- обнаружение возможностей;
- формирование hypotheses;
- оценку направлений;
- приоритизацию;
- выбор следующего действия;
- предложение Scenario;
- отслеживание результатов;
- переоценку ранее отложенных направлений;
- поддержание истории решений.

Intelligence НЕ реализует Forge.

---

FACTORY

Factory отвечает за:

- доступные Scenarios;
- доступные Forge;
- порядок выполнения;
- необходимые входы;
- execution;
- создание artifacts;
- техническую обработку ошибок;
- возврат результата выполнения.

Factory НЕ решает самостоятельно стратегическую цель проекта.

---

5. OPPORTUNITY MODEL

Спроектируй минимальную модель Opportunity.

Она должна позволять описать:

id
project_id
title
description
source
status
priority
confidence
created_at
updated_at
related_artifacts
related_opportunities
recommended_scenarios

Не добавляй поля без необходимости.

---

6. IMPORTANT: STATUS SEMANTICS

Критическое правило:

REJECTED ≠ DEFERRED

Пользовательское решение не должно интерпретироваться бинарно.

Минимально исследуй состояния:

ACTIVE
DEFERRED
PAUSED
COMPLETED
REJECTED
ARCHIVED
SUPERSEDED

Определи семантику каждого состояния.

Особенно:

DEFERRED

Означает:

««Сейчас направление не является приоритетным.»»

Это НЕ означает:

««Направление плохое.»»

Intelligence должен иметь возможность повторно оценить DEFERRED opportunity при появлении нового контекста.

---

7. SCENARIO CONTRACT

Спроектируй минимальный контракт Scenario.

Scenario должен описывать:

scenario_id
name
purpose
required_inputs
optional_inputs
expected_outputs
constraints
execution_requirements

Scenario — это описание способа решения задачи, а не сама задача.

---

8. INTELLIGENCE → FACTORY

Определи минимальный request contract.

Примерная семантика:

ExecutionRequest

project
objective
opportunity
selected_scenario
inputs
constraints
context
expected_output

Но не принимай эту структуру автоматически.

Проверь, как существующая архитектура реально передаёт задачи между компонентами.

Если существующий механизм уже выполняет эту функцию — адаптируйся к нему.

Не создавай второй параллельный механизм.

---

9. FACTORY → INTELLIGENCE

Определи минимальный result contract.

Результат должен позволять Intelligence понять:

execution_status
scenario
artifacts_created
artifacts_changed
execution_metadata
warnings
errors
next_possible_actions

Также должно быть понятно:

- что реально произошло;
- что было создано;
- что не удалось;
- что можно сделать дальше.

---

10. ARTIFACT FEEDBACK LOOP

Спроектируй обратную связь:

Factory
   ↓
Artifact
   ↓
Intelligence
   ↓
Project State Update
   ↓
New Opportunities

Intelligence не должен считать задачу законченной только потому, что Factory вернул "success".

Он должен иметь возможность анализировать полученный artifact и обновлять состояние проекта.

---

11. SCENARIO ≠ OPPORTUNITY

Не смешивать:

Opportunity
=
что потенциально стоит сделать

Scenario
=
как это можно сделать

Например:

Opportunity:
«Из исследования можно создать книгу.»

Possible Scenarios:

Scenario A:
Research → Outline → Chapters → Editing

Scenario B:
Research → Narrative Structure → Draft → Revision

Scenario C:
Research → Knowledge Base → Book Architecture → Draft

Одна Opportunity может иметь несколько Scenario.

Один Scenario может применяться к нескольким Opportunity.

---

12. FACTORY PRESETS

Проверить архитектурное правило:

Factory presets / готовые сценарии — это не ограничения Intelligence.

Например:

REPACK_21

если существует, должен рассматриваться как один из возможных сценариев Factory, а не как архитектурная модель всей Content Intelligence системы.

Intelligence может:

- выбрать существующий Scenario;
- выбрать другой Scenario;
- комбинировать допустимые механизмы;
- предложить новый Scenario, если существующих недостаточно.

---

13. USER CONTROL

Пользователь остаётся владельцем стратегического решения.

Intelligence может:

- предложить;
- объяснить;
- сравнить;
- переоценить;
- рекомендовать.

Но не должен считать:

user_declined = opportunity_deleted

Если пользователь отложил направление:

DEFERRED

оно остаётся частью project intelligence graph/history.

---

14. CONTEXT RE-EVALUATION

Спроектируй механизм:

NEW INFORMATION
        ↓
CONTEXT CHANGE
        ↓
RE-EVALUATE DEFERRED OPPORTUNITIES
        ↓
NEW SCORE / NEW RECOMMENDATION

Например:

Opportunity A
DEFERRED

↓

появился новый artifact

↓

новая информация повышает relevance

↓

Intelligence:
«Ранее отложенное направление снова стало актуальным.»


Не создавай автономную систему принятия решений сверх существующих возможностей repository.

Спроектируй только контракт и необходимый integration point.

---

15. MULTIPLE SCENARIOS

Intelligence может обнаружить:

Opportunity X
    ↓
Scenario A
Scenario B
Scenario C

Он должен иметь возможность:

- сравнить сценарии;
- определить recommended scenario;
- объяснить критерий выбора;
- передать выбранный сценарий Factory.

Не выполнять все сценарии автоматически, если для этого нет явного основания.

---

16. OBSERVABILITY

Определи минимальный набор информации, который должен сохраняться для трассировки:

WHO
WHAT
WHY
SCENARIO
INPUT
OUTPUT
RESULT
TIMESTAMP

Особенно важно сохранить связь:

Opportunity
    ↓
Decision
    ↓
Scenario
    ↓
Execution
    ↓
Artifact

Это позволит восстановить историю того, как появился итоговый результат.

---

17. MVP CONSTRAINT

Не проектируй всю Project Intelligence систему.

Не создавай сразу:

- 15+ новых сущностей;
- полный knowledge graph;
- сложный event-driven ecosystem;
- отдельный orchestration framework;
- новый storage layer;
- новую агентную систему.

Цель этого этапа:

один минимальный вертикальный контракт Intelligence ↔ Factory.

Он должен позволить выполнить:

1 Project
↓
1 Opportunity
↓
1 Scenario
↓
1 Factory execution
↓
1 Artifact
↓
1 Intelligence feedback

После успешного vertical slice можно расширять систему.

---

18. COMPATIBILITY RULE

Если существующая архитектура repository отличается от предлагаемой модели:

адаптируй концепцию к существующей архитектуре.

Не переписывай существующую систему ради красивой модели.

Приоритет:

Existing Architecture
        >
Minimal Extension
        >
New Abstraction
        >
Architectural Rewrite

---

19. REQUIRED OUTPUT

Выдай результат в следующем порядке.

A. REPOSITORY FACTS

Только фактически найденная архитектура.

Таблица:

| Component | Exists | Location | Responsibility | Confidence |

---

B. CURRENT INTEGRATION POINTS

Покажи:

EXISTING COMPONENT
        ↓
EXISTING INTERFACE
        ↓
EXISTING EXECUTION

---

C. GAP ANALYSIS

Что уже существует.

Что отсутствует.

Что действительно необходимо добавить.

Разделяй:

REQUIRED
OPTIONAL
FUTURE

---

D. INTELLIGENCE ↔ FACTORY CONTRACT

Предложи минимальный контракт с конкретными структурами.

---

E. STATE MODEL

Определи минимальные состояния:

Opportunity
Scenario
Execution
Artifact

---

F. DATA FLOW

Покажи полный поток:

USER
 ↓
PROJECT INTELLIGENCE
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
INTELLIGENCE
 ↓
NEXT OPPORTUNITY

Адаптируй его к реальной архитектуре repository.

---

G. MVP VERTICAL SLICE

Определи минимальный slice:

1 Opportunity
→ 1 Scenario
→ 1 Execution
→ 1 Artifact
→ 1 Feedback

Укажи:

- какие файлы изменить;
- какие файлы создать;
- что НЕ менять;
- критерии готовности.

Не начинать реализацию.

---

H. ARCHITECTURAL RISKS

Максимум 5 действительно критичных рисков.

---

I. NEXT STEP

Сформулируй один следующий шаг.

Не выдавай десять направлений.

---

FINAL QUALITY GATE

Перед завершением проверь:

- [ ***REMOVED*** Factory и Intelligence не смешаны.
- [ ***REMOVED*** Opportunity и Scenario не смешаны.
- [ ***REMOVED*** Scenario и Forge не смешаны.
- [ ***REMOVED*** REJECTED ≠ DEFERRED.
- [ ***REMOVED*** Deferred opportunities могут быть переоценены.
- [ ***REMOVED*** Existing repository исследован.
- [ ***REMOVED*** Не придуманы несуществующие компоненты.
- [ ***REMOVED*** Не создана параллельная архитектура.
- [ ***REMOVED*** MVP ограничен одним vertical slice.
- [ ***REMOVED*** Artifact возвращается в Intelligence.
- [ ***REMOVED*** Пользователь сохраняет контроль.
- [ ***REMOVED*** Контракт можно реализовать поверх существующей архитектуры.

Финальная строка:

Анти-галлюцинация: проверено.