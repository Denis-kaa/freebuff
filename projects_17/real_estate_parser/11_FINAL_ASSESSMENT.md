# 11_FINAL_ASSESSMENT — финальная оценка по вопросам промта

## 1. Насколько вакансия соответствует моему опыту?

**~85%.** Ядро задачи (async-парсер + БД + бот + деплой) — прямое продолжение уже реализованных модулей платформы (lead_aggregator, pricing_enumerator, tg_digital_market). Специфика — только домен недвижимости (структура карточек, нормализация площадей/цен/комнат).

## 2. Какие 70–90% задачи уже покрываются существующими знаниями/проектами?

- HTTP-слой (httpx + прокси + TLS-абстракция) — `tls_client.py` ✅
- Retry/backoff/circuit breaker — `retry_policy.py` ✅
- Дедупликация + checkpoint/resume — `deduplicator.py`, `checkpoint_store.py` ✅
- Пайплайн (run_once/run_forever, graceful shutdown) — `pipeline.py` ✅
- Telegram delivery + aiogram-скелет — `telegram.py`, `aiogram_channel.py` ✅
- Hermetic-тесты (ScraperProtocol/FakeScraper) — `test_pricing_enumerator.py` ✅

## 3. Какие части для меня новые?

- Парсеры конкретных порталов недвижимости (нормализация площадей/цен/комнат, пагинация листингов).
- ProxyRotator-реализация (health-check, sticky) — интерфейс есть, реализации нет.
- PostgreSQL-слой (asyncpg) в этой среде — только паттерн SQLite.
- Price-history события (created/price_changed/removed) — паттерн есть в pricing_enumerator (WORM), но не для объектов.

## 4. Что агент может выполнить самостоятельно?

Исследование, архитектуру, весь код (адаптеры, парсер, дедуп, БД, scheduler, бот), hermetic-тесты, Docker, локальный деплой, документацию — **100%**.

## 5. Что обязательно должен сделать я (человек)?

- Выбрать и утвердить сайты-источники (ToS/юр. гейт).
- Купить прокси (провайдер + оплата), прислать URL/ключ.
- Выдать TG bot token, SSH-доступ к серверу, строку подключения к БД.
- Подтвердить установку curl_cffi на сервере деплоя (если понадобится).

## 6. Сколько моего времени реально потребуется?

**~1–2 часа:** утвердить источники, зарегистрировать бота у BotFather, оплатить прокси, выдать SSH-доступ.

## 7. Какие технические риски?

Anti-bot/Cloudflare на источниках (митигируется выбором SSR/API-источников + curl_cffi на сервере), смена HTML-структуры (валидатор + алерты), rate limits (bounded concurrency + retry), юр. ToS-гейт (парсинг только публичных карточек).

## 8. Какой минимальный MVP?

Один SSR-источник → парсер карточек (area/price/rooms/url/external_id) → дедуп → PostgreSQL upsert → APScheduler (ежедневно) → aiogram-бот (/status /run /stats /errors) → docker-compose. Без прокси-ротации и price-history на первом шаге (добавляются конфигом и одной таблицей).

## 9. Какой стек оптимален?

httpx (async) + bs4 + APScheduler + aiogram 3.x + PostgreSQL (asyncpg; SQLite для локальных тестов) + Docker Compose. curl_cffi — optional на сервере, если источник за TLS-блоком.

## 10. Можно ли использовать существующий код?

Да — до ~75%: TLSClient, RetryPolicy, дедуп/чекпоинт-паттерны, пайплайн, aiogram-скелет, тестовые паттерны (ScraperProtocol/FakeScraper).

## 11. Что лучше взять из моих проектов?

- `lead_aggregator/app/core/tls_client.py`, `retry_policy.py` — транспорт и надёжность.
- `lead_aggregator/app/pipeline.py` — каркас прогона.
- `tg_digital_market/.../aiogram_channel.py` — скелет бота.
- `pricing_enumerator.py` — ScraperProtocol/FakeScraper и status-mapping.

## 12. Где Blueprint помогает?

Contract-first адаптеры, additive-структура, готовые retry/dedup-модули, hermetic-тест-паттерны — ускоряет ~70%.

## 13. Где Blueprint избыточен?

Event bus, ModelGateway-скоринг, multi-device sync, ToolRegistry-обёртки для простых HTTP-вызовов — не нужны для MVP.

## 14. Что агент реально смог выполнить?

Весь анализ (01–11), выбор стека, архитектуру с моделью данных и стратегией дедупа, план реализации с acceptance criteria.

## 15. Что агент НЕ смог выполнить?

Реализацию против живого источника (источники не выбраны/не утверждены — C-категория), деплой на реальный сервер (нет SSH-доступа), покупку прокси и выдачу секретов.

## 16. Почему?

Эти шаги по определению требуют человека (оплата, секреты, юр. утверждение источников) — категория C/D из AUTONOMY_MAP.

## 17. Что нужно от человека для завершения?

1. Утвердить список сайтов-источников.
2. Прислать TG bot token.
3. Оплатить прокси, прислать URL/ключ.
4. Выдать SSH-доступ к серверу и строку подключения к БД.
