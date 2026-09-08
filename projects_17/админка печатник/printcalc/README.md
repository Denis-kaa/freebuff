# printcalc — Phase 2 scaffold + Phase 1 web (PrintCalc Pro)

> Статус: COMPLETE · Дата: 2026-09-08 · Часть проекта «админка печатник»
> Этап 2 из `MIGRATION_PLAN.md`: движок + реестр + порт Riso + golden-тесты.
> Этап Phase 1 (v3, `ПРОМПТ_ПЕЧАТНИК_КОНСОЛИДАЦИЯ_v3.md`): web-приложение приёма заказа.

## Что это

Минимальный каркас целевой архитектуры из `TARGET_ARCHITECTURE.md` /
`CALCULATOR_ARCHITECTURE.md`:

```
metadata (CalculatorSpec) → input_schema (FieldSpec) → validation → compute() → CalcResult → UI
```

- **Движок** (`src/printcalc/engine/`) — контракт, валидация по схеме, реестр.
  Не знает ни про UI, ни про хранение.
- **Калькуляторы** (`src/printcalc/calculators/`) — pure-функции + инъекция
  конфига. Риск мутабельных глобалов legacy устранён: `RisoConfig` —
  frozen dataclass, все настройки передаются явно.
- **Golden-тесты** — закрепляют паритет с legacy-EXE на независимых значениях.

## Структура

```
src/printcalc/engine/       CALC-контракт: spec, validate, result, errors, registry
src/printcalc/calculators/riso/   порт Riso: config (канон), spec, compute
src/printcalc_web/          Phase 1 web: FastAPI (api, views, store, db, parser, export, calculators)
templates/, static/         главный экран Р5б, заказы (Р2), админка прайса (Р5а)
tests/                      golden + validate + registry + store + API (45 тестов)
```

## Phase 1 web (v3): приём заказа

Локальный запуск (телефон/разработка):

```bash
PRINTCALC_WEB_DB=data/printcalc.db python3 -m printcalc_web
# http://127.0.0.1:8300 — главный экран Р5б
```

### Продакшн-развёртывание (сервер whimco, ADR-022)

- **URL:** `http://185.233.184.192:8300` (0.0.0.0, systemd-юнит `printcalc-web.service`)
- **venv:** `/opt/printcalc-venv` (fastapi/uvicorn/jinja2)
- **БД:** `/opt/printcalc/data/printcalc.db` (env `PRINTCALC_WEB_DB`)
- **Код:** `/opt/freebuff/projects_17/админка печатник/printcalc` (обновление:
  `git fetch origin && git checkout -f -B master origin/master && systemctl restart printcalc-web`)
- **Логи:** `journalctl -u printcalc-web.service -f`

Реализовано:
- **Прайс-каталог (Р5/Р5а)** — CRUD, поиск «похожих» при добавлении, синонимы,
  массовый импорт «Название — цена» (создаёт unverified=1), CSV-экспорт.
- **Главный экран (Р5б)** — поиск по каталогу/синонимам, ручная позиция,
  калькулятор Riso (серверный расчёт через движок), итог, способ оплаты
  (настраиваемый список), сохранение заказа.
- **Заказы (Р2)** — статусы «новый → в работе → готов → выдан», фильтр,
  `export.txt` для ручного переноса в WF (Р1), отчёт «мимо каталога».
- **Parser (Р6, ступень 1)** — детерминированный словарь «фраза → позиция»;
  неизвестные токены возвращаются в `unknown` (без fallback-гадания, ANTI-6b).

Границы доверия: клиент присылает только выбор (id позиции, параметры
калькулятора); все цены каталога и все расчёты — серверные.

## Паритет с legacy (riso_calc.py)

Источник: «Общий калькулятор печати/riso_calc.py» (серверная изолированная
копия, `/opt/freebuff/projects_17/админка печатник/worktree/…`).

1. **Формулы 1:1** — порядок арифметических операций сохранён
   (riso_calc.py:700–724): `price = (base_rate*qty + (master+extras)*(1+markup)) / (1 - tax)`;
   наценка применяется только к мастерам+допам; ink умножается на стороны,
   бумага — нет; мастера = оригиналы × стороны.
2. **float, не Decimal** — сознательно: golden-тесты сравнивают float-значения
   legacy. Переезд на Decimal — отдельное ADR (Phase 3+).
3. **«Одна ошибка за раз»** — первое нарушение прерывает расчёт
   (CalcInputError), тексты ошибок legacy сохранены дословно.
4. **Динамические опции** — формат/бумага/цветность в legacy заполнялись из
   PRICES/PAPER/INK, поэтому в схеме они STRING, а членство проверяет compute.
   Динамические ENUM-опции — расширение движка Phase 3.
5. **Минимальный заказ** — применяется до поиска диапазона тиража (паритет
   странного, но зафиксированного поведения: qty 499 → расчёт по 500).

## Запуск

```bash
cd projects_17/админка печатник/printcalc
python3 -m pytest -q                                    # 45 passed
python3 -m mypy src/ tests/
```

Зависимости: web-слой — fastapi/uvicorn/jinja2/pydantic (extra `[web]` в
pyproject); тесты — pytest/mypy. Примечание среды: starlette 0.27 несовместим
с httpx 0.28 (TestClient сломан), поэтому интеграционные тесты используют
собственный минимальный ASGI-клиент (`tests/asgi_client.py`).

## Golden-значения (проверены независимой деривацией)

| Кейс | Входы | cost | price_no_tax | price | net_profit |
|------|-------|------|--------------|-------|------------|
| 1 | A4/1000/1/простая/ч/б/Офсетная80/markup 25 | 105.00 | 456.25 | 485.37234042553195 | 351.25 |
| 2 | A5/100→500/2/дуплекс/1 краска/Мел.гл.150/markup 25/все допы | 1980.00 | 2625.00 | 2792.553191489362 | 645.00 |
| 3 | A6/10000/1/простая/2 краски/Газетная/markup 0 | 780.00 | 1005.00 | 1069.148936170213 | 225.00 |
| 4 | A4/499→500 (минзаказ) | 55.00 | 256.25 | 272.60638297872345 | 201.25 |
| 5 | A4/500, кастомный конфиг (мастер 10, минзаказ 100) | 60.00 | 262.50 | 279.25531914893617 | 202.50 |

## Что дальше (не входит в этот этап)

- Phase 3: FastAPI-обёртка движка, Registry Service, schema-driven web-UI.
- Порты остальных калькуляторов по порядку миграции:
  Tablichki → Wide → Digital → Sign → Costing → CNC → Design.
- Загрузка `riso_calc_config.json` legacy в `RisoConfig` (формат совместим
  по ключам — см. WF-аудит, паритет прайс-модели).
