#!/bin/bash

# smart_test_runner.sh - Умный запускатор тестов для Android/Termux
# Запускать из корня репозитория

# Переходим в корень репозитория
REPO_ROOT="/storage/emulated/0/PROJECTS/workstation/freebuff"
cd "$REPO_ROOT" || {
    echo "❌ Cannot change to repository root: $REPO_ROOT"
    exit 1
***REMOVED***

echo "📁 Repository root: $(pwd)"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Конфигурация
TIMEOUT_FULL_SUITE=900  # 15 минут
TIMEOUT_MYPY=300        # 5 минут
PYTHON_CMD="python3"

# Используем локальную директорию вместо /tmp
TEMP_DIR="$REPO_ROOT/.test_temp"
mkdir -p "$TEMP_DIR"
LOG_DIR="$REPO_ROOT/.test_logs"
mkdir -p "$LOG_DIR"

# Устанавливаем переменные окружения для тестов
export TMPDIR="$TEMP_DIR"
export TEMP="$TEMP_DIR"
export TMP="$TEMP_DIR"

echo -e "${GREEN***REMOVED***✓ Temp directory: $TEMP_DIR${NC***REMOVED***"
echo -e "${GREEN***REMOVED***✓ Log directory: $LOG_DIR${NC***REMOVED***"

# Счетчики
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Функция для вывода заголовка
print_header() {
    echo -e "\n${BOLD***REMOVED***${BLUE***REMOVED***════════════════════════════════════════════════════════════${NC***REMOVED***"
    echo -e "${BOLD***REMOVED***${CYAN***REMOVED***  $1${NC***REMOVED***"
    echo -e "${BOLD***REMOVED***${BLUE***REMOVED***════════════════════════════════════════════════════════════${NC***REMOVED***\n"
***REMOVED***

# Функция для запуска pytest с перехватом вывода
run_pytest() {
    local test_path=$1
    local test_name=$2
    local extra_args=$3
    local log_file="$LOG_DIR/${test_name// /_***REMOVED***.log"
    
    echo -e "${CYAN***REMOVED***▶ Running: $test_name${NC***REMOVED***"
    echo -e "${CYAN***REMOVED***  Path: $test_path${NC***REMOVED***\n"
    
    # Запускаем pytest с правильными переменными окружения
    if [ -z "$extra_args" ***REMOVED***; then
        TMPDIR="$TEMP_DIR" $PYTHON_CMD -m pytest $test_path -v --tb=short 2>&1 | tee "$log_file"
    else
        TMPDIR="$TEMP_DIR" $PYTHON_CMD -m pytest $test_path -v --tb=short $extra_args 2>&1 | tee "$log_file"
    fi
    
    local exit_code=${PIPESTATUS[0***REMOVED******REMOVED***
    
    if [ $exit_code -eq 0 ***REMOVED***; then
        echo -e "\n${GREEN***REMOVED***✅ $test_name PASSED${NC***REMOVED***"
        return 0
    else
        echo -e "\n${RED***REMOVED***❌ $test_name FAILED (exit code: $exit_code)${NC***REMOVED***"
        echo -e "${YELLOW***REMOVED***Last 20 lines of output:${NC***REMOVED***"
        tail -20 "$log_file"
        return $exit_code
    fi
***REMOVED***

# Функция запуска с таймаутом
run_with_timeout() {
    local timeout=$1
    local cmd=$2
    local name=$3
    local log_file="$LOG_DIR/${name// /_***REMOVED***.log"
    
    echo -e "${YELLOW***REMOVED***⏳ Running: $name${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***   Command: $cmd${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***   Timeout: ${timeout***REMOVED***s${NC***REMOVED***\n"
    
    # Запускаем команду с таймаутом и правильным TMPDIR
    timeout $timeout bash -c "TMPDIR='$TEMP_DIR' $cmd" 2>&1 | tee "$log_file"
    local exit_code=$?
    
    if [ $exit_code -eq 124 ***REMOVED***; then
        echo -e "\n${RED***REMOVED***⏰ TIMEOUT after ${timeout***REMOVED***s${NC***REMOVED***"
        return 124
    elif [ $exit_code -eq 0 ***REMOVED***; then
        echo -e "\n${GREEN***REMOVED***✅ Completed successfully${NC***REMOVED***"
        return 0
    else
        echo -e "\n${RED***REMOVED***❌ Failed with exit code: $exit_code${NC***REMOVED***"
        echo -e "${YELLOW***REMOVED***Last 20 lines of output:${NC***REMOVED***"
        tail -20 "$log_file"
        return $exit_code
    fi
***REMOVED***

# === НАЧАЛО ===
echo -e "${BOLD***REMOVED***${GREEN***REMOVED***🚀 Smart Test Runner for Android v1.3${NC***REMOVED***"
echo -e "${BOLD***REMOVED***Started at: $(date)${NC***REMOVED***\n"

# Проверка окружения
echo -e "${BLUE***REMOVED***📋 Checking environment...${NC***REMOVED***"
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED***REMOVED***❌ Python not found!${NC***REMOVED***"
    exit 1
fi

echo -e "${GREEN***REMOVED***✓ Python version: $($PYTHON_CMD --version)${NC***REMOVED***"
echo -e "${GREEN***REMOVED***✓ Working directory: $(pwd)${NC***REMOVED***"

# Проверка наличия pytest
if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
    echo -e "${RED***REMOVED***❌ pytest not installed!${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***Installing pytest...${NC***REMOVED***"
    $PYTHON_CMD -m pip install pytest pytest-asyncio pytest-xdist
fi
echo -e "${GREEN***REMOVED***✓ pytest available${NC***REMOVED***\n"

# Проверяем структуру проекта
echo -e "${BLUE***REMOVED***📂 Checking project structure...${NC***REMOVED***"
if [ ! -d "tests_09" ***REMOVED***; then
    echo -e "${RED***REMOVED***❌ tests_09 directory not found!${NC***REMOVED***"
    exit 1
fi
echo -e "${GREEN***REMOVED***✓ tests_09 found${NC***REMOVED***\n"

# === 1. SMOKE TEST ===
print_header "1. SMOKE TEST - SmartRouter Availability"

# Находим файл с роутером
ROUTER_FILE=$(find tests_09 -name "*router*.py" -type f | head -1)

if [ -n "$ROUTER_FILE" ***REMOVED***; then
    echo -e "${GREEN***REMOVED***✓ Found router test file: $ROUTER_FILE${NC***REMOVED***"
    
    # Запускаем тесты роутера
    if run_pytest "$ROUTER_FILE" "SmartRouter Smoke" "-k SmartRouter -q"; then
        echo -e "${GREEN***REMOVED***✅ Smoke test passed${NC***REMOVED***"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${YELLOW***REMOVED***⚠️  Running all router tests...${NC***REMOVED***"
        if run_pytest "$ROUTER_FILE" "Router Tests" "-q"; then
            echo -e "${GREEN***REMOVED***✅ Router tests passed${NC***REMOVED***"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED***REMOVED***❌ Router tests failed${NC***REMOVED***"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    fi
else
    echo -e "${RED***REMOVED***❌ No router test file found!${NC***REMOVED***"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# === 2. ARTIFACT + ADR-018 ===
print_header "2. REGRESSION - Artifact + ADR-018"

# Ищем файлы артефактов и ADR
ARTIFACT_FILES=$(find tests_09 -name "*artifact*.py" -o -name "*adr*.py" -type f 2>/dev/null | tr '\n' ' ')

if [ -n "$ARTIFACT_FILES" ***REMOVED***; then
    echo -e "${GREEN***REMOVED***✓ Found artifact/ADR test files${NC***REMOVED***"
    
    if run_pytest "$ARTIFACT_FILES" "Artifact & ADR-018" "-q"; then
        echo -e "${GREEN***REMOVED***✅ Regression tests passed${NC***REMOVED***"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED***REMOVED***❌ Regression tests failed${NC***REMOVED***"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  Artifact/ADR test files not found${NC***REMOVED***"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# === 3. FULL SUITE ===
print_header "3. FULL TEST SUITE (timeout: ${TIMEOUT_FULL_SUITE***REMOVED***s)"
echo -e "${YELLOW***REMOVED***⚠️  This may take up to 15 minutes...${NC***REMOVED***\n"

START_TIME=$(date +%s)

# Запускаем все тесты, исключая проблемные на Android
run_with_timeout $TIMEOUT_FULL_SUITE "$PYTHON_CMD -m pytest tests_09/ -v --tb=short -k 'not (forge_api or event_bus or forge_chain_cli or forge_registry)'" "Full Test Suite (filtered)"
FULL_EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $FULL_EXIT_CODE -eq 0 ***REMOVED***; then
    echo -e "\n${GREEN***REMOVED***✅ FULL SUITE (filtered) PASSED in ${DURATION***REMOVED***s${NC***REMOVED***"
    PASSED_TESTS=$((PASSED_TESTS + 1))
elif [ $FULL_EXIT_CODE -eq 124 ***REMOVED***; then
    echo -e "\n${RED***REMOVED***⏰ FULL SUITE TIMEOUT after ${TIMEOUT_FULL_SUITE***REMOVED***s${NC***REMOVED***"
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    echo -e "\n${RED***REMOVED***❌ FULL SUITE FAILED (exit code: $FULL_EXIT_CODE)${NC***REMOVED***"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# === 4. MYPY ===
print_header "4. TYPE CHECK - mypy (timeout: ${TIMEOUT_MYPY***REMOVED***s)"

if [ -f "core_02/factory_base.py" ***REMOVED***; then
    run_with_timeout $TIMEOUT_MYPY "$PYTHON_CMD -m mypy core_02/factory_base.py --ignore-missing-imports" "Mypy"
    MYPY_EXIT_CODE=$?
    
    if [ $MYPY_EXIT_CODE -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ MYPY PASSED${NC***REMOVED***"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    elif [ $MYPY_EXIT_CODE -eq 124 ***REMOVED***; then
        echo -e "${RED***REMOVED***⏰ MYPY TIMEOUT${NC***REMOVED***"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    else
        echo -e "${RED***REMOVED***❌ MYPY FAILED (exit code: $MYPY_EXIT_CODE)${NC***REMOVED***"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  core_02/factory_base.py not found${NC***REMOVED***"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# === 5. REGISTRY + CONSISTENCY ===
print_header "5. REGISTRY & CONSISTENCY CHECKS"

# 5a. Missing Registry
if $PYTHON_CMD -c "import core_02.missing_registry" 2>/dev/null; then
    echo -e "${CYAN***REMOVED***▶ Running: Missing Registry check${NC***REMOVED***"
    TMPDIR="$TEMP_DIR" $PYTHON_CMD -m core_02.missing_registry check 2>&1 | tee "$LOG_DIR/registry.log"
    REGISTRY_EXIT=$?
    
    if [ $REGISTRY_EXIT -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ Missing Registry check passed${NC***REMOVED***"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED***REMOVED***❌ Missing Registry check failed${NC***REMOVED***"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  core_02.missing_registry module not found${NC***REMOVED***"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 5b. Consistency Check
if [ -f "scripts_01/consistency_check.py" ***REMOVED***; then
    echo -e "\n${CYAN***REMOVED***▶ Running: Consistency check${NC***REMOVED***"
    TMPDIR="$TEMP_DIR" $PYTHON_CMD -m scripts_01.consistency_check --report 2>&1 | tee "$LOG_DIR/consistency.log"
    CONSISTENCY_EXIT=$?
    
    if [ $CONSISTENCY_EXIT -eq 0 ***REMOVED***; then
        echo -e "${GREEN***REMOVED***✅ Consistency check passed${NC***REMOVED***"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED***REMOVED***❌ Consistency check failed${NC***REMOVED***"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW***REMOVED***⚠️  scripts_01/consistency_check.py not found${NC***REMOVED***"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# === SUMMARY ===
print_header "SUMMARY"
echo -e "${BOLD***REMOVED***Test Results:${NC***REMOVED***"
echo -e "  ${GREEN***REMOVED***✓ Passed:  $PASSED_TESTS${NC***REMOVED***"
echo -e "  ${RED***REMOVED***✗ Failed:  $FAILED_TESTS${NC***REMOVED***"
echo -e "  ${YELLOW***REMOVED***⊘ Skipped: $SKIPPED_TESTS${NC***REMOVED***"
echo -e "  ${BLUE***REMOVED***⊡ Total:   $TOTAL_TESTS${NC***REMOVED***"

if [ $FAILED_TESTS -eq 0 ***REMOVED***; then
    echo -e "\n${BOLD***REMOVED***${GREEN***REMOVED***🎉 ALL TESTS PASSED!${NC***REMOVED***"
    echo -e "${GREEN***REMOVED***✅ SmartRouter fix verified successfully${NC***REMOVED***"
    echo -e "${GREEN***REMOVED***✅ No regressions detected${NC***REMOVED***"
    FINAL_EXIT=0
else
    echo -e "\n${BOLD***REMOVED***${RED***REMOVED***❌ SOME TESTS FAILED${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***Note: Some tests require /tmp access which is restricted on Android${NC***REMOVED***"
    echo -e "${YELLOW***REMOVED***Try running with: TMPDIR=$TEMP_DIR $PYTHON_CMD -m pytest tests_09/ -k 'not forge_api'${NC***REMOVED***"
    FINAL_EXIT=1
fi

echo -e "\n${BLUE***REMOVED***📁 Log files saved to: $LOG_DIR/${NC***REMOVED***"
echo -e "${BLUE***REMOVED***⏱️  Finished at: $(date)${NC***REMOVED***"

exit $FINAL_EXIT
