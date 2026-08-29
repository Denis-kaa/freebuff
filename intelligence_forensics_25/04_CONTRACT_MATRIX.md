# 04 — CONTRACT MATRIX

> Статусы: EXISTS / PARTIAL / MISSING / UNKNOWN. Для EXISTS — реальный файл+API. Для MISSING — только минимальный required contract.

| Контракт | Статус | Реальный файл/API (если EXISTS) | Минимальный required contract (если MISSING/PARTIAL) |
|----------|--------|--------------------------------|------------------------------------------------------|
| Project Contract | EXISTS | `core_02/workspace.py::Project` (`name, root, type, stack, roles, contracts, requirements_steps`; `load/get_requirements/to_dict`) | — |
| Workspace Contract | EXISTS | `core_02/workspace.py::Workspace` + `workspace_registry.py::WorkspaceRegistry` (`seed_defaults/create_workspace/add_project`) | — |
| Agent/Runtime Contract | EXISTS | `scripts_01/model_gateway.py::ModelGateway`; `tool_runtime.py` ToolRegistry | — |
| Scenario Contract | EXISTS | `core_02/scenario.py::Scenario` ABC + `Role` dataclass + `ScenarioManifest.from_yaml` | — |
| Factory Contract | EXISTS | `core_02/forge_passport.py::ForgePassport` (9 passport fields + REQUIRED_FIELDS) + `factory_registry.py` | — |
| Forge Contract | EXISTS | `core_02/forge_facade.py::ForgeFacade` (`initiate_forge`, `run_chain`, `can_initiate`) + `forge_registry.py::ForgeStatus` | — |
| Artifact Contract | EXISTS | `forge_facade.py::RoleArtifactValidator` + `RoleArtifactReport` (existence-only) | — |
| Memory Contract | EXISTS | `core_02/memory_store.py::MemoryStore` (`store_knowledge/link_knowledge/update_feedback/record_learning_event`) | — |
| Knowledge Contract | EXISTS | `scripts_01/knowledge_engine.py::KnowledgeEngine` + `core_02/semantic_layer.py::SemanticLayer` | — |
| Event Contract | EXISTS | `scripts_01/event_bus.py::Event` + `EventBus.publish/subscribe` (wildcard) | — |
| Plugin Contract | EXISTS | `scripts_01/plugin_api.py::BasePlugin` + `scripts_01/plugin_contract.py::validate_plugin_entry` | — |
| MCP Contract | EXISTS | `scripts_01/mcp_server.py` + `freebuff_plugin_03/mcp_server.py` | — |
| **Opportunity Contract** | **PARTIAL** | `scripts_01/opportunity_engine.py::Opportunity` (16 полей dataclass) + `advance` state machine | Регистрация 16 полей в `CONTRACT_REGISTRY_V1.md` (§E) — lifecycle в YAML, content в MemoryStore KO |
| **Whim Contract** | **PARTIAL** | `scripts_01/whim_capture.py::Whim` + `capture/triage/promote/defer` | Регистрация schema в `CONTRACT_REGISTRY_V1.md` (§17.1); cross-ref `related_opportunity_id` |
| **Concept Evolution Contract** | **MISSING** | — (grep 0 matches) | Только точка интеграции: IDEA EXPLORER → CONCEPT EVOLUTION → MATURE CONCEPT → PROMPT ARCHITECT → SCENARIO/FACTORY (НЕ строить сейчас) |
| Traceability Contract | EXISTS | `core_02/anchors_resolver.py::AnchorResolver` (19 namespaces) + `doc_code_verify.py` | — |

## Контракты, существующие, но НЕ зарегистрированные

**FACT:** Opportunity (16 полей) и Whim (schema) существуют в коде, но не внесены в канонический `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md`.
**GAP G2:** contract extension — зарегистрировать Opportunity Contract + Whim Contract в реестре.
