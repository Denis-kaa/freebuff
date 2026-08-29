# PHASE_BC_PLAN.md — Детальный план Phase B+C
# Competency Map v0.1 + Exercism Ingestion Pipeline v0.1

> **Версия:** 0.1.0 · **Дата:** 2026-08-23
> **Исполняется по:** [`prompt1.md`***REMOVED***(prompt1.md) (обязательный источник), контракты — [`python_ai_tutor_blueprint_v0.1.md`***REMOVED***(python_ai_tutor_blueprint_v0.1.md)
> **Цель:** два работающих компонента: машинно-читаемая карта компетенций и идемпотентный ingestion лицензионно-чистого корпуса Exercism в SQLite (metadata + content policy), с отчётами coverage/gaps/low-confidence.
> **Результат фазы:** статус `PHASE B+C COMPLETE · WAITING FOR REVIEW` (prompt1 §40) и gate G-BC из [ROADMAP.md***REMOVED***(ROADMAP.md).

---

## 0. Стартовые решения (фиксируются до кода)

| # | Решение | Обоснование | Статус |
|---|---|---|---|
| S0-1 | Python 3.14.6 (окружение; target ≥3.11 выполнен) | prompt1 §5 | ✅ принято |
| S0-2 | Структура кода: `app/` пакет (как `public_request_parser`), `configs/`, `data/`, `docs/`, `tests/` | prompt1 §33: адаптировать к существующему repo; repo пуст → минимальная структура | ✅ принято |
| S0-3 | Зависимости: только stdlib + PyYAML 6.0.3 (проверен в окружении) | минимум зависимостей; конфиг мапы в YAML | ✅ принято |
| S0-4 | CLI: `python -m app ingest exercism [--source DIR***REMOVED*** [--dry-run***REMOVED*** [--force***REMOVED*** [--report***REMOVED***` | prompt1 §24: `<package> ingest exercism`; поддержка флагов | ✅ принято |
| S0-5 | Способ получения корпуса: **shallow clone** (`git clone --depth 1`) официального `exercism/python` в `data/exercism_src/`; runtime ingestion умеет работать по локальной директории (`--source`), полностью offline | prompt1 §30: сеть только для получения официального источника; локальный source directory обязателен | ✅ принято (Шаг 2: commit `1f6aab8…`, 14 MiB, 2 211 файлов — evidence в [`docs/exercism_research.md`***REMOVED***(docs/exercism_research.md)) |
| S0-6 | Хранение контента: **metadata всегда**; content (statement/tests) локально — только для `approved` источников; иначе ссылка | prompt1 §15 | ✅ зафиксировано (Шаг 2: все классы файлов approved → content локально; иначе ссылка — правило gate в S5) |
| S0-7 | Reference solutions: импорт — только с отдельным license evidence (`--with-refs`); иначе ссылкой | prompt1 §16 | ✅ зафиксировано (Шаг 2: evidence репо-лицензии получено; импорт — только с флагом) |

---

## 1. Последовательность шагов (с контрольными точками и рисками)

### Шаг 0 — Pre-flight и структура

**Закрывает:** prompt1 §4 (частично), §5, §33; автономность §7 платформы.

**Задачи:**
1. Зафиксировать окружение уже заполнено (Python 3.14.6, pytest 9.1.1, PyYAML 6.0.3, PyPI доступен) — в RUNNABLE.md (сделано 2026-08-23).
2. Создать каркас кода:
   ```
   app/__init__.py
   app/curriculum/         # модели, загрузка мапы, валидация
   app/ingestion/          # discovery, parser, license, mapping, pipeline, cli
   configs/competency_map.yaml
   configs/exercise_overrides.yaml
   data/exercism_src/      # локальная копия источника (gitignored)
   data/corpus/            # выходные SQLite-файлы (gitignored, содержание мутируется)
   docs/curriculum_v0.1.md, docs/exercism_ingestion.md (в Шаге 10)
   tests/unit/, tests/fixtures/exercism/, tests/integration/ (в Шаге 9)
   requirements.txt        # только pyyaml; остальное stdlib
   ```
3. Принять решение S0-5 (способ получения) с оценкой размера после первого листинга.
4. Создать первый пустой тест-suite, убедиться, что `pytest` собирает 0/1 тест без ошибок.

**Артефакты:** структура каталогов, `app/__init__.py`, smoke-тест, решение в STEPS.

**Контрольная точка (К0):** `python -m pytest tests/ -q` → «no tests ran» без ошибок импорта; каталоги существуют; решение S0-5 зафиксировано в STEPS.

**Риски:**
| Риск | Вер. | Влияние | Митигация |
|---|---|---|---|
| Структура повторяет «другой проект» не к месту | Н | — | Копируем conventions из public_request_parser (app/ + tests/ + fixtures/) |
| Git-репозиторий корпуса тяжёлый для телефона | С | блокирует S2/S6 | Решение по размеру до клона; при ❌ — скачать только config+подмножество упражнений (metadata-first), pipeline всё равно локальный |

### Шаг 1 — Inspection окружения и проектных фактов (prompt1 §4–§5)

**Задачи:**
1. Подтвердить, что `projects_17/python_mentor/` — пустой (без кода), нет существующих curriculum/competency/exercises/SQLite (проверка).
2. Зафиксировать версию Python (3.14.6) и решение по зависимостям (S0-3) в STEPS.
3. Проверить git status проекта (не удалять пользовательские `.bak`/документацию — они источники).

**CP:** запись в STEPS «Inspection: результат и решения»; ничего не удалено.

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| «Мусорный» код рядом с исходниками | С | Н | Рабочий каталог `app/` отдельно от `projects/doc/`; docics не трогаем |
| Принятие чужого варианта структуры без адаптации | Н | С | Адаптируем под существующий опыт платформы (public_request_parser) |

### Шаг 2 — Exercism research и фиксация license evidence (prompt1 §10–§11)

**Задачи:**
1. Получить официальный источник: `git clone --depth 1 https://github.com/exercism/python data/exercism_src/` (или решение S0-5).
2. Изучить структуру: `exercises/concept/*`, `exercises/practice/*`, `config.json` (track config, exercises: slug/blurb/difficulty/topics), `concepts/*/about.md`, `.meta/` файлы (example.py, tests), `LICENSE` файлы, `docs/`.
3. **License audit (пофайлово, prompt1 §11):**
   - репо `exercism/python` → LICENSE (MIT и т.п.), взять evidence (путь, текст, коммит);
   - проверить **по частям**: содержание упражнений, тесты, метаданные, support-файлы, reference solutions, docs;
   - выписать отдельные файлы со сторонними материалами (напр., упражнения, основанные на Project Euler и др.): отдельный статус, evidence.
4. Составить `docs/exercism_research.md`: структура репо, классы упражнений, license evidence блок (repo license + per-part), ограничения (коммерческое использование не запрашивается; локально для себя — ОК), mapped/не-mapped.
5. Зафиксировать вывод: какие части `approved` импортируются, какие `pending` (требуют ручного решения), какие `rejected`/не плиаствовать.

**Артефакты:** `docs/exercism_research.md` (с блоком license evidence), возможно ticket-записи в STEPS.

**CP (CP-2):** документ существует; маппинг «часть → статус лицензии → evidence» есть; решение по корпусу (S0-5) принято; diff-calculation не в scope.

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| Вывод «всё MIT ⇒ всё можно» | С | В | Пофайловый audit; evidence на каждый класс файлов; ничего unknown→live |
| Отдельные упражнения со сторонними лицензиями (Project Euler и др.) | С | С | Вынести в `external_attribution` с pending/rejected; не включать без ручного gate |
| Объём репо велик (больше 100 МБ) | С | С | shallow clone; при необходимости — только subset+metadata; документируем в research |
| Изменение структуры upstream между датами | Н | С | Фиксируем коммит (content_hash по дереву), fixtures воспроизводят структуру |

### Шаг 3 — Competency Map v0.1 (prompt1 §6–§9, §21)

**Задачи:**
1. Построить YAML `configs/competency_map.yaml` с минимальной, но полной картой (11 групп из §6 → 15–25 компетенций):
   `python_fundamentals` (variables, primitive_types, expressions, boolean_logic), `control_flow` (conditionals, loops, comprehensions), `collections` (lists, tuples, dicts, sets), `functions` (definition, parameters, return, scope, decomposition), `strings`, `exceptions` (raising/handling/custom), `modules`, `oop` (classes/instances/methods/inheritance/composition), `files_io`, `testing`, `code_structure`.
2. Каждая компетенция: `id` (lowercase, machine-readable, независим от Exercism), `name`, `description`, `prerequisites` (acyclic), `understand_criteria`, `can_do_criteria`, `typical_errors`, `verification_exercise`, `project_marker` (template из методики J; проектные маркеры краткие).
3. Сверка по Exercism concepts: посмотреть `exercises/concept/*` → убедиться, что карта покрывает факт. concepts (booleans, numbers, loops, dict, etc.); добавить отсутствующие (например `floating_point`?), объединять дубли → НЕ плодить искусственные.
4. С-совместимость: хранить «критерии», НО НЕ реализовывать state machine / `calculate_competency_state` (запрет §9).

**Артефакты:** `configs/competency_map.yaml`, `app/curriculum/map.py` (загрузка+валидация), валидатор на ацикличность.

**CP (CP-3):**
- validator exit 0 (unique IDs, required fields, valid prerequisites, no cycles);
- тест на детекцию цикла: добавить temporary cycle → pytest fail;
- мапа покрывает все Exercism concepts (сверка по research-документу).

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| Перерасширение карты (сотни компетенций) | Н | С | Минимальна версия (по §6), потом корректировка по факту Exercism |
| Непокрытие Exercism concept'ов | С | С | Research-документ + mapping tests: каждый concept должен мапиться (или явный `unmapped` список) |
| Цикличные prerequisites | Н | В | Валидатор строгий: test must fail; ручной обзор графа при создании |

### Шаг 4 — SQLite schema и constraints (prompt1 §22–§23)

**Задачи:**
1. Таблицы **только этого этапа** (prompt1 разрешает): `competencies`, `competency_prerequisites`, `exercise_sources`, `exercises`, `exercise_competencies` (+ опц. `exercise_tests` при необходимости).
   ❌ НЕ создавать: submissions, evidence, review_states, learning_events, student_competencies.
2. Схема: FK (PRAGMA foreign_keys=ON, CHECK-флаг в тестах), UNIQUE (напр. `exercises(source_id, slug)`/exercise id), индексы для `competency_id`, CHECK-constraints на enum-поля (difficulty_rung, exercise_type, source_status).
3. Отдельная миграция/версия схемы (`user_version` как в public_request_parser).

**Артефакты:** `app/storage/schema.py`, миграция v0.1.

**CP (4):** тесты:
- INSERT с несуществующим FK → IntegrityError;
- UNIQUE duplicate → IntegrityError;
- CHECK bad enum → IntegrityError;
- `PRAGMA foreign_keys` = ON проверено.

**Риски:**
- Соблазн «полезных» таблиц будущего (submissions и т.д.) → запрет по явному списку; только 5 таблиц.
- Ошибки энумов (тип тайпо) → CHECK + enum в Python-константах (Literal).

### Шаг 5 — Provenance + license gate (prompt1 §11–§13)

**Задачи:**
1. Модель `exercise_source`: id, source_name, repository, source_url, path, original_id, license, license_evidence (файл/строка/коммит), redistribution_allowed, modification_allowed, attribution_required, status (pending|approved|rejected), imported_at, content_hash.
2. License gate как функция: `can_be_live(source) <=> source.status == "approved"`; никаких «unknown → live».
3. Ручной шаг approval: механизм «подтвердить» (CLI `--approve source_id` или YAML-список approved sources с evidence из research), не автоматический.
4. Заполнение registry на основе research (Шаг 2) для: exercism (глобальный source), по частям (content/tests/etc).

**CP (5):** тест: exercise с source=pending → в `live corpus` не попадает; с approved → попадает; missing license → rejected/pending; source registry заполнен data из research.

**Риски:**
- Пропуск evidence → выводы; каждый approved обязан иметь license_evidence не пустой.
- Хранение контента: решение S0-6 (approved → content local; иначе ссылка) — фиксируется результатом.

### Шаг 6 — Ingestion pipeline (prompt1 §14–§17, §28, §30)

**Задачи:**
1. `Discovery`: обход `data/exercism_src/exercises/concept|practice` (или `--source`).
2. `Parse metadata`: `config.json`, `.meta/*.json`, `instructions README.md`, `.docs/instructions.md` (зависит от структуры — уточнить на research) → нормализованные поля.
3. `Parse exercise`: statement (условие), files (tests, example).
4. `Resolve provenance`: связь с exercise_source, content_hash (sha256 по файлам упражнения — для change detection).
5. `License gate` → статус.
6. `Competency mapping` — вызывает модуль Шага 7.
7. `Difficulty mapping`: source_difficulty (из Exercism) + pedagogical_rung (repetition..independent) **раздельно** (prompt §19).
8. `Validation` (модельные валидаторы §21) → `SQLite` (INSERT OR IGNORE/UPDATE на базе content_hash).
9. **Идемпотентность:** повторный ingestion → 0 новых записей; изменение upstream-фитбуры → update существующей (контрольный тест §28).
10. Пакетный режим (bounded batch) + чистая обработка ошибок (одна плохая запись не ломает pipeline; ошибки в отчёт).

**Артефакты:** `app/ingestion/discovery.py`, `parser.py`, `license.py`, `pipeline.py`.

**CP (6):** dry-run на фикстуре/локальном мини-корпусе: отчёт показывает discovered/parsed/approved/rejected/pending/concept/practice; повторный run идентичен; вызов без сети работает через `--source`.

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| Структура upstream не соответствует тому, что читаем (пути/имя файлов) | Н | В | Research-документ фиксирует факт. пути; fixture-мини-трек ловит расхождение; tolerant parser + warnings |
| Огромный корпус → память/CEP | С | Н | Поточно-батчированный walk; индексируем по мета, content не грузим в память целиком |
| Change detection со слоганом «импорт повторно создаёт дубль» | Н | В | content_hash + idempotency-тест в С9 |
| Обрыв сети/ошибка источника | Н | Н | Только `--source` для фикст; полный ingest выполняется локально после клона |

### Шаг 7 — Mapping engine + confidence + overrides (prompt1 §18–§20, §31–§32)

**Задачи:**
1. Rule-based mapping: primary competency (из `concepts`/`.meta`/blurb), скилл-теги; если отсутствует — эвристика по названию/описанию.
2. `mapping_confidence`: high (source metadata), medium (несколько признаков), low (эвристика) — сохраняется в базу.
3. Report по low-confidence: exercise_id, current_mapping, confidence, reason.
4. Manual overrides: `configs/exercise_overrides.yaml`:
   ```yaml
   monkeypatch:
     exercise_id: "hello-world"
     competency_id: functions.basics
     skill_tags: [strings, basics***REMOVED***
     difficulty_rung: repetition
     confidence: high
     override: true
   ```
5. Нельзя генерировать «псевдоуверенность»: где не определить — confidence=low + в отчёт + pending для рука (НЕ fake high), и **не LLM**.

**CP-7:** тесты: valid/invalid competency mapping; confidence; override приоритетнее эвристики; отчёт по low-confidence непустой на реальных данных (или обоснованно пуст).

**Риски:**
- Механическое маппинг «имя папки = компетенция» даёт ошибки → несколько источников признаков, low-confidence честно;
- Override-конфликты (двойной override) → детерминированная детекция (тревога) в выводе.

### Шаг 8 — CLI + reporting + gap analysis (prompt1 §24–§26)

**Задачи:**
1. CLI: `python -m app ingest exercism` + флаги `--source`, `--dry-run`, `--force`, `--report`; понятные exit codes (0 = ok, 2 = errors).
2. Отчёт ingestion (dry-run и успешный):
   Total discovered / parsed / approved / rejected / pending; concept vs practice; mapped/unmapped/low-confidence; tests available; reference solutions available; competency coverage (по-компетенции таблица: exercise_count, concept_count, practice_count, difficulty_distribution, mapping_confidence).
3. **Gap analysis** (без автоматического «ремонта»): компетенции с 0/1 упражнением, нет перехода к advanced rung, только 1 rung → CONTENT GAP REPORT.
4. `--report` может вызывать отдельные отчёты (coverage/gaps/low-confidence).

**Артефакты:** `app/ingestion/cli.py` (argparse), шаблоны отчётов.

**CP-8:** все команды работают на фикстурах и (обяз. на реальном небольшом корпусе) дают осмысленные цифры; gap-report честно показывает пробелы.

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| Отчёт не отвечает на вопрос «что импортировано» | Н | Н | CP-команда примера в документе; test CLI golden-output |
| CLI флаги несовместимы между запусками | Н | Н | `--dry-run` = ничтожная БД; `--report` = чтение существующей БД; дальнейший тест в чёрный ящик |
| Gap-report «пыльный» (мало данных) | Н | Н | Секция known-limitations; числа match research |

### Шаг 9 — Tests + fixtures (prompt1 §27–§29)

**Задачи:**
1. Fixtures: `tests/fixtures/exercism/` — мини-трек: 3 concept (booleans, numbers, strings), 3 practice (hello-world, two-fer, bob etc.) с условно-направленными тестами и metadata, **сохраняемая структура** реального репо (размер ~небольшой).
   - Не забыть LICENSE-файл в fixture → gate tests.
2. Unit tests по §27: competency (load, prereqs, cycle, duplicate IDs); source (approved/rejected/pending/missing license); ingestion (parsing, idempotency, duplicate prevention, update detection); mapping (valid/invalid, confidence); database (FK, constraints, PRAGMA).
3. Idempotency-test §28: run → N; run again → N; modify upstream fixture → update (не новый); проверка в составе теста.
4. Integration test (`tests/integration/`) — для полного upstream (помечаем `@pytest.mark.integration`, не выполняется по умолчанию; содержит предупреждение о сети).
5. Hermeticity: основные юниты без сети; фикстуры offline.

**Артефакты:** fixture-директория, ~25–35 юнит-теста.

**CP-9:** `pytest tests/ -q` — ALL PASS (offline); тест ПАДАЕТ при повторном импорте дублей; тест ПАДАЕТ при добавлении цикла в карту; idempotency test в составе.

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| Тесты зависят от live GitHub | С | Н | Fixtures локальные; network не используется в сюите (проверка `--disable-socket` необязат. для целостности, но можно env) |
| Fixture-мини-трек не отражает реальную структуру → ложная уверенность | Н | Н | Создаём из реального репо: копируем 6 упражнений + LICENSE из официального репо, фиксируем их hash |
| Идемпотентность не сработает на «real» при изменении | Н | Н | Юнит-тест update-detection + в … шаг 11 канария проверка |

### Шаг 10 — Документация (prompt1 §34, платформенный §X2)

**Артефакты:**
- `docs/curriculum_v0.1.md`: competency map (полная таблица), mapping principles, difficulty principles, provenance rules, ingestion workflow, known limitations.
- `docs/exercism_ingestion.md`: как получить source (Git-клина), как запустить dry-run/ingest, как посмотреть отчёты, как добавить override, как проголосовать одобрение источника.
- Короткий блок «Как перейти к следующей фазе» (только список зависимостей).

**CP-10:** docs соответствуют фактическому поведению CLI (проверка по шагам ком); README проекта включает эти ссылки.

### Шаг 11 — Финальный gate (prompt1 §36–§39, §40)

**Задачи:**
1. Прогнать DoD все чекбоксы §36 (map, provenance, exercism, mapping, database, reports, tests).
2. Прогнать acceptance §37: `pytest` → ALL TESTS PASS; `python -m app ingest exercism --dry-run` → понятный отчёт; `ingest` → SQLite; повторный запуск без дублей; получение отчётов (coverage, gaps, low-confidence, license).
3. **Canary на реальном клоне:** ingest небольшой выборки из настоящего репо; проверить идемпотентность N→N, отсутствие «мусора» в данных.
4. `git status` + `git diff --stat` (не трогать чужие файлы; рабочее — в STEPS).
5. Отчёт A–I (§39) в STEPS/CHANGELOG: что реализовано; Competency Map (кол-во + дерево); Exercism corpus (discovered/parsed/approved/pending/rejected); coverage; gaps; license; tests; known limitations; следующая фаза (зависимости D).
6. Обновить MANIFEST/ROADMAP/CHECKLIST/RUNNABLE; записать уроки в LESSONS.md.

**CP-11 (G-BC):** все пункты выполнены; статус `PHASE B+C COMPLETE · WAITING FOR REVIEW`; последний запуск `pytest` зелёный; **решение о переходе к Phase D — за пользователем (review).**

**Риски:**
| Риск | P | I | Митигация |
|---|---|---|---|
| «Зелёные тесты, а на реальном репозитории нет» | Н | В | Must-have: canary ingest на real (хотя бы 10–20 упражнений) до закрытия |
| Обнаружение недостающей части (например, нужен pytests для корпуса) | Н | С | Фиксируем в отчёт «зависимости для следующей фазы», не реализуем (правило gated) |
| Унесённый scope: «заодно реализую grading» | С | В | Запрещённый список §35 в шаге 0; самостоятельный чат: всё «запрещённое» декларируется зависимостью |

---

## 2. Сводный риск-реестр (по шагам)

| Шаг | Риск | P (Н/С/В) | Влияние (Н/С/В) | Митигация |
|---|---|---|---|---|
| 0 | Git-клон корпуса тяжёл для телефона | Н | С | shallow clone; subset metadata-first; решение до S6 |
| 2 | «Лицензия репо = лицензия всех файлов» | С | В | Пофайловый audit; evidence; external-attribution → pending |
| 2 | Сторонние материалы в отдельных упражнениях | Н | С | Research-таблица помечает, не импортируем пока они pending |
| 3 | Некорректная мапа (дубли, циклы, пробелы) | С | С | Validator + cycle-тест + сверка с Exercism concepts |
| 4 | Испавление «полезных» таблиц будущего | Н | С | Список разрешённых таблиц; ревью diff |
| 5 | Контент в corpus без license | С | В | live-gate (approved only) + тест unapproved→not live; evidence обязателен |
| 6 | Структура upstream менялась | Н | С | Фикстуры-мини-трек из реальной копии; content_hash |
| 6 | Неконтролируемая память/объём | Н | С | Batch walk; не держать контент в ОЗУ |
| 7 | Механический mapping на «имя папки» | С | Н | multi-source mapping, low-confidence report, overrides |
| 8 | Отчёты не отвечают на вопросы | Н | Н | CP-6 (golden-output), пример «как читать» в docs |
| 9 | Тесты зависят от сети | В | Н | Hermetic fixtures; integration-марка |
| 11 | «Зелень тестов» при сломанном real-импорти | Н | В | Canary ingest real sample (10–20) в gating |
| 11 | Scope creep в соседние фазы | С | В | Список запрета §35, отчёт «зависимости», review-точка |

---

## 3. Контрольные точки (свод)

| CP | Шаг | Проверяемое | Команда/критерий |
|---|---|---|---|
| CP-0 | 0 | структура + smoke | `pytest tests/ -q` без ошибок импорта |
| CP-1 | 1 | inspection-решение | STEPS: Python 3.14, структура, зависимости |
| CP-2 | 2 | research + лицензии | `docs/exercism_research.md` с per-part статусами и evidence |
| CP-3 | 3 | competency map | validator exit 0; cycle-test fail при добавленном цикле; концепты покрытие |
| CP-4 | 4 | schema | тесты FK/UNIQUE/CHECK/PRAGMA — green |
| CP-5 | 5 | license gate | approved → live; pending/rejected → перечисление, никогда unknown→live |
| CP-6 | 6 | pipeline | dry-run: discovered/parsed/approved/…; повтор идемпотентен |
| CP-7 | 7 | mapping | confidence; overrides применяются; low-confidence report честен |
| CP-8 | 8 | CLI+reports | все флаги работают; coverage/gaps/license отчёт |
| CP-9 | 9 | tests+fixtures | `pytest tests/ -q` ALL PASS (offline); idempotency N→N, change→update |
| CP-10 | 10 | docs | оба документа соответствуют фактич. CLI |
| CP-11 | 11 | final gate | DoD §36, acceptance §37, canary real, отчёт A–I, `PHASE B+C COMPLETE · WAITING FOR REVIEW` |

---

## 4. Запрещено в этой фазе (prompt1 §35 — проверка перед каждым коммитом)

❌ Docker / nsjail / subprocess student execution / pytest grader / Pylint/Radon/Bandit execution / AST detector / FSRS / evidence engine / learning state engine / activity selector / FastAPI / frontend / LLM / freeCodeCamp-import / Google-import / MIT-import.

Если нужен компонент из списка — **только** фиксируем dependency в отчёте (п. A.H), не реализуем.

---

## 5. Timeline (ориентир)

| Шаг | Часы (оценка) |
|---|---|
| 0 Pre-flight | 0.5 |
| 1 Inspection | 0.5 |
| 2 Research+license audit | 2–3 |
| 3 Competency map | 1–2 |
| 4 Schema | 1–1.5 |
| 5 License gate | 1–2 |
| 6 Ingestion pipeline | 3–5 |
| 7 Mapping | 2–3 |
| 8 CLI/reports | 1–1.5 |
| 9 Tests/fixtures | 2–3 |
| 10 Docs | 1 |
| 11 Gate | 1–1.5 |
| **Итого** | **≈16–24 h** (~6–10 сессий, соответствует ROADMAP §6) |

---

## 6. Cross-links

- [`prompt1.md`***REMOVED***(prompt1.md) — bind DoD/acceptance (источник)
- [`python_ai_tutor_blueprint_v0.1.md`***REMOVED***(python_ai_tutor_blueprint_v0.1.md) — контракты
- [`ROADMAP.md`***REMOVED***(ROADMAP.md) — гейты/статус фаз
- [`STEPS.md`***REMOVED***(STEPS.md) — журнал: каждые CP и решения фиксируются по-фазово
- [`CHECKLIST.md`***REMOVED***(CHECKLIST.md) — acceptance Phase B+C