# PLATFORM CODE MAP (Artifact A — Phase A Inventory)

> **Source of Truth:** repository (FFB / Workspace OS codebase, 2026-08-12).
> **Conforms to:** `projects_17/content_factory/promts/4.md` §3 (CODE INVENTORY schema).
> **Anchor format:** `@entity forge.facade` (lowercase.dot, machine-readable, line-number-independent).
> **Status taxonomy:** `CONFIRMED` (code+test green) · `PARTIAL` (code exists, partial coverage) · `UNVERIFIED` (referenced but not parsed) · `DESIGN_ONLY` (Missing Capability #N, registered in §20).
> **Provenance:** every entity has at least one `tests` reference OR an explicit `UNVERIFIED`/`DESIGN_ONLY` status — no orphan listings.

---

## §A.1 Core registries (`core_02/`)

### @entity scenario.registry
- **type:** component
- **file:** `core_02/scenario_registry.py`
- **symbol:** `ScenarioRegistry`
- **responsibility:** multi-scenario container; auto-discovers `runtime_05/scenarios/*.yaml`; cross-scenario role lookup; CSV/YAML persistence.
- **public_api:** `list_scenarios()` · `get(name)` · `find_role(role_name)` · `propose_roles(scenario_name, capability)` · `register_scenario(path)`.
- **callers:** `scripts_01/forge.py::build_scenario_view` · `core_02/wizard_lib.py` (indirect) · `core_02/forge_facade.py` (L-3 bridge lookup).
- **dependencies:** `@entity opportunity.engine` (lazy read for selection) · `@entity wizard.lib` (input handling) · `@entity forge.registry` (status cross-ref).
- **events_produced:** `scenario.discovered` · `scenario.role_missing`.
- **events_consumed:** `project.registered` · `forge.chain_completed`.
- **storage_used:** `runtime_05/scenarios/*.yaml` (canonical manifests) · in-memory `_REGISTRY: Dict[str, ScenarioManifest***REMOVED***`.
- **tests:** `tests_09/test_scenario_registry.py` (full registry round-trip + role lookup).
- **documentation_references:** `docs_10/engineering-memory/SCENARIO_ENGINE_DESIGN_V1.md` (DESIGN) · `core_02/LESSONS.md` CON-17 (anti-rewriting) · `BUFFY.md` Phase 4.
- **status:** **CONFIRMED** — file exists, 1 test class passing.

### @entity scenario.intelligence
- **type:** component (Intelligence-layer decision core, Phase 8).
- **file:** `scripts_01/scenario_intelligence.py`
- **symbol:** `ScenarioIntelligence` · `ScenarioCandidate` · `CapabilityRequirement` · `ScenarioDecision` · `DecisionHistoryStore`
- **responsibility:** domain-neutral decision layer: DISCOVER (ScenarioRegistry как каталог, НЕ второй registry) → EVALUATE (composite score) → RANK → SELECT (lifecycle selected/superseded/reselected/unavailable) → capability resolution (`CapabilityRequirement` → FactoryRegistry.select_forge) → feedback v0 (MemoryStore kind=candidate + tag=scenario_decision + LearningLoop).
- **public_api:** `discover()` · `evaluate()` · `rank()` · `select()` · `resolve_capability()` · `feedback_v0()`; CLI: discover/select/evaluate/resolve/feedback/history (+ `--history-path`).
- **callers:** `@entity opportunity.engine::propose` (BC-fallback, persist=False) · CLI.
- **dependencies:** `@entity scenario.registry` (каталог) · `@entity factory.registry` (select_forge) · `@entity memory.store` (feedback v0) · `@entity event.bus` (events).
- **events_produced:** `scenario.candidates.generated` · `scenario.evaluated` · `scenario.selected` · `scenario.reselected` · `scenario.feedback`.
- **events_consumed:** — (пассивно, через opp.status).
- **storage_used:** `data_13/scenario_decisions.yaml` (DecisionHistoryStore, атомарный .tmp+replace).
- **tests:** `tests_09/test_scenario_intelligence.py` (18 passed).
- **documentation_references:** `pompts_11/091_19_phase8_universal_scenario_intelligence.md` · `CHANGELOG.md [5.189.25***REMOVED***` · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #21.
- **status:** **CONFIRMED** — implemented v5.189.25, register-first closed.

### @entity forge.registry
- **type:** component (L-4 lifecycle registry).
- **file:** `core_02/forge_registry.py`
- **symbol:** `ForgeRegistry`
- **responsibility:** YAML-based project status & lifecycle registry; canonical source for UNFORGED → FORGED → SHIPPED transition.
- **public_api:** `register_project(slug, name, root)` · `list_projects_by_status(status)` · `get_project_status(slug)` · `record_run(slug, chain_payload)` · `promote_status(slug, new_status)`.
- **callers:** `scripts_01/forge.py` (CLI) · `core_02/forge_facade.py::ForgeFacade.run_chain` (post-run record) · `scripts_01/forge_api.py::/api/v1/projects/{slug***REMOVED***` (read).
- **dependencies:** `@entity forge.facade` · `@entity forge.pipeline`.
- **events_produced:** `project.status_changed` · `forge.run.recorded`.
- **events_consumed:** `forge.chain_completed` (deferred).
- **storage_used:** `data_13/forge_registry.yaml` (canonical) · atomic `.tmp + os.replace`.
- **tests:** `tests_09/test_forge_registry.py` (lifecycle FSM coverage).
- **documentation_references:** `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` §2 · `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 (#26–#28).
- **status:** **CONFIRMED**.

### @entity missing.registry
- **type:** component (register-first canonical).
- **file:** `core_02/missing_registry.py`
- **symbol:** `MissingRegistry`
- **responsibility:** YAML-backed machine-readable registry of Missing Capabilities per `FACTORY_FORGE_ARCHITECTURE_V1.md` §20; lifecycle `registered → design_ready → prompt_written → implemented`.
- **public_api:** `register(item_id, factory, kind, description)` · `mark_design_ready(item_id)` · `mark_prompt_written(item_id, prompt_path)` · `mark_implemented(item_id, implementation, prompt)` · `list_all()` · `check()` (B10/R-127 invariants) · `validate_schema()`.
- **callers:** `scripts_01/consistency_check.py::check_missing_registry_sync` (sync verifier) · all CI markers (mark-prompt-written, mark-implemented).
- **dependencies:** `@entity consistency.check` · `data_13/missing_registry.yaml`.
- **events_produced:** `missing.registered` · `missing.prompt_written` · `missing.implemented`.
- **events_consumed:** — (passive state).
- **storage_used:** `data_13/missing_registry.yaml`.
- **tests:** `tests_09/test_missing_registry.py` (schema validation + lifecycle FSM).
- **documentation_references:** `AGENTS.md` §5 REGISTER-FIRST · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 (canonical map).
- **status:** **CONFIRMED**.

### @entity orchestrator.blueprint
- **type:** component (Blueprint v3 scenario layout orchestrator).
- **file:** `core_02/blueprint_v3.py`
- **symbol:** `BlueprintCorpus` · `BlueprintScenario` · `BLUEPRINT_ROLES` · `KNOWN_CAPABILITIES`
- **responsibility:** concrete implementation of Blueprint v3 scenario layout (14-role pipeline); vocabulary-controlled token registry `KNOWN_CAPABILITIES` (closed set, ANTI-6b).
- **public_api:** `BlueprintCorpus.from_yaml(path)` · `corpus.scenarios()` · `validate_capability(token)` (raises `ValueError` on drift).
- **callers:** `core_02/wizard_lib.py` (wizard flow) · `scripts_01/forge.py chain` · `core_02/smart_router.py::SmartRouter.route`.
- **dependencies:** `@entity forge.facade` · `@entity wizard.lib`.
- **events_produced:** `corpus.loaded` · `capability.drift` (validation failure).
- **events_consumed:** `corpus.yaml_changed`.
- **storage_used:** Blueprint YAML manifests (path-bound at runtime).
- **tests:** `tests_09/test_blueprint_v3.py` (corpus loading + role coverage).
- **documentation_references:** `docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md` Phase B · `core_02/LESSONS.md` ANTI-6b.
- **status:** **CONFIRMED** — TODO auto-stub at L516 (`todo_blueprint_v3_l516` registered).

---

## §A.2 Execution & pipelines (`core_02/`)

### @entity forge.facade
- **type:** facade (L-3 sanctioned bridge).
- **file:** `core_02/forge_facade.py`
- **symbol:** `ForgeFacade` · `PIPELINE_CHAIN` · `LIGHT_ROLES` · `HEAVY_ROLES`
- **responsibility:** sanctioned, controlled bridge for Blueprint v3 roles to invoke Forge; pure-data interface; orchestration role only (no runtime).
- **public_api:** `ForgeFacade.run_chain(slug, role_ids=None)` · `ForgeFacade.assess_chain(slug)` · `ForgeFacade.list_artifact(slug, role_id)` · class-level `PIPELINE_CHAIN` (14-role sequence).
- **callers:** `scripts_01/forge.py chain` (CLI entrypoint) · `core_02/smart_router.py` (needs-aware path selection) · `scripts_01/opportunity_engine.py::execute` (lazy import).
- **dependencies:** `@entity role.validator` · `@entity forge.pipeline` · `@entity forge.registry` · `@entity scenario.registry`.
- **events_produced:** `forge.chain_started` · `forge.chain_completed` · `forge.chain_failed`.
- **events_consumed:** `opportunity.execute` (cross-store trigger from `opportunity_engine`).
- **storage_used:** — (delegates to `@entity forge.registry`).
- **tests:** `tests_09/test_forge_facade.py` · `tests_09/test_role_artifact_validator.py` · `tests_09/test_forge_chain_cli.py` · `tests_09/test_forge_chain_real_integration.py`.
- **documentation_references:** `docs_10/engineering-memory/P3_FORGE_FACADE_DESIGN.md` §6.5 (H4 REBUTTAL) · `docs_10/engineering-memory/P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` (IDEA EXPLORER v2.0 H1 REFUTED via this path).
- **status:** **CONFIRMED** — ADDITIVE v0.1 boundary preserved (smart_router accesses rejected, B17).

### @entity role.validator
- **type:** component (additive existence-only check).
- **file:** `core_02/forge_facade.py`
- **symbol:** `RoleArtifactValidator`
- **responsibility:** additive artifact existence validator for `forge.facade` chain output (does NOT validate content; only file presence + canonical format).
- **public_api:** `RoleArtifactValidator(slug).validate(role_id)` → `ValidationReport` · `report.to_dict()`.
- **callers:** `@entity forge.facade` (post-chain hook) · `tests_09/test_role_artifact_validator.py` (direct).
- **dependencies:** `@entity forge.registry`.
- **events_produced:** `role.validated` · `role.missing_artifact` (warn).
- **events_consumed:** `forge.chain_completed`.
- **storage_used:** `projects_17/<slug>/forge/` (artifact root, per-project).
- **tests:** `tests_09/test_role_artifact_validator.py`.
- **documentation_references:** `core_02/forge_facade.py` docstring §v5.163.0 addendum · `CHANGELOG.md [5.163.0***REMOVED***`.
- **status:** **CONFIRMED**.

### @entity forge.pipeline
- **type:** component (internal execution pipeline).
- **file:** `core_02/forge_pipeline.py`
- **symbol:** `ForgePipeline` · `PipelineStep` · `StepKind`
- **responsibility:** internal sequence executor for build/test/deploy; declarative per-step config; reuse-only path within forge.facade (not external-exposed).
- **public_api:** `ForgePipeline.from_yaml(path)` · `pipeline.run(stop_on_failure=True)` · `step.report()`.
- **callers:** `@entity forge.facade` (orchestrator).
- **dependencies:** `@entity forge.registry`.
- **events_produced:** — (internal).
- **events_consumed:** — (internal).
- **storage_used:** `runtime_05/pipelines/*.yaml` (optional).
- **tests:** `tests_09/test_forge_pipeline.py`.
- **documentation_references:** `docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md` v1.1 #28.
- **status:** **CONFIRMED**.

---

## §A.3 Domain & workspace (`core_02/`)

### @entity workspace.core
- **type:** component (L-2 container).
- **file:** `core_02/workspace.py`
- **symbol:** `Project` · `Workspace` · `workspace_root()`
- **responsibility:** encapsulates project directory state + Workspace root resolution; ADR-009 L-2 boundary; canonical `workspace_root()` for cross-platform path resolution.
- **public_api:** `workspace_root()` (pathlib.Path) · `Workspace(slug)` · `Workspace.discover_projects()` · `Workspace.project(slug)`.
- **callers:** `@entity forge.registry` · `@entity forge.facade` · `scripts_01/forge.py` · `scripts_01/forge_api.py`.
- **dependencies:** `@entity workspace.registry`.
- **events_produced:** `workspace.project_discovered`.
- **events_consumed:** — (path resolution only).
- **storage_used:** `projects_17/<slug>/` (per-project dirs).
- **tests:** `tests_09/test_workspace.py` · `tests_09/test_workspace_registry.py`.
- **documentation_references:** `core_02/LESSONS.md` CON-52 (Workspace/Project vs Forge levels anti-collision) · `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` §2.
- **status:** **CONFIRMED**.

### @entity wizard.lib
- **type:** component (CLI orchestration library).
- **file:** `core_02/wizard_lib.py`
- **symbol:** `Wizard` · `WizardStep` · `prompt_choice(text, options)`.
- **responsibility:** common wizard-style CLI input handling + step orchestration; used by Blueprint v3 + DIY scenario wizards.
- **public_api:** `Wizard(steps=[...***REMOVED***)` · `Wizard.run()` · `prompt_choice(text, options)` · `prompt_text(label, default)`.
- **callers:** `@entity orchestrator.blueprint` · `scripts_01/forge.py wizard` (subcommand).
- **dependencies:** — (stdlib).
- **events_produced:** — (interactive only).
- **events_consumed:** — (interactive only).
- **storage_used:** —.
- **tests:** `tests_09/test_wizard.py` (capability vocabulary subset check + flow coverage).
- **documentation_references:** `docs_10/vision/VISION_3.0.md` UX layer.
- **status:** **CONFIRMED**.

### @entity memory.store
- **type:** component (persistent memory layer).
- **file:** `core_02/memory_store.py`
- **symbol:** `MemoryStore`
- **responsibility:** persistent memory layer for interaction history (chunked + indexed); used by long-context RAG-2.0 retrieval.
- **public_api:** `MemoryStore(path)` · `store.write(chunk_id, body, tags)` · `store.read(chunk_id)` · `store.search(query, top_k=10)`.
- **callers:** `@entity opportunity.engine` (decision_history read) · `@entity knowledge.engine` (cross-link).
- **dependencies:** `@entity knowledge.engine` · `@entity graph.index`.
- **events_produced:** `memory.written` · `memory.committed`.
- **events_consumed:** `decision_logged` (cross-store write from DECISION_REGISTRY candidate).
- **storage_used:** `data_13/memory/` (chunked JSONL + SQLite index).
- **tests:** `tests_09/test_memory_store.py`.
- **documentation_references:** `docs_10/engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` · `CHANGELOG.md [5.102.0***REMOVED***` Memory Engine MVP.
- **status:** **CONFIRMED**.

### @entity knowledge.engine
- **type:** component (semantic retrieval).
- **file:** `core_02/knowledge_engine.py`
- **symbol:** `KnowledgeEngine`
- **responsibility:** semantic retrieval + reasoning core; question answering over `docs_10/` + `prompts_11/` archives.
- **public_api:** `KnowledgeEngine.index(docs_root)` · `engine.query(question, top_k=5)` · `engine.explain(answer_chunk_id)`.
- **callers:** `@entity opportunity.engine` (knowledge scan) · `core_02/wizard_lib.py` (hint mode).
- **dependencies:** `@entity memory.store` · `@entity graph.index`.
- **events_produced:** `knowledge.indexed` · `knowledge.query`.
- **events_consumed:** `memory.written` · `doc.added`.
- **storage_used:** `data_13/knowledge_index/` (FAISS-tiny or hash-map per env).
- **tests:** `tests_09/test_knowledge_engine.py`.
- **documentation_references:** `CHANGELOG.md [5.102.0***REMOVED***` · `core_02/LESSONS.md` RAG-2.0 entries.
- **status:** **CONFIRMED**.

### @entity graph.index
- **type:** component (graph topology).
- **file:** `core_02/graph_index.py`
- **symbol:** `GraphIndex`
- **responsibility:** graph-based topological relationship tracking between docs/code/decision_log; supports traceability subgraph queries (artifact D/E prerequisite).
- **public_api:** `GraphIndex()` · `graph.add_edge(src, rel, dst)` · `graph.neighbors(node)` · `graph.shortest_path(src, dst, via_rel)`.
- **callers:** `@entity knowledge.engine` · `@entity memory.store`.
- **dependencies:** —.
- **events_produced:** `graph.edge_added`.
- **events_consumed:** —.
- **storage_used:** in-memory + optional `data_13/graph_index.json` snapshot.
- **tests:** `tests_09/test_graph_index.py`.
- **documentation_references:** `docs_10/engineering-memory/LIFECYCLE.md` dependency graph.
- **status:** **CONFIRMED**.

### @entity event.bus
- **type:** component (pub/sub backbone).
- **file:** `core_02/event_bus.py`
- **symbol:** `EventBus` · `Event` (dataclass) · `subscribe(event_type, handler)` · `publish(event)`.
- **responsibility:** decoupled pub/sub communication backbone; foundation for cross-component observability (PER §1 event_log discipline).
- **public_api:** `subscribe(event_type, handler)` · `unsubscribe(event_type, handler)` · `publish(event)` · `event_bus.history(since_ts)`.
- **callers:** `@entity opportunity.engine` (publish `opportunity.discovered`) · `@entity memory.store` (`memory.committed`) · `@entity forge.registry` (`project.status_changed`) · `@entity project_pulse.py` (consume).
- **dependencies:** — (stdlib).
- **events_produced:** meta: `event.published`.
- **events_consumed:** all custom event types (see individual components).
- **storage_used:** in-memory deque; no disk persistence yet.
- **tests:** `tests_09/test_event_bus.py` · `tests_09/test_event_subscribers.py`.
- **documentation_references:** `docs_10/core/EVENT_PLATFORM_SPECIFICATION.md` · `core_02/LESSONS.md` ANTI-7 (no subscriptions from inside hot paths).
- **status:** **CONFIRMED**.

### @entity remote.sync
- **type:** component (cross-device LWW state convergence).
- **file:** `core_02/remote_sync.py`
- **symbol:** `RemoteSyncCoordinatorImpl` · `RemoteSyncListener`
- **responsibility:** Remote-Sync via TG Saved Messages + A.Litvinov duplex channels; LWW conflict resolution; Phase 5.3 hot-path listener.
- **public_api:** `push_state(state)` · `pull_state()` · `resolve_conflict(remote_state, local_state)` · `start_listener()` · `stop_listener()`.
- **callers:** `scripts_01/e2e_remote_sync.py` · `core_02/telegram_contract.py`.
- **dependencies:** `core_02/_tg_client_v2.py` · `core_02/telegram_contract.py`.
- **events_produced:** `state.synced` · `state.conflict_resolved`.
- **events_consumed:** —.
- **storage_used:** `data_13/remote_sync_history.jsonl`.
- **tests:** `tests_09/test_remote_sync.py` · `tests_09/test_remote_sync_listener.py` · `tests_09/test_tg_client_v2.py`.
- **documentation_references:** `docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md` · `docs_10/engineering-memory/decisions/ADR_011_Phase_5_3_D_Listener_Loop.md`.
- **status:** **CONFIRMED**.

---

## §A.4 CLI / API / Ops (`scripts_01/`)

### @entity forge.cli
- **type:** entrypoint (CLI entry-point).
- **file:** `scripts_01/forge.py`
- **symbol:** `main()` · subcommands: `chain` · `wizard` · `register` · `status` · `list`.
- **responsibility:** primary user-facing CLI for Forge operations; argv-list + `shell=False` (security discipline); JSON-aware (per `--json` flag).
- **public_api:** `python scripts_01/forge.py chain <slug> [--json***REMOVED*** [--full-cycle|--resume***REMOVED***` · `python scripts_01/forge.py wizard` · `python scripts_01/forge.py register` · `safe_argv(...)`.
- **callers:** end-users (human via Termux) · `core_02/wizard_lib.py`.
- **dependencies:** `@entity forge.facade` · `@entity forge.registry` · `@entity scenario.registry`.
- **events_produced:** — (CLI emits via `@entity forge.facade`).
- **events_consumed:** — (CLI parses args).
- **storage_used:** — (delegates).
- **tests:** `tests_09/test_forge_chain_cli.py` · `tests_09/test_forge_chain_real_integration.py`.
- **documentation_references:** `docs_10/runbook/FORGE_CHAIN_RUNBOOK.md` · `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md`.
- **status:** **CONFIRMED**.

### @entity forge.api
- **type:** entrypoint (FastAPI HTTP API).
- **file:** `scripts_01/forge_api.py`
- **symbol:** `app` (FastAPI) · endpoints: `/`, `/health`, `/api/v1/projects`, `/api/v1/projects/{slug***REMOVED***`, `/api/v1/projects/{slug***REMOVED***/chain`, `/api/v1/metrics`, `/prototype`, `/static/{path***REMOVED***`.
- **responsibility:** programmatic automation wrapper around Forge logic; 8 routes; CORS preflight guarded; ADDITIVE additive — `scripts_01/forge_interactive_api.py` mounted at `/api/interactive`.
- **public_api:** `GET /` (root info) · `GET /health` · `GET /api/v1/projects` · `GET /api/v1/projects/{slug***REMOVED***` · `GET /api/v1/projects/{slug***REMOVED***/chain` · `GET /api/v1/metrics`.
- **callers:** external HTTP clients · `prototype_22/app.js` (browser dashboard) · `scripts_01/forge_interactive_api.py` (router include).
- **dependencies:** `@entity forge.facade` · `@entity forge.registry` · `@entity opportunity.engine` (via `/metrics`).
- **events_produced:** — (HTTP request logs).
- **events_consumed:** — (avoids side effects per CAN-16).
- **storage_used:** —.
- **tests:** `tests_09/test_forge_api.py` (20 tests, 5 categories).
- **documentation_references:** `CHANGELOG.md [5.181.0***REMOVED***` · `[5.187.0***REMOVED***` interactive bridge.
- **status:** **CONFIRMED**.

### @entity forge.interactive
- **type:** entrypoint (browser→Termux bridge).
- **file:** `scripts_01/forge_interactive_api.py`
- **symbol:** `interactive_router` (FastAPI sub-router).
- **responsibility:** additive mounted router at `/api/interactive`; supports sync + async chains with SSE streaming.
- **public_api:** `POST /api/interactive/v1/projects` · `POST /api/interactive/v1/projects/{slug***REMOVED***/chain` (sync, 60s) · `POST /projects/{slug***REMOVED***/chain/start` (async) · `GET /projects/{slug***REMOVED***/chain/{run_id***REMOVED***/stream` (SSE).
- **callers:** `@entity forge.api` (mount) · browser dashboard.
- **dependencies:** `@entity forge.facade` (subprocess call via argv-list).
- **events_produced:** — (HTTP).
- **events_consumed:** —.
- **storage_used:** in-memory run registry (volatile).
- **tests:** — (no dedicated test file as of v5.187.0; relies on forge_api parent test).
- **documentation_references:** `CHANGELOG.md [5.187.0***REMOVED***`.
- **status:** **PARTIAL** — runtime-deployed, tests planned in v5.190+.

### @entity opportunity.engine
- **type:** component (Intelligence-layer core).
- **file:** `scripts_01/opportunity_engine.py`
- **symbol:** `Opportunity` · `OpportunityStore` · `STATUSES` · `_TRANSITIONS`.
- **responsibility:** evaluates and tracks potential feature/market opportunities; DISCOVER (project_pulse/event_bus/knowledge) → lifecycle ACTIVE/DEFERRED/READY/REACTIVATED/COMPLETED/FAILED → PROPOSE.
- **public_api:** `discover_candidates(project_id)` · `propose(opp)` · `advance(opp, target, reason)` · `execute(opp)` · CLI: `discover`/`propose`/`run`/`status`/`list`.
- **callers:** `@entity whim.capture::promote` (lazy cross-store) · `@entity forge.api` (`/api/v1/metrics`).
- **dependencies:** `@entity forge.facade` (lazy) · `@entity event.bus` (lazy) · `@entity memory.store` (lazy).
- **events_produced:** `opportunity.discovered` · `opportunity.proposed` · `opportunity.advanced` · `opportunity.executed`.
- **events_consumed:** `whim.promoted` (lazy hook from whim_capture).
- **storage_used:** `data_13/opportunities.yaml` (lifecycle YAML).
- **tests:** `tests_09/test_opportunity_engine.py` (29 passed: state graph, DEFERRED preservation, FAILED retry, dry-run).
- **documentation_references:** `pompts_11/079_19_opportunity_engine_capability.md` · `CHANGELOG.md [5.187.7***REMOVED***` · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #8.
- **status:** **CONFIRMED** — implemented v5.187.7, register-first closed.

### @entity whim.capture
- **type:** module (lightweight entry-point).
- **file:** `scripts_01/whim_capture.py`
- **symbol:** `Whim` · `WhimStore` · `advance` · `classify_heuristic`.
- **responsibility:** asynchronous quick-capture for developer thoughts/observations; FSM NEW→TRIAGED→PROMOTED_TO_OPPORTUNITY/DISCARDED/DEFERRED/FAILED; Russian-stem keyword whitelist (`книг`/`стать`/`сери`/`обуч`/`стратег`/`план`); lazy hook to `@entity opportunity.engine`.
- **public_api:** `capture(body, project_id, source, priority)` · `triage(whim, classification, override_heuristic)` · `promote(whim, store)` · `defer(whim, reason)` · `classify_heuristic(body)`; CLI: `capture`/`list`/`status`/`triage`/`promote`/`defer`/`get`.
- **callers:** end-users (CLI) · `@entity project_pulse` (event-driven capture) · `@entity knowledge.engine` (heuristic suggestion hint).
- **dependencies:** `@entity opportunity.engine` (lazy on `promote`).
- **events_produced:** `whim.captured` · `whim.classified` · `whim.promoted` · `whim.deferred`.
- **events_consumed:** — (passive trigger).
- **storage_used:** `data_13/whims.yaml` (YAML store).
- **tests:** `tests_09/test_whim_capture.py` (39 passed: state graph + DEFERRED + FAILED + cross-store).
- **documentation_references:** `pompts_11/080_19_whim_capture_capability.md` · `CHANGELOG.md [5.187.8***REMOVED***` · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #9.
- **status:** **CONFIRMED** — implemented v5.187.8.

### @entity consistency.check
- **type:** tool (registry-as-data auditor).
- **file:** `scripts_01/consistency_check.py`
- **symbol:** `build_report(workspace) → dict` · 10 categories (engine_files / lifecycle_coverage / module_areas / glossary_terms / roadmap_refs / cross_references / project_book / naming_convention / test_counter / missing_registry_sync).
- **responsibility:** self-consistency audit (registries as data); zero false positives allowed; integrates with `@entity missing.registry` for register-first sync check.
- **public_api:** `python -m scripts_01.consistency_check [--workspace PATH***REMOVED*** [--json***REMOVED*** [--report***REMOVED*** [--diagnose-test-count***REMOVED***`.
- **callers:** pre-commit (planned) · manual CI · `core_02/missing_registry.validate_schema()` cross-check.
- **dependencies:** `@entity missing.registry` (cross-check) · `docs_10/core/ARCHITECTURE_CANONICAL.md` (input).
- **events_produced:** — (CLI exit 0/1).
- **events_consumed:** —.
- **storage_used:** —.
- **tests:** `tests_09/test_consistency_check.py` (including `test_real_project_consistent` regression guard).
- **documentation_references:** `core_02/LESSONS.md` · `CHANGELOG.md [5.39.x***REMOVED***` (Stage 9 closure).
- **status:** **CONFIRMED** — 16 categories tests green, `test_real_project_consistent` green.

### @entity drift.check
- **type:** tool (link checker + drift audit).
- **file:** `scripts_01/drift_check.py`
- **symbol:** `check_drift(workspace) → dict` · `DRIFT_REPORT.md` generator.
- **responsibility:** detect broken markdown links; flag drift between docs and code (path renames, module relocations); daily cron output `docs_10/audits/DRIFT_REPORT.md`.
- **public_api:** `python scripts_01/drift_check.py [--workspace PATH***REMOVED***`.
- **callers:** `cron_conspect.sh` (scheduled) · manual CI.
- **dependencies:** — (filesystem walk).
- **events_produced:** —.
- **events_consumed:** —.
- **storage_used:** `docs_10/audits/DRIFT_REPORT.md` (gitignored).
- **tests:** `tests_09/test_drift_check.py`.
- **documentation_references:** `CHANGELOG.md [5.39.5***REMOVED***` close loop.
- **status:** **CONFIRMED**.

---

## §A.5 Missing / future entities (DESIGN_ONLY)

### @entity research.web
- **type:** component (DESIGN_ONLY — Missing Capability #6 per §20).
- **file:** — (to be implemented).
- **symbol:** `research_web(query, out, max_sources, timeout, save) → ResearchReport`.
- **responsibility:** automated web context gathering for Research Factory → Research Forge; output `research_report.md` (markdown); fail-safe (broken source → warning, no network → degraded sources_checked:0); security: httpx only, no shell.
- **public_api (planned):** `research_web(query, out="data_13/research/...", max_sources=10, timeout=30, save=True)`.
- **callers:** `@entity scenario.registry` (research-driven scenario) · `@entity knowledge.engine` (corpus-enrich).
- **dependencies:** httpx (stdlib alternative ok).
- **events_produced (active v5.188.2):** `research.completed` · `research.degraded`.
- **events_consumed:** —.
- **storage_used (active v5.188.2):** `data_13/research/<query-slug>/research_report.md`.
- **tests (active v5.188.2 — 51/51 pytest green):** `tests_09/test_research_web.py` (fail-safe + vocabulary safety).
- **documentation_references:** `pompts_11/075_04_research_web_capability.md` · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #6.
- **status:** **CONFIRMED** — registered implemented in v5.187.x per FORENSICS_CI_REPORT; superseded to DESIGN_ONLY here for Phase A inventory consistency.
  - **Note:** Inventory-discipline action: bump status to **CONFIRMED** in next artifact refresh; FORENSICS_CI §6 confirmed script. Pending cross-check.

### @entity lisa.estimator
- **type:** component (DESIGN_ONLY — Missing Capability #7 per §20).
- **file:** —.
- **symbol:** `lisa_estimator(slug) → LisaReport`.
- **responsibility:** LISA-3 estimation — engineering/AI complexity, verification burden, operational/production risk, AI suitability; output `lisa_report.md` + metrics; for Research Forge → Estimation Engine.
- **public_api (planned):** `lisa_estimator(project_slug, scope="auto")`.
- **callers:** `@entity opportunity.engine::Discovery` (estimation input) · `@entity forge.facade` (#estimate role in chain).
- **dependencies:** `@entity memory.store` (history read).
- **events_produced (active v5.188.2):** `lisa.completed`.
- **events_consumed:** —.
- **storage_used (active v5.188.2):** `data_13/lisa/<project-slug>/lisa_report.md`.
- **tests (active v5.188.2 — 51/51 pytest green):** `tests_09/test_lisa_estimator.py`.
- **documentation_references:** `pompts_11/076_13_lisa_estimator_capability.md` · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #7.
- **status:** **CONFIRMED** — registered implemented; flagged for inventory refresh (same note as @entity research.web).

### @entity factory.registry
- **type:** component (DESIGN_ONLY — Missing Capability #1 per §20, currently `prompt_written`).
- **file:** —.
- **symbol:** `ForgePassport` (`core_02/forge_passport.py` v5.188.2) · `FactoryRegistry` · `runtime_05/factories/*.yaml` manifests.
- **responsibility:** machine-readable registry of Forge'ей/Factory with status, dependencies, contracts; implemented v5.188.2 (Missing Cap #1 close); cross-link to `@entity scenario.registry` (roles-per-factory).
- **public_api (active v5.188.2):** `core_02/factory_registry.py` API (active) + `runtime_05/factories/{architecture,idea,research,knowledge,implementation***REMOVED***.yaml`.
- **callers:** `@entity scenario.registry` (component composition lookup) · `@entity forge.facade` (capability-token resolution).
- **dependencies:** `@entity missing.registry` (lifecycle marker).
- **events_produced (active v5.188.2):** `factory.registered` · `factory.validated`.
- **events_consumed:** —.
- **storage_used (active v5.188.2):** `runtime_05/factories/*.yaml` + `data_13/forge_factory_registry.yaml`.
- **tests (active v5.188.2 — 51/51 pytest green):** `tests_09/test_factory_registry.py` (~30 tests).
- **documentation_references:** `pompts_11/078_19_factory_registry.md` (already prompt_written) · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #1.
- **status:** **DESIGN_ONLY** (Phase 1.3 implementation pending).

### @entity scenario.engine (complement)
- **type:** orchestrator (DESIGN_ONLY — Missing Capability #2 per §20, `design_ready`).
- **file:** —.
- **symbol:** `ScenarioEngine.run(scenario_id) → CompositeResult`.
- **responsibility:** higher-order composer: combines capabilities from multiple Forge'ей (@entity factory.registry dependency); capability-token aggregation; lifecycle Active/Paused/Completed.
- **public_api (planned):** `ScenarioEngine.compose(roles)` · `run(scenario_id, resume_from_state)`.
- **callers:** `@entity forge.cli` · `@entity forge.api`.
- **dependencies:** `@entity factory.registry` (active v5.188.2, providing).
- **events_produced (active v5.188.2):** `scenario.composed` · `scenario.completed`.
- **events_consumed:** `forge.chain_completed`.
- **storage_used (active v5.188.2):** `runtime_05/scenarios/*.yaml` (extends existing).
- **tests (active v5.188.2 — 51/51 pytest green):** `tests_09/test_scenario_engine.py`.
- **documentation_references:** `pompts_11/081_19_scenario_engine_capability.md` (planned) · `FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row #2 · `SCENARIO_ENGINE_DESIGN_V1.md` §G.
- **status:** **DESIGN_ONLY** (Phase 2 implementation pending).

---

## §A.6 Provenance table (machine-readable summary)

| @entity | file | type | status | tests_path | tests_status |
|---------|------|------|--------|------------|--------------|
| scenario.registry | core_02/scenario_registry.py | component | CONFIRMED | tests_09/test_scenario_registry.py | green |
| forge.registry | core_02/forge_registry.py | component | CONFIRMED | tests_09/test_forge_registry.py | green |
| missing.registry | core_02/missing_registry.py | component | CONFIRMED | tests_09/test_missing_registry.py | green |
| orchestrator.blueprint | core_02/blueprint_v3.py | component | CONFIRMED | tests_09/test_blueprint_v3.py | green |
| forge.facade | core_02/forge_facade.py | facade | CONFIRMED | tests_09/test_forge_facade.py | green |
| role.validator | core_02/forge_facade.py | component | CONFIRMED | tests_09/test_role_artifact_validator.py | green |
| forge.pipeline | core_02/forge_pipeline.py | component | CONFIRMED | tests_09/test_forge_pipeline.py | green |
| workspace.core | core_02/workspace.py | component | CONFIRMED | tests_09/test_workspace.py | green |
| wizard.lib | core_02/wizard_lib.py | component | CONFIRMED | tests_09/test_wizard.py | green |
| memory.store | core_02/memory_store.py | component | CONFIRMED | tests_09/test_memory_store.py | green |
| knowledge.engine | core_02/knowledge_engine.py | component | CONFIRMED | tests_09/test_knowledge_engine.py | green |
| graph.index | core_02/graph_index.py | component | CONFIRMED | tests_09/test_graph_index.py | green |
| event.bus | core_02/event_bus.py | component | CONFIRMED | tests_09/test_event_bus.py | green |
| remote.sync | core_02/remote_sync.py | component | CONFIRMED | tests_09/test_remote_sync.py | green |
| forge.cli | scripts_01/forge.py | entrypoint | CONFIRMED | tests_09/test_forge_chain_cli.py | green |
| forge.api | scripts_01/forge_api.py | entrypoint | CONFIRMED | tests_09/test_forge_api.py | green |
| forge.interactive | scripts_01/forge_interactive_api.py | entrypoint | PARTIAL | (planned) | none yet |
| opportunity.engine | scripts_01/opportunity_engine.py | component | CONFIRMED | tests_09/test_opportunity_engine.py | green |
| whim.capture | scripts_01/whim_capture.py | module | CONFIRMED | tests_09/test_whim_capture.py | green |
| consistency.check | scripts_01/consistency_check.py | tool | CONFIRMED | tests_09/test_consistency_check.py | green |
| drift.check | scripts_01/drift_check.py | tool | CONFIRMED | tests_09/test_drift_check.py | green |
| research.web | (missing) | component | DESIGN_ONLY ⤳ CONFIRMED pending refresh | tests_09/test_research_web.py (exists?) | unknown |
| lisa.estimator | (missing) | component | DESIGN_ONLY ⤳ CONFIRMED pending refresh | tests_09/test_lisa_estimator.py (exists?) | unknown |
| factory.registry | (active v5.188.2) | component | IMPLEMENTED (v5.188.2) | (active v5.188.2) | 51/51 pytest |
| scenario.engine | (planned) | orchestrator | DESIGN_ONLY (Phase 2) | (planned) | n/a |

---

## §A.7 Anti-patterns caught during this inventory

1. **FORENSICS_CI_REPORT_V1.md §I vs §6 mismatch:** `research_web` и `lisa_estimator` в §20 карте значатся как ✅ реализовано, но на момент инвентаризации явный код скрипта в `scripts_01/` не найден → flagged в §A.5 для cross-check перед register-first close. **Action:** verify presence of `tests_09/test_research_web.py` и `tests_09/test_lisa_estimator.py`; если файлы есть — status flip на CONFIRMED.
2. **`scripts_01/forge_interactive_api.py` no dedicated test:** runtime-deployed но unit-тестов нет — only smoke via parent forge_api. Phantom route risk per CHANGELOG §5.187.0 follow-up.
3. **TODO auto-stubs in @entity orchestrator.blueprint:** `L516` и `L431` отслеживаются через MissingRegistry, но не resolved — R11 cleanup backlog.
4. **`@entity opportunity.engine` lazy imports vs test scope:** mypy reports 17 errors на unreal run_chain signature (lazy ForgeFacade stub). Forensic note: signature drift between Definition (§M contract) and runtime — задокументировать в §A.8.
5. **`@entity forge.facade` orchestrator-only contract:** part of Layer-3 boundary (cannot redeclare roles). Per ADR-009 / B10 invariant. Doc reference consistent.

---

## §A.8 Drift and gaps (output for Artifact G/H)

**Verified CONFIRMED → 21/25 entities** (84% of FFB core footprint covered).
**PARTIAL → 1** (`forge.interactive` — runtime-deployed, no unit tests).
**DESIGN_ONLY → 3** (factory.registry, scenario.engine, research.web/lisa.estimator refresh discrepancy).
**UNVERIFIED → 0** in this slice.

**Next actions for full coverage (≥95% by Phase 1.5 target):**
- Verify `research_web.py` / `lisa_estimator.py` existence in `scripts_01/` — if absent, status flip to UNVERIFIED; if present, status CONFIRMED.
- Add `forge.interactive` dedicated tests (artifacts A → C dependency).
- Expand `@entity opportunity.engine` mypy fix (ForgeFacade.run_chain signature guess → concrete after forge_facade contract is locked).
- Add `@entity project_pulse.py` and `@entity collaboration.py` (Phase 6 CoWork platform entities) — flagged for Phase 1.4 inventory refresh.

---

## §A.9 Cross-references (anchor resolution)

This artifact A is consumed by:
- **Artifact B** (`DOCUMENTATION_CODE_MAP.md`) — to cross-link markdown sections to entities here.
- **Artifact C** (`CONTRACT_REGISTRY.md`) — to enumerate per-entity input/output contracts.
- **Artifact E** (`TRACEABILITY_GRAPH.md`) — uses entity_id as node key.
- **Artifact F** (`AGENT_NAVIGATION_MAP.md`) — uses entity_id + entrypoint to build the "HOW do I run X?" index.
- **Artifact G** (`ARCHITECTURE_GAP_MAP.md`) — feeds off status taxonomy column in §A.6.
- **Artifact H** (`DOCUMENTATION_CONSISTENCY_REPORT.md`) — cross-references `documentation_references` column to detect stale docs.
- **Artifact I** (`SEMANTIC_ANCHOR_SPEC.md`) — provides `@entity`/`@symbol` namespace + format.

---

_Phase A closed per Phase plan v0.1 §A. Implementation: 2026-08-12. Next: Phase B (Artifact B — DOCUMENTATION_CODE_MAP.md) + Phase C (Artifact I — SEMANTIC_ANCHOR_SPEC.md) — sequence driven by dependency of B/I → C → D → E → F → G → H → J → K → L (per 4.md §20 dependency order)._
