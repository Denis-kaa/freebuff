#!/data/data/com.termux/files/usr/bin/bash
# wait_and_dispatch_all.sh — v5.89.0 (CON-33 operational follow-up)
#
# Ждёт освобождения единственного инстанса freebuff (живая интерактивная
# сессия закрыта), затем прогоняет ВСЕ задачи из user/ через диспетчер
# (--all --no-tg). Переживает закрытие сессии благодаря запуску через:
#
#     setsid nohup bash scripts_01/wait_and_dispatch_all.sh >/dev/null 2>&1 &
#
# Зачем: CON-33 backoff не даёт диспетчеру спавнить freebuff, пока живая сессия
# держит единственный инстанс. Этот watcher — мост: дождался освобождения → сразу
# прогнал очередь (не ждёт cron-тик каждые 5 мин).
#
# Лог: logs_14/dispatch_wait_and_all.log
# Страховка: cron (prompt_dispatch.sh */5) остаётся safety-net на случай сбоя watcher.

set -u

FREEBUFF_ROOT="${FREEBUFF_ROOT:-/storage/emulated/0/PROJECTS/workstation/freebuff***REMOVED***"
LOG="$FREEBUFF_ROOT/logs_14/dispatch_wait_and_all.log"
# Тот же маркер, что _LIVE_INSTANCE_PGREP_PATTERN в prompt_dispatcher.py.
# ВАЖНО: при изменении маркера в Python — обновить здесь (drift сломает watcher).
MARKER="config/manicode/freebuff"
POLL_S=10
STABLE_CHECKS=3
HEARTBEAT_S=600

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** $*" >> "$LOG"; ***REMOVED***

# Лог-директория должна существовать ДО первой записи (иначе все >> $LOG молча теряются)
mkdir -p "$(dirname "$LOG")"

log "watcher started (pid $$); polling '$MARKER' every ${POLL_S***REMOVED***s; need ${STABLE_CHECKS***REMOVED*** consecutive free checks"

free_count=0
last_heartbeat=$(date +%s)
while true; do
    if pgrep -f "$MARKER" >/dev/null 2>&1; then
        free_count=0
    else
        free_count=$((free_count + 1))
        if [ "$free_count" -ge "$STABLE_CHECKS" ***REMOVED***; then
            break
        fi
    fi
    now=$(date +%s)
    if [ $((now - last_heartbeat)) -ge "$HEARTBEAT_S" ***REMOVED***; then
        log "still waiting (free_count=$free_count); session busy or free-not-yet-confirmed"
        last_heartbeat=$now
    fi
    sleep "$POLL_S"
done

# Race safety-net: даже если новая сессия стартует между последним free-check
# и запуском диспетчера — CON-33 pre-check (_live_instance_busy) в самом
# prompt_dispatcher.py поймает занятость и вернёт backoff. STABLE_CHECKS=3
# достаточно именно потому, что диспетчер — финальный guard.
log "instance free (${STABLE_CHECKS***REMOVED*** stable checks); launching dispatch --all --no-tg"
cd "$FREEBUFF_ROOT" || exit 1
python3 scripts_01/prompt_dispatcher.py --all --no-tg >> "$LOG" 2>&1
rc=$?
log "dispatch --all finished (exit $rc)"
exit $rc
