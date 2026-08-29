ANTI-SLOP DESIGN INTELLIGENCE SYSTEM

Техническое задание MVP v0.1

Версия: 0.1
Статус: Draft / Implementation Specification
Тип продукта: Developer Tool / Design Intelligence Layer
Основная задача: предотвращение AI Design Slop при генерации интерфейсов AI-кодерами

---

1. PRODUCT DEFINITION

1.1. Название

Рабочее название:

Anti-Slop Design Intelligence System

CLI-команда:

anti-slop

---

2. ПРОБЛЕМА

Современные AI-кодеры способны быстро генерировать визуально качественный React/Tailwind-код, однако часто воспроизводят статистически распространенные дизайн-паттерны:

- одинаковые hero-секции;
- Bento Grid без функциональной необходимости;
- glassmorphism;
- gradients;
- glow;
- огромные заголовки;
- italic serif accents;
- floating pill navigation;
- бессмысленные dashboard mockups;
- декоративные анимации;
- generic AI copy;
- одинаковую структуру лендингов.

Проблема не в самих компонентах.

Проблема заключается в том, что AI часто выбирает визуальное решение до определения пользовательской задачи.

Поэтому система должна не просто говорить:

«"Не используй gradient."»

Она должна определять:

«"Почему gradient используется здесь и соответствует ли он задаче продукта?"»

---

3. ОСНОВНОЙ ПРИНЦИП

Главная архитектурная парадигма:

PROMPT → UI

заменяется на:

CONTEXT
   ↓
INTENT
   ↓
CONSTRAINTS
   ↓
DESIGN MANIFEST
   ↓
COMPOSITION
   ↓
UI IMPLEMENTATION
   ↓
AUDIT
   ↓
CORRECTION

---

4. ЦЕЛЬ MVP

MVP должен доказать одну ключевую гипотезу:

«Если AI-кодер получает структурированный Design Manifest, содержащий контекст продукта, пользовательские задачи, визуальные ограничения и объяснимые правила, количество типичных AI Design Slop-паттернов в генерируемом интерфейсе уменьшается.»

MVP НЕ должен пытаться решить задачу "определения красоты".

MVP должен определять:

1. наличие известных slop-паттернов;
2. контекстную допустимость этих паттернов;
3. структурную предсказуемость;
4. наличие generic AI copy;
5. соответствие реализации Design Manifest;
6. конкретные способы исправления.

---

5. ГРАНИЦЫ MVP

5.1. Входит в MVP

Core

- Design Manifest Schema;
- Rule Engine;
- deterministic analyzer;
- Tailwind analyzer;
- HTML/DOM analyzer;
- basic CSS analyzer;
- Content Slop detector;
- Layout Slop detector;
- Typography Slop detector;
- Color/Effect Slop detector;
- scoring engine;
- CLI;
- JSON report;
- human-readable terminal report;
- Context Engine;
- Manifest Generator;
- AI Reviewer prompt;
- Cursor/Claude integration files.

5.2. НЕ входит в MVP

Не реализуются:

- собственная React UI library;
- собственная CSS framework;
- Figma plugin;
- полноценный Vision Auditor;
- база 10 000 сайтов;
- полноценный embedding-based TSS;
- автоматическая оценка эстетики;
- автоматическое редизайнирование всего проекта;
- SaaS dashboard;
- cloud infrastructure;
- authentication;
- billing;
- multi-user collaboration.

Это относится к следующим версиям.

---

6. АРХИТЕКТУРА MVP

                    ┌──────────────────┐
                    │     USER BRIEF   │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │  CONTEXT ENGINE  │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ MANIFEST GENERATOR│
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ design_manifest  │
                    │      .yaml       │
                    └────────┬─────────┘
                             ↓
             ┌───────────────┴────────────────┐
             ↓                                ↓
   ┌──────────────────┐             ┌──────────────────┐
   │ AI Coding Agent  │             │ Developer        │
   │ Cursor / Claude  │             │ Implementation   │
   └────────┬─────────┘             └────────┬─────────┘
            └────────────────┬───────────────┘
                             ↓
                    ┌──────────────────┐
                    │   ANTI-SLOP CLI  │
                    └────────┬─────────┘
                             ↓
              ┌─────────────┴──────────────┐
              ↓                            ↓
     ┌────────────────┐           ┌─────────────────┐
     │ Deterministic  │           │ Semantic Review │
     │ Linter         │           │     AI          │
     └───────┬────────┘           └────────┬────────┘
             └──────────────┬─────────────┘
                            ↓
                   ┌───────────────────┐
                   │  SCORE + REPORT   │
                   └───────────────────┘

---

7. REPOSITORY STRUCTURE

MVP должен использовать следующую структуру:

anti-slop/
│
├── package.json
├── README.md
├── LICENSE
├── tsconfig.json
│
├── src/
│   ├── cli/
│   │   ├── index.ts
│   │   ├── commands/
│   │   │   ├── audit.ts
│   │   │   ├── init.ts
│   │   │   ├── manifest.ts
│   │   │   └── explain.ts
│   │   └── output/
│   │       ├── terminal.ts
│   │       ├── json.ts
│   │       └── markdown.ts
│   │
│   ├── core/
│   │   ├── analyzer/
│   │   │   ├── dom.ts
│   │   │   ├── css.ts
│   │   │   ├── tailwind.ts
│   │   │   ├── typography.ts
│   │   │   ├── colors.ts
│   │   │   ├── layout.ts
│   │   │   └── content.ts
│   │   │
│   │   ├── rules/
│   │   │   ├── registry.ts
│   │   │   ├── types.ts
│   │   │   └── builtin/
│   │   │       ├── typography/
│   │   │       ├── color/
│   │   │       ├── effects/
│   │   │       ├── layout/
│   │   │       └── content/
│   │   │
│   │   ├── scoring/
│   │   │   ├── scorer.ts
│   │   │   ├── weights.ts
│   │   │   └── confidence.ts
│   │   │
│   │   ├── manifest/
│   │   │   ├── schema.ts
│   │   │   ├── loader.ts
│   │   │   └── validator.ts
│   │   │
│   │   └── context/
│   │       ├── engine.ts
│   │       └── taxonomy.ts
│   │
│   ├── ai/
│   │   ├── reviewer.ts
│   │   ├── prompts/
│   │   │   └── reviewer.md
│   │   └── adapters/
│   │
│   └── integrations/
│       ├── cursor/
│       └── claude/
│
├── rules/
│   ├── typography.yaml
│   ├── colors.yaml
│   ├── effects.yaml
│   ├── layout.yaml
│   └── content.yaml
│
├── schemas/
│   └── design-manifest.schema.json
│
├── templates/
│   ├── design-manifest.yaml
│   ├── cursorrules
│   └── claude-design-rules.md
│
└── tests/
    ├── rules/
    ├── analyzer/
    ├── scoring/
    ├── manifest/
    └── fixtures/

---

8. DESIGN MANIFEST

Manifest является центральным контрактом системы.

AI-кодер должен рассматривать его как Design Specification, а не как необязательную рекомендацию.

Минимальный формат:

design_manifest:
  version: "0.1"

  project:
    name: "MediCore B2B Portal"

  context:
    domain: "healthcare"
    business_model: "B2B"
    audience:
      description: "clinic administrators"
      age_range: "40+"
      technical_level: "medium"

  intent:
    primary:
      - trust
      - clarity
      - efficiency

    secondary:
      - data_density

  core_tasks:
    - "review patient records"
    - "filter records"
    - "identify errors"
    - "export reports"

  information_architecture:
    density: "high"

    primary_content:
      - tables
      - filters
      - statuses
      - metrics

  visual_language:
    aesthetic: "institutional"
    mood:
      - calm
      - precise
      - trustworthy

    density: "high"

    shape_language:
      radius_max: 4

  typography:
    heading:
      family: "Inter"
      weight: 600
      italic: false

    body:
      family: "Inter"
      weight: 400

    mono:
      allowed_for:
        - ids
        - codes

  color:
    mode: "light"
    primary: "#1F4B7A"
    accent: "#2E7D6B"

  rules:
    forbidden:
      - glassmorphism
      - decorative_gradient
      - gradient_text
      - decorative_glow
      - bento_grid
      - italic_serif_accent
      - decorative_motion

    required:
      - high_contrast
      - data_tables
      - explicit_status
      - clear_navigation

  composition:
    preferred:
      - data_dense_dashboard
      - diagnostic_split
      - editorial_index

  motion:
    policy: "functional_only"

---

9. MANIFEST SCHEMA

Manifest должен быть валидируемым JSON Schema.

Обязательные верхнеуровневые поля:

version
project
context
intent
core_tasks
information_architecture
visual_language
rules

Опциональные:

typography
color
composition
motion
accessibility
brand
components
content

---

10. CONTEXT ENGINE

Context Engine превращает пользовательский brief в структурированную модель.

Вход:

"Сайт для логистической компании.
B2B.
Клиенты - менеджеры среднего бизнеса.
Нужно показывать доставку грузов,
интеграцию с 1C и отслеживание заказов."

Выход:

domain: logistics
business_model: B2B
audience:
  role: operations_managers
  technical_level: medium

primary_tasks:
  - shipment_tracking
  - order_management
  - integration_management

information_density: medium_high

primary_intent:
  - reliability
  - operational_clarity
  - efficiency

---

11. ПРИНЦИП CONTEXT ENGINE

Engine НЕ должен самостоятельно придумывать визуальный стиль на основании популярных сайтов.

Он должен двигаться:

Domain
 ↓
Audience
 ↓
Task
 ↓
Information
 ↓
Priority
 ↓
Interaction
 ↓
Visual constraints

Например:

Accounting
+
40+ users
+
daily data processing
+
high information density

должно приводить примерно к:

high readability
high contrast
compact spacing
stable navigation
tables
filters
minimal decorative motion

а не:

dark mode
glassmorphism
purple glow
floating cards

---

12. RULE ENGINE

Rule Engine является ядром deterministic-аудита.

Каждое правило представляет собой отдельную декларативную сущность.

Формат:

id: TYPO-001

name: Italic Serif Accent

category: typography

severity: high

description:
  "Serif italic accent inside sans-serif heading."

detect:
  selectors:
    - "h1"
    - "h2"

  conditions:
    - font_style: italic
    - font_family_category: serif

context:
  disallowed:
    - fintech
    - healthcare
    - legal
    - b2b_data

  acceptable:
    - editorial
    - luxury
    - fashion

why:
  "Common AI-generated visual trope used without semantic justification."

suggestion:
  "Use weight, scale or spacing contrast instead of decorative serif italic."

confidence:
  base: 0.95

---

13. КАТЕГОРИИ ПРАВИЛ MVP

MVP должен содержать минимум 25 правил.

---

14. TYPOGRAPHY RULES

TYPO-001

Italic Serif Accent

Обнаруживает:

font-style: italic
font-family: serif

внутри:

h1
h2
hero headings

Severity:

high

---

TYPO-002

Tracking Overload

Обнаруживает:

letter-spacing > 0.15em

Особенно для:

uppercase
small labels
body text

Severity:

medium

---

TYPO-003

Scale Shock

Обнаруживает:

hero heading > 120px

при одновременно маленьком body text.

Правило не должно автоматически считать 120px ошибкой.

Оно должно учитывать:

heading/body ratio
viewport
content length
domain

---

TYPO-004

Excessive Display Typography

Обнаруживает чрезмерное количество display-style заголовков.

---

TYPO-005

Decorative Mono

Обнаруживает использование monospace:

badge
label
subtitle
navigation

без manifest justification.

---

15. COLOR RULES

COLOR-001

Startup Purple

Обнаруживает использование известных AI/startup purple цветов.

Важно:

Цвет сам по себе НЕ является violation.

Правило должно создавать:

pattern detected

а severity зависит от context.

---

COLOR-002

AI Cyan

Аналогично.

---

COLOR-003

Gradient Text

Обнаруживает:

background-clip: text

или Tailwind-паттерны gradient text.

---

COLOR-004

Excessive Gradient

Подсчитывает количество gradient declarations.

Violation возникает только после context-aware threshold.

---

COLOR-005

Multi-stop Gradient

Gradient с более чем тремя stops.

---

16. EFFECT RULES

EFFECT-001

Gratuitous Glow

Обнаруживает:

box-shadow
drop-shadow
blur
radial-gradient

используемые декоративно.

---

EFFECT-002

AI Orb

Обнаруживает большие:

blurred radial gradients

без функционального назначения.

---

EFFECT-003

Inner Glow

Обнаруживает:

inset

используемый исключительно декоративно.

---

EFFECT-004

Gratuitous Glassmorphism

Обнаруживает:

backdrop-filter: blur

в сочетании с translucent backgrounds.

---

EFFECT-005

Border Gradient

Обнаруживает gradient borders вокруг UI elements.

---

EFFECT-006

Excessive Blur

Подсчитывает blur effects на странице.

---

17. LAYOUT RULES

LAYOUT-001

Bento Trap

Обнаруживает:

- grid;
- cards;
- varying spans;
- asymmetric card dimensions.

Но Bento не считается нарушением автоматически.

Проверяется:

Is spatial comparison required?

---

LAYOUT-002

Icon + Title + Description Grid

Обнаруживает повторяющийся паттерн:

icon
title
2-3 lines

в 3-6 одинаковых карточках.

---

LAYOUT-003

Marquee Logo Graveyard

Обнаруживает:

marquee
animate-scroll
infinite horizontal logo list

---

LAYOUT-004

Floating Pill Navbar

Обнаруживает:

fixed navbar
rounded-full
backdrop-blur
floating margins

---

LAYOUT-005

Excessive Cardization

Подсчитывает процент контента, помещенного внутрь карточек.

---

LAYOUT-006

Excessive Border Radius

Обнаруживает:

radius > 24px

но severity зависит от context.

---

LAYOUT-007

Repeated Section Template

Обнаруживает повтор:

icon + heading + paragraph

в нескольких секциях.

---

18. MOTION RULES

MOTION-001

Decorative Fade-In

Обнаруживает массовое использование:

fade-in
fade-in-up
slide-up

для каждого элемента.

---

MOTION-002

Excessive Scroll Animation

Обнаруживает большое количество scroll-triggered animations.

---

MOTION-003

Decorative Parallax

Обнаруживает parallax без semantic purpose.

---

19. CONTENT RULES

CONTENT-001

Generic AI Lexicon

Обнаруживает слова:

seamless
elevate
unleash
next-gen
revolutionize
crafted
innovative
powerful
transform
effortless

Важно:

это не должно работать как простой запрет.

Система должна проверять контекст.

---

CONTENT-002

Generic CTA

Например:

Get Started
Learn More
Discover More

без конкретизации действия.

---

CONTENT-003

Fake Dashboard

Обнаруживает признаки mock dashboard:

Lorem ipsum
fake notifications
fake analytics
meaningless numbers
placeholder charts

---

CONTENT-004

Semantic Vagueness

Обнаруживает утверждения вроде:

The future of X
Power your business
Transform your workflow

без конкретного действия или результата.

---

CONTENT-005

Phantom Social Proof

Обнаруживает:

Trusted by leading companies

без реальных идентификаторов.

---

20. META RULES

META-001

Design-by-Checklist

Обнаруживает стандартную структуру:

Hero
↓
Logo Cloud
↓
Features
↓
Testimonials
↓
Pricing
↓
FAQ
↓
CTA

Но наличие такой структуры само по себе не является violation.

Система проверяет:

Does each section serve a declared user/business goal?

---

META-002

Narrative Absence

Если manifest определяет narrative journey, но страница представляет собой набор независимых блоков.

---

META-003

Contextual Mismatch

Например:

legal
+
cyberpunk neon
+
decorative glow
+
glassmorphism

---

21. RULE SEVERITY

Каждое правило имеет:

critical
high
medium
low
info

Рекомендуемые значения:

critical = 25
high     = 15
medium   = 8
low      = 3
info     = 0

Но severity не должна напрямую равняться penalty.

---

22. CONTEXT MATRIX

Каждое правило может иметь context modifier.

Пример:

context_matrix:

  b2b_fintech:
    glassmorphism:
      multiplier: 1.5

  gaming:
    glassmorphism:
      multiplier: 0.2

  editorial:
    italic_serif:
      multiplier: 0.1

  healthcare:
    neon_glow:
      multiplier: 1.5

Таким образом:

Rule
+
Context
=
Verdict

а не:

Rule
=
Bad

---

23. VERDICT TYPES

Rule Engine должен возвращать:

VIOLATION
WARNING
ACCEPTABLE
INFO

Пример:

{
  "rule": "EFFECT-004",
  "pattern": "glassmorphism",
  "verdict": "WARNING",
  "confidence": 0.91,
  "severity": "high",
  "context_modifier": 0.4
***REMOVED***

---

24. FINDING OBJECT

Каждый найденный паттерн должен иметь:

{
  "rule_id": "TYPO-001",
  "category": "typography",
  "severity": "high",
  "confidence": 0.95,
  "verdict": "VIOLATION",

  "file": "src/components/Hero.tsx",

  "line": 42,

  "element": "h1",

  "evidence": {
    "classes": [
      "font-serif",
      "italic"
    ***REMOVED***
  ***REMOVED***,

  "reason":
    "Italic serif accent detected inside a sans-serif hero heading.",

  "context":
    "b2b_fintech",

  "suggestion":
    "Use weight or scale contrast instead."
***REMOVED***

---

25. SCORING ENGINE

Итоговый score:

100 = clean
0   = severe slop

Базовая модель:

Score = 100 - Penalty

Penalty зависит от:

severity
confidence
context multiplier
frequency
duplication

---

26. РАЗДЕЛЕНИЕ SCORE

Итоговый score должен состоять из отдельных компонентов:

Overall Score
│
├── Typography
├── Color
├── Effects
├── Layout
├── Motion
├── Content
├── Contextual Fit
└── Predictability

Пример:

ANTI-SLOP SCORE: 63/100

Typography       82
Color             74
Effects           48
Layout            51
Motion            79
Content           61
Context Fit       88
Predictability    N/A

---

27. ВАЖНОЕ ПРАВИЛО SCORE

Не использовать:

"3 gradients = -30"

Система должна учитывать насыщенность:

1 gradient → insignificant
5 gradients → warning
20 gradients → strong violation

Также учитывать:

page size
component count
domain
manifest

---

28. SCORE LEVELS

90-100 → Excellent
75-89  → Low Slop
60-74  → Moderate Slop
40-59  → High Slop
0-39   → Severe Slop

---

29. CLI

Основная команда:

anti-slop audit ./src

---

30. CLI OPTIONS

Минимальный набор:

anti-slop audit ./src

anti-slop audit ./src \
  --manifest=design_manifest.yaml

anti-slop audit ./src \
  --domain=b2b-fintech

anti-slop audit ./src \
  --format=json

anti-slop audit ./src \
  --format=markdown

anti-slop audit ./src \
  --severity=high

anti-slop audit ./src \
  --fix

anti-slop explain TYPO-001

---

31. INIT

Команда:

anti-slop init

создает:

anti-slop.config.yaml
design_manifest.yaml

---

32. MANIFEST GENERATION

Команда:

anti-slop manifest

запускает Context Engine.

CLI спрашивает:

What are you building?
Who will use it?
What is the primary task?
What information must users see?
What is the business goal?

На выходе:

design_manifest.yaml

---

33. AI MANIFEST GENERATOR

Для генерации Manifest может использоваться LLM.

Но LLM не должна непосредственно писать CSS/UI.

Ее задача:

Brief → structured design constraints

Output должен валидироваться deterministic schema validator.

---

34. AI REVIEWER

AI Reviewer используется только там, где deterministic analysis недостаточно.

Его задачи:

1. Semantic Disconnect

Проверить:

Does visual element correspond to nearby content?

2. Contextual Appropriateness

Проверить:

Does visual language match the domain and audience?

3. Narrative

Проверить:

Does page guide user from problem to solution?

4. Phantom UI

Проверить:

Is displayed UI meaningful or decorative?

---

35. SOCRATIC REVIEW

Перед генерацией AI должен задать себе:

1. Why does this element exist?

2. What user problem does it solve?

3. If I remove it, does functionality suffer?

4. Why is this visual treatment necessary?

5. Could this information be represented more directly?

6. Is this card necessary?

7. Is this animation communicating state or merely decorating?

8. Is this dark theme justified by context?

9. Is this gradient part of the brand or an AI default?

10. Does this layout emerge from the content or from a template?

---

36. AI CODING CONTRACT

AI-кодер должен соблюдать:

MANIFEST > DESIGN TRENDS
MANIFEST > PERSONAL AI PREFERENCE
USER TASK > DECORATION
SEMANTIC PURPOSE > VISUAL NOVELTY

---

37. CURSOR INTEGRATION

MVP должен генерировать:

.cursorrules

или совместимый rules-файл.

Пример логики:

Before writing UI code:

1. Read design_manifest.yaml.
2. Identify domain.
3. Identify audience.
4. Identify primary user task.
5. Identify information hierarchy.
6. Select composition pattern.
7. Only then select components.
8. Do not introduce forbidden patterns.
9. Every non-trivial visual treatment must have a semantic justification.
10. Run anti-slop audit after implementation.

---

38. CLAUDE CODE INTEGRATION

Создается:

.claude/
└── design-rules.md

Файл содержит:

- Manifest contract;
- Anti-Slop rules;
- Socratic Review;
- implementation workflow;
- audit workflow.

---

39. AI GENERATION WORKFLOW

AI должен работать по следующему алгоритму:

STEP 1
Read Manifest

STEP 2
Summarize:
- audience
- task
- information hierarchy
- visual intent

STEP 3
Choose composition

STEP 4
Explain composition

STEP 5
Select components

STEP 6
Implement

STEP 7
Self-review

STEP 8
Run deterministic audit

STEP 9
Fix violations

STEP 10
Return code

---

40. COMPOSITION ENGINE

MVP не генерирует полноценный UI.

Он выбирает структурный skeleton.

Доступные patterns:

editorial_index
diagnostic_split
data_dense_dashboard
object_anatomy
timeline_narrative
comparison_layout
workflow_layout
single_focus
documentation_layout

---

41. COMPOSITION SELECTION

Пример:

composition:
  selected: data_dense_dashboard

  reason:
    "Users primarily compare and filter operational data."

  rejected:
    - bento_grid
    - editorial_index

---

42. COMPONENT SELECTION

Только после Composition Engine:

Composition
↓
Information blocks
↓
Components

Например:

data_dense_dashboard
↓
filters
↓
table
↓
status badges
↓
pagination

а не:

Bento
↓
cards
↓
icons

---

43. DETERMINISTIC ANALYSIS

Основной принцип:

«Всё, что можно определить без LLM, определяется без LLM.»

LLM НЕ должна анализировать:

font-size
border-radius
CSS gradient
Tailwind classes
DOM structure
backdrop-filter
animation classes
keyword frequency

---

44. ТЕХНОЛОГИЧЕСКИЙ СТЕК

Рекомендуемый MVP:

Node.js
TypeScript

Причина:

- CLI;
- npm ecosystem;
- Tailwind;
- PostCSS;
- AST parsing;
- React/JSX;
- удобная интеграция с Cursor;
- распространение через npm.

---

45. ОСНОВНЫЕ LIBRARIES

Предпочтительно:

commander
yaml
zod
postcss
postcss-selector-parser
@babel/parser
@babel/traverse
glob
chalk

Конкретный набор библиотек может быть заменен при реализации, если функциональность сохраняется.

---

46. АНАЛИЗ REACT

Analyzer должен понимать:

<div className="rounded-3xl backdrop-blur-md bg-white/10">

и извлекать:

radius = 24+
backdrop_blur = true
translucent_background = true

---

47. TAILWIND ANALYZER

Необходимо поддержать минимум:

rounded-*
blur-*
backdrop-blur-*
bg-gradient-*
from-*
via-*
to-*
shadow-*
tracking-*
font-serif
font-mono
italic
uppercase
animate-*
transition-*
duration-*

---

48. DOM ANALYSIS

Analyzer должен строить упрощенное представление:

Page
 ├── Header
 ├── Hero
 │    ├── Heading
 │    ├── Paragraph
 │    └── CTA
 ├── Section
 │    ├── Card
 │    ├── Card
 │    └── Card
 └── Footer

Это используется для:

- card counting;
- repeated pattern detection;
- section classification;
- bento detection;
- navbar detection.

---

49. НЕ НУЖНО ПЫТАТЬСЯ СРАЗУ РЕШИТЬ GENERAL DOM UNDERSTANDING

MVP использует heuristics.

Например:

3+ siblings
+
same structural pattern
+
icon
+
heading
+
paragraph
=
probable feature card grid

---

50. MANIFEST COMPLIANCE

Если manifest содержит:

forbidden:
  - glassmorphism

и найден:

backdrop-blur
+
transparent background

результат:

VIOLATION

Если manifest не запрещает glassmorphism:

WARNING / ACCEPTABLE

в зависимости от context.

---

51. RULE OVERRIDES

Manifest должен иметь возможность override:

rule_overrides:

  EFFECT-004:
    verdict: acceptable
    reason: "Required by brand visual identity."

Но AI не должен иметь права silently override rules.

Override должен быть явно записан.

---

52. EXPLAINABILITY

Каждое нарушение должно отвечать на четыре вопроса:

WHAT?
WHY?
WHY HERE?
WHAT INSTEAD?

Пример:

[EFFECT-004***REMOVED*** Glassmorphism

WHAT:
backdrop-blur-md detected.

WHY:
Glass surfaces reduce visual separation.

WHY HERE:
Manifest defines high-density B2B data interface.

WHAT INSTEAD:
Use solid surface + 1px border + elevation.

---

53. FALSE POSITIVE CONTROL

Каждое правило должно иметь:

confidence

Например:

0.95 → strong detection
0.75 → probable
0.50 → weak

CLI:

--confidence=0.8

показывает только уверенные findings.

---

54. DUPLICATION PENALTY

Повтор одного паттерна должен усиливать severity.

Например:

1 glow → warning
5 glows → high
15 glows → severe

Это позволяет выявлять системную проблему, а не наказывать единичное применение.

---

55. PAGE-LEVEL ANALYSIS

MVP должен анализировать не только отдельный компонент.

Нужен уровень:

element
component
section
page
project

Например:

rounded-3xl

один раз:

acceptable

но:

95% interactive surfaces = rounded-3xl

может стать:

warning

---

56. PROJECT-LEVEL ANALYSIS

CLI:

anti-slop audit ./src

должен собирать агрегированные показатели:

files analyzed
components analyzed
pages analyzed
total findings
unique rules triggered
repeated patterns

---

57. TERMINAL REPORT

Пример:

ANTI-SLOP AUDIT
────────────────────────────────────────

Project: MediCore
Domain: healthcare / B2B

Score: 62/100
Level: MODERATE SLOP

Findings: 17

HIGH
────────────────────────────────────────

[TYP-001***REMOVED*** Italic Serif Accent
Hero.tsx:42
Confidence: 0.95

Why:
Healthcare B2B interface has no semantic reason
for decorative serif contrast.

Fix:
Use weight/scale contrast.

[LAYOUT-001***REMOVED*** Bento Grid
Features.tsx:18

Confidence: 0.88

Why:
Content is sequential and does not require
spatial comparison.

Fix:
Use structured list or alternating split layout.


MEDIUM
────────────────────────────────────────

[EFFECT-004***REMOVED*** Glassmorphism × 6

[CONTENT-001***REMOVED*** Generic AI Copy × 4

[MOTION-001***REMOVED*** Decorative Fade-In × 3


CATEGORY SCORES

Typography       81
Color            76
Effects          44
Layout           52
Motion           73
Content          61
Context Fit      87

---

58. JSON OUTPUT

Команда:

anti-slop audit ./src --format=json

возвращает:

{
  "version": "0.1",
  "score": 62,
  "level": "moderate",

  "summary": {
    "files": 42,
    "components": 31,
    "findings": 17
  ***REMOVED***,

  "categories": {
    "typography": 81,
    "color": 76,
    "effects": 44,
    "layout": 52,
    "motion": 73,
    "content": 61,
    "context_fit": 87
  ***REMOVED***,

  "findings": [***REMOVED***
***REMOVED***

---

59. CI/CD MODE

MVP должен поддерживать:

anti-slop audit ./src --ci

Exit codes:

0 = pass
1 = warnings
2 = violations

Конфигурация:

ci:
  fail_on:
    - critical
    - high

  max_score_drop: 20

---

60. GIT / PR USE

Пример:

git push
 ↓
CI
 ↓
anti-slop audit
 ↓
report
 ↓
PASS / FAIL

В будущем это может быть GitHub Action.

В MVP достаточно корректных exit codes и JSON output.

---

61. TEST STRATEGY

MVP должен иметь fixture-based testing.

Каждое правило получает:

positive fixture
negative fixture
context fixture
edge-case fixture

Например:

tests/fixtures/typography/italic-serif.bad.tsx
tests/fixtures/typography/italic-serif.good.tsx
tests/fixtures/typography/italic-serif.editorial.tsx

---

62. MINIMUM TEST COVERAGE

Каждое из 25 правил:

≥ 3 tests

Минимум:

75 rule tests

Плюс:

manifest validation tests
scoring tests
CLI tests
integration tests

Целевой минимум:

100 automated tests

---

63. ACCEPTANCE CRITERIA

MVP считается работающим, если:

A

Команда:

anti-slop audit ./src

работает на реальном React/Tailwind проекте.

B

Система обнаруживает минимум:

25 predefined patterns

C

Каждое обнаружение имеет:

rule
severity
confidence
file
line
reason
suggestion

D

Manifest влияет на verdict.

E

Один и тот же паттерн может быть:

VIOLATION

в одном context и:

ACCEPTABLE

в другом.

F

CLI возвращает score.

G

CLI способен работать без LLM.

H

Manifest Generator способен создавать валидный manifest.

I

Cursor/Claude rules используют manifest.

J

Проект имеет automated tests.

---

64. MVP DEMONSTRATION SCENARIO

Необходимо создать demo project:

demo/

с намеренно типичным AI-generated SaaS интерфейсом:

dark background
purple gradients
glow
glass cards
bento
floating navbar
italic serif
generic copy
fade-in animations
fake dashboard

Запуск:

anti-slop audit ./demo

ожидаемый результат:

Score: ~30-50
Level: High/Severe Slop

После ручного исправления:

solid surfaces
clear hierarchy
real information
contextual layout
minimal effects
specific copy

повторный аудит должен показать существенное улучшение.

---

65. ВАЖНО: SCORE НЕ ДОЛЖЕН БЫТЬ ЦЕЛЬЮ

AI нельзя обучать:

«"получи 100/100".»

Иначе возникнет новый тип gaming.

Цель:

«соответствовать задаче и контексту.»

Поэтому:

Score = diagnostic metric

а не:

Score = optimization target

---

66. ANTI-SLOP SLOP PROTECTION

Система должна иметь отдельную защиту от ложного минимализма.

Она НЕ должна автоматически рекомендовать:

remove all cards
remove all gradients
remove all animation
remove all colors
remove all rounded corners
use black/white only

Вместо этого:

Is the element justified?

---

67. POSITIVE DESIGN RULES

MVP должен иметь не только forbidden patterns.

Нужны positive recommendations:

required_patterns:
  - clear_hierarchy
  - readable_body_text
  - explicit_actions
  - semantic_sections

---

68. DESIGN QUALITY MODEL

Итоговая модель:

DESIGN QUALITY
│
├── Context Fit
├── Task Fit
├── Information Hierarchy
├── Readability
├── Interaction Clarity
├── Semantic Integrity
└── Visual Restraint

Visual novelty не является обязательным quality metric.

---

69. FUTURE: TSS

Template Similarity Score переносится за пределы MVP.

V1/V2:

DOM
 ↓
Structural fingerprint
 ↓
Embedding
 ↓
Reference corpus
 ↓
Cosine similarity
 ↓
TSS

Важно:

TSS не должен напрямую означать "bad".

Он показывает:

predictability

---

70. FUTURE: VISION AUDITOR

V2:

URL / screenshot
 ↓
browser renderer
 ↓
screenshot
 ↓
vision model
 ↓
semantic analysis
 ↓
Anti-Slop report

Vision должен проверять то, чего нельзя достоверно получить из source code:

visual hierarchy
semantic imagery
fake UI
visual noise
composition
contextual mismatch

---

71. FUTURE: FIGMA PLUGIN

Figma Plugin:

Frame
 ↓
Design analyzer
 ↓
rule engine
 ↓
warnings

Пример:

⚠ Possible Slop

3 radius values detected:
8px / 16px / 32px

Gradient text detected.

Question:
Is this distinction required by the design system?

---

72. FUTURE: DESIGN KNOWLEDGE GRAPH

Следующий этап может перейти от flat rules:

rule → violation

к:

Context
 ↓
Intent
 ↓
Task
 ↓
Information
 ↓
Composition
 ↓
Visual Treatment
 ↓
Component
 ↓
Interaction

Это позволит системе не просто обнаруживать slop, а объяснять дизайн-решения.

---

73. PRODUCT EVOLUTION

v0.1

Manifest
+
25 deterministic rules
+
CLI
+
Scoring
+
Cursor/Claude rules

v0.2

Better React/Tailwind AST
+
more rules
+
better context matrix
+
autofix for safe cases

v0.3

AI Semantic Reviewer
+
Manifest Generator improvements

V1

Web interface
+
Manifest generation
+
project upload
+
AI coding integration
+
advanced audit

V2

Vision Auditor
+
URL analysis
+
Screenshot analysis
+
TSS
+
reference corpus

---

74. AUTOFIX

В MVP разрешить autofix только для безопасных трансформаций.

Например:

tracking-[0.2em***REMOVED***

может быть заменено только при явном rule configuration.

Запрещено автоматически менять:

layout
content
brand colors
composition
component hierarchy

без AI/human confirmation.

---

75. RULE DEVELOPMENT STANDARD

Каждое новое правило обязано содержать:

ID
Name
Category
Description
Detection
Severity
Confidence
Context matrix
Why
Suggestion
Tests

Нельзя добавлять правило:

"Это выглядит некрасиво"

Правило должно быть наблюдаемым или объяснимым через контекст.

---

76. WHAT MVP MUST NOT CLAIM

Продукт не должен заявлять:

"This design is objectively bad."

"This website was generated by AI."

"This is ugly."

"This design is original."

Допустимые формулировки:

"Pattern resembles common AI-generated UI conventions."

"Contextual mismatch detected."

"Repeated template-like structure detected."

"Decorative treatment lacks declared semantic justification."

"Potential predictability detected."

---

77. КЛЮЧЕВОЙ PRODUCT LOOP

В конечной системе:

USER
 ↓
BRIEF
 ↓
CONTEXT ENGINE
 ↓
DESIGN MANIFEST
 ↓
AI CODER
 ↓
CODE
 ↓
ANTI-SLOP AUDITOR
 ↓
FINDINGS
 ↓
AI CODER
 ↓
CORRECTED CODE
 ↓
AUDIT

Именно этот цикл является главным продуктом.

Не CLI сам по себе.

Не набор правил.

Не UI Kit.

---

78. DEFINITION OF DONE

MVP v0.1 считается завершенным, когда пользователь может выполнить:

npm install -g anti-slop

затем:

cd my-react-project
anti-slop init

получить:

design_manifest.yaml

затем:

anti-slop audit ./src

получить:

ANTI-SLOP REPORT
Score: XX/100
Findings: XX

и затем:

anti-slop audit ./src --format=json

получить machine-readable результат.

Дополнительно:

anti-slop init --cursor

создает Cursor rules.

И:

anti-slop init --claude

создает Claude Code rules.

---

79. ОСНОВНАЯ ФИЛОСОФИЯ ПРОДУКТА

Anti-Slop не запрещает дизайн.

Он запрещает бездумное использование дизайна.

Не:

gradient = bad

а:

gradient
↓
why?
↓
context?
↓
purpose?
↓
appropriate?

Не:

bento = bad

а:

Does the information benefit from spatial grouping?

Не:

dark mode = bad

а:

Does the user/context benefit from dark mode?

---

80. ФИНАЛЬНАЯ АРХИТЕКТУРНАЯ ФОРМУЛА

                    DESIGN INTELLIGENCE
                           │
             ┌─────────────┴─────────────┐
             │                           │
        CONTEXT ENGINE              RULE ENGINE
             │                           │
             ↓                           ↓
          INTENT                    DETECTION
             │                           │
             ↓                           ↓
       DESIGN MANIFEST              FINDINGS
             │                           │
             └─────────────┬─────────────┘
                           ↓
                    COMPOSITION ENGINE
                           │
                           ↓
                      AI CODER
                           │
                           ↓
                          UI
                           │
                           ↓
                    ANTI-SLOP AUDIT
                           │
                           ↓
                   SCORE + REASONS
                           │
                           ↓
                       CORRECT

Главный принцип MVP:

«"Context → Manifest → Composition → UI → Audit"»

а не:

«"Prompt → Components → Decoration".»

Это и является фундаментом Anti-Slop Design Intelligence System.

# ANTI-SLOP DESIGN SYSTEM  
## Исследование феномена AI Design Slop и архитектура системы защиты от него

> **Важная эпистемическая оговорка.** В текущей среде у меня нет live-доступа к интернету, поэтому я не могу открыть первоисточник прямо сейчас и дословно сверить все 16 паттернов. Ниже я даю максимально полную исследовательскую и архитектурную модель, опираясь на известный дискурс вокруг *Adrian Krebs — “Design Slop”*, аудита большого числа AI/SaaS-лендингов, материалов типа developersdigest и смежной критики AI-generated web design.  
> Там, где я реконструирую вероятный исходный список, я помечаю это как **реконструкцию**. Все новые паттерны и правила разделяются на:
> - **SOURCE-BACKED / HIGH CONFIDENCE** — широко наблюдаемые паттерны;
> - **HYPOTHESIS / MEDIUM/LOW CONFIDENCE** — наши исследовательские гипотезы, требующие валидации на датасете.

---

# 0. EXECUTIVE SUMMARY

## Главный вывод

**AI Design Slop — это не “плохой дизайн” и не конкретный набор запрещённых приёмов.**  
Это дизайн, который:

1. собран из статистически вероятных, AI-коррелированных визуальных клише;
2. не имеет осмысленной связи с продуктом, контентом, пользователем и задачей;
3. предсказуем до ощущения шаблона;
4. использует “премиальные”/“современные” сигналы вместо реальной иерархии, доказательности и ясности;
5. создаётся по логике **компонент → контент**, а не **контент → смысл → структура → форма**.

## Главная гипотеза подтверждается, но требует уточнения

Исходная гипотеза:

> «Anti-Slop — это не запрет определённых визуальных элементов. Это переход от генерации интерфейса по вероятностному шаблону к генерации интерфейса из контекста, смысла и намерения.»

После анализа её нужно уточнить:

> **Anti-Slop — это система доказательного проектирования, где каждое визуальное, структурное и контентное решение имеет прослеживаемую причину в контенте, пользователе, продукте, бренде и контексте.**

Ключевой вопрос системы:

> **«Почему это здесь?»**

Если ответ:  
**«Потому что так обычно выглядят современные AI-лендинги»** — это сигнал slop.

Если ответ:  
**«Потому что этот контент, пользователь, продукт, домен и задача требуют именно такого решения»** — это нормальный дизайн.

## Что нужно строить

Не component library.  
Не просто design system.  
Не просто linter.

Нужно строить:

> **Design Intelligence System (DIS)** — инфраструктуру принятия дизайн-решений, которая сочетает:
> - research database,
> - pattern taxonomy,
> - context engine,
> - design decision engine,
> - anti-slop rules engine,
> - design manifest,
> - composition engine,
> - diversity engine,
> - auditor,
> - AI reviewer,
> - static/vision/semantic analyzers,
> - integration with AI coding agents.

## MVP

Минимально ценный продукт:

1. **Anti-Slop Manifest schema** — machine-readable описание намерения, домена, аудитории, бренда, визуального языка, токенов, ограничений.
2. **Static Anti-Slop Linter** — анализ HTML/CSS/Tailwind/React/DOM по детерминированным правилам.
3. **Audit Report** — score по измерениям, список находок, confidence, объяснение, альтернативы.
4. **AI Reviewer Prompts** — набор вопросов и промптов для LLM-проверки семантики, контента и “почему это существует”.
5. **Context Profiles** — доменные профили: SaaS, medical, legal, fintech, e-commerce, education, gov, portfolio, gaming, dev tool.

Не нужно делать сразу:

- полноценный генератор сайтов;
- “оригинальность score” как абсолютную метрику;
- универсальный визуальный арбитр вкуса;
- огромную библиотеку компонентов;
- автоматическое наказание за любой градиент, серif, glow или cards.

---

# PART I — RESEARCH

---

# 1. Что такое “Design Slop”

**Design Slop** — это визуальный и структурный осадок, который возникает, когда интерфейс собирается не из конкретной продуктовой задачи, а из усреднённых, часто повторяющихся признаков “современного”, “премиального” или “конверсионного” сайта.

В случае AI-generated web design проблема усиливается тем, что модель:

- не понимает продукт;
- не понимает пользователя;
- не понимает бизнес-контекст;
- оптимизируется на поверхностные признаки “похожести на хороший сайт”;
- воспроизводит высокочастотные паттерны из обучающих данных;
- использует шаблонные формулировки и визуальные маркеры “премиальности”.

## Важное различие

### Плохой дизайн

Может быть:

- устаревшим;
- перегруженным;
- некрасивым;
- неудобным;
- низкокачественным по типографике;
- но при этом **не быть AI slop**.

Например, старый сайт районной библиотеки может быть наивным, но он не обязательно является нейрослопом.

### AI Slop

Может быть:

- визуально эффектным;
- “дорогим”;
- аккуратным;
- современным;
- технически гладким;
- но при этом **шаблонным, пустым и предсказуемым**.

То есть:

> **Slop ≠ ugly.**  
> **Slop = generic + predictable + semantically disconnected + AI-correlated.**

---

# 2. Исходное исследование Adrian Krebs: реконструкция и смысл

По доступному пониманию первоисточника и окружающего дискурса, ключевая идея работы:

> Современные AI-генераторы и быстрые SaaS-лендинги массово производят один и тот же визуально-маркетинговый язык: тёмный фон, свечение, градиенты, serif italic, огромные заголовки, стеклянные панели, pill-элементы, карточки, generic copy, marquee, абстрактные 3D-объекты и т.д.

Эти паттерны не плохи сами по себе.  
Проблема в том, что они становятся **дефолтным пучком**, который используется без причины.

## Заявленная логика исходного исследования

Если опираться на заявленную логику аудита большого числа лендингов:

1. берётся большое количество современных посадочных страниц;
2. выделяются повторяющиеся визуальные и структурные приёмы;
3. фиксируются паттерны, которые стали маркерами “типичного AI/SaaS-лендинга”;
4. показывается, что эти паттерны создают ощущение шаблонности и снижают доверие;
5. делается вывод, что проблема не в одном элементе, а в системе дефолтов.

## Реконструируемый список 16 паттернов

Ниже — вероятный состав исходного списка. Если точные формулировки у Krebs отличаются, их можно маппить на те же механизмы.

| # | Паттерн | Как проявляется | Почему это симптом |
|---|---|---|---|
| 1 | Centered hero | Заголовок по центру, подзаголовок, две кнопки, часто без продукта | Самый безопасный и частотный шаблон |
| 2 | Huge hero heading | Огромный display-заголовок, часто пустой по смыслу | Имитация “bold/premium” |
| 3 | Serif italic accent word | Одно слово в заголовке набирается курсивным серifом | Сигнал “утончённости” без причины |
| 4 | Gradient text / gradient CTA | Градиент на тексте или кнопке | Быстрый визуальный “вау-эффект” |
| 5 | Dark background + glow | Тёмный фон и светящиеся пятна/ореолы | Имитация технологичности и премиальности |
| 6 | Glassmorphism / glass navbar | Полупрозрачные панели, blur, floating nav | Тренд из дизайн-шотов и UI-концептов |
| 7 | Pill badges / chips | Овальные бейджи, статусы, labels | Имитация продукта/дашборда |
| 8 | Mono uppercase micro-labels | Маленькие моноширинные подписи капсом | Технический/премиальный декор |
| 9 | Feature card grid | 3–4 карточки: иконка + заголовок + текст | Стандартный блок “преимуществ” |
| 10 | Rounded cards + thin borders | Скруглённые карточки с тонкими обводками | Универсальный “современный” вид |
| 11 | Abstract 3D blobs | Абстрактные 3D-формы, шары, ленты | Декор без продуктовой связи |
| 12 | Generic stock/AI imagery | Стоковые люди, офисы, абстракции, сгенерированные люди | Заполнение места без информации |
| 13 | Logo marquee | Бегущая строка логотипов, часто слабых/фейковых | Имитация социального доказательства |
| 14 | Generic AI copy | “Seamless”, “unlock”, “transform”, “next-generation” | Пустой маркетинговый язык |
| 15 | Scroll animations everywhere | Появление каждого элемента, параллакс, декоративный motion | Имитация “динамичности” |
| 16 | Design-by-checklist | Hero → features → testimonials → pricing → FAQ → CTA | Сборка по шаблону вместо архитектуры |

**Статус:** реконструкция, но паттерны имеют высокую наблюдаемость в AI/SaaS-лендингах.

---

# 3. Анализ 16 паттернов: симптомы и глубинные причины

Эти 16 паттернов не являются независимыми атомами.  
Большинство из них — проявления нескольких глубинных причин.

## Паттерны можно сгруппировать в 4 класса

### A. Premium mimicry

Имитация “дорогого”/“технологичного” продукта.

Сюда относятся:

- dark background;
- glow;
- serif italic;
- gradient text;
- mono labels;
- glassmorphism;
- thin borders;
- huge heading.

**Глубинная причина:**  
Модель и шаблонный рынок путают визуальные сигналы премиальности с реальной ясностью, ценностью и идентичностью.

---

### B. Template structure

Шаблонная структура страницы.

Сюда относятся:

- centered hero;
- identical section rhythm;
- feature cards;
- checklist sections;
- logo marquee;
- CTA every section.

**Глубинная причина:**  
Страница строится не как ответ на пользовательские вопросы, а как последовательность стандартных блоков.

---

### C. Content substitution

Подмена реального содержания декоративными признаками.

Сюда относятся:

- generic copy;
- fake testimonials;
- fake stats;
- fake customer logos;
- badges instead of proof;
- abstract 3D вместо продукта.

**Глубинная причина:**  
Когда нечего сказать о продукте, дизайн заменяет содержание эстетическими сигналами.

---

### D. Decorative motion/effects

Декоративные эффекты без функции.

Сюда относятся:

- scroll animations everywhere;
- parallax;
- animated gradients;
- magnetic buttons;
- cursor effects;
- infinite marquee.

**Глубинная причина:**  
Движение используется как украшение, а не как коммуникация состояния, иерархии или действия.

---

# 4. Почему эти паттерны возникают

## 4.1. Психологические причины

### 1. Сигнал легитимности

Стартапы и AI-продукты часто хотят выглядеть “уже взрослыми”.  
Знакомые премиальные клише кажутся быстрым способом получить доверие.

### 2. Страх выглядеть “простым”

Простота и ясность ошибочно воспринимаются как “слишком обычно”.  
Поэтому добавляются эффекты, градиенты, blur, glow.

### 3. Визуальная конкуренция

В ленте, на шоте, в превью побеждает то, что быстро выглядит “впечатляюще”.  
Это стимулирует overdesign.

---

## 4.2. Маркетинговые причины

### 1. Конверсионные шаблоны

Рынок привык, что лендинг должен содержать:

- hero;
- social proof;
- features;
- testimonials;
- pricing;
- CTA.

Это превращается в механический чеклист.

### 2. Премиализация без продукта

Когда продукт ещё не имеет доказательств, дизайн пытается “продать” его через визуальную дороговизну.

### 3. Быстрое производство

AI-генерация снижает стоимость производства страниц.  
Это увеличивает количество шаблонных решений.

---

## 4.3. Причины со стороны AI

### 1. Training data bias

Модели обучаются на:

- SaaS-лендингах;
- Dribbble/Behance-шотах;
- Tailwind-примерах;
- template marketplaces;
- стартап-страницах;
- open-source UI-репозиториях.

Там много визуально эффектного, но мало глубокой продуктовой специфики.

### 2. Component library bias

shadcn/ui, Radix, Tailwind UI, hero-sections, cards, badges, pills — всё это удобно копировать.  
Модель выбирает то, что часто встречается и легко компилируется.

### 3. Screenshot/preference bias

Если модели или агенты оцениваются по “впечатляющему скриншоту”, они оптимизируются на:

- контраст;
- свечение;
- крупную типографику;
- градиенты;
- “премиальный” вид.

А не на:

- ясность;
- информационную архитектуру;
- доменную уместность;
- читаемость;
- доказательность.

### 4. Prompt bias

Пользователи часто пишут:

- “make it modern”;
- “clean and premium”;
- “dark and futuristic”;
- “like a startup landing”;
- “make it pop”.

Эти запросы не содержат продуктовой конкретики, поэтому модель усредняет.

### 5. Lack of negative constraints

Модель не знает, что именно **не нужно** делать, если это не указано.  
Она выбирает наиболее вероятный “хороший” вариант.

---

# 5. Почему LLM особенно часто воспроизводят эти решения

## Причинно-следственная модель

```
Огромный объём SaaS/Tailwind/Dribbble данных
        ↓
Высокочастотные визуальные паттерны
        ↓
Модель учится: “так выглядит современный сайт”
        ↓
Пользователь просит “modern / premium / clean”
        ↓
Модель выбирает наиболее вероятный bundle
        ↓
Кодовые агенты легко реализуют это через Tailwind/shadcn
        ↓
Получается визуально знакомый, но безликий результат
        ↓
Пользователь принимает это за “хороший дизайн”
        ↓
Подобные примеры снова попадают в данные
        ↓
Цикл усиливается
```

## Ключевые механизмы

### 1. Вероятностная шаблонность

Модель не проектирует. Она предсказывает наиболее вероятное продолжение.  
“Современный лендинг” для неё — это статистический центр распределения.

### 2. Отсутствие продуктовой семантики

Модель не знает:

- чем продукт реально отличается;
- какие у пользователя страхи;
- какие доказательства нужны;
- какие разделы действительно нужны;
- какой домен требует осторожности.

### 3. Оптимизация на поверхностную красоту

Если цель — “чтобы выглядело круто”, модель даст:

- glow;
- gradient;
- dark mode;
- huge type;
- glass;
- cards.

Потому что это часто коррелирует с “круто” в обучающих данных.

### 4. Лёгкость реализации

Многие slop-паттерны легко выразить кодом:

- `bg-gradient-to-r`;
- `backdrop-blur`;
- `rounded-2xl`;
- `shadow-2xl`;
- `text-transparent bg-clip-text`;
- `border-white/10`;
- `tracking-widest uppercase`.

Это делает их особенно “липкими” для AI coding agents.

---

# 6. Критика и ограничения исходного исследования

Исходную идею нельзя принимать без критики.

## Ограничения

### 1. Возможная выборка смещена в сторону SaaS

Если аудит опирался в основном на стартап-лендинги, часть паттернов может быть не “AI slop вообще”, а “SaaS landing slop”.

### 2. Корреляция не равна вине

Градиент, serif или cards могут быть уместны.  
Нельзя считать элемент вредным только потому, что он часто встречается в плохих примерах.

### 3. Риск вкусовщины

Без контекста легко скатиться в:

- “тёмное — плохо”;
- “серif — плохо”;
- “анимация — плохо”;
- “карточки — плохо”.

Это уже анти-дизайн догматизм.

### 4. Не все 16 паттернов равнозначны

Некоторые — самостоятельны.  
Другие — только симптомы более глубоких причин.

### 5. Оригинальность нельзя измерить напрямую

Можно измерять:

- частотность паттернов;
- структурное сходство;
- визуальную похожесть;
- клишированность текста.

Но нельзя абсолютно измерить “оригинальность”.

---

# PART II — NEW TAXONOMY

---

# 7. Иерархия проблемы: от корневых причин к восприятию

```
ROOT CAUSES
│
├── AI imitates statistically common “premium/modern”
├── Design education by template marketplaces
├── Lack of product understanding
├── Speed over intent
├── Optimization for screenshot impression
└── Content emptiness / lack of proof
        ↓
DESIGN BEHAVIORS
│
├── Premium mimicry
├── Design-by-checklist
├── Decoration instead of information
├── Component-first composition
├── Motion as filler
└── Semantic substitution
        ↓
VISUAL PATTERNS
│
├── glow
├── gradient text
├── serif italic accent
├── dark + neon
├── glass panels
├── mono micro-labels
├── huge display type
└── gradient borders
        ↓
COMPONENT PATTERNS
│
├── icon + title + text cards
├── pill badges
├── floating glass navbar
├── rounded containers
├── logo marquee
└── generic CTA buttons
        ↓
PAGE PATTERNS
│
├── centered hero
├── identical section rhythm
├── features/testimonials/pricing checklist
├── repeated card grids
└── predictable narrative
        ↓
USER PERCEPTION
│
├── template recognition
├── distrust
├── fatigue
├── reduced comprehension
├── feeling of artificiality
└── lower perceived credibility
```

---

# 8. Расширенная таксономия AI Design Slop

Ниже — расширенная классификация. Для каждой категории:

- примеры;
- как детектировать;
- почему это возникает;
- когда это может быть уместно.

---

## A. Typography Slop

### Паттерны

1. **Serif + sans pairing без причины**
2. **Italic accent word**
3. **Гигантские hero-заголовки**
4. **Чрезмерный letter-spacing**
5. **All-caps labels**
6. **Mono labels как декор**
7. **Одинаковая иерархия заголовков**
8. **Декоративная типографика вместо информационной**
9. **Слишком много контрастных стилей в одном экране**

### Почему это slop

Типографика начинает играть роль “украшения”, а не структуры.  
Пара серif + sans становится не редакторским решением, а поверхностным сигналом “дизайнерскости”.

### Детекторы

- наличие `font-style: italic` внутри `h1/h2`;
- serif-шрифт только в одном слове заголовка;
- экстремально крупный `font-size` при слабом контенте;
- высокий процент `text-transform: uppercase`;
- использование `tracking-widest` для микроlabels без функциональной роли;
- одна и та же иерархия в разных секциях.

### Когда может быть уместно

- editorial/fashion/luxury — serif уместен;
- dev tool — mono уместен для кода, статусов, логов;
- крупный заголовок уместен, если он несёт конкретный смысл, а не просто “Make it big”.

---

## B. Color Slop

### Паттерны

1. **Purple/blue gradients**
2. **Neon accents**
3. **Dark background + glowing accent**
4. **Orange/purple combinations**
5. **Gradient text**
6. **Gradient blobs**
7. **“AI blue”**
8. **“Startup purple”**
9. **Fake premium palettes**

### Почему это slop

Цвет становится не системой ролей и не брендом, а быстрым сигналом “технологичности”.

### Детекторы

- градиенты на тексте;
- `from-purple-* to-blue-*`;
- высоконасыщенные акценты на тёмном фоне;
- свечения без источника смысла;
- палитра без связи с брендом.

### Когда может быть уместно

- gaming;
- entertainment;
- creative tech;
- brand-driven продукты;
- dark tools для разработчиков, если тёмная тема функциональна.

---

## C. Effects Slop

### Паттерны

1. **Glow**
2. **Blur**
3. **Glassmorphism**
4. **Excessive shadows**
5. **Gradient borders**
6. **Glowing cards**
7. **Radial light sources**
8. **Frosted panels**
9. **Noise overlays**
10. **Grain**
11. **Excessive backdrop-filter**

### Почему это slop

Эффекты создают ощущение “глубины” и “премиальности”, но не объясняют контент.

### Детекторы

- `box-shadow` с большим blur и цветным свечением;
- `backdrop-filter: blur()`;
- `border-image`/gradient borders;
- noise/grain overlay без брендовой причины;
- множественные полупрозрачные слои.

### Когда уместно

- если эффект помогает разделить слои информации;
- если это часть брендовой системы;
- если это нужно для состояния фокуса, глубины, модалки;
- если домен действительно ожидает неоновой/игровой эстетики.

---

## D. Layout Slop

### Паттерны

1. **Centered hero**
2. **Enormous empty space**
3. **Identical section rhythm**
4. **Predictable 12-column layouts**
5. **Repeated card grids**
6. **Symmetrical compositions**
7. **Floating UI**
8. **Excessive rounded containers**
9. **Dashboard-like everything**
10. **Одинаковые вертикальные отступы между всеми секциями**

### Почему это slop

Композиция не отражает смысл. Она просто “выглядит как лендинг”.

### Детекторы

- подряд идущие секции с одинаковой структурой;
- центрирование большинства блоков;
- повторяющиеся карточные сетки;
- отсутствие асимметрии даже там, где она полезна;
- каждая секция = заголовок + текст + карточки.

### Когда уместно

- центрированный hero для события, бренда, простого действия;
- карточные сетки для каталогов, сравнимых объектов;
- симметрия для институционального стиля.

---

## E. Component Slop

### Паттерны

1. **Repeated cards**
2. **Icon + title + paragraph cards**
3. **Feature cards**
4. **Numbered cards**
5. **Pill buttons**
6. **Badges**
7. **Chips**
8. **Fake status indicators**
9. **Excessive rounded containers**

### Почему это slop

Компоненты используются не потому, что они подходят содержанию, а потому что они доступны и часто встречаются.

### Детекторы

- большое количество однотипных карточек;
- иконка + заголовок + абзац как единственный способ подачи;
- бейджи без реального статуса;
- pill-кнопки везде без иерархии.

### Когда уместно

- карточки для повторяемых сущностей;
- бейджи для реальных статусов;
- chips для фильтров;
- pills для тегов, переключателей, категорий.

---

## F. Content Slop

### Паттерны

1. **Meaningless marketing language**
2. **“Revolutionize”**
3. **“Unlock”**
4. **“Transform”**
5. **“Seamless”**
6. **“Powerful”**
7. **“Next-generation”**
8. **“Built for the future”**
9. **Generic AI copy**
10. **Fake authority**
11. **Fake statistics**
12. **Generic testimonials**
13. **Fake customer logos**

### Почему это slop

Это самая опасная категория, потому что она разрушает доверие.  
Пустой текст невозможно компенсировать красивым дизайном.

### Детекторы

- высокая плотность абстрактных глаголов;
- отсутствие чисел, механизмов, деталей;
- тестимониалы без имени, роли, контекста;
- логотипы без объяснения отношений;
- фразы, которые можно подставить в любой продукт.

### Тест на slop

> Если заменить название продукта на название конкурента, и текст всё ещё звучит так же — это сильный признак content slop.

### Когда уместно

Почти никогда в чистом виде.  
Но универсальные формулировки допустимы, если они дополнены конкретикой.

---

## G. Interaction Slop

### Паттерны

1. **Ненужные hover-анимации**
2. **Scroll-triggered animations везде**
3. **Бесцельный параллакс**
4. **Magnetic buttons**
5. **Cursor effects**
6. **Animated gradients**
7. **Entrance animation для каждого элемента**
8. **Infinite marquee**
9. **Декоративный motion**

### Почему это slop

Движение перестаёт быть сигналом и становится шумом.

### Детекторы

- много `IntersectionObserver` reveal-анимаций;
- анимации без изменения смысла/состояния;
- бесконечные marquee;
- hover-эффекты, не улучшающие понимание.

### Когда уместно

- анимация состояния;
- анимация загрузки;
- анимация перехода между контекстами;
- анимация подтверждения действия;
- лёгкий вход для фокуса, если не мешает.

---

## H. Image Slop

### Паттерны

1. **Unsplash hero photos**
2. **Abstract 3D blobs**
3. **Generic AI-generated people**
4. **Fake office photography**
5. **Abstract technology imagery**
6. **Декоративные объекты без связи с продуктом**
7. **Стоковые фото ради заполнения места**

### Почему это slop

Изображение не несёт информации. Оно просто занимает визуальное поле.

### Детекторы

- абстрактные 3D-объекты без продуктовой функции;
- стоковые “улыбающиеся команды”;
- изображения, которые можно подставить в любой сайт;
- отсутствие продукта, процесса, данных, людей, контекста.

### Когда уместно

- брендовая иллюстрация с системой;
- реальный продукт;
- реальные люди;
- схемы, графики, интерфейсы;
- предметная съёмка.

---

## I. Navigation Slop

### Паттерны

1. **Floating glass navbar**
2. **Excessive pill navigation**
3. **Hamburger там, где не нужен**
4. **Oversized CTA**
5. **Идентичная навигационная архитектура на всех сайтах**

### Почему это slop

Навигация строится не по информационной архитектуре, а по визуальному дефолту.

### Детекторы

- стеклянный плавающий navbar без причины;
- одни и те же пункты: Product, Features, Pricing, About, Contact;
- меню, не отражающее реальную структуру продукта.

### Когда уместно

- лёгкая навигация на длинных страницах;
- sticky nav при реальной потребности;
- glass, если это часть языка бренда.

---

## J. “Premium SaaS” Slop

Это **не отдельный паттерн**, а **мета-паттерн**.

### Bundle

```
dark background
+ serif italic accent
+ huge heading
+ glow
+ rounded cards
+ gradient
+ mono labels
+ floating navbar
+ marquee
+ abstract 3D object
```

### Почему это мета-паттерн

Ни один элемент по отдельности не является критической проблемой.  
Проблема в их **статистической совместной повторяемости**.

Это можно назвать:

- **Premium AI Default Bundle**
- **Generic Startup Aesthetic**
- **Artificial Premiumness**

### Детектор

Если на одной странице одновременно присутствуют 4–6 элементов из пучка без явной брендовой/доменной причины, вероятность slop резко растёт.

---

# 9. META-SLOP

Это ошибки, которые невозможно свести к одному визуальному компоненту.

## 1. Predictability

Пользователь заранее знает, что будет дальше:

- сейчас карточки;
- сейчас отзывы;
- сейчас pricing;
- сейчас большой CTA.

**Почему плохо:**  
Страница становится скучной и не удерживает внимание.

---

## 2. Template Recognition

Сайт ощущается как “один из тысяч”.

**Почему плохо:**  
Вызывает недоверие и ощущение массового производства.

---

## 3. Aesthetic Over Function

Эффект существует ради эффекта.

**Пример:**  
blur-панель, которая ухудшает читаемость.

---

## 4. Semantic Disconnect

Визуальный элемент не связан с продуктом.

**Пример:**  
абстрактный 3D-шар для юридической платформы.

---

## 5. False Originality

Сайт выглядит “необычно”, но эта необычность собрана из стандартных приёмов.

**Пример:**  
“неоновый брутализм”, состоящий из тех же gradient/glow/mono/pill.

---

## 6. Excessive Consistency

Всё слишком идеально согласовано, слишком гладко, слишком стерильно.

**Почему плохо:**  
Отсутствие человеческого акцента может создавать ощущение синтетики.

---

## 7. Component Homogenization

Весь интерфейс построен из одинаковых карточек.

**Почему плохо:**  
Разный контент начинает выглядеть одинаково.

---

## 8. Decorative Density

Слишком много декоративных элементов: шум, свечение, градиенты, анимации, слои.

**Почему плохо:**  
Перегружает восприятие.

---

## 9. Narrative Absence

Страница состоит из блоков, но не рассказывает историю и не ведёт аргументацию.

**Почему плохо:**  
Пользователь не понимает, зачем ему это.

---

## 10. Design-by-Checklist

AI выполняет список:

- hero;
- features;
- cards;
- testimonials;
- pricing;
- CTA;
- footer.

Вместо того чтобы спроектировать интерфейс под конкретный продукт.

---

# 10. Почему 16 паттернов недостаточно

16 паттернов — это хороший первый слой, но они описывают в основном **визуальные симптомы**.

Нужны ещё уровни:

1. **Корневые причины**  
   Почему вообще возникает slop.

2. **Поведенческие паттерны**  
   Как система/модель принимает решения.

3. **Семантические паттерны**  
   Где отсутствует связь с продуктом.

4. **Структурные паттерны**  
   Как страница организована.

5. **Восприятие пользователя**  
   Как это влияет на доверие, понимание, конверсию.

---

# 11. Причины: почему AI-агенты создают именно такие сайты

## 1. Training data

Модели обучались на огромном количестве:

- SaaS landing pages;
- template galleries;
- UI kits;
- Dribbble/Behance shots;
- Tailwind examples;
- component docs;
- startup pitch pages.

Там много “визуально современного”, но мало:

- доменной специфики;
- реальных доказательств;
- редакционной структуры;
- уникальной аргументации.

---

## 2. Tailwind ecosystem

Tailwind сам по себе не плох.  
Но он ускоряет использование частотных утилит:

- `rounded-2xl`;
- `bg-gradient-to-r`;
- `backdrop-blur`;
- `shadow-lg`;
- `text-transparent bg-clip-text`;
- `tracking-widest`;
- `uppercase`;
- `border-white/10`.

Это делает шаблонные паттерны особенно лёгкими для воспроизведения.

---

## 3. Component libraries

shadcn/ui и похожие библиотеки хороши, но они:

- дают готовые компоненты;
- не дают дизайн-мышления;
- не отвечают на вопрос “почему именно этот компонент здесь нужен”.

---

## 4. Dribbble / Behance aesthetics

Эти площадки исторически поощряют:

- визуальный эффект;
- концептуальную красоту;
- компактные шоты;
- “вау” за 2 секунды.

Но не обязательно поощряют:

- информационную архитектуру;
- реальный контент;
- доменную уместность;
- доступность;
- долгосрочную читаемость.

---

## 5. Benchmark optimization

Если AI оценивают по:

- “выглядит современно”;
- “похож на стартап”;
- “красивый скриншот”;
- “нравится большинству”;

то система будет оптимизироваться под поверхностные признаки.

---

## 6. Screenshot-based evaluation

Скриншот не показывает:

- смысл;
- качество контента;
- достоверность;
- нарратив;
- уместность;
- пользовательский путь.

---

## 7. Reinforcement / preference optimization

Если люди чаще лайкают/одобряют “яркое и премиальное”, модель закрепляет это как “хорошее”.

---

## 8. User prompting

Пользователи часто не формулируют:

- продукт;
- аудиторию;
- тон;
- доказательства;
- ограничения;
- контент;
- сценарии.

Они говорят:

> “Сделай красиво и современно”.

И модель выдаёт наиболее вероятный “красивый современный” шаблон.

---

# 12. False positives: что не является slop автоматически

Очень важный раздел.  
Без него система превратится в догматический анти-дизайн.

## Не является автоматическим slop

| Элемент | Когда это нормально |
|---|---|
| Градиент | Брендовый переход, инфографика, глубина, продуктовый акцент |
| Карточки | Повторяемые сравнимые сущности: товары, вакансии, статьи, тарифы |
| Serif | Редакционный стиль, мода, культура, люкс, издательский продукт |
| Glow | Игровой продукт, киберспорт, сцена, бренд с неоновым языком |
| Dark mode | Dev tools, media, профессиональные инструменты, ночные сценарии |
| Rounded corners | Дружелюбный потребительский продукт, детский/здоровый/мягкий бренд |
| Анимация | Состояния, переходы, объяснение процесса, обратная связь |
| Марки/бейджи | Реальные статусы, метки, версии, категории |
| Крупный заголовок | Сильный месседж, редакционный акцент, брендовый вход |
| Центрированная композиция | Простое действие, событие, манифест, бренд-страница |

---

# 13. Контрпримеры: почему “современный” не значит “slop”

Нужно искать сайты, которые:

- выглядят современно;
- но не выглядят AI-generated.

## Типы таких сайтов

### 1. Editorial / publishing

Почему не slop:

- типографика служит чтению;
- структура вытекает из статьи;
- изображения имеют смысл;
- нет нужды в карточных фейковых “фичах”.

### 2. Documentation / developer resources

Почему не slop:

- плотность информации;
- навигация по контенту;
- код как главный объект;
- функциональность выше декора.

### 3. Government / public services

Почему не slop:

- понятные действия;
- минимум декора;
- доменная уместность;
- ясность и доступность.

### 4. Craft / portfolio / product niche

Почему не slop:

- уникальные артефакты;
- реальные изображения;
- авторская композиция;
- конкретный голос.

### 5. E-commerce с реальной товарной плотностью

Почему не slop:

- карточки оправданы;
- изображения реальны;
- информация конкретна;
- структура обслуживает выбор.

---

# PART III — ANTI-SLOP MANIFESTO

---

# 14. Anti-Slop Design Manifesto

Ниже — не список запретов, а философия.

## 1. Смысл предшествует форме

Каждый экран, секция, компонент и визуальный эффект должны отвечать на вопрос:

> **Какую задачу это решает?**

Если ответ только “выглядит красиво” — это слабое основание.

---

## 2. Контент — первичный материал дизайна

Дизайн не должен маскировать пустоту.  
Если контента нет, дизайн не обязан заменять его градиентом.

---

## 3. Уместность важнее трендовости

То, что модно, не обязательно подходит.  
Домен, аудитория и продукт сильнее “современного вида”.

---

## 4. Иерархия важнее украшения

Если пользователь не понимает, что главное, страница проваливается, даже если она визуально богатая.

---

## 5. Повторение должно быть оправдано

Карточки, сетки и однотипные блоки хороши, когда контент действительно повторяем.  
Если контент разный — не нужно превращать его в одинаковые контейнеры.

---

## 6. Доказательства важнее декоративных сигналов

Вместо:

- “revolutionary”;
- “seamless”;
- “next-generation”;

лучше:

- как работает;
- какие ограничения;
- какие данные;
- какие результаты;
- какие реальные примеры.

---

## 7. Движение должно что-то сообщать

Анимация допустима, если она объясняет:

- состояние;
- переход;
- приоритет;
- связь;
- действие.

Декоративное движение без причины — кандидат на удаление.

---

## 8. Изображения должны нести информацию

Изображение хорошо, если оно показывает:

- продукт;
- процесс;
- людей;
- данные;
- контекст;
- доказательство.

Абстракция без причины — слабый элемент.

---

## 9. Типографика обслуживает чтение и смысл

Шрифтовая пара, размер, контраст и ритм должны помогать пониманию, а не просто “выгляддеть дизайнерски”.

---

## 10. Специфичность важнее универсальности

Если дизайн можно безболезненно переставить в любой другой продукт — он недостаточно специфичен.

---

## 11. Предсказуемость — не всегда плохо

Иногда знакомые паттерны полезны.  
Плохо, когда предсказуемость становится полной и пустой.

---

## 12. Anti-Slop не должен становиться новым slop

Если все начнут делать:

- только белый фон;
- только чёрный текст;
- только brutalist grids;
- только без анимаций;
- только без серifов;

это будет новый шаблон.

---

## 13. Главная метрика — не “нравится”, а “почему”

Дизайн-решение должно иметь причину:

- контентную;
- пользовательскую;
- брендовую;
- доменную;
- функциональную;
- доступностную.

---

# 15. Ключевые принципы в операционной форме

1. **Не добавляй элемент, если не можешь объяснить его роль.**
2. **Не используй премиальный сигнал как замену содержанию.**
3. **Не копируй структуру лендинга, если продукту нужна другая структура.**
4. **Не делай карточки из всего подряд.**
5. **Не анимируй всё, что можно анимировать.**
6. **Не ставь градиент, если он не имеет брендовой или функциональной причины.**
7. **Не прячь пустоту за шумом, свечением и blur.**
8. **Не путай “выглядит дорого” с “выглядит убедительно”.**
9. **Не создавай страницу по чеклисту секций.**
10. **Не позволяй визуальному языку становиться громче продукта.**

---

# 16. Контекстные правила

Один и тот же элемент может быть:

- **GOOD** в одном контексте;
- **SLOP** в другом.

Формула:

```
RULE
+ CONTEXT
+ INTENT
+ DOMAIN
+ AUDIENCE
= JUDGEMENT
```

## Примеры

### Glow

- **Gaming / киберспорт:** может быть уместен.
- **Медицинский сервис:** обычно неуместен.
- **Ночной диджейский ивент:** уместен.
- **Юридическая платформа:** почти наверняка спорен, если нет бренда.

### Serif

- **Мода / культура / издательство:** уместен.
- **Dev tool:** может быть не нужен, если нет редакционного тона.
- **Финтех:** возможен, если нужен институциональный/премиальный тон, но требует осторожности.

### Dark theme

- **Dev tool:** часто уместен.
- **Клиника:** обычно сомнителен как основной стиль.
- **Кино/музыка/игры:** уместен.

### Cards

- **E-commerce:** уместны.
- **Длинный редакционный лонгрид:** часто не нужны.
- **Сравнение тарифов:** уместны.
- **Уникальный нарратив:** могут мешать.

---

# 17. Исключения

Паттерн может быть разрешён, если есть хотя бы один сильный обоснователь:

1. **Брендовая система** прямо требует этого приёма.
2. **Доменная конвенция** делает его ожидаемым.
3. **Пользовательская задача** требует именно этого.
4. **Контент** структурно повторяем.
5. **Доступность** улучшается от этого решения.
6. **Продукт** имеет реальный визуальный объект, который поддерживает приём.

---

# PART IV — SYSTEM DESIGN

---

# 18. Anti-Slop Rules Engine

## Цель

Превратить философию в проверяемые правила.

## Структура правила

Каждое правило имеет:

```yaml
id:
category:
name:
severity:
detect:
why:
bad_example:
preferred_alternative:
exceptions:
confidence:
evidence_type:
```

---

## Пример правила в YAML

```yaml
id: TYPO-001
category: typography
name: Italic serif accent word
severity: medium
detect:
  - serif italic span inside sans-serif heading
  - italic emphasis limited to one word in hero heading
why:
  - highly correlated with generic AI premium landing pages
  - often decorative rather than semantic
bad_example:
  - "Build the future of seamless automation" with "seamless" in serif italic
preferred_alternative:
  - use typographic contrast structurally
  - emphasize meaning through size, position, or layout, not decorative italic serif
exceptions:
  - editorial brand voice
  - fashion/luxury/culture domain
  - explicit brand typography system
confidence: 0.75
evidence_type: source-backed + hypothesis
```

---

# 19. Ядро каталога правил

Ниже — операционное ядро. В продакшене каталог должен расширяться и калиброваться.

## Typography

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| TYPO-001 | Serif italic accent word | 1 слово в hero в серифном курсиве | medium | структурный контраст; editorial-бренд |
| TYPO-002 | Oversized empty hero | очень крупный заголовок без конкретики | medium | уменьшить размер, усилить содержание |
| TYPO-003 | Mono decorative labels | mono uppercase labels без функции | low | использовать только для кода/статусов |
| TYPO-004 | Serif+sans без причины | пара шрифтов без редакционной логики | medium | одна сильная система или осмысленная пара |
| TYPO-005 | Gradient heading | текст с градиентом | high | однотонный акцент, бренд-градиент по причине |

---

## Color

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| COLOR-001 | Purple/blue gradient CTA | градиент синий/фиолетовый на кнопке/заголовке | medium | брендовый цвет, конкретная роль |
| COLOR-002 | Dark + neon default | тёмный фон + неоновый акцент без причины | medium | домен/бренд/функциональная тёмная тема |
| COLOR-003 | Gradient text | градиент на тексте | high | использовать редко и только как бренд-сигнал |
| COLOR-004 | AI blue/violet palette | палитра из типичного AI-набора | medium | палитра из бренда/контента/домена |

---

## Effects

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| EFFECT-001 | Decorative glow | свечение без источника/функции | medium | свет как состояние/фокус/бренд |
| EFFECT-002 | Glass panels everywhere | много `backdrop-blur` | medium | только для слоёв, где нужна глубина |
| EFFECT-003 | Gradient borders | градиентные обводки карточек | medium | обычные границы, если нет причины |
| EFFECT-004 | Noise/grain overlay | шум как декор | low | брендовая текстура с причиной |

---

## Layout

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| LAYOUT-001 | Centered generic hero | hero по центру + 2 CTA + абстракция | high | объектный/редакционный/продуктный вход |
| LAYOUT-002 | Identical section rhythm | секции одинакового размера и структуры | medium | изменение ритма по смыслу |
| LAYOUT-003 | Repeated card grids | несколько одинаковых карточных сеток подряд | medium | editorial, таблицы, сплиты |
| LAYOUT-004 | Enormous empty space | большие пустые зоны без иерархии | low | воздух должен поддерживать фокус |

---

## Component

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| COMP-001 | Icon+title+text cards | карточки одного типа как единственный паттерн | medium | разные структуры подачи |
| COMP-002 | Fake badges/chips | бейджи без реального статуса | medium | только реальные статусы |
| COMP-003 | Pill buttons everywhere | pill-кнопки без иерархии | low | иерархия кнопок по задаче |
| COMP-004 | Dashboard-like everything | дашбордовые элементы в маркетинге | medium | только если продукт действительно дашборд |

---

## Content

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| CONTENT-001 | Generic verbs | unlock, revolutionize, transform, seamless | medium | конкретика, механизм, результат |
| CONTENT-002 | Fake stats | числа без источника | critical | реальные данные и источник |
| CONTENT-003 | Generic testimonials | отзывы без деталей/контекста | high | конкретные кейсы |
| CONTENT-004 | Logo marquee without proof | логотипы без объяснения отношений | medium | реальные клиенты + контекст |

---

## Motion

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| MOTION-001 | Scroll reveal everywhere | анимация появления каждого блока | medium | анимация только ключевых состояний |
| MOTION-002 | Infinite marquee | бесконечная строка без причины | low/medium | использовать для реальных динамических данных |
| MOTION-003 | Magnetic/cursor effects | декоративные курсорные эффекты | low | только если это часть бренда |

---

## Image

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| IMG-001 | Abstract 3D blob | 3D-абстракция без связи с продуктом | medium | продукт, схема, процесс |
| IMG-002 | Generic stock people | стоковые люди/офис | medium | реальные люди, контекст, продукт |
| IMG-003 | AI generic people | сгенерированные “идеальные” люди | medium | реальные фото или стилизованная система |

---

## Navigation

| ID | Паттерн | Триггер | Severity | Альтернатива / исключение |
|---|---|---|---|---|
| NAV-001 | Floating glass navbar default | стеклянный navbar без причины | low | обычный навбар по информационной архитектуре |
| NAV-002 | Identical nav structure | Product/Features/Pricing/About везде | medium | навигация по реальной структуре продукта |

---

## Meta / Bundle

| ID | Паттерн | Триггер | Severity | Альтернатива |
|---|---|---|---|---|
| META-001 | Premium AI bundle | 4+ из: dark, glow, serif italic, mono labels, gradient, floating nav, 3D | high | сократить до брендово-уместного ядра |
| META-002 | Design-by-checklist | hero/features/testimonials/pricing/FAQ без уникальных секций | high | структура из пользовательских вопросов |
| META-003 | Predictable path | страница полностью угадывается | medium | неожиданная, но осмысленная последовательность |
| SEM-001 | Semantic disconnect | визуальный элемент не связан с продуктом | high | заменить на продуктово-релевантный элемент |

---

# 20. Уровни нарушения

## Level 0 — Healthy

- мало коррелированных паттернов;
- элементы имеют причину;
- дизайн специфичен;
- нет ощущения шаблона.

**Пример:**  
тёмная тема у dev tool с реальным кодом, без glow-абстракций и пустых слоганов.

---

## Level 1 — Suspicious

Есть отдельный шаблонный паттерн, но он не критичен.

**Пример:**  
один градиент в CTA, но остальной контент конкретен.

---

## Level 2 — Sloppy

Несколько коррелирующих паттернов.

**Пример:**  
gradient text + dark background + generic cards + generic copy.

---

## Level 3 — Strong Slop

Сайт очевидно построен по AI-шаблону.

**Пример:**  
тёмный фон, серифный курсив, glow, floating navbar, marquee, feature cards, generic copy.

---

## Level 4 — Critical Slop

Страница почти полностью состоит из AI-тропов и пустого содержания.

**Пример:**  
все секции чеклистом, фейковые логотипы, фейковые отзывы, абстрактные 3D, ноль конкретики.

---

# 21. Anti-Slop Score

## Важно

Недостаточно одного числа.  
Нужен многомерный профиль.

## Измерения

1. **Typography Slop**
2. **Color Slop**
3. **Effects Slop**
4. **Layout Slop**
5. **Component Slop**
6. **Content Slop**
7. **Motion Slop**
8. **Image Slop**
9. **Navigation Slop**
10. **Template Slop**
11. **Semantic Disconnect**
12. **Predictability**

Для продукта можно сгруппировать в 10 шкал:

| Измерение | Вес |
|---|---:|
| Template / Meta Slop | 20% |
| Semantic Disconnect | 15% |
| Predictability | 12% |
| Layout Slop | 10% |
| Component Slop | 10% |
| Typography Slop | 8% |
| Color Slop | 8% |
| Content Slop | 7% |
| Motion Slop | 5% |
| Image Slop | 5% |

---

## Формула находки

Для каждого правила:

```
FindingScore =
  severity_weight
  × confidence
  × context_modifier
  × justification_modifier
```

Где:

### severity_weight

- low = 1
- medium = 3
- high = 6
- critical = 10

### confidence

- 0.0–1.0

### context_modifier

- domain-inappropriate: 1.25
- neutral: 1.0
- domain-congruent: 0.5
- brand-justified: 0.25
- explicitly justified: 0.1

### justification_modifier

- no reason provided: 1.0
- weak reason: 0.7
- strong reason: 0.2

---

## Общий счёт

```
DimensionScore = normalize(sum(FindingScore by dimension))
OverallScore = Σ DimensionScore × dimension_weight
+ bundle_penalty
```

Где `bundle_penalty` добавляется, если срабатывает мета-пучок:

- 3 из 6 элементов: +5
- 4 из 6: +10
- 5+: +18
- 6+ и нет обоснований: +25

---

## Интерпретация

| Диапазон | Уровень | Интерпретация |
|---|---:|---|
| 0–10 | Healthy | почти нет slop |
| 11–25 | Suspicious | отдельные шаблонные сигналы |
| 26–50 | Sloppy | несколько коррелирующих паттернов |
| 51–75 | Strong Slop | очевидный AI-шаблон |
| 76–100 | Critical Slop | почти полностью trope-driven page |

---

# 22. Design Decision Model

## Неправильная модель

```
“Давай добавим красивую карточку”
        ↓
контент подгоняется под карточку
```

## Правильная модель

```
What information needs to be communicated?
        ↓
What user job does it serve?
        ↓
What hierarchy is required?
        ↓
What interaction is required?
        ↓
What visual language supports this?
        ↓
Which component is appropriate?
```

Или короче:

```
Content → Meaning → Hierarchy → Structure → Visual Language → Component
```

---

## Reason Graph

Для каждого элемента нужно уметь восстановить цепочку:

```
Product Goal
    ↓
User Question / Job
    ↓
Content Object
    ↓
Information Priority
    ↓
Composition Pattern
    ↓
Component
    ↓
Visual Tokens
```

Если элемент не имеет цепочки — он кандидат на удаление.

---

# 23. Composition Patterns

Система должна быть выше компонентов.  
Главный уровень — **композиционные паттерны**.

## 1. Editorial Index

**Когда использовать:**  
много текста, статейный контент, нарратив.

**Состав:**

- заголовок;
- подзаголовок;
- лида;
- тело;
- врезки;
- подписи;
- ссылки.

**Почему анти-slop:**  
структура происходит из чтения, а не из карточек.

---

## 2. Narrative Section

**Когда использовать:**  
нужно провести пользователя через аргумент.

**Состав:**

- проблема;
- напряжение;
- механизм;
- доказательство;
- следствие.

---

## 3. Split Information Field

**Когда использовать:**  
слева объяснение, справа доказательство/интерфейс/данные.

**Пример:**  
слева описание модуля, справа скриншот/схема/код.

---

## 4. Dense Information Block

**Когда использовать:**  
спецификации, таблицы, сравнения, документация.

**Почему анти-slop:**  
плотность часто честнее декоративного воздуха.

---

## 5. Contextual Navigation

**Когда использовать:**  
длинная страница со сложной структурой.

**Суть:**  
навигация отражает реальное содержание, а не стандартное меню.

---

## 6. Product Anatomy

**Когда использовать:**  
нужно показать продукт по частям.

**Состав:**

- объект;
- выноски;
- подписи;
- детали;
- состояния.

---

## 7. Timeline

**Когда использовать:**  
процесс, онбординг, история, этапы.

---

## 8. Comparison

**Когда использовать:**  
тарифы, функции, альтернативы, до/после.

---

## 9. Long-form Explanation

**Когда использовать:**  
сложные концепции, исследования, объяснения.

---

## 10. Object-focused Hero

**Когда использовать:**  
главный герой — реальный объект: продукт, интерфейс, документ, схема.

**Противовес:**  
пустой centered hero со слоганом.

---

## 11. Asymmetric Information Layout

**Когда использовать:**  
нужно избежать шаблонной симметрии и создать иерархию.

---

## 12. Evidence Strip

**Когда использовать:**  
показать доказательства: цифры, логи, сертификаты, кейсы.

---

# 24. Design Vocabulary

Нужен словарь визуальных языков, но **не как пресеты**, а как контролируемые режимы.

## Базовые языки

| Язык | Суть |
|---|---|
| Editorial | чтение, текст, ритм, публикация |
| Technical | точность, код, данные, документация |
| Institutional | доверие, стабильность, ясность |
| Experimental | поиск, нестандартная композиция |
| Human | тепло, люди, истории, органика |
| Industrial | утилитарность, модульность, сыроватость |
| Quiet | сдержанность, воздух, низкий визуальный шум |
| Dense | высокая информативность |
| Playful | игра, характер, движение |
| Cinematic | атмосфера, крупный масштаб, сцены |
| Minimal | редукция к необходимому |
| Raw | необработанность, прямой показ материала |
| Crafted | рукотворность, детали, текстура |
| Scientific | данные, точность, графики |
| Luxury | материалы, дистанция, тонкость |
| Utilitarian | функция прежде всего |

---

## Пример атрибутов для нескольких языков

### Editorial

- **Typography:** сильный текстовый шрифт, выраженные размеры заголовков и лида
- **Spacing:** ритм чтения, достаточная ширина колонки
- **Density:** средняя
- **Hierarchy:** заголовок → лида → тело → врезки
- **Shape language:** прямоугольники, линейки, колонки
- **Borders:** тонкие, структурные
- **Imagery:** фото/иллюстрации по теме
- **Motion:** минимальный, только вход в чтение
- **Composition:** колонки, врезки, маргиналии
- **Interaction:** ссылки, сноски, якоря

### Technical

- **Typography:** sans/mono для данных
- **Spacing:** компактный, модульный
- **Density:** высокая
- **Hierarchy:** код/параметры/статусы
- **Shape language:** прямые углы или малый радиус
- **Borders:** явные
- **Imagery:** схемы, скриншоты, логи
- **Motion:** состояния, загрузка
- **Composition:** сплиты, таблицы, панели
- **Interaction:** копирование, фильтры, поиск

### Institutional

- **Typography:** нейтральная, надёжная
- **Spacing:** регулярная
- **Density:** средняя/высокая
- **Hierarchy:** понятные шаги
- **Shape language:** устойчивые формы
- **Borders:** умеренные
- **Imagery:** реальные люди, документы, здания
- **Motion:** минимальный
- **Composition:** сетка, предсказуемость
- **Interaction:** простые действия

### Human

- **Typography:** мягкая, возможно серif/sans с характером
- **Spacing:** свободный
- **Density:** низкая/средняя
- **Hierarchy:** история, голос
- **Shape language:** мягкие формы
- **Borders:** слабые или отсутствуют
- **Imagery:** реальные люди, эмоции
- **Motion:** мягкий
- **Composition:** асимметрия, нарратив
- **Interaction:** тактильная обратная связь

---

# 25. Design Diversity Engine

## Проблема

Если система просто запрещает slop, она может начать выдавать другой шаблон:

- белый фон;
- чёрный текст;
- без градиентов;
- без анимаций;
- без карточек.

Это будет **Anti-Slop Slop**.

## Решение

Нужен механизм **Controlled Diversity**.

---

## Входные данные

- контент;
- домен;
- бренд;
- аудитория;
- функциональные требования;
- визуальный язык;
- ограничения доступности;
- анти-slop правила.

---

## Выход

Не один вариант, а набор:

- Variant A
- Variant B
- Variant C
- Variant D

Все варианты должны быть:

- usable;
- coherent;
- accessible;
- semantic;
- brand-consistent;
- anti-slop compliant.

---

## Оси вариации

1. **Тип входа**  
   - object hero;
   - editorial hero;
   - split hero;
   - data hero.

2. **Плотность**  
   - sparse;
   - medium;
   - dense.

3. **Симметрия**  
   - symmetrical;
   - asymmetrical;
   - modular.

4. **Тип подачи**  
   - cards;
   - list;
   - table;
   - editorial blocks;
   - timeline.

5. **Визуальный язык**  
   - technical;
   - editorial;
   - human;
   - institutional.

6. **Уровень движения**  
   - none;
   - subtle;
   - expressive.

7. **Цветовая температура**  
   - warm;
   - neutral;
   - cool.

8. **Форма**  
   - sharp;
   - rounded;
   - mixed.

---

## Алгоритм

1. Сгенерировать N вариантов.
2. Каждый вариант прогнать через:
   - accessibility checks;
   - anti-slop rules;
   - brand constraints;
   - content fit;
   - usability heuristics.
3. Измерить взаимное расстояние между вариантами.
4. Выбрать те, что:
   - проходят проверки;
   - достаточно различаются;
   - не теряют ясность.

---

## Главная идея

> **Разнообразие должно быть управляемым, а не хаотичным.**

---

# 26. Архитектура Anti-Slop Design System

```
ANTI-SLOP CORE
│
├── Design Principles
├── Pattern Taxonomy
├── Detection Rules
├── Context Engine
├── Design Decision Engine
├── Typography System
├── Color System
├── Spacing System
├── Layout System
├── Interaction System
├── Component System
├── Content Guidelines
├── Image Guidelines
├── Motion Guidelines
└── Audit Engine
```

---

# 27. Design Manifest

Manifest — это machine-readable источник истины для AI-агентов и людей.

## Минимальная структура

```yaml
design_system:
  meta:
    id:
    version:
    generated_from:
    owner:
  intent:
    product:
    audience:
    domain:
    business_goal:
    user_jobs:
    content_evidence:
  philosophy:
    -
  visual_language:
    primary:
    secondary:
  typography:
    display:
    body:
    mono:
    scale:
    usage_rules:
  colors:
    palette:
    roles:
    contrast_rules:
    gradient_policy:
  spacing:
    scale:
    rhythm:
    density:
  geometry:
    radius:
    borders:
    shadows:
  layout:
    grid:
    max_width:
    section_rhythm:
  imagery:
    allowed:
    forbidden:
    preferred_subjects:
  motion:
    intensity:
    allowed_use_cases:
  composition:
    preferred_patterns:
    forbidden_defaults:
  components:
    cards:
    buttons:
    badges:
    nav:
  anti_slop:
    rules:
    exceptions:
    score_budget:
  accessibility:
    contrast:
    reduced_motion:
    focus_visibility:
  responsive:
    breakpoints:
```

---

## Пример фрагмента

```yaml
design_system:
  intent:
    product: "B2B invoice verification platform"
    audience: "finance operations managers"
    domain: "fintech / back-office"
    business_goal: "get demo request"
    user_jobs:
      - "understand how errors are caught"
      - "see proof of accuracy"
      - "evaluate integration effort"
  visual_language:
    primary: "technical"
    secondary: "institutional"
  typography:
    display: "neutral grotesque"
    body: "high-readability sans"
    mono: "for data and statuses"
  colors:
    gradient_policy: "not allowed except brand data visualization"
  anti_slop:
    rules:
      - id: META-001
        enabled: true
      - id: CONTENT-002
        enabled: true
        severity: critical
    exceptions:
      - pattern: dark_theme
        reason: "tool is used in low-light ops environments"
```

---

# 28. Почему система не должна быть component library

Компоненты — это строительные блоки.  
Главная проблема не в кнопках и карточках.

Главная проблема:

> **как компоненты комбинируются и почему.**

Поэтому система должна оперировать:

- композициями;
- нарративными структурами;
- информационными блоками;
- правилами использования;
- контекстом;
- причинами.

Компонентная библиотека может быть следствием, а не ядром.

---

# PART V — TOOLING

---

# 29. Anti-Slop Auditor

## Назначение

Принимать сайт или макет и говорить:

- что не так;
- почему это slop;
- насколько силён сигнал;
- какой паттерн сработал;
- какие альтернативы существуют.

---

## Входы

1. **URL**
2. **HTML**
3. **CSS**
4. **React/Vue code**
5. **Tailwind config**
6. **Design tokens**
7. **Screenshots**
8. **Content export**
9. **Brand manifest**

---

## Выходы

1. **Overall score**
2. **Dimension scores**
3. **Findings list**
4. **Confidence**
5. **Evidence**
6. **Alternatives**
7. **Context notes**
8. **Suggested revision plan**

---

## Pipeline аудитора

```
Input
  ↓
Ingestion
  ↓
Static Analyzer
  ↓
Visual Analyzer
  ↓
Semantic Analyzer
  ↓
Context Engine
  ↓
Rules Engine
  ↓
Score Engine
  ↓
Explanation Generator
  ↓
Report
```

---

# 30. Static analysis vs Visual analysis vs Semantic analysis vs Hybrid

## Static analysis

Что можно проверять без рендера:

- HTML-структура;
- семантические теги;
- заголовки;
- классы Tailwind;
- CSS properties;
- shadow DOM;
- повторяемость компонентов;
- количество секций;
- длина текста;
- список слов;
- использование `uppercase`, `italic`, `gradient`;
- border-radius;
- количество карточек;
- наличие `backdrop-filter`;
- animation names;
- marquee patterns.

**Плюсы:**  
детерминированность, скорость, низкая стоимость.

**Минусы:**  
не видит финальную визуальную композицию.

---

## Visual analysis

Что проверяется по скриншотам:

- glow;
- glass;
- gradient blobs;
- 3D shapes;
- visual symmetry;
- whitespace;
- contrast;
- visual hierarchy;
- composition similarity;
- image type;
- visual clutter;
- embedding similarity to known slop corpus.

**Плюсы:**  
видит реальный пользовательский опыт.

**Минусы:**  
нужны vision models, выше стоимость, возможны ошибки.

---

## Semantic analysis

Что проверяется по контенту:

- generic copy;
- пустые обещания;
- фейковые доказательства;
- нарратив;
- соответствие заголовков содержанию;
- специфичность;
- тон;
- структура аргументации.

**Плюсы:**  
ловит суть, а не только оболочку.

**Минусы:**  
часто требует LLM.

---

## Hybrid analysis

Самый сильный режим:

- статические сигналы;
- визуальные сигналы;
- семантические сигналы;
- контекст;
- манифест.

Пример:

- статически найден `backdrop-blur`;
- визуально подтверждена стеклянная панель;
- семантически панель не несёт информации;
- контекст: медицинский сервис;
- вывод: высокая вероятность неуместного glassmorphism.

---

# 31. Anti-Slop Linter

## Целевой CLI-интерфейс

```bash
anti-slop audit ./website
anti-slop lint ./src --manifest ./design/manifest.yaml
anti-slop review ./page.html --context domain=fintech
anti-slop generate-manifest --brief ./brief.md
anti-slop compare ./variantA ./variantB
```

---

## Пример вывода

```text
ANTI-SLOP AUDIT

Overall Score: 62/100
Level: Strong Slop

Dimension Scores:
- Template Slop: 78
- Semantic Disconnect: 64
- Predictability: 71
- Layout Slop: 55
- Component Slop: 60
- Typography Slop: 49
- Color Slop: 52
- Content Slop: 66
- Motion Slop: 38
- Image Slop: 57

Findings:

[META-001***REMOVED*** Premium AI bundle detected
Confidence: 0.88
Evidence:
  - dark background
  - glow behind hero
  - serif italic accent word
  - floating glass navbar
  - mono micro-labels
Suggestion:
  - reduce bundle to brand-relevant elements
  - replace abstract glow with product artifact

[TYPO-001***REMOVED*** Italic serif accent word
Confidence: 0.84
Evidence:
  - h1 contains span with serif italic
Suggestion:
  - use structural emphasis instead of decorative serif italic

[LAYOUT-003***REMOVED*** Three consecutive feature-card grids
Confidence: 0.90
Evidence:
  - section 3, 4, 5 use identical card grid structure
Suggestion:
  - introduce editorial split, comparison or timeline

[CONTENT-001***REMOVED*** Generic marketing phrase detected
Confidence: 0.79
Evidence:
  - "Unlock seamless transformation"
Suggestion:
  - replace with concrete mechanism and measurable outcome
```

---

# 32. AI Design Reviewer

## Назначение

Не просто находить паттерны, а задавать смысловые вопросы.

## Ключевые вопросы

1. **Почему этот элемент существует?**
2. **Какую информацию он сообщает?**
3. **Можно ли его удалить без потери смысла?**
4. **Специфичен ли этот паттерн для данного продукта?**
5. **Работает ли страница без этого эффекта?**
6. **Это решение вытекает из контента или из общего AI-эстетического шаблона?**
7. **Существует ли эта секция потому, что она нужна продукту, или потому что так принято в лендингах?**
8. **Есть ли доказательство, что пользователь поймёт страницу лучше благодаря этому элементу?**
9. **Если заменить продукт на конкурента, останется ли дизайн таким же?**
10. **Какой доменный контекст был проигнорирован?**

---

## Формат вывода для LLM-ревью

```json
{
  "findings": [
    {
      "id": "REVIEW-001",
      "target": "hero section",
      "question": "Why does this glow exist?",
      "verdict": "semantic_disconnect",
      "confidence": 0.82,
      "reason": "The glow does not relate to invoice verification or financial operations.",
      "alternative": "Use a data visualization or document processing preview as the focal object."
    ***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

# 33. Design System Generator

## Вход

- product description;
- brand;
- audience;
- domain;
- content;
- functional requirements;
- references;
- constraints.

## Выход

Не сайт.  
Сначала:

1. Research summary
2. Design intent
3. Visual direction
4. Design manifest
5. Tokens
6. Composition rules
7. Component rules
8. Anti-slop rules
9. Page architecture proposals

---

## Pipeline генератора

```
Brief
  ↓
Research / domain analysis
  ↓
Content inventory
  ↓
User jobs & questions
  ↓
Design intent
  ↓
Visual direction
  ↓
Design manifest
  ↓
Composition patterns
  ↓
Component rules
  ↓
Page architecture
  ↓
Implementation guidance
```

---

# 34. AI Coding Agent Integration

## Как это должно работать с Claude Code, Codex, Gemini, Cursor и т.д.

### Вариант 1: как контекст-файл

В репозитории:

```
/design
  manifest.yaml
  tokens.json
  compositions.yaml
  anti-slop/rules.yaml
  anti-slop/exceptions.yaml
```

Агент читает эти файлы как источник истины.

---

### Вариант 2: как lint gate

```bash
anti-slop lint ./src --fail-on high
```

Если проверка падает, агент обязан исправить.

---

### Вариант 3: как review loop

1. Агент генерирует страницу.
2. `anti-slop audit` выдаёт находки.
3. Агент получает находки как task list.
4. Агент вносит правки.
5. Повторный аудит.

---

## Пример pipeline

```
User brief
    ↓
Design Research Agent
    ↓
Design System Generator
    ↓
Anti-Slop Reviewer
    ↓
Page Architect
    ↓
Frontend Agent
    ↓
Visual Auditor
    ↓
Anti-Slop Auditor
    ↓
Revision
```

---

## Какие этапы можно автоматизировать

### Полностью детерминированно

- parsing HTML/CSS;
- проверка токенов;
- проверка классов;
- проверка контраста;
- проверка количества карточек;
- проверка повторяемости секций;
- проверка радиусов, теней, градиентов.

### Полуавтоматически

- визуальный анализ;
- определение композиционной похожести;
- кластеризация паттернов.

### Через LLM

- семантическая уместность;
- качество контента;
- нарратив;
- бренд-соответствие;
- объяснение альтернатив.

---

# 35. Design System as Code

## Рекомендуемая структура репозитория

```
/design
  manifest.yaml
  tokens.json
  typography.json
  colors.json
  spacing.json
  geometry.json
  compositions.yaml
  components/
    button.rules.yaml
    card.rules.yaml
    nav.rules.yaml
  patterns/
    hero.rules.yaml
    comparison.rules.yaml
    timeline.rules.yaml
  anti-slop/
    rules.yaml
    bundles.yaml
    exceptions.yaml
    scoring.yaml
  audits/
    audit-2026-09-29.json
  vocabulary/
    editorial.yaml
    technical.yaml
    institutional.yaml
```

---

# 36. Data Model

## Основные сущности

### Project

- id
- name
- domain
- audience
- brand_profile
- goals
- constraints

### Manifest

- id
- version
- project_id
- philosophy
- visual_language
- tokens
- anti_slop_config

### Page

- id
- project_id
- url
- content_inventory
- sections
- score

### Section

- id
- page_id
- type
- purpose
- content_objects
- composition_pattern
- findings

### Element

- id
- section_id
- role
- component
- styles
- justification

### Rule

- id
- category
- severity
- detect
- why
- alternatives
- exceptions

### Finding

- id
- rule_id
- page_id
- element_id
- confidence
- severity
- evidence
- context_modifier

### Audit

- id
- page_id
- timestamp
- scores
- findings
- recommendations

---

# 37. Технический стек

## Рекомендуемый стек

### Core

- TypeScript / Node.js
- CLI: commander / oclif
- Config: YAML / JSON Schema

### Static analysis

- HTML parser
- PostCSS
- csstree
- Tailwind class parser
- React/Vue AST parser

### Rendering / visual capture

- Playwright
- Puppeteer
- sharp
- canvas utilities

### Vision

- CLIP embeddings
- segmentation models
- OCR
- saliency detection
- color extraction

### LLM layer

- semantic review
- copy analysis
- explanation generation
- alternative suggestions

### Storage

- SQLite для локального использования
- PostgreSQL + pgvector для команды
- object storage для скриншотов

---

# 38. API

## Примеры эндпоинтов

### `POST /audit`

Вход:

```json
{
  "url": "https://example.com",
  "manifest_id": "optional",
  "context": {
    "domain": "fintech",
    "audience": "operations managers"
  ***REMOVED***
***REMOVED***
```

Выход:

```json
{
  "overall_score": 62,
  "level": "strong_slop",
  "dimensions": {***REMOVED***,
  "findings": [***REMOVED***
***REMOVED***
```

---

### `POST /manifest/generate`

Вход:

```json
{
  "product": "...",
  "audience": "...",
  "domain": "...",
  "content": "...",
  "brand": "..."
***REMOVED***
```

Выход:

- manifest.yaml
- tokens.json
- rules overrides

---

### `POST /review`

Вход:

- page html
- screenshot
- manifest

Выход:

- LLM review
- questions
- alternatives

---

### `GET /score`

Быстрый скоринг по набору признаков.

---

# 39. Plugin Architecture

## Типы плагинов

### Detectors

- typography detector
- color detector
- layout detector
- motion detector
- image detector
- content detector

### Context profiles

- fintech
- healthcare
- legal
- education
- gaming
- dev tools
- fashion
- gov

### Scorers

- weighted scorer
- bundle scorer
- predictability scorer

### Reporters

- CLI
- JSON
- HTML report
- Figma annotation
- GitHub PR comment

### Generators

- manifest generator
- composition variant generator
- copy reviewer

---

# PART VI — PRODUCT

---

# 40. Проверка на реальных сайтах

Чтобы система была честной, её нужно калибровать на реальной выборке.

## Рекомендуемая выборка

Нужно минимум несколько категорий:

1. **AI-generated landing pages**
2. **SaaS startup pages**
3. **Agency websites**
4. **Portfolio websites**
5. **Corporate websites**
6. **Editorial / magazine websites**
7. **Product / e-commerce websites**
8. **Government / public services**
9. **Documentation websites**
10. **Developer tool websites**

---

## Что нужно измерять

### 1. Частота паттернов

Какие паттерны встречаются чаще всего.

### 2. Совместная встречаемость

Какие паттерны образуют пучки.

### 3. Ложные срабатывания

Где правило ошибочно помечает нормальный дизайн.

### 4. Ложные пропуски

Где slop не распознаётся.

### 5. Контекстные исключения

Где паттерн уместен из-за домена.

### 6. Восприятие пользователями

- вызывает ли страница доверие;
- кажется ли шаблонной;
- кажется ли “сгенерированной”;
- понятна ли она.

---

## Метрики валидации

- Precision
- Recall
- F1
- Inter-rater agreement
- Calibration by domain
- False positive rate
- False negative rate

---

# 41. Оригинальность: честная модель

## Важное предупреждение

> **“Originality score” нельзя измерить абсолютно.**

Нельзя сказать:

> “Этот сайт на 87% оригинален.”

Это было бы псевдонаучно.

Но можно измерять **proxy metrics**.

---

## Proxy-метрики оригинальности

### 1. Pattern frequency

Насколько часто встречаются использованные паттерны.

### 2. Structural similarity

Насколько структура похожа на типовые шаблоны.

### 3. Component repetition

Насколько интерфейс гомогенизирован.

### 4. Visual embedding similarity

Насколько скриншот близок к корпусу известных AI-лендингов.

### 5. Template similarity

Сходство с известными template patterns.

### 6. Phrase similarity

Сходство текста с generic AI/marketing корпусом.

### 7. Composition similarity

Сходство композиционных схем с частотными макетами.

---

## Честная формулировка

Вместо:

> “Этот дизайн оригинален.”

Лучше:

> “Этот дизайн демонстрирует низкое сходство с известными шаблонными паттернами и высокую специфичность к продукту.”

---

# 42. Deterministic vs AI

## Можно и нужно делать детерминированно

### CSS / visual properties

- `border-radius`
- `box-shadow`
- `background-image: linear-gradient`
- `backdrop-filter`
- `font-family`
- `font-style: italic`
- `text-transform: uppercase`
- `letter-spacing`
- `animation`
- `filter: blur`
- `opacity`
- `color contrast`

### DOM structure

- число секций;
- число карточек;
- повторяемость карточек;
- глубина DOM;
- наличие `nav`, `hero`, `footer`;
- структура заголовков;
- количество кнопок;
- количество бейджей.

### Layout heuristics

- центрирование;
- симметрия;
- одинаковые отступы;
- одинаковая высота секций;
- число колонок;
- повторяемые сетки.

### Content heuristics

- длина заголовков;
- плотность стоп-слов;
- процент слов в верхнем регистре;
- число “универсальных” фраз;
- наличие цифр/доказательств.

---

## Требует AI / LLM

- semantic appropriateness;
- brand fit;
- narrative quality;
- intent alignment;
- whether an element is truly necessary;
- whether copy is specific;
- whether image relates to product;
- whether structure tells a coherent story.

---

## Требует Computer Vision

- glow detection by pixels;
- glassmorphism detection;
- abstract blob detection;
- stock photo detection;
- visual clutter;
- visual hierarchy saliency;
- composition embedding similarity;
- screenshot-level bundle detection.

---

## Главный принцип

> **LLM не должен принимать решения там, где можно использовать детерминированные правила.**

LLM нужен для:

- интерпретации;
- контекста;
- смысла;
- объяснений;
- генерации альтернатив.

Но не для базовой проверки `border-radius` или `box-shadow`.

---

# 43. Финальная архитектура продукта

```
ANTI-SLOP
│
├── Research Database
│   ├── pattern corpus
│   ├── site corpus
│   ├── annotations
│   └── evidence links
│
├── Pattern Taxonomy
│   ├── visual patterns
│   ├── component patterns
│   ├── page patterns
│   ├── content patterns
│   └── meta patterns
│
├── Design Manifest
│   ├── intent
│   ├── tokens
│   ├── rules
│   ├── exceptions
│   └── accessibility
│
├── Rules Engine
│   ├── static rules
│   ├── bundle rules
│   ├── severity rules
│   └── scoring rules
│
├── Context Engine
│   ├── domain profiles
│   ├── audience profiles
│   ├── brand constraints
│   └── intent constraints
│
├── Design Generator
│   ├── brief parser
│   ├── intent builder
│   ├── visual direction generator
│   └── manifest generator
│
├── Composition Engine
│   ├── content graph
│   ├── section planner
│   ├── layout selector
│   └── diversity optimizer
│
├── Component System
│   ├── usage rules
│   ├── anti-patterns
│   └── alternatives
│
├── AI Reviewer
│   ├── semantic questions
│   ├── brand fit review
│   └── copy review
│
├── Visual Auditor
│   ├── screenshot analysis
│   ├── embedding similarity
│   └── visual bundle detection
│
├── Code Auditor
│   ├── HTML/CSS lint
│   ├── React/Vue lint
│   └── token lint
│
├── Anti-Slop Linter
│   ├── CLI
│   ├── CI integration
│   └── reports
│
└── AI Coding Agent Integration
    ├── manifest as context
    ├── lint gate
    └── review loop
```

---

# 44. Описание модулей

## 1. Research Database

**Назначение:** хранить паттерны, примеры, доказательства, частотность.  
**Input:** сайты, скриншоты, разметка, аннотации.  
**Output:** справочник паттернов, корпус для калибровки.  
**Детерминированность:** частично.  
**Где нужен LLM:** разметка семантики.  
**Где нужен CV:** визуальная кластеризация.  
**Где нужен static analyzer:** сбор DOM/CSS признаков.

---

## 2. Pattern Taxonomy

**Назначение:** классификация всех видов slop.  
**Input:** исследования, находки, аудит.  
**Output:** онтология паттернов.  
**Детерминированность:** да, как структура данных.  
**LLM:** расширение и интерпретация.  
**CV:** визуальные паттерны.

---

## 3. Design Manifest

**Назначение:** источник истины для конкретного проекта.  
**Input:** brief, brand, content, domain.  
**Output:** YAML/JSON manifest.  
**Детерминированность:** частично.  
**LLM:** генерация и объяснение.

---

## 4. Rules Engine

**Назначение:** применять правила к странице.  
**Input:** DOM, CSS, tokens, content, manifest.  
**Output:** findings, scores.  
**Детерминированность:** высокая для статических правил.  
**LLM:** семантические исключения.  
**CV:** визуальные правила.

---

## 5. Context Engine

**Назначение:** учитывать домен, аудиторию, бренд.  
**Input:** manifest, metadata, user brief.  
**Output:** context modifiers.  
**Детерминированность:** частично.  
**LLM:** интерпретация доменной уместности.

---

## 6. Design Generator

**Назначение:** создавать не сайт, а дизайн-систему и направление.  
**Input:** brief, content, constraints.  
**Output:** manifest, tokens, composition rules.  
**Детерминированность:** низкая/средняя.  
**LLM:** нужен.  
**Где нужен static:** валидация токенов.

---

## 7. Composition Engine

**Назначение:** планировать структуру страниц.  
**Input:** content graph, manifest.  
**Output:** page architecture, variants.  
**Детерминированность:** частично.  
**LLM:** нарратив.  
**Алгоритмы:** constraint solving, diversity optimization.

---

## 8. Component System

**Назначение:** правила использования компонентов.  
**Input:** manifest, patterns.  
**Output:** component usage rules.  
**Детерминированность:** высокая.  
**Не является:** библиотекой компонентов как самоцелью.

---

## 9. AI Reviewer

**Назначение:** задавать смысловые вопросы.  
**Input:** page, manifest, findings.  
**Output:** review comments.  
**LLM:** обязателен.

---

## 10. Visual Auditor

**Назначение:** анализ скриншотов.  
**Input:** screenshots.  
**Output:** visual findings.  
**CV:** обязателен.

---

## 11. Code Auditor

**Назначение:** статический анализ кода.  
**Input:** HTML, CSS, React, Tailwind.  
**Output:** deterministic findings.  
**Static analyzer:** обязателен.

---

## 12. Anti-Slop Linter

**Назначение:** интеграция в CI/CLI.  
**Input:** проект.  
**Output:** pass/fail + report.  
**Детерминированность:** высокая.

---

# 45. MVP / V1 / V2

---

## MVP

Цель: быстро получить ценность без тяжёлой инфраструктуры.

### Входит

1. `manifest.yaml` schema
2. контекстные профили доменов
3. статический линтер:
   - Tailwind classes
   - CSS properties
   - DOM repetition
   - generic copy dictionary
   - heading structure
4. scoring по 10 измерениям
5. markdown/JSON report
6. набор LLM-промптов для review
7. интеграция в AI coding workflow как context file

### Не входит

- полноценный vision analyzer;
- автоматический генератор сайтов;
- оригинальность как абсолютная метрика;
- облачный SaaS;
- сложная база данных.

---

## V1

Цель: сделать систему практически полезной для команд.

### Входит

1. Playwright screenshots
2. визуальные эвристики:
   - color extraction;
   - whitespace estimation;
   - contrast;
   - repeated visual blocks.
3. bundle detection
4. context-aware exceptions
5. design manifest generator
6. composition recommendations
7. Figma/CI integration
8. HTML audit dashboard

---

## V2

Цель: зрелая Design Intelligence System.

### Входит

1. корпус размеченных сайтов
2. embeddings визуальных стилей
3. CV-модели для:
   - glow;
   - glass;
   - 3D blobs;
   - stock imagery;
   - composition similarity.
4. LLM semantic reviewer
5. diversity engine
6. generator of multiple page variants
7. team dashboard
8. API
9. plugin marketplace
10. continuous learning from accepted/rejected findings

---

# 46. Что НЕ нужно делать сейчас

1. Не делать компонентную библиотеку как ядро.
2. Не делать “запрет градиентов” как универсальное правило.
3. Не обещать абсолютный originality score.
4. Не строить полностью автоматический генератор финального сайта.
5. Не полагаться только на LLM.
6. Не превращать систему в эстетический трибунал.
7. Не игнорировать доменные исключения.
8. Не строить скоринг без confidence и объяснений.

---

# 47. Риски

## 1. Anti-Slop станет новым slop

Если система начнёт выдавать один и тот же “чистый” стиль.

**Решение:** diversity engine, контекст, вариативность.

---

## 2. Ложные срабатывания

Например, пометить нормальный dark dev tool как slop.

**Решение:** контекстные профили, исключения, ручное подтверждение.

---

## 3. Игнорирование бренда

Система может запретить приём, который является брендовым.

**Решение:** манифест с явными исключениями.

---

## 4. Переоценка визуальных сигналов

Можно слишком сильно наказывать за визуальные паттерны и недооценивать пустой контент.

**Решение:** высокий вес для content slop и semantic disconnect.

---

## 5. Gaming

Если метрика станет целевой, дизайнеры начнут “обходить” правила формально.

**Решение:** оценивать не только наличие элементов, но и причину, контент и пользовательское восприятие.

---

# 48. Design System vs Design System Generator vs Design Linter vs Design Intelligence System

| Категория | Что делает | Слабое место |
|---|---|---|
| Design System | Даёт готовые правила и компоненты | Может стать шаблоном |
| Design System Generator | Создаёт системы под проект | Может генерировать новые клише |
| Design Linter | Проверяет нарушения | Не понимает смысл без контекста |
| Design Intelligence System | Сочетает исследование, контекст, генерацию, проверку и обучение | Сложнее в производстве |

## Вывод

Самая сильная концепция — **Design Intelligence System**.

Потому что только она закрывает полный цикл:

```
Context → Intent → System → Composition → Implementation → Audit → Revision
```

---

# 49. Финальный философский принцип

## Кратко

> **Anti-Slop — это не эстетический запрет, а дисциплина причины.**

Каждый элемент обязан ответить:

- зачем он здесь?
- кому он нужен?
- какую информацию несёт?
- почему именно такой?
- что случится, если его убрать?
- соответствует ли он продукту и домену?

Если элемент существует только потому, что “так выглядит современный сайт”, — это слабый элемент.

---

# 50. Что мы реально должны построить

Ниже — конкретный ответ.

---

## 1. Что является ядром

Ядро — это **не компоненты**, а:

1. **таксономия slop-паттернов;**
2. **контекстно-зависимый rules engine;**
3. **design manifest как machine-readable источник истины;**
4. **модель принятия решений “почему это здесь”;**
5. **аудитор, который даёт объяснимый диагноз.**

Если совсем коротко:

> **Ядро = Context-Aware Design Reasoning Engine + Anti-Slop Rules Engine.**

---

## 2. Что входит в MVP

MVP должен включать:

1. манифест проекта;
2. статический линтер;
3. scoring по измерениям;
4. контекстные исключения;
5. отчёт с находками и альтернативами;
6. промпты для LLM-ревью;
7. интеграцию с AI coding agents как файл-контекст.

---

## 3. Что НЕ нужно делать сейчас

Не нужно делать:

1. полноценный генератор сайтов;
2. библиотеку компонентов как главный продукт;
3. абсолютный originality score;
4. визуальный арбитр “хорошо/плохо” без контекста;
5. тяжёлую CV-инфраструктуру до валидации правил;
6. публичный лидерборд “самый slop сайт” — это токсично и бесполезно.

---

## 4. Какие данные нужны

Нужны:

1. размеченный корпус сайтов;
2. скриншоты + DOM + CSS;
3. доменные категории;
4. аннотации паттернов;
5. примеры уместных исключений;
6. корпус generic copy vs specific copy;
7. примеры “современно, но не slop”;
8. feedback от дизайнеров и пользователей.

---

## 5. Какие правила должны быть deterministic

Детерминированными должны быть:

- проверка свойств CSS;
- проверка Tailwind-классов;
- проверка структуры DOM;
- подсчёт карточек;
- обнаружение повторяемых секций;
- проверка текста на длину и стоп-слова;
- проверка контраста;
- проверка `uppercase`, `italic`, `radius`, `shadow`, `gradient`;
- проверка количества анимаций;
- проверка структуры заголовков.

---

## 6. Где нужен AI

AI нужен для:

- семантической уместности;
- оценки контента;
- понимания бренда;
- нарратива;
- объяснения находок;
- генерации альтернатив;
- анализа “почему это не подходит продукту”.

---

## 7. Где нужен vision model

Vision нужен для:

- обнаружения визуальных пучков на скриншоте;
- определения glow, glass, blobs, stock imagery;
- оценки композиции;
- визуального сходства с шаблонами;
- выявления перегруженности;
- проверки того, что пользователь реально видит, а не что написано в коде.

---

## 8. Как выглядит manifest

Это декларативный машинно-читаемый файл, который содержит:

- цель продукта;
- аудиторию;
- домен;
- визуальный язык;
- токены;
- правила использования;
- исключения;
- анти-slop конфигурацию;
- требования доступности.

Пример минимально:

```yaml
design_system:
  intent:
    product: "invoice verification platform"
    audience: "finance operations managers"
    domain: "fintech"
  visual_language:
    primary: "technical"
  anti_slop:
    rules:
      - id: META-001
        enabled: true
      - id: CONTENT-002
        enabled: true
        severity: critical
```

---

## 9. Как выглядит audit

Audit — это:

- общий счёт;
- уровни по измерениям;
- список находок;
- confidence;
- evidence;
- альтернативы;
- рекомендации по исправлению;
- контекстные примечания.

Форматы:

- CLI;
- JSON;
- HTML report;
- PR comment;
- Figma annotations.

---

## 10. Как AI coding agent будет использовать систему

Сценарий:

1. Агент читает `/design/manifest.yaml`.
2. Агент планирует страницу по композиционным правилам.
3. Агент генерирует реализацию.
4. Запускается `anti-slop lint`.
5. Агент получает findings.
6. Агент исправляет нарушения.
7. Запускается AI reviewer.
8. Агент вносит смысловые правки.
9. Финальный аудит подтверждает соответствие.

---

## 11. Как система предотвращает превращение Anti-Slop в новый Slop

Через:

1. **запрет не элементов, а отсутствия причины;**
2. **контекстные исключения;**
3. **diversity engine;**
4. **вариативность композиций;**
5. **доменную уместность;**
6. **брендовые оправдания;**
7. **постоянную калибровку на реальных примерах;**
8. **оценку пользовательского восприятия, а не только правил.**

---

## 12. Как это может превратиться в самостоятельный продукт

Это может быть:

### 1. CLI для команд

`anti-slop lint` в CI.

### 2. SaaS-аудитор

Проверка сайта по URL и отчёт.

### 3. Плагин для Cursor / Claude Code

Дизайн-контекст и ревью прямо в агенте.

### 4. Figma plugin

Проверка макетов и аннотации.

### 5. API для платформ

Проверка и генерация манифестов.

### 6. Enterprise Design Intelligence Layer

Единый слой между:

- брендом;
- контентом;
- AI-агентами;
- фронтендом;
- аудитом.

---

# 51. Итоговый ответ

## Что мы должны построить

Мы должны построить не “анти-нейрослоп тему”, а **инфраструктуру дизайн-мышления для AI-эпохи**.

Это продукт класса:

> **Design Intelligence System**

Которая:

1. понимает контекст;
2. формулирует намерение;
3. порождает дизайн-систему;
4. управляет композицией;
5. запрещает беспричинные шаблоны;
6. проверяет код и визуал;
7. задаёт смысловые вопросы;
8. генерирует разнообразные, но осмысленные варианты;
9. не скатывается в новый догматизм;
10. работает как слой между человеком, брендом и AI-агентом.

---

## Финальная формула

```
AI Design Slop
        ↓
Pattern Taxonomy
        ↓
Root Cause Analysis
        ↓
Context-Aware Principles
        ↓
Rules Engine
        ↓
Design Decision Engine
        ↓
Manifest + Tokens + Composition
        ↓
Auditor + Reviewer
        ↓
Design Intelligence System
```

---

## И главный критерий качества

Не “красиво”.  
Не “современно”.  
Не “премиально”.

А:

> **“Это решение существует потому, что оно нужно именно здесь, именно этому продукту, именно этому пользователю, именно в этом контексте.”**

Если система умеет проверять и обеспечивать это — она решает задачу.


# ANTI-SLOP DESIGN SYSTEM: ГЛОБАЛЬНОЕ ИССЛЕДОВАНИЕ И АРХИТЕКТУРА СИСТЕМЫ

Это комплексный документ, объединяющий исследование феномена AI Design Slop, философский манифест, таксономию, архитектуру правил и спецификацию для создания **Design Intelligence System** (Системы Дизайнерского Интеллекта).

---

# PART I — RESEARCH: АНАТОМИЯ НЕЙРОСЛОПА

## 1. Executive Summary
**AI Design Slop** — это не просто «плохой дизайн». Это визуальный и структурный диалект, сформированный вероятностной природой LLM и диффузионных моделей, оптимизированный под усредненное представление о «премиальности» и «современности». Slop возникает, когда AI подменяет *процесс проектирования* (от смысла к форме) *процессом декорирования* (наложением статистически частых визуальных маркеров «крутости» на пустой каркас).

## 2. Деконструкция исследования Adrian Krebs и индустрии
Adrian Krebs и последующие аудиты (включая анализ 1590 лендингов) выделили 16 базовых паттернов. Но если мы посмотрим на них через призму **Root Cause Analysis**, мы увидим, что 16 паттернов — это лишь симптомы **3 фундаментальных ошибок AI**:

1.  **Aesthetic Over Function (Эстетика важнее функции):** AI не понимает, *что* он продает. Он знает лишь, что «темная тема + неон + glassmorphism» статистически коррелирует с высоким engagement в датасетах Dribbble/Behance.
2.  **Structural Homogenization (Структурная гомогенизация):** AI использует шаблон `Hero -> Marquee -> Bento Grid -> Testimonials -> CTA`, потому что это наиболее частая последовательность токенов в обучающей выборке Tailwind/React шаблонов.
3.  **Semantic Disconnect (Семантический разрыв):** Визуальные метафоры (например, 3D-абстракции или «магические» искры) не имеют связи с реальным продуктом.

## 3. Иерархия Slop (От причины к восприятию)

```text
ROOT CAUSE: Вероятностная генерация без семантического заземления
    ↓
AI BEHAVIOR: Имитация визуальных маркеров "премиальности" и "инновационности"
    ↓
DESIGN BEHAVIORS:
  - Максимизация визуального шума (glow, gradients)
  - Унификация структур (bento, cards)
  - Использование "безопасных" маркетинговых клише
    ↓
VISUAL PATTERNS (Симптомы):
  - Serif Italic Accent
  - Purple/Blue Gradients
  - Glassmorphism / Backdrop-blur
  - Floating UI / Pill Navbars
    ↓
USER PERCEPTION:
  - "Это выглядит как все остальные AI-сайты"
  - "Я не понимаю, что делает продукт, но он выглядит 'дорого'"
  - "Template Recognition" (Эффект зловещей долины в дизайне)
```

---

# PART II — NEW TAXONOMY: РАСШИРЕННАЯ КЛАССИФИКАЦИЯ

Мы не принимаем 16 паттернов как истину. Мы группируем их в **мета-паттерны** и выделяем скрытые slop-сигналы.

### A. Typography Slop (Типографический шум)
*   **The Italic Serif Interruption:** `Sans-serif Heading` + `<span class="italic serif">accent</span>`. (Маркер попытки AI сыграть на контрасте "технологичность + элитарность").
*   **Tracking Overload:** `tracking-[0.2em***REMOVED*** uppercase text-xs` для всех подзаголовков.
*   **Scale Shock:** Гигантские (120px+) hero-заголовки, которые несут 2 слова, при микроскопическом body-тексте.
*   **Mono-Labeling:** Использование моноширинного шрифта для бейджей (`[ BETA ***REMOVED***`, `[ NEW ***REMOVED***`) без причины (продукт не для разработчиков).

### B. Color & Light Slop (Световой и цветовой мусор)
*   **The "AI Orb":** Радиальные градиенты (размытые цветные пятна) на фоне, не имеющие источника света.
*   **Startup Purple / AI Cyan:** Доминирование `#7C3AED` (Purple) или `#06B6D4` (Cyan) как маркера "инновации".
*   **Gradient Text Abuse:** Градиентный текст на длинных абзацах (нарушение accessibility и читаемости).
*   **Fake Dark Mode:** Использование темно-серого фона (`#0A0A0A`) с белым текстом для B2B-сервиса, где требуется долгая работа с данными (вызывает fatigue).

### C. Effects & Material Slop (Материальный обман)
*   ** gratuitous Glassmorphism:** `backdrop-blur-md` на карточках, за которыми нет никакого контента для размытия (стекло без фона).
*   **Border Gradient:** Тонкие градиентные обводки (1px) вокруг карточек, которые исчезают на мобильных или при плохом мониторе.
*   **Inner Glow:** Тонкая внутренняя тень (inset shadow), имитирующая 3D-фаску, которая выглядит как артефакт рендера.

### D. Layout & Component Slop (Структурная лень)
*   **The Bento Trap:** Использование Bento-сетки для всего подряд, даже если информация линейна и не требует пространственного сравнения.
*   **Icon + Title + 2 Lines:** Бесконечные сетки из 3 или 4 карточек с иконкой (часто Lucide/Heroicons), заголовком и описанием.
*   **Marquee Logo Graveyard:** Бегущая строка с логотипами "компаний, которые нам доверяют" (часто выдуманных или нерелевантных).
*   **Floating Pill Navbar:** Навигация, оторванная от краев экрана, с сильным blur, которая перекрывает контент.

### E. Content & Interaction Slop (Смысловая пустота)
*   **The "Seamless" Lexicon:** Слова *Elevate, Unleash, Seamless, Next-Gen, Revolutionize, Crafted*.
*   **Decorative Motion:** Анимации появления (fade-in-up) для каждого элемента при скролле, замедляющие потребление информации.
*   **Fake Dashboard:** Скриншоты "дашбордов" в hero-секции, которые при увеличении оказываются бессмысленным набором UI-элементов и lorem ipsum.

### F. META-SLOP (Философские ошибки)
1.  **Design-by-Checklist:** AI генерирует секции не потому, что они нужны пользователю, а потому что они есть в "идеальном лендинге" (Hero -> Social Proof -> Features -> Pricing -> FAQ).
2.  **Narrative Absence:** Страница не ведет пользователя через проблему к решению. Это просто витрина компонентов.
3.  **False Originality:** Сайт выглядит "необычно" (например, brutalism или neo-brutalism), но это просто другой AI-шаблон, наложенный на контент.

---

# PART III — MANIFESTO: ANTI-SLOP DESIGN PHILOSOPHY

**Главный тезис:**
> *«Anti-Slop — это не запрет на градиенты, карточки или темные темы. Это отказ от вероятностного копирования в пользу семантического обоснования. Форма должна вытекать из контекста, а не из статистики Dribbble.»*

### 10 Принципов Anti-Slop
1.  **Intent Over Imitation (Намерение важнее имитации).** Каждый пиксель должен отвечать на вопрос "Зачем?". Если ответ "для красоты" — удали.
2.  **Information Density is a Feature (Плотность информации — это фича).** Не используй гигантские отступы и 3 карточки, если пользователь хочет увидеть таблицу сравнения из 10 пунктов.
3.  **Friction is Allowed (Трение допустимо).** Не всё должно быть "seamless". Иногда сложный график или длинный текст требуют остановки и вдумчивого чтения. Не прячь суть за анимациями.
4.  **Asymmetry implies Thought (Асимметрия подразумевает мысль).** Идеальная симметрия и 12-колоночные сетки — это дефолт. Нарушай сетку там, где контент требует акцента.
5.  **Typography is Structure, Not Decoration (Типографика — это структура).** Шрифт должен управлять вниманием, а не служить холстом для italic-акцентов.
6.  **Context Dictates Aesthetic (Контекст диктует эстетику).** Медицинский сервис не должен выглядеть как киберпанк-стартап.
7.  **Motion Must Communicate (Движение должно коммуницировать).** Анимация показывает причинно-следственную связь или изменение состояния. Декоративный parallax — зло.
8.  **No Phantom UI (Никаких фантомных интерфейсов).** Не рисуй фейковые дашборды и уведомления. Показывай реальный продукт или его точную схему.
9.  **Earn the Dark Mode (Заслужи темную тему).** Темная тема нужна для кинематографичности, фокуса или работы в темноте. Она не делает SaaS "премиальным" автоматически.
10. **Embrace the Mundane (Прими обыденность).** Настоящий дизайн часто выглядит скучно, потому что он невидим и эффективно решает задачу.

---

# PART IV — SYSTEM: АРХИТЕКТУРА ПРАВИЛ И ДВИЖКОВ

## 1. Context-Aware Rules Engine (Движок правил)
Правило не может быть бинарным (`glow = bad`). Оно должно быть контекстным.

```yaml
id: EFFECT-004
category: effects
name: Gratuitous Backdrop Blur (Glassmorphism)
severity: high
detect:
  css_properties: ['backdrop-filter: blur', 'background: rgba(..., 0.5)'***REMOVED***
  dom_context: ['card', 'navbar', 'modal'***REMOVED***
context_matrix:
  domain: [fintech, medical, legal, b2b-data***REMOVED***
  intent: [readability, trust, data-density***REMOVED***
  verdict: SLOP (Creates cognitive load, reduces contrast)
  
  domain: [gaming, entertainment, web3, events***REMOVED***
  intent: [immersion, atmosphere***REMOVED***
  verdict: ACCEPTABLE (If contrast ratio passes WCAG AA)
why: "Glassmorphism obscures underlying data. In data-heavy apps, it's a critical UX failure. In entertainment, it's a stylistic choice."
preferred_alternative: "Solid backgrounds with subtle borders or elevation shadows."
```

## 2. Design Decision Model (Модель принятия решений для AI)
Вместо `Prompt -> UI Components`, AI должен следовать цепочке:

1.  **Domain & Audience:** Кто пользователь? (Например, бухгалтер 50 лет).
2.  **Core Task:** Что он делает? (Сверяет транзакции).
3.  **Information Architecture:** Какие данные нужны на экране? (Таблицы, фильтры, статусы).
4.  **Visual Hierarchy:** Что важнее? (Ошибки и суммы).
5.  **Visual Language:** (High contrast, dense typography, minimal decoration).
6.  **Component Selection:** (Data Grid, Status Badges, Solid Panels).
    *   *Anti-Slop Check:* Нужен ли здесь glow? Нет. Нужен ли Bento? Нет.

## 3. Composition Patterns (Альтернатива Slop-секциям)
Система должна предлагать AI не "Hero Section", а паттерны композиции:
*   **Editorial Index:** Асимметричная сетка, крупная типографика, фокус на тексте (для блогов, манифестов).
*   **Diagnostic Split:** Экран разделен на "Проблему" (слева, плотно) и "Решение" (справа, визуально).
*   **Data-Dense Dashboard:** Утилитарный layout, минимальные отступы, фокус на таблицах и графиках.
*   **Object Anatomy:** Фокус на физическом или цифровом объекте с выносками (для hardware, сложных API).
*   **Timeline / Narrative:** Вертикальный или горизонтальный_storytelling_ без повторяющихся карточек.

---

# PART V — TOOLING: АУДИТ И АВТОМАТИЗАЦИЯ

## 1. Deterministic vs AI Analysis
Чтобы система была быстрой и дешевой, мы разделяем анализ.

### Deterministic Linter (CSS / DOM / HTML)
*Работает мгновенно, без LLM.*
*   **Color Slop:** Поиск специфических HEX-кодов (Startup Purple, AI Cyan) и градиентов с >3 стопами.
*   **Typography Slop:** Поиск `font-style: italic` + `font-family: serif` внутри `h1/h2`. Проверка `letter-spacing` > `0.15em`.
*   **Layout Slop:** Подсчет количества `border-radius` > `24px`. Подсчет `backdrop-filter`. Анализ DOM на наличие бегущих строк (`marquee`, `animate-scroll`).
*   **Content Slop:** Regex-поиск слов-паразитов (*seamless, elevate, unleash, revolutionize*).

### Vision & Semantic AI (LLM + CV)
*Требует мультимодальной модели.*
*   **Semantic Disconnect:** "Соответствует ли изображение тексту рядом с ним?"
*   **Predictability Score:** "Насколько структура этой страницы отличается от стандартного SaaS-шаблона?" (Сравнение embedding'ов структуры).
*   **Contextual Appropriateness:** "Уместен ли этот неоновый дизайн для сайта похоронного бюро?"

## 2. Anti-Slop CLI Auditor (Концепт)
```bash
$ npx anti-slop audit ./src/components --domain=b2b-fintech

[ANTI-SLOP AUDIT REPORT***REMOVED***
Score: 42/100 (Moderate Slop)

⚠️ [TYPO-001***REMOVED*** Italic Serif Accent detected in HeroHeading.tsx
   -> Confidence: 0.95 | Severity: High
   -> Fix: Remove italic serif, use weight/size contrast.

❌ [LAYOUT-04***REMOVED*** "Bento Grid" used for linear feature list
   -> Confidence: 0.88 | Severity: Medium
   -> Context: B2B Fintech requires scannability, not spatial exploration.
   -> Fix: Use alternating split-layout or dense data-list.

⚠️ [CONTENT-12***REMOVED*** Generic AI Copy detected: "Seamless integration"
   -> Fix: Specify WHAT integrates and HOW (e.g., "Syncs with Xero via API").
```

## 3. AI Reviewer (Socratic Prompting)
Интеграция в Cursor / Claude Code. Перед тем как AI сгенерирует код, он должен прогнать его через "Сократического Ревьюера":
*   *"Если я уберу этот градиент, потеряет ли пользователь информацию?"*
*   *"Могу ли я заменить эти 3 карточки на один маркированный список?"*
*   *"Я использую темную тему, потому что это требует бренд, или потому что я так привык?"*

---

# PART VI — PRODUCT: DESIGN INTELLIGENCE SYSTEM

Мы не делаем "еще один UI Kit". Мы создаем **Design Intelligence Layer** (Слой Дизайнерского Интеллекта), который работает *поверх* Tailwind, shadcn/ui, Radix и любых других библиотек.

## 1. Архитектура Продукта

```text
ANTI-SLOP INTELLIGENCE SYSTEM
│
├── 1. Context Engine (Input: Brief, Domain, Audience)
│      └─> Генерирует Design Constraints & Intent
│
├── 2. Manifest Generator (Output: design_manifest.yaml)
│      └─> Определяет токены, правила, запреты и паттерны
│
├── 3. Composition Engine
│      └─> Предлагает структурные layout'ы (не компоненты, а скелеты)
│
├── 4. Coding Agent Integration (Cursor/Claude/Copilot)
│      └─> System Prompt + Rules Injection
│
└── 5. Auditor (CI/CD Pipeline)
       └─> Блокирует PR, если нарушены детерминированные Anti-Slop правила
```

## 2. Формат Machine-Readable Manifest (`manifest.yaml`)
Этот файл читает AI-кодер перед началом работы.

```yaml
design_manifest:
  project: "MediCore B2B Portal"
  domain: "healthcare / data management"
  audience: "clinic administrators, 40+ y.o."
  
  philosophy:
    core_intent: "Trust, clarity, data-density"
    anti_slop_stance: "Strict utilitarian. No decorative motion. No dark mode."
    
  visual_language:
    aesthetic: "Institutional / Scientific"
    density: "High"
    shape_language: "Sharp (radius: 2px max)"
    
  rules:
    forbidden_patterns:
      - "glassmorphism"
      - "gradient_text"
      - "bento_grids"
      - "italic_serif_accents"
    required_patterns:
      - "data_tables"
      - "high_contrast_borders"
      - "system_fonts"
      
  typography:
    heading: "Inter (Weight 500, no tracking)"
    body: "Inter (Weight 400)"
    mono: "JetBrains Mono (Only for IDs and Codes)"
```

## 3. Проблема Originality (Как измерить неизмеримое)
Мы не можем измерить "креативность". Но мы можем измерить **Template Similarity Score (TSS)**.
*   **Алгоритм:** Мы парсим DOM-дерево и CSS-свойства сайта, превращаем их в вектор (embedding).
*   **База данных:** У нас есть 10,000 векторов популярных Tailwind/AI шаблонов.
*   **Метрика:** Если косинусное сходство вектора нового сайта с базой AI-шаблонов > 0.85 — сайт получает штраф за "Predictability".
*   **Решение:** AI должен намеренно вводить "контролируемую асимметрию" или "нетипичную плотность", чтобы сбить вектор сходства.

## 4. Предотвращение "Anti-Slop Slop"
Если мы запретим AI использовать градиенты и карточки, он начнет генерировать "Brutalist / Barebones Slop" (сырой HTML, черный текст на белом фоне, никаких отступов — потому что это тоже стало трендом в AI-кодинге).
**Решение:** Context Engine. Система не запрещает инструменты. Она запрещает *несоответствие инструмента задаче*.
*   *Gaming site?* Используй glow и неон. (Anti-Slop Score: 0).
*   *Accounting software?* Используй glow. (Anti-Slop Score: 90).

---

# ФИНАЛЬНЫЙ ВЫВОД: ЧТО МЫ РЕАЛЬНО ДОЛЖНЫ ПОСТРОИТЬ?

Мы должны построить **Design Intelligence Infrastructure** для AI-агентов.

### 1. Ядро (Core)
Набор YAML-манифестов и JSON-схем, которые описывают не "как выглядит кнопка", а "почему кнопка должна быть именно такой в этом контексте".

### 2. MVP (Что делаем прямо сейчас)
*   **CLI Linter:** Скрипт на Node.js/Python, который анализирует CSS/HTML/Tailwind-классы на наличие 20 самых частых детерминированных Slop-паттернов (Italic Serif, Glow, Bento, Startup Purple).
*   **Cursor Rules / System Prompts:** Готовый набор `.cursorrules` или промптов для Claude, которые заставляют AI-кодера следовать Design Decision Model и проходить Сократический аудит перед выдачей кода.
*   **Anti-Slop Figma Plugin:** Плагин, который подсвечивает "подозрительные" фреймы в макетах дизайнеров (например, "Вы использовали 3 разных радиуса скругления и градиентный текст. Уверены?").

### 3. Что НЕ нужно делать сейчас
*   Не нужно создавать свою UI-библиотеку компонентов (React/Vue). Это бессмысленно. Нужно учить AI правильно использовать *существующие* (shadcn, Tailwind, Radix).
*   Не нужно делать "оценку красоты". Только оценку семантического соответствия и структурной уникальности.

### 4. V1 (Генератор Манифестов)
Веб-интерфейс или CLI, где пользователь вводит: *"Сайт для логистической компании, B2B, интеграция с 1C"*.
Система выдает `manifest.yaml`, который пользователь скармливает Cursor/Claude. AI генерирует код, жестко ограниченный рамками манифеста.

### 5. V2 (Vision Auditor)
Сервис, куда можно кинуть URL или скриншот. Мультимодальная LLM (GPT-4o / Claude 3.5 Sonnet) анализирует картинку по чек-листу Meta-Slop и выдает отчет: *"Этот сайт выглядит как AI-генерация из-за семантического разрыва в Hero-секции и предсказуемой Bento-структуры. Вот 3 способа перестроить layout под вашу бизнес-задачу"*.

### 6. Главный философский сдвиг
Мы переводим индустрию от парадигмы **"Prompt-to-UI"** (где AI угадывает визуал) к парадигме **"Context-to-Manifest-to-UI"** (где AI сначала понимает задачу, формирует ограничения, и только потом пишет код).

**Anti-Slop — это не эстетика. Это возвращение инженерного и дизайнерского смысла в эпоху вероятностной генерации.**