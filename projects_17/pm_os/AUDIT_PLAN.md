# AUDIT_PLAN.md — Аудит этапов и промтов 1–9

## Цель

Проверить не только наличие кода, но и соответствие каждого промта фактически реализованным контрактам, acceptance-сценариям и runtime-поведению.

## Правило аудита

Статус «сделано» ставится только при наличии:

1. требования в исходном промте;
2. реализации в backend/frontend/database;
3. теста или live verification;
4. отсутствия известного регресса;
5. записи evidence (файл, endpoint, test output).

Статусы: `DONE`, `PARTIAL`, `MISSING`, `BLOCKED`, `DEFERRED`, `CONFLICT`.

## Фазы

### A. Инвентаризация

- собрать список исходных файлов промтов и их версий;
- найти все ссылки на промты в `TASK.md`, `CHANGELOG.md`, project docs;
- сопоставить промт → stage → файлы реализации → acceptance;
- не удалять и не перезаписывать промты.

### B. Контрактный аудит по стадиям

| Stage | Основные области проверки |
|---|---|
| 1 | core project model, CRUD, database, import foundation |
| 2 | configurable columns, filters, views, table UX |
| 3 | items, production, tasks, documents, assignments |
| 4 | dashboards, widgets, data providers, finance visibility |
| 5 | calendar, derived events, timezone/date behavior |
| 6 | import/export, templates, mappings, dry-run, rollback, permissions |
| 7 | search, saved views, query builder, workspace filtering |
| 8 | notifications, automation, event chain, risks, scheduler |
| 9 | users, membership, roles, permissions, IDOR, finance security, workspace switching, frontend awareness |

Для каждой области фиксировать: requirement IDs/§, implementation paths, tests, gaps, severity.

### C. Runtime verification

- backend compile/import;
- database schema/migration check;
- API smoke по основным endpoint’ам;
- role matrix: Owner/Admin/Manager/Member/Viewer;
- workspace isolation and IDOR;
- frontend build;
- frontend unit tests;
- Playwright console/page/network errors;
- scheduler/worker health.

### D. Документальный аудит

- проверить MANIFEST/ROADMAP/STEPS/LESSONS/ADR;
- проверить, что каждый реализованный stage имеет evidence;
- проверить, что deferred/auth assumptions явно записаны;
- проверить связи project memory ↔ platform canonical docs;
- проверить, что PM OS не смешан с Workspace OS core.

### E. Итоговая матрица

Создать `AUDIT_MATRIX.md` с колонками:

```text
stage | prompt | section | requirement | implementation | test/evidence |
status | severity | gap | next action | owner/file
```

Severity:

- P0 — security/data loss/blocker;
- P1 — broken core requirement;
- P2 — important missing behavior;
- P3 — polish/documentation.

## Порядок выполнения

1. Stage 1–3 (domain and CRUD).
2. Stage 4–5 (dashboard/calendar).
3. Stage 6–7 (import/export/views/search).
4. Stage 8 (automation/notifications/risk).
5. Stage 9 (RBAC/security/frontend).
6. Cross-stage regression and boundary review.
7. Final report: done/partial/missing/deferred + prioritized backlog.

## Expected outputs

- `AUDIT_MATRIX.md`;
- `AUDIT_FINDINGS.md`;
- updated `ROADMAP.md`;
- project-local lessons for every confirmed incident;
- platform ADR only for findings proven reusable beyond PM OS.

## Current known exclusions

- Real authentication: `DEFERRED`, not a failure for current dev/demo scope.
- Teams API/UI and field_permissions enforcement: `PARTIAL`.
- Object-level access: `PARTIAL`.
- Unauthenticated invitation accept: `DEFERRED` until real authentication.
