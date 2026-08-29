# STEPS — log of actions during ROADMAP-LA-001 (промт 69 × 70)

> Формат: `step N: <что сделано> | <почему> | <что дальше>`.
> Project-local log — зеркалит сессионный `../../steps.md`, но в контексте проекта lead_aggregator.
> Создан по шаблону [`docs_10/templates/PIPELINE_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PIPELINE_TEMPLATE.md).

---

## Step 1: Фаза 1 research (2026-08-10)

**Что сделано:**
1. Прочитан `pompts_11/070_07_lead_aggregator_scraper.md` — протокол 4 фаз, запрет кода до утверждения Фаз 1–2.
2. Выполнена Фаза 1: `PHASE1_RESEARCH.md` (матрица защит Telegram/VK/бирж, баны, векторы, LDE L1/L2/L3) — 3 веб-исследователя + аудит платформы W-1…W-7.
3. По запросу пользователя добавлен Attract-трек: исследован **весь телефон** (`/storage/emulated/0/PROJECTS/`, `/ВАКАНСИИ/`, `DOCUMENTS/`, Termux-home) — реальный стек (резюме, portfolio, KWORK-ledger, вакансии). Создан `ATTRACT_MODULE_RESEARCH.md` (каталог источников клиентов, матрица запрос→источники, W-8…W-11).
4. Ревью цикл: 2 прохода code-reviewer-glm, все замечания закрыты.

**Почему:**
- Протокол промта 69: код запрещён до утверждения Фаз 1–2 → выполняем research максимально глубоко.
- Пользователь: «проведи исследование всех источников, изучи мой стек по всему телефону».

**Что дальше (Step 2):** Фаза 2 архитектура + применение шаблона промта 70.

---

## Step 2: Применение промта 70 (шаблон пайплайна) (2026-08-10)

**Что сделано:**
1. Прочитан `pompts_11/071_02_prompt_architect_1_7.md` — 2 миссии: (a) AGENTS.md + PIPELINE_TEMPLATE, (b) Blueprint v3 → Forge Facade.
2. Проанализированы 3 реальных precedents (`docs_10/ROADMAP_VKUSVILL_DEMO_062.md`, `ROADMAP_VV_002_RESEARCH.md`, `ROADMAP_FORGE_RECONCILIATION.md`) + 5 STEPS/LESSONS файлов (`vkusvill_research`, `vkusvill_demo`, `tg_digital_market`).
3. Создан `docs_10/templates/PIPELINE_TEMPLATE.md` — шаблон-скелет (общие секции 3 precedents, специфика — per-task).
4. Созданы project-local `ROADMAP.md`, `STEPS.md` (этот), `LESSONS.md` по шаблону.
5. Расставлены приоритеты: P0 текущая задача (Attract Фаза 2), P1 шаблон, P2 AGENTS.md, P3 Blueprint Facade.

**Почему:**
- Пользователь: «этот проект в рамках создания платформы, фиксируй все согласно промта 70 и продолжаем задачу».
- Промт 70: «AGENTS.md — предпосылка, шаблон пайплайна — то, что внутри него используется»; «не выдумывай с нуля — анализируй precedents».

**Что дальше (Step 3):** `PHASE2_ARCHITECTURE.md` — архитектура Attract-модуля.

---

## Step 3: Фаза 2 — PHASE2_ARCHITECTURE.md (✅ ЗАВЕРШЁН, ОДОБРЕН)

**Что сделано:**
1. Создан `PHASE2_ARCHITECTURE.md` (Data Flow, модульная структура, абстракции TLSClient/ProxyRotator/CheckpointStore/CaptchaSolver, привязка к ModelGateway/telethon/notification/EventBus, таблица выбора библиотек).
2. Acceptance-критерии Task 1 закрыты: все 5 пунктов + раздел «библиотеки и их обоснование» присутствуют.

**Почему:**
- Промт 69 Фаза 2: «спроектируй модульную асинхронную систему, архитектурная схема Data Flow, обоснование выбора библиотек»; промт 70: atomic-шаги с проверяемыми acceptance criteria.

**Что дальше (Step 4):** ревью Фазы 2 пользователем → по решению пользователя Фаза 3 (код). Код не начинается до утверждения (промт 69).

---

## Step 4: Фаза 3 — код Attract-модуля (2026-08-10)

**Что сделано:**
1. По одобренной Фазе 2 создан пакет `projects_17/lead_aggregator/app/`: `core` (config, retry_policy, tls_client), `storage/checkpoint_store` (SQLite+WAL), `processors` (intent_classifier L1/L2, deduplicator, scorer L3), `adapters` (base + kwork + tg_channel), `delivery/telegram`, `pipeline` (run_once + run_forever).
2. Конфиги: `config/keywords.yaml`, `competence_profile.yaml`, `settings.env.example`.
3. Ревью-цикл: 4 прохода code-reviewer-glm → исправлены circuit breaker (threshold≤max_attempts, cooldown-восстановление, `clone()` для per-adapter изоляции), regex TG (tolerant lookahead, source_id без двойного префикса), resume (флаг `ordered`, numeric-tail `_id_key` для границы 99999→100000), подключение RetryPolicy в пайплайн, NameError в deduplicator, chained-comparison gotcha в тесте.
4. Тесты: `tests_09/test_lead_aggregator_core.py` + `test_lead_aggregator_adapters.py` → **26 passed**.

**Почему:**
- Пользователь: «иди следуй roadmap» → Task 2 (Фаза 3) по roadmap после одобрения Фазы 2.
- Промт 69 Фаза 3: async, изоляция адаптеров, checkpointing, retry+jitter, HTML-экранирование, prompt-injection guard.

**Что дальше (Step 5):** живой запуск (настроить `settings.env`), либо подключение реальных источников и прогон на боевых данных.

---

## Step 5: Фаза 4 — Deploy (CLI + dry-run + боевой запуск) (2026-08-10)

**Что сделано:**
1. **CLI** `app/cli.py` — создан (MANIFEST ссылался, файла не было): `--dry-run` (реальные источники, temp-чекпоинты, без доставки), `--once` (боевой), `--forever` (24/7), `--sources kwork,tg`, `--json`, `--interval`.
2. **config.py** — загрузка `settings.env` на уровне модуля (ДО дефолтов Config) + все env-поля через `default_factory` (LA_* читаются при инстанцировании; раньше os.getenv() в default вычислялся при импорте — settings.env не доходил до полей).
3. **settings.env** — создан из example (LA_TG_* пустые → доставка логируется).
4. **Live-верификация (W-16):** первый dry-run дал **0 лидов** → диагностика реальных источников:
   - `t.me/s/freelance_tg` — блоки имеют доп. классы (`tgme_widget_message text_not_supported_wrap service_message js-widget_message`); regex был строгим (`class="tgme_widget_message"`) → исправлен на `tgme_widget_message(?:\s[^"***REMOVED****)?` (опening + lookahead, не цепляет внутренние div'ы). Live: **2 блока** (сервисные сообщения канала, 0 целевых лидов).
   - `kwork.ru/projects` — стал **SPA** (статичный HTML = скелет с `js-wants-list-preloaders`/`wants-content`, все JSON-эндпоинты 404) → `_looks_like_spa_shell()` честно возвращает [***REMOVED*** + warning (нужен headless, W-2).
5. **Боевой `--once`:** fetched=2 (TG, сервисные сообщения → 0 целевых), errors=0, чекпоинт `data/checkpoints.db` записан.
6. Тесты: `test_lead_aggregator_cli.py` (12) + регрессии адаптеров (live-классы TG, SPA-детектор Kwork) → **40 passed**; ревью-цикл 3 прохода (env default_factory, SPA-детектор, lookahead regex).

**Почему:**
- ROADMAP Task 3 (Фаза 4) + открытый вопрос 4 (реальный запуск).
- W-16: live-данные важнее выдуманных фикстур — dry-run на реальных источниках вскрыл расхождение тест-HTML vs живой HTML.

**Что дальше (Step 6):** заполнить `LA_TG_BOT_TOKEN`/`LA_TG_CHAT_ID` для реальной доставки; для Kwork — headless (playwright/curl_cffi, W-2) или поиск публичного API; `--forever` под supervisor/termux-service.
