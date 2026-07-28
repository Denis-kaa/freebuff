#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# FreeBuff Overlay — Termux:Float / tmux launcher
#
# Режимы запуска:
#   1. termux-float (если установлен termux-api)
#   2. tmux split (fallback — без плавающего окна)
#   3. Прямой запуск (если нет ни termux-float, ни tmux)
#
# Использование:
#   bash scripts/overlay_float.sh              # авто-выбор
#   bash scripts/overlay_float.sh float        # termux-float
#   bash scripts/overlay_float.sh tmux         # tmux
#   bash scripts/overlay_float.sh direct       # прямой запуск
#
# Горячие клавиши:
#   p — пауза     r — продолжить
#   s — стоп      q — закрыть
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FREEBUFF_ROOT="$(dirname "$SCRIPT_DIR")"
MODE="${1:-auto***REMOVED***"

cd "$FREEBUFF_ROOT" || exit 1

# ── Функция: запуск сервера ──────────────────────────────────

run_server() {
    python scripts/overlay_server.py
***REMOVED***

# ── Выбор режима ─────────────────────────────────────────────

if [ "$MODE" = "direct" ***REMOVED***; then
    echo "▶ Прямой запуск оверлея..."
    run_server
    exit $?
fi

if [ "$MODE" = "float" ***REMOVED*** || [ "$MODE" = "auto" ***REMOVED***; then
    if command -v termux-float &>/dev/null; then
        echo "▶ Запуск через Termux:Float..."
        termux-float python scripts/overlay_server.py
        exit $?
    elif [ "$MODE" = "float" ***REMOVED***; then
        echo "❌ termux-float не найден."
        echo "   1. Установи Termux:Float APK из F-Droid"
        echo "   2. Установи termux-api: pkg install termux-api"
        exit 1
    fi
fi

if [ "$MODE" = "tmux" ***REMOVED*** || [ "$MODE" = "auto" ***REMOVED***; then
    if command -v tmux &>/dev/null; then
        echo "▶ Запуск в tmux (split-панель)..."
        if tmux has-session 2>/dev/null; then
            tmux split-window -v -l 12 "python scripts/overlay_server.py"
        else
            tmux new-session -s freebuff-overlay "python scripts/overlay_server.py"
        fi
        exit $?
    elif [ "$MODE" = "tmux" ***REMOVED***; then
        echo "❌ tmux не установлен. Установи: pkg install tmux"
        exit 1
    fi
fi

# ── Fallback: ничего не подошло ──────────────────────────────

echo "▶ Прямой запуск (ни termux-float, ни tmux)..."
echo "   💡 Совет: pkg install termux-api tmux — для лучшего опыта"
echo ""
run_server
