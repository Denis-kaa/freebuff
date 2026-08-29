# 06_EVENT_TRACEABILITY — Событийная трассируемость

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §8 (EVENT FORENSICS)
> **Метод:** для каждого события — publisher / event name / payload / subscribers / side effect / storage / test.

---

## 1. Реальная шина событий

`scripts_01/event_bus.py::EventBus`:
- `publish(event) -> int` (кол-во доставок)
- `subscribe(callback, event_types)` → Subscription
- `unsubscribe(subscription)`
- `get_events(limit, event_type, ...)` — чтение из SQLite (context_12/events.db)
- `get_stats()`, `clear()`
- Хелперы: `task_event`, `step_event`, `memory_event`, `context_event`

**Хранилище:** `context_12/events.db` (SQLite, таблица event_log). Тест: `tests_09/test_event_bus.py`.

## 2. Кто реально публикует (grep evidence)

| Модуль | События |
|--------|---------|
| `scripts_01/event_bus.py` | task_event/step_event/memory_event/context_event (хелперы) |
| `scripts_01/plugin_api.py::PluginRegistry._publish_event` | plugin lifecycle events |
| `core_02/memory_store.py` | memory/learning events (record_learning_event) |
| `scripts_01/orchestrator.py` | task/step events (через event_bus) |
| `scripts_01/telegram_bot.py` | TG-события (notify) |

## 3. Кто реально подписан (grep evidence)

| Модуль | Подписка |
|--------|----------|
| `scripts_01/event_bus.py` | `get_default_event_bus` singleton; пример `on_task_completed` |
| `scripts_01/plugin_api.py::BasePlugin.events_subscribed` | plugin-подписки |
| `scripts_01/event_subscribers.py` | subscriber-хуки (distributed/notification) |

## 4. События, описанные в контрактах, но НЕ публикуемые (DOCUMENTED_ONLY)

Из CONTRACT_REGISTRY §C.5 (26 @event IDs) и INTELLIGENCE_FACTORY_CONTRACT §J:

| Событие | Контракт | Реально публикуется? | Evidence |
|---|---|---|---|
| `opportunity.created/updated/deferred/reactivated` | §J + contract #12 | ❌ НЕТ | grep `opportunity.*` publish в opportunity_engine.py = 0 |
| `opportunity.proposed/advanced/executed` | contract #12 produced | ❌ НЕТ | 0 |
| `whim.captured/classified/promoted/deferred` | §J + contract #13 | ❌ НЕТ | 0 в whim_capture.py |
| `scenario.selected` | §J | ❌ НЕТ | 0 |
| `execution.started/completed/failed` | §J | ❌ НЕТ (в run_chain есть логи, но не EventBus) | 0 в forge_facade.py |
| `artifact.created/validated` | §J | ❌ НЕТ | 0 |
| `forge.chain_started/completed/failed` | contract #1 | ⚠️ PARTIAL | orchestator/forge логи, но не через EventBus.publish с @event ID |

**Вывод:** EventBus **инфраструктурно реализован** (publish/subscribe/хранение/тесты), но **Intelligence-доменные события (opportunity/whim/scenario/execution/artifact) не эмитятся**. Это самый большой разрыв между контрактом и runtime. Зафиксировано в 12_ARCHITECTURAL_CONFLICTS как CONFLICT (contract promises events, code doesn't emit).

## 5. События с разными именами / payload

- `memory_event` хелпер vs `record_learning_event` в memory_store — разные сигнатуры, но оба пишут в learning-логи. Не конфликт, но naming drift (memory_event не используется из opportunity_engine; там `record_learning_event`).

## 6. Рекомендация

Небольшой аддитивный слой: в `opportunity_engine.advance()` и `whim_capture.advance()` добавить `EventBus.publish(Event("opportunity.<transition>", ...))` — закрывает §J и contract #12/#13 produced-списки. Это кандидат в следующий slice (см. 14_NEXT_VERTICAL_SLICE).

---

_Конец 06_EVENT_TRACEABILITY. Переход к 07_ENTRYPOINT_TRACEABILITY._
