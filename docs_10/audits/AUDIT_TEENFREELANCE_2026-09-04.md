# AUDIT: TeenFreelance — Security & Architecture Audit (2026-09-04)

> **Статус:** ACTIVE · **Дата:** 2026-09-04 · **Аудитор:** Buffy (Freebuff)
> **Объект:** `projects_17/TeenFreelance-master` (FastAPI backend + React CRA frontend + PostgreSQL + docker-compose)
> **Контекст:** платформа для подростков 14–18 лет (freelance: заказы, отклики, баланс `balance`/`tf_coins`, роли executor/customer)
> **Метод:** послойный аудит auth → resource authorization → files → WebSocket → minors' data → infrastructure; plus deep-dive CRUD/raw-SQL pass
> **Формат:** каждый факт = файл:строка + фрагмент + severity + конкретный fix

---

## Executive summary

| Severity | Count | Ключевые |
|----------|-------|----------|
| **CRITICAL** | 4 | AUTH-01, B1, I1, I2 |
| **HIGH** | 8 | AUTH-02/03/04, B2/B3/B4, F1, M1 |
| **MEDIUM** | 9 | AUTH-05/08, B5, F2/F3, W1/W2, M2/M3, I3/I4 |
| **LOW/INFO** | 6 | AUTH-06/07, B6, F4, M4, I5 |

Top-priority: **AUTH-01 + I2** (аккаунт-тейкover на развернутом whimco-инстансе прямо сейчас), затем **B1/B2** (неаутентифицированное чтение данных подростков), затем **B3/F1** (саботаж файлов + OOM DoS), затем **I1** (публичный Postgres с дефолтным паролем).

---

## 1. Auth layer

### AUTH-01 — CRITICAL: hardcoded placeholder SECRET_KEY (token forgery)
- **Файл:** `backend/app/core/config.py:30`
- **Фрагмент:** `SECRET_KEY: str = "your-secret-key-change-in-production"`
- **Суть:** pydantic-settings считает placeholder валидным дефолтом: если `.env` не задает `SECRET_KEY`, приложение стартует и подписывает JWT публично известным ключом из репозитория → любой может выковать `{"sub": "<any email>"}` и захватить любой аккаунт, включая WebSocket (`websocket.py` принимает `?token=`).
- **Live-подтверждение:** развернутый whimco-инстанс `/opt/teenfreelance/backend/.env` не задает `SECRET_KEY` — **инстанс работает с placeholder-ключом прямо сейчас**.
- **Fix:** сделать ключ обязательным (fail-fast): `SECRET_KEY: str = Field(...)` + `@field_validator("SECRET_KEY")`, отклоняющий `<32 chars` и известные placeholder-значения; генерация `openssl rand -hex 32`.
- **Immediate ops fix (whimco):** `KEY=$(openssl rand -hex 32); echo "SECRET_KEY=$KEY" >> /opt/teenfreelance/backend/.env && systemctl restart teenfreelance-backend`

### AUTH-02 — HIGH: 7-дневный JWT без revocation, токен в localStorage
- **Файлы:** `config.py:31` (`ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7`), `auth.py:56-59`, `contexts/AppContext.js:91` (localStorage)
- **Суть:** украденный токен (общее/семейное/школьное устройство) работает 7 дней с любой машины; сменa пароля токен не убивает.
- **Fix:** access-токен 1 час + `token_version` (см. AUTH-04) + refresh-токен в httpOnly Secure cookie.

### AUTH-03 — HIGH: нет rate limiting на /login и /register
- **Файлы:** `backend/app/api/v1/endpoints/auth.py:16,35`
- **Суть:** неограниченный brute-force и массовая регистрация.
- **Fix:** `slowapi` (5/minute login по IP+username; 10/hour register) + per-account exponential lockout.

### AUTH-04 — HIGH: нет logout / token_version / revocation
- **Файлы:** `auth.py`, `security.py`, `models/user.py:10-25` (нет колонки)
- **Суть:** украденный токен живёт 7 дней даже после смены пароля.
- **Fix:** колонка `users.token_version` + claim `tvv` в JWT + проверка в `get_current_user`; `POST /auth/logout` поднимает `token_version`; смена пароля тоже поднимает.
- **Патчи (диффы):** см. диффы AUTH-01..08 в ответе сессии / будущем IMPLEMENTATION.md.

### AUTH-05 — MEDIUM: email enumeration + timing side channel
- **Файлы:** `auth.py:23-27` ("Email already registered"), `crud/user.py:37-44` (authenticate возвращается сразу при отсутствии user — без bcrypt-прогона)
- **Fix:** generic error; dummy-bcrypt прогон при user-not-found.

### AUTH-06 — LOW: безлимитная длина пароля + молчаливая обрезка 72 байта
- **Файлы:** `schemas/user.py:12` (`min_length=8`, без max), `security.py:19-22,31-36`
- **Суть:** API принимает сколь угодно длинный пароль, bcrypt молча обрезает до 72 байт.
- **Fix:** `@field_validator("password")`: `len(v.encode("utf-8")) > 72 → ValueError`.

### AUTH-07 — INFO: мертвый passlib
- **Файл:** `security.py:4,13` — `CryptContext` создан, никогда не используется (хеширование напрямую bcrypt); passlib ломается с bcrypt≥4.1.
- **Fix:** удалить импорт и `pwd_context`.

### AUTH-08 — MEDIUM: WebSocket не проверяет is_active
- **Файл:** `backend/app/api/v1/endpoints/websocket.py:60-77` — только `verify_token()` (signature/expiry), без загрузки user и `is_active`.
- **Fix:** после `user = db.query(User)...` добавить `if not user.is_active: close(1008)`.

---

## 2. Resource authorization (IDOR/BOLA)

### B1 — CRITICAL: все отклики читаются без аутентификации
- **Файлы:** `backend/app/api/v1/endpoints/offers.py:99` (`read_offers_by_order`, GET /offers/orders/{id}) и `offers.py:118` (`read_offer`, GET /offers/{id})
- **Суть:** нет `Depends(get_current_active_user)` вообще → любой может перечислить все отклики (имя исполнителя, цены, этапы, описание) на любой заказ.
- **Fix:** требовать auth; выдавать отклики только заказчику заказа / исполнителю отклика / модератору.

### B2 — HIGH: заказ (включая draft) читается без аутентификации
- **Файл:** `backend/app/api/v1/endpoints/orders.py:137` (`read_order`, GET /orders/{id}) — нет auth, нет статуса-проверки.
- **Суть:** draft-заказ клиента (не предназначенный для публикации) читается по ID любым.
- **Fix:** `Depends(get_current_active_user)`; draft → 404 если `customer_id != current_user.id`; в CRUD `get_multi_with_filters` — hard `status != draft` фильтр если не заказчик.

### B3 — HIGH: любой аутентифицированный юзер удаляет любые файлы
- **Файл:** `backend/app/api/v1/endpoints/files.py:96-110` (`delete_file`) — требуется только «любой залогиненный»; комментарий в коде: «В будущем можно добавить проверку прав доступа».
- **Fix:** сохранять `uploaded_by_user_id` при upload; удаление — только владелец / участник заказа / модератор.

### B4 — HIGH: целостность payment-flow
- **Файлы:** `offers.py:244` (`accept_offer` не проверяет, что другой оффер уже accepted), `offers.py:300-330` (`accept_offer_by_executor`: dead check после commit + DDL в request-path `ALTER TYPE orderstatus ADD VALUE`), `orders.py:248` (`complete_order` позволяет исполнителю в одиночку завершить заказ, минуя submit-for-review → accept-work); `/users/me/transactions` (`users.py:126-140`) считает доход от `status == completed` → одну сторону может фальсифицировать сделку.
- **Fix:** single-accept в `accept_offer` (остальные → rejected, заказ → in_progress); dead check до записи; убрать DDL из request-path; complete — только заказчик, исполнитель — только через submit-for-review.

### B5 — MEDIUM: сообщения любому юзеру с подделанным контекстом
- **Файл:** `messages.py` `create_message` (~line 200): `to_user_id`, `offer_id`, `order_id` берутся as-is; нет проверки, что sender — counterparty заказа/оффера; нет block/spam защиты.
- **Fix:** валидировать участие в order/offer; mute/block.

### B6 — LOW: dead check "review" в submit-for-review
- **Файл:** `orders.py:442` — `str(...).upper()` затем `if current_status == "review"` — никогда не true.
- **Fix:** сравнивать case-insensitively (`== "review"` по lowered) или против enum.

**Позитив:** update/delete orders/offers/notes/portfolio/community-post корректно проверяют ownership (`orders.py:180,205` и др.).

---

## 3. Files

### F1 — HIGH: файл полностью читается в RAM до проверки размера
- **Файл:** `files.py:44-45` — `contents = await file.read(); file_size = len(contents)`; то же в `users.py:update_user_me` (~line 95).
- **Суть:** один мульти-GB body полностью буферизуется; несколько concurrent → OOM.
- **Fix:** стримить чанками (`while chunk := await file.read(1MB)`), прерывать при превышении MAX_FILE_SIZE; `client_max_body_size 12m;` в nginx.

### F2 — MEDIUM: Content-Type доверенный, магические байты не проверяются
- **Файл:** `files.py:36-38` — `is_allowed_file_type(file.content_type)` доверяет заголовку.
- **Fix:** проверка magic bytes (`python-magic`/`filetype`) против whitelist.

### F3 — MEDIUM: раскрытие серверного пути
- **Файл:** `files.py:70` — ответ содержит `"file_path": str(file_path)` (абсолютный путь сервера утекает в API).
- **Fix:** возвращать только `url`/`file_name`.

### F4 — LOW: чтение файлов без аутентификации
- **GET /files/{filename}** (`files.py:80-91`) — нет auth. UUIDv4 имена негадуемы, риск низкий.
- **Fix:** ок для публичных; для приватных — signed expiring URLs.

---

## 4. WebSocket

### W1 — MEDIUM: Authorization header пишется в логи
- **Файл:** `websocket.py:19` — `print(f"WebSocket headers: {dict(websocket.headers)}")` — Bearer-токен утекает в journald.
- **Fix:** логировать только несенситивные заголовки.

### W2 — MEDIUM: WS-менеджер in-memory, no is_active
- **Файл:** `websocket_manager.py` — per-process; молча ломается при `--workers 2`; `websocket.py:60-77` не проверяет is_active (см. AUTH-08).
- **Fix:** Redis pub/sub при multi-worker; is_active-check до manager.connect.

---

## 5. Minors' data

### M1 — HIGH: PII несовершеннолетних без lifecycle (consent/verification/deletion)
- **Файлы:** `models/user.py:12-13` (`phone`, `age`), `user.py:60` (`inn`), `schemas/user.py:11` (`age: Optional[int] ge=14 le=18` — **опционально** → взрослые регистрируются, несовершеннолетние могут опустить возраст); `verification_status` нигде не устанавливается; нет DELETE /users/me и export (GDPR Art. 15/17; 152-ФЗ ст. 9/10.1).
- **Fix:** age required + server-side check; DELETE /users/me (hard delete + cascade + log-anonymization); GET /users/me/export; consent-записи (timestamp, IP) для 14–17; inn — шифровать или убрать.

### M2 — MEDIUM: реальные имена подростков публично
- **Файл:** `orders.py:107-108` — `customer_name`, `customer_avatar_url` из неаутентифицированного листинга (B2); `community.py` — `user_name` на каждом посте/комменте.
- **Имя подростка + статистика (customer_projects_count / customer_hired_percent) → профилирование несовершеннолетних не-юзерами.
- **Fix:** first-name + initial (фронт уже имеет getInitials), auth для листинга/детали (B2), аватары только в authenticated-поверхностях.

### M3 — MEDIUM: нет модерации
- Нет admin-роли, report-endpoint, takedown для постов/комментов/сообщений — неприемлемый дефолт для подростковой платформы.
- **Fix:** `UserRole.moderator` + POST /reports + admin review endpoints; rate-limit + фильтрация контента (about, post text, messages) на контакт/ссылки паттерны.

### M4 — LOW: role выбирается клиентом при регистрации
- **Файл:** `schemas/user.py:6` — `role` в `UserBase` → `UserCreate` принимает любой role от клиента.
- **Fix:** исключить role из UserCreate; серверный дефолт.

---

## 6. Infrastructure

### I1 — CRITICAL: Postgres опубликован с дефолтными кредами
- **Файл:** `docker-compose.yml:16-18` — `ports: 5433:5432` + `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}`.
- **Fix:** удалить ports-блок; если нужен внешний доступ — `127.0.0.1:5433:5432` + сильный пароль.

### I2 — CRITICAL (deployment): plain HTTP + токен в localStorage
- **Файлы:** `services/api.js:3` + `App.js:388` (`REACT_APP_API_URL=http://185.233.184.192:8020`), `AppContext.js:91` (localStorage token).
- **Суть:** JWT и учетные данные подростков передаются открытым текстом; localStorage легко эксфильтрируется при XSS.
- **Fix:** TLS (Let's Encrypt), REACT_APP_API_URL=https://..., HSTS + nosniff + X-Frame-Options + CSP в nginx :8021; рассмотреть httpOnly-cookie sessions.

### I3 — MEDIUM: CORS env-passthrough без валидации
- **Файл:** `docker-compose.yml:44` — `BACKEND_CORS_ORIGINS: ${BACKEND_CORS_ORIGINS}` (unset → `[""]`); `main.py:14-20` — allow_credentials=True; комма-строка (config.py:22-26) vs JSON-array (наткнулись при деплое) — misconfig-ловушка.
- **Fix:** startup validation: reject `*` при allow_credentials=True; fail-fast на пустом списке.

### I4 — MEDIUM: dev-флаги и root в prod-контейнерах
- **Файлы:** `docker-compose.yml:30` (`--reload` в prod); backend Dockerfile без `USER` (root).
- **Fix:** убрать --reload; `RUN useradd ... && USER app`.

### I5 — INFO: косметика
- frontend Dockerfile EXPOSE 3000 vs compose PORT=3001; print()-debug в config.py:59, security.py:63-67, websocket.py — структурное логирование без секретов.

---

## 7. Deep-dive дополнение (2026-09-04, 2-й проход)

### D1 — MEDIUM: пагинация без потолка в messages
- **Файл:** `messages.py:141` — `limit: int = 100` (без Query(ge=1, le=500)) → клиент может запросить limit=10^9.
- **Fix:** `limit: int = Query(100, ge=1, le=500)`.

### D2 — LOW: hardcode 50 в /users/me/transactions
- **Файл:** `users.py` — `.limit(50)` hardcoded; константа.
- **Fix:** вынести в `settings`/константу.

### D3 — INFO: CORS print в config
- **Файл:** `config.py:59` — `print("CORS origins from env:", ...)` — убрать в структурное логирование.

### D5 — HIGH: публичный листинг отдаёт чужие draft-заказы через query-параметр
- **Файлы:** `orders.py:15` (`read_orders` принимает `status: Optional[OrderStatus]`) + `crud/order.py` (`get_multi_with_filters`: `if status: query.filter(Order.status == status)` — перекрывает дефолт «публичный список = только OPEN», который применяется только в `elif`-ветке при `status is None`).
- **Атака:** неаутентифицированный `GET /api/v1/orders?status=draft` → все draft-заказы всех пользователей (заголовки, описания, бюджеты). Аналогично `?status=completed`/`?status=cancelled` — чужие приватные сделки.
- **Fix:** в `read_orders` игнорировать клиентский `status` для неаутентифицированных/чужих вызовов: публичный листинг — жёстко `OrderStatus.open` (убрать `elif`, сделать отдельную ветку до передачи `status` в CRUD); draft-статус разрешать только при `customer_id == current_user.id`.

### D6 — MEDIUM: IDOR-чтение любого сообщения через POST /messages/{id}/read
- **Файлы:** `messages.py` `mark_as_read` + `crud/message.py::mark_as_read` — guard `if message and message.to_user_id == user_id` защищает только **модификацию**, но `return message` выполняется безусловно → ответ эндпоинта (MessageResponse с `content`) возвращает чужое сообщение по ID.
- **Атака:** аутентифицированный `POST /api/v1/messages/123/read` с чужим message_id → читает содержимое чужого сообщения (изменения не происходит, 404 только для несуществующих ID) → тихий скимминг переписки перебором ID.
- **Fix:** в crud после guard: `if message is None or message.to_user_id != user_id: return None` (404), либо в эндпоинте проверять `message.to_user_id == current_user.id` до возврата.

### D4 — INFO: order CRUD чист по SQLi
- **Файл:** `crud/order.py:113-124` — `search = f"%{keywords}%"` передается параметром в ORM `ilike()` — **не SQLi**; `_`/`%` wildcard injection только меняет семантику поиска (не security).
- Raw SQL по коду (`messages.py`, `orders.py`, `offers.py`, `database.py`) — **везде bound parameters** — SQLi не найдено.

---

## 8. Positive notes

- Ownership-проверки в update/delete-путях orders/offers/notes/portfolio/community — корректны.
- JWT decode pinned to algorithms=[HS256] (не уязвим к alg-confusion).
- Raw SQL parameterized (D4).
- WS accept-before-auth не утекает данные (close 1008 pre-auth).

---

## 9. Fix priority

| # | Item | Why first |
|---|------|-----------|
| 1 | AUTH-01 + I2 | Account takeover на живом whimco-инстансе |
| 2 | B1, B2, F3 | Неаутентифицированное чтение данных подростков |
| 3 | B3, F1 | Саботаж файлов + OOM DoS |
| 4 | I1 | Публичный Postgres с дефолтными кредами |
| 5 | AUTH-03/04 | Brute force + stolen-token window |
| CodeStyle | — | Мелкие диффы AUTH-05..08, B6, D1 — одним заходом |

---

## 10. Верификация аудита

- Все endpoints прочитаны: auth, users, orders, offers, notes, community, portfolio, messages, files, websocket.
- Models/schemas/crud (user, order, base) прочитаны.
- Deployment: whimco /opt/teenfreelance проверен живьем (см. сессию 2026-09-04).
- Аудит read-only; никаких изменений в TeenFreelance-код в этом заходе не вносилось.

---

## 11. Полная таблица owner-check по всем эндпоинтам (проход 2, 2026-09-05)

Проверено: все 62 маршрута в 12 файлах `app/api/v1/endpoints/*.py`, включая CRUD-слой под ними (`crud/message.py`, `crud/note.py`).

Легенда: ✅ = owner-check есть до чтения/мутации; ❌ = отсутствует; 🔓 = нет даже auth; ➖ = неприменимо (не работает с чужими ресурсами).

### 11.1 Спец-фокус (файлы, notes, portfolio, community)

| Эндпоинт | Метод | Owner-check | Severity | Что может атакующий с чужим ID |
|---|---|---|---|---|
| `files.py:88 /{filename}` | DELETE | ❌ — auth есть, но проверка владельца отсутствует; в коде TODO: «В будущем можно добавить проверку прав доступа» (`files.py:101`) | **HIGH** | Удалить ЛЮБОЙ файл любого пользователя (аватар, портфолио, работы подростков) знанием одного имени файла; имена перебираются (`uuid4` + расширение, но утекают через ответы upload/portfolio) |
| `files.py:72 /{filename}` | GET | 🔓 — `def get_file(filename)` без `Depends(get_current_active_user)` | **HIGH** | Скачивать любой загруженный файл без токена (все uploads публичны) |
| `files.py:29 /upload` | POST | ➖ — файл привязывается к владельцу только неявно (нет таблицы владения файлами) | MEDIUM (дизайн) | Отсутствие ownership-модели — корень проблемы DELETE/GET выше |
| `notes.py:52 /notes/{note_id}` | PUT | ✅ `note.user_id != current_user.id → 403` (`notes.py:59-64`) | — | — |
| `notes.py:74 /notes/{note_id}` | DELETE | ✅ `note.user_id != current_user.id → 403` (`notes.py:81-86`) | — | — |
| `notes.py:13 /orders/{order_id}/notes` | GET | ✅ — фильтрация по `user_id=current_user.id` в CRUD (`crud/note.py::get_by_order_id`); чужие заметки не возвращаются (но existence ордера раскрывается: 404 vs 200) | LOW | Подтвердить существование любого order_id по коду ответа |
| `notes.py:31 /orders/{order_id}/notes` | POST | ✅ — create/update всегда в контексте `user_id=current_user.id` | — | — |
| `portfolio.py:55 /{item_id}` | PUT | ✅ `item.user_id != current_user.id → 403` (`portfolio.py:62-67`) | — | — |
| `portfolio.py:77 /{item_id}` | DELETE | ✅ `item.user_id != current_user.id → 403` (`portfolio.py:84-89`) | — | — |
| `portfolio.py:28 /{item_id}` | GET | ❌ — маршрут без auth-зависимости; читает чужой элемент портфолио | **HIGH** (данные подростков) | Читать имя/описание/файлы работ любого подростка без токена |
| `portfolio.py:13 ""` | GET | ❌/⚠ — auth есть, но `user_id` — произвольный query-параметр (`portfolio.py:17`); собственный ID не требуется | **MEDIUM** | Перебирать user_id → собирать портфолио всех пользователей (например, для скрейпинга несовершеннолетних) |
| `community.py:143 /posts/{post_id}` | PUT | ✅ `post.user_id != current_user.id → 403` (`community.py:151-156`) | — | — |
| `community.py:179 /posts/{post_id}` | DELETE | ✅ `post.user_id != current_user.id → 403` (`community.py:187-192`) | — | — |
| `community.py:201 /posts/{post_id}/like` | ➖ | — (лайк привязан к current_user, чужих ID нет) | — | — |
| `community.py:220 /posts/{post_id}/comments` | GET | 🔓 — без auth; возвращает `user_name` каждого комментатора (`community.py:234-246`) | **MEDIUM** | Собирать реальные имена подростков по любому посту без токена |
| `community.py:240 /posts/{post_id}/comments` | POST | ➖ — комментарий создается от current_user | — | — |
| `community.py:44 /posts`, `:89 /posts/{post_id}` | GET | 🔓 — публичное чтение постов (запроектировано), НО `user_name` = реальные имена несовершеннолетних (см. M2) | **MEDIUM** | Массовый сбор имен+контента подростков |

### 11.2 Offers (все GET-ы без auth; мутации — с проверкой владельца)

| Эндпоинт | Метод | Owner-check | Severity | Что может атакующий с чужим ID |
|---|---|---|---|---|
| `offers.py:120 /orders/{order_id}` | GET | 🔓 без auth; нет фильтра по роли сделки | **CRITICAL** (B1) | Читать все ставки на любой заказ: суммы, описания, executor_id — коммерческая тайна подростков |
| `offers.py:138 /{offer_id}` | GET | 🔓 без auth | **CRITICAL** (B1) | Читать любой оффер по ID (перебором) |
| `offers.py:129 /my` | GET | ➖ (фильтр по current_user) | — | — |
| `offers.py:15 ""` | POST | ➖ — executor_id = current_user | — | — |
| `offers.py:153 /{offer_id}` | PUT | ✅ `offer.executor_id != current_user.id → 403` (`offers.py:162-167`) | — | — |
| `offers.py:175 /{offer_id}` | DELETE | ✅ executor-check (`offers.py:184-189`) | — | — |
| `offers.py:197 /{offer_id}/accept` | POST | ✅ `order.customer_id != current_user.id → 403` (`offers.py:206-211`) | — | — |
| `offers.py:265 /{offer_id}/reject` | POST | ✅ customer-check (тот же паттерн) | — | — |
| `offers.py:314 /{offer_id}/accept-by-executor` | POST | ✅ `offer.executor_id != current_user.id → 403` (`offers.py:331-336`) | — | — |
| `offers.py:454 /{offer_id}/reject-by-executor` | POST | ✅ executor-check | — | — |

### 11.3 Orders

| Эндпоинт | Метод | Owner-check | Severity | Что может атакующий с чужим ID |
|---|---|---|---|---|
| `orders.py:16 ""` | GET | ⚠ — публичный маркетплейс-листинг (запроектировано), НО `status=draft` возвращает чужие черновики (`crud/order.py::get_multi_with_filters` без исключения draft/private) | **HIGH** (B2) | Читать неопубликованные заказы всех заказчиков: заголовки, описания, бюджеты |
| `orders.py:205 /{order_id}` | GET | ⚠ — публичное чтение карточки заказа (в т.ч. draft) — детальная версия того же B2 | **HIGH** (B2) | Читать чужой draft-заказ напрямую по ID |
| `orders.py:141 /my`, `:160 /my-executor` | GET | ✅ — фильтр по current_user | — | — |
| `orders.py:220 ""` | POST | ➖ — customer_id = current_user | — | — |
| `orders.py:247 /{order_id}` | PUT | ✅ `order.customer_id != current_user.id → 403` (`orders.py:261-266`) | — | — |
| `orders.py:269 /{order_id}` | DELETE | ✅ customer-check (`orders.py:283-288`) | — | — |
| `orders.py:297 /complete` | POST | ✅ customer ИЛИ accepted-executor (`orders.py:315-330`) | — | — |
| `orders.py:348 /cancel` | POST | ✅ customer ИЛИ executor (`orders.py:366-381`) | — | — |
| `orders.py:399 /submit-for-review` | POST | ✅ `Only order executor can submit…` (`orders.py:417-432`) | — | — |
| `orders.py:519 /accept-work` | POST | ✅ customer-check | — | — |
| `orders.py:590 /request-revision` | POST | ✅ customer-check | — | — |

### 11.4 Messages / Users / Auth / Categories / Health / WS

| Эндпоинт | Метод | Owner-check | Severity | Что может атакующий с чужим ID |
|---|---|---|---|---|
| `messages.py:113 /{message_id}/read` | POST | ⚠ — проверка ТОЛЬКО в CRUD: `if message and message.to_user_id == user_id` (`crud/message.py:87-88`); при несовпадении **возвращает чужое сообщение 200**, не помечая прочитанным | **HIGH** (B5) | Скимминг чужих сообщений: `POST /messages/123/read` с перебором ID возвращает `content`, `title`, `from_user_id` чужой переписки |
| `messages.py:131 /conversation/{user_id}` | GET | ✅ — SQL-фильтр `(from=me AND to=X) OR (from=X AND to=me)` (`messages.py:157-161`) | — | — |
| `messages.py:16 ""`, `:103 /unread-count`, `:234 ""` | GET/POST | ✅ — все операции от/для current_user | — | — |
| `users.py:28 /me`, `:89 /me` и все `/me/*` (profile, skills, transactions: 12 маршрутов) | GET/PUT/POST/DELETE | ✅ — работают только с current_user; transactions — по user_id=current_user (`users.py:132-146`) | — | — |
| `users.py:267 /me/skills/{skill_name}` | DELETE | ✅ — удаляет скилл только current_user | — | — |
| `auth.py:16 /register`, `:35 /login` | POST | ➖ — публичные (см. AUTH-03 rate limiting, A5 enumeration) | — | — |
| `auth.py:64 /me` | GET | ✅ — токен → current_user | — | — |
| `categories.py:6 ""`, `health.py:5 ""` | GET | ➖ — публичные справочники (запроектировано) | INFO | — |
| `websocket.py:13 /ws` | WS | ⚠ — verify_token есть, НО нет `is_active`-проверки (W2); Channel-маппинг только по user_id из токена | **MEDIUM** | Деактивированный пользователь продолжает слушать канал до exp токена |

### 11.5 Сводка прохода 2

- **Мутации в целом защищены хорошо**: PUT/DELETE orders, offers, notes, portfolio, community — все имеют явные owner-checks (`!= current_user.id → 403`). Основные дыры — в **чтении** (GET без auth: offers, files, portfolio item, comments) и в **ownership-модели файлов** (нет таблицы file↔owner вообще).
- **Новые подтверждения**: portfolio GET /{item_id} без auth (раньше не фигурировал отдельно); files GET без auth; CRUD-скрытая инверсия `mark_as_read` (404 только для несуществующих, 200+content для чужих).
- **Fix-паттерн для всех ❌/🔓**: единая зависимость `get_file_owner_or_403` / require-auth на router-уровне + `user_id` в таблице файлов; для drafts — `status != draft OR current_user.id == customer_id` в фильтрах листинга.

---

## 12. Проход 3 — WebSocket + messages deep-dive (2026-09-05)

Проверены: `websocket.py` (120 строк), `websocket_manager.py`, `messages.py` (366 строк, включая create_message), `schemas/message.py`, фронт `App.js:373-397`. Полный разбор с патчем files.py (magic bytes + ownership) — в сессии 2026-09-05; ниже — итоги по 4 вопросам.

### 12.1 Токен в query string + активное логирование — HIGH (расширение W1/REC-013)

- Транспорт: фронт строит `?token=` (App.js:390) и печатает URL в консоль (App.js:392); сервер предпочитает query (websocket.py:27-30), header — только fallback (:31-35).
- **Ключевое:** сервер логирует токен сам — `websocket.py:16` печатает `query_params` (содержит `?token=`), :17 печатает все заголовки; всего 15 `print()` в websocket.py + 5 в websocket_manager.py → JWT в journald на whimco прямо сейчас.
- Прокси/CDN-риск сегодня отсутствует (WS идёт напрямую в uvicorn :8020), но включается при добавлении TLS-терминации/CDN — access-логи пишут полный request line.
- **Fix:** убрать токен-печатание; одноразовые ws-ticket (`POST /auth/ws-ticket` → TTL 30s, single-use, `ws://…/ws?ticket=…`); header-путь оставить как основной для не-браузеров.

### 12.2 Привязка к user_id строгая; каналов нет вообще — MEDIUM

- Bind только после `verify_token` + DB-lookup (websocket.py:72-77); менеджер — плоский `Dict[int, Set[WebSocket]]` (websocket_manager.py:10), клиент может только heartbeat/pong.
- Подписаться на чужой канал **невозможно структурно** — комнат/тем/подписок в коде нет (grep channel/room/subscribe — пусто); все пуш-рассылки идут серверно через `send_personal_message(msg, user_id)` по аутентифицированному id.
- Реальные риски смежные: нет `is_active`-проверки (W2); наследует A1 (placeholder SECRET_KEY → forged token работает и здесь); in-memory синглтон ломает fan-out при `workers>1` и теряет соединения при рестарте → REC-023 (P2).

### 12.3 Rate limiting сообщений отсутствует — HIGH (новое → REC-022)

- REST: `create_message` (messages.py:234) без throttle; `MessageCreate` без `max_length` (schemas/message.py) — неограниченный флуд на произвольных получателей (плюс B5: без валидации участников).
- WS: receive-цикл (websocket.py:88-97) без token-bucket, без лимита кадра сверх дефолтных 16MB `ws-max-size`, без cap сокетов на user_id → один токен = тысячи записей в `active_connections` (memory DoS).
- **Fix:** slowapi 10/min на пару sender→recipient + 100/hour на sender; `content: Field(max_length=5000)`; WS token-bucket 5 msg/s (burst 10), кадр >64KB отклонять, ≤5 сокетов на user_id; pair-level дневная квота (анти-харассмент).

### 12.4 Модерация/фильтрация контента отсутствует полностью — HIGH (обоснование P2→P1 для REC-012)

- grep report/moderat/block/mute по всем endpoints — ноль совпадений. Телефоны (`+7…`), мессенджеры (t.me/wa.me/vk), email, ссылки проходят без фильтров; вставка в БД сырым SQL без единой проверки контента (messages.py:263-283).
- На площадке несовершеннолетних это grooming-вектор: взрослый «заказчик» (любой зарегистрированный — см. B5) уводит подростка вне платформы без трения; у жертвы нет block/mute/report.
- **Fix (минимум):** regex-скринер phone/messenger/email/url → `moderation_queue` (flag, не silent-drop); `POST /reports`; роль moderator + takedown; `blocked_pairs` для block/mute; для новых пар — удержание первых N сообщений до ревью (продуктовое решение).

### 12.5 Синхронизация с реестром

- REC-012: P2→**P1** (обоснование — §12.4).
- REC-013: расширена формулировкой про `query_params`-логирование и ws-ticket (§12.1).
- **REC-022** (новая, P1): rate limiting WS/messages (§12.3).
- **REC-023** (новая, P2): ConnectionManager redesign (§12.2).

---

## 13. Проход 4 — infra/dependencies deep-dive (2026-09-05)

Проверены: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/app/core/config.py` (полностью), `backend/main.py`, `backend/entrypoint.sh`, `backend/requirements.txt`, `frontend/package.json` + сгенерированный lockfile.

### 13.1 Публикация БД наружу с дефолтными кредами — HIGH (уточнение REC-006/I1)

- `docker-compose.yml:16-17` — `ports: "5433:5432"` на всех интерфейсах хоста; внутренняя сеть compose (`POSTGRES_HOST: db`, :29) публикацию не требует ни для одного сервиса.
- Дефолт `postgres:postgres` зашит в 7 местах (`${POSTGRES_USER:-postgres}` / `${POSTGRES_PASSWORD:-postgres}`: db env ×3 :10-12, backend env ×4 :30-34) — отсутствие `.env` молча даёт рабочие креды.
- **Fix:** удалить `ports:` у db; пароль обязателен — `${POSTGRES_PASSWORD:?set in .env}`; для dev-отладки — `127.0.0.1:5433:5432`.

### 13.2 CORS: wildcard+credentials допускается конфигурацией — MEDIUM (уточнение REC-016/I3)

- `main.py:14-20` — `allow_credentials=True` всегда; `config.py:20-24` пропускает любую строку env (`"*"` → `["*"]`). Комбинация = reflected credentialed CORS с любого origin.
- Сейчас прод не задет: whimco `.env` = один origin; дефолт конфига узкий. Риск активируется httpOnly-cookie из REC-007.
- Гигиена: `config.py:57` печатает origins в лог; `allow_methods/headers=["*"]` шире необходимого.
- **Fix:** field_validator с fail-fast на `"*"`; методы/заголовки — явным списком; print удалить.

### 13.3 Startup-цепочка: unattended-миграции + DDL + `--reload`+root — HIGH (уточнение REC-016/I4)

- `entrypoint.sh` — безопасный passthrough (`exec "$@"`), авто-раннеров нет.
- Реальная цепочка — `docker-compose.yml:28`: `sh -c "alembic upgrade head && uvicorn … --reload"` на каждый старт (restart: unless-stopped): (1) миграции без human-gate — так UPPERCASE-enum дошёл до прода, при том что обязательная вторая половина `fix_enum_cases.py` (CON-01) в цепочке отсутствует; (2) `main.py:29-31` startup-DDL (`ensure_orderstatus_review_enum`) при каждом буте; (3) `--reload` + bind-mount `./backend:/app` + нет `USER` в Dockerfile (root) — dev-режим как «прод».
- Сидинга нет (auto-run непроверенных скриптов нет — только `clean_db.py`/`fix_enum_cases.py` в репо, ничего не выполняется само).
- **Fix:** прод = prebuilt-образ без bind-mount/--reload; миграции явным release-шагом либо гейт `$MIGRATE_ON_START`; в цепочку добавить `python fix_enum_cases.py`; `USER app` в Dockerfile.

### 13.4 Зависимости: OSV-аудит (машинная верификация, api.osv.dev, 2026-09-05) — HIGH (уточнение REC-015)

Артефакты: `projects_17/TeenFreelance-master/audits/2026-09-05_pip_osv.json` (16 pinned+transitive), `2026-09-05_npm_osv.json` (1135 пакетов lockfile). `pip-audit -r` неприменим локально (Termux/py3.14 не собирает pydantic-core 2.5-era) — использован OSV.dev querybatch (та же база, что у pip-audit).

**Backend — 46 advisory на 7 пакетов:**

| Пакет | Версия | Advisories | Ключевые ID |
|---|---|---|---|
| python-multipart | 0.0.6 | **16** | CVE-2024-24762 (ReDoS на пути `POST /files/upload`) + 15 GHSA/PYSEC 2026 |
| starlette (transitive fastapi) | 0.27.0 | **14** | CVE-2024-47874 (multipart DoS) + 13 |
| python-jose | 3.3.0 | **4** | CVE-2024-33663 (JWT forgery), CVE-2024-33664 (DoS) |
| ecdsa (transitive jose) | 0.19.0 | 4 | GHSA-wj6h-64fc-37mp |
| fastapi | 0.104.1 | 1 | PYSEC-2024-38 |
| h11 | 0.14.0 | 2 | GHSA-vqfr-h8mv-ghfj |
| python-dotenv | 1.0.0 | 2 | PYSEC-2026-2270 |

Чисто: uvicorn, sqlalchemy, psycopg2-binary, pydantic, pydantic-settings, alembic, passlib (но abandoned 2016 → AUTH-07).

**Frontend — 107 advisory на 37 пакетов, все в prod-scope:** причина — `package.json` вообще не имеет `devDependencies` (CRA-тулчейн и `@testing-library/*` объявлены как runtime-зависимости), плюс compose использует `npm start` (CRA dev-server) как прод-сервер. npm уже резолвит свежайшие версии — большинство advisory не имеют fix-релиза. Топ: axios 1.13.2 — 29 (CVE-2026-44494, fix 1.16.0), webpack-dev-server 4.15.2 — 6, node-forge 1.3.3 — 4, postcss 8.5.6 — 4, ws 8.19.0 — 2, serialize-javascript 4.0.0, shell-quote, http-proxy-middleware, rollup, lodash, qs. Корневая причина — EOL `react-scripts 5.0.1` (миграция на Vite — стратегическая).

**Вывод:** бэкенд-пины frozen >2 лет; вектора CVE совпадают с уже-принятыми рисками (multipart = files upload path, jose = auth path).

### 13.5 Синхронизация с реестром

- REC-006: уточнена (7 дефолтов кредов, 0.0.0.0-публикация).
- REC-015: дополнена OSV-верифицированным CVE-списком (§13.4).
- REC-016: дополнена (wildcard-validator, startup-цепочка, CRA dev-server).
- REC-010: дополнена (server-side age gate на регистрации и денежных операциях; сущность `parental_consents` — нет ни флага, ни записи; grep consent/parent/guardian — ноль).
- **REC-024** (новая, P1): PII field-hygiene — маски `inn` (`****last4`, убрать echo из POST/PUT), `phone`, write-only `age`; шифрование inn-at-rest; OpenAPI-регрессия (password_hash/inn/phone/age не появляются в кросс-юзер response-моделях). Основание: pass 5 PII-анализ (см. сессию 2026-09-05).
