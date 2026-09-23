#!/usr/bin/env bash
# regcloud_tunnel.sh — reverse-tunnel whimco → reg.cloud (без VPN).
#
# ЗАЧЕМ: whimco (185.233.184.192, NL) недоступен напрямую без VPN (даже :22).
# Исходящий SSH с whimco работает всегда → whimco сам поднимает реверс-туннель
# к бесплатному RU VPS reg.cloud (195.19.195.143) и публикует там свои порты:
#
#   195.19.195.143:10022 → whimco:22    (SSH — вход без VPN)
#   195.19.195.143:10080 → whimco:8300  (printcalc web)
#
# Триггер: auto_deploy.sh deploy_steps() после каждого pull (крон каждые 5 мин),
# т.е. скрипт самовосстанавливается: упал туннель → следующий pull поднимет.
#
# Ключи: при первом запуске генерируется dedicated key /root/.ssh/regcloud_tunnel_key;
# его pubkey выкладывается в репо (docs_10/runbook/regcloud_tunnel.pub), откуда
# его добавляет в authorized_keys на VPS оператор/агент (однократно).
#
# На VPS требуется: GatewayPorts clientspecified (иначе -R биндится только на 127.0.0.1).
#
# Usage:
#   bash scripts_01/regcloud_tunnel.sh ensure    # идемпотентно: ключ+туннель (вызывается из deploy_steps)
#   bash scripts_01/regcloud_tunnel.sh status    # pubkey, состояние туннеля, порты
#   bash scripts_01/regcloud_tunnel.sh stop      # остановить loop и туннель
#
# ⚠️ После подъёма туннеля :22 выставлен наружу (через VPS) — на whimco стоит
# fail2ban; при скан-шторме добавить ignoreip для 195.19.195.143:
#   fail2ban-client set sshd addignoreip 195.19.195.143

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VPS_HOST="${REGCLOUD_VPS:-195.19.195.143}"
VPS_USER="${REGCLOUD_VPS_USER:-tunnel}"
VPS_PORT="${REGCLOUD_VPS_PORT:-22}"
SSH_PORT_BIND="${REGCLOUD_SSH_BIND:-10022}"      # VPS-порт → whimco:22
WEB_PORT_BIND="${REGCLOUD_WEB_BIND:-10080}"      # VPS-порт → whimco:8300
WEB_LOCAL_PORT="${REGCLOUD_WEB_LOCAL:-8300}"

PRIVKEY="/root/.ssh/regcloud_tunnel_key"
PUBKEY_OUT="/tmp/regcloud_tunnel_key.pub"
PUBKEY_REPO="$REPO_ROOT/docs_10/runbook/regcloud_tunnel.pub"
STATE_DIR="/run/regcloud-tunnel"
PIDFILE="$STATE_DIR/loop.pid"
LOG="${REGCLOUD_TUNNEL_LOG:-/var/log/freebuff-regcloud-tunnel.log}"
LOOP_INTERVAL="${REGCLOUD_TUNNEL_INTERVAL:-60}"
KNOWN="/root/.ssh/known_hosts_regcloud"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [regcloud-tunnel] $*" | tee -a "$LOG" >&2; }

SSH_BASE_OPTS="-o ControlMaster=no -o ControlPath=none -o BatchMode=yes
 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KNOWN
 -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=3
 -i $PRIVKEY -p $VPS_PORT"

ensure_key() {
  if [ -f "$PRIVKEY" ] && [ -f "$PUBKEY_OUT" ]; then return 0; fi
  mkdir -p /root/.ssh && chmod 700 /root/.ssh
  if ! command -v ssh-keygen >/dev/null 2>&1; then
    log "ERROR: ssh-keygen не найден — установить openssh-client"; return 1
  fi
  ssh-keygen -t ed25519 -N "" -C "whimco-regcloud-tunnel" -f "$PRIVKEY" -q \
    && cp "$PRIVKEY.pub" "$PUBKEY_OUT" \
    && log "создан новый tunnel-key: $PUBKEY_OUT"
}

# Публикуем pubkey в репо: копируем файл + авто-коммит/пуш (только этот файл),
# чтобы агент/оператор забрал его с другой стороны и установил на VPS.
publish_pubkey() {
  [ -f "$PUBKEY_OUT" ] || return 0
  mkdir -p "$(dirname "$PUBKEY_REPO")"
  if [ ! -f "$PUBKEY_REPO" ] || ! cmp -s "$PUBKEY_OUT" "$PUBKEY_REPO"; then
    cp "$PUBKEY_OUT" "$PUBKEY_REPO" 2>/dev/null || true
    log "pubkey скопирован в $PUBKEY_REPO — авто-коммит+push"
    if ( cd "$REPO_ROOT" && \
         git add "$PUBKEY_REPO" && \
         git commit -m "chore(tunnel): publish whimco regcloud tunnel pubkey (auto)" -- "$PUBKEY_REPO" && \
         git push origin master ) >>"$LOG" 2>&1; then
      log "pubkey закоммичен и запушен в GitHub"
    else
      log "WARN: авто-коммит pubkey не прошёл (нет creds? дерево грязное?) — файл лежит в рабочем дереве"
    fi
  fi
}

# Однократно: пытаемся сами добавить ключ на VPS (работает, если там уже стоит
# наш старый ключ или парольная auth отключена → просто fail, не критично).
deploy_pubkey() {
  [ -f "$PUBKEY_OUT" ] || return 0
  if timeout 25 ssh $SSH_BASE_OPTS "$VPS_USER@$VPS_HOST" \
      "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && \
       grep -qxF '$(cat "$PUBKEY_OUT")' ~/.ssh/authorized_keys || \
       echo '$(cat "$PUBKEY_OUT")' >> ~/.ssh/authorized_keys; \
       chmod 600 ~/.ssh/authorized_keys" >>"$LOG" 2>&1; then
    log "pubkey установлен на VPS автоматически"
  else
    log "pubkey пока НЕ установлен на VPS (ожидается ручная установка из $PUBKEY_REPO)"
  fi
}

# ВАЖНО: реверс-туннель слушает порты на VPS, а НЕ на whimco, поэтому локальный
# port-check тут не работает. Живость туннеля = живость loop-процесса и его
# foreground ssh (упал → loop переподключается сам).

has_loop() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null
}

ensure_tunnel() {
  if has_loop; then
    return 0   # loop жив — он сам держит/переподнимает ssh
  fi
  rm -f "$PIDFILE"
  log "запускаю tunnel-loop → $VPS_USER@$VPS_HOST (-R :$SSH_PORT_BIND→22, :$WEB_PORT_BIND→$WEB_LOCAL_PORT)"
  nohup bash "$0" loop >>"$LOG" 2>&1 </dev/null &
  echo $! > "$PIDFILE"
}

cmd_loop() {
  while true; do
    # прибрать осиротевший ssh от прошлого цикла (по cmdline с нашим маркером)
    pkill -f "ssh .* -o ServerAliveInterval=30 .*-R \*:$SSH_PORT_BIND:" 2>/dev/null || true
    log "поднимаю ssh -R"
    ssh $SSH_BASE_OPTS "$VPS_USER@$VPS_HOST" \
      -R "*:$SSH_PORT_BIND:127.0.0.1:22" \
      -R "*:$WEB_PORT_BIND:127.0.0.1:$WEB_LOCAL_PORT" \
      -N -o ExitOnForwardFailure=yes >>"$LOG" 2>&1 \
      || log "ssh -R завершился (retry через ${LOOP_INTERVAL}s)"
    sleep "$LOOP_INTERVAL"
  done
}

cmd_status() {
  echo "VPS:            $VPS_USER@$VPS_HOST:$VPS_PORT"
  echo "binds:          *:$SSH_PORT_BIND → 127.0.0.1:22 ; *:$WEB_PORT_BIND → 127.0.0.1:$WEB_LOCAL_PORT"
  echo "loop pid:       $(has_loop && cat "$PIDFILE" || echo 'нет')"
  # живая проверка туннеля: спросить VPS, слушает ли он наши порты (best effort)
  if timeout 20 ssh $SSH_BASE_OPTS "$VPS_USER@$VPS_HOST" \
      "ss -tln | grep -E ':($SSH_PORT_BIND|$WEB_PORT_BIND)\b'" >>"$LOG" 2>&1; then
    echo "tunnel:         LIVE (VPS слушает порты)"
  else
    echo "tunnel:         down/unknown (VPS-проверка не прошла — см. $LOG)"
  fi
  echo "pubkey file:    $PUBKEY_OUT $([ -f "$PUBKEY_OUT" ] && echo '(есть)' || echo '(нет — ключ ещё не создан)')"
  echo "pubkey repo:    $PUBKEY_REPO $([ -f "$PUBKEY_REPO" ] && echo '(есть)' || echo '(нет)')"
  [ -f "$PUBKEY_REPO" ] && echo "pubkey:         $(cat "$PUBKEY_REPO")"
}

cmd_stop() {
  if has_loop; then kill "$(cat "$PIDFILE")" 2>/dev/null || true; fi
  pkill -f "-R \*:$SSH_PORT_BIND:" 2>/dev/null || true
  rm -f "$PIDFILE"
  log "туннель остановлен (по запросу)"
}

case "${1:-ensure}" in
  ensure)
    ensure_key || exit 1
    publish_pubkey
    # автодеплой pubkey — сработает, как только на VPS появится предыдущий ключ
    deploy_pubkey
    ensure_tunnel
    ;;
  status) cmd_status ;;
  loop)   cmd_loop ;;
  stop)   cmd_stop ;;
  *) echo "usage: $0 {ensure|status|loop|stop}"; exit 1 ;;
esac
