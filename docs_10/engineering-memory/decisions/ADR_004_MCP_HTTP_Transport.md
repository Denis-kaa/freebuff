# ADR-003: MCP Streamable HTTP Transport — Pure Python ThreadingHTTPServer

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(../../vision/ROADMAP.md), MCP 2025-03-26 spec

## Проблема

MCP-клиенты (Claude, Gemini, OpenClaw) требуют Streamable HTTP транспорт (POST/GET/DELETE на single endpoint), а не только stdio. Спецификация MCP 2025-03-26 заменила устаревший HTTP+SSE транспорт на Streamable HTTP.

## Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: Установить `mcp` SDK** | Готовый Streamable HTTP | Внешняя зависимость, может не работать на Termux |
| **B: Pure Python `http.server`** | Zero зависимостей, stdlib, портативность | Больше кода, ручная реализация SSE |
| **C: Flask/FastAPI** | Удобный API | Тяжёлые зависимости, не для Termux |
| **D: aiohttp** | Async, SSE support | Внешняя зависимость |

## Решение

Выбран **вариант B**: Pure Python `http.server.ThreadingHTTPServer`.

## Ключевые решения

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

## Архитектура

```
External Agent (Claude/Gemini/OpenClaw)
         POST /mcp (JSON-RPC 2.0)
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

## Документация

- [scripts_01/mcp_server.py***REMOVED***(../../../scripts_01/mcp_server.py) — McpSession, McpSessionManager, McpHttpServer, McpHTTPRequestHandler
- [tests_09/test_mcp_server.py***REMOVED***(../../../tests_09/test_mcp_server.py) — 89 тестов (53 stdio + 10 session + 26 HTTP)
- [ROADMAP.md***REMOVED***(../../vision/ROADMAP.md) — Phase 4 (65% → 70%)

## Связанные ADR

- [ADR-002***REMOVED***(ADR_003_MCP_Server_Pure_Python.md) — MCP Server (Pure Python)
- [ADR-004***REMOVED***(ADR_005_FastAPI_Cloudflare.md) — FastAPI Wrapper + Cloudflare Tunnel
- [ADR-007***REMOVED***(ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) — Vision 3.0
- Индекс всех ADR: [DECISIONS.md***REMOVED***(../../decisions/DECISIONS.md)
