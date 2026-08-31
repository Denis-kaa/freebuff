# 04_ARCHITECTURE — парсер недвижимости + Telegram-бот

## Data Flow

```
systemd/APScheduler (ежедневно + ручной /run)
        │
        ▼
┌─ SOURCE ADAPTERS (по сайту-источнику, изолированные) ─┐
│  discovery URL → пагинация → список URL карточек      │
│  Общая шина: TLSClient(httpx|curl_cffi) +             │
│  ProxyRotator + RetryPolicy(jitter) + rate limit      │
└───────────────┬───────────────────────────────────────┘
                ▼  asyncio.Semaphore(4–8) bounded concurrency
┌─ FETCH → PARSE → NORMALIZE → VALIDATE ────────────────┐
│  area (м²), price (+валюта), rooms, address, type,    │
│  url, external_id; отбраковка неполных записей        │
└───────────────┬───────────────────────────────────────┘
                ▼
┌─ DEDUPLICATOR ────────────────────────────────────────┐
│  natural key: (source, external_id) иначе hash(url)   │
│  new / price_changed / unchanged / disappeared        │
└───────────────┬───────────────────────────────────────┘
                ▼
┌─ DATABASE (upsert) ───────────────────────────────────┐
│  property + property_event (история цены)             │
└───────────────┬───────────────────────────────────────┘
                ▼
┌─ TELEGRAM BOT (управление + отчёт) ───────────────────┐
│  /status /run /stop /stats /errors                    │
└───────────────────────────────────────────────────────┘
```

## Модель данных (минимальная)

```sql
CREATE TABLE property (
  id            BIGSERIAL PRIMARY KEY,
  source        TEXT NOT NULL,          -- 'site_a', 'site_b'
  external_id   TEXT NOT NULL,          -- id в источнике
  url           TEXT NOT NULL,
  title         TEXT,
  price         NUMERIC(12,2),
  currency      TEXT DEFAULT 'UZS',
  area_m2       NUMERIC(8,2),
  rooms         NUMERIC(3,1),
  address       TEXT,
  property_type TEXT,
  raw           JSONB,                  -- остальные характеристики
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, external_id)
);
CREATE UNIQUE INDEX property_url_hash ON property (source, md5(url)); -- fallback-ключ

CREATE TABLE property_event (
  id          BIGSERIAL PRIMARY KEY,
  property_id BIGINT REFERENCES property(id),
  kind        TEXT NOT NULL,            -- 'created' | 'price_changed' | 'removed'
  old_value   JSONB, new_value JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE run_log (
  id BIGSERIAL PRIMARY KEY, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  source TEXT, fetched INT, created INT, updated INT, removed INT, errors INT, status TEXT
);
```

**Дедупликация:** primary — (source, external_id); если у источника нет стабильного id — hash(url); при смене url у того же объекта — нормализация url (убрать utm/трекинг-параметры) перед хешированием. «Исчезновение объекта»: не удаляем, ставим событие `removed` и не обновляем `last_seen_at` N дней.

## Модули

```
real_estate_parser/
├── app/
│   ├── core/        config, tls_client, retry_policy, proxy_rotator, rate_limit
│   ├── sources/     base.py + один адаптер на сайт-источник
│   ├── processors/  normalizer, validator, deduplicator
│   ├── storage/     db.py (asyncpg/psycopg), repository.py
│   ├── bot/         aiogram-бот (управление)
│   └── scheduler.py (APScheduler + run_once/run_forever)
├── docker-compose.yml, Dockerfile
└── tests/
```

## Что переиспользуется из платформы

| Модуль | Откуда |
|---|---|
| TLSClient (httpx + fallback) | lead_aggregator `app/core/tls_client.py` |
| RetryPolicy (backoff+jitter+circuit breaker) | lead_aggregator `app/core/retry_policy.py` |
| Дедуп-подход, CheckpointStore-паттерн | lead_aggregator |
| aiogram-скелет бота | tg_digital_market |
| ScraperProtocol + FakeScraper тест-паттерн | pricing_enumerator |

## Blueprint: где помогает / где избыточен

- **Помогает:** contract-first адаптеры, additive-структура, тест-паттерны, retry/dedup готовые модули — ускоряет ~70%.
- **Избыточно для MVP:** event bus, ModelGateway-скоринг, multi-device sync — не подключаем.
