"""Interface contract: Phase 5.3 Remote Sync (Telegram-stored Relay).

**Status:** Spec-only contract (NO implementation yet — Phase 5.3-A schema review).

This file exists **only** to:
  1. document the interface Freebuff-side consumers can rely on (typed),
  2. enable `from interface import RemoteSyncCoordinator` for downstream
     import-time checks (this module is import-safe — no real TG calls),
  3. provide canonical symbol anchors for `ScenarioRegistry`-based discovery.

**Runtime implementation lives elsewhere** (next PR: core_02/remote_sync.py
with Telethon + delta logic per ADR-010 risk-mitigation table).

**Cross-references:**
  - ADR-010: `docs_10/vision/decision_index.md §ADR-010`
  - Source: `runtime_05/scenarios/19_remote_sync/scenario.yaml`
  - Downstream consumer: `interior_planner_app/src/store/remoteSyncOverlay.ts`
    (NOT YET IMPLEMENTED — sibling project)

**Design invariants (do not relax without ADR update):**
  - Per-key LWW (NOT whole-document). See `resolve_conflict()` docstring.
  - Capability tokens are CLOSED-set per CON-8 — never accept free-form strings.
  - All public methods are `async` to mirror Telethon's event loop.
  - FAIL-LOUD per CAN-14 — methods return errors instead of raising
    uncontrolled exceptions; caller decides retry vs surface-to-user.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Protocol, runtime_checkable

# ── Public symbol exports (deliberate, mirrors CON-8 closed-vocab). ───────

__all__ = [
    "SyncEnvelope",
    "SyncDelta",
    "SyncOp",
    "SyncMode",
    "ConflictResolution",
    "SyncDevice",
    "RemoteSyncCoordinator",
    "SYNC_VERSION_V1",
***REMOVED***


# ── Constants ────────────────────────────────────────────────────────────

SYNC_VERSION_V1 = "1.0.0"


# ── Enums (closed-set; extended only via ADR update) ─────────────────────


class SyncOp(str, enum.Enum):
    """Per-key operation type carried in a SyncDelta."""

    SET = "set"        # upsert key with new value
    DELETE = "del"     # tombstone key
    CONFLICT = "conflict"  # marker indicating manual review needed


class SyncMode(str, enum.Enum):
    """Where the state lives on Telegram."""

    SAVED_MESSAGES = "saved_messages"      # primary user_id chat_id
    SYNC_GROUP = "sync_group"              # private TG group fan-out
    DRAFT = "draft"                         # in-flight ephemeral (still image of state)


class ConflictResolution(str, enum.Enum):
    """How a conflict is resolved."""

    LWW_PER_KEY = "lww_per_key"            # default — last-writer-wins per field
    WHOLE_DOC_LWW = "whole_doc_lww"        # NOT recommended — use only for tiny state
    MANUAL = "manual"                       # user-driven via /resolve TG command
    QUARANTINE = "quarantine"               # defer past max_delta_age_seconds; manual only


# ── Dataclasses (immutable shape; consumer must rebuild to mutate) ────────


@dataclass(frozen=True)
class SyncDevice:
    """Identifies one Freebuff device peer in the sync mesh.

    `device_id` is a stable per-install uuid (NOT a TG user_id — TG user_id
    identifies the OWNER, not the device). One user may have multiple devices.

    `tg_user_id` is the TG account owning this device — used for permission
    checks against Sync Group membership.
    """

    device_id: str                          # uuid4 generated at first install
    tg_user_id: int                         # TG user_id (110000000 + chat_id convention)
    label: str                              # human-readable ("lipgloss-laptop")
    registered_at_ms: int                    # epoch ms
    last_seen_ms: int                       # epoch ms (for stale device cleanup)


@dataclass(frozen=True)
class SyncDelta:
    """One atomic state update — the unit exchanged between peers.

    `updated_keys` is per-key — NOT a whole-document snapshot. This is what
    enables parallel-edit safety in interior_planner use case (two users
    moving different chairs DON'T overwrite each other).

    `deleted_keys` is a tombstone set: keys removed since last sync. Tombstones
    propagate for `tombstone_ttl_ms` to prevent resurrection by stale deltas.
    """

    timestamp_ms: int                        # TG message timestamp (or fallback UTC ms)
    source_device_id: str                   # device that produced this delta
    revision: int                           # monotonically increasing per-device
    sync_mode: SyncMode                     # where this delta was sent
    updated_keys: Dict[str, Any***REMOVED***            # key → value (gzip+base64 if >3500 chars)
    deleted_keys: List[str***REMOVED*** = field(default_factory=list)
    envelope_version: str = SYNC_VERSION_V1

    def age_ms(self, now_ms: int) -> int:
        """Returns delta age in milliseconds relative to `now_ms`."""
        return max(0, now_ms - self.timestamp_ms)


@dataclass(frozen=True)
class SyncEnvelope:
    """Transport wrapper around a `SyncDelta` for serialization into a TG message.

    The envelope is what gets GZIPped+base64'd+chunked into the TG message body.

    Field ordering note: in Python, `@dataclass` requires non-default fields
    BEFORE default fields. So `delta` (no default) comes first, then defaults
    (`signature`, `compression`, `marker`) trailing.
    """

    delta: SyncDelta                        # the actual change being transported (required)
    signature: Optional[str***REMOVED*** = None         # xsalsa20_poly1305 HMAC (if pre-encrypted)
    compression: Literal["none", "gzip_base64"***REMOVED*** = "none"
    marker: Literal["##FB_STATE##"***REMOVED*** = "##FB_STATE##"   # message body marker for TGClient.on(NewMessage) filter

    def serialize(self) -> str:
        """Render envelope to single-line JSON suitable for TG message body."""
        # Implementation deferred to Phase 5.3-B core_02/remote_sync.py
        raise NotImplementedError("interface.py is spec-only; use core_02/remote_sync.py")


# ── Public API (Protocol) ────────────────────────────────────────────────


@runtime_checkable
class RemoteSyncCoordinator(Protocol):
    """Orchestrates cross-device state using `core_02/telegram_contract.py::TGClient`.

    Implementations:
      - Phase 5.3-B: `core_02/remote_sync.py::RemoteSyncCoordinatorImpl`
      - Tests:      `tests_09/test_remote_sync.py` (mock-based)
      - Phase 6:    optional Bluetooth companion (DEFERRED per ADR-010)

    All methods are async to mirror Telethon's event loop. Methods are
    `Optional`-returning (not exception-raising) per CAN-14 — failed sync
    surfaces to caller for retry-or-not decision.
    """

    @property
    def device_id(self) -> str:
        """Stable per-install uuid (NOT TG user_id)."""
        ...

    @property
    def my_devices(self) -> List[SyncDevice***REMOVED***:
        """Devices in current Sync Group (or [self***REMOVED*** if using Saved Messages only)."""
        ...

    async def push_state(self, delta: SyncDelta) -> bool:
        """Send delta to TG (Saved Messages or Sync Group).

        Returns True if TGClient.send_message succeeded, False otherwise.
        Caller decides retry policy (per `exception_isolated` invariant).

        Implementation per ADR-010 risk-mitigation:
          - debounce 5s (batch local edits),
          - chunk-or-document fallback for >3500 char envelope,
          - gzip+base64 for envelope >4KB.
        """
        ...

    async def pull_state(self) -> Optional[SyncDelta***REMOVED***:
        """Fetch latest TG messages with marker `##FB_STATE##` and apply
        external deltas to local store.

        Returns the most-recently-applied delta, or None if no incoming
        messages since last pull.

        Implementation: TGClient.on(NewMessage) event listener registered
        at coordinator init, fires reconciliation via `resolve_conflict()`.
        """
        ...

    def resolve_conflict(
        self,
        local: SyncDelta,
        remote: SyncDelta,
        mode: ConflictResolution = ConflictResolution.LWW_PER_KEY,
    ) -> SyncDelta:
        """Per-key LWW merge of local+remote deltas.

        Default mode: per-key LWW. Anti-pattern to disable.

        LWW algorithm:
          for key in (local.updated_keys | remote.updated_keys):
            local_v = local.updated_keys.get(key)
            remote_v = remote.updated_keys.get(key)
            if present in only one side: take that side
            if present in both:
              pick the one with newer timestamp_ms
              if timestamp_ms equal: drop with [CONFLICT***REMOVED*** log (rare, but safe)

        Whole-doc LWW (mode=WHOLE_DOC_LWW) exists for tiny state (memory of
        <100 keys) but is NOT recommended for interior_planner (each chair
        independently movable).
        """
        ...

    def quarantine(self, delta: SyncDelta) -> bool:
        """Mark delta as quarantined if age > max_delta_age_seconds (default 24h).

        Quarantined deltas are NOT auto-applied; user must explicitly
        `/resolve` via TG command.
        """
        ...

    async def register_device(self, label: str) -> SyncDevice:
        """Register a new device peer in the Sync Group.

        Onboards new device; returns the new SyncDevice entry.
        Caller stores this locally + pushes SyncDevice registration delta
        to TG so other devices see it.
        """
        ...

    async def shutdown(self) -> None:
        """Cleanup: drain pending push queue, close TGClient, log final state.

        Called on Freebuff Core shutdown signal (SIGTERM, user /stop, etc.).
        """
        ...

    # ── Observability hooks (CAN-14 fail-loud surfaces) ────────────────

    def get_last_event(self) -> Optional[Dict[str, Any***REMOVED******REMOVED***:
        """For /last_event TG command convenience. Returns None if no events."""
        ...


# ── Helpers (validators, factories; NOT async) ───────────────────────────


def is_valid_sync_envelope_text(text: str) -> bool:
    """Returns True if `text` starts with the `##FB_STATE##` marker.

    Used by TGClient.on(NewMessage) listener to filter incoming messages
    to only sync-relevant ones (TG message stream is mostly non-sync noise).
    """
    return text.startswith(SyncEnvelope().marker)


def make_device_id() -> str:
    """Generate stable per-install uuid4."""
    import uuid

    return str(uuid.uuid4())


def now_ms_utc() -> int:
    """Return current epoch milliseconds (UTC) — used as delta timestamp
    ONLY when TG message timestamp is unavailable (fallback path)."""
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


# ── Module-level constants for downstream consumers ─────────────────────


DEFAULT_DEBOUNCE_PUSH_SECONDS: int = 5
DEFAULT_DEDUPE_WINDOW_SECONDS: int = 30
DEFAULT_MAX_DELTA_AGE_SECONDS: int = 86400       # 24h
DEFAULT_CHUNK_PRIMARY_CHARS: int = 3500
DEFAULT_CHUNK_FALLBACK_CHARS: int = 2_000_000   # 2MB → TG document
DEFAULT_COMPRESSION: Literal["none", "gzip_base64"***REMOVED*** = "gzip_base64"
