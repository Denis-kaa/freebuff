# PM OS

PM OS — прикладной product/runtime project, который ведётся как контейнер контекста Workspace OS.

## Вход

1. Прочитать `MANIFEST.md`.
2. Проверить `ROADMAP.md`.
3. Для текущей задачи открыть `STEPS.md`.
4. Архитектурные решения искать в `decisions/`.
5. Перед реализацией сверить `AUDIT_PLAN.md`.

## Runtime

- Server: `whimco`
- Path: `/var/www/pm_os`
- Backend: FastAPI, PostgreSQL, SQLAlchemy
- Frontend: React, Vite
- Current stage: 9 — RBAC foundation

## Boundary

PM OS development project не равен runtime workspace внутри PM OS. Его runtime-workspaces содержат пользовательские проекты. Возможный перенос общих механизмов (workspace, RBAC, events, memory, automation) в ядро Workspace OS будет решаться только после отдельного architecture review.

## Current status

- Stages 1–8: implemented and accepted;
- Stage 9 RBAC foundation: implemented;
- frontend permission tests: 11/11;
- backend regression: 118 passed;
- stage9 acceptance: 22/22;
- Playwright smoke: no console/page errors.
