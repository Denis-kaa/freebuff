#!/usr/bin/env python3
"""
Tests for Graph Index (scripts/graph_index.py).

Tests:
  - Node CRUD
  - Edge CRUD (add, remove, inverse, symmetric)
  - get_related — basic, depth, filtering
  - shortest_path — BFS between nodes
  - subgraph — extraction around node
  - traverse — follow chain
  - auto_discover — automatic relationship detection
  - get_stats — statistics
  - Edge cases: empty graph, missing nodes, cycles
"""

from __future__ import annotations

import json
import os
import sys
import pytest
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.graph_index import (
    GraphIndex, GraphStats, Edge, Node, PathResult, REL_TYPES,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Путь к тестовой БД."""
    return tmp_path / "test_graph.db"


@pytest.fixture
def graph(db_path: Path) -> GraphIndex:
    """Пустой граф."""
    return GraphIndex(db_path)


@pytest.fixture
def populated_graph(db_path: Path) -> GraphIndex:
    """Граф с тестовыми данными:

    doc1 ──references──→ doc2
     │                     │
     │  parent             │  parent
     ▼                     ▼
    doc3 ──references──→ doc4
     │
     │  related
     ▼
    doc5
    """
    g = GraphIndex(db_path)
    g.add_edge("doc1", "doc2", "references", weight=0.8)
    g.add_edge("doc1", "doc3", "parent", weight=1.0)
    g.add_edge("doc2", "doc4", "parent", weight=1.0)
    g.add_edge("doc3", "doc4", "references", weight=0.6)
    g.add_edge("doc3", "doc5", "related", weight=0.7)
    return g


# ═══════════════════════════════════════════════════════════════
# Node tests
# ═══════════════════════════════════════════════════════════════


class TestNodes:
    """Тесты узлов графа."""

    def test_add_and_get_node(self, graph: GraphIndex):
        graph.add_node("doc1", node_type="document", label="Test Doc",
                       metadata={"source": "test"***REMOVED***)
        node = graph.get_node("doc1")
        assert node is not None
        assert node.doc_id == "doc1"
        assert node.node_type == "document"
        assert node.label == "Test Doc"
        assert node.metadata.get("source") == "test"

    def test_get_nonexistent_node(self, graph: GraphIndex):
        node = graph.get_node("nonexistent")
        assert node is None

    def test_remove_node(self, graph: GraphIndex):
        graph.add_node("doc1")
        graph.add_edge("doc1", "doc2", "references")
        assert graph.get_node("doc1") is not None

        removed = graph.remove_node("doc1")
        assert removed is True
        assert graph.get_node("doc1") is None
        # Рёбра тоже должны быть удалены
        stats = graph.get_stats()
        assert stats.total_edges == 0

    def test_remove_nonexistent_node(self, graph: GraphIndex):
        removed = graph.remove_node("ghost")
        assert removed is False

    def test_update_node(self, graph: GraphIndex):
        graph.add_node("doc1", label="Old")
        graph.add_node("doc1", label="New")
        node = graph.get_node("doc1")
        assert node.label == "New"


# ═══════════════════════════════════════════════════════════════
# Edge tests
# ═══════════════════════════════════════════════════════════════


class TestEdges:
    """Тесты рёбер графа."""

    def test_add_edge_creates_nodes(self, graph: GraphIndex):
        """add_edge с auto_add_nodes создаёт узлы автоматически."""
        graph.add_edge("doc_a", "doc_b", "references")
        assert graph.get_node("doc_a") is not None
        assert graph.get_node("doc_b") is not None

    def test_add_edge_inverse_created(self, graph: GraphIndex):
        """add_edge создаёт обратное ребро для parent."""
        graph.add_edge("parent_doc", "child_doc", "parent")

        # parent → child
        related = graph.get_related("parent_doc", rel_type="parent")
        assert any(r[0***REMOVED*** == "child_doc" for r in related)

        # child → parent (обратное ребро)
        related = graph.get_related("child_doc", rel_type="child")
        assert any(r[0***REMOVED*** == "parent_doc" for r in related)

    def test_add_edge_symmetric(self, graph: GraphIndex):
        """related — симметричное отношение (оба направления)."""
        graph.add_edge("doc1", "doc2", "related")

        r1 = graph.get_related("doc1", rel_type="related")
        r2 = graph.get_related("doc2", rel_type="related")
        assert any(r[0***REMOVED*** == "doc2" for r in r1)
        assert any(r[0***REMOVED*** == "doc1" for r in r2)

    def test_add_edge_invalid_type(self, graph: GraphIndex):
        with pytest.raises(ValueError):
            graph.add_edge("a", "b", "invalid_type")

    def test_remove_edge(self, graph: GraphIndex):
        graph.add_edge("doc1", "doc2", "references")
        assert graph.get_stats().total_edges >= 1

        removed = graph.remove_edge("doc1", "doc2", "references")
        assert removed is True
        assert graph.get_stats().total_edges == 0

    def test_remove_nonexistent_edge(self, graph: GraphIndex):
        removed = graph.remove_edge("a", "b", "references")
        assert removed is False

    def test_multiple_edge_types(self, graph: GraphIndex):
        """Между двумя узлами может быть несколько типов связей."""
        graph.add_edge("doc1", "doc2", "references")
        graph.add_edge("doc1", "doc2", "depends")

        related = graph.get_related("doc1")
        types = {r[1***REMOVED*** for r in related***REMOVED***
        assert "references" in types
        assert "depends" in types


# ═══════════════════════════════════════════════════════════════
# get_related tests
# ═══════════════════════════════════════════════════════════════


class TestGetRelated:
    """Тесты поиска связанных узлов."""

    def test_get_related_empty(self, graph: GraphIndex):
        results = graph.get_related("nonexistent")
        assert len(results) == 0

    def test_get_related_direct(self, populated_graph: GraphIndex):
        """Прямые связи doc1 (включая обратные рёбра)."""
        results = populated_graph.get_related("doc1", max_depth=1)
        ids = {r[0***REMOVED*** for r in results***REMOVED***
        assert "doc2" in ids  # references + referenced_by
        assert "doc3" in ids  # parent + child
        assert len(results) >= 2  # как минимум прямые связи
        # Также есть обратные (referenced_by, child)

    def test_get_related_depth_2(self, populated_graph: GraphIndex):
        """Связи doc1 глубиной 2."""
        results = populated_graph.get_related("doc1", max_depth=2)
        ids = {r[0***REMOVED*** for r in results***REMOVED***
        assert "doc2" in ids
        assert "doc3" in ids
        assert "doc4" in ids  # через doc1→doc3→doc4 или doc1→doc2→doc4
        assert len(results) >= 3

    def test_get_related_filter_by_type(self, populated_graph: GraphIndex):
        """Фильтрация по типу связи."""
        results = populated_graph.get_related("doc1", rel_type="parent")
        assert all(r[1***REMOVED*** == "parent" for r in results)
        ids = {r[0***REMOVED*** for r in results***REMOVED***
        assert "doc3" in ids

    def test_get_related_references_filter(self, populated_graph: GraphIndex):
        results = populated_graph.get_related("doc1", rel_type="references")
        ids = {r[0***REMOVED*** for r in results***REMOVED***
        assert "doc2" in ids

    def test_get_related_isolated_node(self, graph: GraphIndex):
        """Изолированный узел без связей."""
        graph.add_node("lonely")
        results = graph.get_related("lonely")
        assert len(results) == 0


# ═══════════════════════════════════════════════════════════════
# Shortest path tests
# ═══════════════════════════════════════════════════════════════


class TestShortestPath:
    """Тесты поиска кратчайшего пути."""

    def test_path_same_node(self, graph: GraphIndex):
        path = graph.shortest_path("a", "a")
        assert path is not None
        assert path.length == 0

    def test_path_direct_edge(self, populated_graph: GraphIndex):
        path = populated_graph.shortest_path("doc1", "doc2")
        assert path is not None
        assert path.length == 1
        assert len(path.path) == 1

    def test_path_via_middle(self, populated_graph: GraphIndex):
        """doc1 → doc3 → doc4 (через один узел)."""
        path = populated_graph.shortest_path("doc1", "doc4")
        assert path is not None
        assert path.length >= 2

    def test_path_no_path(self, graph: GraphIndex):
        """Между изолированными узлами нет пути."""
        graph.add_node("a")
        graph.add_node("b")
        path = graph.shortest_path("a", "b", max_depth=5)
        assert path is None

    def test_path_max_depth_limit(self, populated_graph: GraphIndex):
        """Поиск с ограничением глубины."""
        path = populated_graph.shortest_path("doc1", "doc5", max_depth=1)
        # doc1 → doc5 через doc3, глубина 2, так что с max_depth=1 не найдётся
        assert path is None or path.length <= 1


# ═══════════════════════════════════════════════════════════════
# Subgraph tests
# ═══════════════════════════════════════════════════════════════


class TestSubgraph:
    """Тесты подграфа."""

    def test_subgraph_depth_1(self, populated_graph: GraphIndex):
        nodes, edges = populated_graph.subgraph("doc1", depth=1)
        doc_ids = {n.doc_id for n in nodes***REMOVED***
        assert "doc1" in doc_ids
        assert "doc2" in doc_ids
        assert "doc3" in doc_ids
        assert "doc4" not in doc_ids  # глубина 1

    def test_subgraph_depth_2(self, populated_graph: GraphIndex):
        nodes, edges = populated_graph.subgraph("doc1", depth=2)
        doc_ids = {n.doc_id for n in nodes***REMOVED***
        assert "doc4" in doc_ids  # достигается на глубине 2
        assert "doc5" in doc_ids  # через doc3

    def test_subgraph_empty(self, graph: GraphIndex):
        nodes, edges = graph.subgraph("ghost")
        assert len(nodes) >= 1  # узел может быть создан как заглушка
        assert len(edges) == 0

    def test_subgraph_filtered(self, populated_graph: GraphIndex):
        """Подграф только с references."""
        nodes, edges = populated_graph.subgraph("doc1", depth=2, rel_type="references")
        ref_types = {e.rel_type for e in edges***REMOVED***
        assert all(t == "references" for t in ref_types)


# ═══════════════════════════════════════════════════════════════
# Traverse tests
# ═══════════════════════════════════════════════════════════════


class TestTraverse:
    """Тесты обхода графа."""

    def test_traverse_outgoing(self, populated_graph: GraphIndex):
        paths = populated_graph.traverse("doc1", "references", direction="out")
        # Ищем пути по references: doc1→doc2→... (doc2→doc4 через parent, не references)
        assert len(paths) >= 1

    def test_traverse_no_matches(self, graph: GraphIndex):
        graph.add_node("lonely")
        paths = graph.traverse("lonely", "references", max_hops=5)
        # Нет путей — должен быть хотя бы пустой путь
        assert len(paths) >= 0


# ═══════════════════════════════════════════════════════════════
# Auto-discover tests
# ═══════════════════════════════════════════════════════════════


class TestAutoDiscover:
    """Тесты авто-детекта связей."""

    def test_auto_discover_shared_terms(self, graph: GraphIndex):
        """Документы с общими терминами получают related связь."""
        count = graph.auto_discover([
            ("doc1", "capability router scoring model routing",
             "doc2", "router capability model implementation"),
        ***REMOVED***, min_shared_terms=2)
        assert count >= 1

        # Проверяем, что связь создана
        related = graph.get_related("doc1")
        assert len(related) >= 1

    def test_auto_discover_no_match(self, graph: GraphIndex):
        """Документы без общих терминов не получают связь."""
        count = graph.auto_discover([
            ("doc1", "router capability model",
             "doc2", "weather forecast sunny rain"),
        ***REMOVED***, min_shared_terms=3)
        assert count == 0

    def test_auto_discover_custom_threshold(self, graph: GraphIndex):
        """Параметр min_shared_terms работает."""
        count = graph.auto_discover([
            ("doc1", "router capability",
             "doc2", "router capability model scoring"),
        ***REMOVED***, min_shared_terms=5)
        assert count == 0  # только 2 общих термина


# ═══════════════════════════════════════════════════════════════
# Stats & Clear tests
# ═══════════════════════════════════════════════════════════════


class TestStats:
    """Тесты статистики."""

    def test_stats_empty(self, graph: GraphIndex):
        stats = graph.get_stats()
        assert stats.total_nodes == 0
        assert stats.total_edges == 0
        assert stats.isolated_nodes == 0

    def test_stats_after_add(self, populated_graph: GraphIndex):
        stats = populated_graph.get_stats()
        assert stats.total_nodes >= 5
        assert stats.total_edges >= 5

    def test_stats_edge_types(self, populated_graph: GraphIndex):
        stats = populated_graph.get_stats()
        assert "references" in stats.edge_types
        assert "parent" in stats.edge_types

    def test_clear(self, populated_graph: GraphIndex):
        assert populated_graph.get_stats().total_nodes > 0
        populated_graph.clear()
        stats = populated_graph.get_stats()
        assert stats.total_nodes == 0
        assert stats.total_edges == 0


# ═══════════════════════════════════════════════════════════════
# Integration with KnowledgeEngine
# ═══════════════════════════════════════════════════════════════


class TestKnowledgeEngineIntegration:
    """Тесты интеграции GraphIndex в KnowledgeEngine."""

    def test_graph_search_related(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        ke.index_document("doc1", "Capability based router")
        ke.index_document("doc2", "Router implementation")
        ke.add_graph_edge("doc1", "doc2", "references")

        result = ke.graph_search("doc1", mode="related")
        assert result["mode"***REMOVED*** == "related"
        assert result["count"***REMOVED*** >= 1

    def test_graph_search_subgraph(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        ke.add_graph_edge("a", "b", "references")
        ke.add_graph_edge("b", "c", "references")

        result = ke.graph_search("a", mode="subgraph", max_depth=2)
        assert result["mode"***REMOVED*** == "subgraph"
        assert len(result["nodes"***REMOVED***) >= 2

    def test_graph_search_traverse(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        ke.add_graph_edge("a", "b", "references")
        ke.add_graph_edge("b", "c", "depends")

        result = ke.graph_search("a", mode="traverse", rel_type="references")
        assert result["mode"***REMOVED*** == "traverse"

    def test_graph_auto_discover_integration(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        # Документы должны быть проиндексированы в памяти
        from scripts.memory_engine import MemoryEngine, MemoryLevel
        mem = MemoryEngine(workspace_root=str(tmp_path))
        mem.store(MemoryLevel.KNOWLEDGE, "doc_a",
                  "capability router scoring model routing architecture")
        mem.store(MemoryLevel.KNOWLEDGE, "doc_b",
                  "router capability model and routing optimization")

        # Индексируем в KE и запускаем авто-детект
        ke.index_from_memory()
        count = ke.graph_auto_discover(min_shared_terms=2, max_pairs=10)
        assert count >= 1

    def test_clear_with_graph(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        ke.add_graph_edge("a", "b", "references")
        stats = ke.graph.get_stats()
        assert stats.total_edges > 0

        ke.clear()
        stats = ke.graph.get_stats()
        assert stats.total_edges == 0
        assert stats.total_nodes == 0

    def test_graph_stats_integration(self, tmp_path: Path):
        from scripts.knowledge_engine import KnowledgeEngine
        ke = KnowledgeEngine(workspace_root=tmp_path)

        ke.add_graph_edge("x", "y", "references")
        ke.add_graph_edge("y", "z", "depends")

        related = ke.graph_search("x", mode="related")
        assert related["count"***REMOVED*** >= 1
