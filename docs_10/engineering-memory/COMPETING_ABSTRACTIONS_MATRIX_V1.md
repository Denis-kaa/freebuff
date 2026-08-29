# COMPETING_ABSTRACTIONS_MATRIX_V1.md — Матрица конкурирующих абстракций

> **Статус:** ANALYTICAL (forensic-only, промт 108 §1 — код не изменялся).
> **Дата:** 2026-08-22
> **Основание:** промт 108 §13 (Competing Abstractions) — таблица «Абстракции / A отвечает за / B отвечает за /
> Дублирование / Различие / Решение».
> **Метод:** каждое утверждение — CLAIM → FILE:LINE (EVIDENCE, промт 108 §25).

---

## 0. Легенда решений (промт 108 §18)

KEEP / MERGE / SPLIT / RENAME / WRAP / ADAPTER / DEPRECATE / NEW CONTRACT / NEW COMPONENT.

---

## 1. FACTORY vs FORGE

| Поле | Значение |
|------|----------|
| **Абстракции** | Factory vs Forge |
| **A (Factory)** отвечает за | Организация capability: `factory.yaml`-манифест, factory-level capability-каталог, отбор (factory, forge)-пары |
| **B (Forge)** отвечает за | Конкретная кузня: `forge_id.yaml`, набор capability кузни, execution через `ForgeFacade.run_chain` |
| **Дублирование** | Оба — паспортные dataclass с IDENTICAL паттерном: `from_yaml` + `frozen=True` + tuple-списки + `validate()` + закрытый словарь KNOWN_CAPABILITIES (lazy-импорт из blueprint_v3). Почти зеркальные модули |
| **Различие** | Factory = **контейнер/организатор** capability (1 фабрика → N кузен); Forge = **исполнитель** capability. Связь: `select_forge(capability)` → (FactoryPassport, ForgePassport) |
| **Решение** | **KEEP** (разные уровни: организация vs исполнение) + мост уже сшит (ADR-018 Path B REAL). НЕ сливать — это B-Rule 1: разделяют state? Нет. Но зеркальный passport-паттерн — кандидат на единый базовый паспорт (NEW CONTRACT, low priority) |

**Evidence:**
- `factory_passport.py:8-9` «машиночитаемый контракт фабрики… `runtime_05/factories/<factory_id>/factory.yaml`»
- `forge_passport.py:8-9` «machine-readable кузня contract… `runtime_05/factories/<factory_id>/<forge_id>.yaml`»
- `factory_passport.py:10` «Pattern mirrors ForgePassport» (самодокументированное дублирование!)
- `factory_registry.py:272` `select_forge(capability, prefer_status)` — возвращает пару
- `factory_registry.py` docstring: status-priority production(3)>material(2)>design(1)

---

## 2. MEMORY vs KNOWLEDGE vs GRAPH (память)

| Поле | Значение |
|------|----------|
| **Абстракции** | MemoryEngine vs MemoryStore vs KnowledgeEngine vs GraphIndex vs SemanticLayer |
| **A (MemoryEngine)** отвечает за | 5 уровней памяти (WORKING/PROJECT/KNOWLEDGE/PERSONAL/ARCHIVE), файловая (level_dir/entry_path) |
| **B (MemoryStore)** отвечает за | SQLite `data_13/context.db`, knowledge-записи (kind), для accumulate-цикла Opportunity |
| **C (KnowledgeEngine)** отвечает за | FTS5 + TF-IDF полнотекстовый поиск по документам |
| **D (GraphIndex)** отвечает за | Графовые связи: Node/Edge, shortest_path, get_related |
| **E (SemanticLayer)** отвечает за | TF-IDF семантический поиск поверх knowledge (index_knowledge / semantic_search / find_similar_patterns) |
| **Дублирование** | **MemoryEngine vs MemoryStore** — две независимые memory-модели (файловая vs SQLite), обе хранят «знание». **KnowledgeEngine vs SemanticLayer** — два полнотекстовых поиска (FTS5 vs TF-IDF) по одному типу данных |
| **Различие** | MemoryEngine = уровни+файлы (быстрая↔постоянная); MemoryStore = SQLite kind-записи (для машинного цикла); KnowledgeEngine = retrieval; GraphIndex = связи; SemanticLayer = similarity |
| **Решение** | Memory ×4 — **НЕ сливать вслепую** (разные уровни системы: persistence / index / semantic layer / domain model — промт 108 §11). Но **MemoryEngine ↔ MemoryStore — кандидат на единый storage-контракт** (NEW CONTRACT, P2 baseline). **KnowledgeEngine ↔ SemanticLayer — кандидат на слой поверх одного индекса** (WRAP/ADAPTER) |

**Evidence:**
- `memory_engine.py:59` `MemoryLevel` (5 уровней); `:107 MemoryEngine`
- `memory_store.py:92` `MemoryStore` (db_path `data_13/context.db`, `:209 store_knowledge`)
- `knowledge_engine.py:224` `FtsIndex` (SQLite FTS5); `:45 _get_graph_index`
- `graph_index.py:110` `GraphIndex` (Node :80 / Edge :67 / shortest_path :432)
- `semantic_layer.py:39` `SemanticLayer` (`:89 semantic_search`, `:123 find_similar_patterns`)
- baseline §2: «Memory/Knowledge ×4 — нет единого source-of-truth»

---

## 3. KNOWLEDGE vs GRAPH

| Поле | Значение |
|------|----------|
| **Абстракции** | KnowledgeEngine vs GraphIndex |
| **A (KnowledgeEngine)** | Поиск по содержимому: FTS5-индекс + TF-IDF ранжирование |
| **B (GraphIndex)** | Структурные связи: узлы/рёбра, соседи, пути |
| **Дублирование** | Оба — SQLite-индексы с одинаковым жизненным циклом (index/remove/search); оба пишут в `data_13/` |
| **Различие** | content-retrieval vs relationship-retrieval (принципиально разные операции) |
| **Решение** | **KEEP** (разные операции, B-Rule 2: терпимы к отсутствию друг друга). Единый источник данных — общий. Дублирование storage можно объединить (P2) |

**Evidence:** `knowledge_engine.py:224 FtsIndex`; `graph_index.py:110 GraphIndex`

---

## 4. AGENT vs ROLE vs RUNTIME (исполнители)

| Поле | Значение |
|------|----------|
| **Абстракции** | IAgent vs AgentNode/AgentMesh vs BaseRoleExecutor vs STANDARD_ROLES vs RuntimeRegistry |
| **A (IAgent)** | ABC-интерфейс агента: `name/version/run()` — LEVIATHAN-паттерн |
| **B (AgentNode/AgentMesh)** | Распределённый mesh-узел: статусы PENDING/CONNECTING/ONLINE/BUSY/ERROR/OFFLINE, capabilities |
| **C (BaseRoleExecutor)** | Исполнитель pipeline-роли: `execute(project, role_id)` (LisaExecutor, LlmRoleExecutor) |
| **D (STANDARD_ROLES)** | 6 collab-ролей (developer/reviewer/documenter/researcher/archiver/orchestrator) + маппинг → owner/editor/viewer |
| **E (RuntimeRegistry)** | Реестр runtimes (плагин freebuff_plugin_03) |
| **Дублирование** | **Три модели «кто исполняет»**: IAgent (интерфейс), AgentNode (mesh), BaseRoleExecutor (роль) — пересекаются по концепции «агент с capabilities». **Две role-системы**: PIPELINE_ROLES (14, forge_facade) vs STANDARD_ROLES (6, roles.py) — имена пересекаются (developer, documenter) |
| **Различие** | IAgent = контракт; AgentNode = сетевая сущность; BaseRoleExecutor = исполнитель роли в forge-контексте; STANDARD_ROLES = collab-права; RuntimeRegistry = среда исполнения |
| **Решение** | **NEW COMPONENT (ADR-019 Proposed)** — единый Agent base class поверх RoleExecutor; **RENAME/namespace** роли (pipeline vs collab — baseline §2 Role ×2); KEEP IAgent как интерфейс |

**Evidence:**
- `interfaces.py:50` `class IAgent(ABC)` (`:68 async run`)
- `distributed_agents.py:111` `class AgentNode` (`:77 AgentNodeStatus`), `:249 AgentMesh`
- `role_executor.py:49` `BaseRoleExecutor`, `:69 RoleExecutorRegistry`, `:223 LlmRoleExecutor`, `:105 LisaExecutor`
- `roles.py:54` `STANDARD_ROLES` (6), `:395 get_collab_role` (orchestrator→owner, developer/reviewer→editor)
- `forge_facade.py:64` `PIPELINE_ROLES` (14)
- `mcp_server.py:359` `RuntimeRegistry` (plugin)

---

## 5. TOOL RUNTIME vs MCP TOOL

| Поле | Значение |
|------|----------|
| **Абстракции** | BaseTool×5 (tool_runtime.py) vs McpTool (mcp_server.py) |
| **A (BaseTool)** | Инструменты: GitTool/SQLiteTool/HTTPTool/FileTool/ShellTool — единый контракт meta/execute/validate_params; ToolRegistry |
| **B (McpTool)** | MCP-инструмент (JSON-RPC): rpc_response/rpc_error, session |
| **Дублирование** | Два tool-контракта; McpTool НЕ наследует BaseTool (разные интерфейсы) |
| **Различие** | Внутренний API (Python-вызовы) vs внешний протокол (JSON-RPC) |
| **Решение** | **ADAPTER** — MCP-слой как адаптер поверх ToolRegistry (промт 108 §15 Integration), не отдельная модель (baseline §2 Tool ×2, P2) |

**Evidence:** `tool_runtime.py:107 BaseTool`, `:616 ToolRegistry`; `mcp_server.py:88 McpTool`

---

## 6. TASK vs ORCHESTRATOR vs OPPORTUNITY

| Поле | Значение |
|------|----------|
| **Абстракции** | task_manager.py vs orchestrator.py vs Opportunity (opportunity_engine.py) |
| **A (task_manager)** | SQLite-задачи с FK на projects |
| **B (orchestrator)** | FSM/DAG-оркестрация шагов |
| **C (Opportunity)** | «Задача-намерение» с roles+lifecycle (ACTIVE/READY/DEFERRED/COMPLETED/FAILED) → сценарий → фабрика → forge |
| **Дублирование** | Task vs Opportunity — обе «задачи», разные lifecycle; orchestrator — третий механизм |
| **Различие** | task_manager = персистентные задачи; Opportunity = эфемерная сущность для forge-цикла (B-Rule 3: разный lifecycle); orchestrator = исполнение шагов |
| **Решение** | **KEEP с контрактом** — Opportunity ≠ Task (ADR-018 Alternatives (б)); orchestrator vs task_manager — кандидат на разграничение контрактов (P2) |

**Evidence:** `task_manager.py:122` FK; `orchestrator.py` (FSM/DAG); `opportunity_engine.py:144 class Opportunity` (`:157 artifacts`, roles, lifecycle)

---

## 7. WORKSPACE vs WORKSPACE_REGISTRY

| Поле | Значение |
|------|----------|
| **Абстракции** | workspace.py vs workspace_registry.py |
| **A (workspace.py)** | Файловый YAML-конфиг: Workspace.load/list_projects/get_project, Project.load |
| **B (workspace_registry.py)** | SQLite mapping/privacy: реестр проектов |
| **Дублирование** | Две модели Project (`workspace.py:126` vs `workspace_registry.py:93`) |
| **Различие** | Конфиг (декларативный) vs mapping (оперативный) — **ADR-017 осознанно разделил** (SQLite = mapping/privacy, YAML = конфиг, sync-контракт) |
| **Решение** | **KEEP BY DESIGN (ADR-017)** — не дублирование, а два уровня; sync-контракт зафиксировать кодом (P0/ADR-017 реализация) |

**Evidence:** `workspace.py:126/331/365/368`; `workspace_registry.py:93`; ADR-017

---

## 8. SCENARIO vs SCENARIO INTELLIGENCE

| Поле | Значение |
|------|----------|
| **Абстракции** | ScenarioRegistry vs scenario_intelligence.py |
| **A (ScenarioRegistry)** | Каталог сценариев: manifest+класс, list/get/filter/propose_roles/find_role |
| **B (ScenarioIntelligence)** | Выбор: ScenarioDiscovery → candidates → evaluation → ranking → selection (ScenarioDecision) |
| **Дублирование** | Registry даёт propose_roles; Intelligence — тоже про выбор сценария. Пересечение: обе выбирают роли/сценарий |
| **Различие** | Registry = каталог+поиск (storage); Intelligence = оценка/ранжирование (decision layer, отдельный промт 091) |
| **Решение** | **KEEP** — storage vs decision (промт 091 §5/§6: реюзает ScenarioRegistry, NO second registry). Уточнить контракт: Registry отдаёт кандидатов, Intelligence ранжирует |

**Evidence:** `scenario_registry.py:65/143/147/151/202`; `scenario_intelligence.py:339-341` «ScenarioRegistry as catalog — NO second registry»

---

## 9. Сводная таблица решений

| Пара | Дублирование | Решение |
|------|-------------|---------|
| Factory vs Forge | Паспорт-паттерн (зеркальный) | KEEP + единый базовый паспорт (NEW CONTRACT, low) |
| MemoryEngine vs MemoryStore | Две memory-модели | KEEP + единый storage-контракт (P2) |
| KnowledgeEngine vs SemanticLayer | Два полнотекстовых поиска | WRAP/ADAPTER (P2) |
| Knowledge vs Graph | Два SQLite-индекса | KEEP (разные операции) |
| IAgent vs AgentNode vs BaseRoleExecutor | Три «исполнителя» | NEW COMPONENT (ADR-019) |
| PIPELINE_ROLES vs STANDARD_ROLES | Две role-системы, имена пересекаются | RENAME/namespace (baseline §2) |
| BaseTool vs McpTool | Два tool-контракта | ADAPTER (MCP поверх ToolRegistry) |
| Task vs Opportunity vs Orchestrator | Три «задачи» | KEEP с контрактом (разные lifecycle) |
| workspace.py vs workspace_registry.py | Две модели Project | KEEP BY DESIGN (ADR-017) + sync-код |
| ScenarioRegistry vs ScenarioIntelligence | Обе про выбор сценария | KEEP (storage vs decision) |

---

## 10. Ключевые находки

1. **Factory↔Forge — зеркальный паспорт-паттерн** — единственное прямое дублирование структуры (самодокументировано: «Pattern mirrors ForgePassport»). Решение: единый базовый класс паспорта — но низкий приоритет, не блокер.
2. **Три модели «исполнителя»** (IAgent/AgentNode/BaseRoleExecutor) — самое концептуальное пересечение; ADR-019 (Proposed) адресует.
3. **Две role-системы с пересекающимися именами** (developer/documenter и в 14 pipeline-ролях, и в 6 collab-ролях) — реальный риск путаницы; нужен namespace (baseline §2 Role ×2).
4. **Memory×4 — не одно дублирование, а 3 разных уровня** (persistence/index/semantic/domain) — сливать нельзя, нужны контракты (промт 108 §11).
5. **Task vs Opportunity — осознанное различие** (жизненный цикл), НЕ дублирование (ADR-018).

---

## 11. История

- **v1.0 (2026-08-22):** построена по промт 108 §13; перекрёстно сверена с `BASELINE_V1_CODE_VERIFICATION.md` и
  `CONTRACT_GRAPH_V1.md`. Код НЕ изменялся (промт 108 §1).
