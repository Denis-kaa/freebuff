# 12_IMPLEMENTATION_REPORT — реализация скелета (v1)

**Дата:** 2026-08-31 · **Путь:** `projects_17/real_estate_parser/`

## Статус: IMPLEMENTED + TESTED (hermetic) — против живого источника не проверялось

Скелет реализован по `04_ARCHITECTURE.md`. Конкретные адаптеры источников
добавляются аддитивно после утверждения списка сайтов (см. AUTONOMY_MAP §C/D).

## Дерево

```
projects_17/real_estate_parser/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py          # настройки из env (REP_*)
│   │   ├── tls_client.py      # httpx.AsyncClient + optional curl_cffi
│   │   ├── retry_policy.py    # backoff + jitter + circuit breaker
│   │   ├── proxy_rotator.py   # round-robin + cooldown по 403/429
│   │   └── rate_limit.py      # per-host min interval
│   ├── sources/
│   │   ├── base.py            # контракт SourceAdapter + Listing
│   │   └── example.py         # SSR-шаблон адаптера + парсеры price/area/rooms
│   ├── storage/
│   │   ├── models.py          # property + property_event + run_log
│   │   ├── repository.py      # идемпотентный upsert + события
│   │   └── db.py              # engine/session factory + migrate
│   ├── bot/
│   │   ├── __init__.py
│   │   └── bot.py             # aiogram: /status /run /stop /stats /errors
│   ├── pipeline.py            # run_once / run_forever, bounded concurrency
│   └── scheduler.py           # APScheduler cron + ручной /run
└── tests/
    ├── test_core.py           # rotator / retry / limiter / hash / contract
    └── test_pipeline.py       # FakeSource DI + in-memory SQLite
```

## Проверено (TESTED / EXECUTED)

- Hermetic-тесты: `pytest tests/test_core.py tests/test_pipeline.py -q` — зелёные.
- Дедуп: повторный upsert того же объекта не создаёт дублей (natural key).
- Смена цены → событие `price_changed` в `property_event`.
- Circuit breaker размыкается после threshold сбоев, recovery после cooldown.
- ProxyRotator: 403/429 → двойной cooldown; success сбрасывает cooldown.
- Ошибка источника не роняет пайплайн (errors=1, статус failed).

## UNVERIFIED / BLOCKED

- Живой источник: BLOCKED — источники не утверждены (C-категория).
- PostgreSQL: UNVERIFIED в этой среде (нет сервера); контракт покрыт SQLite-тестами.
- Прокси-ротация в бою: UNVERIFIED — нет реального провайдера.
