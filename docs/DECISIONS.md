# Decisions — Архитектурные решения Buffy Project

> **Последнее обновление:** 2026-07-28

---

## ADR-001: Model Gateway — единый API для вызова LLM

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 3 ROADMAP***REMOVED***(../docs/ROADMAP.md)

### Проблема
Оркестратор (FSM/DAG) мог планировать задачи, но не мог реально вызвать LLM. Каждый провайдер имеет разный API-формат, разные эндпоинты, разную аутентификацию. Нужен единый слой абстракции.

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: OpenAI SDK** (openai Python package) | Минимум кода, поддержка из коробки | Только OpenAI-совместимые API, нет Gemini/Ollama |
| **B: Model Gateway** (собственный) | Все провайдеры, full control, fallback | Больше кода |
| **C: LiteLLM** (open source) | Все провайдеры, готовое решение | Ещё одна зависимость, тяжелая |

### Решение
Выбран **вариант B**: собственный Model Gateway.
- **OpenAICompatibleProvider** — DeepSeek, OpenRouter, SambaNova, DashScope (один API-формат)
- **GeminiProvider** — отдельная реализация Google Gemini API
- **OllamaProvider** — локальный инференс через Ollama

### Ключевые решения

1. **KeyPool из `.keys/`** — ключи управляются существующей системой KeyPool с ротацией
2. **Graceful fallback** — 3 попытки: primary → смена ключа → модель fallback → error
3. **Capability routing** — интеграция с существующим SmartRouter
4. **EventBus** — model.called / model.fallback / model.cached события
5. **Никаких новых зависимостей** — используется уже установленный httpx

### Документация
- [model_gateway.py***REMOVED***(../scripts/model_gateway.py) — реализация
- [test_model_gateway.py***REMOVED***(../tests/test_model_gateway.py) — 27 тестов
- [ROADMAP.md***REMOVED***(ROADMAP.md) — Phase 3

---

## ADR-002: MCP Server — Pure Python vs Official SDK

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(../docs/ROADMAP.md)

### Проблема
Нужен MCP Server для интеграции Buffy с внешними AI-агентами (Claude, Gemini, OpenClaw).
Существующий `phone_mcp_server.py` использует официальный `mcp` Python SDK,
но пакет не установлен на Termux (`ModuleNotFoundError: No module named 'mcp'`).

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: Установить `mcp` SDK** | Готовые декораторы, типы | Внешняя зависимость, может не работать на Termux ARM64 |
| **B: Pure Python (JSON-RPC 2.0)** | Zero зависимостей, полная контроль, портативность | Больше кода, нужно вручную реализовать протокол |
| **C: Node.js MCP SDK** | Официальная поддержка | Node.js зависимость, не Python |

### Решение
Выбран **вариант B**: Pure Python MCP Server без внешних SDK.

MCP протокол — это JSON-RPC 2.0 over stdio. Реализация на Python stdlib
(json, asyncio, sys) достаточна и полностью портативна.

### Ключевые решения

1. **JSON-RPC 2.0** — стандартные error codes (-32700, -32600, -32601, -32602, -32603)
2. **Protocol version 2024-11-05** — стабильная версия MCP
3. **Lazy loading** — компоненты (ToolRegistry, KnowledgeEngine, MemoryEngine) загружаются при первом обращении
4. **Workspace-aware** — ToolRegistry использует workspace сервера, не хардкод
5. **EventBus интеграция** — mcp.server.initialized, mcp.tool.called, mcp.knowledge.searched
6. **Auto-discovery** — ToolRegistry инструменты автоматически становятся MCP tools
7. **Dynamic resources** — buffy://knowledge/{key***REMOVED***, buffy://memory/{level***REMOVED***/{key***REMOVED*** с pattern matching

### Архитектура

```
External Agent (Claude/Gemini/OpenClaw)
        ↓ stdin (JSON-RPC 2.0)
  BuffyMcpServer
  ├── tools/list → 12 tools (ToolRegistry + Knowledge + Memory + Session)
  ├── tools/call → execute via handler → JSON result
  ├── resources/list → 9 resources (documents + knowledge + memory)
  ├── resources/read → file content / JSON data
  ├── prompts/list → 3 prompts (context_resume, knowledge_search, task_start)
  └── prompts/get → formatted prompt text
        ↓ stdout (JSON-RPC 2.0)
External Agent
```

### Документация
- [mcp_server.py***REMOVED***(../scripts/mcp_server.py) — реализация (~600 строк)
- [test_mcp_server.py***REMOVED***(../tests/test_mcp_server.py) — 53 теста, 0 errors
- [ROADMAP.md***REMOVED***(ROADMAP.md) — Phase 4 (55% → 65%)

---

## ADR-003: MCP Streamable HTTP Transport — Pure Python ThreadingHTTPServer

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(ROADMAP.md), MCP 2025-03-26 spec

### Проблема
MCP-клиенты (Claude, Gemini, OpenClaw) требуют Streamable HTTP транспорт
(POST/GET/DELETE на single endpoint), а не только stdio. Спецификация MCP
2025-03-26 заменила устаревший HTTP+SSE транспорт на Streamable HTTP.

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: Установить `mcp` SDK** | Готовый Streamable HTTP | Внешняя зависимость, может не работать на Termux |
| **B: Pure Python `http.server`** | Zero зависимостей, stdlib, портативность | Больше кода, ручная реализация SSE |
| **C: Flask/FastAPI** | Удобный API | Тяжёлые зависимости, не для Termux |
| **D: aiohttp** | Async, SSE support | Внешняя зависимость |

### Решение
Выбран **вариант B**: Pure Python `http.server.ThreadingHTTPServer`.

### Ключевые решения

1. **Single endpoint `/mcp`** — POST (JSON-RPC), GET (SSE), DELETE (session)
2. **`McpSessionManager`** — thread-safe (`threading.Lock`), `uuid4` session IDs
3. **`Mcp-Session-Id` header** — генерируется при `initialize`, требуется для GET/DELETE
4. **`Mcp-Protocol-Version` header** — во всех ответах (2025-03-26)
5. **Origin validation** — `urlparse().hostname` check (защита от DNS rebinding)
6. **204 No Content** — без `Content-Length` (RFC 7230 §3.3.2)
7. **SSE heartbeat** — каждые 30s (`: heartbeat\n\n`)
8. **`protocol_version = HTTP/1.1`** — для keep-alive/SSE support
9. **`daemon_threads = True`** — clean shutdown при KeyboardInterrupt
10. **CLI: `--http --host 127.0.0.1 --port 8765`** — localhost binding по умолчанию

### Архитектура

```
External Agent (Claude/Gemini/OpenClaw)
        ↓ POST /mcp (JSON-RPC 2.0)
  McpHTTPRequestHandler
  ├── initialize → create session, return Mcp-Session-Id
  ├── tools/call → dispatch → JSON response
  ├── notifications → 202 Accepted
  └── batch → array of responses
        ↓
  GET /mcp (SSE stream)
  ├── Mcp-Session-Id required
  └── data: {notification***REMOVED***\n\n (with 30s heartbeat)
        ↓
  DELETE /mcp
  └── Mcp-Session-Id required → 204 No Content
```

### Документация
- [mcp_server.py***REMOVED***(../scripts/mcp_server.py) — McpSession, McpSessionManager, McpHttpServer, McpHTTPRequestHandler
- [test_mcp_server.py***REMOVED***(../tests/test_mcp_server.py) — 89 тестов (53 stdio + 10 session + 26 HTTP)
- [ROADMAP.md***REMOVED***(ROADMAP.md) — Phase 4 (65% → 70%)

---

## ADR-005: ContextManager Bridge for termux-ai-agent

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** Интеграция локального агента с freebuff ContextManager (SPEC.md, v4.0)

### Проблема
`termux-ai-agent` не сохранял историю диалогов между запусками. После OOM-kill или перезапуска TUI контекст терялся.

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A. JSON-лог в termux-ai-agent** | Просто | Нет суммаризации, чекпоинтов, RAG |
| **B. Своя SQLite в termux-ai-agent** | Контроль | Дублирование ContextManager |
| **C. Reuse freebuff ContextManager** | Единый source of truth, авто-конспекты, checkpoints | Требует sys.path манипуляций |

### Решение
Выбран **вариант C**: `scripts/agent_context_bridge.py` как singleton-мост. Он:
- восстанавливает/создаёт сессию при первом вызове;
- логирует `user`, `assistant`, `system` сообщения;
- делает авточекпоинт каждые 10 сообщений;
- сохраняет конспект через `auto_conspect()`.

### Ключевые решения
1. **Singleton** — несколько вызовов `run()` делят одну сессию.
2. **Graceful degradation** — ошибки freebuff не ломают `run()`.
3. **Lazy import** — `get_context_bridge()` создаёт bridge только при первом использовании.
4. **Compact response** — `log_assistant()` хранит только `status`, `tool`, `error`, `metrics`, не весь JSON.

### Документация
- [scripts/agent_context_bridge.py***REMOVED***(../scripts/agent_context_bridge.py)
- [tests/test_agent_context_bridge.py***REMOVED***(../tests/test_agent_context_bridge.py)
- [TASK.md***REMOVED***(../TASK.md)

---

## ADR-006: Lightpanda Headless Browser Integration

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** Phase 4, веб-автоматизация для Buffy

### Проблема
Для веб-автоматизации (скрапинг, поиск, тестирование) нужен headless-браузер. Chrome/Chromium слишком тяжёлые для Termux ARM64.

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A. Playwright/Chromium** | Зрелый API | >1 GB RAM, OOM-kill, сложная установка |
| **B. requests + BeautifulSoup** | Лёгкий | Не работает с JS-сайтами |
| **C. Lightpanda** | Лёгкий (123 MB), быстрый, Agent Mode, CDP, MCP | Beta, требует glibc/proot |

### Решение
Выбран **вариант C**: Lightpanda через `proot-distro Ubuntu`.

### Ключевые решения
1. **proot-distro Ubuntu** — предоставляет glibc без root на Android.
2. **Wrapper `.tools/lightpanda`** — делегирует вызовы в proot.
3. **Python-класс `LightpandaWorker`** — унифицированный API для скриптов и агента.
4. **Stateless subprocess** — каждый запрос = новый процесс, устойчив к OOM.
5. **CDP-сервер** — background `Popen` для Puppeteer/Playwright.

### Документация
- [docs/LIGHTPANDA_INTEGRATION.md***REMOVED***(LIGHTPANDA_INTEGRATION.md)
- [src/workers/lightpanda_worker.py***REMOVED***(../src/workers/lightpanda_worker.py)
- [scripts/install_lightpanda.sh***REMOVED***(../scripts/install_lightpanda.sh)
- [tests/test_lightpanda_worker.py***REMOVED***(../tests/test_lightpanda_worker.py)

---

## ADR-004: FastAPI Wrapper + Cloudflare Tunnel

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(ROADMAP.md), облачные агенты (Claude, Gemini)

### Проблема
`localhost:8765` недоступен для облачных агентов. MCP клиенты (Claude Desktop,
Gemini) нуждаются в публичном HTTPS endpoint. ThreadingHTTPServer из stdlib
не поддерживает async SSE streaming и не совместим с ASGI ecosystem.

### Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: ThreadingHTTPServer + cloudflared** | Zero deps, уже реализовано | Sync, блокирует event loop, нет async SSE |
| **B: FastAPI + uvicorn + cloudflared** | Async SSE, ASGI, проверенный стек | +2 зависимости (fastapi, uvicorn) |
| **C: FastAPI + Cloudflare Workers** | Serverless, масштабируемость | Требует Cloudflare Workers платный план |
| **D: Starlette (без FastAPI)** | Легковесный ASGI | Меньше экосистемы, нет auto-docs |

### Решение
Выбран **вариант B**: FastAPI + uvicorn + cloudflared.

FastAPI и uvicorn уже установлены на Termux. Cloudflared даёт публичный
HTTPS URL без port forwarding. Async SSE через `asyncio.Queue` совместим
с uvicorn event loop.

### Ключевые решения

1. **Async SSE через `asyncio.Queue`** — не `queue.Queue`, совместим с uvicorn
2. **`asyncio.to_thread()` для dispatch** — `_server.dispatch()` синхронный,
   нужен thread pool чтобы не блокировать event loop
3. **`McpAsyncSessionManager` с `asyncio.Lock`** — thread-safe для async context
4. **Cloudflare Tunnel через `subprocess.Popen`** — daemon thread читает stderr,
   парсит URL (`*.trycloudflare.com`)
5. **Origin validation через `urlparse().hostname`** — защита от DNS rebinding
6. **Module-scoped uvicorn fixture** в тестах — стартует сервер один раз,
   `http.client` для запросов (тот же паттерн что test_mcp_server.py)
7. **`asyncio.run()` в тестах** вместо deprecated `asyncio.get_event_loop()`
8. **CLI: `--fastapi` + `--tunnel`** в mcp_server.py — делегирует в mcp_fastapi.main()

### Архитектура

```
Cloud Agent (Claude/Gemini)
        ↓ HTTPS
  Cloudflare Tunnel (*.trycloudflare.com)
        ↓ HTTP
  uvicorn (ASGI, asyncio event loop)
        ↓
  FastAPI app (/mcp)
  ├── POST → _dispatch() → asyncio.to_thread(BuffyMcpServer.dispatch)
  ├── GET  → StreamingResponse(async event_stream())
  └── DELETE → McpAsyncSessionManager.delete_session()
```

### Документация
- [mcp_fastapi.py***REMOVED***(../scripts/mcp_fastapi.py) — FastAPI app + CLI + tunnel
- [test_mcp_fastapi.py***REMOVED***(../tests/test_mcp_fastapi.py) — 35 тестов
- [ROADMAP.md***REMOVED***(ROADMAP.md) — Phase 4 (70% → 75%)
