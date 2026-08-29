# RUNNABLE — sheet_project

## Поддерживаемые платформы
- [x***REMOVED*** Termux / Android (ARM64)
- [x***REMOVED*** Linux (POSIX)

## Минимальные требования
- Python: >= 3.10
- openpyxl: >= 3.1.0
- Свободная память: >= 256 MB (файлы XLSX небольшие)

## Быстрый старт

```bash
cd projects_17/sheet_project
pip install -r ../../requirements.txt   # или: pip install openpyxl pytest
python3 main.py                          # (появится на этапе 6)
```

## Известные блокеры

- openpyxl **не вычисляет** формулы — расчётная валидация отдельным слоем (LibreOffice headless, опционально).

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|-----------|-----------|--------------|
| `OUTPUT_DIR` | папка для готовых XLSX | `output/` |
