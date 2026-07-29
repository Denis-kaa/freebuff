# ARCHITECTURE 3.0 — AI Infrastructure Layer

> **Версия:** 3.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Черновик (ревизия существующей архитектуры)  
> **Основание:** [VISION_3.0.md***REMOVED***(VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [IDEAS.md***REMOVED***(IDEAS.md)  

---

## 1. Архитектурная философия

### 1.1 Core / Extensions / Labs

Вся система делится на три слоя по степени зрелости и обязательности:

```
┌─────────────────────────────────────────────────┐
│  CORE — Минимальное ядро                        │
│  Обязательно для любого режима работы           │
│  Без Core — Buffy не работает                   │
├─────────────────────────────────────────────────┤
│  EXTENSIONS — Опциональные сервисы              │
│  Подключаются по профилю установки              │
│  Каждый extension — независимо тестируем        │
├─────────────────────────────────────────────────┤
│  LABS — Экспериментальные компоненты            │
│  Могут измениться, исчезнуть или стать Core     │
│  Не влияют на стабильность Core                │
└─────────────────────────────────────────────────┘
```

### 1.2 Принципы

1. **Core не зависит от Extensions и Labs** — ни один core-компонент не импортирует extension
2. **Extensions могут зависеть от Core** — но не друг от друга (горизонтальных связей нет)
3. **Labs могут зависеть от Core и Extensions** — но не наоборот
4. **Каждый компонент имеет единый интерфейс** — замена реализации не ломает систему
5. **Event Bus — единственная глобальная шина** — компоненты не вызывают друг друга напрямую

---

## 2. Layer Architecture

### 2.1 Общая схема компонентов

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CORE                                          │
│                                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐ │
│  │  Session       │  │  Project       │  │  Knowledge Platform          │ │
│  │  Platform      │  │  State         │  │                              │ │
│  │                │  │                │  │  ┌────────┐ ┌─────────────┐  │ │
│  │  ContextManager│  │  ContextBuilder│  │  │ Memory │ │ Knowledge   │  │ │
│  │  StreamSession │  │  Bootstrap     │  │  │ Engine │ │ Engine      │  │ │
│  │  StreamBridge  │  │                │  │  ├────────┤ ├─────────────┤  │ │
│  │  AutoConspect  │  │                │  │  │ Graph  │ │ Semantic    │  │ │
│  └────────────────┘  └────────────────┘  │  │ Index  │ │ Index       │  │ │
│                                           │  └────────┘ └─────────────┘  │ │
│  ┌────────────────┐  ┌────────────────┐  └──────────────────────────────┘ │
│  │  Event         │  │  Workflow      │                                    │
│  │  Platform      │  │  Engine        │  ┌──────────────────────────────┐ │
│  │                │  │                │  │  Policy Engine               │ │
│  │  Event Bus     │  │  Orchestrator  │  │                              │ │
│  │  Event Subscrs │  │  Tool Runtime  │  │  Capability Registry         │ │
│  │  Event Log     │  │  Model Gateway │  │  Policy Store                │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                            EXTENSIONS                                      │
│                                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐ │
│  │  MCP Ecosystem │  │  Bridge        │  │  AI Runtime                  │ │
│  │                │  │  Platform      │  │                              │ │
│  │  MCP Server    │  │                │  │  Runtime Installer           │ │
│  │  MCP Client    │  │  Bridge Layer  │  │  Runtime Doctor              │ │
│  │  MCP FastAPI   │  │  ACP Protocol  │  │  Adapter Layer               │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘ │
│                                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐ │
│  │  Provider      │  │  Scenario      │  │  OOM Protection              │ │
│  │  Infrastructure│  │  Engine        │  │                              │ │
│  │                │  │                │  │  oom_protect.sh              │ │
│  │  Provider Pool │  │  11 сценариев  │  │  Wrapper v4                  │ │
│  │  Key Pool      │  │  TG Bot        │  │  Monitor                     │ │
│  │  Model Pool    │  │  API (/scenario)│  │                              │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                              LABS                                          │
│                                                                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐ │
│  │  Collaboration │  │  Intelligence  │  │  Developer                   │ │
│  │                │  │                │  │  Ecosystem                   │ │
│  │  Presence      │  │  RAG 2.0       │  │                              │ │
│  │  Team Mode     │  │  Re-ranking    │  │  Plugin SDK                  │ │
│  │  Live Collab   │  │  HyDE          │  │  Workflow SDK                │ │
│  │  Project Pulse │  │  Agentic RAG   │  │  Policy Packs                │ │
│  └────────────────┘  └────────────────┘  └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Слои абстракции

```
┌─────────────────────────────────────────────┐
│  CLI / UI Layer                              │
│  freebuff_cli.py, Telegram Bot, API, Overlay │
├─────────────────────────────────────────────┤
│  Communication Layer                         │
│  MCP Server/Client, ACP, Bridge, Event Bus  │
├─────────────────────────────────────────────┤
│  Service Layer                               │
│  Orchestrator, AutoConspect, Drift Check    │
├─────────────────────────────────────────────┤
│  Data Layer                                  │
│  ContextManager, Memory, Knowledge, Graph   │
├─────────────────────────────────────────────┤
│  Storage Layer                               │
│  SQLite, JSON, filesystem                   │
└─────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Session Platform

| Компонент | Класс/Файл | Статус | Тесты |
|-----------|-----------|--------|-------|
| **ContextManager** | `scripts/context_manager.py` | ✅ Production | ~15 (в test_freebuff.py) |
| **StreamSession** | `scripts/stream_session.py` | ✅ Production | ❌ Нет отдельного теста |
| **StreamBridge** | `scripts/stream_bridge.py` | ✅ Production | ❌ Нет отдельного теста |
| **AutoConspect** | `scripts/auto_conspect.py` | ✅ Production | ✅ Есть тесты |
| **Bootstrap** | `scripts/bootstrap.py` | ✅ Production | ✅ Есть тесты |

**Зависимости:** Storage Layer (SQLite)

**Поток данных:**
```
User/Agent → StreamBridge → StreamSession → SQLite + Files
                │
                ▼
          AutoConspect → context/summaries/
                │
                ▼
          ContextManager → data/context.db
```

### 3.2 Knowledge Platform

| Компонент | Класс/Файл | Статус | Тесты |
|-----------|-----------|--------|-------|
| **Memory Engine** | `scripts/memory_engine.py` | ✅ Production | ~15 |
| **Knowledge Engine** | `scripts/knowledge_engine.py` | ✅ Production | 42 |
| **Graph Index** | `scripts/graph_index.py` | ✅ Production | 42 |
| **Semantic Index** | `scripts/graph_index.py` (SemanticIndex) | ✅ Production | 15 |
| **Seed Knowledge** | `scripts/seed_knowledge.py` | ✅ Production | ✅ |

**Зависимости:** Session Platform (ContextManager), Event Bus

**Поток данных:**
```
MemoryStore → Memory Engine (JSON)
                │
                ▼
       Knowledge Engine (FTS5 + TF-IDF)
                │
                ▼
       Graph Index (SQLite + BFS)
                │
                ▼
       Semantic Index (SVD)
```

### 3.3 Event Platform

| Компонент | Класс/Файл | Статус | Тесты |
|-----------|-----------|--------|-------|
| **Event Bus** | `scripts/event_bus.py` | ✅ Production | ~20 |
| **Event Subscribers** | `scripts/event_subscribers.py` | ✅ Production | 4 |
| **Event Log** | SQLite (`context/events.db`) | ✅ Production | — |

**События по категориям:**
- `system.*` — startup, shutdown, error
- `session.*` — created, completed, checkpoint
- `task.*` — created, completed, failed
- `step.*` — started, completed, failed, retrying
- `memory.*` — stored, deleted, cleared
- `knowledge.*` — indexed, searched, rebuilt
- `mcp.*` — server.initialized, tool.called, bridge.*
- `plugin.*` — enabled, disabled

### 3.4 Policy Engine (План)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| **Policy Store** | 💡 План | SQLite-хранилище политик |
| **Capability Registry** | 💡 План | Маппинг capability → модель |
| **Policy Executor** | 💡 План | Исполнение политик при каждом запросе |

**Структура политики (проект):**
```yaml
runtime: freebuff          # Какой Runtime использовать
provider: auto             # Провайдер (auto = по умолчанию)
model: auto                # Модель (auto = по capability)
capabilities:
  coding: deepseek-v4
  review: gpt-5
  research: gemini-2.5
  documentation: local-qwen
fallback:
  strategy: next-available
  max_retries: 3
cost_limits:
  daily: 5.00
  per_task: 0.50
```

### 3.5 Workflow Engine

| Компонент | Статус | Тесты |
|-----------|--------|-------|
| **Orchestrator** (FSM/DAG) | 🟡 MVP | 51 |
| **Tool Runtime** | ✅ Production | 50 |
| **Model Gateway** | ✅ Production | 36 |

**Зависимости:** Event Platform, Knowledge Platform

---

## 4. Extension Components

### 4.1 MCP Ecosystem

```
┌─────────────────────────────────────────┐
│          MCP Ecosystem                    │
│                                           │
│  ┌──────────────┐   ┌─────────────────┐  │
│  │ MCP Server   │   │  MCP Client     │  │
│  │ (scripts/)   │   │  (plugin/)      │  │
│  │              │   │                  │  │
│  │ stdio + HTTP │   │  StdioClient    │  │
│  │ 89 тестов    │   │  HTTPClient     │  │
│  └──────────────┘   └─────────────────┘  │
│                                           │
│  ┌──────────────┐   ┌─────────────────┐  │
│  │ MCP FastAPI  │   │  Phone MCP      │  │
│  │ (scripts/)   │   │  (scripts/)     │  │
│  │              │   │                  │  │
│  │ Cloudflare   │   │  8 tools: SMS,  │  │
│  │ Tunnel       │   │  camera, GPS    │  │
│  └──────────────┘   └─────────────────┘  │
└─────────────────────────────────────────┘
```

### 4.2 Bridge Platform

```
┌─────────────────────────────────────────────┐
│  Bridge Platform                              │
│                                               │
│  ┌────────────────┐  ┌────────────────────┐  │
│  │ ACP Protocol   │  │ Bridge Layer       │  │
│  │ (plugin/)      │  │ (plugin/)          │  │
│  │                │  │                    │  │
│  │ AgentRegistry  │  │ connect_mcp_stdio  │  │
│  │ ACPHandler     │  │ connect_mcp_http   │  │
│  │ send_task      │  │ _forward_to_mcp    │  │
│  │ heartbeat      │  │ _rpc_to_server     │  │
│  │ 60 тестов      │  │ sync_loop + recon  │  │
│  └────────────────┘  └────────────────────┘  │
│                                               │
│  ┌────────────────┐                           │
│  │ SDK Bridge     │                           │
│  │ (scripts/)     │                           │
│  │                │                           │
│  │ SmartRouter    │                           │
│  │ → termux-agent │                           │
│  └────────────────┘                           │
└─────────────────────────────────────────────┘
```

**Поток ACP сообщения:**
```
Agent A → Event Bus → ACPHandler(Agent B)
                          │
                    ┌─────┴─────┐
                    ▼           ▼
              Local Tool    Bridge Layer
                              │
                              ▼
                          MCP Client
                              │
                              ▼
                        External MCP Server
```

### 4.3 Scenario Engine

| Компонент | Файл | Статус | Тесты |
|-----------|------|--------|-------|
| **ScenarioEngine** | `freebuff_plugin/scenario_engine.py` | ✅ Production | 83 |
| **11 сценариев** | `freebuff_plugin/scenarios/*.md` | ✅ Production | — |
| **TG Bot** | `freebuff_plugin/tgbot.py` | ✅ Production | 44 |
| **API endpoints** | `freebuff_plugin/api.py` | ✅ Production | ❌ Нет тестов API |

### 4.4 Provider Infrastructure

| Компонент | Статус | Тесты |
|-----------|--------|-------|
| **ModelGateway** (6 провайдеров) | ✅ Production | 36 |
| **KeyPool** (ротация, валидация) | 🟡 Частично | ❌ Нет тестов |
| **Provider Pool** (OpenAI, Anthropic, DeepSeek, Gemini) | 💡 План | — |
| **Model Registry** | 💡 План | — |

### 4.5 OOM Protection

| Компонент | Статус |
|-----------|--------|
| **oom_protect.sh** — проверка MemAvailable, kill старых процессов | ✅ Production |
| **~/.local/bin/freebuff wrapper v4** — Фаза 0 OOM перед стартом | ✅ Production |
| **freebuff_plugin/monitor.sh** — мониторинг PID/PREFIX | ✅ Production |
| **freebuff_plugin/wrapper.py** — _run_oom_protection в launch() | ✅ Production |

---

## 5. Lab Components

### 5.1 Collaboration (План)

| Компонент | Статус | Зависимости |
|-----------|--------|-------------|
| **Presence System** | 💡 План | Event Bus, Session Platform |
| **Team Mode** | 💡 План | Session Platform, Policy Engine |
| **Live Collaboration** | 💡 План | Presence, Event Bus v2 |
| **Project Pulse** | 💡 План | Event Bus, UI |

### 5.2 Intelligence (План)

| Компонент | Статус | Зависимости |
|-----------|--------|-------------|
| **RAG 2.0** | 💡 План | Knowledge Platform |
| **Re-ranking** | 💡 План | Knowledge Engine |
| **HyDE** | 💡 План | Knowledge Engine, LLM |
| **Agentic RAG** | 💡 План | RAG 2.0, Orchestrator |

### 5.3 Developer Ecosystem (План)

| Компонент | Статус | Зависимости |
|-----------|--------|-------------|
| **Plugin SDK** | 💡 План | Plugin API |
| **Workflow SDK** | 💡 План | Orchestrator |
| **Policy Packs** | 💡 План | Policy Engine |

---

## 6. Data Flow Diagrams

### 6.1 Запрос пользователя → Ответ

```
User/Agent (через любой интерфейс)
    │
    ├── Telegram Bot (Extension) → Intent Router → freebuff CLI
    ├── REST API (Extension) → Intent Router → freebuff CLI
    ├── MCP Server (Core) → Tool Runtime → Knowledge/Memory
    └── ACP Handler (Extension) → Bridge Layer → external MCP
                            │
                            ▼
                      freebuff Agent (Codebuff)
                            │
                            ▼
                      StreamBridge → StreamSession
                            │
                            ▼
                      ContextManager (SQLite)
                            │
                            ▼
                      AutoConspect → summaries/
```

### 6.2 MCP Запрос (внешний агент)

```
External Agent (Claude/Cursor)
    │
    ▼
MCP Server (scripts/mcp_server.py)
    │
    ├── tools/list → список всех инструментов
    ├── tools/call → вызов инструмента
    │       │
    │       ├── knowledge_search → Knowledge Engine
    │       ├── memory_store → Memory Engine
    │       ├── bridge_connect → Bridge Layer → MCP Client
    │       ├── bridge_rpc → Bridge Layer → External MCP
    │       └── git/file/shell → Tool Runtime
    │
    └── resources/read → файлы проекта
```

### 6.3 ACP Сообщение (агент → агент)

```
ACP Agent A
    │
    ▼
Event Bus (scripts/event_bus.py)
    │
    ▼
ACP Handler Agent B
    │
    ├── Tool Handler → выполнение
    │       │
    │       ▼
    │   ACP Result → Event Bus → Agent A
    │
    └── Unknown Tool → ACP Error → Event Bus → Agent A
```

### 6.4 Bridge Layer (MCP ↔ ACP)

```
ACP → MCP:

    Agent A → send_task("buffy-bridge", "mcp.server_name.tool_name", args)
                │
                ▼
          Bridge Layer → _handle_acp_task_on_mcp
                │
                ▼
          _forward_to_mcp("server_name", "tool_name", args)
                │
                ▼
          MCP Client → call_tool("tool_name", args)
                │
                ▼
          External MCP Server → результат


MCP → ACP:

    MCP Client → list_tools()
                │
                ▼
          Bridge Layer → register_capability("mcp.server.tool", desc)
                │
                ▼
          ACP Registry → Agent "buffy-mcp" knows about tool
```

---

## 7. Component Dependency Matrix

```
                    Context     Stream    Memory  Knowledge  Graph   Event    Tool     MCP     Bridge   Plugin
                    Manager     Session   Engine  Engine     Index   Bus      Runtime  Server  Layer    API
ContextManager        ─          W          W        W         W       R        ─        R       ─        ─
StreamSession         W          ─          ─        ─         ─       W        ─        ─       ─        ─
Memory Engine         R          ─          ─        W         ─       W        ─        ─       ─        ─
Knowledge Engine      W          ─          R        ─         R       W        ─        ─       ─        ─
Graph Index           ─          ─          R        W         ─       W        ─        ─       ─        ─
Event Bus             ─          ─          ─        ─         ─       ─        W        W       W        W
Tool Runtime          ─          ─          ─        ─         ─       W        ─        W       ─        W
MCP Server            R          R          R        R         R       W        R        ─       ─        R
Bridge Layer          ─          ─          ─        ─         ─       R        ─        W       ─        ─
Plugin API            R          ─          ─        ─         ─       W        W        ─       ─        ─

R = Read (импортирует/использует)
W = Write (публикует/сохраняет)
─ = Нет прямой зависимости
```

---

## 8. Component Status Summary

| Категория | Всего | ✅ Prod | 🟡 MVP | 💡 План | ❌ Нет отдельного теста |
|-----------|-------|---------|--------|---------|-------------------------|
| **Core** | 12 | 10 | 1 (Orchestrator) | 1 (Policy Engine) | 3 (StreamSession, StreamBridge, KeyPool) |
| **Extensions** (вкл. Bridge Platform) | 14 | 10 | 2 | 2 | 2 (API, KeyPool) |
| **Labs** | 10 | 0 | 0 | 10 | — |
| **ИТОГО** | **36** | **20** | **3** | **13** | **5** |

> Bridge Platform (Bridge Layer, ACP, MCP Client — 3 компонента) входит в состав Extensions, не дублируется.
> "Нет отдельного теста" означает, что компонент не имеет своего test_*.py, но может быть частично покрыт через другие тесты.

---

## 9. Ключевые архитектурные решения

| Решение | Обоснование | Альтернативы |
|---------|-------------|-------------|
| **Core/Extensions/Labs** | Чёткое разделение зрелости, защита Core от нестабильных компонентов | Моноолит (сложно поддерживать), Microservices (слишком сложно для телефона) |
| **Event Bus как единственная шина** | Никаких прямых вызовов между компонентами | Прямые вызовы (tight coupling), Message Queue (избыточно) |
| **JSON-RPC 2.0 для MCP** | Стандартный протокол, без внешних SDK | Official MCP SDK (недоступен на Termux), REST (избыточен для IPC) |
| **MCP + ACP dual protocol** | MCP для внешней интеграции, ACP для внутренней | Только MCP (не хватает для agent collaboration), только ACP (несовместимость с экосистемой) |
| **SQLite как основная БД** | Доступна везде, не требует сервера, WAL-mode | PostgreSQL (избыточен), JSON files (нет индексов), DuckDB (экспериментальна на Termux) |
| **LLM Sparingly** | Детерминированные алгоритмы где можно, LLM только где нужно | LLM everywhere (дорого, медленно, недетерминированно) |

---

*Связанные документы: [VISION_3.0.md***REMOVED***(VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [IDEAS.md***REMOVED***(IDEAS.md), [ROADMAP.md***REMOVED***(ROADMAP.md), [BUFFY.md***REMOVED***(../BUFFY.md)*
