Да. Я бы дал агенту уже не общий промт, а implementation task с жёсткой границей, чтобы он не начал самовольно строить половину системы.

# IMPLEMENTATION TASK
# Deterministic Core — Phase B + C
# Competency Map v0.1 + Exercism Ingestion Pipeline v0.1

РОЛЬ

Ты — Senior Python Engineer / Data & Architecture Engineer.

Твоя задача — реализовать ТОЛЬКО Phase B + Phase C
детерминированного ядра системы обучения Python.

Архитектурный контракт зафиксирован в:

    Deterministic Core — Architecture Blueprint v0.1

Этот документ является source of truth.

НЕ пересматривай архитектуру целиком.
НЕ расширяй scope самостоятельно.
НЕ начинай реализацию следующих фаз.

---

# 1. ЦЕЛЬ ЭТОГО ЭТАПА

Нужно получить два работающих компонента:

1. Competency Map v0.1
2. Exercism Python Corpus Ingestion Pipeline v0.1

На выходе должна существовать локальная база знаний, в которой:

    Exercism exercise
        ↓
    provenance / license
        ↓
    competency
        ↓
    skill tags
        ↓
    difficulty rung
        ↓
    tests / metadata
        ↓
    готово для последующего Grader / Learning Engine

При этом система пока НЕ должна:

- выполнять пользовательский код;
- запускать pytest на student submission;
- запускать sandbox;
- вычислять FSRS;
- выбирать следующее упражнение;
- обновлять competency state;
- использовать LLM;
- поднимать FastAPI;
- создавать UI.

---

# 2. SOURCE OF TRUTH

Ориентируйся на:

    Deterministic Core — Architecture Blueprint v0.1

Ключевые зафиксированные контракты:

## Competency

```yaml
competency:
  id:
  name:
  description:
  prerequisites: [***REMOVED***
  understand_criteria:
  can_do_criteria:
  typical_errors: [***REMOVED***
  verification_exercise:
  project_marker:

Exercise

exercise:
  id:
  source_id:
  type:
    - concept
    - practice
  competency_id:
  skill_tags: [***REMOVED***
  difficulty_rung:
    - repetition
    - analogy
    - new
    - unfamiliar_context
    - combination
    - independent
  tests_ref:
  reference_solution_ref:

Exercise Source

exercise_source:
  id:
  url:
  repo:
  file:
  detected_license:
  license_evidence:
  redistribution_allowed:
  modification_allowed:
  attribution_required:
  status:
    - pending
    - approved
    - rejected

Критическое правило:

EXERCISE НЕ МОЖЕТ ПОПАСТЬ В LIVE CORPUS, если:

exercise_source.status != approved


---

3. SCOPE

В ЭТОМ TASK разрешено реализовать:

Competency definitions
Competency registry
Exercise schema
Exercise source/provenance
Exercism repository ingestion
Exercise metadata parser
Test metadata extraction
Competency mapping
Difficulty mapping
Validation
Corpus reports
SQLite persistence
Unit tests
CLI для ingestion

В ЭТОМ TASK запрещено реализовать:

Sandbox
Docker
nsjail
subprocess execution of student code
Autograder
AST error detector
Pylint execution
Radon execution
Flake8 execution
Bandit execution
FSRS
Learning State Machine
Evidence Engine
Activity Selector
FastAPI
Frontend
LLM integration
Tutor
Mentor
Curator
Project Engine

Если для текущей задачи кажется необходимым что-то из запрещённого списка:

НЕ реализовывай это.

Зафиксируй dependency в отчёте.


---

4. ПЕРЕД КОДОМ — INSPECTION

Перед созданием файлов:

1. Исследуй существующий repository.


2. Определи текущую структуру проекта.


3. Найди существующие:

pyproject.toml

requirements

migrations

database layer

models

config

tests

docs



4. Проверь, есть ли уже что-то связанное с:

curriculum

competency

exercises

learning

SQLite.




НЕ дублируй существующую инфраструктуру.

Если repository пустой — создай минимальную структуру.


---

5. PYTHON VERSION

Используй версию Python, уже принятую проектом.

Если проект не фиксирует версию:

используй современный стабильный Python 3.x, но сначала зафиксируй решение в отчёте.

Не меняй существующий runtime без необходимости.


---

6. COMPETENCY MAP v0.1

Нужно создать первую машинно-читаемую карту компетенций.

Не пытайся создать идеальную педагогическую систему на сотни компетенций.

Нужна:

> минимальная, но достаточно глубокая версия, позволяющая реально маппить Exercism Python.



Минимально исследуй следующие области:

Python Fundamentals
 ├── variables
 ├── primitive_types
 ├── expressions
 ├── boolean_logic
 └── control_flow

Collections
 ├── lists
 ├── tuples
 ├── dictionaries
 └── sets

Control Flow
 ├── conditionals
 ├── loops
 └── comprehensions

Functions
 ├── definition
 ├── parameters
 ├── return_values
 ├── scope
 └── decomposition

Strings
 ├── manipulation
 ├── formatting
 └── parsing

Exceptions
 ├── raising
 ├── handling
 └── custom_exceptions

Modules
 ├── imports
 └── module_structure

Object Oriented Programming
 ├── classes
 ├── instances
 ├── methods
 ├── inheritance
 └── composition

Files / IO
 ├── reading
 ├── writing
 └── paths

Testing
 ├── assertions
 ├── test_structure
 └── edge_cases

Code Structure
 ├── decomposition
 ├── readability
 └── complexity

Это НЕ обязательный финальный список.

Используй структуру Exercism Python track для корректировки карты.

Если Exercism показывает компетенцию, которой здесь нет:

добавь её.

Если несколько пунктов фактически являются одной компетенцией:

объедини.

Не создавай искусственные компетенции только ради количества.


---

7. COMPETENCY IDS

ID должны быть:

стабильными;

lowercase;

machine-readable;

независимыми от названия конкретного источника.


Хорошо:

functions
functions.parameters
collections.dictionary
exceptions.handling
control_flow.loops

Плохо:

exercism_functions
lesson_12
topic_3

Competency ID не должен зависеть от Exercism.


---

8. PREREQUISITES

Для каждой competency определить prerequisites.

Например:

functions.parameters
    requires:
        functions

Но:

НЕ создавать циклические зависимости.

Добавь validator:

competency graph must be acyclic

Тест обязательно должен падать при появлении цикла.


---

9. S-LEVELS

На этом этапе НЕ реализовывать Learning State Machine.

Но competency definitions должны быть совместимы с:

S0
S2
S3
S4
S5
S6

Не реализовывать переходы.

Можно хранить критерии:

understand_criteria:
can_do_criteria:

Но НЕ создавать код:

calculate_competency_state(...)

Это следующая фаза.


---

10. EXERCISM RESEARCH

Перед ingestion исследуй актуальную структуру:

официальный Exercism Python repository;

concepts;

exercises;

practice exercises;

config;

tests;

metadata;

syllabus;

track structure.


Используй официальный repository как primary source.

Не полагайся на случайные mirrors.


---

11. LICENSE GATE

Для Exercism отдельно зафиксируй:

repository;

license;

relevant files/directories;

license evidence;

можно ли использовать;

можно ли модифицировать;

можно ли хранить локальную копию.


Не делай вывод:

> "Exercism = MIT, значит всё внутри автоматически можно использовать."



Проверь конкретные части, которые реально импортируются.

Особенно отдельно проверить:

exercise content;

tests;

metadata;

support files;

runner;

analyzer.


ВАЖНО:

Не импортируй код Exercism test runner/analyzer просто потому, что он существует.

На этом этапе нам нужны упражнения и их данные.

Runner/analyzer — отдельная фаза.


---

12. PROVENANCE

Каждый imported exercise должен иметь provenance.

Например:

source_id:
source_name:
repository:
source_url:
path:
original_id:
license:
license_evidence:
imported_at:
content_hash:
status:

content_hash нужен для отслеживания изменений upstream.


---

13. IMPORT POLICY

Создай строгую политику:

pending
    ↓
license validation
    ↓
approved
    ↓
live corpus

или:

pending
    ↓
rejected

Никогда:

unknown → live

Если лицензия не может быть подтверждена:

status = pending

или:

status = rejected

в зависимости от причины.


---

14. INGESTION PIPELINE

Pipeline должен быть повторяемым.

Примерная модель:

Exercism repository
        ↓
Discovery
        ↓
Parse metadata
        ↓
Parse exercise
        ↓
Parse tests
        ↓
Resolve provenance
        ↓
License gate
        ↓
Competency mapping
        ↓
Difficulty mapping
        ↓
Validation
        ↓
SQLite

Повторный запуск ingestion не должен создавать дубликаты.

Он должен быть:

> idempotent.




---

15. НЕ ХРАНИТЬ ЛИШНЕЕ

Не копируй весь Exercism repository в БД.

Отдели:

Metadata

id
slug
type
source
competency
difficulty
tags

от:

Content

statement
tests
reference_solution

Если legal/provenance model позволяет хранить content локально.

Иначе хранить ссылку.


---

16. REFERENCE SOLUTION

reference_solution — OPTIONAL.

Не считать его обязательным условием импорта.

Если решение:

отсутствует;

имеет другую лицензию;

не предназначено для redistribution;

находится в стороннем repository;


не импортировать его автоматически.

Exercise всё равно может быть:

approved

если условие и тесты легальны.


---

17. TESTS

Определить, какие тесты принадлежат exercise.

Хранить provenance тестов.

Не запускать их на student code.

На этом этапе:

> только ingestion + storage.



Позже Grader будет использовать tests_ref.


---

18. EXERCISE → COMPETENCY MAPPING

Это один из наиболее важных результатов Phase C.

Для каждого exercise определить:

primary competency
secondary skills
difficulty rung

Не маппить механически:

Exercism directory name → competency

если это даёт неправильный результат.

Используй:

concept metadata;

syllabus;

exercise description;

tests;

source structure;

требуемые Python concepts.


Если mapping неоднозначен:

mapping_confidence = low

и пометь для ручной проверки.


---

19. DIFFICULTY RUNG

Использовать:

repetition
analogy
new
unfamiliar_context
combination
independent

Не путать:

source difficulty

с:

pedagogical difficulty rung

Если Exercism имеет собственную difficulty classification:

сохрани её отдельно.

Например:

source_difficulty
pedagogical_rung

Не уничтожай исходную информацию.


---

20. MAPPING CONFIDENCE

Добавь:

mapping_confidence:
    high
    medium
    low

Высокая:

> competency явно указана source metadata.



Средняя:

> определяется из нескольких признаков.



Низкая:

> inferred вручную/эвристически.



Low-confidence mappings НЕ считать окончательными.

Сформируй отдельный report:

exercise_id
current_mapping
confidence
reason


---

21. VALIDATION

Создай validators:

Competency validator

Проверяет:

unique IDs;

required fields;

valid prerequisites;

no cycles;

valid error references;

valid verification exercise references.


Exercise validator

Проверяет:

unique IDs;

valid source;

valid competency;

valid difficulty;

valid type;

valid references.


Provenance validator

Проверяет:

license exists;

license evidence exists;

status valid;

approved exercises have approved source.


Corpus validator

Проверяет:

approved exercise
    → approved source
    → valid competency
    → valid difficulty


---

22. SQLITE

Используй SQLite.

Минимальные таблицы этого этапа:

competencies
competency_prerequisites

exercise_sources
exercises
exercise_competencies

Можно добавить:

exercise_tests

если это действительно необходимо.

НЕ создавать:

submissions
evidence
review_states
learning_events
student_competencies

Они относятся к следующим фазам.

Не создавать таблицы «на будущее» без необходимости.


---

23. SCHEMA DESIGN

Используй:

foreign keys;

unique constraints;

indexes там, где они реально нужны;

CHECK constraints для enum-подобных значений.


SQLite foreign keys должны быть явно включены.

Проверь это тестом.


---

24. CLI

Создай минимальный CLI:

python -m <package> ingest exercism

или эквивалентный интерфейс проекта.

Поддержать:

--source
--dry-run
--force
--report

если они нужны.

Особенно полезен:

--dry-run

который показывает:

сколько найдено;

сколько approved;

сколько rejected;

сколько pending;

сколько low-confidence mappings;

сколько новых;

сколько изменённых;

сколько пропущено.



---

25. REPORTING

После ingestion генерировать отчёт:

Total discovered:
Total parsed:
Approved:
Rejected:
Pending:

Concept exercises:
Practice exercises:

Mapped:
Unmapped:
Low confidence:

Tests available:
Reference solutions available:

Competency coverage:

И отдельную таблицу:

competency
exercise_count
concept_count
practice_count
difficulty_distribution
mapping_confidence

Это должно позволить увидеть реальные пробелы curriculum.


---

26. GAP ANALYSIS

Обязательно определить:

competency with 0 exercises
competency with only 1 exercise
competency with no advanced exercises
competency with only one difficulty rung

Не пытайся автоматически «чинить» пробелы.

Просто сформируй:

> CONTENT GAP REPORT




---

27. TESTING

Написать tests минимум для:

Competency

загрузка;

prerequisites;

cycle detection;

duplicate IDs.


Provenance

approved;

rejected;

pending;

missing license.


Ingestion

parsing;

idempotency;

duplicate prevention;

update detection.


Mapping

valid competency;

invalid competency;

confidence.


Database

foreign keys;

constraints.



---

28. IDEMPOTENCY TEST

Критический тест:

run ingestion
    ↓
N records

run ingestion again
    ↓
N records

Количество записей не должно стать:

2N

Затем изменить upstream fixture:

run ingestion
    ↓
existing record updated

а не создан новый duplicate.


---

29. FIXTURES

НЕ делай все тесты зависимыми от live GitHub.

Создай небольшие локальные fixtures:

tests/fixtures/exercism/

чтобы unit tests работали:

offline;

быстро;

воспроизводимо.


Отдельно может существовать integration test:

tests/integration/

который работает с реальным upstream repository.

Но обычный test suite не должен зависеть от интернета.


---

30. NETWORK

Ingestion может использовать сеть только для:

> получения официального Exercism source.



Но runtime системы после ingestion не должен требовать интернет.

По возможности поддержать:

local source directory

чтобы ingestion можно было запускать полностью offline.


---

31. НЕ ИСПОЛЬЗОВАТЬ LLM

В этом этапе:

LLM calls = 0

Competency mapping должен быть:

deterministic;

metadata-based;

rule-based;

ручные overrides допустимы.


Если невозможно надёжно автоматически определить mapping:

> сохранить low confidence + manual override mechanism.



Не генерировать псевдоуверенный результат.


---

32. MANUAL OVERRIDES

Предусмотреть возможность вручную исправить mapping.

Например:

exercise_id:
  competency_id:
  skill_tags:
  difficulty_rung:
  confidence: high
  override: true

Manual override должен иметь приоритет над автоматической эвристикой.

Но:

> не превращай это в сложную CMS.



На этом этапе достаточно простой декларативной конфигурации.


---

33. ПРЕДЛАГАЕМАЯ СТРУКТУРА

Не копируй её слепо, адаптируй к существующему repository:

src/
  ...
  curriculum/
    competencies/
    exercises/
    provenance/
    mapping/
    ingestion/
    validation/

data/
  curriculum/
  corpus/

configs/
  competency_map.yaml
  exercise_overrides.yaml

tests/
  unit/
  integration/
  fixtures/

Если repository уже имеет другую архитектуру:

> следуй существующей архитектуре.




---

34. ДОКУМЕНТАЦИЯ

Создай короткий документ:

docs/curriculum_v0.1.md

В нём:

competency map;

mapping principles;

difficulty principles;

provenance rules;

ingestion workflow;

known limitations.


Также:

docs/exercism_ingestion.md

с инструкцией:

как скачать/получить source
как запустить ingestion
как сделать dry-run
как посмотреть report
как добавить manual override


---

35. НЕ ДЕЛАТЬ ЭТО

Категорически НЕ делать в рамках задачи:

❌ Docker
❌ nsjail
❌ subprocess student execution
❌ pytest grader
❌ Pylint execution
❌ Radon execution
❌ Bandit execution
❌ AST detector
❌ FSRS
❌ evidence engine
❌ learning state engine
❌ activity selector
❌ FastAPI
❌ frontend
❌ LLM
❌ freeCodeCamp ingestion
❌ Google Python Class ingestion
❌ MIT ingestion

Если увидишь архитектурную необходимость этих компонентов:

> только документируй interface/dependency, не реализуй.




---

36. DEFINITION OF DONE

Phase B + C считается завершённой только если:

Competency Map

[ ***REMOVED*** competency map v0.1 создан;

[ ***REMOVED*** IDs стабильны;

[ ***REMOVED*** prerequisites валидируются;

[ ***REMOVED*** cycles обнаруживаются;

[ ***REMOVED*** descriptions присутствуют;

[ ***REMOVED*** understand/can-do criteria присутствуют;

[ ***REMOVED*** Exercism concepts покрываются map'ом.


Provenance

[ ***REMOVED*** source registry создан;

[ ***REMOVED*** license evidence хранится;

[ ***REMOVED*** approved/pending/rejected реализованы;

[ ***REMOVED*** unapproved content не попадает в live corpus.


Exercism

[ ***REMOVED*** official source исследован;

[ ***REMOVED*** ingestion работает;

[ ***REMOVED*** concept exercises импортируются;

[ ***REMOVED*** practice exercises импортируются;

[ ***REMOVED*** metadata сохраняется;

[ ***REMOVED*** tests references сохраняются;

[ ***REMOVED*** reference solution импортируется только если разрешено;

[ ***REMOVED*** provenance сохраняется.


Mapping

[ ***REMOVED*** exercise → competency;

[ ***REMOVED*** exercise → skill tags;

[ ***REMOVED*** exercise → difficulty rung;

[ ***REMOVED*** confidence;

[ ***REMOVED*** manual overrides.


Database

[ ***REMOVED*** SQLite;

[ ***REMOVED*** foreign keys;

[ ***REMOVED*** constraints;

[ ***REMOVED*** idempotent ingestion.


Reports

[ ***REMOVED*** ingestion report;

[ ***REMOVED*** competency coverage report;

[ ***REMOVED*** content gap report;

[ ***REMOVED*** low-confidence mapping report.


Tests

[ ***REMOVED*** unit tests;

[ ***REMOVED*** ingestion fixtures;

[ ***REMOVED*** idempotency test;

[ ***REMOVED*** validation tests;

[ ***REMOVED*** database constraint tests.



---

37. ACCEPTANCE CRITERIA

После реализации я должен иметь возможность выполнить:

pytest

и получить:

ALL TESTS PASS

Затем:

python -m <package> ingest exercism --dry-run

и получить понятный отчёт.

Затем:

python -m <package> ingest exercism

и получить SQLite corpus.

Повторный запуск:

python -m <package> ingest exercism

не должен создавать duplicates.

Также должен существовать способ получить:

competency coverage
content gaps
low confidence mappings
license status


---

38. GIT / CHANGES

Перед изменениями:

проверь git status

Не удаляй существующие пользовательские изменения.

Не делай destructive migration.

Не переписывай существующую архитектуру проекта без необходимости.

Изменения должны быть минимальными и локальными.

После реализации покажи:

git diff --stat
git status

и кратко объясни каждую группу изменений.


---

39. ФИНАЛЬНЫЙ ОТЧЁТ

После завершения НЕ просто скажи:

> «готово».



Предоставь:

A. Что реализовано

Список файлов/модулей.

B. Competency Map

Количество competencies + дерево.

C. Exercism Corpus

Статистика:

discovered
parsed
approved
pending
rejected

D. Coverage

Какие competencies покрыты и насколько.

E. Gaps

Что пока отсутствует.

F. License

Какие материалы реально разрешены.

G. Tests

Количество тестов + результат.

H. Known limitations

Честно перечислить.

I. Следующая фаза

Только перечислить зависимости для следующего этапа.

НЕ начинать её реализацию.


---

40. ФИНАЛЬНЫЙ GATE

После выполнения остановись.

Не переходи к:

Phase D — Grading
Phase E — Sandbox
Phase F — Error Detector
Phase G — Learning Engine

даже если они кажутся простыми.

Финальный статус:

PHASE B+C COMPLETE
WAITING FOR ARCHITECTURE REVIEW

Главный принцип:

> Сейчас мы строим не «приложение для обучения Python», а качественный, воспроизводимый и юридически чистый фундамент контента и компетенций, на который впоследствии будут опираться Grader, Mentor, Curator, FSRS и LLM-слой.