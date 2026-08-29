#!/bin/bash

# smart_test_runner_fixed.sh - Исправленная версия для Android
REPO_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"
cd "$REPO_ROOT" || exit 1

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Создаем рабочие директории
TEMP_DIR="$REPO_ROOT/.test_temp"
mkdir -p "$TEMP_DIR"
LOG_DIR="$REPO_ROOT/.test_logs"
mkdir -p "$LOG_DIR"

# Экспортируем переменные
export TMPDIR="$TEMP_DIR"
export TEMP="$TEMP_DIR"
export TMP="$TEMP_DIR"
export PYTHONPYCACHEPREFIX="$TEMP_DIR/pycache"
export PYTHONHASHSEED=0

echo -e "${GREEN***REMOVED***✓ Temp: $TEMP_DIR${NC***REMOVED***"
echo -e "${GREEN***REMOVED***✓ Logs: $LOG_DIR${NC***REMOVED***"

# Функция для безопасного запуска pytest
run_pytest_safe() {
    local test_path="$1"
    local test_name="$2"
    local extra_args="$3"
    local log_file="$LOG_DIR/${test_name// /_***REMOVED***.log"
    
    echo -e "${CYAN***REMOVED***▶ $test_name${NC***REMOVED***"
    echo -e "${CYAN***REMOVED***  $test_path${NC***REMOVED***\n"
    
    # Запускаем с перенаправлением вывода
    TMPDIR="$TEMP_DIR" $PYTHON_CMD -m pytest "$test_path" -v --tb=short $extra_args 2>&1 | tee "$log_file"
    local exit_code=${PIPESTATUS[0***REMOVED******REMOVED***
    
    if [ $exit_code -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ PASSED${NC***REMOVED***\n"
        return 0
    else
        echo -e "${RED***REMOVED***❌ FAILED (code: $exit_code)${NC***REMOVED***\n"
        return $exit_code
    fi
***REMOVED***

echo -e "${BOLD***REMOVED***${GREEN***REMOVED***🚀 Smart Test Runner v2.0 (Android)${NC***REMOVED***"
echo -e "Started: $(date)\n"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED***REMOVED***❌ Python not found${NC***REMOVED***"
    exit 1
fi

echo -e "${BLUE***REMOVED***Python: $(python3 --version)${NC***REMOVED***"
echo -e "${BLUE***REMOVED***Pytest: $(python3 -m pytest --version 2>/dev/null | head -1)${NC***REMOVED***\n"

# === 1. SMOKE TEST ===
echo -e "${BOLD***REMOVED***${BLUE***REMOVED***═══ 1. SMOKE TEST ═══${NC***REMOVED***\n"

# Ищем тесты роутера
ROUTER_FILE=$(find tests_09 -name "*router*.py" -type f | head -1)

if [ -n "$ROUTER_FILE" ***REMOVED***; then
    echo -e "${GREEN***REMOVED***✓ Found: $ROUTER_FILE${NC***REMOVED***"
    
    # Запускаем с --collect-only для проверки
    echo -e "${YELLOW***REMOVED***Collecting tests...${NC***REMOVED***"
    python3 -m pytest "$ROUTER_FILE" --collect-only -q 2>/dev/null || true
    
    # Запускаем тесты
    if run_pytest_safe "$ROUTER_FILE" "Router Smoke" "-k SmartRouter -q --no-cov"; then
        PASSED=$((PASSED + 1))
    else
        # Пробуем без фильтра
        if run_pytest_safe "$ROUTER_FILE" "Router All" "-q --no-cov"; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
    fi
else
    echo -e "${RED***REMOVED***❌ Router tests not found${NC***REMOVED***"
    FAILED=$((FAILED + 1))
fi

# === 2. ARTIFACT + ADR ===
echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***═══ 2. REGRESSION TESTS ═══${NC***REMOVED***\n"

ARTIFACT_FILES=$(find tests_09 -name "*artifact*.py" -o -name "*adr*.py" -type f 2>/dev/null | tr '\n' ' ')

if [ -n "$ARTIFACT_FILES" ***REMOVED***; then
    if run_pytest_safe "$ARTIFACT_FILES" "Artifact+ADR" "-q --no-cov"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  Artifact/ADR tests not found${NC***REMOVED***"
    SKIPPED=$((SKIPPED + 1))
fi

# === 3. FULL SUITE (по частям) ===
echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***═══ 3. FULL SUITE (по частям) ═══${NC***REMOVED***\n"

# Разбиваем на группы для стабильности
TEST_GROUPS=(
    "tests_09/test_anchors_resolver.py"
    "tests_09/test_blueprint_registry.py"
    "tests_09/test_canonical_lifecycle.py"
    "tests_09/test_consistency_check.py"
    "tests_09/test_consistency_check_idempotency.py"
    "tests_09/test_factory_base.py"
    "tests_09/test_hermetic_harness.py"
    "tests_09/test_mcp_fastapi.py"
    "tests_09/test_plugin_capabilities.py"
    "tests_09/test_role_artifact_validator.py"
    "tests_09/test_smart_doc.py"
    "tests_09/test_telegram_contract.py"
    "tests_09/test_xlsx_builder.py"
)

for group in "${TEST_GROUPS[@***REMOVED******REMOVED***"; do
    if [ -f "$group" ***REMOVED***; then
        echo -e "${CYAN***REMOVED***▶ Testing: $group${NC***REMOVED***"
        if run_pytest_safe "$group" "$(basename $group)" "-q --no-cov" 2>/dev/null; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
    fi
done

# === 4. MYPY ===
echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***═══ 4. TYPE CHECK ═══${NC***REMOVED***\n"

if [ -f "core_02/factory_base.py" ***REMOVED***; then
    echo -e "${YELLOW***REMOVED***⏳ Running mypy...${NC***REMOVED***"
    TMPDIR="$TEMP_DIR" python3 -m mypy core_02/factory_base.py --ignore-missing-imports 2>&1 | tee "$LOG_DIR/mypy.log"
    MYPY_EXIT=$?
    
    if [ $MYPY_EXIT -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ MYPY PASSED${NC***REMOVED***"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED***REMOVED***❌ MYPY FAILED (code: $MYPY_EXIT)${NC***REMOVED***"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  factory_base.py not found${NC***REMOVED***"
    SKIPPED=$((SKIPPED + 1))
fi

# === 5. REGISTRY ===
echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***═══ 5. REGISTRY CHECKS ═══${NC***REMOVED***\n"

if python3 -c "import core_02.missing_registry" 2>/dev/null; then
    python3 -m core_02.missing_registry check 2>&1 | tee "$LOG_DIR/registry.log"
    if [ ${PIPESTATUS[0***REMOVED******REMOVED*** -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ Registry OK${NC***REMOVED***"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED***REMOVED***❌ Registry FAILED${NC***REMOVED***"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  Registry module not found${NC***REMOVED***"
    SKIPPED=$((SKIPPED + 1))
fi

if [ -f "scripts_01/consistency_check.py" ***REMOVED***; then
    python3 -m scripts_01.consistency_check --report 2>&1 | tee "$LOG_DIR/consistency.log"
    if [ ${PIPESTATUS[0***REMOVED******REMOVED*** -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ Consistency OK${NC***REMOVED***"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED***REMOVED***❌ Consistency FAILED${NC***REMOVED***"
        FAILED=$((FAILED + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  Consistency check not found${NC***REMOVED***"
    SKIPPED=$((SKIPPED + 1))
fi

# === SUMMARY ===
echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***════════════════════════════════════════════════════════════${NC***REMOVED***"
echo -e "${BOLD***REMOVED***${CYAN***REMOVED***  SUMMARY${NC***REMOVED***"
echo -e "${BOLD***REMOVED***${BLUE***REMOVED***════════════════════════════════════════════════════════════${NC***REMOVED***\n"

echo -e "${GREEN***REMOVED***✓ Passed:  $PASSED${NC***REMOVED***"
echo -e "${RED***REMOVED***✗ Failed:  $FAILED${NC***REMOVED***"
echo -e "${YELLOW***REMOVED***⊘ Skipped: $SKIPPED${NC***REMOVED***"
TOTAL=$((PASSED + FAILED + SKIPPED))
echo -e "${BLUE***REMOVED***⊡ Total:   $TOTAL${NC***REMOVED***"

if [ $FAILED -eq 0 ***REMOVED*** && [ $PASSED -gt 0 ***REMOVED***; then
    echo -e "\n${BOLD***REMOVED***${GREEN***REMOVED***🎉 ALL TESTS PASSED!${NC***REMOVED***"
    echo -e "${GREEN***REMOVED***✅ SmartRouter fix verified${NC***REMOVED***"
    EXIT_CODE=0
else
    echo -e "\n${BOLD***REMOVED***${RED***REMOVED***❌ SOME TESTS FAILED${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***Logs: $LOG_DIR/${NC***REMOVED***"
    EXIT_CODE=1
fi

echo -e "\n${BLUE***REMOVED***Finished: $(date)${NC***REMOVED***"
exit $EXIT_CODE
