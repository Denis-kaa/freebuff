#!/data/data/com.termux/files/usr/bin/bash
# monitor.sh v2 — ждёт Codebuff, отправляет промпт, завершает сессию
#
# Использование: monitor.sh <session_id> <prompt> [timeout***REMOVED*** [work_dir***REMOVED***
#
# Фаза 2-3 phase-based подхода:
#   - Ждёт приглашения Codebuff ("Enter a coding task") в tmux панели
#   - Отправляет промпт через tmux send-keys
#   - Ждёт завершения задачи
#   - По таймауту: убивает tmux сессию
#   - Запускает python3 bridge.py end <sid>

set -u

SESSION_ID="${1:-***REMOVED***"
PROMPT="${2:-***REMOVED***"
TIMEOUT="${3:-300***REMOVED***"
WORK_DIR="${4:-***REMOVED***"

FREEBUFF_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"
PLUGIN_DIR="$FREEBUFF_ROOT/freebuff_plugin_03"
SESSION_DIR="${PREFIX:-/data/data/com.termux/files/usr***REMOVED***/tmp/.freebuff_plugin"
TMUX_FILE="$SESSION_DIR/tmux_${SESSION_ID***REMOVED***"
PID_FILE="$SESSION_DIR/pid_${SESSION_ID***REMOVED***"

[ -n "$SESSION_ID" ***REMOVED*** || exit 1

# ── Читаем tmux session name ──
TMUX_SESSION=""
[ -f "$TMUX_FILE" ***REMOVED*** && TMUX_SESSION=$(cat "$TMUX_FILE" 2>/dev/null || echo "")

# ── Ждём приглашения Codebuff ──
wait_for_prompt() {
    local deadline=$(( $(date +%s) + 45 ))  # макс 45с на подключение
    while [ $(date +%s) -lt $deadline ***REMOVED***; do
        if [ -n "$TMUX_SESSION" ***REMOVED***; then
            local text
            text=$(tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null || echo "")
            # Появилось приглашение?
            if echo "$text" | grep -q "Enter a coding task\|coding task"; then
                return 0
            fi
            # Экран выбора модели? Отправляем Enter
            if echo "$text" | grep -q "RECOMMENDED\|Start coding"; then
                tmux send-keys -t "$TMUX_SESSION" Enter 2>/dev/null || true
            fi
        fi
        sleep 2
    done
    return 1
***REMOVED***

# ── Kill tmux ──
kill_tmux() {
    if [ -n "$TMUX_SESSION" ***REMOVED***; then
        tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true
        rm -f "$TMUX_FILE" 2>/dev/null || true
    fi
    if [ -f "$PID_FILE" ***REMOVED***; then
        read -r FREEBUFF_PID _ _ < "$PID_FILE" 2>/dev/null || true
        if [ -n "$FREEBUFF_PID" ***REMOVED*** && [ "$FREEBUFF_PID" -gt 0 ***REMOVED*** 2>/dev/null; then
            kill "$FREEBUFF_PID" 2>/dev/null || true
            sleep 1
            kill -9 "$FREEBUFF_PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE" 2>/dev/null || true
    fi
***REMOVED***

# ── 1. Ждём приглашения Codebuff ──
if ! wait_for_prompt; then
    # Таймаут ожидания — убиваем и выходим
    kill_tmux
    python3 "$PLUGIN_DIR/bridge.py" end "$SESSION_ID" --summary "timeout waiting for Codebuff" 2>/dev/null || true
    rm -f "$PID_FILE" "$TMUX_FILE" 2>/dev/null || true
    exit 1
fi

# ── 2. Отправляем промпт ──
if [ -n "$TMUX_SESSION" ***REMOVED*** && [ -n "$PROMPT" ***REMOVED***; then
    tmux send-keys -t "$TMUX_SESSION" "$PROMPT" Enter 2>/dev/null || true
fi

# ── 3. Ждём завершения задачи (или таймаут) ──
DEADLINE=$(( $(date +%s) + TIMEOUT ))
while [ $(date +%s) -lt $DEADLINE ***REMOVED***; do
    # Проверяем tmux
    TMUX_ALIVE=false
    if [ -n "$TMUX_SESSION" ***REMOVED***; then
        tmux has-session -t "$TMUX_SESSION" 2>/dev/null && TMUX_ALIVE=true
    fi
    # Если tmux нет — проверяем PID
    if [ "$TMUX_ALIVE" = false ***REMOVED*** && [ -f "$PID_FILE" ***REMOVED***; then
        read -r FREEBUFF_PID _ _ < "$PID_FILE" 2>/dev/null || true
        [ -n "$FREEBUFF_PID" ***REMOVED*** && [ "$FREEBUFF_PID" -gt 0 ***REMOVED*** 2>/dev/null && kill -0 "$FREEBUFF_PID" 2>/dev/null && TMUX_ALIVE=true
    fi

    if [ "$TMUX_ALIVE" = false ***REMOVED***; then
        break
    fi
    sleep 3
done

# ── 4. Таймаут? — убиваем ──
if [ -n "$TMUX_SESSION" ***REMOVED***; then
    tmux has-session -t "$TMUX_SESSION" 2>/dev/null && kill_tmux
fi

# ── 5. Очистка AGENTS.md ──
if [ -n "$WORK_DIR" ***REMOVED*** && [ -d "$WORK_DIR" ***REMOVED***; then
    [ -f "$WORK_DIR/.freebuff_original_agents" ***REMOVED*** && mv "$WORK_DIR/.freebuff_original_agents" "$WORK_DIR/AGENTS.md" 2>/dev/null || true
    [ -f "$WORK_DIR/AGENTS.md" ***REMOVED*** && rm -f "$WORK_DIR/AGENTS.md" 2>/dev/null || true
fi

# ── 6. Завершаем сессию ──
python3 "$PLUGIN_DIR/bridge.py" end "$SESSION_ID" --summary "freebuff task completed" 2>/dev/null || true

# ── 7. Финальная чистка ──
rm -f "$PID_FILE" "$TMUX_FILE" 2>/dev/null || true

exit 0
