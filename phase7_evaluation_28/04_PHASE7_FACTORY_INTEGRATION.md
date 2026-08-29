# 04_PHASE7_FACTORY_INTEGRATION.md — Factory Closure (Task B)

> Phase 7 §6 (TASK B — FACTORY CLOSURE) + §7 (FACTORY CONTRACT).

## Целевой путь (после Phase 7)

```
Opportunity
   ↓
Scenario selection (propose → scenario.selected)
   ↓
FactoryRegistry
   ↓
select_forge(capability)
   ↓
Forge (passport)
   ↓
ForgeFacade (EXECUTION BOUNDARY — §16)
   ↓
Artifact → Memory / EventBus
```

## Ключевые символы (scripts_01/opportunity_engine.py)

| Символ | Назначение |
|--------|------------|
| `_derive_capability(opp)` | capability token: `provenance.capability` → `scenario.capability` → None (закрытый словарь ANTI-6b) |
| `_select_factory_forge(opp, factory_registry=None)` | `FactoryRegistry.select_forge(capability)` → `(FactoryPassport, ForgePassport)` или None (fail-safe) |
| `_resolve_project(opp, project_root=None)` | Project-объект: project_root → `projects_17/<id>` → None; sanitize project_id (§16 path traversal) |
| `execute(...)` | Opportunity → Factory selection → ForgeFacade.run_chain(Project, role_ids) |

## execute() — фактический call graph (GAP A closure)

```
execute(opp, *, dry_run, memory_store, learning_loop, project_root, factory_registry, event_bus)
 ├─ dry_run → READY + provenance.dry_run (без Factory/Forge)
 ├─ normalize: COMPLETED→noop; DEFERRED→REACTIVATED→ACTIVE; ACTIVE/FAILED→READY
 ├─ _select_factory_forge(opp, factory_registry)
 │    ├─ _derive_capability(opp) → cap | None
 │    └─ FactoryRegistry.select_forge(cap) → (fp, fg) | None
 ├─ provenance['factory_selection'***REMOVED*** = {factory_id, forge_id, capability***REMOVED*** | {fallback: True***REMOVED***
 ├─ _resolve_project(opp, project_root) → Project | None
 ├─ _emit_event(execution.started)
 ├─ ForgeFacade() → facade.run_chain(project, role_ids=...)
 │    └─ (existing bridge, §7.3 — ForgeFacade остаётся единственным execution boundary)
 ├─ success → advance(COMPLETED) + _emit_event(execution.completed)
 └─ exception → advance(FAILED) + _emit_event(execution.failed)   [never raises***REMOVED***
```

## Backward compatibility

- Нет capability / FactoryRegistry / совпадения → **fallback dict**
  `provenance['factory_selection'***REMOVED*** = {fallback: True***REMOVED***` → существующий pipeline путь.
- `ForgeFacade` по-прежнему инстанцируется и вызывается через `run_chain` —
  **НЕ создан второй execution mechanism** (§17).
- `event_bus=None` (default) → события не публикуются (hermetic, backward compat).

## Тесты (Task B)

| Тест | Проверяет |
|------|-----------|
| `test_derive_capability_from_provenance/scenario/none` | capability resolution |
| `test_select_factory_forge_routes_by_capability` | select_forge(capability) вызван |
| `test_select_factory_forge_none_without_capability` | fail-safe None, registry не инстанцируется |
| `test_execute_records_factory_selection_and_runs_chain` | factory_selection provenance + run_chain |
| `test_execute_factory_fallback_backward_compat` | fallback dict при отсутствии capability |
| `test_execute_passes_project_object_not_string` | GAP A fix: Project-объект (не строка) |

---
_Opportunity больше НЕ обходит Factory. ForgeFacade остаётся execution boundary._
