# 01 — REPOSITORY REALITY MAP

> **Промт:** `pompts_11/084_19_intelligence_integration_forensics.md`
> **Роль документа:** канонический перечень «что реально существует» — по коду, не по документации.
> **Правило:** REPOSITORY = SOURCE OF TRUTH. Код > документации > имён классов.
> **Дата аудита:** 2026-08-16 · **Версия платформы:** v5.189.14

## Статусы верификации (§26)

| Статус | Значение |
|--------|----------|
| `IMPLEMENTED / VERIFIED` | код есть, вызывается, тестируется (pytest зелёный) |
| `IMPLEMENTED / RUNTIME UNVERIFIED` | код есть, но вызывающий путь/реальный прогон не подтверждён |
| `DOCUMENTED ONLY` | есть только документация, код не найден |
| `TESTED / IMPLEMENTATION STATUS REQUIRES REVIEW` | только тест, реализация не подтверждена |
| `NOT VERIFIED` | реализация не найдена |

---

## R1. Инфраструктурные подсистемы Phase 4

| # | Подсистема | Существование | Файл(ы) | Статус |
|---|-----------|---------------|----------|--------|
| R1.1 | Event Bus | ✅ | `scripts_01/event_bus.py` (`EventBus`, `Event`, `Subscription`, `EventLogEntry`, `get_default_event_bus`) | IMPLEMENTED / VERIFIED (177 tests) |
| R1.2 | Plugin API | ✅ | `scripts_01/plugin_api.py` (`BasePlugin`, `PluginRegistry`, `PluginLoader`, `PluginState`) | IMPLEMENTED / VERIFIED |
| R1.3 | MCP Server | ✅ | `scripts_01/mcp_server.py` (HTTP+handlers) + `scripts_01/mcp_fastapi.py` | IMPLEMENTED / VERIFIED |
| R1.4 | Telegram Bot | ✅ | `scripts_01/telegram_bot.py`, `core_02/telegram_contract.py`, `core_02/tgbot_base.py` | IMPLEMENTED / VERIFIED |
| R1.5 | Scenario Engine | ✅ | `core_02/scenario.py` (`Scenario` ABC, `Role`), `core_02/scenario_registry.py` (`ScenarioRegistry`), `core_02/blueprint_v3.py` (`BlueprintCorpus`) | IMPLEMENTED / VERIFIED |
| R1.6 | Factory | ✅ | `core_02/factory_registry.py` (`FactoryRegistry`), `core_02/forge_passport.py` (`ForgePassport`) | IMPLEMENTED / VERIFIED |
| R1.7 | Forge | ✅ | `core_02/forge_facade.py` (`ForgeFacade`, `run_chain`, `RoleArtifactValidator`), `core_02/forge_pipeline.py` (`ForgePipeline`), `core_02/forge_registry.py` (`ForgeRegistry`) | IMPLEMENTED / VERIFIED |
| R1.8 | Memory | ✅ | `core_02/memory_store.py` (`MemoryStore`), `scripts_01/memory_engine.py` | IMPLEMENTED / VERIFIED |
| R1.9 | Knowledge | ✅ | `scripts_01/knowledge_engine.py` (`KnowledgeEngine`), `core_02/semantic_layer.py` (`SemanticLayer`), `scripts_01/graph_index.py` | IMPLEMENTED / VERIFIED |
| R1.10 | Project/Workspace | ✅ | `core_02/workspace.py` (`Workspace` L-1, `Project` L-2), `core_02/workspace_registry.py` (`WorkspaceRegistry`) | IMPLEMENTED / VERIFIED |
| R1.11 | Scheduler | ⚠️ | Нет отдельного `Scheduler`-класса; диспетчеризация есть через `scripts_01/task_manager.py` + `scripts_01/prompt_queue.py` / `prompt_dispatcher.py` | NOT VERIFIED (как имя «Scheduler»); механизм диспетчеризации — IMPLEMENTED / VERIFIED |
| R1.12 | Monitoring | ✅ | `scripts_01/metrics.py`, `scripts_01/system_monitor.py`, `scripts_01/doctor.py`, `core_02/environment_doctor.py` | IMPLEMENTED / VERIFIED |
| R1.13 | Agents (multi-agent) | ✅ | `scripts_01/distributed_agents.py`, `scripts_01/agent_context_bridge.py`, `scripts_01/model_gateway.py` (`ModelGateway`) | IMPLEMENTED / RUNTIME UNVERIFIED |
| R1.14 | Tool Runtime | ✅ | `scripts_01/tool_runtime.py` (ToolRegistry) | IMPLEMENTED / VERIFIED |
| R1.15 | Registry/Contracts | ✅ | `core_02/contracts.py`, `core_02/boundaries_v17.py`, `core_02/missing_registry.py`, `docs_10/engineering-memory/CONTRACT_REGISTRY_V1.md` | IMPLEMENTED / VERIFIED |

---

## R2. Intelligence-специфичные подсистемы (критично для §11–§13)

| # | Подсистема | Существование | Файл(ы) | Статус |
|---|-----------|---------------|----------|--------|
| R2.1 | **Opportunity Engine** | ✅ **УЖЕ СУЩЕСТВУЕТ** | `scripts_01/opportunity_engine.py` (`Opportunity` 16 полей, `OpportunityStore`, `advance`, `discover_candidates`, `propose`, `execute`) | IMPLEMENTED / VERIFIED (68 tests с whim) |
| R2.2 | **Whim Capture** | ✅ **УЖЕ СУЩЕСТВУЕТ** | `scripts_01/whim_capture.py` (`Whim`, `WhimStore`, `capture`, `triage`, `promote`, `defer`, `classify_heuristic`) | IMPLEMENTED / VERIFIED |
| R2.3 | **Concept Evolution System** | ❌ **НЕ СУЩЕСТВУЕТ** | grep `concept_evolution` / `ConceptEvolution` в `*.py` → 0 matches (в docs — только как future-concept, не реализация) | NOT VERIFIED |
| R2.4 | Learning Loop | ✅ | `core_02/learning_loop.py` (`LearningLoop` AFC, `Analysis`, `capture`, `codify`, `record_feedback`) | IMPLEMENTED / VERIFIED |
| R2.5 | Traceability (anchors) | ✅ | `core_02/anchors_resolver.py` (`AnchorResolver`, 17 @-ns + doc.*), `core_02/doc_code_verify.py` | IMPLEMENTED / VERIFIED |
| R2.6 | Consistency check | ✅ | `scripts_01/consistency_check.py` | IMPLEMENTED / VERIFIED |
| R2.7 | Project Pulse (observation) | ✅ | `scripts_01/project_pulse.py` (`ProjectPulse`) | IMPLEMENTED / VERIFIED |

---

## R3. Ключевые выводы о презумпции промта

**Промт §3 («НЕ реализуй Opportunity Engine / Whim UI») и §11–§12 (Opportunity / Whim как будущие контракты) — презумпция УСТАРЕЛА.**

- `scripts_01/opportunity_engine.py` — **полноценная реализация** Opportunity Engine (Phase 1, Missing Capability #8), с lifecycle-машиной, YAML-персистом, CLI.
- `scripts_01/whim_capture.py` — **полноценная реализация** Whim Capture (Phase 1.2, Missing Capability #9), с triage-эвристикой и promote-хуком.
- Оба реализованы по промтам `079_19_opportunity_engine_capability.md` и `080_19_whim_capture_capability.md`.

**FACT:** Opportunity Engine и Whim Capture существуют в production-коде и покрыты тестами.
**INFERENCE:** Intelligence-слой следует НЕ «проектировать Opportunity/Whim с нуля», а «интегрировать существующие primitives».
**DECISION:** Глубина forensics сдвигается с «какой минимальный контракт нужен» на «как связать существующий Opportunity/Whim с остальной цепочкой».

---

## R4. Не найдено / требует явного уточнения

| Сущность | Статус | Примечание |
|----------|--------|-----------|
| `Scheduler` (отдельный класс) | NOT VERIFIED | есть `task_manager.py`, `prompt_queue.py`, `prompt_dispatcher.py` — диспетчеризация есть, «Scheduler» как имя отсутствует |
| `Signal` abstraction | NOT VERIFIED | НЕ нужен — EventBus.emit + ProjectPulse достаточно (см. 03/09) |
| `Concept Evolution` | NOT VERIFIED | единственный реально отсутствующий intelligence-компонент |
| `Workspace UI` | NOT VERIFIED | UI не в scope — корректно (промт §3 запрещает его строить) |
