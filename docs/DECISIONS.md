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
