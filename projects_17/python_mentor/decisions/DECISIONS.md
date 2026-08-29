# DECISIONS.md — Реестр архитектурных решений проекта python_mentor

> Формат: MADR (Context / Options / Decision / Rationale / Consequences).
> Легенда статусов: 🟢 Accepted · 🟡 Proposed/Draft · ⚪ Superseded · 🔴 Rejected.

| ID | Решение | Дата | Статус |
|----|---------|------|--------|
| ADR-001 | Детерминированное ядро первично; LLM — только внешний опциональный слой | 2026-08-23 | 🟢 Accepted |
| ADR-002 | Фазовые гейты B+C → N, запрет перескоков и «реализации на лету» | 2026-08-23 | 🟢 Accepted |
| ADR-003 | Sandbox: два tier'а с единым интерфейсом; MVP — subprocess+limits | 2026-08-23 | 🟢 Accepted |
| ADR-004 | License gate: approved/pending/rejected; unknown никогда → live | 2026-08-23 | 🟢 Accepted |
| ADR-005 | RLIMIT_AS в Termux/proot; граница MVP execution и hardened sandbox | 2026-08-24 | 🟢 Accepted |
| ADR-006 | Локализация learner-контента и контролируемые LLM-assisted обновления | 2026-08-24 | 🟢 Accepted |

## Правила ведения

- Новое решение → новый файл `ADR-NNN_*.md` + строка здесь + ссылка в MANIFEST (§12) если значимо.
- Спор при реализации → решать в ADR, не молча.
- Решения, принятые в канонах (blueprint v0.1 §0/§2/§9) формализованы как ADR-001…006.

## Связь с канонами платформы

- Project-local ADR — внутри проекта; тиражируемые решения дополнительно в `docs_10/engineering-memory/decisions/` (правило «в одну сторону», PROJECT_RULES §2.3).