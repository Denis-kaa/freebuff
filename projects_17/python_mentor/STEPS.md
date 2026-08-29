# STEPS.md — Журнал шагов и «почему» (python_mentor)

> Правило платформы (AGENTS.md §6.5, PROJECT_RULES §3): каждый значимый шаг фиксируем с **почему принято такое решение** и альтернативами. Уроки — в [LESSONS.md***REMOVED***(LESSONS.md), архитектурные решения — в [decisions/***REMOVED***(decisions/).

## Шаг 1 (2026-08-23) — Разбор источника и каркас проекта

**Что сделано:**

1. Прочитаны все 7 документов `projects_17/python_mentor/`:
   - `python_ai_tutor_methodology.md` — педагогика: 5 ролей, S0–S6 (с наблюдаемыми тестами), L0–L6, 5 документов контекста, curriculum по компетенциям.
   - `python_ai_tutor_blueprint_v0.1.md` — контракты для реализации (competency/exercise/evidence/grading/error-pattern/hint/state-machine/FSRS/sandbox/SQLite/provenance/API).
   - `prompt.md` — исходное research-ТЗ (Этап 0–3): сбор лицензионно-чистых банков, research инструментов, архитектура, отчёт.
   - `prompt1.md` — ТЗ первой исполняемой фазы **B+C** (Competency Map + Exercism Ingestion) с DoD §36–37 и запретами §35.
   - `prompt2.md` — ТЗ фаз **D–N** (Grader, Sandbox, AST, Hints, Evidence, FSRS, Selector, Projects, API, UI, E2E) как серия промтов-гейтов.
   - `prompt3.md` — консолидированный master prompt v1.0: инвариант детерминизма, роли → детерминированные реализации, запреты подмены mastery метриками.
   - `python_ai_tutor_prompts.md` — системные промты 5 ролей (это будущий **LLM-слой**, Phase O).

**Почему так:** первый шаг — понять, что уже решено и что осталось исполнить. Blueprint фиксирует контракты, `prompt1` — первая фаза исполнения, `prompt2` — остальные, `prompt3` — свод правил. Методика — источник педагогики; промты ролей относятся к LLM-слою и НЕ блокируют детерминированное ядро.

**Альтернативы, которые рассматривали:**
- (а) сразу начать писать код Phase B+C — отклонено: платформа требует каркаса-контейнера (§1 «нет проекта → сначала каркас»), кроме того пользователь просил роадмап, а не код;
- (б) объединить fewdocs в один большой промт — отклонено: фазовые гейты (prompt2) специально сделаны по одной фазе за раз — перескок невалидируется.
- (в) «массивный» роадмап без каркаса — нет: по правилам проекта контейнер обязателен.

## Шаг 2 (2026-08-23) — Каркас проекта (эта сессия)

**Что сделано:** создан обязательный каркас по PROJECT_RULES §2: MANIFEST.md (паспорт/инварианты), README.md, SPEC.md, ROADMAP.md (роадмап-главный), STEPS.md, LESSONS.md (журнал), RUNNABLE.md + CHECKLIST.md, decisions/DECISIONS + ADR-001…004, project.yaml. Зарегистрирован в `docs_10/projects_meta/PROJECTS_OVERVIEW.md`.

**Почему так:**
- Роадмап построен по той же логике, что и исходные документы: контент → проверка → исполнение → диагностика → память → планирование → проекты → API → UI → валидация. Плюс встроены платформенные гейты (тесты+mypy, docs sync, регистрация).
- Инварианты взяты прямо из blueprint/prompt3 — не пересказом, а списком «нельзя нарушать».

**Альтернативы:**
- Подключать Forge-планирование (Blueprint v3 role pipeline) для планирования — опция, отмечена в ROADMAP §10 item 7; для данного этапа достаточно каркаса, heavy-роли не нужны до фазы B+C.
- Сделать LLM-слой в scope — нет: он опционален и после P8 (промт3 §0).

## Шаг 3 (2026-08-23) — Проверка окружения Termux (по запросу пользователя)

**Что сделано (read-only):**

- Python **3.14.6** ✅, pytest **9.1.1** ✅, SQLite **3.53.4** ✅, pip **26.2.1** + доступ к PyPI ✅.
- RLIMIT: понижение работает (CPU→(2,5), AS→256MB/1GB) ✅ — Phase E может опираться на `resource.setrlimit`; NPROC ограничен (14617).
- `unshare --user`/`--net`: **НЕ подтверждено** — окружение proot (ядро подменяется: `6.17.0-PRoot-Distro`, proot-distro контейнер Ubuntu поверх Termux). Команды возвращают 0, но сеть внутри `unshare --net` НЕ изолировалась (коннект успешен), `/sys/class/net` недоступен.
- Анализаторы: pylint/radon/flake8/bandit/ruff **не установлены**; `flake8` — битый (shebang на python3.13, которого нет). Решение для Phase F: `pip install pylint radon bandit flake8` (сеть есть) или AST-only fallback.
- FSRS: единственный PyPI-кандидат — **`fsrs 6.3.2`** (`fsrs4python`/`sm2`/`fsrs-scheduler` отсутствуют); не установлена.

**Почему так:** среда — не «голый Termux», а Termux + proot-distro Ubuntu; выводы `unshare` обманчивы (артефакт proot), поэтому в плане sandbox изоляция не обещается (честно, как требует blueprint §0), а RLIMIT/временные каталоги — подтверждены. Доступ к PyPI разрешает статику (F) и fsrs (I) устанавливать по мере нужды.

**Что обновлено:** ROADMAP §4 (capability-check), RUNNABLE.md (таблица окружения), этот журнал. Альтернатива — не фиксировать факты и перепроверять каждый раз — отклонена: план должен опираться на зафиксированные факты среды.

## Шаг 5 (2026-08-23) — FSRS подготовка: установка `fsrs 6.3.2` + API-проверка + rating mapping

**Что сделано:**
- Установлен `fsrs==6.3.2` (единственный кандидат PyPI; `fsrs4python`/`sm2` отсутствуют) — `pip install`, успешно, импорт работает на Python 3.14.
- Изучен API: `Card`, `ReviewLog` (**review_duration обязателен**, может быть None), `Scheduler(review_card/reschedule_card/get_card_retrievability)`, сериализация `to_dict/from_dict`.
- **Критичные нюансы:** naive datetime → TypeError (нужен **aware UTC**); `enable_fuzzing=True` по умолчанию → для детерминизма обязателен `enable_fuzzing=False`.
- Живой тест: цепочка Again→Hard→Good→Easy дала корректные переходы Learning→Review, stability/difficulty меняются; `Card.from_dict` roundtrip OK.
- **Rating mapping таблица** (закрывает ROADMAP §7.2): exercise_result без hints→Easy; 1 hint≤L1→Good; ≥2 hints или max≥L2→Hard; fail→Again; review_score≥0.8→Easy / 0.5–0.8→Good / <0.5→Hard; hint_used/error_detected сами по себе НЕ создают review.

**Почему так:** устанавливаем и проверяем на Phase I-prep, чтобы интеграция в Phase I шла по фактическому API (не по памяти), и чтобы зафиксировать mapping до кода (blueprint §8: «зафиксировать таблицей до реализации»). Детерминизм: `enable_fuzzing=False`.

**Что обновлено:** `FSRS_NOTE.md` (API+таблица), ROADMAP §4/§7 (пункт 2 закрыт), RUNNABLE §«Окружение» (fsrs ✅), CHECKLIST (prep-item), MANIFEST (индекс).

## Шаг 6 (2026-08-23) — Статические анализаторы для Phase F: установка и проверка

**Что сделано:** `pip install pylint radon bandit flake8` — установлены **pylint 4.0.7, radon 6.0.1, flake8 7.3.0, bandit 1.9.4** (до этого отсутствовали; битый `flake8` переустановлен). Smoke-тест на файле `def f(x=[***REMOVED***): return x` — flake8 и bandit работают. ruff не ставили: его уникальная ценность для Phase F не подтверждена (prompt2 §7: подключать только если даёт уникальную ценность).

**Почему так:** Phase F строится на адаптерах-сенсорах (prompt2 §5–§8); вместо fallback'а на AST-only теперь есть реальные тулзы. Фиксируем версии для воспроизводимости (среда меняется — версии зафиксируем в requirements на Phase F).

**Что обновлено:** ROADMAP §4 (строка анализаторов), RUNNABLE (окружение), этот журнал.

## Шаг 7 (2026-08-23) — Phase B+C · Шаг 2: Exercism research + пофайловый license audit (CP-2 ✅)

**Что сделано:**
- **S0-5 ЗАКРЫТО:** shallow clone `https://github.com/exercism/python` → `data/exercism_src/` (gitignore). Факт: commit `1f6aab8667bf653b10cc3799f94352fcdb749db6` (2026-08-09), **14 MiB** без .git (оценка S0-5 была 30–60 МБ), 2 211 файлов. Дальше ingestion работает оффлайн по `--source` (prompt1 §30).
- **Структура зафиксирована:** concept 21 / practice 140 / foregone 3 (не импортируются) / concepts 67 (справочники) / shared / reference / docs / bin / .github; упражнение = `.docs/` + `.meta/` + stub `.py` + `*_test.py`; `.meta/config.json` содержит `authors/contributors/files/blurb/source_url`.
- **License audit (пофайлово):** единственный LICENSE — корневой **MIT «Copyright (c) 2021 Exercism»** (21 строка); README содержит раздел «Exercism Python Track License: This repository uses the MIT License» (строки 97–99). По классам файлов (statement/tests/stubs/metadata/reference solutions/concepts/ref-docs/config/CI) — всё **approved** (10 классов, evidence = репо-лицензия + коммит).
- **Сторонние материалы:** Project Euler / RosettaCode / Codewars / HackerRank / LeetCode / AoC — **не найдены** в текстах; `source_url` practice указывает на `exercism/problem-specifications` (canonical-источник, тоже Exercism). Внешние ссылки (bicyclecards.com и т.п.) — ссылки, не контент.
- **Решение S0-6/S0-7 зафиксировано:** content локально для approved (все части — approved → локально); reference solutions approved, но импорт — только с `--with-refs`.
- **Артефакт:** `docs/exercism_research.md` (структура + evidence-блок + статусы) — CP-2 ✅.
- Добавлен `projects_17/python_mentor/.gitignore` (data/exercism_src/, data/corpus/, __pycache__) — источник и корпус не попадают в git (конвенция платформы, как data_13/).

**Почему так:** единственный источник контента должен прийти с доказанной лицензией (legal-first, prompt1 §11); никакого «всё MIT ⇒ всё можно» — аудит по классам файлов с evidence. Хранение клона локально и оффлайн-режим — обязательное условие hermetic pipeline.

**Альтернативы:**
- (а) клонировать с историей — отклонено: 14 MiB достаточно, история не нужна (фиксация коммита и так есть);
- (б) загружать subset + metadata — не понадобилось: размер 14 MiB заметно ниже оценки, полный клон включён;
- (в) считать лицензию «по корневому LICENSE без аудита» — запрещено платформой (prompt1 §11 требует по-частей; audit сделан).

---

## Шаг 8 (2026-08-23) — Phase B+C · Шаг 2 (второй проход): сквозной per-file аудит

**Что сделано (верификация и углубление CP-2):**
- **License-хедеры:** 516 `.py`-файлов, **0** с copyright/license-хедером → единый MIT репо покрывает все файлы, отдельных лицензий внутри нет.
- **origin-ссылки (per-file):** все 161 `.meta/config.json` → распределение хостов `source_url`: wikipedia 30, github (problem-specifications) 18, web.archive 11, **projecteuler.net 7**, turing.edu 5, wolfram 7, pine.fm 4, calpoly 3, twitter 2, forum.exercism 2, остальные по 1. ⚠️ уточнение к первому проходу: «все source_url → problem-specifications» — неверно;
- **Project Euler-производные (7):** difference-of-squares, largest-series-product, nth-prime, palindrome-products, pythagorean-triplet, series, sum-of-multiples. Тексты instructions **проверены** (3 выборочно): перефраз, не verbatim → статус `approved` + `attribution_required=true` + `source_url` в corpus.
- **grep по всем типам файлов** (не только md): 13 файлов с упоминаниями сторонних платформ — все ссылки/attribution (links.json, config.json source_url, LEARNING.md, approach-статья), контентного заимствования нет.
- Документ обновлён: §3.3 уточнён (source_url-модель), добавлен **§3.4** (таблица хостов + PE-вердикт), §4.2 (attribution в evidence).

**Почему так:** первый проход нашёл «только MIT и нет стороннего»; второй проход — перепроверка на глубину per-file, и обнаружил нюанс attribution (7 упражнений из Project Euler) — важно для provenance (Шаг 5): поле `source_url` теперь явно в evidence. Это укрепляет аудит перед license gate.

> 🔁 **Re-verified (2026-08-23, повторный прогон):** clone @ `1f6aab8667bf`, 17 MiB; LICENSE-файлов в дереве — 1 (MIT); .meta/config.json — 161; practice 140 / concept 21; `docs/exercism_research.md` — 150 строк, evidence-блок на месте. CP-2 стабильна, изменений не требуется.
> 🔄 **Live up-to-date check (2026-08-23, сеть):** `git ls-remote https://github.com/exercism/python HEAD` = `1f6aab8667bf…` — HEAD upstream **идентичен** нашему клону. Источник актуален на момент проверки; повторный аудит не требуется (commit-pin актуален).

**Альтернативы:**
- (а) не перепроверять — отклонено: источник корпуса — единый, перепроверка дешева, меняет поле provenance-схемы;
- (б) ставить PE-производные в `pending` — отклонено: тексты парафраз, лицензия MIT покрывает; attribution достаточна (как в upstream docs); если найдётся verbatim — реестр помечает `pending` (механизм в S5).

---

## Шаг 9 (2026-08-23) — Phase B+C: Шаги 0–1 (Pre-flight структуры + Inspection) — CP-0 ✅, CP-1 ✅

**Шаг 0 — Pre-flight и структура (CP-0 ✅):**
- Создан каркас кода (по prompt1 §33, конвенция public_request_parser, S0-2):
  ```
  app/__init__.py (+ version 0.1.0, docstring-инварианты)
  app/curriculum/     # Competency Map (Шаг 3)
  app/ingestion/      # pipe (Шаги 4–8): discovery/parser/license/mapping/pipeline/cli
  configs/competency_map.yaml      # скелет (заполняется в Шаге 3)
  configs/exercise_overrides.yaml  # скелет (Шаг 7)
  data/corpus/                     # выходной SQLite (gitignored)
  tests/unit/, tests/integration/, tests/fixtures/exercism/  # fixtures — Шаг 9
  tests/unit/test_smoke.py         # импорт app
  requirements.txt                 # PyYAML==6.0.3 (S0-3)
  ```
- Env-факты (Python 3.14.6, pytest 9.1.1, PyYAML 6.0.3) уже в RUNNABLE (Шаг 3); S0-5 закрыт в Шаге 2.
- **К0:** `python3 -m pytest tests/ -q` → **1 passed** (1.30s) — сюит собирается без ошибок импорта.

**Шаг 1 — Inspection (prompt1 §4–5, CP-1 ✅):**
- Существующая инфраструктура до этого шага: **только документация** (MANIFEST/README/…, prompt*.md + prompt.md.bak, decisions/, docs/exercism_research.md).
- pyproject.toml — нет; requirements.txt — создан нами; migrations/database/models/config — отсутствуют; tests/docs — созданы нами.
- curriculum/competency/exercises/learning-артефактов в коде до Шага 0 — нет (единственные совпадения в .py — docstring'и только что созданного app/); SQLite-файлов — 0.
- Python-версия: 3.14.6 (проект версию не фиксировал; blueprint target 3.11+ → удовлетворён); решение S0-3 зафиксировано (requirements + CLI target Python 3.14).
- git status платформы: `projects_17/python_mentor/` целиком untracked — нормально (новый проект); `prompt.md.bak` — пользовательский файл, НЕ тронут (правило: документы-источники не удаляем).

**Почему так:** prompt1 §4 требует «не дублировать существующую инфраструктуру, если repo пуст — создать минимальную»; repo содержал только документы → создан минимальный код-каркас по конвенции платформы (app/ пакеты как public_request_parser); Python-версию фиксируем явно (3.14.6) как принят runtime.

**Альтернативы:**
- (а) src-layout (src/python_mentor/) — отклонено: нет сборки/установки, прямой импорт проще в Termux;
- (б) один плоский app/main.py — отклонено: разделение curriculum/ingestion по контрактам blueprint (низкая связанность);
- (в) создать pyproject.toml — не требуется до packaging; requirements.txt достаточно для B+C.

**Артефакты:** структура выше; `3 файла .py + tests/unit/test_smoke.py`; STEPS-запись (эта).

---

## Шаг 10 (2026-08-23) — Phase B+C: Шаги 3–11 выполнены → G-BC ✅ · PHASE B+C COMPLETE · WAITING FOR REVIEW

### Отчёт A–I (prompt1 §39)

**A. Что реализовано (компоненты Phase B+C):**
- `app/curriculum/map.py` — Competency Map: загрузка YAML, валидатор (уникальность, категории, prereq-ссылки, **ацикличность DFS**), coverage-report;
- `configs/competency_map.yaml` (+ генератор `tools/gen_competency_map.py`) — строгая схема (25 компетенций, 11 групп, 34 prereq-связи);
- `app/storage.py` — SQLite v0.1: 5 таблиц, FK/UNIQUE/CHECK, PRAGMA foreign_keys=ON, user_version=1;
- `configs/sources.yaml` + `app/ingestion/license.py` — реестр источников, **license gate** (approved→live; approved требует evidence);
- `app/ingestion/parser.py` — discovery+parse (структура клона exercism/python, content_hash sha256);
- `app/ingestion/pipeline.py` — идемпотентный ингест (INSERT/UPDATE по content_hash; dry-run; `--with-refs`), sync компетенций;
- `app/ingestion/mapping.py` — маппинг: override > rule(concepts) > blurb-эвристика(low) > unmapped-честно; confidence high/medium/low;
- `app/__main__.py` + `app/ingestion/reports.py` — CLI `python -m app ingest/report` + coverage/gaps/low-confidence/license отчёты;
- Fixtures (мини-трек, hermetic) + 37 unit + 2 integration-теста; **mypy: Success (0 errors)**;
- Документы: `PHASE_BC_PLAN.md` обновлён, `docs/curriculum_v0.1.md`, `docs/exercism_ingestion.md`.

**B. Competency Map:** 25 компетенций · 11 групп · 34 связи prereq · validator exit 0 · cycle-test ✅ · **покрытие Exercism: 45/67 concepts (+22 явный unmapped — 0 «дыр»)**.

**C. Exercism corpus:** discovered/parsed **161** (concept 21 + practice 140; foregone 3 исключены · 0 pending · 0 rejected · **лицензия approved**); content hash per упражнения; reference solutions — gated (`--with-refs`).

**D. Mapping:** 161/161 замаплено (после override) · source: rule 153 / override 8 · confidence: high 112 / medium 38 / low 11 · unmapped после overrides — 0. Low-confidence отчёт — для ручных решений (11 low + 38 medium).

**E. Coverage:** по компетенциям — таблица из `python -m app report coverage` (26 строк); сильные: lists 67, boolean-logic 20, classes 15, dicts 11, strings/primitive-types 10; слабые — см. gaps.

**F. Content gaps:** 13 компетенций с 0–1 упражнением (code-structure, comprehensions, files-io, iterators-generators, modules, scope-decomposition, testing, tuples, unpacking — 0; exceptions, expressions, sets — 1; variables — 1 rung). **Gap-отчёт честен, «ремонта» нет** (правило §26).

**G. License:** единственный источник `exercism-python` (MIT ©2021 Exercism), evidence — `docs/exercism_research.md` §3 + `configs/sources.yaml`; attribution через `source_url` сохраняется.

**H. Tests:** `pytest tests/ -q` → **37 passed** (unit, hermetic, offline); `-m integration` → **2 passed** (canary на реальном клоне); `mypy app/ --ignore-missing-imports` → **0 errors**; CLI acceptance: fresh ingest → inserted 161, повтор → unchanged 161 (0 новых).

**I. Known limitations / деп-и для следующей фазы:** 22 Exercism concepts вне карты v0.1 (recursion, regex, decorators, bitwise и др. — новые компетенции Phase D+); mapping по практикам трека (неполные метаданные concept-exercises → medium/low); слабые компетенции — кандидаты на второй источник (freeCodeCamp/Google/MIT — **только после gap-анализа и license gate**, prompt1 §35); `pedagogical_rung` — маппинг от difficulty (выверять на Phase D с реальным учеником); reference solutions требуют `--with-refs`.

**Gates:** CP-0…CP-11 ✅. Статус фазы: **PHASE B+C COMPLETE · WAITING FOR REVIEW** (решение о Phase D — за пользователем).

---

## Phase D (NEXT) — Grading Contract + Autograder (prompt2)

Этап завершён (`PHASE B+C COMPLETE`). Дальше — **Phase D** по `prompt2.md`: стабильный grading contract, pytest-runner (РАЗДЕЛЬНО от sandbox Phase E), нормализованный результат (PASS/FAIL/ERROR/TIMEOUT/INFRASTRUCTURE_ERROR). Входные данные: corpus из `data/corpus/corpus_v0.1.db` (161 упражнение, tests_ref для каждого).

Архивный текст плана B+C (как он был): последовательность CP-0…CP-11, стартовые решения S0-1…S0-7, DoD §36–§39. Всё выполнено (сверка по Шагу 10 выше).*Журнал продолжается по мере выполнения фаз (шаги фаз D…N фиксируются по тому же формату).*

---

## Шаг 11 (2026-08-23) — Phase D: Grading Contract + Autograder → G-D ✅

**Что реализовано:**

- `app/grading/contract.py` — immutable (`frozen=True`) контракт: `SubmissionIdentity`, `Correctness`, `GradingResult`, `EvidenceCandidate`; публичные статусы `PASS`, `FAIL`, `ERROR`, `TIMEOUT`, `INFRASTRUCTURE_ERROR` и отдельный `failure_kind` (`student_failure`/`grader_failure`).
- `app/grading/runner.py` — `PytestGrader`: student code запускается только в child process, отдельном temporary workspace и process group; есть sanitized environment, wall-clock timeout, bounded output, cleanup и JUnit XML normalization.
- `app/grading/catalog.py` — approved-corpus boundary: exercise разрешается к запуску только при `exercise_sources.status == approved`; registry paths проверяются на containment внутри source root.
- `evidence_candidates` возвращаются только как результат grading; Phase D не пишет evidence, competency state, quality score или learning state.
- Preflight различает syntax/import student errors и malformed exercise tests, чтобы collection error не маскировался под grader timeout.

**Почему так:** Phase D отвечает на вопрос «прошли ли тесты», а Phase E будет отвечать на вопрос «насколько безопасно исполнять код». Разделение не расширяет B+C schema и не смешивает correctness с mastery/static metrics.

**Альтернативы:**

- Запускать submission внутри основного Python процесса — отклонено: нарушает execution boundary и оставляет импорт student code в приложении.
- Определять результат только по pytest exit code — отклонено: `returncode=1` одинаково покрывает assertion failure и collection/import failure; нужны JUnit counts + failure kind.
- Реализовывать Docker/nsjail/network isolation в Phase D — отклонено: это scope Phase E и недоступно/не подтверждено в текущем Termux+proot.

**Evidence / acceptance:**

- Phase D tests: **13 passed** (включая corpus catalog → grader, approved gate, pass, partial/multiple fail, syntax/import error, timeout, output limit, malformed/missing tests, duplicate, stable identity, immutability).
- Full project suite at the Phase D checkpoint: **50 passed, 2 skipped** (integration marker по умолчанию); after Phase E the suite is **58 passed, 2 skipped**.
- `python3 -m mypy app/ --ignore-missing-imports`: **Success**, 15 source files.
- `python3 -m compileall -q app tests/unit/test_grading.py`: **OK**.
- Последовательный запуск выбран намеренно: параллельный старт нескольких pytest child processes в proot иногда превышает короткий timeout из-за конкуренции CPU; это не используется как acceptance-режим.

**Статус на checkpoint 2026-08-23:** `PHASE D COMPLETE · WAITING FOR REVIEW` (G-D ✅). Следующий гейт тогда был Phase E; superseded by Шаг 12 below.

---

## Шаг 12 (2026-08-24) — Phase E: Execution Runtime + Sandbox MVP → G-E ✅

**Что реализовано:**

- `app/execution/contract.py` — frozen-контракты `ExecutionJob`, `ExecutionPolicy`, `ExecutionResult`, `ExecutionStatus` и явный `SandboxTier.MVP_UNTRUSTED_SINGLE_USER`; `HARDENED` намеренно отклоняется до будущего backend.
- `app/execution/backend.py` — replaceable `ExecutionBackend` и `TermuxSubprocessBackend`: child process group, sanitized environment, temporary workspace boundary, wall-clock timeout, bounded combined stdout/stderr, `RLIMIT_CPU`, опциональный `RLIMIT_AS`, SIGTERM→SIGKILL cleanup.
- `app/grading/runner.py` — Phase D подключён к Phase E backend без изменения grading contract. Grader использует абсолютный `sys.executable`, CPU/wall-clock/output limits и не включает `RLIMIT_AS` вокруг pytest bootstrap: в текущем proot даже generous cap даёт ложный timeout. Прямые execution jobs могут включать `RLIMIT_AS` через `ExecutionPolicy`.
- `docs/execution_v0.1.md` — контракт, capability facts и security limitations; production/network/filesystem/multi-user isolation не заявляются.
- `tests/unit/test_execution.py` — **8 hermetic tests**: completion, process-group timeout, output cap, sanitized environment, workspace, direct-job address-space policy, MVP tier.

**Почему так:** Phase E отделяет способ запуска кода от вопроса корректности. Backend можно заменить hardened implementation без изменения grader; MVP честно ограничен локальным single-user Termux/proot и не притворяется public sandbox.

**Альтернативы:**

- Docker/nsjail/unshare как обязательный runtime — отклонено: в текущем Termux/proot user/network namespaces не подтверждены, а `unshare --net` не изолирует сеть.
- Включить `RLIMIT_AS` во все pytest runs — отклонено после воспроизводимого ложного timeout даже на 1 GiB; policy сохранена для прямых jobs и проверяется отдельным тестом.
- Передавать команду как `python3` — отклонено: sanitized PATH в окружении не обязан содержать runtime interpreter; backend/grader используют абсолютный `sys.executable`.

**Evidence / acceptance:**

- `python3 -m pytest tests/unit/test_execution.py -q` → **7 passed**.
- `python3 -m pytest tests/unit/test_grading.py -q` → **13 passed**.
- `python3 -m pytest tests/ -q` → **58 passed, 2 skipped** (integration marker по умолчанию).
- `python3 -m mypy app/ --ignore-missing-imports` → **Success**, 18 source files.
- `python3 -m compileall -q app tests` → **OK**.
- `git diff --check -- projects_17/python_mentor` → **OK**.

**Статус:** `PHASE E COMPLETE · WAITING FOR REVIEW` (G-E ✅). Следующий гейт — Phase F (AST/Static Diagnostics).

---

## Шаг 13 (2026-08-24) — ADR-005: RLIMIT_AS в Termux/proot и граница hardened sandbox

**Что сделано:** создан [`ADR-005`***REMOVED***(decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md) и добавлен в реестр решений, `SPEC`, `MANIFEST`, `ROADMAP` и `README`.

**Почему так:** `RLIMIT_AS` доступен как backend policy, но в текущем Termux/proot применение вокруг pytest bootstrap воспроизводимо вызывает ложный timeout даже при 1 GiB. Поэтому grader сохраняет CPU/wall-clock/output limits, direct execution jobs могут явно включить address-space policy, а весь Phase E остаётся `mvp_untrusted_single_user`.

**Граница решения:** наличие `setrlimit()` или успешного `unshare` не доказывает hardened isolation. Переход к hardened tier требует отдельного OS-backed backend с тем же execution contract и положительной проверкой заявленных network/filesystem/process boundaries перед public или multi-user запуском.

**Проверка:** `git diff --check -- projects_17/python_mentor` → OK; код не изменялся.

---

## Шаг 14 (2026-08-24) — Phase F: AST diagnostics + analyzer adapters → G-F ✅

**Что реализовано:**

- `app/diagnostics/contract.py` — immutable `Diagnostic` и `SensorReport`; фиксированные severity/status; `diagnostic_only=True` enforced контрактом.
- `app/diagnostics/ast_rules.py` + `engine.py` — ordered `ASTRuleRegistry`, `RuleContext`, `PatternMatch`, syntax-error normalization и 7 детерминированных правил: mutable default, bare except, excessive nesting, mutable module state, builtin shadowing, unreachable code, oversized function.
- `app/diagnostics/adapters.py` — Pylint JSON, Radon CC/raw/Halstead/MI, Flake8 line output и Bandit JSON; unavailable/failed/invalid output разделены; Bandit запускается только при `security_eligible=True`.
- `app/diagnostics/patterns.py` — reference-only mapping detector → error pattern → hint key; evidence/learning state API отсутствует.
- `docs/diagnostics_v0.1.md` — контракт, ограничения и acceptance evidence.

**Почему так:** анализаторы являются sensors, а не оценкой ученика. Static metrics, maintainability index, количество/тяжесть diagnostics не создают evidence и не меняют competency state; следующий Hint Engine получит только нормализованные reference patterns.

**Evidence / acceptance:**

- `python3 -m pytest tests/unit/test_diagnostics.py -q` → **14 passed**.
- `python3 -m pytest tests/ -q` → **72 passed, 2 skipped**.
- `python3 -m mypy app/ --ignore-missing-imports` → **Success**, 24 source files.
- `python3 -m compileall -q app tests` → **OK**.
- Live adapter smoke: Pylint 4.0.7, Radon 6.0.1, Flake8 7.3.0, Bandit 1.9.4 → all `ok` with 60s adapter timeout.
- `git diff --check -- projects_17/python_mentor` → **OK**.

**Статус:** `PHASE F COMPLETE · WAITING FOR REVIEW` (G-F ✅). Следующий гейт — Phase G (Hint Engine).

---

## Шаг 15 (2026-08-24) — Localization foundation + LLM update boundary

**Что выяснено:** английский Exercism track остаётся learner-facing source. Deterministic extractor нашёл **432 Markdown-документа** и **1,022,490 символов** по текущему pinned clone: `instructions.md`, `introduction.md`, `hints.md`, concept `about.md`. Код, тесты, reference solutions, metadata и license evidence не переводятся.

**Что реализовано:**

- `app/localization/contract.py` — `SourceDocument`, `TranslationDraft`, `LocalizationPolicy`, status `draft/reviewed/stale`.
- `app/localization/extractor.py` — deterministic extraction, SHA-256 source hashes, manifest.
- `app/localization/validator.py` — hash freshness + Markdown code-fence/inline-code/link/heading validation.
- `app/localization/workflow.py` — missing/stale/reviewed status и reviewed-only publication с provenance sidecars.
- `app/localization/provider.py` — внешний `TranslationProvider`; текущий `ExternalLLMTranslationProvider` fail-closed.
- `python -m app localize scan/status/update` — операционный интерфейс.
- `ADR-006`, `prompt_localization.md`, `docs/localization_v0.1.md` — канон локали и controlled LLM boundary.

**Почему так:** английский source нельзя заменять переводом: он нужен для provenance, license audit и change detection. LLM получает только задачу создания draft; live Russian projection появляется после hash/structure validation и review. Upstream change помечает перевод `stale`, а не перезаписывает его тихо.

**Evidence / acceptance:**

- `python3 -m pytest tests/unit/test_localization.py -q` → **6 passed**.
- `python3 -m app localize scan ...` → manifest `432` docs / `1,022,490` chars.
- `python3 -m app localize status ...` → `432 draft` (RU projection пока не создана).
- `python3 -m app localize update --provider external_llm` → fail-closed, понятный provider-not-configured error; внешние credentials не добавлялись.
- `python3 -m mypy app/ --ignore-missing-imports` → **Success**, 31 source files.

**Статус:** Localization foundation ready; full RU batch translation ждёт review. Внешний provider boundary расширен Gemini rotation в следующем шаге.

---

## Шаг 16 (2026-08-24) — Gemini provider + трёхключевая ротация (draft-only)

**Что реализовано:**

- `app/localization/keys.py` — `GeminiKeyPool`: thread-safe round-robin pool; принимает локальный файл с одной credential на строку или `NAME=value`; значения не входят в repr/логи.
- `app/localization/gemini.py` — `GeminiTranslationProvider`: Gemini `generateContent`, модель по умолчанию `gemini-2.5-flash`, retryable HTTP/API failures переключают ключ; результат всегда `TranslationDraft`.
- `app/localization/workflow.py` — отдельная запись `*.draft.md` + metadata JSON; draft не получает reviewed source-hash sidecar.
- `app/localization/cli.py` — `localize update --provider gemini`; по умолчанию обрабатывает один missing/stale документ, `--limit` позволяет явный batch.
- `.gitignore` — credential file и draft directory не попадают в репозиторий.

**Почему так:** три рабочих Gemini credentials используются как резервный внешний provider, но не получают права менять English source, live `ru`, curriculum, evidence или learning state. Default `--limit 1` защищает от случайного расхода и большого сетевого запуска; batch переводится только явно.

**Evidence / acceptance:**

- `python3 -m pytest tests/unit/test_gemini_rotation.py tests/unit/test_localization.py -q` → **19 passed**.
- `python3 -m mypy app/ --ignore-missing-imports` → **Success**, 33 source files.
- `python3 -m compileall -q app tests` → **OK**.
- Hermetic tests не используют реальные credentials и сеть; active key file проверен только по metadata/permissions, без вывода значений.

**Статус:** Gemini adapter подключён как optional additional brain; публикация остаётся review-gated.
