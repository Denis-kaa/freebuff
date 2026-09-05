# LESSONS — TeenFreelance (project-local)

> Формат CON (подтверждено) / CAN (гипотеза) / ANTI (анти-паттерн) / PB (процессный баг) — как в `core_02/LESSONS.md`, но project-local (PROJECT_RULES.md §3.1). Append-only.

---

### CON-01 — Миграции создают UPPERCASE PG-enum'ы, модели используют lowercase (2026-09-04)

**Контекст:** деплой на whimco: после `alembic upgrade head` регистрация падала — `invalid input value for enum userrole: "executor"`. Миграции создали метки `EXECUTOR`, модели SQLAlchemy отдают `executor` (и наоборот для чтения). Затронуты все enum'ы: `userrole`, `orderstatus`, `paymenttype`, `offerstatus` (17 меток в 5 типах).

**Правило (подтверждено):** после `alembic upgrade head` на любом новом инстансе TeenFreelance **обязателен** прогон штатного `backend/fix_enum_cases.py` (переименовывает метки в lowercase). Это не опция, а шаг деплоя — зафиксировано в RUNNABLE.md и CHECKLIST.md.

**Связи:** ADR-001 (Consequences), STEPS.md Сессия 1 Шаг 6.3, RUNNABLE.md.

---

### PB-01 — pydantic-settings v2: list-поля в `.env` только JSON-массивом (2026-09-04)

**Контекст:** `BACKEND_CORS_ORIGINS=http://…,http://…` (CSV) в `.env` молча ломает старт backend — pydantic-settings v2 ждёт JSON: `BACKEND_CORS_ORIGINS=["http://…"]`. Симптом был неочевиден: сервис active, но health не отвечал.

**Правило:** для list-полей Settings в `.env` — только JSON-массив; CSV-формат не поддерживается. Проверять health сразу после старта unit'а, а не только `systemctl is-active`.

**Связи:** STEPS.md Сессия 1 Шаг 6.1.

---

### PB-02 — tar с экзотическими uid/gid ломает nginx static (2026-09-04)

**Контекст:** архив, созданный в Termux, сохранил владельцев 10198:1023; каталоги оказались без world-access — nginx (www-data) отдавал 500 «Permission denied» при валидной конфигурации.

**Правило:** при переносе статики на сервер — после распаковки всегда `chown -R root:root` + `chmod 755` на каталоги / `644` на файлы; диагностика через `tail /var/log/nginx/error.log`, а не только HTTP-код.

**Связи:** STEPS.md Сессия 1 Шаг 6.2.

---

### ANTI-01 — Placeholder-секреты в дефолтном конфиге кода (2026-09-05)

**Контекст:** `config.py:30` — `SECRET_KEY: str = "your-secret-key-change-in-production"`. Приложение стартует без ошибки и без `.env`-override → боевой инстанс подписывает JWT публично известным ключом. Обнаружено только аудитом, хотя деплой прошёл «зелёным».

**Анти-паттерн:** «дефолт, который выглядит как конфиг». Секрет с дефолтом = отсутствие секрета.

**Правило:** обязательные секреты — `Field(...)` без дефолта (fail-fast на старте) + валидатор против известных placeholder-значений. Канонизировать во всех проектах платформы (тиражируемо; см. REC-001).

**Связи:** ADR-002 Волна 1, `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md` §1 (A1), `docs_10/RECOMMENDATIONS.md` REC-001/018.

---

### CON-02 — Мутации защищены, чтение — нет: дыры концентрируются в GET (2026-09-05)

**Контекст:** полный owner-check sweep 62 эндпоинтов (§11 аудита): все PUT/DELETE orders/offers/notes/portfolio/community имеют явные `owner → 403` проверки, но `GET /offers/*`, `GET /files/{filename}`, `GET /portfolio/{item_id}`, `GET /posts/{post_id}/comments` работают без auth или без owner-check.

**Правило:** security-ревью нельзя ограничивать «мутирующими» методами: для платформ с приватными данными (ставки, переписка, данные подростков) **чтение** — такой же вектор утечки. Паттерн проверки: каждый маршрутизатор проходит тестом «что вернёт GET с чужим ID без токена?».

**Связи:** REC-003/021, `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md` §11.5.
