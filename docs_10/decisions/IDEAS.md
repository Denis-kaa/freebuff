# IDEAS.md — Реестр архитектурных идей Buffy

> **Версия:** 1.0.0  
> **Создан:** 2026-07-29  
> **Основание:** [012_01_evolution_cowork_platform.md***REMOVED***(../../pompts_11/012_01_evolution_cowork_platform.md), [013_01_vision_2_0_universal_companion.md***REMOVED***(../../pompts_11/013_01_vision_2_0_universal_companion.md)  
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
- ✅ scripts_01/system_monitor.py (RAM, CPU, battery, swap)
- ✅ OOM Protection (scripts_01/oom_protect.sh)
- ✅ Drift Check (scripts_01/drift_check.py)
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

## 14. Lessons Memory Engine (RAG-объединение уроков и решений)

> **❌ Заменено RFC [Organizational Memory Engine v1***REMOVED***(../engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md) (v5.92.0, 2026-08-05).**
> Причина: Lesson-центричная модель заменена на универсальную Organizational Memory — единый слой памяти платформы с 10+ типами знаний (adr, lesson, pattern, rule, observation, candidate, checklist, guideline, faq, workflow). Подробнее: RFC §12.5 «Альтернативы» и Приложение A «Сравнение Lessons Memory Engine vs Organizational Memory Engine».
>
> **Статус:** ❌ Rejected (заменено RFC Organizational Memory Engine v1)  
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Высокая  
**Основание:** user directive 2026-08-05 («lessons сделать системой с БД, объединить с RAG, чтобы платформа семантически смотрела на решения в похожих ситуациях, расширять семантику, собирать паттерны взаимодействия»)

**Проблема:** `core_02/LESSONS.md` — ~46 уроков CON-/ANTI-/CAND- в одном markdown-файле (782 строки). Уроки пишутся, но читаются только вручную: при возникновении похожей ситуации платформа НЕ видит прошлые решения автоматически — нет семантического поиска, нет связей «урок ↔ файл ↔ решение ↔ событие».

**Решение — lessons как БД + RAG-слой поверх существующей инфраструктуры:**

### 14.1 Схема lessons (в существующей БД, не новая)

Таблица `lessons` в `data_13/context.db` (рядом с уже существующей `arch_decisions`):

```sql
CREATE TABLE lessons (
  id            TEXT PRIMARY KEY,          -- CON-36 / ANTI-7 / CAND-1
  kind          TEXT NOT NULL,             -- confirmed | anti_pattern | candidate
  status        TEXT DEFAULT 'active',     -- active | superseded | archived (анти-drift)
  title         TEXT NOT NULL,
  scenario      TEXT DEFAULT '',           -- «когда возникает ситуация»
  problem       TEXT DEFAULT '',
  decision      TEXT DEFAULT '',
  consequence   TEXT DEFAULT '',
  lesson        TEXT DEFAULT '',           -- главный вывод
  tags          TEXT DEFAULT '',           -- JSON-массив: oom, tg, proot, disk, queue...
  source_files  TEXT DEFAULT '',           -- JSON-массив: scripts_01/prompt_dispatcher.py...
  version       TEXT DEFAULT '',           -- релиз, где урок зафиксирован
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
```

Разграничение с `arch_decisions`: ADR = архитектурные решения (что выбрали и почему); lessons = проверенный опыт/паттерны (что сработало/не сработало). Связь через `source_files` + общие теги — не дублирование, а два слоя памяти.

### 14.2 RAG-объединение (существующий семантический слой)

`context_12/knowledge/` уже содержит FTS5 + TF-IDF + SVD (`scripts_01/knowledge_engine.py::FtsIndex/TfidfIndex`, `index.db`, `vectors.npy`). План:

1. **Импорт**: при записи урока в `lessons` → автоматическая индексация в `knowledge_engine` (doc_id = lesson id; content = scenario + problem + decision + lesson + tags).
2. **Семантический поиск**: перед/в момент новой задачи платформа формирует запрос из контекста ситуации → `knowledge_engine.search()` → топ-N похожих уроков → подставляются в контекст (RAG-пайплайн «поднял прошлые решения»).
3. **Связи**: `graph_index.py` — рёбра lesson→lesson (по общим тегам), lesson→file (source_files), lesson→arch_decision (по версии/теме).
4. **Расширение семантики по ходу**: каждый новый CON-/ANTI-/CAND-урок автоматически индексируется; теги и синонимы накапливаются; повторные схожие ситуации усиливают вес (количество применений урока — метрика ценности).

### 14.3 Паттерны взаимодействия (сбор и кластеризация)

`context_12/events.db::event_log` (event_type, source, data_json, timestamp) уже логирует события. План:

1. **Сбор**: события задач/ошибок/деferral'ов/backoff'ов пишутся в event_log (source = dispatcher/wrapper/bot).
2. **Кластеризация**: периодический анализ (по event_type + data_json-полям) → группы повторяющихся ситуаций → **кандидаты в уроки** (CAND-*) с автогенерацией черновика.
3. **Подтверждение**: кандидат → ревью/подтверждение (CON-*) → запись в `lessons` + индексация.
4. **Замкнутый цикл**: lessons применяются → события показывают результат (урок помог/не помог) → семантика уточняется.

**Риски:**
- Дублирование/путаница с `arch_decisions` — нужна явная граница (ADR = решения, lessons = опыт).
- On-device ограничения: SVD-эмбеддинги дешевле LLM-эмбеддингов — начать с существующего слоя, LLM-эмбеддинги — опционально позже.
- Семантический дрейф (урок устарел) — поле `status` + периодический re-review устаревших.

**Альтернативы:**
- Отдельный `lessons.db` + отдельный векторный индекс — избыточно, существующий слой уже есть.
- Только FTS-поиск без семантики — дешевле, но не «семантически смотрит» (требование user).
- Хранить уроки только в markdown + grep — текущее состояние, не масштабируется.

---

## 15. Lead Aggregator / Attract-модуль (промт 69 × 70)

### 15.1 Attract-модуль (Lead Aggregator)
**Статус:** 🎨 Design → 🔧 In Progress (v5.145.0, 2026-08-10)
**Ценность:** ⭐⭐⭐⭐⭐  
**Сложность:** Высокая  
**Основание:** 070_07_lead_aggregator_scraper (Lead Aggregator) · промт 70 PIPELINE_TEMPLATE · прогоны встроенных промтов (IDEA EXPLORER v2.0 + ПРОМТ АРХИТЕКТОР 1.7) · ADR-014

Автономный поиск заказов/клиентов по запросу пользователя (pull-агрегатор: Kwork + TG-каналы → L1/L2/L3-классификация → доставка в TG-бот).

**Решение (Candidate A из IDEA EXPLORER):** pull-модель (read-only), аддитивность (`projects_17/lead_aggregator/`), юр. гейт (W-7) без outbound-спама.

**Второй трек B7 (inbound-видимость):** автопубликация кейсов/портфолио — отложен, отдельный трек.

**Что есть:** Фаза 1 (research W-1..W-11) + Фаза 2 (PHASE2_ARCHITECTURE.md утверждена) + Фаза 3 (код v1, 26 тестов зелёные) + MANIFEST.md + IDEA_EXPLORER_RUN.md + PROMT_ARCHITECT_RUN.md.

**Риски:** Kwork-анти-бот; ModelGateway fallback (L2-only); юридический гейт перед боевым деплоем.

---

### 15.2 ForgeFacade — мост Blueprint v3 → Forge
**Статус:** ✅ Implemented (v5.145.0, 2026-08-10)
**Ценность:** ⭐⭐⭐⭐  
**Сложность:** Средняя  
**Основание:** 071_02_prompt_architect_1_7 Миссия 2 · ADR-013 · §7.6 gap 2 (`WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md`)

Единственная санкционированная точка входа «роль → Forge-прогон»: `core_02/forge_facade.py`.

**Границы:** §7.3 сохранён (ForgePipeline инстанцируется только в Facade; scenario/wizard не тронуты); явный opt-in (`initiated_explicitly=True`); UNFORGED-семантика через `record_run()`; 14 pipeline-ролей (response_writer вне scope).

**Что есть:** `ForgeFacade` (can_initiate/initiate_forge/get_status) + `ForgeFacadeResult` + 12 тестов (126 в регрессии P3-набора) + ADR-013 + P3_FORGE_FACADE_DESIGN.md.

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
| Lessons Memory Engine | ❌ Rejected | LESSONS.md (~46 уроков), knowledge_engine (FTS/TF-IDF/SVD), graph_index, context.db::arch_decisions, event_log | Заменено RFC Organizational Memory Engine v1 (v5.92.0) — универсальная модель Knowledge Objects вместо специализированной таблицы lessons | — |
| Attract-модуль (Lead Aggregator) | 🔧 In Progress | PHASE1/PHASE2 research + код v1 (26 тестов), reuse ModelGateway/Telethon/notification | L3-скоринг, CheckpointStore, Kwork/TG-адаптеры; B7-трек (inbound) | Высокая |
| ForgeFacade (Blueprint→Forge) | ✅ Implemented | ForgeFacade (14 pipeline-ролей), §7.3 boundary сохранён, record_run, 12 тестов | — | Средняя |

---

*Last updated: 2026-08-10 (§15 Attract-модуль + ForgeFacade добавлены; матрица +2 строки; §14 остаётся ❌ Rejected per RFC v1)*  
*Принцип: идеи не удаляются, только меняют статус.*
