# Buffy Project 2.0 — Agentic Platform & Knowledge OS

> **Версия:** 2.0.0
> **Статус:** 🟡 АКТИВНО (MVP готов, Phase 1-2 в разработке)
> **Девиз:** *Один мозг — много моделей*

---

## 🧬 Концепция

**Buffy — это не coding assistant. Buffy — Agentic Platform и Knowledge Operating System.**

Её задача:
- **Помнить** — многоуровневая память (Working → Project → Knowledge → Personal → Archive)
- **Понимать состояние проекта** — Project State First
- **Автоматически восстанавливать контекст** — после OOM, перезапуска, смены модели
- **Управлять задачами** — TASK.md с ТЗ, промптом, туду
- **Использовать разные модели** — Capability-based Router
- **Работать месяцами без потери контекста** — Streaming Context + Content Builder

Главный принцип: **LLM — это сменный исполнитель. Ядро не зависит от модели.**

---

## 🏗 Архитектура Buffy 2.0

```
┌──────────────────────────────────────────────────────────────────┐
│                       1. BUFFY CORE                              │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Context   │  │  Task Mgr  │  │  Memory  │  │  Document   │  │
│  │  Manager   │  │ (TASK.md)  │  │  Engine  │  │  (docs/)    │  │
│  └─────┬──────┘  └─────┬──────┘  └────┬─────┘  └──────┬──────┘  │
│        │               │              │               │          │
│  ┌─────▼───────────────▼──────────────▼───────────────▼──────┐  │
│  │                2. CONTEXT BUILDER                          │  │
│  │  Динамически собирает контекст перед каждым запросом:     │  │
│  │  Working Memory + Project Memory + RAG + TASK.md + ADR    │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │             3. ORCHESTRATOR (FSM/DAG)                     │  │
│  │  Планирование → Step → Tool → Validator → повторы/ревью  │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │          4. CAPABILITY-BASED MODEL ROUTER                 │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐   │  │
│  │  │ DeepSeek   │ │ Локальная  │ │ vLLM / OpenAI /    │   │  │
│  │  │ Cloud      │ │ Qwen/Ollama│ │ Claude / Gemini    │   │  │
│  │  └────────────┘ └────────────┘ └────────────────────┘   │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                5. TOOL RUNTIME                             │  │
│  │  Shell │ Python │ Filesystem │ Git │ SQLite │ MCP │ HTTP  │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │             6. KNOWLEDGE ENGINE                           │  │
│  │  Vector Search │ FTS │ Keyword │ Graph │ Semantic Search  │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │             7. MEMORY LAYERS                              │  │
│  │  ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────┐  │  │
│  │  │Working │ │Project │ │Knowledge│ │Personal│ │Arch.│  │  │
│  │  └────────┘ └────────┘ └─────────┘ └────────┘ └──────┘  │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │             8. EVENT BUS                                   │  │
│  │  TaskCreated → CheckpointCreated → ContextUpdated → ...   │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │             9. STREAMING CONTEXT LAYER                    │  │
│  │  SQLite WAL │ raw.jsonl │ Checkpoints │ конспекты/rollup  │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🧱 11 архитектурных блоков (соответствуют слоям диаграммы)

### 🟦 Слой 1 — BUFFY CORE ✅
**Model Agnostic + Project State First + Task System**
- LLM — сменный исполнитель. Ядро не зависит от модели.
- Главная сущность — состояние проекта, не чат.
- Каждый проект: TASK.md, ROADMAP.md, CHANGELOG.md, MEMORY.db, docs/
- ContextManager (SQLite), Memory Engine, Task Mgr (TASK.md), Document (docs/)

### 🟦 Слой 2 — Context Builder 🟡
Контекст собирается динамически перед каждым запросом:
- Working Memory + Project Memory + RAG + TASK.md + ADR + CHANGELOG
- После объединения → Unified Context → модели

### 🟦 Слой 3 — Orchestrator (FSM/DAG) 🟡
Goal → Planner → Step → Tool → Validator → Reviewer → Done
Повторные попытки, валидация, ревью, передача между моделями

### 🟦 Слой 4 — Capability-based Router ✅
Вместо `if task == "code" → Qwen`:
- Каждая модель описывает capabilities
- Роутер считает пересечение required_capabilities с capabilities модели
- Data-driven, без hardcoded правил

### 🟦 Слой 5 — Tool Runtime 🟡
Инструменты — отдельная подсистема:
Shell, Python, Filesystem, Git, SQLite, HTTP, MCP, Termux API
Никакой логики инструментов внутри модели

### 🟦 Слой 6 — Knowledge Engine 🟡
Не просто RAG, а комбинация:
- Vector Search + SQLite FTS + Keyword Search + Graph Search + Semantic Search
- Система выбирает лучший способ поиска под задачу

### 🟦 Слой 7 — Memory Layers ✅
5 уровней памяти (от быстрой к архивной):
- **Working** — текущая задача, последние сообщения (SQLite ContextManager)
- **Project** — история, ADR, документация, TASK (Memory Engine)
- **Knowledge** — RAG, best practices, книги (Memory Engine JSON)
- **Personal** — предпочтения, стиль кода (Memory Engine JSON)
- **Archive** — старые проекты, логи (отдельно, не в контексте)

### 🟦 Слой 8 — Event Bus 🟡
Компоненты публикуют события, минимум прямых вызовов:
TaskCreated → CheckpointCreated → ContextUpdated → SummaryGenerated

### 🟦 Слой 9 — Streaming Context ✅
SQLite WAL + raw.jsonl + Checkpoints + Summaries + Auto-Rollup
Контекст переживает: закрытие, OOM, перезапуск, смену модели

### 🟦 Слой 10 — Plugin System 🔴
Plugins/: telegram, discord, github, obsidian, mcp
Каждый плагин подключается без изменения ядра

---

## 🧱 Ключевые принципы

### Model-Agnostic
LLM — сменный исполнитель. Система не зависит от конкретной модели.

### Context Builder First
Контекст собирается динамически из Memory + Task + ADR перед каждым запросом. Это основа работы Buffy.

### Project State First
Главная сущность — состояние проекта, а не диалог.

### Data-Driven Routing
Роутинг по capabilities, а не по if-else с именами моделей.

### Неубиваемость
Контекст на диске (SQLite + JSON + файлы). OOM-kill не страшен.

---

## 🗺 Roadmap проекта

| Фаза | Фокус | Статус |
|------|-------|--------|
| **Phase 1** | Project State + Context Builder + Streaming Context + Task System | 🟡 **Сейчас** |
| **Phase 2** | Memory Layers + Knowledge Engine + RAG + Event Bus |  В разработке |
| **Phase 3** | Capability Router + Orchestrator + Tool Runtime + MCP |  План |
| **Phase 4** | Plugin API + MCP + Local Models | 🔴 План |
| **Phase 5** | Flutter UI + Android Service + Remote Sync | 🔴 План |

---

## 📊 Что уже реализовано (v1.0 → v2.0)

| Блок | Статус | Реализация |
|------|--------|-----------|
| Streaming Context | ✅ Production | ContextManager, stream_session, Context FULL rollup |
| Task System | ✅ Production | TASK.md, CHANGELOG.md, TASK_TEMPLATE.md |
| Capability Router | ✅ Production | core/router.py — data-driven scoring |
| Memory Engine | ✅ Production | scripts/memory_engine.py — 5 уровней |
| Context Builder | 🟡 Каркас | MemoryEngine.build_context(), StreamBridge |
| Tool Runtime | 🟡 Каркас | overlay_server, auto_save, SDK bridge |
| Knowledge Engine | 🟡 MVP | TF-IDF + SVD индекс, поиск в scripts/knowledge_engine.py |
| Event Bus | 🟡 Каркас | scripts/event_bus.py + event_subscribers.py |
| Orchestrator | 🟡 Каркас | FSM/DAG, шаги, валидаторы, parallel execution |
| Plugin System | 🔴 Не начат | В Phase 4 |
| Flutter UI | 🔴 Не начат | В Phase 5 |

---

## 🔗 Экосистема

```
Buffy Project/
├── BUFFY.md              ← мой манифест
├── BUFFY_PROJECT.md       ← этот файл
├── TASK.md                ← текущая задача
├── CHANGELOG.md           ← журнал изменений
│
├── core/                  ← ядро (interfaces, router)
├── scripts/               ← инструменты (context_manager, memory_engine, stream_session, ...)
├── tests/                 ← 94 теста
│
├── context/               ← состояние
│   ├── memory/working/    ← Working Memory (Memory Engine)
│   ├── memory/project/    ← Project Memory
│   ├── memory/knowledge/  ← Knowledge Memory
│   ├── memory/personal/   ← Personal Memory
│   ├── memory/archive/    ← Archive
│   ├── streams/           ← Streaming сессии
│   ├── checkpoints/       ← чекпоинты
│   └── summaries/         ← конспекты
│
├── docs/                  ← документация
└── projects/              ← проекты под управлением
```

---

## 🎯 Почему это «неубиваемая» система

1. **Контекст на диске** — SQLite + JSON + файлы. OOM-kill не страшен.
2. **Memory Layers** — 5 уровней, от быстрой к архивной.
3. **Task-ориентированность** — TASK.md + CHANGELOG.md = полная traceability.
4. **Model-Agnostic** — можно менять модели без изменения архитектуры.
5. **Capability Router** — добавление модели = запись в каталог.
6. **Модульность** — каждый слой заменяется независимо.

---

_Версия: 2.0.0 | 2026-07-28 | Buffy (DeepSeek v4 Flash) — мозг Buffy Project_
