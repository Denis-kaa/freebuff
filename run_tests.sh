#!/data/data/com.termux/files/usr/bin/bash

cd /storage/emulated/0/PROJECTS/workstation/freebuff

echo "========================================"
echo "  RUNNING TESTS (Termux)"
echo "========================================"
echo "Python: $(python3 --version)"
echo ""

# 1. SMOKE
echo "=== 1. ROUTER SMOKE ==="
python3 -m pytest tests_09/core/test_router.py -v -k "SmartRouter" -s 2>&1 | head -50
echo ""

# 2. ARTIFACT + ADR
echo "=== 2. ARTIFACT + ADR ==="
python3 -m pytest tests_09/test_artifact.py tests_09/test_adr018_factory_forge_bridge.py -v -s 2>&1 | head -50
echo ""

# 3. FULL (быстро, 5 ошибок)
echo "=== 3. FULL SUITE (maxfail=5) ==="
python3 -m pytest tests_09/ -v --tb=short --maxfail=5 -s 2>&1 | head -100
echo ""

# 4. MYPY
echo "=== 4. MYPY ==="
python3 -m mypy core_02/factory_base.py --ignore-missing-imports 2>&1 | head -30
echo ""

# 5. REGISTRY
echo "=== 5. REGISTRY ==="
python3 -m core_02.missing_registry check 2>&1
echo ""
python3 -m scripts_01.consistency_check --report 2>&1 | head -20

echo ""
echo "========================================"
echo "  DONE"
echo "========================================"
