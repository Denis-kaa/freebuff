# INTEGRATION TOPOLOGY — sheet_project (D2 генератор)

> **Роль:** decomposer. Как модули связаны между собой (поток данных и зависимости).

## Поток данных (главный путь)

```
main.py
  ├─ читает CONFIG (config/project_dashboard.py → schema.py)
  ├─ читает DATA (data/sample_data.py → models.py)
  ├─ читает STYLES (styles/theme.py)
  ├─ → generator/workbook.py
  │      ├─ generator/sheets.py        (данные в листы)
  │      ├─ generator/dashboard.py     (KPI/блоки/карточки)
  │      ├─ generator/formulas.py      (формулы)
  │      ├─ generator/validation.py    (validation/списки)
  │      └─ generator/references.py    (связи/гиперссылки)
  ├─ сохраняет XLSX → output/*.xlsx
  └─ → validator/validator.py (перечитывает XLSX, сверяет с CONFIG)
```

## Зависимости (направление вызовов)

```
config/schema.py          ← config/project_dashboard.py (использует сущности)
data/models.py            ← data/sample_data.py (инстансы моделей)
styles/theme.py           ← generator/* (применяет стили декларативно)

generator/workbook.py     ← main.py (точка входа в ядро)
  ├── generator/sheets.py        ← workbook.py (делегирует заполнение)
  ├── generator/dashboard.py     ← workbook.py
  ├── generator/formulas.py      ← workbook.py / sheets.py
  ├── generator/validation.py    ← workbook.py / sheets.py
  └── generator/references.py    ← workbook.py (после заполнения)

validator/validator.py    ← main.py (после генерации)
```

## Контракты на стыках

| Стык | Контракт |
|------|----------|
| CONFIG → GENERATOR | CONFIG — dict/dataclass (schema.py); GENERATOR читает, не знает шаблона |
| DATA → GENERATOR | DATA — нормализованные модели (models.py); источник не важен |
| STYLES → GENERATOR | STYLES — theme (словарь визуальных параметров) |
| GENERATOR → XLSX | файл output/*.xlsx (openpyxl Workbook) |
| XLSX → VALIDATOR | validator перечитывает файл и сверяет структуру с CONFIG |

## Что НЕ связано (по дизайну)

- `generator/*` **не** импортирует `config/project_dashboard.py` (не знает конкретного шаблона).
- `validator/*` **не** вызывает Excel/LibreOffice (расчёт формул — отдельный слой).
- `data/*` **не** знает источник (Python/CSV/JSON/Google Sheets/API/Bitrix24) — только интерфейс.
