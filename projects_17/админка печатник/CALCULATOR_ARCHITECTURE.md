# CALCULATOR_ARCHITECTURE.md — архитектура калькуляторов

> Статус: COMPLETE · Дата: 2026-09-07

## 1. Контракт калькулятора

```
Calculator (модуль)
   ↓  metadata.yaml   (id, название, категория, версия, enabled)
   ↓  input_schema.json   (поля, типы, единицы, дефолты)
   ↓  validation      (Pydantic по схеме)
   ↓  calc.py::compute(input, registry) -> Result   (pure-функция)
   ↓  result_schema.json  (поля результата, breakdown, warnings)
   ↓  presentation    (UI рендерит по result_schema)
```

## 2. Реестр и категории

- `data/registry/calculators.yaml` — список: id, категория (`печать`, `наружная реклама`, `дизайн`, `производство`), порядок, enabled.
- Отключение калькулятора = `enabled: false` (без удаления кода).
- Версионирование: `version` в metadata; при изменении формулы — bump + golden-тест обновляется осознанно.

## 3. Схемы (пример)

```json
// calculators/riso/input_schema.json (фрагмент)
{
  "format":   {"type": "enum", "options": ["A4","A5","A6","A3"], "default": "A4"},
  "qty":      {"type": "int", "min": 1},
  "originals":{"type": "int", "min": 1},
  "duplex":   {"type": "bool", "default": false},
  "paper":    {"type": "ref", "registry": "paper"},
  "color":    {"type": "enum", "options": ["ч/б","1 краска","2 краски"]},
  "markup":   {"type": "percent", "default": 25},
  "extras":   {"type": "multi", "options": ["cutting","lamination","folding","stapling","delivery"]}
}
```

## 4. Ошибки и тесты

- Ошибки валидации — 422 с полем; ошибки расчёта (нет ставки) — `{warnings:[...]}` + `price: null` (как сейчас «нет ставки» в ЧПУ).
- Каждый модуль: `tests/calculators/test_<id>.py` — golden-наборы (вход → ожидаемая цена/себестоимость) + контракт-тест схемы.

## 5. Демонстрация критерия расширяемости на существующем калькуляторе (Riso)

Перенос без изменения ядра:
1. `calculators/riso/metadata.yaml` — id `riso`, категория `печать`.
2. `input_schema.json` — поля из текущей формы (формат/тираж/оригиналы/двусторонность/бумага/цветность/наценка/допы).
3. `calc.py::compute()` — перенос формулы из `Коды…/Riso/riso_calc.py:520-645` как pure-функции; `MIN_ORDER`, `TAX_RATE` — из реестра.
4. `result_schema.json` — price, unit_price, cost, breakdown (бумага/краска/мастер/работа/допы), warnings (подъём до мин. тиража).
5. Запись в `calculators.yaml`. Ядро (движок, API, UI) не менялось — требование DoD выполнено на реальном примере.

## 6. DoD

- [x] контракт определён; [x] регистрация/категории/версии; [x] схемы входа/выхода; [x] ошибки; [x] тесты; [x] расширение продемонстрировано на существующем калькуляторе.
