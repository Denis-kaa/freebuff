# TASK: Phase 1 — Infrastructure Core (v5.0.0) + promt16.md

**Статус:** ✅ promt16.md Tasks 0-6 завершены, переход к Policy Engine
**Создана:** 2026-07-29 19:56 UTC
**Версия проекта:** v5.0.0
**Коммит:** da4b60c
**Обновлено:** 2026-07-29

---

## 🎯 Что сделано

### promt16.md — Полный аудит и реструктуризация ✅

| Задача | Содержание | Статус |
|--------|-----------|:------:|
| **Task 0** | VISION_3.0.md: три режима работы, gaps (ACP/Bridge/KeyPool), ARCHITECTURE_PRINCIPLES.md, COMPATIBILITY_MATRIX.md, RUNTIME_VALIDATION_FRAMEWORK.md | ✅ |
| **Task 1** | Реорганизация docs/: 45 файлов → 7 подпапок (core/vision/decisions/audits/plugin/projects_meta/ops), INDEX.md, все ссылки обновлены | ✅ |
| **Task 2** | Граница ядро↔плагин: импорты через __init__.py + try/except, INTEGRATION_CONTRACT.md, doctor.py, runtime/recipes/ | ✅ |
| **Task 2.3** | Marketplace-ready: runtime/providers/ YAML-манифесты, auto-discovery, 69 тестов | ✅ |
| **Task 3** | Унификация projects/: README.md + MANIFEST.md для всех 4 проектов | ✅ |
| **Task 4** | Чистка data/context.db: 91→45 сессий, .gitignore: *.pyc/*.pyo | ✅ |
| **Task 5** | Аудит scripts/: 4 мёртвых → archive/, ссылки обновлены | ✅ |
| **Task 6** | Full smoke-test: 1152 tests, 0 failures, граница CLEAN, CODE_QUALITY_STANDART интегрирован | ✅ |

### v4.5.0 — Scenario Engine + Telegram Bot ✅
- ScenarioEngine (YAML + markdown, 11 сценариев, 83 теста)
- TG Bot (/scenarios list/apply/search, inline keyboard, 44 теста)

### v4.6.0 — Bridge Layer (MCP ↔ ACP) ✅
- MCP Client (StdioMCPClient + HTTPMCPClient)
- ACP Protocol (AgentRegistry + ACPHandler, heartbeat)
- Bridge Layer (трансляция, 4 MCP инструмента, 60 тестов)

### v4.7.0 — Event Platform + Bootstrap Engine ✅
- EventStore (SQLite + FTS5) + EventReplay + Timeline + Audit + Pulse (61 тест)
- Bootstrap Engine (6 модулей, 3 MCP инструмента, 61 тест)

### v4.8.0 — Bootstrap MCP интеграция ✅
- 3 MCP инструмента (bootstrap_check/run/status), 12 тестов

### v4.9.0 — Runtime Abstraction Layer ✅
- RuntimeAdapter ABC + StdioMCPAdapter + HTTPMCPAdapter + AdapterRegistry
- RuntimeRegistry + RuntimeCapabilityRegistry
- FreebuffAdapter + ClaudeCodeAdapter
- 60 тестов

### v4.10.0 — MCP + RAL интеграция ✅
- 5 MCP инструментов (runtime_list/connect/disconnect/select/generate)
- 18 тестов

### v5.0.0 — promt16.md полный цикл ✅
- CHANGELOG.md v5.0.0, ROADMAP.md v3.0.0
- Коммит: da4b60c (256 files, +51753/−1116)

### Тест-статус
```
1152 passed, 1 skipped, 0 failures (305s)
```

---

## 📋 Следующие шаги (Phase 1 — приоритет)

### Шаг 1: Policy Engine 🔜
Пользовательские политики выбора Runtime по capability.
YAML-конфиг для маппинга capability → runtime.

### Шаг 2: Capability Registry (доработка) 🔜
Выбор capability вместо модели. Интеграция с Policy Engine.

### Шаг 3: Runtime Installer 🔜
Авто-установка freebuff, Claude Code, OpenClaw через Bootstrap Engine.
Интеграция `freebuff_plugin/runtime/` с `freebuff_plugin/bootstrap/installer.py`.

---

## 🔧 Ключевые файлы проекта

```
freebuff_plugin/
├── runtime/                    # Runtime Abstraction Layer
│   ├── __init__.py            # Типы
│   ├── adapter.py             # RuntimeAdapter ABC + Adapters
│   ├── registry.py            # RuntimeRegistry + CapabilityRegistry
│   └── adapters/              # Freebuff, Claude Code
├── bootstrap/                  # Bootstrap Engine
│   ├── engine.py, checker.py, installer.py, doctor.py, state.py
│   └── profiles.yaml
├── event/                      # Event Platform
│   ├── store.py, replay.py, timeline.py, audit.py, pulse.py
│   └── schema.sql
├── bridge_layer.py             # Bridge Layer (MCP ↔ ACP)
├── mcp_client.py               # MCP Client (stdio + HTTP)
├── acp_protocol.py             # ACP Protocol
├── scenario_engine.py          # Scenario Engine (11 сценариев)
├── tgbot.py                    # Telegram Bot
├── INTEGRATION_CONTRACT.md     # Контракт ядро↔плагин
runtime/
├── providers/                  # YAML-манифесты (freebuff, claude_code, openclaw)
├── plugins/                    # Плагин-система
├── recipes/                    # Freebuff/Claude Code recipes
└── MARKETPLACE.md              # Marketplace-архитектура
scripts/
├── mcp_server.py               # MCP Server (120 тестов)
├── doctor.py                   # CLI-диагностика
└── archive/                    # Архивные скрипты
    ├── import_qwen.py
    ├── import_sessions.py
    ├── phone_mcp_server.py
    └── dashboard_api.py
docs/
├── core/                       # Спецификации и архитектура
├── vision/                     # ROADMAP, VISION_2.0/3.0, PRODUCT_MANIFESTO
├── decisions/                  # ADR и DECISIONS
├── audits/                     # Аудиты
├── plugin/                     # FREEBUFF_PLUGIN_*
├── projects_meta/              # WORKERS, LIGHTPANDA, PROJECT_REGISTRY
├── ops/                        # TROUBLESHOOTING, TASK_TEMPLATE, AGENTS
└── INDEX.md                    # Навигационный индекс
tests/
├── test_runtime_abstraction.py # 69 тестов
└── test_mcp_server.py          # 120 тестов
```

## ▶️ Команда для продолжения

После перезапуска Termux:
```
cd /storage/emulated/0/PROJECTS/workstation/freebuff
freebuff
```

Сказать:
> "продолжай с Policy Engine — Шаг 1"
