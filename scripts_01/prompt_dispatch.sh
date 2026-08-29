#!/data/data/com.termux/files/usr/bin/bash
# prompt_dispatch.sh — обработка очереди промтов (promt 48).
# Вызывается cron'ом; обрабатывает один промт за запуск (не блокирует надолго).
#
# Добавить в crontab (crontab -e):
#   */5 * * * * /storage/emulated/0/PROJECTS/workstation/freebuff/scripts_01/prompt_dispatch.sh
#
# Опционально: --all обработать всю очередь за раз (для ручного запуска).

FREEBUFF="${FREEBUFF_ROOT:-/storage/emulated/0/PROJECTS/workstation/freebuff***REMOVED***"
LOG="$FREEBUFF/logs_14/prompt_dispatch.log"

cd "$FREEBUFF" || exit 1
mkdir -p "$FREEBUFF/logs_14"

FLAG="${1:---once***REMOVED***"

# ── DUAL-PATH safety-net (v5.83.0): если bot-spawn patrol'ил a runtime crash
# (e.g., `wrapper.launch_and_wait` killed by OOM, leaving stale `.in_progress/` lock),
# `--recover --recover-age` должен запустить ПЕРВЫМ — он толкнёт старые locks обратно в `user/`.
# Если dispatcher ещё не поддерживает --recover (ancient build), игнорируем.
echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: recover stale .in_progress/ locks (<1h orphans)" >> "$LOG"
python scripts_01/prompt_dispatcher.py --recover --recover-age 3600 >> "$LOG" 2>&1 || \
  echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: --recover not supported (stale dispatcher?); skipping" >> "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: prompt dispatch ($FLAG)" >> "$LOG"

python scripts_01/prompt_dispatcher.py "$FLAG" >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: prompt dispatch done" >> "$LOG"
