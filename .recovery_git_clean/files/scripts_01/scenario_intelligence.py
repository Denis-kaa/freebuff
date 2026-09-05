#!/usr/bin/env python3
"""scripts_01/scenario_intelligence.py — Universal Scenario Intelligence (Phase 8).

Domain-neutral decision layer per ``pompts_11/091_19_phase8_universal_scenario_intelligence.md``
(PHASE 8 — UNIVERSAL SCENARIO INTELLIGENCE). Answers ONLY: "which implementation approach best fits
the current Opportunity in the current project context?" — it does NOT produce.

Chain (Phase 8 §2):

    OPPORTUNITY
       ↓
    SCENARIO DISCOVERY      (ScenarioRegistry as catalog — NO second registry)
       ↓
    CANDIDATE SCENARIOS     (one Opportunity → many candidates, any domain)
       ↓
    EVALUATION              (relevance / capability / history / feasibility)
       ↓
    RANKING                 (composite score, explainable)
       ↓
    SELECTION               (ScenarioDecision with provenance)
       ↓
    CAPABILITY              (CapabilityRequirement — domain-neutral token)
       ↓
    FACTORY                 (FactoryRegistry.select_forge)
       ↓
    FORGE                   (ForgeFacade — execution boundary, unchanged)
       ↓
    ARTIFACT → FEEDBACK v0  (MemoryStore / LearningLoop — transparent, no ML)

Domain-neutrality invariant (§1/§4): NO hardcoded "content" dependency. Entities
are ScenarioCandidate / ScenarioDecision / CapabilityRequirement. Capabilities
are opaque tokens (article_generation, api_implementation, image_generation,
market_research, screenplay_development, ...) resolved via FactoryRegistry —
Phase 8 does NOT hardcode any of them.

Reuse (§5/§6/§12): ScenarioRegistry (catalog), FactoryRegistry (capability
selection), ForgeFacade (execution), MemoryStore/SemanticLayer/LearningLoop
(feedback + decision history). NO new DB, NO new registry, NO new event bus.

Events (§11): scenario.candidates.generated / scenario.evaluated /
scenario.selected / scenario.reselected (only when a previously deferred or
superseded scenario is re-selected).

CLI:

    scenario_intelligence discover <opportunity_id> [--top N***REMOVED*** [--json***REMOVED***
    scenario_intelligence select <opportunity_id> [--top N***REMOVED*** [--json***REMOVED***
    scenario_intelligence evaluate <opportunity_id> [--top N***REMOVED*** [--json***REMOVED***
    scenario_intelligence resolve <opportunity_id> [--json***REMOVED***
    scenario_intelligence feedback <opportunity_id> --outcome success|failure [--json***REMOVED***
    scenario_intelligence history [--limit N***REMOVED*** [--json***REMOVED***

Exit codes: 0 success/degraded-safe, 1 not-found/fail, 2 invalid input.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import uuid
import warnings
from dataclasses import dataclass, field, asdict
***REMOVED***
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports (additive, forward-portable — mirrors opportunity_engine).
#
# PHASE 14 (v5.189.34, ADR-015 mirror): module-level ``_LAZY_IMPORT_ERRORS`` is a
# DEPRECATED shim kept for backward-compat re-exports. It is NO LONGER appended
# to from within ScenarioIntelligence methods — per-instance warnings are
# canonical (``self._import_warnings``, fresh [***REMOVED*** per instance via __init__).
# See ADR-015 for migration rationale.
#
# PHASE 14 hardening (v5.189.36): rename backing list to ``__LAZY_IMPORT_ERRORS``
# (double-underscore prefix) so the PEP 562 module-level __getattr__ fires on
# every import/access of ``_LAZY_IMPORT_ERRORS`` and emits a one-shot
# ``DeprecationWarning`` pointing at ``inst._import_warnings``. The exported
# symbol name is preserved (still in __all__) so the migration path is
# transparent — mirrors core_02/factory_base.py v5.189.33.
__LAZY_IMPORT_ERRORS: List[str***REMOVED*** = [***REMOVED***  # backing for deprecated shim


def __getattr__(name: str) -> Any:
    """PEP 562 module-level __getattr__: intercept any access of
    ``_LAZY_IMPORT_ERRORS`` from outside this module and emit a
    ``DeprecationWarning`` pointing at ``inst._import_warnings``.

    Behavior (mirrors core_02/factory_base.py v5.189.33):
    *   First import (`from scripts_01.scenario_intelligence import _LAZY_IMPORT_ERRORS`)
        fires the warning (via stacklevel=2 → points at the call site).
    *   Per-Python warning caching, the default `default` filter shows it
        once per source location, so it does not flood.
    *   Internal methods NO LONGER import this symbol (v5.189.34),
        so they are unaffected.
    *   pytest-friendly: filterable via ``-W error::DeprecationWarning``
        or ``filterwarnings(["ignore", ..., DeprecationWarning, ...)``
        in pytest config; tests can also use
        ``warnings.catch_warnings(record=True)`` to assert emission.
    """
    if name == "_LAZY_IMPORT_ERRORS":
        warnings.warn(
            (
                "scripts_01.scenario_intelligence._LAZY_IMPORT_ERRORS is deprecated "
                "since v5.189.34 (deprecation notice emitted since v5.189.36); "
                "use ``inst._import_warnings`` on a "
                "ScenarioIntelligence instance instead. "
                "See ADR-015 for migration rationale."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return __LAZY_IMPORT_ERRORS
    raise AttributeError(f"module {__name__!r***REMOVED*** has no attribute {name!r***REMOVED***")


# ─── Constants ────────────────────────────────────────────────────────────

DEFAULT_DATA_PATH = Path("data_13/opportunities.yaml")
DEFAULT_MEMORY_DB = Path("data_13/context.db")
DEFAULT_HISTORY_PATH = Path("data_13/scenario_decisions.yaml")

# Evaluation weights — documented, sum = 1.0 (§6/§7 explainable ranking).
EVAL_WEIGHTS: Dict[str, float***REMOVED*** = {
    "relevance": 0.35,   # scenario↔opportunity fuzzy match (ScenarioRegistry)
    "capability": 0.25,  # capability availability (FactoryRegistry)
    "history": 0.20,     # previous executions (MemoryStore kind=scenario_decision)
    "feasibility": 0.20, # enabled + roles present + manifest valid
***REMOVED***

# Decision lifecycle (§10) — matches existing contract semantics.
DECISION_STATUSES: Tuple[str, ...***REMOVED*** = (
    "selected",
    "deferred",
    "superseded",
    "reselected",
    "unavailable",
)


# ─── Domain-neutral entities (§4) ─────────────────────────────────────────

@dataclass(frozen=True)
class ScenarioCandidate:
    """One candidate way to implement an Opportunity (domain-neutral)."""

    scenario_id: str
    display_name: str
    role_id: Optional[str***REMOVED*** = None
    score: float = 0.0
    reasons: List[str***REMOVED*** = field(default_factory=list)
    evidence: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    capability: Optional[str***REMOVED*** = None
    # Phase 13 G-11.6: full sorted+deduped capability tuple for set-membership
    # hard-gate in ``evaluate()`` (vs. ``capability`` which keeps first-element
    # for backward-compat in ``cap_avail``). Frozen dataclass: default factory
    # via ``field(default_factory=tuple)`` for immutability + empty default.
    scenario_caps: Tuple[str, ...***REMOVED*** = field(default_factory=tuple)
    available: bool = True


@dataclass(frozen=True)
class CapabilityRequirement:
    """Domain-neutral capability token required to execute a scenario."""

    capability: str
    scenario_id: str
    role_id: Optional[str***REMOVED*** = None


@dataclass
class ScenarioDecision:
    """Explainable selection result with full provenance (§7)."""

    opportunity_id: str
    project_id: str
    selected_scenario_id: Optional[str***REMOVED*** = None
    score: Optional[float***REMOVED*** = None
    reasons: List[str***REMOVED*** = field(default_factory=list)
    evidence: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    capability: Optional[str***REMOVED*** = None
    factory_id: Optional[str***REMOVED*** = None
    forge_id: Optional[str***REMOVED*** = None
    status: str = "selected"
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return asdict(self)


# ─── Helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _new_id() -> str:
    return f"sd-{uuid.uuid4().hex[:10***REMOVED******REMOVED***"


def _lazy_import(module_name: str, attr: str) -> Any:
    """Lazy import with top-level fallback (mirrors opportunity_engine)."""
    try:
        return getattr(__import__(module_name, fromlist=[attr***REMOVED***), attr)
    except ImportError:
        bare = module_name.rsplit(".", 1)[-1***REMOVED***
        try:
            return getattr(__import__(bare, fromlist=[attr***REMOVED***), attr)
        except ImportError:
            return None


def _emit_event(event_bus: Any, event_type: str, *, source: str, **payload: Any) -> None:
    """Best-effort canonical EventBus.publish. Never raises (§11)."""
    if event_bus is None:
        return
    try:
        from scripts_01.event_bus import Event
        event_bus.publish(Event(type=event_type, source=source, data=dict(payload)))
    except Exception:  # noqa: BLE001 — event failure must not break decision
        pass


# ─── Decision history persistence (NO new DB — YAML store, atomic) ────────

class DecisionHistoryStore:
    """YAML-backed history of ScenarioDecision records (data_13/scenario_decisions.yaml).

    Additive: separate lightweight store for decision history; knowledge content
    lives in MemoryStore (kind=scenario_decision) per §12. Atomic .tmp+replace.
    """

    def __init__(self, path: Path = DEFAULT_HISTORY_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = self._load()

    def _load(self) -> Dict[str, Dict[str, Any***REMOVED******REMOVED***:
        if not self.path.exists():
            return {***REMOVED***
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: dict(v) for k, v in data.items() if isinstance(v, dict)***REMOVED***
            return {***REMOVED***
        except Exception:
            return {***REMOVED***

    def _save(self) -> None:
        import yaml  # type: ignore
        body = yaml.safe_dump(self._records, allow_unicode=True, sort_keys=False)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        import os
        os.replace(tmp, self.path)

    def add(self, decision: ScenarioDecision) -> str:
        sid = _new_id()
        decision.created_at = _now_iso()
        self._records[sid***REMOVED*** = decision.to_dict()
        self._save()
        return sid

    def all(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        return list(self._records.values())

    def by_opportunity(self, opportunity_id: str) -> List[Dict[str, Any***REMOVED******REMOVED***:
        return [
            r for r in self._records.values()
            if r.get("opportunity_id") == opportunity_id
        ***REMOVED***

    def latest(self, opportunity_id: str) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        recs = self.by_opportunity(opportunity_id)
        return recs[-1***REMOVED*** if recs else None


# ─── Scenario Intelligence ────────────────────────────────────────────────

class ScenarioIntelligence:
    """Universal decision layer: discovery → evaluation → ranking → selection.

    Domain-neutral: operates on any Opportunity / any scenario manifest / any
    capability token. Reuses ScenarioRegistry (catalog), FactoryRegistry
    (capability→factory/forge), MemoryStore/SemanticLayer/LearningLoop (history
    + feedback). ForgeFacade remains the sole execution boundary (§17).
    """

    # PHASE 14 (v5.189.34, ADR-015 mirror): per-instance warnings list. Class-level
    # declaration is required for mypy --strict (PEP 526 forward-reference).
    # Instances get a fresh `[***REMOVED***` via __init__; lazy-import failures append HERE,
    # not the legacy module-level singleton (deprecated since v5.189.34).
    _import_warnings: List[str***REMOVED***

    def __init__(
        self,
        registry: Any = None,
        factory_registry: Any = None,
        memory_store: Any = None,
        history_store: Optional[DecisionHistoryStore***REMOVED*** = None,
    ):
        self._registry = registry
        self._factory_registry = factory_registry
        self._memory_store = memory_store
        self._history_store = history_store or DecisionHistoryStore()
        # PHASE 14 (v5.189.34, ADR-015 mirror): per-instance warnings list.
        # Lazy import failures are appended HERE instead of the module-level
        # singleton — prevents two SI instances from cross-polluting each
        # other's diagnostics when one of them has a missing dependency.
        self._import_warnings: List[str***REMOVED*** = [***REMOVED***  # fresh per instance

    # ─── registry access (lazy, fail-safe) ────────────────────────────────

    def _scenario_registry(self) -> Any:
        if self._registry is not None:
            return self._registry
        reg = _lazy_import("core_02.scenario_registry", "ScenarioRegistry")
        if reg is None:
            self._import_warnings.append("scenario_registry: unavailable")
            return None
        try:
            self._registry = reg()
        except Exception as exc:  # noqa: BLE001
            self._import_warnings.append(f"scenario_registry: {exc***REMOVED***")
            return None
        return self._registry

    # ─── 1. Discovery (§5) ────────────────────────────────────────────────

    def discover(
        self,
        opp: Any,
        *,
        top_n: int = 5,
        event_bus: Any = None,
    ) -> List[ScenarioCandidate***REMOVED***:
        """One Opportunity → many candidate scenarios (ScenarioRegistry as catalog).

        Uses ``propose_roles`` (fuzzy role match) + ``list_scenarios`` (catalog).
        Never a second registry. Each candidate carries a domain-neutral
        capability token (scenario.capabilities[0***REMOVED*** or role routing_hint[0***REMOVED***).
        """
        registry = self._scenario_registry()
        if registry is None:
            return [***REMOVED***
        query = f"{getattr(opp, 'title', '')***REMOVED*** {getattr(opp, 'description', '')***REMOVED***".strip()
        candidates: List[ScenarioCandidate***REMOVED*** = [***REMOVED***

        # Primary: fuzzy role match (scenario, role, score).
        try:
            proposals = registry.propose_roles(query, top_n=top_n)
        except Exception:  # noqa: BLE001
            proposals = [***REMOVED***
        for scenario, role, score in proposals:
            if scenario is None:
                continue
            capability = self._candidate_capability(scenario, role)
            candidates.append(ScenarioCandidate(
                scenario_id=scenario.scenario_id,
                display_name=getattr(scenario, "display_name", "") or scenario.scenario_id,
                role_id=getattr(role, "role_id", None),
                score=float(score),
                reasons=["scenario role fuzzy match"***REMOVED***,
                evidence={"match_score": float(score), "role_id": getattr(role, "role_id", None)***REMOVED***,
                capability=capability,
                scenario_caps=self._candidate_capabilities_all(scenario, role),
                available=True,
            ))

        # Fallback: catalog-only (no role match) — any enabled scenario.
        if not candidates:
            try:
                all_scenarios = registry.list_scenarios()
            except Exception:  # noqa: BLE001
                all_scenarios = [***REMOVED***
            for scenario in all_scenarios[:top_n***REMOVED***:
                capability = self._candidate_capability(scenario, None)
                candidates.append(ScenarioCandidate(
                    scenario_id=scenario.scenario_id,
                    display_name=getattr(scenario, "display_name", "") or scenario.scenario_id,
                    score=0.0,
                    reasons=["catalog fallback (no role match)"***REMOVED***,
                    evidence={***REMOVED***,
                    capability=capability,
                    available=True,
                ))

        _emit_event(
            event_bus, "scenario.candidates.generated", source="scenario_intelligence",
            opportunity_id=getattr(opp, "id", None),
            project_id=getattr(opp, "project_id", None),
            candidate_count=len(candidates),
            scenario_ids=[c.scenario_id for c in candidates***REMOVED***,
        )
        return candidates

    @staticmethod
    def _candidate_capability(scenario: Any, role: Any) -> Optional[str***REMOVED***:
        """Domain-neutral capability token: scenario.capabilities → role.routing_hint → None."""
        caps = getattr(scenario, "capabilities", None) or ()
        if isinstance(caps, (tuple, list)) and caps:
            return str(caps[0***REMOVED***)
        if role is not None:
            hint = getattr(role, "routing_hint", None) or ()
            if isinstance(hint, (tuple, list)) and hint:
                return str(hint[0***REMOVED***)
        return None

    @staticmethod
    def _candidate_capabilities_all(scenario: Any, role: Any) -> Tuple[str, ...***REMOVED***:
        """Domain-neutral: extract FULL capability tuple (sorted + deduped).

        Resolution priority: scenario.capabilities → role.routing_hint → () empty.
        Phase 13 G-11.6 set-membership semantics (REPLACES first-element
        ``_candidate_capability`` for hard-gate comparison; latter preserved
        for backward-compat in ``cap_avail`` calculation).
        """
        caps: List[str***REMOVED*** = [***REMOVED***
        scen_caps = getattr(scenario, "capabilities", None) or ()
        if isinstance(scen_caps, (tuple, list)):
            caps.extend(str(c) for c in scen_caps if c)
        if role is not None and not caps:
            hint = getattr(role, "routing_hint", None) or ()
            if isinstance(hint, (tuple, list)):
                caps.extend(str(c) for c in hint if c)
        return tuple(sorted(set(caps)))

    # ─── 2. Evaluation (§6) ───────────────────────────────────────────────

    def evaluate(
        self,
        opp: Any,
        candidates: List[ScenarioCandidate***REMOVED***,
        *,
        event_bus: Any = None,
    ) -> List[ScenarioCandidate***REMOVED***:
        """Score each candidate: relevance + capability + history + feasibility.

        Composite score ∈ [0,1***REMOVED*** = Σ weight_i · component_i (weights §EVAL_WEIGHTS).
        Each component is explainable (reasons + evidence).

        PHASE 12 G-11.6 (CANONICAL_ENGINE_ROUTING_V1.md): capability-match hard gate —
        opportunity's declared capability MUST match candidate scenario's declared
        capability(s); cross-domain candidates are INFEASIBLE (feas=0.0, available=False)
        BEFORE ranking. Without this gate (Phase 11 limitation), SI returned the
        highest-relevance scenario, even if its capability tag mismatched the opp
        — cross-domain routing risk (closed here via defense-in-depth).
        """
        factory_registry = self._factory_registry or self._lazy_factory_registry()
        memory = self._memory_store or self._lazy_memory_store()

        # ─── PHASE 12 G-11.6: extract opp.required_capability — single source of truth ───
        opp_capability: Optional[str***REMOVED*** = None
        _prov = getattr(opp, "provenance", None) or {***REMOVED***
        if isinstance(_prov, dict):
            _cap = _prov.get("capability")
            if isinstance(_cap, str) and _cap:
                opp_capability = _cap
        if opp_capability is None:
            _sc = getattr(opp, "scenario", None)
            if isinstance(_sc, dict):
                _cap = _sc.get("capability")
                if isinstance(_cap, str) and _cap:
                    opp_capability = _cap

        evaluated: List[ScenarioCandidate***REMOVED*** = [***REMOVED***
        for cand in candidates:
            reasons: List[str***REMOVED*** = [***REMOVED***
            evidence: Dict[str, Any***REMOVED*** = {***REMOVED***

            # relevance — raw fuzzy-match score (already in [0,1***REMOVED*** from registry)
            relevance = max(0.0, min(1.0, cand.score))
            reasons.append(f"relevance={relevance:.2f***REMOVED***")
            evidence["relevance"***REMOVED*** = relevance

            # capability availability — FactoryRegistry.capability_catalog
            capability = cand.capability
            cap_avail = 0.5  # neutral default (unknown token)
            if capability and factory_registry is not None:
                try:
                    if hasattr(factory_registry, "capability_catalog"):
                        catalog = factory_registry.capability_catalog()
                        cap_avail = 1.0 if capability in (catalog or {***REMOVED***) else 0.0
                    elif hasattr(factory_registry, "find_factories_by_capability"):
                        cap_avail = 1.0 if factory_registry.find_factories_by_capability(capability) else 0.0
                except Exception:  # noqa: BLE001
                    cap_avail = 0.5
            elif capability is None:
                cap_avail = 0.5  # no token → neutral
            reasons.append(f"capability={cap_avail:.2f***REMOVED***" + (f" ({capability***REMOVED***)" if capability else ""))
            evidence["capability"***REMOVED*** = capability
            evidence["capability_available"***REMOVED*** = cap_avail

            # history — previous executions (MemoryStore kind=candidate, tag=scenario_decision;
            # scenario_decision НЕ в KNOWLEDGE_KINDS — reuse существующего kind per §12).
            # limit=500: в загруженной БД opportunity-accumulate KO не должны вытеснять
            # scenario-записи за пределы среза (reviewer nit — иначе history молча нейтральна).
            hist = 0.5  # neutral (no history)
            if memory is not None:
                try:
                    kos = memory.query_by_type("candidate", limit=500)
                    matches = [
                        k for k in kos
                        if (k.get("title") or "").startswith(f"scenario:{cand.scenario_id***REMOVED***")
                    ***REMOVED***
                    if matches:
                        ok = sum(1 for k in matches if k.get("status") == "success")
                        hist = ok / len(matches)
                        evidence["history_count"***REMOVED*** = len(matches)
                        evidence["history_success_rate"***REMOVED*** = round(hist, 4)
                        reasons.append(f"history={hist:.2f***REMOVED*** ({ok***REMOVED***/{len(matches)***REMOVED***)")
                    else:
                        reasons.append("history=neutral (no prior executions)")
                except Exception:  # noqa: BLE001
                    reasons.append("history=neutral (memory unavailable)")
            else:
                reasons.append("history=neutral (no memory)")
            evidence["history"***REMOVED*** = hist

            # PHASE 13 G-11.6 (CANONICAL_ENGINE_ROUTING_V1.md §8): set-membership semantics.
            # The ``capability`` variable retains the first-element (backward-compat for
            # ``cap_avail``). Set-membership comparison uses the FULL tuple
            # ``cand.scenario_caps`` (sorted + deduped via ``_candidate_capabilities_all``).
            # Cross-domain candidates are STILL filtered BEFORE ranking (I-6 invariant
            # preserved). Defense-in-depth via canonical ``select_forge()`` resolution
            # afterwards (Phase 11 universality proof, never broken by SI bug).
            domain_match: bool = True
            if opp_capability is not None:
                scenario_caps_full: Tuple[str, ...***REMOVED*** = cand.scenario_caps or ((capability,) if capability else ())
                domain_match = bool(scenario_caps_full) and opp_capability in set(scenario_caps_full)

            # feasibility — enabled + roles present + capability resolvable + DOMAIN_MATCH
            feas = 1.0
            if not domain_match:
                feas = 0.0  # INFEASIBLE — domain mismatch (G-11.6 hard gate, closed here)
                reasons.append(
                    f"feasibility=0.00 (DOMAIN_MISMATCH: opp.capability={opp_capability!r***REMOVED*** "
                    f"!= scenario.capability={capability!r***REMOVED***; G-11.6 hard gate per "
                    f"CANONICAL_ENGINE_ROUTING_V1.md)"
                )
            elif capability is not None and cap_avail == 0.0:
                feas = 0.3  # capability declared but no factory/forge offers it
                reasons.append("feasibility=0.30 (capability not offered by any factory)")
            else:
                reasons.append(f"feasibility={feas:.2f***REMOVED***")
            evidence["feasibility"***REMOVED*** = feas
            evidence["domain_match"***REMOVED*** = domain_match
            evidence["opp_capability"***REMOVED*** = opp_capability

            w = EVAL_WEIGHTS
            composite = round(
                relevance * w["relevance"***REMOVED***
                + cap_avail * w["capability"***REMOVED***
                + hist * w["history"***REMOVED***
                + feas * w["feasibility"***REMOVED***,
                4,
            )
            evaluated.append(ScenarioCandidate(
                scenario_id=cand.scenario_id,
                display_name=cand.display_name,
                role_id=cand.role_id,
                score=composite,
                reasons=reasons,
                evidence=cand.evidence | evidence,
                capability=capability,
                # feas=0.3 (capability not offered) → unavailable (0.3 > 0.3 = False),
                # so available_only=True in select() filters infeasible candidates.
                available=feas > 0.3,
            ))

        _emit_event(
            event_bus, "scenario.evaluated", source="scenario_intelligence",
            opportunity_id=getattr(opp, "id", None),
            project_id=getattr(opp, "project_id", None),
            evaluated=[{"scenario_id": c.scenario_id, "score": c.score***REMOVED*** for c in evaluated***REMOVED***,
        )
        return evaluated

    def _lazy_factory_registry(self) -> Any:
        reg = _lazy_import("core_02.factory_registry", "FactoryRegistry")
        if reg is None:
            self._import_warnings.append("factory_registry: unavailable")
            return None
        try:
            return reg()
        except Exception as exc:  # noqa: BLE001
            self._import_warnings.append(f"factory_registry: {exc***REMOVED***")
            return None

    def _lazy_memory_store(self) -> Any:
        ms = _lazy_import("core_02.memory_store", "MemoryStore")
        if ms is None:
            self._import_warnings.append("memory_store: unavailable")
            return None
        # Hermetic guard: не создавать реальную БД (data_13/context.db) в тестах —
        # если файла нет, история нейтральна (history=neutral), без side-effect.
        if not DEFAULT_MEMORY_DB.exists():
            return None
        try:
            return ms(DEFAULT_MEMORY_DB)
        except Exception as exc:  # noqa: BLE001
            self._import_warnings.append(f"memory_store: {exc***REMOVED***")
            return None

    # ─── 3. Ranking (§7) ─────────────────────────────────────────────────

    @staticmethod
    def rank(candidates: List[ScenarioCandidate***REMOVED***) -> List[ScenarioCandidate***REMOVED***:
        """Sort by composite score desc; tie-break stable by scenario_id."""
        return sorted(
            candidates,
            key=lambda c: (-c.score, c.scenario_id),
        )

    # ─── 4. Selection (§7) ───────────────────────────────────────────────

    def select(
        self,
        opp: Any,
        *,
        top_n: int = 5,
        event_bus: Any = None,
        persist: bool = True,
        available_only: bool = True,
    ) -> ScenarioDecision:
        """Discover → evaluate → rank → pick best → ScenarioDecision (explainable).

        Provenance (§7): selected scenario_id, score, reasons, evidence,
        capability, factory/forge (via resolve_capability). Never black-box.
        """
        candidates = self.discover(opp, top_n=top_n, event_bus=event_bus)
        if not candidates:
            return ScenarioDecision(
                opportunity_id=getattr(opp, "id", ""),
                project_id=getattr(opp, "project_id", ""),
                selected_scenario_id=None,
                score=None,
                reasons=["no candidate scenarios available"***REMOVED***,
                evidence={"empty": True***REMOVED***,
                status="unavailable",
            )
        evaluated = self.evaluate(opp, candidates, event_bus=event_bus)
        ranked = self.rank(evaluated)
        if available_only:
            ranked = [c for c in ranked if c.available***REMOVED***
        if not ranked:
            return ScenarioDecision(
                opportunity_id=getattr(opp, "id", ""),
                project_id=getattr(opp, "project_id", ""),
                selected_scenario_id=None,
                score=None,
                reasons=["all candidates infeasible"***REMOVED***,
                evidence={"available": False***REMOVED***,
                status="unavailable",
            )

        best = ranked[0***REMOVED***
        # Re-selection semantics (§10): if the same opportunity previously
        # selected a different scenario, this is a "superseded" transition.
        prev = self._history_store.latest(getattr(opp, "id", ""))
        status = "selected"
        if prev and prev.get("selected_scenario_id") and \
                prev["selected_scenario_id"***REMOVED*** != best.scenario_id:
            status = "superseded"
        elif prev and prev.get("status") in ("deferred", "superseded"):
            status = "reselected"

        capability = best.capability
        factory_id: Optional[str***REMOVED*** = None
        forge_id: Optional[str***REMOVED*** = None
        if capability:
            capability_req = CapabilityRequirement(
                capability=capability,
                scenario_id=best.scenario_id,
                role_id=best.role_id,
            )
            factory_id, forge_id = self.resolve_capability(capability_req)

        decision = ScenarioDecision(
            opportunity_id=getattr(opp, "id", ""),
            project_id=getattr(opp, "project_id", ""),
            selected_scenario_id=best.scenario_id,
            score=best.score,
            reasons=best.reasons,
            evidence=best.evidence | {
                "display_name": best.display_name,
                "role_id": best.role_id,
                "all_candidates": [
                    {"scenario_id": c.scenario_id, "score": c.score***REMOVED*** for c in ranked
                ***REMOVED***,
            ***REMOVED***,
            capability=capability,
            factory_id=factory_id,
            forge_id=forge_id,
            status=status,
        )
        if persist:
            self._history_store.add(decision)

        event_type = "scenario.reselected" if status == "reselected" else "scenario.selected"
        _emit_event(
            event_bus, event_type, source="scenario_intelligence",
            opportunity_id=decision.opportunity_id,
            project_id=decision.project_id,
            scenario_id=decision.selected_scenario_id,
            role_id=best.role_id,
            score=decision.score,
            capability=decision.capability,
            factory_id=decision.factory_id,
            forge_id=decision.forge_id,
            status=decision.status,
        )
        return decision

    # ─── 5. Capability resolution (§8) ───────────────────────────────────

    def resolve_capability(
        self,
        requirement: CapabilityRequirement,
    ) -> Tuple[Optional[str***REMOVED***, Optional[str***REMOVED******REMOVED***:
        """Capability → FactoryRegistry.select_forge → (factory_id, forge_id).

        Domain-neutral: capability is an opaque token; FactoryRegistry decides
        which factory/forge offers it. ForgeFacade stays the execution boundary.
        Returns (None, None) if no factory/forge offers the capability.
        """
        factory_registry = self._factory_registry or self._lazy_factory_registry()
        if factory_registry is None:
            return None, None
        try:
            if hasattr(factory_registry, "select_forge"):
                pair = factory_registry.select_forge(requirement.capability)
                if pair is None:
                    return None, None
                fp, fg = pair
                return (
                    getattr(fp, "factory_id", None),
                    getattr(fg, "forge_id", None),
                )
        except Exception:  # noqa: BLE001
            return None, None
        return None, None

    # ─── 6. Feedback v0 (§9) ─────────────────────────────────────────────

    def feedback_v0(
        self,
        decision: ScenarioDecision,
        outcome: str,
        *,
        memory_store: Any = None,
        learning_loop: Any = None,
        event_bus: Any = None,
    ) -> Dict[str, Any***REMOVED***:
        """Transparent feedback v0: decision outcome → MemoryStore + LearningLoop.

        outcome: "success" | "failure" | "neutral". Stores a knowledge object
        kind=scenario_decision (title=f"scenario:{scenario_id***REMOVED***") + learning
        event. NO ML/RL — only transparent traceability for future ranking.
        """
        memory = memory_store or self._memory_store or self._lazy_memory_store()
        result: Dict[str, Any***REMOVED*** = {
            "recorded": False,
            "knowledge_id": None,
            "learning_event_id": None,
            "outcome": outcome,
            "error": None,
        ***REMOVED***
        if memory is None:
            result["error"***REMOVED*** = "memory_store unavailable"
            return result

        scenario_id = decision.selected_scenario_id or "none"
        try:
            # kind="candidate" (существующий KNOWLEDGE_KINDS) + tag scenario_decision —
            # НЕ создаём новый kind (MemoryStoreError иначе); §12 reuse существующей инфры.
            kid = memory.store_knowledge(
                kind="candidate",
                content=json.dumps(decision.to_dict(), ensure_ascii=False, default=str),
                title=f"scenario:{scenario_id***REMOVED***",
                summary=(
                    f"opportunity={decision.opportunity_id***REMOVED*** project={decision.project_id***REMOVED*** "
                    f"outcome={outcome***REMOVED*** score={decision.score***REMOVED***"
                ),
                tags=["scenario_decision", scenario_id, decision.opportunity_id***REMOVED***,
                # lifecycle_stage из закрытого LIFECYCLE_STAGES (validated/raw) —
                # "applied" там нет (MemoryStoreError); status всегда "draft" (default).
                lifecycle_stage="validated" if outcome == "success" else "raw",
                status="draft",
                confidence_score=decision.score if decision.score is not None else 0.5,
            )
            result["knowledge_id"***REMOVED*** = kid
        except Exception as exc:  # noqa: BLE001
            result["error"***REMOVED*** = f"store_knowledge: {exc***REMOVED***"
            return result

        try:
            eid = memory.record_learning_event(
                trigger_id=f"scenario:{scenario_id***REMOVED***",
                context_snapshot={
                    "opportunity_id": decision.opportunity_id,
                    "scenario_id": scenario_id,
                    "capability": decision.capability,
                    "factory_id": decision.factory_id,
                    "forge_id": decision.forge_id,
                    "outcome": outcome,
                ***REMOVED***,
                outcome=outcome,
                lesson_id=kid,
            )
            result["learning_event_id"***REMOVED*** = eid
        except Exception as exc:  # noqa: BLE001
            result["error"***REMOVED*** = f"record_learning_event: {exc***REMOVED***"

        if learning_loop is not None and outcome in ("success", "failure"):
            try:
                learning_loop.record_feedback(kid, outcome)
            except Exception:  # noqa: BLE001
                pass

        result["recorded"***REMOVED*** = True
        _emit_event(
            event_bus, "scenario.feedback", source="scenario_intelligence",
            opportunity_id=decision.opportunity_id,
            project_id=decision.project_id,
            scenario_id=scenario_id,
            outcome=outcome,
            knowledge_id=kid,
        )
        return result


# ─── CLI ──────────────────────────────────────────────────────────────────

def _load_opp(data_path: Path, opportunity_id: str) -> Any:
    from scripts_01.opportunity_engine import OpportunityStore
    store = OpportunityStore(data_path)
    return store.get(opportunity_id)


def _emit_json(payload: Dict[str, Any***REMOVED***) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _emit_text(line: str, *, json_mode: bool) -> None:
    out = sys.stderr if json_mode else sys.stdout
    out.write(line + "\n")
    out.flush()


def _cli_discover(args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r***REMOVED*** not found", json_mode=bool(args.json))
        return 1
    si = ScenarioIntelligence()
    candidates = si.discover(opp, top_n=args.top)
    payload = {
        "scenario_intelligence": "discover",
        "opportunity_id": args.opportunity_id,
        "candidates": [asdict(c) for c in candidates***REMOVED***,
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"discovered: {len(candidates)***REMOVED*** candidate(s) for {args.opportunity_id***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_select(args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r***REMOVED*** not found", json_mode=bool(args.json))
        return 1
    si = ScenarioIntelligence()
    decision = si.select(opp, top_n=args.top, persist=not bool(getattr(args, "no_persist", False)))
    payload = {
        "scenario_intelligence": "select",
        "decision": decision.to_dict(),
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"selected: {decision.selected_scenario_id***REMOVED*** score={decision.score***REMOVED*** "
            f"capability={decision.capability***REMOVED*** factory={decision.factory_id***REMOVED*** forge={decision.forge_id***REMOVED*** "
            f"status={decision.status***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_evaluate(args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r***REMOVED*** not found", json_mode=bool(args.json))
        return 1
    si = ScenarioIntelligence()
    candidates = si.discover(opp, top_n=args.top)
    evaluated = si.evaluate(opp, candidates)
    ranked = si.rank(evaluated)
    payload = {
        "scenario_intelligence": "evaluate",
        "opportunity_id": args.opportunity_id,
        "ranked": [asdict(c) for c in ranked***REMOVED***,
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(f"evaluated: {len(ranked)***REMOVED*** ranked candidate(s)", json_mode=False)
    return 0


def _cli_resolve(args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r***REMOVED*** not found", json_mode=bool(args.json))
        return 1
    si = ScenarioIntelligence()
    decision = si.select(opp, top_n=args.top, persist=False)
    payload = {
        "scenario_intelligence": "resolve",
        "opportunity_id": args.opportunity_id,
        "decision": decision.to_dict(),
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"resolve: scenario={decision.selected_scenario_id***REMOVED*** capability={decision.capability***REMOVED*** "
            f"factory={decision.factory_id***REMOVED*** forge={decision.forge_id***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_feedback(args: argparse.Namespace) -> int:
    opp = _load_opp(Path(args.data_path), args.opportunity_id)
    if opp is None:
        _emit_text(f"error: opportunity_id {args.opportunity_id!r***REMOVED*** not found", json_mode=bool(args.json))
        return 1
    si = ScenarioIntelligence()
    decision = si.select(opp, top_n=args.top, persist=False)
    result = si.feedback_v0(decision, args.outcome)
    payload = {
        "scenario_intelligence": "feedback",
        "opportunity_id": args.opportunity_id,
        "feedback": result,
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"feedback: recorded={result['recorded'***REMOVED******REMOVED*** outcome={result['outcome'***REMOVED******REMOVED*** "
            f"knowledge_id={result['knowledge_id'***REMOVED******REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_history(args: argparse.Namespace) -> int:
    si = ScenarioIntelligence(
        history_store=DecisionHistoryStore(Path(args.history_path)),
    )
    records = si._history_store.all()[-args.limit:***REMOVED*** if args.limit else si._history_store.all()
    payload = {
        "scenario_intelligence": "history",
        "count": len(records),
        "records": records,
        "import_warnings": list(si._import_warnings),
        "timestamp": _now_iso(),
    ***REMOVED***
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(f"history: {len(records)***REMOVED*** decision(s)", json_mode=False)
    return 0


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scenario_intelligence",
        description="Universal Scenario Intelligence — Phase 8 (domain-neutral).",
    )
    parser.add_argument(
        "--data-path", default=str(DEFAULT_DATA_PATH),
        help=f"Opportunity YAML persistence path (default {DEFAULT_DATA_PATH***REMOVED***)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, fn, help_text in (
        ("discover", _cli_discover, "candidate scenario discovery"),
        ("select", _cli_select, "evaluate + rank + select best scenario"),
        ("evaluate", _cli_evaluate, "evaluate + rank candidates"),
        ("resolve", _cli_resolve, "capability → factory/forge resolution"),
        ("feedback", _cli_feedback, "record decision outcome (feedback v0)"),
        ("history", _cli_history, "list decision history"),
    ):
        p = sub.add_parser(name, help=help_text)
        if name == "history":
            p.add_argument("--limit", type=int, default=None)
            p.add_argument("--history-path", default=str(DEFAULT_HISTORY_PATH),
                           help=f"decision history YAML path (default {DEFAULT_HISTORY_PATH***REMOVED***)")
            p.add_argument("--json", action="store_true")
        else:
            p.add_argument("opportunity_id")
            p.add_argument("--top", type=int, default=5)
            p.add_argument("--json", action="store_true")
        if name == "select":
            p.add_argument("--no-persist", action="store_true")
        if name == "feedback":
            p.add_argument("--outcome", choices=("success", "failure", "neutral"), default="neutral")
        p.set_defaults(func=fn)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — fail-safe per spec
        _emit_text(f"error: scenario_intelligence unexpected failure: {exc***REMOVED***", json_mode=False)
        return 2


__all__ = [
    "ScenarioCandidate",
    "CapabilityRequirement",
    "ScenarioDecision",
    "ScenarioIntelligence",
    "DecisionHistoryStore",
    "EVAL_WEIGHTS",
    "DECISION_STATUSES",
    # DEPRECATED v5.189.34 (ADR-015 mirror): kept for backward-compat re-exports.
    # No longer appended to from ScenarioIntelligence methods — use
    # ``inst._import_warnings`` instead.
    "_LAZY_IMPORT_ERRORS",
***REMOVED***


if __name__ == "__main__":
    sys.exit(main())
