# DECISIONS.md — Индекс решений проекта Model Dispatcher

> **Scope:** PROJECT-LOCAL — решения, принадлежащие проекту.
> **Конвенция:** `docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md` §4.

| # | Решение | Статус | Дата | Related |
|---|---------|--------|------|---------|
| ADR-001 | Имитация человека через tmux + стартовый экран (вместо HTTP-провайдеров GLM/MiniMax) | ✅ Accepted | 2026-08-12 | 081_19_model_dispatcher, CON-2 |
| ADR-002 | Таймер сессии по умолчанию 1 час + сохранение контекста (timeout без kill, `--continue`) | ✅ Accepted | 2026-08-12 | 081_19_model_dispatcher, CON-3 |
| ADR-003 | Самодостаточная очередь (md_queue, совместимый формат) без импорта платформенных скриптов | ✅ Accepted | 2026-08-12 | PROJECT_RULES §7, ANTI-1 |

## Как добавлять ADR

1. Копия шаблона (Context / Decision / Альтернативы / Consequences).
2. Файл: `ADR-NNN_<slug>.md`.
3. Строка в эту таблицу.
4. Cross-link в `MANIFEST.md`.
