# ROADMAP.md — PM OS

## Stage status

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| 1 | Core project data and import foundation | 🟢 | server runtime + regression |
| 2 | Project views and configurable columns | 🟢 | frontend/backend runtime |
| 3 | Items, production, tasks, documents | 🟢 | backend tests |
| 4 | Dashboard engine and widgets | 🟢 | widget data API |
| 5 | Calendar and events | 🟢 | calendar/event checks |
| 6 | Import/export | 🟡 | Excel/CSV verified on server; Google Sheets/background jobs remain |
| 7 | Filters, views and search | 🟡 | Stage 7 backend 6/6; browser view/search flow verified; grouping/virtualization/sharing remain |
| 8 | Notifications, automations and risk | 🟢 | stage8 acceptance: 10/10 |
| 9 | Users, roles, permissions, workspace access | 🟡 | audit: PARTIAL; stage9 acceptance 22/22, UI 8/8, frontend 11/11; follow-up items remain |
| 10 | Teams, field permissions, object-level access | 🟡 | Teams CRUD/member assignment deployed and backend tests 3/3; field permissions/object access remain; dedicated Teams browser acceptance pending |
| 11 | Auth Provider/session integration | ⚪ | deliberately deferred |
| 12 | Workspace OS integration review | ⚪ | required after factual audit; candidate primitives documented |

## Stage 9 follow-up

- Teams API/UI — basic CRUD and member assignment deployed; focused backend tests 3/3; add dedicated browser acceptance;
- field_permissions enforcement;
- object-level access;
- invitation accept after real authentication;
- complete frontend permission coverage for dashboard/export/import actions.

## Architecture review gate

Before extracting any PM OS component into Workspace OS core, perform a separate review:

1. identify generic contracts;
2. compare lifecycle and namespace boundaries;
3. verify B1/B2/B7/B9/B10 boundaries;
4. separate platform primitives from PM OS domain policy;
5. create platform ADR and migration plan;
6. keep PM OS backward compatible as an external consumer.
