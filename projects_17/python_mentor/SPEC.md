# SPEC.md — Детерминированная платформа обучения Python (сводка системы)

> Canonical-спецификация проекта живёт в документах-канонах (см. Приложение А). Этот файл — короткая сводка системы и указатель, чтобы каждая фаза стартовала с единого описания.
> **Дата:** 2026-08-23 · Версия: 0.1.0

## 1. Суть продукта

Автономный learning runtime, который ведёт ученика по заранее определённому curriculum:

```
State → Decision → Activity → Evidence → State
```

Все образовательные решения — через явные детерминированные функции: `get_eligible_activities`, `select_next_activity`, `calculate_competency_state`, `determine_hint_level`, `calculate_review_state`, `evaluate_project_usage`. Запрещено прятать такую логику в endpoints, UI, триггеры БД или side effects (prompt3 §2).

## 2. Роли платформы и их детерминированные реализации

| Роль (методика) | Детерминированная реализация | Фаза |
|---|---|---|
| Куратор | Curriculum Engine + Competency State + Activity Selector (eligibility ≠ selection) | H, J |
| Тьютор (explain+drill) | versioned content bank + лестница difficulty (repetition→…→independent) | B+C, J |
| Ментор | Error Pattern Detector (AST/статика) + Hint Bank + эскалация L0–L6 | F, G |
| Практикум | Exercise Bank + Difficulty Model + Activity Selector | B+C, J |
| Заказчик | versioned project templates + question trees + acceptance criteria | K |
| Ревьюер | pytest + AST + статические анализаторы (sensors) | D, F |

## 3. Ключевые контракты (детали — blueprint v0.1)

- **Competency:** id, description, prerequisites (acyclic), understand/can_do criteria, typical_errors, verification_exercise, project_marker.
- **Exercise:** id, source_id, type(concept|practice), competency_id, skill_tags, difficulty_rung, tests_ref, reference_solution_ref; **не в live corpus без approved source**.
- **Evidence event:** append-only log → state = pure fold (S0/S2/S3/S4/S5, S6 = pending_llm_review).
- **Grading contract:** immutable результат; correctness(PASS/FAIL/ERROR/TIMEOUT/INFRASTRUCTURE_ERROR) + diagnostics (что никогда не становится evidence) + evidence_candidates.
- **Hint:** L0–L6; эскалация max +1; L4+ permission; project cap L3; новый exercise → L0.
- **Execution:** единый Job → Worker → Sandbox → Result интерфейс; MVP tier subprocess+limits; hardened — future.
- **FSRS:** единица — competency; scheduling state отделён от learning state.

## 4. Детерминизм vs LLM (граница)

- LLM-вызовы в ядре запрещены (0).
- Не верно: `tests_passed → mastery`, `pylint_score → competency`, `maintainability_index → mastery` (diagnostic_only).
- S6 и ось Thinking — `pending_llm_review`, честная точка эскалации (blueprint §1/§7).
- Phase O (LLM-слой) — опционально, после P-N, поверх чистого API, ядро не модифицируется.
- **Localization:** English upstream остаётся canonical; `ru` — versioned projection с source hash; LLM создаёт только reviewed translation drafts через внешний provider (ADR-006).

## 5. Хранилище

SQLite (stdlib), без Postgres в MVP. Таблицы по фазам (blueprint §10): competencies, competency_prerequisites, exercises, exercise_sources, exercise_competencies, (позже) submissions, test_results, static_analysis_results, error_patterns, detected_errors, hint_bank, student_competencies, competency_evidence, review_states, review_events, learning_events. FK + UNIQUE + CHECK; PRAGMA foreign_keys = ON (проверять тестом, prompt1 §23).

## 6. Развёртывание (MV)

- Termux, non-root, localhost; FastAPI (после L) на 127.0.0.1:PORT; LAN по IP телефона.
- Никаких зависимостей от leviathan_agent/hermes/openclaw; автономно.

## 7. Принятые решения (ADR)

| ADR | Суть | Статус |
|---|---|---|
| ADR-001 | Детерминированное ядро первично; LLM — внешний опциональный слой | 🟢 Accepted |
| ADR-002 | Фазовые гейты B+C→N, без перескоков | 🟢 Accepted |
| ADR-003 | Sandbox: MVP-tier (subprocess+limits) и единый Job/Worker/Sandbox интерфейс; hardened — future | 🟢 Accepted |
| ADR-004 | License gate: approved/pending/rejected; unknown → никогда live | 🟢 Accepted |
| ADR-005 | RLIMIT_AS в Termux/proot; граница MVP execution и hardened sandbox | 🟢 Accepted |
| ADR-006 | Локализация learner-контента и контролируемые LLM-assisted обновления | 🟢 Accepted |

## Приложение А — Canonical-источники

1. `python_ai_tutor_blueprint_v0.1.md` — контракты (schema, границы, API)
2. `python_ai_tutor_methodology.md` — методика (роли, S/L-модели, curriculum)
3. `prompt.md` — исходное ТЗ (research)
4. `prompt1.md` — Phase B+C: DoD, acceptance, запреты
5. `prompt2.md` — Phase D–N: DoD каждого этапа
6. `prompt3.md` — master prompt v1.0 (инварианты, ограничения)
7. `python_ai_tutor_prompts.md` — промты ролей (Phase O)