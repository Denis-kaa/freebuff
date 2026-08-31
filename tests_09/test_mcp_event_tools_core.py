#!/usr/bin/env python3
"""
Тесты MCP event-инструментов в scripts_01/mcp_server.py (core server).

Покрытие: event_search, event_timeline, event_replay, event_audit, event_pulse
(5 инструментов из EVENT_PLATFORM_SPECIFICATION §9, category="event").

Паттерн вызова: handle_tools_call({"name": ..., "arguments": ...}) →
{"content": [{"type": "text", "text": "<json>"}]}.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from scripts_01.mcp_server import BuffyMcpServer
from freebuff_plugin_03.event.store import EventStore
from freebuff_plugin_03.event.audit import AuditEngine
from freebuff_plugin_03.event import AuditDecision, AuditAction


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_db() -> Generator[Path, None, None]:
    """Временная БД для тестов."""
    tmp = tempfile.mktemp(suffix=".db", prefix="mcp_event_core_test_")
    yield Path(tmp)
    if Path(tmp).exists():
        Path(tmp).unlink(missing_ok=True)


@pytest.fixture
def store(tmp_db: Path) -> EventStore:
    """EventStore с временной БД."""
    return EventStore(db_path=tmp_db)


@pytest.fixture
def populated_store(store: EventStore) -> EventStore:
    """EventStore с тестовыми событиями (5 штук)."""
    store.store(event_type="system.startup", source="system",
                data={"version": "4.7.0"})
    store.store(event_type="session.created", source="context_manager",
                data={"topic": "Test Session"}, session_id="sess-core-1")
    store.store(event_type="task.created", source="orchestrator",
                data={"task_id": "t-core-1"}, session_id="sess-core-1")
    store.store(event_type="task.completed", source="orchestrator",
                data={"task_id": "t-core-1", "duration_ms": 500},
                session_id="sess-core-1")
    store.store(event_type="session.completed", source="context_manager",
                data={}, session_id="sess-core-1")
    return store


@pytest.fixture
def server(tmp_path: Path) -> BuffyMcpServer:
    """BuffyMcpServer с временным workspace (не трогает реальный data_13)."""
    return BuffyMcpServer(workspace_root=str(tmp_path))


def _call(server: BuffyMcpServer, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Вызвать инструмент через handle_tools_call и вернуть распарсенный payload."""
    result = server.handle_tools_call({"name": name, "arguments": arguments})
    text = result["content"][0]["text"]
    return json.loads(text)


# ═══════════════════════════════════════════════════════════════
# 1. Event tools in tools/list
# ═══════════════════════════════════════════════════════════════


class TestEventToolsRegistered:
    """Проверка что 5 event tools зарегистрированы в core-сервере."""

    def test_event_tools_in_list(self, server: BuffyMcpServer) -> None:
        """Все 5 event tools должны быть в handle_tools_list."""
        tools = server.handle_tools_list({})["tools"]
        names = {t["name"] for t in tools}
        for expected in ("event_search", "event_timeline", "event_replay",
                         "event_audit", "event_pulse"):
            assert expected in names

    def test_event_tools_category(self, server: BuffyMcpServer) -> None:
        """Каждый event tool имеет category='event' и inputSchema."""
        for name in ("event_search", "event_timeline", "event_replay",
                     "event_audit", "event_pulse"):
            tool = server._tools[name]
            assert tool.category == "event"
            assert tool.input_schema["type"] == "object"

    def test_event_search_schema(self, server: BuffyMcpServer) -> None:
        """event_search принимает event_type, session_id, data_search, limit."""
        props = server._tools["event_search"].input_schema["properties"]
        assert "event_type" in props
        assert "session_id" in props
        assert "data_search" in props
        assert "limit" in props


# ═══════════════════════════════════════════════════════════════
# 2. Event Search
# ═══════════════════════════════════════════════════════════════


class TestEventSearch:
    """MCP event_search tool (core)."""

    def test_search_empty(self, server: BuffyMcpServer, tmp_db: Path) -> None:
        """event_search в пустом Event Store."""
        server._event_store = EventStore(db_path=tmp_db)
        data = _call(server, "event_search", {})
        assert data["success"] is True
        assert data["data"] == []

    def test_search_by_type(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_search по wildcard event_type."""
        server._event_store = populated_store
        data = _call(server, "event_search", {"event_type": "task.*"})
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_search_by_session(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_search по session_id."""
        server._event_store = populated_store
        data = _call(server, "event_search", {"session_id": "sess-core-1"})
        assert data["success"] is True
        assert len(data["data"]) == 4

    def test_search_return_fields(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_search возвращает id/type/source/data/timestamp."""
        server._event_store = populated_store
        data = _call(server, "event_search", {})
        entry = data["data"][0]
        for field in ("id", "type", "source", "data", "timestamp"):
            assert field in entry


# ═══════════════════════════════════════════════════════════════
# 3. Event Timeline
# ═══════════════════════════════════════════════════════════════


class TestEventTimeline:
    """MCP event_timeline tool (core)."""

    def test_timeline_empty(self, server: BuffyMcpServer, tmp_db: Path) -> None:
        """event_timeline в пустом Event Store."""
        server._event_store = EventStore(db_path=tmp_db)
        data = _call(server, "event_timeline", {})
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert "📭" in data["data"]["text"]

    def test_timeline_with_events(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_timeline возвращает отформатированные события."""
        server._event_store = populated_store
        data = _call(server, "event_timeline", {"limit": 5})
        assert data["success"] is True
        assert data["data"]["total"] >= 1
        assert len(data["data"]["entries"]) >= 1
        assert " — " in data["data"]["text"]


# ═══════════════════════════════════════════════════════════════
# 4. Event Replay
# ═══════════════════════════════════════════════════════════════


class TestEventReplay:
    """MCP event_replay tool (core)."""

    def test_replay_empty(self, server: BuffyMcpServer, tmp_db: Path) -> None:
        """event_replay в пустом Event Store."""
        server._event_store = EventStore(db_path=tmp_db)
        data = _call(server, "event_replay", {})
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["delivered"] == 0

    def test_replay_with_events(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_replay с событиями."""
        server._event_store = populated_store
        data = _call(server, "event_replay", {"event_type": "system.*"})
        assert data["success"] is True
        assert data["data"]["total"] == 1
        assert data["data"]["errors"] == 0
        assert "duration_ms" in data["data"]

    def test_replay_instant(self, server: BuffyMcpServer, populated_store: EventStore) -> None:
        """event_replay со speed=instant."""
        server._event_store = populated_store
        data = _call(server, "event_replay", {"event_type": "task.*", "speed": "instant"})
        assert data["success"] is True
        assert data["data"]["total"] == 2


# ═══════════════════════════════════════════════════════════════
# 5. Event Audit
# ═══════════════════════════════════════════════════════════════


class TestEventAudit:
    """MCP event_audit tool (core)."""

    def test_audit_empty(self, server: BuffyMcpServer, tmp_db: Path) -> None:
        """event_audit в пустом Event Store."""
        server._event_store = EventStore(db_path=tmp_db)
        data = _call(server, "event_audit", {})
        assert data["success"] is True
        assert "Нет записей аудита" in data["data"]["text"]

    def test_audit_with_decisions(self, server: BuffyMcpServer, store: EventStore) -> None:
        """event_audit с audit.decision событиями."""
        server._event_store = store
        AuditEngine(store).log_decision(AuditDecision(
            policy_name="test-policy",
            capability="coding",
            runtime_selected="freebuff",
            cost_estimate=0.01,
        ))
        data = _call(server, "event_audit", {"limit": 10})
        assert data["success"] is True
        assert "AUDIT LOG" in data["data"]["text"]
        assert "test-policy" in data["data"]["text"]

    def test_audit_filter_by_type(self, server: BuffyMcpServer, store: EventStore) -> None:
        """event_audit с фильтром target_type."""
        server._event_store = store
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="policy-x", capability="coding", runtime_selected="freebuff"
        ))
        audit.log_action(AuditAction(actor="user", action="override", target="runtime"))

        data = _call(server, "event_audit", {"target_type": "decision"})
        assert data["data"]["entries"] and data["data"]["entries"][0]["type"] == "decision"
        assert "DECISION" in data["data"]["text"]

        data = _call(server, "event_audit", {"target_type": "action"})
        assert data["data"]["entries"] and data["data"]["entries"][0]["type"] == "action"
        assert "ACTION" in data["data"]["text"]


# ═══════════════════════════════════════════════════════════════
# 6. Event Pulse
# ═══════════════════════════════════════════════════════════════


class TestEventPulse:
    """MCP event_pulse tool (core)."""

    def test_pulse_empty(self, server: BuffyMcpServer, tmp_db: Path) -> None:
        """event_pulse в пустом Event Store."""
        server._event_store = EventStore(db_path=tmp_db)
        data = _call(server, "event_pulse", {})
        assert data["success"] is True
        assert data["data"] == []

    def test_pulse_with_events(self, server: BuffyMcpServer, store: EventStore) -> None:
        """event_pulse с _pulse событиями (fallback по категориям)."""
        server._event_store = store
        store.store(event_type="task.completed", source="orchestrator",
                    data={"task_id": "t-001", "_pulse": True})
        store.store(event_type="memory.stored", source="memory_engine",
                    data={"key": "note", "_pulse": True})

        data = _call(server, "event_pulse", {"limit": 10})
        assert data["success"] is True
        assert len(data["data"]) >= 1
        for field in ("icon", "title", "severity"):
            assert field in data["data"][0]


# ═══════════════════════════════════════════════════════════════
# 7. Error handling
# ═══════════════════════════════════════════════════════════════


class TestEventToolsErrorHandling:
    """Обработка ошибок в event tools (core)."""

    def test_search_store_error(self, server: BuffyMcpServer, store: EventStore) -> None:
        """Ошибка EventStore.query возвращает success=False."""
        server._event_store = store
        import unittest.mock as mock
        with mock.patch.object(store, "query", side_effect=RuntimeError("boom")):
            data = _call(server, "event_search", {"event_type": "test"})
        assert data["success"] is False
        assert "boom" in data["error"]

    def test_store_unavailable(self, server: BuffyMcpServer, monkeypatch: pytest.MonkeyPatch) -> None:
        """EventStore недоступен — graceful degradation."""
        server._event_store = None
        monkeypatch.setattr(server, "_get_event_store", lambda: None)
        data = _call(server, "event_search", {})
        assert data["success"] is False
        assert "not available" in data["error"]
