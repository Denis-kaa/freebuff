# ADR-005: ContextManager Bridge for termux-ai-agent

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** Интеграция freebuff агента с freebuff ContextManager (SPEC.md, v4.0)

## Проблема

`termux-ai-agent` не сохранял историю диалогов между запусками. После OOM-kill или перезапуска TUI контекст терялся.

## Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A. JSON-лог в termux-ai-agent** | Просто | Нет суммаризации, чекпоинтов, RAG |
| **B. Своя SQLite в termux-ai-agent** | Контроль | Дублирование ContextManager |
| **C. Reuse freebuff ContextManager** | Единый source of truth, авто-конспекты, checkpoints | Требует sys.path манипуляций |

## Решение

Выбран **вариант C**: `scripts/agent_context_bridge.py` как singleton-мост. Он:

- восстанавливает/создаёт сессию при первом вызове;
- логирует `user`, `assistant`, `system` сообщения;
- делает авточекпоинт каждые 10 сообщений;
- сохраняет конспект через `auto_conspect()`.

## Ключевые решения

1. **Singleton** — несколько вызовов `run()` делят одну сессию.
2. **Graceful degradation** — ошибки freebuff не ломают `run()`.
3. **Lazy import** — `get_context_bridge()` создаёт bridge только при первом использовании.
4. **Compact response** — `log_assistant()` хранит только `status`, `tool`, `error`, `metrics`, не весь JSON.

## Документация

- [scripts/agent_context_bridge.py***REMOVED***(../../../scripts/agent_context_bridge.py)
- [tests/test_agent_context_bridge.py***REMOVED***(../../../tests/test_agent_context_bridge.py)
- [TASK.md***REMOVED***(../../../TASK.md)
