#!/usr/bin/env bash
# scripts_01/update_freebuff_safe.sh
#
# Безопасное обновление Freebuff CLI на Android/Termux + proot-distro ubuntu.
#
# КАК УСТРОЕН FREEBUFF (см. freebuff-android-setup.md):
#   - npm-пакет `freebuff` — это ТОНКИЙ ЗАГРУЗЧИК (index.js -> launcher.js).
#     Он сам скачивает нативный бинарь с
#     https://codebuff.com/api/releases/download/{version***REMOVED***/freebuff-{platform***REMOVED***.tar.gz
#     в ~/.config/manicode/freebuff (и tree-sitter.wasm), а НЕ при npm install.
#   - Бинарь — glibc ELF, запускается ТОЛЬКО внутри proot-distro ubuntu.
#   - Повседневный запуск — через ~/.local/bin/freebuff (обёртка -> proot),
#     которая МИНУЕТ Node-лаунчер.
#   - Env-конфиг (FREEBUFF_BINARY_TARGET / FREEBUFF_SKIP_UPDATE) задаётся в
#     обёртке ~/.local/bin/freebuff (export + --env в proot-distro login).
#     launcher.js БОЛЬШЕ НЕ патчится — патч снят, npm install больше ничего
#     не стирает.
#
# ПРАВИЛЬНАЯ процедура обновления:
#   1. npm install -g freebuff@latest --force   (обновить лаунчер; --force из-за
#      EBADPLATFORM, т.к. process.platform=android)
#   2. Удалить freebuff-metadata.json            (форсировать повторное скачивание)
#   3. FREEBUFF_BINARY_TARGET=linux-arm64 node .../index.js
#      (лаунчер скачает новый бинарь + .wasm, потом упадёт ENOENT при попытке
#      spawn'ить glibc-бинарь вне proot — это ОЖИДАЕМО, игнорируем)
#   4. Проверить --version бинаря внутри proot
#   5. Smoke-тест TUI внутри proot
#   6. Авто-откат при любом провале (бинарь + metadata + wasm + npm)
#
# Exit-коды:
#   0 — успех · 1 — preflight · 2 — провал, откат OK · 3 — откат не удался
#
# Использование:
#   bash scripts_01/update_freebuff_safe.sh                  # полный цикл
#   bash scripts_01/update_freebuff_safe.sh --smoke-only     # только smoke-тест
#   bash scripts_01/update_freebuff_safe.sh --force          # игнор живой сессии
#
# ВАЖНО: запускайте из нативного Termux (отдельное окно), НЕ изнутри
# freebuff-сессии — внутри proot нет npm/proot-distro.

set -u
set -o pipefail

# ── Конфигурация (совпадает с freebuff_plugin_03/config.py) ──────────────

BIN_DIR="${MANICODE_DIR:-$HOME/.config/manicode***REMOVED***"
BIN_PATH="$BIN_DIR/freebuff"
META_PATH="$BIN_DIR/freebuff-metadata.json"
SETTINGS_PATH="$BIN_DIR/settings.json"
WASM_PATH="$BIN_DIR/tree-sitter.wasm"
PROOT_DISTRO="${PROOT_DISTRO_NAME:-ubuntu***REMOVED***"

# Корень проекта (для smoke-dir — он виден внутри proot, в отличие от
# нативного /tmp Termux, который в Ubuntu-chroot НЕ примонтирован).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0***REMOVED******REMOVED***")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Версия npm-пакета-лаунчера (переопределяется через NPM_VERSION; default latest).
# --force обязателен: пакет объявляет os=[darwin,linux,win32***REMOVED***, на Termux
# process.platform=android → EBADPLATFORM без --force.
NPM_VERSION="${NPM_VERSION:-latest***REMOVED***"

# Стартовые строки TUI (по freebuff_plugin_03/monitor.sh).
SMOKE_OK_MARKERS=("Start coding" "RECOMMENDED" "Enter a coding task")
# «бинарь запустился, но занят другой инстанцией» (не провал загрузки).
SMOKE_BUSY_MARKERS=("Freebuff is already running" "Only one freebuff instance")
# Аварийные маркеры (glibc/loader/краш) — любой = провал.
# Намеренно узкий набор: «No such file or directory»/«Killed» могут появляться
# в нормальном TUI-выводе и дали бы ложный откат.
SMOKE_CRASH_MARKERS=(
    "error while loading shared libraries"
    "cannot open shared object file"
    "Segmentation fault"
    "Command not found"
)

SMOKE_TIMEOUT="${SMOKE_TIMEOUT_SECONDS:-45***REMOVED***"
VERSION_TIMEOUT="${VERSION_TIMEOUT_SECONDS:-30***REMOVED***"

BACKUP_SUFFIX=".bak-$(date +%Y%m%d-%H%M%S)"
SMOKE_TMUX="fb_smoke_$$"
SMOKE_DIR=""
ROLLED_BACK=0

# ── Утилиты ──────────────────────────────────────────────────────────────

log()  { echo "  $*"; ***REMOVED***
ok()   { echo "✅ $*"; ***REMOVED***
warn() { echo "⚠️  $*" >&2; ***REMOVED***
fail() { echo "❌ $*" >&2; ***REMOVED***

usage() {
    cat <<'EOF'
Использование:
  bash scripts_01/update_freebuff_safe.sh                  # полный цикл
  bash scripts_01/update_freebuff_safe.sh --smoke-only     # только smoke-тест
  bash scripts_01/update_freebuff_safe.sh --force          # игнор живой сессии
  NPM_VERSION="0.0.153" \
      bash scripts_01/update_freebuff_safe.sh              # пин конкретной версии

Exit-коды:
  0 = успех · 1 = preflight-ошибка · 2 = провал, откат OK · 3 = откат не удался
EOF
***REMOVED***

cleanup() {
    if [ -n "${SMOKE_TMUX:-***REMOVED***" ***REMOVED***; then
        tmux kill-session -t "$SMOKE_TMUX" 2>/dev/null || true
    fi
    if [ -n "${SMOKE_DIR:-***REMOVED***" ***REMOVED*** && [ -d "$SMOKE_DIR" ***REMOVED***; then
        rm -rf "$SMOKE_DIR" 2>/dev/null || true
    fi
***REMOVED***
trap cleanup EXIT

# ── Проверки ─────────────────────────────────────────────────────────────

# Нативный Termux (не внутри proot): TERMUX_VERSION непустой И proot-distro
# доступен (внутри proot он печатает «should not be executed under PRoot»).
is_native_termux() {
    [ -n "${TERMUX_VERSION:-***REMOVED***" ***REMOVED*** && command -v proot-distro >/dev/null 2>&1
***REMOVED***

get_meta_version() {
    if [ -f "$META_PATH" ***REMOVED***; then
        grep -oE '"version"[[:space:***REMOVED******REMOVED****:[[:space:***REMOVED******REMOVED****"[^"***REMOVED****"' "$META_PATH" 2>/dev/null \
            | head -1 | sed 's/.*"\([^"***REMOVED****\)"$/\1/'
    else
        echo "unknown"
    fi
***REMOVED***

live_instance_pid() {
    pgrep -f "config/manicode/freebuff" 2>/dev/null | head -1 || true
***REMOVED***

# Пути к глобальному пакету-лаунчеру (вычисляем ОДИН раз; подпроцесс npm root -g
# дорогой и при сбое вернул бы мусорные относительные пути).
NPM_ROOT="$(npm root -g 2>/dev/null || echo "")"
INDEX_JS="$NPM_ROOT/freebuff/index.js"

# NB: launcher.js НЕ патчится. Env-конфиг (FREEBUFF_BINARY_TARGET /
# FREEBUFF_SKIP_UPDATE) живёт в обёртке ~/.local/bin/freebuff; здесь ниже
# FREEBUFF_BINARY_TARGET задаётся inline только для запуска лаунчера при
# скачивании нового бинаря.

# ── Smoke-тест ───────────────────────────────────────────────────────────
# Запускает бинарь внутри proot в чистой tempdir, ждёт стартовых строк TUI.
# Возврат: 0 = OK, 1 = crash/таймаут, 2 = занят (single-instance).

smoke_test() {
    # Smoke-dir под PROJECT_ROOT (shared storage) — путь виден внутри proot.
    SMOKE_DIR="$(mktemp -d "$PROJECT_ROOT/.smoke_XXXXXX" 2>/dev/null)" || SMOKE_DIR=""
    if [ -z "$SMOKE_DIR" ***REMOVED***; then
        SMOKE_DIR="$PROJECT_ROOT/.smoke_$$"
        mkdir -p "$SMOKE_DIR"
    fi
    local log_file="$SMOKE_DIR/smoke.log"

    # Без вложенных кавычек: $BIN_PATH/$SMOKE_DIR без пробелов.
    local proot_cmd="proot-distro login $PROOT_DISTRO -- $BIN_PATH --cwd $SMOKE_DIR"

    log "smoke-тест: запускаю бинарь внутри proot (timeout ${SMOKE_TIMEOUT***REMOVED***s)…"
    tmux new-session -d -s "$SMOKE_TMUX" \
        "script -q '$log_file' -c '$proot_cmd' >/dev/null 2>&1" 2>/dev/null

    local deadline=$(( $(date +%s) + SMOKE_TIMEOUT ))
    local result=""
    while [ "$(date +%s)" -lt "$deadline" ***REMOVED***; do
        [ -f "$log_file" ***REMOVED*** || { sleep 1; continue; ***REMOVED***

        for m in "${SMOKE_CRASH_MARKERS[@***REMOVED******REMOVED***"; do
            if grep -qiF -- "$m" "$log_file" 2>/dev/null; then
                result="crash"; break 2
            fi
        done
        for m in "${SMOKE_OK_MARKERS[@***REMOVED******REMOVED***"; do
            if grep -qiF -- "$m" "$log_file" 2>/dev/null; then
                result="ok"; break 2
            fi
        done
        for m in "${SMOKE_BUSY_MARKERS[@***REMOVED******REMOVED***"; do
            if grep -qiF -- "$m" "$log_file" 2>/dev/null; then
                result="busy"; break 2
            fi
        done

        sleep 1
    done

    # Грациозное завершение: Ctrl-C → пауза → kill-session (без kill -9 по proot).
    tmux send-keys -t "$SMOKE_TMUX" C-c 2>/dev/null || true
    sleep 2
    tmux kill-session -t "$SMOKE_TMUX" 2>/dev/null || true

    # Сироты — только по уникальной smoke-директории, только SIGTERM.
    local orphans
    orphans="$(pgrep -f "freebuff.*--cwd .*${SMOKE_DIR***REMOVED***" 2>/dev/null || true)"
    if [ -n "$orphans" ***REMOVED***; then
        for p in $orphans; do kill "$p" 2>/dev/null || true; done
        sleep 3
        for p in $orphans; do kill "$p" 2>/dev/null || true; done
    fi

    case "$result" in
        ok)   ok "smoke-тест пройден: TUI инициализировался."; return 0 ;;
        busy) warn "smoke-тест: бинарь запустился, но занят другой инстанцией (не провал загрузки)."; return 2 ;;
        crash) fail "smoke-тест ПРОВАЛЕН: аварийный маркер в выводе."; return 1 ;;
        *)     fail "smoke-тест ПРОВАЛЕН: таймаут (${SMOKE_TIMEOUT***REMOVED***s), стартовые строки не появились."; return 1 ;;
    esac
***REMOVED***

# ── Откат ────────────────────────────────────────────────────────────────
# Успех решается ТОЛЬКО по восстановлению бинаря. Остальное — best-effort.
# Возврат: 0 = успех, 1 = провал восстановления бинаря.

rollback() {
    local old_version="$1"

    warn "откат на $old_version…"

    if [ -f "${BIN_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$BIN_BACKUP" "$BIN_PATH"; then
        ok "бинарь восстановлен из бэкапа."
    else
        fail "НЕ удалось восстановить бинарь (критично). Бэкап: ${BIN_BACKUP:-<нет>***REMOVED***"
        # best-effort: остальное возвращаем как есть, но npm/launcher.js НЕ
        # трогаем — без рабочего бинаря система всё равно требует ручного
        # вмешательства.
        [ -f "${META_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$META_BACKUP" "$META_PATH" 2>/dev/null || true
        [ -f "${SETTINGS_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$SETTINGS_BACKUP" "$SETTINGS_PATH" 2>/dev/null || true
        [ -f "${WASM_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$WASM_BACKUP" "$WASM_PATH" 2>/dev/null || true
        ROLLED_BACK=0
        return 1
    fi

    [ -f "${META_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$META_BACKUP" "$META_PATH" 2>/dev/null || true
    [ -f "${SETTINGS_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$SETTINGS_BACKUP" "$SETTINGS_PATH" 2>/dev/null || true
    [ -f "${WASM_BACKUP:-***REMOVED***" ***REMOVED*** && mv -f "$WASM_BACKUP" "$WASM_PATH" 2>/dev/null || true

    # Синхронизируем npm-лаунчер с откаченной версией (если версия известна).
    # launcher.js при этом не трогаем — он больше не патчится.
    if [ "$old_version" != "unknown" ***REMOVED*** && command -v npm >/dev/null 2>&1; then
        if npm install -g "freebuff@${old_version***REMOVED***" --force >/dev/null 2>&1; then
            ok "npm-лаунчер откачен до $old_version."
        else
            warn "бинарь откачен, но npm sync до $old_version не удался."
        fi
    fi

    ROLLED_BACK=1
    return 0
***REMOVED***

# ── Разбор аргументов ────────────────────────────────────────────────────

SMOKE_ONLY=0
FORCE=0
for arg in "$@"; do
    case "$arg" in
        --smoke-only) SMOKE_ONLY=1 ;;
        --force)      FORCE=1 ;;
        -h|--help)    usage; exit 0 ;;
        *) fail "неизвестный аргумент: $arg"; usage; exit 1 ;;
    esac
done

# ── Preflight ────────────────────────────────────────────────────────────

if ! is_native_termux; then
    fail "скрипт должен запускаться из нативного Termux (не изнутри proot)."
    echo ""
    echo "  Вы, похоже, внутри proot (npm и proot-distro недоступны)."
    echo "  Откройте отдельное окно Termux и выполните:"
    echo ""
    echo "      bash scripts_01/update_freebuff_safe.sh"
    echo ""
    exit 1
fi

if [ ! -f "$BIN_PATH" ***REMOVED*** || [ ! -x "$BIN_PATH" ***REMOVED***; then
    fail "бинарь не найден или не исполняемый: $BIN_PATH"
    exit 1
fi

# Обязательные инструменты: node (скачивание бинаря лаунчером) и tmux (smoke-тест).
# Проверяем заранее, чтобы падение не выглядело как «metadata не пересоздан»
# или как 45-секундный таймаут smoke-теста.
for tool in node tmux; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        fail "не найден обязательный инструмент: $tool"
        exit 1
    fi
done

if [ ! -f "$META_PATH" ***REMOVED***; then
    warn "metadata не найден: $META_PATH (версия будет 'unknown')."
fi

OLD_VERSION="$(get_meta_version)"
log "текущая версия: $OLD_VERSION"
log "бинарь: $BIN_PATH"

# ── Режим --smoke-only: только проверка текущего бинаря ──────────────────

if [ "$SMOKE_ONLY" -eq 1 ***REMOVED***; then
    log "режим --smoke-only: обновление пропущено."
    smoke_test
    rc=$?
    exit $(( rc == 1 ? 1 : 0 ))   # busy(2) трактуем как «бинарь жив»
fi

# ── Защита от живой сессии ───────────────────────────────────────────────

LIVE_PID="$(live_instance_pid)"
if [ -n "$LIVE_PID" ***REMOVED*** && [ "$FORCE" -ne 1 ***REMOVED***; then
    warn "обнаружена живая freebuff-сессия (PID $LIVE_PID)."
    echo ""
    echo "  Обновление во время живой сессии приведёт к ложному провалу smoke-теста"
    echo "  (single-instance lock). Закройте сессию и повторите, либо используйте --force."
    exit 1
fi

# ── Бэкап ────────────────────────────────────────────────────────────────

BIN_BACKUP="$BIN_PATH$BACKUP_SUFFIX"
META_BACKUP="$META_PATH$BACKUP_SUFFIX"
SETTINGS_BACKUP="$SETTINGS_PATH$BACKUP_SUFFIX"
WASM_BACKUP="$WASM_PATH$BACKUP_SUFFIX"

cp -p "$BIN_PATH" "$BIN_BACKUP" || { fail "не удалось создать бэкап бинаря."; exit 1; ***REMOVED***
[ -f "$META_PATH" ***REMOVED*** && cp -p "$META_PATH" "$META_BACKUP" 2>/dev/null || true
[ -f "$SETTINGS_PATH" ***REMOVED*** && cp -p "$SETTINGS_PATH" "$SETTINGS_BACKUP" 2>/dev/null || true
[ -f "$WASM_PATH" ***REMOVED*** && cp -p "$WASM_PATH" "$WASM_BACKUP" 2>/dev/null || true

ok "бэкап создан: $BIN_BACKUP"

# ── Обновление ───────────────────────────────────────────────────────────

log "обновление лаунчера: npm install -g freebuff@${NPM_VERSION***REMOVED*** --force"
if ! npm install -g "freebuff@${NPM_VERSION***REMOVED***" --force >/dev/null 2>&1; then
    fail "npm-обновление лаунчера провалилось."
    rollback "$OLD_VERSION"
    if [ "$ROLLED_BACK" -eq 1 ***REMOVED***; then exit 2; else exit 3; fi
fi

# Форсируем повторное скачивание бинаря: удаляем metadata, затем запускаем
# Node-лаунчер. Он скачает новый бинарь + .wasm и упадёт ENOENT при попытке
# spawn'ить glibc-бинарь вне proot — это ожидаемо, игнорируем.
log "скачивание нового бинаря через Node-лаунчер…"
rm -f "$META_PATH"

if [ ! -f "$INDEX_JS" ***REMOVED***; then
    fail "index.js лаунчера не найден: $INDEX_JS"
    rollback "$OLD_VERSION"
    if [ "$ROLLED_BACK" -eq 1 ***REMOVED***; then exit 2; else exit 3; fi
fi

# NB: FREEBUFF_SKIP_UPDATE НЕ ставим — нужно РАЗРЕШИТЬ апдейт.
FREEBUFF_BINARY_TARGET=linux-arm64 node "$INDEX_JS" >/dev/null 2>&1 || true

# Признак успешной загрузки: лаунчер ПЕРЕСОЗДАЁТ metadata.json, который мы
# удалили ДО скачивания. Старый бинарь при этом мог остаться на месте, поэтому
# проверять только его наличие нельзя (это дало бы ложный «успех»).
if [ ! -f "$META_PATH" ***REMOVED***; then
    fail "лаунчер не пересоздал metadata.json — загрузка бинаря не завершилась."
    rollback "$OLD_VERSION"
    if [ "$ROLLED_BACK" -eq 1 ***REMOVED***; then exit 2; else exit 3; fi
fi

# Быстрая проверка: бинарь запускается внутри proot и отдаёт версию.
NEW_VERSION="unknown"
if V_OUT="$(timeout "$VERSION_TIMEOUT" proot-distro login "$PROOT_DISTRO" -- \
        "$BIN_PATH" --version 2>&1)"; then
    NEW_VERSION="$(printf '%s' "$V_OUT" | grep -oE '[0-9***REMOVED***+\.[0-9***REMOVED***+\.[0-9***REMOVED***+' | head -1)"
    [ -n "$NEW_VERSION" ***REMOVED*** || NEW_VERSION="unknown"
    ok "--version отдал: $NEW_VERSION"
    if [ "$NEW_VERSION" = "$OLD_VERSION" ***REMOVED*** && [ "$NEW_VERSION" != "unknown" ***REMOVED***; then
        warn "версия бинаря не изменилась ($OLD_VERSION) — возможно, новый релиз ещё не вышел."
    fi
else
    fail "--version провалился (библиотека/loader сломан)."
    rollback "$OLD_VERSION"
    if [ "$ROLLED_BACK" -eq 1 ***REMOVED***; then exit 2; else exit 3; fi
fi

# ── Smoke-тест ───────────────────────────────────────────────────────────

smoke_test
SMOKE_RC=$?

if [ "$SMOKE_RC" -eq 0 ***REMOVED***; then
    ok "обновление успешно и проверено (${OLD_VERSION***REMOVED*** → ${NEW_VERSION***REMOVED***)."
    warn "бэкап оставлен на случай ручного отката: $BIN_BACKUP"
    exit 0
elif [ "$SMOKE_RC" -eq 2 ***REMOVED***; then
    warn "бинарь загружается (single-instance), но полный smoke-тест не выполнен."
    warn "рекомендуется повторить с --smoke-only после закрытия живых сессий."
    warn "бэкап оставлен: $BIN_BACKUP"
    exit 0
else
    fail "smoke-тест провален — откатываю."
    rollback "$OLD_VERSION"
    if [ "$ROLLED_BACK" -eq 1 ***REMOVED***; then exit 2; else exit 3; fi
fi
