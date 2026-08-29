# 14_NEXT_VERTICAL_SLICE — Следующий минимальный implementation slice

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §17 (FIND NEXT SLICE) + §25 (FINAL DECISION)
> **Метод:** один минимальный vertical slice: INPUT → DECISION → EXECUTION → ARTIFACT → MEMORY → FEEDBACK. Минимум новых файлов.

---

## 1. FINAL DECISION: **B — READY AFTER CONTRACT RECONCILIATION**

Платформа в целом зрелая (15/16 контрактов CURRENT), но есть 2 контрактных promises, которые код не выполняет:
1. **CONFLICT-2:** Intelligence-доменные события (`opportunity.*`, `whim.*`) не эмитятся.
2. **CONFLICT-3:** Factory→Forge соединение (`select_forge`) не подключено к `opportunity_engine.execute`.

Оба — малые аддитивные изменения, закрывающие существующие контракты. После них платформа готова к следующему содержательному slice.

## 2. РЕКОМЕНДУЕМЫЙ СЛЕДУЮЩИЙ SLICE: «Factory-путь + event-эмиссия в Intelligence-цикле»

**Один вертикальный slice, который закрывает оба конфликта:**

```
INPUT      → opportunity_engine discover (уже есть)
DECISION   → select_forge(capability) из FactoryRegistry  [NEW — подключить***REMOVED***
EXECUTION  → ForgeFacade.run_chain (через выбранный forge)  [уже есть, маршрутизировать***REMOVED***
ARTIFACT   → RoleArtifactValidator (уже есть)
MEMORY     → accumulate → MemoryStore (уже есть)
FEEDBACK   → EventBus.publish(opportunity.*, execution.*)  [NEW — emit в advance/execute***REMOVED***
```

## 3. Новые файлы (минимально)

| Файл | WHY | OWNER | DEPENDENCIES | INTERFACE | TEST | REMOVAL CONDITION |
|------|-----|-------|--------------|-----------|------|-------------------|
| (НЕТ нового файла — аддитивные правки в 2 существующих) | | | | | | |
| `scripts_01/opportunity_engine.py` (правка) | подключить select_forge + emit событий | opportunity_engine | FactoryRegistry (lazy), EventBus (lazy) | `execute()` маршрутизирует через `select_forge`; `advance()`/`execute()` публикуют события | `test_opportunity_engine.py` + `test_intelligence_loop_phase5.py` | если Factory-путь признан ненужным |
| `scripts_01/whim_capture.py` (правка) | emit whim.* событий в advance | whim_capture | EventBus (lazy) | `advance()` публикует `whim.<transition>` | `test_whim_capture.py` | если событийность не нужна |

**Новых файлов: 0.** Правки: 2 существующих модуля (аддитивно, CAN-16). Это минимальный vertical slice.

## 4. Скоуп (что именно)

1. **`opportunity_engine.execute()`**: перед `run_chain` — `FactoryRegistry.select_forge(capability)` (capability из opp.scenario/roles); если найден forge — использовать его `forge_id` как подсказку для role_ids; если нет — fallback на текущий pipeline (backward-compat).
2. **`opportunity_engine.advance()` + `execute()`**: `EventBus.publish(Event("opportunity.<from>→<to>", {opportunity_id, project_id, ...***REMOVED***))` — закрывает §J + contract #12 produced.
3. **`whim_capture.advance()`**: `EventBus.publish(Event("whim.<transition>", ...))` — закрывает contract #13 produced.
4. **Тесты**: регрессионные — select_forge-маршрутизация (mock FactoryRegistry) + event emission (mock EventBus, assert publish called).

## 5. Почему именно этот slice

- **Закрывает 2 реальных контрактных конфликта** (не roadmap-фича).
- **Минимален**: 0 новых файлов, 2 правки существующих, аддитивно (CAN-16).
- **Разблокирует Factory-путь** (C-2 из 09_FUTURE_GAPS уже реализован как select_forge — осталось подключить).
- **Улучшает observability** (события → event_log → DISCOVER-источник для следующего цикла).
- **Вертикален**: INPUT (discover) → DECISION (select_forge) → EXECUTION (run_chain) → ARTIFACT (validator) → MEMORY (accumulate) → FEEDBACK (events).

## 6. Что НЕ входит (намеренно)

- НЕ Content Intelligence / Concept Evolution (roadmap-треки, требуют отдельные промты).
- НЕ Scenario Engine (design_ready, отдельный промт).
- НЕ MCP/TG entrypoints для opportunity (CONFLICT-5 — следующий, отдельный шаг).
- НЕ reconcile §E (CONFLICT-1 — doc-only, отдельный шаг).

---

_Конец 14_NEXT_VERTICAL_SLICE. Переход к 15_EXECUTIVE_SUMMARY._
