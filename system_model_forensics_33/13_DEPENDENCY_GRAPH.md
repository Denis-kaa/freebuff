# 13_DEPENDENCY_GRAPH.md — Граф зависимостей

> **Статус:** FORENSIC FACT (по import-графу, read_files)

---

## Направленный граф (core flow)

```
                      [ENTRYPOINTS***REMOVED***
    forge.py (CLI) · forge_api.py (HTTP) · mcp_fastapi.py · telegram_bot.py · wizard.py
          │                    │                    │                │            │
          ▼                    ▼                    ▼                ▼            ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          PLATFORM CORE (core_02/)                        │
    │                                                                         │
    │   workspace.py ──► workspace_registry.py (B1)                           │
    │   scenario.py ──► scenario_registry.py ──► blueprint_v3.py              │
    │   factory_registry.py ──► factory_passport.py + forge_passport.py       │
    │   factory_base.py ──► factory_registry.py + forge_facade.py + memory    │
    │   forge_facade.py ──► forge_pipeline.py + forge_registry.py + role_executor.py │
    │   role_executor.py ──► blueprint_v3.py + model_gateway.py               │
    │   router.py (SmartRouter/ModelCatalog)                                  │
    │   boundaries_v17.py (B1–B14)                                            │
    └─────────────────────────────────────────────────────────────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
   [INTELLIGENCE HEAD***REMOVED***   [TOOLS***REMOVED***            [MEMORY/KNOWLEDGE***REMOVED***
   whim_capture.py      tool_runtime.py     memory_store.py
   opportunity_engine.py                    learning_loop.py
   scenario_intelligence.py                 knowledge_engine.py
   (всё → forge_facade.py)                  semantic_layer.py + rag_engine.py + graph_index.py
```

## Сходимость на ForgeFacade

```
whim_capture ─► opportunity_engine ─► scenario_intelligence ─► factory_registry
                                                                   │
                                                                   ▼
                                            ┌────── ForgeFacade.run_chain ◄──────┐
                                            │                                        │
                          forge.py cmd_chain ───────────────────────────────────────┘
```

`ForgeFacade` — **единственный execution boundary** (§7.3). Три входа:
1. `forge.py cmd_chain` (CLI-явный).
2. `opportunity_engine.execute` (intelligence-путь).
3. `BaseFactory.execute` (factory-адаптер).

## Ортогональный (НЕ соединён) путь

```
orchestrator.py (Goal→Plan→Execute→Validate)
   └─ StepType.MODEL ─► core_02/router.SmartRouter (НЕ ForgeFacade)
   └─ StepType.TOOL  ─► tool_runtime.py / ToolExecutor
```

## Запрещённые/нарушенные рёбра

| Ребро | Статус | Комментарий |
|-------|--------|-------------|
| scenario → forge (напрямую) | ЗАПРЕЩЕНО §7.3 | соблюдается (только через ForgeFacade) |
| project → platform (импорт scripts_01 из projects_17) | НАРУШЕНО | встречается (promt105) |
| core → interfaces | ЗАПРЕЩЕНО | не наблюдается |
| factory → scenario | не должно | FactoryRegistry не импортирует scenario (B-Rule 4/5) |
