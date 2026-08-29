# 06 — GAP MAP

> G0 = already exists · G1 = adapter/integration · G2 = contract extension · G3 = new primitive · G4 = architectural conflict.

## GAP-таблица

| ID | Gap | Класс | Description | Evidence | Why existing insufficient | Minimal solution | Dependencies | Risk |
|----|-----|-------|-------------|----------|--------------------------|------------------|--------------|------|
| GAP-1 | Реальные DISCOVER-источники | **G1** | `discover_candidates` генерирует STUB-кандидатов (по одному на source), а не реальные pulls | `opportunity_engine.py::discover_candidates` — `title="Stub signal from {src***REMOVED***"`, `provenance={"stub": True***REMOVED***` | STUB не даёт реальных сигналов из whims/pulse/knowledge | заменить STUB на реальные pulls: `WhimStore` (TRIAGED), `ProjectPulse.list`, `MemoryStore.query_by_type(kind="observation")` | whim_capture, project_pulse, memory_store | Средний |
| GAP-2 | ACCUMULATE в MemoryStore | **G1** | docstring заявляет «ACCUMULATE (memory_store KO kind=opportunity + Learning Loop capture)», но `execute()` НЕ пишет в MemoryStore | `opportunity_engine.py::execute` — только `advance(COMPLETED)` + `artifacts`, нет `store_knowledge` | Opportunity не попадает в граф знаний → LEARN не срабатывает | `execute()` → `MemoryStore.store_knowledge(kind="opportunity", ...)` + `LearningLoop.record_feedback` | memory_store, learning_loop | Средний |
| GAP-3 | Opportunity↔Project↔Workspace lineage | **G1** | `Opportunity.project_id` есть, но нет интеграции с `WorkspaceRegistry` (owner_chat_id, workspace_id) | `opportunity_engine.py::Opportunity.project_id` | lineage неполон: opportunity не знает workspace | опциональный adapter: связать `project_id` с `WorkspaceRegistry.get` | workspace_registry | Низкий |
| GAP-4 | Opportunity Contract в реестре | **G2** | 16 полей dataclass не зарегистрированы в CONTRACT_REGISTRY_V1.md | `opportunity_engine.py::Opportunity` | контракт невидим для контрактного слоя | зарегистрировать §E Opportunity Contract | doc-only | Низкий |
| GAP-5 | Whim Contract в реестре | **G2** | Whim schema не в CONTRACT_REGISTRY_V1.md | `whim_capture.py::Whim` | контракт невидим | зарегистрировать §17.1 Whim Contract | doc-only | Низкий |
| GAP-6 | Concept Evolution System | **G3** | отсутствует (grep 0) | — | единственный реально новый intelligence-компонент | НЕ строить сейчас — только точка интеграции (§13) | future | Низкий (deferred) |
| GAP-7 | Opportunity.execute docstring↔code drift | **G4** | docstring (module header) заявляет ACCUMULATE, код не реализует | `opportunity_engine.py` header vs `execute` | doc/code расхождение вводит в заблуждение | закрыть GAP-2 (реализовать ACCUMULATE) либо исправить docstring | GAP-2 | Низкий |

## GAP-вывод

**FACT:** 5 из 7 gap — адаптеры/контракты (G1/G2), НЕ новые примитивы.
**FACT:** Только Concept Evolution (GAP-6) — реальный новый primitive (G3), и он deferred.
**FACT:** GAP-7 (G4) — не архитектурный конфликт, а doc/code drift, закрывается GAP-2.
**DECISION:** Минимальный implementation path = GAP-1 (реальные DISCOVER) + GAP-2 (ACCUMULATE) + GAP-4/GAP-5 (контракты в реестр). GAP-3/GAP-6 — опционально/deferred.

## Статус закрытия (v5.189.15)

- **GAP-4 / GAP-5 → CLOSED** (2026-08-16): контракты Opportunity (§E, 24 поля dataclass) и Whim (§17.1, 21 поле dataclass) зарегистрированы в `CONTRACT_REGISTRY_V1.md` как #15 `opportunity.schema` / #16 `whim.schema`.
- **Register-first:** capability `intelligence_integration` → `prompt_written` (промт 084) в `data_13/missing_registry.yaml`; §20 карта row #17.
- Остаются открытыми: GAP-1 (реальные DISCOVER-источники), GAP-2 (ACCUMULATE в MemoryStore), GAP-3 (lineage, низкий), GAP-6 (Concept Evolution, deferred), GAP-7 (закрывается GAP-2).
