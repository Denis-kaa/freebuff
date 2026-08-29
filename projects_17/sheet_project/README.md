# sheet_project — конфигурируемый генератор Excel-дашбордов

Проект реализует архитектуру **D2**: структура XLSX, данные, стили и правила проверки отделены от кода генератора.

## Идея

```
CONFIG → GENERATOR → XLSX
```

Меняем CONFIG — получаем другой XLSX, не трогая ядро генератора.

## Стек

- Python 3
- openpyxl (запись + чтение XLSX)
- pytest (тесты)

## Быстрый старт

```bash
cd projects_17/sheet_project
python3 -c "import openpyxl; print(openpyxl.__version__)"  # 3.1.5
```

_(точка входа `main.py` появится на этапе 6)_

## Документы

- `STEPS.md` — план выполнения простыми словами
- `promt1.md` — полное ТЗ
- `decisions/` — проектные решения (стек, toolchain)
- `adr/` — архитектурные ADR (роль architect)
