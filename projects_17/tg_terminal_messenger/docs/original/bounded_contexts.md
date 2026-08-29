# BOUNDED CONTEXTS — tg-terminal-toolkit

> **Стадия:** 05 — Decomposer (AI System Decomposer v3.1.0)
> **Проект:** tg-terminal-toolkit
> **LISA:** 4.86 (MEDIUM)
> **Входы:** `brief.md`, `parsed_requirements.md`, `lisa_report.md`, `risk_manager_report.md`, `architect/report_v1.md`, `roadmap.md`
> **Дата:** 2026-08-02

---

## 1. System Decomposition Overview

**System Purpose:** Локальный терминальный Telegram-клиент (TUI) для Android/Termux: просмотр чатов, переписка, отправка текста и медиа через встроенный файловый менеджер, архивация истории переписок. User API (MTProto через Telethon), Bot API не используется.

**Decomposition Strategy:** Система разделена по зонам ответственности и границам владения данными, а не по технологическим слоям. Ключевой драйвер — **единственная внешняя интеграция (Telegram MTProto)**, которая изолируется за явным контрактом, и **строгое разделение UI-потока (Textual) от сетевого (Telethon)**, которое уже эмпирически потребовало threading-моста на Python 3.14.

**Main Architectural Boundaries:**
1. **UI ⇄ TG**: единственная точка интеграции — асинхронный мост `ThreadedTGClient` (Futures, а не прямые вызовы). Прямые обращения UI к Telethon запрещены.
2. **TG ⇄ Session**: клиент владеет Telethon, session-модуль владеет файлом `.session`, креденшелами и lifecycle (создание/восстановление/права 600).
3. **Domain data**: сообщения/чаты — транзитные данные через контракты (DTO-события), не общая mutable-память.
4. **Archive**: изолированный контекст экспорта/скачивания со своим хранилищем (SQLite/JSON/файлы).

**Critical Risks:**
- Threading-мост (workaround Python 3.14 + Textual) — наибольший интеграционный риск, требует чёткого shutdown-протокола.
- Хардкод креденшелов (api_id/api_hash/phone) прямо в `client.py` — нарушение NFR-005 (санитизация) и security-границы.
- `ui/app.py` 491 строка — риск god-module, требует разбивки по контекстам.
- `FloodWaitError` при массовой архивации — требует централизованного retry/backoff.

---

## 2. Modules

| # | Module | Type | Responsibility | Data Ownership | Inputs | Outputs | Dependencies | Parallelizable | Criticality |
|---|--------|------|----------------|----------------|--------|---------|--------------|----------------|-------------|
| M1 | `tg_session` | Security | Авторизация (телефон+2FA), lifecycle `.session`, права 600, восстановление | `.session` файл, api_id/api_hash, phone, 2FA state | phone, code, password, session_path | authorized: bool, session_file | — | ✅ (первый) | 🔴 Critical |
| M2 | `tg_gateway` | External Gateway | Обёртка Telethon: диалоги, сообщения, отправка, медиа, апдейты; FloodWait/retry; threading-мост | Нет своих данных (транзит) | команды (dialogs/messages/send/…) | Dialog[***REMOVED***, Message[***REMOVED***, futures | M1 | ✅ (после M1) | 🔴 Critical |
| M3 | `tui_delivery` | UI/Delivery | Textual TUI: ChatList, MessageView, FilePicker, оркестрация workers, Q_IN/Q_OUT | favorites.json, UI state (active_chat, messages cache) | клавиши, ввод, выбор файла | команды в M2, рендер | M2 (через мост), M4 (архив) | ✅ (после M2) | 🔴 Critical |
| M4 | `archive_storage` | Data | Экспорт истории JSON/SQLite, скачивание медиа в `./downloads/{chat_id***REMOVED***/`, прогресс | SQLite, downloads/, JSON-экспорты | chat_id, команды archive | файлы архива, progress tuples | M2, M5 | ✅ (параллельно M3) | 🟠 High |
| M5 | `async_utils` | Platform | retry-with-backoff, TokenBucket rate limiter, sanitize_log, таймауты | — (без состояния) | callable/data | обёрнутые вызовы, санитизированные логи | — | ✅ (первый) | 🟡 Medium |

---

## 3. Module Dependency Graph

```
M5 async_utils  (основание — без зависимостей)
      ▲
      │ sanitize, retry, rate-limit
      │
M1 tg_session ──► (Telethon internals) ──► Telegram MTProto
      ▲
      │ session path, авторизация
      │
M2 tg_gateway ──► Telegram MTProto
      ▲
      │ Future-мост (ThreadedTGClient)
      │
M3 tui_delivery ──► M2 ◄── M4 archive_storage
      │                │        ▲
      └── команды ─────┘────────┘
             (M3→M4: экспорт)
```

- **Bottleneck:** M2 `tg_gateway` — единственный путь к Telegram; от него зависят M3 и M4.
- **Coupling risks:** M3→M2 через Future-контракт (не через Telethon-типы напрямую — DTO/события). M3→M4 только для экспорта.
- **Циклов нет.** M4 не зависит от M3 (может работать из CLI-скрипта). M1 не знает о M3/M4.

---

## 4. Integration Topology

| From | To | Communication | Contract | Ownership | Failure Risk | Retry Strategy | Idempotency |
|------|----|---------------|----------|-----------|--------------|----------------|-------------|
| M3 | M2 | async (Future через `run_coroutine_threadsafe` + `wrap_future`) | `get_dialogs(limit)`, `get_messages(entity,limit)`, `send_message(entity,text)`, `get_me()` | M2 | Средний (threading-гонки на shutdown) | Нет на уровне моста (см. M2→TG) | Отправка — 1 раз по событию UI; повтор только по явному ретраю |
| M2 | M1 | sync/async вызов | `is_user_authorized()`, `start()`, session_path | M1 | Низкий | Нет | Не нужна |
| M2 | Telegram | MTProto (Telethon) | Telethon API | M2 | Высокий (FloodWait, сетевая нестабильность) | Exponential backoff + `asyncio.sleep(e.seconds)` | Чтение идемпотентно; отправка — нет (нужен UI-guard) |
| M3 | M4 | async | `export_chat(chat_id, dest)`, progress callback | M4 | Средний (долгие операции, дисковые ошибки) | Частичный (пропуск ошибок, continue) | Да (append/replace по индексу) |
| M4 | M2 | async | `get_messages(chat_id, offset_id)`, `download_media(msg, dest)` | M2 (данные), M4 (файлы) | Высокий (FloodWait при массовой загрузке) | retry_with_backoff | Чекпоинты по offset_id |

---

## 5. Development Sequencing

**Phase 1 — Foundation:** M5 `async_utils`, M1 `tg_session` (авторизация + сессия + права 600)
**Phase 2 — Core Domains:** M2 `tg_gateway` (ядро: диалоги/сообщения/отправка + FloodWait/retry)
**Phase 3 — Integrations:** M3 `tui_delivery` MVP (ChatList + MessageView + отправка текста через мост)
**Phase 4 — Orchestration:** M3 full (FilePicker, поиск, избранное, авто-обновление), M4 `archive_storage`
**Phase 5 — Delivery:** полировка, тесты (pytest), экспорт Markdown/HTML (FR-025), темы (FR-027)

**Critical Path:** M5 → M1 → M2 → M3 (чат-лист → переписка → отправка) → M3 (FilePicker → медиа) → M4 (архив)

**Parallelizable:**
- M4 можно вести параллельно с M3 (после стабилизации контракта M2).
- M5 и M1 — полностью параллельны (обе без зависимостей).

**Текущий статус кода:** M1 ✅ (авторизация, восстановление при `AuthKeyUnregisteredError`), M2 ✅ (TGClient + ThreadedTGClient, но без DTO-границы и централизованного rate limiter), M3 ⚠️ (работает, но `app.py` — монолит 491 стр., нет FilePicker, нет Q_IN-апдейтов), M4 ❌ (не начат), M5 ⚠️ (нет выделенного модуля — retry/backoff встроены в client частично).

---

## 6. Module Internal Structure

### M1 `tg_session`
- **Layers:** domain (lifecycle сессии: new → authorized → revoked) / application (use cases: start, restore, ensure_permissions) / infrastructure (Telethon auth API, файловый I/O)
- **Public API:** `connect() -> bool`, `start(phone, code_callback) -> bool`, `is_authorized() -> bool`, `session_file: Path`, `disconnect()`
- **Private:** креденшелы, код 2FA, права файла (chmod 600)
- **File Structure:** `src/telegram/session.py` (+ `auth.py` при росте)
- **Dependencies Direction:** наружу не зависит; внутрь — Telethon
- **Контракт с infra:** пароль/код не логируются (sanitize через M5)

### M2 `tg_gateway`
- **Layers:** application (команды: dialogs/messages/send/download) / infrastructure (Telethon client, threading-мост, rate limiter)
- **Public API:** `get_dialogs(limit)`, `get_messages(entity, limit)`, `send_message(entity, text)`, `get_me()`, `send_file(entity, path)`; threading: `connect_async()`, `get_dialogs_async()`, `shutdown()`
- **Private:** `TelethonClient` инстанс, `_run_loop`, `_submit`, обработка `FloodWaitError`/`AuthKeyUnregisteredError`
- **File Structure:** `src/telegram/client.py` (TGClient), `src/telegram/threaded.py` (ThreadedTGClient), `src/telegram/errors.py`
- **Dependencies Direction:** M2 → M1 (session), M2 → M5 (retry/rate-limit)
- **Точка расширения:** подписка на `NewMessage` события (сейчас отсутствует — апдейты не стримятся в UI)

### M3 `tui_delivery`
- **Layers:** application (оркестрация: workers, таймеры, Q_IN/Q_OUT) / infrastructure (Textual widgets, файл favorites.json)
- **Public API:** `TGApp.run()`, Screens (`ChatListScreen`, `ChatViewScreen`, `FilePickerScreen`), bindings
- **Private:** reactive state (`_tg`, `_tg_connected`, `_total_unread`), `favorites.json`, история поиска
- **File Structure:** `src/ui/app.py` (каркас+оркестрация) → разбить: `src/ui/screens/chat_list.py`, `src/ui/screens/chat_view.py`, `src/ui/screens/file_picker.py`, `src/ui/state.py`
- **Dependencies Direction:** M3 → M2 (через Future-мост), M3 → M4 (экспорт), M3 → M5 (асинхронные таймеры)
- **Контракт с M2:** только DTO (не Telethon-типы) — снизить coupling

### M4 `archive_storage`
- **Layers:** domain (модель экспорта: сообщение/медиа) / application (use cases: export_chat, download_media) / infrastructure (SQLite через aiosqlite, aiofiles, ФС)
- **Public API:** `export_chat(chat_id, dest_dir) -> AsyncIterator[progress***REMOVED***`, `download_media(msg, dest_dir) -> Path`
- **Private:** SQLite schema (messages/chats/media), папка `./downloads/{chat_id***REMOVED***/`
- **File Structure:** `src/storage/archive.py`, `src/storage/db.py`
- **Dependencies Direction:** M4 → M2 (данные), M4 → M5 (retry)

### M5 `async_utils`
- **Layers:** application (готовые утилиты)
- **Public API:** `@retry_with_backoff(max_retries=3, base_delay=1.0)`, `TokenBucket(rate, capacity)`, `sanitize_log(data) -> str`
- **Private:** внутренняя реализация (таймеры, re-паттерны)
- **File Structure:** `src/utils/async_helpers.py` (НЕ свалка: одна зона — async-resilience)
- **Dependencies Direction:** только stdlib

---

## 7. Architect Requirements

### M1 `tg_session`
- **Constraints:** креденшелы НЕ в коде (сейчас нарушено — вынести в env/config с sanitize); chmod 600 обязателен; NFR-004, NFR-005
- **Scaling:** N/A (одна сессия; multi-account — в будущем отдельный контекст)
- **Security:** запрет логирования кодов/паролей; права `600`
- **Integration:** только Telethon auth API
- **Extension Points:** смена сессии, multi-account (сериализация session_name)
- **Consistency:** единый источник правды для авторизации

### M2 `tg_gateway`
- **Constraints:** все сетевые операции асинхронны; NFR-001 (не блокировать UI), NFR-007 (авто-переподключение)
- **Scaling:** rate limit (TokenBucket) + FloodWait backoff; ленивая пагинация диалогов
- **Security:** не логировать содержимое сообщений; sanitize
- **Integration Constraints:** единая граница ошибок (FloodWait, сетевые, session-revoked); DTO на границе с M3
- **Extension Points:** апдейты (NewMessage) → publisher для M3
- **Consistency:** транзакционность не нужна (MTProto); идемпотентность чтения

### M3 `tui_delivery`
- **Constraints:** NFR-002 (отклик <100ms — никаких блокировок в event loop), NFR-003 (RAM <200MB — sliding window сообщений), NFR-006 (graceful shutdown)
- **Scaling:** виртуализация списков (Textual native), лимит 50 сообщений в памяти
- **Security:** санитизация вывода (не выводить секреты), безопасные пути FilePicker (защита от path traversal — ADR-003)
- **Integration Constraints:** только через мост M2; Q_IN/Q_OUT с maxsize (backpressure)
- **Extension Points:** темы (FR-027), превью изображений (FR-026), поиск по сообщениям (FR-022)
- **Consistency:** favorites.json — атомарная запись

### M4 `archive_storage`
- **Constraints:** NFR-003 (память при экспорте больших чатов), прогресс-бар (FR-021)
- **Scaling:** постраничная выгрузка (offset_id), лимит concurrent downloads
- **Security:** пути только внутри dest_dir; санитизация имён файлов
- **Integration Constraints:** FloodWait-safe (retry + паузы); продолжение после ошибок (FS-002)
- **Extension Points:** экспорт Markdown/HTML (FR-025)
- **Consistency:** чекпоинты по offset_id; идемпотентность append

### M5 `async_utils`
- **Constraints:** чистые функции/декораторы, без глобального состояния
- **Scaling:** параметризуемые тайминги
- **Security:** `sanitize_log` обязателен во всех логах (NFR-005)
- **Integration:** совместимость с asyncio и threads (thread-safe)

---

## 8. Dangerous Coupling & Risk Areas

| Area | Risk | Why It Happens | Consequences | Mitigation |
|------|------|----------------|--------------|------------|
| Threading-мост M2↔M3 | Гонки/зависание на shutdown; утечка event loop | Python 3.14: `connect()` виснет в loop Textual → костыль с отдельным потоком | UI фризит, несохранённые данные, висячие потоки | Строгий shutdown-протокол (`shutdown()` с таймаутами), мониторинг потоков |
| Креденшелы в коде | Утечка api_id/api_hash/phone | Захардкожены в `client.py` (строки 40-42) | Компрометация аккаунта | Вынести в env/config; sanitize; права 600 |
| God-module `ui/app.py` | Нарушение SRP, сложный рефакторинг | Вся оркестрация + экраны + state в одном файле | Ошибки при доработке, высокий coupling | Разбить на screens/state/workers (см. M3) |
| Прямые Telethon-типы на границе M3 | Coupling к внутренностям Telethon | `Dialog`, `Message` используются в UI напрямую | Любое обновление Telethon ломает UI | DTO/датаклассы на границе моста |
| Нет стрима апдейтов | Пропуск новых сообщений без ручного refresh | `get_messages` только по запросу | UI не live | `client.run_until_disconnected()`/event handler → Q_IN |
| `favorites.json` путь/race | Потеря избранного | Запись из нескольких мест | UX-деградация | Единый владелец (M3), атомарная запись |

---

## 9. Decomposition Quality Assessment

| Criteria | Status | Notes |
|----------|--------|-------|
| Независимая разработка модулей | ✅ | M1/M5 с Phase 1; M4 параллельно M3 |
| Независимое тестирование | ✅ | M1 (mock Telethon), M5 (unit), M4 (fixtures) |
| Понятные boundaries | ✅ | UI/TG/session/archive/utils — чёткие зоны |
| Минимальный coupling | ⚠️ | Прямые Telethon-типы в UI — требуется DTO |
| Нет cyclic dependencies | ✅ | Граф направленный, циклов нет |
| Нет god-modules | ⚠️ | `ui/app.py` 491 стр. — декомпозиция запланирована |
| Понятный ownership | ✅ | Таблица модулей, data ownership |
| Заменяемость модуля | ✅ | M2 заменяем (интерфейс моста), M5 чистый |
| Нет переусложнения | ✅ | 5 модулей для MEDIUM-проекта — адекватно |
| Внутренняя структура модулей | ✅ | Слои domain/application/infrastructure определены |

---

## ✅ Заключение для Architect

Готово к стадии **Developer**. Для каждого модуля определены: границы, владение данными, контракты, слои, зависимости, точки расширения и риски. Ключевые указания Developer'у:
1. Вынести креденшелы из кода (M1).
2. Разбить `ui/app.py` на screens/state/workers (M3).
3. Добавить DTO-границу между M3 и M2.
4. Реализовать M4 `archive_storage` (не начат).
