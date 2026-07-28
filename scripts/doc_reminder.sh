#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Doc Reminder — проверка состояния документации
#
# Использование:
#   bash scripts/doc_reminder.sh                  — проверить сейчас
#   bash scripts/doc_reminder.sh tmux             — проверить в tmux-попапе
#   bash scripts/doc_reminder.sh daemon           — запустить фоновую проверку (каждый час)
#   bash scripts/doc_reminder.sh view             — открыть TROUBLESHOOTING.md
# ============================================================

FREEBUFF="/storage/emulated/0/PROJECTS/workstation/freebuff"
CMD="${1:-check***REMOVED***"

check_docs() {
    local issues=0

    echo "📝 FreeBuff Docs Check — $(date '+%Y-%m-%d %H:%M')"
    echo ""

    # Обязательные файлы
    for f in TROUBLESHOOTING.md DECISIONS.md REFERENCES.md OVERLAY_IMPLEMENTATION.md; do
        if [ -f "$FREEBUFF/docs/$f" ***REMOVED***; then
            age=$((($(date +%s) - $(stat -c %Y "$FREEBUFF/docs/$f")) / 86400))
            echo "  ✅ docs/$f ($age дн.)"
        else
            echo "  ❌ docs/$f ОТСУТСТВУЕТ"
            issues=$((issues + 1))
        fi
    done

    # README.md
    if [ -f "$FREEBUFF/README.md" ***REMOVED***; then
        age=$((($(date +%s) - $(stat -c %Y "$FREEBUFF/README.md")) / 86400))
        if [ $age -ge 7 ***REMOVED***; then
            echo "  ⚠️ README.md ($age дн. — пора обновить)"
            issues=$((issues + 1))
        else
            echo "  ✅ README.md ($age дн.)"
        fi
    else
        echo "  ❌ README.md ОТСУТСТВУЕТ"
        issues=$((issues + 1))
    fi

    echo ""
    if [ $issues -eq 0 ***REMOVED***; then
        echo "✅ Документация в порядке"
    else
        echo "⚠️ $issues проблем(ы) — см. выше"
        # Уведомление если есть termux-notification
        if command -v termux-notification &>/dev/null; then
            termux-notification \
                --title "📝 FreeBuff: Docs" \
                --content "Найдено $issues проблем" \
                --action "bash $FREEBUFF/scripts/doc_reminder.sh view"
        else
            # Лог-файл как fallback — проверяй: cat .docs.log
            echo "  💡 Установи termux-api для уведомлений: pkg install termux-api"
            echo "[$(date '+%Y-%m-%d %H:%M')***REMOVED*** Docs: $issues проблем" >> "$FREEBUFF/.docs.log"
        fi
    fi
***REMOVED***

case "$CMD" in
    check)
        check_docs
        ;;
    tmux)
        if [ -z "$TMUX" ***REMOVED***; then
            echo "❌ Эта команда работает только внутри tmux"
            exit 1
        fi
        tmux display-popup -w 60% -h 50% -E "bash $FREEBUFF/scripts/doc_reminder.sh check; echo ''; echo 'Нажми Enter для закрытия...'; read"
        ;;
    daemon)
        # Фоновый цикл внутри tmux-сессии (переживает убийство терминала)
        SESS="doc-reminder"
        if tmux has-session -t "$SESS" 2>/dev/null; then
            echo "⚠️ Демон уже запущен (tmux session: $SESS)"
            exit 1
        fi
        echo "▶ Запуск демона документации (каждый час)"
        tmux new-session -d -s "$SESS" \
            "while true; do
                echo '[$(date \"+%H:%M\")***REMOVED*** Docs check...'
                cd $FREEBUFF
                bash scripts/doc_reminder.sh check
                sleep 3600
            done"
        echo "  tmux session: $SESS"
        echo "  Подключиться: tmux attach -t $SESS"
        echo "  Остановить:  tmux kill-session -t $SESS"
        ;;
    view)
        if [ -f "$FREEBUFF/docs/TROUBLESHOOTING.md" ***REMOVED***; then
            if command -v less &>/dev/null; then
                less "$FREEBUFF/docs/TROUBLESHOOTING.md"
            else
                cat "$FREEBUFF/docs/TROUBLESHOOTING.md"
            fi
        else
            echo "❌ TROUBLESHOOTING.md не найден"
        fi
        ;;
    *)
        echo "Использование: doc_reminder.sh [check|tmux|daemon|view***REMOVED***"
        echo "  check  — проверить документацию (по умолчанию)"
        echo "  tmux   — проверить в tmux-попапе"
        echo "  daemon — фоновый демон (каждый час, через tmux)"
        echo "  view   — открыть TROUBLESHOOTING.md"
        exit 1
        ;;
esac
