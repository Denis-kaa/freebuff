# ADR-002: Стек Excel-движка (Python vs PHP) для `kwork_site`

> **Статус:** ⚪ **DRAFT** — ждёт ответа клиента по **Q1** в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) (TBD).
> **Дата черновика:** 2026-08-17
> **Дата принятия:** TBD (после ответа клиента → перевод ⚪ → 🟢 ACCEPTED 🔴 DEPRECATED ⚪ DRAFT остаётся при отказе от обеих альтернатив в пользу третьего пути)
> **Категория:** Архитектура / Tech-debt
> **Блокер:** 🔴 **Q1** в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) (Python vs PHP, дословная цитата клиента: «*php или питон скрипт*» из [`бриф.md`***REMOVED***(../бриф.md)).
> **Зависимости:** [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1 (Python canonical, Backend-row таблицы «Архитектурный минимум») + [`SPEC.md`***REMOVED***(../SPEC.md) §5.1 (технический стек).
> **Канон-формат:** **Context / Options / Decision / Rationale / Consequences** ([шаблон в `DECISIONS.md`***REMOVED***(DECISIONS.md#2-шаблон-adr-canonical-format)).

---

## 1. Контекст

Клиент в [`бриф.md`***REMOVED***(../бриф.md) сформулировал движок обработки Excel-файлов как **«php или питон скрипт»** — это явная альтернатива, без явного предпочтения. [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1 фиксирует **Python как default** (Backend-row в таблице «Архитектурный минимум»): (а) явное указание в [`промт.md`***REMOVED***(../промт.md) «Python-скрипт парсинга/сведения 2 Excel-файлов»; (б) бюджет 30 000 ₽ не покрывает PHP-specific инфру (LAMP-stack + composer-зависимости + отдельный dev-цикл). *Замечание: §8 Decisions в PLAN_BREAKDOWN не про Python — Decision 1/2/3 относятся к freeze-схемы / механики-загрузки / email-доставке заявок.*

Однако это **решение client-facing** — клиент должен явно подтвердить стек до старта кода. До подтверждения — ADR остаётся в статусе ⚪ DRAFT.

**Ключевые ограничения:**

- **Бюджет** 30 000 ₽ (Этап 1 = 15 000 ₽, Этап 2 = 15 000 ₽) — не позволяет две альтернативные кодовые базы.
- **[`SPEC.md`***REMOVED***(../SPEC.md) §5.1** уже фиксирует Python + SQLite WAL + Jinja2 + Bootstrap 5 + HTMX; PHP-альтернатива потребовала бы переписать SPEC.md §5/§6 + пересобрать таймлайн.
- **Время:** до ответа клиента Этап 1.0 (архитектурный шаг) блокирован по пункту «Согласовать Python vs PHP с клиентом (блокер §0 #1)» (per [`STEPS.md`***REMOVED***(../STEPS.md) §1.0).
- **Refundable:** при отказе клиента от Python — переоценка трудозатрат и бюджета (PHP-альтернатива ≈ +5–10 ч к Этапу 1) — см. §5.2 (отрицательные последствия).

---

## 2. Рассмотренные варианты

### Вариант A: Python (FastAPI или Flask) — **рекомендуется**

Per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1: Python + FastAPI/Flask — **canonical default**. Excel-движок: `pandas` + `openpyxl`. Backend-фреймворк выбирается между FastAPI (async, type hints, OpenAPI авто) и Flask (минималистичный, sync) — обе укладываются в 30 000 ₽.

- **Плюсы:**
  - ✅ Соответствует [`промт.md`***REMOVED***(../промт.md) (явное указание «Python-скрипт парсинга»).
  - ✅ Минимальные изменения SPEC.md — [`SPEC.md`***REMOVED***(../SPEC.md) §5.1 уже описывает Python-стек.
  - ✅ Совместимо с ADR-001 (auth + tenant isolation на SQLite + cookie-session — Python-native).
  - ✅ `pandas` + `openpyxl` — стандарт для Excel-парсинга в B2B (читается большинством разработчиков).
  - ✅ Тестируемость: `pytest` ecosystem.
- **Минусы:**
  - 🟡 FastAPI/Flask — нужен выбор (оба ок, но требует мини-disclosure).
  - 🟡 Python single-threaded GIL — при большой нагрузке (>100k контейнеров) потребуется multiprocessing или миграция на FastAPI async.
- **Цена:** низкая (одна `requirements.txt`, один `venv`).

### Вариант B: PHP (LAMP-stack или PHP-FPM)

Реализация всего сервиса на PHP: PHP-парсер Excel (PhpSpreadsheet), backend на Laravel или Symfony, frontend на Blade или Nuxt.

- **Плюсы:**
  - ✅ Если у клиента **уже** есть PHP-инфра на hosting-cliente (типично для Kwork-проектов российских хостингов) — деплой проще.
  - ✅ LAMP-stack дешёвый (shared-hosting).
- **Минусы:**
  - ❌ **Требует переписать** [`SPEC.md`***REMOVED***(../SPEC.md) §5.1 (стек) + §6.2 (auth-pattern) + §6 (architecture) — весь технический ТЗ пересобирается.
  - ❌ Расхождение с [`промт.md`***REMOVED***(../промт.md) (явное указание Python).
  - ❌ Vendor lock-in: PhpSpreadsheet, Laravel-зависимости — всё opensource но для Kwork-проекта на 30 000 ₽ overhead ощутим.
  - ❌ Нет easy integration с ADR-001 (tenant isolation через row-level SQL применим, но cookie-session + bcrypt надо повторять на PHP).
  - ❌ Сложнее с [`README.md`***REMOVED***(../README.md) «быстрый старт» примером (нужен LAMP-инструкция, не Python venv).
- **Цена:** средняя (≈+8–12 ч на адаптацию SPEC + перекодирование) — **риск выхода за 30 000 ₽**.

### Вариант C: Гибрид — Python backend + статический frontend на PHP

Минимальный PHP только для hosting-на-клиент-сайт (публичный landing, redirect на Python-API). Python отвечает за всю логику (Excel-pipeline, ЛК, дислокация).

- **Плюсы:**
  - ✅ Если клиент **настаивает** на PHP у себя — landing/redirect удовлетворяет, а основной backend остаётся Python.
- **Минусы:**
  - ❌ Сложность: 2 codepaths, 2 deploy-process.
  - ❌ Per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.2, landing **OUT-OF-SCOPE** — гибрид не нужен.
- **Цена:** ❌ **out-of-scope per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.2**.

---

## 3. Решение

⚠️ **DRAFT-плейсхолдер — будет заполнен после Q1.**

После ответа клиента Q1 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) один из вариантов ниже станет финальным Decision:

- **Если «Python» или «Python (default)»** → принять **Вариант A** (Python — FastAPI или Flask; выбор между ними — отдельное микро-решение в [`STEPS.md`***REMOVED***(../STEPS.md) §1.0).
- **Если «PHP»** → пересмотреть [`SPEC.md`***REMOVED***(../SPEC.md) §5 + ADR-002 → переписать таймлайн → **возможен отказ от заказа**, если бюджет 30 000 ₽ не покрывает PHP-путь (per §5.2).
- **Если «Hybrid» или «рассмотрите другие»** → ⚪ DRAFT остаётся; открыть новый ADR (ADR-002b) под альтернативный стек.

**Текущее намерение** (будет вычеркнуто при принятии ADR): принять **Вариант A** (Python).

> 📌 **Действия после ответа:** обновить этот раздел ⚠️ → ✅ Решение; вычеркнуть плейсхолдер; обновить [`STEPS.md`***REMOVED***(../STEPS.md) §1.0 чекбокс; обновить [`DECISIONS.md`***REMOVED***(DECISIONS.md) статус ⚪ → 🟢/🔴.

---

## 4. Обоснование (Rationale)

### 4.1 Соответствие [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1

> **Цитата PLAN_BREAKDOWN §5.1:** «Backend: **Python** (FastAPI **или** Flask) — НЕ PHP. Промт явно: "Python-скрипт парсинга/сведения 2 Excel-файлов"; в брифе альтернатива "php или питон" — это 🔴-блокер, нужно подтверждение клиента»

PLAN_BREAKDOWN уже выбрал A как default; ADR-002 фиксирует формально.

### 4.2 Соответствие бюджету

Вариант A = 1 `requirements.txt` + FastAPI/Flask setup = **минимум часов**. Вариант B требует переписать SPEC + адаптировать ≈+8–12 ч; риск выхода за 30 000 ₽.

### 4.3 Совместимость с ADR-001

ADR-001 (Cookie-session + bcrypt + row-level SQL tenant-isolation) реализуется идентично на Python (Flask/FastAPI). На PHP потребовалось бы дублировать middleware + repository layer.

### 4.4 Соответствие [`SPEC.md`***REMOVED***(../SPEC.md) §5.1 (уже написанного)

[`SPEC.md`***REMOVED***(../SPEC.md) §5.1 уже описывает Python-стек (FastAPI/Flask + pandas + openpyxl + Jinja2 + SQLite WAL + Bootstrap 5 + HTMX + Leaflet). Принятие варианта A = **нет изменений SPEC.md**; вариант B = **переписать SPEC.md**.

---

## 5. Последствия (Consequences)

### 5.1 Положительные *(при принятии Варианта A — Python)*

- ✅ **Минимальная стоимость:** укладывается в 30 000 ₽, нет пере-архитектурирования.
- ✅ **Совместимо с ADR-001** (Cookie-session + repository-obligation + NFR-007/010/011 применимы напрямую).
- ✅ **Тестируемость:** `pytest` ecosystem + стандартные mock-фреймворки для tenant-isolation (см. [ADR-001 §5.4***REMOVED***(ADR-001_auth_tenant_isolation.md)).
- ✅ **Богатая экосистема** для Excel: `pandas` + `openpyxl` + `xlrd` (legacy).
- ✅ **Быстрый онбординг** для следующего разработчика (Python популярнее PHP в 2026 для B2B-MVP).

### 5.2 Отрицательные / риски *(при принятии Варианта B — PHP)*

- ❌ **Переписать [`SPEC.md`***REMOVED***(../SPEC.md) §5.1 + §6.2** — техническое ТЗ целиком (≈+2 ч).
- ❌ **Переписать ADR-001** под PHP-аналогию (Cookie-session + bcrypt + row-level SQL остаются, но middleware/repository layer — на PHP) — ≈+3 ч.
- ❌ **Переписать README.md** «Быстрый старт» под LAMP вместо Python venv — ≈+1 ч.
- ❌ **Таймлайн:** ≈+8–12 ч overhead → риск выхода за 30 000 ₽ → вероятный **отказ от заказа** или **сильное сокращение scope**.
- ❌ **Vendor lock-in** на `PhpSpreadsheet`, Laravel/Symfony.

### 5.3 Требования к реализации (при принятии Варианта A)

> ⚠️ Пункты ниже — **под Вариант A** (Python). При принятии Варианта B (PHP) — переписать.

1. `requirements.txt` фиксирует версии:
   - `fastapi` или `flask` (выбор — отдельное решение в [`STEPS.md`***REMOVED***(../STEPS.md) §1.0)
   - `pandas` (≥ 2.0), `openpyxl` (≥ 3.1), `xlrd` (≥ 2.0, для legacy .xls)
   - `bcrypt` (≥ 4.0), `jinja2` (≥ 3.1), `pydantic` (≥ 2.0 для FastAPI)
   - `pytest` (≥ 7.0), `ruff`, `black`, `mypy`
2. `pyproject.toml` настраивает ruff/black/mypy.
3. **Excel-парсер:** `app/excel_pipeline/parser.py` — модуль с функциями `parse_workbook(path) → DataFrame`, `reconcile(dfs) → DataFrame` (сведение по общему ключу из [ADR-003 §3 Decision***REMOVED***(ADR-003_excel_schema_v1.md), когда он будет принят).
4. **FastAPI BackgroundTasks** или Flask executor — загрузка асинхронно, чтобы UI не блокировался.
5. **SMTP-отправка заявок** (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §8 Decision 3) — `aiosmtplib` или `smtplib`.

### 5.4 Требования к тестированию

- **≥ 3 парсер-теста:** happy path, частично сломанные данные, пустой файл.
- **≥ 1 тест сведения** на зафиксированных фикстурах (после принятия ADR-003).
- **≥ 5 tenant-isolation тестов** — обязательно (см. [ADR-001 §5.4***REMOVED***(ADR-001_auth_tenant_isolation.md)).
- Coverage target: **≥ 80 %** строк в `app/excel_pipeline/`.

### 5.5 ADR supersedes / related

| ADR | Relationship |
|---|---|
| [ADR-002***REMOVED***(ADR-002_python_vs_php.md) | **этот ADR** *(⚪ DRAFT — ждёт Q1)* |
| [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md) | 🟢 ACCEPTED — auth + tenant-isolation **независимы** от выбора Python/PHP (Cookie-session + row-level SQL применимы на обоих стеках). |
| [ADR-003***REMOVED***(ADR-003_excel_schema_v1.md) | ⚪ DRAFT (зависит от Q2). При выборе варианта **A** (Python) — парсер на pandas; при варианте **B** (PHP) — парсер на PhpSpreadsheet (миграция кода ~80 %). |

---

## Cross-links

### Проектные документы

- [`../MANIFEST.md`***REMOVED***(../MANIFEST.md) — Scope Rules (аддитивность, конфиденциальность)
- [`../SPEC.md`***REMOVED***(../SPEC.md) §5.1 (технический стек; уже на Python), §11 Q1 — open question
- [`../STEPS.md`***REMOVED***(../STEPS.md) §0 #1 (блокер) + §1.0 (Архитектурный шаг) + §1.3 (Excel pipeline)
- [`../01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1 (стек, Python canonical) + §8 Decision 2 (default = Python)
- [`../CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md) **Q1** — дословная цитата клиента «php или питон»; default = Python; действие после ответа
- [`../бриф.md`***REMOVED***(../бриф.md) — сырой бриф клиента (где встречается фраза)

### Канонические источники платформы

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) §3.1 (уроки в проекте) + §7 (миграция ADR)

### Соседние ADR

- [`DECISIONS.md`***REMOVED***(DECISIONS.md) — индекс project-local ADR
- [`ADR-001_auth_tenant_isolation.md`***REMOVED***(ADR-001_auth_tenant_isolation.md) — 🟢 ACCEPTED
- [`ADR-003_excel_schema_v1.md`***REMOVED***(ADR-003_excel_schema_v1.md) — ⚪ DRAFT (зависит от Q2)

### Стилевые образцы

- [`ADR-001_auth_tenant_isolation.md`***REMOVED***(ADR-001_auth_tenant_isolation.md) — структурный образец (5 канонических разделов)

---

*ADR создан: 2026-08-17 (черновик) · Статус: ⚪ DRAFT до ответа клиента Q1 · Канон: Context/Options/Decision/Rationale/Consequences · Опоры: PLAN_BREAKDOWN §5.1/§8 + бриф.md «php или питон» + SPEC §5.1 · Автор: Buffy (Workspace OS / Freebuff)*
