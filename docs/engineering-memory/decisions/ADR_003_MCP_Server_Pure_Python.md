# ADR-002: MCP Server — Pure Python vs Official SDK

**Дата:** 2026-07-28
**Статус:** ✅ Принято
**Контекст:** [Phase 4 ROADMAP***REMOVED***(../../vision/ROADMAP.md)

## Проблема

Нужен MCP Server для интеграции Buffy с внешними AI-агентами (Claude, Gemini, OpenClaw). Существующий `phone_mcp_server.py` использует официальный `mcp` Python SDK, но пакет не установлен на Termux (`ModuleNotFoundError: No module named 'mcp'`).

## Альтернативы

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A: Установить `mcp` SDK** | Готовые декораторы, типы | Внешняя зависимость, может не работать на Termux ARM64 |
| **B: Pure Python (JSON-RPC 2.0)** | Zero зависимостей, полная контроль, портативность | Больше кода, нужно вручную реализовать протокол |
| **C: Node.js MCP SDK** | Официальная поддержка | Node.js зависимость, не Python |

## Решение

Выбран **вариант B**: Pure Python MCP Server без внешних SDK.

MCP протокол — это JSON-RPC 2.0 over stdio. Реализация на Python stdlib (json, asyncio, sys) достаточна и полностью портативна.

## Ключевые решения

1. **JSON-RPC 2.0** — стандартные error codes (-32700, -32600, -32601, -32602, -32603)
2. **Protocol version 2024-11-05** — стабильная версия MCP
3. **Lazy loading** — компоненты (ToolRegistry, KnowledgeEngine, MemoryEngine) загружаются при первом обращении
4. **Workspace-aware** — ToolRegistry использует workspace сервера, не хардкод
5. **EventBus интеграция** — mcp.server.initialized, mcp.tool.called, mcp.knowledge.searched
6. **Auto-discovery** — ToolRegistry инструменты автоматически становятся MCP tools
7. **Dynamic resources** — buffy://knowledge/{key***REMOVED***, buffy://memory/{level***REMOVED***/{key***REMOVED*** с pattern matching

## Архитектура

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

## Документация

- [scripts/mcp_server.py***REMOVED***(../../../scripts/mcp_server.py) — реализация (~600 строк)
- [tests/test_mcp_server.py***REMOVED***(../../../tests/test_mcp_server.py) — 53 теста, 0 errors
- [ROADMAP.md***REMOVED***(../../vision/ROADMAP.md) — Phase 4 (55% → 65%)
