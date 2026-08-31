# 05_IMPLEMENTATION_PLAN.md — порядок реализации

## Фазы

1. **Каркас** — пакет `real_estate_parser/` с config, tls_client (httpx), retry_policy, proxy_rotator, rate_limit.
2. **Первый источник** — base.py + один адаптер на сайт-источник: discovery URL → пагинация → список URL карточек.
3. **FETCH → PARSE → NORMALIZE → VALIDATE** — area (м²), price (+валюта), rooms, address, type, url, external_id; отбраковка неполных записей.
4. **DEDUPLICATOR** — natural key: (source, external_id), fallback hash(url); события created/price_changed/removed.
5. **БД** — PostgreSQL (asyncpg) + upsert; SQLite-фолбэк для локальной разработки.
6. **Scheduler** — APScheduler: cron-триггер ежедневно + ручной /run из бота; run_log для /stats.
7. **Telegram-бот** — aiogram 3.x: /status /run /stop /stats /errors.
8. **Docker + деплой** — Dockerfile + docker-compose + systemd-инструкция + README.

## Acceptance criteria (по фазам)

1. Каркас: `python -m pytest tests/ -q` → зелёные hermetic-тесты без сети.
2. Источник: live-проверка curl/адаптера — карточки извлекаются.
3. Нормализация: price/area/rooms парсятся из fixture-HTML всех форматов источника.
4. Дедуп: повторный прогон не создаёт дублей; смена цены → событие price_changed.
5. БД: upsert идемпотентен; restart не теряет state (run_log + property).
6. Scheduler: ручной /run из бота запускает прогон; cron срабатывает по расписанию.
7. Бот: /status /run /stop /stats /errors отвечают.
8. Деплой: docker-compose up поднимает всё; README воспроизводит с нуля.

## Порядок работ

Каркас → источник (live-проверка) → парсер+нормализация → дедуп+БД → scheduler → бот → Docker/деплой → финальные отчёты (12–14).
