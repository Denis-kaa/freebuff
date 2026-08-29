# 101_19_weighted_scoring_engine — Capability priority scorer

> **AGENTS.md §5 REGISTER-FIRST** lifecycle. Этап 2 (`prompt_written`) → переход implementation через `pompts_11/101_19_weighted_scoring_engine.md`.

## Цель

Реализовать `scripts_01/weighted_scoring_engine.py` — multi-criteria weighted scorer для SUPPORTED гипотез из `hypothesis_ledger`.

Downstream consumer: приоритизация capability-ов в `capability_gap_auditor` first-slice + manual triage в `research_factory`.

## Контракт

- **Public API**: `WeightedScoringEngine(weights=None) -> instance`
  - `.score_supported(*, focus_tags=None, root=None) -> List[RankedCapability***REMOVED***`
  - `RankedCapability`: hid, text, score, confidence, evidence_count, days_since_update, tag_match_score, breakdown
- **CLI**: `python -m scripts_01.weighted_scoring_engine [--tag X***REMOVED*** [--json***REMOVED***`
- **Source contract**: `scripts_01/hypothesis_ledger.query_by_status(HypothesisStatus.SUPPORTED, *, root=None) -> List[HypothesisSummary***REMOVED***`
- **Wire**: `research_factory.RESEARCH_TOOLS['weighted_scoring_engine'***REMOVED***` → `module="scripts_01.weighted_scoring_engine"`, `function="WeightedScoringEngine"` (replace stub).

## Multi-criteria formula (defaults, sum=1.0)

```python
DEFAULT_WEIGHTS = {
    "confidence": 0.40,   # HypothesisSummary.confidence ∈ [0,1***REMOVED***
    "evidence": 0.20,     # count(evidence_url across kill_criteria), saturate at 5
    "recency": 0.25,      # exp-decay by updated_at (half-life 7d)
    "tag_match": 0.15,    # |focus ∩ hypothesis.tags| / |focus|; 0.5 if no focus
***REMOVED***
score = w_conf*conf + w_ev*ev_norm + w_rec*recency + w_tag*tag_score
```

Tie-break: equal scores → smaller `days_since_update` first.

## Invariants (per thinker v5.189.65)

1. **Score ∈ [0.0, 1.0***REMOVED***** — clamp safety (no overflow from saturated evidence).
2. **4-factor linear combo** — weights closed set; named keys (`confidence`, `evidence`, `recency`, `tag_match`).
3. **Defense**: `normalize_weights` rejects missing/extra keys + zero total (degenerate).
4. **ADR-016 fail-safe**: lazy import hypothesis_ledger → returns `[***REMOVED***` on ImportError.
5. **Empty ledger** → `[***REMOVED***` (CLI: "(empty: no supported hypotheses found in ledger)").
6. **Empty/corrupt summary** → silently skipped (handled внутри `hypothesis_ledger._events_to_summary`).

## Files

- **NEW**: `scripts_01/weighted_scoring_engine.py` (~280 LOC).
- **NEW**: `tests_09/test_weighted_scoring_engine.py` (~280 LOC, hermetic via `tmp_path`+monkeypatch).
- **MOD**: `scripts_01/research_factory.py` (REGISTRY entry: replace `nil` stubs).
- **MOD**: `data_13/missing_registry.yaml` (mark-implemented step via CLI).

## REGISTER-FIRST workflow

```bash
python -m core_02.missing_registry mark-prompt-written \
    weighted_scoring_engine --prompt pompts_11/101_19_weighted_scoring_engine.md

# Implement scripts_01/weighted_scoring_engine.py.

python -m core_02.missing_registry mark-implemented \
    weighted_scoring_engine \
    --implementation scripts_01/weighted_scoring_engine.py \
    --prompt pompts_11/101_19_weighted_scoring_engine.md
```

## Tests (hermetic, ~280 LOC)

- **TestWeights** (8): default sum=1, 4 keys, normalize edge cases.
- **TestScoreSupported** (10): empty/single/multi/sorting/evidence-saturation/tag-boost/clamping/custom-weights/constructor-validation.
- **TestCLI** (4): json empty dir, json with seeded hypothesis, text format markers, --version flag.

## Forward workflow (post-impl)

1. Update `docs_10/engineering-memory/FACTORY_FORGE_ARCHITECTURE_V1.md` §20 row 45→status=`implemented` (`scripts_01/weighted_scoring_engine.py`).
2. `python -m scripts_01.consistency_check` → exit 0 (counter race vs. +N tests).
3. CHANGELOG v5.189.65 entry prepended.
4. `_curated_llm_gateway.py` provenance annotation: weighted_scoring_engine remains "Inferred (Section A)" — TAXONOMY text-trigger stays "weighted ... engine"; no TAXONOMY row update needed (Section A gap is intentional — score is consumed via API, not via keyword).
