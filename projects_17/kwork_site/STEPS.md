# STEPS.md — Пошаговый чек-лист Этапов 1+2

> **Канон:** [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §4 (задача идёт через проект; уроки фиксировать по ходу)
> **Бюджет-разбивка (per [`промт.md`***REMOVED***(промт.md)):** Этап 1 — **15 000 ₽**, Этап 2 — **15 000 ₽** (общий — 30 000 ₽)
> **Статус:** 🟡 **PLANNING** — чек-лист расписан, код ещё не начат; до старта нужны блокеры (§0)
> **Связь с планом:** детали решений и стек — [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md); статусы и реестр — [`MANIFEST.md`***REMOVED***(MANIFEST.md)

---

## 0. 🔴 Блокеры до старта кода

> Перед стартом Этапа 1.0 нужно **получить от клиента** в Kwork-чате. См. детали в [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §6/§7/§8.

- [ ***REMOVED*** 🔴 **Стек Excel-движка: Python vs PHP** (дословный «php или питон» в [`бриф.md`***REMOVED***(бриф.md); промт фиксирует Python — нужно подтверждение клиента)
- [ ***REMOVED*** 🔴 **2 эталонных Excel-файла** для парсинга (структура колонок, общий ключ контейнера, периодичность обновления)
- [ ***REMOVED*** 🔴 **«Скрин конкурента»** — файл или текстовый термин в [`бриф.md`***REMOVED***(бриф.md)? (в папке только 2 jpg-фото)
- [ ***REMOVED*** 🔴 **Фирменные цвета КТК ТРАСТ** (HEX/RGB — извлечь из PNG или получить от клиента)
- [ ***REMOVED*** 🔴 **Список полей онлайн-заявки** (обязательные + опциональные)
- [ ***REMOVED*** 🟡 **Тестовая выборка гео-координат маршрутов** *(для Этапа 2; см. [🟡 Q-soft A в `CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) — не блокирует старт Этапа 1.0, можно уточнять параллельно с Этапом 1)*
- [ ***REMOVED*** 🟡 **Деплой-платформа** (VPS / shared hosted / облако клиента)
- [ ***REMOVED*** 🟡 **Лицензия исходного кода** (MIT / proprietary / согласуется)

---

## Этап 1 (15 000 ₽) — Базовый сервис и обработка данных

**Acceptance-критерий этапа:** клиент ТК «КТК ТРАСТ» может (1) авторизоваться в ЛК; (2) увидеть таблицу дислокации контейнеров своей компании; (3) клиент компании может оставить онлайн-заявку, и она уходит диспетчеру на email.

### 1.0 — Архитектурный шаг (закладывает основу)

- [ ***REMOVED*** **Принять [`decisions/ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md)** 🟢 — **первый архитектурный шаг** (модель авторизации + tenant-isolation через row-level `WHERE company_id = ?` из сессии пользователя; **не зависит от блокеров §0** — можно стартовать сразу).
  - Формат ADR: Context / Options / Decision / Rationale / Consequences (см. [`decisions/DECISIONS.md`***REMOVED***(decisions/DECISIONS.md)).
  - Уже принят 2026-08-17 (статус 🟢 ACCEPTED; см. ADR-001 §5.3 реализация-требования).
  - Тест-план: **≥ 5 автотестов** tenant-isolation (NFR-010, см. ADR-001 §5.4); coverage repository-функций **≥ 80 %** (NFR-011).
- [ ***REMOVED*** Согласовать Python vs PHP с клиентом (блокер §0 #1)
- [ ***REMOVED*** Зафиксировать стек: **Python (FastAPI или Flask) + SQLite (WAL) + Jinja2 + Bootstrap 5 + HTMX** (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §5.1)
- [ ***REMOVED*** Зафиксировать структуру БД-минимум: Company / User / Container / Dislocation (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §3) — соответствует INVARIANT'ам [`decisions/ADR-001`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) §5.3 (каждая тенантная таблица содержит `company_id` FK)
- [ ***REMOVED*** Зафиксировать путь деплоя (VPS / shared / облако — согласуется в §0 #7)
- [ ***REMOVED*** Согласовать качество логотип-SVG: flat+моно+1 polish round (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §4.3 default-предложение)

### 1.1 — Окружение и инфраструктура

- [ ***REMOVED*** Создать структуру каталогов (`app/`, `tests/`, `static/`, `data/`, `docs/`, `decisions/`) — план в [`README.md`***REMOVED***(README.md)
- [ ***REMOVED*** `requirements.txt` с фиксированными версиями (FastAPI/Flask, pandas, openpyxl, jinja2, bcrypt, pytest, ruff, black)
- [ ***REMOVED*** `pyproject.toml` (для ruff/black/mypy конфигов)
- [ ***REMOVED*** `Makefile` или `justfile` с основными таргетами (`make dev`, `make test`, `make lint`)
- [ ***REMOVED*** `.env.example` с шаблоном переменных окружения (SECRET_KEY, SMTP creds, DATABASE_URL)
- [ ***REMOVED*** `pytest.ini` + базовые unit-тесты-«sanity check» (импорты)
- [ ***REMOVED*** Pre-commit hooks (ruff + black + блок на секреты)

### 1.2 — Авторизация и tenant-isolation

- [ ***REMOVED*** bcrypt-хэширование паролей (никогда plain)
- [ ***REMOVED*** Cookie-based sessions (Secure + HttpOnly + SameSite=Lax)
- [ ***REMOVED*** `current_user` middleware: tenant_id из сессии
- [ ***REMOVED*** `current_company()` middleware для per-row фильтрации
- [ ***REMOVED*** Login-flow (`/login`, `/logout`) + CSRF-токен
- [ ***REMOVED*** Middleware-проверка `company_id` перед каждым запросом к контейнерам/заявкам
- [ ***REMOVED*** **Тест tenant-isolation:** контейнеры компании A **не видны** пользователю компании B (минимум 5 unit-тестов)

### 1.3 — Excel pipeline

- [ ***REMOVED*** Получить 2 эталонных файла от клиента (блокер §0 #2)
- [ ***REMOVED*** Python-скрипт парсинга (`pandas` + `openpyxl`)
- [ ***REMOVED*** Сведение по общему ключу (container_no) с выводом ошибок для не-сведённых строк
- [ ***REMOVED*** Сохранение в SQLite (PRAGMA journal_mode=WAL активен)
- [ ***REMOVED*** FastAPI BackgroundTasks — загрузка асинхронно, чтобы UI не блокировался
- [ ***REMOVED*** Страница `/admin/upload` для админа КТК ТРАСТ (только авторизованным админам)
- [ ***REMOVED*** Валидация файлов (тип, размер, заголовки)
- [ ***REMOVED*** Логирование загрузки (`UploadLog` таблица: file_name, uploaded_by, parsed_rows, errors)
- [ ***REMOVED*** Тесты парсера на фикстурах (3+ теста: happy path, частично сломанные данные, пустой файл)

### 1.4 — Личный кабинет: таблица дислокации

- [ ***REMOVED*** Дашборд `/dashboard` — таблица контейнеров компании с фильтрами (статус, дата, маршрут) и сортировкой
- [ ***REMOVED*** DataTables.js или эквивалент (server-side pagination если данных > 1000 строк)
- [ ***REMOVED*** Empty state («пока нет контейнеров»), loading state, error state — единый шаблон
- [ ***REMOVED*** Клик по строке → мини-карточка контейнера (модалка или offcanvas)
- [ ***REMOVED*** Контекстный CTA «Оставить заявку» на дашборде

### 1.5 — Личный кабинет: онлайн-заявка → email

- [ ***REMOVED*** Форма `/request/new` — поля по спецификации клиента (блокер §0 #5)
- [ ***REMOVED*** Client-side валидация (HTML5 + легкий JS)
- [ ***REMOVED*** Server-side валидация (Pydantic / marshmallow)
- [ ***REMOVED*** CSRF защита формы
- [ ***REMOVED*** **Submit → SMTP** на email диспетчера КТК ТРАСТ (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §8 Decision 3)
- [ ***REMOVED*** Confirmation page + confirmation email клиенту (опционально)
- [ ***REMOVED*** Anti-spam базовый (rate limit per IP per session)
- [ ***REMOVED*** Тесты: happy path submit, валидация отказ, rate limit

### 1.6 — Профиль компании + история заявок (минимально)

- [ ***REMOVED*** `/profile` — реквизиты компании (read-only), контактные лица (edit)
- [ ***REMOVED*** `/profile/requests` — история email-заявок (по факту — last seen; БД-реестр не ведётся в MVP, см. §8 Decision 3)
- [ ***REMOVED*** `/profile/password` — смена пароля (с подтверждением старого)
- [ ***REMOVED*** Logout-cookie cleanup

### 1.7 — Приёмка Этапа 1

- [ ***REMOVED*** Все acceptance-критерии 1.0–1.6 выполнены
- [ ***REMOVED*** Демонстрация клиенту в Kwork-чате (запись экрана или скринкаст)
- [ ***REMOVED*** Подтверждение клиента → оплата 15 000 ₽ → переход к Этапу 2
- [ ***REMOVED*** Зафиксировать LESSONS по итогам Этапа 1 (CON/ANTI от удачных и неудачных решений)

---

## Этап 2 (15 000 ₽) — Гео-интеграция и визуализация

**Acceptance-критерий этапа:** клиент ТК «КТК ТРАСТ» пользуется в ЛК интерактивной картой маршрутов; SVG-логотип в продакшене; пройдено финальное тестирование.

### 2.1 — SVG-логотип (качественная конвертация)

- [ ***REMOVED*** Конвертировать 3 растровых PNG-варианта → SVG (auto-trace + 1 раунд ручных правок)
- [ ***REMOVED*** Монохромный вариант для favicon
- [ ***REMOVED*** Тест SVG на retina/HD/маленьких размерах (читаемость в 16/32/64/256 px)

### 2.2 — Ассеты и иконки

- [ ***REMOVED*** `/static/favicon.ico` (16, 32, 64, 256 px)
- [ ***REMOVED*** `/static/icons/` — SVG-sprite: статусы контейнеров (погрузка / в пути / разгрузка / доставлен), действия (открыть / закрыть / редактировать)
- [ ***REMOVED*** UI-тема (CSS variables) на базе фирменных цветов (блокер §0 #4)

### 2.3 — Интерактивная карта (Leaflet)

- [ ***REMOVED*** Зависимости: `leaflet` (1.9+) + `leaflet-draw` (опц., если нужно рисовать маршруты в UI), подключение CDN или npm-style
- [ ***REMOVED*** Карта на странице `/map` — отдельный полноэкранный layout
- [ ***REMOVED*** OSM-тайлы (бесплатные) как основа
- [ ***REMOVED*** SVG-overlay для линий маршрутов (Polyline с vertex-точками)
- [ ***REMOVED*** Pin'ы: точки погрузки (зелёный), выгрузки (синий), транзитные (серый)
- [ ***REMOVED*** Tooltip по клику: ID контейнера, текущий статус, дата последнего обновления
- [ ***REMOVED*** Layer-control: переключение «все / только моя компания / по статусу»
- [ ***REMOVED*** Производительность: при 100+ pin'ов — clustering (опц.)
- [ ***REMOVED*** Мобильный viewport — pinch-zoom работает

### 2.4 — Финальное тестирование

- [ ***REMOVED*** E2E-тесты критических путей (Playwright/Selenium): login → view table → submit form → see map
- [ ***REMOVED*** Cross-browser sanity: Chrome desktop + mobile viewport
- [ ***REMOVED*** Tenant-isolation тесты (повторно, после карты — убедиться что overlay не утекает)
- [ ***REMOVED*** Мини-нагрузочный тест: `locust` или аналог, 10 одновременных пользователей
- [ ***REMOVED*** Security smoke: SQL injection (через tenant_id), XSS в форме заявки, CSRF bypass attempts
- [ ***REMOVED*** Багфиксing по итогам тестов

### 2.5 — Деплой и миграция клиенту

- [ ***REMOVED*** Согласовать деплой-платформу (если не сделано в §0 #7)
- [ ***REMOVED*** `RUNNABLE.md` — инструкции по запуску (deps, env vars, db init, seed fixtures)
- [ ***REMOVED*** `CHECKLIST.md` — финальный чек-лист готовности (per [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md))
- [ ***REMOVED*** Мини-deply на тестовой платформе (staging)
- [ ***REMOVED*** Smoke test на staging
- [ ***REMOVED*** Передача исходников + БД-дампа + README клиенту

### 2.6 — Приёмка Этапа 2

- [ ***REMOVED*** Демонстрация интерактивной карты клиенту
- [ ***REMOVED*** Финальная оплата 15 000 ₽
- [ ***REMOVED*** Закрытие LESSONS по итогам Этапа 2 (CON, ANTI по итогам)
- [ ***REMOVED*** Закрытие проекта в [`MANIFEST.md`***REMOVED***(MANIFEST.md) (статус → 🟢 SHIPPED)

---

## ⛔ Out-of-scope (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §5.2)

- ❌ Полноценный landing-сайт (корпоративный hero с маркетингом) — **по умолчанию**.
- ❌ iOS / Android нативное мобильное приложение.
- ❌ Telegram-бот для клиентов (промт принцип №3 упомянул «при необходимости» — не необходимость).
- ❌ Email-рассылки (mass mailing) — только уведомления о заявках.
- ❌ Интеграция с 1С / CRM клиента.
- ❌ Иерархия ролей внутри клиентской компании.
- ❌ BI / аналитические графики на дашборде.
- ❌ CI/CD в облако, продвинутый мониторинг, system-логи в облако.

> 💡 Любой из этих пунктов — **только за доплату** в новом заказе.

---

## Cross-links

- [`MANIFEST.md`***REMOVED***(MANIFEST.md) — паспорт + реестр проекта
- [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) — детальный план-разбор и stack-обоснование
- [`README.md`***REMOVED***(README.md) — how-to для исполнителя и клиента
- [`LESSONS.md`***REMOVED***(LESSONS.md) — журнал уроков (заполняется по ходу каждого этапа)
- [`бриф.md`***REMOVED***(бриф.md) — исходный бриф клиента
- [`промт.md`***REMOVED***(промт.md) — декомпозиция промта (Этапы 1+2)
- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §4 (порядок работы)
- `projects_17/lead_aggregator/STEPS.md` — образец filled-чеклиста для сравнения

---

*STEPS создан: 2026-08-17 · Статус: 🟡 PLANNING · Канон: PROJECT_RULES.md §2/§4/§8 · Бюджет: 30 000 ₽ (15 + 15) · Автор: Buffy (Workspace OS / Freebuff)*
