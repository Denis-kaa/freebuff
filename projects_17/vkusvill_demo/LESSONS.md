# LESSONS.md — project-local lessons для vkusvill_demo

> **Per user constraint (clarifications to Q1-Q4):**
> Записывай в project-local LESSONS.md только то, что реально всплыло при работе над этой конкретной задачей.
> Не предлагай новые Forge или расширения архитектуры платформы в рамках этой задачи.
> Открытый вопрос — одной строкой как `Q:`, не развивать архитектурно.

---

## Факты (привязаны к коду, narrow scope)

### F-1: cell-content proxy вместо openpyxl defined_name

Для **non-obvious element 2** (`post_incident_2024_correction`) выбран cell-content подход (значение `0.92` в `H22` + label `INCIDENT_2024_CORRECTION` в `J7`) **вместо** полноценного openpyxl `defined_names` API. Причина:
- API `core_02/xlsx_builder.py` минимальный (Task 0 scope) — `define_name()` helper НЕ существует;
- расширение xlsx_builder добавило бы **новый Forge-уровень компонент**, что нарушает user constraint «не расширять архитектуру платформы в рамках этой задачи»;
- **cell-content эквивалентен по видимости** для аналитика: label в J7 + значение в H22 читается так же, как defined name `post_incident_2024_correction` в legacy VBA.

Если в будущем понадобится парсить/писать named ranges — это отдельный tool/Forge (см. открытый вопрос).

### F-2: weekday pattern для напитков имеет «спад вт-ср + пик сб»

В [business_logic.md §2.2***REMOVED***(./business_logic.md#22-weekday-seasonality-index--принцип-2) pattern `[0.90, 0.85, 0.85, 0.95, 1.25, 1.50, 1.30***REMOVED***` отражает реальный ритейл-профиль (сб пик 1.5×, вт-ср спад 0.85×). Использован как **ground truth из retail-практики** (Hyndman & Athanasopoulos, OTexts) — не как «выдуманные числа для красоты». Аналитик имеет возможность cross-check с отраслевыми литературными паттернами.

### F-3: parity path — Python recompute + formulas (NO Excel eval)

**Per Q1 variant (b)** parity pipeline: `build_model_xlsx` пишет formulas + pre-computed values в cell через `value=...`; `forecast.py` пересчитывает **только из raw history** через `load_workbook(data_only=True, read_only=True)` — **никакой formula eval**; `parity_check.py` сравнивает cached values vs Python dict.

Никакого LibreOffice / Excel-run / формул-вычислений — просто dict comparison с tolerance ±0.01. Этот класс pipelinа убирает **системную зависимость** (тот же class risk, что PB-2/PB-9 для pyyaml на Termux).

---

## Открытый вопрос (1 строка per user constraint)

- ⏳ **Q-vkusvill-xlsx-parser:** если в будущем понадобится parsing произвольного `.xlsx` (чужого файла) — отдельный tool/skill, или расширение `xlsx_builder`? **Текущий scope** — мы только пишем свой `model_forecast.xlsx` + читаем его же; ни parser чужого xlsx, ни editor named-range, ни chart layer. **Не предлагаю** Forge в этом LESSONS.md (per user constraint).

## BUG-001 (2026-08-08)
- Excel-формула заказа dairy отличалась от Python: `MAX(0,D-C+B*BUF*CORR)` vs `max(0,D-C+B*BUF)*CORR` → 8.3% расхождение. Parity (Python-vs-Python JSON) не ловил. Исправлено: `=MAX(0,D-C+B*0.1)*0.92` ≡ Python.

## BUG-005 — закрыт через независимый Excel-eval (2026-08-08)

**Что всплыло при работе:** parity, сравнивающий два Python-источника (snapshot от build_model + forecast), НЕ доказывает Excel-vs-Python эквивалентность — Excel-формулы никогда не вычислялись.

**Точечный фикс:** `excel_eval.py` — минимальный независимый evaluator формул из .xlsx (tokenizer + recursive descent, без eval/exec), подключён как Leg 2 в `parity_check.py` v3. Причины отказа от стандартных путей (факт среды): pycel несовместим с Python 3.14 (`ast.Str` removed), `formulas` требует numpy/pandas — не ставится на ARM64 Termux за разумное время, LibreOffice недоступен.

**Факт для будущего:** на Termux/Python 3.14 «доказать Excel-vs-Python» означает одно из: (a) собственный evaluator под подмножество формул проекта (как здесь, 0 новых зависимостей); (b) вендорный Excel-движок. Выбор (a) снимает зависимость от LibreOffice — тот же класс решения, что Q1 variant (b).
