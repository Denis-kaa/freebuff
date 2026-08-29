# steps.md — Журнал шагов агента платформы

**Задача:** 070_07_lead_aggregator_scraper · Фаза 1 (Research & Reconnaissance) — Lead Aggregator / Scraper Engine
**Режим выполнения:** агент платформы Workspace OS (Freebuff), dogfooding-режим
**Сессия:** 2026-08-10 · **Агент:** Buffy (z-ai/glm-5.2)

> Цель журнала — фиксировать КАЖДЫЙ шаг так, как это делал бы агент платформы,
> и по ходу отмечать слабые места платформы, которые мешают/замедляют выполнение задачи.

---

## Шаг 1 — Приём задачи (070_07_lead_aggregator_scraper)

- [x***REMOVED*** Прочитан `pompts_11/070_07_lead_aggregator_scraper.md` (SYSTEM PROMPT: Autonomous Production Scraper & Lead Aggregator Engineer).
- [x***REMOVED*** Понят строгий 4-фазный протокол: **Фаза 1 (Research) → Фаза 2 (Architecture) → Фаза 3 (Code) → Фаза 4 (Deploy)**. Код (Фаза 3) запрещён до утверждения пользователем Фаз 1–2.
- [x***REMOVED*** Пользователь выбрал: начать **Фазу 1**, выполнять как агент платформы, фиксировать шаги в `steps.md`, искать слабые места платформы.

### 🟡 Слабое место платформы W-1 (процессное)
Промт требует «выдай отчёт, жду ревью перед Фазой 3» — но платформа не имеет **встроенного workflow-стейт-машины для промтов** (нет артефакта типа `PHASE_STATUS`). Журнал `steps.md` ведётся вручную агентом, статус фаз не машиночитаем. Формат журнала не стандартизирован (глобальный поиск `**/steps.md` → 0 файлов, конвенция отсутствует).

---

## Шаг 2 — Контекст платформы (что платформа умеет)

- [x***REMOVED*** Прочитаны `PLATFORM.md` (позиционирование Workspace OS) и `TASK.md` (v5.110.0, Phase 5 открыта).
- [x***REMOVED*** Составлен инвентарь: `core_02/` (24 модуля: workspace_registry, remote_sync, forge_pipeline, scenario_registry, router, memory_store…), `scripts_01/` (tool_runtime, model_gateway, telegram_bot, prompt_queue, event_bus…), `freebuff_plugin_03/`, `projects_17/` (7 проектов).
- [x***REMOVED*** Проверено окружение: **Python 3.14.6 / Android (Termux)**. Установлены: `telethon`, `aiohttp`, `httpx`, `bs4`, `fastapi`, `asyncio`. **Отсутствуют:** `curl_cffi`, `playwright`, `asyncpg`, `redis`, `socks`.
- [x***REMOVED*** Изучен `scripts_01/tool_runtime.py` (HTTPTool = голый `httpx.Client`, без TLS-impersonation/прокси/ретраев) и `scripts_01/model_gateway.py` (6 провайдеров: DeepSeek/Gemini/Ollama/OpenRouter/SambaNova/DashScope — **готовая база для L3-классификатора лидов**).
- [x***REMOVED*** Код-поиск подтвердил: платформа **уже** умеет Telegram/Telethon (`core_02/_tg_client_v2.py`, `core_02/remote_sync.py`, паттерны `FLOOD_WAIT` в `scripts_01/e2e_dual_path_tg_verify.py`), экспоненциальный backoff (`scripts_01/notification.py`, `freebuff_plugin_03/bootstrap/installer.py`, `scripts_01/orchestrator.py`).

### 🟡 Слабые места платформы (инфраструктурные)
- **W-2 (библиотеки):** стек промта 69 требует `curl_cffi` (TLS/JA3-impersonation), `playwright` (headless), `asyncpg` (PostgreSQL), `redis`, `pysocks`. На платформе **ничего из этого нет** → Фаза 3 потребует установки новых зависимостей в Termux, риск несовместимости с Python 3.14.6 (например, для `curl_cffi` на Termux/ARM64 вероятно нет готовых wheel — потребуется сборка из C-исходников).
- **W-3 (хранилище):** платформа — SQLite-only (`data_13/context.db`, WAL). Промт 69 требует PostgreSQL + Redis. Для чекаупоинтов парсера Redis не нужен (SQLite достаточно), но PostgreSQL — архитектурный разрыв.
- **W-4 (HTTP-инструмент):** `HTTPTool` не умеет ни прокси, ни TLS-impersonation, ни retry-with-jitter, ни подмены заголовков на уровне браузера. Для боевого парсинга придётся писать отдельный адаптер — `tool_runtime` не расширяем под это без модификаций.
- **W-5 (асинхронность):** `tool_runtime` синхронный (`httpx.Client`, `subprocess.run`). Промт 69 требует полной async-модели (`asyncio`/`httpx.AsyncClient`). Асинхронные инструменты (`aiohttp` есть) не обёрнуты в ToolRegistry.

### ✅ Сильные стороны платформы (найденные по ходу)
- **S-1:** ModelGateway → L3 (Micro-LLM) классификатор лидов «из коробки», с fallback и key rotation.
- **S-2:** Telethon уже интегрирован → Telegram-адаптер (User API) реализуем на готовой базе (`_tg_client_v2`).
- **S-3:** паттерны `FLOOD_WAIT`-обработки и exponential backoff уже есть в коде — можно переиспользовать.
- **S-4:** EventBus + notification.py → Delivery Engine (Telegram-уведомления о лидах) готов.

---

## Шаг 3 — Внешнее исследование целей (Фаза 1 промта)

- [x***REMOVED*** Запущены 3 веб-исследователя параллельно:
  - **Telegram**: MTProto rate-limits (`FLOOD_WAIT_X`, ошибка 420), Bot API vs User API, баны userbot-аккаунтов, прогрев сессий, `t.me/s/<channel>` web-превью как fallback.
  - **VK**: лимиты Official API (3/20/5–60 rps по типу ключа), ошибка 6 «too many requests», капча, fingerprinting, приватные API-эндпоинты веб-фронта.
  - **Cloudflare/WAF-ландшафт 2025–2026**: 5 слоёв trust-score (TLS-JA3/JA4, browser fingerprint, behavior, IP reputation, Turnstile), инструменты `curl_cffi`/`tls-client`/Nodriver/Camoufox/SeleniumBase UC, прокси-стратегии (sticky sessions, pool fatigue, soak-тесты).

### 🟡 Слабое место платформы W-6 (исследовательский конвейер)
Платформа не имеет **встроенного research-конвейера с источниками и цитированием** — веб-исследование выполняется внешними агентами вне реестра платформы, результаты не складываются в `engineering_memory` автоматически (нужно ручное действие). Отчёт Фазы 1 формируется агентом вручную.

---

## Шаг 4 — Анализ и синтез (выполнен в этом журнале + отчёт)

- [x***REMOVED*** Составлена **Матрица уязвимостей и методов обхода** (3 площадки × защита × вектор × риск) — см. `projects_17/lead_aggregator/PHASE1_RESEARCH.md` §2.
- [x***REMOVED*** Классифицированы типы банов (IP / Browser-Fingerprint / Account) — §3.
- [x***REMOVED*** Определены векторы извлечения (API / headless / DOM-scan / web-preview) — §4.
- [x***REMOVED*** Спроектирован **Lead Detection Engine** (L1 regex → L2 intent → L3 LLM-score 0–100) с привязкой к ModelGateway платформы — §5.
- [x***REMOVED*** Собран **Аудит слабых мест платформы** (W-1…W-7) — §6.

### 🟡 Слабое место платформы W-7 (легальный/этический контроль)
Промт 69 требует «обходить WAF, баны, CAPTCHA, 24/7» — это зона юридического риска (ToS, 152-ФЗ, GDPR для персональных данных лидов). Платформа не имеет **policy-гейта** (нет модуля, который бы требовал подтверждения легальности сбора до деплоя адаптера). Для боевого продукта это must-have перед Фазой 3.

---

---

## Шаг 5 — Глубокое исследование всего телефона (реальный стек, не README)

- [x***REMOVED*** По просьбе пользователя вышел за пределы проекта: `/storage/emulated/0/PROJECTS/` (34+ директорий), `/storage/emulated/0/PROJECTS/workstation/` (27), `/storage/emulated/0/ВАКАНСИИ/`, `/storage/emulated/0/pompts/`, `DOCUMENTS/`, `/root/` (Termux home).
- [x***REMOVED*** Прочитаны **реальные артефакты**: резюме (`DOCUMENTS/work_reports/РЕЗЮМЕ`), портфолио (`portfolio_full/index.html`), KWORK-манифест и ledger (реальные заказы: Clean_Landing 5к, Joomla_Stairs 8к, КД-расчёт кровати 40к), HR-агент (конвейер откликов), dietolog (TG-бот с Gemini), FREELANCER_OS (аудиофабрика: писатель/диктор/дизайнер → TG/YT/VK/Дзен), 5 файлов реальных вакансий.
- [x***REMOVED*** Учтено указание пользователя: код и доки написаны агентами (Buffy/другие НС) → стек выводится из **живых артефактов** (резюме, portfolio meta, ledgers, bash_history), а не из самоописаний в README.
- [x***REMOVED*** ⚠️ Пометка о полноте: профиль стека — выборка по ~15 директориям из 34 (ai-oracle/ и arbitr_cockpit/ пусты — только tar.gz); для competence_profile (W-8) нужен полный enumeration-проход.

**Собранный стек пользователя (реальный):**
- **AI-разработчик / интегратор LLM** — Python, LLM API (OpenAI/Claude/DeepSeek/Gemini), мультиагентные системы, промпт-инжиниринг, RAG, Pydantic/JSON Schema.
- **Telegram-боты** — aiogram + Telethon (пользовательские и userbot), автоматизация.
- **Backend/инфра** — FastAPI, Docker, REST/вебхуки, Android/Termux, Linux/Git.
- **Сайты** — HTML/CSS лендинги, Joomla, WordPress (WP Builder + ACF), КД-расчёты мебели.
- **Продукты на телефоне** — interior_planner, tg_terminal_messenger, diet_platform, realtor_os, tg_digital_market, vkusvill_demo, LUDMILA_SITE (артбук), audiofabrika.

### 🟡 Слабые места платформы (найдены на этом шаге)
- **W-8 (нет реестра компетенций):** платформа не хранит стек пользователя — его пришлось собирать вручную из резюме/портфолио/ledgers. Attract-модулю нужен машиночитаемый профиль компетенций (для генерации запросов).
- **W-9 (нет scan-модуля вне проекта):** платформа не имеет инструмента сканирования ФС телефона за пределами workspace — исследование `/storage/emulated/0` выполнено вручную через shell.

---

## Шаг 6 — Веб-исследование источников клиентов под стек

- [x***REMOVED*** 3 веб-исследователя: (1) фриланс-биржи рунета, (2) TG-каналы/боты с заказами, (3) аутрич для AI-автоматизации.
- [x***REMOVED*** Собран каталог: биржи (Kwork/FL.ru/Weblancer/Profi/Яндекс Услуги/Хабр Фриланс), TG-каналы заказов (@freelance_tg, @freelance_it, @kwork_parsing, @it_freelance_chat, @freelance_bay, @proger_orders), боты-агрегаторы (@Golubin_bot, @FreelanceBot, @OrderBot), вакансии (@job_python, @datasciencejobs, @data_science_job, @getmatch_it, @python_jobs_ru), аутрич (2ГИС/Яндекс.Карты, TenChat, VC.ru), партнёрства (интеграторы AmoCRM).

### 🟡 Слабое место платформы W-10 (нет коннекторов к источникам заказов)
Платформа имеет Telegram-интеграцию (для своих сообщений), но **не имеет адаптеров к биржам/каналам заказов** (Kwork API-парсер, TG-агрегаторы) — это и есть ядро будущего Attract-модуля. Также нет хранения «интент-профиля» заказчика (стек пользователя ↔ запрос ↔ каналы).

---

## Шаг 8 — P3: Blueprint v3 → Forge Facade, Задача 0 (исследование) (2026-08-10)

- [x***REMOVED*** Прочитан промт 70 Миссия 2 — Задача 0: внутренний аудит 17 ролей + проверка runtime_05/providers/ auto-discovery.
- [x***REMOVED*** Направление А: role-by-role аудит 17 ролей из `blueprints_v3/registry.yaml` → **15/17 — производственные стадии** (explainer→…→retrospective, имеют dependencies+outputs), **2/17 — справочные** (orchestrator, context_keeper), `response_writer` — presale-параллельный трек.
- [x***REMOVED*** Критическая находка: цепочка **декларативна, но НЕ исполняется** — `resolve_pipeline()` вызывается только из тестов (live-grep: 0 prod-вызовов); `wizard.py` выбирает одну роль; grep `forge` в scenario_registry/wizard_lib → 0.
- [x***REMOVED*** Направление Б: внутренний прецедент auto-discovery **подтверждён** — ARCHITECTURE_MANIFEST принцип №7 Marketplace-Ready + 3 реализации (providers `runtime_05/providers/` / scenarios `runtime_05/scenarios/` / plugins `plugins_04/`).
- [x***REMOVED*** Дрейф: `8a_ssa.md` на диске, но НЕ в registry.yaml; `environment_doctor` в CAPABILITIES_OVERRIDE, но не в pipeline (grep 0).
- [x***REMOVED*** Создан `docs_10/engineering-memory/P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md` (findings + evidence-index + forward-выводы для Задачи 1) + ревью-цикл (замечания закрыты: критерий стадии, Facade-scope для response_writer, live-верификация claims).
- [x***REMOVED*** Forward для Задачи 1: Facade узкий (15 стадий), сохраняет §7.3 boundary, UNFORGED-семантику, `record_run()` готов (`forge.py:151`); паттерн — YAML+dispatch (как providers/scenarios).

## Шаг 7 — Промт 70: приоритеты + шаблон пайплайна (2026-08-10)

- [x***REMOVED*** Прочитан `pompts_11/071_02_prompt_architect_1_7.md` — 2 миссии: (a) AGENTS.md + PIPELINE_TEMPLATE, (b) Blueprint v3 → Forge Facade.
- [x***REMOVED*** Расставлены приоритеты: **P0** текущая задача (Attract Фаза 2) → **P1** PIPELINE_TEMPLATE (промт 70 Задача 2) → **P2** AGENTS.md/CLAUDE.md (Задача 1) → **P3** Blueprint Facade (Миссия 2).
- [x***REMOVED*** Проанализированы 3 реальных precedents (ROADMAP_VKUSVILL_DEMO_062, ROADMAP_VV_002_RESEARCH, ROADMAP_FORGE_RECONCILIATION) + 5 STEPS/LESSONS — выведено ~11 общих секций.
- [x***REMOVED*** Создан `docs_10/templates/PIPELINE_TEMPLATE.md` (шаблон-скелет: explain-first, roll-up, границы, capability-check, gates, карта файлов, atomic-шаги, риски, acceptance, вопросы, cross-links).
- [x***REMOVED*** Шаблон применён к проекту: `projects_17/lead_aggregator/{ROADMAP.md, STEPS.md, LESSONS.md***REMOVED***`.
- [x***REMOVED*** Создан `projects_17/lead_aggregator/PHASE2_ARCHITECTURE.md` — архитектура Attract-модуля (Data Flow, модули, абстракции TLSClient/ProxyRotator/CheckpointStore, привязка к ModelGateway/telethon/notification, выбор библиотек).

### 🟡 Слабые места платформы (найдены на этом шаге)
- **W-12 (нет PIPELINE_TEMPLATE до этого шага):** 3-кратный паттерн STEPS+LESSONS+ROADMAP использовался ad hoc без общего шаблона (подтверждено промтом 70). Шаблон создан — механизм закрыт.
- **W-13 (AGENTS.md конфликтует с session-checkpoint) — RESOLVED (P2):** корневой `AGENTS.md` — теперь канонические правила платформы; конфликт решён через `wrapper._backup_agents_md()` (бэкап → `.freebuff_original_agents`) + `monitor.sh::restore_agents()` (восстановление после сессии, в т.ч. в timeout-пути). Раньше `launch()` писал session-файл без бэкапа, а `monitor.sh` после `mv` удалял файл `rm -f` — канон терялся после каждой сессии.

## Шаг 9 — P3: Blueprint v3 → Forge Facade, Задачи 1+2 (дизайн + реализация) (2026-08-10)

- [x***REMOVED*** Задача 1: создан `docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md` — дизайн ForgeFacade: единственная санкционированная точка входа роль → Forge-прогон, сохраняет §7.3 boundary (ForgePipeline инстанцируется ТОЛЬКО в Facade), явный opt-in `initiate_forge()` (не автоматически, не молча), UNFORGED-семантика делегирована `record_run()`.
- [x***REMOVED*** Задача 2: создан `core_02/forge_facade.py` — `PIPELINE_ROLES` = **14 ролей** (12 ядро + frontend + devops; Задача 0 считала 15/17 **с** presale-треком response_writer, который из Facade-scope исключён), `ForgeFacadeResult` (frozen dataclass, `initiated_explicitly=True`), `can_initiate()` gate, `initiate_forge()` (register_project → ForgePipeline.run → record_run), `get_status()` read-only.
- [x***REMOVED*** Тесты `tests_09/test_forge_facade.py` (12 тестов): gate-тесты, явная инициация, record_run-история, ValueError для справочных/неизвестных ролей, сводка стадий, §7.3 grep-инвариант (scenario_registry/wizard_lib не знают про forge).
- [x***REMOVED*** Регрессия: `test_forge_facade + test_scenario_registry + test_forge_pipeline + test_blueprint_v3` → **72 passed**.
- [x***REMOVED*** Ревью-цикл: найдены и исправлены 2 бага — (1) недосчёт 15 vs 14 ролей (тест ждал 15, множество = 14; согласованы код/тест/дизайн-док с пояснением про response_writer); (2) `get_status("web_app")` → None (register_project слагифицирует `web_app` → `web-app` через `_slug()`; тест теперь использует `result.project_id`). Финальное ревью — чисто.

## Шаг 10 — Документационный слой: встроенные промты 071_02_prompt_architect_1_7 + MANIFEST + ADR (2026-08-10)

- [x***REMOVED*** **Ответ на критику пользователя:** 071_02_prompt_architect_1_7.md содержит 2 встроенных промта (ПРОМТ АРХИТЕКТОР 1.7 стр. 1–380, IDEA EXPLORER v2.0 стр. 381–925), которые ранее не применялись; lead_aggregator не имел MANIFEST.md/ADR — исправлено.
- [x***REMOVED*** Прогон **IDEA EXPLORER v2.0** → `IDEA_EXPLORER_RUN.md` (7 веток → score → prune → depth-2 → cross-pollination → reframe → 3 кандидата → A подтверждён, B7-трек, B2-park).
- [x***REMOVED*** Прогон **ПРОМТ АРХИТЕКТОР 1.7** → `PROMT_ARCHITECT_RUN.md` (base prompt для Фазы 3, CONSISTENCY GATE 11/11).
- [x***REMOVED*** **MANIFEST.md** для lead_aggregator (конвенция платформы: паспорт/цели/архитектура/scope/контроль Buffy).
- [x***REMOVED*** **ADR-013** (ForgeFacade) + **ADR-014** (Attract-модуль) — 13/14-й ADR платформы.
- [x***REMOVED*** Обновлены реестры: IDEAS.md §15 (2 идеи со статусами) + DOCUMENT_REGISTRY.md (ACTIVE 79→86).
- [x***REMOVED*** CHANGELOG v5.146.0 prepended.

## Шаг 11 — Project-local ADR конвенция + Протокол миграции проекта (2026-08-10)

- [x***REMOVED*** Исследование: platform ADR (14 в `docs_10/engineering-memory/decisions/`), project-local ADR в проектах → 0 (grep), PLATFORM.md:493 открытый вопрос «экспортируемость workspace-ов», принцип портируемости MANIFEST-конвенции.
- [x***REMOVED*** Создан **`docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md`** — протокол выноса проекта с сохранением решений (инвентаризация → самодостаточность → экспорт → конвертация платформенных ADR с provenance → приёмка).
- [x***REMOVED*** Создана **project-local ADR конвенция** для lead_aggregator (`decisions/`): `DECISIONS.md` (индекс) + **ADR-001** (pull-модель + порядок источников) + **ADR-002** (юр. гейт read-only) + **ADR-003** (контракты-адаптеры вместо импортов).
- [x***REMOVED*** MANIFEST.md обновлён (секция decisions + «Миграция (готовность к выносу)»).
- [x***REMOVED*** CHANGELOG v5.147.0 + DOCUMENT_REGISTRY ACTIVE 86→88.

## Шаг 12 — Рекомендация W-14 закрыта: pre-flight гейт встроенных промтов (2026-08-10)

- [x***REMOVED*** Выполнена рекомендация W-14 (шаг 10): встроенные промты 071_02_prompt_architect_1_7 (ПРОМТ АРХИТЕКТОР 1.7 стр. 1–372, IDEA EXPLORER v2.0 стр. 373–925) зафиксированы в `docs_10/templates/PIPELINE_TEMPLATE.md` §0 как **опциональный pre-flight гейт**.
- [x***REMOVED*** Гейт содержит: критерии включения (таблица: развилки → IDEA EXPLORER, компиляция концепции → ПРОМТ АРХИТЕКТОР), порядок (ДО создания ROADMAP), фильтр пропуска (микрозадачи без развилок), эталон прогонов (`lead_aggregator/IDEA_EXPLORER_RUN.md` + `PROMT_ARCHITECT_RUN.md`).
- [x***REMOVED*** Границы строк **уточнены live-grep**: IDEA EXPLORER v2.0 — строка 373 (а не ~381 из ранней оценки Шага 10) → в §0 зафиксировано 1–372 / 373–925 с оговоркой о перепроверке.
- [x***REMOVED*** CHANGELOG v5.149.0 prepended.

## Итог шагов

| Шаг | Действие | Статус | Артефакт |
|-----|----------|--------|----------|
| 1 | Приём задачи 070_07_lead_aggregator_scraper | ✅ | `pompts_11/070_07_lead_aggregator_scraper.md` |
| 2 | Контекст платформы + окружение | ✅ | `steps.md` §Шаг 2 |
| 3 | Веб-исследование 3 целей | ✅ | `PHASE1_RESEARCH.md` §2–§4 |
| 4 | Синтез: матрица + LDE + аудит | ✅ | `PHASE1_RESEARCH.md` §5–§6 |
| 5 | Исследование всего телефона (реальный стек) | ✅ | `steps.md` §Шаг 5 |
| 6 | Веб-исследование источников клиентов | ✅ | `ATTRACT_MODULE_RESEARCH.md` |
| 7 | Промт 70: приоритеты + PIPELINE_TEMPLATE + применение | ✅ | `templates/PIPELINE_TEMPLATE.md`, `ROADMAP/STEPS/LESSONS.md` |
| 8 | P3 Задача 0: аудит 17 ролей + auto-discovery | ✅ | `P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md` |
| 9 | P3 Задачи 1+2: ForgeFacade дизайн + реализация | ✅ | `P3_FORGE_FACADE_DESIGN.md`, `core_02/forge_facade.py`, `test_forge_facade.py` |
| 10 | Документационный слой: IDEA EXPLORER + ПРОМТ АРХИТЕКТОР + MANIFEST + ADR-013/014 | ✅ | `IDEA_EXPLORER_RUN.md`, `PROMT_ARCHITECT_RUN.md`, `MANIFEST.md`, ADR-013/014 |
| 11 | Project-local ADR + Протокол миграции проекта | ✅ | `PROJECT_MIGRATION_TEMPLATE.md`, `decisions/DECISIONS.md` + ADR-001…003 |
| 12 | Рекомендация W-14 закрыта: pre-flight гейт встроенных промтов | ✅ | `PIPELINE_TEMPLATE.md` §0 |

**Слабых мест платформы найдено: 15 (W-1…W-15).** W-1…W-7 — `PHASE1_RESEARCH.md` §6, W-8…W-11 — `ATTRACT_MODULE_RESEARCH.md` §5, W-12/W-13 — шаг 7, W-14 — шаг 10, W-15 — шаг 11. **W-13 → RESOLVED (P2):** канонический AGENTS.md + CLAUDE.md `@AGENTS.md` import + session-overlay restore (`.freebuff_original_agents`). **W-14 → RESOLVED (шаг 10) + рекомендация выполнена (шаг 12):** встроенные промты 071_02_prompt_architect_1_7 (архитектор + идей) применены прогонами `IDEA_EXPLORER_RUN.md` + `PROMT_ARCHITECT_RUN.md`; оба зафиксированы как опциональный pre-flight гейт в `docs_10/templates/PIPELINE_TEMPLATE.md` §0 — W-14 не повторится в следующих задачах. **W-15 → RESOLVED (шаг 11):** не было протокола миграции проекта с сохранением решений (PLATFORM.md:493) — закрыт `docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md` + project-local ADR (`projects_17/lead_aggregator/decisions/`).
