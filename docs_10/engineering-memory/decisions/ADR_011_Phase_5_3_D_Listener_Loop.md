# ADR-011: Phase 5.3-D Realtime Listener & TGClient Fork Strategy

**Date:** 2026-08-03
**Status:** Accepted
**Context:** Phase 5.3-D requires realtime conflict detection via persistent TG event listener.

## Context

Phase 5.3-D (extension of Remote Sync closure at v5.64.0) requires a persistent `TGClient.on(events.NewMessage)` event listener in `core_02/remote_sync.py` to detect incoming StateV2 sync messages in realtime, closing the gap between operator-driven `pull_state` (polling) and push-delivered `events.NewMessage` hot-path.

**Problem 1 (functional):** Existing `TGClient` wrapper at `projects_17/tg_terminal_messenger/src/telegram/client.py` does NOT expose telethon event subscription API (`add_event_handler` / `remove_event_handler`). It only provides polling-oriented methods (`get_me`, `get_messages`, `send_message`).

**Problem 2 (CON-31):** `TGClient.get_messages(self, entity, limit=5)` does NOT accept `ids=` kwarg (telethon-native feature). This was discovered in v5.62.2 (CAN-9 + 5.3-C round-trip runner) where stage3 had to pivot to `client.get_messages(chat_id, limit=100)` + client-side `id` filter. Fixing this for the listener requires extending API surface.

**Cross-project constraint:** `projects_17/tg_terminal_messenger/` is part of the larger `tg_terminal_messenger` project (textual-based terminal messenger), maintained separately from Freebuff main project. In-place changes would violate upstream boundary discipline (CON-20 anti-fragility).

## Decision Drivers

- **D-1**: Avoid `projects_17/` upstream taint (in-place modifications may break tg_terminal_messenger stability).
- **D-2**: Minimize Freebuff-side code duplication (auth + connect lifecycle not duplicated).
- **D-3**: Preserve Phase 5.3-C round-trip runner behavior (CON-31 already documented and accepted).
- **D-4**: Hot-path safety: Telethon event loop vs Freebuff asyncio loop boundary must not race.
- **D-5**: Forward-compatibility for future listener-loop needs (e.g., reaction events for collaborative editing).

## Considered Options

### Option 1 - In-place modification of `projects_17/tg_terminal_messenger/src/telegram/client.py`

Modify upstream TGClient class directly. Adds `add_event_handler` / `remove_event_handler` + `ids` kwarg.

- **Pros:** Zero new files; reuses existing TGClient entirely.
- **Cons:** Taints upstream project boundary. Risk of accidental break of tg_terminal_messenger existing terminal UI flows. Cross-project version drift potential.

**Decision**: Rejected (D-1 violation).

### Option 2 - In-tree fork .fork extension

Create `projects_17/.../client.py.fork` beside original. Breaks Python module resolution.

- **Pros:** No new directories; preserves git history visibility.
- **Cons:** .fork extension not importable via `import` semantics. Requires Python plugin loader hack. Brittle at relocation (D-2 violation - CON-20 lesson).

**Decision**: Rejected (D-2 violation).

### Option 3 - Core Fork (`core_02/_tg_client_v2.py`) - SELECTED

Create new minimal TGClient extension in Freebuff core. Reuses core_02/telegram_contract.py sequencing; extends with event subscription API + `ids` kwarg.

- **Pros:** Clean upstream isolation (D-1 satisfied). Single new file (~80 lines, manageable). Lifecycle via core_02/telegram_contract.py (D-2 satisfied - auth/connect not duplicated). Cross-project version drift impossible (fork IS in freebuff core).
- **Cons:** Minor auth+connection lifecycle duplication (~30 LOC from TGClient). Need to keep fork synced with upstream TGClient contract changes.

**Decision**: SELECTED (D-1 + D-2 + cross-project cleanliness win).

### Option 4 - Raw telethon instantiation in `remote_sync.py`

Bypass TGClient wrapper entirely. Raw `TelegramClient` instantiation + manual event loop setup.

- **Pros:** No fork dependency; direct telethon API access.
- **Cons:** Major auth+connection logic duplication. Lifecycle management brittle (reconnect handling per CON-31 ad-hoc). Risk of heterogeneous session state if both TGClient AND raw telethon are active.

**Decision**: Rejected (D-2 violation; lifecycle nightmare).

## Decision Outcome

**We adopt Option 3 (Core Fork).** Create `core_02/_tg_client_v2.py` with minimal TGClient extensions:

1. `add_event_handler(callback, event) -> None` - wraps telethon `client.add_event_handler`.
2. `remove_event_handler(callback, event) -> None` - wraps telethon `client.remove_event_handler`.
3. `get_messages(self, entity, limit=5, ids=None)` - add `ids` kwarg; if `ids` provided, forward to telethon `get_messages(entity, ids=ids)`; else preserve existing limit-scan semantics (CON-31 backward-compat).

`RemoteSyncListener.start()` will bootstrap the v2 fork via `core_02/telegram_contract.py` factory + attach `events.NewMessage(chats=(SAVED_MESSAGES_CHAT_ID, ALEX_LITVINOV_CHAT_ID))` handler.

## Consequences

**Positive:**
- D-1: `projects_17/tg_terminal_messenger` upstream boundary preserved. No cross-project PR.
- D-2: Auth + connect lifecycle delegated to `core_02/telegram_contract.py` (single source of truth).
- D-5: Forward-compatible for reaction events / collaborative editing hot-path.
- section 5.20 closure comment about "future Phase 5.3-D needs persistent listener" finally actionable.

**Negative:**
- ~30 LOC auth/connect sequence duplication between TGClient and TGClientV2.
- Fork must track upstream TGClient contract changes (mitigated by typed Protocol interface).
- DEBT-5.21 stays OPEN until `_tg_client_v2.py` written + tests pass + listener wired + cross-checked against telethon reconnect semantics.

**Neutral:**
- CON-31 lesson stays as-is (current limit-scan pattern) until v2 fork removes the underlying constraint. Update CON-31 to "partially resolved" once fork ships.

## Cross-References

- **ADR-010** (Remote Sync Telegram Relay): broader context - this ADR addresses specific sub-need within ADR-010 architecture.
- **ARCHITECTUAL_DEBT.md section 5.20** (Remote Sync Runtime - RESOLVED): section 5.20 contained forward-looking guard about Phase 5.3-D listener need; this ADR resolves that forward-looking guard.
- **ARCHITECTUAL_DEBT.md section 5.21** (NEW - Phase 5.3-D Realtime Listener - OPEN): implementation dep tracker.
- **LESSONS.md CON-31** (TGClient wrapper constraint): root-cause lesson for `ids=` kwarg gap; this ADR proposes the cure via fork.
- **CON-20** (anti-fragile code duplication): constraint that drove Option 3 selection over Option 2.
- **CHANGELOG v5.64.0**: Cumulative TG round-trip audit-trail father that confirmed Phase 5.3-C e2e path - Phase 5.3-D builds on this verified layer.

## Implementation Plan

**Phase 5.3-D Execution Sequence** (next session):

1. Write `core_02/_tg_client_v2.py` (~80 LOC - Protocol + 3 method delegates)
2. Write 6-8 mock tests in `tests_09/test_tg_client_v2.py`: get_messages_ids_kwarg + add_event_handler + remove_event_handler + reconnect_pull_state + buffer_overflow_maxlen.
3. Wire `RemoteSyncListener.start()` + `_on_new_message()` + `drain_incoming()` real bodies.
4. Integration test: e2e_push_pull_sync_in_real_time (using mock TGClient + previously-fixed 5.3-C runner pattern).
5. Update CON-31 lesson to mark `ids=` resolution as "RESOLVED via ADR-011 + _tg_client_v2 fork".
6. Bump CHANGELOG to v5.65.0; close DEBT-5.21.

## Forward-Looking Guards

Per ADR-011 risk assessment (thinker validated):

- **Memory leak guard**: `_incoming_buffer` uses `collections.deque(maxlen=128)` - no unbounded growth.
- **Reconnect guard**: on TGClient disconnect, trigger `pull_state()` history fetch to recover missed events.
- **Asyncio loop boundary**: handler writes to buffer (no coroutine), `pull_state()` reads atomically via `drain_incoming()`. Avoids `run_coroutine_threadsafe` complexity.

