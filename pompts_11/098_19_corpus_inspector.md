---
item_id: corpus_inspector
kind: tool
factory: ''
status: prompt_written
registered_at: 2026-08-20T...
updated_at: 2026-08-20T...
backfill: false
---

# pompts_11/098_19_corpus_inspector.md

## Задача

Реализовать `scripts_01/corpus_inspector.py` — read-only + safe-cleanup tool для `corpus_persistence` (v5.189.54), CLI subcommands:

1. **`stats`** — URL count per source, age distribution (4 buckets), top domains (top-10).
2. **`dedup`** — find URL variants (same content via different params: utm_*, ref, fragment, session ids, tracked params).
3. **`evict --older-than-days N`** — TTL cleanup. **`--apply` обязателен для мутации** (default = dry-run).

INVARIANTS (AGENTS.md §5 REGISTER-FIRST lifecycle):

- (1) `register` ✅ (v5.189.58) →
- (2) `prompt_written` ✅ (this file) →
- (3) `implemented` → close after tests pass.

## Discovered during brainstorm (thinker v5.189.58)

URL-variant detection: Strategy C (hybrid canonicalization) — strip fragment, lowercase scheme/host, normalize trailing-slash path, drop known tracking params (allowlist of 16: `utm_*, fbclid, gclid, msclkid, mc_eid, mc_cid, _ga, ref, igshid, si, feature, mibextid`).

Age buckets: 4 standard correlations to retain-corpus phases (active / warming / stale / archival): `<7d`, `7-30d`, `30-90d`, `>90d` + `total` + `invalid_timestamp_count` (failed parses не валят stats).

DRY-RUN semantics: explicit `--apply` opt-in. Default = `[DRY-RUN***REMOVED*** no files removed` (operators inspect before destruction). Reject `--older-than-days < 0` via `argparse.ArgumentTypeError`.

Evict atomicity: per-URL — **whole-file unlink** if ALL entries older than TTL, else **atomic read-filter-write-rename** (mirrors `corpus_persistence.persist` pattern; no `.tmp` leftover; partial failures → leave file untouched + warn + continue).

## Interface (decided)

```python
python -m scripts_01.corpus_inspector stats [--json***REMOVED*** [--root DIR***REMOVED***
python -m scripts_01.corpus_inspector dedup [--json***REMOVED*** [--root DIR***REMOVED***
python -m scripts_01.corpus_inspector evict --older-than-days N [--apply***REMOVED*** [--json***REMOVED*** [--root DIR***REMOVED***
```

## Implementation skeleton (registered as TODO — to be done)

1. `scripts_01/corpus_inspector.py`:
   - Module-level `_TRACKING_PARAMS: frozenset` (16 entries).
   - Helper: `_canonicalize_url(url: str) -> str` (uses `urllib.parse`).
   - Helper: `_safe_parse_timestamp(ts: str) -> Optional[datetime***REMOVED***` (fail-safe: invalid → None).
   - Helper: `_age_bucket(now, ts) -> Optional[str***REMOVED***` (None if timestamp invalid).
   - Helpers: `_group_variants(entries) -> list[VariantGroup***REMOVED***`, `_group_by_domain(entries) -> list[DomainStat***REMOVED***`.
   - Public API + subcommand dispatch (mirror `corpus_persistence.main()`).
   - Evict uses `corpus_persistence.FILE_LOCK` (cross-module shared lock to prevent race с persist).
   - ADR-016 fail-safe everywhere (try/except in JSONL reads, in evict file ops, in URL canonicalization).

2. `tests_09/test_corpus_inspector.py` (8 hermetic tests, all `tmp_path`):
   - `test_stats_calculates_age_buckets_correctly`
   - `test_stats_handles_invalid_timestamps_gracefully`
   - `test_stats_top_domains_sorted_by_count`
   - `test_dedup_groups_tracking_variants` (utm_*, ref, fragment)
   - `test_dedup_preserves_semantic_query_params` (?page=1 != ?page=2)
   - `test_evict_dry_run_does_not_delete_files`
   - `test_evict_apply_unlinks_fully_stale_files` (whole-file unlink)
   - `test_evict_apply_partial_evicts_mixed_age_files_atomically` (atomic filter, no `.tmp` leftover)

## Non-goals (out of scope v1)

- Cross-corpus dedup (only within single root).
- URL canonicalization beyond strategy C (no semantic content comparison — same path+stripped-query = same content by heuristic, not actual hash check).
- CLI progress bar for large corpora.
- Backup `.bak` snapshots before evict (skipped for v1 simplicity — ADR-016 fail-safe via atomic + warn-on-error is acceptable scope).

## Risks (must be tested)

- Age bucket boundary timing — `now()` inside tests cause flake; use fixed timestamps + safe distance (T - 5d for "<7d" bucket).
- Path.glob не deterministic — always `sorted()` before assertions.
- dataclass `.to_dict()` not auto-serialized by default — explicit mapping in JSON outputs.

## Validation gates

- `pytest tests_09/test_corpus_inspector.py -v` → all 8 passed.
- `mypy scripts_01/corpus_inspector.py --ignore-missing-imports` → 0 errors.
- `python -m scripts_01.corpus_inspector --version` → exits 0 with version.
- AGENTS.md §4 (no root, all paths parametrized via `--root`).

## Lifecycle close (mark after tests):

```bash
python -m core_02.missing_registry mark-implemented corpus_inspector --implementation scripts_01/corpus_inspector.py
python -m core_02.missing_registry check   # B10-revalidates schema
```
