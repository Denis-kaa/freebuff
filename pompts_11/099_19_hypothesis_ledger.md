---
item_id: hypothesis_ledger
kind: module
factory: docs_10
status: prompt_written
registered_at: 2026-08-20T...
updated_at: 2026-08-20T...
backfill: false
---

# pompts_11/099_19_hypothesis_ledger.md

## Задача

Реализовать `scripts_01/hypothesis_ledger.py` — STATE-MACHINE для tracking гипотез (vocal/задача.md §10). Vocals-task + downstream consumer-ecosystem требуют:

1. **State machine lifecycle:** `open → {supported, refuted***REMOVED***` → `kill-criteria-met` terminal (forward-only DAG, NO regression).
2. **Кill-criteria aggregate:** structured `[{"criterion": "...", "met": False, "evidence_url": "..."***REMOVED******REMOVED***` list. `kill-criteria-met` is terminal only if ALL criteria `met=True`. Empty criteria → inapplicable (terminal state unreachable, stale at open/supported/refuted).
3. **Hypothesis ID:** `h_<8-hex-slug>_<sha256(text_normalized)[:8***REMOVED***>` — stable, machine-readable, human-readable prefix.
4. **Persistence pattern:** mirror `corpus_persistence.py` — `data_13/hypothesis_ledger/<sha256>.jsonl` (one file per hypothesis; one event log per ID).
5. **Cross-module FILE_LOCK:** thread-safe writes с concurrent consumers (`devil_advocate_pass`, `weighted_scoring_engine`, `capability_gap_auditor`).
6. **ADR-016 fail-safe:** corrupt JSONL lines skip-on-error, atomic write-tmp+fsync+rename, no exceptions наружу.
7. **Public API minimal:** `add_hypothesis`, `update_status`, `query_by_id`, `query_by_status`, `list_all`, `stats` — return typed dataclasses (`HypothesisSummary` + `HypothesisFull`).
8. **Confidence field:** optional float `[0.0, 1.0***REMOVED***`, default 0.5 — downstream-compatible с `weighted_scoring_engine`.
9. **Tags:** `List[str***REMOVED***`, lowercase normalization, no-schema filter friendly.

INVARIANTS (AGENTS.md §5 REGISTER-FIRST lifecycle):

- (1) `register` ✅ (vocal-task pre-batch, ~2026-08-20).
- (2) `prompt_written` ✅ (this file).
- (3) `implemented` → close after tests.

Реестр на сегодня (от 2026-08-20):
- `data_13/missing_registry.yaml` — already `kind=module, status=registered, factory=docs_10`. Lifecycle advanced to `prompt_written` после CLI `register`/`mark-prompt-written` calls in session.

## Discovered during brainstorm (thinker, validated 9 design decisions)

| # | Decision | Justification |
|---|----------|---------------|
| 1 | Forward-only DAG (`open → {supported, refuted***REMOVED*** → kill-criteria-met`) | Prevents regression; dead stays dead. |
| 2 | JSONL per-id in `data_13/hypothesis_ledger/<sha256>.jsonl` | Mirror corpus_persistence v5.189.54 pattern; per-entity atomic writes scale to hundreds of hypotheses. |
| 3 | `h_<8-hex-slug>_<sha256[***REMOVED***>[:8***REMOVED***>` | Stable + human-readable for CLI. |
| 4 | Kill-criteria: structured list of dicts (criterion + met + evidence_url) | Partial-progress tracking; aggregate status only when ALL met. |
| 5 | Confidence: optional float [0.0, 1.0***REMOVED***, default 0.5 | Loosely compatible с weighted_scoring_engine downstream. |
| 6 | Tags: List[str***REMOVED***, lowercase normalize | Zero-schema filter friendly for module consumers. |
| 7 | threading.Lock module-level | Single-process Freebuff; lock guarantees thread-safety. |
| 8 | Public API minimal: add/update/query/list/stats → typed dataclasses | Stable contract for downstream modules. |
| 9 | CLI with `--json` per-subcommand | Corresponds corpus_persistence / corpus_inspector pattern. |

## Interface (decided, mirror corpus_persistence)

```python
from scripts_01.hypothesis_ledger import (
    Hypothesis, HypothesisStatus, HypothesisSummary, HypothesisFull,
    add_hypothesis, update_status, query_by_id, query_by_status,
    list_all, stats,
)

# State machine (forward-only DAG).
# open → supported | refuted → kill-criteria-met [terminal***REMOVED***

# Public API.
result = add_hypothesis(
    "StarMaker аудитория считает вокал-обучение частью paid-tier",
    tags=["pricing", "starmaker"***REMOVED***,
    kill_criteria=[
        {"criterion": "conversion > 5%", "met": False,
         "evidence_url": "https://..."***REMOVED***,
    ***REMOVED***,
    confidence=0.5,
)
# → HypothesisSummary(hid, text, status='open', confidence=0.5, ...)

update_status(result.hid, "supported", evidence_url="https://...")
# → raises ValueError if transition invalid OR if kill_criteria unmet

# Query API.
h = query_by_id(result.hid)            # → Optional[HypothesisFull***REMOVED*** (with history log)
opened = query_by_status(HypothesisStatus.OPEN)  # → List[HypothesisSummary***REMOVED***
all_hyp = list_all()                   # → List[HypothesisSummary***REMOVED***
counts = stats()                       # → Dict[str, int***REMOVED*** (counts per status)
```

## Implementation skeleton (registered as TODO — to be done this commit)

1. `scripts_01/hypothesis_ledger.py`:
   - `HypothesisStatus` enum: `OPEN, SUPPORTED, REFUTED, KILL_CRITERIA_MET`.
   - Dataclasses: `KillCriterion`, `HypothesisSummary`, `HypothesisFull` (with status-history log).
   - Module-level `FILE_LOCK: threading.Lock`.
   - State machine transition validator `_validate_transition(current: str, new: str) -> bool`.
   - Kill-criteria aggregate check: `_is_kill_criteria_met(criteria: List[KillCriterion***REMOVED***) -> bool`.
   - Atomic JSONL writer `_atomic_write_jsonl(path, records) -> None` (mirror corpus_persistence pattern).
   - Public API: `add_hypothesis`, `update_status`, `query_by_id`, `query_by_status`, `list_all`, `stats`.
   - Fail-safe JSONL read с corrupt-line recovery (ADR-016).
   - CLI с `add`/`update`/`query`/`list`/`stats` subcommands (mirror corpus_persistence CLI shape).

2. `tests_09/test_hypothesis_ledger.py` — 8+ hermetic tests:
   - `test_add_hypothesis_new` — generates stable ID, initial state `open`, defaults.
   - `test_add_idempotency_text_normalization` — same text → same ID; second add returns `is_duplicate=True`.
   - `test_transition_dag_valid` — `open → supported → refuted → ?` per forward rules.
   - `test_transition_dag_invalid_terminal_block` — `kill-criteria-met → *` raises `ValueError`.
   - `test_kill_criteria_aggregate` — terminal only if ALL criteria `met=True`.
   - `test_query_filters_status_and_tags` — Intersection filters work.
   - `test_corrupt_jsonl_recovery` — Write garbage byte, query still returns valid entries.
   - `test_concurrent_writes_under_lock` — 10 parallel threads adding/updating same id; final state consistent.
   - `test_cli_add_update_list` — sys.executable + --root + --json flow.
   - All tests use `root=tmp_path` (autouse fixture patches `DEFAULT_LEDGER_DIR`).

## Non-goals (out of scope v1)

- Async / concurrent-process synchronization (single-process Freebuff assumption).
- Multi-user access control (Freebuff is single-owner local-first).
- Distributed replication (`data_13/` is local FS).
- Schema migrations for backward-compatibility with v0 (no v0 yet).

## Risks (must be tested)

- **State machine regression:** Future code can accidentally allow backward transitions; test `test_transition_dag_invalid_terminal_block` catches.
- **Kill-criteria race:** terminal state set after partial criteria met; test `test_kill_criteria_aggregate` covers.
- **Hash collision for similar texts:** 8-hex prefix ≈ 2^32; sha256 suffix handles real uniqueness; test `test_add_idempotency_text_normalization` catches if text normalization logic differs.
- **JSONL corruption on concurrent writes:** `FILE_LOCK` ensures writes are serialized; test `test_concurrent_writes_under_lock` covers.
- **Confidence-range edge cases:** `<0.0`, `>1.0`, `None`; test cosmetic but anchor contract.
- **Empty `kill_criteria` semantics:** terminal state unreachable; assert state cannot be `kill-criteria-met` unless all criteria met AND list is non-empty.

## Validation gates

- `pytest tests_09/test_hypothesis_ledger.py -v` → n passed.
- `mypy scripts_01/hypothesis_ledger.py --ignore-missing-imports` → 0 errors.
- `python -m scripts_01.hypothesis_ledger --version` → exit 0 with version string.
- AGENTS.md §4 (no root, all paths parametrized via `--root`).
- ADR-016 fail-safe verified: lookup never raises, corrupt recovery works end-to-end.

## Lifecycle close (mark after tests green):

```bash
python -m core_02.missing_registry mark-implemented hypothesis_ledger \
    --implementation scripts_01/hypothesis_ledger.py
python -m core_02.missing_registry check  # B10/R-127 schema re-verifies
```
