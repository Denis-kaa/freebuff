"""Cowork ContextManager tests: local (default) + remote via mocked RemoteDB + integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts_01.context_manager import (
    ContextManager, SessionStatus, CheckpointType, _CoworkConn, _CoworkCursor,
)
from core_02.remote_db import RemoteDB, _FakeRow


# ─── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def local_cm(tmp_path: Path) -> ContextManager:
    """Локальный ContextManager."""
    ws = str(tmp_path / "workspace")
    cm = ContextManager(ws)
    yield cm


@pytest.fixture
def mock_remote() -> MagicMock:
    """Мок RemoteDB."""
    mock = MagicMock(spec=RemoteDB)
    mock.remote_url = "http://fake:4001"
    mock.local_path = Path("/tmp/fake.db")
    mock.execute.return_value = []
    mock.fetchall.return_value = []
    mock.fetchone.return_value = None
    mock.executescript = MagicMock()
    mock.commit = MagicMock()
    mock.close = MagicMock()
    return mock


# ─── Tests: local mode ───────────────────────────────────────────────────


class TestLocalMode:
    """Локальный контекст-менеджер работает как раньше."""

    def test_start_session(self, local_cm: ContextManager) -> None:
        snap = local_cm.start_session(project="test", topic="hello")
        assert snap.session_id is not None
        assert snap.status == SessionStatus.ACTIVE
        assert snap.project == "test"

    def test_add_message(self, local_cm: ContextManager) -> None:
        snap = local_cm.start_session(project="test", topic="msg test")
        result = local_cm.add_message(snap.session_id, "user", "Hello!")
        assert result is None  # нет авто-чекпоинта при малом количестве

    def test_list_sessions(self, local_cm: ContextManager) -> None:
        local_cm.start_session(project="p1", topic="A")
        local_cm.start_session(project="p2", topic="B")
        sessions = local_cm.list_sessions()
        assert len(sessions) >= 2

    def test_is_remote_false(self, local_cm: ContextManager) -> None:
        assert local_cm.is_remote is False


# ─── Tests: Cowork mode (mocked RemoteDB) ─────────────────────────────────


class TestCoworkMode:
    """ContextManager с RemoteDB — операции маршрутизируются в remote."""

    def test_is_remote_true(self, mock_remote: MagicMock, tmp_path: Path) -> None:
        cm = ContextManager(str(tmp_path / "ws"), remote_db=mock_remote)
        assert cm.is_remote is True

    def test_start_session_uses_remote(self, mock_remote: MagicMock, tmp_path: Path) -> None:
        mock_remote.execute.return_value = []  # SELECT returns nothing → new session
        cm = ContextManager(str(tmp_path / "ws"), remote_db=mock_remote)
        mock_remote.execute.reset_mock()

        cm.start_session(project="cowork", topic="shared")
        assert mock_remote.execute.call_count >= 1
        calls = " ".join(str(c) for c in mock_remote.execute.call_args_list)
        assert "INSERT" in calls or "sessions" in calls

    def test_add_message_uses_remote(self, mock_remote: MagicMock, tmp_path: Path) -> None:
        mock_remote.execute.return_value = []  # SELECT returns nothing
        cm = ContextManager(str(tmp_path / "ws"), remote_db=mock_remote)
        mock_remote.execute.reset_mock()

        snap = cm.start_session(project="test", topic="msg")
        mock_remote.execute.reset_mock()

        # Simulate session exists
        mock_remote.execute.side_effect = [
            [],  # INSERT message
            [],  # UPDATE sessions
            [_FakeRow(["message_count", "token_estimate"], [1, 10])],  # SELECT after update
        ]

        cm.add_message(snap.session_id, "user", "Hello cowork!")
        assert mock_remote.execute.call_count >= 2

    def test_executescript_called_on_init(self, mock_remote: MagicMock, tmp_path: Path) -> None:
        cm = ContextManager(str(tmp_path / "ws"), remote_db=mock_remote)
        # executescript вызывается при _init_db для создания схемы
        assert mock_remote.executescript.call_count >= 1


# ─── Tests: _CoworkConn / _CoworkCursor wrappers ─────────────────────────


class TestCoworkWrappers:
    """Внутренние классы-обёртки."""

    def test_cursor_fetchone_empty(self) -> None:
        cur = _CoworkCursor([])
        assert cur.fetchone() is None

    def test_cursor_fetchone_with_data(self) -> None:
        row = _FakeRow(["a", "b"], [1, 2])
        cur = _CoworkCursor([row])
        result = cur.fetchone()
        assert result is not None
        assert result["a"] == 1

    def test_cursor_fetchall(self) -> None:
        rows = [
            _FakeRow(["x"], [10]),
            _FakeRow(["x"], [20]),
        ]
        cur = _CoworkCursor(rows)
        assert len(cur.fetchall()) == 2

    def test_cursor_rowcount(self) -> None:
        assert _CoworkCursor([]).rowcount == 0
        assert _CoworkCursor([_FakeRow(["a"], [1])]).rowcount == 1

    def test_conn_execute_delegates(self, mock_remote: MagicMock) -> None:
        mock_remote.execute.return_value = [_FakeRow(["col"], [42])]
        conn = _CoworkConn(mock_remote)
        cur = conn.execute("SELECT 1")
        assert cur.fetchone()["col"] == 42
        mock_remote.execute.assert_called_once()

    def test_conn_executescript_delegates(self, mock_remote: MagicMock) -> None:
        conn = _CoworkConn(mock_remote)
        conn.executescript("CREATE TABLE t(x)")
        mock_remote.executescript.assert_called_once_with("CREATE TABLE t(x)")

    def test_conn_commit_delegates(self, mock_remote: MagicMock) -> None:
        conn = _CoworkConn(mock_remote)
        conn.commit()
        mock_remote.commit.assert_called_once()


# ─── Integration: real rqlite ─────────────────────────────────────────────


@pytest.mark.integration
class TestIntegrationRqlite:
    """Интеграционные тесты с реальным rqlite."""

    RQLITE_URL = "http://localhost:4001"

    @pytest.fixture
    def cowork_cm(self, tmp_path: Path) -> ContextManager:
        import urllib.request
        try:
            req = urllib.request.Request(f"{self.RQLITE_URL}/status?pretty=false")
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pytest.skip("rqlite not available")

        from core_02.remote_db import RemoteDB
        remote = RemoteDB(remote_url=self.RQLITE_URL)
        cm = ContextManager(str(tmp_path / "ws"), remote_db=remote)
        yield cm

    def test_start_and_list(self, cowork_cm: ContextManager) -> None:
        snap = cowork_cm.start_session(project="cowork", topic="integration test")
        sessions = cowork_cm.list_sessions()
        assert any(s["session_id"] == snap.session_id for s in sessions)

    def test_add_message_and_checkpoint(self, cowork_cm: ContextManager) -> None:
        snap = cowork_cm.start_session(project="test", topic="cp")
        # Add enough messages to trigger auto-checkpoint at interval=3
        cowork_cm.add_message(snap.session_id, "user", "msg1")
        cowork_cm.add_message(snap.session_id, "user", "msg2")
        result = cowork_cm.add_message(
            snap.session_id, "user", "msg3", auto_checkpoint_interval=3
        )
        assert result is not None
        assert result["checkpoint_type"] == CheckpointType.AUTO_INTERVAL.value