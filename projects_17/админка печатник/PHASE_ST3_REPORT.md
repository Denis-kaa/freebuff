# PHASE_ST3_REPORT.md — Этап 3: Consumption → Orders (роадмап v6 / промт_5)

> Дата: 2026-09-09 · Статус: COMPLETE · Коммит: см. git log (`stage-3: consumption engine → orders`).
> Основа: промт_печатник_4 (§48 consumption API, §13/§14 трассировка пользователю, §9 без ручного переноса), промт_печатник_5 (Stage 3 — Consumption → Orders, раньше Production).
> Правила владельца, полученные голосом 2026-09-09 и закреплённые тестами:
> 1. Изделие, не влезающее в рулон по ширине, **разворачивается** (ширина↔высота, изображение на рулоне) и считается повёрнутым; ошибка — только если не влезает ни прямо, ни поворотом.
> 2. **Ручная ширина загруженного рулона**: оператор вводит фактическую ширину рулона (1 м / 1.52 м / 3 м плоттер…) — она перекрывает значение реестра.

## 1. Что сделано

- **`POST /api/consumption/calculate`** (§48): material_id из реестра + размеры
  изделия в см + quantity + опциональные policy_overrides (bleed/gap/margins, мм)
  и **roll_width_mm** (ручной рулон). Возвращает полный MaterialConsumptionResult
  движка: product/production area (м²), раскрой (pieces_across×rows),
  погонную длину, отход, remnant-классификацию и расчётную трассировку.
- **Правило поворота** в `choose_plan` (engine): план «как введено» и план
  «повёрнутый» теперь оба пробуются; если прямой не помещается, а повёрнутый —
  помещается, берётся повёрнутый с предупреждением. Ошибка PRODUCT_DOES_NOT_FIT
  только когда не помещается ни одна ориентация (честная ошибка, не
  приблизительный результат — §38 ТЗ промт_3).
- **Расход в заказе**: при сохранении позиции kind=calculator с калькулятора
  `wide` сервер автоматически считает расход по материалу из params
  (legacy-поле material резолвится в реестре по имени/алиасам — BR-W1) и
  сохраняет snapshot в новый столбец `order_items.consumption_json`. Цена
  позиции от расхода НЕ меняется (разделение движков §33 ТЗ промт_4).
- **`roll_width_mm` как поле спеки wide** (additive): расход считается движком
  прямо при `/api/calculate`, если оператор указал рулон; попадает в
  `details.consumption` и показывается в UI расчёта. Без рулона — поведение
  1:1 как раньше (backward compat, паритет golden-тестов не тронут).
- **UI**: в карточке заказа под позицией — строка «расход X м² · 2×1
  (1000x3000) · отход N% · остаток …»; в диалоге расчёта — поле «Ширина
  загруженного рулона, мм» и строка расхода в результате.

## 2. Какие файлы изменены

- `src/printcalc/engine/consumption/roll.py` — choose_plan: правило поворота.
- `src/printcalc/calculators/wide/compute.py` — опциональный вызов движка при roll_width_mm.
- `src/printcalc/calculators/wide/spec.py` — поле roll_width_mm (required=False).
- `src/printcalc_web/db.py` — миграция order_items.consumption_json.
- `src/printcalc_web/store.py` — calculate_material_consumption,
  _consumption_for_calculator_item, расход в _resolve_item и dict-сериализации.
- `src/printcalc_web/api.py` — ConsumptionCalculateIn + POST /consumption/calculate.
- `src/printcalc_web/static/orders.js` — строка расхода в карточке заказа.
- `src/printcalc_web/static/app.js` — ручной рулон + строка расхода в диалоге.
- `src/printcalc_web/static/style.css` — .consumption-line.
- `src/printcalc_web/templates/index.html` — поле рулона в диалоге расчёта.
- `tests/consumption/test_roll.py` — Test 9 переписан под новое правило
  (плюс отдельный тест «не влезает ни так ни эдак»).

## 3. Какие файлы созданы

- `tests/test_consumption_web.py` (8 тестов)
- `PHASE_ST3_REPORT.md` (этот файл)

## 4. Какие API добавлены

- `POST /api/consumption/calculate` — {material_id, width_cm, height_cm,
  quantity, policy_overrides?, roll_width_mm?} → MaterialConsumptionResult.to_dict().
- Расширение существующих (additive, без breaking): `/api/calculate` для wide
  принимает необязательный roll_width_mm; заказы/позиции отдают consumption.

## 5. Какие модели добавлены

- Столбец `order_items.consumption_json` (TEXT, nullable) — snapshot расхода.

## 6. Какие миграции добавлены

- `ALTER TABLE order_items ADD COLUMN consumption_json` (идемпотентно по
  PRAGMA table_info; применяется при connect() — на сервере автоматически).

## 7. Какие тесты добавлены

- `test_consumption_web.py` (8): расход 3×1×2 на рулоне 1 м (поворот, 6 м²,
  0% отхода, трассировка); ручной рулон 3 м (прямая ориентация, те же 6 м²);
  ручной рулон 1.2 м (7.2 м², отход > 0); PRODUCT_DOES_NOT_FIT при полном
  непомещении; неизвестный материал 400; расход автоматически в заказе;
  отсутствие материала не блокирует заказ; цена позиции не зависит от расхода.
- `test_roll.py`: test_product_wider_than_roll_is_rotated (новое правило),
  test_product_does_not_fit_at_all (ошибка при полном непомещении).

## 8. Результат тестов

- `pytest tests -q`: **153 passed** (было 144)
- `mypy src/`: **Success: no issues found in 38 files**
- golden-тесты Riso/Таблички/Wide — без изменений и зелёные (паритет сохранён).

## 9. Что осталось (Этап 4+)

- Production: operations/tasks/QC (OPERATIONS_CATALOG готов как документ).
- Stock (Этап 5): резерв по production_consumption из consumption_json.
- Consumption для Табличек (SHEET-режим реестра — движок уже поддерживает) и
  расход в сметах (сейчас только в заказах).
- Автоподстановка roll_width_mm из последнего использования (память рулона).

## 10. Известные ограничения

- Расход в заказе сейчас только для wide; Таблички/Digital — следующий шаг.
- policy_overrides в заказе фиксированы (дефолты движка) — ручные припуски
  доступны через standalone-эндпоинт.
- consumption_json не пересчитывается при правке заказа (snapshot §49 дух).

## 11. UNKNOWN

- Правило выбора материала, если в params имя не совпало ни с одним алиасом:
  сейчас расход просто отсутствует (не блокирует приём заказа) — возможно,
  владельцу нужен выбор материала вручную в диалоге расчёта.

## 12. Риски следующего этапа

- Production-операции завязаны на consumption (люверсы → OP-13): нужно
  зафиксировать, что production_consumption — источник для резерва (Этап 5),
  а не product_area.

## DoD §21 промт_5

[x] код [x] миграции [x] API [x] тесты [x] ошибки обработаны
[x] документация [x] существующий функционал не сломан (153 зелёных, golden
без изменений) [x] integration tests [x] acceptance: «баннер 3×1×2 → расход
и раскрой видны» проходит [x] git diff проверен [x] нет debug print
[x] нет secrets [x] нет TODO вместо реализации
