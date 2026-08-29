# MANIFEST.md — tg_digital_market

> **Проект:** `tg_digital_market` (Telegram-маркетплейс цифровых товаров)
> **Источник:** `pompts_11/060_04_telegram_bot_aiogram.md`
> **Версия:** 0.1.0

## Pipeline State

```yaml
project: tg_digital_market
version: 0.1.0
status: mvp_ready
test_count: 8+
backend_test_status: green
aiogram_layer_status: written (integration tests pending)
```

## Components

| Слой | Файл | Статус |
|---|---|---|
| Domain models | `src/market_bot/models.py` | ✅ |
| DB schema | `src/market_bot/db/schema.sql` | ✅ |
| DB wrapper | `src/market_bot/db/database.py` | ✅ (WAL + lock) |
| Repository | `src/market_bot/db/repository.py` | ✅ (атомарный UPDATE+подзапрос) |
| Catalog service | `src/market_bot/services/catalog.py` | ✅ |
| Order service | `src/market_bot/services/orders.py` | ✅ (FSM + recovery) |
| Payment service | `src/market_bot/services/payments.py` | ✅ (порт + Mock + Stars-verify) |
| Delivery service | `src/market_bot/services/delivery.py` | ✅ |
| Notification service | `src/market_bot/services/notifications.py` | ✅ (порт + FakeChannel) |
| Config loader | `src/market_bot/config.py` | ✅ |
| Bot entry | `src/market_bot/bot/main.py` | ✅ |
| Bot DI | `src/market_bot/bot/services_container.py` | ✅ |
| Bot keyboards | `src/market_bot/bot/keyboards.py` | ✅ |
| Bot states | `src/market_bot/bot/states.py` | ✅ |
| Bot channel | `src/market_bot/bot/aiogram_channel.py` | ✅ |
| Handlers /start | `src/market_bot/bot/handlers/common.py` | ✅ |
| Handlers catalog | `src/market_bot/bot/handlers/catalog.py` | ✅ |
| Handlers cart | `src/market_bot/bot/handlers/cart.py` | ✅ (Mock + Stars) |
| Handlers account | `src/market_bot/bot/handlers/account.py` | ✅ |
| Handlers admin | `src/market_bot/bot/handlers/admin.py` | ✅ (статистика) |
| Handlers seller | `src/market_bot/bot/handlers/seller.py` | ✅ (FSM-добавление) |

## Tests

| Файл | Тестов | Покрывает |
|---|---|---|
| `tests/test_repository.py` | 4 | CRUD users/products/orders/payments |
| `tests/test_atomicity.py` | 1 (10 потоков) | Атомарная выдача под гонкой |
| `tests/test_order_fsm.py` | 4 | FSM, идемпотентность, запрет cancel PAID |
| `tests/test_ttl_expiration.py` | 1 | TTL → CANCELLED + release key + fail payment |
| **Итого** | **10** | core-логика (без aiogram) |

## Документация

- [README.md***REMOVED***(README.md) — обзор, архитектура
- [RUNNABLE.md***REMOVED***(RUNNABLE.md) — запуск, .env, быстрый старт
- [CHECKLIST.md***REMOVED***(CHECKLIST.md) — pre-flight
- [STEPS.md***REMOVED***(STEPS.md) — журнал реализации (пошагово)
- [project.yaml***REMOVED***(project.yaml) — Forge-конфиг (`core_02/workspace.py`)
- [MANIFEST.md***REMOVED***(MANIFEST.md) — этот файл

## Roadmap (вне MVP)

- [ ***REMOVED*** Refund-флоу для PAID-заказов (отдельный сервис).
- [ ***REMOVED*** Escrow на стороне продавца (вывод средств).
- [ ***REMOVED*** Web-админка (FastAPI + WebSocket для real-time модерации).
- [ ***REMOVED*** Поддержка Postgres через замену `Database` на `asyncpg.Pool`.
- [ ***REMOVED*** Расширенное админ-меню: set_role, deactivate_product, ban_user, рассылка.
- [ ***REMOVED*** Защита admin-роутов middleware (сейчас проверка в `cmd_admin` и callback).
- [ ***REMOVED*** FSM TTL cleanup для seller-флоу (если продавец забудет подтвердить).
- [ ***REMOVED*** Migration framework (Alembic-like) при развитии схемы.
