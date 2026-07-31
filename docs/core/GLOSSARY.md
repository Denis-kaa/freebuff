# GLOSSARY — Единый глоссарий терминов Workspace OS

> **Версия:** 1.0.0
> **Дата:** 2026-07-31
> **Статус:** 🟢 КАНОНИЧЕСКИЙ — единственный источник истины о значении терминов проекта
> **Миссия:** Этап 7 консолидации (`pompts/promt32.md`)
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md)
> **Связанные:** [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md) (поведение агента), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md)

---

## 1. Назначение и правила

**Зачем этот документ:** термины проекта используются в коде, документации, промтах и
архитектурных решениях. Если один термин значит разное в разных местах — это источник
противоречий. Этот глоссарий фиксирует **единственные канонические определения**.

**Правила использования:**

1. **Single Source of Truth:** значение термина здесь — единственное. Другие документы
   могут расширять определение, но не противоречить ему.
2. **Приоритет при конфликте:** Manifest > GLOSSARY > ARCHITECTURE_CANONICAL > конкретные спецификации.
3. **Новые термины** добавляются только сюда, а не в разрозненные документы.
4. **Изменение определения** — архитектурное решение, требует ADR.
5. **Запрещённые синонимы** (раздел 8) не использовать в новых документах/промтах.

---

## 2. Базовые понятия

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Workspace** | Рабочее пространство Buffy: корневая директория проекта платформы (содержит `scripts/`, `freebuff_plugin/`, `docs/`, `data/`, `context/`). В узком смысле — «Workspace OS» — название самой платформы как AI Infrastructure Layer. | `WORKSPACE` (корень), `data/`, `context/` | VISION_3.0 §1, BUFFY.md |
| **Project** | Пользовательский проект, с которым работает Buffy (напр. `projects/diet_platform/`). У каждого проекта своё состояние, память и лента изменений. **Не путать с Workspace** (см. §7). | `projects/`, ProjectPulse, Project State | BUFFY.md, ARCHITECTURE_MANIFEST §1 |
| **Session** | Сессия работы агента/пользователя с контекстом: история сообщений, чекпоинты, конспекты. Персистентность — `data/context.db`. | ContextManager, StreamBridge, checkpoints, summaries | SYSTEM_INVENTORY Слой 2 |
| **Runtime** | Внешний исполняющий AI-агент (Claude Code, OpenClaw, Codex, Codebuff, freebuff), который Buffy усиливает через Runtime Abstraction Layer. Buffy не содержит Runtime внутри. | Runtime Abstraction, `runtime/providers/`, adapters | VISION_3.0 §5.2 |
| **Adapter** | Реализация Runtime API для конкретного Runtime (StdioMCPAdapter, HTTPMCPAdapter). Всё общение с Runtime — только через Adapter Layer. | `freebuff_plugin/runtime/adapter.py` | VISION_3.0 §5.2 |
| **Provider** | API-провайдер моделей (Gemini, DeepSeek, Groq, Sambanova, OpenRouter, Ollama). | `core/router.py`, ModelGateway, KeyPool | SYSTEM_INVENTORY Слой 1 |
| **Model** | Конкретная LLM-модель (машинный контракт ModelCatalog). | `core/router.py`, ModelCatalog | SYSTEM_INVENTORY Слой 1 |
| **Capability** | Пользовательская возможность (planning, coding, documentation, review, research, testing, architecture, refactoring, translation). Пользователь выбирает capability, а не модель. | Capability Registry, RoleEngine (capabilities ролей) | VISION_3.0 §5.5 |
| **Policy** | Правило пользователя, определяющее выбор Runtime/Provider/Model/Workflow/Fallback/Cost. Buffy исполняет политики, а не решает за пользователя. | Policy Engine, `freebuff_plugin/policy/` | VISION_3.0 §5.3 |
| **Context** | Собранное состояние для работы агента: сессия + память + знания + чекпоинты. Управляется ContextManager (порог CONTEXT_FULL 28K токенов). | ContextManager, `_estimate_tokens()`, summaries | SYSTEM_INVENTORY Слой 1–2 |

---

## 3. Код и компоненты

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Module** | Единица кода: Python-модуль/пакет (файл или директория с `__init__.py`). Нижний уровень иерархии. Модуль = одна задача (SRP) + тесты + регистрация в реестре. | `scripts/*.py`, `freebuff_plugin/*/`, `plugins/*/` | ARCHITECTURE_MANIFEST §5 |
| **Component** | Архитектурный компонент: логическая единица системы (движок, слой, сервис). Компонент может состоять из нескольких модулей. Полный каталог — SYSTEM_INVENTORY. | SYSTEM_INVENTORY, Module Registry (Этап 6) | ARCHITECTURE_MANIFEST §4 |
| **Engine** | `*Engine`-класс движка — компонент с собственной ответственностью и хранилищем (MemoryEngine, KnowledgeEngine, EMEngine, CollaborationEngine, PresenceEngine, RoleEngine, MetricsEngine, RAGEngine). Границы — в ARCHITECTURE_CANONICAL §3. | `scripts/*_engine.py` | ARCHITECTURE_CANONICAL §3 |
| **Tool** | Исполняемый инструмент, доступный агенту: MCP-инструмент (`mcp_server.py`), CLI-команда или ToolRuntime-инструмент. Валидация и исполнение — ToolRuntime. | ToolRuntime, MCP Server, `scripts/tool_runtime.py` | ARCHITECTURE_MANIFEST §4.2 |
| **Plugin** | Расширение платформы по Plugin API: жизненный цикл BasePlugin (on_load/enable/disable/unload), манифест, do_* действия, EventBus-подписка. Ядро → Плагин только через `freebuff_plugin/__init__.py`. | PluginAPI, `plugins/*/` (hello_world, tg_messenger, system_monitor, knowledge_sync) | ARCHITECTURE_MANIFEST §3.2 |
| **Connector** | Интеграционный адаптер «компонент ↔ внешняя система» (MCP-клиент, ACP-пир, мост). **Плановый термин** для интеграций верхнего уровня (Integration Registry). Не путать с Adapter (Runtime) и Plugin (расширение платформы). | MCP Client, ACP Protocol, Bridge Layer | promt32, INTEGRATION_CONTRACT.md |
| **Integration** | Интеграция платформы с внешней системой/сервисом (Claude Code, OpenClaw, Telegram, Termux:API). Каждая интеграция — запись в Integration Registry (Этап 9), реализуется только через публичные API. | INTEGRATION_REGISTRY.md (план), Bridge Layer | ARCHITECTURE_MANIFEST §7 |
| **Registry** | Реестр: перечисляет сущности категории и их статусы. Каталог компонентов — SYSTEM_INVENTORY; реестры Module/Agent/Integration — цель Этапов 6/9. Реестр = данные для авто-проверки консистентности. | SYSTEM_INVENTORY, Module/Agent/Integration Registry (план) | promt32 Этап 6/9 |
| **Lifecycle** | Жизненный цикл компонента: Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление. Ни один компонент не существует без описанного Lifecycle. | ARCHITECTURE_MANIFEST §5, Этап 8 | ARCHITECTURE_MANIFEST §5 |

---

## 4. Память и знания

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Memory** | Память агента (MemoryEngine): сессионная/рабочая, 6 уровней (short→long + vector). Краткосрочная по KMS-правилу. | MemoryEngine, `data/memory*` | ARCHITECTURE_MANIFEST §3.4 |
| **Knowledge** | Знания проекта (KnowledgeEngine): канонический индексатор фактов и документов. FTS5 + TF-IDF + SemanticIndex. Средняя/долгая память. | KnowledgeEngine, `context/knowledge/index.db` | ARCHITECTURE_MANIFEST §3.4 |
| **Graph Index** | Граф связей между сущностями (GraphIndex): BFS, subgraph, графовые запросы. Дополняет Knowledge, не заменяет. | GraphIndex, `scripts/graph_index.py` | ARCHITECTURE_MANIFEST §3.4 |
| **RAG** | Семантический поиск с ранжированием (RAGEngine): 5 режимов, RRF, re-ranking. **Целевое состояние: фича KnowledgeEngine** (KMS-решение promt31), сейчас отдельный движок. | RAGEngine, KnowledgeEngine | ARCHITECTURE_MANIFEST §3.4 |
| **Engineering Memory** | Нарративная память проекта (EMEngine): ADR, инциденты, ретроспективы, уроки. Долгая, человекочитаемая. Хранится в `docs/engineering-memory/`. | EMEngine, `docs/engineering-memory/` | ARCHITECTURE_MANIFEST §3.4 |
| **Project Book** | Единый нарративный документ проекта (`docs/engineering-memory/PROJECT_BOOK.md`): инженерная история из CHANGELOG, аудитов, коммитов. «Второй Project Book» — запрещён (анти-паттерн). | PROJECT_BOOK.md, CHANGELOG.md | ARCHITECTURE_MANIFEST §7 |
| **Decision Log** | Журнал архитектурных решений: полные ADR в `docs/engineering-memory/decisions/ADR_NNN_*.md`, индекс — `docs/decisions/DECISIONS.md`. Дублирование журнала запрещено. | DECISIONS.md, ADR-файлы | ARCHITECTURE_MANIFEST §6 |
| **Pulse** | Лента изменений проекта (ProjectPulse): git-коммиты, изменения файлов, события EventBus. Единый таймлайн активности. | ProjectPulse, `data/project_pulse.db` | SYSTEM_INVENTORY, ARCHITECTURE_CANONICAL S6 |

---

## 5. Коммуникация и агенты

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Event** | Событие EventBus: `Event(type, data, ...)`. Все значимые операции публикуют события; компоненты не вызывают друг друга напрямую. | EventBus, `scripts/event_bus.py` | ARCHITECTURE_MANIFEST §2 |
| **EventBus** | Шина событий: publish/subscribe, wildcard, SQLite-лог. Единственный канал связи между слоями. | EventBus, `context/events.db` | ARCHITECTURE_CANONICAL C5 |
| **Agent** | AI-агент. Два значения: (1) внешний Runtime-агент, который Buffy усиливает; (2) распределённый агент внутри платформы (AgentMesh, DistributedCoordinator). В документах уточнять контекст. | AgentMesh, DistributedCoordinator, `scripts/distributed_agents.py` | ARCHITECTURE_CANONICAL §2, promt32 |
| **Distributed Agent** | Агент распределённой сети (зарегистрирован в AgentMesh), участвует в распределённых воркфлоу. | AgentMesh, TaskDistributor, DistributedWorkflow | CHANGELOG v5.14.0 |
| **Presence** | Присутствие агента (PresenceEngine): статусы online/offline/busy/away/error, heartbeat, prune. | PresenceEngine, `data/presence.db` | ARCHITECTURE_CANONICAL S3 |
| **Role** | Роль участника (RoleEngine): 6 стандартных ролей (developer, reviewer, documenter, researcher, archiver, orchestrator) + capabilities + collab-маппинг (orchestrator→owner, developer/reviewer→editor). | RoleEngine, `data/roles.db` | ARCHITECTURE_CANONICAL S4 |
| **Collaboration** | Совместная работа (CollaborationEngine): сессии, участники, роли owner/editor/viewer, история сообщений. | CollaborationEngine, `data/collaboration.db` | ARCHITECTURE_CANONICAL S2 |
| **MCP** | Model Context Protocol — один из протоколов коммуникации (STDIO/HTTP). MCP — не суть платформы, а лишь протокол. | MCP Server, MCP Client, `scripts/mcp_server.py` | VISION_3.0 §4.2 |
| **ACP** | Agent Collaboration Protocol — протокол взаимодействия агентов. | ACP Protocol, `freebuff_plugin/acp_protocol.py` | VISION_3.0 §5 |
| **Bridge Layer** | Трансляция MCP ↔ ACP между агентными системами. | Bridge Layer, `freebuff_plugin/bridge_layer.py` | VISION_3.0 §5 |
| **Scenario** | Готовый сценарий-шаблон задачи (Scenario Engine): 11+ сценариев в `freebuff_plugin/scenarios/`. | Scenario Engine, `scenarios/` | SYSTEM_INVENTORY, VISION_3.0 |

---

## 6. Жизненный цикл и статусы документации

| Термин | Каноническое определение |
|--------|--------------------------|
| **Lifecycle стадии** | Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление (архитектурный канон, ARCHITECTURE_MANIFEST §5). |
| **ACTIVE** | Статус документа: актуален, обязателен к соблюдению. |
| **LEGACY** | Устаревающий документ: ещё действует, но заменяется; новые документы не ссылаются. |
| **ARCHIVED** | Архив: история, не используется. Хранится, не удаляется (запрет на удаление истории). |
| **DRAFT** | Черновик: не обязателен, может измениться. |
| **OBSOLETE** | Полностью устарел: ссылки должны быть актуализированы (Этап 4). |

---

## 7. Разрешённые неоднозначности (как разграничено)

| Часто путают | Каноническое разграничение |
|--------------|----------------------------|
| **Workspace vs Project** | Workspace — платформа/корень Buffy. Project — пользовательский проект внутри `projects/`. У Buffy один Workspace, много Projects. |
| **Memory vs Knowledge vs Engineering Memory** | Memory = краткосрочная рабочая (MemoryEngine). Knowledge = канонический индексатор фактов (KnowledgeEngine). Engineering Memory = человекочитаемая нарративная (EMEngine). KMS-правило. |
| **Module vs Component vs Engine** | Module — единица кода. Component — архитектурная единица (может содержать модули). Engine — `*Engine`-компонент с ответственностью и хранилищем. |
| **Tool vs Plugin vs Connector** | Tool — исполняемый инструмент для агента. Plugin — расширение платформы по Plugin API. Connector — интеграционный адаптер «компонент ↔ внешняя система». |
| **Adapter vs Connector** | Adapter — реализация Runtime API (для конкретного Runtime). Connector — интеграция с внешней системой (плановый). |
| **RAG vs Knowledge vs Vector Memory** | RAG и Vector Memory — фичи/надстройки KnowledgeEngine (KMS-решение). KnowledgeEngine — единственный канонический индексатор. |
| **Decision Log vs IDEAS** | Decision Log — принятые решения (ADR). IDEAS — реестр идей (хранится вечно, статусы меняются). |
| **Project Book vs CHANGELOG** | Project Book — нарративная история (инженерная память). CHANGELOG — фактологический журнал версий. Project Book компилируется из CHANGELOG + аудитов. |
| **Pulse vs Drift Check** | Pulse — лента событий проекта (ProjectPulse). Drift Check — самодиагностика расхождений (drift_check.py). Разные домены. |
| **Metrics vs Pulse vs Drift** | Metrics — метрики качества (VCR/SRG/CpVO/RRR/TTD). Pulse — лента событий. Drift — самодиагностика документации. |

---

## 8. Запрещённые синонимы (не использовать)

| ❌ Не использовать | ✅ Вместо этого |
|--------------------|----------------|
| «база знаний» для MemoryEngine | `KnowledgeEngine` / Knowledge |
| «второй источник истины» как норма | Single Source of Truth (запрещено дублирование) |
| «новый Project Book» | Расширять `PROJECT_BOOK.md` |
| «ещё один Decision Log» | `DECISIONS.md` индекс + ADR |
| «новый storage engine» | Переиспользовать KnowledgeEngine / MemoryEngine |
| «агент-бот» / «chat-bot» | Engineering Agent / AI Agent |

---

## 9. Как добавить термин

1. Термин уже используется в коде/доке? Если да — определение берётся из фактического поведения + канонических документов.
2. Новый термин → сначала сюда, потом в документы.
3. Изменение канонического определения → ADR (docs/engineering-memory/decisions/).
4. Каждый термин ссылается на исходный компонент/файл — без ссылки термин не добавляется.

---

## 10. Критерий согласованности (Этап 7)

- [x***REMOVED*** Канонические определения для: Workspace, Project, Module, Agent, Tool, Plugin, Connector, Integration, Knowledge, Memory, Project Book, Engineering Memory, Lifecycle, Registry, Decision Log, Pulse
- [x***REMOVED*** Разграничены неоднозначности (Memory/Knowledge/EM, Workspace/Project, Module/Component/Engine, Tool/Plugin/Connector)
- [x***REMOVED*** Запрещённые синонимы зафиксированы
- [x***REMOVED*** Связан с Manifest / ARCHITECTURE_CANONICAL / CORE_PROMPT

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
