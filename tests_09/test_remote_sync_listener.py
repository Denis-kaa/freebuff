"""Tests for Phase 5.3-E persistent listener loop (`RemoteSyncListener._listener_loop`).

Tests cover:
1. Lifecycle: start() creates asyncio.Task, is_running=True, stop() cancels task
2. Event dispatch: _on_new_message pushes into buffer, drain_incoming drains
3. Listener loop: drain_incoming → _apply_remote_envelope → pull_state cycle
4. Reconnect recovery: pull_state() called on each loop cycle (missed history)
5. Buffer overflow: deque maxlen=128 is respected (no crash on overflow)
6. LWW resolve: envelopes applied through coordinator's LWW merge
7. Stop idempotent: stop() called twice doesn't error
8. Malformed envelope: loop continues on JSON decode error (resilience)
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Imports under test ─────────────────────────────────────────────────────

import sys
from pathlib import Path

sys.path.insert(0, str(Path("/storage/emulated/0/PROJECTS/workstation/freebuff")))

import core_02.remote_sync as rs
from core_02.remote_sync import (
    RemoteSyncCoordinatorImpl,
    RemoteSyncListener,
    SyncDelta,
    SyncEnvelope,
    SyncMode,
    _SYNC_MARKER_PREFIX,
    _reconstruct_envelope_from_parsed,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_delta(
    *,
    ts: int = 1_700_000_000_000,
    src: str = "d1",
    rev: int = 1,
    updated: dict | None = None,
    deleted: list | None = None,
) -> SyncDelta:
    return SyncDelta(
        timestamp_ms=ts,
        source_device_id=src,
        revision=rev,
        sync_mode=SyncMode.SAVED_MESSAGES,
        updated_keys=updated or {"a": "v_a"},
        deleted_keys=deleted or [],
    )


def _make_envelope_text(delta: SyncDelta) -> str:
    """Build a TG message text body that looks like a real ##FB_STATE## message."""
    payload = json.dumps(
        {
            "v": "1.0.0",
            "delta": {
                "timestamp_ms": delta.timestamp_ms,
                "source_device_id": delta.source_device_id,
                "revision": delta.revision,
                "sync_mode": delta.sync_mode.value,
                "updated_keys": delta.updated_keys,
                "deleted_keys": list(delta.deleted_keys),
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{_SYNC_MARKER_PREFIX} V1.0.0 corr-{delta.revision} CHUNK 0/1\n{payload}"


class _FakeEvent:
    """Minimal telethon-like event for testing _on_new_message."""

    def __init__(self, msg_id: int, text: str):
        self.message = MagicMock()
        self.message.id = msg_id
        self.message.text = text


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def coordinator():
    """Create a coordinator with test-friendly defaults (no TG)."""
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:test-laptop"
    return impl


@pytest.fixture
def listener(coordinator):
    """Create a RemoteSyncListener with injected coordinator (no TG connect)."""
    lst = RemoteSyncListener(coordinator)
    # Patch _tg_client to avoid real TG connect
    lst._tg_client = MagicMock()
    lst._tg_client.remove_event_handler = MagicMock()
    return lst


# ── 1. Lifecycle: start/stop ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listener_start_creates_task(listener):
    """start() sets is_running=True and creates a listener task."""
    # Patch the heavy deps that start() imports
    with patch(
        "core_02.telegram_contract._get_tg_client_factory",
        return_value=lambda: AsyncMock(),
    ), patch(
        "core_02._tg_client_v2.TGClientV2",
        lambda base: base,
    ), patch("telethon.events.NewMessage") as mock_event:
        mock_event.return_value = MagicMock()
        result = await listener.start()
        assert result is True
        assert listener.is_running is True
        assert listener._listener_task is not None
        assert not listener._listener_task.done()
        # Cleanup
        await listener.stop()


@pytest.mark.asyncio
async def test_listener_stop_cancels_task(listener):
    """stop() cancels the listener task and clears the buffer."""
    # Manually set running + create a dummy task
    listener._running = True
    listener._incoming_buffer.append((1, b"test"))

    async def dummy_loop():
        try:
            await asyncio.sleep(999)
        except asyncio.CancelledError:
            raise

    listener._listener_task = asyncio.ensure_future(dummy_loop())
    await asyncio.sleep(0.01)  # let the task start

    await listener.stop()
    assert listener.is_running is False
    assert listener._listener_task is None
    assert listener.pending_count == 0


@pytest.mark.asyncio
async def test_listener_stop_idempotent(listener):
    """Second stop() call does not error."""
    listener._running = True
    listener._listener_task = None  # already stopped
    await listener.stop()  # first
    await listener.stop()  # second — should not raise


# ── 2. Event dispatch: _on_new_message → buffer → drain_incoming ────────────


def test_on_new_message_pushes_to_buffer(listener):
    """_on_new_message pushes (msg_id, bytes) into _incoming_buffer."""
    listener._running = True
    text = _make_envelope_text(_make_delta(rev=1))
    event = _FakeEvent(msg_id=42, text=text)
    listener._on_new_message(event)
    assert listener.pending_count == 1
    msg_id, envelope_bytes = listener._incoming_buffer[0]
    assert msg_id == 42
    assert text.encode("utf-8") == envelope_bytes


def test_on_new_message_ignores_non_marker(listener):
    """Messages without ##FB_STATE## marker are ignored."""
    listener._running = True
    event = _FakeEvent(msg_id=99, text="regular chat message")
    listener._on_new_message(event)
    assert listener.pending_count == 0


def test_drain_incoming_returns_all_and_clears(listener):
    """drain_incoming() returns all buffered items and empties the buffer."""
    listener._running = True
    listener._incoming_buffer.append((1, b"a"))
    listener._incoming_buffer.append((2, b"b"))
    listener._incoming_buffer.append((3, b"c"))
    drained = listener.drain_incoming()
    assert len(drained) == 3
    assert listener.pending_count == 0
    assert drained[0] == (1, b"a")
    assert drained[1] == (2, b"b")
    assert drained[2] == (3, b"c")


def test_drain_incoming_returns_empty_when_not_running(listener):
    """drain_incoming() returns [] when not running."""
    listener._running = False
    listener._incoming_buffer.append((1, b"x"))
    drained = listener.drain_incoming()
    assert drained == []


# ── 3. Listener loop: drain → apply → pull_state cycle ──────────────────────


@pytest.mark.asyncio
async def test_listener_loop_drains_and_applies(coordinator):
    """Listener loop drains buffer, applies envelopes, and calls pull_state."""
    listener = RemoteSyncListener(coordinator)
    listener._running = True
    listener._tg_client = MagicMock()

    # Seed the buffer with a real envelope
    delta = _make_delta(rev=1, updated={"key1": "val1"})
    text = _make_envelope_text(delta)
    listener._incoming_buffer.append((100, text.encode("utf-8")))

    # Patch pull_state to track calls
    original_pull = coordinator.pull_state
    pull_called = False

    async def tracking_pull():
        nonlocal pull_called
        pull_called = True
        return None

    coordinator.pull_state = tracking_pull  # type: ignore[assignment]

    # Run one loop iteration (short poll interval)
    listener._POLL_INTERVAL_SECONDS = 0.01
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.05)

    # Verify: envelope was applied to coordinator
    assert coordinator._local_state.get("key1") == ("val1", delta.timestamp_ms)
    assert pull_called is True

    # Cleanup
    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


# ── 4. Reconnect recovery: pull_state on each cycle ─────────────────────────


@pytest.mark.asyncio
async def test_listener_loop_calls_pull_state_when_buffer_non_empty(coordinator):
    """pull_state() is called when buffer was non-empty (reconnect guard)."""
    listener = RemoteSyncListener(coordinator)
    listener._running = True
    listener._tg_client = MagicMock()

    call_count = 0

    async def counting_pull():
        nonlocal call_count
        call_count += 1
        return None

    coordinator.pull_state = counting_pull  # type: ignore[assignment]

    # Seed the buffer so the loop calls pull_state
    # Use a real envelope text (not raw bytes with .encode() on a b-prefix string)
    text = "##FB_STATE## V1.0.0 test CHUNK 0/1\n" + '{"v":"1.0.0","delta":{"timestamp_ms":100,"source_device_id":"d1","revision":1,"sync_mode":"saved_messages","updated_keys":{"k":"v"],"deleted_keys":[]]]'
    listener._incoming_buffer.append((1, text.encode("utf-8")))

    listener._POLL_INTERVAL_SECONDS = 0.02
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.07)

    assert call_count >= 1  # pull_state called because buffer was non-empty

    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_listener_loop_skips_pull_state_when_buffer_empty(coordinator):
    """pull_state() is NOT called when buffer is empty."""
    listener = RemoteSyncListener(coordinator)
    listener._running = True
    listener._tg_client = MagicMock()

    call_count = 0

    async def counting_pull():
        nonlocal call_count
        call_count += 1
        return None

    coordinator.pull_state = counting_pull  # type: ignore[assignment]

    listener._POLL_INTERVAL_SECONDS = 0.02
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.07)

    assert call_count == 0  # pull_state NOT called (buffer was empty)

    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


# ── 5. Buffer overflow: deque maxlen=128 ────────────────────────────────────


def test_buffer_overflow_respected(listener):
    """deque maxlen=128 prevents unbounded growth on overflow."""
    listener._running = True
    for i in range(200):
        listener._incoming_buffer.append((i, b"x"))
    assert listener.pending_count == 128  # maxlen respected
    # Oldest entries evicted
    oldest_id, _ = listener._incoming_buffer[0]
    assert oldest_id == 200 - 128  # 72 (first 72 evicted)


# ── 6. Malformed envelope resilience ────────────────────────────────────────


@pytest.mark.asyncio
async def test_listener_loop_continues_on_malformed_envelope(coordinator):
    """Listener loop continues after a malformed envelope (JSON decode error)."""
    listener = RemoteSyncListener(coordinator)
    listener._running = True
    listener._tg_client = MagicMock()

    # Seed buffer with a malformed entry (not valid JSON)
    listener._incoming_buffer.append((999, b"not-json-at-all"))

    # Also seed a valid one that should be processed
    delta = _make_delta(rev=2, updated={"good": "data"})
    text = _make_envelope_text(delta)
    listener._incoming_buffer.append((1000, text.encode("utf-8")))

    call_count = 0

    async def counting_pull():
        nonlocal call_count
        call_count += 1
        return None

    coordinator.pull_state = counting_pull  # type: ignore[assignment]

    listener._POLL_INTERVAL_SECONDS = 0.01
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.05)

    # Verify: good envelope was applied despite malformed one
    assert coordinator._local_state.get("good") == ("data", delta.timestamp_ms)
    assert call_count >= 1

    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


# ── 7. LWW resolve: envelopes applied through coordinator LWW merge ─────────


@pytest.mark.asyncio
async def test_listener_loop_lww_resolve_newer_wins(coordinator):
    """When two envelopes conflict, newer timestamp wins (LWW)."""
    listener = RemoteSyncListener(coordinator)
    listener._running = True
    listener._tg_client = MagicMock()

    # Seed coordinator with old value
    coordinator._local_state["key_x"] = ("old_value", 100)

    # Newer envelope arrives
    newer_delta = _make_delta(ts=200, rev=3, updated={"key_x": "new_value"})
    text = _make_envelope_text(newer_delta)
    listener._incoming_buffer.append((200, text.encode("utf-8")))

    async def noop_pull():
        return None

    coordinator.pull_state = noop_pull  # type: ignore[assignment]

    listener._POLL_INTERVAL_SECONDS = 0.01
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.05)

    # LWW: newer (200) > older (100) → new_value wins
    assert coordinator._local_state["key_x"] == ("new_value", 200)

    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass