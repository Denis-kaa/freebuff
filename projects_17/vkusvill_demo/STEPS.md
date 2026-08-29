# STEPS — log of actions during promt 62 (ROADMAP-VV-001)

> Формат: `step N: <что сделано> | <почему> | <что дальше>`.
> Project-local log — mirror того, что происходит в рамках этой задачи, чтобы пользователь мог проверить промежуточный прогресс, не вникая в ворох CHANGELOG/LESSONS.

---

<!-- step 1: Task 0 — xlsx-skill зародыш -->

## Step 1: xlsx-skill создан (Task 0)

**Что сделано:**
1. Установлен `openpyxl>=3.1.0` (3.1.5 фактически) — валидация PB-2/PB-9 прошла (`import openpyxl` exit 0).
2. `core_02/xlsx_builder.py` создан с минимальным API (`Workbook`, `sheet(name)`, `cell(addr, value=...) / formula=...) / fmt=...)`, `save(path)` atomic, `Workbook.load(path)` classmethod).
3. `tests_09/test_xlsx_builder.py` создан, 10 тестов покрывают: roundtrip, multi-sheet formula persistence, value XOR formula constraint, formula helper, data_only split, format persistence, atomic-save cleanup.
4. `requirements.txt` обновлён: добавлен `openpyxl>=3.1.0` после `pyyaml>=6.0.1` (per roadmap §5 Task 0 §0.1).
5. `projects_17/vkusvill_demo/` создан — корневая директория для всех артефактов демо.

**Почему:**
- Q1–Q4 закрыты (variant `b` для parity-check; 3 категории молочная/крупа/напиток; 2 неочевидных элемента; only Mission B).
- Минимальный API — соответствует roadmap §5 Task 0 (§0.3); PB-9 lesson применяется: explicit `import openpyxl` на уровне модуля даёт loud ошибку при пропадании пакета, как с pyyaml.
- Atomic save (`tempfile + os.replace`) — protected against fuseblk partial writes (PB-7 lesson mirror).

**Что дальше (Step 2):**
- Запустить `pytest tests_09/test_xlsx_builder.py -q` — ожидается 10/10 PASSED.
- Если pass — записать CHANGELOG.md v5.105.0 §Task 0 + перейти к Task 1 (модельный Excel).
- Если fail — задиагностировать через basher, поправить before CHANGELOG.

---

<!-- step 2: Task 1 — model xlsx design + build_model_xlsx.py -->

## Step 2: Task 1 — модельный .xlsx дизайн + build_model_xlsx.py

**Что сделано:**
1. Web-research об общепринятых 4 принципах ритейл-прогнозирования: SMA(W=N), weekday seasonality, safety stock Z×σ×√L, shelf-life correction. Sources: Chopra & Meindl, Hyndman & Athanasopoulos (open), AbcSupplyChain, Relex Solutions.
2. `projects_17/vkusvill_demo/build_model_xlsx.py` создан (~150 строк) — конструктор через xlsx_builder:
   - **3 категории (Q2)**: «Молоко 3.2% 1л» (dairy, shelf=7/lead=2), «Крупа гречневая 800г» (groats, 365/5), «Напиток газир. 1л» (beverage, 90/3);
   - **12-week история** с drift +0.5%/week + per-category weekday pattern;
   - **3 листа**: history (raw sales_qty), forecast (формулы + pre-computed values), order (финальный заказ);
   - **4 принципа в формулах**: `AVERAGE` (SMA W=4), `STDEV.P×1.65×SQRT(L)` (safety stock), `IF(shelf<2L, 0.5, 1.0)` (shelf-life), per-cat weekday index;
   - **2 NON_OBVIOUS (Q3)**: (1) `forecast!K5 = 1.65` без комментария «это Z для 95%»; (2) `forecast!H22 = 0.92` cell-content proxy legacy defined name `post_incident_2024_correction`.
   - **MUST marker «МОДЕЛЬНЫЙ»** в `A1` каждого листа (bold) — guards against confused reading как «настоящий инструмент ВкусВилл».
3. Side-car `projects_17/vkusvill_demo/model_snapshot.json` — pre-computed values dict для parity_check baseline.

**Почему:**
- Per Q1–Q4 clarifications: variant (b) parity, 3 categories, 2 non-obvious, Mission B only.
- Per **user constraint** «не предлагай новые Forge/расширения»: НЕ расширяем xlsx_builder API (`define_name()` helper) для NON_OBVIOUS_2 — cell-content proxy эквивалентен по видимости аналитика (label в J7 читается так же, как defined name).
- **Reuse-first**: `build_model_xlsx.CATEGORIES + constants (SMA_WINDOW, SERVICE_LEVEL_Z, INCIDENT_2024_CORRECTION, CATEGORIES, BASE_DATE)` — один source of truth. `forecast.py` импортирует их, никакой magic numbers ad-hoc.

**Что дальше (Step 3):**
- Запустить `python3 projects_17/vkusvill_demo/build_model_xlsx.py` → ожидается `OK: model_forecast.xlsx` + `OK: model_snapshot.json`.
- Cross-check через openpyxl `wb.sheetnames` → `['history','forecast','order'***REMOVED***`. Проверить `forecast!K5 == 1.65` + `forecast!H22 == 0.92`.

---

<!-- step 3: build_model_xlsx ran + .xlsx валиден -->

## Step 3: Task 1 build выполнен, .xlsx валиден (3 sheets, formulas, NON_OBVIOUS)

**Что сделано:**
1. `python3 build_model_xlsx.py` → output: `model_forecast.xlsx` (3 листа) + `model_snapshot.json` (3 SKU с полями forecast/order + `_meta`).
2. openpyxl cross-check: `wb.sheetnames` = `['history','forecast','order'***REMOVED***`. `forecast!G4:G6` содержат формулы `=(C*D+E)*F`. `forecast!K5 = 1.65` (NON_OBVIOUS_1 ✓), `forecast!H22 = 0.92` (NON_OBVIOUS_2 ✓). `forecast!A1` содержит МОДЕЛЬНЫЙ marker (bold).
3. Side-car `model_snapshot.json`: 3 SKU × {sma, wd_factor, safety_buffer, shelf_correction, final_forecast***REMOVED*** + order + `_meta.{base_date, weeks, categories, non_obvious***REMOVED***`.

**Почему:**
- Per CAN-16 (splice-with-guard + additivity): xlsx_builder API не расширен, всё через существующий public API.
- Per CAN-17 (anti-rewriting + audit-trail): каждое решение зафиксировано в этом STEPS.md, и в PROJECT_REQUIREMENTS.md / business_logic.md.

**Что дальше (Step 4):**
- Перейти к Task 2: forecast.py (Python-recompute) + parity_check.py (variant b) + vkusvill_demo.yaml.

---

<!-- step 4: Task 2 — Teamwork 3 роли -->

## Step 4: Task 2 — Teamwork 3 роли (analyst / developer / reviewer)

**Что сделано:**
1. `projects_17/vkusvill_demo/forecast.py` создан (~80 строк) — developer-role артефакт:
   - Imports `CATEGORIES, SMA_WINDOW, SERVICE_LEVEL_Z, INCIDENT_2024_CORRECTION, BASE_DATE, WEEKS` from `build_model_xlsx` (one source of truth, NO duplicates).
   - `load_history_from_xlsx()` — read raw sales_qty через `openpyxl.load_workbook(data_only=True, read_only=True)`. **NO formula eval** (variant b per Q1).
   - `compute_forecast()` — applies same 4 принципа в Python: SMA via `sum[-W:***REMOVED***`, sigma via `pstdev`, safety via `sigma×Z×√L`, shelf via `IF(shelf<2L, 0.5, 1.0)`, final = `((sma×wd)+safety)×shelf`.
   - `compute_order()` — `max(0, final×L − stock + final×0.1)` + **`× INCIDENT_2024_CORRECTION` ТОЛЬКО для категории `dairy`** (NON_OBVIOUS_2 применённый at order level).
   - Output `forecast_python.json` (3 SKU × {forecast, order***REMOVED***).
2. `projects_17/vkusvill_demo/parity_check.py` создан (~100 строк) — reviewer-role артефакт (variant b):
   - `_read_xlsx_precomputed()` — reads cached values из `forecast!G* + order!E*` через `data_only=True, read_only=True`. NO `formula=`, NO LibreOffice, NO Excel eval.
   - `_compare()` — pure dict comparison: per-SKU fields (sma, wd_factor, safety_buffer, shelf_correction, final_forecast) + order.order_qty. Tolerance ±0.01.
   - Output `parity_report.md` с PASS/FAIL per row + OVERALL status.
   - Exit 0 если PASS, 1 если FAIL.
3. `runtime_05/scenarios/vkusvill_demo.yaml` создан:
   - `id: vkusvill_demand_forecast`, `type: teamwork`, `display_name: «ВкусВилл demo — разбор legacy Excel/VBA логики прогноза/заказа»`.
   - `capabilities: [reasoning, explain, code, validate, verify***REMOVED***`.
   - `metadata.roadmap_id: ROADMAP-VV-001`, `bound_to_data: false` (modельное, не реальный ритейлер).
   - 3 роли (analyst/developer/reviewer) как ADDITIVE keys (ScenarioRegistry парсит все yaml в директории, non-standard keys — ADDITIVE не ломают парсер).

**Почему:**
- Per **Q1 variant (b)**: Python-recompute vs pre-computed Excel values, **NO LibreOffice invocation** — убирает внешнюю системную зависимость, тот же class risk что PB-2/PB-9 для pyyaml на Termux.
- Per **user constraint**: НЕ расширяем ScenarioRegistry для YAML с ролями — keys roles/inputs/verification ADDITIVE, не требуют миграции парсера.

**Что дальше (Step 5):**
- Прогнать `python3 projects_17/vkusvill_demo/forecast.py` → ожидается JSON.
- Прогнать `python3 projects_17/vkusvill_demo/parity_check.py` → ожидается `OVERALL: PASS`. Если FAIL — диагностика (xlsx-side computed vs Python).

---

<!-- step 5: Парность PASS + parity_report.md -->

## Step 5: Parity Check ✅ PASS (3/3 SKUs)

**Что сделано:**
1. `python3 forecast.py` → `OK: forecast_python.json` + total order_qty ≈ xlsx-side total (modulo float rounding).
2. `python3 parity_check.py` → `parity_report.md` сгенерирован, `OVERALL: ✅ PASS` (3/3 SKUs × {5 forecast-полей + order_qty***REMOVED*** = 18 PASS-строк, 0 FAIL).
3. Tolerance ±0.01 соблюдён по всем строкам.

**Почему:**
- Pre-computed values в `.xlsx` (openpyxl сохраняет то, что мы передали в `value=...`) — это numeric snapshot, не formula evaluation. `data_only=True` для read XLSX читает этот cached value.
- Per Q2 (variant b): **NO Excel/LibreOffice invocation**, NO pychart, just dict comparison.

**Что дальше (Step 6):**
- Task 3: README + short_report + registry updates (INDEX + DOC REGISTRY).

---

<!-- step 6: Task 3 done, registry updated -->

## Step 6: Task 3 — честный артефакт + реестр

**Что сделано:**
1. `projects_17/vkusvill_demo/README.md` создан: явный МОДЕЛЬНЫЙ marker в первой строке, инструкция запуска (3 команды), границы честности (NO real data / NO VBA / NO LibreOffice / NO Forge-ext).
2. `projects_17/vkusvill_demo/short_report.md` создан (<100 строк): TL;DR всех 4 задач + parity result + 4 принципа + 2 NON_OBVIOUS + manifest файлов.
3. `projects_17/vkusvill_demo/LESSONS.md` создан (узкий per user constraint): 3 конкретных факта + 1 открытый вопрос, без Forge-ext.
4. `docs_10/INDEX.md` обновлён: ROADMAP_VV-001 добавлен рядом с ROADMAP_FORGE_RECONCILIATION.
5. `docs_10/DOCUMENT_REGISTRY.md` обновлён: ACTIVE counter +1, добавлена строка `ROADMAP_VKUSVILL_DEMO_062.md | ACTIVE | ROADMAP-VV-001 v5.105.0 …`.
6. `core_02/LESSONS.md` обновлён: **CON-54** (Teamwork-decomposition: роль ≠ generic, role = конкретный узкий output).
7. `CHANGELOG.md` v5.105.0 записан полностью (Task 0/1/2/3 все заполнены).

**Почему:**
- Per user constraint «записывай в project-local LESSONS.md только то, что реально всплыло при работе над этой конкретной задачей»: 3 факта + 1 open Q — не больше.
- Per **CAN-17**: mutual cross-refs в INDEX/DOC REGISTRY/CHANGELOG.

**Что дальше:** close сессию, записать .freebuff_result, suggest_followups.

## Step 9 — BUG-001 FIX (2026-08-08)

- **Что сделано:** унифицирована Excel-формула заказа dairy в `build_model_xlsx.py` с Python-семантикой `forecast.py`. Было: `=MAX(0,D-C+B*0.1*0.92)` (коррекция только на буфер B*0.1). Стало: `=MAX(0,D-C+B*0.1)*0.92` (dairy) / `*1.0` (прочие) — коррекция на ВЕСЬ заказ, математически эквивалентно Python `max(0, final*L - stock + final*BUF) * CORR`.
- **Почему:** аудит promt 64 нашёл BUG-001 CRITICAL — расхождение Excel vs Python 8.3% (823.87 vs 760.90) для dairy, parity этого не ловил (оба источника — Python).
- **Верификация:** пересборка build→forecast→parity: формула-simulated Excel ≡ Python для всех 3 SKU (max diff = 0.000000, tolerance 0.01), parity OVERALL PASS.
- **Не трогались:** `forecast.py`, `parity_check.py` (их Python-логика была корректной).
- **Статус BUG-001:** RESOLVED. BUG-005 (circular parity — parity сравнивает Python-vs-Python, Excel-формулы не вычисляются) остаётся открытым как отдельная задача.

## Step 10 — BUG-005 FIX: dual-leg parity + независимый Excel-eval (2026-08-08)

- **Что сделано:** parity переведён на **dual-leg**: Leg 1 = Python-consistency (snapshot vs forecast_python, как раньше) + **Leg 2 = независимый Excel-eval**. Создан `projects_17/vkusvill_demo/excel_eval.py` (~450 строк) — минимальный Excel-formula evaluator: читает формулы прямо из `.xlsx` (`openpyxl data_only=False`), парсит (tokenizer + recursive descent, БЕЗ eval/exec), вычисляет. Поддерживает AVERAGE/STDEV.P(pstdev)/SQRT/IF/MAX/SUM, cross-sheet refs, range refs, вложенные формулы с ленивым кэшем + cycle-detection. `parity_check.py` v3: Leg 2 сравнивает excel_eval результат с forecast_python.json.
- **Почему:** BUG-005 — заявленная «Excel-vs-Python эквивалентность» доказывалась Python-vs-Python (оба источника — один код). Реальный Excel-eval невозможен: pycel падает на Python 3.14 (`ast.Str` removed), `formulas` требует numpy/pandas (не ставится на ARM64 Termux), LibreOffice недоступен. Собственный безопасный parser — 0 новых зависимостей (только openpyxl, уже в requirements).
- **Верификация:** `tests_09/test_excel_eval.py` — 20/20 PASS (в т.ч. temp-workbook тесты: MAX clamp, IF, cross-sheet, circular reference, unknown sheet, bad address, VLOOKUP unsupported). Полный pipeline build→forecast→excel_eval→parity: **Leg1 PASS + Leg2 PASS → OVERALL PASS**. Excel-eval ≡ Python по всем 3 SKU + TOTAL (diff ≤ 0.01). Регрессия test_xlsx_builder.py чистая. py_compile OK.
- **Не трогались:** build_model_xlsx.py (формулы корректны после BUG-001 fix), forecast.py.
- **Статус BUG-005:** RESOLVED. parity теперь реально доказывает, что формулы В ФАЙЛЕ (что посчитал бы Excel) дают те же значения, что Python.
