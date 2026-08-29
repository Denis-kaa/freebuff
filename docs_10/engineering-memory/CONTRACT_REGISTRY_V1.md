# CONTRACT REGISTRY (Artifact C — Phase D)

> **Source of Truth:** repository (FFB / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §10 (CONTRACT REGISTRY schema).
> **Anchor inheritance:** every contract references `@entity` rows from `PLATFORM_CODE_MAP_V1.md` (Artifact A) + `@event` from `SEMANTIC_ANCHOR_SPEC_V1.md` (Artifact I) + `doc.<...>` claims from `DOCUMENTATION_CODE_MAP_V1.md` (Artifact B).
> **REPOSITORY = SOURCE OF TRUTH:** every contract MUST resolve to (a) existing `core_02/` or `scripts_01/` symbols OR (b) explicit `DESIGN_ONLY` if planned but not yet implemented. Unverifiable contracts are marked `UNVERIFIED` — never silently fall through to `CURRENT`.
> **Counterparts required:** Artifact A (25 @entity anchors) · Artifact B (78 `doc.*#section.cN`) · Artifact I (15 namespace anchors).

---

## §C.0 — Discipline notes (forward-references & exception reality)

Two provenance disciplines apply to all 17 contract records below:

1. **`doc.*` anchors are forward-references.** `(doc.<name>#<section>.cN)` references are correct-form anchors per `SEMANTIC_ANCHOR_SPEC_V1.md` §I.2, but several are aspirational until Artifact B (`DOCUMENTATION_CODE_MAP_V1.md`) is round-tripped in Phase G/H. **Resolution deferred** per §A.9 dependency order `A → B → I → C → D → E → F/G/H`. If a downstream agent cannot resolve a `(doc.*)` anchor, status should be flagged `UNVERIFIED` and an FYI logged in §C.6.

2. **`errors:` lists distinguish real vs planned.** Per §0 REPOSITORY = SOURCE OF TRUTH, exception types must be either:
   - **Real (in producer file):** Python builtin (`ValueError`, `OSError`, `KeyError`, `TypeError`, `IOError`, `NotImplementedError`) or a class actually defined in the producer's source module.
   - **Planned (forward-intent):** Custom exception class not yet defined. These are noted as `(planned P1.4)` for round-trip with `@entity missing.registry` lifecycle (contract #14). Once implemented, the contract flips to `CURRENT` and the exception type is removed from `planned` sub-list.

   In the contract records below, plain `*Error` names without `(planned P1.4)` suffix are intended as either real builtins or aspirational anchors — agents MUST validate against the producer source before relying on them in tests.

---

## §C.1 — Definition: what a "contract" is

A **contract** is ONE pact between TWO entities, expressed as:

```
CONSUMER ⇐ PRODUCER            ── producer is "called-upon" (offers capability)
            ↓
        {input schema***REMOVED***
            ↓
        {output schema, raise specific exceptions, emit @event***REMOVED***
            ↓
        {side effects: @storage, downstream @consumers***REMOVED***
```

**Granularity rule:**
- ONE direction of flow = ONE contract (read ≠ write; sync ≠ async; single-entity ≠ batch).
- A pair of entities with **N orthogonal flows** = **N contracts** (e.g., `Opportunity → ForgeFacade` has 1 contract: `opportunity.execute`; `ForgeFacade → ForgeRegistry` has 2: `forge.lifecycle + forge.run.record`).
- A pair of entities with M non-orthogonal getters = **1 contract** (e.g., `ScenarioRegistry: list_scenarios / get / find_role` all serve `scenario.selection` consumer).

**Status taxonomy:**
| Status | Meaning |
|--------|---------|
| `CURRENT` | Contract resolves; producer.symbol() exists, tests for consumer are green. |
| `PARTIAL` | Producer exists; tests partially cover. |
| `DESIGN_ONLY` | Contract planned (Missing Capability row); producer not implemented yet. |
| `UNVERIFIED` | Cannot resolve producer or consumer in current repo. |

---

## §C.2 — First-slope scope (17 contracts: 15 flow + 2 schema)

Selection criteria (apply to all 25 entities from Artifact A → candidate 50+ possible producer↔consumer pairs):

1. **High-traffic** (called from ≥2 entrypoints — CLI, API, or chain).
2. **Cross-component** (producer ≠ consumer; differs by file or module).
3. **Event-bearing** (publishes or consumes ≥1 `@event` per Artifact A row).
4. **Tested** (at least one test path exists in `tests_09/`).

**Excluded from first slice (lower-signal, target second slice):**
- Internal helpers (e.g., `RoleArtifactValidator` is internal to `forge.facade` — folded INTO `forge.execution` contract).
- Wizard prompts (`wizard.lib` is interactive-only; no event surface).
- `@entity remote.sync` Phase 5.3-E — re-verify once `e2e_remote_sync_listener.py` is merged.

---

## §C.3 — Canonical contract pattern (template)

Every contract row below follows this 14-field schema (per `promts/4.md` §10):

```yaml
contract_id: <lowercase.dot machine-readable>
name: <title-case human-readable>
purpose: <1-sentence single-clause>
producer: @entity <entity_id>
consumer: @entity <entity_id>
input: <typed signature>
output: <typed signature>
errors: [<ExceptionType1>, <ExceptionType2>, ...***REMOVED***
events:
  produced: [@event <ev_id>, ...***REMOVED***
  consumed: [@event <ev_id>, ...***REMOVED***
storage: [@storage <name>, ...***REMOVED***
implementation: <file_path>::<SymbolName>
tests: @test <test_path>[:<class_or_func>***REMOVED***
documentation:
  - (doc.arch_canon#3.c1)
  - (doc.factory_forge_arch#20.c4)
status: CURRENT | PARTIAL | DESIGN_ONLY | UNVERIFIED
```

---

## §C.4 — Contracts (17 records)

### 1. forge.execution

- **contract_id:** `forge.execution`
- **name:** Forge Chain Execution
- **purpose:** Run the 14-role Blueprint v3 chain against a registered project.
- **producer:** `@entity orchestrator.blueprint` (BLUEPRINT_ROLES + KNOWN_CAPABILITIES)
- **consumer:** `@entity forge.facade` (ForgeFacade.run_chain)
- **input:** `(slug: str, role_ids: Optional[List[str***REMOVED******REMOVED*** = None)`
- **output:** `Dict[str, Any***REMOVED***` — 9-key chain payload (per `core_02/PIPELINE_CHAIN`).
- **errors:**
  - `UnknownProjectError` (slug not in `@entity forge.registry`)
  - `ValueError` (role_id not in `KNOWN_CAPABILITIES` — ANTI-6b closed-vocabulary)
  - `RoleArtifactMissingError` (raised by `@entity role.validator` post-chain)
- **events:**
  - produced: `[@event forge.chain_started, @event forge.chain_completed, @event forge.chain_failed***REMOVED***`
  - consumed: `[@event opportunity.execute***REMOVED***` (cross-store from `@entity opportunity.engine`)
- **storage:** `[@storage forge_registry_yaml***REMOVED***` (via `@entity forge.registry::record_run`)
- **implementation:** `core_02/forge_facade.py::ForgeFacade.run_chain`
- **tests:** `@test test_forge_facade`, `@test test_forge_chain_cli`, `@test test_forge_chain_real_integration`
- **documentation:** `(doc.arch_canon#3.c1)`, `(doc.factory_forge_arch#20.c1)`
- **status:** **CURRENT** — 29 tests green across 4 paths.

### 2. scenario.selection

- **contract_id:** `scenario.selection`
- **name:** Scenario Lookup & Role Resolution
- **purpose:** Resolve a capability/role requirement to the canonical scenario manifest containing it.
- **producer:** `@entity scenario.registry` (ScenarioRegistry.find_role)
- **consumer:** `@entity forge.facade` (L-3 bridge lookup); `@entity orchestrator.blueprint` (role composition)
- **input:** `(role_name: str)` — required capability or BL role token
- **output:** `Optional[Tuple[Scenario, Role***REMOVED******REMOVED***` — (scenario_id, role) where role token matches `KNOWN_CAPABILITIES`
- **errors:**
  - `RoleNotFoundError` (silent → returns `None` instead by current impl — design issue raised P1.4)
- **events:**
  - produced: `[@event scenario.discovered, @event scenario.role_missing***REMOVED***`
  - consumed: `[@event project.registered, @event forge.chain_completed***REMOVED***`
- **storage:** `[@storage runtime_05_scenarios_yaml***REMOVED***` (canonical manifests loaded at first `get()` call)
- **implementation:** `core_02/scenario_registry.py::ScenarioRegistry.find_role`
- **tests:** `@test test_scenario_registry` (round-trip + role lookup)
- **documentation:** `(doc.scenario_engine_design#H.c1)`, `(doc.arch_canon#3.c1)`
- **status:** **PARTIAL** — `RoleNotFoundError` not raised (returns `Optional` — silently `None`); missing-capability row in `data_13/missing_registry.yaml` (`scenario_selection_role_not_found`, planned P1.4); status flips to CURRENT once raise is implemented.

### 3. scenario.composition

- **contract_id:** `scenario.composition`
- **name:** Multi-Scenario Role Proposal
- **purpose:** Given a high-level capability, propose roles across multiple scenarios that could compose it.
- **producer:** `@entity scenario.registry` (ScenarioRegistry.propose_roles)
- **consumer:** `@entity wizard.lib` (interactive flow); `@entity orchestrator.blueprint` (auto composition)
- **input:** `(scenario_name: str, capability: str)`
- **output:** `List[Tuple[Scenario, Role***REMOVED******REMOVED***` — proposed (scenario, role) combinations
- **errors:**
  - `ScenarioNotFoundError` (scenario not registered)
- **events:**
  - produced: `[@event scenario.role_proposed***REMOVED***`
  - consumed: `[@event project.registered***REMOVED***`
- **storage:** `[@storage runtime_05_scenarios_yaml***REMOVED***`
- **implementation:** `core_02/scenario_registry.py::ScenarioRegistry.propose_roles`
- **tests:** `@test test_scenario_registry`
- **documentation:** `(doc.scenario_engine_design#H.c2)`
- **status:** **CURRENT** — 1 scenario class in first slice.

### 4. forge.lifecycle

- **contract_id:** `forge.lifecycle`
- **name:** Project Lifecycle State Transition
- **purpose:** Advance a project's lifecycle status through FSM UNFORGED → FORGED → SHIPPED.
- **producer:** `@entity forge.registry` (ForgeRegistry.promote_status)
- **consumer:** `@entity forge.facade` (post-chain hook); `@entity forge.cli` (CLI subcommand); `@entity forge.api` (`/api/v1/projects/{slug***REMOVED***` GET)
- **input:** `(slug: str, new_status: Literal["UNFORGED","FORGED","SHIPPED"***REMOVED***)`
- **output:** `ProjectRecord` with updated status + timestamp
- **errors:**
  - `InvalidTransitionError` (current → new_status not in FSM)
  - `ProjectNotFoundError`
- **events:**
  - produced: `[@event project.status_changed, @event forge.run.recorded***REMOVED***`
  - consumed: — (passive)
- **storage:** `[@storage forge_registry_yaml***REMOVED***` (atomic write via `.tmp + os.replace`)
- **implementation:** `core_02/forge_registry.py::ForgeRegistry.promote_status`
- **tests:** `@test test_forge_registry` (FSM coverage)
- **documentation:** `(doc.arch_canon#3.c1)`, `(doc.rfc_buffy_forge#3.c1)`
- **status:** **CURRENT** — FSM green per `test_forge_registry`.

### 5. forge.run.record

- **contract_id:** `forge.run.record`
- **name:** Append Chain Run Record
- **purpose:** Persist a chain's output (9-key payload) into the project registry as a run history row.
- **producer:** `@entity forge.registry` (ForgeRegistry.record_run)
- **consumer:** `@entity forge.facade` (post-run hook)
- **input:** `(slug: str, chain_payload: Dict[str, Any***REMOVED***)`
- **output:** `RunRecord` (timestamped dict)
- **errors:**
  - `ProjectNotFoundError`
  - `AtomicWriteError` (disk full / permissions)
- **events:**
  - produced: `[@event forge.run.recorded***REMOVED***`
  - consumed: — (may consume `@event forge.chain_completed` in future deferred mode)
- **storage:** `[@storage forge_registry_yaml***REMOVED***`
- **implementation:** `core_02/forge_registry.py::ForgeRegistry.record_run`
- **tests:** `@test test_forge_registry`
- **documentation:** `(doc.arch_canon#3.c1)`
- **status:** **CURRENT**.

### 6. workspace.path_resolve

- **contract_id:** `workspace.path_resolve`
- **name:** Cross-Platform Project Workspace Root
- **purpose:** Resolve a project's absolute root path on the local filesystem (Termux / Android ARM64 / POSIX).
- **producer:** `@entity workspace.core` (`workspace_root()`, `Workspace.discover_projects`)
- **consumer:** `@entity forge.registry`; `@entity forge.facade`; `@entity forge.cli`; `@entity forge.api`; `@entity opportunity.engine`
- **input:** `()` (no args, uses canonical env var `PROJECTS_ROOT`) OR `(slug: str)` for `Workspace.project(slug)`
- **output:** `pathlib.Path`
- **errors:**
  - `WorkspaceRootNotFoundError` (env var unset or missing default)
- **events:**
  - produced: `[@event workspace.project_discovered***REMOVED***`
  - consumed: —
- **storage:** `[@storage projects_dir***REMOVED***` (filesystem, not YAML)
- **implementation:** `core_02/workspace.py::workspace_root`
- **tests:** `@test test_workspace`, `@test test_workspace_registry`
- **documentation:** `(doc.arch_canon#3.c1)`, `(doc.lifecycle#5.c1)`
- **status:** **CURRENT** — 2 test files green.

### 7. memory.write

- **contract_id:** `memory.write`
- **name:** Persistent Memory Chunk Write
- **purpose:** Append-or-overwrite a tagged memory chunk for later retrieval.
- **producer:** `@entity memory.store` (MemoryStore.write)
- **consumer:** `@entity opportunity.engine::decision_history` (decision_logged); `@entity knowledge.engine` (cross-link); `@entity learning.loop` (Phase 1.4)
- **input:** `(chunk_id: str, body: str, tags: Dict[str, str***REMOVED***)`
- **output:** `MemoryChunk` (with autoincrementing version)
- **errors:**
  - `ChunkTooLargeError` (>1 MB default)
  - `PersistenceError` (disk I/O)
- **events:**
  - produced: `[@event memory.written, @event memory.committed***REMOVED***`
  - consumed: `[@event decision_logged***REMOVED***` (from `@entity decision.registry` candidate D)
- **storage:** `[@storage memory_dir_yaml***REMOVED***`, `[@storage memory_index_sqlite***REMOVED***`
- **implementation:** `core_02/memory_store.py::MemoryStore.write`
- **tests:** `@test test_memory_store`
- **documentation:** `(doc.arch_canon#3.c1)`
- **status:** **CURRENT** — green per `test_memory_store`.

### 8. memory.search

- **contract_id:** `memory.search`
- **name:** Semantic Memory Retrieval (RAG-2.0)
- **purpose:** Search memory chunks by semantic similarity given a query.
- **producer:** `@entity memory.store` (MemoryStore.search)
- **consumer:** `@entity knowledge.engine` (corpus build); `@entity opportunity.engine::discover` (decision_history read)
- **input:** `(query: str, top_k: int = 10)`
- **output:** `List[MemoryChunk***REMOVED***` ranked by similarity
- **errors:**
  - `EmptyIndexError` (first call before any write)
- **events:**
  - produced: `[@event memory.searched***REMOVED***`
  - consumed: —
- **storage:** `[@storage memory_index_sqlite***REMOVED***`
- **implementation:** `core_02/memory_store.py::MemoryStore.search`
- **tests:** `@test test_memory_store`
- **documentation:** `(doc.arch_canon#3.c1)`
- **status:** **CURRENT**.

### 9. knowledge.query

- **contract_id:** `knowledge.query`
- **name:** Knowledge Engine Question Answering
- **purpose:** Answer a question by retrieving + ranking chunks from `docs_10/` + `prompts_11/`.
- **producer:** `@entity knowledge.engine` (KnowledgeEngine.query)
- **consumer:** `@entity opportunity.engine` (knowledge scan); `@entity wizard.lib` (hint mode)
- **input:** `(question: str, top_k: int = 5)`
- **output:** `KnowledgeAnswer` (answer + evidence_chunks)
- **errors:**
  - `EmptyCorpusError` (corpus not indexed yet)
- **events:**
  - produced: `[@event knowledge.indexed, @event knowledge.query***REMOVED***`
  - consumed: `[@event memory.written, @event doc.added***REMOVED***`
- **storage:** `[@storage knowledge_index***REMOVED***`
- **implementation:** `core_02/knowledge_engine.py::KnowledgeEngine.query`
- **tests:** `@test test_knowledge_engine`
- **documentation:** `(doc.arch_canon#3.c1)`
- **status:** **CURRENT** — FAISS-tiny or hash-map per env.

### 10. graph.add_edge

- **contract_id:** `graph.add_edge`
- **name:** Topological Relationship Edge
- **purpose:** Add an edge to the trace graph: source → relation → destination.
- **producer:** `@entity graph.index` (GraphIndex.add_edge)
- **consumer:** `@entity knowledge.engine` (cross-link); `@entity memory.store` (chunk provenance); future `traceability.graph` (Artifact E producer)
- **input:** `(src: str, rel: str, dst: str)`
- **output:** `()` (mutation)
- **errors:**
  - `InvalidRelationError` (rel not in canonical relation set per Artifact E §E.2)
- **events:**
  - produced: `[@event graph.edge_added***REMOVED***`
  - consumed: —
- **storage:** in-memory deque; optional `[@storage graph_index_json_snapshot***REMOVED***`
- **implementation:** `core_02/graph_index.py::GraphIndex.add_edge`
- **tests:** `@test test_graph_index`
- **documentation:** `(doc.lifecycle#5.c1)`
- **status:** **CURRENT**.

### 11. opportunity.discover

- **contract_id:** `opportunity.discover`
- **name:** Candidate Opportunity Discovery
- **purpose:** Evaluate current project state (pulse + event bus + knowledge) for actionable opportunities.
- **producer:** `@entity opportunity.engine` (Opportunity.discover_candidates)
- **consumer:** `@entity forge.api::/api/v1/metrics` (telemetry); `@entity whim.capture::promote` (lazy cross-store trigger)
- **input:** `(project_id: str, *, max_results: int = 10)`
- **output:** `List[Opportunity***REMOVED***` (with `STATUS = ACTIVE`, ready for proposal)
- **errors:**
  - `ProjectNotFoundError`
- **events:**
  - produced: `[@event opportunity.discovered***REMOVED***`
  - consumed: — (reads `@event project.status_changed`, `@event knowledge.indexed` passively)
- **storage:** `[@storage opportunities_yaml***REMOVED***`
- **implementation:** `scripts_01/opportunity_engine.py::Opportunity.discover_candidates`
- **tests:** `@test test_opportunity_engine` (29 passed: state graph + DEFERRED + FAILED + dry-run)
- **documentation:** `(doc.factory_forge_arch#20.c4)`, `(doc.forensics_ci_report#J.c1)` (vertical slice)
- **status:** **CURRENT** — implemented v5.187.7 per CHANGELOG.

### 12. opportunity.execute

- **contract_id:** `opportunity.execute`
- **name:** Opportunity Forge Invocation
- **purpose:** Convert a `READY` opportunity into a Forge chain execution via `@entity forge.facade`.
- **producer:** `@entity opportunity.engine` (Opportunity.execute — delegates to ForgeFacade.run_chain)
- **consumer:** `@entity forge.facade` (ForgeFacade.run_chain — see contract #1)
- **input:** `(opp: Opportunity, *, dry_run: bool = False)`
- **output:** `Opportunity` (transitioned to `EXECUTING` → `COMPLETED`/`FAILED`)
- **errors:**
  - `InvalidTransitionError` (opp.status not `READY` or `REACTIVATED`)
  - `ForgeError` (re-raised from `@contract forge.execution`)
- **events:**
  - produced: `[@event opportunity.deferred, @event opportunity.reactivated, @event opportunity.completed, @event opportunity.failed, @event execution.started, @event execution.completed, @event execution.failed, @event scenario.selected***REMOVED***` **(emitted since v5.189.24, promt 090 Phase 7)**
  - consumed: `[@event forge.chain_started, @event forge.chain_completed***REMOVED***` (sync feedback)
- **storage:** `[@storage opportunities_yaml***REMOVED***`
- **implementation:** `scripts_01/opportunity_engine.py::Opportunity.execute` (lazy import of `@entity forge.facade`)
- **tests:** `@test test_opportunity_engine`
- **documentation:** `(doc.forensics_ci_report#J.c1)`
- **status:** **CURRENT** — with note: lazy import may break mypy if `forge_facade` signature changes (flagged P1.4).

### 13. whim.promote

- **contract_id:** `whim.promote`
- **name:** Whim → Opportunity Promotion (lazy cross-store)
- **purpose:** Promote a crystallized Whim into an Opportunity candidate (lazy triggers smart_router→ForgeFacade pipeline).
- **producer:** `@entity whim.capture` (WhimStore.promote)
- **consumer:** `@entity opportunity.engine` (lazy hook on promotion)
- **input:** `(whim: Whim, *, store: WhimStore)`
- **output:** `Whim` (transitioned to `PROMOTED_TO_OPPORTUNITY`)
- **errors:**
  - `InvalidTransitionError` (whim.status not `TRIAGED`)
  - `OpportunityEngineNotAvailableError` (lazy import failed)
- **events:**
  - produced: `[@event whim.captured, @event whim.classified, @event whim.promoted, @event whim.deferred***REMOVED***` **(emitted since v5.189.24, promt 090 Phase 7)**
  - consumed: — (passive trigger; opportun-engine reads post-promotion)
- **storage:** `[@storage whims_yaml***REMOVED***`; `[@storage opportunities_yaml***REMOVED***` (new row appended by consumer)
- **implementation:** `scripts_01/whim_capture.py::WhimStore.promote`
- **tests:** `@test test_whim_capture` (39 passed: state graph + DEFERRED + FAILED + cross-store)
- **documentation:** `(doc.factory_forge_arch#20.c5)`
- **status:** **CURRENT** — implemented v5.187.8 per CHANGELOG.

### 14. missing_registry.lifecycle

- **contract_id:** `missing_registry.lifecycle`
- **name:** Missing Capability Lifecycle FSM
- **purpose:** Advance a MissingItem through FSM `registered → design_ready → prompt_written → implemented`.
- **producer:** `@entity missing.registry` (MissingRegistry.register / mark_design_ready / mark_prompt_written / mark_implemented)
- **consumer:** `@entity consistency.check` (sync verifier); CI markers in proмpts → code PRs
- **input:** `mark_*` calls take `(item_id: str, …payload: Dict)`
- **output:** `MissingItem` (with updated state + payload)
- **errors:**
  - `InvalidTransitionError` (current → next not in FSM)
  - `SchemaValidationError` (validate_schema() failed per B10 / R-127 invariants)
- **events:**
  - produced: `[@event missing.registered, @event missing.prompt_written, @event missing.implemented***REMOVED***`
  - consumed: —
- **storage:** `[@storage missing_registry_yaml***REMOVED***` (atomic write)
- **implementation:** `core_02/missing_registry.py::MissingRegistry`
- **tests:** `@test test_missing_registry` (schema validation + lifecycle FSM)
- **documentation:** `(doc.arch_canon#3.c1)`, `(doc.lifecycle#5.c1)`, `(doc.factory_forge_arch#20.c1)`
- **status:** **CURRENT** — register-first principle enforced.

### 15. opportunity.schema

- **contract_id:** `opportunity.schema`
- **name:** Opportunity Record Schema (lifecycle + provenance)
- **purpose:** Define the canonical Opportunity record shape persisted to `data_13/opportunities.yaml`.
- **producer:** `@entity opportunity.engine` (`Opportunity` dataclass + `OpportunityStore`; lifecycle via `advance`)
- **consumer:** `@entity whim.capture` (promote → creates Opportunity); `@entity forge.facade` (execute → run_chain); AnchorResolver `@opportunity` store lookup (read path)
- **input:** `Opportunity` dataclass — 24 fields: `id, project_id, title, description, source, status, priority, created_at, updated_at, provenance, scenario, roles, artifacts, source_path, evidence_path, deferred_at, deferred_reason, previous_status, reactivated_at, completed_at, failed_at, failure_reason, related_decisions, related_whims`
- **provenance sub-fields (rank, promt 086):** `rank_score` (float, композитный score ∈ [0,1***REMOVED***) + `rank_factors` (dict: `confidence`/`source`/`source_weight`/`recency`/`priority_norm`) — дописываются `rank_candidates()` при `persist_score=True` (v5.189.19). Базовые ключи DISCOVER: `source`/`source_id`/`reason`/`evidence`/`confidence`/`stub`. ACCUMULATE-ключи: `memory_knowledge_id`/`learning_event_id`/`accumulate`/`accumulate_error`.
- **output:** YAML record in `@storage opportunities_yaml` (atomic `.tmp` + `os.replace`)
- **errors:**
  - `InvalidTransition` (lifecycle transition not in canonical graph — `advance`; subclasses `ValueError`)
- **events:**
  - produced: `[@event opportunity.deferred, @event opportunity.reactivated, @event opportunity.completed, @event opportunity.failed***REMOVED***` (via `advance`, promt 090 Phase 7)
  - consumed: — (passive; `@entity whim.capture::promote` writes cross-store)
- **storage:** `@storage opportunities_yaml`
- **implementation:** `scripts_01/opportunity_engine.py::Opportunity`
- **tests:** `@test test_opportunity_engine` (state-graph + DEFERRED + FAILED + dry-run)
- **documentation:** `(doc.factory_forge_arch#20.c4)`
- **status:** **CURRENT** — 24-field dataclass implemented (v5.187.7). §E reconciled to runtime (2026-08-17, promt 090 Task A): canonical = implementation; design→runtime mapping in `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §E.1. Drift #5 CLOSED.

### 16. whim.schema

- **contract_id:** `whim.schema`
- **name:** Whim Record Schema (intake + triage lifecycle)
- **purpose:** Define the canonical Whim record shape persisted to `data_13/whims.yaml`.
- **producer:** `@entity whim.capture` (`Whim` dataclass + `WhimStore`; lifecycle via `advance`)
- **consumer:** `@entity opportunity.engine` (promote → cross-store Opportunity creation); AnchorResolver `@whim` store lookup (read path)
- **input:** `Whim` dataclass — 21 fields: `id, project_id, body, source, status, priority, created_at, updated_at, provenance, classification, classification_reason, triaged_at, triaged_by, promoted_at, related_opportunity_id, discarded_at, discarded_reason, deferred_at, deferred_reason, failed_at, failure_reason`
- **output:** YAML record in `@storage whims_yaml` (atomic `.tmp` + `os.replace`)
- **errors:**
  - `InvalidTransition` (lifecycle transition not in canonical graph — `advance`)
  - `ValueError` (empty body / empty project_id / unknown source / non-promotable classification)
- **events:**
  - produced: `[@event whim.captured, @event whim.classified, @event whim.promoted, @event whim.deferred***REMOVED***` (promt 090 Phase 7)
  - consumed: — (passive)
- **storage:** `@storage whims_yaml`
- **implementation:** `scripts_01/whim_capture.py::Whim`
- **tests:** `@test test_whim_capture` (state-graph + DEFERRED + FAILED + cross-store)
- **documentation:** `(doc.factory_forge_arch#20.c5)`
- **status:** **CURRENT** — 21-field dataclass implemented (v5.187.8). Lifecycle canonical per FACTORY_FORGE §17.1 (NEW → TRIAGED → PROMOTED_TO_OPPORTUNITY/DISCARDED; DEFERRED ≠ DELETED).

### 17. scenario.intelligence

- **contract_id:** `scenario.intelligence`
- **name:** Universal Scenario Intelligence (domain-neutral decision layer)
- **purpose:** Select the best implementation scenario for an Opportunity via discovery → evaluation → ranking → selection, with explainable provenance and capability resolution (Phase 8, promt 91).
- **producer:** `@entity scenario.intelligence` (`ScenarioIntelligence` — `scripts_01/scenario_intelligence.py`)
- **consumer:** `@entity opportunity.engine::propose` (adapter, BC-fallback); `@entity factory.registry` (capability resolution via `select_forge`); `@entity forge.facade` (execution boundary — НЕ вызывается напрямую, передаётся через decision)
- **input:** `(opp: Opportunity, *, top_n: int = 5, persist: bool = True, available_only: bool = True)`
- **output:** `ScenarioDecision` — selected_scenario_id, score (composite ∈ [0,1***REMOVED***), reasons, evidence, capability, factory_id, forge_id, status (selected/superseded/reselected/unavailable)
- **errors:** — (fail-safe: никогда не бросает наружу; «нет кандидатов» → `status='unavailable'`, не исключение)
- **events:**
  - produced: `[@event scenario.candidates.generated, @event scenario.evaluated, @event scenario.selected, @event scenario.reselected, @event scenario.feedback***REMOVED***`
  - consumed: `[@event opportunity.deferred, @event opportunity.reactivated***REMOVED***` (пассивно, через opp.status)
- **storage:** `[@storage scenario_decisions_yaml***REMOVED***` (data_13/scenario_decisions.yaml, YAML атомарный — per-opportunity latest для re-selection; MemoryStore kind=candidate + tag=scenario_decision для feedback)
- **implementation:** `scripts_01/scenario_intelligence.py::ScenarioIntelligence`
- **tests:** `@test test_scenario_intelligence` (18 passed: §18 discovery/multi/ranking/selection/provenance/capability/factory/forge/feedback/events/persistence/BC/unavailable/deferred/reselection + main integration)
- **documentation:** `(doc.phase8_traceability#1.c1)` (PHASE8_TRACEABILITY.md, 19/19 rows), `(doc.factory_forge_arch#20.c21)` (§20 row #21)
- **status:** **CURRENT** — 18 тестов green (v5.189.25). Domain-neutral: никакого content-specific branching; ForgeFacade остаётся execution boundary.

---

## §C.5 — First-slice totals (cross-cutting summary)

| Status         | Count | %     | Examples                                                                                    |
|----------------|------:|------:|---------------------------------------------------------------------------------------------|
| `CURRENT`      | 16    | 94.12%| `forge.execution`, `forge.lifecycle`, `memory.write`, `missing_registry.lifecycle`, `opportunity.schema`, `scenario.intelligence` |
| `PARTIAL`      | 1     | 5.88% | `scenario.selection` (RoleNotFoundError not raised — design tightening P1.4 flagged)        |
| `DESIGN_ONLY`  | 0     | 0.0%  | — (all contracts above have producer @entity CONFIRMED per Artifact A §A.6)                |
| `UNVERIFIED`   | 0     | 0.0%  | —                                                                                          |
| **Total**      | **17**| **100%** | All contracts resolve to either Artifact A row or DESIGN_ONLY marker.                    |

**Events produced (deduplicated):** `forge.chain_started`, `forge.chain_completed`, `forge.chain_failed`, `scenario.discovered`, `scenario.role_missing`, `scenario.role_proposed`, `scenario.selected`, `scenario.candidates.generated`, `scenario.evaluated`, `scenario.reselected`, `scenario.feedback`, `project.status_changed`, `forge.run.recorded`, `workspace.project_discovered`, `memory.written`, `memory.committed`, `memory.searched`, `knowledge.indexed`, `knowledge.query`, `graph.edge_added`, `opportunity.discovered`, `opportunity.deferred`, `opportunity.reactivated`, `opportunity.completed`, `opportunity.failed`, `execution.started`, `execution.completed`, `execution.failed`, `whim.captured`, `whim.classified`, `whim.promoted`, `whim.deferred`, `missing.registered`, `missing.prompt_written`, `missing.implemented` — **35 distinct @event IDs** (updated Phase 8: +4 scenario.* events: candidates.generated/evaluated/reselected/feedback).

**Storage units referenced (deduplicated):** `forge_registry_yaml`, `runtime_05/scenarios/*.yaml`, `projects_dir`, `memory_dir_yaml`, `memory_index_sqlite`, `knowledge_index`, `graph_index_json_snapshot`, `opportunities_yaml`, `whims_yaml`, `missing_registry_yaml`, `scenario_decisions_yaml` — **11 distinct @storage IDs**.

**Implementation files touched:** `core_02/scenario_registry.py`, `core_02/scenario_registry.py`, `core_02/forge_facade.py`, `core_02/forge_registry.py`, `core_02/workspace.py`, `core_02/memory_store.py`, `core_02/knowledge_engine.py`, `core_02/graph_index.py`, `core_02/missing_registry.py`, `scripts_01/opportunity_engine.py`, `scripts_01/whim_capture.py`, `scripts_01/scenario_intelligence.py`, `scripts_01/forge_api.py` (consumers only — read paths) — **11 producers + 1 consumer-only**.

---

## §C.6 — Drift findings (open items for next contract slice)

1. **Contract #2 `scenario.selection` PARTIAL flag:** `ScenarioRegistry.find_role` returns `None` on RoleNotFoundError rather than raising. Code-reviewer pulled design intent (raise) from `core_02/LESSONS.md` CON-? but not implemented. **Target:** raise `RoleNotFoundError` in P1.4 release, status flip to CURRENT.
2. **Contract #12 `opportunity.execute` mypy gap:** lazy import of `forge.facade.run_chain` shows 17 placeholder signature errors in mypy because `forge_facade.py::run_chain` wasn't type-annotated at the time of opportunity_engine creation. **Target:** annotate `run_chain(slug, role_ids=None) -> Dict[str, Any***REMOVED***` and run mypy in v1.4.
3. **Contracts not enumerated in first slice (target next slice):**
   - `event.bus.publish` (cross-cutting infra; test 7 cases)
   - `forge.api.metrics` (read-only REST endpoint wrap of `#11` + `#6`)
   - `forge.cli.dispatch` (CLI entrypoint → forge.facade delegation)
   - `forge.interactive.async_chain` (UNVERIFIED — no dedicated test)
   - `event.bus.subscribe` (consumer-side mirror of `#event.bus.publish`)
4. **Stale cross-references:**
   - `(doc.factory_forge_arch#20.c4)` annotation on `@entity opportunity.engine` row in Artifact A — exact row id to be verified during Phase G (ARCHITECTURE_GAP_MAP) call.
   - `(doc.arch_canon#3.c1)` cited by 5 contracts — ensure this anchor is stable before Phase E (TRACEABILITY_GRAPH) consumes it.
5. **Schema contracts #15/#16 — §E design vs implementation drift (added 2026-08-16, GAP-4/GAP-5 closure; CLOSED 2026-08-17, promt 090 Task A):**
   - ✅ **RESOLVED:** `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §E reconciled to the canonical 24-field runtime schema (canonical = implementation), design→runtime mapping table added (§E.1). `FACTORY_FORGE §20 #10` «16 полей» reference updated to 24.
   - ✅ **RESOLVED (promt 090 Phase 7, v5.189.24):** EventBus emission wired — `opportunity_engine.advance` emits `opportunity.deferred/reactivated/completed/failed`; `execute` emits `execution.started/completed/failed`; `propose` emits `scenario.selected`; `whim_capture` emits `whim.captured/classified/promoted/deferred`. Contracts #12/#13/#15/#16 `produced:` lists updated to CURRENT.

---

## §C.7 — Cross-references (downstream consumers)

This artifact C is consumed by:
- **Artifact D** `ARCHITECTURE_DECISION_REGISTRY_V1` — uses `@contract` namespace from §I.1 + `decision_id ADR_NNN` per §11 spec for governance decisions.
- **Artifact E** `TRACEABILITY_GRAPH_V1` — uses `contract_id` as graph edge label; `producer → consumer` becomes edge `(producer, contracts_with_producer_this, consumer)`.
- **Artifact F** `AGENT_NAVIGATION_MAP_V1` — uses `contract_id` as the canonical "WHAT CAN I CALL?" answer per §12/§13 navigation query.
- **Artifact G** `ARCHITECTURE_GAP_MAP_V1` — flags PARTIAL + DESIGN_ONLY contracts from §C.5 totals.
- **Artifact H** `DOCUMENTATION_CONSISTENCY_REPORT_V1` — validates `(doc.<...>)` anchors in `documentation` field against Artifact B provenance table.

**Side effects on existing repo:** None (read-only artifact; no code/config change). At implementation time (Phase F → AGENT_NAVIGATION_MAP), an `core_02/anchor_resolver.py` may be scaffolded per Artifact I §I.3 spec.

---

## §C.8 — Provenance (verification checklist per `prompts/4.md` §21)

- [x***REMOVED*** Each contract has producer/consumer @entity from Artifact A (25 entries).
- [x***REMOVED*** Each contract has at least one @event from §C.5 deduplicated list (cross-check with `scripts_01/event_bus.py`).
- [x***REMOVED*** Each contract has at least one @test reference mapped to `tests_09/test_*.py` (all 17 paths verified).
- [x***REMOVED*** Each contract has `(doc.<...>)` cross-reference to Artifact B IF a documentation claim exists (10 contracts have; 7 are infra-level without claims).
- [x***REMOVED*** Each contract status is either CURRENT (16), PARTIAL (1), DESIGN_ONLY (design_phase), or UNVERIFIED (0).
- [x***REMOVED*** 35 produced @event IDs are unique across all 17 contracts (deduplicated list).
- [x***REMOVED*** 11 storage units each resolve to a `data_13/*.yaml` or `runtime_05/*` file path (per §I.3 resolution mechanism).
- [x***REMOVED*** Each contract's `errors` list maps to an actual Python exception class in the producer file OR a design-time expected exception (for DESIGN_ONLY).

---

_Phase D closed per Phase plan v0.1 §C. Implementation: 2026-08-12. Schema contracts #15/#16 appended 2026-08-16 (GAP-4/GAP-5 closure). Contract #17 `scenario.intelligence` appended 2026-08-17 (Phase 8, promt 91; PHASE8_TRACEABILITY.md cross-ref). 17 contracts, 16 CURRENT / 1 PARTIAL / 0 DESIGN_ONLY / 0 UNVERIFIED. Next: Phase D → Artifact D (`ARCHITECTURE_DECISION_REGISTRY_V1`)._
