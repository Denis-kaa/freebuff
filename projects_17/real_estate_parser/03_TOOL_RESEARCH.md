# 03_TOOL_RESEARCH — стек для парсера недвижимости (2026)

## HTTP-клиент

| Инструмент | Вывод |
|---|---|
| **httpx** | Основной выбор: async, HTTP/2, поддержка прокси, retries. Уже есть в среде (0.27.2 pinned). |
| **curl_cffi** | Нужен только если источник за Cloudflare/TLS-fingerprint-блоком. Абстракция `TLSClient` с fallback — как в lead_aggregator (ADR-003). |
| aiohttp | Запасная, не нужна. |
| requests | Нет async — отброшено. |

Вывод из сравнения клиентов (2026): «requests — для простых скриптов, httpx — sync+async один клиент, curl_cffi — когда 403 не лечится заголовками». Наш случай: httpx основной, curl_cffi optional.

## Парсинг

- **BeautifulSoup4 + lxml** — для SSR-страниц (карточки объектов). Есть в среде.
- **Playwright** — только если источник SPA. На Termux/ARM64 не ставится (W-2); на сервере деплоя — ок, но добавляет ~400MB. Решение: НЕ подключать до подтверждения, что источник требует JS (урок W-16: Kwork стал SPA — сначала live-проверка источника, потом выбор).
- **Выбор источников:** приоритет порталам с SSR или публичным API. Живой тест каждого кандидата до написания парсера (curl → есть ли данные в HTML).

## Concurrency

- **asyncio + `httpx.AsyncClient` + `asyncio.Semaphore(4–8)`** — I/O-bound задача, threads не нужны. Per-host rate limit (токен-бакет или min-interval) + `RetryPolicy` с jitter + circuit breaker (готов в lead_aggregator).

## Scheduler

| Вариант | Вердикт |
|---|---|
| **APScheduler (в процессе с ботом)** | ✅ выбор: cron-триггер ежедневно + ручной /run из бота в одном процессе |
| systemd timer | запасной вариант, если бот отдельным процессом |
| Celery/RQ/Redis | избыточно для ежедневного прогона одного пайплайна |

## Telegram-бот

- **aiogram 3.x** — готовый скелет в `projects_17/tg_digital_market/src/market_bot/bot/aiogram_channel.py`. Команды MVP: /status, /run, /stop, /stats, /errors.

## БД

- **PostgreSQL** (целевая, в вакансии «БД» на сервере) через asyncpg/psycopg; **SQLite+WAL** как v1-фолбэк — паттерн `CheckpointStore` готов. Модель: таблица `property` + upsert по natural key.

## Прокси

- Ротация round-robin по списку из конфига + health-check + cooldown при 403/429. Провайдера выбирает человек (C-категория): residential при гео-блоках, datacenter если достаточно. Реализация провайдер-агностична (URL-список в env).
