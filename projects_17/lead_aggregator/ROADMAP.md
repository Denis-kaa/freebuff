# ROADMAP-LA-001 — Lead Aggregator + Attract-модуль (промт 69 × 70)

> Источник: `pompts_11/070_07_lead_aggregator_scraper.md` (Lead Aggregator) + `pompts_11/071_02_prompt_architect_1_7.md` (PIPELINE_TEMPLATE) · 2026-08-10
> Шаблон: [`docs_10/templates/PIPELINE_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PIPELINE_TEMPLATE.md)
> Журнал: [`steps.md`***REMOVED***(../../steps.md) (session-level) · Project-local: [`STEPS.md`***REMOVED***(STEPS.md) + [`LESSONS.md`***REMOVED***(LESSONS.md)

## 0. Explain-first (порядок и почему)

1. **Фаза 1 (research)** уже выполнена — `PHASE1_RESEARCH.md` + `ATTRACT_MODULE_RESEARCH.md` (пользователь дал добро на продолжение).
2. Сейчас — **Фаза 2 (архитектура)** по промту 69. Порядок: сначала архитектура как документ (`PHASE2_ARCHITECTURE.md`), затем — по ревью пользователя — Фаза 3 (код).
3. Причина порядка: промт 69 жёстко запрещает код до утверждения Фаз 1–2; промт 70 требует explain-first и atomic-шаги с acceptance criteria.
4. Ограничение среды: Python 3.14.6 / Termux / SQLite-only. Стек промта 69 (curl_cffi, playwright, PG, Redis) частично отсутствует → архитектура проектируется с учётом W-2/W-4/W-5 (из PHASE1_RESEARCH.md §6).

## 📊 Прогресс Roll-up (живая таблица)

| Этап | Статус |
|------|--------|
| Фаза 1: research (площадки + Attract) | ✅ выполнено (PHASE1 + ATTRACT) |
| Шаблон пайплайна (промт 70 Задача 2) | ✅ `docs_10/templates/PIPELINE_TEMPLATE.md` |
| Применение шаблона к LA (этот ROADMAP + STEPS + LESSONS) | ✅ создано |
| Фаза 2: PHASE2_ARCHITECTURE.md | ✅ создан, одобрен (Kwork первым, топ-3 компетенции, юр. гейт принят) |
| Фаза 3: код | ✅ выполнено (26 тестов зелёные) |
| Фаза 4: Deploy — CLI + dry-run + боевой запуск | ✅ CLI (`app/cli.py`) + settings.env + dry-run (TG: 2 блока, 0 целевых — сервисные сообщения канала) + once-запуск; **W-16**: Kwork стал SPA (нужен headless) — честная диагностика |
| Task 4: pre-flight гейт (W-14) — IDEA EXPLORER на W-16 | ✅ `IDEA_EXPLORER_RUN_KWORK_SPA.md` (7 веток → score → prune → depth-2 → cross-pollination → reframe → 3 кандидата); вывод: TG-зеркала Kwork (B2/A) — первый шаг (0 зависимостей), Lightpanda (B1/B) — опциональный upgrade (ADR-007), Playwright отклонён |

## 📌 1. Границы (что НЕ делается — explicit scope-exclusion)

- ✅ Код Фазы 3 написан по утверждённой Фазе 2 (Kwork + TG первыми).
- НЕ трогаем существующие модули платформы (`core_02/`, `scripts_01/`) — архитектура аддитивная (соблюдено: только новый пакет `projects_17/lead_aggregator/`).
- НЕ устанавливаем новые зависимости — `TLSClient` работает на httpx (уже в среде), curl_cffi/playwright остаются optional (W-2).
- НЕ реализуем Blueprint v3 → Forge Facade (промт 70, Миссия 2) — отдельный трек P3.

## 📌 2. Capability-check (CON-40)

| Требование промта 69 | Статус в среде | Решение в архитектуре |
|----------------------|----------------|------------------------|
| async (asyncio/httpx/aiohttp) | ✅ есть (aiohttp, httpx) | Используем `httpx.AsyncClient` |
| Telegram User API (Telethon) | ✅ есть | Переиспользуем `core_02/_tg_client_v2.py` паттерн |
| L3-классификатор (LLM) | ✅ ModelGateway | Reuse `scripts_01/model_gateway.py` |
| TLS-impersonation (curl_cffi) | ❌ нет | Абстракция `TLSClient` с fallback на httpx; curl_cffi — optional install (W-2) |
| PostgreSQL / Redis | ❌ SQLite-only | Абстракция `CheckpointStore` (SQLite v1, PG/REDIS — контракт) |
| Прокси (socks) | ❌ нет | Интерфейс `ProxyRotator` (stub v1, реализация после выбора провайдера) |

## 📌 3. Sequential-порядок и явные зависимости (gates)

```
Task 0 (шаблон+project-local)  → gate: ROADMAP/STEPS/LESSONS существуют
        ↓
Task 1 (PHASE2_ARCHITECTURE.md) → gate: пользователь утвердил Фазу 2
        ↓
Task 2 (Фаза 3 код, ПОСЛЕ ревью) → gate: архитектура одобрена
```

**Gate 1 → Task 2:** без утверждения Фазы 2 код не пишется (промт 69).

## 📌 4. Карта файлов (artifact placement)

| Файл | Назначение |
|------|-----------|
| `docs_10/templates/PIPELINE_TEMPLATE.md` | Шаблон пайплайна (промт 70) |
| `projects_17/lead_aggregator/ROADMAP.md` | Этот документ (оркестрация) |
| `projects_17/lead_aggregator/STEPS.md` | Живой project-local чек-лист |
| `projects_17/lead_aggregator/LESSONS.md` | Узкие находки при работе |
| `projects_17/lead_aggregator/PHASE1_RESEARCH.md` | Фаза 1 (выполнено) |
| `projects_17/lead_aggregator/ATTRACT_MODULE_RESEARCH.md` | Attract-исследование (выполнено) |
| `projects_17/lead_aggregator/PHASE2_ARCHITECTURE.md` | Фаза 2 — целевой артефакт этого этапа |

## 📌 5. Детальные atomic-шаги (с точными acceptance criteria)

### Task 0 — Шаблон + project-local конвенция (ВЫПОЛНЕНО)
- [x***REMOVED*** `docs_10/templates/PIPELINE_TEMPLATE.md` создан из 3 precedents.
- [x***REMOVED*** `STEPS.md` + `LESSONS.md` + этот `ROADMAP.md` созданы.
- **Acceptance:** файлы существуют; структура секций совпадает с шаблоном (grep по `^## `).

### Task 1 — PHASE2_ARCHITECTURE.md (✅ СОЗДАН, ОДОБРЕН)
- [x***REMOVED*** Data Flow диаграмма (источники → адаптеры → LDE → дедуп → delivery).
- [x***REMOVED*** Модульная структура (core/adapters/processors/storage/delivery/utils).
- [x***REMOVED*** Абстракции: TLSClient, ProxyRotator, CheckpointStore, CaptchaSolver (интерфейсы).
- [x***REMOVED*** Привязка к платформе: ModelGateway, telethon, notification, EventBus.
- [x***REMOVED*** **Acceptance:** документ содержит все 5 пунктов + раздел «библиотеки и их обоснование».

### Task 2 — Фаза 3 (код) — ВЫПОЛНЕНО (26 тестов ✅)
- [x***REMOVED*** Скелет проекта `app/core|adapters|processors|storage|delivery`.
- [x***REMOVED*** `RetryPolicy` (backoff+jitter+circuit breaker c cooldown-восстановлением, `clone()` для per-adapter изоляции).
- [x***REMOVED*** `CheckpointStore` (SQLite+WAL), `IntentClassifier` (L1/L2), `Deduplicator` (exact+normalize+fuzzy), `Scorer` (L3 + ModelGateway-fallback, prompt-injection guard).
- [x***REMOVED*** Адаптеры: `KworkAdapter` (feed), `TGChannelAdapter` (t.me/s preview), флаг `ordered` (resume только для упорядоченных фидов).
- [x***REMOVED*** `TelegramDelivery` (HTML-экранирование), `LeadPipeline` (`run_once` + `run_forever` с graceful shutdown).
- [x***REMOVED*** Конфиги: `keywords.yaml`, `competence_profile.yaml`, `settings.env.example`.
- [x***REMOVED*** Тесты: `tests_09/test_lead_aggregator_core.py` + `test_lead_aggregator_adapters.py`.
- **Acceptance:** `python -m pytest tests_09/test_lead_aggregator_core.py tests_09/test_lead_aggregator_adapters.py -q` → **26 passed** (проверено).

### Task 3 — Фаза 4 (Deploy) — ВЫПОЛНЕНО (40 тестов ✅)
- [x***REMOVED*** `app/cli.py` — CLI: `--dry-run` (реальные источники, temp-чекпоинты, без доставки), `--once` (боевой), `--forever` (24/7), `--sources kwork,tg`, `--json`, `--interval`.
- [x***REMOVED*** `app/core/config.py` — загрузка `settings.env` (module-level, до дефолтов Config) + все env-поля через `default_factory` (LA_* читаются при инстанцировании).
- [x***REMOVED*** `settings.env` — создан из example (LA_TG_* пустые → доставка логируется, не отправляется).
- [x***REMOVED*** **Live-верификация (W-16):** dry-run на реальных источниках показал 0 лидов → диагностика:
  - `TGChannelAdapter` — regex `tgme_widget_message(?:\s[^"***REMOVED****)?` (живой класс содержит доп. токены: `text_not_supported_wrap service_message js-widget_message`); lookahead не цепляет внутренние div'ы (`_user/_text/_wrap`). Live: **2 блока** из t.me/s/freelance_tg (сервисные сообщения канала, 0 целевых лидов).
  - `KworkAdapter` — kwork.ru/projects стал **SPA** (статичный HTML = скелет с прелоадерами `js-wants-list-preloaders`/`wants-content`, все JSON-эндпоинты 404) → `_looks_like_spa_shell()` честно возвращает [***REMOVED*** + warning (W-16, нужен headless-браузер — W-2).
- [x***REMOVED*** Тесты: `test_lead_aggregator_cli.py` (12: parser, _parse_sources, _select_adapters, _CaptureDelivery, env-файл, пропагация env→Config) + регрессии адаптеров (live-классы TG, SPA-детектор Kwork).
- [x***REMOVED*** Боевой `--once`: fetched=2 (TG, сервисные сообщения → 0 целевых), errors=0, чекпоинт `data/checkpoints.db` записан, доставка логируется (LA_TG_* не заданы).
- **Acceptance:** `python -m pytest tests_09/test_lead_aggregator_core.py tests_09/test_lead_aggregator_adapters.py tests_09/test_lead_aggregator_cli.py -q` → **40 passed** (проверено); `python -m app.cli --dry-run` → реальные лиды из TG.

### Task 4 — Pre-flight гейт (W-14): IDEA EXPLORER v2.0 на W-16 (✅ ВЫПОЛНЕНО)
- [x***REMOVED*** Применён встроенный промт **IDEA EXPLORER v2.0** (PIPELINE_TEMPLATE Приложение B) к задаче с развилками — W-16 (Kwork SPA).
- [x***REMOVED*** `IDEA_EXPLORER_RUN_KWORK_SPA.md` — по эталону (7 веток: headless/Lightpanda, TG-зеркала, Playwright, curl_cffi, гибрид, без Kwork, mobile API) → BRANCH SCORE → STATUS (DEEPEN B1/B5, DROP B3) → DEPTH-2 (B1, B5) → CROSS-POLLINATION (B1+B2=B5 EMERGENT) → REFRAME (рендер → доступ) → 3 кандидата (A TG-зеркала, B гибрид, C Kwork-as-a-Service).
- [x***REMOVED*** **Критическая развилка:** покрывают ли TG-зеркала нужные разделы Kwork? → Решение: эксперимент A первым (live-проверка зеркал, 15 мин, 0 зависимостей); Lightpanda (B) — следующий шаг.
- **Acceptance:** run-артефакт существует (18+ секций, handoff §18 заполнен), маркеры `IDEA EXPLORER v2.0` + `W-16` присутствуют; результат импортирован в Risk register (§6) и открытые вопросы (§8).

## 📌 6. Risk register

| Риск | Митигация |
|------|-----------|
| Установка curl_cffi на Python 3.14.6/ARM64 | Архитектурная абстракция TLSClient + fallback на httpx |
| Юридический (W-7): ToS/152-ФЗ/GDPR | Policy-гейт в конфиге адаптеров (обсуждается с пользователем) |
| Ревью Фазы 2 затягивается | Отчёт структурирован; открытые вопросы сформулированы |
| Объём архитектуры | Ограничен границами §1; P3 (Blueprint Facade) не смешиваем |
| **Kwork стал SPA (W-16, live-verify)** | Честная диагностика `_looks_like_spa_shell()` + warning; путь вперёд — headless (playwright/curl_cffi, W-2) или поиск публичного API; TG-каналы уже дают лиды |
| **W-16 fork (Task 4, IDEA EXPLORER):** headless vs TG-зеркала | **TG-зеркала Kwork первым** (B2/A: 0 зависимостей, деплой сегодня) → live-проверка (acceptance: fetched>0); при пустоте — Lightpanda (B1/B, ADR-007); Playwright (B3) отклонён (W-2, ARM64) |

## 📌 7. Acceptance Summary (финальный чек-лист перед commit)

- [x***REMOVED*** ROADMAP/STEPS/LESSONS соответствуют PIPELINE_TEMPLATE.
- [x***REMOVED*** PHASE2_ARCHITECTURE.md покрывает Data Flow, модули, абстракции, библиотеки.
- [x***REMOVED*** Ни один модуль платформы не изменён (additive).
- [x***REMOVED*** Код Фазы 3 написан и покрыт тестами (26 passed).
- [x***REMOVED*** Открытые вопросы Фазы 2 закрыты (Kwork, топ-3, юр. гейт).
- [ ***REMOVED*** Финальное ревью пользователя кода Фазы 3 (не блокирует, ожидается).

## 📌 8. Открытые вопросы к пользователю

- ✅ ~~**Q-ROADMAP-1 — Первый источник для реализации: Kwork-парсер или TG-агрегатор?**~~ Решено (roadmap): Kwork первым (рекомендация PHASE2 §8). [closed***REMOVED***
- ✅ ~~**Q-ROADMAP-2 — Компетенции для старта: все или топ-3?**~~ Решено: топ-3 (AI-автоматизация, TG-боты, лендинги) — `competence_profile.yaml`. [closed***REMOVED***
- ✅ ~~**Q-ROADMAP-3 — Юр. периметр: исключаем спам-запросы?**~~ Решено: спам-зоны исключены (L1 policy-гейт, stopwords казино/реклама/накрутка). [closed***REMOVED***
- ✅ ~~**Q-ROADMAP-4 — Реальный запуск: настроить `TG_BOT_TOKEN`/`TG_CHAT_ID` + источники в `settings.env`?**~~ Фаза 4 выполнена: CLI работает, dry-run + once запущены; для реальной доставки лидов заполни `LA_TG_BOT_TOKEN`/`LA_TG_CHAT_ID` в `settings.env`. [closed***REMOVED***
- ✅ ~~**Q-ROADMAP-5 — Как получать заказы Kwork, если лента стала SPA?**~~ IDEA EXPLORER (Task 4): TG-зеркала Kwork первым (`@kwork_parsing` и аналоги в `LA_TG_CHANNELS`), live-проверка; Lightpanda — опциональный headless-fallback (ADR-007). [closed***REMOVED***   

## 🔗 Cross-links

- [`docs_10/templates/PIPELINE_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PIPELINE_TEMPLATE.md)
- [`PHASE1_RESEARCH.md`***REMOVED***(PHASE1_RESEARCH.md) · [`ATTRACT_MODULE_RESEARCH.md`***REMOVED***(ATTRACT_MODULE_RESEARCH.md)
- [`pompts_11/070_07_lead_aggregator_scraper.md`***REMOVED***(../../pompts_11/070_07_lead_aggregator_scraper.md) · [`pompts_11/071_02_prompt_architect_1_7.md`***REMOVED***(../../pompts_11/071_02_prompt_architect_1_7.md)
