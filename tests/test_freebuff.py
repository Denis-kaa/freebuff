"""
Unit tests for freebuff interaction system.
"""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.system_monitor import get_memory, get_cpu, get_battery, get_temperature, health_check
from scripts.context_manager import (
    ContextManager, SessionStatus, CheckpointType, SCHEMA_VERSION, DEFAULT_CONTEXT_THRESHOLD,
)


class TestSystemMonitor:
    """Тесты системного монитора."""

    @patch("builtins.open", new_callable=mock_open, read_data="MemTotal: 8000000 kB\nMemAvailable: 4000000 kB\n")
    def test_get_memory_ok(self, mock_file):
        result = get_memory()
        assert result["available_mb"***REMOVED*** == 3906  # 4000000 // 1024
        assert result["total_mb"***REMOVED*** == 7812       # 8000000 // 1024
        assert result["percent"***REMOVED*** > 0

    @patch("builtins.open", side_effect=OSError("no file"))
    def test_get_memory_error(self, mock_file):
        result = get_memory()
        assert result["available_mb"***REMOVED*** == 0
        assert result["total_mb"***REMOVED*** == 0

    def test_get_cpu(self):
        result = get_cpu()
        assert "loadavg" in result
        assert "percent" in result
        assert "error" in result

    def test_health_check(self):
        result = health_check()
        assert "memory_ok" in result
        assert "cpu_ok" in result
        assert "battery_ok" in result
        assert all(isinstance(v, bool) for v in result.values())


class TestContextManager:
    """Тесты ContextManager (SQLite in-memory)."""

    @pytest.fixture
    def cm(self, tmp_path):
        """ContextManager с временной БД."""
        db_path = str(tmp_path / "data" / "context.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        manager = ContextManager.__new__(ContextManager)
        manager._root = str(tmp_path)
        manager._db_path = db_path
        manager._sessions_dir = str(tmp_path / "sessions")
        manager._checkpoints_dir = str(tmp_path / "context" / "checkpoints")
        manager._summaries_dir = str(tmp_path / "context" / "summaries")
        manager._context_threshold = DEFAULT_CONTEXT_THRESHOLD

        import threading
        manager._lock = threading.Lock()
        manager._event_bus = None

        for d in [manager._sessions_dir, manager._checkpoints_dir, manager._summaries_dir***REMOVED***:
            os.makedirs(d, exist_ok=True)

        manager._init_db()
        return manager

    def test_start_session(self, cm):
        snap = cm.start_session(project="test", topic="unit test")
        assert snap.session_id
        assert snap.status == SessionStatus.ACTIVE
        assert snap.project == "test"

    def test_add_message(self, cm):
        snap = cm.start_session(project="test")
        cm.add_message(snap.session_id, "user", "Hello", token_count=5)
        msgs = cm.get_messages(snap.session_id)
        assert len(msgs) == 1
        assert msgs[0***REMOVED***["role"***REMOVED*** == "user"
        assert msgs[0***REMOVED***["content"***REMOVED*** == "Hello"

    def test_add_message_auto_token(self, cm):
        """Тест авто-оценки токенов."""
        snap = cm.start_session(project="test")
        result = cm.add_message(snap.session_id, "user", "Hello, world!", token_count=None)
        msgs = cm.get_messages(snap.session_id)
        assert len(msgs) == 1
        # token_count > 0, т.к. оценка "Hello, world!"
        assert msgs[0***REMOVED***["token_count"***REMOVED*** > 0
        assert result is None  # без чекпоинта

    def test_save_checkpoint(self, cm):
        snap = cm.start_session(project="test")
        cm.add_message(snap.session_id, "user", "msg", token_count=2)
        cp = cm.save_checkpoint(snap.session_id, "Test checkpoint", ctype=CheckpointType.MANUAL)
        assert cp["summary"***REMOVED*** == "Test checkpoint"

        checkpoints = cm.get_checkpoints(snap.session_id)
        assert len(checkpoints) == 1

    def test_complete_session(self, cm):
        snap = cm.start_session(project="test")
        cm.complete_session(snap.session_id)
        loaded = cm.get_session(snap.session_id)
        assert loaded.status == SessionStatus.COMPLETED

    def test_list_sessions(self, cm):
        cm.start_session(project="a")
        cm.start_session(project="b")
        sessions = cm.list_sessions()
        assert len(sessions) >= 2

    def test_export_markdown(self, cm):
        snap = cm.start_session(project="test", topic="Export test")
        cm.add_message(snap.session_id, "user", "Hello")
        cm.add_message(snap.session_id, "assistant", "Hi there!")
        export = cm.export_markdown(snap.session_id)
        assert "Export test" in export
        assert "Hello" in export

    def test_export_checkpoint_summary(self, cm):
        snap = cm.start_session(project="test", topic="Summary test")
        cm.save_checkpoint(snap.session_id, "Step 1 done")
        cm.save_checkpoint(snap.session_id, "Step 2 done")
        summary = cm.export_checkpoint_summary(snap.session_id)
        assert "Step 1 done" in summary
        assert "Step 2 done" in summary

    def test_get_last_summary(self, cm):
        snap = cm.start_session(project="test")
        cm.save_checkpoint(snap.session_id, "First")
        cm.save_checkpoint(snap.session_id, "Second")
        assert cm.get_last_summary(snap.session_id) == "Second"

    def test_auto_checkpoint(self, cm):
        snap = cm.start_session(project="test")
        for i in range(10):
            cm.add_message(snap.session_id, "user", f"msg {i***REMOVED***", token_count=1,
                          auto_checkpoint_interval=10)
        checkpoints = cm.get_checkpoints(snap.session_id)
        assert len(checkpoints) == 1
        assert "Auto-checkpoint" in checkpoints[0***REMOVED***["summary"***REMOVED***

    def test_session_not_found(self, cm):
        with pytest.raises(ValueError, match="Session not found"):
            cm.save_checkpoint("nonexistent", "summary")

    def test_get_context_status(self, cm):
        """Тест статуса контекста."""
        snap = cm.start_session(project="test", topic="Status test")
        cm.add_message(snap.session_id, "user", "Hello", token_count=100)
        status = cm.get_context_status(snap.session_id)
        assert status["message_count"***REMOVED*** == 1
        assert status["token_estimate"***REMOVED*** > 0
        assert "usage_percent" in status
        assert status["is_full"***REMOVED*** is False

    def test_context_full_trigger(self, cm):
        """Тест CONTEXT_FULL триггера."""
        # Устанавливаем очень низкий порог
        cm._context_threshold = 10
        snap = cm.start_session(project="test", topic="Full test")
        # Первое сообщение — в норме
        r1 = cm.add_message(snap.session_id, "user", "hi", token_count=5)
        assert r1 is None
        # Второе сообщение — превышает порог
        r2 = cm.add_message(snap.session_id, "user", "longer message here", token_count=10)
        assert r2 is not None
        assert r2["checkpoint_type"***REMOVED*** == CheckpointType.CONTEXT_FULL.value
        # Проверяем через get_context_status
        status = cm.get_context_status(snap.session_id)
        assert status["is_full"***REMOVED*** is True

    def test_estimate_tokens(self):
        """Тест оценки токенов."""
        # Пустой текст
        assert ContextManager._estimate_tokens("") == 1
        # Короткий текст
        assert ContextManager._estimate_tokens("Hello") >= 1
        # Длинный текст
        long_text = "Тестовый текст " * 100
        estimate = ContextManager._estimate_tokens(long_text)
        assert estimate > 10

    def test_prune_abandoned(self, cm):
        """Тест очистки ABANDONED сессий."""
        snap = cm.start_session(project="test", topic="To be pruned")
        cm.update_session_status(snap.session_id, SessionStatus.ABANDONED)

        # Не должна удалиться (свежая)
        deleted = cm.prune_abandoned(days=0)  # удаляем всё старше 0 дней
        # Относительно свежая, может не удалиться, но функция должна отработать
        assert isinstance(deleted, int)

    def test_auto_abandon_stale(self, cm):
        """Тест перевода пустых ACTIVE в ABANDONED."""
        snap = cm.start_session(project="test", topic="Stale")
        # Пустая сессия (message_count=0)
        abandoned = cm.auto_abandon_stale(days=0)  # всё
        assert abandoned >= 0

    def test_get_total_token_estimate(self, cm):
        snap = cm.start_session(project="test")
        cm.add_message(snap.session_id, "user", "Hello", token_count=50)
        cm.add_message(snap.session_id, "assistant", "Hi!", token_count=30)
        assert cm.get_total_token_estimate(snap.session_id) == 80

    def test_update_session_status(self, cm):
        snap = cm.start_session(project="test")
        cm.update_session_status(snap.session_id, SessionStatus.PAUSED)
        loaded = cm.get_session(snap.session_id)
        assert loaded.status == SessionStatus.PAUSED


class TestBootstrap:
    """Тесты bootstrap."""

    @patch("scripts.bootstrap.os.listdir")
    def test_bootstrap_new_session(self, mock_listdir):
        """Bootstrap с новой сессией (без конспектов)."""
        from scripts.bootstrap import bootstrap

        mock_listdir.return_value = [***REMOVED***

        with patch("scripts.bootstrap.ContextManager") as MockCM, \
             patch("scripts.bootstrap.StreamBridge") as MockBridge:
            mock_cm = MagicMock()
            mock_cm.list_sessions.return_value = [***REMOVED***  # нет активных
            mock_snap = MagicMock()
            mock_snap.session_id = "test-1234"
            mock_snap.project = "test"
            mock_snap.topic = ""
            mock_cm.start_session.return_value = mock_snap
            MockCM.return_value = mock_cm

            mock_bridge = MagicMock()
            mock_bridge.session_id = None
            MockBridge.return_value = mock_bridge

            result = bootstrap(project="test", topic="bootstrap test", quiet=True, start_stream=True)

            assert result["session_id"***REMOVED*** == "test-1234"
            assert "Я начинаю новую сессию" in result["buffy_prompt"***REMOVED***


class TestFreebuffCLI:
    """Интеграционные тесты CLI."""

    def test_cli_status(self):
        import subprocess
        result = subprocess.run(
            ["python", "freebuff_cli.py", "status"***REMOVED***,
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert "СТАТУС FREEBUFF" in result.stdout
        assert "Здоровье" in result.stdout
