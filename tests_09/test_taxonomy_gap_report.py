"""tests_09/test_taxonomy_gap_report.py — Hermetic tests for taxonomy gap report.

Per LLM_SYSTEM_PROMPT contract (≥18 capabilities, mix EXPLICIT+INFERRED,
KINDS ∈ {tool, module, role, engine}) AND Section A/B categorization
(in TAXONOMY vs NOT-in-TAXONOMY).

Pattern follows tests_09/test_corpus_persistence.py style — focused unit tests
with curated fixtures (no network, no real LLM).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core_02.capability_gap_auditor import (
    TAXONOMY,
    _extract_capabilities_from_text,
    _parse_llm_response,
)
from scripts_01._curated_llm_gateway import (
    CuratedLlmGateway,
    CuratedResponse,
)
from scripts_01.taxonomy_gap_report import (
    build_gap_analysis,
    render_report,
)


# ─── TestCuratedGateway ─────────────────────────────────────────────────────


class TestCuratedGateway:
    def test_returns_18_capabilities_from_curated_default(self):
        gw = CuratedLlmGateway()
        parsed = _parse_llm_response(gw.generate_by_capabilities([], []).content)
        assert len(parsed) == 18, f"expected 18 capabilities, got {len(parsed)}"

    def test_explicit_count_is_8(self):
        gw = CuratedLlmGateway()
        parsed = _parse_llm_response(gw.generate_by_capabilities([], []).content)
        explicit = [item for item in parsed if item.get("explicit")]
        assert len(explicit) == 8

    def test_inferred_count_is_10(self):
        gw = CuratedLlmGateway()
        parsed = _parse_llm_response(gw.generate_by_capabilities([], []).content)
        inferred = [item for item in parsed if not item.get("explicit")]
        assert len(inferred) == 10

    def test_all_kinds_are_valid_closed_set(self):
        gw = CuratedLlmGateway()
        parsed = _parse_llm_response(gw.generate_by_capabilities([], []).content)
        valid_kinds = {"tool", "module", "role", "engine"}
        invalid = [item for item in parsed if item["kind"] not in valid_kinds]
        assert not invalid, f"invalid kinds: {[(i['item_id'], i['kind']) for i in invalid]}"

    def test_provenance_field_present_per_item(self):
        gw = CuratedLlmGateway()
        parsed = _parse_llm_response(gw.generate_by_capabilities([], []).content)
        # _provenance is allowed to be dropped by parser (only 6 known fields parsed).
        # We assert via the raw JSON to confirm each item has it.
        raw = json.loads(gw.response_content.replace("```json\n", "").replace("\n```", ""))
        for item in raw:
            assert "_provenance" in item, (
                f"missing _provenance: {item['item_id']}"
            )

    def test_call_count_increments(self):
        gw = CuratedLlmGateway()
        gw.generate_by_capabilities(["plan"], [{"role": "user", "content": "x"}])
        gw.generate_by_capabilities(["plan"], [{"role": "user", "content": "y"}])
        assert gw.call_count == 2

    def test_last_messages_captured_for_inspection(self):
        gw = CuratedLlmGateway()
        msgs = [
            {"role": "system", "content": "You are ..."},
            {"role": "user", "content": "extract capabilities"},
        ]
        gw.generate_by_capabilities(["plan"], msgs)
        assert gw.last_messages == msgs


# ─── TestBuildGapAnalysis ──────────────────────────────────────────────────


class TestBuildGapAnalysis:
    def test_sec_a_categorizes_in_taxonomy_not_keyword_matched(self):
        """7 INFERRED caps already in TAXONOMY but no regex trigger → Section A."""
        gw = CuratedLlmGateway()
        curated = gw.generate_by_capabilities([], []).content
        # Use EMPTY task text to force 0 deterministic → all LLM caps are inferred.
        analysis = build_gap_analysis("", curated)
        sec_a_expected = {
            "research_web", "competitor_matrix_builder", "hypothesis_ledger",
            "corpus_persistence", "vanity_metric_filter",
            "weighted_scoring_engine", "persona_funnel_analyzer",
        }
        assert analysis["sec_a_in_taxonomy_not_matched"] == sec_a_expected

    def test_sec_b_categorizes_not_in_taxonomy(self):
        """3 INFERRED caps NOT-in-TAXONOMY → Section B (new entries needed)."""
        gw = CuratedLlmGateway()
        curated = gw.generate_by_capabilities([], []).content
        analysis = build_gap_analysis("", curated)
        sec_b_expected = {
            "tone_of_voice_auditor", "hallucination_detector", "cost_estimator",
        }
        assert analysis["sec_b_not_in_taxonomy"] == sec_b_expected

    def test_inferred_gap_at_least_n(self):
        """Curated mock must yield ≥8 INFERRED (10 expected) — sanity check."""
        gw = CuratedLlmGateway()
        analysis = build_gap_analysis("", gw.generate_by_capabilities([], []).content)
        assert len(analysis["inferred_gaps"]) >= 8, (
            f"curated mock insufficient: only {len(analysis['inferred_gaps'])} inferred gaps"
        )

    def test_deterministic_8_on_vocal_fragment(self):
        """Sanity-check the deterministic baseline matches v5.189.61 contract (8 caps)."""
        gw = CuratedLlmGateway()
        vocal_text = (
            "anti-pattern mining заброшенные школы; "
            "бизнес-модель 14 полей конструкции; "
            "claim source tracker [fact] vs observation vs hypothesis; "
            "devil's advocate kill-questions; "
            "unit economics teacher time calibration; "
            "прайс-скан pricing enumerator; "
            "MVP предпродажа pilot groups; "
            "qualitative review отзыв pain-points cluster; "
            "Anti-pattern mining заброшенные школы"  # duplicate to test dedup
        )
        analysis = build_gap_analysis(vocal_text, gw.generate_by_capabilities([], []).content)
        # 8 deterministic (matches v5.189.61 contract).
        assert len(analysis["deterministic_ids"]) == 8


# ─── TestRenderReport ──────────────────────────────────────────────────────


class TestRenderReport:
    def test_report_contains_section_a_and_b_headers(self):
        gw = CuratedLlmGateway()
        analysis = build_gap_analysis("", gw.generate_by_capabilities([], []).content)
        report = render_report("vocal", "задача.md", analysis)
        assert "## Section A" in report
        assert "## Section B" in report

    def test_report_includes_section_b_with_provenance(self):
        gw = CuratedLlmGateway()
        analysis = build_gap_analysis("", gw.generate_by_capabilities([], []).content)
        report = render_report("vocal", "задача.md", analysis)
        # Section B entries include `_provenance` text.
        assert "NOT-IN-TAXONOMY" in report
        assert "tone_of_voice_auditor" in report
        assert "hallucination_detector" in report
        assert "cost_estimator" in report

    def test_report_markdown_is_well_formed(self):
        gw = CuratedLlmGateway()
        analysis = build_gap_analysis("", gw.generate_by_capabilities([], []).content)
        report = render_report("vocal", "задача.md", analysis)
        assert report.startswith("# TAXONOMY Gap Report")
        assert report.rstrip().endswith("_")


# ─── TestEndToEnd (project_root → gap-report.md) ───────────────────────────


class TestEndToEnd:
    def test_cli_on_real_vocal_project_produces_report(self, tmp_path):
        """End-to-end: copy vocal task into tmp_path, run script, assert report."""
        # Setup minimal project.
        project_dir = tmp_path / "vocal_test"
        project_dir.mkdir()
        # Reuse v5.189.61 keywords that fired deterministic 8 caps.
        # (We don't need full vocal — sufficient to construct a tiny task file.)
        vocal_task = (
            "## 1. Anti-pattern mining\n"
            "## 2. Бизнес-модель: 14 полей конструкции\n"
            "## 3. Claim source tracker [fact]\n"
            "## 4. Devil's advocate kill-questions\n"
            "## 5. Unit economics calibration teacher time\n"
            "## 6. Прайс-скан pricing enumerator\n"
            "## 7. MVP предпродажа pilot groups\n"
            "## 8. Qualitative review отзыв pain-points\n"
        )
        (project_dir / "задача.md").write_text(vocal_task, encoding="utf-8")

        cmd = [
            sys.executable, "-m", "scripts_01.taxonomy_gap_report",
            str(project_dir),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        report_path = project_dir / "TAXONOMY_GAP_REPORT.md"
        assert report_path.is_file()
        report = report_path.read_text(encoding="utf-8")
        assert "TAXONOMY Gap Report" in report
        # Has Section A (in TAXONOMY but not keyword-matched — empty because we crafted a fragment that fully matches).
        # Has deterministic baseline.
        assert "Deterministic caps (keyword/regex): 8" in report
