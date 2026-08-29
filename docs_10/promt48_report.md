# Отчёт: Система промтов с диспетчером и TG-ботом (promt 48)

**Дата:** 2026-08-04
**Версия реализации:** v5.70.0
**Статус:** ✅ реализовано (18/18 тестов зелёные, код-ревью APPROVE)

---

## 1. Что было изучено (окружение)

Перед реализацией проведён полный аудит существующих компонентов (файлы читал, команды не менял):

| Компонент | Файл | Что понял |
|-----------|------|-----------|
| **TG-бот** | `scripts_01/telegram_bot.py` | python-telegram-bot, сессии через `ContextManager`, команды `/start /status /new /session /notify /notify_client`. Расширяем — команду `/task` добавляю сюда (Reuse First, не новый бот). |
| **Базовый класс бота** | `scripts_01/tgbot_base.py` | `.env`-загрузка, токен, `ApplicationBuilder`, polling-цикл, общий error handler. |
| **Сценарный бот** | `freebuff_plugin_03/tgbot.py` | `/scenarios*`, `/escalate` — второй бот на том же `BaseTGBot`. |
| **Запуск бота** | `scripts_01/start_telegram_bot.sh` | `PYTHONPATH=$WORKSPACE exec python scripts_01/telegram_bot.py`. |
| **TG-отправка** | `core_02/telegram_contract.py` | `report_to_saved_messages()` + `report_to_alex_litvinov()` — реальный dual-channel (chat_id 7709651193/1063827731). **`report_to_saved_messages` — async.** |
| **Плагин** | `plugins_04/tg_messenger/` | `send_message`, авто-форвардинг событий, manifest. |
| **Оркестратор** | `scripts_01/orchestrator.py` | Внутрипроцессный оркестратор шагов — НЕ файловый диспетчер очереди промтов. |
| **Event bus** | `scripts_01/event_bus.py` | `publish(event)` / `subscribe(...)` — для событий цикла. |
| **Task manager** | `scripts_01/task_manager.py` | SQLite-статусы — но промт 48 требует **файловый** подход (перемещение файлов). |
| **CLI Баффи** | `freebuff_cli.py` | Парсит `sys.argv` вручную (без argparse), НЕ имеет команды «выполнить промт и дождаться результата» — только управление сессиями. |
| **Запуск Баффи** | `freebuff_plugin_03/wrapper.py` | `launch_and_wait(prompt, cwd, timeout)` — **phase-based (анти-OOM)**: `launch()` стартует сессию и завершается сразу, результат забирается опросом `.freebuff_result` (mtime-baseline против стейл-файла). Тот же путь, что у MCP `run_freebuff`; `synchronous_oneshot` устарел (OOM-риск). |
| **Cron** | `scripts_01/cron_conspect.sh` | Cron в Termux **работает** (`*/30 * * * * .../cron_conspect.sh`) — готовый канал для бесперебойности. |
| **Naming-convention** | `scripts_01/consistency_check.py` | `check_naming_convention` сканирует `pompts_11/*.md` **нерекурсивно** (только верхний уровень) — файлы очереди в подпапках не нарушают правило `NNN_TT`. |

**Ключевые выводы аудита:**
1. Реальный путь запуска Баффи на задаче — `wrapper.launch_and_wait()` (phase-based, анти-OOM), НЕ `freebuff_cli.py` и НЕ `synchronous_oneshot`.
2. TG-отправка — через существующий `core_02/telegram_contract.py` (async → оборачивать в `asyncio.run`).
3. Папки `pompts_11/{user,running,done,failed***REMOVED***` не существовали — созданы.
4. Команды `/task` в боте не было — добавлена.

---

## 2. Что было создано/изменено

### Создано

| Файл | Назначение |
|------|------------|
| `pompts_11/README.md` | Канон формата файла-промта + схема цикла + как запустить. |
| `pompts_11/{user,running,done,failed***REMOVED***/` | Папки очереди (статусы = перемещение файлов, без БД). |
| `scripts_01/prompt_queue.py` | Ядро очереди: метаданные, запись/парсинг промтов, move-статусы, `scan_pending` (сортировка по приоритету), `set_report`, `queue_counts`, `recover_stale_running` (восстановление зависших), CLI-вход для ручного добавления. |
| `scripts_01/prompt_dispatcher.py` | Диспетчер: poll `user/` → запуск Баффи → `done/`/`failed/` → TG-отчёт. Флаги: `--once/--all/--dry-run/--no-tg/--recover/--recover-age/--timeout`. |
| `scripts_01/prompt_dispatch.sh` | Cron-обёртка (логирование в `logs_14/prompt_dispatch.log`). |
| `tests_09/test_prompt_queue.py` | 9 тестов очереди (изоляция через `FREEBUFF_ROOT`→tmp_path). |
| `tests_09/test_prompt_dispatcher.py` | 9 тестов диспетчера (fake launcher, `send_tg=False`). |
| `docs_10/promt48_report.md` | Этот отчёт. |

### Изменено

| Файл | Изменение |
|------|-----------|
| `scripts_01/telegram_bot.py` | Добавлен handler `cmd_task` (строка 313) + регистрация `CommandHandler("task", cmd_task)` в `main()` (строка 443) + упоминание `/task` в help-текстах. |
| `crontab` | Добавлена строка `*/5 * * * * .../prompt_dispatch.sh` (идемпотентно; строка `cron_conspect.sh` сохранена). |

---

## 3. Как это работает (цикл)

```
Telegram: /task <текст>
     │  cmd_task → write_user_prompt(chat_id, text)
     ▼
pompts_11/user/task_<id>_<chat>.md   (pending)
     │
     │  cron каждые 5 мин: prompt_dispatch.sh → prompt_dispatcher.py --once
     │  (зависшие running/ >1ч возвращаются в user/ только при --recover —
     │   флаг вручную или при будущей доработке cron-строки)
     ▼
move_to_status → running/            (метка занятости, файл «не потеряется»)
     │
     │  wrapper.launch_and_wait(meta.body, WORKSPACE, timeout=300)
     │  (phase-based: launch → опрос .freebuff_result, анти-OOM)
     │  ← запуск Баффи (тот же путь, что MCP run_freebuff)
     ▼
успех → set_report(done, отчёт)  |  провал → set_report(failed, причина)
     │
     │  TG-отчёт (best-effort, None-safe):
     │  report_to_saved_messages(📨 [prompt dispatcher***REMOVED*** …)  ← в Избранное
     │  _send_to_chat(chat_id, отчёт)                       ← reply в исходный чат
     ▼
done/ (✅ отчёт в файле) / failed/ (❌ причина в файле)  — повторно не выполняются
```

**Детали:**
- **Формат файла:** `# TASK: <название>` + метаданные `**Ключ:** значение` (`ID`, `Chat ID`, `Created`, `Priority`, `Status`, `Source`) + `---` + тело + `## Отчёт`.
- **Приоритеты:** `scan_pending()` сортирует по убыванию приоритета, затем по имени.
- **Статусы детерминированы** перемещением файлов между папками (требование промт 48), без БД.
- **Отказоустойчивость TG:** отправка отчёта — best-effort (исключения логируются, диспетчер не падает). `report_to_saved_messages` — async, обёрнут в `asyncio.run` (диспетчер — sync CLI).
- **Восстановление после сбоя диспетчера:** `recover_stale_running(max_age_s)` — если процесс умер между `move_to_status(running)` и `set_report(done/failed)`, файл старше 1 часа возвращается в `user/` для повторной обработки («не терять задачу»).
- **Имя файла** `task_<ts>_<uuid6>_<chat>.md` — не подпадает под `NNN_TT` naming-convention (проверка нерекурсивна).

---

## 4. Как запустить

```bash
# ── Бот (нужен для /task) ──
bash scripts_01/start_telegram_bot.sh

# ── Диспетчер вручную ──
python scripts_01/prompt_dispatcher.py --all       # обработать все ожидающие
python scripts_01/prompt_dispatcher.py --once      # один промт (как cron)
python scripts_01/prompt_dispatcher.py --dry-run   # показать очередь без обработки
python scripts_01/prompt_dispatcher.py --recover --dry-run  # восстановить зависшие + посмотреть
python scripts_01/prompt_dispatcher.py --all --no-tg       # без TG-отчёта

# ── Ручное добавление промта в очередь ──
python scripts_01/prompt_queue.py "текст задачи"

# ── Cron (бесперебойность) ──
# Уже установлено: */5 * * * * /storage/emulated/0/PROJECTS/workstation/freebuff/scripts_01/prompt_dispatch.sh
crontab -l | grep prompt_dispatch

# ── Тесты ──
python -m pytest tests_09/test_prompt_queue.py tests_09/test_prompt_dispatcher.py -q   # 18/18
```

**Сценарий использования:** написать в Telegram боту `/task исправь баг в login`, диспетчер в течение ≤5 минут подхватит задачу, запустит Баффи и пришлёт отчёт в Избранное и в чат.

---

## 5. Что не сделано и почему

| Пункт | Статус | Причина |
|-------|--------|---------|
| **Автозапуск бота после перезагрузки Android** (Termux:Boot) | ⏳ не сделано | Честно по правилу промт 48: «не знаю, нужно проверить» — требует проверки на устройстве. Сейчас бот переживает только ручной запуск / держание сессии. |
| **Публичный `send_to_chat(chat_id, text)` в `core_02/telegram_contract.py`** | ⏳ отложено (minor, non-blocking) | `_send_to_chat` в диспетчере повторяет паттерн `_send_text` из telegram_contract. Рефакторинг в единый публичный API — вопрос CON-19 single-source-of-truth, вынесен отдельно. |
| **`rsplit("/", 1)` Windows-портируемость** | ⏳ accepted | Код работает на Termux/POSIX (целевая платформа). Не блокер. |
| **Диагностика «почему Баффи упал» внутри phase-based запуска** | ✅ частично | Причина (launch-ошибка или timeout опроса `.freebuff_result`) пишется в `failed/`-файл и в отчёт; глубокий анализ внутри запущенной сессии — вне scope. |
| **События цикла в event_bus** (`task.*`) | ⏳ не сделано | Не требовалось для MVP; `event_bus.publish` доступен для будущего расширения. |

---

## 6. Открытые вопросы

1. **Termux:Boot** — как настроить автозапуск TG-бота (и при желании диспетчера) после перезагрузки Android? Нужна проверка на устройстве: пакет `termux-boot` + скрипт в `~/.termux/boot/`.
2. **Реальный end-to-end прогон** — тесты покрывают цикл с mock/fake launcher и `send_tg=False`. Первый живой прогон `/task` → реальный запуск Баффи → реальная доставка в TG ещё не выполнен (требует живой TG-сессии и токена в `.env`).
3. **`freebuff_cli.py`** — парсит аргументы вручную и не имеет команды «выполнить промт»; диспетчер идёт через `wrapper.launch_and_wait` (phase-based). Стоит ли добавить в CLI команду `freebuff run <prompt-file>` для симметрии с диспетчером?
4. **Поведение при `--recover` без `--dry-run`** — `--recover` возвращает зависшие файлы и сразу продолжает обычную обработку. Ожидаемое поведение для cron; для ручного запуска может быть неожиданным — документировано в help.
5. **Синхронная очередь** — диспетчер обрабатывает по одному промту за запуск cron (`--once`). При большой очереди `--all` вручную или увеличение частоты cron — решение за оператором.

---

## 7. Multi-turn / interactive режим (v5.79.0)

Расширение промта 48: если Баффи посреди задачи оставляет `pending_task` в `.freebuff_result`, файл не уходит в `done/`, а возвращается в `running/` для следующего cron-тика. Цикл продолжается до завершения (no pending_task) или до принудительного стопа по `**Max Iterations:** N` (default 3).

### Сигнал продолжения

`.freebuff_result` после итерации может содержать JSON:

```json
{
  "status": "ok",
  "pending_task": "Какой порт нужен?",
  "session_id": "abc123",
  "timestamp": "2026-08-04T10:00:00Z"
***REMOVED***
```

Поле `pending_task` — STRING. При пустом/отсутствующем/non-string/malformed-JSON значении → single-turn behaviour (terminal done/failed). Парсер `_extract_pending_task(result)` в `scripts_01/prompt_dispatcher.py` все edge cases returns None (CAN-14 fail-loud).

### Файловый state-machine (расширенный)

| Старая папка | Расширенная роль | Multi-turn статус |
|--------------|------------------|-------------------|
| `pompts_11/user/` | Новый промт | `**Status:** pending` |
| `pompts_11/running/` | В работе / resumable | `**Status:** running` (текущая итерация) или `**Status:** running-pending` (ждущий следующего cron-тика) |
| `pompts_11/running/.in_progress/` | Atomic lock во время dispatch | Файл перемещён сюда под rename, другие cron-тики skip'ют |
| `pompts_11/done/` | Terminal success | Multi-turn `done` после final итерации без pending_task |
| `pompts_11/failed/` | Terminal fail (или max-reached multi-turn) | Single-turn fail или `failed-multi-turn-max` если pending_task исчерпал `max_iterations` |

### Цикл multi-turn

```
Iter 1: file moves user→running; launcher returns pending_task
  → append_iteration(2, "question"); file stays running/ as running-pending
  → released from .in_progress/ lock to running/

Iter 2 (next cron tick ≤5 мин): scan_resumable() finds file
  → atomic lock (rename to running/.in_progress/foo.md)
  → launcher.full_body (includes iter 1 transcript); returns pending_task
  → append_iteration(3, "question"); released back to running/ as running-pending

Iter N (<= max_iterations): same pattern; eventually:
  - no pending_task → terminal done/ (multi-turn w/ badge)
  - pending_task at max → forced failed/ with reason "max_iterations_reached"
```

### Atomic lock discipline (concurrency safety)

- `_move_to_lock(path)` → `rename` под `running/.in_progress/`. POSIX-atomic.
- Другой cron-тик в следующие 5 мин → `scan_resumable()` excludes `running/.in_progress/` → не подхватывает.
- При crash диспетчера во время lock → файл остаётся в `.in_progress/`; `recover_stale_running` (default age 1h) НЕ покрывает этот случай → DEFERRED known limitation (см. ниже).

### File format diff (iter 1 → iter 2)

```
# TASK: Setup nginx
**ID:** 20260804_abc1234
**Status:** running-pending           ← was 'pending', now in multi-turn
**Iteration:** 2                      ← was '1', now promoted
**Max Iterations:** 3                 ← unchanged

---

Setup nginx.

--- Iteration 2 (2026-08-04T10:00:00+00:00) ---    ← new block, before `## Отчёт`
**Баффи:** Какой порт нужен?

---

## Отчёт

**Статус:** iteration 1 оставил pending_task; ожидает следующий cron-тик.
```

### TG-reports

Каждая итерация отправляет отчёт в `core_02.telegram_contract`:
- badge `[Multi-turn N/M***REMOVED***` в статусе (visible operator-у сколько итераций прошло).
- строка `Итерация: N/M`.
- inline `**Следующий pending_task:** …` (full text) для visibility оператора.

При `max_iterations_reached` — badge `[Multi-turn N/M MAX-reached***REMOVED***` + последний pending_task inline.

### Backward compatibility

- Старые файлы в `pompts_11/` (v5.70/5.78) без `**Max Iterations:**` header → `parse_prompt` defaults to 3 (single-turn behavior preserved).
- Single-turn файлы без `pending_task` в `.freebuff_result` → terminal done/failed (existing path unchanged).
- Файлы с explicit `**Max Iterations:** 1` + pending_task → теперь force-fail (was silently `done` — bug fix v5.79.0).

### Known limitations (deferred k v6.x)

- **Orphan `.in_progress/` locks после crash**: `recover_stale_running` смотрит только на `running/` без `.in_progress/` подпапки. Если диспетчер упал во время iter → файл застревает в `.in_progress/` навсегда. Forward-looking guard: добавить recovery-проход для `.in_progress/` с тем же age-cutoff.
- **`running-resumable` status — dead code path**: scan_resumable() accept'ит, но НИЧЕГО не устанавливает этот статус (reserved для future `/answer` TG command, out of scope v5.79.0).
- **Per-iteration TG noise**: max_iterations=3 → до 4 TG-reports per cycle (3 итерации + 1 final). Design Option C (every iter + final); consolidation = future polish.
- **Code duplication ~50 lines** между `_dispatch_multi_turn_iteration` и single-turn branch в `dispatch_one` (extract `_dispatch_iter(...)` shared helper — followup).

## 8. Открытые вопросы (post-multi-turn)

1. **`/answer` TG command** — зарезервировано в `scan_resumable` (status `running-resumable`), но не реализовано. План: оператор отвечает на pending_task напрямую через TG → файл перемещается в `running/` как `running-resumable` → следующий cron-тик подхватывает. Требует дизайна хранения «оператор ответил vs auto-cleared».
2. **Orphan `.in_progress/` recovery** — нужен cron sweep каждые 24h или modified `recover_stale_running` (см. §7 known limitations).
3. **Real TG end-to-end multi-turn прогон** — тесты покрывают цикл mock-launcher'ом и `send_tg=False`. Первый живой прогон `/task` → real pending_task → real TG round-trip ещё не выполнен (требует живой TG-сессии, итеративных TG-сообщений).
4. **Code dedup `_dispatch_iter` shared helper** — followup polish (см. §7 known limitations).
