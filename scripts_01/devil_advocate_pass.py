"""scripts_01/devil_advocate_pass.py — first ACTIVE consumer of hypothesis_ledger.

AGENTS.md §5 REGISTER-FIRST lifecycle (v5.189.66):
    registered (data_13/missing_registry.yaml: devil_advocate_pass)
        → prompt_written (pompts_11/102_19_devil_advocate_pass.md)
        → implemented (this file).

Sibling pattern: scripts_01/hypothesis_ledger.py (state-machine target),
                 scripts_01/weighted_scoring_engine.py (downstream consumer).

Pattern (inversion of passive observation):
- DEFAULTS to passive (read-only) IF hypothesis_ledger absent.
- When ledger importable: BEFORE updating original.status=REFUTED, generates 3
  counter-candidate hypotheses (inversion / boundary / steel-man) and registers
  each via hypothesis_ledger.add_hypothesis(...). Then atomically (per
  FILE_LOCK in ledger) updates original to REFUTED — IF ≥1 candidate was
  successfully registered (fail-safe: never refute without seeding).

Use cases::

    from scripts_01.devil_advocate_pass import (
        DevilAdvocateReport, devil_advocate_pass, Strategy,
    )

    # Consumer: forge_pipeline OR capability_gap_auditor feeds OPEN hypotheses.
    report = devil_advocate_pass(open_hypothesis)
    if report.refuted:
        for c in report.new_candidates:
            print(f"  new: {c.hid} → {c.text[:60]}")

CLI::

    python -m scripts_01.devil_advocate_pass --hid <sha-prefix> [--root P] [--json]

Design invariants (per thinker v5.189.66):
- **Forward-only DAG:** original moved to REFUTED (terminal) ONLY AFTER ≥1
  candidate registered. Never refutes without seeding the next iteration.
- **No regression on passive mode:** If ledger import fails, returns Report with
  refuted=False + iteration_count=0; never raises (ADR-016).
- **3-kill-questions deterministic:** text generation uses pure string
  transforms (no LLM); hermetic tests; O(1) token cost.
- **Confidence bias:** candidates created with confidence=0.4 (slight
  pessimism — adversarial exploration encouraged; weighted_scoring_engine
  downstream can reweight via tag_match).
- **Tag inheritance:** parent.tags passed to children (cross-pollination;
  preserves topical lineage).
- **Kill-criteria inheritance:** parent.kill_criteria[:3] passed to children
  (keeps the analytical frame consistent).
- **Idempotent:** if parent already REFUTED or KILL_CRITERIA_MET → return
  empty Report immediately (no-op, no second update_status attempt).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
}
from typing import Any, Dict, List, Literal, Optional

__all__ = [
    "Strategy",
    "DevilAdvocateReport",
    "devil_advocate_pass",
    "main",
]


# ─── types ──────────────────────────────────────────────────────────────


Strategy = Literal["3-kill-questions", "alternative-perspective", "evidence-gap"]


@dataclass
class DevilAdvocateReport:
    """Result of one devil's-advocate Pass — what changed in the ledger.

    Attributes (all public — used by tests + CLI):
        original_hid: hypothesis id that was examined.
        refuted: True iff original was successfully moved to REFUTED state.
        new_candidates: List of HypothesisSummary registered during this pass
            (empty when passive mode triggered or all candidates failed).
        strategy: which heuristic family produced candidates (default
            "3-kill-questions"; passive mode still advertises default for
            symmetry with non-passive callers).
        iteration_count: number of new candidates actually written to
            ledger (0 when refuted=False, even if generator produced text).
        warnings: list of stderr-able warnings (e.g., candidate registration
            failure per index; useful in tests for diagnostic).
    """

    original_hid: str
    refuted: bool
    new_candidates: List[Any]  # List[HypothesisSummary]; Any for lazy-typing
    strategy: Strategy
    iteration_count: int
    warnings: List[str] = field(default_factory=list)


# ─── helpers (deterministic, no LLM) ────────────────────────────────────


def _invert(text: str) -> str:
    """Heuristic 1 — INVERSION: derives negation hypothesis.

    Very naive string transform: split on first " is " and flip to " is NOT ".
    Falls back to "Counter: <text>" prefix when pattern absent.
    """
    clean = text.strip()
    if not clean:
        return "Counter: (empty claim)"
    if " is " in clean:
        return clean.replace(" is ", " is NOT ", 1)
    return f"Counter: {clean}"


def _boundary_probe(text: str) -> str:
    """Heuristic 2 — BOUNDARY: derives conditional hypothesis probe.

    Wraps original claim in "Under extreme boundary conditions, <claim> is
    invalid" — surfaces edge-case scenarios where the original could fail.
    """
    clean = text.strip() or "empty claim"
    return f"Edge case: Under extreme boundary conditions, '{clean}' is invalid."


def _steel_man(text: str) -> str:
    """Heuristic 3 — STEEL-MAN: derives evidence-gap counter-hypothesis.

    Frames the question: what's the strongest counter-evidence that would
    invalidate the original claim? Forces evidence_url collection downstream.
    """
    clean = text.strip() or "empty claim"
    return f"Evidence-gap hypothesis: Strongest counter-evidence invalidates '{clean}'."


def _generate_candidates(text: str) -> List[str]:
    """Deterministic 3-candidate generator. Order: invert → boundary → steel-man."""
    return [_invert(text), _boundary_probe(text), _steel_man(text)]


def _warn(message: str) -> None:
    """stderr-only warning (never pollutes stdout/JSON)."""
    sys.stderr.write(f"devil_advocate_pass: {message}\n")


def _kc_to_dicts(kc_list: Any) -> List[Dict[str, Any]]:
    """Defensively convert KillCriterion list (mixed dataclass / dict) to dict-format.

    hypothesis_ledger.add_hypothesis (per _validate_kill_criteria lines 282-298)
    accepts ONLY dicts. Engine receives parent.kill_criteria as a list of
    KillCriterion dataclasses (per HypothesisSummary schema). This helper
    normalises both — handles dataclass (uses .to_dict()), raw dict (copies),
    and arbitrary objects (extracts .__dict__).
    Returns first 3 (engine policy: cap size to prevent injection).
    """
    out: List[Dict[str, Any]] = []
    for kc in (kc_list or [])[:3]:
        if hasattr(kc, "to_dict") and callable(getattr(kc, "to_dict")):
            out.append(kc.to_dict())
        elif isinstance(kc, dict):
            out.append(dict(kc))
        else:
            d = getattr(kc, "__dict__", {}) or {}
            out.append({
                "criterion": str(d.get("criterion", "")),
                "met": bool(d.get("met", False)),
                "evidence_url": d.get("evidence_url"),
            ])
    return out


# ─── core: state machine wiring ─────────────────────────────────────────


def devil_advocate_pass(
    hypothesis: Any,
    *,
    root: Optional[Path] = None,
) -> DevilAdvocateReport:
    """Drive one adversarial-pass iteration on ``hypothesis``.

    ADR-016 fail-safe semantics:
        * hypothesis_ledger missing / ImportError → return Report(refuted=False,
          new_candidates=[], iteration_count=0) + stderr warning.
        * candidate registration failure (any of 3) → log warning, continue.
        * all 3 candidates fail → DO NOT refute original (fails-open;
          preserves state machine invariant: refutation requires seed).

    Forward-only DAG invariant:
        * If hypothesis.status already REFUTED or KILL_CRITERIA_MET → return
          empty Report immediately (idempotent; no backward transition).
        * ELSE:  register candidates FIRST, THEN update original to
          REFUTED (write order = read-after-write safe within FILE_LOCK).

    Args:
        hypothesis: HypothesisSummary-like (duck-typed: needs .hid, .text,
            .status, .tags, optional .kill_criteria).
        root: optional override for hypothesis_ledger.DEFAULT_LEDGER_DIR.

    Returns:
        DevilAdvocateReport with refuted=True iff the original was moved to
        REFUTED during this call, and new_candidates=list of registered
        HypothesisSummary.
    """
    original_hid = getattr(hypothesis, "hid", "") or ""
    if not original_hid:
        _warn("hypothesis.hid missing — returning empty report")
        return DevilAdvocateReport(
            original_hid="",
            refuted=False,
            new_candidates=[],
            strategy="3-kill-questions",
            iteration_count=0,
            warnings=["hypothesis.hid missing"],
        )

    try:
        from scripts_01.hypothesis_ledger import (  # lazy
            add_hypothesis,
            update_status,
            HypothesisStatus,
        )
    except ImportError as exc:
        _warn(f"hypothesis_ledger unavailable — passive mode: {exc}")
        return DevilAdvocateReport(
            original_hid=original_hid,
            refuted=False,
            new_candidates=[],
            strategy="3-kill-questions",
            iteration_count=0,
            warnings=[f"ImportError: {exc}"],
        )

    original_status = getattr(hypothesis, "status", None)
    # Compare via .value (string) to handle cross-enum-instance drift between
    # summary.status (from JSONL round-trip) and HypothesisStatus.REFUTED
    # (fresh import). Forward-only DAG invariant preserved.
    orig_val = getattr(original_status, "value", original_status) if original_status else None
    if orig_val in (
        HypothesisStatus.REFUTED.value,
        HypothesisStatus.KILL_CRITERIA_MET.value,
    ):
        return DevilAdvocateReport(
            original_hid=original_hid,
            refuted=False,
            new_candidates=[],
            strategy="3-kill-questions",
            iteration_count=0,
            warnings=[
                f"already terminal: {original_status.value if original_status else 'unknown'}"
            ],
        )

    # Generate 3 candidates (deterministic, no LLM).
    candidate_texts = _generate_candidates(getattr(hypothesis, "text", "") or "")
    parent_tags: List[str] = list(getattr(hypothesis, "tags", []) or [])
    parent_kc: List[Dict[str, Any]] = _kc_to_dicts(getattr(hypothesis, "kill_criteria", None))

    registered: List[Any] = []
    warnings: List[str] = []
    for idx, text in enumerate(candidate_texts):
        clean_text = (text or "").strip()
        if not clean_text:
            warnings.append(f"candidate[{idx}]: empty text — skipped")
            continue
        try:
            summary = add_hypothesis(
                clean_text,
                tags=parent_tags,
                kill_criteria=parent_kc,  # truncated to parent's first 3
                confidence=0.4,            # adversarial pessimism
                root=root,
            )
            registered.append(summary)
        except Exception as exc:  # noqa: BLE001 — ADR-016 fail-safe
            warnings.append(f"candidate[{idx}]: add_hypothesis failed — {exc!r}")

    # Fails-open invariant: at least one candidate must succeed for refutation.
    if not registered:
        _warn(f"all {len(candidate_texts)} candidates failed; NOT refuting {original_hid}")
        return DevilAdvocateReport(
            original_hid=original_hid,
            refuted=False,
            new_candidates=[],
            strategy="3-kill-questions",
            iteration_count=0,
            warnings=warnings,
        )

    # Refutation step: only AFTER ≥1 candidate registered. Cross-module FILE_LOCK
    # in hypothesis_ledger serializes writes — read-after-write of candidates
    # is guaranteed here.
    try:
        update_status(original_hid, HypothesisStatus.REFUTED, root=root)
    except Exception as exc:  # noqa: BLE001 — ADR-016 fail-safe
        warnings.append(f"update_status(REFUTED) failed: {exc!r}")
        _warn(f"candidates registered but refutation of {original_hid} failed: {exc!r}")
        # Conservative: report refuted=False since original is NOT terminal.
        # Candidates remain in OPEN — next iteration can retry refutation.
        return DevilAdvocateReport(
            original_hid=original_hid,
            refuted=False,
            new_candidates=registered,
            strategy="3-kill-questions",
            iteration_count=len(registered),
            warnings=warnings,
        )

    return DevilAdvocateReport(
        original_hid=original_hid,
        refuted=True,
        new_candidates=registered,
        strategy="3-kill-questions",
        iteration_count=len(registered),
        warnings=warnings,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────


def _format_text(report: DevilAdvocateReport) -> str:
    """Human-readable report (CLI text format)."""
    if not report.refuted and report.iteration_count == 0:
        msg = "no-op"
        if report.warnings:
            msg += "; warnings: " + "; ".join(report.warnings)
        return f"[{report.original_hid}] {msg}\n"
    lines: List[str] = []
    lines.append(
        f"[{report.original_hid}] refuted={report.refuted}; "
        f"new_candidates={report.iteration_count}; strategy={report.strategy}"
    )
    for i, c in enumerate(report.new_candidates, start=1):
        text = getattr(c, "text", "") or ""
        lines.append(f"  {i:2d}. [{getattr(c, 'hid', '?')}] {text[:72]}")
    if report.warnings:
        lines.append("  warnings:")
        for w in report.warnings:
            lines.append(f"    - {w}")
    return "\n".join(lines) + "\n"


def _print_json(report: DevilAdvocateReport) -> None:
    payload = {
        "original_hid": report.original_hid,
        "refuted": report.refuted,
        "iteration_count": report.iteration_count,
        "strategy": report.strategy,
        "new_candidates": [
            {
                "hid": getattr(c, "hid", ""),
                "text": getattr(c, "text", ""),
                "confidence": getattr(c, "confidence", None),
                "tags": list(getattr(c, "tags", []) or []),
            }
            for c in report.new_candidates
        ],
        "warnings": list(report.warnings),
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="devil_advocate_pass",
        description=(
            "Active hypothesis_ledger consumer. Generates 3 counter-candidates "
            "(inversion / boundary / steel-man) BEFORE refuting the original, "
            "so the state machine drives the iteration loop."
        ),
    )
    p.add_argument("--version", action="version", version="devil_advocate_pass 1.0.0 (v5.189.66)")
    p.add_argument(
        "--hid",
        required=True,
        help="hypothesis id (or sha-prefix ≥4 chars) to refute",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="hypothesis_ledger root override (default=data_13/hypothesis_ledger)",
    )
    p.add_argument("--json", action="store_true", help="JSON output (machine-readable)")
    return p


def _resolve_hid(prefix: str, root: Optional[Path] = None) -> Optional[Any]:
    """Resolve short hid prefix → HypothesisSummary; None on miss OR ambiguity.

    CLI guard against silent ambiguity (v5.189.66 code-review audit issue #2):
    when multiple hypotheses share the same prefix → return None (caller exits 2),
    so operator must specify longer prefix to disambiguate.
    """
    try:
        from scripts_01.hypothesis_ledger import list_all
    except ImportError:
        return None
    try:
        summaries = list_all(root=root)
    except Exception:  # noqa: BLE001
        return None
    matches = [s for s in summaries if (s.hid or "").startswith(prefix)]
    if not matches:
        return None
    if len(matches) > 1:
        _warn(f"hid-prefix '{prefix}' is ambiguous ({len(matches)} matches); specify more chars")
        return None
    return matches[0]


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary = _resolve_hid(args.hid, root=args.root)
    if summary is None:
        sys.stderr.write(f"devil_advocate_pass: no hypothesis matching hid-prefix '{args.hid}'\n")
        return 2  # Distinct from ledger-importerror (1) — caller can retry.

    report = devil_advocate_pass(summary, root=args.root)
    if args.json:
        _print_json(report)
    else:
        sys.stdout.write(_format_text(report))
    return 0 if report.refuted else 1


if __name__ == "__main__":
    sys.exit(main())
