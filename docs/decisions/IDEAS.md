# IDEAS.md — Реестр архитектурных идей Buffy

> **Версия:** 1.0.0  
> **Создан:** 2026-07-29  
> **Основание:** [promt12.md***REMOVED***(../pompts/promt12.md), [promt13.md***REMOVED***(../pompts/promt13.md)  
> **Принцип:** Никакие идеи не удаляются. Каждая имеет статус. История решений сохраняется.

---

## Статусы идей

| Статус | Значение |
|--------|----------|
| 💡 **Idea** | Концепция предложена, требуется исследование |
| 🔬 **Research** | Идёт изучение подходов, альтернатив, рисков |
| 🧪 **Prototype** | Создан прототип/proof-of-concept |
| 🎨 **Design** | Готовая архитектура/спецификация |
| 📋 **Planned** | Запланировано в ROADMAP |
| 🔧 **In Progress** | В активной разработке |
| ✅ **Implemented** | Реализовано и протестировано |
| ⏸️ **Deferred** | Отложено, будет пересмотрено позже |
| ❌ **Rejected** | Отклонено с обоснованием |

---

## 1. Companion Platform

### 1.1 Companion Engine Core
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Очень высокая  

Buffy работает как независимый Companion Engine рядом с любым AI-агентом.  
Не конкурирует, а усиливает существующие системы.

**Ключевые характеристики:**
- Работает рядом с агентом (Claude Code, Cursor, OpenClaw, Codex)
- Выполняет инфраструктурные задачи без участия основной LLM
- Сохраняет контекст между сессиями разных агентов
- Предоставляет единый Project State всем агентам

**Риски:**
- Сложность интеграции с разными агентными экосистемами
- Необходимость поддержки множества протоколов
- Risk of feature creep — может превратиться в очередного агента

**Альтернативы:**
- Сделать плагином к Claude Code / Cursor / VS Code
- Ограничиться MCP-сервером
- Сфокусироваться только на одной экосистеме

---

### 1.2 Companion Runtime
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Высокая  

Автономная runtime-среда, выполняющая задачи в фоне без участия LLM.

**Компоненты:**
- Планировщик фоновых задач
- Мониторинг файловой системы (inotify)
- Авто-суммаризация и конспектирование
- Обновление Knowledge Graph
- GC и обслуживание системы

**Что уже есть:**  
✅ StreamBridge (фоновый мост)  
✅ Auto-Conspect (суммаризация)  
✅ Drift Check (аудит)  
✅ OOM Protection  
✅ Cron-задачи  

**Что отсутствует:**
- Планировщик с приоритетами
- Интеграция с файловым вотчером
- Авто-обновление Knowledge Graph в фоне

---

## 2. Project State

### 2.1 Shared Project State
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Средняя  

Единое состояние проекта, доступное всем агентам и пользователям.

**Что уже есть:**  
✅ ContextManager (SQLite-сессии)  
✅ Memory Engine (5 уровней)  
✅ Knowledge Engine (FTS5 + TF-IDF + Graph)  
✅ EventBus (публикация изменений)  

**Что отсутствует:**
- REST/WS API для внешнего доступа к состоянию
- Версионирование состояния (snapshots)
- Conflict resolution при параллельных изменениях
- API для чтения состояния без SQLite

---

### 2.2 Project Pulse (Лента событий)
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Средняя  

Общая лента событий проекта: кто, что, когда, почему изменил.

**Что уже есть:**  
✅ EventBus с SQLite-логом  
✅ raw.jsonl в stream-сессиях  
✅ CHANGELOG.md  

**Что отсутствует:**
- UI для просмотра ленты
- Фильтры по участнику, типу события, времени
- Привязка к Shared Project State

---

## 3. Session Layer

### 3.1 Session Manager
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Средняя  

Отдельные независимые сессии для людей, агентов, устройств.

**Что уже есть:**  
✅ ContextManager (множество сессий)  
✅ StreamSession (стрим-сессии с файлами)  
✅ Bridge (session_start / session_end)  

**Что отсутствует:**
- Разделение сессий по типу участника (человек vs агент vs устройство)
- Общий Project State между сессиями
- Привязка сессий к участникам, а не к чатам

---

## 4. Event Bus

### 4.1 Event Bus (существующий)
**Статус:** ✅ Implemented  
**Роль:** Основа событийной архитектуры  

- publish/subscribe с wildcard matching
- SQLite лог с запросами
- Thread-safe
- Интегрирован с: Orchestrator, MemoryEngine, KnowledgeEngine, ContextManager, MCP

---

### 4.2 Event Bus v2 — распределённый
**Статус:** 🔬 Research  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Высокая  

Распределённый Event Bus для multi-device сценариев.

**Требует:**
- WebSocket/SSE транспорт
- Сериализация событий в JSON
- Гарантия доставки (at-least-once)
- Очереди для offline-участников

---

## 5. Collaboration

### 5.1 Live Collaboration
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Очень высокая  

Совместная работа нескольких пользователей + агентов + устройств в реальном времени.

**Компоненты:**
- WebSocket сервер для real-time связи
- Presence system (онлайн/офлайн/статус)
- Operational Transform / CRDT для конкурентных изменений
- Multi-device синхронизация состояния

**Риски:**
- Огромная сложность реализации
- Конкуренция с成熟ыми платформами (Linear, Notion, Figma)
- Требует серверной инфраструктуры

---

### 5.2 Presence System
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐  
**Сложность:** Средняя  

Система присутствия участников проекта.

**Сущности:**
- Участник: человек | агент | сервер | сервис
- Статус: online | offline | busy | away
- Роль: developer | reviewer | documenter | researcher | archiver
- Активность: текущая задача, последнее действие

---

### 5.3 Collaboration Roles
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Средняя  

Роли участников, независимые от типа участника.

| Роль | Ответственность |
|------|----------------|
| Developer | Код, рефакторинг, тесты |
| Reviewer | Code review, архитектурное ревью |
| Documenter | Документация, ADR, CHANGELOG |
| Researcher | Исследования, PoC, альтернативы |
| Archiver | Память, Knowledge Graph, суммаризация |
| Orchestrator | Планирование, координация |

**Что уже есть:**  
✅ Capability Router (частично — выбор модели под задачу)  
❌ Нет разделения агентов по ролям  
❌ Нет User Preferences для назначения ролей

---

## 6. Workflow Engine

### 6.1 Workflow Engine
**Статус:** 🔬 Research (частично есть)  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Очень высокая  

Пользователь определяет последовательность работы агентов.

**Что уже есть:**  
✅ Orchestrator (FSM/DAG)  
✅ Parallel step execution  
✅ Tool Runtime  
❌ Нет пользовательского интерфейса для workflow  
❌ Нет сохранения/загрузки workflow  
❌ Нет условных переходов (if/else)  
❌ Нет циклов  
❌ Нет интеграции с ролями участников

---

## 7. Bridge Layer

### 7.1 Universal Bridge Layer
**Статус:** 🔬 Research  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Очень высокая  

Универсальный слой интеграции различных агентных экосистем.

**Целевые системы:**
- Hermes
- OpenClaw
- Claude Code
- Codex (AutoGPT)
- Cursor
- VS Code extensions
- Будущие платформы

**Что уже есть:**  
✅ MCP Server (STDIO + HTTP)  
✅ Plugin API  
✅ Intent Router  
✅ freebuff_plugin (wrapper + bridge)  

**Что отсутствует:**
- Hermes integration bridge
- OpenClaw native integration
- Claude Code plugin/config
- Двусторонний Reverse Bridge

---

### 7.2 Reverse Bridge
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Высокая  

Двусторонняя интеграция: Buffy подключается к внешним системам И сам подключает внешние системы.

**Сценарии:**
- Claude Code использует Knowledge Engine Buffy
- OpenClaw сохраняет сессии в ContextManager Buffy
- Cursor получает Project State через MCP
- Buffy запускает задачи в Claude Code

---

## 8. MCP

### 8.1 MCP как транспортный слой
**Статус:** ✅ Implemented (частично)  
**Сложность:** Средняя  

**Что уже есть:**  
✅ MCP Server (STDIO)  
✅ MCP Streamable HTTP  
✅ MCP FastAPI wrapper  
✅ 12 инструментов, 9 ресурсов, 3 промпта  

**Что отсутствует (для полноценного транспортного слоя):**
- MCP Client — подключение внешних MCP-серверов
- MCP Gateway — единая точка входа для всех MCP-серверов
- MCP Discovery — автоматическое обнаружение MCP-серверов

---

## 9. ACP (Agent Collaboration Protocol)

### 9.1 ACP — внутренний протокол Buffy
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐  
**Сложность:** Высокая  

Собственный протокол взаимодействия компонентов Buffy.

**Сущности:**
- Агент (Agent ID, capabilities, status)
- Задача (Task ID, type, payload, status)
- Событие (Event type, source, target, payload)
- Сообщение (Message ID, type, payload, response_to)

**Сообщения:**
- `agent.register` — регистрация нового агента
- `agent.status` — смена статуса
- `task.assign` — назначение задачи агенту
- `task.result` — результат выполнения
- `knowledge.query` — запрос к Knowledge Engine
- `knowledge.respond` — ответ Knowledge Engine
- `memory.store` — сохранение в память
- `memory.retrieve` — чтение из памяти

**Важно:** ACP — внутренний протокол, не претендующий на мировой стандарт.

---

## 10. Knowledge & Memory

### 10.1 Graph Memory
**Статус: 🔬 Research** (частично есть)  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Высокая  

Графовая память как основа долговременного хранения знаний.

**Что уже есть:**  
✅ GraphIndex (SQLite-граф, BFS, subgraph)  
✅ Knowledge Engine с семантическим поиском  
✅ Memory Engine с 5 уровнями  

**Что отсутствует:**
- Авто-построение графа из документов
- Визуализация графа
- Temporal graph (история изменений)
- Graph-based RAG

---

### 10.2 RAG v2
**Статус:** 🔬 Research  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Высокая  

Современная RAG-архитектура, не ограниченная Vector Search.

**Что уже есть:**  
✅ FTS5 (keyword search + BM25)  
✅ TF-IDF vector index  
✅ Semantic search (SVD)  
✅ Graph search  

**Что отсутствует:**
- Ранжирование (Re-ranking)
- Query expansion
- HyDE (Hypothetical Document Embeddings)
- Agentic RAG (агент выбирает стратегию поиска)
- Multi-modal RAG (код + текст + изображения)

---

### 10.3 Minimize LLM Usage
**Статус:** ✅ Implemented (частично)  
**Ценность:** ⭐⭐⭐⭐⭐  
**Принцип:** Детерминированные алгоритмы где можно, LLM только где нужно.

**Детерминированные компоненты:**
- ✅ OOM Protection (bash)
- ✅ Context Manager (SQLite)
- ✅ Knowledge Engine (FTS5 + TF-IDF)
- ✅ Graph Index (BFS)
- ✅ Event Bus (SQLite)
- ✅ Drift Check (file comparison)
- ✅ Auto-Conspect (суммаризация через LLM — оправдано)
- ✅ Scenario Engine (шаблоны)

**Где LLM действительно нужна:**
- Генерация кода
- Суммаризация
- Ответы на вопросы
- Архитектурный анализ

---

## 11. User Preferences

### 11.1 User Preferences System
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Средняя  

Пользователь назначает, какой агент за что отвечает.

**Настройки:**
- Кто пишет код → DeepSeek / Claude / Codebuff
- Кто исследует → GPT-5 / Perplexity
- Кто документирует → Buffy / Claude
- Кто делает ревью → GPT-5 / DeepSeek
- Кто суммаризирует → Qwen 0.5B / Buffy
- Кто обновляет базу знаний → Buffy (background)

**Формат хранения:** `config.yaml` или `MemoryLevel.PERSONAL`

---

## 12. Monitoring & Observability

### 12.1 System Monitor
**Статус:** ✅ Implemented  
**Компоненты:**
- ✅ scripts/system_monitor.py (RAM, CPU, battery, swap)
- ✅ OOM Protection (scripts/oom_protect.sh)
- ✅ Drift Check (scripts/drift_check.py)
- ✅ Status endpoint (API)

### 12.2 Metrics & Tracing
**Статус:** 💡 Idea  
**Ценность:** ⭐⭐⭐  
**Сложность:** Средняя  

- Метрики: время ответа моделей, количество токенов, частота OOM
- Трейсинг: жизненный цикл задачи от создания до завершения
- Дашборд: веб-интерфейс для мониторинга

---

## 13. Product Positioning

### 13.1 Варианты позиционирования

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **Companion Platform** | Не конкурирует с агентами, усиливает их | Неочевидно для новых пользователей |
| **CoWork Engine** | Понятно для команд | Ассоциация с Google Docs |
| **AI Collaboration Layer** | Технически точно | Сложно для маркетинга |
| **AI Infrastructure Platform** | Понятно инженерам | Скучно для пользователей |
| **Plugin Ecosystem** | Модульность, расширяемость | Требует экосистемы плагинов |
| **Middleware** | Понятно архитекторам | Непонятно пользователям |
| **Standalone Agent** | Просто для понимания | Конкуренция с Claude/Cursor |

**Рекомендация:** **Companion Platform** — наилучший баланс понятности и уникальности.

---

## Приложение: Матрица «Идея → Реализация»

| Идея | Статус | Что уже есть | Что нужно | Сложность |
|------|--------|-------------|-----------|-----------|
| Companion Runtime | 💡 Idea | StreamBridge, OOM, Cron | Планировщик, вотчер | Высокая |
| Shared Project State | 💡 Idea | ContextManager, Memory, Knowledge, EventBus | REST API, snapshots | Средняя |
| Project Pulse | 💡 Idea | EventBus, JSONL, CHANGELOG | UI, фильтры | Средняя |
| Session Manager | 💡 Idea | ContextManager, StreamSession, Bridge | Типы участников | Средняя |
| Event Bus v2 | 🔬 Research | EventBus v1 | WebSocket, очереди | Высокая |
| Live Collaboration | 💡 Idea | Нет | WS server, CRDT, Presence | Очень высокая |
| Presence System | 💡 Idea | Нет | Статусы, роли | Средняя |
| Workflow Engine | 🔬 Research | Orchestrator, Tool Runtime | UI, сохранение, условия | Очень высокая |
| Bridge Layer | 🔬 Research | MCP, Plugin API, Router | Hermes, OpenClaw, Reverse | Очень высокая |
| MCP Transport | ✅ Partial | MCP Server (STDIO+HTTP) | MCP Client, Gateway | Средняя |
| ACP | 💡 Idea | Нет | Протокол, сущности | Высокая |
| Graph Memory | 🔬 Research | GraphIndex, KnowledgeEngine | Авто-построение, визуализация | Высокая |
| RAG v2 | 🔬 Research | FTS5, TF-IDF, SVD, Graph | Re-rank, HyDE, Agentic | Высокая |
| User Preferences | 💡 Idea | Memory Engine (Personal) | Конфиг, UI | Средняя |
| Metrics & Tracing | 💡 Idea | System Monitor | Дашборд, трейсинг | Средняя |

---

*Last updated: 2026-07-29*  
*Принцип: идеи не удаляются, только меняют статус.*
