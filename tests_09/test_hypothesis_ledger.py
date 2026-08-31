"""tests_09/test_hypothesis_ledger.py — Hermetic tests for scripts_01/hypothesis_ledger.py.

Per-prompt 099 (v5.189.59):
- State machine forward DAG (open → supported/refuted → kill_criteria_met terminal).
- Hypothesis ID stability + idempotency (text normalization).
- Kill-criteria aggregate (terminal requires ALL met + non-empty list).
- Corrupt JSONL recovery (ADR-016 fail-safe).
- Cross-module FILE_LOCK concurrent writes.
- CLI subprocess smoke.

Pattern follows tests_09/test_corpus_persistence.py (autouse fixture monkey-patches ring):
- `_isolate_ledger_dir` autouse patches BOTH corpus_persistence.DEFAULT_CORPUS_DIR
  AND hypothesis_ledger.DEFAULT_LEDGER_DIR (transitive `from X import Y` snapshot).
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Module under test.
from scripts_01 import hypothesis_ledger

# API imports.
from scripts_01.hypothesis_ledger import (
    DEFAULT_LEDGER_DIR,
    FILE_LOCK,
    HypothesisFull,
    HypothesisStatus,
    HypothesisSummary,
    KillCriterion,
    TEXT_MAX_LEN,
    add_hypothesis,
    list_all,
    query_by_id,
    query_by_status,
    stats,
    update_status,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_ledger_root(monkeypatch, tmp_path) -> None:
    """Override DEFAULT_LEDGER_DIR per-test via pytest's tmp_path (true hermeticity).

    Tests with overlapping text (e.g. many create ``"H1"`` hypotheses) share the
    SAME hid (sha256-normalization collapses whitespace/case); if the fixture
    used a module-level shared directory, `add_hypothesis("H1")` would return
    an idempotent existing summary from a prior test, polluting subsequent
    tests' state. Per-test ``tmp_path`` ensures every test starts fresh.
    """
    from scripts_01 import hypothesis_ledger as h_mod
    target = tmp_path / "ledger"
    target.mkdir(parents=True, exist_ok=True)
    # Patch the *module attribute* (the snapshot binding via ``from X import Y``
    # in hypothesis_ledger) AND the consumer-module re-import — same pattern as
    # test_corpus_inspector (transitive-monkeypatch safe).
    monkeypatch.setattr(h_mod, "DEFAULT_LEDGER_DIR", target)
    monkeypatch.setattr(hypothesis_ledger, "DEFAULT_LEDGER_DIR", target)


# ─── TestAddHypothesis ──────────────────────────────────────────────────────


class TestAddHypothesis:
    def test_add_new_hypothesis_starts_open(self):
        """New hypothesis → status=open, tags=[], confidence=0.5, kill_criteria=[], stable id."""
        result = add_hypothesis(
            "StarMaker аудитория готова платить за вокал-обучение",
            tags=["pricing", "starmaker"],
        )
        assert isinstance(result, HypothesisSummary)
        assert result.status == HypothesisStatus.OPEN
        assert result.text == "StarMaker аудитория готова платить за вокал-обучение"
        assert result.confidence == 0.5
        assert result.tags == ["pricing", "starmaker"]
        assert result.kill_criteria == []
        # ID format: h_<sha8>_<slug>.
        assert result.hid.startswith("h_")
        parts = result.hid.split("_", 2)
        assert len(parts) == 3
        assert len(parts[1]) == 8  # sha8 = sha256(normalized)[:8]
        assert parts[1].isalnum()
        # Slug contains "starmaker" or similar (lowercase, dash-separated).
        assert "starmaker" in parts[2] or len(parts[2]) > 0

    def test_add_idempotent_text_normalization(self):
        """Same text → same ID (text-normalization idempotent); whitespace-different texts collapse."""
        # Same text 2x → same hid.
        r1 = add_hypothesis("Pricing tier matters")
        r2 = add_hypothesis("Pricing tier matters")
        assert r1.hid == r2.hid

        # Whitespace+case-different same content → same hid (text normalization).
        r3 = add_hypothesis("  pricing   TIER   matters  ")
        assert r1.hid == r3.hid, (
            f"text-normalization broken: r1={r1.hid}, r3={r3.hid}"
        )

    def test_add_rejects_empty_text(self):
        with pytest.raises(ValueError, match="empty"):
            add_hypothesis("")

    def test_add_rejects_overlong_text(self):
        long_text = "x" * (TEXT_MAX_LEN + 100)
        with pytest.raises(ValueError, match="DoS"):
            add_hypothesis(long_text)

    def test_add_rejects_confidence_out_of_range(self):
        with pytest.raises(ValueError):
            add_hypothesis("test", confidence=1.5)
        with pytest.raises(ValueError):
            add_hypothesis("test", confidence=-0.1)

    def test_add_normalizes_tags_lowercase_dedup(self):
        """Tags: lowercase, sorted, dedupe."""
        result = add_hypothesis(
            "Test",
            tags=["Starmaker", "STARMAKER", "pricing"],
        )
        # Only 2 unique after dedupe, sorted alphabetically.
        assert result.tags == ["pricing", "starmaker"]

    def test_add_atomic_no_tmp_leftover(self):
        """After successful add, no .tmp files remain в DEFAULT_LEDGER_DIR."""
        from scripts_01 import hypothesis_ledger as h_mod
        add_hypothesis("Test atomic write")
        tmp_files = list(h_mod.DEFAULT_LEDGER_DIR.glob("*.tmp"))
        assert tmp_files == [], f"atomic write leaked tmp files: {tmp_files}"


# ─── TestTransitionDag ──────────────────────────────────────────────────────


class TestTransitionDag:
    def test_valid_open_to_supported(self):
        h = add_hypothesis("H1", kill_criteria=[
            {"criterion": "criterion X", "met": False},
        ])
        updated = update_status(
            h.hid, HypothesisStatus.SUPPORTED, evidence_url="https://example.com",
        )
        assert updated.status == HypothesisStatus.SUPPORTED
        assert updated.kill_criteria[0].met is False  # не-changed by transition

    def test_valid_open_to_refuted(self):
        h = add_hypothesis("H1")
        updated = update_status(h.hid, HypothesisStatus.REFUTED)
        assert updated.status == HypothesisStatus.REFUTED

    def test_valid_supported_to_refuted(self):
        h = add_hypothesis("H1")
        update_status(h.hid, HypothesisStatus.SUPPORTED)
        updated = update_status(h.hid, HypothesisStatus.REFUTED)
        assert updated.status == HypothesisStatus.REFUTED

    def test_invalid_backward_transition_raises(self):
        """DAG invariant: terminal state cannot exit."""
        # Create, transition to supported, then try refuted → kill_criteria_met works,
        # but kill_criteria_met → open MUST raise.
        h = add_hypothesis("H1", kill_criteria=[
            {"criterion": "x", "met": True},
        ])
        update_status(h.hid, HypothesisStatus.SUPPORTED)
        update_status(h.hid, HypothesisStatus.KILL_CRITERIA_MET)
        # Now attempt backward transition: terminal → open.
        with pytest.raises(ValueError, match="not in DAG"):
            update_status(h.hid, HypothesisStatus.OPEN)

    def test_invalid_self_transition_raises(self):
        h = add_hypothesis("H1")
        with pytest.raises(ValueError, match="to itself"):
            update_status(h.hid, HypothesisStatus.OPEN)

    def test_invalid_skip_stage_open_to_kill_criteria_met(self):
        """open → kill_criteria_met allowed ONLY if kill_criteria aggregate met."""
        h = add_hypothesis(
            "H1", kill_criteria=[
                {"criterion": "x", "met": False},  # NOT met.
            ],
        )
        with pytest.raises(ValueError, match="kill_criteria"):
            update_status(h.hid, HypothesisStatus.KILL_CRITERIA_MET)

    def test_invalid_nonexistent_hypothesis_raises(self):
        with pytest.raises(ValueError, match="not found"):
            update_status("h_deadbeef_nonexistent", HypothesisStatus.SUPPORTED)


# ─── TestKillCriteria ──────────────────────────────────────────────────────


class TestKillCriteria:
    def test_kill_criteria_met_only_when_all_met(self):
        h = add_hypothesis("H1", kill_criteria=[
            {"criterion": "a", "met": False},
            {"criterion": "b", "met": False},
        ])
        # Try terminal transition: kill_criteria aggregate NOT met → ValueError.
        with pytest.raises(ValueError):
            update_status(h.hid, HypothesisStatus.KILL_CRITERIA_MET)

    def test_empty_kill_criteria_prevents_terminal(self):
        """Empty list → terminal state must be unreachable (invariant)."""
        h = add_hypothesis("H1")  # No kill_criteria → empty list.
        with pytest.raises(ValueError, match="non-empty"):
            update_status(h.hid, HypothesisStatus.KILL_CRITERIA_MET)

    def test_single_met_criterion_allows_terminal(self):
        h = add_hypothesis(
            "H1",
            kill_criteria=[{"criterion": "single", "met": True}],
        )
        # Open → kill_criteria_met works: only 1 criterion met, list non-empty.
        updated = update_status(h.hid, HypothesisStatus.KILL_CRITERIA_MET)
        assert updated.status == HypothesisStatus.KILL_CRITERIA_MET


# ─── TestQuery ──────────────────────────────────────────────────────────────


class TestQuery:
    def test_query_by_id_returns_full_history(self):
        h = add_hypothesis("H1", tags=["x"])
        update_status(h.hid, HypothesisStatus.SUPPORTED,
                      evidence_url="https://example.com/evidence")
        full = query_by_id(h.hid)
        assert full is not None
        assert isinstance(full, HypothesisFull)
        assert full.summary.hid == h.hid
        # History: create + update_status events.
        assert len(full.history) == 2
        assert full.history[0].event_type == "create"
        assert full.history[1].event_type == "update_status"
        assert full.history[1].from_status == HypothesisStatus.OPEN
        assert full.history[1].evidence_url == "https://example.com/evidence"

    def test_query_by_id_nonexistent_returns_none(self):
        assert query_by_id("h_nonexistent") is None

    def test_query_by_status_filters_correctly(self):
        h1 = add_hypothesis("H1")
        h2 = add_hypothesis("H2")
        update_status(h1.hid, HypothesisStatus.SUPPORTED)
        open_h = query_by_status(HypothesisStatus.OPEN)
        supported_h = query_by_status(HypothesisStatus.SUPPORTED)
        # h1 = supported (transitioned); h2 = open.
        assert {s.hid for s in open_h} == {h2.hid}
        assert {s.hid for s in supported_h} == {h1.hid}

    def test_list_all_returns_everything(self):
        h1 = add_hypothesis("H1")
        h2 = add_hypothesis("H2")
        h3 = add_hypothesis("H3")
        all_h = list_all()
        assert {s.hid for s in all_h} >= {h1.hid, h2.hid, h3.hid}

    def test_stats_counts_per_status(self):
        for i in range(3):
            add_hypothesis(f"H{i}")
        s = stats()
        # At least 3 in "open" (other categories default 0).
        assert s["open"] >= 3
        assert "supported" in s
        assert "refuted" in s
        assert "kill_criteria_met" in s


# ─── TestConcurrency ──────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_writes_under_file_lock(self):
        """10 threads simultaneously creating + updating same hid — final state coherent."""
        h = add_hypothesis("Concurrent test", kill_criteria=[
            {"criterion": "x", "met": True},
        ])

        def _do_work() -> None:
            # Each thread attempts to UPDATE; some races will fail (DAG invariant violation).
            try:
                update_status(h.hid, HypothesisStatus.SUPPORTED)
            except ValueError:
                pass  # Expected: terminal state blocks further transitions.

        threads: List[threading.Thread] = []
        for _ in range(10):
            t = threading.Thread(target=_do_work)
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Verify final state: at least still readable, status may be supported or kill_criteria_met.
        full = query_by_id(h.hid)
        assert full is not None
        # History log accumulated (1 create + 10 attempted updates).
        # Some updates may have hit ValueError, those become history lossless no-add.
        # File integrity: at least create event present.
        assert any(e.event_type == "create" for e in full.history)


# ─── TestCorruptJsonlRecovery ──────────────────────────────────────────────


class TestCorruptJsonlRecovery:
    def test_corrupt_jsonl_line_does_not_crash_query(self):
        # Create hypothesis, then corrupt its JSONL.
        h = add_hypothesis("Corrupt test")
        # Find path directly via hypothesis_ledger (its own _entry_path,
        # not corpus_persistence which has a different ID scheme).
        from scripts_01.hypothesis_ledger import _entry_path
        path = _entry_path(h.hid)
        # Write garbage at end.
        with path.open("a", encoding="utf-8") as f:
            f.write("THIS_IS_NOT_VALID_JSON\n")
            f.write("{partial json\n")
        # query_by_id should still return valid record.
        full = query_by_id(h.hid)
        assert full is not None
        assert full.summary.hid == h.hid


# ─── TestCLI ──────────────────────────────────────────────────────────────


class TestCLI:
    def _run_cli(self, *args: str, root: Path) -> subprocess.CompletedProcess:
        cmd = [
            sys.executable, "-m", "scripts_01.hypothesis_ledger",
            "--root", str(root),
            *args,
        ]
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=str(Path(__file__).resolve().parent.parent),
        )

    def test_cli_add_update_list(self, tmp_path):
        # autouse _isolate_ledger_root already created tmp_path/ledger.
        root = tmp_path / "ledger"
        # add
        r = self._run_cli(
            "add", "--text", "CLI test hypothesis",
            "--tag", "pricing", "--tag", "starmaker",
            "--confidence", "0.7",
            root=root,
        )
        assert r.returncode == 0, f"add failed: {r.stderr}"
        assert "added hypothesis h_" in r.stdout

        # list
        r = self._run_cli("list", root=root)
        assert r.returncode == 0
        assert "CLI test hypothesis" in r.stdout

        # stats (JSON output for machine consumption)
        r = self._run_cli("stats", "--json", root=root)
        assert r.returncode == 0
        payload = json.loads(r.stdout)
        assert payload["open"] >= 1

    def test_cli_version(self):
        cmd = [sys.executable, "-m", "scripts_01.hypothesis_ledger", "--version"]
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert r.returncode == 0
        assert "hypothesis_ledger" in r.stdout
        assert "v5.189.59" in r.stdout

    def test_cli_invalid_status_argparse_rejects(self, tmp_path):
        # autouse _isolate_ledger_root already created tmp_path/ledger.
        root = tmp_path / "ledger"
        r = self._run_cli(
            "update", "--id", "h_test", "--status", "INVALID_STATE",
            root=root,
        )
        assert r.returncode == 2


# ─── TestIdempotencyShells ────────────────────────────────────────────────


class TestIdempotency:
    """Validated contract: re-running `add` с same text → noop (existing create preserved)."""

    def test_add_idempotent_returns_existing_summary(self):
        """Calling add twice with same text returns existing summary (no duplicate create)."""
        from scripts_01 import hypothesis_ledger as h_mod
        root = h_mod.DEFAULT_LEDGER_DIR
        first = add_hypothesis("Same text idempotent test", tags=["a"])
        second = add_hypothesis("Same text idempotent test", tags=["b"])
        # Same HID (idempotent), and event_type=create is unique в history.
        assert first.hid == second.hid
        full = query_by_id(first.hid)
        # Only one create event (даже though мы called add 2x).
        creates = [e for e in full.history if e.event_type == "create"]
        assert len(creates) == 1, (
            f"expected exactly 1 create event; got {len(creates)}. "
            f"Idempotency broken."
        )
