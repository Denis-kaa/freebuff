# Architectural Audit Report: Project Buffy / Workspace OS

**Document:** `docs_10/audits/ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md`  
**Date:** 2026-07-31  
**Author:** Principal Software Architect / Lead Systems Auditor  
**Objective:** Deep architectural audit prior to implementing ideas from prompts 27-31.  
**Core Principle:** *Reuse First. Extend Second. Create Last.*

---

## 1. Project State Summary

### Scale & Evolution

Project Buffy/FreeBuff has rapidly evolved from a simple Termux AI assistant into **Workspace OS**, an agentic platform with distributed capabilities. The system leverages an `EventBus`, SQLite-based `MemoryEngine` and `KnowledgeEngine`, multi-provider `ModelGateway`, and a growing plugin ecosystem.

### Key Numbers (as of 2026-07-31)

| Metric | Value |
|--------|-------|
| Total tests | ~1280 passed, 1 skipped, 0 failures |
| Core scripts | 40+ modules in `scripts_01/` |
| Plugins | 4 in `plugins_04/`, 3 recovered from bytecode |
| Documentation files | 78+ markdown files in `docs_10/` |
| MCP tools | 12+ tools + runtime_05/bootstrap extensions |
| Runtime providers | 3 YAML manifests in `runtime_05/providers/` |

### Recent Milestones & Crises

- **2026-07-28:** Genesis of FreeBuff 2.0 (`core_02/router.py`, `ContextManager`, `MemoryEngine`, 500+ tests) and integration with MCP & Cloudflare Tunnels.
- **2026-07-30:** Massive engine influx: `MetricsEngine`, Vector Memory, `RoleEngine`, `PresenceEngine`, `CollaborationEngine`, RAG 2.0, Plugins, Notifications.
- **2026-07-31 (The Crucible):** Two major security audits led to removal of `shell=True`/`exec` and Bearer Auth for MCP. Simultaneously, uncommitted (`untracked`) files including `scripts_01/metrics.py` and 10 other modules were lost, forcing recovery from compiled `.pyc` bytecode.
- **Current Shift:** The system's complexity dictates that **Engineering Memory (EM)** is now a first-class entity. Documentation must be living, automated, and human-readable to prevent context loss between agent sessions.

---

## 2. Architectural Map of Existing Components (Relevant to Target Subsystems)

```
─────────────────────────────────────────────────────────────────────┐
│                        Workspace OS                                 │
─────────────────────────────────────────────────────────────────────┤
│  EventBus (scripts_01/event_bus.py)                                    │
│   ├── ContextManager (SQLite sessions_15/checkpoints)                   │
│   ├── MemoryEngine (5-level memory)                                  │
│   ├── KnowledgeEngine (FTS5/TF-IDF/Graph/Vector)                     │
│   ├── Orchestrator (FSM/DAG workflow)                                │
│   ├── Plugin API (plugins_04/)                                          │
│   ├── Project Pulse (git + event feed)                               │
│   ├── Presence / Collaboration / Distributed Agents                  │
│   └── Engineering Memory (scripts_01/engineering_memory.py)             │
├─────────────────────────────────────────────────────────────────────┤
│  Documentation Layer                                                │
│   ├── docs_10/engineering-memory/PROJECT_BOOK.md                       │
│   ├── docs_10/engineering-memory/ARCHITECTURE.md                       │
│   ├── docs_10/core/SYSTEM_INVENTORY.md                                 │
│   ├── docs_10/core/PROJECT_REGISTRY.md                                 │
│   ├── docs_10/decisions/DECISIONS.md                                   │
│   └── docs_10/audits/DRIFT_REPORT.md                                   │
├─────────────────────────────────────────────────────────────────────┤
│  External Interfaces                                                │
│   ├── MCP Server / FastAPI / Cloudflare Tunnel                     │
│   ├── Runtime Abstraction Layer (freebuff_plugin_03/runtime/)           │
│   ├── Telegram Bot (scripts_01/telegram_bot.py)                        │
│   └── Notification (scripts_01/notification.py)                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Per-Subsystem Analysis

| # | Subsystem | Status | Existing Components | Gaps / Overlaps | Recommended Approach | Risk |
|---|-----------|--------|---------------------|-----------------|----------------------|------|
| 1 | **Knowledge Management System** | Partial | `KnowledgeEngine`, `RAG`, `Vector Memory`, `docs_10/engineering-memory/` | Overlap between `KnowledgeEngine`, `RAG_engine`, `Vector Memory` and `Engineering Memory` | **Reuse/Extend:** Consolidate indexing around `engineering_memory.py`. No new engine. | Low |
| 2 | **Project Book** | Exists | `docs_10/engineering-memory/PROJECT_BOOK.md` | Updated manually or via massive EM prompts | **Reuse:** Keep as main narrative. Automate appending via EM triggers. | Low |
| 3 | **Project Retrospective System** | Partial | `docs_10/engineering-memory/retrospectives/`, EM templates | Missing automatic triggers on `task.completed` / significant events | **Extend:** Connect `EventBus` to EM Orchestrator to draft retros automatically. | Medium |
| 4 | **Decision Log** | Exists | `docs_10/decisions/DECISIONS.md`, EM `decisions/` templates | Duplication between core `DECISIONS.md` and EM decision journals | **Merge:** Unify under `docs_10/engineering-memory/decisions/`. | Low |
| 5 | **Architectural Debt** | Missing | `drift_check.py` touches drift, `ARCHITECTURE_REVIEW.md` | No formal debt log tied to drift findings | **Create:** Add `docs_10/core/ARCHITECTURAL_DEBT.md` linked to `drift_check.py` outputs. | Low |
| 6 | **Module Registry** | Partial | `docs_10/core/SYSTEM_INVENTORY.md`, `docs_10/core/PROJECT_REGISTRY.md`, `FILE_REGISTRY.md` | Gets outdated quickly (untracked-modules crisis) | **Extend:** Automate updates via `scripts_01/doctor.py` or a new registry generator. | Medium |
| 7 | **Agent Registry** | Partial | `AGENTS.md`, `scripts_01/roles.py`, `scripts_01/presence.py`, `freebuff_plugin_03/acp_protocol.py` | `AGENTS.md` is session checkpoint, not formal capability registry | **Extend:** Formalize `docs_10/core/AGENT_REGISTRY.md` synced with `roles.py` / `AgentMesh`. | Low |
| 8 | **Integration Registry** | Missing | Dispersed in MCP plugins, `runtime_05/providers/`, `MARKETPLACE.md` | No unified view of external integrations | **Create:** Implement `docs_10/core/INTEGRATION_REGISTRY.md`. | Low |
| 9 | **Lifecycle Management** | Partial | `EventBus`, `bootstrap.py`, `ProjectPulse`, `Orchestrator` | Lifecycle exists but lacks strict phase-gating (init → work → verify → teardown) | **Extend:** Standardize task wrappers emitting lifecycle events. | High |
| 10 | **Notification System** | Exists | `scripts_01/notification.py`, visual summary | Needs alignment with Promt27 (progress, long ops, stages) | **Extend:** Add `ProgressTracker` and EventBus hooks. | Medium |
| 11 | **Story/History** | Exists | `PROJECT_BOOK.md`, `CHANGELOG.md`, audit reports | Already implemented as Engineering Memory | **Reuse:** Feed it better data from EM triggers. | Low |
| 12 | **Architectural Map** | Partial | `ARCHITECTURE.md`, `SYSTEM_INVENTORY.md`, `ARCHITECTURE_3.0.md` | Missing dynamic visual generation/dependency trees | **Extend:** Add generator from `drift_check.py` / `SYSTEM_INVENTORY.md`. | Low |

---

## 4. GAP Analysis Matrix

| Idea | Current Implementation | What's Missing | Reuse? | New Module? | Effort | Risk |
|------|------------------------|---------------|--------|-------------|--------|------|
| KMS | `KnowledgeEngine` + `engineering_memory.py` | Unified indexing policy, deduplication of RAG/Vector/Memory | Yes | No | Medium | Medium |
| Project Book | `PROJECT_BOOK.md` | Auto-update on milestones | Yes | No | Low | Low |
| Retrospectives | EM templates | EventBus subscribers + threshold logic | Yes | No | Medium | Medium |
| Decision Log | `DECISIONS.md` + EM templates | Single source of truth | Yes | No | Low | Low |
| Architectural Debt | `drift_check.py` | Dedicated debt document + triage workflow | Yes | No | Low | Low |
| Module Registry | `SYSTEM_INVENTORY.md`, `PROJECT_REGISTRY.md` | Auto-generation from code + freshness checks | Yes | No | Medium | Medium |
| Agent Registry | `AGENTS.md`, `roles.py`, `presence.py` | Unified capability/role/availability registry | Yes | No | Medium | Low |
| Integration Registry | Scattered across plugins_04/providers | Centralized registry of all external integrations | Yes | No | Medium | Low |
| Lifecycle Management | `EventBus` + `bootstrap.py` | Phase-gated FSM for tasks | Yes | No | High | High |
| Notification System | `notification.py` | Progress tracking, stage events, long-op heartbeat | Yes | No | Medium | Medium |
| Story/History | `PROJECT_BOOK.md`, `CHANGELOG.md` | Automated chronicle assembly | Yes | No | Low | Low |
| Architectural Map | `ARCHITECTURE.md`, `SYSTEM_INVENTORY.md` | Dynamic/periodically regenerated maps | Yes | No | Low | Low |

---

## 5. Prioritized Implementation Roadmap

### Guiding Constraint

No new engines. All implementations extend `EventBus`, `KnowledgeEngine`, and `engineering_memory.py`.

### Immediate Priority (Hardening & Validation)

1. **Notification System (Promt 28):** Extend `scripts_01/notification.py` to listen to `EventBus` for long-running operations, task stage changes, and completion/failure. Add progress heartbeat and stage-based notifications.
2. **Registry Consolidation (Promt 29/31):** Merge `docs_10/decisions/DECISIONS.md` into the EM structure under `docs_10/engineering-memory/decisions/`. Create `docs_10/core/MODULE_REGISTRY.md` and `docs_10/core/AGENT_REGISTRY.md` using `scripts_01/doctor.py` and existing metadata as the data source.

### Short-term Priority (Knowledge & Automation)

3. **Automated KMS Triggers (Promt 27/29):** Update `scripts_01/engineering_memory.py` to subscribe to `task.completed`, `task.failed`, `git.merge`, and `system.error` via `EventBus`. Auto-draft Task Retrospectives and Incident Reports based on thresholds (LOC, duration, severity).
4. **Integration Layer Audit (Promt 29):** Create `docs_10/core/INTEGRATION_REGISTRY.md` mapping all MCP tools, plugins, runtime providers, and external API gateways. Do not build new integrations until this map is approved.
5. **Architectural Debt Tracker:** Add a hook in `scripts_01/drift_check.py` to log structural violations and outdated docs to `docs_10/core/ARCHITECTURAL_DEBT.md`.

### Future Priority (Workspace OS Refinement)

6. **Full Lifecycle Management:** Enforce a strict FSM in the `Orchestrator` that broadcasts phase shifts to the Notification System and Project Pulse. Add lifecycle events: `lifecycle.init`, `lifecycle.work`, `lifecycle.verify`, `lifecycle.teardown`.

---

## 6. Main Risks and Recommendations

### Risk 1: Component Duplication (High)

- *Context:* `MemoryEngine`, `KnowledgeEngine`, `RAG_engine`, `Vector Memory`, and `Engineering Memory` overlap in responsibilities.
- *Recommendation:* **Halt all new engine creation.** Unify RAG and Vector Memory under `KnowledgeEngine`. Restrict `MemoryEngine` to short-term session context. Use `Engineering Memory` only for long-term human-readable records.

### Risk 2: The "Untracked Ghost" Syndrome (Critical)

- *Context:* The 2026-07-31 crisis proved that relying on `__pycache__` to restore untracked files is unacceptable.
- *Recommendation:* The new Module Registry MUST run a pre-commit or `doctor.py` check to fail if a running module is not tracked in Git or documented in `SYSTEM_INVENTORY.md`.

### Risk 3: Over-Documentation (Medium)

- *Context:* Automatically generating a retro for *every* event will flood the KMS.
- *Recommendation:* Set strict thresholds in `EMTrigger` (e.g., `LOC > 100`, `duration > 10m`, `severity = high`) before triggering auto-documentation in `engineering_memory.py`.

### Risk 4: Lifecycle Gaps (High)

- *Context:* Long operations lack uniform phase tracking and teardown.
- *Recommendation:* Standardize lifecycle wrappers in `Orchestrator` that always emit `lifecycle.*` events and call cleanup in `finally` blocks.

---

## 7. Final Verdict

The project architecture is highly capable but suffering from rapid-growth fragmentation. The Workspace OS pivot is correct. We do not need new systems for Prompts 27-31; we need to string the existing `EventBus`, `Engineering Memory`, and Markdown schemas together into a cohesive, automated lifecycle.

The highest leverage next steps are:

1. Halt engine duplication and consolidate under `KnowledgeEngine`.
2. Implement EventBus-driven EM auto-drafting with thresholds.
3. Create living registries (Module, Agent, Integration) auto-generated from code/docs.
4. Extend `notification.py` into a progress-aware notification framework.
5. Add a formal Architectural Debt tracker linked to drift checks.

---

## Appendix: Key Files Referenced

- `pompts_11/027_05_projectbook_storybook.md` — Project Book / StoryBook evolution
- `pompts_11/028_04_notification_framework.md` — Notification framework
- `pompts_11/029_04_integration_registry.md` — Integration research and registry
- `pompts_11/030_05_knowledge_management_system.md` — Knowledge Management System design
- `pompts_11/031_03_arhitekturnyy_audit.md` — Architectural audit mandate
- `docs_10/engineering-memory/PROJECT_BOOK.md`
- `docs_10/engineering-memory/ARCHITECTURE.md`
- `docs_10/core/SYSTEM_INVENTORY.md`
- `docs_10/core/PROJECT_REGISTRY.md`
- `docs_10/decisions/DECISIONS.md`
- `scripts_01/engineering_memory.py`
- `scripts_01/drift_check.py`
- `scripts_01/doctor.py`
- `scripts_01/notification.py`
- `scripts_01/event_bus.py`
