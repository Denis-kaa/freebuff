# ARCHITECTURE — sheet_project (D2 конфигурируемый генератор Excel-дашбордов)

> **Роль:** architect (AI System Architect, blueprint `06_architect.md` v3.1.0)
> **Вход:** decomposition.md + module_list.md + integration_topology.md (decomposer), parsed_requirements.md, risk_matrix.md, brief.md.
> **Архитектурный стиль:** Modular Monolith (одна Python-пакета, без микросервисов/событий).
> **Связанные контракты:** `contracts.yaml` (формальный контракт на стыках) · **ADR:** `decisions/ADR-001` (стек), `adr/ADR-002` (layered генератор).

---

## 1. System Overview

### Purpose
D2 — **конфигурируемый генератор Excel-дашбордов**: структура XLSX (листы, колонки, типы, KPI, карточки, справочники, формулы, правила валидации) и стили выносятся из кода в декларативный CONFIG. Ядро (GENERATOR) не содержит ни одного зашитого названия листа и ни одной ветки `if project_dashboard:` — новый дашборд добавляется **без правки ядра**, только новым CONFIG (+ DATA + STYLES).

### Core Entities
| Сущность | Описание | Владелец |
|----------|----------|----------|
| `Workbook` | корень CONFIG: список листов + порядок + метаданные | CONFIG |
| `Sheet` | один лист: название, колонки, блоки, справочники | CONFIG |
| `Field` / `Column` | колонка: имя, тип, обязательность, формат | CONFIG |
| `DataSource` | привязка листа к коллекции: `source` (имя коллекции) + `field_map` (колонка → поле) | CONFIG |
| `DashboardBlock` | блок дашборда (заголовок + набор KPI/карточек) | CONFIG |
| `KPI` | ключевой показатель (название, формула/поле, формат) | CONFIG |
| `Card` | карточка (шаблон представления записи) | CONFIG |
| `ValidationRule` | правило data validation (список/диапазон/тип) | CONFIG |
| `Formula` | Excel-формула (структурно, без расчёта) | CONFIG |
| `Anchor` | якорь цели формулы/ссылки: колонка (логическое имя) + строка-якорь + смещение + протяжённость | CONFIG |
| `Relationship` / `Reference` | связь/гиперссылка между листами | CONFIG |
| `DisplayRule` | правило условного форматирования/видимости | CONFIG |
| `Style` / `Theme` | цвета, шрифты, границы, ширины | STYLES |
| `Row` / `Record` | нормализованная строка данных | DATA |
| `GenerationArtifact` | результат генерации: путь + метаданные (generation_id, template_id/version, status) | GENERATOR/Orchestrator |

### High-Level Data Flow
```
CONFIG (декларация) ──┐
DATA   (вход) ────────┼──→ GENERATOR (ядро) ──→ XLSX (output/*.xlsx) ──→ VALIDATOR (структура)
STYLES (визуал) ──────┘
```
Главный путь (single-threaded, синхронный): `main.py` читает CONFIG → DATA → STYLES, передаёт в `generator/workbook.py`, тот последовательно делегирует заполнение листов / блоков / формул / валидации / ссылок, **пишет во временный файл (CREATING→GENERATED)**, затем `validator/validator.py` перечитывает файл и сверяет структуру/семантику с CONFIG (VALIDATING); при успехе артефакт **атомарно публикуется** (`temp → rename`) на `output/*.xlsx` и получает статус **READY** (audit G1/G4).

### Architectural Style — Modular Monolith
**Выбор:** один Python-пакет с чётким разбиением по bounded contexts (CONFIG / DATA / STYLES / GENERATOR / VALIDATOR).

**Почему:**
- Задача локальная, offline, один процесс, один пользователь — нет оснований для сети/очередей/событий.
- Конфигурируемость достигается **разделением изменяемого/неизменяемого**, а не распределением.
- openpyxl синхронен и stateful (объект Workbook) — event-driven только добавит сложность.

**Отвергнуто:** микросервисы, event-driven, message broker, shared mutable state между модулями (всё против `architecture_principles` blueprint: не усложнять MVP, не предлагать паттерны «ради паттернов»).

---

## 2. Module Architecture

Проектирую до уровня слоёв, границ и контрактов (без конкретных классов — это задача Developer). Декомпозиция по bounded contexts из `decomposition.md`.

### 2.1 CONFIG (config/schema.py + config/project_dashboard.py)
- **Responsibility:** декларативное описание структуры дашборда (сущности + конкретный шаблон). Чистые данные, **без исполняемой бизнес-логики**.
- **Boundaries (НЕ делает):** не читает файлы, не пишет XLSX, не вычисляет, не знает openpyxl.
- **Inputs:** человек/код объявляет структуру через сущности `schema.py`.
- **Outputs:** валидный CONFIG-граф (dict/dataclass), сериализуемый в YAML/JSON.
- **Internal Layers:**
  - *domain* — сущности `schema.py` (`Workbook`, `Sheet`, `Field`, …) — чистые модели с валидацией типов.
  - *application* — `project_dashboard.py` инстанцирует домен для шаблона «проектный дашборд» (use-case сборки CONFIG).
  - *infrastructure* — **отсутствует** (CONFIG не ходит наружу). Будущие адаптеры (читать CONFIG из YAML) — сюда.
- **Layer Contracts:** application зависит от domain; domain не знает про конкретный шаблон.
- **Public API:** `load_config(...) → Workbook` (или импорт модуля `project_dashboard` с готовым CONFIG).
- **Private Components:** внутренние helper-ы сборки полей/стилей шаблона.
- **Data Ownership:** владеет **структурой** дашборда (не данными).
- **Dependencies:** только `schema.py` (внутренний), stdlib. НЕ зависит от `generator/*`.
- **Failure Modes:** невалидный CONFIG (неизвестный тип поля, битая ссылка на лист) → ранняя ошибка с указанием поля (fail-fast на входе).
- **Scaling Concerns:** рост числа шаблонов → нужен реестр шаблонов (см. §6), не рост кода ядра.
- **Security Concerns:** CONFIG не исполняется (`eval`/импорт чужого кода запрещён) — только данные.
- **Observability:** логировать «CONFIG загружен: N листов, M полей».
- **Suggested Patterns:** Value Objects + строгая типизация (dataclass/pydantic-like), Registry для шаблонов (Open-Closed).
- **Complexity:** Low.

### 2.2 DATA (data/models.py + data/sample_data.py)
- **Responsibility:** нормализованные структуры входных данных, source-agnostic.
- **Boundaries (НЕ делает):** не знает источник (Python/CSV/JSON/Google Sheets/API/Bitrix24), не знает, как данные лягут в лист.
- **Inputs:** источник через адаптер (в этой итерации — `sample_data.py`).
- **Outputs:** **именованные коллекции** `Row`/`Record` — `map[collection_name → list[Record***REMOVED******REMOVED***` (например `projects`, `tasks`), НЕ один плоский список.
- **Sheet binding (audit H2):** каждый `Sheet` ссылается на коллекцию через `data_source.source`; `field_map` маппит колонки листа на поля записи этой коллекции. Summary-лист (KPI) — без `data_source` (считается формулами из других листов). Одна коллекция может питать несколько листов с разными `field_map`. Пустая коллекция → лист с заголовками (не ошибка); якорь на `first_data`/`last_data` пустой коллекции → fail-fast (H1). Неиспользуемая коллекция → warning, не падать.
- **Internal Layers:**
  - *domain* — `models.py` (модели: Project, Task, Status, Deadline — домен проектного дашборда).
  - *application* — `sample_data.py` (use-case: пример данных первого шаблона).
  - *infrastructure* — будущие адаптеры источников (CSV/JSON/API/Bitrix24).
- **Layer Contracts:** domain ← application; источник подключается через единый интерфейс адаптера (не в этой итерации).
- **Public API:** `get_rows(data_source) → list[Record***REMOVED***` (`data_source.source` выбирает коллекцию, `field_map` отбирает/переименовывает поля).
- **Private Components:** маппинг сырого источника → модели.
- **Data Ownership:** владеет **значениями** данных.
- **Dependencies:** только `models.py`. НЕ зависит от `generator/*`, `config/*`.
- **Failure Modes:** пустые/неполные данные, несоответствие колонок → validator укажет расхождение.
- **Scaling Concerns:** большие объёмы → потоковая запись строк в openpyxl (write-only mode) вместо материализации всего в память (§6).
- **Security Concerns:** данные не интерпретируются как формулы (значения, начинающиеся с `=`, экранируются при записи).
- **Observability:** логировать число строк/записей.
- **Suggested Patterns:** Repository/Adapter (источник за интерфейсом), Immutable Records.
- **Complexity:** Low.

### 2.3 STYLES (styles/theme.py)
- **Responsibility:** визуальная конфигурация (цвета, шрифты, границы, выравнивание, ширины). Тоже чистые данные.
- **Boundaries (НЕ делает):** не пишет XLSX, не знает логику генерации, не знает конкретного листа.
- **Inputs:** объявление темы.
- **Outputs:** Theme-словарь (ключ → Style).
- **Internal Layers:** один слой (домен-данные). Инфраструктура не нужна.
- **Layer Contracts:** GENERATOR применяет стили **декларативно в конце** генерации; STYLES ничего не знает о GENERATOR.
- **Public API:** `load_theme() → Theme`.
- **Private Components:** конкретные значения цветов/шрифтов.
- **Data Ownership:** владеет **визуалом**.
- **Dependencies:** нет (чистые данные).
- **Failure Modes:** отсутствующий стиль (неизвестный ключ) → fallback на дефолтный стиль с warning (не падать).
- **Scaling Concerns:** темы/брендинги → несколько theme-модулей.
- **Security Concerns:** нет.
- **Observability:** warning при fallback-стиле.
- **Suggested Patterns:** Theme как data-class, default-fallback.
- **Complexity:** Low.

### 2.4 GENERATOR (ядро) — generator/*.py
- **Responsibility:** создать XLSX из CONFIG + DATA + STYLES. **Неизменяемое ядро.**
- **Boundaries (НЕ делает):** не содержит зашитых названий листов, не знает конкретного шаблона (`config/project_dashboard.py`), не вычисляет формулы (openpyxl пишет формулу, но не считает), не импортирует `config/project_dashboard.py`.
- **Inputs:** CONFIG (Workbook), DATA (`map[collection_name → list[Record***REMOVED******REMOVED***`), STYLES (Theme).
- **Outputs:** `GenerationArtifact` (метаданные: path/status/generation_id/template_id/version); промежуточный `openpyxl.Workbook` — внутренний, не выходит наружу; финальный файл `output/*.xlsx` — только READY (atomic publish, G4).
- **Internal Layers:**
  - *domain* — понятия генерации: построение листа из описания, применение стиля, создание формулы/validation/ссылки.
  - *application* — `workbook.py` (use-case: собрать workbook по CONFIG), делегирует `sheets/dashboard/formulas/validation/references`.
  - *infrastructure* — **openpyxl** изолирован здесь: единственное место, где вызывается библиотека. `styles/theme.py` НЕ зависит от openpyxl.
- **Layer Contracts:** domain (логика сборки) ← application (`workbook.py`); infrastructure (openpyxl) вызывается только из application/домена через тонкую обёртку. Внутренние под-модули вызываются из `workbook.py` (не напрямую из `main.py`).
- **Public API:** `generate(workbook_config, data, theme) → GenerationArtifact` (промежуточный `openpyxl.Workbook` внутренний).
- **Private Components (внутренние):**
  - `sheets.py` — заполнение листов данными;
  - `dashboard.py` — Dashboard-блоки + KPI + карточки;
  - `formulas.py` — формулы (структурно);
  - `validation.py` — data validation + выпадающие списки;
  - `references.py` — связи/гиперссылки.
- **Anchor Resolution (audit H1):** формулы и ссылки описывают цель **якорем** (`Anchor`: колонка по логическому имени + строка-якорь `header|first_data|last_data` + смещение `offset` + протяжённость `range`), а НЕ буквой ячейки. Реальные координаты (`A1`, диапазон) вычисляет **ядро** в момент генерации, когда известны позиция таблицы и число строк данных. CONFIG остаётся свободен от статичных координат: при перестановке колонок или росте данных формула «едет» за ними автоматически, без правки CONFIG.
- **Input Snapshot (audit G5):** `generate()` фиксирует snapshot входов (CONFIG + DATA + STYLES + options) на старте; ядро не читает mutable DATA посреди процесса — исключает смесь состояний в одном артефакте.
- **Artifact Lifecycle (audit G1) + Atomic Publish (audit G4):** артефакт проходит `CREATING → GENERATED → VALIDATING → READY` (неуспех: `FAILED`/`INVALID`). Запись идёт во временный файл, публикация на `output/*.xlsx` — атомарным `temp → rename` **только для READY**. Метаданные `GenerationArtifact` несут `generation_id` + `template_id`/`template_version` + `status` (audit G3).
- **Data Ownership:** владеет **процессом генерации** и промежуточным объектом Workbook; не владеет ни CONFIG, ни DATA, ни STYLES.
- **Dependencies:** CONFIG-сущности (`schema.py` — читает), DATA-модели (`models.py` — читает), STYLES (`theme.py` — читает), openpyxl (infra). **НЕ** `config/project_dashboard.py`.
- **Failure Modes:**
  - битая ссылка на несуществующий лист → fail-fast с точным именем;
  - неразрешимый якорь (неизвестная колонка / row-якорь без данных / offset за границами) → fail-fast с именем якоря;
  - тип поля не поддерживается openpyxl → ошибка с указанием поля;
  - значение данных, похожее на формулу, → экранирование.
- **Scaling Concerns:** большой объём данных → write-only mode openpyxl, потоковая запись; много листов → порядок и лимиты (Excel: 1 048 576 строк, 16 384 колонок) валидируются заранее.
- **Security Concerns:** экранирование формул из данных (formula injection: значение `=cmd|...` не должно стать формулой); CONFIG не исполняется.
- **Observability:** логировать каждый лист/блок при генерации, тайминги, число записанных строк.
- **Suggested Patterns:** Template Method / Strategy (варианты блоков), Builder для Workbook, Façade (`workbook.py` как единый вход).
- **Complexity:** Medium (наибольший модуль — это и есть суть системы).

### 2.5 VALIDATOR (validator/validator.py)
- **Responsibility:** **структурная + семантическая** проверка результата (уровни L2/L3): перечитать XLSX и сверить с CONFIG (листы, колонки, типы, validation, формулы, ссылки) и с DATA (field_map, якоря). Расчёт формул (L4) — НЕ здесь.
- **Validation Levels (audit G2):** `L1 CONFIG` (fail-fast, владелец `config/schema.py`, до генерации) → `L2 STRUCTURAL` (XLSX↔CONFIG, validator) → `L3 SEMANTIC` (CONFIG↔DATA + якоря, validator) → `L4 CALCULATION` (LibreOffice, вне D2). L1 НЕ дублируется в validator; validator отвечает за L2/L3.
- **Boundaries (НЕ делает):** не вычисляет формулы, не вызывает Excel/LibreOffice, не чинит результат, не меняет XLSX.
- **Inputs:** путь к `output/*.xlsx` + CONFIG.
- **Outputs:** отчёт проверки (список passed/failed с привязкой к листу/полю) + exit-код.
- **Internal Layers:**
  - *domain* — правила структурной сверки (лист↔Sheet, колонка↔Field, …).
  - *application* — `validator.py` (use-case: прочитать workbook через openpyxl и применить правила).
  - *infrastructure* — openpyxl (чтение). **Расчёт формул** — отдельный будущий слой (LibreOffice headless) и НЕ входит в validator (§6).
- **Layer Contracts:** application читает CONFIG и XLSX, применяет domain-правила; infrastructure изолирует openpyxl.
- **Public API:** `validate(xlsx_path, workbook_config) → ValidationReport` (exit 0/1).
- **Private Components:** правила сверки по типам сущностей.
- **Data Ownership:** не владеет; только читает.
- **Dependencies:** `config/schema.py`, openpyxl (чтение). НЕ `generator/*`, НЕ LibreOffice.
- **Failure Modes:** файл не существует / повреждён / не соответствует CONFIG → подробный отчёт с конкретным расхождением.
- **Scaling Concerns:** большой XLSX → читать по листам, не материализуя всё.
- **Security Concerns:** только чтение; не доверять содержимому ячеек (не eval).
- **Observability:** число проверок, число failures, итоговый verdict.
- **Suggested Patterns:** Strategy (набор правил проверки), Result/Report object.
- **Complexity:** Low–Medium.

### 2.6 Orchestrator (main.py)
- **Responsibility:** склеить поток: CONFIG → DATA → STYLES → GENERATOR → XLSX → VALIDATOR → публикация. Тонкий.
- **Workflow (9 шагов, audit G1/G4):** (1) Load Config → (2) Validate Config (L1, fail-fast) → (3) Load Data → (4) Validate Data Contract → (5) Load Theme → (6) Prepare Generation Context (snapshot, G5) → (7) Generate Artifact (temp, CREATING→GENERATED) → (8) Validate Artifact (L2/L3, VALIDATING) → (9) Publish Result (atomic `temp → rename`, только READY). Публикация — шаг оркестратора, НЕ отдельный Delivery-модуль.
- **Boundaries:** не содержит генерационной/валидационной логики.
- **Public API:** CLI `python main.py` (или точка входа `__main__`).
- **Complexity:** Low.

---

## 3. Integration Architecture

### Communication Model
- **Sync, Direct Calls** (нет async/событий/брокера — локальный offline-процесс).
- **API-based** (функции/объекты), не events.

### Contracts (формально — `contracts.yaml`)
| Стык | Контракт |
|------|----------|
| CONFIG → GENERATOR | `Workbook` (граф сущностей `schema.py`); GENERATOR читает, не знает шаблона |
| DATA → GENERATOR | `map[collection_name → list[Record***REMOVED******REMOVED***` (именованные коллекции); `DataSource.source` выбирает коллекцию для каждого листа |
| STYLES → GENERATOR | `Theme` (словарь Style) |
| GENERATOR → XLSX | `openpyxl.Workbook` → `output/*.xlsx` (через temp → rename, только READY) |
| GENERATOR → Orchestrator | `GenerationArtifact` (метаданные: path/status/generation_id/template_id/version) |
| XLSX → VALIDATOR | validator перечитывает файл (temp-артефакт) и сверяет с CONFIG |
| GENERATOR → openpyxl | единственный инфраструктурный вызов (изолирован) |

### Failure Propagation
- Ошибки **fail-fast на входе** (невалидный CONFIG/DATA) — до генерации.
- Ошибки генерации — с точным контекстом (лист/поле), без частично-молчаливых результатов.
- Validator-расхождения — отчёт, а не exception (читаемый список).
- **Не** глотать ошибки; пустой CONFIG → явная ошибка, а не пустой файл.

### Retry Strategy
- Retries не нужны (нет сети/внешних зависимостей). Идемпотентность: повторный запуск детерминирован; при успехе READY атомарно заменяет предыдущий `output/*.xlsx`, при неудаче (FAILED/INVALID) предыдущий READY остаётся нетронутым (temp удаляется, audit G4).

### Consistency Model
- **Strong (single-threaded)**: весь процесс в одном потоке, общий state — только локальный объект Workbook в рамках одного запуска. Нет shared mutable state между модулями.
- **Input snapshot (audit G5):** входы фиксируются на старте генерации; mutable DATA не читается посреди процесса — согласованный артефакт без смеси состояний.

### Orchestration Model
- **Процедурный оркестратор** `main.py`: линейная последовательность шагов, каждый шаг — вызов фасада соответствующего контекста. Не state-machine (не нужна), не workflow-engine.

---

## 4. Project Structure

```
sheet_project/
├── config/
│   ├── schema.py            # domain: сущности CONFIG (Workbook, Sheet, Field, …)
│   └── project_dashboard.py # application: CONFIG первого шаблона
├── data/
│   ├── models.py            # domain: нормализованные модели
│   └── sample_data.py       # application: пример данных
├── generator/               # ЯДРО (неизменяемое)
│   ├── workbook.py          # application: фасад генерации (единый вход)
│   ├── sheets.py            # domain: заполнение листов
│   ├── dashboard.py         # domain: блоки/KPI/карточки
│   ├── formulas.py          # domain: формулы (структурно)
│   ├── validation.py        # domain: data validation
│   └── references.py        # domain: связи/гиперссылки
├── styles/
│   └── theme.py             # данные: тема (цвета/шрифты/границы)
├── validator/
│   └── validator.py         # application: структурная проверка XLSX↔CONFIG
├── output/                  # готовые XLSX (git-ignored)
├── main.py                  # оркестратор
├── contracts.yaml           # формальный контракт на стыках
├── adr/                     # архитектурные решения (blueprint output)
├── decisions/               # проектные решения (PROJECT_RULES convention)
└── … (brief/lisa/risk/decomposition/module_list/integration_topology + каркас)
```

Причины выделения папок: каждая папка = один bounded context (низкая связанность, высокая связность); `generator/` = неизменяемое ядро, изолированное от изменяемых `config/`/`styles/`/`data/`.

---

## 5. Risks & Dangerous Areas

| Risk | Why It Happens | Consequences | Mitigation |
|------|----------------|--------------|------------|
| **R1 Формулы не вычисляются** (openpyxl) | openpyxl пишет формулы, но не считает | клиент видит «сырые» формулы, думает, что сломано | разделить structural (validator, в scope) vs calculation (LibreOffice, отдельный слой §6); документировать |
| **R2 Бизнес-логика «протекает» в ядро** | желание быстро захардкодить шаблон | ядро теряет конфигурируемость, каждый шаблон = правка кода | инвариант: `generator/*` не импортирует `config/project_dashboard.py`; тест-защита (меняем CONFIG без правки ядра) |
| **R3 Invalid contracts (битая ссылка лист/поле)** | CONFIG/DATA не согласованы | генерация падает поздно или даёт битый файл | fail-fast валидация CONFIG на входе + validator post-check |
| **R4 Переусложнение ради D3/D4** | соблазн добавить расчёт/веб/мульти-источник сразу | раздутый MVP, непроверяемые модули | жёсткий scope: D2 = генератор; D3/D4 = §6 Evolution, отдельно |
| **R5 Coupling GENERATOR↔openpyxl** | инфраструктура расползается по модулям | замена/обновление openpyxl ломает всё | openpyxl изолирован в одном слое; STYLES/CONFIG не знают openpyxl |
| **R6 Partial failures (часть листов записана, часть нет)** | ошибка в середине генерации | «почти готовый» файл принят за готовый | генерировать в память → temp-файл → atomic `rename` на финальный путь только для READY (audit G4) |
| **R7 Scaling bottleneck (большие данные)** | весь датасет материализуется в память | OOM на Termux/Android (ограниченная RAM) | write-only mode openpyxl + потоковая запись (§6) |
| **R8 Stale data (устаревший output)** | повторный запуск не очищает выход | клиент берёт старый файл | перезапись output детерминированно; validator читает именно свежий файл |
| **R11 Mutable data mid-generation** | источник данных меняется, пока идёт генерация | артефакт = смесь состояний (несогласованный) | input snapshot на входе `generate()` (audit G5); ядро не читает DATA посреди процесса |
| **R9 Formula injection из данных** | значение ячейки начинается с `=`/`+`/`-`/`@` | выполнение формул/макросов из данных | экранирование строк из DATA при записи (префикс `'`) |
| **R10 Secret leakage** | подключение внешних источников с токенами | утечка ключей (API/Bitrix24) | N/A в D2 (нет внешних API); при появлении — секреты только через `.env`, не в CONFIG |
| **Race conditions** | не применимо: single-threaded, локальный процесс | — | — |
| **Retry storms** | не применимо: нет сети | — | — |

---

## 6. Evolution Path

### MVP (D2, эта итерация)
- Один шаблон (`project_dashboard.py`), пример данных, ядро GENERATOR + VALIDATOR (structural). Расчёт формул — вне scope. Всё локально, offline.

### Growth Stage
- **Несколько шаблонов** → реестр шаблонов в CONFIG (Registry, Open-Closed) — новые дашборды без правки ядра.
- **Данные из файлов** (CSV/JSON) → адаптеры в `data/` инфраструктурном слое.
- **Большие данные** → write-only mode openpyxl, потоковая запись строк.

### Production Scale
- **Расчёт формул** → отдельный слой LibreOffice headless (`soffice --convert-to xlsx --calc`) для пересчёта; validator-разделение: structural (свой) + calculation (внешний).
- **Больше источников** (Google Sheets, API, Bitrix24) — только новые адаптеры, ядро не меняется.
- **Наблюдаемость** — структурированные логи генерации/валидации.

### Future Extensions (без переписывания)
- **Web-редактор CONFIG** — генерировать/редактировать CONFIG через UI (CONFIG уже сериализуем).
- **Разные форматы вывода** (CSV/HTML) — новый output-адаптер параллельно XLSX.
- **Темы/брендинги** — несколько `theme.py`.

---

## 7. Explicit Recommendations

**Обязательно:**
1. openpyxl изолировать в одном инфраструктурном слое GENERATOR (+ чтение в VALIDATOR); `config/`, `data/`, `styles/` не должны импортировать openpyxl.
2. Fail-fast валидация CONFIG на входе (битая ссылка лист/поле → ошибка до генерации).
3. Экранировать строки из DATA от formula injection (префикс `'` для `= + - @`).
4. Защитить инвариант «ядро не знает шаблон» архитектурным тестом: сменить CONFIG без правки `generator/*`.
5. Расчёт формул оставить отдельным слоем (LibreOffice), НЕ засовывать в validator.
6. Формулы и ссылки привязывать через `Anchor` (колонка + строка-якорь + смещение + протяжённость), а не статичными координатами; координаты разрешает только ядро в момент генерации (закрывает audit H1 — «якорение формул/ссылок к диапазонам данных»).
7. Вести lifecycle артефакта `CREATING→GENERATED→VALIDATING→READY`, публиковать атомарно (`temp → rename`, только READY) и нести в `GenerationArtifact` метаданные `generation_id` + `template_id`/`template_version` (закрывает audit G1/G3/G4); входы фиксировать snapshot на старте генерации (G5).
8. Привязку DATA→sheet строить через `DataSource` на каждый лист (`source` = имя коллекции + `field_map`); summary-листы без `data_source` (закрывает audit H2).

**Чего избегать:**
- хардкода названий листов / веток `if project_dashboard:` в `generator/*`;
- `eval`/исполнения CONFIG-кода;
- микросервисов/событий/брокеров (нет причин);
- материализации всего датасета в память на больших объёмах.

**Что можно упростить:**
- STYLES — одна тема, один файл, default-fallback;
- Orchestrator — линейная последовательность, без state-machine;
- в MVP — один шаблон, один источник данных;
- Delivery — шаг оркестратора (atomic publish), НЕ отдельный модуль/context;
- rules (формулы/ссылки) — остаются частью CONFIG/GENERATOR, без отдельного `rules/`;
- Layers (domain/application/infrastructure) — dependency boundaries, НЕ физические папки (плоская структура §4 сохраняется).

**Что нельзя откладывать:**
- разделение structural/calculation validation (R1) — заложить границу сразу, даже если расчёт добавим позже;
- экранирование формул (R9) — безопасность с первого дня;
- архитектурный тест «CONFIG-смена без правки ядра» — это и есть D2, проверить немедленно.
