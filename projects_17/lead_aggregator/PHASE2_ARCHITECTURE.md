# PHASE 2 — ARCHITECTURE & BYPASS LAYER (Attract-модуль)

**Промт:** `pompts_11/070_07_lead_aggregator_scraper.md` Фаза 2 · **Шаблон:** [`docs_10/templates/PIPELINE_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PIPELINE_TEMPLATE.md)
**Статус:** 📐 ГОТОВО к ревью (Фаза 3 — код — по промту 69 только после утверждения)
**Наследует:** `PHASE1_RESEARCH.md` §2–§6 + `ATTRACT_MODULE_RESEARCH.md` §2–§6
**Ограничения среды:** Python 3.14.6 / Termux / SQLite-only; curl_cffi, playwright, asyncpg, redis, socks отсутствуют (W-2/W-4/W-5)

---

## 1. Архитектурная схема Data Flow

```
[Запрос пользователя: «разработка телеграм ботов»***REMOVED***
        │
        ▼
┌─ SIGNATURE GENERATOR ──────────────────────────────┐
│  competence_profile.yaml (W-8) → сигнатуры запросов│
│  «бот», «телеграм», «python», «парсер» …           │
└───────────────┬────────────────────────────────────┘
                ▼
┌─ SOURCE ADAPTERS (изолированные, Adapter Pattern) ─┐
│  ├─ KworkAdapter        (лента заказов)            │
│  ├─ TGChannelAdapter    (@freelance_tg, @proger…)  │
│  ├─ VacancyAdapter      (@job_python, hh-proekt)   │
│  └─ OutreachAdapter     (2ГИС — опционально)       │
│  Общая шина: TLSClient(impersonate|fallback) +     │
│  ProxyRotator + RetryPolicy(jitter) + CaptchaSolver│
└───────────────┬────────────────────────────────────┘
                ▼
┌─ NORMALIZER → DEDUPLICATOR (hash + simhash) ───────┐
└───────────────┬────────────────────────────────────┘
                ▼
┌─ LEAD DETECTION ENGINE (переиспользуемый из Фазы 1)┐
│  L1 regex/stop-words → L2 intent (клиент ищет      │
│  исполнителя) → L3 ModelGateway score 0–100        │
│  + скоринг под competence_profile (релевантность)  │
└───────────────┬────────────────────────────────────┘
                ▼
┌─ CHECKPOINT STORE (SQLite v1, контракт PG/Redis) ──┐
│  last_processed_id / timestamp (resume после рестарта│
└───────────────┬────────────────────────────────────┘
                ▼
┌─ DELIVERY ENGINE (notification.py + TG Bot) ───────┐
│  «Найден клиент: <текст> | источник | score»        │
└─────────────────────────────────────────────────────┘
```

## 2. Модульная структура (вход в Фазу 3)

```text
lead_aggregator/
├── app/
│   ├── core/          # AsyncEngine, Config, ProxyManager, CaptchaSolver, RetryPolicy
│   ├── adapters/      # KworkAdapter, TGChannelAdapter, VacancyAdapter, (OutreachAdapter)
│   ├── processors/    # Normalizer, Deduplicator, IntentClassifier(L1/L2), Scorer(L3)
│   ├── storage/       # CheckpointStore(SQLite), Schema, models
│   ├── delivery/      # TelegramBot (notification.py reuse), WebhookPublisher
│   └── utils/         # User-Agents, TLS profiles, stealth helpers
├── config/            # keywords.yaml, competence_profile.yaml, settings.env
├── tests/             # (позже переносится в tests_09/)
└── docker-compose.yml # опционально (вне Termux)
```

## 3. Ключевые абстракции (интерфейсы, не реализации)

| Абстракция | Ответственность | Реализация v1 | Примечание (W-код) |
|-----------|-----------------|---------------|---------------------|
| **`TLSClient`** | HTTP-запросы с опцией impersonation | `httpx.AsyncClient`; опционально `curl_cffi` если установится | W-2/W-4: fallback обязателен |
| **`ProxyRotator`** | ротация/health-check прокси, sticky | stub-интерфейс v1 (без сети) | нужен выбор провайдера (вопрос OQ-LA) |
| **`RetryPolicy`** | exponential backoff + jitter, circuit breaker | свой модуль (аналог `notification.py` RETRY) | переиспользуем паттерн платформы |
| **`CaptchaSolver`** | Turnstile/reCAPTCHA (CapMonster/2Captcha) | интерфейс, integration deferred | Фаза 3 резервный вектор |
| **`CheckpointStore`** | last_processed_id/timestamp, атомарность | SQLite + WAL (паттерн workspace_registry) | контракт под PG/Redis позже |
| **`LeadDetector`** | L1+L2+L3 цепочка | rules + ModelGateway | reuse Фазы 1 дизайна |

## 4. Привязка к платформе (переиспользование)

| Платформенный модуль | Использование |
|----------------------|---------------|
| `scripts_01/model_gateway.py` | L3-скоринг (Ollama локально / DeepSeek-Gemini fallback) — **уже есть** |
| `core_02/_tg_client_v2.py` + telethon | Telegram-адаптер (User API паттерн, FLOOD_WAIT) |
| `scripts_01/notification.py` | Delivery: TG-уведомления о лидах |
| `scripts_01/event_bus.py` | события `lead.found`, `adapter.error`, `checkpoint.updated` |
| `core_02/workspace_registry.py` | SQLite+WAL паттерн для CheckpointStore |
| `core_02/remote_sync.py` | (опция) синхронизация найденных лидов между устройствами |

## 5. Обоснование выбора библиотек

| Библиотека | Зачем | Статус в среде | Решение |
|-----------|-------|----------------|---------|
| `httpx` | async HTTP, retries, proxy support | ✅ есть | основная |
| `aiohttp` | альтернативный async-клиент | ✅ есть | запасная |
| `telethon` | Telegram User API | ✅ есть | для приватных источников |
| `python-telegram-bot` | Delivery Bot | ✅ есть | доставка |
| `beautifulsoup4` | DOM-парсинг t.me/s/, Kwork | ✅ есть | парсинг |
| `curl_cffi` | TLS/JA3 impersonation (биржи под Cloudflare) | ❌ нет | **optional**: абстракция + fallback |
| `pydantic` | валидация лидов/конфигов | ✅ есть (через fastapi) | модели |
| `PyYAML` | keywords.yaml / competence_profile | ✅ есть | конфиги |
| `asyncpg` / `redis` | PG / Redis | ❌ нет | НЕ нужны в v1 (SQLite) |
| `playwright` | headless stealth | ❌ нет | НЕ нужен в v1 (только если биржа без API) |

## 6. Слабые места платформы, закрываемые этой архитектурой

- **W-2/W-4** → абстракция `TLSClient` + optional `curl_cffi` (не блокирует v1).
- **W-3** → `CheckpointStore` с SQLite v1 и контрактом под PG/Redis (дешёвый старт).
- **W-5** → `httpx.AsyncClient` уже async; ToolRegistry не трогаем (additive).
- **W-8** → `competence_profile.yaml` (seed из ATTRACT_MODULE_RESEARCH §2).
- **W-10** → Source Adapters (первый: Kwork или TG-агрегатор — вопрос OQ-LA-1).
- **W-11** → LeadDetector c query-driven сигнатурами из профиля компетенций.
- **W-7** → policy-гейт в конфиге адаптеров (юридический, обсудить с пользователем).

## 7. Что НЕ делается (границы Фазы 2)

- НЕ код (Фаза 3 — после ревью).
- НЕ установка зависимостей сейчас.
- НЕ реализация ProxyRotator/CaptchaSolver (только интерфейсы — нужны внешние решения: провайдер прокси, captcha-сервис).
- НЕ модификация существующих модулей платформы.

## 8. Открытые вопросы (на ревью)

> **Snapshot (PHASE 2 draft, на ревью):** Q1-Q3 этих вопросов closed позже, см. [`ROADMAP.md` §8***REMOVED***(../ROADMAP.md#открытые-вопросы-к-пользователю) (Q-ROADMAP-1/2/3 + Q-ROADMAP-4/5). Q4 (Прокси) — отдельный вопрос, в ROADMAP §8 closed не отражён (proxy-решение архитектурно → готовность adopting curl_cffi / альтернатив).

- ✅ **Q-PHASE2-1 — Первый адаптер:** Kwork-парсер или TG-агрегатор (OQ-LA-1)? Рекомендация: Kwork — прямые заказы, проще парсинг; TG-агрегатор — второй. [closed per ROADMAP §8 Q-ROADMAP-1***REMOVED***
- ✅ **Q-PHASE2-2 — Компетенции:** весь стек из §2 ATTRACT или топ-3 (AI-автоматизация, TG-боты, лендинги)? [closed per ROADMAP §8 Q-ROADMAP-2***REMOVED***
- ✅ **Q-PHASE2-3 — Юр. периметр (W-7):** исключаем спам-запросы? (пример — `/ВАКАНСИИ/5.md`). [closed per ROADMAP §8 Q-ROADMAP-3***REMOVED***
- ⏳ **Q-PHASE2-4 — Прокси:** нужны ли в v1 (Kwork без анти-бота на простом GET?) или достаточно лимитов + jitter? [открыт; архитектурно delegated в `TLSClient` abstract layer (W-2) + headline recommendation "достаточно лимитов+jitter" для v1***REMOVED*** 
