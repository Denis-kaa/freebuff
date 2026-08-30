"""
rag_engine.py — RAG 2.0 Engine (Phase 7: CoWork / Companion Platform).

Улучшенный поиск поверх KnowledgeEngine с:
  1. Reciprocal Rank Fusion (RRF) — робастное слияние ранжированных списков
  2. Feature-based Re-ranking — мульти-факторное ранжирование
  3. Query Expansion — расширение запроса релевантными терминами
  4. Contextual Snippets — улучшенное выделение сниппетов

Архитектура:
  RAGEngine
    ├── search()           — унифицированный поиск с RRF fusion
    ├── hybrid_search()    — keyword + semantic + semantic_ml через RRF
    ├── rerank()           — feature-based переранжирование
    ├── expand_query()     — расширение запроса терминами из результатов
    └── rrf_merge()        — алгоритм Reciprocal Rank Fusion

Использование:
    from scripts_01.rag_engine import RAGEngine

    rag = RAGEngine()
    results = rag.search("capability router scoring", mode="hybrid_rrf")
    for r in results:
        print(f"  [{r.score:.4f}] {r.doc_id}: {r.snippet[:80]}")
"""

from __future__ import annotations

import argparse
import json
import math
}
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

RRF_K = 60
MAX_RERANK_CANDIDATES = 50
DEFAULT_TOP_K = 10


@dataclass
class RAGResult:
    """Результат поиска RAG 2.0."""

    doc_id: str
    score: float
    content: str
    snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    matched_terms: List[str] = field(default_factory=list)
    rank_sources: Dict[str, float] = field(default_factory=dict)
    features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в dict для JSON."""
        snippet = self.snippet or self.content[:200]
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        return {
            "doc_id": self.doc_id,
            "score": round(self.score, 4),
            "content": self.content,
            "snippet": snippet,
            "metadata": self.metadata,
            "matched_terms": self.matched_terms,
            "rank_sources": self.rank_sources,
            "features": self.features,
        }


@dataclass
class RAGReport:
    """Отчёт поиска RAG 2.0."""

    query: str
    mode: str
    results: List[RAGResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    expanded_query: str = ""
    query_terms: List[str] = field(default_factory=list)
    total_candidates: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в dict для JSON."""
        return {
            "query": self.query,
            "mode": self.mode,
            "results": [r.to_dict() for r in self.results],
            "total_time_ms": round(self.total_time_ms, 2),
            "expanded_query": self.expanded_query,
            "query_terms": self.query_terms,
            "total_candidates": self.total_candidates,
        }


@dataclass
class FeatureVector:
    """Признаки для re-ranking."""

    coverage: float = 0.0
    term_frequency: float = 0.0
    position: float = 0.0
    length_norm: float = 0.0
    freshness: float = 0.0
    bm25_score: float = 0.0
    semantic_score: float = 0.0

    def combined_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Взвешенная комбинация признаков.

        Default weights:
          - coverage: 0.30
          - term_frequency: 0.15
          - position: 0.20
          - length_norm: 0.10
          - freshness: 0.10
          - bm25_score: 0.10
          - semantic_score: 0.05
        """
        w = weights or {
            "coverage": 0.30,
            "term_frequency": 0.15,
            "position": 0.20,
            "length_norm": 0.10,
            "freshness": 0.10,
            "bm25_score": 0.10,
            "semantic_score": 0.05,
        }
        score = 0.0
        score += w.get("coverage", 0.0) * self.coverage
        score += w.get("term_frequency", 0.0) * self.term_frequency
        score += w.get("position", 0.0) * self.position
        score += w.get("length_norm", 0.0) * self.length_norm
        score += w.get("freshness", 0.0) * self.freshness
        score += w.get("bm25_score", 0.0) * self.bm25_score
        score += w.get("semantic_score", 0.0) * self.semantic_score
        return score

    def to_dict(self) -> Dict[str, float]:
        """Сериализация в dict."""
        return {
            "coverage": self.coverage,
            "term_frequency": self.term_frequency,
            "position": self.position,
            "length_norm": self.length_norm,
            "freshness": self.freshness,
            "bm25_score": self.bm25_score,
            "semantic_score": self.semantic_score,
        }


class RAGEngine:
    """RAG 2.0 Engine — улучшенный поиск с RRF и re-ranking.

    Строится поверх существующего KnowledgeEngine и добавляет:
      - Reciprocal Rank Fusion (keyword + semantic + semantic_ml)
      - Feature-based re-ranking (покрытие, частота, позиция, свежесть)
      - Query expansion (расширение релевантными терминами)
    """

    def __init__(self, knowledge_engine: Any = None, workspace_root: str | Path | None = None):
        if knowledge_engine is not None:
            self._ke = knowledge_engine
        else:
            from scripts_01.knowledge_engine import KnowledgeEngine

            self._ke = KnowledgeEngine(workspace_root=workspace_root)

    # ── RRF ───────────────────────────────────────────────────────────

    @staticmethod
    def rrf_merge(
        rank_lists: List[List[Tuple[str, float, str, Dict[str, Any]]]],
        k: int = 60,
        top_k: int = 10,
    ) -> List[Tuple[str, float, str, Dict[str, Any], Dict[str, float]]]:
        """Reciprocal Rank Fusion — слияние ранжированных списков.

        Args:
            rank_lists: список списков (doc_id, score, content, metadata)
            k: константа RRF (стандарт: 60)
            top_k: количество результатов

        Returns:
            Список (doc_id, rrf_score, content, metadata, rank_sources)
        """
        rrf_scores: Dict[str, float] = defaultdict(float)
        sources: Dict[str, Dict[str, float]] = defaultdict(dict)
        content_map: Dict[str, str] = {}
        meta_map: Dict[str, Dict[str, Any]] = {}

        for list_idx, rank_list in enumerate(rank_lists):
            for rank, (doc_id, score, content, metadata) in enumerate(rank_list, start=1):
                rrf_scores[doc_id] += 1.0 / (k + rank)
                sources[doc_id][f"source_{list_idx}"] = score
                if doc_id not in content_map:
                    content_map[doc_id] = content
                    meta_map[doc_id] = metadata

        merged = sorted(
            rrf_scores.items(), key=lambda kv: kv[1], reverse=True
        )[:top_k]

        return [
            (doc_id, score, content_map.get(doc_id, ""), meta_map.get(doc_id, {}), dict(sources[doc_id]))
            for doc_id, score in merged
        ]

    # ── Query Expansion ───────────────────────────────────────────────

    def expand_query(self, query: str, max_terms: int = 5, co_occurrence_window: int = 5) -> Tuple[str, List[str]]:
        """Расширяет запрос релевантными терминами.

        Стратегия:
          1. Сначала делаем keyword search по исходному запросу
          2. Извлекаем top термины из найденных документов (TF-IDF)
          3. Добавляем термины, часто встречающиеся рядом с терминами запроса
        """
        if not query.strip():
            return query, []

        query_terms = [t for t in re.findall(r"[а-яa-z0-9)+", query.lower(), re.IGNORECASE) if len(t) > 1]
        if len(query_terms) < 2:
            return query, []

        try:
            results = self._ke.search(query, top_k=10, mode="keyword")
        except Exception:
            return query, []

        # Считаем термины в найденных документах (TF-IDF-подобная эвристика).
        term_counts: Counter = Counter()
        doc_freq: Counter = Counter()
        co_occur: Counter = Counter()
        n_docs = max(1, len(results))

        for res in results:
            content = getattr(res, "content", "") or ""
            tokens = [t for t in re.findall(r"[а-яa-z0-9)+", content.lower(), re.IGNORECASE) if len(t) > 2]
            doc_terms = set(tokens)
            for t in tokens:
                term_counts[t] += 1
            for t in doc_terms:
                doc_freq[t] += 1
            # Термины рядом с терминами запроса.
            for i, token in enumerate(tokens):
                if token in query_terms:
                    for j in range(max(0, i - co_occurrence_window), min(len(tokens), i + co_occurrence_window + 1)):
                        if i != j and tokens[j] not in query_terms:
                            co_occur[tokens[j]] += 1

        # TF-IDF-эвристика: частота × обратная документная частота.
        scores: Dict[str, float] = {}
        for term, count in term_counts.items():
            if term in query_terms:
                continue
            idf = math.log(1.0 + n_docs / (1.0 + doc_freq[term]))
            scores[term] = count * idf * (1.0 + 0.5 * co_occur[term])

        extra_terms = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:max_terms]]
        expanded = query
        if extra_terms:
            expanded = f"{query} {' '.join(extra_terms)}"
        return expanded, extra_terms

    # ── Feature Extraction ────────────────────────────────────────────

    def _extract_features(
        self,
        content: str,
        query_terms: List[str],
        bm25_score: float = 0.0,
        semantic_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeatureVector:
        """Извлекает признаки для re-ranking из контента документа.

        Args:
            content: содержимое документа
            query_terms: термины запроса
            bm25_score: исходный BM25 score (из FTS5)
            semantic_score: исходный семантический score
            metadata: метаданные документа
        """
        fv = FeatureVector()
        if not content:
            return fv
        text = content.lower()
        n_terms = len(query_terms)
        if n_terms == 0:
            return fv

        # coverage: доля найденных терминов запроса.
        found = [t for t in query_terms if t in text]
        fv.coverage = len(found) / n_terms

        # term_frequency: нормированная частота терминов запроса.
        total = sum(text.count(t) for t in found)
        words = len(re.findall(r"\S+", text)) or 1
        fv.term_frequency = min(1.0, total / words * 10.0)

        # position: насколько рано встречается первый термин.
        first_positions = [text.find(t) for t in found if text.find(t) >= 0]
        if first_positions:
            first = min(first_positions)
            fv.position = max(0.0, 1.0 - first / 2000.0)
        else:
            fv.position = 0.0

        # length_norm: идеальный диапазон 1000–2000 символов → 1.0,
        # за его пределами — линейный штраф (константы из оригинального байткода).
        length = len(content)
        if length < 1000:
            fv.length_norm = length / 1000.0
        elif length <= 2000:
            fv.length_norm = 1.0
        else:
            fv.length_norm = max(0.0, 1.0 - (length - 2000) / 2000.0)

        # freshness: свежесть по created_at (в днях).
        fv.freshness = 0.5  # default (нет даты)
        meta = metadata or {}
        created = meta.get("created_at")
        if created:
            try:
                created_dt = datetime.fromisoformat(str(created))
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0
                fv.freshness = max(0.0, 1.0 - age_days / 30.0)
            except (ValueError, TypeError):
                fv.freshness = 0.5

        fv.bm25_score = max(0.0, min(1.0, bm25_score))
        fv.semantic_score = max(0.0, min(1.0, semantic_score))
        return fv

    # ── Re-ranking ────────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        candidates: List[RAGResult],
        feature_weights: Optional[Dict[str, float]] = None,
        keep_features: bool = True,
    ) -> List[RAGResult]:
        """Feature-based re-ranking кандидатов.

        Args:
            query: поисковый запрос
            candidates: список RAGResult для переранжирования
            feature_weights: веса признаков (см. FeatureVector.combined_score)
            keep_features: сохранять ли признаки в result.features

        Returns:
            Переранжированный список RAGResult.
        """
        if not candidates:
            return []
        query_terms = [t for t in re.findall(r"[а-яa-z0-9)+", query.lower(), re.IGNORECASE) if len(t) > 1]
        scored: List[Tuple[float, RAGResult]] = []
        for cand in candidates:
            fv = self._extract_features(
                content=cand.content,
                query_terms=query_terms,
                bm25_score=cand.rank_sources.get("keyword", cand.score),
                semantic_score=cand.rank_sources.get("semantic", 0.0),
                metadata=cand.metadata,
            )
            combined = fv.combined_score(feature_weights)
            if keep_features:
                cand.features = fv.to_dict()
            # Базовый score (RRF) + вес признаков.
            total = cand.score * 0.4 + combined * 0.6
            scored.append((total, cand))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        return [c for _, c in scored]

    # ── Поиск ─────────────────────────────────────────────────────────

    def hybrid_search(self, query: str, top_k: int = DEFAULT_TOP_K) -> RAGReport:
        """Быстрый hybrid search с RRF (рекомендуемый режим)."""
        return self.search(query, top_k=top_k, mode="hybrid_rrf")

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        mode: str = "hybrid_rrf",
        expand_query: bool = True,
        rerank_results: bool = True,
        fts_weight: float = 0.4,
    ) -> RAGReport:
        """Унифицированный поиск RAG 2.0.

        Args:
            query: поисковый запрос
            top_k: количество результатов
            mode: режим поиска:
              - 'keyword' — только FTS5
              - 'semantic' — только TF-IDF
              - 'hybrid' — взвешенная комбинация keyword + semantic
              - 'hybrid_rrf' — RRF keyword + semantic (рекомендуемый)
              - 'full_rrf' — RRF keyword + semantic + semantic_ml
            expand_query: расширять ли запрос
            rerank_results: переранжировать ли результаты
            fts_weight: вес FTS5 в hybrid режиме

        Returns:
            RAGReport с результатами.
        """
        start = time.time()
        report = RAGReport(query=query, mode=mode)
        if not query.strip():
            return report

        query_terms = [t for t in re.findall(r"[а-яa-z0-9)+", query.lower(), re.IGNORECASE) if len(t) > 1]
        report.query_terms = query_terms

        expanded = query
        extra_terms: List[str] = []
        if expand_query:
            expanded, extra_terms = self.expand_query(query)
            report.expanded_query = expanded
            if extra_terms:
                query_terms.extend(extra_terms)

        keyword_results: List[Tuple[str, float, str, Dict[str, Any]]] = []
        semantic_results: List[Tuple[str, float, str, Dict[str, Any]]] = []
        semantic_ml_results: List[Tuple[str, float, str, Dict[str, Any]]] = []

        try:
            if mode in ("keyword", "hybrid", "hybrid_rrf", "full_rrf"):
                for res in self._ke.search(expanded, top_k=top_k * 3, mode="keyword"):
                    keyword_results.append(
                        (res.doc_id, res.score, res.content, res.metadata)
                    )
            if mode in ("semantic", "hybrid", "hybrid_rrf", "full_rrf"):
                for res in self._ke.search(expanded, top_k=top_k * 3, mode="semantic"):
                    semantic_results.append(
                        (res.doc_id, res.score, res.content, res.metadata)
                    )
            if mode in ("semantic_ml", "full_rrf"):
                for res in self._ke.search(expanded, top_k=top_k * 3, mode="semantic_ml"):
                    semantic_ml_results.append(
                        (res.doc_id, res.score, res.content, res.metadata)
                    )
        except Exception:
            # Graceful degradation: при ошибке возвращаем пустой отчёт.
            pass

        report.total_candidates = (
            len(keyword_results) + len(semantic_results) + len(semantic_ml_results)
        )

        # Инициализация ДО веток режимов — защита от UnboundLocalError
        # при пустых результатах (контракт тестов).
        merged: List[Tuple[str, float, str, Dict[str, Any]]] = []
        rank_sources: Dict[str, Dict[str, float]] = {}

        if mode == "keyword":
            merged = [(doc_id, score, content, meta) for doc_id, score, content, meta in keyword_results]
        elif mode == "semantic":
            merged = [(doc_id, score, content, meta) for doc_id, score, content, meta in semantic_results]
        elif mode == "semantic_ml":
            merged = [(doc_id, score, content, meta) for doc_id, score, content, meta in semantic_ml_results]
        elif mode == "hybrid":
            # Взвешенная комбинация (без RRF).
            combined: Dict[str, Dict[str, Any]] = {}
            for doc_id, score, content, meta in keyword_results:
                combined[doc_id] = {"score": score * fts_weight, "content": content, "meta": meta, "kw": score}
            for doc_id, score, content, meta in semantic_results:
                if doc_id in combined:
                    combined[doc_id]["score"] += score * (1 - fts_weight)
                    combined[doc_id]["sem"] = score
                else:
                    combined[doc_id] = {"score": score * (1 - fts_weight), "content": content, "meta": meta, "sem": score}
            merged = [
                (doc_id, info["score"], info["content"], info["meta"])
                for doc_id, info in sorted(combined.items(), key=lambda kv: kv[1]["score"], reverse=True)
            ]
        elif mode in ("hybrid_rrf", "full_rrf"):
            rank_lists = [keyword_results, semantic_results]
            if mode == "full_rrf" and semantic_ml_results:
                rank_lists.append(semantic_ml_results)
            for doc_id, score, content, meta, sources in self.rrf_merge(
                rank_lists, k=RRF_K, top_k=top_k * 2
            ):
                merged.append((doc_id, score, content, meta))
                rank_sources[doc_id] = sources
        else:
            raise ValueError(f"Unknown search mode: {mode}")

        # Формируем RAGResult.
        results: List[RAGResult] = []
        seen: Set[str] = set()
        for doc_id, score, content, meta in merged:
            if doc_id in seen:
                continue
            seen.add(doc_id)
            snippet = content[:200]
            results.append(
                RAGResult(
                    doc_id=doc_id,
                    score=float(score),
                    content=content,
                    snippet=snippet,
                    metadata=dict(meta or {}),
                    matched_terms=[t for t in query_terms if t in content.lower()],
                    rank_sources=rank_sources.get(doc_id, {}),
                )
            )
            if len(results) >= top_k * 3:
                break

        # Переранжирование.
        if rerank_results and mode in ("hybrid_rrf", "full_rrf"):
            results = self.rerank(query, results[:MAX_RERANK_CANDIDATES])

        report.results = results[:top_k]
        report.total_time_ms = (time.time() - start) * 1000.0
        return report

class Colors:
    """ANSI-цвета для CLI."""

    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"


# ── CLI ───────────────────────────────────────────────────────────────

def _cmd_search(args: argparse.Namespace) -> None:
    rag = RAGEngine()
    report = rag.search(
        args.query,
        top_k=args.top_k,
        mode=args.mode,
        expand_query=not args.no_expand,
        rerank_results=not args.no_rerank,
    )
    print(f"🔍 RAG 2.0 Search (mode: {report.mode})")
    print(f"  Query:      {report.query}")
    if report.expanded_query:
        print(f"  Expanded:   {report.expanded_query}")
    print(f"  Candidates: {report.total_candidates}")
    print(f"  Time:       {report.total_time_ms:.1f} ms")
    if not report.results:
        print("📭 No results")
        return
    print(f"  Results:    {len(report.results)}")
    for i, r in enumerate(report.results, start=1):
        print(f"  {i}. [{r.score:.4f}] {r.doc_id}")
        print(f"     {r.snippet[:120]}")


def _cmd_hybrid(args: argparse.Namespace) -> None:
    rag = RAGEngine()
    report = rag.hybrid_search(args.query, top_k=args.top_k)
    print("🔍 RAG 2.0 Hybrid Search (RRF)")
    print(f"  Query:      {report.query}")
    print(f"  Candidates: {report.total_candidates}")
    print(f"  Time:       {report.total_time_ms:.1f} ms")
    if not report.results:
        print("📭 No results")
        return
    for i, r in enumerate(report.results, start=1):
        print(f"  {i}. [{r.score:.4f}] {r.doc_id}")
        print(f"     {r.snippet[:120]}")


def _cmd_rerank(args: argparse.Namespace) -> None:
    rag = RAGEngine()
    report = rag.search(args.query, top_k=args.top_k * 3, mode="hybrid_rrf", rerank_results=False)
    print("Feature-based re-ranking кандидатов.")
    print(f"  Before rerank: {len(report.results)}")
    for r in report.results[:3]:
        print(f"    [{r.score:.4f}] {r.doc_id}")
    reranked = rag.rerank(args.query, report.results)
    print(f"  After rerank: {len(reranked)}")
    for r in reranked[:args.top_k]:
        print(f"    [{r.score:.4f}] {r.doc_id}  Features: {r.features}")


def _cmd_expand(args: argparse.Namespace) -> None:
    rag = RAGEngine()
    expanded, extra = rag.expand_query(args.query, max_terms=args.max_terms)
    print("Query Expansion")
    print(f"  Original:  {args.query}")
    print(f"  Expanded:  {expanded}")
    print(f"  Extra terms: {extra}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RAG 2.0 Engine — семантический поиск с ранжированием (Phase 7: CoWork)"
    )
    parser.add_argument("--json", action="store_true", help="JSON вывод")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Поиск с RAG 2.0")
    p_search.add_argument("query", help="Поисковый запрос")
    p_search.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Количество результатов")
    p_search.add_argument("--mode", default="hybrid_rrf", help="Режим поиска")
    p_search.add_argument("--no-expand", action="store_true", help="Отключить расширение запроса")
    p_search.add_argument("--no-rerank", action="store_true", help="Отключить переранжирование")

    p_hybrid = sub.add_parser("hybrid", help="Быстрый hybrid search (RRF)")
    p_hybrid.add_argument("query", help="Поисковый запрос")
    p_hybrid.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Количество результатов")

    p_rerank = sub.add_parser("rerank", help="Переранжирование результатов")
    p_rerank.add_argument("query", help="Поисковый запрос")
    p_rerank.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Количество результатов")

    p_expand = sub.add_parser("expand", help="Расширение запроса")
    p_expand.add_argument("query", help="Поисковый запрос")
    p_expand.add_argument("--max-terms", type=int, default=5, help="Максимум дополнительных терминов")

    args = parser.parse_args()

    handlers = {
        "search": _cmd_search,
        "hybrid": _cmd_hybrid,
        "rerank": _cmd_rerank,
        "expand": _cmd_expand,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
