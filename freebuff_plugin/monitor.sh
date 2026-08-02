#!/usr/bin/env bash
# freebuff_plugin/monitor.sh — DEPRECATED COMPATIBILITY SHIM.
#
# Канонический путь: freebuff_plugin_03/monitor.sh (NN-name scheme).
# Этот файл сохранён для совместимости со stale-вызывающими
# (bash history / tmux send-keys, зафиксировавшими путь до ренейма
# директорий в Этап 4 консолидации). Используйте канонический путь.
#
# Поведение: warning в stderr → exec bash <canonical> "$@"
# Коды возврата: 127, если canonical отсутствует; иначе — exit canonical.
#
# Переносимость: shebang `env bash` + FREEBUFF_ROOT выводится из BASH_SOURCE,
# поэтому shim работает в Termux (прод-окружение) и CI/Linux/macOS одинаково
# (на не-Termux запусках canonical не требуется — `exec bash` подхватит PATH).

# Resolve our own directory → workspace root (one level up from freebuff_plugin/).
SHIM_PATH="${BASH_SOURCE[0***REMOVED***:-$0***REMOVED***"
SHIM_DIR="$(cd "$(dirname "$SHIM_PATH")" && pwd)"
FREEBUFF_ROOT_RESOLVED="$(cd "$SHIM_DIR/.." && pwd)"
FREEBUFF_ROOT="${FREEBUFF_ROOT:-$FREEBUFF_ROOT_RESOLVED***REMOVED***"
CANONICAL="$FREEBUFF_ROOT/freebuff_plugin_03/monitor.sh"

echo "⚠️  DEPRECATED shim: используйте $CANONICAL" >&2

if [ ! -f "$CANONICAL" ***REMOVED***; then
    echo "❌ freebuff_plugin/monitor.sh: канонический скрипт не найден: $CANONICAL" >&2
    exit 127
fi

exec bash "$CANONICAL" "$@"
