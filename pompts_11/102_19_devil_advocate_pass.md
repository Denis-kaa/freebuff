# pompts_11/102_19_devil_advocate_pass.md — Devil's Advocate Pass (v5.189.66)

## 0. Status

- **Канонический id:** `devil_advocate_pass` (AGENTS.md §5 vocabulary contract).
- **Lifecycle (REGISTER-FIRST):**
  - `registered` — `data_13/missing_registry.yaml` row 476 (kind=`module`, factory=`thinker`).
  - ✅ `prompt_written` — this file.
  - → `implemented` — `scripts_01/devil_advocate_pass.py` (~340 LOC).
- **Версия:** v5.189.66 (2026-08-20).
- **Связанные ADR:** ADR-016 (fail-safe semantics), ADR-018 (state-machine wiring).

## 1. Задача

Wire `devil_advocate_pass` как **active consumer** of `hypothesis_ledger` state machine.

**Было (passive):** `devil_advocate_pass` — зарегистрированный модуль с пометкой "adversarial audit";
любые упоминания в `core_02/capability_gap_auditor.py:162-164` / `core_02/LESSONS.md` ANTI-6b
говорили только о том, что tool существует в реестре, но фактически consumer-логики не было.

**Стало (active):** каждый `devil_advocate_pass` call на OPEN гипотезе:
1. Generate 3 counter-candidates via deterministic text transforms
   (`_invert` / `_boundary_probe` / `_steel_man`).
2. Register each candidate via `hypothesis_ledger.add_hypothesis(...)` — BEFORE
   any refutation step.
3. ONLY IF ≥1 candidate registered → call `update_status(original_hid, REFUTED)`.
4. Else: fails-open — original stays OPEN, candidates may be empty.
5. ADR-016 fallback: when `hypothesis_ledger` import fails → return empty Report
   (no raise, no stderr crash).

This inverts the iteration loop: each refutation **seeds** the next round of
investigation. `weighted_scoring_engine.score_supported(...)` then prioritizes
the new OPEN candidates.

## 2. Public API

```python
from scripts_01.devil_advocate_pass import (
    DevilAdvocateReport, Strategy, devil_advocate_pass,
)

report = devil_advocate_pass(open_hypothesis, root=optional_path)
# DevilAdvocateReport(
#     original_hid="h_12345678_...",
#     refuted=True,                            # True iff original moved to REFUTED
#     new_candidates=[HypothesisSummary, ...***REMOVED***, # ≥1 registered
#     strategy="3-kill-questions",
#     iteration_count=3,                       # len(new_candidates)
#     warnings=[***REMOVED***,                             # list of stderr-able diagnostics
# )
```

## 3. 3-Kill-Questions Heuristics (deterministic, no LLM)

| # | Heuristic | Text transform |
|---|-----------|----------------|
| 1 | **INVERSION** | Replace first ` is ` → ` is NOT `; prefix `Counter: ` if absent. |
| 2 | **BOUNDARY** | Wrap in `Edge case: Under extreme boundary conditions, '<claim>' is invalid.` |
| 3 | **STEEL-MAN** | Wrap in `Evidence-gap hypothesis: Strongest counter-evidence invalidates '<claim>'.` |

**Why no LLM:** hermetic testability (string transforms are deterministic);
zero token cost; § E below documents future LLM-mode parity.

## 4. State Machine Flow

```
                ┌──────────────────────────────────────────┐
                │ guard: hypothesis.status ∈ {REFUTED,   │
                │         KILL_CRITERIA_MET***REMOVED***?             │
                └────┬─────────────────────────┬──────────┘
                     │ yes                     │ no
                     ▼                         ▼
           ┌─────────────────┐    ┌─────────────────────────┐
           │ return empty    │    │ generate 3 candidates   │
           │ Report (early)  │    │ (invert/boundary/steel) │
           └─────────────────┘    └──────────┬──────────────┘
                                             ▼
                            ┌──────────────────────────────────┐
                            │ for each candidate:              │
                            │   add_hypothesis(text, tags,     │
                            │     kill_criteria[:3***REMOVED***,           │
                            │     confidence=0.4)              │
                            └──────────┬───────────────────────┘
                                       ▼
                          ┌────────────────────────────────┐
                          │ registered_count >= 1?         │
                          └───┬────────────────────────┬───┘
                              │ yes                    │ no
                              ▼                        ▼
            ┌─────────────────────────────┐  ┌──────────────────────┐
            │ update_status(REFUTED)      │  │ fail-open: do NOT   │
            │ Report(refuted=True,        │  │ refute; return      │
            │   iteration_count=N)        │  │ refuted=False       │
            └─────────────────────────────┘  └──────────────────────┘
```

## 5. ADR-016 Fail-Safe Semantics

| Failure mode | Behavior |
|--------------|----------|
| `hypothesis_ledger` ImportError | return `Report(refuted=False, iteration_count=0)` + stderr warning |
| All 3 candidates fail add_hypothesis | return `Report(refuted=False, new_candidates=[***REMOVED***)`; **no refutation** |
| update_status raises (e.g., external concurrent refutation) | return `Report(refuted=False, new_candidates=registered)`; candidates remain OPEN |
| Empty `hypothesis.hid` | early-return empty Report (no raise) |
| Parent already terminal (REFUTED, KILL_CRITERIA_MET) | idempotent early-return empty Report |

## 6. Edge Cases Addressed

- **Empty text from `_invert`**: fallback to `Counter: (empty claim)` (never empty).
- **Parent refuted-already**: idempotent — return `refuted=False, iteration_count=0`,
  no fallback refutation attempted.
- **Confidence bias**: candidates registered with `confidence=0.4` (slight pessimism;
  encourages further investigation before confirmation via `weighted_scoring_engine`).
- **Lock-free concurrent safety**: delegated to `hypothesis_ledger.FILE_LOCK` —
  all 3 candidate writes + the refutation write are serialized via the cross-module
  lock.
- **TOCTOU:** between candidate-add and refutation, if another process refutes
  the original, `update_status` raises — caught by ADR-016 → return refuted=False
  with candidates registered (conservative semantics: candidates are NOT lost).
- **Tag inheritance:** parents.tags passed to children → downstream `weighted_scoring_engine`
  tag-match scoring works across the iteration graph.
- **Kill-criteria inheritance:** parent's `kill_criteria[:3***REMOVED***` inherited (caps
  size to avoid leakage).

## 7. Tests (Hermetic Integration via `isolated_ledger` Fixture)

File: `tests_09/test_devil_advocate_pass_integration.py`.

| # | Test name | Setup | Assert |
|---|-----------|-------|--------|
| 1 | `test_devil_advocate_pass_registers_3_new_candidates_then_refutes` | Seed OPEN HYP_A; run | query_by_status(REFUTED) contains HYP_A; query_by_status(OPEN) has ≥3 new entries inheriting parent tags |
| 2 | `test_devil_advocate_pass_lazy_import_fail_returns_empty_report` | monkeypatch sys.modules to drop hypothesis_ledger | DevilAdvocateReport(refuted=False, new_candidates=[***REMOVED***) returned; stderr warning captured |
| 3 | `test_devil_advocate_pass_idempotent_on_already_refuted` | Seed REFUTED HYP_A; run | refuted=False, iteration_count=0, candidates=[***REMOVED***; original stays REFUTED |
| 4 | `test_devil_advocate_pass_fails_open_when_candidates_lost` | monkeypatch add_hypothesis to raise | refuted=False, candidates=[***REMOVED***; original stays OPEN |

## 8. Risks (Production Considerations)

1. **TOCTOU on cross-process refutation.** Mitigated by ADR-016 catch on `update_status`;
   candidates remain OPEN rather than being lost.
2. **Naive text heuristics vs. semantic quality.** Candidates may be grammatically
   awkward (no parse-level understanding). Mitigation: downstream `weighted_scoring_engine`
   re-ranks them by factor 4 (confidence/evidence/recency/tag_match) — low-priority
   candidates naturally sink.
3. **Ledger lock contention.** 3 sequential candidate writes + 1 refutation write =
   4 FILE_LOCK acquisitions per pass. Mitigation: single-process deployment per
   AGENTS.md §11; contention irrelevant.
4. **No semantic dedup.** `_invert("X is Y")` vs `_invert("Y IS X")` produce similar
   text but different `hid`. Mitigation: downstream `query_by_status` filters by
   `confidence*tag_match*recency` — semantically equivalent candidates will surface
   near each other.

## 9. Files Created

1. `scripts_01/devil_advocate_pass.py` (~340 LOC, NEW).
2. `pompts_11/102_19_devil_advocate_pass.md` (this file).
3. `tests_09/test_devil_advocate_pass_integration.py` (~140 LOC, NEW).

## 10. Files Updated Post-implementation

1. `data_13/missing_registry.yaml` — `devil_advocate_pass` row 476 status:
   `registered` → `design_ready` → `prompt_written` (this file cycled) → `implemented`
   (via `python -m core_02.missing_registry mark-implemented ...`).
2. `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` row 37 status:
   `Thinker | 🟡 Medium — зарегистрировано` → `scripts_01 | 🟠 Medium — ✅ реализовано (v5.189.66)`.
3. `scripts_01/research_factory.py::RESEARCH_TOOLS` — append entry for
   `devil_advocate_pass` (factory slug: script-based, callable.
   `module="scripts_01.devil_advocate_pass"`, `function="devil_advocate_pass"`).
4. `CHANGELOG.md` — v5.189.66 entry prepended.
