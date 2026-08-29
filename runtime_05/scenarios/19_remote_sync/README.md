# Scenario 19 — Remote Sync (Telegram-stored Relay)

**Status:** ACTIVE — Phase 5.3 (ADR-010, 2026-08-03)
**Schema:** `1.0.0` (spec authoritative; runtime is Phase 5.3-B post-MVP)
**Source-of-truth rationale:** [`docs_10/vision/decision_index.md` §ADR-010***REMOVED***(../../decision_index.md#adr-010-telegram-stored-relay-phase-53)

---

## Что это

`19_remote_sync/` defines the Freebuff cross-device state-synchronization
overlay built on top of Telegram as a *stored-relay* substrate. State is serialized
to JSON, chunked/compressed if necessary, and persisted into Telegram's
**Saved Messages** + an optional **Sync Group** chat. Multi-device fan-out
is implicit: TG clients on phone/laptop/tablet see the same message history
and can replay the delta stream.

This scenario does NOT replace local storage. For Interior Planner use-case,
`interior_planner_app/src/store/roomStore.ts` (Zustand+AsyncStorage) remains
the synchronous local Source-of-Truth for the UI — fast read/write, no
latency. Remote Sync **watches** AsyncStorage, computes **delta** diffs,
**pushes** them to TG, and **merges** incoming TG deltas back.

---

## Архитектурная диаграмма

```
┌─────────────────┐                   ┌─────────────────┐
│  Device A       │                   │  Device B       │
│  (Android Termux)│                  │  (Laptop TG)    │
│  ┌────────────┐ │                   │  ┌────────────┐ │
│  │ UI / React │ │                   │  │  TG client │ │
│  └─────┬──────┘ │                   │  └─────┬──────┘ │
│        ▼        │                   │        ▲        │
│  ┌────────────┐ │  delta push (JSON) │        │        │
│  │roomStore.ts│─┼─────5s debounce───▶│  TG  /  /       │
│  │(AsyncStorage)│         ┌─────────┤Saved   Group    │
│  └─────┬──────┘ │         │         │Messages 1   2   │
│        ▲        │         │         └─────┬──┬───▲────┘
│        │        │         │               │  │   │
│  ┌─────┴──────┐ │         │               │  │   │
│  │Watch       │ │         │               │  │   │
│  │(diff+deltas)│ │         ▼               ▼  ▼   │
│  └─────┬──────┘ │   ┌──────────────────────────┐ │
│        │        │   │ core_02/telegram_contract│ │
│  ┌─────┴──────┐ │   │ ::TGClient (Telethon)    │ │
│  │RemoteSync  │◀┼───┤ ::report_to_saved_msgs   │ │
│  │Coordinator │ │   │ ::TGClient.on(NewMessage)│ │
│  └────────────┘ │   └──────────────────────────┘ │
└─────────────────┘
```

Solid arrows = synchronous flow. Dotted = TBD (Phase 5.3-B implementation).

---

## Решаемая задача

**Goal:** Allow Freebuff state to follow the user across devices, **without
running our own servers**. State lives on Freebuff + Telegram servers;
user controls access (Saved Messages = user-only; Sync Group = user-managed
membership).

**Non-goals (explicit):**
- Not a generic Notion/Linear replacement (no rich-text formatting).
- Not a CRDT library (CRDT-lite suffices — interior_planner furniture is
  discrete objects, no overlapping concurrent edits of same object).
- Not a TG-bot (interacts via TGClient/MTProto, not Bot API → caller is
  the user, no rate-limit surprises).

---

## Sync Algorithm (CRDT-lite LWW per key)

```
push_state(local_state) -> TG message
  - compute diff(local_state, last_pushed_state)
  - if diff empty, skip (debounce will trigger again on next edit)
  - compress-or-chunk per chunking.{primary_threshold,fallback_threshold***REMOVED***
  - encode sync envelope: {v:1, ts:NOW, dev:DEVICE_ID, op:"set"|"del", ks:{...***REMOVED***, kr:[...***REMOVED******REMOVED***
  - TGClient.send_message(Saved Messages or Sync Group, envelope)

pull_state() -> applied_incoming_deltas
  - TGClient.on(NewMessage): if message text starts with "##FB_STATE##", parse envelope
  - resolve_conflict(local, remote):
      per-key LWW: if remote.ts > local.ts AND remote.dev != local.dev → accept remote
                   if remote.ts == local.ts (rare) → safety: drop with [CONFLICT***REMOVED*** log
                   if remote.ts <  local.ts → reject (stale)
  - applied deltas committed to local AsyncStorage (via watch→apply path)

delta_quarantine: if remote.ts - local.ts > 86400s → log + alert
                   user must manually reconcile via /resolve conflict_id="…"
```

**Why per-key, not whole-doc?** Interior planner user-move-chair-A while
collaborator-moves-chair-B. Whole-doc LWW would erase one chair. Per-key
LWW preserves both.

**Why TG's `message.timestamp`?** MTProto timestamp is sorted via TG's
distributed clock; server-side authoritative. No clock-skew problem
between devices.

---

## Onboarding (concrete UX flow)

1. **First install** — user provides TG account (`tg_terminal_messenger`
   session credentials via `tg_session.session` sqlite3 file).
2. **Create-or-join Sync Group** — user creates **private TG group**,
   invites other devices. Freebuff-side: `RemoteSyncCoordinator` registers
   `SYNC_GROUP_CHAT_ID` (numeric via `client.get_dialogs(limit=500)` matching
   on title or hash).
3. **Initial state push** — on first sync, full snapshot goes to Saved Messages
   (user can inspect, audit).
4. **Steady-state** — debounced delta push every 5s on local edit, real-time
   pull via `TGClient.on(NewMessage)` (Telethon MTProto event listener).

---

## Conflict UI (TG-mediated)

Conflicts surface via Saved Messages as `[CONFLICT***REMOVED***` tagged messages, e.g.:

```
[CONFLICT***REMOVED*** 2026-08-04 12:34:56
remote device: lipgloss-laptop
local version: room_state[kitchen_wall_texture***REMOVED***=beige
remote version: room_state[kitchen_wall_texture***REMOVED***=navy
resolution pending — call /resolve conflict_id=c_8a3f to pick
```

User picks winner via `/resolve conflict_id=c_8a3f pick=remote` TG command
forwarded to Freebuff via `tg_messenger` python module. **CAN-15 fail-loud**
applied: never silently overwrite.

---

## Risk Mitigation (mirrored from ADR-010)

| Risk | Mitigation |
|------|------------|
| TG 4096 char/message | gzip+base64 + chunk at 3500 chars |
| TG 2GB document cap | TG Documents fallback for >2MB blobs |
| TG Bot API rate limits | **TGClient via MTProto** (user-client), not Bot API |
| Multi-device edit conflicts | Per-key LWW (NOT whole-doc), explicit conflict log |
| Privacy / GDPR | Saved Messages = user-only; Sync Group = user-managed; pre-encryption optional |
| TG session unavailable | drop delta + log + retry at next tick (no exception propagation) |
| Network mid-sync disconnect | reconnect with exponential backoff (1s→60s cap) |
| Stale deltas (e.g. 1 week old) | quarantine + manual `/resolve` UI |

---

## Failure modes (CAN-14 honesty: surface, not hide)

- **TG session unavailable** — Freebuff keeps running locally; delta queue
  grows in-memory (bounded 100 entries), and one-shot replays on TG reconnection.
- **Conflicting updates detected** — see Conflict UI section.
- **User removes device from Sync Group** — Freebuff detects via
  `client.get_dialogs` (TG-side membership change) → applies next delta
  from remaining group, no orphan-state recovery needed (rest of group has truth).
- **TG itself goes down** — Freebuff state diverges, user notified via
  in-app banner on next reconnect. No rollover protocol (we DON'T own a backup).

---

## Out of Scope (explicit, not TODO bloat)

- **Bluetooth / USB option A** — deferred to v6.X. Termux Android BT support
  unreliable; community pattern is `termux-api` posture, but lacks generic
  data-socket streaming (only file transfer via OBEX). RFCOMM/L2CAP require
  root or Android-side akwardness. Defer until v6.x.
- **End-to-end encryption via Secret Chats** — TG Secret Chats don't support
  groups, so Sync Group cannot use Secret Chat protocol. User-pre-encryption
  (`encryption: required_pre_encryption` default) is the bootstrap alternative.
- **Persistent local-only fallback** — already covered by `roomStore.ts`
  AsyncStorage. User always has local state available offline.

---

## Cross-Links

- **Decision:** [`docs_10/vision/decision_index.md §ADR-010`***REMOVED***(../../decision_index.md#adr-010-telegram-stored-relay-phase-53)
- **TASK source:** [`TASK.md` §5.3***REMOVED***(../../TASK.md) (Remote Sync spec)
- **TG foundation:** [`core_02/telegram_contract.py`***REMOVED***(../../../core_02/telegram_contract.py)
- **TG-send helper:** [`scripts_01/tg_send_v5570.py`***REMOVED***(../../../scripts_01/tg_send_v5570.py)
- **Distributed agents (intra-process, NOT cross-device):** [`scripts_01/distributed_agents.py`***REMOVED***(../../../scripts_01/distributed_agents.py)
- **ADR-001 (Vision 3.0):** [`docs_10/vision/decision_index.md §ADR-001`***REMOVED***(../../decision_index.md#adr-001-positioning-vision-30)

---

## Lessons inherited

- **CON-23 (directive discrepancy)**: "ping telegram_contract.py /v1/health" was wrong; TG-stored-relay is **state-as-message-payload**, not HTTP. README reflects this lesson by anchoring on TGClient.send_message + receive, not on bot API HTTP routes.
- **CAN-14 honesty**: every failure mode is enumerated, not hidden. `/resolve` UI is fail-loud.
- **CAN-9 round-trip discipline**: any sync coordinator MUST go through real TG round-trip in CI before declaring "shipped" (mirrors `e2e_promt47.py` pattern in `interior_planner_e2e/`).
- **AV-3 (no own servers)**: relay substrate is TG; Freebuff owns zero servers. Adding `/mcp_server` stargate pattern from existing scripts is NOT in scope for §5.3 (avoids scope-creep into MCP-via-TG-pipe).
