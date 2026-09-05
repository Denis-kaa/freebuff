# Паспорт проекта TeenFreelance

> **Canonical (платформа):** этот паспорт — единый вход в проект-контейнер (PROJECT_RULES.md §2).
> Аудит безопасности ведётся в `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md` + `docs_10/RECOMMENDATIONS.md` (REC-001..021) — канон там, кросс-ссылки здесь (правило одностороннего дублирования, PROJECT_RULES.md §3.2).

| Поле | Значение |
|---|---|
| **Название** | TeenFreelance — фриланс-платформа для подростков |
| **Версия** | 1.0.0 (MVP, унаследована) |
| **Назначение** | Биржа микро-заказов для подростков: заказчик публикует заказ, исполнитель откликается оффером; чат, портфолио, сообщество, баланс (RUB + tf_coins) |
| **Стек** | Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL 16 + JWT (python-jose) + bcrypt. Frontend: React (CRA) + axios. Инфра: docker-compose (dev) / нативный systemd + nginx (prod whimco) |
| **Статус** | 🔴 Deployed-BUT-insecure: живой инстанс на whimco работает с P0-уязвимостями (REC-001/002 — placeholder SECRET_KEY, plain HTTP) |
| **Deployment (prod)** | whimco 185.233.184.192 — backend :8020 (systemd `teenfreelance-backend`), frontend :8021 (nginx static), PG 16 локальный (db `teenfreelance`, user `teenapp`) |
| **Роли** | customer / executor (единая сущность User, роль выбирается при регистрации) |
| **Аудит** | Единый клиентский отчёт: [AUDIT_REPORT.md](AUDIT_REPORT.md); подробный канонический аудит — `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md`; remediation — `docs_10/RECOMMENDATIONS.md` REC-001..024; карантин-приоритет: P0 ×7 |
| **Зависимости от платформы** | НЕТ (код автономен; платформа выступает только как аудитор/деплойер) |

## Архитектура (как есть)

```
React CRA (:8021 nginx static, SPA fallback)
  └─ REACT_APP_API_URL=http://185.233.184.192:8020
      └─ FastAPI uvicorn :8020 (systemd)
          ├─ /api/v1/{auth,users,orders,offers,messages,notes,community,portfolio,files,categories,health}
          ├─ /api/v1/ws (websocket_manager, in-memory)
          └─ PostgreSQL 16 (localhost:5432, db teenfreelance)
```

## Известные критичные проблемы (top-4, все OPEN)

1. **A1/I2** — placeholder `SECRET_KEY` в коде + прод без override → подделка токенов любого аккаунта (REC-001, REC-018).
2. **B1** — `GET /offers/*` без auth: ставки всех подростков читаются перебором ID (REC-003).
3. **B3/F4** — файлы: DELETE любого файла любым аутентифицированным; GET вообще без токена; ownership-модели нет (REC-004, REC-021).
4. **I1** — docker-compose публикует Postgres `5433:5432` с `postgres:postgres` (REC-006).

## Индекс документов проекта

| Документ | Назначение |
|---|---|
| [STEPS.md](STEPS.md) | Хронология сессий 2026-09-04…05: деплой + аудит, «почему» по каждому шагу |
| [decisions/DECISIONS.md](decisions/DECISIONS.md) | Реестр ADR (ADR-001 деплой-топология, ADR-002 security-ремедиация) |
| [LESSONS.md](LESSONS.md) | Project-local уроки (CON/CAN/ANTI/PB) |
| [ROADMAP.md](ROADMAP.md) | Дорожная карта ремедиации, привязанная к REC-ID |
| [RUNNABLE.md](RUNNABLE.md) / [CHECKLIST.md](CHECKLIST.md) | Готовность и проверка запуска |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | Единый client-ready отчёт по проходам 1–7: critical/high, medium/low, minors compliance, roadmap S/M/L, сильные стороны |
| [TRAJECTORY_ROADMAP.md](TRAJECTORY_ROADMAP.md) | Роадмап плейсхолдеров концепта «Траектория» (задача.md): инвентаризация 7 слотов, промты IMG-01..07, этапы (Stage 1 React-миграции ✅) |
| [trajectory/](trajectory/README.md) | React-приложение «Траектория» (Stage 1: канонические типы + FSD-скелет, `tsc` strict clean) |
| [задача.md](задача.md) | Концепт «Траектория»: HTML-прототип (с плейсхолдерами IMG-01..07 и реестром промтов Data.imagePrompts) + React-архитектура + вижн платформы |
| README.md | Быстрый старт |

## Кросс-ссылки (платформенный канон)

- Аудит: `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md` (36 находок + §11 owner-check таблица 62 эндпоинтов)
- Реестр фиксов: `docs_10/RECOMMENDATIONS.md` (REC-001..023; 7×P0, 14×P1, 2×P2)
- Урок платформы: `core_02/LESSONS.md` CON-68 (канон-пара AUDIT + RECOMMENDATIONS)
- Долг платформы по этому проекту: TRACK-002 в `docs_10/core/ARCHITECTURAL_DEBT.md` не относится к коду проекта (артефакты PM-OS), указан для полноты
