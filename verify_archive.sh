#!/bin/bash
# Verify audit-ready archive per ROADMAP_MIN_V0_1 §11 + 065_03_vkusvill_research_audit close-out
# Usage: bash verify_archive.sh <archive>.tar.gz
set -e
ARCHIVE="${1:-promts_59_67_complete_work_*.tar.gz***REMOVED***"

echo '═══ Independent Audit: Archive Verification ═══'
echo ''
echo '1. Existence:'
ls -la "$ARCHIVE" 2>&1 | head -3
echo ''
echo '2. SHA256:'
sha256sum "$ARCHIVE" 2>&1 | awk '{print $1***REMOVED***'
echo ''
echo '3. Entry count:'
TAR_COUNT=$(tar -tzf "$ARCHIVE" 2>/dev/null | wc -l)
echo "Total entries in archive: $TAR_COUNT (expected >=60)"
echo ''
echo '4. Required sections (11 keywords):'
for keyword in "AUDIT_WS_OS" "vkusvill_research" "vkusvill_demo" "WORKSPACE_OS" "ROADMAP_MIN_V0_1" "ROADMAP_FORGE" "ROADMAP_PHASE2" "COVER_LETTER" "09_audit_promt64" "RFC_BUFFY_FORGE" "MANIFEST"; do
  cnt=$(tar -tzf "$ARCHIVE" 2>/dev/null | grep -c "$keyword" 2>/dev/null || echo 0)
  status='✓'
  if [ "$cnt" -lt 1 ***REMOVED***; then status='✗'; fi
  echo "  $status $keyword: $cnt occurrences"
done
echo ''
echo '═══ Verification complete ═══'
echo 'If all 11 keywords show ✓, archive is independent-audit ready.'
