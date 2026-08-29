# 11 — DO NOT BUILD

> Всё, что УЖЕ существует — не строить дубликаты. Каждое утверждение подтверждено repository.

## DO NOT BUILD (с evidence)

| Не строить | Потому что уже есть | Evidence |
|-----------|---------------------|----------|
| second EventBus | `EventBus` (pub/sub + SQLite log + wildcard) | scripts_01/event_bus.py |
| second Memory system | `MemoryStore` (SQLite, 10 KO kinds, граф) | core_02/memory_store.py |
| second Knowledge engine | `KnowledgeEngine` + `SemanticLayer` | scripts_01/knowledge_engine.py, core_02/semantic_layer.py |
| second Scenario Registry | `ScenarioRegistry` (auto-discovery) | core_02/scenario_registry.py |
| second Forge executor | `ForgeFacade.run_chain` (единственный мост §7.3) | core_02/forge_facade.py |
| second Agent runtime | `ModelGateway` + `distributed_agents` | scripts_01/model_gateway.py |
| second scheduler | диспетчеризация (prompt_queue/dispatcher/task_manager) | scripts_01/prompt_queue.py и др. |
| second plugin system | `PluginRegistry` + `PluginLoader` | scripts_01/plugin_api.py |
| second MCP layer | mcp_server (HTTP+handlers) + mcp_fastapi | scripts_01/mcp_server.py, mcp_fastapi.py |
| **Opportunity Engine** (с нуля) | `opportunity_engine.py` УЖЕ реализован | scripts_01/opportunity_engine.py |
| **Whim UI / capture** (с нуля) | `whim_capture.py` УЖЕ реализован | scripts_01/whim_capture.py |
| Signal abstraction (новый слой) | `EventBus` + `ProjectPulse` достаточно выразительны | scripts_01/event_bus.py, project_pulse.py |
| Вторая traceability-система | `AnchorResolver` (17 @-ns + doc.*) | core_02/anchors_resolver.py |
| Второй Learning Loop | `LearningLoop` (AFC) | core_02/learning_loop.py |

## Ключевой вывод

**FACT:** Промт §3 запрещает строить Opportunity Engine / Whim UI / Concept Evolution «с нуля». Opportunity и Whim УЖЕ построены → запрет трансформируется в «не переписывать, а интегрировать».
**FACT:** Единственное, чего действительно НЕТ — Concept Evolution (grep 0). И его строить НЕ нужно сейчас (§13).
