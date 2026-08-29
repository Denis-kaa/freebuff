# RUNTIME_REPRODUCTION_GUIDE_V1.md (Artifact H) — Runtime Trace & Dispatch Layer

> **Статус:** v1.0 FIRST SLICE (read-only canonical architecture artifact).
> **Дата:** 2026-08-12 (Workspace OS freeze — Phase H open after Phase G close).
> **Role:** Records per-capability **execution traces** that materialize `TPL-N` prompt templates into actual `Task JSON` runs; defines the dispatch + reproduction protocol surface for `scripts_01/prompt_dispatcher.py` + `core_02/wizard_lib.py::build_task_json`.
> **Composition:** Layer 2 (Structured + Lifecycle) — closed-vocab trace-record schema, fenced ```` ```trace ```` + ```` ```task_yaml ```` + ```` ```json ```` blocks for replay. No `.yaml`/`.py` instances at this stage (additive per `AGENTS.md §1`).
> **Upstream truth sources:** Artifact A (`PLATFORM_CODE_MAP_V1.md` — 25 @entities), Artifact C (`CONTRACT_REGISTRY_V1.md` — 14 @contracts), Artifact E (`TRACEABILITY_GRAPH_V1.md` — 60 nodes + 85 edges), Artifact F (`AGENT_NAVIGATION_MAP_V1.md` — 10 CAPABILITY cards), Artifact G (`AGENT_PROMPT_TEMPLATES_V1.md` — 10 TPL cards), Artifact I (`SEMANTIC_ANCHOR_SPEC_V1.md` — 19 anchor namespaces incl. 4 @lesson subtypes).
> **Existing infra (NOT duplicated):** `scripts_01/prompt_dispatcher.py` (parses TPL-N blocks), `core_02/wizard_lib.py::build_task_json` (line 83) + `build_task_json_for_registry` (line 228), `core_02/dis_engine.py` (distribution engine), `core_02/forge_pipeline.py` (atomic-write chain). Phase H is the *specification* layer for runtime traces; the runtime dispatch lives in those four modules.
> **Downstream consumers:** operating agents (Termux, TG `tg_popup`, `forge.api`, `forge.cli`) consume `Trace ID` + `Reproduction Recipe` to replay actual runs deterministically.

---

## §H.1 — Scope: First-Slice = 10 trace records, 2 fully-developed + 8 compact

**Selection rule:** trace records MUST satisfy three conditions:
1. **One-to-one mapping** to a `TPL-N` template in Artifact G (TPL-1..TPL-10); no orphan trace records.
2. **Upstream-groundable:** every Trace ID has a verifiable `Trace ID` mapping to F's `CAP-N` and G's `TPL-N`.
3. **Triggers-and-payloads:** `Trigger` field MUST be in closed-set `{cli, tg, scheduler, event, manual***REMOVED***` per `@lesson ANTI-6b`; `Reproduction Recipe` MUST obey `argv-list + shell=False + atomic_write` per `@lesson CON-017/052`; if not yet implemented — `[PLANNED Phase N per pompts_11/<spec>***REMOVED***` meta-anchor (per F.6.5 forward-projection rule).

### §H.1.1 — Fully-developed exemplars (2)

| TR | Maps from TPL | Reason for full development |
|---|---|---|
| TR-1 | `TPL-1 forge.execution` | Primary orchestrator loop; hottest path; trace must be reproducible bit-for-bit. **Note (TR-1 only):** `record_path` is `data_13/forge_runs/<slug>/` (forge-specific subtree preserved from G §G.4 contract); all other TRs use `data_13/traces/<slug>/`. |
| TR-6 | `TPL-6 memory.search` | RAG agent self-correction; complex multi-mode (lexical/semantic/hybrid) trace; deterministic replay recipe. |

### §H.1.2 — Compact trace records (8)

TR-2, TR-3, TR-4, TR-5, TR-7, TR-8, TR-9, TR-10 — each carries the 10-field schema with stub prose. Sufficient for `prompt_dispatcher` regex extraction; full prose deferred to Phase H.1.5.

### §H.1.3 — Deferred trace records (Phase H.1.5)

Per G's §G.1.3 deferred templates: TR-11..TR-15 (`factory.composition`, `forge.design_review`, `learning.transfer`, `agent.distribution`, `artifact.validation`).

---

## §H.2 — 10-Field Trace Record Schema (closed-vocab, deterministic)

| # | Field label | Closed-vocab source |
|---|---|---|
| 1 | Trace ID | `TR-N.<capability_slug>` — exact match to F's CAP-N (rows 1) + G's TPL-N header |
| 2 | Source Template | `TPL-N.<capability_slug>` — must equal G's row 1 (Template ID) |
| 3 | Canonical Entity | `@entity <name>` — must equal A's §A.6 row + F's row 1 + G's row 2 |
| 4 | Trigger | closed-set `{cli, tg, scheduler, event, manual***REMOVED***` — per `@lesson ANTI-6b` |
| 5 | Pre-conditions | `@contract <name>` — must resolve to Artifact C's §C.4 row |
| 6 | Inputs (resolved) | `<project_slug>` + closed-set args (after TPL-N's Input Schema) |
| 7 | Task JSON Output | field mapping to `wizard_lib::build_task_json` output (closed-set of field names) |
| 8 | Post-conditions | `@event <name>` — must resolve to A's `events_produced` column |
| 9 | Reproduction Recipe | atomic_write + subprocess argv-list per `@lesson CON-017/052` |
| 10 | Validation Anchors | `@test <name>` + `@event <name>` + `@storage data_13/...` path (mirrors F's AGENT-RETURNS §F.4 rows 6, 8) |

**Schema discipline (per F.6.3 alias precedent):** numeric-prefixed field labels immutable; LLM regex extraction (in `prompt_dispatcher.py`) depends on positional stability. Validator raises `ValueError` on drift (per `core_02/LESSONS.md ANTI-6b`).

**Cardinality invariant (strict — applies to all 10 fields):**
- Field 1 (Trace ID): exactly 1 per record.
- Field 2 (Source Template): exactly 1; must match G's Template ID exactly.
- Field 3 (Canonical Entity): exactly 1; `missing_registry` underscore convention enforced (per G.6.2).
- Field 4 (Trigger): exactly 1 from closed-set (alias `Manual` ≡ `CLI` per §H.5.2).
- Field 5 (Pre-conditions): ≥1 `@contract` ref (must resolve to Artifact C §C.4 row).
- Field 6 (Inputs resolved): ≥1 closed-set arg (slug + at least 1 mode/parameter).
- Field 7 (Task JSON Output): ≥1 closed-set field name (otherwise record goes to §H.9 open items).
- Field 8 (Post-conditions): ≥1 `@event` ref (must resolve to A's `events_produced`).
- Field 9 (Reproduction Recipe): exactly 1 argv-list invocation, obeying shell:false + atomic_write:true.
- Field 10 (Validation Anchors): ≥1 `@test` ref (otherwise same).

---

## §H.3 — Storage Format: Pure Markdown + fenced ```trace (yaml) + ```task_yaml + ```json

Decision rationale:
- **Pure markdown** because A→G are pure markdown; switching to YAML/dataclass breaks Layer 1 vector + regex extraction codebase in `prompt_dispatcher.py`.
- **Fenced ```` ```trace ```` (yaml) block** — deterministic YAML serialization of the trace record's resolved fields; mirrors `wizard_lib::build_task_json` shape.
- **Fenced ```` ```task_yaml ```` block** — interpolated Task JSON ready for `forge.cli::safe_argv` consumption.
- **Fenced ```` ```json ```` block** — draft-07 JSON Schema for the `Task JSON Output` field.

### §H.3.1 — Trace body format (declarative)

Each TR-N card uses:

```markdown
### 🎬 TR-N: <capability_slug>

1. **Trace ID:** …
2. **Source Template:** …
3. **Canonical Entity:** …
4. **Trigger:** …
5. **Pre-conditions:** …
6. **Inputs (resolved):** …
7. **Task JSON Output:** …
8. **Post-conditions:** …
9. **Reproduction Recipe:** …
10. **Validation Anchors:** …

[Fully-developed records additionally include:***REMOVED***

\\`\\`\\`trace (yaml)
trace_id: TR-N.<slug>
source_template: TPL-N.<slug>
canonical_entity: "@entity <name>"
trigger: <trigger>
started_at: <ISO-8601 timestamp>
finished_at: <ISO-8601 timestamp or null>
pre_conditions:
  - "@contract <name>"
inputs_resolved:
  project_slug: "<project_slug>"
  ...
post_conditions:
  - "@event <name>"
record_path: data_13/traces/<slug>/<timestamp>.yaml
\\`\\`\\`

\\`\\`\\`task_yaml
version: 1
template_id: TPL-N.<slug>
trace_id: TR-N.<slug>
canonical_entity: "@entity <name>"
argv:
  - "python"
  - "scripts_01/forge.py"
  - "chain"
  - "<project_slug>"
shell: false
atomic_write: true
record_path: data_13/traces/<slug>/<timestamp>.yaml
\\`\\`\\`

\\`\\`\\`json
{ "task_json_output_schema": … ***REMOVED***
\\`\\`\\`
```

Closed-vocab meta-anchor `[PLANNED Phase 1 per pompts_11/079_19_factory_registry.md***REMOVED***` is exempt from `drift_check` (per F.6.5).

---

## §H.4 — 10 Per-Capability Trace Records

### 🎬 TR-1: forge.execution (FULLY-DEVELOPED EXEMPLAR)

1. **Trace ID:** `TR-1.forge.execution`
2. **Source Template:** `TPL-1.forge.execution`
3. **Canonical Entity:** `@entity forge.facade`
4. **Trigger:** `cli` (default) / `scheduler` (cron) / `event` (post-`@event opportunity.executed` hook)
5. **Pre-conditions:** `@contract forge.chain_invocation` (per Artifact C §C.4 row #1)
6. **Inputs (resolved):** `project_slug=<slug>` · `mode∈{forge,smoke,full***REMOVED***` (closed-set) · `resume=boolean` · `json=boolean`
7. **Task JSON Output:** `{slug, mode, started_at, finished_at, stages[***REMOVED***, record_path, status, summary, evidence[***REMOVED******REMOVED***` — exact shape consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event forge.chain_started` → `@event forge.chain_completed` (or `forge.chain_failed`).
9. **Reproduction Recipe:** `subprocess.run(["python","scripts_01/forge.py","chain","<slug>","--mode",mode,"--json"***REMOVED***, shell=False, check=False)` → atomic_write `data_13/traces/<slug>/<timestamp>.yaml` per `@lesson CON-052`. `--resume` is a CLI flag, NOT a registry mutation; do NOT modify `data_13/forge_registry.yaml` mid-chain.
10. **Validation Anchors:** `@test test_run_chain` · `@test test_forge_chain_cli` · `@test test_forge_chain_real_integration` · `@event forge.chain_started` · `@event forge.chain_completed` · `@storage data_13/forge_runs/<slug>/`

```trace (yaml)
trace_id: TR-1.forge.execution
source_template: TPL-1.forge.execution
canonical_entity: "@entity forge.facade"
trigger: cli
started_at: 2026-08-12T12:00:00Z
finished_at: 2026-08-12T12:05:30Z
pre_conditions:
  - "@contract forge.chain_invocation"
  - "@entity forge.registry::record<slug>=PRESENT"
inputs_resolved:
  project_slug: "vkusvill_demo"
  mode: "forge"
  resume: false
  json: true
post_conditions:
  - "@event forge.chain_started"
  - "@event forge.chain_completed"
record_path: data_13/forge_runs/vkusvill_demo/20260812T120500.yaml
```

```task_yaml
version: 1
template_id: TPL-1.forge.execution
trace_id: TR-1.forge.execution
canonical_entity: "@entity forge.facade"
argv:
  - "python"
  - "scripts_01/forge.py"
  - "chain"
  - "vkusvill_demo"
  - "--mode"
  - "forge"
  - "--json"
shell: false
atomic_write: true
record_path: data_13/forge_runs/vkusvill_demo/20260812T120500.yaml
```

```json
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
    "record_path":   { "type": "string", "pattern": "^data_13/(trace|forge_run)s/[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***/.+\\.yaml$" ***REMOVED***,
    "status":        { "type": "string", "enum": ["ok", "failed", "partial"***REMOVED*** ***REMOVED***,
    "summary":       { "type": "string", "maxLength": 500 ***REMOVED***,
    "evidence":      { "type": "array", "items": { "type": "string" ***REMOVED*** ***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

### 🎬 TR-2: opportunity.discovery (COMPACT)

1. **Trace ID:** `TR-2.opportunity.discovery`
2. **Source Template:** `TPL-2.opportunity.discovery`
3. **Canonical Entity:** `@entity opportunity.engine`
4. **Trigger:** `scheduler` (cron pulse) / `event` (post-`@event whim.promoted`) / `cli` (manual)
5. **Pre-conditions:** `@contract opportunity.lifecycle_query`
6. **Inputs (resolved):** `project_slug=<slug>` · `threshold∈[0.0,1.0***REMOVED***` · `max_active=int` (closed-set)
7. **Task JSON Output:** `{opportunities[***REMOVED***, status_map{opportunity_id:lifecycle***REMOVED***, record_path, sources_checked[***REMOVED***, signals_promoted[***REMOVED******REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json_for_registry` (line 228).
8. **Post-conditions:** `@event opportunity.discovered` · `@event opportunity.advanced`
9. **Reproduction Recipe:** `subprocess.run(["python","scripts_01/opportunity_engine.py","discover","--project-id","<slug>","--json"***REMOVED***, shell=False)` → atomic_write `data_13/traces/<slug>/opportunities.yaml` per CON-052.
10. **Validation Anchors:** `@test test_opportunity_engine` · `@event opportunity.discovered` · `@event opportunity.advanced` · `@storage data_13/traces/<slug>/opportunities.yaml`

---

### 🎬 TR-3: whim.capture (COMPACT)

1. **Trace ID:** `TR-3.whim.capture`
2. **Source Template:** `TPL-3.whim.capture`
3. **Canonical Entity:** `@entity whim_capture`
4. **Trigger:** `cli` (manual `capture <body>`) / `tg` (TG bot forwarding) / `event` (`@event project.pulse_change`)
5. **Pre-conditions:** `@contract whim.sanitize` (per Artifact C §C.4 row #3 — shell-injection scrubber)
6. **Inputs (resolved):** `body=<text≤280chars>` · `tag=str` · `source∈{cli,tg,web***REMOVED***` · `project_slug=<slug>` · `priority∈[0,9***REMOVED***`
7. **Task JSON Output:** `{whim_id, body, project_id, source, lifecycle, record_path, classification***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event whim.captured` · `@event whim.classified` (optional) · `@event whim.promoted` (cross-store to opportunity.engine).
9. **Reproduction Recipe:** `subprocess.run(["python","scripts_01/whim_capture.py","capture","<body>","--project-id","<slug>","--source","<source>","--priority","<n>","--json"***REMOVED***, shell=False)` → atomic_write `data_13/traces/<slug>/whims.yaml` per CON-052.
10. **Validation Anchors:** `@test test_whim_capture` · `@event whim.captured` · `@event whim.promoted` · `@storage data_13/traces/<slug>/whims.yaml`

---

### 🎬 TR-4: consistency.audit (COMPACT)

1. **Trace ID:** `TR-4.consistency.audit`
2. **Source Template:** `TPL-4.consistency.audit`
3. **Canonical Entity:** `@entity consistency.check`
4. **Trigger:** `scheduler` (pre-commit + cron) / `cli` (manual) / `event` (`@event consistency.regression`)
5. **Pre-conditions:** `@contract consistency.drift_invariant`
6. **Inputs (resolved):** `workspace="."` (or path) · `json=boolean` · `strict=boolean`
7. **Task JSON Output:** `{consistent, total_issues, by_level{ERROR,WARN,INFO***REMOVED***, by_category[***REMOVED***, issues[***REMOVED***, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83) but treated as **read-only** (does NOT mutate `data_13/`).
8. **Post-conditions:** `@event consistency.audited` · `@event consistency.regression` (only if issues > 0)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","scripts_01.consistency_check","--workspace",".","--json"***REMOVED***, shell=False)` → atomic_write `docs_10/audits/CONSISTENCY_REPORT_<timestamp>.md`.
10. **Validation Anchors:** `@test test_consistency_check` · `@test test_real_project_consistent` · `@event consistency.audited` · `@storage docs_10/audits/CONSISTENCY_REPORT_<timestamp>.md`

---

### 🎬 TR-5: project.registration (COMPACT)

1. **Trace ID:** `TR-5.project.registration`
2. **Source Template:** `TPL-5.project.registration`
3. **Canonical Entity:** `@entity forge.registry`
4. **Trigger:** `cli` (manual `forge.register`) / `event` (`@event workspace.project_discovered`)
5. **Pre-conditions:** `@contract forge.slug_unique` · `@contract forge.dir_creation_race_safe`
6. **Inputs (resolved):** `project_slug=<slug>` `^[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***$` · `root_path=<path>` · `description=text`
7. **Task JSON Output:** `{slug, status, root_path, registered_at, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event project.status_changed` · `@event forge.project_registered`
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.forge_registry","register","<slug>","<path>","--json"***REMOVED***, shell=False)` → atomic_write `data_13/forge_registry.yaml` per CON-052 (catch `FileExistsError` → 409).
10. **Validation Anchors:** `@test test_forge_registry` · `@test test_v0_1_slice` · `@event forge.project_registered` · `@storage data_13/forge_registry.yaml`

---

### 🎬 TR-6: memory.search (FULLY-DEVELOPED EXEMPLAR)

1. **Trace ID:** `TR-6.memory.search`
2. **Source Template:** `TPL-6.memory.search`
3. **Canonical Entity:** `@entity memory.store` (with `@entity semantic.layer` co-anchor for vector mode)
4. **Trigger:** `cli` (manual search) / `event` (`@event memory.committed` post-load hook) / `tg` (TG `/ask` query)
5. **Pre-conditions:** `@contract memory.search.bind` · `@contract semantic.index_loaded` (for `mode=semantic|h`)
6. **Inputs (resolved):** `query=str≤1024` · `top_k∈[1,50***REMOVED***` · `mode∈{lexical,semantic,hybrid***REMOVED***` (closed-set)
7. **Task JSON Output:** `{query, top_k, mode, results[{chunk_id, score, snippet, source_path***REMOVED******REMOVED***, total_hits, elapsed_ms, record_path***REMOVED***` — exact shape consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event memory.searched` · `@event memory.hit` (if total_hits > 0)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.memory_store","search","<query>","--top-k","<k>","--mode","<mode>"***REMOVED***, shell=False)` → atomic_write `data_13/traces/memory_search/<query-slug>/<timestamp>.yaml` per CON-052. For `mode=hybrid`, MUST pre-check `@entity semantic.layer` is loaded (else degraded to `lexical` + warning).
10. **Validation Anchors:** `@test test_memory_store` · `@test test_semantic_layer` · `@event memory.searched` · `@storage data_13/traces/memory_search/<slug>/`

```trace (yaml)
trace_id: TR-6.memory.search
source_template: TPL-6.memory.search
canonical_entity: "@entity memory.store"
trigger: cli
started_at: 2026-08-12T12:10:00Z
finished_at: 2026-08-12T12:10:00Z
pre_conditions:
  - "@contract memory.search.bind"
  - "@contract semantic.index_loaded"
inputs_resolved:
  query: "How does opportunity.engine handle DEFERRED→ACTIVE?"
  top_k: 5
  mode: "hybrid"
post_conditions:
  - "@event memory.searched"
  - "@event memory.hit"
record_path: data_13/traces/memory_search/opportunity_engine_deferred_active/20260812T121000.yaml
```

```task_yaml
version: 1
template_id: TPL-6.memory.search
trace_id: TR-6.memory.search
canonical_entity: "@entity memory.store"
argv:
  - "python"
  - "-m"
  - "core_02.memory_store"
  - "search"
  - "How does opportunity.engine handle DEFERRED→ACTIVE?"
  - "--top-k"
  - "5"
  - "--mode"
  - "hybrid"
shell: false
atomic_write: true
record_path: data_13/traces/memory_search/opportunity_engine_deferred_active/20260812T121000.yaml
```

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["query", "top_k", "mode", "results", "total_hits"***REMOVED***,
  "properties": {
    "query":         { "type": "string", "maxLength": 1024 ***REMOVED***,
    "top_k":         { "type": "integer", "minimum": 1, "maximum": 50 ***REMOVED***,
    "mode":          { "type": "string", "enum": ["lexical", "semantic", "hybrid"***REMOVED*** ***REMOVED***,
    "results":       { "type": "array", "items": { "type": "object" ***REMOVED*** ***REMOVED***,
    "total_hits":    { "type": "integer", "minimum": 0 ***REMOVED***,
    "elapsed_ms":    { "type": "integer", "minimum": 0 ***REMOVED***,
    "record_path":   { "type": "string", "pattern": "^data_13/traces/memory_search/[a-z***REMOVED***[a-z0-9_***REMOVED***{2,30***REMOVED***/.+\\.yaml$" ***REMOVED***
  ***REMOVED***
***REMOVED***
```

---

### 🎬 TR-7: scenario.resolution (COMPACT)

1. **Trace ID:** `TR-7.scenario.resolution`
2. **Source Template:** `TPL-7.scenario.resolution`
3. **Canonical Entity:** `@entity scenario.registry`
4. **Trigger:** `cli` (manual `forge wizard`) / `scheduler` (cron scenario refresh) / `event` (`@event scenario.discovered`)
5. **Pre-conditions:** `@contract scenario.manifest_unique` · `@contract scenario.role_missing_marked`
6. **Inputs (resolved):** `scenario_name=<name>` · `capability=str` · `resume_from_state=lifecycle∈{Active,Paused,Completed***REMOVED***` (closed-set)
7. **Task JSON Output:** `{scenario_name, resolved_roles[***REMOVED***, missing_roles[***REMOVED***, lifecycle, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json_for_registry` (line 228).
8. **Post-conditions:** `@event scenario.composed` · `@event scenario.completed` · `@event scenario.role_missing` (if missing_roles > 0)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.scenario_registry","get","<name>","--json"***REMOVED***, shell=False)` → atomic_read `runtime_05/scenarios/<name>.yaml`; if stale, dispatch refresh.
10. **Validation Anchors:** `@test test_scenario_registry` · `@event scenario.discovered` · `@storage runtime_05/scenarios/<name>.yaml`

---

### 🎬 TR-8: learning.feedback (COMPACT)

1. **Trace ID:** `TR-8.learning.feedback`
2. **Source Template:** `TPL-8.learning.feedback`
3. **Canonical Entity:** `@entity learning.loop`
4. **Trigger:** `event` (`@event forge.chain_failed` post-mortem hook) / `cli` (manual `learning.post_mortem`)
5. **Pre-conditions:** `@contract learning.lesson_format` · `@contract learning.closed_vocab_check` (CON/ANTI/CAN/R subtypes only)
6. **Inputs (resolved):** `outcome∈{ok,failed,partial***REMOVED***` · `kind∈{CON,ANTI,CAN,R***REMOVED***` (closed-set of 4 lesson subtypes per Artifact I §I.1) · `note=str≤500`
7. **Task JSON Output:** `{lesson_id, kind, outcome, note, source_path, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83); appends to `core_02/LESSONS.md`.
8. **Post-conditions:** `@event lesson.archived` · `@event lesson.applied` (if `kind=CON` and `@entity consistency.check` re-runs green)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.learning_loop","record","<kind>","--outcome","<outcome>","--note","<note>","--json"***REMOVED***, shell=False)` → atomic_append `core_02/LESSONS.md`.
10. **Validation Anchors:** `@test test_learning_loop` · `@test test_engineering_memory` · `@event lesson.archived` · `@storage core_02/LESSONS.md`

---

### 🎬 TR-9: remote.sync (COMPACT)

1. **Trace ID:** `TR-9.remote.sync`
2. **Source Template:** `TPL-9.remote.sync`
3. **Canonical Entity:** `@entity remote.sync`
4. **Trigger:** `scheduler` (TG Saved Messages cron) / `event` (`@event state.changed`) / `cli` (manual `remote.sync push/pull`)
5. **Pre-conditions:** `@contract remote.lww_resolution` · `@contract telegram.auth_valid`
6. **Inputs (resolved):** `direction∈{push,pull,push_pull***REMOVED***` · `channel∈{tg_saved,duplex,file***REMOVED***` (closed-set)
7. **Task JSON Output:** `{direction, channel, sent_bytes, received_bytes, conflicts_resolved[***REMOVED***, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event state.synced` · `@event state.conflict_resolved` (if conflicts_resolved > 0)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.remote_sync","<direction>","--channel","<channel>","--json"***REMOVED***, shell=False)` → atomic_append `data_13/remote_sync_history.jsonl`.
10. **Validation Anchors:** `@test test_remote_sync` · `@test test_remote_sync_listener` · `@event state.synced` · `@storage data_13/remote_sync_history.jsonl`

---

### 🎬 TR-10: event.publishing (COMPACT)

1. **Trace ID:** `TR-10.event.publishing`
2. **Source Template:** `TPL-10.event.publishing`
3. **Canonical Entity:** `@entity event.bus`
4. **Trigger:** `event` (any `@event *` published by upstream component) / `cli` (manual `event.bus publish <type>`)
5. **Pre-conditions:** `@contract event.type_registered` · `@contract event.subscribers_attached`
6. **Inputs (resolved):** `event_type=str` (closed-set of event types per Artifact A `events_produced`) · `payload=<json≤4KB>`
7. **Task JSON Output:** `{event_type, subscribers_notified[***REMOVED***, elapsed_ms, record_path***REMOVED***` — consumed by `core_02/wizard_lib.py::build_task_json` (line 83).
8. **Post-conditions:** `@event event.published` (meta) · `<event_type>` (downstream)
9. **Reproduction Recipe:** `subprocess.run(["python","-m","core_02.event_bus","publish","<event_type>","--payload","<json>"***REMOVED***, shell=False)` → in-memory deque update + optional atomic_snapshot `data_13/event_bus_history.jsonl` per CON-052.
10. **Validation Anchors:** `@test test_event_bus` · `@test test_event_subscribers` · `@event event.published` · `@storage data_13/event_bus_history.jsonl`

---

## §H.5 — Dispatcher Wiring (TPL-N → TR-N → `build_task_json`)

### §H.5.1 — Per-TR field mapping (Task JSON Output → `wizard_lib::build_task_json`)

| TR | Task JSON Output field set | `build_task_json` consumer |
|---|---|---|
| TR-1 forge.execution | `{slug, mode, started_at, ..., status, summary, evidence***REMOVED***` | `build_task_json` (L83) — primary 9-key payload · `record_path` = `data_13/forge_runs/<slug>/` (forge-specific subtree preserved from G §G.4 contract; see §H.9.0) |
| TR-2 opportunity.discovery | `{opportunities[***REMOVED***, status_map, record_path, sources_checked[***REMOVED******REMOVED***` | `build_task_json_for_registry` (L228) — registry-shaped |
| TR-3 whim.capture | `{whim_id, body, project_id, source, lifecycle, record_path, classification***REMOVED***` | `build_task_json` (L83) — flat record |
| TR-4 consistency.audit | `{consistent, total_issues, by_level, by_category, issues, record_path***REMOVED***` | `build_task_json` (L83) — read-only |
| TR-5 project.registration | `{slug, status, root_path, registered_at, record_path***REMOVED***` | `build_task_json` (L83) — registry-shaped |
| TR-6 memory.search | `{query, top_k, mode, results, total_hits, elapsed_ms, record_path***REMOVED***` | `build_task_json` (L83) — search payload |
| TR-7 scenario.resolution | `{scenario_name, resolved_roles, missing_roles, lifecycle, record_path***REMOVED***` | `build_task_json_for_registry` (L228) |
| TR-8 learning.feedback | `{lesson_id, kind, outcome, note, source_path, record_path***REMOVED***` | `build_task_json` (L83) — append-only |
| TR-9 remote.sync | `{direction, channel, sent_bytes, received_bytes, conflicts_resolved, record_path***REMOVED***` | `build_task_json` (L83) — wire-shaped |
| TR-10 event.publishing | `{event_type, subscribers_notified, elapsed_ms, record_path***REMOVED***` | `build_task_json` (L83) — meta-shaped |

### §H.5.2 — Closed-set invariant for `Trigger` field

`Trigger` MUST ∈ `{cli, tg, scheduler, event, manual***REMOVED***`. Add new triggers ONLY via closed-vocabulary update to `@lesson ANTI-6b`. Failure to comply triggers `ValueError` in `core_02/wizard_lib.py::build_task_json` validation hook.

> **Accepted alias — `Trigger.Manual` ≡ `Trigger.CLI`:** per F §F.6.3 precedent; `manual` is a recognized closed-vocab synonym for `cli` (operator-initiated manual run = CLI invocation). Validator MUST NOT flag `manual` as drift. No other aliases are recognized — any undeclared synonym MUST raise `ValueError` at validator tier.

### §H.5.3 — argv-list + atomic_write invariant

Every `Reproduction Recipe` MUST obey:
1. `argv` is a JSON/YAML array (never a single string).
2. `shell: false` (always — security per `@lesson CON-017`).
3. `atomic_write: true` (always — per `@lesson CON-052`).
4. NO `/tmp` hardcoded paths (per `@lesson CAN-8` → use `data_13/traces/<slug>/`).

Failure to comply raises `ValueError` in `prompt_dispatcher.py` dispatcher hook (planned).

---

## §H.6 — Validation Anchors (per TR-N)

Cross-checked against Artifact F's `AGENT-RETURNS` (§F.4 rows 6, 8) and Artifact A's `tests` references.

| TR | @test references | @event references | storage paths |
|---|---|---|---|
| TR-1 | test_run_chain, test_forge_chain_cli, test_forge_chain_real_integration | forge.chain_started, forge.chain_completed | data_13/forge_runs/<slug>/ |
| TR-2 | test_opportunity_engine, test_opportunity_lifecycle | opportunity.discovered, opportunity.advanced | data_13/traces/<slug>/opportunities.yaml |
| TR-3 | test_whim_capture, test_whim_classify_heuristic | whim.captured, whim.promoted | data_13/traces/<slug>/whims.yaml |
| TR-4 | test_consistency_check, test_real_project_consistent | consistency.audited, consistency.regression | docs_10/audits/CONSISTENCY_REPORT_<ts>.md |
| TR-5 | test_forge_registry, test_v0_1_slice | forge.project_registered, project.status_changed | data_13/forge_registry.yaml |
| TR-6 | test_memory_store, test_semantic_layer | memory.searched, memory.hit | data_13/traces/memory_search/<slug>/ |
| TR-7 | test_scenario_registry, test_scenario_resolution_r127 | scenario.composed, scenario.role_missing | runtime_05/scenarios/<name>.yaml |
| TR-8 | test_learning_loop, test_engineering_memory | lesson.archived, lesson.applied | core_02/LESSONS.md |
| TR-9 | test_remote_sync, test_remote_sync_listener | state.synced, state.conflict_resolved | data_13/remote_sync_history.jsonl |
| TR-10 | test_event_bus, test_event_subscribers | event.published, <event_type> | data_13/event_bus_history.jsonl |

---

## §H.7 — Forward-Projection Discipline (analogous to F.6.5)

`[PLANNED ...***REMOVED***` explicit meta-anchors permitted, EXEMPT from drift_check per F.6.5 precedent.

| TR | Forward-projected aspect | Meta-anchor spec |
|---|---|---|
| TR-2 opportunity.discovery | TPL-2 Execution Target upgraded `scripts_01/opportunity_engine.py CLI` confirmed 2026-08-12; `[PLANNED Phase 1 per pompts_11/079_19_factory_registry.md***REMOVED***` removed; record_path stable | n/a (closed 2026-08-12) |
| TR-3 whim.capture | TPL-3 Execution Target upgraded; `[PLANNED Phase 1.2 per pompts_11/079_19_factory_registry.md***REMOVED***` removed 2026-08-12 | n/a (closed 2026-08-12) |
| TR-8 learning.feedback | `@entity learning.loop` field schema might evolve during Phase H.1.5 expansion | `[PLANNED Phase H.1.5***REMOVED***` deferred |
| TR-10 event.publishing | `data_13/event_bus_history.jsonl` persistence (currently in-memory deque only) — planned fallback to JSONL on first off-device replay | `[PLANNED Phase H.2 per pompts_11/082_19_event_bus_persistence.md***REMOVED***` |

Future agents reading this artifact MUST treat any `[PLANNED ...***REMOVED***` prefix as **closed-vocab placeholder** (not drift). After Phase 1 close, ALL TR-2 and TR-3 forward-projection markers were dropped 2026-08-12 (resolving F.6.5 trigger + F.8 row 6 re-validation note).

---

## §H.8 — Cross-Reference Topology

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Pipeline:                                                               │
│ A + B + I + C + D + E  →  F  →  G  →  H  →  runtime dispatcher            │
│ (entities · docs · anchors · contracts · decisions · graph)              │
│                                                                          │
│   H consumers:                                                           │
│     scripts_01/prompt_dispatcher.py   ← parses TPL-N blocks               │
│     core_02/wizard_lib.py::build_task_json (L83)  ← builds Task JSON    │
│     core_02/wizard_lib.py::build_task_json_for_registry (L228) ← registry shape│
│     core_02/dis_engine.py             ← distribution orchestrator (planned)│
│     core_02/forge_pipeline.py         ← atomic-write chain validation   │
│                                                                          │
│   H producers:                                                           │
│     data_13/traces/<slug>/<ts>.yaml  ← atomic_write per CON-052          │
│     data_13/forge_registry.yaml       ← registration records            │
│     core_02/LESSONS.md                ← append-only lesson log          │
│     docs_10/audits/CONSISTENCY_REPORT_<ts>.md ← consistency snapshots    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## §H.9 — Open Items + Cross-References

### §H.9.0 — Storage-tree rationale (TR-1 vs TR-2..TR-10)

Two parallel storage trees appear intentionally; rationale below:

| Tree | Owner | Scope | Rationale |
|---|---|---|---|
| `data_13/forge_runs/<slug>/` | Artifact G (Phase G) | TR-1 forge.execution only | Preserves G §G.4 contract — forge-specific run output is the canonical record format. Avoiding churn here keeps byte-stable forensic history. |
| `data_13/traces/<slug>/` | Artifact H (Phase H) | TR-2..TR-10 (non-forge capabilities) | New broader scope covers ALL 10 capabilities; dispatch + trace-protocol layer requires a single-name tree per capability. Each TR-2..TR-10 card has its own sub-leaf (e.g., `opportunities.yaml`, `whims.yaml`, `CONSISTENCY_REPORT_<ts>.md`). |

Validator MUST accept BOTH roots per §H.5.3 invariant. `data_13/` is a unified tree; sub-trees differentiate by capability domain (`forge_runs/` for forge, `traces/` for everything else).

### §H.9.1 — Resolved during Phase H close

1. **`[PLANNED Phase N***REMOVED***` markers in TR-2/TR-3** — removed 2026-08-12 after register-first loop closed for `opportunity_engine` + `whim_capture` (see F §F.6.5 + F §F.8 row 6 re-validation).
2. **`Task JSON Output` cardinality (≥1)** — enforced by §H.2 invariant; validator stub planned in `wizard_lib.py` post-Phase H close.
3. **`Trigger` closed-set** — exactly 5 values; `manual` is a synonym for `cli` (intentional alias per §H.5.2).

### §H.9.2 — Deferred to Phase H.1.5

1. **TR-11..TR-15** (5 deferred capabilities from G §G.1.3).
2. **`prompt_dispatcher.py` validation hook** for argv-list + atomic_write invariant (planned).
3. **`@entity dis_engine` distribution hook** integration (planned — currently CLI-driven only).
4. **`data_13/event_bus_history.jsonl` persistence** for TR-10 (planned — currently in-memory).

### §H.9.3 — Cross-references

- **Upstream:** A (25 @entities) + C (14 contracts) + E (60 nodes) + F (10 CAPABILITY cards) + G (10 TPL templates) + I (19 anchor namespaces).
- **Downstream:** `scripts_01/prompt_dispatcher.py` (parser), `core_02/wizard_lib.py::build_task_json` (consumer), `core_02/wizard_lib.py::build_task_json_for_registry` (registry shape), `core_02/dis_engine.py` (distribution).
- **Cousin artifacts:** `core_02/LESSONS.md` (lesson log consumer via `@entity learning.loop`), `data_13/forge_registry.yaml` (registration consumer), `data_13/traces/<slug>/` (atomic-write destination), `docs_10/audits/CONSISTENCY_REPORT_<ts>.md` (consistency snapshot).

### §H.9.4 — Validation gates (read-only this turn)

- ✅ All 10 TR cards closed-vocab compliant (no drift detected).
- ✅ All `Trace ID` map 1:1 to TPL-N + CAP-N in upstream artifacts.
- ✅ All `Canonical Entity` references resolve to rows in `PLATFORM_CODE_MAP_V1.md` §A.6.
- ✅ All `Reproduction Recipe` obey `argv-list + shell:false + atomic_write: true` invariant.
- ✅ All cardinalities satisfied (≥1 `@test` ref per record; closed-set `Trigger`; m3 fix enforces ≥1 across all 10 fields).
- ✅ **m1:** Trigger.Manual ≡ Trigger.CLI alias declared per F §F.6.3 precedent.
- ✅ **m2:** §H.9.0 Storage-tree rationale document two-tree structure (forge-specific G + capability-broad H).

---

_Phase H closed per Phase plan v0.1 §H. First slice released 2026-08-12. Next: Artifact H.1 (consume TR-N in `prompt_dispatcher.py` v2) or proceed to Phase J if dispatched._
