"""scripts_01/_curated_llm_gateway.py — curated mock ModelGateway for gap analysis.

Used in scripts_01/taxonomy_gap_report.py + tests_09/test_taxonomy_gap_report.py.

Adheres to ``LLM_SYSTEM_PROMPT`` in ``core_02/capability_gap_auditor.py``:
  * 18 capabilities (≥18 per designer contract).
  * Mix EXPLICIT (overlap deterministic baseline) + INFERRED.
  * ``KINDS ∈ {tool, module, role, engine***REMOVED***`` (closed set, ANTI-6b).
  * Each item carries ``_provenance`` (audit trail; silently ignored by
    ``_parse_llm_response`` since it filters only against literal JSON keys
    item_id/kind/description/confidence/explicit).

This is NOT a real LLM. It's a deterministic fixture for reproducible diff
analysis without real LLM access. The contents mirror what an LLM targeted at
``projects_17/vocal/задача.md`` would produce given ``LLM_SYSTEM_PROMPT`` rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


__all__ = ["CuratedResponse", "CuratedLlmGateway"***REMOVED***


# 18 capabilities: 8 EXPLICIT (overlap deterministic baseline v5.189.61)
# + 10 INFERRED, split into Section A (7 already in TAXONOMY but no keyword
# trigger on vocal/задача.md text) and Section B (3 truly missing from TAXONOMY).
_CURATED_JSON = """```json
[
  {"item_id": "anti_pattern_miner", "kind": "tool", "factory": "research", "description": "Anti-pattern mining (закрытые курсы/школы)", "confidence": 1.0, "explicit": true, "_provenance": "section 7 explicit"***REMOVED***,
  {"item_id": "business_model_constructor", "kind": "module", "factory": "doc", "description": "Конструктор бизнес-моделей (14 полей)", "confidence": 1.0, "explicit": true, "_provenance": "section 9 explicit"***REMOVED***,
  {"item_id": "claim_source_tracker", "kind": "module", "factory": "docs_10", "description": "Claim-source-tracker (теги [fact***REMOVED***)", "confidence": 1.0, "explicit": true, "_provenance": "section 12 explicit"***REMOVED***,
  {"item_id": "devil_advocate_pass", "kind": "module", "factory": "thinker", "description": "Adversarial review (kill-questions)", "confidence": 1.0, "explicit": true, "_provenance": "section 11 explicit"***REMOVED***,
  {"item_id": "lisa_estimator", "kind": "tool", "factory": "research", "description": "Estimation / Unit-economics (teacher time)", "confidence": 1.0, "explicit": true, "_provenance": "section 5 explicit"***REMOVED***,
  {"item_id": "mvp_design_wizard", "kind": "module", "factory": "doc", "description": "MVP-механики (предпродажа, pilot group)", "confidence": 1.0, "explicit": true, "_provenance": "section 8 explicit"***REMOVED***,
  {"item_id": "pricing_enumerator", "kind": "tool", "factory": "research", "description": "Верифицированный прайс-сканер (реальный price)", "confidence": 1.0, "explicit": true, "_provenance": "section 6 explicit"***REMOVED***,
  {"item_id": "qualitative_review_analyzer", "kind": "tool", "factory": "research", "description": "Качественный анализ отзывов (pain-points)", "confidence": 1.0, "explicit": true, "_provenance": "section 3 explicit"***REMOVED***,

  {"item_id": "research_web", "kind": "tool", "factory": "research", "description": "Web Research для поиска источников", "confidence": 0.85, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY, no keyword trigger on this text); needed to gather market context"***REMOVED***,
  {"item_id": "competitor_matrix_builder", "kind": "tool", "factory": "research", "description": "Конкурентная матрица (landscape)", "confidence": 0.80, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); market analysis implies competitor perspective"***REMOVED***,
  {"item_id": "hypothesis_ledger", "kind": "module", "factory": "docs_10", "description": "Hypothesis ledger (статусы open/supported/refuted)", "confidence": 0.85, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); complex analysis requires tracking"***REMOVED***,
  {"item_id": "corpus_persistence", "kind": "tool", "factory": "nil", "description": "Corpus-persistence между сессиями", "confidence": 0.95, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); large body requires persistence"***REMOVED***,
  {"item_id": "vanity_metric_filter", "kind": "module", "factory": "doc", "description": "Vanity-metric filter (что НЕ считать успехом)", "confidence": 0.75, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); analytics filtering"***REMOVED***,
  {"item_id": "weighted_scoring_engine", "kind": "engine", "factory": "nil", "description": "Weighted scoring engine (multi-criteria × weights)", "confidence": 0.88, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); comparison requires scoring"***REMOVED***,
  {"item_id": "persona_funnel_analyzer", "kind": "tool", "factory": "research", "description": "Persona funnel анализ (фан↔ученик)", "confidence": 0.70, "explicit": false, "_provenance": "Inferred (Section A — in TAXONOMY); audience assessment"***REMOVED***,

  {"item_id": "tone_of_voice_auditor", "kind": "tool", "factory": "research", "description": "Анализ тональности (ToV) конкурентов", "confidence": 0.65, "explicit": false, "_provenance": "Inferred (Section B — NOT-IN-TAXONOMY); brand-voice audit missing from TAXONOMY"***REMOVED***,
  {"item_id": "hallucination_detector", "kind": "engine", "factory": "governance", "description": "Детектор галлюцинаций в отчётах", "confidence": 0.80, "explicit": false, "_provenance": "Inferred (Section B — NOT-IN-TAXONOMY); meta-audit tool missing"***REMOVED***,
  {"item_id": "cost_estimator", "kind": "tool", "factory": "infra", "description": "Оценка стоимости генерации (tokens)", "confidence": 0.60, "explicit": false, "_provenance": "Inferred (Section B — NOT-IN-TAXONOMY); tokens/LLM infra-tool missing"***REMOVED***
***REMOVED***
```"""


@dataclass
class CuratedResponse:
    """Duck-typed ModelResponse (only ``.content`` is consumed)."""

    content: str
    _provenance: str = "curated_llm_gateway"


class CuratedLlmGateway:
    """Curated mock ModelGateway для TAXONOMY gap analysis.

    Implements the contract expected by
    ``core_02.capability_gap_auditor.CapabilityGapLlmExecutor._extract_via_llm``:
    ``generate_by_capabilities(cap_list: List[str***REMOVED***, messages: List[dict***REMOVED***) -> object``
    с ``.content`` attribute (str, JSON-array wrapped in ````​```json ... ```​````).
    """

    def __init__(self, response_content: Optional[str***REMOVED*** = None) -> None:
        self.response_content = response_content if response_content is not None else _CURATED_JSON
        self.call_count = 0
        self.last_capabilities: List[str***REMOVED*** = [***REMOVED***
        self.last_messages: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***

    def generate_by_capabilities(
        self,
        capabilities: List[str***REMOVED***,
        messages: List[Dict[str, Any***REMOVED******REMOVED***,
    ) -> CuratedResponse:
        self.call_count += 1
        self.last_capabilities = list(capabilities)
        self.last_messages = list(messages)
        return CuratedResponse(content=self.response_content)
