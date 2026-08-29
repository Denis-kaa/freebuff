# BUFFY UNFINISHED TAILS — from the dump (2026-07-27 → 2026-08-29)

Sources: buffy_history_full.md (58 sessions) + core_02/LESSONS.md + session endings.
Every item below was left mid-flight in the dump: an explicit pause, an interrupted
session, a stated follow-up that no later session picked up, or a documentation
conflict still unresolved. Ordered by priority.

---

## A. Explicitly paused, waiting on an external signal

### A1. imperial_phuket website clone — paused 2026-08-23, waiting on the client
- Session: 2026-08-23T02-30 (phone). User said: "пока зафиксируй, заказчик откликнется - вернемся" ("park it for now, when the client responds we'll come back").
- State saved in `imperial_phuket_CLONE_STATUS.md` (root): full audit report, cost estimate, 38 pages / 10 templates / 699 media files inventoried, media archive, handoff package + letter, all with SHA-256.
- One open defect noted in-session: a mangled/duplicated section in the handoff letter (str_replace produced duplicate "## Контакты" headings) — flagged, never fixed.
- Resume trigger: client replies on Kwork. No action possible until then.

---

## B. Dangling threads inside otherwise-finished sessions

### B1. 2026-07-28 — four platform gaps raised, only partially closed
Late in the 07-28 12-03 session the user raised four issues; the session (and the next one) closed some but not all:
1. Buffy → StreamBridge integration (Buffy's answers written to the stream) — addressed in-session, later regressions never re-verified.
2. **Knowledge Engine empty — DB exists, no data.** knowledge_objects/knowledge_links/knowledge_tags/knowledge_sources tables still empty to this day.
3. events.db empty / EventBus unused — partially closed later (lisa_estimator events exist); the post-08-23 gap was only closed on 08-29 by the TUI history import.
4. Git repo not initialized — resolved (repo exists now).

### B2. 2026-07-29 — Termux "error 9" (process killed) after long tasks
- Investigated in 07-29 01-32 session; mitigations discussed (phantom process reaper, shorter tasks).
- Never confirmed fully solved; long pytest runs still risk it (tmux server died again on 08-14 mid-suite).

### B3. 2026-08-02 14-24 — tg_terminal_messenger SPEC features not implemented
- Last AI message of the session: about to add **FilePicker for sending media** and **chat archive (archival of conversations)** to the TUI TG app.
- Session ended there; no later session revisits these two SPEC features.

### B4. 2026-08-02 10-55 — stale Codebuff CLI call source never found
- User answered "хочу" to the offer: (1) find the exact source of the stale/deprecated shim call, (2) register it in the canonical debt registry.
- Session ended right after; the "exact source" hunt was never completed (only the debt row got registered).

### B5. 2026-08-02 15-24 — "send really feya a message about what can be done in Termux"
- Session shows the request being picked up, then ends. No confirmation the TG message was ever sent.

### B6. 2026-08-07 — the 9-books structured-education material
- User wanted a full verbatim merge of 9 scattered books into one structured educational path (no paraphrase, dedup overlapping chapters, add explanations).
- The session ends mid-clarification ("я обьясню, у меня есть девять книг..."). No book file, no reading plan artifact exists in the repo.

### B7. 2026-08-09 17-45 — leviathan integrity check after cleanup
- Session ends while scanning var_www/opt/root (6.6 GB) for leftover leviathan sources. Final verification never reported.

### B8. 2026-08-14 20-33 — pomt83 full pytest suite run never confirmed
- The tmux session `pomt83_pytest4` died ("no server running") mid-poll; the done marker never appeared; the suite result was never recorded.

### B9. 2026-08-17 — kwork_site ROADMAP.md
- Last AI message: about to create `projects_17/kwork_site/ROADMAP.md` (flagged as the missing doc per PROJECT_RULES §2). File does not exist in the repo — the session ended before writing it.

### B10. 2026-08-20 01-35 — Chrome install
- Attempt to install Chrome/Chromium in Termux ends with the session. No browser ever installed (still relevant for the browser-use prototype idea).

### B11. 2026-08-22 06-46 — update_freebuff_safe.sh from native Termux
- The script intentionally refuses inside proot; user was told to run `bash scripts_01/update_freebuff_safe.sh` from native Termux. No record it was ever run/successful.

### B12. 2026-08-23 13-10 — automation idea for the friend's dairy/meat sales workflow
- Conversation about automating "call warm/cold leads → ask what they need → create order" ends mid-exploration. No spec, no project folder.

### B13. 2026-08-24 06-29 — severny_chay bore tunnel verification
- Last message: TCP tunnel `bore.pub:57365` up, "Testing..." — the external reachability check result was never recorded.

### B14. 2026-08-27 (server) — security fixes in ai-dubber routes.py
- Last AI message lists the endpoint-by-endpoint fix plan (ownership checks on POST /jobs/{id***REMOVED***/cancel, etc.). No later server session confirms all fixes landed.

### B15. 2026-08-28 (server) — video A1AUPWrd-0A usefulness verdict
- Transcription pipeline started ("figuring out what tools are available"); no analysis output saved on the server side.

---

## C. Named debts still open in the platform's own ledgers

### C1. The three flagged CHANGELOG/debt leftovers (stated twice, never actioned)
From the 08-03 22-45 session, repeated verbatim on 08-03:
1. naming convention cleanup (promt47.md)
2. test counter drift (1891→1991)
3. stale /tmp paths in old CHANGELOG/debt entries
User instruction: "Разобрать их в отдельной задаче" — that separate task never happened.

### C2. CAN-8 documentation conflict (core_02/LESSONS.md line 294 + 868)
- LESSONS.md says CAN-8 closed v5.57.0; ARCHITECTURAL_DEBT.md says CAN-8 OPEN. The fact-check session itself documented the contradiction and did not resolve it.

### C3. Pre-commit hook for buffy_autodoc.py (07-28)
- Requested ("Добавить pre-commit hook..."), planned in-session, no hook file exists in .git/hooks or scripts_01.

### B-list platform items carried in-session but never picked up:
- **Overlay notification system** (07-27, prompt at line 116 of dump): floating overlay with Pause/Resume/Stop over Termux — spec'd, never built.
- **Phase 0 rollup** (07-28): auto-summary on CONTEXT_FULL for context injection — added to todo, never built.
- **Phase 2 leftovers** (07-28): auto-indexing documents into Memory Engine + filling Knowledge Memory with best practices — the two named TODOs of Phase 2.
- **Multi-prompt support in MissingRegistry** (prompt_paths/related_prompts) — registered in 09_FUTURE_GAPS row #8, not implemented.
- **CapabilityGapLlmExecutor** (LLM variant with ModelGateway DI, ≥18 capabilities vs 15 deterministic) — explicitly a Todo in v1, not implemented.
- **LEVIATHAN split** (08-03): duplicate the project into a separate LEVIATHAN repo (platform docs/scripts/contracts only, Buffy as a connected agent) — discussed, never started.
- **Workspace/project registration UX** (08-03): the 5000-word plain-language positioning doc with ≤50 open questions — no such md in root.
- **promt 49 plan** (08-05): user asked to show the implementation plan since it was "partly done" — answer not in dump.
- **promt 65 §33 Minimal v0.1** (08-10): synthesize 5 meta-audit themes into a buildable roadmap — no follow-through artifact.
- **Frontend not finished** (08-12, "помоему не завершена задача по созданию фронтенда") — user's own words; never picked back up.
- **Furniture/canvas broken in interior prototype** (08-12: "мебель не нажимается, канвас не работает") — bug report with no fix session.
- **Vkusvill BUG-001 Excel/Python parity + independent Excel-eval (pycel/LibreOffice)** — parity work started, independent Excel path not confirmed.
- **Vkusvill vacancy fact-check** (verify "вайб-кодинг" quote in hh vacancy 135746053) + final cover letter send gated on TRUST ≥8.5 — the send was conditional; no confirmation in dump.
- **hh release pipeline** (08-14-ish, line 3242): commit+push, tag force-push, CI poll, release verify — TODOs left unchecked mid-run.

---

## D. Interrupted responses (session cut mid-answer, task possibly lost)

- 2026-07-29 21-51 — "[response interrupted***REMOVED***" (status check session, 2 messages).
- 2026-08-08 23-07 — "[response interrupted***REMOVED***" right after "прочитай promt64".
- 2026-08-22 04-53 and 06-41 — two "[response interrupted***REMOVED***" sessions (update checks).
- 2026-08-29 08-00 (final AI message) — dump build verification cut off mid-run ("53 телефонные сесс..."); the current session is the continuation.

---

## E. Confirmed clean (no tail)

All remaining sessions (both devices) ended with the work complete: context restores,
audits with reports written, releases committed, projects scaffolded, отклики saved,
forensics written, and the unified dump itself. Those are listed in
BUFFY_SESSION_SUMMARY_2026-07-27_to_08-29.md and are not repeated here.

---

## Suggested pickup order (highest value first)

1. **C1** — the three flagged debts (naming convention, test counter drift, /tmp paths): small, well-defined, unblocks clean CHANGELOG.
2. **B3** — FilePicker + chat archive for tg_terminal_messenger: user explicitly wanted the features.
3. **B6** — the 9-books structured material: a concrete personal deliverable the user cared about.
4. **C2** — resolve the CAN-8 contradiction between LESSONS.md and ARCHITECTURAL_DEBT.md.
5. **B9** — write the missing kwork_site/ROADMAP.md (platform-rules compliance).
6. **A1** — imperial_phuket: nothing to do until the client responds, but re-verify the handoff letter's mangled headings before sending.
