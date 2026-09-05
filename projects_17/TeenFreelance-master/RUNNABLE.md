# RUNNABLE — TeenFreelance

> Стандарт готовности: `docs_10/core/PROJECT_REQUIREMENTS.md`. Проверено на whimco 2026-09-04 (ADR-001).

## Способы запуска

### A. Прод-топология whimco (каноническая, работает)

| Компонент | Как запускается | Проверка |
|---|---|---|
| PostgreSQL 16 | системный сервис сервера, db `teenfreelance`, user `teenapp` | `psql -h 127.0.0.1 -U teenapp -d teenfreelance -c 'select 1'` |
| Backend FastAPI | `systemctl start teenfreelance-backend` (venv uvicorn, :8020) | `curl -s http://127.0.0.1:8020/health` |
| Frontend | nginx static `/opt/teenfreelance/frontend/build`, :8021 | `curl -sI http://127.0.0.1:8021` → 200 |

### B. Локальная разработка (docker-compose проекта)

```bash
docker compose up --build   # backend :8000, frontend :3000, postgres :5433*
```

⚠️ compose проекта публикует Postgres `5433:5432` с `postgres:postgres` — **не запускать на публичном сервере** (REC-006/P0; зафиксировано в аудите I1).

### C. Только backend локально (без Docker)

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export POSTGRES_SERVER=127.0.0.1 POSTGRES_PORT=5432 POSTGRES_DB=teenfreelance POSTGRES_USER=… POSTGRES_PASSWORD=…
export BACKEND_CORS_ORIGINS='["http://localhost:3000"]'   # JSON-массив! (PB-01)
alembic upgrade head
python backend/fix_enum_cases.py          # ОБЯЗАТЕЛЬНО после миграций (CON-01)
uvicorn app.main:app --port 8000
```

## Порядок первого запуска (check-порядок)

1. Postgres доступен, БД/юзер созданы.
2. `alembic upgrade head` — 9 миграций.
3. `python fix_enum_cases.py` — нормализация enum-меток (CON-01: иначе регистрация падает).
4. Backend стартует с корректным `.env` (list-поля — JSON, PB-01).
5. `/health` → 200; регистрация → логин → `/users/me` → 200.
6. Frontend build с `REACT_APP_API_URL` на адрес backend; nginx SPA-fallback.

## Известные ограничения

- `SECRET_KEY` в коде — placeholder (REC-001/P0): прод **обязан** задавать его в `.env` до приёма трафика.
- Деплой-скриптов нет: повторение прод-топологии — по STEPS.md Сессия 1 (ручные шаги).
- `fix_enum_cases.py` идёт в комплекте проекта и должен запускаться после каждой свежей миграционной базы.
