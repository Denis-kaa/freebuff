#!/usr/bin/env python3
"""scripts_01/content_factory.py — Content Factory (Phase 12, ADR-013 BaseFactory).

Phase 9: первый доменный Factory-adapter поверх универсального ядра Phase 8.
Phase 12: рефакторинг — наследует shared-логику из core_02.factory_base.BaseFactory.
Subclass добавляет ONLY домен-специфичные поля (article/book/report normalization)
через константы + нормализацию.

Phase 13 G-13.1 (ADR-015): per-instance warnings. `_LAZY_IMPORT_ERRORS` dropped
from imports + __all__ — consumers must use ``inst._import_warnings`` instead.

Инварианты (Phase 9/12 — неизменны):
- НЕ является content-движком: производство — через существующий ForgeFacade.
- CAN-16 ADDITIVE: НЕ модифицирует ForgePipeline / ForgeFacade / Blueprint / SI.
- ScenarioIntelligence НЕ знает о существовании ContentFactory.

CLI:
    content_factory resolve <opportunity_id> [--json]
    content_factory run <opportunity_id> [--dry-run] [--project-root PATH] [--json]
"""

from __future__ import annotations

import sys
}
from typing import Any, Dict, Optional

from core_02.factory_base import BaseFactory, ExecutionRequest


class ContentFactory(BaseFactory):
    """Первый доменный Factory-adapter (Phase 9, promt 092; refactored Phase 12).

    Capabilities: article_generation, book_generation, report_generation.
    ArtifactKind: content_artifact. Domain: Content.
    """

    CAPABILITIES = ("article_generation", "book_generation", "report_generation")
    ROLE_IDS = ("explainer", "documenter", "retrospective")
    ARTIFACT_KIND = "content_artifact"
    ID_PREFIX = "art"
    TAG_PREFIX = "content_factory"
    TITLE_PREFIX = "content"
    PROG = "content_factory"
    FACTORY_ID = "content"

    def normalize_input(self, opp: Any) -> Dict[str, Any]:
        """Opportunity → нормализованный контентный вход (title/desc/sources).

        Только общие поля Opportunity (24-полевой контракт §E) — никаких новых
        систем хранения. Доменная специфика Content = сам Opportunity целиком.
        """
        return {
            "title": getattr(opp, "title", "") or "",
            "description": getattr(opp, "description", "") or "",
            "source": getattr(opp, "source", "") or "",
            "source_path": getattr(opp, "source_path", "") or "",
            "evidence_path": getattr(opp, "evidence_path", "") or "",
            "provenance": dict(getattr(opp, "provenance", {}) or {}),
            "related_whims": list(getattr(opp, "related_whims", None) or []),
        }


# ─── Backward-compat module-level aliases (Phase 9 tests reference these) ───

# Re-export ExecutionRequest from BaseFactory (backward compat).
__all__ = [
    "ContentFactory",
    "ExecutionRequest",
    "CONTENT_CAPABILITIES",
    "CONTENT_ROLE_IDS",
]

CONTENT_CAPABILITIES: tuple = ContentFactory.CAPABILITIES
CONTENT_ROLE_IDS: tuple = ContentFactory.ROLE_IDS


if __name__ == "__main__":
    sys.exit(ContentFactory.main())
