"""scripts_01/hypothesis_ledger.py — STATE-MACHINE tracking for hypothesis lifecycle.

AGENTS.md §5 REGISTER-FIRST lifecycle (v5.189.59):
    registered → prompt_written (pompts_11/099_19_hypothesis_ledger.md) → implemented (this file).

Reference: pompts_11/099_19_hypothesis_ledger.md.
Sibling: scripts_01/corpus_persistence.py (URL corpus). Pattern mirroring:
- JSONL per-id atomic write-tmp + fsync + rename.
- threading.Lock module-level.
- ADR-016 fail-safe (corrupt JSONL → warn + skip; never raises).
- Cross-module FILE_LOCK sharing (`devil_advocate_pass`, `weighted_scoring_engine`,
  `capability_gap_auditor` may all drive this state machine concurrently).

Design invariants (per thinker v5.189.59):
- **Forward-only DAG:** open → {supported, refuted} → kill-criteria-met (terminal).
  No backward transitions; once dead, stays dead.
- **State machine + terminal:** kill-criteria-met is terminal — once entered,
  NEVER any other state. Backward transitions raise ``ValueError``.
- **Kill-criteria aggregate:** kill-criteria-met is reachable ONLY IF
  ``kill_criteria`` is non-empty AND ALL criteria `met=True`.
- **Hypothesis ID:** ``h_<sha8>_<slug>`` where sha8 = sha256(text_normalized)[:8],
  slug = lowercase.no-spaces.text-prefix (max 32 chars).
- **Persistence:** one JSONL file per ID:
  ``data_13/hypothesis_ledger/<sha256(full_id)>.jsonl`` — append-only event log.
  Latest event's snapshot = current state.
- **Fail-safe:** corrupt JSONL lines skip + warn (stderr); never raises.
- **Cross-module lock:** single ``threading.Lock`` at module level (no fcntl,
  Freebuff is single-process per AGENTS.md §11).

Use cases::

    from scripts_01.hypothesis_ledger import (
        HypothesisStatus, DEFAULT_LEDGER_DIR,
        add_hypothesis, update_status, query_by_id,
        query_by_status, list_all, stats,
    )

    result = add_hypothesis(
        "StarMaker аудитория считает вокал-обучение частью paid-tier",
        tags=["pricing", "starmaker"],
        kill_criteria=[{"criterion": "conversion > 5%", "met": False}],
    )
    update_status(result.hid, HypothesisStatus.SUPPORTED)

    open_h = query_by_status(HypothesisStatus.OPEN)
    counts = stats()  # {"open": 3, "supported": 2, ...}
"""

from __future__ import annotations

import argparse
import datetime as _dt
import enum
import hashlib
import json
import os
import re
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "HypothesisStatus",
    "KillCriterion",
    "HypothesisSummary",
    "HypothesisFull",
    "DEFAULT_LEDGER_DIR",
    "LAMBDAS_VALUE_ERROR",
    "TEXT_MAX_LEN",
    "FILE_LOCK",
    "add_hypothesis",
    "update_status",
    "query_by_id",
    "query_by_status",
    "list_all",
    "stats",
    "main",
]

# ─── constants ──────────────────────────────────────────────────────────────

# Canonical storage root for hypothesis-ledger JSONL files (per-hypothesis).
# Mirrors corpus_persistence.DEFAULT_CORPUS_DIR pattern с monkeypatch-friendly Path object.
DEFAULT_LEDGER_DIR: Path = Path("data_13/hypothesis_ledger")

# ReDoS-hardcap: text length must bound (DoS protection).
TEXT_MAX_LEN: int = 4096

# Kill-criteria list size hardcap.
KILL_CRITERIA_MAX: int = 50

# Forward DAG: dict[from_status, set(to_statuses)]. Terminal status
# (``kill_criteria_met``) has no to_statuses → transitions out raise ValueError.
# ``open`` / ``supported`` / ``refuted`` may all transition INTO
# ``kill_criteria_met`` — the aggregate check (non-empty AND all
# ``met=True``) is enforced in ``update_status`` AFTER the DAG check, NOT
# in this table. This separation lets tests verify the structural DAG
# without entangling the kill-criteria invariant.
# BACKWARD TRANSITIONS to ``open`` from ``supported`` / ``refuted`` /
# ``kill_criteria_met`` are NOT in this table (semantically: re-judging a
# closed hypothesis requires registering a NEW hypothesis — the persisted
# history IS the audit trail). Only DAG-forwards listed; all omissions raise
# ``ValueError`` on attempted transition.
_TRANSITIONS: Dict[str, frozenset] = {
    "open": frozenset({"supported", "refuted", "kill_criteria_met"}),
    "supported": frozenset({"refuted", "kill_criteria_met"}),
    "refuted": frozenset({"kill_criteria_met"}),
    "kill_criteria_met": frozenset(),  # TERMINAL — no out-transitions.
}

# Module-level file lock (Freebuff is single-process; threading.Lock is sufficient).
# Same pattern as corpus_persistence.FILE_LOCK; potential cross-module future
# lock-sharing для atomic persist+ledger-write operations.
FILE_LOCK: "threading.Lock" = threading.Lock()


# ─── enum ───────────────────────────────────────────────────────────────────


class HypothesisStatus(enum.Enum):
    """4-state lifecycle per vocal/задача.md §10 + capability_gap_auditor taxonomy.

    Forward DAG (см. ``_TRANSITIONS``):
        open → {supported, refuted} → kill_criteria_met [terminal].
    """

    OPEN = "open"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    KILL_CRITERIA_MET = "kill_criteria_met"


# ─── dataclasses ────────────────────────────────────────────────────────────


@dataclass
class KillCriterion:
    """One criterion in kill-criteria aggregate. All-must-be-met для terminal state.

    Attributes:
        criterion: short description (e.g., "conversion > 5%").
        met: True ↔ criterion satisfied (external verification).
        evidence_url: optional URL supporting met/False (corpus-persistence entry).
    """

    criterion: str
    met: bool = False
    evidence_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KillCriterion":
        known = {"criterion", "met", "evidence_url"}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


@dataclass
class HypothesisSummary:
    """Current state of a hypothesis (latest snapshot, no history)."""

    hid: str
    text: str
    status: HypothesisStatus
    confidence: float
    tags: List[str]
    kill_criteria: List[KillCriterion]
    created_at: str  # ISO 8601 UTC 'Z'
    updated_at: str  # ISO 8601 UTC 'Z'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hid": self.hid,
            "text": self.text,
            "status": self.status.value,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "kill_criteria": [kc.to_dict() for kc in self.kill_criteria],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class HistoryEvent:
    """One entry in the append-only event log. Latest event = current state."""

    timestamp: str
    event_type: str  # "create" | "update_status" | "update_confidence" | "update_kill_criteria" | "add_tag" | "remove_tag"
    summary: HypothesisSummary
    from_status: Optional[HypothesisStatus] = None  # для update_status events.
    evidence_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "summary": self.summary.to_dict(),
            "from_status": self.from_status.value if self.from_status else None,
            "evidence_url": self.evidence_url,
        }


@dataclass
class HypothesisFull:
    """Hypothesis + append-only history log. Returned by query_by_id."""

    summary: HypothesisSummary
    history: List[HistoryEvent] = field(default_factory=list)


# ─── helpers ────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    """UTC ISO 8601 'Z' suffix (mirror corpus_persistence)."""
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_text(text: str) -> str:
    """Lowercase + collapse internal whitespace + strip for stable hashing.

    Идемпотентно + reversible (lower-cased → lower, original text NOT restored,
    but two equivalent texts produce same sha256 → same hypothesis id).
    """
    return re.sub(r"\s+", " ", text.strip().lower())


def _slug_from_text(text: str) -> str:
    """Human-readable prefix (max 32 chars): lowercase, ASCII alphanumeric + dashes.

    Slug is for CLI display only — NOT used for uniqueness (sha256 provides that).
    """
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9)+", "-", slug).strip("-")
    return slug[:32]


def _validate_text(text: Any) -> None:
    """Reject None, non-str, empty, overlong, non-printable edge cases."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got {type(text).__name__}")
    if not text or not text.strip():
        raise ValueError("text is empty")
    if len(text) > TEXT_MAX_LEN:
        raise ValueError(f"text len={len(text)} > TEXT_MAX_LEN={TEXT_MAX_LEN} (DoS hardcap)")


def _validate_confidence(c: Any) -> None:
    """Confidence ∈ [0.0, 1.0] inclusive."""
    if c is None:
        return  # use default downstream
    if not isinstance(c, (int, float)):
        raise TypeError(f"confidence must be numeric, got {type(c).__name__}")
    if not (0.0 <= float(c) <= 1.0):
        raise ValueError(f"confidence {c} not in [0.0, 1.0]")


def _validate_tags(tags: Optional[List[str]]) -> List[str]:
    """Normalize tags: lowercase, sorted, dedup; reject non-str."""
    if tags is None:
        return []
    out: List[str] = []
    seen: set[str] = set()
    for t in tags:
        if not isinstance(t, str):
            raise TypeError(f"tag must be str, got {type(t).__name__}")
        norm = t.strip().lower()
        if not norm:
            continue  # skip empty after strip
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return sorted(out)


def _validate_kill_criteria(
    kc: Optional[List[Dict[str, Any]]],
) -> List[KillCriterion]:
    """Validate kill-criteria list size + per-structure (ADR-016 fail-safe).

    Defensive: missing keys default sensibly (criterion="", met=False,
    evidence_url=None). Each entry parsed через ``KillCriterion.from_dict``.
    """
    if kc is None:
        return []
    if not isinstance(kc, list):
        raise TypeError(f"kill_criteria must be list of dict, got {type(kc).__name__}")
    if len(kc) > KILL_CRITERIA_MAX:
        raise ValueError(
            f"kill_criteria len={len(kc)} > KILL_CRITERIA_MAX={KILL_CRITERIA_MAX}"
        )
    return [KillCriterion.from_dict(item if isinstance(item, dict) else {})
            for item in kc]


def _is_kill_criteria_met(kc: List[KillCriterion]) -> bool:
    """True iff ``kc`` is non-empty AND every criterion `met=True`."""
    if not kc:
        return False  # empty list → terminal unreachable (testable invariant)
    return all(c.met for c in kc)


def _validate_transition(from_st: HypothesisStatus, to_st: HypothesisStatus) -> None:
    """Raise ValueError если переход invalid (forward DAG invariant).

    Caller вызывает separately kill-criteria check для terminal transition.
    """
    if from_st == to_st:
        raise ValueError(f"transition from {from_st.value} to itself is invalid")
    allowed = _TRANSITIONS.get(from_st.value, frozenset())
    if to_st.value not in allowed:
        raise ValueError(
            f"transition {from_st.value} → {to_st.value} is not in DAG "
            f"(allowed: {sorted(allowed) or ['<terminal>']})"
        )


def _entry_path(hid: str, root: Optional[Path] = None) -> Path:
    """``<root>/<sha256(hid)>.jsonl`` — sha256 hex (64 chars) ensures path-safety."""
    base = root if root is not None else DEFAULT_LEDGER_DIR
    return base / f"{hashlib.sha256(hid.encode('utf-8')).hexdigest()}.jsonl"


def _read_jsonl_safely(path: Path) -> List[Dict[str, Any]]:
    """Прочитать JSONL с corrupt-line recovery (mirror corpus_persistence)."""
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    sys.stderr.write(
                        f"hypothesis_ledger: corrupt JSONL at {path}:{line_num}: "
                        f"{exc}; line skipped\n"
                    )
    except OSError as exc:
        sys.stderr.write(f"hypothesis_ledger: read {path}: {exc}\n")
    return out


def _atomic_write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    """Atomic write-tmp + fsync + rename (mirror corpus_persistence pattern)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=False))
                f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _events_to_summary(events: List[Dict[str, Any]]) -> Optional[HypothesisSummary]:
    """Compute current state (Latest event's snapshot). Returns None if events empty/invalid."""
    if not events:
        return None
    last = events[-1]
    snap = last.get("summary", {})
    try:
        return HypothesisSummary(
            hid=snap["hid"],
            text=snap["text"],
            status=HypothesisStatus(snap["status"]),
            confidence=float(snap.get("confidence", 0.5)),
            tags=list(snap.get("tags", [])),
            kill_criteria=[
                KillCriterion.from_dict(k)
                for k in snap.get("kill_criteria", [])
            ],
            created_at=snap["created_at"],
            updated_at=snap["updated_at"],
        )
    except (KeyError, ValueError, TypeError):
        return None  # corrupt summary → ADR-016 fail-safe (return None → caller skips)


def _events_to_history(events: List[Dict[str, Any]]) -> List[HistoryEvent]:
    """Convert events TO history log (latest-event's snapshot + from_status)."""
    out: List[HistoryEvent] = []
    for e in events:
        snap_data = e.get("summary", {})
        try:
            snap = HypothesisSummary(
                hid=snap_data["hid"],
                text=snap_data["text"],
                status=HypothesisStatus(snap_data["status"]),
                confidence=float(snap_data.get("confidence", 0.5)),
                tags=list(snap_data.get("tags", [])),
                kill_criteria=[
                    KillCriterion.from_dict(k)
                    for k in snap_data.get("kill_criteria", [])
                ],
                created_at=snap_data["created_at"],
                updated_at=snap_data["updated_at"],
            )
        except (KeyError, ValueError, TypeError):
            continue  # skip corrupt event
        from_st = None
        if e.get("from_status"):
            try:
                from_st = HypothesisStatus(e["from_status"])
            except ValueError:
                pass
        out.append(HistoryEvent(
            timestamp=e["timestamp"],
            event_type=e.get("event_type", "?"),
            summary=snap,
            from_status=from_st,
            evidence_url=e.get("evidence_url"),
        ))
    return out


# ─── public API ──────────────────────────────────────────────────────────────


def _make_hid(text: str) -> str:
    """Stable, human-readable, machine-unique ID per normalized text."""
    sha8 = hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()[:8]
    slug = _slug_from_text(text)
    return f"h_{sha8}_{slug}"


def add_hypothesis(
    text: str,
    *,
    tags: Optional[List[str]] = None,
    kill_criteria: Optional[List[Dict[str, Any]]] = None,
    confidence: float = 0.5,
    root: Optional[Path] = None,
) -> HypothesisSummary:
    """Register new hypothesis в state `open` (initial state of FIG DAG).

    Returns HypothesisSummary. Subsequent updates append events to existing file.
    """
    _validate_text(text)
    _validate_confidence(confidence)
    tags_n = _validate_tags(tags)
    kc_n = _validate_kill_criteria(kill_criteria)

    hid = _make_hid(text)
    now = _now_iso()
    summary = HypothesisSummary(
        hid=hid,
        text=text,
        status=HypothesisStatus.OPEN,
        confidence=float(confidence),
        tags=tags_n,
        kill_criteria=kc_n,
        created_at=now,
        updated_at=now,
    )
    event = HistoryEvent(
        timestamp=now,
        event_type="create",
        summary=summary,
    )
    path = _entry_path(hid, root=root)
    with FILE_LOCK:
        # Read existing events (preserve history if any — idempotent by hid).
        existing = _read_jsonl_safely(path)
        # De-dupe: if create event for this hid already exists, noop (idempotent).
        if any(
            e.get("event_type") == "create" and
            e.get("summary", {}).get("hid") == hid
            for e in existing
        ):
            # Unchanged — return latest summary.
            existing_summary = _events_to_summary(existing)
            if existing_summary is not None:
                return existing_summary
        # Append create event (preserve any prior history if it existed).
        records = list(existing) + [event.to_dict()]
        _atomic_write_jsonl(path, records)
    return summary


def update_status(
    hid: str,
    new_status: HypothesisStatus,
    *,
    evidence_url: Optional[str] = None,
    confidence: Optional[float] = None,
    root: Optional[Path] = None,
) -> HypothesisSummary:
    """Transition hypothesis forward (DAG). Raises ValueError if invalid.

    Optional: support ``evidence_url`` (corpus-persistence link) + ``confidence``
    update в same call (atomic — one new event).
    """
    if not isinstance(hid, str) or not hid:
        raise ValueError("hid must be non-empty str")
    if not isinstance(new_status, HypothesisStatus):
        raise ValueError(
            f"new_status must be HypothesisStatus enum, got {type(new_status).__name__}"
        )
    if confidence is not None:
        _validate_confidence(confidence)

    path = _entry_path(hid, root=root)
    with FILE_LOCK:
        events = _read_jsonl_safely(path)
        if not events:
            raise ValueError(f"hypothesis {hid} not found (no events in log)")
        current = _events_to_summary(events)
        if current is None:
            raise ValueError(f"hypothesis {hid} has corrupt snapshot, cannot update")
        # Validate transition (forward DAG).
        _validate_transition(current.status, new_status)
        # Validate kill-criteria aggregate для terminal transition.
        if (
            new_status == HypothesisStatus.KILL_CRITERIA_MET
            and not _is_kill_criteria_met(current.kill_criteria)
        ):
            raise ValueError(
                "transition to kill_criteria_met requires non-empty list AND "
                "every criterion met=True"
            )
        # Build new snapshot = current + transition + (optional) confidence.
        now = _now_iso()
        new_snapshot = HypothesisSummary(
            hid=current.hid,
            text=current.text,
            status=new_status,
            confidence=float(confidence) if confidence is not None else current.confidence,
            tags=current.tags,
            kill_criteria=current.kill_criteria,
            created_at=current.created_at,
            updated_at=now,
        )
        event = HistoryEvent(
            timestamp=now,
            event_type="update_status",
            summary=new_snapshot,
            from_status=current.status,
            evidence_url=evidence_url,
        )
        records = list(events) + [event.to_dict()]
        _atomic_write_jsonl(path, records)
    return new_snapshot


def query_by_id(
    hid: str, *, root: Optional[Path] = None,
) -> Optional[HypothesisFull]:
    """Return HypothesisFull (summary + history) или None if hid не существует."""
    if not isinstance(hid, str) or not hid:
        return None
    path = _entry_path(hid, root=root)
    with FILE_LOCK:
        events = _read_jsonl_safely(path)
    if not events:
        return None
    summary = _events_to_summary(events)
    if summary is None:
        return None
    history = _events_to_history(events)
    return HypothesisFull(summary=summary, history=history)


def query_by_status(
    status: HypothesisStatus, *, root: Optional[Path] = None,
) -> List[HypothesisSummary]:
    """All hypotheses currently в state ``status``. Sorted by updated_at DESC."""
    out: List[HypothesisSummary] = []
    base = root if root is not None else DEFAULT_LEDGER_DIR
    if not base.is_dir():
        return []
    with FILE_LOCK:
        for jsonl in sorted(base.glob("*.jsonl")):
            events = _read_jsonl_safely(jsonl)
            summary = _events_to_summary(events)
            if summary is None:
                continue
            # Compare via .value (string) to handle cross-enum-instance drift
            # (HypothesisStatus from JSONL round-trip vs fresh import).
            if getattr(summary.status, "value", summary.status) == getattr(status, "value", status):
                out.append(summary)
    # Stable order: newest-first by updated_at (string sort OK для ISO 8601 'Z' format).
    out.sort(key=lambda s: s.updated_at, reverse=True)
    return out


def list_all(*, root: Optional[Path] = None) -> List[HypothesisSummary]:
    """All hypotheses across all statuses. Sorted by updated_at DESC."""
    out: List[HypothesisSummary] = []
    base = root if root is not None else DEFAULT_LEDGER_DIR
    if not base.is_dir():
        return []
    with FILE_LOCK:
        for jsonl in sorted(base.glob("*.jsonl")):
            events = _read_jsonl_safely(jsonl)
            summary = _events_to_summary(events)
            if summary is None:
                continue
            out.append(summary)
    out.sort(key=lambda s: s.updated_at, reverse=True)
    return out


def stats(*, root: Optional[Path] = None) -> Dict[str, int]:
    """Counts per status. Schema: {``"open": N, "supported": M, ...]``."""
    out: Dict[str, int] = {st.value: 0 for st in HypothesisStatus}
    base = root if root is not None else DEFAULT_LEDGER_DIR
    if not base.is_dir():
        return out
    with FILE_LOCK:
        for jsonl in sorted(base.glob("*.jsonl")):
            events = _read_jsonl_safely(jsonl)
            summary = _events_to_summary(events)
            if summary is None:
                continue
            out[summary.status.value] = out.get(summary.status.value, 0) + 1
    return out


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _cli_add(args: argparse.Namespace) -> int:
    try:
        # CLI's --kill-criterion accepts repeated ``key=value`` pairs (criterion|met|evidence_url).
        kc: List[Dict[str, Any]] = []
        for spec in (args.kill_criterion or []):
            parts = dict(p.split("=", 1) for p in spec.split("|") if "=" in p)
            criterion_text = parts.get("criterion", "").strip()
            if not criterion_text:
                sys.stderr.write(
                    f"error: kill-criterion requires non-empty 'criterion=...'\n"
                )
                return 2
            kc.append({
                "criterion": criterion_text,
                "met": parts.get("met", "false").lower() in ("true", "1", "yes"),
                "evidence_url": parts.get("evidence_url") or None,
            })
        result = add_hypothesis(
            args.text,
            tags=args.tag,
            kill_criteria=kc,
            confidence=args.confidence if args.confidence is not None else 0.5,
            root=args.root,
        )
    except (TypeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    if args.json:
        _print_json(result.to_dict())
        return 0
    sys.stdout.write(
        f"added hypothesis {result.hid} status={result.status.value} "
        f"confidence={result.confidence}\n"
    )
    return 0


def _cli_update(args: argparse.Namespace) -> int:
    try:
        new_st = HypothesisStatus(args.status)
        confidence: Optional[float] = None
        if args.confidence is not None:
            confidence = args.confidence
        result = update_status(
            args.id,
            new_st,
            evidence_url=args.evidence,
            confidence=confidence,
            root=args.root,
        )
    except (TypeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    if args.json:
        _print_json(result.to_dict())
        return 0
    sys.stdout.write(
        f"updated {result.hid} → status={result.status.value}\n"
    )
    return 0


def _cli_query(args: argparse.Namespace) -> int:
    full = query_by_id(args.id, root=args.root)
    if full is None:
        sys.stderr.write(f"error: hypothesis {args.id} not found\n")
        return 2
    if args.json:
        _print_json({
            "summary": full.summary.to_dict(),
            "history": [e.to_dict() for e in full.history],
        })
        return 0
    sys.stdout.write(f"hypothesis {full.summary.hid}\n")
    sys.stdout.write(f"  text: {full.summary.text}\n")
    sys.stdout.write(f"  status: {full.summary.status.value}\n")
    sys.stdout.write(f"  confidence: {full.summary.confidence}\n")
    sys.stdout.write(f"  tags: {full.summary.tags or '(none)'}\n")
    sys.stdout.write(f"  kill_criteria: "
                     f"{len(full.summary.kill_criteria)} entries\n")
    if full.history:
        sys.stdout.write(f"  history ({len(full.history)} events):\n")
        for ev in full.history:
            sys.stdout.write(
                f"    - [{ev.timestamp}] {ev.event_type} "
                f"{('from=' + ev.from_status.value) if ev.from_status else ''}\n"
            )
    return 0


def _cli_list(args: argparse.Namespace) -> int:
    if args.status:
        try:
            statuses_enum = HypothesisStatus(args.status)
        except ValueError:
            sys.stderr.write(
                f"error: status {args.status!r} not in "
                f"{[s.value for s in HypothesisStatus]}\n"
            )
            return 2
        summaries = query_by_status(statuses_enum, root=args.root)
    else:
        summaries = list_all(root=args.root)
    if args.json:
        _print_json([s.to_dict() for s in summaries])
        return 0
    if not summaries:
        sys.stdout.write("(empty ledger)\n")
        return 0
    for s in summaries:
        sys.stdout.write(
            f"- [{s.status.value}] {s.hid}: {s.text[:64]}"
            f"{'…' if len(s.text) > 64 else ''}\n"
        )
    return 0


def _cli_stats(args: argparse.Namespace) -> int:
    s = stats(root=args.root)
    if args.json:
        _print_json(s)
        return 0
    sys.stdout.write("### hypothesis ledger stats\n")
    for st in HypothesisStatus:
        sys.stdout.write(f"- {st.value}: {s.get(st.value, 0)}\n")
    total = sum(s.values())
    sys.stdout.write(f"- total: {total}\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hypothesis_ledger",
        description=(
            "State-machine ledger for hypothesis tracking. "
            "Forward-only DAG: open → {supported, refuted] → "
            "kill_criteria_met [terminal]."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="hypothesis_ledger 1.0.0 (v5.189.59)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="ledger root override (default=data_13/hypothesis_ledger); "
             "use для tests или staging vs prod deployments",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON output (machine-readable)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="register new hypothesis в state 'open'")
    p_add.add_argument("--text", required=True, help="hypothesis text (≤4096 chars)")
    p_add.add_argument(
        "--tag", action="append", default=None,
        help="tag (повторяемый; lowercase normalized)",
    )
    p_add.add_argument(
        "--kill-criterion", action="append", default=None,
        help="criterion=...|met=true|false|evidence_url=... (повторяемый)",
    )
    p_add.add_argument(
        "--confidence", type=float, default=None,
        help="initial confidence ∈ [0.0, 1.0] (default: 0.5)",
    )
    p_add.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_add.set_defaults(func=_cli_add)

    # update
    p_upd = sub.add_parser(
        "update", help="transition hypothesis forward (DAG)",
    )
    p_upd.add_argument("--id", required=True, help="hypothesis id (h_…)")
    p_upd.add_argument(
        "--status", required=True, choices=[s.value for s in HypothesisStatus],
        help="target status",
    )
    p_upd.add_argument(
        "--evidence", default=None, help="optional corpus-persistence URL reference",
    )
    p_upd.add_argument(
        "--confidence", type=float, default=None,
        help="optional confidence update ∈ [0.0, 1.0]",
    )
    p_upd.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_upd.set_defaults(func=_cli_update)

    # query
    p_q = sub.add_parser("query", help="show hypothesis + history")
    p_q.add_argument("--id", required=True)
    p_q.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_q.set_defaults(func=_cli_query)

    # list
    p_l = sub.add_parser("list", help="list hypotheses (optionally filter by status)")
    p_l.add_argument(
        "--status", default=None,
        choices=[s.value for s in HypothesisStatus],
        help="filter by current status",
    )
    p_l.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_l.set_defaults(func=_cli_list)

    # stats
    p_s = sub.add_parser("stats", help="counts per status")
    p_s.add_argument(
        "--json", action="store_true",
        help="JSON output (machine-readable)",
    )
    p_s.set_defaults(func=_cli_stats)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point::

        python -m scripts_01.hypothesis_ledger add --text "..." [--tag X] [--kill-criterion ...]
        python -m scripts_01.hypothesis_ledger update --id h_XXX --status supported
        python -m scripts_01.hypothesis_ledger query --id h_XXX
        python -m scripts_01.hypothesis_ledger list [--status open]
        python -m scripts_01.hypothesis_ledger stats
        python -m scripts_01.hypothesis_ledger --version
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)  # type: ignore[no-any-return]


if __name__ == "__main__":
    sys.exit(main())
