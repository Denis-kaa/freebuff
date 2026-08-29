# PROJECTS_OVERVIEW — Сводный обзор проектов платформы

| Поле | Значение |
|------|----------|
| **Документ ID** | PROJECTS-OVERVIEW-001 |
| **Версия** | 1.2 |
| **Статус** | 🟢 Актуально |
| **Дата** | 2026-08-17 (ADR-система добавлена в kwork_site) |
| **Основание** | PLAN_NEXT_OPERATIONS.md Этап 1 + PROJECT_RULES.md §8 (регистрация новых проектов) + kwork_site ADR-система (decisions/DECISIONS.md + 3 ADR-файла) |

---

## Сводная таблица

| Проект | Стек | Статус | Роли | Платформенные зависимости | Приоритет |
|--------|------|--------|------|--------------------------|-----------|
| `interior_planner` | React Native Web + Canvas + esbuild-wasm | 🟡 в разработке | interior_consultant | environment_doctor, router | HIGH |
| `diet_platform` | Python 3.10+ (aiogram + FastAPI + SQLite) | 🟢 PRODUCTION (v1.0.0 MVP) | — | — | MEDIUM |
| `realtor_os` | Python (llama.cpp/Ollama + Tesseract OCR + SQLite RAG) | 🟢 Production-ready foundation | — | buffy_manifest.json, companion/state.json | MEDIUM |
| `realtor_automation` | Python (аналог realtor_os) | 🟡 v0.1 foundation | — | — | LOW |
| `freebuff_flutter_app` | Flutter 3.16+ / Dart 3.2+ | 🟡 Phase 5.1 A (shell + lifecycle) | — | core_02/telegram_contract (HTTP bridge) | HIGH |
| `tg_terminal_messenger` | Python + Telethon | 🟢 рабочий | — | используется для TG-доставки | HIGH |
| `kwork_site` | Python (FastAPI/Flask) + SQLite WAL + Jinja2 + Bootstrap 5 + HTMX + Leaflet.js + SMTP | 🟡 DRAFT (каркас проекта готов; до старта кода 6 🔴-блокеров) | — | — (клиентский Kwork-проект; код НЕ зависит от платформенных модулей core_02/scripts_01/freebuff_plugin*) | client (Kwork) |
| `sheet_project` | Python 3 + openpyxl (+ pytest) | 🟡 планирование (каркас + план готовы; код не начат) | — | — (автономный, не зависит от core_02/scripts_01) | LOW |
| `public_request_parser` | Python 3.11+ + SQLite/WAL + RSS/Atom + Telegram delivery (planned) | 🟡 DRAFT (документационный каркас, код не начат) | operator; user (future) | автономный; Telegram fixture-only до policy approval | MEDIUM |
| `python_mentor` | Python 3.11+ + SQLite + pytest; по фазам: pylint/radon/flake8/bandit, fsrs, FastAPI, static UI | 🟡 PLANNING (каркас + роадмап B+C…N; код не начат) | learner (future); curator/mentor/client — deterministic (automated) | автономный, без core_02/scripts_01/freebuff_plugin* | MEDIUM |

---

## Детали по проектам

### 🟡 interior_planner — боевая задача пайплайна

- **Стек:** React Native Web + HTML5 Canvas + esbuild-wasm bundle
- **Роль:** `interior_consultant` (routing: vision, reasoning, plan, explain, multimodal → gemini-2.5-flash)
- **Состояние:** RUNNABLE.md + CHECKLIST.md + README.md ✅, Env Doctor: ok (0 blockers)
- **Последние фичи:** Picsum-текстуры, mobile-first, экспорт/импорт JSON, зум/поворот
- **Следующее:** touch-жесты, текстуры мебели, undo/redo, валидация комнаты

### 🟢 diet_platform — «Пухляш» (nutrition assistant)

- **Стек:** Python 3.10+, aiogram (TG-бот), FastAPI (API), SQLite, APScheduler
- **Статус:** PRODUCTION v1.0.0 MVP
- **Структура:** `main.py` + `bot.py` + `bot_handlers/` (recipes, scheduling, settings) + `api/` (cabinets, mini-apps) + `modules/` (recipes, fitness, personas Puhlyash/Irisochka)
- **Платформенные связи:** нет (автономный VPS-проект)
- **Вывод:** самодостаточный, не требует пайплайна Freebuff. Может быть примером зрелого Python-проекта (эталон структуры).

### 🟢 realtor_os — ОС для риелтора

- **Стек:** Python, локальная LLM (llama.cpp/Ollama), Tesseract OCR, SQLite RAG, работает в Termux ARM64
- **Фокус:** полная операционная среда риелтора: локальный RAG, шифрование PII, OCR, интеграции (Яндекс Диск/Email) с маскированием
- **Связь с Buffy:** `buffy_manifest.json` + `companion/state.json` — взаимодействие с платформой
- **Вывод:** готовый foundation; интересен как проект, использующий локальные LLM (без облака)

### 🟡 realtor_automation — модули автоматизации

- **Стек:** аналогичен realtor_os (Python, SQLite, Tesseract, локальная LLM)
- **Статус:** v0.1 foundation
- **Структура:** модули `rag/`, `security/`, `ocr/`, `llm/`, `integrations/`, `curator/` + CLI
- **Связь с realtor_os:** automation = набор библиотек/модулей, realtor_os = интегрированная система поверх них
- **Вывод:** дублирует архитектуру realtor_os; кандидат на консолидацию

### 🟡 freebuff_flutter_app — мобильный компаньон Freebuff

- **Стек:** Flutter 3.16+/Dart 3.2+, `http` (мост к Freebuff), wakelock_plus
- **Цель:** держать core-процесс Freebuff живым в фоне на Android 14/15 (обход Phantom Process Killer)
- **Статус:** Phase 5.1 A — Android shell + foreground service (`connectedDevice` type) + lifecycle + smoke tests
- **Ключевые файлы:** `FreebuffForegroundService.kt`, `AndroidManifest.xml`, `lib/main.dart`, `sync_status.dart`
- **Платформенные связи:** chat_id + reports через `core_02/telegram_contract` (HTTP bridge)
- **Приоритет:** HIGH — прямой мост к платформе

### 🟢 tg_terminal_messenger — TG-доставка

- **Стек:** Python + Telethon
- **Роль:** транспорт для всех TG-уведомлений платформы (Saved Messages + Литвинов)
- **Статус:** рабочий, используется `core_02/telegram_contract.py` + `_tg_client_v2.py`

### 🟡 kwork_site — B2B-портал для ТК «КТК ТРАСТ» (клиентский Kwork-проект)

- **Slug:** `kwork_site`
- **Тип:** **внешний клиентский заказ** (Kwork.ru, **НЕ** платформенный модуль Workspace OS — изоляция per `MANIFEST.md` Scope Rules).
- **Назначение:** B2B-портал: личный кабинет компании-грузополучателя с дислокацией контейнеров (из 2 Excel-файлов), онлайн-заявкой и интерактивной картой маршрутов.
- **Стек:** Python 3.10+ (FastAPI или Flask) + SQLite 3.35+ (`PRAGMA journal_mode=WAL`) + Jinja2 SSR + Bootstrap 5 + HTMX + Leaflet.js 1.9+ (OSM + SVG-overlay маршрутов) + SMTP для email-доставки заявок.
- **Бюджет:** **30 000 ₽** (Этап 1: 15 000 ₽ — базовый сервис + Excel pipeline; Этап 2: 15 000 ₽ — карта + SVG-логотип + финальное тестирование).
- **Клиент:** ООО ТК «**КТК ТРАСТ**» (контейнерные перевозки) — коммерческая тайна (per `MANIFEST.md`, **не публиковать** материалы в `docs_10/` кроме одной строки в этом обзоре).
- **Состояние (на 2026-08-17):** 🟡 **DRAFT** — каркас проекта создан:
  - ✅ `MANIFEST.md` — паспорт проекта (DRAFT v0.1.0)
  - ✅ `01_PLAN_BREAKDOWN.md` — план-разбор (entity model / sitemap / asset gap / stack / 3 sharp decisions)
  - ✅ `STEPS.md` — чек-лист Этапов 1+2 (15+15 чек-пунктов + 8 🔴-блокеров §0)
  - ✅ `README.md` — навигатор исполнителя + каркас клиента
  - ✅ `LESSONS.md` — пустой CON/CAN/ANTI/PB-журнал
  - ✅ `SPEC.md` — формальное ТЗ (13 разделов; 45 FR-NNN + 21 NFR-NNN + 18 AC + SQL DDL)
  - ✅ `decisions/{DECISIONS.md, ADR-NNN_*.md***REMOVED***` — ADR-каталог (см. ниже «DOCS integration (ADR)»).
  - 🟡 Запланировано: `ROADMAP.md`, `RUNNABLE.md`, `CHECKLIST.md` (по графику Этапов)
- **📄 DOCS integration (ADR-система, 2026-08-17):**
  - [`projects_17/kwork_site/decisions/`***REMOVED***(../../projects_17/kwork_site/decisions/) создан: индекс [`decisions/DECISIONS.md`***REMOVED***(../../projects_17/kwork_site/decisions/DECISIONS.md) (status legend 🟢/🟡/🔴/⚪) + 3 ADR-файла в MADR-формате (**Context / Options / Decision / Rationale / Consequences**).
  - **🟢 [`ADR-001_auth_tenant_isolation.md`***REMOVED***(../../projects_17/kwork_site/decisions/ADR-001_auth_tenant_isolation.md) — ACCEPTED 2026-08-17:** принят как **первый архитектурный шаг** Этапа 1.0 (см. `STEPS.md` §1.0 first bullet + `README.md` «Архитектурные правила» rule #1). Решение: row-level `WHERE company_id = ?` через repository-обёртку (`app/database/repository.py`); tenant-isolation инвариант (NFR-007/010/011) + Coverage ≥ 80 % (NFR-011) + ≥ 5 автотестов (NFR-010). **Не зависит от блокеров Q1..Q5** (auth вне Excel-pipeline per `01_PLAN_BREAKDOWN.md` §1.2), поэтому принят заблаговременно — это **первый решенный вопрос** Этапа 1.0.
  - **⚪ [`ADR-002_python_vs_php.md`***REMOVED***(../../projects_17/kwork_site/decisions/ADR-002_python_vs_php.md) — DRAFT:** структура решения подготовлена (3 варианта: Python recommended / PHP / Hybrid out-of-scope); ждёт промоции ⚪ → 🟢 после ответа клиента по **Q1** из `CLIENT_QUESTIONS_v1.md` (Python vs PHP; default по `01_PLAN_BREAKDOWN.md` §5.1 = Python). Downstream: при принятии PHP — переписать `SPEC.md` §5.1 + таймлайн.
  - **⚪ [`ADR-003_excel_schema_v1.md`***REMOVED***(../../projects_17/kwork_site/decisions/ADR-003_excel_schema_v1.md) — DRAFT:** структура решения подготовлена (4 варианта: `container_no` UNIQUE-constraint + manual upload recommended / composite-key / auto-detect / auto-CSV-detect); ждёт промоции ⚪ → 🟢 после ответа клиента по **Q2** из `CLIENT_QUESTIONS_v1.md` (структура колонок + общий ключ + периодичность). **Downstream impact:** при принятии обновить `SPEC.md` §4 SQL DDL (финальные колонки `Container` / `Dislocation` / `UploadLog`).
  - **ADR-система пересекается с:** `STEPS.md §1.0` (ADR-001 = first bullet) и `README.md` «Архитектурные правила» rule #1 (dual-source: ADR-001 + SPEC §6.2 + NFR-007/010/011 + INV-1).

- **3 sharp decisions** (per `01_PLAN_BREAKDOWN.md` §8): **(1)** 🔴 freeze DB schema до получения 2 эталонных Excel от клиента; **(2)** 🔴 ручная `/admin/upload` (без FTP/API-интеграций); **(3)** 🟡 email-доставка заявок через SMTP (без БД-реестра в MVP).
- **Блокеры до старта кода** (см. `STEPS.md` §0 / `SPEC.md` §11): 🔴 Python vs PHP / 🔴 2 эталонных Excel (структура, общий ключ) / 🔴 «скрин конкурента» (файл vs термин) / 🔴 фирменные цвета КТК ТРАСТ (HEX/RGB) / 🔴 список полей онлайн-заявки / 🔴 тестовая выборка гео-координат. Без их разрешения SPEC.md остаётся в статусе DRAFT и кодинг не стартует.
- **Связь с платформой Freebuff:** ❌ **нет** (per `MANIFEST.md` Scope Rules — аддитивность: код проекта — только в `projects_17/kwork_site/`, без изменений в `core_02/`/`scripts_01/`/`freebuff_plugin*`).
- **Следующее:** `ADR-001` ✅ **уже принят** (см. «DOCS integration» выше) → отправить клиенту в Kwork-чат готовые вопросы из [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../../projects_17/kwork_site/CLIENT_QUESTIONS_v1.md) § «Сообщение для отправки» (5🔴+3🟡) → дождаться **Q1** (Python vs PHP) + **Q2** (Excel schema) → промоция `ADR-002`/`ADR-003` ⚪ → 🟢 → запросить остальные 🔴-блокеры → развернуть `ROADMAP.md` / `RUNNABLE.md` / `CHECKLIST.md`.

---

### 🟡 python_mentor — детерминированная платформа обучения Python

- **Стек:** Python 3.11+ + SQLite (stdlib) + pytest; по фазам — pylint/radon/flake8/bandit (diagnostics), fsrs (scheduler), FastAPI (thin layer), static HTML/CSS/JS (UI).
- **Назначение:** автономный learning runtime без LLM в базовом контуре: competency map → лицензионно-чистый corpus (Exercism) → автогрейдер → execution runtime (MVP-tier) → AST/статика → hints L0–L6 → evidence-first state machine (S0–S5) → FSRS → activity selector (Куратор) → project engine («Заказчик») → FastAPI → минимальный UI → E2E-валидация. LLM — опциональный внешний слой (фаза O).
- **Состояние (2026-08-23):** 🟡 PLANNING — создан обязательный каркас (MANIFEST/README/SPEC/ROADMAP/STEPS/LESSONS/RUNNABLE/CHECKLIST/decisions, project.yaml) + ADR-001…004 (детерминизм-первичность, фазовые гейты, sandbox tiers, license gate). Код не начат.
- **Каноны внутри проекта:** `python_ai_tutor_blueprint_v0.1.md` (контракты, source of truth), `python_ai_tutor_methodology.md` (педагогика), `prompt1.md` (Phase B+C), `prompt2.md` (Phase D–N), `prompt3.md` (master), `python_ai_tutor_prompts.md` (LLM-промты, future).
- **Связь с платформой Freebuff:** ❌ нет (автономный, self-contained в `projects_17/python_mentor/`; запрет импорта core_02/scripts_01/freebuff_plugin*).
- **Следующее:** Phase B+C — Competency Map + Exercism Ingestion (по `prompt1.md`): research → карта компетенций → license gate → idempotent ingestion → coverage/gap отчёты → G-BC → Phase D.

---

### 🟡 public_request_parser — универсальный парсер публичных заявок

- **Стек:** Python 3.11+, SQLite/WAL, RSS/Atom first; Telegram adapter fixture-only до отдельного policy/legal approval.
- **Назначение:** поиск открытых публикаций с запросами на услуги по персональным профилям, дедупликация, TTL полного текста и Telegram-доставка.
- **Состояние (2026-08-22):** 🟡 DRAFT — создан обязательный каркас MANIFEST/README/SPEC/ROADMAP/STEPS/LESSONS/RUNNABLE/CHECKLIST, код не начат.
- **Граница:** универсальный parser отделён от `projects_17/lead_aggregator`, который остаётся прикладным Attract/lead-сценарием с competence и commercial scoring.
- **Policy:** read-only, без outbound к авторам, без базы авторов и без обхода ограничений; Telegram live не включается автоматически.
- **Следующее:** source/policy matrix для первого RSS/Atom URL → domain contracts → RSS/Atom vertical slice.

### 🟡 sheet_project — конфигурируемый генератор Excel-дашбордов (D2)

- **Стек:** Python 3 + openpyxl 3.1.5 (+ pytest)
- **Назначение:** архитектура D2 — структура XLSX, данные, стили и правила проверки отделены от кода генератора (`CONFIG → GENERATOR → XLSX`). Первый результат — эталонный проектный дашборд, затем другие XLSX без правки ядра.
- **Состояние (2026-08-18):** 🟡 каркас проекта создан (MANIFEST/LESSONS/decisions/ROADMAP/README/RUNNABLE/CHECKLIST/STEPS); план из 10 шагов задокументирован в `STEPS.md`; ADR-001 (стек) принят. Код не начат.
- **Ограничения:** без VBA/макросов; openpyxl не вычисляет формулы (расчёт — отдельный опциональный слой LibreOffice); без внешних интеграций на первом этапе.
- **Связь с платформой Freebuff:** ❌ нет (автономный, self-contained в `projects_17/sheet_project/`).

---

## Рекомендации

1. **Запускать в первую очередь:** freebuff_flutter_app (мост к платформе, HIGH), interior_planner (боевая задача)
2. **Требуют ролей:** interior_planner (interior_consultant ✅), realtor_os (кандидат: realtor_consultant)
3. **Блокированы окружением:** realtor_os/realtor_automation — требуют Tesseract + локальную LLM (тяжёлая установка на Termux)
4. **Консолидация:** realtor_automation дублирует realtor_os — рассмотреть слияние
5. **Автономны (не трогать):** diet_platform — production VPS-проект

---

## Следующие шаги

- [ ***REMOVED*** Аудит каждого проекта через Env Doctor (`python3 -m core_02.environment_doctor <path>`)
- [ ***REMOVED*** Регистрация ролей для realtor_os (если нужен пайплайн)
- [ ***REMOVED*** Интеграция freebuff_flutter_app с continue_endpoint.py (держать сессию живой с телефона)
