## [5.67.0***REMOVED*** — 2026-08-03

### Added (Phase 5.3-E Persistent Realtime Listener Loop — RemoteSyncListener)

- **`core_02/remote_sync.py::RemoteSyncListener._listener_loop()`** — persistent
  asyncio.Task-based LWW resolve cycle: sleep 1s → drain_incoming() → for each
  envelope: decode JSON → `_apply_remote_envelope()` to coordinator → if buffer
  non-empty: `pull_state()` (reconnect guard).
- **Lifecycle wiring**: `start()` spawns `_listener_loop` as `asyncio.ensure_future`;
  `stop()` cancels with 5s timeout + drains buffer + removes event handler.
- **Resilience**: malformed envelopes (JSON decode error) logged and skipped;
  `CancelledError` propagated; generic exceptions logged, loop continues.
- **pull_state gating**: only called when buffer was non-empty (avoids expensive
  TG API calls on idle cycles).
- **`tests_09/test_remote_sync_listener.py`** — 13 tests: lifecycle (start/stop
  task, stop idempotent), event dispatch (push, ignore non-marker, drain),
  listener loop (drain→apply, pull_state on non-empty, skip on empty),
  buffer overflow (maxlen=128), malformed envelope resilience, LWW resolve.

### Verify Gate (2026-08-03)

- **py_compile**: `remote_sync.py`, `test_remote_sync_listener.py` — all OK.
- **pytest** (13 tests): 13/13 PASS.
- **Regression**: `test_remote_sync.py` (26/26), `test_tg_client_v2.py` (8/8) — all green.
- **Cold import**: RemoteSyncListener import OK.
- **drift_check + consistency_check**: pre-existing minor warnings (unchanged).

---

## [5.66.0***REMOVED*** — 2026-08-03

### Added (Phase 5.3-D DEBT-5.21 close — TGClientV2 fork)

- **`core_02/_tg_client_v2.py::TGClientV2`** — CON-31 resolution: new thin wrapper exposing
  `add_event_handler(callback, event)`, `remove_event_handler(callback, event)`, and
  `get_messages(entity, limit=5, ids=None)` with `ids=` kwarg (delegates to telethon's native
  `ids=` param, eliminating the limit-scan + client-side filter pivot). Wraps (not extends)
  upstream `projects_17/tg_terminal_messenger` boundary per ADR-011 Option 3.
- **`RemoteSyncListener.start()`** wired to use `TGClientV2` with real `events.NewMessage`
  handler (sync callback per N-1 fix — Telethon does NOT await coroutines).
- **`RemoteSyncListener._on_new_message()`** — real hot-path callback: validates
  `##FB_STATE##` marker, pushes `(msg_id, envelope_bytes)` into `_incoming_buffer`.
- **`tests_09/test_tg_client_v2.py`** — 8 tests covering: `get_messages` with `ids=` kwarg,
  fallback to limit-scan, single-int `ids`, `add_event_handler`, `remove_event_handler`,
  multiple independent handlers, handler error resilience, lifecycle delegation
  (connect/disconnect/send_message/get_me).
- **`core_02/LESSONS.md` CON-31 entry updated** — resolved status with full resolution path.

### Verify Gate (2026-08-03)

- **py_compile**: `_tg_client_v2.py`, `remote_sync.py`, `test_tg_client_v2.py` — all OK.
- **pytest tests_09/test_tg_client_v2.py**: 8/8 PASS in 0.93s.
- **Cold import**: TGClientV2 imports correctly from `core_02._tg_client_v2`.
- **drift_check + consistency_check**: exit 0 (pre-existing minor warnings unchanged).

---

## [5.65.0***REMOVED*** — 2026-08-03

### Added (Phase 5.3-D Listener Loop Pre-work)

- **`core_02/remote_sync.py::RemoteSyncListener` scaffold** — persistent `TGClient.on(events.NewMessage)`
  realtime event-listener interface (Phase 5.3-D hot-path). Lifecycle: `start()/stop()/drain_incoming()`;
  `_incoming_buffer` = `collections.deque(maxlen=128)`; `_source_chat_ids` hardcoded (Saved 7709651193 +
  Литвинов 1063827731). Real body deferred to DEBT-5.21 closure PR (next session).
- **ARCHITECTURAL_DEBT §5.21** — new OPEN entry tracking cross-project dependency: `core_02/_tg_client_v2.py`
  TGClient fork needed to expose `add_event_handler` + `ids=` kwarg on `get_messages` (CON-31 gap).
- **ADR-011** — `docs_10/engineering-memory/decisions/ADR_011_Phase_5_3_D_Listener_Loop.md`: Option 3
  (Core Fork) SELECTED; 4 options evaluated; 5 decision drivers; forward-looking guards (memory leak via
  deque maxlen, reconnect via pull_state recovery, asyncio loop boundary).
- **`docs_10/vision/decision_index.md`** — ADR-011 registered (Accepted).

### Version-drift closure (v5.62.0 → v5.65.0)

- **AGENTS.md** + **BUFFY_PROJECT.md** bumped to **v5.65.0** (were stale at v5.62.0; closes drift from
  v5.63.0 / v5.64.0 era). CHANGELOG canonical version now v5.65.0.

### Discipline note (CON-NEW, forward-looking guard)

- **`path.write_text()` is NOT atomic on `UnicodeEncodeError`** — during v5.64.0 session, ARCHITECTURAL_DEBT.md
  was truncated to 2,003 bytes (was 68,455) by a partial write. Recovery: `git checkout HEAD -- <file>`. Future
  large-doc writes should use atomic-rename via `tempfile.NamedTemporaryFile` + `os.replace()`. Tracked for
  LESSONS.md follow-up.

### Verify Gate (2026-08-03)

- py_compile `core_02/remote_sync.py` → exit 0.
- pytest `tests_09/` collection → 2060 tests (target 2059+, +1 from N-P3 integration test).
- drift_check + consistency_check → stable (1 pre-existing test-count warning 1991→2041, non-blocking).
- Code-reviewer: APPROVE-WITH-NITS (N-1 async handler / N-2 hardcoded chat_ids / N-3 write non-atomicity
  — all deferred to DEBT-5.21 closure PR per ADR-011 implementation plan).

---


## [5.64.0***REMOVED*** — 2026-08-03

### Verified (Phase 5.3-C Remote Sync Gate D — real TG round-trip)

- **Cumulative harness audit-trail extension**: real `--client --silent` end-to-end прогон через архітектурно-viable путь `core_02/remote_sync.py::RemoteSyncCoordinatorImpl` + `core_02/telegram_contract.py::report_to_saved_messages`/`report_to_alex_litvinov`. **Saved Messages** (chat_id=**7709651193**): msg_id=**138366**, retrieved via `TGClient.get_messages(7709651193, limit=100)` limit-scan + client-side filter (CON-31 pivot), non-empty text, real TG history ✓. **А. Литвинов** (chat_id=**1063827731**): msg_id=**138367**, retrieved via `TGClient.get_messages(1063827731, limit=100)` limit-scan + client-side filter, non-empty text, real TG history ✓. Both messages contain canonical `##FB_STATE##` marker (programmatically generated by `RemoteSyncCoordinatorImpl.push_state()` as part of StateV2a SyncDelta payload body field — used by Stage 3 round-trip verification to distinguish real state syncs from echo/control/test артефактов; discovery-pattern per CON-35).
- **Cumulative audit-trail (CAN-9 anchor в `docs_10/e2e_logs/promt47_run.md` ## Historical Verification Runs):** v5.45 137901/137902 → v5.46.0 138040/138042 → v5.47.0 138044/138045 → v5.49-50 138047/138048 → v5.56.0 138128/138129 → v5.56.1 138130/138131 → v5.59.0 138170/138171 → **v5.64.0 138366/138367** (this release).
- **Anti-rewriting (CAN-17) соблюдено**: все 7 prior rows в audit-trail preserved в неизменном виде; v5.64.0 row added at TOP of section per codebase's append-to-top convention (verified by `basher` actual-file-structure read).
- **TGClient×API pivot (CON-31)**: physical `get_messages(chat_id, limit=N)` + client-side `id` filter — not `ids=` kwarg which TGClient wrapper не поддержує.

### Verified Gate (2026-08-03 real run)

- **Pre-flight (Stage 0, --skip-tg CHECK-only)**: TG session alive (`projects_17/tg_terminal_messenger/tg_session.session`, sqlite entities кэш валидний), `core_02.remote_sync` + `core_02.telegram_contract` importable через `_freebuff_locator.resolve_freebuff_root()` без PYTHONPATH, API surface (push_state + pull_state + resolve_conflict + quarantine + register_device + shutdown) accessible.
- **Real TG side-effects** (--sync-group --silent): `python3 scripts_01/e2e_remote_sync.py --sync-group --silent --run-tag phase_5_3_c_gate_d_real_v5_64_0` → exit 0.
- **Round-trip (Stage 3, native `TGClient.get_messages`)**: Saved + Литвинов both retrieved, non-empty text, real TG history. Script-native Stage 3 (per-loggger `##FB_STATE##` marker pattern) sufficient — no separate side-script required (thinker correction #1).
- **Audit-trail**: new Run row prepended at TOP of `## Historical Verification Runs` section; 7 prior rows intact (CAN-17 verified by basher `awk` section dump).
- **drift_check**: exit 0 (No discrepancies).
- **consistency_check**: exit 0 (1 pre-existing CAN-10 naming warning — не входит в scope v5.64.0).

### Lesson (NEW)

- **CON-35 (Phase 5.3-C Live TG Validation + CAN-17 append direction)**: First real `--sync-group --silent` end-to-end TG round-trip validates Phase 5.3-C Gate D. Relying on script-native Stage 3 `TGClient.get_messages(limit=100)` limit-scan proved sufficient for read-back verification without needing standalone side-script (per thinker correction). **Additionally**: `##FB_STATE##` marker in TG message body establishes canonical round-trip detection pattern. **Crucially**: CAN-17 anti-rewriting in `## Historical Verification Runs` is `append-to-TOP` (verified from actual file structure — contradicts initial thinker position of BOTTOM-append). For future real TG round-trips: anchor on `## Historical Verification Runs` and prepend immediately after the header.

### Code review

- **Pending**: `code-reviewer-minimax-m3` review (concurrent with ship-gate, this turn). Self-grading-claim запрещено в CHANGELOG до verdict — этот раздел оставлен placeholder до explicit APPROVE/WITH-NITS verdict от code-reviewer.

---


## [5.63.0***REMOVED*** — 2026-08-03

### Phase 5.1-B Heartbeat Executor (Flutter Scaffold body — v5.63.0 refinement)

- **`FreebuffForegroundService.kt` canonical impl (v5.63.0)** — заменён stub `onStartCommand` на реальный heartbeat executor. Реализует все 3 компоненты user-spec:
  1. **Heartbeat executor (stdlib-only)**: `ScheduledExecutorService.scheduleWithFixedDelay(::tick, 0L, HEARTBEAT_INTERVAL_MS=30_000, MILLISECONDS)` + `HttpURLConnection GET http://127.0.0.1:8765/` каждые 30s. Парсит JSON body `{"status":"ok",...***REMOVED***` либо фиксирует ошибку. **3 quick-retry с 2s backoff** (CON-23 discipline) перед тем как пометить notification как `down`.
  2. **WakeLockPlus-equivalent native manifest** (MethodChannel bridge comment-out; 1 первый starred на `_freebuff_locator`-equivalent pattern). В Kotlin — native `PowerManager.newWakeLock(PARTIAL_WAKE_LOCK, "Freebuff:ForegroundService")` в `onStartCommand` + `acquire(3_600_000L /* 1h */)` belt-and-suspenders + `release()` в `onDestroy` под try-finally. (Flutter plugin `WakelockPlus.enable()` будет вызываться через MethodChannel bridge из Flutter UI слоя; Kotlin native stub гарантирует независимость от Flutter binding races.)
  3. **Notification update loop** — `setOnlyAlertOnce(true)` + silent content update через `Notification.Builder(...)` (modern API; v5.60.0 зафиксировал: `setLatestEventInfo` deprecated в API 23+; используем `setContentText` equivalent). Текст: `Last ping HH:MM:SS • healthy` или `down` после 3-retry failure. `notify(NOTIFICATION_ID, buildNotification(...))` на каждом tick — без heads-up re-fire.
- **Lifecycle correctness**: `executor.shutdownNow()` + `wakeLock?.release()` в `onDestroy` под try-finally — foreground service не держит ресурсы после STOP. `START_STICKY` return чтобы система перезапускала service при OOM kill.
- **`scripts_01/mcp_fastapi.py` `GET /` health endpoint** — используется (как canonical substrate для heartbeat ping); v5.60.0 fixed ping target изначально указывал `core_02/telegram_contract.py /v1/health` (которого не существует) — CON-23 lesson applied.

### Lesson (refinement of CON-23)

- **CON-23.1 (Flutter plugin ↔ Kotlin native binding boundary)**: Flutter `WakelockPlus` plugin operates via MethodChannel. Pure-Kotlin stub должен использовать **native `PowerManager.newWakeLock`** для гарантии того, что foreground service `onStartCommand` не зависит от Flutter binding state. Реальный "WakelockPlus-equivalent" behavior — нативный wake lock; Flutter binding bridge добавляется поверх только когда UI слой хочет visual feedback (e.g., "Device awake" badge).

### Known Limitations (deferred)

- **Flutter `WakelockPlus.enable()` не вызывается напрямую** — MethodChannel bridge — out of Phase 5.1-B scope (Flutter UI binding layer separately).
- **`setLatestEventInfo` API deprecated (API 23+)** — используем `Notification.Builder.setContentText` equivalent, который имеет идентичное visual output. Polar пользовательский use case „Direct setLast..." notes added в code review публичных comments.
- **Real-time heartbeat тестирование** отложен: требует `scripts_01/mcp_fastapi.py` запущенного на `127.0.0.1:8765`. CI тесты остаются через статические method-name assertions.

### Code review

- `code-reviewer-minimax-m3` (parallel with verify): modern Android API compliance (Notification.Builder vs deprecated setLatestEventInfo explicitly documented), WakeLockPlus native stub vs MethodChannel bridge distinction clear (CON-34), 1h acquire belt-and-suspenders timeout pattern matches v5.60.0 baseline. APPROVE ship-ready.

---

# Changelog

> Все значимые изменения в проекте Freebuff фиксируются в этом файле.
> Формат: [Keep a Changelog***REMOVED***(https://keepachangelog.com/en/1.1.0/),
> версионирование: [Semantic Versioning***REMOVED***(https://semver.org/spec/v2.0.0.html).

---


## [5.62.2***REMOVED*** — 2026-08-03

### Добавлено (Phase 5.3-C real TG round-trip runner)

- **`scripts_01/e2e_remote_sync.py` (NEW, ~430 lines)** — Phase 5.3-C real-TG round-trip runner mirroring `e2e_promt47.py` discipline. 4-stage pipeline: Stage 0 (pre-flight CHECK-only) → Stage 1 (SyncDelta planning) → Stage 2 (push via `RemoteSyncCoordinatorImpl`) → Stage 3 (round-trip via `TGClient.get_messages`). Per-run timestamped log file `docs_10/e2e_logs/remote_sync_<UTC-TS>.md` honoring user directive `<timestamp>`.
- **Dual-channel** via `--sync-group` flag: Saved Messages (mandatory, CAN-3 v5.40.0 chat_id 7709651193) + Литвинов (optional, ALEX_LITVINOV_CHAT_ID 1063827731 — SYNC_GROUP fallback per CON-26 pending_resolve). Saved=msg_id_X + Литвинов=msg_id_X+1 captured from Stage 2 push.
- **CAN-9 round-trip discipline** verified via `TGClient.get_messages(chat_id, limit=100)` + client-side filter `next(m for m in recent if m.id == saved_msg_id)` then text non-empty check. Mirrors `tg_send_v5570.py::round_trip_verify` pattern.
- **CLI flags** (`--silent --skip-tg --sync-group --dry-run --e2e-log PATH --run-tag TEXT`): mirror `e2e_promt47.py` discipline + remote-sync-specific additions. Exit 0 = PASS/skipped, Exit 1 = FAIL (round-trip mismatch).
- **TGClient.get_messages pivot** (CRITICAL pre-flight discovery): TGClient wrapper signature `(entity, limit=5)` — does NOT expose `ids=` kwarg (Telethon-native). PIVOTED stage3_round_trip to limit-scan + filter pattern, matching Phase 5.3-B `_history_via_tgclient`. Tradeoff: 1 TG roundtrip + ~100 msgs scan per verify (acceptable for cold-path verify; hot-path listener loop in Phase 5.3-D would need `ids=` support).
- **`write_e2e_log` markdown writer**: structured sections (Run banner + Stage 0 table + Stage 1 delta summary + Stage 2 push table + Stage 3 round-trip + Bugs (when present) + Summary + Exit code). Per-run file isolation (CAN-16 anti-rewriting ruled per-file). Markdown table cells escaped via `_table_escape()` helper — sanitizes `|` and `\` chars to prevent silent table-break (code-reviewer N-B2 fix).
- **Pre-flight Check** (zero TG side-effects): TG session alive (`TGClient.connect() + get_me()`), `core_02.remote_sync.RemoteSyncCoordinatorImpl` importable, log-dir writable. Failure short-circuits before any push/write.
- **Dry-run mode** (`--dry-run`): builds content + log-only, returns synthetic `DRY_RUN` msg_ids. Lets user verify log structure before committing real TG side-effects.

### Tests

- **`tests_09/test_e2e_remote_sync.py` (NEW, 14 mock-based tests, all passing 7.52s)**:
  1. **Stage 0** (3 tests): log_dir writable (tmp_path fixture), skip-tg no TG call, core_02 import.
  2. **Stage 1** (2 tests): unique round_ids (UUID-derived), sync_group mode selection.
  3. **Stage 2** (3 tests): dry-run synthetic msg_ids, dual-channel w/ sync_group, single-channel w/o sync_group.
  4. **Stage 3** (3 tests): dry-run synthetic, limit-scan happy path (FakeTGClient w/ msg_id in history), limit-scan empty (msg_id NOT in recent 100 msgs).
  5. **`write_e2e_log`** (3 tests): happy path (all section headers + ✅ PASS badge + msg_id rendered), skip-tg truncation (Stage 1-3 NOT emitted), bugs section (round-trip fail populated).
- **pytest totals**: 1991 → 2059 (basher Gate G confirmed; pre-existing test_counter doc lag inherited from v5.61.0 polish items - CHANGELOG counter under-shoots actual count).

### Architectural decisions documented

- **CON-31 (TGClient.get_messages pivot discipline)**: при verification-gate обнаружил mismatch — TGClient wrapper signature `(entity, limit=5)` не expose `ids=` kwarg. Pivoted mid-PR to limit-scan + client-side filter. Lesson: at verify-gate, ENUMERATE actual external API signatures BEFORE assuming telethon-native patterns. Hot-path listener in Phase 5.3-D will likely need TGClient.py fork for `ids=` support.
- **CON-32 (per-run log file vs splice-append)**: chose per-run file isolation over splice-append (which promt47_run.md uses) because user directive literal `<timestamp>` placeholder. Cross-run comparison via `ls -lt docs_10/e2e_logs/remote_sync_*.md`. Trade-off: no in-file audit-trail — solved by chronological filenames. Splice-append rejected to avoid horizontal expansion of single log file across many runs.
- **CON-33 (markdown table `|` sanitization)**: TG error strings can contain `|` (e.g., telethon tracebacks) which break markdown table structure silently. N-B2 fix applies `_table_escape()` to all `error` cells before insertion.

### Verify Gate (2026-08-03 final)

- **Gate A (py_compile)**: 3/3 files OK (`scripts_01/e2e_remote_sync.py` + `tests_09/test_e2e_remote_sync.py` + `runtime_05/scenarios/19_remote_sync/interface.py`). ✔
- **Gate B (--skip-tg pre-flight)**: exit 0, log generated at `docs_10/e2e_logs/remote_sync_<TS>.md`. ✔
- **Gate C (--dry-run --sync-group)**: exit 0, dry-run log generated + verified head structure. ✔
- **Gate D (pytest FULL RUN)**: `python3 -m pytest tests_09/test_e2e_remote_sync.py -v --tb=short` → **14/14 pass in 7.52s**. ✔
- **Gate E (drift_check)**: cached/skipped (already ran today). ✔
- **Gate F (consistency_check)**: 2 pre-existing items (test_counter doc lag 1991→2041+ actual — inherited from v5.61.0 polish items, NOT introduced by v5.62.2). ✔
- **Gate G (full tests_09 collection)**: **2059 tests collected** (no regressions from prior). ✔
- **Gate H (log markdown structure spot-check)**: head 50 lines of dry-run log render correctly with ✅ PASS status. ✔
- **Code-reviewer-minimax-m3**: APPROVE-WITH-NITS (N-B1 auto-resolved by Gate D; N-B2 fixed pre-ship; N-P1..N-P4 polish-deferrable).

### Known Limitations (deferred)

- **`TGClient.get_messages` lacks `ids=` kwarg**: limit-scan (1 roundtrip + ~100 msgs scan) is cold-path-friendly but suboptimal for hot-path. Phase 5.3-D listener loop ТРЕБУЕТ TGClient.py fork to expose `ids=` — separate scope, tracked as cross-project debt (TGClient lives in `projects_17/tg_terminal_messenger`).
- **Race risk in dual-channel push**: Stage 2 spawns two separate `RemoteSyncCoordinatorImpl` instances (one per channel) and awaits sequentially. If Saved succeeds (msg_id_X captured) but Литвинов fails due to TG rate-limit (msg_id_X+1 = None), stage3 round-trip for Литвинов returns `lit_msg_text_non_empty: None` (indeterminate). Behavior is fail-loud but unclear to reader. Future improvement: explicit verdict note in stage3 + retry-on-fail policy.
- **Hardcoded `limit=100` scan window**: for Saved Messages with >100 msgs/hour (active users), the freshly-pushed msg could fall outside the limit-scan window, returning False. Mitigations enable in v6.x: bump to `limit=200`, expose `_ROUND_TRIP_SCAN_LIMIT` constant, OR TGClient.py `ids=` support (above).

### Real TG Round-Trip Ledger (Phase 5.3-C)

- v5.62.2 e2e runner committed; first real-TG round-trip invocation is shipped-ready, awaiting operator (TG session must be alive + `python3 scripts_01/e2e_remote_sync.py --sync-group --silent` invocation).
- Cumulative harness audit-trail (Saved/Литвинов per release, extended from CAN-9 v5.59.0): v5.45 137901/137902 → v5.46.0 138040/138042 → v5.47.0 138044/138045 → v5.49-50 138047/138048 → v5.56.0 138128/138129 → v5.56.1 138130/138131 → v5.59.0 138170/138171 → **Phase 5.3-C v5.62.2 next (pending operator invocation)**.
- Anti-rewriting (CAN-17) preserved — 7 prior msg_ids intact, v5.62.2 only appends "Phase 5.3-C v5.62.2 next" entry. Source-of-truth for msg_ids remains `docs_10/e2e_logs/remote_sync_<TS>.md` (per-run file isolation, CAN-16).

### Code review

- `code-reviewer-minimax-m3` (this turn, parallel with verify): TGClient.get_messages pivot correct pragmatically (limit-scan matches Phase 5.3-B `_history_via_tgclient` pattern); per-run log files honor user directive verbatim; CAN-9 round-trip discipline preserved (real `TGClient.get_messages`, NOT synthetic). N-B2 markdown `|` sanitization fixed pre-ship. N-P1..N-P4 polish-deferrable (Race risk, default_limit, integration test, hardcoded path). **APPROVE-WITH-NITS ship-ready post-N-B2-fix**.

---


## [5.62.1***REMOVED*** — 2026-08-03

### Добавлено (Phase 5.3-B Remote Sync runtime)

- **`core_02/remote_sync.py` (NEW, ~625 lines)** — `RemoteSyncCoordinatorImpl` runtime implementing Phase 5.3-A spec contract (`runtime_05/scenarios/19_remote_sync/interface.py::RemoteSyncCoordinator` Protocol). Реализует все 6 pub-методов спеки: `push_state()`, `pull_state()`, `resolve_conflict()`, `quarantine()`, `register_device()`, `shutdown()` + `capabilities()` для closed-vocab report.
- **TG integration via function-based API**: re-uses `core_02/telegram_contract.py::report_to_saved_messages` / `report_to_alex_litvinov` для sends (CAN-3 v5.40.0 chat_ids verified). Lazy-imports `projects_17/tg_terminal_messenger.TGClient` ТОЛЬКО для `get_me()` / `get_history()` (не exposed через `telegram_contract`). Injectable `SendFn / HistoryFn / MeFn` async hooks для mock-based tests (no real TG session в CI).
- **Interface-spec import через `importlib.util`**: directory `19_remote_sync/` имеет digit-prefix → Python dotted-notion import fails. Workaround: `spec_from_file_location("remote_sync_interface", `_INTERFACE_PATH)` + manual `sys.modules["remote_sync_interface"***REMOVED*** = _interface_mod` registration (CRITICAL для dataclass introspection — `cls.__module__` lookup in `sys.modules.__dict__`).
- **Per-key LWW algorithm**: `_lww_merge_per_key()` canonical impl + `resolve_conflict()` 4 modes (LWW_PER_KEY canonical, WHOLE_DOC_LWW legacy, MANUAL, QUARANTINE). Deterministic tie-break keeps local (avoid flapping on shared-clock-drift edits).
- **Chunking + serialization**: `_chunk_envelope_payload()` 3500-char primary chunks + gzip_base64 fallback для >2MB envelopes. Marker format `##FB_STATE## V1.0.0 <correlation_id> CHUNK i/N` — TG-parseable через `client.on(NewMessage)` event listener (Phase 5.3-C).
- **Quarantine buffer** bounded `deque[SyncEnvelope***REMOVED***` maxlen=1000 (CON-21 policy), 24h age cutoff (per scenario.yaml). Certificate per-key-timestamp loss explicitly documented (CAN-14 fail-loud: limitation, not silent).
- **Capability closed-vocab (CON-8)**: 4 tokens `state-sync | telegram-mtproto-relay | delta-resolution | chunked-large-state`. `capabilities()` returns immutable `frozenset` (prevents caller mutation of global closed-set).
- **FAIL-LOUD per CAN-14**: structured `{"ok": False/True, "error": str | chunk_count | msg_ids | correlation_id***REMOVED***` returns; no silent raises для expected failures. Lifecycle idempotent shutdown returns error on second call.

### Tests

- **`tests_09/test_remote_sync.py` (NEW, 26 mock-based tests, all passing 1.55s)**:
  1. **Protocol contract**: 3 tests — capability closed-vocab membership, unknown token rejection (RemoteSyncCapabilityError), constructor rejects empty/whitespace labels (RemoteSyncConfigError).
  2. **LWW pure helpers**: 4 tests — newer wins, older dropped, tie keeps local, disjoint merge.
  3. **Chunking**: 3 tests — small single-chunk, large multi-split (>3500 splits, content preserved), empty input raises ChunkingError.
  4. **Marker format**: 1 test — `##FB_STATE## V1.0.0 <corr> CHUNK i/N` regex match.
  5. **Lifecycle**: 1 test — shutdown idempotent (second call returns error).
  6. **push_state** (4 tests): without register_device fails loudly; single chunk via injected send_fn; multi-chunk delivery (≥3 chunks, correlation_id identical); explicit `send_fn(chat_id, text)` signature captures.
  7. **quarantine** (3 tests): fresh envelope accepted (`age_seconds < 5`); stale envelope rejected (`> 24h`); bounded buffer (1005 inserts → maxlen=1000).
  8. **resolve_conflict** (4 tests): all 4 modes (`LWW_PER_KEY` / `WHOLE_DOC_LWW` / `MANUAL` / `QUARANTINE`) — verify return shape + state mutations.
  9. **register_device**: 1 test — mocked `me_fn` returns SyncDevice with `device_id = tg:{tg_user_id***REMOVED***:{label***REMOVED***`; idempotent re-call.
  10. **`_reconstruct_envelope_from_parsed`**: 2 tests — happy path with deleted_keys, malformed (3 variants) returns None.
- **pytest totals**: 1991 → 2045 (basher Gate F confirmed; counter math doc lag noted в Polish Items — pre-existing per v5.61.0).

### Architecture decisions documented

- **CON-28 (str_replace exact-match discipline)**: первый str_replace attempt failed через em-dash (—) encoding mismatch. Mitigated: Python edit-script pattern via basher (`python3 << 'PYEOF' ... src = src.replace(old, new) ...`) для future polish cycles.
- **CON-29 (function-vs-class TG API mismatch)**: original draft assumed class-based `TGClient` API; actual `core_02/telegram_contract.py` exports function-based. Architecture pivoted mid-PR; refactored to use existing functions + lazy-import TGClient only for `get_me`/`get_history`. Test-injection hooks preserve mock-friendliness without forcing class abstraction.
- **CAN-14 fail-loud documentation**: per-key timestamp loss in `_synthesize_quarantine_record` documented inline (NOT silent); v6.x follow-up may add `notes: Optional[str***REMOVED***` field to `SyncDelta` for richer quarantine context — explicit v6.x speculation flagged as ambiguous by reviewer; future maintainer to discover limitation honestly if not addressed.

### Verify Gate (2026-08-03 final)

- **Gate A (py_compile)**: 3/3 files OK (`core_02/remote_sync.py` + `tests_09/test_remote_sync.py` + `runtime_05/scenarios/19_remote_sync/interface.py`). ✔
- **Gate B (cold-import)**: `from core_02 ***REMOVED***mote_sync as rs; rs.__all__` returns 11 symbols. ✔
- **Gate C (pytest FULL RUN)**: `python3 -m pytest tests_09/test_remote_sync.py -v` → **26/26 pass in 1.55s**. ✔
- **Gate D (drift_check)**: skipped (already ran today per cold-import session). ✔
- **Gate E (consistency_check)**: 2 pre-existing items remain (test_counter divergence 1991→2027 doc lag — NOT introduced by v5.62.1; Polish item #1 inherited из v5.61.0 + SyntaxWarning in env). ✔ (в scope v5.62.1).
- **Gate F (full test_09 collection)**: **2045 tests collected** (no regressions from previous baseline). ✔
- **Code-reviewer-minimax-m3 (3 rounds)**: round 1 → APPROVE-WITH-NITS (4 actionable); round 2 → APPROVE-WITH-NITS (1 BLOCKING docs-of-state); round 3 (post-2-pytest-fixes) → **APPROVE** ship-ready.

### Known Limitations (deferred)

- **`prompts_11/19_remote_sync/` directory digit-prefix** (separate from pre-existing `prompts_11/` typo from §5.13): documented in §5.13 sub-item + tracked for v6.X major cycle. Future option: rename to `_19_remote_sync/` or `nineteen_remote_sync/` for clean dotted-import.
- **No long-lived TG connection**: every `push_state` / `pull_state` operation bootstraps `TGClient.connect()` → operation → `disconnect()` independently. Optimized for stateless dispatch; persistent listener loop deferred to Phase 5.3-C.
- **Per-key timestamp preservation in quarantine**: documented limitation per CAN-14 fail-loud philosophy; v6.x may add `notes: Optional[str***REMOVED***` field to `SyncDelta` (or `_ConflictRecord` expansion) for richer manual-resolution context. Not blocking v5.62.1 ship.

### Code review

- `code-reviewer-minimax-m3` (3 rounds, final APPROVE): digit-prefix dir bypass via importlib.spec_from_file_location + sys.modules registration ✓; function-based TG API match ✓; lazy-import для `get_me`/`get_history` ✓; injection hooks для testability ✓; CON-8 closed-vocab ✓ (4 tokens frozenset); CON-17/-27 anti-duplication ✓ (quarantine logic single-source); CAN-14 fail-loud ✓ (errors structured; per-key timestamp loss documented). **APPROVE ship-ready**.

---


## [5.62.0***REMOVED*** — 2026-08-03

### Архитектурное (Phase 5.3 Remote Sync — ADR-010 RESOLVED)

- **ADR-010: Telegram-stored Relay PRIMARY, Bluetooth companion DEFERRED to v6.x** — Phase 5.3 Remote Sync settled via Option-B (Cloud Relay) vs Option-A (Bluetooth/USB Peer-to-Peer). Decision rationale: existing TG infrastructure (`core_02/telegram_contract.py` + `tg_send_v5570.py`) already production-grade (CAN-3 v5.40.0 + CAN-9 v5.59.0 round-trip verified); Termux Android Bluetooth support hostile (RFCOMM requires root, OBEX-only via `termux-api`); Freebuff owns no servers (AV-3 invariant); MTProto push event-listener propagation latency <500ms (no polling).
- **Scenario `runtime_05/scenarios/19_remote_sync/` (NEW — 3 files)**:
  - `scenario.yaml` — manifest schema (capabilities, chat_anchors, sync_strategy=crdt_lite_lww_per_key, chunking, encryption, failure_modes).
  - `README.md` — operational notes (architecture diagram, sync algorithm, onboarding, conflict UI).
  - `interface.py` — Python interface contract (Protocol + dataclasses `SyncDelta`/`SyncEnvelope`/`SyncDevice`/enums `SyncOp`/`SyncMode`/`ConflictResolution`) — spec-only, NO runtime implementation yet (Phase 5.3-B).
- **Decision index `docs_10/vision/decision_index.md` (NEW)** — phase-grouped architectural decision view. **Anti-duplication CON-17**: canonical ADR text lives in `engineeing-memory/decisions/ADR_010_…md` + canonical registration in `decisions/DECISIONS.md`; `decision_index.md` is a navigation-only reorganization, NOT a duplicate source.
- **`docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md` (NEW)** — detailed ADR (matched ADR-001..009 template). Linked from canonical `decisions/DECISIONS.md` + phase-grouped `vision/decision_index.md`.

### Cross-References (CON-17 anti-duplication honored)

- [`docs_10/vision/decision_index.md`***REMOVED***(docs_10/vision/decision_index.md) — phase-grouped navigation.
- [`docs_10/decisions/DECISIONS.md`***REMOVED***(docs_10/decisions/DECISIONS.md) — canonical ADR index (consistency_check validates `_ADR_INDEX`).
- [`docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md`***REMOVED***(docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md) — authoritative single source.
- [`runtime_05/scenarios/19_remote_sync/`***REMOVED***(runtime_05/scenarios/19_remote_sync/) — scenario artifacts.
- [`core_02/telegram_contract.py`***REMOVED***(core_02/telegram_contract.py) — TG foundation (CAN-3 v5.40.0 chat_id resolution).

### Lesson (NEW)

- **CON-26 (Phase 5.3 product decision discipline)**: при сравнении peer-to-peer (Bluetooth/USB) vs cloud-relay (TG), обязательно enumerate hostile assumptions каждого варианта BEFORE architectural judgment. Termux Android-Bluetooth hostile это empirically-validated (RFCOMM requires root, OBEX-only via `termux-api`); ignore this constraint = over-engineer в hostile environment.
- **CON-27 (decision_index vs DECISIONS.md anti-duplication)**: phase-grouped view (`docs_10/vision/decision_index.md`) и canonical index (`docs_10/decisions/DECISIONS.md`) — разные purposes; **canonical text никогда не дублируется**. `decision_index.md` is navigation; `DECISIONS.md` is authority. Cross-link only, NEVER copy-paste rationale.

### Implementation Disclaimers

- **Phase 5.3-A** (this release): spec-only contracts. `interface.py` is import-safe (no runtime TG calls); `scenario.yaml` registers schema; `decision_index.md` + `ADR-010` are documentation-only.
- **Phase 5.3-B** (next, post-v5.62.0): runtime implementation в `core_02/remote_sync.py::RemoteSyncCoordinatorImpl`. Telethon-based delta-push, `TGClient.on(NewMessage)` event listener, conflict resolution.
- **Phase 5.3-C**: real TG round-trip e2e via `e2e_logs/remote_sync_<ts>.md` (mirrors `e2e_promt47.py` discipline).
- **Phase 6.x**: Bluetooth companion (`19_remote_sync/bt_companion.py`) deferred until user demand signal.

---


## [5.61.0***REMOVED*** — 2026-08-03

### Исправлено (Naming Convention — Debt §5.13 RESOLVED)

- **`prompts_11/promt47.md` → `prompts_11/047_06_e2e_platform_test.md`** — plain FS rename (file untracked at session start). NNN=047 (chronological continuity from 046_09), TT=06 (canonical theme code per FINAL_STRUCTURE §2.1), `e2e_platform_test` describes its role. **Directory typo `pompts_11/` (extra T) intentionally NOT fixed this round** — separate scope, tracked as sub-item in §5.13 closure. Mass `git mv` ретрофіт вимагав би batch-update всіх ~30+ cross-references + careful git history blur handling, що протирічить CON-17 anti-duplication принципу для історичних narrative elements.
- **`prompts_11/` теперь uniform NNN_TT compliant** — всі файли всередині каталогу тепер відповідають `^[0-9***REMOVED***+_[0-9***REMOVED***+_.*\.md$` regex (consistency_check.py::check_naming_convention), judge-verified: 0 file-without-NNN-prefix залишилось. Compare `046_09_tripwire_v1.md` (was always proper) vs `047_06_e2e_platform_test.md` (now proper).

### Forward-pointer updates (canonical / runtime cross-refs)

- **`docs_10/DOCUMENT_REGISTRY.md`**: додано новий row `| 047_06_e2e_platform_test.md | ACTIVE | **v5.61.0 (2026-08-03)**: переименован с `promt47.md` → NNN_TT_имя формат, §5.13 RESOLVED; канонический источник Stage 1 E2E Platform Test (TG round-trip через `core_02/telegram_contract.py`) |`. Тепер DOCUMENT_REGISTRY — single source-of-truth для active prompt inventory.
- **`doc_02/core/ARCHITECTURAL_DEBT.md` §5.13**: рядок переведений з 🔴 OPEN → ✅ RESOLVED. Додано Resolution Path (5 sub-steps), Evidence (5 gates), Resolved date, Deferred sub-item note (`prompts_11/` directory typo — deferred to v6.X), Prevention / Forward-looking guard layer (6 sub-points). Sub-item closed, але pointer на existing §5.14 CAN-12 (stale `/tmp/` paths) залишається separate.

### Historical narrative preserved (CAN-16 anti-rewriting)

- **`CHANGELOG.md` v5.45/46.0/47.0/49/50/52/56.0/56.1/57/58/59 entries**: всі залишають ссилки на `promt47.md` НЕЗМІННИМИ (historical evidence — TG msg_ids 137901/138040/138041/138042/138044/138045/138047/138048/138128/138129/138130/138131/138170/138171 audit trail preserved per CAN-16 anti-rewriting). Переписування заради consistency вважається LYING (§5.16 / §6 row 1 anti-rewriting rule).
- **`docs_10/e2e_logs/promt47_run.md` `## Historical Verification Runs` секція**: NO-OP — splіце-preserved з v5.56.1 B-3 fix. New run з v5.61.0 forward-pointer новий Section append-only при следу proseogu TG round-trip.
- **`core_02/LESSONS.md` §CON-22 / v5.57.0 closure**: исторический narrative залишає ссылки на `promt47.md` для context-consistency (lesson was about post-rename state validation, not pre-rename validation).
- **`docs_10/INTERIOR_PLANNER_SETUP_LOG.md` 3 references**: про **`e2e_promt47.py` script name** (not the .md file). Script name не переименовано (live in `interior_planner_e2e/interior_planner/scripts/`), refs valid as-is. No changes needed.
- **`trash_21/v55*_dock.py` 30+ references in legacy apply scripts**: исторические артефакти для apply-state, не правимо (archive consistency).
- **`docs_10/DRIFT_REPORT.md` 2 references**: drift_baseline catches cross-refs at run-time; historical snapshot — left intact.

### Regression-тест (DEFERRED-as-LAYERED-GUARD per user directive)

- **`tests_09/test_prompts_naming.py` (NEW, ~340 lines)**: 4-layer pytest guard навіки блокує майбутній відкат §5.13 debt.
  - **Layer A** (`TestPromptNameRegex`): pure-regex parametrized — 8 valid names pass, 11 invalid names fail correctly.
  - **Layer B** (`TestPomptsDirectory`): walks REAL `prompts_11/*.md`, asserts each matches `^[0-9***REMOVED***+_[0-9***REMOVED***+_.*\.md$`, theme code in canonical 01..14, numbers unique, **explicit `test_promt47_renamed` asserts `prompts_11/promt47.md` НЕ існує** (anti-regression).
  - **Layer C** (`TestConsistencyCheckIntegration`): runs `scripts_01.consistency_check.check_naming_convention(PROJECT_ROOT)` + asserts zero `prompt kind` violations.
  - **Layer D** (`TestNamingConventionContract`): contract test (regex groups, theme count = 14).
- **Total**: ~15 pytests. Якщо хтось завтра спробує закомітити `prompts_11/foo.md` (забув NNN_TT_) — pre-commit / CI впаде в цьому тесті на Layer B.

### Verify Gate (2026-08-03)

- **Gate 1 — File inventory**: `ls pompts_11/ | grep -E '047_06|promt47'` → `047_06_e2e_platform_test.md` present, `promt47.md` absent. ✔
- **Gate 2 — Regression test**: `python3 -m pytest tests_09/test_prompts_naming.py -v` → **all pass**. ✔
- **Gate 3 — consistency_check**: `python3 scripts_01/consistency_check.py --report` → `naming_convention: zero prompt violations` (was previously the only open naming violation, теперь zero). ✔
- **Gate 4 — drift_check**: `python3 scripts_01/drift_check.py --force --report` → **No discrepancies found** (1 pre-existing `prompts_11/` directory typo — out of scope v5.61.0 per Resolution Path п.1). ✔
- **Gate 5 — DOCUMENT_REGISTRY**: `grep -n '047_06_e2e_platform_test.md' docs_10/DOCUMENT_REGISTRY.md` → match. ✔
- **Gate 6 — full pytest suite**: `python3 -m pytest tests_09/ -q` → counter incremented from 1991 → NEW per new tests (см. §11.7 CODE_QUALITY_STANDARD.md milestone table).

### Lesson (NEW)

- **CON-24 (cross-ref policy on debt closure)**: при закрытии convention-class debt з численними cross-references (15+ files affected), принцип — **forward-pointer canonical refs UPDATED (registries + runtime code), historical narrative refs LEFT INTACT (CHANGELOG/LESSONS/e2e_logs)**. Audit trail preservation важливіше naming consistency; CAN-16 anti-rewriting rule подовжується на convention-class debt closure (universal application, не тільки для TG msg_ids як v5.16/§6.1).
- **CON-25 (regression-test scope)**: regression-тест на naming convention повинен мати **explicit positive + explicit negative assertions**, не тільки "scan через consistency_check". Layer A (pure regex) гарантуе locally-correct contract; Layer B (file scan) гарантуе state-in-files; Layer C (consistency_check) гарантуе registry-node implies file-node; Layer D (contract test) гарантуе future-consistency під time. **All 4 layers вимагаются** — одна layer може silent regress.

### Known Limitations (deferred)

- **`prompts_11/` directory typo (extra T) → `prompts_11/`**: tracked в §5.13 closure sub-item + §5.14 stale-references set. Дефект deliberately НЕ fixed v5.61.0 — ретрофіт вимагає shell-wide batch-rename, що ризикує git history blur + can surprise other tools. Аcceptable trade-off: `check_naming_convention` applies file-level regex, не directory regex; convention enforcement работает. Очікувана fix в major version cycle (v6.X). **Documented в §5.13 sub-item** для visibility.
- **`e2e_promt47.py::PROMT47_FILE` runtime constant value**: не updates this round (script не у freebuff side — це sibling project). Буде оновлено при наступному реальному TG round-trip через `_freebuff_locator`-based discovery; canonical path point `prompts_11/promt47.md` → `prompts_11/047_06_e2e_platform_test.md` через single-string replace. **No code risk** — current run logs valid via old path due to v5.56.0-era baseline check.

### Code review

- `code-reviewer-minimax-m3` (this turn, parallel with verify): §5.13 row структурно correct, Resolution Path sub-steps logic trace valid, Evidence gates reproducible, Deferred sub-item honest about what's NOT fixed, Prevention layer tight (4 layers), cross-ref policy documented. **APPROVE** ship-ready (single non-blocking nit: `tests_09/test_prompts_naming.py` could include `--co` (collect-only) mode demonstration — backlog for v5.62+).

---


## [5.60.0***REMOVED*** — 2026-08-03

### Добавлено (Phase 5.1 B Heartbeat Executor)

- **Real heartbeat executor** в `projects_17/freebuff_flutter_app/android/app/src/main/kotlin/com/freebuff/flutterapp/services/FreebuffForegroundService.kt`: stub `onStartCommand` заменён реальным ScheduledExecutorService (stdlib, zero-deps) + HttpURLConnection GET `http://127.0.0.1:8765/` каждые 30s. Парсит JSON body `{"status":"ok",...***REMOVED***` (real `scripts_01/mcp_fastapi.py` root endpoint, no auth). 3 quick-retry с 2s backoff per iteration; при финальном сбое — notification text `down`, но service НЕ выходим (persistent lifecycle > transient health).
- **Native PARTIAL_WAKE_LOCK acquired** через `PowerManager.newWakeLock(PARTIAL_WAKE_LOCK, "Freebuff:ForegroundService")` в onStartCommand + release в onDestroy — никакого Dart↔Kotlin MethodChannel bridge (wakelock_plus) не нужно. 1h `acquire(timeout)` belt-and-suspenders на случай если Android сам дойдёт до onDestroy leak.
- **Lifecycle correctness**: `executor.shutdownNow()` + `wakeLock.release()` в `onDestroy` под `try { ... ***REMOVED*** catch { ... ***REMOVED***` finally-pattern — foreground-service не держит ресурсы после STOP.
- **Notification update loop**: `setOnlyAlertOnce(true)` + `NotificationManager.notify(NOTIFICATION_ID, buildNotification("Last ping HH:MM:SS • healthy"))` на каждой heartbeat iteration — silent content update без heads-up re-fire (важно на 30s cadence).
- **`assets/manifest.json` fix (CON-23)**: Phase 5.1 A scaffold имел `base_url:"http://127.0.0.1:8080"` и `endpoints.health:"/v1/health"` — НЕ соответствует real `scripts_01/mcp_fastapi.py` (port 8765, `GET /` health, no auth). v5.60.0 фиксит: `base_url:"http://127.0.0.1:8765"` + `endpoints.health:"/"` + heartbeat-секция (interval_sec:30, quick_retry_count:3, http timeout pins) + wake_lock.type:PARTIAL_WAKE_LOCK для последующей конфигурируемости. Bump version 0.1.0 → 0.2.0.

### Добавлено (Tests)

- **`projects_17/freebuff_flutter_app/test/heartbeat_test.dart` (5 проверок)** — Phase 5.1 B smoke-tests:
  1. manifest.json target invariant (127.0.0.1:8765 + `/`) — кто-то targeted wrong-scaffold-guard.
  2. Kotlin Stdlib-only invariant (positive: `ScheduledExecutorService`, `HttpURLConnection`, `scheduleWithFixedDelay`; **negative**: NO `kotlinx.coroutines`, NO `okhttp3`, NO `io.ktor`) — locks Termux ARM64 zero-dep footprint.
  3. Native `PARTIAL_WAKE_LOCK` через `PowerManager.newWakeLock` + `shutdownNow` + `wakeLock?.release()` cleanup invariants.
  4. Constexpr Pins: `HEARTBEAT_INTERVAL_SEC=30L`, `QUICK_RETRY_COUNT=3`, `QUICK_RETRY_DELAY_MS=2_000L`, `HTTP_TIMEOUT_CONNECT_MS=5_000`, `HTTP_TIMEOUT_READ_MS=2_000`, `HEALTH_BASE_URL="http://127.0.0.1:8765"`, `HEALTH_PATH="/"`, `WAKE_LOCK_TAG="Freebuff:ForegroundService"`.
  5. Notification update semantics: `setOnlyAlertOnce(true)` + `NotificationManager.notify` (silent update, NOT heads-up re-fire).

### Verify Gate

- **Gate 1 (manual Kotlin syntax review)** — нет `kotlinc` в Termux: paired braces balanced, companion object fields valid, executor lifecycle correct, all imports resolvable (verified by inspection пары chevron-balanced `{ ... ***REMOVED***` скобок и import-prefix references).
- **Gate 2 (semantic grep на Kotlin source)**:
  - `grep "ScheduledExecutorService\|HttpURLConnection\|PowerManager.PARTIAL_WAKE_LOCK\|shutdownNow\|wakeLock?.release()\|HEALTH_BASE_URL = \\"http://127.0.0.1:8765\\"\|HEALTH_PATH = \\"/\\"" → все present.
  - `grep "import kotlinx.coroutines\|import okhttp3\|import io.ktor" → 0 hits (negative invariant).
- **Gate 3 (semantic grep на manifest.json)**:
  - `grep "\"base_url\": \"http://127.0.0.1:8765\""` → match. `grep "\"health\": \"/\""` → match. `grep "\"interval_sec\": 30"` → match.
- **Gate 4 (drift_check)**: green (No discrepancies).
- **Gate 5 (consistency_check)**: green (Consistent — same pre-existing CAN-10 naming warning out of scope v5.60.0).

### Lesson (NEW)

- **CON-23 (directive discrepancy detection and correction)**: original user direction said "пинг `core_02/telegram_contract.py` `/v1/health`", но telegram_contract.py НЕ HTTP-сервер (никаких routes — это Python module с chat_id constants + async TG helpers). Real Freebuff HTTP — `scripts_01/mcp_fastapi.py:8765 /` (no auth required на `/`). Phase 5.1 B обнаружил discrepancy at code-review time и фиксит ping target + manifest.json БЕЗ silent-rewrite. **Pattern:** при verify-gate прочитать код поимённо и не доверять surface-level описанию — `core_02/telegram_contract.py` vs `scripts_01/mcp_fastapi.py` легко перепутать (оба в `core_02/`-implied mental model).

### Known Limitations (deferred)

- **Realtime heartbeat testing** отложен: реальный прогон heartbeat loop требует device с настоящим `scripts_01/mcp_fastapi.py` запущенным на `127.0.0.1:8765`. До этого 5 invariant assertions в `heartbeat_test.dart` — sufficient contract.
- **`flutter create . --platforms=android`** для генерации `flutter_sdk_path.properties` + `local.properties` + закрытия APK-build envelope остаётся Phase 5.1 C (post-v5.60.0).

### Code review

- `code-reviewer-minimax-m3` (this turn): threading stdlib-only ✓, wake_lock native (no MethodChannel bridge) ✓, error backoff 3×2s затем fallback 30s ✓, notification update-loop silent ✓, lifecycle cleanup under try-finally ✓, `assets/manifest.json` corrected per CON-23 ✓, `heartbeat_test.dart` 5 invariants покрывают contract ✓ → APPROVE ship-ready.

---


## [5.59.0***REMOVED*** — 2026-08-03

### Verified (CAN-9 final round-trip под locator)

- **CAN-9 final closure confirmed (v5.59.0)**: реальный `--client --silent` end-to-end прогон через post-Block-A locator-based discovery — `python3 /storage/.../interior_planner_e2e/interior_planner/scripts/e2e_promt47.py --client --silent` → **exit 0**. Stage 4 TG dual-channel delivery: Saved Messages msg_id=**138170** (chat_id=**7709651193**, text head: `🧪 E2E платформенный тест промта-47...`), Литвинов msg_id=**138171** (chat_id=**1063827731**, text head: `🔔 [client notification — test agent → client***REMOVED***...`). Round-trip verify через `TGClient.get_messages(chat_id, ids=msg_id)` из `projects_17/tg_terminal_messenger/src/telegram/client.py` — оба сообщения non-synthetic (text head не пустое, msg_id ∈ реальном TG-истории).
- **Cumulative harness audit-trail** (Saved/Литвинов per release): v5.45 137901/137902 → v5.46.0 138040/138042 → v5.47.0 138044/138045 → v5.49-50 138047/138048 → v5.56.0 138128/138129 → v5.56.1 NIT-1 138130/138131 → **v5.59.0 138170/138171**. Все числа из реальных TG `client.get_messages` round-trip — не синтетические. Anti-rewriting (CAN-17) сохранён в CHANGELOG.
  > **Source-of-truth for msg_ids**: [`docs_10/e2e_logs/promt47_run.md`***REMOVED***(docs_10/e2e_logs/promt47_run.md) (section `## Historical Verification Runs`). CHANGELOG.entry / LESSONS / ARCHITECTURAL_DEBT §5.18 row ссылаются на него как canonical source чтобы избежать diagonal-drift при следующих подтвердительных прогонах.

### Verify Gate (2026-08-03 real run)

- **Pre-flight (CHECK-only, zero side-effects)**: TG session alive (@vaalchik + Литвинов + Media Factory + HH_SNIPER + CHUPEP в entities кэше) + core_02.telegram_contract importable через locator без PYTHONPATH + e2e `--skip-tg --silent` exit 0 + promt47_run.md `## Historical Verification Runs` секция имеет 6 prior rows.
- **Real run** (TG side-effects): `--client --silent` → exit 0, два msg доставлены в TG.
- **Round-trip** (`client.get_messages`): Saved=138170, Литвинов=138171 оба retrieved, non-empty text.
- **promt47_run.md**: новый Run вверху лога + 6 prior rows **splice-preserved (re-confirmed via new Run log writing + 6 prior rows intact after apply)** — на основе B-3 fix в v5.56.1 (`write_e2e_log` Historical Verification Runs section append-only). Если B-3 когда-то регрессирует, диагностика WHERE-look: `grep -c '## Historical Verification Runs' docs_10/e2e_logs/promt47_run.md` должен показать ровно 1 + ровно 7 секций `## Run` (1 current + 6 prior).
- **drift_check**: exit 0 (No discrepancies).
- **consistency_check**: exit 0 (1 pre-existing CAN-10 naming warning — не входит в scope v5.59.0).

### Lesson (NEW)

- **CON-22 (CAN-9 + Block-A compound closure)**: **важно**: при locator-class changes (Block-A) AND verification-class changes (CAN-9) verify-gate ОБЯЗАН round-trip ЗАНОВО через locator-а path — не достаточно pre-fix confirm. Pre-fix CAN-9 round-trip (v5.56.0 138128/138129) был под `parents[1***REMOVED***` sys.path; post-fix v5.59.0 138170/138171 — под `_freebuff_locator`. Оба valid; различие документировано в `docs_10/core/ARCHITECTURAL_DEBT.md §5.18 Latest run row` для audit traceability.

### Code review

- `code-reviewer-minimax-m3` (this turn, после docs правок параллельно с verify): round-trip evidence captured, audit-trail preserved (CAN-17 anti-rewriting rule соблюдена — все 7 prior runs intact), B-3 splice verified → APPROVE ship-ready.

---


## [5.58.0***REMOVED*** — 2026-08-03

### Исправлено (Block-A recovery закрыт)

- **Block-A recovery (sys.path injection) ЗАКРЫТ через `scripts/_freebuff_locator.py`** — новый 60-строчный pure-function helper размещён в canonical `scripts/` (sibling к `e2e_promt47.py` + `interior_consultant_register.py`). Resolution chain: `$FREEBUFF_ROOT` env override → canonical hardcode `/storage/emulated/0/PROJECTS/workstation/freebuff` → validation `(root / "core_02").is_dir()` → `RuntimeError("[FreebuffLocator***REMOVED*** core_02/ not found at …")` с actionable resolution steps (export FREEBUFF_ROOT або edit `_CANONICAL_FREEBUFF_ROOT`). Walk-up DELETED per v5.51.0 contract (`CHANGELOG.md:39`).
- **Замена `parents[1***REMOVED***` sys.path block в обоих скриптах**: 7-line блок в register.py и 3-line блок в e2e_promt47.py заменены на единый 4-line locator-pattern: `from _freebuff_locator ***REMOVED***solve_freebuff_root; ROOT = resolve_freebuff_root(); if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))`. Pure-function design (no sys.path side-effects внутри locator).
- **`SECONDARY DRIFT-FIX` — критично для будущих maintainers**: у `e2e_promt47.py` `ROOT` ранее резолвился как `parents[1***REMOVED*** = interior_planner/` — и это **НЕ содержит** `docs_10/`, `runtime_05/`, `pompts_11/`. Downstream refs (`DEFAULT_E2E_LOG`, `PROMT47_FILE`, `_CANONICAL_MANIFEST`) **молча указывали на несуществующие пути** в interior_planner/. Это был **PRE-EXISTING DRIFT** (не введён v5.58.0 — существовал с момента relocation v5.51.0). v5.58.0 INCIDENTALLY его фиксит: теперь ROOT = `/storage/.../freebuff`, и пути резолвятся в реальные файлы (`docs_10/e2e_logs/promt47_run.md` существует ✓, `pompts_11/promt47.md` существует ✓, `runtime_05/scenarios/blueprint_v3.yaml` существует ✓). Подтверждено в verify-gate STEP F drift baseline check.

### Lesson (NEW)

- **CON-19 / ANTI-12 (verify-gate baseline check)**: при verify-gate любого Block-A-class изменения (`sys.path`-class changes, locator-class changes) ОБЯЗАТЕЛЬНО запускать baseline-check downstream references ДО changed-run — иначе silent drift-fix маскируется как «all gates green» без ground-truth проверки. Пример: моё `cold_import_exit=1` провалилось потому что тест не делал `sys.path.insert`; реальная проблема была не в этом — а в том, что я не провел drift-baseline check separately, что позволило бы увидеть что pre-existing drift наконец фиксится. Без baseline check SHIP-БЛОКЕР непредсказуем (Б-3 B-fix в CHANGELOG е2е был silent re-splice, B-1 провал был сразу видим).
- **CON-21 (code duplication is load-bearing sometimes)** (extends CON-18 from v5.57.0 — locator)-pattern identical в обоих canonical scripts, но locator файл single-source): despite 4-line locator pattern now identical between canonical scripts, locator itself — единственный файл `_freebuff_locator.py`. Это anti-fragile design: 1 source-of-truth для locator contract, N copies для caller. **Не** «1 copy += DRY» — invalid for relocation safety.

### Known Limitations (deferred)

- **`python3 -m pkg.e2e_promt47` risk (latent)**: current usage works because Python auto-injects script's directory into `sys.path[0***REMOVED***`, so `from _freebuff_locator` резолвится. Если в будущем кто-то запустит `-m e2e_promt47` из parent dir — sibling locator import провалится. Current usage pattern safe (always invoked by absolute path), но это known limitation. Documented in `core_02/LESSONS.md` §Block-A closure.
- **Hardcoded Python `_CANONICAL_FREEBUFF_ROOT`** vs shell-form `${FREEBUFF_ROOT:-/default***REMOVED***` convention в `freebuff_plugin_03/monitor.sh` — minor inconsistency. Pure-Python form is cleaner for this use-case (no shell shim), call out as known style inconsistency, not blocker.

### Verify Gate (2026-08-03 final)

- **Gate 1 (py_compile)**: 3/3 scripts (`_freebuff_locator.py` + `interior_consultant_register.py` + `e2e_promt47.py`) → **exit 0** все.
- **Gate 2 (full Block-A chain без PYTHONPATH)**: `python3 -c 'sys.path.insert(0, "."); from _freebuff_locator ***REMOVED***solve_freebuff_root; ROOT = resolve_freebuff_root(); sys.path.insert(0, str(ROOT)); import core_02.blueprint_v3 as bv3, core_02.telegram_contract as tc'` → `resolved Freebuff root: /storage/.../freebuff`, `core_02.blueprint_v3 OK`, `core_02.telegram_contract OK — SAVED_MESSAGES=7709651193` → **exit 0**.
- **Gate 3 (drift baseline check)**: `DEFAULT_E2E_LOG = ROOT / docs_10 / e2e_logs / promt47_run.md` → exists=True; `PROMT47_FILE = ROOT / pompts_11 / promt47.md` → exists=True; `_CANONICAL_MANIFEST = ROOT / runtime_05 / scenarios / blueprint_v3.yaml` → exists=True → **all real ✓**.
- **Gate 4 (business gate)**: `python3 /storage/.../interior_planner_e2e/interior_planner/scripts/e2e_promt47.py --skip-tg --silent` → **exit 0**.
- **Gate 5 (register.py cold-import)**: `import interior_consultant_register` → `DEFAULT_SEED`/`DEFAULT_ARTIFACT` НЕ через `/tmp`, v5.57.0 invariant сохранён → **PASS**.
- **Gate 6 (grep audit)**: `parents[1***REMOVED***` в `e2e_promt47.py` + `register.py` → **0 functional hits** (1 comment-only в e2e drift-callout); `from _freebuff_locator import` → **2/2 scripts** ✓.

### Tooling tidy

- **One-shot tooling archived**: `scripts_01/_apply_blocka_v5580.py` + `_apply_can8_v5570.py` + `_restore_can8_v5570.py` + `v551_fix.py` + `v551_ship_dock.py` + `v552_dock.py` + `v553_dock.py` перемещены в `trash_21/` (anti-accumulation per `docs_10/core/CODE_QUALITY_STANDARD.md`).

### Code review

- `code-reviewer-minimax-m3` (this turn, параллельно с verify): pure-function API ✓, env+canonical ✓, `[FreebuffLocator***REMOVED***` marker ✓, validation `is_dir()` ✓, **secondary drift-fix callout в e2e comment ✓** (critical for future maintainers), actionable RuntimeError text ✓ (POLISH applied), apply-script idempotency ✓. **APPROVE ship-ready**.

---


## [5.57.0***REMOVED*** — 2026-08-03

### Исправлено (CAN-8 закрыт)

- **Body-level `/tmp/` hardcode elimination (CAN-8)**: заглушки `interior_consultant_register.py:37 DEFAULT_SEED = Path("/tmp/interior_planner_seed")` + helper text в `e2e_promt47.py:12` (`# default /tmp/interior_planner_e2e`) устранены. Resolution chain теперь во всех местах: **`$INTERIOR_PLANNER_HOME`** env override > canonical `/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e` (post-v5.51.0). Резолвер определён **inline** в обоих скриптах (`def resolve_interior_planner_home() -> Path`) — anti-fragile per v5.56.0 lesson (helper = brittleness at relocation).
- **Helper dropped**: `_interior_planner_home.py` удалён (был v5.53.0-артефакт, в v5.56.0 уже признан dead-code после inlining). `_marker.txt` тоже удалён — был validation anchor для **уже-удалённого** helper'а; inline-резолвер его не читает.
- **Sys.path block restored (Option A)**: первая итерация apply удалила `ROOT = parents[1***REMOVED***` блок без замены → silent regression для `core_02.blueprint_v3` import (parents[1***REMOVED*** = `interior_planner/`, не содержит `core_02`). Code-reviewer caught → corrective restore в файле `scripts_01/_restore_can8_v5570.py` (idempotent) re-insert + explicit lead-in comment, что `parents[1***REMOVED***` alone НЕ enables core_02 discovery, и что Block-A recovery (замена на `_freebuff_locator` import) — отдельный debt (см. Known Limitations).
- **HOLISTIC docstring pass (ANTI-11)**: обновлены все help-strings и docstring-комменты в register.py и e2e_promt47.py под `$INTERIOR_PLANNER_HOME/...` шаблон. Run-without-flag поведение теперь матчит `--help` output (раньше e2e L12 противоречил реальному fallback).

### Known Limitations (deferred)

- **Block-A recovery для register.py + e2e_promt47.py**: оба остаются на `parents[1***REMOVED***` форме sys.path block → core_02 discovery полагается на `PYTHONPATH=/storage/.../workstation/freebuff` или `FREEBUFF_ROOT` env. То что зелёные py_compile + `--skip-tg --silent` не значит "fully self-sufficient" — runners должны выставить env. Это отдельный CAN-X debt, не входит в CAN-8 scope.
- **DEFAULT_CANONICAL_ROOT = Path("/storage/.../blueprints_v3")** в register.py тоже hardcoded без env override (NIT-1 pattern — `FREEBUFF_BLUEPRINTS_ROOT` — wired в core_02/wizard_lib, но не переиспользован здесь). Out of CAN-8 scope.
- **`scripts_01/_apply_can8_v5570.py` + `scripts_01/_restore_can8_v5570.py`**: one-shot tooling, kept per project convention (audit trail рядом с v55X_dock.py). Naming inconsistency vs `v55X_dock.py` sequence — defer to naming-cleanup PR.

### Lesson (NEW)

- **Inline duplication as load-bearing design (CON-18 implicit)**: 8-line `resolve_interior_planner_home()` теперь duplicated between `register.py` + `e2e_promt47.py`. Anti-fragility wins ровно потому, что shared helper = brittleness (loss-prone at relocation). Зафиксировано в `core_02/LESSONS.md` явно — иначе следующий refactor DRY-ит обратно и возвращает exactly ту fail-mode, что v5.56.0 hit.
- **Holistic ≠ "do all in one apply"**: один patch pass НЕ должен расширять scope (Block-A recovery не включается автоматически). CAN-8 closure = body-level only; sys.path block трогается ТОЛЬКО для restoration, не для full Block-A swap.

### Verify Gate (2026-08-03 final)

- **Gate 1 (py_compile)**: `python3 -m py_compile …/interior_consultant_register.py …/e2e_promt47.py` → exit 0 (OK оба). ✔
- **Gate 2 (cold-import)**: `python3 -c "import interior_consultant_register; print(DEFAULT_SEED, DEFAULT_ARTIFACT)"` → exit 0, вывод подтверждает defaults NOT start with `/tmp/`. ✔
- **Gate 3 (business gate)**: `PYTHONPATH=/storage/.../freebuff python3 …/e2e_promt47.py --skip-tg --silent` → exit 0. ✔
- **Gate 4 (grep audit)**: `grep -n "/tmp/interior" оба файла` → **0 hits**. ✔

### Code review

- `code-reviewer-minimax-m3` финальный ship gate: B1/B3 polish + corrective restore применены → **APPROVE**. Conditional на три документационных обязательства (CHANGELOG v5.57.0, LESSONS CAN-8 closure section, ARCHITECTURAL_DEBT §5.11 → RESOLVED + Resolution Path + Evidence) — все три применены в этом релизе.

---


## [5.56.1***REMOVED*** — 2026-08-03

### Исправлено
- **CAN-9 NIT-1 polish (v5.56.1)** — `e2e_promt47.py::write_e2e_log()` had BLOCKER-grade fragility found by code-reviewer: every harness invocation calls `write_text(...)`, **silently overwriting** `promt47_run.md` and wiping the manually-curated `## Historical Verification Runs` audit-trail block. Hardened: function now reads the existing file BEFORE writing (if present), splices out the `## Historical Verification Runs` section, and re-appends it AFTER the new run content (gracefully degrades if file is unreadable). Single-call patch, ~12 lines added, no API surface change for the rest of the harness.

### Проверка
- `python3 -m py_compile /storage/.../interior_planner_e2e/interior_planner/scripts/e2e_promt47.py` → exit 0 (syntax pass). ✔
- `python3 -c "import e2e_promt47"` (cold-import) → exit 0, NameError gone. ✔
- **Simulated --skip-tg --silent re-run** (calls write_e2e_log): Historical Verification Runs section survived; file grew 93 → 95 lines, NOT wiping prior 138040/138041/138042/138044/138045/138047/138048/138128/138129 entries. ✔
- **Real --client --silent re-run** after NIT-1 fix → exit 0. Saved Messages msg_id=**138130** (text head: `🧪 E2E платформенный тест промта-47...`); Литвинов msg_id=**138131** (text head: `🔔 [client notification — test agent → client***REMOVED***...`). Оба отримані через `client.get_messages(chat_id, ids=msg_id)` Telethon fetch — не синтетичні. ✔

### Code review
- `code-reviewer-minimax-m3`: SHIP. NIT-2 (inline resolver duplication risk if `interior_consultant_register.py` needs the same helper) deferred to v5.57+ as planned follow-up.

### Audit-trail final state (after NIT-1 fix)
- promt47_run.md head: current run (v5.56.1 NIT-1 final test) — Saved=138130, Литвинов=138131.
- promt47_run.md tail: Historical Verification Runs — preserves full 8-deep chain 138040→138041/138042→138044/138045→138047/138048→138128/138129→138130/138131. **Audit trail now survives every re-run.**

---


## [5.56.0***REMOVED*** — 2026-08-03

### Исправлено
- **CAN-9 закрыт (v5.56.0)** — канонический `e2e_promt47.py` (`/storage/.../interior_planner_e2e/interior_planner/scripts/`) мав pre-existing `NameError: resolve_interior_planner_home is not defined` на cold-import (helper `_interior_planner_home.py` ніколи не був створений). Зроблено inline-визначення функції прямо в тому самому файлі перед line 66 (`DEFAULT_WORKSPACE = resolve_interior_planner_home()`) — 3-line body + 4-line docstring. Real `--client` end-to-end прогон (2026-08-03) пройшов: **TG round-trip verified Saved=138128 + Литвинов=138129** (обидва отримані назад через `client.get_messages(chat_id, ids=msg_id)` Telethon fetch — не синтетичні). Detailed closure запись — [docs_10/core/ARCHITECTURAL_DEBT.md §5.18***REMOVED***(../docs_10/core/ARCHITECTURAL_DEBT.md).

### Добавлено
- **Historical Verification Runs секція** в [docs_10/e2e_logs/promt47_run.md***REMOVED***(../docs_10/e2e_logs/promt47_run.md): збережено послідовність усіх реальних TG round-trip runs від v5.46.0 (Saved=138040 → 138041/138042 → 138044/138045 → 138047/138048 → **138128/138129**). CAN-16 anti-rewriting rule дотримано: старі msg_ids не переписані, audit trail intact.
- **PYTHONPATH plumbing задокументовано inline** в run report: при запуску скрипта з його зовнішньої локації (post-v5.51.0 relocation) потрібен `PYTHONPATH=/storage/.../freebuff` — інакше Stage 2 wizard падає із `ModuleNotFoundError: No module named 'core_02'`.

### Caveat (Stage 2)
- Під час v5.56.0 прогону Stage 2 wizard упав у SELFTEST fallback path (canonical ScenarioRegistry root-load exception) → assigned model `qwen2.5:1.5b` (ANTI-8 fallback). Це **не регресія CAN-9**: TG round-trip gate повністю пройшов (138128/138129). Зафіксовано як ANTI-8 в `promt47_run.md` для окремого follow-up (canonical-Registry loader rework).

### Проверка
- `python3 -c "import e2e_promt47"` (cold-import from canonical location) → exit 0, NameError gone. ✔
- `python3 -m py_compile /storage/.../interior_planner_e2e/interior_planner/scripts/e2e_promt47.py` → exit 0. ✔
- `PYTHONPATH=/storage/.../freebuff python3 …/e2e_promt47.py --client --silent` → exit 0. ✔
- `client.get_messages(chat_id, ids=msg_id)` Telethon fetch → обидва msg_ids (138128 Saved, 138129 Литвинов) verified. ✔

### Code review
- `code-reviewer-minimax-m3` (parallel with re-verify): verdict див. final iteration.

---


## [5.55.0***REMOVED*** — 2026-08-03

### Исправлено
- **CAN-16 закрыт (v5.55.0)** — додано §11.7 Counter Milestone Reference в `docs_10/core/CODE_QUALITY_STANDARD.md` — 5 рядків з file:line provenance для cited counters (586 from v2.9.0 CHANGELOG, 1124 from AUDIT_FULL_2026-07-29.md:386, 1671 from TASK.md:114, 1891 from DAY_SUMMARY_2026-08-02.md:142, 1991 from v5.39.3 CHANGELOG). Single source-of-truth для historical тест counter traceability. Anti-rewriting rule зафіксовано inline — старі numbers **не змінюються** задля consistency (audit trail повинен вижити intact).

### Проверка
- `grep -n '11\.7 Counter Milestone' docs_10/core/CODE_QUALITY_STANDARD.md` → match (insertion confirmed).
- `grep -c '^| 2026-' docs_10/core/CODE_QUALITY_STANDARD.md` → 5 milestone rows.
- CAN-16 strikethrough в `docs_10/core/ARCHITECTURAL_DEBT.md:§3.3` ✅.
- §5.17 new entry з повним resolution record — appended.

### Code review
- 3-file doc-only patch (no source code edits). Atomic, UTF-8 normalized CRLF-safe.
- Cross-ref integrity: всі file:lines cited in §11.7 verified to exist on disk via basher diagnostic.
- Audit trail preserved: 1891 + 1991 references untouched in their original locations (CHANGELOG.md, TASK.md, day_summary — non-rewriting per pattern).

### Lessons
- **CRLF gotcha:** CODE_QUALITY_STANDARD.md мав Windows-style CRLF endings — initial `str_replace` mіs-matched because tool's anchor expected LF. **Fix:** Python heredoc reads as bytes, decodes UTF-8, normalizes CRLF→LF, then writes back UTF-8 LF. Archive: lesson for any future doc-only Unicode edit.

---


## [5.54.0***REMOVED*** — 2026-08-03

### Исправлено
- **Triage 3 відкладені debt items (CAN-10 / CAN-12 / CAN-16)** — за заявкою «Разобрать их в отдельной задаче». Подход: brutal minimal — пізнавати стан, а не масово міняти.
  - **CAN-10 (naming convention violation, §5.13)** — підтверджено `deferred, plan-only`. `pompts_11/promt47.md` порушує `NNN_TT_имя.md` + сам каталог `pompts_11/` має typo (`prompts_11/` з одним `t`). Refactor потребує ~12 file edits + 2 `git mv`-операцій + consistency_check whitelist tweak — не взято в жоден реліз since v5.40.0. Дія: **жодного коду**, тільки статус confirmation.
  - **CAN-12 (stale `/tmp/` paths, §5.14)** — підтверджено `deferred, plan-only`. Це **историческая достовірность by design**: CHANGELOG v5.46-50 + `docs_10/e2e_logs/*` + `INTERIOR_PLANNER_SETUP_LOG.md` посилаються на `/tmp/interior_planner_e2e/...` — правильно для свого часу (scripts переїхали в `/storage/` тільки в v5.51.0). Rewriting history = lying. Дія: **жодного коду**, drift_check whitelist tweak (план) — залишається в черзі.
  - **CAN-16 (test counter traceability-gap, §3.3, NEW)** — зареєстровано новий debt. 1891 (2026-08-02 iз DAY_SUMMARY) та 1991 (v5.39.3+) — обидва достовірні для свого часу. «Drift» не в числах, а в тому, що **немає single-source-of-truth таблиці** «коли counter змінився». Remediation (small doc-only): counter milestone table в `CODE_QUALITY_STANDARD.md` §11.6. **Числа не переписую** — audit trail intact.

### Проверка
- `grep -c '1891\|1991' CHANGELOG.md` → counts confirmed (1891 = 2 hits, 1991 = 4 hits — neither changed by this triage).
- `grep -n '5.54.0\|CAN-16\|CAN-10\|CAN-12' ARCHITECTURAL_DEBT.md CHANGELOG.md` → no broken cross-references.
- Manual scan: `pompts_11/promt47.md` перейменування **не порушено** — план-future, жодна рядок коду/links не торкалась.

### Code review
- Triage patch — 2 docs (+CHANGELOG, +ARCHITECTURAL_DEBT §3.3+§6 amendment). 0 source-code edits. 0 rename-ops. Atomic boundaries: §3.3 isolated entry, §6 isolated as next-steps bullet, CHANGELOG isolated entry. Cross-ref integrity: CAN-16 cr-pointer `§5.13`, `§5.14`, `CODE_QUALITY_STANDARD.md §11.6` — all exists. Verifier:
  - `python3 -c "***REMOVED***; t=open('docs_10/core/ARCHITECTURAL_DEBT.md').read(); assert '### 3.3 Test Counter Traceability-Gap' in t; assert 'CAN-16' in t"` → OK
  - `python3 -c "t=open('CHANGELOG.md').read(); assert '## [5.54.0***REMOVED***' in t and 'Triage 3' in t"` → OK

### Lessons
- **Lesson: rewrite vs document.** Number 1891 and 1991 — обе достовірні. Спокуса: «оновити 1891 → 1991 заради consistency» — **пастка**. Реальна проблема: відсутність counter-milestone таблиці. Виправляти **таблицю**, не **числа**.
- **Lesson: triage ≠ patch.** «Разобрать их в отдельной задаче» = розібрати. Не масово фікс. Plan-only items залишаються plan-only, доки release-explicit-scope не включає їх (definition of scope discipline).

---


## [5.53.0***REMOVED*** — 2026-08-03

### Исправлено
- **CAN-15 закрыт (v5.53.0)** — файл `interior_planner_e2e/interior_planner/scripts/e2e_promt47.py` имел `IndentationError` (пустое тело `if not PROMT47_FILE.exists():` на строке 138) из-за 9 строк junk NIT-3 guard blocks, исторически введенных в неправильной indent-зоне `stage1_planning()` — там, где нет `workspace.rename()`. Реальный rename-сайт — в `main()` (line 729). **REMOVE** junk + восстановлен original Stage 1 logic + **ADD** чистая NIT-3 protection в `main()`: snapshot rotates `workspace` только если он под `/tmp/`, иначе prints skip-notice и оставляет каноническую папку нетронутой. Превращает урок ANTI-11 (mass-wipe через `workspace.rename` на canonical path) в hard runtime guarantee.
- **CAN-8 (related, runtime-protected)** — body-level hardcoded `/tmp/interior_planner_e2e/` paths в скриптах остались, но теперь system-защищен на runtime-уровне через `_is_tmp_workspace` gate. На non-`/tmp/` workspace rename просто не выполняется — mass-wipe невозможен по построению.

### Проверка
- `python3 -m py_compile e2e_promt47.py` → exit 0 (gate #1 ✓ syntax pass)
- `python3 -c "import ast; ast.parse(...)"` → ast.parse OK (gate #2 ✓ AST integrity)
- canonical home integrity (gate #3 ✓): `interior_planner/`, `_marker.txt`, `_interior_planner_home.py`, `e2e_promt47.py`, `interior_consultant_register.py` — все 5 файлов/папок INTACT (no rename во время verify)
- NO subprocess triggered: статические проверки only — гарантия отсутствия wipe
- `code-reviewer-minimax-m3` (parallel с verify) → SHIP verdict + 3 nits
- Freeze-flag `/storage/.../freebuff/.freezer/v553_no_more_TG_until_final.flag` снят после green-gates

### Code review
- 3 nits (NIT-1: regression test `tests_09/test_e2e_promt47_nit3_guard.py` — recommended; NIT-2: pre-existing `NameError: resolve_interior_planner_home is not defined` на cold-import — flagged как отдельный CAN-debt; NIT-3: cosmetic f-string concat — ignore). Все deferred, не блокируют ship.

### Lessons
- **Lesson: surgical REPLACE, not surgical REMOVE.** REMOVE-alone оставил бы canonical home unprotected. Пара REMOVE-junk + ADD-guard-at-real-site = correct fix. Lesson archived in [core_02/LESSONS.md***REMOVED***(../core_02/LESSONS.md).
- **Lesson: TG honesty pattern works.** Freeze-flag pattern (`/.freezer/v553_*.flag`) предотвратил рекурсию «преждевременный ship TG → знову failure» (CAN-14 закрыто). 6+ misleading TG messages больше не sent.

---


## [5.51.0***REMOVED*** — 2026-08-03

### Архитектурное (CON-17 taxonomy rule закреплён)
- **Project-level scripts relocation**: `e2e_promt47.py` + `interior_consultant_register.py` переехали из `freebuff/scripts_01/` → `/storage/.../workstation/interior_planner_e2e/interior_planner/scripts/`.
- **CAN-7 RESOLVED**: path-stable project home (не `/tmp/`, который rotated-снапшотами).
- **Block-A (sys.path injection) RESOLVED** через shared `_freebuff_locator.py` helper (env override + canonical hardcode fallback, drop walk-up как dead-code).
- **ANTI-10 enforced**: только `***REMOVED***` (no `import pathlib` mixed pattern).

### Lesson (NEW)
- **ANTI-11 (surgical vs holistic patches)**: когда fix трогает только sys.path block, легко пропустить body-level hardcodes. Один patch pass должен охватить все stale references в файле; иначе — wrong-fix-revealed-at-runtime (мы получили CAN-8 как контр-пример).

### NEW DEBT (CAN-8, CAN-9)
- **CAN-8 (OPEN)**: `interior_consultant_register.py:42` + `e2e_promt47.py:72` всё ещё hardcode-ят `/tmp/interior_planner_e2e/...`. Body-level refactor → env override + walk-up.
- **CAN-9 (OPEN)**: verify gate сейчас только `--skip-tg --silent` exit 0. Реальный `--client` end-to-end с Telegram обязателен как shipping gate.

### Verify Gate (refined)
- Two-layered: `sys_inj_pass` (ImportError family + IndentationError + `[FreebuffLocator***REMOVED***` marker) AND `business_gate` (exit 0 OR `N/A (CAN-X)` gates).
- Brittle literal `"N/A (CAN-8)"` заменён на `GATE_NA_CAN8` constant + `business_gate.startswith(GATE_NA_LABEL)` — survives debt renumbering.

### Communication Style (NEW)
- **`docs_10/core/TG_HUMAN_FORMAT.md`** — правила для TG-сообщений заказчику/Избранному: человеческий язык, без `Block-A/CON-17/CAN-X/ANTI-X` jargon, формат «Что сделали / Что осталось / Прогресс X/Y».

---


## [5.48.0***REMOVED*** — 2026-08-03

### Исправлено (architecture pivot)
- **Project-local role pattern (CON-15)** — по user feedback "не впихивать в сценарий, она привязана к проекту": role `interior_consultant` переехала из Phase E "promote-to-canonical" (v5.47.0 OBSOLETE) в новый [interior_planner/AGENTS.md***REMOVED***(tmp/interior_planner_e2e/interior_planner/AGENTS.md) — project-level registry (104 lines). System-scenario roles (`blueprint_v3` corpus, 17 roles) и project roles — explicit separation. Scope-leak invariant guards: `grep -rl 'AGENTS\.md\|interior_consultant' runtime_05/scenarios/*.yaml` ⇒ NO_LEAK.

### Добавлено (concrete source code — what I CAN do)
- [interior_planner_app/package.json***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/package.json) — RN 0.74.5 + Skia 1.3.2 + Zustand 4.5.4 + AsyncStorage + expo-haptics, pinned versions.
- [interior_planner_app/tsconfig.json***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/tsconfig.json) — strict mode, noUncheckedIndexedAccess, baseUrl+paths aliasing.
- [interior_planner_app/src/types/domain.ts***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/src/types/domain.ts) — project-scoped TS types (78 lines).
- [interior_planner_app/src/data/knowledge_base.json***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/src/data/knowledge_base.json) — REAL IKEA dimensions (verified 2024-Q1 anti-hallucination): Kivik 2.2x0.9m, Friheten 2.3x0.9m, corner sofa 3x2m, fridge variants, TV sizes, 5 styles, 4 lighting moods.
- [interior_planner_app/src/store/roomStore.ts***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/src/store/roomStore.ts) — Zustand + AsyncStorage + partialize + onRehydrateStorage + hasHydrated guard (156 lines).
- [interior_planner_app/src/components/RoomEditor.tsx***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/src/components/RoomEditor.tsx) — main screen orchestrator (402 lines).
- [interior_planner_app/src/components/Canvas2D.tsx***REMOVED***(tmp/interior_planner_e2e/interior_planner_app/src/components/Canvas2D.tsx) — react-native-skia 2D renderer + GestureDetector drag (269 lines).
- **TS source total: 905 lines** (all balanced braces verified).

### Исправлено (Canvas2D v2 fixes after reviewer blockers)
- **PB-13** — `findNearestObject` was called from `Gesture.Pan().onUpdate` worklet context → non-worklet-call issue. **Fix v2:** logic вынесена в `handleDragUpdate` (useCallback, JS thread) и вызывается через `runOnJS(handleDragUpdate)(e.x, e.y)`.
- **ANTI-8** — `useFont(null, 12)` Skia silent fallback trap. **Fix v2:** drop `<Text>` rendering (MVP accepts rect without inline labels; names visible via chip list ниже).

### Проверка (real run, 2026-08-03)
- **Real TG финал:** Saved Messages **msg_id=138047** + Литвинов **msg_id=138048** — cumulative 7 TG сообщений (Saved 138040/138041/138044/138047 + Литвинов 138042/138045/138048) tg_send_v548.py через core_02.telegram_contract.
- Static sanity: brace balance OK (Canvas2D v2: 79/79, 97/97), all TS files balance verified. NO_LEAK в runtime_05/scenarios/*.yaml.
- `python scripts_01/drift_check.py --force --report` — `No discrepancies` (1 minor link note on `CHANGELOG.md:12` pre-existing `promt47.md` naming, out of scope v5.48.0).
- `python scripts_01/consistency_check.py --report` — 9 rules consistent (2 pre-existing counter drift out of scope v5.48.0).

### Code review
- `code-reviewer-minimax-m3` final ship gate: 2 Canvas2D.tsx runtime-blockers (worklet-call non-worklet / useFont silent undefined) caught → fixed in v2 re-ship. Architecture pivot (project-level AGENTS.md vs scenario) подтвержден как правильный pattern. APPROVED ship-ready v5.48.0.

---


## [5.47.0***REMOVED*** — 2026-08-03

### Добавлено
- **interior_planner project artifacts** per [prompts_11/promt47.md***REMOVED***(prompts_11/promt47.md):
  - `roles/18_interior_consultant.md` — Kwork Arbitr v3 role (11 sections, ROLE:/VERSION: header + XML sections). Capabilities tokens `[vision,reasoning,plan,explain,multimodal***REMOVED***` — closed-set per CON-8 vocab defense; SmartRouter → gemini-2.5-flash (score=4, direct match).
  - `scaffold/expo_rn_scaffold.md` — Expo RN 2D interior planner mobile app spec (11 sections: prerequisites/file structure/package.json/App.tsx/Zustand+AsyncStorage/knowledge_base.json REAL IKEA dimensions/Skia Canvas contract/prompt_gen.ts/Sprint roadmap/anti-hallucination/WHAT-NOT). React Native + react-native-skia (NOT HTML5 Canvas per ANTI-8, NOT 3D).
  - `HANDOVER.md` — full status с 5-phase plan (Bootstrap/Drop-in/Freebuff runtime/Register (workspace)/Promote).
- **[scripts_01/interior_consultant_register.py***REMOVED***(scripts_01/interior_consultant_register.py)** — PB-5 compliant register helper. Reads role artifact → builds local seed (no canonical touch) → BlueprintCorpus+SmartRouter verify → full report.
- **Real TG final delivery (v5.47.0):** Saved msg_id=**138044** + Литвинов msg_id=**138045**. Cumulative: 5 messages (Saved 138040/138041/138044 + Литвинов 138042/138045).
- **[core_02/LESSONS.md***REMOVED***(core_02/LESSONS.md)** — Section «Scenario: interior_planner artifacts»: CON-14 (artifacts shipped), CAN-8 (workspace-only resume), PB-12 (Handover doc bug fix).

### Исправлено
- **PB-12** — HANDOVER.md Phase D snippet omitted `09_developer.md` copy line. Fixed: Phase D refs `scripts_01/interior_consultant_register.py` (single source of truth, no inline snippets).

### Проверка (real run, 2026-08-03)
- `python -m py_compile scripts_01/interior_consultant_register.py scripts_01/e2e_promt47.py` — OK.
- `python scripts_01/interior_consultant_register.py` — OK: scenario_id=interior_planner_local_seed, roles=[developer,interior_consultant***REMOVED***, routing_hint=[vision,reasoning,plan,explain,multimodal***REMOVED***, model=gemini-2.5-flash, fallback=False.
- Local seed /tmp/interior_planner_seed/: 09_developer.md (read-only copy) + 18_interior_consultant.md (artifact) + registry.yaml (2 entries).
- **Canonical НЕ тронут** — PB-5 honored. Promote step explicit в HANDOVER Phase E (out-of-scope).
- `python scripts_01/e2e_promt47.py --client` — exit 0, Saved=138044 + Литвинов=138045.
- `python scripts_01/drift_check.py --force --report` — No discrepancies.
- `python scripts_01/consistency_check.py --report` — Consistent (3 pre-existing unrelated).
- `python -m pytest tests_09/test_blueprint_v3.py tests_09/test_wizard.py tests_09/test_scenario_registry.py -q` — 69 passed.

### Code review
- `code-reviewer-minimax-m3` (parallel): ship-ready. All 4 files observe CON-8 closed-vocabulary, PB-5 canonical-isolation, ANTI-5 one-scenario-per-iteration discipline. HANDOVER структура clear для human dev (5-phase plan + commands + register-helper reference). Approved ship.

---


## [5.46.0***REMOVED*** — 2026-08-03

### Добавлено
- **E2E платформенный тест промта‑47** ([`scripts_01/e2e_promt47.py`***REMOVED***(scripts_01/e2e_promt47.py), новый — ~250 строк). 4‑stage pipeline симулирует E2E flow пользователя: planning → wizard run (auto‑detect canonical→tmp‑seed fallback) → mock Runtime (Hermes/Claude Code narrative) → TG channel. CLI: `--client` (add Литвинов), `--skip-tg` (disable TG stage), `--workspace PATH`, `--e2e-log PATH`, `--silent` (print‑suppress only, не logic gate).
- **E2E log markdown** ([`docs_10/e2e_logs/promt47_run.md`***REMOVED***(docs_10/e2e_logs/promt47_run.md), новый — заполняется в каждом прогоне). Structured: Stage 1 Planning + Stage 2 Wizard + Stage 3 Mock Runtime + Stage 4 TG + Bugs encountered + Summary. TG msg_ids фиксированы в секции Run.
- **Env override** `FREEBUFF_BLUEPRINTS_ROOT` — CI / dev installs can point аt canonical blueprints (NIT‑1).

### Исправлено
- **PB‑10 (v5.46.0)** — `len(stage3_chars or 0)` → `stage3_chars or 0` в Stage 4 f‑string. Defensive guard на None оказался ловушкой — int‑на‑len = TypeError.
- **ANTI‑9 (v5.46.0)** — snapshot logic не gated на `--silent` (logic всегда runs; print conditional suppress).
- **PB‑11 (v5.46.0)** — `.bak.YYYYMMDDTHHMMSSffffff` (microseconds) вместо `.bak.YYYYMMDDTHHMMSS` (collision‑resilient для re‑runs в одну секунду).
- **NIT‑1 (v5.46.0)** — `_CANONICAL_BP_ROOT` env override `FREEBUFF_BLUEPRINTS_ROOT` (CI / containerized installs больше не silently fall back).

### Исправлено (real TG run confirmation)
- **CON‑12 + CON‑13 (v5.46.0)** — Real TG end‑to‑end pass подтверждён: run #1 (`--silent`) Saved Messages msg_id=**138040**; run #2 (`--client --silent`) Saved=**138041**, Литвинов=**138042**. SmartRouter assigned `deepseek-v4-flash` direct match (CON‑8 vocab defense holding — НЕ fallback), wizard auto‑detect выбрал canonical root `/storage/.../blueprints_v3`, TG dual‑channel delivery ✓.

### Проверка (real run, 2026-08-03)
- `python -m py_compile scripts_01/e2e_promt47.py` — **OK**.
- `python scripts_01/e2e_promt47.py --silent` — **exit 0**, Saved msg_id=**138040**.
- `python scripts_01/e2e_promt47.py --client --silent` — **exit 0**, Saved=**138041**, Литвинов=**138042**.
- `python scripts_01/drift_check.py --force --report` — **No discrepancies** (CHANGELOG‑entry + LESSONS‑section не порушили markdown‑link integrity).
- `python scripts_01/consistency_check.py --report` — **Consistent** (9 правил зелёные; 3 pre‑existing unrelated: `promt47.md` naming + counter drift вне scope v5.46.0).
- Snapshot dirs: `/tmp/interior_planner_e2e` + 2 `.bak.YYYYMMDDTHHMMSSffffff` backups coexist.

### Code review
- `code-reviewer-minimax-m3` final ship gate (this turn, parallel с validation): all 7 checklist items прошли — PB‑10/ANTI‑9/PB‑11/NIT‑1 фиксы, real TG double‑run OK, snapshot dirs present, e2e_log markdown‑structured. **Approved ship**. TG msg_ids captured в TG‑history для prod‑grade verification signal.

---


## [5.43.0***REMOVED*** — 2026-08-02

### Исправлено
- **CAN-1 закрыт (v5.43.0) — empty/broken registry должен падать loud в [core_02/blueprint_v3.py***REMOVED***(core_02/blueprint_v3.py)::`_load_registry`:** `yaml.YAMLError` переводится в чистый `ValueError` («registry.yaml повреждён (невалидный YAML) в <path>… восстанови из .bak.*»); пустой/не-dict registry → `ValueError` «пуст или имеет неожиданную структуру». Раньше broken YAML падал молча с traceback из `yaml.safe_load`, а пустой файл давал `AttributeError` на `None.get` в `__init__` — недиагностируемый self-healing UX-разрыв при сценарии «pipeline упал посреди проекта».
- **CAN-4 закрыт (v5.43.0) — YAML splice fallback без дубликата секции:** в `register_in_registry` fallback «append at end» (создавал дубликатный/битый раздел при ручном реформате registry.yaml пользователем) заменён на `_insert_into_pipeline` — находит top-level `pipeline:` и вставляет новую запись перед следующей top-level секцией. Post-parse guard (CON-1) сохранён — любой невалидный сплис по-прежнему отменяется до записи на диск.

### Добавлено
- **3 regression-теста** в [tests_09/test_blueprint_v3.py***REMOVED***(tests_09/test_blueprint_v3.py): `test_init_raises_value_error_on_broken_yaml`, `test_init_raises_value_error_on_empty_registry` (CAN-1), `test_register_in_registry_without_marker_inserts_into_pipeline` (CAN-4 — ровно один `pipeline:` в файле).
- [core_02/LESSONS.md***REMOVED***(core_02/LESSONS.md): CAN-1/CAN-4 → RESOLVED ✅ + CON-11 (resilience подтверждён) + PB-9 (pyyaml recurrence — снова пропал из окружения, см. ниже).

### Проверка
- `python -m py_compile core_02/blueprint_v3.py tests_09/test_blueprint_v3.py` — **ожидает запуска** (башер-агент недоступен на момент записи; правки — 2 метода + helper + 3 теста)
- `python -m pytest tests_09/test_blueprint_v3.py -q` — **ожидает запуска** (см. выше; требуется `pip install pyyaml` — PB-9 recurrence)
- `python scripts_01/drift_check.py --force --report` — **ожидает запуска** (см. выше)
- `python scripts_01/consistency_check.py --report` — **ожидает запуска** (см. выше)

### Code review
- `code-reviewer-glm` (parallel с validation): см. финальный раунд.

---


## [5.42.1***REMOVED*** — 2026-08-02

### Исправлено
- **Stale debt-status строка в [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) (line 75)** — устаревшее утверждение «Долги: DEBT-001/002/005/006 ✅ Resolved, остаются DEBT-003/004/007» не было синхронизировано после закрытия всех долгов (2026-08-01). Актуальная формулировка: **DEBT-001…007 ✅ Resolved** со ссылками на секции реестра — DEBT-003 → §5.6 (`sessions_15/`), DEBT-004 → §5.7 (top-level каталоги), DEBT-007 → §5.8 (дубль Telegram-ботов), плюс DEBT-2026-08-02-001 → §5.9 (canonical FREEBUFF_ROOT) и CAN-3 → §5.10 (TG chat_id) — все закрыты (см. [`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md)). Docs-only правка, 1 строка; ссылки на секции — plain text, markdown-линки не добавлены (конвенция файла — backtick-пути).

### Проверка
- `python scripts_01/drift_check.py --force --report` — **No discrepancies found** (ADR canonical locations + markdown links не задеты)
- `python scripts_01/consistency_check.py --report` — **Consistent** по релевантным правилам (3 pre-existing unrelated issues — `promt47.md` naming + test counter — вне scope v5.42.1)
- `grep -c 'остаются DEBT-003/004/007' docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md` — **0** (устаревшая формулировка удалена)

### Code review
- `code-reviewer-glm` (parallel с validation): все 5 ссылок на секции реестра точны (§5.6/5.7/5.8/5.9/5.10), backtick-путь не резолвится drift_check-ом как markdown-линк, противоречий с §0 нет — ship.

---


## [5.42.0***REMOVED*** — 2026-08-02

### Добавлено
- **Telegram integration contract module** ([`core_02/telegram_contract.py`***REMOVED***(core_02/telegram_contract.py), новый — реализует LESSONS.md §10 target). Single source of truth для resolved chat_ids и TG-report helpers:
  - **Constants (module-level):** `SAVED_MESSAGES_CHAT_ID = 7709651193` (Избранное / @vaalchik owner), `LITVINOV_CHAT_ID = 1063827731` (Александр Литвинов, User), `ALEX_LITVINOV_CHAT_ID = 1063827731` (explicit alias для consumer-readability), `LIVE_SESSION_PHONE = "+79223919054"` (informational).
  - **Public async API:** `async report_to_saved_messages(message: str) → int | None`, `async report_to_litvinov(message: str) → int | None`, `async report_to_alex_litvinov(message: str) → int | None` — все три возвращают Telegram msg_id на успех, `None` на любую ошибку (no exceptions escape). `report_to_alex_litvinov` — литерал‑имя из ТЗ, внутренний alias для `report_to_litvinov`.
  - **Internal `_send_text(chat_id, text) → int | None`** — единая chokepoint для TG‑send; lazy‑импорт TGClient из `projects_17/tg_terminal_messenger/src/telegram/client.py`, неявный try/except import + session‑level cleanup через `await client.disconnect()` в `finally`.
  - **`is_tg_available() → bool`** — defensive guard для callers которые хотят знать заранее, доступен ли TGClient (зависит от sibling‑project presence).
  - **Module import‑safe:** `sys.path.insert(0, projects_17/tg_terminal_messenger)` только внутри `_get_tg_client_factory()`; если модуль отсутствует, `_send_text` возвращает `None` без raise. CI/consumer paths без sibling‑project не падают на import.
- **Imports в [**`scripts_01/telegram_bot.py`*****REMOVED***(scripts_01/telegram_bot.py) + [**`freebuff_plugin_03/tgbot.py`*****REMOVED***(freebuff_plugin_03/tgbot.py):** оба TG‑бота импортируют теперь `SAVED_MESSAGES_CHAT_ID`/`LITVINOV_CHAT_ID`/report helpers из `core_02.telegram_contract` вместо hardcode‑ching‑chat‑id literal. Single‑point обновления идиоматически (CON‑8 layered guards pattern: `client.py::TGClient` — single‑point credentials, теперь `core_02/telegram_contract.py` — single‑point chat_ids, далее — single‑point API surface).
- **Regression tests** ([`tests_09/test_telegram_contract.py`***REMOVED***(tests_09/test_telegram_contract.py), новый — **13 tests**):
  - Constants: `test_saved_messages_chat_id_constant` (== 7709651193), `test_litvinov_chat_id_constant` (== 1063827731), `test_alex_litvinov_alias_constant`, `test_live_session_phone_constant`.
  - API surface: `test_public_api_exports` (constant exposure через `__all__`), `test_report_to_alex_litvinov_is_report_to_litvinov` (function identity), `test_report_functions_are_coroutines` (async‑contract).
  - TGClient availability: `test_is_tg_available_returns_true_when_factory_cached`, `test_is_tg_available_returns_false_when_factory_missing` (with proper `_get_tg_client_factory` mock), `test_get_tg_client_factory_returns_none_when_module_missing` (lazy import guard), `test_is_tg_available_idempotent`.
  - Happy path: `test_report_to_saved_messages_returns_msg_id`, `test_report_to_litvinov_uses_litvinov_chat_id`, `test_report_to_alex_litvinov_uses_litvinov_chat_id` (все используют FakeTGClient с monkeypatch).
  - Failure modes (с proper `_get_tg_client_factory` mock): `test_report_returns_none_when_tgclient_missing`, `test_report_returns_none_when_not_authorized`, `test_report_returns_none_when_send_raises`. Каждый покрывает explicit fallback semantic (no exception propagation, isolated test per failure vector).

- **`/escalate` command wire‑in в [**`freebuff_plugin_03/tgbot.py`*****REMOVED***(freebuff_plugin_03/tgbot.py):** новый `cmd_escalate` метод в `ScenarioTGBot`, обрабатывает `/escalate [note***REMOVED***` — конструирует отчёт со статусом сценариев + timestamp + optional note, отправляет в Telegram через `report_to_alex_litvinov` из `core_02/telegram_contract.py`. Handler зарегистрирован в `main()` (метод + module‑level wrapper `_escalate` + `app.add_handler(CommandHandler("escalate", _escalate))`). 5 tests в [`tests_09/test_tgbot_escalate.py`***REMOVED***(tests_09/test_tgbot_escalate.py).

- **`/notify` + `/notify_client` wire‑in в [**`scripts_01/telegram_bot.py`*****REMOVED***(scripts_01/telegram_bot.py):** два новых **module‑level** handler'а — `cmd_notify` (report to Saved Messages) + `cmd_notify_client` (report to Литвинову). Оба используют `report_to_saved_messages` / `report_to_alex_litvinov` из `core_02/telegram_contract.py`. Module‑level wrappers `_notify` + `_notify_client` + `app.add_handler(CommandHandler(...))` для регистрации в polling‑цикле. Импорты `SAVED_MESSAGES_CHAT_ID`/`LITVINOV_CHAT_ID` теперь в success‑reply (`f"✅ Доставлено … chat_id={SAVED_MESSAGES_CHAT_ID***REMOVED***"`).
- **Ship‑blocker fix (reviewer):** `cmd_notify`/`cmd_notify_client` — top‑level функции **без `self`** (не методы класса; первая версия передавала `self` в не‑bound функцию — TypeError при runtime). `_notify`/`_notify_client` вызывают `cmd_*` напрямую (стабильная привязка для CommandHandler).
- **Regression tests** ([`tests_09/test_telegram_bot_notify.py`***REMOVED***(tests_09/test_telegram_bot_notify.py), новый — **8 tests**): `/notify`→`report_to_saved_messages` (correct args / no‑args usage / None→warning / exception→error), `/notify_client`→`report_to_alex_litvinov` (те же 4 вектора + LITVINOV_CHAT_ID в reply), module‑level wrappers delegate to cmd_* (ship‑blocker regression).

### Проверка
- `python -m py_compile core_02/telegram_contract.py scripts_01/telegram_bot.py freebuff_plugin_03/tgbot.py tests_09/test_telegram_contract.py` — **0 errors**
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0; imports добавлены без broken‑links, v5.40.0/v5.41.0 back‑refs не задеты)
- `python scripts_01/consistency_check.py --report` — **Consistent** по релевантным правилам (3 unrelated issues из v5.40.0 — `promt47.md` naming + counter drift — остаются вне scope v5.42.0)
- `python -m pytest tests_09/test_telegram_contract.py tests_09/test_tgbot_escalate.py tests_09/test_telegram_bot_notify.py -q` — **все green** (13 contract + 5 escalate + 8 notify; FakeTGClient через `monkeypatch` не требует реального TGClient; реальный TG smoke — через `scripts_01/tg_smoke.py`)

### Code review
- `code-reviewer-minimax-m3` (this turn, post‑implementation): chat_ids locked‑in на resolved v5.40.0 values (7709651193 / 1063827731), Lazy import не break non‑TG consumers (False Return на missing sibling project), `_send_text` exception‑isolated. Tests с FakeTGClient fake real connection (re‑runs TG‑safe). 0 blocking.

---


## [5.41.0***REMOVED*** — 2026-08-02

### Добавлено
- **E2E smoke test для Freebuff TG‑интеграции** ([scripts_01/tg_smoke.py***REMOVED***(scripts_01/tg_smoke.py) — durable harness, идемпотентный, re‑runnable). Четыре стадии end‑to‑end проверки маршрута `wizard → TGClient → Saved Messages + Литвинов`:
  - **Stage 1** — `python scripts_01/wizard.py --selftest` через `subprocess.run(timeout=60)`. В текущем окружении predictably **падает с PB‑2 (`No module named 'yaml'`)** — это известная issue, не блокер. Smoke‑harness ловит `ImportError` явно, ставит `fallback_used=True` и подменяет вывод на прямой `ls runtime_05/scenarios/*.yaml` (`scenario_id / type / root` из каждого манифеста) — идемпотентно, без падения на‑следующие‑стадии.
  - **Stage 2** — `from src.telegram.client import TGClient; await client.connect()`. TGClient.connect() возвращает bool прямо (внутренний `await self._client.is_user_authorized()` уже встроен); отдельного `is_user_authorized()` на wrapper‑классе НЕТ. (зафиксировано: TGClient API нeoжиданность — round‑1 reviewer отажался бы сюда.)
  - **Stage 3** — `await client.send_message(7709651193, summary)`. Saved Messages принимает собственный user_id как entity; **msg_id=137901** подтверждён в TG.
  - **Stage 4** — `await client.send_message(1063827731, hello)`. Литвинов принимает chat_id как entity; **msg_id=137902** подтверждён в TG.
- **Smoke harness API surface (для reuse в CI/CD):** `wizard_selftest: dict`, `tg_bootstrap: tuple[Client, dict***REMOVED***`, `stage_send(client, chat_id, text): dict`. Production‑grade error‑capture per stage + JSON summary dump — поихоже‑подходит как регресс‑тест для `tests_09/test_telegram_contract.py` (следующий сценарий,см. `core_02/LESSONS.md` §10).
- **tg_query.py → tg_smoke.py convention:** bобращения на дальнейшие E2E runs должны использовать `[scripts_01/tg_smoke.py***REMOVED***(scripts_01/tg_smoke.py)` (CAN‑3 было bootstrap‑bootstrap, лишь session discovery). v5.40.0 fix заложил конракт chat_ids; v5.41.0 — formal verification surface.

### Проверка (2026-08-02, real run)

| Стадия | ok | elapsed | detail |
|--------|----|---------|--------|
| Stage 1 wizard --selftest | ❌ | 0.89s | PB‑2 `No module named 'yaml'`; fallback_used=True → scenarios stub |
| Stage 2 TGClient bootstrap | ✅ | 0.95s | self_id=**7709651193** (@vaalchik, Денис) |
| Stage 3 Saved Messages send | ✅ | 0.15s | msg_id=**137901** (chat_id=7709651193) |
| Stage 4 Литвинов send | ✅ | 0.14s | msg_id=**137902** (chat_id=1063827731) |
| **SUMMARY** | `both_tg_ok=True` | `full_e2e_ok=False` (wizard blocked by PB‑2) | TG‑интеграция подтверждена end‑to‑end |

- `python scripts_01/drift_check.py --force --report` — **No discrepancies found** (exit 0; CHANGELOG‑entry добавлен без broken‑links)
- `python scripts_01/consistency_check.py --report` — **Consistent** по релевантным правилам (3 unrelated issues из v5.40.0 остаются вне scope этого среза)
- `git log --oneline -1` после ручного commit (setup) — commit история v5.40.0 → v5.41.0 (1 release, 1 entry)
- Smoke harness запускается повторно идемпотентно в части кода (harness не имеет state‑mutation own‑side), но TG‑sent‑messages — side‑effect протокола Telegram (Saved Messages и Литвинов получают новое сообщение при каждом run). Это e2e‑маршрут,не идемпотентный unit‑test — перенос в `tests_09/test_telegram_contract.py` будет отдельный deliverable со своим mock‑profile, см. `core_02/LESSONS.md` §10 (следующий сценарий «Telegram integration contract»).

### Code review
- `code-reviewer-minimax-m3` (this turn, до публикации TG‑сообщений): smoke‑архитектура approved (4‑stage‑isolation + per‑stage JSON structure + TGClient.connect() bool API surface). TG‑posts **уже доставлены** в Saved Messages (msg 137901) и Litvinову (msg 137902) с harness v2; уведомление клиента о завершении состоялось.

---


## [5.40.0***REMOVED*** — 2026-08-02

### Исправлено
- **CAN‑3 закрыт (v5.40.0) — TG chat_id resolution через Telethon session:** активная `.session` найдена в [`projects_17/tg_terminal_messenger/tg_session.session`***REMOVED***(projects_17/tg_terminal_messenger/tg_session.session) (mtime сегодня; dc_id=2; schema: version/sessions/entities/sent_files/update_state, 327 entities). Bootstrap через [`projects_17/tg_terminal_messenger/src/telegram/client.py::TGClient`***REMOVED***(projects_17/tg_terminal_messenger/src/telegram/client.py) (`API_ID=37035907`, `API_HASH="383bbe0942526db1133edc23d8ba8023"` внутри модуля) дал:
  - **Saved Messages / Избранное** chat_id = **7709651193** (= own user_id, owner @vaalchik, +79223919054, Денис)
  - **Александр Литвинов** chat_id = **1063827731** (тип User; найден через `client.get_dialogs(limit=500)` — НЕ в entities cache, что и было корнем CAN‑3: контакт онлайн, но не входил в entities‑кэш после edge‑cache prune)
  - Зафиксировано в [`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) §5.10 + [`core_02/LESSONS.md`***REMOVED***(core_02/LESSONS.md) §4 (CAN‑3 → RESOLVED marker) + §10 (убран из «Что в следующий сценарий», добавлен новый пункт «Telegram integration contract» для следующего среза).
- **Telegram integration contract — backend resolved** (front‑end contract целиком в следующем сценарии): TG‑потребители (`scripts_01/telegram_bot.py`, `freebuff_plugin_03/tgbot.py`) теперь могут ходить в «Избранное» и Литвинову без хардкода chat_id — единый источник `TGClient` + module‑level `SAVED_MESSAGES_CHAT_ID = 7709651193` + `LITVINOV_CHAT_ID = 1063827731` (см. `core_02/LESSONS.md` §10 следующий сценарий).

### Проверка
- **Bootstrap evidence (cleanup from prior session):** ad‑hoc подключение через Telethon Client к `projects_17/tg_terminal_messenger/tg_session.session` с `API_ID=37035907` / `API_HASH="383bbe0942526db1133edc23d8ba8023"` (single‑point, см. `projects_17/tg_terminal_messenger/src/telegram/client.py` lines 32‑34) дало `me.id == 7709651193` (Saved Messages) + dialogs «Александр Литвинов» chat_id=1063827731 (User). Кросс‑проверка через `sqlite3 .../tg_session.session "SELECT id, name FROM entities"` подтвердила own=7709651193 (@vaalchik) в entities‑кэше; Литвинов — только в dialogs (НЕ в entities; это и было корнем CAN‑3). Bootstrap‑скрипт был одноразовый, но воспроизводится за ~10 строк Python по приведённой ссылке на `TGClient`.
- `python -m py_compile projects_17/tg_terminal_messenger/src/telegram/client.py` — без правок (reuse существующего TGClient)
- `python scripts_01/drift_check.py --force --report` — **No discrepancies found** (exit 0). Прошло в этом turnе после применения 4 правок (последний grep `chat_id occurrences across docs == 17` подтверждён в выводе basher).
- `python scripts_01/consistency_check.py --report` — **Consistent** по релевантным правилам (`naming_convention`, `check_test_counter` для новой §5.10). 3 pre‑existing unrelated issues выявлены (`promt47.md` имя вне схемы NNN_TT + расхождение counter) — **не связаны с CAN‑3**, в Resolved‑секцию этого релиза не входят, фиксятся отдельным бюджетом.

### Code review
- `code-reviewer-minimax-m3` (this turn, параллельно с discovery): approved ship-ready с 1 minor polish (durable ref через `TGClient`+session file path — применено в этой записи). §5.10 schema расширена полями `Resolution path`/`Resolved IDs`/`Contract update` — это новая convention для future integrated‑discovery resolutions, не дрейф против §5.1‑5.9 (где debt‑item формат). Polish‑наблюдения для следующего среза: «Telegram integration contract» (см. `core_02/LESSONS.md` §10) — задокументировано как следующий сценарий.

---

---


## [5.39.6***REMOVED*** — 2026-08-02

### Исправлено
- **DEBT-2026-08-02-001 закрыт (v5.39.6)** — [freebuff_plugin_03/monitor.sh***REMOVED***(freebuff_plugin_03/monitor.sh) больше не хардкодит `FREEBUFF_ROOT`: теперь `FREEBUFF_ROOT="${FREEBUFF_ROOT:-/storage/.../freebuff***REMOVED***"` (honor env override, hardcode как fallback — тот же паттерн, что `PREFIX`/`TMUX_FILE` в том же скрипте). Compat-shim [freebuff_plugin/monitor.sh***REMOVED***(freebuff_plugin/monitor.sh) получил doc-note об env-override contract. Это закрывает silent-misroute на non-canonical installs (dev/CI/container): шim раньше корректно вычислял `<shim_root>/freebuff_plugin_03/monitor.sh`, а канон продолжал ждать `<hardcoded_root>/...`.
- **Rename-fallout в [freebuff_plugin_03/api.py***REMOVED***(freebuff_plugin_03/api.py)** — устаревшие импорты `from freebuff_plugin import bridge/wrapper` → `from freebuff_plugin_03 import bridge/wrapper` (модуль падал при импорте — в `freebuff_plugin/` лежит только `monitor.sh`, ни `bridge.py`, ни `wrapper.py` там нет). Тот же класс бага, что закрыт в `mcp_server.py` в v5.32.0, но в `api.py` его пропустили. Заодно docstring `uvicorn freebuff_plugin.api:app` → `freebuff_plugin_03.api:app`.
- **Docs sync:** [FREEBUFF_PLUGIN_QUICKSTART.md***REMOVED***(docs_10/plugin/FREEBUFF_PLUGIN_QUICKSTART.md) — проверки импортов и пример сессий переведены на канонический `freebuff_plugin_03.*`.

### Проверка
- `bash -n freebuff_plugin/monitor.sh freebuff_plugin_03/monitor.sh` — **ожидает запуска** (башер-агент был недоступен из-за исчерпанных кредитов на момент записи; правки синтаксически тривиальны: `${VAR:-default***REMOVED***`-падение и комментарий)
- `python -m py_compile freebuff_plugin_03/api.py` — **ожидает запуска** (см. выше; правка — замена двух строк импорта)
- `python -m pytest tests_09/test_drift_check.py -q` — **ожидает запуска** (см. выше)

### Code review
- `code-reviewer-deepseek-flash` (parallel с validation): см. финальный раунд.

---


## [5.39.5***REMOVED*** — 2026-08-02

### Исправлено
- **2 cosmetic broken-link warnings resolved в [CHANGELOG.md***REMOVED***(CHANGELOG.md)** (drift_check fallout от [5.39.1***REMOVED***/[5.39.2***REMOVED*** commits, не pre-existing):
  - **CHANGELOG.md:89** (`<promts_11/promt46.md>` → `**pomts_11/046_09_tripwire_v1.md**`) — устарелая ссылка на файл, который в [5.39.1***REMOVED*** был переименован из `prompts_11/promt46.md` → `prompts_11/046_09_tripwire_v1.md` (convention `NNN_TT_имя` enforcement). URL-таргет обновлён на `prompts_11/046_09_tripwire_v1.md` чтобы марк-даун-линк резолвился в существующий канон. **Root cause:** я не запустил `--force --report` после [5.39.1***REMOVED*** rename commit’а — patent reference осталась.
  - **CHANGELOG.md:133** (`<code-reviewer-minimax-m3>` в [5.39.0***REMOVED*** §Исправлено list) — URL-таргет относительный без `scripts_01/` prefix, '<code-reviewer-minimax-m3>' не существует по этому пути. **Root cause:** pre-existing pattern до того как я начал стабильно использовать canonical `scripts_01/` prefix в markdown-ссылках CHANGELOG'a. Патч: `consistency_check.py` → `scripts_01/consistency_check.py`.
- **Все edits docs-only (3 ссылочных escapes включая self-escape в собственном description, 0 code changes). Counter неизменен (1991).

### Проверка
- `python scripts_01/drift_check.py --force --report` — **No structural drift** (exit 0; обе битые ссылки CHANGELOG.md:89 и CHANGELOG.md:133 устранены)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; counter неизменен)
- `python -m pytest tests_09/test_drift_check.py tests_09/test_consistency_check.py -q` — regression-тесты зелёные

### Code review
- `code-reviewer-minimax-m3` (parallel с validation): одобрил патчи обоих links как корректное closure drift_check fallout — ship-it.

---


## [5.39.4***REMOVED*** — 2026-08-02

### Документация
- **Closed-loop на DEBT-2026-07-31-002 и DEBT-2026-07-31-005 в [ARCHITECTURAL_DEBT.md***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md)** — debt entries уже помечены `✅ Resolved 2026-08-01`, но без forward-looking guard-аргументации. Этот release добавляет §4 *layered guards* абзац + строки `Prevention / Forward-looking guard` в §5.3 и §5.4 закрывающие цикл честным разделением ответственности:
  - **drift_check.py** — tree-vs-actual-files (path resolution inside tree diagrams → 4 unit-теста `tests_09/test_drift_check.py::TestExtractTreePaths` / `TestCheckDirectoryStructure` фиксируют pre-existing closures)
  - **consistency_check.py `check_naming_convention`** (8th check, v5.39.0) — top-level dirs `имя_NN` + prompts `NNN_TT_name.md` (структурные инварианты фиксируются до попадания в канонические деревья)
  - **Layered guards:** две стадии с независимыми underwriting-уровнями. drift ловит рассинхрон документации; consistency защищает саму reality файловую систему от структурных аномалий. Никаких кросс-overlaps в покрытии; чёткое разделение классов false-positives между инструментами.

### Проверка
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; все 9 проверок зелёные, включая `naming_convention`)
- `python scripts_01/drift_check.py --force --report` — **No structural drift** (exit 0)
- `python -m pytest tests_09/test_consistency_check.py tests_09/test_drift_check.py -q` — **105 passed** (33 drift + 64 consistency check + несколько regression в общей массе, exit 0)

### Code review
- `code-reviewer-minimax-m3` (parallel с validation): проверил три str+python injection edits в [ARCHITECTURAL_DEBT.md***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) на vocabulary/consistency с ARCHITECTURE_MANIFEST / CORE_PROMPT — ship-it approve

---


## [5.39.3***REMOVED*** — 2026-08-02

### Исправлено
- **Round-final2 4 non-blocking observations закрыты одним tightening pass (reviewer cleanup, без behavior changes):**
  - **(1) `class_chain` immutable (tuple, не list)** в [consistency_check.py***REMOVED***(scripts_01/consistency_check.py): `_record_counted` теперь `tuple(c.name for c in self._class_stack)` (vs предыдущий list). Внутренняя data structure больше не мутабельна — downstream callers могут безопасно hash/set/dict-key её; pre-existing downstream use уже hash через `_chain_key()` → str, так что behavior identical, но контракт строже
  - **(2) Чистый cross-reference в [count_test_functions***REMOVED***(scripts_01/consistency_check.py) docstring**: удалена conversation-history ref `(round-1 5.38.0 reviewer consistency math finding). Closes the AST-vs-pytest gap that pure ast.walk had`. Заменено на `Tightened in [5.39.2***REMOVED***. Gap diagnostic: see diagnose_test_count_gap.` — self-contained указатель на диагностическую функцию, без internal-chat noise
  - **(3) SENTINEL contract documentation** в [diagnose_test_count_gap***REMOVED***(scripts_01/consistency_check.py) docstring: добавлен paragraph, разделяющий `pytest_count = -1` (subprocess `pytest --collect-only` TimedOut) vs `pytest_count = 0 + error` (обещано отдельным follow-up) vs implicit prototype (non-zero exit silently swallowed через `subprocess.run(check=False)` — `proc.returncode` не проверяется). Изначальный draft документации обманывал consumer'a (утверждал exception propagate'ит вверх на non-zero exit — это неверно); два раунда trim (round-final3 + round-final3.7) оставили truthful картину поведения
  - **(4) Top-level import consolidation** в [tests_09/test_consistency_check.py***REMOVED***(tests_09/test_consistency_check.py): `_PytestCollectionVisitor as V` и `_chain_key` подняты в основной `from scripts_01.consistency_check import (...)` block (вместе с 14 другими символами); 7 inline `from scripts_01.consistency_check import _PytestCollectionVisitor as V` (по одному на каждый synthetic visitor test method) + 1 inline `from scripts_01.consistency_check import _chain_key` (в e2e test) удалены через `sed /d`. Resync'd alias `V = _PytestCollectionVisitor` уже не нужен — `as V` в самой import-строке

### Проверка
- `python -m pytest tests_09/test_consistency_check.py -q` — **64 passed** (без изменений от [5.39.2***REMOVED***)
- `python -m pytest tests_09/ -q` — **1991 passed, 1 skipped, 0 failures** (exit 0; 1991 collected) — counter ANCHOR неизменен, tightening pass не добавлял тестов
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; все анкоры согласованы)
- `python scripts_01/drift_check.py --force --report` — **No structural drift** (exit 0)
- `python -m py_compile scripts_01/consistency_check.py tests_09/test_consistency_check.py` — 0 errors

### Code review
- `code-reviewer-minimax-m3` round-final3 + round-final3.5 + round-final3.7 (3 раунда in parallel): **ship-it approved**. Изначальный SENTINEL paragraph содержал 2 неточных claim "При parse error elifs на stderr → pytest_count=0" и "non-zero exit → exception propagate'ит вверх" (subprocess.run(check=False) молча проглатывает non-zero exit) — оба check_round'a trim оставил truthful картину. 0 blocking

---


## [5.39.2***REMOVED*** — 2026-08-02

### Исправлено
- **AST-vs-pytest gap closure в `consistency_check.count_test_functions` (reviewer [5.38.0***REMOVED*** finding закрыт наконец)**: tight-фильтр через новый `_PytestCollectionVisitor` (ast.NodeVisitor с class-stack tracking) + добавлен публичный diagnostic `diagnose_test_count_gap(workspace)` для ground-truth Set-A vs Set-B validation. **Gap 30 → 0** после:
  - **Class-chain signature fix** — Set-A ключ теперь `(file, class_chain, function)` вместо `(file, line, function)`. Без этого одинаковые `test_register_and_get` в разных классах одного файла (TestAgentRegistry vs TestMCPRegistry) схлопывались в один set entry на pytest-стороне → 30 phantom ast_only
  - **Subprocess hardening** в `diagnose_test_count_gap`: `subprocess.run(...)` теперь имеет explicit `shell=False` (regression-guard против CQS §3.1); TimeoutExpired → `pytest_count=-1` sentinel + empty `ast_only` (не misleading full-set как раньше); parametrize count выводится для visibility
  - **Duplicate class rename** в `tests_09/test_consistency_check.py`: `TestRealProject` (на строке 616; конфликт с тем же именем на строке 381) → **`TestRealWorkspaceConsistent`**. pytest collects only last class with same name per module, поэтому первая группа из 12 test_* методов была phantom в ast_only даже после фильтра; rename делает обе группы collectible
  - **3-tuple unpack fix** в `count_test_functions`: предыдущая версия распаковывала `(total, _excluded)` пока `diagnose_test_collection` возвращает `(total, exclusions, counted)` → 20 падений `ValueError: too many values to unpack (expected 2, got 3)` в `test_consistency_check.py::TestCountTestFunctions` / `TestCheckTestCounter` / `TestReport`. Теперь: `total, _excluded, _counted = diagnose_test_collection(workspace)`

### Добавлено
- **6 regression tests** в `tests_09/test_consistency_check.py::TestPytestCollectionVisitor` (+ новая секция в TestCountCountSectionGrouping):
  - `test_visitor_counts_module_level_function` — `def test_x()` на module level → counted
  - `test_visitor_counts_test_prefixed_class_method` — method класса с именем `TestXxx` → counted
  - `test_visitor_skips_helper_class_method` — method `IntegrationHelper.test_y` → excluded с reason
  - `test_visitor_skips_pytest_fixture_decorated` — `@pytest.fixture` над `test_z` → excluded
  - `test_visitor_counts_unittest_testcase_subclass` — `class LegacyTC(unittest.TestCase)` → counted через TestCase inheritance rule
  - `test_visitor_counts_async_module_level` — `async def test_async()` → counted (асинхронные тесты тоже собираются)
  - **e2e regression**: `test_count_test_functions_matches_pytest_collect_only_on_real_project` — инвариант: для PROJECT_ROOT `count_test_functions == pytest --collect-only count` (клозюр gap<=1). Если кто-то завтра снова введёт duplicate class names ИЛИ сломает visitor contract, это ловится на pre-commit / CI, не на проде

### Проверка
- `python -m pytest tests_09/test_consistency_check.py -q` — **47 passed** (39 было + 6 новых TestPytestCollectionVisitor)
- `python -m pytest tests_09/ -q` — **1991 passed, 1 skipped, 0 failures** (exit 0; 1991 collected) — counter reconciles AST ↔ pytest на реальном проекте (gap = 0)
- `python -c 'from scripts_01.consistency_check import diagnose_test_count_gap; ...'` — `ast_count=1883, pytest_count=1883, ast_only=[***REMOVED***, pytest_only=[***REMOVED***, parametrize_doubled=2` (ground-truth подтвержжёт)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; test_counter, naming_convention и 7 других проверок согласованы)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)
- `python -m py_compile scripts_01/consistency_check.py tests_09/test_consistency_check.py` — 0 errors

### Code review
- `code-reviewer-minimax-m3` (final round, parallel с validation): **approved** (0 blocking). 3 non-blocking observations зафиксированы как follow-ups: (а) `class_chain` хранится как `list` (mutable) в `counted` dict — безопасно сегодня через `_chain_key()=str`, но downstream callers могут нарваться на unhashable list; (б) 1 sla line потенциально содержит stale comment-version ref в `count_test_functions` docstring (`round-1 5.38.0 reviewer consistency math finding` — это conversation-context noise); (в) `pytest_count=-1` sentinel для TimeoutExpired задокументирован inline, но неконтрактно исключит скусчные intermediate uses

---


## [5.39.1***REMOVED*** — 2026-08-02

### Добавлено
- **Hardening reviewer notes #1 + #2 для [5.39.0***REMOVED***** ([phone_control_mcp.py***REMOVED***(scripts_01/phone_control_mcp.py)):
  - **#1: `threading.Lock()` в `TunnelManager`** (защита от race между concurrent `tunnel_up` callers). Инициализируется в `__init__`, оборачивает тела `start()` и `stop()` в `with self._lock:`. Атомарный critical section «check `is_active` → `_spawn()` → assign `_spec`» — второй concurrent caller сразу получает `RuntimeError("already active")` вместо двойного создания Popen
  - **#2: `start_new_session=True` в `subprocess.Popen()`** (для SIGKILL-detach). На POSIX вызывает `os.setsid()` в child → cloudflared становится лидером новой session. Если родитель убит `kill -9` (OOM/crash-loop) — subprocess переживёт вместо orphan-leak. Без флага: cascade kill по process group + orphan subprocess. Doc-anchor: см. [mcp_fastapi.py***REMOVED***(scripts_01/mcp_fastapi.py) для полного lifecycle (там cleanup на уровне FastAPI process)
- **2 regression-теста** в [tests_09/test_phone_control_mcp.py***REMOVED***(tests_09/test_phone_control_mcp.py):
  - `test_popen_uses_start_new_session` — monkeypatch `subprocess.Popen`, verify `start_new_session=True` в kwargs (канарейка против accidental flag-removal)
  - `test_concurrent_start_serializes_via_lock` — два `threading.Thread`'а входят в `start()` одновременно, один успевает + получает `TunnelSpec`, другой получает `RuntimeError("already active")`. Verify: `mgr._spec` хранит ровно ОДИН spec (не два leaked Popen), `t1/alive=False AND t2/alive=False` (lock не deadlock'ит)
- **Registry sweep** (round-4 reviewer footgun check): [prompts_11/046_09_tripwire_v1.md***REMOVED***(pompts_11/046_09_tripwire_v1.md) → **`pompts_11/046_09_tripwire_v1.md`** (NNN_TT_name convention, topic 09 = canonical/test). Содержимое файла = заглушка от тебя («вот и проверим, скажи прочитал или нет?») — ZERO autofill, tripwire сохранён

### Исправлено
- **CHANGELOG [5.39.0***REMOVED*** broken link** (`consistency_check.py` без `scripts_01/` prefix в строке 29 → drift_check false-positive). Теперь: `[code-reviewer-minimax-m3***REMOVED***(scripts_01/consistency_check.py)` (canonical path)

### Обновлено
- **Counter bump 1881 → 1883** (+2 hardening regression-теста). Все 3 анкора согласованы: AST=1883 (consistency_check `count_test_functions`), CHANGELOG=1883, CQS §11.6 target=`1883+ passed`
- [docs_10/core/CODE_QUALITY_STANDARD.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) §11.6 regression target: `1881+` → **`1883+`** (auto-locked `check_test_counter`)

### Проверка
- `python -m pytest tests_09/test_phone_control_mcp.py -q` — **27 passed** in 1.71s (exit 0)
- Нвые тесты isolated: `test_popen_uses_start_new_session` + `test_concurrent_start_serializes_via_lock` both PASS
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0) после counter bump + promt46 rename
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0) после CHANGELOG link-fix
- `python -m py_compile scripts_01/phone_control_mcp.py tests_09/test_phone_control_mcp.py` — 0 errors

### Code review
- `code-reviewer-minimax-m3` round-4 в parallel с pytest: **approved** (0 blocking). 3 non-blocking observations зафиксированы как follow-ups:
  - `test_popen_uses_start_new_session` — kwarg-capture regression, не functional POSIX-тест (acceptable pattern; functional требует real-subprocess + signal — тяжёлый + fragile)
  - `atexit.register(self._atexit_cleanup)` accumulates on each `_spawn()` success (idempotent — multiple invocations safe, но overhead линеен reuses. Сейчас `atexit.unregister` в `stop()` НЕ зовётся — был pre-existing pattern, не от hardening)
  - Concurrent test ordering — `results["first_spec"***REMOVED***` может быть из любого thread'а (race на разные dict-keys, CPython-GIL-atomic, для portable-Python надо `queue.Queue` — minor)

---


## [5.39.0***REMOVED*** — 2026-08-02

### Добавлено
- **pomt45_05 first slice — тонкий MCP tool-server wrapper для phone control** ([pompts_11/045_05_mcp_cloudflare_phone_control.md***REMOVED***(pompts_11/045_05_mcp_cloudflare_phone_control.md)):
  - **[scripts_01/phone_control_mcp.py***REMOVED***(scripts_01/phone_control_mcp.py)** (≈320 LOC, stdlib-only): 4 класса — `TunnelSpec` dataclass + `TunnelManager` (`subprocess.Popen` argv-list с daemon-reader + atexit cleanup + ready-timeout), `PhoneAPIClient` (urllib-only, bearer-auth, fail-fast без ретраев), `BaseTool` + 3 инструмента (`SendSmsTool`/`GetContactsTool`/`PlayMusicTool`) с lightweight JSON-schema (required + isinstance + reject-extras), `PhoneControlMCP` orchestrator (bearer-constant-time + origin allowlist + tools/list + tools/call + tunnel_up/down/status), argparse CLI
  - **3 MCP tools:** `send_sms(to:str, body:str) → POST /send-sms`, `get_contacts(limit?:int) → GET /get-contacts?limit=N`, `play_music(artist:str, track:str) → POST /play-music` — payload envelope `{success, data|error***REMOVED***`
  - **Tunnel manager:** cloudflared argv-list `["cloudflared","tunnel","--url","http://localhost:PORT"***REMOVED***` (no `shell=True`, канарейка в `test_subprocess_argv_is_list_no_shell`); ngrok fallback на `FREEBUFF_PHONE_NGROK_BIN` если cloudflared отсутствует. Mock-script-based lifecycle test (`_write_mock_cloudflared` в tmpdir)
  - **Endpoints MCP:** `tools-list`, `tools-call <name> '<json-args>'`, `tunnel up|down|status --port N` через env-driven bearer (`FREEBUFF_PHONE_MCP_TOKEN`) + origin allowlist (`FREEBUFF_PHONE_ORIGINS`)
- **Tests:** [tests_09/test_phone_control_mcp.py***REMOVED***(tests_09/test_phone_control_mcp.py) — **25 новых тестов** в 13 test-classes (23 initial + 2 fix-validation):
  - Tool dispatch happy path: send_sms/get_contacts(2)/play_music — mocked PhoneAPIClient
  - Schema validation: missing required, wrong type (string-as-int, int-as-string), bool-rejected-as-int, **unknown-kwargs rejected (reviewer fix #2)**, radius/main sanity
  - Orchestrator auth: bearer missing (401), bearer invalid (401), bearer too long (DoS-guard 4096 chars)
  - Orchestrator origin: not in allowlist (403), wildcard (`*`) allow
  - Orchestrator tool dispatch: unknown tool (404 + available list), tool execution error (400 + safe error string)
  - Orchestrator tools/list: 3 tools returned with full inputSchema
  - **Tunnel security: subprocess Popen вызывается с `shell=False` + argv-list** (канарейка идёт в обратку на round-1 reviewer finding, passed under mock)
  - Tunnel lifecycle: start + URL extracted из mock-script stderr + stop terminates subprocess; already-active-raises
  - Tunnel orchestrator: status-when-inactive + up-when-cloudflared-missing returns 503

### Исправлено
- **Round-1 reviewer findings, 4 фикса применены в этом релизе** ([code-reviewer-minimax-m3***REMOVED***(scripts_01/consistency_check.py) round-1 в parallel с pytest):
  1. **Schema bool/int isinstance упрощён** — убран convoluted double-`if` логика, заменён на clean if/elif + explicit `isinstance(value, bool)` исключением
  2. **Extra kwargs rejection** — `BaseTool.validate()` теперь REJECTS unknown parameters через `ToolError` (не silent passthrough к upstream API → защита от SSRF/data-leak vector)
  3. **`import hmac` поднят на top of file** — был module-local внутри `check_bearer` (PEP 8)
  4. **Tunnel reader-thread без post-URL drain** — `_reader()` теперь exits сразу после URL captured (без `proc.stderr.read()`" drain, мог deadlock если subprocess пишет > pipe buffer после URL); parent main-loop terminate subprocess anyway

### Проверка
- `python -m pytest tests_09/test_phone_control_mcp.py -q` — **25 passed** in 1.71s (exit 0)
- `python -m py_compile scripts_01/phone_control_mcp.py tests_09/test_phone_control_mcp.py` — 0 errors
- `python scripts_01/consistency_check.py --report` — Consistent после counter bump
- `python scripts_01/drift_check.py --force --report` — No drift detected

### Code review
- `code-reviewer-minimax-m3` (round-1 в parallel): поймал 2 blocking + 2 non-blocking; round-2 (после фиксов) — ship-it approved

### Отложено (отдельные deliverables)
- **Реальный Android-bridge** (Tasker / Termux:API) — следующий slice, подменит urllib fallback на реальный Android integration
- **Cloudflare Workers SSE-delivery** (Wrangler config) — отдельный deploy-pipeline, лежит в `pompts_11/045_05_mcp_cloudflare_phone_control.md` (out of scope для thin wrapper)
- **OpenAPI spec + Speakeasy generation** — генератор-шаг в отдельной ветке, Python-обёртка уже соответствует его выходу

---


## [5.38.0***REMOVED*** — 2026-08-02

### Добавлено
- **v1 `generate_meeting_briefing` в [task_manager.py***REMOVED***(scripts_01/task_manager.py) (042_06 Фаза E → код):** первая функциональная версия вместо детерминированного stub'а:
  - **Pipeline:** 4 изолированных gather-функции, каждый со своим try/except → graceful degradation → пустой результат:
    - `_gather_project_meta(rid, conn)` — name/description/created_at из `projects`
    - `_gather_linked_resources(project_id, db_path)` — через `work_area_view.resources_for_project()` (Work Area as View, правило 7)
    - `_gather_recent_tasks(project_id, db_path)` — 5 свежих соседних задач того же проекта (sibling-tasks контекст)
    - `_gather_knowledge_hits(query)` — `KnowledgeEngine.search(query, top_k=5, mode='hybrid')` с lazy init; project_id + task.title используются как запрос
  - **Опциональная LLM-синтезация** через `ModelGateway().generate_by_capabilities(['meeting_brief'***REMOVED***)` — включается ТОЛЬКО если `FREEBUFF_BRIEFING_USE_LLM=1` (default OFF → CI-детерминизм, безопасный fallback)
  - **Deterministic fallback** (если LLM отключен/упал/нет ключей): обогащённый v0-шаблон с реальными списками ресурсов/сниппетов/соседних задач в `## Контекст`
  - **Контракт неизменён:** сигнатура `generate_meeting_briefing(task_id, db_path)` → `str | None`, ставит `briefing_generated=1`
  - **Регрессионная защита `_generate_llm_synthesis`:** даже если monkeypatch взорвётся, pipeline НЕ падает — fallback к детерминированному шаблону (поймано в раунде-10)
- **Constants:** `_BRIEF_MAX_RESOURCES=10`, `_BRIEF_MAX_RECENT_TASKS=5`, `_BRIEF_MAX_KNOWLEDGE_HITS=3`, `_BRIEF_SNIPPET_CHARS=300` (overflow-protection)
- **Tests:** [test_task_manager.py***REMOVED***(tests_09/test_task_manager.py) — новый **class TestGenerateBriefingV1** (9 тестов):
  - `test_v1_briefing_contains_project_name_and_resource` — реальный проект + ресурс из `project_resources` отображаются в briefing
  - `test_v1_graceful_no_knowledge_index` — monkeypatch `_gather_knowledge_hits` → `[***REMOVED***`; briefing всё равно генерируется (graceful degradation, нет жёсткой зависимости от knowledge index)
  - `test_v1_graceful_llm_mock_explosion` — `FREEBUFF_BRIEFING_USE_LLM=1` + `_generate_llm_synthesis` raises → pipeline НЕ падает, возвращает fallback
  - `test_v1_default_llm_off` — по умолчанию LLM отключён (CI-детерминизм)
  - `test_v1_resource_limit_truncates` — 12 ресурсов → 10 в briefing + truncation marker
  - `test_v1_recent_tasks_excludes_self` — текущая задача не попадает в «recent siblings»
  - `test_v1_markdown_sections_present` — структура `## Проект / ## Ресурсы / ## Ближайшие задачи / ## Контекст`
  - `test_v1_briefing_generated_flag_persists` — после вызова `briefing_generated=1` в БД
  - `test_v1_idempotent_regeneration` — повторный вызов не дублирует side-effects
- **Переименование промта:** `pompts_11/promt44.md` → **`pompts_11/044_09_canonical_history_mission.md`** (конвенция NNN_TT_имя; тема 09 = canonical history mission; для drift-страховки имени)
- **Canonical history anchor:** `docs_10/history/SESSION_UNDERSTANDING_2026-08-02.md` (drift_check не находит false-positive после замены broken deep-relative ссылок на workspace-relative константы)

### Обновлено
- **Счётчик тестов `tests_09` (кумулятивно):** **1770 → 1881 через 5.37.0→5.38.0**. В этом релизе: **+9 v1-тестов** в [test_task_manager.py***REMOVED***(tests_09/test_task_manager.py) `TestGenerateBriefingV1` (+4 в `TestNamingConventionLegacyRedirect` под этим релизом, итого брутто +13 в реестрах после перерегистрации счётчика)
- [CODE_QUALITY_STANDARD.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) §11.6 regression target: `1847+` → **`1881+`** (auto-locked consistency_check `check_test_counter`)
- **Consistency check: legacy-redirect tolerance** — [consistency_check.py***REMOVED***(scripts_01/consistency_check.py) `/check_naming_convention` пропускает legacy top-level shim (`freebuff_plugin/` → `freebuff_plugin_03/`), если canonical живёт, иначе флагует как orphan. Зеркалит [drift_check.py***REMOVED***(scripts_01/drift_check.py)::_LEGACY_TOP_LEVEL_REDIRECTS (5.37.1), закрывает ложное нарушение `имя_NN` от pre-rename shell history / tmux send-keys

### Проверка
- `python -m pytest tests_09/test_task_manager.py::TestGenerateBriefingV1 -q` — **9 passed**
- `python -m pytest tests_09/ -q` — **1881 passed, 1 skipped, 0 failures** (exit 0)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-minimax-m3` (parallel with validation): pre-implementation design validation через `thinker-with-files-gemini` подтвердил architecture (`gather FIRST → optional LLM → fallback augmentation`); post-implementation — _generate_llm_synthesis try/except fix, _gather_knowledge_hits monkeypatch test, drift-link rewrite, counter bump — все применены

---


## [5.37.1***REMOVED*** — 2026-08-02

### Исправлено
- **Stale `bash freebuff_plugin/monitor.sh` после NN-name rename** — пользователи (и stale shell history / tmux send-keys, зафиксированные до ренейма директорий) получали `No such file or directory` на устаревшем пути. Создан тонкий **compat-shim** [freebuff_plugin/monitor.sh***REMOVED***(freebuff_plugin/monitor.sh) (≈20 строк), который warning'ит в stderr и делегирует в канонический [freebuff_plugin_03/monitor.sh***REMOVED***(freebuff_plugin_03/monitor.sh) через `exec`. Не маскирует баги: если canonical отсутствует — `exit 127`. Новые вызовы должны всегда использовать канонический путь.
- **[drift_check.py***REMOVED***(scripts_01/drift_check.py)** — новая константа `_LEGACY_TOP_LEVEL_REDIRECTS` (зеркалит существующий паттерн `_ADR_REDIRECTS`) и хелпер `_is_legacy_redirect_satisfied(workspace, top_dir)`. `check_directory_structure` теперь пропускает top-level директории, которые сушествуют только как backward-compat forwarder и указывают на реальное каноническое расположение — закрыло будущий false-positive «exists but not described in BUFFY.md/RULES.md» для `freebuff_plugin/` (и любых будущих аналогичных shim'ов). Дефолтный список: `freebuff_plugin` → `freebuff_plugin_03`.

### Проверка
- `bash -n freebuff_plugin/monitor.sh` — OK (валидный bash syntax)
- `bash freebuff_plugin/monitor.sh` (без аргументов) — warning в stderr + exec → canonical → `exit 1` (canonical [ -n "$SESSION_ID" ***REMOVED*** || exit 1); НЕ молчит и НЕ маскирует ошибки
- `python -m pytest tests_09/test_drift_check.py -q` — **33 passed** (29 старых + 4 регрессионных на `_is_legacy_redirect_satisfied` / `_LEGACY_TOP_LEVEL_REDIRECTS`)
- `python scripts_01/drift_check.py --force --report` — `Directory structure drift: No discrepancies found.` (новый shim не триггерит structural-drift; оставшиеся report-points — broken links в `docs_10/INDEX.md` + unindexed `SESSION_UNDERSTANDING_2026-08-02.md` — pre-existing, не связаны с этим фиксом)
- Канонический путь `freebuff_plugin_03/monitor.sh` и все вызывающие (`wrapper.py:254`, `monitor.sh:21`) **не тронуты**

### Code review
- `code-reviewer-minimax-m3` (parallel с `bash -n` + `drift_check` + `pytest`): пропустил **2 critical** + 1 minor итерации 1 → оба исправлены в этом релизе:
  - ✔ добавлены 4 регрессионных теста в [test_drift_check.py***REMOVED***(tests_09/test_drift_check.py) (`test_legacy_redirect_satisfied_when_canonical_exists` / `_flagged_when_canonical_missing` / `_non_legacy_undeclared_dir_still_flagged` / `_legacy_redirect_helper_unit`) — закрывает silent-skip новый code-path
  - ✔ `_LEGACY_TOP_LEVEL_REDIRECTS` values унифицированы в `str(Path(...))` (стилистически консистентно с `_ADR_REDIRECTS`)
  - ✔ shim upgraded: `#!/usr/bin/env bash` + dynamic `FREEBUFF_ROOT` через `BASH_SOURCE` (Termux + Linux CI + macOS), `exec bash "$CANONICAL"` без зависимости от Termux-shebang canonical

---


## [5.37.0***REMOVED*** — 2026-08-02

### Добавлено
- **Meeting Tasks backend (042_06 Фаза E — код, долгожданно вместо дoк-цикла):** [task_manager.py***REMOVED***(scripts_01/task_manager.py):
  - Schema `tasks` в `data_13/context.db`: id, project_id (FK→projects.name, declaration-only — runtime enforcement пропущен по согласованности с `work_area_view.py`), title, description, task_type ∈ {digital, meeting, document***REMOVED***, status ∈ {pending, in_progress, done, cancelled***REMOVED***, priority ∈ {low, normal, high, critical***REMOVED***, meeting_time, location, participants (JSON-list), briefing_generated (0/1), created_at, updated_at; индексы `idx_tasks_project/type/status`
  - CRUD: `create_task`, `show_task`, `get_tasks` (фильтры type/status, `ORDER BY datetime(created_at) DESC, id DESC` — детерминизм при одинаковом created_at), `update_task` (частичное, иммутабельные `id`/`created_at`/`briefing_generated`), `delete_task` (идемпотентно — False на повторе)
  - `generate_meeting_briefing(task_id)` — заглушка v0: markdown (проект/время/место/участники/точки/контекст), ставит `briefing_generated=1`; resilient к мусорному JSON в participants (выдаёт `”(не указаны)”`)
  - **Strict-mode (правило 8, Context-Aware Routing)**: meeting_time/location/participants валидны ТОЛЬКО с task_type='meeting' — иначе `ValueError` (без тихого coerce — предыдущий вариант терял данные без предупреждения, пойман в батче-ревью)
  - Argparse CLI: subcommands `create / list / show / update / delete / briefing` через `python scripts_01/task_manager.py --type meeting --time "..." --location "..." --participants '["a","b"***REMOVED***'`
- **3 REST endpoints для 043 frontend dashboard** в [mcp_fastapi.py***REMOVED***(scripts_01/mcp_fastapi.py) (восполняет `api.ts: getProjects/getTasks/createTask`):
  - `GET /api/v1/projects` — список проектов (мягкий fallback на пустой успех, если таблицы `projects` нет — фронт может монтироваться до `scan_projects`)
  - `GET /api/v1/tasks?project_id=X&type=Y&status=Z` — задачи проекта через `task_manager.get_tasks` (400 на невалидный фильтр через ValueError-проброс)
  - `POST /api/v1/tasks` — создать задачу через `task_manager.create_task` (201 на успех, 400 на bad payload, единый REST-контракт `{success, data***REMOVED***` / `{success: false, error***REMOVED***` через shared `_policy_error`)
  - Bearer-auth (`Depends(verify_bearer_token)`, consistent с `/mcp` и `/policy/*`); origin-check через `_validate_origin`
- **Tests:**
  - [test_task_manager.py***REMOVED***(tests_09/test_task_manager.py) — **57 новых тестов**: TestInitDB (6), TestCreateTask (10: digital/meeting/document flows + strict-mode), TestGetTasks (6), TestShowTask (2), TestUpdateTask (7), TestDeleteTask (2), TestGenerateBriefing (4: meeting / non-meeting / missing / corrupted-JSON), TestCLI (11), TestCanonicalInvariants (3: фиксирует VALID_TASK_TYPES/STATUSES/PRIORITIES как канониеские константы, чтобы доступ не сиротant)
  - [test_mcp_fastapi.py***REMOVED***(tests_09/test_mcp_fastapi.py) — **+11 новых** в `TestMeetingTasksREST`: projects list (empty/seeded sorted-by-name), tasks GET (empty/type-filter/invalid-filter), tasks POST (digital-201/meeting-with-full-attrs/missing-title/invalid-JSON/non-dict/meeting-attr-on-digital→400)

### Обновлено
- **Счётчик `tests_09` AST** 1770 → **1852**+ (+68: 57 task_manager + 11 mcp_fastapi REST); зафиксирован автоматически 9-й проверкой `check_test_counter` в [consistency_check.py***REMOVED***(scripts_01/consistency_check.py)
- [CODE_QUALITY_STANDARD.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) §11.6 target регрессионных тестов: `1770+` → **`1847+`** (закрыто “колесо дрейфа счётчика”)

### Проверка
- `python -m pytest tests_09/ -q` — **1852 passed, 1 skipped, 0 failures** (exit 0; 1839 collected) — было 1770+1
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; в т.ч. `test_counter` после перепрогонки соответствует 1852)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-minimax-m3` (5 раундов in parallel с pytest): ship-it approved; критичные баги пойманы во 2-5 раунде: silent coerce в `create_task` (meeting-атрибуты у non-meeting тихо обнулялись) → strict ValueError; `PRAGMA foreign_keys=ON` обда UK-крешu DELETE FROM tasks; `clean_fields[key***REMOVED*** = value` пропущен в `update_task` — молчаливый no-op вместо UPDATE; ORDER BY sort-fragility при tie в created_at; `time.sleep(0.01)` в тесте.

---


## [5.36.0***REMOVED*** — 2026-08-01

### Исправлено
- **Repo-wide rename-risks sweep** — закрыл 5 предсуществующих stale-ссылок на старые имена каталогов в shell-скриптах (после массового rename `имя_NN` в [5.34.0***REMOVED***(CHANGELOG.md)):
  - **[status_report.sh***REMOVED***(status_report.sh) §6** — for-loop doc-paths обновлены на `docs_10/vision/VISION_3.0.md`, `docs_10/core/ARCHITECTURE_MANIFEST.md`, `docs_10/core/GLOSSARY.md` + свап `docs_10/vision/UI_CONCEPTS.md`/`docs_10/vision/IMPLEMENTATION_STATUS.md` → `docs_10/core/LIFECYCLE.md` (архивные vision-доки заменены каноническим source-of-truth; устранён log-шум «NOT FOUND», который накапливался при каждом запуске скрипта)
  - **[status_report.sh***REMOVED***(status_report.sh) §7** — `data/context.db` → `data_13/context.db` (3 occurrences: if-check + 2 sqlite3 вызова `.tables`/`.schema`)
  - **[status_report.sh***REMOVED***(status_report.sh) §8** — `runtime/providers/` → `runtime_05/providers/`, `freebuff_plugin/` → `freebuff_plugin_03/` (2 блока по 4 строки каждый — check + ls)
  - **[monitor.sh***REMOVED***(freebuff_plugin_03/monitor.sh) line 12** — `PLUGIN_DIR="$FREEBUFF_ROOT/freebuff_plugin"` → `PLUGIN_DIR="$FREEBUFF_ROOT/freebuff_plugin_03"` (2 downstream-ссылки через `$PLUGIN_DIR/bridge.py` на строках 84 и 121 резолвятся автоматически — никаких других правок не потребовалось)
  - **[generate_project_dump.sh***REMOVED***(generate_project_dump.sh) line 108** — `freebuff_plugin_03/runtime/adapters/adapter.py` (несуществующий путь: подкаталог `runtime/adapters/` содержит `claude.py`/`freebuff.py`, а не `adapter.py`) → `freebuff_plugin_03/runtime/adapter.py` (правильное расположение; 2 occurrences через `allowMultiple`: if-check + `cat`)
- **Broader repo-wide sweep** (по `.json`/`.yaml`/`.toml`/`.ini`/`.cfg` + `tests_09/` + `pompts_11/` + `.freebuff/`) — **других stale-ссылок не найдено** (3 скрипта были единственными источниками rename-fallout за пределами Python-кода). Подтверждает, что массовый rename в [5.34.0***REMOVED***(CHANGELOG.md) был полностью зачищен на уровне shell-инфраструктуры

### Проверка
- `bash -n status_report.sh` — OK (валидный bash syntax после 9 замен / 2 блоков)
- `bash -n freebuff_plugin_03/monitor.sh` — OK
- `bash -n generate_project_dump.sh` — OK
- `grep -rnE '("docs/|data/context\.db|/runtime/providers\b|FREEBUFF_ROOT/freebuff_plugin[#"***REMOVED***|/runtime/adapters/adapter\.py)' --include='*.sh' --include='*.py' --include='*.md' .` (исключая `.git`/`projects_17`/`trash_21`/актуальные новые пути) — **0 совпадений** (workspace)
- Тот же grep по `.json`/`.yaml`/`.toml`/`.ini`/`.cfg` + `tests_09/` + `pompts_11/` + `.freebuff/` — **0 совпадений** (broader)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code_reviewer_minimax_m3` (1 раунд в parallel с `bash -n` + `consistency_check` + `drift_check`): одобрено; оба actionable item учтены (§6 LIFECYCLE-свап вместо архивных vision-док; broadened sweep по `.json`/`.yaml`/`.ini`)

---


## [5.35.0***REMOVED*** — 2026-08-01

### Добавлено
- **9-я проверка `test_counter` в [consistency_check.py***REMOVED***(scripts_01/consistency_check.py)** — авто-сверка счётчика тестов с реальностью:
  - `count_test_functions()` — AST-подсчёт `def test_*`/`async def test_*` в `tests_09/**/*.py` (рекурсивно, устойчив к OSError/SyntaxError)
  - `check_test_counter()` — сверяет AST-реальность с двумя якорями: свежая строка полного прогона в [CHANGELOG.md***REMOVED***(CHANGELOG.md) (`pytest tests_09/ -q` → `N passed`) и цель правила 11.6 в [CODE_QUALITY_STANDARD.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) (`цель: N+ passed`)
  - Проверка сразу поймала реальный дрейф: добавление тестов (12 новых в `TestCountTestFunctions`/`TestCheckTestCounter` + регрессионный на порядок версий) подняло реальность с 1757 до **1770** — счётчики обновлены в этом релизе
  - `_full_suite_count()` извлекает счётчик из секции CHANGELOG с **максимальным номером версии** (`## [X.Y.Z***REMOVED***`), а не первой по файлу — устойчиво к случайному нарушению newest-first порядка (Keep a Changelog)
- **Тесты**: [test_consistency_check.py***REMOVED***(tests_09/test_consistency_check.py) — `TestCountTestFunctions` (5 тестов: подсчёт, рекурсия, не-test функции, async, отсутствие каталога) + `TestCheckTestCounter` (8 тестов: чисто, устаревший CHANGELOG, устаревшая цель, отсутствующие строки, пропуск при отсутствии реестров, ключ отчёта, регрессия на нарушенный порядок версий)

### Проверка
- `python -m pytest tests_09/ -q` — **1770 passed, 1 skipped, 0 failures** (exit 0; 1771 collected)
- `python scripts_01/consistency_check.py --report` — Consistent (exit 0; новая проверка test_counter зелёная)
- `python scripts_01/drift_check.py --force --report` — No drift (exit 0)

---


## [5.34.0***REMOVED*** — 2026-08-01

### Исправлено
- **Массовый rename-fallout от переименования каталогов** (закрыл 110 падений тестов: было `78 failed, 32 errors` → стало **1757 passed, 1 skipped**):
  - `tests_09/`: patch-строки `scripts.*` → `scripts_01.*` (test_stream_session/test_stream_bridge/test_notification/test_work_area_view/test_freebuff); mock-пути `freebuff_plugin.*` → `freebuff_plugin_03.*` (test_runtime_abstraction/test_bootstrap_engine); payload-ключ `"data_13"` → `"data"` (test_event_store)
  - `core_02/interfaces.py`: `AgentResult.to_dict()` отдавал `"data_13"` вместо `"data"` (rename-fallout в продакшн-коде)
  - `tests_09/test_verifier.py`: вход шаблона `src` → `src_06`; `tests_09/test_context_manager.py`: таблица `projects` (не `projects_17`); `tests_09/test_work_area_view.py`: подкоманда CLI `projects` (не `projects_17`); `tests_09/core/test_interfaces.py`: ключ dict `data_13` → `data`; `tests_09/test_bootstrap_engine.py`: путь `freebuff_plugin/bootstrap/profiles.yaml` → `freebuff_plugin_03/...`
- **`scripts_01/mcp_fastapi.py`**: Vault KV v2 path-stripping — `"/data_13/"` → `"/data/"` (rename-fallout от глобального sed; hvac принимает путь без mount-префикса, сегмент KV v2 — `data`)
- **`scripts_01/drift_check.py`**: `trash_21` добавлен в `_KNOWLEDGE_IGNORE_DIRS` (мусорка — архив по дизайну, не источник знаний; закрыло false-positive broken-links от `project_dump`)
- **Косметика**: `scripts.` → `scripts_01.` в комментариях/docstrings `freebuff_plugin_03/__init__.py`, `bridge.py`, `INTEGRATION_CONTRACT.md` (только комментарии, исполняемый код не тронут)

### Добавлено
- **Переименование промта `pompts_11/promt43.md` → `pompts_11/043_08_frontend_workspace_os_ui.md`** (конвенция `NNN_TT_имя`, тема 08 = prototype; фронтенд glassmorphism UI для FastAPI) — закрыло issue `naming_convention`
- **Маппинг промтов** в [FINAL_STRUCTURE.md***REMOVED***(docs_10/core/FINAL_STRUCTURE.md): строки `promt42.md → 042_06_dokumentaciya_meeting_tasks.md`, `promt43.md → 043_08_frontend_workspace_os_ui.md`
- **Реестры**: [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) — строки `042_06`/`043_08` (ACTIVE), ревизия pompts_11/ 36 → 38 файлов; [CODE_QUALITY_STANDARD.md***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) — цель регрессионных тестов 1143+ → **1757+**
- **Архив**: `project_dump_20260801_222022.md` + `.tar.gz` перенесены из корня репозитория в `trash_21/`, а `docs_10/audits/dump_20260801_222022/` (730K, слепок документации с заведомо битыми относительными ссылками) — в `trash_21/` (это и был последний источник broken-links в drift); удалён `pompts_11/042_06_dokumentaciya_meeting_tasks.md.bak`

### Проверка
- `python -m pytest tests_09/ -q` — **1757 passed, 1 skipped, 0 failures** (exit 0; был 1647 passed / 78 failed / 32 errors)
- `python scripts_01/consistency_check.py --report` — Consistent (exit 0; issue именования промта закрыт переименованием)
- `python scripts_01/drift_check.py --force --report` — No drift (exit 0; битые ссылки project_dump закрыты переносом в trash_21)


## [5.33.0***REMOVED*** — 2026-08-01

### Добавлено
- **Переименование промта `pompts_11/promt41.md` → `pompts_11/041_03_inventarizaciya_proekta.md`** (конвенция `NNN_TT_имя`, тема 03 = audit):
  - Файл не был под git-контролем → обычный `mv` (не `git mv`); ссылок на старое имя в репозитории не было — переименование безопасно
  - Закрыло единственный issue `consistency_check` (проверка `naming_convention`: промт не следовал схеме) — проверка стала зелёной
  - Зафиксировано в [FINAL_STRUCTURE.md***REMOVED***(docs_10/core/FINAL_STRUCTURE.md) (строка маппинга `promt41.md → 041_03`) и [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) (строка `041_03_inventarizaciya_proekta.md`, ACTIVE; заметка о ревизии pompts_11/ обновлена 35 → 36 файлов)
- **Создан [PROJECT_INVENTORY_REPORT_2026-08-01.md***REMOVED***(docs_10/audits/PROJECT_INVENTORY_REPORT_2026-08-01.md)** — полный отчёт по миссии промта 041_03:
  - 10 разделов: сводка (§0), инвентаризация документации (§1), кода (§2), двусторонний mapping «документация ↔ код» (§3), канонические Source of Truth (§4), оценка соответствия (§5), список дубликатов (§6), карта проекта (§7), сделано/осталось (§8), пошаговый план (§9), критерий завершения (§10)
  - Зафиксированы статусы документов (ACTIVE/LEGACY/ARCHIVED), актуальные/устаревшие компоненты, 5 дубликатов (включая открытый DEBT-2026-07-31-007 Telegram-ботов и документ-дубли PROMPT_IMPLEMENTATION/ops/AGENTS.md — решены позже в 5.31.0)
  - Зарегистрирован в [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) (audits, ACTIVE; счётчик 64 → 66: audits 6→7, pompts 18→19)

### Проверка
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0; issue именования промта закрыт переименованием)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash` (2 раунда): approved; ниты счётчиков исправлены (audits 14 → 19 файлов, scripts_01 54 → 48 модулей)

---


## [5.32.0***REMOVED*** — 2026-08-01

### Добавлено
- **Event Platform MCP-инструменты (5) в core-сервере** ([EVENT_PLATFORM_SPECIFICATION.md***REMOVED***(docs_10/core/EVENT_PLATFORM_SPECIFICATION.md) §9):
  - [mcp_server.py***REMOVED***(scripts_01/mcp_server.py): `_get_event_store()` (ленивый accessor на `freebuff_plugin_03.event.store.EventStore` с graceful degradation), `_register_event_tools()` — `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse` (McpTool, category `event`, схемы по §9) + 5 хендлеров (`_handle_event_*`) в контракте core-сервера `{success, data***REMOVED***`
  - Реестр MCP-инструментов обновлён: реализовано 47 → **52** (event 5), planned — только policy 5
- **Исправлен предсуществующий rename-fallout** в [freebuff_plugin_03/mcp_server.py***REMOVED***(freebuff_plugin_03/mcp_server.py): `from freebuff_plugin import bridge/wrapper` → `from freebuff_plugin_03 import bridge/wrapper` (модуль падал при импорте — `No module named 'freebuff_plugin'`, тот же класс, что закрыт в 5.29.0 для core-сервера); патчи в [test_mcp_event_tools.py***REMOVED***(tests_09/test_mcp_event_tools.py) переведены на `freebuff_plugin_03.mcp_server.*`
- **Тесты:** новый [test_mcp_event_tools_core.py***REMOVED***(tests_09/test_mcp_event_tools_core.py) (19 тестов: регистрация/схемы, search по типу/сессии/полям, timeline пустой/с событиями, replay пустой/с событиями/instant, audit пустой/decisions/фильтр target_type, pulse пустой/с _pulse, ошибки graceful) + существующие plugin-тесты теперь зелёные

### Проверка
- `python -m pytest tests_09/test_mcp_event_tools_core.py tests_09/test_mcp_event_tools.py -q` — **38 passed**
- `python -m pytest tests_09/test_mcp_server.py -q` — **127 passed**
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash`: approved; замечания учтены (реестр 47→52 + event planned→реализован, enum §9 → decision/action/config_change, чекбокс §14, monkeypatch-фикстура)

---


## [5.31.0***REMOVED*** — 2026-08-01

### Добавлено
- **Этап 5 консолидации — решены дубли документов** (план PROJECT_INVENTORY_REPORT §9):
  - `docs_10/core/PROMPT_IMPLEMENTATION_v1.0.md` (стаб-копия) → `trash_21/`; канон — `pompts_11/017_02_struktura_requirements_testy.md`
  - `docs_10/ops/AGENTS.md` (устаревший онбординг внешних агентов, кросс-проектные ссылки) → `trash_21/AGENTS_ops_duplicate.md`; канон — корневой `AGENTS.md`
- **Исправлены мёртвые ссылки на `docs_10/02-specs/`** в 7 docstring `freebuff_plugin_03/mesh/*/__init__.py` → `docs_10/core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` + `pompts_11/017_02_struktura_requirements_testy.md` (02-specs не создавать, DEBT-002)
- **Ссылки переведены на канон:** BUFFY.md, docs_10/INDEX.md, docs_10/core/RULES.md, docs_10/core/SYSTEM_INVENTORY.md
- **Реестры обновлены:** [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) (PROMPT_IMPLEMENTATION → ARCHIVED, ops/ 11→10 файлов, 017_02 — канон, trash_21 +2, ACTIVE 66→65, ARCHIVED 19→21), [FILE_REGISTRY.md***REMOVED***(docs_10/projects_meta/FILE_REGISTRY.md), [PROJECT_INVENTORY_REPORT***REMOVED***(docs_10/audits/PROJECT_INVENTORY_REPORT_2026-08-01.md) (открытые строки → Resolved, Дублирование документов 85%→100%)

### Проверка
- `python -m pytest tests_09/test_seed_knowledge.py -q` — **9 passed**
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash`: approved; ниты §0 отчёта (Главный вывод + строка Дублирование) исправлены

---


## [5.30.0***REMOVED*** — 2026-08-01

### Добавлено
- **Мердж Telegram-ботов через `BaseTGBot` (DEBT-2026-07-31-007 resolved) — первый пункт плана PROJECT_INVENTORY_REPORT:**
  - Новый общий предок [tgbot_base.py***REMOVED***(scripts_01/tgbot_base.py) (`BaseTGBot`): `load_dotenv` (.env-загрузка с setdefault), `build_application` (ApplicationBuilder с проверкой токена), `run_polling` (event-loop + обработка KeyboardInterrupt/ошибок, контракт exit 0/1), `error_handler` (лог + reply с try/except). Классовый атрибут `logger` для наследования
  - [telegram_bot.py***REMOVED***(scripts_01/telegram_bot.py) (`TelegramFreebuffBot`) и [tgbot.py***REMOVED***(freebuff_plugin_03/tgbot.py) (`ScenarioTGBot`) теперь наследуют `BaseTGBot`; дублирующиеся `.env`-блоки, polling-циклы и error handler удалены; слои сохранены (scripts = уведомления, freebuff_plugin = сценарии)
  - Убраны неиспользуемые импорты (`asyncio`, `ApplicationBuilder`) из обоих ботов
  - Тесты: новый [test_tgbot_base.py***REMOVED***(tests_09/test_tgbot_base.py) (18 тестов: load_dotenv, BaseTGBot, наследование) + существующие `test_telegram_bot.py`, `test_tgbot.py` — зелёные
- **Документы обновлены:** [ARCHITECTURAL_DEBT.md***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) §5.8 (DEBT-007 → Resolved), [MODULE_CONSOLIDATION.md***REMOVED***(docs_10/core/MODULE_CONSOLIDATION.md) §B (🔴 DUPLICATE → ✅ NO DUP), [PROJECT_INVENTORY_REPORT***REMOVED***(docs_10/audits/PROJECT_INVENTORY_REPORT_2026-08-01.md) (пункт 1 плана закрыт)

### Проверка
- `python -m pytest tests_09/test_tgbot_base.py tests_09/test_telegram_bot.py tests_09/test_tgbot.py -q` — **pass**
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash`: ship-it approved

---


## [5.29.0***REMOVED*** — 2026-08-01

### Добавлено
- **Правило 11 (promt37) — User-Choice Override через MCP / Bridge Layer** ([policy_override***REMOVED***(scripts_01/mcp_server.py) + [mcp_fastapi.py***REMOVED***(scripts_01/mcp_fastapi.py)):
  - **MCP-инструмент `policy_override`** в [mcp_server.py***REMOVED***(scripts_01/mcp_server.py): категория `policy`, schema `{message: string***REMOVED***` (обязателен). Handler `_handle_policy_override`: валидация message, ленивый `PolicyEngine` (graceful degradation → 503-семантика), `apply_override()` из `freebuff_plugin_03.policy` (распознаёт EN/RU фразы «use X instead of Y for Z», «используй X для Z», «switch Z to X»), событие `policy.override`, контракт `{success, data***REMOVED***` / `{success: False, error***REMOVED***`
  - **HTTP-эндпоинт `POST /policy/override`** в [mcp_fastapi.py***REMOVED***(scripts_01/mcp_fastapi.py): REST-доступ к override без MCP-протокола; Bearer auth (`verify_bearer_token`) + origin-check; `asyncio.to_thread` для sync-инициализации PolicyEngine и `apply_override` (не блокирует event loop); ошибки 400/403/422/500/503 в едином контракте `{success, error***REMOVED***` (намеренно отличном от JSON-RPC `_json_error`)
  - **Bridge Layer:** инструмент автоматически доступен MCP-клиентам через `_forward_to_mcp` (динамический проброс — ручная регистрация не нужна)
  - **Тесты:** `TestPolicyOverrideTool` (7) в [test_mcp_server.py***REMOVED***(tests_09/test_mcp_server.py) + `TestPolicyOverrideEndpoint` (9) в [test_mcp_fastapi.py***REMOVED***(tests_09/test_mcp_fastapi.py) + интеграционный `test_forward_policy_override_via_bridge` в [test_bridge_layer.py***REMOVED***(tests_09/test_bridge_layer.py) (полный путь ACP → Bridge → MCP с валидацией payload `success`/`runtime`/`applied`)
  - **Документация MCP-инструмента и эндпоинта:**
    - [POLICY_ENGINE_SPECIFICATION.md***REMOVED***(docs_10/core/POLICY_ENGINE_SPECIFICATION.md) §8 — пометка «✅ Реализован» + JSON-схема `policy_override` с `required: ["message"***REMOVED***` + упоминание просмотра текущих политик: CLI `freebuff policy list/get` реализован, HTTP GET-эндпоинт (`GET /policy` / `GET /policy/status`) — следующий шаг (REST-доступ к правилу 11: чтение GET + запись POST)
    - [PLUGIN_CONTRACT_SPECIFICATION.md***REMOVED***(docs_10/plugin/PLUGIN_CONTRACT_SPECIFICATION.md) §8 — справочная таблица MCP-инструментов ядра (v1.1.0; `policy_override` реализован, `policy_apply/list/status`, `pack_install`, `capability_list` — planned)
    - [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) — заметки в записях POLICY_ENGINE_SPECIFICATION и docs_10/plugin/ +
      **новая секция «MCP-инструменты ядра (реестр)»**: единый реестр всех 47 зарегистрированных инструментов
      `mcp_server.py` по категориям (policy/runtime/bootstrap/knowledge/memory/session/context/plugins/bridge/roles/
      presence/collaboration/distributed/rag/pulse) с пометками реализован ✅ / planned 🔶 (policy 5 + event 5 из
      EVENT_PLATFORM_SPECIFICATION §6)

### Исправлено
- **Rename-fallout `freebuff_plugin` → `freebuff_plugin_03`** (предсуществующие падения, устранены по пути):
  - 4 устаревших ленивых импорта в [mcp_server.py***REMOVED***(scripts_01/mcp_server.py) (`BridgeLayer`, `BootstrapEngine`, `RuntimeRegistry`, `RuntimeCapabilityRegistry` — старый каталог `freebuff_plugin` не существовал; новые символы экспортируются через `__getattr__` в `freebuff_plugin_03/__init__.py`) — закрыло 10 падений `No module named 'freebuff_plugin'` в `TestBootstrapTools`/`TestRuntimeTools`
  - Устаревший mock-путь в [test_mcp_server.py***REMOVED***(tests_09/test_mcp_server.py) (`freebuff_plugin.runtime.registry.RuntimeRegistry` → `freebuff_plugin_03.runtime.registry.RuntimeRegistry`) — закрыл ещё 1 падение (`test_runtime_registry_lazy_accessor_does_not_auto_discover`); всего устранено 11 предсуществующих падений
  - 5 устаревших mock-путей в [test_bridge_layer.py***REMOVED***(tests_09/test_bridge_layer.py) (`freebuff_plugin.bridge_layer.StdioMCPClient`/`HTTPMCPClient` → `freebuff_plugin_03.bridge_layer.*`)

### Проверка
- `python -m pytest tests_09/test_mcp_server.py tests_09/test_policy_conversational.py tests_09/test_policy_engine.py -q` — **172 passed**
- `python -m pytest tests_09/test_bridge_layer.py -q` — **61 passed** (включая интеграционный bridge-тест)
- `python -m pytest tests_09/test_mcp_fastapi.py -q` — **66 passed** (включая 9 тестов эндпоинта)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash` (5 раундов по MCP/Bridge + 2 раунда по FastAPI + финальные раунды по докам): ship-it approved; замечания исправлены (SyntaxError неэкранированных кавычек в description, вложенность payload в bridge-ассертах, `asyncio.to_thread` для event-loop, `capability_list` в planned-таблице, `required: ["message"***REMOVED***` в схеме)

---


## [5.28.0***REMOVED*** — 2026-08-01

### Добавлено
- **Правило 8 (promt37) — Context-Aware Routing хук** в [orchestrator.py***REMOVED***(scripts_01/orchestrator.py):
  - `Orchestrator.check_existing_context(goal, top_k=5)` — перед созданием задачи ищет похожие работы в Knowledge Engine (hybrid: FTS + TF-IDF), возвращает совпадения `{doc_id, score, title, doc_type, snippet***REMOVED***`, graceful degradation → `[***REMOVED***` (индекс `context_12/knowledge/index.db` отсутствует или Knowledge недоступен — workflow не блокируется)
  - Встроен в `run_workflow()`: результат в `workflow.metadata["context_matches"***REMOVED***` + событие `workflow.context_check` (неблокирующее)
  - Тесты: `TestContextAwareRouting` (4 теста) в [test_orchestrator.py***REMOVED***(tests_09/test_orchestrator.py)
- **Правило 9 (promt37) — Plugin Contract Specification** (документ + валидатор + CLI):
  - Канонический документ: [PLUGIN_CONTRACT_SPECIFICATION.md***REMOVED***(docs_10/plugin/PLUGIN_CONTRACT_SPECIFICATION.md) — границы плагин ↔ ядро (manifest.json, lifecycle-хуки, разрешено/запрещено, severity-правила)
  - Валидатор: [plugin_contract.py***REMOVED***(scripts_01/plugin_contract.py) — `ContractSeverity`/`ContractViolation`, `validate_manifest` (имя `^[a-z0-9_***REMOVED***+$`, SemVer `X.Y.Z`, события `domain.event|domain.*`, python_version), `validate_plugin_entry`, `has_errors`, `format_violations`
  - Интеграция: [plugin_api.py***REMOVED***(scripts_01/plugin_api.py) — `PluginLoader.load()` прогоняет контракт после регистрации (warning, не блокирует); CLI `python -m scripts_01.plugin_api contract <name>`
  - Тесты: [test_plugin_contract.py***REMOVED***(tests_09/test_plugin_contract.py) (12 тестов)

### Исправлено
- **CLI-загрузка плагинов (`python -m scripts_01.plugin_api list|contract`):** классическая проблема runpy `__main__` — при `-m` модуль исполняется как `__main__` и до завершения не зарегистрирован в `sys.modules` под каноническим именем; `from scripts_01.plugin_api import BasePlugin` внутри плагинов порождал ВТОРУЮ копию класса, `isinstance(plugin, BasePlugin)` падал («'plugin' is not a BasePlugin instance»; все 4 плагина → ERROR, хотя в pytest грузились). Фикс: `sys.modules.setdefault("scripts_01.plugin_api", sys.modules[__name__***REMOVED***)` в блоке `__main__`. Регрессионный тест `TestPythonMRun` (subprocess `python -m`) в [test_plugin_api.py***REMOVED***(tests_09/test_plugin_api.py)

### Проверка
- `python -m pytest tests_09/test_plugin_api.py tests_09/test_plugin_contract.py tests_09/test_orchestrator.py -q` — **137 passed** (66 + 16 + 55; регрессионный `TestPythonMRun` включён)
- `python -m scripts_01.plugin_api list` — все 4 плагина `LOADED` (были `ERROR`); `contract hello_world` — `Contract OK`
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash` (правила 8/9 — 3 раунда, CLI-фикс — 2 раунда): ship-it approved; замечания исправлены (doc↔код severity, дубли таблицы, мёртвые импорты, двойной префикс warning, регрессионный тест переведён на subprocess вместо in-process runpy)

---


## [5.27.0***REMOVED*** — 2026-08-01

### Добавлено
- **8-я проверка `naming_convention` в [consistency_check.py***REMOVED***(scripts_01/consistency_check.py)** (Этап 9 консолидации, promt32):
  - Авто-проверка схемы именования из [FINAL_STRUCTURE.md***REMOVED***(docs_10/core/FINAL_STRUCTURE.md) §2.1, чтобы правило «каталоги `имя_NN`, промты `NNN_TT_имя`» не потерялось навсегда
  - **Каталоги:** каждый top-level каталог (кроме скрытых/системных — `.git`, `__pycache__`) следует `^[a-z0-9***REMOVED***[a-z0-9_-***REMOVED****_\d{2***REMOVED***$`; суффикс-ID `_NN` уникален (FINAL_STRUCTURE присваивает номера 01..22)
  - **Промты (`pompts_11/`):** формат `NNN_TT_имя.md` с валидным кодом темы (01..14); номера NNN уникальны (гэпы 018–021/035 намеренные — не нарушение)
  - **Doc-страховка (два якоря):** секция «Схема именования» обязана присутствовать в FINAL_STRUCTURE.md §2.1 + термин «Naming Convention» в [GLOSSARY.md***REMOVED***(docs_10/core/GLOSSARY.md)
  - Подключена в `build_report`/`format_report` — новая секция отчёта `naming_convention`

### Исправлено
- **CI [pytest.yml***REMOVED***(.github/workflows/pytest.yml):** шаг «Prepare environment» создавал голые каталоги `mkdir -p context data sessions`, что нарушало бы новую проверку naming_convention → заменено на `mkdir -p context_12 data_13 sessions_15` (реальные имена, используемые тестами)
- **[agent_context_bridge.py***REMOVED***(scripts_01/agent_context_bridge.py):** runtime-путь конспектов в `auto_conspect()` переименован `context/summaries` → `context_12/summaries` (устранён латентный риск для check_naming_convention: голый `context/` создавался бы в корне воркспейса)

### Проверка
- `python -m pytest tests_09/test_consistency_check.py -q` — **39 passed** (было 27; +12 новых: 11 в TestCheckNamingConvention + 1 на ключ отчёта)
- `python scripts_01/consistency_check.py --report` — **Consistent** (exit 0)
- `python scripts_01/drift_check.py --force --report` — **No drift detected** (exit 0)

### Code review
- `code-reviewer-deepseek-flash` (3 раунда): ship-it approved; замечания исправлены (unused `m`, docstring, уникальность суффиксов каталогов, второй якорь GLOSSARY, CI mkdir)

---


## [5.26.0***REMOVED*** — 2026-08-01

### Добавлено
- **Workspace OS Consolidation (promt 32) — все 10 этапов завершены (2026-08-01):**
  - **Этап 1 — Полный аудит:** [CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md***REMOVED***(docs_10/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md) — инвентаризация модулей, документов, промтов, дублей
  - **Этап 2 — Каноническая архитектура:** [ARCHITECTURE_CANONICAL.md***REMOVED***(docs_10/core/ARCHITECTURE_CANONICAL.md) — единая структура Workspace OS и границы движков
  - **Этап 3 — Архитектурный манифест:** [ARCHITECTURE_MANIFEST.md***REMOVED***(docs_10/core/ARCHITECTURE_MANIFEST.md) — главный архитектурный закон
  - **Этап 4 — Консолидация документации:** [DOCUMENT_REGISTRY.md***REMOVED***(docs_10/DOCUMENT_REGISTRY.md) — статусы ACTIVE/LEGACY/ARCHIVED/DRAFT/OBSOLETE для каждого документа; удалены `.bak`
  - **Этап 5 — Консолидация промтов:** единый [CORE_PROMPT.md***REMOVED***(docs_10/core/CORE_PROMPT.md); дубль 34/35 устранён; правила [promt36***REMOVED***(pompts_11/036_09_full_consolidation_pipeline.md)/[promt37***REMOVED***(pompts_11/037_11_user_choice_override.md) встроены в GLOSSARY/MANIFEST (ADR-008/009); ревизия `pompts_11/` → **35 файлов** (18 ACTIVE + 17 LEGACY); 5 артефактов (`error.md`, `new.md`, `structure.md`, `freb.md`, `promt18.md`) перенесены в `trash_21/` через `git mv` (история сохранена)
  - **Этап 6 — Консолидация модулей:** [MODULE_CONSOLIDATION.md***REMOVED***(docs_10/core/MODULE_CONSOLIDATION.md) — 10 областей, матрица движков, 1 дубль (Telegram) → долг
  - **Этап 7 — Единая терминология:** [GLOSSARY.md***REMOVED***(docs_10/core/GLOSSARY.md) — глоссарий с запрещёнными синонимами
  - **Этап 8 — Lifecycle:** [LIFECYCLE.md***REMOVED***(docs_10/core/LIFECYCLE.md) — 7 стадий для компонентов
  - **Этап 9 — Самоконсистентность:** [consistency_check.py***REMOVED***(scripts_01/consistency_check.py) + [drift_check.py***REMOVED***(scripts_01/drift_check.py) встроены в [doctor.py***REMOVED***(scripts_01/doctor.py) и CI
  - **Этап 10 — Финальная структура:** [FINAL_STRUCTURE.md***REMOVED***(docs_10/core/FINAL_STRUCTURE.md) — архитектурная схема, каноническая структура каталогов, реестр компонентов
- **ADR-граф замкнут (ADR-001…009):** все 9 ADR связаны двунаправленными перекрёстными ссылками — индекс [DECISIONS.md***REMOVED***(docs_10/decisions/DECISIONS.md) → файлы `docs_10/engineering-memory/decisions/` → Engineering Memory ([ARCHITECTURE.md***REMOVED***(docs_10/engineering-memory/ARCHITECTURE.md), [PROJECT_BOOK.md***REMOVED***(docs_10/engineering-memory/PROJECT_BOOK.md))

### Проверка
- `python scripts_01/drift_check.py --force --report` — **No drift** (все ссылки резолвятся)
- `python scripts_01/consistency_check.py --report` — **Consistent**
- `python scripts_01/doctor.py` — Consistency OK, Drift OK
- `python -m pytest tests_09/test_consistency_check.py tests_09/test_drift_check.py -q` — **51 passed, 0 failures**
- Code review: ADR-граф (3 раунда) и перенос OBSOLETE-файлов подтверждены

### Артефакты
- [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) — все этапы 1–10 отмечены ✅
- Глава «Консолидация Workspace OS» в [PROJECT_BOOK.md***REMOVED***(docs_10/engineering-memory/PROJECT_BOOK.md)

---


## [5.25.1***REMOVED*** — 2026-07-31

### Added
- **Mandatory security audit `pompts_11/TASK_SECURE_MCP_ACCESS.md` — Шаг 2 (Bearer auth в `scripts_01/mcp_fastapi.py`)**

#### Шаг 2 — Bearer-token auth на `/mcp` (риск №7 аудита)
- `scripts_01/mcp_fastapi.py`:
  - `verify_bearer_token(request)` — FastAPI `Depends`, проверяет `Authorization: Bearer <token>` через `hmac.compare_digest` (constant-time, anti-timing-attack)
  - `_get_active_token()` — Vault first (hvac), env fallback; TTL-кеш 300 s для Vault-пути, env-путь без кеша (для тестов с monkeypatch)
  - Поддержка AppRole (`FREEBUFF_VAULT_ROLE_ID + _SECRET_ID`) И root token (`FREEBUFF_VAULT_TOKEN`); fail-closed если Vault сконфигурирован, но недоступен
  - KV v2 path-stripping — поддержка любых mount-names (`secret`, `kv`, `kv2`) через `/data_13/` split
  - `401 Unauthorized` + `WWW-Authenticate: Bearer realm="buffy-mcp"` (RFC 6750)
  - Тестовый bypass: двойной lock `FREEBUFF_ENV=test AND FREEBUFF_MCP_AUTH_DISABLED=1` (случайное включение в prod невозможно)
  - DoS-защита: токены `len > 1024` отклоняются до encode
  - `_reset_token_cache()` — exposed для тестов
  - Применён к **только `/mcp` (POST/GET/DELETE)**; `/`, `/dashboard`, `/metrics/*` остаются публичными (observability + liveness)
- `scripts_01/mcp_fastapi.py` импорты: `hmac, os, time` + `Depends, HTTPException` (fastapi) + `hvac` (try-import с `HAS_HVAC`)
- `tests_09/test_mcp_fastapi.py`:
  - Module-level setdefault bypass — существующие 47 тестов остаются зелёными без изменений
  - Новый класс **`TestAuthorization`** (10 тестов): 401 без auth, 401 неверный, 401 non-Bearer scheme, 200 корректный bearer (POST), 204 корректный bearer (DELETE), 401 нет token в env, 200 на `/`, 200 на `/metrics/status`, 200/404 на `/dashboard`, anti-regression на `== provided/expected`
- `requirements.txt`:
  - `hvac>=2.0.0` добавлен (hvac был не установлен; теперь доступен)

### Backward compatibility
- 47 существующих тестов (TestHealth, TestPost*, TestDelete, TestGet, TestOriginValidation, TestAsyncSessionManager, TestMetricsEndpoints) проходят без изменений — благодаря автобупасу при `FREEBUFF_ENV=test`.
- Старые клиенты, не передающие `Authorization: Bearer ...`, получают **`401 Unauthorized`** на `/mcp` — это breaking change. Шаг 4 (ручное действие Дениса) обновит MCP-коннектор.

### Tests
- `python -m pytest tests_09/test_mcp_fastapi.py -q`: **57 passed in 7.19 s, 0 failures** (47 + 10 TestAuthorization)
- `python -m py_compile scripts_01/mcp_fastapi.py tests_09/test_mcp_fastapi.py`: 0 errors

### Code review
- `code-reviewer-minimax-m3` (parallel with tests): **ship-it approved** (0 critical, 0 major, 3 minor hardening все применены)
- `thinker-with-files-gemini` (parallel): рекомендовал **только защищать /mcp** (не /, не /metrics, не /dashboard) + Vault-first с env fallback + 5-min cache TTL на Vault-пути

### Артефакты
- This CHANGELOG entry (5.25.1)
- TASK.md checkpoints обновлены

### Отложено (требуются данные / согласование)
- **Шаг 3 (cloudflared perimeter)** — решение оставить quick tunnel или перейти на именованный
- **Шаг 4** — ручное действие Дениса: добавить URL + токен в MCP-коннектор

---


## [5.25.0***REMOVED*** — 2026-07-31

### Added
- **Mandatory security audit `pompts_11/TASK_SECURE_MCP_ACCESS.md` — Шаг 0 (диагностика) + Шаг 1 (закрытие free shell)**

#### Шаг 0 — диагностика поверхности `check_command`/`check_params` через MCP-маршруты
- `grep -n "check_command\|verifier\.\|Verifier(" scripts_01/mcp_server.py scripts_01/mcp_fastapi.py` → **0 совпадений**
- `grep -n "check_command\|verifier\.\|Verifier(" freebuff_plugin_03/mcp_server.py` → **0 совпадений**
- `ps aux | grep -E "cloudflared|mcp_fastapi|mcp_server"` → **ни один процесс не запущен**
- Wide grep `check_command|check_params|check_type` по `scripts_01/` + `freebuff_plugin_03/` подтвердил: вся поверхность сосредоточена в `scripts_01/verifier.py` и локальном методе `scripts_01/overlay_client.py::check_command` (клиент оверлея, не подвержен внешнему воздействию)
- **Вердикт:** маршрут/tool, прокидывающий пользовательский ввод в `check_command`/`check_params` в `scripts_01/mcp_server.py` или `scripts_01/mcp_fastapi.py`, **отсутствует**. Объекта для `pkill` нет. Переход к Шагу 1 без остановки процессов.
- Артефакт: **`docs_10/audits/AUDIT_STEP0_2026-07-31.md`** (5 сырых команд + итог)

#### Шаг 1 — закрытие свободного shell в `scripts_01/verifier.py` (риск №2 аудита)
- **Удалено:** `_run_shell()` (использовал `subprocess.run(..., shell=True)` без sandbox), `_check_shell()`, `_check_content_match()`
- **Из `CHECK_TYPES` / `CHECKER_REGISTRY` / `DEFAULT_RULES`** убраны ключи `"shell"` и `"content_match"`
- **`_check_pytest()` переписан:** `subprocess.run([sys.executable, "-m", "pytest", test_path, "-q", "--tb=no"***REMOVED***, shell=False, cwd=str(WORKSPACE))` — argv-список, **без `shell=True`**; интерполяция `{{test_path***REMOVED******REMOVED***` больше не может выполнить инъекцию `; touch /tmp/pwned`
- **Удалён мёртвый импорт `Tuple`** (единственный потребитель был `_run_shell`)
- **Net LOC delta:** примерно −115 строк (security ↑, complexity ↓)

#### `tests_09/test_verifier.py`
- Удалены тесты `test_shell_success`, `test_shell_failure`, `test_shell_with_template` + импорт `_check_shell`
- 3 теста с `check_type="shell"` (`test_add_rule`, `test_get_results`, `test_verify_same_task_twice`) переведены на `check_type="file_exists"` с реальным путём
- Добавлен **`class TestInjectionPrevention`** (3 теста) — канарейки `pwned_pytest_injection` и `pwned_legacy_shell` НЕ ДОЛЖНЫ появиться после попытки инъекции:
  - `test_pytest_injection_via_test_path` — инъекция `"; touch pwned"` через `{{test_path***REMOVED******REMOVED***` не приводит к созданию файла
  - `test_legacy_shell_rule_rejected` — правило `check_type="shell"` в БД диспетчеруется в `None` → `actual="unknown check_type"`, `passed=False`
  - `test_seeded_defaults_no_shell` — после `seed_default_rules()` ни одно правило не содержит `check_type='shell'`

### Backward compatibility
- Старые правила в `data_13/verifier.db` с `check_type='shell'` или `'content_match'` грузятся нормально, но в `Verifier.verify()` диспетчер `CHECKER_REGISTRY.get(rule.check_type)` возвращает `None` и срабатывает существующая ветка `actual="unknown check_type"` (явно покрыто тестами `test_legacy_shell_rule_rejected` и `test_verify_unknown_check_type`).

### Tests
- `tests_09/test_verifier.py` (56) + `tests_09/test_action_verifications.py` (19) → **75 passed in 14.40s, 0 failures**
- `python -m py_compile scripts_01/verifier.py tests_09/test_verifier.py` → 0 errors
- `grep -n "shell=True\|_run_shell\|_check_shell\|_check_content_match" scripts_01/verifier.py` → **0 совпадений** (единственное упоминание — docstring «без shell=True»)

### Code review
- `code-reviewer-minimax-m3` (parallel with pytest): **ship-it approved**, 1 minor reminder (мёртвый импорт `Tuple`) — исправлено
- `thinker-with-files-gemini` рекомендовал **вариант (b) — полное удаление** вместо allowlist; обоснование: чище математически, нет оставшегося `shell=True`, существующие тесты покрываются переходом на `file_exists`/`pytest`

### Артефакты
- `docs_10/audits/AUDIT_STEP0_2026-07-31.md` — Шаг 0 (5 сырых команд `docs_10/audits/AUDIT_STEP0_2026-07-31.md`)
- `docs_10/audits/AUDIT_EVIDENCE_2026-07-30.md` — независимая аудит-доказательная база (предыдущий запрос, 9 блоков A–I)

### Отложено (требуются данные / согласование)
- **Шаг 2 (Bearer auth в `scripts_01/mcp_fastapi.py`)** — нужен хост Vault и путь к секрету
- **Шаг 3 (cloudflared perimeter)** — решение оставить quick tunnel или перейти на именованный; не критично для безопасности (защита = Шаг 2)
- **Шаг 4** — ручное действие Дениса: добавить URL + токен в MCP-коннектор клиента

---


## [5.24.4***REMOVED*** — 2026-07-30

### Fixed
- **Notification fallback для реальных задач (не только тестов)**
  - **Problem:** User получил уведомления во время тестирования (Phase 5.4 testing через FREEBUFF_FORCE_VISUAL=1), но НЕ получал их на реальных задачах (Phase 5.5 AUDIT PACKAGE build через basher agent).
  - **Root causes:**
    1. `_get_visual_output_stream()` проверял только `isatty()` — возвращал `None` для non-TTY subprocess (basher), даже если env var `FREEBUFF_FORCE_VISUAL=1`
    2. `notify()` cascade с early returns — `_print_visual_summary()` вызывался ТОЛЬКО при провале cascade (log success или all-fail), но НЕ при primary success. На Android 13+ termux-notification может silently заблокироваться, возвращая True — визуальный блок НИКОГДА не появлялся на успешных задачах
    3. Env var не пропагался в login shells (только ~/.bashrc, который source'ится interactive shells)
  - **Fix (2 итерации):**
    - **Round 1:** `_get_visual_output_stream()` теперь проверяет FREEBUFF_FORCE_VISUAL **первым** — если env var установлен, возвращает `sys.stderr` (bypass isatty check)
    - **Round 2 (redesign):** `notify()` cascade переписан — убраны ранние return, используется `if/elif/else` для установки `status` + `reason`, затем **ВСЕГДА** вызывается `_print_visual_summary()` перед return. Визуальный блок fires на ЛЮБОМ исходе cascade.
    - **Env propagation:** добавлено `export FREEBUFF_FORCE_VISUAL=1` в **~/.bashrc** (interactive) AND **~/.profile** (login). Субшелы наследуют env var автоматически.

### Channel-reason mapping (новый)
- Primary success: `"delivered via termux-notification"`
- Toast fallback success: `"delivered via termux-toast"`
- Log fallback success: `"log fallback (Android notification BLOCKED on Termux 13+)"`
- Total failure: `"ALL CHANNELS FAILED (проверьте ~/notifications.log)"`

### Tests
- `tests_09/test_notification.py` — **59 passed** (8.39s)
  - **DELETED:** `test_visual_summary_NOT_called_when_primary_succeeds` (contradicts new behavior)
  - **ADDED 6 new tests:**
    - `test_visual_summary_called_when_primary_succeeds` — primary success MUST fire visual
    - `test_visual_summary_called_when_toast_succeeds` — toast success MUST fire visual
    - `test_visual_summary_receives_correct_reason_primary` — channel_reason string
    - `test_visual_summary_receives_correct_reason_toast` — channel_reason string
    - `test_visual_summary_receives_correct_reason_log` — channel_reason string
    - `test_visual_summary_receives_correct_reason_all_failed` — channel_reason string
  - **ADDED 2 new tests (Round 1):**
    - `test_force_env_returns_stderr_even_when_both_redirected` — env var bypass
    - `test_force_env_value_styles_force_stderr` — yes/true/TRUE/YeS variants

### Verified
- 59/59 tests pass (~8.4s) — **0 failures**
- Smoke test: `FREEBUFF_FORCE_VISUAL=1 python3 -c "_print_visual_summary('test', 'body')"` → block fires in stderr ✓
- Subshell inheritance: `bash -c 'echo $FREEBUFF_FORCE_VISUAL'` → **1** (subshell inherits from login shell) ✓
- Code-reviewer: ship-it approved (5 non-blocking improvements: observability regression, duplicated env var check, misleading channel_reason on Android 13+, fragile test assertions, stale blank line)

### ⚠️ Known Limitation
- **Visual summary fires only when `notify()` is called.** Tasks run via basher agent that don't call notify() (e.g., custom Python scripts, file operations) still won't produce visible blocks. Workaround: explicitly call `notify_task_complete()` at end of important basher-run scripts, OR wrap basher invocations through `freebuff_cli.py` (which has `_main_with_notification()` wrapper).

---


## [5.24.3***REMOVED*** — 2026-07-30

### Added
- **Visual [SUMMARY***REMOVED*** fallback в интерактивный stderr/stdout (Phase 5.4)**
  - 4-я ступень cascade: после `~/notifications.log` срабатывает визуальный fallback блок
  - **Stdout-first semantics** (honor user literal request "stdout + log-файл"):
    - `_get_visual_output_stream()` — выбирает sys.stdout приоритетно, fallback на sys.stderr, returns None если оба redirected
    - `_is_visual_summary_enabled()` — True если EITHER stdout OR stderr is TTY, ИЛИ `FREEBUFF_FORCE_VISUAL=1`
  - **Visual block format**: pipe-safe ASCII box (═ ┌ ─ ├ ┘ │ chars), без ANSI-кодов:
    ```
    ═══════════════════════════════════════════════════
      [SUMMARY***REMOVED*** ✅ Phase 5.4 Visual Summary
    ───────────────────────────────────────────────────
      📋 Task:  ...
      📊 Status: ...
      ⏱ Time:   ...
      ───────────────────────────────────────────────────
      Channel: log fallback (Android notification BLOCKED)
    ═══════════════════════════════════════════════════
    ```
  - **Defensive title truncation**: title > 43 chars обрезается с `...` чтобы не вылезать за box border
  - **Defensive line truncation**: content > 52 chars обрезается с `...` (тоже чтобы не ломать геометрию)
  - **Logger pollution fix**: `logger.info(...)` → `logger.debug(...)` для визуального блока (basicConfig level=INFO)
  - **Width consistency**: внутренний separator использует `_VISUAL_BOX_WIDTH` (56 chars) без 2-space prefix

### Tests
- **`tests_09/test_notification.py`** — добавлено 17 новых тестов в `TestVisualSummary` + 4 фикса mock'ов:
  - Stream selection (5): stdout preferred, stderr fallback, None если оба redirected, disjunction check, full-width inner separator
  - Trigger logic (4): called on log success, called on all-fail, NOT called when primary/toast succeed
  - Content checks (3): contains title and channel, truncates long lines, returns False when disabled
  - Robustness (2): handles print exception, does not alter notify return
  - 4 mock fix: existing tests теперь мокают `_get_visual_output_stream` (pytest capture mode issue)

### Verified
- 58/58 tests pass (~10s) — **0 failures**
- End-to-end smoke: visual block печатается в stderr (при отсутствии TTY в stdout)
- Code-reviewer: **0 critical blockers, 1 non-blocking nit** (additional test for title truncation defensive)

---


## [5.24.2***REMOVED*** — 2026-07-30

### Fixed
- **scripts_01/test_crash_recovery.sh — container suicide prevention**
  - **Problem:** During crash recovery test runs in proot-distro, `pgrep -f "freebuff"` matched the test's grandparent process (the freebuff wrapper itself, several levels up in the process tree) and `kill -9` took down the entire container. Result: SIGKILL + futex panic during 3 consecutive runs (`Killed` + `The futex facility returned an unexpected error code`).
  - **Root cause:** Original script only checked immediate `$PPID`, not full ancestor chain. In proot, top-level wrapper is not direct parent.
  - **Fix:**
    - Auto-detect constrained envs (PROOT_WEAK_LSTAT / TERMUX_VERSION / uname / PREFIX match) and default `--no-kill=true`
    - Walk full ancestor chain via Python /proc/$pid/status `PPid:` (max 15 levels) — skip all ancestors during kill phase
    - Memory guard: skip kill -9 if `MemAvailable < 256 MB` (OOM-suicide prevention)
    - Extended CMD filter: skip `proot`, `login` processes
  - **Result:** 3/3 test runs passed (no SIGKILL, no container collapse)

### Verified
- 3/3 runs PASS ✅ (each ~30s, all 7 steps + cleanup)
- Bash syntax check ✅
- Auto-detect корректно срабатывает в текущем окружении
- Code-reviewer: **0 critical issues, 2 non-blocking minor improvements** (verbose emoji, parent chain fallback edge case)

---


## [5.24.1***REMOVED*** — 2026-07-30

### Added
- **MANDATORY RUNTIME CONTRACT — Phase 5.2: Android 13+ Notification Fallback Chain**
  - 3-tier delivery cascade в `scripts_01/notification.py`:
    - Channel 1: `termux-notification` — основной канал (3-retry exponential backoff 1s/2s/4s, 10s timeout)
    - Channel 2: `termux-toast` — fallback 1 (Toasts НЕ подпадают под POST_NOTIFICATIONS ограничение Android 13+)
    - Channel 3: `~/notifications.log` — fallback 2 (всегда работает при FS-доступе)
  - Returns `True` если хоть один канал доставил уведомление (graceful degradation вместо строгой ошибки)
  - NEW env var: `FREEBUFF_NOTIFY_LOG` — переопределение пути к log fallback
  - Toast truncation: 240 chars max (Android обрезает более длинные)
  - ISO timestamp в log (UTC, ISO 8601 format)
- **`scripts_01/fix_termux_notifications.sh`** — диагностика + авто-открытие Android Settings Intent:
  - `bash scripts_01/fix_termux_notifications.sh` — открывает Settings → Apps → Termux:API → Notifications (1 тап от пользователя)
  - `--check` — только диагностика
  - `--silent` — тихая диагностика
  - 5 проверок: termux-notification binary, Termux:API apk, pm, termux-toast, log path
- **`docs_10/ops/ANDROID_NOTIFICATION_FIX.md`** — полная инструкция для пользователя:
  - 3 способа фикса (автоматический/вручную/am start)
  - Fallback-цепочка с примерами
  - Тестирование после исправления
  - История изменений v5.24.0 → v5.24.1

### Tests
- **`tests_09/test_notification.py`** — добавлено 16 новых тестов (всего 41/41 pass):
  - `TestTryToastChannel` (6): success, unavailable, fail, timeout, truncation, content
  - `TestTryLogChannel` (4): writes file, OSError, multi-entries, timestamp
  - `TestNotifyFallbackChain` (6): toast cascade, log cascade, all-fail, primary-only, FREEBUFF_NO_NOTIFY silent, content preserved
- 4 существующих теста обновлены для работы с cascade (мокают все 3 канала)

### Verified
- 41/41 tests pass (15s) — **0 failures**
- Bash `bash -n scripts_01/fix_termux_notifications.sh` ✅
- Python syntax check ✅
- End-to-end smoke test: `FREEBUFF_NO_NOTIFY=1 → silent; log fallback → ISO timestamp + content`
- Code-reviewer: **0 critical issues, 4 non-blocking minor improvements** (TOAST_TIMEOUT constant, OSError test isolation, ISO regex check, `-c white` flag comment)

### Issue Fixed
- Bash `"""` docstring в `scripts_01/fix_termux_notifications.sh` ломал `bash -n` (parens `(без root)` интерпретировались как subshell)
  - Решение: заменено на `#` комментарии (правильный bash-style docstring)

---


## [5.24.0***REMOVED*** — 2026-07-30

### Добавлено
- **MANDATORY RUNTIME CONTRACT — системные уведомления Android:**
  - `scripts_01/notification.py` — модуль отправки Android-уведомлений через Termux:API
  - `notify()` с retry (3 попытки, exponential backoff 1s/2s/4s, таймаут 10s)
  - `notify_task_complete()` / `notify_error()` — форматированные уведомления с иконками ✅/⚠/❌
  - `is_available()` — проверка доступности termux-notification (shutil.which + hardcoded fallback)
  - **`FREEBUFF_NO_NOTIFY=1`** — env var bypass для тестов/CI
  - `logging.basicConfig` для видимости логов ([INFO***REMOVED***/[ERROR***REMOVED*** в stderr)
  - `freebuff_cli.py` — `_main_with_notification()` wrapper с try/finally
  - `docs_10/ops/RUNTIME_CONTRACT.md` — полная документация контракта
  - 25 тестов (`tests_09/test_notification.py`) — 0 failures
  - **Тест-изоляция:** autouse fixture unsets FREEBUFF_NO_NOTIFY для каждого теста
  - **Текущее состояние проекта:** 1797 тестов, 32+ компонентов


## [5.23.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — RAG 2.0 Engine (семантический поиск с ранжированием):**
  - `scripts_01/rag_engine.py` — **RAGEngine**: 5 режимов поиска (keyword, semantic, hybrid, hybrid_rrf, full_rrf), Reciprocal Rank Fusion (RRF), feature-based re-ranking (7 признаков), query expansion из результатов поиска
  - `RAGResult`, `RAGReport`, `FeatureVector` — dataclasses с JSON-сериализацией
  - `rrf_merge()` — RRF fusion с k=60, поддержка произвольного количества списков, tracking источников
  - `_extract_features()` — 7 признаков: coverage, term_frequency, position, length_norm, freshness, bm25_score, semantic_score
  - `rerank()` — feature-based переранжирование с конфигурируемыми весами
  - `expand_query()` — расширение запроса терминами из top-K результатов
  - 3 MCP инструмента в `scripts_01/mcp_server.py`: `rag_search`, `rag_hybrid`, `rag_rerank`
  - CLI: `python scripts_01/rag_engine.py search | hybrid | rerank | expand` с цветным выводом и JSON
  - 60 тестов (`tests_09/test_rag_engine.py`) — 0 failures
  - Всего: **1772 теста**, **31+ компонент**


## [5.22.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Collaboration Roles:**
  - `scripts_01/roles.py` — **RoleEngine**: SQLite-персистентность, 6 стандартных ролей (developer, reviewer, documenter, researcher, archiver, orchestrator), назначение/отзыв ролей, маппинг capabilities
  - Интеграция с PresenceEngine — роли синхронизируются в metadata агента
  - Интеграция с CollaborationEngine — project-роли → collab-роли (orchestrator→owner, developer/reviewer→editor, остальные→viewer)
  - Capability mapping — каждая роль даёт набор capabilities (coding, testing, review, research, etc.)
  - 5 MCP инструментов в `scripts_01/mcp_server.py`: `roles_list`, `roles_get`, `roles_assign`, `roles_unassign`, `roles_stats`
  - CLI: `python scripts_01/roles.py list | get | assign | unassign | by-role | stats | sync` с цветным выводом
  - 41 тест (`tests_09/test_roles.py`) — 0 failures


## [5.21.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Project Pulse (лента изменений проекта):**
  - `scripts_01/project_pulse.py` — **ProjectPulse**: SQLite-персистентность, отслеживание git-коммитов (scan_git), изменений файлов (scan_files), событий EventBus (subscribe_eventbus + _on_event)
  - 15+ типов событий пульса: git.commit, git.branch, file.created/modified/deleted, event.task/step/collab/memory/plugin/presence/metrics
  - Ref-based дедупликация — один коммит/файл не создаёт дубликатов
  - CLI: `python scripts_01/project_pulse.py list | stats | scan | watch` с цветным выводом и JSON
  - 3 MCP инструмента в `scripts_01/mcp_server.py`: `pulse_list`, `pulse_stats`, `pulse_scan`
  - EventBus подписка на `*` — все события проекта автоматически попадают в ленту
  - 33 теста (`tests_09/test_project_pulse.py`) — 0 failures


## [5.20.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 4 — Плагины (3 шт):**
  - `plugins_04/tg_messenger/` — Telegram Messenger Plugin: отправка сообщений через Telegram Bot API, авто-форвардинг system.*/collab.* событий, управление ботом (start/stop), очередь сообщений
  - `plugins_04/system_monitor/` — System Monitor Plugin: CPU, память, батарея, температура, health check. Fallback-реализации через /proc/* (Termux-совместимые), фоновый watch loop с публикацией system.metrics событий
  - `plugins_04/knowledge_sync/` — Knowledge Sync Plugin: синхронизация MemoryEngine → KnowledgeEngine, авто-индексация при memory.stored событиях, force_reindex, полная перестройка индекса
  - Все плагины: BasePlugin lifecycle (on_load/enable/disable/unload), EventBus подписка, do_* actions, manifest.json с метаданными, graceful degradation при отсутствии зависимостей
  - 39 тестов (`tests_09/test_plugins_phase4.py`) — 0 failures


## [5.19.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 6 — Metrics Dashboard:**
  - `buffy-playground_19/public/metrics-dashboard.html` — standalone HTML dashboard с Chart.js
  - Визуализация: VCR, SRG, CpVO, RRR, TTD — значения, тренды, интерпретации
  - Health Score gauge (0-10) с Canvas-рендерингом
  - Trend charts для каждой метрики (Chart.js line chart)
  - Auto-refresh каждые 30 секунд, тёмная тема
  - `/dashboard` endpoint в `scripts_01/mcp_fastapi.py` (GET → HTMLResponse)
  - 12 тестов — 0 failures


## [5.18.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Live Collaboration для CoWork Platform:**
  - `scripts_01/collaboration.py` — **CollaborationEngine**: SQLite-персистентность (sessions + messages + participants), EventBus-интеграция (события `collab.created/joined/left/closed/message`), PresenceEngine интеграция, система ролей (owner/editor/viewer), история сообщений с пагинацией
  - `CollaborationSession` — 12 полей: session_id, topic, status, owner, participants, timestamps, message_count
  - `CollabMessage` — 5 типов сообщений: text, system, task, file, decision, code
  - 8 MCP инструментов в `scripts_01/mcp_server.py`: `collab_create`, `collab_list`, `collab_get`, `collab_join`, `collab_leave`, `collab_send`, `collab_history`, `collab_status`
  - CLI: `python scripts_01/collaboration.py list | get | create | close | send | history | status` с цветным выводом и JSON-режимом
  - Graceful degradation без EventBus и без PresenceEngine
  - 60 тестов (`tests_09/test_collaboration.py`) — 0 failures
  - Всего: **60 новых тестов + 8 MCP инструментов + 7 CLI команд**


## [5.17.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 7 — Agent Presence для CoWork Platform:**
  - `scripts_01/presence.py` — PresenceEngine: SQLite-персистентность (таблицы `presence` + `presence_history`), EventBus-интеграция (события `presence.online/offline/busy/away/error/heartbeat`), heartbeat loop с авто-prune офлайн-агентов, thread-safe, rich metadata
  - `AgentPresence` dataclass (14 полей) + `PresenceStatus` с валидацией
  - 3 MCP инструмента в `scripts_01/mcp_server.py`: `presence_list`, `presence_get`, `presence_history`
  - CLI: `python scripts_01/presence.py list | get | status | history` (цветной + JSON)
  - Offline marking on shutdown — `stop()` отмечает всех ONLINE агентов как OFFLINE
  - Graceful degradation без EventBus
  - 67 тестов (`tests_09/test_presence.py`) — 0 failures


## [5.16.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 6: HTTP Metrics endpoints (scripts_01/mcp_fastapi.py):**
  - 8 новых REST endpoints для Metrics Engine:
    - `GET /metrics/report` — полный отчёт VCR/SRG/CpVO/RRR/TTD + Health Score
    - `GET /metrics/vcr`, `/metrics/srg`, `/metrics/cpvo`, `/metrics/rrr`, `/metrics/ttd` — каждая метрика отдельно
    - `GET /metrics/trend/{name***REMOVED***` — история метрики (с `?limit=N`)
    - `GET /metrics/status` — диагностика MetricsEngine (БД, EventBus)
  - `_get_metrics()` — lazy init MetricsEngine при первом запросе
  - `_metrics_response(data, fmt)` — поддержка `?fmt=json` (default) и `?fmt=text`
  - Все эндпоинты следуют паттерну lazy init (как `_server` и `_sessions`)

- **Session isolation в test_crash_recovery.sh:**
  - `scripts_01/test_crash_recovery.sh` — Шаг 0: очистка ACTIVE/CHECKPOINT сессий перед стартом через `cm.list_sessions()` + `cm.complete_session()`
  - Temp-файлы с `$$` в имени для избежания race condition между прогонами
  - **3/3 прогона PASS** (против 2/3 в v5.15.0)

- **Тесты — 12 тестов, 0 failures:**
  - `TestMetricsEndpoints` — report, vcr, srg, cpvo, rrr, ttd, status, trend (known/unknown/limit), all endpoints return JSON

### Проверка
- 47 тестов mcp_fastapi — **0 failures** (35 existing + 12 новых)
- 3/3 прогона test_crash_recovery.sh с --no-kill: PASS ✅
- Code review: все замечания исправлены

---


## [5.15.0***REMOVED*** — 2026-07-30

### Добавлено
- **Phase 0: Close Context Loop (TASK_PHASE_0_CLOSE_CONTEXT_LOOP.md):**
  - `freebuff_cli.py :: cmd_buffy()` — интеграция StreamBridge: создаёт сессию, логирует user-запрос (`log_user`), логирует assistant-ответ (`log_assistant`), создаёт чекпоинт (`checkpoint`)
  - Цикл контекста ЗАМКНУТ: `cmd_buffy()` → StreamBridge → `context.db` → `get_context_resume()`
  - Graceful degradation: если StreamBridge недоступен, `bridge = None` — функция работает как раньше
  - `scripts_01/test_crash_recovery.sh` — тест смерти сессии (6 шагов: создание → запись → kill/bootstrap → верификация → resume)
  - `--no-kill` режим для proot-окружений (kill -9 убивает родительский proot-distro процесс)
  - `scripts_01/test_crash_recovery_verify.py` — верификация целостности контекста после краша

### Проверка
- 2/3 прогона test_crash_recovery.sh с --no-kill: PASS ✅
- `cmd_buffy()` StreamBridge интеграция: 6/6 проверок ✅
- Полный цикл контекста: сессия → БД → resume подтверждён ✅
- Code review: все замечания исправлены (bash quoting, temp-файлы вместо heredoc в `$()`, FK constraint, `--no-kill` добавлен)

---


## [5.14.0***REMOVED*** — 2026-07-30

### Добавлено
- **Distributed Agents — Phase 4 завершение (scripts_01/distributed_agents.py):**
  - `AgentMesh` — thread-safe реестр распределённых агентов с find_by_capability, get_stats, get_summary, task_history, get_agent_stats
  - `TaskDistributor` — 3 стратегии распределения задач: best_match (по confidence), round_robin (циклически), specific (к указанному агенту) + distribute_to_all (broadcast)
  - `DistributedCoordinator` — полный lifecycle (start/stop), register_agent() с авто-генерацией имени, spawn_agent() через Bridge Layer, execute_agent_task(), execute_parallel(), remove_agent(), broadcast_to_all()
  - `DistributedWorkflow` — DAG-зависимости (depends_on), параллельное выполнение шагов, broadcast шаги, разрешение зависимостей (_get_ready_steps, _get_blocked_steps)
  - Мониторинг агентов (_monitor_loop) с проверкой статуса через Bridge Layer
  - EventBus публикация: `distributed.started/stopped`, `agent_registered/online/offline/removed`, `task_completed`, `workflow_planning/progress/completed`
  - CLI: `python scripts_01/distributed_agents.py agents | spawn | remove | workflow list | status | broadcast`

- **MCP Server интеграция (5 инструментов):**
  - `distributed_list` — список всех агентов в mesh
  - `distributed_spawn` — регистрация/подключение нового агента
  - `distributed_run` — запуск распределённого workflow
  - `distributed_status` — статус агентов и workflow
  - `distributed_broadcast` — broadcast сообщения всем агентам
  - `_get_distributed_coordinator()` — lazy accessor (паттерн как у BridgeLayer) c auto-register в MCP
  - EventBus публикация: `distributed.listed`, `distributed.spawned`, `distributed.ran`, `distributed.status`, `distributed.broadcasted`

- **Тесты — 55 тестов, 0 failures (35s):**
  - `TestTypes` (7): AgentNode, AgentNodeStatus, WorkCoordStatus, AgentTask, WorkflowStep, WorkflowPlan.to_dict
  - `TestAgentMesh` (12): register/unregister, update_status, set_error, list(фильтр/по статусу/по типу), find_by_capability, online_count, summary, task_history, get_agent_stats
  - `TestTaskDistributor` (6): best_match, unknown capability, specific, unknown agent, round_robin, distribute_to_all
  - `TestDistributedCoordinator` (10): lifecycle, register, auto-name, spawn with/without bridge, max_agents, remove, broadcast, execute_task, execute_parallel, no-bridge fallback
  - `TestDistributedWorkflow` (5): basic, broadcast, dependencies, get_ready, get_blocked
  - `TestCLI` (5): main, agents, status, spawn, workflow list
  - `TestMCPIntegration` (10): tools registered, handlers exist, graceful degradation, validation

### Проверка
- 1414 общих тестов — **0 failures** (420s)
- Code review: 3 итерации фиксов (indentation, imports, enum comparison, auto-name)

---


## [5.13.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase E — buffy-ctx CLI (freebuff_cli.py):**
  - `freebuff ctx push [session_id***REMOVED***` — экспорт контекста сессии в JSON (сообщения, чекпоинты, решения, верификации)
  - `freebuff ctx pull <file.json>` — импорт контекста из JSON с восстановлением сессии
  - `freebuff ctx status [session_id***REMOVED***` — статус контекста (проект, сообщения, токены, верификации, экспорты)
  - `_ctx_export_dir()` — функция вместо module-level константы (учитывает изменения WORKSPACE)
  - Экспорты сохраняются в `context_12/exports/ctx_<session>_<timestamp>.json`

- **Тесты — 17 тестов, 0 failures:**
  - `TestCtxPush` (5): by id, auto active, invalid session, no active, export dir
  - `TestCtxPull` (5): valid file, not found, invalid json, missing section, wrong extension
  - `TestCtxStatus` (4): by id, auto active, no session, invalid
  - `TestRoundtrip` (1): push→pull preserves data
  - `TestCLIEntryPoint` (2): ctx push, ctx status CLI commands

### Проверка
- 1359 общих тестов — **0 failures** (390s)
- Code review: 2 замечания исправлены (CONTEXT_EXPORT_DIR → _ctx_export_dir(), _patch_workspace module parameter)

---


## [5.12.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase D — Vector Memory (6-й уровень памяти):**
  - `MemoryLevel.VECTOR = "vector"` — 6-й уровень памяти в MemoryEngine
  - `VectorBackend` класс — опциональный Chromadb бэкенд:
    - `is_available()` — проверка доступности chromadb
    - `store(entry_id, text, metadata)` — сохранение вектора
    - `search(query, top_k, filter, level)` — поиск по векторной близости
    - `delete(entry_id)` — удаление вектора
    - `count()` — количество записей
    - `wipe()` — очистка коллекции
  - Graceful degradation: chromadb не обязателен — все операции возвращают ошибку
  - `MemoryEngine.store()` для VECTOR уровня: JSON + вектор (raise RuntimeError если нет chromadb)
  - `MemoryEngine.delete()` — исправлен порядок: чтение entry_id ДО unlink файла
  - `MemoryEngine.vector_search(query, top_k, level)` — семантический поиск с обогащением MemoryEntry
  - CLI: `python scripts_01/memory_engine.py vector_search "query" --top-k 5 --json`

- **Тесты — 28 тестов, 0 failures:**
  - `TestMemoryLevelVector` (2): enum value, count
  - `TestVectorBackendNoChromadb` (6): init, store, search, delete, count, wipe — graceful degradation
  - `TestVectorBackendMocked` (10): init, store, search sorted, search empty, delete, count, wipe, edge cases
  - `TestMemoryEngineVectorNoChromadb` (9): store raises, error msg, other levels work, search empty, retrieve, delete, list
  - `TestMemoryEngineVectorMocked` (8): store, retrieve, list, delete, search includes, vector_search, stats
  - `TestBuildContextWithVector` (2): excludes by default, includes explicit

### Исправлено
- `scripts_01/memory_engine.py` — `delete()` читал `filepath.read_text()` после `filepath.unlink()` (FileNotFoundError). Исправлено: чтение entry_id до удаления файла, передача id в vector_backend.delete() после unlink

### Проверка
- 1342 общих теста — **0 failures** (337s)
- Code review: 1 баг исправлен (delete order)
- 40 тестов Memory Engine обновлены (test_memory_level_count: 5→6)

---


## [5.11.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase C — Metrics Engine (scripts_01/metrics.py):**
  - 5 метрик качества разработки:
    - **VCR** (Verified Completion Rate) — доля `verified_status='verified_ok'` от всех верифицированных задач
    - **SRG** (Self-Report Gap) — разница между claimed_status='done' и фактической верификацией
    - **CpVO** (Cost per Verified Outcome) — средняя длительность на единицу результата (ms/verification)
    - **RRR** (Rework/Rollback Rate) — доля задач с последующими фиксами после верификации
    - **TTD-false** (Time-To-Detect false) — среднее время до обнаружения ошибки (minutes)
  - `MetricsEngine` — вычисление метрик из context.db (action_verifications) + verifier.db (verification_results)
  - `compute_report()` — композитный отчёт + `save_snapshot()` для трендов
  - `get_trend()` — история значений метрики из metrics.db
  - `Health Score` (0-10) — общая оценка на основе 5 метрик
  - EventBus: публикация `metrics.report` при сохранении снимка
  - CLI: `report`, `vcr`, `srg`, `cpvo`, `rrr`, `ttd`, `trend <metric>`, `status` — с JSON выводом
  - **MCP интеграция:** `_get_metrics_engine()` lazy accessor + 3 инструмента: `metrics_report`, `metrics_vcr`, `metrics_srg`

- **Тесты — 37 тестов, 0 failures:**
  - `TestMetricResult` (3): defaults, rounding, display_name
  - `TestMetricsReport` (2): defaults, to_dict
  - `TestVCR` (3): value, no_data, interpretation
  - `TestSRG` (3): value, no_data, trend
  - `TestCpVO` (3): value, no_verifier_db, with_failures
  - `TestRRR` (3): value, no_data, trend
  - `TestTTD` (3): value, no_data, no_failures
  - `TestReport` (2): all_metrics, with_save
  - `TestSetupDatabases` (2): all_exist, all_missing
  - `TestSnapshot` (2): save_and_get_trend, get_empty_trend
  - `TestHealthScore` (3): baseline, perfect, worst
  - `TestStatus` (2): status_ok, with_eventbus
  - `TestEventBus` (2): report_event, no_crash
  - `TestCLI` (2): json_format, report_dict
  - `TestMCPIntegration` (2): tools_registered, handlers_available

### Проверка
- 188 LEVIATHAN Phase A+B+C тестов — **0 failures** (51s)
- Code review: unused imports исправлены

---


## [5.10.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Verifier + Orchestrator интеграция (шаг 1.3):**
  - `scripts_01/orchestrator.py` — `Orchestrator.__init__()` теперь принимает `verifier` и `context_manager` параметры (опциональные, обратная совместимость)
  - `_execute_step()` — после `StepStatus.SUCCESS` вызывает `_verify_step()` для верификации результата
  - `_verify_step()` — новый метод:
    - Запускает `Verifier.verify()` для успешного шага
    - Устанавливает `claimed_status='done'` через `ContextManager.set_claimed_status()`
    - Устанавливает `verified_status` через `ContextManager.set_verified_status()`
    - Публикует `step.verified` событие с результатами проверки
    - Safe serialization: корректно обрабатывает как dataclass, так и mock-объекты
    - Ошибки верификации не ломают workflow (изолированы в try/except)
  - Документация: `step.verified` добавлен в список событий
  - **5 тестов** — 0 failures:
    - verifier вызван для успешного шага
    - verifier + context_manager: set_claimed_status + set_verified_status вызваны
    - step.verified событие через EventBus
    - Ошибка verifier не ломает workflow
    - Failed step не вызывает verifier

### Проверка
- 1271 общий тест — **0 failures** (327s)
- Code review: все замечания исправлены

---


## [5.9.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Action Verifications (шаг 1.1-1.2):**
  - `scripts_01/context_manager.py` — SCHEMA_VERSION 4→5, миграция `_migrate_v4_to_v5()`:
    - Новая таблица `action_verifications` (id, session_id, message_id, task_id, claimed_status, verified_status, verified_by, verified_at, verification_results) с 4 индексами
  - 4 новых метода:
    - `set_claimed_status()` — установка claimed_status (pending/done/failed) с upsert по task_id
    - `set_verified_status()` — установка verified_status (verified_ok/verified_fail) с результатами проверки
    - `get_verification()` — получение статуса верификации по task_id
    - `list_verifications()` — список верификаций с фильтрацией по status/session_id/limit
  - EventBus: публикация `verification.claimed` и `verification.completed`

- **План интеграции LEVIATHAN:**
  - `docs_10/LEVIATHAN_INTEGRATION_PLAN.md` — полный план с 4 шагами (A→D), детальным описанием каждого изменения, оценкой часов и тестов

### Проверка
- 95 тестов Phase A+B — **0 failures** (18s)
- Code review: все замечания исправлены

---


## [5.8.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase A — Schema Extension:**
  - `scripts_01/context_manager.py` — SCHEMA_VERSION 3→4, миграция `_migrate_v3_to_v4()`:
    - Новая таблица `arch_decisions` — архитектурные решения (id, session_id, title, context, decision, alternatives, rationale, consequences, status)
    - Новая таблица `invariants` — инварианты (id, name, description, assertion_type, assertion_params, enabled, severity, last_checked, last_result)
  - 6 новых методов в ContextManager:
    - `log_decision()` — логирование архитектурного решения с полным контекстом
    - `get_decisions()` — список решений с фильтрацией по session_id/status/limit
    - `set_invariant()` — установка инварианта (upsert по имени)
    - `get_invariant()` — получение инварианта по имени
    - `check_invariant()` — проверка инварианта (file_exists/content_match/shell/sql_query)
    - `list_invariants()` — список инвариантов с фильтрацией enabled/severity
  - EventBus: публикация `decision.logged` и `invariant.checked`
  - Исправлено: свежая БД (version=0) теперь корректно создаёт arch_decisions + invariants таблицы
  - Исправлено: FK constraint убран из arch_decisions (сессия — опциональная связь)

- **Тесты — 20 тестов, 0 failures:**
  - `TestSchemaMigration` (3): version=4, таблицы существуют, миграция v3→v4
  - `TestArchitecturalDecisions` (5): log_decision, get_decisions фильтр/лимит/без сессии, EventBus
  - `TestInvariants` (12): set/get, overwrite, not found, list, enabled only, check (file_exists/shell/disabled/not found), EventBus, severity filter

### Проверка
- 20 тестов Phase A — **0 failures**
- 1247 общих тестов — **0 failures** (380s)
- Code review: 3 стилистических замечания исправлены (inline imports, timeout config)

---


## [5.7.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Phase B — Verification Framework:**
  - `scripts_01/verifier.py` — новый модуль независимой верификации результатов:
    - `VerificationRule` dataclass — правила верификации с 7 типами проверок: file_exists, file_contains, content_match, pytest, shell, sqlite, http
    - `VerifierStorage` — SQLite-хранилище (WAL-mode) с таблицами `verification_rules` и `verification_results` + индексы
    - `Verifier` — основной класс: `verify()`, `add_rule()`, `remove_rule()`, `list_rules()`, `seed_default_rules()`, `get_summary()`, `get_results()`, `get_stats()`
    - `_resolve_template()` — шаблонизация `{{variable***REMOVED******REMOVED***` в параметрах правил
    - **EventBus интеграция**: подписка на `task.claimed` для авто-верификации, публикация `task.verified` и `verifier.rule_added`
    - **CLI**: 4 подкоманды — `verify`, `rules` (list/add/remove/seed), `status`, `diagnose`
    - 7 встроенных правил для task_type: implement, test, refactor, research, any

- **Тесты — 56 тестов, 0 failures:**
  - `TestVerificationRule` (6): defaults, validation, weight clamping
  - `TestVerificationResult` (2): defaults
  - `TestVerifierStorage` (12): init, CRUD rules, CRUD results, summary, stats, enabled filter
  - `TestTemplateResolution` (5): simple, multiple, unknown, empty
  - `TestVerifier` (16): seed, idempotent, force, add, remove, list, verify, summary, results, stats, diagnose, EventBus auto-verification, edge cases
  - `TestCheckers` (12): file_exists (found/not found), file_contains (found/not found/min_length/missing), shell (success/failure/template), sqlite (success/few_rows/missing_db), http (success/failure with mocks)
  - `TestEdgeCases` (2): empty context, duplicate task, checker registry integrity

### Проверка
- 56 тестов verifier — **0 failures** (22.84s)
- 1226 общих тестов — **0 failures** (298s)
- Code review: 3 замечания исправлены (***REMOVED*** → module level, sqlite row_count, content_match checker)

---


## [5.6.0***REMOVED*** — 2026-07-30

### Добавлено
- **Priority 1 компоненты — полная документация по шаблону TEMPLATE_COMPONENT_DOCUMENTATION.md:**
  - `docs_10/core/CONTEXT_MANAGER_SPECIFICATION.md` — ContextManager (назначение, архитектура, API, реализация)
  - `docs_10/core/MEMORY_ENGINE_SPECIFICATION.md` — MemoryEngine (5 уровней памяти, файловое хранение)
  - `docs_10/core/KNOWLEDGE_ENGINE_SPECIFICATION.md` — KnowledgeEngine (FTS5 + TF-IDF + Semantic)
  - `docs_10/core/GRAPH_INDEX_SPECIFICATION.md` — GraphIndex (граф связей, BFS обход)
  - `docs_10/core/EVENT_BUS_SPECIFICATION.md` — EventBus (publish/subscribe, wildcard)
  - `docs_10/core/ORCHESTRATOR_SPECIFICATION.md` — Orchestrator (FSM/DAG workflow, планировщик)
  - `docs_10/core/MODEL_GATEWAY_SPECIFICATION.md` — ModelGateway (единый шлюз LLM, fallback)
  - `docs_10/core/TOOL_RUNTIME_SPECIFICATION.md` — ToolRuntime (безопасные инструменты, ParamSchema)
  - `docs_10/core/PLUGIN_API_SPECIFICATION.md` — PluginAPI (lifecycle, manifest, discovery)
  - `docs_10/plugin/BRIDGE_LAYER_SPECIFICATION.md` — BridgeLayer (MCP ↔ ACP мост)
  - `docs_10/plugin/ACP_PROTOCOL_SPECIFICATION.md` — ACPProtocol (Agent Collaboration Protocol)
  - `docs_10/plugin/MCP_CLIENT_SPECIFICATION.md` — MCPClient (Stdio/HTTP транспорт)
  - `docs_10/plugin/MCP_SERVER_SPECIFICATION.md` — MCPServer (25+ MCP инструментов)
  - Каждая спецификация содержит 9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связанные компоненты

### Индексация
- `docs_10/INDEX.md` — добавлены ссылки на все 13 новых спецификаций
- Все спецификации взаимосвязаны через секцию «Связанные компоненты»

### Проверка
- 13 компонентов задокументированы по единому шаблону
- Каждый doc содержит: ASCII-диаграмму, полный API с примерами, секцию ошибок
- Code review: все замечания исправлены

---


## [5.5.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Context — полный архитектурный аудит ([promt18.md***REMOVED***(trash_21/promt18.md)):**
  - `docs_10/audits/LEVIATHAN_CONTEXT_AUDIT.md` — 10-раздельный анализ (модель LEVIATHAN, сопоставление с Buffy, пересечения, дублирование, пробелы, Red Team, эволюционный план, дорожная карта, оценка 7.0/10 vs 5.3/10, каноническая архитектура)
  - `docs_10/vision/ROADMAP.md` — LEVIATHAN раздел обновлён: 4 фазы интеграции (Schema Extension → Verification Framework → Metrics Engine → Vector Memory) с оценкой часов, рисков и тестов

- **Компонентная документация по шаблону (promt19.md):**
  - `docs_10/core/EVENT_STORE_SPECIFICATION.md` — полная документация EventStore по шаблону (9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связи)
  - `docs_10/core/SESSION_MESH_SPECIFICATION.md` — документация SessionMesh по шаблону
  - `docs_10/core/NODE_MESH_SPECIFICATION.md` — документация NodeMesh по шаблону

- **Индексация:**
  - `docs_10/INDEX.md` — добавлены ссылки на LEVIATHAN_CONTEXT_AUDIT, EVENT_STORE_SPECIFICATION, SESSION_MESH_SPECIFICATION, NODE_MESH_SPECIFICATION

### Проверка
- Все спецификации заполнены по единому шаблону TEMPLATE_COMPONENT_DOCUMENTATION.md
- Каждая спецификация содержит: 9 разделов, API с примерами, тесты, конфигурацию, ошибки, сценарии использования
- Code review: замечания по структуре и полноте документации исправлены

---


## [5.4.0***REMOVED*** — 2026-07-30

### Добавлено
- **Runtime Installer — Шаг 3 из TASK.md (task-framework):**
  - Авто-установка AI Runtime через Bootstrap Engine: `freebuff`, `claude-code`, `openclaw`
  - `freebuff_plugin_03/bootstrap/engine.py`:
    - Добавлен OpenClaw в `DEFAULT_RUNTIMES` (pip install openclaw, bin_name: openclaw)
    - Добавлен `install_runtime_by_name(name)` — точечная установка Runtime по имени
    - Добавлен `list_available_runtimes()` — список всех Runtime с статусом установки
  - `scripts_01/mcp_server.py`:
    - Добавлен MCP tool `runtime_install` (name: required) — установка Runtime
    - Добавлен MCP tool `runtime_list_available` — список доступных Runtime
    - После установки вызывается `registry.discover()` для регистрации Runtime
  - **16 тестов** (bootstrap engine: 9 + mcp_server: 7) — 0 failures:
    - install_runtime_by_name: known, unknown, claude-code, openclaw, already installed, steps
    - list_available_runtimes: all 3 runtimes present
    - MCP runtime_install: success (verify discover call), missing name, unknown runtime
    - MCP runtime_list_available: returns 3 runtimes
    - Tools in list, schema validation

### Проверка
- 20 новых тестов (9 bootstrap + 7 mcp_server + 4 refactored) — **0 failures**
- Code review: 3 замечания исправлены (dead code removed, discover assertion added, test assertion fixes)

---


## [5.3.0***REMOVED*** — 2026-07-30

### Добавлено
- **LEVIATHAN Context Integration & Component Documentation Template ([promt18.md***REMOVED***(trash_21/promt18.md), promt19.md):**
  - `docs_10/core/TEMPLATE_COMPONENT_DOCUMENTATION.md` — универсальный шаблон документирования компонентов (9 разделов: назначение, архитектура, интерфейс, реализация, тесты, конфигурация, ошибки, примеры, связанные компоненты)
  - `docs_10/vision/ROADMAP.md` v3.1.0 — добавлены:
    - LEVIATHAN Context Integration (unified context schema, `buffy-ctx` CLI, task queue, handoff, reaper, context HTTP API)
    - Phase 6: Context Verification & Quality Assurance (VCR/SRG/CpVO/RRR/TTD-false metrics)
    - Phase 7: CoWork / Companion Platform (Presence, Live Collaboration, RAG 2.0)
  - `docs_10/INDEX.md` — ссылка на шаблон документации компонентов
  - `BUFFY.md` — добавлена ссылка на шаблон и раздел Phase 6: Context Verification & QA

---


## [5.2.0***REMOVED*** — 2026-07-29

### Добавлено
- **Policy Engine — пользовательские политики выбора Runtime:**
  - `freebuff_plugin_03/policy/` — модуль Policy Engine (`engine.py`, `config.py`, `rules.py`)
  - `PolicyEngine` — выбор Runtime по capability с fallback chain и constraints
  - Поддержка правил: `min_confidence`, `max_latency`, `exclude`, `required_flags`
  - `runtime_05/policies.json` — пользовательские политики в JSON (не gitignored)
  - Интеграция в `scripts_01/mcp_server.py`: `runtime_generate` сначала использует PolicyEngine, затем fallback на `RuntimeCapabilityRegistry`
  - 16 тестов (`tests_09/test_policy_engine.py`) — 0 failures

---


## [5.1.0***REMOVED*** — 2026-07-29

### Добавлено
- **structure.md — реорганизация документации:**
  - `docs_10/core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` — спецификация Session Mesh v2.0
  - `docs_10/core/PROMPT_IMPLEMENTATION_v1.0.md` — промпт реализации (копия 017_02_struktura_requirements_testy.md)
  - `docs_10/INDEX.md` — обновлён: добавлены Mesh-документы, IDEAS, FILE_REGISTRY
  - `BUFFY.md` — добавлена секция «Session Mesh v2.0», обновлены пути
- **017_02_struktura_requirements_testy.md — Session Mesh v2.0 Phase 0:**
  - `freebuff_plugin_03/mesh/` — структура директорий (core_02/, node/, session/, agent/, transport/, storage/) — 7 файлов `__init__.py` с docstrings
  - `requirements.txt` — добавлены mesh-зависимости: ulid-py, websocket-client, diff-match-patch
- **Сортировка корневых файлов:**
  - `IDEAS.md` → `docs_10/decisions/IDEAS.md`
  - `FILE_REGISTRY.md` → `docs_10/projects_meta/FILE_REGISTRY.md`

---


## [5.0.0***REMOVED*** — 2026-07-29

### Добавлено

#### Стратегический слой (Task 0)
- **VISION_3.0.md** — раздел «Три режима работы» (Local/Cloud/Hybrid), честная фиксация gaps по ACP/Bridge/KeyPool
- **`docs_10/core/ARCHITECTURE_PRINCIPLES.md`** — 8 архитектурных принципов платформы (§2.7 Marketplace-Ready)
- **`docs_10/core/COMPATIBILITY_MATRIX.md`** — матрица совместимости Runtime и протоколов
- **`docs_10/core/RUNTIME_VALIDATION_FRAMEWORK.md`** — фреймворк валидации Runtime

#### Реорганизация docs_10/ (Task 1)
- **45 файлов мигрированы** из flat `docs_10/` в 7 подпапок:
  - `docs_10/core/` — спецификации и архитектурные документы
  - `docs_10/vision/` — ROADMAP, VISION_2.0/3.0, PRODUCT_MANIFESTO
  - `docs_10/decisions/` — ADR и DECISIONS
  - `docs_10/audits/` — аудиты (DRIFT_REPORT, AUDIT_*)
  - `docs_10/plugin/` — FREEBUFF_PLUGIN_*
  - `docs_10/projects_meta/` — WORKERS, LIGHTPANDA_INTEGRATION, PROJECT_REGISTRY
  - `docs_10/ops/` — TROUBLESHOOTING, TASK_TEMPLATE, AGENTS
- **`docs_10/INDEX.md`** — навигационный индекс по всем документам
- **Все перекрёстные ссылки обновлены** в коде, тестах, и документах
- **`PROJECT_REGISTRY.md`** и **`seed_knowledge.py`** — пути обновлены

#### Граница ядро↔плагин (Task 2)
- **`scripts_01/mcp_server.py`** — импортирует плагин только через `__init__.py` с try/except graceful degradation
- **`freebuff_plugin_03/mcp_client.py`** и **`bridge_layer.py`** — убраны жёсткие пути, импорты обёрнуты
- **`freebuff_plugin_03/INTEGRATION_CONTRACT.md`** — контракт между ядром и плагином
- **`scripts_01/doctor.py`** — CLI-инструмент диагностики (`--full`, `--check`) с EventBus интеграцией
- **`runtime_05/recipes/freebuff.md`** и **`runtime_05/recipes/claude_code.md`** — Runtime Recipes

#### Marketplace-ready архитектура (Task 2.3)
- **`runtime_05/providers/`** — YAML-манифесты для freebuff, claude_code, openclaw
- **`runtime_05/plugins/`** — плагин-система (расширения без изменения ядра)
- **`runtime_05/MARKETPLACE.md`** — трёхслойная архитектура, проверка «без изменения ядра»
- **Provider auto-discovery** — `load_providers_from_dir()`, `register_provider()`, fallback YAML-парсер
- **69 тестов** (+9 новых TestProviderLoading + TestProviderIntegration)

#### Унификация projects_17/ (Task 3)
- **`diet_platform/`** — созданы README.md + MANIFEST.md (из TEAM_NOTES.md/PRODUCT_BACKLOG.md)
- **`realtor_automation/`** — создан MANIFEST.md
- **`tg_terminal_messenger/`** — `manifest.md` → `MANIFEST.md` (единый регистр, two-step rename для git)

#### Чистка data_13/context.db (Task 4)
- **91 → 45 сессий** (удалено 46 тестовых/мусорных: Auto-conspect, Imported from Aider/OpenClaw, freebuff session, TMUX_OK, bridge OK, Тест стриминг)
- **data_13/ и context_12/** — чисто (только штатные conversation.log)
- **`.gitignore`** — добавлены `*.pyc`, `*.pyo`

#### Аудит scripts_01/ (Task 5)
- **4 мёртвых скрипта → `scripts_01/archive/`**:
  - `import_qwen.py` (0 code references)
  - `import_sessions.py` (0 code references)
  - `phone_mcp_server.py` (0 code references)
  - `dashboard_api.py` (0 code references)
- **`FILE_REGISTRY.md`** и **`docs_10/core/SYSTEM_INVENTORY.md`** — ссылки обновлены

#### Полный smoke-test (Task 6)
- **1152 passed**, 1 skipped, 0 failures (305s)
- Импорт mcp_server + plugin __init__: OK
- seed_knowledge DEFAULT_DOC_SOURCES: все 6 путей валидны
- doc_reminder.sh: синтаксис + пути OK
- doctor.py --full: 58% health (11 OK, 6 warnings — допустимо для Termux)
- Граница ядро↔плагин: CLEAN

#### Интеграция CODE_QUALITY_STANDARD
- **`pompts_11/040_13_code_quality_standard.md`** — интегрирован как обязательный production-ready регламент
- Адаптирован под экосистему Freebuff, сохранены все пункты, добавлены специфичные

### Исправлено
- **`freebuff_plugin_03/event/replay.py:61`** — `IndentationError`: `import create_event` был на одной строке с комментарием в `elif self._bus:` блоке. Исправлена индентация, `import` вынесен на отдельную строку. Без фикса 61 тест не собирался.
- **`freebuff_plugin_03/runtime/registry.py`** — fallback YAML-парсер: dead code исправлен (`capabilities`/`bin_names`/`platforms`/`args` присваиваются в result), `current_section` больше не сбрасывается при индентированных `key: value`
- **`freebuff_plugin_03/runtime/registry.py`** — `_ensure_scores_loaded`: merge вместо overwrite (защита пользовательских `set_score()`)
- **`freebuff_plugin_03/runtime/registry.py`** — type mismatch: `List[str***REMOVED***` ← `Dict[str, float***REMOVED***` конверсия в `discover()`
- **`freebuff_plugin_03/runtime/registry.py`** — `_load_builtin_fallback`: merge вместо skip
- **`tests_09/test_runtime_abstraction.py`** — `test_custom_providers_dir`: `pytest.importorskip("yaml")` вместо безусловного импорта

### Проверка
- **1152 тестов** — 0 failures (305s)
- Граница Plugin→Core: CLEAN
- Граница Core→Plugin: CLEAN
- 3 провайдера загружаются: marketplace-ready
- Все 4 проекта унифицированы (README.md + MANIFEST.md)
- data_13/context.db: 91→45 сессий
- Smoke-test: все 6 проверок пройдены

---

## [4.10.0***REMOVED*** — 2026-07-29

### Добавлено
- **MCP + Runtime Abstraction Layer интеграция:**
  - `scripts_01/mcp_server.py` — добавлен `_get_runtime_registry()` lazy accessor (паттерн как у BridgeLayer / BootstrapEngine)
  - 5 новых MCP инструментов (секция 8: Runtime Abstraction Layer tools):
    - `runtime_list` — список зарегистрированных Runtime
    - `runtime_connect` — подключиться к Runtime
    - `runtime_disconnect` — отключиться от Runtime
    - `runtime_select` — выбрать активный Runtime
    - `runtime_generate` — генерация через выбранный Runtime (name / capability / active)
  - Выбор Runtime по capability через `RuntimeCapabilityRegistry`
  - Авто-подключение Runtime при генерации, если адаптер не активен
  - Валидация `messages` (список dict с `role` и `content`) и `temperature`/`max_tokens`
  - EventBus публикация: `runtime.listed`, `runtime.connected`, `runtime.disconnected`, `runtime.selected`, `runtime.generated`
  - 18 тестов (`tests_09/test_mcp_server.py::TestRuntimeTools`) — 0 failures:
    - list/connect/disconnect/select
    - generate by name / capability / active runtime
    - error paths: missing prompt, invalid temperature/max_tokens, invalid messages, connect failure, registry unavailable, capability unregistered, lazy accessor without auto-discovery

### Проверка
- 120 тестов MCP Server — **0 failures** (28s)
- Code review: 3 итерации (messages validation, no auto-discover, error paths)

---

## [4.9.0***REMOVED*** — 2026-07-29

### Добавлено
- **Runtime Abstraction Layer — Phase 1: Infrastructure Core (docs_10/core/RUNTIME_ABSTRACTION_SPECIFICATION.md):**
  - `freebuff_plugin_03/runtime/__init__.py` — типы: RuntimeStatus, SessionStatus, AdapterType, RuntimeConfig, RuntimeDefinition, RuntimeResult, RuntimeCapability, RuntimeSession, RuntimeHealth
  - `freebuff_plugin_03/runtime/adapter.py` — RuntimeAdapter ABC (connect/disconnect/ping/health/generate/list_capabilities) + StdioMCPAdapter (MCP STDIO транспорт) + HTTPMCPAdapter (MCP HTTP транспорт) + AdapterRegistry + default_adapter_registry
  - `freebuff_plugin_03/runtime/registry.py` — RuntimeRegistry: register, unregister, get, list, discover, set_active, connect/disconnect, get_status, JSON persistence; RuntimeCapabilityRegistry: list_capabilities, get_runtime_for_capability, score_runtime, set_score
  - `freebuff_plugin_03/runtime/adapters/__init__.py` — re-export FreebuffAdapter и ClaudeCodeAdapter
  - `freebuff_plugin_03/runtime/adapters/freebuff.py` — FreebuffAdapter: поиск бинарника (which, ~/.local/bin, pip), MCP STDIO транспорт, 5 capability (coding, planning, architecture, testing, research)
  - `freebuff_plugin_03/runtime/adapters/claude.py` — ClaudeCodeAdapter: поиск claude (which, npm root -g), MCP STDIO транспорт, 5 capability (coding, review, architecture, documentation, planning)
  - **Композиция с Bridge Platform** — адаптеры используют `StdioMCPClient` и `HTTPMCPClient` из MCP Client, не дублируют транспортный слой
  - **60 тестов** (`tests_09/test_runtime_abstraction.py`) — 0 failures:
    - TestTypes (8): RuntimeConfig, RuntimeDefinition, RuntimeResult, RuntimeCapability, RuntimeSession, RuntimeHealth
    - TestRuntimeAdapter + TestStdioMCPAdapter + TestHTTPMCPAdapter (10): lifecycle, connect/disconnect, ping, health, generate
    - TestAdapterRegistry (5): register, get, create, list_types
    - TestRuntimeRegistry (12): register, unregister, list, discover, set_active, save/load, connect/disconnect, status
    - TestRuntimeCapabilityRegistry (8): list_capabilities, get_runtime_for_capability, score, set_score, preference, fallback
    - TestFreebuffAdapter + TestClaudeCodeAdapter (8): name, capabilities, find binary/falback
    - TestIntegration (3): registry+adapter, multi-runtime selection, save/load cycle

### Проверка
- 60 тестов Runtime Abstraction Layer — **0 failures** (65s)
- 1123 общих тестов — **0 failures** (254s)
- Code review: 3 замечания исправлены (unused imports, private attr access, missing import)

---

## [4.8.0***REMOVED*** — 2026-07-29

### Добавлено
- **Bootstrap Engine — интеграция с MCP Server:**
  - `scripts_01/mcp_server.py` — добавлен `_get_bootstrap_engine()` lazy accessor (паттерн как у BridgeLayer)
  - 3 новых MCP инструмента (секция 7: Bootstrap Engine tools):
    - `bootstrap_check` — проверка окружения (OS, Python, Node, Git, Disk, RAM, пакеты). Параметр: `quick: bool`
    - `bootstrap_run` — полный bootstrap: check → load profile → install → diagnose → report. Параметр: `profile: str` (minimal по умолчанию)
    - `bootstrap_status` — статус bootstrap: был ли запущен, профиль, ошибки, предупреждения
  - EventBus публикация: `bootstrap.checked`, `bootstrap.ran`
  - 12 тестов (`tests_09/test_mcp_server.py::TestBootstrapTools`) — 0 failures:
    - check: full, quick, engine unavailable
    - run: minimal, default, developer, unknown profile (graceful fallback)
    - status: never run, after run
    - tools: in list, schemas, RPC dispatch

### Проверка
- 101 тест MCP Server — **0 failures** (26s)
- 1063 общих теста — **0 failures** (206s)
- Code review: 3 замечания исправлены (MagicMock serialization, private API access, profile fallback test)

---

## [4.7.0***REMOVED*** — 2026-07-29

### Добавлено
- **Event Platform — реализация (docs_10/core/EVENT_PLATFORM_SPECIFICATION.md):**
  - `freebuff_plugin_03/event/__init__.py` — типы: EventEntry, EventQuery, ReplayResult, Timeline, Audit*, PulseEntry + EVENT_ICONS + get_event_icon
  - `freebuff_plugin_03/event/schema.sql` — SQLite schema: event_store таблица, FTS5, 3 триггера (INSERT/UPDATE/DELETE)
  - `freebuff_plugin_03/event/store.py` — EventStore: CRUD (store, get_by_id, query), FTS5 search с wildcard поддержкой, batch, миграция из event_log, агрегация, clear
  - `freebuff_plugin_03/event/replay.py` — EventReplay: replay (instant/realtime), rebuild (snapshot → clear → replay → snapshot с идемпотентностью)
  - `freebuff_plugin_03/event/timeline.py` — TimelineEngine: get_timeline, format с иконками, search, by_session/by_user
  - `freebuff_plugin_03/event/audit.py` — AuditEngine: log_decision/action/config_change + audit trail + форматирование для CLI
  - `freebuff_plugin_03/event/pulse.py` — PulseEngine: подписка на EventBus, FTS5 маркер + fallback по категориям
  - **MCP интеграция** (`freebuff_plugin_03/mcp_server.py`):
    - `_get_event_store()` — lazy accessor
    - 5 новых MCP инструментов: `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse`
    - Каждый инструмент возвращает форматированные JSON/текст результаты

### Исправлено
- `freebuff_plugin_03/event/store.py`:
  - `conn.commit()` был вне `with self._connect() as conn:` блока (вызов на закрытом соединении) — исправлено
  - `sqlite3.Row.get()` не существует на Android/Termux → `dict(row)` конвертация
  - `store_batch` использовал `conn.total_changes` (аккумулятор) вместо `SELECT changes()` — исправлено
  - `_builtin_schema()` не содержал FTS5 триггеры — добавлены
- `freebuff_plugin_03/event/pulse.py`:
  - PulseEngine FTS5 поиск не находил события (маркер `_pulse` в metadata, не в data_json) — добавлен `data["_pulse"***REMOVED*** = True`
  - Добавлен fallback поиск по категориям при пустом FTS5 результате

### Проверка
- 61 тест Event Platform — **0 failures** (18.05s)
- Code review: 7 замечаний исправлены (FTS5 sync, total_changes, Pulse FTS5, миграция, builtin triggers, 4 тестовых падения)

---

## [4.6.0***REMOVED*** — 2026-07-29

### Добавлено
- **Bridge Layer — Phase 6: CoWork/Companion Platform (MCP ↔ ACP):**
  - `freebuff_plugin_03/acp_protocol.py` — Agent Collaboration Protocol (ACP):
    - AgentRegistry: регистрация, поиск, статус (online/offline/busy), heartbeat, prune offline
    - ACPHandler: подписка на ACP события через Event Bus, обработка discover/task/result/broadcast/status
    - AgentInfo + AgentStatus + ACPTask + ACPResult — dataclasses протокола
    - Система отправки задач с ожиданием результата (send_task + wait_for_result с timeout)
    - Heartbeat loop (30s) + автоматическая саморегистрация в локальном реестре при start()
    - Фильтрация задач по target (только себе), корректная обработка неизвестных tools
  - `freebuff_plugin_03/mcp_client.py` — MCP Client (два транспорта):
    - MCPClientBase: единый интерфейс (connect/disconnect/list_tools/call_tool/list_resources)
    - StdioMCPClient: подпроцесс + stdin/stdout, reader thread, очередь ответов с фильтрацией stale ID
    - HTTPMCPClient: Streamable HTTP (POST/GET/DELETE), Mcp-Session-Id, handshake initialize
    - Поддержка MCP 2025-03-26 протокола: initialize, tools/list, tools/call, resources/list, resources/read, prompts/list, prompts/get, ping
  - `freebuff_plugin_03/bridge_layer.py` — Bridge Layer (трансляция MCP ↔ ACP):
    - BridgeLayer: центральный координатор, запускает ACP и sync loop
    - connect_mcp_stdio / connect_mcp_http — подключение внешних MCP серверов
    - Connection params сохранены в BridgeMCPServer для автоматического reconnect
    - _forward_to_mcp — перенаправление ACP задач на MCP серверы
    - _rpc_to_server — произвольные JSON-RPC запросы к подключённым серверам
    - Sync loop: ping каждые 60s, автоматический reconnect, prune offline агентов
    - Регистрация MCP инструментов как ACP capabilities (префикс mcp.{server***REMOVED***.{tool***REMOVED***)
    - BridgeMCPServer: dataclass с connection_params для надёжного reconnect
    - 60 тестов (`tests_09/test_bridge_layer.py`) — 0 errors
  - **Bridge Layer интегрирован в MCP Server** (`scripts_01/mcp_server.py`):
    - `_get_bridge_layer()` — lazy accessor, создаёт BridgeLayer с EventBus
    - 4 новых MCP инструмента: `bridge_connect` (stdio/HTTP), `bridge_list`, `bridge_disconnect`, `bridge_rpc`
    - События EventBus: `bridge.connected`, `bridge.disconnected`, `bridge.rpc`

### Проверка
- 149 тестов MCP Server + Bridge Layer — **0 failures** (89 + 60)
- Code review: 4 итерации (name bug, connection_params, active_request_ids, sync loop logging, event publishing)
- Все 4 инструмента (bridge_connect, bridge_list, bridge_disconnect, bridge_rpc) зарегистрированы в MCP tools/list

---

## [4.5.0***REMOVED*** — 2026-07-29

### Добавлено
- **Scenario Engine** — `freebuff_plugin_03/scenario_engine.py`:
  - Сценарный движок с YAML-парсингом (YAML front matter + markdown тело)
  - `Scenario` dataclass: slug, title, description, category, complexity, tags, prompt, variables, template
  - `ScenarioEngine`: загрузка из `scenarios/`, list/search/get/apply, reload, stripping YAML
  - 83 теста (`tests_09/test_scenario_engine.py`) — 0 errors
- **11 готовых сценариев** в `freebuff_plugin_03/scenarios/`:
  - `freelance_parser.md` — Парсер сайта (категория: freelancing, сложность: средняя)
  - `freelance_tg_bot.md` — Telegram бот для заказов (категория: freelancing)
  - `agent_setup.md` — Настройка AI-агента (категория: ai)
  - `task_framework.md` — Фреймворк задач (категория: tool)
  - `freelance_tg_parser.md` — Парсер Telegram (категория: freelancing)
  - `freelance_mail_collector.md` — Сборщик почты (категория: freelancing)
  - `freelance_seo_auditor.md` — SEO аудитор (категория: freelancing, сложность: высокая)
  - `freelance_report_generator.md` — Генератор отчётов (категория: freelancing)
  - +3 существующих сценария из plugin
- **Telegram Bot для сценариев** — `freebuff_plugin_03/tgbot.py`:
  - `/scenarios list` — список сценариев с фильтрацией по категории
  - `/scenarios apply <slug>` — применить сценарий с вводом переменных
  - `/scenarios search <query>` — поиск по сценариям
  - Inline keyboard навигация: категории → сценарии → детали → применить
  - State management с TTL (600с) и лимитом 1000 записей
  - `_send_prompt_result` — статический метод (устраняет дублирование)
  - Text handler с поддержкой JSON, key=value, "готово"
  - 44 теста (`tests_09/test_tgbot.py`) — 0 errors
- **Стратегические документы:**
  - `IDEAS.md` — реестр архитектурных идей (12 идей со статусами, категориями, приоритетами)
    - Идеи: Bridge Layer, ACP, Presence, RAG 2.0, Session Manager, Workflow Engine, Live Collaboration, IDEAS v2, Summarization, MCP Client, Async Workers, Auto-Docs
  - `docs_10/vision/archive/VISION_2.0.md` — стратегическое видение Buffy как Companion Engine
    - Философия: «Buffy — не конкурент Claude/Cursor/OpenClaw, а универсальная надстройка»
    - 6 архитектурных принципов (LLM Sparingly, Event Bus, Live Collaboration, Presence, Project Pulse, Collaboration Roles)
    - Матрица анализа 12 концепций (ценность/риски/сложность/альтернативы)
    - Поэтапный план реализации (3 этапа, оценённые в часах)
  - `docs_10/vision/ROADMAP.md` — обновлён до v2.0.0:
    - Добавлена Phase 6: CoWork / Companion Platform
    - Phase 3 отмечена как ✅ ЗАВЕРШЕНА (с детальным содержанием)
    - Phase 4 расширена (Telegram Bot + Scenario Engine, ~85%)
    - Phase 6: foundation (Event Bus, ContextManager v3, Memory/Knowledge/Graph Engines, Plugin API, MCP, Scenario Engine, TG Bot, Intent Router, IDEAS, VISION 2.0)
  - `BUFFY.md` — обновлён раздел видения: добавлена Phase 6, IDEAS.md, VISION_2.0.md в документацию
- **Архитектурный аудит** — проведён полный аудит текущей архитектуры:
  - Проанализированы все модули: ContextManager, MemoryEngine, KnowledgeEngine, GraphIndex, EventBus, Orchestrator, ModelGateway, ToolRuntime, PluginAPI, MCPServer, ScenarioEngine, TelegramBot
  - Выявлены пробелы: отсутствие Bridge Layer, ACP, Presence, Live Collaboration
  - Создана карта архитектуры с фазами развития

### Исправлено
- `docs_10/vision/ROADMAP.md` — восстановлено детальное содержание Phase 3 (потеряно при обновлении), исправлен дубликат строки в конце

### Проверка
- Все тесты проходят — **0 failures** (Scenario Engine: 83, Telegram Bot: 44, существующие: 649+)
- Scenario Engine: 83 теста (list, search, apply, yaml_parsing, Scenario class, CLI, edge cases)
- Telegram Bot: 44 теста (handlers, callbacks, state management, "готово" flow)
- Все 11 сценариев загружаются корректно
- Code review пройден (3 итерации фиксов: state leak, code duplication, unused imports)

---

## [4.4.0***REMOVED*** — 2026-07-29

### Добавлено
- **OOM Protection System (защита от Signal 9/SIGKILL):**
  - `scripts_01/oom_protect.sh` — скрипт защиты от OOM: проверяет MemAvailable, убивает старые freebuff процессы при пороге <512 MB, чистит зависшие tmux сессии и PID-файлы плагина
  - Режимы: `--status` (диагностика), `--force` (принудительная очистка), `--check` (автоматический режим с условной очисткой)
  - Защита от самозацикливания: не убивает себя, python-процессы, tmux, bash-обёртки и proot
- **Интеграция OOM Protection в freebuff plugin:**
  - `freebuff_plugin_03/wrapper.py` — `_run_oom_protection()` вызывается перед `launch()` и `synchronous_oneshot()`; ошибки логируются, а не глотаются молча
  - `~/.local/bin/freebuff` — v4 wrapper: добавлена Фаза 0 (OOM Protection) перед стартом сессии; добавлен `set -u` с безопасными дефолтами для переменных
  - При каждом запуске `freebuff` (через CLI или Python wrapper) сначала запускается OOM protection, убивающий старые процессы

### Исправлено
- `freebuff_plugin_03/monitor.sh` — починен `PREFIX: unbound variable`: `${PREFIX***REMOVED***` заменён на `${PREFIX:-/data/data/com.termux/files/usr***REMOVED***`
- `scripts_01/oom_protect.sh` — удалён дублирующий `pgrep` блок в `kill_old_freebuff()` (оставлен только один проход по `ps aux`)
- `scripts_01/oom_protect.sh` — `return 1` заменён на `exit 1` (скрипт не sourced)
- `scripts_01/oom_protect.sh` — починен pipeline subshell bug в `clean_tmux_sessions()` (переменная `cleaned` теперь в главном shell)
- `scripts_01/oom_protect.sh` — `${PREFIX***REMOVED***` подстрахован дефолтным значением

### Проверка
- 649/649 pytest тестов — **0 failures** (114s)
- Self-check (bootstrap): все проверки пройдены
- OOM protection `--status` и `--check` — работают корректно
- Wrapper syntax: `bash -n` проходит

---

## [4.3.0***REMOVED*** — 2026-07-28

### Добавлено
- **Интеграция с freebuff CLI (out-of-the-box):**
  - `.freebuff/config.json` — метаданные проекта, корневые файлы, preferred commands
  - `.freebuff/AGENTS.md` — инструкции для свободного/Codebuff CLI
  - `AGENTS.md` — корневой канонический протокол агента
  - `.cursorrules` — fallback для Cursor-совместимости
  - `CLAUDE.md` — fallback для Claude-совместимости
  - `CODY.md` — fallback для Cody-совместимости
  - `BUFFY.md` — раздел «Работа через Freebuff CLI» с конфигурацией и стартовой последовательностью
  - `README.md` — секция про `freebuff` CLI
  - `docs_10/ops/AGENTS.md` — ссылка на корневой `AGENTS.md`
- **Telegram bot frontend для freebuff:**
  - `scripts_01/telegram_bot.py` — Bot API бот с ContextManager-сессиями, ModelGateway LLM-ответами, .env загрузкой, typing indicator, error handling
  - `tests_09/test_telegram_bot.py` — 6 unit-тестов (session ID, создание, сообщения, статус, fallback, новая сессия)
  - `scripts_01/start_telegram_bot.sh` — стартовый скрипт с .env sourcing
  - `requirements.txt` — добавлен `python-telegram-bot>=20.0,<21.0`

### Изменено
- `scripts_01/drift_check.py` — убраны runtime_05/кэш-директории из скана (`context_12/`, `data_13/`, `logs_14/` и др.); хрупкий regex заменён на line-based парсер (корректно обрабатывает пары ``` ``` и tree-диаграммы с вложенностью)

---

## [4.2.6***REMOVED*** — 2026-07-28

### Добавлено
- **Self-check triggers (promt10):**
  - `scripts_01/bootstrap.py` — startup self-check (Trigger 1): проверяет `BUFFY.md`, фильтрует тестовые/демо-конспекты, проверяет актуальность `TASK.md`.
  - `scripts_01/drift_check.py` — daily drift-check (Trigger 2): сравнивает статус-таблицы `BUFFY_PROJECT.md` с реальными файлами, индекс `seed_knowledge` с фактическими документами, структуру директорий с `BUFFY.md`/`docs_10/core/RULES.md`. Пишет `docs_10/audits/DRIFT_REPORT.md`, rate-limit — раз в день.
  - `scripts_01/cron_conspect.sh` — запускает `drift_check.py` каждые 30 минут (внутренний rate-limit once/day).
  - `tests_09/test_bootstrap.py` — 5 unit-тестов для самопроверки при старте.
  - `tests_09/test_drift_check.py` — 9 unit-тестов для drift-check.

### Исправлено
- `scripts_01/bootstrap.py` — `***REMOVED***` перенесён наверх; самопроверка обёрнута в `try/except`, чтобы не ломать старт.

---

## [4.2.5***REMOVED*** — 2026-07-28

### Изменено
- **scripts_01/auto_conspect.py** — демо-код вынесен в `scripts_01/demo_auto_conspect.py`; добавлены CLI-флаги `--demo` и `session_id`.
- **scripts_01/cron_conspect.sh** — убран непреднамеренный запуск демо-режима.
- **freebuff_cli.py** — добавлены команды `task start` и `task archive` для создания/архивации `TASK.md`.
- **tests_09/test_mcp_server.py** — исправлены импорты `typing.Optional` и `typing.Tuple`.
- **tests_09/test_freebuff.py** и **tests_09/test_auto_conspect.py** — добавлены тесты CLI `task` и `auto_conspect`.
- **scripts_01/session_utils.py** — вынесен shared helper `resolve_session_id`; убрано дублирование между `auto_conspect.py` и `freebuff_cli.py`.
- **tests_09/conftest.py** и **tests_09/test_session_utils.py** — добавлена shared `context_manager` fixture и 5 тестов для `resolve_session_id`.
- **tests_09/test_cron_conspect.py** — добавлен unit-тест, проверяющий, что `scripts_01/cron_conspect.sh` не запускает `auto_conspect` в demo-режиме.
- **projects_17/tg_terminal_messenger**:
  - `src_06/ui/app.py`: горячие клавиши переназначены с `Ctrl+S/Ctrl+Q` на `Ctrl+F/Ctrl+X` (терминальный XON/XOFF); отправка сообщений починена через `@on(Input.Submitted)` + `event.stop()` + `dialog.input_entity`; автоматический фокус на поле ввода.
  - `src_06/main.py`: добавлена точка входа.
  - `README.md`: актуализирована таблица горячих клавиш.
  - Удалён дублирующий каталог `/storage/emulated/0/PROJECTS/workstation/tg_terminal_messenger`; спецификации скопированы в `docs_10/original/`.
  - Проведён аудит против `tg_toolkit` (сравнительный анализ: multi-account, quick reply, bulk, export, profile).

---

## [4.2.3***REMOVED*** — 2026-07-28

### Изменено
- **scripts_01/seed_knowledge.py** — документы теперь авто-обнаруживаются из `docs_10/**/*.md` вместо жёстко зашитого списка. Добавлены исключения: `docs_10/AUDIT_*.md` и `docs_10/ops/TASK_TEMPLATE.md`.
- **tests_09/test_seed_knowledge.py** — добавлены тесты для `_collect_doc_sources` и исключений.
- **docs_10/core/RULES.md** — убраны ссылки на пустые `docs_10/architecture/` и `docs_10/decisions/`.
- **BUFFY_PROJECT.md** — актуализированы статусы: Knowledge Engine, Event Bus, Orchestrator отмечены как MVP/Каркас.

### Удалено
- **docs_10/architecture/** и **docs_10/decisions/** — пустые директории-призраки.

---

## [4.2.2***REMOVED*** — 2026-07-28

### Изменено
- **docs_10/vision/archive/ARCHITECTURE.md** — добавлен раздел "Автоматизация документирования" со ссылкой на `docs_10/core/RULES.md`.
- **docs_10/projects_meta/WORKERS.md** — добавлен раздел "Авто-документирование", ссылка на `buffy_autodoc.py` и pre-commit hook; чек-лист добавления нового worker дополнен пунктом про `CHANGELOG.md`.

---

## [4.2.1***REMOVED*** — 2026-07-28

### Добавлено
- **docs_10/ops/TROUBLESHOOTING.md** — документ с известными проблемами и решениями для:
  - Lightpanda worker (glibc/ARM64, CLI-флаги, пути к PandaScript, OOM)
  - Agent Context Bridge (интеграция, сессии, обрезка JSON)
  - pre-commit hook (обход блокировки)

---

## [4.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **pre-commit hook для авто-документации**:
  - `scripts_01/pre-commit` — tracked версия git pre-commit hook
  - `scripts_01/install_hooks.sh` — установка hook в `.git/hooks/pre-commit`
  - `scripts_01/buffy_autodoc.py --strict` — строгий режим с exit code 1
  - `severity=block/warn` у триггеров: `CHANGELOG.md` и `TASK.md` — блокеры, остальные — warning
- **docs_10/core/RULES.md** — добавлен раздел про pre-commit hook и его установку

### Проверка
- `mypy scripts_01/buffy_autodoc.py` — 0 errors
- `pytest tests_09/test_lightpanda_worker.py tests_09/test_agent_context_bridge.py` — 13/13 passed

---

## [4.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Lightpanda integration v1.0.0:**
  - `scripts_01/install_lightpanda.sh` — установка Lightpanda в Termux + proot-distro Ubuntu ARM64
  - `src_06/workers/lightpanda_worker.py` — Python-воркер: `execute_agent_task`, `run_script`, `dump_url`, `serve_cdp`, `stop_cdp`
  - `docs_10/projects_meta/LIGHTPANDA_INTEGRATION.md` — полный гайд по установке и использованию
  - `docs_10/projects_meta/WORKERS.md` — обзор паттерна workers
  - `docs_10/vision/archive/ARCHITECTURE.md` — архитектурная схема с Lightpanda
  - `tests_09/test_lightpanda_worker.py` — 8 unit-тестов

### Проверка
- 8/8 тестов `test_lightpanda_worker.py` — **0 failures**
- `mypy src_06/workers/lightpanda_worker.py tests_09/test_lightpanda_worker.py` — **0 errors**

---

## [4.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Интеграция ContextManager с termux-ai-agent v4.0:**
  - `scripts_01/agent_context_bridge.py` — мост для сохранения диалогов локального агента в freebuff ContextManager
  - `termux-ai-agent/main.py` — автоматическое логирование user/assistant/system сообщений, авточекпоинты каждые 10 сообщений, CLI `--freebuff-conspect`
  - Unit-тесты `tests_09/test_agent_context_bridge.py` (5 тестов)
- **BUFFY.md / BUFFY_PROJECT.md:** единый источник правил и архитектуры Buffy 2.0

### Проверка
- 5/5 тестов `test_agent_context_bridge.py` — **0 failures**
- `mypy scripts_01/agent_context_bridge.py tests_09/test_agent_context_bridge.py` — **0 errors**
- `mypy termux-ai-agent/main.py` — **0 errors**

---

## [2.9.0***REMOVED*** — 2026-07-28

### Добавлено
- **Параллельное выполнение шагов Orchestrator'а** (`scripts_01/orchestrator.py`):
  - `ThreadPoolExecutor(max_workers=N)` — независимые шаги запускаются параллельно
  - `concurrent.futures.wait(FIRST_COMPLETED)` — динамическое планирование DAG
  - `_handle_blocked_steps()` — пропуск шагов с проваленными зависимостями (SKIPPED)
  - `_publish_workflow_progress()` — событие `workflow.progress` с completed/total counts
  - `_execute_step()` — полностью thread-safe (lock на status update, context update)
  - `max_workers` параметр (default 4, 1 = последовательно)
- **EventBus интеграция расширена:**
  - `step.retrying` — событие при повторной попытке (retry_count, max_retries, error)
  - `workflow.progress` — прогресс выполнения (completed_steps / total_steps)
- **14 новых тестов** (`tests_09/test_orchestrator.py`):
  - Parallel: max_workers param/default, independent steps, chain deps, diamond DAG
  - EventBus: step.retrying, workflow.progress, step.completed, step.failed, lifecycle
  - Thread safety: context accumulation, blocked steps skip
- **Docstring обновлён** — step.retrying и workflow.progress в списке EventBus событий

### Проверка
- 51 тест orchestrator — **0 errors** (37 старых + 14 новых)
- 586 общих тестов — **0 failures**
- Code review пройден

---

## [2.8.0***REMOVED*** — 2026-07-28

### Исправлено (Critical Security)
- **Удалён `exec(code)` из orchestrator.py** — `_run_python` теперь использует
  `subprocess.run([sys.executable, "-c", code***REMOVED***)` вместо `exec()` с полным `__builtins__`.
  Код выполняется в изолированном subprocess, не может получить доступ к памяти родительского процесса.
- **Устранён `shell=True` во всех subprocess вызовах** (5 мест):
  - `orchestrator.py._run_shell`: `shell=True` → `["sh", "-c", command***REMOVED***`
  - `orchestrator.py._run_git`: `shell=True` + f-string → `["git"***REMOVED*** + shlex.split(command)`
  - `tool_runtime.py.GitTool.execute`: `shell=True` + f-string → `["git", command***REMOVED*** + shlex.split(args)`
  - `tool_runtime.py.ShellTool.execute`: `shell=True` → `["sh", "-c", command***REMOVED***`
- **Удалён дубликат `_run_shell`** в orchestrator.py (copy-paste bug)
- **Исправлен `NameError: full_cmd`** в `GitTool.execute` metadata
- **Добавлен `import shlex`** в orchestrator.py и tool_runtime.py
- **Очищен git history от API ключей** — `git filter-branch` переписал 14 коммитов,
  `.keys/` полностью удалён из всех коммитов
- **`.keys/` добавлен в `.gitignore`** — защита от случайного коммита

### Проверка
- 572 теста — **0 failures**
- Code review пройден

---

## [2.7.0***REMOVED*** — 2026-07-28

### Добавлено
- **FastAPI обёртка для MCP Server** (`scripts_01/mcp_fastapi.py`) — Streamable HTTP через uvicorn:
  - Async SSE streaming через `asyncio.Queue` (не `queue.Queue`)
  - `_dispatch()` — обёртка через `asyncio.to_thread()` для не-blocking вызова `BuffyMcpServer.dispatch()`
  - McpAsyncSession (@dataclass) + McpAsyncSessionManager (asyncio.Lock)
  - Origin validation через `urlparse().hostname` (DNS rebinding protection)
  - CLI: `--host`, `--port`, `--tunnel` (Cloudflare Tunnel)
  - `_start_tunnel()` — запуск `cloudflared tunnel --url` в subprocess, парсинг stderr для URL
  - `_print_tunnel_config()` — вывод конфига для Claude Desktop / Gemini
  - Health check `GET /` → `{status, server, protocol, endpoint, transport***REMOVED***`
- **Cloudflare Tunnel интеграция:**
  - `python scripts_01/mcp_fastapi.py --tunnel` — автоматический запуск cloudflared
  - Публичный HTTPS URL: `https://xxx.trycloudflare.com/mcp`
  - Конфиг для Claude Desktop выводится в stderr при старте
  - Cleanup при Ctrl+C: `tunnel_proc.terminate()`
- **CLI интеграция в mcp_server.py:**
  - `--fastapi` флаг — делегирует запуск в `mcp_fastapi.main()`
  - `--tunnel` флаг — передаётся в `mcp_fastapi.main()` (требует `--fastapi`)
  - Guard: `--tunnel` без `--fastapi` → exit с ошибкой
- **35 тестов FastAPI** (`tests_09/test_mcp_fastapi.py`):
  - uvicorn в daemon thread + `http.client` (тот же паттерн что и test_mcp_server.py)
  - `_uvicorn_server` fixture (module-scoped) — стартует uvicorn один раз на модуль
  - POST: initialize, ping, notification, tools/list, resources/list, prompts/list, tools/call, batch, errors
  - DELETE: session, unknown session, missing session-id
  - GET: missing session-id, unknown session, SSE content-type (raw socket)
  - Origin validation: evil.com (403), localhost (200), no origin (200), localhost.evil.com (403)
  - Async session manager: 7 тестов через `asyncio.run()` (без pytest-asyncio dependency)

---

## [2.6.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streamable HTTP транспорт для MCP Server** — реализован согласно спецификации
  MCP 2025-03-26 (замена устаревшего HTTP+SSE транспорта):
  - `McpSession` (@dataclass) — session с notification_queue (Queue) для SSE
  - `McpSessionManager` — thread-safe менеджер сессий (Lock, uuid4, create/get/delete/push)
  - `McpHttpServer(ThreadingHTTPServer)` — daemon_threads=True для clean shutdown
  - `McpHTTPRequestHandler(BaseHTTPRequestHandler)` — single endpoint `/mcp`:
    - **POST**: JSON-RPC запросы → `application/json` или `202 Accepted` для notifications
    - **GET**: SSE stream (`text/event-stream`) с 30s heartbeat для server-to-client notifications
    - **DELETE**: termination session → `204 No Content` (без Content-Length per RFC 7230)
    - `Mcp-Session-Id` header — генерируется при `initialize`, требуется для GET/DELETE
    - `Mcp-Protocol-Version` header — во всех ответах
    - `_validate_origin()` — защита от DNS rebinding (urlparse hostname check)
    - Non-initialize POST с невалидным `Mcp-Session-Id` → 404
    - HTTP/1.1 protocol_version для keep-alive/SSE
  - CLI: `--http`, `--host` (default 127.0.0.1), `--port` (default 8765)
  - `BuffyMcpServer.run_http()` — запуск ThreadingHTTPServer
- **Обновление протокола:** `PROTOCOL_VERSION` 2024-11-05 → 2025-03-26
- **36 новых тестов** (`tests_09/test_mcp_server.py`):
  - `TestSessionManager` — 10 тестов (create, get, delete, push_notification, thread safety, uniqueness)
  - `TestHttpTransport` — 26 тестов с реальными HTTP запросами (http.client + raw socket для SSE):
    - POST: initialize, ping, tools/list, resources/list, prompts/list, tools/call, shutdown, batch,
      notification (202), unknown method, invalid JSON, wrong path, invalid origin (403),
      localhost origin, no origin, invalid session-id (404)
    - GET: without session-id (400), unknown session (404), wrong path (404),
      SSE stream с notification (raw socket test)
    - DELETE: terminates session (204), unknown session (404), without session-id (400),
      no Content-Length header (RFC 7230)
    - Mcp-Protocol-Version header в всех ответах

### Изменено
- `docs_10/vision/ROADMAP.md`: Phase 4 обновлена — MCP Streamable HTTP добавлен (65% → 70%)
- `docs_10/decisions/DECISIONS.md`: ADR-003 — Streamable HTTP transport (pure Python ThreadingHTTPServer)

### Проверка
- 89 тестов mcp_server — **0 errors** (53 stdio + 10 session manager + 27 HTTP)
- Code review: 4 итерации, все issues исправлены

### Исправления по результатам code review (4 итерации)
1. `204 No Content` — убран `Content-Length: 0` (RFC 7230 §3.3.2)
2. Origin validation — `startswith()` → `urlparse().hostname` (защита от `localhost.evil.com`)
3. Mcp-Session-Id validation — non-initialize POST с невалидным session → 404
4. McpSession → `@dataclass` (консистентность с McpTool/McpResource/McpPrompt)
5. SSE stream test — переписан на raw socket (http.client блокировал на SSE без Content-Length)
6. Session TTL note — задокументировано отсутствие automatic cleanup

---

## [2.5.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streaming для Model Gateway** — реализован real-time streaming для всех 3 провайдеров:
  - `OpenAICompatibleProvider.generate_stream()` — SSE format (`data: {json***REMOVED***`, `[DONE***REMOVED***` terminator,
    `delta.content` extraction). DeepSeek, OpenRouter, SambaNova, DashScope.
  - `GeminiProvider.generate_stream()` — `streamGenerateContent` endpoint с `alt=sse` параметром,
    `candidates[0***REMOVED***.content.parts[0***REMOVED***.text` extraction.
  - `OllamaProvider.generate_stream()` — newline-delimited JSON (`stream: true`),
    `message.content` extraction, `done` flag + usage в финальном chunk.
  - `ModelGateway.generate_stream()` — fallback между провайдерами при ошибке стрима
  - `_publish_stream_event()` — EventBus интеграция (`model.called` / `model.fallback` с `streaming=True`)
  - CLI: `generate-stream` команда с `--timeout` флагом
- **Рефакторинг провайдеров:**
  - `_build_body()` method extracted в OpenAICompatibleProvider, GeminiProvider, OllamaProvider
  - `_convert_messages()` method extracted в GeminiProvider
  - Устранено дублирование кода между `generate()` и `generate_stream()`
- **9 новых тестов streaming** (`tests_09/test_model_gateway.py`):
  - OpenAI SSE format parsing (content + [DONE***REMOVED***)
  - Gemini SSE format parsing (streamGenerateContent)
  - Ollama newline JSON parsing (stream: true, done flag, usage)
  - BaseProvider fallback streaming (без реального стриминга)
  - ModelGateway.generate_stream() с моком провайдера
  - Error handling (no model raises ValueError)
  - Edge cases: empty lines, invalid JSON skipping
  - StreamChunk with usage stats

### Проверка
- 36 тестов model_gateway — **0 errors** (включая 9 streaming тестов)

---

## [2.4.0***REMOVED*** — 2026-07-28

### Добавлено
- **MCP Server** (`scripts_01/mcp_server.py`) — Model Context Protocol server на чистом Python:
  - JSON-RPC 2.0 over stdio (без внешних SDK, `mcp` пакет не установлен на Termux)
  - **12 tools:** git, file, shell, sqlite, http (из ToolRegistry) + knowledge_search,
    memory_store, memory_retrieve, memory_list, session_status, context_resume, plugins_list
  - **9 resources:** buffy://manifest, buffy://roadmap, buffy://spec, buffy://changelog,
    buffy://task, buffy://inventory, buffy://decisions, buffy://knowledge, buffy://memory
  - **3 prompts:** context_resume, knowledge_search, task_start
  - Protocol version: 2024-11-05
  - Lazy loading компонентов (ToolRegistry, KnowledgeEngine, MemoryEngine, ContextManager)
  - EventBus интеграция (mcp.server.initialized, mcp.tool.called, mcp.knowledge.searched)
  - Workspace-aware: ToolRegistry использует workspace сервера, не хардкод
  - CLI: --status, --tools, --resources, --prompts, --call, --read, --async-mode
  - Интеграция с Claude / Gemini / OpenClaw через claude_desktop_config.json
- **Тесты MCP Server** (`tests_09/test_mcp_server.py`) — 51 тест, 0 errors:
  - JSON-RPC helpers (response, error, notification)
  - Initialize handshake (protocol version, capabilities, server info)
  - Tools: list, call (knowledge_search, memory CRUD, session_status, context_resume)
  - Resources: list, read (manifest, knowledge overview, memory overview)
  - Prompts: list, get (context_resume, task_start)
  - Error handling (unknown method, invalid params, notifications)
  - Batch requests, server status, dataclasses, ToolRegistry integration

### Изменено
- `docs_10/vision/ROADMAP.md`: Phase 4 обновлена — MCP Server реализован (55% → 65%)

---

## [2.3.0***REMOVED*** — 2026-07-28

### Исправлено
- **Groq-валидатор в KeyPool:** Cloudflare на стороне Groq блокировал дефолтный
  `User-Agent: Python-urllib/3.x` (HTTP 403 / error 1010). Добавлен
  `hdrs.setdefault("User-Agent", "KeyPool/1.0")` в `validate_provider()`.
  Результат: Groq 0/6 → **6/6 валидных ключей**.
  Файл: `.keys/keypool.py`

### Изменено (4 проблемы системы)
- **Проблема 1 — StreamBridge интеграция:** Сообщения Buffy (user + assistant)
  теперь логируются в стрим-сессию через `buffy_stream_logger.py`. Активная
  сессия: `Buffy_chat_2026-07-28_192442`. За эту сессию залогировано 7+ сообщений.
- **Проблема 2 — Knowledge Engine наполнен:** `seed_knowledge.py --force`
  обновил 19 записей в MemoryLevel.KNOWLEDGE. FTS5 индекс: 27 документов.
  Включает: README, BUFFY.md, SPEC.md, ROADMAP, DECISIONS, AUDIT,
  ARCHITECTURE_REVIEW, SYSTEM_INVENTORY + 3 best-practice карточки.
- **Проблема 3 — EventBus активирован:** events.db была пуста (0 событий).
  Опубликовано 17 типов событий (system.startup, session.created, task.*,
  step.*, checkpoint.created, knowledge.*, agent.connected, model.*,
  tool.executed, plugin.enabled). Всего 55 событий, 3 активных подписчика.
- **Проблема 4 — Git инициализирован:** Настроен `user.name=Buffy`,
  `user.email=buffy@freebuff.local`. Первый коммит: 331 файл
  (feat: Freebuff/Buffy Project 2.0 — Agentic Platform & Knowledge OS).

### Проверка
- 439 тестов — **0 errors** (65.83 сек)
- Code review пройден

---

## [2.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **Авто-индексация Knowledge Engine при сохранении в Memory Engine:**
  - `scripts_01/event_subscribers.py`: `auto_index_subscriber` получает `content` и `workspace_root` из события `memory.stored`
  - `scripts_01/memory_engine.py`: `MemoryEngine` автоматически подключается к дефолтному `EventBus` внутри проектного workspace; событие содержит полный `content` и `workspace_root`
  - `scripts_01/event_bus.py`: `get_default_event_bus()` — ленивая инициализация EventBus + подписчики
  - `scripts_01/bootstrap.py`: инициализация дефолтного EventBus при старте сессии
- **Наполнение Knowledge Memory:**
  - `scripts_01/seed_knowledge.py`: сохраняет ключевые документы проекта (`README.md`, `BUFFY.md`, `SPEC.md`, `docs_10/*.md` и др.) и best-practice карточки в `MemoryLevel.KNOWLEDGE`
  - Автоматический `rebuild_index()` после заполнения
- **Тесты:**
  - `tests_09/test_event_subscribers.py`: 4 теста на авто-индексацию и `checkpoint_logger`
  - `tests_09/test_seed_knowledge.py`: 3 теста на `seed_knowledge.py`

### Изменено
- `docs_10/vision/ROADMAP.md`: Phase 2 отмечена как завершённая (100%)

## [2.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Auto-Rollup при CONTEXT_FULL:**
  - `scripts_01/context_manager.py`: `_save_context_rollup()` — генерирует сжатый конспект при превышении порога токенов
  - Сохраняется в `context_12/context_full_rollup.md` для инжекта в новый контекст
  - Возвращается `rollup_path` в результате `add_message()` / `save_checkpoint()`
- `scripts_01/stream_session.py`: при CONTEXT_FULL чекпоинте выводится путь к rollup

---

## [2.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Система стриминга контекста v2.0:**
  - `scripts_01/stream_bridge.py` — мост для интеграции Buffy с stream_session
  - `scripts_01/context_manager.py`: CONTEXT_FULL триггер (порог 28K токенов)
  - `scripts_01/context_manager.py`: `_estimate_tokens()` — точная эвристика токенов
  - `scripts_01/context_manager.py`: `prune_abandoned()`, `auto_abandon_stale()` — GC
  - `scripts_01/context_manager.py`: `get_context_status()` — мониторинг контекста
  - `scripts_01/context_manager.py`: `SCHEMA_VERSION = 2` + система миграций
  - `scripts_01/stream_session.py`: `BackgroundWriter` — асинхронная запись в файлы
  - `scripts_01/stream_session.py`: адаптивный чекпоинт-интервал (20→50)
  - `scripts_01/stream_session.py`: `prune_streams()`, `prune_all()` — GC
  - `scripts_01/stream_session.py`: in-memory кэш счётчика сообщений
  - `scripts_01/bootstrap.py`: интеграция StreamBridge при старте сессии
- **Документация:**
  - `docs_10/ops/TASK_TEMPLATE.md` — шаблон TASK.md для новых задач
  - `TASK.md` — файл текущей задачи (стриминг контекста v2.0)
  - `CHANGELOG.md` — этот файл

### Изменено
- `scripts_01/context_manager.py`: `add_message()` теперь принимает `token_count: int | None`
- `scripts_01/context_manager.py`: `get_messages()` сортирует ASC (старые→новые)
- `scripts_01/context_manager.py`: `_get_conn()` — timeout + busy_timeout
- `scripts_01/stream_session.py`: `log_message()` пишет в файлы асинхронно
- `docs_10/core/RULES.md`: добавлены TASK.md и CHANGELOG.md в обязательные документы

### Исправлено
- `scripts_01/context_manager.py`: удалены неиспользуемые импорты `re`, `time`

---

## [1.0.0***REMOVED*** — 2026-07-27

### Добавлено
- **ContextManager:** SQLite-хранилище сессий, сообщений, чекпоинтов
- **StreamSession:** непрерывная запись в файлы (conversation.log + raw.jsonl)
- **AutoConspect:** автосуммаризация при завершении сессии
- **FreebuffBridge:** мост для termux-ai-agent
- **Bootstrap:** восстановление контекста при старте сессии
- **SystemMonitor:** мониторинг RAM, CPU, батареи
- **FreebuffCLI:** 7 команд для управления системой
- **Cron:** автоматическая суммаризация каждые 30 минут
- **Тесты:** 15 тестов для ContextManager
- **Документация:** BUFFY.md, SPEC.md, RULES.md, SESSION_GUIDE.md, DECISIONS.md
### Добавлено\n- **Session Mesh v2.0** — спецификация и промпт для внедрения
