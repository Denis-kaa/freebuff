# 12_FILE_MANIFEST — манифест пакета

> Протокол pomt83 §18: «relevant source files + relevant tests + relevant documentation,
> только те, которые необходимы независимому аудитору».

## Файлы Evaluation Package (`phase4_evaluation_24/`)

| Файл | Роль |
|---|---|
| `01_EXECUTIVE_SUMMARY.md` | Executive summary |
| `02_FORENSICS_REALITY_MAP.md` | Forensic-карта секций A–N (READY) |
| `03_DOCUMENTATION_CODE_TRACEABILITY.md` | Док ↔ код traceability |
| `04_PHASE4_ARCHITECTURE.md` | Фактическая архитектура Phase 4 |
| `05_PHASE4_IMPLEMENTATION_PLAN.md` | Gap-анализ + vertical slices |
| `06_EVIDENCE_LEDGER.md` | CLAIM→EVIDENCE→TEST ledger |
| `07_CHANGELOG.md` | Изменения аудита |
| `08_TEST_REPORT.md` | Тест-отчёт |
| `09_RUNTIME_VALIDATION.md` | Runtime-валидация (VSLICE-1..5) |
| `10_OPEN_ISSUES.md` | Открытые пункты + риски |
| `11_DECISIONS.md` | Архитектурные решения |
| `12_FILE_MANIFEST.md` | Этот файл |
| `13_SELF_AUDIT.md` | §22 чек-лист самоаудита (16/16 `[x***REMOVED***`) — добавлен 2026-08-16 |

## Сопутствующие артефакты

| Файл | Роль |
|---|---|
| `runtime_05/anchors_resolver_report.json` | Резолвер анкоров (valid JSON, exit 0) |
| `pompts_11/083_19_pomt83_protocols.md` | Сам промт (источник требований) |

## Ключевые source-файлы (для аудитора)

| Файл | Компонент |
|---|---|
| `scripts_01/plugin_api.py` | Plugin Registry |
| `scripts_01/event_bus.py` | Event Bus |
| `scripts_01/event_subscribers.py` | Subscribers |
| `scripts_01/mcp_server.py` | MCP Server |
| `scripts_01/mcp_fastapi.py` | MCP FastAPI |
| `scripts_01/telegram_bot.py` | Telegram Bot |
| `scripts_01/memory_engine.py` | Memory Engine |
| `scripts_01/knowledge_engine.py` | Knowledge Engine |
| `scripts_01/distributed_agents.py` | Distributed Agents |
| `freebuff_plugin_03/scenario_engine.py` | Scenario Engine |
| `freebuff_plugin_03/bootstrap/engine.py` | Bootstrap Engine |
| `core_02/scenario_registry.py` | Scenario Registry |
| `core_02/factory_registry.py` | Factory Registry |
| `core_02/forge_facade.py` | Forge Facade |
| `core_02/forge_pipeline.py` | Forge Pipeline |
| `core_02/forge_passport.py` | Forge Passport |
| `core_02/anchors_resolver.py` | Anchor Resolver |
| `core_02/workspace.py` + `workspace_registry.py` | Project/Workspace model |
| `scripts_01/forge.py` | Forge CLI |

## Ключевые тесты

| Файл | Компонент |
|---|---|
| `tests_09/test_plugin_api.py`, `test_event_bus.py`, `test_event_subscribers.py` | Phase 4 core |
| `tests_09/test_mcp_server.py`, `test_mcp_fastapi.py`, `test_telegram_bot.py` | интерфейсы |
| `tests_09/test_scenario_engine.py`, `test_scenario_registry.py` | scenarios |
| `tests_09/test_factory_registry.py`, `test_forge_facade.py`, `test_forge_pipeline.py`, `test_forge_passport.py` | forge |
| `tests_09/test_memory_engine.py`, `test_knowledge_engine.py` | memory |
| `tests_09/test_forge_chain_real_integration.py` | vertical slice |
| `tests_09/test_anchors_resolver.py`, `test_consistency_check.py`, `test_prompts_naming.py` | мета |

## Ключевая документация

| Файл | Роль |
|---|---|
| `AGENTS.md` | Канонические правила |
| `BUFFY.md` | Манифест среды |
| `docs_10/core/CORE_PROMPT.md` | Core prompt |
| `docs_10/engineering-memory/PLATFORM_CODE_MAP_V1.md` | Artifact A |
| `docs_10/engineering-memory/DOCUMENTATION_CODE_MAP_V1.md` | Artifact B |
| `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | Artifact C |
| `docs_10/engineering-memory/TRACEABILITY_GRAPH_V1.md` | Artifact E |

## Исключено из архива (§20/§21)

`.git`, `venv`, `__pycache__`, `node_modules`, datasets, секреты, API keys, tokens,
credentials, runtime caches, build artifacts. Secret-scan перед упаковкой — см. `SECURITY_FINDINGS.md`
(создаётся только при обнаружении секрета; в этой сессии секретов не найдено).
