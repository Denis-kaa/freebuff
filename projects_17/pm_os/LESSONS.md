# LESSONS.md — PM OS

Формат: CON / CAN / ANTI / PB.

## CON-001 — Runtime workspace и platform project нельзя смешивать

- **Контекст:** PM OS разрабатывается внутри Workspace OS, а сам PM OS содержит runtime-workspaces.
- **Вывод:** development project, platform Workspace и runtime workspace имеют разные lifecycle/namespace/owner. Связь делать контрактом и review, не общим state.

## CON-002 — Frontend permission awareness не заменяет backend authorization

- **Контекст:** viewer UI скрывает действия, но backend всё равно проверяет permission.
- **Вывод:** frontend — UX-слой; backend — security boundary.

## PB-001 — Белый экран из-за монтирования nullable drawer

- **Контекст:** ProjectDetail монтировался с `project=null` и обращался к `project.id`.
- **Исправление:** nullable guard в компоненте + Playwright smoke.
- **Вывод:** все опциональные overlay/drawer компоненты должны иметь null-safe boundary.

## CAN-001 — Teams/RBAC могут стать переносимыми platform primitives

- **Статус:** гипотеза до architecture review.
- **Условие:** выделить generic contracts и не переносить PM OS-specific domain policy.

## CON-003 — Acceptance требует разделения evidence и статуса реализации

- **Контекст:** stage acceptance и регрессия зелёные, но подробные prompt-пункты (Google OAuth, background jobs, Teams API, field-level enforcement) ещё не полностью закрыты.
- **Вывод:** зелёный acceptance подтверждает конкретные сценарии, но не автоматически делает весь промт DONE; аудит обязан классифицировать PARTIAL/MISSING отдельно.

## ANTI-001 — Не считать модель готовой функцией

- **Контекст:** `Team`, `TeamMember`, `FieldPermission` существуют как ORM-модели.
- **Вывод:** без API, UI, enforcement и теста это архитектурный задел, а не завершённая feature.
