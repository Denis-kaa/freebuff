# pompts_11/ — очередь промтов (promt 48)

Файловая очередь задач для диспетчера. Статусы = перемещение файлов (без БД):

| Папка | Статус | Что происходит |
|-------|--------|----------------|
| `user/` | `pending` | Промт создан (`/task` в Telegram или вручную), ждёт диспетчера |
| `running/` | `running` | Диспетчер подхватил, Баффи выполняет |
| `done/` | `done` | Выполнено ✅ (в файле — отчёт о результате) |
| `failed/` | `failed` | Ошибка ❌ (в файле — причина) |

## Формат файла промта

Имя: `task_<YYYYmmdd_HHMMSS>_<chat_id_or_anon>.md`
(не подпадает под `NNN_TT` — проверка naming-convention сканирует только `pompts_11/*.md` на верхнем уровне).

```markdown
# TASK: <краткое название>

**ID:** <uuid>
**Chat ID:** <telegram chat_id или 0>
**Created:** <ISO timestamp>
**Priority:** <0-9, по умолчанию 0>
**Status:** pending | running | done | failed
**Source:** tg | cli

---

<тело промта — полный текст задачи>

---

## Отчёт

**Результат:** <заполняет диспетчер>
```

## Цикл

```
user/ ──(cron: prompt_dispatch.sh)──▶ dispatcher ──▶ running/
                                                        │  launch Баффи (launch_and_wait, phase-based анти-OOM)
                                                        ▼
                                         done/ (✅ отчёт) / failed/ (❌ причина)
                                                        │
                                                        ▼
                                        report_to_saved_messages() + reply в чат
```

## Как запустить

```bash
# Диспетчер (вручную, обработать все ожидающие):
python scripts_01/prompt_dispatcher.py --all

# Один промт (для cron):
python scripts_01/prompt_dispatcher.py --once

# Cron (бесперебойность, добавлено в crontab):
*/5 * * * * bash /storage/emulated/0/PROJECTS/workstation/freebuff/scripts_01/prompt_dispatch.sh
```

## Бесперебойность

- Диспетчер: cron-строка (инфраструктура cron в Termux уже работает — см. `cron_conspect.sh`).
- TG-бот: `bash scripts_01/start_telegram_bot.sh`.
- Автозапуск после перезагрузки Android — через Termux:Boot (нужно проверить на устройстве).
