# RECOMMENDATIONS — Единый реестр рекомендаций платформы

> **Статус:** ACTIVE **[канон]** · **Создан:** 2026-09-04
> **Роль:** единый источник истины по рекомендациям (не только security) — аудит-фиксы,
> архитектурные улучшения, ops-гигиена. Каждая рекомендация имеет ID, источник, приоритет,
> статус, owner-область и критерий закрытия.
> **Правило ведения:** append-only по номерам (REC-NNN); статусы: `OPEN` / `IN_PROGRESS` /
> `DONE` / `WONTFIX` (с обоснованием) / `OBSOLETE`. Никогда не удалять записи; закрытие —
> только через смену статуса + дату + ссылку на verify (commit / command / test).
> **Связь:** дополняет `core_02/LESSONS.md` (уроки = что выучили; рекомендации = что сделать)
> и `docs_10/audits/` (аудит = источник находок). Подчиняется RULES.md §«Аудит и анализ».

---

## Как вести

1. Новая рекомендация = следующий свободный `REC-NNN` (никогда не переиспользовать номера).
2. Формат записи: таблица ниже — одна строка = одна рекомендация; детали — в anchor-доке.
3. Источник (Source) — аудит/инцидент/ревью, который породил рекомендацию.
4. Приоритет: `P0` (делать немедленно, живой риск) / `P1` (ближайший релиз) / `P2` (бэклог).
5. Закрытие: статус `DONE` + ссылка на commit/verify в «Verify» колонке.
6. Реестр проверяется `consistency_check` (см. «Fix priority» таблицы в аудите — реестр не должен с ними расходиться).

---

## Реестр

| ID | Дата | Источник | Область | Рекомендация | Приоритет | Статус | Verify |
|----|------|----------|---------|--------------|-----------|--------|--------|
| REC-001 | 2026-09-04 | AUDIT_TEENFREELANCE §1 | teenfreelance/auth | Сделать `SECRET_KEY` обязательным (`Field(...)` + validator против placeholder), сгенерировать per-env ключ; ops-фикс на whimco (openssl rand -hex 32 в .env + restart) | P0 | OPEN | — |
| REC-002 | 2026-09-04 | AUDIT_TEENFREELANCE §6 | teenfreelance/infra | TLS на whimco (Let's Encrypt + domain), REACT_APP_API_URL → https, HSTS/nosniff/X-Frame-Options/CSP в nginx :8021 | P0 | OPEN | — |
| REC-003 | 2026-09-04 | AUDIT_TEENFREELANCE §2 | teenfreelance/authz | Auth + ownership на offers-чтение (B1) и order-detail/draft-фильтр (B2) | P0 | OPEN | — |
| REC-004 | 2026-09-04 | AUDIT_TEENFREELANCE §3 | teenfreelance/files | Ownership на delete_file (B3) + убрать `file_path` из ответа upload (F3) | P0 | OPEN | — |
| REC-005 | 2026-09-04 | AUDIT_TEENFREELANCE §3 | teenfreelance/files | Стриминговая загрузка файлов (чанки вместо `await file.read()`) + `client_max_body_size` в nginx (F1) | P1 | OPEN | — |
| REC-006 | 2026-09-04 | AUDIT_TEENFREELANCE §6; §13.1 | teenfreelance/infra | Убрать `ports: 5433:5432` из docker-compose (I1). Уточнено 2026-09-05: публикация на всех интерфейсах + дефолт `postgres:postgres` в 7 местах (compose :10-12, :30-34); пароль обязателен `${POSTGRES_PASSWORD:?…}`; dev-отладка — `127.0.0.1:5433:5432` | P0 | OPEN | — |
| REC-007 | 2026-09-04 | AUDIT_TEENFREELANCE §1 | teenfreelance/auth | `token_version` + claim `tvv` + `POST /auth/logout` + короткий access-токен (1h) (AUTH-02/04) | P1 | OPEN | — |
| REC-008 | 2026-09-04 | AUDIT_TEENFREELANCE §1 | teenfreelance/auth | slowapi rate-limit на /login (5/min) и /register (10/hour) (AUTH-03) | P1 | OPEN | — |
| REC-009 | 2026-09-04 | AUDIT_TEENFREELANCE §2 | teenfreelance/authz | Payment-flow integrity: single-accept, complete только заказчиком, убрать DDL из request-path (B4) | P1 | OPEN | — |
| REC-010 | 2026-09-04 | AUDIT_TEENFREELANCE §5; §13.5 | teenfreelance/minors | PII-lifecycle: age required, DELETE /users/me, export, consent-записи (M1). Дополнено 2026-09-05: server-side age-gate обязателен на регистрации И перед денежными операциями (сейчас `ge=14/le=18` только в pydantic-схеме и только если клиент прислал age — omit = bypass); parental consent отсутствует как сущность (grep consent/parent/guardian — ноль) — завести `parental_consents` (user_id, guardian_contact, consent_type, granted_at, revoked_at, proof_ref), гейт перед первым paid-transaction | P1 | OPEN | — |
| REC-011 | 2026-09-04 | AUDIT_TEENFREELANCE §5 | teenfreelance/minors | Имя → first-name+initial в публичных поверхностях; аватары только в auth-зонах (M2) | P1 | OPEN | — |
| REC-012 | 2026-09-04 | AUDIT_TEENFREELANCE §5; WS/messages deep-dive 2026-09-05 | teenfreelance/minors | Модерация: роль moderator, POST /reports, takedown, контент-фильтры (M3). Пересмотр 2026-09-05 **P2→P1**: фильтрация контента в messages/WebSocket отсутствует полностью — телефоны/мессенджеры/ссылки/PII проходят без фильтров (grooming-вектор на площадке несовершеннолетних); нужны content_filter (phone/messenger/email/url-regex), moderation_queue, block/mute для жертвы | P1 | OPEN | — |
| REC-013 | 2026-09-04 | AUDIT_TEENFREELANCE §4; WS deep-dive 2026-09-05 | teenfreelance/websocket | Убрать печать Authorization-заголовков из WS-логов (W1); is_active-проверка в WS (AUTH-08). Расширено 2026-09-05: websocket.py:16 печатает `query_params` с `?token=` (утечка JWT в journald, 15 print в websocket.py + 5 в manager), фронт App.js:392 логирует URL с токеном в консоль; перейти на одноразовые ws-ticket (POST /auth/ws-ticket, TTL 30s, single-use) вместо query-токена | P1 | OPEN | — |
| REC-014 | 2026-09-04 | AUDIT_TEENFREELANCE §2 | teenfreelance/authz | Валидация участников в create_message (B5); пагинация le=500 в conversation (D1) | P1 | OPEN | — |
| REC-015 | 2026-09-04 | AUDIT_TEENFREELANCE §1; §13.4 | teenfreelance/auth | Мелкие auth-фиксы одним заходом: enumeration/timing (AUTH-05), пароль max-72-bytes (AUTH-06), удалить passlib (AUTH-07), B6 dead-check, M4 role-not-from-client. Дополнено 2026-09-05 OSV-аудитом (46 advisory на backend): python-multipart 0.0.6→0.0.9+ (CVE-2024-24762 ReDoS, путь /files/upload), python-jose 3.3.0→PyJWT (CVE-2024-33663 forgery, 33664 DoS), starlette 0.27 transitive (CVE-2024-47874) — требует bump fastapi; артефакт audits/2026-09-05_pip_osv.json | P1 | OPEN | — |
| REC-016 | 2026-09-04 | AUDIT_TEENFREELANCE §6; §13.2/§13.3 | teenfreelance/infra | docker-compose prod-гигиена: убрать `--reload`, non-root USER, CORS startup-validation (I3/I4). Дополнено 2026-09-05: fail-fast validator на `"*"` в BACKEND_CORS_ORIGINS (allow_credentials=True всегда!); startup-цепочка compose:28 = unattended `alembic upgrade head` без `fix_enum_cases.py` (CON-01) + startup-DDL main.py:29-31 + bind-mount ./backend:/app; frontend в compose = CRA dev-server (`npm start`) как прод-сервер | P1 | OPEN | — |
| REC-017 | 2026-09-04 | AUDIT_TEENFREELANCE §3 | teenfreelance/files | Magic-bytes проверка контента (F2); signed URLs для приватных файлов (F4) | P2 | OPEN | — |
| REC-018 | 2026-09-04 | Session 2026-09-04 (deployment) | freebuff/deploy | Задеплоенный whimco-инстанс TeenFreelance использует placeholder SECRET_KEY — ops-фикс провести ДО следующего релиза кода (см. REC-001) | P0 | OPEN | — |
| REC-019 | 2026-09-04 | AUDIT_TEENFREELANCE §7 D5 | teenfreelance/authz | Публичный листинг заказов: жёсткий фильтр OPEN для неаутентифицированных; draft/completed/cancelled — только владельцу (D5) | P0 | OPEN | — |
| REC-020 | 2026-09-04 | AUDIT_TEENFREELANCE §7 D6 | teenfreelance/authz | POST /messages/{id}/read: 404 если message.to_user_id != current_user.id — закрыть IDOR-чтение переписки (D6) | P1 | OPEN | — |
| REC-021 | 2026-09-05 | AUDIT_TEENFREELANCE §11.1 (pass 2) | teenfreelance/authz | `GET /portfolio/{item_id}` без auth (portfolio.py:28) — добавить `get_current_active_user`; в листинге `/portfolio` ограничить `user_id` query-param собственными данными либо оставить публичным только published-элементам | P1 | OPEN | — |
| REC-022 | 2026-09-05 | WS/messages deep-dive 2026-09-05 | teenfreelance/antiflood | Rate-limit сообщений: REST `create_message` без лимитов и без max_length (slowapi 10/min на пару sender→recipient + 100/hour на sender; `content: Field(max_length=5000)`); WS-цикл (websocket.py:88-97) без token-bucket — добавить 5 msg/s burst 10, кадр >64KB отклонять, cap 5 сокетов на user_id (сейчас — тысячи соединений на один токен, DoS памяти); pair-level дневная квота как анти-харассмент бэкстоп | P1 | OPEN | — |
| REC-023 | 2026-09-05 | WS deep-dive 2026-09-05 | teenfreelance/websocket | ConnectionManager redesign: in-memory синглтон (websocket_manager.py:29 `manager = ConnectionManager()`) ломает fan-out при `workers>1` (сокет получателя в другом процессе) и теряет все соединения при рестарте; нужен Redis pub/sub или шардирование + reconnect-буфер; eviction мёртвых соединений уже частично есть в send_personal_message — унифицировать | P2 | OPEN | — |
| REC-024 | 2026-09-05 | AUDIT_TEENFREELANCE §13.5 (pass 5 PII) | teenfreelance/minors | PII field-hygiene: `inn` маскировать (`****last4`), убрать echo из POST/PUT профиля, encrypt-at-rest, собирать только при payout; `phone` маскировать; `age` write-only (не возвращать); OpenAPI-регрессия: password_hash/inn/phone/age не должны появляться в кросс-юзер response-моделях | P1 | OPEN | — |

---

## Статистика

- **Всего:** 24 · **P0:** 7 (REC-001, REC-002, REC-003, REC-004, REC-006, REC-018, REC-019) · **P1:** 15 (REC-005, 007–016, 020–022, 024) · **P2:** 2 (REC-017, REC-023)
- **Открыто:** 24 · **Закрыто:** 0
- **Изменение 2026-09-05:** REC-012 P2→P1 (grooming-вектор, WS/messages deep-dive); добавлены REC-022 (antiflood), REC-023 (WS manager redesign), REC-024 (PII field-hygiene, pass 5); REC-006/010/015/016 дополнены результатами infra/deps OSV-аудита (§13 аудита)

---

## Cross-links

- Источник находок: [`docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md`](audits/AUDIT_TEENFREELANCE_2026-09-04.md)
- Уроки платформы: [`core_02/LESSONS.md`](../core_02/LESSONS.md) (CON-68 — урок о ведении рекомендаций)
- Документ-реестр: [`docs_10/DOCUMENT_REGISTRY.md`](DOCUMENT_REGISTRY.md)
- Правила документирования: [`docs_10/core/RULES.md`](core/RULES.md)
- Правила ведения проектов: [`docs_10/core/PROJECT_RULES.md`](core/PROJECT_RULES.md)
