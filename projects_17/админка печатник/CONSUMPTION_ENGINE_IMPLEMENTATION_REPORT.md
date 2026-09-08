# CONSUMPTION_ENGINE_IMPLEMENTATION_REPORT.md — отчёт перед реализацией движка расхода

> Статус: COMPLETE (pre-study) · Дата: 2026-09-08 ·
> Выполнено по §58 ТЗ «Production Material Consumption & Cut Engine» (промт_печатник_3.md):
> изучение выполнено, кодирование ещё не начато. Реализация стартует только после
> подтверждения плана (Phase 1 → адаптер Wide → проверка контрольных примеров).

## 1. Что уже существует (факты, file:line)

### 1.1 printcalc — текущее ядро (живой код, в репозитории)

| Компонент | Файл | Факт |
|---|---|---|
| Контракт | `printcalc/src/printcalc/engine/spec.py` | `CalculatorSpec` / `FieldSpec` / `FieldKind` (STRING/NUMBER/BOOLEAN) |
| Валидация | `printcalc/src/printcalc/engine/validate.py` | схема-валидация входов до compute |
| Реестр | `printcalc/src/printcalc/engine/registry.py` | закрытый реестр, дубликат/неизвестный id = RegistryError |
| Результат | `printcalc/src/printcalc/engine/result.py` | `CalcResult(price, price_no_tax, cost, net_profit, unit_price, lines, warnings, details)` + `CostLine` |
| Ошибки | `printcalc/src/printcalc/engine/errors.py` | `CalcError` / `CalcInputError` / `RegistryError` / `ValidationIssue` |
| Калькуляторы | `printcalc/src/printcalc/calculators/{riso,tablichki,wide}/` | config → spec → compute, реестр через `register()` |
| Web-мост | `printcalc/src/printcalc_web/calculators.py` | `get_registry()` (lru_cache) + опции STRING-полей из канонических конфигов |
| Тесты | `printcalc/tests/` | 71 passed: golden Riso (5+), Tablichki (7), Wide (10), реестр, store, API |
| Типизация | mypy | clean, 30 файлов |

### 1.2 Документы

- **CALCULATOR_MATRIX.md** (COMPLETE, 2026-09-07) — матрица 8 калькуляторов;
  §2: кандидаты на общий движок (диапазонный прайс ×4, PricePair ×3, люверсы ×2,
  нормализация единиц, монтаж по высоте ×2, налог/наценка ×3); §3: правило миграции
  «переносить только из wrapper-редакций (Общий калькулятор печати), standalone —
  исторический артефакт».
- **MATERIAL_MODEL.md** (COMPLETE-проект, 2026-09-07) — реестр материалов с id/alias,
  единицы и нормализация (§4: Input → расчётная → Display), закупки/расход/остатки —
  PROPOSED (в исходниках отсутствуют), остатки расчётные, не инвентаризация;
  нормы: баннер = площадь×1.1 (коэффициент владельца), люверсы = периметр/шаг (BR-06),
  краска RISO 20 л/1000 оттисков (equipment.json), тонер 0.8 мл/лист.
- **PHASE1_REPORT.md** — roadmap A–F; потребление материалов — этап E.

### 1.3 Legacy-исходники (Калькуляторы.zip, 328 МБ)

Все 8 калькуляторов доступны **как исходный код** (не только аудиты):

| Калькулятор | wrapper-редакция (канон) | standalone | Важное для движка расхода |
|---|---|---|---|
| RISO | `Общий…/riso_calc.py` (39 472 B) | `Коды…/Riso/` | НЕ переводить на nesting (§30 ТЗ); consumption_mode = SHEET/COUNT |
| Wide | `Общий…/wide_format.py` (37 306 B) | `Коды…/Shirokoformat/` | **Первый адаптер**: рулонные материалы (баннер 440/510, плёнка, холст), площадь тиража, периметр-работы (загибка/карман), люверсы ceil(перим/шаг)×тираж |
| Таблички | `Общий…/tablichki.py` (37 932 B) | `Коды…/Tablichki/` | листовые заготовки (ПВХ/акрил/композит), крепёж за штуку |
| Вывески | `Общий…/sign_calc.py` (65 122 B) | `Коды…/Буквы/` | Phase 3: профиль → пог.м, акрил/ПВХ → лист/раскрой, крепёж → шт |
| Digital | `Общий…/digital_calc.py` (51 674 B) | дубль 51 672 B | Phase 2: рулонный digital через производственную длину |
| ЧПУ/Laser | `Калькулятор фрезерной…/cnc_calc.py` (29 454 B) | — | Phase 3+: SHEET_NESTING (kerf, edge_margin), bounding boxes |
| Дизайн | `Калькулятор макетов/design_calc.py` (43 515 B) | — | услуга, материал не расходуется |
| Себестоимость | `Калькулятор себестоимости/universal_calc.py` (54 566 B) | — | машино-час; Cost Engine использует его нормы |

## 2. Что переиспользуется (без переписывания)

1. **Контракт Spec → validation → compute → Result** — движок расхода встраивается
   как новый слой под калькуляторами, CalcResult не ломается (§47 ТЗ: поле
   `consumption` в details / отдельное поле).
2. **`CalcInputError`** — все ошибки движка расхода наследуют его (§38 ТЗ),
   коды ошибок (ROLL_WIDTH_TOO_SMALL и т.д.) — в поле code.
3. **Golden-подход** — независимо выведенные ожидания; существующие golden-тесты
   RISO/Tablichki/Wide не изменяются (§44, §45).
4. **Единицы** — MATERIAL_MODEL §4 уже фиксирует Input/расчётная/Display; нормализатор
   движка (мм ↔ м) станет реализацией этого раздела.
5. **Прайс-тиры Wide** — `PriceTier` (уже в `calculators/wide/config.py`) — тот же
   паттерн, что просит §2 CALCULATOR_MATRIX для общего прайса.
6. **Store/Web** — SQLite-схема заказов аддитивно расширяется snapshot'ом расхода (§48).

## 3. Что нужно создать (Phase 1 — ядро)

```
printcalc/src/printcalc/engine/consumption/
    __init__.py        # ConsumptionEngine.calculate(material, item, policy)
    models.py          # Material, MaterialConsumptionPolicy, MaterialConsumptionResult,
                       # Scrap/Remnant, Layout, CalculationTrace
    policies.py        # OrientationPolicy (MIN_WASTE/MIN_LENGTH/FIXED),
                       # RoundingMode (NONE/CEIL/FLOOR/ROUND/CEIL_TO_STEP)
    units.py           # нормализатор мм/см/м → внутр. мм; м²; пог.м (единый, §41)
    normalize.py       # effective dimensions: bleed+trim+gap+side_margin (§13)
    roll.py            # RollNestingCalculator: pieces_across/rows/length (§11)
    sheet.py           # SheetConsumptionCalculator / SheetNestingCalculator (§17)
    area.py            # AreaConsumptionCalculator (м² без рулона — текущее поведение Wide)
    linear.py          # LinearConsumptionCalculator (пог.м)
    nesting.py         # выбор ориентации A/B, сравнение расхода (§12, §16)
    rounding.py        # правила округления в одной точке (§19, §40)
    errors.py          # коды: ROLL_WIDTH_TOO_SMALL, PRODUCT_DOES_NOT_FIT, …
```

Плюс: `CalcResult.details["consumption"]` (аддитивно), endpoint
`POST /api/consumption/calculate` (§46, путь v1-префикс согласуем с текущим /api),
tests/consumption/ (Test 1–12 из §43), golden-сравнение legacy Wide vs движок.

## 4. Какие калькуляторы переводятся первыми

1. **Wide Format** — адаптер (Phase 2 ТЗ): рулонные баннер/плёнка/холст получают
   roll-nesting; для старых заказов сохраняется AREA-режим (backward compat, §45).
2. **Digital** — вторым (рулонный, расчёт через производственную длину).
3. **Таблички** — лист/штучные режимы без nesting в первой итерации.

RISO — не трогаем (§30): consumption_mode = SHEET/COUNT, без roll nesting.

## 5. Формулы, подтверждённые исходниками

| Формула | Источник |
|---|---|
| pieces_across = floor(W_eff / w_eff); rows = ceil(Q / across); length = rows × h_eff | §11 ТЗ + подтверждается практикой Wide (периметр-работы уже считают геометрию: wide_format.py:671-673) |
| Люверсы: ceil(перим_см / шаг) × тираж | wide_format.py:700-709 (текущий порт `calculators/wide/compute.py::_work_quantity`) |
| Общий периметр = (Ш+В)·2/100 × тираж | wide_format.py:671 (порт: perim_m_total) |
| Тированный прайс по площади, верхняя граница включительно | wide_format.py:112-122 (порт: `_get_price`) |
| Мин. заказ поднимает sell, не cost | wide_format.py:724-733 |
| Краска/мастера RISO | riso_calc.py:681-724 (порт: calculators/riso/compute.py) |

## 6. Формулы, требующие отдельного подтверждения (не придумывать)

1. **Отход % на загибку баннера** — MATERIAL_MODEL даёт «площадь×1.1» как
   владелец-коэффициент; в исходниках Wide загибка — отдельная работа (пог.м),
   а не коэффициент отхода. → параметр политики, значение спрашивать у владельца.
2. **Интервал люверсов по умолчанию (50 см)** — из GUI legacy; подтвердить у Дениса.
3. **Мин. оплачиваемый расход материалов** — в исходниках только мин. сумма заказа
   (₽), НЕ мин. расход в пог.м. → новое бизнес-правило, значения — от владельца.
4. **Setup/leader/trailer для рулонной печати** — в исходниках отсутствуют;
   взяты из практики roll-калькуляторов (ТЗ §20-21). Значения по умолчанию = 0.
5. **Кратность закупки (рулон 50 м)** — MATERIAL_MODEL PROPOSED; из исходников
   не выводится.

## 7. Возможные breaking changes

| Изменение | Риск | Митигация |
|---|---|---|
| `CalcResult.details["consumption"]` | нет — details открытый dict | аддитивно |
| Wide: материал становится реестром `Material` | средний | адаптер: старые входы (строка-имя) валидны, roll-режим — opt-in через политику |
| Деньги float → Decimal | высокий (golden-тесты) | §42 ТЗ: Decimal только в Cost Engine, consumption возвращает числа; golden не трогаем |
| Новые ошибки `PRODUCT_DOES_NOT_FIT` | низкий | только для roll-режима; AREA-режим ведёт себя как раньше |

## 8. План миграции (соответствует §54)

- **Phase 1 (ядро):** models, units, normalize, roll, orientation, gaps/bleed/margins,
  min consumption vs billing consumption, setup/leader/trailer, rounding, trace,
  Scrap/Remnant-классификация. Unit-тесты Test 1–12.
- **Phase 2 (интеграция):** адаптер Wide (opt-in roll-режим) + сравнение
  «legacy result vs engine result» с регистрацией расхождений; Digital.
- **Phase 3:** Вывески, CNC/Laser (SHEET_NESTING, kerf).
- **Phase 4:** sheet nesting для остатков, gang jobs, SVG-превью, remnant inventory.
- Критерий готовности (§56): сценарий плёнка 1000 мм × 700×800 × 1 →
  product 0,56 / production 0,80 / waste 0,24 (30%) / billing 1,00 пог.м при min 1 м.

## 9. План тестирования

1. `tests/consumption/test_roll.py` — Test 1, 2, 9, 10, 11 (базовая раскладка, границы).
2. `tests/consumption/test_orientation.py` — Test 3 (выбор меньшего расхода) + FIXED.
3. `tests/consumption/test_allowances.py` — Test 4 (gap), 5 (bleed), 7 (setup), 8 (leader/trailer).
4. `tests/consumption/test_billing.py` — Test 6 (production 0.8 vs billing 1.0), min_consumption ≠ min_billing.
5. `tests/consumption/test_remnants.py` — Test 12 (REMNANT/SCRAP по порогам политики).
6. `tests/consumption/test_trace.py` — расчётный след (§9, §53): объяснимость «почему 0,8».
7. `tests/test_wide_golden.py` — остаются без изменений (AREA-режим = текущее поведение).
8. Phase 2: golden «legacy Wide vs engine» — расхождения фиксируются явно, не маскируются.

## 10. Открытые вопросы к владельцу (не блокируют Phase 1)

1. Стандартная ширина рулонов на производстве (баннер 1050/1100/3200? плёнка 1520?).
2. Значения min_billing по материалам (или пока 0 = выкл).
3. Габариты листов ПВХ/акрила для будущего sheet-режима (3050×2050 из ТЗ §17 — подтвердить).
4. Правило: что идёт в себестоимость — production или billing расход (§32 ТЗ).
