# STEPS — TeenFreelance: деплой и security-аудит (сессии 2026-09-04…05)

> Формат: шаг → что сделано → **почему принято такое решение** (PROJECT_RULES.md §2). Хронологический журнал двух сессий: деплой на whimco и канонический аудит.

## Сессия 1 — Деплой на whimco (2026-09-04)

### Шаг 1. Обнаружение: Docker недоступен локально → цель = удалённый сервер
- Локальная среда (Termux/Android) не имеет Docker; PostgreSQL 18 + Python + Node есть нативно, но пользователь передал `SERVER_ACCESS_WHIMCO.md` с доступами к серверу.
- **Почему:** пользователь явно попросил «разверни на сервере сайт» — локальный запуск теряет смысл при наличии серверной цели.

### Шаг 2. Выбор портов 8020/8021
- На сервере заняты :8000 (ai-dubber), :3001 и :8010 (PM OS), :8020/:8021 свободны, firewall не блокирует.
- **Почему:** Additive Architecture — не трогать чужие сервисы; свободные порты минимально вторгаются в систему.

### Шаг 3. Схема деплоя: нативный venv + systemd (backend), nginx static (frontend)
- **Почему:** на сервере нет Docker; systemd даёт автозапуск/restart-on-failure; CRA-сборка — статика, nginx с SPA-fallback — самый простой боевой вариант. WebSocket фронтенд строит от `REACT_APP_API_URL`, поэтому проксирование не понадобилось — фронтенд бьёт напрямую в :8020.

### Шаг 4. БД
- Созданы PostgreSQL-база `teenfreelance` и пользователь `teenapp` на уже работающем PG 16 сервера.
- **Почему:** отдельная БД/пользователь = изоляция от других сервисов; публичную публикацию порта не делали (в отличие от docker-compose проекта — см. ADR-002).

### Шаг 5. Миграции и запуск
- `alembic upgrade head` — 9 миграций применились; `.env` создан с `BACKEND_CORS_ORIGINS` на фронтенд-origin.
- **Почему:** конфиг через env (pydantic-settings) вместо правки кода — код проекта в сессии деплоя не переписывался.

### Шаг 6. Три боевых бага по ходу деплоя
1. **CORS-формат:** pydantic-settings v2 требует JSON-массив для list-полей (не CSV) → переписали `.env`.
2. **nginx 500:** tar сохранил экзотические uid/gid (10198:1023), www-data не мог пройти по дереву → `chown -R root:root` + `chmod 755`.
3. **Регистрация падала:** enum-кейс-мисматч — миграции создали PG enum'ы UPPERCASE (`EXECUTOR`), модели используют lowercase (`executor`). Прогнали штатный `fix_enum_cases.py` из репозитория → 17 меток в 5 enum'ах нормализованы.
- **Почему именно так:** использованы собственные скрипты проекта, а не ручной SQL — фикс воспроизводим для следующих деплоев.

### Шаг 7. Верификация
- Frontend HTTP 200; `/health`, `/api/v1/categories`, `/api/v1/orders` OK; регистрация → логин → `/users/me` полный цикл; CORS-preflight 200; WS-handshake 101.
- **Результат:** сайт живой на `http://185.233.184.192:8021`; тестовый юзер `test@example.com` создан.
- **Честная оговорка:** SECRET_KEY остался placeholder'ом из кода (не был известен как критичный до аудита) — зафиксировано как REC-018/P0.

## Сессия 2 — Security-аудит (2026-09-04…05)

### Шаг 1. Послойный аудит (read-only)
- Слои: auth → resource authz → files → websocket → minors' data → infra; затем deep-dive CRUD/raw-SQL и полный endpoint-sweep (62 маршрута, 12 файлов).
- **Почему read-only:** CON-68 (платформенный канон): аудит не меняет код объекта; фиксы — отдельные заходы, каждый закрывает REC-записи с verify.

### Шаг 2. 36 находок, все с файлом:строкой и fix
- Ключевые: A1 placeholder SECRET_KEY (critical), B1 offers без auth (critical), B3 delete любых файлов (critical), I1 публичный Postgres (critical), F1 OOM DoS на upload, 7-дневный JWT без logout, отсутствие rate-limit, enum-кейс как источник prod-инцидента.
- **Почему формат «факт, а не совет»:** требование задачи пользователя + CON-68; каждый fix — конкретный дифф.

### Шаг 3. Фиксация по канону
- Аудит → `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md`; рекомендации → `docs_10/RECOMMENDATIONS.md` (REC-001..021, 7×P0); урок → CON-68 в `core_02/LESSONS.md`; реестры DOCUMENT_REGISTRY/RULES/INDEX обновлены тем же заходом (CON-63/64: register-first).
- **Почему:** Single Source of Truth — аудит-канон живёт на платформе, проект ссылается (MANIFEST.md), а не копирует.

### Шаг 4. Полный owner-check sweep (проход 2)
- Таблица 62 эндпоинтов в §11 аудита: мутации хорошо защищены; дыры в чтении (offers/files/portfolio GET без auth), у files нет ownership-модели вообще; `mark_as_read` возвращает чужое сообщение 200 (CRUD-инверсия).
- **Почему отдельный проход:** пользователь запросил явную таблицу «эндпоинт | метод | owner-check | severity | атака» с фокусом на files/notes/portfolio/community.

### Шаг 5. Каркас проекта (эта сессия)
- Созданы MANIFEST/STEPS/LESSONS/ROADMAP/RUNNABLE/CHECKLIST/decisions по PROJECT_RULES.md §2/§8.
- **Почему:** проект = контейнер контекста, а не папка с кодом; деплой- и аудит-контекст обязан жить в проекте (PROJECT_RULES.md §3.1), тиражируемое — на платформе (§3.2).

## Сессия 3 — Концепт «Траектория»: плейсхолдеры + React Stage 1 (2026-09-05)

### Шаг 1. Плейсхолдеры с промтами в `задача.md`
- Инвентаризация: 7 слотов изображений, 3 с эфемерными `image.qwenlm.ai`-ссылками (hero и аватар делили один файл), 2 пустых. Заменены на двухслойную систему (`.ph-prompt` fallback + `<img>` поверх) с реестром `Data.imagePrompts` (IMG-01..07).
- **Почему:** эфемерный хост генерации умрёт; промты = ТЗ для регенерации и живут в коде (git = бэкап). Роадмап — `TRAJECTORY_ROADMAP.md`.

### Шаг 2. React Stage 1 — типы + FSD-скелет (`trajectory/`)
- `src/types/index.ts` — канонические типы (Freelancer/Mentor/Client/Parent, Project/Task + версионность ревью, Skill Score, Proof, ParentalConsent, BudgetDistribution 51/20/20/9).
- FSD: `entities/{user,project,task,skill}` (барелы реэкспортируют канон), `features/{team-builder,review-system,skill-tree}`, `widgets/{dashboard,parent-control}`, `shared/{api,mock}`, `app/`. Реестр промтов перенесён в `shared/mock/imagePrompts.ts`.
- **Почему так:** Этапы 1–2 системного промта концепта; FSD-структура задана в самом концепте; Single Source of Truth — типы в одном модуле, слои не переопределяют формы сущностей.

### Шаг 3. Верификация strict-типизацией
- `tsc --noEmit` (TS 5.4.5, strict + noUncheckedIndexedAccess): **clean** на 12 файлах. Один реальный баг найден и исправлен (баррел `entities/user` не экспортировал `ActivityEntry`), ошибки окружения (FUSE/sdcard) обойдены typecheck-копией в ext4.
- **Почему не полный `npm install` в папке проекта:** sdcard-FUSE не даёт symlink → node_modules невозможен на `/sdcard`; методика задокументирована в `trajectory/README.md`.

## Статус

| Что | Где | Состояние |
|---|---|---|
| Деплой whimco | :8020/:8021 | 🟢 работает (но с P0-дырами) |
| Аудит | AUDIT_TEENFREELANCE_2026-09-04.md | ✅ завершён |
| REC-реестр | REC-001..021 | 🔴 21 OPEN (7×P0) |
| Фиксы кода | — | ⬜ отдельный заход (ADR-002) |
