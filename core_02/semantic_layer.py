# core_02/semantic_layer.py — Semantic Layer поверх KnowledgeEngine
# Organizational Memory Engine (RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md §6)
# Reuse: scripts_01/knowledge_engine.py (KnowledgeEngine — гибридный поиск).

"""Семантический слой Organizational Memory.

Этап 3.3 из PLAN_NEXT_OPERATIONS.md. Индексирует Knowledge Objects
(title + summary + content, tags как метаданные) в существующий
KnowledgeEngine (FTS5 + TF-IDF + гибридный поиск) и предоставляет:

    index_knowledge(knowledge_id, content) -> embedding_id
    semantic_search(query, top_k=10)       -> list[(knowledge_id, score)]
    find_similar_patterns(situation_vector) -> list[PatternMatch]
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from scripts_01.knowledge_engine import KnowledgeEngine
except ImportError:  # pragma: no cover — fallback для окружений без полного проекта
    KnowledgeEngine = None  # type: ignore

from core_02.memory_store import MemoryStore


def _normalize(text: str) -> str:
    """Нормализация для токенизации: нижний регистр, латиница+кириллица."""
    return re.sub(r"[^a-zа-яё0-9\s)", " ", text.lower())


def _tokenize(text: str) -> List[str]:
    return [t for t in _normalize(text).split() if len(t) > 1]


class SemanticLayer:
    """Мост между Memory Store и KnowledgeEngine (гибридный поиск).

    Каждый Knowledge Object индексируется с doc_id = knowledge_id.
    Кэш doc_id -> knowledge_id является тождественным (doc_id и есть id KO).
    """

    def __init__(
        self,
        store: MemoryStore,
        workspace_root: Optional[str | Path] = None,
    ):
        self.store = store
        if KnowledgeEngine is None:
            raise RuntimeError(
                "SemanticLayer требует scripts_01.knowledge_engine (KnowledgeEngine)"
            )
        self.engine = KnowledgeEngine(workspace_root=workspace_root)

    # ── Индексация (§6: title + summary + content, tags → metadata) ──
    def index_knowledge(
        self,
        knowledge_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Индексировать Knowledge Object. Возвращает embedding_id (= knowledge_id).

        Если content не передан — берёт title+summary+content из Memory Store.
        """
        ko = self.store.get_knowledge(knowledge_id)
        if not ko:
            raise KeyError(f"Knowledge Object {knowledge_id} не найден в Memory Store")
        text = content if content is not None else self._ko_text(ko)
        meta = dict(metadata or {})
        meta.setdefault("tags", ",".join(ko.get("tags") or []))
        meta.setdefault("kind", ko.get("kind"))
        self.engine.index_document(knowledge_id, text, meta)
        return knowledge_id

    @staticmethod
    def _ko_text(ko: Dict[str, Any]) -> str:
        parts = [ko.get("title", ""), ko.get("summary", ""), ko.get("content", "")]
        return "\n".join(p for p in parts if p)

    def remove(self, knowledge_id: str) -> None:
        if hasattr(self.engine, "remove"):
            self.engine.remove(knowledge_id)

    # ── Поиск ────────────────────────────────────────────────────────
    def semantic_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Гибридный поиск (keyword + semantic). Возвращает [(knowledge_id, score)]."""
        results = self.engine.search(query, top_k=top_k)
        out: List[Tuple[str, float]] = []
        for r in results:
            doc_id = self._result_doc_id(r)
            if doc_id:
                out.append((doc_id, self._result_score(r)))
        return out

    def search_related(
        self,
        query: str,
        top_k: int = 5,
        max_depth: int = 1,
    ) -> Dict[str, Any]:
        """RAG-контекст: top-k гибридного поиска + граф до depth (RFC §6)."""
        hits = self.semantic_search(query, top_k=top_k)
        related: List[Dict[str, Any]] = []
        seen: set = set()
        for kid, _score in hits:
            if kid in seen:
                continue
            seen.add(kid)
            for rel in self.store.find_related(kid, max_depth=max_depth):
                rk = rel["knowledge"].get("id")
                if rk and rk not in seen:
                    seen.add(rk)
                    related.append(rel)
        return {
            "hits": [{"knowledge_id": kid, "score": sc} for kid, sc in hits],
            "related": related,
        }

    def find_similar_patterns(
        self,
        situation_vector: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Поиск паттернов/уроков по описанию ситуации (AFC: analyze)."""
        results = self.semantic_search(situation_vector, top_k=top_k)
        out: List[Dict[str, Any]] = []
        for kid, score in results:
            ko = self.store.get_knowledge(kid)
            if not ko:
                continue
            if ko.get("kind") not in ("pattern", "lesson", "anti_pattern", "guideline", "adr"):
                continue
            out.append({
                "knowledge_id": kid,
                "kind": ko.get("kind"),
                "title": ko.get("title"),
                "score": score,
                "confidence": ko.get("confidence_score"),
            })
        out.sort(key=lambda x: -x["score"])
        return out

    @staticmethod
    def _result_doc_id(result: Any) -> Optional[str]:
        # Кортеж: (doc_id, score, ...) — формат FtsIndex/TfidfIndex/LsaIndex
        if isinstance(result, (tuple, list)) and result:
            return str(result[0])
        for attr in ("doc_id", "document_id", "id"):
            v = getattr(result, attr, None)
            if v:
                return str(v)
        return None

    @staticmethod
    def _result_score(result: Any) -> float:
        if isinstance(result, (tuple, list)) and len(result) > 1:
            try:
                return float(result[1])
            except (TypeError, ValueError):
                pass
        v = getattr(result, "score", None)
        try:
            return float(v) if v is not None else 1.0
        except (TypeError, ValueError):
            return 1.0

    # ── Утилиты ──────────────────────────────────────────────────────
    def count_indexed(self) -> int:
        if hasattr(self.engine, "count"):
            try:
                return int(self.engine.count())
            except Exception:
                pass
        return 0

    def reindex_all(self) -> int:
        """Переиндексация всех Knowledge Objects (RFC §6: daily или после ~10 новых)."""
        count = 0
        for ko in self.store.query_all():
            try:
                self.index_knowledge(ko["id"])
                count += 1
            except Exception:
                continue
        return count
