#!/data/data/com.termux/files/usr/bin/bash
# oom_protect.sh — защита от OOM/Signal 9 в Termux
#
# Использование:
#   bash scripts/oom_protect.sh          # проверить и почистить
#   bash scripts/oom_protect.sh --force  # принудительно убить все freebuff
#   bash scripts/oom_protect.sh --status # только показать статус
#
# Что делает:
#   1. Проверяет MemAvailable из /proc/meminfo
#   2. Убивает старые freebuff (Codebuff CLI) процессы
#   3. Чистит зависшие tmux сессии
#   4. Чистит мусорные PID-файлы плагина
#
# Принцип: держим минимум 512 MB свободной памяти,
# иначе убиваем самые жирные процессы.

set -u

SELF_PID=$$
SCRIPT_NAME="${0##*/***REMOVED***"
MIN_MEM_KB=$((512 * 1024))  # 512 MB
CRITICAL_MEM_KB=$((256 * 1024))  # 256 MB

# ── Цветной вывод ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN***REMOVED***[OOM***REMOVED***${NC***REMOVED*** $*"; ***REMOVED***
warn()  { echo -e "${YELLOW***REMOVED***[OOM***REMOVED***${NC***REMOVED*** $*"; ***REMOVED***
error() { echo -e "${RED***REMOVED***[OOM***REMOVED***${NC***REMOVED*** $*" >&2; ***REMOVED***

# ── Функции ──

get_mem_kb() {
    # Возвращает MemAvailable в kB
    local mem
    mem=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2***REMOVED***')
    echo "${mem:-0***REMOVED***"
***REMOVED***

get_memfree_kb() {
    # Возвращает MemFree в kB
    local mem
    mem=$(grep MemFree /proc/meminfo 2>/dev/null | awk '{print $2***REMOVED***')
    echo "${mem:-0***REMOVED***"
***REMOVED***

kill_old_freebuff() {
    # Убивает ВСЕ freebuff процессы, кроме:
    # - самого себя (bash)
    # - Python процессов с нашими скриптами
    # - tmux сессий (их чистим отдельно)
    local killed=0

    # Ищем бинарники Codebuff CLI
    while IFS= read -r line; do
        pid=$(echo "$line" | awk '{print $2***REMOVED***')
        rss=$(echo "$line" | awk '{print $6***REMOVED***')
        cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""***REMOVED***')

        # Не убиваем себя
        [ "$pid" = "$SELF_PID" ***REMOVED*** && continue
        [ "$pid" -le 1 ***REMOVED*** && continue

        # Не убиваем python процессы (наши скрипты)
        echo "$cmd" | grep -qE "^python|python3" && continue
        # Не убиваем tmux
        echo "$cmd" | grep -q "tmux" && continue
        # Не убиваем bash (обёртки)
        echo "$cmd" | grep -qE "^bash$|^/.*/bash$" && continue
        # Не убиваем proot (умрёт сам, когда Codebuff убьём)
        echo "$cmd" | grep -q "proot-distro\|proot " && continue
        # Не убиваем наш oom_protect.sh
        echo "$cmd" | grep -q "oom_protect" && continue

        # Проверяем, что это действительно бинарник freebuff/Codebuff
        if echo "$cmd" | grep -q "manicode/freebuff\|codebuff\|freebuff_cli"; then
            warn "Убиваю freebuff PID=$pid (RSS=${rss:-?***REMOVED*** kB, cmd: ${cmd:0:60***REMOVED***)"
            kill "$pid" 2>/dev/null || true
            sleep 0.5
            kill -9 "$pid" 2>/dev/null || true
            killed=$((killed + 1))
        fi
    done < <(ps aux 2>/dev/null | grep -v "grep\|defunct" || true)

    return $killed
***REMOVED***

clean_tmux_sessions() {
    # Убивает зависшие tmux сессии, кроме текущей (если внутри tmux)
    local cleaned=0
    local current_session=""
    [ -n "${TMUX:-***REMOVED***" ***REMOVED*** && current_session=$(tmux display-message -p '#{session_name***REMOVED***' 2>/dev/null || echo "")

    # Собираем все сессии в список, чтобы избежать subshell
    local sessions=""
    sessions=$(tmux list-sessions -F "#{session_name***REMOVED***" 2>/dev/null || echo "")
    
    local s
    for s in $sessions; do
        [ -z "$s" ***REMOVED*** && continue
        if echo "$s" | grep -q "^fb_"; then
            if [ "$s" != "$current_session" ***REMOVED***; then
                tmux kill-session -t "$s" 2>/dev/null || true
                cleaned=$((cleaned + 1))
            fi
        fi
    done

    # Также убиваем любые старые сессии без клиентов
    for s in $sessions; do
        [ -z "$s" ***REMOVED*** && continue
        [ "$s" = "$current_session" ***REMOVED*** && continue
        local attached
        attached=$(tmux list-clients -t "$s" 2>/dev/null | wc -l)
        if [ "$attached" -eq 0 ***REMOVED***; then
            tmux kill-session -t "$s" 2>/dev/null || true
            cleaned=$((cleaned + 1))
        fi
    done

    return $cleaned
***REMOVED***

clean_plugin_pidfiles() {
    # Чистит PID-файлы для мёртвых процессов
    local cleaned=0
    local sess_dir="${PREFIX:-/data/data/com.termux/files/usr***REMOVED***/tmp/.freebuff_plugin"

    [ ! -d "$sess_dir" ***REMOVED*** && return 0

    for f in "$sess_dir"/pid_* "$sess_dir"/tmux_*; do
        [ ! -f "$f" ***REMOVED*** && continue
        # Читаем PID из файла
        local pid_val
        pid_val=$(head -1 "$f" 2>/dev/null || echo "0")
        # Проверяем только числовые PID
        if echo "$pid_val" | grep -qE '^[0-9***REMOVED***+$'; then
            if ! kill -0 "$pid_val" 2>/dev/null; then
                rm -f "$f" 2>/dev/null || true
                cleaned=$((cleaned + 1))
            fi
        else
            # tmux_ файлы содержат имя сессии, не PID
            local sname="$pid_val"
            if ! tmux has-session -t "$sname" 2>/dev/null; then
                rm -f "$f" 2>/dev/null || true
                cleaned=$((cleaned + 1))
            fi
        fi
    done

    return $cleaned
***REMOVED***

show_status() {
    local mem_avail mem_free swap_total swap_free
    mem_avail=$(get_mem_kb)
    mem_free=$(get_memfree_kb)
    swap_total=$(grep SwapTotal /proc/meminfo 2>/dev/null | awk '{print $2***REMOVED***')
    swap_free=$(grep SwapFree /proc/meminfo 2>/dev/null | awk '{print $2***REMOVED***')

    echo "=== ПАМЯТЬ ==="
    echo "MemAvailable:   $((mem_avail / 1024)) MB"
    echo "MemFree:        $((mem_free / 1024)) MB"
    echo "Swap:           $(( (swap_total - swap_free) / 1024 )) / $((swap_total / 1024)) MB used"
    echo ""

    echo "=== FREEBUFF ПРОЦЕССЫ ==="
    local fb_count=0
    while IFS= read -r line; do
        pid=$(echo "$line" | awk '{print $2***REMOVED***')
        rss=$(echo "$line" | awk '{print $6***REMOVED***')
        cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""***REMOVED***' | head -c 80)
        if [ -n "$pid" ***REMOVED*** && [ "$pid" != "PID" ***REMOVED***; then
            echo "  PID=$pid RSS=$((rss / 1024))MB cmd: $cmd"
            fb_count=$((fb_count + 1))
        fi
    done < <(ps aux 2>/dev/null | grep -E "manicode/freebuff|freebuff_cli" | grep -v grep | head -10)
    [ "$fb_count" -eq 0 ***REMOVED*** && echo "  (нет запущенных)"
    echo ""

    echo "=== TMUX СЕССИИ ==="
    local tmux_count=0
    for s in $(tmux list-sessions -F "#{session_name***REMOVED***" 2>/dev/null || true); do
        local attached
        attached=$(tmux list-clients -t "$s" 2>/dev/null | wc -l)
        echo "  $s (clients: $attached)"
        tmux_count=$((tmux_count + 1))
    done
    [ "$tmux_count" -eq 0 ***REMOVED*** && echo "  (нет сессий)"

    echo ""
    echo "=== ПЛАГИН PID-файлы ==="
    local sess_dir="${PREFIX:-/data/data/com.termux/files/usr***REMOVED***/tmp/.freebuff_plugin"
    if [ -d "$sess_dir" ***REMOVED***; then
        ls -la "$sess_dir"/ 2>/dev/null | grep -v "^total" | grep -v "^\.$" | grep -v "^\.\.$" || echo "  (пусто)"
    else
        echo "  (нет директории)"
    fi

    # Вердикт
    echo ""
    if [ "$mem_avail" -lt "$CRITICAL_MEM_KB" ***REMOVED***; then
        error "КРИТИЧЕСКИ: MemAvailable ${mem_avail***REMOVED***kB < ${CRITICAL_MEM_KB***REMOVED***kB — риск OOM!"
    elif [ "$mem_avail" -lt "$MIN_MEM_KB" ***REMOVED***; then
        warn "ВНИМАНИЕ: MemAvailable ${mem_avail***REMOVED***kB < ${MIN_MEM_KB***REMOVED***kB — рекомендуется очистка"
    else
        info "OK: MemAvailable ${mem_avail***REMOVED***kB >= ${MIN_MEM_KB***REMOVED***kB"
    fi
***REMOVED***

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

MODE="${1:-check***REMOVED***"

case "$MODE" in
    --status|-s)
        show_status
        exit 0
        ;;
    --force|-f)
        warn "Принудительная очистка всех freebuff процессов..."
        kill_old_freebuff
        clean_tmux_sessions
        clean_plugin_pidfiles
        info "Очистка завершена"
        show_status
        exit 0
        ;;
    check|--check|-c|"")
        mem_avail=$(get_mem_kb)
        mem_free=$(get_memfree_kb)

        # Статус
        echo "[OOM***REMOVED*** MemAvailable: $((mem_avail / 1024)) MB | MemFree: $((mem_free / 1024)) MB | Threshold: $((MIN_MEM_KB / 1024)) MB"

        # Если памяти достаточно — только чистим PID-файлы
        if [ "$mem_avail" -ge "$MIN_MEM_KB" ***REMOVED***; then
            clean_plugin_pidfiles
            exit 0
        fi

        # Памяти мало — убиваем старые freebuff
        warn "MemAvailable ($((mem_avail / 1024)) MB) ниже порога ($((MIN_MEM_KB / 1024)) MB)"
        warn "Очищаю память..."

        # Сначала чистим PID-файлы и tmux
        clean_tmux_sessions
        clean_plugin_pidfiles

        # Убиваем freebuff
        kill_old_freebuff

        # Финальная проверка
        sleep 0.5
        mem_after=$(get_mem_kb)
        info "MemAvailable после очистки: $((mem_after / 1024)) MB"

        # Если всё ещё критично — предупреждаем
        if [ "$mem_after" -lt "$CRITICAL_MEM_KB" ***REMOVED***; then
            error "Памяти всё ещё критически мало ($((mem_after / 1024)) MB). Рекомендуется закрыть другие приложения."
            exit 1
        fi

        info "Очистка завершена OK"
        exit 0
        ;;
    *)
        echo "Использование: $0 [--status|--force|--check***REMOVED***"
        exit 1
        ;;
esac
