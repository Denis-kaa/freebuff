---
category: freelancing
complexity: средняя
description: Разработка REST API сервера для интеграции с внешними сервисами. CRM, платежи, дашборды, вебхуки.
tags:
  - api
  - fastapi
  - backend
---

# Сценарий: API сервер / Интеграция  

## Описание задачи

Разработка REST API сервера для интеграции с внешними сервисами.
Типовые задачи: CRM интеграция, платёжный шлюз, дашборд данных, вебхуки.

## Технические требования

```yaml
стек:
  python: 3.11+
  фреймворк: fastapi
  библиотеки:
    - pydantic  # валидация
    - sqlalchemy/aiosqlite  # БД
    - httpx/aiohttp  # внешние API
    - celery/arq  # фоновые задачи (опционально)
  бд: postgresql | sqlite
  документация: openapi (авто, через FastAPI)
```

## Промт для freebuff

```
Разработай API сервер для {описание_сервиса***REMOVED***.

Требования:
1. Фреймворк: FastAPI
2. Эндпоинты:
   GET    /api/v1/{resource***REMOVED***      — список
   GET    /api/v1/{resource***REMOVED***/:id   — детали
   POST   /api/v1/{resource***REMOVED***      — создание
   PUT    /api/v1/{resource***REMOVED***/:id   — обновление
   DELETE /api/v1/{resource***REMOVED***/:id   — удаление
   {доп_эндпоинты***REMOVED***
3. Модели данных (Pydantic + SQLAlchemy)
4. Валидация входящих данных
5. Обработка ошибок с HTTP статусами
6. Логирование запросов

Структура проекта:
```
api/
├── main.py           # точка входа
├── app/
│   ├── __init__.py
│   ├── models.py     # SQLAlchemy модели
│   ├── schemas.py    # Pydantic схемы
│   ├── crud.py       # операции с БД
│   └── routers/      # эндпоинты
│       ├── __init__.py
│       └── {resource***REMOVED***.py
├── requirements.txt
└── Dockerfile (опционально)
```

Напиши полный код.
```

## Варианты

| Тип | Интеграция | Сложность |
|-----|-----------|-----------|
| CRM | Создание/обновление лидов | средняя |
| Платежи | Stripe/ЮKassa вебхуки | высокая |
| Дашборд | Статистика, графики | средняя |
| Вебхуки | Приём и обработка событий | низкая |
| Агрегатор | Сбор данных из 2+ API | средняя |
