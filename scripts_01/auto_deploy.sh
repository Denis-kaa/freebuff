#!/usr/bin/env bash
# auto_deploy.sh — server-side pull-on-push deploy (whimco pattern).
#
# Makes a server copy of this repository track origin/master automatically:
#   1. post-merge git hook  — runs the deploy steps after every successful pull
#   2. cron poller          — pulls every N minutes, so pushes are picked up
#                             even when nothing else triggers a fetch
#
# Deploy steps after each pull (edit DEPLOY_CMD below or override with env):
#   - keep .env / data_13/ / context_12/ untouched (they are gitignored)
#   - run DEPLOY_CMD (default: none — the checkout itself is the deploy)
#
# Usage (run ON THE SERVER, from the repo copy):
#   bash scripts_01/auto_deploy.sh install [--interval 5] [--branch master]
#   bash scripts_01/auto_deploy.sh remove
#   bash scripts_01/auto_deploy.sh status
#   bash scripts_01/auto_deploy.sh pull        # one manual pull + deploy steps
#
# Env overrides:
#   DEPLOY_CMD   command run after each successful pull (default: empty)
#   DEPLOY_LOG   log file (default: /var/log/freebuff-autodeploy.log)

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${DEPLOY_BRANCH:-master}"
INTERVAL="${DEPLOY_INTERVAL:-5}"
DEPLOY_CMD="${DEPLOY_CMD:-}"
DEPLOY_LOG="${DEPLOY_LOG:-/var/log/freebuff-autodeploy.log}"
HOOK_DST="$REPO_ROOT/.git/hooks/post-merge"
CRON_MARKER="# freebuff-autodeploy"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$DEPLOY_LOG" >&2; }

deploy_steps() {
  log "deploy steps start"
  if [ -n "$DEPLOY_CMD" ]; then
    ( cd "$REPO_ROOT" && eval "$DEPLOY_CMD" ) >>"$DEPLOY_LOG" 2>&1 \
      || log "WARN: DEPLOY_CMD failed"
  fi
  log "deploy steps done"
}

do_pull() {
  cd "$REPO_ROOT" || exit 1
  # Only pull when the working tree is clean of tracked changes; server data
  # (.env, DBs) is gitignored so checkout never touches it.
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    log "SKIP: tracked local changes present, not pulling"
    exit 0
  fi
  git fetch origin "$BRANCH" >>"$DEPLOY_LOG" 2>&1 || { log "fetch failed"; exit 1; }
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse "origin/$BRANCH")
  if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0  # already up to date — silent
  fi
  log "pulling $LOCAL -> $REMOTE"
  git merge --ff-only "origin/$BRANCH" >>"$DEPLOY_LOG" 2>&1 \
    || { log "ERROR: fast-forward failed, manual intervention needed"; exit 1; }
  # post-merge hook runs deploy_steps automatically on a real merge
}

install_hook() {
  cat > "$HOOK_DST" <<'HOOK'
#!/usr/bin/env bash
# installed by scripts_01/auto_deploy.sh
"$(git rev-parse --show-toplevel)/scripts_01/auto_deploy.sh" hook-post-merge
HOOK
  chmod +x "$HOOK_DST"
  log "post-merge hook installed: $HOOK_DST"
}

install_cron() {
  local cron_line="*/$INTERVAL * * * * cd $REPO_ROOT && bash scripts_01/auto_deploy.sh pull $CRON_MARKER"
  ( crontab -l 2>/dev/null | grep -v "$CRON_MARKER"; echo "$cron_line" ) | crontab -
  log "cron poller installed (every $INTERVAL min)"
}

case "${1:-}" in
  install)
    [ -d "$REPO_ROOT/.git" ] || { echo "ERROR: $REPO_ROOT is not a git repo"; exit 1; }
    while [ $# -gt 0 ]; do
      case "$1" in
        --interval) INTERVAL="$2"; shift 2 ;;
        --branch)   BRANCH="$2";   shift 2 ;;
        *) shift ;;
      esac
    done
    install_hook
    install_cron
    log "auto-deploy installed (branch=$BRANCH interval=${INTERVAL}min)"
    ;;
  remove)
    rm -f "$HOOK_DST"
    ( crontab -l 2>/dev/null | grep -v "$CRON_MARKER" ) | crontab -
    log "auto-deploy removed"
    ;;
  status)
    echo "repo:        $REPO_ROOT"
    echo "branch:      $BRANCH"
    echo "hook:        $([ -x "$HOOK_DST" ] && echo installed || echo missing)"
    echo "cron:        $(crontab -l 2>/dev/null | grep -c "$CRON_MARKER") job(s)"
    echo "local HEAD:  $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null)"
    echo "origin:      $(git -C "$REPO_ROOT" rev-parse --short "origin/$BRANCH" 2>/dev/null)"
    ;;
  pull)
    do_pull
    ;;
  hook-post-merge)
    deploy_steps
    ;;
  *)
    echo "usage: $0 {install [--interval N] [--branch B] | remove | status | pull}"
    exit 1
    ;;
esac
