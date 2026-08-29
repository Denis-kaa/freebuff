# ADR-010: Phase 5.3 Remote Sync — Telegram-stored Relay (primary), Bluetooth companion deferred to v6.x

**Дата:** 2026-08-03
**Статус:** ✅ Принято
**Контекст:** [TASK.md §5.3***REMOVED***(../../TASK.md) (Remote Sync — синхронизация состояния Freebuff между устройствами / с облаком),
[pompts_11/003_01_buffy_2_agentic_platform.md:497***REMOVED***(../../../pompts_11/003_01_buffy_2_agentic_platform.md) (Phase 5 spec),
[`docs_10/vision/decision_index.md`***REMOVED***(../../vision/decision_index.md) §ADR-010 (phase-grouped navigation index),
[ADR-001***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) (Vision 3.0 — Freebuff як layer over agent runtimes),
[ADR-009***REMOVED***(ADR_009_Consolidation_Promt37_User_Choice_Override.md) (User-Choice Override — precedent for cross-device UX),
[AV-3 invariant***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) (Freebuff owns **no servers** — TG is our relay substrate),
[CAN-3 §5.10***REMOVED***(../../core/ARCHITECTURAL_DEBT.md#510) (TG chat_id resolution: `SAVED_MESSAGES_CHAT_ID=7709651193`, `LITVINOV_CHAT_ID=1063827731`),
[CAN-9 §5.18 + §5.19***REMOVED***(../../core/ARCHITECTURAL_DEBT.md#518-519) (TG round-trip discipline: Saved=138170, Литвинов=138171 via `TGClient.get_messages`)

## Решение

Phase 5.3 Remote Sync uses **Telegram as a *stored-relay* substrate** (TG Saved Messages + private Sync Group chat) with **per-key LWW delta-sync**. Bluetooth/USB peer-to-peer companion **deferred to v6.x** for large binary blobs (>2MB cut-off).

**Option B (Cloud Relay) is primary.** **Option A (Bluetooth/USB) deferred to v6.x.**

## Обоснование

### Option A: Bluetooth/USB — HOSTILE in Termux

Termux Android Bluetooth support is unreliable for generic data-stream
sockets:

- **RFCOMM/L2CAP** require root or complex Java wrappers via `termux-api`
  (which only exposes OBEX file transfer plus system-level BT controls,
  **not** generic data-channel APIs).
- **Pairing UX** adds friction: Android requires user to manually pair
  via Settings UI on first use of each device pair; no Freebuff-side
  automation possible without violating OS-level separation.
- **USB host mode** on Termux/Android is asymmetric (Termux can be USB
  *device*, not host — Desktop host required, contrary to Freebuff's
  mobile-first direction).
- **Discovery maintenance** is a non-trivial engineering cost: how does
  Device A know Device B exists? Manual pairing? Bonjour-like broadcast?
  Beacon? Each path adds 500-2000 lines of code.
- **Conflict resolution** for parallel edits (not whole-doc LWW, but
  per-key merges) requires running either CRDT library (heavy) or a
  custom logic engine (build + test + maintain).

### Option B: Telegram-stored Relay — production-ready, FREE, reusable

- **`core_02/telegram_contract.py::TGClient`** is already production-grade
  (CAN-3 v5.40.0 — chat_id resolution frozen, `report_to_*` helpers
  idempotent, lazy-import safe).
- **`tg_send_v5570.py`** durable TG-send helper (CAN-9 v5.56.0 + v5.59.0
  verified: Saved=138170, Литвинов=138171 fetched via Telethon
  `client.get_messages` round-trip).
- **MTProto event listener** (`Telethon ≥1.36`) supports real-time
  push via `client.on(events.NewMessage)` — **no polling latency**.
- **Zero infrastructure**: Freebuff does NOT own a server (AV-3
  invariant). TG is the substrate.
- **Cross-device zero-friction**: user already has TG on phone, laptop,
  tablet, iOS, web. No pairing ceremony.
- **Designer-persona alignment**: interior designers (Phase 5.3 user
  persona — sibling project `interior_planner_app/`) already informally
  save drafts to TG Saved Messages; productizing that pattern is
  natural-intuitive UX.
- **Pattern consistency**: TG-as-orchestration-substrate established
  since v5.10.0 (TG chat_id resolution), v5.42.0 (TG integration
  contract), v5.51.0+ (TG round-trip discipline).

### Option C: Hybrid — over-engineered for v5.62.0 budget

- Doubles implementation cost (both BT and TG).
- BT is hostile (above).
- Defer until v6.x with actual user demand signal.

## Последствия

### Positive

- **Zero new infrastructure**. TG substrate is on the user's phone
  already. Usable from day 1.
- **Cross-device**, real-time sync with <500ms typical latency (MTProto
  push event listener, no polling).
- **Pattern consistency** with Freebuff's TG-first posturing.
- **Designer-persona UX is intuitive** (Saved Messages as personal
  state relay is a familiar mental model).
- **Schema proven** in CAN-9 v5.56.0 + v5.59.0 + v5.61.0 round-trips.

### Negative

- **TG 4096 char/message limit**: chunk + gzip+base64 envelope at
  3500-char threshold (mitigated via scenario.yaml `chunking` config).
- **TG 2GB document cap**: TG Documents fallback for large blobs (binary
  vectors, 3D model files); somewhat orthogonal but Section 5.3-A
  implements the metadata-relay path; binary companion deferred to v6.x.
- **Privacy**: state lives on TG servers (mitigated: Saved Messages =
  user-only; Sync Group = user-managed; pre-encryption optional via
  `xsalsa20_poly1305` keyed by SYNC_GROUP_CHAT_ID).
- **Server-side storage on TG** is acceptable for non-sensitive data;
  design pattern allows user to gate (no PII by default).
- **Local-first `roomStore.ts` AsyncStorage untouched** — Remote Sync
  is an *overlay*, not a `AsyncStorage` replacement. AsyncStorage remains
  synchronous Source-of-Truth for the UI.

### Risk Mitigation Table

| Risk | Severity | Mitigation |
|------|----------|------------|
| TG 4096 char limit | 🟡 | chunk at 3500 chars; fallback TG document for >2MB |
| TG Bot API rate limits | 🟢 | use TGClient via MTProto (user-client), not Bot API |
| Bluetooth omitted | 🟢 | Termux BT hostile; deferred to v6.x companion |
| Sync conflicts (overlapping edits) | 🟡 | **per-key LWW** (NOT whole-doc LWW); explicit `[CONFLICT***REMOVED***` log + `/resolve` TG cmd |
| Stale deltas (>24h old) | 🟡 | quarantine + manual `/resolve conflict_id=…` UI |
| TG session unavailable | 🟡 | drop delta locally + retry at next debounce tick; bounded queue (max 100) |
| Network mid-sync disconnect | 🟡 | reconnect exponential backoff (1s→60s cap); resume from last-seen-offset |
| GDPR / data-residency | 🟡 | Saved Messages = user-only; Sync Group = user-managed; pre-encryption optional |
| Server-side storage on TG | 🟢 | acceptable for non-PII; design-up allows gating |
| Freebuf Core не запущен | 🟢 | каждый девайс работает independently; no central authority |

## Implementation Anchors

- **Scenario spec:** [`runtime_05/scenarios/19_remote_sync/scenario.yaml`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/scenario.yaml)
- **Operational notes:** [`runtime_05/scenarios/19_remote_sync/README.md`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/README.md)
- **Interface contract (spec-only):** [`runtime_05/scenarios/19_remote_sync/interface.py`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/interface.py)
- **TASK.md §5.3:** [`TASK.md`***REMOVED***(../../TASK.md) (Remote Sync source spec)
- **TG foundation:** [`core_02/telegram_contract.py`***REMOVED***(../../core_02/telegram_contract.py)
- **TG-send helper:** [`scripts_01/tg_send_v5570.py`***REMOVED***(../../scripts_01/tg_send_v5570.py)
- **Distributed agents (intra-process, NOT cross-device — для сравнения):** [`scripts_01/distributed_agents.py`***REMOVED***(../../scripts_01/distributed_agents.py)

## Отложено (после Phase 5.3-B + Phase 6.x)

- **Phase 5.3-A** (this ADR + scenario files): spec-only contracts.
- **Phase 5.3-B** (next release, post-v5.62.0): runtime implementation
  в `core_02/remote_sync.py::RemoteSyncCoordinatorImpl`.
- **Phase 5.3-C**: real TG round-trip e2e via `e2e_logs/remote_sync_<ts>.md`
  (mirrors `e2e_promt47.py` discipline in `interior_planner_e2e/`).
- **Phase 6.x**: Bluetooth companion (`19_remote_sync/bt_companion.py`)
  для large binary blobs (>2MB cut-off) — only if user demand signals.
- **Phase 6.x**: pre-encryption helpers (`19_remote_sync/encryption_xsalsa20.py`)
  — required by `encryption: required_pre_encryption default mode` for
  Sync Group channels but no concrete key-exchange protocol yet.

## Decisions NOT YET made (block on real user demand signal)

- Pre-encryption key exchange: shared-secret via QR-code-scan vs
  out-of-band TG-voice-call? Block on real Sync Group onboarding.
- Stale-delta quarantine threshold: 24h default, but use-case dependent
  (interior_planner might prefer 1h, notebook-research might prefer 7d).
- Conflict UI: TG message-thread-based vs in-app dedicated UI?
  Block on Phase 5.3-B feedback.

## Disciplines applied (forward-looking guard)

- **CAN-14 honesty**: every failure mode enumerated + fail-loud
  surface, not silently dropped.
- **CAN-9 round-trip discipline**: any sync coordinator MUST go through
  real TG round-trip in CI before declaring "shipped" (mirroring
  `e2e_promt47.py` pattern in `interior_planner_e2e/`).
- **CON-8 closed-vocab capabilities**: state-sync | telegram-mtproto-relay
  | delta-resolution | chunked-large-state. NO free-form strings.
- **CON-23 lesson applied**: "ping telegram_contract.py /v1/health" was
  wrong (CON-23 derived from Phase 5.1-B); TG-stored-relay is NOT
  HTTP; it's `state-as-message-payload` via `TGClient.send_message()`.
- **CON-17 anti-duplication**: this ADR cross-references
  `docs_10/vision/decision_index.md` for the vision-grouped view, and
  DECISIONS.md for the canonical index. Detailed text here is the
  authoritative single source.

---

_Связанные документы: [`docs_10/vision/decision_index.md`***REMOVED***(../../vision/decision_index.md) (phase-grouped), [`docs_10/decisions/DECISIONS.md`***REMOVED***(../../decisions/DECISIONS.md) (canonical index), [ADR-001***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md), [ADR-009***REMOVED***(ADR_009_Consolidation_Promt37_User_Choice_Override.md), [Project Book §Phase 5***REMOVED***(../PROJECT_BOOK.md), [TASK.md §5.3***REMOVED***(../../TASK.md)_
