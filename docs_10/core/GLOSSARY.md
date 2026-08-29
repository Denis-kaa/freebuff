# GLOSSARY — Единый глоссарий терминов Workspace OS

> **Версия:** 1.4.0
> **Дата:** 2026-08-19
> **Статус:** 🟢 КАНОНИЧЕСКИЙ — единственный источник истины о значении терминов проекта
> **Миссия:** Этап 7 консолидации (`pompts_11/032_09_workspace_os_konsolidaciya.md`)
> **Высший закон:** [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md)
> **Связанные:** [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md) (границы движков), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md) (жизненные циклы), [MODULE_CONSOLIDATION.md***REMOVED***(MODULE_CONSOLIDATION.md) (модули), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md) (поведение агента), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md)

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
| **Workspace** | Рабочее пространство Buffy: корневая директория проекта платформы (содержит `scripts_01/`, `freebuff_plugin_03/`, `docs_10/`, `data_13/`, `context_12/`). В узком смысле — «Workspace OS» — название самой платформы как AI Infrastructure Layer. | `WORKSPACE` (корень), `data_13/`, `context_12/` | VISION_3.0 §1, BUFFY.md |
| **Project** | Пользовательский проект, с которым работает Buffy (напр. `projects_17/diet_platform/`). У каждого проекта своё состояние, память и лента изменений. **Не путать с Workspace** (см. §7). | `projects_17/`, ProjectPulse, Project State | BUFFY.md, ARCHITECTURE_MANIFEST §1 |
| **Session** | Сессия работы агента/пользователя с контекстом: история сообщений, чекпоинты, конспекты. Персистентность — `data_13/context.db`. | ContextManager, StreamBridge, checkpoints, summaries | SYSTEM_INVENTORY Слой 2 |
| **Runtime** | Внешний исполняющий AI-агент (Claude Code, OpenClaw, Codex, Codebuff, freebuff), который Buffy усиливает через Runtime Abstraction Layer. Buffy не содержит Runtime внутри. | Runtime Abstraction, `runtime_05/providers/`, adapters | VISION_3.0 §5.2 |
| **Adapter** | Реализация Runtime API для конкретного Runtime (StdioMCPAdapter, HTTPMCPAdapter). Всё общение с Runtime — только через Adapter Layer. | `freebuff_plugin_03/runtime/adapter.py` | VISION_3.0 §5.2 |
| **Provider** | API-провайдер моделей (Gemini, DeepSeek, Groq, Sambanova, OpenRouter, Ollama). | `core_02/router.py`, ModelGateway, KeyPool | SYSTEM_INVENTORY Слой 1 |
| **Model** | Конкретная LLM-модель (машинный контракт ModelCatalog). | `core_02/router.py`, ModelCatalog | SYSTEM_INVENTORY Слой 1 |
| **Capability** | Пользовательская возможность (planning, coding, documentation, review, research, testing, architecture, refactoring, translation). Пользователь выбирает capability, а не модель. | Capability Registry, RoleEngine (capabilities ролей) | VISION_3.0 §5.5 |
| **Policy** | Правило пользователя, определяющее выбор Runtime/Provider/Model/Workflow/Fallback/Cost. Buffy исполняет политики, а не решает за пользователя. | Policy Engine, `freebuff_plugin_03/policy/` | VISION_3.0 §5.3 |
| **Context** | Собранное состояние для работы агента: сессия + память + знания + чекпоинты. Управляется ContextManager (порог CONTEXT_FULL 28K токенов). | ContextManager, `_estimate_tokens()`, summaries | SYSTEM_INVENTORY Слой 1–2 |

---

## 3. Код и компоненты

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Module** | Единица кода: Python-модуль/пакет (файл или директория с `__init__.py`). Нижний уровень иерархии. Модуль = одна задача (SRP) + тесты + регистрация в реестре. | `scripts_01/*.py`, `freebuff_plugin_03/*/`, `plugins_04/*/` | ARCHITECTURE_MANIFEST §5 |
| **Component** | Архитектурный компонент: логическая единица системы (движок, слой, сервис). Компонент может состоять из нескольких модулей. Полный каталог — SYSTEM_INVENTORY. | SYSTEM_INVENTORY, Module Registry (Этап 6) | ARCHITECTURE_MANIFEST §4 |
| **Engine** | `*Engine`-класс движка — компонент с собственной ответственностью и хранилищем (MemoryEngine, KnowledgeEngine, EMEngine, CollaborationEngine, PresenceEngine, RoleEngine, MetricsEngine, RAGEngine). Границы — в ARCHITECTURE_CANONICAL §3. | `scripts_01/*_engine.py` | ARCHITECTURE_CANONICAL §3 |
| **Tool** | Исполняемый инструмент, доступный агенту: MCP-инструмент (`mcp_server.py`), CLI-команда или ToolRuntime-инструмент. Валидация и исполнение — ToolRuntime. | ToolRuntime, MCP Server, `scripts_01/tool_runtime.py` | ARCHITECTURE_MANIFEST §4.2 |
| **Plugin** | Расширение платформы по Plugin API: жизненный цикл BasePlugin (on_load/enable/disable/unload), манифест, do_* действия, EventBus-подписка. Ядро → Плагин только через `freebuff_plugin_03/__init__.py`. | PluginAPI, `plugins_04/*/` (hello_world, tg_messenger, system_monitor, knowledge_sync) | ARCHITECTURE_MANIFEST §3.2 |
| **Connector** | Интеграционный адаптер «компонент ↔ внешняя система» (MCP-клиент, ACP-пир, мост). **Плановый термин** для интеграций верхнего уровня (Integration Registry). Не путать с Adapter (Runtime) и Plugin (расширение платформы). | MCP Client, ACP Protocol, Bridge Layer | promt32, INTEGRATION_CONTRACT.md |
| **Integration** | Интеграция платформы с внешней системой/сервисом (Claude Code, OpenClaw, Telegram, Termux:API). Каждая интеграция — запись в Integration Registry (Этап 9), реализуется только через публичные API. | INTEGRATION_REGISTRY.md (план), Bridge Layer | ARCHITECTURE_MANIFEST §7 |
| **Registry** | Реестр: перечисляет сущности категории и их статусы. Каталог компонентов — SYSTEM_INVENTORY; реестры Module/Agent/Integration — цель Этапов 6/9. Реестр = данные для авто-проверки консистентности. | SYSTEM_INVENTORY, Module/Agent/Integration Registry (план) | promt32 Этап 6/9 |
| **Lifecycle** | Жизненный цикл компонента: Создание → Инициализация → Работа → Обновление → Завершение → Архивация → Удаление. Ни один компонент не существует без описанного Lifecycle. | ARCHITECTURE_MANIFEST §5, Этап 8 | ARCHITECTURE_MANIFEST §5 |
| **Naming Convention** | Канон именования сущностей Workspace: **каталоги** — `имя_NN` (суффикс-ID, `scripts_01/`), **промты** — `NNN_TT_имя` (префикс-порядок, `032_09_workspace_os_konsolidaciya.md`). Цифра в начале имени Python-пакета запрещена (импорты) — поэтому каталогам суффикс, промтам префикс. Полные таблицы old→new — FINAL_STRUCTURE §2.1. | каталоги, `pompts_11/` | FINAL_STRUCTURE §2.1 |

---

## 4. Память и знания

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Memory** | Память агента (MemoryEngine): сессионная/рабочая, 6 уровней (short→long + vector). Краткосрочная по KMS-правилу. | MemoryEngine, `data_13/memory*` | ARCHITECTURE_MANIFEST §3.4 |
| **Knowledge** | Знания проекта (KnowledgeEngine): канонический индексатор фактов и документов. FTS5 + TF-IDF + SemanticIndex. Средняя/долгая память. | KnowledgeEngine, `context_12/knowledge/index.db` | ARCHITECTURE_MANIFEST §3.4 |
| **Graph Index** | Граф связей между сущностями (GraphIndex): BFS, subgraph, графовые запросы. Дополняет Knowledge, не заменяет. | GraphIndex, `scripts_01/graph_index.py` | ARCHITECTURE_MANIFEST §3.4 |
| **RAG** | Семантический поиск с ранжированием (RAGEngine): 5 режимов, RRF, re-ranking. **Целевое состояние: фича KnowledgeEngine** (KMS-решение promt31), сейчас отдельный движок. | RAGEngine, KnowledgeEngine | ARCHITECTURE_MANIFEST §3.4 |
| **Engineering Memory** | Нарративная память проекта (EMEngine): ADR, инциденты, ретроспективы, уроки. Долгая, человекочитаемая. Хранится в `docs_10/engineering-memory/`. | EMEngine, `docs_10/engineering-memory/` | ARCHITECTURE_MANIFEST §3.4 |
| **Project Book** | Единый нарративный документ проекта (`docs_10/engineering-memory/PROJECT_BOOK.md`): инженерная история из CHANGELOG, аудитов, коммитов. «Второй Project Book» — запрещён (анти-паттерн). | PROJECT_BOOK.md, CHANGELOG.md | ARCHITECTURE_MANIFEST §7 |
| **Decision Log** | Журнал архитектурных решений: полные ADR в `docs_10/engineering-memory/decisions/ADR_NNN_*.md`, индекс — `docs_10/decisions/DECISIONS.md`. Дублирование журнала запрещено. | DECISIONS.md, ADR-файлы | ARCHITECTURE_MANIFEST §6 |
| **Pulse** | Лента изменений проекта (ProjectPulse): git-коммиты, изменения файлов, события EventBus. Единый таймлайн активности. | ProjectPulse, `data_13/project_pulse.db` | SYSTEM_INVENTORY, ARCHITECTURE_CANONICAL S6 |

---

## 5. Коммуникация и агенты

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Event** | Событие EventBus: `Event(type, data, ...)`. Все значимые операции публикуют события; компоненты не вызывают друг друга напрямую. | EventBus, `scripts_01/event_bus.py` | ARCHITECTURE_MANIFEST §2 |
| **EventBus** | Шина событий: publish/subscribe, wildcard, SQLite-лог. Единственный канал связи между слоями. | EventBus, `context_12/events.db` | ARCHITECTURE_CANONICAL C5 |
| **Agent** | AI-агент. Два значения: (1) внешний Runtime-агент, который Buffy усиливает; (2) распределённый агент внутри платформы (AgentMesh, DistributedCoordinator). В документах уточнять контекст. | AgentMesh, DistributedCoordinator, `scripts_01/distributed_agents.py` | ARCHITECTURE_CANONICAL §2, promt32 |
| **Distributed Agent** | Агент распределённой сети (зарегистрирован в AgentMesh), участвует в распределённых воркфлоу. | AgentMesh, TaskDistributor, DistributedWorkflow | CHANGELOG v5.14.0 |
| **Presence** | Присутствие агента (PresenceEngine): статусы online/offline/busy/away/error, heartbeat, prune. | PresenceEngine, `data_13/presence.db` | ARCHITECTURE_CANONICAL S3 |
| **Role** | Роль участника (RoleEngine): 6 стандартных ролей (developer, reviewer, documenter, researcher, archiver, orchestrator) + capabilities + collab-маппинг (orchestrator→owner, developer/reviewer→editor). | RoleEngine, `data_13/roles.db` | ARCHITECTURE_CANONICAL S4 |
| **Collaboration** | Совместная работа (CollaborationEngine): сессии, участники, роли owner/editor/viewer, история сообщений. | CollaborationEngine, `data_13/collaboration.db` | ARCHITECTURE_CANONICAL S2 |
| **MCP** | Model Context Protocol — один из протоколов коммуникации (STDIO/HTTP). MCP — не суть платформы, а лишь протокол. | MCP Server, MCP Client, `scripts_01/mcp_server.py` | VISION_3.0 §4.2 |
| **ACP** | Agent Collaboration Protocol — протокол взаимодействия агентов. | ACP Protocol, `freebuff_plugin_03/acp_protocol.py` | VISION_3.0 §5 |
| **Bridge Layer** | Трансляция MCP ↔ ACP между агентными системами. | Bridge Layer, `freebuff_plugin_03/bridge_layer.py` | VISION_3.0 §5 |
| **Scenario** | Готовый сценарий-шаблон задачи (Scenario Engine): 11+ сценариев в `freebuff_plugin_03/scenarios/`. | Scenario Engine, `scenarios/` | SYSTEM_INVENTORY, VISION_3.0 |

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
| **Workspace vs Project** | Workspace — платформа/корень Buffy. Project — пользовательский проект внутри `projects_17/`. У Buffy один Workspace, много Projects. |
| **Memory vs Knowledge vs Engineering Memory** | Memory = краткосрочная рабочая (MemoryEngine). Knowledge = канонический индексатор фактов (KnowledgeEngine). Engineering Memory = человекочитаемая нарративная (EMEngine). KMS-правило. |
| **Module vs Component vs Engine** | Module — единица кода. Component — архитектурная единица (может содержать модули). Engine — `*Engine`-компонент с ответственностью и хранилищем. |
| **Tool vs Plugin vs Connector** | Tool — исполняемый инструмент для агента. Plugin — расширение платформы по Plugin API. Connector — интеграционный адаптер «компонент ↔ внешняя система». |
| **Adapter vs Connector** | Adapter — реализация Runtime API (для конкретного Runtime). Connector — интеграция с внешней системой (плановый). |
| **RAG vs Knowledge vs Vector Memory** | RAG и Vector Memory — фичи/надстройки KnowledgeEngine (KMS-решение). KnowledgeEngine — единственный канонический индексатор. |
| **Decision Log vs IDEAS** | Decision Log — принятые решения (ADR). IDEAS — реестр идей (хранится вечно, статусы меняются). |
| **Project Book vs CHANGELOG** | Project Book — нарративная история (инженерная память). CHANGELOG — фактологический журнал версий. Project Book компилируется из CHANGELOG + аудитов. |
| **Pulse vs Drift Check** | Pulse — лента событий проекта (ProjectPulse). Drift Check — самодиагностика расхождений (drift_check.py). Разные домены. |
| **Metrics vs Pulse vs Drift** | Metrics — метрики качества (VCR/SRG/CpVO/RRR/TTD). Pulse — лента событий. Drift — самодиагностика документации. |
| **Workspace (платформа) vs Workspace (сфера)** | Workspace-платформа — корень платформы Buffy (существующее определение §2). Workspace-сфера — уровень доменной модели promt36 (Работа/Хобби/Личное). При использовании уточнять контекст. |
| **Work Area vs Workspace vs Project** | Work Area — **View**, а не сущность (динамический список проектов по Resource). Workspace — сфера. Project — цель внутри сферы. |
| **Рекомендация DPE vs User-Choice Override** | DPE **рекомендует** исполнителя по приоритету и ролям; User-Choice Override — право пользователя **переопределить** рекомендацию в любой момент. Рекомендация ≠ принуждение. |
| **Factory vs Forge vs Scenario vs RoleExecutorRegistry** | Factory — доменный adapter (генерация артефактов по capability, universal boundary). Forge — метасистема оркестрации/валидации (не генерирует LIGHT-артефакты). Scenario — корпус данных (блюпринты ролей). RoleExecutorRegistry — генераторы LIGHT-ролей, отдельный слой от Scenario (ADR-016, §7.3). |

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
| «Work Area как папка/сущность» | Work Area — **View** (список проектов по Resource), не сущность и не каталог |
| «Заметки» как точка входа | Точка входа — «Продолжить работу над проектом» (Knowledge as Byproduct) |

---

## 9. Как добавить термин

1. Термин уже используется в коде/доке? Если да — определение берётся из фактического поведения + канонических документов.
2. Новый термин → сначала сюда, потом в документы.
3. Изменение канонического определения → ADR (docs_10/engineering-memory/decisions/).
4. Каждый термин ссылается на исходный компонент/файл — без ссылки термин не добавляется.

---

## 10. Критерий согласованности (Этап 7)

- [x***REMOVED*** Канонические определения для: Workspace, Project, Module, Agent, Tool, Plugin, Connector, Integration, Knowledge, Memory, Project Book, Engineering Memory, Lifecycle, Registry, Decision Log, Pulse
- [x***REMOVED*** Разграничены неоднозначности (Memory/Knowledge/EM, Workspace/Project, Module/Component/Engine, Tool/Plugin/Connector)
- [x***REMOVED*** Запрещённые синонимы зафиксированы
- [x***REMOVED*** Связан с Manifest / ARCHITECTURE_CANONICAL / CORE_PROMPT

---

## 11. Доменная модель Workspace OS (11 канонических правил, promt36 + promt37)

> **Источники:** `pompts_11/036_09_full_consolidation_pipeline.md` — каноническая доменная модель Workspace OS (правила 1–10);
> `pompts_11/037_11_user_choice_override.md` — аддендум: правило 11 (User-Choice Override) + уточнение правила 7 (DPE).
> Термины из «11 правил» — единые определения для пользовательских сценариев
> (SINGLE/COWORK/TEAM/COMMUNITY). Не конфликтуют с определениями §2–5
> (разграничения — в §7).

| Термин | Каноническое определение |
|--------|--------------------------|
| **Workstation** | Оболочка: устройство/среда, где работает пользователь (Termux на Android, ноутбук, рабочий стол). Верхний уровень иерархии. |
| **Workspace (сфера)** | Сфера деятельности: **Работа / Хобби / Личное**. Второй уровень иерархии. Не путать с Workspace-платформа (§7). |
| **Project (цель)** | Цель пользователя внутри сферы: **Сайт / CRM / Блог**. Третий уровень иерархии. |
| **Work Area (as View)** | **НЕ папка и НЕ сущность.** Динамический список проектов, связанных с конкретным **Resource** («нажал на Telegram → увидел все проекты с Telegram»). |
| **Resource** | Внешний ресурс, связывающий проекты (Telegram, Git, Cloudflare, MCP-сервер). Связь `project ↔ resource` (таблица `project_resources`). |
| **Squad** | Группа ролей/участников, работающих над целью проекта. |
| **Workspace Owner** | Создатель Workspace: видит всё и управляет ролями участников. |
| **DPE (Delegation & Priority Engine)** | Ассистент-делегатор: оценивает приоритет задачи (1-Critical / 2-High / 3-Normal), сверяет с возможностями ролей (Role Capabilities) и **рекомендует** исполнителя на основе Policy Engine. **НО:** пользователь может переопределить выбор в любой момент (правило 11, User-Choice Override). |
| **TaskAnalyzer** | Компонент DPE: преобразует поток идей пользователя в структурированную задачу. |
| **Context-Aware Task Routing** | Перед созданием задачи — проверка Knowledge/Graph/Task System; не создавать дубли. |
| **Presence-aware Auto-delegation** | Система сама назначает задачу тому участнику, кто **онлайн** и имеет нужную роль. |
| **Knowledge as Byproduct** | Пользователь работает, система **сама** строит знания как побочный продукт. Заметки — не точка входа; точка входа — «Продолжить работу над проектом». |
| **Plugin Contract Specification** | Архитектура плагинов есть (Plugin API); требуется контрактная спецификация плагина (Plugin Contract Specification) как единый документ о границах плагин ↔ ядро. |
| **Policy Engine** | Исполнитель пользовательских политик выбора Runtime/Provider/Model/Workflow/Fallback/Cost. Рекомендации Policy Engine — основа DPE (правило 7) и User-Choice Override (правило 11): система рекомендует, пользователь выбирает. |
| **User-Choice Override** | **Система рекомендует, но пользователь выбирает** (правило 11). Пользователь может назначить конкретную модель/агента для каждой capability, переопределить автоматический выбор системы в любой момент, использовать бесплатные ключи (Qwen, Ollama, локальные модели) и миксовать провайдеров (Claude — архитектура, DeepSeek — код, Gemini — исследования). |
| **Режимы работы** | SINGLE (1 пользователь) / COWORK (1 + несколько Runtime) / TEAM (2–10 пользователей) / COMMUNITY (100+, будущее). Параллельные ветки с разной изоляцией. |

---

## 12. Конвейер исполнения: Forge / Factory / Blueprint v3 (ADR-013/016)

> Термины конвейера проектирования и автоисполнения ролей. Дополняют §3 (компоненты)
> и §5 (агенты/Scenario). Не конфликтуют с ними — разграничения в §7.

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **Forge** | Метасистема проектирования: отвечает на вопрос «как Buffy проектирует себя». Оркестрирует pipeline ролей и валидацию. **НЕ** runtime-платформа, НЕ CI/CD, НЕ мониторинг. | ForgeFacade, ForgePipeline, ForgeRegistry | RFC_BUFFY_FORGE_V1.md §12, AGENTS.md §2 |
| **ForgeFacade** | Единственный санкционированный мост Blueprint v3 → Forge (§7.3: Scenario/роли НЕ вызывают Forge напрямую). `run_chain` — chain-runner по pipeline-ролям. | `core_02/forge_facade.py`, `initiate_forge`, `run_chain` | ADR-013, `core_02/forge_facade.py` |
| **ForgePipeline** | Полный цикл Forge (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT) для HEAVY-ролей. Инстанцируется ТОЛЬКО внутри ForgeFacade. | `core_02/forge_pipeline.py`, `stage_check` | `core_02/forge_pipeline.py` |
| **Factory** | Доменный adapter (content/research/test): universal boundary `resolve(capability → (factory, forge)) → build_execution_request → execute(ForgeFacade.run_chain) → normalize_output → accumulate(MemoryStore)`. | `core_02/factory_base.py`, `scripts_01/{content,research,test***REMOVED***_factory.py`, FactoryRegistry | FACTORY_FORGE_ARCHITECTURE_V1.md, `core_02/factory_base.py` |
| **Blueprint (Blueprint v3 / BlueprintCorpus)** | Корпус блюпринтов ролей (XML-tagged Markdown + декларативный `registry.yaml`, Kwork Arbitr v3). Reader + creator; `routing_hint(role_id)` → capabilities для SmartRouter. | `core_02/blueprint_v3.py`, BlueprintCorpus, `CAPABILITIES_OVERRIDE` | `core_02/blueprint_v3.py` |
| **LIGHT-роль** | Pipeline-роль аналитического/документационного типа (explainer/lisa/risk/decomposer/architect/auditor/documenter/retrospective): артефакты создаёт САМА роль, Forge их не генерирует → режим check_only/generate. | `LIGHT_ROLES`, RoleExecutorRegistry, RoleArtifactValidator | `core_02/forge_facade.py` |
| **HEAVY-роль** | Pipeline-роль с реальными side-effects кода/тестов (developer/tester/fixer/acceptance) → полный цикл ForgePipeline. | `HEAVY_ROLES`, ForgePipeline | `core_02/forge_facade.py` |
| **RoleExecutor / RoleExecutorRegistry** | Аддитивный слой автоисполнения LIGHT-ролей (ADR-016): реестр `role_id → executor`, отдельный от Scenario (Scenario = корпус данных). Executor НЕ вызывает Forge напрямую (§7.3). | `core_02/role_executor.py`, `BaseRoleExecutor`, `RoleExecutorRegistry` | ADR-016, `core_02/role_executor.py` |
| **LlmRoleExecutor** | LLM-экзекьютор LIGHT-роли: один вызов `ModelGateway.generate_by_capabilities` по blueprint-промпту → файлы (file-block протокол `@@FILE/@@ENDFILE`). | `core_02/role_executor.py`, ModelGateway | ADR-016 |
| **LisaExecutor** | Детерминированный executor роли lisa (обёртка `lisa_estimator`, без LLM) — пишет `lisa_report.md`. | `core_02/role_executor.py`, `lisa_estimator` | ADR-016 |
| **LISA (LISA-3)** | AI-Native Complexity Estimator: детерминированная оценка сложности проекта по 6 осям (engineering/ai-native/verification/operational/production/ai_suitability) + вердикт GO/COND/NO-GO. | `scripts_01/lisa_estimator.py`, `data_13/lisa_calibration.yaml` | `scripts_01/lisa_estimator.py` |
| **light_mode (check_only \| generate)** | Режим `run_chain` для LIGHT-ролей: `check_only` (валидация существования артефактов) \| `generate` (материализация через RoleExecutorRegistry). | `ForgeFacade.run_chain` | ADR-016, `core_02/forge_facade.py` |
| **chain / run_chain** | Прогон цепочки pipeline-ролей (PIPELINE_CHAIN) с per-role stage (check_only/generate/full_cycle/conditional_skip) + aggregated overall. | `ForgeFacade.run_chain`, `ChainStage`, `ChainRun` | `core_02/forge_facade.py` |
| **MissingRegistry / register-first** | Реестр недостающих элементов (capability/tool/engine/forge/role/модуль) с lifecycle `registered→design_ready→prompt_written→implemented`. Принцип: обнаружил недостающее → зафиксируй в реестре ДО реализации. | `core_02/missing_registry.py`, `data_13/missing_registry.yaml` | AGENTS.md §5; **→ см. также: backfill (MissingRegistry), §13** (machine-readable `backfill: bool` поле для retroactive-регистрации уже реализованного) |

---

## 13. Интеллектуальный слой: Scenario / Opportunity / Factory Registry (Phase 8–13)

> Термины интеллектуального слоя платформы (Phase 8–13): domain-neutral выбор подхода,
> opportunity-адаптер, авто-обнаружение фабрик, хранилище решений, организационная память/обучение
> и сущности выбора. Дополняют §12 (Factory), §4 (Memory/Knowledge) и §5 (Scenario).

| Термин | Каноническое определение | Связанные компоненты | Источник |
|--------|--------------------------|----------------------|----------|
| **ScenarioIntelligence** | Domain-neutral Universal Scenario Intelligence (Phase 8): `discover → evaluate → rank → select → resolve_capability → feedback`. Отвечает «какой подход лучше под Opportunity в контексте проекта», НЕ производит артефакты. Entities: ScenarioCandidate / CapabilityRequirement / ScenarioDecision. ForgeFacade — единственный execution boundary (модуль его НЕ вызывает). | `scripts_01/scenario_intelligence.py`, ScenarioCandidate, ScenarioDecision | `scripts_01/scenario_intelligence.py`, promt 091 |
| **OpportunityEngine** | Intelligence head поверх execution tail: `propose()` делегирует в ScenarioIntelligence.select (read-only адаптер) с BC-fallback на legacy ScenarioRegistry путь. | `scripts_01/opportunity_engine.py`, `_derive_capability` | `scripts_01/opportunity_engine.py`, promt 079 |
| **FactoryRegistry** | Авто-обнаружение + query API поверх декларативных YAML-манифестов `runtime_05/factories/<factory_id>/`. `select_forge(capability) → (factory_id, forge_id)`; `resolve_by_policy(capability)`; CODE_RESOLUTION_POLICY (D-2: factory-слой authoritative). | `core_02/factory_registry.py`, `runtime_05/factories/` | `core_02/factory_registry.py`, CANONICAL_ENGINE_ROUTING_V1.md |
| **DecisionHistoryStore** | Хранилище решений ScenarioIntelligence (YAML `data_13/scenario_decisions.yaml`, атомарный .tmp+replace): per-opportunity latest() для re-selection lifecycle. | `scenario_intelligence.py`, `data_13/scenario_decisions.yaml` | `scripts_01/scenario_intelligence.py`, promt 091 |
| **MemoryStore** | SQLite-хранилище Organizational Memory (`data_13/context.db`): knowledge objects + граф связей + learning events + analytics. `store_knowledge(kind, …)` (10 закрытых KNOWLEDGE_KINDS), `query_by_type`, `link_knowledge`, `record_learning_event`, `update_feedback` (confidence). | `core_02/memory_store.py`, KNOWLEDGE_KINDS, LIFECYCLE_STAGES | RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md §3–§5 |
| **LearningLoop** | AFC-цикл обучения (Analyze → Formalize → Codify): `analyze(situation) → Analysis` → `formalize` → KnowledgeObject → `codify` (LESSONS.md CON-N / DEBT / TG) → `record_feedback`. Прозрачный, БЕЗ ML/RL. | `core_02/learning_loop.py`, SemanticLayer | RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md §7 |
| **ScenarioCandidate** | Domain-neutral frozen dataclass — один кандидат-способ реализации Opportunity: scenario_id, display_name, role_id, score, reasons, evidence, capability, scenario_caps (full tuple), available. | `scripts_01/scenario_intelligence.py` | promt 091 |
| **CapabilityRequirement** | Domain-neutral capability token (capability, scenario_id, role_id) для `resolve_capability` → FactoryRegistry.select_forge → (factory_id, forge_id). | `scripts_01/scenario_intelligence.py`, FactoryRegistry | promt 091 |
| **ScenarioDecision** | Explainable результат селекции с полным provenance: opportunity_id, selected_scenario_id, score, reasons, evidence, capability, factory_id, forge_id, status. | `scripts_01/scenario_intelligence.py` | promt 091 |
| **backfill (MissingRegistry)** | Machine-readable поле `backfill: bool` в `MissingItem` (запись реестра `MissingRegistry`), фиксирующее факт **retroactive-регистрации** — элемент существовал до создания реестра и был внесён как `status: implemented` без прохождения lifecycle `registered→design_ready→prompt_written`. B10-инвариант: `backfill=true` ⇔ `status==implemented` (семантика: «зарегистрировано задним числом уже реализованное»). Альтернатива free-text маркеру `⚠️ BACKFILL (…)` в `description` устарела с v5.189.49. | `core_02/missing_registry.py`, `data_13/missing_registry.yaml` | CON-63 (register-first disciplinary rule), v5.189.49 (machine-readable field), B10/R-127 (schema invariants) |

---

_Связанные документы: [ARCHITECTURE_MANIFEST.md***REMOVED***(ARCHITECTURE_MANIFEST.md), [ARCHITECTURE_CANONICAL.md***REMOVED***(ARCHITECTURE_CANONICAL.md), [LIFECYCLE.md***REMOVED***(LIFECYCLE.md), [MODULE_CONSOLIDATION.md***REMOVED***(MODULE_CONSOLIDATION.md), [CORE_PROMPT.md***REMOVED***(CORE_PROMPT.md), [VISION_3.0.md***REMOVED***(../vision/VISION_3.0.md), [SYSTEM_INVENTORY.md***REMOVED***(SYSTEM_INVENTORY.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md)_
