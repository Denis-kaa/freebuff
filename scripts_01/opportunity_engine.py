#!/usr/bin/env python3
"""scripts_01/opportunity_engine.py — Opportunity Engine (Phase 1, Missing #8).

Implementation of the first Content Intelligence vertical slice per
``pompts_11/079_19_opportunity_engine_capability.md`` (ARC-ARB-005
READY WITH ADAPTERS): minimal Intelligence head over the existing execution
tail.

Workflow:

    Whim → Opportunity (DISCOVER)
        ↓
    PROPOSE  (SELECT via ScenarioRegistry.propose_roles)
        ↓
    EXECUTE  (ForgeFacade.run_chain — EXCLUSIVE bridge per B-rule §7.3)
        ↓
    VALIDATE (RoleArtifactValidator → ACTIVE state after success, FAILED otherwise)
        ↓
    ACCUMULATE (memory_store KO kind=candidate, tag=opportunity + Learning Loop
                feedback — CAN-16: KNOWLEDGE_KINDS не содержит kind=opportunity)
        ↓
    COMPLETED

Lifecycle (forward-only via :func:`_STATUS_RANK`):

    ACTIVE  ↔  DEFERRED   (DEFERRED → ACTIVE = REACTIVATED semantic)
    ACTIVE  →  READY
    REACTIVATED → READY | DEFERRED | FAILED
    READY   →  COMPLETED  (HARD terminal)
    READY   →  DEFERRED   (backtrack before run)
    any     →  FAILED     (retry-allowed per promt §3.1 #7)

PERSISTENCE: ``data_13/opportunities.yaml`` (CONTRACT §E persistence decision:
lifecycle in YAML, content in MemoryStore KO). Schema header is in the YAML
file itself.

ADDITIVE GUARANTEE: zero modifications to ForgeFacade/ScenarioRegistry/
MemoryStore/LearningLoop/MissingRegistry. Lazy imports for forward-portability.

CLI (always exit-0 on degraded-safe per ``research_web`` precedent):

    opportunity_engine discover [--json] [--max N]
    opportunity_engine propose <opportunity_id> [--json]
    opportunity_engine run <opportunity_id> [--dry-run] [--json]
    opportunity_engine status <opportunity_id> [--json]
    opportunity_engine list [--status ACTIVE|DEFERRED|READY|COMPLETED|FAILED] [--json]

Exit codes:  0 success/found/degraded-safe, 1 not-found/fail, 2 invalid input.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports (additive, forward-portable).
#
# PHASE 14 (v5.189.35, Option B3 — ADR-015 §extension): opportunity_engine is a
# FUNCTIONAL module (no class instances), so the natural warning scope is
# per-CLI-INVOCATION. Each ``_cli_*`` helper starts with
# ``_LAZY_IMPORT_ERRORS.clear()`` (the invocation boundary) and reports
# ``import_warnings`` in its JSON payload. Library callers may still append
# (e.g. execute/propose); CLI helpers must NOT inherit warnings from a
# previous invocation or from module-import time.
_LAZY_IMPORT_ERRORS: List[str] = []

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore
    _LAZY_IMPORT_ERRORS.append("yaml")


# Constants
DEFAULT_DATA_PATH = Path("data_13/opportunities.yaml")

STATUSES: Tuple[str, ...] = (
    "ACTIVE",
    "DEFERRED",
    "READY",
    "REACTIVATED",
    "COMPLETED",
    "FAILED",
)
# Only COMPLETED is the hard terminal (promt 079_19 §3.1 #7: FAILED retry-allowed).
TERMINAL_STATUSES: Tuple[str, ...] = ("COMPLETED",)

_STATUS_RANK: Dict[str, int] = {s: i for i, s in enumerate(STATUSES)}

# Canonical state graph (allowed transitions). REACTIVATED is a transient
# audit-trail label that collapses to ACTIVE in :func:`advance`.
_TRANSITIONS: Dict[str, Tuple[str, ...]] = {
    "ACTIVE":      ("DEFERRED", "READY", "FAILED"),
    "DEFERRED":    ("REACTIVATED", "FAILED"),
    "REACTIVATED": ("READY", "DEFERRED", "FAILED"),
    "READY":       ("COMPLETED", "DEFERRED", "FAILED"),
    "COMPLETED":   (),  # strict terminal
    "FAILED":      ("ACTIVE", "READY"),  # retry path (promt §3.1 #7)
}

SOURCES: Tuple[str, ...] = (
    "whim",
    "project_pulse",
    "event_bus",
    "knowledge",
    "hand",
)

# GAP-1 (promt 085 §7): дефолтные пути РЕАЛЬНЫХ источников DISCOVER.
# Перекрываются через ``source_paths`` в discover_candidates / CLI-флаги.
WHIM_DATA_PATH = Path("data_13/whims.yaml")
PULSE_DB_PATH = Path("data_13/project_pulse.db")
EVENT_DB_PATH = Path("context_12/events.db")
MEMORY_DB_PATH = Path("data_13/context.db")


# RANKING (Advanced Opportunity Ranking — promt 086): композитный score поверх
# provenance confidence. Аддитивно; веса документированы, сумма = 1.0.
RANK_WEIGHTS: Dict[str, float] = {
    "confidence": 0.5,  # provenance confidence — первичный сигнал
    "source": 0.2,      # надёжность источника
    "recency": 0.2,     # свежесть (30-дневный линейный decay)
    "priority": 0.1,    # явный приоритет (1-10 → 0..1)
}
SOURCE_WEIGHTS: Dict[str, float] = {
    "whim": 1.0,        # курируемый интент (человек/агент)
    "hand": 1.0,        # ручной
    "knowledge": 0.8,   # накопленный candidate KO (предыдущий цикл)
    "project_pulse": 0.6,
    "event_bus": 0.5,
}
_RECENCY_DAYS = 30.0


# Dataclass: minimal Opportunity (CONTRACT §E 16 fields)
@dataclass
class Opportunity:
    id: str
    project_id: str
    title: str
    description: str
    source: str
    status: str = "ACTIVE"
    priority: int = 5
    created_at: str = ""
    updated_at: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    scenario: Optional[Dict[str, Any]] = None
    roles: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    source_path: str = ""
    evidence_path: str = ""
    deferred_at: Optional[str] = None
    deferred_reason: Optional[str] = None
    previous_status: Optional[str] = None
    reactivated_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    related_decisions: List[str] = field(default_factory=list)
    related_whims: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _new_id() -> str:
    return f"opp-{uuid.uuid4().hex[:10]}"


_OPP_FIELDS = {f for f in Opportunity.__dataclass_fields__}


# Persistence (YAML, atomic .tmp+replace per v5.39.0 Lesson)
class OpportunityStore:
    """YAML-backed lifecycle store for Opportunity records (CONTRACT §E)."""

    def __init__(self, path: Path = DEFAULT_DATA_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            text = self.path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) if yaml is not None else json.loads(text)
            if isinstance(data, dict):
                return {k: dict(v) for k, v in data.items() if isinstance(v, dict)}
            return {}
        except Exception:
            # Robust against yaml.parser.ParserError, BOM, scanner errors,
            # OSError on partially-written files, etc.: degrade to empty.
            return {}

    def _save(self) -> None:
        if yaml is not None:
            body = yaml.safe_dump(self._records, allow_unicode=True, sort_keys=False)
        else:
            body = json.dumps(self._records, ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, self.path)

    # CRUD
    def upsert(self, opp: Opportunity) -> None:
        opp.updated_at = _now_iso()
        if not opp.created_at:
            opp.created_at = opp.updated_at
        self._records[opp.id] = opp.to_dict()
        self._save()

    def get(self, opp_id: str) -> Optional[Opportunity]:
        rec = self._records.get(opp_id)
        if rec is None:
            return None
        return Opportunity(**{k: v for k, v in rec.items() if k in _OPP_FIELDS})

    def all(self) -> List[Opportunity]:
        return [
            Opportunity(**{k: v for k, v in rec.items() if k in _OPP_FIELDS})
            for rec in self._records.values()
        ]

    def by_status(self, status: str) -> List[Opportunity]:
        return [o for o in self.all() if o.status == status]

    def count(self) -> int:
        return len(self._records)

    def find_by_provenance(self, source: str, source_id: str) -> Optional[Opportunity]:
        """Найти opportunity по (source, source_id) — детерминированный identity (§18).

        Идемпотентность DISCOVER (promt 085 §18): один и тот же сигнал не должен
        бесконечно создавать одинаковые Opportunity. Возвращает первую запись
        с совпадающей парой provenance.source / provenance.source_id, либо None.
        """
        for rec in self._records.values():
            prov = rec.get("provenance") or {}
            if prov.get("source") == source and prov.get("source_id") == source_id:
                return Opportunity(**{k: v for k, v in rec.items() if k in _OPP_FIELDS})
        return None


# State machine
class InvalidTransition(ValueError):
    """Raised when requested lifecycle transition is not in the canonical graph."""


def _check_transition(current: str, target: str) -> None:
    if current not in _STATUS_RANK:
        raise InvalidTransition(f"unknown current status {current!r}")
    if target not in _STATUS_RANK:
        raise InvalidTransition(f"unknown target status {target!r}")
    if current in TERMINAL_STATUSES:
        raise InvalidTransition(
            f"opportunity is in terminal state {current!r}; cannot transition"
        )
    allowed = _TRANSITIONS[current]
    if target not in allowed:
        raise InvalidTransition(
            f"transition {current!r} → {target!r} not allowed; "
            f"allowed from {current!r}: {list(allowed)}"
        )


def advance(opp: Opportunity, target: str, *, reason: str = "", event_bus: Any = None) -> Opportunity:
    """Move an opportunity to ``target`` state, enforcing the canonical graph.

    Updates timestamps and provenance fields. Returns the same Opportunity
    for fluent use; raises :class:`InvalidTransition` if the graph prohibits.

    Phase 7 (GAP B closure): при ``event_bus`` публикует ``opportunity.<target_lower>``
    для DEFERRED/REACTIVATED/COMPLETED/FAILED (наблюдаемость §J; event_bus=None → no-op).
    """
    _check_transition(opp.status, target)
    now = _now_iso()
    opp.previous_status = opp.status
    opp.updated_at = now

    if target == "DEFERRED":
        opp.deferred_at = now
        opp.deferred_reason = reason or "(no reason given)"
        opp.status = "DEFERRED"
    elif target == "REACTIVATED":
        # REACTIVATED is the audit-trail label for DEFERRED → ACTIVE; we
        # persist reactivated_at, and collapse to ACTIVE per promt §10.
        opp.reactivated_at = now
        opp.status = "ACTIVE"
    elif target == "COMPLETED":
        opp.completed_at = now
        opp.status = target
    elif target == "FAILED":
        opp.failed_at = now
        opp.failure_reason = reason or "(no reason given)"
        opp.status = target
    else:
        # ACTIVE, READY
        opp.status = target

    if event_bus is not None and target in ("DEFERRED", "REACTIVATED", "COMPLETED", "FAILED"):
        _emit_event(
            event_bus, f"opportunity.{target.lower()}", source="opportunity_engine",
            opportunity_id=opp.id, project_id=opp.project_id,
            previous_status=opp.previous_status, reason=reason,
        )
    return opp


# Discover (sources → candidates)
# GAP-1 (promt 085 §7-§8): REAL DISCOVER — реальные пулы из существующих источников
# (whim_capture, project_pulse, event_bus, memory_store) с provenance. Никаких стубов.
# Каждый источник fail-safe: отсутствующий/нечитаемый файл → пустой список (не мусор).


def _lazy_import(module_name: str, attr: str) -> Any:
    """Ленивый импорт с fallback на top-level имя (CLI-контекст scripts_01)."""
    try:
        return getattr(__import__(module_name, fromlist=[attr]), attr)
    except ImportError:
        bare = module_name.rsplit(".", 1)[-1]
        try:
            return getattr(__import__(bare, fromlist=[attr]), attr)
        except ImportError:
            return None


def _discover_from_whims(
    project_id: str, *, path: Path, max_results: int, now: str,
) -> List[Opportunity]:
    """Реальный источник #1: WhimStore (whims.yaml) — whim'ы проекта."""
    WhimStore = _lazy_import("scripts_01.whim_capture", "WhimStore")
    if WhimStore is None or not path.exists():
        return []
    try:
        store = WhimStore(path)
        whims = store.all()
    except Exception:  # noqa: BLE001 — fail-safe per spec
        return []
    out: List[Opportunity] = []
    for w in whims:
        if len(out) >= max_results:
            break
        if w.project_id != project_id:
            continue
        if w.status not in ("NEW", "TRIAGED", "DEFERRED"):
            continue  # PROMOTED/DISCARDED/FAILED — не сигналы
        # DEFERRED-whim включается сознательно (promt 085 §13: DEFERRED ≠ DELETED —
        # при новом контексте сигнал должен снова обнаруживаться; confidence 0.6).
        if w.related_opportunity_id:
            continue  # уже связан с opportunity (dedup по whim)
        confidence = 0.6
        if w.classification == "PROMOTE_CANDIDATE":
            confidence = 0.8
        out.append(Opportunity(
            id=_new_id(),
            project_id=project_id,
            title=f"Whim: {w.body[:60]}",
            description=(
                f"Whim {w.id}: {w.body!r} (source={w.source}, "
                f"classification={w.classification or '-'})"
            ),
            source="whim",
            status="ACTIVE",
            priority=w.priority,
            created_at=now,
            updated_at=now,
            provenance={
                "source": "whim",
                "source_id": w.id,
                "reason": w.classification_reason or f"whim:{w.status}",
                "evidence": w.body,
                "confidence": confidence,
                "stub": False,
            },
            evidence_path=str(path),
            related_whims=[w.id],
        ))
    return out


def _discover_from_pulse(
    project_id: str, *, path: Path, max_results: int, now: str,
) -> List[Opportunity]:
    """Реальный источник #2: ProjectPulse (project_pulse.db) — свежие события пульса."""
    ProjectPulse = _lazy_import("scripts_01.project_pulse", "ProjectPulse")
    if ProjectPulse is None or not path.exists():
        return []
    try:
        pulse = ProjectPulse(db_path=path)
        entries = pulse.list(limit=max_results * 3)
    except Exception:  # noqa: BLE001
        return []
    out: List[Opportunity] = []
    for e in entries:
        if len(out) >= max_results:
            break
        out.append(Opportunity(
            id=_new_id(),
            project_id=project_id,
            title=f"Pulse: {e.title[:60]}",
            description=f"{e.event_type}: {e.description[:200]}",
            source="project_pulse",
            status="ACTIVE",
            priority=5,
            created_at=now,
            updated_at=now,
            provenance={
                "source": "project_pulse",
                "source_id": e.id,
                "reason": e.event_type,
                "evidence": e.description or e.title,
                "confidence": 0.5,
                "stub": False,
                "pulse_ref": e.ref,
            },
            evidence_path=str(path),
        ))
    return out


def _discover_from_events(
    project_id: str, *, path: Path, max_results: int, now: str,
) -> List[Opportunity]:
    """Реальный источник #3: EventBus (events.db) — последние события шины."""
    EventBus = _lazy_import("scripts_01.event_bus", "EventBus")
    if EventBus is None or not path.exists():
        return []
    try:
        bus = EventBus(db_path=path)
        entries = bus.get_events(limit=max_results * 3)
    except Exception:  # noqa: BLE001
        return []
    out: List[Opportunity] = []
    for e in entries:
        if len(out) >= max_results:
            break
        out.append(Opportunity(
            id=_new_id(),
            project_id=project_id,
            title=f"Event: {e.event_type}",
            description=f"{e.event_type} from {e.source}: {e.data_json[:200]}",
            source="event_bus",
            status="ACTIVE",
            priority=5,
            created_at=now,
            updated_at=now,
            provenance={
                "source": "event_bus",
                "source_id": e.event_id,
                "reason": e.event_type,
                "evidence": e.data_json,
                "confidence": 0.5,
                "stub": False,
            },
            evidence_path=str(path),
        ))
    return out


def _discover_from_knowledge(
    project_id: str, *, path: Path, max_results: int, now: str,
) -> List[Opportunity]:
    """Реальный источник #4: MemoryStore (context.db) — Knowledge Objects kind=candidate."""
    MemoryStore = _lazy_import("core_02.memory_store", "MemoryStore")
    if MemoryStore is None or not path.exists():
        return []
    try:
        store = MemoryStore(path)
        kos = store.query_by_type("candidate", limit=max_results * 3)
    except Exception:  # noqa: BLE001
        return []
    out: List[Opportunity] = []
    for ko in kos:
        if len(out) >= max_results:
            break
        # v5.189.20: убрать `or 0.5` falsy-0.0 баг — confidence_score=0.0 больше
        # не промоутится в 0.5 (зеркалит паттерн rank_score/rank_candidates).
        _conf = ko.get("confidence_score")
        out.append(Opportunity(
            id=_new_id(),
            project_id=project_id,
            title=f"KO: {(ko.get('title') or 'candidate')[:60]}",
            description=(ko.get("summary") or ko.get("content") or "")[:200],
            source="knowledge",
            status="ACTIVE",
            priority=5,
            created_at=now,
            updated_at=now,
            provenance={
                "source": "knowledge",
                "source_id": ko.get("id", ""),
                "reason": f"kind:{ko.get('kind')}",
                "evidence": (ko.get("summary") or ko.get("content") or ""),
                "confidence": float(_conf if _conf is not None else 0.5),
                "stub": False,
            },
            evidence_path=str(path),
        ))
    return out


def discover_candidates(
    project_id: str,
    *,
    max_results: int = 10,
    store: Optional[OpportunityStore] = None,
    source_paths: Optional[Dict[str, Path]] = None,
    rank: bool = False,
) -> List[Opportunity]:
    """GAP-1: REAL DISCOVER — реальные источники вместо stub-кандидатов (promt 085 §7).

    Пулит из 4 существующих источников (whim_capture / project_pulse / event_bus /
    memory_store), каждый кандидат несёт provenance (source, source_id, reason,
    evidence, confidence — §8). Отсутствующий/пустой источник даёт 0 кандидатов
    (никаких «Stub signal» — §8 DISCOVER НЕ ДОЛЖЕН ГЕНЕРИРОВАТЬ МУСОР).

    Idempotency (§18): детерминированный identity (source, source_id) — при
    переданном ``store`` кандидаты, уже существующие в нём, пропускаются.

    ``rank=True`` (promt 086): собрать пул со всех источников БЕЗ раннего обрыва,
    дедуп, затем ``rank_candidates()`` (композитный score поверх confidence) и
    срез top-N. ``rank=False`` — прежнее поведение (порядок источников + ранний обрыв).
    """
    paths = dict(source_paths or {})
    now = _now_iso()
    # (ключ source_paths, источник, дефолтный путь) — явный список, ключи
    # консистентны с CLI-флагами (--whim-path/--pulse-db/--event-db/--memory-db).
    _SOURCE_DEFAULTS = (
        ("whims", _discover_from_whims, WHIM_DATA_PATH),
        ("pulse", _discover_from_pulse, PULSE_DB_PATH),
        ("events", _discover_from_events, EVENT_DB_PATH),
        ("memory", _discover_from_knowledge, MEMORY_DB_PATH),
    )
    candidates: List[Opportunity] = []
    for key, src_fn, default_path in _SOURCE_DEFAULTS:
        src_path = paths.get(key, default_path)
        try:
            batch = src_fn(project_id, path=Path(src_path), max_results=max_results, now=now)
        except Exception:  # noqa: BLE001
            continue
        candidates.extend(batch)
        if not rank and len(candidates) >= max_results:
            break

    # Idempotency (§18): дедупликация против уже существующих записей ДО среза,
    # чтобы свежие кандидаты за дубликатами не терялись (reviewer nit).
    if store is not None:
        deduped: List[Opportunity] = []
        for c in candidates:
            src = c.provenance.get("source", c.source)
            src_id = c.provenance.get("source_id", "")
            if store.find_by_provenance(src, src_id) is not None:
                continue
            deduped.append(c)
        candidates = deduped
    if rank:
        candidates = rank_candidates(candidates)
    return candidates[:max_results]


# RANKING (Advanced Opportunity Ranking — promt 086 §SPEC)
def _parse_dt(value: str) -> Optional[_dt.datetime]:
    """ISO-8601 → naive UTC datetime (с/без tz); не парсится → None."""
    if not value:
        return None
    try:
        dt = _dt.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return dt


def _recency_score(created_at: str, now: _dt.datetime) -> float:
    """Линейный decay: свежий (0 дней) = 1.0 → 30+ дней = 0.0; нет даты = 0.5."""
    dt = _parse_dt(created_at)
    if dt is None:
        return 0.5
    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
    return max(0.0, min(1.0, 1.0 - age_days / _RECENCY_DAYS))


def _priority_norm(priority: int) -> float:
    """priority (1-10, default 5) → [0, 1]; вне диапазона clamp."""
    try:
        p = float(priority)
    except (TypeError, ValueError):
        return 0.5
    if p < 1:
        return 0.0
    if p > 10:
        return 1.0
    return (p - 1.0) / 9.0


def rank_score(
    opp: Opportunity,
    *,
    now: Optional[_dt.datetime] = None,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Композитный ranking score для одного opportunity (promt 086 §SPEC).

    score = confidence·w_conf + source·w_src + recency·w_rec + priority·w_pri
    Каждая компонента в [0,1]; дефолтные веса суммируются в 1.0 → score ∈ [0,1].
    """
    w = dict(RANK_WEIGHTS)
    if weights:
        w.update(weights)
    if now is None:
        now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)

    _conf = opp.provenance.get("confidence")
    confidence = max(0.0, min(1.0, float(_conf if _conf is not None else 0.5)))
    source = opp.provenance.get("source") or opp.source or ""
    source_w = SOURCE_WEIGHTS.get(source, 0.5)
    recency = _recency_score(opp.created_at, now)
    prio = _priority_norm(opp.priority)

    return round(
        confidence * w.get("confidence", 0.5)
        + source_w * w.get("source", 0.2)
        + recency * w.get("recency", 0.2)
        + prio * w.get("priority", 0.1),
        4,
    )


def rank_candidates(
    candidates: List[Opportunity],
    *,
    now: Optional[_dt.datetime] = None,
    weights: Optional[Dict[str, float]] = None,
    persist_score: bool = True,
) -> List[Opportunity]:
    """Advanced Opportunity Ranking — сортировка кандидатов по score (убывание).

    Tie-break: выше score → новее ``created_at`` → стабильность исходного порядка.
    При ``persist_score=True`` пишет ``provenance['rank_score']`` и
    ``provenance['rank_factors']`` (breakdown) — traceability ранга.
    """
    if now is None:
        now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    scored: List[Tuple[float, str, int, Opportunity]] = []
    for i, c in enumerate(candidates):
        s = rank_score(c, now=now, weights=weights)
        if persist_score:
            src = c.provenance.get("source") or c.source or ""
            _conf = c.provenance.get("confidence")
            c.provenance["rank_score"] = s
            c.provenance["rank_factors"] = {
                "confidence": round(float(_conf if _conf is not None else 0.5), 4),
                "source": src,
                "source_weight": SOURCE_WEIGHTS.get(src, 0.5),
                "recency": round(_recency_score(c.created_at, now), 4),
                "priority_norm": round(_priority_norm(c.priority), 4),
            }
        scored.append((s, c.created_at, -i, c))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [t[3] for t in scored]


# ─── Phase 7 helpers: events + factory selection + project resolution ──────
# GAP B closure (CONFLICT-2): EventBus emission — best-effort, никогда не ломает
# lifecycle. GAP A closure (CONFLICT-3): Factory selection + Project resolution.


def _emit_event(event_bus: Any, event_type: str, *, source: str, **payload: Any) -> None:
    """Best-effort EventBus.publish. Never raises (event failure must not break lifecycle).

    ``event_bus=None`` → no-op (hermetic default для библиотечных вызовов/тестов).
    Публикует ``Event(type, source, data)`` в существующий canonical EventBus
    (scripts_01/event_bus.py) — НЕ создаёт вторую event schema (§9 контракта).
    """
    if event_bus is None:
        return
    try:
        from scripts_01.event_bus import Event
        event_bus.publish(Event(type=event_type, source=source, data=dict(payload)))
    except Exception:  # noqa: BLE001 — event failure must not break lifecycle
        pass


def _derive_capability(opp: Opportunity) -> Optional[str]:
    """Capability token для Factory selection: provenance.capability → scenario.capability → None.

    Закрытый словарь (ANTI-6b): токен ДОЛЖЕН быть в KNOWN_CAPABILITIES, иначе
    ``select_forge`` не найдёт пару (FactoryRegistry.find_by_capability фильтрует
    по capabilities паспортов). None → caller использует pipeline fallback.
    """
    prov = opp.provenance or {}
    cap = prov.get("capability")
    if isinstance(cap, str) and cap:
        return cap
    if opp.scenario:
        cap = opp.scenario.get("capability")
        if isinstance(cap, str) and cap:
            return cap
    return None


def _select_factory_forge(
    opp: Opportunity,
    *,
    factory_registry: Any = None,
) -> Optional[Tuple[Any, Any]]:
    """Factory selection (GAP A closure): Opportunity → FactoryRegistry.select_forge(capability).

    Возвращает ``(FactoryPassport, ForgePassport)`` или None (fallback на pipeline).
    Fail-safe: отсутствие capability / FactoryRegistry / совпадения → None (НЕ краш).
    """
    capability = _derive_capability(opp)
    if not capability:
        return None
    try:
        if factory_registry is None:
            FactoryRegistry = _lazy_import("core_02.factory_registry", "FactoryRegistry")
            if FactoryRegistry is None:
                _LAZY_IMPORT_ERRORS.append("factory_registry: unavailable")
                return None
            factory_registry = FactoryRegistry()
        pair = factory_registry.select_forge(capability)
        if pair is None:
            return None
        # Явный кортеж (не Any) — mypy no-any-return fix.
        return (pair[0], pair[1])
    except Exception:  # noqa: BLE001 — fail-safe per spec
        return None


def _resolve_project(opp: Opportunity, *, project_root: Optional[Path] = None) -> Any:
    """Resolve a Project object for ForgeFacade.run_chain (GAP A fix).

    Best-effort: explicit ``project_root`` → ``projects_17/<project_id>`` → None.
    Возвращает None если проект неразрешим (caller передаёт None в run_chain,
    реальный ForgeFacade упадёт с понятной причиной → FAILED).
    """
    try:
        from core_02.workspace import Project
    except ImportError as exc:
        _LAZY_IMPORT_ERRORS.append(f"workspace.Project: {exc}")
        return None
    candidates: List[Path] = []
    if project_root is not None:
        candidates.append(Path(project_root))
    # Sanitize project_id: только простой slug (без '/', '..') — защита §16
    # от path traversal при резолве projects_17/<project_id>.
    pid = opp.project_id
    if pid and "/" not in pid and "\\" not in pid and pid not in ("..", "."):
        candidates.append(Path("projects_17") / pid)
    for cand in candidates:
        try:
            if cand.exists():
                return Project.load(cand)
        except Exception:  # noqa: BLE001 — broken project.yaml → try next
            continue
    return None


# PROPOSE / SELECT (Universal Scenario Intelligence adapter — Phase 8)
def propose(opp: Opportunity, *, event_bus: Any = None) -> Opportunity:
    """PROPOSE: SELECT a scenario via Universal Scenario Intelligence (Phase 8).

    Phase 8 (promt 91): делегирует в ``ScenarioIntelligence.select()`` —
    domain-neutral decision layer (discovery → evaluation → ranking → selection
    → capability resolution → factory/forge). Решение сохраняется в
    ``provenance['scenario_decision']`` (traceability §7).

    Fallback (backward compatibility): если ScenarioIntelligence недоступен или
    вернул ``unavailable`` — legacy путь напрямую через ScenarioRegistry
    (прежнее поведение Phase 7). Никогда не бросает наружу (fail-safe).

    Phase 7 (GAP B): при успешном выборе публикует ``scenario.selected``
    (через ScenarioIntelligence; event_bus=None → no-op).
    """
    # Phase 8 canonical path: Universal Scenario Intelligence.
    SI = _lazy_import("scripts_01.scenario_intelligence", "ScenarioIntelligence")
    if SI is not None:
        try:
            decision = SI().select(opp, top_n=3, event_bus=event_bus, persist=False)
            if decision.selected_scenario_id is not None:
                opp.scenario = {
                    "scenario_id": decision.selected_scenario_id,
                    "role_id": decision.evidence.get("role_id"),
                    "score": decision.score,
                    "title": decision.evidence.get("display_name") or decision.selected_scenario_id,
                    "capability": decision.capability,
                }
                opp.roles = _probe_pipeline_roles()
                opp.provenance["scenario_decision"] = decision.to_dict()
                return opp
        except Exception as exc:  # noqa: BLE001 — fall back to legacy
            _LAZY_IMPORT_ERRORS.append(f"scenario_intelligence: {exc}")

    # Legacy path (BC) — direct ScenarioRegistry (pre-Phase 8 behavior).
    try:
        from core_02.scenario_registry import ScenarioRegistry
    except ImportError as exc:
        _LAZY_IMPORT_ERRORS.append(f"scenario_registry: {exc}")
        return opp

    try:
        registry = ScenarioRegistry()
    except Exception:  # noqa: BLE001
        return opp

    proposals: List[Tuple[Any, Any, float]] = []
    try:
        proposals = registry.propose_roles(opp.title + " " + opp.description, top_n=3)
    except Exception:  # noqa: BLE001
        proposals = []

    if not proposals:
        return opp

    scenario, role, score = proposals[0]
    opp.scenario = {
        "scenario_id": scenario.scenario_id,
        "role_id": role.role_id,
        "score": float(score),
        "title": getattr(role, "title", "") or role.role_id,
    }
    opp.roles = _probe_pipeline_roles()
    _emit_event(
        event_bus, "scenario.selected", source="opportunity_engine",
        opportunity_id=opp.id, project_id=opp.project_id,
        scenario_id=opp.scenario.get("scenario_id"),
        role_id=opp.scenario.get("role_id"),
        score=opp.scenario.get("score"),
    )
    return opp


def _probe_pipeline_roles() -> List[Dict[str, Any]]:
    """Probe PIPELINE_CHAIN from ForgeFacade if available; else empty list."""
    try:
        from core_02.forge_facade import ForgeFacade  # type: ignore
    except ImportError as exc:
        _LAZY_IMPORT_ERRORS.append(f"forge_facade: {exc}")
        return []
    chain = getattr(ForgeFacade, "PIPELINE_CHAIN", None) or []
    return [{"role_id": r, "source": "PIPELINE_CHAIN"} for r in chain]


# EXECUTE (ForgeFacade adapter)
def execute(
    opp: Opportunity,
    *,
    dry_run: bool = False,
    memory_store: Any = None,
    learning_loop: Any = None,
    project_root: Optional[Path] = None,
    factory_registry: Any = None,
    event_bus: Any = None,
) -> Opportunity:
    """EXECUTE: Opportunity → Scenario → Factory → ForgeFacade.run_chain.

    Phase 7 (GAP A closure, CONFLICT-3):
      - Резолвит Project-объект (НЕ строку project_id — фикс бага real-path).
      - Factory selection через ``FactoryRegistry.select_forge(capability)``;
        при отсутствии capability/фабрики/кузни — fallback на существующий
        pipeline (backward compatibility, evidence-based).
      - ForgeFacade инстанцируется (run_chain — instance method) и остаётся
        единственным execution boundary (§16).
      - Selection записывается в ``provenance['factory_selection']`` (traceability §15).

    NOTE (ADR-018 §2 — семантика полей):
      - capability: закрытый токен (KNOWN_CAPABILITIES); None → fallback
        (provenance['factory_selection'].fallback=True), не краш.
      - factory_id / forge_id: АДВИЗОРНЫЕ (traceability в provenance),
        НЕ управляют исполнением. Единственный управляющий вход в
        ForgeFacade.run_chain — role_ids из opp.roles.
      - В системе единый ForgeFacade/ForgePipeline; физического выбора кузни нет.

    GAP-2 (promt 085 §9): после execution результат возвращается в Memory/Learning
    через :func:`accumulate` — на обоих исходах (COMPLETED → success, FAILED → failure).
    Ошибки ACCUMULATE НЕ меняют статус (закрытый словарь статусов) — фиксируются
    в ``provenance['accumulate_error']`` (§17 partial failure без маскировки).

    Phase 7 (GAP B closure, CONFLICT-2): публикует ``execution.started/completed/failed``
    и передаёт ``event_bus`` в :func:`advance` (opportunity.deferred/reactivated/
    completed/failed). ``event_bus=None`` → no-op (hermetic default).
    """
    if dry_run:
        opp.status = "READY" if opp.status == "ACTIVE" else opp.status
        opp.provenance.setdefault("dry_run", True)
        return opp

    # Нормализация статуса ДО run_chain (fail-safe, никогда не крашит):
    #  - COMPLETED — терминальный: повторный execute не трогаем (no-op);
    #  - DEFERRED — реактивация по графу (DEFERRED→REACTIVATED→ACTIVE) перед run;
    #  - ACTIVE/FAILED — через READY (retry-allowed для FAILED, promt 079_19 §3.1 #7);
    #  - READY — уже готов к run.
    if opp.status == "COMPLETED":
        return opp
    if opp.status == "DEFERRED":
        opp = advance(opp, "REACTIVATED",
                      reason="execute reactivates deferred", event_bus=event_bus)
    if opp.status in ("ACTIVE", "FAILED"):
        opp = advance(opp, "READY", reason="execution started")

    # Factory selection (GAP A closure): Opportunity → FactoryRegistry.select_forge
    selected = _select_factory_forge(opp, factory_registry=factory_registry)
    if selected is not None:
        fp, fg = selected
        opp.provenance["factory_selection"] = {
            "factory_id": fp.factory_id,
            "forge_id": fg.forge_id,
            "capability": _derive_capability(opp),
        }
    else:
        opp.provenance["factory_selection"] = {
            "fallback": True,
            "reason": "no capability/factory/forge match — pipeline fallback",
        }

    ForgeFacade = _lazy_import("core_02.forge_facade", "ForgeFacade")
    if ForgeFacade is None:
        _LAZY_IMPORT_ERRORS.append("forge_facade: unavailable")
        opp = advance(opp, "FAILED", reason="forge_facade unavailable", event_bus=event_bus)
        _accumulate_best_effort(opp, memory_store=memory_store, learning_loop=learning_loop)
        return opp

    # Project resolution (GAP A fix): run_chain требует Project-объект, не строку.
    project = _resolve_project(opp, project_root=project_root)
    role_ids = [r.get("role_id") for r in opp.roles if r.get("role_id")]

    _emit_event(
        event_bus, "execution.started", source="opportunity_engine",
        opportunity_id=opp.id, project_id=opp.project_id,
        role_ids=role_ids, factory_selection=opp.provenance.get("factory_selection"),
    )
    try:
        facade = ForgeFacade()
        result = facade.run_chain(project, role_ids=role_ids)
    except Exception as exc:  # noqa: BLE001
        opp = advance(opp, "FAILED", reason=f"run_chain raised: {exc}", event_bus=event_bus)
        _emit_event(
            event_bus, "execution.failed", source="opportunity_engine",
            opportunity_id=opp.id, project_id=opp.project_id, reason=str(exc),
        )
        _accumulate_best_effort(opp, memory_store=memory_store, learning_loop=learning_loop)
        return opp

    if hasattr(result, "to_dict"):
        raw = result.to_dict()
    else:
        raw = getattr(result, "__dict__", None) or str(result)
    opp.artifacts = [{"raw": raw}]
    try:
        opp = advance(opp, "COMPLETED", reason="forge chain finished", event_bus=event_bus)
    except InvalidTransition:
        # Fail-safe (never raises): неожиданный входной статус (напр. REACTIVATED,
        # не прошедший нормализацию) не должен крашить execute() — деградируем в
        # FAILED с понятной причиной (docstring: никогда не бросает наружу).
        _reason = f"cannot complete from status {opp.status!r}"
        try:
            opp = advance(opp, "FAILED", reason=_reason, event_bus=event_bus)
        except InvalidTransition:
            # Последний рубеж: даже незарегистрированный/повреждённый статус не
            # должен выйти наружу из execute() — прямое присвоение (минуя граф).
            # Намеренное расхождение с graph-путём: previous_status не трогаем и
            # opportunity.failed не эмитим (это не валидный переход) — только
            # execution.failed ниже, чтобы не вводить подписчиков в заблуждение.
            opp.status = "FAILED"
            opp.failed_at = _now_iso()
            opp.failure_reason = _reason
            opp.updated_at = _now_iso()
        _emit_event(
            event_bus, "execution.failed", source="opportunity_engine",
            opportunity_id=opp.id, project_id=opp.project_id, reason=_reason,
        )
        _accumulate_best_effort(opp, memory_store=memory_store, learning_loop=learning_loop)
        return opp

    _emit_event(
        event_bus, "execution.completed", source="opportunity_engine",
        opportunity_id=opp.id, project_id=opp.project_id,
        overall=getattr(result, "overall", None),
    )
    _accumulate_best_effort(opp, memory_store=memory_store, learning_loop=learning_loop)
    return opp


# ACCUMULATE (GAP-2, promt 085 §9-§11): результат Opportunity → Memory → Learning.
def accumulate(
    opp: Opportunity,
    *,
    memory_store: Any = None,
    learning_loop: Any = None,
    memory_db: Optional[Path] = None,
) -> Dict[str, Any]:
    """ACCUMULATE: Artifact → MemoryStore (KO kind=candidate, tag=opportunity) → LearningLoop.

    Lineage §10: OPPORTUNITY → ARTIFACT → MEMORY ENTRY хранится в существующей
    модели (knowledge_id в ``provenance['memory_knowledge_id']``), без новой БД.

    Returns:
        {"accumulated": bool, "knowledge_id": str|None, "learning_event_id": str|None,
         "confidence": float|None, "outcome": "success"|"failure", "error": str|None]
    """
    MemoryStore = _lazy_import("core_02.memory_store", "MemoryStore")
    if MemoryStore is None:
        return {"accumulated": False, "knowledge_id": None, "learning_event_id": None,
                "confidence": None, "outcome": "failure", "error": "memory_store unavailable"}
    store = memory_store if memory_store is not None else MemoryStore(memory_db or MEMORY_DB_PATH)
    outcome = "success" if opp.status == "COMPLETED" else "failure"

    kid: Optional[str] = None
    try:
        content = json.dumps(opp.artifacts, ensure_ascii=False, default=str)
        kid = store.store_knowledge(
            kind="candidate",
            content=content[:4000],
            title=f"Opportunity {opp.id}: {opp.title}",
            summary=(f"source={opp.source} project={opp.project_id} status={opp.status} "
                     f"priority={opp.priority}"),
            tags=["opportunity", opp.id, opp.project_id],
            lifecycle_stage="validated" if opp.status == "COMPLETED" else "raw",
            status="draft",
            confidence_score=0.9 if opp.status == "COMPLETED" else 0.3,
        )
    except Exception as exc:  # noqa: BLE001
        return {"accumulated": False, "knowledge_id": None, "learning_event_id": None,
                "confidence": None, "outcome": outcome, "error": f"store_knowledge: {exc}"}

    eid: Optional[str] = None
    try:
        eid = store.record_learning_event(
            trigger_id=f"opportunity:{opp.id}",
            context_snapshot={
                "opportunity_id": opp.id,
                "project_id": opp.project_id,
                "source": opp.source,
                "status": opp.status,
                "artifact_count": len(opp.artifacts),
            },
            outcome=outcome,
            lesson_id=kid,
        )
    except Exception as exc:  # noqa: BLE001
        return {"accumulated": True, "knowledge_id": kid, "learning_event_id": None,
                "confidence": None, "outcome": outcome, "error": f"record_learning_event: {exc}"}

    confidence: Optional[float] = None
    if opp.status == "COMPLETED":
        try:
            loop = learning_loop
            if loop is None:
                LearningLoop = _lazy_import("core_02.learning_loop", "LearningLoop")
                if LearningLoop is not None:
                    loop = LearningLoop(store)
            if loop is not None:
                confidence = loop.record_feedback(kid, "success")
        except Exception:  # noqa: BLE001 — feedback best-effort
            confidence = None

    opp.provenance["memory_knowledge_id"] = kid
    opp.provenance["learning_event_id"] = eid
    return {"accumulated": True, "knowledge_id": kid, "learning_event_id": eid,
            "confidence": confidence, "outcome": outcome, "error": None}


def _accumulate_best_effort(opp: Opportunity, *, memory_store: Any = None, learning_loop: Any = None) -> None:
    """Вызвать accumulate с полным fail-safe: ошибки фиксируются, статус не меняется (§17)."""
    try:
        result = accumulate(opp, memory_store=memory_store, learning_loop=learning_loop)
        opp.provenance["accumulate"] = result
        if result.get("error"):
            opp.provenance["accumulate_error"] = result["error"]
    except Exception as exc:  # noqa: BLE001
        opp.provenance["accumulate_error"] = str(exc)


# JSON / output discipline
def _emit_json(payload: Dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _emit_text(line: str, *, json_mode: bool) -> None:
    out = sys.stderr if json_mode else sys.stdout
    out.write(line + "\n")
    out.flush()


# CLI
def _cli_discover(args: argparse.Namespace) -> int:
    store = OpportunityStore(args.data_path)
    json_mode = bool(args.json)
    _LAZY_IMPORT_ERRORS.clear()
    source_paths: Dict[str, Path] = {}
    if getattr(args, "whim_path", None):
        source_paths["whims"] = Path(args.whim_path)
    if getattr(args, "pulse_db", None):
        source_paths["pulse"] = Path(args.pulse_db)
    if getattr(args, "event_db", None):
        source_paths["events"] = Path(args.event_db)
    if getattr(args, "memory_db", None):
        source_paths["memory"] = Path(args.memory_db)
    candidates = discover_candidates(
        args.project_id,
        max_results=args.max_results,
        store=store,
        source_paths=source_paths or None,
        rank=bool(getattr(args, "rank", False)),
    )
    for c in candidates:
        store.upsert(c)
    payload = {
        "opportunity_engine": "discover",
        "project_id": args.project_id,
        "discovered": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
        "degraded": not candidates,
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if json_mode:
        _emit_json(payload)
    else:
        _emit_text(
            f"discovered: {len(candidates)} candidate(s); project_id={args.project_id}",
            json_mode=False,
        )
    return 0


def _cli_propose(args: argparse.Namespace) -> int:
    _LAZY_IMPORT_ERRORS.clear()  # per-invocation boundary (Phase 14 Option B3)
    store = OpportunityStore(args.data_path)
    opp = store.get(args.opportunity_id)
    if opp is None:
        _emit_text(
            f"error: opportunity_id {args.opportunity_id!r} not found",
            json_mode=bool(args.json),
        )
        return 1
    opp = propose(opp)
    store.upsert(opp)
    payload = {
        "opportunity_engine": "propose",
        "opportunity": opp.to_dict(),
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        scen = opp.scenario or {}
        _emit_text(
            f"proposed: scenario={scen.get('scenario_id', '-')} "
            f"role={scen.get('role_id', '-')} roles_count={len(opp.roles)}",
            json_mode=False,
        )
    return 0


def _make_cli_event_bus() -> Any:
    """Реальный EventBus для CLI execution path (canonical app bus). Fail-safe.

    Использует ``get_default_event_bus()`` (bootstrap-конвенция) — НЕ создаёт
    вторую шину/схему (§9). None при недоступности (degraded-safe).
    """
    try:
        from scripts_01.event_bus import get_default_event_bus
        return get_default_event_bus()
    except Exception:  # noqa: BLE001
        return None


def _cli_run(args: argparse.Namespace) -> int:
    _LAZY_IMPORT_ERRORS.clear()  # per-invocation boundary (Phase 14 Option B3)
    store = OpportunityStore(args.data_path)
    opp = store.get(args.opportunity_id)
    if opp is None:
        _emit_text(
            f"error: opportunity_id {args.opportunity_id!r} not found",
            json_mode=bool(args.json),
        )
        return 1
    # Real CLI execution path публикует события (dry-run — нет, hermetic).
    bus = None if args.dry_run else _make_cli_event_bus()
    opp = propose(opp, event_bus=bus)
    if args.dry_run:
        opp.provenance["dry_run"] = True
        store.upsert(opp)
        payload = {
            "opportunity_engine": "run",
            "dry_run": True,
            "opportunity": opp.to_dict(),
            "import_warnings": list(_LAZY_IMPORT_ERRORS),
            "timestamp": _now_iso(),
        }
        if args.json:
            _emit_json(payload)
        else:
            scen = opp.scenario or {}
            _emit_text(
                f"dry-run plan: scenario={scen.get('scenario_id', '-')} "
                f"roles={[r.get('role_id') for r in opp.roles]}",
                json_mode=False,
            )
        return 0
    opp = execute(opp, dry_run=False, event_bus=bus)
    store.upsert(opp)
    payload = {
        "opportunity_engine": "run",
        "dry_run": False,
        "opportunity": opp.to_dict(),
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"run result: status={opp.status} "
            f"artifacts={len(opp.artifacts)} failed_at={opp.failed_at or '-'}",
            json_mode=False,
        )
    return 0 if opp.status != "FAILED" else 1


def _cli_status(args: argparse.Namespace) -> int:
    _LAZY_IMPORT_ERRORS.clear()  # per-invocation boundary (Phase 14 Option B3)
    store = OpportunityStore(args.data_path)
    opp = store.get(args.opportunity_id)
    if opp is None:
        _emit_text(
            f"error: opportunity_id {args.opportunity_id!r} not found",
            json_mode=bool(args.json),
        )
        return 1
    payload = {
        "opportunity_engine": "status",
        "opportunity": opp.to_dict(),
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"{opp.id} status={opp.status} source={opp.source} "
            f"priority={opp.priority} created={opp.created_at}",
            json_mode=False,
        )
    return 0


def _cli_list(args: argparse.Namespace) -> int:
    _LAZY_IMPORT_ERRORS.clear()  # per-invocation boundary (Phase 14 Option B3)
    store = OpportunityStore(args.data_path)
    items = store.by_status(args.status) if args.status else store.all()
    payload = {
        "opportunity_engine": "list",
        "count": len(items),
        "filter_status": args.status,
        "items": [o.to_dict() for o in items],
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(
            f"count={len(items)}" + (f" status={args.status}" if args.status else ""),
            json_mode=False,
        )
    return 0


def _cli_rank(args: argparse.Namespace) -> int:
    """Read-only: ранжирование существующих opportunity по композитному score (promt 086)."""
    _LAZY_IMPORT_ERRORS.clear()  # per-invocation boundary (Phase 14 Option B3)
    store = OpportunityStore(args.data_path)
    items = store.all()
    ranked = rank_candidates(items)
    top = ranked[0].id if ranked else "-"
    payload = {
        "opportunity_engine": "rank",
        "count": len(ranked),
        "top": top,
        "items": [o.to_dict() for o in ranked],
        "import_warnings": list(_LAZY_IMPORT_ERRORS),
        "timestamp": _now_iso(),
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_text(f"ranked: {len(ranked)} opportunity(ies); top={top}", json_mode=False)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opportunity_engine",
        description="Opportunity Engine — Phase 1 vertical slice (per promt 079_19).",
    )
    parser.add_argument(
        "--data-path", default=str(DEFAULT_DATA_PATH),
        help=f"YAML persistence path (default {DEFAULT_DATA_PATH})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_dis = sub.add_parser("discover", help="scan real sources → opportunity candidates")
    p_dis.add_argument("--project-id", required=True)
    p_dis.add_argument("--max", type=int, default=10, dest="max_results")
    p_dis.add_argument("--whim-path", default=None, help="path to whims.yaml (default data_13/whims.yaml)")
    p_dis.add_argument("--pulse-db", default=None, help="path to project_pulse.db (default data_13/project_pulse.db)")
    p_dis.add_argument("--event-db", default=None, help="path to events.db (default context_12/events.db)")
    p_dis.add_argument("--memory-db", default=None, help="path to context.db (default data_13/context.db)")
    p_dis.add_argument("--rank", action="store_true", help="rank candidates by composite score (promt 086)")
    p_dis.add_argument("--json", action="store_true")
    p_dis.set_defaults(func=_cli_discover)

    p_prop = sub.add_parser("propose", help="SELECT scenario for opportunity")
    p_prop.add_argument("opportunity_id")
    p_prop.add_argument("--json", action="store_true")
    p_prop.set_defaults(func=_cli_propose)

    p_run = sub.add_parser("run", help="PROPOSE → EXECUTE → VALIDATE cycle")
    p_run.add_argument("opportunity_id")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=_cli_run)

    p_stat = sub.add_parser("status", help="show lifecycle state")
    p_stat.add_argument("opportunity_id")
    p_stat.add_argument("--json", action="store_true")
    p_stat.set_defaults(func=_cli_status)

    p_list = sub.add_parser("list", help="list opportunities")
    p_list.add_argument("--status", choices=STATUSES, default=None)
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cli_list)

    p_rank = sub.add_parser("rank", help="rank stored opportunities by composite score (read-only)")
    p_rank.add_argument("--json", action="store_true")
    p_rank.set_defaults(func=_cli_rank)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse calls sys.exit() on parse error; surface as our exit code 2.
        return int(exc.code) if exc.code is not None else 2
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 — fail-safe per spec
        _emit_text(f"error: opportunity_engine unexpected failure: {exc}", json_mode=False)
        return 2


__all__ = [
    "Opportunity",
    "OpportunityStore",
    "advance",
    "InvalidTransition",
    "discover_candidates",
    "propose",
    "execute",
    "accumulate",
    "rank_score",
    "rank_candidates",
    "RANK_WEIGHTS",
    "SOURCE_WEIGHTS",
    "STATUSES",
    "TERMINAL_STATUSES",
]


if __name__ == "__main__":
    sys.exit(main())
