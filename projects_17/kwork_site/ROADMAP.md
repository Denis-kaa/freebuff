# ROADMAP.md — Календарный план, milestone'ы и риски проекта `kwork_site`

> **Канонические источники:** [`SPEC.md`***REMOVED***(SPEC.md) §10 (Этапы реализации) + §11 (блокеры Q1..Q8) + §6 (архитектура) + [`STEPS.md`***REMOVED***(STEPS.md) §1.0–1.7 + §2.1–2.6 (чек-лист) + [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §6 (риски) + §8 (3 sharp decisions) + [`decisions/`***REMOVED***(decisions/) (ADR-001 🟢 + ADR-002/003 ⚪).
> **Канон проектного каркаса:** [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2 (обязательные файлы: ROADMAP — нужен для проекта).
> **Бюджет:** **30 000 ₽** (Этап 1 = 15 000 ₽; Этап 2 = 15 000 ₽).
> **Версия:** 0.1.0 · **Дата:** 2026-08-17 · **Статус:** 🟡 **DRAFT** (готов к старту pre-Этап 1.0 после закрытия блокеров).
> **Аудитория:** исполнитель (основная) + клиент КТК ТРАСТ (опциональная вторичная — для понимания таймлайна и где он сейчас).

> ⚠️ **Конфиденциальность:** этот документ — коммерческая тайна клиента ТК «КТК ТРАСТ». Не публиковать в общем реестре `docs_10/` кроме одной строки в [`PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) per [`PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §8.

---

## 0. TL;DR (executive summary)

| Поле | Значение |
|---|---|
| **Общий срок** | **~22–25 календарных дней** от pre-start до финальной приёмки (включая 3 дня на ожидание ответов клиента) |
| **Трудоёмкость** | **~17–21 час** разработки (исполнитель @ ставка 1 500–1 800 ₽/ч = бюджет 30 000 ₽) |
| **Календарный разрез** | **10–11 рабочих дней Этап 1** + **7–9 рабочих дней Этап 2** + 2 приёмочных этапа + async-ожидание ответов клиента (~3 дня) |
| **2 decision gates (оплата)** | После приёмки Этапа 1 → 15 000 ₽ → переход к Этапу 2 · После приёмки Этапа 2 → 15 000 ₽ → закрытие проекта |
| **Critical path** | Q1 (Python vs PHP) + Q2 (Excel-схема) → принять ADR-002/003 → старт §1.0. ADR-001 уже принят (independent от Excel-pipeline, параллельно с ожиданием ответов). |
| **Текущий статус (2026-08-17)** | 🟡 **DRAFT pre-start**: каркас проекта готов (8 файлов из 9 по `PROJECT_RULES.md §2` — ROADMAP создан в этом turn); ADR-001 🟢 ACCEPTED; ADR-002/003 ⚪ DRAFT (ждут Q1/Q2). |

---

## 1. Календарный план (timeline)

> Ориентиры: 1 рабочий день = ~1.5 ч продуктивной работы исполнителя (Kwork-freelance ритм); ожидание ответов клиента в Kwork-чате = async-период (не считается «рабочий день» исполнителя).

### 1.1 Pre-старт (T-3 … T0)

| День | Что происходит |
|---|---|
| **T-3** | Отправить клиенту готовый текст из [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) § «Сообщение для отправки» (8 пунктов: 5🔴 + 3🟡) — copy-paste в Kwork-чат. |
| **T-3..T0** | Асинхронное ожидание ответов Q1..Q5 (5🔴). Клиент отвечает по одному или все сразу. Каждый ответ → фиксируется в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) per-Q-таблица «Ответ клиента». |
| **T0** | Все 5🔴 закрыты (или клиент дал «дефолт» на silent-timer 3 дня). **Gate pre-start → Этап 1**: принять `ADR-002` + `ADR-003` (⚪ → 🟢 per `decisions/DECISIONS.md`); зафиксировать Q5 в `SPEC.md §2.1.D`; зафиксировать Q2 в `SPEC §4` SQL DDL финальными колонками; добавить первый CON-урок в `LESSONS.md`. |

### 1.2 Этап 1 — Базовый сервис (T1 … T10..11)

> Acceptance-критерий: все AC-001..010 из [`SPEC.md §8.1`***REMOVED***(SPEC.md#81-этап-1-15-000-р--definition-of-done) + 15 000 ₽ оплата.

| День | STEPS § | Что делается | FR / NFR / AC |
|---|:-:|---|---|
| **T1** | §1.0 | Архитектурный шаг (ADR-001 уже 🟢; stack фиксируется: Python + FastAPI **или** Flask — выбор). Создать структуру `app/`, `tests/`, `static/`. | ADR-001 + технический стек из `SPEC §5.1` |
| **T2** | §1.1 | Окружение: `requirements.txt` (FastAPI/Flask, pandas, openpyxl, jinja2, bcrypt, pytest-cov ≥ 5.0, ruff, black, mypy); `pyproject.toml`; `Makefile` (`make dev`/`make test`/`make lint`); `.env.example`. | DEP-001 |
| **T3** | §1.2 | Auth + tenant-isolation: bcrypt + cookie-session + `current_company()` middleware + repository-обёртка (`app/database/repository.py`) per `decisions/ADR-001`. **5 обязательных unit-тестов** tenant-isolation (NFR-010); coverage repository-функций ≥ 80 % (NFR-011). | FR-001..005, NFR-007/010/011, **AC-009** |
| **T4..T5** | §1.3 | Excel-pipeline: `app/excel_pipeline/{parser,merger,importer,background***REMOVED***.py`; pandas+openpyxl; сведение по ключу из ADR-003; `/admin/upload` (admin-only); `UploadLog` (FR-016); фикстуры `tests/data/*.xlsx`. | FR-011..016, **AC-005** |
| **T6** | §1.4 | ЛК — таблица дислокации: `/dashboard` с фильтрами (статус/дата/маршрут), paging, empty/loading/error states; мини-карточка контейнера (offcanvas/modal). | FR-006..010 |
| **T7** | §1.5 | Онлайн-заявка: `/request/new` (поля per Q5); client+server валидация; CSRF защита; submit → SMTP (`aiosmtplib`/`smtplib`); anti-spam rate-limit. | FR-017..022, **AC-006** |
| **T8** | §1.6 | Профиль компании: `/profile` (реквизиты read-only, контакты edit); `/profile/password` (с подтверждением старого); + `/admin/users` (admin: list/create/reset) — FR-023. | FR-023 |
| **T9** | — | E2E-сценарий (playwright/ручной): login → table → submit → email → 200 OK; прогон `make test`/`make lint`/`make typecheck`. | **AC-007**, **AC-008** |
| **T10..11** | §1.7 | Демонстрация клиенту в Kwork-чате (запись экрана / скринкаст). Клиент подтверждает → оплата **15 000 ₽**. Закрытие LESSONS по итогам Этапа 1 (CON/CAN/ANTI от удачных/неудачных решений). | **AC-010** |

### 1.3 Этап 2 — Гео-интеграция (T12 … T19..20)

> Acceptance-критерий: все AC-011..018 из [`SPEC.md §8.2`***REMOVED***(SPEC.md#82-этап-2-15-000-р--definition-of-done) + 15 000 ₽ оплата.

| День | STEPS § | Что делается | FR / AC |
|---|:-:|---|---|
| **T12** | §2.1 | SVG-логотип КТК ТРАСТ: конвертация 3 PNG → SVG (auto-trace + 1 раунд ручных правок per `01_PLAN_BREAKDOWN §4.3`); монохромный вариант для favicon; тест читаемости 16/32/64/256 px. | FR-032..034 |
| **T13** | §2.2 | Ассеты: `/static/favicon.ico` + SVG-sprite иконок (статусы контейнеров, действия); UI-тема (CSS variables) на базе фирменных цветов из Q4. | (мелкие) |
| **T14..T15** | §2.3 | Карта Leaflet: `/map` полноэкранный layout; OSM-тайлы; pin'ы (loading=green / unloading=blue / transit=grey); SVG-overlay линий маршрутов через `RoutePoint seq`; tooltip; layer-control; mobile pinch-zoom. | FR-026..031 |
| **T16** | §2.4 | Финальное тестирование: E2E критических путей (Playwright/Selenium); cross-browser sanity (Chrome desktop + mobile viewport); повторный прогон tenant-isolation (после карты — убедиться, что overlay не утекает, **AC-014**); security smoke (SQL injection через tenant_id, XSS в форме заявки, CSRF bypass — все заблокированы, **AC-016**). | **AC-014**, **AC-015**, **AC-016** |
| **T17** | §2.5 | Деплой + миграция: `RUNNABLE.md` (deps, env vars, db init, seed fixtures); `CHECKLIST.md` (финальный чек-лист готовности per `docs_10/core/PROJECT_REQUIREMENTS.md`); mini-deploy на staging; smoke test зелёный. | **AC-017** |
| **T18..20** | §2.6 | Демонстрация клиенту (запись экрана: таблица + карта + форма). Клиент подтверждает → финальная оплата **15 000 ₽**. Закрытие проекта в `MANIFEST.md` (статус 🟢 SHIPPED); финальный LESSONS (CON, ANTI). | **AC-018** |

### 1.4 Post-project (T21+)

- Передача исходников + БД-дампа + `README.md` клиенту.
- Сопровождение: 1 месяц багфиксов (опционально, согласуется отдельно).

---

## 2. Milestones (M0…M11) — критерии достижения

| # | Milestone | Acceptance-критерий | Связанный STEPS § + ADR + FR |
|:-:|---|---|---|
| **M0** | Pre-start завершён | Все 5🔴 блокеры закрыты; `ADR-002` + `ADR-003` приняты (⚪ → 🟢); `LESSONS.md` имеет CON-001 «Блокеры закрыты» | [`STEPS.md §0`***REMOVED***(STEPS.md); [`decisions/ADR-002_python_vs_php.md`***REMOVED***(decisions/ADR-002_python_vs_php.md); [`decisions/ADR-003_excel_schema_v1.md`***REMOVED***(decisions/ADR-003_excel_schema_v1.md) |
| **M1** | §1.0 — архитектурный шаг | ADR-001 🟢; стек зафиксирован; структура `app/` создана | [`STEPS.md §1.0`***REMOVED***(STEPS.md); [`decisions/ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) |
| **M2** | §1.1 — окружение | `requirements.txt`+`pyproject.toml`+`Makefile`+`.env.example` готовы; `make dev` запускается | DEP-001 |
| **M3** | §1.2 — auth + tenant-isolation | `pytest` ≥ 5 unit-тестов на изоляцию зелёный; coverage repository ≥ 80 % | FR-001..005, NFR-007/010/011, **AC-009** |
| **M4** | §1.3 — Excel-pipeline | `/admin/upload` принимает 2 .xlsx; `UploadLog` пишется; sample-фикстуры парсятся и видны в `/dashboard` | FR-011..016, **AC-005** |
| **M5** | §1.4..1.6 — ЛК + заявка + профиль | `/dashboard`/`/request/new`/`/profile` работают; submit → SMTP для тестового email | FR-006..022, FR-023, **AC-006** |
| **M6** | §1.7 — приёмка Этапа 1 → **оплата 15 000 ₽** | Демонстрация клиенту OK; клиент подтвердил; оплата получена; LESSONS по итогам закрыты | **AC-010** |
| **M7** | §2.1 — SVG-логотип | 3 SVG-варианта + моно + favicon; тест на 16/32/64/256 px | FR-032..034 |
| **M8** | §2.3 — карта Leaflet | `/map` рендерит OSM + pin'ы + линии маршрутов; mobile pinch-zoom | FR-026..031 |
| **M9** | §2.4 — финальное тестирование | E2E (Playwright); tenant-isolation повторно зелёный после карты; security smoke заблокирован | **AC-014**, **AC-015**, **AC-016** |
| **M10** | §2.5 — деплой + миграция | `RUNNABLE.md` + `CHECKLIST.md` готовы; smoke test на staging зелёный | **AC-017** |
| **M11** | §2.6 — приёмка Этапа 2 → **оплата 15 000 ₽** → 🟢 SHIPPED | Демонстрация OK; клиент подтвердил; оплата получена; `MANIFEST.md` статус 🟢 SHIPPED | **AC-018** |

---

## 3. Decision Gates (стратегические ADR-переключатели)

| Stage | ADR | Условие принятия | Downstream impact | Связь с этапом |
|:-:|---|---|---|---|
| **pre-start** | [`ADR-002_python_vs_php.md`***REMOVED***(decisions/ADR-002_python_vs_php.md) ⚪→🟢 | Ответ клиента по **Q1** из [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) | `SPEC §5.1` (если PHP — переписать); таймлайн (если PHP ≈ +8–12 ч); бюджет 30 000 ₽ (PHP рискованно) | T-3..T0 |
| **pre-start** | [`ADR-003_excel_schema_v1.md`***REMOVED***(decisions/ADR-003_excel_schema_v1.md) ⚪→🟢 | Ответ клиента по **Q2** (2 эталонных Excel: структура + общий ключ + периодичность) | `SPEC §4` SQL DDL (финальные колонки `Container`/`Dislocation`/`UploadLog`); MERGE logic; fixture-данные | T-3..T0 |
| **M1 (T1)** | [`ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) **🟢 ✅ уже принят 2026-08-17** | — | ADR-001 уже зафиксирован — auth + tenant-isolation **не блокирует** Excel-pipeline (per `01_PLAN_BREAKDOWN §1.2`); §1.0 / §1.2 стартуют независимо от Q1/Q2 | T1+ |
| **(опц.) §2.5** | `ADR-NNN_fastapi_vs_flask.md` (новый, если в §1.0 выбор не сделан) | Результат FastAPI-vs-Flask dilemma из §1.0 | Структура `app/` (async vs sync); ASGI/WSGI выбор | T1..T2 |

> **Гейт pre-start → Этап 1 = ADR-002 🟢 AND ADR-003 🟢.** До их принятия код Этапа 1.0 НЕ стартует (за исключением §1.0 архитектурный шаг с ADR-001, который уже 🟢).

---

## 4. Этапы с под-linkage к SPEC/STEPS

### 4.1 Этап 1 — 6 шардов (per [`STEPS.md §1`***REMOVED***(STEPS.md))

| Шард | STEPS § | FR-NNN | NFR-NNN | AC | Файлы-результаты (expected, будут созданы в Этапе 1) |
|---|:-:|---|---|---|---|
| **§1.0 Архитектурный шаг** | ✅ ARD-001 | — | — | — | `app/` (структура), `requirements.txt` |
| **§1.1 Окружение** | — | — | DEP-001 | DEP-001 | `pyproject.toml`, `Makefile`, `.env.example`, `pytest.ini`, `.gitignore`, `pre-commit hooks` |
| **§1.2 Auth + tenant-isolation** | — | FR-001..005 | **NFR-007/010/011** (инвариант + ≥5 автотестов + ≥80% coverage) | **AC-009** | `app/auth/{routes,service,middleware,repository***REMOVED***.py`, `tests/test_auth.py`, `tests/test_tenant_isolation.py` |
| **§1.3 Excel-pipeline** | — | FR-011..016 | — | **AC-005** | `app/excel_pipeline/{parser,merger,importer,background***REMOVED***.py`, `tests/test_excel_pipeline.py`, `tests/data/*.xlsx` (фикстуры) |
| **§1.4 ЛК — таблица** | — | FR-006..010 | — | (в составе §1.7) | `app/dashboard/views.py`, `app/ui/templates/dashboard/`, `tests/test_dashboard.py` |
| **§1.5 Онлайн-заявка** | — | FR-017..022 | NFR-008 (SMTP creds в env) | **AC-006** | `app/requests/{forms,service,smtp***REMOVED***.py`, `tests/test_requests.py` |
| **§1.6 Профиль + админ** | — | FR-023 | — | (в составе §1.7) | `app/profile/views.py`, `app/admin/views.py` |
| **§1.7 Приёмка Этапа 1** | — | — | — | **AC-001..010** | Demos в Kwork, закрытие LESSONS |

### 4.2 Этап 2 — 5 шардов (per [`STEPS.md §2`***REMOVED***(STEPS.md))

| Шард | STEPS § | FR-NNN | AC | Файлы-результаты |
|---|:-:|---|---|---|
| **§2.1 SVG-логотип** | — | FR-032..034 | (в составе §2.6) | `static/logo.svg`, `static/logo_mono.svg`, `static/favicon.ico` |
| **§2.2 Ассеты + иконки** | — | — | (в составе §2.6) | `static/icons.svg` (sprite), CSS variables (UI-тема) |
| **§2.3 Карта Leaflet** | — | FR-026..031 | (в составе §2.6) | `app/map/views.py`, `app/ui/templates/map.html`, `tests/test_map.py` |
| **§2.4 Финальное тестирование** | — | — | **AC-014**, **AC-015**, **AC-016** | `tests/e2e/`, security smoke reports |
| **§2.5 Деплой + миграция** | — | — | **AC-017** | `RUNNABLE.md`, `CHECKLIST.md`, `data/seed.py`, `Makefile deploy` |
| **§2.6 Приёмка Этапа 2** | — | — | **AC-011..018** | Demos в Kwork, закрытие проекта в `MANIFEST.md` 🟢 SHIPPED |

---

## 5. Оценки трудозатрат (часы × ставка × ₽)

> Базовая ставка: **1 500–1 800 ₽/ч** (типичный Kwork-range для fullstack-Flask/FastAPI). Бюджет 30 000 ₽ → 16.7–20 ч продуктивной разработки.

### 5.1 Этап 1 (~11.5–13.5 ч)

| Шард | Диапазон ч | Оценка (медиана) |
|---|:-:|:-:|
| §1.0 Архитектурный шаг | 0.5–1 | **0.75** |
| §1.1 Окружение | 1.5–2 | **1.75** |
| §1.2 Auth + tenant-isolation (с тестами) | 2.5–3 | **2.75** |
| §1.3 Excel-pipeline | 1.5–2 | **1.75** |
| §1.4 ЛК — таблица | 1.5–2 | **1.75** |
| §1.5 Онлайн-заявка SMTP | 1–1.5 | **1.25** |
| §1.6 Профиль + админ | 0.5–1 | **0.75** |
| §1.7 Демонстрация + LESSONS | 1–2 | **1.5** |
| **ИТОГО Этап 1** |  | **~12.25 ч** → **~12 ч** = **18 000–21 600 ₽** (при ставке 1 500–1 800 ₽/ч) |

> ⚠️ Оценка §1.2 самая дорогая (тесты на tenant-isolation — инвариант NFR-010). Расширение scope (больше ADMIN-функций или доп. ролей) может легко съесть остаток бюджета Этапа 1 → **строго придерживаться FR-001..023** (без FR-035..045 SHOULD/COULD).

### 5.2 Этап 2 (~7.5–10 ч)

| Шард | Диапазон ч | Оценка (медиана) |
|---|:-:|:-:|
| §2.1 SVG-логотип (auto-trace + 1 polish round) | 1.5–2.5 | **2** |
| §2.2 Ассеты + иконки + UI-тема | 0.5–1 | **0.75** |
| §2.3 Карта Leaflet + overlay маршрутов | 2.5–3.5 | **3** |
| §2.4 Финальное тестирование (E2E, security, cross-browser) | 1.5–2 | **1.75** |
| §2.5 RUNNABLE.md + CHECKLIST.md + staging deploy | 0.75–1 | **0.875** |
| §2.6 Демонстрация + LESSONS + закрытие проекта | 0.5–1 | **0.75** |
| **ИТОГО Этап 2** |  | **~9.125 ч** → **~9 ч** = **13 500–16 200 ₽** |

> ⚠️ §2.3 самая дорогая (Leaflet + кастомный SVG-overlay — требует аккуратной работы с vertex-точками). Если реальные данные маршрутов сложны — возможно +1–2 ч, тогда Этап 2 → ~11 ч → **строго обсудить с клиентом** или **сократить scope** (отключить clustering FR-038).

### 5.3 Total

| | Минимум | Медиана | Максимум |
|---|:-:|:-:|:-:|
| **Часы** | 19 | **~21.5** | 23.5 |
| **₽ при 1 500 ₽/ч** | 28 500 | 32 250 | 35 250 |
| **₽ при 1 800 ₽/ч** | 34 200 | 38 700 | 42 300 |

> 📊 **Честная оценка:** медианная трудоёмкость ~21.5 ч **.может не влезть в 30 000 ₽** при ставке 1 800 ₽/ч. Если исполнитель берёт 1 800 ₽/ч — клиент должен знать, что **возможен недобор scope** или **согласование доплаты**. При ставке 1 500 ₽/ч — бюджет 30 000 ₽ = ~20 ч, что покрывает медианную оценку.

### 5.4 Буфер на непредвиденное

- **+10 % буфер** на каждую оценку (типовой риск-планинг) → +2 ч → итого ~24 ч.
- **Max-effort порог:** 30 ч → при ставке 1 500 ₽/ч = 45 000 ₽ (превышение бюджета на 50 %). При таком превышении — **обязательное согласование с клиентом** (split delivery или доплата).

---

## 6. Риски & митигации (расширенная версия [`01_PLAN_BREAKDOWN §6`***REMOVED***(01_PLAN_BREAKDOWN.md))

> Аддитивно к 8 рискам из PLAN_BREAKDOWN §6 — добавлены 4 новых (бюджетные/процессные).

| # | Риск | Вероятность | Impact | Митигация | Связь |
|:-:|---|:-:|:-:|---|---|
| R-1 | **2 эталонных Excel не предоставлены** → парсер «из головы» = хрупкий код | 🔴 высокая | 🔴 высокий | Hard-stop per `01_PLAN_BREAKDOWN §8 Decision 1`; фикстур-fallback (генерим 2 sample Excel от исполнителя); ADR-003 обязательно фиксирует источник данных | _Блокер Q2_ |
| R-2 | **Клиент настаивает на PHP** вместо Python | 🟡 средняя | 🔴 высокий (переписать SPEC + таймлайн) | ADR-002 формально зафиксирует решение; если PHP — переоценка бюджета + явное согласие клиента на +5–10 ₽ | _Блокер Q1_ |
| R-3 | **Качество SVG-логотипа** (авто-трейс грязный) | 🟡 средняя | 🟡 средний | 1 раунд ручных правок (default per `01_PLAN_BREAKDOWN §4.3`); опц. согласовать доп. итерации с клиентом | _Этап 2 §2.1_ |
| R-4 | **Сведение 2 Excel** с разной структурой колонок | 🟡 средняя | 🔴 высокий (не сводится → данные пропадают) | ADR-003 фиксирует общий ключ + нормализацию заголовков; тест на 5+ edge cases | _§1.3_ |
| R-5 | **Tenant-isolation invariant нарушен** (SQL без `WHERE company_id`) | 🟢 низкая (после ADR-001) | 🔴 critical (утечка данных) | Repository-обёртка обязательна; **NFR-007** lint; **≥ 5 автотестов** (NFR-010); code-review на каждый SQL | _§1.2_ — critical path |
| R-6 | **Security: XSS / CSRF bypass / SQL injection** | 🟡 средняя | 🔴 высокий | Jinja2 autoescape; CSRF token обязателен; Pydantic валидация; security smoke tests (§2.4 AC-016); **никаких `eval`/`exec`** (NFR-009) | _§2.4_ |
| R-7 | **Деплой-платформа нестандартная** (shared-hosting без Python 3.10+, no SQLite WAL) | 🟡 средняя | 🟡 средний | RUNNABLE.md явно перечисляет требования (VPS recommended); согласовать Q7 в early-Этап 2.5 | _§2.5_ |
| R-8 | **Лицензия исходного кода** не определена на финальной приёмке | 🟢 низкая | 🟡 средний (юридический риск) | Q8 — обсудить в §2.6; default — proprietary (KTK TRACT owns code) | _§2.6_ |
| **R-9** | **Бюджетное превышение** (трудоёмкость > 21 ч) | 🟡 средняя | 🔴 высокий | Тесная коммуникация с клиентом на каждом M3/M5; «зелёная зона» = ≤ 21 ч; «жёлтая» = 21–25 ч (буфер +10 %); «красная» = > 25 ч → split delivery или доплата | _все этапы_ |
| **R-10** | **Тестовая выборка гео-координат** не предоставлена (для карты) | 🟡 средняя | 🟡 средний | Demo-полигон (5 городов из OSM Russia) — рабочий fallback; Q-soft A можно уточнять параллельно с Этапом 1 | _Этап 2 §2.3_ |
| **R-11** | **Фирменные цвета КТК ТРАСТ** не предоставлены | 🟢 низкая | 🟡 средний | Extract HEX из PNG-лого (3 варианта в папке); Q4 fallback acceptable | _Этап 2 §2.2_ |
| **R-12** | **Поле заявки превышает 7 default** (Q5 клиент добавляет поля) | 🟡 средняя | 🟢 низкая | Default-набор (FR-017 default field set) — MVP-минимум; добавить поля = +0.5 ч на spec update + форму | _§1.5_ |
| **R-13** | **Сложность карты** — отрисовка линий маршрутов на Leaflet через SVG-overlay (vertex-точки) может оказаться дороже медианной оценки §5.2 | 🟡 средняя | 🟡 средний | (a) Pin clustering (FR-038) при > 100 pin'ов; (b) Buffer +1–2 ч в §5.2; (c) при превышении ≥ 11 ч на §2.3 → split scope (отключить overlay) + доплата | _§2.3_ |

---

## 7. Критерии приёмки (cross-link к SPEC §8)

### 7.1 Этап 1 — все AC-001..010 ([`SPEC §8.1`***REMOVED***(SPEC.md#81-этап-1-15-000-р--definition-of-done))

| AC | Описание | Связь с STEPS § / ADR | Status (target) |
|:-:|---|---|:---:|
| **AC-001** | FR-001..005/006..010/011..016/017..022/023 реализованы + ≥ 70 % coverage (pytest-cov) | §1.2–1.6 | 🟡 to-M3..M5 |
| **AC-002** | Cookie-сессии + CSRF | §1.2 / NFR-006 | 🟡 to-M3 |
| **AC-003** | Tenant-isolation инвариант проверен тестами | §1.2 / AC-009 / NFR-010 | 🟡 to-M3 |
| **AC-004** | `make run` запускается одной командой | §1.1 | 🟡 to-M2 |
| **AC-005** | Sample Excel парсятся и видны в `/dashboard` | §1.3 / FR-013 | 🟡 to-M4 |
| **AC-006** | Заявка → email диспетчера (SMTP-test) | §1.5 / FR-019 | 🟡 to-M5 |
| **AC-007** | E2E-сценарий зелёный | §1.5–1.6 | 🟡 to-T9 |
| **AC-008** | `make test`/`make lint`/`make typecheck` зелёные | непрерывно | 🟡 to-T9 |
| **AC-009** | Tenant-isolation тест: ≥ 5 unit-тестов зелёный | §1.2 / ADR-001 §5.4 | 🟡 to-M3 |
| **AC-010** | Демонстрация клиенту + оплата 15 000 ₽ | §1.7 | 🟡 to-M6 |

### 7.2 Этап 2 — все AC-011..018 ([`SPEC §8.2`***REMOVED***(SPEC.md#82-этап-2-15-000-р--definition-of-done))

| AC | Описание | Связь | Status |
|:-:|---|---|:---:|
| **AC-011** | FR-026..034 реализованы | §2.1–2.3 | 🟡 to-M7..M8 |
| **AC-012** | Карта рендерит OSM-тайлы + pin'ы + линии | §2.3 / FR-026..031 | 🟡 to-M8 |
| **AC-013** | SVG-логотип 3+1 варианта + favicon | §2.1 / FR-032..034 | 🟡 to-M7 |
| **AC-014** | Повторный прогон tenant-isolation — НЕ нарушен после карты | §2.4 (security audit) | 🟡 to-M9 |
| **AC-015** | Cross-browser sanity (Chrome desktop + mobile ≥ 360 px) | §2.4 / NFR-016/017 | 🟡 to-M9 |
| **AC-016** | Security smoke (SQL injection, XSS, CSRF bypass) заблокированы | §2.4 / NFR-005..009 | 🟡 to-M9 |
| **AC-017** | RUNNABLE.md + CHECKLIST.md готовы; staging deploy зелёный | §2.5 | 🟡 to-M10 |
| **AC-018** | Демонстрация + оплата 15 000 ₽ + 🟢 SHIPPED | §2.6 | 🟡 to-M11 |

### 7.3 Общие DoD ([`SPEC §8.3`***REMOVED***(SPEC.md#83-общие-dod-для-всего-проекта))

- **AC-G1:** соответствие [`CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md) — ruff/black/mypy/pre-commit.
- **AC-G2:** самодостаточность (`PROJECT_MIGRATION_TEMPLATE.md`): код только в `projects_17/kwork_site/`, без зависимостей от `core_02`/`scripts_01`/`freebuff_plugin*`.
- **AC-G3:** конфиденциальность соблюдена (нет публикации материалов клиента в общий реестр `docs_10/`).

---

## 8. Critical Path (что блокирует что)

```
[T-3***REMOVED*** Отправить 8 вопросов клиенту
 │
 ▼
[T-3..T0***REMOVED*** Async-ожидание Q1..Q5 ──────────┬──► Q1 → принять ADR-002 ⚪→🟢
                                          ├──► Q2 → принять ADR-003 ⚪→🟢
                                          ├──► Q3..Q5 → обновить SPEC/manif/etc
                                          │
                                          ▼
[T0***REMOVED*** **GATE pre-start → Этап 1**
 │  (ВСЕ 5🔴 закрыты AND ADR-002🟢 AND ADR-003🟢)
 │
 ├──► [T1..T2***REMOVED*** §1.0 + §1.1 (архитектура + окружение)   ← ADR-001 уже 🟢, НЕ блокирует
 │
 ├──► [T3***REMOVED*** §1.2 auth + tenant-isolation (NFR-007/010/011)
 │
 ├──► [T4..T5***REMOVED*** §1.3 Excel-pipeline (ADR-003 определяет ключ + схему)
 │
 ├──► [T6..T8***REMOVED*** §1.4 + §1.5 + §1.6 (ЛК + заявка + профиль)
 │
 ├──► [T9***REMOVED*** E2E + make test/lint/typecheck
 │
 ▼
[T10..T11***REMOVED*** §1.7 приёмка → **💰 15 000 ₽ оплата**
 │
 ▼
[T12***REMOVED*** §2.1 SVG-логотип
 │
[T13***REMOVED*** §2.2 ассеты + UI-тема
 │
[T14..T15***REMOVED*** §2.3 карта Leaflet (Q-soft A координаты не блокирует — demo-полигон fallback)
 │
[T16***REMOVED*** §2.4 финальное тестирование (security + tenant-isolation повторно)
 │
[T17***REMOVED*** §2.5 RUNNABLE.md + CHECKLIST.md + staging-deploy
 │
[T18..T20***REMOVED*** §2.6 приёмка → **💰 15 000 ₽ оплата → 🟢 SHIPPED**
```

> 📊 **Critical path:** последовательность T-3 → T0 → T1 → T3 → T4 → T10 → T12 → T14 → T17 → T20. **Любая задержка Q1/Q2 на T-3..T0 критична** — старт Этапа 1 невозможен без принятия ADR-002 + ADR-003. Q-soft A/B/C и фирменные цвета — НЕ блокируют critical path (fallback'ы есть).

---

## 9. Метрики успеха проекта

- **Календарное соответствие:** старт T0 + ~20 дней → приёмка T20 (в пределах ±2 дня).
- **Бюджет:** 30 000 ₽ (≤ 5 % превышение допустимо в буфер; > 5 % — доплата клиента).
- **Code coverage:** repository-функции ≥ 80 % (NFR-011); общий ≥ 70 % (AC-001 pytest-cov).
- **Тесты:** ≥ 5 автотестов tenant-isolation (NFR-010) + ≥ 3 парсер-теста + ≥ 5 автотестов ЛК + ≥ 5 автотестов заявки + ≥ 5 автотестов карты = **~ 23+ автотеста** к концу Этапа 2.
- **Defect-rate:** ≤ 3 бага категории P1 к приёмке Этапа 1; ≤ 5 P1 к приёмке Этапа 2 *(≤ 5 % от AC-NNN = 18 в [`SPEC §8`***REMOVED***(SPEC.md); AC-G1..G3 = 3 обще-проектных AC вынесены в отдельный уровень DoD per [`SPEC §8.3`***REMOVED***(SPEC.md#83-общие-dod-для-всего-проекта))*.
- **Acceptance runs:** клиент OK на обеих приёмках (M6, M11) → оплаты получены → проект закрыт 🟢 SHIPPED.

---

## 10. Cross-links (канон-карта проекта)

### Внутренние (внутри `projects_17/kwork_site/`)

| Документ | Связь в ROADMAP | Когда писать |
|---|---|---|
| [`SPEC.md`***REMOVED***(SPEC.md) | §10 (Этапы) + §11 (блокеры) + §4 (SQL DDL) + §6 (архитектура) + §8 (DoD) | Базис (🟢 уже создан) |
| [`STEPS.md`***REMOVED***(STEPS.md) | §1.0–1.7 + §2.1–2.6 (детальный чек-лист) | Базис (🟢 уже создан, sync §0 5🔴+3🟡) |
| [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) | §6 (риски) + §8 (3 sharp decisions: freeze; manual upload; SMTP) | Базис (🟢 уже создан) |
| [`decisions/ADR-001_auth_tenant_isolation.md`***REMOVED***(decisions/ADR-001_auth_tenant_isolation.md) | §3 (decision gates) + §4.1 (§1.2) | 🟢 ACCEPTED 2026-08-17 |
| [`decisions/ADR-002_python_vs_php.md`***REMOVED***(decisions/ADR-002_python_vs_php.md) | §3 (decision gate pre-start) | ⚪ DRAFT, ждёт **Q1** |
| [`decisions/ADR-003_excel_schema_v1.md`***REMOVED***(decisions/ADR-003_excel_schema_v1.md) | §3 (decision gate pre-start) + §4.1 (§1.3) | ⚪ DRAFT, ждёт **Q2** |
| [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) | §1.1 (T-3) + §3 (decision gates) | 🟢 (готов к отправке в Kwork-чат) |
| [`CLIENT_ANSWER_INTAKE_PROCEDURE.md`***REMOVED***(CLIENT_ANSWER_INTAKE_PROCEDURE.md) | §1.1 (T-3..T0 приём ответов) | 🟢 процедура-гайд |
| [`MANIFEST.md`***REMOVED***(MANIFEST.md) | §11 (M11 — статус 🟢 SHIPPED) | Базис (🟢 уже создан) |
| [`LESSONS.md`***REMOVED***(LESSONS.md) | §1.1 (T0: CON-001 «Блокеры закрыты») + §2 (M6, M11 — итоги этапов) | Пустой; первая запись — T0 |
| [`README.md`***REMOVED***(README.md) | §10 (cross-link) | Базис (🟢 уже создан) |

### Внешние (корневые канонические документы)

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §2 (каркас ROADMAP — required) + §4 (порядок работы) + §8 (проектная регистрация).
- [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../docs_10/core/CODE_QUALITY_STANDARD.md) — стандарт качества кода (ruff/black/mypy/pre-commit hooks обязательны per M2).
- [`docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md) — стандарт готовности (RUNNABLE/CHECKLIST появятся в `M10` / `§2.5`).
- [`docs_10/projects_meta/PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md) — реестр проектов платформы (v1.2 — 7 проектов; kwork_site зарегистрирован).

### Стилевые образцы (sibling-проекты)

- `projects_17/lead_aggregator/` — образец filled-STEPS.md (использован как стиль `STEPS.md`).
- `projects_17/diet_platform/README.md` — образец README для зрелого проекта.
- `projects_17/tg_terminal_messenger/docs/original/tz.md` — канон формата ТЗ (FR/NNN/DoD).

---

*ROADMAP создан: 2026-08-17 · Версия 0.1.0 · Статус: 🟡 DRAFT (готов к старту pre-Этап 1 после закрытия блокеров) · Канон: PROJECT_RULES.md §2 + SPEC §10/§11 + STEPS §1+§2 + ADR-001🟢 + ADR-002/003⚪ + PLAN_BREAKDOWN §6/§8 · Трудоёмкость: ~21 ч / 30 000 ₽ · Календарь: ~22-25 дней · Автор: Buffy (Workspace OS / Freebuff)*
