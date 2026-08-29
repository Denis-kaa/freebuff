> ## ⚠️ СТАТУС: справочный superset — НЕ канон
>
> Этот документ (`arch_1.md`) — **справочный superset** архитектуры D2. Канонические источники: **`architecture.md`** (архитектура) + **`contracts.yaml`** (контракты). При расхождении прав канон.
>
> **Что из `arch_1.md` перенесено в канон (G1–G5):**
> - **G1** artifact lifecycle `CREATING→GENERATED→VALIDATING→READY` (+FAILED/INVALID) → `contracts.yaml` `generator.lifecycle`.
> - **G2** уровни валидации L1–L4 с разграничением ownership (L1 → `config/schema.py` fail-fast, L2/L3 → validator, L4 → LibreOffice вне D2) → `contracts.yaml` `validator.levels`.
> - **G3** `generation_id` + `template_id`/`template_version` в метаданных артефакта → `contracts.yaml` `Workbook` + `generator.artifact`.
> - **G4** atomic delivery (`temp → rename`, только READY на финальном пути) → `contracts.yaml` `generator.writes` + `generator.lifecycle`.
> - **G5** input snapshot на старте генерации → `contracts.yaml` `generator.snapshot`.
>
> **Расхождения с каноном (из `arch_1.md` НЕ брать):**
> - **`Delivery` как отдельный модуль** — в каноне это шаг оркестратора (atomic publish), отдельного context нет.
> - **`rules/` как отдельный модуль** — в каноне формулы/ссылки живут в CONFIG/GENERATOR.
> - **Физическая вложенность `domain/application/infrastructure`** — в каноне это dependency boundaries, НЕ папки (§4 architecture.md — плоская структура по context).
> - **Пропущен data formula injection** — `arch_1.md` экранирует только CONFIG-injection; канон дополнительно закрывает **R9** (экранирование значений DATA, начинающихся с `=`/`+`/`-`/`@`). R9 обязателен, его не терять.
> - **Счётчик модулей противоречив** — заявлено «7 bounded modules», перечислено 9, финальная диаграмма опускает `rules/`. Канон: 5 contexts (CONFIG/DATA/STYLES/GENERATOR/VALIDATOR) + orchestrator.
>
> **Статус H1/H2:** H1 (якорение формул/ссылок) в `arch_1.md` НЕ решён — в каноне закрыт сущностью `Anchor`. H2 (привязка DATA→sheet) закрыта в каноне: `Sheet.data_source` → `DataSource.source` (именованные коллекции DATA).

---

1. System Overview

Purpose

Спроектировать D2 Modular Monolith — конфигурируемый генератор Excel-дашбордов, где:

Template Config
      +
Normalized Data
      +
Theme
      ↓
Generation
      ↓
XLSX Artifact
      ↓
Validation

Первый экземпляр — Project Management Dashboard.

Ключевое свойство D2:

> Новый тип XLSX должен добавляться преимущественно изменением конфигурации, а не изменением Generation Core.



Это не означает, что абсолютно любой Excel-интерфейс должен описываться конфигом. Конфигурация должна покрывать поддерживаемую модель возможностей D2.


---

Core Entities

Entity	Ownership

Template Definition	Configuration
Workbook Definition	Configuration
Sheet Definition	Configuration
Field Definition	Configuration
Dashboard Block Definition	Configuration
Card Definition	Configuration
Formula Definition	Rules
Relationship Definition	Rules
Normalized Dataset	Data
Theme	Style
Generation Job	Orchestration
XLSX Artifact	Generation/Delivery
Validation Report	Validation


Ключевое разделение

Project, Task, Deadline, Status — данные предметной области.

Sheet, Column, DashboardBlock, Card — описание представления этих данных в Excel.

Это принципиально важно: Generator не должен превращаться в место хранения бизнес-модели проектов.


---

High-Level Data Flow

┌──────────────────┐
                  │ Template Config  │
                  └────────┬─────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Config      │
                    │ Validation  │
                    └──────┬──────┘
                           │
                           ▼
┌──────────────┐    ┌───────────────┐    ┌──────────────┐
│ Normalized   │───▶│ Generation    │◀───│ Theme        │
│ Data         │    │ Core          │    │              │
└──────────────┘    └───────┬───────┘    └──────────────┘
                             │
                             ▼
                       XLSX Artifact
                             │
                             ▼
                      ┌─────────────┐
                      │ Validator   │
                      └──────┬──────┘
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
             VALIDATION OK          VALIDATION ERROR
                  │                     │
                  ▼                     ▼
               Delivery             Diagnostics


---

Architectural Style

Modular Monolith.

Не microservices и не event-driven.

Причина: D2 генерирует локальный artifact в рамках одного workflow. Здесь нет независимых deployment units, требующих сетевой коммуникации, и нет объективной необходимости вводить broker.

Модули имеют строгие boundaries внутри одного приложения.

Это даёт:

низкую операционную сложность;

простой debugging;

транзакционную целостность workflow;

отсутствие сетевых failure points между внутренними модулями;

возможность позже выделить отдельный компонент, если появится реальная необходимость.



---

ADR-001: Modular Monolith

Context: D2 должен быть расширяемым, но первый сценарий — генерация одного XLSX.

Decision: Использовать modular monolith с внутренними архитектурными boundaries.

Alternatives:

Microservices.

Event-driven architecture.

Монолит без модульных границ.


Trade-offs:

Теряем независимый deployment модулей.

Получаем значительно меньшую инфраструктурную сложность и более простой lifecycle.


Consequences:
Нужно строго соблюдать dependency rules внутри одного процесса. В будущем выделение модуля в сервис возможно только через уже существующий public contract.


---

ADR-002: Configuration-Driven Templates

Context: Основная ценность D2 — создание разных XLSX без переписывания Generator.

Decision: Template Definition является декларативным описанием поддерживаемого workbook.

Alternatives:

Отдельный код под каждый шаблон.

Универсальный DSL с произвольным программированием.

Жёстко заданный project dashboard.


Trade-offs:

CONFIG становится сложнее простого Python-конфига.

Зато новый template не требует изменения core.


Consequences:
CONFIG должен иметь строгую schema и versioning. Произвольный код внутри CONFIG запрещён.


---

ADR-003: Normalized Data Contract

Context: Будущие источники данных могут быть различными.

Decision: Generator работает только с Normalized Data Contract.

Alternatives:

Generator напрямую читает CSV/API/Google Sheets.

Каждый template сам преобразует источник данных.


Trade-offs:

Появляется дополнительный normalization layer.

Зато Generator полностью изолирован от источника.


Consequences:
Любой будущий adapter обязан выдавать один и тот же semantic contract.


---

ADR-004: Independent Validation

Context: Генератор не должен считаться доказательством корректности собственного результата.

Decision: Validator работает как независимый consumer artifact.

Alternatives:

Validation внутри Generator.

Ручная проверка XLSX.


Trade-offs:

Некоторое дублирование знания о структуре.

Существенно выше доверие к результату.


Consequences:
Validator получает artifact + expected configuration и не имеет доступа к internal state Generator.


---

ADR-005: Synchronous Generation

Context: D2 генерирует файл в рамках одного процесса.

Decision: Generation workflow синхронный.

Alternatives:

Queue + worker.

Event-driven generation.


Trade-offs:

Большой XLSX может блокировать текущий execution.

Зато нет broker, job persistence и distributed failure handling.


Consequences:
При появлении длительных generation jobs можно добавить async execution над существующим Generation Contract, не меняя сам Generator.


---

2. Module Architecture

Module: Configuration

Responsibility:
Превратить raw template configuration в validated normalized configuration.

Boundaries — НЕ делает:

не создаёт XLSX;

не читает business data;

не применяет styles;

не выполняет arbitrary code.


Inputs:

Raw Template Definition

Outputs:

Normalized Template Definition

Internal Layers:

domain
  ↓
application
  ↓
infrastructure (если появится внешний config storage)

Layer Contracts

application
    ↓
Template Definition
    ↓
Schema Rules

Infrastructure не должна проникать в domain.

Public API

Концептуально:

load/normalize template
validate template
return normalized template

Private

schema internals;

normalization mechanics;

internal validation rules.


Data Ownership

Configuration module владеет:

template definitions;

schema;

template metadata.


Dependencies

Только собственные domain contracts.

Failure Modes

invalid configuration;

unsupported feature;

missing required field;

inconsistent reference.


Ошибки должны остановить generation до создания artifact.

Scaling Concerns

При большом количестве шаблонов bottleneck — validation/normalization configuration, но не runtime generation.

Security

CONFIG нельзя рассматривать как executable code.

Observability

Логировать:

template ID;

config version;

validation result;

configuration errors.


Не логировать секреты или потенциально чувствительные data values без необходимости.

Suggested Patterns

Schema-driven validation.

Не нужен generic rules engine.

Complexity

Medium.


---

Module: Template Definition

Responsibility:
Конкретный preset project_management.

Boundaries — НЕ делает:

не генерирует workbook;

не знает реализацию Generator;

не получает данные из Bitrix;

не управляет файлами.


Inputs: Template schema.

Outputs: Template Definition.

Layers

domain
application

Infrastructure не требуется на D2.

Public API

Получение зарегистрированного template.

Private

Конкретные:

sheets;

fields;

dashboard blocks;

cards;

rules.


Ownership

Владеет только описанием template, не данными проектов.

Extension Point

Новый template:

project_management
sales
production

не должен требовать изменения Generation Core.

Complexity

Medium.


---

Module: Data

Responsibility:
Предоставить Generator нормализованный набор данных.

Boundaries — НЕ делает:

не знает Excel rendering;

не создаёт Dashboard;

не форматирует workbook.


Layers

domain
  ↓
application
  ↓
infrastructure

Domain

Semantic data contract.

Application

Получение/normalization use cases.

Infrastructure

Будущие adapters.

На D2 фактически достаточно встроенного/sample adapter.

Public API

get normalized dataset

Ownership

Data module владеет input dataset в рамках generation context.

Source of truth для реальных данных будет определяться будущим adapter/source.

Failure Modes

missing required data;

invalid records;

inconsistent identifiers;

unsupported data type.


Scaling

Большие datasets могут потребовать:

streaming;

batching;

memory-aware generation.


Но это не внедрять в MVP заранее.

Security

Входные данные могут содержать business-sensitive information.

Data values не должны попадать в обычные application logs.

Complexity

Medium.


---

Module: Style / Theme

Responsibility:
Предоставить semantic visual definitions.

Boundaries — НЕ делает:

не знает проекты;

не принимает business decisions;

не вычисляет KPI.


Layers

domain
application

Public API

Получение validated theme.

Private

palette;

typography;

spacing;

semantic styles.


Ownership

Theme definitions.

Extension Point

default_theme
corporate_theme
dark_theme

Complexity

Low.


---

Module: Formula / Reference Rules

Responsibility:
Описывать вычисляемые связи между workbook elements.

Boundaries — НЕ делает:

не выполняет Excel calculation;

не меняет source DATA;

не принимает business state.


Layers

domain
application

Public API

Validated formula/reference definitions.

Critical Boundary

Formula engine должен различать:

Formula Definition
        ≠
Formula Evaluation

Generation создаёт формулу.

Excel/другой calculation engine потенциально вычисляет её.

openpyxl умеет записывать формулы и работать со структурой workbook, но сам не является Excel calculation engine; при загрузке data_only=True он может читать cached values, сохранённые последним Excel-приложением. 

Complexity

Medium.


---

Module: Generation Core

Responsibility:
Преобразовать validated configuration + normalized data + theme в XLSX artifact.

Template
   +
Data
   +
Theme
   +
Rules
   ↓
Generation Core
   ↓
Artifact

Boundaries — НЕ делает

не получает данные из внешнего API;

не знает Bitrix24;

не владеет template definitions;

не валидирует собственный результат;

не управляет delivery;

не хранит persistent business state.


Internal Layers

domain
   ↓
application
   ↓
infrastructure

Domain

Semantic generation model:

workbook;

sheet;

field;

block;

artifact.


Application

Generation workflow.

Infrastructure

Excel-specific rendering.

Это единственный слой, который должен быть тесно связан с конкретным XLSX library.

Public API

Единый Generation Contract:

validated template
+
normalized data
+
theme
+
generation options
→
artifact

Private Components

workbook renderer;

sheet renderer;

dashboard renderer;

card renderer;

formula renderer;

reference renderer;

style renderer.


Ownership

Generator владеет создаваемым artifact во время generation lifecycle.

После завершения ownership переходит Delivery/Artifact storage boundary.

Dependencies

Generation Application
        ↓
Generation Domain

Infrastructure
        ↓
Application contracts

Failure Modes

invalid rendering instruction;

unsupported config feature;

invalid formula reference;

XLSX write failure;

corrupted artifact.


Generation должен быть atomic from consumer perspective:

generation failed
→ no artifact marked as ready

Scaling

Основной bottleneck всей D2-системы.

Особенно:

количество rows;

количество formatting operations;

количество formulas;

количество conditional formatting rules;

workbook size.


openpyxl поддерживает стили, conditional formatting и data validation, но сложные formatting rules требуют аккуратного управления диапазонами и формулами. 

Security

Не позволять CONFIG приводить к произвольному выполнению Python.

Observability

Каждая generation operation должна иметь:

generation ID;

template ID/version;

input dataset identifier;

duration;

artifact size;

validation status;

error category.


Suggested Patterns

Renderer strategy — только если реально существует несколько rendering mechanisms.

Ports/contracts для infrastructure.

Pipeline orchestration внутри application layer.


Не вводить generic factory/abstract factory без реального варианта замены.

Complexity

High.

Это центральный модуль.


---

Module: Validator

Responsibility:
Независимо проверить artifact относительно expected configuration.

Layers

domain
   ↓
application
   ↓
infrastructure

Validation Levels

L1 CONFIG
    ↓
L2 STRUCTURAL XLSX
    ↓
L3 SEMANTIC
    ↓
L4 CALCULATION

Для D2 обязательны L1–L3.

L4 — отдельная extension boundary.

Public API

artifact + expected config
→ ValidationReport

Private

Individual validation rules.

Ownership

Validator владеет только ValidationReport.

Он не изменяет XLSX.

Failure Modes

artifact unreadable;

missing sheet;

unexpected structure;

broken reference;

missing validation;

invalid config mapping.


Scaling

Количество validation rules × workbook size.

Security

Artifact считается untrusted input.

Observability

Каждая ошибка должна иметь:

rule ID;

severity;

location;

description;

generation ID.


Complexity

High.


---

Module: Orchestrator

Responsibility:
Координация generation workflow.

Не должен делать

business calculations;

rendering;

validation rules;

data transformation logic.


Workflow

1. Load Config
2. Validate Config
3. Load Data
4. Validate Data Contract
5. Load Theme
6. Prepare Generation Context
7. Generate Artifact
8. Validate Artifact
9. Publish Result

Failure boundary

Config invalid
     ↓
STOP

Data invalid
     ↓
STOP

Generation failure
     ↓
NO READY ARTIFACT

Validation failure
     ↓
ARTIFACT NOT READY

Complexity

Medium.


---

Module: Artifact Delivery

Responsibility:
Сделать результат доступным consumer.

Для MVP это может быть локальный output artifact.

Boundary

Не знает, как XLSX был создан.

Complexity

Low.


---

3. Integration Architecture

Communication Model

Все внутренние взаимодействия D2:

synchronous, in-process.

Orchestrator
    ↓
Config
    ↓
Data
    ↓
Generator
    ↓
Validator
    ↓
Delivery

Broker не нужен.


---

Contracts

Главные контракты:

TemplateDefinition
NormalizedDataset
ThemeDefinition
GenerationOptions
GenerationArtifact
ValidationReport

Особенно важен GenerationArtifact.

Он должен описывать не только путь к файлу, но и metadata:

artifact identity
template identity/version
generation identity
validation status
creation metadata


---

ADR-006: Artifact Status

Context: Нельзя считать любой созданный файл успешным результатом.

Decision:

Использовать lifecycle:

CREATING
   ↓
GENERATED
   ↓
VALIDATING
   ↓
READY

Failure:

CREATING ──→ FAILED
GENERATED ─→ INVALID
VALIDATING ─→ INVALID

Alternatives:

Просто наличие файла.

Boolean success.


Trade-offs:
Немного сложнее lifecycle, но исчезает неоднозначность между «файл создан» и «файл пригоден».

Consequences:
Delivery публикует только READY.


---

Retry Strategy

Для D2 retries минимальны.

Не retry автоматически:

invalid CONFIG;

invalid DATA;

broken formula reference;

unsupported feature.


Можно retry:

временный filesystem error;

transient external storage error, если такой появится.


Главный принцип:

> Не retry deterministic failure.




---

Idempotency

Generation должна быть логически idempotent:

same template version
+
same normalized data
+
same theme
+
same options

→ эквивалентный artifact.

Для повторного запуска не должно происходить:

duplicate records
duplicate sheets
duplicate rules


---

Failure Propagation Model

CONFIG ERROR
    ↓
Generation not started

DATA ERROR
    ↓
Generation not started

GENERATION ERROR
    ↓
Artifact not READY

VALIDATION ERROR
    ↓
Artifact not READY

DELIVERY ERROR
    ↓
Artifact remains generated
but unavailable through delivery

Важно разделить:

generation failure и delivery failure.

Если XLSX успешно создан, но не удалось его опубликовать, это не означает, что Generator сломался.


---

Consistency Model

Для D2:

Strong consistency внутри одного generation workflow.

Нет необходимости в eventual consistency.

Input snapshot должен быть фиксирован на начало generation.

То есть Generator не должен читать mutable DATA посреди процесса и получать смесь разных состояний.


---

Orchestration Model

Используется explicit application workflow, а не event-driven choreography.

Prepare
  ↓
Validate Inputs
  ↓
Generate
  ↓
Validate Artifact
  ↓
Publish

Это делает состояние workflow очевидным и легко диагностируемым.


---

4. Project Structure

Архитектурное дерево:

project/
│
├── config/
│   ├── domain/
│   │   ├── schema/
│   │   └── definitions/
│   ├── application/
│   │   ├── normalization/
│   │   └── validation/
│   └── templates/
│       └── project_management/
│
├── data/
│   ├── domain/
│   ├── application/
│   └── infrastructure/
│       └── adapters/
│
├── styles/
│   ├── domain/
│   ├── application/
│   └── themes/
│
├── rules/
│   ├── formulas/
│   └── references/
│
├── generation/
│   ├── domain/
│   ├── application/
│   └── infrastructure/
│       └── xlsx/
│
├── validation/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── rules/
│
├── orchestration/
│   └── application/
│
├── delivery/
│   ├── application/
│   └── infrastructure/
│
├── tests/
│   ├── contracts/
│   ├── configuration/
│   ├── generation/
│   ├── validation/
│   └── integration/
│
└── output/

Важная поправка

Не следует превращать эту структуру в обязательный физический layout каждого маленького компонента.

Например, styles достаточно прост, поэтому его не нужно искусственно дробить на десятки пакетов.

Архитектурный принцип:

> Layers — это dependency boundaries, а не требование создавать папку ради каждой архитектурной коробки.




---

5. Risks & Dangerous Areas

Risk	Why It Happens	Consequences	Mitigation

Race conditions	Два generation job используют один output/state	Перезапись artifact	Уникальный generation context + atomic delivery
Coupling	Generator знает template	D2 превращается в D1	Только normalized config
God Generator	Все rendering rules помещаются внутрь Core	Невозможность расширения	Renderer boundaries + CONFIG-driven behavior
Scaling bottleneck	Большой workbook + много formatting operations	Долгая генерация / memory pressure	Измерять generation profile; оптимизировать только после измерений
Partial failure	Generation прошла, validation упала	Некорректный файл может быть опубликован	READY только после validation
Stale data	DATA меняется во время generation	Несогласованный workbook	Input snapshot
Invalid contracts	CONFIG и DATA расходятся	Ошибки в runtime	Pre-generation contract validation
Retry storms	Retry deterministic failures	Повторные бесполезные generation jobs	Retry только transient failures
Secret leakage	Debug logging input/config	Утечка business data/secrets	Structured logs + redaction
Formula false confidence	Structural check принимается за calculation	KPI могут быть неверными	Отдельный calculation validation layer
Config injection	CONFIG допускает executable logic	Arbitrary code execution	Declarative-only configuration
Workbook corruption	Ошибка во время записи	Неполный artifact	Temporary artifact → atomic publish
Validation drift	Validator и CONFIG начинают расходиться	False positives/negatives	Validator работает against explicit contract
Shared mutable state	Модули одновременно изменяют workbook	Непредсказуемость	Generation Core — единственный owner workbook during generation


Secret leakage

Для D2 сейчас нет внешних credentials.

Но архитектурное правило следует установить уже сейчас:

секреты не входят ни в CONFIG, ни в DATA, ни в generated artifact metadata.

Если позже появится Bitrix24/API adapter, secrets должны принадлежать отдельному security/configuration boundary, а не Data module.


---

6. Evolution Path

MVP — D2.0

Config
Data
Theme
Generator
Validator
Orchestrator
Delivery

Один процесс.

Один project-management template.

Один нормализованный источник sample/real data.

Без:

API integrations;

queues;

distributed workers;

SaaS;

multi-tenant;

plugin marketplace.



---

Growth Stage — D2.x

Появляются:

Template Registry
Multiple Templates
Multiple Card Variants
Multiple Themes
More Data Adapters
Artifact History

Первое, что потенциально начнёт ломаться — не модульная архитектура, а expressiveness CONFIG.

Если CONFIG начинает содержать:

if
for
custom Python
arbitrary expressions

это сигнал, что модель конфигурации достигла своего предела.

Тогда нужно расширять декларативную модель, а не превращать CONFIG в язык программирования.


---

Production Scale

Если появятся:

тысячи generation jobs;

большие datasets;

параллельная генерация;

длительные jobs;

внешнее storage;

пользователи;


тогда можно добавить:

API / UI
    ↓
Job Orchestrator
    ↓
Queue
    ↓
Generation Workers
    ↓
Artifact Storage

Но существующий Generation Contract должен сохраниться.


---

ADR-007: Async Evolution Boundary

Context: Долгие generation jobs могут блокировать synchronous workflow.

Decision: Не использовать queue в D2, но сохранить Generation Core независимым от способа запуска.

Alternatives:

Queue сразу.

Оставить Generator связанным с HTTP/UI lifecycle.


Trade-offs:
D2 проще; при росте появится дополнительный orchestration layer.

Consequences:
Generation Core не должен знать, запущен он CLI, API, worker или scheduler.


---

Future Extensions

D3

Template Registry
      ↓
Project Management
Sales
Production
...

D4

External Sources
      ↓
Adapters
      ↓
Normalized Data
      ↓
Existing Generator

Это главное архитектурное преимущество.

Bitrix24 не должен требовать:

Bitrix → Generator modification

Должно быть:

Bitrix Adapter
      ↓
Normalized Data
      ↓
Existing Generator


---

7. Explicit Recommendations

Обязательно сделать

1. Зафиксировать Normalized Data Contract до реализации Generator.


2. Зафиксировать Configuration Schema до написания template.


3. Разделить Template Definition и Generation Core.


4. Сделать Validator независимым от внутренних компонентов Generator.


5. Ввести Generation ID и Template Version.


6. Ввести artifact lifecycle: GENERATED → VALIDATING → READY.


7. Не публиковать artifact до успешной структурной validation.


8. Разделить structural validation и calculation validation.


9. Зафиксировать ownership workbook: только Generation Core изменяет его во время generation.


10. Сделать CONFIG декларативным и запретить executable logic.



Чего избегать

Не делать микросервисы.

Не добавлять Redis/queue/broker без реальной нагрузки.

Не делать универсальный DSL.

Не делать plugin system.

Не добавлять Bitrix24 до стабилизации Data Contract.

Не переносить business logic в Generator.

Не делать utils модулем-свалкой.

Не делать config.py огромным файлом со всей системой.

Не пытаться заранее поддержать все возможные Excel features.


Что можно упростить

На первом этапе допустимо объединить:

Configuration Schema
+
Template Definition

если физическое разделение создаёт больше сложности, чем пользы.

Также Formula/Reference Rules можно оставить частью Configuration Domain, пока они не начинают иметь собственный lifecycle.


---

Что нельзя откладывать

Есть три вещи, которые лучше определить до первой реализации:

1. Configuration Contract

Что именно может описывать CONFIG?

2. Data Contract

Какие данные получает Generator?

3. Generation Contract

Что именно считается входом и выходом Generator?

Если эти три контракта не зафиксировать, разработка почти неизбежно начнёт смешивать:

business data
template
rendering
validation

и D2 постепенно вернётся к исходному варианту:

Python script → конкретный XLSX


---

Финальное архитектурное решение

Я бы зафиксировал не 10 независимых сервисов, а один modular monolith с 7 основными bounded modules:

┌────────────────────┐
                    │   ORCHESTRATION    │
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼──────────────────┐
          ▼                   ▼                  ▼
   ┌────────────┐      ┌────────────┐     ┌────────────┐
   │   CONFIG   │      │    DATA    │     │   THEME    │
   │  + TEMPLATE│      │  CONTRACT  │     │            │
   └──────┬─────┘      └──────┬─────┘     └─────┬──────┘
          │                   │                  │
          └───────────────────┼──────────────────┘
                              ▼
                    ┌──────────────────┐
                    │    GENERATOR     │
                    │      CORE        │
                    └────────┬─────────┘
                             │
                             ▼
                       ┌───────────┐
                       │   XLSX    │
                       │  ARTIFACT │
                       └─────┬─────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    VALIDATOR     │
                    └────────┬─────────┘
                             │
                             ▼
                         DELIVERY

Главный architectural invariant:

Template changes
       ↓
CONFIG changes
       ↓
Generator stays unchanged

Второй:

Data source changes
       ↓
Adapter changes
       ↓
Normalized Data stays unchanged
       ↓
Generator stays unchanged

Третий:

Generator changes
       ↓
Validator must NOT depend on its internals

Это уже достаточно конкретная архитектура, чтобы передавать каждый модуль отдельному Senior Engineer/Developer, но ещё не спускается на уровень классов и реализации.

Knowledge verification

Для текущего архитектурного решения проверена официальная документация openpyxl: библиотека поддерживает создание workbook, стили, conditional formatting и data validation; при этом работа с формулами не должна интерпретироваться как полноценный Excel calculation engine. 

Codebase / project docs / Context7: в предоставленном входе отсутствует реальный codebase и проектная документация, а Context7-инструмент в текущем окружении недоступен. Поэтому архитектура не делает предположений о существующих конвенциях или коде.