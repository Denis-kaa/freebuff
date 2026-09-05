# AUDIT_FINDINGS — PM OS stages/prompts 1–9

> Updated: 2026-09-04. PM OS runtime verified on `whimco` via port `8010`; port `80` serves an unrelated application and was left unchanged.

## Executive result

The runtime is operational and stable for the current development/demo scope. The implemented core path is verified on `whimco`; however, stages 3–9 are not fully complete against every detailed prompt section. They should be marked `PARTIAL`, not fully done.

## Evidence

- Backend compile: `COMPILE_OK`;
- backend regression: **122 passed** (including Teams tests **3/3** and Stage 5 search regression);
- Stage 5 backend: **22 passed** (including source-title search regression);
- stage 8 live acceptance: **10/10**;
- stage 9 live acceptance: **22/22**;
- stage 9 UI API flow: **8/8**;
- frontend permission tests: **11/11**;
- frontend build: successful;
- Playwright smoke: `/`, `/projects`, `/calendar`, `/automations`, `/team`, `/roles`, `/profile`, `/automation-history` — **0 console errors, 0 page errors, 0 failed responses**;
- Stage 5 calendar E2E on PM OS `:8010`: month/week/day, URL state, event search, payment filter, project navigation, custom event creation — **passed; 0 console/page errors**.

## P1 — security / correctness

### F-001 — Real authentication is absent (DEFERRED)

- Current identity: `X-User-Id` plus controlled demo-admin fallback.
- Authorization and workspace isolation are active.
- This is not counted as a defect for the current dev/demo scope by decision ADR-002.
- Before public production, require a real Auth Provider/session layer and remove unrestricted demo fallback.

### F-002 — Field-level permission table is not enforced

- `field_permissions` model/table exists.
- Finance is protected by coarse `finance.read` and masked in project/export APIs.
- Individual field rules are not dynamically read from `field_permissions`.
- Next: implement a field policy service and tests for per-field read/update.

### F-003 — Import authorization fixed during audit

- `project.import` is now checked on upload, mapping, history, job inspection, confirm/cancel and templates.
- Jobs/mappings use `ctx.workspace_id`.
- Verified Viewer receives 403.

## P2 — functional gaps

### F-013 — Stage 7 View Engine browser verification and URL-state fix

- Server Stage 7 suite: **6/6 passed**.
- Live browser acceptance on `whimco`: default views, saved view with nested filter controls, URL view ID after creation, reload restoration, Table/Kanban/Calendar switching, global search, temporary-view cleanup, and zero browser errors.
- Fixed `ProjectsView` so a newly created view writes `?view=<id>` to the URL, making the saved view immediately shareable/restorable by the existing route contract.
- Stage 7 remains `PARTIAL`: grouping/virtualization, complete share visibility enforcement, and full custom-field/formula browser scenarios are not yet closed.



### F-004 — Teams basic API/UI implemented; dedicated acceptance remains

- `Team` and `TeamMember` tables/models exist.
- Contract-first CRUD and member assignment endpoints are deployed:
  `GET/POST/PATCH/DELETE /workspaces/{id}/teams` and member add/remove routes.
- TeamView supports team creation, deletion and member toggling for authorized users.
- Workspace isolation and `member.read`/`member.update` checks are enforced.
- Backend regression remains green; focused Teams tests cover CRUD, member assignment, duplicate-name rejection and workspace isolation. Dedicated Teams browser acceptance should be added next.

### F-005 — Invitation accept is authentication-dependent

- Safe accept for an already identified user is implemented.
- Unauthenticated link → account creation/login → membership is deferred until real auth.
- Resend is not implemented.

### F-006 — Ownership transfer foundation exists

- Owner-only transfer endpoint and Team UI action are implemented.
- New owner must be active; old owner becomes Admin; audit is recorded.
- Future enhancement: integrate transfer into owner deactivation flow.

### F-007 — Stage 6 Google Sheets is incomplete

- Local Excel/CSV import/export is verified on `whimco`: backend Stage 6 `19/19`; live UI covers template download, invalid CSV preview with confirmation blocked, CSV export, and zero browser/server errors.
- `google_sheets.py` still contains a TODO for gspread/credentials/table enumeration; the live status correctly reports Google as not configured.
- OAuth, spreadsheet enumeration, import/export, sync conflict resolution and manual Google Sheets acceptance are not implemented/proven.

### F-008 — Background import jobs are not complete

- Current import processing remains request-bound.
- Prompt §46 asks for background worker/progress for large imports; job status fields exist, but no worker queue/progress lifecycle is wired.
- Next: use existing queue infrastructure only after checking current project conventions.

### F-009 — Dashboard/calendar browser acceptance is incomplete

**Verified dashboard controls:** add, drag, resize, reload persistence, widget settings, hide/restore, rename, duplicate, and delete pass on `whimco`. **Verified calendar controls:** month/week/day views, URL query state, task-title search, payment type filter, event details/project navigation, and custom-event creation pass with zero browser errors. Recurrence and broader cross-stage browser coverage remain future work.

- Backend/unit coverage is substantial.
- Calendar Engine search now matches both linked source projects and event-owned text (task titles, production fields, documents, and custom-event title/description).
### F-010 — Stage 3 delivery/NextAction completeness

- Core items/tasks/documents/events exist.
- Delivery data and a dedicated `NextActionService` are not fully represented as separate contracts/UI blocks.

## P3 — test/documentation hygiene

### F-011 — Acceptance scripts mutate shared demo DB

- `acceptance_v8.py`, `acceptance_v9.py` and `ui_acceptance_v9.py` create test rows; the latest server run completed successfully.
- Focused Teams tests use an isolated test workspace and do not rely on demo members.
- The live acceptance scripts still need deterministic cleanup or a dedicated acceptance database.

### F-012 — Prompt 1 was restored and reviewed

- Canonical source `pompts_11/user/new/1.md` is now present.
- It defines the platform-wide architecture and acceptance contract, not only one narrow feature.
- Stage 1 remains `PARTIAL` because implementation evidence is distributed across stages 2–9 and full browser acceptance is not yet captured.
- Next: create a traceable Stage 1 acceptance checklist without modifying the prompt.

## Architecture candidates for later Workspace OS review

These are candidates, not extraction decisions:

1. Workspace/membership/role/permission contracts;
2. event chain + audit log;
3. notification and automation contracts;
4. project-centric context/memory/acceptance model;
5. dashboard/widget data-provider contracts;
6. portable workspace isolation patterns.

Review constraints:

- preserve B1/B2/B7/B9/B10 boundaries;
- separate generic primitive from PM OS-specific policy;
- no direct runtime-state merge;
- extraction only through an ADR and backward-compatible adapter.

## Prioritized backlog

1. P0/P1 before production: real authentication, dynamic field permissions, complete invitation accept.
2. P1/P2: dedicated Teams browser acceptance and invitation/team UX polish.
3. P2: Google Sheets OAuth/sync and background imports.
4. P2: dedicated Playwright acceptance for dashboard/calendar/import/export flows.
5. P2: delivery/NextAction contracts and remaining stage 3 UX.
6. P3: isolated acceptance fixtures and prompt-1 source recovery.
7. After facts are stable: Workspace OS portability review.
