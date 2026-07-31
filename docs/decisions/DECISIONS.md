# Decisions — Архитектурные решения Buffy Project

> **Последнее обновление:** 2026-07-31
> 
> Этот файл больше не хранит ADR в одном месте. Каждое решение вынесено в отдельный журнал в [`docs/engineering-memory/decisions/`***REMOVED***(../engineering-memory/decisions/).

---

## Индекс архитектурных решений

| ID | Название | Дата | Статус | Ссылка |
|----|----------|------|--------|--------|
| ADR-007 | Vision 3.0 — AI Infrastructure Layer | 2026-07-29 | ✅ Принято | [ADR_001_Vision_3.0_AI_Infrastructure_Layer.md***REMOVED***(../engineering-memory/decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md) |
| ADR-001 | Model Gateway — единый API для вызова LLM | 2026-07-28 | ✅ Принято | [ADR_002_Model_Gateway.md***REMOVED***(../engineering-memory/decisions/ADR_002_Model_Gateway.md) |
| ADR-002 | MCP Server — Pure Python vs Official SDK | 2026-07-28 | ✅ Принято | [ADR_003_MCP_Server_Pure_Python.md***REMOVED***(../engineering-memory/decisions/ADR_003_MCP_Server_Pure_Python.md) |
| ADR-003 | MCP Streamable HTTP Transport — Pure Python ThreadingHTTPServer | 2026-07-28 | ✅ Принято | [ADR_004_MCP_HTTP_Transport.md***REMOVED***(../engineering-memory/decisions/ADR_004_MCP_HTTP_Transport.md) |
| ADR-004 | FastAPI Wrapper + Cloudflare Tunnel | 2026-07-28 | ✅ Принято | [ADR_005_FastAPI_Cloudflare.md***REMOVED***(../engineering-memory/decisions/ADR_005_FastAPI_Cloudflare.md) |
| ADR-005 | ContextManager Bridge for termux-ai-agent | 2026-07-28 | ✅ Принято | [ADR_006_ContextManager_Bridge.md***REMOVED***(../engineering-memory/decisions/ADR_006_ContextManager_Bridge.md) |
| ADR-006 | Lightpanda Headless Browser Integration | 2026-07-28 | ✅ Принято | [ADR_007_Lightpanda.md***REMOVED***(../engineering-memory/decisions/ADR_007_Lightpanda.md) |

---

## Почему разделение?

- **Единый источник правды:** индекс хранит ссылки, а полные ADR живут в Engineering Memory.
- **Повторное использование:** шаблоны Engineering Memory (`decision_journal.md`) обеспечивают единый формат.
- **Автоматизация:** drift-check и другие инструменты могут сканировать отдельные ADR без парсинга одного большого файла.

---

_См. также [Engineering Memory***REMOVED***(../engineering-memory/ARCHITECTURE.md) и [Project Book***REMOVED***(../engineering-memory/PROJECT_BOOK.md)_.
