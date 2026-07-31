# Roadmap: Workspace OS Consolidation (Promt 32)

**Version:** 1.0.0
**Date:** 2026-07-31
**Status:** Active — Mission Lock
**Source:** `pompts/promt32.md`
**Supersedes feature roadmap order:** `docs/vision/ROADMAP_PROMT31_WORKSPACE_OS.md`

---

## 0. Mission Lock (главное правило)

> **Запрещено добавлять новые пользовательские возможности**, пока не завершена консолидация.
> Source of Truth должен быть один.

Это касается и ранее предложенных шагов:
- ~~Wire real git/system publishers~~ → отложить до консолидации (это новая функциональность)
- ~~Build integration registry~~ → частично входит в Этап 9 (самоконсистентность), но как часть консолидации, не как фича
- ~~Generate module registry~~ → частично входит в Этап 6 (консолидация модулей)

Исключения: изменения, необходимые непосредственно для консолидации (реестры, проверки, манифест, глоссарий, lifecycle-документация).

---

## 1. Миссия

Привести проект из стадии активного проектирования в стадию **зрелой инженерной платформы**:

- код, документация, архитектура, промты и внутренняя логика — единое целое;
- ни одного «второго источника истины»;
- если архитектура изменилась → документация изменилась;
- если появился модуль → Registry знает о нём;
- если удалён компонент → все ссылки актуализированы;
- система не противоречит самой себе.

---

## 2. Принципы (из promt32 + promt31)

| Принцип | Источник |
|---------|----------|
| Reuse First. Extend Second. Create Last. | promt31 |
| Single Source of Truth | promt32 |
| Event Driven | promt32 |
| Documentation First | promt32 |
| Project State First | promt32 |
| Engineering Memory | promt32 |
| Backward Compatibility | promt32 |
| Минимизация дублирования | promt32 |
| Расширяемость и масштабируемость | promt32 |

---

## 3. Пересечение с текущей работой (проверено)

| Этап promt32 | Пересекается с | Статус |
|--------------|----------------|--------|
| Этап 1. Полный аудит | `ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md` | ✅ Stage 1 выполнен (`docs/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md`) |
| Этап 2. Каноническая архитектура | — | ✅ Создана (`docs/core/ARCHITECTURE_CANONICAL.md`) |
| Этап 4. Консолидация документации | promt31 4.4 (DECISIONS merge — done), `drift_check.py` | 🟡 Частично |
| Этап 6. Консолидация модулей | promt31 4.6 (Module Registry), 4.7 (Agent Registry) | 🟡 Частично |
| Этап 9. Самоконсистентность | `drift_check.py` + markdown link check (сделаны) | 🟡 Частично |
| Этап 5. Консолидация промтов | `AGENTS.md` / `BUFFY.md` / `CLAUDE.md` / `CODY.md` / `.cursorrules` (5 файлов!) | 🔴 Не начато |
| Этап 3. Архитектурный манифест | — | ✅ Создан (`docs/core/ARCHITECTURE_MANIFEST.md`) |
| Этап 7. Единая терминология | — | ✅ Создан глоссарий (`docs/core/GLOSSARY.md`) |
| Этап 8. Lifecycle | promt31 4.9 (lifecycle events) | 🔴 Не начато |

**Вывод:** часть работы promt31 (Phase A: notification, DECISIONS merge, ARCHITECTURAL_DEBT) уже выполнена и совпадает с Этапами 4/9. Остальные этапы promt32 — новый фронт работ.

---

## 4. Этапы выполнения (порядок)

### Этап 1 — Полный аудит ✅ (начат)
- [x***REMOVED*** Собраны факты (модули, документы, промты, дубли, мёртвые файлы)
- [x***REMOVED*** Отчёт: `docs/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md`

### Этап 2 — Каноническая архитектура ✅
- [x***REMOVED*** Определена единая структура Workspace OS (`docs/core/ARCHITECTURE_CANONICAL.md`)
- [x***REMOVED*** Для каждого компонента: назначение, ответственность, зависимости, lifecycle, владелец
- [x***REMOVED*** Устранены неоднозначности (RAG=фича Knowledge, Metrics/Pulse/Drift разделены, RoleEngine-DI)
- [x***REMOVED*** Выявлен критический долг: тесты для 6 движков отсутствуют (→ ARCHITECTURAL_DEBT)

### Этап 3 — Архитектурный манифест ✅
- [x***REMOVED*** Создан `docs/core/ARCHITECTURE_MANIFEST.md`
- [x***REMOVED*** Миссия платформы, принципы, правила, границы ответственности
- [x***REMOVED*** Манифест = главный архитектурный закон (приоритет над остальными документами)

### Этап 4 — Консолидация документации
- [ ***REMOVED*** Присвоить каждому документу статус: ACTIVE / LEGACY / ARCHIVED / DRAFT / OBSOLETE
- [ ***REMOVED*** Устаревшие — в архив (не удалять), актуальные — переписать
- [ ***REMOVED*** Удалить `.bak` файлы (`pompts/AUDIT_PROMPT.md.bak`, `docs/core/CODE_QUALITY_STANDARD.md.bak`)

### Этап 5 — Консолидация промтов
- [ ***REMOVED*** Выделить единый **Core Prompt** (личность, обязанности, ограничения, поведение Buffy)
- [ ***REMOVED*** Остальные промты — расширяют Core Prompt, не переопределяют
- [ ***REMOVED*** Удалить дубли/устаревшие/конфликтующие правила (37 файлов в `pompts/`)
- [ ***REMOVED*** Устранить расхождение: `AGENTS.md`, `BUFFY.md`, `CLAUDE.md`, `CODY.md`, `.cursorrules`

### Этап 6 — Консолидация модулей
- [ ***REMOVED*** Проверить: Router, Telegram, MCP, Memory, Knowledge, Registry, Context, Tool Runtime, Plugin API, EventBus
- [ ***REMOVED*** Дубли → объединить / оформить как адаптеры / задокументировать причину
- [ ***REMOVED*** 8 движков в `scripts/`: MemoryEngine, KnowledgeEngine, EMEngine, RAGEngine, CollaborationEngine, PresenceEngine, RoleEngine, MetricsEngine — проверить пересечение

### Этап 7 — Единая терминология ✅
- [x***REMOVED*** Глоссарий создан: `docs/core/GLOSSARY.md` (Workspace, Project, Module, Agent, Tool, Plugin, Connector, Integration, Knowledge, Memory, Project Book, Engineering Memory, Lifecycle, Registry, Decision Log, Pulse)
- [x***REMOVED*** Разрешённые неоднозначности и запрещённые синонимы зафиксированы
- [x***REMOVED*** Единые определения связаны с Manifest / ARCHITECTURE_CANONICAL / CORE_PROMPT

### Этап 8 — Lifecycle
- [ ***REMOVED*** Для каждого ключевого компонента: создание, инициализация, работа, обновление, завершение, архивация, удаление
- [ ***REMOVED*** Ни один компонент без описанного Lifecycle

### Этап 9 — Самоконсистентность
- [ ***REMOVED*** Механизм авто-проверки: дрейф, устаревшая документация, битые ссылки, дубли, неиспользуемые модули, несоответствие Roadmap/Registry/Project Book
- [ ***REMOVED*** Реестры (Module/Agent/Integration) — как данные для проверки
- [ ***REMOVED*** Подключить CI / `doctor.py`

### Этап 10 — Финальная структура
- [ ***REMOVED*** Архитектурная схема, структура каталогов, реестр компонентов
- [ ***REMOVED*** Список архивированных/обновлённых документов, удалённых дублей
- [ ***REMOVED*** Принятые ADR + список оставшихся задач

---

## 5. Порядок относительно ROADMAP_PROMT31_WORKSPACE_OS.md

1. **Сначала** — Этапы 1–10 консолидации (promt32).
2. **После консолидации** — возобновить Phase B/C фичи (publishers, registries, lifecycle FSM, Project Book compile, Architecture Map).
3. Этапы 4/6/9 частично вбирают в себя Phase B пункты 5–7 (registries) — их делать в рамках консолидации, а не как фичи.

---

## 6. Ограничения

- Запрещено добавлять новые пользовательские функции.
- Запрещено менять поведение системы без необходимости.
- Запрещено переписывать рабочий код ради красоты.
- Запрещено удалять историю проекта.
- Все изменения обратимы, безопасны, с обоснованием.

---

## 7. Критерий завершения

Консолидация завершена, когда:
- [ ***REMOVED*** код, документация и промты полностью согласованы;
- [ ***REMOVED*** существует `ARCHITECTURE_MANIFEST.md`;
- [ ***REMOVED*** существует единый Core Prompt;
- [ ***REMOVED*** устранены критические дублирования;
- [ ***REMOVED*** вся документация имеет статус ACTIVE/LEGACY/ARCHIVED;
- [ ***REMOVED*** создан план автоматической проверки консистентности.

---

## 8. Связанные документы

- `pompts/promt32.md` — оригинал миссии
- `docs/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md` — Stage 1 аудит
- `docs/vision/ROADMAP_PROMT31_WORKSPACE_OS.md` — roadmap фич (возобновится после консолидации)
- `docs/core/ARCHITECTURAL_DEBT.md` — реестр долгов
