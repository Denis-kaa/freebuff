# TASK: Phase 1 — Infrastructure Core (v5.0)

**Статус:** В РАБОТЕ
**Создана:** 2026-07-29 19:56 UTC
**Версия проекта:** v4.9.0
**Обновлено:** 2026-07-29

---

## 🎯 Что сделано (в этой сессии)

### v4.8.0 — Bootstrap MCP интеграция ✅
- **3 MCP инструмента** в `scripts/mcp_server.py`:
  - `bootstrap_check` — проверка окружения
  - `bootstrap_run` — полный bootstrap cycle
  - `bootstrap_status` — статус bootstrap
- **12 тестов** `tests/test_mcp_server.py::TestBootstrapTools` — все пройдены
- EventBus публикация: `bootstrap.checked`, `bootstrap.ran`

### v4.9.0 — Runtime Abstraction Layer ✅
- `freebuff_plugin/runtime/__init__.py` — типы и data classes
- `freebuff_plugin/runtime/adapter.py` — RuntimeAdapter ABC + StdioMCPAdapter + HTTPMCPAdapter + AdapterRegistry
- `freebuff_plugin/runtime/registry.py` — RuntimeRegistry + RuntimeCapabilityRegistry
- `freebuff_plugin/runtime/adapters/freebuff.py` — FreebuffAdapter (поиск бинарника, MCP STDIO)
- `freebuff_plugin/runtime/adapters/claude.py` — ClaudeCodeAdapter (поиск npm/which, MCP STDIO)
- **60 тестов** `tests/test_runtime_abstraction.py` — все пройдены
- **1123 общих теста** — `0 failures`

### Тест-статус на момент чекпоинта
```
1123 passed, 1 skipped, 0 failures (254s)
```

---

## 📋 Следующие шаги (Phase 1 — приоритет)

### Шаг 1: MCP + RAL интеграция ✅
Добавлены 5 MCP инструментов в `scripts/mcp_server.py`:
- `runtime_list` — список зарегистрированных Runtime
- `runtime_connect` — подключиться к Runtime
- `runtime_disconnect` — отключиться от Runtime
- `runtime_select` — выбрать активный Runtime
- `runtime_generate` — генерация через выбранный Runtime

**Результат:** 120 тестов MCP Server — 0 failures.

### Шаг 2: Runtime Installer 🔜
Авто-установка freebuff, Claude Code, OpenClaw через Bootstrap Engine.
Интеграция `freebuff_plugin/runtime/` с `freebuff_plugin/bootstrap/installer.py`.

### Шаг 3: Policy Engine (начало) 🔜
Пользовательские политики выбора Runtime по capability.
YAML-конфиг для маппинга capability → runtime.

### Шаг 4: Capability Registry 🔜
Выбор capability вместо модели. Integration с Policy Engine.

---

## 🔧 Ключевые файлы проекта

```
freebuff_plugin/
├── runtime/                    # Runtime Abstraction Layer (НОВЫЙ)
│   ├── __init__.py            # Типы: RuntimeDefinition, RuntimeResult, RuntimeCapability...
│   ├── adapter.py             # RuntimeAdapter ABC + StdioMCPAdapter + HTTPMCPAdapter
│   ├── registry.py            # RuntimeRegistry + RuntimeCapabilityRegistry
│   └── adapters/
│       ├── __init__.py
│       ├── freebuff.py        # FreebuffAdapter
│       └── claude.py          # ClaudeCodeAdapter
├── bootstrap/                  # Bootstrap Engine (готово)
│   ├── engine.py, checker.py, installer.py, doctor.py, state.py
│   └── profiles.yaml
├── event/                      # Event Platform (готово)
├── bridge_layer.py             # Bridge Layer (готово)
├── mcp_client.py               # MCP Client (готово)
├── acp_protocol.py             # ACP Protocol (готово)
├── scenario_engine.py          # Scenario Engine (готово)
├── tgbot.py                    # Telegram Bot (готово)
scripts/
└── mcp_server.py               # MCP Server (+ bootstrap инструменты готовы)
tests/
├── test_runtime_abstraction.py # 60 тестов (НОВЫЙ)
└── test_mcp_server.py          # 101 тест (+12 bootstrap тестов)
```

## ▶️ Команда для продолжения

После перезапуска Termux:
```
cd /storage/emulated/0/PROJECTS/workstation/freebuff
freebuff
```

Сказать:
> "продолжай"
