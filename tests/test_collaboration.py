#!/usr/bin/env python3
"""
Tests for Collaboration Engine (scripts/collaboration.py).

Tests:
  - ParticipantRole / SessionStatus validation
  - Sessions: create, get, list, close
  - Participants: join, leave, role update, presence sync
  - Messages: send, history, system messages, pagination
  - EventBus integration
  - Status / diagnostics
  - CLI commands
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collaboration import (
    CollaborationEngine,
    CollaborationSession,
    CollabMessage,
    Participant,
    ParticipantRole,
    SessionStatus,
)


# ═══════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════


class _StubEventBus:
    """Минимальный EventBus: публикация в память."""

    def __init__(self):
        self.events = [***REMOVED***

    def publish(self, event):
        self.events.append(event)

    def get_events(self, limit=100):
        return self.events[-limit:***REMOVED***


class _StubPresence:
    """Минимальный PresenceEngine: offline для заданных агентов."""

    def __init__(self, offline: list[str***REMOVED*** | None = None):
        self.offline = set(offline or [***REMOVED***)

    def get(self, name):
        class _P:
            def __init__(self, status):
                self.status = status

        return _P("offline" if name in self.offline else "online")


@pytest.fixture
def engine(tmp_path) -> CollaborationEngine:
    return CollaborationEngine(db_path=tmp_path / "collab_test.db")


@pytest.fixture
def session(engine: CollaborationEngine) -> CollaborationSession:
    return engine.create_session(
        topic="Code Review",
        owner="buffy",
        participants=["alice", "bob"***REMOVED***,
    )


# ═══════════════════════════════════════════════════════════════
# Roles / Status validation
# ═══════════════════════════════════════════════════════════════


class TestRolesAndStatus:
    def test_participant_role_constants(self):
        assert ParticipantRole.OWNER == "owner"
        assert ParticipantRole.EDITOR == "editor"
        assert ParticipantRole.VIEWER == "viewer"

    def test_participant_role_is_valid(self):
        assert ParticipantRole.is_valid("owner")
        assert ParticipantRole.is_valid("editor")
        assert ParticipantRole.is_valid("viewer")
        assert not ParticipantRole.is_valid("admin")

    def test_session_status_constants(self):
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.CLOSED == "closed"
        assert SessionStatus.ARCHIVED == "archived"

    def test_session_status_is_valid(self):
        assert SessionStatus.is_valid("active")
        assert SessionStatus.is_valid("closed")
        assert not SessionStatus.is_valid("pending")


# ═══════════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════════


class TestSessions:
    def test_create_session(self, engine: CollaborationEngine):
        s = engine.create_session(topic="Planning", owner="buffy", participants=["alice"***REMOVED***)
        assert s.session_id.startswith("collab-")
        assert s.topic == "Planning"
        assert s.status == SessionStatus.ACTIVE
        assert s.owner == "buffy"
        assert s.message_count == 0

    def test_create_session_owner_is_participant(self, engine: CollaborationEngine):
        s = engine.create_session(topic="T", owner="buffy")
        assert s.has_participant("buffy")
        owner_p = s.get_participant("buffy")
        assert owner_p is not None
        assert owner_p.role == ParticipantRole.OWNER

    def test_create_session_with_participants(self, engine: CollaborationEngine):
        s = engine.create_session(topic="T", owner="buffy", participants=["alice", "bob"***REMOVED***)
        assert set(s.participant_names()) == {"buffy", "alice", "bob"***REMOVED***
        alice = s.get_participant("alice")
        assert alice is not None
        assert alice.role == ParticipantRole.EDITOR

    def test_create_session_owner_as_list(self, engine: CollaborationEngine):
        # Контракт: owner вторым позиционным аргументом может быть список участников.
        # Примечание: движок всегда вставляет участника-владельца (здесь name=""),
        # поэтому проверяем только членство alice/bob.
        s = engine.create_session("T", ["alice", "bob"***REMOVED***)
        names = s.participant_names()
        assert "alice" in names
        assert "bob" in names

    def test_get_session_missing(self, engine: CollaborationEngine):
        assert engine.get_session("collab-nope") is None

    def test_get_session_roundtrip(self, engine: CollaborationEngine, session: CollaborationSession):
        loaded = engine.get_session(session.session_id)
        assert loaded is not None
        assert loaded.topic == session.topic
        assert loaded.owner == "buffy"
        assert len(loaded.participants) == 3

    def test_list_sessions_empty(self, engine: CollaborationEngine):
        assert engine.list_sessions() == [***REMOVED***

    def test_list_sessions_filter_by_status(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.close_session(session.session_id)
        sessions = engine.list_sessions(status=SessionStatus.ACTIVE)
        assert all(s.session_id != session.session_id for s in sessions)
        closed = engine.list_sessions(status=SessionStatus.CLOSED)
        assert [s.session_id for s in closed***REMOVED*** == [session.session_id***REMOVED***

    def test_list_sessions_filter_by_participant(self, engine: CollaborationEngine):
        s1 = engine.create_session(topic="A", owner="buffy", participants=["alice"***REMOVED***)
        s2 = engine.create_session(topic="B", owner="alice")
        mine = engine.list_sessions(participant_name="alice")
        ids = {s.session_id for s in mine***REMOVED***
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_close_session(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.close_session(session.session_id) is True
        loaded = engine.get_session(session.session_id)
        assert loaded is not None
        assert loaded.status == SessionStatus.CLOSED
        assert loaded.closed_at != ""

    def test_close_session_twice_returns_false(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.close_session(session.session_id)
        assert engine.close_session(session.session_id) is False

    def test_close_missing_session(self, engine: CollaborationEngine):
        assert engine.close_session("collab-nope") is False

    def test_session_to_dict(self, session: CollaborationSession):
        d = session.to_dict()
        assert d["session_id"***REMOVED*** == session.session_id
        assert d["topic"***REMOVED*** == "Code Review"
        assert d["participant_count"***REMOVED*** == 3
        assert "participants" in d


# ═══════════════════════════════════════════════════════════════
# Participants
# ═══════════════════════════════════════════════════════════════


class TestParticipants:
    def test_join_session(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.join_session(session.session_id, "carol") is True
        loaded = engine.get_session(session.session_id)
        assert loaded is not None
        assert loaded.has_participant("carol")

    def test_join_session_with_role(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.join_session(session.session_id, "carol", role=ParticipantRole.VIEWER)
        loaded = engine.get_session(session.session_id)
        carol = loaded.get_participant("carol")
        assert carol is not None
        assert carol.role == ParticipantRole.VIEWER

    def test_join_owner_role_downgraded_to_editor(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.join_session(session.session_id, "mallory", role=ParticipantRole.OWNER)
        loaded = engine.get_session(session.session_id)
        mallory = loaded.get_participant("mallory")
        assert mallory.role == ParticipantRole.EDITOR

    def test_join_closed_session_fails(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.close_session(session.session_id)
        assert engine.join_session(session.session_id, "carol") is False

    def test_join_invalid_role_fails(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.join_session(session.session_id, "carol", role="admin") is False

    def test_leave_session(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.leave_session(session.session_id, "alice") is True
        loaded = engine.get_session(session.session_id)
        alice = loaded.get_participant("alice")
        assert alice is not None
        assert alice.is_present is False

    def test_leave_non_participant(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.leave_session(session.session_id, "ghost") is False

    def test_update_participant_role(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.update_participant_role(session.session_id, "alice", ParticipantRole.VIEWER) is True
        loaded = engine.get_session(session.session_id)
        alice = loaded.get_participant("alice")
        assert alice.role == ParticipantRole.VIEWER

    def test_update_role_owner_for_non_owner_downgraded(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.update_participant_role(session.session_id, "alice", ParticipantRole.OWNER)
        loaded = engine.get_session(session.session_id)
        alice = loaded.get_participant("alice")
        assert alice.role == ParticipantRole.EDITOR

    def test_update_role_invalid(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.update_participant_role(session.session_id, "alice", "admin") is False

    def test_update_role_missing_participant(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.update_participant_role(session.session_id, "ghost", ParticipantRole.VIEWER) is False

    def test_sync_presence_marks_offline(self, tmp_path):
        engine = CollaborationEngine(
            db_path=tmp_path / "c.db",
            presence_engine=_StubPresence(offline=["alice"***REMOVED***),
        )
        s = engine.create_session(topic="T", owner="buffy", participants=["alice", "bob"***REMOVED***)
        updated = engine.sync_presence()
        assert updated >= 1
        loaded = engine.get_session(s.session_id)
        alice = loaded.get_participant("alice")
        assert alice.is_present is False
        bob = loaded.get_participant("bob")
        assert bob.is_present is True

    def test_sync_presence_without_engine(self, engine: CollaborationEngine):
        assert engine.sync_presence() == 0


# ═══════════════════════════════════════════════════════════════
# Messages
# ═══════════════════════════════════════════════════════════════


class TestMessages:
    def test_send_message(self, engine: CollaborationEngine, session: CollaborationSession):
        msg = engine.send_message(session.session_id, "alice", "Hello!")
        assert isinstance(msg, CollabMessage)
        assert msg.sender == "alice"
        assert msg.content == "Hello!"
        assert msg.msg_type == "text"
        assert msg.session_id == session.session_id

    def test_send_message_increments_count(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.send_message(session.session_id, "alice", "one")
        engine.send_message(session.session_id, "bob", "two")
        loaded = engine.get_session(session.session_id)
        assert loaded.message_count == 2

    def test_send_message_to_closed_session(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.close_session(session.session_id)
        assert engine.send_message(session.session_id, "alice", "hi") is None

    def test_send_message_with_type_and_reply(self, engine: CollaborationEngine, session: CollaborationSession):
        first = engine.send_message(session.session_id, "buffy", "decision made", msg_type="decision")
        reply = engine.send_message(session.session_id, "alice", "agreed", reply_to=first.id)
        assert reply.reply_to == first.id

    def test_send_message_not_required_to_be_participant(self, engine: CollaborationEngine, session: CollaborationSession):
        # Контракт: отправитель не обязан быть участником.
        msg = engine.send_message(session.session_id, "outsider", "ping")
        assert msg is not None

    def test_get_history(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.send_message(session.session_id, "alice", "hello")
        engine.send_message(session.session_id, "bob", "hi there")
        history = engine.get_history(session.session_id)
        contents = [m.content for m in history***REMOVED***
        assert "hello" in contents
        assert "hi there" in contents

    def test_history_includes_system_messages(self, engine: CollaborationEngine, session: CollaborationSession):
        history = engine.get_history(session.session_id)
        system_msgs = [m for m in history if m.msg_type == "system"***REMOVED***
        assert len(system_msgs) >= 2  # created + joined
        assert any("created" in m.content for m in system_msgs)
        assert any("joined" in m.content for m in system_msgs)

    def test_history_pagination_limit(self, engine: CollaborationEngine, session: CollaborationSession):
        for i in range(5):
            engine.send_message(session.session_id, "alice", f"msg {i***REMOVED***")
        history = engine.get_history(session.session_id, limit=3)
        assert len(history) <= 3

    def test_history_since_filter(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.send_message(session.session_id, "alice", "before")
        since = datetime.now(timezone.utc).isoformat()
        engine.send_message(session.session_id, "alice", "after")
        history = engine.get_history(session.session_id, since=since)
        assert all(m.content == "after" for m in history)

    def test_history_missing_session(self, engine: CollaborationEngine):
        assert engine.get_history("collab-nope") == [***REMOVED***


# ═══════════════════════════════════════════════════════════════
# EventBus integration
# ═══════════════════════════════════════════════════════════════


class TestEventBus:
    def test_publishes_events(self, tmp_path):
        bus = _StubEventBus()
        engine = CollaborationEngine(db_path=tmp_path / "c.db", event_bus=bus)
        s = engine.create_session(topic="T", owner="buffy")
        engine.send_message(s.session_id, "buffy", "hi")
        engine.close_session(s.session_id)
        types = [getattr(e, "type", None) for e in bus.events***REMOVED***
        assert "collab.created" in types
        assert "collab.message" in types
        assert "collab.closed" in types

    def test_join_publishes_joined(self, tmp_path):
        bus = _StubEventBus()
        engine = CollaborationEngine(db_path=tmp_path / "c.db", event_bus=bus)
        s = engine.create_session(topic="T", owner="buffy")
        engine.join_session(s.session_id, "alice")
        engine.leave_session(s.session_id, "alice")
        types = [getattr(e, "type", None) for e in bus.events***REMOVED***
        assert "collab.joined" in types
        assert "collab.left" in types

    def test_get_recent_events_with_bus(self, tmp_path):
        bus = _StubEventBus()
        engine = CollaborationEngine(db_path=tmp_path / "c.db", event_bus=bus)
        s = engine.create_session(topic="T", owner="buffy")
        engine.send_message(s.session_id, "buffy", "hello")
        events = engine.get_recent_events(s.session_id, limit=10)
        assert any(e["data"***REMOVED***.get("session_id") == s.session_id for e in events)

    def test_get_recent_events_without_bus(self, engine: CollaborationEngine, session: CollaborationSession):
        assert engine.get_recent_events(session.session_id) == [***REMOVED***


# ═══════════════════════════════════════════════════════════════
# Status / diagnostics
# ═══════════════════════════════════════════════════════════════


class TestStatus:
    def test_get_status(self, engine: CollaborationEngine, session: CollaborationSession):
        engine.send_message(session.session_id, "alice", "hello")
        st = engine.get_status()
        assert st["status"***REMOVED*** == "running"
        assert st["running"***REMOVED*** is True
        assert st["total_sessions"***REMOVED*** >= 1
        assert st["active_sessions"***REMOVED*** >= 1
        assert st["total_messages"***REMOVED*** >= 1
        assert st["total_participants"***REMOVED*** >= 1
        assert st["eventbus_connected"***REMOVED*** is False
        assert st["presence_connected"***REMOVED*** is False

    def test_get_status_with_connections(self, tmp_path):
        bus = _StubEventBus()
        engine = CollaborationEngine(
            db_path=tmp_path / "c.db",
            event_bus=bus,
            presence_engine=_StubPresence(),
        )
        st = engine.get_status()
        assert st["eventbus_connected"***REMOVED*** is True
        assert st["presence_connected"***REMOVED*** is True


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts.collaboration import main

        monkeypatch.setattr(sys, "argv", ["collaboration.py", "--help"***REMOVED***)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_no_command(self, monkeypatch, capsys):
        from scripts.collaboration import main

        monkeypatch.setattr(sys, "argv", ["collaboration.py"***REMOVED***)
        code = main()
        assert code == 1
