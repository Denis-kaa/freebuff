# 05 — EXISTING REUSE MAP

> Что Intelligence переиспользует БЕЗ создания дубликатов. Каждое утверждение — с evidence.

## REUSE-таблица

| Reuse target | Что берёт Intelligence | Evidence | Примечание |
|--------------|----------------------|----------|-----------|
| `MemoryStore` | KO (kind=opportunity/lesson/pattern), граф, confidence | `core_02/memory_store.py` — 10 kinds, `find_related`, `update_feedback` | НЕ создавать вторую memory system |
| `SemanticLayer` | гибридный поиск по KO | `core_02/semantic_layer.py::semantic_search` | UNDERSTAND |
| `LearningLoop` | AFC-обучение + codify (LESSONS.md CON-N) | `core_02/learning_loop.py::capture/codify` | LEARN |
| `EventBus` | публикация/подписка на сигналы | `scripts_01/event_bus.py::EventBus` | НЕ создавать Signal abstraction |
| `ProjectPulse` | OBSERVE (git/file/event timeline) | `scripts_01/project_pulse.py` | — |
| `OpportunityEngine` | lifecycle + персист + DISCOVER | `scripts_01/opportunity_engine.py` | УЖЕ есть — не переписывать |
| `WhimCapture` | input intake + triage | `scripts_01/whim_capture.py` | УЖЕ есть |
| `ScenarioRegistry` | SELECT сценария | `core_02/scenario_registry.py::propose_roles` | — |
| `FactoryRegistry` | capability-резолв | `core_02/factory_registry.py::find_by_capability` | — |
| `ForgeFacade` | EXECUTE | `core_02/forge_facade.py::run_chain` | единственный мост §7.3 |
| `RoleArtifactValidator` | VALIDATE | `core_02/forge_facade.py::RoleArtifactValidator` | — |
| `AnchorResolver` | TRACE + PROVENANCE анкоров | `core_02/anchors_resolver.py` | уже резолвит @opportunity/@whim |
| `MissingRegistry` | register-first для новых элементов | `core_02/missing_registry.py` | — |

## Ключевой REUSE-вывод

**FACT:** Intelligence может опереться на 13 существующих primitives БЕЗ единой новой memory/event/registry системы.
**INFERENCE:** Единственные реальные достройки — 2 адаптера (G1): реальные DISCOVER-источники + запись Opportunity в MemoryStore (ACCUMULATE).
**DECISION:** НЕ строить новый Signal слой — `EventBus.emit` + `ProjectPulse` выразительны достаточно; при необходимости Signal = тонкий mapper над EventBus (не отдельный слой).
