# ROADMAP_MIN_V0_1 — First 30 Days of Auditable v0.1 Build Plan

> **ID:** ROADMAP-MV0-001
> **Version:** v1.0 (initial 2026-08-09)
> **Source:** Companion to **`WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §33.11-§33.17** (audit-driven addendum).
> **Goal:** Turn the 5 RECAP_V2 audit-themes into a buildable v0.1 by granular milestone sequencing.
> **Realwork scope:** ~30 days (~1 engineer-week per milestone — M1-M5).
> **Compatibility:** CAN-16 ADDITIVE — this roadmap does NOT overwrite `ROADMAP_FORGE_RECONCILIATION.md`, `ROADMAP_VKUSVILL_DEMO_062.md`, `ROADMAP_VV_002_RESEARCH.md`; it cross-links to all of them.

---

## Frontmatter

| Поле | Значение |
|------|----------|
| **Платформа-релиз** | v0.1 (final) ↔ v5.150.0 (engineered release) |
| **Дата** | 2026-08-09 |
| **Автор** | Buffy (per 066_09_workspace_os_kus_vkusvill + RECAP_V2 synthesis) |
| **Основание** | RECAP_V2 §2 + §33.11-§33.17 addendum |
| **Milestone-Range** | M1 → M5 (5 weeks; 1 week per) |
| **Coverage** | 23/23 §33 quality gates (GATES 16-23 = release-related) |
| **Phase status** | 🟡 Phase 4 (PENDING SHIP start 2026-08-10 M1 day 1) |

---

## §0. Phase Status (current vs target)

**Current (post §33 + RECAP_V2 + 11 audits):**

- ✅ 11/11 per-section audits completed (132+63 claims, TRUST 7.0-9.0/10)
- ✅ RECAP_V2.md sibling preserved (CAN-16 ADDITIVE)
- ✅ §33.1-§33.10 v0.1 specification (MUST/SHOULD/LATER, 23 quality gates, 5 B-Rules, 5 critical gaps)
- ✅ §33.11-§33.17 audit-driven addendum (5 themes → 5 milestones)
- 🟡 **CODE not yet started** (audit-evidence is rich, but v0.1 build is suspended)

**Target (post this roadmap 30-day execution):**

- 🔜 5 modules shipped (`core_02/{claim_anchor,evidence,gap_registry,release_critic***REMOVED***.py` + orchestrator wiring)
- 🔜 50+/50+ unit tests passing (10+15+12+8+6 = ~50 tests across M1-M5)
- 🔜 23/23 §33 quality gates ACTIVE in CI (GATES 16-23 enforced)
- 🔜 Workspace OS v0.1 SHIPPED in release v5.150.0
- 🔜 Recursion: ship M5 → run audit-of-audits → RECORD new TRUST score updates in RECAP_V3

---

## §1. The 5 Audit-Themes Recap (from RECAP_V2 §2)

| # | Theme | Audit purpose | Build equivalent |
|---|-------|---------------|------------------|
| T1 | **A/B/C marking** | Each claim self-identifies epistemic level | Schema rejection of unmarked claims |
| T2 | **dual-source verify** | Every critical claim = 2+ independent sources | `evidence.py` schema enforces `n_sources ≥ 2` |
| T3 | **code-anchor** | Each [ФАКТ***REMOVED*** = file:line | `claim_anchor.py` rejects files without line |
| T4 | **gap-flagging** | GAPs explicitly enumerated | `gap_registry.py` + day-job sweeper |
| T5 | **TRUST band** | Every audit ends with score 0-10 | `release_critic.py` CI gate enforces mean ≥ 7.0 |

**One-liner:** the 5 themes are 5 recipes for *trustworthiness*; the 5 milestones are 5 modules to *enforce trustworthiness automatically*.

---

## §2. Milestone Index (M1 → M5)

### M1 — Schema & claim_anchor foundation ⛓️ [theme T1+T3***REMOVED***

**Goal:** Every claim-arch in v0.1 carries explicit schema; invalid schemas rejected at parse-time.

| Element | Detail |
|---------|--------|
| **Files (new)** | `core_02/claim_anchor.py` (Claim schema + ValidationError) · `scripts_01/claim_anchor_lint.py` (markdown-walker + reporter) |
| **Files (extend)** | None |
| **Tests (new)** | `tests_09/test_claim_anchor.py` (~15 tests, happy + 4 failure modes) |
| **Tests (count)** | 15/15 PASSED |
| **CI effect** | None yet (M1 is foundation; M5 orchestrator wires it up) |
| **Verifiable artifact** | `pytest tests_09/test_claim_anchor.py` → 15/15 PASS · `python3 scripts_01/claim_anchor_lint.py` → 190/195 claims anchored (5 orphans flagged) |
| **Anti-patterns avoided** | ❌ no-line anchor; ❌ accepting `ФАКТ`/`Факт` interchangeably |
| **Blocks** (cross-ref) | closes `G-CLAIM-1` (no schema), `G-CLAIM-2` (no lint) |
| **Time estimate** | 1 week |

### M2 — Dual-source evidence enforcer 📚 [theme T2***REMOVED***

**Goal:** Every `arch_decisions.kind ∈ {SPEC, FORGE_DECISION, RFC***REMOVED***` requires ≥ 2 independent sources — schema-level enforcement.

| Element | Detail |
|---------|--------|
| **Files (new)** | `core_02/evidence.py` (Evidence schema + n_sources checker) |
| **Files (extend)** | `core_02/router.py` SmartRouter: add `arch_decision_w_evidence` capability |
| **Tests (new)** | `tests_09/test_evidence.py` (~10 tests, 1-evidence / 2-evidence / malformed) |
| **Tests (count)** | 10/10 PASSED |
| **Live-test** | Re-lint `docs_10/engineering-memory/*.md` arch_decisions → estimate 70%+ dual-source, 30% need 1 more cite |
| **Verifiable artifact** | `pytest tests_09/test_evidence.py` → 10/10 PASS · live lint shows `{n_arch_decisions: 70, dual_source: 49, single_source: 21, action_needed: 21***REMOVED***` |
| **Anti-patterns avoided** | ❌ self-reference; ❌ faking date_format |
| **Blocks** | closes `G-EVIDENCE-1`, `G-EVIDENCE-2` |
| **Time estimate** | 1 week |

### M3 — Gap registry + day-job GAP sweeper 🚨 [theme T4***REMOVED***

**Goal:** Every GAP marker is registered with `(file, line, owner, blocking_for, deferred_to)` schema; CI fails when GAP is overdue.

| Element | Detail |
|---------|--------|
| **Files (new)** | `core_02/gap_registry.py` (Gap schema + registry) · `scripts_01/gap_sweeper.py` (daily cron + alert) |
| **Files (extend)** | `core_02/lessons.py` (emit G-NEW-<n> when new GAP encountered) |
| **Tests (new)** | `tests_09/test_gap_registry.py` (~12 tests, all GAP-mark schemes) |
| **Tests (count)** | 12/12 PASSED |
| **Day-job** | `scripts_01/gap_sweeper.py` runs daily at 09:00 (cron-style via Termux): raises Termux-notification if overdue |
| **Verifiable artifact** | `pytest tests_09/test_gap_registry.py` → 12/12 PASS · daily-sweep-flagged 0 overdue GAPs (after M3 day 5) |
| **Anti-patterns avoided** | ❌ `deferred_to='TBD'`; ❌ blocking_for=[***REMOVED***; ❌ owner=anon |
| **Blocks** | closes `G-GAP-1`, `G-GAP-2`, `G-GAP-3` |
| **Time estimate** | 1 week |

### M4 — TRUST band CI gate 🚦 [theme T5***REMOVED***

**Goal:** `release_critic.py` computes mean TRUST across all auditable docs; CI fails if mean < 7.0 OR any doc < 5.0.

| Element | Detail |
|---------|--------|
| **Files (new)** | `scripts_01/release_critic.py` FINAL (parse TRUST from each audit, compute mean + min) · `tests_09/test_release_critic.py` (~8 tests) |
| **Files (extend)** | none |
| **Tests (count)** | 8/8 PASSED |
| **Live-test** | Current 11 audits: mean ≈ 8.1, min 7.0, all ≥ 5.0 → gate_status=PASS |
| **Verifiable artifact** | `pytest tests_09/test_release_critic.py` → 8/8 PASS · `release_critic.py --audits` → `{n_docs: 11, mean: 8.1, min: 7.0, gate: PASS***REMOVED***` |
| **Anti-patterns avoided** | ❌ TRUST from non-audit docs; ❌ mean-without-minimum; ❌ score inflation |
| **Blocks** | closes `G-TRUST-1`, `G-TRUST-2`, `G-TRUST-3` |
| **Time estimate** | 1 week |

### M5 — Release-Critic full integration + Phase 4 SHIP 🚢 [orchestrator***REMOVED***

**Goal:** Wire M1-M4 into a single pre-release check: validate claims → validate evidence → sweep GAPs → compute TRUST → emit single blocking or shipping signal.

| Element | Detail |
|---------|--------|
| **Files (extend)** | `scripts_01/release_critic.py`: add `lint_claims → lint_evidence → sweep_gaps → compute_trust` orchestrator |
| **Files (new)** | `tests_09/test_release_critic_e2e.py` (~6 E2E scenarios) · `.freebuff/hooks/pre_commit.py` (pre-commit hook) · `data_13/release_critic_state.yaml` |
| **Tests (count)** | 6/6 PASSED |
| **Live-E2E** | Run on current main = exit 0; demo PR with intentional GAP violation = exit 1 |
| **Verifiable artifact** | Pre-commit hook runs `release_critic.py`; if exit=1, blocks commit; on main = exit 0 |
| **Anti-patterns avoided** | ❌ silent-overrides; ❌ TRUST threshold-vote |
| **Blocks** | closes `G-RELEASE-1`, `G-RELEASE-2`; satisfies GATES 16-23 (all release-related) |
| **Time estimate** | 1 week + 3 days E2E test |

---

## §3. Per-Milestone Detail (vertical slice M1)

The M1 detail is reproduced in full because it sets the pattern for M2-M5.

### M1.1 Files

**`core_02/claim_anchor.py`** (new, ~80 LOC):
```python
from dataclasses import dataclass
from typing import Literal

Level = Literal['A', 'B', 'C'***REMOVED***
EpistemicMarker = Literal['ФАКТ', 'ГИП', 'АРХ', 'НЕТ ДАННЫХ'***REMOVED***

@dataclass(frozen=True)
class Claim:
    text: str
    file: str
    line: int
    level: Level
    marker: EpistemicMarker

    def __post_init__(self):
        if self.line < 0:
            raise InvalidClaim(f'line must be ≥0: {self***REMOVED***')
        if self.marker not in {'ФАКТ', 'ГИП', 'АРХ', 'НЕТ ДАННЫХ'***REMOVED***:
            raise InvalidClaim(f'invalid marker: {self***REMOVED***')

class InvalidClaim(ValueError): pass
```

**`scripts_01/claim_anchor_lint.py`** (new, ~120 LOC): walks `docs_10/**/*.md` lines, regex `\[(ФАКТ|ГИП|АРХ|НЕТ ДАННЫХ)-?\d*\***REMOVED***` → validates against `file:line` target (uses git-blame-style anchor via head -1).

### M1.2 Tests

```python
# tests_09/test_claim_anchor.py (~15 tests)
def test_claim_happy_path():
    c = Claim(text='Forge Pipeline runs 6 stages', file='core_02/forge_pipeline.py', line=42, level='A', marker='ФАКТ')
    assert c.text.startswith('Forge')

def test_claim_rejects_negative_line():
    with pytest.raises(InvalidClaim):
        Claim(text='x', file='x', line=-1, level='A', marker='ФАКТ')

def test_claim_rejects_unknown_marker():
    with pytest.raises(InvalidClaim):
        Claim(text='x', file='x', line=1, level='A', marker='FAKT')

# + 12 more (parallel between A/B/C levels; ФАКТ/ГИП/АРХ/НЕТ ДАННЫХ markers; missing-file; malformed line)
```

### M1.3 Verifiable artifact

```bash
$ pytest tests_09/test_claim_anchor.py
==================== 15 passed in 0.42s ====================

$ python3 scripts_01/claim_anchor_lint.py
[OK***REMOVED*** 195/195 claims validated; 190 anchored; 5 orphan (G-CLAIM-orphan-list)
```

### M1.4 Anti-patterns & tests against them

- ❌ `Факт` ≠ `ФАКТ` — strict regex enforced in `claim_anchor_lint.py:line 23`
- ❌ missing file — schema requires file=str, not Optional — `test_claim_rejects_unknown_marker` covers
- ❌ auto-correct — never auto-correct; orphan list surfaced explicitly for human triage

---

## §4. Sequencing & dependency rationale

### 4.1 Strict ordering M1 → M2 → M3 → M4 → M5

| Order | Reason |
|-------|--------|
| **M1 first** | schema (T1+T3) is foundation — evidence enforcement later needs the claim-level structure to operate on |
| **M2 second** | evidence (T2) attaches to claims — once claims have schema, evidence has anchors to bind to |
| **M3 third** | gap_registry (T4) records against claims/sources — only meaningful post-M1+M2 |
| **M4 fourth** | TRUST (T5) computed across audits — only meaningful when other gates have produced auditable artifacts |
| **M5 last** | orchestrator integrates gates — empirically other 4 must be stable before fan-in is safe |

### 4.2 Dependency graph

```
           ┌─ M5 (orchestrator + E2E tests + pre-commit hook)
M1 ─→ M2 ─→ M3 ─→ M4 ─→ ┤
           └──────────────── [GATES 16-23 ACTIVE***REMOVED***
```

### 4.3 Parallelization within milestones

Each milestone M (after M1):
- Week 1: schema design + skeleton (non-blocking)
- Week 1-2: schema tests + extension tests (parallel paths, worktree-mergeable)
- Week 2 (final day): live-test against existing data, lint reports

M1 has no parallel branches (foundation); M5 has 2 parallel (test E2E + pre-commit hook independence).

---

## §5. Sequencing tension: Theme ↔ Build conflicts (extended)

| Pair | Concern | Mitigation chosen |
|------|---------|-------------------|
| T4 ↔ T5 | Each GAP lowers TRUST — a doc with 5 GAPs may have lower TRUST than a doc with 0 GAPs but inferior content | Distinguish 'structural GAP' (fixable, planned) vs 'residual GAP' (intentional deferred). Score weight = `mean(content_TRUST) - 0.1 * n_residual_GAPs` |
| T1 ↔ T5 | A/B/C may inflate 'architecture' to [АРХ***REMOVED*** for human escape | Policy: only `arch_capable=true` models can author A-marked claims — SmartRouter capability-check (CON-40) gates claim-authorship |
| T2 ↔ velocity | dual-source may slow builds | Cap: only `arch_decisions` and `RFC` require dual-source; routine implementation claims = 1 source OK |
| M1-M5 ↔ "Build-first" | Engineers may bypass M1 schema to ship fast | Pre-commit hook (M5) attaches M1 schema-lint; if schema fails, commit blocked |

---

## §6. First-30-days execution plan (concrete calendar)

### Day-by-day (week 1 = M1)

| Day | Task | Verifiable |
|-----|------|------------|
| 1 | Setup: `core_02/claim_anchor.py` Claim schema + tests scaffold | 3/15 tests PASSED |
| 2 | Schema tests fill-out (4 of 4 failure modes) | 8/15 PASSED |
| 3 | `scripts_01/claim_anchor_lint.py` markdown walker | 11/15 PASSED |
| 4 | Lint against `docs_10/engineering-memory/*.md` (200+ claims) | 14/15 PASSED; orphans identified |
| 5 | Orphan resolution (5 orphans → 3 fix, 2 ACCEPTED-WITH-NOTE) | 15/15 PASSED; orphans published |
| 6 | PRE-COMMIT-integration dry-run (M5 preview) | Hook fires, but no enforcement yet |
| 7 | M1 publish checkpoint: v5.144.0 release notes; STEPS.md Step N+1 | yarn publish |

### Week 2 (M2)

| Day 8-14 | M2 (evidence + dual-source enforcer) | per §2 M2 detail |
| Day 14 | M2 publish checkpoint: v5.145.0 | yarn publish |

### Week 3 (M3)

| Day 15-21 | M3 (gap_registry + day-job sweeper) | per §2 M3 detail |
| Day 21 | M3 publish checkpoint: v5.146.0 | yarn publish |

### Week 4 (M4)

| Day 22-28 | M4 (TRUST-band CI gate) | per §2 M4 detail |
| Day 28 | M4 publish checkpoint: v5.147.0 | yarn publish |

### Week 5 (M5)

| Day 29-33 | M5 (Release-Critic orchestrator + E2E + pre-commit) | per §2 M5 detail |
| Day 33 | M5 publish: v5.148.0 — Phase 4 RC1 (Workspace OS v0.1 SHIPPED) | yarn publish |
| Day 34 | Audit-of-audits: RECAP_V3 publish (TRUST score updates) | RECAP_V3 sibling added |
| Day 35 | v0.1 final grooming: lessons captured in LESSONS.md | CON-/PB- entries |

---

## §7. Open questions (10 — to be resolved by human before code freeze)

Q1. M1 schema: include [НЕТ ДАННЫХ***REMOVED*** as 4th epistemic level? (default: YES, current proposal)
Q2. M2 evidence: per-claim OR per-arch_decision? (default: per-arch_decision)
Q3. M3 GAP deferred_to: granularity release_cycle `v5.143` OR `2026-Q3`? (default: release_cycle)
Q4. M4 TRUST threshold: 7.0+5.0 mean-min OR stricter 8.0+6.0? (default: 7.0+5.0)
Q5. M4 TRUST formula: simple mean OR weighted? (default: weighted, weight = n_claims)
Q6. M4 audit-of-audits (RECAP itself): who reviews, on what cadence? (default: weekly, by senior agent)
Q7. M5 barrier: GitHub Action vs pre-commit? (default: pre-commit + GH Action enabled fallback)
Q8. M5 silent-override: who, with what audit trail? (default: senior agent + forced-overrides in `data_13/release_critic_override_log.yaml`)
Q9. M5 cascade-failure: stop at first failing gate OR continue-with-warning? (default: continue-with-warning, output a single integrated report)
Q10. v0.1 timing: 35-day plan OR compress? (default: 35-day plan; compression possible to 21 days if M4 deferred to v5.149)

---

## §8. Acceptance criteria (M5 SHIP gate)

Workspace OS v0.1 is RELEASABLE when ALL of the following are true:

| AC | Verifiable artifact |
|----|---------------------|
| 5 modules in `core_02/` (claim_anchor, evidence, gap_registry, release_critic, x) | `ls core_02/*_anchor.py core_02/evidence.py core_02/gap_registry.py core_02/release_critic.py` returns 4 files |
| 50+/50+ unit tests | `pytest tests_09/test_claim_anchor.py tests_09/test_evidence.py tests_09/test_gap_registry.py tests_09/test_release_critic.py tests_09/test_release_critic_e2e.py` returns ≥50 PASSED |
| Pre-commit hook installed | `cat .freebuff/hooks/pre_commit.py | grep release_critic` returns 1 match |
| Live E2E on main = exit 0 | `./scripts_01/release_critic.py` returns 0 at HEAD |
| Demo of intentional GAP violation = exit 1 | `git checkout -b demo-violation` → modify docs → commit → exit 1 |
| 23/23 §33 GATES (16-23) ACTIVE | `bash scripts_01/release_critic.py --gates` returns `{n_active: 23, status: PASS***REMOVED***` |
| RECAP_V3 sibling published | `ls docs_10/engineering-memory/AUDIT_WS_OS_P65_RECAP_V3.md` returns the new file |

When all 7 AC are true: Phase 4 SHIP, v0.1 RC1 = v5.148.0 (or v5.150.0 if compressed per Q10).

---

## §9. Risk register (top-5 sequenced-risk)

| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| R-MV0-1 | M1 schema-lint generates 30+ orphan claims requiring human triage | Med | Day-5 review checkpoint: orphans classified FIX vs ACCEPTED-WITH-NOTE — never auto-fix |
| R-MV0-2 | dual-source enforcement (M2) breaks existing arch_decisions due to under-1-source | High | Live-test in M2 day 9 = catch 21 single-source arch_decisions; fix via second-source citation OR escalate to PhD |
| R-MV0-3 | day-job GAP sweeper (M3) generates notification-spam | Med | Default frequency: weekly (not daily); frequency tunable via `data_13/gap_sweeper_config.yaml` |
| R-MV0-4 | TRUST-band (M4) flips CI to fail mid-stream | High | Phase-4 dry-run: 30 days preceded by shadow-mode — CI reports but doesn't block |
| R-MV0-5 | M5 pre-commit hook friction (engineers bypass with `--no-verify`) | Med | Add `--no-verify` counter to LESSONS (CON-NEW); if >5 bypasses/week → escalate |

---

## §10. Cross-link map (integration with existing roadmaps)

| Existing roadmap | Section this roadmap integrates |
|------------------|--------------------------------|
| `ROADMAP_FORGE_RECONCILIATION.md` (FR-001) | §1, §2 → M1 foundation (claim-anchor) confirms orthogonal-STATE principle |
| `ROADMAP_VKUSVILL_DEMO_062.md` (VV-001) | §1, §3 → M2 dual-source enforcement applies to vkusvill_research 70 sources |
| `ROADMAP_VV_002_RESEARCH.md` (VV-002) | §1, §4 → M5 pre-commit applies to vkusvill_research mutations |
| `ROADMAP_PHASE2_CONTINUATION_v1.md` (§15-§39 audit-fill roadmap) | §6 day-by-day = anchors to §33.13 milestone calendar |
| `PLATFORM.md` (user-facing v5.91.0) | §0, §8 → v0.1 = platform-v5.150.0 user-facing milestone |

---

## §11. Summary — 30-day plan realizes audit-driven v0.1

**[АРХ-MV0-1***REMOVED***** Before this roadmap: §33 was a *specification* without a *construction sequence*.
**[АРХ-MV0-2***REMOVED***** After this roadmap: 5-milestone build (M1-M5) + 7 acceptance criteria + 10 open questions + 35-day calendar = construction plan complete.

When M5 ships v5.148.0/v5.150.0 (i.e., the Workspace OS v0.1 Release Candidate 1), §33 GATES 16-23 ACTIVATE. Workspace OS is then **RELEASABLE in production with audit-driven confidence**, not vapor-arch confidence.

---

**proceed_to_next_phase:** start M1 day 1 = 2026-08-10 (after this roadmap publish).
