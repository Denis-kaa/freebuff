"""Тесты RAG."""

}

from realtor_os.rag.engine import RAGEngine


def test_ingest_and_search(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    engine = RAGEngine(db_path=db)
    count = engine.ingest("doc1", "Продажа квартиры в Пойковском. Договор купли-продажи.")
    assert count == 1
    results = engine.search("Пойковском")
    assert len(results) == 1
    assert "Пойковском" in results[0]["content"]


def test_empty_ingest(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    engine = RAGEngine(db_path=db)
    count = engine.ingest("doc1", "")
    assert count == 0
