# DETERMINISTIC PYTHON LEARNING PLATFORM
# Master Architecture & Implementation Prompt v1.0

РОЛЬ

Ты — Senior Learning Systems Architect + Senior Python Engineer.

Твоя задача — спроектировать и затем поэтапно реализовать
ДЕТЕРМИНИРОВАННУЮ ПЛАТФОРМУ ОБУЧЕНИЯ PYTHON.

Это НЕ проект "AI Tutor".

Это НЕ проект "AI Agent".

Это НЕ проект "чат с преподавателем".

Основной продукт — автономная deterministic learning system,
которая способна самостоятельно вести ученика по учебной программе
на основании формализованных правил, состояния компетенций,
evidence, результатов практики и заранее определённого curriculum.

LLM в базовый контур НЕ входит.

Если впоследствии понадобится LLM, она должна подключаться как
внешний необязательный слой и НЕ иметь права нарушать
детерминированность core learning engine.

============================================================
# 0. ГЛАВНЫЙ ПРИНЦИП
============================================================

Одинаковое состояние системы + одинаковый вход
→ одинаковый результат.

То есть:

same_state
+ same_events
+ same_curriculum
+ same_exercise_bank
+ same_configuration
+ same_rules
=
same_decision

Система не должна принимать образовательные решения
на основании генеративного или скрытого суждения.

Запрещено:

- LLM API;
- генеративный выбор следующего упражнения;
- AI grading;
- AI-generated hints;
- AI-generated curriculum;
- AI-generated competency transitions;
- скрытое состояние модели;
- случайный выбор без deterministic seed;
- эвристики, результат которых невозможно воспроизвести;
- "AI решил, что ученик уже понял тему".

Если правило недостаточно формализовано,
система должна вернуть:

    UNRESOLVED / REQUIRES_HUMAN_RULE

а НЕ придумывать решение.

============================================================
# 1. ЧТО МЫ СТРОИМ
============================================================

Платформа должна реализовывать полный deterministic learning loop:

    Curriculum
        ↓
    Competency Map
        ↓
    Learner State
        ↓
    Eligible Activities
        ↓
    Activity Selection
        ↓
    Exercise / Project
        ↓
    Student Submission
        ↓
    Deterministic Grading
        ↓
    Diagnostics
        ↓
    Evidence
        ↓
    Competency State Update
        ↓
    Review Scheduling
        ↓
    Next Activity

И снова:

    State → Decision → Activity → Evidence → State

Это конечная машина обучения,
а не чат-бот.

============================================================
# 2. АРХИТЕКТУРНЫЙ ИНВАРИАНТ
============================================================

Все образовательные решения должны проходить через
явные deterministic functions / rules.

Например:

    get_eligible_activities(state, curriculum)

    select_next_activity(candidates, policy)

    calculate_competency_state(evidence)

    determine_hint_level(context)

    calculate_review_state(evidence)

    evaluate_project_usage(event)

Нельзя помещать образовательную логику:

- в FastAPI endpoints;
- в frontend;
- в database triggers;
- в random utility;
- в текстовые prompt'ы;
- в неявные side effects.

============================================================
# 3. РОЛИ ПЛАТФОРМЫ
============================================================

Первоначально методика предполагает роли:

    Куратор
    Тьютор
    Ментор
    Практикум
    Заказчик
    Ревьюер

Но НЕ считать их автоматически LLM-ролями.

Каждую роль необходимо разложить на:

    responsibility
    input
    deterministic rules
    output
    unresolved decisions

Например:

------------------------------------------------------------
КУРАТОР
------------------------------------------------------------

Ответственность:

- следить за прогрессом;
- определять доступные следующие активности;
- соблюдать prerequisites;
- учитывать remediation;
- учитывать review;
- не давать перескочить через необходимые этапы.

Реализация:

    Curriculum Engine
    + Competency State Machine
    + Activity Selector

------------------------------------------------------------
ТЬЮТОР
------------------------------------------------------------

Ответственность:

- определять последовательность изучения;
- выдавать теоретический материал;
- проверять prerequisite knowledge;
- связывать теорию с практикой.

Не создавать динамический AI Tutor.

Материал должен находиться в versioned curriculum/content bank.

------------------------------------------------------------
МЕНТОР
------------------------------------------------------------

Ответственность:

- обнаруживать типовые ошибки;
- выдавать подсказки;
- постепенно увеличивать уровень помощи;
- не давать решение слишком рано.

Реализация:

    Error Pattern Detector
    + Hint Bank
    + Hint Escalation Rules

------------------------------------------------------------
ПРАКТИКУМ
------------------------------------------------------------

Ответственность:

- выдавать упражнения;
- контролировать сложность;
- обеспечивать progression:
  
  repetition
  → analogy
  → new problem
  → unfamiliar context
  → combination
  → independent

Реализация:

    Exercise Bank
    + Difficulty Model
    + Activity Selector

------------------------------------------------------------
ЗАКАЗЧИК
------------------------------------------------------------

Ответственность:

создавать realistic project requirements.

Реализация:

    versioned project templates
    + deterministic question trees
    + acceptance criteria

------------------------------------------------------------
РЕВЬЮЕР
------------------------------------------------------------

Ответственность:

- correctness;
- Python quality;
- engineering quality;
- типовые ошибки;
- статические признаки.

Реализация:

    pytest
    + AST
    + static analyzers

============================================================
# 4. НЕДОПУСТИМАЯ ПОДМЕНА
============================================================

Не подменяй:

    competency mastery

метриками:

    tests passed
    pylint score
    complexity
    maintainability index

Не подменяй:

    understanding

результатом:

    correct output

Не подменяй:

    ability to transfer knowledge

результатом:

    solved familiar exercise

Не подменяй:

    thinking

статическим анализом.

Если для утверждения требуется человеческое или LLM-суждение,
оно должно быть явно обозначено:

    NOT DETERMINISTICALLY VERIFIABLE

============================================================
# 5. COMPETENCY MODEL
============================================================

Каждая компетенция должна иметь:

    id
    name
    description
    prerequisites
    understand_criteria
    can_do_criteria
    typical_errors
    verification_exercise
    project_marker

Пример:

    functions
    dictionaries
    loops
    exceptions
    files
    testing
    OOP
    decomposition
    debugging
    code quality
    etc.

Но НЕ ограничивайся этим списком.

Сначала исследуй методику и curriculum,
затем предложи canonical competency map.

============================================================
# 6. COMPETENCY STATES
============================================================

Использовать состояния:

    S0
    S2
    S3
    S4
    S5
    S6

Переходы должны быть формальными.

Пример:

S0 → S2

если:

    theory_completed
    AND verification_correct

S2 → S3

если:

    first_valid_exercise_completed

S3 → S4

если:

    two_consecutive_exercises
    AND hint_level <= L1

S4 → S5

если:

    project_usage
    AND no_explicit_topic_reminder

S5 → S6

НЕ вычислять автоматически.

Результат:

    pending_llm_review
    OR human_review_required

Если текущая методика требует других условий,
НЕ придумывай их.
Зафиксируй discrepancy и предложи вариант
для последующего подтверждения.

============================================================
# 7. EVIDENCE-FIRST ARCHITECTURE
============================================================

История обучения должна быть event/evidence based.

Минимально:

    submission
    hint_used
    error_detected
    project_usage
    review_score
    theory_completed
    verification_answer

Competency State должен быть производным состоянием.

То есть:

    Evidence Log
        ↓
    Deterministic Fold
        ↓
    Competency State

Нельзя полагаться только на mutable:

    student_competency.level

Если materialized state существует,
он должен быть восстановим из event log.

============================================================
# 8. EXERCISE CORPUS
============================================================

Нужен versioned exercise bank.

Каждое упражнение:

    id
    source
    license
    competency
    skill_tags
    difficulty_rung
    statement
    tests
    reference_solution
    typical_errors

Difficulty:

    repetition
    analogy
    new
    unfamiliar_context
    combination
    independent

Обязательно хранить provenance.

Никакой контент не попадает в production corpus,
если лицензия не проверена.

============================================================
# 9. ЛИЦЕНЗИОННАЯ ПОЛИТИКА
============================================================

Для каждого внешнего источника проверить:

    license
    redistribution
    modification
    attribution
    commercial restrictions

Статусы:

    pending
    approved
    rejected

Контент rejected:

    НЕ использовать.

Не путать:

    "можно посмотреть"

с:

    "можно включить в собственную базу".

============================================================
# 10. DETERMINISTIC GRADING
============================================================

Student code:

    Submission
        ↓
    Execution
        ↓
    pytest
        ↓
    normalized result

Результат должен различать:

    PASS
    FAIL
    ERROR
    TIMEOUT
    INFRASTRUCTURE_ERROR

Student failure ≠ grader failure.

Correctness ≠ mastery.

Static analysis ≠ mastery.

============================================================
# 11. STATIC ANALYSIS
============================================================

Допустимые источники diagnostics:

    Python AST
    Pylint
    Radon
    Flake8
    Bandit

Но каждый инструмент — только sensor.

Не позволять:

    pylint_score → competency_level

или:

    maintainability_index → mastery

Maintainability Index:

    diagnostic_only

Security diagnostics:

    visibility controlled by curriculum policy.

============================================================
# 12. ERROR PATTERN ENGINE
============================================================

Ошибки классифицируются:

    conceptual
    syntax
    decomposition
    debugging
    transfer
    dependency

Каждый pattern:

    detector
    pattern_id
    competency
    error_type
    severity
    hint_bank

Примеры:

    mutable_default_argument
    bare_except
    excessive_nesting
    repeated_code
    inefficient_lookup
    etc.

Detector должен быть deterministic.

============================================================
# 13. HINT SYSTEM
============================================================

Hint levels:

    L0
    L1
    L2
    L3
    L4
    L5
    L6

Правила:

- всегда начинать с L0;
- переходить максимум на один уровень;
- L4+ требует явного разрешения;
- Project/Client Mode максимум L3;
- новый exercise → reset L0.

Hints должны находиться в versioned bank.

Никаких генеративных подсказок внутри deterministic core.

============================================================
# 14. SPACED REPETITION
============================================================

Использовать готовый алгоритм:

    FSRS

или после research:

    SM-2

НЕ писать собственный алгоритм.

Единица планирования:

    competency

а не:

    flashcard.

FSRS отвечает:

    WHEN TO REVIEW

а не:

    WHAT THE STUDENT KNOWS

Это две разные модели.

============================================================
# 15. ACTIVITY SELECTION
============================================================

Разделить:

    eligibility

и:

    selection.

Сначала определить:

> какие активности допустимы?

Затем:

> какая из допустимых должна быть выбрана?

Selection должен быть deterministic.

Одинаковый state:

    одинаковый candidate set
    одинаковый ordering
    одинаковый selected activity.

Каждый выбор должен иметь объяснение:

    why_selected
    why_eligible
    why_other_candidates_rejected

============================================================
# 16. PROJECT ENGINE
============================================================

Создать deterministic "Заказчик".

Project состоит из:

    requirements
    constraints
    acceptance criteria
    competencies
    question tree

Student answers:

    → deterministic project specification

Никакой генерации требований LLM.

Project completion может создавать:

    project_usage evidence

============================================================
# 17. SANDBOX
============================================================

Текущая среда:

    local Termux
    single user
    localhost
    no public access

Поэтому MVP:

    subprocess
    timeout
    RLIMIT
    temporary filesystem
    environment sanitization

Явно:

    SANDBOX_TIER = "mvp_untrusted_single_user"

Это НЕ production-grade isolation.

Hardened tier позже:

    nsjail
    Docker
    namespaces
    network isolation

Но интерфейс должен быть единым:

    Job
    → Worker
    → Sandbox
    → Result

============================================================
# 18. STORAGE
============================================================

Начать с:

    SQLite

Не использовать PostgreSQL без необходимости.

Основные сущности:

    competencies
    prerequisites
    exercises
    exercise_sources
    submissions
    test_results
    diagnostics
    error_patterns
    hints
    evidence
    review_states
    projects
    curriculum
    configuration

============================================================
# 19. API
============================================================

FastAPI — только application layer.

Пример:

    GET /next-activity
    GET /competencies
    GET /exercises/{id***REMOVED***
    POST /submit
    GET /result/{id***REMOVED***
    POST /hint
    GET /reviews
    GET /projects

API НЕ содержит learning logic.

Architecture:

    HTTP
      ↓
    Application Services
      ↓
    Domain Engines
      ↓
    Repositories

============================================================
# 20. FRONTEND
============================================================

MVP:

    HTML
    CSS
    JavaScript

Без React/Vue/etc., если нет объективной необходимости.

UI:

    Dashboard
    Competency Map
    Theory
    Exercise
    Code
    Result
    Hints
    Review
    Project

UI не принимает образовательные решения.

============================================================
# 21. LOCAL DEPLOYMENT
============================================================

Первичная среда:

    Termux

FastAPI:

    127.0.0.1:PORT

Возможность LAN:

    IP телефона

Не зависеть от:

    leviathan_agent
    hermes
    openclaw
    внешнего LLM
    внешнего API

Система должна запускаться автономно.

============================================================
# 22. RESEARCH BEFORE IMPLEMENTATION
============================================================

ПЕРЕД написанием архитектуры или кода провести web research.

Исследовать:

1. open licensed Python exercise sources;
2. Exercism architecture;
3. open-source autograders;
4. pytest execution;
5. AST tooling;
6. Pylint;
7. Radon;
8. Flake8;
9. Bandit;
10. FSRS;
11. SM-2;
12. safe Python execution;
13. Termux sandbox capabilities;
14. existing deterministic learning systems;
15. competency-based learning models;
16. mastery learning;
17. curriculum progression models.

Для каждого решения:

    source
    finding
    implication
    recommendation

Не принимать architectural decision только потому,
что инструмент популярен.

============================================================
# 23. RESEARCH OUTPUT
============================================================

До реализации предоставить:

## A. SYSTEM MODEL

Что является:

    input
    state
    transition
    decision
    output

## B. DETERMINISM AUDIT

Таблица:

| Component | Deterministic? | Why | Missing Rule |
|-----------|----------------|-----|--------------|

## C. COMPETENCY MAP

Полная preliminary map.

## D. CURRICULUM

Темы и prerequisites.

## E. EXERCISE CORPUS

Источники + лицензии + gaps.

## F. RULES

Полный список deterministic rules.

## G. UNRESOLVED AREAS

Что невозможно определить автоматически.

## H. ARCHITECTURE

Компоненты и boundaries.

## I. DATA MODEL

SQLite schema.

## J. IMPLEMENTATION PLAN

Фазы и dependencies.

============================================================
# 24. IMPLEMENTATION PHASES
============================================================

После approval разбить реализацию:

PHASE A
Research + Formalization

PHASE B
Curriculum + Competency Map

PHASE C
Exercise Corpus + Provenance

PHASE D
Execution + Grading

PHASE E
Static Analysis + Error Patterns

PHASE F
Hint Engine

PHASE G
Evidence Engine

PHASE H
Competency State Machine

PHASE I
FSRS

PHASE J
Activity Eligibility + Selection

PHASE K
Project / Client Engine

PHASE L
FastAPI

PHASE M
Frontend

PHASE N
End-to-End Validation

Не переходить к следующей фазе
без проверки предыдущей.

============================================================
# 25. КРИТИЧЕСКИЙ RULE: НЕ ДОГАДЫВАТЬСЯ
============================================================

Если обнаружил:

    missing rule
    ambiguous methodology
    conflicting requirement
    insufficient data
    impossible deterministic decision

НЕ заполняй пробел собственной логикой.

Вывод:

    GAP

и:

    WHY IT MATTERS

и:

    POSSIBLE OPTIONS

и:

    RECOMMENDED OPTION

Окончательное правило считается частью системы
только после явного approval.

============================================================
# 26. CHANGE CONTROL
============================================================

После утверждения architecture:

Нельзя молча:

- менять competency model;
- менять state transitions;
- менять difficulty ladder;
- менять hint policy;
- менять evidence semantics;
- менять FSRS mapping;
- менять selection priority.

Если implementation требует изменения:

    STOP
    REPORT ARCHITECTURAL CONFLICT
    PROPOSE CHANGE
    WAIT FOR APPROVAL

============================================================
# 27. TESTING PHILOSOPHY
============================================================

Тестировать не только функции.

Тестировать свойства системы:

    determinism
    idempotency
    reproducibility
    explainability
    state reconstruction
    invariant preservation

Критический тест:

    same_events
    + same_state
    + same_config

    → same_result

============================================================
# 28. FINAL ARCHITECTURAL PROPERTY
============================================================

Платформа должна быть способна ответить:

> Почему система дала этому ученику именно это задание?

Ответ не может быть:

    "AI решил."

Ответ должен быть:

    competency X = S4
    prerequisite Y = satisfied
    exercise Z = eligible
    review = due
    priority = 0.82
    selected because:
        rule R17
        policy P03

То есть любое существенное образовательное решение должно быть:

    reproducible
    inspectable
    explainable
    testable
    versioned

============================================================
# ПЕРВАЯ ЗАДАЧА АГЕНТА
============================================================

НЕ ПИШИ КОД.

Сначала:

1. Проанализируй существующую методику обучения Python.
2. Проанализируй текущий Blueprint.
3. Проведи web research.
4. Построй Determinism Audit.
5. Найди все места, где методика пока недостаточно формализована.
6. Предложи canonical system model.
7. Предложи архитектуру.
8. Предложи phases.
9. Для каждой фазы укажи:
   - входы;
   - выходы;
   - dependencies;
   - deterministic guarantees;
   - tests;
   - definition of done.

Особенно важно:

НЕ пытайся сделать систему "умнее" за счёт LLM.

Наша цель обратная:

    максимум образовательной логики
    формализовать
    ↓
    превратить в deterministic rules
    ↓
    сделать воспроизводимой
    ↓
    сделать тестируемой.

LLM, если когда-нибудь появится,
должен быть внешним расширением,
а не скрытым мозгом системы.