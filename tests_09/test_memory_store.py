# tests_09/test_memory_store.py — Memory Store + Knowledge Graph (Этап 3.1, 3.2)
import pytest

from core_02.memory_store import (
    MemoryStore,
    MemoryStoreError,
    KNOWLEDGE_KINDS,
    ORG_REL_TYPES,
    REL_TYPES,
)


@pytest.fixture
def store(tmp_path):
    ms = MemoryStore(tmp_path / "test_memory.db")
    yield ms
    ms.close()


# ─── Хранилище (3.1) ──────────────────────────────────────────────────────

class TestStoreKnowledge:
    def test_store_and_get(self, store):
        kid = store.store_knowledge(
            kind="lesson",
            content="Никогда не использовать Unsplash Source API — закрыт в 2024.",
            title="Урок: внешние API",
            tags=["api", "lessons"],
            sources=[{"file_path": "core_02/LESSONS.md"}],
        )
        ko = store.get_knowledge(kid)
        assert ko["id"] == kid
        assert ko["kind"] == "lesson"
        assert ko["title"] == "Урок: внешние API"
        assert "api" in ko["tags"]
        assert ko["lifecycle_stage"] == "raw"

    def test_invalid_kind_rejected(self, store):
        with pytest.raises(MemoryStoreError):
            store.store_knowledge(kind="nonsense", content="x")

    def test_invalid_stage_rejected(self, store):
        with pytest.raises(MemoryStoreError):
            store.store_knowledge(kind="lesson", content="x", lifecycle_stage="bad")

    def test_query_by_type(self, store):
        for k in ("lesson", "pattern", "lesson"):
            store.store_knowledge(kind=k, content=f"content-{k}")
        lessons = store.query_by_type("lesson")
        assert len(lessons) == 2
        assert store.count_objects("lesson") == 2
        assert store.count_objects() == 3

    def test_update_and_delete(self, store):
        kid = store.store_knowledge(kind="rule", content="a")
        assert store.update_knowledge(kid, content="b", status="active")
        assert store.get_knowledge(kid)["content"] == "b"
        assert store.delete_knowledge(kid) is True
        assert store.get_knowledge(kid) is None

    def test_all_kinds_known(self):
        assert "adr" in KNOWLEDGE_KINDS
        assert "workflow" in KNOWLEDGE_KINDS
        assert len(KNOWLEDGE_KINDS) == 10


# ─── Knowledge Graph (3.2) ────────────────────────────────────────────────

class TestKnowledgeGraph:
    def _seed_chain(self, store):
        a = store.store_knowledge(kind="pattern", content="A")
        b = store.store_knowledge(kind="lesson", content="B")
        c = store.store_knowledge(kind="rule", content="C")
        store.link_knowledge(a, b, "supports")
        store.link_knowledge(b, c, "derived_from")
        return a, b, c

    def test_link_and_find_related_depth1(self, store):
        a, b, _c = self._seed_chain(store)
        related = store.find_related(a, max_depth=1)
        assert len(related) == 1
        assert related[0]["rel_type"] == "supports"
        assert related[0]["knowledge"]["id"] == b

    def test_find_related_depth2(self, store):
        a, _b, c = self._seed_chain(store)
        related = store.find_related(a, max_depth=2)
        ids = {r["knowledge"]["id"] for r in related}
        assert c in ids
        depths = {r["knowledge"]["id"]: r["depth"] for r in related}
        assert depths[c] == 2

    def test_find_related_rel_type_filter(self, store):
        a, b, _c = self._seed_chain(store)
        related = store.find_related(a, rel_types=["contradicts"], max_depth=2)
        assert related == []
        related = store.find_related(a, rel_types=["supports"], max_depth=1)
        assert related[0]["knowledge"]["id"] == b

    def test_shortest_path(self, store):
        a, _b, c = self._seed_chain(store)
        path = store.shortest_path(a, c)
        assert [p["from"] for p in path] == [a, _b]
        assert [p["to"] for p in path] == [_b, c]
        assert [p["rel_type"] for p in path] == ["supports", "derived_from"]

    def test_shortest_path_none(self, store):
        a = store.store_knowledge(kind="pattern", content="A")
        z = store.store_knowledge(kind="rule", content="Z")
        assert store.shortest_path(a, z) == []

    def test_find_patterns(self, store):
        # Две одинаковые тройки A-sup->B-der->C и D-sup->E-der->F
        for n in ("A", "B", "C", "D", "E", "F"):
            store.store_knowledge(kind="pattern", content=n, knowledge_id=f"ko-{n}")
        store.link_knowledge("ko-A", "ko-B", "supports")
        store.link_knowledge("ko-B", "ko-C", "derived_from")
        store.link_knowledge("ko-D", "ko-E", "supports")
        store.link_knowledge("ko-E", "ko-F", "derived_from")
        patterns = store.find_patterns(min_occurrences=2)
        assert any(p["pattern"] == "supports → derived_from" for p in patterns)
        pat = next(p for p in patterns if p["pattern"] == "supports → derived_from")
        assert pat["occurrences"] == 2

    def test_invalid_rel_type(self, store):
        a = store.store_knowledge(kind="pattern", content="A")
        b = store.store_knowledge(kind="rule", content="B")
        with pytest.raises(MemoryStoreError):
            store.link_knowledge(a, b, "magic_link")

    def test_rel_types_registry(self):
        assert "supersedes" in ORG_REL_TYPES
        assert len(ORG_REL_TYPES) == 9
        assert "supports" in REL_TYPES
        assert "child" in REL_TYPES  # базовые из graph_index сохранены


# ─── Learning events + analytics ──────────────────────────────────────────

class TestLearningAndAnalytics:
    def test_record_learning_event(self, store):
        eid = store.record_learning_event(
            trigger_id="review-1",
            context_snapshot={"problem": "TDZ crash"},
            outcome="failure",
        )
        events = store.list_learning_events()
        assert events[0]["id"] == eid
        assert events[0]["outcome"] == "failure"

    def test_invalid_outcome(self, store):
        with pytest.raises(MemoryStoreError):
            store.record_learning_event(trigger_id="x", context_snapshot={}, outcome="maybe")

    def test_update_feedback_confidence(self, store):
        kid = store.store_knowledge(kind="lesson", content="x", confidence_score=0.5)
        store.update_feedback(kid, "success")
        store.update_feedback(kid, "success")
        c = store.update_feedback(kid, "failure")
        ko = store.get_knowledge(kid)
        assert ko["success_count"] == 2
        assert ko["failure_count"] == 1
        assert ko["usage_count"] == 3
        assert c is not None and 0.0 < c < 1.0
        assert abs(c - 2 / 3) < 1e-6

    def test_feedback_unknown_object(self, store):
        assert store.update_feedback("ko-missing", "success") is None

    def test_analytics_record_and_get(self, store):
        store.record_analytics("confidence", 0.8)
        store.record_analytics("confidence", 0.6)
        avg = store.get_analytics("confidence", days=7)
        assert avg is not None and abs(avg - 0.7) < 1e-6

    def test_analytics_report(self, store):
        store.record_learning_event(trigger_id="t", context_snapshot={}, outcome="neutral")
        report = store.analytics_report()
        assert report["total_events"] == 1
        assert "metrics" in report
