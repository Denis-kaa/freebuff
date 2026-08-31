# 08_BLUEPRINT_MAPPING — Blueprint vs Engineering Way

## PLATFORM WAY (по методологии платформы)

- Соблюдать границы платформы: сначала анализ, потом планирование, затем выполнение.
- Prefer editing existing files over creating new ones.
- Verify a library is already used in the project before employing it.
- Verify non-trivial changes by running the project's typecheck and relevant tests.
- Use write_todos to plan and track multi-step tasks.
- Проверять каждую зависимость перед использованием.

## ENGINEERING WAY (оптимальный путь для этой вакансии)

- Сначала live-проверить каждый источник (curl → есть ли данные в HTML, SSR или API).
- Выбрать минимальный стек: httpx + bs4 + APScheduler + aiogram + PostgreSQL (asyncpg) или SQLite.
- Не устанавливать новые сервисы, если существующая инфраструктура решает задачу.

## Сравнение

| Этап | PLATFORM WAY | ENGINEERING WAY | Вывод |
|---|---|---|---|
| Исследование источников | Через code_search/glob по проекту | Живой curl к каждому источнику | Engineering быстрее даёт ответ «парсится ли источник» |
| Concurrency | Через ToolRegistry/обёртки | Прямой `asyncio.Semaphore` | Engineering проще и надёжнее |
| Scheduler | Через ToolRegistry/обёртки | APScheduler в процессе бота | Engineering проще |
| Прокси | Через ToolRegistry/обёртки | URL-список в env + round-robin | Engineering проще |

## Итог

Blueprint помогает с contract-first адаптерами, additive-структурой, готовыми retry/dedup модулями — ускоряет ~70%. Избыточен для MVP: event bus, ModelGateway-скоринг, multi-device sync — не подключаем.
