#!/usr/bin/env python3
"""
graph_index.py — Graph Search для Buffy Project.

Хранит связи между записями памяти как направленный граф в SQLite.

Типы связей:
  references   — документ A ссылается на документ B
  parent       — A родитель B (иерархия)
  child        — A дочерний B (обратная parent)
  depends      — A зависит от B
  related      — A связан с B (симметрично)
  tagged       — A помечен тегом B (B — узел-тег)
  contains     — A содержит B (композиция)

Использование:
    from scripts_01.graph_index import GraphIndex

    g = GraphIndex(Path("context_12/knowledge/index.db"))
    g.add_edge("doc1", "doc2", "references")
    g.add_edge("doc1", "doc3", "related", weight=0.8)

    related = g.get_related("doc1")
    path = g.shortest_path("doc1", "doc3")
    sub = g.subgraph("doc1", depth=2)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

REL_TYPES = {
    "references", "parent", "child", "depends",
    "related", "tagged", "contains",
}

REL_INVERSE = {
    "references": "referenced_by",
    "parent": "child",
    "child": "parent",
    "depends": "depended_by",
    "related": "related",          # symmetric
    "tagged": "tags",
    "contains": "part_of",
}

# Для симметричных отношений — обе стороны храним одинаково
SYMMETRIC_RELS = {"related"}

# Для обратных отношений — создаём автоматически
AUTO_INVERSE = {"parent", "references", "depends", "contains", "tagged"}


@dataclass
class Edge:
    """Ребро графа."""
    source_id: str
    target_id: str
    rel_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Node:
    """Узел графа."""
    doc_id: str
    node_type: str = "document"
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PathResult:
    """Результат поиска пути в графе."""
    path: List[Tuple[str, str, str]]  # [(from, to, rel_type), ...]
    length: int = 0
    total_weight: float = 0.0


@dataclass
class GraphStats:
    """Статистика графа."""
    total_nodes: int = 0
    total_edges: int = 0
    edge_types: Dict[str, int] = field(default_factory=dict)
    isolated_nodes: int = 0


# ═══════════════════════════════════════════════════════════════
# GraphIndex
# ═══════════════════════════════════════════════════════════════


class GraphIndex:
    """Граф связей между записями памяти.

    Хранит узлы и рёбра в SQLite (та же БД, что и FTS-индекс).
    Поддерживает:
      - CRUD для узлов и рёбер
      - get_related — найти всё, что связано с узлом
      - shortest_path — BFS между двумя узлами
      - subgraph — подграф вокруг узла
      - traverse — обход по типу связи
      - auto_discover — авто-детект связей по содержимому
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Создаёт таблицы графа."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    doc_id TEXT PRIMARY KEY,
                    node_type TEXT DEFAULT 'document',
                    label TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    rel_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    PRIMARY KEY (source_id, target_id, rel_type)
                );

                CREATE INDEX IF NOT EXISTS idx_edges_source
                    ON graph_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_target
                    ON graph_edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_edges_type
                    ON graph_edges(rel_type);
            """)
            conn.commit()

    # ── Узлы ──────────────────────────────────────────────

    def add_node(
        self,
        doc_id: str,
        node_type: str = "document",
        label: str = "",
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        """Добавляет или обновляет узел графа."""
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO graph_nodes
                       (doc_id, node_type, label, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (doc_id, node_type, label, meta_json, now),
                )
                conn.commit()

    def remove_node(self, doc_id: str) -> bool:
        """Удаляет узел и все связанные рёбра.

        Returns:
            True если узел существовал.
        """
        with self._lock:
            with self._connect() as conn:
                # Удаляем рёбра, где узел — source или target
                conn.execute(
                    "DELETE FROM graph_edges WHERE source_id = ? OR target_id = ?",
                    (doc_id, doc_id),
                )
                cur = conn.execute(
                    "DELETE FROM graph_nodes WHERE doc_id = ?",
                    (doc_id,),
                )
                conn.commit()
                return cur.rowcount > 0

    def get_node(self, doc_id: str) -> Node | None:
        """Читает узел графа."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM graph_nodes WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
            if row is None:
                return None
            return Node(
                doc_id=row["doc_id"],
                node_type=row["node_type"],
                label=row["label"],
                metadata=json.loads(row["metadata"] or "{)"),
            )

    # ── Рёбра ─────────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        weight: float = 1.0,
        metadata: Dict[str, Any] | None = None,
        auto_add_nodes: bool = True,
        create_inverse: bool = True,
    ) -> None:
        """Добавляет ребро графа.

        Args:
            source_id: откуда
            target_id: куда
            rel_type: тип связи (references, parent, depends, related, etc.)
            weight: вес связи [0..1]
            metadata: произвольные метаданные
            auto_add_nodes: создать узлы, если не существуют
            create_inverse: создать обратные рёбра (parent→child и т.д.)
        """
        if rel_type not in REL_TYPES:
            raise ValueError(
                f"Unknown rel_type: '{rel_type}'. "
                f"Valid: {', '.join(sorted(REL_TYPES))}"
            )

        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        with self._lock:
            with self._connect() as conn:
                # Авто-создание узлов
                if auto_add_nodes:
                    for doc_id in (source_id, target_id):
                        conn.execute(
                            """INSERT OR IGNORE INTO graph_nodes
                               (doc_id, created_at) VALUES (?, ?)""",
                            (doc_id, now),
                        )

                # Прямое ребро
                conn.execute(
                    """INSERT OR REPLACE INTO graph_edges
                       (source_id, target_id, rel_type, weight, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (source_id, target_id, rel_type, weight, meta_json, now),
                )

                # Для симметричных отношений — дублируем
                if rel_type in SYMMETRIC_RELS:
                    conn.execute(
                        """INSERT OR REPLACE INTO graph_edges
                           (source_id, target_id, rel_type, weight, metadata, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (target_id, source_id, rel_type, weight, meta_json, now),
                    )

                # Обратное ребро (parent → child, references → referenced_by, etc.)
                if create_inverse and rel_type in AUTO_INVERSE and rel_type not in SYMMETRIC_RELS:
                    inverse_type = REL_INVERSE[rel_type]
                    conn.execute(
                        """INSERT OR REPLACE INTO graph_edges
                           (source_id, target_id, rel_type, weight, metadata, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (target_id, source_id, inverse_type, weight, meta_json, now),
                    )

                conn.commit()

    def remove_edge(self, source_id: str, target_id: str, rel_type: str) -> bool:
        """Удаляет ребро графа (включая обратное, если есть).

        Returns:
            True если хотя бы одно ребро существовало.
        """
        with self._lock:
            with self._connect() as conn:
                # Прямое ребро
                cur1 = conn.execute(
                    "DELETE FROM graph_edges WHERE source_id=? AND target_id=? AND rel_type=?",
                    (source_id, target_id, rel_type),
                )
                # Обратное ребро (если есть — например referenced_by для references)
                inverse_type = REL_INVERSE.get(rel_type)
                if inverse_type:
                    conn.execute(
                        "DELETE FROM graph_edges WHERE source_id=? AND target_id=? AND rel_type=?",
                        (target_id, source_id, inverse_type),
                    )
                # Симметричное (related хранится в обе стороны)
                if rel_type in SYMMETRIC_RELS:
                    conn.execute(
                        "DELETE FROM graph_edges WHERE source_id=? AND target_id=? AND rel_type=?",
                        (target_id, source_id, rel_type),
                    )
                conn.commit()
                return cur1.rowcount > 0

    # ── Поиск в графе ────────────────────────────────────

    def get_related(
        self,
        doc_id: str,
        rel_type: str | None = None,
        max_depth: int = 1,
        min_weight: float = 0.0,
    ) -> List[Tuple[str, str, str, float, int]]:
        """Находит все узлы, связанные с doc_id.

        Возвращает связанные узлы с информацией о связи.
        Один узел может появиться несколько раз с разными типами связей,
        но не дублируется с одинаковым типом.

        Args:
            doc_id: центральный узел
            rel_type: фильтр по типу связи (None = все)
            max_depth: глубина обхода (1 = прямые связи)
            min_weight: минимальный вес связи

        Returns:
            Список (related_id, rel_type, direction, weight, depth)
            direction: 'out' — от doc_id, 'in' — к doc_id
        """
        if max_depth < 1:
            return []

        with self._lock:
            with self._connect() as conn:
                visited: Set[str] = {doc_id}
                results: List[Tuple[str, str, str, float, int]] = []
                # Для отслеживания уникальных (node, type) пар
                seen_pairs: Set[Tuple[str, str]] = set()

                queue: deque = deque()
                queue.append((doc_id, 0))

                while queue:
                    current_id, depth = queue.popleft()

                    if depth >= max_depth:
                        continue

                    # Исходящие рёбра
                    query = """
                        SELECT e.target_id, e.rel_type, e.weight
                        FROM graph_edges e
                        WHERE e.source_id = ? AND e.weight >= ?
                    """
                    params: List[Any] = [current_id, min_weight]
                    if rel_type:
                        query += " AND e.rel_type = ?"
                        params.append(rel_type)

                    outgoing_rows = conn.execute(query, params).fetchall()
                    for row in outgoing_rows:
                        neighbor_id = row["target_id"]
                        rtype = row["rel_type"]
                        pair_key = (neighbor_id, rtype)

                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            results.append((
                                neighbor_id, rtype, "out",
                                row["weight"], depth + 1,
                            ))

                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            if depth + 1 < max_depth:
                                queue.append((neighbor_id, depth + 1))

                    # Входящие рёбра
                    query = """
                        SELECT e.source_id, e.rel_type, e.weight
                        FROM graph_edges e
                        WHERE e.target_id = ? AND e.weight >= ?
                    """
                    params = [current_id, min_weight]
                    if rel_type:
                        query += " AND e.rel_type = ?"
                        params.append(rel_type)

                    incoming_rows = conn.execute(query, params).fetchall()
                    for row in incoming_rows:
                        neighbor_id = row["source_id"]
                        rtype = row["rel_type"]
                        pair_key = (neighbor_id, rtype)

                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            results.append((
                                neighbor_id, rtype, "in",
                                row["weight"], depth + 1,
                            ))

                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            if depth + 1 < max_depth:
                                queue.append((neighbor_id, depth + 1))

        return results

    def shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        rel_type: str | None = None,
    ) -> PathResult | None:
        """BFS поиск кратчайшего пути между двумя узлами.

        Args:
            source_id: начальный узел
            target_id: конечный узел
            max_depth: максимальная глубина поиска
            rel_type: фильтр по типу связи

        Returns:
            PathResult или None если путь не найден
        """
        if source_id == target_id:
            return PathResult(path=[], length=0, total_weight=1.0)

        visited: Set[str] = {source_id}
        # queue: (current_id, path_so_far, total_weight)
        queue: deque = deque()
        queue.append((source_id, [], 0.0))

        with self._connect() as conn:
            while queue:
                current_id, path, total_weight = queue.popleft()

                if len(path) >= max_depth:
                    continue

                # Исходящие рёбра
                query = """
                    SELECT e.target_id, e.rel_type, e.weight
                    FROM graph_edges e
                    WHERE e.source_id = ?
                """
                params: List[Any] = [current_id]
                if rel_type:
                    query += " AND e.rel_type = ?"
                    params.append(rel_type)

                for row in conn.execute(query, params).fetchall():
                    neighbor_id = row["target_id"]
                    if neighbor_id == target_id:
                        return PathResult(
                            path=path + [(current_id, neighbor_id, row["rel_type"])],
                            length=len(path) + 1,
                            total_weight=total_weight + row["weight"],
                        )
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((
                            neighbor_id,
                            path + [(current_id, neighbor_id, row["rel_type"])],
                            total_weight + row["weight"],
                        ))

                # Входящие рёбра (для обратных связей)
                query = """
                    SELECT e.source_id, e.rel_type, e.weight
                    FROM graph_edges e
                    WHERE e.target_id = ?
                """
                params = [current_id]
                if rel_type:
                    query += " AND e.rel_type = ?"
                    params.append(rel_type)

                for row in conn.execute(query, params).fetchall():
                    neighbor_id = row["source_id"]
                    if neighbor_id == target_id:
                        return PathResult(
                            path=path + [(current_id, neighbor_id, row["rel_type"])],
                            length=len(path) + 1,
                            total_weight=total_weight + row["weight"],
                        )
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((
                            neighbor_id,
                            path + [(current_id, neighbor_id, row["rel_type"])],
                            total_weight + row["weight"],
                        ))

        return None

    def subgraph(
        self,
        doc_id: str,
        depth: int = 2,
        rel_type: str | None = None,
    ) -> Tuple[List[Node], List[Edge]]:
        """Извлекает подграф вокруг узла.

        Returns:
            (nodes, edges) — список узлов и рёбер в подграфе.
        """
        related = self.get_related(doc_id, rel_type=rel_type, max_depth=depth)

        # Собираем все doc_id в подграфе
        node_ids: Set[str] = {doc_id}
        for related_id, _, _, _, _ in related:
            node_ids.add(related_id)

        with self._connect() as conn:
            # Узлы
            nodes = []
            for nid in node_ids:
                row = conn.execute(
                    "SELECT * FROM graph_nodes WHERE doc_id = ?", (nid,)
                ).fetchone()
                if row:
                    nodes.append(Node(
                        doc_id=row["doc_id"],
                        node_type=row["node_type"],
                        label=row["label"],
                        metadata=json.loads(row["metadata"] or "{)"),
                    ))
                else:
                    nodes.append(Node(doc_id=nid))

            # Рёбра между узлами подграфа
            placeholders = ",".join("?" for _ in node_ids)
            edges = []
            for row in conn.execute(
                f"""SELECT * FROM graph_edges
                    WHERE source_id IN ({placeholders})
                    AND target_id IN ({placeholders})""",
                list(node_ids) + list(node_ids),
            ).fetchall():
                if rel_type is None or row["rel_type"] == rel_type:
                    edges.append(Edge(
                        source_id=row["source_id"],
                        target_id=row["target_id"],
                        rel_type=row["rel_type"],
                        weight=row["weight"],
                        metadata=json.loads(row["metadata"] or "{)"),
                        created_at=row["created_at"],
                    ))

        return nodes, edges

    def traverse(
        self,
        start_id: str,
        rel_type: str,
        direction: str = "out",
        max_hops: int = 10,
    ) -> List[List[Tuple[str, str, float]]]:
        """Обход графа по цепочке связей.

        Args:
            start_id: начальный узел
            rel_type: тип связи для обхода
            direction: 'out' — от узла, 'in' — к узлу
            max_hops: максимальное количество шагов

        Returns:
            Список путей, каждый путь — список (node_id, rel_type, weight)
        """
        paths: List[List[Tuple[str, str, float]]] = []
        visited: Set[str] = {start_id}

        def _dfs(current: str, path: List[Tuple[str, str, float]]):
            if len(path) >= max_hops:
                paths.append(list(path))
                return

            found = False
            with self._connect() as conn:
                if direction == "out":
                    rows = conn.execute(
                        """SELECT target_id, rel_type, weight
                           FROM graph_edges
                           WHERE source_id = ? AND rel_type = ?""",
                        (current, rel_type),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT source_id, rel_type, weight
                           FROM graph_edges
                           WHERE target_id = ? AND rel_type = ?""",
                        (current, rel_type),
                    ).fetchall()

                for row in rows:
                    neighbor_id = row[0]
                    if neighbor_id not in visited:
                        found = True
                        visited.add(neighbor_id)
                        path.append((neighbor_id, row[1], row[2]))
                        _dfs(neighbor_id, path)
                        path.pop()
                        visited.discard(neighbor_id)

            if not found:
                paths.append(list(path))

        _dfs(start_id, [])
        return paths

    # ── Авто-детект связей ───────────────────────────────

    def auto_discover(
        self,
        doc_pairs: List[Tuple[str, str, str, str]],
        min_shared_terms: int = 3,
    ) -> int:
        """Автоматически обнаруживает связи между документами.

        Анализирует пары документов и создаёт рёбра 'related',
        если у них достаточно общих терминов (по TF-IDF токенам).

        Args:
            doc_pairs: список (doc_id1, tokens1, doc_id2, tokens2)
                       где tokens — строка содержимого
            min_shared_terms: минимальное количество общих терминов

        Returns:
            Количество созданных рёбер.
        """
        from scripts_01.knowledge_engine import Tokenizer

        count = 0
        for doc_id1, tokens1, doc_id2, tokens2 in doc_pairs:
            # Токенизируем
            set1 = set(Tokenizer.tokenize(tokens1))
            set2 = set(Tokenizer.tokenize(tokens2))

            shared = set1 & set2
            if len(shared) >= min_shared_terms:
                weight = min(1.0, len(shared) / 10.0)
                self.add_edge(
                    source_id=doc_id1,
                    target_id=doc_id2,
                    rel_type="related",
                    weight=round(weight, 2),
                    metadata={"shared_terms": list(shared)[:10]},
                    auto_add_nodes=True,
                    create_inverse=True,
                )
                count += 1

        return count

    def auto_discover_from_memory(
        self,
        min_shared_terms: int = 3,
        max_pairs: int = 100,
    ) -> int:
        """Авто-детект связей между всеми записями в Memory Engine.

        Args:
            min_shared_terms: минимальное количество общих терминов
            max_pairs: максимальное количество пар для анализа

        Returns:
            Количество созданных рёбер.
        """
        # Lazy import
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel

        engine = MemoryEngine(workspace_root=str(self._db_path.parent.parent.parent))

        all_entries = []
        for level in MemoryLevel:
            entries = engine.list_entries(level=level)
            for e in entries:
                all_entries.append((f"mem_{level.value}_{e.key}", e.content))

        # Анализируем пары
        count = 0
        pairs_done = 0
        for i in range(len(all_entries)):
            for j in range(i + 1, len(all_entries)):
                if pairs_done >= max_pairs:
                    return count

                doc_id1, content1 = all_entries[i]
                doc_id2, content2 = all_entries[j]

                from scripts_01.knowledge_engine import Tokenizer
                set1 = set(Tokenizer.tokenize(content1))
                set2 = set(Tokenizer.tokenize(content2))
                shared = set1 & set2

                if len(shared) >= min_shared_terms:
                    weight = min(1.0, len(shared) / 10.0)
                    self.add_edge(
                        source_id=doc_id1,
                        target_id=doc_id2,
                        rel_type="related",
                        weight=round(weight, 2),
                        metadata={"shared_terms": list(shared)[:10]},
                        auto_add_nodes=True,
                        create_inverse=True,
                    )
                    count += 1

                pairs_done += 1

        return count

    # ── Статистика ───────────────────────────────────────

    def get_stats(self) -> GraphStats:
        """Статистика графа."""
        with self._connect() as conn:
            total_nodes = conn.execute(
                "SELECT COUNT(*) FROM graph_nodes"
            ).fetchone()[0]

            total_edges = conn.execute(
                "SELECT COUNT(*) FROM graph_edges"
            ).fetchone()[0]

            # Типы рёбер
            edge_types: Dict[str, int] = {}
            for row in conn.execute(
                "SELECT rel_type, COUNT(*) as cnt FROM graph_edges GROUP BY rel_type"
            ).fetchall():
                edge_types[row["rel_type"]] = row["cnt"]

            # Изолированные узлы (без рёбер)
            isolated = conn.execute(
                """SELECT COUNT(*) FROM graph_nodes n
                   WHERE NOT EXISTS (
                       SELECT 1 FROM graph_edges e
                       WHERE e.source_id = n.doc_id OR e.target_id = n.doc_id
                   )"""
            ).fetchone()[0]

        return GraphStats(
            total_nodes=total_nodes,
            total_edges=total_edges,
            edge_types=edge_types,
            isolated_nodes=isolated,
        )

    def clear(self) -> None:
        """Очищает граф."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM graph_edges")
                conn.execute("DELETE FROM graph_nodes")
                conn.commit()


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Graph Index — связи между записями памяти Buffy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/graph_index.py related doc1                    # все связи doc1
  python scripts_01/graph_index.py path doc1 doc5                  # кратчайший путь
  python scripts_01/graph_index.py subgraph doc1 --depth 3        # подграф
  python scripts_01/graph_index.py edge add doc1 doc2 references   # добавить ребро
  python scripts_01/graph_index.py auto                            # авто-детект
  python scripts_01/graph_index.py stats                           # статистика
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # related
    p_rel = sub.add_parser("related", help="Связанные узлы")
    p_rel.add_argument("doc_id", help="Центральный узел")
    p_rel.add_argument("--depth", type=int, default=2, help="Глубина")
    p_rel.add_argument("--type", dest="rel_type", help="Тип связи")

    # path
    p_path = sub.add_parser("path", help="Кратчайший путь")
    p_path.add_argument("source", help="Откуда")
    p_path.add_argument("target", help="Куда")

    # subgraph
    p_sub = sub.add_parser("subgraph", help="Подграф")
    p_sub.add_argument("doc_id", help="Центральный узел")
    p_sub.add_argument("--depth", type=int, default=2, help="Глубина")

    # edge
    p_edge = sub.add_parser("edge", help="Управление рёбрами")
    p_edge.add_argument("action", choices=["add", "remove"], help="Действие")
    p_edge.add_argument("source", help="Откуда")
    p_edge.add_argument("target", help="Куда")
    p_edge.add_argument("rel_type", help="Тип связи")

    # node
    p_node = sub.add_parser("node", help="Информация об узле")
    p_node.add_argument("doc_id", help="ID узла")

    # auto
    p_auto = sub.add_parser("auto", help="Авто-детект связей")
    p_auto.add_argument("--min-terms", type=int, default=3, help="Мин. общих терминов")
    p_auto.add_argument("--max-pairs", type=int, default=100, help="Макс. пар")

    # stats
    sub.add_parser("stats", help="Статистика")

    # clear
    sub.add_parser("clear", help="Очистить граф")

    args = parser.parse_args()

    from scripts_01.knowledge_engine import DEFAULT_DB_PATH, DEFAULT_WORKSPACE
    db_path = DEFAULT_WORKSPACE / DEFAULT_DB_PATH
    g = GraphIndex(db_path)

    if args.command == "related":
        results = g.get_related(
            args.doc_id,
            rel_type=getattr(args, "rel_type", None),
            max_depth=args.depth,
        )
        if not results:
            print(f"📭 No relations found for '{args.doc_id}'")
            return
        print(f"🔗 {len(results)} relations for '{args.doc_id}' (depth={args.depth}):")
        for rel_id, rtype, direction, weight, depth in results:
            arrow = "→" if direction == "out" else "←"
            print(f"  {'  ' * (depth - 1)}[{weight:.2f}] {rel_id} {arrow} {rtype}")

    elif args.command == "path":
        result = g.shortest_path(args.source, args.target)
        if result is None:
            print(f"❌ No path found between '{args.source}' and '{args.target}'")
            return
        print(f"🛤 Path (length={result.length}, weight={result.total_weight:.2f}):")
        for from_id, to_id, rtype in result.path:
            print(f"  {from_id} →[{rtype}]→ {to_id}")

    elif args.command == "subgraph":
        nodes, edges = g.subgraph(args.doc_id, depth=args.depth)
        print(f"📊 Subgraph around '{args.doc_id}' (depth={args.depth}):")
        print(f"   Nodes: {len(nodes)}")
        print(f"   Edges: {len(edges)}")
        for e in edges[:10]:
            print(f"   {e.source_id} →[{e.rel_type} ({e.weight})]→ {e.target_id}")
        if len(edges) > 10:
            print(f"   ... and {len(edges) - 10} more")

    elif args.command == "edge":
        if args.action == "add":
            g.add_edge(args.source, args.target, args.rel_type)
            print(f"✅ Edge added: {args.source} →[{args.rel_type}]→ {args.target}")
        elif args.action == "remove":
            ok = g.remove_edge(args.source, args.target, args.rel_type)
            print(f"{'🗑 Removed' if ok else '❌ Not found'}: {args.source} →[{args.rel_type}]→ {args.target}")

    elif args.command == "node":
        node = g.get_node(args.doc_id)
        if node:
            print(f"📖 Node: {node.doc_id}")
            print(f"   Type:  {node.node_type}")
            print(f"   Label: {node.label or '(none)'}")
            if node.metadata:
                print(f"   Meta:  {json.dumps(node.metadata, ensure_ascii=False)[:200]}")
        else:
            print(f"❌ Node not found: {args.doc_id}")

    elif args.command == "auto":
        count = g.auto_discover_from_memory(
            min_shared_terms=args.min_terms,
            max_pairs=args.max_pairs,
        )
        print(f"✅ Auto-discovered {count} relations")

    elif args.command == "stats":
        stats = g.get_stats()
        print("📊 GRAPH STATS")
        print(f"   Nodes:  {stats.total_nodes}")
        print(f"   Edges:  {stats.total_edges}")
        print(f"   Isolated: {stats.isolated_nodes}")
        if stats.edge_types:
            print(f"   Edge types:")
            for rtype, cnt in sorted(stats.edge_types.items()):
                print(f"     {rtype}: {cnt}")

    elif args.command == "clear":
        g.clear()
        print("🗑 Graph cleared")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
