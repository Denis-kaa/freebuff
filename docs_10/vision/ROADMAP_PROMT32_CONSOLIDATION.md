# Roadmap: Workspace OS Consolidation (Promt 32)

**Version:** 2.2.0
**Date:** 2026-07-31 (обновлено 2026-08-01: промты 42/43)
**Status:** ✅ Consolidation Complete — **Mission Lock снят (2026-08-01)**
**Source:** `pompts_11/032_09_workspace_os_konsolidaciya.md`
**Supersedes feature roadmap order:** `docs_10/vision/ROADMAP_PROMT31_WORKSPACE_OS.md`

---

## 0. Mission Lock (главное правило) — 🔓 СНЯТ 2026-08-01

> ~~**Запрещено добавлять новые пользовательские возможности**, пока не завершена консолидация.~~
> ~~Source of Truth должен быть один.~~

**Решение архитектора (2026-08-01):** все этапы 1–10 консолидации завершены,
проверки зелёные (drift_check / consistency_check / doctor / тесты), поэтому **Mission Lock снят**
и начаты пост-консолидационные задачи — см. `docs_10/core/ARCHITECTURAL_DEBT.md`
(DEBT-001…007) и Этап 10 §6 `docs_10/core/FINAL_STRUCTURE.md`.

Историческая справка (до снятия):
- ~~Wire real git/system publishers~~ → отложить до консолидации (это новая функциональность)
- ~~Build integration registry~~ → частично входит в Этап 9 (самоконсистентность), но как часть консолидации, не как фича
- ~~Generate module registry~~ → частично входит в Этап 6 (консолидация модулей)

Исключения (во время действия лока): изменения, необходимые непосредственно для консолидации
(реестры, проверки, манифест, глоссарий, lifecycle-документация).

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
| Этап 1. Полный аудит | `docs_10/audits/ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md` | ✅ Stage 1 выполнен (`docs_10/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md`) |
| Этап 2. Каноническая архитектура | — | ✅ Создана (`docs_10/core/ARCHITECTURE_CANONICAL.md`) |
| Этап 4. Консолидация документации | promt31 4.4 (DECISIONS merge — done), `scripts_01/drift_check.py` | ✅ Выполнен (`docs_10/DOCUMENT_REGISTRY.md`) |
| Этап 6. Консолидация модулей | promt31 4.6 (Module Registry), 4.7 (Agent Registry) | ✅ Аудит выполнен (`docs_10/core/MODULE_CONSOLIDATION.md`) |
| Этап 9. Самоконсистентность | `scripts_01/drift_check.py` + `scripts_01/consistency_check.py` (реестры как данные) | ✅ Выполнен |
| Этап 5. Консолидация промтов | `AGENTS.md` / `BUFFY.md` / `CLAUDE.md` / `CODY.md` / `.cursorrules` (5 файлов!) | ✅ Выполнен (Core Prompt, дубли 34/35, promt36+promt37, ревизия pompts_11/ 35 файлов, 5 артефактов → trash_21/) |
| Этап 3. Архитектурный манифест | — | ✅ Создан (`docs_10/core/ARCHITECTURE_MANIFEST.md`) |
| Этап 7. Единая терминология | — | ✅ Создан глоссарий (`docs_10/core/GLOSSARY.md`) |
| Этап 8. Lifecycle | promt31 4.9 (lifecycle events) | ✅ Создан реестр (`docs_10/core/LIFECYCLE.md`) |
| Этап 10. Финальная структура | — | ✅ Создан итоговый синтез (`docs_10/core/FINAL_STRUCTURE.md`) |

**Вывод:** часть работы promt31 (Phase A: notification, DECISIONS merge, ARCHITECTURAL_DEBT) уже выполнена и совпадает с Этапами 4/9. **Все этапы promt32 (1–10) завершены** (2026-08-01) — консолидация закрыта; **Mission Lock снят** и начаты пост-консолидационные задачи. Долги: DEBT-001/002/005/006 ✅ Resolved, остаются DEBT-003/004/007 (см. `docs_10/core/ARCHITECTURAL_DEBT.md`). **Отложенные канонические шаги promt36/37 реализованы кодом (2026-08-01):** Work Area as View, User Preferences CLI (правило 11), Context-Aware Routing (правило 8), Plugin Contract Specification (правило 9) — подробности в Этапе 10 §6 (`docs_10/core/FINAL_STRUCTURE.md`). **Следующие миссии promt42/promt43 (документация+Meeting Tasks, позиционирование Teamwork, фронтенд) — §9.**

---

## 4. Этапы выполнения (порядок)

### Этап 1 — Полный аудит ✅ (начат)
- [x***REMOVED*** Собраны факты (модули, документы, промты, дубли, мёртвые файлы)
- [x***REMOVED*** Отчёт: `docs_10/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md`

### Этап 2 — Каноническая архитектура ✅
- [x***REMOVED*** Определена единая структура Workspace OS (`docs_10/core/ARCHITECTURE_CANONICAL.md`)
- [x***REMOVED*** Для каждого компонента: назначение, ответственность, зависимости, lifecycle, владелец
- [x***REMOVED*** Устранены неоднозначности (RAG=фича Knowledge, Metrics/Pulse/Drift разделены, RoleEngine-DI)
- [x***REMOVED*** Выявлен критический долг: тесты для 6 движков отсутствуют (→ ARCHITECTURAL_DEBT)

### Этап 3 — Архитектурный манифест ✅
- [x***REMOVED*** Создан `docs_10/core/ARCHITECTURE_MANIFEST.md`
- [x***REMOVED*** Миссия платформы, принципы, правила, границы ответственности
- [x***REMOVED*** Манифест = главный архитектурный закон (приоритет над остальными документами)

### Этап 4 — Консолидация документации ✅
- [x***REMOVED*** Создан единый реестр статусов: `docs_10/DOCUMENT_REGISTRY.md` (ACTIVE / LEGACY / ARCHIVED / DRAFT / OBSOLETE для всех документов)
- [x***REMOVED*** Удалены `.bak` файлы: `pompts_11/038_03_audit_prompt.md.bak`, `docs_10/core/CODE_QUALITY_STANDARD.md.bak`
- [x***REMOVED*** Статус-баннеры добавлены в LEGACY-документы (ARCHITECTURE_3.0, ARCHITECTURE_REVIEW, ROADMAP.md)
- [x***REMOVED*** `docs_10/INDEX.md` — добавлена ссылка на реестр

**Отклонение от формулировки:** пункт «Устаревшие — в архив (не удалять), актуальные — переписать»
выполнен как **назначение статусов в месте расположения** (реестр `docs_10/DOCUMENT_REGISTRY.md`),
а не физический перенос файлов: физическое перемещение документов с входящими
markdown-ссылками сломало бы link-checker `scripts_01/drift_check.py` (CI).
История сохранена, ничего не удалено (кроме `.bak`).

### Этап 5 — Консолидация промтов 🟡 Частично
- [x***REMOVED*** Единый **Core Prompt** существует: `docs_10/core/CORE_PROMPT.md` (личность, обязанности, ограничения, поведение)
- [x***REMOVED*** Все 5 файлов инструкций (`AGENTS.md`, `BUFFY.md`, `CLAUDE.md`, `CODY.md`, `.cursorrules`) ссылаются на Core Prompt как источник истины (проверено; правка внесена только в `AGENTS.md` — остальные 4 уже были выверены ранее)
- [x***REMOVED*** Дубль промтов устранён: идентичная копия промта 34 (файл 35 в pompts_11/) удалена — остался единственный DPE-промт
- [x***REMOVED*** Канонические правила promt36 (Work Area as View, 10 правил) встроены в `docs_10/core/GLOSSARY.md` (§11) и `docs_10/core/ARCHITECTURE_MANIFEST.md` (принципы 14–17, анти-паттерны)
- [x***REMOVED*** Правило 11 (User-Choice Override) и уточнение правила 7 (DPE) из `pompts_11/037_11_user_choice_override.md` встроены: GLOSSARY §11 (термины User-Choice Override, Policy Engine; клауза «пользователь может переопределить выбор» в DPE; разграничение в §7), MANIFEST (принцип 18 + анти-паттерн «навязывать модель») — ADR-009
- [x***REMOVED*** `AGENTS.md` актуализирован (v5.25.1, статус консолидации)
- [x***REMOVED*** Полная ревизия файлов в `pompts_11/` выполнена: классификация пофайловая (ACTIVE 18 / LEGACY 17; 5 артефактов OBSOLETE → `trash_21/`) зафиксирована в `docs_10/DOCUMENT_REGISTRY.md`; опечатка CODE_QUALITY_STANDART → STANDARD исправлена (git mv + 5 ссылок); пустые freb / promt18 и артефакты error / new / structure перенесены в `trash_21/` (Этап 5); байт-дублей правил не выявлено (после устранения 34/35)

### Этап 6 — Консолидация модулей ✅
- [x***REMOVED*** Аудит выполнен: `docs_10/core/MODULE_CONSOLIDATION.md` — 10 областей (Router, Telegram, MCP, Memory, Knowledge, Registry, Context, Tool Runtime, Plugin API, EventBus)
- [x***REMOVED*** Матрица 10 движков проверена по импортам — пересечений ответственности нет
- [x***REMOVED*** 1 реальный дубль найден (Telegram: 2 бота) → передан в ARCHITECTURAL_DEBT
- [x***REMOVED*** Осознанные повторы зафиксированы с причиной (Router-слои, Registry-паттерн, Plugin-терминология)

### Этап 7 — Единая терминология ✅
- [x***REMOVED*** Глоссарий создан: `docs_10/core/GLOSSARY.md` (Workspace, Project, Module, Agent, Tool, Plugin, Connector, Integration, Knowledge, Memory, Project Book, Engineering Memory, Lifecycle, Registry, Decision Log, Pulse)
- [x***REMOVED*** Разрешённые неоднозначности и запрещённые синонимы зафиксированы
- [x***REMOVED*** Единые определения связаны с Manifest / ARCHITECTURE_CANONICAL / CORE_PROMPT

### Этап 8 — Lifecycle ✅
- [x***REMOVED*** Реестр создан: `docs_10/core/LIFECYCLE.md` — 7 стадий для Core C1–C6 + State S1–S7 + инфраструктурные слои
- [x***REMOVED*** Эталонные паттерны зафиксированы (graceful shutdown, миграции, lazy init, graceful degradation)
- [x***REMOVED*** Правило: компонент без описанного Lifecycle запрещён к регистрации в SYSTEM_INVENTORY

### Этап 9 — Самоконсистентность ✅
- [x***REMOVED*** Создан `scripts_01/consistency_check.py` — авто-проверка: файлы движков из реестра, покрытие LIFECYCLE, области MODULE_CONSOLIDATION, термины GLOSSARY, ссылки ROADMAP, взаимные ссылки канонических документов
- [x***REMOVED*** Реестры как данные: ARCHITECTURE_CANONICAL / LIFECYCLE / MODULE_CONSOLIDATION / GLOSSARY / ROADMAP
- [x***REMOVED*** Подключен в `scripts_01/doctor.py` (проверка Consistency) и CI (`.github/workflows/pytest.yml`, шаг consistency_check)

### Этап 10 — Финальная структура ✅
- [x***REMOVED*** Создан итоговый синтез: `docs_10/core/FINAL_STRUCTURE.md` — архитектурная схема (слои Core/Extensions/State/Labs, режимы масштабирования, 11 канонических правил), каноническая структура каталогов, сводный реестр компонентов (→ SYSTEM_INVENTORY)
- [x***REMOVED*** Зафиксирован список архивированных/обновлённых документов и удалённых дублей (promt35, .bak, опечатка CODE_QUALITY_STANDART→STANDARD; статусы из DOCUMENT_REGISTRY)
- [x***REMOVED*** Перечислены 9 принятых ADR (ADR-001…009) + оставшиеся задачи (долги DEBT-001…007, Phase B/C, отложенные шаги promt36/37)

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
- [x***REMOVED*** код, документация и промты полностью согласованы (drift_check green, consistency_check green);
- [x***REMOVED*** существует `docs_10/core/ARCHITECTURE_MANIFEST.md`;
- [x***REMOVED*** существует единый Core Prompt;
- [x***REMOVED*** устранены критические дублирования;
- [x***REMOVED*** вся документация имеет статус ACTIVE/LEGACY/ARCHIVED (реестр `docs_10/DOCUMENT_REGISTRY.md`);
- [x***REMOVED*** создан план автоматической проверки консистентности.

---

## 8. Связанные документы

- `pompts_11/032_09_workspace_os_konsolidaciya.md` — оригинал миссии
- `docs_10/audits/CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md` — Stage 1 аудит
- `docs_10/vision/ROADMAP_PROMT31_WORKSPACE_OS.md` — roadmap фич (возобновится после консолидации)
- `docs_10/core/ARCHITECTURAL_DEBT.md` — реестр долгов
- `pompts_11/042_06_dokumentaciya_meeting_tasks.md` — миссия 9.1/9.2 (документация + Meeting Tasks + Teamwork-позиционирование)
- `pompts_11/043_08_frontend_workspace_os_ui.md` — миссия 9.3 (фронтенд Workspace OS)

---

## 9. Пост-консолидационные миссии: promt42 / promt43 (2026-08-01)

Mission Lock снят, поэтому промты 42/43 — следующие шаги развития. Статусы ниже
зафиксированы по фактическому состоянию репозитория (2026-08-01).

### Миссия 9.1 — Документация + Meeting Tasks (promt42, часть 1)

| Фаза | Задача | Статус |
|------|--------|--------|
| A | `docs_10/vision/VISION_3.0.md`: разделы 8–11 (Client Portal, Meeting Intelligence & Task Types, Telegram as Sensor Network, Cross-Workspace Analysis) | 🟡 Частично — Teamwork-режим уже есть (§3), разделы 8–11 отсутствуют |
| B | `docs_10/core/GLOSSARY.md`: Work Area as View, DPE, TaskAnalyzer, Client Portal, Meeting Task, AFC | 🟡 Частично — DPE/TaskAnalyzer/Policy уже есть; Work Area as View, Meeting Task, AFC, Client Portal — нет |
| C | `docs_10/core/ARCHITECTURE_MANIFEST.md`: разделы 19–22 (AFC Protocol, Manifest Versioning Rules, Definition of Done, Backward Compatibility) | ❌ Нет (манифест содержит 18 принципов, разделы 19–22 отсутствуют) |
| D | Таблица `tasks` в `data_13/context.db` (task_type, meeting_time, location, participants, briefing_generated) | ❌ Нет |
| E | Модуль task_manager.py в scripts_01/ + CLI + тесты в tests_09/ (создаются в рамках миссии) | ❌ Нет |

### Миссия 9.2 — Стратегическое позиционирование Teamwork (promt42, часть 2)

| Фаза | Задача | Статус |
|------|--------|--------|
| A | `docs_10/vision/VISION_3.0.md`: раздел «Оркестратор, а не конкурент» (Teamwork = ниша; Single/Cowork — необходимый минимум; «Всё есть Артефакт») | ❌ Нет |
| B | `docs_10/core/GLOSSARY.md`: Worksheet, Project Vault, Cross-Project Intelligence, Agent Integration Contract | ❌ Нет |
| C | Документ AGENT_INTEGRATION_CONTRACT.md в docs_10/core/ (правила чтения/записи/изоляции/статусов для внешних агентов; создаётся в рамках миссии) | ❌ Нет |

### Миссия 9.3 — Frontend Workspace OS (promt43)

| Фаза | Задача | Статус |
|------|--------|--------|
| A | React + TypeScript (Vite) + Tailwind + framer-motion + @dnd-kit + lucide-react | ❌ Нет (в `frontend_18/` только `BuffyDashboard.tsx`) |
| B | Glassmorphism UI: бургер-меню, карточки проектов и задачи с drag-and-drop, AI-панель | ❌ Нет |
| C | Интеграция с FastAPI (`scripts_01/mcp_fastapi.py`, порт 8000) + мок-фолбэк при недоступности бэкенда | ❌ Нет |
