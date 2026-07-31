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
