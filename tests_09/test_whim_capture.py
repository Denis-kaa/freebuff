"""tests_09/test_whim_capture.py — Unit tests for Whim Capture (Phase 1.2).

Coverage (mirror opportunity_engine.py test design):
- Lifecycle forward-only state graph (per promt 080_19 §3.3 #8).
- Terminal statuses PROMOTED_TO_OPPORTUNITY/DISCARDED block all transitions.
- Invalid transitions raise InvalidTransition (NEW→PROMOTED-TO-OPPORTUNITY is NOT allowed).
- "DEFERRED ≠ DELETED" semantics: record preserved through deferred-cycle.
- Triage heuristic is deterministic (keyword whitelist).
- Capture validation: empty body / empty project_id → ValueError.
- Schema persistence: corrupt YAML degrades to empty.
- Atomic write: no .tmp leftovers after upsert.
- Lazy hook to opportunity_engine (whim_promote → opp_upsert) integration.
- CLI --json output is parseable; exit codes 0/1/2 deterministic.
- ANTI-6b vocab safety: whim_capture NOT in KNOWN_CAPABILITIES.
"""
from __future__ import annotations

import json
import subprocess
import sys
}
from typing import List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts_01"
DATA_13 = REPO_ROOT / "data_13"
sys.path.insert(0, str(SCRIPTS_DIR))

from whim_capture import (  # noqa: E402
    Whim,
    WhimStore,
    InvalidTransition,
    STATUSES,
    TERMINAL_STATUSES,
    CLASSIFICATIONS,
    advance,
    capture,
    triage,
    promote,
    defer,
    classify_heuristic,
    main,
    _cli_capture,
    _cli_list,
    _cli_status,
    _cli_triage,
    _cli_promote,
    _cli_defer,
    _cli_get,
)


# ─── Helpers ──────────────────────────────────────────────────────────────

def _make_whim(project_id: str = "proj-test", **kwargs) -> Whim:
    now = "2026-08-12T00:00:00+00:00"
    whim = Whim(
        id="whim-test-001",
        project_id=project_id,
        body="Test whim body",
        source="cli",
        status="NEW",
        created_at=now,
        updated_at=now,
    )
    for k, v in kwargs.items():
        setattr(whim, k, v)
    return whim


# ─── 1. Lifecycle status constants ───────────────────────────────────────

def test_statuses_canonical():
    assert STATUSES == (
        "NEW", "TRIAGED", "PROMOTED_TO_OPPORTUNITY",
        "DISCARDED", "DEFERRED", "FAILED",
    )
    # Per pomt 080_19 §3.3 #8 — these two are terminal only.
    assert TERMINAL_STATUSES == ("PROMOTED_TO_OPPORTUNITY", "DISCARDED")
    assert "CLASSIFICATIONS" in dir(sys.modules["whim_capture"])
    assert CLASSIFICATIONS == ("KEEP", "DISCARD", "PROMOTE_CANDIDATE")


def test_valid_transitions_per_pomt():
    """Per pomt 080_19 §3.1 + thinker design verification."""
    from whim_capture import _TRANSITIONS
    assert set(_TRANSITIONS["NEW"]) == {"TRIAGED", "DEFERRED", "FAILED"}
    assert set(_TRANSITIONS["TRIAGED"]) == {"PROMOTED_TO_OPPORTUNITY", "DISCARDED", "DEFERRED", "FAILED"}
    assert tuple(_TRANSITIONS["PROMOTED_TO_OPPORTUNITY"]) == ()  # terminal
    assert tuple(_TRANSITIONS["DISCARDED"]) == ()  # terminal
    assert set(_TRANSITIONS["DEFERRED"]) == {"TRIAGED", "DISCARDED", "FAILED"}
    assert set(_TRANSITIONS["FAILED"]) == {"NEW"}  # retry path
    # NEW cannot skip TRIAGED → PROMOTED_TO_OPPORTUNITY:
    assert "PROMOTED_TO_OPPORTUNITY" not in _TRANSITIONS["NEW"]


# ─── 2. State machine enforcement ────────────────────────────────────────

def test_new_to_triaged_succeeds():
    w = _make_whim()
    w = advance(w, "TRIAGED")
    assert w.status == "TRIAGED"
    assert w.triaged_at  # timestamp set


def test_triaged_to_promoted_succeeds():
    w = _make_whim(status="TRIAGED", classification="PROMOTE_CANDIDATE")
    # Direct advance bypasses promote()'s classification gate (used in tests only).
    w = advance(w, "PROMOTED_TO_OPPORTUNITY")
    assert w.status == "PROMOTED_TO_OPPORTUNITY"
    assert w.promoted_at


def test_new_to_promoted_blocked():
    """NEW cannot skip TRIAGED per pomt 080_19 lifecycle design."""
    w = _make_whim()
    with pytest.raises(InvalidTransition) as ei:
        advance(w, "PROMOTED_TO_OPPORTUNITY")
    assert "NEW" in str(ei.value) and "PROMOTED_TO_OPPORTUNITY" in str(ei.value)


def test_terminal_promoted_blocks_transitions():
    w = _make_whim(status="PROMOTED_TO_OPPORTUNITY")
    for target in ("NEW", "TRIAGED", "DISCARDED", "DEFERRED", "FAILED"):
        with pytest.raises(InvalidTransition):
            advance(w, target)


def test_terminal_discarded_blocks_transitions():
    w = _make_whim(status="DISCARDED")
    for target in ("NEW", "TRIAGED", "PROMOTED_TO_OPPORTUNITY", "DEFERRED", "FAILED"):
        with pytest.raises(InvalidTransition):
            advance(w, target)


def test_failed_to_new_retry_path():
    """FAILED retry-allowed → NEW (per opportunity_engine pattern, promt §3.3)."""
    w = _make_whim(status="FAILED", classification="PROMOTE_CANDIDATE")
    w.failure_reason = "opportunity_engine unavailable"
    w = advance(w, "NEW")
    assert w.status == "NEW"
    # NEW retry resets classification
    assert w.classification is None
    assert w.triaged_at is None
    assert w.failure_reason is None


def test_deferred_preserves_record_through_retriage():
    """DEFERRED ≠ DELETED: classification/timestamps preserved."""
    w = _make_whim(classification="KEEP")
    # Pre-trip via advance() so triaged_at timestamp is actually set.
    w = advance(w, "TRIAGED")
    assert w.triaged_at is not None  # sanity: timestamps set
    w = advance(w, "DEFERRED", reason="later")
    assert w.status == "DEFERRED"
    assert w.deferred_reason == "later"
    assert w.classification == "KEEP"  # preserved
    assert w.triaged_at is not None  # preserved through DEFERRED cycle
    original_id = w.id
    w = advance(w, "TRIAGED")
    assert w.status == "TRIAGED"
    assert w.id == original_id


def test_unknown_status_raises():
    w = _make_whim(status="FOOBAR")
    with pytest.raises(InvalidTransition):
        advance(w, "TRIAGED")


# ─── 3. Capture validation ──────────────────────────────────────────────

def test_capture_empty_body_raises():
    with pytest.raises(ValueError):
        capture("   ", project_id="proj-x", source="cli")


def test_capture_empty_project_id_raises():
    with pytest.raises(ValueError):
        capture("valid body", project_id="", source="cli")


def test_capture_invalid_source_raises():
    with pytest.raises(ValueError):
        capture("valid body", project_id="proj-x", source="invalid")


def test_capture_priority_clamped():
    w = capture("body", project_id="proj-x", source="cli", priority=99)
    assert w.priority == 10  # clamped to max
    w = capture("body", project_id="proj-x", source="cli", priority=-5)
    assert w.priority == 0   # clamped to min


def test_capture_persists(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    w = capture("body", project_id="proj-1", source="cli", priority=5, store=store)
    assert w.id
    loaded = store.get(w.id)
    assert loaded is not None
    assert loaded.body == "body"


# ─── 4. Triage heuristic deterministic ───────────────────────────────────

def test_classify_promote_keywords():
    # v1.0 stem-fix (Russian morphology): PROMOTE_KEYWORDS now contain stems
    # ('стать' catches 'статья'/'статьи', 'книг' catches 'книга'/'книгу'/'книги').
    # Each tuple: (body, expected_stem_in_why).
    for body, stem in (
        ("Идея статья по теме X", "стать"),
        ("Идея книга по теме X", "книг"),
        ("Идея guide по теме X", "guide"),
        ("Идея план по теме X", "план"),
        ("Идея tutorial по теме X", "tutorial"),
    ):
        cls, why = classify_heuristic(body)
        assert cls == "PROMOTE_CANDIDATE", f"body={body!r} cls={cls!r}"
        assert why == f"matched-keyword:{stem}", f"body={body!r} why={why!r}"


def test_classify_discard_keywords():
    for kw in ("спам", "тест", "junk", "повтор"):
        cls, why = classify_heuristic(f"Какой-то {kw} content")
        assert cls == "DISCARD"
        assert why == f"matched-keyword:{kw}"


def test_classify_no_keyword_default_keep():
    cls, why = classify_heuristic("Просто текст без ключевых слов")
    assert cls == "KEEP"
    assert why == "no-keyword-matched"


def test_classify_promote_wins_over_discard():
    """Order: PROMOTE_KEYWORDS checked first (per pomt 080_19 §3.1 #2)."""
    cls, why = classify_heuristic("спам про книгу")  # both keywords present
    assert cls == "PROMOTE_CANDIDATE"


# ─── 5. Triage explicit override ─────────────────────────────────────────

def test_triage_explicit_classification(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    w = capture("body", project_id="proj-x", source="cli", store=store)
    triage(w, classification="DISCARD", reason="test override", override_heuristic=True)
    assert w.status == "TRIAGED"
    assert w.classification == "DISCARD"
    assert w.classification_reason == "test override"
    assert w.triaged_by == "user"


def test_triage_uses_heuristic_when_no_override(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    w = capture("статья по архитектуре", project_id="proj-x", source="cli", store=store)
    triage(w, override_heuristic=False)
    assert w.classification == "PROMOTE_CANDIDATE"
    assert w.triaged_by == "heuristic"


def test_triage_invalid_classification_raises():
    w = _make_whim()
    with pytest.raises(ValueError):
        triage(w, classification="invalid_class", override_heuristic=True)


def test_triage_invalid_source_state_raises(tmp_path: Path):
    w = _make_whim(status="DISCARDED")
    with pytest.raises(InvalidTransition):
        triage(w, classification="KEEP")


# ─── 6. Promote hook (lazy opportunity_engine integration) ───────────────

def test_promote_requires_promote_candidate_classification(tmp_path: Path):
    w = _make_whim()
    w = triage(w, classification="KEEP", override_heuristic=True)
    # classification must be PROMOTE_CANDIDATE for promote
    store = WhimStore(tmp_path / "whims.yaml")
    with pytest.raises(ValueError) as ei:
        promote(w, store=store)
    assert "PROMOTE_CANDIDATE" in str(ei.value)


def test_promote_creates_opportunity(tmp_path: Path, monkeypatch):
    """Lazy hook to opportunity_engine creates opportunity in data_13/opportunities.yaml."""
    # Use tmp_path for opportunities.yaml too (override DEFAULT via monkeypatch)
    opp_path = tmp_path / "opps_test.yaml"
    whim_path = tmp_path / "whims_test.yaml"

    import scripts_01.opportunity_engine as opp_engine
    monkeypatch.setattr(opp_engine, "DEFAULT_DATA_PATH", opp_path)

    store = WhimStore(whim_path)
    w = capture("статья по архитектуре", project_id="proj-promote", source="cli", store=store)
    triage(w, override_heuristic=False)  # classification=PROMOTE_CANDIDATE (heuristic)
    promote(w, store=store)
    assert w.status == "PROMOTED_TO_OPPORTUNITY"
    assert w.related_opportunity_id is not None
    assert w.promoted_at
    # Verify opportunity written
    opp_store = opp_engine.OpportunityStore(opp_path)
    opp = opp_store.get(w.related_opportunity_id)
    assert opp is not None
    assert opp.project_id == "proj-promote"
    assert w.id in opp.related_whims


def test_promote_failed_no_opportunity_engine(tmp_path: Path, monkeypatch):
    """If opportunity_engine import fails, promote → FAILED."""
    # Break the import target: point sys.modules to a fake module that raises ImportError
    import sys as _sys
    monkeypatch.setitem(_sys.modules, "scripts_01.opportunity_engine", None)
    # When modules dict has None, import raises ImportError
    whim_path = tmp_path / "whims.yaml"
    store = WhimStore(whim_path)
    w = capture("статья по архитектуре", project_id="proj-x", source="cli", store=store)
    triage(w, override_heuristic=False)
    promote(w, store=store)
    # falls through to FAILED transition with reason
    assert w.status == "FAILED"
    assert w.failure_reason and "promote failed" in w.failure_reason


# ─── 7. Defer preserves audit ─────────────────────────────────────────────

def test_defer_preserves_classification():
    w = _make_whim(status="TRIAGED", classification="PROMOTE_CANDIDATE")
    w = defer(w, reason="after launch")
    assert w.status == "DEFERRED"
    assert w.classification == "PROMOTE_CANDIDATE"  # preserved
    assert w.deferred_reason == "after launch"


def test_defer_from_terminal_blocked():
    w = _make_whim(status="PROMOTED_TO_OPPORTUNITY")
    with pytest.raises(InvalidTransition):
        defer(w, reason="too late")


# ─── 8. Persistence ───────────────────────────────────────────────────────

def test_store_roundtrip(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    w = _make_whim()
    store.upsert(w)
    store2 = WhimStore(p)
    loaded = store2.get(w.id)
    assert loaded is not None
    assert loaded.body == "Test whim body"


def test_store_corrupt_yaml_recovers(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    p.write_text(":bad:yaml::: [invalid", encoding="utf-8")
    store = WhimStore(p)
    assert store.count() == 0


def test_store_atomic_write_no_tmp_leak(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    store.upsert(_make_whim())
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == [], f"atomic write leaked: {leftovers}"


def test_store_filter_by_status_and_project(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    store = WhimStore(p)
    store.upsert(_make_whim(id="w1", **{"status": "NEW", "project_id": "alpha"}))
    store.upsert(_make_whim(id="w2", **{"status": "TRIAGED", "project_id": "alpha"}))
    store.upsert(_make_whim(id="w3", **{"status": "NEW", "project_id": "beta"}))
    assert len(store.by_status("NEW")) == 2
    assert len(store.by_project("alpha")) == 2
    assert len(store.by_status("DISCARDED")) == 0


# ─── 9. JSON discipline (CLI --json stdout parseable) ───────────────────

def test_cli_capture_json_is_parseable(tmp_path: Path):
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "whim_capture.py"),
         "--data-path", str(tmp_path / "whims.yaml"),
         "capture", "Test idea", "--project-id", "proj-cj", "--json"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0, f"capture failed: stderr={rc.stderr}"
    parsed = json.loads(rc.stdout)
    assert "whim" in parsed
    assert parsed["whim"]["status"] == "NEW"
    assert parsed["whim"]["body"] == "Test idea"


def test_cli_list_json_is_parseable(tmp_path: Path):
    p = tmp_path / "whims.yaml"
    # Pre-seed
    WhimStore(p)  # ensure parent exists
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "whim_capture.py"),
         "--data-path", str(p),
         "capture", "Seeded", "--project-id", "p1"],
        check=False,
    )
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "whim_capture.py"),
         "--data-path", str(p),
         "list", "--json"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0
    parsed = json.loads(rc.stdout)
    assert "items" in parsed
    assert parsed["count"] >= 1


# ─── 10. Exit codes ───────────────────────────────────────────────────────

def test_cli_status_unknown_returns_1():
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "whim_capture.py"),
         "--data-path", "/tmp/unused_whim.yaml",
         "status", "whim-does-not-exist"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 1


def test_cli_capture_empty_body_returns_2(tmp_path: Path):
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "whim_capture.py"),
         "--data-path", str(tmp_path / "whims.yaml"),
         "capture", "   ", "--project-id", "proj-x"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 2


def test_main_missing_command_returns_2():
    rc = main([])
    assert rc == 2


# ─── 11. ANTI-6b vocab safety ─────────────────────────────────────────────

def test_module_no_side_effects_on_known_capabilities():
    """whim_capture must NOT mutate core_02/blueprint_v3.py::KNOWN_CAPABILITIES."""
    import importlib
    if "whim_capture" in sys.modules:
        importlib.reload(sys.modules["whim_capture"])
    else:
        importlib.import_module("whim_capture")
    try:
        from core_02.blueprint_v3 import KNOWN_CAPABILITIES
    except ImportError:
        pytest.skip("blueprint_v3 not importable")
    assert "whim_capture" not in KNOWN_CAPABILITIES, (
        "ANTI-6b violation: whim_capture MUST NOT appear in KNOWN_CAPABILITIES"
    )


def test_module_loads_clean():
    """Smoke: import side-effects free."""
    import importlib
    importlib.import_module("whim_capture")
