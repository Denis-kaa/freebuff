"""tests_09/test_devil_advocate_pass_integration.py — v5.189.66 integration tests.

Hermetic integration tests validating that `devil_advocate_pass` is the FIRST
ACTIVE consumer of `hypothesis_ledger`: registers counter-candidates BEFORE
refuting the original, with ADR-016 fail-safe semantics preserved throughout.

Pattern: isolated_ledger fixture monkeypatches hypothesis_ledger.DEFAULT_LEDGER_DIR
to a tmp_path so tests are hermetic (parallel-safe + isolated from prod data).
"""

from __future__ import annotations

import pytest

from scripts_01.hypothesis_ledger import (
    HypothesisStatus,
    add_hypothesis,
    query_by_status,
    update_status,
)
from scripts_01.devil_advocate_pass import (
    DevilAdvocateReport,
    Strategy,
    devil_advocate_pass,
)


# ─── fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_ledger(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Override hypothesis_ledger DEFAULT_LEDGER_DIR to tmp_path."""
    from scripts_01 import hypothesis_ledger

    ledger_dir = tmp_path / "hypothesis_ledger"
    monkeypatch.setattr(hypothesis_ledger, "DEFAULT_LEDGER_DIR", ledger_dir)
    yield ledger_dir


# ─── helpers (test-local; mirror `test_hypothesis_ledger.py` pattern) ─────


def _seed_open_hypothesis(text: str = "StarMaker pricing tier matters", *, tags=None) -> str:
    """Seed an OPEN hypothesis. Returns hid."""
    summary = add_hypothesis(text, tags=tags or ["pricing", "starmaker"], confidence=0.6)
    return summary.hid


def _seed_refuted_hypothesis(text: str = "Already refuted claim") -> str:
    """Seed a hypothesis REFUTED in two-step (open then refute)."""
    summary = add_hypothesis(text, tags=["legacy"], confidence=0.5)
    update_status(summary.hid, HypothesisStatus.REFUTED)
    return summary.hid


# ─── tests ────────────────────────────────────────────────────────────────


class TestActiveRefutationLoop:
    """The INVARIANT: devil_advocate_pass registers candidates BEFORE refuting."""

    def test_devil_advocate_pass_registers_3_new_candidates_then_refutes(
        self, isolated_ledger,
    ) -> None:
        """OPEN HYP_A → 3 NEW candidates (inherit parent tags) → HYP_A → REFUTED.

        Order invariant: candidates exist BEFORE refutation (query_by_status
        must surface both new OPEN + REFUTED in the post-pass state).
        """
        hid_a = _seed_open_hypothesis(
            "StarMaker pricing tier matters",
            tags=["pricing", "starmaker"],
        )

        # Get the HypothesisSummary back from the ledger.
        a_summary = next(s for s in query_by_status(HypothesisStatus.OPEN) if s.hid == hid_a)

        report: DevilAdvocateReport = devil_advocate_pass(a_summary)

        # ── 1. Pass finished cleanly with refuted=True.
        assert report.refuted is True, (
            f"devil_advocate_pass should refute the original; warnings={report.warnings}"
        )
        assert report.original_hid == hid_a
        assert isinstance(report.strategy, str)
        assert report.strategy == "3-kill-questions"

        # ── 2. Exactly 3 new candidates registered (inversion+boundary+steel-man).
        assert report.iteration_count == 3, (
            f"expected 3 candidates (3-kill-questions); got {report.iteration_count}"
        )
        assert len(report.new_candidates) == 3

        # ── 3. Each candidate has parent-tag inheritance (cross-pollination).
        for c in report.new_candidates:
            assert set(c.tags or []) >= {"pricing", "starmaker"}, (
                f"candidate {c.hid} missing parent tags: {c.tags}"
            )

        # ── 4. Ledger state — original REFUTED, 3 new candidates OPEN.
        open_candidates = [s for s in query_by_status(HypothesisStatus.OPEN) if s.hid != hid_a]
        refuted = query_by_status(HypothesisStatus.REFUTED)
        assert len(refuted) == 1
        assert refuted[0].hid == hid_a
        assert len(open_candidates) >= 3, (
            f"expected ≥3 new candidates in OPEN; got {len(open_candidates)}: "
            f"{[c.hid for c in open_candidates]}"
        )

    def test_devil_advocate_pass_text_heuristics_are_deterministic(
        self, isolated_ledger,
    ) -> None:
        """Three heuristics — invert / boundary / steel-man — produce distinct text.

        Catches accidental heuristic collapse (e.g., all 3 returning same prefix).
        """
        hid_a = _seed_open_hypothesis("Quality > price in edtech market")
        a_summary = next(s for s in query_by_status(HypothesisStatus.OPEN) if s.hid == hid_a)

        report = devil_advocate_pass(a_summary)
        assert report.iteration_count == 3

        texts = {c.text for c in report.new_candidates}
        assert len(texts) == 3, (
            f"3 heuristics should produce 3 distinct candidate texts; got {len(texts)}: {texts}"
        )
        # Heuristic signatures: "Counter" / "Edge case" / "Evidence-gap".
        joined = " | ".join(sorted(texts))
        assert "Counter" in joined or "is NOT" in joined, "missing INVERSION signature"
        assert "Edge case" in joined, "missing BOUNDARY signature"
        assert "Evidence-gap" in joined, "missing STEEL-MAN signature"

    def test_devil_advocate_pass_inherits_parent_kill_criteria(
        self, isolated_ledger,
    ) -> None:
        """Parent kill_criteria[:3] propagated to children."""
        parent_kc = [
            {"criterion": f"crit_{i}", "met": False, "evidence_url": f"https://x.test/{i}"}
            for i in range(3)
        ]
        summary = add_hypothesis(
            "Hypothesis with detailed kill criteria",
            tags=["test"],
            kill_criteria=parent_kc,
            confidence=0.6,
        )
        # Engine defensively normalizes parent.kill_criteria (list of KillCriterion dataclasses)
        # into dicts via _kc_to_dicts() before forwarding to hypothesis_ledger.add_hypothesis.
        report = devil_advocate_pass(summary)
        assert report.refuted is True
        assert report.iteration_count == 3
        # Each candidate inherits parent's first 3 kill criteria.
        for c in report.new_candidates:
            assert len(c.kill_criteria or []) == 3, (
                f"candidate should inherit 3 parent kill_criteria; got "
                f"{len(c.kill_criteria or [])} for {c.hid}"
            )

    def test_devil_advocate_pass_confidence_pessimism(
        self, isolated_ledger,
    ) -> None:
        """Counter-candidate confidence = 0.4 (adversarial pessimism)."""
        hid_a = _seed_open_hypothesis("Parent claim")
        a_summary = next(s for s in query_by_status(HypothesisStatus.OPEN) if s.hid == hid_a)

        report = devil_advocate_pass(a_summary)
        for c in report.new_candidates:
            assert c.confidence == pytest.approx(0.4, abs=1e-6), (
                f"counter-candidate confidence should be 0.4 (adversarial skepticism); "
                f"got {c.confidence} for {c.hid}"
            )


class TestADR016FailSafe:
    """ADR-016 fail-safe semantics: never raise, always return safe-state Report."""

    def test_devil_advocate_pass_lazy_import_fail_returns_empty_report(
        self, monkeypatch,
    ) -> None:
        """Simulate hypothesis_ledger unavailable → empty Report, no raise.

        Approach (v5.189.66 round-3): ``monkeypatch.setitem(sys.modules, name, None)``
        is the canonical Python idiom for forcing ``ModuleNotFoundError`` on the next
        ``from X import Y`` (set to ``None`` distinguishes from a fresh finder lookup).
        ADR-016 fail-safe catches at function-call time inside devil_advocate_pass.
        Pytest's ``monkeypatch`` restores sys.modules on teardown — no manual cleanup.
        """
        import sys as _sys
        import io as _io
        from dataclasses import dataclass as _dc

        # 1) Force the next import of ``scripts_01.hypothesis_ledger`` to fail.
        monkeypatch.setitem(_sys.modules, "scripts_01.hypothesis_ledger", None)

        @_dc
        class _Fake:
            hid: str = "h_test0000_fake"
            text: str = "fake hypothesis for lazy-import test"
            status: Any = HypothesisStatus.OPEN
            tags: tuple = ()
            kill_criteria: tuple = ()

        fake = _Fake()

        # 2) Capture stderr (devil_advocate_pass writes warning on ImportError).
        buf = _io.StringIO()
        monkeypatch.setattr(_sys, "stderr", buf)

        # 3) Call devil_advocate_pass; inside, the lazy ``from scripts_01.
        # hypothesis_ledger import ...`` raises ModuleNotFoundError, which the
        # ``except ImportError`` branch in the engine catches → empty Report.
        report = devil_advocate_pass(fake)

        assert report.refuted is False
        assert report.new_candidates == []
        assert report.iteration_count == 0
        assert any(("Import" in w) or ("ModuleNotFound" in w) for w in report.warnings), (
            f"warnings should mention Import/ModuleNotFoundError; got {report.warnings}"
        )
        stderr_text = buf.getvalue()
        assert ("hypothesis_ledger" in stderr_text) or ("passive mode" in stderr_text), (
            f"stderr should mention hypothesis_ledger or passive mode; got {stderr_text!r}"
        )


class TestInvariantsAndIdempotency:
    """Forward-only DAG invariant + idempotency on already-terminal parents."""

    def test_devil_advocate_pass_idempotent_on_already_refuted(
        self, isolated_ledger,
    ) -> None:
        """Already-REFUTED parent → empty Report, no second update attempt."""
        hid_a = _seed_refuted_hypothesis("Already refuted legacy claim")
        refuted_summary = next(
            s for s in query_by_status(HypothesisStatus.REFUTED) if s.hid == hid_a
        )

        # Ensure enum identity parity (prior tests may have created separate HypothesisStatus
        # instances via reload; re-import ensures single-module identity).
        from scripts_01.hypothesis_ledger import HypothesisStatus as HS
        if refuted_summary.status != HS.REFUTED:
            refuted_summary.status = HS.REFUTED

        report = devil_advocate_pass(refuted_summary)
        # Idempotent: no transition attempted.
        assert report.refuted is False
        assert report.iteration_count == 0
        assert report.new_candidates == []
        # Original stays REFUTED (no rollback).
        assert query_by_status(HypothesisStatus.REFUTED)[0].hid == hid_a
        # No spurious OPEN candidates created.
        open_count_before_and_after = len(query_by_status(HypothesisStatus.OPEN))
        assert open_count_before_and_after == 0

    def test_devil_advocate_pass_empty_hid_returns_empty_report(
        self, isolated_ledger,
    ) -> None:
        """Hypothesis with empty .hid → empty Report, no raise."""
        from dataclasses import dataclass as _dc

        @_dc
        class _EmptyHid:
            hid: str = ""
            text: str = ""
            status = HypothesisStatus.OPEN
            tags = []
            kill_criteria = []

        fake = _EmptyHid()
        report = devil_advocate_pass(fake)
        assert report.refuted is False
        assert report.iteration_count == 0
        assert any("hid missing" in w for w in report.warnings)


class TestFailsOpenWhenCandidatesLost:
    """If all 3 candidate registrations fail → do NOT refute (fails-open)."""

    def test_devil_advocate_pass_fails_open_when_all_candidates_fail(
        self, isolated_ledger, monkeypatch,
    ) -> None:
        """Monkeypatch add_hypothesis → raise. Devil's-advocate must NOT refute."""
        from scripts_01 import hypothesis_ledger as _hl

        call_count = {"n": 0}

        def _raising_add(*args, **kwargs):
            call_count["n"] += 1
            raise RuntimeError(f"simulated candidate[{call_count['n']}] add failure")

        # SEED FIRST (uses real add_hypothesis) — monkeypatch applied AFTER.
        hid_a = _seed_open_hypothesis("Candidate registration failing")
        open_summary = next(
            s for s in query_by_status(HypothesisStatus.OPEN) if s.hid == hid_a
        )

        monkeypatch.setattr(_hl, "add_hypothesis", _raising_add)

        report = devil_advocate_pass(open_summary)

        # Fails-open: refuted=False, no candidates, original stays OPEN.
        assert report.refuted is False
        assert report.new_candidates == []
        assert report.iteration_count == 0
        # All 3 add_hypothesis attempts were made (deterministic sequential).
        assert call_count["n"] == 3, (
            f"expected 3 add_hypothesis attempts (1 per heuristic); got {call_count['n']}"
        )
        # Original is still OPEN (no refutation attempted).
        assert any(s.hid == hid_a for s in query_by_status(HypothesisStatus.OPEN))
        assert not any(s.hid == hid_a for s in query_by_status(HypothesisStatus.REFUTED))
