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
