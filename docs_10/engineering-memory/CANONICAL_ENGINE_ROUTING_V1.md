# CANONICAL_ENGINE_ROUTING_V1.md — Phase 12 G-11.6 Workshop Consensus

**Status:** ✅ IMPLEMENTED (v5.189.30, 2026-08-18) — `code` capability routing closed.
**Workshop:** Phase 12 G-11.6 (ADR-013 follow-up) — `code` capability конкурировал между BlueprintCorpus (ModelRouter assignment) и FactoryRegistry (ForgeFacade execution).
**Outcome:** ONE canonical resolution path across all three engine layers + capability-match HARD GATE at SI level (defence-in-depth).

---

## 1. Executive Summary

The `code` capability was simultaneously routed through three engine layers, each with its own purpose, but without an explicit precedence contract. This caused a Phase 11 known SI-ranking limitation: scenario_content (article_generation, relevance 0.9) could win the SI ranking over scenario_code (`code`, relevance 0.6) for an Opportunity with `code` — wrong-scenario routing risk.

Phase 12 G-11.6 workshop (between Phase 8 ScenarioIntelligence author, Phase 11 TestFactory author, and Blueprint v3 author) concluded:

> **The `code` capability is DOMAIN-NEUTRAL across all three layers, with SINGLE deterministic resolution: opportunity's declared capability MUST match candidate scenario's declared capability. Cross-domain scenarios are INFEASIBLE before ranking.**

Three engine layers are now orthogonal by design:

| Layer | Module | Purpose | `code` resolution |
|-------|--------|---------|-------------------|
| A. Model Routing | `core_02/router.py::SmartRouter` | pick model for role | developer/frontend/devops/tester/fixer roles (CAPABILITIES_OVERRIDE) → code-capable models |
| B. Scenario Decision | `scripts_01/scenario_intelligence.py::evaluate` | pick scenario+role for opp | SI-hard-gate: opp.capability ∈ scenario.capabilities (NEW) |
| C. Factory Execution | `core_02/factory_registry.py::select_forge` | pick (factory, forge) for capability | `code` → `(test, verifier)` per Phase 11 TestFactory manifest (UNCHANGED) |

The flow is:

```
Opp (capability=code)
   ↓
SI.discover() ─ → candidates (scenario_content[article_gen***REMOVED***, scenario_code[code***REMOVED***)
   ↓
SI.evaluate() ─ ─ opp_capability='code'
   ↓
[NEW***REMOVED*** HARD GATE: scenario.capabilities ⊇ opp_capability?
   ↓
   YES (scenario_code) → feasibility=1.0 → available=True → rank wins
   NO  (scenario_content) → DOMAIN_MISMATCH → feasibility=0.0 → available=False ╳
   ↓
SI.select() picks scenario_code
   ↓
FactoryRegistry.select_forge('code') → (test, verifier) — UNCHANGED
   ↓
ModelRouter.route(role='developer') → code-capable model (UNCHANGED)
   ↓
ForgeFacade.run_chain(test, verifier) — UNCHANGED
```

---

## 2. Workshop Decisions (3 design-of-record entries)

### Decision 1 (Phase 12 G-11.6 D-1) — SI capability-match HARD GATE (NEW: scenario_intelligence.py)

**Before (Phase 11):** SI returned the highest-relevance scenario regardless of capability-match. An opp with `code` could route through scenario_content (article_generation capability) if relevance score was higher — wrong-scenario routing risk. Documented in test_content_factory.py:317 as `xfail(strict=False)`.

**After:** `_make_opp(scenario_cap=...)` extracts `opp_capability` from `opp.provenance.capability` or `opp.scenario.capability`. In `evaluate()`, the feasibility block now reads:

```python
domain_match = (
    opp_capability is not None and capability is not None
    and opp_capability == capability
)
if not domain_match:
    feas = 0.0  # INFEASIBLE — domain mismatch
```

Cross-domain candidates are filtered BEFORE ranking. `cap_avail` (capability in FactoryRegistry catalog) remains as a secondary feasibility signal.

**Rationale:**
- (1) Semantic correctness — opportunity's declared capability IS the primary routing intent; relevance is orthogonal.
- (2) Defense-in-depth — single source of truth (opp.capability) gates route at the earliest possible decision point.
- (3) Closed-vocabulary consistency — same principle as anti-vocabulary-drift in ANTI-6b: only matched tokens may proceed.
- (4) ADR-013 alignment — universal boundary invariant: ONE canonical path per opp.

### Decision 2 (Phase 12 G-11.6 D-2) — FactoryRegistry `code → (test, verifier)` policy (UNCHANGED, documented in factory_registry.py)

**Already correct (Phase 11 factory manifest):** `runtime_05/factories/test/factory.yaml` and `runtime_05/factories/test/verifier.yaml` declare `code` capability. `select_forge('code')` returns `(test, verifier)` deterministically (status-priority tie-break, deterministic factory_id lexicographic tie-break).

**Documentation addition:** Added explicit ASCII comment in `select_forge()` docstring explaining the `code` policy for future auditors.

**Rationale:**
- (1) Defense-in-depth — even if SI misroutes (regression, future bug, manual override), `select_forge('code')` still returns canonical (test, verifier).
- (2) Phase 11 universality proof — `factory_id == 'test'` is the ONLY canonical factory for `code` (test_15 META-TEST asserts `factories == {"content", "research", "test"***REMOVED***` strict set equality).

### Decision 3 (Phase 12 G-11.6 D-3) — BlueprintCorpus CAPABILITIES_OVERRIDE semantic clarification (UNCHANGED)

**Already correct:** `core_02/blueprint_v3.py::CAPABILITIES_OVERRIDE` declares that `code` is a capability of developer/frontend/devops/tester/fixer roles. This is used by `core_02/router.py::SmartRouter.route(role_id)` to pick the CODE-CAPABLE model for the role (Layer A — model assignment).

**No conflict with Layer C:** When the role is `developer` AND the opportunity's capability is `code`, ModelRouter assigns a code-capable model (e.g., deepseek-coder); the execution layer still routes via `(test, verifier)`. The two layers answer different questions:
- ModelRouter: "Which model best handles the role's semantic + the opp's intent?"
- FactoryRegistry: "Which (factory, forge) pair executes the opp's capability?"

**Rationale:**
- (1) Roles are NOT factories — they are sub-capabilities of the forge-execution pipeline (`ROLE_FORGE_MATRIX_V1.md`).
- (2) Capability-match (Layer B) is the authoritative filter for which scenario participates in execution; role-tagged capabilities in CAPABILITIES_OVERRIDE remain authoritative for model assignment (Layer A only).

---

## 3. Cross-Engine Invariants (now enforced)

After Phase 12 G-11.6 closure, the following invariants hold:

| Invariant | Module | Source |
|-----------|--------|--------|
| I-1: Opp.capability is single source of truth for routing intent | arrived at SI via `opp.scenario.capability` or `opp.provenance.capability` | `scenario_intelligence.py:evaluate` |
| I-2: SI ranking requires capability-match (feasibility > 0) | HARD GATE | `scenario_intelligence.py:evaluate` (NEW) |
| I-3: FactoryRegistry resolves capability → (factory, forge) | status-priority tie-break | `factory_registry.py:select_forge` |
| I-4: `code` capability → `(test, verifier)` is the canonical pair | defense-in-depth + universality proof | TestFactory manifest (Phase 11) |
| I-5: ModelRouter assigns code-capable models to developer/frontend/devops/tester roles | CAPABILITIES_OVERRIDE vocabulary | `blueprint_v3.py:120–145` |
| I-6: cross-domain scenarios are INFEASIBLE BEFORE ranking | defense-in-depth | `scenario_intelligence.py:evaluate` (NEW, this turn) |

**Composite routing invariant (NEW):**
> For any Opportunity with `provenance.capability = X`:
>   (a) SI MUST rank ONLY scenarios that declare `X ∈ capabilities` (HARD GATE).
>   (b) FactoryRegistry MUST resolve `X` to ONE (factory, forge) pair (status-priority).
>   (c) ModelRouter MUST assign a model whose `capabilities ⊇ X` to the role (CAPABILITIES_OVERRIDE).
>   (d) All three resolutions are orthogonal and deterministic.

---

## 4. Closure Evidence (3 artifacts)

### Artifact 1 — `scripts_01/scenario_intelligence.py::evaluate` (modified)

```python
# PHASE 12 G-11.6 (CANONICAL_ENGINE_ROUTING_V1.md): capability-match hard gate.
domain_match = (
    opp_capability is not None and capability is not None
    and opp_capability == capability
)
if not domain_match:
    feas = 0.0  # INFEASIBLE — domain mismatch (G-11.6 hard gate, closed here)
```

### Artifact 2 — `tests_09/test_scenario_intelligence.py::test_13_routing_hard_gate_for_code_opp` (NEW)

Asserts that an Opportunity with `capability=code` ALWAYS routes through `scenario_code` (developer role, code capability), regardless of `scenario_content` (writer role, article_generation capability, higher relevance) being available.

### Artifact 3 — §20 row 26 in `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` (NEW)

Acquaintance record: Phase 12 G-11.6 closed via canonical routing + hard gate. References this doc as the authoritative routing contract.

---

## 5. Test Promotion (test_13b closure)

- `tests_09/test_test_factory.py::test_13b_si_routes_code_opp_to_test_factory` — was `xfail(strict=False)` (Phase 10 lenient marker). After Phase 12 G-11.6 fix: `xpassed` (passing under xfail marker; still slightly lenient because test_13b uses competitive scenario registration, no explicit hard-gate assertion). Tightening to `strict=True` is a Phase 12+ follow-up (per ADR-015).
- `tests_09/test_content_factory.py::test_13b_competitive_routing_for_code_opp` — same as above.
- `tests_09/test_scenario_intelligence.py::test_13_routing_hard_gate_for_code_opp` (NEW) — strict assertion of the hard-gate invariant.

---

## 6. ADR-013 Closure Note

ADR-013 (BaseFactory refactor) deferred G-11.6 (capability routing resolution conflict) to Phase 12. THIS DOCUMENT closes G-11.6 with three orthogonal layers, mandatory capability-match hard gate, and defense-in-depth via status-priority tie-break. ADR-013 + ADR-014 (NOT PRODUCTION for test_factory) fully closed at v5.189.30.

---



## 8. Phase 13 G-11.6b Workshop Reconvene — Set-Membership Refactor + Multi-Cap Coverage (v5.189.31)

**Status:** ✅ IMPLEMENTED (v5.189.31, 2026-08-18) — set-membership refactor landed.
**Reconvene rationale:** Phase 12 G-11.6 used `scenario.capabilities[0***REMOVED***` (first-element) for hard-gate comparison; worked for single-cap scenarios but would yield false negatives for hypothetical multi-cap scenarios (`scenario_fullstack.capabilities=["code","refactor"***REMOVED***` with `opp(capability="refactor")`).
**Outcome:** 3 design decisions ratified.

### Phase 13 D-1 — `CapabilityResolutionPolicy` frozen dataclass (NEW: core_02/factory_registry.py)

Previous: D-2 lived only in `select_forge()` docstring audit-trail.
**Now:** `CapabilityResolutionPolicy` is a Python dataclass with `capability / factory_id / forge_id / status_min / rationale / decided_by / decision_date`. Module-level `CODE_RESOLUTION_POLICY: dict[str, CapabilityResolutionPolicy***REMOVED***` provides programmatic lookup. New API: `FactoryRegistry.resolve_by_policy(capability)` returns the policy or `None`. Backward-compat: `select_forge()` API unchanged.

### Phase 13 D-2 — SI hard-gate set-membership refactor (MOD: scenario_intelligence.py)

Previous: `domain_match = (opp_capability == capability)` where `capability = cand.capability = scenario.capabilities[0***REMOVED***`.
**Now:** `domain_match = bool(scenario_caps_full) and opp_capability in set(scenario_caps_full)` comparing against full `cand.scenario_caps` tuple (sorted + deduped via new `_candidate_capabilities_all()` helper). Backward-compat: `_candidate_capability()` helper preserved (returns first element) for `cap_avail` calculation.

### Phase 13 D-3 — Multi-cap scenario regression coverage (NEW: 2 tests)

- `test_13c_multi_cap_set_membership_positive` — scenario_fullstack[code, refactor***REMOVED*** with opp(refactor) MUST be feasible.
- `test_13d_multi_cap_cross_domain_rejected` — scenario_fullstack[code, refactor***REMOVED*** with opp(image_generation) MUST be rejected (DOMAIN_MISMATCH).

### Participants
- Phase 8 ScenarioIntelligence author — re-signed D-2.
- Phase 11 TestFactory author — re-signed D-1 (CapabilityResolutionPolicy data shape aligned with TestFactory manifest universality proof).
- Blueprint v3 author — no changes (CAPABILITIES_OVERRIDE unchanged for code).

### Updated composite routing invariant

> I-4 (revised): For any Opportunity with `provenance.capability = X`:
>   (a) `scenario_caps := _candidate_capabilities_all(scenario, role)`.
>   (b) domain_match = `X ∈ scenario_caps` (set-membership).
>   (c) cross-domain scenarios where `X ∉ scenario_caps` are INFEASIBLE BEFORE ranking.

## 7. References

- `docs_10/engineering-memory/ROLE_FORGE_MATRIX_V1.md` — roles vs factories classification
- `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` — Scenario engine design §6.2
- `docs_10/engineering-memory/ARCHITECTURE_DECISION_REGISTRY_V1.md` — ADR ledger (CAN-16, ANTI-6, etc.)
- `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row 25 (BaseFactory template), 26 (G-11.6)
- `core_02/LESSONS.md` ANTI-6, ANTI-6b (vocabulary drift defense), CON-16 (ADDITIVE invariant)
- `runtime_05/factories/test/` (Phase 11 manifests), `content/`, `research/`, `architecture/`
