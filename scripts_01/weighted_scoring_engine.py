"""scripts_01/weighted_scoring_engine.py — multi-criteria priority scorer.

AGENTS.md §5 REGISTER-FIRST lifecycle (v5.189.65):
    registered (data_13/missing_registry.yaml: weighted_scoring_engine)
        → prompt_written (pompts_11/101_19_weighted_scoring_engine.md)
        → implemented (this file).

Sibling pattern: scripts_01/hypothesis_ledger.py (state-machine source),
                 scripts_01/corpus_persistence.py (atomic-JSONL persistence).
Multi-criteria priority: confidence × evidence × recency × tag-match (4 axes).
Default weights sum to 1.0; tunable via ``WeightedScoringEngine(weights=...)``.

Use cases::

    from scripts_01.weighted_scoring_engine import (
        RankedCapability, WeightedScoringEngine, DEFAULT_WEIGHTS,
    )

    engine = WeightedScoringEngine()  # default weights
    ranked = engine.score_supported(focus_tags=["pricing"])
    for r in ranked:
        print(f"{r.score:.3f}  {r.hid}  ev={r.evidence_count} age={r.days_since_update:.1f}d")

CLI::

    python -m scripts_01.weighted_scoring_engine [--tag X] [--tag Y] [--json]
    python -m scripts_01.weighted_scoring_engine --help
    python -m scripts_01.weighted_scoring_engine --version

Design invariants (per thinker v5.189.65):
- **Score ∈ [0.0, 1.0]**: bounded, deterministic per (weights, summary).
- **4-factor linear combo**: confidence + evidence + recency + tag_match.
- **Default weights normalize to 1.0**: tunable, but closed-set keys (4 mandatory).
- **Lazy hypothesis_ledger import**: ADR-016 fail-safe on missing module.
- **Empty ledger = empty list**: returns [] without raising; CLI prints "no supported".
- **Tie-break by recency**: equal-score entries sorted by ascending days-since-update.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "DEFAULT_WEIGHTS",
    "DEFAULT_RECENCY_HALF_LIFE_DAYS",
    "DEFAULT_EVIDENCE_SATURATION",
    "RankedCapability",
    "WeightedScoringEngine",
    "normalize_weights",
    "main",
]


# Кaнonic weights (sum=1.0; closed set; tunable per deployment).
DEFAULT_WEIGHTS: Dict[str, float] = {
    "confidence": 0.40,   # HypothesisSummary.confidence ∈ [0.0, 1.0] — direct LLM signal.
    "evidence": 0.20,     # count(evidence_url across kill_criteria), saturated at SAT.
    "recency": 0.25,      # exp-decay by updated_at (1.0 at t=0, 0.5 at half-life).
    "tag_match": 0.15,    # Jaccard-like: |focus_tags ∩ summary.tags| / |focus_tags|.
}

# Half-life for recency exp-decay (days): t*=7d → 0.5 weight at 7-day-old summary.
DEFAULT_RECENCY_HALF_LIFE_DAYS: float = 7.0

# Evidence saturation point: 5+ evidence URLs → max signal (avoid unbounded growth).
DEFAULT_EVIDENCE_SATURATION: int = 5


# ─── dataclasses ────────────────────────────────────────────────────────


@dataclass
class RankedCapability:
    """One scored capability (hypothesis в state 'supported' after weighting).

    Attributes (all public — used by tests + CLI):
        hid: hypothesis id (h_<sha8>_<slug>).
        text: hypothesis text.
        score: combined weighted score ∈ [0.0, 1.0].
        confidence: raw confidence из summary ∈ [0.0, 1.0].
        evidence_count: number of evidence_urls across all kill_criteria.
        days_since_update: age in days (now - updated_at).
        tag_match_score: ∈ [0.0, 1.0]; 0.5 (neutral) if focus_tags absent.
        breakdown: per-factor contribution AFTER weights applied (for explainability).
    """

    hid: str
    text: str
    score: float
    confidence: float
    evidence_count: int
    days_since_update: float
    tag_match_score: float
    breakdown: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hid": self.hid,
            "text": self.text,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "evidence_count": self.evidence_count,
            "days_since_update": round(self.days_since_update, 2),
            "tag_match_score": round(self.tag_match_score, 4),
            "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()},
        }


# ─── helpers ────────────────────────────────────────────────────────────


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize numeric weights to sum=1.0.

    Strict: 4 keys required (closed set per ``DEFAULT_WEIGHTS`` shape). Reweights
    via sum-of-nonnegatives to ensure repeatability. Raises ``ValueError`` для:
    - missing keys;
    - extra/unknown keys;
    - sum AFTER cleaning is zero (degenerate weights).
    """
    required = {"confidence", "evidence", "recency", "tag_match"}
    missing = required - set(weights.keys())
    if missing:
        raise ValueError(f"weights missing keys: {sorted(missing)} (required: {sorted(required)})")
    extra = set(weights.keys()) - required
    if extra:
        raise ValueError(f"weights has unknown keys: {sorted(extra)} (closed set: {sorted(required)})")
    # Use input dict's insertion order (NOT ``required`` set) — Python set iteration
    # is hash-randomized; pairing values via ``zip(required, cleaned)`` would scramble
    # inputs and break tag_match=0.0 preservation contract (test_normalize_weights_allows_zero_tag_match).
    cleaned = {k: max(0.0, float(weights[k])) for k in weights.keys()}
    s = sum(cleaned.values())
    if s <= 0.0:
        raise ValueError("weights sum to 0 (degenerate — at least one positive weight required)")
    return {k: cleaned[k] / s for k in weights.keys()}


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _parse_iso_lenient(timestamp: str) -> _dt.datetime:
    """Lenient ISO 8601 'Z' parser — defensively return datetime.min on bad input.

    Empty / unparseable → datetime.min (ranked entries with such timestamps get
    oldest-recency tie-break; does NOT raise). Caller treats this consistently.
    """
    if not timestamp:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    s = timestamp.rstrip("Z")
    try:
        return _dt.datetime.fromisoformat(s).replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)


def _days_between(later: _dt.datetime, earlier: _dt.datetime) -> float:
    """Days elapsed (float, can be 0.0 если equal)."""
    return (later - earlier).total_seconds() / 86400.0


def _recency_factor(
    days_since: float,
    half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS,
) -> float:
    """Exp-decay: 1.0 at t=0, 0.5 at t=half_life, → 0 at t→∞.

    Future-dated timestamps (days_since < 0, e.g., clock skew) clamped to 1.0
    (we trust author timestamp authoritatively; no negativity penalty).
    """
    if days_since <= 0.0:
        return 1.0
    days_ratio = float(days_since) / float(half_life_days)  # explicit cast for mypy
    decay: float = float(0.5 ** days_ratio)  # explicit cast for mypy
    return max(0.0, decay)


def _evidence_count_normalized(
    summary: Any,
    saturation: int = DEFAULT_EVIDENCE_SATURATION,
) -> tuple:
    """Count evidence_urls across all kill_criteria + return normalized [0,1] signal.

    Returns (raw_count, normalized_score). Normalization saturates at ``saturation``
    (5+ evidences → max score 1.0) — prevents unbounded growth from distorting ranking.
    """
    raw = sum(
        1 for kc in (getattr(summary, "kill_criteria", None) or [])
        if getattr(kc, "evidence_url", None)
    )
    norm = min(raw / max(1, saturation), 1.0)
    return raw, norm


def _tag_match(hyp_tags: List[str], focus: Optional[List[str]]) -> float:
    """Jaccard-like coverage: |focus ∩ hypothesis.tags| / |focus|.

    Neutral 0.5 if focus is absent/empty (operator did not specify focus_tags →
    tag factor not penalized).
    """
    if not focus:
        return 0.5
    focus_set = {(t or "").strip().lower() for t in focus if t and t.strip()}
    if not focus_set:
        return 0.5
    hyp_set = {(t or "").strip().lower() for t in (hyp_tags or []) if t and t.strip()}
    return len(focus_set & hyp_set) / len(focus_set)


# ─── engine ──────────────────────────────────────────────────────────────


class WeightedScoringEngine:
    """Multi-criteria priority scorer for SUPPORTED hypotheses.

    Closure ports:
    - constructor validates weights (sum=1.0, closed keyset);
    - ``score_supported`` consumes ``hypothesis_ledger.query_by_status(SUPPORTED)``;
    - returns ``List[RankedCapability]`` sorted score-DESC.
    """

    def __init__(
        self,
        *,
        weights: Optional[Dict[str, float]] = None,
        half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS,
        evidence_saturation: int = DEFAULT_EVIDENCE_SATURATION,
    ) -> None:
        self.weights = normalize_weights(weights if weights is not None else dict(DEFAULT_WEIGHTS))
        if not (0.0 < float(half_life_days) <= 365.0):
            raise ValueError(
                f"half_life_days must be in (0, 365), got {half_life_days!r}"
            )
        self.half_life_days = float(half_life_days)
        if not (1 <= int(evidence_saturation) <= 100):
            raise ValueError(
                f"evidence_saturation must be in [1, 100], got {evidence_saturation!r}"
            )
        self.evidence_saturation = int(evidence_saturation)

    def score_supported(
        self,
        *,
        focus_tags: Optional[List[str]] = None,
        root: Optional[Path] = None,
    ) -> List[RankedCapability]:
        """Score all SUPPORTED hypotheses, sorted score-DESC (ties: recency).

        ADR-016 fail-safe:
        - hypothesis_ledger import failure → [] (no exception).
        - query_by_status failure → [] (no exception).
        - corrupt summary entries → silently skipped (handled внутри ledger).

        Args:
            focus_tags: optional list of tags (lowercase normalized). Boosts
                tag_match factor for hypotheses sharing any tag. None → neutral 0.5.
            root: optional override for ``hypothesis_ledger.DEFAULT_LEDGER_DIR``
                (для tests / staging vs prod).
        """
        try:
            from scripts_01.hypothesis_ledger import (  # lazy
                HypothesisStatus,
                query_by_status as _qbs,
            )
        except ImportError:
            return []  # fail-safe
        try:
            supported = _qbs(HypothesisStatus.SUPPORTED, root=root)
        except Exception:  # noqa: BLE001 — ADR-016 fail-safe
            return []

        ranked: List[RankedCapability] = []
        now = _now_utc()
        for summary in supported:
            confidence = float(getattr(summary, "confidence", 0.0) or 0.0)
            ev_raw, ev_norm = _evidence_count_normalized(
                summary, saturation=self.evidence_saturation,
            )
            updated = _parse_iso_lenient(getattr(summary, "updated_at", ""))
            days_since = _days_between(now, updated)
            recency = _recency_factor(days_since, half_life_days=self.half_life_days)
            tag_score = _tag_match(
                list(getattr(summary, "tags", []) or []),
                focus_tags,
            )

            breakdown = {
                "confidence": self.weights["confidence"] * confidence,
                "evidence": self.weights["evidence"] * ev_norm,
                "recency": self.weights["recency"] * recency,
                "tag_match": self.weights["tag_match"] * tag_score,
            }
            total_raw = sum(breakdown.values())
            clamped = max(0.0, min(1.0, total_raw))

            ranked.append(
                RankedCapability(
                    hid=summary.hid,
                    text=summary.text,
                    score=clamped,
                    confidence=confidence,
                    evidence_count=ev_raw,
                    days_since_update=days_since,
                    tag_match_score=tag_score,
                    breakdown=breakdown,
                )
            )

        # Stable sort: score DESC; ties broken by recency (smaller days_since first).
        ranked.sort(key=lambda r: (-r.score, r.days_since_update))
        return ranked


# ─── CLI ──────────────────────────────────────────────────────────────────


def _format_text(ranked: List[RankedCapability]) -> str:
    """Human-readable ranked list (CLI text format).

    Format: 5 lines per entry, indented break-down breakdown.
    """
    if not ranked:
        return "(empty: no supported hypotheses found in ledger)\n"
    lines: List[str] = []
    for i, r in enumerate(ranked, start=1):
        lines.append(
            f"{i:3d}. [score={r.score:.3f}  hid={r.hid}]  {r.text[:72]}"
        )
        lines.append(
            f"      confidence={r.confidence:.2f}  "
            f"evidence_count={r.evidence_count}  "
            f"days_since={r.days_since_update:.1f}  "
            f"tag_match={r.tag_match_score:.2f}"
        )
        for k, v in r.breakdown.items():
            lines.append(f"        {k:11s} = {v:.4f}")
    return "\n".join(lines) + "\n"


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="weighted_scoring_engine",
        description=(
            "Multi-criteria priority scorer for SUPPORTED hypotheses. "
            "Consumes hypothesis_ledger.query_by_status(\"supported\")."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version="weighted_scoring_engine 1.0.0 (v5.189.65)",
    )
    p.add_argument(
        "--tag",
        action="append",
        default=None,
        help=(
            "focus tag (повторяемый); boost score for hypothesis sharing "
            "any tag. Default: empty (= neutral 0.5 for tag factor)."
        ),
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "hypothesis_ledger root override (default=data_13/hypothesis_ledger); "
            "use для tests/staging."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="JSON output (machine-readable; default: text)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    engine = WeightedScoringEngine()
    ranked = engine.score_supported(focus_tags=args.tag, root=args.root)
    if args.json:
        _print_json([r.to_dict() for r in ranked])
    else:
        sys.stdout.write(_format_text(ranked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
