# AGENT_PROMPT_TEMPLATES_V1.md (Artifact G) — Agent Prompt-Template Layer

> **Статус:** v1.0 FIRST SLICE — read-only canonical architecture artifact.
> **Дата:** 2026-08-12 (Workspace OS freeze — Phase G open after Phase F close).
> **Role:** Reusable prompt templates for AI agents operating on Workspace OS, keyed by Artifact F's CAPABILITY slugs.
> **Composition:** Layer 1 (Structured) — closed-vocab field schema. Fenced ```` ```prompt ````/```` ```json ```` blocks for agent-extraction. No `.yaml`/`.py` instances at this stage (additive per `AGENTS.md §1`).
> **Upstream truth sources:** Artifact A `PLATFORM_CODE_MAP_V1.md` (25 @entities), Artifact C `CONTRACT_REGISTRY_V1.md` (14 @contracts), Artifact D `ARCHITECTURE_DECISION_REGISTRY_V1.md` (22 records), Artifact E `TRACEABILITY_GRAPH_V1.md` (60 nodes + 85 edges), Artifact F `AGENT_NAVIGATION_MAP_V1.md` (10 CAPABILITY cards).
> **Existing infra (NOT duplicated):** `core_02/blueprint_v3.py::BlueprintCorpus`, `scripts_01/prompt_queue.py`, `scripts_01/prompt_dispatcher.py`, `core_02/wizard_lib.py::build_agent_json`. Phase G is the *specification* layer; runtime dispatch remains in those modules.
> **Downstream consumer:** Phase H → Artifact H (`RUNTIME_REPRODUCTION_GUIDE_V1.md`) records execution traces; `scripts_01/prompt_dispatcher.py` will eventually consume `Template ID` + `Execution Target` to build `Task JSON`.

---

## §G.1 — Scope: First-Slice = 10 templates, 2 fully-developed exemplars + 8 compact

**Selection rule:** templates MUST satisfy three conditions:
1. **One-to-one mapping** to a CAPABILITY slug in Artifact F (CAP-1..CAP-10); no orphan templates.
2. **Upstream-groundable:** every Template ID has a verifiable AGENT-RETURNS block in F's §F.4.
3. **Downstream-dispatchable:** `Execution Target` field is either (a) existing CLI in `scripts_01/forge.py` / `python -m core_02.X` or (b) `[PLANNED Phase N per pompts_11/<spec>***REMOVED***` meta-anchor (per F.6.5 forward-projection rule).

### §G.1.1 — Fully-developed exemplars (2)

| TPL | Capability | Reason for full development |
|---|---|---|
| TPL-1 | `forge.execution` | Primary orchestrator loop; most-clicked capability; zero-shot example mandatory for downstream H trace validation. |
| TPL-6 | `memory.search` | RAG agent self-correction; semantic-rich exemplar showing Layer-3 wiring + mixed lexical/semantic/hybrid modes. |

### §G.1.2 — Compact templates (8)

TPL-2, TPL-3, TPL-4, TPL-5, TPL-7, TPL-8, TPL-9, TPL-10 — each carries the 10-field schema with stub prose. Sufficient for LLM regex extraction; full prose deferred to Phase G.1.5.

### §G.1.3 — Deferred templates (Phase G.1.5)

Per F's §F.1.2 deferred capabilities: TPL-11..TPL-15 (factory.composition, forge.design_review, learning.transfer, agent.distribution, artifact.validation) — Phase G.1.5 expansion candidates.

---

## §G.2 — 10-Field Schema (closed-vocab, deterministic)

| # | Field label | Closed-vocab source |
|---|---|---|
| 1 | Template ID | `CAP-N.<capability_slug>` — exact match to F's §F.4 CAP-N header |
| 2 | Canonical Entity | `@entity <name>` — must equal F's row 1 (Canonical Entity) |
| 3 | Intent | free-text (≤1 sentence) — describes what the agent achieves |
| 4 | Blueprint Role | `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role <name>` —resolver against `@entity blueprint.v3` (per Artifact A) |
| 5 | Input Schema | derives from F's `Input:` field — argparse args + flags as a closed-set list |
| 6 | Execution Target | derives from F's `Entrypoint:` field — exact CLI command OR API route OR forward-projected prefix |
| 7 | Layer 3 Wiring | explicit Artifact E query method invocation (one of the 5 methods: `shortest_path` / `neighbors` / `subgraph` / `contradictions` / `enforces`) |
| 8 | Failure Recovery | actionable agent instruction — *what to do* on CLI non-zero exit OR `<entity>` exception |
| 9 | Fallback Strategy | graceful degradation path — alternative capability OR escalation to human |
| 10 | Validation Anchors | closed-set of `@test <test_name>` + `@event <event_name>` (must equal F's AGENT-RETURNS rows 6 + 8) |

**Schema discipline (per F.6.3 alias precedent):** numeric-prefixed field labels are immutable; LLM regex extraction depends on positional stability. Validator raises `ValueError` on drift (per `core_02/LESSONS.md ANTI-6b`).

**Cardinality invariant:**
- Field 1 (Template ID): exactly 1 per card.
- Field 2 (Canonical Entity): exactly 1; must match F's Canonical Entity exactly.
- Field 6 (Execution Target): exactly 1 (CLI command OR `[PLANNED ...***REMOVED***` prefixed forward-projection per F.6.5).
- Field 10 (Validation Anchors): ≥1 `@test` ref (otherwise card goes to §G.8 open items).

---

## §G.3 — Storage Format: Pure Markdown with fenced codeblocks

Decision rationale (from design verification `B`):
- **Pure markdown** because A→F are pure markdown; switching to YAML/dataclass breaks the Layer 1 vector + regex extraction codebase in `prompt_queue.py` + `prompt_dispatcher.py`.
- **Fenced ```` ```prompt ```` blocks** let the dispatcher's existing parser regex-extract prompt body without bespoke code in `core_02`.
- **Fenced ```` ```json ```` blocks** for expected output schema — easier to validate against `tests_09/test_prompts_naming.py` closed-set convention.

### §G.3.1 — Template body format (declarative)

Each TPL-N card uses:

```markdown
### 🧠 TPL-N: <capability_slug>

1. **Template ID:** …
2. **Canonical Entity:** …
3. **Intent:** …
4. **Blueprint Role:** …
5. **Input Schema:** …
6. **Execution Target:** …
7. **Layer 3 Wiring:** …
8. **Failure Recovery:** …
9. **Fallback Strategy:** …
10. **Validation Anchors:** …

[Fully-developed templates additionally include:***REMOVED***

\`\`\`prompt
<system prose>
<user prompt body>
\`\`\`

\`\`\`json
{ "expected_output_schema": … ***REMOVED***
\`\`\`
```

Closed-vocab meta-anchor `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED***` is exempt from drift_check (per F.6.5).

---

## §G.4 — 10 Template Cards

### 🧠 TPL-1: forge.execution (FULLY-DEVELOPED EXEMPLAR)

1. **Template ID:** `CAP-1.forge.execution`
2. **Canonical Entity:** `@entity forge.facade`
3. **Intent:** Invoke a Forge chain on a registered project, atomic-write the run record, emit lifecycle events, and return a 9-key chain payload.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role orchestrator` (resolver: `@entity blueprint.v3::BlueprintCorpus[fqn=orchestrator***REMOVED***`)
5. **Input Schema:** `<project_slug>` `[--mode {forge|smoke|full***REMOVED******REMOVED***` `[--resume***REMOVED***` `[--json***REMOVED***`
6. **Execution Target:** `python scripts_01/forge.py chain <project_slug> [--mode {forge|smoke|full***REMOVED******REMOVED*** [--resume***REMOVED*** [--json***REMOVED***`
7. **Layer 3 Wiring:** `Artifact E::shortest_path(@entity forge.facade, @test test_run_chain)` — verifies chain path resolves through scenario.registry → forge.facade → memory.store; followed by `Artifact E::enforces(@entity forge.facade)` to surface any `@lesson CON/R` constraints in effect.
8. **Failure Recovery:** On non-zero exit: read `stderr`, lookup `@event forge.chain_failed` to identify the failing stage; if `--resume` not in input, retry with `--resume` flag from last `@event forge.stage_completed` timestamp; if state-collision, invoke `@entity consistency.check` (TPL-4) to surface registry drift before retry. Per `core_02/LESSONS.md CON-052` (atomic write), do NOT manually edit `data_13/forge_runs/<slug>/`.
9. **Fallback Strategy:** If `forge.execution` returns `consistent=False` from upstream consistency check, escalate to **TPL-4 `consistency.audit`** as a precondition. If project not in `@entity forge.registry`, escalate to **TPL-5 `project.registration`** first.
10. **Validation Anchors:** `@test test_run_chain`, `@test test_forge_chain_cli`, `@test test_forge_chain_real_integration`, `@event forge.chain_started`, `@event forge.chain_completed`, `@event forge.chain_failed`

```prompt
SYSTEM:
You are an AI-orchestrator driving a Workspace OS Forge chain. Your target capability is `@entity forge.facade`.
Hard rules:
1. NEVER bypass `@entity forge.registry` — projects not in registry MUST be added first (see TPL-5).
2. NEVER call forge from a scenario without `@entity forge.facade` mediation (per `@lesson R-127` Wizard↔Forge orthogonal-STATE).
3. ALL writes to `data_13/forge_runs/` are atomic per `@lesson CON-052`; never modify record files in-place.
4. `--mode` MUST be in closed-set `{forge, smoke, full***REMOVED***` per `@lesson ANTI-06b`; reject any other value.

USER:
Запусти forge-цепочку для проекта `<project_slug>` в режиме `<mode>` (default=forge). 
Если есть прерванный запуск, попробуй `--resume`. 
Верни результат строго в JSON-формате §G.4 schema.

EXPECTED OUTPUT SCHEMA (json):
```
{
  "slug": "<project_slug>",
  "mode": "<mode>",
  "started_at": "ISO-8601 timestamp",
  "finished_at": "ISO-8601 timestamp or null",
  "stages": [
    {"stage_id": "string", "status": "ok|skipped|failed", "started_at": "...", "finished_at": "...", "evidence": ["..."***REMOVED******REMOVED***
  ***REMOVED***,
  "record_path": "data_13/forge_runs/<slug>/<timestamp>.yaml",
  "status": "ok|failed|partial",
  "summary": "human-readable 1-2 sentences",
  "evidence": ["record path", "events emitted"***REMOVED***
***REMOVED***
```

OUTPUT (json):
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["slug", "mode", "started_at", "stages", "record_path", "status", "summary"***REMOVED***,
  "properties": {
    "slug":          { "type": "string", "pattern": "^[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***$" ***REMOVED***,
    "mode":          { "type": "string", "enum": ["forge", "smoke", "full"***REMOVED*** ***REMOVED***,
    "started_at":    { "type": "string", "format": "date-time" ***REMOVED***,
    "finished_at":   { "type": ["string", "null"***REMOVED***, "format": "date-time" ***REMOVED***,
    "stages":        { "type": "array", "items": { "type": "object" ***REMOVED*** ***REMOVED***,
    "record_path":   { "type": "string", "pattern": "^data_13/forge_runs/[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***/.+\\.yaml$" ***REMOVED***,
    "status":        { "type": "string", "enum": ["ok", "failed", "partial"***REMOVED*** ***REMOVED***,
    "summary":       { "type": "string", "maxLength": 500 ***REMOVED***,
    "evidence":      { "type": "array", "items": { "type": "string" ***REMOVED*** ***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

### 🧠 TPL-2: opportunity.discovery (COMPACT)

1. **Template ID:** `CAP-2.opportunity.discovery`
2. **Canonical Entity:** `@entity opportunity.engine`
3. **Intent:** Discover and lifecycle-promote opportunity signals from `@entity project.pulse` / `@entity knowledge.engine`.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role analyst`
5. **Input Schema:** `[--threshold 0.5***REMOVED***` `[--max-active 50***REMOVED***`
6. **Execution Target:** `python scripts_01/opportunity_engine.py discover --project-id <slug> [--max 10***REMOVED*** [--json***REMOVED***` *(CLI landed with Vertical Slice CI Phase 1 2026-08-12)*
7. **Layer 3 Wiring:** `Artifact E::neighbors(@entity opportunity.engine, via_rel='CALLS')` — surfaces upstream pulse / knowledge sources; followed by `Artifact E::contradictions(@entity opportunity.engine)` to surface ANTI-constraints before promotion.
8. **Failure Recovery:** On `ValueError` from closed-lifecycle mapping (`@lesson R-001`), DO NOT propose lifecycle transition; emit `@event opportunity.lifecycle_blocked` (registration required); consult TPL-3 `whim.capture` if the signal originates from a user text-grab.
9. **Fallback Strategy:** If `opportunity.engine` is not yet implemented (CAP-2 forward-projected per F.6.5), fall back to **TPL-3 `whim.capture`** pattern: register signal as a `@lesson candidate` via **`core_02/missing_registry.py::register`**, then defer to post-Phase-1 lifecycle.
10. **Validation Anchors:** `@test test_opportunity_engine` (414 LOC, 68 tests passing 2026-08-12), `@event opportunity.discovered`, `@event opportunity.lifecycle_changed`

---

### 🧠 TPL-3: whim.capture (COMPACT)

1. **Template ID:** `CAP-3.whim.capture`
2. **Canonical Entity:** `@entity whim_capture`
3. **Intent:** Rapid developer CLI to grab a fleeting text idea as a `@lesson candidate` and stage it for later `whim.promote`.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role archivist`
5. **Input Schema:** `<text>` `[--tag <tag>***REMOVED***` `[--source {cli|tg|web***REMOVED******REMOVED***` (text ≤280 chars per design)
6. **Execution Target:** `python scripts_01/whim_capture.py capture <body> --project-id <slug> [--source {cli|hand|project_pulse|event_bus|knowledge|whim***REMOVED******REMOVED*** [--priority 5***REMOVED*** [--json***REMOVED***` *(CLI landed with Vertical Slice CI Phase 1.2 2026-08-12)*
7. **Layer 3 Wiring:** `Artifact E::shortest_path(@entity whim_capture, @entity opportunity.engine)` — confirms downstream promotion pipeline; followed by `neighbors(@entity whim_capture, via_rel='EMITS')` to list other event producers.
8. **Failure Recovery:** On `ValueError` (whim text contains shell-injection patterns per `@lesson CON-017`): sanitize via `text.replace(';', '').replace('|', '').replace('`', '')` and retry on captured text; if still failing, surface as `@lesson R-127` violation, escalate via TPL-8 `learning.feedback`.
9. **Fallback Strategy:** If `whim_capture` not yet implemented, fall back to **TPL-8 `learning.feedback`** with `text=<original_text> --outcome deferred --note captured_pre_implementation`.
10. **Validation Anchors:** `@test test_whim_capture` (471 LOC, 68 tests passing 2026-08-12), `@event whim.captured`, `@event whim.promoted`, `@storage data_13/whims.yaml`

---

### 🧠 TPL-4: consistency.audit (COMPACT)

1. **Template ID:** `CAP-4.consistency.audit`
2. **Canonical Entity:** `@entity consistency.check`
3. **Intent:** Cross-validate the entire Workspace OS (registry sync, document_registry, ADR slot coverage, missing_registry) and return drift issues.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role validator`
5. **Input Schema:** `--workspace .` `[--json***REMOVED***` `[--strict***REMOVED***`
6. **Execution Target:** `python -m scripts_01.consistency_check --workspace . [--json***REMOVED*** [--strict***REMOVED***`
7. **Layer 3 Wiring:** `Artifact E::subgraph({@entity forge.registry, @entity scenario.registry, @entity missing_registry***REMOVED***, depth=2)` — extracts the registry sub-graph; followed by `contradictions(@entity consistency.check)` to surface meta-anchor violations (`[PLANNED ...***REMOVED***` past Phase 1 close deadline per F.6.5).
8. **Failure Recovery:** On `consistent=False`: read `--json` output, group `issues[***REMOVED***` by `level` (ERROR/WARN); for ERRORs, locate the canonical artifact (per the `source` field — e.g., `§20 of FACTORY_FORGE_ARCHITECTURE_V1.md`) and patch before re-running. For WARN with `--strict`, treat as ERROR. Per `@lesson ANTI-5`, do NOT consider consistency alone sufficient — always pair with `pytest tests_09/ -q`.
9. **Fallback Strategy:** Read-only audit; if execution fails (Python crash), call `--workspace . --json` to dump raw results regardless; if `--workspace` path-traversal rejected per `@lesson CON-017`, hard-fail with `Path traversal rejected`.
10. **Validation Anchors:** `@test test_consistency_check`, `@test test_drift_check`

---

### 🧠 TPL-5: project.registration (COMPACT)

1. **Template ID:** `CAP-5.project.registration`
2. **Canonical Entity:** `@entity forge.registry`
3. **Intent:** Register a new project directory under `projects_17/` and append it to the Forge registry.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role onepager`
5. **Input Schema:** `<project_id>` `<root_path>` `[--description <text>***REMOVED***`
6. **Execution Target:** `python -m core_02.forge_registry register <project_id> <root_path> [--description <text>***REMOVED***`
7. **Layer 3 Wiring:** `Artifact E::contradictions(@entity forge.registry)` — confirm no anti-pattern constraints; followed by `neighbors(@entity forge.registry, via_rel='STORES')` to confirm storage path.
8. **Failure Recovery:** On slug-validation failure (`@lesson CON-017`): suggest corrected slug matching `^[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***$`; on `FileExistsError` (captured per race-safe mkdir pattern): suggest `--recover` to attach to existing dir; on atomic-write failure (`@lesson CON-052`): re-run with `--no-resume` flag.
9. **Fallback Strategy:** If `forge.registry` is corrupted, escalate to **TPL-4 `consistency.audit`** first, fix the registry YAML, then re-run registration. **Never** clobber existing rows — additive only per `@lesson CAN-016`.
10. **Validation Anchors:** `@test test_forge_registry`, `@test test_v0_1_slice`, `@event forge.project_registered`

---

### 🧠 TPL-6: memory.search (FULLY-DEVELOPED EXEMPLAR)

1. **Template ID:** `CAP-6.memory.search`
2. **Canonical Entity:** `@entity memory.store` (with `@entity semantic.layer` co-anchor for vector mode)
3. **Intent:** Search the workspace knowledge index (RAG) for prior context relevant to a query, returning ranked snippets.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role archivist`
5. **Input Schema:** `<query>` `[--top-k 5***REMOVED***` `[--mode {lexical|semantic|hybrid***REMOVED******REMOVED***`
6. **Execution Target:** `python -m core_02.memory_store search "<query>" [--top-k 5***REMOVED*** [--mode {lexical|semantic|hybrid***REMOVED******REMOVED***`
7. **Layer 3 Wiring:** `Artifact E::neighbors(@entity memory.store, via_rel='IMPLEMENTS')` → pulls `@contract memory.search` binding; followed by `neighbors(@entity semantic.layer, via_rel='CALLS')` to confirm vector pipeline is wired; followed by `enforces(@entity memory.store)` to surface @lesson CON/R constraints (e.g., `CON-052` atomic refresh on index rebuild).
8. **Failure Recovery:** On `--mode` validation rejection (`@lesson R-001` closed-set `{lexical, semantic, hybrid***REMOVED***`): retry with `--mode hybrid` (default-fallback); on index-corruption (low-recall on `semantic` mode): rebuild via `python -m core_02.memory_store rebuild-index`; if rebuild fails, downgrade to `--mode lexical` (degraded but functional per `@lesson ANTI-3` "search without test coverage = hallucination risk").
9. **Fallback Strategy:** **NEVER proceed without search** if context relevance is uncertain — fall back to **TPL-4 `consistency.audit`** for registry-ground truth, then to ad-hoc `grep -r "<query>" docs_10/engineering-memory/` (open-coded but tractable per `@lesson CAN-016` additive-only).
10. **Validation Anchors:** `@test test_memory_store`, `@test test_semantic_layer`, `@test test_rag_engine`, `@storage data_13/memory_index_sqlite` (derived per F's row 9)

```prompt
SYSTEM:
You are an AI-archivist performing RAG search on Workspace OS. Your target capability is `@entity memory.store` plus `@entity semantic.layer`.
Hard rules:
1. `--mode` MUST be in `{lexical, semantic, hybrid***REMOVED***` per `@lesson R-001` (closed-set vocabulary).
2. `<query>` MUST NOT contain shell-injection chars per `@lesson CON-017` — strip `;`, `|`, backticks, `$(...)`.
3. `--top-k` default is 5; values >50 trigger `@lesson R-011` "search saturation" (refine query instead).
4. Per `@lesson ANTI-3`: NEVER use search results without ground-truth test coverage regenerated per index bump.

USER:
Найди в базе знаний Workspace OS всё, что относится к `"<query>"`. 
Режим — `<mode>` (default=hybrid). Top-K — `<top_k>` (default=5).
Верни результат в §G.4 JSON-схеме.

EXPECTED OUTPUT SCHEMA (json):
```
[
  {
    "doc_id": "string (path-like)",
    "title": "string",
    "snippet": "string (max 500 chars)",
    "score": "float [0.0..1.0***REMOVED***",
    "source_module": "@entity <name>"
  ***REMOVED***
***REMOVED***
```

OUTPUT (json):
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["doc_id", "title", "snippet", "score", "source_module"***REMOVED***,
    "properties": {
      "doc_id":         { "type": "string", "minLength": 1 ***REMOVED***,
      "title":          { "type": "string", "minLength": 1 ***REMOVED***,
      "snippet":        { "type": "string", "maxLength": 500 ***REMOVED***,
      "score":          { "type": "number", "minimum": 0.0, "maximum": 1.0 ***REMOVED***,
      "source_module":  { "type": "string", "pattern": "^@entity [a-z***REMOVED***[a-z0-9_.***REMOVED***{2,40***REMOVED***$" ***REMOVED***
    ***REMOVED***
  ***REMOVED***,
  "maxItems": 50
***REMOVED***
```

---

### 🧠 TPL-7: scenario.resolution (COMPACT)

1. **Template ID:** `CAP-7.scenario.resolution`
2. **Canonical Entity:** `@entity scenario.registry`
3. **Intent:** Resolve a scenario manifest into the Blueprint role list for chain composition.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role wizard`
5. **Input Schema:** `list [--vertical <name>***REMOVED***` OR `find <scenario_slug>`
6. **Execution Target:** `python -m core_02.scenario_registry list [--vertical <name>***REMOVED***` OR `python -m core_02.scenario_registry find <scenario_slug>`
7. **Layer 3 Wiring:** `Artifact E::subgraph({@entity scenario.registry, @entity forge.facade, @entity blueprint.v3***REMOVED***, depth=2)` — extracts the composition sub-graph; followed by `contradictions(@entity scenario.registry)` to surface `@lesson ANTI-5` / `@lesson R-127` violations.
8. **Failure Recovery:** On `<scenario_slug>` not found: print available slugs via `list`; on per-vertical filter returning empty: list `_universal` vertical scenarios; on Blueprint role reference missing → bubble `OrchestratorRoleMissing` to **TPL-5 `project.registration`** (re-resolve via `forge.registry`).
9. **Fallback Strategy:** Wizard↔Forge orthogonal — **NEVER call forge from scenario** directly per `@lesson R-127`. Use TPL-1 `forge.execution` as the cross-boundary mediator. If scenario composition fails, escalate to **TPL-4 `consistency.audit`** + manual review of `runtime_05/scenarios/*.yaml`.
10. **Validation Anchors:** `@test test_scenario_registry`, `@test test_wizard`, `@test test_role_artifact_validator`

---

### 🧠 TPL-8: learning.feedback (COMPACT)

1. **Template ID:** `CAP-8.learning.feedback`
2. **Canonical Entity:** `@entity learning.loop`
3. **Intent:** Record a domain event's success/failure outcome as a lesson candidate and trigger re-indexing.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role archivist`
5. **Input Schema:** `<event_id>` `--outcome {success|failure|partial***REMOVED***` `[--note "<text>"***REMOVED***`
6. **Execution Target:** `python -m core_02.learning_loop record <event_id> --outcome {success|failure|partial***REMOVED*** [--note "<text>"***REMOVED***`
7. **Layer 3 Wiring:** `Artifact E::neighbors(@entity learning.loop, via_rel='EMITS')` — list emitted lesson-candidate events; followed by `enforces(@entity learning.loop)` — surface any `@lesson CON/R` rules blocking this outcome classification.
8. **Failure Recovery:** On `--outcome` validation rejection (`@lesson ANTI-6b` closed-set): retry with `--outcome partial` (most inclusive); on `event_id` not found in closed-set (per `core_02/missing_registry.py`): emit `@event lesson.candidate_orphan` and route to **`core_02/missing_registry.py::register`**.
9. **Fallback Strategy:** Atomic-write failures per `@lesson CON-052`: re-run with no `--note` (shorter payload likely succeeds); if still failing, surface as `@lesson R-new` violation and promote to a new ADR via **TPL-8** recurrence.
10. **Validation Anchors:** `@test test_learning_loop`, `@event lesson.candidate_registered`, `@event lesson.finalized`, `@storage data_13/lessons.yaml`

---

### 🧠 TPL-9: remote.sync (COMPACT)

1. **Template ID:** `CAP-9.remote.sync`
2. **Canonical Entity:** `@entity remote.sync`
3. **Intent:** Synchronize Workspace OS state (`data_13/`, `core_02/memory_store`, prompted events) with a remote sink.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role distributor`
5. **Input Schema:** subcommand `{status|push|pull|e2e***REMOVED***`; `e2e_remote_sync.py` for orchestrator-driven end-to-end.
6. **Execution Target:** `python -m core_02.remote_sync {status|push|pull***REMOVED***` OR `python scripts_01/e2e_remote_sync.py` for full cycle.
7. **Layer 3 Wiring:** `Artifact E::neighbors(@entity remote.sync, via_rel='CONSUMES')` — list event streams being pulled across; followed by `enforces(@entity remote.sync)` — surface any `@lesson CON-017` network-bound constraints.
8. **Failure Recovery:** On network failure (`@lesson CON-017`): retry with exponential backoff up to 3 attempts; if all attempts fail, log to `data_13/remote_sync_state.yaml` as `status=degraded` and continue (queue-and-forward on next sync cycle). On state-corruption: re-run `status` subcommand first, then `pull` subcommand.
9. **Fallback Strategy:** If remote sink is unreachable for >24h, escalate via **`core_02/event_bus.py::publish(event_id='remote.drift_alert')`** and route to **TPL-8 `learning.feedback`** with `--outcome failure --note remote_unreachable_24h`.
10. **Validation Anchors:** `@test test_remote_sync`, `@test test_e2e_remote_sync`, `@test test_remote_sync_listener`, `@test test_remote_sync_integration`, `@test test_remote_sync_status`, `@event remote.sync_started`, `@event remote.sync_completed`, `@event remote.drift_detected`

---

### 🧠 TPL-10: event.publishing (COMPACT)

1. **Template ID:** `CAP-10.event.publishing`
2. **Canonical Entity:** `@entity event.bus`
3. **Intent:** Publish a typed event to the in-process EventBus for synchronous fan-out to registered subscribers.
4. **Blueprint Role:** `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED*** @role archivist`
5. **Input Schema:** `Event(event_id=<@event-name>, payload=<dict>, ts=<ISO8601>)` — `event_id` MUST be in `@event` closed-set.
6. **Execution Target:** programmatic only (no CLI): `bus = EventBus(); bus.publish(Event(event_id=<name>, payload={...***REMOVED***, ts=<iso>))`
7. **Layer 3 Wiring:** `Artifact E::neighbors(@entity event.bus, via_rel='EMITS')` → cross-cuts all publishers; followed by `contradictions(@entity event.bus)` to surface `@lesson R-001` no-wildcard-subscribers constraint.
8. **Failure Recovery:** On `event_id` not in closed-set (`@lesson ANTI-6b`): raise `ValueError` per `core_02/LESSONS.md ANTI-6b`; do NOT silently fallback (per "closed vocabulary contract"). Surface to calling agent via `RuntimeError`; route to **TPL-8 `learning.feedback`** with `event_id=<unknown_id>` for vocabulary extension consideration.
9. **Fallback Strategy:** No fallback — event publishing is the structural primitive. Subscribers MUST be registered explicitly (no `*` / wildcard). If event is "internal-only", route via direct callback.
10. **Validation Anchors:** `@test test_event_store`, `@test test_telegram_bot_notify` (notify-subscriber coverage)

---

## §G.5 — Cross-Reference Topology

```
┌─────────────────────────────────────────────────────────────┐
│  A: PLATFORM_CODE_MAP_V1          ← 25 @entities            │
│  B: DOCUMENTATION_CODE_MAP_V1      ← 78 doc.* claim rows     │
│  I: SEMANTIC_ANCHOR_SPEC_V1        ← 19 anchor namespaces    │
│  C: CONTRACT_REGISTRY_V1           ← 14 @contracts           │
│  D: ARCHITECTURE_DECISION_REGISTRY ← 14 ADRs + 8 lessons     │
│  E: TRACEABILITY_GRAPH_V1          ← 60 nodes + 85 edges     │
│  F: AGENT_NAVIGATION_MAP_V1        ← 10 CAPABILITY slugs     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  G: AGENT_PROMPT_TEMPLATES_V1 (THIS) ── 10 TPL cards         │
│     ├─ TPL-1, TPL-6:     fully-developed + ```prompt``` / ```json```
│     └─ TPL-2..5,7..10:  compact field-only                  │
│     Layer 3 wiring: All cards consume E's 5 query methods    │
│     Blueprint Role:    All forwarding to @entity blueprint.v3│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Downstream consumers:                                        │
│  H: RUNTIME_REPRODUCTION_GUIDE_V1   ← records actual traces │
│  scripts_01/prompt_dispatcher.py    ← parses TPL-N blocks    │
│  core_02/wizard_lib.py::build_task_json ← builds Task JSON   │
└─────────────────────────────────────────────────────────────┘
```

### §G.5.1 — Edge-by-edge couplings

| TPL | Upstream artifact rows consumed | Downstream artifact produced for |
|---|---|---|
| TPL-1 forge.execution | F.4 CAP-1 (10 rows); C.4 #1-3; blueprint.v3 orchestrator; E 60 nodes | H.4 trace forge.execution |
| TPL-2 opportunity.discovery | F.4 CAP-2 (forward-projected per F.6.5); E neighbors(CALLS) | H.4 trace opportunity.discovery |
| TPL-3 whim.capture | F.4 CAP-3 (forward-projected per F.6.5); E shortest_path | H.4 trace whim.capture |
| TPL-4 consistency.audit | F.4 CAP-4; E subgraph(registry); E contradictions | H.4 trace consistency.audit |
| TPL-5 project.registration | F.4 CAP-5; E contradictions; E neighbors(STORES) | H.4 trace project.registration |
| TPL-6 memory.search | F.4 CAP-6; E neighbors(IMPLEMENTS, CALLS); RAG 2.0 references | H.4 trace memory.search |
| TPL-7 scenario.resolution | F.4 CAP-7; role_forge_matrix; E subgraph({registry,facade,v3***REMOVED***); R-127 | H.4 trace scenario.resolution |
| TPL-8 learning.feedback | F.4 CAP-8; LESSONS archive; E neighbors(EMITS) | H.4 trace learning.feedback |
| TPL-9 remote.sync | F.4 CAP-9; E neighbors(CONSUMES); remote_sync_design | H.4 trace remote.sync |
| TPL-10 event.publishing | F.4 CAP-10; E neighbors(EMITS, all); event_bus_design | H.4 trace event.publishing |

---

## §G.6 — Schema Discipline (closed-vocab invariants)

### §G.6.1 — Field label immutability

The 10 field labels (numeric-prefixed) MUST appear verbatim in every TPL card. Zero renaming, zero abbreviations, zero localized variants. Same discipline as F.6.1.

### §G.6.2 — Closed-vocab anchors (per Artifact I §I.1)

`@entity`, `@contract`, `@event`, `@storage`, `@test`, `@module`, `@role`, `doc.<shortname>#section.c<n>`, `[PLANNED Phase N per pompts_11/<spec>***REMOVED***` — all anchors come from `SEMANTIC_ANCHOR_SPEC_V1.md §I.1` (19 namespaces incl. 4 @lesson subtypes) + F.6.5 forward-projection meta-anchor. **No freeform anchors.**

### §G.6.3 — Codeblock syntax discipline

Fully-developed TPLs (TPL-1, TPL-6) MUST use:
- ```` ```prompt ```` for prompt body (system + user)
- ```` ```json ```` for expected output schema (`$schema` + `type` + `required` + `properties`)
- Draft JSON Schema (draft-07) — universally supported

Fenced blocks enable `tests_09/test_prompt_templates.py` (planned Phase G.1.5) to regex-extract schema for closed-vocab validation.

### §G.6.4 — Cardinality invariants recap

| Field | Cardinality | If violated |
|---|---|---|
| Template ID | exactly 1 | card invalid — re-locate in F's CAP-N header |
| Canonical Entity | exactly 1; = F's row 1 | card invalid — drift from F |
| Execution Target | exactly 1 (CLI OR `[PLANNED ...***REMOVED***` prefixed) | card invalid |
| Validation Anchors | ≥1 `@test` OR annotated "tests pending" | card → §G.8 (no test surface) |
| Layer 3 Wiring | exactly 1 Artifact E query method | card wobbly — promote or demote |
| Blueprint Role | exactly 1 (forward-projected until role resolvers launched) | card ok — exempt by F.6.5 |

---

## §G.7 — Sample Executable Trace (CAP-1 forge.execution)

A complete end-to-end trace showing how an agent uses **G.4 TPL-1** to execute a Forge chain. References F's CAP-1 + E's query API.

```
[AGENT invocation***REMOVED***
  - Reads TPL-1 from G.4
  - Reads F's CAP-1 (10 AGENT-RETURNS rows)
  - Reads C's #1 forge.execution contract
  ↓
[Layer 3 wiring step***REMOVED***
  - Calls E::shortest_path(@entity forge.facade, @test test_run_chain) → returns
        [@entity forge.facade → @entity scenario.registry → @entity memory.store → @test test_run_chain***REMOVED***
  - Calls E::enforces(@entity forge.facade) → returns
        [@lesson CON-052 atomic write***REMOVED***
        [@lesson ANTI-06b closed --mode vocabulary***REMOVED***
  ↓
[CLI invocation per TPL-1 row 6***REMOVED***
  $ python scripts_01/forge.py chain partner_id --mode forge --json
  ↓
[Output validation per TPL-1 row 10***REMOVED***
  Parse stdout JSON → check required keys (slug/mode/started_at/...)
  Check status ∈ {ok, failed, partial***REMOVED***
  Check stages[***REMOVED*** non-empty
  ↓
[Side-effect validation per F's row 8***REMOVED***
  Verify @event forge.chain_started published
  Verify @event forge.stage_completed per stage
  Verify @event forge.chain_completed OR @event forge.chain_failed
  ↓
[Layer 3 verification***REMOVED***
  - E::subgraph({@entity forge.facade***REMOVED***, depth=2) → check no NEW @decision SUPERSEDES the chain result
  ↓
[Return payload to caller***REMOVED***
  → Returns JSON conforming to TPL-1's expected_output_schema
  → On failure: invoke TPL-1 row 8 Fallback Strategy
```

---

## §G.8 — Open Items

1. **TPL-2 / TPL-3 test coverage** — pending Phase 1 vertical slice per `pompts_11/079_19_factory_registry.md`; matches F.4 CAP-2/CAP-3 forward-projection.
2. **Blueprint Role resolution** — All 10 TPLs forward-project `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED***` until `core_02/blueprint_v3.py` exposes resolvable role functions. Same lifecycle as F.6.5 CAP-2/CAP-3.
3. **`tests_09/test_prompt_templates.py`** — Phase G.1.5: validate fenced ```` ```prompt ````/```` ```json ```` block syntax + numeric-prefixed field stability across all 10 TPLs.
4. **Scenarios / chains / traces** — TPL-7 (scenario.resolution) needs empirical validation against `runtime_05/scenarios/*.yaml` once `core_02/scenario_registry.py::list_scenarios` exposes `vertical` filter.
5. **Layer-3 wiring edge cases** — `subgraph({large_set***REMOVED***, depth=2)` may yield >100 nodes; agents must implement early-truncation (currently unhandled — Phase G.1.5).
6. **Open-coded fallback grep** (TPL-6 row 9) — fallback `grep -r` for memory.search drift detection is intentional but should migrate to `@entity semantic.layer` query once Phase G.1.5 completes.

---

## §G.9 — Operator Handoff / Checklist

This artifact is **CLOSED** when all of the following hold:

- [x***REMOVED*** §G.1 first-slice justified (10 TPL cards = 1:1 with F's CAP-1..CAP-10; 2 fully-developed exemplars + 8 compact)
- [x***REMOVED*** §G.2 10-field schema declared (numeric-prefixed, closed-vocab, deterministic)
- [x***REMOVED*** §G.3 storage format declared (pure Markdown + fenced ```` ```prompt ````/```` ```json ```` blocks; no `.yaml`/`.py` instances at this slice)
- [x***REMOVED*** §G.4 all 10 TPL cards present (TPL-1 + TPL-6 with full prose + JSON Schema; TPL-2..5,7..10 compact)
- [x***REMOVED*** §G.5 cross-reference topology diagram (A+B+I+C+D+E+F → G → H + prompt_dispatcher + wizard_lib)
- [x***REMOVED*** §G.5.1 edge-by-edge coupling table (10 rows × upstream/downstream columns)
- [x***REMOVED*** §G.6 schema discipline (10 numeric-prefixed labels + closed-vocab anchors + codeblock discipline + cardinality recap)
- [x***REMOVED*** §G.7 sample executable trace (TPL-1 forge.execution end-to-end)
- [x***REMOVED*** §G.8 open items enumerated with Phase G.1.5 / Phase H owners
- [x***REMOVED*** Footer integrity: cardinality, upstream_count, exemplar_count, status_summary
- [x***REMOVED*** consistency_check passes (no broken anchors / cross-refs)
- [x***REMOVED*** No code modifications (read-only artifact, per `core_02/LESSONS.md ANTI-5`)

---

## Footer

- **Artifact:** G `AGENT_PROMPT_TEMPLATES_V1.md`
- **Upstream truth (6):** A (entities), B (docs), I (anchors), C (contracts), D (ADRs+lessons), E (graph), F (CAPABILITY slugs)
- **First-slice template count:** 10 (TPL-1..TPL-10)
- **Fully-developed exemplars:** 2 (TPL-1 forge.execution, TPL-6 memory.search)
- **Compact templates:** 8 (TPL-2, TPL-3, TPL-4, TPL-5, TPL-7, TPL-8, TPL-9, TPL-10)
- **Forward-projected (gated by Phase G.1.5):** all 10 Blueprint Role fields (`@role orchestrator` / `analyst` / `archivist` / `validator` / `wizard` / `distributor`) under `[PLANNED Phase G.1.5 per pompts_11/077_02_prompt_architect_intelligence_factory.md***REMOVED***`
- **Forward-projected (gated by Phase 1):** TPL-2 + TPL-3 Execution Target under `[ACTIVE v5.188.2 (Missing Cap #1 closed)***REMOVED***` (matches F.6.5)
- **Status:** v1.0 FIRST SLICE — read-only, awaiting Phase H consumption
- **Updated:** 2026-08-12 (Workspace OS freeze between Phase F close and Phase G open)
- **Doctrine:** additive only (no overwrite of upstream artifacts per `core_02/LESSONS.md ANTI-5`)
