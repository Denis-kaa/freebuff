# RUNNABLE — public_request_parser

## Поддерживаемые платформы

- [x***REMOVED*** Termux / Android ARM64 — целевая среда
- [x***REMOVED*** Linux / POSIX — ожидаемый dev fallback
- [ ***REMOVED*** Live production — не заявлен; реализованы P3 domain layer + P4 RSS/Atom fixture engine + P5 matcher

## Минимальные требования

- Python >= 3.11
- SQLite с WAL (планируется для runtime)
- Сетевой доступ только к разрешённым источникам
- Telegram credentials — только для будущего Bot API delivery, не хранить в репозитории

## Текущий запуск

Реализованы автономный P3 domain layer, P4 RSS/Atom fixture engine (offline) и P5 deterministic matcher. Рабочего HTTP/Telegram entrypoint ещё нет; live polling не включён.

Проверка проекта:

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/ -q
python -m mypy app tests --strict
```

Проверить структуру документов:

```bash
cd projects_17/public_request_parser
find . -maxdepth 2 -type f | sort
```

## Планируемый запуск после этапа реализации

```bash
python -m public_request_parser.cli --dry-run --source <approved-rss-url>
python -m public_request_parser.cli --once --profile <profile-id>
```

Команды являются целевым контрактом, а не утверждением существующего кода. До появления CLI они не должны выполняться как acceptance test.

## Переменные окружения (план)

| Переменная | Назначение | Секрет |
|---|---|---:|
| `PRP_DB_PATH` | SQLite database path | Нет |
| `PRP_CONFIG_PATH` | Profile/source config path | Нет |
| `PRP_TG_BOT_TOKEN` | Telegram delivery token | Да |
| `PRP_TG_CHAT_ID` | Default delivery target | Может быть идентификатором |
| `PRP_POLL_INTERVAL` | Global lower-bound scheduler interval | Нет |
| `PRP_DEFAULT_TEXT_TTL` | Default full-text retention | Нет |

## Известные блокеры

- Первый live RSS/Atom URL ещё не выбран и не прошёл policy matrix.
- Telegram web-preview отключён до отдельного разрешения.
- RSS/Atom parser и matcher реализованы только в offline режиме на fixtures; HTTP transport, SQLite storage, delivery и runtime entrypoint ещё не созданы.
