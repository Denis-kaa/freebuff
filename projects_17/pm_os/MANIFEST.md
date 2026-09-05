# MANIFEST.md — Паспорт проекта `pm_os`

> **Slug:** `pm_os`
> **Тип:** прикладной продукт / кандидат на переносимый runtime-слой
> **Версия:** 0.9.0
> **Статус:** 🟡 development / Stage 9 implemented
> **Дата:** 2026-09-01
> **Runtime:** `/var/www/pm_os` на `whimco`

## Назначение

PM OS — workspace-centric операционная система для управления проектами, задачами, производством, документами, календарём, автоматизациями, уведомлениями и финансовыми данными.

## Архитектурная позиция

Этот каталог — **проект разработки PM OS в Workspace OS**, а не runtime-workspace PM OS. Runtime-workspace — это сущность внутри самого PM OS, где пользователи ведут рабочие проекты.

Рабочая модель:

```text
Workspace OS (платформа)
└── Project: PM OS (этот проект разработки)
    └── PM OS runtime
        └── Runtime Workspaces
            └── User Projects
```

## Обязательный будущий review

При интеграции PM OS с Workspace OS необходимо отдельно оценить, какие части PM OS могут стать платформенным ядром или переносимым runtime-слоем:

- workspace/tenant isolation;
- Project/Task/Resource contracts;
- RBAC и permission engine;
- event/audit chain;
- notifications/automation orchestration;
- project-centric memory и acceptance flow;
- dashboard/widget data contracts.

До завершения review PM OS остаётся отдельным прикладным проектом. Нельзя автоматически переносить runtime-код в `core_02/` или смешивать runtime workspace с платформенным Workspace.

## Scope

В scope входят PM OS backend, frontend, database migrations, acceptance, deployment и проектная память.

Вне текущего scope: полноценная production authentication (login/session/refresh/password reset), пока используется MVP identity-контракт `X-User-Id`.

## Индекс документов

- `README.md` — быстрый вход;
- `ROADMAP.md` — стадии и аудит прогресса;
- `STEPS.md` — текущие шаги и rationale;
- `LESSONS.md` — project-local lessons;
- `decisions/DECISIONS.md` — индекс решений;
- `decisions/ADR-001_workspace_boundary.md` — граница platform/runtime;
- `decisions/ADR-002_auth_deferred.md` — deferred authentication;
- `AUDIT_PLAN.md` — план аудита промтов и стадий 1–9;
- `RUNNABLE.md`, `CHECKLIST.md` — эксплуатационная готовность.
