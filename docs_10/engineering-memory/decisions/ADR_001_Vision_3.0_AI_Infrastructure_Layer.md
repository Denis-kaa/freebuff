# ADR-007: Vision 3.0 — AI Infrastructure Layer

**Дата:** 2026-07-29
**Статус:** ✅ Принято
**Контекст:** [VISION_3.0.md***REMOVED***(../../vision/VISION_3.0.md), [ADR_001_Vision_3.0_AI_Infrastructure_Layer.md***REMOVED***(../../decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md)

## Решение

Перейти от позиционирования «Companion Platform» к **«AI Infrastructure Layer»**.

Buffy — не агент, не фреймворк, не IDE. Это инфраструктурный слой между AI-агентами (Claude Code, Cursor, Codebuff, OpenClaw) и данными проекта.

## Ключевые изменения

1. **Позиционирование** — Companion Platform → AI Infrastructure Layer
2. **Core** — добавляются Bootstrap Engine, Policy Engine, Runtime Abstraction
3. **Extensions** — MCP Ecosystem, Bridge Platform, Scenario Engine
4. **Labs** — Collaboration, Presence, Plugin SDK (будущие)
5. **Принципы** — Runtime Agnostic, Provider Agnostic, Model Agnostic, Local First

## Полный ADR

Детальное обоснование, альтернативы (4 варианта), weighted decision matrix, roadmap перехода и риски — в [ADR_001_Vision_3.0_AI_Infrastructure_Layer.md***REMOVED***(../../decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md).

## Связанные ADR

- [ADR-001***REMOVED***(ADR_002_Model_Gateway.md) — Model Gateway
- [ADR-002***REMOVED***(ADR_003_MCP_Server_Pure_Python.md) — MCP Server (Pure Python)
- [ADR-003***REMOVED***(ADR_004_MCP_HTTP_Transport.md) — MCP Streamable HTTP Transport
- [ADR-004***REMOVED***(ADR_005_FastAPI_Cloudflare.md) — FastAPI Wrapper + Cloudflare Tunnel
- [ADR-005***REMOVED***(ADR_006_ContextManager_Bridge.md) — ContextManager Bridge
- [ADR-006***REMOVED***(ADR_007_Lightpanda.md) — Lightpanda Headless Browser
- [ADR-008***REMOVED***(ADR_008_Consolidation_Promt36_Canonical_Rules.md) — Канонические правила Workspace OS (promt36)
- [ADR-009***REMOVED***(ADR_009_Consolidation_Promt37_User_Choice_Override.md) — Правило 11 User-Choice Override (promt37)
- Индекс всех ADR: [DECISIONS.md***REMOVED***(../../decisions/DECISIONS.md)
