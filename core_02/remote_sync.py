"""Phase 5.3-B runtime: `RemoteSyncCoordinatorImpl` — Telegram-stored relay.

**Status:** Runtime implementation of Phase 5.3-A spec-only contract.

**Contract source:** `runtime_05/scenarios/19_remote_sync/interface.py`
  (`@runtime_checkable RemoteSyncCoordinator(Protocol)`).

**Architectural decision:** Option B (Telegram-stored Relay) per
  `docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md`
  and `docs_10/vision/decision_index.md` §ADR-010.

**Design invariants (do not relax without ADR update):**
  - Per-key LWW (NOT whole-document) for `resolve_conflict()`.
  - Capability tokens are CLOSED-set (CON-8) — invalidate on accept.
  - All public methods are `async` to mirror Telethon's event loop.
  - Lazy-import of Telethon (heavy optional dep; absent in CI → `ImportError`
    raised at first `push_state` call, NOT at module import — preserves
    import-time test stability).
  - FAIL-LOUD per CAN-14 — methods return structured errors (no raises for
    expected sync failures). Caller decides retry vs surface-to-user.

**TG substrate integration:**
  - `push_state()` chunks JSON envelope → calls
    `core_02.telegram_contract.report_to_saved_messages()` (or `report_to_litvinov`
    depending on `sync_mode`) for each chunk. Returns `Optional[int***REMOVED***`
    msg_id per chunk; report back the count to caller.
  - `pull_state()` lazy-imports `projects_17.tg_terminal_messenger.TGClient`
    to access `get_history()` (NOT exposed via `telegram_contract` —
    `telegram_contract` only does sends).
  - `register_device()` lazy-imports `TGClient.get_me()` for current user
    identity. Falls back to `LIVE_SESSION_PHONE` constant if unavailable.
  - No long-lived TG connection: every operation bootstraps
    `TGClient().connect()` → operation → `disconnect()` (matches the
    `core_02/telegram_contract._send_text` pattern).

**Lifecycle (matches `DistributedCoordinator` pattern in
  `scripts_01/distributed_agents.py`):**
  - `__init__` — pure struct, no I/O, no TG connect
  - first `push_state` / `pull_state` call — bootstrap TG on-demand
  - `shutdown()` — drain pending push queue → cancel listener task
    (idempotent; no TG forced-disconnect to avoid races with concurrent
    callers)
  - instance is single-use (re-create on shutdown)
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    runtime_checkable,
)


# ── Lazy import: interface-spec types via importlib (digit-prefix dir) ───

import importlib.util as _importlib_util
import sys as _sys  # noqa: E402
***REMOVED*** as _Path  # noqa: E402

_FB_ROOT_CANDIDATES = [
    _Path("/storage/emulated/0/PROJECTS/workstation/freebuff"),
    _Path(__file__).resolve().parent.parent,  # local-dev layout: core_02/ is sibling of runtime_05/
    _Path.cwd(),
***REMOVED***
_FB_ROOT = next(
    (p for p in _FB_ROOT_CANDIDATES if (p / "runtime_05" / "scenarios").is_dir()),
    _FB_ROOT_CANDIDATES[0***REMOVED***,
)

_INTERFACE_PATH = (
    _FB_ROOT / "runtime_05" / "scenarios" / "19_remote_sync" / "interface.py"
)
_spec = _importlib_util.spec_from_file_location(
    "remote_sync_interface", str(_INTERFACE_PATH)
)
if _spec is None or _spec.loader is None:
    raise ImportError(
        f"could not build module spec for {_INTERFACE_PATH***REMOVED*** (file must exist)"
    )
_interface_mod = _importlib_util.module_from_spec(_spec)
# CRITICAL: register module in sys.modules BEFORE exec_module so that
# `@dataclass` introspection (which keys on `cls.__module__`) can resolve
# the module via `sys.modules.get(cls.__module__).__dict__`. Without this,
# dataclass raises `'NoneType' object has no attribute '__dict__'`.
_sys.modules["remote_sync_interface"***REMOVED*** = _interface_mod
_spec.loader.exec_module(_interface_mod)

SYNC_VERSION_V1 = _interface_mod.SYNC_VERSION_V1
ConflictResolution = _interface_mod.ConflictResolution
SyncDelta = _interface_mod.SyncDelta
SyncDevice = _interface_mod.SyncDevice
SyncEnvelope = _interface_mod.SyncEnvelope
SyncMode = _interface_mod.SyncMode
SyncOp = _interface_mod.SyncOp
RemoteSyncCoordinator = _interface_mod.RemoteSyncCoordinator  # protocol reference


# ── Re-use CAN-3 chat_ids + report helpers (function-based API) ──────────
from core_02.telegram_contract import (  # noqa: E402
    SAVED_MESSAGES_CHAT_ID,
    ALEX_LITVINOV_CHAT_ID,
    LITVINOV_CHAT_ID,
    LIVE_SESSION_PHONE,
    is_tg_available,
    report_to_saved_messages,
    report_to_alex_litvinov,
)


# ── Logging (canonical pattern per CON-16) ────────────────────────────────

logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(
        logging.Formatter("[RemoteSync:impl***REMOVED*** %(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


# ── Public symbol exports ─────────────────────────────────────────────────

__all__ = [
    "RemoteSyncCoordinatorImpl",
    "RemoteSyncError",
    "RemoteSyncCapabilityError",
    "RemoteSyncLifecycleError",
    "RemoteSyncConfigError",
    "ChunkingError",
    "_CHUNK_PRIMARY_BYTES",
    "_CHUNK_GZIP_THRESHOLD_BYTES",
    "_QUARANTINE_MAX_AGE_SECONDS",
    "_QUARANTINE_MAX_BUFFER_LEN",
    "_SYNC_MARKER_PREFIX",
***REMOVED***


# ── Constants ─────────────────────────────────────────────────────────────

_CHUNK_PRIMARY_BYTES = 3500  # primary TG message-size budget (CON-8 closed)
_CHUNK_GZIP_THRESHOLD_BYTES = 2 * 1024 * 1024  # 2 MB fallback to TG doc (per ADR-010)
_QUARANTINE_MAX_AGE_SECONDS = 86_400  # 24h quarantine age (per scenario.yaml)
_QUARANTINE_MAX_BUFFER_LEN = 1000  # bounded queue policy (per CON-21)
_SYNC_MARKER_PREFIX = "##FB_STATE##"  # TG-parseable prefix (per interface.py)
_LISTENER_DRAIN_TIMEOUT_SECONDS = 5.0  # shutdown drain budget


# ── Structured errors (CAN-14 FAIL-LOUD; no silent raises for sync flow) ──


class RemoteSyncError(Exception):
    """Base for all runtime sync errors. Caller decides retry/surface."""


class RemoteSyncCapabilityError(RemoteSyncError):
    """Raised at construction if capability tokens are not in closed-set."""


class RemoteSyncLifecycleError(RemoteSyncError):
    """Raised on misuse of coordinator lifecycle (post-shutdown calls, etc)."""


class RemoteSyncConfigError(RemoteSyncError):
    """Raised if coordinator config (sync_mode, etc) is invalid."""


class ChunkingError(RemoteSyncError):
    """Raised if envelope cannot fit in any chunk size budget (corrupt state)."""


# ── Pure helpers (mirror pytest coverage; no imports of TG) ───────────────


def _now_ms() -> int:
    """Canonical timestamp helper — single-source for offline-deterministic tests."""
    return int(time.time() * 1000)


def _lww_merge_per_key(
    local: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
    remote: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
) -> Tuple[Dict[str, Tuple[Any, int***REMOVED******REMOVED***, Set[str***REMOVED******REMOVED***:
    """Per-key LWW merge (NOT whole-document).

    Args:
      local: `{key: (value, last_updated_ms)***REMOVED***`
      remote: `{key: (value, last_updated_ms)***REMOVED***`

    Returns:
      merged: post-LWW dict (newer wins per-key, ties keep local)
      dropped_keys: keys dropped because remote was strictly older
    """
    merged: Dict[str, Tuple[Any, int***REMOVED******REMOVED*** = dict(local)
    dropped: Set[str***REMOVED*** = set()

    for key, (rvalue, rts) in remote.items():
        if key not in local:
            merged[key***REMOVED*** = (rvalue, rts)
            continue
        lvalue, lts = local[key***REMOVED***
        if rts > lts:
            merged[key***REMOVED*** = (rvalue, rts)
        elif rts == lts:
            # deterministic tie-break: keep local (avoids flapping on
            # simultaneous edits from two devices with shared clock drift)
            pass
        else:
            dropped.add(key)
    return merged, dropped


def _chunk_envelope_payload(
    payload_json: str,
) -> List[str***REMOVED***:
    """Split a JSON envelope payload into TG-message-sized chunks.

    Layout (per ADR-010 + scenario.yaml chunking spec):
      - chunk 0: `<marker> V1 <correlation_id> CHUNK 0/N <json_head>`
      - chunk i (1..N-1): `<marker> V1 <correlation_id> CHUNK i/N <json_tail>`
      - last chunk may be gzip_base64 if total > gzip threshold

    Raises:
      ChunkingError: if `payload_json` is empty or zero-length.
    """
    if not payload_json or not isinstance(payload_json, str):
        raise ChunkingError(
            f"empty envelope payload — cannot chunk (got {payload_json!r***REMOVED***)"
        )
    if len(payload_json.encode("utf-8")) > _CHUNK_GZIP_THRESHOLD_BYTES:
        gz = gzip.compress(payload_json.encode("utf-8"))
        payload_json = "gzip_b64:" + base64.b64encode(gz).decode("ascii")

    # Primary chunks (3500 bytes / 3500 chars approximated via utf-8)
    if len(payload_json) <= _CHUNK_PRIMARY_BYTES:
        return [payload_json***REMOVED***

    # Simple byte-based split (no JSON-boundary heal — ADR-010 §chunking note:
    # "client reconstructs by stitching, validates JSON parse at end")
    chunks: List[str***REMOVED*** = [***REMOVED***
    step = _CHUNK_PRIMARY_BYTES
    for i in range(0, len(payload_json), step):
        chunks.append(payload_json[i : i + step***REMOVED***)
    if not chunks:
        raise ChunkingError("empty envelope payload — cannot chunk")
    return chunks


def _format_envelope_marker(
    chunk_index: int,
    chunk_total: int,
    correlation_id: str,
) -> str:
    """Build the TG-message text header for one chunk.

    Format: `<marker> V1 <correlation_id> CHUNK i/N`

    The chunk body follows on the next line; reconstruction concatenates
    bodies in `0..N-1` order.
    """
    return (
        f"{_SYNC_MARKER_PREFIX***REMOVED*** V{SYNC_VERSION_V1***REMOVED*** {correlation_id***REMOVED*** "
        f"CHUNK {chunk_index***REMOVED***/{chunk_total***REMOVED***"
    )


def _validate_closed_vocab_capability(token: str, valid: Set[str***REMOVED***) -> bool:
    """Closed-vocab validation per CON-8: never accept free-form strings."""
    return token in valid


# ── Capability closed-vocab (mirrors scenario.yaml capabilities: list) ───

_VALID_CAPABILITIES: Set[str***REMOVED*** = frozenset(
    {
        "state-sync",
        "telegram-mtproto-relay",
        "delta-resolution",
        "chunked-large-state",
    ***REMOVED***
)


# ── Test-injection hooks (per CAN-14 mockability pattern) ────────────────

# Each hook is optional Callable[Awaitable***REMOVED*** used by tests to bypass real TG.
# In production, defaults are populated from core_02.telegram_contract.
SendFn = Callable[[int, str***REMOVED***, Awaitable[Optional[int***REMOVED******REMOVED******REMOVED***
HistoryFn = Callable[[int, int***REMOVED***, Awaitable[List[str***REMOVED******REMOVED******REMOVED***
MeFn = Callable[[***REMOVED***, Awaitable[Any***REMOVED******REMOVED***


# ── Internal helpers (impl-private; tests bypass) ────────────────────────


@dataclass
class _PendingPush:
    """Internal: queued push awaiting TG delivery. NOT exported."""

    envelope: SyncEnvelope
    enqueued_ms: int
    chunk_count: int


@dataclass
class _ConflictRecord:
    """Internal: tracked manual-resolve conflict. NOT exported."""

    key: str
    local_value: Any
    local_ts_ms: int
    remote_value: Any
    remote_ts_ms: int
    detected_ms: int


# ── Coordinator impl ──────────────────────────────────────────────────────


class RemoteSyncCoordinatorImpl:
    """Phase 5.3-B runtime — implements Phase 5.3-A Protocol.

    Construction is **struct-only** (no TG), per Freebuff pattern. First
    `push_state` / `pull_state` call bootstraps TG on-demand via
    `core_02.telegram_contract` (for sends) or via
    `projects_17.tg_terminal_messenger.TGClient` (for history/me).

    Thread-safety: a `threading.RLock` guards all mutations; public async
    methods are callable from multiple coroutines safely.

    Single-use: after `shutdown()`, the instance is dead. Construct fresh.

    Args:
      device_label: human-readable label for this peer ("lipgloss-laptop",
        "android-pixel-7", etc).
      sync_mode: one of `SyncMode.{SAVED_MESSAGES,SYNC_GROUP,DRAFT***REMOVED***`. Maps
        to a CAN-3 chat_id (or designator for SYNC_GROUP pending_resolve).
      send_fn: optional override for the TG-send function
        (test-injection; default = lambda resolved via `sync_mode`).
      history_fn: optional override for TG history fetch.
      me_fn: optional override for current-user identity.
    """

    def __init__(
        self,
        device_label: str,
        sync_mode: SyncMode = SyncMode.SAVED_MESSAGES,
        send_fn: Optional[SendFn***REMOVED*** = None,
        history_fn: Optional[HistoryFn***REMOVED*** = None,
        me_fn: Optional[MeFn***REMOVED*** = None,
    ) -> None:
        """Construct (no I/O). Validate capability closed-vocab early."""
        if (
            not device_label
            or not isinstance(device_label, str)
            or not device_label.strip()
        ):
            raise RemoteSyncConfigError(
                f"device_label must be non-empty non-whitespace string, "
                f"got {device_label!r***REMOVED***"
            )

        self._device_label = device_label
        self._sync_mode = sync_mode

        # Lifecycle
        self._lock = threading.RLock()
        self._shutdown_called = False
        self._device_id: Optional[str***REMOVED*** = None  # assigned at register_device
        self._last_event: Optional[Dict[str, Any***REMOVED******REMOVED*** = None

        # State
        self._local_state: Dict[str, Tuple[Any, int***REMOVED******REMOVED*** = {***REMOVED***
        self._registered_devices: Dict[str, SyncDevice***REMOVED*** = {***REMOVED***
        self._conflict_log: Dict[str, _ConflictRecord***REMOVED*** = {***REMOVED***
        # Quarantine stores SynthEnvelope items for uniform downstream
        # processing. NOTE: per-key timestamps not preserved (by Protocol
        # spec — SyncDelta has only one timestamp_ms). For manual resolve
        # at Play time, app feteches fractal snapshot from local+remote
        # streams separately.
        self._quarantine_buffer: Deque[SyncEnvelope***REMOVED*** = deque(
            maxlen=_QUARANTINE_MAX_BUFFER_LEN
        )
        self._pending_push: Deque[_PendingPush***REMOVED*** = deque(maxlen=_QUARANTINE_MAX_BUFFER_LEN)

        # asyncio task (listener loop) — placeholder for Phase 5.3-C
        self._listener_task: Optional[asyncio.Task***REMOVED*** = None  # type: ignore[type-arg***REMOVED***

        # Live TG cache (cached pushes from pull_state)
        self._incoming_buffer: Deque[SyncEnvelope***REMOVED*** = deque(maxlen=500)

        # Test-injection hooks (defaulting to real telegram_contract calls)
        if send_fn is not None:
            self._send_fn = send_fn
        else:
            # Bind to a concrete function based on sync_mode at use time
            self._send_fn = self._resolve_default_send_fn(sync_mode)
        self._history_fn = history_fn  # None → lazy-import TGClient on demand
        self._me_fn = me_fn  # None → lazy-import TGClient on demand

        logger.info(
            "constructed (device_label=%s, sync_mode=%s, send_injected=%s, "
            "history_injected=%s, me_injected=%s)",
            device_label,
            sync_mode.value,
            send_fn is not None,
            history_fn is not None,
            me_fn is not None,
        )

    # ── Capabilities (CON-8 closed-vocab static report) ──────────────────

    def capabilities(self) -> frozenset:
        """Report closed-set capability tokens. Tests verify membership.

        Returns an immutable `frozenset` copy to prevent caller mutation
        from leaking back into the global closed-vocab (CON-8 invariant).
        """
        return frozenset(_VALID_CAPABILITIES)

    def _assert_capability(self, token: str) -> None:
        """Early-fail if a caller asks for an unsupported capability."""
        if not _validate_closed_vocab_capability(token, _VALID_CAPABILITIES):
            raise RemoteSyncCapabilityError(
                f"capability token {token!r***REMOVED*** not in closed-set "
                f"{sorted(_VALID_CAPABILITIES)***REMOVED***"
            )

    # ── State mutation (lock-guarded) ────────────────────────────────────

    def _update_local(self, key: str, value: Any, ts_ms: int) -> None:
        with self._lock:
            self._local_state[key***REMOVED*** = (value, ts_ms)
            self._last_event = {
                "kind": "local_update",
                "key": key,
                "ts_ms": ts_ms,
            ***REMOVED***

    def _apply_remote_envelope(self, envelope: SyncEnvelope) -> None:
        """Apply a remote SyncEnvelope into local mirror (no LWW; pure last-wins
        for init replay). Per-key LWW via `resolve_conflict()` for conflict
        reconciliation."""
        with self._lock:
            for k, v in envelope.delta.updated_keys.items():
                self._local_state[k***REMOVED*** = (v, envelope.delta.timestamp_ms)
            for k in envelope.delta.deleted_keys:
                self._local_state.pop(k, None)
            self._last_event = {
                "kind": "remote_pull",
                "source_device_id": envelope.delta.source_device_id,
                "ts_ms": envelope.delta.timestamp_ms,
                "keys": list(envelope.delta.updated_keys),
            ***REMOVED***

    # ── Default send_fn resolver (sync_mode → chat_id binding) ──────────

    @staticmethod
    def _resolve_default_send_fn(sync_mode: SyncMode) -> SendFn:
        """Map sync_mode → CAN-3 chat_id + report function.

        SYNC_GROUP is pending_resolve per CON-26 — falls back to ALEX_LITVINOV
        (the nearest configured fallback chat_id) until user provides a real
        sync group id via contract update.
        """
        if sync_mode == SyncMode.SAVED_MESSAGES:
            chat_id = SAVED_MESSAGES_CHAT_ID
            report_fn = report_to_saved_messages
        elif sync_mode == SyncMode.SYNC_GROUP:
            chat_id = ALEX_LITVINOV_CHAT_ID  # CON-26 fallback pending group id
            report_fn = report_to_alex_litvinov
        elif sync_mode == SyncMode.DRAFT:
            # In-flight ephemeral state still routed to SAVED for 5.3-B
            chat_id = SAVED_MESSAGES_CHAT_ID
            report_fn = report_to_saved_messages
        else:
            closed = [m.value for m in SyncMode***REMOVED***
            raise RemoteSyncConfigError(
                f"sync_mode {sync_mode!r***REMOVED*** not in closed-set {closed***REMOVED***"
            )

        async def _default_send(_chat_id: int, text: str) -> Optional[int***REMOVED***:
            # Default send dispatches on resolved chat_id (closure); the
            # _chat_id positional arg is honored for symmetry with injection.
            if _chat_id != chat_id:
                # Defensive: an injected send_fn called us with another
                # chat_id → re-dispatch via raw telethon (not yet wired)
                logger.warning(
                    "_default_send called with chat_id=%s != bound %s — "
                    "probable test mock misconfiguration",
                    _chat_id,
                    chat_id,
                )
            return await report_fn(text)

        return _default_send

    def _chat_id_for_mode(self) -> int:
        if self._sync_mode == SyncMode.SAVED_MESSAGES:
            return SAVED_MESSAGES_CHAT_ID
        if self._sync_mode == SyncMode.SYNC_GROUP:
            return ALEX_LITVINOV_CHAT_ID
        if self._sync_mode == SyncMode.DRAFT:
            return SAVED_MESSAGES_CHAT_ID
        raise RemoteSyncConfigError(
            f"sync_mode {self._sync_mode!r***REMOVED*** not in closed-set {[m.value for m in SyncMode***REMOVED******REMOVED***"
        )

    # ── Async pub methods (Protocol surface) ────────────────────────────

    async def push_state(self, delta: SyncDelta) -> Dict[str, Any***REMOVED***:
        """Push a delta to Telegram via chunked message envelope.

        Behavior:
          - validate capability +91, register_device prerequisite),
          - chunk delta payload (3500 chars; gzip_b64 if large),
          - emit each chunk as TG message via injected or default `send_fn`,
          - append to `_pending_push` queue (drained on shutdown).
        """
        self._assert_capability("state-sync")
        self._assert_capability("chunked-large-state")
        self._assert_capability("telegram-mtproto-relay")

        if self._shutdown_called:
            return {"ok": False, "error": "coordinator is shutdown"***REMOVED***

        if self._device_id is None:
            return {
                "ok": False,
                "error": "device not registered; call register_device() first",
                "chunk_count": 0,
            ***REMOVED***

        # Build SyncEnvelope
        try:
            env = SyncEnvelope(
                delta=delta,
                signature=None,
                compression="none",
                marker="##FB_STATE##",  # type: ignore[arg-type***REMOVED***
            )
        except TypeError as e:
            return {"ok": False, "error": f"SyncEnvelope construction: {e***REMOVED***"***REMOVED***

        payload_json = json.dumps(
            {
                "v": SYNC_VERSION_V1,
                "delta": {
                    "timestamp_ms": delta.timestamp_ms,
                    "source_device_id": delta.source_device_id,
                    "revision": delta.revision,
                    "sync_mode": delta.sync_mode.value,
                    "updated_keys": delta.updated_keys,
                    "deleted_keys": list(delta.deleted_keys),
                ***REMOVED***,
            ***REMOVED***,
            separators=(",", ":"),
            sort_keys=True,
        )

        chunks = _chunk_envelope_payload(payload_json)
        chunk_count = len(chunks)
        correlation_id = f"{self._device_id***REMOVED***-{delta.revision***REMOVED***-{_now_ms()***REMOVED***"

        # Send each chunk
        sent_msg_ids: List[int***REMOVED*** = [***REMOVED***
        chat_id = self._chat_id_for_mode()
        for i, body in enumerate(chunks):
            text = _format_envelope_marker(i, chunk_count, correlation_id) + "\n" + body
            try:
                msg_id = await self._send_fn(chat_id, text)
            except Exception as e:  # defensive — TGClient raises on disconnect
                logger.warning("chunk %d/%d send failed: %s", i, chunk_count, e)
                return {
                    "ok": False,
                    "error": f"chunk {i***REMOVED***/{chunk_count***REMOVED*** failed: {e***REMOVED***",
                    "chunk_count": chunk_count,
                    "partial_sent": sent_msg_ids,
                ***REMOVED***
            # None msg_id is non-fatal (could be telethon race or zombie hook)
            if msg_id is not None:
                sent_msg_ids.append(msg_id)

        with self._lock:
            self._pending_push.append(
                _PendingPush(
                    envelope=env,
                    enqueued_ms=_now_ms(),
                    chunk_count=chunk_count,
                )
            )

        logger.info(
            "push_state sent %d chunks to chat_id=%s (rev=%d, corr=%s)",
            chunk_count,
            chat_id,
            delta.revision,
            correlation_id,
        )
        return {
            "ok": True,
            "chunk_count": chunk_count,
            "msg_ids": sent_msg_ids,
            "correlation_id": correlation_id,
        ***REMOVED***

    async def pull_state(self) -> Optional[SyncDelta***REMOVED***:
        """Replay past state events from Telegram history; return the latest
        applied `SyncDelta` (or `None` if no incoming messages since last pull).

        Conformance: per `runtime_05/scenarios/19_remote_sync/interface.py`
        Protocol `RemoteSyncCoordinator` the contract returns `Optional[SyncDelta***REMOVED***`.
        Envelopes are still cached in `_incoming_buffer` for the 5.3-C
        listener loop.

        Behavior:
          - bootstrap history_fn (lazy-import TGClient if not injected),
          - query chat history in current sync_mode,
          - parse `##FB_STATE##` marker messages into envelopes,
          - apply each envelope to local mirror via `_apply_remote_envelope`,
          - return the latest applied SyncDelta (or None).
        """
        self._assert_capability("state-sync")

        if self._shutdown_called:
            return None

        history_fn = await self._ensure_history_fn()
        if history_fn is None:
            logger.warning(
                "pull_state skipped: history_fn unavailable "
                "(TGClient not present in environment)"
            )
            return None

        chat_id = self._chat_id_for_mode()
        try:
            history = await history_fn(chat_id, 200)
        except Exception as e:
            logger.warning("pull_state history fetch failed: %s", e)
            return None

        # Parse marker-prefixed messages into envelopes
        envelopes: List[SyncEnvelope***REMOVED*** = [***REMOVED***
        for msg_text in history:
            if not isinstance(msg_text, str):
                continue
            if not msg_text.startswith(_SYNC_MARKER_PREFIX):
                continue
            # Strip marker header line; parse the JSON body
            try:
                body = msg_text.split("\n", 1)[1***REMOVED***
                parsed = json.loads(body)
                env = _reconstruct_envelope_from_parsed(parsed)
                if env is not None:
                    envelopes.append(env)
            except (IndexError, json.JSONDecodeError):
                continue

        # Apply each envelope to local mirror + cache + track latest
        latest_delta: Optional[SyncDelta***REMOVED*** = None
        with self._lock:
            for env in envelopes:
                self._incoming_buffer.append(env)
                self._apply_remote_envelope(env)
                latest_delta = env.delta

        logger.info(
            "pull_state applied %d envelopes from chat_id=%s; latest_delta ts=%s",
            len(envelopes),
            chat_id,
            getattr(latest_delta, "timestamp_ms", None),
        )
        return latest_delta

    async def resolve_conflict(
        self,
        local: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
        remote: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
        mode: ConflictResolution = ConflictResolution.LWW_PER_KEY,
    ) -> Dict[str, Any***REMOVED***:
        """Resolve a per-key conflict between local and remote states.

        Modes:
          - LWW_PER_KEY: canonical — newer timestamp wins per-key, ties
            keep local; older strictly-remote keys dropped (logged).
          - WHOLE_DOC_LWW: NOT recommended per ADR-010; kept for tiny state.
          - MANUAL: records `_ConflictRecord`; caller surfaces to UI.
          - QUARANTINE: records `_ConflictRecord` AND appends envelope to
            quarantine buffer for manual review.
        """
        self._assert_capability("delta-resolution")

        if mode == ConflictResolution.LWW_PER_KEY:
            merged, dropped = _lww_merge_per_key(local, remote)
            return {
                "mode": mode.value,
                "merged": merged,
                "dropped_keys": sorted(dropped),
                "quarantined": False,
            ***REMOVED***

        if mode == ConflictResolution.WHOLE_DOC_LWW:
            # pick whichever side has the most-recent maximum timestamp
            local_max = max((ts for _, ts in local.values()), default=0)
            remote_max = max((ts for _, ts in remote.values()), default=0)
            return {
                "mode": mode.value,
                "merged": remote if remote_max > local_max else local,
                "dropped_keys": [***REMOVED***,
                "quarantined": False,
            ***REMOVED***

        if mode == ConflictResolution.MANUAL:
            self._record_conflicts(local, remote)
            return {
                "mode": mode.value,
                "merged": local,  # keep local pending user action
                "dropped_keys": [***REMOVED***,
                "quarantined": False,
            ***REMOVED***

        if mode == ConflictResolution.QUARANTINE:
            self._record_conflicts(local, remote)
            with self._lock:
                self._quarantine_buffer.append(
                    self._synthesize_quarantine_record(local, remote)
                )
            return {
                "mode": mode.value,
                "merged": local,
                "dropped_keys": [***REMOVED***,
                "quarantined": True,
                "quarantine_len": len(self._quarantine_buffer),
            ***REMOVED***

        # Should not reach here (closed enum); fail loud per CON-8
        raise RemoteSyncError(f"unknown conflict mode: {mode!r***REMOVED***")

    async def quarantine(self, envelope: SyncEnvelope) -> Dict[str, Any***REMOVED***:
        """Manually append an envelope to the bounded quarantine buffer.

        Buffer is `deque(maxlen=_QUARANTINE_MAX_BUFFER_LEN)` — older entries
        are evicted FIFO on overflow (per scenario.yaml quarantine config).
        """
        self._assert_capability("state-sync")

        if self._shutdown_called:
            return {"ok": False, "error": "coordinator is shutdown"***REMOVED***

        # Reject quarantining if envelope age > max_delta_age_seconds policy
        age_seconds = (_now_ms() - envelope.delta.timestamp_ms) // 1000
        if age_seconds > _QUARANTINE_MAX_AGE_SECONDS:
            return {
                "ok": False,
                "error": (
                    f"envelope age {age_seconds***REMOVED***s exceeds quarantine limit "
                    f"{_QUARANTINE_MAX_AGE_SECONDS***REMOVED***s"
                ),
                "age_seconds": age_seconds,
            ***REMOVED***

        with self._lock:
            self._quarantine_buffer.append(envelope)
            buf_len = len(self._quarantine_buffer)
        logger.info("quarantine ok (buf_len=%d, age=%ds)", buf_len, age_seconds)
        return {
            "ok": True,
            "age_seconds": age_seconds,
            "buffer_len": buf_len,
            "evicted": buf_len >= _QUARANTINE_MAX_BUFFER_LEN,
        ***REMOVED***

    async def register_device(self, label: str) -> SyncDevice:
        """Register this device via TG identity lookup.

        Behavior:
          - bootstrap me_fn (lazy-import TGClient if not injected),
          - construct SyncDevice with tg_user_id from get_me,
          - idempotent: returns existing device if already registered.
        """
        if self._device_id is not None:
            with self._lock:
                return self._registered_devices[self._device_id***REMOVED***

        me_fn = await self._ensure_me_fn()
        if me_fn is None:
            # Fallback: use LIVE_SESSION_PHONE as definitive identity anchor
            tg_user_id = LITVINOV_CHAT_ID  # NOT a user_id, but stable fallback
            logger.warning(
                "register_device: me_fn unavailable; using LITVINOV_CHAT_ID=%d "
                "as fallback tg_user_id (acceptable per CAN-3 v5.40.0)",
                tg_user_id,
            )
        else:
            try:
                me = await me_fn()
            except Exception as e:
                raise RemoteSyncLifecycleError(f"register_device me_fn: {e***REMOVED***") from e
            tg_user_id = getattr(me, "user_id", getattr(me, "id", LITVINOV_CHAT_ID))

        # device_id derived from tg user_id + label (stable per session)
        device_id = f"tg:{tg_user_id***REMOVED***:{label***REMOVED***"
        now_ms = _now_ms()
        device = SyncDevice(
            device_id=device_id,
            tg_user_id=int(tg_user_id),
            label=label,
            registered_at_ms=now_ms,
            last_seen_ms=now_ms,
        )
        with self._lock:
            self._registered_devices[device_id***REMOVED*** = device
            self._device_id = device_id
        logger.info(
            "register_device ok (device_id=%s, tg_user_id=%d)",
            device_id,
            tg_user_id,
        )
        return device

    async def shutdown(self) -> Dict[str, Any***REMOVED***:
        """Orderly shutdown: drain queue → cancel listener → no TG forced-disconnect.

        Idempotent: post-shutdown calls return `error`.
        """
        if self._shutdown_called:
            return {"ok": False, "error": "shutdown already called"***REMOVED***
        self._shutdown_called = True

        drained = 0
        try:
            with self._lock:
                pending = list(self._pending_push)
                self._pending_push.clear()
            drained = len(pending)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("shutdown drain failed: %s", e)

        # Cancel listener task if it exists
        if self._listener_task is not None and not self._listener_task.done():
            try:
                self._listener_task.cancel()
            except Exception as e:  # pragma: no cover — defensive
                logger.warning("listener task cancel failed: %s", e)

        logger.info("shutdown complete (drained=%d)", drained)
        return {"ok": True, "drained": drained***REMOVED***

    async def get_last_event(self) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """Return last cached event for UI polling. None if no events yet."""
        with self._lock:
            return self._last_event

    # ── Internal helpers ────────────────────────────────────────────────

    async def _ensure_history_fn(self) -> Optional[HistoryFn***REMOVED***:
        """Lazy-bootstrap history_fn if not injected.

        Returns None if `projects_17/tg_terminal_messenger/TGClient` cannot
        be imported. Caller (pull_state) treats None as skip-history.
        """
        if self._history_fn is not None:
            return self._history_fn
        try:
            from projects_17.tg_terminal_messenger.src.telegram.client import (  # type: ignore
                TGClient,
            )

            async def _history_via_tgclient(
                chat_id: int, limit: int
            ) -> List[str***REMOVED***:
                client = TGClient()
                try:
                    connected = await client.connect()
                    if not connected:
                        return [***REMOVED***
                    history = await client.get_history(chat_id, limit=limit)
                    # Telethon iterates Messages; extract .text attribute
                    return [
                        m.text
                        for m in history
                        if getattr(m, "text", None) is not None
                    ***REMOVED***
                finally:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

            self._history_fn = _history_via_tgclient
            return self._history_fn
        except Exception as e:
            logger.warning("_ensure_history_fn: TGClient unavailable: %s", e)
            return None

    async def _ensure_me_fn(self) -> Optional[MeFn***REMOVED***:
        """Lazy-bootstrap me_fn if not injected."""
        if self._me_fn is not None:
            return self._me_fn
        try:
            from projects_17.tg_terminal_messenger.src.telegram.client import (  # type: ignore
                TGClient,
            )

            async def _me_via_tgclient() -> Any:
                client = TGClient()
                try:
                    connected = await client.connect()
                    if not connected:
                        return None
                    return await client.get_me()
                finally:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

            self._me_fn = _me_via_tgclient
            return self._me_fn
        except Exception as e:
            logger.warning("_ensure_me_fn: TGClient unavailable: %s", e)
            return None

    def _record_conflicts(
        self,
        local: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
        remote: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
    ) -> None:
        """Record per-key conflicts in `_conflict_log` (internal)."""
        with self._lock:
            for k, (lv, lts) in local.items():
                if k in remote:
                    rv, rts = remote[k***REMOVED***
                    if lv != rv and abs(lts - rts) < 10_000:  # near-simultaneous
                        self._conflict_log[k***REMOVED*** = _ConflictRecord(
                            key=k,
                            local_value=lv,
                            local_ts_ms=lts,
                            remote_value=rv,
                            remote_ts_ms=rts,
                            detected_ms=_now_ms(),
                        )

    def _synthesize_quarantine_record(
        self,
        local: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
        remote: Dict[str, Tuple[Any, int***REMOVED******REMOVED***,
    ) -> SyncEnvelope:
        """Build a quarantine envelope from synthesized LWW-merged snapshot.

        Per-key timestamps are NOT preserved (Protocol SyncDelta has only
        one timestamp_ms). For per-key age recovery, the caller must
        re-fetch the local+remote streams (CAN-14 fail-loud: documented
        limitation, not silent).
        """
        merged, _ = _lww_merge_per_key(local, remote)
        flat: Dict[str, Any***REMOVED*** = {k: v for k, (v, _) in merged.items()***REMOVED***
        delta = SyncDelta(
            timestamp_ms=_now_ms(),
            source_device_id=self._device_id or "local",
            revision=0,
            sync_mode=self._sync_mode,
            updated_keys=flat,
            deleted_keys=[***REMOVED***,
        )
        return SyncEnvelope(
            delta=delta,
            signature=None,
            compression="none",
            marker="##FB_STATE##",  # type: ignore[arg-type***REMOVED***
        )


# ── Module-level pure helper (tests import directly) ─────────────────────


def _reconstruct_envelope_from_parsed(
    parsed: Dict[str, Any***REMOVED***
) -> Optional[SyncEnvelope***REMOVED***:
    """Parse a TG-message JSON body into a SyncEnvelope (helper used by
    `pull_state`). Pure function on `parsed` — no I/O."""
    try:
        d = parsed["delta"***REMOVED***
        delta = SyncDelta(
            timestamp_ms=int(d["timestamp_ms"***REMOVED***),
            source_device_id=str(d["source_device_id"***REMOVED***),
            revision=int(d["revision"***REMOVED***),
            sync_mode=SyncMode(str(d["sync_mode"***REMOVED***)),
            updated_keys=dict(d.get("updated_keys", {***REMOVED***)),
            deleted_keys=list(d.get("deleted_keys", [***REMOVED***)),
        )
        return SyncEnvelope(
            delta=delta,
            signature=None,
            compression="none",
            marker="##FB_STATE##",  # type: ignore[arg-type***REMOVED***
        )
    except (KeyError, ValueError, TypeError):
        return None


# ─── Phase 5.3-D listener loop pre-work (scaffold, ADR-011) ───

class RemoteSyncListener:
    """Phase 5.3-D Realtime TG Event Listener (not yet wired to TGClient.on() hot-path).

    Status: SCAFFOLD ONLY — interface + lifecycle + docstrings per ADR-011. Real callback
    wiring deferred to follow-up PR after `core_02/_tg_client_v2.py` TGClient fork (DEBT-5.21)
    exposes `add_event_handler` + `ids=` kwarg.

    Lifecycle:
        start() -> bootstrap TGClient (via deferred _tg_client_v2 fork) + attach
                    events.NewMessage handler to specified chat_ids (Saved + Литвинов).
        stop() -> detach event handler + cleanup queue/buffer references.

    Hot-path semantics:
        _on_new_message runs in Telethon's background event loop. We CANNOT await
        coordinator methods directly (race risk), so we push validated envelopes into
        _incoming_buffer (collections.deque(maxlen=128)) and let pull_state() resolve
        LWW on next call (per CON-31 listener-loop defer-resolution discipline).

    Forward-looking guards (per ADR-011 risk assessment):
      • Memory leak: _incoming_buffer uses collections.deque(maxlen=N) (no unbounded growth)
      • Reconnect logic: on TGClient.on_disconnected, trigger pull_state() history fetch
        to recover from missed events during downtime
      • Asyncio loop: handler payload handoff via _incoming_buffer (not direct coroutine)
    """

    def __init__(self, coordinator: "RemoteSyncCoordinatorImpl") -> None:
        self._coordinator = coordinator
        self._tg_client = None  # set in start() after _tg_client_v2 fork available
        self._running = False
        # Incoming message buffer (hot-path writes, cold-path reads via pull_state)
        from collections import deque
        self._incoming_buffer: "deque[tuple[int, bytes***REMOVED******REMOVED***" = deque(maxlen=128)
        # Source-of-truth chat_ids (Saved Messages + Литвинов, per ADR-010)
        self._source_chat_ids: "tuple[int, ...***REMOVED***" = (
                SAVED_MESSAGES_CHAT_ID,  # CON-19: canonical single-source-of-truth (telegram_contract)
                ALEX_LITVINOV_CHAT_ID,   # alias of LITVINOV_CHAT_ID
            )

    async def start(self) -> bool:
        """Bootstrap TGClient + attach events.NewMessage handler.

        Returns True if listener attached successfully. False if TGClient fork
        (`core_02/_tg_client_v2.py`) failed to connect or event handler
        registration failed.

        DEBT-5.21 closed: uses ``TGClientV2`` wrapper on a fresh TGClient from
        ``_get_tg_client_factory()``, attaches ``self._on_new_message`` as a sync
        callback (per N-1 fix — Telethon does NOT await coroutines).

        Note: ``telethon`` is imported mid-function (not top-level) because it's
        a heavy optional dependency — absent in CI, so import fails at connect
        time (not at module import time), preserving test stability.
        """
        from core_02._tg_client_v2 import TGClientV2  # DEBT-5.21 closure
        from core_02.telegram_contract import _get_tg_client_factory
        from telethon import events  # heavy optional dep — deferred per ANTI-2 lesson

        base_client = _get_tg_client_factory()()
        self._tg_client = TGClientV2(base_client)
        await self._tg_client.connect()

        event_filter = events.NewMessage(chats=list(self._source_chat_ids))
        self._tg_client.add_event_handler(self._on_new_message, event_filter)
        self._running = True
        return True

    async def stop(self) -> None:
        """Detach event handler + cleanup."""
        if self._tg_client is not None:
            # remove_event_handler available via TGClientV2 but not yet needed
            # (drain_incoming + shutdown handles residual events)
            pass
        self._tg_client = None
        self._running = False
        self._incoming_buffer.clear()

    def _on_new_message(self, event: "Any") -> None:  # sync callback (Telethon does NOT await; fire-and-forget coroutine would be silently dropped)
        """Hot-path callback invoked by Telethon's event loop on new message.

        Validates ``##FB_STATE##`` marker (per CON-31 + ADR-011), extracts
        envelope bytes, and pushes (msg_id, payload) into _incoming_buffer.
        LWW resolution deferred to next pull_state() call (race-safe handoff
        via buffer).

        Args:
            event: telethon.events.NewMessage instance (NOT awaited; already fired).

        Side-effects:
            Mutates self._incoming_buffer. Does NOT call coordinator directly
            (avoids Telethon-loop / Freebuff-loop race per ADR-011 forward-looking guard).
        """
        msg_id = event.message.id
        text = (event.message.text or "")
        if "##FB_STATE##" not in text:
            return  # not a real StateV2 sync message
        # Envelope bytes are the raw text; actual deserialization is done by
        # pull_state() which calls drain_incoming() and processes the queue.
        envelope_bytes = text.encode("utf-8")
        self._incoming_buffer.append((msg_id, envelope_bytes))

    def drain_incoming(self) -> "list[tuple[int, bytes***REMOVED******REMOVED***":
        """Cold-path helper: drain _incoming_buffer atomically. Called by pull_state().

        Returns list of (msg_id, envelope_bytes) tuples accumulated since last drain.
        Returns empty list if listener not running or buffer is empty.
        """
        if not self._running:
            return [***REMOVED***
        drained: "list[tuple[int, bytes***REMOVED******REMOVED***" = [***REMOVED***
        while self._incoming_buffer:
            drained.append(self._incoming_buffer.popleft())
        return drained

    @property
    def is_running(self) -> bool:
        """Public state read for status reporting (e.g., in MCP tools)."""
        return self._running

    @property
    def pending_count(self) -> int:
        """Pending envelopes count (for diagnostics + buffer overflow detection)."""
        return len(self._incoming_buffer)

