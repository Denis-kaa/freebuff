# core_02/memory_store.py — Memory Store + Knowledge Graph
# Organizational Memory Engine (RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md §3-§5)
# SQLite (stdlib sqlite3), база: data_13/context.db (существующая).

"""Хранилище Organizational Memory: knowledge objects + граф связей.

Этап 3.1 (Memory Store) и 3.2 (Knowledge Graph) из PLAN_NEXT_OPERATIONS.md.
Таблицы создаются идемпотентно (CREATE TABLE IF NOT EXISTS) и не трогают
существующие таблицы context.db.

API:
    store_knowledge(...)          -> knowledge_id
    link_knowledge(source, target, rel_type, weight=1.0)
    query_by_type(kind)           -> list[dict***REMOVED***
    record_learning_event(...)    -> event_id
    get_analytics(metric, ...)    -> float | None
    get_confidence, update_feedback (Learning Loop §7)
    find_related(id, rel_types, max_depth=2) -> list[dict***REMOVED***
    find_patterns()               -> list[dict***REMOVED***
    shortest_path(from_id, to_id) -> list[dict***REMOVED***
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
***REMOVED***
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core_02.remote_db import RemoteDB, _FakeRow

logger = logging.getLogger(__name__)

# ─── Константы ────────────────────────────────────────────────────────────

# 10 типов Knowledge Objects (RFC §3.1)
KNOWLEDGE_KINDS: Tuple[str, ...***REMOVED*** = (
    "adr", "lesson", "pattern", "rule", "observation",
    "candidate", "checklist", "guideline", "faq", "workflow",
)

# 9 rel_types Organizational Memory (RFC §5) — расширение базовых из graph_index
ORG_REL_TYPES: Tuple[str, ...***REMOVED*** = (
    "supports", "contradicts", "duplicates", "supersedes",
    "derived_from", "caused_by", "resolved_by", "generalizes", "specializes",
)

# Базовые rel_types из scripts_01/graph_index.py (совместимость)
BASE_REL_TYPES: Tuple[str, ...***REMOVED*** = (
    "child", "contains", "depends", "parent", "references", "related", "tagged",
)

# Полный реестр допустимых типов связей
REL_TYPES: Tuple[str, ...***REMOVED*** = ORG_REL_TYPES + BASE_REL_TYPES

# Стадии жизненного цикла Knowledge Object
LIFECYCLE_STAGES: Tuple[str, ...***REMOVED*** = ("raw", "candidate", "validated", "review", "superseded", "archived")

# Пороги confidence (RFC §7)
REVIEW_CONFIDENCE = 0.3
VALIDATED_CONFIDENCE = 0.9
VALIDATED_MIN_EVIDENCE = 5
DECAY_AFTER_DAYS = 90  # confidence затухает при неиспользовании


# ─── Вспомогательные ──────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "ko") -> str:
    return f"{prefix***REMOVED***-{uuid.uuid4().hex[:12***REMOVED******REMOVED***"


def _row_to_dict(row: sqlite3.Row | Any) -> Dict[str, Any***REMOVED***:
    """Преобразовать строку (sqlite3.Row или _FakeRow) в словарь."""
    d = dict(row)
    for key in ("tags", "sources", "metadata_json"):
        if key in d and isinstance(d.get(key), str):
            try:
                d[key***REMOVED*** = json.loads(d[key***REMOVED***)
            except (json.JSONDecodeError, TypeError):
                d[key***REMOVED*** = None
    return d


class MemoryStoreError(Exception):
    """Ошибка домена Memory Store."""


class _CoworkResult:
    """Обёртка результата remote_db.execute() — имитирует sqlite3.Cursor.rowcount."""

    def __init__(self, rows: list) -> None:
        self._rows = rows
        # rqlite не возвращает rowcount для простого execute;
        # всегда >0 чтобы update_knowledge/delete_knowledge работали

    @property
    def rowcount(self) -> int:
        return 1  # оптимистично: операция выполнена

    def fetchall(self) -> list:
        return self._rows


# ─── Memory Store ─────────────────────────────────────────────────────────

class MemoryStore:
    """SQLite-хранилище Knowledge Objects + связей + событий обучения."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS knowledge_objects (
        id               TEXT PRIMARY KEY,
        kind             TEXT NOT NULL,
        status           TEXT NOT NULL DEFAULT 'draft',
        lifecycle_stage  TEXT NOT NULL DEFAULT 'raw',
        title            TEXT NOT NULL DEFAULT '',
        summary          TEXT NOT NULL DEFAULT '',
        content          TEXT NOT NULL DEFAULT '',
        confidence_score REAL NOT NULL DEFAULT 0.5,
        evidence_count   INTEGER NOT NULL DEFAULT 0,
        usage_count      INTEGER NOT NULL DEFAULT 0,
        success_count    INTEGER NOT NULL DEFAULT 0,
        failure_count    INTEGER NOT NULL DEFAULT 0,
        superseded_by    TEXT,
        source_event_id  TEXT,
        version          INTEGER NOT NULL DEFAULT 1,
        created_at       TEXT NOT NULL,
        updated_at       TEXT NOT NULL,
        last_used_at     TEXT,
        last_validated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS knowledge_tags (
        knowledge_id TEXT NOT NULL,
        tag          TEXT NOT NULL,
        PRIMARY KEY (knowledge_id, tag),
        FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
    );
    CREATE TABLE IF NOT EXISTS knowledge_sources (
        knowledge_id TEXT NOT NULL,
        file_path    TEXT NOT NULL,
        line         INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (knowledge_id, file_path, line),
        FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
    );
    CREATE TABLE IF NOT EXISTS knowledge_references (
        knowledge_id TEXT NOT NULL,
        ref_url      TEXT NOT NULL,
        ref_type     TEXT NOT NULL DEFAULT 'url',
        PRIMARY KEY (knowledge_id, ref_url),
        FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
    );
    CREATE TABLE IF NOT EXISTS knowledge_links (
        source_id  TEXT NOT NULL,
        target_id  TEXT NOT NULL,
        rel_type   TEXT NOT NULL,
        weight     REAL NOT NULL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        PRIMARY KEY (source_id, target_id, rel_type),
        FOREIGN KEY (source_id) REFERENCES knowledge_objects(id),
        FOREIGN KEY (target_id) REFERENCES knowledge_objects(id)
    );
    CREATE TABLE IF NOT EXISTS knowledge_events (
        event_id         TEXT NOT NULL,
        knowledge_id     TEXT NOT NULL,
        relation_type    TEXT NOT NULL DEFAULT 'source',
        created_at       TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (event_id, knowledge_id),
        FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
    );
    CREATE TABLE IF NOT EXISTS learning_events (
        id               TEXT PRIMARY KEY,
        trigger_id       TEXT,
        context_snapshot TEXT NOT NULL DEFAULT '{***REMOVED***',
        outcome          TEXT NOT NULL DEFAULT 'neutral',
        lesson_id        TEXT,
        created_at       TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS experience_analytics (
        metric_name  TEXT NOT NULL,
        metric_value REAL NOT NULL,
        dimension    TEXT NOT NULL DEFAULT 'global',
        recorded_at  TEXT NOT NULL,
        PRIMARY KEY (metric_name, dimension, recorded_at)
    );
    CREATE INDEX IF NOT EXISTS idx_ko_kind ON knowledge_objects(kind);
    CREATE INDEX IF NOT EXISTS idx_ko_stage ON knowledge_objects(lifecycle_stage);
    CREATE INDEX IF NOT EXISTS idx_ko_confidence ON knowledge_objects(confidence_score);
    CREATE INDEX IF NOT EXISTS idx_links_target ON knowledge_links(target_id);
    """

    def __init__(self, db_path: str | Path = "data_13/context.db", *, remote_db: RemoteDB | None = None):
        """Инициализировать MemoryStore.

        Parameters
        ----------
        db_path : str | Path
            Путь к локальной SQLite БД (используется если remote_db=None).
        remote_db : RemoteDB | None
            Подключение к rqlite для Cowork-режима. Если передано,
            ВСЕ операции идут через удалённую БД, локальная не используется.
        """
        self._remote_db = remote_db
        self._conn: sqlite3.Connection | None = None

        if remote_db is not None:
            # Cowork mode: schema через remote, без локального подключения
            remote_db.executescript(self.SCHEMA)
            logger.info("MemoryStore: cowork mode (rqlite)")
        else:
            # Local mode
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            # R-1 (069_19_first_vertical_slice_v0_1 §34.7): WAL + serialized writes
            self._conn.execute("PRAGMA foreign_keys = ON")
            try:
                self._conn.execute("PRAGMA journal_mode = WAL")
            except sqlite3.Error:  # pragma: no cover — WAL необязателен на экзотичных FS
                pass
            self._conn.executescript(self.SCHEMA)
            self._conn.commit()

    # ── жизненный цикл соединения ────────────────────────────────────

    @property
    def is_remote(self) -> bool:
        """True если используется удалённая БД (Cowork-режим)."""
        return self._remote_db is not None

    def close(self) -> None:
        if self._remote_db:
            self._remote_db.close()
        elif self._conn:
            self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _execute(self, sql: str, params: Sequence[Any***REMOVED*** = ()) -> Any:
        """Выполнить SQL. В remote-режиме возвращает список _FakeRow,
        в локальном — sqlite3.Cursor."""
        if self._remote_db:
            result = self._remote_db.execute(sql, params)
            # Для совместимости: возвращаем объект с .rowcount для INSERT/UPDATE/DELETE
            return _CoworkResult(result)
        assert self._conn is not None
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def _fetchall(self, sql: str, params: Sequence[Any***REMOVED*** = ()) -> list:
        """Выполнить SELECT и вернуть список строк (sqlite3.Row или _FakeRow)."""
        if self._remote_db:
            return self._remote_db.fetchall(sql, params)
        assert self._conn is not None
        return self._conn.execute(sql, params).fetchall()

    # ── CRUD Knowledge Objects ───────────────────────────────────────
    def store_knowledge(
        self,
        kind: str,
        content: str = "",
        title: str = "",
        summary: str = "",
        tags: Iterable[str***REMOVED*** = (),
        sources: Iterable[Dict[str, Any***REMOVED******REMOVED*** = (),
        references: Iterable[Dict[str, Any***REMOVED******REMOVED*** = (),
        lifecycle_stage: str = "raw",
        status: str = "draft",
        confidence_score: float = 0.5,
        source_event_id: Optional[str***REMOVED*** = None,
        knowledge_id: Optional[str***REMOVED*** = None,
        superseded_by: Optional[str***REMOVED*** = None,
    ) -> str:
        """Создать Knowledge Object (RFC §3.2). Возвращает knowledge_id."""
        if kind not in KNOWLEDGE_KINDS:
            raise MemoryStoreError(
                f"Неизвестный kind '{kind***REMOVED***'. Допустимые: {', '.join(KNOWLEDGE_KINDS)***REMOVED***"
            )
        if lifecycle_stage not in LIFECYCLE_STAGES:
            raise MemoryStoreError(f"Неизвестная стадия '{lifecycle_stage***REMOVED***'")
        kid = knowledge_id or _new_id("ko")
        now = _now()
        self._execute(
            """INSERT OR REPLACE INTO knowledge_objects
               (id, kind, status, lifecycle_stage, title, summary, content,
                confidence_score, source_event_id, superseded_by, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (kid, kind, status, lifecycle_stage, title, summary, content,
             confidence_score, source_event_id, superseded_by, now, now),
        )
        for tag in set(tags):
            self._execute(
                "INSERT OR IGNORE INTO knowledge_tags (knowledge_id, tag) VALUES (?,?)",
                (kid, tag),
            )
        for src in sources:
            self._execute(
                """INSERT OR IGNORE INTO knowledge_sources (knowledge_id, file_path, line)
                   VALUES (?,?,?)""",
                (kid, src.get("file_path") or src.get("file", ""), src.get("line") or 0),
            )
        for ref in references:
            self._execute(
                """INSERT OR IGNORE INTO knowledge_references (knowledge_id, ref_url, ref_type)
                   VALUES (?,?,?)""",
                (kid, ref.get("url") or ref.get("ref_url", ""), ref.get("ref_type", "url")),
            )
        return kid

    def update_knowledge(self, knowledge_id: str, **fields: Any) -> bool:
        """Обновить поля Knowledge Object. Возвращает True если объект найден."""
        allowed = {"title", "summary", "content", "status", "lifecycle_stage",
                   "confidence_score", "superseded_by"***REMOVED***
        # None = «не менять» (позволяет обновлять subset полей без знания остальных)
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None***REMOVED***
        if not updates:
            return self.get_knowledge(knowledge_id) is not None
        updates["updated_at"***REMOVED*** = _now()
        cols = ", ".join(f"{k***REMOVED***=?" for k in updates)
        cur = self._execute(
            f"UPDATE knowledge_objects SET {cols***REMOVED*** WHERE id=?",
            (*updates.values(), knowledge_id),
        )
        return cur.rowcount > 0

    def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        row = self._fetchall(
            "SELECT * FROM knowledge_objects WHERE id=?", (knowledge_id,)
        )
        if not row:
            return None
        ko = _row_to_dict(row[0***REMOVED***)
        ko["tags"***REMOVED*** = [r["tag"***REMOVED*** for r in self._fetchall(
            "SELECT tag FROM knowledge_tags WHERE knowledge_id=?", (knowledge_id,))***REMOVED***
        return ko

    def query_by_type(self, kind: str, limit: int = 100) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Поиск Knowledge Objects по kind (RFC §3.1)."""
        rows = self._fetchall(
            "SELECT * FROM knowledge_objects WHERE kind=? ORDER BY updated_at DESC LIMIT ?",
            (kind, limit),
        )
        return [_row_to_dict(r) for r in rows***REMOVED***

    def query_all(self, limit: int = 500) -> List[Dict[str, Any***REMOVED******REMOVED***:
        rows = self._fetchall(
            "SELECT * FROM knowledge_objects ORDER BY updated_at DESC LIMIT ?", (limit,)
        )
        return [_row_to_dict(r) for r in rows***REMOVED***

    def count_objects(self, kind: Optional[str***REMOVED*** = None) -> int:
        if kind:
            return self._fetchall(
                "SELECT COUNT(*) AS c FROM knowledge_objects WHERE kind=?", (kind,)
            )[0***REMOVED***["c"***REMOVED***
        return self._fetchall("SELECT COUNT(*) AS c FROM knowledge_objects")[0***REMOVED***["c"***REMOVED***

    def delete_knowledge(self, knowledge_id: str) -> bool:
        cur = self._execute("DELETE FROM knowledge_objects WHERE id=?", (knowledge_id,))
        return cur.rowcount > 0

    # ── Knowledge Graph (§5) ─────────────────────────────────────────
    def link_knowledge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        weight: float = 1.0,
    ) -> None:
        """Создать ребро графа. rel_type — из REL_TYPES."""
        if rel_type not in REL_TYPES:
            raise MemoryStoreError(
                f"Неизвестный rel_type '{rel_type***REMOVED***'. Допустимые: {', '.join(REL_TYPES)***REMOVED***"
            )
        self._execute(
            """INSERT OR REPLACE INTO knowledge_links
               (source_id, target_id, rel_type, weight, created_at)
               VALUES (?,?,?,?,?)""",
            (source_id, target_id, rel_type, weight, _now()),
        )

    def find_related(
        self,
        knowledge_id: str,
        rel_types: Optional[Iterable[str***REMOVED******REMOVED*** = None,
        max_depth: int = 2,
    ) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """BFS по графу связей до max_depth. Возвращает [{knowledge, rel_type, depth, weight***REMOVED******REMOVED***."""
        if max_depth < 1:
            return [***REMOVED***
        rel_filter = set(rel_types) if rel_types else set(REL_TYPES)
        visited = {knowledge_id***REMOVED***
        queue: deque[Tuple[str, int***REMOVED******REMOVED*** = deque([(knowledge_id, 0)***REMOVED***)
        results: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
        while queue:
            node, depth = queue.popleft()
            if depth >= max_depth:
                continue
            rows = self._fetchall(
                """SELECT source_id, target_id, rel_type, weight
                   FROM knowledge_links WHERE source_id=? OR target_id=?""",
                (node, node),
            )
            for r in rows:
                if r["rel_type"***REMOVED*** not in rel_filter:
                    continue
                neighbor = r["target_id"***REMOVED*** if r["source_id"***REMOVED*** == node else r["source_id"***REMOVED***
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                ko = self.get_knowledge(neighbor)
                if ko:
                    results.append({
                        "knowledge": ko,
                        "rel_type": r["rel_type"***REMOVED***,
                        "depth": depth + 1,
                        "weight": r["weight"***REMOVED***,
                    ***REMOVED***)
                queue.append((neighbor, depth + 1))
        results.sort(key=lambda x: (x["depth"***REMOVED***, -x["weight"***REMOVED***))
        return results

    def shortest_path(self, from_id: str, to_id: str) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Кратчайший путь между двумя Knowledge Objects (BFS). Пустой список = пути нет."""
        if from_id == to_id:
            return [***REMOVED***
        visited = {from_id***REMOVED***
        parent: Dict[str, Tuple[str, str, float***REMOVED******REMOVED*** = {***REMOVED***  # node -> (prev, rel_type, weight)
        queue: deque[str***REMOVED*** = deque([from_id***REMOVED***)
        while queue:
            node = queue.popleft()
            rows = self._fetchall(
                """SELECT source_id, target_id, rel_type, weight
                   FROM knowledge_links WHERE source_id=? OR target_id=?""",
                (node, node),
            )
            for r in rows:
                neighbor = r["target_id"***REMOVED*** if r["source_id"***REMOVED*** == node else r["source_id"***REMOVED***
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor***REMOVED*** = (node, r["rel_type"***REMOVED***, r["weight"***REMOVED***)
                if neighbor == to_id:
                    # восстанавливаем путь
                    path: List[Dict[str, Any***REMOVED******REMOVED*** = [***REMOVED***
                    cur = to_id
                    while cur != from_id:
                        prev, rel, w = parent[cur***REMOVED***
                        path.append({"from": prev, "to": cur, "rel_type": rel, "weight": w***REMOVED***)
                        cur = prev
                    path.reverse()
                    return path
                queue.append(neighbor)
        return [***REMOVED***

    def find_patterns(self, min_occurrences: int = 2) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Паттерн-детекция: повторяющиеся тройки A--rel1-->B--rel2-->C.

        Возвращает [{pattern, occurrences, examples:[(a,b,c)***REMOVED******REMOVED******REMOVED***.
        """
        rows = self._fetchall(
            """SELECT source_id, target_id, rel_type FROM knowledge_links"""
        )
        # строим граф смежности
        adj: Dict[str, List[Tuple[str, str***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        for r in rows:
            adj.setdefault(r["source_id"***REMOVED***, [***REMOVED***).append((r["target_id"***REMOVED***, r["rel_type"***REMOVED***))
        patterns: Dict[Tuple[str, str***REMOVED***, List[Tuple[str, str, str***REMOVED******REMOVED******REMOVED*** = {***REMOVED***
        for a, edges in adj.items():
            for b, r1 in edges:
                for c, r2 in adj.get(b, [***REMOVED***):
                    key = (r1, r2)
                    patterns.setdefault(key, [***REMOVED***).append((a, b, c))
        result = [***REMOVED***
        for (r1, r2), examples in patterns.items():
            # дедупликация троек
            uniq = list(dict.fromkeys(examples))
            if len(uniq) >= min_occurrences:
                result.append({
                    "pattern": f"{r1***REMOVED*** → {r2***REMOVED***",
                    "occurrences": len(uniq),
                    "examples": uniq,
                ***REMOVED***)
        result.sort(key=lambda x: -x["occurrences"***REMOVED***)
        return result

    # ── Learning Events (RFC §7) ─────────────────────────────────────
    def record_learning_event(
        self,
        trigger_id: str,
        context_snapshot: Dict[str, Any***REMOVED***,
        outcome: str = "neutral",
        lesson_id: Optional[str***REMOVED*** = None,
    ) -> str:
        """Зафиксировать событие обучения (AFC: trigger → feedback)."""
        if outcome not in ("success", "failure", "neutral"):
            raise MemoryStoreError("outcome должен быть success|failure|neutral")
        eid = _new_id("ev")
        self._execute(
            """INSERT INTO learning_events
               (id, trigger_id, context_snapshot, outcome, lesson_id, created_at)
               VALUES (?,?,?,?,?,?)""",
            (eid, trigger_id, json.dumps(context_snapshot, ensure_ascii=False),
             outcome, lesson_id, _now()),
        )
        return eid

    def list_learning_events(self, limit: int = 100) -> List[Dict[str, Any***REMOVED******REMOVED***:
        rows = self._fetchall(
            "SELECT * FROM learning_events ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [_row_to_dict(r) for r in rows***REMOVED***

    # ── Feedback & Confidence (§7) ───────────────────────────────────
    def update_feedback(self, knowledge_id: str, outcome: str) -> Optional[float***REMOVED***:
        """Обновить usage/success/failure и пересчитать confidence_score.

        RFC §7: confidence = success / (success + failure). Пороги:
        < 0.3 → status 'review'; > 0.9 и evidence >= 5 → 'validated'.
        Возвращает новое значение confidence или None если объект не найден.
        """
        ko = self.get_knowledge(knowledge_id)
        if not ko:
            return None
        usage = ko["usage_count"***REMOVED*** + 1
        success = ko["success_count"***REMOVED*** + (1 if outcome == "success" else 0)
        failure = ko["failure_count"***REMOVED*** + (1 if outcome == "failure" else 0)
        evidence = success + failure
        confidence = success / evidence if evidence else ko["confidence_score"***REMOVED***
        # затухание при неиспользовании 90+ дней (RFC §7)
        if ko.get("last_used_at"):
            try:
                last = datetime.fromisoformat(ko["last_used_at"***REMOVED***)
                if (datetime.now(timezone.utc) - last).days > DECAY_AFTER_DAYS:
                    confidence *= 0.5
            except (ValueError, TypeError):
                pass
        if confidence < REVIEW_CONFIDENCE:
            status = "review"
        elif confidence > VALIDATED_CONFIDENCE and evidence >= VALIDATED_MIN_EVIDENCE:
            status = "validated"
        else:
            status = ko["status"***REMOVED***
        now = _now()
        self._execute(
            """UPDATE knowledge_objects
               SET usage_count=?, success_count=?, failure_count=?,
                   evidence_count=?, confidence_score=?, status=?, last_used_at=?,
                   last_validated_at=CASE WHEN ?='validated' AND ?!=? THEN ? ELSE last_validated_at END,
                   updated_at=?
               WHERE id=?""",
            (usage, success, failure, evidence, confidence, status, now,
             status, status, ko["status"***REMOVED***, now, now, knowledge_id),
        )
        self.record_analytics("confidence", confidence, dimension=knowledge_id)
        return confidence

    # ── Experience Analytics (§8) ────────────────────────────────────
    def record_analytics(self, metric_name: str, metric_value: float, dimension: str = "global") -> None:
        self._execute(
            """INSERT INTO experience_analytics (metric_name, metric_value, dimension, recorded_at)
               VALUES (?,?,?,?)""",
            (metric_name, float(metric_value), dimension, _now()),
        )

    def get_analytics(
        self,
        metric_name: str,
        dimension: str = "global",
        days: int = 30,
    ) -> Optional[float***REMOVED***:
        """Среднее значение метрики за последние N дней (RFC §8)."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self._fetchall(
            """SELECT AVG(metric_value) AS avg_val FROM experience_analytics
               WHERE metric_name=? AND dimension=? AND recorded_at >= ?""",
            (metric_name, dimension, since),
        )
        val = rows[0***REMOVED***["avg_val"***REMOVED*** if rows else None
        return float(val) if val is not None else None

    def analytics_report(self, days: int = 30) -> Dict[str, Any***REMOVED***:
        """Отчёт по метрикам (RFC §8)."""
        metrics = self._fetchall(
            """SELECT metric_name, COUNT(*) AS n, AVG(metric_value) AS avg_val,
                      MAX(metric_value) AS max_val
               FROM experience_analytics
               WHERE recorded_at >= ?
               GROUP BY metric_name""",
            ((datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),),
        )
        return {
            "days": days,
            "metrics": [dict(r) for r in metrics***REMOVED***,
            "total_events": self.count_learning_events(),
            "total_objects": self.count_objects(),
        ***REMOVED***

    def count_learning_events(self) -> int:
        return self._fetchall("SELECT COUNT(*) AS c FROM learning_events")[0***REMOVED***["c"***REMOVED***
