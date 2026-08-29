# 07_AGENT_RUNTIME_SKILL_TOOL_ANALYSIS.md — Слой агентов / рантаймов / скиллов / тулов

> **Задача (§2):** НЕ объединять похожие понятия. Восстановить реальные границы.

---

## Agent — PARTIAL (размазан по 4+ местам)

В коде **нет единой абстракции `Agent`** (stateful сущность с памятью и скиллами).
То, что выполняет агентскую функцию, размазано:

| Место | Символ | Роль |
|-------|--------|------|
| `core_02/role_executor.py` | `RoleExecutorRegistry`, `LisaExecutor`, `LlmRoleExecutor` | роль как **генератор артефакта** (один LLM-вызов на роль) |
| `scripts_01/distributed_agents.py` | (distributed agents) | распределённые агенты (Phase 5+) |
| `freebuff_plugin_03/runtime/registry.py` | `RuntimeRegistry`, `RuntimeCapabilityRegistry` | реестр рантаймов-агентов |
| `scripts_01/roles.py` + `presence.py` + `collaboration.py` | roles/presence/collab | коллаборационный слой (Phase 7 CoWork) |
| `plugins_04/` | manifest.json + `__init__.py` | плагины (заглушки hello_world/tg_messenger/system_monitor/knowledge_sync) |

**Что такое Agent в реальности?** — Не класс, а **роль** (`Role` dataclass в
`scenario.py` + `RoleExecutor` в `role_executor.py`). Роль = id + title + role_type +
routing_hint. Исполнение роли = один LLM-вызов (`LlmRoleExecutor.execute`) или
детерминированный генератор (`LisaExecutor`).

## Role vs Agent vs Runtime vs Skill vs Tool vs Workflow

| Понятие | Реальность | Модуль |
|---------|-----------|--------|
| **Role** | dataclass: id/title/role_type/routing_hint + executor | `core_02/scenario.py::Role` + `core_02/role_executor.py` |
| **Agent** | ABSENT как stateful; ≈ RoleExecutor (stateless генератор) | `role_executor.py`, `distributed_agents.py` |
| **Runtime** | реестр рантаймов-агентов (policy: user-choice override) | `freebuff_plugin_03/runtime/registry.py` |
| **Skill** | ABSENT как модуль; capability-токены (closed vocab) | `KNOWN_CAPABILITIES` (blueprint_v3) + `missing_registry.py` |
| **Tool** | интерфейс к действию (5 инструментов) | `scripts_01/tool_runtime.py` |
| **Workflow** | фиксированный порядок (chain) ИЛИ DAG (orchestrator) | `forge_facade.PIPELINE_CHAIN` / `orchestrator.py` |
| **Scenario** | корпус ролей ИЛИ decision-слой | `scenario.py` / `scenario_intelligence.py` |

## Ответы на §2 вопросы

1. **Где слой агента?** — размазан (см. таблицу выше).
2. **Что такое Agent?** — нет единого класса; роль-исполнитель.
3. **Что такое Runtime?** — `freebuff_plugin_03/runtime/registry.py` (реестр + policy).
4. **Что такое Role?** — `scenario.py::Role` + `role_executor.py::RoleExecutor`.
5. **Что такое Skill?** — НЕ существует; capability-токен.
6. **Что такое Tool?** — `tool_runtime.py::BaseTool`.
7. **Что такое Workflow?** — 2 механизма: chain (фикс. порядок) + DAG (orchestrator).
8. **Что такое Scenario?** — двойственен (corpus + decision).
9. **Как связаны?** — Role → (RoleExecutor) → Artifact; Scenario → (Registry) → Role;
   Factory → (select_forge) → Forge → (run_chain) → Role; Orchestrator → (DAG) → Tool/Agent/Model.
10. **Кто решает о запуске Factory/Forge?** — `opportunity_engine.execute` →
    `_select_factory_forge` (capability → FactoryRegistry), или `forge.py cmd_chain` (CLI-явный).
11. **Может ли агент сам инициировать execution?** — Orchestrator может (автономный
    Goal→Plan→Execute), но **не соединён** с ForgeFacade. ForgeFacade — только по явному
    запросу роли (§7.3 «не молча»).
12. **Через какой интерфейс?** — `ForgeFacade.initiate_forge` (роль→Forge) / `run_chain`.
13. **Где контекст пользователя?** — `scripts_01/context_manager.py`.
14. **Где контекст Project?** — `projects_17/<slug>/` + `Project.get_requirements`.
15. **Где память разговора?** — `memory_store.py` (KO) + `memory_engine.py`.
16. **Где knowledge?** — `knowledge_engine.py` + `semantic_layer.py` + `rag_engine.py`.
17. **Где execution state?** — `forge_registry.py` (статусы) + `data_13/forge_registry.yaml` + `opportunities.yaml`.

## Вывод

Слой агента **существует функционально, но не архитектурно**: роль-исполнитель
(`RoleExecutor`) — это stateless генератор, а не stateful агент с памятью. Skill
**отсутствует** — его место занимает закрытый словарь capability-токенов.
Runtime — реестр, а не полноценный агентский слой. Это ключевой gap между
target-моделью («companion + специализированные агенты») и кодом.
