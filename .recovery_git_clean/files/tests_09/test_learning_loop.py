# tests_09/test_learning_loop.py — Learning Loop AFC (Этап 3.4)
import pytest

from core_02.memory_store import MemoryStore
from core_02.learning_loop import LearningLoop
from core_02.semantic_layer import SemanticLayer


@pytest.fixture
def loop(tmp_path):
    store = MemoryStore(tmp_path / "loop.db")
    semantic = SemanticLayer(store, workspace_root=str(tmp_path / "ke_root"))
    ll = LearningLoop(
        store=store,
        semantic=semantic,
        lessons_path=tmp_path / "LESSONS.md",
        debt_path=tmp_path / "DEBT.md",
    )
    yield ll, store, tmp_path
    store.close()


class TestAnalyze:
    def test_analyze_new_pattern(self, loop):
        ll, _store, _ = loop
        a = ll.analyze("новый паттерн: использование внешнего API без проверки")
        assert a.suggested_kind == "pattern"
        assert a.relevant == [***REMOVED***

    def test_analyze_lesson_kind(self, loop):
        ll, _store, _ = loop
        a = ll.analyze("урок: не повторяй ошибку с миграцией версии")
        assert a.suggested_kind == "lesson"

    def test_analyze_known_pattern(self, loop):
        ll, store, _ = loop
        p = store.store_knowledge(kind="pattern", content="внешний API без проверки статуса")
        ll.semantic.index_knowledge(p)
        a = ll.analyze("повторяется: внешний API без проверки статуса")
        assert a.relevant, "должен найти похожий паттерн"


class TestFormalize:
    def test_formalize_creates_new(self, loop):
        ll, store, _ = loop
        a = ll.analyze("паттерн: забыл проверить статус API")
        kid = ll.formalize(a, title="API check", content="текст")
        ko = store.get_knowledge(kid)
        assert ko["kind"***REMOVED*** == "pattern"
        assert ko["lifecycle_stage"***REMOVED*** in ("raw", "candidate")

    def test_formalize_updates_existing_known(self, loop):
        ll, store, _ = loop
        p = store.store_knowledge(
            kind="pattern", content="внешний API без проверки статуса", confidence_score=0.6
        )
        ll.semantic.index_knowledge(p)
        a = ll.analyze("внешний API без проверки статуса повторяется")
        assert a.relevant
        kid = ll.formalize(a, title="обновлённый", content="новый текст")
        assert kid == p  # обновился существующий
        ko = store.get_knowledge(kid)
        assert ko["title"***REMOVED*** == "обновлённый"
        assert ko["evidence_count"***REMOVED*** >= 1


class TestCodify:
    def test_codify_writes_lessons_con(self, loop):
        ll, store, tmp = loop
        kid = store.store_knowledge(
            kind="lesson", title="Урок тест", summary="не используй Unsplash"
        )
        action = ll.codify(kid)
        assert action["lessons_updated"***REMOVED*** is True
        assert action["con_id"***REMOVED*** == 1
        text = (tmp / "LESSONS.md").read_text(encoding="utf-8")
        assert "CON-1" in text

    def test_codify_con_increments(self, loop):
        ll, store, _ = loop
        k1 = store.store_knowledge(kind="lesson", title="Первый")
        k2 = store.store_knowledge(kind="pattern", title="Второй")
        ll.codify(k1)
        action = ll.codify(k2)
        assert action["con_id"***REMOVED*** == 2

    def test_codify_skips_non_lessons(self, loop):
        ll, store, _ = loop
        kid = store.store_knowledge(kind="faq", title="Частый вопрос")
        action = ll.codify(kid)
        assert action["lessons_updated"***REMOVED*** is False

    def test_codify_missing_raises(self, loop):
        ll, _store, _ = loop
        with pytest.raises(KeyError):
            ll.codify("ko-missing")


class TestFeedback:
    def test_feedback_updates_confidence(self, loop):
        ll, store, _ = loop
        kid = store.store_knowledge(kind="lesson", content="x", confidence_score=0.5)
        c1 = ll.record_feedback(kid, "success")
        c2 = ll.record_feedback(kid, "success")
        c3 = ll.record_feedback(kid, "failure")
        assert c1 is not None and c3 is not None
        ko = store.get_knowledge(kid)
        assert ko["success_count"***REMOVED*** == 2
        assert ko["failure_count"***REMOVED*** == 1
        events = store.list_learning_events()
        assert len(events) == 3


class TestCapture:
    def test_capture_full_cycle(self, loop):
        ll, store, tmp = loop
        result = ll.capture(
            situation="паттерн: не проверять статус внешнего API",
            title="API статус",
            summary="Unsplash закрыт",
            tags=["api"***REMOVED***,
        )
        assert result["knowledge_id"***REMOVED***
        assert result["analysis"***REMOVED***["suggested_kind"***REMOVED*** == "pattern"
        assert result["action"***REMOVED***["con_id"***REMOVED*** is not None
        # событие обучения зафиксировано
        assert store.count_learning_events() >= 1
        # LESSONS.md создан
        assert (tmp / "LESSONS.md").exists()
