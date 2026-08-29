# MANIFEST.md — Паспорт проекта `python_mentor`

> **Slug:** `python_mentor`
> **Версия:** 0.1.0
> **Статус:** 🟡 ACTIVE — Phase F complete, waiting for review; Phase G is next
> **Дата:** 2026-08-24
> **Стек:** Python 3.11+ · SQLite (stdlib) · pytest · (по фазам: pylint/radon/flake8/bandit, fsrs, FastAPI, статический HTML/JS)
> **Среда развёртывания:** локальный Termux (Android, non-root), 127.0.0.1:PORT; НЕ публичный сервис
> **Ключевые каноны:** [`python_ai_tutor_blueprint_v0.1.md`***REMOVED***(python_ai_tutor_blueprint_v0.1.md) (source of truth для реализации) · [`python_ai_tutor_methodology.md`***REMOVED***(python_ai_tutor_methodology.md) (педагогика)

## Назначение

Детерминированная (без LLM в базовом контуре) платформа обучения Python: ведёт ученика по curriculum на основе формальных правил, evidence и заранее определённого банка упражнений. **Это не chat-bot и не «AI-тьютор»** — это learning runtime со стабильным состоянием, removable LLM-слоем (промты ролей готовы: `python_ai_tutor_prompts.md`).

## First vertical slice (цель Phase B+C)

```text
Exercism repository
  → license gate (approved/pending/rejected)
  → exercise + provenance + competency mapping
  → idempotent SQLite corpus
  → coverage / gap / low-confidence reports
```

## Обязательные инварианты проекта

- **Детерминизм:** same state + same input = same decision; нерешённое правило → `UNRESOLVED/REQUIRES_HUMAN_RULE` (prompt3 §0);
- **LLM-call = 0** в ядре: optional translation provider создаёт только drafts; никаких прямых LLM-записей в corpus, curriculum, evidence или learning state;
- **License gate:** ни одно упражнение не попадает в live corpus без `exercise_source.status == approved` (blueprint §2, prompt1 §13);
- **Evidence-first:** состояние компетенций — pure function от append-only лога; никаких мутируемых «оценок» без возможности rebuild (blueprint §3, §7; prompt2 Phase H);
- **Static metrics ≠ evidence:** maintainability index и прочие diagnostic-only поля физически не могут порождать evidence (blueprint §4);
- **Sandbox честен:** `SANDBOX_TIER = "mvp_untrusted_single_user"`; никаких обещаний production-isolation (blueprint §0);
- **Локальность:** zero-cost, без внешних API и зависимости от leviathan_agent/hermes/openclaw (prompt.md);
- **Фазы по гейтам:** не перескакивать (prompt1 §40, prompt2) — каждая фаза заканчивается `WAITING FOR REVIEW`;
- **Самодостаточность:** код проекта НЕ импортирует `core_02/`, `scripts_01/`, `freebuff_plugin*` (PROJECT_RULES §7);
- **Additive:** существующие модули не переписываются без явной причины (AGENTS.md §6.4).

## Индекс документов

| Файл | Назначение |
|---|---|
| `MANIFEST.md` | Паспорт и границы (этот файл) |
| `README.md` | Навигация и текущий статус |
| `SPEC.md` | Сводка системы + указатель на каноны |
| `ROADMAP.md` | **Роадмап P0, B+C…N (главный план), гейты, риски** |
| `PHASE_BC_PLAN.md` | **Детальный операционный план Phase B+C: шаги, контрольные точки, риски, DoD** |
| `FSRS_NOTE.md` | **Подготовка Phase I: API fsrs 6.3.2 + rating mapping** |
| `docs/exercism_research.md` | **Exercism research + пофайловый license audit (CP-2, Шаг 2)** |
| `docs/grading_v0.1.md` | **Phase D grading contract, runner boundary, and limits** |
| `docs/execution_v0.1.md` | **Phase E execution contract, MVP limits, and security boundaries** |
| `docs/diagnostics_v0.1.md` | **Phase F AST diagnostics, analyzer adapters, and diagnostic-only boundary** |
| `docs/localization_v0.1.md` | **English source inventory, Russian projection, and LLM update boundary** |
| `decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md` | **RLIMIT_AS в Termux/proot и граница MVP/hardened sandbox** |
| `decisions/ADR-006_localization_and_llm_content_updates.md` | **Локализация learner-контента и LLM-assisted update boundary** |
| `prompt_localization.md` | **Контракт локализации, source hashes и review gate** |
| `data/localization/` | **Manifest и versioned locale projections (runtime-generated)** |
| `docs/PHASES_GRAPH.md` | Визуальная схема фаз B+C…N: граф, зависимости, открытые вопросы |
| `STEPS.md` | Журнал шагов и «почему» |
| `LESSONS.md` | Project-local уроки (CON/CAN/ANTI/PB) |
| `RUNNABLE.md` | Запуск и ограничения |
| `CHECKLIST.md` | Pre-flight и acceptance |
| `project.yaml` | Метаданные Workspace/Forge |
| `python_ai_tutor_blueprint_v0.1.md` | Контракты (source of truth) |
| `python_ai_tutor_methodology.md` | Педагогика, S-уровни, L-подсказки |
| `python_ai_tutor_prompts.md` | Промты ролей — будущий LLM-слой (Phase O) |
| `prompt.md` | Исходное research-ТЗ (Этап 0–3) |
| `prompt1.md` | ТЗ Phase B+C (DoD + acceptance) |
| `prompt2.md` | ТЗ Phase D–N (серия промтов-гейтов) |
| `prompt3.md` | Master prompt v1.0 (консолидированный) |
| `decisions/` | Project-local ADR |

## Текущий статус

- [x***REMOVED*** P0: research выполнен, контракты зафиксированы в blueprint v0.1; методика и промты готовы.
- [x***REMOVED*** P1: каркас проекта создан (MANIFEST/README/SPEC/ROADMAP/STEPS/LESSONS/RUNNABLE/CHECKLIST/decisions/project.yaml); зарегистрирован в `PROJECTS_OVERVIEW.md`.
- [x***REMOVED*** **Phase B+C ГОТОВА (G-BC ✅, 2026-08-23):** Competency Map v0.1 (25 компетенций) + Exercism ingestion (161 упражнение) → `PHASE B+C COMPLETE · WAITING FOR REVIEW`.
  - [x***REMOVED*** Шаги 0–1: структура `app/` + проверка (CP-0/CP-1)
  - [x***REMOVED*** Шаг 2: License audit (CP-2)
  - [x***REMOVED*** Шаги 3–8: map+validator / schema / license gate / pipeline / mapping / CLI+reports
  - [x***REMOVED*** Шаги 9–11: hermetic tests (37 unit + 2 integration) / docs / final gate
- [x***REMOVED*** **Phase D ГОТОВА (G-D ✅, 2026-08-23):** immutable grading contract + approved-corpus boundary + normalized pytest runner; student/grader separation; 13 hermetic tests.
- [x***REMOVED*** **Phase E ГОТОВА (G-E ✅, 2026-08-24):** replaceable ExecutionJob/Policy/Result backend; subprocess process-group cleanup; timeout, CPU/output/address-space policies; sanitized environment; explicit `mvp_untrusted_single_user` tier; 8 hermetic execution tests.
- [x***REMOVED*** **Phase F ГОТОВА (G-F ✅, 2026-08-24):** ordered ASTRule registry (7 rules); normalized diagnostic contract; Pylint/Radon/Flake8/Bandit adapters; reference-only error patterns; 14 diagnostic-only tests.
- [ ***REMOVED*** Phase G…N: по роадмапу; следующая — Phase G (Hint Engine) — по `prompt2.md`.
- [x***REMOVED*** Localization foundation: source scan/status/validator plus optional Gemini three-key rotation; 432 documents inventoried; drafts are review-gated and full RU publication is not automatic.
- [ ***REMOVED*** Phase O (LLM-слой) — только после P-N; translation provider остаётся отдельной внешней boundary.

## Open decisions (см. ROADMAP §10)

hardened sandbox/network isolation (future) · доп. источники после gap-анализа · приоритизация в J · использование Forge pipeline.
