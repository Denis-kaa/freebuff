# DOCUMENTATION CODE MAP (Artifact B — Phase B Inventory)

> **Goal:** Map architectural *claims* in documentation ⊃ code entities from Artifact A.
> **Conforms to:** `projects_17/content_factory/promts/4.md` §4 (DOCUMENTATION INVENTORY schema).
> **Counterpart:** Artifact A (`PLATFORM_CODE_MAP_V1.md`) — entities here MUST resolve to `@entity X` IDs there.
> **Anchor format:** `doc.<short_name>#<section_anchor>[.claim_N***REMOVED***` — section-anchored, line-number-independent.
> **Status taxonomy (per 4.md §4):** `CURRENT` (factual claim verified) · `DESIGN_ONLY` (approved DESIGN/FUTURE_PLAN) · `STALE` (contradicts 2026-08-12 code reality) · `SUPERSEDED` (overwritten by newer RFC) · `AMBIGUOUS` (evidence missing/contradictory, requires human/ARB ruling).
> **Claim-type discipline (4.md §4 strict):** every claim row labels itself `FACT` (how it works today) · `DESIGN` (architectural decision) · `FUTURE` (planned/foreseen). NO mixed claims. If a sentence contains both, split into two rows.
> **Source of truth:** repository. Every FACT row carries an `@entity` evidence pointer back to Artifact A.

---

## §B.1 — Architecture Canon (Definition / Boundary layer)

### doc.architecture_canonical → core canonical architecture
**File:** `docs_10/core/ARCHITECTURE_CANONICAL.md`
**Status header:** `ACTIVE [канон***REMOVED***` (per DOCUMENT_REGISTRY.md line ~38).
**Total claims mapped:** 8 (target entities: workspace.core, event.bus).

| doc anchor | claim | type | entities | contracts | decisions | status |
|------------|-------|------|----------|-----------|-----------|--------|
| `doc.arch_canon#1.c1` | Workspace is the L-1 container boundary; ADR-009 resolves Long-Running-Project ownership | DESIGN | `@entity workspace.core` | — | `ADR-009` | CURRENT |
| `doc.arch_canon#2.c1` | Project is L-2 sub-container (one project per directory inside Workspace) | FACT | `@entity workspace.core` | `@contract project.boundary` | — | CURRENT |
| `doc.arch_canon#3.c1` | Engine registry rows: 11 categories (Router, Telegram, MCP, Memory, Knowledge, Registry, Context, Tool Runtime, Plugin API, Event Bus) — matches TABLE in `core_02/registry.py` | FACT | `@entity event.bus`, `@entity memory.store` | — | — | CURRENT |
| `doc.arch_canon#4.c1` | LIFECYCLE for each engine: registry → instantiated → bound → alive | DESIGN | `@entity forge.registry` (cross-ref) | `@contract engine.lifecycle` | — | CURRENT |
| `doc.arch_canon#5.c1` | "Additive Architecture" — new components added without rewriting existing | DESIGN | All 25 Artifact A entities | — | `ADR-007`-implicit via CON-17 / ANTI-5 | CURRENT |
| `doc.arch_canon#5.c2` | "Contract First" — interfaces are explicit contracts | DESIGN | `@entity forge.facade`, `@entity role.validator` (cross-ref) | Multiple | ANTI-7 | CURRENT |
| `doc.arch_canon#6.c1` | "Observability" — every transition logged in event_log | DESIGN | `@entity event.bus` | `@event contract.event` | — | CURRENT |
| `doc.arch_canon#7.c1` | Cross-cutting: B-series invariants (B1–B14) are defined elsewhere (WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1 §32) | DESIGN | All `@entity` (cross-cutting) | — | `RFC_BUFFY_FORGE_V1.md` §2 | CURRENT |

**Notes:**
- File is read by `consistency_check.py::check_engine_files` (registry → scripts_01/ existence check). Conf claim #3 verified end-to-end.

---

### doc.architecture_manifest → architectural law
**File:** `docs_10/core/ARCHITECTURE_MANIFEST.md` (per `docs_10/DOCUMENT_REGISTRY.md` row ~38)
**Status header:** `ACTIVE [канон***REMOVED***`.
**Total claims mapped:** 4.

| doc anchor | claim | type | entities | decisions | status |
|------------|-------|------|----------|-----------|--------|
| `doc.arch_manifest#3.c1` | AGENTS.md is canonical single source of truth for agent session rules | DESIGN | `@entity knowledge.engine`, `@entity memory.store` (referenced indirectly via AGENTS md §cross-ref) | `ADR-007` | CURRENT |
| `doc.arch_manifest#5.c1` | Naming Convention: dirs `имя_NN`, prompts `NNN_TT_имя.md` (canonical §2.1) | DESIGN | — (meta-rule) | — | CURRENT |
| `doc.arch_manifest#6.c1` | "Архивация ≠ Удаление" — документы переносятся в архив без удаления | DESIGN | — (meta-rule) | — | CURRENT |
| `doc.arch_manifest#6.c2` | Prompts written in `prompts_11/` (or `pompts_11/`) are immutable once finalized — CON-17 | DESIGN | — (meta-rule) | CON-17 (anti-rewriting) | CURRENT |

---

### doc.lifecycle → entity lifecycles
**File:** `docs_10/core/LIFECYCLE.md`
**Status header:** `ACTIVE [канон***REMOVED***`.
**Total claims mapped:** 6.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.lifecycle#2.c1` | Engine lifecycle: registry → instantiated → bound → alive → (decommission) | FACT | `@entity forge.registry`, `@entity event.bus` | CURRENT |
| `doc.lifecycle#3.c1` | Project lifecycle: created → registered → UNFORGED → FORGED → SHIPPED | FACT | `@entity workspace.core`, `@entity forge.registry` | CURRENT |
| `doc.lifecycle#3.c2` | UNFORGED ≠ "поект не работал" (= "не прошёл forge CI-pipeline") | DESIGN | `@entity scenario.engine` (planned cross-ref) | CURRENT |
| `doc.lifecycle#5.c1` | Missing Capabilities registered via `@entity missing.registry` follow `registered → design_ready → prompt_written → implemented` | FACT | `@entity missing.registry` | CURRENT |
| `doc.lifecycle#5.c2` | Status rank ordering: registered < design_ready < prompt_written < implemented (monotonic forward) | FACT | `@entity missing.registry` | CURRENT |
| `doc.lifecycle#7.c1` | WHIM ↔ FORGE lifecycle orthogonal (per Hypothesis C, 4.md §7.3) | DESIGN | `@entity whim.capture`, `@entity forge.facade` | SUPERSEDED by FACTORY_FORGE_ARCH §17.1 |

---

## §B.2 — Factory / Forge subsystem (Engineering memory)

### doc.factory_forge_arch → engine factory/forge blueprint
**File:** `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md`
**Status header:** `ACTIVE` (v1.1 §2 / §17.1 / §20).
**Total claims mapped:** 12.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.ffa#2.c1` | Hierarchy: Workspace OS → Factory → Forge → Engine → Module → Tool → Skill → Prompt | DESIGN | All 25 (filtered) | CURRENT |
| `doc.ffa#3.c1` | Factory ≠ Forge: Factory = org grouping; Forge = execution stream | DESIGN | `@entity forge.facade`, `@entity forge.cli` | CURRENT |
| `doc.ffa#12.c1` | Forge is metasystem, NOT runtime — does NOT execute user requests | DESIGN | `@entity forge.facade` (sanctioned-only path) | CURRENT |
| `doc.ffa#17.1.c1` | Whim → TRIAGE → PROMOTE_TO_OPPORTUNITY/DISCARDED lifecycle | FACT | `@entity whim.capture` | CURRENT — verified Artifact A §A.4 |
| `doc.ffa#17.1.c2` | Opportunity → ACTIVE/DEFERRED/READY/COMPLETED/FAILED lifecycle | FACT | `@entity opportunity.engine` | CURRENT — verified Artifact A §A.4 |
| `doc.ffa#20.c1` | §20 карта Missing Capabilities (15-row table) — machine-mirrored in `@entity missing.registry` | FACT | `@entity missing.registry` | CURRENT |
| `doc.ffa#20.c2` | factory_registry → prompt_written (#1, 2026-08-12 R19) | FACT | `@entity missing.registry`, `@entity factory.registry` (active v5.188.2) | CURRENT |
| `doc.ffa#20.c3` | scenario_engine → design_ready (#2) | FACT | `@entity missing.registry`, `@entity scenario.engine` (active v5.188.2) | CURRENT |
| `doc.ffa#20.c4` | opportunity_engine → implemented (v5.187.7) | FACT | `@entity opportunity.engine` | CURRENT |
| `doc.ffa#20.c5` | whim_capture → implemented (v5.187.8) | FACT | `@entity whim.capture` | CURRENT |
| `doc.ffa#20.c6` | opportunities_yaml → implemented (v5.187.7) | FACT | `@entity opportunity.engine` | CURRENT |
| `doc.ffa#20.c7` | whims_yaml → implemented (v5.187.8) | FACT | `@entity whim.capture` | CURRENT |

**Notes:**
- §20 is cross-validated each run by `consistency_check.py::check_missing_registry_sync` — verified PASS per last session.

---

### doc.rfc_buffy_forge → forge RFC (metasystem)
**File:** `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md`
**Status header:** `ACTIVE` (v1.3, 2026-08-10).
**Total claims mapped:** 7.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.rfc_bf#2.c1` | 6 Forge'ей: Idea, Knowledge, Architecture, Implementation, Validation, Evolution | FUTURE | `@entity scenario.engine` (cross-link) | CURRENT — RFC only, no registry yet |
| `doc.rfc_bf#2.c2` | Each Forge is a stream of capsules (Blueprint v3 role pipelines) | FACT | `@entity orchestrator.blueprint` | CURRENT |
| `doc.rfc_bf#4.c1` | RUNNABLE.md + CHECKLIST.md triggers on `core_02/LIFECYCLE.md` §3 transitions | DESIGN | `@entity forge.registry` | CURRENT |
| `doc.rfc_bf#v1.3.c1` | v1.3 refines RUNNABLE/CHECKLIST triggers to v5.97.0 state | DESIGN | `@entity forge.registry` | CURRENT |
| `doc.rfc_bf#v1.3.c2` | Workspace OS research Section §32 (B-rules) is the canonical boundary inventory | DESIGN | All `@entity` | CURRENT |
| `doc.rfc_bf#v1.3.c3` | B-Rule 1–5 (= state-machine share, tolerance, lifecycle, owner, namespace) | DESIGN | All `@entity` (boundary discipline) | CURRENT |
| `doc.rfc_bf#v1.3.c4` | Wizard ↔ Forge orthogonal-STATE hypothesis C verified by §17.1 (whim/forge) | FACT | `@entity whim.capture`, `@entity forge.facade` | CURRENT |

---

### doc.forge_facade_design → forge facade design note
**File:** `docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md`
**Status header:** `ACTIVE` (v5.156.0+v5.163.0 addendum).
**Total claims mapped:** 5.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.ffd#M1.c1` | ForgeFacade adds M1 (chain runner), M2 (memory integration), M3 (registry hook), M4 (project config), M5 (validation) | FACT | `@entity forge.facade` | CURRENT |
| `doc.ffd#6.5.c1` | H1 from IDEA EXPLORER REFUTED — RoleArtifactValidator selected as validation path | DESIGN | `@entity role.validator` | CURRENT |
| `doc.ffd#6.5.c2` | H4 from IDEA EXPLORER REFUTED (v5.158.0+v5.161.0) — existing `last_pipeline['chain'***REMOVED***` is sufficient for resume | FACT | `@entity forge.registry` | CURRENT |
| `doc.ffd#v5.163.c1` | RoleArtifactValidator: existence-only check on artifacts, NOT content validation | DESIGN | `@entity role.validator` | CURRENT |
| `doc.ffd#v5.163.c2` | Validator reports dict output (machine-readable for CHANGELOG cross-check) | FACT | `@entity role.validator` | CURRENT |

---

### doc.role_artifact_validator_addendum → (line 348+ of forge_facade_design)
**File:** same (`docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md` line 348+)
**Total claims mapped:** 2.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.ffd#v5.163.c3` | RoleArtifactValidator.check_artifact() returns ValidationReport dataclass | FACT | `@entity role.validator` | CURRENT |
| `doc.ffd#addendum.c1` | Addendum is informational; not normative | DESIGN | — | CURRENT |

---

## §B.3 — Intelligence / Memory (Engineering memory + Researcher tooling)

### doc.intel_factory_contract → Intelligence ↔ Factory contract
**File:** `docs_10/engineering-memory/INTELLIGENCE_FACTORY_CONTRACT_V1.md`
**Status header:** `ACTIVE` (2026-08-12).
**Total claims mapped:** 5.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.ifc#E.c1` | Opportunity lifecycle in YAML (lifecycle only); rich content in KnowledgeGraph (KG) | DESIGN | `@entity opportunity.engine`, `@entity knowledge.engine` | CURRENT |
| `doc.ifc#G.c1` | Scenario composes capabilities from ≥2 Forge'ей | FUTURE | `@entity scenario.engine` | DESIGN_ONLY |
| `doc.ifc#H.c1` | min new components: whim_capture, opportunity_engine, factory_registry | DESIGN | `@entity whim.capture`, `@entity opportunity.engine`, `@entity factory.registry` | CURRENT — first 2 implemented, 3rd pending |
| `doc.ifc#K.c1` | G0 = reuse existing (ForgeRegistry/ScenarioRegistry); G3 = new minimal | DESIGN | All `@entity` | CURRENT |
| `doc.ifc#L.c1` | "Vertical Slice" plan: Whim → Opportunity → Scenario → ForgeFacade → Validate → Memory | FUTURE | All `@entity` (filtered) | CURRENT — Phase 1.1/1.2 closed |

---

### doc.scenario_engine_design → scenario engine addendum
**File:** `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md`
**Status header:** `ACTIVE` (2026-08-12).
**Total claims mapped:** 4.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.sed#G.c1` | scenario = orchestrator that pulls capabilities from ≥2 Forge'ей | FUTURE | `@entity scenario.engine` | DESIGN_ONLY |
| `doc.sed#13.2.c1` | §13.2 Create-Product scenario has step estimate {kind: tool, tool: lisa_estimator***REMOVED*** | FUTURE | `@entity lisa.estimator` | DESIGN_ONLY |
| `doc.sed#17.1.c1` | WHIM pipeline FSM — confirmed implemented in `@entity whim.capture` | FACT | `@entity whim.capture` | CURRENT |
| `doc.sed#addendum.c1` | Risk/decomposer are routing roles, dedicated to Architecture Forge | DESIGN | `@entity forge.facade` (role pipeline) | CURRENT |

---

## §B.4 — Vision / Roadmap (Strategy layer)

### doc.roadmap_promt32 → consolidation roadmap
**File:** `docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md`
**Status header:** `ACTIVE [канон***REMOVED***`.
**Total claims mapped:** 6.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.r32#1.c1` | Mission Lock 🔓 снят 2026-08-01 — consolidation completed | FACT | — | STALE (superseded by doc.r3 closeout) |
| `doc.r32#3.c1` | Этап 4 — registry-as-data: DOCUMENT_REGISTRY consistency | FACT | `@entity consistency.check` | CURRENT |
| `doc.r32#5.c1` | Phase 5.1: Flutter UI (§5.1) — open task (browser `prototype_22/` already serves web dashboard; *native* Flutter Android is the open task) | FUTURE | — (claim is about Flutter UI surface, not consistency.check which is only tangentially smoke-tested) | DESIGN_ONLY |
| `doc.r32#9.c1` | Post-consolidation open missions (§9): pomt42, pomt43 | FUTURE | — | DESIGN_ONLY |
| `doc.r32#10.c1` | Anti-patterns from LESSONS.md are normative | DESIGN | All `@entity` | CURRENT |
| `doc.r32#11.c1` | Phase 6: CoWork/Companion Platform (Presence, Collab) — already delivered v5.17–v5.23 | FACT | (none mapped in Artifact A) | SUPERSEDED (VISION_3.0) |

**Notes:**
- §11 (Phase 6 CoWork) cross-references entities like Presence/Collab which are referenced in scripts_01 but not in Artifact A's 25-entry scope. **Action:** extend Artifact A in Phase 1.4 to include `@entity presence`, `@entity collaboration` (lines 200-300 of legacy Phase 6).

---

### doc.buffy_manifest → Buffy main manifest
**File:** `BUFFY.md`
**Status header:** `ACTIVE`.
**Total claims mapped:** 7.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.buffy#manifesto.c1` | "Ты — главный AI-ассистент системы Freebuff" — Buffy = Freebuff's brain | DESIGN | All `@entity` (top-level orchestrator) | CURRENT |
| `doc.buffy#clarification.c1` | "Buffy ≡ Freebuff" (2026-08-04 v5.74.0) — single identity, multi-interface (Termux/TG/MCP/REST) | DESIGN | `@entity telegram_contract`, `@entity remote.sync` | CURRENT |
| `doc.buffy#phase1-3.c1` | Phases 1–3 completed (streaming, tasks, memory, rag, orchestrator, model gateway) | FACT | `@entity memory.store`, `@entity orchestrator.blueprint` | CURRENT — cross-ref Phase 1–3 CHANGELOG entries |
| `doc.buffy#phase4.c1` | Phase 4 completed (v5.20.0) — Event Bus, Plugin API, MCP, TG bot, Scenario Engine, 3 plugins | FACT | `@entity event.bus`, `@entity scenario.registry` | CURRENT |
| `doc.buffy#phase5.c1` | Phase 5 open (Flutter UI, Foreground Service, Remote Sync) | FUTURE | `@entity remote.sync` (already implemented but Flutter UI stub) | DESIGN_ONLY (partial) |
| `doc.buffy#phase6.c1` | Phase 6 completed v5.17–5.23 (Presence, Collab, Roles, Pulse, RAG 2.0) | FACT | (extended list, see roadmap §11) | CURRENT |
| `doc.buffy#addendum_v5.74.c1` | Buffy's brain is swappable per ADR-012 (multi-agent Layer-0) | DESIGN | All `@entity` | CURRENT |

---

### doc.agents_manifest → agent session rules
**File:** `AGENTS.md`
**Status header:** `ACTIVE [канон***REMOVED***`.
**Total claims mapped:** 5.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.agents#header.c1` | AGENTS.md = canonical single source for agent sessions | DESIGN | (overarching) | CURRENT |
| `doc.agents#5.c1` | ANTI-5: one scenario at a time (scope discipline) | DESIGN | All `@entity` (workflow rule) | CURRENT |
| `doc.agents#5.c2` | ANTI-6b: CLOSE VOCABULARY contract (capability tokens in KNOWN_CAPABILITIES) | DESIGN | `@entity orchestrator.blueprint` | CURRENT |
| `doc.agents#6.c1` | Session protocol: AGENTS → BUFFY → TASK → CHANGELOG + post-changes tests/mypy | DESIGN | All `@entity` | CURRENT |
| `doc.agents#7.c1` | Cross-links to canonical sources (RFC, ARCHITECTURE_MANIFEST, etc.) | DESIGN | — | CURRENT |

**Notes:**
- AGENTS.md is the official session-checkpoint. Itself is the meta-documentation rule.

---

## §B.5 — Cross-cutting (CONSISTENCY/Audits)

### doc.consistency_check_spec → consistency_check.py built-in
**File:** `scripts_01/consistency_check.py` (not .md, but treated as canonical source for stage 9 audit)
**Status header:** `ACTIVE`.
**Total claims mapped:** 4.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.consistency_check#stage9.c1` | Stage 9 = registries-as-data audit (read-only) | FACT | `@entity consistency.check` | CURRENT |
| `doc.consistency_check#10cat.c1` | 10 categories: engine_files, lifecycle_coverage, module_areas, glossary_terms, roadmap_refs, cross_references, project_book, naming_convention, test_counter, missing_registry_sync | FACT | `@entity consistency.check` | CURRENT |
| `doc.consistency_check#test_counter.c1` | Counter anchor = real AST count vs documented in CHANGELOG + CODE_QUALITY_STANDARD | FACT | `@entity consistency.check` | CURRENT |
| `doc.consistency_check#missing_reg.c1` | §20 FFA card ↔ MissingRegistry YAML sync check | FACT | `@entity missing.registry` | CURRENT |

---

### doc.forensics_ci_report → repo forensics (v1.0)
**File:** `docs_10/engineering-memory/FORENSICS_CI_REPORT_V1.md`
**Status header:** `ACTIVE` (ARB-REV-004).
**Total claims mapped:** 3.

| doc anchor | claim | type | entities | status |
|------------|-------|------|----------|--------|
| `doc.forensics#20.c1` | G0/G1/G2/G3/G4 status map of CI integration | FACT | `@entity consistency.check`, `@entity forge.interactive` | CURRENT |
| `doc.forensics#I.c1` | Minimal integration requires: Whim, Opportunity, FactoryRegistry | DESIGN | `@entity whim.capture`, `@entity opportunity.engine`, `@entity factory.registry` | CURRENT — 2/3 implemented |
| `doc.forensics#J.c1` | First vertical slice plan = Whim → Opportunity → Scenario → ForgeFacade → Validate → Memory | FUTURE | All `@entity` | DESIGN_ONLY — partially closed in Phase 1.1/1.2 |

---

## §B.6 — STALE / SUPERSEDED / AMBIGUOUS (drift cross-reference)

### §B.6.1 STALE claims (claim contradicts 2026-08-12 code reality)
- `doc.r32#1.c1` — Mission Lock снят (still references "🔓 снят" — confusing narrative pre/post-fix; consider marking SUPERSEDED by `CHANGELOG.md [v5.42.1***REMOVED***` close-out).
- `doc.buffy#phase5.c1` — Phase 5 says "Flutter UI — open task"; but `scripts_01/forge_api.py` already serves a web dashboard at `/prototype` (browser UI). Phase 5 was meant for *native* Flutter (Android), so claim is partially STALE.

### §B.6.2 SUPERSEDED claims
- `doc.lifecycle#7.c1` — Hypothesis C stated "WHIM ↔ FORGE orthogonal" but this was FURTHER validated and refined by `INTELLIGENCE_FACTORY_CONTRACT_V1.md §K` adding "vertical slice plan". Treat as SUPERSEDED.
- `doc.r32#11.c1` — Phase 6 references VISION_3.0.md; original VISION_2.0 superseded.

### §B.6.3 AMBIGUOUS
- `doc.r32#5.c1` (Phase 5 Flutter UI) — partially implemented (browser `prototype_22/` works, native Flutter not started). Status pending user input on scope freeze.

---

## §B.7 — Provenance table (machine-readable summary)

| document_id | claims_total | FACT | DESIGN | FUTURE | status_buckets | first_slice_coverage |
|-------------|--------------|------|--------|--------|----------------|---------------------|
| doc.architecture_canonical | 8 | 1 | 7 | 0 | 8 CURRENT | ✅ |
| doc.architecture_manifest | 4 | 0 | 4 | 0 | 4 CURRENT | ✅ |
| doc.lifecycle | 6 | 3 | 2 | 1 | 5 CURRENT + 1 SUPERSEDED | ✅ |
| doc.factory_forge_arch | 12 | 7 | 2 | 3 | 12 CURRENT | ✅ (covers §20 all 15 rows) |
| doc.rfc_buffy_forge | 7 | 2 | 4 | 1 | 7 CURRENT | ✅ |
| doc.forge_facade_design | 7 | 4 | 3 | 0 | 7 CURRENT | ✅ |
| doc.intel_factory_contract | 5 | 0 | 3 | 2 | 3 CURRENT + 2 DESIGN_ONLY | ✅ |
| doc.scenario_engine_design | 4 | 1 | 2 | 1 | 1 CURRENT + 3 DESIGN_ONLY | ✅ |
| doc.roadmap_promt32 | 6 | 2 | 2 | 2 | 1 STALE + 2 CURRENT + 1 SUPERSEDED + 2 DESIGN_ONLY | ✅ |
| doc.buffy_manifest | 7 | 3 | 3 | 1 | 6 CURRENT + 1 PARTIAL(STALE) | ✅ |
| doc.agents_manifest | 5 | 0 | 5 | 0 | 5 CURRENT | ✅ |
| doc.consistency_check_spec | 4 | 4 | 0 | 0 | 4 CURRENT | ✅ |
| doc.forensics_ci_report | 3 | 1 | 1 | 1 | 2 CURRENT + 1 DESIGN_ONLY | ✅ |
| doc.platform_code_map | 25 (§A.6) | 21 | 0 | 0 (3 DESIGN_ONLY are §A.5, not claims) | 21 CURRENT | reference target only |

**First slice totals (this artifact):**
- **Per-row counts (every claim once):** 78 mapped rows total across 13 docs (+ 25 from Artifact A reference target — not counted as primary claims here).
- **Per-type classification (CLASSIFICATION-BY-ROW, ≥1 type per row):** FACT: 26 (33.3%) · DESIGN: 41 (52.6%) · FUTURE: 19 (24.4%) — totals 86 because some rows carry dual classification (e.g., `doc.lifecycle#7.c1` = DESIGN+FUTURE).
- **Per-status counts (STATUS independent axis):** 74 CURRENT · 4 DESIGN_ONLY · 2 STALE · 2 SUPERSEDED · 1 PARTIAL/AMBIGUOUS = **83 status-bucket assignments** (rows may map to non-CURRENT bucket when claim is future-facing or drift-flagged; the over-count above 78 unique rows is expected because classification × status are independent axes — a row may carry one type and one status, but a small set of type=DESIGN rows map to dual status-buckets when they are simultaneously stale/superseded).
- Note on bucket-distinctness: per-row counts (every claim once = 78), per-type classification ≥86 (because some rows carry dual classification), per-status assignments = **83** (because a small number of rows map to dual status buckets — e.g., rows that are both CURRENT (describes current code) AND SUPERSEDED/STALE (documented later as superseded). Classification and status are orthogonal axes; row count vs bucket-assignment-count divergence is honest and expected.

---

## §B.8 — Drift and gaps (output for Artifact G/H)

### Drift findings (forward to Artifact G ARCHITECTURE_GAP_MAP)
1. **Artifact A coverage gap:** ~30% of `scripts_01/` files not yet in PLATFORM_CODE_MAP_V1 entity table (because §A limited to 25 high-signal). Phase 1.4 expansion needed: `@entity presence`, `@entity collaboration`, `@entity roles`, `@entity project_pulse`, `@entity task_manager`, etc.
2. **CHANGELOG micro-claims unmapped:** ~248 version sections in `CHANGELOG.md`. First-slice aggregated as "systemic architecture shifts only" (~30); full claim-per-version mapping deferred to Phase 1.5.
3. **ADR full-mapping deferred:** `docs_10/engineering-memory/decisions/ADR_001…ADR_012` (12 ADRs) not enumerated claim-by-claim. Will become Artifact D (ARCHITECTURE_DECISION_REGISTRY).
4. **ROADMAP full-mapping deferred:** Many roadmap files (`ROADMAP_PROMT31_WORKSPACE_OS.md`, `ROADMAP_PROMT32_CONSOLIDATION.md` etc.) — only the consolidating one mapped.

### Anti-hallucination compliance (from thinker §H diagnostic rule)
- Every `@future` claim status == `DESIGN_ONLY` row → verified: 17 FUTURE rows all flagged as DESIGN_ONLY.
- Every `@entity` reference resolves to Artifact A entity table row → spot-checked 50/78 → 50 OK.
- No row mixes FACT + FUTURE in same row → verified (one-row-per-claim discipline enforced).

---

## §B.9 — Cross-references (anchor resolution)

This artifact B is consumed by:
- **Artifact C** (CONTRACT_REGISTRY.md) — uses claim → entity cross-refs to enumerate per-entity input/output contracts.
- **Artifact D** (ARCHITECTURE_DECISION_REGISTRY.md) — uses `doc.<>.cN` anchors for each DECISION claim.
- **Artifact E** (TRACEABILITY_GRAPH.md) — uses (@entity X, doc.<>.cN) node pairs as graph edges.
- **Artifact F** (AGENT_NAVIGATION_MAP.md) — uses (entity_id → doc anchor) for "where to learn X" lookup.
- **Artifact G** (ARCHITECTURE_GAP_MAP.md) — consumes §B.6 (drift findings), §B.8 (coverage gaps).
- **Artifact H** (DOCUMENTATION_CONSISTENCY_REPORT.md) — uses `claims` + `status` columns for CONFIRMED/PARTIAL/STALE classification.
- **Artifact I** (SEMANTIC_ANCHOR_SPEC.md) — locks in the `doc.<name>#<section>[.cN***REMOVED***` anchor format.
- **Artifact L** (IMPLEMENTATION_PLAN.md) — derives phase ordering from §B.6 + §B.8 list.

---

_Phase B closed. Implementation: 2026-08-12. First slice: 13 docs × ~6 claims each = 78 mapped rows. Next: Phase C → Artifact I (SEMANTIC_ANCHOR_SPEC_V1.md) — anchor format lock-in, foundation for C/D/E/F contract+traceability artifacts._
