# Exercism Research & License Audit — Python Track

> **Фаза:** B+C · Шаг 2 (CP-2) · **Дата:** 2026-08-23
> **Источник:** [`PHASE_BC_PLAN.md`***REMOVED***(../PHASE_BC_PLAN.md) Шаг 2 (prompt1 §10–§11)
> **Статус:** ✅ выполнен — вывод: корпус **approved** (MIT), импортируем полностью с evidence; сторонних лицензий в контенте не обнаружено

---

## 1. Получение источника (решение S0-5 — ЗАКРЫТО)

| Параметр | Значение |
|---|---|
| Репозиторий | `https://github.com/exercism/python` (официальный Exercism Python Track) |
| Способ | `git clone --depth 1` (shallow, без истории) |
| Коммит (фиксация) | `1f6aab8667bf653b10cc3799f94352fcdb749db6` — 2026-08-09 «[Ellen's Alien Game***REMOVED*** Test that an instance variable is used for the health, not a class variable. (#4273)» |
| Размер | **14 MiB** без `.git` (17 MiB с ним) — заметно меньше оценки 30–60 МБ из S0-5 |
| Файлов | 2 211 |
| Локальный путь | `data/exercism_src/` (gitignored, воспроизводим командой выше) |

**Вывод:** shallow clone ✅ принят (S0-5). Полный оффлайн-источник для ingestion; сеть больше не нужна (prompt1 §30).

---

## 2. Структура репозитория (факт, зафиксирован на коммите выше)

| Часть | Путь | Файлов | Роль в импорте (Phase B+C) |
|---|---|---|---|
| Track config | `config.json` | 1 | Все упражнения: `exercises.{concept:21, practice:140, foregone:3***REMOVED***`; `concepts` (67); `files`, `test_runner`, `tags` |
| Concept-упражнения | `exercises/concept/*` (21 шт.) | 173 | Statement: `.docs/{instructions,introduction,hints***REMOVED***.md`; metadata: `.meta/config.json`, `.meta/design.md`; reference: `.meta/exemplar.py`; stub `*.py`; tests `*_test.py` |
| Practice-упражнения | `exercises/practice/*` (140 шт.) | 1 473 | `.docs/instructions.md`; `.meta/{config.json,example.py,template.j2,tests.toml***REMOVED***`; stub `*.py`; tests `*_test.py`; `.approaches/` (32 шт. — статьи подходов сообщества) |
| Общее | `exercises/shared/` | 4 | `pytest.ini` и т.п. — только для upstream-тестирования |
| Concepts (справочники) | `concepts/*` (68 шт.) | 268 | `about.md`, `introduction.md`, `links.json` — справочный материал (вне импорта v0.1, но маппятся на competency map) |
| Reference-доки | `reference/` | 231 | MD-конспекты концепций + `exercise-concepts/` (маппинг упражнение→концепты) — вспомогательный |
| Доки трека | `docs/` | 21 | ABOUT/LEARNING/TDD и т.п. — не импортируются |
| Инструменты | `bin/`, `.github/`, `config/` | 27 | CI/генераторы — не импортируются |
| Политика | `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`, `.flake8`, `.style.yapf`, `pylintrc`, `pytest.ini`, `requirements*.txt` | — | Evidence для аудита |

**Формат metadata упражнения** (`.meta/config.json`): `authors`, `contributors`, `files{solution,test,example***REMOVED***`, `blurb`, `source_url` (≈ все practice ссылаются на `exercism/problem-specifications` — «canonical source»). Поля `config.json` трека: `slug/name/uuid/practices/prerequisites/difficulty` (+ blurb для concepts).

---

## 3. License audit (пофайловый, по частям)

### 3.1 Репозиторный LICENSE (главный evidence)

- **Файл:** `data/exercism_src/LICENSE` (21 строка, полный текст MIT).
- **Правообладатель:** «Copyright (c) 2021 Exercism».
- **Дополнительный evidence:** `README.md` → раздел **«Exercism Python Track License»**: «This repository uses the [MIT License***REMOVED***(/LICENSE).» (строки 97–99, коммит выше).
- **Проверка уникальности:** по всему дереву (без `.git`) найден **ровно один** LICENSE/COPYING-файл — корневой. Файлы .py не содержат license-хедеров (проверены примеры stub/example/exemplar/test) — единая лицензия репо покрывает всё.

### 3.2 Пофайловый статус по классам файлов

| # | Класс файлов | Примеры | Статус | Evidence (по коммиту `1f6aab8…`) |
|---|---|---|---|---|
| 1 | Content exercises (statement/инструкции) | `exercises/*/.docs/instructions.md`, `introduction.md`, `hints.md` | ✅ **approved** | файлы в дереве репо; MIT (LICENSE + README §License) |
| 2 | Tests | `exercises/*/*_test.py` (concept 21 + practice 140) | ✅ **approved** | там же |
| 3 | Stubs (заготовки решения) | `exercises/*/*.py` (без `_test`) | ✅ **approved** | там же |
| 4 | Metadata упражнений | `.meta/config.json`, `.meta/design.md`, `.meta/tests.toml` | ✅ **approved** | там же |
| 5 | Reference solutions | `.meta/example.py` (practice), `.meta/exemplar.py` (concept) | ✅ **approved** (но импорт — только с `--with-refs`, S0-7) | там же |
| 6 | Concepts-справочники | `concepts/*/{about.md,introduction.md,links.json***REMOVED***` | ✅ **approved** | там же |
| 7 | Reference-доки трека | `reference/*.md`, `docs/*.md` | ✅ **approved** (не импортируются в v0.1) | там же |
| 8 | Трек-конфиг | `config.json`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | ✅ **approved** | там же |
| 9 | Инструменты/CI | `bin/`, `.github/`, `config/`, `pylintrc`, `.flake8`, `.style.yapf` | ✅ **approved** (не импортируются) | там же |
| 10 | Approaches (статьи сообщества) | `exercises/practice/*/.approaches/**` (32) | ✅ **approved** (в v0.1 НЕ импортируются — вне scope ingestion) | там же |

### 3.3 Сторонние материалы (отдельный блок)

| Проверка | Результат |
|---|---|
| Project Euler / Rosetta Code / Codewars / HackerRank / LeetCode / AoC в текстах репо (`*.md`, `exercises/`) | ❌ **не найдено** ни одного упоминания в statements/инструкциях (grep по всему дереву, включая `exercises/`) |
| `config.json` (slug/blurb/topics) | ❌ упоминаний сторонних платформ нет |
| `source_url` в `.meta/config.json` | ⚠️ **смешанные**: ~58% ведут на внешние origins, не только `exercism/problem-specifications` — см. §3.4 (полная таблица хостов) |
| Внешние ссылки в `links.json` / `docs/` | Есть (обучающие материалы; `concepts/{bitwise-operators,secrets***REMOVED***/links.json`, `docs/LEARNING.md`) — это **ссылки**, not заимствованный контент; импорт statement НЕ копирует ссылки как контент |
| Примечание | Тексты задач написаны сообществом Exercism под MIT, от **исходников идей** paraphrase-ваны (проверено на Project Euler-производных, §3.4); attribution сохраняется через `source_url` |

**Статус:** external-блок **approved с условием** — attribution: `source_url` каждого упражнения сохраняется в corpus (поле metadata), тексты paraphrase, ссылки не импортируются; если при ручном ревью конкретного упражнения будет найден verbatim-текст стороннего источника (не перефразированный) → помечаем `pending` (правило: ничего нàивно→live).

### 3.4 ВТОРОЙ ПРОХОД — сквозной per-file аудит (2026-08-23, верификация)

Повторный проход по ВСЕМ 161 упражнениям и 516 `.py`-файлам (дополняет §3.1–3.3).

**1) License-хедеры в `.py`:** 516 `.py`-файлов, **0** содержат license/copyright-хедер (первые 400 символов, поиск copyright/license/©) → единая repo-лицензия MIT покрывает все файлы, отдельных лицензий нет.

**2) origin-ссылок в `.meta/config.json` всех practice-упражнений (161 файл):**

| Хост | Кол-во | Тип |
|---|---|---|
| `en.wikipedia.org` | 30 | исток задачи (математические): affine-cipher, atbash-cipher, complex-numbers, binary-search… |
| `github.com` | 18 | exercism/problem-specifications (canonical) |
| `web.archive.org` | 11 | kata-источники (bowling kata Uncle Bob, coin-change kata…) |
| `projecteuler.net` | **7** | разборы Project Euler (см. ниже) |
| `www.turing.edu` | 5 | allergies и др. (учебный курс) |
| `www.wolframalpha.com` + `reference.wolfram.com` + `demonstrations.wolfram.com` | 7 | мат. описание (binary, complex-numbers…) |
| `pine.fm` | 4 | beer-song/bob (книга Learn to Program) |
| `users.csc.calpoly.edu` | 3 | crypto-square, grade-school и др. (курс J. Dalbey) |
| `twitter.com` | 2 | accumulate (автор @jeg2), транскрипт — исток идеи |
| `forum.exercism.org` | 2 | ссылки на форум |
| `rosalind.info`, `codingdojo.org`, `cyber-dojo.org`, `www.richardpmann.com`, `www.cs.cornell.edu`, `www.oreilly.com`, `www.udacity.com`, `www.freecodecamp.org`, `www.imdb.com`, `www.rubykoans.com`, `splice.com` | 1 каждый | единичные origins |

**3) Project Euler-производные (7 упражнений):** `difference-of-squares`, `largest-series-product`, `nth-prime`, `palindrome-products`, `pythagorean-triplet`, `series`, `sum-of-multiples` — `source_url: projecteuler.net/problem=…`.
   Проверены тексты instructions (difference-of-square, nth-prime, sum-of-multiples): **перефразировка от исходной задачи** (свой пример, своя формулировка, цель — pedagogy), НЕ копия Project Euler-текста. Вывод: статус `approved` с `attribution_required=true` и сохранением `source_url` в corpus; при импорте запись будет содержать origin-ссылку (provenance).

**4) grep по всем файлам (не только md) `project euler|rosettacode|codewars|hackerrank|khan academy|advent of code|cracking the coding`:** 11 файлов (7 config.json с projecteuler.net, 2 links.json, LEARNING.md, robot-name approach article) — все это ссылки/attribution, не verbatim-тексты сторонних платформ.

**Вывод:** второй проход подтвердил лицензионную чистоту (единый MIT), уточнил attribution-модель (source_url сохраняем), новых рисков не добавил. Все данные — на коммите `1f6aab8…`.

---

## 4. Выводы (statutus → импорт)

### 4.1 Классификация по лицензии → гейт

| Класс | Статус | В `live` corpus | Комментарий |
|---|---|---|---|
| Всё содержимое `exercises/concept\|practice` (statement, tests, stubs, metadata) | ✅ **approved** | да | MIT, redistribution_allowed=TRUE (с сохранением copyright notice — требование MIT) |
| Reference solutions (`example.py`/`exemplar.py`) | ✅ **approved** | только c `--with-refs` | отдельный evidence уже есть (репо-лицензия); флаг — организационное решение S0-7 |
| `concepts/`, `reference/`, `docs/`, конфигурации | ✅ **approved** | нет (справочно) | не являются source-контентом упражнений |
| Сторонний (не-Exercism) контент | — | **НЕ найден** | если появится → `pending`, ручной review (правило: ничего unknown→live) |

### 4.2 Evidence для license-слоя (передача в Шаг 5 — License gate)

Для каждого импортируемого `exercise_source` заполняются:
- `license`: `MIT`
- `license_evidence`: `repo:exercism/python@1f6aab8…/LICENSE` + `README.md §"Exercism Python Track License"`
- `redistribution_allowed = true`, `modification_allowed = true`, `attribution_required = true` (сохранение «Copyright (c) 2021 Exercism» и условий MIT в выходных данных; для локального персонального использования — не требуется публикация)
- `attribution`: `source_url` каждого упражнения сохраняется в corpus (origin задачи — в т.ч. Project Euler-производных, wikipedia и т.д., §3.4)
- `content_policy`: content локально (S0-6: approved → `content_fetch = local`)
- `reference_solution`: `approved` (с флагом, S0-7)

### 4.3. Концептуальный маппинг (для Шага 3, competency map)

- `config.json → concepts` (67 шт.) — кандидат в компетенции (bools, numbers, strings, lists, dicts, loops, conditionals, functions, classes, testing и т.д. — покрывается группами §6 blueprint).
- `reference/exercise-concepts/*.md` — маппинг «упражнение → концепты» (помощнее для маппинг-шага 7).

---

## 5. Ограничения и честность

- Аудит выполнен на **конкретном коммите** (`1f6aab8…`). Upstream меняется → коммит фиксируется в `data/exercism_src/` (git-метаданные клона); при изменении — повторный аудит в баз-гейт («change → update», Шаг 6).
- MIT допускает коммерческое использование; мы используем локально для себя — ограничений нет (prompt1 §11: «коммерческое использование не запрашивается»).
- `foregone` (3: lens-person, nucleotide-count, parallel-letter-frequency) — НЕ импортируются (исключены конфигом трека; pipeline должен их игнорировать).
- `.approaches/`, `bin/`, `.github/` — вне импорта v0.1; при расширении scope — пересмотреть класс 10.

---

## 6. Cross-links

- [`PHASE_BC_PLAN.md`***REMOVED***(../PHASE_BC_PLAN.md) — Шаг 2, CP-2; Шаг 5 (license gate), Шаг 7 (mapping)
- [`prompt1.md`***REMOVED***(../prompt1.md) — §10–§16 (sources/provenance/license)
- [`STEPS.md`***REMOVED***(../STEPS.md) — журнал: CP-2 выполнен, S0-5 закрыт
- Реестр лицензий фактически реализуется в Шаге 5 (`app/ingestion/license.py`)