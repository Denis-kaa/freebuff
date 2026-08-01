# INDEX — Buffy Documentation

> **Дата:** 2026-07-29
> **Версия:** 1.0.0
> **Стартовая точка:** [VISION_3.0.md***REMOVED***(vision/VISION_3.0.md) → раздел «Три режима работы»

---

## Быстрая навигация

| Категория | Где искать | Что там |
|-----------|-----------|---------|
| **Куда движется система** | [`vision/`***REMOVED***(vision/) | VISION_3.0, ROADMAP, PRODUCT_MANIFESTO |
| **Архитектурные принципы** | [`core/`***REMOVED***(core/) | ARCHITECTURE_PRINCIPLES, CODE_QUALITY_STANDARD, RULES, спецификации |
| **Архитектурные решения** | [`decisions/`***REMOVED***(decisions/) | DECISIONS, ADR |
| **Аудиты системы** | [`audits/`***REMOVED***(audits/) | Хронологические аудиты, DRIFT_REPORT |
| **Engineering Memory** | [`engineering-memory/`***REMOVED***(engineering-memory/) | Архитектура, Книга проекта, шаблоны |
| **Плагин freebuff_plugin** | [`plugin/`***REMOVED***(plugin/) | API, архитектура, Quickstart, Bridge |
| **Интеграции и проекты** | [`projects_meta/`***REMOVED***(projects_meta/) | Lightpanda, Overlay, Workers |
| **Операционная документация** | [`ops/`***REMOVED***(ops/) | Гайды, troubleshooting, шаблоны |

---

## Три режима работы (отправная точка)

См. [`vision/VISION_3.0.md`***REMOVED***(vision/VISION_3.0.md), раздел 2:

| Режим | Суть | Статус |
|-------|------|--------|
| **Single** | Один пользователь, один воркспейс | ✅ Готово |
| **Cowork** | Один пользователь, несколько Runtime | 🟡 Connectivity готов, orchestration — нет |
| **Teamwork** | Несколько пользователей + агентов | 🟡 ACP/Bridge готовы, task assignment — план |

---

## Ключевые документы

| Документ | Путь |
|----------|------|
| **Статусы документации** 🆕 | [`DOCUMENT_REGISTRY.md`***REMOVED***(DOCUMENT_REGISTRY.md) |
| **Vision 3.0** | [`vision/VISION_3.0.md`***REMOVED***(vision/VISION_3.0.md) |
| **Карта компонентов** | [`vision/VISION_3.0_MAP.md`***REMOVED***(vision/VISION_3.0_MAP.md) |
| **Roadmap** | [`vision/ROADMAP.md`***REMOVED***(vision/ROADMAP.md) |
| **Product Manifesto** | [`vision/PRODUCT_MANIFESTO.md`***REMOVED***(vision/PRODUCT_MANIFESTO.md) |
| **Архитектурные принципы** | [`core/ARCHITECTURE_PRINCIPLES.md`***REMOVED***(core/ARCHITECTURE_PRINCIPLES.md) |
| **Runtime Validation** | [`core/RUNTIME_VALIDATION_FRAMEWORK.md`***REMOVED***(core/RUNTIME_VALIDATION_FRAMEWORK.md) |
| **Compatibility Matrix** | [`core/COMPATIBILITY_MATRIX.md`***REMOVED***(core/COMPATIBILITY_MATRIX.md) |
| **Bootstrap Spec** | [`core/BOOTSTRAP_SPECIFICATION.md`***REMOVED***(core/BOOTSTRAP_SPECIFICATION.md) |
| **Event Platform Spec** | [`core/EVENT_PLATFORM_SPECIFICATION.md`***REMOVED***(core/EVENT_PLATFORM_SPECIFICATION.md) |
| **Policy Engine Spec** | [`core/POLICY_ENGINE_SPECIFICATION.md`***REMOVED***(core/POLICY_ENGINE_SPECIFICATION.md) |
| **Session Mesh v2.0 Spec** 🆕 | [`core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md`***REMOVED***(core/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md) |
| **Session Mesh Implementation** 🆕 | [`../pompts_11/017_02_struktura_requirements_testy.md`***REMOVED***(../pompts_11/017_02_struktura_requirements_testy.md) |
| **Code Quality Standard** | [`core/CODE_QUALITY_STANDARD.md`***REMOVED***(core/CODE_QUALITY_STANDARD.md) |
| **Plugin Architecture** | [`plugin/FREEBUFF_PLUGIN_ARCHITECTURE.md`***REMOVED***(plugin/FREEBUFF_PLUGIN_ARCHITECTURE.md) |
| **IDEAS Registry** | [`decisions/IDEAS.md`***REMOVED***(decisions/IDEAS.md) |
| **File Registry** | [`projects_meta/FILE_REGISTRY.md`***REMOVED***(projects_meta/FILE_REGISTRY.md) |
| **Agent Instructions** | [`../AGENTS.md`***REMOVED***(../AGENTS.md) (корневой чекпоинт; ops-дубль → trash_21) |

---

## Для нового участника / агента

1. Начни с [`vision/VISION_3.0.md`***REMOVED***(vision/VISION_3.0.md) — раздел «Три режима работы»
2. Прочитай [`core/ARCHITECTURE_PRINCIPLES.md`***REMOVED***(core/ARCHITECTURE_PRINCIPLES.md)
3. Изучи [`core/CODE_QUALITY_STANDARD.md`***REMOVED***(core/CODE_QUALITY_STANDARD.md) — обязательный стандарт
4. Ознакомься с [`vision/ROADMAP.md`***REMOVED***(vision/ROADMAP.md)
5. Для работы с кодом — см. [`../BUFFY.md`***REMOVED***(../BUFFY.md) и [`../AGENTS.md`***REMOVED***(../AGENTS.md)
