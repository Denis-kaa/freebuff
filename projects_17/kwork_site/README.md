# README.md — Веб-сервис КТК ТРАСТ (Личный кабинет + дислокация)

> **Канон:** [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2/§4 + [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md)
> **Статус:** 🟡 **DRAFT** — каркас проекта в работе, код ещё не начат
> **Версия:** 0.1.0-draft
> **Дата создания:** 2026-08-17
> **Аудитория:** исполнитель (основная — этот README и есть первичная инструкция по запуску); клиент (опциональная вторичная — дополняется после приёмки Этапа 1)

---

## Что это за проект

**Клиент:** транспортная компания «**КТК ТРАСТ**» (контейнерные перевозки).
**Задача:** B2B-портал с **личным кабинетом, дислокацией контейнеров** (из 2 Excel-файлов), **онлайн-заявкой** и **интерактивной картой** маршрутов.
**Площадка:** [Kwork.ru***REMOVED***(https://kwork.ru).
**Бюджет:** **30 000 ₽** — Этап 1 (15 000 ₽) + Этап 2 (15 000 ₽).
**Срок:** согласуется после архитектурного шага (см. [`STEPS.md`***REMOVED***(STEPS.md) §0).

### Канонические документы (читать в этом порядке)

1. [`MANIFEST.md`***REMOVED***(MANIFEST.md) — паспорт (что, зачем, статус)
2. [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) — план-разбор (entity model, sitemap, asset gap, stack, 3 sharp decisions)
3. [`STEPS.md`***REMOVED***(STEPS.md) — чек-лист этапов 1+2 (что делать дальше)
4. [`LESSONS.md`***REMOVED***(LESSONS.md) — журнал уроков (CON/CAN/ANTI/PB)
5. [`бриф.md`***REMOVED***(../../projects_17/kwork_site/бриф.md) — исходный бриф клиента (Kwork-сообщение)
6. [`промт.md`***REMOVED***(../../projects_17/kwork_site/промт.md) — декомпозиция промта (архитектурный шаг Этапа 1)

> ⚠️ Этот README — **стартовая точка** + навигатор; детали — в документах выше.

---

## Быстрый старт для исполнителя

### Окружение

```bash
# Требования
python --version      # Python 3.10+
sqlite3 --version     # ≥ 3.x (WAL поддерживается нативно)
git --version

# Создать venv (после старта кода — Этап 1.1)
python -m venv .venv
source .venv/bin/activate  # на Termux: `.venv/bin/activate`

# Установить зависимости (после появления requirements.txt)
pip install -r requirements.txt
```

### Где мы сейчас

🟡 **Каркас проекта в работе.** Код ещё не начат. Блокеры §0 в [`STEPS.md`***REMOVED***(STEPS.md) — **до старта Этапа 1.0**.

### Покрытие каркаса (per [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2)

| Файл | Статус | Когда появится |
|---|:---:|---|
| `MANIFEST.md` | 🟢 готов | — |
| `LESSONS.md` (пустой CON/CAN/ANTI/PB) | 🟢 готов | Первая запись — по ходу Этапа 1.0 |
| `README.md` (навигатор) | 🟢 готов | — |
| `STEPS.md` (чеклист 1+2) | 🟢 готов | — |
| `01_PLAN_BREAKDOWN.md` (research-precursor) | 🟢 готов | — |
| `decisions/DECISIONS.md` + `ADR-NNN_*.md` | 🟡 | Этап 1.0 — принятие ADR-001 |
| `ROADMAP.md` | 🟡 | После Этапа 1 ТЗ (задача №1 из `промт.md`) |
| `RUNNABLE.md` | 🟡 | К концу Этапа 1 (первый runnable artifact) |
| `CHECKLIST.md` | 🟡 | К концу Этапа 1 |

**Итого: 5 из 9 файлов каркаса готовы; 4 — по графику Этапов 1.0–2.5 (см. [`STEPS.md`***REMOVED***(STEPS.md)).**

> 📌 Отдельная obligation per [`PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §8: **регистрация проекта** в [`docs_10/projects_meta/PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) — однострочная запись (slug + статус + краткое назначение). Не блокирует код; можно сделать **на любом шаге каркаса**. См. раздел «Корневые реестры» в [`MANIFEST.md`***REMOVED***(MANIFEST.md).

### Запуск локально (после старта кода — Этап 1.2 → 1.4)

```bash
# Инициализация БД (SQLite WAL)
flask --app app.main init-db         # или
python -m app.cli init-db

# Запуск dev-сервера
flask run --port 8150                # если Flask
# или
uvicorn app.main:app --port 8150 --reload   # если FastAPI

# Открыть в браузере
http://127.0.0.1:8150/login
```

### После Этапа 1.1 — dev workflow (тесты, линт, type-check)

> ⚠️ Эти команды начнут работать только после Этапа 1.1 (`requirements.txt` + начальные тесты). На текущей стадии (каркас проекта) инфраструктура ещё не настроена.

```bash
# Прогон тестов проекта
python -m pytest tests/ -q

# Линт + формат
ruff check .
black --check .

# Type-check
mypy . --ignore-missing-imports

# Pre-commit (перед коммитом)
pre-commit run --all-files
```

> Полный список тестовых/линт-таргетов — в `Makefile` (после Этапа 1.1).

---

## Структура проекта (план)

```
projects_17/kwork_site/
├── README.md              # ← ВЫ ЗДЕСЬ (навигатор)
├── MANIFEST.md            # паспорт проекта (DRAFT)
├── 01_PLAN_BREAKDOWN.md   # план-разбор (entity model, sitemap, asset gap, stack)
├── STEPS.md               # чек-лист этапов 1+2 со ссылками
├── LESSONS.md             # журнал уроков (CON/CAN/ANTI/PB) — пустой
├── бриф.md                # исходный бриф клиента (вход, не править)
├── промт.md               # декомпозиция промта (вход, не править)
│
├── decisions/             # появляется в Этапе 1.0
│   ├── DECISIONS.md       # индекс ADR
│   └── ADR-NNN_*.md       # архитектурные решения
│
├── docs/                  # опц. — runtime-документация (заметки по ходу)
│
├── app/                   # код приложения (Этап 1.1 →)
│   ├── main.py            # entry-point
│   ├── auth/              # Этап 1.2: авторизация + tenant-isolation
│   ├── excel_pipeline/    # Этап 1.3: парсер / сведение / загрузка
│   ├── ui/                # Jinja2 шаблоны + статические страницы
│   ├── map/               # Этап 2.3: Leaflet-карта + SVG-overlay
│   └── ...
│
├── static/                # SVG-лого, иконки, favicon (Этап 2.1 → 2.2)
│   ├── favicon.ico
│   ├── logo.svg
│   ├── logo_mono.svg
│   └── icons.svg
│
├── tests/                 # pytest (Этап 1.1 → 1.6, Этап 2.4)
│   ├── test_auth.py
│   ├── test_excel_pipeline.py
│   ├── test_tenant_isolation.py
│   └── ...
│
├── data/                  # SQLite БД + Excel-фикстуры (не в git)
│   ├── ktv_trust.db
│   └── samples/
│       ├── dislocations_aug.xlsx
│       └── dislocations_sep.xlsx
│
├── requirements.txt       # появится в Этапе 1.1
├── pyproject.toml         # ruff/black/mypy конфиги
├── Makefile               # dev / test / lint / run
├── .env.example           # шаблон env vars (SECRET_KEY, SMTP_*)
├── .gitignore             # НЕ коммитим: data/, .venv/, .env, *.db
│
├── RUNNABLE.md            # появится в Этапе 2.5 — инструкции по запуску
└── CHECKLIST.md           # появится в Этапе 2.5 — финальный чек-лист готовности
```

---

## Архитектурные принципы (per [`промт.md`***REMOVED***(../../projects_17/kwork_site/промт.md) + [`decisions/ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) 🟢 + [`SPEC.md`***REMOVED***(SPEC.md) §6.2)

> **Обязательные** для всего кода проекта. Нарушение — это урок ANTI в [`LESSONS.md`***REMOVED***(LESSONS.md).

1. **Изоляция контекстов и данных** — каждый клиент видит **только свои** контейнеры/заявки. Реализуется через row-level `WHERE company_id = ?` из сессии пользователя (per [`decisions/ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) 🟢 ACCEPTED 2026-08-17 + [`SPEC.md`***REMOVED***(SPEC.md) §6.2 `locked architectural decisions`). **Любой query без этой проверки — утечка данных.**

   **Реализация (per ADR-001 §5.3):**

   - Каждый запрос **обязан** идти через repository-обёртку (`app/database/repository.py`); raw SQL без обёртки = утечка (NFR-007).
   - `current_company()` middleware читает `company_id` из bcrypt-cookie-session и прокидывает в repository.
   - SQL DDL: каждая тенантная таблица (User / Container / Dislocation / MapPoint / Route / Order) содержит `company_id` FK (INV-1 + NFR-007).
   - Тест-план: **≥ 5 автотестов** tenant-isolation (NFR-010); coverage repository-функций **≥ 80 %** (NFR-011).
2. **Модульность + сменный ИИ-мозг** — в MVP это только Python-скрипт обработки Excel (Этап 1.3). Мультиагентная система = **out-of-scope** по бюджету.
3. **Поэтапность под доступные ресурсы** — жёсткое разделение Этап 1 (15 000 ₽) → Этап 2 (15 000 ₽). **Feature creep без доплаты запрещён** (см. блок out-of-scope в [`STEPS.md`***REMOVED***(STEPS.md)).

---

## Стандарт качества кода

Обязательно перечитать перед каждой правкой: [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md).

Кратко:

- **Читаемость:** docstrings, понятные имена, единый стиль.
- **Надёжность:** обработка ошибок, логирование, идемпотентность.
- **Безопасность:** bcrypt для паролей, **никаких root**, секреты в `.env`, валидация ввода, CSRF, no shell=True.
- **UX:** DEBUG/QUIET-флаги, прогресс-бар, exit-коды корректные.
- **Принципы:** KISS, DRY, SOLID, идиоматичный Python.

---

## How-to для клиента (после приёмки Этапа 1)

> ⚠️ Этот раздел будет **дополнен после Этапа 1.7** (демонстрация клиенту). До тех пор — **read-only** для клиента.

### Что клиент получает на каждом этапе

- **Этап 1** — рабочий MVP: авторизация в ЛК, таблица дислокации контейнеров компании (из 2 Excel-файлов), онлайн-заявка (через SMTP на email диспетчера КТК ТРАСТ).
- **Этап 2** — интерактивная карта маршрутов (Leaflet+OSM), SVG-логотип для сайта (3 варианта), финальное тестирование.

### Где развёрнуто

> TBD — согласуется в Этапе 1.0 (VPS / shared / облако клиента).

### Как войти в ЛК

```text
URL:       https://<домен>/login
Логин:     <email, выданный админом КТК ТРАСТ>
Пароль:    <выдаёт админ КТК ТРАСТ; сменить после первого входа>
```

### Как добавить нового сотрудника клиента

Через админку КТК ТРАСТ → `/admin/users` → «Создать пользователя» (с привязкой к Company).

### Часто задаваемые вопросы (FAQ)

*Пополняется по ходу Этапа 1.6 → 2.4. Сюда выносятся реальные вопросы клиента из Kwork-чата.*

---

## Состояние и версии

| Поле | Значение |
|---|---|
| **Версия** | 0.1.0-draft |
| **Статус** | 🟡 DRAFT |
| **Дата создания** | 2026-08-17 |
| **Этап** | каркас проекта (блокеры §0 в [`STEPS.md`***REMOVED***(STEPS.md)) |

См. детальный статус в [`MANIFEST.md`***REMOVED***(MANIFEST.md).

---

## Конфиденциальность

> ⚠️ **Материалы этого проекта — коммерческая тайна клиента.**

- **Не публиковать** исходный код и материалы в общем реестре [`docs_10/`***REMOVED***(../../docs_10/) (за исключением одной строки в [`PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) — см. PROJECT_RULES §8).
- **Не передавать** материалы третьим лицам без явного согласия клиента ТК «КТК ТРАСТ».
- При передаче результата клиенту — отдельный пакет с инструкцией по деплою (формируется в Этапе 2.5).

---

## Cross-links

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2 (каркас) + §4 (порядок работы) + §8 (чек-лист)
- [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md) — стандарт готовности (RUNNABLE/CHECKLIST)
- [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md) — регламент качества кода
- [`MANIFEST.md`***REMOVED***(MANIFEST.md) — паспорт проекта
- [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) — план-разбор
- [`STEPS.md`***REMOVED***(STEPS.md) — чек-лист этапов
- [`LESSONS.md`***REMOVED***(LESSONS.md) — журнал уроков
- `projects_17/lead_aggregator/README.md` — образец fully-scaffolded README (для сравнения)
- `projects_17/diet_platform/README.md` — альтернативный формат (для сравнения)
- [`docs_10/projects_meta/PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) — сводный реестр проектов платформы (однострочная регистрация проекта)

---

*README создан: 2026-08-17 · Status 🟡 DRAFT · Канон: PROJECT_RULES.md §4 + PROJECT_REQUIREMENTS.md · Автор: Buffy (Workspace OS / Freebuff)*
