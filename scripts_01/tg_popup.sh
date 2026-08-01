#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Telegram Popup Overlay — быстрый доступ к TG без переключения
#
# Использование:
#   bash scripts_01/tg_popup.sh          ← открыть TG поверх всего
#   bash scripts_01/tg_popup.sh start    ← запустить TG в фоне
#   bash scripts_01/tg_popup.sh kill     ← остановить фоновый TG
#
# В попапе:
#   ↑↓ Enter — выбрать чат и читать
#   Ctrl+F   — отправить сообщение
#   Ctrl+S   — поиск по чатам
#   Ctrl+Q   — закрыть попап и вернуться
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FREEBUFF_ROOT="$(dirname "$SCRIPT_DIR")"
TG_DIR="$FREEBUFF_ROOT/projects_17/tg_terminal_messenger"
SESSION="tg-bg"

CMD="${1:-popup***REMOVED***"

# ── Запуск фоновой сессии ──────────────────────────────────

start_bg() {
    tmux start-server 2>/dev/null

    if tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "▶ Telegram уже запущен в фоне (сессия: $SESSION)"
        return 0
    fi

    # ── Самоисцеление: убиваем orphaned python, чистим лок-файлы ──
    kill -9 $(ps aux 2>/dev/null | grep 'python.*src_06/ui/app' | awk '{print $2***REMOVED***') 2>/dev/null || true
    rm -f "$TG_DIR"/tg_session.session.lock "$TG_DIR"/tg_session.session-journal \
          "$TG_DIR"/tg_session.session-wal "$TG_DIR"/tg_session.session-shm 2>/dev/null

    echo "▶ Запускаю Telegram в фоне..."
    cd "$TG_DIR" || exit 1
    tmux new-session -d -s "$SESSION" \
        "TERM=xterm-256color python src_06/ui/app.py; echo 'TG_STOPPED'; sleep 300"

    # Ждём загрузку
    echo -n "   Подключение"
    for i in {1..10***REMOVED***; do
        sleep 0.5
        echo -n "."
        if tmux capture-pane -t "$SESSION" -p 2>/dev/null | strings | grep -q '👤'; then
            echo " готов!"
            return 0
        fi
    done
    echo " (фон)"
    return 0
***REMOVED***

# ── Открытие попапа ────────────────────────────────────────

open_popup() {
    start_bg

    if [ -n "$TMUX" ***REMOVED***; then
        # Внутри tmux — показываем компактный попап справа-снизу
        echo "▶ Telegram (Ctrl+Q — закрыть)"
        tmux display-popup \
            -w 55% -h 65% \
            -x 42% -y 30% \
            -b rounded \
            -E "tmux attach -t $SESSION"
        echo "▶ Вернулся!"
    else
        # Не в tmux — создаём временную сессию для попапа
        echo "▶ Telegram (Ctrl+Q — вернуться)"
        tmux kill-session -t _tg_wrapper 2>/dev/null
        tmux new-session -s _tg_wrapper \
            "tmux display-popup -w 55% -h 65% -x 42% -y 30% -b rounded -E \"tmux attach -t $SESSION\""
        echo "▶ Вернулся!"
    fi
***REMOVED***

# ── Остановка ──────────────────────────────────────────────

kill_bg() {
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "✅ Telegram остановлен" || echo "⚠️ Сессия не найдена"
***REMOVED***

# ── Main ───────────────────────────────────────────────────

case "$CMD" in
    popup)   open_popup ;;
    start)   start_bg ;;
    kill)    kill_bg ;;
    *)
        echo "Использование: tg_popup.sh [popup|start|kill***REMOVED***"
        echo "  popup  — открыть TG как оверлей (по умолчанию)"
        echo "  start  — запустить TG в фоне"
        echo "  kill   — остановить TG"
        exit 1
        ;;
esac
