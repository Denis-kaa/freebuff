# UNIFIED_CONCLUSIONS.md — Единый Executive Summary (6 проходов: 104/105/106/107 + ADR-019/020)

> Синтез всех forensic-проходов. Формат: «что уже система / что набор механизмов /
> что только документация / чего реально не хватает» (promt107 §27). Все P1-контракты ЗАКРЫТЫ (v5.189.81).

---

## 1. Что уже является СИСТЕМОЙ

**Buffy Forge-слой** — единственный домен, где механизмы соединены сквозным контрактом:

```
Workspace(L-1) → Project(L-2) → ForgePipeline(L-3) → ForgeRegistry(L-4) → ForgeFacade
    core_02/workspace.py   core_02/forge_pipeline.py  core_02/forge_registry.py  core_02/forge_facade.py
```

- Подтверждено: 104 (FACTORY_FORGE_ANALYSIS), 106 (06_…ANALYSIS), 107 (§B/C/I).
- Полный жизненный цикл: FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT, статусы
  UNFORGED → DEPLOYED/FAILED, B10-валидация, chain-runner 14 ролей (LIGHT/HEAVY/CONDITIONAL).
- Сопровождается тестами: test_forge_pipeline/registry/facade/chain_cli/chain_real_integration.

Дополнительно **capability-роутинг** — data-driven: `SmartRouter/ModelCatalog`
(core_02/router.py) + `ModelGateway` (scripts_01/model_gateway.py) + closed-set
capability tokens (паспорта, KNOWN_CAPABILITIES).

## 2. Что является НАБОРОМ РАБОТАЮЩИХ МЕХАНИЗМОВ (не связанных между собой)

| Кластер | Механизмы | Проблема |
|---------|-----------|----------|
| **Memory/Knowledge** ×4 | memory_engine, knowledge_engine, graph_index, engineering_memory | нет единого source-of-truth; конкурируют |
| **Role** ×2 | Blueprint pipeline-роли (14-17) vs roles.py collab-роли (6) | разные слои, но оба называют себя «роли» |
| **Task** ×2 | task_manager.py (SQLite) vs orchestrator.py (Workflow/Step) | два механизма управления задачами |
| **Tool** ×2 | tool_runtime.py (BaseTool×5) vs mcp_server.py (McpTool) | два tool-контракта |
| **Registry** ×6 | workspace, scenario, factory, forge, missing, tool (+role_executor) | разные форматы/хранилища, нет единого registry-контракта |
| **Workspace** ×2 | workspace.py (YAML) vs workspace_registry.py (SQLite) | два source-of-truth об одном домене |

## 3. Что является ТОЛЬКО ДОКУМЕНТАЦИЕЙ (DOCUMENTED ONLY)

| Концепт | Где документирован | Реальность в коде |
|---------|--------------------|-------------------|
| Сквозной `Project → Scenario → Factory → Forge → Artifact` конвейер | RFC_BUFFY_FORGE_V1, RESEARCH_V1 | разрозненно; Path A (REAL) и Path B (REAL — см. §5, code evidence) как две независимые ветки |
| PROJECT ROLE (Owner/PM/Contributor) ≠ AGENT ROLE | promt107 §5 | roles.py смешивает (get_collab_role маппит agent→collab) |
| Sandbox / tenant isolation | promt107 §14 | отсутствует; единая доверенная зона Termux |

> **Закрыто из DOCUMENTED ONLY → IMPLEMENTED (v5.189.80-v5.189.81):**
> - AGENT как класс с lifecycle → `core_02/agent_base.py::Agent` (ABC) + `AgentLifecycle` (forward-only DAG) + 29 тестов (ADR-019, v5.189.80).
> - Integration/Connector/Adapter слой → `core_02/integration_base.py::IntegrationAdapter` (ABC) + AuthSpec + `INTENT_CAPABILITY_MAP` + 33 теста (ADR-020, v5.189.81).

## 4. Чего РЕАЛЬНО НЕ ХВАТАЕТ (чтобы стать единой платформой)

1. **P0-блокеры:** единая Workspace модель (2 source-of-truth — design: ADR-017); sandbox/tool-ACL для
   внешних мостов (ShellTool без ограничений для локальных вызывающих).
2. **P1-контракты — ВСЕ ЗАКРЫТЫ (v5.189.81):**
   - Factory→Forge мост ЗАКРЫТ (ADR-018, REAL: `opportunity_engine.execute` → `ForgeFacade.run_chain`).
   - Agent base class + lifecycle ЗАКРЫТ (ADR-019, `core_02/agent_base.py`, 29 тестов).
   - Integration adapter boundary ЗАКРЫТ (ADR-020, `core_02/integration_base.py`, 33 теста).
3. **Дубли (P2):** task ×2, tool ×2, memory ×4.
4. **Репозиторий (P3):** историческая нумерация каталогов, смешение доменов,
   code/docs/prompts/tests/data вперемешку.
5. **Enhancements (P4):** семантические теги, метрики, UX — только после P0-P2.

## 5. Какие СВЯЗИ уже существуют в коде (а какие только предполагаем)

**Существуют (evidence в merged ledger):**
- Project → ForgeFacade → ForgePipeline → ForgeRegistry (REAL)
- Role → SmartRouter → ModelGateway (REAL, через routing_hint)
- ScenarioRegistry.find_role → wizard → role (REAL)
- FactoryRegistry.select_forge → (FactoryPassport, ForgePassport) → **ForgeFacade.run_chain**
  (REAL, мост сшит: `scripts_01/opportunity_engine.py:941` `facade.run_chain(project, role_ids=role_ids)`
  внутри `execute()`; `core_02/factory_base.py:361` внутри `BaseFactory.execute()`;
  `scripts_01/forge.py:490` chain-CLI. Селекция записывается в
  `provenance['factory_selection'***REMOVED***`; forge_id адвизорный — исполнение по role_ids сценария)
- WorkspaceRegistry.assert_path_privacy → PrivacyViolationError (REAL)
- ScenarioIntelligence → DecisionHistoryStore → EventBus (REAL)

**Только предполагаем (гипотеза, DOCUMENTED ONLY):**
- Project → Scenario → Factory → Forge → Artifact как единая последовательность (опровергнута 107)
- «Factory — производственная система» (на деле: CLI-обёртки BaseFactory + декларативные манифесты)

> **Снято с DOCUMENTED ONLY (v5.189.80-v5.189.81):**
> - AGENT — реализован (ADR-019, `core_02/agent_base.py`).
> - Integration-слой — реализован (ADR-020, `core_02/integration_base.py`).

## 6. Итоговый вердикт (по 104→107 + ADR-019/020)

> Платформа — **набор работающих механизмов с частично связанными границами**, в котором
> зрелым ядром является Forge-слой + capability-роутинг + Agent-класс (ADR-019) +
> Integration-граница (ADR-020). Все P1-контракты закрыты (v5.189.81). Чтобы стать
> единой платформой, нужны P0-фиксы (единая Workspace-модель — design: ADR-017,
> sandbox) и P2-дедупликация — по Additive Architecture, каждый шаг
> small/reversible/testable.
