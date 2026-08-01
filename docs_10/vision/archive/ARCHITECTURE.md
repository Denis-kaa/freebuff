# Architecture

> **Версия:** 1.0.0
> **Статус:** актуальная схема с интеграцией Lightpanda

---

## Общая схема

```mermaid
graph TB
    subgraph freebuff
        O[orchestrator.py***REMOVED***
        TR[scripts_01/tool_runtime.py***REMOVED***
        LW[src_06/workers/lightpanda_worker.py***REMOVED***
        MS[scripts_01/mcp_server.py***REMOVED***
        CM[scripts_01/context_manager.py***REMOVED***
    end

    subgraph proot[proot-distro Ubuntu***REMOVED***
        LP_BIN[/usr/local/bin/lightpanda***REMOVED***
    end

    subgraph Mobile
        FL[Flutter / Termux***REMOVED***
    end

    O --> TR
    TR --> LW
    MS --> LW
    LW --> |wrapper| LP_BIN
    FL --> O
    O --> CM
```

## Компоненты

| Компонент | Роль |
|-----------|------|
| `orchestrator.py` | Главный планировщик задач |
| `scripts_01/tool_runtime.py` | Реестр инструментов с единым интерфейсом |
| `src_06/workers/lightpanda_worker.py` | Воркер для веб-автоматизации через Lightpanda |
| `scripts_01/mcp_server.py` | MCP сервер, экспонирующий инструменты |
| `scripts_01/context_manager.py` | SQLite-хранилище сессий и сообщений |

## Lightpanda Worker

```
┌──────────────────┐
│ LightpandaWorker│
├──────────────────┤
│ execute_agent_task()
│ run_script()
│ dump_url()
│ serve_cdp()
│ stop_cdp()
└────────┬─────────┘
         │ subprocess
         ▼
   .tools/lightpanda  (wrapper)
         │
         ▼
   proot-distro login ubuntu
         │
         ▼
   /usr/local/bin/lightpanda
```

## Поток запроса

1. Пользователь или агент запрашивает веб-автоматизацию.
2. Orchestrator выбирает `lightpanda` через `ToolRegistry`.
3. `LightpandaWorker` формирует команду.
4. Wrapper `.tools/lightpanda` делегирует вызов в proot-distro Ubuntu.
5. Lightpanda выполняет действие и возвращает stdout/stderr.
6. Результат передаётся обратно через `LightpandaResult`.

## Автоматизация документирования

Правила документирования вынесены в `RULES.md` и контролируются автоматически:

- `scripts_01/buffy_autodoc.py` — сканирует `git diff` и выводит чек-лист документов, которые нужно обновить.
- `scripts_01/pre-commit` + `scripts_01/install_hooks.sh` — git pre-commit hook, который блокирует коммит, если для кода не обновлён `CHANGELOG.md`.
- Подробнее: [`RULES.md` — Авто-триггер документирования***REMOVED***(../../core/RULES.md).

## Слои изоляции

- **Termux** — основная среда выполнения freebuff.
- **proot-distro Ubuntu** — изолированный Linux с glibc для Lightpanda.
- **Worker** — Python-обёртка с таймаутами и обработкой ошибок.
- **Orchestrator** — не знает о glibc/proot; работает через единный API.
