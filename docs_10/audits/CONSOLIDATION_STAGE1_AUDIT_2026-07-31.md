# Consolidation Stage 1 — Full Audit

**Дата:** 2026-07-31
**Миссия:** `pompts_11/032_09_workspace_os_konsolidaciya.md` — Workspace OS Consolidation
**Статус:** Отчёт по результатам анализа (этап 1 из 10)
**Метод:** Факты из кодовой базы, документации, файловой системы (без изменений кода)

---

## 1. Что реализовано (движки и системы)

Проверено по `scripts_01/` — классы `*Engine`:

| Движок | Файл | Назначение |
|--------|------|-----------|
| `MemoryEngine` | `scripts_01/memory_engine.py` | 6 уровней памяти + VectorBackend |
| `KnowledgeEngine` | `scripts_01/knowledge_engine.py` | FTS5 + TF-IDF, канонический индексатор |
| `EMEngine` | `scripts_01/engineering_memory.py` | Engineering Memory (драфты, ADR-индекс) |
| `RAGEngine` | `scripts_01/rag_engine.py` | 5 режимов поиска + RRF |
| `CollaborationEngine` | `scripts_01/collaboration.py` | коллаборативные сессии |
| `PresenceEngine` | `scripts_01/presence.py` | присутствие агентов |
| `RoleEngine` | `scripts_01/roles.py` | роли и capabilities |
| `MetricsEngine` | `scripts_01/metrics.py` | VCR/SRG/CpVO/RRR/TTD |

Плюс: `EventBus`, `Orchestrator`, `ContextManager`, `ToolRuntime`, `PluginAPI`, `ProjectPulse`, `NotificationManager`, `ProgressTracker`, `AgentMesh/TaskDistributor/DistributedCoordinator`, `ScenarioEngine`, `BridgeLayer`, `RuntimeRegistry`.

## 2. Что осталось концепцией / устарело

- `docs_10/core/ARCHITECTURE_REVIEW.md`, `docs_10/core/ARCHITECTURE_3.0.md`, `docs_10/core/ARCHITECTURE_PRINCIPLES.md` — три архитектурных документа без взаимной сверки; требуют статуса.
- `docs_10/vision/archive/VISION_2.0.md` — статус ARCHIVED.
- `promt31` roadmap: Phase B/C пункты (registries, lifecycle FSM, Project Book compile, Architecture Map) — ещё не реализованы, но **заморожены** mission lock'ом promt32.
- `buffy-playground_19/`, `frontend_18/BuffyDashboard.tsx` — UI-артефакты без явного статуса (активные/экспериментальные?).

## 3. Устаревшие документы

- `docs_10/DRIFT_REPORT.md` — фиксирует «ghost dirs» (`02-specs`, `audits`, `ops`, `plugin`, `projects_meta`, `vision`), которых нет в описанном виде; при этом активные директории (`buffy-playground`, `cli`, `frontend`, `infa`) отсутствуют в документации проекта. **Важно:** отчёт может быть устаревшим относительно недавно обновлённого `drift_check.py` (ADR redirects, link checker) — требует перепрогона перед интерпретацией.
- `docs_10/session_dumps/` и `docs_10/task_archive/` — исторические архивы (статус: ARCHIVED по определению, но не помечены).

## 4. Дублирования

### 4.1 Дублирование правил в промтах
Один и тот же набор правил (Code Quality Standard, Reuse First, Engineering Memory) встречается минимум в 6 файлах:
- `pompts_11/038_03_audit_prompt.md`
- `pompts_11/CODE_QUALITY_STANDARD.md` (опечатка в имени STANDART→STANDARD исправлена в Этапе 5)
- `pompts_11/025_02_principy_agenta.md`, `026_05_engineering_memory.md`, `031_03_arhitekturnyy_audit.md`, `032_09_workspace_os_konsolidaciya.md`

### 4.2 Множественные агентские инструкции
5 корневых файлов инструкций с разным объёмом и содержанием:
| Файл | Размер | Роль |
|------|--------|------|
| `AGENTS.md` | 9 KB | инструкции агентов |
| `BUFFY.md` | 23 KB | главный документ Buffy |
| `CLAUDE.md` | 0.5 KB | для Claude Code |
| `CODY.md` | 0.5 KB | для Cody |
| `.cursorrules` | 0.8 KB | для Cursor |

### 4.3 Движки: возможное пересечение
- `RAGEngine` vs `KnowledgeEngine.search(mode=...)` — RAG уже реализован внутри KnowledgeEngine? Требуется проверка границ (Этап 6).
- `MetricsEngine`, `ProjectPulse`, `drift_check` — три механизма «состояния проекта», границы не формализованы.
- `RoleEngine` vs `presence.metadata` vs `AgentMesh` — три источника данных об агентах.

## 5. Противоречия

- `docs_10/DRIFT_REPORT.md` сообщает о несуществующих директориях, хотя `docs_10/audits`, `docs_10/ops`, `docs_10/plugin`, `docs_10/projects_meta`, `docs_10/vision` физически существуют (проверено: audits=18 файлов, core=18, engineering-memory=18, ops=11, vision=7, projects_meta=5, plugin=4). Скорее всего отчёт устарел относительно текущего `drift_check.py`, чем реально противоречит файловой системе — требует перепрогона.
- Опечатка `CODE_QUALITY_STANDART.md` (в `pompts_11/`) vs `docs_10/core/CODE_QUALITY_STANDARD.md` — два имени одной сущности (устранена в Этапе 5: переименован в `CODE_QUALITY_STANDARD.md`).

## 6. Мёртвые файлы и каталоги

- `pompts_11/038_03_audit_prompt.md.bak` — бэкап, подлежит удалению (Этап 4).
- `docs_10/core/CODE_QUALITY_STANDARD.md.bak` — бэкап, подлежит удалению (Этап 4).
- `trash_21/`, `screenshots_16/` — каталоги без явного назначения в документации.
- `__pycache__/` в корне — артефакт; проверить покрытие в `.gitignore`.
- 37 файлов в `pompts_11/` — нумерация промтов неоднородна (promt1–32 + отдельные файлы `new.md`, `structure.md`, `freb.md`, `error.md`, `039_12_terminal_ai_studio_mobile.md`).

## 7. Инвентаризация документации (факты)

> Счётчики зафиксированы на момент аудита, до добавления артефактов этого отчёта.

| Каталог | Файлов |
|---------|--------|
| `docs_10/audits` | 18 |
| `docs_10/core` | 18 |
| `docs_10/engineering-memory` | 18 |
| `docs_10/ops` | 11 |
| `docs_10/vision` | 7 |
| `docs_10/projects_meta` | 5 |
| `docs_10/plugin` | 4 |
| `docs_10/decisions` | 3 |
| `docs_10/session_dumps` | 3 |
| `docs_10/task_archive` | 2 |

Дубликатов имён спецификаций в `docs_10/core/*.md` нет; дублирования MCP-спецификаций между `docs_10/core/` и `docs_10/plugin/` не обнаружено.

## 8. Что уже сделано и совпадает с консолидацией

- `DECISIONS.md` → отдельные ADR + индекс (Этап 4 частично).
- `drift_check.py` + markdown link checker (Этап 9 частично).
- `ARCHITECTURAL_DEBT.md` (Этап 9 база).
- EM auto-triggers + NotificationManager (инфраструктура для события, не фича).

---

## Рекомендованный следующий шаг

Перейти к **Этапу 2 (Каноническая архитектура)** и **Этапу 5 (Консолидация промтов)** — они устраняют самые дорогие дублирования (5 файлов инструкций, 37 промтов, дубли правил). Этап 3 (Манифест) — после фиксации канонической архитектуры.
