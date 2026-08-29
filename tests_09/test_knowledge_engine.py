#!/usr/bin/env python3
"""
Tests for Knowledge Engine (scripts_01/knowledge_engine.py).

Tests:
  - Tokenizer: tokenization, stop words, snippets
  - FtsIndex: CRUD, search, clear
  - TfidfIndex: indexing, search, persistence
  - KnowledgeEngine: unified search (keyword, semantic, hybrid)
  - KnowledgeEngine: index from memory, rebuild, stats
  - CLI commands
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import pytest
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts_01.knowledge_engine import (
    KnowledgeEngine, KnowledgeEngineStats,
    FtsIndex, TfidfIndex,
    Tokenizer, SearchResult,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Временная директория для тестов."""
    d = tmp_path / "ke_test"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def fts_index(tmp_dir: Path) -> FtsIndex:
    """FTS5 индекс во временной директории."""
    db_path = tmp_dir / "test_fts.db"
    return FtsIndex(db_path)


@pytest.fixture
def tfidf_index(tmp_dir: Path) -> TfidfIndex:
    """TF-IDF индекс во временной директории."""
    return TfidfIndex(
        vectors_path=tmp_dir / "vectors.npy",
        vocab_path=tmp_dir / "vocab.json",
        meta_path=tmp_dir / "metadata.json",
    )


@pytest.fixture
def knowledge_engine(tmp_dir: Path) -> KnowledgeEngine:
    """Knowledge Engine во временной директории."""
    return KnowledgeEngine(workspace_root=tmp_dir)


# ═══════════════════════════════════════════════════════════════
# Tokenizer tests
# ═══════════════════════════════════════════════════════════════


class TestTokenizer:
    """Тесты токенизатора."""

    def test_tokenize_simple(self):
        tokens = Tokenizer.tokenize("hello world test")
        assert len(tokens) >= 3
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_russian(self):
        tokens = Tokenizer.tokenize("привет мир тест")
        assert "привет" in tokens
        assert "мир" in tokens

    def test_tokenize_stop_words_removed(self):
        tokens = Tokenizer.tokenize("the and of this is a test")
        assert "test" in tokens
        assert "the" not in tokens, "Stop word 'the' should be removed"
        assert "and" not in tokens, "Stop word 'and' should be removed"

    def test_tokenize_code_identifiers(self):
        tokens = Tokenizer.tokenize("def test_function(param_name): return result_value")
        assert "test_function" in tokens
        assert "param_name" in tokens
        assert "result_value" in tokens
        assert "def" not in tokens, "Keyword 'def' should be removed"

    def test_tokenize_short_tokens_filtered(self):
        tokens = Tokenizer.tokenize("a b c test")
        assert "test" in tokens
        assert "a" not in tokens, "Single char 'a' should be filtered"
        assert "b" not in tokens

    def test_tokenize_mixed_language(self):
        tokens = Tokenizer.tokenize("capability роутер scoring")
        assert "capability" in tokens
        assert "роутер" in tokens
        assert "scoring" in tokens

    def test_extract_snippet(self):
        text = "This is a long text about capability-based routing with scoring system"
        snippet = Tokenizer.extract_snippet(text, ["routing"***REMOVED***)
        assert "routing" in snippet
        assert len(snippet) > 10

    def test_extract_snippet_short_text(self):
        text = "Short text"
        snippet = Tokenizer.extract_snippet(text, ["missing"***REMOVED***)
        assert len(snippet) > 0
        assert "Short" in snippet


# ═══════════════════════════════════════════════════════════════
# FtsIndex tests
# ═══════════════════════════════════════════════════════════════


class TestFtsIndex:
    """Тесты FTS5 индекса."""

    def test_index_and_search(self, fts_index: FtsIndex):
        fts_index.index("doc1", "capability based router with scoring")
        fts_index.index("doc2", "memory engine with five levels")
        fts_index.index("doc3", "context builder unified context")

        results = fts_index.search("router")
        assert len(results) >= 1
        assert results[0***REMOVED***[0***REMOVED*** == "doc1"

    def test_search_no_results(self, fts_index: FtsIndex):
        results = fts_index.search("nonexistent_query_xyz")
        assert len(results) == 0

    def test_search_multiple_terms(self, fts_index: FtsIndex):
        fts_index.index("doc1", "capability router scoring")
        fts_index.index("doc2", "memory engine architecture")

        results = fts_index.search("engine architecture")
        assert len(results) >= 1
        assert results[0***REMOVED***[0***REMOVED*** == "doc2"

    def test_remove_document(self, fts_index: FtsIndex):
        fts_index.index("doc1", "test content")
        assert fts_index.count() == 1

        removed = fts_index.remove("doc1")
        assert removed is True
        assert fts_index.count() == 0

    def test_remove_nonexistent(self, fts_index: FtsIndex):
        removed = fts_index.remove("nonexistent")
        assert removed is False

    def test_clear(self, fts_index: FtsIndex):
        fts_index.index("doc1", "test")
        fts_index.index("doc2", "test")
        assert fts_index.count() == 2

        fts_index.clear()
        assert fts_index.count() == 0

    def test_count_empty(self, fts_index: FtsIndex):
        assert fts_index.count() == 0

    def test_metadata_stored(self, fts_index: FtsIndex):
        fts_index.index("doc1", "test content", {"title": "Test Doc", "source": "test"***REMOVED***)
        results = fts_index.search("test")
        assert len(results) >= 1
        doc_id, score, content, meta = results[0***REMOVED***
        assert meta.get("title") == "Test Doc"
        assert meta.get("source") == "test"

    def test_update_document(self, fts_index: FtsIndex):
        fts_index.index("doc1", "old content")
        fts_index.index("doc1", "new updated content")
        assert fts_index.count() == 1
        results = fts_index.search("updated")
        assert len(results) >= 1


# ═══════════════════════════════════════════════════════════════
# TfidfIndex tests
# ═══════════════════════════════════════════════════════════════


class TestTfidfIndex:
    """Тесты TF-IDF векторного индекса."""

    def test_index_and_search(self, tfidf_index: TfidfIndex):
        tfidf_index.index_documents([
            ("doc1", "capability based router with scoring system python"),
            ("doc2", "memory engine with five levels working archive"),
            ("doc3", "context builder unified memory stream task"),
        ***REMOVED***)

        results = tfidf_index.search("router scoring")
        assert len(results) >= 1
        assert results[0***REMOVED***[0***REMOVED*** == "doc1"

    def test_search_semantic_related(self, tfidf_index: TfidfIndex):
        """TF-IDF находит семантически близкие документы (по общим токенам)."""
        tfidf_index.index_documents([
            ("doc1", "capability router model route routing"),
            ("doc2", "memory storage context session archive"),
        ***REMOVED***)

        results = tfidf_index.search("router capability")
        assert len(results) >= 1
        # doc1 имеет больше общих терминов с запросом
        top_doc = results[0***REMOVED***[0***REMOVED***
        assert top_doc == "doc1"

    def test_search_empty_index(self, tfidf_index: TfidfIndex):
        results = tfidf_index.search("test")
        assert len(results) == 0

    def test_is_empty(self, tfidf_index: TfidfIndex):
        assert tfidf_index.is_empty() is True
        tfidf_index.index_documents([("doc1", "test content")***REMOVED***)
        assert tfidf_index.is_empty() is False

    def test_count(self, tfidf_index: TfidfIndex):
        assert tfidf_index.count() == 0
        tfidf_index.index_documents([("doc1", "test"), ("doc2", "test")***REMOVED***)
        assert tfidf_index.count() == 2

    def test_clear(self, tfidf_index: TfidfIndex):
        tfidf_index.index_documents([("doc1", "test")***REMOVED***)
        assert tfidf_index.count() == 1
        tfidf_index.clear()
        assert tfidf_index.count() == 0

    def test_persistence(self, tmp_dir: Path):
        """Проверяет сохранение и загрузку индекса."""
        # Создаём и наполняем
        idx1 = TfidfIndex(
            vectors_path=tmp_dir / "vectors.npy",
            vocab_path=tmp_dir / "vocab.json",
            meta_path=tmp_dir / "metadata.json",
        )
        idx1.index_documents([("doc1", "test content router")***REMOVED***)
        assert idx1.count() == 1

        # Создаём новый экземпляр (должен загрузить с диска)
        idx2 = TfidfIndex(
            vectors_path=tmp_dir / "vectors.npy",
            vocab_path=tmp_dir / "vocab.json",
            meta_path=tmp_dir / "metadata.json",
        )
        assert idx2.count() == 1
        results = idx2.search("router")
        assert len(results) >= 1

    def test_score_relevance(self, tfidf_index: TfidfIndex):
        """Более релевантный документ получает выше score."""
        tfidf_index.index_documents([
            ("relevant", "router capability routing scoring system"),
            ("irrelevant", "weather forecast sunny cloudy rain"),
        ***REMOVED***)

        results = tfidf_index.search("router scoring")
        assert len(results) >= 1
        # relevant должен иметь более высокий score
        relevant_score = None
        irrelevant_score = None
        for doc_id, score, _ in results:
            if doc_id == "relevant":
                relevant_score = score
            elif doc_id == "irrelevant":
                irrelevant_score = score

        if relevant_score is not None and irrelevant_score is not None:
            assert relevant_score > irrelevant_score, \
                f"Relevant doc should score higher: {relevant_score***REMOVED*** vs {irrelevant_score***REMOVED***"


# ═══════════════════════════════════════════════════════════════
# KnowledgeEngine tests
# ═══════════════════════════════════════════════════════════════


class TestKnowledgeEngine:
    """Тесты унифицированного API."""

    def test_index_and_search_keyword(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document(
            "doc1", "capability based router with scoring system"
        )
        knowledge_engine.index_document(
            "doc2", "memory engine with five storage levels"
        )

        results = knowledge_engine.search("router", mode="keyword")
        assert len(results) >= 1
        assert results[0***REMOVED***.doc_id == "doc1"

    def test_search_semantic(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document(
            "doc1", "capability router routing model"
        )
        knowledge_engine.index_document(
            "doc2", "weather sunny cloudy rainy cold"
        )

        results = knowledge_engine.search("routing capabilities", mode="semantic")
        assert len(results) >= 1
        assert results[0***REMOVED***.doc_id == "doc1"

    def test_search_hybrid(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document(
            "doc1", "capability based router scoring system"
        )
        knowledge_engine.index_document(
            "doc2", "memory engine with storage levels"
        )

        results = knowledge_engine.search("router capability", mode="hybrid")
        assert len(results) >= 1
        assert results[0***REMOVED***.doc_id == "doc1"

    def test_search_no_results(self, knowledge_engine: KnowledgeEngine):
        results = knowledge_engine.search("nonexistent_xyz_123")
        assert len(results) == 0

    def test_search_empty_query(self, knowledge_engine: KnowledgeEngine):
        results = knowledge_engine.search("")
        assert len(results) == 0

    def test_search_whitespace_query(self, knowledge_engine: KnowledgeEngine):
        results = knowledge_engine.search("   ")
        assert len(results) == 0

    def test_search_capabilities(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document(
            "router_doc", "capability router scoring routing model selection",
            metadata={"source": "memory/project/router", "doc_type": "text"***REMOVED***,
        )
        caps = knowledge_engine.search_capabilities("router scoring", top_k=3)
        assert len(caps) >= 1

    def test_get_stats_empty(self, knowledge_engine: KnowledgeEngine):
        stats = knowledge_engine.get_stats()
        assert stats.total_docs == 0
        assert stats.fts_docs == 0
        assert stats.vector_docs == 0

    def test_get_stats_after_index(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document("doc1", "test content")
        stats = knowledge_engine.get_stats()
        assert stats.total_docs >= 1
        assert stats.fts_docs >= 1

    def test_clear(self, knowledge_engine: KnowledgeEngine):
        knowledge_engine.index_document("doc1", "test content")
        assert knowledge_engine.get_stats().total_docs >= 1
        knowledge_engine.clear()
        assert knowledge_engine.get_stats().total_docs == 0

    def test_snippet_generation(self, knowledge_engine: KnowledgeEngine):
        long_text = "This is a very long document about " + "capability router ".join(
            str(i) for i in range(20)
        )
        knowledge_engine.index_document("doc1", long_text)

        results = knowledge_engine.search("capability router")
        assert len(results) >= 1
        assert results[0***REMOVED***.snippet is not None
        assert len(results[0***REMOVED***.snippet) > 0


# ═══════════════════════════════════════════════════════════════
# KnowledgeEngine indexing from memory
# ═══════════════════════════════════════════════════════════════


class TestMemoryIntegration:
    """Тесты интеграции с Memory Engine."""

    def test_index_from_memory_empty(self, knowledge_engine: KnowledgeEngine):
        """index_from_memory() на пустой памяти не падает."""
        count = knowledge_engine.index_from_memory()
        assert count == 0

    def test_index_from_memory_with_stored(self, knowledge_engine: KnowledgeEngine, tmp_dir: Path):
        """index_from_memory() индексирует записи из Memory Engine."""
        # Сначала сохраняем в Memory Engine
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType

        mem = MemoryEngine(workspace_root=str(tmp_dir))
        mem.store(
            MemoryLevel.KNOWLEDGE, "test_doc",
            "knowledge about capability router scoring",
            content_type=ContentType.TEXT,
            summary="Test knowledge document",
        )

        # Индексируем
        count = knowledge_engine.index_from_memory()
        assert count >= 1, "Should index at least 1 document from memory"

        # Ищем
        results = knowledge_engine.search("capability router")
        assert len(results) >= 1

    def test_rebuild_index(self, knowledge_engine: KnowledgeEngine, tmp_dir: Path):
        """rebuild_index() перестраивает индекс с нуля."""
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel
        from unittest.mock import patch

        mem = MemoryEngine(workspace_root=str(tmp_dir))
        mem.store(MemoryLevel.KNOWLEDGE, "doc1", "router capability content")
        mem.store(MemoryLevel.KNOWLEDGE, "doc2", "memory engine content")

        # v5.189.10 speedup: fit_semantic (SVD) стоит 17.8s на этом устройстве;
        # контракт rebuild-теста — FTS/TF-IDF счётчики (count/total_docs),
        # они не зависят от SVD-слоя (покрыт test_search_semantic отдельно).
        with patch.object(KnowledgeEngine, "fit_semantic", return_value=None):
            count = knowledge_engine.rebuild_index()
        assert count >= 2
        assert knowledge_engine.get_stats().total_docs >= 2


# ═══════════════════════════════════════════════════════════════
# Result type tests
# ═══════════════════════════════════════════════════════════════


class TestSearchResult:
    """Тесты SearchResult dataclass."""

    def test_snippet_from_content(self):
        r = SearchResult(
            doc_id="test",
            score=0.95,
            content="This is a long content for testing snippet generation",
        )
        assert r.snippet is not None
        assert len(r.snippet) > 0

    def test_custom_snippet(self):
        r = SearchResult(
            doc_id="test",
            score=0.95,
            content="Some content",
            snippet="Custom snippet",
        )
        assert r.snippet == "Custom snippet"

    def test_matched_terms_default(self):
        r = SearchResult(doc_id="test", score=0.5, content="content")
        assert r.matched_terms == [***REMOVED***
