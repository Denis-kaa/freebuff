# Vision 3.0 — Карта компонентов

> **Дата:** 2026-07-29  
> **Версия:** 1.0.0  
> **Всего документов:** 11  
> **Всего спец/реализаций:** 9 спецификаций + 1 реализация  
> **Всего тестов реализации:** ~61 (Event Platform)

---

## 1. Сводная таблица

| # | Компонент | Статус | Документация | Реализация | Тесты | Зависимости |
|---|-----------|--------|--------------|------------|-------|-------------|
| 1 | **Vision 3.0** | ✅ Готово | `VISION_3.0.md` | — | — | — |
| 2 | **Architecture 3.0** | ✅ Готово | `ARCHITECTURE_3.0.md` | — | — | Vision 3.0 |
| 3 | **ADR 001** | ✅ Готово | `ADR_001_Vision_3.0_AI_Infrastructure_Layer.md` | — | — | Vision 3.0 |
| 4 | **Product Manifesto** | ✅ Готово | `PRODUCT_MANIFESTO.md` | — | — | Vision 3.0 |
| 5 | **Bootstrap Engine** | 🟡 Spec | `BOOTSTRAP_SPECIFICATION.md` | — | — | — |
| 6 | **Runtime Abstraction** | 🟡 Spec | `RUNTIME_ABSTRACTION_SPECIFICATION.md` | — | — | ModelGateway |
| 7 | **Policy Engine** | 🟡 Spec | `POLICY_ENGINE_SPECIFICATION.md` | — | — | — |
| 8 | **Capability Registry** | 🟡 Spec | `CAPABILITY_SPECIFICATION.md` | — | — | Policy Engine |
| 9 | **Bridge Platform** | 🟡 Spec | `BRIDGE_PLATFORM_SPECIFICATION.md` | Bridge Layer (v1) | 60 | MCP, ACP |
| 10 | **Event Platform** | ✅ Реализовано | `EVENT_PLATFORM_SPECIFICATION.md` | `freebuff_plugin/event/` | **61** | Event Bus |
| 11 | **Vision 3.0 MAP** | ✅ Создан | `VISION_3.0_MAP.md` (этот) | — | — | Все |

---

## 2. Компоненты по категориям

### Core (6 компонентов)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **Event Bus** | ✅ Production | `scripts/event_bus.py` — publish/subscribe, wildcard, SQLite лог, ~20 тестов |
| **Event Platform** | ✅ Реализовано | Event Store + Replay + Timeline + Audit + Pulse, 61 тест |
| **Context Manager** | ✅ Production | SQLite сессии, сообщения, чекпоинты, миграции (v3) |
| **Memory Engine** | ✅ Production | 4 уровня (session/project/knowledge/personal), SQLite, ~20 тестов |
| **Knowledge Engine** | ✅ Production | FTS5 + TF-IDF, авто-индексация через EventBus |
| **Graph Index** | ✅ Production | SQLite граф связей, поиск пути, кластеризация |
| **Bootstrap Engine** | 🟡 Spec | Идемпотентное развёртывание, self-check, drift detection |

### Extensions (7 компонентов)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **MCP Server** | ✅ Production | STDIO + Streamable HTTP, 15+ tools, 89 тестов |
| **MCP Client** | ✅ Production | Stdio + HTTP транспорты, auto-reconnect, 60 тестов |
| **Bridge Layer** | ✅ Production | MCP↔ACP трансляция, 4 MCP инструмента, 60 тестов |
| **ACP Protocol** | ✅ Production | Agent Collaboration Protocol, AgentRegistry, heartbeat |
| **Scenario Engine** | ✅ Production | YAML сценарии, 11 готовых, 83 теста |
| **Telegram Bot** | ✅ Production | `/scenarios list/apply/search`, 44 теста |
| **Runtime Abstraction** | 🟡 Spec | Адаптеры для freebuff/Claude/OpenClaw/Hermes/GPT-4o |
| **Policy Engine** | 🟡 Spec | Политики (YAML), fallback chain, cost limits |
| **Capability Registry** | 🟡 Spec | capability discovery, routing, scoring |
| **Bridge Platform** | 🟡 Spec | Reverse bridge, внешние MCP сервера |

### Labs (будущие)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **Collaboration** | 🔵 Концепт | **GAP: нет round-robin, task assignment, agent carousel.** ACP/Bridge = connectivity, не orchestration. См. [VISION_3.0.md***REMOVED***(VISION_3.0.md) раздел 2. |
| **Presence** | 🔵 Концепт | Online status, activity tracking |
| **Plugin SDK** | 🔵 Концепт | External plugin development kit |

---

## 3. Файловая структура

```
freebuff_plugin/
├── event/                          # Event Platform (реализовано)
│   ├── __init__.py                 # Типы (EventEntry, EventQuery, иконки)
│   ├── schema.sql                  # SQLite + FTS5 + триггеры
│   ├── store.py                    # EventStore (CRUD, FTS5, batch)
│   ├── replay.py                   # EventReplay (replay, rebuild)
│   ├── timeline.py                 # TimelineEngine (format, icons)
│   ├── audit.py                    # AuditEngine (decision, action, config)
│   └── pulse.py                    # PulseEngine (EventBus subscription)
├── bridge_layer.py                 # Bridge Layer (реализовано)
├── acp_protocol.py                 # ACP Protocol (реализовано)
├── mcp_client.py                   # MCP Client (реализовано)
├── mcp_server.py                   # MCP Server (+ 5 event tools)
├── scenario_engine.py              # Scenario Engine (реализовано)
├── scenarios/                      # 11 готовых сценариев
└── tgbot.py                        # Telegram Bot (реализовано)
```

```
docs/
├── VISION_3.0.md                   # Стратегическое видение
├── ARCHITECTURE_3.0.md             # Архитектурная ревизия
├── PRODUCT_MANIFESTO.md            # Открытая инфраструктурная платформа
├── ADR_001_Vision_3.0_AI_Infrastructure_Layer.md
├── BOOTSTRAP_SPECIFICATION.md      # Bootstrap Engine (spec)
├── RUNTIME_ABSTRACTION_SPECIFICATION.md  # Runtime API (spec)
├── POLICY_ENGINE_SPECIFICATION.md  # Policy Engine (spec)
├── CAPABILITY_SPECIFICATION.md     # Capability Registry (spec)
├── BRIDGE_PLATFORM_SPECIFICATION.md # Bridge Platform (spec)
├── EVENT_PLATFORM_SPECIFICATION.md  # Event Platform (spec)
└── VISION_3.0_MAP.md               # Этот файл (карта)
```

```
tests/
└── test_event_store.py             # 61 тест Event Platform
```

---

## 4. Статистика покрытия

### По компонентам

| Компонент | Spec | Тесты | Статус |
|-----------|------|-------|--------|
| **Event Bus** | ✅ | ~20 | 🟢 Production |
| **Event Store** | ✅ | 25 | 🟢 Реализовано |
| **Event Replay** | ✅ | 8 | 🟢 Реализовано |
| **Timeline** | ✅ | 9 | 🟢 Реализовано |
| **Audit** | ✅ | 6 | 🟢 Реализовано |
| **Pulse** | ✅ | 4 | 🟢 Реализовано |
| **Migration** | ✅ | 2 | 🟢 Реализовано |
| **Boundary** | ✅ | 4 | 🟢 Реализовано |
| **Integration** | ✅ | 4 | 🟢 Реализовано |
| **MCP tools** | ✅ | — | 🟢 Добавлены в MCP Server |

### По этапам Vision 3.0

| Этап | Статус | Что входит |
|------|--------|------------|
| **Этап 0: База** | ✅ Завершён | Docs: Vision 3.0, Architecture 3.0, ADR 001, Manifesto, MAP |
| **Этап 1: Infrastructure Core** | 🟡 Specs + Event реализация | Bootstrap Engine (spec), Event Platform (✅ реализация), Policy Engine (spec), Capability Registry (spec) |
| **Этап 2: Ecosystem** | 🟡 Specs | Bridge Platform (spec), Runtime Abstraction (spec) |
| **Этап 3: Collaboration** | 🔵 Концепт | Multi-agent, Presence, **CoWork** (см. [VISION_3.0.md***REMOVED***(VISION_3.0.md), раздел «Три режима работы») |
| **Этап 4: Intelligence** | 🔵 Концепт | Auto-optimization, learning |

---

## 5. Диаграмма зависимостей

```
VISION_3.0.md
  └── ARCHITECTURE_3.0.md
        ├── ADR_001
        ├── PRODUCT_MANIFESTO.md
        ├── BOOTSTRAP_SPECIFICATION.md
        ├── POLICY_ENGINE_SPECIFICATION.md ←── CAPABILITY_SPECIFICATION.md
        ├── RUNTIME_ABSTRACTION_SPECIFICATION.md ←── ModelGateway
        ├── BRIDGE_PLATFORM_SPECIFICATION.md ←── MCP + ACP
        └── EVENT_PLATFORM_SPECIFICATION.md
              └── freebuff_plugin/event/* (61 тестов) ←── Event Bus
                    └── MCP Server (5 инструментов)
```

---

## 6. Следующие шаги (приоритет)

| Приоритет | Компонент | Действие | Примерный объём |
|-----------|-----------|----------|-----------------|
| P0 | **Event Store → MCP tools** | ✅ Интегрировано | 5 tools |
| P0 | **Bootstrap Engine** | Реализация | 3 файла, ~50 тестов |
| P0 | **Cowork: Agent Carousel** | Реализация round-robin | 🔴 GAP — не реализовано |
| P1 | **Capability Registry** | Реализация | 3 файла, ~55 тестов |
| P3 | **Runtime Abstraction** | ✅ Реализовано (v4.9.0) | 60 тестов |
| P3 | **Bridge Platform (v2)** | Reverse bridge | 2 файла, ~36 тестов |
| P3 | **CLI / MCP tools** | buffy event search/timeline | ~5 тестов |

---

*Связанные документы: [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(../core/ARCHITECTURE_3.0.md), [EVENT_PLATFORM_SPECIFICATION.md***REMOVED***(../core/EVENT_PLATFORM_SPECIFICATION.md), [CHANGELOG.md***REMOVED***(../../CHANGELOG.md)*
