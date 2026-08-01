# ADR-008: Принятие канонических правил Workspace OS (promt36)

**Дата:** 2026-08-01
**Статус:** ✅ Принято
**Позднее расширен:** [ADR-009***REMOVED***(ADR_009_Consolidation_Promt37_User_Choice_Override.md) — правило 11 (User-Choice Override) + уточнение правила 7 (DPE) (promt37)
**Контекст:** [036_09_full_consolidation_pipeline.md***REMOVED***(../../../pompts_11/036_09_full_consolidation_pipeline.md) (10 канонических правил Workspace OS), [ARCHITECTURE_MANIFEST.md***REMOVED***(../../core/ARCHITECTURE_MANIFEST.md) §9 (изменения требуют ADR)

## Решение

Встроить канонические правила доменной модели Workspace OS из `pompts_11/036_09_full_consolidation_pipeline.md`
в единые источники истины:

- **GLOSSARY.md** (`docs_10/core/GLOSSARY.md`) — новая секция §11 «Доменная модель
  Workspace OS (10 канонических правил, promt36)»: Workstation, Workspace (сфера),
  Project (цель), Work Area (as View, не сущность), Resource, Squad, Workspace Owner,
  DPE, TaskAnalyzer, Context-Aware Task Routing, Presence-aware Auto-delegation,
  Knowledge as Byproduct, Plugin Contract Specification, режимы работы
  (SINGLE/COWORK/TEAM/COMMUNITY). Плюс 2 разграничения в §7 и 2 запрещённых синонима в §8.
- **ARCHITECTURE_MANIFEST.md** (`docs_10/core/ARCHITECTURE_MANIFEST.md`) — принципы 14–17:
  Context-Aware Task Routing, Role-based Context Isolation, Presence-aware
  Auto-delegation, Knowledge as a Byproduct; и 3 анти-паттерна (задача без проверки
  контекста, комплексная задача одним агентом, «Заметки» как точка входа).

## Обоснование

- Правила промта 36 — это каноническая доменная модель, которую промт 32 (Этап 5)
  предписывает консолидировать в единые реестры.
- GLOSSARY и MANIFEST — единственные источники истины для терминов и принципов
  (Single Source of Truth).
- Физическая реализация (Work Area as View: таблица `project_resources`, CLI-команда)
  отложена до завершения консолидации (Mission Lock промта 32) — см. ADR.

## Последствия

- Термины promt36 становятся каноническими; новые документы обязаны их использовать.
- Work Area зафиксирован как **View**, а не сущность/папка (разрешённая неоднозначность §7).
- Изменение определений — архитектурное решение, требует нового ADR (GLOSSARY §1.4).

## Отложено (после консолидации)

- Work Area as View: таблица `project_resources` + CLI `freebuff resource projects` (promt36 Phase 3).
- DPE-маршрутизация в `orchestrator.py` (promt34).
- Plugin Contract Specification (promt36 правило 9 — термин зафиксирован, документ позже).

---

_Связанные документы: [GLOSSARY.md***REMOVED***(../../core/GLOSSARY.md) §11, [ARCHITECTURE_MANIFEST.md***REMOVED***(../../core/ARCHITECTURE_MANIFEST.md) §2/§7, [ADR-007***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md), [ADR-009***REMOVED***(ADR_009_Consolidation_Promt37_User_Choice_Override.md) (правило 11), [DECISIONS.md***REMOVED***(../../decisions/DECISIONS.md) (индекс ADR), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../../vision/ROADMAP_PROMT32_CONSOLIDATION.md) Этап 5_
