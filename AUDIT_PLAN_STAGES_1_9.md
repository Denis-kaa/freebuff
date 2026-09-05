# AUDIT PLAN — PM OS stages/prompts 1–9

## Goal

Verify whether every requirement in prompts 1–9 was actually implemented, tested and deployed, while distinguishing `DONE`, `PARTIAL`, `MISSING`, `DEFERRED`, `BLOCKED` and `CONFLICT`.

## Scope boundary

This is an audit of the PM OS development project. It does not merge PM OS runtime workspaces with the Workspace OS platform Workspace. Any reusable primitive found during the audit goes to a later architecture review and ADR.

## Audit method

For each prompt section:

1. read the source prompt and preserve it unchanged;
2. extract atomic requirements and section IDs;
3. locate backend/frontend/schema/migration implementation;
4. locate unit, integration, acceptance or Playwright evidence;
5. run a live server check where evidence is missing;
6. classify status and severity;
7. record next action and owner file.

### Statuses

- `DONE` — implementation + evidence + no known regression;
- `PARTIAL` — meaningful implementation exists, but a requirement/subflow is missing;
- `MISSING` — no implementation found;
- `DEFERRED` — deliberately postponed and documented;
- `BLOCKED` — cannot complete until an external decision/input exists;
- `CONFLICT` — implementation contradicts canonical architecture or prompt.

### Severity

- P0 security/data loss/blocker;
- P1 broken core behavior;
- P2 important gap;
- P3 polish/documentation.

## Stage passes

### Pass 1 — prompts and inventory

- enumerate all prompt files for stages 1–9;
- map aliases/versions and references;
- record prompt path, date/version, sections and expected acceptance;
- check that no prompt in `pompts_11/` was removed or overwritten.

### Pass 2 — domain and CRUD (stages 1–3)

- Project/Workspace/User/Task/Item/Document schemas;
- CRUD and optimistic locking;
- database tables and foreign keys;
- workspace_id propagation;
- manager/assignee assignment;
- object relationships and historical-data preservation.

### Pass 3 — presentation and planning (stages 4–5)

- dashboards/widgets/data provider contracts;
- calendar and derived events;
- timezone/UTC handling;
- finance widget permissions;
- frontend routes and empty/error/loading states.

### Pass 4 — data movement and query UX (stages 6–7)

- Excel/CSV upload, mapping, preview, confirm, rollback;
- templates and import history;
- export columns and finance masking;
- saved views, filters, sorting, search;
- import/export permission and workspace isolation.

### Pass 5 — event and automation system (stage 8)

- notification lifecycle/read-all/grouping;
- automation templates, CRUD, test/tick;
- event chain and run history;
- overdue scheduler and risk refresh;
- deduplication/idempotency and workspace isolation.

### Pass 6 — RBAC/security (stage 9)

- users/memberships/roles/permissions;
- Owner/Admin/Manager/Member/Viewer behavior;
- IDOR and workspace isolation;
- finance field/API/export/dashboard security;
- workspace switching and creation;
- manager/assignee selection;
- frontend permission awareness and tests;
- invitations, ownership transfer;
- Teams and `field_permissions` completeness;
- authentication status: `DEFERRED`, not a failure for current dev/demo scope.

### Pass 7 — runtime and deployment

- server service status and backup evidence;
- migrations applied to correct database;
- frontend build and static serving;
- backend regression and stage acceptance;
- Playwright console/page/network errors;
- stale duplicate data and environment drift.

### Pass 8 — Workspace OS integration review

Only after the factual audit:

- identify generic contracts in PM OS;
- compare B1/B2/B7/B9/B10 boundaries;
- separate platform primitives from PM OS-specific policy;
- assess workspace/RBAC/event/audit/memory/automation portability;
- create ADR and migration proposal only for proven reusable pieces;
- preserve PM OS as a backward-compatible consumer.

## Evidence matrix

Create `projects_17/pm_os/AUDIT_MATRIX.md`:

```text
stage | prompt_path | section | atomic_requirement |
implementation_paths | migration | test/evidence |
status | severity | gap | next_action | owner
```

## Findings report

Create `projects_17/pm_os/AUDIT_FINDINGS.md` grouped by:

1. P0/P1 security and data integrity;
2. P1 core functional gaps;
3. P2 missing features;
4. P3 polish/documentation;
5. deferred decisions;
6. architecture candidates for Workspace OS review.

## Execution order

1. inventory prompts;
2. audit stages 1–3;
3. audit stages 4–5;
4. audit stages 6–7;
5. audit stage 8;
6. audit stage 9;
7. live runtime verification;
8. produce matrix/findings;
9. update PM OS roadmap and lessons;
10. decide whether a Workspace OS integration ADR is warranted.

## Definition of done

- every prompt section has a row in the matrix;
- every `DONE` row has implementation and evidence;
- every `PARTIAL/MISSING` row has severity and next action;
- deferred authentication is explicitly separated from defects;
- no unreviewed PM OS runtime code is moved into platform core;
- report is readable by a future agent without chat history.
