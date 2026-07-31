# ADR-004: FastAPI Wrapper + Cloudflare Tunnel

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(../../vision/ROADMAP.md), облачные агенты (Claude, Gemini)

## Проблема

`localhost:8765` недоступен для облачных агентов. MCP клиенты (Claude Desktop, Gemini) нуждаются в публичном HTTPS endpoint. ThreadingHTTPServer из stdlib не поддерживает async SSE streaming и не совместим с ASGI ecosystem.

## Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: ThreadingHTTPServer + cloudflared** | Zero deps, уже реализовано | Sync, блокирует event loop, нет async SSE |
| **B: FastAPI + uvicorn + cloudflared** | Async SSE, ASGI, проверенный стек | +2 зависимости (fastapi, uvicorn) |
| **C: FastAPI + Cloudflare Workers** | Serverless, масштабируемость | Требует Cloudflare Workers платный план |
| **D: Starlette (без FastAPI)** | Легковесный ASGI | Меньше экосистемы, нет auto-docs |

## Решение

Выбран **вариант B**: FastAPI + uvicorn + cloudflared.

FastAPI и uvicorn уже установлены на Termux. Cloudflared даёт публичный HTTPS URL без port forwarding. Async SSE через `asyncio.Queue` совместим с uvicorn event loop.

## Ключевые решения

1. **Async SSE через `asyncio.Queue`** — не `queue.Queue`, совместим с uvicorn
2. **`asyncio.to_thread()` для dispatch** — `_server.dispatch()` синхронный, нужен thread pool чтобы не блокировать event loop
3. **`McpAsyncSessionManager` с `asyncio.Lock`** — thread-safe для async context
4. **Cloudflare Tunnel через `subprocess.Popen`** — daemon thread читает stderr, парсит URL (`*.trycloudflare.com`)
5. **Origin validation через `urlparse().hostname`** — защита от DNS rebinding
6. **Module-scoped uvicorn fixture** в тестах — стартует сервер один раз, `http.client` для запросов (тот же паттерн что test_mcp_server.py)
7. **`asyncio.run()` в тестах** вместо deprecated `asyncio.get_event_loop()`
8. **CLI: `--fastapi` + `--tunnel`** в mcp_server.py — делегирует в mcp_fastapi.main()

## Архитектура

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

## Документация

- [scripts/mcp_fastapi.py***REMOVED***(../../../scripts/mcp_fastapi.py) — FastAPI app + CLI + tunnel
- [tests/test_mcp_fastapi.py***REMOVED***(../../../tests/test_mcp_fastapi.py) — 35 тестов
- [ROADMAP.md***REMOVED***(../../vision/ROADMAP.md) — Phase 4 (70% → 75%)
