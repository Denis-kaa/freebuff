# CHECKLIST — tg_digital_market

## Pre-flight (перед каждым запуском)

### Окружение

- [ ***REMOVED*** Python: `python3 --version` ≥ 3.10
- [ ***REMOVED*** Postgres не требуется (используется stdlib sqlite3)

### Зависимости

- [ ***REMOVED*** `python3 -m pip install -r requirements.txt` — без ошибок
- [ ***REMOVED*** `python3 -c 'import aiogram; print(aiogram.__version__)'` — ≥ 3.10

### Конфигурация

- [ ***REMOVED*** `.env` существует (скопирован из `.env.example`)
- [ ***REMOVED*** `BOT_TOKEN` задан (от @BotFather)
- [ ***REMOVED*** `ADMIN_IDS` содержит ваш Telegram ID (можно узнать у @userinfobot)
- [ ***REMOVED*** Если планируется Stars-оплата: `PAYMENT_PROVIDER=telegram_stars` и
       `PAYMENT_PROVIDER_TOKEN` задан (см. https://core.telegram.org/bots/payments)

### База данных

- [ ***REMOVED*** Каталог `data/` существует (создаётся автоматически при `init`)
- [ ***REMOVED*** Миграций нет — применяется свежая `schema.sql` при `Database.init()`

### Тесты

- [ ***REMOVED*** `python3 -m pytest tests/ -v` — все 4 файла зелёные

## Pre-flight перед добавлением товара (для теста)

- [ ***REMOVED*** Вам выдана роль `seller`:
      либо через SQLite (`UPDATE users SET role='seller' WHERE id=...`),
      либо `/admin` → «Назначить роль» (вне MVP — ручной SQL).
- [ ***REMOVED*** `/seller` показывает ваш кабинет.
- [ ***REMOVED*** В FSM добавления товара ввели: имя, описание, категорию, цену, ≥ 1 ключ.
- [ ***REMOVED*** После добавления ключей видно сообщение «Добавлено ключей: N».
- [ ***REMOVED*** Переключились на обычного пользователя → `/start` → категория → «💳 Купить» (или «⛔ Нет в наличии» — тогда добавьте больше ключей).
