"""Tests for scripts_01/stream_session.py.

Covers:
- BackgroundWriter (async I/O via Queue)
- start_session / resume_session / attach_session
- log_message (async + sync via ContextManager)
- Counter cache persistence
- Adaptive checkpoint interval
- prune_streams / prune_all (GC)
- print_status / print_tail / list_sessions
"""

from __future__ import annotations

import json
import os
import sys
***REMOVED***
from queue import Queue, Empty
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01.stream_session import (
    BackgroundWriter,
    start_session,
    resume_session,
    attach_session,
    log_message,
    _get_counter,
    _inc_counter,
    _get_adaptive_interval,
    _safe_topic,
    _current_session_path,
    _set_current_session,
    prune_streams,
    prune_all,
    print_status,
    print_tail,
    list_sessions,
    STREAMS_DIR,
    CURRENT_FILE,
    AUTO_CHECKPOINT_INTERVAL_START,
    AUTO_CHECKPOINT_INTERVAL_MAX,
    AUTO_CHECKPOINT_INTERVAL_STEP,
    MAX_STREAM_DIRS,
)


# ================================================================
# BackgroundWriter Tests
# ================================================================


class TestBackgroundWriter:
    """Tests for BackgroundWriter — async I/O via Queue."""

    def test_init(self):
        """BackgroundWriter starts with empty queue and no thread."""
        bw = BackgroundWriter()
        assert bw._queue.qsize() == 0
        assert bw._started is False
        assert bw._thread is None

    def test_start_creates_thread(self):
        """start() creates a daemon thread."""
        bw = BackgroundWriter()
        bw.start()
        assert bw._started is True
        assert bw._thread is not None
        assert bw._thread.daemon is True
        assert bw._thread.name == "stream-bg-writer"

    def test_start_idempotent(self):
        """start() called twice doesn't create two threads."""
        bw = BackgroundWriter()
        bw.start()
        thread1 = bw._thread
        bw.start()
        assert bw._thread is thread1  # same thread

    def test_enqueue_starts_writer(self):
        """enqueue() auto-starts the writer if not started."""
        bw = BackgroundWriter()
        assert bw._started is False
        bw.enqueue("log", session_dir="/tmp", role="user", content="hello")
        assert bw._started is True

    def test_enqueue_adds_to_queue(self):
        """enqueue() adds an item to the queue."""
        bw = BackgroundWriter()
        bw.enqueue("log", session_dir="/tmp", role="user", content="hello")
        assert bw._queue.qsize() == 1

    def test_flush_empty_queue(self):
        """flush() on empty queue returns 0."""
        bw = BackgroundWriter()
        assert bw.flush(timeout=0.1) == 0

    def test_handle_log_writes_files(self, tmp_path):
        """_handle_log writes conversation.log and raw.jsonl."""
        session_dir = tmp_path / "test_session"
        session_dir.mkdir()

        BackgroundWriter._handle_log(
            session_dir=session_dir,
            role="user",
            content="Hello, world!",
            count=1,
            ts="2026-07-29 12:00:00",
        )

        # Check conversation.log
        log_file = session_dir / "conversation.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "[user***REMOVED***" in content
        assert "Hello, world!" in content
        assert "msg#1" in content

        # Check raw.jsonl
        jsonl_file = session_dir / "raw.jsonl"
        assert jsonl_file.exists()
        entry = json.loads(jsonl_file.read_text().strip())
        assert entry["role"***REMOVED*** == "user"
        assert entry["msg_num"***REMOVED*** == 1
        assert entry["content"***REMOVED*** == "Hello, world!"

    def test_handle_log_without_session_dir(self):
        """_handle_log with no session_dir doesn't crash."""
        BackgroundWriter._handle_log()  # should not raise

    def test_handle_checkpoint_writes_summary(self, tmp_path):
        """_handle_checkpoint writes to summary.md."""
        session_dir = tmp_path / "test_session"
        session_dir.mkdir()

        BackgroundWriter._handle_checkpoint(
            session_dir=session_dir,
            summary="Test checkpoint summary",
            count=5,
            ts="2026-07-29 12:00:00",
        )

        summary_file = session_dir / "summary.md"
        assert summary_file.exists()
        content = summary_file.read_text()
        assert "msg#5" in content
        assert "Test checkpoint summary" in content

    def test_worker_processes_queue(self, tmp_path):
        """Worker thread processes queued items."""
        bw = BackgroundWriter()
        session_dir = tmp_path / "test_session"
        session_dir.mkdir()

        bw.start()
        bw.enqueue("log", session_dir=session_dir, role="user", content="test")
        bw.flush(timeout=2.0)

        assert (session_dir / "conversation.log").exists()
        assert (session_dir / "raw.jsonl").exists()

    def test_unknown_operation_doesnt_crash(self):
        """Unknown operation in worker doesn't crash the thread."""
        bw = BackgroundWriter()
        bw.start()
        bw.enqueue("unknown_op", data="test")
        bw.flush(timeout=1.0)
        assert bw._thread.is_alive()  # thread still running


# ================================================================
# _safe_topic Tests
# ================================================================


class TestSafeTopic:
    def test_normal_topic(self):
        assert _safe_topic("Hello World") == "Hello_World"

    def test_special_chars(self):
        result = _safe_topic("test/topic:name?")
        assert "/" not in result
        assert ":" not in result
        assert "?" not in result

    def test_long_topic(self):
        long_topic = "a" * 100
        assert len(_safe_topic(long_topic)) <= 40

    def test_empty_topic(self):
        assert _safe_topic("") == ""


# ================================================================
# Adaptive Checkpoint Interval Tests
# ================================================================


class TestAdaptiveInterval:
    def test_under_20(self):
        assert _get_adaptive_interval(5) == AUTO_CHECKPOINT_INTERVAL_START
        assert _get_adaptive_interval(19) == AUTO_CHECKPOINT_INTERVAL_START

    def test_under_100(self):
        assert _get_adaptive_interval(20) == 30
        assert _get_adaptive_interval(50) == 30
        assert _get_adaptive_interval(99) == 30

    def test_under_500(self):
        assert _get_adaptive_interval(100) == 40
        assert _get_adaptive_interval(300) == 40
        assert _get_adaptive_interval(499) == 40

    def test_over_500(self):
        assert _get_adaptive_interval(500) == AUTO_CHECKPOINT_INTERVAL_MAX
        assert _get_adaptive_interval(1000) == AUTO_CHECKPOINT_INTERVAL_MAX


# ================================================================
# Counter Cache Tests
# ================================================================


class TestCounterCache:
    def test_get_counter_initial(self, tmp_path):
        """_get_counter returns 0 for new session."""
        session_dir = tmp_path / "new_session"
        session_dir.mkdir()
        assert _get_counter(session_dir) == 0

    def test_inc_counter(self, tmp_path):
        """_inc_counter increments and persists to .counter file."""
        session_dir = tmp_path / "test_session"
        session_dir.mkdir()
        assert _inc_counter(session_dir) == 1
        assert _inc_counter(session_dir) == 2
        assert _inc_counter(session_dir) == 3
        # Check file persistence
        counter_file = session_dir / ".counter"
        assert counter_file.exists()
        assert counter_file.read_text() == "3"

    def test_get_counter_persisted(self, tmp_path):
        """_get_counter reads from persisted .counter file."""
        from scripts_01.stream_session import _counter_cache
        _counter_cache.clear()  # clean slate

        session_dir = tmp_path / "counter_persist_test"
        session_dir.mkdir()
        _inc_counter(session_dir)
        _inc_counter(session_dir)
        # Clear cache to force re-read from file
        _counter_cache.pop(session_dir.name, None)
        assert _get_counter(session_dir) == 2


# ================================================================
# start_session Tests
# ================================================================


class TestStartSession:
    def test_start_creates_dirs_and_files(self, tmp_path, monkeypatch):
        """start_session creates directory structure and log file."""
        mock_current = tmp_path / ".current"
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", mock_current)
        monkeypatch.setattr("scripts_01.stream_session.cm", None)
        from scripts_01.stream_session import _counter_cache
        _counter_cache.clear()

        session_dir = start_session("Test Topic")
        assert session_dir.exists()
        assert (session_dir / "conversation.log").exists()
        assert mock_current.exists()
        content = mock_current.read_text()
        assert "Test_Topic" in content

    def test_start_creates_session_id(self, tmp_path, monkeypatch):
        """start_session writes .session_id file."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        session_dir = start_session("Test Topic")
        sid_file = session_dir / ".session_id"
        assert sid_file.exists()
        assert len(sid_file.read_text().strip()) > 0

    def test_start_topic_sanitized(self, tmp_path, monkeypatch):
        """start_session sanitizes topic for directory name."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        session_dir = start_session("Special/Chars:Test?")
        assert "/" not in session_dir.name
        assert "?" not in session_dir.name
        assert "Test" in session_dir.name

    def test_start_with_context_manager(self, tmp_path, monkeypatch, context_manager):
        """start_session integrates with ContextManager if available."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)

        session_dir = start_session("CM Test", session_id="test-cm-session-001")
        assert session_dir.exists()

        # Check ContextManager session
        snap = context_manager.get_session("test-cm-session-001")
        assert snap is not None
        assert snap.topic == "CM Test"


# ================================================================
# Current Session Tests
# ================================================================


class TestCurrentSession:
    def test_set_and_get_current(self, tmp_path, monkeypatch):
        """_set_current_session and _current_session_path work together."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")

        session_dir = tmp_path / "my_session"
        session_dir.mkdir()

        _set_current_session("my_session")
        result = _current_session_path()
        assert result is not None
        assert result.name == "my_session"

    def test_current_session_none(self, tmp_path, monkeypatch):
        """_current_session_path returns None when no active session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")

        assert _current_session_path() is None


# ================================================================
# resume_session Tests
# ================================================================


class TestResumeSession:
    def test_resume_by_session_id(self, tmp_path, monkeypatch):
        """resume_session finds by .session_id prefix."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        # Create session with known ID
        session_dir = tmp_path / "test_topic_20260729_120000"
        session_dir.mkdir()
        (session_dir / ".session_id").write_text("abc12345")

        result = resume_session("abc")
        assert result is not None
        assert result.name == "test_topic_20260729_120000"

    def test_resume_nonexistent(self, tmp_path, monkeypatch):
        """resume_session returns None for unknown session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        result = resume_session("nonexistent")
        assert result is None

    def test_resume_unknown_returns_none(self, tmp_path, monkeypatch):
        """resume_session with no match returns None."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        result = resume_session("unknown")
        assert result is None


# ================================================================
# attach_session Tests
# ================================================================


class TestAttachSession:
    def test_attach_creates_stream_dir(self, tmp_path, monkeypatch, context_manager):
        """attach_session creates a stream directory linked to a CM session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)

        # Create a session in ContextManager first
        snap = context_manager.start_session(project="test", topic="Attach Test")

        result = attach_session(snap.session_id[:8***REMOVED***)
        assert result is not None
        assert result.exists()
        # Check .session_id file
        sid_file = result / ".session_id"
        assert sid_file.exists()
        assert sid_file.read_text() == snap.session_id

    def test_attach_nonexistent(self, tmp_path, monkeypatch, context_manager):
        """attach_session returns None for nonexistent session."""
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)

        result = attach_session("deadbeef")
        assert result is None


# ================================================================
# log_message Tests
# ================================================================


class TestLogMessage:
    def test_log_without_active_session(self, tmp_path, monkeypatch):
        """log_message returns None when no active session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        result = log_message("user", "test")
        assert result is None

    def test_log_increments_counter(self, tmp_path, monkeypatch):
        """log_message increments the message counter."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)
        monkeypatch.setattr("scripts_01.stream_session.BG_WRITER", MagicMock())

        # Start session
        session_dir = start_session("Log Test")
        # Manually set current
        _set_current_session(session_dir.name)

        count1 = log_message("user", "first message")
        count2 = log_message("assistant", "second message")

        assert count1 == 1
        assert count2 == 2

    def test_log_writes_to_sqlite(self, tmp_path, monkeypatch, context_manager):
        """log_message writes to ContextManager if available."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)
        monkeypatch.setattr("scripts_01.stream_session.BG_WRITER", MagicMock())

        session_dir = start_session("SQLite Test", session_id="test-sqlite-log-001")
        _set_current_session(session_dir.name)

        log_message("user", "Hello from test")
        log_message("assistant", "Hi there!")

        # Verify messages in ContextManager
        sid_file = session_dir / ".session_id"
        sid = sid_file.read_text().strip()
        messages = context_manager.get_messages(sid)
        assert len(messages) == 2
        assert messages[0***REMOVED***["role"***REMOVED*** == "user"
        assert messages[0***REMOVED***["content"***REMOVED*** == "Hello from test"
        assert messages[1***REMOVED***["role"***REMOVED*** == "assistant"
        assert messages[1***REMOVED***["content"***REMOVED*** == "Hi there!"


# ================================================================
# prune_streams / prune_all Tests
# ================================================================


class TestPruneStreams:
    def test_prune_old_dirs(self, tmp_path, monkeypatch):
        """prune_streams removes old directories beyond max_keep."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.MAX_STREAM_DIRS", 3)

        # Create 5 session directories
        for i in range(5):
            d = tmp_path / f"session_{i***REMOVED***"
            d.mkdir()
            (d / "conversation.log").write_text(f"log {i***REMOVED***")
            (d / ".counter").write_text(str(i))
            # Set mtime to make them ordered
            import time
            atime = time.time() - (5 - i) * 100
            os.utime(str(d), (atime, atime))

        deleted = prune_streams(keep=3, dry_run=False)
        assert deleted == 2  # 5 - 3 = 2 deleted

        remaining = list(tmp_path.iterdir())
        assert len(remaining) == 3  # only 3 left

    def test_prune_dry_run(self, tmp_path, monkeypatch):
        """prune_streams with dry_run doesn't delete anything."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)

        for i in range(5):
            d = tmp_path / f"session_{i***REMOVED***"
            d.mkdir()

        deleted = prune_streams(keep=3, dry_run=True)
        assert deleted == 0  # dry run doesn't delete

        remaining = list(tmp_path.iterdir())
        assert len(remaining) == 5  # all still there

    def test_prune_keeps_active(self, tmp_path, monkeypatch):
        """prune_streams doesn't delete the active session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.MAX_STREAM_DIRS", 1)

        # Create 3 sessions, mark one as current
        active_dir = tmp_path / "active_session"
        active_dir.mkdir()
        _set_current_session("active_session")

        for i in range(2):
            d = tmp_path / f"old_session_{i***REMOVED***"
            d.mkdir()
            import time
            os.utime(str(d), (time.time() - 1000, time.time() - 1000))

        deleted = prune_streams(keep=1, dry_run=False)
        # active session should NOT be deleted
        assert active_dir.exists()

    def test_prune_all_gc(self, tmp_path, monkeypatch, context_manager):
        """prune_all runs full GC cycle."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)
        monkeypatch.setattr("scripts_01.stream_session.MAX_STREAM_DIRS", 3)

        # Create some sessions in CM
        context_manager.start_session(project="test", topic="Session 1")
        context_manager.start_session(project="test", topic="Session 2")

        # Create stream dirs
        for i in range(5):
            d = tmp_path / f"stream_{i***REMOVED***"
            d.mkdir()
            (d / ".counter").write_text(str(i))
            (d / "conversation.log").write_text(f"log {i***REMOVED***")

        result = prune_all(dry_run=False)
        assert isinstance(result, dict)
        assert "streams" in result
        assert "abandoned" in result
        assert result["streams"***REMOVED*** >= 2  # at least 2 streams pruned


# ================================================================
# print_status / print_tail / list_sessions Tests
# ================================================================


class TestPrintFunctions:
    def test_print_status_no_session(self, tmp_path, monkeypatch, capsys):
        """print_status shows 'no session' message."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        print_status()
        captured = capsys.readouterr()
        assert "Нет активной сессии" in captured.out

    def test_print_status_active(self, tmp_path, monkeypatch, capsys):
        """print_status shows active session info."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        start_session("Status Test")
        print_status()
        captured = capsys.readouterr()
        assert "Status Test" in captured.out or "Активная сессия" in captured.out

    def test_print_tail_no_session(self, tmp_path, monkeypatch, capsys):
        """print_tail shows message when no active session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")

        print_tail(5)
        captured = capsys.readouterr()
        assert "Нет активной сессии" in captured.out

    def test_print_tail_empty_log(self, tmp_path, monkeypatch, capsys):
        """print_tail shows 'empty' message when log is empty."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        session_dir = start_session("Tail Test")
        # Remove the log file to simulate empty
        (session_dir / "conversation.log").unlink()

        print_tail(5)
        captured = capsys.readouterr()
        assert "Лог пуст" in captured.out

    def test_list_sessions_empty(self, tmp_path, monkeypatch, capsys):
        """list_sessions shows 'empty' when no sessions."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)

        list_sessions()
        captured = capsys.readouterr()
        assert "Нет стрим-сессий" in captured.out

    def test_list_sessions_with_sessions(self, tmp_path, monkeypatch, capsys):
        """list_sessions shows session list."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.cm", None)

        # Create sessions
        d1 = tmp_path / "session_a_20260729_120000"
        d1.mkdir()
        (d1 / ".session_id").write_text("aaaa1234")
        (d1 / ".counter").write_text("5")
        (d1 / "conversation.log").write_text("a" * 100)

        d2 = tmp_path / "session_b_20260729_130000"
        d2.mkdir()
        (d2 / ".session_id").write_text("bbbb5678")
        (d2 / ".counter").write_text("3")
        (d2 / "conversation.log").write_text("b" * 100)

        list_sessions()
        captured = capsys.readouterr()
        assert "session_a" in captured.out or "Всего стрим-сессий" in captured.out


# ================================================================
# Integration Tests
# ================================================================


class TestIntegration:
    def test_full_session_lifecycle(self, tmp_path, monkeypatch, context_manager):
        """Full lifecycle: start → log → resume → log → list."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", context_manager)
        monkeypatch.setattr("scripts_01.stream_session.BG_WRITER", MagicMock())

        # Start
        session_dir = start_session("Integration Test", session_id="integration-test-001")
        assert session_dir.exists()

        sid_file = session_dir / ".session_id"
        sid = sid_file.read_text().strip()

        # Log messages
        _set_current_session(session_dir.name)
        log_message("user", "Message 1")
        log_message("assistant", "Response 1")
        log_message("user", "Message 2")

        # Verify counter
        assert _get_counter(session_dir) == 3

        # Verify in ContextManager
        messages = context_manager.get_messages(sid)
        assert len(messages) == 3

        # Resume by prefix
        resumed = resume_session(sid[:8***REMOVED***)
        assert resumed is not None
        assert resumed.name == session_dir.name

    def test_prune_with_active_session(self, tmp_path, monkeypatch):
        """Prune doesn't remove active session."""
        monkeypatch.setattr("scripts_01.stream_session.STREAMS_DIR", tmp_path)
        monkeypatch.setattr("scripts_01.stream_session.CURRENT_FILE", tmp_path / ".current")
        monkeypatch.setattr("scripts_01.stream_session.cm", None)
        monkeypatch.setattr("scripts_01.stream_session.MAX_STREAM_DIRS", 2)

        # Create active session
        active_dir = start_session("Active")
        active_name = active_dir.name

        # Create more sessions
        for i in range(3):
            d = tmp_path / f"old_{i***REMOVED***"
            d.mkdir()
            (d / ".counter").write_text("1")
            (d / "conversation.log").write_text(f"log {i***REMOVED***")
            import time
            os.utime(str(d), (time.time() - 1000, time.time() - 1000))

        prune_streams(keep=2, dry_run=False)

        # Active session must survive
        assert (tmp_path / active_name).exists()
