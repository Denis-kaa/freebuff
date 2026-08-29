#!/usr/bin/env bash
# run_tests_fast.sh — быстрый параллельный прогон тестов (v5.189.10).
#
# Полный сьюит (2 893 теста) в один поток: ~15 мин. С pytest-xdist (-n 4,
# --dist loadfile): ~5-7 мин. С -m "not slow" (пропуск интеграционных
# subprocess/сетевых тестов): ещё быстрее для fast-feedback цикла.
#
# Использование:
#   bash run_tests_fast.sh                    # -n 4 --dist loadfile
#   bash run_tests_fast.sh -- -m "not slow"   # быстрый цикл без slow
#   bash run_tests_fast.sh -n 2               # меньше параллелизма
#
# Канонический полный прогон остаётся: python -m pytest tests_09/ -q
set -euo pipefail
cd "$(dirname "$0")"

WORKERS="${PYTEST_WORKERS:-4***REMOVED***"
ARGS=()
if [[ "${1:-***REMOVED***" == "--" ***REMOVED******REMOVED***; then
    shift
    ARGS+=("$@")
fi

# Предусловие: pytest-xdist должен быть установлен (python -m pytest -n ...)
if ! python -c 'import xdist' 2>/dev/null; then
    echo "ERROR: pytest-xdist не установлен. Выполните: pip install pytest-xdist" >&2
    exit 1
fi

# --dist loadgroup: файлы с маркером xdist_group(forge_real_registry)
# (forge_api / forge_chain_cli / forge_chain_real_integration) сериализуются
# на одном воркере — они читают/пишут реальный data_13/forge_registry.yaml
# и при параллелизме дают torn-read гонки (v5.189.12). Остальные файлы
# распределяются параллельно как обычно.
echo "== pytest-xdist: -n $WORKERS --dist loadgroup (${ARGS[****REMOVED***:-no extra args***REMOVED***) =="
python -m pytest tests_09/ -n "$WORKERS" --dist loadgroup -q "${ARGS[@***REMOVED******REMOVED***"
