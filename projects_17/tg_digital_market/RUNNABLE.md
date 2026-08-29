# RUNNABLE — tg_digital_market

## Поддерживаемые платформы

- [x***REMOVED*** Linux (с Python 3.10+, включая Termux на Android)
- [x***REMOVED*** macOS / Linux servers (systemd)
- [ ***REMOVED*** Windows — должен работать (aiosqlite не используется; sqlite3 — stdlib)

> Бот — Python-only, не требует Node/esbuild. Web-фолбэк НЕ нужен, потому
> что проект не использует React Native / Expo / нативные модули.

## Минимальные требования

- Python: ≥ 3.10
- ОЗУ: ≥ 100 МБ (бот стартует в 30–60 МБ)
- Диск: ≥ 30 МБ (aiogram + код)
- Сеть: исходящий доступ к `api.telegram.org`

## Быстрый старт

### 1. Получите токен

- Откройте [@BotFather***REMOVED***(https://t.me/BotFather) в Telegram.
- Команда `/newbot`, следуйте инструкциям.
- Скопируйте токен в `.env` как `BOT_TOKEN=...`.

### 2. Подготовьте окружение

```bash
cd projects_17/tg_digital_market
python3 --version             # ожидаемо ≥ 3.10
python3 -m pip install -r requirements.txt
cp .env.example .env
$EDITOR .env
# — обязательно задать BOT_TOKEN и ADMIN_IDS (ваш Telegram ID).
# — по умолчанию PAYMENT_PROVIDER=mock — для теста без @BotFather Payments.
```

### 3. Запустите бота

```bash
PYTHONPATH=src python3 -m market_bot.bot.main
```

Бот начнёт polling. В Telegram найдите своего бота и нажмите `/start`.

### 4. Тестовый заказ (mock)

1. `/start` → главное меню.
2. «🛍 Каталог» → категории (по умолчанию пусто, пока продавец не добавит товар).
3. Чтобы добавить тестовый товар — установите себя продавцом:
   ```sql
   sqlite3 data/market.sqlite \
     "UPDATE users SET role='seller' WHERE id=<ваш_telegram_id>;"
   ```
   или попросите админа выполнить то же через `/admin`.
4. `/seller` → «➕ Добавить товар» → название / описание / категория / цена / ключи (по одному в строке).
5. Переключитесь на обычного пользователя (другая учётка) → `/start` → каталог → «💳 Купить» → «✅ Подтверждаю».
6. Вы получите код; продавцу придёт уведомление.

### 5. Mock-платёж без UI

Если идёте через mock без inline-кнопки «Подтверждаю»:

```bash
# В Telegram:
/mock_pay <payment_id>
# (payment_id печатается в логах при создании заказа)
```

## Известные блокеры

- **Нет `ADMIN_IDS` в `.env`** — админ-команды не работают. Бот работает как обычный пользователь.
- **Нет `PAYMENT_PROVIDER_TOKEN`** в режиме Stars — инвойс не создастся. Будет ошибка при попытке `/start` → категории → покупка.
- **FS FAT32 (sdcard)** — может мешать `os.symlink` в виртуальных средах. `pip install aiogram` в этом случае может падать с permission errors — используйте `python3 -m venv .venv && pip install -r requirements.txt` на полноценном разделе или работайте в Termux-песочнице.

## Переменные окружения

| Переменная | Что | Дефолт |
|---|---|---|
| `BOT_TOKEN` | Токен от @BotFather | (нет, обязательно) |
| `ADMIN_IDS` | Через запятую Telegram ID админов | пусто |
| `DEFAULT_SELLER_ID` | Продавец по умолчанию (опционально) | пусто |
| `DATABASE_PATH` | Путь к SQLite | `data/market.sqlite` |
| `PAYMENT_PROVIDER` | `mock` или `telegram_stars` | `mock` |
| `PAYMENT_PROVIDER_TOKEN` | Токен провайдера для Stars | пусто |
| `PAYMENT_TTL_SECONDS` | TTL pending-заказа | 900 (15 мин) |
| `LOG_LEVEL` | Уровень логов | `INFO` |

## Команды

| Команда | Кто | Что |
|---|---|---|
| `/start` | все | Регистрация + главное меню |
| `/help` | все | Список команд |
| `/seller` | продавец | Кабинет продавца |
| `/admin` | админ | Админ-панель |
| `/mock_pay <id>` | админ | Финализировать mock-платёж |
