"""tests_09/test_opportunity_ranking.py — Advanced Opportunity Ranking (promt 086).

Реализация roadmap 09_FUTURE_GAPS.md C-1: композитный score поверх provenance
confidence. Герметично: никаких production-БД, только tmp-пути.

Спека (promt 086 §SPEC):
  score = confidence·0.5 + source·0.2 + recency·0.2 + priority·0.1
  rank_candidates() — сортировка по убыванию, tie-break по свежести.
  discover_candidates(rank=True) — пул со всех источников → топ-N по score.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
}
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts_01"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT))

from opportunity_engine import (  # noqa: E402
    SOURCE_WEIGHTS,
    Opportunity,
    OpportunityStore,
    discover_candidates,
    main,
    rank_candidates,
    rank_score,
)
from scripts_01.whim_capture import WhimStore, capture, triage  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_opp(
    *,
    opp_id: str = "opp-1",
    source: str = "hand",
    confidence: float = 0.5,
    priority: int = 5,
    created_at: str = "",
    project_id: str = "proj-r",
) -> Opportunity:
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    return Opportunity(
        id=opp_id,
        project_id=project_id,
        title=f"Opp {opp_id}",
        description="ranking test",
        source=source,
        status="ACTIVE",
        priority=priority,
        created_at=created_at,
        updated_at=created_at,
        provenance={"source": source, "confidence": confidence, "stub": False},
    )


def _days_ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _hermetic_sources(tmp_path: Path, whims_yaml: Path) -> Dict[str, Path]:
    return {
        "whims": whims_yaml,
        "pulse": tmp_path / "missing_pulse.db",
        "events": tmp_path / "missing_events.db",
        "memory": tmp_path / "missing_memory.db",
    }


# ═════════════════════════════════════════════════════════════════════════
# rank_score — unit
# ═════════════════════════════════════════════════════════════════════════

def test_rank_score_default_weights_bounds():
    """score ∈ [0,1] при дефолтных весах; известная точка для hand/fresh/prio5."""
    opp = _make_opp(source="hand", confidence=0.5, priority=5)
    s = rank_score(opp)
    assert 0.0 <= s <= 1.0
    # confidence 0.5*0.5 + source 1.0*0.2 + recency ~1.0*0.2 + prio 0.444*0.1
    assert 0.68 <= s <= 0.71


def test_rank_score_confidence_clamping():
    ts = _days_ago(0)
    low = _make_opp(source="hand", confidence=0.0, created_at=ts)
    high = _make_opp(source="hand", confidence=1.0, created_at=ts)
    assert rank_score(low) < rank_score(high)
    assert rank_score(_make_opp(source="hand", confidence=-5, created_at=ts)) == rank_score(low)
    assert rank_score(_make_opp(source="hand", confidence=99, created_at=ts)) == rank_score(high)


def test_rank_score_source_weights():
    """whim=1.0 > knowledge=0.8 > event_bus=0.5; unknown=0.5 (равны event_bus)."""
    ts = _days_ago(0)
    base: Dict[str, Any] = {"confidence": 0.5, "priority": 5}
    whim = _make_opp(source="whim", created_at=ts, **base)
    kn = _make_opp(source="knowledge", created_at=ts, **base)
    ev = _make_opp(source="event_bus", created_at=ts, **base)
    unk = _make_opp(source="unknown_source", created_at=ts, **base)
    assert rank_score(whim) > rank_score(kn) > rank_score(ev)
    assert rank_score(ev) == rank_score(unk)


def test_rank_score_recency_decay():
    fresh = _make_opp(created_at=_days_ago(0))
    old = _make_opp(created_at=_days_ago(40))
    assert rank_score(fresh) > rank_score(old)
    # 40 дней назад → recency 0.0; без даты → 0.5 (выше)
    assert rank_score(_make_opp(created_at="")) > rank_score(_make_opp(created_at=_days_ago(40)))


def test_rank_score_priority_norm():
    ts = _days_ago(0)
    p1 = _make_opp(priority=1, created_at=ts)
    p5 = _make_opp(priority=5, created_at=ts)
    p10 = _make_opp(priority=10, created_at=ts)
    assert rank_score(p1) < rank_score(p5) < rank_score(p10)


def test_rank_score_custom_weights_override():
    """weights override аддитивно: confidence*1.0 доминирует."""
    ts = _days_ago(0)
    low = _make_opp(source="event_bus", confidence=0.5, priority=1, created_at=ts)
    high = _make_opp(source="event_bus", confidence=0.9, priority=1, created_at=ts)
    w = {"confidence": 1.0, "source": 0.0, "recency": 0.0, "priority": 0.0}
    assert rank_score(high, weights=w) > rank_score(low, weights=w)


# ═════════════════════════════════════════════════════════════════════════
# rank_candidates — сортировка
# ═════════════════════════════════════════════════════════════════════════

def test_rank_candidates_sorts_desc_by_score():
    low = _make_opp(opp_id="low", source="event_bus", confidence=0.3, priority=1)
    high = _make_opp(opp_id="high", source="whim", confidence=0.9, priority=10)
    mid = _make_opp(opp_id="mid", source="knowledge", confidence=0.6, priority=5)
    ranked = rank_candidates([low, high, mid])
    assert [o.id for o in ranked] == ["high", "mid", "low"]


def test_rank_candidates_tiebreak_newer_first():
    old = _make_opp(opp_id="old", created_at=_days_ago(10))
    new = _make_opp(opp_id="new", created_at=_days_ago(0))
    ranked = rank_candidates([old, new])
    assert [o.id for o in ranked] == ["new", "old"]


def test_rank_candidates_stable_on_full_tie():
    ts = _days_ago(0)
    a = _make_opp(opp_id="a", created_at=ts)
    b = _make_opp(opp_id="b", created_at=ts)
    c = _make_opp(opp_id="c", created_at=ts)
    ranked = rank_candidates([a, b, c])
    assert [o.id for o in ranked] == ["a", "b", "c"]


def test_rank_candidates_persists_traceability():
    opp = _make_opp(source="whim", confidence=0.8, priority=7)
    rank_candidates([opp])
    assert "rank_score" in opp.provenance
    assert "rank_factors" in opp.provenance
    f = opp.provenance["rank_factors"]
    assert f["source"] == "whim"
    assert f["source_weight"] == SOURCE_WEIGHTS["whim"]
    assert f["confidence"] == 0.8


def test_rank_candidates_no_persist():
    opp = _make_opp()
    rank_candidates([opp], persist_score=False)
    assert "rank_score" not in opp.provenance


# ═════════════════════════════════════════════════════════════════════════
# discover integration
# ═════════════════════════════════════════════════════════════════════════

def test_discover_rank_true_orders_by_score(tmp_path: Path):
    """rank=True: whim PROMOTE_CANDIDATE (0.8) выше plain (0.6) — топ-1 по score."""
    whims_yaml = tmp_path / "whims.yaml"
    wstore = WhimStore(whims_yaml)
    w1 = capture("Промоут-сигнал", project_id="proj-r", source="cli", store=wstore)
    triage(w1, classification="PROMOTE_CANDIDATE", reason="keyword")
    wstore.upsert(w1)
    w2 = capture("Обычный сигнал", project_id="proj-r", source="cli", store=wstore)
    wstore.upsert(w2)

    cands = discover_candidates(
        "proj-r", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), rank=True
    )
    assert len(cands) == 2
    assert cands[0].provenance["confidence"] == 0.8  # PROMOTE_CANDIDATE выше
    assert cands[1].provenance["confidence"] == 0.6
    assert cands[0].provenance.get("rank_score") is not None


def test_discover_rank_false_backward_compat(tmp_path: Path):
    """rank=False: прежний порядок источников (whim store order), без rank_score."""
    whims_yaml = tmp_path / "whims.yaml"
    wstore = WhimStore(whims_yaml)
    w1 = capture("Первый", project_id="proj-b", source="cli", store=wstore)
    triage(w1, classification="PROMOTE_CANDIDATE", reason="keyword")
    wstore.upsert(w1)
    w2 = capture("Второй", project_id="proj-b", source="cli", store=wstore)
    wstore.upsert(w2)

    cands = discover_candidates(
        "proj-b", max_results=5, source_paths=_hermetic_sources(tmp_path, whims_yaml), rank=False
    )
    assert len(cands) == 2
    assert cands[0].provenance["confidence"] == 0.8  # порядок источников (вставки)
    assert "rank_score" not in cands[0].provenance


# ═════════════════════════════════════════════════════════════════════════
# CLI smoke
# ═════════════════════════════════════════════════════════════════════════

def test_cli_rank_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture):
    """rank subcommand: read-only, сортирует stored opportunities."""
    store = OpportunityStore(tmp_path / "opps.yaml")
    store.upsert(_make_opp(opp_id="low", source="event_bus", confidence=0.3, priority=1))
    store.upsert(_make_opp(opp_id="high", source="whim", confidence=0.9, priority=10))

    rc = main(["--data-path", str(tmp_path / "opps.yaml"), "rank", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["opportunity_engine"] == "rank"
    assert payload["top"] == "high"
    assert [i["id"] for i in payload["items"]] == ["high", "low"]
