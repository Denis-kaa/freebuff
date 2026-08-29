# ROADMAP-PYM-001 — Deterministic Python Learning Platform (python_mentor)

> **Версия roadmap:** 0.1.0
> **Статус:** 🟡 ACTIVE — Phase F complete; Phase G is next
> **Дата обновления:** 2026-08-24
> **Канонические источники проекта:**
> - Методика: [`python_ai_tutor_methodology.md`***REMOVED***(python_ai_tutor_methodology.md) (5 ролей, S0–S6, L0–L6, 5 документов)
> - Контракты: [`python_ai_tutor_blueprint_v0.1.md`***REMOVED***(python_ai_tutor_blueprint_v0.1.md) (source of truth для реализации)
> - Промты фаз: [`prompt.md`***REMOVED***(prompt.md) (research) · [`prompt1.md`***REMOVED***(prompt1.md) (Phase B+C) · [`prompt2.md`***REMOVED***(prompt2.md) (Phase D–N) · [`prompt3.md`***REMOVED***(prompt3.md) (master prompt v1.0)
> - Промты ролей (LLM-слой, будущее): [`python_ai_tutor_prompts.md`***REMOVED***(python_ai_tutor_prompts.md)
> **Шаблон:** `docs_10/templates/PIPELINE_TEMPLATE.md`

---

## 0. Целевое состояние

Строим **детерминированную платформу обучения Python** — автономный learning runtime без LLM в базовом контуре:

```text
Curriculum → Competency Map → Learner State → Eligible Activities
  → Selection → Exercise/Project → Submission → Deterministic Grading
  → Diagnostics → Evidence → Competency State Update → Review Scheduling
  → Next Activity (цикл)
```

Главный принцип (prompt3 §0): `same_state + same_events + same_curriculum + same_exercise_bank + same_configuration + same_rules = same_decision`. Если правило не формализовано — система возвращает `UNRESOLVED / REQUIRES_HUMAN_RULE`, а не «придумывает».

LLM **не входит** в базовый контур. Если появится — только как внешний опциональный слой поверх чистого API-контракта, **без права нарушать детерминированность ядра** (prompt3 §0, §2; blueprint §12; схема «Deterministic Core + LLM Layer» в prompt2, финал).

## 1. Explain-first: порядок и логика

Порядок выбран от фундамента контента к пользовательскому интерфейсу, каждый слой опирается на предыдущий (prompt2: B+C → D → E → F → G → H → I → J → K → L → M → N):

1. Сначала **легально чистый фундамент** контента и компетенций (license gate до всего) — без него Grader/Curator нечем кормить (prompt.md Этап 0).
2. Затем **корректность исполнения**: autograder (pytest) → отдельно execution runtime/sandbox (безопасность ≠ проверка кода).
3. Затем **диагностика** (AST/статика) → **hints** (детерминированная часть Ментора).
4. Затем **память**: evidence-first состояние компетенций (H) → FSRS-планирование повторов (I) → детерминированный Куратор/J (activity selector).
5. Затем **проектный режим** (Заказчик, K).
6. **Только после доменного ядра** — FastAPI (L), затем минимальный UI (M).
7. В конце — **E2E валидация всей цепочки** (N): детерминизм доказывается сценариями, а не словами.
8. LLM-слой (O) — отдельный опциональный трек, только после валидации ядра; промты ролей уже готовы.

Причины:

- LLM обсуждение (Tutor/Mentor/Thinking) нельзя валидировать, пока нет доказанного детерминированного состояния (prompt2: «LLM можно менять хоть каждый день, а состояние обучения, corpus, grading и правила остаются стабильными»).
- Sandbox отделён от Grader: «что проверять» ≠ «как безопасно исполнять» (prompt2 Phase E).
- API и UI — последние: в них нельзя спрятать образовательную логику (prompt3 §2 — запрет бизнес-логики в endpoints).

## 2. Полная карта этапов

| ID | Этап | Статус | Результат | Выходной gate |
|---|---|---|---|---|
| P0 | Research + Blueprint (prompt.md) | ✅ Done | Контракты в blueprint v0.1 (sandbox tiers, competency/exercise/evidence/hint-модели, grading contract, SQLite-схема, API boundaries) | Архитектура зафиксирована; подтверждение пользователя |
| P1 | Project card (эта сессия) | ✅ Каркас создан | MANIFEST/ROADMAP/STEPS/LESSONS/decisions/RUNNABLE/CHECKLIST + регистрация в PROJECTS_OVERVIEW | G1: контейнер существует; зарегистрирован |
| P-B+C | Competency Map + Exercism Ingestion | ✅ Complete (G-BC, 2026-08-23) | Машинно-читаемая карта компетенций (acyclic prerequisites), python corpus из Exercism с provenance/license gate, idempotent SQLite ingestion, отчёты coverage/gaps/low-confidence (DoD: prompt1 §§36–37). Детальный план: [`PHASE_BC_PLAN.md`***REMOVED***(PHASE_BC_PLAN.md) | G-BC: pytest green + `ingest --dry-run` + corpus-отчёт + content gap report |
| P-D | Grading Contract + Autograder | ✅ Complete (G-D, 2026-08-23) | Стабильный immutable grading contract; pytest-runner; PASS/FAIL/ERROR/TIMEOUT/INFRASTRUCTURE_ERROR; evidence **candidates** (не запись evidence) | G-D: runner работает, student vs grader failures разделены |
| P-E | Execution Runtime + Sandbox MVP | ✅ Complete (G-E, 2026-08-24) | `ExecutionJob/Policy/Result` + replaceable `ExecutionBackend`; `TermuxSubprocessBackend` (timeout, process-group cleanup, RLIMIT_CPU/AS policy, output limit, temp workspace, sanitized env); `SANDBOX_TIER="mvp_untrusted_single_user"`; hardened backend не реализован | G-E: 8 security/limit tests; network/filesystem isolation не заявлены |
| P-F | Static Analysis + AST Error Detector | ✅ Complete (G-F, 2026-08-24) | Ordered ASTRule registry (7 deterministic rules); normalized diagnostic contract; Pylint/Radon/Flake8/Bandit adapters; reference-only error-pattern mapping; no evidence side effects | G-F: 14 diagnostic-only tests; live sensor smoke; MI никогда не создаёт evidence |
| P-G | Hint Engine (детерминированный Ментор) | 🔲 Запланировано | hint_bank (L0–L6, pattern_id nullable, requires_permission L4+, project_mode_cap L3); чистая функция `next_hint_level`; generic hints; без LLM | G-G: escalation tests (no jump, reset, permission, cap, fallback) |
| P-H | Evidence Engine + Competency State Machine | 🔲 Запланировано | Append-only evidence log; state = pure fold(log); переходы S0→S2→S3→S4→S5; S6 = `pending_llm_review`; rebuild/идемпотентность/explainability | G-H: каждый переход + rebuild + duplicate event + escalate |
| P-I | FSRS integration | 🔲 Запланировано | Готовый алгоритм (fsrs или SM-2 после research), единица — **competency** (не карточка); rating mapping таблицей заранее; scheduling state отдельно от learning state; `get_due_competencies()` без селекции | G-I: mapping/review/due/overdue/persistence/rebuild tests |
| P-J | Activity Selector (детерминированный Куратор) | 🔲 Запланировано | Eligibility ≠ Selection; приоритетная policy (blocked → remediation → overdue → new → reinforcement); детерминированный порядок; explainability (why eligible/why selected/why rejected) | G-J: priority, determinism, empty set, explainability |
| P-K | Project Engine («Заказчик») | 🔲 Запланировано | Versioned project templates + question trees → детерминированная проектная спецификация; client mode cap L3; project_usage evidence | G-K: branching/invalid/requirements/competency mapping/cap tests |
| P-L | FastAPI Application Layer | 🔲 Запланировано | Тонкий API (Learning/Exercises/Submission/Hints/Reviews/Projects); никакой learning-логики в endpoints | G-L: contract tests; 0 business logic в endpoints |
| P-M | Minimal UI (HTML/CSS/JS) | 🔲 Запланировано | Dashboard, competency map, exercise+editor, результат, hints, review queue, project mode; UI не принимает образовательных решений | G-M: state flow через API только |
| P-N | E2E Educational Validation | 🔲 Запланировано | 9 сценариев (beginner/struggling/strong/failed-infra/duplicate/rebuild/FSRS/project/LLM-boundary); final acceptance: same input → same state/candidates/grading | G-N: DETERMINISTIC CORE VALIDATED |
| P-O | LLM layer (опциональный, future) | 🔮 Зарезервировано | Подключение ролей (Тьютор/Ментор/Куратор-LLM/Заказчик/Ревьюер) поверх clean API; промты готовы (`python_ai_tutor_prompts.md`); S6-reviews, Thinking-ось | Отдельный ADR после P-N; ядро не изменяется |
| X5 | Localization + LLM-assisted content updates | 🟡 Foundation + Gemini adapter ready | English source manifest; Russian versioned projection; three-key Gemini failover creates reviewable drafts; hash-based stale detection | отдельный localization gate; review policy остаётся внешней |

### Track X (обязательный кросс-режущий, во всех фазах)

| ID | Требование | Содержание |
|---|---|---|
| X1 | Hermetic/deterministic tests | Каждая фаза: pytest green + mypy; тесты не зависят от Сети (fixtures) |
| X2 | Docs sync | `docs/curriculum_v0.1.md`, `docs/exercism_ingestion.md` (DoD prompt1 §34) + ADR на спорные решения |
| X3 | Platform gates | инварианты (см. MANIFEST), регистрация в PROJECTS_OVERVIEW |
| X4 | Runbook | `RUNNABLE.md`/`CHECKLIST.md` актуальны после каждой фазы |

## 3. Scope и границы

### Входит в целевую систему (по фазам)

| Область | Фазы |
|---|---|
| Competency map, prerequisites, acyclic validator | B+C |
| Exercise registry + provenance + license gate + corpus reports | B+C |
| Exercism ingestion (concept + practice; idempotent) | B+C |
| Автогрейдер на pytest с нормализованным контрактом | D |
| Execution abstraction + Termux subprocess backend | E |
| AST rules + Pylint/Radon/Flake8/Bandit адаптеры (sensors) | F |
| Hint bank + эскалация L0–L6, permission, project cap | G |
| Evidence-log + state machine (event-sourced) | H |
| FSRS review scheduler на уровне компетенций | I |
| Activity eligibility/selection с explainability | J |
| Project engine (детерминированный «Заказчик») | K |
| FastAPI thin layer | L |
| Минимальный HTML/CSS/JS UI | M |
| E2E validation (9 сценариев, determinism acceptance) | N |
| LLM-слой (только после N, опционально) | O |

### Явно не входит

- ❌ LLM-вызовы в детерминированном контуре (всегда 0); генерация hints/exercises/curriculum/transitions через LLM
- ❌ Docker/nsjail в MVP; hardening — только через единый интерфейс (E)
- ❌ Свободное исполнение student code без limits в production-стилье
- ❌ public multi-tenant исполнение с student code
- ❌ FastAPI/UI до этапов L/M
- ❌ Другие источники (freeCodeCamp, Google Python Class, MIT) до gap-анализа после B+C (prompt1 §35: каждый источник — свой license gate)
- ❌ Postgres/Redis (SQLite достаточно для MVP)
- ❌ Записи в evidence/learning engine из других фаз (только candidates)
- ❌ Зависимости кода от `core_02/`, `scripts_01/`, `freebuff_plugin*` (проект самодостаточен, PROJECT_RULES §7)

## 4. Capability-check (окружение Termux — проверки по фазам)

> Факты зафиксированы 2026-08-23 (окружение: Termux python 3.14.6 в proot-distro контейнере Ubuntu на Android).

| Возможность | Факт (2026-08-23) | Где используется | Решение |
|---|---|---|---|
| Python 3.14.6 | ✅ `python3 --version` = 3.14.6 (`/data/data/com.termux/files/usr/bin/python3`) | все фазы | target 3.11+ выполнен |
| pytest 9.1.1 | ✅ установлен | все фазы | тестовый слой |
| SQLite 3.53.4 | ✅ stdlib | B+C | store v0.1 |
| pip 26.2.1 + доступ к PyPI | ✅ `pip index` работает | установка инструментов | — |
| RLIMIT_CPU / RLIMIT_AS (setrlimit) | ✅ понижение работает (тест: CPU→(2,5), AS→256MB/1GB применились); NPROC уже ограничен (14617) | E | через `resource.setrlimit` |
| `unshare --user` (userns) | ⚠️ НЕ ПОДТВЕРЖДЕНО — окружение proot-подобное: команда возвращает 0, но `unshare --net` НЕ изолирует сеть (коннект прошёл), `/sys/class/net` недоступен | E | не обещать; G-E закрыт на subprocess+limits MVP-tier; hardened isolation — future |
| pylint / radon / flake8 / bandit | ✅ **установлены** (2026-08-23): pylint 4.0.7, radon 6.0.1, flake8 7.3.0 (ранее битый — переустановлен), bandit 1.9.4; smoke-тест OK | F | адаптеры (sensors) поверх готовых тулзов; ruff не ставили — его уникальная ценность не подтверждена |
| fsrs-библиотека | ✅ установлена `fsrs 6.3.2`; единственный кандидат PyPI (`fsrs4python`/`sm2`/`fsrs-scheduler` отсутствуют); API проверен; см. [`FSRS_NOTE.md`***REMOVED***(FSRS_NOTE.md) | I | `enable_fuzzing=False` + aware UTC + rating mapping таблица |
| fastapi + uvicorn | ⏳ не проверялось (нужно на Phase L) | L | проверить при старте L |
| static UI | ✅ stdlib http.server + FastAPI StaticFiles | M | — |
| fastapi + unicorn в Termux | L | приложение layer |
| static UI | M | stdlib/http.server + FastAPI StaticFiles |

## 5. Sequential gates

```text
P0  → G0: blueprint принят
P1  → G1: контейнер проекта, регистрация в сводке
P-B+C → G-BC: pytest green; dry-run отчёт; corpus; gap report; idempotency
P-D → G-D: grading contract стабилен; student vs infra failures
P-E → G-E: 8 security/limit tests; честные лимиты (network/filesystem isolation не обещаны)
P-F → G-F: AST rules + adapters + false-positive tests
P-G → G-G: hint escalation/без LLM
P-H → G-H: state machine + rebuild + explainability
P-I → G-I: FSRS + due state
P-J → G-J: eligibility/selection policy + determinism
P-K → G-K: project engine + cap
P-L → G-L: API contracts (0 бизнес-логики)
P-M → G-M: UI через API только
P-N → G-N: E2E сценарии + determinism доказан
P-O → G-O: LLM-слой поверх стабильного ядра (опционально)
```

## 6. Оценка объёма по фазам (ориентир)

| Фаза | Размер | Ожидаемые сессии | Ключевой риск |
|---|---|---|---|
| B+C | L | 6–10 | лицензии/структура Exercism, mapping качества |
| D | M | 2–4 | pytest isolation, нормализация |
| E | S–M | 1–3 | ограничения Termux; честность лимитов |
| F | M | 2–4 | false positives, Bandit policy |
| G | S | 1–2 | банк подсказок L0–L6 на паттерны (контент!) |
| H | M | 2–4 | корректные transition rules + rebuild |
| I | S | 1–2 | выбор lib + rating mapping |
| J | M | 2–3 | policy приоритизации |
| K | S–M | 1–3 | вопросы дерева ТЗ |
| L | M | 2–3 | thin layer, contracts |
| M | M | 2–4 | UI минимализм, без learning logic |
| N | M | 2–3 | синтетические сценарии full-loop |
| Итого ядро (B+C…N) | XL | ~24–42 | — |

Оценки условные, уточняются после B+C (первые фактические часы дам в STEPS).

## 7. Open decisions (регистрируются в ADR по мере решения)

1. ~~FSRS-библиотека (fsrs / SM-2 wrapper) — research перед Phase I, ADR.~~ → **закрыто 2026-08-23:** установлен и проверен `fsrs 6.3.2` (см. FSRS_NOTE.md); формализация ADR — в Phase I.
2. ~~Evidence → FSRS rating mapping (Again/Hard/Good/Easy) — зафиксировать таблицей до Phase I (blueprint §8).~~ → **закрыто 2026-08-23:** таблица в FSRS_NOTE.md §3 (exercise_result/review_score → Again/Hard/Good/Easy; hint_used/error_detected сами по себе review не создают).
3. Доступность `unshare --user` / RLIMIT на текущем Termux — проверить перед E (blueprint §9 action item).
4. Доступность pylint/radon/bandit в Termux — проверить перед F; fallback AST-правила.
5. Источники после Exercism: freeCodeCamp, Google Python Class, MIT 6.0001 — **только** после gap-анализа B+C и отдельного license gate (prompt1 §35 запрещает в B+C).
6. Приоритизация в J (due-review vs новые темы; blueprint §8, prompt2 Phase J §4).
7. Использовать ли платформенный Forge pipeline (core_02/forge_facade.py) для исполнения фаз — опционально, см. STEPS.

## 8. Artifact placement

| Этап | Артефакты |
|---|---|
| P1 | MANIFEST/README/SPEC/STEPS/LESSONS/RUNNABLE/CHECKLIST/ROADMAP/decisions/project.yaml |
| B+C | `app/curriculum/`, `app/ingestion/`, `data/corpus/`, `configs/competency_map.yaml`, `configs/exercise_overrides.yaml`, `docs/curriculum_v0.1.md`, `docs/exercism_ingestion.md`, fixtures `tests/fixtures/exercism/`, план: `PHASE_BC_PLAN.md` |
| D | `app/grading/` (contract, runner) |
| E | `app/execution/` (job, policy, backend) |
| F | `app/diagnostics/` (contract, ast_rules, engine, adapters, patterns) + `docs/diagnostics_v0.1.md` |
| X5 | `app/localization/` (contract, extractor, validator, workflow, provider, Gemini rotation, CLI) + `prompt_localization.md` + `docs/localization_v0.1.md` |
| G | `app/hints/` |
| H | `app/evidence/` |
| I | `app/scheduler/` |
| J | `app/selector/` |
| K | `app/projects/` + `data/projects/` |
| L | `app/api/` |
| M | `web/` |
| N | `tests/e2e/` + отчёт валидации |

## 8.1 Localization track (cross-cutting, not a replacement for P0–N)

- **Source:** approved English Exercism clone remains canonical.
- **Current inventory:** 432 learner-facing Markdown documents, ~1,022,490 characters, generated by `localize scan`.
- **Target:** Russian `ru` projection under generated `data/localization/`; current status is missing until a provider creates reviewed drafts.
- **Update rule:** source hash mismatch → `stale`; upstream refresh never overwrites translations silently.
- **LLM rule:** external provider → draft only → structural/hash validation → reviewed publication; no direct writes to curriculum/evidence/learning state.
- **Provider:** explicit `GeminiTranslationProvider` uses the ignored root `.keys/gemini_active.keys` pool (three local credentials, no values in logs); retryable API failures rotate to the next key.
- **Open operational dependency:** review and publish drafts; credentials remain outside deterministic core and the full 432-document batch is not run implicitly.

## 9. Risk register

| Risk | Стадия | Mitigation |
|---|---|---|
| Exercism структура/лицензия неоднородна | B+C | ✅ audit выполнен (Шаг 2): единый MIT по всему дереву; evidence — [`docs/exercism_research.md`***REMOVED***(docs/exercism_research.md); при изменениях upstream — повторный audit по change-detection |
| Том corpus велик для телефона | B+C | хранить метаданные + content policy (ссылка vs локально, prompt1 §15) |
| Student code опасен | D–E | отдельный subprocess, temp dir, limits, MVP-tier честно, без обещаний isolation |
| False positives статанализа | F | positive/negative/edge тесты на каждое правило |
| Translation drift / hallucination | X5 | source hashes, protected Markdown validation, reviewed-only publication, English fallback |
| Transition rules неточны | H | сценарии beginner/struggling/strong в N |
| FSRS-библиотека недоступна в Termux | I | fallback SM-2 реализация под единый интерфейс |
| Mapping «машинный» ломает понимание уровня | B+C | mapping_confidence + manual overrides + low-confidence report |
| Постоянный scope creep (FastAPI/UI ранее L/M) | все | гейты G-, запрет перескоков из prompt1 §3/35/§40 |

## 10. Definition of Done финального релиза (ядра, P-N)

- [ ***REMOVED*** все gates G0–GN closed;
- [ ***REMOVED*** pytest: ALL TESTS PASS (полный комплекс);
- [ ***REMOVED*** `ingest exercism` идемпотентно (N при повторном = N);
- [ ***REMOVED*** coverage и gap-отчёты существуют;
- [ ***REMOVED*** evidence state реконструируется из лога (rebuild);
- [ ***REMOVED*** одинаковый state → одинаковые decisions (детерминизм доказан);
- [ ***REMOVED*** LLM в контуре = 0;
- [ ***REMOVED*** нет evidence из диагностических метрик (contract enforcement);
- [ ***REMOVED*** `CHANGELOG`/`RUNNABLE`/`CHECKLIST` актуальны.

## 11. Current status и next action

**✅ PHASE B+C COMPLETE (2026-08-23, G-BC):** Competency Map v0.1 (25 компетенций, 11 групп, ДАГ 34 ребра, покрытие 45/67 concepts) + Exercism Ingestion (161 упражнение, license-gated, идемпотентный, corpus `data/corpus/corpus_v0.1.db`) + CLI `python -m app ingest/report` + отчёты coverage/gaps/low-confidence/license + 37 unit- и 2 integration-теста, mypy 0 ошибок. Доказательства: `docs/exercism_research.md`, `docs/curriculum_v0.1.md`, `docs/exercism_ingestion.md`, отчёт A–I в STEPS Шаг 10.

**✅ PHASE D COMPLETE (2026-08-23, G-D):** `app/grading/` содержит immutable contract, approved-corpus catalog adapter и isolated pytest runner. Нормализуются PASS/FAIL/ERROR/TIMEOUT/INFRASTRUCTURE_ERROR; student/grader failure разделены; partial test counts сохраняются; выдаются только evidence candidates. Проверено 13 Phase D-тестами; итоговый suite после Phase E — 58 passed, 2 integration skipped, mypy без ошибок. Подробности: [`docs/grading_v0.1.md`***REMOVED***(docs/grading_v0.1.md).

**✅ PHASE E COMPLETE (2026-08-24, G-E):** `app/execution/` содержит `ExecutionJob/Policy/Result`, replaceable backend и `TermuxSubprocessBackend` с process-group cleanup, timeout, CPU/output/address-space policies и sanitized environment. Проверено 8 hermetic execution-тестами. В proot `RLIMIT_AS` не включается в pytest grader из-за ложных bootstrap timeout; network/filesystem/public security isolation не заявляются. Подробности: [`docs/execution_v0.1.md`***REMOVED***(docs/execution_v0.1.md) и [`ADR-005`***REMOVED***(decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md).

**✅ PHASE F COMPLETE (2026-08-24, G-F):** `app/diagnostics/` содержит ordered ASTRule registry (7 правил), AST syntax normalization, immutable `Diagnostic/SensorReport`, Pylint/Radon/Flake8/Bandit adapters и reference-only error-pattern mapping. Проверено 14 hermetic diagnostic-only тестами и live smoke установленных сенсоров; `mypy` без ошибок. MI, diagnostic counts и severity не создают evidence. Подробности: [`docs/diagnostics_v0.1.md`***REMOVED***(docs/diagnostics_v0.1.md).

**Следующий action: Phase G** (Hint Engine): deterministic hint bank + escalation policy, без LLM и без auto-evidence. Localization Track X5 остаётся отдельным review-gated потоком.

**Localization status:** source scan/status/validation plus optional Gemini rotation implemented (ADR-006); RU projection currently `432 draft/missing`, а Gemini создаёт drafts в отдельном ignored-каталоге и не публикует их автоматически.

## Cross-links

- [`MANIFEST.md`***REMOVED***(MANIFEST.md) · [`README.md`***REMOVED***(README.md) · [`SPEC.md`***REMOVED***(SPEC.md) · [`STEPS.md`***REMOVED***(STEPS.md) · [`LESSONS.md`***REMOVED***(LESSONS.md) · [`CHECKLIST.md`***REMOVED***(CHECKLIST.md) · [`RUNNABLE.md`***REMOVED***(RUNNABLE.md)
- [`decisions/DECISIONS.md`***REMOVED***(decisions/DECISIONS.md) + ADR-001…005
- Каноны: [`prompt1.md`***REMOVED***(prompt1.md) (Phase B+C DoD) · [`prompt2.md`***REMOVED***(prompt2.md) (Phase D–N DoD) · [`prompt3.md`***REMOVED***(prompt3.md) (master prompt)
- Платформа: [`../../docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) · [`../../docs_10/core/PROJECT_REQUIREMENTS.md`***REMOVED***(../../docs_10/core/PROJECT_REQUIREMENTS.md) · [`../../docs_10/projects_meta/PROJECTS_OVERVIEW.md`***REMOVED***(../../docs_10/projects_meta/PROJECTS_OVERVIEW.md)