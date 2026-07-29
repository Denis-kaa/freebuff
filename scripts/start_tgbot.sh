#!/data/data/com.termux/files/usr/bin/env bash
# Start the Freebuff Plugin Telegram Bot (Scenario Engine integration).
# Usage:
#   bash scripts/start_tgbot.sh
# Requirements:
#   TELEGRAM_BOT_TOKEN must be set in the environment or in .env

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"

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

PYTHONPATH="$WORKSPACE" exec python freebuff_plugin/tgbot.py
