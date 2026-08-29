# CONTRACT GRAPH — promt107 forensic

> Для каждой стрелки: REAL CONTRACT / PARTIAL / IMPLICIT / NO CONTRACT.

## Граф 1: Work/Production (гипотеза promt107 §3)

```
PROJECT ──REAL──→ WORK (ForgePipeline stage_*) 
   │
   ├─PARTIAL─→ SCENARIO (ScenarioRegistry.find_role, НЕ обязателен для forge)
   │
   ├─REAL─→ FACTORY (Opportunity → FactoryRegistry.select_forge → (FactoryPassport,
   │            ForgePassport) → ForgeFacade.run_chain через opportunity_engine.execute
   │            и BaseFactory.execute — execution-мост СШИТ, селекция адвизорная)
   │
   └─REAL──→ FORGE (ForgeFacade.initiate_forge → ForgePipeline → ForgeRegistry)
               │
               └─REAL──→ ARTIFACT (RoleArtifactValidator + Project.get_requirements)
```

**Вердикт §26 (уточнение по code evidence):** последовательность `PROJECT → SCENARIO → FACTORY → FORGE`
как ОДИН сквозной конвейер в строгой форме — **DOCUMENTED ONLY**, но обе ветки РЕАЛЬНЫ:
- **Path A (REAL):** `Project → ForgeFacade → ForgePipeline → ForgeRegistry → Artifact` (Forge-слой).
- **Path B (REAL):** `Opportunity → capability → FactoryRegistry.select_forge → (ForgePassport)`
  → **`ForgeFacade.run_chain`** (роль-ориентированное исполнение). Evidence:
  - `scripts_01/opportunity_engine.py:941` — `facade.run_chain(project, role_ids=role_ids)` внутри `execute()`;
    селекция записывается в `provenance['factory_selection'***REMOVED***` (traceability §15).
  - `core_02/factory_base.py:361` — `facade.run_chain(...)` внутри `BaseFactory.execute()`
    (resolve → build_execution_request → run_chain → normalize_output → _accumulate).
  - `scripts_01/forge.py:490` — chain-CLI также вызывает `run_chain`.
  Единственный нюанс: `forge_id` из паспорта — **адвизорный** (traceability), исполнение идёт
  по `role_ids` сценария; в системе один ForgeFacade/ForgePipeline, поэтому физический
  выбор кузни отсутствует по дизайну (не дыра).

## Граф 2: Agent/Model/Role/Task/Tool

```
HUMAN/AGENT ──IMPLICIT──→ ROLE (нет Agent-класса; роль выбирается wizard'ом или задаётся)
ROLE ──REAL──→ MODEL (BlueprintCorpus.routing_hint → SmartRouter.route → ModelCatalog)
ROLE ──REAL──→ TASK (ForgeFacade.run_chain → role stages)
TASK ──REAL──→ TOOL (tool_runtime / mcp_server) [ДВА несвязанных tool-механизма***REMOVED***
TOOL ──REAL──→ EXECUTION (subprocess / LLM call)
```

## Граф 3: Knowledge/Memory

```
WORKSPACE ──PARTIAL──→ KNOWLEDGE (knowledge_engine, graph_index, engineering_memory —
                       конкурирующие, единого source-of-truth нет)
KNOWLEDGE ──IMPLICIT──→ PROJECTS (нет link от memory к project кроме graph_index Node/Edge)
```

## Граф 4: Integration

```
WORKSPACE ──NO CONTRACT──→ INTEGRATION LAYER (слой не существует как граница)
WORKSPACE ──IMPLICIT──→ EXTERNAL (TG/MCP/phone вшиты напрямую в ядро)
```

## Сводка контрактов

| Связь | Тип контракта | Что не хватает |
|-------|--------------|----------------|
| Project → Forge | REAL (ForgeFacade) | — |
| Scenario → Forge | IMPLICIT (через wizard→role→facade) | явный Scenario→Factory→Forge контракт |
| Factory → Forge | REAL (select_forge → ForgeFacade.run_chain; opportunity_engine.py:941, factory_base.py:361) | forge_id адвизорный; единый ForgeFacade |
| Agent → Role | NO (нет Agent-класса) | Agent base class + lifecycle |
| Role → Model | REAL (routing_hint → SmartRouter) | — |
| Task ↔ Task | CONFLICTING (task_manager vs orchestrator) | единый task-механизм или явное разграничение |
| Tool ↔ Tool | CONFLICTING (tool_runtime vs mcp_server) | единый tool-контракт |
| Memory ↔ Memory | CONFLICTING (×4 движка) | единый memory source-of-truth |
| Workspace ↔ Project | REAL + DUPLICATED (2 модели) | единая Workspace модель |
| Integration → External | NO (нет adapter-слоя) | Integration/Connector/Adapter layer |
