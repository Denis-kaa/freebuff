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

# 2. run the audit, keep full output as a timestamped report
TS=$(date +%Y-%m-%d_%H%M%S)
REPORT="$LOG_DIR/report-$TS.log"
if (cd "$TRAJ_DIR" && timeout 240 python3 scripts/layout_audit.py) > "$REPORT" 2>&1; then
  log "PASS audit ok (report: $REPORT)"
else
  log "FAIL audit (report: $REPORT); last lines:"
  tail -8 "$REPORT" | sed 's/^/    /' >> "$LOG"
fi

# 3. rotate: keep the newest $KEEP reports
ls -1t "$LOG_DIR"/report-*.log 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
