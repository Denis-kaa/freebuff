#!/usr/bin/env bash
#
# Nightly layout audit of the deployed Freeстарт presentation (:8022).
# Installed on whimco via cron (marker: freestart-layout-audit).
#
# Design notes:
# - Invoked as `/bin/bash <path>` → no exec-bit dependency (CON: auto_deploy
#   lost +x on fresh checkouts; /bin/bash invocation is immune).
# - Reports + summary live in /var/log/freebuff-layout-audit/ (outside the
#   git tree — untracked files inside /opt/freebuff would interfere with
#   the auto-deploy fast-forward).
# - layout_audit.py exits non-zero on layout defects; every run leaves a
#   timestamped report, summary lines go to nightly.log, reports rotate.
set -u

TRAJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR=/var/log/freebuff-layout-audit
KEEP=14

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# 1. site-up guard: audit is meaningless (and noisy) if nginx is down
HTTP=$(curl -s -o /dev/null -m 15 -w '%{http_code}' http://127.0.0.1:8022/ || echo 000)
if [ "$HTTP" != "200" ]; then
  log "FAIL site :8022 → HTTP $HTTP (audit skipped)"
  exit 1
fi

# 2. layout audit (exit non-zero on layout defects)
TS=$(date +%Y-%m-%d_%H%M%S)
REPORT="$LOG_DIR/report-$TS.log"
if (cd "$TRAJ_DIR" && timeout 240 python3 scripts/layout_audit.py) > "$REPORT" 2>&1; then
  log "PASS layout audit ok (report: $REPORT)"
else
  log "FAIL layout audit (report: $REPORT); last lines:"
  tail -8 "$REPORT" | sed 's/^/    /' >> "$LOG"
fi

# 3. media/console pass: screenshots + console/page errors + video motion
#    (--strict: exit 1 on any console/page error, failed request, paused or
#     non-advancing video, or missing shots)
MEDIA_REPORT="$LOG_DIR/media-$TS.json"
if (cd "$TRAJ_DIR" && timeout 300 python3 scripts/screenshots.py --report "$MEDIA_REPORT" --strict) > "$LOG_DIR/media-$TS.log" 2>&1; then
  log "PASS media/console ok (report: $MEDIA_REPORT)"
else
  log "FAIL media/console (report: $MEDIA_REPORT); last lines:"
  tail -8 "$LOG_DIR/media-$TS.log" | sed 's/^/    /' >> "$LOG"
fi

# 4. rotate: keep the newest $KEEP reports of each kind
ls -1t "$LOG_DIR"/report-*.log  2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -1t "$LOG_DIR"/media-*.log   2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
ls -1t "$LOG_DIR"/media-*.json 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
