---
category: freelancing
complexity: средняя
description: Разработка парсера для извлечения данных с веб-сайта. HTML, API, SPA.
tags:
  - parser
  - scraper
  - bs4
  - playwright
---

# Сценарий: Парсер сайта  

## Описание задачи

Разработка парсера для извлечения данных с веб-сайта. 
Парсер должен собирать структурированные данные и сохранять их в удобном формате (JSON, CSV, SQLite).

## Технические требования

```yaml
стек:
  python: 3.11+
  библиотеки:
    - requests/aiohttp  # HTTP запросы
    - beautifulsoup4/lxml  # HTML парсинг
    - selenium/playwright  # JavaScript (если нужен)
    - pydantic  # модели данных
  хранение: json|csv|sqlite
  вывод: файл на диске
```

## Промт для freebuff

```
Разработай парсер для сайта {URL***REMOVED***.

Требования:
1. Язык: Python 3.11+
2. Библиотеки: requests, beautifulsoup4, pydantic
3. Извлекаемые данные:
   - {поле1***REMOVED***
   - {поле2***REMOVED***
   - {поле3***REMOVED***
4. Сохранение в {формат***REMOVED*** (JSON/CSV/SQLite)
5. Обработка ошибок: таймауты, ретраи, логирование
6. User-Agent ротация
7. Асинхронный режим (опционально)

Структура проекта:
```
parser/
├── main.py          # точка входа
├── scraper.py       # логика парсинга
├── models.py        # pydantic модели
├── config.py        # настройки
└── requirements.txt
```

Напиши полный код всех файлов.
```

## Варианты

| Тип сайта | Инструмент | Сложность |
|-----------|-----------|-----------|
| Статический HTML | requests + bs4 | низкая |
| SPA (React/Vue) | playwright | средняя |
| API (JSON) | requests | низкая |
| Авторизация | requests + session | средняя |
| CAPTCHA | capsolver/2captcha | высокая |
