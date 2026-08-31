"""Tests for scripts_01/stream_bridge.py.

Covers:
- StreamBridge lifecycle (start_session, log, end_session)
- auto_bootstrap behavior
- get_context_resume
- get_status
- Integration with ContextManager and stream_session
"""

from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.stream_bridge import StreamBridge


# ================================================================
# StreamBridge Tests
# ================================================================


class TestStreamBridgeInit:
    """Tests for StreamBridge initialization."""

    def test_init_defaults(self, tmp_path, monkeypatch):
        """StreamBridge initializes with no session."""
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock(return_value={}))

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        assert bridge._session_dir is None
        assert bridge._sid is None
        assert bridge._topic == ""

    def test_init_runs_gc(self, tmp_path, monkeypatch):
        """StreamBridge runs GC on init if run_gc=True."""
        mock_prune = MagicMock(return_value={"streams": 0, "abandoned": 0})
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", mock_prune)
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=True)
        mock_prune.assert_called_once_with(dry_run=False)

    def test_gc_error_doesnt_crash(self, tmp_path, monkeypatch):
        """GC error on init doesn't crash the bridge."""
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock(side_effect=Exception("GC failed")))

        bridge = StreamBridge(auto_bootstrap=False, run_gc=True)
        assert bridge is not None  # should not crash


class TestStreamBridgeStartSession:
    """Tests for StreamBridge.start_session."""

    def test_start_creates_session(self, tmp_path, monkeypatch):
        """start_session creates a new stream session."""
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())
        monkeypatch.setattr("scripts_01.stream_bridge.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_bridge.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_bridge._start_session", MagicMock(return_value=tmp_path / "test_session"))

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.start_session(topic="Test Bridge Session")

        assert result == "unknown"  # no .session_id file → fallback
        assert bridge._topic == "Test Bridge Session"

    def test_start_session_sets_sid(self, tmp_path, monkeypatch):
        """start_session reads .session_id file and sets bridge._sid."""
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())

        session_dir = tmp_path / "test_session"
        session_dir.mkdir()
        (session_dir / ".session_id").write_text("test-bridge-sid-12345")

        monkeypatch.setattr("scripts_01.stream_bridge._start_session", MagicMock(return_value=session_dir))

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.start_session(topic="Test")
        assert result == "test-bri"  # first 8 chars
        assert bridge._sid == "test-bridge-sid-12345"


class TestStreamBridgeLogging:
    """Tests for StreamBridge logging methods."""

    def test_log_user(self, tmp_path, monkeypatch):
        """log_user calls _log_message with 'user' role."""
        mock_log = MagicMock(return_value=1)
        monkeypatch.setattr("scripts_01.stream_bridge._log_message", mock_log)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        # We need an active session_dir for log to work
        bridge._session_dir = tmp_path / "fake_session"

        result = bridge.log_user("Hello from user")
        mock_log.assert_called_once_with("user", "Hello from user")
        assert result == 1

    def test_log_assistant(self, tmp_path, monkeypatch):
        """log_assistant calls _log_message with 'assistant' role."""
        mock_log = MagicMock(return_value=1)
        monkeypatch.setattr("scripts_01.stream_bridge._log_message", mock_log)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.log_assistant("Response from assistant")
        mock_log.assert_called_once_with("assistant", "Response from assistant")
        assert result == 1

    def test_log_system(self, tmp_path, monkeypatch):
        """log_system calls _log_message with 'system' role."""
        mock_log = MagicMock(return_value=1)
        monkeypatch.setattr("scripts_01.stream_bridge._log_message", mock_log)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.log_system("System message")
        mock_log.assert_called_once_with("system", "System message")
        assert result == 1


class TestStreamBridgeCheckpoint:
    """Tests for StreamBridge.checkpoint."""

    def test_checkpoint_without_sid(self, tmp_path, monkeypatch):
        """checkpoint does nothing without an active session."""
        mock_save = MagicMock()
        monkeypatch.setattr("scripts_01.stream_bridge.ContextManager", MagicMock())

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge.checkpoint("Test checkpoint")  # should not raise

    def test_checkpoint_with_sid(self, tmp_path, monkeypatch):
        """checkpoint saves via ContextManager if sid is set."""
        mock_cm = MagicMock()
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._sid = "test-sid"
        bridge._context_manager = mock_cm

        bridge.checkpoint("Manual checkpoint")
        mock_cm.save_checkpoint.assert_called_once()

    @pytest.mark.parametrize("summary", ["Test", "Longer summary with details"])
    def test_checkpoint_with_summary(self, tmp_path, monkeypatch, summary):
        """checkpoint passes the summary correctly."""
        mock_cm = MagicMock()
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._sid = "test-sid"
        bridge._context_manager = mock_cm

        bridge.checkpoint(summary)
        call_kwargs = mock_cm.save_checkpoint.call_args[1]
        assert call_kwargs["summary"] == summary


class TestStreamBridgeEndSession:
    """Tests for StreamBridge.end_session."""

    def test_end_session(self, tmp_path, monkeypatch):
        """end_session completes the session and resets state."""
        mock_save = MagicMock()
        mock_complete = MagicMock()
        mock_cm = MagicMock()
        mock_cm.save_checkpoint = mock_save
        mock_cm.complete_session = mock_complete

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._sid = "test-sid-001"
        bridge._topic = "End Test"
        bridge._context_manager = mock_cm
        bridge._session_dir = tmp_path / "fake_session"

        result = bridge.end_session(do_conspect=False)
        mock_complete.assert_called_once_with("test-sid-001")
        assert bridge._sid is None
        assert bridge._session_dir is None
        assert bridge._topic == ""

    def test_end_session_resets_state(self, tmp_path, monkeypatch):
        """end_session clears all internal state."""
        mock_cm = MagicMock()
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._sid = "sid"
        bridge._topic = "topic"
        bridge._session_dir = tmp_path
        bridge._context_manager = mock_cm

        bridge.end_session(do_conspect=False)

        assert bridge._sid is None
        assert bridge._session_dir is None
        assert bridge._topic == ""

    def test_end_session_without_sid(self, tmp_path, monkeypatch):
        """end_session without sid doesn't crash."""
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.end_session(do_conspect=False)
        assert result == ""


class TestStreamBridgeGetContextResume:
    """Tests for StreamBridge.get_context_resume."""

    def test_get_context_resume_no_summaries(self, tmp_path, monkeypatch):
        """get_context_resume returns empty string when no summaries."""
        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.get_context_resume()
        assert result == ""

    def test_get_context_resume_with_summary(self, tmp_path, monkeypatch):
        """get_context_resume returns latest summary content."""
        # Create summaries dir with a test file
        summaries_dir = tmp_path / "context_12" / "summaries"
        summaries_dir.mkdir(parents=True)
        summary_file = summaries_dir / "test_summary.md"
        summary_file.write_text("# Test Summary\n\nSession completed successfully.")

        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.get_context_resume()
        assert "# Test Summary" in result
        assert "Session completed successfully" in result

    def test_get_context_resume_multiple_files(self, tmp_path, monkeypatch):
        """get_context_resume returns the most recent summary."""
        summaries_dir = tmp_path / "context_12" / "summaries"
        summaries_dir.mkdir(parents=True)

        # Create two summaries with different mtimes
        old_file = summaries_dir / "old.md"
        old_file.write_text("Old summary")
        import time
        time.sleep(0.1)  # ensure different mtime
        new_file = summaries_dir / "new.md"
        new_file.write_text("New summary")

        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.get_context_resume()
        assert result == "New summary"

    def test_get_context_resume_empty_file(self, tmp_path, monkeypatch):
        """get_context_resume handles empty summary files gracefully."""
        summaries_dir = tmp_path / "context_12" / "summaries"
        summaries_dir.mkdir(parents=True)
        (summaries_dir / "empty.md").write_text("")

        monkeypatch.setattr("scripts_01.stream_bridge.WORKSPACE", tmp_path)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        result = bridge.get_context_resume()
        assert result == ""


class TestStreamBridgeGetStatus:
    """Tests for StreamBridge.get_status."""

    def test_get_status_no_session(self, tmp_path, monkeypatch):
        """get_status returns 'no_session' when not active."""
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        status = bridge.get_status()
        assert status["status"] == "no_session"

    def test_get_status_with_session(self, tmp_path, monkeypatch):
        """get_status returns session info when active."""
        mock_status = {"token_estimate": 100, "threshold": 28000, "usage_percent": 0.36, "is_full": False}
        mock_cm = MagicMock()
        mock_cm.get_context_status.return_value = mock_status

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._sid = "test-sid"
        bridge._session_dir = tmp_path / "fake_session"
        bridge._context_manager = mock_cm

        status = bridge.get_status()
        assert "token_estimate" in status
        assert status["token_estimate"] == 100


class TestStreamBridgeProperties:
    """Tests for StreamBridge properties."""

    def test_context_manager_property(self, tmp_path, monkeypatch):
        """context_manager property returns the CM instance."""
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        assert bridge.context_manager is bridge._context_manager

    def test_session_id_property(self, tmp_path, monkeypatch):
        """session_id property returns current sid or None."""
        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        assert bridge.session_id is None

        bridge._sid = "test-sid"
        assert bridge.session_id == "test-sid"


class TestStreamBridgeAutoBootstrap:
    """Tests for auto_bootstrap behavior."""

    def test_auto_bootstrap_with_active_session(self, tmp_path, monkeypatch):
        """auto_bootstrap restores an active session if available."""
        mock_cm = MagicMock()
        mock_cm.list_sessions.return_value = [
            {"session_id": "test-active-sid-001", "topic": "Active Session"}
        ]
        mock_attach = MagicMock(return_value=tmp_path / "attached_session")

        monkeypatch.setattr("scripts_01.stream_bridge._attach_session", mock_attach)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())

        bridge = StreamBridge.__new__(StreamBridge)
        bridge._context_manager = mock_cm
        bridge._session_dir = None
        bridge._sid = None
        bridge._topic = ""

        bridge._auto_bootstrap()
        mock_attach.assert_called_once_with("test-active-sid-001")

    def test_auto_bootstrap_no_active_sessions(self, tmp_path, monkeypatch):
        """auto_bootstrap does nothing with no active sessions."""
        mock_cm = MagicMock()
        mock_cm.list_sessions.return_value = []

        bridge = StreamBridge.__new__(StreamBridge)
        bridge._context_manager = mock_cm
        bridge._session_dir = None
        bridge._sid = None
        bridge._topic = ""

        bridge._auto_bootstrap()
        assert bridge._session_dir is None
        assert bridge._sid is None

    def test_auto_bootstrap_attach_error_handling(self, tmp_path, monkeypatch):
        """auto_bootstrap handles attach errors gracefully."""
        mock_cm = MagicMock()
        mock_cm.list_sessions.return_value = [
            {"session_id": "test-sid", "topic": "Test"}
        ]
        mock_attach = MagicMock(side_effect=Exception("Attach failed"))

        monkeypatch.setattr("scripts_01.stream_bridge._attach_session", mock_attach)
        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())

        bridge = StreamBridge.__new__(StreamBridge)
        bridge._context_manager = mock_cm
        bridge._session_dir = None
        bridge._sid = None
        bridge._topic = ""

        bridge._auto_bootstrap()  # should not raise


class TestStreamBridgeFullLifecycle:
    """Integration-style tests for full StreamBridge lifecycle."""

    def test_full_lifecycle_with_mocks(self, tmp_path, monkeypatch):
        """Full lifecycle: init, start_session, log, checkpoint, end."""
        mock_cm = MagicMock()
        mock_log = MagicMock(return_value=1)
        mock_session_dir = tmp_path / "test_session"
        mock_session_dir.mkdir()
        (mock_session_dir / ".session_id").write_text("test-full-lifecycle")

        monkeypatch.setattr("scripts_01.stream_bridge._prune_all", MagicMock())
        monkeypatch.setattr("scripts_01.stream_bridge._start_session", MagicMock(return_value=mock_session_dir))
        monkeypatch.setattr("scripts_01.stream_bridge._log_message", mock_log)

        bridge = StreamBridge(auto_bootstrap=False, run_gc=False)
        bridge._context_manager = mock_cm

        # Start
        bridge.start_session(topic="Full Lifecycle Test")

        # Log
        bridge.log_user("User message")
        assert mock_log.called

        # Checkpoint
        bridge.checkpoint("Test checkpoint")

        # End
        result = bridge.end_session(do_conspect=False)
        mock_cm.complete_session.assert_called_once()

        # State cleaned
        assert bridge._sid is None
        assert bridge._session_dir is None
