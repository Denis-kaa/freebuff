"""Tests for Phase 5.4 sync-status surface (Flutter UI indicator).

Covers the Python-side status derivation + active-coordinator registry:

  - `derive_sync_status()` — closed-vocab priority: quarantine > conflict >
    connected > idle.
  - `_normalize_sync_status()` — unknown tokens collapse to `idle` (CON-8).
  - `set_active_coordinator` / `get_active_coordinator` — registry round-trip.
  - `publish_sync_status_event()` — None-safe per CAN-14 (no active
    coordinator / EventStore unavailable → None, never raises).
  - MCP tool `sync_status` handler (`freebuff_plugin_03.mcp_server`) —
    returns a JSON text snapshot with closed-vocab status.
"""

from __future__ import annotations

import json
import threading
from unittest.mock import MagicMock

from core_02.remote_sync import (
    RemoteSyncCoordinatorImpl,
    _normalize_sync_status,
    derive_sync_status,
    get_active_coordinator,
    publish_sync_status_event,
    set_active_coordinator,
)


def _fresh_coordinator() -> RemoteSyncCoordinatorImpl:
    """Construct a coordinator with no listener attached (idle by default)."""
    return RemoteSyncCoordinatorImpl(device_label="test-ui-indicator")


class _FakeListener:
    """Minimal listener stub exposing only what derive_sync_status reads."""

    def __init__(self, running: bool) -> None:
        self._running = running

    @property
    def is_running(self) -> bool:
        return self._running


# ── _normalize_sync_status (closed-vocab guard) ─────────────────────────


class TestNormalizeSyncStatus:
    def test_known_tokens_pass_through(self) -> None:
        for token in ("idle", "connected", "conflict", "quarantine"):
            assert _normalize_sync_status(token) == token

    def test_unknown_token_collapses_to_idle(self) -> None:
        assert _normalize_sync_status("suspicious-token") == "idle"
        assert _normalize_sync_status("") == "idle"
        assert _normalize_sync_status("CONNECTED") == "idle"  # case-sensitive


# ── derive_sync_status priority ─────────────────────────────────────────


class TestDeriveSyncStatus:
    def test_fresh_coordinator_is_idle(self) -> None:
        coord = _fresh_coordinator()
        snap = derive_sync_status(coord)
        assert snap["status"***REMOVED*** == "idle"
        assert snap["listener_running"***REMOVED*** is False
        assert snap["pending_count"***REMOVED*** == 0
        assert snap["conflict_count"***REMOVED*** == 0
        assert snap["quarantine_count"***REMOVED*** == 0
        assert "timestamp_ms" in snap

    def test_running_listener_is_connected(self) -> None:
        coord = _fresh_coordinator()
        coord.attach_listener(_FakeListener(running=True))  # type: ignore[arg-type***REMOVED***
        snap = derive_sync_status(coord)
        assert snap["status"***REMOVED*** == "connected"
        assert snap["listener_running"***REMOVED*** is True

    def test_stopped_listener_is_idle(self) -> None:
        coord = _fresh_coordinator()
        coord.attach_listener(_FakeListener(running=False))  # type: ignore[arg-type***REMOVED***
        snap = derive_sync_status(coord)
        assert snap["status"***REMOVED*** == "idle"

    def test_conflict_beats_connected(self) -> None:
        coord = _fresh_coordinator()
        coord.attach_listener(_FakeListener(running=True))  # type: ignore[arg-type***REMOVED***
        with coord._lock:
            coord._conflict_log["k1"***REMOVED*** = MagicMock()  # type: ignore[attr-defined***REMOVED***
        snap = derive_sync_status(coord)
        assert snap["status"***REMOVED*** == "conflict"
        assert snap["conflict_count"***REMOVED*** == 1

    def test_quarantine_beats_conflict(self) -> None:
        coord = _fresh_coordinator()
        coord.attach_listener(_FakeListener(running=True))  # type: ignore[arg-type***REMOVED***
        with coord._lock:
            coord._conflict_log["k1"***REMOVED*** = MagicMock()  # type: ignore[attr-defined***REMOVED***
            coord._quarantine_buffer.append(MagicMock())  # type: ignore[attr-defined***REMOVED***
        snap = derive_sync_status(coord)
        assert snap["status"***REMOVED*** == "quarantine"
        assert snap["quarantine_count"***REMOVED*** == 1


# ── Active-coordinator registry ─────────────────────────────────────────


class TestActiveCoordinatorRegistry:
    def test_set_get_roundtrip(self) -> None:
        coord = _fresh_coordinator()
        set_active_coordinator(coord)
        try:
            assert get_active_coordinator() is coord
        finally:
            set_active_coordinator(None)

    def test_clear_returns_none(self) -> None:
        set_active_coordinator(None)
        assert get_active_coordinator() is None

    def test_registry_thread_safe(self) -> None:
        """Registry uses a threading.Lock — concurrent set/get must not race."""
        coord = _fresh_coordinator()
        errors: list[Exception***REMOVED*** = [***REMOVED***

        def _writer() -> None:
            try:
                for _ in range(50):
                    set_active_coordinator(coord)
                    set_active_coordinator(None)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=_writer) for _ in range(4)***REMOVED***
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [***REMOVED***


# ── publish_sync_status_event (None-safe per CAN-14) ────────────────────


class TestPublishSyncStatusEvent:
    def test_no_active_coordinator_returns_none(self) -> None:
        set_active_coordinator(None)
        assert publish_sync_status_event() is None

    def test_with_coordinator_never_raises(self) -> None:
        """EventStore may be unavailable in CI → None; never raises."""
        coord = _fresh_coordinator()
        set_active_coordinator(coord)
        try:
            result = publish_sync_status_event()
            assert result is None or isinstance(result, str)
        finally:
            set_active_coordinator(None)


# ── MCP tool handler (`sync_status`) ────────────────────────────────────


class TestMcpSyncStatusTool:
    def test_tool_registered(self) -> None:
        from freebuff_plugin_03.mcp_server import MCPServer

        server = MCPServer()
        names = [t["name"***REMOVED*** for t in server._list_sync_tools()***REMOVED***
        assert "sync_status" in names

    def test_tool_handler_returns_closed_vocab_status(self) -> None:
        from freebuff_plugin_03.mcp_server import MCPServer

        server = MCPServer()
        result = server._call_tool("sync_status", {***REMOVED***)
        assert "content" in result and result["content"***REMOVED***
        payload = json.loads(result["content"***REMOVED***[0***REMOVED***["text"***REMOVED***)
        assert payload["status"***REMOVED*** in ("idle", "connected", "conflict", "quarantine")
        # No active coordinator in test → idle + registered false
        assert payload.get("registered") is False
        assert "recent_events" in payload  # None-safe EventStore read

    def test_unknown_tool_still_errors(self) -> None:
        from freebuff_plugin_03.mcp_server import MCPServer

        server = MCPServer()
        result = server._call_tool("not_a_tool", {***REMOVED***)
        assert result.get("isError") is True
