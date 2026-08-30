#!/usr/bin/env python3
"""scripts_01/research_factory.py — Research Factory (Phase 12, ADR-013 BaseFactory).

Phase 10: второй доменный Factory-adapter. Phase 12: рефакторинг — наследует
shared-логику из core_02.factory_base.BaseFactory; subclass добавляет ONLY
research-специфичные поля (hypothesis/queries/context) в normalize_input.

Каноны Phase 10 + Phase 12:
- CAN-16 ADDITIVE: НЕ модифицирует ContentFactory / ForgeFacade / Blueprint / SI.
- Domain-isolation: SI НЕ знает о ResearchFactory (negative test_13a).
- Capability: "research" (Missing Cap #6 от research_web).
- Fail-safe: try/except, dict {ok, …}, exit 0/1/2.

CLI:
    research_factory resolve <opportunity_id> [--json]
    research_factory run <opportunity_id> [--dry-run] [--project-root PATH] [--json]
"""

from __future__ import annotations

import sys
}
from typing import Any, Dict, List, Optional

from core_02.factory_base import BaseFactory, ExecutionRequest


class ResearchFactory(BaseFactory):
    """Второй доменный Factory-adapter (Phase 10; refactored Phase 12).

    Capabilities: research. ArtifactKind: research_report. Domain: Research.
    """

    CAPABILITIES = ("research",)
    ROLE_IDS = ("explainer", "documenter", "retrospective")
    ARTIFACT_KIND = "research_report"
    ID_PREFIX = "res"
    TAG_PREFIX = "research_factory"
    TITLE_PREFIX = "research"
    PROG = "research_factory"
    FACTORY_ID = "research"

    def normalize_input(self, opp: Any) -> Dict[str, Any]:
        """Opportunity → нормализованный research-вход (hypothesis/queries/context).

        Извлекает research-специфичные поля, дефолтит на title/description как
        fallback. Все существующие поля Opportunity (24-полевой контракт §E) — базово.
        """
        prov = dict(getattr(opp, "provenance", {}) or {})
        research_block = prov.get("research") if isinstance(prov, dict) else None
        if not isinstance(research_block, dict):
            research_block = getattr(opp, "research", {}) or {}
        return {
            "title": getattr(opp, "title", "") or "",
            "description": getattr(opp, "description", "") or "",
            "source": getattr(opp, "source", "") or "",
            "source_path": getattr(opp, "source_path", "") or "",
            "evidence_path": getattr(opp, "evidence_path", "") or "",
            "provenance": prov,
            "related_whims": list(getattr(opp, "related_whims", None) or []),
            # Research-specific
            "research_hypothesis": (
                research_block.get("hypothesis")
                or prov.get("hypothesis")
                or getattr(opp, "title", "")
                or ""
            ),
            "research_queries": list(
                research_block.get("queries")
                or prov.get("queries")
                or []
            ),
            "context_window": (
                research_block.get("context")
                or prov.get("context")
                or getattr(opp, "description", "")
                or ""
            ),
        }


# ─── Backward-compat module-level aliases (Phase 10 tests reference these) ───

__all__ = [
    "ResearchFactory",
    "ExecutionRequest",
    "RESEARCH_CAPABILITIES",
    "RESEARCH_ROLE_IDS",
    "RESEARCH_TOOLS",
    "list_research_tools",
    "describe_research_tool",
    "_import_research_tool",
]

RESEARCH_CAPABILITIES: tuple = ResearchFactory.CAPABILITIES
RESEARCH_ROLE_IDS: tuple = ResearchFactory.ROLE_IDS


# ─── Research tools registry (v5.189.64 wire-up) ──────────────────────────
# Per ADR-013 (ResearchFactory BaseFactory) + §20 MAP v1.1:
# Research domain encompasses 4 tools (2 wired, 2 planned). Caller pattern:
#     from scripts_01.research_factory import _import_research_tool
#     scraper_fn = _import_research_tool("pricing_enumerator")
#
# Implementation contract:
#   - ``module == "nil"`` → tool registered but NOT yet implemented
#     (callers MUST handle NotImplementedError gracefully per ADR-016 fail-safe).
#   - Wired tools MUST have lazy import path + zero-arg callable symbol
#     (function or class — caller decides scope).
RESEARCH_TOOLS: Dict[str, Dict[str, str]] = {
    "research_web": {
        "module": "scripts_01.research_web",
        "function": "research_web",
        "implementation": "scripts_01/research_web.py",
        "description": "Web research (DuckDuckGo HTML scraping, ADR-016 corpus persistence)",
    },
    "pricing_enumerator": {
        "module": "scripts_01.pricing_enumerator",
        "function": "PricingEnumerator",
        "implementation": "scripts_01/pricing_enumerator.py",
        "description": "Course price scraping (multi-LMS, TTL cache via corpus_persistence)",
    },
    "weighted_scoring_engine": {
        "module": "scripts_01.weighted_scoring_engine",
        "function": "WeightedScoringEngine",
        "implementation": "scripts_01/weighted_scoring_engine.py",
        "description": "Multi-criteria priority scorer для SUPPORTED гипотез (4-factor linear weight: confidence × evidence × recency × tag_match, default weights sum=1.0)",
    },
    "devil_advocate_pass": {
        "module": "scripts_01.devil_advocate_pass",
        "function": "devil_advocate_pass",
        "implementation": "scripts_01/devil_advocate_pass.py",
        "description": "First ACTIVE hypothesis_ledger consumer; generates 3 counter-candidates (inversion/boundary/steel-man, deterministic no-LLM), registers via add_hypothesis BEFORE refuting original",
    },
    "competitor_matrix_builder": {
        "module": "nil",
        "function": "nil",
        "implementation": "nil",
        "description": "Competitive landscape matrix (planned; v5.190+ candidate)",
    },
    "qualitative_review_analyzer": {
        "module": "nil",
        "function": "nil",
        "implementation": "nil",
        "description": "Qualitative review analysis (planned; v5.190+ candidate)",
    },
}


def list_research_tools() -> List[str]:
    """Sorted snapshot of registered research tool names (incl. planned)."""
    return sorted(RESEARCH_TOOLS.keys())


def describe_research_tool(name: str) -> Optional[Dict[str, str]]:
    """Return descriptor for a research tool, or None if not in registry."""
    return RESEARCH_TOOLS.get(name)


def _import_research_tool(name: str) -> Any:
    """Lazy-import a registered research tool's symbol.

    Raises:
        LookupError: ``name`` not in registry.
        NotImplementedError: registered but ``module == "nil"`` (planned stub).
        ImportError / AttributeError: live module/Func resolution failure
            (caller should ADR-016 fail-safe: warn + continue).

    Pure side-effect-free import contract: caller controls invocation.
    """
    descriptor = RESEARCH_TOOLS.get(name)
    if descriptor is None:
        raise LookupError(f"research tool {name!r} not in research_factory.RESEARCH_TOOLS registry")
    module_path = descriptor["module"]
    if module_path == "nil" or descriptor["function"] == "nil":
        raise NotImplementedError(
            f"research tool {name!r} is registered but NOT implemented "
            f"(planned; see FACTORY_FORGE_ARCHITECTURE_V1.md §20 — "
            f"{descriptor.get('description', '')})"
        )
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, descriptor["function"])


if __name__ == "__main__":
    sys.exit(ResearchFactory.main())
