# RUNNABLE — public_request_parser

## Поддерживаемые платформы

- [x***REMOVED*** Termux / Android ARM64 — целевая среда
- [x***REMOVED*** Linux / POSIX — ожидаемый dev fallback
- [ ***REMOVED*** Live production — не заявлен; реализованы P3–P9 (offline/fixture): domain, RSS/Atom, matcher, SQLite/WAL v2, delivery contract, pipeline CLI, TG fixture adapter, gated HTTP

## Минимальные требования

- Python >= 3.11
- SQLite с WAL (планируется для runtime)
- Сетевой доступ только к разрешённым источникам
- Telegram credentials — только для будущего Bot API delivery, не хранить в репозитории

## Текущий запуск

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m app.cli --once --fixture fixtures/rss/sample_rss.xml --db parser.db
PYTHONPATH=. python -m app.cli --maintenance --db parser.db
```

Первый прогон: 2 fetched / 2 new / 1 accepted / 1 delivered (dry-run). Второй прогон: fetched=0 (checkpoint-resume). Maintenance: TTL-expire + backup. Live polling не включён до G2.

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

## Будущие режимы после закрытия G2

```bash
python -m app.cli --once --source <approved-rss-url>   # HttpFeedAdapter (live)
python -m app.cli --once --profile <profile-id>
```

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

- **G2-активация**: источник выбран и `allowed` (HeadHunter API, SRC-011/ADR-011), но live polling выключен до регистрации приложения на dev.hh.ru, API-ключа (secret storage) и canary-прогона — это единственный блокер live-участков; transport готов и gated (`allowed` + `can_poll`).
- Telegram web-preview отключён до отдельного разрешения (fixture-only).
- Живой Telegram delivery transport и общий runtime entrypoint — после policy approval.
