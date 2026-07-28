#!/usr/bin/env python3
"""
knowledge_engine.py — Knowledge Engine для Buffy Project.

Трёхуровневый поиск по знаниям:

  1. KEYWORD   → SQLite FTS5 (BM25) — быстрый полнотекстовый поиск
  2. SEMANTIC  → TF-IDF + cosine similarity (numpy) — смысловой поиск
  3. HYBRID    → Взвешенная комбинация keyword + semantic

Хранилище:
  context/knowledge/index.db      — SQLite (FTS5 + метаданные)
  context/knowledge/vectors.npy   — TF-IDF векторы (numpy)
  context/knowledge/vocab.json    — Словарь термин→id

Использование:
    from scripts.knowledge_engine import KnowledgeEngine

    ke = KnowledgeEngine()
    ke.index_document("router-v2", "Capability-based router with scoring...")
    results = ke.search("capability router scoring")
    for r in results:
        print(f"  [{r.score:.3f***REMOVED******REMOVED*** {r.doc_id***REMOVED***: {r.snippet[:80***REMOVED******REMOVED***")
"""

from __future__ import annotations

import json
import math
import os
***REMOVED***
import sqlite3
import threading
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# Lazy import for GraphIndex (to avoid circular imports)
_GraphIndex = None
def _get_graph_index():
    global _GraphIndex
    if _GraphIndex is None:
        from scripts.graph_index import GraphIndex as _GI
        _GraphIndex = _GI
    return _GraphIndex


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = "context/knowledge/index.db"
DEFAULT_VECTORS_PATH = "context/knowledge/vectors.npy"
DEFAULT_VOCAB_PATH = "context/knowledge/vocab.json"
DEFAULT_META_PATH = "context/knowledge/metadata.json"

# Стоп-слова (технические, для кода и документации)
STOP_WORDS: Set[str***REMOVED*** = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "by", "with", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "we", "our", "you", "your", "he", "she", "his", "her", "him",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very",
    "just", "about", "above", "after", "again", "all", "also", "any",
    "because", "before", "between", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same",
    "into", "over", "under", "up", "out", "off", "down",
    "using", "used", "use", "like", "make", "made", "get", "got",
    "one", "two", "three", "first", "last", "new", "old", "next",
    "here", "there", "where", "when", "what", "which", "who", "whom",
    "how", "why", "let", "set", "put", "take", "give", "show",
    "within", "without", "along", "around", "through", "during",
    "while", "ever", "never", "always", "often", "usually",
    # Русские стоп-слова
    "и", "в", "во", "на", "с", "со", "у", "о", "об", "от", "за",
    "по", "под", "над", "к", "ко", "до", "для", "через", "между",
    "это", "этот", "эта", "эти", "тот", "та", "те", "все", "всё",
    "весь", "вся", "всех", "всем", "всеми", "который", "которая",
    "которые", "которого", "которой", "которых", "что", "чтобы",
    "как", "так", "такой", "такая", "такие", "такого", "такой",
    "но", "а", "или", "да", "нет", "не", "ни", "без", "если",
    "бы", "быть", "есть", "был", "была", "было", "были",
    "из", "из-за", "изо", "перед", "при", "про", "через",
    "его", "её", "ее", "их", "его", "её", "мне", "меня", "мной",
    "нам", "нас", "нами", "вам", "вас", "вами", "ему", "ей",
    "им", "них", "нему", "неё", "нее", "ними",
    "потому", "поэтому", "также", "тоже", "ещё", "еще",
    "уже", "ещё", "вот", "вон", "тут", "там", "здесь",
    "можно", "нужно", "надо", "нельзя", "должен", "должна",
    "должны", "может", "могут", "можем", "можете", "могу",
    "является", "являются", "называется", "называют",
    # Код-специфичные
    "def", "class", "return", "import", "from", "self", "if", "else",
    "elif", "for", "while", "try", "except", "finally", "with",
    "as", "pass", "break", "continue", "raise", "yield", "lambda",
    "true", "false", "none", "null", "undefined", "const", "let",
    "var", "function", "async", "await", "export", "default",
    "extends", "implements", "interface", "type", "typeof",
    "instanceof", "new", "delete", "void", "typeof",
    "int", "str", "bool", "float", "list", "dict", "tuple", "set",
    "print", "len", "range", "map", "filter", "sorted", "reversed",
    "enumerate", "zip", "open", "read", "write", "close",
    "assert", "del", "global", "nonlocal",
***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class SearchResult:
    """Результат поиска."""
    doc_id: str
    score: float
    content: str
    snippet: str = ""
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    matched_terms: List[str***REMOVED*** = field(default_factory=list)

    def __post_init__(self):
        if not self.snippet:
            self.snippet = self.content[:200***REMOVED***.replace("\n", " ").strip()


@dataclass
class Document:
    """Документ для индексации."""
    doc_id: str
    content: str
    metadata: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ═══════════════════════════════════════════════════════════════
# Tokenizer
# ═══════════════════════════════════════════════════════════════


class Tokenizer:
    """Токенизатор для технических текстов и кода."""

    @staticmethod
    def tokenize(text: str) -> List[str***REMOVED***:
        """Разбивает текст на токены, убирает стоп-слова и короткие токены."""
        # Приводим к нижнему регистру
        text = text.lower()

        # Извлекаем слова (буквы, цифры, подчёркивания, дефисы)
        # Для кода: сохраняем snake_case, kebab-case, CamelCase как один токен
        tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9***REMOVED***[\w\-***REMOVED***{1,***REMOVED***", text)

        # Фильтруем
        result = [***REMOVED***
        for token in tokens:
            token = token.strip("_-")
            if len(token) < 2:
                continue
            if token in STOP_WORDS:
                continue
            if token.isdigit():
                continue
            result.append(token)

        return result

    @staticmethod
    def extract_snippet(text: str, query_terms: List[str***REMOVED***, context_chars: int = 150) -> str:
        """Извлекает сниппет с подсветкой релевантных терминов."""
        if not text or not text.strip():
            return "(semantic match — content not stored in vector index)"

        text_lower = text.lower()
        best_pos = -1
        best_count = 0

        # Ищем позицию с максимальным количеством совпадений
        for i, term in enumerate(query_terms):
            pos = text_lower.find(term.lower())
            if pos >= 0:
                # Считаем, сколько терминов рядом
                count = sum(
                    1 for t in query_terms
                    if t.lower() in text_lower[
                        max(0, pos - context_chars):
                        pos + context_chars
                    ***REMOVED***
                )
                if count > best_count:
                    best_count = count
                    best_pos = pos

        if best_pos < 0:
            return text[:200***REMOVED***.replace("\n", " ").strip()

        start = max(0, best_pos - context_chars // 2)
        end = min(len(text), best_pos + context_chars)

        snippet = text[start:end***REMOVED***.replace("\n", " ")
        if start > 0:
            snippet = "... " + snippet
        if end < len(text):
            snippet = snippet + " ..."

        return snippet.strip()


# ═══════════════════════════════════════════════════════════════
# FTS5 Index (keyword search)
# ═══════════════════════════════════════════════════════════════


class FtsIndex:
    """SQLite FTS5 индекс для быстрого полнотекстового поиска."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Создаёт таблицы и FTS5 индекс."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
                USING fts5(content, doc_id UNINDEXED, tokenize='porter unicode61')
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS doc_meta (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    doc_type TEXT DEFAULT 'text',
                    created_at TEXT,
                    updated_at TEXT,
                    char_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ── CRUD ──────────────────────────────────────────────

    def index(self, doc_id: str, content: str, metadata: Dict[str, Any***REMOVED*** | None = None) -> None:
        """Индексирует документ в FTS5."""
        meta = metadata or {***REMOVED***
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with self._connect() as conn:
                # Удаляем старую версию
                conn.execute("DELETE FROM docs_fts WHERE doc_id = ?", (doc_id,))
                conn.execute("DELETE FROM doc_meta WHERE doc_id = ?", (doc_id,))

                # Вставляем в FTS
                conn.execute(
                    "INSERT INTO docs_fts (doc_id, content) VALUES (?, ?)",
                    (doc_id, content),
                )

                # Метаданные
                conn.execute(
                    """INSERT INTO doc_meta
                       (doc_id, title, source, doc_type, created_at, updated_at, char_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        doc_id,
                        meta.get("title", ""),
                        meta.get("source", ""),
                        meta.get("doc_type", "text"),
                        meta.get("created_at", now),
                        now,
                        len(content),
                    ),
                )
                conn.commit()

    def remove(self, doc_id: str) -> bool:
        """Удаляет документ из индекса."""
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM docs_fts WHERE doc_id = ?", (doc_id,))
                conn.execute("DELETE FROM doc_meta WHERE doc_id = ?", (doc_id,))
                conn.commit()
                return cur.rowcount > 0

    def search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[str, float, str, Dict[str, Any***REMOVED******REMOVED******REMOVED***:
        """Поиск по FTS5. Возвращает (doc_id, score, content, metadata)."""
        # Экранируем спецсимволы FTS5
        safe_query = self._sanitize_query(query)
        if not safe_query:
            return [***REMOVED***

        with self._lock:
            with self._connect() as conn:
                try:
                    rows = conn.execute(
                        """SELECT d.doc_id, d.rank, d.content, m.title, m.source, m.doc_type
                           FROM docs_fts d
                           LEFT JOIN doc_meta m ON d.doc_id = m.doc_id
                           WHERE docs_fts MATCH ?
                           ORDER BY rank
                           LIMIT ?""",
                        (safe_query, top_k),
                    ).fetchall()
                except sqlite3.OperationalError:
                    # FTS5 синтаксическая ошибка — пробуем как phrase
                    try:
                        safe_query = f'"{safe_query***REMOVED***"'
                        rows = conn.execute(
                            """SELECT d.doc_id, d.rank, d.content, m.title, m.source, m.doc_type
                               FROM docs_fts d
                               LEFT JOIN doc_meta m ON d.doc_id = m.doc_id
                               WHERE docs_fts MATCH ?
                               ORDER BY rank
                               LIMIT ?""",
                            (safe_query, top_k),
                        ).fetchall()
                    except sqlite3.OperationalError:
                        return [***REMOVED***

        results = [***REMOVED***
        for doc_id, rank, content, title, source, doc_type in rows:
            # FTS5 rank — отрицательное число (чем меньше, тем лучше)
            # Конвертируем в score [0, 1***REMOVED***
            score = max(0.0, min(1.0, -rank / 100.0)) if rank < 0 else 0.5
            meta = {
                "title": title or "",
                "source": source or "",
                "doc_type": doc_type or "text",
                "search_method": "fts5",
            ***REMOVED***
            results.append((doc_id, score, content, meta))

        return results

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Экранирует спецсимволы FTS5.

        Использует пробельное разделение (OR-like поведение),
        чтобы не требовать ALL terms.
        """
        # Удаляем спецсимволы FTS5
        special = '^()*":<>~+-'
        for ch in special:
            query = query.replace(ch, " ")
        # Схлопываем пробелы — пробел = OR в FTS5
        query = " ".join(
            t for t in query.split() if len(t) > 1
        )
        return query

    def count(self) -> int:
        """Количество проиндексированных документов."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()
            return row[0***REMOVED*** if row else 0

    def clear(self) -> None:
        """Очищает индекс."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM docs_fts")
                conn.execute("DELETE FROM doc_meta")
                conn.commit()


# ═══════════════════════════════════════════════════════════════
# TF-IDF Vector Index (semantic search)
# ═══════════════════════════════════════════════════════════════


class TfidfIndex:
    """TF-IDF векторный индекс для семантического поиска.

    Хранит:
      - vocab.json:  словарь {термин: id***REMOVED***
      - vectors.npy: матрица документ-термин (n_docs × n_terms), float32
      - metadata.json: список doc_id в порядке строк матрицы
    """

    def __init__(
        self,
        vectors_path: Path,
        vocab_path: Path,
        meta_path: Path,
    ):
        self._vectors_path = vectors_path
        self._vocab_path = vocab_path
        self._meta_path = meta_path
        self._lock = threading.Lock()

        # In-memory кэш
        self._vocab: Dict[str, int***REMOVED*** = {***REMOVED***       # термин → id
        self._idf: np.ndarray | None = None     # IDF веса
        self._vectors: np.ndarray | None = None  # матрица документов
        self._doc_ids: List[str***REMOVED*** = [***REMOVED***            # документы
        self._dirty: bool = False                # нужно ли сохранять

        self._load()

    # ── Персистентность ──────────────────────────────────

    def _load(self) -> None:
        """Загружает индексы с диска."""
        if self._vocab_path.exists():
            with open(self._vocab_path, "r", encoding="utf-8") as f:
                self._vocab = json.load(f)

        if self._vectors_path.exists():
            try:
                self._vectors = np.load(str(self._vectors_path))
            except Exception:
                self._vectors = None

        if self._meta_path.exists():
            with open(self._meta_path, "r", encoding="utf-8") as f:
                self._doc_ids = json.load(f)

        # IDF из частоты документов
        if self._vocab and self._vectors is not None:
            n_docs = len(self._doc_ids)
            df = np.bincount(
                (self._vectors > 0).sum(axis=0).astype(int),
                minlength=len(self._vocab),
            )
            self._idf = np.log((n_docs + 1) / (df + 1)) + 1

    def _save(self) -> None:
        """Сохраняет индексы на диск."""
        if not self._dirty:
            return

        self._vectors_path.parent.mkdir(parents=True, exist_ok=True)

        if self._vectors is not None:
            np.save(str(self._vectors_path), self._vectors)

        with open(self._vocab_path, "w", encoding="utf-8") as f:
            json.dump(self._vocab, f, ensure_ascii=False, indent=2)

        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self._doc_ids, f, ensure_ascii=False, indent=2)

        self._dirty = False

    # ── Индексация ───────────────────────────────────────

    def index_documents(
        self, docs: List[Tuple[str, str***REMOVED******REMOVED***, rebuild: bool = False
    ) -> None:
        """Индексирует список документов (doc_id, content).

        Если rebuild=True — перестраивает весь индекс с нуля.
        Иначе — добавляет/обновляет документы.
        """
        if rebuild:
            with self._lock:
                self._vocab = {***REMOVED***
                self._idf = None
                self._vectors = None
                self._doc_ids = [***REMOVED***
                self._dirty = True

        # 1. Токенизируем все документы
        tokenized: List[Tuple[str, Counter***REMOVED******REMOVED*** = [***REMOVED***
        for doc_id, content in docs:
            tokens = Tokenizer.tokenize(content)
            tokenized.append((doc_id, Counter(tokens)))

        with self._lock:
            # 2. Строим/обновляем словарь
            existing_ids = set(self._doc_ids)

            for doc_id, counter in tokenized:
                # Удаляем старую версию
                if doc_id in existing_ids:
                    self._remove_doc(doc_id)
                    existing_ids.discard(doc_id)

                for token in counter:
                    if token not in self._vocab:
                        self._vocab[token***REMOVED*** = len(self._vocab)

            # 3. Строим матрицу
            n_docs = len(self._doc_ids) + len(tokenized)
            n_terms = len(self._vocab)
            matrix = np.zeros((n_docs, n_terms), dtype=np.float32)
            new_doc_ids: List[str***REMOVED*** = [***REMOVED***

            # Старые документы — их векторы могут быть короче новой матрицы
            old_n_terms = self._vectors.shape[1***REMOVED*** if self._vectors is not None else 0
            for i, doc_id in enumerate(self._doc_ids):
                if doc_id in existing_ids:
                    # Копируем только существующие колонки (новые = 0)
                    if old_n_terms > 0:
                        matrix[i, :old_n_terms***REMOVED*** = self._vectors[i***REMOVED***
                    new_doc_ids.append(doc_id)

            # Новые документы
            start_idx = len(new_doc_ids)
            for i, (doc_id, counter) in enumerate(tokenized):
                row = start_idx + i
                for token, count in counter.items():
                    if token in self._vocab:
                        col = self._vocab[token***REMOVED***
                        matrix[row, col***REMOVED*** = count
                new_doc_ids.append(doc_id)

            self._vectors = matrix
            self._doc_ids = new_doc_ids

            # 4. Пересчитываем IDF
            n_docs_actual = len(self._doc_ids)
            if n_docs_actual > 0 and n_terms > 0:
                df = np.bincount(
                    (self._vectors > 0).sum(axis=0).astype(int),
                    minlength=n_terms,
                )
                self._idf = np.log((n_docs_actual + 1) / (df + 1)) + 1

            self._dirty = True

        self._save()

    def _remove_doc(self, doc_id: str) -> None:
        """Удаляет документ из внутренних структур."""
        if doc_id in self._doc_ids:
            idx = self._doc_ids.index(doc_id)
            self._doc_ids.pop(idx)
            if self._vectors is not None:
                self._vectors = np.delete(self._vectors, idx, axis=0)
            self._dirty = True

    # ── Поиск ────────────────────────────────────────────

    def search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[str, float, List[str***REMOVED******REMOVED******REMOVED***:
        """Векторный поиск по TF-IDF косинусной близости.

        Returns:
            Список (doc_id, score, matched_terms)
        """
        if self._vectors is None or len(self._doc_ids) == 0:
            return [***REMOVED***

        # 1. Токенизируем запрос
        query_tokens = Tokenizer.tokenize(query)
        if not query_tokens:
            return [***REMOVED***

        # 2. Строим вектор запроса (TF-IDF)
        q_counter = Counter(query_tokens)
        q_vec = np.zeros(len(self._vocab), dtype=np.float32)

        for token, count in q_counter.items():
            if token in self._vocab:
                col = self._vocab[token***REMOVED***
                # TF = log(1 + count)
                tf = math.log(1 + count)
                # IDF
                idf = self._idf[col***REMOVED*** if self._idf is not None else 1.0
                q_vec[col***REMOVED*** = tf * idf

        # 3. TF-IDF для документов
        if self._idf is not None:
            doc_vectors = self._vectors * self._idf
        else:
            doc_vectors = self._vectors

        # 4. Косинусная близость
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-10:
            return [***REMOVED***

        q_unit = q_vec / q_norm
        doc_norms = np.linalg.norm(doc_vectors, axis=1)
        doc_norms = np.where(doc_norms < 1e-10, 1.0, doc_norms)
        doc_unit = doc_vectors / doc_norms[:, np.newaxis***REMOVED***

        similarities = doc_unit @ q_unit

        # 5. Топ-K
        top_indices = np.argsort(similarities)[-top_k:***REMOVED***[::-1***REMOVED***

        results = [***REMOVED***
        for idx in top_indices:
            score = float(similarities[idx***REMOVED***)
            if score < 0.01:
                continue
            doc_id = self._doc_ids[idx***REMOVED***

            # Какие термины совпали
            matched = [
                token for token in q_counter
                if token in self._vocab
            ***REMOVED***

            results.append((doc_id, score, matched))

        return results

    def is_empty(self) -> bool:
        """Пуст ли индекс."""
        return len(self._doc_ids) == 0

    def count(self) -> int:
        """Количество документов."""
        return len(self._doc_ids)

    def clear(self) -> None:
        """Очищает индекс."""
        with self._lock:
            self._vocab = {***REMOVED***
            self._idf = None
            self._vectors = None
            self._doc_ids = [***REMOVED***
            self._dirty = True
        self._save()


# ═══════════════════════════════════════════════════════════════
# Semantic Index (torch SVD — LSA embeddings)
# ═══════════════════════════════════════════════════════════════


class SemanticIndex:
    """Семантический индекс на основе LSA (Latent Semantic Analysis).

    Использует truncated SVD через torch для создания плотных семантических
    эмбеддингов из разреженных TF-IDF векторов.

    Принцип:
      TF-IDF матрица (n_docs × n_terms)
      → torch SVD → U·Σ·V^T
      → truncated to k компонент
      → Document embeddings: Uₖ · Σₖ
      → Query projection: q · Vₖᵀ · Σₖ⁻¹
      → Cosine similarity в семантическом пространстве

    Хранит:
      svd_u.npy      — левые сингулярные векторы (n_docs × k)
      svd_s.npy      — сингулярные числа (k,)
      svd_vh.npy     — правые сингулярные векторы (k × n_terms)
      svd_meta.json  — doc_ids, n_components
    """

    def __init__(self, workspace: Path):
        self._workspace = workspace
        self._svd_dir = workspace / "context" / "knowledge"
        self._lock = threading.Lock()

        # SVD компоненты
        self._u: np.ndarray | None = None      # document embeddings
        self._s: np.ndarray | None = None      # singular values
        self._vh: np.ndarray | None = None     # term projections
        self._doc_ids: List[str***REMOVED*** = [***REMOVED***
        self._n_components: int = 0
        self._vocab: Dict[str, int***REMOVED*** = {***REMOVED***

        self._load()

    def _path(self, name: str) -> Path:
        return self._svd_dir / name

    def _load(self):
        """Загружает SVD компоненты с диска."""
        try:
            if self._path("svd_u.npy").exists():
                self._u = np.load(str(self._path("svd_u.npy")))
            if self._path("svd_s.npy").exists():
                self._s = np.load(str(self._path("svd_s.npy")))
            if self._path("svd_vh.npy").exists():
                self._vh = np.load(str(self._path("svd_vh.npy")))
            if self._path("svd_meta.json").exists():
                with open(self._path("svd_meta.json"), "r") as f:
                    meta = json.load(f)
                self._doc_ids = meta.get("doc_ids", [***REMOVED***)
                self._n_components = meta.get("n_components", 0)
                self._vocab = meta.get("vocab", {***REMOVED***)
        except Exception:
            self._u = self._s = self._vh = None
            self._doc_ids = [***REMOVED***

    def _save(self):
        """Сохраняет SVD компоненты на диск."""
        self._svd_dir.mkdir(parents=True, exist_ok=True)
        if self._u is not None:
            np.save(str(self._path("svd_u.npy")), self._u)
        if self._s is not None:
            np.save(str(self._path("svd_s.npy")), self._s)
        if self._vh is not None:
            np.save(str(self._path("svd_vh.npy")), self._vh)
        with open(self._path("svd_meta.json"), "w", encoding="utf-8") as f:
            json.dump({
                "doc_ids": self._doc_ids,
                "n_components": self._n_components,
                "vocab": self._vocab,
            ***REMOVED***, f, ensure_ascii=False, indent=2)

    def fit(self, tfidf_vectors: np.ndarray, doc_ids: List[str***REMOVED***,
            vocab: Dict[str, int***REMOVED***, n_components: int = 100) -> None:
        """Обучает SVD на TF-IDF матрице.

        Args:
            tfidf_vectors: матрица (n_docs × n_terms), float32
            doc_ids: список doc_id в порядке строк
            vocab: словарь {термин: id***REMOVED***
            n_components: количество SVD компонент
        """
        n_docs, n_terms = tfidf_vectors.shape
        # Нужно минимум 2 документа и 2 термина для осмысленной SVD
        if n_docs < 2 or n_terms < 2:
            self._u = self._s = self._vh = None
            self._doc_ids = [***REMOVED***
            self._n_components = 0
            self._vocab = {***REMOVED***
            return
        k = min(n_components, n_docs, n_terms)

        # Нормализуем TF-IDF векторы (как в search)
        norms = np.linalg.norm(tfidf_vectors, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        normalized = tfidf_vectors / norms

        with self._lock:
            try:
                # Пробуем torch SVD
                import torch
                t = torch.from_numpy(normalized.astype(np.float64))
                u, s, vh = torch.linalg.svd(t, full_matrices=False)
                self._u = u[:, :k***REMOVED***.numpy().astype(np.float32) * s[:k***REMOVED***.numpy().astype(np.float32)
                self._s = s[:k***REMOVED***.numpy().astype(np.float32)
                self._vh = vh[:k, :***REMOVED***.numpy().astype(np.float32)
            except Exception:
                # Fallback: numpy SVD
                u, s, vh = np.linalg.svd(normalized, full_matrices=False)
                self._u = u[:, :k***REMOVED***.astype(np.float32) * s[:k***REMOVED***.astype(np.float32)
                self._s = s[:k***REMOVED***.astype(np.float32)
                self._vh = vh[:k, :***REMOVED***.astype(np.float32)

            self._doc_ids = list(doc_ids)
            self._n_components = k
            self._vocab = dict(vocab)

        self._save()

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, List[str***REMOVED******REMOVED******REMOVED***:
        """Поиск в семантическом пространстве LSA.

        Returns:
            Список (doc_id, score, matched_terms)
        """
        if self._u is None or self._vh is None or len(self._doc_ids) == 0:
            return [***REMOVED***

        # 1. Строим TF-IDF вектор запроса
        query_tokens = Tokenizer.tokenize(query)
        if not query_tokens:
            return [***REMOVED***

        from collections import Counter
        import math
        q_counter = Counter(query_tokens)
        q_vec = np.zeros(len(self._vocab), dtype=np.float32)
        for token, count in q_counter.items():
            if token in self._vocab:
                col = self._vocab[token***REMOVED***
                q_vec[col***REMOVED*** = math.log(1 + count)

        # 2. Нормализуем
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-10:
            return [***REMOVED***
        q_unit = q_vec / q_norm

        # 3. Проецируем запрос в семантическое пространство
        # q_proj = q · Vh^T (без деления на S — это даёт projection, а не coordinates)
        # На самом деле: doc_emb = U · S, query_proj = q · Vh^T
        # cosine similarity = (U·S) · (q·Vh^T)^T / norms
        # Но более правильно: q_proj = q · Vh^T, и similarity = cos(doc_emb, q_proj)
        q_proj = q_unit @ self._vh.T  # (n_terms,) @ (n_terms, k) = (k,)

        # 4. Косинусная близость
        doc_norms = np.linalg.norm(self._u, axis=1, keepdims=True)
        doc_norms = np.where(doc_norms < 1e-10, 1.0, doc_norms)
        doc_unit = self._u / doc_norms

        q_proj_norm = np.linalg.norm(q_proj)
        if q_proj_norm < 1e-10:
            return [***REMOVED***
        q_proj_unit = q_proj / q_proj_norm

        similarities = doc_unit @ q_proj_unit  # (n_docs,)

        # 5. Топ-K
        top_indices = np.argsort(similarities)[-top_k:***REMOVED***[::-1***REMOVED***

        results = [***REMOVED***
        for idx in top_indices:
            score = float(similarities[idx***REMOVED***)
            if score < 0.01:
                continue
            doc_id = self._doc_ids[idx***REMOVED***

            # Какие термины запроса есть в словаре
            matched = [
                token for token in q_counter
                if token in self._vocab
            ***REMOVED***

            results.append((doc_id, score, matched))

        return results

    def is_empty(self) -> bool:
        return self._u is None

    def clear(self):
        self._u = self._s = self._vh = None
        self._doc_ids = [***REMOVED***
        self._n_components = 0
        self._vocab = {***REMOVED***
        # Удаляем файлы
        for name in ["svd_u.npy", "svd_s.npy", "svd_vh.npy", "svd_meta.json"***REMOVED***:
            p = self._path(name)
            if p.exists():
                p.unlink()


# ═══════════════════════════════════════════════════════════════
# Knowledge Engine (unified API)
# ═══════════════════════════════════════════════════════════════


@dataclass
class KnowledgeEngineStats:
    """Статистика Knowledge Engine."""
    total_docs: int = 0
    fts_docs: int = 0
    vector_docs: int = 0
    vocab_size: int = 0
    db_size_bytes: int = 0
    vectors_size_bytes: int = 0


class KnowledgeEngine:
    """Knowledge Engine — единый интерфейс для поиска по знаниям.

    Объединяет:
      - FTS5 (keyword) — быстрый, точный поиск
      - TF-IDF (semantic) — смысловой поиск на numpy
      - Hybrid — взвешенная комбинация

    Порядок использования:
      1. index_document() или index_from_memory() — наполнить знания
      2. search() — найти релевантные документы
      3. search_capabilities() — определить возможности по запросу

    EventBus: публикует knowledge.indexed, knowledge.searched, knowledge.rebuilt
    """

    def __init__(self, workspace_root: str | Path | None = None, event_bus: Any = None):
        ws = Path(workspace_root) if workspace_root else DEFAULT_WORKSPACE
        self._workspace = ws

        db_path = ws / DEFAULT_DB_PATH
        vectors_path = ws / DEFAULT_VECTORS_PATH
        vocab_path = ws / DEFAULT_VOCAB_PATH
        meta_path = ws / DEFAULT_META_PATH

        self._fts = FtsIndex(db_path)
        self._tfidf = TfidfIndex(vectors_path, vocab_path, meta_path)
        self._semantic: SemanticIndex | None = None  # Lazy init
        self._graph: Any = None  # Lazy init
        self._lock = threading.Lock()
        self._event_bus = event_bus  # Optional EventBus instance

    # ── Индексация ──────────────────────────────────────

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any***REMOVED*** | None = None,
    ) -> None:
        """Индексирует один документ (в FTS5 + TF-IDF)."""
        # FTS5
        self._fts.index(doc_id, content, metadata)

        # TF-IDF (SemanticIndex обновится при следующем fit_semantic())
        self._tfidf.index_documents([(doc_id, content)***REMOVED***)

        # Публикуем событие
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                meta = metadata or {***REMOVED***
                self._event_bus.publish(Event(
                    type="knowledge.indexed",
                    source="knowledge_engine",
                    data={
                        "doc_id": doc_id,
                        "title": meta.get("title", ""),
                        "doc_type": meta.get("doc_type", "text"),
                        "char_count": len(content),
                    ***REMOVED***,
                ))
            except Exception:
                pass

    def fit_semantic(self, n_components: int = 100) -> None:
        """Обучает Semantic Index на текущем TF-IDF индексе.

        Должен вызываться после index_document или rebuild.
        """
        if self._tfidf._vectors is None or self._tfidf.count() < 2:
            return

        si = self.semantic
        si.fit(
            tfidf_vectors=self._tfidf._vectors,
            doc_ids=self._tfidf._doc_ids,
            vocab=self._tfidf._vocab,
            n_components=n_components,
        )

    def index_from_memory(
        self,
        level: str | None = None,
    ) -> int:
        """Индексирует все записи из Memory Engine.

        Args:
            level: если указан — только этот уровень (working/project/knowledge/…)

        Returns:
            Количество проиндексированных документов.
        """
        # Lazy import to avoid circular dependency
        from scripts.memory_engine import MemoryEngine, MemoryLevel

        engine = MemoryEngine(workspace_root=str(self._workspace))

        if level:
            levels = [MemoryLevel(level)***REMOVED***
        else:
            levels = [
                MemoryLevel.KNOWLEDGE,
                MemoryLevel.PROJECT,
                MemoryLevel.WORKING,
                MemoryLevel.PERSONAL,
            ***REMOVED***

        count = 0
        for lvl in levels:
            entries = engine.list_entries(level=lvl)
            for entry in entries:
                doc_id = f"mem_{lvl.value***REMOVED***_{entry.key***REMOVED***"
                self.index_document(
                    doc_id=doc_id,
                    content=entry.content,
                    metadata={
                        "title": entry.key,
                        "source": f"memory/{lvl.value***REMOVED***/{entry.key***REMOVED***",
                        "doc_type": entry.content_type.value,
                        "created_at": entry.created_at,
                    ***REMOVED***,
                )
                count += 1

        return count

    def rebuild_index(self) -> int:
        """Перестраивает весь индекс с нуля из Memory Engine."""
        self._fts.clear()
        self._tfidf.clear()
        count = self.index_from_memory()
        self.fit_semantic()

        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="knowledge.rebuilt",
                    source="knowledge_engine",
                    data={"count": count***REMOVED***,
                ))
            except Exception:
                pass

        return count

    # ── Поиск ───────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
        fts_weight: float = 0.4,
    ) -> List[SearchResult***REMOVED***:
        """Поиск по знаниям.

        Args:
            query: поисковый запрос (на русском или английском)
            top_k: количество результатов
            mode: 'keyword' — только FTS5, 'semantic' — только TF-IDF,
                  'hybrid' — взвешенная комбинация
            fts_weight: вес FTS5 в hybrid режиме (0.0 = только semantic)

        Returns:
            Список SearchResult, отсортированных по score (убывание).
        """
        if not query.strip():
            return [***REMOVED***

        query_terms = Tokenizer.tokenize(query)

        # Keyword search (FTS5)
        fts_results: Dict[str, Tuple[float, str, Dict[str, Any***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        # Semantic ML search (LSA via torch SVD)
        semantic_results: Dict[str, Tuple[float, List[str***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        if mode == "semantic_ml":
            si = self.semantic
            if not si.is_empty():
                for doc_id, score, matched in si.search(query, top_k * 3):
                    if doc_id not in semantic_results or score > semantic_results[doc_id***REMOVED***[0***REMOVED***:
                        semantic_results[doc_id***REMOVED*** = (score, matched)

        if mode in ("keyword", "hybrid"):
            for doc_id, score, content, meta in self._fts.search(query, top_k * 3):
                if doc_id not in fts_results or score > fts_results[doc_id***REMOVED***[0***REMOVED***:
                    fts_results[doc_id***REMOVED*** = (score, content, meta)

        # Semantic search (TF-IDF)
        tfidf_results: Dict[str, Tuple[float, List[str***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        if mode in ("semantic", "hybrid"):
            for doc_id, score, matched in self._tfidf.search(query, top_k * 3):
                if doc_id not in tfidf_results or score > tfidf_results[doc_id***REMOVED***[0***REMOVED***:
                    tfidf_results[doc_id***REMOVED*** = (score, matched)

        # Комбинируем
        combined: Dict[str, Dict[str, Any***REMOVED******REMOVED*** = {***REMOVED***

        if mode == "keyword":
            for doc_id, (score, content, meta) in fts_results.items():
                combined[doc_id***REMOVED*** = {
                    "score": score,
                    "content": content,
                    "metadata": meta,
                    "matched_terms": [t for t in query_terms if t.lower() in content.lower()***REMOVED***,
                ***REMOVED***

        elif mode == "semantic":
            for doc_id, (score, matched) in tfidf_results.items():
                combined[doc_id***REMOVED*** = {
                    "score": score,
                    "content": "",
                    "metadata": {"search_method": "tfidf"***REMOVED***,
                    "matched_terms": matched,
                ***REMOVED***

        elif mode == "semantic_ml":
            for doc_id, (score, matched) in semantic_results.items():
                combined[doc_id***REMOVED*** = {
                    "score": score,
                    "content": "",
                    "metadata": {"search_method": "semantic_ml"***REMOVED***,
                    "matched_terms": matched,
                ***REMOVED***

        elif mode == "hybrid":
            all_ids = set(fts_results.keys()) | set(tfidf_results.keys())

            for doc_id in all_ids:
                fts_score = fts_results.get(doc_id, (0.0, "", {***REMOVED***))[0***REMOVED***
                tfidf_score = tfidf_results.get(doc_id, (0.0, [***REMOVED***))[0***REMOVED***
                content = fts_results.get(doc_id, ("", {***REMOVED***))[1***REMOVED*** if doc_id in fts_results else ""
                meta = fts_results.get(doc_id, ("", {***REMOVED***))[2***REMOVED*** if doc_id in fts_results else {***REMOVED***

                # Нормализованная комбинация
                hybrid_score = fts_weight * fts_score + (1 - fts_weight) * tfidf_score

                matched = tfidf_results.get(doc_id, (0.0, [***REMOVED***))[1***REMOVED*** if doc_id in tfidf_results else [***REMOVED***
                if not matched:
                    matched = [t for t in query_terms if t.lower() in content.lower()***REMOVED***

                combined[doc_id***REMOVED*** = {
                    "score": hybrid_score,
                    "content": content,
                    "metadata": {**meta, "search_method": "hybrid"***REMOVED***,
                    "matched_terms": matched,
                ***REMOVED***

        # Сортируем и формируем результат
        sorted_ids = sorted(
            combined.keys(),
            key=lambda did: combined[did***REMOVED***["score"***REMOVED***,
            reverse=True,
        )[:top_k***REMOVED***

        results = [***REMOVED***
        for doc_id in sorted_ids:
            info = combined[doc_id***REMOVED***
            content = info["content"***REMOVED***
            snippet = Tokenizer.extract_snippet(content, info["matched_terms"***REMOVED***)

            results.append(SearchResult(
                doc_id=doc_id,
                score=round(info["score"***REMOVED***, 4),
                content=content,
                snippet=snippet,
                metadata=info["metadata"***REMOVED***,
                matched_terms=info["matched_terms"***REMOVED***,
            ))

        # Публикуем событие поиска
        if self._event_bus is not None:
            try:
                from scripts.event_bus import Event
                self._event_bus.publish(Event(
                    type="knowledge.searched",
                    source="knowledge_engine",
                    data={
                        "query": query[:100***REMOVED***,
                        "mode": mode,
                        "result_count": len(results),
                    ***REMOVED***,
                ))
            except Exception:
                pass

        return results

    def search_capabilities(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[str***REMOVED***:
        """Извлекает capabilities (возможности) из запроса.

        Анализирует запрос и возвращает наиболее релевантные
        capability-теги на основе проиндексированных знаний.

        Args:
            query: запрос пользователя
            top_k: максимальное количество capability

        Returns:
            Список capability-строк (например: ["code", "router", "memory"***REMOVED***)
        """
        results = self.search(query, top_k=top_k, mode="hybrid")
        capabilities: List[str***REMOVED*** = [***REMOVED***

        for r in results:
            # Из метаданных
            source = r.metadata.get("source", "")
            doc_type = r.metadata.get("doc_type", "")

            parts = source.split("/")
            if len(parts) >= 2:
                capabilities.append(f"{parts[-2***REMOVED******REMOVED***:{parts[-1***REMOVED******REMOVED***")

            capabilities.extend(r.matched_terms[:3***REMOVED***)

        # Убираем дубликаты, сохраняем порядок
        seen: Set[str***REMOVED*** = set()
        unique: List[str***REMOVED*** = [***REMOVED***
        for cap in capabilities:
            if cap not in seen:
                seen.add(cap)
                unique.append(cap)

        return unique[:top_k***REMOVED***

    # ── Графовый поиск ─────────────────────────────────

    @property
    def semantic(self) -> SemanticIndex:
        """Lazy init SemanticIndex."""
        if self._semantic is None:
            self._semantic = SemanticIndex(self._workspace)
        return self._semantic

    @property
    def graph(self):
        """Lazy init GraphIndex на той же БД."""
        if self._graph is None:
            GI = _get_graph_index()
            db_path = self._workspace / DEFAULT_DB_PATH
            self._graph = GI(db_path)
        return self._graph

    def graph_search(
        self,
        doc_id: str,
        mode: str = "related",
        max_depth: int = 2,
        rel_type: str | None = None,
    ) -> Dict[str, Any***REMOVED***:
        """Поиск по графу связей.

        Args:
            doc_id: центральный узел
            mode: 'related' — связанные узлы,
                  'subgraph' — подграф,
                  'path' — поиск пути (требует target_id в metadata),
                  'traverse' — цепочка связей
            max_depth: глубина обхода
            rel_type: фильтр по типу связи

        Returns:
            Dict с результатами поиска.
        """
        g = self.graph

        if mode == "related":
            related = g.get_related(doc_id, rel_type=rel_type, max_depth=max_depth)
            return {
                "mode": "related",
                "central": doc_id,
                "count": len(related),
                "results": [
                    {"doc_id": r[0***REMOVED***, "rel_type": r[1***REMOVED***,
                     "direction": r[2***REMOVED***, "weight": r[3***REMOVED***, "depth": r[4***REMOVED******REMOVED***
                    for r in related
                ***REMOVED***,
            ***REMOVED***

        elif mode == "subgraph":
            nodes, edges = g.subgraph(doc_id, depth=max_depth, rel_type=rel_type)
            return {
                "mode": "subgraph",
                "central": doc_id,
                "nodes": [n.doc_id for n in nodes***REMOVED***,
                "edges": [
                    {"source": e.source_id, "target": e.target_id,
                     "type": e.rel_type, "weight": e.weight***REMOVED***
                    for e in edges
                ***REMOVED***,
            ***REMOVED***

        elif mode == "traverse":
            paths = g.traverse(
                doc_id,
                rel_type=rel_type or "references",
                max_hops=max_depth,
            )
            return {
                "mode": "traverse",
                "start": doc_id,
                "paths": [
                    [{"node": p[0***REMOVED***, "rel_type": p[1***REMOVED***, "weight": p[2***REMOVED******REMOVED*** for p in path***REMOVED***
                    for path in paths
                ***REMOVED***,
            ***REMOVED***

        return {"mode": mode, "error": f"Unknown mode: {mode***REMOVED***"***REMOVED***

    def add_graph_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        weight: float = 1.0,
        metadata: Dict[str, Any***REMOVED*** | None = None,
    ) -> None:
        """Добавляет связь в граф."""
        self.graph.add_edge(source_id, target_id, rel_type, weight, metadata)

    def graph_auto_discover(
        self,
        min_shared_terms: int = 3,
        max_pairs: int = 100,
    ) -> int:
        """Авто-детект связей между документами."""
        return self.graph.auto_discover_from_memory(
            min_shared_terms=min_shared_terms,
            max_pairs=max_pairs,
        )

    # ── Статистика ───────────────────────────────────────

    def get_stats(self) -> KnowledgeEngineStats:
        """Статистика Knowledge Engine."""
        """Статистика Knowledge Engine."""
        fts_count = self._fts.count()
        vec_count = self._tfidf.count()

        db_path = self._workspace / DEFAULT_DB_PATH
        vectors_path = self._workspace / DEFAULT_VECTORS_PATH

        db_size = db_path.stat().st_size if db_path.exists() else 0
        vec_size = vectors_path.stat().st_size if vectors_path.exists() else 0

        return KnowledgeEngineStats(
            total_docs=max(fts_count, vec_count),
            fts_docs=fts_count,
            vector_docs=vec_count,
            vocab_size=len(self._tfidf._vocab) if hasattr(self._tfidf, "_vocab") else 0,
            db_size_bytes=db_size,
            vectors_size_bytes=vec_size,
        )

    def clear(self) -> None:
        """Очищает все индексы, граф и семантику."""
        self._fts.clear()
        self._tfidf.clear()
        if self._semantic is not None:
            self._semantic.clear()
        if self._graph is not None:
            self._graph.clear()


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Knowledge Engine — поиск по знаниям Buffy Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/knowledge_engine.py search "capability router"
  python scripts/knowledge_engine.py search "memory engine architecture" --mode semantic
  python scripts/knowledge_engine.py index                          # из Memory Engine
  python scripts/knowledge_engine.py index --doc my_doc "content"   # прямой
  python scripts/knowledge_engine.py rebuild                        # перестроить
  python scripts/knowledge_engine.py stats                          # статистика
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Поиск по знаниям")
    p_search.add_argument("query", help="Поисковый запрос")
    p_search.add_argument("--top-k", type=int, default=10, help="Количество результатов")
    p_search.add_argument(
        "--mode", choices=["keyword", "semantic", "hybrid", "semantic_ml"***REMOVED***,
        default="hybrid", help="Режим поиска (semantic_ml = LSA через torch)",
    )

    # index
    p_index = sub.add_parser("index", help="Индексация документов")
    p_index.add_argument("--doc", nargs=2, metavar=("ID", "CONTENT"),
                         help="Прямая индексация: --doc my_id 'content'")
    p_index.add_argument("--level", help="Уровень памяти (working/project/knowledge/...)")

    # rebuild
    sub.add_parser("rebuild", help="Перестроить индекс из Memory Engine")

    # stats
    sub.add_parser("stats", help="Статистика")

    # clear
    sub.add_parser("clear", help="Очистить индекс")

    args = parser.parse_args()

    ke = KnowledgeEngine()

    if args.command == "search":
        results = ke.search(args.query, top_k=args.top_k, mode=args.mode)
        if not results:
            print("🔍 No results")
            return
        print(f"🔍 {len(results)***REMOVED*** results for '{args.query***REMOVED***' ({args.mode***REMOVED***):")
        print()
        for i, r in enumerate(results, 1):
            print(f"  {i***REMOVED***. [{r.score:.4f***REMOVED******REMOVED*** {r.doc_id***REMOVED***")
            print(f"     📝 {r.snippet[:120***REMOVED******REMOVED***")
            if r.matched_terms:
                print(f"     🏷  {', '.join(r.matched_terms[:5***REMOVED***)***REMOVED***")
            print()

    elif args.command == "index":
        if args.doc:
            doc_id, content = args.doc
            ke.index_document(doc_id, content)
            print(f"✅ Indexed: {doc_id***REMOVED*** ({len(content)***REMOVED*** chars)")
        elif args.level:
            count = ke.index_from_memory(level=args.level)
            print(f"✅ Indexed {count***REMOVED*** documents from memory level '{args.level***REMOVED***'")
        else:
            count = ke.index_from_memory()
            print(f"✅ Indexed {count***REMOVED*** documents from memory")

    elif args.command == "rebuild":
        count = ke.rebuild_index()
        print(f"✅ Index rebuilt: {count***REMOVED*** documents")

    elif args.command == "stats":
        stats = ke.get_stats()
        print("📊 KNOWLEDGE ENGINE STATS")
        print(f"   Total docs:     {stats.total_docs***REMOVED***")
        print(f"   FTS5 (keyword): {stats.fts_docs***REMOVED***")
        print(f"   TF-IDF (vector): {stats.vector_docs***REMOVED***")
        print(f"   Vocabulary:     {stats.vocab_size***REMOVED*** terms")
        print(f"   DB size:        {stats.db_size_bytes:,***REMOVED*** bytes")
        print(f"   Vectors size:   {stats.vectors_size_bytes:,***REMOVED*** bytes")

    elif args.command == "clear":
        ke.clear()
        print("🗑 Index cleared")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
