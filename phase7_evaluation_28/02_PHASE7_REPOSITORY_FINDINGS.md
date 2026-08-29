# 02_PHASE7_REPOSITORY_FINDINGS.md — Repository Forensics / Findings

> Phase 7 §1 (обязательное предварительное исследование) + §2 (baseline = Phase 6 package).

## Method

Repository-first: evidence из кода (`grep`/AST/read), НЕ из документации. Каждый
GAP подтверждён реальным символом/вызовом/тестом.

## GAP A — Opportunity → ForgeFacade напрямую, минуя Factory selection

**Evidence (baseline, `scripts_01/opportunity_engine.py`):**
- `execute()` вызывал `ForgeFacade.run_chain(opp.project_id, role_ids=...)` — строкой,
  без Factory selection.
- `run_chain` в `core_02/forge_facade.py` — **instance method**; классовый вызов
  строкой был багом real-path (Project-объект не резолвился).
- `FactoryRegistry` (`core_02/factory_registry.py`, Missing Cap #1, status=implemented)
  существовал, но не был подключён к Opportunity execution path.

**Impact:** Opportunity обходила Factory (нарушение целевой архитектуры §4:
OPPORTUNITY → SCENARIO → FACTORY → FACTORY SELECTION → FORGE → FORGE FACADE).

**Closure (Task B):** `execute()` теперь:
1. резолвит **Project-объект** (`_resolve_project` — project_root → `projects_17/<id>` → None);
2. вызывает **Factory selection** (`_select_factory_forge` → `FactoryRegistry.select_forge(capability)`);
3. записывает `provenance['factory_selection'***REMOVED***` (factory_id/forge_id/capability или fallback);
4. инстанцирует `ForgeFacade()` и вызывает `facade.run_chain(project, role_ids)` — **ForgeFacade остаётся единственным execution boundary (§16)**.

## GAP B — Intelligence lifecycle не интегрирован с EventBus

**Evidence (baseline):**
- `advance()`, `execute()`, `propose()`, `whim_capture.capture/triage/promote/defer`
  не публиковали события (grep EventBus в этих функциях = 0).
- Контракты §J/§K (INTELLIGENCE_FACTORY_CONTRACT_V1.md) декларировали
  `opportunity.deferred/reactivated/completed/failed`, `execution.*`, `scenario.selected`,
  `whim.*` — но события были **planned, не emitted** (CONTRACT_REGISTRY §C.6 #5).

**Closure (Task C):** добавлен `_emit_event()` (best-effort, `event_bus=None` → no-op,
canonical `EventBus`/`Event` из `scripts_01/event_bus.py` — НЕ вторая event schema §9).
Реально публикуются (см. 05):
- `execution.started` / `execution.completed` / `execution.failed` (execute);
- `opportunity.deferred` / `opportunity.reactivated` / `opportunity.completed` / `opportunity.failed` (advance);
- `scenario.selected` (propose);
- `whim.captured` / `whim.classified` / `whim.promoted` / `whim.deferred` (whim_capture).

## GAP C — расхождение Opportunity contract / documentation / runtime schema

**Evidence:**
- `INTELLIGENCE_FACTORY_CONTRACT_V1.md` §E — 15-полевая design-схема
  (`signal/hypothesis/rationale/related_knowledge/selected_scenario/resulting_artifact`).
- Runtime `Opportunity` dataclass — **24 поля** (другие имена + lifecycle audit-поля + priority).
- CONTRACT_REGISTRY §C.6 drift #5 фиксировал расхождение (2026-08-16).

**Closure (Task A):** каноническая схема = **implementation** (24 поля).
§E обновлён + добавлена таблица design→runtime mapping (§E.1). Drift #5 CLOSED.
См. 03_PHASE7_CONTRACT_RECONCILIATION.md.

## Прочие findings (не GAP, зарегистрированы)

- Реальный `EventBus.Event(type, source, data)` сигнатура совпадает с `_emit_event`
  (проверено интеграционным тестом `test_emit_event_real_eventbus_roundtrip`).
- `promote()` в whim_capture пишет в `OpportunityStore(DEFAULT_DATA_PATH)` — тесты
  герметизированы monkeypatch'ем `DEFAULT_DATA_PATH` на tmp (без pollution data_13/).
- `ScenarioRegistry()` конструктор грузит реальные манифесты и может варнировать на
  `vkusvill_demo.yaml` (unknown scenario_type 'teamwork') — тесты герметизированы
  подменой `sys.modules['core_02.scenario_registry'***REMOVED***` (паттерн `_mock_forge_facade`).

---
_3 GAP подтверждены evidence и закрыты (A→Task B, B→Task C, C→Task A)._
