# ADR-001: Модель авторизации и tenant-isolation для `kwork_site`

> **Статус:** 🟢 **ACCEPTED**
> **Дата:** 2026-08-17
> **Категория:** Архитектура / Безопасность
> **Связанные блокеры:** **нет** — auth не зависит от Excel-pipeline (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §1.2), поэтому ADR может быть принят ДО ответов клиента.
> **Зависимости:** `SPEC.md` §6.2 (locked key principles) + §3.3 NFR-007/010/011 (invariants) + §2.1 FR-003/FR-006 (functional anchors) + `01_PLAN_BREAKDOWN.md` §5.1 (row-level strategy).
> **Канон-формат:** **Context / Options / Decision / Rationale / Consequences** ([шаблон в `DECISIONS.md`***REMOVED***(DECISIONS.md#2-шаблон-adr-canonical-format)).

---

## 1. Контекст

Проект — **B2B-портал для транспортной компании «КТК ТРАСТ»** с личным кабинетом, дислокацией контейнеров, онлайн-заявкой и интерактивной картой маршрутов. Несколько компаний-грузополучателей работают параллельно через один сервис; каждая компания должна видеть **только свои контейнеры и заявки**.

Ключевые ограничения (`01_PLAN_BREAKDOWN.md` §5.1 + [`SPEC.md`***REMOVED***(../SPEC.md) §6.2):

- **Изоляция пространств и данных (Workspace OS принцип #1):** клиент видит **только свои контейнеры**.
- **Бюджет** 30 000 ₽ (Этап 1 = 15 000 ₽, Этап 2 = 15 000 ₽) — не позволяет сложных абстракций (database-per-tenant, schema-per-tenant).
- **Стек:** Python + SQLite (WAL) + Jinja2 + Cookie-сессии.

Без формального решения auth + isolation **любая ошибка в одном SQL-запросе = утечка данных между компаниями**. Это инвариант, который должен быть **обязательно покрыт автотестами** (NFR-010).

---

## 2. Рассмотренные варианты

### Вариант A: Row-level tenant isolation через SQL `WHERE company_id = ?`

Один SQLite-файл на всё приложение; каждая таблица имеет FK `company_id`; каждый запрос проходит через **обёртку-repository**, читающую `company_id` из текущей сессии пользователя и автоматически добавляющую `WHERE company_id = ?` ко всем запросам.

- **Плюсы:**
  - Минимальная стоимость для 30 000 ₽ (нет инфра-сложностей).
  - Простая миграция (один файл `/data/ktv_trust.db`).
  - Тестируется: легко mock-ить сессию и убедиться, что запрос с чужим `company_id` возвращает 0 строк.
  - Покрывает B2B-MVP-нагрузку (~100 клиентских компаний × 1000 контейнеров = 100k строк) в SQLite WAL.
- **Минусы:**
  - **Любой** обходной путь (raw SQL без обёртки) = утечка данных. Требует discipline + lint-правил + code-review.
  - С масштабированием выше ~1M строк может потребоваться партиционирование / sharding.
- **Цена:** низкая (один .db файл, один repo-layer).

### Вариант B: Database-per-tenant (отдельный SQLite-файл на компанию)

Каждая компания-клиент имеет свой файл `/data/ktv_trust_<company_id>.db`; маршрутизация запросов на нужный файл через middleware.

- **Плюсы:**
  - Полная физическая изоляция (нет риска SQL-ошибки).
  - Теоретически проще для бэкапов (один файл = один клиент).
- **Минусы:**
  - **Невозможно** сделать кросс-тенант запросы (для админ-операций КТК ТРАСТ — например, глобальный список заявок).
  - Миграции — N файлов одновременно (overhead на deploy).
  - Connection management (N соединений) — боттлнек Python-asyncio.
  - Ad-hoc reporting для КТК ТРАСТ (глобальная статистика) усложняется.
- **Цена:** средняя (сложнее deploy, но без инфра-расходов).

### Вариант C: Schema-per-tenant (SQLite ATTACH DATABASE)

Одна СУБД-инстанция, но каждая компания получает свою SQLite-схему (`main` для КТК ТРАСТ + `tenant_<company_id>` для каждого клиента). Все запросы автоматически переключают `search_path` (эквивалент PostgreSQL).

- **Плюсы:**
  - Физически один файл, но логически изолированы схемы.
  - Удобно для бэкапа (всё в одном файле).
  - Поддержка глобальных операций — есть (cross-schema JOIN возможен).
- **Минусы:**
  - SQLite имеет ограниченную поддержку `ATTACH` — не равноценна PostgreSQL `SCHEMA`.
  - Миграции — `N+1` схем для обновления (overhead).
  - Tooling / debugging — сложнее (нужно знать, в какой схеме ищем).
- **Цена:** высокая (непропорционально для 30 000 ₽).

### Вариант D: JWT / OAuth claims с role-based access (out-of-budget)

JWT-токены с role-claims (`{ role: "client", tenant_id: 42, … ***REMOVED***`); каждый API-вызов авторизует на основе claims.

- **Плюсы:**
  - Stateless (нет server-side session storage).
  - Легко масштабируется (multi-instance без shared session store).
- **Минусы:**
  - **Не входит** в 30 000 ₽ (OAuth-сервер = дополнительная инфра-стоимость).
  - Избыточно для MVP (нагрузка оправдывает только session-based).
  - Cookie+session проще для тестирования.
- **Цена:** ❌ out-of-budget per [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.2.

---

## 3. Решение

**Принят Вариант A**: **Row-level tenant isolation через SQL `WHERE company_id = ?`** — единая SQLite-БД, обёрнутый repository layer, принудительное инжектирование `company_id` из cookie-session в каждый query.

Аутентификация — Cookie-based sessions + bcrypt-хэширование паролей (per [`SPEC.md`***REMOVED***(../SPEC.md) §5.1).

---

## 4. Обоснование (Rationale)

### 4.1 Соответствие принципам [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1

Per PLAN_BREAKDOWN §5.1, **tenant isolation на уровне SQL** (= Вариант A) выбран явно: «Database-per-tenant / schema-per-tenant = overkill; row-level фильтрация достаточна».

### 4.2 Соответствие бюджету

Вариант A = 1 SQLite-файл + 1 repository-обёртка = **минимум кода и инфры**. Варианты B/C требуют дополнительного connection management / миграций; Вариант D — out-of-budget.

### 4.3 Тестируемость

Обёрнутый repository легко mock-ить: тест с подменой cookie-session → проверка, что **запрос возвращает только строки своего `company_id`**. Это — NFR-010 (обязательные tenant-isolation-тесты, минимум 5 unit-тестов per [`STEPS.md`***REMOVED***(../STEPS.md) §1.2).

### 4.4 Coverage на B2B-MVP

Нагрузка MVP (по [`01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §3): Company × Container = 100 × 1000 = **100k строк**. SQLite WAL уверенно покрывает это; индексирование по `company_id` даёт sub-100ms query time.

### 4.5 Эвакуация к другому варианту (если потребуется)

Если в будущем (>100k строк или ЮР-требования к физической изоляции) Вариант A станет недостаточным — **миграция** на Вариант B (database-per-tenant) возможна через **federated migration** (`decisions/ADR-NNN_migrate_to_db_per_tenant.md`) без потери данных.

---

## 5. Последствия (Consequences)

### 5.1 Положительные

- ✅ Минимальная стоимость (укладывается в 30 000 ₽ — нет инфры OAuth/sticky-session/etc).
- ✅ Простая миграция (один файл, один ALTER TABLE).
- ✅ Тестируемость (mock-session, 5+N автотестов на изоляцию).
- ✅ Покрывает B2B-MVP нагрузку.
- ✅ Прямой ad-hoc reporting для КТК ТРАСТ (admin-операции просты).
- ✅ Совместимо с SQLite WAL per NFR-018.

### 5.2 Отрицательные / риски

- ❌ **Каждый** SQL-запрос **обязан** идти через обёртку. Прямой запрос = утечка данных.
- ❌ Нужна **discipline** в code-review: любой SQL-review должно проверить наличие `company_id = ?`.
- ❌ Lint-правило желательно: «SQL без `company_id` → fail review» (можно настроить в `ruff`/`mypy`).
- ❌ Scalability ceiling ~1M строк; выше — потребуется sharding.

### 5.3 Требования к реализации (в коде)

1. SQL DDL включает `company_id` FK в каждой "тенантной" таблице (per [`SPEC.md`***REMOVED***(../SPEC.md) §4: User / Container / Dislocation / Order / Route).
2. **Repository layer** (`app/repository.py` или `app/database/repository.py`) предоставляет:
   - методы, принимающие `current_company_id` как **обязательный** параметр;
   - внутри — автоматическое добавление `WHERE company_id = ?` ко всем query;
   - запрет raw-SQL через lint/code-review (raw SQL — только через repository).
3. **Middleware** (`app/auth/middleware.py`):
   - читает cookie + bcrypt-проверка;
   - устанавливает `request.state.current_user` + `current_company_id`;
   - если `current_company_id is None` — 403 (для не-аутентифицированных запросов).
4. INV-1 (per [`SPEC.md`***REMOVED***(../SPEC.md) §4.9): у каждого User либо `company_id IS NOT NULL` (`role='client'`), либо `NULL` (`role='admin'`).
5. FR-003 (per [`SPEC.md`***REMOVED***(../SPEC.md) §2.1 A) — каждый query к Container/Dislocation/Order фильтрует по `company_id` (must).

### 5.4 Требования к тестированию (NFR-010)

Минимум **5 обязательных автотестов** (per [`STEPS.md`***REMOVED***(../STEPS.md) §1.2 + [`SPEC.md`***REMOVED***(../SPEC.md) §8 AC-009):

| Test | Setup | Assertion |
|---|---|---|
| `test_user_A_sees_own_containers` | 2 companies, 5 containers each; session = company A | `GET /dashboard` возвращает 5 строк компании A, не 10 |
| `test_user_A_does_not_see_B_containers` | (тот же) | 0 строк компании B в ответе для company A |
| `test_admin_sees_all` | session = admin (role='admin', company_id=NULL) | все контейнеры обеих компаний |
| `test_unauthenticated_redirects_to_login` | без cookie | 302 → `/login` |
| `test_query_with_wrong_company_id_returns_nothing` | прямой SQL с чужим company_id | возвращает 0 строк |

**Coverage target:** repository-функции **≥ 80 %** lines (per NFR-011 per [`SPEC.md`***REMOVED***(../SPEC.md) §3.3).

### 5.5 ADR supersedes / related *(supersedes — нет для первого ADR проекта)*

| ADR | Relationship |
|---|---|
| [ADR-001***REMOVED***(ADR-001_auth_tenant_isolation.md) | **этот ADR** *(нет — первый ADR проекта)* |
| [ADR-002***REMOVED***(ADR-002_python_vs_php.md) | ⚪ DRAFT — Excel-движок (Python vs PHP); черновик структуры готов, ждёт Q1 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md); независим от ADR-001, может быть принят параллельно. |
| [ADR-003***REMOVED***(ADR-003_excel_schema_v1.md) | ⚪ DRAFT — Excel schema; черновик структуры готов, ждёт Q2 в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(../CLIENT_QUESTIONS_v1.md); **downstream-зависимость**: влияет на схему БД (финальные колонки Container/Dislocation), поэтому после принятия ADR-003 обновить SQL DDL в [`SPEC.md`***REMOVED***(../SPEC.md) §4. |

---

## Cross-links

### Проектные документы

- [`../MANIFEST.md`***REMOVED***(../MANIFEST.md) — Scope Rules (аддитивность, конфиденциальность)
- [`../SPEC.md`***REMOVED***(../SPEC.md) §2.1 A (FR-001..005 — auth), §2.3 (Дашборд, FR-006), §3.3 (NFR-007/010/011 — tenant-isolation invariants), §6.2 (locked patterns), §8 AC-009 (tenant-isolation test), §4 (SQL DDL)
- [`../STEPS.md`***REMOVED***(../STEPS.md) §1.2 — реализация auth (bcrypt, cookie, middleware)
- [`../01_PLAN_BREAKDOWN.md`***REMOVED***(../01_PLAN_BREAKDOWN.md) §5.1 (row-level strategy lock-in) + §5.2 (out-of-scope)

### Канонические источники платформы

- [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../../docs_10/core/PROJECT_RULES.md) §3.1 (уроки в проекте) + §7 (миграция ADR)
- [`docs_10/core/CODE_QUALITY_STANDARD.md`***REMOVED***(../../../docs_10/core/CODE_QUALITY_STANDARD.md) — обязательный регламент качества кода

### Соседние ADR

- [`DECISIONS.md`***REMOVED***(DECISIONS.md) — индекс project-local ADR
- [`ADR-002_python_vs_php.md`***REMOVED***(ADR-002_python_vs_php.md) — ⚪ DRAFT (зависит от Q1)
- [`ADR-003_excel_schema_v1.md`***REMOVED***(ADR-003_excel_schema_v1.md) — ⚪ DRAFT (зависит от Q2)

### Стилевые образцы

- `docs_10/engineering-memory/decisions/ADR-NNN_*.md` — platform-wide ADR для эталона формата
- Стандарт MADR/ADR (https://adr.github.io/madr/) — соблюдён Context/Options/Decision/Rationale/Consequences

---

*ADR принят: 2026-08-17 · Канон: Context/Options/Decision/Rationale/Consequences · Опоры: SPEC §6.2 + NFR-007/010/011 + FR-003/006 + 01_PLAN_BREAKDOWN §5.1 · Автор: Buffy (Workspace OS / Freebuff)*
