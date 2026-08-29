# 05_CONCEPT_TRACEABILITY.md — Concept → Target → Actual → Gap

> **Формат (§5):** | Concept | Target responsibility | Actual implementation | Status | Evidence | Gap |

| Concept | Target responsibility | Actual implementation | Status | Evidence | Gap |
|---------|----------------------|----------------------|--------|----------|-----|
| WHIM | сырая мысль | `scripts_01/whim_capture.py` → `Whim` (lifecycle NEW→TRIAGED→PROMOTED→…) | CONFIRMED | `Whim`, `WhimStore`, `data_13/whims.yaml` | термин совпадает |
| WORKSPACE | local-first среда | `core_02/workspace.py::Workspace` (L-1) | PARTIAL | `Workspace.load(workspace.yaml)` | «среда» есть, «разговор/обсуждения» — нет (в ContextManager) |
| PROJECT | рабочая тетрадь/история | `core_02/workspace.py::Project` (L-2) + `projects_17/<slug>/` | PARTIAL | `Project.load(project.yaml)`, STEPS.md, get_requirements | «тетрадь» частично = STEPS.md; обсуждения/решения в Memory/LESSONS, не в Project |
| AGENT | companion + специализированные | размазан: `role_executor.py` + `distributed_agents.py` + `freebuff_plugin_03/runtime/` + `plugins_04/` | PARTIAL | `RoleExecutorRegistry`, `distributed_agents.py` | нет единой абстракции Agent |
| SCENARIO | ЧТО + тип работы | двойственен: `scenario.py` (корпус ролей) + `scenario_intelligence.py` (decision) | PARTIAL (dual) | `Scenario` (ABC) vs `ScenarioIntelligence.select()` | два понятия под одним именем |
| FACTORY | capability (класс результатов) | `factory_registry.py` + `factory_base.py` + `runtime_05/factories/*/factory.yaml` | CONFIRMED | `FactoryRegistry.select_forge()`, `FactoryPassport` | глобальная, НЕ принадлежит Project (совпадает с гипотезой) |
| FORGE | конкретный workflow внутри Factory | 4 смысла: `forge_passport.py` / `forge_facade.py` / `forge_pipeline.py` / `forge_registry.py` | PARTIAL (overloaded) | `ForgePassport`, `ForgeFacade.run_chain`, `ForgePipeline.run`, `ForgeRegistry` | термин перегружен 4 смыслами |
| ROLE | участник внутри Forge | `role_executor.py` (RoleExecutor) + `scenario.py::Role` + 14 PIPELINE_CHAIN ролей | CONFIRMED | `PIPELINE_CHAIN`, `RoleExecutorRegistry` | роль = генератор артефакта, не stateful агент |
| SKILL | атомарная способность | ABSENT как модуль; capability-токены | ABSENT | нет skill*.py; `KNOWN_CAPABILITIES` + `missing_registry.py` | Skill описан в целевой модели, отсутствует в коде |
| TOOL | интерфейс к внешнему действию | `scripts_01/tool_runtime.py` | CONFIRMED | `ToolRegistry`, `GitTool`…`ShellTool` | изолирован (не соединён с Forge chain) |
| RUNTIME | среда исполнения | `freebuff_plugin_03/runtime/registry.py` | PARTIAL | `RuntimeRegistry` | реестр, не полноценный слой |
| WORKFLOW | порядок шагов | `forge_facade.PIPELINE_CHAIN` (фикс. порядок) + `orchestrator.py` (DAG) | PARTIAL | `PIPELINE_CHAIN`, `Orchestrator` | два разных «workflow» механизма |
| ARTIFACT | результат | файлы в `project.root` (не тип-контейнер) | CONFIRMED | `RoleArtifactValidator`, `DEFAULT_ROLE_OUTPUTS` | файлы, не объект |
| MEMORY | разговор/история | `memory_store.py` + `memory_engine.py` | CONFIRMED | `MemoryStore`, `MemoryEngine` | совпадает |
| KNOWLEDGE | накопленные факты | `knowledge_engine.py` + `semantic_layer.py` + `rag_engine.py` | CONFIRMED | `KnowledgeEngine`, `SemanticLayer` | совпадает |
| EVENT | переходы | `event_bus.py` + `context_12/events.db` | CONFIRMED | `EventBus.publish`, `Event` | совпадает |
| TASK | единица работы | `orchestrator.Step` + `task_manager.py` + Opportunity | PARTIAL | `Step`, `TaskManager` | «task» размазан по 2-3 системам |

---

## Сводка статусов

- **CONFIRMED:** WHIM, FACTORY, ROLE, TOOL, ARTIFACT, MEMORY, KNOWLEDGE, EVENT (8)
- **PARTIAL:** WORKSPACE, PROJECT, AGENT, SCENARIO, FORGE, WORKFLOW, TASK (7)
- **ABSENT:** SKILL (1)
- **Дополнительный слой в коде:** OPPORTUNITY (нет в target) — см. R1.

## Главный вывод traceability

Целевая модель **пропускает слой Opportunity** (ключевой в Intelligence-пути) и
**избыточно описывает Skill** (отсутствует как модуль). Термины **Forge** и
**Scenario** в коде означают больше, чем в целевой модели.
