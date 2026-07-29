"""Тесты Knowledge Curator."""

from realtor_os.curator.knowledge import KnowledgeCurator


def test_learn_and_list(tmp_path) -> None:
    store = tmp_path / "knowledge.json"
    curator = KnowledgeCurator(store_path=store)
    curator.learn("холодные звонки", [
        {"title": "Книга", "url": "#", "why": "полезно"***REMOVED***,
    ***REMOVED***)
    assert "холодные звонки" in curator.list_topics()
