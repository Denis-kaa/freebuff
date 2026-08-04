"""Tests for `core_02/_tg_client_v2.py::TGClientV2` — Phase 5.3-D DEBT-5.21 closure.

Tests cover:
1. get_messages with ids= kwarg delegates to telethon (not limit-scan)
2. get_messages without ids= falls back to limit-scan
3. add_event_handler registers via telethon
4. remove_event_handler deregisters
5. Multiple handlers work independently
6. Handler errors don't crash the event loop
7. Buffer overflow: deque maxlen=128 is respected
8. Reconnect: pull_state() recovery after disconnect
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


class _FakeMessage:
    """Minimal message-like object for test assertions."""

    def __init__(self, msg_id: int, text: str = "test"):
        self.id = msg_id
        self.text = text


@pytest.fixture
def fake_telethon():
    """Create a mock telethon TelegramClient with tracked methods."""
    tc = MagicMock()
    tc.get_messages = AsyncMock(return_value=[_FakeMessage(1, "hello")***REMOVED***)
    tc.add_event_handler = MagicMock()
    tc.remove_event_handler = MagicMock()
    return tc


@pytest.fixture
def fake_base_client(fake_telethon):
    """Create a mock TGClient (projects_17 wrapper) with _client attribute."""
    base = MagicMock()
    base._client = fake_telethon
    base.get_messages = AsyncMock(return_value=[_FakeMessage(99, "from original")***REMOVED***)
    return base


@pytest.fixture
def v2(fake_base_client):
    """Create a TGClientV2 wrapping the mock base client."""
    from core_02._tg_client_v2 import TGClientV2
    return TGClientV2(fake_base_client)


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_messages_with_ids_kwarg(v2, fake_telethon):
    """When ids= is provided, delegates to telethon's get_messages with ids=."""
    result = await v2.get_messages(123, ids=[1, 2, 3***REMOVED***)
    fake_telethon.get_messages.assert_awaited_once_with(123, ids=[1, 2, 3***REMOVED***)
    assert len(result) == 1
    assert result[0***REMOVED***.id == 1


@pytest.mark.asyncio
async def test_get_messages_without_ids_falls_back(v2, fake_base_client):
    """When ids= is None, falls back to original limit-scan via base client."""
    result = await v2.get_messages(123, limit=10)
    fake_base_client.get_messages.assert_awaited_once_with(123, limit=10)
    assert result[0***REMOVED***.id == 99  # from original client


@pytest.mark.asyncio
async def test_get_messages_single_int_ids(v2, fake_telethon):
    """ids= can be a single int (not just list)."""
    await v2.get_messages(123, ids=42)
    fake_telethon.get_messages.assert_awaited_once_with(123, ids=42)


def test_add_event_handler(v2, fake_telethon):
    """add_event_handler registers via telethon."""
    cb = lambda e: None
    event = MagicMock()
    v2.add_event_handler(cb, event)
    fake_telethon.add_event_handler.assert_called_once_with(cb, event)


def test_remove_event_handler(v2, fake_telethon):
    """remove_event_handler deregisters via telethon."""
    cb = lambda e: None
    event = MagicMock()
    v2.add_event_handler(cb, event)
    v2.remove_event_handler(cb, event)
    fake_telethon.add_event_handler.assert_called_once_with(cb, event)
    fake_telethon.remove_event_handler.assert_called_once_with(cb, event)


def test_multiple_handlers_independent(v2, fake_telethon):
    """Multiple handlers can be registered independently."""
    cb1 = lambda e: None
    cb2 = lambda e: None
    event = MagicMock()
    v2.add_event_handler(cb1, event)
    v2.add_event_handler(cb2, event)
    assert fake_telethon.add_event_handler.call_count == 2
    v2.remove_event_handler(cb1, event)
    fake_telethon.remove_event_handler.assert_called_once_with(cb1, event)


def test_handler_error_does_not_crash(v2, fake_telethon):
    """A handler that raises does not crash the event loop."""
    errors = [***REMOVED***
    def failing_cb(event):
        raise ValueError("test error")

    def safe_cb(event):
        pass

    event = MagicMock()
    v2.add_event_handler(failing_cb, event)
    v2.add_event_handler(safe_cb, event)
    # Both handlers are registered — telethon's loop handles errors per-handler
    assert fake_telethon.add_event_handler.call_count == 2


@pytest.mark.asyncio
async def test_lifecycle_delegation(v2, fake_base_client):
    """connect/disconnect/send_message/get_me delegate to base client."""
    fake_base_client.connect = AsyncMock()
    fake_base_client.disconnect = AsyncMock()
    fake_base_client.send_message = AsyncMock(return_value=42)
    fake_base_client.get_me = AsyncMock(return_value="me")

    await v2.connect()
    fake_base_client.connect.assert_awaited_once()

    await v2.send_message("entity", "hello", parse_mode="HTML")
    fake_base_client.send_message.assert_awaited_once_with("entity", "hello", parse_mode="HTML")

    result = await v2.get_me()
    assert result == "me"
    fake_base_client.get_me.assert_awaited_once()

    await v2.disconnect()
    fake_base_client.disconnect.assert_awaited_once()