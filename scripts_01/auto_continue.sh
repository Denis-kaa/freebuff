#!/data/data/com.termux/files/usr/bin/bash
# scripts_01/auto_continue.sh — Авто-продолжение сессии Freebuff
# Каждые 55 минут отправляет POST /api/continue на continue_endpoint.py (порт 8081).
# Также пробует tmux send-keys и termux-notification как fallback.
#
# Usage (fuseblk FS не хранит бит исполнения → запускать через bash):
#   bash scripts_01/auto_continue.sh [interval_seconds***REMOVED***
#
# Default: 3300s (55 min). Freebuff таймаут: ~60 мин.
# Перед запуском: python3 scripts_01/continue_endpoint.py --port 8081 &
# Остановка: Ctrl+C или kill PID.

set -euo pipefail

INTERVAL="${1:-3300***REMOVED***"
CONTINUE_URL="${CONTINUE_URL:-http://127.0.0.1:8081/api/continue***REMOVED***"
STATUS_URL="${STATUS_URL:-http://127.0.0.1:8081/api/status***REMOVED***"
LOG_FILE="${HOME***REMOVED***/.auto_continue.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** $*" | tee -a "$LOG_FILE"
***REMOVED***

# ─── Методы отправки Continue ─────────────────────────────────────────

# Метод 1 (основной): HTTP POST к continue_endpoint.py
continue_http() {
    local http_code
    http_code=$(curl -s -o /dev/null -w '%{http_code***REMOVED***' \
        -X POST "$CONTINUE_URL" \
        -H "Content-Type: application/json" \
        -d "{\"action\":\"continue\",\"timestamp\":\"$(date -Iseconds)\"***REMOVED***" \
        --connect-timeout 5 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ***REMOVED******REMOVED***; then
        log "✅ Continue: HTTP $http_code → $CONTINUE_URL"
        return 0
    fi
    log "⚠️  HTTP continue failed (code=$http_code)"
    return 1
***REMOVED***

# Метод 2: tmux send-keys (если сессия в tmux)
continue_tmux() {
    local tmux_session
    tmux_session=$(tmux list-sessions -F '#{session_name***REMOVED***' 2>/dev/null | head -1 || true)
    if [[ -n "$tmux_session" ***REMOVED******REMOVED***; then
        tmux send-keys -t "$tmux_session" Enter 2>/dev/null && {
            log "✅ Continue: Enter → tmux session '$tmux_session'"
            return 0
        ***REMOVED***
    fi
    return 1
***REMOVED***

# Метод 3: termux-notification (напомнить пользователю)
continue_notify() {
    if command -v termux-notification &>/dev/null; then
        termux-notification \
            --id freebuff-continue \
            --title "⏰ Freebuff — продолжить?" \
            --content "Сессия истекает. Нажми 'Продолжить' в терминале." \
            --priority high \
            --vibrate 500,200,500,200,500
        log "📱 Continue reminder → phone"
        return 0
    fi
    return 1
***REMOVED***

# ─── Главный метод ────────────────────────────────────────────────────

send_continue() {
    # Пробуем HTTP (основной канал)
    if continue_http; then return 0; fi

    # Fallback 1: tmux
    if continue_tmux; then return 0; fi

    # Fallback 2: уведомление пользователю
    if continue_notify; then return 0; fi

    log "❌ ALL continue methods failed"
    return 1
***REMOVED***

# ─── Главный цикл ─────────────────────────────────────────────────────

# Pre-flight: check endpoint is alive
if ! curl -s --connect-timeout 3 "$STATUS_URL" >/dev/null 2>&1; then
    echo "❌ Continue endpoint ($CONTINUE_URL) недоступен."
    echo "   Запусти сначала: python3 scripts_01/continue_endpoint.py --port 8081 &"
    exit 1
fi

log "🚀 Auto-continue started (interval=${INTERVAL***REMOVED***s)"
log "   HTTP endpoint: $CONTINUE_URL"
log "   Status: $STATUS_URL"
log "   PID: $$, log: $LOG_FILE"

trap 'log "🛑 Stopped."; exit 0' INT TERM

CYCLE=0
while true; do
    CYCLE=$((CYCLE + 1))
    log "--- Cycle $CYCLE ---"

    if send_continue; then
        count=$(curl -s "$STATUS_URL" --connect-timeout 3 2>/dev/null | grep -o '"continue_count":[0-9***REMOVED****' | cut -d: -f2 || echo "?")
        log "   Continue count: $count"
    fi

    log "💤 Sleeping ${INTERVAL***REMOVED***s..."
    sleep "$INTERVAL"
done
