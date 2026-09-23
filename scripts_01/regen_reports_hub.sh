#!/usr/bin/env bash
# regen_reports_hub.sh — перегенерация сайта Reports Hub (services_08/reports_hub).
#
# Гвард: stamp-файл хранит HEAD последней успешной генерации. Если HEAD не
# изменился — тихий выход, поэтому скрипт дёшево вызывать хоть каждые 5 минут.
# При ошибке генерации stamp НЕ обновляется — следующая попытка через cron.
#
# Триггеры (SYNC_RUNBOOK §1b):
#   1. auto_deploy.sh deploy_steps() — после каждого pull (post-merge hook);
#   2. cron-строка «# reports-hub-regen» — ловит локальные коммиты на сервере.
#
# Ручной запуск: bash scripts_01/regen_reports_hub.sh [--force]

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$REPO_ROOT/services_08/reports_hub/site/.last_regen"
LOG="${REGEN_LOG:-/var/log/freebuff-reports-regen.log}"
PY="${REGEN_PYTHON:-/opt/printcalc-venv/bin/python}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

HEAD_NOW="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
if [ "${1:-}" != "--force" ] && [ -f "$STAMP" ] && [ "$(cat "$STAMP" 2>/dev/null)" = "$HEAD_NOW" ]; then
  exit 0  # сайт уже соответствует HEAD
fi

mkdir -p "$(dirname "$STAMP")"
log "regen start (HEAD $HEAD_NOW)"
if ( cd "$REPO_ROOT" && "$PY" -m services_08.reports_hub generate --all --platform ) >>"$LOG" 2>&1; then
  echo "$HEAD_NOW" > "$STAMP"
  log "regen OK"
else
  log "ERROR: generate failed — stamp not updated (retry on next trigger)"
  exit 1
fi
