# ROADMAP-VV-001 — Промт 62: Модельный Excel-демо для ВкусВилл × xlsx-skill для freebuff

**Версия документа:** v1.0 (draft roadmap, awaiting user command to start implementation)
**Дата:** 2026-08-06
**Миссия:** Демо-сценарий для отклика вакансии «Специалист по AI-автоматизации бизнес-процессов» (ВкусВилл) — разбор модельной Excel/VBA-логики прогноза/автозаказа через Teamwork-роли с построением переиспользуемого xlsx-skill.
**Источник:** `pompts_11/063_08_vkusvill_demo_scenario.md` (содержит две слитые формулировки одной задачи — A и B).
**Версия-цель в CHANGELOG:** **v5.105.0** (bump от текущего v5.104.0 из промта-61).

---

## 🰠 0. Авторское решение: как читать промт 62 (Mission A vs Mission B)

В `pompts_11/063_08_vkusvill_demo_scenario.md` записаны **две формулировки одной миссии** — первая более «доменная» (Task 0–2 про ВкусВилл), вторая более «платформенная» (Task 0 про xlsx-skill + Task 1–3 про использование skill'а).

**Решение (deliberate unification):** берём **Mission B как authoritative**, потому что она строже требует переиспользуемой платформенной возможности (skills не должны быть одноразовыми хаками — это архитектурное правило, зафиксированное в `RFC_BUFFY_FORGE_V1.md`). Mission A — это `Задача 0+` (построить `.xlsx`), Mission B разносит её на `Задача 0 + Задача 1`.

| Mission A (доменная) | Mission B (платформенная, **binds**) |
|---|---|
| Задача 0: построить `.xlsx` | **Задача 0: построить xlsx-skill** + **Задача 1: построить `.xlsx` через skill** |
| Задача 1: Teamwork-разбор | Задача 2: Teamwork-разбор (через `openpyxl`-программное чтение) |
| Задача 2: честный артефакт | Задача 3: честный артефакт |

**Итого 4 задачи (Task 0–3) по Mission B.**

---

## 📊 Прогресс Roll-up (живая таблица, обновляется по факту)

| Task | Название | Зависит от | Acceptance gate | CHANGELOG line | Статус |
|------|----------|-----------|----------------|----------------|--------|
| **Task 0** | xlsx-skill как платформенная возможность | (ничего) | (a) `import openpyxl` == OK после pip install (PB-2/PB-9 защита); (b) `tests_09/test_xlsx_builder.py` PASSED; (c) roundtrip create+open сохраняет формулы и ссылки между листами | `v5.105.0 §Task 0` | ⏳ awaiting go |
| **Task 1** | Модельный `.xlsx` через xlsx-skill | Task 0 | (a) `projects_17/vkusvill_demo/model/demand_forecast_model.xlsx` существует + открывается через `openpyxl` без warnings; (b) 2-3 листа: `История`, `Прогноз`, `Заказ`; (c) минимум 2 «неочевидных» элемента бизнес-логики с пояснением в `business_logic.md`; (d) везде marker «МОДЕЛЬНЫЙ ПРИМЕР, НЕ РЕАЛЬНЫЙ ИНСТРУМЕНТ ВКУСВИЛЛА» | `v5.105.0 §Task 1` | ⏳ awaiting Task 0 |
| **Task 2** | Teamwork-разбор через 3 роли | Task 1 | (a) 3 scenario-карточки добавлены в `runtime_05/scenarios/vkusvill_demo.yaml` (analyst/developer/reviewer); (b) `tests_09/test_scenario_registry.py` остаётся зелёным + 3 новых теста под role-контракты; (c) `analyst` ⇒ `business_logic.md` с non-obvious business смыслом; (d) `developer` ⇒ Python-реализация в `projects_17/vkusvill_demo/python/forecast.py` без магических коэффициентов; (e) `reviewer` ⇒ `parity_report.md` с Δ-proдолжением до 2-decimal precision (Excel vs Python); (f) **CON-54 записан в `core_02/LESSONS.md`** как «первый прецедент многоролевого разбора одного источника, отличный от interior_planner» | `v5.105.0 §Task 2` | ⏳ awaiting Task 1 |
| **Task 3** | Честный артефакт для показа | Task 2 | (a) `README.md` в `projects_17/vkusvill_demo/` явно: «демо-сценарий для ВкусВилл, НЕ платформа, НЕ auto-apply»; (b) все 4 файла × пара nit собраны; (c) ровно ОДИН короткий `report.md` (`< 2 экранов`), без маркетинговой риторики | `v5.105.0 §Task 3` | ⏳ awaiting Task 2 |

> Закрытие ROADMAP-VV-001 фиксируется записью: *«ROADMAP-VV-001 closed YYYY-MM-DD — Hypothesis Mission B unification validated через Task 0+1+2+3, vkusvill_demo артефакт готов для показа пользователю, НЕ для auto-отправки работодателю»*.

---

## 📌 1. Границы (что НЕ делается в этой итерации — explicit scope-exclusion)

Эти ограничения зафиксированы **до** реализации, чтобы не сползать в длительный side-трек:

1. **VBA-макросы НЕ реализуем** — `openpyxl` не поддерживает исполняемый код внутри Excel; отдельная `xlwings`/`pywin32`-библиотека непропорциональна цели демо. Достаточно сложных Excel-формул (`=AVERAGEIF`, `=IF`, межлистовые ссылки), чтобы продемонстрировать «накопившуюся» логику.
2. **docx/pdf/xlsxwriter НЕ подключаются** — только `openpyxl` (одна кодовая база, минимальный API).
3. **Визуальный полишинг xlsx не критичен** — достаточно базового форматирования (заголовки жирным, линии gridline); никаких условных форматов, charts, images.
4. **LLM-слой НЕ предлагается** — все три роли реализуются как Python-функции (analyst = parser business_logic, developer = класс ForecastModel, reviewer = parity checker); без обращения к LLM API.
5. **Числа — модельные, не реальные данные ВкусВилла** — данные про 2-3 категории товаров на ~8-12 недель истории. Никаких попыток извлечь реальные данные.
6. **НЕ «у нас готова платформа»** — артефакт только демонстрирует один реально прогнанный случай (per prompt 62 §Task 3 explicit).
7. **Open-source reusable** — xlsx-skill публичный, тесты публичные; НЕ proprietary, НЕ привязан к конкретному data shape.

---

## 📌 2. Capability-check для аналитических решений (CON-40 pattern)

Сложные аналитические решения внутри Task 1 (выбор принципов прогнозирования) и Task 2 (design 3-role контракта) проходят через **аналитический capability-check**, по образцу **`v5.97.0 CON-40`** (`SmartRouter.route(["reasoning", "plan", "architecture"***REMOVED***)` ⇒ `deepseek-v4-pro`, который имеет все 3 capability-tokens).

> Если в окружении v5.74.0+ capability-инфраструктура падает (Model Gateway недоступен) — это **non-blocking**, fallback на heuristic/LLM-free вариант уже встроен в step-by-step acceptance criteria обоих task.

---

## 📌 3. Sequential-порядок и явные зависимости

### Task 0 → Task 1 (sequential gate: «без xlsx-skill модельный файл не строится»)
- **Reasoning:** Skill = переиспользуемый модуль; если построить `.xlsx` напрямую через ad-hoc openpyxl-код в Task 1 — придётся переписывать его в Task 2 (developer role из Teamwork), потому что dev-role должен использовать skill API, а не ad-hoc.
- **Verify gate:** `python3 -c 'from core_02.xlsx_builder import Workbook; wb=Workbook(); wb.save("/tmp/canary.xlsx"); print("OK")'` exit 0.

### Task 1 → Task 2 (sequential gate: «без `.xlsx` роли не над чем работать; analyst/read tools нужно показать на реальном файле»)
- **Reasoning:** Analyst role = читать формулы через openpyxl; если файла нет — reviewer не может сравнивать; developer не может реализовать.
- **Verify gate:** `projects_17/vkusvill_demo/model/demand_forecast_model.xlsx` существует, размер > 5KB, минимум 3 листа.

### Task 2 → Task 3 (sequential gate: «без parity report артефакт нельзя показывать — обещание "reproduction" не закрыто»)
- **Reasoning:** Вакансионный текст явно требует «воспроизведение логики в новых, более гибких решениях». Доказательство воспроизведения — это и есть parity numbers.
- **Verify gate:** `parity_report.md` имеет явную таблицу «Excel значение vs Python значение» с **Δ ≤ 1e-6** на всех строках расчёта прогноза.

---

## 📌 4. Карта файлов (artifact placement)

Все артефакты — **внутри one well-scoped demo-directory**, не в production code path:

```
projects_17/
└── vkusvill_demo/                          ← новый (created by Task 1)
    ├── README.md                           ← Task 3: «что это, чего это НЕ, marker МОДЕЛЬНЫЙ»
    ├── model/
    │   └── demand_forecast_model.xlsx      ← Task 1: продукт xlsx_builder
    │       ├── Sheet "История"            ← модельные данные продаж (8-12 недель × 2-3 категории)
    │       ├── Sheet "Прогноз"             ← формулы: скользящее среднее × day-of-week × safety × shelf-life
    │       └── Sheet "Заказ"               ← финальный расчёт заказа (forecast + safety stock)
    ├── python/
    │   ├── forecast.py                     ← Task 2 developer: чистая Python-реализация
    │   ├── parity_check.py                 ← Task 2 reviewer: Excel ↔ Python validator
    │   └── requirements.txt                ← локальный pin: openpyxl>=3.1.0 (sed cross-check)
    ├── reports/
    │   ├── business_logic.md               ← Task 2 analyst: что и почему в каждом «неочевидном» элементе
    │   ├── parity_report.md                ← Task 2 reviewer: Excel ⟷ Python numerical match
    │   └── short_report.md                 ← Task 3: ОДИН короткий отчёт для показа (< 2 экранов)
    └── AGENTS.md                           ← local context (project-level role, не в canonical registry)
```

Платформенные артефакты (NOT inside vkusvill_demo):

```
core_02/
├── xlsx_builder.py                         ← Task 0: reusable skill API
├── LESSONS.md                              ← +CON-54 запись Task 2
└── router.py                               ← (no changes expected, но проверить capability для ["reasoning","plan","architecture"***REMOVED*** уже supported)

tests_09/
└── test_xlsx_builder.py                    ← Task 0: roundtrip + multi-sheet + formula persistence

runtime_05/scenarios/
└── vkusvill_demo.yaml                      ← Task 2: 3 scenario-cards (analyst/developer/reviewer)

CHANGELOG.md                                ← v5.105.0 entry covering Task 0+1+2+3
docs_10/INDEX.md                            ← +1 (ROADMAP-VV-001)
docs_10/DOCUMENT_REGISTRY.md                ← ACTIVE count +1
```

---

## 📌 5. Детальные atomic-шаги (с точными acceptance criteria)

### Task 0 — xlsx-skill как платформенная возможность

| Шаг | Действие | Acceptance (тестируемые факты) |
|-----|----------|------------------------------|
| 0.1 | Добавить `openpyxl>=3.1.0` в `requirements.txt` (после `pyyaml>=6.0.1`). | `grep -n openpyxl requirements.txt` показывает 1 строку. |
| 0.2 | `pip install openpyxl` + **валидация PB-2/PB-9** (`python3 -c 'import openpyxl; print(openpyxl.__version__)'` exit 0 → версия ≥ 3.1.0 в stdout). | Команда exit 0; stdout содержит semver-строку. |
| 0.3 | Создать `core_02/xlsx_builder.py` API: `class Workbook`, `sheet(name)`, `cell(addr, value)`, `cell(addr, formula=…)`, `cell(addr, value=…, fmt=…)`, `save(path)`, `load(path) → Workbook`. **НЕ избыточно** — точно эти 4 публичные операции. | `python3 -c 'from core_02.xlsx_builder import Workbook; print(dir(Workbook))'` показывает ровно `cell/sheet/save/load` (без избыточности). |
| 0.4 | Написать `tests_09/test_xlsx_builder.py`: (а) создание книги с 2 листами; (б) формула `=AVERAGE('Historia'!B2:B10)` на листе 2 ссылается на лист 1; (в) save → load → assert `cell.value` совпадает + `cell.formula` сохранён. | pytest PASSED; тестов минимум 4. |
| 0.5 | CHANGELOG.md bump v5.105.0 + Task 0 секция. | `head -3 CHANGELOG.md` показывает `## [5.105.0***REMOVED***`. |

### Task 1 — Модельный `.xlsx` через xlsx-skill

| Шаг | Действие | Acceptance |
|-----|----------|-----------|
| 1.1 | Web-исследование принципов прогнозирования спроса в ритейле: скользящее среднее (4-недельное окно по истории продаж), day-of-week коэффициенты (пн–пт × 1.0, сб × 1.15, вс × 1.25), страховой запас (1σ × 1.65 = 95% покрытие), поправка на срок годности (для скоропортящейся категории × 0.85 план-фактор). **Никаких выдуманных методик.** | Список 4 принципов записан в `projects_17/vkusvill_demo/reports/business_logic.md §Принципы прогнозирования` с короткими 1-line ссылками на источники (например, "industry textbook стандарт"). |
| 1.2 | Создать каталог `projects_17/vkusvill_demo/model/.` | `ls projects_17/vkusvill_demo/model/` exit 0. |
| 1.3 | Сгенерировать 8-12 недель × 2-3 категории × {молоко (скоропортящаяся), крупа (долгохранящаяся), напиток упакованный***REMOVED*** модельные данные продаж (5-30 упаковок/день с day-of-week + сезонный паттерн). | Sheet «История» содержит ячейки A1:D100+ с заголовками `Категория\|Товар\|Дата\|Продано_шт`. |
| 1.4 | Sheet «Прогноз»: среднее скользящее (`AVERAGEIF`), day-of-week коэффициент через `VLOOKUP` на отдельный мини-lookup, safety stock × категория, shelf-life multiplier × «молоко». | Все формулы Excel-валидны (parse-error = 0). |
| 1.5 | Sheet «Заказ»: финальный расчёт = прогноз + safety stock - текущий остаток. | Итоговый лист связан с «Прогноз» через `=Лист2!Cn`. |
| 1.6 | **«Неочевидные» элементы** (минимум 2): (1) коэффициент `поправка_после_сбоя_2024` в ячейке, без комментария — `business_logic.md §Неочевидное 1` объясняет «это пост-аварийная коррекция, +8% к прогнозу на скоропортящуюся после инцидента 2024-Q2»; (2) ячейка `shrinking_factor_Q3_leto` = 0.92 без явной формулы — `business_logic.md §Неочевидное 2` объясняет «летнее снижение спроса на напитки, июль-август». | `business_logic.md` имеет секции «Принципы прогнозирования» (4 пункта) + «Неочевидные бизнес-правила» (≥ 2 пункта с named-cell разбором). |
| 1.7 | **Везде** маркер «МОДЕЛЬНЫЙ ПРИМЕР, НЕ РЕАЛЬНЫЙ ИНСТРУМЕНТ ВКУСВИЛЛА»: в Sheet «README» (новый лист с одной ячейкой A1=MARKER), в имени файла явно (`demand_forecast_model.xlsx`, НЕ `vkusvill_forecast.xlsx`), в `business_logic.md` header. | `grep -ri 'МОДЕЛЬНЫЙ ПРИМЕР\|model example' projects_17/vkusvill_demo/` — ≥ 3 hits. |

### Task 2 — Teamwork-разбор через 3 роли (analyst / developer / reviewer)

| Шаг | Действие | Acceptance |
|-----|----------|-----------|
| 2.1 | Создать `runtime_05/scenarios/vkusvill_demo.yaml` с тремя `roles:` entries, каждая имеет `id`, `responsibility`, `inputs`, `outputs`. | `tests_09/test_scenario_registry.py` остаётся зелёным; новый тест `test_vkusvill_demo_scenario_registers_three_roles` PASSED. |
| 2.2 | **Analyst role**: Python-скрипт (или role-script) `parse_demand_model.py`, который через `openpyxl` читает `demand_forecast_model.xlsx`, вытаскивает все формулы + named-cells, и формирует `business_logic.md` с **бизнес-смыслом** каждой named-cell'и (НЕ просто «формула X делает Y», а «почему это так»). | `business_logic.md` содержит секции «Принципы прогнозирования» + «Неочевидные бизнес-правила» с named-cell-level комментариями. |
| 2.3 | **Developer role**: Чистая Python-реализация `forecast.py` без магических коэффициентов — все константы названы: `MOVING_AVG_WINDOW_WEEKS=4`, `WEEKEND_BOOST=1.15`, `SAFETY_STOCK_Z_SCORE=1.65`, `DAIRY_SHELF_LIFE_FACTOR=0.85`, `POST_INCIDENT_DAIRY_BOOST=1.08`, `SUMMER_DRINKS_FACTOR=0.92`. Сигнатуры: `class ForecastModel(history: pd.DataFrame) → forecast_week(target_date)` → `data class WeeklyForecast`. | `forecast.py` lint clean (no `import *`, docstrings); все константы top-level с `UPPER_SNAKE_CASE`; ни одной цифры внутри docstring без имени. |
| 2.4 | **Reviewer role**: `parity_check.py` открывает `demand_forecast_model.xlsx` через `openpyxl`, считает значения **через ту же формулу** (data_only=True после `xlwings`-style recalc trick, либо Python-парсер формул через `pycel` если доступно, либо **самый честный путь** — пересчёт прогноза в Python по тем же входным данным и сравнение с **сохранёнными значениями** в xlsx, которые Excel уже посчитал при save). | `parity_report.md` содержит таблицу «Excel_value \| Python_value \| Δ» с **Δ ≤ 1e-6** на всех строках расчёта прогноза. NB: если `openpyxl` не считает формулы (это его limitation) — использовать встроенный LibreOffice headless recalc ИЛИ указать в отчёте, что Python пересчитывает прогноз по своим правилам и сверяет численно с теми же входами. |
| 2.5 | **LESSONS.md запись CON-54**: «Teamwork-разбор через 3 роли (analyst/developer/reviewer) для demand-forecast demo — первый прецедент многоролевого разбора одного источника, отличный от interior_planner (где была одна role). Вывод: ScenarioRegistry.search_role_by_id позволяет разным ролям получать доступ к ОДНОМУ источнику с РАЗНЫМИ responsibility/outputs». | `grep -n 'CON-54' core_02/LESSONS.md` = 1 hit (формат: `- CON-54: <title> + full body`). |
| 2.6 | Regression test: 3 теста под role-контракты в `tests_09/test_scenario_registry.py` или в `tests_09/test_vkusvill_demo_roles.py` (отдельный файл, если уместно). | pytest PASSED, +3 теста vs baseline. |

### Task 3 — Честный артефакт для показа

| Шаг | Действие | Acceptance |
|-----|----------|-----------|
| 3.1 | `projects_17/vkusvill_demo/README.md`: (1) явно: «МОДЕЛЬНЫЙ пример, НЕ реальный инструмент ВкусВилла», (2) что внутри (4 files), (3) чего НЕ внутри (НЕ платформа, НЕ auto-apply), (4) как смотреть (запустить `python parity_check.py`, открыть `demand_forecast_model.xlsx` в LibreOffice). | README.md ≤ 80 строк, marker присутствует, `grep -i 'МОДЕЛЬНЫЙ\|model example'` ≥ 1 hit. |
| 3.2 | `report.md` (< 2 экранов): (1) что было разобрано (1 параграф), (2) список неочевидных правил (bullet list из `business_logic.md` с указанием на named-cells), (3) результат parity_check одной строкой (Excel↔Python Δ). | report.md ≤ 100 строк, конкретные числа в разделе parity. |
| 3.3 | CHANGELOG bump секции Task 1+2+3. | `head -50 CHANGELOG.md` корректно отражает v5.105.0. |
| 3.4 | `docs_10/INDEX.md` + `docs_10/DOCUMENT_REGISTRY.md` register ROADMAP-VV-001. | ACTIVE count +1. |

---

## 📌 6. Risk register

| Risk | Severity | Mitigation |
|------|---------|------------|
| **R-1** openpyxl пропадает после Termux reinstall (PB-2/PB-9 recurrence) | Medium | Step 0.2 explicit validation `python3 -c 'import openpyxl'`; если fail → резкий STOP с сообщением пользователю. |
| **R-2** parity_check не может прочитать сохранённые значения из xlsx (openpyxl limitation: не считает формулы) | Medium | Step 2.4 fallback: LibreOffice headless recalc через `subprocess.run(['libreoffice','--headless','--convert-to','csv'***REMOVED***)`. Если LibreOffice недоступен — parity_check реализует **Pythonверсию формул** + сравнение с **Python-forecast**. Явный план в parity_report.md. |
| **R-3** Capability-check для deepseek-v4-pro недоступен в текущем окружении | Low | Fallback на heuristic/LLM-free path; Step детальные acceptance criteria уже содержат конкретные testable facts, без LLM-зависимости. |
| **R-4** Задумываемся о VBA-макросах | Medium | Explicit scope-exclusion §1 — НЕ реализуем. Если убедительность без VBA недостаточна — отдельная следующая итерация с xlwings/pywin32. |
| **R-5** Аудитория воспринимает vkusvill_demo как «у меня готова платформа» | Medium | README.md и report.md явно позиционируют: один прогон, один сценарий, не платформа. README §"Чего НЕ внутри" — обязательно. |
| **R-6** `docs_10/ROADMAP_FORGE_RECONCILIATION.md` имеет naming collision (VV-001 vs FR-001) | Low | Подтверждено через grep, что `ROADMAP_FORGE_RECONCILIATION.md` — singular, не серия. ROADMAP-VV-001 — отдельная уникальная метка. |
| **R-7** Scenario-registry ломается после Task 2 (`test_scenario_registry.py` краснеет) | High | Task 2.1 поручает на роль-protected отдельный файл `vkusvill_demo.yaml`; baseline-check `pytest tests_09/test_scenario_registry.py` ДО и ПОСЛЕ правок (CON-19 lesson). |
| **R-8** pompt62 остаётся под именем `063_08_vkusvill_demo_scenario.md`, не по конвенции `062_xx` | Low | Опционально: после финала rename `pompts_11/063_08_vkusvill_demo_scenario.md` → `pompts_11/062_22_vkusvill_demo_excel_teamwork.md` (по аналогии с 058_21_prioritization). Делаем в Task 3, если не блокирует. |

---

## 📌 7. Что НЕ делается (per Mission B explicit) — boundary re-cap

- ✗ VBA-макросы внутри .xlsx (только формулы);
- ✗ docx/pdf/xlsxwriter (только openpyxl);
- ✗ Визуальный полишинг (basic formatting OK, charts/conditional formats — избыточно);
- ✗ LLM-call (heuristic + testable acceptance criteria);
- ✗ Реальные данные ВкусВилла (только модельные);
- ✗ Auto-отправка работодателю (только локальный показ пользователю).

---

## 📌 8. Acceptance Summary — финальный чек-лист перед commit

- [ ***REMOVED*** `import openpyxl` без ошибок (PB-2/PB-9 validated).
- [ ***REMOVED*** `pytest tests_09/test_xlsx_builder.py` PASSED.
- [ ***REMOVED*** `pytest tests_09/test_scenario_registry.py` PASSED (baseline не сломан).
- [ ***REMOVED*** `projects_17/vkusvill_demo/model/demand_forecast_model.xlsx` существует, 3 листа, формулы parseable.
- [ ***REMOVED*** `business_logic.md` имеет 4 принципа + ≥ 2 неочевидных named-cell разбора.
- [ ***REMOVED*** `forecast.py` без магических коэффициентов (grep по digits-in-code возвращает 0 hits для бизнес-логики — только в named constants).
- [ ***REMOVED*** `parity_report.md` имеет таблицу Excel vs Python с Δ ≤ 1e-6 во всех строках.
- [ ***REMOVED*** `README.md` явно позиционирует демо (МОДЕЛЬНЫЙ, не платформа).
- [ ***REMOVED*** `report.md` < 100 строк, конкретные числа parity.
- [ ***REMOVED*** `core_02/LESSONS.md` содержит CON-54 с правильным форматом.
- [ ***REMOVED*** `CHANGELOG.md` v5.105.0 с покрытием Task 0+1+2+3.
- [ ***REMOVED*** `docs_10/INDEX.md` + `docs_10/DOCUMENT_REGISTRY.md` register ROADMAP-VV-001 (ACTIVE +1).
- [ ***REMOVED*** Везде, где упоминается инструмент, присутствует маркер «МОДЕЛЬНЫЙ ПРИМЕР» (grep ≥ 3 hits).

---

## 📌 9. Открытые вопросы к пользователю (дождаться ответов перед началом)

Эти 4 вопроса явно выходят за рамки роадмапа и должны быть закрыты пользователем **до** старта реализации. Если ответы будут «оставляй на твой judgement» — двигаемся с самым разумным default'ом.

1. **Q1: Parity-check подход.** Шаг 2.4 имеет два варианта: (a) LibreOffice headless recalc + read computed values; (b) Python-формулы + сравнение с Python-forecast (без чтения сохранённых значений из xlsx). Какой предпочесть? Default: (b), честнее и не зависит от LibreOffice.
2. **Q2: Набор категорий.** Молоко + крупа + напиток упакованный (3 категории, 1 скоропортящаяся) — ок, или хотите другой набор? Default: 3 категории как описано.
3. **Q3: Глубина «неочевидных» элементов.** Минимум 2 обязательно. Хотите 3 или 4 для убедительности? Default: 3 (1 magic-coefficient + 1 named-cell + 1 hardcoded post-incident adjust).
4. **Q4: scope промта.** Confirmation что используем только Mission B как authoritative (4 tasks)? Или нужно покрыть Mission A (доменная формулировка) тоже? Default: только Mission B.

---

## 🔗 Cross-links

- Источник: [`pompts_11/063_08_vkusvill_demo_scenario.md`***REMOVED***(../pompts_11/063_08_vkusvill_demo_scenario.md)
- Capability-check паттерн: [`docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md`***REMOVED***(../docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md) §Cat-A (Capability)
- Lesson формат: [`core_02/LESSONS.md`***REMOVED***(./core_02/LESSONS.md) §CON-40, CON-19
- Scenario-registry API: [`core_02/scenario.py`***REMOVED***(./core_02/scenario.py), [`core_02/scenario_registry.py`***REMOVED***(./core_02/scenario_registry.py)
- xlsx-skill размещение (аналогия): нет прямых аналогов в проекте → новый модуль `core_02/xlsx_builder.py`
- Roadmap-формат образец: [`docs_10/ROADMAP_FORGE_RECONCILIATION.md`***REMOVED***(./docs_10/ROADMAP_FORGE_RECONCILIATION.md)

---

**Состояние:** ⏸ ROADMAP draft v1.0 — ожидаю команды пользователя «поехали» / «начинай Task 0» / «внеси правки в §X» / «ответ на Q1-Q4».

**После команды:** применяю Task 0 → Task 1 → Task 2 → Task 3 в sequential-порядке с detailed atomic-steps §5 и фиксирую прогресс в таблице §0 + пишу `.freebuff_result` close-out.
