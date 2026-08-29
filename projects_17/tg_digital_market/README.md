# tg_digital_market

> **Выполнение `pompts_11/060_04_telegram_bot_aiogram.md`** — Telegram-маркетплейс цифровых товаров.

Telegram-бот на **aiogram 3.x**, реализующий маркетплейс цифровых товаров с
каталогом, личным кабинетом, оплатой, историей заказов, админ-панелью,
кабинетом продавца и автоматической выдачей цифровых кодов после оплаты.

## Стек

- **Python 3.10+**
- **aiogram 3.x** — Telegram-бот-фреймворк
- **sqlite3 (stdlib)** + WAL — БД
- **pytest / pytest-asyncio** (опционально) — тесты

Размер зависимостей минимален: только `aiogram` рантайм + `pytest`. Никаких
`aiosqlite`/`SQLAlchemy`/`pydantic` — потому что и без них всё надёжно и
портативно в Termux.

## Архитектура

```
┌─ handlers (bot/handlers/*.py) ────────@router.message/@callback_query
│                                           │
├── services ─────────────────────────────────┴────────── async-обёртки
│   ├── CatalogService      (каталог)
│   ├── OrderService        (стейт-машина, атомарная выдача)
│   ├── PaymentService      (порт PaymentProvider: mock|telegram_stars)
│   ├── DeliveryService     (публикация ключа после оплаты)
│   └── NotificationService (порт NotificationChannel: FakeChannel|Aiogram)
│
├── db ───────────────────────────────────── sync sqlite3, WAL
│   ├── Database            (обёртка с lock + transactions)
│   └── Repository          (CRUD + атомарный UPDATE с подзапросом)
│
└── models.py ──────────────────────── frozen dataclasses, Enum'ы
```

### Ключевые архитектурные решения

| Решение | Почему |
|---|---|
| **Sync `sqlite3` + `asyncio.to_thread`** | Минимум зависимостей, надёжнее в Termux-sandbox; aiogram-хэндлеры оборачивают DB в `to_thread`. Глобальный lock сериализует — для маркетплейсов этой нагрузки достаточно. |
| **Атомарный `UPDATE … WHERE id = (SELECT … LIMIT 1)` в `reserve_key_for_order`** | SQLite сериализует писателей; подзапрос и UPDATE под одной блокировкой. Гарантия: «один ключ — один заказ» без двойных выдач. |
| **Платёжный порт `PaymentProvider`** с адаптерами `MockPaymentProvider` + `TelegramStarsVerifyProvider` | Mock для dev/test без Telegram; Stars-адаптер verify-only (отправку делает aiogram). |
| **FSM только для Seller-флоу** | Cart-флоу реализован на inline-кнопках (без FSM) — проще и достаточно для MVP. |
| **Авто-recovery PAID-orphans при старте бота** | Если процесс упал между `mark_paid` и `publish`, ключ остался бы в `reserved`. Recovery находит PAID без доставки и публикует. |

## Структура проекта

```
tg_digital_market/
├── README.md
├── RUNNABLE.md           # инструкции запуска
├── CHECKLIST.md          # pre-flight
├── MANIFEST.md           # состояние «конвейера»
├── STEPS.md              # журнал реализации
├── project.yaml          # Forge-конфиг
├── requirements.txt
├── .env.example
├── pytest.ini
├── src/
│   └── market_bot/
│       ├── __init__.py
│       ├── config.py               # из .env
│       ├── models.py               # dataclasses + enums
│       ├── db/
│       │   ├── __init__.py
│       │   ├── schema.sql          # инициализация БД
│       │   ├── database.py         # sync sqlite3 обёртка
│       │   └── repository.py       # CRUD + атомарные операции
│       ├── services/
│       │   ├── __init__.py
│       │   ├── catalog.py
│       │   ├── orders.py           # стейт-машина
│       │   ├── payments.py         # порт + адаптеры
│       │   ├── delivery.py
│       │   └── notifications.py
│       └── bot/
│           ├── __init__.py
│           ├── keyboards.py        # CallbackData + builders
│           ├── states.py           # FSM-группы
│           ├── aiogram_channel.py
│           ├── services_container.py
│           ├── main.py             # entrypoint
│           └── handlers/
│               ├── __init__.py
│               ├── common.py       # /start, /help, /mock_pay
│               ├── catalog.py
│               ├── account.py
│               ├── cart.py
│               ├── admin.py
│               └── seller.py
└── tests/
    ├── conftest.py
    ├── test_repository.py
    ├── test_atomicity.py           # 10 потоков на 5 ключей
    ├── test_order_fsm.py
    └── test_ttl_expiration.py
```

## Установка

```bash
cd projects_17/tg_digital_market
pip install -r requirements.txt
cp .env.example .env
# заполнить BOT_TOKEN из @BotFather, ADMIN_IDS — свой Telegram ID
```

## Запуск

```bash
# Из корня проекта:
python -m market_bot.bot.main

# или:
PYTHONPATH=src python -m market_bot.bot.main
```

Бот начнёт polling. Для отладки (без Telegram) — используйте `PAYMENT_PROVIDER=mock`
и команду `/mock_pay <payment_id>` для финализации mock-платежей.

## Тесты

```bash
# Все unit-тесты (core-слой, без aiogram):
python -m pytest tests/ -v
```

Тестовые сценарии:
- `test_atomicity.py` — 10 потоков с 5 ключами: ровно 5 успешных, 5 — OutOfStock.
- `test_order_fsm.py` — полный happy-path, идемпотентность, запрет cancel PAID.
- `test_ttl_expiration.py` — просроченный pending → CANCELLED + ключ возвращён + payment фейлится.
- `test_repository.py` — CRUD-проверки всех сущностей.

## Расширение

| Хочу | Куда |
|---|---|
| Добавить способ оплаты | Новый класс с `name` и `verify` в `services/payments.py` + регистрация в `get_provider()`. |
| Другая БД (Postgres) | Реализовать `Database`-интерфейс через `asyncpg` и подменить в `ServiceFactory.build()`. |
| Многоязычность | Вынести тексты в `market_bot/texts.py`, прокинуть в хэндлеры. |
| Поддержка escrow | Добавить таблицу `escrow` + `OrderService.payout_seller(seller_id, order_id)`. |
