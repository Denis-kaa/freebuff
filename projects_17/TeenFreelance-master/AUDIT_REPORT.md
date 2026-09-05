# Аудит TeenFreelance — 2026-09-05

**Объект:** `projects_17/TeenFreelance-master`  
**Прод-контур:** whimco (`teenfreelance-backend` на `:8020`, nginx на `:8021`)  
**Стек:** FastAPI, SQLAlchemy/Alembic, PostgreSQL, JWT (`python-jose`), bcrypt, React CRA, WebSocket, Docker Compose  
**Целевая аудитория:** подростки 14–18 лет; роли `customer` и `executor`; денежные поля `balance` и `tf_coins`

> Это технический security-аудит, а не юридическое заключение и не формальная сертификация CVSS. PoC-сценарии ниже предназначены только для локального/staging-контура с тестовыми аккаунтами; проверка на проде без отдельного разрешения запрещена.

## Объём и методика

Отчёт объединяет семь проходов:

1. authentication и управление сессиями;
2. resource authorization / IDOR / BOLA по всем `app/api/v1/endpoints/*.py`;
3. загрузка, чтение, удаление и хранение файлов;
4. WebSocket и сообщения;
5. данные несовершеннолетних, возраст, согласие и PII;
6. Docker, deployment, CORS, startup и инфраструктура;
7. зависимости и известные уязвимости по OSV-аудиту.

Проверялись endpoint-модули, схемы, модели, CRUD-слой, конфигурация Docker/доступа, frontend-вызовы и состояние развёрнутого whimco-инстанса. Номера строк относятся к аудированному снимку; после внесения исправлений их необходимо перепроверить.

---

## Executive summary

TeenFreelance имеет пригодную для MVP основу: используется FastAPI с типизированными схемами, SQLAlchemy с параметризованными запросами, есть разделение ролей `customer`/`executor`, а большинство операций изменения ресурсов проверяет владельца. Однако в текущем состоянии платформа не готова к безопасной эксплуатации с несовершеннолетними и реальными деньгами. Главные проблемы — публично известный fallback для подписи JWT, передача данных по HTTP, незащищённое чтение офферов и черновиков, возможность удаления чужих файлов и публикация PostgreSQL с дефолтными учётными данными. Дополнительно отсутствуют возрастной и родительский consent-lifecycle, модерация общения, anti-flood и минимизация чувствительных данных. До закрытия P0 следует остановить реальные платные операции и не допускать неконтролируемое общение подростков с заказчиками.

### Сводка риска

| Область | Оценка |
|---|---|
| Аутентификация | **Критический риск:** при отсутствии `SECRET_KEY` в `.env` возможна подделка JWT; отсутствуют отзыв токенов и rate limiting |
| Авторизация ресурсов | **Критический/высокий риск:** несколько GET не требуют auth или не проверяют отношение пользователя к ресурсу |
| Файлы | **Высокий риск:** нет ownership-модели, удаление чужого файла, публичное чтение, доверие MIME, полная буферизация в RAM |
| WebSocket/сообщения | **Высокий риск:** JWT в query string и логах, нет ограничений флуда и модерации |
| Несовершеннолетние | **Высокий риск:** nullable age, отсутствует parental consent, избыточное раскрытие PII и нет lifecycle удаления/экспорта |
| Инфраструктура | **Критический/высокий риск:** публичный Postgres с дефолтными кредами, HTTP, dev-настройки в production compose, устаревшие зависимости |

---

## Критические находки (critical/high)

### C-01 — CRITICAL: публичный fallback `SECRET_KEY` позволяет подделать токены

- **CVSS-подобная оценка:** **9.8/10** — удалённая эксплуатация, низкая сложность, не требуется аккаунт или взаимодействие; затронуты confidentiality, integrity и availability всех аккаунтов.
- **Файл/фрагмент:** `backend/app/core/config.py:30`
  ```python
  SECRET_KEY: str = "your-secret-key-change-in-production"
  ```
  Токены подписываются в `auth.py`, а проверяются в `security.py`. В аудированном прод `.env` не переопределял этот ключ.
- **Воздействие:** атакующий, знающий значение из репозитория, может создать JWT с `sub` любого пользователя и обойти ownership-checks, получить доступ к профилю, балансу, сообщениям и WebSocket.
- **Безопасный PoC:** в локальном стенде создать HS256-токен с тестовым email и известным ключом, затем вызвать `/api/v1/users/me`. Успешный `200` от имени тестового пользователя подтверждает проблему.
- **Исправление:** убрать default; сделать `SECRET_KEY` обязательным через `Field(...)`, отклонять placeholder и ключи короче 32 случайных байт, сгенерировать per-environment secret, немедленно ротировать ключ и инвалидировать все старые токены.
- **Реестр:** `REC-001`, `REC-018`.

### C-02 — CRITICAL: production API и WebSocket работают по plain HTTP

- **CVSS-подобная оценка:** **9.1/10** — пассивный сетевой атакующий может читать credentials, JWT, сообщения и PII.
- **Файлы/фрагменты:** `frontend/src/services/api.js` и production-конфигурация используют `http://185.233.184.192:8020`; WebSocket строится без WSS; JWT хранится в `localStorage` (`frontend/src/AppContext.js:91`).
- **Воздействие:** токены и пароли могут быть перехвачены в публичной, школьной или общей Wi-Fi-сети. Украденный bearer-токен действует до истечения срока.
- **Безопасный PoC:** в staging через тестовый HTTP-интерцептор показать, что `Authorization: Bearer ...` и тело login-запроса читаются без расшифровки.
- **Исправление:** домен + HTTPS/WSS, `REACT_APP_API_URL=https://...`, HSTS, CSP, `nosniff`, clickjacking protection; access-token сделать короткоживущим, refresh хранить в `httpOnly; Secure; SameSite` cookie с ротацией.
- **Реестр:** `REC-002`.

### C-03 — CRITICAL: офферы читаются без аутентификации

- **CVSS-подобная оценка:** **8.6/10** — удалённый доступ без привилегий, раскрытие коммерческой и пользовательской информации.
- **Файлы/фрагменты:** `backend/app/api/v1/endpoints/offers.py:120` — `GET /offers/orders/{order_id}`; `:138` — `GET /offers/{offer_id}`. В сигнатурах нет `Depends(get_current_active_user)`.
- **Воздействие:** анонимный клиент может перебирать ID и получать суммы, описания, статусы, `executor_id` и все ставки на чужие заказы.
- **Безопасный PoC:** без заголовка `Authorization` запросить в staging `GET /api/v1/offers/1` и `GET /api/v1/offers/orders/1`; `200` с чужим тестовым оффером подтверждает проблему.
- **Исправление:** требовать auth; разрешать чтение только заказчику, исполнителю оффера, принятому контрагенту или модератору; для недоступных ресурсов возвращать `404`.
- **Реестр:** `REC-003`.

### C-04 — CRITICAL: PostgreSQL опубликован наружу с дефолтными credentials

- **CVSS-подобная оценка:** **9.8/10** при запуске на публичном хосте.
- **Файл/фрагмент:** `docker-compose.yml:16-17` — `ports: "5433:5432"`; в нескольких местах есть `${POSTGRES_PASSWORD:-postgres}` и аналогичные fallback для пользователя/пароля.
- **Воздействие:** база доступна с интерфейсов хоста; при неполном `.env` используются `postgres/postgres`. Компрометация раскрывает пользователей, балансы, сообщения, заказы и PII, а также позволяет менять данные.
- **Безопасный PoC:** в disposable staging выполнить `docker compose config`, проверить опубликованный порт и доступность TCP `5433` из разрешённой тестовой сети. Не подбирать пароль на production.
- **Исправление:** удалить `ports` у db в production; оставить Compose DNS `db:5432`; для локальной отладки использовать только `127.0.0.1:5433:5432`; применить `${POSTGRES_PASSWORD:?set in .env}` и ротировать пароль.
- **Реестр:** `REC-006`.

### H-01 — HIGH: публичная выдача draft и приватных заказов

- **CVSS-подобная оценка:** **8.1/10**.
- **Файлы/фрагменты:** `orders.py:16` принимает клиентский `status`; `crud/order.py::get_multi_with_filters` применяет его и обходится без жёсткого фильтра `OPEN`; `orders.py:205` (`GET /orders/{order_id}`) не проверяет владельца draft.
- **Атака:** `GET /api/v1/orders?status=draft` без auth возвращает чужие черновики; `completed`/`cancelled` раскрывают историю сделок.
- **PoC:** создать draft тестовым пользователем A, затем запросить список и detail без токена от пользователя B.
- **Исправление:** анонимному листингу разрешить только `OPEN`; draft/private статусы — только владельцу или разрешённому контрагенту.
- **Реестр:** `REC-003`, `REC-019`.

### H-02 — HIGH: любой аутентифицированный пользователь может удалить чужой файл

- **CVSS-подобная оценка:** **8.1/10**.
- **Файл/фрагмент:** `backend/app/api/v1/endpoints/files.py:96-110`; проверяется только факт auth, ownership отсутствует. В коде есть TODO о добавлении прав «в будущем».
- **Атака:** пользователь B получает имя файла пользователя A из утечки URL/ответа и вызывает `DELETE /api/v1/files/{filename}`; удаляется аватар, портфолио или вложение A.
- **PoC:** загрузить два disposable-файла пользователями A и B; авторизоваться как B и удалить имя файла A. Успешный ответ подтверждает IDOR-разрушение.
- **Исправление:** таблица `files` с `owner_user_id`, `storage_key`, optional `order_id`/`portfolio_item_id`, MIME и timestamps; удаление только владельцем, участником заказа или модератором.
- **Реестр:** `REC-004`.

### H-03 — HIGH: скачивание файлов публичное, ownership-модели нет

- **CVSS-подобная оценка:** **7.5/10**; UUID снижает вероятность угадывания, но не заменяет контроль доступа.
- **Файл/фрагмент:** `files.py:72` — `GET /files/{filename}` без `Depends(get_current_active_user)`.
- **Что хранится:** общая директория может содержать аватары, работы портфолио и потенциальные вложения заказов.
- **Атака:** любой, кто получил filename из ответа, frontend URL, логов или другого API, скачивает файл без токена.
- **PoC:** загрузить тестовый файл пользователем A, открыть его URL из чистого клиента без auth; `200` подтверждает публичность.
- **Исправление:** разделить public/private files; private выдавать только через auth endpoint или короткоживущий signed URL; ownership хранить в БД.
- **Реестр:** `REC-004`, `REC-017`, `REC-021`.

### H-04 — HIGH: `POST /messages/{id}/read` раскрывает чужое сообщение

- **CVSS-подобная оценка:** **7.5/10** — требуется только любой валидный аккаунт.
- **Файлы/фрагменты:** `messages.py:113`; `crud/message.py:87-88` проверяет recipient только перед изменением, но затем возвращает объект сообщения даже при несовпадении `to_user_id`.
- **Атака:** перебором ID получить `content`, отправителя и метаданные чужой переписки.
- **PoC:** A отправляет B тестовое сообщение; авторизованный C вызывает `POST /api/v1/messages/{message_id}/read`; `200` с текстом подтверждает IDOR.
- **Исправление:** при `message is None` или `message.to_user_id != current_user.id` возвращать `None`/`404` до сериализации; добавить регрессионный тест.
- **Реестр:** `REC-020`.

### H-05 — HIGH: JWT живёт семь дней, logout/revocation отсутствуют

- **CVSS-подобная оценка:** **7.4/10**.
- **Файлы/фрагменты:** `config.py:31` — `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7`; `auth.py:56-59` выдаёт токен; нет blacklist, `token_version` или `logout`; frontend хранит токен в `localStorage`.
- **Воздействие:** украденный токен с общей машины, из XSS, расширения браузера или лога действует до семи дней и не отзывается после смены пароля.
- **Исправление:** access около 1 часа, rotating refresh cookie, `token_version`/server-side sessions, `POST /auth/logout`, отзыв при смене пароля.
- **Реестр:** `REC-007`.

### H-06 — HIGH: на `/login` и `/register` нет rate limiting

- **CVSS-подобная оценка:** **7.3/10**.
- **Файл/фрагмент:** `auth.py:16` и `:35`; нет IP/account throttling, backoff, lockout или abuse monitoring.
- **Воздействие:** brute-force паролей, массовая регистрация, автоматизированный спам и атаки на аккаунты подростков.
- **Исправление:** лимиты по IP + account identifier, exponential backoff, generic errors, метрики и алерты. Базовая настройка: login 5/min по паре IP+account, register 10/hour по IP/device с последующей настройкой по телеметрии.
- **Реестр:** `REC-008`.

### H-07 — HIGH: денежный workflow не является строгой state machine

- **CVSS-подобная оценка:** **8.0/10**.
- **Файлы/фрагменты:** `offers.py:244` не гарантирует единственный accepted offer; `offers.py:300-330` содержит dead check и DDL в request-path; `orders.py:248` допускает завершение по executor-пути без надёжной последовательности review/accept; `/users/me/transactions` (`users.py:126-140`) выводит операции из `status == completed`.
- **Воздействие:** двойное принятие офферов, преждевременное завершение и некорректные балансы/транзакции.
- **Исправление:** DB-backed state machine, один accepted offer, `submit → review → accept/revision`, row locks, idempotency keys, атомарные денежные операции; убрать DDL из HTTP-запросов.
- **Реестр:** `REC-009`.

### H-08 — HIGH: возраст и parental consent не являются контролями доступа

- **CVSS-подобная оценка:** **8.0/10** — системный safety/compliance-риск.
- **Файл/фрагмент:** `backend/app/schemas/user.py:11` — `age: Optional[int] = Field(None, ge=14, le=18)`. Ограничение применяется только если клиент прислал значение; заказ/оффер/оплата возраст не проверяют. Поиск `consent/parent/guardian` не выявил сущность, workflow или флаг parental consent.
- **Воздействие:** пользователь может зарегистрироваться без возраста, взрослый может не декларировать возраст, paid-flow не требует подтверждения возраста или согласия законного представителя.
- **PoC:** в staging зарегистрировать аккаунт с пропущенным `age`, затем пройти тестовый paid-flow; отсутствие серверного отказа подтверждает bypass.
- **Исправление:** определить политику возраста с юристами/product, сделать проверку server-side, добавить `parental_consents` (`user_id`, guardian identity/contact, scope, proof, granted/revoked timestamps), гейтить платные и социальные функции.
- **Реестр:** `REC-010`.

### H-09 — HIGH: нет модерации общения и anti-grooming controls

- **CVSS-подобная оценка:** **8.2/10** для площадки несовершеннолетних.
- **Файлы/фрагменты:** `messages.py:234-283` сохраняет текст без moderation; `schemas/message.py` не задаёт достаточный `max_length`; report/moderator/block/mute/takedown endpoint-ы не обнаружены.
- **Воздействие:** можно передавать телефоны, email, URL, `t.me`, `wa.me`, VK и другой контакт, уводить подростка вне платформы, спамить и избегать контроля.
- **Исправление:** content screener с `moderation_queue`, report/takedown, moderator role, block/mute, retention evidence, rate/size limits. Фильтр должен создавать review signal, а не безвозвратно удалять сообщение без процедуры.
- **Реестр:** `REC-012`, `REC-022`.

### H-10 — HIGH: JWT WebSocket передаётся и логируется в query string

- **CVSS-подобная оценка:** **7.1/10**.
- **Файлы/фрагменты:** frontend `App.js:390-392` строит и логирует `?token=...`; `websocket.py:27-35` принимает query token; `websocket.py:16-17` печатает query params и headers.
- **Где утечёт:** browser console/history, journald, proxy/CDN access logs, мониторинг и скриншоты общей машины.
- **PoC:** подключиться в staging тестовым JWT и проверить browser console и service log; токен должен быть виден в текущей реализации.
- **Исправление:** убрать credential-bearing logs; для браузера использовать short-lived single-use WebSocket ticket, для не-browser клиентов — Authorization header; очистить старые логи по политике retention.
- **Реестр:** `REC-013`.

### H-11 — HIGH: загрузка файла целиком буферизуется в RAM

- **CVSS-подобная оценка:** **7.5/10**.
- **Файлы/фрагменты:** `files.py:44-45` — `contents = await file.read()` до проверки размера; похожий путь есть в avatar update в `users.py` примерно около строки 95.
- **Воздействие:** один большой body или несколько concurrent upload могут вызвать OOM и падение backend.
- **Исправление:** читать чанками, останавливать после лимита, выставить nginx `client_max_body_size`, quotas и monitoring.
- **Реестр:** `REC-005`.

### H-12 — HIGH: backend/frontend dependencies имеют advisory и EOL-компоненты

- **CVSS-подобная оценка:** **7.0/10 aggregate**, точная эксплуатируемость зависит от reachability кода и runtime.
- **Артефакты:** `audits/2026-09-05_pip_osv.json`, `audits/2026-09-05_npm_osv.json`.
- **Backend:** OSV-выгрузка указала advisory для `python-multipart==0.0.6`, transitive `starlette==0.27.0`, `python-jose==3.3.0`, transitive `ecdsa`, `fastapi==0.104.1`, `h11` и `python-dotenv`. Среди ключевых записей аудита: CVE-2024-24762, CVE-2024-47874, CVE-2024-33663 и CVE-2024-33664.
- **Frontend:** `package.json` не разделяет runtime и dev dependencies; CRA toolchain и testing packages попадают в production scope; `react-scripts` 5.0.1 — EOL. OSV/npm-отчёт содержит advisories для axios, webpack-dev-server, node-forge, postcss, ws, serialize-javascript, shell-quote, `http-proxy-middleware`, rollup, lodash и qs.
- **Ограничение проверки:** локальный `pip-audit -r` не выполнился из-за сборки старых `pydantic-core` на Termux/Python 3.14; вместо него использован OSV querybatch. Перед релизом повторить `pip-audit` в CI/Linux и `npm audit` по lockfile.
- **Исправление:** обновить FastAPI/Starlette/multipart совместным tested-блоком, заменить/пересмотреть `python-jose`, разделить `devDependencies`, мигрировать с CRA на поддерживаемый bundler, закрепить audit в CI.
- **Реестр:** `REC-015`.

---

## Средние и низкие находки

### M-01 — MEDIUM: MIME type доверяется заголовку клиента

- **Файл/фрагмент:** `files.py:36-38` проверяет `file.content_type`; расширение берётся из client-controlled filename.
- **Риск:** бинарный/исполняемый файл можно отправить с `Content-Type: image/png`. Текущий download принудительно отдаёт `application/octet-stream`, что снижает stored-XSS-риск, но не делает байты безопасными.
- **Fix:** magic bytes, согласование detected type и extension, узкий allowlist, size/quota и malware scanning при необходимости.
- **Реестр:** `REC-017`.

### M-02 — MEDIUM/LOW: нет явной path containment-проверки

- **Файл/фрагмент:** `files.py:70,92` строит `UPLOAD_DIR / filename` без `resolve()` и проверки принадлежности каталогу.
- **Сегодня:** server-generated UUID делает write-side traversal маловероятным, а текущий single-segment route converter ограничивает обычный `../` payload.
- **Риск:** route refactor на `{filename:path}` или изменение framework behavior может превратить это в arbitrary-file read/delete.
- **Fix:** запретить absolute path, `..`, null byte и separators; `candidate.resolve()` + `candidate.is_relative_to(UPLOAD_DIR.resolve())`; лучше использовать opaque DB key.

### M-03 — MEDIUM: API раскрывает абсолютный filesystem path

- **Файл/фрагмент:** `files.py:70` возвращает `"file_path": str(file_path)`.
- **Риск:** раскрывается layout сервера и создаётся ненужная зависимость клиента от filesystem.
- **Fix:** возвращать только opaque file ID, URL или signed URL.
- **Реестр:** `REC-004`.

### M-04 — MEDIUM: анонимно скрейпятся имена и портфолио подростков

- **Файлы:** `portfolio.py:28` — public item read; `portfolio.py:13-17` — произвольный `user_id`; `community.py:220-246` — comments с `user_name`; public post endpoints также возвращают реальные имена.
- **Риск:** профилирование по именам, аватарам, статистике и пользовательскому контенту.
- **Fix:** privacy-safe display name, опубликованные элементы отделить от private, private work авторизовать, real name убрать из public DTO.
- **Реестр:** `REC-011`, `REC-021`.

### M-05 — MEDIUM: `UserResponse` слишком широк для публичной сериализации

- **Файлы:** `backend/app/schemas/user.py:6-37` содержит `phone`, nullable `age`, `role`, `is_active`, `balance`, `tf_coins`; `UserProfileResponse` (`:39-64`) содержит plaintext `inn`; модель хранит `inn` в `models/user.py:49-63`.
- **Что проверено:** `password_hash` в reviewed response schema не входит — это хорошо; cross-user endpoint с `inn` не найден, profile path scoped к `/users/me`.
- **Риск:** широкая `UserResponse` может случайно попасть в list/relationship endpoint и раскрыть phone, age, role, balance, coins; `inn` возвращается владельцу без маскирования и шифрования.
- **Fix:** отдельные `PublicUserResponse`, `PrivateUserResponse`, `AdminUserResponse`; public DTO не содержит phone/age/balance/coins/verification; `inn` — write-only/masked/encrypted-at-rest и только для payout.
- **Реестр:** `REC-024`.

### M-06 — MEDIUM: WebSocket не проверяет `is_active`, manager in-memory

- **Файлы:** `websocket.py:60-77` проверяет token/user, но не отклоняет `is_active=False`; `websocket_manager.py` хранит `Dict[int, Set[WebSocket]]` в памяти процесса.
- **Риск:** деактивированный аккаунт остаётся подключённым до exp; multi-worker fan-out ломается, restart теряет соединения.
- **Fix:** проверять `is_active`, закрывать stale sockets; при нескольких workers использовать Redis pub/sub или другой shared event layer.
- **Реестр:** `REC-013`, `REC-023`.

### M-07 — MEDIUM/HIGH: нет лимитов WebSocket и сообщений

- **Файлы:** `websocket.py:88-97` — нет token bucket, frame cap и socket cap; `messages.py:234` — нет sender/recipient throttle; `MessageCreate` не ограничивает размер.
- **Риск:** spam, harassment, memory/storage DoS и тысячи сокетов на одном токене.
- **Fix:** REST limits per sender/pair, `content max_length`, WS около 5 msg/s с burst 10, frame ≤64 KB, ≤5 sockets/user, daily pair quota.
- **Реестр:** `REC-022`.

### M-08 — MEDIUM: CORS допускает опасную конфигурацию wildcard + credentials

- **Файлы:** `main.py:14-20` — `allow_credentials=True`; `config.py:20-24` принимает env, включая `*`; methods/headers wildcard.
- **Риск:** сегодня localStorage bearer снижает классический CSRF-риск, но при появлении cookie auth любой origin сможет получить credentialed CORS.
- **Fix:** fail-fast validator против `*`, non-empty explicit allowlist, явные methods/headers.
- **Реестр:** `REC-016`.

### M-09 — MEDIUM: production compose использует dev-поведение и root

- **Файлы:** `docker-compose.yml:28-30` запускает `alembic upgrade head` и `uvicorn --reload` при старте с bind mount; Dockerfile не задаёт non-root `USER`; `main.py:29-31` выполняет startup DDL; `entrypoint.sh` — только `exec "$@"`, автоматического seeding не обнаружено.
- **Риск:** unattended schema changes, mutable source, reload и root-level impact; миграция enum уже приводила к несовместимым uppercase/lowercase значениям.
- **Fix:** immutable prebuilt image, non-root, migration release gate, убрать `--reload`/bind mount и request/startup DDL; `fix_enum_cases.py` — явный проверяемый этап после миграции.
- **Реестр:** `REC-016`.

### M-10 — MEDIUM/LOW: auth/input hygiene

- **Файлы:** `auth.py:23-27` — email enumeration; `crud/user.py:37-44` — timing difference для неизвестного пользователя; `schemas/user.py:12` — нет max byte length; `security.py` содержит неиспользуемый passlib; `schemas/user.py:6` позволяет клиенту выбрать `role`.
- **Отдельный bcrypt-риск:** bcrypt учитывает только первые 72 байта; без валидатора длинный пароль может молча обрезаться.
- **Fix:** generic errors + dummy hash verification, отклонять пароль длиннее 72 UTF-8 bytes или перейти на современную схему, удалить dead passlib, назначать role server-side.
- **Реестр:** `REC-015`.

### M-11 — LOW/MEDIUM: неограниченная пагинация и hard-coded limit

- **Файлы:** `messages.py:141` принимает `limit` без верхнего предела; `users.py` использует `.limit(50)` для transactions.
- **Fix:** `Query(100, ge=1, le=500)`, cursor pagination и централизованные лимиты.
- **Реестр:** `REC-014` и deep-dive D2.

### M-12 — LOW/MEDIUM: debug logging и отсутствие единой redaction policy

- **Файлы:** `config.py:57-59`, `security.py:63-67`, WebSocket-модули используют `print()`; WebSocket-вариант повышен до H-10 из-за credentials.
- **Fix:** structured logging, redaction, retention/access controls и regression test на отсутствие токенов/PII в логах.

### M-13 — LOW/MEDIUM: dead-check в order workflow

- **Файл:** `orders.py:442` сравнивает status так, что проверка review не срабатывает.
- **Fix:** сравнивать нормализованный enum/status и покрыть переходы state-machine тестами.

### M-14 — INFO: SQL injection в проверенных ORM-путях не найден

- **Файл:** `crud/order.py:113-124` передаёт search через параметризованный `ilike()`, а не конкатенацию SQL.
- **Оговорка:** `%` и `_` могут менять семантику wildcard-поиска; это не подтверждённая SQL injection.

---

## Специфика «подростковой» аудитории — комплаенс-риски

Юридические требования зависят от страны, возраста, вида оплаты и модели обработки данных; этот блок обозначает технические gaps для обязательной проверки product/legal/safeguarding специалистами.

### 1. Возраст не подтверждается и не гейтит paid-flow

`age` nullable и self-declared. Ограничения Pydantic действуют только при наличии поля. Нет проверенного age lifecycle и серверного контроля перед созданием paid order, принятием offer или завершением работы.

### 2. Нет parental/guardian consent

Отсутствует запись, фиксирующая кто дал согласие, на что, когда, каким способом, с каким доказательством и когда согласие отозвано. Consent не должен быть декоративным профилем — он должен влиять на доступ к платным и социальным функциям.

### 3. Публичная идентификация и профилирование

Real names, avatars, portfolio, community comments и activity statistics могут собираться анонимно. Рекомендуется pseudonymous display identity, private-by-default visibility, минимизация полей и запрет выдачи балансов/age/phone/verification в public DTO.

### 4. Чувствительные персональные данные

`UserProfile.inn` хранится и возвращается plaintext в self-profile response. Даже при отсутствии найденного cross-user IDOR поле нужно шифровать at rest либо не собирать до проверенного payout; в API — маскировать (`****last4`) или делать write-only. `phone` и `age` не должны попадать в публичные списки.

### 5. Grooming, off-platform contact и harassment

Messages/WebSocket не имеют screening, report, block/mute, moderator и takedown процесса. Телефоны, email, URL и мессенджеры проходят без фильтра. Для площадки, где взрослый заказчик общается с подростком, это самостоятельный high-risk safeguarding gap.

### 6. Нет полноценного data-subject lifecycle

Не найден однозначный self-service account deletion, export, retention schedule и anonymization workflow для профилей, сообщений, файлов, заказов и аудиторских записей. Нужны политики хранения, удаления, legal hold и доступа к evidence.

### Минимальный safeguarding gate до возобновления paid activity

1. утверждённая age policy и server-side age verification;
2. parental consent там, где это требуется законом;
3. moderator/report/block/takedown workflow;
4. контроль телефонов, email и off-platform links;
5. TLS, private-by-default files/profiles и token hardening;
6. incident response, retention, deletion и evidence-access procedures.

---

## Roadmap исправлений

Оценка: **S** — до одного рабочего дня; **M** — несколько дней; **L** — примерно 1–3 недели с миграциями, тестированием и review.

### P0 — quarantine до реальных платных операций

| Приоритет | Работа | Находки | Оценка | Критерий приёмки |
|---|---|---|---:|---|
| P0.1 | Убрать placeholder secret, сгенерировать per-env key, ротировать токены | C-01 | S | Без ключа сервис не стартует; forged-token тест даёт 401; старые токены недействительны |
| P0.2 | HTTPS/WSS и security headers | C-02 | M | API/frontend/WS используют TLS; HSTS/CSP/nosniff проверены |
| P0.3 | Закрыть PostgreSQL и убрать default credentials | C-04 | S | Публичного `5433` нет; internal Compose access работает; без password старт запрещён |
| P0.4 | Закрыть offers, orders/drafts, portfolio и files | C-03, H-01–H-03, M-04 | M | anonymous/cross-user tests дают 401/403/404; owner/counterparty matrix зелёная |
| P0.5 | Исправить message-read IDOR | H-04 | S | foreign message ID даёт 404 и не сериализует content |

**Release gate:** до прохождения P0.1–P0.5 в staging и повторной проверки production-конфигурации не принимать реальные деньги и не открывать неконтролируемое общение несовершеннолетних с заказчиками.

### P1 — первый security-релиз

| Приоритет | Работа | Находки | Оценка | Критерий приёмки |
|---|---|---|---:|---|
| P1.1 | Short-lived access, refresh rotation, logout, revocation | H-05 | M | logout/password change инвалидируют сессии; refresh replay отклоняется |
| P1.2 | Login/register throttling и abuse monitoring | H-06 | S/M | IP/account limits, backoff, metrics и alerts протестированы |
| P1.3 | Строгая payment/order state machine | H-07, M-13 | L | один accepted offer; review/accept sequence; idempotent balance effects; request-path DDL отсутствует |
| P1.4 | File ownership и безопасный upload service | H-02/H-03/H-11, M-01–M-03 | L | ownership FK, magic bytes, streaming, quotas, containment, signed URLs, нет filesystem paths в API |
| P1.5 | Age/consent/PII lifecycle | H-08, M-04/M-05 | L | age/consent gates, masked/encrypted PII, safe DTOs, deletion/export/retention tests |
| P1.6 | Moderation, reports, block/mute и anti-flood | H-09, M-07 | L | report/takedown, screening, limits и moderator audit trail работают |
| P1.7 | Dependency upgrades и dev/prod separation | H-12 | L | `pip-audit`/`npm audit` в CI; поддерживаемый stack; CRA dev-server не используется как production server |
| P1.8 | Production container hardening | M-08/M-09/M-12 | M | нет wildcard credentialed CORS, reload/bind mount и root; migrations явные и наблюдаемые |

### P2 — resilience и hygiene

| Приоритет | Работа | Находки | Оценка | Критерий приёмки |
|---|---|---|---:|---|
| P2.1 | Shared WebSocket event layer | M-06 | M/L | multi-worker fan-out, reconnect и restart semantics протестированы |
| P2.2 | Bounded pagination и централизованные limits | M-11 | S | все list endpoints имеют верхний предел или cursor |
| P2.3 | Structured redacted logging и security regression suite | M-12 | S/M | токены/PII отсутствуют в логах; authz matrix запускается в CI |
| P2.4 | Privacy review public identity/content visibility | M-04/M-05 | M | public DTO содержат только утверждённые поля |

---

## Что сделано хорошо

1. **Параметризованные SQL-запросы.** В проверенных ORM/raw-SQL путях значения передаются как bound parameters. В частности, `crud/order.py:113-124` использует параметризованный `ilike()`. SQL injection в аудированных путях не найден.
2. **Ownership-checks в большинстве mutation endpoints.** `orders.py`, `offers.py`, `notes.py`, `portfolio.py` и `community.py` обычно проверяют `resource.owner_id != current_user.id` до изменения/удаления и возвращают `403`. Особенно чистый пример — `notes.py:59-64` и `:81-86`.
3. **Скоупинг `/users/me/*`.** Профиль, skills, transactions и другие личные операции строятся от `current_user`, а не от произвольного owner ID.
4. **Разделение ролей `customer`/`executor`.** Роли явно присутствуют в модели, а order/offer actions различают стороны сделки. Это хорошая основа для усиления state machine; нужно только убрать client-controlled role assignment.
5. **Алгоритм JWT зафиксирован.** Проверка токена использует явный allowlist `HS256`, поэтому классическая `alg=none`/algorithm-confusion проблема в проверенном коде не обнаружена. Это не спасает от слабого `SECRET_KEY`, но сама настройка алгоритма безопаснее.
6. **Server-generated имена файлов.** При загрузке сохраняется UUID-derived имя, а не raw client filename. Это снижает write-side traversal-риск; остаются authz, magic bytes и containment.
7. **WebSocket identity binding ограничен.** После проверки токена соединение помещается в manager по аутентифицированному `user_id`; клиентского room/channel subscription API не найдено. Подписка на чужую комнату в текущем протоколе структурно не наблюдалась.
8. **Типизированные схемы и settings.** Pydantic и FastAPI validation уже используются. Основная проблема — критичные ограничения сделаны optional или неполными, а не полное отсутствие валидации.
9. **Alembic и операционная проверяемость.** Миграции существуют, а deployment checklist фиксирует порядок миграций и enum-case repair. Следующий шаг — сделать их release gates, а не бесконтрольными startup/request действиями.
10. **Аудитируемость исправлений.** Находки привязаны к файлам и фрагментам и сопоставлены с `REC-001`–`REC-024`, поэтому исправления можно проверять по конкретным acceptance criteria.

---

## Итоговая оценка

**Статус: Deployed, но security-недопустим для реальных платных операций и неконтролируемого общения несовершеннолетних.** Полная перепись не нужна: текущие роли, модели заказов и базовые authz-паттерны можно сохранить, добавив явные границы доступа, file ownership, state machine, safeguarding и privacy DTO. Немедленное решение — P0 quarantine до ротации `SECRET_KEY`, включения TLS, закрытия Postgres, защиты приватного чтения и исправления message/file IDOR.

### Канонические источники

- Подробный технический аудит: `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md`
- Реестр remediation: `docs_10/RECOMMENDATIONS.md` (`REC-001`–`REC-024`)
- Project roadmap: `ROADMAP.md`
- Security ADR: `decisions/ADR-002_security_remediation_plan.md`
- Project lessons: `LESSONS.md`
