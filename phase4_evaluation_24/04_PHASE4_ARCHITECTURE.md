# 04_PHASE4_ARCHITECTURE — фактическая архитектура Phase 4

> Протокол pomt83 §4: восстановить фактический смысл Phase 4 из кода, а не из старых доков.

## 4.1 Фактический смысл Phase 4

**Phase 4 = интерфейсный/интеграционный слой платформы**, закрыт на **v5.20.0**.
Состав (по факту кода, не по заголовкам доков):

1. **Event Bus** — событийная шина с wildcard-подпиской (`task.*`, `*`).
2. **Plugin API** — контракт плагинов + `PluginRegistry`.
3. **MCP Server** — JSON-RPC 2.0 (StdIO + Streamable HTTP), lazy-loaded движки.
4. **Telegram Bot** — внешний интерфейс (`/task`, `/queue`, onboarding).
5. **Scenario Engine** — маркетплейс сценариев (YAML front-matter + manifest).
6. **Плагины** — `tg_messenger`, `system_monitor`, `knowledge_sync` (v5.20.0).

## 4.2 Ключевые компоненты и точки привязки

| Компонент | Классы/функции | Файл | Entry point |
|---|---|---|---|
| Plugin Registry | `PluginRegistry` | `scripts_01/plugin_api.py` | `python -m scripts_01.plugin_api` |
| Event Bus | `EventBus`, `get_default_event_bus` | `scripts_01/event_bus.py` | `python -m scripts_01.event_bus` |
| MCP Server | `BuffyMcpServer`, `McpSessionManager`, `McpTool` | `scripts_01/mcp_server.py` | `python -m scripts_01.mcp_server` |
| MCP FastAPI | `McpAsyncSession`, `McpAsyncSessionManager` | `scripts_01/mcp_fastapi.py` | `python -m scripts_01.mcp_fastapi` |
| Telegram Bot | `TelegramFreebuffBot` | `scripts_01/telegram_bot.py` | `python -m scripts_01.telegram_bot` |
| Scenario Engine | `Scenario`, `ScenarioEngine` | `freebuff_plugin_03/scenario_engine.py` | auto-load `.md` from `scenarios/` |
| Scenario Registry | `ScenarioRegistry` | `core_02/scenario_registry.py` | `python -m core_02.scenario_registry` |
| Event Subscribers | `auto_index_subscriber` и др. | `scripts_01/event_subscribers.py` | register via `register_all()` |

## 4.3 Ключевые события (event vocabulary)

`system.*`, `task.*`, `step.*`, `memory.*`, `knowledge.*`, `context.*`, `agent.*`,
`checkpoint.*`, `mcp.*`, `plugin.{enabled,disabled***REMOVED***`, `event.{search,timeline,replay,audit,pulse***REMOVED***`,
`presence.*`, `collab.*`, `distributed.*`, `pulse.*`.

## 4.4 Контракты (существующие, НЕ новые)

Phase 4 закрыта → новых контрактов не требуется. Действующие контракты —
`docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` (14 контрактов × 14 полей).

## 4.5 B-границы (AGENTS.md §4)

- **B1 (Workspace↔Project)** — через MCP tools + `WorkspaceRegistry`, не в обход.
- **B2 (Project↔Forge)** — `ForgeFacade.initiate_forge()` единственный sanctioned мост.
- **B10 (State↔Mode)** — multi-level memory ↔ mode-tiers (working=tasks, archive=cold).

## 4.6 Что Phase 4 НЕ должна переписывать (REUSE-вердикт)

Существующие и НЕ переписанные механизмы (промт §5/§9/§11):
MemoryEngine, KnowledgeEngine, GraphIndex, EventBus, TaskManager, PromptDispatcher,
ScenarioRegistry, FactoryRegistry, ForgeFacade, ForgePipeline, ForgePassport,
MCP, CLI, API — все переиспользованы, параллельной архитектуры нет.
