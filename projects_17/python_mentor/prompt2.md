Да. И я бы сделал не один огромный промт на всю реализацию, а серию промтов-гейтов. Тогда агент после каждой фазы не сможет «уехать» в соседнюю архитектуру.

У нас уже есть Phase B+C — Competency Map + Exercism Ingestion. Ниже — следующие этапы в том порядке, в котором я бы реально их давал агенту.


---

PHASE D — Grading Contract + Autograder

# IMPLEMENTATION TASK
# Deterministic Core — Phase D
# Grading Contract + Python Autograder v0.1

РОЛЬ

Ты — Senior Python Engineer, специализация:
automated assessment / testing infrastructure.

SOURCE OF TRUTH:

    Deterministic Core — Architecture Blueprint v0.1

Предыдущая фаза:

    Phase B+C
    Competency Map + Exercism Ingestion

Используй существующий corpus.
Не меняй его модель без необходимости.

---

# ЦЕЛЬ

Реализовать deterministic grading pipeline:

    Student Submission
          ↓
    Exercise Tests
          ↓
    Test Result
          ↓
    Normalized Grading Result
          ↓
    Evidence Candidate

На этом этапе НЕ реализовывать:

- sandbox hardening;
- AST error detector;
- FSRS;
- Learning State Engine;
- Activity Selector;
- LLM;
- FastAPI;
- frontend.

---

# 1. GRADING CONTRACT

Создай стабильный машинный контракт результата.

Минимальные категории:

```yaml
grading_result:
  submission_id:
  exercise_id:

  correctness:
    status:
      passed
      failed
      error
      timeout
    tests_total:
    tests_passed:
    tests_failed:

  diagnostics:
    ...

  patterns:
    ...

  evidence_candidates:
    ...

Не копируй этот пример буквально.

Спроектируй нормальный immutable result contract.

Критическое правило:

STATIC METRICS НЕ ДОЛЖНЫ АВТОМАТИЧЕСКИ СТАНОВИТЬСЯ COMPETENCY EVIDENCE.


---

2. PYTEST

Использовать pytest как основной механизм проверки correctness.

Exercise уже содержит tests_ref.

Не создавать новый язык тестов.

Runner должен:

1. получить submission;


2. получить exercise;


3. собрать временное execution workspace;


4. положить student code;


5. подключить exercise tests;


6. запустить pytest;


7. собрать результат;


8. нормализовать результат.



На этом этапе execution может использовать существующий MVP execution boundary, но НЕ проектируй полноценную hardened sandbox.

Если для запуска нужен временный subprocess:

зафиксируй dependency для Phase E.


---

3. РЕЗУЛЬТАТ ТЕСТОВ

Различать:

PASS
FAIL
ERROR
TIMEOUT
INFRASTRUCTURE_ERROR

Не смешивать:

> student code failed



и:

> grader infrastructure failed.



Например:

student_failure
grader_failure

должны быть разными состояниями.


---

4. PARTIAL RESULTS

Если часть тестов прошла:

не превращать результат просто в:

false

Сохранять:

tests_total
tests_passed
tests_failed
tests_error

Но correctness score не должен автоматически использоваться как competency score.


---

5. SUBMISSION IDENTITY

Каждый submission должен иметь:

submission_id
exercise_id
student_code_hash
created_at

Одинаковый код должен иметь определяемую идентичность.


---

6. TEST ISOLATION

Даже на MVP:

отдельный temporary directory;

timeout;

ограничение размера output;

очистка временных файлов;

отсутствие доступа к application database.


НЕ выполнять student code внутри основного Python process.


---

7. OUTPUT NORMALIZATION

Разные pytest/internal errors привести к стабильному формату.

Например:

AssertionError
SyntaxError
ImportError
Timeout
RuntimeError
InfrastructureError

Но не привязывать public contract к строкам pytest.


---

8. EVIDENCE CANDIDATE

Grader может вернуть:

evidence_candidate:
  type: exercise_result
  competency_id:
  strength:
  metadata:

Но НЕ записывать evidence в Learning Engine.

На этом этапе:

> Grader produces evidence candidates.



Evidence Engine будет отдельной фазой.


---

9. TESTING

Обязательно:

passing submission;

failing submission;

syntax error;

import error;

timeout;

multiple failed tests;

infrastructure failure;

malformed exercise;

duplicate submission.


Все тесты должны использовать fixtures.


---

10. DEFINITION OF DONE

pytest runner работает;

grading contract стабилен;

результаты нормализуются;

infrastructure errors отделены от student errors;

tests pass;

нет LLM;

нет FSRS;

нет Learning State Engine;

нет production sandbox.


Финальный статус:

PHASE D COMPLETE
WAITING FOR REVIEW

---

# PHASE E — Sandbox / Execution Runtime

Вот эту фазу я бы **обязательно отделил от Grader**.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase E
# Execution Runtime + Sandbox Abstraction v0.1

SOURCE OF TRUTH:

    Deterministic Core — Architecture Blueprint v0.1

ЦЕЛЬ:

Создать execution abstraction, позволяющую Grader запускать student code
через единый интерфейс.

Ключевой контракт:

    Job
      ↓
    Execution Worker
      ↓
    Sandbox
      ↓
    Execution Result

---

# 1. SECURITY CONTEXT

Текущий environment:

- один пользователь;
- собственный код;
- локальный Termux;
- нерутованный Android;
- localhost;
- не public service;
- не multi-tenant.

Поэтому текущая реализация:

    MVP-tier

НЕ является production security boundary.

Явно сохранить:

```python
SANDBOX_TIER = "mvp_untrusted_single_user"

Никаких обещаний:

> "sandbox безопасен для arbitrary public users."




---

2. ОБЯЗАТЕЛЬНО ИССЛЕДОВАТЬ ACTUAL TERMUX

Перед реализацией проверить:

unshare --user echo ok

и доступные механизмы:

RLIMIT;

process limits;

timeout;

user switching;

namespaces;

seccomp;

filesystem isolation.


Не предполагать наличие root/unprivileged namespaces.


---

3. INTERFACE

Создать абстракцию:

ExecutionJob
ExecutionPolicy
ExecutionResult
ExecutionBackend

Примерно:

execute(job, policy) -> ExecutionResult

Backend должен быть заменяемым.


---

4. MVP BACKEND

Реализовать:

subprocess backend

с:

timeout;

RLIMIT_CPU;

RLIMIT_AS;

output limit;

temporary filesystem;

cleanup;

non-root user если реально доступен;

environment sanitization.


Не обещать OS-level network isolation, если Termux этого не предоставляет.


---

5. NETWORK

В MVP:

> отсутствие сетевого доступа не считать гарантированным, если оно не обеспечено OS-level механизмом.



Зафиксировать это как security limitation.

НЕ писать:

network_isolation = true

если реально используется только отсутствие сетевых API.


---

6. HARDENED BACKEND

НЕ реализовывать nsjail/Docker сейчас.

Создать только interface:

SandboxBackend
 ├── TermuxSubprocessBackend
 └── HardenedBackend (future)

Future backend должен иметь тот же контракт.


---

7. SECURITY TESTS

Проверить:

timeout;

CPU exhaustion;

memory exhaustion;

huge stdout;

subprocess tree;

temporary file cleanup;

environment leakage;

application DB access;

working directory isolation.


Не пытаться доказать полноценную sandbox security.


---

8. DEFINITION OF DONE

execution abstraction;

Termux backend;

limits;

cleanup;

security tests;

explicit MVP tier;

documentation limitations.


НЕ реализовывать:

Docker;

nsjail;

public execution;

multi-user isolation.


Финальный статус:

PHASE E COMPLETE
WAITING FOR SECURITY REVIEW

---

# PHASE F — AST Error Detector + Static Analysis

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase F
# Static Analysis + AST Error Pattern Detector v0.1

SOURCE OF TRUTH:

    Architecture Blueprint v0.1

ЦЕЛЬ:

Добавить диагностический слой:

    Student Code
        ↓
    AST Rules
    Pylint
    Radon
    Flake8
    Bandit
        ↓
    Normalized Diagnostics
        ↓
    Error Patterns
        ↓
    Hint Candidate

---

# 1. PRINCIPLE

Analyzers are sensors.

Они НЕ определяют:

> "насколько хорош ученик."

Они предоставляют evidence/diagnostics.

---

# 2. AST ENGINE

Использовать стандартный:

    Python ast

Создать registry:

```text
ASTRule
RuleContext
PatternMatch

Каждое правило:

pattern_id
description
severity
competency_id
location
message


---

3. FIRST RULES

Минимально реализовать:

mutable default argument;

bare except;

excessive nesting;

suspicious mutable state;

obvious shadowing;

unreachable code;

oversized function.


Не реализовывать сложные semantic анализаторы без необходимости.


---

4. FALSE POSITIVES

Каждый detector должен иметь tests:

positive case
negative case
edge case

Не включать правило только потому, что оно красиво выглядит.


---

5. PYLINT

Подключить Pylint через adapter.

Не позволять Pylint contract напрямую протекать во внутреннюю доменную модель.

Создать:

PylintAdapter


---

6. RADON

Использовать для:

cyclomatic complexity;

LOC;

Halstead;

maintainability.


Maintainability Index:

diagnostic_only = true

Он НИКОГДА не создаёт evidence напрямую.


---

7. FLAKE8

Подключить только если он даёт уникальную ценность.

Если результат полностью дублируется другими инструментами:

зафиксировать это и не тащить лишнюю зависимость.


---

8. BANDIT

Bandit включается только для:

security_eligible = true

На ранних уровнях результаты могут храниться, но не показываться ученику.


---

9. NORMALIZATION

Все анализаторы приводятся к единому формату:

diagnostic:
  source:
  rule_id:
  pattern_id:
  severity:
  file:
  line:
  column:
  message:
  diagnostic_only:


---

10. ERROR PATTERN

Связь:

detector
    ↓
error_pattern
    ↓
competency
    ↓
hint_bank

НЕ создавать evidence автоматически для каждого diagnostic.


---

11. TESTING

Для каждого detector:

positive;

negative;

false-positive edge cases.


Для adapters:

parser;

malformed output;

tool unavailable;

tool failure.



---

12. DEFINITION OF DONE

AST registry;

initial rules;

analyzer adapters;

normalized diagnostics;

error pattern mapping;

tests;

no LLM;

no FSRS;

no Learning State Engine.


Финальный статус:

PHASE F COMPLETE
WAITING FOR REVIEW

---

# PHASE G — Hint Engine / Deterministic Mentor Layer

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase G
# Hint Bank + Hint Escalation Engine v0.1

ЦЕЛЬ:

Реализовать детерминированную часть Менторской роли.

Architecture:

    Error Pattern
         ↓
    Hint Bank
         ↓
    Current Hint Level
         ↓
    Next Hint

---

# 1. HINT LEVELS

Использовать:

```text
L0
L1
L2
L3
L4
L5
L6

L0:

> не показывать подсказку.



Каждый следующий уровень раскрывает больше информации.


---

2. ESCALATION

Функция:

next_hint_level(current_level, stuck_signal)

Правила:

старт L0;

повышение максимум на один уровень;

нельзя перескочить;

L4+ требует permission;

project/client mode ограничивает максимум L3;

новое упражнение начинает с L0.



---

3. HINT BANK

Структура:

hint_bank
pattern_id
level
text
requires_permission
project_mode_cap


---

4. GENERIC HINTS

Поддержать hints без pattern_id:

pattern_id = null

Например:

"Проверь входные данные."

"Попробуй найти место, где состояние меняется."

"Проверь граничный случай."



---

5. НЕ ГЕНЕРИРОВАТЬ HINTS LLM

Все hints этого слоя:

> заранее написанные deterministic content.



LLM появится позже как отдельный optional layer.


---

6. PERMISSION

L4+ не должен автоматически показываться.

Должен существовать явный signal:

student_requested_hint = true

или соответствующий policy.


---

7. TESTS

Проверить:

escalation;

no jumping;

reset;

permission;

project cap;

missing hint;

generic hint fallback.



---

8. DEFINITION OF DONE

Hint Engine работает независимо от LLM.

Финальный статус:

PHASE G COMPLETE
WAITING FOR REVIEW

---

# PHASE H — Evidence Engine + Competency State

Вот здесь начинается **ядро всей методики**.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase H
# Evidence Engine + Competency State Machine v0.1

SOURCE OF TRUTH:

    Architecture Blueprint v0.1
    Competency Map v0.1

ЦЕЛЬ:

Реализовать:

    Evidence Log
        ↓
    Deterministic Fold
        ↓
    Competency State
        ↓
    Transition Rules

---

# 1. EVENT SOURCING

Evidence является append-only log.

Не хранить competency state как единственный source of truth.

State:

    pure function(events)

---

# 2. EVENTS

Поддержать:

```text
submission
hint_used
error_detected
project_usage
review_score

и необходимые system events.

Каждое событие:

id
timestamp
competency_id
exercise_id
event_type
payload


---

3. STATE

S0
S2
S3
S4
S5
S6

S6 НЕ вычисляется.

Он:

pending_llm_review


---

4. TRANSITIONS

S0 → S2

Условия:

explain content completed;

verification question correct.


S2 → S3

Первое решённое exercise.

S3 → S4

2 упражнения подряд:

hint_level <= L1

S4 → S5

project_usage

без явного напоминания темы.

S5 → S6

НЕ реализовывать.

Возвращать:

pending_llm_review


---

5. NO GLOBAL SCORE

State vector:

functions = S4
loops = S5
dicts = S3
exceptions = S2


---

6. REBUILD

Должна существовать возможность:

events
   ↓
rebuild()
   ↓
same state

Удаление cached state не должно уничтожать знания.


---

7. IDEMPOTENCY

Повторная обработка одного event:

> не должна дважды повысить competency.




---

8. EXPLAINABILITY

Для state transition хранить reason:

transition:
S3 → S4

reason:
2 consecutive exercises passed with hint_level <= L1


---

9. ESCALATION

Если правило не может принять решение:

escalate_to_llm_or_human

НЕ придумывать deterministic решение.


---

10. TESTS

Обязательно:

каждый transition;

invalid transition;

duplicate event;

rebuild;

explainability;

prerequisites;

S6 escalation.


Финальный статус:

PHASE H COMPLETE
WAITING FOR REVIEW

---

# PHASE I — FSRS Integration

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase I
# FSRS Competency Review Scheduler v0.1

ЦЕЛЬ:

Интегрировать готовый FSRS.

НЕ писать собственную spaced repetition algorithm.

---

# 1. UNIT

Единица планирования:

    competency

НЕ:

    flashcard
    exercise

---

# 2. SEPARATION

FSRS state:

    scheduling state

Competency state:

    learning state

Они НЕ являются одним объектом.

---

# 3. REVIEW EVENT

После значимого evidence:

```text
evidence
    ↓
rating mapping
    ↓
FSRS
    ↓
next_review


---

4. RATING MAPPING

До реализации создать таблицу:

evidence
hint usage
correctness
repeated success
failure

→

Again
Hard
Good
Easy

Не угадывать mapping.

Сначала формализовать его.


---

5. IMPORTANT

FSRS НЕ меняет competency state напрямую.

Он только отвечает:

> когда компетенцию стоит повторно проверить.




---

6. PRIORITY

Activity selector пока не реализовывать.

Создать API:

get_due_competencies()

но не решать:

> что делать следующим.



Это Phase J.


---

7. TESTS

rating mapping;

review;

due;

overdue;

persistence;

rebuild;

separate competencies.


Финальный статус:

PHASE I COMPLETE
WAITING FOR REVIEW

---

# PHASE J — Deterministic Activity Selector / Curator

Это уже замена существенной части Куратора.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase J
# Activity Eligibility + Selection Engine v0.1

ЦЕЛЬ:

На основе:

    Competency State
    Prerequisites
    Exercise Corpus
    Evidence
    FSRS Due State

определять:

> какие активности сейчас допустимы.

---

# 1. ELIGIBILITY ≠ SELECTION

Сначала:

```text
eligible activities

Потом:

selection

Не смешивать.


---

2. ELIGIBILITY

Exercise eligible если:

competency prerequisite выполнены;

exercise approved;

exercise не заблокирован;

difficulty соответствует состоянию;

нет curriculum violation.



---

3. CANDIDATES

Результат:

candidate:
  activity_id:
  competency_id:
  reason:
  difficulty:
  due:
  priority:


---

4. PRIORITY

Создать явную policy.

Например:

1. blocked prerequisite → reject
2. critical remediation → high
3. overdue review → high
4. new required competency
5. reinforcement
6. optional practice

Но НЕ копировать этот порядок автоматически.

Исследуй и формализуй policy.


---

5. DETERMINISM

Одинаковый state:

> одинаковый candidate ordering.



Не использовать random без seed.


---

6. EXPLAINABILITY

Для каждой рекомендации:

why eligible
why selected
why not other candidate


---

7. HINT DEPENDENCY

Если ученик систематически использует L4+:

это пока не означает автоматическую деградацию competency.

Только evidence signal.


---

8. TESTS

prerequisites;

due;

remediation;

difficulty;

blocked exercises;

deterministic ordering;

empty candidate set;

explainability.


Финальный статус:

PHASE J COMPLETE
WAITING FOR REVIEW

---

# PHASE K — Project / “Заказчик”

Это уже отдельная интересная часть твоей методики.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase K
# Project Specification / Client Simulation v0.1

ЦЕЛЬ:

Создать deterministic project engine,
который позволяет ученику получать проект через заранее подготовленное
дерево требований.

НЕ использовать LLM для генерации requirements.

---

# 1. PROJECT TEMPLATE

```yaml
project:
  id:
  title:
  description:
  difficulty:
  competencies:
  requirements:
  constraints:
  acceptance_criteria:


---

2. QUESTION TREE

Question
 ├── answer
 ├── next_question
 └── condition

Ответы ученика приводят к заранее определённым требованиям.


---

3. RESULT

Student Answers
      ↓
Project Specification
      ↓
Requirements
      ↓
Acceptance Criteria


---

4. НЕ ГЕНЕРИРОВАТЬ

Никаких:

> "AI придумал тебе приложение."



Каждый project template заранее создан и versioned.


---

5. CLIENT MODE

В Client Mode:

hints ограничены L3;

студент не получает готовое решение;

requirements не объясняют implementation.



---

6. COMPETENCY LINK

Каждый project содержит:

required_competencies
optional_competencies

После выполнения project создаёт:

project_usage evidence


---

7. TESTS

question branching;

invalid answers;

requirements;

acceptance criteria;

competency mapping;

hint cap.


Финальный статус:

PHASE K COMPLETE
WAITING FOR REVIEW

---

# PHASE L — FastAPI API

И только теперь API.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase L
# FastAPI Application Layer v0.1

ЦЕЛЬ:

Создать тонкий API layer над уже реализованным deterministic core.

ВАЖНО:

API НЕ СОДЕРЖИТ БИЗНЕС-ЛОГИКУ.

```text
HTTP
 ↓
Application Service
 ↓
Domain Engine
 ↓
Repository


---

ENDPOINTS

Learning

GET /next-activity
GET /competency-map
GET /profile
GET /competencies/{id***REMOVED***

Exercises

GET /exercises/{id***REMOVED***
GET /exercises

Submission

POST /submit
GET /result/{job_id***REMOVED***

Hints

POST /hint

Reviews

GET /reviews/due

Projects

GET /projects
POST /projects/{id***REMOVED***/start
POST /projects/{id***REMOVED***/answer


---

RULE

Не помещать в endpoint:

if competency...

или:

select_next_exercise(...)

Такая логика должна находиться в domain/application service.


---

TESTING

API contract tests;

validation;

error responses;

deterministic results;

no business logic duplication.


Финальный статус:

PHASE L COMPLETE
WAITING FOR REVIEW

---

# PHASE M — Frontend

И только после API.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase M
# Minimal Learning UI v0.1

ЦЕЛЬ:

Создать простой HTML/CSS/JS интерфейс.

НЕ использовать React/Vue/etc.

---

# ЭКРАНЫ

1. Dashboard
2. Current competency map
3. Current exercise
4. Code editor
5. Submission result
6. Hint progression
7. Review queue
8. Project mode

---

# PRINCIPLE

UI не содержит learning logic.

```text
UI
 ↓
API
 ↓
Deterministic Core


---

EXERCISE SCREEN

Показывать:

condition;

competency;

difficulty;

code editor;

run/check;

hints.


Не показывать внутренние diagnostic metrics, если curriculum policy запрещает их на данном уровне.


---

RESULT

Показывать:

tests passed
tests failed
useful feedback
next hint

Не превращать интерфейс в IDE.


---

STYLE

Минималистично.

Без:

кислотных цветов;

перегруженных dashboard;

игровых наград ради самих наград.


Финальный статус:

PHASE M COMPLETE
WAITING FOR REVIEW

---

# И ЕЩЁ ОДНА ФАЗА, КОТОРУЮ Я БЫ ОБЯЗАТЕЛЬНО ДОБАВИЛ

## PHASE N — End-to-End Educational Validation

Вот этого в исходном плане не хватало. И она **очень важна**, потому что технически корректная система ещё не означает, что методика работает.

```text
# IMPLEMENTATION TASK
# Deterministic Core — Phase N
# End-to-End Educational Validation v0.1

ЦЕЛЬ:

Проверить всю цепочку как единую deterministic learning system.

НЕ добавлять новые функции.

Только validation.

---

# SCENARIO 1 — BEGINNER

Создать synthetic learner:

```text
S0

Пройти:

explanation
→ verification
→ S2
→ exercise
→ S3
→ exercise
→ S4
→ project
→ S5

Проверить каждый переход.


---

SCENARIO 2 — STRUGGLING LEARNER

Ученик:

ошибается;

использует hints;

повторяет ошибку;

получает L1 → L2 → L3.


Проверить:

hint escalation;

error detection;

evidence;

state.



---

SCENARIO 3 — STRONG LEARNER

Ученик:

решает без hints;

проходит новые contexts;

быстро достигает S4/S5.


Проверить, что система:

> не заставляет его искусственно проходить лишние beginner exercises.




---

SCENARIO 4 — FAILED INFRASTRUCTURE

Sandbox/grader падает.

Проверить:

> competency НЕ изменяется.




---

SCENARIO 5 — DUPLICATE EVENT

Один event отправлен дважды.

Проверить:

> state не изменяется дважды.




---

SCENARIO 6 — REBUILD

Удалить materialized state.

Пересобрать из event log.

Проверить:

> идентичный результат.




---

SCENARIO 7 — FSRS

Проверить:

evidence
→ review rating
→ due state
→ candidate


---

SCENARIO 8 — PROJECT

Project usage:

без reminder

→ соответствующее evidence.


---

SCENARIO 9 — LLM BOUNDARY

Проверить состояния:

S5
    ↓
S6
    ↓
pending_llm_review

Система НЕ должна самостоятельно выдавать S6.


---

FINAL ACCEPTANCE

Проверить:

same input
    ↓
same state
same candidates
same grading
same explanations

То есть:

> deterministic ядро действительно детерминировано.



Финальный статус:

PHASE N COMPLETE
DETERMINISTIC CORE VALIDATED

---

## В итоге получается нормальная дорожка

```text
B+C
│
├── Competency Map
└── Exercism Corpus
        ↓
D
└── Grader
        ↓
E
└── Execution / Sandbox
        ↓
F
└── AST + Static Analysis
        ↓
G
└── Hint Engine
        ↓
H
└── Evidence + Competency State
        ↓
I
└── FSRS
        ↓
J
└── Deterministic Curator
        ↓
K
└── Project / Client
        ↓
L
└── FastAPI
        ↓
M
└── UI
        ↓
N
└── E2E Validation

И самое главное — LLM вообще отсутствует в этом pipeline:

┌───────────────────────┐
                    │   DETERMINISTIC CORE  │
                    │                       │
Exercises ─────────►│ Competencies          │
                    │ Grader                │
Student Code ──────►│ Sandbox               │
                    │ AST                   │
                    │ Static Analysis       │
                    │ Hints                 │
                    │ Evidence              │
                    │ FSRS                  │
                    │ State Machine         │
                    │ Activity Selector     │
                    │ Projects              │
                    └───────────┬───────────┘
                                │
                         clean API boundary
                                │
                    ┌───────────▼───────────┐
                    │      LLM LAYER        │
                    │                       │
                    │ Tutor                 │
                    │ Mentor                │
                    │ Explanations          │
                    │ Socratic dialogue     │
                    │ Thinking evaluation   │
                    │ Adaptation             │
                    └───────────────────────┘

И это, на мой взгляд, гораздо сильнее первоначальной идеи «сделаем AI-тьютора». Получается настоящий учебный runtime: LLM можно менять хоть каждый день, а состояние обучения, corpus, grading, competency progression и правила остаются стабильным.