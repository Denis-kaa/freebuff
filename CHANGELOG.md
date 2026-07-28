# Changelog

> Все значимые изменения в проекте Freebuff фиксируются в этом файле.
> Формат: [Keep a Changelog***REMOVED***(https://keepachangelog.com/en/1.1.0/),
> версионирование: [Semantic Versioning***REMOVED***(https://semver.org/spec/v2.0.0.html).

---

## [2.7.0***REMOVED*** — 2026-07-28

### Добавлено
- **FastAPI обёртка для MCP Server** (`scripts/mcp_fastapi.py`) — Streamable HTTP через uvicorn:
  - Async SSE streaming через `asyncio.Queue` (не `queue.Queue`)
  - `_dispatch()` — обёртка через `asyncio.to_thread()` для не-blocking вызова `BuffyMcpServer.dispatch()`
  - McpAsyncSession (@dataclass) + McpAsyncSessionManager (asyncio.Lock)
  - Origin validation через `urlparse().hostname` (DNS rebinding protection)
  - CLI: `--host`, `--port`, `--tunnel` (Cloudflare Tunnel)
  - `_start_tunnel()` — запуск `cloudflared tunnel --url` в subprocess, парсинг stderr для URL
  - `_print_tunnel_config()` — вывод конфига для Claude Desktop / Gemini
  - Health check `GET /` → `{status, server, protocol, endpoint, transport***REMOVED***`
- **Cloudflare Tunnel интеграция:**
  - `python scripts/mcp_fastapi.py --tunnel` — автоматический запуск cloudflared
  - Публичный HTTPS URL: `https://xxx.trycloudflare.com/mcp`
  - Конфиг для Claude Desktop выводится в stderr при старте
  - Cleanup при Ctrl+C: `tunnel_proc.terminate()`
- **CLI интеграция в mcp_server.py:**
  - `--fastapi` флаг — делегирует запуск в `mcp_fastapi.main()`
  - `--tunnel` флаг — передаётся в `mcp_fastapi.main()` (требует `--fastapi`)
  - Guard: `--tunnel` без `--fastapi` → exit с ошибкой
- **35 тестов FastAPI** (`tests/test_mcp_fastapi.py`):
  - uvicorn в daemon thread + `http.client` (тот же паттерн что и test_mcp_server.py)
  - `_uvicorn_server` fixture (module-scoped) — стартует uvicorn один раз на модуль
  - POST: initialize, ping, notification, tools/list, resources/list, prompts/list, tools/call, batch, errors
  - DELETE: session, unknown session, missing session-id
  - GET: missing session-id, unknown session, SSE content-type (raw socket)
  - Origin validation: evil.com (403), localhost (200), no origin (200), localhost.evil.com (403)
  - Async session manager: 7 тестов через `asyncio.run()` (без pytest-asyncio dependency)

---

## [2.6.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streamable HTTP транспорт для MCP Server** — реализован согласно спецификации
  MCP 2025-03-26 (замена устаревшего HTTP+SSE транспорта):
  - `McpSession` (@dataclass) — session с notification_queue (Queue) для SSE
  - `McpSessionManager` — thread-safe менеджер сессий (Lock, uuid4, create/get/delete/push)
  - `McpHttpServer(ThreadingHTTPServer)` — daemon_threads=True для clean shutdown
  - `McpHTTPRequestHandler(BaseHTTPRequestHandler)` — single endpoint `/mcp`:
    - **POST**: JSON-RPC запросы → `application/json` или `202 Accepted` для notifications
    - **GET**: SSE stream (`text/event-stream`) с 30s heartbeat для server-to-client notifications
    - **DELETE**: termination session → `204 No Content` (без Content-Length per RFC 7230)
    - `Mcp-Session-Id` header — генерируется при `initialize`, требуется для GET/DELETE
    - `Mcp-Protocol-Version` header — во всех ответах
    - `_validate_origin()` — защита от DNS rebinding (urlparse hostname check)
    - Non-initialize POST с невалидным `Mcp-Session-Id` → 404
    - HTTP/1.1 protocol_version для keep-alive/SSE
  - CLI: `--http`, `--host` (default 127.0.0.1), `--port` (default 8765)
  - `BuffyMcpServer.run_http()` — запуск ThreadingHTTPServer
- **Обновление протокола:** `PROTOCOL_VERSION` 2024-11-05 → 2025-03-26
- **36 новых тестов** (`tests/test_mcp_server.py`):
  - `TestSessionManager` — 10 тестов (create, get, delete, push_notification, thread safety, uniqueness)
  - `TestHttpTransport` — 26 тестов с реальными HTTP запросами (http.client + raw socket для SSE):
    - POST: initialize, ping, tools/list, resources/list, prompts/list, tools/call, shutdown, batch,
      notification (202), unknown method, invalid JSON, wrong path, invalid origin (403),
      localhost origin, no origin, invalid session-id (404)
    - GET: without session-id (400), unknown session (404), wrong path (404),
      SSE stream с notification (raw socket test)
    - DELETE: terminates session (204), unknown session (404), without session-id (400),
      no Content-Length header (RFC 7230)
    - Mcp-Protocol-Version header в всех ответах

### Изменено
- `docs/ROADMAP.md`: Phase 4 обновлена — MCP Streamable HTTP добавлен (65% → 70%)
- `docs/DECISIONS.md`: ADR-003 — Streamable HTTP transport (pure Python ThreadingHTTPServer)

### Проверка
- 89 тестов mcp_server — **0 errors** (53 stdio + 10 session manager + 27 HTTP)
- Code review: 4 итерации, все issues исправлены

### Исправления по результатам code review (4 итерации)
1. `204 No Content` — убран `Content-Length: 0` (RFC 7230 §3.3.2)
2. Origin validation — `startswith()` → `urlparse().hostname` (защита от `localhost.evil.com`)
3. Mcp-Session-Id validation — non-initialize POST с невалидным session → 404
4. McpSession → `@dataclass` (консистентность с McpTool/McpResource/McpPrompt)
5. SSE stream test — переписан на raw socket (http.client блокировал на SSE без Content-Length)
6. Session TTL note — задокументировано отсутствие automatic cleanup

---

## [2.5.0***REMOVED*** — 2026-07-28

### Добавлено
- **Streaming для Model Gateway** — реализован real-time streaming для всех 3 провайдеров:
  - `OpenAICompatibleProvider.generate_stream()` — SSE format (`data: {json***REMOVED***`, `[DONE***REMOVED***` terminator,
    `delta.content` extraction). DeepSeek, OpenRouter, SambaNova, DashScope.
  - `GeminiProvider.generate_stream()` — `streamGenerateContent` endpoint с `alt=sse` параметром,
    `candidates[0***REMOVED***.content.parts[0***REMOVED***.text` extraction.
  - `OllamaProvider.generate_stream()` — newline-delimited JSON (`stream: true`),
    `message.content` extraction, `done` flag + usage в финальном chunk.
  - `ModelGateway.generate_stream()` — fallback между провайдерами при ошибке стрима
  - `_publish_stream_event()` — EventBus интеграция (`model.called` / `model.fallback` с `streaming=True`)
  - CLI: `generate-stream` команда с `--timeout` флагом
- **Рефакторинг провайдеров:**
  - `_build_body()` method extracted в OpenAICompatibleProvider, GeminiProvider, OllamaProvider
  - `_convert_messages()` method extracted в GeminiProvider
  - Устранено дублирование кода между `generate()` и `generate_stream()`
- **9 новых тестов streaming** (`tests/test_model_gateway.py`):
  - OpenAI SSE format parsing (content + [DONE***REMOVED***)
  - Gemini SSE format parsing (streamGenerateContent)
  - Ollama newline JSON parsing (stream: true, done flag, usage)
  - BaseProvider fallback streaming (без реального стриминга)
  - ModelGateway.generate_stream() с моком провайдера
  - Error handling (no model raises ValueError)
  - Edge cases: empty lines, invalid JSON skipping
  - StreamChunk with usage stats

### Проверка
- 36 тестов model_gateway — **0 errors** (включая 9 streaming тестов)

---

## [2.4.0***REMOVED*** — 2026-07-28

### Добавлено
- **MCP Server** (`scripts/mcp_server.py`) — Model Context Protocol server на чистом Python:
  - JSON-RPC 2.0 over stdio (без внешних SDK, `mcp` пакет не установлен на Termux)
  - **12 tools:** git, file, shell, sqlite, http (из ToolRegistry) + knowledge_search,
    memory_store, memory_retrieve, memory_list, session_status, context_resume, plugins_list
  - **9 resources:** buffy://manifest, buffy://roadmap, buffy://spec, buffy://changelog,
    buffy://task, buffy://inventory, buffy://decisions, buffy://knowledge, buffy://memory
  - **3 prompts:** context_resume, knowledge_search, task_start
  - Protocol version: 2024-11-05
  - Lazy loading компонентов (ToolRegistry, KnowledgeEngine, MemoryEngine, ContextManager)
  - EventBus интеграция (mcp.server.initialized, mcp.tool.called, mcp.knowledge.searched)
  - Workspace-aware: ToolRegistry использует workspace сервера, не хардкод
  - CLI: --status, --tools, --resources, --prompts, --call, --read, --async-mode
  - Интеграция с Claude / Gemini / OpenClaw через claude_desktop_config.json
- **Тесты MCP Server** (`tests/test_mcp_server.py`) — 51 тест, 0 errors:
  - JSON-RPC helpers (response, error, notification)
  - Initialize handshake (protocol version, capabilities, server info)
  - Tools: list, call (knowledge_search, memory CRUD, session_status, context_resume)
  - Resources: list, read (manifest, knowledge overview, memory overview)
  - Prompts: list, get (context_resume, task_start)
  - Error handling (unknown method, invalid params, notifications)
  - Batch requests, server status, dataclasses, ToolRegistry integration

### Изменено
- `docs/ROADMAP.md`: Phase 4 обновлена — MCP Server реализован (55% → 65%)

---

## [2.3.0***REMOVED*** — 2026-07-28

### Исправлено
- **Groq-валидатор в KeyPool:** Cloudflare на стороне Groq блокировал дефолтный
  `User-Agent: Python-urllib/3.x` (HTTP 403 / error 1010). Добавлен
  `hdrs.setdefault("User-Agent", "KeyPool/1.0")` в `validate_provider()`.
  Результат: Groq 0/6 → **6/6 валидных ключей**.
  Файл: `.keys/keypool.py`

### Изменено (4 проблемы системы)
- **Проблема 1 — StreamBridge интеграция:** Сообщения Buffy (user + assistant)
  теперь логируются в стрим-сессию через `buffy_stream_logger.py`. Активная
  сессия: `Buffy_chat_2026-07-28_192442`. За эту сессию залогировано 7+ сообщений.
- **Проблема 2 — Knowledge Engine наполнен:** `seed_knowledge.py --force`
  обновил 19 записей в MemoryLevel.KNOWLEDGE. FTS5 индекс: 27 документов.
  Включает: README, BUFFY.md, SPEC.md, ROADMAP, DECISIONS, AUDIT,
  ARCHITECTURE_REVIEW, SYSTEM_INVENTORY + 3 best-practice карточки.
- **Проблема 3 — EventBus активирован:** events.db была пуста (0 событий).
  Опубликовано 17 типов событий (system.startup, session.created, task.*,
  step.*, checkpoint.created, knowledge.*, agent.connected, model.*,
  tool.executed, plugin.enabled). Всего 55 событий, 3 активных подписчика.
- **Проблема 4 — Git инициализирован:** Настроен `user.name=Buffy`,
  `user.email=buffy@freebuff.local`. Первый коммит: 331 файл
  (feat: Freebuff/Buffy Project 2.0 — Agentic Platform & Knowledge OS).

### Проверка
- 439 тестов — **0 errors** (65.83 сек)
- Code review пройден

---

## [2.2.0***REMOVED*** — 2026-07-28

### Добавлено
- **Авто-индексация Knowledge Engine при сохранении в Memory Engine:**
  - `scripts/event_subscribers.py`: `auto_index_subscriber` получает `content` и `workspace_root` из события `memory.stored`
  - `scripts/memory_engine.py`: `MemoryEngine` автоматически подключается к дефолтному `EventBus` внутри проектного workspace; событие содержит полный `content` и `workspace_root`
  - `scripts/event_bus.py`: `get_default_event_bus()` — ленивая инициализация EventBus + подписчики
  - `scripts/bootstrap.py`: инициализация дефолтного EventBus при старте сессии
- **Наполнение Knowledge Memory:**
  - `scripts/seed_knowledge.py`: сохраняет ключевые документы проекта (`README.md`, `BUFFY.md`, `SPEC.md`, `docs/*.md` и др.) и best-practice карточки в `MemoryLevel.KNOWLEDGE`
  - Автоматический `rebuild_index()` после заполнения
- **Тесты:**
  - `tests/test_event_subscribers.py`: 4 теста на авто-индексацию и `checkpoint_logger`
  - `tests/test_seed_knowledge.py`: 3 теста на `seed_knowledge.py`

### Изменено
- `docs/ROADMAP.md`: Phase 2 отмечена как завершённая (100%)

## [2.0.0***REMOVED*** — 2026-07-28

### Добавлено
- **Система стриминга контекста v2.0:**
  - `scripts/stream_bridge.py` — мост для интеграции Buffy с stream_session
  - `scripts/context_manager.py`: CONTEXT_FULL триггер (порог 28K токенов)
  - `scripts/context_manager.py`: `_estimate_tokens()` — точная эвристика токенов
  - `scripts/context_manager.py`: `prune_abandoned()`, `auto_abandon_stale()` — GC
  - `scripts/context_manager.py`: `get_context_status()` — мониторинг контекста
  - `scripts/context_manager.py`: `SCHEMA_VERSION = 2` + система миграций
  - `scripts/stream_session.py`: `BackgroundWriter` — асинхронная запись в файлы
  - `scripts/stream_session.py`: адаптивный чекпоинт-интервал (20→50)
  - `scripts/stream_session.py`: `prune_streams()`, `prune_all()` — GC
  - `scripts/stream_session.py`: in-memory кэш счётчика сообщений
  - `scripts/bootstrap.py`: интеграция StreamBridge при старте сессии
- **Документация:**
  - `docs/TASK_TEMPLATE.md` — шаблон TASK.md для новых задач
  - `TASK.md` — файл текущей задачи (стриминг контекста v2.0)
  - `CHANGELOG.md` — этот файл

### Изменено
- `scripts/context_manager.py`: `add_message()` теперь принимает `token_count: int | None`
- `scripts/context_manager.py`: `get_messages()` сортирует ASC (старые→новые)
- `scripts/context_manager.py`: `_get_conn()` — timeout + busy_timeout
- `scripts/stream_session.py`: `log_message()` пишет в файлы асинхронно
- `docs/RULES.md`: добавлены TASK.md и CHANGELOG.md в обязательные документы

### Исправлено
- `scripts/context_manager.py`: удалены неиспользуемые импорты `re`, `time`

---

## [2.1.0***REMOVED*** — 2026-07-28

### Добавлено
- **Auto-Rollup при CONTEXT_FULL:**
  - `scripts/context_manager.py`: `_save_context_rollup()` — генерирует сжатый конспект при превышении порога токенов
  - Сохраняется в `context/context_full_rollup.md` для инжекта в новый контекст
  - Возвращается `rollup_path` в результате `add_message()` / `save_checkpoint()`
- `scripts/stream_session.py`: при CONTEXT_FULL чекпоинте выводится путь к rollup

---

## [1.0.0***REMOVED*** — 2026-07-27

### Добавлено
- **ContextManager:** SQLite-хранилище сессий, сообщений, чекпоинтов
- **StreamSession:** непрерывная запись в файлы (conversation.log + raw.jsonl)
- **AutoConspect:** автосуммаризация при завершении сессии
- **FreebuffBridge:** мост для termux-ai-agent
- **Bootstrap:** восстановление контекста при старте сессии
- **SystemMonitor:** мониторинг RAM, CPU, батареи
- **FreebuffCLI:** 7 команд для управления системой
- **Cron:** автоматическая суммаризация каждые 30 минут
- **Тесты:** 15 тестов для ContextManager
- **Документация:** BUFFY.md, SPEC.md, RULES.md, SESSION_GUIDE.md, DECISIONS.md
