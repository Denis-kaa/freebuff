#!/data/data/com.termux/files/usr/bin/env bash
# Start the Freebuff Telegram bot in the current workspace.
# Usage:
#   bash scripts/start_telegram_bot.sh
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

PYTHONPATH="$WORKSPACE" exec python scripts/telegram_bot.py
