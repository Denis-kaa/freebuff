# PHASE_DIGITAL_REPORT.md — портирование калькулятора Digital (роадмап v6, параллельный трек)

> Дата: 2026-09-10 · Статус: COMPLETE · Коммиты: `stage-digital` (см. git log)
> Основа: legacy `Калькуляторы.zip → Общий калькулятор печати/build_all/calc_digital.py` (1030 строк, Tkinter).

## 1. Что перенесено

**Калькулятор «Цифровая печать (Digital)»** — четвёртый в реестре платформы
(`digital → riso → tablichki → wide`). Порт 1:1 семантики legacy
`DigitalPolyCalc.calculate()` (строки 349–455):

| Элемент | Legacy | Порт |
|---|---|---|
| Бумага (8 позиций, цена листа A4) | `PAPERS` стр. 21 | `DigitalConfig.papers` |
| Краска ч/б 0.10 / цветная 1.20 | `INK` стр. 39 | `DigitalConfig.ink` |
| Подготовка 100 ₽, мин. заказ 500 ₽, наценка 30% | стр. 42–44 | `setup_cost/min_order_price/markup_default` |
| 6 доп. операций (лист/копия/заказ) | `STANDARD_OPERATIONS` стр. 43–50 | `Operation` + чекбоксы `extras_*` |
| Листы A4/A3/SRA3 + зазор 2 мм | `SHEET_FORMATS`/`GAP` | `sheet_formats`/`gap` |
| 9 шаблонов изделий | `PRODUCT_TEMPLATES` стр. 55–65 | `ProductTemplate` (+ опции UI) |
| Прайс изделий по диапазонам тиража | `init_default_prices` стр. 67–76 | `PriceRange` + fallback 10 ₽/шт |
| Плотность раскладки (floor с зазором) | `calc_density` стр. 315–330 | `_calc_density` |
| Листы: 1 полоса → ceil(copies/density); duplex → ceil(pages/2)×copies; simplex → pages×copies | стр. 375–383 | 1:1 |
| Цена = прайс×тираж + (допы+подготовка)×(1+наценка); min order | стр. 386–428 | 1:1 |

**Отличие от legacy (осознанные, задокументированные):**
- GUI (Tkinter, messagebox) → `CalcInputError` с теми же текстами ошибок.
- JSON-настройки (`digital_poly_config.json`) → инъекционный `DigitalConfig`
  (frozen dataclass, правила CODE_QUALITY 4.x); редактирование — будущий UI настроек.
- Налог 6% (включённый, как в канонических калькуляторах платформы) добавлен
  поверх `price_no_tax`; в legacy Digital налога не было — цена выводилась как есть.
- Себестоимость = бумага + краска + допы + подготовка (печать — доход, не расход),
  как в legacy; `net_profit` = цена без налога − себестоимость.

## 2. Файлы

- `src/printcalc/calculators/digital/config.py` — канонические константы (frozen)
- `src/printcalc/calculators/digital/spec.py` — 16 полей (5 STRING с опциями из конфига, 4 NUMBER, 1 BOOLEAN duplex + 6 extras-чекбоксов)
- `src/printcalc/calculators/digital/compute.py` — чистая функция, порт 1:1
- `src/printcalc_web/calculators.py` — регистрация + резолвер опций STRING-полей
- `src/printcalc_web/parser.py` — ключевые слова «цифра/цифровая(ую)» для интент-парсера
- `tests/test_digital_golden.py` — 9 golden-тестов с независимой деривацией

## 3. Golden-тесты (деривация в докстринге каждого кейса)

1. **Визитка 90×50, A4, 100 шт, duplex, цветная** → density 10, печать 400,
   бумага 3.5, краска 24, себестоимость 127.5, цена 530 → **563.83 ₽** (налог 6%)
2. **Листовка А5, 10 шт + ламинация** → min order 500 применяется
   (цена без налога 229.5 → 500), warning «Применён минимальный заказ»
3. **Евробуклет 2 полосы duplex** → листы = ceil(2/2)×50 = 50, fallback-прайс 10 ₽/шт
4. **2 полосы simplex** → листы = pages×copies = 200
5. **SRA3** → area_mult ≈ 2.306, density 24
6–9. Ошибки: изделие не помещается на лист, неверная бумага/цветность, тираж ≤ 0,
   fallback-прайс без диапазонов.

## 4. Качество

- **204 теста** (было 195, +9 golden), mypy clean (43 файла).
- Реестр: `ids = ['digital', 'riso', 'tablichki', 'wide']` — тест API обновлён.
- Парсер: «нужна цифра 100 визиток» → `digital` с qty=100 (визитки — fallback
  прайса изделия; слово «визиток» в unknown до добавления синонима).
- UI: диалог расчёта строится schema-driven — Digital появился автоматически,
  все 5 справочников (изделие/бумага/цветность/лист) подтягиваются из конфига.

## 5. Осталось портировать

`sign_calc.py` (Буквы/Вывески, 59k), `cnc_calc.py` (ЧПУ, 29k),
`design_calc.py` (Дизайн/макеты, 44k), `universal_calc.py` (Себестоимость, 55k).
