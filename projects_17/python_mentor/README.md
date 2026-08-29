# python_mentor — Детерминированная платформа обучения Python

> 🟢 **Статус:** **Phase F ✅ COMPLETE (2026-08-24)** — G-BC, G-D, G-E и G-F пройдены; diagnostics остаются diagnostic-only, без auto-evidence. Дальше — Phase G (Hint Engine).

Локальная (Termux) система обучения Python, которая ведёт ученика по curriculum **без LLM** в базовом контуре: формальные правила, evidence-лог, state machine компетенций, автогрейдер, детерминированный Куратор. LLM при необходимости подключается позже как внешний опциональный слой.

## Быстрый старт по документам

| Файл | Что это |
|---|---|
| [`MANIFEST.md`***REMOVED***(MANIFEST.md) | Паспорт, инварианты, границы |
| [`ROADMAP.md`***REMOVED***(ROADMAP.md) | Роадмап фаз B+C → N + гейты, риски, оценки |
| [`PHASE_BC_PLAN.md`***REMOVED***(PHASE_BC_PLAN.md) | Детальный план первой фазы: шаги, CP, риски, DoD |
| [`docs/exercism_research.md`***REMOVED***(docs/exercism_research.md) | License audit Exercism (CP-2) |
| [`docs/curriculum_v0.1.md`***REMOVED***(docs/curriculum_v0.1.md) | Карта компетенций v0.1 (25) и принципы |
| [`docs/exercism_ingestion.md`***REMOVED***(docs/exercism_ingestion.md) | Runbook ingestion: команды, overrides, источники |
| [`docs/grading_v0.1.md`***REMOVED***(docs/grading_v0.1.md) | Phase D contract, runner, limits |
| [`docs/execution_v0.1.md`***REMOVED***(docs/execution_v0.1.md) | Phase E execution contract, MVP limits, security boundaries |
| [`docs/diagnostics_v0.1.md`***REMOVED***(docs/diagnostics_v0.1.md) | Phase F AST rules, analyzer adapters, normalized diagnostics |
| [`docs/localization_v0.1.md`***REMOVED***(docs/localization_v0.1.md) | Русская локаль, source hashes, review и LLM update boundary |
| [`decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md`***REMOVED***(decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md) | ADR: RLIMIT_AS и граница MVP/hardened sandbox |
| [`decisions/ADR-006_localization_and_llm_content_updates.md`***REMOVED***(decisions/ADR-006_localization_and_llm_content_updates.md) | ADR: русская локаль и LLM-assisted content updates |
| [`prompt_localization.md`***REMOVED***(prompt_localization.md) | Контракт extractor/manifest/translation provider/review |
| [`python_ai_tutor_blueprint_v0.1.md`***REMOVED***(python_ai_tutor_blueprint_v0.1.md) | Contracts — source of truth для реализации |
| [`python_ai_tutor_methodology.md`***REMOVED***(python_ai_tutor_methodology.md) | Педагогика: 5 ролей, S0–S6, L0–L6, 5 документов |
| [`prompt1.md`***REMOVED***(prompt1.md) | ТЗ первой исполняемой фазы (B+C) |
| [`prompt2.md`***REMOVED***(prompt2.md) | ТЗ фаз D–N |
| [`prompt3.md`***REMOVED***(prompt3.md) | Master prompt v1.0 |
| [`python_ai_tutor_prompts.md`***REMOVED***(python_ai_tutor_prompts.md) | Промты ролей — будущий LLM-слой |

## Статус фаз

```text
P0 Research/Blueprint ✅ → P1 Проектный каркас ✅ → Phase B+C ✅ → D Grader ✅ (2026-08-23) → E Sandbox ✅ (2026-08-24) → F AST/Статика ✅ (2026-08-24)
→ G Hints → H Evidence/State
→ I FSRS → J Selector → K Projects → L API → M UI → N E2E Validation → O LLM (future)
```

Подробности и гейты: [ROADMAP.md***REMOVED***(ROADMAP.md).

## Запуск (Phase B+C, D, E, F и localization)

```bash
python3 -m app ingest exercism --dry-run     # отчёт по корпусу (без записи)
python3 -m app ingest exercism               # идемпотентный импорт в data/corpus/corpus_v0.1.db
python3 -m app ingest exercism --with-refs   # + reference solutions
python3 -m app report coverage|gaps|low-confidence|license
python3 -m pytest tests/ -q                  # 91 passed, 2 integration skipped (hermetic)
python3 -m pytest tests/ -q -m integration   # + canary на реальном клоне
# Phase D: PytestGrader и контракт — см. docs/grading_v0.1.md
python3 -m pytest tests/unit/test_execution.py -q # Phase E execution limits
# Phase E: backend contract and security limits — см. docs/execution_v0.1.md
# Phase F: AST rules and external analyzer sensors — см. docs/diagnostics_v0.1.md
# Localization: source scan/status + optional Gemini rotation, draft-only — см. docs/localization_v0.1.md и prompt_localization.md
```

Подробности: [RUNNABLE.md***REMOVED***(RUNNABLE.md), [CHECKLIST.md***REMOVED***(CHECKLIST.md), docs/exercism_ingestion.md.