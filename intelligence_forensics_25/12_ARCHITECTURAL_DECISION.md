# 12 — ARCHITECTURAL DECISION

> Финальный однозначный вывод (промт §22). Без «что выбрать?».

## DECISION

**Мы должны:**
1. Строить Intelligence Layer как **тонкий integration-слой поверх 13 существующих primitives** (OpportunityEngine, WhimCapture, ScenarioRegistry, FactoryRegistry, ForgeFacade, MemoryStore, SemanticLayer, LearningLoop, EventBus, ProjectPulse, AnchorResolver, MissingRegistry, RoleArtifactValidator).
2. Закрыть **2 адаптера (G1)** как первый implementation-шаг:
   - GAP-1: реальные DISCOVER-источники (whims.yaml TRIAGED + ProjectPulse + MemoryStore observations) вместо STUB.
   - GAP-2: ACCUMULATE — `execute()` пишет `MemoryStore.store_knowledge(kind="opportunity")` + `LearningLoop.record_feedback`.
3. Зарегистрировать **Opportunity Contract + Whim Contract** в `CONTRACT_REGISTRY_V1.md` (GAP-4/GAP-5).
4. Использовать **AnchorResolver `@opportunity`/`@whim`** для TRACE/PROVENANCE — уже готово.

**Потому что:**
- Opportunity Engine и Whim Capture УЖЕ реализованы и покрыты тестами (68 passed) — переписывать = нарушение Additive Architecture (CAN-16).
- Memory/Knowledge/Event/Observation/Forge — все уже есть; единственные реальные gaps — 2 адаптера + 2 контракт-регистрации.
- ForgeFacade.run_chain — единственный мост §7.3; Intelligence обязан идти через него, а не обходить.

**Мы НЕ должны:**
- Создавать вторую memory/event/registry/forge/scheduler/plugin/MCP систему.
- Создавать Signal abstraction (EventBus + ProjectPulse достаточно).
- Строить Concept Evolution System сейчас (это G3, deferred).
- Смешивать Intelligence с Factory, а Concept Evolution — с Project Intelligence.

**Следующий шаг:**
Implementation-промт на закрытие GAP-1 + GAP-2 (+ GAP-4/5 doc) — точечные правки `scripts_01/opportunity_engine.py` и `scripts_01/whim_capture.py` по CAN-16 ADDITIVE, без изменения ForgeFacade/ScenarioRegistry/MemoryStore/LearningLoop.

## Обоснование по промт §22

- Рекомендация сделана на forensic evidence (не задан вопрос пользователю).
- Формат DECISION соблюдён: «Мы должны / Потому что / Мы НЕ должны / Следующий шаг».
