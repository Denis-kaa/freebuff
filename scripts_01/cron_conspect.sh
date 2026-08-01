#!/data/data/com.termux/files/usr/bin/bash
# cron_conspect.sh — автосуммаризация сессий Freebuff
# Добавить в crontab:
#   crontab -e
#   */30 * * * * /data/data/com.termux/files/home/storage/shared/PROJECTS/workstation/freebuff/scripts_01/cron_conspect.sh

FREEBUFF="/storage/emulated/0/PROJECTS/workstation/freebuff"
LOG="$FREEBUFF/logs_14/cron.log"

cd "$FREEBUFF" || exit 1
mkdir -p "$FREEBUFF/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: auto-conspect" >> "$LOG"

# Суммаризируем активные сессии (без demo-режима)
python scripts_01/auto_conspect.py >> "$LOG" 2>&1

# Ежедневная проверка дрейфа документации/кода (внутри rate-limit once/day)
python scripts_01/drift_check.py >> "$LOG" 2>&1

# Проверяем здоровье
python -c "
from scripts.system_monitor import health_check
h = health_check()
if not h['memory_ok'***REMOVED***:
    print('WARNING: Low memory!')
" >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** Cron: done" >> "$LOG"
