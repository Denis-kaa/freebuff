# STEPS.md — Текущие шаги PM OS

## Operating rule

Каждую следующую задачу вести через этот проект: зафиксировать цель, затронутые контракты, изменения, acceptance и lesson.

## Current milestone — Stage 9 follow-up

1. Реализовать Teams API/UI.
2. Подключить `field_permissions` к точечному finance masking.
3. Проверить object-level access boundary.
4. Расширить frontend permission tests.
5. Зафиксировать результаты acceptance.

## Decisions / rationale

- PM OS остаётся отдельным development project, а не новым runtime-workspace внутри PM OS.
- Runtime workspace и platform Workspace OS — разные state/lifecycle/namespace boundaries.
- Teams и RBAC допустимо развивать внутри PM OS: они не мешают будущему переносу, если контракты остаются явными и domain policy не смешивается с platform primitives.
- Authentication отложена: MVP использует `X-User-Id`; production auth будет отдельным integration layer.
- Все серверные изменения выполняются на `whimco`; локальная frontend-сборка не является обязательным gate.

## Acceptance protocol

- backend syntax/tests on server;
- stage acceptance script;
- frontend `npm test`;
- frontend build;
- Playwright smoke with console/page errors;
- update `MANIFEST.md`, `ROADMAP.md`, `LESSONS.md`.
