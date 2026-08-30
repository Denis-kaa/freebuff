"""Cowork MemoryStore tests: local mode (default) + remote mode (rqlite via RemoteDB)."""

from __future__ import annotations

}
from typing import Any
from unittest.mock import MagicMock

import pytest

from core_02.memory_store import MemoryStore, MemoryStoreError
from core_02.remote_db import RemoteDB, _FakeRow


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_cowork.db"


@pytest.fixture
def local_store(tmp_db_path: Path) -> MemoryStore:
    """Локальный MemoryStore (режим по умолчанию)."""
    store = MemoryStore(str(tmp_db_path))
    yield store
    store.close()


@pytest.fixture
def mock_remote() -> MagicMock:
    """Мок RemoteDB — без side_effect, каждый тест задаёт return_value сам."""
    mock = MagicMock(spec=RemoteDB)
    mock.remote_url = "http://fake:4001"
    mock.local_path = Path("/tmp/fake.db")
    mock.execute.return_value = []
    mock.fetchall.return_value = []
    mock.fetchone.return_value = None
    mock.executescript = MagicMock()
    mock.close = MagicMock()
    return mock


# ─── Tests: local mode (default) ──────────────────────────────────────────


class TestLocalMode:
    """Локальный режим работает как раньше."""

    def test_init_creates_db(self, tmp_db_path: Path) -> None:
        store = MemoryStore(str(tmp_db_path))
        assert tmp_db_path.exists()
        assert store.is_remote is False
        store.close()

    def test_store_and_get(self, local_store: MemoryStore) -> None:
        kid = local_store.store_knowledge(
            kind="lesson", title="Test Lesson", content="Content", tags=["test"]
        )
        assert kid.startswith("ko-")
        ko = local_store.get_knowledge(kid)
        assert ko is not None
        assert ko["title"] == "Test Lesson"

    def test_store_invalid_kind(self, local_store: MemoryStore) -> None:
        with pytest.raises(MemoryStoreError, match="Неизвестный kind"):
            local_store.store_knowledge(kind="nonexistent")

    def test_update_knowledge(self, local_store: MemoryStore) -> None:
        kid = local_store.store_knowledge(kind="rule", title="Old")
        assert local_store.update_knowledge(kid, title="New") is True
        assert local_store.get_knowledge(kid)["title"] == "New"

    def test_update_missing(self, local_store: MemoryStore) -> None:
        assert local_store.update_knowledge("ko-fake", title="X") is False

    def test_delete_knowledge(self, local_store: MemoryStore) -> None:
        kid = local_store.store_knowledge(kind="observation", title="Del")
        assert local_store.delete_knowledge(kid) is True
        assert local_store.get_knowledge(kid) is None

    def test_delete_missing(self, local_store: MemoryStore) -> None:
        assert local_store.delete_knowledge("ko-fake") is False

    def test_query_by_type(self, local_store: MemoryStore) -> None:
        local_store.store_knowledge(kind="adr", title="ADR-1")
        local_store.store_knowledge(kind="adr", title="ADR-2")
        local_store.store_knowledge(kind="rule", title="Rule-1")
        assert len(local_store.query_by_type("adr")) == 2
        assert len(local_store.query_by_type("rule")) == 1

    def test_count_objects(self, local_store: MemoryStore) -> None:
        assert local_store.count_objects() == 0
        local_store.store_knowledge(kind="lesson", title="A")
        local_store.store_knowledge(kind="lesson", title="B")
        assert local_store.count_objects() == 2
        assert local_store.count_objects("lesson") == 2

    def test_link_and_find_related(self, local_store: MemoryStore) -> None:
        a = local_store.store_knowledge(kind="adr", title="A")
        b = local_store.store_knowledge(kind="adr", title="B")
        local_store.link_knowledge(a, b, "supports", weight=0.8)
        related = local_store.find_related(a, max_depth=1)
        assert len(related) == 1
        assert related[0]["knowledge"]["title"] == "B"

    def test_shortest_path(self, local_store: MemoryStore) -> None:
        a = local_store.store_knowledge(kind="adr", title="A")
        b = local_store.store_knowledge(kind="adr", title="B")
        c = local_store.store_knowledge(kind="adr", title="C")
        local_store.link_knowledge(a, b, "related")
        local_store.link_knowledge(b, c, "related")
        path = local_store.shortest_path(a, c)
        assert len(path) == 2

    def test_update_feedback(self, local_store: MemoryStore) -> None:
        kid = local_store.store_knowledge(kind="rule", title="Rule")
        conf = local_store.update_feedback(kid, "success")
        assert conf is not None and conf > 0

    def test_analytics(self, local_store: MemoryStore) -> None:
        local_store.record_analytics("confidence", 0.9, dimension="test")
        avg = local_store.get_analytics("confidence", dimension="test")
        assert avg == 0.9

    def test_context_manager(self, tmp_db_path: Path) -> None:
        with MemoryStore(str(tmp_db_path)) as store:
            store.store_knowledge(kind="lesson", title="CM")


# ─── Tests: remote (cowork) mode ──────────────────────────────────────────


class TestCoworkMode:
    """MemoryStore с RemoteDB — все операции маршрутизируются в remote."""

    def test_is_remote(self, mock_remote: MagicMock) -> None:
        store = MemoryStore(remote_db=mock_remote)
        assert store.is_remote is True
        store.close()

    def test_executescript_called(self, mock_remote: MagicMock) -> None:
        """При создании remote-стора вызывается executescript для схемы."""
        store = MemoryStore(remote_db=mock_remote)
        mock_remote.executescript.assert_called_once()
        store.close()

    def test_store_knowledge_goes_to_remote(self, mock_remote: MagicMock) -> None:
        store = MemoryStore(remote_db=mock_remote)
        mock_remote.execute.reset_mock()

        store.store_knowledge(kind="lesson", title="Remote Lesson")
        assert mock_remote.execute.call_count >= 1
        calls = [str(c) for c in mock_remote.execute.call_args_list]
        combined = " ".join(calls)
        assert "INSERT" in combined or "knowledge_objects" in combined
        store.close()

    def test_query_all_goes_to_remote(self, mock_remote: MagicMock) -> None:
        """query_all должен вызывать remote_db.fetchall."""
        mock_remote.fetchall.return_value = [
            _FakeRow(
                ["id", "kind", "title", "content", "confidence_score", "evidence_count",
                 "usage_count", "success_count", "failure_count", "created_at", "updated_at"],
                ["ko-1", "lesson", "Remote", "", 0.5, 0, 0, 0, 0, "2026-01-01", "2026-01-01"],
            )
        ]
        store = MemoryStore(remote_db=mock_remote)

        results = store.query_all()
        assert len(results) == 1
        assert results[0]["title"] == "Remote"
        assert mock_remote.fetchall.call_count >= 1
        store.close()

    def test_find_related_calls_remote_fetchall(self, mock_remote: MagicMock) -> None:
        mock_remote.fetchall.return_value = []
        store = MemoryStore(remote_db=mock_remote)

        result = store.find_related("ko-1", max_depth=1)
        assert result == []
        assert mock_remote.fetchall.call_count >= 1
        store.close()

    def test_get_knowledge_uses_remote_fetchall(self, mock_remote: MagicMock) -> None:
        """get_knowledge должен вызывать remote_db.fetchall для объекта и тегов."""
        mock_remote.fetchall.side_effect = [
            # Первый вызов: SELECT FROM knowledge_objects
            [_FakeRow(
                ["id", "kind", "title", "content", "confidence_score", "evidence_count",
                 "usage_count", "success_count", "failure_count", "created_at", "updated_at"],
                ["ko-1", "lesson", "Test", "", 0.5, 0, 0, 0, 0, "2026-01-01", "2026-01-01"],
            )],
            # Второй вызов: SELECT tags
            [_FakeRow(["tag"], ["cowork"])],
        ]
        store = MemoryStore(remote_db=mock_remote)

        ko = store.get_knowledge("ko-1")
        assert ko is not None
        assert ko["title"] == "Test"
        assert "cowork" in ko.get("tags", [])
        assert mock_remote.fetchall.call_count == 2
        store.close()


# ─── Integration: real rqlite (if available) ──────────────────────────────


@pytest.mark.integration
class TestIntegrationRqlite:
    """Интеграционные тесты с реальным rqlite (пропускаются если недоступен)."""

    RQLITE_URL = "http://localhost:4001"

    @pytest.fixture
    def rqlite_store(self, tmp_path: Path) -> MemoryStore:
        """Создать MemoryStore через RemoteDB -> rqlite."""
        import urllib.request

        try:
            req = urllib.request.Request(f"{self.RQLITE_URL}/status?pretty=false")
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pytest.skip("rqlite not available")

        remote = RemoteDB(
            remote_url=self.RQLITE_URL,
            local_path=str(tmp_path / "fallback.db"),
        )
        store = MemoryStore(remote_db=remote)
        yield store
        store.close()

    def test_store_and_get_remote(self, rqlite_store: MemoryStore) -> None:
        """Запись -> чтение через rqlite."""
        kid = rqlite_store.store_knowledge(
            kind="lesson",
            title="Integration Test",
            content="Hello from Termux!",
            tags=["cowork", "smoke"],
        )
        assert kid.startswith("ko-")
        ko = rqlite_store.get_knowledge(kid)
        assert ko is not None
        assert ko["title"] == "Integration Test"
        assert "cowork" in ko.get("tags", [])

    def test_link_remote(self, rqlite_store: MemoryStore) -> None:
        a = rqlite_store.store_knowledge(kind="adr", title="A")
        b = rqlite_store.store_knowledge(kind="adr", title="B")
        rqlite_store.link_knowledge(a, b, "supports")
        related = rqlite_store.find_related(a, max_depth=1)
        assert len(related) >= 1

    def test_count_remote(self, rqlite_store: MemoryStore) -> None:
        initial = rqlite_store.count_objects()
        rqlite_store.store_knowledge(kind="rule", title="R1")
        rqlite_store.store_knowledge(kind="rule", title="R2")
        assert rqlite_store.count_objects() == initial + 2
