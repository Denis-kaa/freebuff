# CHECKLIST.md — Pre-flight и acceptance (python_mentor)

> Обновляется после каждой фазы. Текущий статус: Phase F complete, waiting for review.

## Pre-flight (каркас проекта)

- [x***REMOVED*** `projects_17/python_mentor/` создан
- [x***REMOVED*** `MANIFEST.md` — паспорт, инварианты
- [x***REMOVED*** `README.md` — навигация и статус
- [x***REMOVED*** `SPEC.md` — сводка системы и канонические источники
- [x***REMOVED*** `ROADMAP.md` — роадмап P0, B+C…N + гейты
- [x***REMOVED*** `STEPS.md` — журнал шагов с «почему»
- [x***REMOVED*** `LESSONS.md` — журнал уроков (пуст)
- [x***REMOVED*** `RUNNABLE.md` + `CHECKLIST.md`
- [x***REMOVED*** `decisions/DECISIONS.md` + ADR-001…005
- [x***REMOVED*** `project.yaml` — метаданные
- [x***REMOVED*** Зарегистрирован в `docs_10/projects_meta/PROJECTS_OVERVIEW.md`
- [x***REMOVED*** Prep Phase I: `fsrs 6.3.2` установлен и проверен; rating mapping зафиксирован в `FSRS_NOTE.md` (ROADMAP §7.1/7.2 закрыты)

## Phase B+C: инфраструктура (Шаги 0–2)

- [x***REMOVED*** Шаг 0: структура `app/` + `configs/` + `data/corpus/` + `tests/{unit,integration,fixtures***REMOVED***` (CP-0: `pytest tests/ -q` → 1 passed)
- [x***REMOVED*** Шаг 1: inspection §4 выполнен (только документация; Python 3.14.6; ничего не удалено) — CP-1
- [x***REMOVED*** Шаг 2: exercism/python shallow-clone @ `1f6aab8…` + пофайловый license audit (MIT) → `docs/exercism_research.md` — CP-2
- [x***REMOVED*** Шаги 3–11: competency map, schema, license gate, ingestion, mapping, reports, tests, docs, G-BC

## Acceptance Phase B+C (по prompt1 §36–37) — ✅ ЗАКРЫТО 2026-08-23

- [x***REMOVED*** competency map v0.1 (25 компетенций, IDs стабильные, lowercase)
- [x***REMOVED*** prerequisites валидируются; циклы — тест (test_cycle_detected)
- [x***REMOVED*** understand/can_do criteria у каждой; Exercism concepts покрываются (45/67 + 22 явный unmapped)
- [x***REMOVED*** source registry c license evidence; approved/pending/rejected (sources.yaml + gate)
- [x***REMOVED*** unapproved content не попадает в live (test_pending_source_not_in_live)
- [x***REMOVED*** ingestion concept + practice; idempotent (N→N, change→update) — тесты + CLI acceptance
- [x***REMOVED*** provenance сохраняется; reference solution — только с --with-refs
- [x***REMOVED*** mapping exercise→competency + rung + confidence + manual overrides (overrides.yaml)
- [x***REMOVED*** SQLite: FK/UNIQUE/CHECK, PRAGMA foreign_keys=ON (9 тестов storage)
- [x***REMOVED*** отчёты: coverage/gaps/low-confidence/license (python -m app report …)
- [x***REMOVED*** tests: 37 unit (hermetic, offline) + 2 integration (canary real)
- [x***REMOVED*** `pytest` ALL PASS (37 passed) + `python3 -m mypy app/ --ignore-missing-imports` → 0 errors
- [x***REMOVED*** Docs: `docs/curriculum_v0.1.md`, `docs/exercism_ingestion.md`
- [x***REMOVED*** CLI: `ingest exercism --dry-run` → понятный отчёт (161 discovered)
- [x***REMOVED*** Финал: статус `PHASE B+C COMPLETE · WAITING FOR REVIEW` (STEPS Шаг 10)
- [x***REMOVED*** Отчёт A–I — в STEPS (Шаг 10, 2026-08-23)

## Acceptance: Phase D–N (кратко; детали DoD — в prompt2.md)

- [x***REMOVED*** D: grading contract + pytest runner + норм. результат + infra/student separation (13 tests, G-D)
- [x***REMOVED*** E: execution abstraction + Termux backend + timeout/CPU/output/address-space policies + process-group cleanup + sanitized environment (8 tests, G-E; MVP-tier)
- [x***REMOVED*** F: ordered AST registry (7 rules) + Pylint/Radon/Flake8/Bandit adapters + normalization + reference-only error patterns + 14 diagnostic-only tests (G-F)
- [ ***REMOVED*** G: hint bank + `next_hint_level` (no jump, reset, permission, cap, fallback)
- [ ***REMOVED*** H: evidence append-only + state fold + переходы S0–S5 + rebuild/idempotency/explainability + S6 escalate
- [ ***REMOVED*** I: FSRS (competency unit) + rating mapping + due/overdue + persistence
- [ ***REMOVED*** J: eligibility ≠ selection + policy + determinism + explainability
- [ ***REMOVED*** K: project templates + question tree + compliance cap + project_usage evidence
- [ ***REMOVED*** L: FastAPI thin layer (0 learning logic в endpoints) + contract tests
- [ ***REMOVED*** M: UI screens через API только, без learning logic
- [ ***REMOVED*** N: 9 сценариев E2E; финальный acceptance детерминизма
- [ ***REMOVED*** P-O (future): только после P-N; не трогает ядро

## Инварианты (перед любой «green»-пометкой)

- [x***REMOVED*** LLM-вызовы = 0
- [x***REMOVED*** Никакой evidence из diagnostic-only метрик
- [x***REMOVED*** Ни одного exercise без approved source
- [x***REMOVED*** Никакого импорта `core_02`/`scripts_01`/`freebuff_plugin*` в коде
- [x***REMOVED*** Никаких перескоков фаз (гейт-статусы честные)
