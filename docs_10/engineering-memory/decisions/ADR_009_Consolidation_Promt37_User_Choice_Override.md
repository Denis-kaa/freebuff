# ADR-009: Принятие правила 11 User-Choice Override (promt37)

**Дата:** 2026-08-01
**Статус:** ✅ Принято
**Контекст:** [037_11_user_choice_override.md***REMOVED***(../../../pompts_11/037_11_user_choice_override.md) (аддендум к promt36: 11-й канонический принцип User-Choice Override + уточнение правила 7 DPE), [ADR-008***REMOVED***(ADR_008_Consolidation_Promt36_Canonical_Rules.md) (прецедент встраивания промт-правил), [ARCHITECTURE_MANIFEST.md***REMOVED***(../../core/ARCHITECTURE_MANIFEST.md) §9 (изменения требуют ADR)

## Решение

Встроить правило 11 (User-Choice Override) и уточнение правила 7 (DPE) из `pompts_11/037_11_user_choice_override.md`
в единые источники истины:

- **GLOSSARY.md** (`docs_10/core/GLOSSARY.md`) — секция §11 расширена: заголовок
  «11 канонических правил (promt36 + promt37)», добавлены термины **User-Choice Override**
  (правило 11: система рекомендует, но пользователь выбирает) и **Policy Engine**
  (основа рекомендаций DPE), строка DPE уточнена клаузой «НО: пользователь может
  переопределить выбор в любой момент». В §7 добавлено разграничение
  «Рекомендация DPE vs User-Choice Override» (рекомендация ≠ принуждение).
- **ARCHITECTURE_MANIFEST.md** (`docs_10/core/ARCHITECTURE_MANIFEST.md`) — принцип 18
  **User-Choice Override** и анти-паттерн «Навязывать пользователю модель/агента
  без возможности переопределения».

## Обоснование

- Правило 11 закрывает критическое упущение promt36: пользовательский контроль
  над выбором исполнителя (модель/агент на каждую capability) — ключевая часть
  философии «множество провайдеров + бесплатные ключи».
- Уточнение правила 7: DPE — **рекомендующий** делегатор, а не принуждающий;
  финальное решение всегда за пользователем.
- Существующий код уже покрывает ~80% механизма: `scripts_01/model_gateway.py`
  (6 провайдеров), `core_02/router.py` (capability-based routing), `scripts_01/roles.py`
  (RoleEngine), `freebuff_plugin_03/policy/` (Policy Engine) — принцип фиксирует
  поведение, а не добавляет новую фичу (Mission Lock промта 32 соблюдён).

## Последствия

- Термины User-Choice Override и Policy Engine становятся каноническими;
  новые документы обязаны их использовать.
- Запрещено навязывать пользователю модель/агента без возможности переопределения.
- Изменение определений — архитектурное решение, требует нового ADR (GLOSSARY §1.4).

## Отложено (после консолидации)

- Хранение пользовательских предпочтений (User Preferences: `config.yaml` /
  MemoryLevel.PERSONAL) и CLI для назначения моделей на capabilities (promt37 Phase 3).
- Механизм переопределения в рантайме («используй X вместо Y») — после
  завершения консолидации (Mission Lock промта 32).

---

_Связанные документы: [GLOSSARY.md***REMOVED***(../../core/GLOSSARY.md) §11/§7, [ARCHITECTURE_MANIFEST.md***REMOVED***(../../core/ARCHITECTURE_MANIFEST.md) §2/§7, [ADR-007***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md), [ADR-008***REMOVED***(ADR_008_Consolidation_Promt36_Canonical_Rules.md), [DECISIONS.md***REMOVED***(../../decisions/DECISIONS.md) (индекс ADR), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../../vision/ROADMAP_PROMT32_CONSOLIDATION.md) Этап 5_
