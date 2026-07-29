---
category: freelancing
complexity: средняя
description: Разработка генератора отчётов из данных (CSV, JSON, БД) в форматированные документы: PDF, HTML, Excel, DOCX.
tags:
  - report
  - pdf
  - excel
  - visualization
---

# Сценарий: Генератор отчётов  \n

## Описание задачи

Разработка генератора форматированных отчётов из сырых данных.
Поддерживает вход: CSV, JSON, SQLite/PostgreSQL. Выход: PDF, HTML, Excel, DOCX.
Включает визуализацию данных (графики, таблицы) и авто-рассылку.

## Технические требования

```yaml
стек:
  python: 3.11+
  библиотеки:
    - pandas  # обработка данных
    - matplotlib/plotly  # графики
    - jinja2  # HTML шаблоны
    - openpyxl  # Excel
    - weasyprint/pdfkit  # PDF из HTML
    - python-docx  # Word документы
  вход: csv | json | sqlite | postgresql
  выход: pdf | html | xlsx | docx
```

## Промт для freebuff

```
Разработай генератор отчётов из {источник_данных***REMOVED***.

Требования:
1. Язык: Python 3.11+
2. Входные данные: {формат_данных***REMOVED*** (CSV/JSON/SQLite/PostgreSQL)
3. Функционал:
   - Загрузка данных из {источник***REMOVED***
   - Обработка: фильтрация, агрегация, сортировка
   - Визуализация: {тип_графиков***REMOVED*** (столбчатые/круговые/линейные/тепловые карты)
   - Шаблоны: Jinja2 для настройки внешнего вида
   - Вывод в {выходной_формат***REMOVED*** (PDF/HTML/Excel/DOCX)
4. Периодичность: разовый / ежедневно / еженедельно / ежемесячно
5. Авто-рассылка: отправка по email (smtplib), в Telegram, в Slack (опционально)
6. Логирование, обработка ошибок

Структура проекта:
```
report_generator/
├── main.py               # точка входа (CLI + schedule)
├── loader.py             # загрузка данных
├── processor.py          # обработка и агрегация
├── charts.py             # визуализация (matplotlib/plotly)
├── templates/            # Jinja2 шаблоны
│   ├── report.html       # шаблон HTML
│   └── style.css         # стили
├── exporters/
│   ├── __init__.py
│   ├── pdf_exporter.py   # экспорт в PDF
│   ├── excel_exporter.py # экспорт в Excel
│   └── html_exporter.py  # экспорт в HTML
├── notifier.py           # отправка (email/TG/Slack)
├── models.py             # pydantic модели
├── config.py             # настройки
└── requirements.txt
```

Напиши полный код со всеми модулями и примерами шаблонов.
```

## Варианты

| Тип отчёта | Источник | Выход | Сложность |
|-----------|---------|-------|-----------|
| Финансовый | CSV/Excel выписка | PDF с графиками | средняя |
| Статистика | SQLite/Postgres | HTML дашборд | средняя |
| Ежедневный дайджест | API / JSON | HTML + Telegram | низкая |
| Акты сверки | SQLite | Excel (.xlsx) | низкая |
| SEO отчёт | JSON | PDF + email | средняя |
| Инвойс | JSON + шаблон | PDF / DOCX | низкая |
