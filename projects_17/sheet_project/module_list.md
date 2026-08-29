# MODULE LIST — sheet_project (D2 генератор)

> **Роль:** decomposer. Перечень модулей с ответственностью и статусом (план / реализован).

## Структура (по promt1.md Шаг 3)

```
project/
├── config/
│   ├── schema.py            # доменная модель CONFIG (сущности)
│   └── project_dashboard.py # CONFIG первого шаблона (проектный дашборд)
├── data/
│   ├── models.py            # нормализованные модели данных
│   └── sample_data.py       # пример данных первого шаблона
├── generator/
│   ├── workbook.py          # создание workbook + листов по CONFIG
│   ├── sheets.py            # заполнение листов данными
│   ├── dashboard.py         # Dashboard-блоки + KPI + карточки
│   ├── formulas.py          # формулы
│   ├── validation.py        # data validation + выпадающие списки
│   └── references.py        # связи/гиперссылки между листами
├── styles/
│   └── theme.py             # визуальная тема (цвета/шрифты/границы/ширины)
├── validator/
│   └── validator.py         # структурная проверка XLSX ↔ CONFIG
├── output/                  # готовые XLSX
└── main.py                  # точка входа (CONFIG+DATA+STYLES → XLSX → VALIDATOR)
```

## Модули

| Модуль | Ответственность | Статус |
|--------|-----------------|--------|
| `config/schema.py` | доменная модель CONFIG: Workbook, Sheet, Field/Column, DataSource, Reference, DashboardBlock, KPI, Card, LookupTable, ValidationRule, Formula, DisplayRule (Style → styles/theme.py; Relationship поглощён Reference.kind) | ⚪ план (этап 1) |
| `config/project_dashboard.py` | декларативный CONFIG проектного дашборда (листы, поля, KPI, карточка, справочники, формулы) | ⚪ план (этап 4) |
| `data/models.py` | нормализованные структуры данных (проекты, задачи, статусы, дедлайны) | ⚪ план (этап 5) |
| `data/sample_data.py` | пример данных для первого шаблона | ⚪ план (этап 5) |
| `generator/workbook.py` | ядро: создать workbook, листы в порядке CONFIG | ⚪ план (этап 6) |
| `generator/sheets.py` | заполнить листы данными по CONFIG | ⚪ план (этап 6) |
| `generator/dashboard.py` | собрать Dashboard-блоки, KPI, карточки | ⚪ план (этап 6) |
| `generator/formulas.py` | создать формулы (структурно, без расчёта) | ⚪ план (этап 6) |
| `generator/validation.py` | data validation, выпадающие списки, диапазоны | ⚪ план (этап 6) |
| `generator/references.py` | связи и гиперссылки между листами | ⚪ план (этап 6) |
| `styles/theme.py` | тема: цвета, шрифты, границы, выравнивание, ширины | ⚪ план (этап 6) |
| `validator/validator.py` | структурная проверка результата | ⚪ план (этап 7) |
| `main.py` | оркестрация: CONFIG → DATA → GENERATOR → XLSX → VALIDATOR | ⚪ план (этап 8) |

## Правила ядра (инварианты)

1. Ни один модуль `generator/*` не содержит зашитых названий листов или `if project_dashboard:`.
2. `config/` и `styles/` — чистые данные, без исполняемой бизнес-логики.
3. `data/` нормализован, источник подключается через адаптер (не в этой итерации).
4. `validator/` проверяет только структуру; расчёт формул — отдельный слой (LibreOffice).
