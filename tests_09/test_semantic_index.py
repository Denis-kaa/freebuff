#!/usr/bin/env python3
"""
Tests for Semantic Index (torch SVD LSA) in scripts_01/knowledge_engine.py.
"""

from __future__ import annotations

import sys
import numpy as np
import pytest
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.knowledge_engine import (
    SemanticIndex, KnowledgeEngine,
)
from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ke_test"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def populated_ke(tmp_workspace: Path) -> KnowledgeEngine:
    ke = KnowledgeEngine(workspace_root=tmp_workspace)
    ke.index_document("router_doc", "capability based router with scoring routing model")
    ke.index_document("memory_doc", "memory engine with five storage levels context")
    ke.index_document("context_doc", "context builder unified context stream bridge")
    ke.index_document("graph_doc", "graph index with nodes edges relationships traversal")
    ke.index_document("knowledge_doc", "knowledge engine fts index vector search hybrid")
    return ke


@pytest.fixture
def fitted_ke(populated_ke: KnowledgeEngine) -> KnowledgeEngine:
    populated_ke.fit_semantic(n_components=3)
    return populated_ke


class TestSemanticIndex:
    """Direct tests of SemanticIndex."""

    def test_fit_creates_embeddings(self, tmp_workspace: Path):
        si = SemanticIndex(tmp_workspace)
        vocab = {"router": 0, "memory": 1, "context_12": 2, "engine": 3}
        vectors = np.zeros((3, 4), dtype=np.float32)
        vectors[0] = [3, 0, 0, 0]
        vectors[1] = [0, 3, 0, 2]
        vectors[2] = [0, 0, 3, 0]
        si.fit(vectors, ["router", "memory", "context_12"], vocab, n_components=2)
        assert not si.is_empty()
        assert si._u.shape == (3, 2)
        assert si._s.shape == (2,)
        assert si._vh.shape == (2, 4)

    def test_fit_too_few_docs(self, tmp_workspace: Path):
        si = SemanticIndex(tmp_workspace)
        vocab = {"test": 0}
        vectors = np.ones((1, 1), dtype=np.float32)
        si.fit(vectors, ["doc1"], vocab, n_components=5)
        assert si.is_empty()

    def test_search_returns_results(self, tmp_workspace: Path):
        si = SemanticIndex(tmp_workspace)
        vocab = {"router": 0, "memory": 1, "scoring": 2, "engine": 3}
        vectors = np.zeros((2, 4), dtype=np.float32)
        vectors[0] = [3, 0, 2, 0]
        vectors[1] = [0, 3, 0, 2]
        si.fit(vectors, ["router_doc", "memory_doc"], vocab, n_components=2)
        results = si.search("router scoring", top_k=5)
        assert len(results) >= 1
        assert results[0][0] == "router_doc"

    def test_search_empty_index(self, tmp_workspace: Path):
        si = SemanticIndex(tmp_workspace)
        assert si.search("test") == []

    def test_persistence(self, tmp_workspace: Path):
        si1 = SemanticIndex(tmp_workspace)
        vocab = {"alpha": 0, "beta": 1}
        vectors = np.array([[2, 0], [0, 2]], dtype=np.float32)
        si1.fit(vectors, ["doc_alpha", "doc_beta"], vocab, n_components=1)
        assert not si1.is_empty()

        si2 = SemanticIndex(tmp_workspace)
        assert not si2.is_empty()
        results = si2.search("alpha")
        assert len(results) >= 1

    def test_clear(self, tmp_workspace: Path):
        si = SemanticIndex(tmp_workspace)
        vocab = {"alpha": 0, "beta": 1}
        vectors = np.array([[2, 0], [0, 2]], dtype=np.float32)
        si.fit(vectors, ["doc_alpha", "doc_beta"], vocab, n_components=1)
        assert not si.is_empty()
        si.clear()
        assert si.is_empty()
        assert not (tmp_workspace / "context_12" / "knowledge" / "svd_u.npy").exists()


class TestSemanticMLMode:
    """Tests for semantic_ml mode in KnowledgeEngine."""

    def test_semantic_ml_search(self, fitted_ke: KnowledgeEngine):
        results = fitted_ke.search("router routing", mode="semantic_ml")
        assert len(results) >= 1
        assert results[0].doc_id == "router_doc"

    def test_semantic_ml_empty_query(self, fitted_ke: KnowledgeEngine):
        results = fitted_ke.search("", mode="semantic_ml")
        assert len(results) == 0

    def test_without_fit(self, populated_ke: KnowledgeEngine):
        results = populated_ke.search("router", mode="semantic_ml")
        assert len(results) == 0


class TestSemanticEdgeCases:
    """Edge cases."""

    def test_fit_after_index(self, populated_ke: KnowledgeEngine):
        populated_ke.fit_semantic(n_components=2)
        assert not populated_ke.semantic.is_empty()

    def test_fit_twice(self, fitted_ke: KnowledgeEngine):
        fitted_ke.fit_semantic(n_components=2)
        fitted_ke.fit_semantic(n_components=2)
        assert not fitted_ke.semantic.is_empty()

    def test_stats_after_fit(self, fitted_ke: KnowledgeEngine):
        stats = fitted_ke.get_stats()
        assert stats.total_docs >= 5

    def test_semantic_index_structure(self, fitted_ke: KnowledgeEngine):
        si = fitted_ke.semantic
        assert si._u.shape[0] == 5
        assert si._u.shape[1] == 3
        assert len(si._s) == 3
        assert si._vh.shape[0] == 3

    def test_search_after_clear(self, fitted_ke: KnowledgeEngine):
        fitted_ke.clear()
        results = fitted_ke.search("router", mode="semantic_ml")
        assert len(results) == 0

    def test_rebuild_with_fit(self, tmp_workspace: Path):
        """rebuild_index from Memory Engine auto-fits semantic."""
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel
        mem = MemoryEngine(workspace_root=str(tmp_workspace))
        mem.store(MemoryLevel.KNOWLEDGE, "doc_a",
                  "capability router scoring model routing architecture")
        mem.store(MemoryLevel.KNOWLEDGE, "doc_b",
                  "memory engine storage context archive session")
        mem.store(MemoryLevel.KNOWLEDGE, "doc_c",
                  "graph index nodes edges traversal bfs path")

        ke = KnowledgeEngine(workspace_root=tmp_workspace)
        ke.rebuild_index()
        assert not ke.semantic.is_empty()
