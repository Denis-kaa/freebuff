# 02_ARCHITECTURE_REALITY_MAP — Фактическая карта платформы

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §12 (CURRENT ARCHITECTURE MAP) + §15 (CRITICAL ARCHITECTURAL QUESTION)
> **Метод:** каждый узел — реальный код (path+symbol), статус IMPLEMENTED / PARTIAL / PLANNED / MISSING.

---

## 1. Фактическая модель (что реально в коде)

```
                    USER
                      │  (CLI / API / TG / MCP)
        ┌─────────────┼─────────────────┐
        ↓             ↓                 ↓
   forge.py      forge_api.py      telegram_bot.py / mcp_server.py
   (CLI)         (REST :8765)      (entrypoints)
        │             │                 │
        └─────────────┼─────────────────┘
                      ↓
              INTELLIGENCE  (opportunity_engine.py + whim_capture.py)   [IMPLEMENTED***REMOVED***
                      │   DISCOVER (4 реальных источника) / PROPOSE / EXECUTE / ACCUMULATE
        ┌─────────────┼─────────────────┐
        ↓             ↓                 ↓
   SIGNALS        STATE            OPPORTUNITIES
   whims.yaml    project_pulse.db   opportunities.yaml
   events.db     forge_registry.yaml
        │             │                  │
        └─────────────┼──────────────────┘
                      ↓
               SCENARIO  (scenario_registry.py, ScenarioRegistry)   [IMPLEMENTED***REMOVED***
                      │   SELECT: propose_roles / find_role
                      ↓
               FACTORY  (factory_registry.py + factory_passport.py) [IMPLEMENTED v5.189.21***REMOVED***
                      │   select_forge(capability) → (factory, forge)
                      ↓
                FORGE  (forge_facade.py, ForgeFacade.run_chain)     [IMPLEMENTED***REMOVED***
                      │   EXECUTION — 14-ролевая цепочка (PIPELINE_CHAIN)
                      ↓
               ARTIFACT  (RoleArtifactValidator)                    [IMPLEMENTED***REMOVED***
                      ↓
               MEMORY  (memory_store.py, MemoryStore)               [IMPLEMENTED***REMOVED***
                      │   ACCUMULATE: store_knowledge(kind=candidate)
                      ↓
              LEARNING  (learning_loop.py, LearningLoop)            [IMPLEMENTED***REMOVED***
                      │   record_feedback / record_learning_event
                      └──────────→ INTELLIGENCE (переоценка)
```

## 2. Статусная матрица компонентов

| Компонент | Файл | Статус |
|-----------|------|--------|
| Event Bus | `scripts_01/event_bus.py` (`EventBus`, `publish`/`subscribe`/`get_events`) | ✅ IMPLEMENTED |
| Plugin API | `scripts_01/plugin_api.py` (`PluginRegistry`, `BasePlugin`, `PluginLoader`) | ✅ IMPLEMENTED |
| Plugin Contract | `scripts_01/plugin_contract.py` (`validate_manifest`) | ✅ IMPLEMENTED |
| MCP | `scripts_01/mcp_server.py` (40+ `_handle_*` tools) | ✅ IMPLEMENTED |
| Telegram Bot | `scripts_01/telegram_bot.py` (`cmd_task`, `cmd_notify`, `_handle_message`) | ✅ IMPLEMENTED |
| Scenario Registry | `core_02/scenario_registry.py` (`ScenarioRegistry`) | ✅ IMPLEMENTED |
| Scenario Engine (оркестратор) | — | ⏸ PLANNED (`scenario_engine` design_ready в missing_registry) |
| Factory Registry | `core_02/factory_registry.py` + `factory_passport.py` | ✅ IMPLEMENTED (v5.189.21) |
| Forge Facade | `core_02/forge_facade.py` (`ForgeFacade.run_chain`) | ✅ IMPLEMENTED |
| Forge Pipeline | `core_02/forge_pipeline.py` (`ForgePipeline`) | ✅ IMPLEMENTED |
| Forge Registry | `core_02/forge_registry.py` (`ForgeRegistry`) | ✅ IMPLEMENTED |
| Opportunity Engine | `scripts_01/opportunity_engine.py` | ✅ IMPLEMENTED |
| Whim Capture | `scripts_01/whim_capture.py` | ✅ IMPLEMENTED |
| Memory | `core_02/memory_store.py` (`MemoryStore`) | ✅ IMPLEMENTED |
| Knowledge | `scripts_01/knowledge_engine.py` (`KnowledgeEngine`) | ✅ IMPLEMENTED |
| Learning | `core_02/learning_loop.py` (`LearningLoop`) | ✅ IMPLEMENTED |
| Project State | `core_02/workspace.py` + `workspace_registry.py` + `forge_registry.py` | ✅ IMPLEMENTED |
| Project Pulse | `scripts_01/project_pulse.py` (`ProjectPulse`) | ✅ IMPLEMENTED |
| Scheduler | — (grep: 0 совпадений `class Scheduler`/`def schedule`) | ❌ MISSING |
| Agent Runtime | — (grep: 0 совпадений `AgentRuntime`) | ❌ MISSING (distributed_agents.py ≠ runtime) |
| Graph Index | `scripts_01/graph_index.py` (`GraphIndex`) | ✅ IMPLEMENTED |
| Semantic Layer | `core_02/semantic_layer.py` (`SemanticLayer`) | ✅ IMPLEMENTED |
| Intelligence Loop (CI) | `opportunity_engine` DISCOVER→…→ACCUMULATE | ✅ IMPLEMENTED (v5.189.16) |

## 3. Где заканчивается execution layer и где начинается Intelligence (§15)

**Фактическая граница (проверено кодом):**

- **Execution layer** (нижняя половина): `ForgeFacade.run_chain` → `RoleArtifactValidator` → `MemoryStore` → `LearningLoop`. Исполняет, валидирует, накапливает.
- **Intelligence layer** (верхняя половина): `opportunity_engine` (DISCOVER→PROPOSE→SELECT→EXECUTE→VALIDATE→ACCUMULATE) + `whim_capture`. Принимает решения WHAT/WHY, НЕ исполняет сам.

**Ключевой факт:** граница проходит **внутри** `opportunity_engine.execute()` — оно вызывает `ForgeFacade.run_chain` (единственный санкционированный мост, B-rule §7.3). Никакой другой код НЕ вызывает Forge напрямую из Intelligence-слоя. Это соответствует модели INTELLIGENCE → SCENARIO → FACTORY → FORGE → ARTIFACT.

**Расхождение с идеальной моделью:** в идеале между SCENARIO и FORGE стоит FACTORY (select_forge). Фактически `opportunity_engine.execute()` вызывает `ForgeFacade.run_chain` **напрямую** (через `_probe_pipeline_roles()`), не используя `select_forge()` из FactoryRegistry. **Соединительный слой FACTORY→FORGE в цикле пока не подключён** (см. 14_NEXT_VERTICAL_SLICE).

## 4. Вертикальный slice (реальный execution path, §4)

```
USER: opportunity_engine discover --project-id X  (CLI)
  ↓  scripts_01/opportunity_engine.py::_cli_discover
  ↓  discover_candidates(X, rank=...)  → 4 реальных источника
  ↓    _discover_from_whims  (WhimStore→whims.yaml)
  ↓    _discover_from_pulse  (ProjectPulse→project_pulse.db)
  ↓    _discover_from_events (EventBus→events.db)
  ↓    _discover_from_knowledge (MemoryStore→context.db)
  ↓  rank_candidates (score, provenance['rank_score'***REMOVED***/rank_factors)
  ↓  OpportunityStore.upsert → data_13/opportunities.yaml
USER: opportunity_engine run <id>
  ↓  propose (ScenarioRegistry.propose_roles → opp.scenario)
  ↓  execute → ForgeFacade.run_chain(project_id, role_ids)
  ↓  advance(opp, "COMPLETED"/"FAILED")
  ↓  accumulate → MemoryStore.store_knowledge(kind=candidate) + LearningLoop
```

Каждый переход подтверждён реальным вызовом функции (см. code evidence в 03_CODE_CONTRACT_MAP).

---

_Конец 02_ARCHITECTURE_REALITY_MAP. Переход к 03_CODE_CONTRACT_MAP._
