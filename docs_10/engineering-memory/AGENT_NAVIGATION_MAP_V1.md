# AGENT_NAVIGATION_MAP_V1.md (Artifact F) — Layer 3 Navigation for AI-Agents

> **Статус:** v1.0 FIRST SLICE — read-only canonical architecture artifact.
> **Дата:** 2026-08-12 (workspace freeze between Phase E close → Phase F open).
> **Spec source:** `projects_17/content_factory/prompts/4.md` §12 + §13 (verbatim, see §F.2 below).
> **Role:** answers the question **"How do I run X?"** for AI agents operating on Workspace OS.
> **Composition:** Layer 1 (Structured) + Layer 2 (Vector) + Layer 3 (Graph — consumes Artifact E `TRACEABILITY_GRAPH_V1.md` query API).
> **Upstream truth sources:** Artifact A `PLATFORM_CODE_MAP_V1.md` (25 @entities), Artifact C `CONTRACT_REGISTRY_V1.md` (14 @contracts), Artifact D `ARCHITECTURE_DECISION_REGISTRY_V1.md` (22 records), Artifact E `TRACEABILITY_GRAPH_V1.md` (60 nodes + 85 edges + 19 relation-types).
> **Downstream consumer:** Phase G → Artifact G (`AGENT_PROMPT_TEMPLATES_V1.md`) will resolve CAPABILITY names into reusable prompt templates; Phase H → Artifact H (`RUNTIME_REPRODUCTION_GUIDE_V1.md`) will record execution traces for these capabilities.

---

## §F.1 — Scope: First-Slice = 10 Anchored Capabilities

**Selection rule:** capabilities MUST satisfy three conditions:
1. **Have a stable CLI entrypoint** in `scripts_01/` or `core_02/` (per Artifact A row coverage).
2. **Cross at least 2 relationships** in Artifact E (single-relationship nodes are not navigation-worthy, by §E.0 scoping).
3. **Have at least one test anchor** in `tests_09/` (per Artifact E's VALIDATED_BY edges; navigation without test surface is unsafe per `core_02/LESSONS.md` ANTI-3 "untested nav = hallucination").

### §F.1.1 — Anchored capability set (10)

| # | Capability slug | Canonical @entity | CLI entrypoint | Test surface |
|---|---|---|---|---|
| 1 | `forge.execution` | `@entity forge.facade` | `python scripts_01/forge.py chain <slug>` | `@test test_run_chain`, `@test test_forge_chain_cli` |
| 2 | `opportunity.discovery` | `@entity opportunity.engine` | `python scripts_01/opportunity_engine.py discover` | (vertical slice — pending Phase 1 implementation per `pompts_11/079_19_factory_registry.md` content) |
| 3 | `whim.capture` | `@entity whim_capture` | `python scripts_01/whim_capture.py capture <text>` | (vertical slice — pending) |
| 4 | `consistency.audit` | `@entity consistency.check` | `python -m scripts_01.consistency_check --workspace .` | `@test test_consistency_check` |
| 5 | `project.registration` | `@entity forge.registry` | `python -m core_02.forge_registry register <name> <root>` | `@test test_forge_registry` |
| 6 | `memory.search` | `@entity memory.store` (+ `@entity semantic.layer`) | `python -m core_02.memory_store search "<query>"` | `@test test_memory_store`, `@test test_semantic_layer` |
| 7 | `scenario.resolution` | `@entity scenario.registry` | `python -m core_02.scenario_registry list` | `@test test_scenario_registry` |
| 8 | `learning.feedback` | `@entity learning.loop` | `python -m core_02.learning_loop record <event>` | `@test test_learning_loop` |
| 9 | `remote.sync` | `@entity remote.sync` | `python -m core_02.remote_sync status` | `@test test_remote_sync`, `@test test_e2e_remote_sync` |
| 10 | `event.publishing` | `@entity event.bus` | (programmatic: `bus.publish(Event(...))`) | `@test test_event_bus` (via notify/event coverage in `test_telegram_bot_notify`) |

### §F.1.2 — Deferred capabilities (Phase 1.5 expansion candidates)

Per §A.9 dependency order, NOT in first slice (close in Phase 1.5+):
- `factory.composition` — requires Phase 1.5 `factory.registry` implementation (`pompts_11/078_19_factory_registry.md`).
- `forge.design_review` — `@entity blueprint.v3` exists in Artifact A but stable CLI not yet landed (`core_02/blueprint_v3.py` is module-level, no argparse).
- `learning.transfer` — cross-project memory transfer; design §38 RESERVED.
- `agent.distribution` — `@entity distributed.agents` exists; mint as CAP-11 only after Phase 1.5 closes vertical-slice CI.
- `artifact.validation` — overlaps with `consistency.audit`; deferred until §F.7 cross-reference topology §C is non-circular.

---

## §F.2 — §12 + §13 Spec Mapping (verbatim cite)

### §F.2.1 — §F.4 follows §12 verbatim chain

§12 of `prompts/4.md` (verbatim):
> **§12.** Для каждой capability определи:
> CAPABILITY → ENTRYPOINT → SCRIPT / FUNCTION → INPUT → OUTPUT → SIDE EFFECTS → RELATED CONTRACTS → RELATED DOCUMENTATION

Each capability card in §F.4 below uses **exact field labels** in this order. No synonyms (closed-vocabulary invariant per `core_02/LESSONS.md` ANTI-6b).

### §F.2.2 — §F.4 AGENT-RETURNS block follows §13 verbatim list

§13 of `prompts/4.md` (verbatim):
> **§13.** Для каждого запроса вида "Как выполнить X?" агент должен получать:
> 1. canonical entity; 2. implementation; 3. entrypoint; 4. contract; 5. dependencies;
> 6. tests; 7. documentation; 8. related events; 9. storage; 10. known limitations.

Each capability card §F.4.Conclusion includes a 10-row AGENT-RETURNS block in §13 ordering (numeric-keyed for LLM regex extraction).

### §F.2.3 — Cardinality invariants (closed-set)

| Field | Cardinality | Source of truth |
|---|---|---|
| Canonical entity | exactly 1 @entity | Artifact A (PLATFORM_CODE_MAP_V1 §A.1 row N) |
| Implementation | exactly 1 @module path | Artifact A (field `module_path`) |
| Entrypoint | exactly 1 CLI command OR API route | grep `add_parser` / `FastAPI` route in Artifact A |
| Input | 0..N args (positional + flag list) | extract from `argparse` definitions |
| Output | exactly 1 payload description | extract from function return |
| Side Effects | 0..N @event publishes | grep `bus.publish` calls |
| Related Contracts | 1..N @contract refs | Artifact C §C.4 |
| Related Documentation | 1..N `doc.<shortname>#section` refs | Artifact B (DOCUMENTATION_CODE_MAP §B) |

If a field cannot be grounded in Artifact A/C/E evidence, the capability is **NOT navigation-worthy** and goes to §F.1.2 Deferred.

---

## §F.3 — 3-Layer Architecture Integration (Layer 1 / 2 / 3)

§14 of `prompts/4.md` requires:
> **Layer 1 STRUCTURED INDEX** — exact @entity/@contract anchors.
> **Layer 2 VECTOR INDEX** — semantic content over `docs_10/engineering-memory/` and `prompts/11/`.
> **Layer 3 GRAPH** — explicit relations via Artifact E.

This artifact **IS** Layer 1's primary payload (the canonical navigation index). It is **NOT** Layer 2 (that is `data_13/embeddings.parquet` or equivalent — separate artifact in Phase 2). It IS the **dispatcher** for Layer 3 (each capability card tells the agent which Artifact E query method to call for relational context).

### §F.3.1 — Layer 1 (this artifact)

Each §F.4 entry is a **deterministic anchor block**: the same CAPABILITY slug always resolves to the same @entity, same module path, same CLI command. No fuzzy matching at L1; pure regex extraction per §F.6 vocabulary.

### §F.3.2 — Layer 2 dispatch contract (downstream)

A future Layer-2 vector retriever (Phase 2, not in this slice) MUST:
- Index field-prose text (not raw anchors) to enable intent matching ("how do I run a chain" → "forge.execution").
- Return the **CAPABILITY slug** as primary key.
- Use §F.4 cards as ground-truth labels for vector-store validation.

### §F.3.3 — Layer 3 dispatch contract (Artifact E consumption)

Each capability card specifies which **Artifact E query method** to call for relational context:

| Query intent | Artifact E method | Returns |
|---|---|---|
| "What calls this?" | `neighbors(@entity, via_rel='CALLS')` | upstream callers |
| "What does this extend?" | `shortest_path(@entity, @entity_extension_root)` | inheritance chain |
| "What enforces this?" | `enforces(@entity)` | @lesson CON/R nodes |
| "What does this contradict?" | `contradictions(@entity)` | @lesson ANTI nodes |
| "What tests cover this?" | `neighbors(@entity, via_rel='VALIDATED_BY')` | @test list |
| "What emitted events flow here?" | `neighbors(@entity, via_rel='CONSUMES')` | @event list |

**Phase 1 discipline:** Layer 3 is OPTIONAL during navigation; if Artifact E is unavailable, the agent must return the §13 AGENT-RETURNS block standalone with `LIMITATION: graph layer unresolved` appended. Never block navigation behind Layer 3 (per `core_02/LESSONS.md` ANTI-4 "graph not required for basic nav").

---

## §F.4 — 10 Capability Cards (FIRST SLICE)

> Each card is structured for LLM parsing: bold field labels in `§12` order, then AGENT-RETURNS block in `§13` order. All anchors resolvable via `grep` against Artifacts A/C/E.

### ⚡ CAP-1: forge.execution

- **Canonical Entity:** `@entity forge.facade`
- **Implementation:** `core_02/forge_facade.py::class ForgeFacade::run_chain`
- **Entrypoint:** `python scripts_01/forge.py chain <project_slug> [--mode {forge|smoke|full***REMOVED******REMOVED*** [--resume***REMOVED*** [--json***REMOVED***`
- **Input:** `--project_slug` (positional, required); `--mode` (default `forge`); `--resume` (flag, picks up after last record); `--json` (flag, JSON-only output)
- **Output:** 9-key JSON chain payload: `{slug, mode, started_at, finished_at, stages[***REMOVED***, record_path, status, summary, evidence[***REMOVED******REMOVED***`
- **Side Effects:** EMITS `@event forge.chain_started` (1×, at start); `@event forge.stage_completed` (1× per stage); `@event forge.chain_completed` (1×, success) OR `@event forge.chain_failed` (1×, failure). STORES record to `data_13/forge_runs/<slug>/<timestamp>.yaml` (atomic-write per `core_02/tmp_atomic_write.py`).
- **Related Contracts:** `@contract forge.execution` (C.4 #1), `@contract forge.lifecycle` (C.4 #2), `@contract forge.run.record` (C.4 #3)
- **Related Documentation:** `doc.factory_forge_arch#4.c1` (Forge v1.1 §4 Lifecycle), `doc.arch_canon#3.c1` (CORE_PROMPT §3 Responsibilities), `doc.changelog#5.187.0.c1` (forge bridge CHANGELOG)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity forge.facade`
2. Implementation: `core_02/forge_facade.py::ForgeFacade.run_chain`
3. Entrypoint: `python scripts_01/forge.py chain <project_slug>`
4. Contract: `@contract forge.execution`
5. Dependencies: `@entity scenario.registry`, `@entity forge.registry`, `@entity memory.store`, `@entity blueprint.v3`
6. Tests: `@test test_run_chain`, `@test test_forge_chain_cli`, `@test test_forge_chain_real_integration`, `@test test_forge_facade`
7. Documentation: `doc.factory_forge_arch#4.c1`, `doc.arch_canon#3.c1`, `doc.changelog#5.187.0.c1`
8. Related Events: `@event forge.chain_started`, `@event forge.stage_completed`, `@event forge.chain_completed`, `@event forge.chain_failed`
9. Storage: `@storage data_13/forge_runs/<slug>/` (atomic-write enforced per `@lesson CON-052`)
10. Known Limitations: `@lesson CON-052` (atomic write mandatory), `@lesson ANTI-06b` (vocabulary: `--mode` must be in KNOWN_MODES set)

---

### ⚡ CAP-2: opportunity.discovery

- **Canonical Entity:** `@entity opportunity.engine`
- **Implementation:** `scripts_01/opportunity_engine.py::OpportunityStore::discover_candidates` *(Phase 1 ✅ implemented 2026-08-12, see CHANGELOG)*
- **Entrypoint:** `python scripts_01/opportunity_engine.py discover --project-id <slug> [--max 10***REMOVED*** [--json***REMOVED***`
- **Input:** `--threshold` (float, default 0.5); `--max-active` (int, default 50)
- **Output:** JSON list of opportunities: `[{opportunity_id, source_signal, score, lifecycle: {ACTIVE|DEFERRED|READY|REACTIVATED***REMOVED***, promote_hint***REMOVED******REMOVED***`
- **Side Effects:** EMITS `@event opportunity.discovered` (1× per detected signal); EMITS `@event opportunity.lifecycle_changed` (on ACTIVE→READY transitions). STORES to `data_13/opportunities.yaml` (YAML-backed registry, per `pompts_11/079_19_factory_registry.md`).
- **Related Contracts:** `@contract opportunity.discover` (C.4 #11), `@contract opportunity.execute` (C.4 #12)
- **Related Documentation:** `doc.factory_forge_arch#17.1.c1` (Research Factory §17.1), `doc.forensics_ci_report#I.c1` (Forensics §I G3-1), `doc.missing_registry#lisa_estimator.c1` (Missing Capability lifecycle analog)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity opportunity.engine`
2. Implementation: `scripts_01/opportunity_engine.py::OpportunityEngine::discover`
3. Entrypoint: `python scripts_01/opportunity_engine.py discover`
4. Contract: `@contract opportunity.discover`
5. Dependencies: `@entity project.pulse`, `@entity event.bus`, `@entity knowledge.engine`, `@entity scenario.registry` (PROPOSE), `@entity forge.facade` (EXECUTE — via `run_chain`)
6. Tests: (pending Phase 1 vertical slice per `pompts_11/079_19_factory_registry.md`)
7. Documentation: `doc.factory_forge_arch#17.1.c1`, `doc.forensics_ci_report#I.c1`, `doc.missing_registry#opportunity_engine.c1`
8. Related Events: `@event opportunity.discovered`, `@event opportunity.lifecycle_changed`
9. Storage: `@storage data_13/opportunities.yaml`
10. Known Limitations: `@lesson CON-052` (atomic write to YAML), `@lesson R-001` (lifecycle state machine inverse-mapping closed-set), `@lesson CAN-016` (additive only — never modify existing opportunity rows in-place)

---

### ⚡ CAP-3: whim.capture

- **Canonical Entity:** `@entity whim_capture`
- **Implementation:** `scripts_01/whim_capture.py::WhimStore::capture` *(Phase 1.2 ✅ implemented 2026-08-12, see CHANGELOG)*
- **Entrypoint:** `python scripts_01/whim_capture.py capture "<text>" [--tag <tag>***REMOVED*** [--source {cli|tg|web***REMOVED******REMOVED***`
- **Input:** `--text` (positional, required, ≤280 chars per design); `--tag` (single tag); `--source` (default `cli`)
- **Output:** JSON: `{whim_id, captured_at, text, tag, source, lifecycle: PENDING***REMOVED***`
- **Side Effects:** EMITS `@event whim.captured`. STORES to `data_13/whims.yaml`. Promotes via `whim_capture.promote(whim_id, project_slug)` — successful promotion EMITS `@event whim.promoted` and feeds into `@entity opportunity.engine`.
- **Related Contracts:** `@contract whim.promote` (C.4 #13)
- **Related Documentation:** `doc.factory_forge_arch#17.2.c1` (Research Factory §17.2), `doc.forensics_ci_report#I.c2` (Forensics §I G3-2), `doc.missing_registry#whim_capture.c1`

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity whim_capture`
2. Implementation: `scripts_01/whim_capture.py::WhimCapture::capture`
3. Entrypoint: `python scripts_01/whim_capture.py capture "<text>"`
4. Contract: `@contract whim.promote`
5. Dependencies: `@entity opportunity.engine` (downstream consumer), `@entity event.bus`
6. Tests: (pending Phase 1 vertical slice)
7. Documentation: `doc.factory_forge_arch#17.2.c1`, `doc.forensics_ci_report#I.c2`, `doc.missing_registry#whim_capture.c1`
8. Related Events: `@event whim.captured`, `@event whim.promoted`
9. Storage: `@storage data_13/whims.yaml`
10. Known Limitations: `@lesson CON-017` (no shell injection in text capture), `@lesson R-001` (lifecycle state: PENDING → PROMOTED → MERGED → ARCHIVED)

---

### ⚡ CAP-4: consistency.audit

- **Canonical Entity:** `@entity consistency.check`
- **Implementation:** `scripts_01/consistency_check.py::class ConsistencyCheck::run` (entry: `python -m scripts_01.consistency_check`)
- **Entrypoint:** `python -m scripts_01.consistency_check --workspace . [--json***REMOVED*** [--strict***REMOVED***`
- **Input:** `--workspace` (path, default `.`); `--json` (flag); `--strict` (treat WARN as FAIL)
- **Output:** JSON: `{total_issues, consistent: bool, issues: [{level: ERROR|WARN, source: str, path: str, hint: str***REMOVED******REMOVED******REMOVED***`
- **Side Effects:** READ-ONLY (no EMIT, no STORE). Cross-validates: missing_registry sync (§20 map ↔ `data_13/missing_registry.yaml`); document_registry (§Artifact B); ADR slot coverage.
- **Related Contracts:** (this artifact IS the contract — see §F.4 cross-ref to `@contract workspace.path_resolve`)
- **Related Documentation:** `doc.consistency_check_design.c1` (in-script docstring §1), `doc.architecture_manifest#1.c1`, `doc.drift_report#main` (cross-validation target)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity consistency.check`
2. Implementation: `scripts_01/consistency_check.py::class ConsistencyCheck`
3. Entrypoint: `python -m scripts_01.consistency_check --workspace .`
4. Contract: `@contract workspace.path_resolve` (consumes)
5. Dependencies: `@entity forge.registry` (validates), `@entity scenario.registry` (validates), `@entity missing.registry` (validates)
6. Tests: `@test test_consistency_check`, `@test test_drift_check`
7. Documentation: `doc.architecture_manifest#1.c1`, `doc.drift_report#main`
8. Related Events: (none — read-only audit)
9. Storage: (none — read-only)
10. Known Limitations: `@lesson CON-017` (path traversal guard on `--workspace`), `@lesson ANTI-5` (consistency-check IS NOT a CI replacement — must be paired with `tests_09/` pytest run)

---

### ⚡ CAP-5: project.registration

- **Canonical Entity:** `@entity forge.registry`
- **Implementation:** `core_02/forge_registry.py::class ForgeRegistry::register_project`
- **Entrypoint:** `python -m core_02.forge_registry register <project_id> <root_path>`
- **Input:** `--project_id` (slug, validated `^[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***$`); `--root_path` (must exist, must be under `projects_17/`); optional `--description`
- **Output:** YAML row appended to `data_13/forge_registry.yaml`; stdout confirmation with row summary.
- **Side Effects:** EMITS `@event forge.project_registered`. Atomically creates `projects_17/<project_id>/` skeleton (README, SPEC.md stub, `manifests/` empty dir).
- **Related Contracts:** `@contract workspace.path_resolve` (C.4 #6)
- **Related Documentation:** `doc.forge_v17_audit#main`, `doc.factory_forge_arch#6.c1` (Forge Registry §6), `doc.changelog#5.187.0.c1`

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity forge.registry`
2. Implementation: `core_02/forge_registry.py::ForgeRegistry::register_project`
3. Entrypoint: `python -m core_02.forge_registry register <id> <root>`
4. Contract: `@contract workspace.path_resolve`
5. Dependencies: `@entity forge.facade` (downstream consumer), `@entity event.bus`
6. Tests: `@test test_forge_registry`, `@test test_v0_1_slice` (covers edge cases), `@test test_lead_aggregator_core` (consumers)
7. Documentation: `doc.forge_v17_audit#main`, `doc.factory_forge_arch#6.c1`
8. Related Events: `@event forge.project_registered`
9. Storage: `@storage data_13/forge_registry.yaml` (atomic write per `core_02/tmp_atomic_write.py`)
10. Known Limitations: `@lesson CON-017` (slug validation, no shell), `@lesson CON-052` (atomic write), `@lesson CAN-016` (additive — never clobber existing rows)

---

### ⚡ CAP-6: memory.search

- **Canonical Entity:** `@entity memory.store` (+ `@entity semantic.layer` co-anchor for vector layer)
- **Implementation:** `core_02/memory_store.py::class MemoryStore::search` (calls `core_02/semantic_layer.py::SemanticLayer::encode`)
- **Entrypoint:** `python -m core_02.memory_store search "<query>" [--top-k 5***REMOVED*** [--mode {lexical|semantic|hybrid***REMOVED******REMOVED***`
- **Input:** `--query` (positional, required); `--top-k` (int, default 5); `--mode` (default `hybrid`)
- **Output:** JSON: `[{doc_id, title, snippet, score, source_module***REMOVED******REMOVED***`
- **Side Effects:** READ-ONLY (no EMIT). Optionally updates an in-process cache (`@entity memory.store` LRU).
- **Related Contracts:** `@contract memory.search` (C.4 #8), `@contract memory.write` (C.4 #7) for write-side companion
- **Related Documentation:** `doc.factory_forge_arch#15.c1` (Memory Engine §15), `doc.memory_engine_design#main`, `doc.changelog#5.23.0.c1` (RAG 2.0)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity memory.store`
2. Implementation: `core_02/memory_store.py::MemoryStore::search`
3. Entrypoint: `python -m core_02.memory_store search "<query>"`
4. Contract: `@contract memory.search`
5. Dependencies: `@entity semantic.layer`, `@entity knowledge.engine`, `@entity graph.index`
6. Tests: `@test test_memory_store`, `@test test_semantic_layer`, `@test test_rag_engine`
7. Documentation: `doc.factory_forge_arch#15.c1`, `doc.memory_engine_design#main`
8. Related Events: (none — read-only; publishes ONLY via `@entity learning.loop` if results are used for new runs)
9. Storage: `@storage data_13/memory_index_sqlite` (per Artifact E §E.7 cross-artifact provenance; derived from Contract C §C.4 #7)
10. Known Limitations: `@lesson CON-052` (atomic refresh on index rebuild), `@lesson ANTI-3` (search without test coverage = hallucination risk; tests MUST be regenerated per index bump), `@lesson R-001` (`--mode` closed-set: `lexical|semantic|hybrid`)

---

### ⚡ CAP-7: scenario.resolution

- **Canonical Entity:** `@entity scenario.registry`
- **Implementation:** `core_02/scenario_registry.py::class ScenarioRegistry::find_role` (with `list_scenarios` for discovery)
- **Entrypoint:** `python -m core_02.scenario_registry list [--vertical <name>***REMOVED***` OR `find <slug>`
- **Input:** `list [--vertical content|architecture|research***REMOVED***`; `find <scenario_slug>`
- **Output:** JSON: `[{slug, name, vertical, roles: [{role_id, blueprint_step, weight***REMOVED******REMOVED******REMOVED******REMOVED***`
- **Side Effects:** READ-ONLY. Cross-references `runtime_05/scenarios/*.yaml` manifests.
- **Related Contracts:** `@contract scenario.composition` (C.4 #4), `@contract scenario.selection` (C.4 #5)
- **Related Documentation:** `doc.scenario_engine_design#13.2.c1`, `doc.role_forge_matrix#main`, `doc.factory_forge_arch#7.3.c1` (Wizard↔Forge orthogonal STATE)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity scenario.registry`
2. Implementation: `core_02/scenario_registry.py::ScenarioRegistry::find_role`
3. Entrypoint: `python -m core_02.scenario_registry list`
4. Contract: `@contract scenario.composition`
5. Dependencies: `@entity forge.facade` (consumes in chain), `@entity blueprint.v3` (role definitions)
6. Tests: `@test test_scenario_registry`, `@test test_wizard` (scenario-init), `@test test_role_artifact_validator`
7. Documentation: `doc.scenario_engine_design#13.2.c1`, `doc.role_forge_matrix#main`, `doc.factory_forge_arch#7.3.c1`
8. Related Events: (none — scenarios are static manifests)
9. Storage: `@storage runtime_05/scenarios/` (YAML manifests, additive — never delete, only `archive_*.yaml`)
10. Known Limitations: `@lesson CON-8` (vocabulary defense: scenario slugs MUST be in closed-set), `@lesson ANTI-5` (one scenario per release — scope discipline), `@lesson R-127` (Wizard↔Forge orthogonal — never call FORGE directly from SCENARIO)

---

### ⚡ CAP-8: learning.feedback

- **Canonical Entity:** `@entity learning.loop`
- **Implementation:** `core_02/learning_loop.py::class LearningLoop::record`
- **Entrypoint:** `python -m core_02.learning_loop record "<event_id>" --outcome {success|failure***REMOVED*** [--note "<text>"***REMOVED***`
- **Input:** `--event_id` (positional, required; ref to an `@event` from Artifact A); `--outcome` (closed-set); `--note` (free text, ≤1k chars)
- **Output:** JSON: `{learning_id, event_id, outcome, captured_at, reflection: str, lesson_candidates: [str***REMOVED******REMOVED***`
- **Side Effects:** EMITS `@event lesson.candidate_registered`. Atomically appends to `data_13/lessons.yaml`. Triggers `@entity knowledge.engine` re-indexing if a `@lesson` row is finalized.
- **Related Contracts:** `@contract missing_registry.lifecycle` (C.4 #14) for cross-action propagation
- **Related Documentation:** `doc.factory_forge_arch#18.c1` (Learning Loop §18), `doc.lessons_archive#main`

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity learning.loop`
2. Implementation: `core_02/learning_loop.py::LearningLoop::record`
3. Entrypoint: `python -m core_02.learning_loop record "<event_id>" --outcome {success|failure***REMOVED***`
4. Contract: `@contract missing_registry.lifecycle` (analogy)
5. Dependencies: `@entity event.bus`, `@entity knowledge.engine`, `@entity missing.registry`
6. Tests: `@test test_learning_loop`
7. Documentation: `doc.factory_forge_arch#18.c1`, `doc.lessons_archive#main`
8. Related Events: `@event lesson.candidate_registered`, `@event lesson.finalized`
9. Storage: `@storage data_13/lessons.yaml` (atomic write)
10. Known Limitations: `@lesson CON-052` (atomic write), `@lesson ANTI-6b` (closed-set `--outcome` vocabulary; reject drift), `@lesson ANTI-5` (one lesson per incident — scope discipline)

---

### ⚡ CAP-9: remote.sync

- **Canonical Entity:** `@entity remote.sync`
- **Implementation:** `core_02/remote_sync.py::class RemoteSync::status` (with `push`/`pull`/`e2e` companions)
- **Entrypoint:** `python -m core_02.remote_sync {status|push|pull***REMOVED***` (with `e2e_remote_sync.py` for end-to-end dispatcher)
- **Input:** subcommand `status` (read-only); `push` (writes); `pull` (writes)
- **Output:** JSON: `{last_sync, drift_issues: [***REMOVED***, pending_push: [***REMOVED***, last_pull***REMOVED***`
- **Side Effects:** EMITS `@event remote.sync_completed` (1× per push/pull). STORES sync-state to `data_13/remote_sync_state.yaml`.
- **Related Contracts:** (consumes `@contract memory.write` for state persistence)
- **Related Documentation:** `doc.remote_sync_design#main`, `doc.changelog#5.67.0.c1` (persistent listener Phase 5.3-E)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity remote.sync`
2. Implementation: `core_02/remote_sync.py::RemoteSync::status`
3. Entrypoint: `python -m core_02.remote_sync status`
4. Contract: `@contract memory.write` (consumer)
5. Dependencies: `@entity event.bus`, `@entity memory.store`
6. Tests: `@test test_remote_sync`, `@test test_e2e_remote_sync`, `@test test_remote_sync_listener`, `@test test_remote_sync_integration`, `@test test_remote_sync_status`
7. Documentation: `doc.remote_sync_design#main`, `doc.changelog#5.67.0.c1`
8. Related Events: `@event remote.sync_started`, `@event remote.sync_completed`, `@event remote.drift_detected`
9. Storage: `@storage data_13/remote_sync_state.yaml`
10. Known Limitations: `@lesson CON-017` (network calls validated; no shell), `@lesson CON-052` (atomic write on state), `@lesson R-001` (subcommand closed-set: `status|push|pull|e2e`)

---

### ⚡ CAP-10: event.publishing

- **Canonical Entity:** `@entity event.bus`
- **Implementation:** `core_02/event_bus.py::class EventBus::publish` (with `subscribe`, `record_run`)
- **Entrypoint:** programmatic only (no CLI): `from core_02.event_bus import bus; bus.publish(Event(event_id='forge.chain_started', payload={...***REMOVED***))`
- **Input:** `Event(event_id: str, payload: dict, ts: ISO8601)` — `event_id` MUST be in `@event` closed-set (per Artifact A vocabulary)
- **Output:** (async fan-out; subscribers receive payload via `bus.subscribe(event_id)` callback)
- **Side Effects:** dispatches to all registered subscribers. Optionally persists to log via `event_subscribers.py::LogSubscriber` (when debug mode set).
- **Related Contracts:** (consumes via `@contract forge.lifecycle` indirectly; cardinality: every chain emits 3-4 events per CAP-1)
- **Related Documentation:** `doc.event_bus_design#main`, `doc.factory_forge_arch#14.c1` (EventBus §14)

**AGENT RETURNS (per §13):**
1. Canonical Entity: `@entity event.bus`
2. Implementation: `core_02/event_bus.py::EventBus::publish`
3. Entrypoint: programmatic: `EventBus().publish(Event(event_id, payload))`
4. Contract: (hub — consumed by definition; no single owning @contract)
5. Dependencies: (ALL entities publishing events; see Artifact A for publisher list)
6. Tests: `@test test_event_store`, `@test test_telegram_bot_notify` (covers notify subscriber)
7. Documentation: `doc.event_bus_design#main`, `doc.factory_forge_arch#14.c1`
8. Related Events: (ALL — see Artifact A `@event` namespace)
9. Storage: (in-process; no persistent storage by default — `event.store` is optional Phase 2)
10. Known Limitations: `@lesson CON-052` (atomic dispatch — no partial fan-out), `@lesson ANTI-6b` (event_id closed-set, validator raises ValueError on drift), `@lesson R-001` (no `*` / wildcard subscribers — explicit registration required)

---

## §F.5 — Demonstrable Workflow Trace (forge.execution walkthrough)

The end-to-end trace below shows how a future AI-agent uses this artifact to answer `"Как запустить forge?cycle?"`:

### §F.5.1 — User query → Layer 2 match (Phase 2 stub)

```
USER: "как запустить цепочку Forge для проекта partner_id?"
       ↓
[Phase 2 Layer-2 retriever: semantic match***REMOVED***
       ↓
RESULT: CAPABILITY slug = "forge.execution" (top-1 cosine over §F.4 prose)
       ↓
[Layer 1 dispatch — read §F.4 CAP-1***REMOVED***
```

### §F.5.2 — Layer 1 retrieval

```
FROM AGENT_NAVIGATION_MAP_V1 §F.4 CAP-1:
  - entrypoint:  python scripts_01/forge.py chain <project_slug>
  - contract:    @contract forge.execution
  - tests:       test_run_chain, test_forge_chain_cli, ...
  - docs:        doc.factory_forge_arch#4.c1
  - events:      forge.chain_started, forge.stage_completed, forge.chain_completed
  - storage:     data_13/forge_runs/<slug>/
  - limits:      CON-052 (atomic write), ANTI-06b (closed --mode vocab)
```

### §F.5.3 — Layer 3 (Artifact E) — optional enrichment

```
QUERY: neighbors(@entity forge.facade, via_rel='CALLS')
RESULT: ['@entity scenario.registry', '@entity forge.registry', '@entity memory.store'***REMOVED***
  → Agent can answer: "запустить forge для partner_id вызовет chain_started event,
                      запишет record в data_13/forge_runs/partner_id/..."
```

### §F.5.4 — Agent's final response (canonical §13 block)

```
Чтобы запустить forge-цикл для проекта partner_id:

python scripts_01/forge.py chain partner_id --mode forge --json

После запуска:
- Будет создан record в data_13/forge_runs/partner_id/<timestamp>.yaml
- В EventBus уйдут: forge.chain_started → forge.stage_completed × N → forge.chain_completed (или ..._failed)

Контракт: forge.execution (см. CONTRACT_REGISTRY_V1.md §C.4 #1).
Тесты покрытия: test_run_chain, test_forge_chain_cli, test_forge_chain_real_integration.
Документация: docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md §4.
Ограничения: режимы строго из KNOWN_MODES; writes атомарны (CON-052).
```

---

## §F.6 — Schema Discipline (closed-vocab invariants)

Per `core_02/LESSONS.md` ANTI-6b, this artifact enforces:

### §F.6.1 — Field labels (immutable)

`Canonical Entity`, `Implementation`, `Entrypoint`, `Input`, `Output`, `Side Effects`, `Related Contracts`, `Related Documentation` — these 8 labels MUST appear verbatim in every capability card. **No renaming, no abbreviations, no localized variants.**

### §F.6.2 — AGENT-RETURNS field labels (immutable, numeric-keyed)

`1. Canonical Entity`, `2. Implementation`, `3. Entrypoint`, ..., `10. Known Limitations` — numeric-prefixed, no rewording. LLM regex extraction depends on positional stability.

### §F.6.3 — Anchor vocabulary (closed-set, mirrored from Artifact I)

`@entity`, `@contract`, `@event`, `@storage`, `@test`, `@module`, `doc.<shortname>#section.c<n>` — all anchors from `SEMANTIC_ANCHOR_SPEC_V1.md §I.1`. **No freeform anchors.** Validator raises `ValueError` on drift (per ANTI-6b "closed vocabulary contract").

**Accepted alias — `doc.<shortname>#main`:** When a documentation row is the primary entry of a document (e.g., the cover anchor of `ROLE_FORGE_MATRIX_V1.md` referenced by §F.4 CAP-7), the suffix `#main` is a closed-vocab alias for `doc.<shortname>#0.c1` (document root claim). Equivalent under Artifact I §I.1 row 13 (doc.* namespace): `doc.<shortname>#main ≡ doc.<shortname>#0.c1`. Validator MUST NOT flag this as drift per declared alias.

### §F.6.4 — Cardinality invariants recap

| Field | Cardinality | If violated |
|---|---|---|
| Canonical Entity | exactly 1 | artifact invalid — re-locate in Artifact A |
| Implementation | exactly 1 | artifact invalid — re-locate in Artifact A |
| AGENT-RETURNS numbers | all 10 rows present | card → §F.8 open items |
| @test refs | ≥1 | capability → §F.8 (no test surface) |

### §F.6.5 — Forward-projected capabilities (Phase 1+ pending)

**✅ APPLIED (2026-08-12) — CAP-2 + CAP-3 closed:** `opportunity_engine` and `whim_capture` moved from `[PLANNED Phase 1 per pompts_11/079_19_factory_registry.md***REMOVED***` (forward-projected per `core_02/missing_registry.py` lifecycle) → **canonical Artifact A evidence** (status `implemented`, files: `scripts_01/opportunity_engine.py` 587 LOC, `scripts_01/whim_capture.py` 723 LOC, 68 tests passing). §F.4 CAP-2 + CAP-3 updated; §F.8 row 6 marked ✅ applied; CHANGELOG entry added.

**Vocabulary extension (preserved for future forward-projection) — `[PLANNED Phase N per pompts_11/<spec>***REMOVED***`:** any anchor value prefixed with the closed-set meta-token `[PLANNED Phase N per pompts_11/<spec>***REMOVED***` is exempt from `consistency_check` regression failure UNTIL Phase N close. After Phase N close, the `[PLANNED***REMOVED***` prefix MUST be removed and the path becomes canonical Artifact A evidence.

**Convention:** the `[PLANNED ...***REMOVED***` prefix is itself a meta-anchor (closed-vocab token), distinct from `@entity` / `@module` prefixes.

**Remaining forward-projected capabilities (Phase 1.5+ candidates):** `factory.composition`, `forge.design_review`, `learning.transfer`, `agent.distribution`, `artifact.validation` — see §F.1.2. None currently carry the `[PLANNED***REMOVED***` meta-anchor; if any subsequently enters the forward-projection state, the meta-anchor MUST be applied.

---

## §F.7 — Cross-Reference Topology (Layer-3 wiring)

This artifact is **downstream of A+B+C+D+E** and **upstream of G+H**. It is the L1 endpoint that connects L2 (vector) and L3 (graph) to operational reality.

```
┌─────────────────────────────────────────────────────────────┐
│  A: PLATFORM_CODE_MAP_V1          ← ground truth: 25 @entities│
│  B: DOCUMENTATION_CODE_MAP_V1      ← 78 doc.* claim rows        │
│  I: SEMANTIC_ANCHOR_SPEC_V1        ← 19 anchor namespaces       │
│  C: CONTRACT_REGISTRY_V1           ← 14 @contracts              │
│  D: ARCHITECTURE_DECISION_REGISTRY ← 14 ADRs + 8 lessons        │
│  E: TRACEABILITY_GRAPH_V1          ← 60 nodes, 85 edges         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  F: AGENT_NAVIGATION_MAP_V1 (THIS) ← 10 CAPABILITY cards     │
│     → layer 1 dispatch to CLI / module paths                  │
│     → layer 3 dispatch to E query methods                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phases G/H/J/K/L: PROMPT_TEMPLATES + RUNTIME_GUIDE + ...     │
│     → consume CAPABILITY slugs as prompt-template keys       │
│     → record execution traces for reproducibility            │
└─────────────────────────────────────────────────────────────┘
```

### §F.7.1 — Wiring to Artifact E (5 query methods × capability layers)

For each capability the §F.4 card implicitly invokes:
- `CAP-1 forge.execution`: `shortest_path(@entity forge.facade, @test test_run_chain)` (impact analysis) + `enforces(@entity forge.facade)` (constraint check)
- `CAP-2 opportunity.discovery`: `neighbors(@entity opportunity.engine, via_rel='CALLS')` → upstream event sources
- `CAP-5 project.registration`: `contradictions(@entity forge.registry)` → no anti-pattern currently enforced (good signal)
- `CAP-7 scenario.resolution`: `subgraph({@entity scenario.registry, @entity forge.facade***REMOVED***, depth=2)` → role composition graph
- `CAP-10 event.publishing`: hub — `neighbors(*, via_rel='EMITS')` cross-cuts all publishers

(Per capability, agent chooses; §F.4 does not hard-code the query — that's the agent's runtime decision.)

---

## §F.8 — Open Items

1. **§F.1.2 deferred capabilities** (5 candidates: factory.composition, forge.design_review, learning.transfer, agent.distribution, artifact.validation) — Phase 1.5 follow-up.
2. **§F.6.5 re-validation trigger** — ✅ applied 2026-08-12 (see §F.6.5 APPLIED banner): CAP-2 + CAP-3 `[PLANNED Phase 1 ...***REMOVED***` prefixes dropped; canonical entities migrated to Artifact A's `@entity` inventory; missing_registry status flipped design_ready → implemented for both opportunity_engine + whim_capture. ✅ APPLIED (CHANGELOG entry).
2. **§F.3 Layer-2 vector retriever** — NOT in this slice; Phase 2 dependency. The CAPABILITY slugs in §F.4 ARE the labels for that future index.
3. **§F.4 CAP-2 / CAP-3 test coverage** — pending Phase 1 vertical-slice CI implementation per `pompts_11/079_19_factory_registry.md`.
4. **§F.7.1 query patterns** are illustrative, not exhaustive; agents may compose differently.
5. **Cross-ref to Phase G/H artifacts** (not yet written) — CAPABILITY slugs are the key linking this artifact downstream.

---

## §F.9 — Operator Handoff / Checklist

This artifact is **CLOSED** when all of the following hold:

- [x***REMOVED*** §F.1 first-slice justified (10 capabilities selected by §F.1 3-condition filter; choices grounded in Artifact A)
- [x***REMOVED*** §F.2 §12 + §13 spec mapping is verbatim cite (no paraphrase)
- [x***REMOVED*** §F.3 3-layer integration contract defined (Layer 1 = this; Layer 2 = Phase 2 stub; Layer 3 = Artifact E consumer)
- [x***REMOVED*** §F.4 all 10 capability cards present, each with 8 §12 fields + 10-row §13 AGENT-RETURNS
- [x***REMOVED*** §F.5 demonstrable workflow trace (forge.execution example)
- [x***REMOVED*** §F.6 schema discipline (8 §12 labels + 10 §13 numerics + closed-vocab anchors)
- [x***REMOVED*** §F.7 cross-reference topology diagram (A+B+I+C+D+E → F → G/H/J/K/L)
- [x***REMOVED*** §F.8 open items enumerated with Phase 1.5 / Phase 2 owners
- [x***REMOVED*** Footer integrity: artifact_count, upstream_count, deferred_count, status_summary
- [x***REMOVED*** consistency_check passes (no broken anchors / cross-refs)
- [x***REMOVED*** No code modifications (read-only artifact, per ANTI-5 scope discipline)

---

## Footer

- **Artifact:** F `AGENT_NAVIGATION_MAP_V1.md`
- **Spec cite:** `projects_17/content_factory/prompts/4.md` §12 + §13 + §14
- **Upstream truth (5):** A (entities), B (docs), I (anchors), C (contracts), D (ADRs+lessons), E (graph)
- **First-slice capability count:** 10 (CAP-1..CAP-10)
- **Deferred to Phase 1.5+:** 5 (factory.composition, forge.design_review, learning.transfer, agent.distribution, artifact.validation)
- **Status:** v1.0 FIRST SLICE — read-only, awaiting Phase G/H consumption
- **Updated:** 2026-08-12 (workspace freeze between Phase E close and Phase F open)
- **Doctrine:** additive only (no overwrite of upstream artifacts per `core_02/LESSONS.md` ANTI-5)
