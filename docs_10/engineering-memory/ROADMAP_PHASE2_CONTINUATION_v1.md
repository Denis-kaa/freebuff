# ROADMAP — Phase 2 Continuation (Autonomous Execution Mode)

| Поле | Значение |
|------|----------|
| **Документ ID** | ROADMAP-P2-CONT-001 |
| **Версия** | 1.0 (initial, 2026-08-09) |
| **Источник директивы** | `pompts_11/068_07_autonomous_project_executor.md` — «AUTONOMOUS PROJECT EXECUTOR» mode |
| **Target Document** | `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` |
| **Tracker** | `docs_10/engineering-memory/AUDIT_WS_OS_P65_RECAP.md` |
| **Текущее состояние** | Phase 2 CLOSED (§4-§14 SHIPed), 32 R-entries registered (R-1..R-32), v1.6 published 2026-08-09 |
| **Цель** | Autonomous completion §15-§39 (25 sections, Phase 3-4 deferred) |
| **Sequencing** | Phase 3 first (§15-§26 primitives) → Phase 4 synthesis (§27-§32) → convergence spec (§33) → narrative close (§34-§39) |
| **PIE** | Promote, Iterate, Evaluate — per `core_02/LESSONS.md` CON-N protocol |

---

## §1. CONTEXT & EXECUTION AUTHORITY

**Mission:** Autonomous completion of Workspace OS Architecture Research (§15-§39), applying `068_07_autonomous_project_executor.md` directives:

- **Cycle:** UNDERSTAND → DECOMPOSE → ROADMAP → EXECUTE → VERIFY → IMPROVE → NEXT STEP
- **Execution mode:** NO ask-permission; continue until BLOCKER or session-end
- **Quality gates:** 8-point checklist per section (per §11 section above)
- **Self-correction:** CREATE → CRITIQUE → IMPROVE → VERIFY

**Established section cycle precedent (from §13/§14 SHIPed):**

1. Fill stub with 8 subsections (§X.1-§X.8)
2. Real evidence file:line refs (no invented facts)
3. Marker discipline: ~24 markers (16 [ФАКТ***REMOVED*** + 7 [АРХ***REMOVED*** + 1 [ГИП***REMOVED*** typical)
4. 5 explicit gaps → 5 R-NN appendices in RECAP
5. Audit doc: 16 primary + 8 secondary + 5 gaps → TRUST 8.5-9.0/10
6. RECAP v1.N → v1.N+1 bump + R-NN+1..R-NN+5 append
7. INDEX.md + DOCUMENT_REGISTRY.md sync (counters + entries)
8. CHANGELOG.md [5.NNN.0***REMOVED*** entry (v1.N+1 publish checkpoint)
9. STEPS.md Step N+1 append (CON-58 publication marker)

**Estimated work per section:** ~25-30 min cycle; 25 sections = ~10-15 hours total (multi-session).

---

## §2. EXECUTION ROADMAP TABLE (24 steps + 1 DEFERRED)

| Step | Section | Topic | Phase | Pre-req | Predicted R-NN | Audit Doc | Subagents Needed | Status |
|------|---------|-------|-------|---------|---------------|-----------|------------------|--------|
| 1 | §15 | Long-Lived Project / Project container | 3 | R-2, R-18 | R-33..R-37 | `AUDIT_WS_OS_P65_§15_V1.md` | basher, thinker, reviewer | QUEUED |
| 2 | §16 | Memory (10 KO kinds, semantic_layer, learning_loop) | 3 | RFC OM v1.0 v5.92.0, MVP v5.102.0 §16.1 | R-38..R-42 | `AUDIT_WS_OS_P65_§16_V1.md` | basher, thinker, reviewer | QUEUED |
| 3 | §17 | Learning Loop (AFC pattern per OM RFC §7) | 3 | §16 | R-43..R-47 | `AUDIT_WS_OS_P65_§17_V1.md` | thinker, reviewer | QUEUED |
| 4 | §18 | Artifact System (versioning+lineage+provenance) | 3 | §15, §16 | R-48..R-52 | `AUDIT_WS_OS_P65_§18_V1.md` | basher, researcher | QUEUED |
| 5 | §19 | Evidence + Provenance (NDA-aware constraint propagation) | 3 | §18 | R-53..R-57 | `AUDIT_WS_OS_P65_§19_V1.md` | thinker, reviewer | QUEUED |
| 6 | §20 | Decision System (DIS: ARE/CAE/TDA/PC/EP) | 3 | RFC DIS v1 v5.94.0, §19 | R-58..R-62 | `AUDIT_WS_OS_P65_§20_V1.md` | thinker, reviewer | QUEUED |
| 7 | §21 | Feedback pipeline (TG round-trip + Event Bus) | 3 | §17, §20 | R-63..R-67 | `AUDIT_WS_OS_P65_§21_V1.md` | thinker | QUEUED |
| 8 | §22 | Workspace as Operating Environment (architectural narrative) | 3 | §15-§21 | R-68..R-72 | `AUDIT_WS_OS_P65_§22_V1.md` | thinker, reviewer | QUEUED |
| 9 | §23 | Cross-factory orchestration (Forge⇆Scenario) | 3 | §8, §9, §22 | R-73..R-77 | `AUDIT_WS_OS_P65_§23_V1.md` | basher, thinker, reviewer | QUEUED |
| 10 | §24 | Reusability (Skill/Forge/Factory/Scenario/Project) | 3 | §23 | R-78..R-82 | `AUDIT_WS_OS_P65_§24_V1.md` | thinker | QUEUED |
| 11 | §25 | Security & Governance (AG per Architecture Governance 055_18) | 3 | §19, §20 | R-83..R-87 | `AUDIT_WS_OS_P65_§25_V1.md` | thinker, reviewer | QUEUED |
| 12 | §26 | Failure modes (30+ via CON-/ANTI- in LESSONS) | 3 | §20, §25 | R-88..R-92 | `AUDIT_WS_OS_P65_§26_V1.md` | basher, thinker | QUEUED |
| **13** | **§27** | **Overengineering audit (POR = 14 principles)** | **4** | **§15-§26** | **R-93..R-97** | **`AUDIT_WS_OS_P65_§27_V1.md`** | **reviewer × 3** | **QUEUED** |
| 14 | §28 | Real-world stress test (5+ types: vkusvill+interior_planner+diet+realtor+tg_messenger) | 4 | §4-§7, §22 | R-98..R-102 | `AUDIT_WS_OS_P65_§28_V1.md` | thinker | QUEUED |
| 15 | §29 | Architecture vertical (Forge RFC §2 + Manifest v2) | 4 | RFC Forge v1.2, FR-001 §2a | R-103..R-107 | `AUDIT_WS_OS_P65_§29_V1.md` | thinker, basher | QUEUED |
| 16 | §30 | Final pipeline synthesis (cross-link vkusvill_research/08) | 4 | §28, §29 | R-108..R-112 | `AUDIT_WS_OS_P65_§30_V1.md` | thinker | QUEUED |
| 17 | §31 | Workspace OS definition (formal: data layer + control plane + orchestration surface) | 4 | §22, §30 | R-113..R-117 | `AUDIT_WS_OS_P65_§31_V1.md` | thinker, reviewer | QUEUED |
| 18 | §32 | Boundaries (LEVIATHAN Cat-A/B/C inventory integration) | 4 | §31, LEV v1.1 | R-118..R-122 | `AUDIT_WS_OS_P65_§32_V1.md` | basher, reviewer | QUEUED |
| **19** | **§33** | **Minimal v0.1 spec (MUST/SHOULD/LATER)** | **4** | **R-1..R-122 (BLOCKED until §15-§32 complete)** | **R-123..R-127** | **`AUDIT_WS_OS_P65_§33_V1.md`** | **thinker x2, reviewer** | **DEFERRED** |
| 20 | §34 | Final Narrative 1: Workspace OS Impact Story | 4 | §33 | R-128..R-131 | `AUDIT_WS_OS_P65_§34_V1.md` | thinker | QUEUED |
| 21 | §35 | Final Narrative 2: Adoption paths (who/when/how) | 4 | §34 | R-132..R-135 | `AUDIT_WS_OS_P65_§35_V1.md` | thinker | QUEUED |
| 22 | §36 | Final Narrative 3: Limitations + Anti-patterns catalog | 4 | §35 | R-136..R-139 | `AUDIT_WS_OS_P65_§36_V1.md` | thinker | QUEUED |
| 23 | §37 | Final Narrative 4: Future extensions + Research frontiers | 4 | §36 | R-140..R-143 | `AUDIT_WS_OS_P65_§37_V1.md` | thinker | QUEUED |
| 24 | §38 | Final Narrative 5: 14 Success Questions (validate Workspace OS) | 4 | §37 | R-144..R-148 | `AUDIT_WS_OS_P65_§38_V1.md` | reviewer | QUEUED |
| 25 | §39 | Mission statement close (per `pompts_11/066_09_workspace_os_kus_vkusvill.md` §0: «сделать проект») | 4 | §38 | R-149..R-152 | `AUDIT_WS_OS_P65_§39_V1.md` | thinker | QUEUED |

> **§33 (Step 19) strictly DEFERRED** until ALL of §15-§32 cycles are COMPLETED.

---

## §3. DEPENDENCIES GRAPH

```
[Phase 3 primitives***REMOVED***
   §15 (Long-Lived) ────────┬─────► §16 (Memory)
                            │             │
                            ▼             ▼
                       §18 (Artif.) ◄── §17 (Learning Loop)
                            │
                            ▼
                       §19 (Evidence)
                            │
                            ▼
                       §20 (Decision System) ──► §21 (Feedback)
                            │                         │
                            ▼                         ▼
                       §25 (Security) ◄────── §26 (Failure modes)
                                                      │
[Phase 4 synthesis***REMOVED***                                    │
   §27 (Overeng) ◄── §15-§26 ──► §28 (Stress-test)    │
                            │                │        │
                            ▼                ▼        ▼
                       §23 (Cross-fact) ─► §24 (Reusability)
                            │
                            ▼
                       §22 (OperatingEnv ◄─── §21, §17)
                            │
                            ▼
                       §29 (Architecture vertical)
                            │
                            ▼
                       §30 (Pipeline synthesis)
                            │
                            ▼
                       §31 (WS-OS definition) ──► §32 (Boundaries)
                            │
                            ▼ (BLOCKED until all above)
                       §33 (v0.1 spec) ─────────────────┐
                                                       │
                                                       ▼
                       §34 → §35 → §36 → §37 → §38 → §39 (Mission close)
```

**Critical path (§15 → §16 → §18 → §19 → §20 → §31 → §33):** longest dependency chain. Parallel nodes: §17, §21, §23-§26 can be interleaved.

---

## §4. SEQUENCING POLICY

1. **Phase 3 (Steps 1-12, ~7-8 hours):** §15-§26 — build foundational primitives (Memory, Artifacts, Feedback, Decisions)
2. **Phase 4 (Steps 13-18, ~3-4 hours):** §27-§32 — synthesize across primitives (Overengineering audit, Stress test, Boundaries)
3. **Convergence spec (Step 19, ~30 мин):** §33 — DEFERRED until Steps 1-18 complete; consumes all R-1..R-122
4. **Narrative close (Steps 20-25, ~3-4 hours):** §34-§39 — final chapters, mission statement

**Per section flow (no ask-permission):**

```
QUEUED → IN_PROGRESS → [fill script***REMOVED*** → [verify***REMOVED*** → [audit pass***REMOVED*** → [sync ops***REMOVED*** → COMPLETED
```

**Default verification gate per step:**

- [ ***REMOVED*** 8 subsections present
- [ ***REMOVED*** ~24 markers distributed ([ФАКТ***REMOVED***[АРХ***REMOVED***[ГИП***REMOVED***)
- [ ***REMOVED*** 5 explicit gaps → 5 R-NN appendices
- [ ***REMOVED*** Audit doc with TRUST ≥8.5/10
- [ ***REMOVED*** RECAP v1.N → v1.N+1 bumped
- [ ***REMOVED*** INDEX + DOCUMENT_REGISTRY synced
- [ ***REMOVED*** CHANGELOG entry prepended
- [ ***REMOVED*** STEPS Step N+1 appended

---

## §5. QUALITY GATES (per-cycle 8-point checklist)

For every Step N (applied recursively):

1. **[ ***REMOVED*** Target section** in `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` holds strictly **8 subsections** (§X.1-§X.8)
2. **[ ***REMOVED*** Markers count:** ~24 inline markers distributed (16 [ФАКТ***REMOVED*** + 7 [АРХ***REMOVED*** + 1 [ГИП***REMOVED*** expected; ±25% tolerance per topic)
3. **[ ***REMOVED*** Audit pass doc:** created at `docs_10/engineering-memory/AUDIT_WS_OS_P65_§XX_V1.md` with 16 primary + 8 secondary + 5 gaps claims
4. **[ ***REMOVED*** TRUST score:** audit doc reports TRUST ≥8.5/10 (SHIPPABLE)
5. **[ ***REMOVED*** RECAP sync:** v1.N → v1.N+1 bump + R-NN+1..R-NN+5 newly appended
6. **[ ***REMOVED*** INDEX + DOC REGISTRY:** newly added AND counters bumped (ACTIVE +1, Audit ×N→×N+1, engineering-memory +1)
7. **[ ***REMOVED*** CHANGELOG:** `[5.NNN.0***REMOVED***` entry prepended (v1.N+1 publish checkpoint)
8. **[ ***REMOVED*** STEPS:** `Step N+1` appended at end of `projects_17/vkusvill_research/STEPS.md` (CON-58 publication marker)

Mark ALL 8 = COMPLETED before advancing to next step.

---

## §6. AUTONOMOUS STOP CONDITIONS

Execution halts ONLY under:

1. **Real BLOCKER:** Hard missing input (e.g., file not found, mandatory source missing)
2. **Quality failure:** 8 consecutive `NEEDS-FIX` verdicts from `code-reviewer-minimax-m3` in single section → escalate to user with full context dump
3. **Session timeout:** ~30-50 min per turn — preserve state via RECAP bump + STEPS append before yielding
4. **COMPLETION:** Step 25 (§39) marked COMPLETE → final validation pass + project closeout

**NOT stop conditions:**
- "Section topic is hard" → use thinker agent → continue
- "Audit score is moderate (not SHIPPABLE)" → fix → re-audit → continue
- "External source missing" → mark [НЕТ ДАННЫХ***REMOVED*** in fill → continue

---

## §7. ARTIFACT TRACKING

| A-ID | Artifact | Status | Version | Dependencies | Quality Gate |
|------|----------|--------|---------|--------------|--------------|
| A-001 | `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` | IN PROGRESS | v1.6 (target: v1.31) | All §X fills | Gate 1+2 per cycle |
| A-002 | `AUDIT_WS_OS_P65_RECAP.md` | IN PROGRESS | v1.5 (target: v1.30) | All §X audits | Gate 5 per cycle |
| A-003..A-027 | `AUDIT_WS_OS_P65_§XX_V1.md` (`XX` ∈ {15,16,...,39***REMOVED***) | QUEUED | v1.0 each | §XX fill | Gate 3+4 per cycle |
| A-028 | `docs_10/INDEX.md` | IN PROGRESS | current | A-003..A-027 | Gate 6 per cycle |
| A-029 | `docs_10/DOCUMENT_REGISTRY.md` | IN PROGRESS | current | A-003..A-027 | Gate 6 per cycle |
| A-030 | `CHANGELOG.md` | IN PROGRESS | current | All audits | Gate 7 per cycle |
| A-031 | `projects_17/vkusvill_research/STEPS.md` | IN PROGRESS | current | Per cycle | Gate 8 per cycle |
| **A-032** | **`ROADMAP_PHASE2_CONTINUATION_v1.md` (NEW)** | **CREATE 2026-08-09** | **v1.0** | **068_07_autonomous_project_executor directive** | **[EXISTING***REMOVED*** ✓** |

---

## §8. PREDICTED METRICS POST-EXECUTION

- **Total R-entries:** ~152 (32 existing + ~120 new from Steps 1-25) [per cycle: 5 new R-NN per section × 24 sections***REMOVED***
- **Total markers applied:** ~600 new inline markers (§15-§39) [per section ~24 markers × 25 sections***REMOVED***
- **Total audit docs:** 25 new `.md` files (`AUDIT_WS_OS_P65_§15..§39_V1.md`)
- **Document version target:** v1.6 → **v1.31** upon completion (one bump per section + conceptual chapter bump)
- **RECAP version:** v1.5 → **v1.30** (one bump per audit)
- **CHANGELOG entries:** ~25 new `[5.NNN.0***REMOVED***` entries
- **DOCUMENT_REGISTRY ACTIVE counter:** audit ×8 → ×33, engineering-memory +25, ACTIVE +25
- **Estimated time:** ~10-15 hours total compute (multi-session) — pass multiple Freebuff sessions

---

## §9. FIRST EXECUTION STEP — Step 1: §15 Long-Lived Project

**Starting immediately after this ROADMAP ships.**

Inputs available:
- `core_02/workspace.py` (Workspace/Project containers L-1/L-2)
- `data_13/context.db` (10+ tables, sessions/messages/checkpoints)
- `projects_17/vkusvill_research/` (de-facto Project instance — vkusvill_demo without formal project.yaml)
- `projects_17/interior_planner/` (Wizard-driven 17-role run v5.64.0)
- §3.3 inventory: ✅ `workspace.py L-1` `[обновлено 2026-08-09 — ранее «🟢 Hypothesis» → Production***REMOVED***`
- §4 Stage 1 + §5 Stage 1: Project(yaml) gap already noted as [АРХ***REMOVED***

Predicted 8 subsections of §15:
- §15.1 Hypothesis: Workspace = L-1 container, Project = L-2 isolated instance
- §15.2 Q1-Q8 trace (8 questions on workspace.py / context.db / project.yaml)
- §15.3 3-level architecture (Workspace L-1 / Project L-2 / Snapshot/checkpoint)
- §15.4 Boundary demarcation (Workspace vs Project vs session vs task)
- §15.5 Coverage tally
- §15.6 5 gaps G-LLP-1..5 → R-33..R-37
- §15.7 Q-recap
- §15.8 Verdict + cross-link to §33 Minimal v0.1

Predicted audit doc:
- `AUDIT_WS_OS_P65_§15_V1.md` (16 primary C-LLP-01..16 + 8 secondary C-LS-1..8 + 5 gaps G-LLP-1..5, TRUST 8.5-9.0/10)

Predicted subagents:
- basher (state validation)
- thinker (architecture framing)
- reviewer (audit SHIP/NEEDS-FIX verdict)

**EXECUTE now.** ↓

---

## §10. PROMISE & HONEST FRAMING

- **Honest:** путь всего 25 секций × ~25-30 мин = ~10-15 часов. Multi-session required. Current session может выполнить Step 1 (§15) и начать Step 2 (§16). Дальше — следующая сессия resumes per CON-N recovery.
- **Quality first:** НЕ жертвовать MUST ради OPTIONAL. Каждый fill обогащается real evidence, не invented claims.
- **Conservative scale:** AGENTS_NOTES-style meta-markers in each section (🔵 proven / 🟡 partial / ❌ gap) for transparency.
- **DON'T STOP:** until BLOCKER or session-end. Continue autonomous execution per `068_07_autonomous_project_executor.md`.

---

## §11. REFERENCES

- `pompts_11/068_07_autonomous_project_executor.md` — autonomous execution doctrine (this roadmap follows)
- `pompts_11/066_09_workspace_os_kus_vkusvill.md` — research source directive (§0-§39)
- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` — target doc
- `docs_10/engineering-memory/AUDIT_WS_OS_P65_RECAP.md` — tracker (v1.5)
- `docs_10/engineering-memory/AUDIT_WS_OS_P65_§14_V1.md` — last SHIP template
- `core_02/LESSONS.md` (~1178 lines) — CON-/ANTI-/CAN protocol
- `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` — §16/§17 design source
- `RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md` — §20 design source
- `RFC_BUFFY_FORGE_V1.md` v1.2 — §15/§18/§23 cross-link
- `LEVIATHAN_INVENTORY_V1.md` v1.1 — §32 source

---
