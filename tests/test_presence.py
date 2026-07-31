#!/usr/bin/env python3
"""
Tests for Presence Engine (scripts/presence.py).

Tests:
  - PresenceStatus validation
  - register / get / unregister
  - update_status with task/error/metadata
  - heartbeat
  - list / filters / count
  - history
  - JSON helpers (MCP)
  - lifecycle: start/stop, prune offline
  - CLI commands
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.presence import (
    PresenceEngine,
    AgentPresence,
    PresenceHistoryEntry,
    PresenceStatus,
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_PRUNE_TIMEOUT,
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


@pytest.fixture
def engine(tmp_path) -> PresenceEngine:
    return PresenceEngine(
        db_path=tmp_path / "presence_test.db",
        heartbeat_interval=1000,  # не даём heartbeat-потоку мешать тестам
    )


# ═══════════════════════════════════════════════════════════════
# PresenceStatus
# ═══════════════════════════════════════════════════════════════


class TestPresenceStatus:
    def test_constants(self):
        assert PresenceStatus.ONLINE == "online"
        assert PresenceStatus.OFFLINE == "offline"
        assert PresenceStatus.BUSY == "busy"
        assert PresenceStatus.AWAY == "away"
        assert PresenceStatus.ERROR == "error"

    def test_is_valid(self):
        assert PresenceStatus.is_valid("online")
        assert PresenceStatus.is_valid("busy")
        assert PresenceStatus.is_valid("error")
        assert not PresenceStatus.is_valid("zombie")

    def test_defaults(self):
        assert DEFAULT_HEARTBEAT_INTERVAL == 30
        assert DEFAULT_PRUNE_TIMEOUT == 120


# ═══════════════════════════════════════════════════════════════
# Register / get / unregister
# ═══════════════════════════════════════════════════════════════


class TestRegister:
    def test_register_returns_agent(self, engine: PresenceEngine):
        agent = engine.register("buffy", capabilities={"code": "Code generation"***REMOVED***)
        assert isinstance(agent, AgentPresence)
        assert agent.agent_name == "buffy"
        assert agent.status == PresenceStatus.ONLINE
        assert agent.capabilities == {"code": "Code generation"***REMOVED***

    def test_register_persists(self, engine: PresenceEngine):
        engine.register("buffy")
        loaded = engine.get("buffy")
        assert loaded is not None
        assert loaded.agent_name == "buffy"

    def test_register_invalid_status_defaults_to_online(self, engine: PresenceEngine):
        agent = engine.register("weird", status="zombie")
        assert agent.status == PresenceStatus.ONLINE

    def test_register_with_host_and_metadata(self, engine: PresenceEngine):
        agent = engine.register(
            "buffy",
            version="2.0.0",
            host_info={"os": "linux"***REMOVED***,
            metadata={"team": "core"***REMOVED***,
        )
        assert agent.version == "2.0.0"
        assert agent.host_info == {"os": "linux"***REMOVED***
        assert agent.metadata == {"team": "core"***REMOVED***

    def test_register_twice_preserves_registered_at(self, engine: PresenceEngine):
        first = engine.register("buffy")
        second = engine.register("buffy")
        assert second.registered_at == first.registered_at

    def test_get_missing_returns_none(self, engine: PresenceEngine):
        assert engine.get("ghost") is None

    def test_unregister(self, engine: PresenceEngine):
        engine.register("buffy")
        assert engine.unregister("buffy") is True
        assert engine.get("buffy") is None

    def test_unregister_missing(self, engine: PresenceEngine):
        assert engine.unregister("ghost") is False


# ═══════════════════════════════════════════════════════════════
# update_status / heartbeat
# ═══════════════════════════════════════════════════════════════


class TestUpdateStatus:
    def test_update_status_busy_with_task(self, engine: PresenceEngine):
        engine.register("buffy")
        agent = engine.update_status("buffy", PresenceStatus.BUSY, current_task="Refactoring")
        assert agent is not None
        assert agent.status == PresenceStatus.BUSY
        assert agent.current_task == "Refactoring"

    def test_update_status_error(self, engine: PresenceEngine):
        engine.register("buffy")
        agent = engine.update_status("buffy", PresenceStatus.ERROR, error="boom")
        assert agent.status == PresenceStatus.ERROR
        assert agent.error == "boom"

    def test_update_status_metadata_merged(self, engine: PresenceEngine):
        engine.register("buffy")
        agent = engine.update_status("buffy", PresenceStatus.BUSY, metadata={"roles": ["developer"***REMOVED******REMOVED***)
        assert agent.metadata["roles"***REMOVED*** == ["developer"***REMOVED***

    def test_update_status_unknown_agent(self, engine: PresenceEngine):
        assert engine.update_status("ghost", PresenceStatus.BUSY) is None

    def test_update_status_invalid_status(self, engine: PresenceEngine):
        engine.register("buffy")
        assert engine.update_status("buffy", "zombie") is None

    def test_update_status_offline_online(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.update_status("buffy", PresenceStatus.OFFLINE)
        agent = engine.get("buffy")
        assert agent.status == PresenceStatus.OFFLINE
        engine.update_status("buffy", PresenceStatus.ONLINE)
        agent = engine.get("buffy")
        assert agent.status == PresenceStatus.ONLINE

    def test_heartbeat_updates_last_heartbeat(self, engine: PresenceEngine):
        engine.register("buffy")
        before = engine.get("buffy").last_heartbeat
        agent = engine.heartbeat("buffy")
        assert agent is not None
        assert agent.last_heartbeat >= before

    def test_heartbeat_unknown_agent(self, engine: PresenceEngine):
        assert engine.heartbeat("ghost") is None


# ═══════════════════════════════════════════════════════════════
# Lists / filters / count
# ═══════════════════════════════════════════════════════════════


class TestLists:
    def test_list_agents(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.register("alice")
        assert len(engine.list_agents()) == 2

    def test_list_agents_by_status(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.register("alice")
        engine.update_status("buffy", PresenceStatus.BUSY)
        busy = engine.list_agents(status=PresenceStatus.BUSY)
        assert [a.agent_name for a in busy***REMOVED*** == ["buffy"***REMOVED***

    def test_list_agents_by_capability(self, engine: PresenceEngine):
        engine.register("buffy", capabilities={"code": "gen"***REMOVED***)
        engine.register("alice", capabilities={"docs": "write"***REMOVED***)
        agents = engine.list_agents(capability="code")
        assert [a.agent_name for a in agents***REMOVED*** == ["buffy"***REMOVED***

    def test_list_online(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.register("alice")
        engine.update_status("alice", PresenceStatus.OFFLINE)
        online = engine.list_online()
        assert [a.agent_name for a in online***REMOVED*** == ["buffy"***REMOVED***

    def test_count(self, engine: PresenceEngine):
        assert engine.count() == 0
        engine.register("buffy")
        engine.register("alice")
        assert engine.count() == 2


# ═══════════════════════════════════════════════════════════════
# History
# ═══════════════════════════════════════════════════════════════


class TestHistory:
    def test_history_records_status_changes(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.update_status("buffy", PresenceStatus.BUSY, current_task="T1")
        engine.update_status("buffy", PresenceStatus.ONLINE)
        history = engine.get_history(agent_name="buffy")
        assert len(history) >= 3
        assert all(isinstance(e, PresenceHistoryEntry) for e in history)
        new_statuses = [e.new_status for e in history***REMOVED***
        assert PresenceStatus.BUSY in new_statuses

    def test_history_filter_by_agent(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.register("alice")
        engine.update_status("alice", PresenceStatus.BUSY)
        history = engine.get_history(agent_name="alice")
        assert all(e.agent_name == "alice" for e in history)

    def test_history_limit(self, engine: PresenceEngine):
        engine.register("buffy")
        for _ in range(5):
            engine.update_status("buffy", PresenceStatus.BUSY, current_task="x")
            engine.update_status("buffy", PresenceStatus.ONLINE)
        history = engine.get_history(limit=3)
        assert len(history) <= 3

    def test_history_empty(self, engine: PresenceEngine):
        assert engine.get_history() == [***REMOVED***


# ═══════════════════════════════════════════════════════════════
# JSON helpers (MCP)
# ═══════════════════════════════════════════════════════════════


class TestJsonHelpers:
    def test_list_agents_json(self, engine: PresenceEngine):
        engine.register("buffy")
        payload = engine.list_agents_json()
        assert payload["success"***REMOVED*** is True
        assert payload["total"***REMOVED*** == 1
        assert payload["agents"***REMOVED***[0***REMOVED***["agent_name"***REMOVED*** == "buffy"
        assert payload["data"***REMOVED***["total"***REMOVED*** == 1

    def test_get_agent_json(self, engine: PresenceEngine):
        engine.register("buffy")
        payload = engine.get_agent_json("buffy")
        assert payload["success"***REMOVED*** is True
        assert payload["found"***REMOVED*** is True
        assert payload["data"***REMOVED***["agent_name"***REMOVED*** == "buffy"

    def test_get_agent_json_missing(self, engine: PresenceEngine):
        payload = engine.get_agent_json("ghost")
        assert payload["success"***REMOVED*** is False
        assert payload["found"***REMOVED*** is False

    def test_get_history_json(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.update_status("buffy", PresenceStatus.BUSY)
        payload = engine.get_history_json(agent_name="buffy")
        assert payload["success"***REMOVED*** is True
        assert payload["total"***REMOVED*** >= 1

    def test_agent_to_dict(self, engine: PresenceEngine):
        agent = engine.register("buffy")
        d = agent.to_dict()
        assert d["agent_name"***REMOVED*** == "buffy"
        assert "status" in d and "capabilities" in d


# ═══════════════════════════════════════════════════════════════
# Lifecycle: start / stop / prune
# ═══════════════════════════════════════════════════════════════


class TestLifecycle:
    def test_start_starts_heartbeat(self, engine: PresenceEngine):
        engine.start()
        assert engine.get_status()["running"***REMOVED*** is True
        engine.stop()

    def test_start_idempotent(self, engine: PresenceEngine):
        engine.start()
        engine.start()
        engine.stop()

    def test_stop_marks_online_agents_offline(self, engine: PresenceEngine):
        engine.register("buffy")
        engine.register("alice")
        engine.start()
        engine.stop()
        buffy = engine.get("buffy")
        alice = engine.get("alice")
        assert buffy.status == PresenceStatus.OFFLINE
        assert alice.status == PresenceStatus.OFFLINE

    def test_prune_offline_stale_agent(self, tmp_path):
        engine = PresenceEngine(
            db_path=tmp_path / "p.db",
            heartbeat_interval=1000,
            prune_timeout=1,
        )
        engine.register("stale")
        agent = engine.get("stale")
        agent.last_heartbeat = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        engine._save_agent(agent)
        pruned = engine._prune_offline()
        assert pruned == 1
        refreshed = engine.get("stale")
        assert refreshed.status == PresenceStatus.OFFLINE

    def test_prune_offline_fresh_agent(self, tmp_path):
        engine = PresenceEngine(db_path=tmp_path / "p.db", heartbeat_interval=1000, prune_timeout=60)
        engine.register("fresh")
        assert engine._prune_offline() == 0

    def test_publishes_events(self, tmp_path):
        bus = _StubEventBus()
        engine = PresenceEngine(db_path=tmp_path / "p.db", event_bus=bus)
        engine.register("buffy")
        engine.update_status("buffy", PresenceStatus.BUSY)
        engine.heartbeat("buffy")
        types = [getattr(e, "type", None) for e in bus.events***REMOVED***
        assert "presence.online" in types
        assert "presence.busy" in types
        assert "presence.heartbeat" in types

    def test_get_status(self, engine: PresenceEngine):
        st = engine.get_status()
        assert st["status"***REMOVED*** in ("running", "stopped")
        assert st["total_agents"***REMOVED*** == 0
        assert st["eventbus_connected"***REMOVED*** is False
        assert st["heartbeat_interval"***REMOVED*** == 1000


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


class TestCLI:
    def test_main_help(self, monkeypatch):
        from scripts.presence import main

        monkeypatch.setattr(sys, "argv", ["presence.py", "--help"***REMOVED***)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_main_no_command(self, monkeypatch, capsys):
        from scripts.presence import main

        monkeypatch.setattr(sys, "argv", ["presence.py"***REMOVED***)
        code = main()
        assert code == 1
