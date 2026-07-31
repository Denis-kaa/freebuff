# Architectural Debt Register

> **Document:** `docs/core/ARCHITECTURAL_DEBT.md`  
> **Source:** `scripts/drift_check.py`  
> **Generated:** 2026-07-31  
> **Status:** Living document — regenerate after each drift check  

---

## 1. Purpose

This document tracks **architectural debt** identified by the daily self-audit in `scripts/drift_check.py`. It is not a task list for features; it records structural gaps, documentation drift, and maintenance obligations that accumulate as the codebase grows.

**Principles:**

- *Debt must be observable.* Every entry references evidence (drift report, file, or test).
- *Debt must be prioritised.* Severity and owner are explicit.
- *Debt must be actionable.* Each entry has a clear remediation step and an ETA.

---

## 2. How This Document Is Maintained

1. `scripts/drift_check.py --force --report` generates the current drift report.
2. Findings are triaged: false positives are documented, real issues become debt entries.
3. This file is updated manually; a future enhancement may automate debt entry creation.
4. When a debt item is resolved, it is moved to the **Resolved Debt** section with a reference to the fixing commit.

---

## 3. Current Debt Register

### 3.1 Knowledge Index Drift

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-001 |
| **Component** | `scripts/seed_knowledge.py` / `scripts/drift_check.py` |
| **Severity** | 🟢 Low |
| **Type** | Documentation hygiene |
| **Description** | Three root-level project documents are not indexed by the knowledge engine: `AGENTS.md`, `CLAUDE.md`, `CODY.md`. These files contain session/context instructions and provider-specific rules and should be searchable alongside other project docs. |
| **Evidence** | `drift_check.py` reports "unindexed project docs" for `AGENTS.md`, `CLAUDE.md`, `CODY.md`. |
| **Impact** | Provider-specific context and agent instructions are not surfaced by `KnowledgeEngine` / RAG queries, increasing the risk of outdated or missing context in long sessions. |
| **Owner** | `scripts/seed_knowledge.py` |
| **Remediation** | Add the three files to the canonical source list in `_collect_indexed_sources()` (or the equivalent in `seed_knowledge.py`) and verify `scripts/drift_check.py` no longer reports them. |
| **ETA** | 2026-08-02 |

---

### 3.2 Directory Structure Drift — Missing Described Directories

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-002 |
| **Component** | `BUFFY.md` / `docs/core/RULES.md` tree diagrams |
| **Severity** | 🟡 Medium |
| **Type** | Documentation accuracy |
| **Description** | `drift_check.py` reports several directories/files as "described but missing": `02-specs`, `INDEX.md`, `audits`, `decisions`, `ops`, `plugin`, `projects_meta`, `scripts/monitor.sh`, `tests/...`, and `vision`. A spot check showed that most of these items **do exist** under `docs/`, not at the project root, indicating that the tree parser or the documented paths are inaccurate. The only genuinely missing item is `docs/02-specs` (or `docs/core/02-specs`). |
| **Evidence** | `drift_check.py` directory-structure drift report; manual verification confirmed `docs/INDEX.md`, `docs/audits/`, `docs/decisions/`, `docs/ops/`, `docs/plugin/`, `docs/projects_meta/`, `docs/vision/` all exist. `docs/02-specs` does not exist. |
| **Impact** | The daily drift check produces false positives, eroding trust in the report and hiding real drift. |
| **Owner** | `scripts/drift_check.py` + `BUFFY.md` authors |
| **Remediation** | 1. Fix `drift_check.py` path resolution so it looks under `docs/` for documented items. <br> 2. Either create `docs/02-specs` (or `docs/core/02-specs`) or remove it from the tree diagram. <br> 3. Clarify `scripts/monitor.sh` — it may have been renamed/removed; update docs or restore the file. |
| **ETA** | 2026-08-03 |

---

### 3.3 Directory Structure Drift — Empty `sessions/` Directory

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-003 |
| **Component** | `sessions/` directory / Stream Session management |
| **Severity** |  Low |
| **Type** | Operational / cleanup |
| **Description** | The `sessions/` directory is described in documentation but is currently empty. This is expected in a fresh checkout or after pruning, but it should be documented as a runtime directory rather than a structural drift. |
| **Evidence** | `drift_check.py` reports `sessions/` as "described but empty". |
| **Impact** | Low; the directory is a runtime artifact. However, it contributes noise to the drift report. |
| **Owner** | `scripts/stream_session.py` / `scripts/bootstrap.py` |
| **Remediation** | 1. Add a `.gitkeep` or a README inside `sessions/` explaining its purpose. <br> 2. Update `drift_check.py` to ignore runtime directories that are intentionally empty. |
| **ETA** | 2026-08-02 |

---

### 3.4 Directory Structure Drift — Undocumented Top-Level Directories

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-004 |
| **Component** | `BUFFY.md` / `docs/core/RULES.md` top-level structure |
| **Severity** | 🟢 Low |
| **Type** | Documentation completeness |
| **Description** | `drift_check.py` reports the following directories as "exists but not described": `buffy-playground/`, `cli/`, `frontend/`, `infa/`, `plugins/`, `projects/`, `screenshots/`, `services/`, `src/`, and `trash/`. Some are legitimate subsystems (`plugins/`, `projects/`, `src/`, `cli/`, `frontend/`, `buffy-playground/`, `services/`), while others (`screenshots/`, `trash/`, `infa/`) may be temporary, personal, or archive directories. |
| **Evidence** | `drift_check.py` directory-structure drift report; all listed directories exist at the project root. |
| **Impact** | The project structure is not fully reflected in the canonical tree, making onboarding harder. Some directories may be artifacts that should be ignored or removed. |
| **Owner** | Documentation maintainers |
| **Remediation** | 1. Document legitimate subsystems (`plugins/`, `projects/`, `src/`, `cli/`, `frontend/`, `buffy-playground/`, `services/`) in `BUFFY.md` / `docs/core/RULES.md`. <br> 2. Decide fate of `screenshots/`, `trash/`, and `infa/` — move to `.gitignore`, archive, or document if intentional. |
| **ETA** | 2026-08-05 |

---

### 3.5 Duplicate Telegram Bots

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-007 |
| **Component** | `scripts/telegram_bot.py` (`TelegramFreebuffBot`) + `freebuff_plugin/tgbot.py` (`ScenarioTGBot`) |
| **Severity** | 🟡 Medium |
| **Type** | Duplicate functionality (found in Stage 6 module consolidation) |
| **Description** | Two independent Telegram bots with overlapping responsibilities (message sending, command handling), each with its own test file (`tests/test_telegram_bot.py`, `tests/test_tgbot.py`) and start script (`scripts/start_telegram_bot.sh`, `scripts/start_tgbot.sh`). |
| **Evidence** | `docs/core/MODULE_CONSOLIDATION.md` §B — verified by code search: `TelegramFreebuffBot` (scripts/telegram_bot.py:82), `ScenarioTGBot` (freebuff_plugin/tgbot.py:91). |
| **Impact** | Two ways to run a Telegram bot, divergent features, duplicated maintenance. |
| **Owner** | `scripts/telegram_bot.py` + `freebuff_plugin/tgbot.py` |
| **Remediation** | 1. Introduce shared `BaseTGBot` (sending, commands, health) and make both bots inherit, keeping layer separation (scripts = notifications, freebuff_plugin = scenarios). <br> 2. Or route both through EventBus as adapters. <br> 3. Keep the older start script as a thin alias; update tests. |
| **ETA** | 2026-08-10 (after consolidation Stage 6/9 complete) |

---

## 4. False Positives and Tooling Debt

### 4.1 `drift_check.py` Path Resolution

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-005 |
| **Component** | `scripts/drift_check.py` (`check_directory_structure`) |
| **Severity** | 🟡 Medium |
| **Type** | Tool accuracy |
| **Description** | The directory-structure checker treats paths extracted from tree diagrams as relative to the project root, even when the diagram describes the `docs/` subtree. This causes `docs/INDEX.md`, `docs/audits/`, etc., to be reported as missing when they are not. |
| **Evidence** | Spot check shows `docs/INDEX.md`, `docs/audits/`, `docs/decisions/`, `docs/ops/`, `docs/plugin/`, `docs/projects_meta/`, and `docs/vision/` all exist. `drift_check.py` still flags them. |
| **Impact** | Noise in the daily report; reduces trust in the tool; hides genuine drift. |
| **Owner** | `scripts/drift_check.py` |
| **Remediation** | Improve path extraction in `_extract_tree_paths()` or post-process paths relative to the document they came from. Add unit tests for tree parsing. |
| **ETA** | 2026-08-03 |

---

## 5. Resolved Debt

### 5.1 Missing Tests for 6 Engines (S1–S6) — RESOLVED

| Field | Value |
|-------|-------|
| **ID** | DEBT-2026-07-31-006 |
| **Component** | `RAGEngine`, `CollaborationEngine`, `PresenceEngine`, `RoleEngine`, `MetricsEngine`, `ProjectPulse` |
| **Severity** | 🔴 Critical → ✅ Resolved |
| **Type** | Test coverage |
| **Description** | Test files for 6 engines were absent from `tests/` and git history despite CHANGELOG claims of 60+ tests (noted in `ARCHITECTURE_CANONICAL.md` §3.2). Restored on 2026-07-31: `test_rag_engine.py` (34), `test_collaboration.py` (48), `test_presence.py` (42), `test_roles.py` (44), `test_metrics.py` (23), `test_project_pulse.py` (34). |
| **Evidence** | `python -m pytest tests/test_rag_engine.py tests/test_collaboration.py tests/test_presence.py tests/test_roles.py tests/test_metrics.py tests/test_project_pulse.py -q` → **225 passed, 0 failed** (~56s). |
| **Resolved** | 2026-07-31, commit `c2df854` — test: restore test suites for 6 engines (close critical debt). |

---

## 6. Recommended Next Steps

1. **Fix `drift_check.py` path resolution** (DEBT-2026-07-31-005) to eliminate false positives before adding more debt entries.
2. **Index `AGENTS.md`, `CLAUDE.md`, `CODY.md`** in the knowledge engine (DEBT-2026-07-31-001).
3. **Clarify or create `docs/02-specs`** and `scripts/monitor.sh` (DEBT-2026-07-31-002).
4. **Document or ignore top-level directories** (DEBT-2026-07-31-004).

---

## 7. Related Documents

- `scripts/drift_check.py` — daily self-audit tool
- `docs/audits/DRIFT_REPORT.md` — raw daily drift report
- `docs/core/SYSTEM_INVENTORY.md` — component inventory
- `docs/vision/ROADMAP_PROMT31_WORKSPACE_OS.md` — roadmap addressing related architectural gaps

