# TASK: Freebuff — открытые задачи и состояние проекта

**Версия проекта:** v5.189.67 (2026-08-20; предыдущая: v5.189.66)
**Обновлено:** 2026-08-21 (R2 version-sync: headers → v5.189.67 + snapshot refresh — TRACK-001 close (consistency_check exit 0 + idempotency invariant); previous snapshot v5.189.36 dated 2026-08-18)
**Предыдущее обновление:** 2026-08-16 (R1 version-sync: headers → v5.189.18 — Advanced Opportunity Ranking (промт 086): rank_candidates + discover --rank, register-first `opportunity_ranking` closed)
**Предыдущий снапшот:** v5.74.0 (2026-08-04) — см. `CHANGELOG.md` для полной истории промежуточных релизов

> **Иерархия источников правды (anti-duplication принцип CON-17):**
>
> - **Закрытые вехи v5.21.0 → v5.59.0** → [`CHANGELOG.md`***REMOVED***(CHANGELOG.md) (полная история, не дублируем здесь).
> - **Архитектурные долги** → [`docs_10/core/ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) (реестр с §3 OPEN + §5 RESOLVED).
> - **Пост-консолидационные миссии** → [`docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md`***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) §9 (promt42/43).
> - **Жизненный цикл / правила / манифест / глоссарий** → [`docs_10/core/`***REMOVED***(docs_10/core/) (CORE_PROMPT / ARCHITECTURE_MANIFEST / GLOSSARY / LIFECYCLE / FINAL_STRUCTURE / CODE_QUALITY_STANDARD).

---

## 🎯 OPEN TASKS — User-Facing (Product/Phase 5)

Все три пункта НЕ начаты (нет исходного кода; только спецификации в промтах). Реализация — отдельный sibling-проект по конвенции `projects_17/<project_name>/` (как `interior_planner_app/`).

### 5.1 Flutter-приложение (idea · web-first)
- [ ***REMOVED*** **💡 Идея на будущее** (не является sprint-ready). Мобильное приложение Freebuff на Flutter (Android).
- **Strategy · web-first:** Flutter-mobile фаза **отложена**. Первый этап — web-приложение (см. [`buffy-playground_19/`***REMOVED***(buffy-playground_19/) — React + TypeScript + Vite scaffold) — работы уже ведутся. Web-UI даёт быструю итерацию (DevTools + hot reload + cross-platform без APK-build); Flutter-mobile подключается после того, как web-app достигнет нужного UX/feature-coverage.
- **Не путать с:** `projects_17/interior_planner_app/` (React Native + Skia — sibling-проект interior_planner, не Freebuff).
- **Спецификация (когда дойдёт):** [`pompts_11/039_12_terminal_ai_studio_mobile.md`***REMOVED***(pompts_11/039_12_terminal_ai_studio_mobile.md) — Flutter SDK Termux ARM64, APK-сборка, OpenAI-совместимый HTTP API порт 8080.
- **Где ещё упоминается:** [`docs_10/audits/AUDIT_2026-07-29_v5.0.0.md`***REMOVED***(docs_10/audits/AUDIT_2026-07-29_v5.0.0.md) §622 (P3-2 XL-effort); [`pompts_11/003_01_buffy_2_agentic_platform.md`***REMOVED***(pompts_11/003_01_buffy_2_agentic_platform.md):493.
- **Зависимости (когда фаза начнется):** §5.2 Foreground Service (обязательно для живучести процесса — Android 15+ Phantom Process Killer).
- **Предлагаемый путь (когда фаза начнется):** `projects_17/freebuff_flutter_app/` (sibling-project, как `interior_planner_app/`).

### 5.2 Foreground Service (Phantom Process Killer fix)
- [ ***REMOVED*** Android Foreground Service для Flutter-приложения, устойчивый к Phantom Process Killer.
- **Статус:** deferred вместе с §5.1 до начала Flutter-mobile-фазы (см. §5.1 web-first strategy). Web-app-этап не требует Foreground Service.
- **Спецификация:** [`pompts_11/039_12_terminal_ai_studio_mobile.md`***REMOVED***(pompts_11/039_12_terminal_ai_studio_mobile.md) — разделы "Flutter + Termux" (часть 6) и "Phantom Process Killer" (часть 8).
- **Особенности Android 15+:** требуется foreground service type `connectedDevice` (НЕ `dataSync` — deprecated).
- **Связь с core:** управляет Freebuff core процессом через `android.app.Notification` + wake lock.
- **Зависимости:** §5.1 Flutter-приложение.

### 5.3 Remote Sync
- [x***REMOVED*** **✅ architecturally decided (ADR-010)** — Option B (Telegram-stored Relay) primary architecture.
  - **Phase 5.3-A spec-only** ✅ v5.62.0 — `runtime_05/scenarios/19_remote_sync/{scenario.yaml, README.md, interface.py***REMOVED***` (Protocol + dataclasses + manifest).
  - **Phase 5.3-B runtime** ✅ v5.62.1 — `core_02/remote_sync.py::RemoteSyncCoordinatorImpl` (Telethon-based + per-key LWW + chunking + 24h quarantine; 26 mock tests pass in 1.55s).
  - **Phase 5.3-C TG round-trip runner** ✅ v5.62.2 — `scripts_01/e2e_remote_sync.py` (4-stage pipeline: pre-flight → push → round-trip via `TGClient.get_messages`; 14 mock tests pass in 7.52s; awaiting operator real TG round-trip).
  - **Спецификация:** [`pompts_11/003_01_buffy_2_agentic_platform.md`***REMOVED***(pompts_11/003_01_buffy_2_agentic_platform.md):497 (Phase 5 параллельно Flutter UI).
- **Спецификация:** [`pompts_11/003_01_buffy_2_agentic_platform.md`***REMOVED***(pompts_11/003_01_buffy_2_agentic_platform.md):497 (Phase 5 параллельно Flutter UI).
- **Зависимости:** нет строгой зависимости от §5.1/§5.2 (можно стартовать независимо как backend-фичу). Важно: sync-target определяет scope (peer-to-peer vs cloud — выбор за командой).
- **Note:** существующая `interior_planner_app/src/store/roomStore.ts` использует локальный AsyncStorage без sync — Remote Sync **не закрывает** её.
- **ADR (v5.62.0):** ✅ [`docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md`***REMOVED***(docs_10/engineering-memory/decisions/ADR_010_Remote_Sync_Telegram_Relay.md) — Option B (Telegram-stored Relay) PRIMARY, Bluetooth companion DEFERRED to v6.x. Termux Android-Bluetooth hostile (RFCOMM requires root); TG-substrate free via AV-3 invariant; CAN-3 + CAN-9 verified chat_id + round-trip.
- **SPEC contract (v5.62.0):** ✅ [`runtime_05/scenarios/19_remote_sync/`***REMOVED***(runtime_05/scenarios/19_remote_sync/) — `scenario.yaml` + `README.md` + `interface.py` (Protocol + 4 enums + 3 frozen dataclasses + helpers).
- **Runtime (v5.62.1):** ✅ [`core_02/remote_sync.py::RemoteSyncCoordinatorImpl`***REMOVED***(core_02/remote_sync.py) — Telethon-based runtime re-using `core_02/telegram_contract.py::report_to_*` функции (function-based API, не class-based). SendFn / HistoryFn / MeFn injection hooks для mock-based tests. Per-key LWW + 24h quarantine + 3500-char chunking + gzip_base64 fallback. 26 mock tests в [`tests_09/test_remote_sync.py`***REMOVED***(tests_09/test_remote_sync.py) pass in 1.55s. Phase 5.3-B specs-closed; Phase 5.3-C persisted listener loop deferred (ровно як ADR-010 §Implementation Disclaimers describes).
- **Real TG round-trip runner (v5.62.2, THIS RELEASE):** ✅ [`scripts_01/e2e_remote_sync.py`***REMOVED***(scripts_01/e2e_remote_sync.py) — e2e runner mirroring `e2e_promt47.py` discipline. 4-stage pipeline (pre-flight → planning → push → round-trip via `TGClient.get_messages`). Per-run log file `docs_10/e2e_logs/remote_sync_<UTC-TS>.md` honoring user directive `<timestamp>`. Dual-channel via `--sync-group` flag. TGClient.get_messages pivot к limit-scan (TGClient не expose `ids=` kwarg — matches Phase 5.3-B `_history_via_tgclient` pattern). 14 mock tests в [`tests_09/test_e2e_remote_sync.py`***REMOVED***(tests_09/test_e2e_remote_sync.py) pass in 7.52s. CLI flags: `--silent --skip-tg --sync-group --dry-run --e2e-log PATH --run-tag TEXT`.
- **Что в работе в 5.3-C**: First real TG round-trip invocation awaiting operator (`python3 scripts_01/e2e_remote_sync.py --sync-group --silent`) з TG session alive; результати у `docs_10/e2e_logs/remote_sync_<TS>.md`. CAN-9 cumulative audit-trail: next entry msg_id_X = 138172 (post-v5.59.0 138170/138171).

---

## 📊 Состояние проекта (snapshot v5.189.67, 2026-08-20)

- **Версия:** v5.189.67 ([`CHANGELOG.md`***REMOVED***(CHANGELOG.md) top)
- **Тесты:** **3342+ passed, 0 failures** (AST-truth counter; цель в [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(docs_10/core/CODE_QUALITY_STANDARD.md) §11.6 — `3342+ passed`)
- **Реестр возможностей (MissingRegistry):** 45 записей — 28 implemented · 16 registered · 1 design_ready; `missing_registry check` exit 0 (B10/R-127)
- **Consistency:** `consistency_check` exit 0 на baseline v5.189.67 (TRACK-001 CLOSED — idempotency-инвариант восстановлен; counter 3104→3342)
- **Новое наблюдение (2026-08-21):** `pompts_11/promt103.md` нарушал naming-конвенцию `NNN_TT_name.md` (CAN-10 класс) — **переименован** в `pompts_11/103_19_forensic_engineering_reporter.md` (см. ниже); `consistency_check` снова exit 0.
- **Закрыто между v5.21.0 → v5.59.0:** 38 релизов (security audit Steps 0/1/2 `pompts_11/TASK_SECURE_MCP_ACCESS.md` / MANDATORY RUNTIME CONTRACT / TG chat_id resolution v5.40.0 / CAN-3/8/9/16 / Block-A recovery v5.58.0 / TG integration contract v5.42.0 / Distributed Agents v5.14.0 / Plugins v5.20.0 / Presence+Collab+Roles+Pulse+RAG v5.17–v5.23 / Metrics Dashboard v5.19 / Counter milestone table v5.55 / validations drift + consistency). Детали и verify gates — в `CHANGELOG.md` (НЕ дублируем здесь).
- **Закрыто между v5.60.0 → v5.189.67:** ~30+ релизов — Forge/Factory vertical slices (Phases 4–13), Intelligence Loop (opportunity_engine, whim_capture, hypothesis_ledger, corpus_persistence/inspector, pricing_enumerator, taxonomy_gap_report, weighted_scoring_engine, devil_advocate_pass), Remote Sync (v5.62–v5.67), capability_gap_auditor + REGISTER-FIRST lifecycle. Полная история — в `CHANGELOG.md`.
- **Mission Lock:** 🔓 снят 2026-08-01 после закрытия всех 10 этапов консолидации promt32 + ADR-001…009 + canonical steps promt36/37 (Work Area as View, User-Choice Override, Context-Aware Routing, Plugin Contract). См. [`docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md`***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) §0.
- **DEBT-001…007 (post-consolidation):** ✅ все Resolved. Источники: [ARCHITECTURAL_DEBT.md §3.1–§3.3***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) + §5.5–§5.12.
- **TRACK-001 (§20 Missing-Capabilities Map Drift):** ✅ CLOSED (v5.189.67) — counter refresh 3104→3342 + idempotency test + §20 backfill; см. [`ARCHITECTURAL_DEBT.md`***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) §3.0/§5.23.
- **Закрыто между v5.21.0 → v5.59.0:** 38 релизов (security audit Steps 0/1/2 `pompts_11/TASK_SECURE_MCP_ACCESS.md` / MANDATORY RUNTIME CONTRACT / TG chat_id resolution v5.40.0 / CAN-3/8/9/16 / Block-A recovery v5.58.0 / TG integration contract v5.42.0 / Distributed Agents v5.14.0 / Plugins v5.20.0 / Presence+Collab+Roles+Pulse+RAG v5.17–v5.23 / Metrics Dashboard v5.19 / Counter milestone table v5.55 / validations drift + consistency). Детали и verify gates — в `CHANGELOG.md` (НЕ дублируем здесь).
- **Mission Lock:** 🔓 снят 2026-08-01 после закрытия всех 10 этапов консолидации promt32 + ADR-001…009 + canonical steps promt36/37 (Work Area as View, User-Choice Override, Context-Aware Routing, Plugin Contract). См. [`docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md`***REMOVED***(docs_10/vision/ROADMAP_PROMT32_CONSOLIDATION.md) §0.
- **DEBT-001…007 (post-consolidation):** ✅ все Resolved. Источники: [ARCHITECTURAL_DEBT.md §3.1–§3.3***REMOVED***(docs_10/core/ARCHITECTURAL_DEBT.md) + §5.5–§5.12.
---




## Phase 4 CLOSED 2026-08-09 (v3.5)

- Workspace OS Research workflow completed: 39/39 sections = 100% CLOSED
- Mission compliance: 7.6/10 weighted (above 6/10 target by 27%)
- See: `docs_10/MISSION_CLOSE_20260809.md` for full summary
- Phase 5 = §39.6 forward-action implementation (~6-8 hours)

