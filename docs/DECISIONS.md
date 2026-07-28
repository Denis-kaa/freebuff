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
