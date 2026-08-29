# 07 — DOCUMENTATION ↔ CODE DRIFT

> Аудит «документация описывает несуществующий код / код отсутствует в документации / противоречивые lifecycle».

## D1. Найденные drift-ы

| # | DOC CLAIM | CODE REALITY | STATUS | ACTION |
|---|-----------|--------------|--------|--------|
| D-1 | `opportunity_engine.py` module header: «ACCUMULATE (memory_store KO kind=opportunity + Learning Loop capture)» | `execute()` НЕ вызывает `MemoryStore.store_knowledge`, только `advance(COMPLETED)` | **CONTRADICTORY** | реализовать ACCUMULATE (GAP-2) ИЛИ исправить header |
| D-2 | Промт 084 §3: «НЕ реализуй Opportunity Engine / Whim UI» | Opportunity Engine (`opportunity_engine.py`) и Whim (`whim_capture.py`) УЖЕ реализованы (v5.188+) | **OBSOLETE ARCHITECTURE** | обновить презумпцию: не «проектировать», а «интегрировать» |
| D-3 | Промт 084 §1: «Scheduler» в списке Phase 4 | отдельного `Scheduler`-класса нет; есть `task_manager.py`, `prompt_queue.py`, `prompt_dispatcher.py` | **DUPLICATED TERMINOLOGY / CLAIM WITHOUT EVIDENCE** | уточнить: диспетчеризация есть, «Scheduler» как имя отсутствует |
| D-4 | `anchors_resolver.py` header: «19-namespace» | 17 @-namespace в `ANCHOR_RE` + `doc.*` (17+1), но в `_NAMESPACE_ORDER` = все ключи (18: 17 @ + doc). Термин «19» из spec §I.3 (включает requirement/scenario/… в полном списке) | **MINOR DRIFT (counting)** | не блокирует; зафиксировать точный счёт в spec |
| D-5 | `opportunity_engine.py` docstring: «lifecycle в YAML, content в MemoryStore KO (CONTRACT §E)» | content в MemoryStore НЕ реализован (только YAML lifecycle) | **CONTRADICTORY** (тот же root, что D-1) | GAP-2 |

## D2. Код, отсутствующий в документации

| # | CODE | STATUS |
|---|------|--------|
| D-6 | `scripts_01/whim_capture.py` — Whim lifecycle (NEW→TRIAGED→PROMOTED_TO_OPPORTUNITY/DISCARDED) | не отражён в CONTRACT_REGISTRY_V1.md |
| D-7 | `scripts_01/opportunity_engine.py` — 16-полей Opportunity dataclass | не отражён в CONTRACT_REGISTRY_V1.md |
| D-8 | `Opportunity.SOURCES` = (whim, project_pulse, event_bus, knowledge, hand) | не задокументирован как контракт входов DISCOVER |

## D3. Противоречивые lifecycle-определения

**FACT:** `opportunity_engine.py` `TERMINAL_STATUSES = ("COMPLETED",)` — FAILED retry-allowed.
**FACT:** `whim_capture.py` `TERMINAL_STATUSES = ("PROMOTED_TO_OPPORTUNITY", "DISCARDED")` — FAILED → NEW retry.
**FACT:** Оба соответствуют своим промтам (079_19 §3.1 #7, 080_19 §3.3) — **НЕТ противоречия** между ними, но есть риск смешения понятий «terminal» между Opportunity (только COMPLETED) и Whim (2 terminal).

## D4. Вывод

**FACT:** Главный drift — D-1/D-5: Opportunity ACCUMULATE заявлен в docstring, не реализован в коде.
**FACT:** Вторичный drift — D-2: презумпция промта 084 устарела (Opportunity/Whim уже существуют).
**DECISION:** D-1/D-5 закрываются GAP-2; D-2/D-3 — обновление документации (этот пакет + CONTRACT_REGISTRY).
