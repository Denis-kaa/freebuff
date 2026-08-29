# RFC BUFFY FORGE v1.1 — Архитектурная метасистема Buffy (+Workspace/Project)

| Поле | Значение |
|------|----------|
| **RFC ID** | RFC-BF-001 |
| **Версия** | 1.2 |
| **Статус** | 📋 RFC (v1.1: Альтернатива A из ARB-REV-001) |
| **Релиз платформы** | v5.97.0 |
| **Дата** | 2026-08-05 |
| **Автор** | Buffy (promt56: синтез; promt57→promt58: ARB-вердикт REJECT WITH ALTERNATIVE → Альтернатива A) |
| **Предшественники** | RFC OM v1 (v5.92.0), RFC OM Evolution v1.1 (v5.93.0), RFC DIS v1 (v5.94.0), ARB Constitution (054), AG Constitution (055), ARB-REV-001 (v5.96.0) |
| **Тип** | Meta-Architecture / Platform Design |
| **Затрагивает** | Все подсистемы Buffy |

---

## 0. Architectural Fit Check (AFC)

### Что уже существует в production

| Компонент | Статус | Где |
|-----------|--------|-----|
| `KnowledgeEngine` (FtsIndex, TfidfIndex, SemanticIndex) | ✅ Production | `scripts_01/knowledge_engine.py` |
| `GraphIndex` (7 rel_types) | ✅ Production | `scripts_01/graph_index.py` |
| `context.db` (10+ таблиц: arch_decisions, invariants, sessions, messages, ...) | ✅ Production | `data_13/context.db` |
| `events.db` (event_log, event_store, event_fts) | ✅ Production | `context_12/events.db` |
| `knowledge/index.db` (FTS5 + embeddings) | ✅ Production | `context_12/knowledge/` |
| `EventBus` + `prompt_dispatcher.py` | ✅ Production | `scripts_01/prompt_dispatcher.py` |
| `LESSONS.md` (~46 CON/ANTI/CAN уроков) | ✅ Production | `core_02/LESSONS.md` |
| `drift_check.py` | ✅ Production | `scripts_01/drift_check.py` |
| `IDEAS.md` | ✅ Production | `docs_10/decisions/IDEAS.md` |

### Что уже спроектировано (RFC, ждёт реализации)

| Компонент | Статус | Документ |
|-----------|--------|----------|
| Organizational Memory Engine (10 типов KO, Memory Store, Knowledge Graph +9 rel_types) | 📋 RFC | `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` (v5.92.0) |
| Evolution v1.1 (12 improvements: Authority, DecisionTrace, Policy, Conflict, Versioning, ...) | 📋 RFC | `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md` (v5.93.0) |
| Decision Intelligence System (ARE, CAE, TDA, PC, EP, RFC Reviewer — 6 компонентов) | 📋 RFC | `RFC_DECISION_INTELLIGENCE_SYSTEM_V1.md` (v5.94.0) |
| Architecture Review Board (конституция: 10-шаговый анализ, 6 вердиктов) | 📋 Constitution | `054_17_arb_architecture_review_board.md` |
| Architecture Governance (конституция: compliance, drift, 5 вердиктов) | 📋 Constitution | `055_18_ag_architecture_governance.md` |

### Проблема

Пять RFC/конституций описывают компоненты, но **нет единой карты**, показывающей как они связаны. Нет документа, который бы ответил на вопросы:

- Forge — это подсистема, уровень архитектуры или метасистема?
- Как OM, DIS, ARB и AG взаимодействуют?
- Где границы между ними?
- Есть ли дублирование ответственности?
- Какой жизненный цикл у архитектурного знания?

Настоящий RFC даёт ответы на все эти вопросы.

---

## 1. Назначение

Buffy Forge — **метасистема проектирования и управления архитектурой платформы Buffy**. Это не подсистема, не уровень и не компонент. Это **зонтичная платформа**, объединяющая весь жизненный цикл архитектурного знания:

```
Идея → Знание → Архитектура → Реализация → Валидация → Эволюция → Идея
```

Forge отвечает не на вопрос «как реализовать X?», а на вопрос **«как Buffy проектирует, принимает, контролирует и эволюционирует саму себя?»**.

---

## 2. Архитектурные принципы Forge

| Принцип | Суть |
|---------|------|
| **Additive Architecture** | Каждый новый Forge добавляется без переписывания существующих |
| **Separation of Concerns** | Каждый Forge имеет единственную ответственность |
| **Contract First** | Интерфейсы между Forge'ами — явные контракты (события, API) |
| **Single Source of Truth** | Каждый артефакт (RFC, ADR, Lesson) имеет ровно одно каноническое место |
| **Observability** | Каждый переход между Forge'ами логируется в event_log |
| **Explainability** | Каждое архитектурное решение имеет DecisionTrace |
| **Backward Compatibility** | Новые Forge'ы не ломают существующие цепочки |
| **Low Coupling** | Forge'ы связаны через события, а не прямые вызовы |
| **High Cohesion** | Внутри одного Forge'а — максимальная связность |

---

## 2a. Организационные контейнеры: Workspace → Project

> **Источник:** Альтернатива A из ARB-REV-001 (v5.96.0) — интеграция визионерского ядра Factory/Forge Manifest (документ 68).

Buffy Forge управляет архитектурным знанием, но не определяет, **кому** оно принадлежит и **в каком контексте** создаётся. Для этого вводятся два организационных контейнера над L0-L5:

```
Workspace (L-1)
    │
    ├── Project A (L-2)
    │   └── Buffy Forge (L0→L5)
    │
    ├── Project B (L-2)
    │   └── Buffy Forge (L0→L5)
    │
    └── Project C (L-2)
        └── Buffy Forge (L0→L5)
```

### Workspace (L-1)

**Workspace** — наивысший уровень организации. Принадлежит человеку, компании или команде. Содержит множество проектов.

| Поле | Значение |
|------|----------|
| **Концепт** | Организационный контейнер верхнего уровня |
| **Принадлежит** | Человеку / компании / команде |
| **Содержит** | 1+ Project |
| **Аналог в Manifest** | Workspace OS → Workspace |
| **Реализация** | Директория верхнего уровня (например, `/storage/.../workstation/`) |
| **Зрелость** | 📋 Design |

**Ответственность:**
- Владение всеми проектами пользователя/команды
- Глобальные настройки (Provider Pool, Key Pool, Preference)
- Кросс-проектный Organizational Memory (общие уроки, паттерны)

**Граница:** Workspace не содержит бизнес-логики. Это контейнер.

### Project (L-2)

**Project** — изолированная среда разработки конкретного продукта. Каждый проект имеет собственный экземпляр Buffy Forge (L0-L5).

| Поле | Значение |
|------|----------|
| **Концепт** | Экосистема проекта |
| **Содержит** | Собственную память, документацию, архитектуру, Forge, процессы, историю решений, знания |
| **Изоляция** | Проекты не разделяют состояние (кроме явного кросс-проектного OM) |
| **Аналог в Manifest** | Workspace OS → Project |
| **Реализация** | Корневая директория проекта (например, `freebuff/`) |
| **Зрелость** | ✅ Production (текущий `freebuff/` уже является Project) |

**Что входит в Project:**

| Элемент | Где в freebuff |
|---------|---------------|
| Идеи | `docs_10/decisions/IDEAS.md` |
| Исследования | `docs_10/` |
| Архитектура | `docs_10/engineering-memory/` (RFC, ADR) |
| Документация | `docs_10/`, `CHANGELOG.md`, `TASK.md` |
| Память | `core_02/LESSONS.md`, `data_13/context.db` |
| Решения | `docs_10/decisions/ADR_*.md` |
| Знания | Organizational Memory (RFC v5.92.0) |
| Артефакты | `scripts_01/`, `core_02/`, `projects_17/` |
| Код | `core_02/`, `scripts_01/` |
| Тесты | `tests_09/` |
| История развития | `CHANGELOG.md`, `docs_10/e2e_logs/` |

**Граница:** Project — контейнер, не метасистема. Buffy Forge (L0-L5) работает ВНУТРИ Project.

### Почему Workspace/Project — не Forge-уровни

| Концепт | Forge (L0-L5) | Workspace/Project (L-1, L-2) |
|---------|--------------|-------------------------------|
| **Что делает** | Куёт артефакты | Содержит контекст |
| **Жизненный цикл** | Принимает → куёт → передаёт | Владеет → изолирует → организует |
| **Связность** | Forge'ы связаны потоком артефактов | Контейнеры связаны иерархией владения |
| **Инфраструктура** | Использует EventBus, OM, DIS | Использует файловую систему, конфигурацию |

Workspace и Project — **организационные контейнеры**, а не производственные мастерские. Они не «куют» — они **содержат**.

### Соответствие ARB-REV-001

| Пункт ARB Review | Статус |
|------------------|--------|
| Принять визионерское ядро Manifest как философию Buffy | ✅ Этот раздел |
| Workspace как организационный контейнер | ✅ Добавлен (L-1) |
| Project как экосистема (не только код) | ✅ Формализован (L-2) |
| Prompt как нижний уровень, не центр | ✅ Совместимо с существующей архитектурой |
| НЕ создавать параллельную Factory/Forge систему | ✅ Workspace/Project — контейнеры, не Factory |

---

### §2a.1 — Граница ответственности: Forge Pipeline ↔ Wizard/Scenario (PB-16, ROADMAP-FR-001 Step 2, Case 2' doc-only)

v1.1 §2a установил Workspace/Project как организационные контейнеры, работающие НАД Buffy Forge L0-L5. v1.2 ADDITIVE проясняет дополнительный внутренний уровень: внутри Project, **Forge Pipeline** (L-3) и **Wizard/Scenario** (cross-cutting sub-layer через L-2) являются ORTHOGONAL-доменами по STATE-данным, но имеют общий **TG transport layer** (см. §2a.2).

| Аспект | Forge Pipeline (CI-stages) | Wizard / Scenario (role-driven execution) |
|--------|-------------------------------|--------------------------------------------|
| **CLI entry-point** | `forge forge <project>` / `forge check <project>` | `scripts_01/wizard.py <args>` (или programmatic `core_02/wizard_lib.run_wizard_with_registry(...)`) |
| **Pipeline стадии** | FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT | role resolution (developer, interior_consultant, ...) → scenario YAML load → task generation → mock-runtime / real-runtime narrative → TG delivery → optional TG round-trip read-back |
| **State source** | `data_13/forge_registry.yaml` (статусы: UNFORGED/CHECKING/BUILDING/TESTING/DEPLOYED/FAILED + history по `forge forge` запускам) | in-memory `core_02.scenario_registry.ScenarioRegistry` + filesystem (`docs_10/e2e_logs/promt47_run.md`, `/tmp/<project>_e2e/...`) + TG channel (msg_id хранится в e2e-логах, audit-trail под CAN-17) |
| **State scope** | CI-stage lifecycle конкретного проекта: был ли запущен `forge forge`? какой exit-code? какие подстадии что вернули? | scenario-driven role execution lifecycle: какие role-артефакты сгенерированы? какие TG-сообщения доставлены? round-trip read-back ok? |
| **Default cmd** | `core_02/forge_pipeline.py:258-280` `_default_build_cmd()` — реальная O/S-level команда (esbuild-wasm/npm/python -m build) | `core_02/wizard_lib.run_wizard_with_registry()` — Python-уровень: scenario registry → role YAML → blueprint generation |
| **Schema isolation** | YAML c `forgespec` статусами; **не** хранит role/scenario данные | ABC `Scenario` (roles, validate, routing_hint); **не** хранит CI-stage статусы |
| **Cross-call (verification, PB-16 Fact 2-3)** | НЕТ (`grep -nE 'wizard|scenario_registry|run_wizard' core_02/forge_pipeline.py` → 0 hits) | НЕТ (`grep -nE 'forge_pipeline|forge_registry' core_02/wizard_lib.py core_02/scenario_registry.py` → 0 hits) |
| **TG transport (PB-16 Урок 1 corrigendum)** | `scripts_01/forge.py:cmd_forge.on_report` → `tg_session.send_text_message(text)` / `TgClientV2().send(text)` | `core_02.telegram_contract:report_to_saved_messages(text)` / `:report_to_alex_litvinov(text)` |

Эти два домена **никогда не должны merge-иться в единый STATE-SoT** (это НЕ PB-14-класс docs-sync баг; это архитектурно distinct domains по design). Их intersection — **только TG transport layer** (§2a.2).

### §2a.2 — STATE-orthogonal между forge_registry.yaml UNFORGED и Wizard-progressed (PB-16, ROADMAP-FR-001 Step 1 result)

**Факт-чекинг (PB-16, 2026-08-06):** между `data_13/forge_registry.yaml: interior-planner: status=UNFORGED` и `docs_10/e2e_logs/promt47_run.md: 8 interior_planner refs + v5.64.0 TG msg_id **138366** Saved + **138367** Литвинов (Wizard path) — нет синхронизационного бага. Это **orthogonal STATE** — два разных семантических пространства:

| Запрос (read-world) | Источник истины | Ожидаемый ответ для interior-planner (по факту на 2026-08-06) |
|---------------------|-----------------|----------------------------------------------------------------|
| "Прошёл ли interior-planner через `forge forge` CI-stages?" | `data_13/forge_registry.yaml` | **UNFORGED** — никогда не запускался в Forge Pipeline (честен, не баг) |
| "Прошёл ли interior-planner через Wizard с TG-доставкой?" | `docs_10/e2e_logs/promt47_run.md` + TG round-trip read-back | **Passed** — TG msg_id 138366/138367 v5.64.0 (Wizard path, не context.db) |

Эти два ответа **не противоречат друг другу** — они трекают orthogonal аспекты жизненного цикла проекта. До v1.2 §2a устанавливал только контейнерный уровень (Workspace/Project). v1.2 явно фиксирует **STATE-orthogonal** между Forge-Pipeline-state и Wizard/Scenario-state для предотвращения повторной confusion «Forge doesn't work» (FALSE — Forge works, просто interior-planner не запускался через Forge-CLI).

**TG transport — shared infrastructure (PB-16 Урок 1 corrigendum):** оба домена доставляют отчёты через один TG transport layer:

- **Forge-Pipeline path:** `scripts_01/forge.py:cmd_forge.on_report` → `tg_session.send_text_message(text)` (primary) / `TgClientV2().send(text)` (fallback, см. CON-31 v5.66.0)
- **Wizard/Scenario path:** `core_02/telegram_contract.py:report_to_saved_messages(text)` / `:report_to_alex_litvinov(text)` (TG-channel constants зафиксированы в CAN-3 fixed v5.40.0: chat_id=7709651193 / 1063827731)

То есть transport shared, но **state-реестры — раздельные**. Это уточнение важно для аудита: msg_id в `docs_10/e2e_logs/promt47_run.md` (`## Historical Verification Runs` секция) может быть порождён любым из двух путей, и это нормально (совместимо с CAN-17 — audit-trail сохраняется независимо от source path).

### §2a.3 — UNFORGED naming clarification (PB-16 Lesson suggestion → doc-polish)

**Проблема:** значение `status=UNFORGED` в `data_13/forge_registry.yaml` инфелецитозно — буквальное прочтение означает «проект вообще не работал», что приводит к репутации *"Forge doesn't work"* при виде interior-planner в UNFORGED. Реальность другая: interior-planner **реально работает** через Wizard/Scenario path (TG msg_id 138366/138367 v5.64.0), просто **никогда не запускался через `forge forge` CLI**. Это naming ambiguity, не bug; фикс — schema-header doc-polish (ниже).

**Schema-header clarification (mandatory для всех читателей `data_13/forge_registry.yaml`):**

```
Статусы в Forge Pipeline — это CI-stage lifecycle, НЕ общий проект-жизненный цикл:

  UNFORGED     = "не прошёл forge forge" (проект может быть отлично рабочим
                  через другой pipeline — например Wizard/Scenario + TG round-trip)
  CHECKING     = "running forge check, но не full forge forge"
  BUILDING     = "running forge forge; этап BUILD активен"
  TESTING      = "running forge forge; этап TEST активен"
  DEPLOYING    = "running forge forge; этап DEPLOY активен"
  DEPLOYED     = "forge forge завершён успешно"
  FAILED       = "forge forge завершён с failure на одной из стадий"
```

UNFORGED **никогда не означает**:

- «проект не работает» (это проверит Wizard/Scenario + TG channel — см. §2a.2)
- «код не написан» (это проверит filesystem)
- «артефакты не доставлены» (это проверит `docs_10/e2e_logs/`)

UNFORGED **означает только**: «`forge forge <project>` CLI никогда не запускался для этого проекта ИЛИ был запущен, но завершился error до первой стадии и registry не зарегистрировал запуск».

**Следствие для downstream-сервисов:** при виде UNFORGED в `data_13/forge_registry.yaml` **не следует делать вывод о project health**. Смотреть в `docs_10/e2e_logs/<project>_run.md` + TG audit-trail (`#FB_STATE##` marker; см. CON-35 v5.64.0) для ортопроверки.

### Связанные артефакты (§2a.1–§2a.3)

- `core_02/LESSONS.md` PB-16 (первичный источник правки; ROADMAP-FR-001 Step 1 result)
- `docs_10/ROADMAP_FORGE_RECONCILIATION.md` (Step 2 closure зафиксирован здесь)
- `docs_10/e2e_logs/promt47_run.md` (TG audit-trail basis; v5.64.0 msg_id 138366/138367)
- `data_13/forge_registry.yaml` (STATE source #1 — Forge-Pipeline CI-stages)
- `data_13/context.db` (НЕ хранит ScenarioRuntime — PB-16 Fact 5; cross-table LIKE '%interior%' → 0 rows)
- `core_02/forge_pipeline.py:56-65,94-106,132-146,159-172,258-280` (Forge Pipeline implementation)
- `core_02/wizard_lib.py` (Wizard implementation; `run_wizard_with_registry`)
- `core_02/scenario_registry.py` (ABC + auto-discovery)
- `core_02/telegram_contract.py:report_to_*.messages` (Wizard TG transport)
- `scripts_01/forge.py:cmd_forge.on_report` (Forge TG transport)
- ROADMAP-FR-001 readiness gate для Шага 3 (LEVIATHAN inventory) — теперь **разблокирован**.

---
## 3. Forge как класс подсистем

### Определение

**Forge** — специализированная мастерская с единственной ответственностью: создавать, поддерживать и эволюционировать определённый класс архитектурных артефактов.

Каждый Forge:
- **Принимает** сырые материалы (идеи, события, данные)
- **Кузёт** артефакты (идеи, знания, архитектурные решения, код)
- **Передаёт** готовые артефакты следующему Forge'у
- **Учит** Organizational Memory через Learning Loop

### Классификация

| Уровень | Forge | Артефакты | Зрелость |
|---------|-------|-----------|----------|
| **L0 — Genesis** | Idea Forge | Ideas, Proposals, Draft RFC | 📋 Design |
| **L1 — Knowledge** | Knowledge Forge | Lessons, Patterns, Knowledge Objects | 📋 RFC |
| **L2 — Architecture** | Architecture Forge | RFC, ADR, ARB-решения, AG-отчёты | 📋 RFC |
| **L3 — Implementation** | Implementation Forge | Tasks, Code, Migrations, Tests | 📋 Design |
| **L4 — Validation** | Validation Forge | Compliance-отчёты, Drift-отчёты | 📋 Design |
| **L5 — Evolution** | Evolution Forge | Analytics, Feedback, Pattern Discovery | 📋 Design |

---

## 4. Шесть форджей Buffy

### 4.1 Idea Forge (L0 — Genesis)

**Что куёт:** идеи → предложения → черновики RFC.

| Вход | Выход |
|------|-------|
| Мысли разработчика | Idea (записанная, классифицированная) |
| Проблемы из event_log | Proposal (формализованное предложение) |
| Гипотезы из Pattern Discovery | Draft RFC (черновик для ARB) |
| Feedback из Evolution Forge | обратно в цикл |

**Ответственность:**
- Захват и структурирование идей
- Классификация по доменам (Architecture, Knowledge, Tooling, Process)
- Приоритизация (Critical / High / Medium / Low)
- Формирование Draft RFC

**Граница:** Idea Forge не принимает архитектурных решений. Он только готовит предложения.

**Реализация:** IDEAS.md (текущий) → таблица `ideas` в context.db (Phase 2).

---

### 4.2 Knowledge Forge (L1 — Knowledge)

**Что куёт:** знания из опыта.

| Вход | Выход |
|------|-------|
| События из event_log | Observations (автоматические) |
| Ошибки и баги | Candidates (полуавтоматические) |
| Уроки из LESSONS.md | Knowledge Objects (CON-*, ANTI-*, CAND-*) |
| Результаты AG-проверок | Patterns (повторяющиеся ситуации) |
| Результаты Evolution Analytics | обновлённые confidence_scores |

**Внутренние компоненты:**
- **Organizational Memory Engine** — Memory Store + Knowledge Graph + Semantic Layer (RFC v5.92.0)
- **Pattern Discovery** — кластеризация событий → кандидаты CAND-* (Evolution v5.93.0, I-6)
- **Knowledge Evolution** — версионирование KO (Evolution v5.93.0, I-7)
- **Learning Loop** — observation → candidate → confirmed → validated → superseded

**Граница:** Knowledge Forge не принимает архитектурных решений. Он предоставляет знания для Architecture Forge.

---

### 4.3 Architecture Forge (L2 — Architecture)

**Что куёт:** архитектурные решения.

Это **центральный Forge** — место, где архитектурные знания превращаются в решения.

| Вход | Выход |
|------|-------|
| Draft RFC из Idea Forge | RFC (утверждённый или отклонённый) |
| Knowledge Objects из Knowledge Forge | ADR (Architecture Decision Record) |
| DecisionTrace из DIS | ARB-вердикты |
| AG-отчёты о дрифте | обновлённые RFC (re-review) |

**Внутренние компоненты:**

| Компонент | Роль | Документ |
|-----------|------|----------|
| **Architecture Review Board (ARB)** | Архитектурный суд: принимать/отклонять RFC | 054_17 |
| **Decision Intelligence System (DIS)** | 6 движков анализа: ARE, CAE, TDA, PC, EP, RFC Reviewer | RFC DIS v5.94.0 |
| **Architecture Governance (AG)** | Архитектурный надзор: compliance, drift detection | 055_18 |
| **Authority Model** | Уровни доверия: system > reviewed > candidate > generated > user | Evolution v5.93.0, I-1 |
| **Policy Engine** | Правила: advisory / mandatory / blocking | Evolution v5.93.0, I-3 |
| **Conflict Resolver** | Стратегии: newest_wins, authority_wins, merge | Evolution v5.93.0, I-5 |

**Процесс внутри Architecture Forge:**

```
Draft RFC
    │
    ▼
DIS: RFC Reviewer (пре-скрининг)
    │
    ▼
ARB: 10-шаговый анализ
    │
    ├── APPROVED ──────────► RFC (published)
    ├── CHANGES REQUIRED ──► возврат автору
    ├── SPIKE REQUIRED ───► архитектурный эксперимент
    ├── DEFERRED ─────────► postponed
    └── REJECTED ─────────► архив
            │
            ▼
    ADR (Architecture Decision Record)
            │
            ▼
    Implementation (L3)
            │
            ▼
    AG: Compliance Check
            │
            ├── COMPLIANT ────────► OK
            ├── MINOR DRIFT ──────► предупреждение
            ├── MAJOR DRIFT ──────► исправление
            ├── VIOLATION ────────► mandatory fix
            └── REQUIRES ARB ─────► re-review
```

**Где живёт AG:** Architecture Governance выполняет проверку соответствия в Validation Forge (L4), но её вердикты (MAJOR DRIFT, VIOLATION, REQUIRES ARB REVIEW) возвращаются в Architecture Forge (L2) для повторного архитектурного решения. AG — мост между L2 и L4, а не дублирование. Она проверяет реализацию (L4), но её результаты влияют на архитектурные решения (L2).

**Граница:** Architecture Forge управляет архитектурными решениями, но не пишет код.

---

### 4.4 Implementation Forge (L3 — Implementation)

**Что куёт:** код.

| Вход | Выход |
|------|-------|
| RFC (APPROVED) из Architecture Forge | Tasks (разбивка на задачи) |
| ADR из Architecture Forge | Implementation (код) |
| Контракты API | Code Generation (по контрактам) |
| | Migrations (БД, данные) |
| | Tests |

**Ответственность:**
- Разбивка RFC на атомарные задачи
- Генерация кода по контрактам
- Миграции данных
- Интеграционное тестирование

**Граница:** Implementation Forge не принимает архитектурных решений. Если в ходе реализации выясняется архитектурная проблема — возврат в Architecture Forge.

---

### 4.5 Validation Forge (L4 — Validation)

**Что куёт:** уверенность.

| Вход | Выход |
|------|-------|
| Implementation из L3 | Compliance-отчёты |
| RFC + ADR из Architecture Forge | Drift-отчёты |
| Codebase | Governance Violations |
| | Policy Compliance |

**Внутренние компоненты:**
- **Architecture Governance (AG)** — полный цикл проверки (055_18)
- **Drift Detection** — автоматическое обнаружение расхождений (существующий `drift_check.py`)
- **Principle Compliance** — проверка 10 принципов Buffy
- **Dependency Governance** — циклические зависимости, лишние библиотеки

**Граница:** Validation Forge только выявляет проблемы. Исправления — через Architecture Forge (новый RFC) или Implementation Forge (bugfix).

---

### 4.6 Evolution Forge (L5 — Evolution)

**Что куёт:** будущее платформы.

| Вход | Выход |
|------|-------|
| Event Log (все события) | Analytics (дашборды, тренды) |
| Compliance-отчёты из L4 | Feedback → Knowledge Forge |
| Decision History из DIS | Pattern Discovery → новые CAND-* |
| Organizational Memory | обновлённые confidence_scores |
| | новые RFC (через Idea Forge) |

**Внутренние компоненты:**
- **Experience Analytics** — 7 SQL-запросов из OM RFC §8 + daily/weekly/monthly отчёты
- **Learning Loop** — observation → candidate → KO → feedback → confidence → validation
- **Pattern Discovery** — кластеризация событий, поиск повторяющихся ситуаций
- **Knowledge Decay** — TTL, пересмотр устаревших KO

**Граница:** Evolution Forge не меняет архитектуру напрямую. Он генерирует инсайты → Idea Forge.

---

## 5. Единая карта архитектуры Buffy

> **Примечание (v1.1):** Workspace (L-1) и Project (L-2) — организационные контейнеры над Buffy Forge (см. §2a). Диаграмма ниже показывает только Forge-уровни (L0-L5). Полная архитектура: Workspace → Project → Buffy Forge (L0→L5).

```
                        BUFFY FORGE (метасистема, L0→L5 внутри Project)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌──────────┐        ┌──────────┐          ┌──────────┐
   │   L0     │        │   L1     │          │   L2     │
   │IDEA FORGE│───────►│KNOWLEDGE │─────────►│ARCHITEC- │
   │          │        │  FORGE   │          │TURE FORGE│
   └──────────┘        └──────────┘          └──────────┘
        ▲                     ▲                     │
        │                     │                     ▼
        │               ┌──────────┐          ┌──────────┐
        │               │   L5     │          │   L3     │
        │               │EVOLUTION │◄─────────│IMPLEMEN- │
        │               │  FORGE   │          │TATION    │
        │               └──────────┘          │FORGE     │
        │                     ▲               └──────────┘
        │                     │                     │
        │               ┌──────────┐                │
        │               │   L4     │◄───────────────┘
        └───────────────│VALIDATION│
                        │  FORGE   │
                        └──────────┘


ИНФРАСТРУКТУРА (все уровни):

┌─────────────────────────────────────────────────────┐
│                   Event Bus                         │
│         (все переходы логируются в event_log)        │
├─────────────────────────────────────────────────────┤
│              Organizational Memory                  │
│     (Memory Store + Knowledge Graph + Semantic)      │
├─────────────────────────────────────────────────────┤
│              Decision Intelligence                  │
│     (ARE + CAE + TDA + PC + EP + RFC Reviewer)      │
├─────────────────────────────────────────────────────┤
│              Knowledge Engine                       │
│        (FTS5 + TF-IDF + SVD + GraphIndex)           │
└─────────────────────────────────────────────────────┘
```

**Ключевое:** инфраструктурные компоненты (EventBus, OM, DIS, KnowledgeEngine) — **горизонтальные**, обслуживают все уровни. Forge'ы — **вертикальные**, специализированные мастерские.

---

## 6. Потоки данных между Forge'ами

| Переход | Тип | Событие в event_log |
|---------|-----|---------------------|
| Idea → Knowledge | `idea.promoted` | Idea получила статус Proposal |
| Knowledge → Architecture | `knowledge.ready` | KO достиг `confirmed` + `confidence > 0.7` |
| Architecture → Implementation | `rfc.approved` | ARB вердикт APPROVED |
| Implementation → Validation | `implementation.complete` | Все tasks закрыты, тесты пройдены |
| Validation → Evolution | `validation.complete` | AG-отчёт готов |
| Evolution → Idea | `insight.generated` | Pattern Discovery нашёл новый паттерн |
| Любой → Architecture (re-review) | `drift.detected` | AG обнаружил MAJOR DRIFT или VIOLATION |

---

## 7. Жизненный цикл архитектурного знания

```
                    ┌──────────────┐
                    │   Идея       │ (L0: Idea Forge)
                    └──────┬───────┘
                           │ proposal
                           ▼
                    ┌──────────────┐
                    │ Наблюдение   │ (L1: Knowledge Forge)
                    │ (observation)│
                    └──────┬───────┘
                           │ pattern discovery
                           ▼
                    ┌──────────────┐
                    │ Кандидат     │ (L1: Knowledge Forge)
                    │ (candidate)  │
                    └──────┬───────┘
                           │ human confirmation
                           ▼
                    ┌──────────────┐
                    │ Знание       │ (L1 → L2: Architecture Forge)
                    │ (confirmed)  │
                    └──────┬───────┘
                           │ ARB review
                           ▼
                    ┌──────────────┐
                    │ Решение      │ (L2: Architecture Forge)
                    │ (RFC/ADR)    │
                    └──────┬───────┘
                           │ implementation
                           ▼
                    ┌──────────────┐
                    │ Реализация   │ (L3: Implementation Forge)
                    └──────┬───────┘
                           │ validation
                           ▼
                    ┌──────────────┐
                    │ Проверка     │ (L4: Validation Forge)
                    └──────┬───────┘
                           │ analytics
                           ▼
                    ┌──────────────┐
                    │ Инсайт       │ (L5: Evolution Forge)
                    └──────┬───────┘
                           │ feedback
                           ▼
                    (обратно в L0: Idea Forge)
```

Каждая стадия — отдельный Forge. Каждый переход — событие в EventBus.

---

## 8. Границы ответственности (анти-дублирование)

| Компонент | Принимает решения о... | НЕ принимает решения о... |
|-----------|------------------------|----------------------------|
| **Idea Forge** | Какие идеи формализовать в Proposal | Архитектурная ценность (это ARB) |
| **Knowledge Forge** | Какие observations → candidates → KO | Какие KO применять (это DIS + ARB) |
| **ARB** | Принимать/отклонять RFC | Реализация (это Implementation Forge) |
| **AG** | Соответствие реализации RFC | Архитектурная ценность (это ARB) |
| **DIS** | Анализ и рекомендации | Финальное решение (это ARB) |
| **Implementation Forge** | Как реализовать RFC | Менять ли архитектуру (это ARB) |
| **Evolution Forge** | Какие паттерны обнаружены | Внедрять ли изменения (это ARB + Idea Forge) |

**Ключевое правило:** ни один Forge не имеет права принимать решения из области ответственности другого Forge'а.

---

## 9. Forge как расширяемая платформа

### Будущие Forge'ы (L2+ extensions)

Forge как **класс подсистем** позволяет добавлять новые мастерские без ломки архитектуры:

| Forge | Артефакты | Когда |
|-------|-----------|-------|
| **Code Forge** | Генерация кода по контрактам | L3 extension |
| **Agent Forge** | Проектирование AI-агентов | L2 extension |
| **Workflow Forge** | Проектирование процессов | L2 extension |
| **Prompt Forge** | Проектирование промтов и ролей | L2 extension |
| **Security Forge** | Аудит безопасности архитектуры | L4 extension |
| **Performance Forge** | Анализ производительности | L4 extension |

Каждый новый Forge:
1. Наследует контракт (EventBus, OM, KnowledgeEngine)
2. Определяет свои артефакты
3. Интегрируется в цепочку уровней L0→L5
4. Регистрируется в ARCH_TRACK

---

## 10. Приоритеты реализации

| Фаза | Что | Зависимости | Срок |
|------|-----|-------------|------|
| **Phase 1** | **RFC Forge v1** (этот документ) | — | ✅ Текущая |
| **Phase 2** | OM Phase 2: Memory Store + Knowledge Objects | RFC OM v5.92.0 | Следующая |
| **Phase 3** | DIS Phase 1: RFC Reviewer + ARE | RFC DIS v5.94.0 | После Phase 2 |
| **Phase 4** | ARB как automation (не ручной процесс) | Phase 3 | После Phase 3 |
| **Phase 5** | AG automation: drift detection + compliance | Phase 3 | После Phase 3 |
| **Phase 6** | Evolution Forge: Analytics + Pattern Discovery | Phase 2+5 | Параллельно |

**Quick wins** (можно сделать сразу):
- `ideas` таблица в context.db (Idea Forge, L0)
- ARB конституция как markdown (уже есть: 054_17)
- AG конституция как markdown (уже есть: 055_18)

---

## 11. Соответствие существующим принципам Buffy

| Принцип | Статус | Комментарий |
|---------|--------|-------------|
| Additive Architecture | ✅ | Новые Forge'ы добавляются без переписывания |
| Contract First | ✅ | Интерфейсы Forge↔Forge — события EventBus |
| Modular Monolith | ✅ | Единая платформа, модульные Forge'ы |
| Privacy First | ✅ | Данные внутри платформы |
| Local First | ✅ | on-device: FTS5 + SVD вместо облачных LLM |
| Explainability | ✅ | DecisionTrace на каждом переходе |
| Observability | ✅ | event_log на всех границах Forge↔Forge |
| Low Coupling | ✅ | События, не прямые вызовы |
| High Cohesion | ✅ | Один Forge = одна ответственность |
| Single Source of Truth | ✅ | Каждый артефакт в своём каноническом месте |

---

## 12. Что НЕ делает Forge

Forge — метасистема проектирования. Он **не является**:

- ❌ **Runtime-платформой** — Forge не исполняет пользовательские запросы
- ❌ **CI/CD** — Forge не деплоит код
- ❌ **Мониторингом** — Forge не собирает production-метрики
- ❌ **Балансировщиком нагрузки** — Forge не управляет инфраструктурой
- ❌ **Заменой разработчику** — финальные архитектурные решения за ARB (человек + AI)

Forge отвечает на вопрос «как Buffy проектирует себя», а не «как Buffy работает в production».

---

## 13. Риски

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| Over-engineering: 6 Forge'ов до того, как OM реализован | Medium | High | Phase 1-6 с явными зависимостями; не прыгать через фазы |
| Размывание границ: Forge'ы начнут дублировать ответственность | Medium | High | Явные контракты + AG проверяет границы |
| Forge останется только на бумаге | Medium | Critical | Каждый Forge имеет минимум один concrete artifact (таблицу, скрипт) |
| Слишком много уровней абстракции | Low | Medium | L0-L2 — приоритет; L3-L5 — по мере зрелости |

---

## 14. Альтернативы

| Альтернатива | Плюсы | Минусы | Почему отклонено |
|-------------|-------|--------|------------------|
| Не создавать Forge, оставить отдельные RFC | Проще | Нет целостной картины; дублирование; drift между RFC | Уже есть 5 документов — дальше будет хуже |
| Forge как один монолитный компонент | Быстрее реализовать | Не расширяемо; нарушает Low Coupling | Противоречит Additive Architecture |
| Forge как чистая документация без кода | Нет риска over-engineering | Нулевая ценность; нельзя автоматизировать | Forge должен иметь concrete implementation |

---

## 15. Рекомендации

1. **Forge НЕ реализуется как монолит.** Каждый уровень (L0-L5) — независимая фаза.
2. **Начать с L1 (Knowledge Forge)**, потому что OM RFC уже готов.
3. **L2 (Architecture Forge) — критический путь.** ARB + AG + DIS должны работать вместе.
4. **L0 (Idea Forge) — quick win:** `ideas` таблица + миграция из IDEAS.md.
5. **Не блокировать L1 ожиданием L3-L5.** Implementation и Validation — отдельный трек.
6. **Каждый новый Forge регистрировать в ARCH_TRACK** с датой, статусом, зависимостями.

---

## 16. Связь с предыдущими RFC и ARB-решениями

| RFC | Как вписывается в Forge |
|-----|-------------------------|
| **RFC OM v1** (v5.92.0) | L1: Knowledge Forge — Memory Store + Knowledge Graph |
| **RFC OM Evolution v1.1** (v5.93.0) | L1-L2: Authority, DecisionTrace, Policy, Conflict, Versioning |
| **RFC DIS v1** (v5.94.0) | L2: Architecture Forge — движки анализа решений |
| **ARB Constitution** (054_17) | L2: Architecture Forge — принятие решений |
| **AG Constitution** (055_18) | L4-L2: Validation Forge + Architecture Forge |
| **ARB-REV-001** (v5.96.0) | L-1, L-2: Workspace/Project контейнеры (Альтернатива A) |

Forge не заменяет эти RFC. Он показывает, как они образуют единую систему.

**v1.1 (v5.97.0):** Альтернатива A из ARB-REV-001 интегрирована — Workspace/Project добавлены как организационные контейнеры над L0-L5. Соблюдён CAN-16: оригинальный RFC v1.0 не переписан, только расширен ADDITIVE-секцией §2a.

---

*Конец RFC Buffy Forge v1.*


**v1.2 (2026-08-06):** ROADMAP-FR-001 Шаг 2 (Case 2' doc-only) — ADDITIVE расширение §2a тремя подразделами: §2a.1 (Forge Pipeline ↔ Wizard/Scenario responsibility table), §2a.2 (STATE-orthogonal semantics между `forge_registry.yaml` UNFORGED и Wizard-progressed через TG round-trip), §2a.3 (UNFORGED-naming clarification schema-header из PB-16). Соблюдён CAN-16: оригинальный RFC v1.0 и v1.1 (Workspace/Project Альтернатива A из ARB-REV-001) не переписаны, а расширены ADDITIVE-подразделами §2a.1–§2a.3 к существующему §2a. Теперь §2a покрывает три уровня: (a) Workspace/Project контейнеры (v1.1); (b) Forge-Pipeline ↔ Wizard/Scenario boundary (v1.2 — orthogonal STATE + shared TG transport); (c) UNFORGED schema-header doc-polish (v1.2 — PB-16 derived). Это разблокирует ROADMAP-FR-001 Шаг 3 (LEVIATHAN inventory: forge_pipeline.py/forge_registry.py/workspace.py кандидаты в Category A — после согласованного state, не в текущем виде с расхождением).
