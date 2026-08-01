#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# Screenshot Tools — просмотр и анализ скриншотов
#
# Папка: /storage/emulated/0/Pictures/Screenshots/
#
# Использование:
#   bash scripts_01/screenshot_tools.sh              — последние 5 скриншотов
#   bash scripts_01/screenshot_tools.sh last         — последний
#   bash scripts_01/screenshot_tools.sh list [N***REMOVED***     — последние N
#   bash scripts_01/screenshot_tools.sh info [file***REMOVED***  — детали файла
#   bash scripts_01/screenshot_tools.sh copy         — скопировать последний в /tmp
# ============================================================

SCREENSHOTS="/storage/emulated/0/Pictures/Screenshots"
CMD="${1:-list***REMOVED***"
COUNT="${2:-5***REMOVED***"

case "$CMD" in
    list)
        echo "📸 Последние $COUNT скриншотов:"
        echo ""
        i=0
        for f in $(ls -t "$SCREENSHOTS"/*.png 2>/dev/null); do
            [ $i -ge "$COUNT" ***REMOVED*** && break
            i=$((i + 1))
            base=$(basename "$f")
            sz=$(stat -c %s "$f" | numfmt --to=iec 2>/dev/null || stat -c '%s B' "$f")
            dt=$(stat -c '%y' "$f" | cut -d'.' -f1)
            printf "  %-36s %8s  %s\n" "$base" "$sz" "$dt"
        done
        echo ""
        echo "Всего: $(ls -1 "$SCREENSHOTS"/*.png 2>/dev/null | wc -l) скриншотов"
        ;;
    last)
        latest=$(ls -t "$SCREENSHOTS"/*.png 2>/dev/null | head -1)
        if [ -z "$latest" ***REMOVED***; then
            echo "❌ Нет скриншотов"
            exit 1
        fi
        sz=$(stat -c %s "$latest" | numfmt --to=iec 2>/dev/null || stat -c '%s bytes' "$latest")
        echo "📸 Последний скриншот:"
        echo "  Файл: $(basename "$latest")"
        echo "  Размер: $sz"
        echo "  Дата: $(stat -c '%y' "$latest")"
        echo "  Тип: $(file -b "$latest")"
        echo "  Путь: $latest"
        ;;
    info)
        if [ -n "$2" ***REMOVED***; then
            FILE="$2"
        else
            FILE=$(ls -t "$SCREENSHOTS"/*.png 2>/dev/null | head -1)
        fi
        if [ ! -f "$FILE" ***REMOVED***; then
            echo "❌ Файл не найден: $FILE"
            exit 1
        fi
        echo "📄 Информация о файле:"
        echo "  Имя: $(basename "$FILE")"
        echo "  Путь: $FILE"
        echo "  Размер: $(stat -c %s "$FILE" | numfmt --to=iec)"
        echo "  Дата: $(stat -c '%y' "$FILE")"
        echo "  Тип: $(file -b "$FILE")"
        ;;
    copy)
        latest=$(ls -t "$SCREENSHOTS"/*.png 2>/dev/null | head -1)
        if [ -z "$latest" ***REMOVED***; then
            echo "❌ Нет скриншотов"
            exit 1
        fi
        cp "$latest" /tmp/latest_screenshot.png
        echo "✅ Скопирован в /tmp/latest_screenshot.png ($(stat -c %s /tmp/latest_screenshot.png) bytes)"
        ;;
    *)
        echo "Использование: screenshot_tools.sh [list|last|info|copy***REMOVED*** [N***REMOVED***"
        echo "  list [N***REMOVED*** — последние N скриншотов (по умолч. 5)"
        echo "  last     — детали последнего"
        echo "  info [f***REMOVED*** — детали файла"
        echo "  copy     — скопировать последний в /tmp"
        exit 1
        ;;
esac
