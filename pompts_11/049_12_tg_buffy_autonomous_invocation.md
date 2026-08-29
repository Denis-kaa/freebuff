# TASK: Автономный вызов Баффи из TG — on-demand + cron (фоновая nohup-совместимая сессия)

## Контекст (изучи перед работой — Reuse First!)

Баффи = ИИ-мозг Freebuff (см. ADR-012 + docs_10/core/CORE_PROMPT.md). «Запустить Баффи» НЕ значит «запустить бинарь напрямую» — прочти `docs_10/HOW_TO_LAUNCH_BUFFY.md` + `freebuff_plugin_03/wrapper.py` перед кодом.

### Как на самом деле вызывается Buffy (research + recon, 2026-08-05)

1. **Codebuff/Freebuff CLI — interactive TUI** (web-research подтвердил): `npm i -g codebuff|freebuff`, бинарь интерактивный, НЕ имеет native `--prompt`/headless флага, НЕ пишет результат в файл сам. **Прямой `nohup <binary>` НЕ работает** — процесс зависнет в TUI без ввода.
2. **Правильный механизм фонового запуска — `freebuff_plugin_03/wrapper.py`**:
   - `launch()` (phase-based, анти-OOM): создаёт tmux-сессию → `script -q <log> -c '<proot_cmd>'` → фоновый `monitor.sh` ждёт результат → `.freebuff_result` файл.
   - `launch_and_wait()` — launch() + опрос `.freebuff_result` (для cron/диспетчера, анти-OOM).
   - `synchronous_oneshot()` — legacy sync (только отладка).
   - `_build_buffer_cmd(work_dir)`: внутри proot → `{FREEBUFF_BINARY***REMOVED*** --cwd {work_dir***REMOVED***` (direct); нативный Termux → `proot-distro login ubuntu -- {FREEBUFF_BINARY***REMOVED*** --cwd {work_dir***REMOVED***` (v5.73.0 CON-31).
3. **Уже есть рабочий конвейер** (promt-48, v5.70–v5.87): `TG /task` → `pompts_11/user/*.md` → `scripts_01/prompt_dispatcher.py::dispatch_one` → `wrapper.launch_and_wait` → `done/failed` + отчёт в TG.
4. **Двухпутевая доставка (dual-path, v5.83.0)**: `cmd_task` сразу spawn'ит dispatcher (1–3 сек) + cron `*/5 * * * * prompt_dispatch.sh` как safety-net.
5. **OOM-урок CON-27 (v5.87.0)**: на phone-class RAM реальный Buffy-spawn (proot, GB-class) может умереть signal 9. Lean-path подтверждает round-trip отдельно (`scripts_01/tg_roundtrip_verify.py`).

## Цель

Сделать так, чтобы **Telegram-бот мог вызвать Баффи**:
- **По вызову (on-demand)**: пользователь пишет `/task <текст>` → Баффи запускается в фоне (nohup/tmux-совместимо) → выполняет операцию → результат приходит в TG.
- **По крону**: очередь промтов обрабатывается автоматически каждые ≤5 мин, даже если бот упал (safety-net).
- Баффи «установлен в корне всей файловой системы freebuff» (`/storage/emulated/0/PROJECTS/workstation/freebuff`) — все пути резолвятся от `FB_ROOT`, никаких hardcoded `/tmp` и PYTHONPATH-магии (Block-A: `_freebuff_locator` pattern).

## Что уже есть (НЕ переписывать!)

| Компонент | Файл | Статус |
|-----------|------|--------|
| TG `/task` + dual-path spawn | `scripts_01/telegram_bot.py::cmd_task` | ✅ v5.83.0 |
| Диспетчер очереди (phase-based) | `scripts_01/prompt_dispatcher.py` | ✅ v5.70–v5.79 |
| Cron safety-net | `scripts_01/prompt_dispatch.sh` (crontab `*/5`) | ✅ |
| Фоновый запуск Buffy | `freebuff_plugin_03/wrapper.py::launch/launch_and_wait` | ✅ v5.71 |
| Multi-turn цикл | `scripts_01/prompt_queue.py` (iteration/max_iterations) | ✅ v5.79 |
| OOM-safe live round-trip | `scripts_01/tg_roundtrip_verify.py` | ✅ v5.87 |
| Запуск бота | `scripts_01/start_telegram_bot.sh` / `start_tgbot.sh` | ✅ |

## Задачи (реализуй то, чего не хватает)

1. **Стабильный daemon-запуск TG-бота на Termux** (nohup/setsid/tmux): `start_telegram_bot.sh` должен запускаться через `nohup ... &` или tmux detached так, чтобы Termux-kill Android не терял бота навсегда (используй `scripts_01/oom_protect.sh` + `start_tgbot.sh` паттерны). Проверь `TELEGRAM_BOT_TOKEN` из `.env`.
   > **⚠️ КРИТИЧЕСКИ ВАЖНО (nohup vs wrapper.launch)**: `nohup` применим ТОЛЬКО к процессу TG-бота (обычный Python-скрипт — безопасно). Сам Buffy (Codebuff CLI, interactive TUI) НИКОГДА не запускается через прямой `nohup` — только через `wrapper.launch()`/`launch_and_wait()` (tmux-сессия + `.freebuff_result` polling). Не путай два уровня запуска.
2. **Гарантия обработки очереди**: cron `*/5` + immediate spawn. Если `cmd_task` spawn упал → ответ должен упоминать cron safety-net (уже есть, проверь).
3. **Ожидание результата в TG**: убедись, что отчёт доходит до исходного chat_id (через `core_02/telegram_contract.send_to_chat`, CON-19 — единая точка).
4. **OOM-защита**: диспетчер использует `launch_and_wait` (не `synchronous_oneshot`). Если Buffy умирает по OOM — файл остаётся в `running/.in_progress/` и `--recover` подхватывает при следующем cron-тике.
5. **Пути**: все `FB_ROOT`-резолвинг, никаких hardcoded абсолютных путей вне корня.

## Критерии приёмки (Verify Gate)

- `python3 -m py_compile` всех затронутых файлов → exit 0.
- `pytest tests_09/test_prompt_dispatcher.py tests_09/test_prompt_queue.py tests_09/test_multi_turn_dispatcher.py tests_09/test_wrapper_phase.py` → зелёные.
- `python3 scripts_01/prompt_dispatcher.py --once --dry-run` → корректный report без TG-отправки.
- `scripts_01/prompt_dispatch.sh` → логирует в `logs_14/cron.log` и завершается.
- Live-smoke `/task` (если оператор разрешит): round-trip через `scripts_01/tg_roundtrip_verify.py` → Saved msg_id положительный.
- `drift_check` + `consistency_check` → exit 0 (без новых warnings).

## Открытые вопросы (зафиксируй, если не можешь решить сам)

1. Бот живёт в tmux-detached vs nohup — что надёжнее на Termux при Android kill? (Смотри `overlay_float.sh`/`oom_protect.sh` прецеденты.)
2. Нужен ли `/status` в боте с состоянием очереди (user/running/done/failed counts) — или уже достаточно `/queue list`?
3. `AGENTS.md`/`BUFFY_PROJECT.md` version stamps — синхронизировать с релизом после закрытия этой задачи.

## Правила

- **Reuse First**: не создавай второй диспетчер/второй wrapper/второй telegram_contract. Расширяй существующее.
- Файловая очередь, без DB. Атомарные rename-локи, без daemon.
- Код — production-ready, документируй всё (docstrings, README).
- После работы: `git add` + commit + CHANGELOG entry + bump версии.
