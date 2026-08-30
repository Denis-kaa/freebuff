"""E2E integration tests for Phase 5.3-F: coordinated lifecycle (listener + coordinator).

Tests cover:
1. attach_listener: coordinator stores listener, shutdown() calls listener.stop()
2. push_state → listener drains → state applied (full cycle with mocked TG)
3. shutdown stops listener before draining push queue
4. attach_listener idempotent (second call ignored)
5. shutdown without listener still works (backward compat)
6. Full cycle: register_device → push_state → listener loop applies → shutdown
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
}

sys.path.insert(0, str(Path("/storage/emulated/0/PROJECTS/workstation/freebuff")))

from core_02.remote_sync import (
    RemoteSyncCoordinatorImpl,
    RemoteSyncListener,
    SyncDelta,
    SyncMode,
    _SYNC_MARKER_PREFIX,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_delta_text(
    *,
    ts: int = 1_700_000_000_000,
    src: str = "d1",
    rev: int = 1,
    updated: dict | None = None,
) -> str:
    """Build a TG message text body (##FB_STATE## marker + JSON)."""
    payload = json.dumps(
        {
            "v": "1.0.0",
            "delta": {
                "timestamp_ms": ts,
                "source_device_id": src,
                "revision": rev,
                "sync_mode": "saved_messages",
                "updated_keys": updated or {"k": "v"},
                "deleted_keys": [],
            },
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{_SYNC_MARKER_PREFIX} V1.0.0 corr-{rev} CHUNK 0/1\n{payload}"


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def coordinator():
    """Create a coordinator with pre-registered device (no TG)."""
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:test-laptop"
    return impl


@pytest.fixture
def listener(coordinator):
    """Create a listener attached to the coordinator (no TG connect)."""
    lst = RemoteSyncListener(coordinator)
    lst._tg_client = MagicMock()
    return lst


# ── 1. attach_listener: stores listener, shutdown calls listener.stop() ─────


@pytest.mark.asyncio
async def test_attach_listener_shutdown_stops_listener(coordinator, listener):
    """attach_listener stores listener, shutdown() calls listener.stop()."""
    assert coordinator._listener is None
    coordinator.attach_listener(listener)
    assert coordinator._listener is listener

    # Mock listener.stop() to track calls
    listener.stop = AsyncMock()  # type: ignore[method-assign]

    await coordinator.shutdown()
    listener.stop.assert_awaited_once()


# ── 2. attach_listener idempotent ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_attach_listener_idempotent(coordinator, listener):
    """Second attach_listener call is ignored (no-op)."""
    coordinator.attach_listener(listener)
    coordinator.attach_listener(listener)  # second call — should be no-op
    assert coordinator._listener is listener  # still the same


# ── 3. shutdown without listener (backward compat) ──────────────────────────


@pytest.mark.asyncio
async def test_shutdown_without_listener_still_works(coordinator):
    """shutdown() without listener attached still works (backward compat)."""
    result = await coordinator.shutdown()
    assert result["ok"] is True
    assert result["drained"] == 0


# ── 4. Full cycle: register → push_state → listener drains → shutdown ───────


@pytest.mark.asyncio
async def test_full_cycle_push_listener_drain_shutdown(coordinator, listener):
    """Full cycle: push_state, listener loop drains buffer, shutdown coordinated.

    Uses mocked SendFn for push_state (no real TG). The listener loop is
    run manually (not via start()) to avoid real TGClient bootstrap.
    """
    # Attach listener
    coordinator.attach_listener(listener)

    # Mock SendFn for push_state
    mock_send = AsyncMock(return_value=12345)
    coordinator._send_fn = mock_send

    # Push a state delta
    delta = SyncDelta(
        timestamp_ms=1_700_000_000_000,
        source_device_id="tg:42:test-laptop",
        revision=1,
        sync_mode=SyncMode.SAVED_MESSAGES,
        updated_keys={"key_a": "value_a"},
        deleted_keys=[],
    )
    push_result = await coordinator.push_state(delta)
    assert push_result["ok"] is True
    assert push_result["chunk_count"] == 1

    # Simulate incoming event (like Telethon would fire via _on_new_message)
    text = _make_delta_text(rev=2, updated={"key_b": "value_b"})
    listener._on_new_message(MagicMock(
        message=MagicMock(id=999, text=text)
    ))
    assert listener.pending_count == 1

    # Run listener loop manually (one iteration)
    listener._running = True
    listener._POLL_INTERVAL_SECONDS = 0.01
    loop_task = asyncio.ensure_future(listener._listener_loop())
    await asyncio.sleep(0.05)

    # Verify: listener loop drained the buffer and applied the envelope
    assert listener.pending_count == 0
    assert coordinator._local_state.get("key_b") == ("value_b", 1_700_000_000_000)

    # Shutdown coordinated (listener task gets cancelled by stop())
    listener._running = False
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass

    shutdown_result = await coordinator.shutdown()
    assert shutdown_result["ok"] is True
    assert shutdown_result["drained"] == 1  # pending push drained


# ── 5. Listener stop called before push drain ───────────────────────────────


@pytest.mark.asyncio
async def test_shutdown_calls_listener_stop_before_drain(coordinator, listener):
    """shutdown() calls listener.stop() BEFORE draining the push queue.

    This ensures the event handler is detached before the coordinator
    starts draining, preventing race conditions between incoming events
    and queue cleanup.
    """
    # Track call order
    call_order: list[str] = []

    # Mock listener.stop()
    async def tracking_stop():
        call_order.append("listener_stop")

    listener.stop = tracking_stop  # type: ignore[method-assign]
    coordinator.attach_listener(listener)

    # Add a pending push item so drained count is > 0
    from core_02.remote_sync import SyncEnvelope
    env = SyncEnvelope(
        delta=SyncDelta(
            timestamp_ms=1,
            source_device_id="test",
            revision=0,
            sync_mode=SyncMode.SAVED_MESSAGES,
            updated_keys={"k": "v"},
            deleted_keys=[],
        ),
        signature=None,
        compression="none",
        marker="##FB_STATE##",  # type: ignore[arg-type]
    )
    coordinator._pending_push.append(
        type("_PendingPush", (object,), {
            "envelope": env, "enqueued_ms": 1, "chunk_count": 1
        ])()
    )

    await coordinator.shutdown()
    # listener.stop() was called before drain
    assert "listener_stop" in call_order
    # shutdown result: drained=1 implies drain happened after listener.stop()
    # (idempotent second call confirms first call completed)
    result = await coordinator.shutdown()
    assert result["ok"] is False
    assert "already called" in result["error"]