# SPEC.md — Техническое задание
## «Веб-сервис КТК ТРАСТ» (Личный кабинет + дислокация)

> **Версия документа:** 0.1.0
> **Дата создания:** 2026-08-17
> **Статус:** 🟡 **DRAFT** — готов к review Этапа 1.0; код ещё не начат; до старта нужны блокеры ([§11***REMOVED***(#11-открытые-вопросы-блокеры))
> **Канонические ссылки проекта:** [`MANIFEST.md`***REMOVED***(MANIFEST.md) · [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) · [`STEPS.md`***REMOVED***(STEPS.md) · [`LESSONS.md`***REMOVED***(LESSONS.md) · [`README.md`***REMOVED***(README.md)
> **Стилевой образец:** [`projects_17/tg_terminal_messenger/docs/original/tz.md`***REMOVED***(../tg_terminal_messenger/docs/original/tz.md) — канон FR-NNN / NFR-NNN / DoD

> ⚠️ **Конфиденциальность:** этот документ — коммерческая тайна клиента ТК «КТК ТРАСТ». Не публиковать в общем реестре `docs_10/` кроме одной строки в `PROJECTS_OVERVIEW.md` per `PROJECT_RULES.md` §8.

---

## 1. Обзор проекта

### 1.1 Назначение

B2B-портал для транспортной компании «КТК ТРАСТ»: клиенты (юр. лица — грузополучатели) получают доступ к **личному кабинету** с актуальной **дислокацией контейнеров** (сводится из 2 Excel-файлов, загружаемых администратором КТК ТРАСТ), могут оставлять **онлайн-заявки** на новые перевозки, и пользоваться **интерактивной картой маршрутов** с точками погрузки/выгрузки и линиями.

### 1.2 Целевая аудитория

- **Сотрудники клиентских компаний** (юр. лица) — основная аудитория ЛК (видят только свои контейнеры и заявки).
- **Администратор КТК ТРАСТ** — загружает Excel-файлы в БД, управляет учётками клиентов (минимум: list + create + reset).

### 1.3 Ключевые возможности (MVP)

- 🔐 Cookie-аутентификация в ЛК (BCrypt + `Secure; HttpOnly; SameSite=Lax`).
- 📊 Табличный дашборд с фильтрами/сортировкой по контейнерам компании.
- 📦 Автоматический пайплайн парсинга и сведения 2 Excel-файлов (pandas + openpyxl).
- ✉️ Онлайн-заявка с отправкой на email диспетчера КТК ТРАСТ через SMTP.
- 🗺️ Интерактивная карта (Leaflet + OSM + SVG-overlay маршрутов).
- 🖼️ SVG-логотип КТК ТРАСТ (качественная конвертация PNG → SVG).

### 1.4 Бюджет и срок

- **Общий бюджет:** 30 000 ₽ (= 15 000 ₽ × 2 этапа).
- **Этап 1:** «Базовый сервис и обработка данных» — 15 000 ₽.
- **Этап 2:** «Гео-интеграция и визуализация» — 15 000 ₽.
- **Срок:** согласуется после архитектурного шага (Этап 1.0).

### 1.5 Бюджетный гейт (явный)

> Все НЕ-функциональные требования (NFR) и архитектурные решения в этом документе продиктованы **бюджетом 30 000 ₽**. Любая фича, выходящая за пределы MVP, согласуется с клиентом как **дополнительный заказ**, не как расширение текущего.

---

## 2. Функциональные требования (FR)

> Соглашение: 🟢 = MVP (в скоупе обязательно) · 🟡 = SHOULD (если останется бюджет) · 🔵 = COULD (только при доплате клиента) · ❌ = WON'T (явно out-of-scope).

### 2.1 🟢 MUST (MVP обязательно для приёмки Этапов 1+2)

#### A. Аутентификация и tenant-isolation

- **FR-001:** Аутентификация по email + пароль с хэшированием bcrypt (cost ≥ 12).
- **FR-002:** Cookie-сессии с атрибутами `Secure; HttpOnly; SameSite=Lax; Path=/` + CSRF-token для всех mutating-запросов.
- **FR-003:** Каждый query к данным контейнеров/заявок фильтрует по `company_id` из текущей сессии. Ни один SQL query не возвращает данные чужой компании — это инвариант проверяется тестами на изоляцию (см. §8 AC-009).
- **FR-004:** Logout очищает cookie + инвалидирует серверную сессию.
- **FR-005:** Смена пароля требует ввода текущего; BCrypt-rehash при успехе.

#### B. Личный кабинет — таблица дислокации

- **FR-006:** Страница `/dashboard` — таблица контейнеров **только текущей компании** (per FR-003), колонки: `container_no`, `type/size`, `current_status`, `current_lat/lon`, `updated_at`, `route_summary`.
- **FR-007:** Фильтры по статусу, дате обновления, маршруту + серверная пагинация (если строк > 1000).
- **FR-008:** Сортировка по всем колонкам; дефолт — по `updated_at DESC`.
- **FR-009:** Empty state, loading state, error state — единый шаблон.
- **FR-010:** Клик по строке → мини-карточка контейнера (offcanvas или модалка) с историей дислокации.

#### C. Excel-pipeline

- **FR-011:** Страница `/admin/upload` (только для admin-роли) — форма загрузки 2 Excel-файлов.
- **FR-012:** Серверная валидация файлов (тип `.xlsx`/`.xls`, размер ≤ 10 MB, заголовки).
- **FR-013:** Парсинг через `pandas` + `openpyxl`, сведение по **общему ключу** `container_no` (по умолчанию; уточняется после получения эталонных файлов).
- **FR-014:** Результат сведения сохраняется в SQLite (UPSERT в `Container` + append в `Dislocation (log)`); не-сведённые строки — в error-отчёт админу.
- **FR-015:** Загрузка асинхронна (FastAPI BackgroundTasks) — UI не блокируется.
- **FR-016:** Логирование в таблицу `UploadLog`: `file_name`, `uploaded_by`, `parsed_rows`, `errors_json`, `uploaded_at`.

#### D. Онлайн-заявка (per §8 Decision 3)

- **FR-017:** Страница `/request/new` (только для client-роли) — форма с полями согласно Q5 ([§11***REMOVED***(#11-открытые-вопросы-блокеры)). **Default-набор полей (если клиент молчит на Q5):** `contact_name`, `contact_phone`, `contact_email`, `route_from` (MapPoint или свободный адрес), `route_to`, `cargo_description` (текст), `preferred_date` (опц.). Дополнительные поля — после согласования с клиентом.
- **FR-018:** Client-side валидация (HTML5 + лёгкий JS) + server-side (Pydantic).
- **FR-019:** Submit → отправка email диспетчеру КТК ТРАСТ через SMTP (реквизиты из `SMTP_*` env vars).
- **FR-020:** Confirmation page + опциональный confirmation email клиенту.
- **FR-021:** Anti-spam: rate limit per IP + session (≤ 5 заявок / час).
- **FR-022:** CSRF защита формы.

#### E. Админ-функционал КТК ТРАСТ (минимальный)

- **FR-023:** Страница `/admin/users` — list + create + reset пароля (только admin-роль).
- **FR-024:** Страница `/admin/upload` — загрузка Excel (см. C).
- ~~**FR-025:** Реестр заявок~~ — ❌ **вычеркнуто** per §8 Decision 3 (заявки идут на email). **ID FR-025 намеренно пропущен** — следующий допустимый FR-ID — FR-026.

#### F. Интерактивная карта (Этап 2)

- **FR-026:** Страница `/map` — Leaflet + OSM-тайлы (open-source), pin'ы точек погрузки (зелёный), выгрузки (синий), транзитные (серый).
- **FR-027:** SVG-overlay линий маршрутов (Polyline с vertex-точками).
- **FR-028:** Tooltip по клику: ID контейнера, текущий статус, дата обновления.
- **FR-029:** Layer-control: «все / только моя компания / по статусу».
- **FR-030:** Полноэкранный layout карты.
- **FR-031:** Pinch-zoom на мобильном viewport (тестируется в Этапе 2.4).

#### G. SVG-логотип (Этап 2)

- **FR-032:** Конвертация 3 растровых PNG-вариантов → SVG (auto-trace + 1 раунд ручных правок).
- **FR-033:** Монохромный вариант (для favicon / печати).
- **FR-034:** Тест читаемости SVG на 16/32/64/256 px (retina/HD).

### 2.2 🟡 SHOULD (рекомендуемые; если останется время/бюджет)

- **FR-035:** Мини-нагрузочный тест: `locust` или аналог, 10 одновременных пользователей.
- **FR-036:** Confirmation email клиенту при успешной заявке.
- **FR-037:** Server-side pagination через DataTables.js (если тестовые данные > 1000 строк).
- **FR-038:** Pin clustering на карте при > 100 контейнеров (без clustering — перегрузка render).
- **FR-039:** E2E-тесты критических путей через Playwright.

### 2.3 🔵 COULD (только за доплату клиента)

- **FR-040:** Публичный landing-сайт (корпоративный hero, маркетинг).
- **FR-041:** Telegram-бот для уведомлений.
- **FR-042:** Иерархия ролей внутри клиентской компании (диспетчер / менеджер / бухгалтер / директор).
- **FR-043:** BI-дашборд с графиками (объём перевозок, среднее время доставки).
- **FR-044:** Email-рассылки (mass mailing).
- **FR-045:** Интеграция с 1С / CRM клиента.

### 2.4 ❌ WON'T (явно out-of-scope для этого заказа)

- ❌ iOS / Android нативное мобильное приложение.
- ❌ Native push-уведомления.
- ❌ CI/CD в облако, продвинутый мониторинг, system-логи в облако.
- ❌ UI-реестр заявок (per §8 Decision 3 — заявки на email).
- ❌ OAuth / SSO (только email+пароль).
- ❌ WebSocket-обновления дислокации в реальном времени (только по загрузке нового Excel).

---

## 3. Нефункциональные требования (NFR)

### 3.1 Производительность

- **NFR-001:** Время отклика UI **< 200 ms** для действий без сетевых запросов.
- **NFR-002:** Загрузка дашборда (`/dashboard`) **≤ 1 сек** при ≤ 1000 контейнеров в компании (с пагинацией).
- **NFR-003:** Excel-парсинг **≤ 30 сек** для 10 000 строк (в фоне; UI не блокируется).
- **NFR-004:** Открытие карты (`/map`) **≤ 1.5 сек** для ≤ 100 pin'ов без clustering.

### 3.2 Безопасность

- **NFR-005:** Пароли хранятся только в виде BCrypt-хэша (cost ≥ 12). Никогда plain / без хэша.
- **NFR-006:** Сессионная cookie — `Secure` + `HttpOnly` + `SameSite=Lax`. CSRF-token обязателен для всех POST.
- **NFR-007:** Все SQL-запросы проходят через обёртку, читающую `company_id` из сессии; **без обёртки доступ к БД запрещён** (lint-правило или codereview).
- **NFR-008:** SMTP-credentials — только из env vars, никогда в коде/репозитории.
- **NFR-009:** Нет `eval`/`exec` или `shell=True` в коде (CI/static-check).

### 3.3 Tenant-isolation (изоляция пространств)

- **NFR-010:** **Инвариант:** при наличии пользователя компании A в сессии ни один запрос к `Container` / `Dislocation` / `Order` не возвращает сущности компании B. Тестируется автотестами (AC-009).
- **NFR-011:** Каждая query в репозитории имеет явный binding `company_id` (или пустой binding = ошибка линтера). Покрытие тестами ≥ 80% repository-функций.

### 3.4 Надёжность

- **NFR-012:** Graceful shutdown при SIGINT/SIGTERM (HTTP-сервер, BackgroundTasks завершают in-flight).
- **NFR-013:** DB connection — переиспользуемый connection pool (не открывать на каждый запрос).
- **NFR-014:** Все ошибки логируются с `request_id` (для traceability).

### 3.5 Совместимость

- **NFR-015:** Python 3.10+ (термин «не ниже 3.10»).
- **NFR-016:** Поддержка браузеров: актуальные Chrome / Edge / Firefox / Safari (desktop + mobile viewport). IE — **не поддерживается**.
- **NFR-017:** Мобильный viewport ≥ 360 px (iPhone SE baseline).
- **NFR-018:** SQLite WAL-mode активен (`PRAGMA journal_mode=WAL` выставляется при инициализации БД).

### 3.6 Локализация

- **NFR-019:** UI на русском (основной язык клиента).
- **NFR-020:** Тексты ошибок — на русском (для админа и клиента ЛК).
- **NFR-021:** Зарезервированная таблица `Order` (см. §4.8) **НЕ создаётся** при стандартной инициализации БД. Автоматическая миграция добавляет её **только при ADR-NNN, активирующем БД-реестр заявок (Этап 3 / пост-MVP)** — **не** при Этапе 2.6 («Приёмка Этапа 2»), который является приёмочным этапом, а не кодошагом. До активации ADR заявки хранятся только в SMTP-потоке (per §8 Decision 3).

---

## 4. Структура данных (data schema)

> **Конвенция:** SQL DDL-стиль; типы SQLite3; FK-ограничения включены. Все ID — INTEGER PRIMARY KEY (autoincrement в SQLite по умолчанию). Все timestamps — `TEXT` (ISO8601 UTC).

### 4.1 `Company` (юр. лицо — клиент)

```sql
CREATE TABLE Company (
  id              INTEGER PRIMARY KEY,
  name            TEXT NOT NULL,
  inn             TEXT NOT NULL UNIQUE,        -- ИНН
  contract_no     TEXT,                         -- № договора
  email           TEXT NOT NULL,                -- основной контактный email
  phone           TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','archived'))
);
```

### 4.2 `User` (сотрудник компании или админ КТК ТРАСТ)

```sql
CREATE TABLE User (
  id              INTEGER PRIMARY KEY,
  company_id      INTEGER,                      -- NULL для admin (КТК ТРАСТ)
  email           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,                -- bcrypt(cost=12+)
  role            TEXT NOT NULL CHECK (role IN ('client','admin')),
  full_name       TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  last_login_at   TEXT,
  FOREIGN KEY (company_id) REFERENCES Company(id) ON DELETE CASCADE
);
CREATE INDEX idx_user_company ON User(company_id);
```

### 4.3 `Container` (контейнер, принадлежит компании)

```sql
CREATE TABLE Container (
  id              INTEGER PRIMARY KEY,
  company_id      INTEGER NOT NULL,
  container_no    TEXT NOT NULL UNIQUE,         -- напр., MSKU1234567
  type_size       TEXT,                         -- напр., '20ft', '40ft'
  current_status  TEXT NOT NULL DEFAULT 'unknown'
                  CHECK (current_status IN ('loading','in_transit','unloading','delivered','unknown')),
  current_lat     REAL,
  current_lon     REAL,
  current_point_id INTEGER,                    -- FK на MapPoint (см. §4.5)
  route_id        INTEGER,                      -- FK на Route (см. §4.6) — Этап 2
  updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (company_id) REFERENCES Company(id) ON DELETE CASCADE,
  FOREIGN KEY (current_point_id) REFERENCES MapPoint(id),
  FOREIGN KEY (route_id) REFERENCES Route(id)
);
CREATE INDEX idx_container_company ON Container(company_id);
CREATE INDEX idx_container_status ON Container(company_id, current_status);
```

### 4.4 `Dislocation` (журнал перемещений контейнера)

```sql
CREATE TABLE Dislocation (
  id              INTEGER PRIMARY KEY,
  container_id    INTEGER NOT NULL,
  status          TEXT NOT NULL,
  lat             REAL,
  lon             REAL,
  point_id        INTEGER,
  timestamp_event TEXT NOT NULL,
  source_file     TEXT,                         -- имя Excel-файла, из которого пришла запись
  source_upload_id INTEGER,                    -- FK на UploadLog
  FOREIGN KEY (container_id) REFERENCES Container(id) ON DELETE CASCADE,
  FOREIGN KEY (point_id) REFERENCES MapPoint(id),
  FOREIGN KEY (source_upload_id) REFERENCES UploadLog(id)
);
CREATE INDEX idx_dislocation_container ON Dislocation(container_id, timestamp_event DESC);
```

### 4.5 `MapPoint` (справочник гео-точек маршрутов)

```sql
CREATE TABLE MapPoint (
  id              INTEGER PRIMARY KEY,
  name            TEXT NOT NULL,
  lat             REAL NOT NULL,
  lon             REAL NOT NULL,
  kind            TEXT NOT NULL CHECK (kind IN ('loading','unloading','transit')),
  -- компания-агрегатор точек: NULL = shared (КТК ТРАСТ), иначе per-company
  company_id      INTEGER,
  FOREIGN KEY (company_id) REFERENCES Company(id)
);
CREATE INDEX idx_mappoint_kind ON MapPoint(kind, company_id);
```

### 4.6 `Route` (маршрут — последовательность точек)

```sql
CREATE TABLE Route (
  id              INTEGER PRIMARY KEY,
  container_id    INTEGER NOT NULL,
  name            TEXT,                         -- человек-читаемое имя маршрута
  company_id      INTEGER NOT NULL,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (container_id) REFERENCES Container(id) ON DELETE CASCADE,
  FOREIGN KEY (company_id) REFERENCES Company(id) ON DELETE CASCADE
);
CREATE TABLE RoutePoint (                     -- M2M Route ↔ MapPoint, ordered
  route_id        INTEGER NOT NULL,
  point_id        INTEGER NOT NULL,
  seq             INTEGER NOT NULL,            -- порядковый номер точки в маршруте
  PRIMARY KEY (route_id, point_id),
  FOREIGN KEY (route_id) REFERENCES Route(id) ON DELETE CASCADE,
  FOREIGN KEY (point_id) REFERENCES MapPoint(id)
);
```

### 4.7 `UploadLog` (лог загрузок Excel)

```sql
CREATE TABLE UploadLog (
  id              INTEGER PRIMARY KEY,
  file_name       TEXT NOT NULL,
  uploaded_by     INTEGER NOT NULL,            -- FK на User.id (admin)
  parsed_rows     INTEGER NOT NULL DEFAULT 0,
  errors_json     TEXT,                         -- JSON-массив ошибок парсинга
  uploaded_at     TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at     TEXT,
  status          TEXT NOT NULL DEFAULT 'processing'
                  CHECK (status IN ('processing','done','failed')),
  FOREIGN KEY (uploaded_by) REFERENCES User(id)
);
CREATE INDEX idx_uploadlog_status ON UploadLog(status, uploaded_at DESC);
```

### 4.8 `Order` (онлайн-заявка — НЕ сохраняется в MVP per §8 Decision 3)

> ⚠️ **MVP:** заявки летят на email SMTP, в БД **не сохраняются**. Таблица `Order` зарезервирована для возможного Этапа 2.6 или out-of-scope.

```sql
-- RESERVED (не используется в MVP). Активация — после согласования с клиентом.
CREATE TABLE IF NOT EXISTS Order (
  id              INTEGER PRIMARY KEY,
  company_id      INTEGER NOT NULL,
  user_id         INTEGER NOT NULL,
  payload_json    TEXT NOT NULL,                -- JSON с полями формы заявки
  status          TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','seen','done','rejected')),
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (company_id) REFERENCES Company(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES User(id)
);
```

### 4.9 Инварианты целостности

- **INV-1:** у каждого пользователя либо `company_id IS NOT NULL` (client), либо `company_id IS NULL` (`role='admin'`).
- **INV-2:** все запросы к `Container`, `Dislocation`, `Route` фильтруют по `company_id` (см. NFR-007).
- **INV-3:** `current_status` в `Container` согласован с последней записью в `Dislocation` для этого контейнера (по `timestamp_event`).

---

## 5. Технический стек (зафиксировано)

### 5.1 Язык и runtime

| Слой | Решение | Обоснование |
|---|---|---|
| **Backend** | Python 3.10+ (FastAPI или Flask) | Промт явно. Деталь 1.0 стека — выбор между FastAPI/Flask согласуется в Этапе 1.0. |
| **DB** | SQLite 3.35+ (`PRAGMA journal_mode=WAL`) | Промт явно про WAL; SQLite покрывает нагрузку B2B-MVP. |
| **Frontend** | Jinja2 SSR + Bootstrap 5 + HTMX | Бюджет не покрывает SPA. HTMX даёт интерактивность. |
| **Карта** | Leaflet 1.9+ + OSM + SVG-overlay | Бюджет не покрывает полную custom-SVG-карту РФ. Leaflet + overlay линий — компромисс. |

### 5.2 Зависимости (планируемые; фиксируются в `requirements.txt` по итогам 1.1)

| Библиотека | Версия | Назначение |
|---|---|---|
| `fastapi` *или* `flask` | ≥ 0.110 | Backend framework |
| `uvicorn` *или* `gunicorn` | ≥ 0.27 | ASGI/WSGI сервер |
| `jinja2` | ≥ 3.1 | Templates |
| `pandas` | ≥ 2.1 | Excel-парсинг |
| `openpyxl` | ≥ 3.1 | Excel-чтение |
| `bcrypt` | ≥ 4.1 | Хэширование паролей |
| `itsdangerous` | ≥ 2.1 | Подпись cookies / CSRF |
| `pydantic` (если FastAPI) | ≥ 2.6 | Валидация |
| `pytest` | ≥ 8.0 | Тесты |
| `pytest-cov` | ≥ 5.0 | Покрытие тестами (целевое **≥ 70 %** per AC-001/AC-008) |
| `ruff` | ≥ 0.4 | Линтер |
| `black` | ≥ 24.0 | Форматтер |
| `mypy` | ≥ 1.10 | Type-check |
| `pre-commit` | ≥ 3.7 | Git hooks |

### 5.3 Внешние ресурсы

- **OSM-тайлы** (для карты) — open-source, без API-ключа.
- **Bootstrap 5** — через CDN или npm-аналог, выбор — в Этапе 1.0.
- **HTMX** — через CDN, **без npm-сборки**.
- **Leaflet** — через CDN, **без npm-сборки**.

### 5.4 SMTP для заявок

- SMTP-сервер, предоставленный клиентом (реквизиты в `.env` переменных `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_TO_DISPATCHER`).
- В MVP — **только отправка** (без получения/INBOX-интеграции).

### 5.5 Деплой-платформа

- Согласуется с клиентом в Этапе 1.0: VPS / shared hosting / облако клиента.
- **Минимум:** Python 3.10+, SQLite WAL, исходящий SMTP.
- **Инструкции по деплою** — в `RUNNABLE.md` (Этап 2.5).

---

## 6. Архитектурные решения (locked per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md))

### 6.1 Структура проекта (план)

```
projects_17/kwork_site/
├── SPEC.md               # ← этот файл
├── MANIFEST.md           # паспорт проекта
├── 01_PLAN_BREAKDOWN.md  # план-разбор (precursor к SPEC)
├── STEPS.md              # чек-лист Этапов 1+2
├── LESSONS.md            # журнал уроков (CON/CAN/ANTI/PB)
├── README.md             # навигатор для исполнителя/клиента
├── бриф.md, промт.md     # входные данные (НЕ править)
│
├── decisions/            # ADR (после Этапа 1.0)
│   ├── DECISIONS.md
│   └── ADR-NNN_*.md
│
├── app/                  # код приложения (Этап 1.1 →)
│   ├── main.py           # entry-point (FastAPI/Flask)
│   ├── config.py         # env vars + настройки
│   ├── auth/             # FR-001..005
│   │   ├── __init__.py
│   │   ├── routes.py     # /login /logout
│   │   ├── service.py    # bcrypt + sessions
│   │   ├── middleware.py # tenant-isolation (FR-003)
│   │   └── repository.py # User CRUD (+ NFR-007 wrapper)
│   ├── companies/        # company mgmt (admin)
│   ├── excel_pipeline/   # FR-011..016
│   │   ├── parser.py     # pandas + openpyxl
│   │   ├── merger.py     # сведение по container_no
│   │   ├── importer.py   # SQLite UPSERT + error-logging
│   │   └── background.py # BackgroundTasks
│   ├── dashboard/        # FR-006..010
│   ├── requests/         # FR-017..022 + SMTP
│   ├── map/              # FR-026..031 (Этап 2)
│   ├── ui/
│   │   ├── templates/    # Jinja2
│   │   └── components/   # переиспользуемые блоки
│   └── repository.py     # общая обёртка tenant-safe queries (NFR-007)
│
├── static/               # SVG-лого, иконки, favicon (Этап 2) — на корне проекта (tz.md конвенция)
├── tests/
│   ├── test_auth.py
│   ├── test_tenant_isolation.py  # ключевой тест!
│   ├── test_excel_pipeline.py
│   ├── test_dashboard.py
│   ├── test_requests.py
│   └── test_map.py       # Этап 2
│
├── data/                 # SQLite БД + samples (не в git)
├── requirements.txt
├── pyproject.toml
├── Makefile
├── .env.example
├── .gitignore
└── RUNNABLE.md           # инструкции по запуску (Этап 2.5)
```

### 6.2 Ключевые паттерны

| Решение | Источник |
|---|---|
| **Row-level tenant isolation** через SQL `WHERE company_id = ?` из сессии | [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §5.1, NFR-007 |
| **Ручная загрузка Excel** через `/admin/upload` (admin-only) | Decision 2 (Этап 1) |
| **Email-доставка заявок** через SMTP (без БД-реестра) | Decision 3 (Этап 1) |
| **SQLite WAL** для всех конкурентных reads/writes | NFR-018 |
| **Async Excel-парсинг** через BackgroundTasks | FR-015 |

### 6.3 Обработка ошибок

```python
# Принцип: ошибка → логируется с request_id + возвращает клиенту generic message
try:
    operation()
except SpecificError as e:
    logger.error(f"op failed: {e***REMOVED***", extra={"request_id": rid***REMOVED***)
    return {"error": "generic_message"***REMOVED***, 4xx/5xx
```

### 6.4 Идемпотентность Excel-импорта

- UPSERT (replace if `container_no` exists) — повторный запуск парсера не дублирует.
- Каждая загрузка создаёт **новую** запись в `UploadLog` (даже если данные не изменились).

---

## 7. UI-страницы (по этапам)

> Ссылки на детали в [`STEPS.md`***REMOVED***(STEPS.md) §1+§2. Каждая страница имеет acceptance-критерии в §8.

### 7.1 PUBLIC (без авторизации)

| URL | Назначение | FR | Этап |
|---|---|---|---|
| `GET /login` | Форма логина | FR-001, FR-002 | 1 |
| `POST /login` | Submit логина → сессия | FR-001, FR-002 | 1 |

### 7.2 ЛК (client auth)

| URL | Назначение | FR | Этап |
|---|---|---|---|
| `GET /dashboard` | Таблица дислокации | FR-006..010 | 1 |
| `GET /request/new` | Форма онлайн-заявки | FR-017..022 | 1 |
| `POST /request/new` | Submit → SMTP | FR-019, FR-022 | 1 |
| `GET /profile` | Профиль компании + контакты | (минимально) | 1.6 |
| `GET /map` | Интерактивная карта | FR-026..031 | 2 |

### 7.3 ADMIN (admin auth)

| URL | Назначение | FR | Этап |
|---|---|---|---|
| `GET /admin/upload` | Форма загрузки Excel | FR-011, FR-012 | 1 |
| `POST /admin/upload` | Submit → async парсинг | FR-013..016 | 1 |
| `GET /admin/users` | Список пользователей | FR-023 | 1.6 |
| `POST /admin/users` | Создать пользователя | FR-023 | 1.6 |
| `POST /admin/users/<id>/reset` | Сброс пароля | FR-023 | 1.6 |

### 7.4 Auth (любая роль)

| URL | Назначение | FR |
|---|---|---|
| `POST /logout` | Очистка сессии | FR-004 |
| `POST /profile/password` | Смена пароля | FR-005 |

---

## 8. Критерии приёмки (Definition of Done)

### 8.1 Этап 1 (15 000 ₽) — Definition of Done

- **AC-001:** ✅ Все FR-001..005, FR-006..010, FR-011..016, FR-017..022, FR-023 реализованы и проходят unit-тесты (покрытие **≥ 70 %**, замер через `pytest-cov` — см. §5.2 зависимости).
- **AC-002:** ✅ Cookie-сессии работают; CSRF защита mutating-запросов.
- **AC-003:** ✅ Tenant-isolation инвариант проверен тестом (см. AC-009).
- **AC-004:** ✅ Nginx/uwsgi/gunicorn запускается одной командой (`make run`); README содержит инструкцию.
- **AC-005:** ✅ Sample Excel-данные (фикстуры) парсятся и видны в `/dashboard` после загрузки через `/admin/upload`.
- **AC-006:** ✅ Заявка из `/request/new` приходит на email диспетчера КТК ТРАСТ (SMTP-test).
- **AC-007:** ✅ E2E-сценарий (playwright/ручной): login → table дислокации → submit заявки → email диспетчера.
- **AC-008:** ✅ `make test` зелёный (`pytest`), `make lint` зелёный (`ruff`), `make typecheck` зелёный (`mypy`).
- **AC-009:** ✅ Тест на tenant-isolation: пользователь компании A делает запрос к `/dashboard` — НЕ получает контейнеры компании B (минимум 5 тест-кейсов).
- **AC-010:** ✅ Демонстрация клиенту в Kwork-чате (запись экрана / скринкаст) — клиент подтверждает приёмку → оплата 15 000 ₽.

### 8.2 Этап 2 (15 000 ₽) — Definition of Done

- **AC-011:** ✅ Все FR-026..034 реализованы.
- **AC-012:** ✅ Карта на `/map` рендерит OSM-тайлы + pin'ы точек + линии маршрутов.
- **AC-013:** ✅ SVG-логотип 3 варианта + монохромный вариант + favicon — в `/static/`, читаются на 16/32/64/256 px.
- **AC-014:** ✅ Повторный прогон tenant-isolation тестов — НЕ нарушен (после карты).
- **AC-015:** ✅ Cross-browser sanity: Chrome desktop + mobile viewport (≥ 360 px).
- **AC-016:** ✅ Security smoke: SQL injection (через tenant_id), XSS в форме заявки, CSRF bypass attempts — заблокированы.
- **AC-017:** ✅ `RUNNABLE.md` + `CHECKLIST.md` готовы; mini-deploy на staging; smoke test зелёный.
- **AC-018:** ✅ Демонстрация клиенту в Kwork-чате — клиент подтверждает → оплата 15 000 ₽.

### 8.3 Общие DoD (для всего проекта)

- **AC-G1:** Проект соответствует [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md): pep8-стиль через ruff/black, type hints, docstrings, безопасность (нет eval/exec, секреты в env vars), обработка ошибок.
- **AC-G2:** Проект самодостаточен (PROJECT_MIGRATION_TEMPLATE.md): код только в `projects_17/kwork_site/`, без зависимостей от `core_02`/`scripts_01`/`freebuff_plugin*`.
- **AC-G3:** Конфиденциальность материалов клиента соблюдается — код не публикуется в общий реестр `docs_10/`.

---

## 9. Ограничения и допущения

### 9.1 Ограничения (бюджетные)

- **Бюджет:** 30 000 ₽ — жёсткий лимит. Любая фи超出 MVP — **только за доплату** (см. §2.3 COULD + §2.4 WON'T).
- **Время исполнителя:** ≈ 15-20 часов (Kwork ставки ~1 500-2 000 ₽/час). Не позволяет:
  - Полноценный landing-сайт.
  - Native mobile apps.
  - Telegram-бот.
  - CI/CD в облако.
  - Иерархия ролей (более 1 роли на компанию-клиента).

### 9.2 Технические допущения

- **SQLite** покрывает нагрузку MVP (до ≈ 100 клиентских компаний × до 1000 контейнеров = до 100 000 строк в `Container`).
- **OSM-тайлы** доступны по умолчанию (если политика клиента не блокирует — уточнить).
- **SMTP-сервер** клиента доступен из deployment-платформы (не за файрволом).

### 9.3 Допущения о клиенте

- Клиент предоставит **минимум 2 эталонных Excel-файла** (текущий + предыдущий период) для калибровки парсера.
- Клиент подтвердит **Python (не PHP)** до старта Этапа 1.0.
- Клиент предоставит **фирменные цвета** (HEX/RGB) и (опционально) **фирменный шрифт**.
- Клиент согласует **список полей формы заявки** (обязательные + опциональные).

---

## 10. Этапы реализации (per [`STEPS.md`***REMOVED***(STEPS.md))

| Этап | Бюджет | Acceptance (DoD) | Шаги |
|---|---:|---|---|
| **Этап 1** | 15 000 ₽ | AC-001..010 | §1.0 → §1.7 (`STEPS.md`) |
| **Этап 2** | 15 000 ₽ | AC-011..018 | §2.1 → §2.6 (`STEPS.md`) |

> Подробный поэтапный чек-лист с подзадачами см. в [`STEPS.md`***REMOVED***(STEPS.md).

---

## 11. Открытые вопросы (блокеры)

> ⚠️ **Эти вопросы нужно закрыть с клиентом ДО старта Этапа 1.0.** Они не блокируют написание этого SPEC, но блокируют **код**. См. подробнее в [`STEPS.md`***REMOVED***(STEPS.md) §0 и [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §6.

| # | Блокер | Тип | Когда закрывается |
|---|---|---|---|
| **Q1** | **Python vs PHP** для Excel-движка (дословный «php или питон» в [`бриф.md`***REMOVED***(бриф.md)) | 🔴 | До старта Этапа 1.0 |
| **Q2** | 2 эталонных Excel-файла (структура колонок, общий ключ `container_no`, периодичность обновления) | 🔴 | До старта §1.3 |
| **Q3** | «Скрин конкурента» (референс стиля) — файл или текстовый термин в брифе? | 🔴 | До §1.x (UI-стиль) |
| **Q4** | Фирменные цвета КТК ТРАСТ (HEX/RGB) + фирменный шрифт (если есть) | 🔴 | До §2.2 |
| **Q5** | Список полей онлайн-заявки (обязательные + опциональные) | 🔴 | До §1.5 |
| **Q6** | Тестовая выборка гео-координат маршрутов | 🔴 | До §2.3 |
| **Q7** | Деплой-платформа (VPS / shared / облако клиента) | 🟡 | До §2.5 |
| **Q8** | Лицензия исходного кода (MIT / proprietary / согласуется) | 🟡 | До §2.6 (приёмка) |

> **Ответы клиента** должны быть зафиксированы в: (a) чате Kwork — для traceability, (b) `LESSONS.md` проекта — если ответ выявил нетривиальное решение, достойное урока.

---

## 12. Кросс-ссылки (canonical-карта проекта)

### Внутренние (внутри `projects_17/kwork_site/`)

- [`MANIFEST.md`***REMOVED***(MANIFEST.md) — паспорт проекта + реестр + scope rules + конфиденциальность.
- [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) — **источник правды** для: 3 sharp decisions (заморозить схему до Excel samples; ручная загрузка; email-SMTP), stack-обоснования, asset gap, рисков.
- [`STEPS.md`***REMOVED***(STEPS.md) — **источник правды** для: блокеров §0 + пошагового чек-листа.
- [`README.md`***REMOVED***(README.md) — навигатор + структура проекта + быстрый старт исполнителя.
- [`LESSONS.md`***REMOVED***(LESSONS.md) — журнал уроков (CON/CAN/ANTI/PB).
- [`бриф.md`***REMOVED***(бриф.md) — **исходный** текст клиента (НЕ править).
- [`промт.md`***REMOVED***(промт.md) — декомпозиция промта (НЕ править).

### Внешние (корневые канонические документы)

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2 (каркас) + §4 (порядок работы) + §8 (чек-лист нового проекта).
- [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md) — стандарт качества кода.
- [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md) — стандарт готовности (RUNNABLE/CHECKLIST).
- [`docs_10/projects_meta/PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) — реестр проектов платформы.

### Стилевые образцы (sibling-проекты)

- `projects_17/tg_terminal_messenger/docs/original/tz.md` — канон формата ТЗ (FR-NNN / NFR-NNN / DoD).
- `projects_17/lead_aggregator/PHASE2_ARCHITECTURE.md` — канон архитектурного документа.

---

## 13. Глоссарий

| Термин | Определение |
|---|---|
| **B2B-портал** | Web-приложение для юр. лиц (клиентов) |
| **ЛК (личный кабинет)** | Защищённая область сайта после аутентификации |
| **Tenant** | Юр. лицо-клиент, чьи данные логически изолированы |
| **WAL** | Write-Ahead Log — режим SQLite для конкурентного чтения/записи |
| **MVP** | Minimum Viable Product — минимальная работающая версия |
| **Kwork** | Платформа фриланс-заказов (kwork.ru), где размещён этот заказ |
| **Excel-pipeline** | Парсер + сведение 2 Excel-файлов → SQLite |
| **BackgroundTask** | Асинхронная задача (FastAPI), не блокирует UI |

---

*SPEC версия 0.1.0 создан: 2026-08-17 · Статус: 🟡 DRAFT (готов к review Этапа 1.0) · Канон: PROJECT_RULES.md §2 + tz.md стиль + 3 sharp decisions из PLAN_BREAKDOWN §8 · Автор: Buffy (Workspace OS / Freebuff)*
