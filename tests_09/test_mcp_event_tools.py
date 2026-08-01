"""
Тесты для MCP event инструментов в freebuff_plugin_03/mcp_server.py.

Покрытие: event_search, event_timeline, event_replay, event_audit, event_pulse
~12 тестов
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
***REMOVED***
from typing import Any, Dict, Generator, List

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from freebuff_plugin_03.event.store import EventStore
from freebuff_plugin_03.event.audit import AuditEngine
from freebuff_plugin_03.event import AuditDecision, AuditAction


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def tmp_db() -> Generator[Path, None, None***REMOVED***:
    """Временная БД для тестов."""
    tmp = tempfile.mktemp(suffix=".db", prefix="mcp_event_test_")
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
                data={"version": "4.7.0"***REMOVED***)
    store.store(event_type="session.created", source="context_manager",
                data={"topic": "Test Session"***REMOVED***, session_id="sess-mcp-1")
    store.store(event_type="task.created", source="orchestrator",
                data={"task_id": "t-mcp-1"***REMOVED***, session_id="sess-mcp-1")
    store.store(event_type="task.completed", source="orchestrator",
                data={"task_id": "t-mcp-1", "duration_ms": 500***REMOVED***,
                session_id="sess-mcp-1")
    store.store(event_type="session.completed", source="context_manager",
                data={***REMOVED***, session_id="sess-mcp-1")
    return store


@pytest.fixture
def server() -> Generator[Any, None, None***REMOVED***:
    """MCPServer instance with mocked dependencies."""
    # We don't want to actually run the plugin bridge/wrapper
    # So we test through _call_tool directly on a patched server
    from unittest.mock import patch

    with patch("freebuff_plugin_03.mcp_server.plugin_bridge"), \
         patch("freebuff_plugin_03.mcp_server.plugin_wrapper"), \
         patch("freebuff_plugin_03.mcp_server.ScenarioEngine"):
        from freebuff_plugin_03.mcp_server import MCPServer
        srv = MCPServer()
        yield srv


# ═══════════════════════════════════════════════════════════════
# 1. Event tools in tools/list
# ═══════════════════════════════════════════════════════════════


class TestEventToolsList:
    """Проверка что event tools есть в tools/list."""

    def test_event_tools_registered(self, server):
        """5 event tools должны быть в _list_tools()."""
        tools = server._list_tools()
        names = [t["name"***REMOVED*** for t in tools***REMOVED***
        assert "event_search" in names
        assert "event_timeline" in names
        assert "event_replay" in names
        assert "event_audit" in names
        assert "event_pulse" in names

    def test_event_tools_have_schema(self, server):
        """Каждый event tool имеет inputSchema."""
        tools = server._list_tools()
        event_tools = [t for t in tools if t["name"***REMOVED***.startswith("event_")***REMOVED***
        assert len(event_tools) == 5
        for t in event_tools:
            assert "inputSchema" in t
            assert t["inputSchema"***REMOVED***["type"***REMOVED*** == "object"

    def test_event_search_has_properties(self, server):
        """event_search должен иметь event_type, session_id, data_search."""
        tools = server._list_tools()
        es = next(t for t in tools if t["name"***REMOVED*** == "event_search")
        props = es["inputSchema"***REMOVED***["properties"***REMOVED***
        assert "event_type" in props
        assert "session_id" in props
        assert "data_search" in props


# ═══════════════════════════════════════════════════════════════
# 2. Event Search
# ═══════════════════════════════════════════════════════════════


class TestEventSearch:
    """MCP event_search tool."""

    def test_event_search_empty(self, server, tmp_db):
        """event_search в пустом Event Store."""
        estore = EventStore(db_path=tmp_db)
        server._event_store = estore
        result = server._call_tool("event_search", {***REMOVED***)
        assert "content" in result
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_event_search_by_type(self, server, populated_store):
        """event_search по event_type."""
        server._event_store = populated_store
        result = server._call_tool("event_search", {"event_type": "task.*"***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert len(data) >= 2

    def test_event_search_by_session(self, server, populated_store):
        """event_search по session_id."""
        server._event_store = populated_store
        result = server._call_tool("event_search", {"session_id": "sess-mcp-1"***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert len(data) >= 4

    def test_event_search_return_fields(self, server, populated_store):
        """event_search возвращает корректные поля."""
        server._event_store = populated_store
        result = server._call_tool("event_search", {***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert len(data) >= 1
        assert "id" in data[0***REMOVED***
        assert "type" in data[0***REMOVED***
        assert "source" in data[0***REMOVED***
        assert "data" in data[0***REMOVED***
        assert "timestamp" in data[0***REMOVED***


# ═══════════════════════════════════════════════════════════════
# 3. Event Timeline
# ═══════════════════════════════════════════════════════════════


class TestEventTimeline:
    """MCP event_timeline tool."""

    def test_timeline_empty(self, server, tmp_db):
        """event_timeline в пустом Event Store."""
        estore = EventStore(db_path=tmp_db)
        server._event_store = estore
        result = server._call_tool("event_timeline", {***REMOVED***)
        assert "content" in result
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        # format_timeline_text для пустой шкалы: "📭 Нет событий в временной шкале."
        assert "📭" in text
        assert isinstance(text, str)
        assert len(text) > 0

    def test_timeline_has_events(self, server, populated_store):
        """event_timeline возвращает отформатированные события."""
        server._event_store = populated_store
        result = server._call_tool("event_timeline", {"limit": 5***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert len(text) > 0
        # Должны быть иконки и таймштампы
        assert " — " in text


# ═══════════════════════════════════════════════════════════════
# 4. Event Replay
# ═══════════════════════════════════════════════════════════════


class TestEventReplay:
    """MCP event_replay tool."""

    def test_replay_empty(self, server, tmp_db):
        """event_replay в пустом Event Store."""
        estore = EventStore(db_path=tmp_db)
        server._event_store = estore
        result = server._call_tool("event_replay", {***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert data["total"***REMOVED*** == 0
        assert data["delivered"***REMOVED*** == 0

    def test_replay_with_events(self, server, populated_store):
        """event_replay с событиями."""
        server._event_store = populated_store
        result = server._call_tool("event_replay", {"event_type": "system.*"***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert data["total"***REMOVED*** >= 1
        assert data["errors"***REMOVED*** == 0
        assert "duration_ms" in data

    def test_replay_instant_speed(self, server, populated_store):
        """event_replay со speed=instant."""
        server._event_store = populated_store
        result = server._call_tool("event_replay", {
            "event_type": "task.*",
            "speed": "instant",
        ***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert data["total"***REMOVED*** == 2


# ═══════════════════════════════════════════════════════════════
# 5. Event Audit
# ═══════════════════════════════════════════════════════════════


class TestEventAudit:
    """MCP event_audit tool."""

    def test_audit_empty(self, server, tmp_db):
        """event_audit в пустом Event Store."""
        estore = EventStore(db_path=tmp_db)
        server._event_store = estore
        result = server._call_tool("event_audit", {***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert "Нет записей аудита" in text

    def test_audit_with_decisions(self, server, store):
        """event_audit с audit.decision событиями."""
        server._event_store = store
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="test-policy",
            capability="coding",
            runtime_selected="freebuff",
            cost_estimate=0.01,
        ))

        result = server._call_tool("event_audit", {"limit": 10***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert "AUDIT LOG" in text
        assert "test-policy" in text

    def test_audit_filter_by_type(self, server, store):
        """event_audit с фильтром target_type."""
        server._event_store = store
        audit = AuditEngine(store)
        audit.log_decision(AuditDecision(
            policy_name="policy-x", capability="coding", runtime_selected="freebuff"
        ))
        audit.log_action(AuditAction(
            actor="user", action="override", target="runtime"
        ))

        # Фильтр по decision
        result = server._call_tool("event_audit", {"target_type": "decision"***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert "DECISION" in text
        assert "policy-x" in text

        # Фильтр по action
        result = server._call_tool("event_audit", {"target_type": "action"***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        assert "ACTION" in text
        assert "user" in text


# ═══════════════════════════════════════════════════════════════
# 6. Event Pulse
# ═══════════════════════════════════════════════════════════════


class TestEventPulse:
    """MCP event_pulse tool."""

    def test_pulse_empty(self, server, tmp_db):
        """event_pulse в пустом Event Store."""
        estore = EventStore(db_path=tmp_db)
        server._event_store = estore
        result = server._call_tool("event_pulse", {***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_pulse_with_events(self, server, store):
        """event_pulse с _pulse событиями.

        Note: relies on PulseEngine fallback (FTS5 unicode61 tokenizer
        treats _pulse as single token, not matching 'pulse' search term).
        """
        server._event_store = store
        store.store(
            event_type="task.completed",
            source="orchestrator",
            data={"task_id": "t-001", "_pulse": True***REMOVED***,
        )
        store.store(
            event_type="memory.stored",
            source="memory_engine",
            data={"key": "note", "_pulse": True***REMOVED***,
        )

        result = server._call_tool("event_pulse", {"limit": 10***REMOVED***)
        text = result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
        data = json.loads(text)
        assert len(data) >= 1
        assert "icon" in data[0***REMOVED***
        assert "title" in data[0***REMOVED***
        assert "severity" in data[0***REMOVED***


# ═══════════════════════════════════════════════════════════════
# 7. Error Handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Обработка ошибок в event tools."""

    def test_unknown_tool(self, server):
        """Неизвестный инструмент."""
        result = server._call_tool("nonexistent", {***REMOVED***)
        assert result["isError"***REMOVED*** is True
        assert "Unknown tool" in result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***

    def test_event_search_exception(self, server, store):
        """Ошибка в event_search."""
        # Мокаем query чтобы он выбросил исключение
        import unittest.mock as mock
        store._event_store = None  # Это не сработает, т.к. _get_event_store создаёт новый
        # Правильный подход: пакуем store с багнутой query
        server._event_store = store
        with mock.patch.object(store, 'query', side_effect=RuntimeError("test error")):
            result = server._call_tool("event_search", {"event_type": "test"***REMOVED***)
            assert result["isError"***REMOVED*** is True
            assert "Error" in result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
            assert "test error" in result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***
