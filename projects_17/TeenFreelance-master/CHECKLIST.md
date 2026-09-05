# CHECKLIST — TeenFreelance

> Чек-лист проверки запуска/релиза (PROJECT_RULES.md §2, PROJECT_REQUIREMENTS.md). Отмечено по состоянию whimco 2026-09-04…05.

## Инфраструктура

- [x] PostgreSQL доступен, БД `teenfreelance` + user `teenapp` созданы
- [x] Backend unit `teenfreelance-backend` active + enabled + Restart=on-failure
- [x] nginx static :8021 + SPA-fallback, права root:root 755/644 (PB-02)
- [ ] SECRET_KEY задан в `.env` (перенос из кода) — 🔴 блокер релиза, REC-001/018
- [ ] TLS + security-заголовки — 🔴 REC-002 (нужен домен)

## Backend

- [x] `.env`: POSTGRES_* + BACKEND_CORS_ORIGINS (JSON-массив, PB-01)
- [x] `alembic upgrade head` — 9 миграций применились
- [x] `fix_enum_cases.py` выполнен (CON-01 — иначе регистрация падает)
- [x] `/health`, `/api/v1/categories` → 200
- [x] Регистрация → логин → `/users/me` → 200
- [x] CORS preflight с фронтенд-origin → 200
- [ ] Rate-limit на /login /register — REC-008
- [ ] Auth на GET offers/files/portfolio — REC-003/021

## Frontend

- [x] Production build с `REACT_APP_API_URL=http://185.233.184.192:8020`
- [x] `GET /` → 200, SPA-fallback на deep-links
- [x] WS-handshake → 101
- [ ] Переезд на https origin после REC-002

## Безопасность (аудит 2026-09-04 + deep-dives, 36 находок; реестр REC-001..023)

- [ ] Волна 1 (P0 ×7) — ADR-002 — 🔴 блокер эксплуатации
- [ ] Волна 2 (P1 ×15) — ADR-002 (ревизия 2026-09-05: +модерация, +antiflood, +PII field-hygiene)
- [ ] Волна 3 (P2 ×2) — ADR-002

## Документация проекта

- [x] MANIFEST.md (паспорт)
- [x] STEPS.md (деплой + аудит, с «почему»)
- [x] decisions/DECISIONS.md + ADR-001, ADR-002
- [x] LESSONS.md (project-local CON/PB/ANTI)
- [x] ROADMAP.md (привязан к REC-ID)
- [x] RUNNABLE.md + этот чек-лист
- [x] Зарегистрирован в docs_10/projects_meta/PROJECTS_OVERVIEW.md
