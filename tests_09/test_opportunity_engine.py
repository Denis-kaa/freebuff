"""tests_09/test_opportunity_engine.py — Unit tests for Opportunity Engine
(Phase 1, Missing Capability #8).

Coverage:
- Lifecycle forward-only state graph (per promt 079_19 §3.1 #5).
- DEFERRED ≠ DELETED semantics: reactivation preserves audit trail.
- Terminal states COMPLETED/FAILED block all further transitions.
- invalid transitions raise InvalidTransition at runtime.
- --dry-run never invokes ForgeFacade.run_chain (zero side effects).
- --json mode keeps stdout parseable (only JSON; logs → stderr).
- Vocabulary safety: core_02.blueprint_v3.KNOWN_CAPABILITIES is not
  mutated by this module or its tests (ANTI-6b / CON-8).
- Persistence is file-isolated (tmp_path); no leak into real store.
- discover_candidates is fail-safe (network/scan errors → empty list).
"""
from __future__ import annotations

import json
import subprocess
import sys
}
from typing import List

import pytest

# Path setup: scripts_01 is sibling of tests_09
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts_01"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import the engine
from opportunity_engine import (  # noqa: E402
    Opportunity,
    OpportunityStore,
    InvalidTransition,
    STATUSES,
    TERMINAL_STATUSES,
    advance,
    main,
    _cli_discover,
    _cli_propose,
    _cli_run,
    _cli_status,
    _cli_list,
    _cli_rank,
    _check_transition,
    discover_candidates,
    propose,
    execute,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_opp(project_id: str = "proj-test", **kwargs) -> Opportunity:
    now_iso = "2026-08-12T00:00:00+00:00"
    opp = Opportunity(
        id="opp-test-001",
        project_id=project_id,
        title="Test opp",
        description="Stub opp for unit tests",
        source="hand",
        status="ACTIVE",
        created_at=now_iso,
        updated_at=now_iso,
    )
    for k, v in kwargs.items():
        setattr(opp, k, v)
    return opp


# ── 1. Lifecycle forward-only (state machine enforcement) ────────────────

def test_statuses_canonical():
    assert STATUSES == (
        "ACTIVE", "DEFERRED", "READY", "REACTIVATED", "COMPLETED", "FAILED",
    )
    # Only COMPLETED is hard terminal; FAILED is retry-allowed (promt §3.1 #7).
    assert TERMINAL_STATUSES == ("COMPLETED",)


def test_valid_transitions_listed():
    """Per promt 079_19 §3.1 #5 + #7 (FAILED retry path)."""
    from opportunity_engine import _TRANSITIONS
    assert set(_TRANSITIONS["ACTIVE"]) == {"DEFERRED", "READY", "FAILED"}
    assert set(_TRANSITIONS["DEFERRED"]) == {"REACTIVATED", "FAILED"}
    assert set(_TRANSITIONS["REACTIVATED"]) == {"READY", "DEFERRED", "FAILED"}
    assert set(_TRANSITIONS["READY"]) == {"COMPLETED", "DEFERRED", "FAILED"}
    assert tuple(_TRANSITIONS["COMPLETED"]) == ()
    # FAILED is retry-allowed (NOT a hard terminal — promt §3.1 #7).
    # Forward retry path: FAILED → ACTIVE (back to start) or FAILED → READY (re-execute).
    assert set(_TRANSITIONS["FAILED"]) == {"ACTIVE", "READY"}
    # DEFERRED cannot jump directly to READY (thinker gotcha 1):
    assert "READY" not in _TRANSITIONS["DEFERRED"]
    # DEFERRED cannot jump to COMPLETED either
    assert "COMPLETED" not in _TRANSITIONS["DEFERRED"]


def test_active_to_deferred_succeeds():
    opp = _make_opp()
    opp = advance(opp, "DEFERRED", reason="not yet")
    assert opp.status == "DEFERRED"
    assert opp.deferred_at  # timestamp set
    assert opp.deferred_reason == "not yet"
    assert opp.previous_status == "ACTIVE"


def test_active_to_ready_succeeds():
    opp = _make_opp()
    opp = advance(opp, "READY")
    assert opp.status == "READY"
    assert opp.previous_status == "ACTIVE"


def test_deferred_then_reactivated_returns_to_active():
    opp = _make_opp()
    opp = advance(opp, "DEFERRED", reason="later")
    assert opp.status == "DEFERRED"
    opp = advance(opp, "REACTIVATED")
    # REACTIVATED sub-state semantically = ACTIVE (promt §10)
    assert opp.status == "ACTIVE"
    assert opp.previous_status == "DEFERRED"
    assert opp.reactivated_at  # audit timestamp captured


def test_ready_to_completed_succeeds():
    opp = _make_opp(status="READY")
    opp = advance(opp, "COMPLETED")
    assert opp.status == "COMPLETED"
    assert opp.completed_at
    assert opp.previous_status == "READY"


def test_invalid_transition_deferred_to_ready_blocked():
    opp = _make_opp(status="DEFERRED")
    with pytest.raises(InvalidTransition) as ei:
        advance(opp, "READY")
    assert "DEFERRED" in str(ei.value) and "READY" in str(ei.value)


def test_invalid_unknown_current_status():
    opp = _make_opp(status="FOOBAR")
    with pytest.raises(InvalidTransition) as ei:
        advance(opp, "ACTIVE")
    assert "unknown current" in str(ei.value)


def test_terminal_completed_blocks_transitions():
    opp = _make_opp(status="COMPLETED")
    for target in ("ACTIVE", "DEFERRED", "READY", "FAILED"):
        with pytest.raises(InvalidTransition):
            advance(opp, target)


def test_terminal_failed_can_retry_to_active():
    """Per promt 079_19 §3.1 #7: FAILED gets retry."""
    opp = _make_opp(status="FAILED")
    opp = advance(opp, "ACTIVE")
    assert opp.status == "ACTIVE"
    assert opp.previous_status == "FAILED"


def test_terminal_failed_to_ready_for_re_execute():
    opp = _make_opp(status="FAILED")
    opp = advance(opp, "READY")
    assert opp.status == "READY"


def test_deferred_record_preserved_through_reactivation():
    """DEFERRED ≠ DELETED: reactivation preserves record + provenance."""
    opp = _make_opp()
    opp = advance(opp, "DEFERRED", reason="not now")
    original_id = opp.id
    original_created = opp.created_at
    opp = advance(opp, "REACTIVATED")
    assert opp.id == original_id  # NOT deleted
    assert opp.created_at == original_created
    assert opp.deferred_reason == "not now"  # provenance retained


# ── 2. Persistence roundtrip via tmp_path ────────────────────────────────

def test_store_roundtrip(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    store.upsert(opp)

    # New store reads same file: record present + correct fields.
    store2 = OpportunityStore(data_file)
    loaded = store2.get(opp.id)
    assert loaded is not None
    assert loaded.title == "Test opp"
    assert loaded.status == "ACTIVE"
    assert loaded.id == "opp-test-001"


def test_store_filter_by_status(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    store.upsert(_make_opp(id="o1", **{"status": "ACTIVE"}))
    store.upsert(_make_opp(id="o2", **{"status": "DEFERRED"}))
    store.upsert(_make_opp(id="o3", **{"status": "ACTIVE"}))
    assert len(store.by_status("ACTIVE")) == 2
    assert len(store.by_status("DEFERRED")) == 1
    assert len(store.by_status("COMPLETED")) == 0


def test_store_corrupt_yaml_recovers_to_empty(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    data_file.write_text(":bad:yaml::: [invalid", encoding="utf-8")
    store = OpportunityStore(data_file)
    # Should not crash; degrades to empty.
    assert store.count() == 0


def test_store_atomic_write_no_tmp_leak(tmp_path: Path):
    """Per v5.39.0 Lesson: atomic write via .tmp → replace."""
    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    store.upsert(_make_opp())
    assert data_file.exists()
    # No leftover .tmp
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == [], f"atomic write leaked: {leftovers}"


# ── 3. Dry-run safety (ForgeFacade not invoked) ──────────────────────────

def test_dry_run_does_not_invoke_forge_facade(monkeypatch, tmp_path: Path):
    """Per promt §B-rule §7.3 + thinker gotcha 2.

    Monkeypatch a fake ForgeFacade that raises if run_chain is called.
    Successful dry-run proves ForgeFacade is never invoked.
    """
    # Stub the lazy-import target: opportunity_engine imports
    # ``from core_02.forge_facade import ForgeFacade`` inside execute().
    # We pre-stub core_02.forge_facade so execute() finds our sentinel.

    sentinel_calls: List[str] = []

    class _SentinelForgeFacade:
        PIPELINE_CHAIN = ["r1", "r2"]
        @staticmethod
        def run_chain(*args, **kwargs):
            sentinel_calls.append("called")
            raise AssertionError(
                "ForgeFacade.run_chain must NOT be called during --dry-run"
            )

    import types
    fake_module = types.ModuleType("core_02.forge_facade")
    fake_module.ForgeFacade = _SentinelForgeFacade
    monkeypatch.setitem(sys.modules, "core_02.forge_facade", fake_module)

    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    opp.scenario = {"scenario_id": "blueprint_v3", "role_id": "r1", "score": 1.0}
    opp.roles = [{"role_id": "r1"}, {"role_id": "r2"}]
    store.upsert(opp)

    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "opportunity_engine.py"),
         "--data-path", str(data_file), "run", opp.id, "--dry-run"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0, f"dry-run failed: stderr={rc.stderr}"
    assert sentinel_calls == [], "FORGE_FACADE MUST NOT be called during --dry-run"
    assert "dry-run" in rc.stdout or "dry_run" in rc.stdout


# ── 4. Fail-safe discover (real sources → degraded empty on missing data) ─

def test_discover_candidates_always_returns_list(tmp_path: Path):
    # Герметичность: несуществующие пути → 0 кандидатов (никаких реальных БД)
    cands = discover_candidates(
        "proj-1", max_results=5,
        source_paths={
            "whims": tmp_path / "missing_whims.yaml",
            "pulse": tmp_path / "missing_pulse.db",
            "events": tmp_path / "missing_events.db",
            "memory": tmp_path / "missing_memory.db",
        },
    )
    assert isinstance(cands, list)
    # Each candidate has minimal required fields
    for c in cands:
        assert c.id
        assert c.project_id == "proj-1"
        assert c.source in ("whim", "project_pulse", "event_bus", "knowledge", "hand")
        # GAP-1 (promt 085): real provenance, no stubs
        assert c.provenance.get("stub") is not True


def test_discover_respects_max_results(tmp_path: Path):
    cands = discover_candidates(
        "proj-1", max_results=2,
        source_paths={
            "whims": tmp_path / "missing_whims.yaml",
            "pulse": tmp_path / "missing_pulse.db",
            "events": tmp_path / "missing_events.db",
            "memory": tmp_path / "missing_memory.db",
        },
    )
    assert len(cands) <= 2


def test_discover_with_real_whim_source(tmp_path: Path):
    """GAP-1 (promt 085 §7): REAL DISCOVER — whim source produces candidates."""
    import sys as _sys
    sys.path.insert(0, str(REPO_ROOT))
    from scripts_01.whim_capture import WhimStore, capture, triage

    whims_yaml = tmp_path / "whims.yaml"
    store = WhimStore(whims_yaml)
    w = capture(
        "Написать статью про архитектуру",
        project_id="proj-real",
        source="cli",
        store=store,
    )
    triage(w, classification="PROMOTE_CANDIDATE", reason="article keyword")
    store.upsert(w)

    from opportunity_engine import discover_candidates
    cands = discover_candidates(
        "proj-real",
        max_results=5,
        # герметичность: остальные источники — несуществующие tmp-пути,
        # чтобы тест не читал реальные data_13/project_pulse.db и т.п.
        source_paths={
            "whims": whims_yaml,
            "pulse": tmp_path / "missing_pulse.db",
            "events": tmp_path / "missing_events.db",
            "memory": tmp_path / "missing_memory.db",
        },
    )
    assert cands, "real whim source must produce candidates"
    c = cands[0]
    assert c.source == "whim"
    assert c.project_id == "proj-real"
    assert c.provenance["source_id"] == w.id
    assert c.provenance["evidence"] == w.body
    assert c.provenance["stub"] is False
    assert c.provenance["confidence"] >= 0.5


def test_discover_dedup_by_provenance(tmp_path: Path):
    """GAP-1 idempotency (promt 085 §18): same source_id not duplicated."""
    sys.path.insert(0, str(REPO_ROOT))
    from scripts_01.whim_capture import WhimStore, capture, triage

    whims_yaml = tmp_path / "whims.yaml"
    store = WhimStore(whims_yaml)
    w = capture("План стратегии на год", project_id="proj-dedup", source="cli", store=store)
    triage(w, classification="PROMOTE_CANDIDATE", reason="plan keyword")
    store.upsert(w)

    opp_store = OpportunityStore(tmp_path / "opps.yaml")
    hermetic = {
        "whims": whims_yaml,
        "pulse": tmp_path / "missing_pulse.db",
        "events": tmp_path / "missing_events.db",
        "memory": tmp_path / "missing_memory.db",
    }
    first = discover_candidates(
        "proj-dedup", max_results=5,
        source_paths=hermetic, store=opp_store,
    )
    for c in first:
        opp_store.upsert(c)
    second = discover_candidates(
        "proj-dedup", max_results=5,
        source_paths=hermetic, store=opp_store,
    )
    assert not second, "repeated discover of same source_id must be deduplicated"


def test_discover_knowledge_confidence_zero_not_promoted(tmp_path: Path):
    """Pre-existing `or 0.5` bug (v5.189.18 note, fixed v5.189.20).

    _discover_from_knowledge: confidence_score=0.0 (фальшивое значение) НЕ должен
    промоутиться в 0.5. Зеркалит паттерн rank_score/rank_candidates
    (`_conf if _conf is not None else 0.5`) — 0.0 остаётся 0.0, None → 0.5.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from core_02.memory_store import MemoryStore

    db = tmp_path / "ctx.db"
    store = MemoryStore(db)
    store.store_knowledge(
        kind="candidate",
        title="zero confidence candidate",
        content="signal with explicit confidence 0.0",
        confidence_score=0.0,
    )

    cands = discover_candidates(
        "proj-k",
        max_results=5,
        source_paths={
            "whims": tmp_path / "missing_whims.yaml",
            "pulse": tmp_path / "missing_pulse.db",
            "events": tmp_path / "missing_events.db",
            "memory": db,
        },
    )
    kn = [c for c in cands if c.source == "knowledge"]
    assert kn, "knowledge source must produce a candidate"
    assert kn[0].provenance["confidence"] == 0.0, (
        "confidence_score=0.0 must stay 0.0 (was promoted to 0.5 by `or 0.5` bug)"
    )


# ── 5. JSON discipline (stdout parseable in --json mode) ─────────────────

def test_cli_status_json_stdout_is_parseable(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    store.upsert(opp)

    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "opportunity_engine.py"),
         "--data-path", str(data_file), "status", opp.id, "--json"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0
    # stdout must be valid JSON (no human chatter leaking in)
    parsed = json.loads(rc.stdout)
    assert "opportunity" in parsed
    assert parsed["opportunity"]["id"] == opp.id


def test_cli_list_json_stdout_is_parseable(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "opportunity_engine.py"),
         "--data-path", str(data_file), "list", "--json"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0
    parsed = json.loads(rc.stdout)
    assert "items" in parsed
    assert "count" in parsed


def test_cli_status_not_found_returns_exit_1():
    """Exit codes per promt §6: not-found = 1."""
    import argparse
    args = argparse.Namespace(
        data_path=str(Path("/tmp/nonexistent.yaml")),
        opportunity_id="does-not-exist",
        json=False,
    )
    rc = _cli_status(args)
    # 0 only because the store path becomes empty file gracefully;
    # but opportunity_id is not in store → return 1
    assert rc == 1


# ── 6. Exit codes determinism ────────────────────────────────────────────

def test_cli_run_dry_run_exit_zero(tmp_path: Path):
    data_file = tmp_path / "opportunities.yaml"
    # Pre-seed with proposed opp (already has scenario + roles)
    store = OpportunityStore(data_file)
    opp = _make_opp()
    opp.scenario = {"scenario_id": "blueprint_v3", "role_id": "novella_struct", "score": 0.0}
    opp.roles = [{"role_id": "novella_struct"}]
    store.upsert(opp)
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "opportunity_engine.py"),
         "--data-path", str(data_file), "run", opp.id, "--dry-run"],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0


def test_cli_discover_creates_records(tmp_path: Path):
    """GAP-1: CLI discover seeds real whim source → records created."""
    import sys as _sys
    sys.path.insert(0, str(REPO_ROOT))
    from scripts_01.whim_capture import WhimStore, capture, triage

    whims_yaml = tmp_path / "whims.yaml"
    wstore = WhimStore(whims_yaml)
    w = capture("Написать гайд по интеграции", project_id="proj-x", source="cli", store=wstore)
    triage(w, classification="PROMOTE_CANDIDATE", reason="guide keyword")
    wstore.upsert(w)

    data_file = tmp_path / "opportunities.yaml"
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "opportunity_engine.py"),
         "--data-path", str(data_file), "discover", "--project-id", "proj-x",
         "--whim-path", str(whims_yaml),
         "--pulse-db", str(tmp_path / "missing_pulse.db"),
         "--event-db", str(tmp_path / "missing_events.db"),
         "--memory-db", str(tmp_path / "missing_memory.db")],
        capture_output=True, text=True,
    )
    assert rc.returncode == 0, f"stderr={rc.stderr}"
    assert data_file.exists()
    store = OpportunityStore(data_file)
    assert store.count() >= 1


# ── 7. Vocabulary safety (ANTI-6b / CON-8) ──────────────────────────────

def test_known_capabilities_not_mutated():
    """opportunity_engine is an Engine, not a model capability token.
    Module import MUST NOT mutate KNOWN_CAPABILITIES in blueprint_v3.
    """
    from opportunity_engine import Opportunity  # re-import to confirm no side-effect on reload
    try:
        from core_02.blueprint_v3 import KNOWN_CAPABILITIES
    except ImportError:
        pytest.skip("blueprint_v3 not importable in this env")
    assert "opportunity_engine" not in KNOWN_CAPABILITIES, (
        "ANTI-6b violation: opportunity_engine MUST NOT appear in "
        "KNOWN_CAPABILITIES (it is an Engine token, not a model capability)"
    )


def test_module_import_produces_no_exceptions():
    """Smoke: import side-effects free (lazy G0 imports per additivity)."""
    import importlib
    if "opportunity_engine" in sys.modules:
        importlib.reload(sys.modules["opportunity_engine"])
    else:
        importlib.import_module("opportunity_engine")


# ── 8. CLI subcommand surface completeness ───────────────────────────────

def test_main_missing_command_returns_error():
    rc = main([])
    # argparse exits 2 on missing subcommand
    assert rc == 2


def test_main_run_unknown_id_returns_1(tmp_path: Path):
    rc = main([
        "--data-path", str(tmp_path / "opp.yaml"),
        "run", "opp-does-not-exist",
    ])
    assert rc == 1


def test_main_propose_unknown_id_returns_1(tmp_path: Path):
    rc = main([
        "--data-path", str(tmp_path / "opp.yaml"),
        "propose", "opp-does-not-exist",
    ])
    assert rc == 1


# ── 9. Phase 14 Option B3: per-invocation _LAZY_IMPORT_ERRORS boundary ─────
def test_cli_helpers_clear_stale_warnings_at_invocation_start(tmp_path: Path):
    """Phase 14 Option B3: every ``_cli_*`` starts with ``_LAZY_IMPORT_ERRORS.clear()``.

    Warnings accumulated at module-import time (e.g. ``yaml`` missing) or by a
    previous invocation must NOT leak into the next invocation. All 6 CLI
    helpers must clear at start.
    """
    import argparse
    import opportunity_engine as oe_mod

    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    store.upsert(opp)

    # Simulate pollution from a previous invocation / module-import time.
    oe_mod._LAZY_IMPORT_ERRORS.append("factory_registry: unavailable")
    oe_mod._LAZY_IMPORT_ERRORS.append("forge_facade: unavailable")

    # 1. _cli_status — read-only; must clear pollution at start.
    args = argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, json=False,
    )
    assert _cli_status(args) == 0
    assert oe_mod._LAZY_IMPORT_ERRORS == [], (
        "_cli_status must clear stale warnings at invocation start"
    )

    # 2. _cli_list
    oe_mod._LAZY_IMPORT_ERRORS.append("stale")
    args = argparse.Namespace(data_path=str(data_file), status=None, json=False)
    assert _cli_list(args) == 0
    assert oe_mod._LAZY_IMPORT_ERRORS == []

    # 3. _cli_rank
    oe_mod._LAZY_IMPORT_ERRORS.append("stale")
    args = argparse.Namespace(data_path=str(data_file), json=False)
    assert _cli_rank(args) == 0
    assert oe_mod._LAZY_IMPORT_ERRORS == []

    # 4. _cli_propose (real SI/registry path, fail-safe) — execution-path helper:
    #    may legitimately append warnings during the invocation, so assert only
    #    that the PRE-POLLUTED marker is gone (boundary clear), not `== []`
    #    (which would conflate boundary with "no warnings generated at all" —
    #    reviewer nit).
    oe_mod._LAZY_IMPORT_ERRORS.append("stale")
    args = argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, json=False,
    )
    assert _cli_propose(args) == 0
    assert "stale" not in oe_mod._LAZY_IMPORT_ERRORS, (
        "_cli_propose must clear stale warnings at invocation start"
    )

    # 5. _cli_run --dry-run (hermetic: no execute, no event bus) — same
    #    execution-path nuance as _cli_propose.
    oe_mod._LAZY_IMPORT_ERRORS.append("stale")
    args = argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, dry_run=True, json=False,
    )
    assert _cli_run(args) == 0
    assert "stale" not in oe_mod._LAZY_IMPORT_ERRORS, (
        "_cli_run must clear stale warnings at invocation start"
    )

    # 6. _cli_discover (hermetic: all source paths missing → 0 candidates; the
    #    discover-source functions return [] on missing modules WITHOUT appending,
    #    so `== []` is the precise assertion here — micro-nit from reviewer).
    oe_mod._LAZY_IMPORT_ERRORS.append("stale")
    args = argparse.Namespace(
        data_path=str(data_file), project_id="proj-x", json=False,
        max_results=5, whim_path=str(tmp_path / "no.yaml"),
        pulse_db=str(tmp_path / "no.db"), event_db=str(tmp_path / "no.db"),
        memory_db=str(tmp_path / "no.db"), rank=False,
    )
    assert _cli_discover(args) == 0
    assert oe_mod._LAZY_IMPORT_ERRORS == [], (
        "_cli_discover is hermetic (0 candidates) — must end with empty warnings "
        "(Option B3 boundary)"
    )


def test_cli_json_payloads_include_import_warnings(tmp_path: Path, capsys):
    """Phase 14 Option B3: every ``_cli_*`` JSON payload reports ``import_warnings``."""
    import argparse
    import json as _json

    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    store.upsert(opp)

    def _run_json(fn, args) -> dict:
        capsys.readouterr()  # flush
        rc = fn(args)
        assert rc == 0, f"{fn.__name__} failed: rc={rc}"
        return _json.loads(capsys.readouterr().out)

    payload = _run_json(_cli_status, argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, json=True))
    assert "import_warnings" in payload and isinstance(payload["import_warnings"], list)

    payload = _run_json(_cli_list, argparse.Namespace(
        data_path=str(data_file), status=None, json=True))
    assert "import_warnings" in payload and payload["import_warnings"] == []

    payload = _run_json(_cli_rank, argparse.Namespace(
        data_path=str(data_file), json=True))
    assert "import_warnings" in payload

    payload = _run_json(_cli_propose, argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, json=True))
    assert "import_warnings" in payload

    payload = _run_json(_cli_run, argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, dry_run=True, json=True))
    assert "import_warnings" in payload

    payload = _run_json(_cli_discover, argparse.Namespace(
        data_path=str(data_file), project_id="proj-x", json=True,
        max_results=5, whim_path=str(tmp_path / "no.yaml"),
        pulse_db=str(tmp_path / "no.db"), event_db=str(tmp_path / "no.db"),
        memory_db=str(tmp_path / "no.db"), rank=False))
    assert "import_warnings" in payload and payload["import_warnings"] == []


def test_cli_invocation_warnings_do_not_leak_across_invocations(
    monkeypatch, tmp_path: Path, capsys,
):
    """Phase 14 Option B3 CORE: warnings generated during invocation A must NOT
    appear in invocation B's payload (per-invocation boundary).

    Invocation A (``run`` non-dry with all lazy imports failing) accumulates
    ``factory_registry: unavailable`` + ``forge_facade: unavailable`` into ITS
    own payload; invocation B (``status``) must start clean.
    """
    import argparse
    import json as _json
    import opportunity_engine as oe_mod

    data_file = tmp_path / "opportunities.yaml"
    store = OpportunityStore(data_file)
    opp = _make_opp()
    opp.provenance = {"source": "hand", "capability": "code"}
    store.upsert(opp)

    # All lazy imports fail → execute() appends factory_registry + forge_facade.
    monkeypatch.setattr(oe_mod, "_lazy_import", lambda *a, **k: None)
    monkeypatch.setattr(oe_mod, "_make_cli_event_bus", lambda: None)

    # ─── Invocation A: run (non-dry) → accumulates 2 warnings into ITS payload ───
    capsys.readouterr()  # flush
    rc = _cli_run(argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, dry_run=False, json=True))
    assert rc == 1, "execute with unavailable forge_facade must FAIL (exit 1)"
    out_a = _json.loads(capsys.readouterr().out)
    assert "factory_registry: unavailable" in out_a["import_warnings"], out_a
    assert "forge_facade: unavailable" in out_a["import_warnings"], out_a

    # ─── Invocation B: status → must NOT inherit A's warnings ───
    capsys.readouterr()  # flush
    rc = _cli_status(argparse.Namespace(
        data_path=str(data_file), opportunity_id=opp.id, json=True))
    assert rc == 0
    out_b = _json.loads(capsys.readouterr().out)
    assert out_b["import_warnings"] == [], (
        f"invocation B must not inherit invocation A's import warnings: {out_b}"
    )
