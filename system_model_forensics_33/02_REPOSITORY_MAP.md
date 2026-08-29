# 02_REPOSITORY_MAP.md — Карта компонентов

> **Статус:** FORENSIC FACT (по read_subtree + read_files, не по документации)

---

## Каталоги → слой системы

| Каталог | Роль | Слой системы | Status |
|---------|------|--------------|--------|
| `core_02/` | Каноническое ядро (Workspace/Project/Scenario/Factory/Forge/Router/RoleExecutor/Boundaries) | PLATFORM CORE | CONFIRMED |
| `scripts_01/` | Entrypoints + Intelligence + tools + runtime (CLI, HTTP, TG, MCP) | PLATFORM ENTRY/INTELLIGENCE | CONFIRMED |
| `runtime_05/` | Декларативные манифесты: factories/, scenarios/, recipes/, providers/, plugins/ | PLATFORM CONFIG (declarative) | CONFIRMED |
| `plugins_04/` | Плагины (hello_world, tg_messenger, system_monitor, knowledge_sync) — манифесты | PLATFORM PLUGINS | PARTIAL (seed) |
| `services_08/` | `system/monitor.py` — сервисный монитор | PLATFORM SERVICES | PARTIAL (seed) |
| `src_06/` | `workers/lightpanda_worker.py` — headless-браузер воркер | PLATFORM WORKERS | PARTIAL (seed) |
| `cli_07/` | `__init__.py` — пусто | PLATFORM CLI | ABSENT (stub) |
| `freebuff_plugin_03/` | Плагин Freebuff: API/MCP/TG/bridge/runtime/acp — рантайм-слой | PLATFORM RUNTIME (plugin) | CONFIRMED |
| `context_12/` | events_db (EventBus-хранилище) | PLATFORM STORAGE | CONFIRMED |
| `data_13/` | YAML/SQLite: whims/opportunities/forge_registry/context.db | PLATFORM STORAGE | CONFIRMED |
| `projects_17/` | Пользовательские проекты (diet_platform, tg_terminal_messenger, …) | PROJECT LAYER | CONFIRMED |
| `tests_09/` | Тесты платформы | PLATFORM TESTS | CONFIRMED |
| `pompts_11/` | Промты-контракты (NNN_TT_name.md) | PLATFORM PROMPTS | CONFIRMED |
| `docs_10/` | Документация (core/engineering-memory/decisions/vision) | PLATFORM DOCS | CONFIRMED |
| `phase*_evaluation_*` (24–31) | Исторические forensic/evaluation пакеты | LEGACY (аудит-след) | CONFIRMED legacy |
| `architecture_forensics_v2/`, `repository_organization_forensics_32/` | Recent forensic пакеты (promt103–105) | EVALUATION PACKAGES | CONFIRMED |
| `screenshots_16/`, `logs_14/`, `sessions_15/`, `books_out_23/`, `trash_21/`, `infa_20/`, `frontend_18/` | Артефакты/логи/материалы | LEGACY / ARTIFACTS | CONFIRMED |
| `buffy-playground_19/`, `prototype_22/` | Frontend-прототипы | EXPERIMENT | CONFIRMED |
| `freebuff_plugin/` (без NN) | Старый плагин | LEGACY | CONFIRMED |

## Компоненты core_02 (платформенное ядро)

| Модуль | Символ | Роль | Layer |
|--------|--------|------|-------|
| `workspace.py` | `Workspace`, `Project` | L-1/L-2 контейнеры | CORE |
| `scenario.py` | `Scenario` (ABC), `Role`, `ScenarioManifest` | корпус ролей | CORE |
| `scenario_registry.py` | `ScenarioRegistry` | auto-discovery сценариев | CORE |
| `factory_registry.py` | `FactoryRegistry` | auto-discovery фабрик/кузен | CORE |
| `factory_base.py` | `BaseFactory` | базовый адаптер Factory (ADR-013) | CORE |
| `factory_passport.py` | `FactoryPassport` | паспорт фабрики | CORE |
| `forge_passport.py` | `ForgePassport` | паспорт кузни | CORE |
| `forge_facade.py` | `ForgeFacade`, `ChainRun`, `ChainStage`, `RoleArtifactValidator` | chain-runner (14 ролей) | CORE |
| `forge_pipeline.py` | `ForgePipeline`, `PipelineRun` | CI FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT | CORE |
| `forge_registry.py` | `ForgeRegistry`, `ForgeStatus` | реестр статусов (B10/R-127) | CORE |
| `role_executor.py` | `RoleExecutorRegistry`, `BaseRoleExecutor`, `LisaExecutor`, `LlmRoleExecutor` | автоисполнение LIGHT-ролей (ADR-016) | CORE |
| `router.py` | `SmartRouter`, `ModelCatalog` | capability-роутинг моделей | CORE |
| `blueprint_v3.py` | `BlueprintCorpus` | блюпринты ролей + KNOWN_CAPABILITIES | CORE |
| `boundaries_v17.py` | `BOUNDARIES_V17`, `BState` | B1–B14 границы | CORE |
| `missing_registry.py` | `MissingRegistry` | реестр недостающих элементов (REGISTER-FIRST) | CORE |
| `memory_store.py` | `MemoryStore` | SQLite Knowledge Objects | MEMORY |
| `learning_loop.py` | `LearningLoop` | обратная связь | MEMORY |
| `semantic_layer.py` | — | семантический слой | KNOWLEDGE |
| `wizard_lib.py`, `wizard.py` | — | мастер подбора ролей | AGENT |
| `workspace_registry.py` | `WorkspaceRegistry` | B1 (Workspace↔Project) | CORE |
| `telegram_contract.py`, `_tg_client_v2.py` | — | TG-транспорт | INTERFACE |
| `remote_sync.py` | — | удалённая синхронизация | INTERFACE |

## Компоненты scripts_01 (entrypoints + intelligence + tools)

| Модуль | Роль |
|--------|------|
| `forge.py` | CLI: forge/check/status/register/report/step/chain |
| `forge_api.py`, `forge_interactive_api.py`, `mcp_fastapi.py`, `mcp_server.py` | HTTP/MCP интерфейсы |
| `telegram_bot.py`, `tgbot_base.py` | TG-бот |
| `whim_capture.py` | WHIM intake |
| `opportunity_engine.py` | OPPORTUNITY lifecycle |
| `scenario_intelligence.py` | Scenario decision-layer |
| `orchestrator.py` | FSM/DAG (Goal→Plan→Execute→Validate) |
| `tool_runtime.py` | ToolRegistry (5 инструментов) |
| `model_gateway.py` | LLM gateway |
| `context_manager.py`, `memory_engine.py`, `knowledge_engine.py`, `rag_engine.py`, `graph_index.py` | контекст/память/знания |
| `roles.py`, `presence.py`, `collaboration.py`, `distributed_agents.py` | агентский/коллаборационный слой |
| `content_factory.py`, `research_factory.py`, `test_factory.py` | Factory-адаптеры (наследники BaseFactory) |
| `consistency_check.py`, `drift_check.py` | инструменты самопроверки |
| `phone_control_mcp.py` | MCP-обёртка phone-control |

## Platform vs Project boundary

- **Platform** = `core_02/`, `scripts_01/` (platform-часть), `runtime_05/`, `freebuff_plugin_03/`, `plugins_04/`, `services_08/`, `src_06/`, `context_12/`, `data_13/` (platform-данные).
- **Project** = `projects_17/<slug>/` — пользовательские проекты, изолированы файлово.
- **Нарушение изоляции:** `core_02/workspace.py::Project` — проект-контейнер читает только свой `project.yaml`; но Knowledge/Memory **глобальны** (`data_13/context.db`), а `project→platform` импорты встречаются (проекты импортируют `scripts_01/*`). Логической изоляции нет (см. 08, promt105 R-вывод).
