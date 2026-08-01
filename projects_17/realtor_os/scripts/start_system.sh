#!/usr/bin/env bash
# start_system.sh — аудит среды и запуск Realtor OS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0***REMOVED******REMOVED***")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR***REMOVED***/.." && pwd)"
LOG_FILE="${PROJECT_ROOT***REMOVED***/logs/start_system.log"
mkdir -p "${PROJECT_ROOT***REMOVED***/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')***REMOVED*** $*" | tee -a "${LOG_FILE***REMOVED***"
***REMOVED***

log "=== Realtor OS environment audit ==="

# Check Termux
if [[ -z "${PREFIX:-***REMOVED***" ***REMOVED******REMOVED***; then
    log "WARNING: PREFIX not set; may not be running in Termux."
fi

# Check Python
if ! command -v python >/dev/null 2>&1; then
    log "ERROR: python not found"
    exit 1
fi
PYTHON_VERSION=$(python --version)
log "Python: ${PYTHON_VERSION***REMOVED***"

# Check Tesseract
if command -v tesseract >/dev/null 2>&1; then
    log "Tesseract: $(tesseract --version 2>&1 | head -1)"
else
    log "WARNING: tesseract not installed. OCR will not work."
fi

# Check Ollama
if command -v ollama >/dev/null 2>&1; then
    log "Ollama: $(ollama --version 2>&1 | head -1)"
else
    log "WARNING: ollama not installed. LLM integration will not work."
fi

# Check .env
if [[ -f "${PROJECT_ROOT***REMOVED***/.env" ***REMOVED******REMOVED***; then
    log ".env present"
else
    log "WARNING: .env not found. Copy .env.example to .env and fill secrets."
fi

# Create dirs
mkdir -p "${PROJECT_ROOT***REMOVED***/data" "${PROJECT_ROOT***REMOVED***/logs" "${PROJECT_ROOT***REMOVED***/companion"

# Generate manifest
PYTHONPATH="${PROJECT_ROOT***REMOVED***/src" python -m realtor_os.cli manifest >/dev/null 2>&1 || true

log "=== Audit complete ==="
