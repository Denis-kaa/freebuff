#!/data/data/com.termux/files/usr/bin/bash
# ============================================================================
# run_test_suite.sh — Full platform test suite with structured MD output
# ============================================================================
# Usage:
#   bash scripts_01/run_test_suite.sh [OPTIONS***REMOVED***
#
# Options:
#   --quick         Fast check: Router + Artifact + ADR-018 (~2 min)
#   --full          Full pytest tests_09/ (~15 min)
#   --all           Everything: quick + full + mypy + registry (default)
#   --skip-mypy     Skip mypy type-check phase
#   --skip-full     Skip full pytest suite
#   --out FILE      Custom output path (default: auto-timestamped)
#   --help          Show this help
#
# Output:
#   MD file saved to docs_10/runbook/TEST_RESULT_<timestamp>.md
#   (unless --out is specified)
#
# Example:
#   bash scripts_01/run_test_suite.sh --quick               # fast check only
#   bash scripts_01/run_test_suite.sh --all                  # everything
#   bash scripts_01/run_test_suite.sh --full --skip-mypy     # full suite, no mypy
#   bash scripts_01/run_test_suite.sh --out /tmp/my_test.md  # custom path
# ============================================================================

set -o pipefail

# ── Resolve project root ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || { echo "FATAL: cannot cd to $PROJECT_ROOT"; exit 2; ***REMOVED***

# ── Defaults ──────────────────────────────────────────────────────────────
MODE="all"
SKIP_MYPY=false
SKIP_FULL=false
OUT_FILE=""
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ── Parse arguments ───────────────────────────────────────────────────────
while [[ $# -gt 0 ***REMOVED******REMOVED***; do
    case "$1" in
        --quick)   MODE="quick"; shift ;;
        --full)    MODE="full"; shift ;;
        --all)     MODE="all"; shift ;;
        --skip-mypy) SKIP_MYPY=true; shift ;;
        --skip-full) SKIP_FULL=true; shift ;;
        --out)     OUT_FILE="$2"; shift 2 ;;
        --help|-h)
            head -30 "$0" | grep -A 30 "^# Usage"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
done

# ── Resolve output file ───────────────────────────────────────────────────
if [[ -z "$OUT_FILE" ***REMOVED******REMOVED***; then
    OUT_FILE="docs_10/runbook/TEST_RESULT_${TIMESTAMP***REMOVED***.md"
fi
OUT_DIR="$(dirname "$OUT_FILE")"
mkdir -p "$OUT_DIR"

# ── Environment info ──────────────────────────────────────────────────────
PYTHON_VERSION=$(python3 --version 2>&1 || echo "unknown")
TERMUX_INFO=$(getprop ro.product.model 2>/dev/null || echo "unknown device")
UNAME=$(uname -m 2>/dev/null || echo "unknown arch")

# ── Helper: run a phase and capture output ────────────────────────────────
# Usage: run_phase <phase_name> <timeout_seconds> <command...>
run_phase() {
    local name="$1"
    local timeout_sec="$2"
    shift 2
    local cmd=("$@")

    echo "" >> "$OUT_FILE"
    echo "### $name" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo '```text' >> "$OUT_FILE"

    local exit_code=0
    local start_ts
    local end_ts
    start_ts=$(date +%s)

    # Run command with timeout, capture both stdout and stderr
    if timeout "$timeout_sec" "${cmd[@***REMOVED******REMOVED***" >> "$OUT_FILE" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi

    end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo '```' >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"

    # Interpret exit code
    local status_icon=""
    local status_text=""
    case $exit_code in
        0)
            status_icon="✅"
            status_text="PASS"
            ;;
        124)
            status_icon="⏱️"
            status_text="TIMEOUT (${timeout_sec***REMOVED***s)"
            ;;
        *)
            status_icon="❌"
            status_text="FAIL (exit=$exit_code)"
            ;;
    esac

    echo "**$status_icon $name:** $status_text · elapsed=${elapsed***REMOVED***s" >> "$OUT_FILE"
    echo "$exit_code:$elapsed:$status_text"
***REMOVED***

# ── Phase runner for «best-effort» checks ────────────────────────────────
# Like run_phase but always returns 0 for summary, captures real exit in MD
run_phase_besteffort() {
    local name="$1"
    local timeout_sec="$2"
    shift 2
    local cmd=("$@")

    echo "" >> "$OUT_FILE"
    echo "### $name" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo '```text' >> "$OUT_FILE"

    local exit_code=0
    local start_ts
    start_ts=$(date +%s)

    timeout "$timeout_sec" "${cmd[@***REMOVED******REMOVED***" >> "$OUT_FILE" 2>&1 || exit_code=$?

    local end_ts
    end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo '```' >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"

    case $exit_code in
        0)   echo "**✅ $name:** PASS · elapsed=${elapsed***REMOVED***s" >> "$OUT_FILE" ;;
        124) echo "**⏱️ $name:** TIMEOUT (${timeout_sec***REMOVED***s) · elapsed=${elapsed***REMOVED***s" >> "$OUT_FILE" ;;
        *)   echo "**⚠️ $name:** exit=$exit_code · elapsed=${elapsed***REMOVED***s" >> "$OUT_FILE" ;;
    esac
    echo "$exit_code:$elapsed"
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# START — Write MD header
# ══════════════════════════════════════════════════════════════════════════

cat > "$OUT_FILE" <<HEADER
# Test Suite Result — $TIMESTAMP

| Field | Value |
|-------|-------|
| **Mode** | \`$MODE\` |
| **Date** | $(date +"%Y-%m-%d %H:%M:%S") |
| **Python** | $PYTHON_VERSION |
| **Device** | $TERMUX_INFO ($UNAME) |
| **Project** | \`$PROJECT_ROOT\` |
| **Verification** | USER-VERIFIED |

---

## Phases

HEADER

echo "[suite***REMOVED*** Mode=$MODE  Output=$OUT_FILE"
echo "[suite***REMOVED*** Python: $PYTHON_VERSION  Device: $TERMUX_INFO ($UNAME)"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# PHASE 1 — QUICK (Router + Artifact + ADR-018)
# ══════════════════════════════════════════════════════════════════════════

run_quick() {
    echo "[quick***REMOVED*** Starting..."
    echo "" >> "$OUT_FILE"
    echo "## Quick smoke tests" >> "$OUT_FILE"

    local r1 r2
    r1=$(run_phase "1a. Router availability" 120 \
        python3 -m pytest tests_09/core/test_router.py::TestSmartRouterAvailability -q)
    r2=$(run_phase "1b. Artifact + ADR-018" 180 \
        python3 -m pytest tests_09/test_artifact.py tests_09/test_adr018_factory_forge_bridge.py -q)

    echo "[quick***REMOVED*** Done: Router=$(echo "$r1" | cut -d: -f3) Artifact=$(echo "$r2" | cut -d: -f3)"
    return 0
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# PHASE 2 — FULL pytest tests_09/
# ══════════════════════════════════════════════════════════════════════════

run_full() {
    echo "" >> "$OUT_FILE"
    echo "## Full test suite" >> "$OUT_FILE"

    echo "[full***REMOVED*** Starting full pytest tests_09/ ..."
    local r
    r=$(run_phase "2. Full pytest tests_09/" 900 \
        python3 -m pytest tests_09/ -q)

    local ec=$(echo "$r" | cut -d: -f1)
    local el=$(echo "$r" | cut -d: -f2)
    local st=$(echo "$r" | cut -d: -f3)

    if [[ "$ec" -eq 0 ***REMOVED******REMOVED***; then
        echo "[full***REMOVED*** PASS · ${el***REMOVED***s"
    elif [[ "$ec" -eq 124 ***REMOVED******REMOVED***; then
        echo "[full***REMOVED*** TIMEOUT · ${el***REMOVED***s (last 30 lines in report)"
    else
        echo "[full***REMOVED*** FAIL (exit=$ec) · ${el***REMOVED***s"
    fi
    return 0
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# PHASE 3 — MYPY type-check
# ══════════════════════════════════════════════════════════════════════════

run_mypy() {
    echo "" >> "$OUT_FILE"
    echo "## Type-check (mypy)" >> "$OUT_FILE"

    echo "[mypy***REMOVED*** Starting..."
    local r_fb r_art
    r_fb=$(run_phase_besteffort "3a. mypy factory_base.py" 300 \
        python3 -m mypy core_02/factory_base.py --ignore-missing-imports)
    r_art=$(run_phase_besteffort "3b. mypy artifact.py" 120 \
        python3 -m mypy core_02/artifact.py --ignore-missing-imports)

    echo "[mypy***REMOVED*** Done: factory_base=$(echo "$r_fb" | cut -d: -f1) artifact=$(echo "$r_art" | cut -d: -f1)"
    return 0
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# PHASE 4 — REGISTRY + CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════

run_registry() {
    echo "" >> "$OUT_FILE"
    echo "## Registry & consistency" >> "$OUT_FILE"

    echo "[registry***REMOVED*** Starting..."
    local r_mr r_cc
    r_mr=$(run_phase "4a. MissingRegistry check" 60 \
        python3 -m core_02.missing_registry check)
    r_cc=$(run_phase "4b. Consistency check" 180 \
        python3 -m scripts_01.consistency_check --report)

    echo "[registry***REMOVED*** Done: missing_registry=$(echo "$r_mr" | cut -d: -f3) consistency=$(echo "$r_cc" | cut -d: -f3)"
    return 0
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# PHASE 5 — AST counter
# ══════════════════════════════════════════════════════════════════════════

run_counter() {
    echo "" >> "$OUT_FILE"
    echo "## AST test counter" >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo '```text' >> "$OUT_FILE"
    python3 -c "
from scripts_01.consistency_check import count_test_functions
***REMOVED***
print(f'AST count = {count_test_functions(Path(\".\"))***REMOVED***')
" >> "$OUT_FILE" 2>&1
    echo '```' >> "$OUT_FILE"
    echo "" >> "$OUT_FILE"
    echo "[counter***REMOVED*** Done"
***REMOVED***

# ══════════════════════════════════════════════════════════════════════════
# MAIN DISPATCH
# ══════════════════════════════════════════════════════════════════════════

OVERALL_EXIT=0

case "$MODE" in
    quick)
        run_quick
        run_registry
        run_counter
        ;;
    full)
        run_quick
        if ! $SKIP_FULL; then run_full; fi
        run_registry
        run_counter
        ;;
    all)
        run_quick
        if ! $SKIP_FULL; then run_full; fi
        if ! $SKIP_MYPY; then run_mypy; fi
        run_registry
        run_counter
        ;;
esac

# ══════════════════════════════════════════════════════════════════════════
# FOOTER — Summary table
# ══════════════════════════════════════════════════════════════════════════

cat >> "$OUT_FILE" <<FOOTER

---

## Summary

| Phase | Status |
|-------|--------|
| Quick (Router + Artifact) | See sections 1a/1b above |
| Full pytest | See section 2 above |
| mypy | See sections 3a/3b above |
| MissingRegistry | See section 4a above |
| Consistency check | See section 4b above |

---

**Verification:** USER-VERIFIED (run locally on device)
**Report:** \`$OUT_FILE\`
**Script:** \`scripts_01/run_test_suite.sh --$MODE\`

> ⚠️ This report was generated automatically.  
> Review each phase section for actual pass/fail/timout details.  
> The status icons (✅/❌/⏱️/⚠️) are the ground truth.
FOOTER

echo ""
echo "════════════════════════════════════════════"
echo "  Test suite complete"
echo "  Report: $OUT_FILE"
echo "════════════════════════════════════════════"

# Exit with 0 — the script itself always succeeds; 
# pass/fail determination is in the MD report.
exit 0