#!/usr/bin/env python3
"""scripts_01/whim_capture.py — Whim Capture (Phase 1.2, Missing #9).

Implementation per ``pompts_11/080_19_whim_capture_capability.md``.
ARB-REV-005 §8 + §9 Gate Permission step 3: minimal Whim intake layer for
Content Intelligence vertical slice.

Workflow:

    Whim entry (CLI / hand / project_pulse)
        ↓
    Whim (NEW — body + project context + timestamp)
        ↓
    TRIAGE (heuristic classification: KEEP | DISCARD | PROMOTE_CANDIDATE)
        ↓
    PROMOTE → Opportunity Engine (lazy hook to opportunity_engine.discover_candidates)
        ↓
    Existing execution tail (opportunity_engine.run → ForgeFacade → ...)

Lifecycle (forward-only via status_rank):

    NEW  → TRIAGED | DEFERRED | FAILED
    TRIAGED → PROMOTED_TO_OPPORTUNITY | DISCARDED | DEFERRED | FAILED
    PROMOTED_TO_OPPORTUNITY = terminal (record has related_opportunity_id as link)
    DISCARDED = terminal (record preserved — DEFERRED ≠ DELETED applies here too)
    DEFERRED → TRIAGED | DISCARDED | FAILED
    FAILED → NEW (retry path per opportunity_engine pattern)

PERSISTENCE: ``data_13/whims.yaml`` (atomic .tmp+replace per v5.39.0 Lesson).
Cross-reference to opportunity: Whim.related_opportunity_id when PROMOTED_TO_OPPORTUNITY.

ADDITIVE GUARANTEE (CAN-16): zero modifications to opportunity_engine/ForgeFacade/
ScenarioRegistry/MemoryStore/LearningLoop/MissingRegistry. Lazy hooks
for promotion step.

CLI shell (always exit-0 on degraded-safe):

    whim_capture capture <body> [--project-id X***REMOVED*** [--source X***REMOVED*** [--priority N***REMOVED*** [--json***REMOVED***
    whim_capture list [--status X***REMOVED*** [--project-id X***REMOVED*** [--json***REMOVED***
    whim_capture status <whim_id> [--json***REMOVED***
    whim_capture triage <whim_id> [--classification KEEP|DISCARD|PROMOTE_CANDIDATE***REMOVED*** [--reason X***REMOVED*** [--json***REMOVED***
    whim_capture promote <whim_id> [--json***REMOVED***
    whim_capture defer <whim_id> [--reason X***REMOVED*** [--json***REMOVED***
    whim_capture get <whim_id> [--json***REMOVED***

Exit codes: 0 success/found/degraded-safe, 1 not-found/fail, 2 invalid input.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
***REMOVED***
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports (additive)
_LAZY_IMPORT_ERRORS: List[str***REMOVED*** = [***REMOVED***

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore
    _LAZY_IMPORT_ERRORS.append("yaml")


# ─── Constants ───────────────────────────────────────────────────────────

DEFAULT_DATA_PATH = Path("data_13/whims.yaml")

STATUSES: Tuple[str, ...***REMOVED*** = (
    "NEW",
    "TRIAGED",
    "PROMOTED_TO_OPPORTUNITY",
    "DISCARDED",
    "DEFERRED",
    "FAILED",
)
TERMINAL_STATUSES: Tuple[str, ...***REMOVED*** = ("PROMOTED_TO_OPPORTUNITY", "DISCARDED")

_STATUS_RANK: Dict[str, int***REMOVED*** = {s: i for i, s in enumerate(STATUSES)***REMOVED***

# Canonical state graph (allowed transitions). FAILED is retry-allowed (mirror
# opportunity_engine pattern, per promt 080_19 §3.3).
_TRANSITIONS: Dict[str, Tuple[str, ...***REMOVED******REMOVED*** = {
    "NEW":                     ("TRIAGED", "DEFERRED", "FAILED"),
    "TRIAGED":                 ("PROMOTED_TO_OPPORTUNITY", "DISCARDED", "DEFERRED", "FAILED"),
    "PROMOTED_TO_OPPORTUNITY": (),  # terminal
    "DISCARDED":               (),  # terminal — audit trail preserved
    "DEFERRED":                ("TRIAGED", "DISCARDED", "FAILED"),
    "FAILED":                  ("NEW",),  # retry path: re-capture
***REMOVED***

CLASSIFICATIONS: Tuple[str, ...***REMOVED*** = ("KEEP", "DISCARD", "PROMOTE_CANDIDATE")

SOURCES: Tuple[str, ...***REMOVED*** = (
    "cli",
    "hand",
    "project_pulse",
    "event_bus",
    "knowledge",
    "whim",
)

# Heuristic keywords (promt 080_19 §3.1 — keep deterministic).
# Using morphological stems to match inflected Russian forms:
#   "книг" matches: книга, книгу, книги, книгой, книгами
#   "стать" matches: статья, статьи, статью
#   "тест" matches: тест, теста, тестирование (broad but safe in trash context)
#   "план" matches: план, плана, планы
# Latins work as exact substrings (no Russian inflection).
_PROMOTE_KEYWORDS = (
    "стать", "article", "guide", "гайд", "книг", "book", "план", "plan",
    "стратег", "strategy", "roadmap", "сери", "series", "tutorial",
    "обуч", "course", "lesson", "howto", "how-to",
)
_DISCARD_KEYWORDS = (
    "спам", "spam", "тест", "test", "повтор", "dup", "фигн", "ерунд",
    "junk", "throwaway",
)


# ─── Dataclass ────────────────────────────────────────────────────────────

@dataclass
class Whim:
    """Minimal Whim record (CONTRACT §17.1 + ARB-REV-005 §8 schema)."""

    id: str
    project_id: str
    body: str
    source: str
    status: str = "NEW"
    priority: int = 5
    created_at: str = ""
    updated_at: str = ""
    provenance: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    classification: Optional[str***REMOVED*** = None
    classification_reason: Optional[str***REMOVED*** = None
    triaged_at: Optional[str***REMOVED*** = None
    triaged_by: Optional[str***REMOVED*** = None
    promoted_at: Optional[str***REMOVED*** = None
    related_opportunity_id: Optional[str***REMOVED*** = None
    discarded_at: Optional[str***REMOVED*** = None
    discarded_reason: Optional[str***REMOVED*** = None
    deferred_at: Optional[str***REMOVED*** = None
    deferred_reason: Optional[str***REMOVED*** = None
    failed_at: Optional[str***REMOVED*** = None
    failure_reason: Optional[str***REMOVED*** = None

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return asdict(self)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _new_id() -> str:
    return f"whim-{uuid.uuid4().hex[:10***REMOVED******REMOVED***"


_WHIM_FIELDS = {f for f in Whim.__dataclass_fields__***REMOVED***


# ─── Persistence ──────────────────────────────────────────────────────────

class WhimStore:
    """YAML-backed lifecycle store for :class:`Whim` records.

    Atomic writes (write to ``.tmp`` then ``os.replace``) per v5.39.0 Lesson.
    Robustness: corrupt YAML degrades to empty store (no crash, fail-safe).
    """

    def __init__(self, path: Path = DEFAULT_DATA_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = self._load()

    def _load(self) -> Dict[str, Dict[str, Any***REMOVED******REMOVED***:
        if not self.path.exists():
            return {***REMOVED***
        try:
            text = self.path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) if yaml is not None else json.loads(text)
            if isinstance(data, dict):
                return {k: dict(v) for k, v in data.items() if isinstance(v, dict)***REMOVED***
            return {***REMOVED***
        except Exception:
            return {***REMOVED***

    def _save(self) -> None:
        if yaml is not None:
            body = yaml.safe_dump(self._records, allow_unicode=True, sort_keys=False)
        else:
            body = json.dumps(self._records, ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, self.path)

    def upsert(self, whim: Whim) -> None:
        whim.updated_at = _now_iso()
        if not whim.created_at:
            whim.created_at = whim.updated_at
        self._records[whim.id***REMOVED*** = whim.to_dict()
        self._save()

    def get(self, whim_id: str) -> Optional[Whim***REMOVED***:
        rec = self._records.get(whim_id)
        if rec is None:
            return None
        return Whim(**{k: v for k, v in rec.items() if k in _WHIM_FIELDS***REMOVED***)

    def all(self) -> List[Whim***REMOVED***:
        return [
            Whim(**{k: v for k, v in rec.items() if k in _WHIM_FIELDS***REMOVED***)
            for rec in self._records.values()
        ***REMOVED***

    def by_status(self, status: str) -> List[Whim***REMOVED***:
        return [w for w in self.all() if w.status == status***REMOVED***

    def by_project(self, project_id: str) -> List[Whim***REMOVED***:
        return [w for w in self.all() if w.project_id == project_id***REMOVED***

    def count(self) -> int:
        return len(self._records)


# ─── State machine ───────────────────────────────────────────────────────

class InvalidTransition(ValueError):
    """Raised when requested lifecycle transition is not in the canonical graph."""


def _check_transition(current: str, target: str) -> None:
    if current not in _STATUS_RANK:
        raise InvalidTransition(f"unknown current status {current!r***REMOVED***")
    if target not in _STATUS_RANK:
        raise InvalidTransition(f"unknown target status {target!r***REMOVED***")
    if current in TERMINAL_STATUSES:
        raise InvalidTransition(
            f"whim is in terminal state {current!r***REMOVED***; cannot transition"
        )
    allowed = _TRANSITIONS[current***REMOVED***
    if target not in allowed:
        raise InvalidTransition(
            f"transition {current!r***REMOVED*** → {target!r***REMOVED*** not allowed; "
            f"allowed from {current!r***REMOVED***: {list(allowed)***REMOVED***"
        )


# ─── Phase 7 helper: event emission (GAP B closure, CONFLICT-2) ────────────

def _emit_event(event_bus: Any, event_type: str, *, source: str, **payload: Any) -> None:
    """Best-effort EventBus.publish. Never raises (event failure must not break lifecycle).

    ``event_bus=None`` → no-op (hermetic default). Uses existing canonical EventBus
    (scripts_01/event_bus.py) — НЕ создаёт вторую event schema (§9 контракта).
    """
    if event_bus is None:
        return
    try:
        from scripts_01.event_bus import Event
        event_bus.publish(Event(type=event_type, source=source, data=dict(payload)))
    except Exception:  # noqa: BLE001 — event failure must not break lifecycle
        pass


def advance(whim: Whim, target: str, *, reason: str = "", event_bus: Any = None) -> Whim:
    """Move a whim to ``target`` state, enforcing the canonical graph.

    Updates timestamps and provenance fields. Returns the same Whim for fluent
    use; raises :class:`InvalidTransition` if the graph prohibits.

    Phase 7 (GAP B closure): при ``event_bus`` публикует ``whim.<target_lower>``
    для TRIAGED/DEFERRED/FAILED/NEW (наблюдаемость §17.1; event_bus=None → no-op).
    """
    _check_transition(whim.status, target)
    now = _now_iso()
    prev_status = whim.status  # Phase 7: для payload события (Whim не хранит previous_status)
    whim.updated_at = now

    if target == "TRIAGED":
        whim.triaged_at = now
        whim.status = target
    elif target == "PROMOTED_TO_OPPORTUNITY":
        whim.promoted_at = now
        whim.status = target
    elif target == "DISCARDED":
        whim.discarded_at = now
        whim.discarded_reason = reason or "(no reason given)"
        whim.status = target
    elif target == "DEFERRED":
        whim.deferred_at = now
        whim.deferred_reason = reason or "(no reason given)"
        whim.status = target
    elif target == "FAILED":
        whim.failed_at = now
        whim.failure_reason = reason or "(no reason given)"
        whim.status = target
    elif target == "NEW":
        # FAILED → NEW retry path. Reset triage-classification so re-evaluation is required.
        whim.classification = None
        whim.classification_reason = None
        whim.triaged_at = None
        whim.triaged_by = None
        whim.failed_at = None
        whim.failure_reason = None
        whim.status = target
    else:
        whim.status = target

    # TRIAGED НЕ эмитится здесь (triage() владеет whim.classified — нет double-emit).
    if event_bus is not None and target in ("DEFERRED", "FAILED", "NEW"):
        _emit_event(
            event_bus, f"whim.{target.lower()***REMOVED***", source="whim_capture",
            whim_id=whim.id, project_id=whim.project_id, previous_status=prev_status,
        )
    return whim


# ─── Triage heuristic ────────────────────────────────────────────────────

def classify_heuristic(body: str) -> Tuple[str, str***REMOVED***:
    """Return (classification, reason) per heuristic — deterministic.

    Per promt 080_19 §3.1 #2:
    - PROMOTE_KEYWORDS → PROMOTE_CANDIDATE
    - DISCARD_KEYWORDS → DISCARD
    - default → KEEP
    """
    text = body.lower()
    for kw in _PROMOTE_KEYWORDS:
        if kw in text:
            return "PROMOTE_CANDIDATE", f"matched-keyword:{kw***REMOVED***"
    for kw in _DISCARD_KEYWORDS:
        if kw in text:
            return "DISCARD", f"matched-keyword:{kw***REMOVED***"
    return "KEEP", "no-keyword-matched"


# ─── Capture (NEW entry) ─────────────────────────────────────────────────

def capture(
    body: str,
    *,
    project_id: str,
    source: str = "cli",
    priority: int = 5,
    store: Optional[WhimStore***REMOVED*** = None,
    event_bus: Any = None,
) -> Whim:
    """Capture a whim in NEW state.

    Phase 7 (GAP B closure): при ``event_bus`` публикует ``whim.captured``
    (event_bus=None → no-op).
    """
    if not body.strip():
        raise ValueError("body must not be empty")
    if not project_id.strip():
        raise ValueError("project_id must not be empty")
    if source not in SOURCES:
        raise ValueError(f"source {source!r***REMOVED*** not in {SOURCES***REMOVED***")
    whim = Whim(
        id=_new_id(),
        project_id=project_id,
        body=body,
        source=source,
        status="NEW",
        priority=max(0, min(10, priority)),
        provenance={"capture_mechanism": source, "runtime": "python"***REMOVED***,
    )
    if store is not None:
        store.upsert(whim)
    _emit_event(
        event_bus, "whim.captured", source="whim_capture",
        whim_id=whim.id, project_id=whim.project_id, body=whim.body, whim_source=whim.source,
    )
    return whim


# ─── Triage (NEW/DEFERRED → TRIAGED) ────────────────────────────────────

def triage(
    whim: Whim,
    *,
    classification: Optional[str***REMOVED*** = None,
    reason: str = "",
    override_heuristic: bool = True,
    event_bus: Any = None,
) -> Whim:
    """Move whim from NEW/DEFERRED to TRIAGED with classification.

    Phase 7 (GAP B closure): при ``event_bus`` публикует ``whim.classified``
    (event_bus=None → no-op).
    """
    _check_transition(whim.status, "TRIAGED")
    if classification is None or not override_heuristic:
        cls, why = classify_heuristic(whim.body)
        whim.classification = cls
        whim.classification_reason = why
        whim.triaged_by = "heuristic"
    else:
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"classification {classification!r***REMOVED*** not in {CLASSIFICATIONS***REMOVED***")
        whim.classification = classification
        whim.classification_reason = reason or "user-provided"
        whim.triaged_by = "user"
    advance(whim, "TRIAGED", event_bus=event_bus)
    _emit_event(
        event_bus, "whim.classified", source="whim_capture",
        whim_id=whim.id, project_id=whim.project_id, classification=whim.classification,
    )
    return whim


# ─── Promote (lazy hook to opportunity_engine) ───────────────────────────

def promote(whim: Whim, *, store: WhimStore, event_bus: Any = None) -> Whim:
    """Promote TRIAGED whim → Opportunity via lazy opportunity_engine.discover_candidates.

    Best-effort: if opportunity_engine unavailable, transition is recorded
    as FAILED with reason; doesn't crash.

    Phase 7 (GAP B closure): при ``event_bus`` публикует ``whim.promoted``
    (event_bus=None → no-op).
    """
    _check_transition(whim.status, "PROMOTED_TO_OPPORTUNITY")
    if whim.classification != "PROMOTE_CANDIDATE":
        raise ValueError(
            f"whim classification {whim.classification!r***REMOVED*** cannot promote; "
            f"only PROMOTE_CANDIDATE may promote"
        )

    opportunity_id: Optional[str***REMOVED*** = None
    failures: List[str***REMOVED*** = [***REMOVED***

    # Lazy import opportunity_engine + its persistence
    try:
        from scripts_01.opportunity_engine import (  # type: ignore
            Opportunity, OpportunityStore, advance as opp_advance,
            DEFAULT_DATA_PATH as OPP_DEFAULT_PATH,
        )
    except ImportError as exc:
        failures.append(f"opportunity_engine import: {exc***REMOVED***")
    else:
        try:
            opp = Opportunity(
                id=f"opp-{uuid.uuid4().hex[:10***REMOVED******REMOVED***",
                project_id=whim.project_id,
                title=f"Whim-derived: {whim.body[:60***REMOVED***.strip()***REMOVED***",
                description=(
                    f"Auto-promoted from whim {whim.id***REMOVED*** (body: {whim.body!r***REMOVED***). "
                    f"Source: {whim.source***REMOVED***, classification={whim.classification***REMOVED***."
                ),
                source=f"whim:{whim.source***REMOVED***",
                priority=whim.priority,
                provenance={
                    "origin": "whim_capture",
                    "whim_id": whim.id,
                    "classification": whim.classification,
                    "triaged_by": whim.triaged_by,
                    "promoted_at": _now_iso(),
                ***REMOVED***,
                related_whims=[whim.id***REMOVED***,
            )
            opp_advance(opp, "READY", reason="whim-promoted")
            opp_store = OpportunityStore(OPP_DEFAULT_PATH)
            opp_store.upsert(opp)
            opportunity_id = opp.id
        except Exception as exc:  # noqa: BLE001
            failures.append(f"opportunity upsert: {exc***REMOVED***")

    if not opportunity_id:
        reason_msg = "; ".join(failures) if failures else "unknown"
        return advance(whim, "FAILED", reason=f"promote failed: {reason_msg***REMOVED***", event_bus=event_bus)

    whim.related_opportunity_id = opportunity_id
    advance(whim, "PROMOTED_TO_OPPORTUNITY")
    _emit_event(
        event_bus, "whim.promoted", source="whim_capture",
        whim_id=whim.id, project_id=whim.project_id, opportunity_id=opportunity_id,
    )
    return whim


# ─── Defer (any → DEFERRED) ──────────────────────────────────────────────

def defer(whim: Whim, *, reason: str = "", event_bus: Any = None) -> Whim:
    """Move whim to DEFERRED (can resume via re-triage)."""
    return advance(whim, "DEFERRED", reason=reason, event_bus=event_bus)


# ─── Output discipline ───────────────────────────────────────────────────

def _emit_json(payload: Dict[str, Any***REMOVED***) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _emit_text(line: str, *, json_mode: bool) -> None:
    out = sys.stderr if json_mode else sys.stdout
    out.write(line + "\n")
    out.flush()


# ─── CLI ─────────────────────────────────────────────────────────────────

def _cli_capture(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    try:
        whim = capture(
            args.body,
            project_id=args.project_id,
            source=args.source,
            priority=args.priority,
            store=store,
        )
    except ValueError as exc:
        _emit_text(f"error: {exc***REMOVED***", json_mode=json_mode)
        return 2
    payload = {"whim_capture": "capture", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(
            f"captured: id={whim.id***REMOVED*** status={whim.status***REMOVED*** project_id={whim.project_id***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_list(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    items = store.all()
    if args.status:
        items = [w for w in items if w.status == args.status***REMOVED***
    if args.project_id:
        items = [w for w in items if w.project_id == args.project_id***REMOVED***
    payload = {
        "whim_capture": "list",
        "count": len(items),
        "filter_status": args.status,
        "filter_project_id": args.project_id,
        "items": [w.to_dict() for w in items***REMOVED***,
    ***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        suffix = [***REMOVED***
        if args.status:
            suffix.append(f"status={args.status***REMOVED***")
        if args.project_id:
            suffix.append(f"project_id={args.project_id***REMOVED***")
        suffix_str = (" " + " ".join(suffix)) if suffix else ""
        _emit_text(f"count={len(items)***REMOVED***{suffix_str***REMOVED***", json_mode=False)
    return 0


def _cli_status(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    whim = store.get(args.whim_id)
    if whim is None:
        _emit_text(f"error: whim_id {args.whim_id!r***REMOVED*** not found", json_mode=json_mode)
        return 1
    payload = {"whim_capture": "status", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(
            f"{whim.id***REMOVED*** status={whim.status***REMOVED*** source={whim.source***REMOVED*** "
            f"priority={whim.priority***REMOVED*** classification={whim.classification or '-'***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_triage(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    whim = store.get(args.whim_id)
    if whim is None:
        _emit_text(f"error: whim_id {args.whim_id!r***REMOVED*** not found", json_mode=json_mode)
        return 1
    try:
        triage(
            whim,
            classification=args.classification,
            reason=args.reason or "",
            override_heuristic=bool(args.classification),
        )
    except (InvalidTransition, ValueError) as exc:
        _emit_text(f"error: {exc***REMOVED***", json_mode=json_mode)
        return 2 if isinstance(exc, ValueError) else 1
    store.upsert(whim)
    payload = {"whim_capture": "triage", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(
            f"triaged: classification={whim.classification***REMOVED*** "
            f"by={whim.triaged_by***REMOVED*** reason={whim.classification_reason***REMOVED***",
            json_mode=False,
        )
    return 0


def _cli_promote(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    whim = store.get(args.whim_id)
    if whim is None:
        _emit_text(f"error: whim_id {args.whim_id!r***REMOVED*** not found", json_mode=json_mode)
        return 1
    try:
        promote(whim, store=store)
    except InvalidTransition:
        _emit_text(
            f"error: transition not allowed from status={whim.status!r***REMOVED***",
            json_mode=json_mode,
        )
        return 1
    except ValueError as exc:
        _emit_text(f"error: {exc***REMOVED***", json_mode=json_mode)
        return 2
    # promote() may have transitioned to FAILED (when opportunity_engine unavailable).
    # In that case, status is set to FAILED but we still want to exit non-zero on FAILED.
    rc = 0 if whim.status == "PROMOTED_TO_OPPORTUNITY" else 1
    store.upsert(whim)
    payload = {"whim_capture": "promote", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(
            f"promote: status={whim.status***REMOVED*** related_opportunity={whim.related_opportunity_id or '-'***REMOVED***",
            json_mode=False,
        )
    return rc


def _cli_defer(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    whim = store.get(args.whim_id)
    if whim is None:
        _emit_text(f"error: whim_id {args.whim_id!r***REMOVED*** not found", json_mode=json_mode)
        return 1
    try:
        defer(whim, reason=args.reason or "")
    except InvalidTransition:
        _emit_text(
            f"error: cannot defer from terminal state {whim.status!r***REMOVED***",
            json_mode=json_mode,
        )
        return 1
    store.upsert(whim)
    payload = {"whim_capture": "defer", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(f"deferred: at={whim.deferred_at***REMOVED*** reason={whim.deferred_reason or '-'***REMOVED***", json_mode=False)
    return 0


def _cli_get(args: argparse.Namespace) -> int:
    json_mode = bool(args.json)
    store = WhimStore(args.data_path)
    whim = store.get(args.whim_id)
    if whim is None:
        _emit_text(f"error: whim_id {args.whim_id!r***REMOVED*** not found", json_mode=json_mode)
        return 1
    payload = {"whim_capture": "get", "whim": whim.to_dict()***REMOVED***
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(f"{whim.id***REMOVED*** body={whim.body!r***REMOVED*** status={whim.status***REMOVED***", json_mode=False)
    return 0


def main(argv: Optional[List[str***REMOVED******REMOVED*** = None) -> int:
    parser = argparse.ArgumentParser(
        prog="whim_capture",
        description="Whim Capture — Phase 1.2 vertical slice (per pomt 080_19).",
    )
    parser.add_argument(
        "--data-path", default=str(DEFAULT_DATA_PATH),
        help=f"YAML persistence path (default {DEFAULT_DATA_PATH***REMOVED***)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_cap = sub.add_parser("capture", help="capture a new whim (NEW)")
    p_cap.add_argument("body")
    p_cap.add_argument("--project-id", required=True)
    p_cap.add_argument("--source", choices=SOURCES, default="cli")
    p_cap.add_argument("--priority", type=int, default=5)
    p_cap.add_argument("--json", action="store_true")
    p_cap.set_defaults(func=_cli_capture)

    p_list = sub.add_parser("list", help="list whims")
    p_list.add_argument("--status", choices=STATUSES, default=None)
    p_list.add_argument("--project-id", default=None)
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cli_list)

    p_stat = sub.add_parser("status", help="show lifecycle state")
    p_stat.add_argument("whim_id")
    p_stat.add_argument("--json", action="store_true")
    p_stat.set_defaults(func=_cli_status)

    p_trg = sub.add_parser("triage", help="classify a whim (NEW/DEFERRED → TRIAGED)")
    p_trg.add_argument("whim_id")
    p_trg.add_argument(
        "--classification", choices=CLASSIFICATIONS, default=None,
        help="explicit override; without this flag heuristic is used",
    )
    p_trg.add_argument("--reason", default="")
    p_trg.add_argument("--json", action="store_true")
    p_trg.set_defaults(func=_cli_triage)

    p_prm = sub.add_parser("promote", help="TRIAGED → PROMOTED_TO_OPPORTUNITY (lazy hook)")
    p_prm.add_argument("whim_id")
    p_prm.add_argument("--json", action="store_true")
    p_prm.set_defaults(func=_cli_promote)

    p_def = sub.add_parser("defer", help="any → DEFERRED")
    p_def.add_argument("whim_id")
    p_def.add_argument("--reason", default="")
    p_def.add_argument("--json", action="store_true")
    p_def.set_defaults(func=_cli_defer)

    p_get = sub.add_parser("get", help="fetch whim by id")
    p_get.add_argument("whim_id")
    p_get.add_argument("--json", action="store_true")
    p_get.set_defaults(func=_cli_get)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — fail-safe per spec
        _emit_text(f"error: whim_capture unexpected failure: {exc***REMOVED***", json_mode=False)
        return 2


__all__ = [
    "Whim",
    "WhimStore",
    "advance",
    "InvalidTransition",
    "capture",
    "triage",
    "promote",
    "defer",
    "classify_heuristic",
    "STATUSES",
    "TERMINAL_STATUSES",
    "CLASSIFICATIONS",
    "SOURCES",
***REMOVED***


if __name__ == "__main__":
    sys.exit(main())
