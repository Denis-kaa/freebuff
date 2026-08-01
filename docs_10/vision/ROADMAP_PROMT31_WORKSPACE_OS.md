# Roadmap: Workspace OS Subsystems (Promt 27-31)

**Version:** 1.0.0  
**Date:** 2026-07-31  
**Status:** Draft  
**Source:** `pompts_11/027_05_projectbook_storybook.md` — `031_03_arhitekturnyy_audit.md`  
**Companion:** `docs_10/audits/ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md`

---

## 1. Principles

This roadmap implements the ideas from `027_05_projectbook_storybook.md` (Project Book / StoryBook), `028_04_notification_framework.md` (Notification Framework), `029_04_integration_registry.md` (Integration Research & Registry), `030_05_knowledge_management_system.md` (Knowledge Management System), and `031_03_arhitekturnyy_audit.md` (Architectural Audit).

**Guiding rule from `031_03_arhitekturnyy_audit.md`:**

> *Reuse First. Extend Second. Create Last.*

Therefore:
- No new engines unless existing ones cannot be extended.
- All new documentation artifacts reuse `scripts_01/engineering_memory.py`, `scripts_01/event_bus.py`, and existing Markdown templates.
- Every new module must be registered in `docs_10/core/SYSTEM_INVENTORY.md`.
- Every new integration must be registered in `docs_10/core/INTEGRATION_REGISTRY.md`.

---

## 2. Goal

Transform the project from a collection of engines into a coherent **Workspace OS** where:

- Humans and AI agents share a single source of truth about the project.
- Every significant task, decision, incident, and integration is recorded automatically.
- Notifications keep the user informed without spam.
- The architecture remains understandable as the system grows.

---

## 3. Status Legend

| Emoji | Meaning |
|-------|---------|
| ✅ | Already exists |
| 🟡 | Partial / needs extension |
| 🔴 | Missing |

---

## 4. Subsystem Roadmap

### 4.1 Knowledge Management System (KMS)

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | `KnowledgeEngine`, `RAG`, `Vector Memory`, `Engineering Memory` |
| **Gap** | Overlap between memory/knowledge/RAG/EM engines; no unified indexing policy |
| **Decision** | **Reuse.** `KnowledgeEngine` is the canonical indexer. `Engineering Memory` stores human-readable records. `MemoryEngine` keeps short-term session context. |

**Steps:**
1. Define a clear responsibility boundary:
   - `MemoryEngine` = session/working memory (short-term).
   - `KnowledgeEngine` = indexed project facts and documents (medium/long-term).
   - `Engineering Memory` = narrative/decision/incident records (long-term, human-readable).
   - `RAG` / `Vector Memory` = features of `KnowledgeEngine`, not separate engines.
2. Move `Vector Memory` logic to a backend inside `KnowledgeEngine`.
3. Make `engineering_memory.py` always index final documents into `KnowledgeEngine`.
4. Add a `knowledge_policy.md` describing what goes where.

**Deliverables:**
- `docs_10/core/KNOWLEDGE_POLICY.md`
- Refactored `scripts_01/knowledge_engine.py` (absorbs vector backend)
- `scripts_01/engineering_memory.py` auto-indexes records

---

### 4.2 Project Book

| | |
|---|---|
| **Status** | ✅ Exists |
| **Current** | `docs_10/engineering-memory/PROJECT_BOOK.md` |
| **Gap** | Manual updates; no automatic chapter generation |
| **Decision** | **Reuse.** Keep `PROJECT_BOOK.md` as the main narrative. Add automatic appendices from EM. |

**Steps:**
1. Add a `compile_project_book()` function in `scripts_01/engineering_memory.py`.
2. Generate/append chapters from EM Milestone Chronicles after each version bump.
3. Add a CLI command `python scripts_01/engineering_memory.py compile-project-book`.
4. Link `PROJECT_BOOK.md` from `docs_10/INDEX.md` and `AGENTS.md`.

**Deliverables:**
- `scripts_01/engineering_memory.py :: compile_project_book()`
- Updated `docs_10/engineering-memory/PROJECT_BOOK.md`

---

### 4.3 Project Retrospective System

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | EM templates in `docs_10/engineering-memory/templates/task_retrospective.md` |
| **Gap** | No automatic trigger on task completion |
| **Decision** | **Extend.** Subscribe to `EventBus` and auto-draft retros when thresholds are met. |

**Steps:**
1. Define `EMTrigger` thresholds (LOC > 100, duration > 10 min, or task failed).
2. Add EventBus subscriber in `scripts_01/event_subscribers.py` or `engineering_memory.py`.
3. Create a draft in `MemoryEngine.WORKING`.
4. Promote to `docs_10/engineering-memory/retrospectives/` on human/AI approval.
5. Add tests in `tests_09/test_engineering_memory.py`.

**Deliverables:**
- `scripts_01/engineering_memory.py` auto-retro subscriber
- `tests_09/test_engineering_memory.py` retro trigger tests
- New retrospectives in `docs_10/engineering-memory/retrospectives/`

---

### 4.4 Decision Log

| | |
|---|---|
| **Status** | ✅ Exists |
| **Current** | `docs_10/decisions/DECISIONS.md` (индекс) + `docs_10/engineering-memory/decisions/` (ADR) + EM Decision Journal template |
| **Gap** | Two separate sources of decisions |
| **Decision** | **Merge.** Move core decisions into `docs_10/engineering-memory/decisions/` and make `DECISIONS.md` an index. |

**Steps:**
1. Convert each entry in `DECISIONS.md` to a Decision Journal file under `docs_10/engineering-memory/decisions/`.
2. Replace `DECISIONS.md` with an auto-generated index.
3. Add `record_decision()` to create new Decision Journals directly in EM.
4. Link new decisions in `PROJECT_BOOK.md` and `AGENTS.md`.

**Deliverables:**
- `docs_10/engineering-memory/decisions/` directory with migrated ADRs
- `docs_10/decisions/DECISIONS.md` as an index → done
- Updated `scripts_01/engineering_memory.py` helpers

---

### 4.5 Architectural Debt

| | |
|---|---|
| **Status** | 🔴 Missing |
| **Current** | `drift_check.py` detects drift; `ARCHITECTURE_REVIEW.md` discusses issues |
| **Gap** | No formal architectural debt log |
| **Decision** | **Create.** Add `docs_10/core/ARCHITECTURAL_DEBT.md` populated by `drift_check.py`. |

**Steps:**
1. Define debt entry format: ID, date, component, description, severity, blocker, owner, ETA.
2. Add `drift_check.py` mode that outputs debt candidates.
3. Create `docs_10/core/ARCHITECTURAL_DEBT.md` and seed it from current drift findings.
4. Run `drift_check.py` in CI to keep the log fresh.

**Deliverables:**
- `docs_10/core/ARCHITECTURAL_DEBT.md`
- `scripts_01/drift_check.py` debt-report mode

---

### 4.6 Module Registry

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | `docs_10/core/SYSTEM_INVENTORY.md`, `docs_10/core/PROJECT_REGISTRY.md`, `docs_10/projects_meta/FILE_REGISTRY.md` |
| **Gap** | Manual, gets outdated, no freshness check |
| **Decision** | **Extend.** Generate `docs_10/core/MODULE_REGISTRY.md` from code + existing docs. |

**Steps:**
1. Create a registry schema: module name, file path, owner, status, dependencies, related tests, related docs.
2. Add a generator script (e.g., `scripts_01/generate_module_registry.py`) that scans `scripts_01/`, `core_02/`, `freebuff_plugin_03/`, `plugins_04/`.
3. Compare generated registry with `SYSTEM_INVENTORY.md` and flag drift.
4. Add a CI/pre-commit check that fails if a module is not registered.

**Deliverables:**
- `docs_10/core/MODULE_REGISTRY.md`
- `scripts_01/generate_module_registry.py`
- Pre-commit or `doctor.py` check

---

### 4.7 Agent Registry

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | `AGENTS.md`, `scripts_01/roles.py`, `scripts_01/presence.py`, `freebuff_plugin_03/acp_protocol.py` |
| **Gap** | No unified registry of agents, roles, and capabilities |
| **Decision** | **Extend.** Create `docs_10/core/AGENT_REGISTRY.md` synced with `roles.py` and `AgentMesh`. |

**Steps:**
1. Define agent schema: name, role, capabilities, tools, files touched, docs updated.
2. Add helper to export `roles.py` data into the registry.
3. Add helper to export `AgentMesh` agents from `scripts_01/distributed_agents.py`.
4. Link `AGENT_REGISTRY.md` in `AGENTS.md`.

**Deliverables:**
- `docs_10/core/AGENT_REGISTRY.md`
- Export helpers in `scripts_01/roles.py` and `scripts_01/distributed_agents.py`

---

### 4.8 Integration Registry

| | |
|---|---|
| **Status** | 🔴 Missing |
| **Current** | `runtime_05/providers/`, `plugins_04/`, `MARKETPLACE.md`, `INTEGRATION_CONTRACT.md` |
| **Gap** | No single map of all external integrations |
| **Decision** | **Create.** Add `docs_10/core/INTEGRATION_REGISTRY.md` listing all integrations with status and owner. |

**Steps:**
1. Inventory all integrations: MCP, Telegram, Cloudflare, Termux:API, LLM providers, plugins.
2. For each integration record: name, type, purpose, API/auth, status, risks, files, owner.
3. Add a generator script or maintain manually with freshness checks.
4. Link registry from `docs_10/INDEX.md`.

**Deliverables:**
- `docs_10/core/INTEGRATION_REGISTRY.md`
- Integration checklist in `scripts_01/doctor.py`

---

### 4.9 Lifecycle Management

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | `EventBus`, `bootstrap.py`, `ProjectPulse`, `Orchestrator` |
| **Gap** | No uniform phase-gated lifecycle for long tasks |
| **Decision** | **Extend.** Standardize lifecycle events in `Orchestrator` and `freebuff_cli.py`. |

**Steps:**
1. Define lifecycle events: `lifecycle.init`, `lifecycle.work`, `lifecycle.verify`, `lifecycle.teardown`.
2. Update `Orchestrator` to publish these events at phase boundaries.
3. Update `notification.py` and `ProjectPulse` to listen to lifecycle events.
4. Add tests in `tests_09/test_orchestrator.py`.

**Deliverables:**
- `scripts_01/orchestrator.py` lifecycle event publishing
- Updated `scripts_01/project_pulse.py` subscriber
- Lifecycle tests

---

### 4.10 Notification System

| | |
|---|---|
| **Status** | ✅ Exists |
| **Current** | `scripts_01/notification.py` |
| **Gap** | No progress/stage/long-operation notifications |
| **Decision** | **Extend.** Make `notification.py` listen to `EventBus` and emit stage/progress notifications. |

**Steps:**
1. Define notification events: `task.started`, `task.stage_changed`, `task.progress`, `task.completed`, `task.failed`, `task.warning`.
2. Add EventBus subscriber in `scripts_01/notification.py`.
3. Add progress heartbeat for long operations.
4. Add configuration: global quiet mode, completion-only, all-events.
5. Add tests.

**Deliverables:**
- `scripts_01/notification.py` EventBus subscriber
- Notification configuration file or env vars
- `tests_09/test_notification.py` event-driven tests

---

### 4.11 Story / History of the Project

| | |
|---|---|
| **Status** | ✅ Exists |
| **Current** | `PROJECT_BOOK.md`, `CHANGELOG.md`, audit reports |
| **Gap** | Automated chronicle assembly |
| **Decision** | **Reuse.** Keep `PROJECT_BOOK.md` and `CHANGELOG.md`. Add auto-assembly from EM. |

**Steps:**
1. Add `compile_chronicle()` in `engineering_memory.py`.
2. Generate timeline from git commits + EM records + Project Pulse.
3. Append to `PROJECT_BOOK.md` appendix.

**Deliverables:**
- `scripts_01/engineering_memory.py :: compile_chronicle()`
- Auto-generated timeline appendix

---

### 4.12 Architectural Map

| | |
|---|---|
| **Status** | 🟡 Partial |
| **Current** | `ARCHITECTURE.md`, `SYSTEM_INVENTORY.md`, `ARCHITECTURE_3.0.md` |
| **Gap** | No dynamic or periodically regenerated visual/structural map |
| **Decision** | **Extend.** Add a generator that produces Mermaid/ASCII maps from registry data. |

**Steps:**
1. Add `scripts_01/generate_architecture_map.py`.
2. Read `MODULE_REGISTRY.md`, `AGENT_REGISTRY.md`, `INTEGRATION_REGISTRY.md`.
3. Output Mermaid or ASCII diagram to `docs_10/core/ARCHITECTURE_MAP.md`.
4. Run on each commit or nightly.

**Deliverables:**
- `scripts_01/generate_architecture_map.py`
- `docs_10/core/ARCHITECTURE_MAP.md`

---

## 5. Execution Order

### Phase A — Immediate (this session / next task)

1. Extend `scripts_01/notification.py` with EventBus progress/stage notifications (Promt 28).
2. Create `docs_10/core/ARCHITECTURAL_DEBT.md` from current `drift_check.py` findings.
3. Merge `DECISIONS.md` into `docs_10/engineering-memory/decisions/` (Promt 27 / 31).

### Phase B — Short-term (next 1-3 sessions)

4. Implement EM auto-triggers for `task.completed`, `task.failed`, `git.merge`, `system.error`.
5. Create `docs_10/core/INTEGRATION_REGISTRY.md`.
6. Generate `docs_10/core/MODULE_REGISTRY.md` from code.
7. Generate `docs_10/core/AGENT_REGISTRY.md` from `roles.py` / `AgentMesh`.
8. Define `KNOWLEDGE_POLICY.md` and consolidate RAG/Vector under `KnowledgeEngine`.

### Phase C — Future (after Phase B)

9. Implement full lifecycle event FSM in `Orchestrator`.
10. Auto-compile `PROJECT_BOOK.md` and chronicle timeline.
11. Auto-generate `ARCHITECTURE_MAP.md` from registries.
12. Add CI checks for registry freshness and untracked modules.

---

## 6. Anti-Goals

- **Do not create a new storage engine.** Reuse `KnowledgeEngine` and `MemoryEngine`.
- **Do not create a second Project Book.** Extend `PROJECT_BOOK.md` instead.
- **Do not duplicate decision logs.** Merge `DECISIONS.md` into EM.
- **Do not build new integrations before the registry exists.** Map first, integrate second.
- **Do not auto-document every event.** Use thresholds to avoid noise.

---

## 7. Success Criteria

- [ ***REMOVED*** All 12 subsystems have a documented status and owner.
- [ ***REMOVED*** `docs_10/core/` contains: `MODULE_REGISTRY.md`, `AGENT_REGISTRY.md`, `INTEGRATION_REGISTRY.md`, `ARCHITECTURAL_DEBT.md`.
- [x***REMOVED*** `docs_10/engineering-memory/decisions/` holds individual ADRs; `docs_10/decisions/DECISIONS.md` remains as an index.
- [ ***REMOVED*** `scripts_01/notification.py` emits progress/stage notifications from EventBus.
- [ ***REMOVED*** `scripts_01/engineering_memory.py` auto-drafts retrospectives and incidents.
- [ ***REMOVED*** `scripts_01/drift_check.py` feeds `ARCHITECTURAL_DEBT.md`.
- [ ***REMOVED*** `doctor.py` fails on untracked/unregistered modules.
- [ ***REMOVED*** Tests for new EM subscribers and notification events pass.

---

## 8. Related Documents

- `docs_10/audits/ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md` — full audit with evidence
- `docs_10/engineering-memory/ARCHITECTURE.md` — EM architecture
- `docs_10/engineering-memory/PROJECT_BOOK.md` — project narrative
- `docs_10/core/SYSTEM_INVENTORY.md` — existing component inventory
- `docs_10/vision/ROADMAP.md` — technical phase roadmap
