# EXECUTION_PATHS.md — Реальные execution paths

> **Статус:** FORENSIC FACT (из кода)

---

## 1. Главный путь: Factory vertical slice

```
User → CLI/TG/MCP
  ↓
Opportunity (whim_capture.promote() OR manual)
  ↓
ScenarioIntelligence.discover(opportunity_id) → ScenarioCandidate[***REMOVED***
  ↓
ScenarioIntelligence.evaluate(opportunity_id) → ranked candidates
  ↓
ScenarioIntelligence.select(opportunity_id) → ScenarioDecision
  ↓
BaseFactory.execute(opp):
  1. _derive_capability(opp) → capability token
  2. resolve(capability) → (FactoryPassport, ForgePassport)
  3. build_execution_request(opp, capability) → ExecutionRequest
  4. _resolve_project(opp) → Project.load(projects_17/<id>)
  5. ForgeFacade.run_chain(project, role_ids) → ChainRun
  6. normalize_output(run, opp, request) → artifact dict
  7. _accumulate(opp, artifact, run) → MemoryStore + LearningLoop
  ↓
Artifact → MemoryStore (kind=candidate)
```

**Ключевые файлы:**
- scripts_01/scenario_intelligence.py — decision
- core_02/factory_base.py — vertical slice
- core_02/factory_registry.py — capability→factory/forge
- core_02/forge_facade.py — run_chain
- core_02/forge_pipeline.py — 6 stages

## 2. Путь Whim → Opportunity

```
User → whim_capture capture <body> --project-id X
  ↓
Whim (NEW)
  ↓
whim_capture triage <id> → heuristic classify (KEEP/DISCARD/PROMOTE_CANDIDATE)
  ↓
whim_capture promote <id> → opportunity_engine.discover_candidates (lazy)
  ↓
Opportunity (READY)
  ↓
[затем путь #1***REMOVED***
```

**Ключевые файлы:** scripts_01/whim_capture.py, scripts_01/opportunity_engine.py

## 3. Путь Orchestrator (multi-step задача)

```
User → python scripts_01/orchestrator.py run "Goal"
  ↓
Orchestrator.run_workflow(goal):
  1. check_existing_context(goal) → Knowledge search (Rule 8)
  2. DefaultPlanner.plan(goal) → Step[***REMOVED***
  3. ThreadPoolExecutor: execute steps (DAG resolution)
  4. StepValidator.validate(step)
  5. save_workflow() → MemoryEngine
  ↓
Workflow (COMPLETED/FAILED)
```

**Ключевые файлы:** scripts_01/orchestrator.py

## 4. Путь Forge CLI (прямой)

```
User → python scripts_01/forge.py forge <project>
  ↓
ForgeFacade.initiate_forge(project, role_id)
  ↓
ForgePipeline.run() → PipelineRun (6 stages)
  ↓
ForgeRegistry.record_run(project_id, run) → status update (DEPLOYED/FAILED)
```

**Ключевые файлы:** scripts_01/forge.py, core_02/forge_facade.py, core_02/forge_registry.py

## 5. Путь Forge chain-runner (14 ролей)

```
ForgeFacade.run_chain(project, role_ids=PIPELINE_CHAIN)
  ↓
Pre-flight: RoleArtifactValidator.validate() → ValidationSummary
  ↓
Per-role:
  - LIGHT (explainer/lisa/risk/decomposer/architect/auditor/documenter/retrospective)
    → check_only (existence) OR generate (ADR-016 executor)
  - HEAVY (developer/tester/fixer/acceptance)
    → initiate_forge full cycle
  - CONDITIONAL (frontend: web-only, devops: always)
    → full_cycle or conditional_skip
  ↓
ChainRun (stage-by-stage report)
```

**Ключевые файлы:** core_02/forge_facade.py (run_chain)

## 6. Путь MCP

```
External → MCP JSON-RPC 2.0
  ↓
McpSessionManager.handle_initialize
  → handle_tools_list → tools
  → handle_tools_call → execute tool
  → handle_resources_list/read
  → handle_prompts_list/get
```

**Ключевые файлы:** scripts_01/mcp_server.py

## 7. Путь Telegram

```
User → TG /task <text>
  ↓
telegram_bot.py (или freebuff_plugin_03/tgbot.py ScenarioTGBot)
  ↓
Scenario engine / task dispatch
  ↓
[затем путь #1 или #3***REMOVED***
```

**Ключевые файлы:** scripts_01/telegram_bot.py, freebuff_plugin_03/tgbot.py
