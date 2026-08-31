#!/usr/bin/env python3
"""
Tests for RAG 2.0 Engine (scripts_01/rag_engine.py).

Tests:
  - RAGResult / RAGReport / FeatureVector serialization
  - rrf_merge: Reciprocal Rank Fusion
  - _extract_features: coverage, position, length normalization
  - rerank: feature-based re-ranking
  - expand_query: query expansion
  - search: keyword / hybrid_rrf modes, graceful degradation
  - CLI commands
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.rag_engine import (
    RAGEngine,
    RAGResult,
    RAGReport,
    FeatureVector,
    RRF_K,
    DEFAULT_TOP_K,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


class _StubResult:
    """Минимальный результат поиска KnowledgeEngine (контракт SearchResult)."""

    def __init__(self, doc_id: str, score: float, content: str, metadata: dict | None = None):
        self.doc_id = doc_id
        self.score = score
        self.content = content
        self.metadata = metadata or {}


class _StubKnowledgeEngine:
    """Заглушка KnowledgeEngine: простой keyword-поиск по словарю документов."""

    def __init__(self, docs: dict[str, str]):
        self.docs = docs  # doc_id -> content

    def search(self, query: str, top_k: int = 10, mode: str = "keyword"):
        terms = [t for t in re.findall(r"[а-яa-z0-9)+", query.lower()) if len(t) > 1]
        results = []
        for doc_id, content in self.docs.items():
            score = float(sum(1 for t in terms if t in content.lower()))
            results.append(_StubResult(doc_id, score, content))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


@pytest.fixture
def docs() -> dict[str, str]:
    return {
        "d1": "capability based router with scoring system for task distribution",
        "d2": "semantic search engine ranking documents by relevance and freshness",
        "d3": "collaboration session presence tracking for distributed agents",
        "d4": "capability scoring router re-ranking with bm25 and rrf fusion",
    }


@pytest.fixture
def engine(docs: dict[str, str]) -> RAGEngine:
    return RAGEngine(knowledge_engine=_StubKnowledgeEngine(docs))


# ═══════════════════════════════════════════════════════════════
# Dataclass serialization
# ═══════════════════════════════════════════════════════════════


class TestSerialization:
    def test_rag_result_to_dict(self):
        res = RAGResult(
            doc_id="d1",
            score=0.75,
            content="some content",
            snippet="short",
            metadata={"source": "test"},
            matched_terms=["router"],
            rank_sources={"keyword": 0.5},
            features={"coverage": 0.5},
        )
        d = res.to_dict()
        assert d["doc_id"] == "d1"
        assert d["score"] == 0.75
        assert d["snippet"] == "short"
        assert d["metadata"] == {"source": "test"}
        assert d["matched_terms"] == ["router"]
        assert d["rank_sources"] == {"keyword": 0.5}
        assert d["features"] == {"coverage": 0.5}

    def test_rag_result_snippet_default_and_truncation(self):
        long_content = "x" * 300
        res = RAGResult(doc_id="d1", score=1.0, content=long_content)
        d = res.to_dict()
        # Сниппет по умолчанию — первые 200 символов контента.
        assert len(d["snippet"]) == 200
        assert d["snippet"] == long_content[:200]

    def test_rag_result_snippet_long_explicit_truncated(self):
        res = RAGResult(doc_id="d1", score=1.0, content="c", snippet="y" * 300)
        d = res.to_dict()
        assert len(d["snippet"]) == 200
        assert d["snippet"].endswith("...")

    def test_rag_report_to_dict(self, engine: RAGEngine):
        report = engine.search("capability router", mode="keyword")
        d = report.to_dict()
        assert d["query"] == "capability router"
        assert d["mode"] == "keyword"
        assert isinstance(d["results"], list)
        assert "total_time_ms" in d
        assert "query_terms" in d

    def test_feature_vector_combined_score_default_weights(self):
        fv = FeatureVector(coverage=1.0, position=0.5)
        score = fv.combined_score()
        assert score > 0
        assert score == pytest.approx(1.0 * 0.30 + 0.5 * 0.20, abs=1e-6)

    def test_feature_vector_combined_score_custom_weights(self):
        fv = FeatureVector(coverage=1.0, term_frequency=1.0)
        score = fv.combined_score({"coverage": 0.5, "term_frequency": 0.5})
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_feature_vector_to_dict(self):
        fv = FeatureVector(coverage=0.5)
        d = fv.to_dict()
        assert d["coverage"] == 0.5
        assert set(d.keys()) == {
            "coverage", "term_frequency", "position", "length_norm",
            "freshness", "bm25_score", "semantic_score",
        }


# ═══════════════════════════════════════════════════════════════
# rrf_merge
# ═══════════════════════════════════════════════════════════════


class TestRRFMerge:
    def test_merge_two_lists(self):
        list_a = [("d1", 0.9, "c1", {}), ("d2", 0.8, "c2", {})]
        list_b = [("d2", 0.95, "c2", {}), ("d3", 0.7, "c3", {})]
        merged = RAGEngine.rrf_merge([list_a, list_b], k=60, top_k=10)
        assert len(merged) == 3
        doc_ids = [m[0] for m in merged]
        # d2 присутствует в обоих списках → выше суммарный RRF.
        assert doc_ids[0] == "d2"
        assert "d1" in doc_ids and "d3" in doc_ids

    def test_merge_rank_sources(self):
        list_a = [("d1", 0.9, "c1", {})]
        list_b = [("d1", 0.5, "c1", {})]
        merged = RAGEngine.rrf_merge([list_a, list_b], top_k=10)
        _, score, content, meta, sources = merged[0]
        assert content == "c1"
        assert "source_0" in sources and "source_1" in sources
        assert sources["source_0"] == 0.9
        assert sources["source_1"] == 0.5

    def test_merge_top_k_limit(self):
        list_a = [("d1", 1.0, "c1", {}), ("d2", 0.9, "c2", {}), ("d3", 0.8, "c3", {})]
        merged = RAGEngine.rrf_merge([list_a], top_k=2)
        assert len(merged) == 2

    def test_merge_empty(self):
        merged = RAGEngine.rrf_merge([[], []], top_k=10)
        assert merged == []

    def test_rrf_k_constant(self):
        assert RRF_K == 60


# ═══════════════════════════════════════════════════════════════
# Feature extraction
# ═══════════════════════════════════════════════════════════════


class TestFeatureExtraction:
    def test_coverage_full_and_partial(self, engine: RAGEngine):
        content = "capability router scoring"
        fv_full = engine._extract_features(content, ["capability", "router", "scoring"])
        assert fv_full.coverage == pytest.approx(1.0, abs=1e-6)
        fv_part = engine._extract_features(content, ["capability", "router", "missing"])
        assert fv_part.coverage == pytest.approx(2 / 3, abs=1e-6)

    def test_position_early_term(self, engine: RAGEngine):
        content = "router appears right at the start of the document text"
        fv = engine._extract_features(content, ["router"])
        assert fv.position == pytest.approx(1.0, abs=1e-6)

    def test_length_norm_short_and_long(self, engine: RAGEngine):
        fv_short = engine._extract_features("ab", ["ab"])
        assert fv_short.length_norm == pytest.approx(0.002, abs=1e-6)
        long_text = "word " * 1200  # ~6000 chars
        fv_long = engine._extract_features(long_text, ["word"])
        assert 0.0 <= fv_long.length_norm <= 1.0

    def test_empty_content(self, engine: RAGEngine):
        fv = engine._extract_features("", ["term"])
        assert fv.coverage == 0.0

    def test_freshness_default(self, engine: RAGEngine):
        fv = engine._extract_features("content with term", ["term"], metadata={})
        assert fv.freshness == pytest.approx(0.5, abs=1e-6)


# ═══════════════════════════════════════════════════════════════
# Re-ranking
# ═══════════════════════════════════════════════════════════════


class TestRerank:
    def test_rerank_reorders_by_features(self, engine: RAGEngine):
        candidates = [
            RAGResult(doc_id="far", score=1.0, content="text at end of document " * 50),
            RAGResult(doc_id="near", score=0.9, content="router capability near the beginning"),
        ]
        reranked = engine.rerank("router capability", candidates)
        assert len(reranked) == 2
        assert reranked[0].doc_id == "near"

    def test_rerank_empty_candidates(self, engine: RAGEngine):
        assert engine.rerank("query", []) == []

    def test_rerank_keeps_features(self, engine: RAGEngine):
        candidates = [RAGResult(doc_id="d1", score=1.0, content="router capability")]
        reranked = engine.rerank("router capability", candidates, keep_features=True)
        assert "coverage" in reranked[0].features
        fresh = [RAGResult(doc_id="d1", score=1.0, content="router capability")]
        reranked2 = engine.rerank("router capability", fresh, keep_features=False)
        assert reranked2[0].features == {}


# ═══════════════════════════════════════════════════════════════
# Query expansion
# ═══════════════════════════════════════════════════════════════


class TestExpandQuery:
    def test_empty_query(self, engine: RAGEngine):
        expanded, extra = engine.expand_query("")
        assert expanded == ""
        assert extra == []

    def test_single_term_query_unchanged(self, engine: RAGEngine):
        expanded, extra = engine.expand_query("router")
        assert expanded == "router"
        assert extra == []

    def test_expansion_returns_extra_terms(self, engine: RAGEngine):
        expanded, extra = engine.expand_query("capability router scoring", max_terms=3)
        assert isinstance(extra, list)
        assert all(isinstance(t, str) for t in extra)


# ═══════════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════════


class TestSearch:
    def test_empty_query_returns_empty_report(self, engine: RAGEngine):
        report = engine.search("")
        assert isinstance(report, RAGReport)
        assert report.results == []

    def test_keyword_mode_returns_results(self, engine: RAGEngine):
        report = engine.search("capability router", mode="keyword")
        assert report.mode == "keyword"
        assert len(report.results) >= 1
        # d4 и d1 содержат оба термина.
        assert any(r.doc_id in ("d1", "d4") for r in report.results)

    def test_hybrid_rrf_mode(self, engine: RAGEngine):
        report = engine.search("capability router", mode="hybrid_rrf")
        assert report.mode == "hybrid_rrf"
        assert len(report.results) >= 1

    def test_hybrid_search_alias(self, engine: RAGEngine):
        report = engine.hybrid_search("scoring router")
        assert report.mode == "hybrid_rrf"

    def test_no_expand_flag(self, engine: RAGEngine):
        report = engine.search("capability router", mode="keyword", expand_query=False)
        assert report.expanded_query == ""

    def test_top_k_respected(self, engine: RAGEngine):
        report = engine.search("router", mode="keyword", top_k=2)
        assert len(report.results) <= 2

    def test_unknown_mode_raises(self, engine: RAGEngine):
        with pytest.raises(ValueError):
            engine.search("router", mode="nope")

    def test_graceful_degradation_without_ke(self, tmp_path):
        # KnowledgeEngine по умолчанию создаётся с пустым workspace — без падения.
        rag = RAGEngine(workspace_root=tmp_path)
        report = rag.search("anything", mode="hybrid_rrf")
        assert isinstance(report, RAGReport)
        assert report.results == []

    def test_rerank_not_called_for_keyword(self, engine: RAGEngine):
        report = engine.search("capability router", mode="keyword")
        for r in report.results:
            assert r.features == {}


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts_01.rag_engine import main

        monkeypatch.setattr(sys, "argv", ["rag_engine.py", "--help"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_no_command_prints_help(self, monkeypatch, capsys):
        from scripts_01.rag_engine import main

        monkeypatch.setattr(sys, "argv", ["rag_engine.py"])
        code = main()
        assert code == 1
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "Commands" in out
