#!/usr/bin/env python3
"""scripts_01/test_factory.py — Test Factory (Phase 12, ADR-013 BaseFactory).

Phase 11: третий доменный Factory-adapter. Phase 12: рефакторинг — наследует
shared-логику из core_02.factory_base.BaseFactory; subclass добавляет ONLY
test-специфичные поля (requested_code/assertion/expected_outcome/context).

Каноны Phase 11 + Phase 12:
- CAN-16 ADDITIVE: НЕ модифицирует ContentFactory / ResearchFactory / ForgeFacade.
- NOT PRODUCTION per promt93 §11 Variant B (MISSING PRODUCTION EXECUTION
  CAPABILITY — нет реального Code/Verifier execution pipeline).
- Domain-isolation: SI НЕ знает о TestFactory (negative test_13a).
- Capability: "code" (Missing Cap #0 Blueprint).

CLI:
    test_factory resolve <opportunity_id> [--json***REMOVED***
    test_factory run <opportunity_id> [--dry-run***REMOVED*** [--project-root PATH***REMOVED*** [--json***REMOVED***
"""

from __future__ import annotations

import sys
***REMOVED***
from typing import Any, Dict

from core_02.factory_base import BaseFactory, ExecutionRequest


class TestFactory(BaseFactory):
    """Третий доменный Factory-adapter (Phase 11; refactored Phase 12).

    Capabilities: code. ArtifactKind: verifier_report. Domain: Verifier.
    Status: material (NOT PRODUCTION per promt93 §11 Variant B).
    """

    CAPABILITIES = ("code",)
    ROLE_IDS = ("explainer", "documenter", "retrospective")
    ARTIFACT_KIND = "verifier_report"
    ID_PREFIX = "tst"
    TAG_PREFIX = "test_factory"
    TITLE_PREFIX = "test"
    PROG = "test_factory"
    FACTORY_ID = "test"

    def normalize_input(self, opp: Any) -> Dict[str, Any***REMOVED***:
        """Opportunity → нормализованный test-вход (requested_code/assertion/context).

        Извлекает test-специфичные поля, дефолтит на title/description как
        fallback. Все существующие поля Opportunity — базово.
        """
        prov = dict(getattr(opp, "provenance", {***REMOVED***) or {***REMOVED***)
        test_block = prov.get("test") if isinstance(prov, dict) else None
        if not isinstance(test_block, dict):
            test_block = getattr(opp, "test", {***REMOVED***) or {***REMOVED***
        return {
            "title": getattr(opp, "title", "") or "",
            "description": getattr(opp, "description", "") or "",
            "source": getattr(opp, "source", "") or "",
            "source_path": getattr(opp, "source_path", "") or "",
            "evidence_path": getattr(opp, "evidence_path", "") or "",
            "provenance": prov,
            "related_whims": list(getattr(opp, "related_whims", None) or [***REMOVED***),
            # Test-specific
            "requested_code": (
                test_block.get("requested_code")
                or prov.get("requested_code")
                or getattr(opp, "title", "")
                or ""
            ),
            "test_assertion": (
                test_block.get("assertion")
                or prov.get("assertion")
                or "deterministic assertion pending"
            ),
            "expected_outcome": (
                test_block.get("expected_outcome")
                or prov.get("expected_outcome")
                or "ok"
            ),
            "verification_context": (
                test_block.get("context")
                or prov.get("context")
                or getattr(opp, "description", "")
                or ""
            ),
        ***REMOVED***


# ─── Backward-compat module-level aliases ───

__all__ = [
    "TestFactory",
    "ExecutionRequest",
    "TEST_CAPABILITIES",
    "TEST_ROLE_IDS",
***REMOVED***

TEST_CAPABILITIES: tuple = TestFactory.CAPABILITIES
TEST_ROLE_IDS: tuple = TestFactory.ROLE_IDS


if __name__ == "__main__":
    sys.exit(TestFactory.main())
