@AGENTS.md

# CLAUDE.md — Claude Code адаптер для Freebuff Workspace

> **Роль:** инструмент-специфичный слой поверх канонического `AGENTS.md` (import выше).
> **Почему import, не симлинк:** лимит Claude Code ~40k символов; import работает на Windows без прав администратора (см. `docs_10/canonical/architecture.md` §3 и SESSION_UNDERSTANDING §5).

## Claude-специфичные дополнения

1. Канонические правила платформы — см. `AGENTS.md` (import выше). Не дублировать здесь.
2. Полный контекст среды: `docs_10/core/CORE_PROMPT.md` (идентичность, обязанности, ограничения, поведение) + `BUFFY.md` (рабочий манифест окружения).
3. Перед изменениями — перечитать `docs_10/core/CODE_QUALITY_STANDARD.md` (обязательно).

## Quick protocol

1. `AGENTS.md` (правила, import выше) → `docs_10/core/CORE_PROMPT.md` → `BUFFY.md`.
2. `TASK.md` (активные задачи) → `CHANGELOG.md` (последние релизы).
3. `python freebuff_cli.py status` — состояние системы.
4. После изменений: `python -m pytest tests_09/ -q` и `python -m mypy scripts_01/ core_02/ --ignore-missing-imports`.
