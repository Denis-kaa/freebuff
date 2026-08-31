# 02_PROJECT_EXPERIENCE_MAP — что уже умею и что переиспользую

Evidence-based: только то, что реально подтверждается кодом в репозитории.

## Подтверждённые навыки (SKILL → PROJECT → FILE → CONFIDENCE)

| SKILL | PROJECT | FILE | Реализация | Confidence |
|---|---|---|---|---|
| Async HTTP client | lead_aggregator | `projects_17/lead_aggregator/app/core/tls_client.py` | `httpx.AsyncClient` + optional proxy + impersonation-абстракция | HIGH |
| Парсинг HTML (SSR) | pricing_enumerator | `scripts_01/pricing_enumerator.py` (WebScraper: httpx + bs4, schema.org → CSS fallback) | fetch+parse+status mapping | HIGH |
| Скрапер-контракт + hermetic-тесты | pricing_enumerator | `ScraperProtocol` + `FakeScraper` (DI, без сети) | паттерн переиспользуется напрямую | HIGH |
| Retry/backoff/jitter + circuit breaker | lead_aggregator | `app/core/retry_policy.py` | готовый модуль | HIGH |
| Дедупликация | lead_aggregator | `app/processors/deduplicator.py` (exact+normalize+fuzzy) | переиспользуемая логика | HIGH |
| Checkpoint/resume (SQLite+WAL) | lead_aggregator | `app/storage/checkpoint_store.py` | атомарные чекпоинты по источнику | HIGH |
| Scheduler-пайплайн (run_once/run_forever, graceful shutdown) | lead_aggregator | `app/pipeline.py`, `app/cli.py` | каркас для ежедневного прогона | HIGH |
| Telegram delivery (HTML, экранирование) | lead_aggregator | `app/delivery/telegram.py` (httpx) | уведомления | HIGH |
| Telegram-бот (aiogram 3.x) | tg_digital_market | `projects_17/tg_digital_market/src/market_bot/bot/aiogram_channel.py` | скелет бота с командами | MEDIUM-HIGH |
| Прокси-интерфейс (ротация) | lead_aggregator | `ProxyRotator` (stub v1, ADR-003) | интерфейс есть, реализация — новая | MEDIUM |
| SPA-детекция (честная диагностика) | lead_aggregator | `_looks_like_spa_shell()` | W-16-урок: Kwork стал SPA | HIGH |
| Модельный скоринг (LLM) | platform | `scripts_01/model_gateway.py` | не требуется для этой вакансии | — |

## Частичные навыки (есть, но требуют доработки)

| Навык | Что есть | Чего не хватает |
|---|---|---|
| Прокси-ротация | stub-интерфейс + proxy-параметр в TLSClient | реализация rotator с health-check, sticky-сессии |
| PostgreSQL | паттерн SQLite+WAL; контракт под PG | реальный asyncpg/psycopg-слой в этой среде |
| Headless-браузер | нет (playwright не ставится на Termux/ARM64, W-2) | если источник SPA — Lightpanda/curl_cffi на сервере |
| TLS-impersonation | абстракция + fallback | curl_cffi не установлен (W-2) |

## GAPS (в репозитории практически нет)

- Парсеры недвижимости как таковые (структура карточек, price/area/rooms нормализация под RU/междунар. форматы).
- Price-history tracking (last_seen_at, изменение цены) — паттерн есть в pricing_enumerator (WORM JSONL), но не для объектов.
- systemd-timer юниты для парсера (есть systemd-опыт из ai-dubber деплоя — вне этого репозитория).

## Вывод

~70–80% задачи покрывается существующим кодом: HTTP-слой, retry, дедуп, чекпоинты, пайплайн, TG-доставка, aiogram-скелет, тестовые паттерны. Новое: парсеры конкретных источников, ProxyRotator-реализация, схема объектов недвижимости, деплой-конфиг.
