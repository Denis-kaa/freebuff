"""Tests for scripts_01/agent_context_bridge.py."""
from __future__ import annotations

import os
import sys

import pytest

FREEBUFF_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FREEBUFF_ROOT)

from scripts_01.agent_context_bridge import AgentContextBridge
from scripts_01.context_manager import ContextManager, SessionStatus


def _make_bridge(tmp_path) -> AgentContextBridge:
    workspace = str(tmp_path / "freebuff")
    os.makedirs(os.path.join(workspace, "data_13"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "context_12", "summaries"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "context_12", "checkpoints"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "sessions_15"), exist_ok=True)

    bridge = AgentContextBridge(workspace)
    bridge._cm = ContextManager(workspace)
    return bridge


def test_ensure_session_creates_new_session(tmp_path) -> None:
    bridge = _make_bridge(tmp_path)
    sid = bridge.ensure_session(project="test-project", topic="test-topic")
    assert sid
    assert bridge.session_id == sid

    sessions = bridge._cm.list_sessions(SessionStatus.ACTIVE)
    assert any(s["session_id"***REMOVED*** == sid for s in sessions)


def test_log_user_and_assistant(tmp_path) -> None:
    bridge = _make_bridge(tmp_path)
    bridge.ensure_session()
    bridge.log_user("hello")
    bridge.log_assistant({"status": "ok", "tool": "test"***REMOVED***)

    assert bridge.session_id is not None
    messages = bridge._cm.get_messages(bridge.session_id)
    assert len(messages) == 2
    assert messages[0***REMOVED***["role"***REMOVED*** == "user"
    assert messages[0***REMOVED***["content"***REMOVED*** == "hello"
    assert messages[1***REMOVED***["role"***REMOVED*** == "assistant"
    assert "ok" in messages[1***REMOVED***["content"***REMOVED***


def test_log_error(tmp_path) -> None:
    bridge = _make_bridge(tmp_path)
    bridge.ensure_session()
    bridge.log_error(RuntimeError("boom"))

    assert bridge.session_id is not None
    messages = bridge._cm.get_messages(bridge.session_id)
    assert len(messages) == 1
    assert messages[0***REMOVED***["role"***REMOVED*** == "system"
    assert "boom" in messages[0***REMOVED***["content"***REMOVED***


def test_checkpoint_creates_checkpoint(tmp_path) -> None:
    bridge = _make_bridge(tmp_path)
    bridge.ensure_session()
    bridge.checkpoint("manual checkpoint")

    assert bridge.session_id is not None
    checkpoints = bridge._cm.get_checkpoints(bridge.session_id)
    assert len(checkpoints) == 1
    assert checkpoints[0***REMOVED***["checkpoint_type"***REMOVED*** == "manual"
    assert checkpoints[0***REMOVED***["summary"***REMOVED*** == "manual checkpoint"


def test_auto_conspect_creates_summary(tmp_path) -> None:
    bridge = _make_bridge(tmp_path)
    bridge.ensure_session(project="termux-ai-agent", topic="test")
    bridge.log_user("hello")
    bridge.log_assistant({"status": "ok"***REMOVED***)

    path = bridge.auto_conspect()
    assert path and os.path.exists(path)
    assert path.endswith(".md")

    # Session should be completed after conspect
    assert bridge.session_id is not None
    session = bridge._cm.get_session(bridge.session_id)
    assert session is not None
    assert session.status == SessionStatus.COMPLETED
