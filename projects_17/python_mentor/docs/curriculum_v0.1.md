# Curriculum v0.1 — Competency Map python_mentor

> **Версия:** 0.1.0 · **Дата:** 2026-08-23 · **Источник:** `configs/competency_map.yaml` (генерируется `tools/gen_competency_map.py`)
> **Фаза:** B+C (Шаги 3, 7) · pronto1 §6–§9, §34

## 1. Карта компетенций (25, 11 групп)

Источник данных о компетенциях — **YAML**, не код. Эта страница — человекочитаемое зеркало; правки — в `configs/competency_map.yaml` (затем `python3 tools/gen_competency_map.py`).

| # | id | Группа | Prerequisites | Verification exercise |
|---|---|---|---|---|
| 1 | variables | python_fundamentals | — | guidos-gorgeous-lasagna |
| 2 | primitive-types | python_fundamentals | variables | currency-exchange |
| 3 | expressions | python_fundamentals | primitive-types | difference-of-squares |
| 4 | boolean-logic | python_fundamentals | expressions | ghost-gobble-arcade-game |
| 5 | conditionals | control_flow | boolean-logic | log-levels |
| 6 | loops | control_flow | conditionals | making-the-grade |
| 7 | comprehensions | control_flow | loops, lists | flatten-array |
| 8 | lists | collections | expressions | list-ops |
| 9 | tuples | collections | lists | cater-waiter |
| 10 | dicts | collections | lists | inventory-management |
| 11 | sets | collections | lists | restaurant-rozalynn |
| 12 | functions | functions | conditionals, loops | hello-world |
| 13 | function-parameters | functions | functions, tuples | two-fer |
| 14 | scope-decomposition | functions | functions | matching-brackets |
| 15 | strings | strings | primitive-types | reverse-string |
| 16 | string-methods | strings | strings | isogram |
| 17 | exceptions | exceptions | functions, conditionals | error-handling |
| 18 | modules | modules | functions | little-sisters-vocab |
| 19 | classes | oop | dicts, functions | ellens-alien-game |
| 20 | class-inheritance | oop | classes | diamond |
| 21 | files-io | files_io | string-methods, modules | word-count |
| 22 | testing | testing | functions, exceptions | pytest-мини-сют |
| 23 | code-structure | code_structure | functions, scope-decomposition | собственный модуль |
| 24 | iterators-generators | control_flow | loops, functions | series |
| 25 | unpacking | functions | tuples, function-parameters | making-the-grade |

Каждая компетенция в YAML несёт `understand_criteria`, `can_do_criteria`, `typical_errors`, `verification_exercise`, `project_marker` — контракт для последующих фаз (Grader, Hints, Evidence).

## 2. Prerequisites-граф (инварианты)

- DAG: проверяется валидатором при каждом запуске (`validate_competency_map`, тест на цикл — `test_cycle_detected`);
- корни: `variables` (единственный с пустыми prerequisites);
- CI-гейт: любое изменение YAML с циклом/битой ссылкой — `python -m app.curriculum.map` exit 2.

## 3. Покрытие Exercism concepts

- 67 concepts из exercism/python:
  - **45 — покрыты** (замаплены на компетенции);
  - **22 — явно в `unmapped_exercism_concepts`** (advanced v0.1): bitwise, descriptors, recursion, regex, decorators и др. — кандидаты в новые компетенции Phase D+.
- Правило: никакого concept без статуса — «покрыт ИЛИ в unmapped», иначе валидатор гейта.
- Проверка: `python3 -m app.curriculum.map configs/competency_map.yaml --concepts data/exercism_src/concepts`

## 4. Difficulty principles

- `source_difficulty` — исходное из Exercism (1..10);
- `pedagogical_rung` — маппинг по лестнице (blueprint §2): repetition → analogy → new → unfamiliar_context → combination → independent;
- Инвариант: rung и source difficulty хранятся **раздельно** (colonne в exercises), маппинг — детерминированная функция, см. `app/ingestion/pipeline.py::rung_from_difficulty`.

## 5. Provenance и license (кратко)

Полный аудит — [`exercism_research.md`***REMOVED***(exercism_research.md). Источник `exercism-python` — единственный, **approved (MIT)**, evidence в `configs/sources.yaml`. Правило (ADR-004): approved → live; pending/rejected/unknown → нет; reference solutions — только с `--with-refs`.

## 6. Ingestion workflow

```
python3 -m app ingest exercism --dry-run    # что найдёт (161 упражнения, без записи)
python3 -m app ingest exercism              # идемпотентный импорт в data/corpus/corpus_v0.1.db
python3 -m app ingest exercism --report     # + convergence/gap/low-license отчёты
python3 -m app report coverage              # отчёт по компетенциям
python3 -m app report gaps                  # gap-анализ
python3 -m app report low-confidence        # ручные ревью-кнеки
python3 -m app report license               # статус источников
```

## 7. Known limitations

1. Map v0.1 — 25 компетенций: не покрывает экзотику (bitwise, regexes, async, memoryview).
2. Mapping основывается на practices/prerequisites из track config; упражнения без явных меток — low/override, попадают в low-confidence отчёт.
3. Некоторые компетенции имеют 0–1 упражнение (gap report показывает честно — content gap fix: следующий источник или ручное дополнение).
4. Curriculum не является «планом обучения» — последовательность выбора упражнений — Phase J.

## Cross-links

- `configs/competency_map.yaml` — источник истины; `tools/gen_competency_map.py` — генератор
- `app/curriculum/map.py` — валидатор/загрузка
- `PHASE_BC_PLAN.md` — детальный план B+C (Шаги 3, 7)
- `[exercism_ingestion.md***REMOVED***(exercism_ingestion.md)` — как развернуть ingestion