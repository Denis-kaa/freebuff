# Architectural Decision Index — Freebuff (vision/ scope)

**Purpose:** Vision-tier architectural decisions for Freebuff. This file groups
ADRs by **phase / product scope** rather than by **`ADR_NNN` chronologic** order
(the latter is canonical in [`decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md)).

**Hierarchy (canonical supersedes):**
- Source-of-truth: [`docs_10/decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md) — canonical ADR index, never duplicated.
- Authority: [`docs_10/decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md) is the only authoritative ADR registry (consistency_check validates `_ADR_INDEX`).
- This file (`decision_index.md`) is **vision-grouped view** — same ADRs, regrouped under product phases. **Bidirectional cross-link only**; no new ADRs created here without also registering in `DECISIONS.md`.

**Anti-duplication principle (CON-17):** Decision texts live in the canonical ADR files. This file is an **index**, not a copy of rationale.

---

## Quick navigation

- [Phase 1 — Genesis***REMOVED***(#phase-1--genesis)
- [Phase 2 — Protocols***REMOVED***(#phase-2--protocols)
- [Phase 3 — Security pivot***REMOVED***(#phase-3--security-pivot)
- [Phase 4 — Workspace OS***REMOVED***(#phase-4--workspace-os)
- [Phase 5 — User-Facing***REMOVED***(#phase-5--user-facing) (Flutter UI, FG Service, **Remote Sync**)
- [Phase 6 — Deferred v6.x***REMOVED***(#phase-6--deferred-v6x)

---

## Phase 1 — Genesis

### ADR-001 — Positioning (Vision 3.0)

**Date:** 2026-07-28 · **Status:** ✅ Accepted
**One-liner:** Freebuff is a **layer over existing agent runtimes**, not a competitor — postured as the protocol/wrapper that adds Memory/Registry/Policy around raw LLM APIs.
**Detail:** [`docs_10/engineering-memory/decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md`***REMOVED***(../engineering-memory/decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) · **Canonical row:** [`decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md)

---

## Phase 2 — Protocols

### ADR-002 — JSON Contracts (vs binary gRPC/protobuf)

**Date:** 2026-07-29 · **Status:** ✅ Accepted
**One-liner:** All Freebuff <-> runtime / Freebuff <-> MCP / Freebuff <-> Telegram interfaces use JSON contracts (text-readable, debuggable, version-tolerant). gRPC is reserved for performance-critical experimental paths only.
**Detail:** [`docs_10/vision/VISION_3.0.md` §6***REMOVED***(../vision/VISION_3.0.md#6-interfaces-and-contracts) · **Canonical row:** [`decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md)

---

## Phase 3 — Security pivot

### ADR-003 — Drop `shell=True`, `exec`, `os.system`

**Date:** 2026-07-30 · **Status:** ✅ Accepted
**One-liner:** Freebuff never invokes shell with user input. All subprocess work uses `subprocess.run(args=[...***REMOVED***, shell=False)` with leaked arg whitelist (validated upstream by `verifier.py`).

### ADR-004 — Bearer auth mandatory on internal HTTP endpoints

**Date:** 2026-07-31 · **Status:** ✅ Accepted
**One-liner:** All Freebuff HTTP endpoints (mcp_server, capability registry) require `Authorization: Bearer <token>`. Anonymous requests return 401 with diagnostic.

### ADR-005 — Synchronous verification (`py_compile --force`) before every TG-send

**Date:** 2026-07-31 · **Status:** ✅ Accepted (CAN-14 lesson)
**One-liner:** TG-send messages advertising "release complete" require a `release.success` flag written atomically AFTER verify-gate; without flag, TG broadcast deferred.

---

## Phase 4 — Workspace OS

### ADR-006 — Lightpanda integration (deprecated path)

**Date:** 2026-07-28 · **Status:** ✅ Accepted (now superseded by ADR-006.1 below)
**Original:** Lightpanda headless browser for fast MCP-tool smoke tests.

### ADR-006.1 — Lightpanda DEPRECATED in favor of direct MCP round-trip

**Date:** 2026-08-02 · **Status:** ✅ Accepted
**One-liner:** Direct MCP round-trip via `subprocess.run(["mcp", "tools/list"***REMOVED***)` is the canonical verification path. Lightpanda retained for legacy compat-shim only.

### ADR-007 — Workspace OS consolidation (Phase 4 docs → ops split)

**Date:** 2026-07-31 · **Status:** ✅ Accepted
**Canonical row:** [`decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md)

### ADR-008 — DPE realization deferred; principles absorbed into GLOSSARY §11 + MANIFEST §4

**Date:** 2026-08-01 · **Status:** ✅ Accepted

### ADR-009 — User-Choice Override (Rule 11)

**Date:** 2026-08-01 · **Status:** ✅ Accepted
**One-liner:** When user-given instruction contradicts canonical ARCHITECTURE_MANIFEST rules, the **user instruction wins** unless it would violate a hard safety invariant (shell-exec, etc.). Scope-rule precedence: USER > SCENARIO > MANIFEST.
**Detail:** [`docs_10/engineering-memory/decisions/ADR_009_User_Choice_Override.md`***REMOVED***(../engineering-memory/decisions/ADR_009_User_Choice_Override.md) · **Canonical row:** [`decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md)

---

## Phase 5 — User-Facing

### 5.1 Flutter UI App

**Status:** Scaffold complete (Phase 5.1-A, 2026-08-03). Heartbeat executor live (Phase 5.1-B). APK build envelope pending (Phase 5.1-C).
**Detail:** [`projects_17/freebuff_flutter_app/`***REMOVED***(../../projects_17/freebuff_flutter_app/)

### 5.2 Android Foreground Service

**Status:** Spec defined. Native `PARTIAL_WAKE_LOCK` (Phase 5.1-B). Phantom Process Killer hardening pending.

### 5.3 Remote Sync

**→ See ADR-010 below.**

---

## Phase 6 — Deferred v6.x

- Bluetooth/USB peer-to-peer companion (deferred from Phase 5.3, see ADR-010 risk-mitigation table).
- Full CRDT library (CRDT-lite suffices for interior_planner use case; revisit if scope expands).
- Persistent `Freebuff-Cloud` (we explicitly DO NOT own hosting; AV-3 invariant).

---

## ADR-010 — Telegram-stored Relay (Phase 5.3)

**Date:** 2026-08-03 (lifecycle matching `v5.62.0` roadmap cycle) · **Status:** ✅ Accepted
**One-liner:** Phase 5.3 Remote Sync uses Telegram as a *stored-relay* substrate (TG Saved Messages + private Sync Group channel), with per-key LWW delta-sync. Bluetooth/USB companion deferred to v6.x.

### Context

Freebuff states are increasingly cross-device (interior designer drafts on
phone, reviews on laptop, tests on emulator). Without sync, devices diverge.
Phase 5.3 Remote Sync closes this gap. Two options were evaluated:

- **Option A — Peer-to-Peer (Bluetooth/USB).**
- **Option B — Cloud Relay (Telegram-stored Relay).**
- **Option C — Hybrid.** (broke engineering budget: doubled implementation cost)

### Decision

**Option B is the primary interface. Option A deferred to v6.x as
companion fast-path for large binaries (e.g., 3D model files).**

### Rationale (driving factors)

1. **Existing TG infrastructure is production-grade.** `core_02/telegram_contract.py::TGClient` (CAN-3 v5.40.0) already resolves `SAVED_MESSAGES_CHAT_ID=7709651193` + `LITVINOV_CHAT_ID=1063827731`. `tg_send_v5570.py` (CAN-9 v5.56.0 + v5.59.0) proven via real Telethon `client.get_messages` round-trip (Saved=138170, Литвинов=138171 verified).
2. **Termux Android Bluetooth support is hostile.** RFCOMM/L2CAP requires root. `termux-api` provides OBEX file transfer but lacks generic data-stream sockets. Pairing UX adds friction; cross-device discovery is a maintenance burden.
3. **Time-to-value.** TG-stored-relay uses 1 substrate (TGClient); BT would require auth+pairing+conflict resolution+OBEX/MTP = 5-10x more code.
4. **Designer-persona alignment.** Interior designers already informally save drafts to TG Saved Messages. Productizing that workflow is natural.
5. **AV-3 invariant — "Freebuff owns no servers".** TG is the substrate. Mirrors our existing TG-as-orchestration-substrate pattern.
6. **Schema-proven substrate.** MTProto (Telethon) supports real-time event listeners (`client.on(events.NewMessage)`) — no polling latency.

### Consequences

**Positive:**
- Zero new infrastructure to stand up.
- Cross-device zero-friction (TG on phone, laptop, tablet, web — user already has them).
- Real-time sync via MTProto event listener — latency typically **<500ms when device is awake and online**; worst case minutes on doze-mode / background devices reconnecting (TG push delivery is server-best-effort, NOT Freebuff-controlled).
- Architecture consistency (TG-first pattern established since v5.10.0).
- Designer-persona UX is intuitive (Saved Messages = user-owned state).

**Negative:**
- TG 4096 char/message limit (mitigated: chunk + gzip+base64 envelope at 3500-char threshold).
- TG 2GB document cap (mitigated: TG Documents fallback for large blobs; binary vectors).
- Privacy: state lives on TG servers (mitigated: Saved Messages = user-only; Sync Group = user-managed; pre-encryption optional via xsalsa20_poly1305).
- Polling NOT needed (MTProto listener), but TG-client disconnect handling is the main robustness concern (mitigated: reconnect-with-exponential-backoff loop, drops no deltas).
- Local-first `roomStore.ts` (AsyncStorage) untouched — see §Consumer below.

### Risk Mitigation Table (pointer-only per CON-17 anti-duplication)

**For full table + discussion, see [`engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md` §Risk Mitigation Table***REMOVED***(../engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md#risk-mitigation-table)** (canonical authoritative source; navigation view intentionally does NOT re-list mitigations to avoid drift per CON-27).

### Implementation Anchors

- **Scenario spec:** [`runtime_05/scenarios/19_remote_sync/scenario.yaml`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/scenario.yaml)
- **Operational notes:** [`runtime_05/scenarios/19_remote_sync/README.md`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/README.md)
- **Interface contract:** [`runtime_05/scenarios/19_remote_sync/interface.py`***REMOVED***(../../runtime_05/scenarios/19_remote_sync/interface.py)
- **TASK.md §5.3:** [`TASK.md`***REMOVED***(../tasks.md cross-link) (Remote Sync source spec)
- **TG foundation:** [`core_02/telegram_contract.py`***REMOVED***(../../core_02/telegram_contract.py)

### Follow-Up (not in this ADR scope, but tracked)

- Phase 5.3-B: implementation (`core_02/remote_sync.py::RemoteSyncCoordinatorImpl`).
- Phase 5.3-C: real TG round-trip e2e via `e2e_logs/remote_sync_<ts>.md` (mirrors `e2e_promt47.py` discipline in `interior_planner_e2e/`).
- Phase 6.x: Bluetooth companion (`19_remote_sync/bt_companion.py`) for large binary blobs (>2MB cut-off).
- Phase 6.x: pre-encryption helpers (`19_remote_sync/encryption_xsalsa20.py`).

---

## Cross-discipline summary

| Topic | Decision |
|-------|----------|
| API contracts | ADR-002 (JSON everywhere; gRPC exception) |
| Vision positioning | ADR-001 (layer over agent runtimes, not competitor) |
| Security baseline | ADR-003 + ADR-004 + ADR-005 |
| Workspace OS structure | ADR-007 + ADR-008 + ADR-009 |
| Cross-device sync | **ADR-010 (TG-stored relay primary; BT deferred)** |

---

_Anti-duplication: This index file groups ADRs by phase. The canonical decision text lives in [`docs_10/decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md) and detailed ADR files under `engineering-memory/decisions/`. Visual organization here is for navigation only._

- **ADR-011:** Phase 5.3-D Realtime Listener & TGClient Fork Strategy (`docs_10/engineering-memory/decisions/ADR_011_Phase_5_3_D_Listener_Loop.md`, status: Accepted)
