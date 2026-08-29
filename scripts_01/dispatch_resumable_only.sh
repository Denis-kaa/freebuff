#!/usr/bin/env bash
#dispatch_resumable_only.sh — Task 3 (promt 61): rapid cron poller for running/-resumable tasks.
#
#Background poller with `--resumable-only` flag: skippuser/ queue entirely
#and processes только running/-resumable tasks. Predan by crontab.
#
#Usage:
# bash scripts_01/dispatch_resumable_only.sh           # process one resumable
#bash scripts_01/dispatch_resumable_only.sh --one       # alias for default
#
#Install as crontab: `* * * * * cd /path/to/freebuff && bash scripts_01/dispatch_resumable_only.sh`
#(reduces cycle latency from 5 min (existing cron) to 1 min, but ONLY for resumable /ра-обработки TG /answer).

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"
exec python3 scripts_01/prompt_dispatcher.py \
    --resumable-only \
    --no-tg \
    --timeout=120 \
    "$@"
