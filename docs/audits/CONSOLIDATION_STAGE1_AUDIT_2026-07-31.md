# Consolidation Stage 1 — Full Audit

**Дата:** 2026-07-31
**Миссия:** `pompts/promt32.md` — Workspace OS Consolidation
**Статус:** Отчёт по результатам анализа (этап 1 из 10)
**Метод:** Факты из кодовой базы, документации, файловой системы (без изменений кода)

---

## 1. Что реализовано (движки и системы)

Проверено по `scripts/` — классы `*Engine`:

| Движок | Файл | Назначение |
|--------|------|-----------|
| `MemoryEngine` | `scripts/memory_engine.py` | 6 уровней памяти + VectorBackend |
| `KnowledgeEngine` | `scripts/knowledge_engine.py` | FTS5 + TF-IDF, канонический индексатор |
| `EMEngine` | `scripts/engineering_memory.py` | Engineering Memory (драфты, ADR-индекс) |
| `RAGEngine` | `scripts/rag_engine.py` | 5 режимов поиска + RRF |
| `CollaborationEngine` | `scripts/collaboration.py` | коллаборативные сессии |
| `PresenceEngine` | `scripts/presence.py` | присутствие агентов |
| `RoleEngine` | `scripts/roles.py` | роли и capabilities |
| `MetricsEngine` | `scripts/metrics.py` | VCR/SRG/CpVO/RRR/TTD |

Плюс: `EventBus`, `Orchestrator`, `ContextManager`, `ToolRuntime`, `PluginAPI`, `ProjectPulse`, `NotificationManager`, `ProgressTracker`, `AgentMesh/TaskDistributor/DistributedCoordinator`, `ScenarioEngine`, `BridgeLayer`, `RuntimeRegistry`.

## 2. Что осталось концепцией / устарело

- `docs/core/ARCHITECTURE_REVIEW.md`, `docs/core/ARCHITECTURE_3.0.md`, `docs/core/ARCHITECTURE_PRINCIPLES.md` — три архитектурных документа без взаимной сверки; требуют статуса.
- `docs/vision/archive/VISION_2.0.md` — статус ARCHIVED.
- `promt31` roadmap: Phase B/C пункты (registries, lifecycle FSM, Project Book compile, Architecture Map) — ещё не реализованы, но **заморожены** mission lock'ом promt32.
- `buffy-playground/`, `frontend/BuffyDashboard.tsx` — UI-артефакты без явного статуса (активные/экспериментальные?).

## 3. Устаревшие документы

- `docs/DRIFT_REPORT.md` — фиксирует «ghost dirs» (`02-specs`, `audits`, `ops`, `plugin`, `projects_meta`, `vision`), которых нет в описанном виде; при этом активные директории (`buffy-playground`, `cli`, `frontend`, `infa`) отсутствуют в документации проекта. **Важно:** отчёт может быть устаревшим относительно недавно обновлённого `drift_check.py` (ADR redirects, link checker) — требует перепрогона перед интерпретацией.
- `docs/session_dumps/` и `docs/task_archive/` — исторические архивы (статус: ARCHIVED по определению, но не помечены).

## 4. Дублирования

### 4.1 Дублирование правил в промтах
Один и тот же набор правил (Code Quality Standard, Reuse First, Engineering Memory) встречается минимум в 6 файлах:
- `pompts/AUDIT_PROMPT.md`
- `pompts/CODE_QUALITY_STANDART.md` (внимание: опечатка в имени — STANDART вместо STANDARD)
- `pompts/promt25.md`, `promt26.md`, `promt31.md`, `promt32.md`

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

- `docs/DRIFT_REPORT.md` сообщает о несуществующих директориях, хотя `docs/audits`, `docs/ops`, `docs/plugin`, `docs/projects_meta`, `docs/vision` физически существуют (проверено: audits=18 файлов, core=18, engineering-memory=18, ops=11, vision=7, projects_meta=5, plugin=4). Скорее всего отчёт устарел относительно текущего `drift_check.py`, чем реально противоречит файловой системе — требует перепрогона.
- Опечатка `CODE_QUALITY_STANDART.md` (в `pompts/`) vs `docs/core/CODE_QUALITY_STANDARD.md` — два имени одной сущности.

## 6. Мёртвые файлы и каталоги

- `pompts/AUDIT_PROMPT.md.bak` — бэкап, подлежит удалению (Этап 4).
- `docs/core/CODE_QUALITY_STANDARD.md.bak` — бэкап, подлежит удалению (Этап 4).
- `trash/`, `screenshots/` — каталоги без явного назначения в документации.
- `__pycache__/` в корне — артефакт; проверить покрытие в `.gitignore`.
- 37 файлов в `pompts/` — нумерация промтов неоднородна (promt1–32 + отдельные файлы `new.md`, `structure.md`, `freb.md`, `error.md`, `TERMINAL_AI_STUDIO_MOBILE.md`).

## 7. Инвентаризация документации (факты)

| Каталог | Файлов |
|---------|--------|
| `docs/audits` | 18 |
| `docs/core` | 18 |
| `docs/engineering-memory` | 18 |
| `docs/ops` | 11 |
| `docs/vision` | 7 |
| `docs/projects_meta` | 5 |
| `docs/plugin` | 4 |
| `docs/decisions` | 3 |
| `docs/session_dumps` | 3 |
| `docs/task_archive` | 2 |

Дубликатов имён спецификаций в `docs/core/*.md` нет; дублирования MCP-спецификаций между `docs/core/` и `docs/plugin/` не обнаружено.

## 8. Что уже сделано и совпадает с консолидацией

- `DECISIONS.md` → отдельные ADR + индекс (Этап 4 частично).
- `drift_check.py` + markdown link checker (Этап 9 частично).
- `ARCHITECTURAL_DEBT.md` (Этап 9 база).
- EM auto-triggers + NotificationManager (инфраструктура для события, не фича).

---

## Рекомендованный следующий шаг

Перейти к **Этапу 2 (Каноническая архитектура)** и **Этапу 5 (Консолидация промтов)** — они устраняют самые дорогие дублирования (5 файлов инструкций, 37 промтов, дубли правил). Этап 3 (Манифест) — после фиксации канонической архитектуры.
