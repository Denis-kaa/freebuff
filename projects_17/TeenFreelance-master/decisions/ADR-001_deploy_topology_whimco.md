# ADR-001: Деплой-топология whimco (нативный venv + systemd + nginx)

- **Дата:** 2026-09-04
- **Статус:** ✅ Accepted
- **Контекст задачи:** STEPS.md, Сессия 1

## Context

TeenFreelance поставляется с docker-compose (backend + frontend + postgres). Целевой сервер whimco (Ubuntu 24.04, 7.8 GB RAM) **не имеет Docker**. На сервере уже живут чужие сервисы: ai-dubber (:8000), PM OS (:3001, :8010); Postgres 16 уже установлен и используется. Пользователь передал доступы (`SERVER_ACCESS_WHIMCO.md`) и попросил развернуть сайт.

## Options

| # | Вариант | Почему нет/да |
|---|---|---|
| 1 | Установить Docker на whimco и поднять compose как есть | Тяжёлое вторжение в чужую систему; compose проекта публикует Postgres наружу (`5433:5432`) с дефолтными кредами — небезопасно (аудит I1) |
| 2 | **Нативно: venv + uvicorn (systemd) + nginx static + существующий PG16** | Без новых рантайм-зависимостей; изоляция через отдельные БД/юзера/порты; systemd = автозапуск и restart |
| 3 | Локальный запуск (Termux, нативный PG18) | Не соответствует запросу «разверни на сервере» |

## Decision

Вариант 2:
- backend: `/opt/teenfreelance/backend`, venv, uvicorn на **:8020**, unit `teenfreelance-backend.service` (Restart=on-failure, enabled);
- frontend: `/opt/teenfreelance/frontend/build`, nginx static + SPA fallback на **:8021**;
- БД: существующий PG16, database `teenfreelance`, user `teenapp`, только localhost;
- `.env` backend: `POSTGRES_*`, `BACKEND_CORS_ORIGINS` (JSON-массив), **SECRET_KEY не задан** — унаследовал placeholder из кода (признано P0 позже, REC-001/018).

## Rationale

- **Additive Architecture:** чужие сервисы не затронуты; свободные порты; отдельная БД.
- **Backward Compatibility:** код проекта не переписывался под деплой — только конфиги/скрипты проекта (включая штатный `fix_enum_cases.py` против UPPERCASE-enum инцидента).
- nginx static — минимум движущихся частей для CRA-сборки; WS ходит напрямую на :8020 (фронтенд строит URL из `REACT_APP_API_URL`), проксирование не нужно.

## Consequences

- ✅ Сайт живой: `http://185.233.184.192:8021`, полный цикл регистрация→логин→WS проверен.
- ⚠️ Унаследованы P0-дыры кода: placeholder SECRET_KEY (любой может подделать токен), plain HTTP. Ремедиация — ADR-002.
- ⚠️ `fix_enum_cases.py` обязателен к прогону после `alembic upgrade head` на любом новом инстансе (миграции создают UPPERCASE-enum'ы) — зафиксировано в RUNNABLE.md/CHECKLIST.md.
- 📋 Деплой-скрипт не автоматизирован: повторный деплой = ручные шаги из STEPS.md §Сессия 1.
