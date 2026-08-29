#!/data/data/com.termux/files/usr/bin/env bash
# start_tgbot.sh — daemon-запуск Scenario-бота Freebuff (промт 050_13).
#
# Демонизация: nohup + setsid → процесс переживает закрытие терминала и
# Termux-kill Android. Повторный запуск идемпотентен (убивает старый инстанс).
# Паттерн — копия scripts_01/start_telegram_bot.sh (единая daemon-логика).
#
# ⚠️ ВАЖНО (nohup vs wrapper.launch): nohup применим ТОЛЬКО к TG-боту
#    (обычный Python-скрипт — безопасно). Сам Buffy (Codebuff CLI, interactive TUI)
#    НИКОГДА не запускается через прямой nohup — только через
#    `freebuff_plugin_03/wrapper.py::launch()/launch_and_wait()` (tmux + .freebuff_result).
#
# Usage:
#   bash scripts_01/start_tgbot.sh
# Requirements:
#   TELEGRAM_BOT_TOKEN must be set in the environment or in .env

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"

LOG="$WORKSPACE/logs_14/tgbot.log"
mkdir -p "$WORKSPACE/logs_14"

if [ -f .env ***REMOVED***; then
    # shellcheck disable=SC1091
    set -a
    # shellcheck disable=SC1091
    . .env
    set +a
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-***REMOVED***" ***REMOVED***; then
    echo "❌ TELEGRAM_BOT_TOKEN is not set."
    echo "Get a token from @BotFather and either:"
    echo "  export TELEGRAM_BOT_TOKEN=xxx"
    echo "or add it to $WORKSPACE/.env"
    exit 1
fi

echo "🤖 Starting Freebuff Plugin Telegram Bot..."
echo "   REST API for scenarios: http://127.0.0.1:8410/scenarios"
echo "   Bot commands: /start /scenarios /scenarios_list /scenarios_apply /scenarios_search"
echo ""

# Идемпотентность: останавливаем старый инстанс, если висит.
pkill -f 'tgbot.py' 2>/dev/null || true
sleep 1

# Демонизация: nohup (SIGHUP-устойчивость) + setsid (новая сессия, без TTY).
# stdin из /dev/null — бот не читает терминал; stdout/stderr → tgbot.log.
nohup env PYTHONPATH="$WORKSPACE" python freebuff_plugin_03/tgbot.py \
  >> "$LOG" 2>&1 < /dev/null &
BOT_PID=$!
disown 2>/dev/null || true

echo "🤖 Scenario-бот запущен: pid=$BOT_PID log=$LOG"

# Проверка живучести: даём боту несколько секунд на старт polling'а.
sleep 2
ALIVE_PID="$(pgrep -f 'tgbot.py' | head -1 || true)"
if [ -n "$ALIVE_PID" ***REMOVED***; then
    echo "✅ Scenario-бот жив: pid=$ALIVE_PID"
    exit 0
else
    echo "❌ Scenario-бот не поднялся за 2s — смотри $LOG"
    exit 1
fi
