# tests_09/test_semantic_layer.py — Semantic Layer поверх KnowledgeEngine (Этап 3.3)
import pytest

from core_02.memory_store import MemoryStore
from core_02.semantic_layer import SemanticLayer


@pytest.fixture
def layer(tmp_path):
    store = MemoryStore(tmp_path / "semantic.db")
    sl = SemanticLayer(store, workspace_root=str(tmp_path / "ke_root"))
    yield sl, store
    store.close()


class TestSemanticLayer:
    def test_index_and_search(self, layer):
        sl, store = layer
        kid = store.store_knowledge(
            kind="lesson",
            title="Undo/redo push-after",
            content="История хранит текущее состояние, undo берёт history[idx-1].",
            tags=["undo", "zustand"],
        )
        sl.index_knowledge(kid)
        hits = sl.semantic_search("undo redo история", top_k=5)
        assert any(k == kid for k, _s in hits)

    def test_search_unknown_query_empty_result(self, layer):
        sl, store = layer
        kid = store.store_knowledge(kind="rule", content="правило номер один")
        sl.index_knowledge(kid)
        # Поиск по отсутствующему слову не должен падать
        hits = sl.semantic_search("zxqjvbnm", top_k=5)
        assert isinstance(hits, list)

    def test_search_related_includes_graph(self, layer):
        sl, store = layer
        a = store.store_knowledge(kind="pattern", content="Picsum seed API для картинок")
        b = store.store_knowledge(kind="lesson", content="Unsplash закрыт, используй Picsum")
        store.link_knowledge(a, b, "supports")
        sl.index_knowledge(a)
        sl.index_knowledge(b)
        ctx = sl.search_related("картинки Picsum API", top_k=2, max_depth=1)
        assert len(ctx["hits"]) >= 1
        assert isinstance(ctx["related"], list)

    def test_find_similar_patterns_filters_kinds(self, layer):
        sl, store = layer
        p = store.store_knowledge(kind="pattern", content="повторяющийся паттерн ошибки X")
        r = store.store_knowledge(kind="rule", content="правило про X")
        sl.index_knowledge(p)
        sl.index_knowledge(r)
        res = sl.find_similar_patterns("паттерн ошибки X повторяется", top_k=5)
        kinds = {x["kind"] for x in res}
        assert kinds <= {"pattern", "lesson", "guideline", "adr", "anti_pattern"}
        assert all("knowledge_id" in x for x in res)

    def test_index_missing_object_raises(self, layer):
        sl, _store = layer
        with pytest.raises(KeyError):
            sl.index_knowledge("ko-does-not-exist")

    def test_reindex_all(self, layer):
        sl, store = layer
        for i in range(3):
            store.store_knowledge(kind="lesson", content=f"урок номер {i}")
        n = sl.reindex_all()
        assert n == 3

    def test_result_helpers_handle_tuples(self):
        # search() реального KnowledgeEngine возвращает кортежи (doc_id, score, ...)
        assert SemanticLayer._result_doc_id(("ko-1", 0.9, "content")) == "ko-1"
        assert abs(SemanticLayer._result_score(("ko-1", 0.9)) - 0.9) < 1e-9
        assert abs(SemanticLayer._result_score(("ko-1",)) - 1.0) < 1e-9
