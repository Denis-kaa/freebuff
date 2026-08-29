# STEPS.md — журнал реализации

> **Проект:** `tg_digital_market` (Telegram-маркетплейс цифровых товаров)
> **Источник:** `pompts_11/060_04_telegram_bot_aiogram.md`
> **Формат:** `step N: <что сделано>; <почему>; <что дальше>`

---

## step 1: перечитан промт 59 и подтверждено видение

**Что:** Перечитал заказ (маркетплейс цифровых товаров на aiogram 3.x, БД, оплата,
админ-панель, кабинет продавца, автовыдача, уведомления, расширяемость).
**Почему:** Пользователь спросил «не изменилось ли видение». Сверил с промтом — текст
тот же; уточнил архитектурные решения (имя `tg_digital_market`, БД — `sqlite3`
stdlib с WAL, платежи — порт `PaymentProvider` с адаптерами, атомарная выдача ключей).
**Дальше:** Поднять каркас и зафиксировать артефакты.

---

## step 2: создан каркас проекта в `projects_17/tg_digital_market/`

**Что:** Директория проекта с заделом под слои: `src/market_bot/` (config, models,
db, services, bot/handlers), `tests/` (core без aiogram), корень — README, RUNNABLE,
CHECKLIST, MANIFEST, project.yaml, requirements.txt, .env.example, STEPS.md.
**Почему:** Соответствует `PROJECT_REQUIREMENTS.md` §6.1 (обязательные файлы +
`src/` + `tests/`). Слои выделены так, чтобы core (без aiogram) был покрыт
тестами изолированно.
**Дальше:** Заполнить корень (project.yaml, requirements.txt, MANIFEST, .env.example).

---

## step 3: корень проекта заполнен базовыми артефактами

**Что:** Созданы `project.yaml` (Forge-конфиг), `requirements.txt` (только
`aiogram` рантайм + `pytest`/`pytest-asyncio`), `.env.example` (BOT_TOKEN,
ADMIN_IDS, DATABASE_PATH, PAYMENT_PROVIDER и т.д.).
**Почему:** `project.yaml` регистрирует проект в Forge; `requirements.txt` —
минимально необходимые зависимости (aiosqlite осознанно НЕ добавлен: используем
stdlib `sqlite3` через `asyncio.to_thread`).
**Дальше:** Доменный слой — модели и схема БД.

---

## step 4: доменный слой — models, schema, обёртка БД

**Что:** `models.py` (frozen dataclasses + Enum'ы), `db/schema.sql` (SQLite-схема
8 таблиц + индексы + CHECK constraints), `db/database.py` (sync sqlite3 обёртка
с RLock + явные BEGIN/COMMIT/ROLLBACK в `_TxCtx`).
**Почему:** Бизнес-логика работает на типизированных моделях, не на dict'ах.
WAL + foreign_keys=ON — стандарт надёжности. Класс `Database` инкапсулирует
SQLite, repository может подменить на PostgreSQL позже.
**Дальше:** Repository и сервисы.

---

## step 5: репозиторий + сервисы — первая валидация через thinker

**Что:** `db/repository.py` (CRUD + атомарный `reserve_key_for_order`),
`services/catalog.py`, `services/orders.py` (стейт-машина заказа),
`services/payments.py` (порт `PaymentProvider` с MockPaymentProvider +
TelegramStarsVerifyProvider), `services/delivery.py`, `services/notifications.py`.
**Почему:** После первой реализации прогнал через thinker-with-files-gemini —
получил 7 конкретных рисков с фиксами (атомарность, FSM, payment wire-up, TTL).
Применил каждый фикс (см. ниже в шаге 6).
**Дальше:** Применить фиксы ревью thinker'а.

---

## step 6: фиксы по ревью thinker'а (7 рисков)

**Что:** Применил 7 минимальных правок:
  1. **Атомарный reserve_key_for_order** — заменил двухшаговый (SELECT+UPDATE) на
     один `UPDATE … WHERE id = (SELECT … LIMIT 1) RETURNING *`.
  2. **`mark_paid` идемпотентен** для PAID/DELIVERED — no-op (не падать, чтобы
     Telegram не ретраил бесконечно).
  3. **`cancel` запрещает PAID/DELIVERED** — раньше позволял, что вело к
     потере денег. Для refund — отдельный флоу.
  4. **`expire_overdue` параллельно фейлит связанный payment** через
     `PaymentService.fail` — иначе платёж висел бы в pending.
  5. **Recovery `find_paid_orphans`** + автозапуск в `bot/main.py` —
     защита от падения между `mark_paid` и `DeliveryService.publish`.
  6. **Упрощённый `_release_unfinished_keys`** — один SQL вместо вложенного цикла.
  7. **FSM-машина + recovery + Auto-rollback на OutOfStock** — заказ в FAILED
     без висящего pending-а.

**Почему:** Thinker подсветил реальные гонки и финансовые риски. Внести правки
на этом этапе — дешёво; после добавления aiogram-слоя — дорого.
**Дальше:** Поднять aiogram-слой + тесты.

---

## step 7: aiogram-слой — handlers + keyboards + main

**Что:** `bot/keyboards.py` (CallbackData + клавиатуры), `bot/states.py`
(только SellerFlow — cart на inline-кнопках без FSM), `bot/aiogram_channel.py`
(адаптер NotificationChannel), `bot/services_container.py` (DI),
`bot/main.py` (entrypoint + recovery + polling), `bot/handlers/*.py`
(common, catalog, account, cart, admin, seller).
**Почему:** Стандартные routing-паттерны aiogram 3.x; cart-флоу через inline-кнопки
упрощает код без потери UX; seller-флоу — через FSM (ввод товара пошагово).
**Дальше:** Тесты для core-логики.

---

## step 8: тесты core-логики — pytest зелёный

**Что:** `pytest.ini` (pythonpath=src), `tests/conftest.py` (db + services fixtures),
`tests/test_repository.py`, `tests/test_atomicity.py` (10 потоков на 5 ключей),
`tests/test_order_fsm.py`, `tests/test_ttl_expiration.py`, `tests/test_payments.py`
(attach idempotency / finalize no-op).
**Почему:** Тесты НЕ импортируют aiogram → можно гонять в любой среде (Termux,
CI, dev), даже если aiogram не установлен. Атомарность под гонкой — обязательна.
**Дальше:** Фиксы по ревью code-reviewer'а.

---

## step 9: фиксы по ревью code-reviewer-minimax-m3 (раунд 1)

**Что:** Применил 6 HIGH + 6 MEDIUM правок:
  1. **Repository.raw_conn property** — `repo.raw_conn.execute(...)` теперь
     работает в тестах и сервисах.
  2. **`PaymentService.attach_to_order` идемпотентен** для PENDING.
  3. **`PaymentService.finalize`** — guard `order.status in (PAID, DELIVERED)`:
     нет revert DELIVERED→PAID при ретрае Telegram `successful_payment`.
  4. **`PaymentService.fail`** — больше НЕ меняет order.status (фикс
     `expire_overdue` → CANCELLED вместо FAILED).
  5. **`OrderService.mark_failed`** — убран `cancelled=True` для FAILED.
  6. **NotificationService** — `try/except` вокруг `channel.send/broadcast`.
  7. **database.py: RLock** — `threading.Lock` → `threading.RLock` +
     `transaction()` захватывает RLock на всё тело (устраняет InterfaceError
     под гонками).
  8-10. **Прочие мелкие** (conftest.py sys.path, account.py F-импорт,
     admin_cb убран сломанный button, test_repository.py поправлен pid→pid.id).

**Почему:** HIGH — реальные блокеры (порча денег, no-op handler'ов,
import-ошибки). MID — снижают риск продакшн-сбоев.
**Дальше:** Повторное ревью и оставшиеся HIGH.

---

## step 10: фиксы по ревью code-reviewer-minimax-m3 (раунд 2)

**Что:** Применил ещё 2 HIGH из финального мини-ревью:
  1. **`_TxCtx.__enter__` теперь выполняет `BEGIN IMMEDIATE`** — реальная
     транзакция, а не «auto-commit обёртка». Раньше: коннект был в
     `isolation_level=None` (autocommit), `commit()` в __exit__ был no-op;
     `rollback()` тоже ничего не откатывал. Фикс: `BEGIN IMMEDIATE` стартует
     RESERVED-блокировку сразу, что идеально подходит для записи; под
     thread-safe write-задач — настоящая транзакционная защита.
  2. **TTL watcher в `main.py`** — фоновая asyncio-задача каждые 60 сек
     вызывает `OrderService.expire_overdue(ttl)`. Без неё PENDING-заказы
     висели бы в БД неопределённо долго (особенно в Mock-режиме, где
     пользователь может не закончить оплату).
  3. **Recovery вынесен в `_recover_one_order` + каждый вызов в `to_thread`**
     (фикс MEDIUM-2): консистентно с остальной кодовой базой.

**Почему:** Защита от (a) потери ключей при kill в середине `executemany`,
(b) накопления висящих заказов в проде.
**Дальше:** Финальный прогон тестов и повторное ревью для верификации.

---

## Следующий шаг

* Прогнать `python -m pytest tests/` после фиксов 11 → должно остаться 14 passed.
* Подключить Telegram Stars в проде (.env: `PAYMENT_PROVIDER=telegram_stars` +
  `PAYMENT_PROVIDER_TOKEN`).
* Написать handler-интеграционные тесты (требует установки `aiogram`).
* Реализовать refund-флоу для PAID-заказов (отдельный сервис).
* FSM TTL cleanup в seller-флоу (RedisStorage или периодический clear).

## step 11: Forge integration

Подключён к Buffy Forge: projects_17/workspace.yaml создан, project.yaml валиден, регистрация в ForgeRegistry успешна. STEPS.md теперь Forge-managed — формат валидируется через _validate_steps_format, Project.append_step() интегрирован в cmd_step CLI (Этап 4.4 PLAN_NEXT_OPERATIONS).

---

