# FSRS_NOTE.md — Интеграция FSRS (Phase I): API и rating mapping

> **Дата:** 2026-08-23 · **Версия:** 0.1.0 · **Статус:** input для Phase I (библиотека установлена и проверена)
> **Кандидат PyPI → установлен:** `fsrs 6.3.2` (единственный подходящий на PyPI; `fsrs4python`, `sm2`, `fsrs-scheduler` недоступны)
> **Проверено в окружении:** Termux/Python 3.14.6 — установка `pip install fsrs==6.3.2` успешна, импорт и сериализация работают.

---

## 1. Зачем это в проекте (связь с планом)

- Phase I (ROADMAP P-I) использует **готовый алгоритм FSRS**, единица планирования — **competency** (не flashcard) (blueprint §8; prompt2 Phase I).
- Этот документ закрывает open decision **ROADMAP §7.2** («evidence → FSRS rating mapping — зафиксировать таблицей до Phase I»).
- Библиотека устанавливается сейчас (а не на Phase I), чтобы **проверить API реально**, а не по памяти — и зафиксировать нюансы (naive/aware datetime, сериализация).

---

## 2. API библиотеки fsrs 6.3.2 (проверено интерактивно)

### Основные типы

```python
import datetime, fsrs

card = fsrs.Card()                                   # card_id: int | None; state(Learning/Review/Relearning); step; stability; difficulty; due; last_review
log  = fsrs.ReviewLog(card_id=card.card_id, rating=fsrs.Rating.Good,
                      review_datetime=<aware-now>, review_duration=None)   # review_duration ОБЯЗАТЕЛЕН (может быть None)
sched = fsrs.Scheduler()                       # параметры по умолчанию (FSRS-4.5, desired_retention=0.9, learning_steps=(60s, 600s), relearning_steps=(600s,), max_interval=36500, enable_fuzzing=True)
```

### Основной цикл (проверено)

```python
new_card, new_log = sched.review_card(card, rating, review_datetime, review_duration=None)
# rating: fsrs.Rating.Again/Hard/Good/Easy; return (new_card, new_log)
sched.reschedule_card(card, ...)  # перепланирование без фиксации
sched.get_card_retrievability(card, now)  # retrievability (для overdue-логики)
```

### Сериализация

```python
d = card.to_dict()        # {'card_id','state','step','stability','difficulty','due','last_review'***REMOVED***
c2 = fsrs.Card.from_dict(d)  # roundtrip OK (стабильность совпадает)
sd = sched.to_dict(); s2 = fsrs.Scheduler.from_dict(sd)  # параметры
to_json/from_json тоже есть
```

### Критичные нюансы для интеграции

1. **`review_datetime` обязан быть timezone-aware (UTC)**. Naive datetime → `TypeError: unsupported operand type(s) for -: datetime.datetime and int`. Все даты в проекте — aware UTC (как в public_request_parser contracts).
2. **`ReviewLog.review_duration` обязателен** (может быть `None`) — несёт время решения; не data-essential для ядра.
3. **`enable_fuzzing=True` по умолчанию** — нарушает детерминизм: для ядра **обязательно `Scheduler(enable_fuzzing=False)`**.
4. `state` — enum `Learning(1)/Review(2)/Relearning(3)`; интервалы из `due` (datetime), stability, difficulty.
5. `card_id` — авто-генерится (int).

---

## 3. Rating mapping — детерминированная таблица evidence → Rating

(согласовано 2026-08-23; это решение ROADMAP §7.2, формализуется ADR в Phase I)

| Evidence-сигнал | Условие | FSRS Rating |
|---|---|---|
| **exercise_result (прошло)** | hints_used == 0 | `Easy` |
| **exercise_result (прошло)** | hints_used == 1, level ≤ L1 | `Good` |
| **exercise_result (прошло)** | hints_used ≥ 2 ИЛИ max_hint ≥ L2 | `Hard` |
| **exercise_result (не прошло)** | любое | `Again` |
| **review_score* (S4/S5-подтверждение)** | score ≥ 0.8 | `Easy` |
| **review_score** | 0.5 ≤ score < 0.8 | `Good` |
| **review_score** | score < 0.5 | `Hard` |
| **hint_used** (сам по себе) | — | НЕ создаёт review (только сигнал для exercise_result) |
| **error_detected** | — | НЕ создаёт review (только для диагностики/Mentor) |
| **theory_completed / verification** | — | НЕ review-события (S0→S2) |

Правило карты: **hint usage → rating**. Воспроизводимо, без LLM; все даты — aware UTC; rating только при значимом evidence (успех/неудача по задаче). Чистая функция: `map_evidence_to_fsrs_rating(evidence) -> Rating`.

Обоснование:
- Успех без подсказок = «легко» (Easy — интервал растёт быстро);
- 1 подсказка ≤ L1 = уверенное усвоение (Good);
- ≥2 подсказок или более высокий уровень = закрепление (Hard, короче интервал);
- провал = переучить (Again);
- review_score ≥ S4 = подтверждение переноса (Easy), средний — закрепление (Good), слабый — усилить (Hard).

---

## 4. Архитектура Phase I (кратко): как встраивается

```text
Evidence (exercise_result / review_score)
  → map_evidence_to_fsrs_rating()      [эта таблица***REMOVED***
  → Scheduler(enable_fuzzing=False).review_card(card_for_competency, rating, aware_now)
  → обновить review_states (SQLite): card dict + next_review_date
  → get_due_competencies(now) -> [competency_id***REMOVED***  (просто список, без selection — Phase J)
```

Единица — **competency**: 1 card per competency (card_id = competency_id hash или slug); `review_states` отдельная таблица (не путать с competency state S-уровня — это learning state, не scheduling).

## 5. Напоминание для реализации (Phase I)

- [ ***REMOVED*** Использовать `fsrs==6.3.2`; версия зафиксирована в этой заметке (в requirements — на Phase I).
- [ ***REMOVED*** Все datetime — aware UTC; сконвертировать на входе.
- [ ***REMOVED*** `Scheduler(enable_fuzzing=False)` в коде ядра (детерминизм!), с параметрами по умолчанию (или explicit parameters).
- [ ***REMOVED*** rating mapping — через единую функцию (таблица выше), покрыть юнит-тестами (каждый столбец).
- [ ***REMOVED*** Реализовать `get_due_competencies()` без selection (это Phase J).
- [ ***REMOVED*** Схема: `review_states (competency_id PK, card_json, due_at, last_review_at)` + `review_events`.
- [ ***REMOVED*** Файл заметки: `FSRS_NOTE.md` оставить как living doc при Phase I (после реализации phaseI может актуализироваться версию).

## 6. Cross-links

- [ROADMAP.md***REMOVED***(ROADMAP.md) — Фаза P-I, Open decisions §7.1/7.2 (закрывает 7.1 кандидатом+проверкой; 7.2 — таблицей)
- [STEPS.md***REMOVED***(STEPS.md) — запись Шаг 5 (эта проверка)
- `python_ai_tutor_blueprint_v0.1.md` §8 — FSRS integration boundary