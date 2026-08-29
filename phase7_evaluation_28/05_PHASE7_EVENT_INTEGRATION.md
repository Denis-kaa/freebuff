# 05_PHASE7_EVENT_INTEGRATION.md — Event Closure (Task C)

> Phase 7 §8 (TASK C — EVENT CLOSURE) + §9 (EVENT CONTRACT) + §10 (FEEDBACK LOOP).

## Canonical EventBus

Используется существующий `scripts_01/event_bus.py` (`EventBus.publish(event) -> int`,
`Event(type, source, data)`). **НЕ создана вторая event schema** (§9).

## `_emit_event` (scripts_01/opportunity_engine.py)

```python
def _emit_event(event_bus, event_type, *, source, **payload) -> None:
    if event_bus is None: return          # hermetic default
    event_bus.publish(Event(type=event_type, source=source, data=dict(payload)))
```

Best-effort: событие никогда не ломает lifecycle (try/except).

## Реально публикуемые события (producers)

| Событие | Producer | Payload |
|---------|----------|---------|
| `execution.started` | `execute()` | opportunity_id, project_id, role_ids, factory_selection |
| `execution.completed` | `execute()` | opportunity_id, project_id, overall |
| `execution.failed` | `execute()` (exception / degrade) | opportunity_id, project_id, reason |
| `opportunity.deferred` | `advance(DEFERRED)` | opportunity_id, project_id, previous_status, reason |
| `opportunity.reactivated` | `advance(REACTIVATED)` | opportunity_id, project_id, previous_status, reason |
| `opportunity.completed` | `advance(COMPLETED)` | opportunity_id, project_id, previous_status, reason |
| `opportunity.failed` | `advance(FAILED)` | opportunity_id, project_id, previous_status, reason |
| `scenario.selected` | `propose()` | opportunity_id, project_id, scenario_id, role_id, score |
| `whim.captured` | `whim_capture.capture()` | whim_id, project_id, whim_source, body |
| `whim.classified` | `whim_capture.triage()` | whim_id, project_id, classification, reason |
| `whim.promoted` | `whim_capture.promote()` | whim_id, project_id, opportunity_id |
| `whim.deferred` | `whim_capture.defer()` | whim_id, project_id, reason |

## Consumers

- **CLI execution path** (`_cli_run`) — `_make_cli_event_bus()` (get_default_event_bus) публикует события реального прогона; dry-run — нет (hermetic).
- События читаемы из `EventBus.get_events()` (SQLite storage) — проверено `test_execute_with_real_eventbus`.
- Feedback loop (§10): OPPORTUNITY → EXECUTION → EVENT → MEMORY/KNOWLEDGE → INTELLIGENCE — техническая возможность создана; автономный feedback engine НЕ реализован (deferred, §10).

## Тесты (Task C)

| Тест | Проверяет |
|------|-----------|
| `test_execute_emits_execution_events` | execution.started/completed + payload |
| `test_execute_emits_execution_failed_on_exception` | execution.failed + opportunity.failed |
| `test_advance_emits_lifecycle_events` | opportunity.deferred/reactivated/completed |
| `test_propose_emits_scenario_selected` | scenario.selected (real propose, hermetic registry) |
| `test_whim_capture_emits_captured` | whim.captured |
| `test_whim_triage_emits_classified_single` | whim.classified (ровно один, без дублей) |
| `test_whim_promote_emits_promoted` | whim.promoted + opportunity_id |
| `test_emit_event_real_eventbus_roundtrip` | реальный EventBus (tmp db) publish→get_events |
| `test_execute_with_real_eventbus` | lifecycle-события читаемы из реального лога |
| `test_execute_degrade_path_emits_execution_failed` | degrade-путь: execution.failed, НЕ execution.completed |

---
_EventBus-интеграция подтверждена. События реально публикуются и читаемы._
