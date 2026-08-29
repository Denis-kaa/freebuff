FORENSIC TASK — INTERNAL RETRIEVAL & DOCUMENTATION KNOWLEDGE AUDIT

Роль

Ты — Senior AI Systems Architect + Forensic Code Auditor.

Твоя задача — не проектировать новую Retrieval/RAG-систему, а установить, что уже существует в текущей кодовой базе Buffy / Workspace OS и насколько оно способно поддерживать внутренний retrieval loop агента.

Особое внимание удели документации как источнику знаний.

---

1. Контекст

В архитектуре появилась гипотеза:

«Агент перед принятием решения должен уметь самостоятельно сформулировать информационную потребность, обратиться к Knowledge Infrastructure и получить релевантные сведения, не зная заранее, где физически лежит информация.»

Пример:

AGENT
  ↓
INTERNAL QUESTION
  ↓
RETRIEVAL
  ↓
EVIDENCE
  ↓
REASONING
  ↓
DECISION / ACTION

Retrieval потенциально может использовать:

SQL
FTS
Vector / Semantic Search
Graph
Hybrid Retrieval

При этом агент не должен сам выбирать конкретную БД, файл или индекс.

Также появилась гипотеза, что документация должна быть полноценным источником знаний для этого механизма:

LESSONS
ADR
DECISIONS
CHANGELOG
ARCHITECTURE
MANIFEST
PROJECT DOCUMENTATION
...
        ↓
Knowledge Infrastructure
        ↓
Agent Retrieval

Но это пока только архитектурная гипотеза.

---

2. Главный вопрос аудита

Установи фактом по текущему коду:

«Существует ли уже механизм, позволяющий агенту самостоятельно формулировать информационные вопросы и получать из существующей Knowledge/Memory/Documentation инфраструктуры релевантную информацию перед выполнением действия?»

Неважно, называется ли он Retrieval Planner, RAG, Context Retrieval, Knowledge Search, Query Planner или иначе.

Ищи фактическую ответственность, а не название.

---

3. Второй главный вопрос

Установи:

«Является ли документация уже частью машинно используемой Knowledge Infrastructure или сейчас она фактически остаётся преимущественно Markdown-источником для человека/LLM?»

Проверь отдельно:

LESSONS.md
CHANGELOG.md
ADR
DECISIONS
ARCHITECTURE
MANIFEST
ROADMAP
PROJECT documentation
другие значимые *.md

Для каждого установить:

хранится ли в БД?
индексируется ли?
участвует ли в FTS?
участвует ли в semantic retrieval?
имеет ли embeddings?
связан ли через GraphIndex?
имеет ли provenance?
доступен ли агенту автоматически?
требует ли ручного чтения файла?

---

4. НЕ ПРОЕКТИРУЙ НОВУЮ СИСТЕМУ

До завершения forensic:

- не создавать RetrievalPlanner;
- не создавать новый RAG;
- не создавать новую БД;
- не создавать новый Vector Store;
- не создавать новый KnowledgeEngine;
- не создавать DocumentationEngine;
- не менять существующие контракты;
- не рефакторить код;
- не переименовывать сущности;
- не исправлять архитектуру.

Только READ → MAP → CROSS-REFERENCE → VERIFY → REPORT.

---

5. Проверить существующие механизмы

Обязательно исследуй:

Knowledge

- KnowledgeEngine
- FTS5
- TF-IDF
- SVD
- embeddings
- semantic search
- indexing
- ingestion
- retrieval APIs

Memory

- MemoryEngine
- рабочую/сессионную память
- долгосрочную память
- контекст
- context.db

Graph

- GraphIndex
- типы связей
- traversal
- subgraph
- поиск связанных сущностей

Events

- EventBus
- event store
- event log
- event FTS
- связи событий с проектами/решениями/артефактами

Agent Runtime

Найди место, где агент:

получает задачу
→ получает context
→ принимает решение
→ вызывает tool
→ выполняет действие

Установи:

«Может ли он в этот момент самостоятельно запросить Knowledge?»

Если может — покажи конкретный код.

Если не может — зафиксируй GAP.

---

6. Особое внимание — внутренние вопросы агента

Ищи не только явный код вида:

retrieval_planner()

Ищи весь фактический путь:

Task
 ↓
Context construction
 ↓
Question generation
 ↓
Knowledge query
 ↓
Retrieval
 ↓
Evidence
 ↓
Agent

Определи, какие части уже существуют.

Возможные результаты:

FULLY EXISTS
PARTIALLY EXISTS
EXISTS BUT NOT CONNECTED
ONLY DOCUMENTED
NO EVIDENCE

---

7. Проверка документации

Составь таблицу:

Документ| Canonical source| DB| FTS| Vector| Graph| Agent-accessible| Automatic
LESSONS| ?| ?| ?| ?| ?| ?| ?
CHANGELOG| ?| ?| ?| ?| ?| ?| ?
ADR| ?| ?| ?| ?| ?| ?| ?
DECISIONS| ?| ?| ?| ?| ?| ?| ?
ARCHITECTURE| ?| ?| ?| ?| ?| ?| ?
MANIFEST| ?| ?| ?| ?| ?| ?| ?
PROJECT docs| ?| ?| ?| ?| ?| ?| ?

Не заполняй "?" предположением.

Если не найден механизм:

"UNKNOWN — NOT VERIFIED"

---

8. CHANGELOG — отдельная проверка

Особенно исследуй CHANGELOG.

Не исходи из предположения, что его нужно переносить в БД.

Проверь:

1. Есть ли уже event store?
2. Есть ли уже event log?
3. Можно ли считать CHANGELOG проекцией событий?
4. Дублирует ли CHANGELOG данные, которые уже существуют в SQLite?
5. Может ли агент получить историю изменений без чтения огромного Markdown?
6. Есть ли structured representation изменений?
7. Есть ли связь:

CHANGE
 ↓
DECISION
 ↓
CODE CHANGE
 ↓
TEST
 ↓
ARTIFACT

Если существующий Event infrastructure уже способен решить эту задачу — зафиксируй это как reuse opportunity.

Не создавай ChangelogDB только потому, что "CHANGELOG.md" большой.

---

9. LESSONS — отдельная проверка

Исследуй:

LESSONS.md

и все связанные механизмы.

Ответь:

1. Является ли Markdown canonical storage?
2. Есть ли структурированное представление Lesson?
3. Может ли Lesson попасть в KnowledgeEngine?
4. Может ли агент найти Lesson семантически?
5. Можно ли найти Lesson по:

domain
type
severity
project
component
status
date

6. Есть ли provenance/evidence?
7. Есть ли связи Lesson → ADR → Component → Project?
8. Может ли агент автоматически получить релевантные Lessons перед действием?

Особенно проверь потенциальную связь:

REUSE FIRST
      ↓
Agent собирается создать новый компонент
      ↓
Retrieval
      ↓
Existing component?
Existing decision?
Existing lesson?
Existing pattern?
      ↓
YES → reuse/extend
NO  → creation may proceed

Установи, существует ли это фактически, а не только концептуально.

---

10. Шесть Registry — контрольный тест гипотезы

Известно, что предыдущий forensic-анализ обнаруживал несколько конкурирующих Registry.

Используй это как архитектурный контрольный пример.

Вопрос:

«Если бы Internal Retrieval + Evidence Retrieval уже существовали и реально использовались агентами, могла бы система обнаружить существующий Registry/решение до создания нового?»

Не утверждай причинность без evidence.

Раздели:

FACT
INFERENCE
HYPOTHESIS

Если механизм retrieval существует, проверь:

- используется ли он агентом;
- является ли использование обязательным;
- может ли агент его обойти;
- возвращает ли он evidence;
- влияет ли результат retrieval на decision/action.

---

11. Определить фактические границы

Построй карту:

                 CURRENT SYSTEM

Agent
 │
 ├── Context ─────────────── ?
 │
 ├── Memory ──────────────── ?
 │
 ├── Knowledge ───────────── ?
 │
 ├── Graph ───────────────── ?
 │
 ├── Events ──────────────── ?
 │
 └── Documentation ───────── ?

И отдельно:

                 PROPOSED MODEL

Agent
 ↓
Internal Question
 ↓
Retrieval Planner
 ↓
Retrieval Fabric
 ├── SQL
 ├── FTS
 ├── Vector
 ├── Graph
 └── Hybrid
 ↓
Evidence / Context
 ↓
Reasoning
 ↓
Action

Покажи разницу между CURRENT и PROPOSED.

---

12. Конкурирующие ответственности

Особенно ищи дублирование между:

- MemoryEngine
- KnowledgeEngine
- GraphIndex
- ContextManager
- EventStore
- EventBus
- prompt_dispatcher
- существующими RAG/retrieval механизмами
- документацией
- registry/search механизмами
- agent context assembly

Для каждого спорного компонента:

Component
Actual responsibility
Inputs
Outputs
Who calls it
What it stores
What it retrieves
Overlap
Evidence
Confidence

---

13. Итоговая классификация

Каждую найденную функцию классифицируй:

A — EXISTS

Механизм уже реализован и соответствует задаче.

B — PARTIAL

Часть механизма существует, но цепочка не замкнута.

C — EXISTS BUT DISCONNECTED

Компонент есть, но агент его не использует.

D — DOCUMENTED ONLY

Есть концепция/документация, но код не найден.

E — GAP

Функциональности действительно нет.

F — UNKNOWN

Недостаточно evidence.

---

14. Финальный вывод

Ответь на пять вопросов:

Q1

Есть ли уже Internal Retrieval Loop?

Q2

Есть ли уже Retrieval Planner?

Q3

Может ли агент самостоятельно инициировать retrieval перед действием?

Q4

Является ли документация полноценным источником машинного Knowledge?

Q5

Нужна ли вообще новая подсистема Retrieval или существующие KnowledgeEngine + GraphIndex + Events + DB можно объединить существующими контрактами?

---

15. Архитектурное решение НЕ принимать

В конце НЕ пиши:

««Нужно создать Retrieval Fabric».»

Вместо этого напиши:

CURRENT FACTS
↓
IDENTIFIED GAPS
↓
EXISTING REUSABLE COMPONENTS
↓
CONTRACT GAPS
↓
MINIMAL NEXT INVESTIGATION

Если окажется, что новая подсистема действительно нужна, сформулируй это только как:

«CANDIDATE ARCHITECTURAL DIRECTION»

а не как утверждённую архитектуру.

---

16. Формат результата

Отчёт должен иметь:

1. Executive Summary
2. Evidence Map
3. Current Retrieval Architecture
4. Agent → Context → Knowledge flow
5. Documentation Knowledge Audit
6. LESSONS Audit
7. CHANGELOG / EventStore Audit
8. Memory / Knowledge / Graph boundary audit
9. Registry control-case analysis
10. Duplicate responsibility matrix
11. Current vs Proposed model
12. Gaps
13. Reusable existing components
14. UNKNOWN / NOT VERIFIED
15. Minimal next step
16. Recommendation

Для каждого существенного утверждения:

CLAIM
EVIDENCE
CONFIDENCE
STATUS

---

17. Жёсткое ограничение

Код не изменять.

Не создавать файлы.

Не выполнять рефакторинг.

Не исправлять найденные проблемы.

Не реализовывать Retrieval Planner.

Не реализовывать RAG.

Не переносить документацию в SQL.

Не менять CHANGELOG.

Не менять LESSONS.

Задача заканчивается архитектурной forensic-картой, на основании которой следующий агент сможет принять решение.

Главная цель:

«Понять, что в текущей Buffy уже является Retrieval/Knowledge Infrastructure, что действительно отсутствует, и является ли Internal Retrieval Loop новой сущностью или недостающим контрактом между уже существующими компонентами.»