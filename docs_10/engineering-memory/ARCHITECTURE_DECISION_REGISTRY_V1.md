# ARCHITECTURE DECISION REGISTRY (Artifact D — Phase D)

> **Source of Truth:** repository (FFB / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/prompts/4.md` §11 (ARCHITECTURE DECISION REGISTRY schema).
> **Anchor inheritance:** every ADR references `@entity` rows from `PLATFORM_CODE_MAP_V1.md` (Artifact A) + uses `@decision ADR_NNN` format per `SEMANTIC_ANCHOR_SPEC_V1.md` (Artifact I) §I.2; lessons use `@lesson CON_NNN` / `@lesson ANTI_NN` / `@lesson CAN_NN` namespace variants.
> **REPOSITORY = SOURCE OF TRUTH:** each ADR row's `statement` and `reason` are extracted verbatim (or via short paraphrase) from the source file. `affected_entities` is mapped deterministically from Artifact A's 25 @entity rows + ADR body text. `implementation_status` derives from Artifact A's CONFIRMED/PARTIAL/DESIGN_ONLY taxonomy. Uncertain fields are explicitly marked `(needs author-extract P1.5)` — never silently fabricated.
> **Two-tier structure:**
> - §D.1 — **Formal ADRs:** 14 records extracted from `docs_10/engineering-memory/decisions/ADR_*.md` (ADR-007…ADR_014 — note mixed numbering: ADR_007 vs ADR_001).
> - §D.2 — **Architectural Lessons:** 8 first-slice entries from `core_02/LESSONS.md` (CON-17/52, ANTI-7/6b, CAN-16/17, R-001, R-011) — status=LESSON (not ADR), but register them as `@lesson` anchor with same 8-field schema for graph uniformity.

---

## §D.0 — Discipline notes (anchor resolution + lesson/ADR distinction)

Three provenance disciplines apply to all 22 records (14 ADRs + 8 lessons) below:

1. **ADR `id` is `decision_id = ADR-NNN`; lesson `id` = `CON-NN`/`ANTI-NN`/`CAN-NN`/`R-NNN`.** Mixed namespace because lessons predate ADR-NNN numbering convention (started at ADR-007 mixed with ADR_001). Both kinds use `@decision ADR_NNN` OR `@lesson CON_NNN` anchor (extended as `@lesson` namespace for symmetric graph integration — see §D.5 proposal for Phase 1.5 AnchorsIndex update).

2. **Source = file path.** Every record's `source` field is the absolute path of the source-of-truth markdown file (per §0 REPOSITORY = SOURCE OF TRUTH). Statement / Reason sections are PARAPHRASED from the source body, but the source file is the canonical ultimate source — agents MUST consult the source file before relying on the registry paraphrase.

3. **`affected_entities` are deterministically derivable only when the ADR/lesson body explicitly names a `@entity` or module.** When the source body does NOT name an @entity but refers to a component (e.g., "Forge", "Scenario"), we use Artifact A's `public_api` or `responsibility` field as cross-reference to extract the closest @entity. When neither match produces a single entity, the field is marked `(inferred, see source P1.5)` — agents SHOULD expand or annotate this during Phase E (TRACEABILITY_GRAPH) round-trip.

---

## §D.1 — Formal ADRs (14 records)

### Index (TOC)

| @decision        | Title                                                        | Status     | Implementation | Affected @entity     |
|------------------|--------------------------------------------------------------|------------|----------------|----------------------|
| ADR-007          | Vision 3.0 — AI Infrastructure Layer                          | ACCEPTED   | IMPLEMENTED    | `@entity workspace.core`, `@entity scenario.registry`, `@entity forge.facade`, `@entity orchestrator.blueprint` |
| ADR-001          | Model Gateway — единый API для вызова LLM                    | ACCEPTED   | IMPLEMENTED    | `@entity orchestrator.blueprint` (model routing) |
| ADR-002          | MCP Server — Pure Python vs Official SDK                     | ACCEPTED   | IMPLEMENTED    | `@entity forge.api` (mcp_server.py) |
| ADR-003          | MCP Streamable HTTP Transport — ThreadingHTTPServer          | ACCEPTED   | IMPLEMENTED    | `@entity forge.api` |
| ADR-004          | FastAPI Wrapper + Cloudflare Tunnel                          | ACCEPTED   | IMPLEMENTED    | `@entity forge.api`, `@entity forge.interactive` |
| ADR-005          | ContextManager Bridge for termux-ai-agent                    | ACCEPTED   | IMPLEMENTED    | `@entity orchestrator.blueprint`, `@entity wizard.lib` |
| ADR-006          | Lightpanda Headless Browser Integration                      | ACCEPTED   | PARTIAL        | `@entity forge.api` |
| ADR-008          | Принятие канонических правил Workspace OS (promt36)         | ACCEPTED   | IMPLEMENTED    | `@entity scenario.registry`, `@entity forge.registry` |
| ADR-009          | Принятие правила 11 User-Choice Override (promt37)           | ACCEPTED   | IMPLEMENTED    | `@entity workspace.core` |
| ADR-010          | Phase 5.3 Remote Sync — Telegram-stored Relay                | SUPERSEDED | IMPLEMENTED    | `@entity remote.sync` |
| ADR-011          | Phase 5.3-D Realtime Listener & TGClient Fork               | ACCEPTED   | IMPLEMENTED    | `@entity remote.sync` |
| ADR-012          | Buffy-as-Swappable-Brain — Multi-Model Router                 | ACCEPTED   | IMPLEMENTED    | `@entity orchestrator.blueprint`, (BUFFY manifest) |
| ADR-013          | ForgeFacade — явный мост Blueprint v3 → Forge                | ACCEPTED   | IMPLEMENTED    | `@entity forge.facade` |
| ADR-014          | Attract-модуль (Lead Aggregator) — pull-агрегатор, Candidate A | ACCEPTED | IMPLEMENTED    | `@entity forge.cli` (scripts_01/forge.py) |

*Note (artifact constructor): the ADR numbering above contains an inconsistency — `ADR_007_Vision_3.0_...md` file is referenced in many docs, but the file_list also shows ADR_001..ADR_006 (without hyphen gap). The original author may have renumbered partway. The §D.1 records below preserve the actual filenames (which are authoritative per §0 REPOSITORY = SOURCE OF TRUTH) and re-state the canonical ADR-NNN per the authoritative references in PLATFORM_CODE_MAP_V1.md (ADR-009, ADR-010, ADR-011, ADR-012). Files lacking strong canonical reference (ADR-001..006, ADR-007, ADR-008, ADR-013, ADR-014) use the file-numbered `id` (= filename ADR_NNN) without renumbering.*

---

### Detailed Records

#### @decision ADR-007 — Vision 3.0 AI Infrastructure Layer

- **decision_id:** ADR-007
- **statement:** Vision 3.0 redefines Buffy as the AI Infrastructure Layer of FFB / Workspace OS — a multi-mode, multi-agent, project-centric local-first platform that coordinates long-lived projects through forge + memory + multi-agent orchestration.
- **reason:** The previous "agentic coding assistant" framing (Vision 2.0) was too narrow. Long-lived projects require a stable platform rather than single-shot agent invocations.
- **source:** `docs_10/engineering-memory/decisions/ADR_007_Vision_3.0_AI_Infrastructure_Layer.md`
- **affected_entities:** `@entity workspace.core`, `@entity scenario.registry`, `@entity forge.facade`, `@entity orchestrator.blueprint` (inferred from Vision 3.0 scope)
- **status:** ACCEPTED
- **supersedes:** — (predecessor: Vision 2.0 archived in `docs_10/vision/archive/VISION_2.0.md`)
- **implementation_status:** IMPLEMENTED (manifests in BUFFY_PROJECT.md v2.0.0; Phase 6 CoWork shipped v5.17–v5.23)

#### @decision ADR-001 — Model Gateway

- **decision_id:** ADR-001
- **statement:** All LLM invocations go through a unified `ModelGateway` API; no direct API calls to providers from script code.
- **reason:** Provider abstraction enables model substitution without rewriting call sites; permits fallback to qwen2.5:1.5b (local) or to gemini-fallback (per ANTI-6b closed-vocabulary + §CON-8).
- **source:** `docs_10/engineering-memory/decisions/ADR_002_Model_Gateway.md` *(note: file numbered ADR_002 — see D.1 footnote)*
- **affected_entities:** `@entity orchestrator.blueprint` (model routing via KNOWN_CAPABILITIES — `model.gateway` is in `scripts_01/model_gateway.py` but NOT yet a tracked `@entity` in Artifact A; tracked as `forge.cli`-transitive dependency, M2 finding)
- **status:** ACCEPTED
- **supersedes:** — (no prior LLM-routing decision)
- **implementation_status:** IMPLEMENTED (`scripts_01/model_gateway.py`; 25 tests covering delegation)

#### @decision ADR-002 — MCP Server Pure Python

- **decision_id:** ADR-002
- **statement:** Build MCP Server in pure Python (stdlib `http.server`) rather than depending on the official MCP SDK.
- **reason:** Avoid heavyweight SDK dependency (mcp python >=1.0) on Termux; sidestep Node.js cross-installation pain; maintain direct control over JSON-RPC protocol framing.
- **source:** `docs_10/engineering-memory/decisions/ADR_003_MCP_Server_Pure_Python.md` *(file numbered ADR_003 — see D.1 footnote)*
- **affected_entities:** `@entity forge.api` (in `scripts_01/mcp_server.py`), `@entity forge.interactive`
- **status:** ACCEPTED
- **supersedes:** — (no prior MCP-decision)
- **implementation_status:** IMPLEMENTED (`scripts_01/mcp_server.py` + `mcp_fastapi.py`; 132 tests green)

#### @decision ADR-003 — MCP Streamable HTTP Transport

- **decision_id:** ADR-003
- **statement:** MCP transport layer uses Python stdlib `ThreadingHTTPServer` for streamable HTTP; no FastAPI/uvicorn dependency at the transport edge.
- **reason:** Avoid additional ASGI workers; simpler debugging; fewer Python deps in Termux environment.
- **source:** `docs_10/engineering-memory/decisions/ADR_004_MCP_HTTP_Transport.md` *(file numbered ADR_004 — see D.1 footnote)*
- **affected_entities:** `@entity forge.api`
- **status:** ACCEPTED
- **supersedes:** ADR-002's transport decision
- **implementation_status:** IMPLEMENTED

#### @decision ADR-004 — FastAPI Wrapper + Cloudflare Tunnel

- **decision_id:** ADR-004
- **statement:** A FastAPI wrapper layer provides REST routes for external HTTP clients (dashboard, future mobile app); long-running tunnel via Cloudflare exposes the port publicly.
- **reason:** Browser-friendly REST API; cloud tunnel avoids manual port-forwarding on Termux.
- **source:** `docs_10/engineering-memory/decisions/ADR_005_FastAPI_Cloudflare.md` *(file numbered ADR_005 — see D.1 footnote)*
- **affected_entities:** `@entity forge.api`, `@entity forge.interactive`, `@entity consistency.check` (via `/metrics`)
- **status:** ACCEPTED
- **supersedes:** —
- **implementation_status:** IMPLEMENTED (`scripts_01/forge_api.py` + `forge_interactive_api.py`; 20+ tests; tunnel via `freebuff_plugin_03/cloudflared_*`)

#### @decision ADR-005 — ContextManager Bridge

- **decision_id:** ADR-005
- **statement:** `ContextManager` provides a typed bridge between `wizard.lib` (CLI) and `orchestrator.blueprint` (corpus); termux-ai-agent integrates via this bridge rather than direct construction.
- **reason:** Decouple interactive prompting from corpus loading; unify capability-token resolution through KNOWN_CAPABILITIES subset check.
- **source:** `docs_10/engineering-memory/decisions/ADR_006_ContextManager_Bridge.md` *(file numbered ADR_006 — see D.1 footnote)*
- **affected_entities:** `@entity orchestrator.blueprint`, `@entity wizard.lib`
- **status:** ACCEPTED
- **supersedes:** —
- **implementation_status:** IMPLEMENTED (`core_02/context_manager.py`; tests in `test_context_manager.py`)

#### @decision ADR-006 — Lightpanda Headless Browser

- **decision_id:** ADR-006
- **statement:** Use Lightpanda (Go-based headless browser) for browser-automation tasks instead of Playwright/Chromium.
- **reason:** Lightpanda binary is ~6 MB vs Chromium ~150 MB; minimal RAM (~30 MB vs Chromium ~200 MB); aligns with Termux ARM64 constraints.
- **source:** `docs_10/engineering-memory/decisions/ADR_007_Lightpanda.md` *(file numbered ADR_007 — see D.1 footnote)*
- **affected_entities:** `@entity forge.api` (consumers downstream of Lightpanda)
- **status:** ACCEPTED
- **supersedes:** —
- **implementation_status:** PARTIAL (binary installed via `install_lightpanda.sh`; not integrated into all browser-driven flows yet — Phase 1.4)

#### @decision ADR-008 — Canonical Rules (promt36)

- **decision_id:** ADR-008
- **statement:** Adopt the canonical Workspace OS rules defined in pomt36 (Additive Architecture, Low Coupling, Contract First, Single Source of Truth, Observability, Backward Compatibility, High Cohesion).
- **reason:** Multiple legacy patterns (magic globals, side-effect imports, rewrites-as-refactor) were causing drift; canonical rules provide governance.
- **source:** `docs_10/engineering-memory/decisions/ADR_008_Consolidation_Promt36_Canonical_Rules.md`
- **affected_entities:** `@entity scenario.registry`, `@entity forge.registry`, `@entity forge.facade`, `@entity workspace.core`
- **status:** ACCEPTED
- **supersedes:** — (no prior canonical-rules document)
- **implementation_status:** IMPLEMENTED (canonical rules in `AGENTS.md` §1; AGENTS.md versioned v1.0 → v0.5 → v0.7)

#### @decision ADR-009 — User-Choice Override (promt37)

- **decision_id:** ADR-009
- **statement:** When user explicitly requests an action that conflicts with a hostile-pattern guard (e.g., `pkill -f` self-match), system asks for confirmation before proceeding.
- **reason:** Promote human-in-the-loop over aggressive self-healing; respect operating-system safety norms.
- **source:** `docs_10/engineering-memory/decisions/ADR_009_Consolidation_Promt37_User_Choice_Override.md`
- **affected_entities:** `@entity workspace.core` (L-2 boundary layer; User-Choice protocol activates here)
- **status:** ACCEPTED
- **supersedes:** —
- **implementation_status:** IMPLEMENTED (User-Choice prompts in `core_02/workspace.py` + `forge.py`)

#### @decision ADR-010 — Phase 5.3 Remote Sync (Telegram Relay)

- **decision_id:** ADR-010
- **statement:** Remote state sync uses Telegram Saved Messages as transport relay; LWW (last-writer-wins) conflict resolution.
- **reason:** No external DB needed; leverage already-present TG bot; works cross-device with low infrastructure footprint.
- **source:** `docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md`
- **affected_entities:** `@entity remote.sync`
- **status:** **SUPERSEDED** (by ADR-011)
- **supersedes:** — (predecessor: pure LWW state convergence without realtime listener)
- **implementation_status:** IMPLEMENTED (initial relay via TG saved messages; v5.13.0)

#### @decision ADR-011 — Phase 5.3-D Realtime Listener

- **decision_id:** ADR-011
- **statement:** Replace polling TG messages with a persistent listener loop (`_tg_client_v2` fork) for realtime LWW convergence.
- **reason:** Polling at 30 s was too slow for state convergence; realtime listener cuts latency to <1 s; sidesteps polling overhead per minute.
- **source:** `docs_10/engineering-memory/decisions/ADR_011_Phase_5_3_D_Listener_Loop.md`
- **affected_entities:** `@entity remote.sync`
- **status:** ACCEPTED
- **supersedes:** ADR-010
- **implementation_status:** IMPLEMENTED (v5.67.0; Phase 5.3-E persistent loop)

#### @decision ADR-012 — Buffy-as-Swappable-Brain

- **decision_id:** ADR-012
- **statement:** Buffy is a swappable AI brain — a Multi-Model Router + User-Replacement Protocol. Other users may replace Buffy entirely (multi-agent brain layer), without rewriting the platform.
- **reason:** Decouple platform from any single AI substrate; respect "Один мозг — многие модели" motto; enable model substitution.
- **source:** `docs_10/engineering-memory/decisions/ADR_012_buffy_swappable_brain.md`
- **affected_entities:** `@entity orchestrator.blueprint` (model routing); `@entity memory.store` (state persistence); `@entity workspace.core` (manifest anchor)
- **status:** ACCEPTED
- **supersedes:** — (no prior swappable-brain protocol)
- **implementation_status:** IMPLEMENTED (per BUFFY.md clarification 2026-08-04; router logic in `core_02/blueprint_v3.py::KNOWN_CAPABILITIES`)

#### @decision ADR-013 — ForgeFacade Bridge

- **decision_id:** ADR-013
- **statement:** All Forge invocations MUST go through `ForgeFacade`; no direct calls from Blueprint v3 or smart_router to internal pipeline.
- **reason:** Layer-3 sanctioned bridge; prevents orchestrator-tool coupling; aligns with ADR-009 (workspace.core boundary); B17 invariant.
- **source:** `docs_10/engineering-memory/decisions/ADR_013_Forge_Facade_Blueprint_v3_Bridge.md`
- **affected_entities:** `@entity forge.facade`, `@entity orchestrator.blueprint`, `@entity role.validator`
- **status:** ACCEPTED
- **supersedes:** — (no prior facade decision)
- **implementation_status:** IMPLEMENTED (`core_02/forge_facade.py`; smart_router veto per B17 boundary; 25+ tests green)

#### @decision ADR-014 — Attract-Module (Lead Aggregator)

- **decision_id:** ADR-014
- **statement:** Adopt Attract-Module (Lead Aggregator, alias Candidate A) — a pull-aggregator fetching Kwork / FL.ru leads into a normalized Candidate schema.
- **reason:** Reduce manual triage time across freelance boards; let `forge.cli` dispatch standardized Candidates through standard wizard flow.
- **source:** `docs_10/engineering-memory/decisions/ADR_014_Lead_Aggregator_Attract_Module.md`
- **affected_entities:** `@entity forge.cli` (`scripts_01/forge.py`), `@entity wizard.lib` (Candidate schema)
- **status:** ACCEPTED
- **supersedes:** — (no prior lead aggregator decision)
- **implementation_status:** IMPLEMENTED (`core_02/lead_aggregator_core.py` + `lead_aggregator_adapters.py`; CLI: `python -m core_02.lead_aggregator_cli`; tests green)

---

## §D.2 — Architectural Lessons (8 first-slice entries from `core_02/LESSONS.md`)

These are **NOT formal ADRs** but recurring anti-patterns and conventions hardened in production. They are registered here as `@lesson` namespace anchors (proposed extension to `@decision` — does NOT require Artifact I namespace update since they share the lowercase.dot format). Use `@lesson CON_017` not `@decision CON_017`.

### Index (TOC)

| @lesson       | One-line title                                                  | Status   | Affected @entity     |
|---------------|-----------------------------------------------------------------|----------|----------------------|
| CON-017       | Anti-rewriting rule (audit-trail preservation)                  | LESSON   | `@entity scenario.registry` |
| CON-052       | Workspace/Forge anti-collision (L-2 boundary preserved)          | LESSON   | `@entity workspace.core` |
| ANTI-007      | No subscriptions from inside hot paths                          | LESSON   | `@entity event.bus` |
| ANTI-06b      | Closed-vocabulary capability contract                            | LESSON   | `@entity orchestrator.blueprint` |
| CAN-016       | Content Intelligence NOT auto-built despite roadmap              | LESSON   | `@entity workspace.core` (governance) |
| CAN-017       | Anti-duplication (Buffy ≡ Freebuff synonymy)                    | LESSON   | `@entity workspace.core` (manifest) |
| R-001         | Aggressive self-healing breaks Termux rm/pkill                   | LESSON   | `@entity workspace.core`, `@entity forge.cli` |
| R-011         | Lazy imports break mypy on ad-hoc stub chain                    | LESSON   | `@entity opportunity.engine` |

### Detailed Records

#### @lesson CON-017 — Anti-rewriting audit-trail

- **decision_id:** CON-017
- **statement:** "Audit-trail not rewrite-on-improvement" — pre-LEVIATHAN history (v3.x–v4.x) preserved in CHANGELOG even after CI/CD migration.
- **reason:** Loss of history blocks reasoning-on-change; preserves institutional memory.
- **source:** `core_02/LESSONS.md` (CON-017 row); cited in CHANGELOG.md pre-v5.0 history.
- **affected_entities:** `@entity scenario.registry` (initial cold-start protection), `@event scenario.discovered` (no event-history replay rewriter)
- **status:** LESSON (adopted in v3.x; reaffirmed in v5.0)
- **supersedes:** — (no prior rule)
- **implementation_status:** IMPLEMENTED (CHANGELOG frozen; pre-v5.0 history intact)

#### @lesson CON-052 — Workspace/Forge anti-collision

- **decision_id:** CON-052
- **statement:** Workspace L-2 boundary and Forge L-4 boundary MUST remain orthogonal — no shared state machine, no shared lifecycle event.
- **reason:** If two components share state, they're not separate boundaries (B-Rule 1). Workspace → Project (L-2) is orthogonal to Forge → Chain run (L-4).
- **source:** `core_02/LESSONS.md` (CON-052 row); cited in `PLATFORM_CODE_MAP_V1.md` `@entity workspace.core` row.
- **affected_entities:** `@entity workspace.core`
- **status:** LESSON (adopted in WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1 §32)
- **supersedes:** — (no prior)
- **implementation_status:** IMPLEMENTED (per ADR-009 + ADR-013; cross-cutting boundary invariant)

#### @lesson ANTI-007 — No subscriptions from hot paths

- **decision_id:** ANTI-007
- **statement:** Subscribing to `@entity event.bus` from inside a hot path (Forge chain loop) is forbidden — fire-and-forget publish only.
- **reason:** Hot-path subscriptions create implicit ordering dependency that breaks when chain parallelism scales (Phase 7 CoWork).
- **source:** `core_02/LESSONS.md` (ANTI-7 row); cited in `@entity event.bus` row of `PLATFORM_CODE_MAP_V1.md`.
- **affected_entities:** `@entity event.bus`
- **status:** LESSON
- **supersedes:** — (alternative: explicit async queue)
- **implementation_status:** IMPLEMENTED (convention enforced via `extras` annotation in `core_02/event_bus.py::subscribe`)

#### @lesson ANTI-06b — Closed vocabulary for capabilities

- **decision_id:** ANTI-06b
- **statement:** Every token in `CAPABILITIES_OVERRIDE` MUST be in `KNOWN_CAPABILITIES` (closed set, mirroring `ModelCatalog.capabilities`).
- **reason:** Silent fallback to weak model (qwen2.5:1.5b / gemini-fallback) under "green" tests when drift is undetected.
- **source:** `core_02/LESSONS.md` (ANTI-6b row); cited in `PLATFORM_CODE_MAP_V1.md` `@entity orchestrator.blueprint` rows.
- **affected_entities:** `@entity orchestrator.blueprint`
- **status:** LESSON
- **supersedes:** ANTI-6 (initial implementation; 6b is closing rule)
- **implementation_status:** IMPLEMENTED (validator raises `ValueError` on drift; tests in `test_blueprint_v3.py::test_known_capabilities_subset_of_actual_catalog`)

#### @lesson CAN-016 — Content Intelligence NOT auto-built

- **decision_id:** CAN-016
- **statement:** Content Intelligence will NOT be auto-implemented even if listed in `prompts_11/079_*` etc.; it requires explicit register-first + scope approval.
- **reason:** Auto-implementation of roadmap items leads to unverifiable modules; per 4.md §1, register-first is the foundation.
- **source:** `core_02/LESSONS.md` (CAN-16 row); cited in `prompts/4.md` §18 ("Не переписывай платформу").
- **affected_entities:** `@entity workspace.core` (governance), `@entity forge.cli` (chain dispatch)
- **status:** LESSON
- **supersedes:** — (no prior; counter-rules the auto-ship-via-roadmap habit)
- **implementation_status:** IMPLEMENTED (registry-first principle codified in `AGENTS.md` §5; `missing_registry.py` cycle enforced)

#### @lesson CAN-017 — Buffy ≡ Freebuff synonymy

- **decision_id:** CAN-017
- **statement:** "Buffy" and "Freebuff" are SYNONYMS in all current docs; do not create two parallel namespaces.
- **reason:** Avoid duplicate CAN-17 ANTI-pattern (files referencing both names redundantly).
- **source:** `core_02/LESSONS.md` (CAN-17 row); clarified in `BUFFY.md` v5.59.0 (2026-08-04).
- **affected_entities:** `@entity workspace.core` (manifest anchor)
- **status:** LESSON
- **supersedes:** — (no prior)
- **implementation_status:** IMPLEMENTED (BUFFY.md, AGENTS.md, BUFFY_PROJECT.md all adopt synonymy)

#### @lesson R-001 — Aggressive self-healing breaks Termux

- **decision_id:** R-001
- **statement:** Aggressive self-healing (automatic `rm -rf`, `pkill -f self-match`, force-restart) breaks Termux environment and abandons state.
- **reason:** Promotes destruction over recovery; conflicts with ADR-009 User-Choice Override.
- **source:** `core_02/LESSONS.md` (R-001 row); origin: v5.187.0 ops lessons (CHANGELOG JSONDecodeError fallout).
- **affected_entities:** `@entity workspace.core`, `@entity forge.cli`
- **status:** LESSON
- **supersedes:** — (no prior)
- **implementation_status:** IMPLEMENTED (`pkill -f` self-match workaround with bracket-trick `forge_ap[i***REMOVED***.py`)

#### @lesson R-011 — Lazy imports break mypy on stub chain

- **decision_id:** R-011
- **statement:** Lazy module-level imports (e.g., `from forge_facade import ForgeFacade` inside `opportunity_engine.py::execute`) leave mypy with 17 placeholder signature errors when stub chain isn't type-annotated.
- **reason:** mypy cannot infer types across lazy imports → silent signature drift.
- **source:** `core_02/LESSONS.md` (R-011 row); cited in `PLATFORM_CODE_MAP_V1.md` §A.7 row #4.
- **affected_entities:** `@entity opportunity.engine`, `@entity forge.facade` (consumed via lazy)
- **status:** LESSON
- **supersedes:** — (no prior)
- **implementation_status:** PARTIAL (flagged in §C.6 of `CONTRACT_REGISTRY_V1.md`; target P1.4 to annotate `ForgeFacade.run_chain` and refactor lazy import)

---

## §D.3 — Supersedes chain (visual)

```
ADR-010 (Phase 5.3 Relay)
        │
        ▼ (supersedes)
ADR-011 (Phase 5.3-D Realtime Listener)
```

```
(CON-NN / ANTI-NN / CAN-NN / R-NN)
ANTI-6 ─── evolves to ───▶ ANTI-6b (closed-vocabulary rule)
```

```
Vision 2.0 (archive) ─── superseded by ───▶ ADR-007 (Vision 3.0)
```

No other supersedes-chains verified in first slice. Phase 1.5 expansion should query all `docs_10/engineering-memory/decisions/*.md` for "supersedes" mentions and populate §D.3.

---

## §D.4 — First-slice totals

| Status                  | Count | %     | Examples                                                      |
|-------------------------|------:|------:|---------------------------------------------------------------|
| ACCEPTED                | 13    | 59.1% | ADR-007 (Vision), ADR-001 (Model Gateway), ADR-002 (MCP Pure Py), ADR-003 (HTTP Transport), ADR-004 (FastAPI/CF), ADR-005 (CTX Bridge), ADR-006 (Lightpanda), ADR-008 (promt36), ADR-009 (promt37), ADR-011 (Listener), ADR-012 (Swappable Brain), ADR-013 (ForgeFacade), ADR-014 (Lead Aggregator) |
| SUPERSEDED              | 1     | 4.5%  | ADR-010 (superseded by ADR-011)                                |
| LESSON                  | 8     | 36.4% | CON-17, CON-52, ANTI-7, ANTI-6b, CAN-16, CAN-17, R-001, R-011 |
| PROPOSED                | 0     | 0.0%  | —                                                             |
| DEPRECATED              | 0     | 0.0%  | —                                                             |
| **Total**               | **22**| **100%** | 14 ADRs + 8 lessons; all backed by file source.             |

**Implementation-status cross-cut:**

| Implementation          | Count | %     | Examples                                              |
|-------------------------|------:|------:|-------------------------------------------------------|
| IMPLEMENTED             | 20    | 90.9% | ADR-007, ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-008, ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, CON-017, CON-052, ANTI-007, ANTI-06b, CAN-016, CAN-017, R-001 |
| PARTIAL                 | 2     | 9.1%  | ADR-006 (Lightpanda), R-011 (mypy lazy chain)         |
| NOT_IMPLEMENTED         | 0     | 0.0%  | —                                                     |
| VERIFIED                | 0     | 0.0%  | —                                                     |

*Note (M3 fix): UNVERIFIED was previously listed as a 5th implementation-status category but is NOT in §11 spec. The spec allows only 4 statuses: NOT_IMPLEMENTED / PARTIAL / IMPLEMENTED / VERIFIED. All 22 records have either real implementations (20) or partial implementations (2), so NOT_IMPLEMENTED=0 AND VERIFIED=0. The earlier UNVERIFIED row was a fabrication artifact (M3) replaced by the canonical 4-status taxonomy.*

---

## §D.5 — Cross-references (downstream consumers)

- **Artifact E** `TRACEABILITY_GRAPH_V1` — uses `decision_id` as graph node, with `supersedes` as graph edge type; CON/ANTI/CAN/R lessons map to graph rule-nodes (constraints, invariants).
- **Artifact F** `AGENT_NAVIGATION_MAP_V1` — uses `decision_id` as "WHY is X done this way?" answer per §12/§13 navigation; lessons (@lesson CON_017, ANTI-006b) provide constraint context.
- **Artifact G** `ARCHITECTURE_GAP_MAP_V1` — flags PARTIAL implementation-status records (R-011, ADR-006 etc.) as known-but-resolvable gaps.
- **Artifact H** `DOCUMENTATION_CONSISTENCY_REPORT_V1` — validates that every @decision/@lesson cited in artifacts A/B/C has a corresponding record here; flags orphan citations.

**Side effects on repository (anticipated):**
- None now (read-only artifact).
- Future: `core_02/decision_registry.py` may be scaffolded (analogous to `core_02/missing_registry.py`) to provide runtime checks for ADR/Lesson consistency per @decision anchor resolution (Artifact I §I.3).

**Proposed extension to Artifact I namespaces (§I.5 candidate):** *(resolved via §I.1 rows 16–19; §I.5 still describes status mapping only)*
- `@lesson X` (lowercase.dot or underscore, four subtypes: CON, ANTI, CAN, R) — parallel to `@decision`.

**✅ APPLIED (Phase 1.5, 2026-08-12):** Per `SEMANTIC_ANCHOR_SPEC_V1.md` §I.1 rows 16–19 + §I.2 regex + §I.3 ANCHOR_RE pseudocode. Counter to what this proposal claimed ("does NOT require Artifact I namespace update since they share the lowercase.dot format"), the lesson-vs-decision semantic distinction was strong enough to warrant a first-class 4-subtype `@lesson` namespace rather than reusing `@decision`. Artifact I extended 15 → 19 namespaces; `@lesson` resolves via static grep of `core_02/LESSONS.md` (~126 lessons across CON:80, ANTI:12, CAN:34, R:0); consumer Artifact E (`TRACEABILITY_GRAPH_V1`) gains lesson-as-constraint-nodes with edge mappings `CON→USES`, `ANTI→CONTRADICTS`, `CAN→allowed/denied`, `R→hard rule`.

---

## §D.6 — Drift findings (open items)

1. **ADR-NNN file numbering inconsistency:** `ADR_007_Vision_3.0_...md` follows filename convention `ADR_NNN_<topic>.md`, but several files have number mismatches with their title (e.g., `ADR_002_Model_Gateway.md` is the same decision as ADR-001; `ADR_003_MCP_Server_Pure_Python.md` is the same as ADR-002). Per §0 REPOSITORY = SOURCE OF TRUTH, **filenames are authoritative**, but the canonical ADR-NNN id per `PLATFORM_CODE_MAP_V1.md` (ADR-009, ADR-010, ADR-011, ADR-012) is the durable public id. **Target:** ADR-013+ use canonical ADR-NNN; pre-013 records carry `filename_nbr` `=>` `canonical_id` mapping in §D.7.
2. **Affected_entities gap:** for ADRs ADR-001 through ADR-007, affected_entities are inferred from context, not explicitly cited in source files. **Target:** Phase E (TRACEABILITY_GRAPH) extracts from PLATFORM_CODE_MAP cross-references or annotates ADR body with @entity refs.
3. **§D.3 supersedes chain incomplete:** Vision 3.0 (ADR-007) supersedes Vision 2.0 archive, but no other supersedes chain was deterministically derived. **Target:** Phase E + Phase 1.5 expansion.
4. **Phase 1.5 AnchorsIndex update:** `@lesson CON_NNN` is NOT in `SEMANTIC_ANCHOR_SPEC_V1.md` §I.1. The 15-namespace taxonomy lacks lessons. **Target:** add 4 lesson subtypes to Artifact I §I.1 in Phase 1.5 refresh.

---

## §D.7 — Filename → canonical-id reconciliation table

| Filename                                          | Title per BODY H1              | Canonical ADR-NNN        | Conflict? |
|---------------------------------------------------|--------------------------------|--------------------------|-----------|
| `ADR_007_Vision_3.0_AI_Infrastructure_Layer.md`   | Vision 3.0                      | ADR-007 (matches file)    | ✓ no |
| `ADR_002_Model_Gateway.md`                         | Model Gateway                   | ADR-001 (PLATFORM_CODE_MAP)| ⚠ mismatch (file says 002; canonical 001) |
| `ADR_003_MCP_Server_Pure_Python.md`                | MCP Server Pure Python          | ADR-002                    | ⚠ |
| `ADR_004_MCP_HTTP_Transport.md`                    | MCP HTTP Transport              | ADR-003                    | ⚠ |
| `ADR_005_FastAPI_Cloudflare.md`                    | FastAPI + Cloudflare            | ADR-004                    | ⚠ |
| `ADR_006_ContextManager_Bridge.md`                 | ContextManager Bridge           | ADR-005                    | ⚠ |
| `ADR_007_Lightpanda.md`                            | Lightpanda                      | ADR-006                    | ⚠ |
| `ADR_008_Consolidation_Promt36_Canonical_Rules.md` | Canonical Rules (promt36)       | ADR-008 (matches file)     | ✓ no |
| `ADR_009_Consolidation_Promt37_User_Choice_Override.md` | User-Choice Override (promt37) | ADR-009 (matches file) | ✓ no |
| `ADR_010_Remote_Sync_Telegram_Relay.md`            | Phase 5.3 Remote Sync (Relay)   | ADR-010 (matches file)    | ✓ no |
| `ADR_011_Phase_5_3_D_Listener_Loop.md`             | Phase 5.3-D Listener Loop       | ADR-011 (matches file)    | ✓ no |
| `ADR_012_buffy_swappable_brain.md`                 | Buffy-as-Swappable-Brain        | ADR-012                    | ✓ no |
| `ADR_013_Forge_Facade_Blueprint_v3_Bridge.md`      | ForgeFacade Bridge              | ADR-013                    | ✓ no |
| `ADR_014_Lead_Aggregator_Attract_Module.md`        | Attract-Module                  | ADR-014                    | ✓ no |

**Resolution:** Keep filenames unchanged (§0 REPOSITORY = SOURCE OF TRUTH); canonical ADR-NNN id per `PLATFORM_CODE_MAP_V1.md` references take precedence in @decision anchors (e.g., ADR-009 = Workspace L-2 boundary, NOT just ADR-009 file = User-Choice Override). The conflict is cosmetic — both refer to the same decision — and is harmless because both names point to the same source-of-truth file body.

**Registry strategy:** the §D.1 records use **canonical ADR-NNN** (per PLATFORM_CODE_MAP references) as @decision anchors. Filename is in the `source` field for traceability. Phase 1.5: rename files to match canonical ids — but this is a CHANGELOG-tracked convention change, not an FFB-source-of-truth change.

**Filename-inferred canonical IDs (m1 fix):** Rows for ADR-001..006 (where filename `ADR_002_Model_Gateway.md` etc. diverges from `PLATFORM_CODE_MAP_V1.md`'s canonical references) carry the marker `(inferred by file-name ordering — confirm P1.5)` for downstream agents. PLATFORM_CODE_MAP only authoritatively references ADR-009, ADR-010, ADR-011, ADR-012 as public, durable ids. ADR-001..006 + ADR-007/008/013/014 are file-order projections — until source-of-truth canonical assignment is confirmed, downstream consumers SHOULD treat the §D.7 canonical column for these rows as `(inferred)`.

**ADR-007 filename collision (M1 fix):** Two distinct decisions share an `ADR_007_` filename prefix:
- `ADR_007_Vision_3.0_AI_Infrastructure_Layer.md` → canonical `@decision ADR-007` (Vision 3.0)
- `ADR_007_Lightpanda.md` → canonical `@decision ADR-006` (Lightpanda)

This is a filename-numeric coincidence, NOT a §D.1 numbering duplication. §D.1 records consistently assign **Decision content → Canonical ADR-NNN** (Vision → 007, Lightpanda → 006). Resolution path: Phase 1.5 rename `ADR_007_Lightpanda.md` → `ADR_006_Lightpanda.md`. Until then, the @decision anchors are canonical (ADR-007 = Vision, ADR-006 = Lightpanda) and filenames are cosmetic.

---

## §D.8 — Provenance (verification checklist per `prompts/4.md` §21)

- [x***REMOVED*** Each major architectural decision has a source file path.
- [x***REMOVED*** Each ADR's `statement` is paraphrased from source file (not invented).
- [x***REMOVED*** Each ADR's `affected_entities` are explicit when source body references @entity by name; otherwise marked `(inferred, see source P1.5)`.
- [x***REMOVED*** Status taxonomy (PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED | LESSON) used consistently.
- [x***REMOVED*** Implementation-status taxonomy (NOT_IMPLEMENTED | PARTIAL | IMPLEMENTED | VERIFIED) used consistently.
- [x***REMOVED*** 14 ADRs documented; 8 lessons documented; total 22 records.
- [x***REMOVED*** 19/22 records marked IMPLEMENTED, 2 PARTIAL, 0 NOT_IMPLEMENTED — matches CHANGELOG reality of v5.187.x Workspace OS release.
- [x***REMOVED*** §D.7 filename-vs-canonical-id reconciliation table addresses ADR-numbering drift honestly (§D.6 finding #1).
- [x***REMOVED*** No graph relationships invented — §D.3 supersedes-chain visual derived only from explicit ADR body refs.

---

_Phase D closed per Phase plan v0.1 §D. Implementation: 2026-08-12. 22 records (14 ADRs + 8 lessons), 13 ACCEPTED + 1 SUPERSEDED + 8 LESSON = 22 ✓; 20 IMPLEMENTED + 2 PARTIAL = 22 ✓ (per §11 4-status taxonomy). Next: Phase E → Artifact E (`TRACEABILITY_GRAPH_V1`)._
