"""Tests for scripts_01/weighted_scoring_engine.py (v5.189.65).

Hermetic via ``isolated_ledger`` fixture (mirrors conftest pattern: monkeypatch
``hypothesis_ledger.DEFAULT_LEDGER_DIR`` to tmp_path). Tests cover weights
normalization, multi-criteria scoring against synthetic ledger entries, and
the CLI subprocess end-to-end.
"""

from __future__ import annotations

import json
import subprocess
import sys
***REMOVED***

import pytest


# ─── helpers ────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_ledger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Re-route ``scripts_01.hypothesis_ledger.DEFAULT_LEDGER_DIR`` to tmp.

    Mirrors ``tests_09/conftest.py::isolated_corpus_root`` pattern. Each test
    gets its own ledger_dir (per-hypothesis JSONL files appear inside).
    """
    import scripts_01.hypothesis_ledger as hl

    ledger_dir = tmp_path / "hypothesis_ledger"
    monkeypatch.setattr(hl, "DEFAULT_LEDGER_DIR", ledger_dir)
    return ledger_dir


def _seed_supported(
    text: str,
    *,
    confidence: float = 0.5,
    tags=None,
    kill_criteria=None,
) -> str:
    """Add hypothesis + transition to SUPPORTED; return hid."""
    from scripts_01.hypothesis_ledger import (
        HypothesisStatus,
        add_hypothesis,
        update_status,
    )
    summary = add_hypothesis(
        text,
        tags=tags,
        kill_criteria=kill_criteria,
        confidence=confidence,
    )
    update_status(summary.hid, HypothesisStatus.SUPPORTED)
    return summary.hid


# ─── weight math ────────────────────────────────────────────────────────


class TestWeights:
    def test_default_weights_sum_to_one(self) -> None:
        from scripts_01.weighted_scoring_engine import DEFAULT_WEIGHTS

        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_default_weights_have_4_expected_keys(self) -> None:
        from scripts_01.weighted_scoring_engine import DEFAULT_WEIGHTS

        assert set(DEFAULT_WEIGHTS.keys()) == {
            "confidence", "evidence", "recency", "tag_match",
        ***REMOVED***

    def test_normalize_weights_rejects_missing_keys(self) -> None:
        from scripts_01.weighted_scoring_engine import normalize_weights

        with pytest.raises(ValueError, match="missing keys"):
            normalize_weights({"confidence": 0.5, "evidence": 0.5***REMOVED***)

    def test_normalize_weights_rejects_unknown_keys(self) -> None:
        from scripts_01.weighted_scoring_engine import normalize_weights

        with pytest.raises(ValueError, match="unknown keys"):
            normalize_weights({
                "confidence": 0.4, "evidence": 0.2, "recency": 0.25,
                "tag_match": 0.15, "rogue": 0.0,
            ***REMOVED***)

    def test_normalize_weights_allows_zero_tag_match(self) -> None:
        """Zero weight допустимо (operator opts out of tag factor)."""
        from scripts_01.weighted_scoring_engine import normalize_weights
        out = normalize_weights({
            "confidence": 0.5, "evidence": 0.3, "recency": 0.2,
            "tag_match": 0.0,
        ***REMOVED***)
        assert sum(out.values()) == 1.0
        assert out["tag_match"***REMOVED*** == 0.0

    def test_normalize_weights_rejects_zero_total(self) -> None:
        from scripts_01.weighted_scoring_engine import normalize_weights

        with pytest.raises(ValueError, match="degenerate"):
            normalize_weights({
                "confidence": 0.0, "evidence": 0.0, "recency": 0.0,
                "tag_match": 0.0,
            ***REMOVED***)

    def test_normalize_weights_rescales_to_unit_sum(self) -> None:
        from scripts_01.weighted_scoring_engine import normalize_weights
        # raw sum 4.0 → each / 4.
        out = normalize_weights({
            "confidence": 1.6, "evidence": 0.8, "recency": 1.0,
            "tag_match": 0.6,
        ***REMOVED***)
        assert abs(sum(out.values()) - 1.0) < 1e-9
        # Ratio between keys preserved.
        assert abs(out["confidence"***REMOVED*** / out["evidence"***REMOVED*** - 2.0) < 1e-9

    def test_recency_factor_at_zero_is_unity(self) -> None:
        from scripts_01.weighted_scoring_engine import _recency_factor
        assert _recency_factor(0.0) == 1.0

    def test_recency_factor_half_life_is_half(self) -> None:
        from scripts_01.weighted_scoring_engine import _recency_factor
        assert abs(_recency_factor(7.0, half_life_days=7.0) - 0.5) < 1e-9

    def test_recency_factor_old_entry_decays_to_zero(self) -> None:
        from scripts_01.weighted_scoring_engine import _recency_factor
        # 28 days (~4× half-life) → 2^-4 = 0.0625.
        assert abs(_recency_factor(28.0) - 0.0625) < 1e-6

    def test_recency_factor_negative_days_clamps_to_unity(self) -> None:
        from scripts_01.weighted_scoring_engine import _recency_factor
        # Future-dated (clock skew): clamp to 1.0 (don't penalize).
        assert _recency_factor(-0.5) == 1.0

    def test_tag_match_full_overlap_is_unity(self) -> None:
        from scripts_01.weighted_scoring_engine import _tag_match
        assert _tag_match(["a", "b"***REMOVED***, ["a", "b"***REMOVED***) == 1.0

    def test_tag_match_zero_overlap_is_zero(self) -> None:
        from scripts_01.weighted_scoring_engine import _tag_match
        assert _tag_match(["x", "y"***REMOVED***, ["a", "b"***REMOVED***) == 0.0

    def test_tag_match_no_focus_is_neutral_half(self) -> None:
        from scripts_01.weighted_scoring_engine import _tag_match
        assert _tag_match(["anything"***REMOVED***, focus=None) == 0.5
        assert _tag_match(["anything"***REMOVED***, focus=[***REMOVED***) == 0.5


# ─── engine ─────────────────────────────────────────────────────────────


class TestScoreSupported:
    def test_empty_ledger_returns_empty_list(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        engine = WeightedScoringEngine()
        assert engine.score_supported() == [***REMOVED***

    def test_single_supported_scores_nonnegatively(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        _seed_supported("Test hypothesis A", confidence=0.8)
        engine = WeightedScoringEngine()
        ranked = engine.score_supported()
        assert len(ranked) == 1
        r = ranked[0***REMOVED***
        assert r.score > 0.0
        assert r.confidence == pytest.approx(0.8)
        assert r.evidence_count == 0
        # Breakdown must sum to score (within floating-point tolerance).
        assert sum(r.breakdown.values()) == pytest.approx(r.score, abs=1e-6)

    def test_only_supported_hypotheses_appear(self, isolated_ledger: Path) -> None:
        """OPEN / REFUTED / kill_criteria-met hypotheses не должны появляться."""
        from scripts_01.hypothesis_ledger import add_hypothesis, query_by_status
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        # Add OPEN — should NOT appear in scoring.
        add_hypothesis("Open hypothesis", confidence=0.99)
        engine = WeightedScoringEngine()
        assert engine.score_supported() == [***REMOVED***

    def test_sort_descending_by_score(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        _seed_supported("Low  conf: 0.2", confidence=0.2)
        _seed_supported("High conf: 0.9", confidence=0.9)
        _seed_supported("Mid  conf: 0.6", confidence=0.6)
        engine = WeightedScoringEngine()
        scores = [r.confidence for r in engine.score_supported()***REMOVED***
        assert scores == sorted(scores, reverse=True), (
            f"Expected desc-sorted, got {scores***REMOVED***"
        )

    def test_evidence_count_saturates_at_configured_max(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import (
            WeightedScoringEngine,
        )
        # Seed with 5+ evidence urls → normalized to 1.0 (saturation=5).
        kc = [
            {
                "criterion": f"crit_{i***REMOVED***",
                "met": False,
                "evidence_url": f"https://x.test/{i***REMOVED***",
            ***REMOVED***
            for i in range(5)
        ***REMOVED***
        _seed_supported("Many evidences", confidence=0.5, kill_criteria=kc)
        engine = WeightedScoringEngine(evidence_saturation=5)
        ranked = engine.score_supported()
        r = ranked[0***REMOVED***
        assert r.evidence_count == 5
        assert r.breakdown["evidence"***REMOVED*** == pytest.approx(0.20, abs=1e-6)
        # Same hypothesis at 10 evidences → same normalized (saturated).
        kc2 = kc + [
            {"criterion": f"crit_{i***REMOVED***", "met": False, "evidence_url": f"https://x.test/{i***REMOVED***"***REMOVED***
            for i in range(5, 10)
        ***REMOVED***
        _seed_supported("Many evidences more", confidence=0.5, kill_criteria=kc2)
        ranked2 = engine.score_supported()
        # Find second entry (added second).
        more = [r for r in ranked2 if r.evidence_count == 10***REMOVED***[0***REMOVED***
        assert more.breakdown["evidence"***REMOVED*** == pytest.approx(0.20, abs=1e-6)

    def test_focus_tag_match_boosts_score(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        _seed_supported("Pricing hypothesis", confidence=0.5, tags=["pricing"***REMOVED***)
        _seed_supported("Other topic", confidence=0.5, tags=["unrelated"***REMOVED***)
        engine = WeightedScoringEngine()
        # Without focus: both equally weighted (match_score=0.5 each).
        no_focus = engine.score_supported()
        # With focus=pricing: pricing hypothesis gets tag_match=1.0, others 0.0.
        with_focus = engine.score_supported(focus_tags=["pricing"***REMOVED***)
        # The pricing hypothesis's score WITH focus > WITHOUT focus.
        pricing_no = [r for r in no_focus if "Pricing" in r.text***REMOVED***[0***REMOVED***
        pricing_yes = [r for r in with_focus if "Pricing" in r.text***REMOVED***[0***REMOVED***
        assert pricing_yes.score > pricing_no.score, (
            f"focus should boost pricing score: no={pricing_no.score:.4f***REMOVED*** "
            f"yes={pricing_yes.score:.4f***REMOVED***"
        )

    def test_score_clamped_to_unit_interval(self, isolated_ledger: Path) -> None:
        """Even with all factors max, score <= 1.0 (clamp safety)."""
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        _seed_supported(
            "All maxes",
            confidence=1.0,
            tags=["pricing", "research", "tools"***REMOVED***,
            kill_criteria=[
                {"criterion": "x", "met": False, "evidence_url": "https://x.test/1"***REMOVED***
            ***REMOVED*** * 5,
        )
        engine = WeightedScoringEngine()
        ranked = engine.score_supported(focus_tags=["pricing", "research"***REMOVED***)
        assert 0.0 <= ranked[0***REMOVED***.score <= 1.0

    def test_score_4factors_sum_to_weighted_sum(self, isolated_ledger: Path) -> None:
        """Sanity: breakdown[factor***REMOVED*** = weights[factor***REMOVED*** * raw_factor_value."""
        from scripts_01.weighted_scoring_engine import (
            DEFAULT_WEIGHTS,
            WeightedScoringEngine,
        )
        _seed_supported("Breakdown math", confidence=0.5)
        engine = WeightedScoringEngine()
        ranked = engine.score_supported()
        r = ranked[0***REMOVED***
        assert r.breakdown["confidence"***REMOVED*** == pytest.approx(
            DEFAULT_WEIGHTS["confidence"***REMOVED*** * r.confidence, abs=1e-6
        )

    def test_score_zero_evidence_zero_factor(self, isolated_ledger: Path) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        _seed_supported("No evidence", confidence=0.5)
        engine = WeightedScoringEngine()
        ranked = engine.score_supported()
        assert ranked[0***REMOVED***.breakdown["evidence"***REMOVED*** == 0.0

    def test_custom_weights_redistribute(self, isolated_ledger: Path) -> None:
        """Custom weights (confidence=1.0) → score == confidence."""
        from scripts_01.weighted_scoring_engine import (
            WeightedScoringEngine,
        )
        _seed_supported("Custom weights", confidence=0.7)
        engine = WeightedScoringEngine(
            weights={
                "confidence": 1.0, "evidence": 0.0,
                "recency": 0.0, "tag_match": 0.0,
            ***REMOVED***
        )
        ranked = engine.score_supported()
        assert ranked[0***REMOVED***.score == pytest.approx(0.7, abs=1e-6)

    def test_engine_constructor_validates_half_life(self) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        with pytest.raises(ValueError, match="half_life_days"):
            WeightedScoringEngine(half_life_days=0.0)
        with pytest.raises(ValueError, match="half_life_days"):
            WeightedScoringEngine(half_life_days=400.0)

    def test_engine_constructor_validates_saturation(self) -> None:
        from scripts_01.weighted_scoring_engine import WeightedScoringEngine
        with pytest.raises(ValueError, match="evidence_saturation"):
            WeightedScoringEngine(evidence_saturation=0)
        with pytest.raises(ValueError, match="evidence_saturation"):
            WeightedScoringEngine(evidence_saturation=101)


# ─── CLI ─────────────────────────────────────────────────────────────────


class TestCLI:
    def test_cli_json_empty_dir_subprocess(self, tmp_path: Path) -> None:
        """CLI --json на пустой/hypothetical root → stdout == '[***REMOVED***'."""
        empty_dir = tmp_path / "empty_ledger"
        empty_dir.mkdir()
        result = subprocess.run(
            [
                sys.executable, "-m", "scripts_01.weighted_scoring_engine",
                "--root", str(empty_dir),
                "--json",
            ***REMOVED***,
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
        assert result.returncode == 0, (
            f"non-zero exit: stderr={result.stderr!r***REMOVED***"
        )
        json_out = result.stdout.strip()
        assert json_out == "[***REMOVED***", f"Expected '[***REMOVED***', got {json_out!r***REMOVED***"

    def test_cli_runs_subprocess_with_supported(self, tmp_path: Path) -> None:
        """Seed 1 SUPPORTED hypothesis + run CLI → stdout contains hid + score."""
        ledger_dir = tmp_path / "ledger"
        ledger_dir.mkdir()
        import scripts_01.hypothesis_ledger as hl
        original = hl.DEFAULT_LEDGER_DIR
        try:
            hl.DEFAULT_LEDGER_DIR = ledger_dir
            _seed_supported("CLI subprocess hypothesis", confidence=0.7)
        finally:
            hl.DEFAULT_LEDGER_DIR = original

        result = subprocess.run(
            [
                sys.executable, "-m", "scripts_01.weighted_scoring_engine",
                "--root", str(ledger_dir),
                "--json",
            ***REMOVED***,
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
        assert result.returncode == 0, f"stderr={result.stderr!r***REMOVED***"
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover
            pytest.fail(f"non-JSON output: {result.stdout!r***REMOVED***: {exc***REMOVED***")
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0***REMOVED***["confidence"***REMOVED*** == pytest.approx(0.7)
        assert parsed[0***REMOVED***["hid"***REMOVED***.startswith("h_")

    def test_cli_text_format_includes_score_and_breakdown(
        self, tmp_path: Path,
    ) -> None:
        """Text output contains score=N.NNN + per-factor breakdown lines."""
        ledger_dir = tmp_path / "ledger"
        ledger_dir.mkdir()
        import scripts_01.hypothesis_ledger as hl
        original = hl.DEFAULT_LEDGER_DIR
        try:
            hl.DEFAULT_LEDGER_DIR = ledger_dir
            _seed_supported("Text CLI test", confidence=0.6)
        finally:
            hl.DEFAULT_LEDGER_DIR = original

        result = subprocess.run(
            [
                sys.executable, "-m", "scripts_01.weighted_scoring_engine",
                "--root", str(ledger_dir),
            ***REMOVED***,
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
        assert result.returncode == 0
        out = result.stdout
        assert "score=" in out, "Text must include 'score=' marker"
        assert "confidence" in out
        assert "evidence" in out
        assert "recency" in out
        assert "tag_match" in out

    def test_cli_version_flag(self) -> None:
        result = subprocess.run(
            [
                sys.executable, "-m", "scripts_01.weighted_scoring_engine",
                "--version",
            ***REMOVED***,
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0
        assert "weighted_scoring_engine" in result.stdout
        assert "v5.189.65" in result.stdout
