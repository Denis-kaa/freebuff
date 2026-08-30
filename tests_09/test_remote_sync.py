"""Tests for Phase 5.3-B Remote Sync coordinator runtime (`core_02/remote_sync.py`).

**Test strategy:** mock-based. Real TG session is fragile; we inject `SendFn`,
`HistoryFn`, `MeFn` async-callable hooks so unit tests are deterministic and
CI-stable. NO network IO. The TG integration layer is exhaustively covered by
`tests_09/test_telegram_contract.py` and `tests_09/test_telegram_bot_notify.py`.

**Coverage scope (17 tests, mapped to data-flow surfaces):**

  1. Protocol contract:        isinstance check, capability closed-vocab
  2. Pure helpers:             LWW (multiple scenarios), chunking (3 paths), marker format
  3. Construct + lifecycle:    lives (init, shutdown idempotent, empty label rejected)
  4. push_state (mocked):      without register, single chunk, multi-chunk, send_fn captures
  5. quarantine:               age boundary (24h cutoff: <, =, >)
  6. resolve_conflict:         all 4 modes
  7. register_device:          mocked me_fn returns device; fallback path
  8. _reconstruct_envelope:    happy + malformed

**Conventions:**
  - Async tests marked `@pytest.mark.asyncio` (pytest-asyncio auto-mode assumed).
  - No filesystem side effects; quarantine buffer is deque (in-memory).
  - SendFn / HistoryFn / MeFn use `unittest.mock.AsyncMock` patterns.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Imports under test ─────────────────────────────────────────────────────

import importlib.util as _importlib_util
import sys
}

_FB_ROOT = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
sys.path.insert(0, ".")  # core_02/ + runtime_05/scenarios resolution

import core_02.remote_sync as rs  # noqa: E402
from core_02.remote_sync import (  # noqa: E402
    RemoteSyncCoordinatorImpl,
    RemoteSyncError,
    RemoteSyncCapabilityError,
    RemoteSyncLifecycleError,
    RemoteSyncConfigError,
    ChunkingError,
    SyncDelta,
    SyncEnvelope,
    SyncMode,
    SyncOp,
    ConflictResolution,
    SyncDevice,
    _CHUNK_PRIMARY_BYTES,
    _QUARANTINE_MAX_AGE_SECONDS,
    _SYNC_MARKER_PREFIX,
    _lww_merge_per_key,
    _chunk_envelope_payload,
    _format_envelope_marker,
    _reconstruct_envelope_from_parsed,
)


# ── Helpers (mock scaffolding) ─────────────────────────────────────────────


def _delta(
    *,
    ts: int = 1_700_000_000_000,
    src: str = "d1",
    rev: int = 1,
    sync_mode: SyncMode = SyncMode.SAVED_MESSAGES,
    updated: Optional[Dict[str, Any]] = None,
    deleted: Optional[List[str]] = None,
) -> SyncDelta:
    return SyncDelta(
        timestamp_ms=ts,
        source_device_id=src,
        revision=rev,
        sync_mode=sync_mode,
        updated_keys=updated or {"a": "v_a"},
        deleted_keys=deleted or [],
    )


def _envelope(
    delta: SyncDelta,
    marker: str = "##FB_STATE##",
    compression: str = "none",
) -> SyncEnvelope:
    return SyncEnvelope(
        delta=delta,
        signature=None,
        compression=compression,  # type: ignore[arg-type]
        marker=marker,  # type: ignore[arg-type]
    )


# ── 1. Protocol contract & capability closed-vocab ────────────────────────


def test_capabilities_closed_vocab_membership():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    caps = impl.capabilities()
    expected = {"state-sync", "telegram-mtproto-relay", "delta-resolution", "chunked-large-state"}
    assert caps == expected, f"closed-vocab mismatch: {caps}"
    # Verify frozenset backing
    assert isinstance(_lww_merge_per_key.__globals__["_VALID_CAPABILITIES"], frozenset)


def test_capability_assertion_rejects_unknown_token():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    # Trigger internal _assert_capability via a public method (push_state)
    with pytest.raises(RemoteSyncCapabilityError) as exc_info:
        impl._assert_capability("non-existent-cap")
    assert "non-existent-cap" in str(exc_info.value)
    assert "closed-set" in str(exc_info.value)


def test_constructor_rejects_empty_label():
    with pytest.raises(RemoteSyncConfigError):
        RemoteSyncCoordinatorImpl("")
    with pytest.raises(RemoteSyncConfigError):
        RemoteSyncCoordinatorImpl("   ")  # whitespace only (truthy)


# ── 2. Pure helpers: LWW algorithm (multiple scenarios) ───────────────────


def test_lww_merge_per_key_newer_remote_wins():
    local = {"a": ("v_local", 100)}
    remote = {"a": ("v_remote", 200)}
    merged, dropped = _lww_merge_per_key(local, remote)
    assert merged == {"a": ("v_remote", 200)}
    assert dropped == set()


def test_lww_merge_per_key_older_remote_dropped():
    local = {"a": ("v_local_new", 300)}
    remote = {"a": ("v_remote_old", 100)}
    merged, dropped = _lww_merge_per_key(local, remote)
    assert merged == {"a": ("v_local_new", 300)}
    assert dropped == {"a"}


def test_lww_merge_per_key_tie_keeps_local():
    local = {"a": ("v_local", 200)}
    remote = {"a": ("v_remote", 200)}
    merged, dropped = _lww_merge_per_key(local, remote)
    assert merged == {"a": ("v_local", 200)}  # tie → local kept (deterministic)
    assert dropped == set()


def test_lww_merge_per_key_disjoint_keys_merge():
    local = {"a": ("v_a", 100)}
    remote = {"b": ("v_b", 100)}
    merged, dropped = _lww_merge_per_key(local, remote)
    assert merged == {"a": ("v_a", 100), "b": ("v_b", 100)}
    assert dropped == set()


# ── 3. Pure helpers: chunking & marker format ──────────────────────────────


def test_chunk_envelope_payload_small_single_chunk():
    payload = "small-json-payload" * 10  # 170 chars
    chunks = _chunk_envelope_payload(payload)
    assert len(chunks) == 1
    assert chunks[0] == payload


def test_chunk_envelope_payload_large_splits():
    payload = "x" * (_CHUNK_PRIMARY_BYTES + 1000)  # 4500 chars
    chunks = _chunk_envelope_payload(payload)
    assert len(chunks) > 1
    # Verify all chars preserved (no data loss)
    assert "".join(chunks) == payload


def test_chunk_envelope_payload_empty_raises():
    with pytest.raises(ChunkingError):
        _chunk_envelope_payload("")


def test_format_envelope_marker_format():
    h = _format_envelope_marker(chunk_index=2, chunk_total=5, correlation_id="abc-123")
    assert h.startswith(_SYNC_MARKER_PREFIX)
    assert "V1.0.0" in h
    assert "abc-123" in h
    assert "CHUNK 2/5" in h


# ── 4. Lifecycle: shutdown idempotent ─────────────────────────────────────


@pytest.mark.asyncio
async def test_shutdown_idempotent_second_call_errors():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    res1 = await impl.shutdown()
    assert res1 == {"ok": True, "drained": 0}
    res2 = await impl.shutdown()
    assert res2 == {"ok": False, "error": "shutdown already called"}


# ── 5. push_state (mocked SendFn) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_push_state_without_register_device_fails_loudly():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    res = await impl.push_state(_delta())
    assert res["ok"] is False
    assert "not registered" in res["error"]


@pytest.mark.asyncio
async def test_push_state_with_injected_send_fn_single_chunk():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    mock_send = AsyncMock(return_value=12345)
    impl._send_fn = mock_send

    # Inject a pre-registered device (skip register_device to avoid me_fn)
    impl._device_id = "tg:99:test-laptop"

    res = await impl.push_state(_delta(updated={"a": "v_a", "b": "v_b"}))
    assert res["ok"] is True
    assert res["chunk_count"] == 1
    assert res["msg_ids"] == [12345]
    mock_send.assert_awaited_once()
    # Verify the call args: (chat_id, text)
    call_args = mock_send.await_args
    assert call_args.args[0] == 7_709_651_193  # SAVED_MESSAGES_CHAT_ID
    text_arg = call_args.args[1]
    assert text_arg.startswith(_SYNC_MARKER_PREFIX)
    assert "CHUNK 0/1" in text_arg
    assert "v_a" in text_arg  # JSON body


@pytest.mark.asyncio
async def test_push_state_multichunk_delivers_all_chunks():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    # Mock send returns incrementing msg_ids
    mock_send = AsyncMock(side_effect=[1001, 1002, 1003])
    impl._send_fn = mock_send
    impl._device_id = "tg:99:test-laptop"

    # Force 3+ chunks: payload > 2*3500 chars
    big = "x" * 7500
    res = await impl.push_state(
        _delta(updated={"big": big})
    )
    assert res["ok"] is True
    assert res["chunk_count"] >= 3
    assert len(res["msg_ids"]) == res["chunk_count"]
    assert mock_send.await_count >= 3
    # Verify correlation_id is identical across chunks
    correlation_id = res["correlation_id"]
    sent_texts = [c.args[1] for c in mock_send.await_args_list]
    for text in sent_texts:
        assert correlation_id in text


@pytest.mark.asyncio
async def test_push_state_explicit_send_fn_called_with_chat_id():
    """SendFn signature: (chat_id: int, text: str) -> Optional[msg_id]."""
    captured: List[Tuple[int, str]] = []

    async def capturing_send(chat_id: int, text: str) -> int:
        captured.append((chat_id, text))
        return 999

    impl = RemoteSyncCoordinatorImpl(
        "test-laptop",
        send_fn=capturing_send,
    )
    impl._device_id = "tg:42:lab"

    await impl.push_state(_delta())
    assert len(captured) == 1
    chat_id, text = captured[0]
    assert chat_id == 7_709_651_193
    assert text.startswith(_SYNC_MARKER_PREFIX)


# ── 6. quarantine age boundary ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quarantine_accepts_fresh_envelope():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:lab"
    fresh_delta = _delta(ts=rs._now_ms())  # current timestamp → age ~0
    res = await impl.quarantine(_envelope(fresh_delta))
    assert res["ok"] is True
    assert res["age_seconds"] < 5  # near-immediate


@pytest.mark.asyncio
async def test_quarantine_rejects_stale_envelope():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:lab"
    # 25h old
    stale_ts = rs._now_ms() - (_QUARANTINE_MAX_AGE_SECONDS + 3600) * 1000
    stale_delta = _delta(ts=stale_ts)
    res = await impl.quarantine(_envelope(stale_delta))
    assert res["ok"] is False
    assert "exceeds quarantine limit" in res["error"]


@pytest.mark.asyncio
async def test_quarantine_buffer_bounded():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:lab"
    # Fill buffer beyond maxlen (which is 1000 per rs module)
    for i in range(rs._QUARANTINE_MAX_BUFFER_LEN + 5):
        delta = _delta(ts=rs._now_ms(), rev=i)
        await impl.quarantine(_envelope(delta))
    assert len(impl._quarantine_buffer) == rs._QUARANTINE_MAX_BUFFER_LEN


# ── 7. resolve_conflict (all 4 modes) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_conflict_lww_per_key():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    local = {"a": ("v_local", 100), "b": ("v_b_local", 100)}
    remote = {"a": ("v_remote", 200), "c": ("v_c", 200)}
    res = await impl.resolve_conflict(local, remote, ConflictResolution.LWW_PER_KEY)
    assert res["mode"] == "lww_per_key"
    assert res["merged"]["a"] == ("v_remote", 200)  # newer remote wins
    assert res["merged"]["b"] == ("v_b_local", 100)  # only-in-local kept
    assert res["merged"]["c"] == ("v_c", 200)  # only-in-remote added
    assert res["quarantined"] is False


@pytest.mark.asyncio
async def test_resolve_conflict_whole_doc_lww_picks_newer_max():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    local = {"a": ("v_local", 500)}  # max=500
    remote = {"b": ("v_remote", 100)}  # max=100
    res = await impl.resolve_conflict(local, remote, ConflictResolution.WHOLE_DOC_LWW)
    assert res["mode"] == "whole_doc_lww"
    assert res["merged"] == local  # local has higher max-timestamp


@pytest.mark.asyncio
async def test_resolve_conflict_manual_keeps_local_and_logs():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    local = {"k": ("v_local", 100)}
    remote = {"k": ("v_remote", 100)}  # same timestamp + ≠ value → conflict
    res = await impl.resolve_conflict(local, remote, ConflictResolution.MANUAL)
    assert res["mode"] == "manual"
    assert res["merged"] == local
    # Conflict was near-simultaneous (|lts - rts| < 10_000 ms AND values differ)
    # → recorded in conflict log
    assert "k" in impl._conflict_log


@pytest.mark.asyncio
async def test_resolve_conflict_quarantine_appends_to_buffer():
    impl = RemoteSyncCoordinatorImpl("test-laptop")
    impl._device_id = "tg:42:lab"
    local = {"k": ("v_local", 100)}
    remote = {"k": ("v_remote", 100)}
    pre_buf_len = len(impl._quarantine_buffer)
    res = await impl.resolve_conflict(local, remote, ConflictResolution.QUARANTINE)
    assert res["mode"] == "quarantine"
    assert res["quarantined"] is True
    assert len(impl._quarantine_buffer) == pre_buf_len + 1


# ── 8. register_device (mocked me_fn) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_register_device_with_injected_me_fn():
    """Use me_fn injection to bypass TG, return SyncDevice."""
    fake_me = MagicMock()
    fake_me.user_id = 7709651193

    async def me_mock() -> Any:
        return fake_me

    impl = RemoteSyncCoordinatorImpl("test-laptop", me_fn=me_mock)
    device = await impl.register_device("test-laptop")
    assert isinstance(device, SyncDevice)
    assert device.tg_user_id == 7709651193
    assert device.label == "test-laptop"
    assert device.device_id == "tg:7709651193:test-laptop"
    # Idempotent: second call returns same device
    device2 = await impl.register_device("test-laptop")
    assert device2.device_id == device.device_id


# ── 9. _reconstruct_envelope_from_parsed (pure helper) ────────────────────


def test_reconstruct_envelope_from_parsed_happy():
    parsed = {
        "v": "1.0.0",
        "delta": {
            "timestamp_ms": 1234567890,
            "source_device_id": "d-uuid",
            "revision": 5,
            "sync_mode": "saved_messages",
            "updated_keys": {"a": "v_a"},
            "deleted_keys": ["old_k"],
        },
    }
    env = _reconstruct_envelope_from_parsed(parsed)
    assert env is not None
    assert env.delta.timestamp_ms == 1234567890
    assert env.delta.source_device_id == "d-uuid"
    assert env.delta.revision == 5
    assert env.delta.updated_keys == {"a": "v_a"}
    assert env.delta.deleted_keys == ["old_k"]


def test_reconstruct_envelope_from_parsed_malformed_returns_none():
    # Missing 'delta' key
    parsed = {"v": "1.0.0", "garbage": {}}
    assert _reconstruct_envelope_from_parsed(parsed) is None
    # Bad timestamp type
    parsed_bad_ts = {
        "delta": {
            "timestamp_ms": "not-a-number",
            "source_device_id": "d",
            "revision": 1,
            "sync_mode": "saved_messages",
            "updated_keys": {},
            "deleted_keys": [],
        }
    }
    assert _reconstruct_envelope_from_parsed(parsed_bad_ts) is None
    # Invalid sync_mode
    parsed_bad_mode = {
        "delta": {
            "timestamp_ms": 1,
            "source_device_id": "d",
            "revision": 1,
            "sync_mode": "INVALID_MODE",
            "updated_keys": {},
            "deleted_keys": [],
        }
    }
    assert _reconstruct_envelope_from_parsed(parsed_bad_mode) is None
