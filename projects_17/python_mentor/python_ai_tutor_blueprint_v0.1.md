# Deterministic Core — Architecture Blueprint v0.1

Синтез research-отчёта агента + привязка к методике (`python_ai_tutor_methodology.md`). Это фиксация контрактов ДО реализации — агент получает команду на код только после подтверждения этого документа.

---

## 0. Модель угроз для sandbox — до всего остального

Отчёт агента предполагает nsjail/Docker — это правильно для публичной multi-tenant платформы, но НЕ соответствует текущей реальности:

- levi недоступен → работаем локально в Termux (нерутованный Android);
- nsjail/Docker требуют unprivileged user namespaces или root — на стоковом Termux это обычно не работает вообще, надо отдельно проверять (`unshare --user echo ok`), не считать доступным по умолчанию;
- пользователь ровно один — сам Максим гоняет свой же код, это не untrusted multi-tenant сценарий.

**Решение — два явных tier'а, интерфейс между ними одинаковый (Job → Worker → Sandbox → Result), поэтому смена tier'а не требует переписывать остальную систему:**

| | MVP-tier (сейчас, Termux) | Hardened-tier (потом, levi) |
|---|---|---|
| Изоляция | `subprocess` + resource limits (RLIMIT_CPU, RLIMIT_AS) + timeout + отдельный непривилегированный пользователь если возможно | nsjail или Docker с network isolation, filesystem restrictions |
| Сеть | Запрещена на уровне кода (нет прямого os-level firewall) | Запрещена на уровне контейнера |
| Область применения | Только локально, только для себя. НЕ выставлять наружу за пределы localhost | Можно расширять на других пользователей |
| Явный флаг в коде | `SANDBOX_TIER = "mvp_untrusted_single_user"` — чтобы не забыть, что это не production-safe | `SANDBOX_TIER = "hardened"` |

---

## 1. Competency Map (schema)

```
competency:
  id, name, description
  prerequisites: [competency_id***REMOVED***
  understand_criteria: text   # что должен объяснить
  can_do_criteria: text        # что должен уметь без подсказки
  typical_errors: [error_pattern_id***REMOVED***
  verification_exercise: exercise_id
  project_marker: text
```

S-уровни — машинно-проверяемые триггеры (из методики, раздел D), с явной оговоркой:

| Переход | Триггер (детерминированный) |
|---|---|
| S0→S2 | пройден explain-контент + верный ответ на проверочный вопрос |
| S2→S3 | первое решённое упражнение (любой hint level) |
| S3→S4 | 2 упражнения подряд закрыты на hint_level ≤ L1 |
| S4→S5 | evidence-событие `project_usage` без явного напоминания темы |
| S5→S6 | **не вычисляется детерминированным ядром.** Требует оценки объяснения/критики (ось Thinking) — помечается статусом `pending_llm_review`, не блокирует остальную систему, просто такие компетенции всегда идут с флагом "нужен LLM-проход, когда будет доступен". |

Это важная граница, которую стоит зафиксировать явно: детерминированное ядро доводит компетенцию максимум до S5 самостоятельно.

---

## 2. Exercise Schema

```
exercise:
  id, source_id, type(concept|practice)
  competency_id, skill_tags: [text***REMOVED***
  difficulty_rung(repetition|analogy|new|unfamiliar_context|combination|independent)
  tests_ref, reference_solution_ref

exercise_source (provenance):
  id, url, repo, file
  detected_license, license_evidence
  redistribution_allowed: bool
  modification_allowed: bool
  attribution_required: bool
  status(pending|approved|rejected)
```

Жёсткое правило: ни одно упражнение не попадает в живой банк, пока `exercise_source.status != approved`. Approval — ручной шаг, не автоматический.

---

## 3. Evidence model

```
evidence_event:
  id, timestamp, competency_id, exercise_id (nullable)
  event_type(submission | hint_used | error_detected | project_usage | review_score)
  payload: json
```

Competency state — чистая функция от лога evidence-событий (fold), не мутируемое поле напрямую. Следствие: состояние можно пересобрать из лога в любой момент — полезное свойство для отладки и для будущего датасета.

---

## 4. Grading contract

```json
{
  "submission_id": "...",
  "correctness": 0.94,
  "python_quality": 0.72,
  "engineering": {
    "cyclomatic_complexity": 6,
    "function_length": 42,
    "maintainability_index": 61
  ***REMOVED***,
  "security": null,
  "detected_patterns": ["mutable_default_argument"***REMOVED***
***REMOVED***
```

Правила контракта:
- `maintainability_index` — только диагностика, никогда не идёт напрямую в evidence как оценка (согласно предупреждению самого Radon);
- `security` — `null`, пока компетенция ученика не дошла до "security-eligible" уровня по curriculum (Bandit не показывается новичку на втором уроке);
- любое поле с пометкой diagnostic-only физически не может создавать evidence_event — это проверяется на уровне кода, не соглашением.

---

## 5. Error-pattern model

```
error_pattern:
  id, detector(pylint_rule|bandit_id|ast_rule|custom)
  competency_id
  error_type(conceptual|syntax|decomposition|debugging|transfer|dependency)  # из методики, раздел H
  hint_bank_ref
```

Пример: `R1702 (pylint) → competency=code_structure → error_type=decomposition → hint_bank=nesting`.

---

## 6. Hint model L0–L6

```
hint_bank:
  id, pattern_id (nullable — часть подсказок общие, не привязаны к паттерну)
  level(L0..L6), text
  requires_permission: bool   # true для L4+
  project_mode_cap: bool      # true = недоступен в режиме Заказчика (потолок L3)
```

Функция эскалации — чистая, без состояния кроме текущего уровня:
`next_hint_level(current_level, stuck_signal) -> level` — поднимает на 1, никогда не прыгает, всегда стартует с L0 на новом упражнении (правила из промта Ментора).

---

## 7. Learning State Machine

```
State = { competency_id: s_level, for each competency ***REMOVED***
Evidence Log → Transition Rules → new State
State + Curriculum Prerequisites → Eligible Activities → Next Activity
```

Пример:
```
functions=S4, loops=S4, dicts=S3, error_handling=S2
  → next: error_handling.practice

functions=S5, loops=S5, collections=S5, files=S4
  → project_eligible=true
```

Важная граница: не все решения полностью автоматизируются. Точки, требующие живого суждения (S6, ось Thinking, "3+ повтор одной ошибки → возможно, тема пройдена слишком быстро" из методики) возвращают исход `escalate_to_llm_or_human`, а не решение сами — это не баг, это честная граница детерминированного ядра.

---

## 8. FSRS integration boundary

Единица планирования — **компетенция**, не отдельная карточка.

```
on evidence_update:
  rating = map_evidence_to_fsrs_rating(hint_level_used, correctness)
  fsrs.review(card=competency_card, rating=rating)
  → next_review_date

Learning State Engine при выборе next activity сверяется со списком
"due for review" наравне с новыми темами (не приоритет по умолчанию —
конкретное правило приоритезации нужно решить отдельно: например,
due-review сначала, если due date просрочен более чем на N дней).
```

Маппинг evidence → FSRS rating (Again/Hard/Good/Easy) — нужно зафиксировать таблицей отдельно перед реализацией, в отчёте агента этого нет.

---

## 9. Sandbox boundary

См. раздел 0 — двухуровневая модель. Интерфейс единый независимо от tier'а:

```
Submission API → Job Queue → Execution Worker → Sandbox → 
  {pytest, AST rules, Pylint, Radon, Flake8, Bandit***REMOVED*** → Normalized Result
```

Action item перед реализацией MVP-tier: проверить `unshare --user` в конкретном Termux-окружении — если хоть что-то из user namespaces доступно, MVP можно сделать чуть безопаснее, чем голый subprocess.

---

## 10. SQLite logical schema

```
competencies, competency_prerequisites
exercises, exercise_sources, exercise_competencies
submissions, test_results, static_analysis_results
error_patterns, detected_errors, hint_bank
student_competencies, competency_evidence
review_states (FSRS state per competency), review_events
learning_events (evidence log)
```

Финальные ORM-модели — после подтверждения этого документа, не раньше.

---

## 11. Source/license provenance model

Формализовано в разделе 2 (`exercise_source`). Правило: Exercism (MIT, формат) — основной источник, freeCodeCamp (BSD-3) и Google Python Class (Apache 2.0, но file-level audit обязателен) — дополнительные, MIT 6.0001 (CC BY-NC-SA) — маркируется отдельно как non-commercial reference и не смешивается с permissive corpus, Python Docs (PSF/Zero-Clause BSD) — reference-слой, не банк упражнений.

---

## 12. API boundaries

```
Learning API:
  GET /next-activity
  GET /competency-map
  GET /profile

Submission API:
  POST /submit {exercise_id, code***REMOVED*** -> job_id
  GET  /result/{job_id***REMOVED***

Review API (для случаев pending_llm_review):
  POST /review-note {submission_id, thinking_axis_note***REMOVED***
```

---

## Что дальше

Blueprint фиксирует контракты. Следующий шаг для агента — **Phase B + C**: реализовать Competency Map (раздел 1) и ingestion только для Exercism (единственный источник с явно чистой лицензией на формат), без sandbox и без остальных источников — это можно начинать уже сейчас, независимо от того, вернётся ли levi.
