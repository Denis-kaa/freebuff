# ARCHITECTURE_DECISION_108_V1.md — EXECUTIVE ARCHITECTURE DECISION (промт 108)

> **Статус:** ANALYTICAL · CODE = READ ONLY (промт 108 §1/§27) · код НЕ изменялся.
> **Дата:** 2026-08-22
> **Входные материалы:** ARCHITECTURAL_BASELINE_V1.md, форензика 104–107
> (UNIFIED_CONCLUSIONS / EVIDENCE_LEDGER_MERGED / AUDIT_DELTA / CONTRACT_GRAPH),
> собственные verification-документы: BASELINE_V1_CODE_VERIFICATION.md,
> CONTRACT_GRAPH_V1.md, COMPETING_ABSTRACTIONS_MATRIX_V1.md.
> **Основание:** промт 108 §24 A–M, §25 Evidence Rule, §26 Final Verdict.

---

## A. EXECUTIVE ARCHITECTURE DECISION (кратко)

### Какая модель подтверждается

| Модель (промт 108) | Статус | Evidence |
|--------------------|--------|----------|
| **WHIM** (лёгкая фиксация мысли) | ✅ **CONFIRMED** — `scripts_01/whim_capture.py::WhimStore` (whims.yaml), статусы NEW/TRIAGED/DEFERRED/PROMOTED/DISCARDED/FAILED; DISCOVER-стадия конвертирует whim → Opportunity | `whim_capture.py:130 class Whim`, `:172 class WhimStore`; `opportunity_engine.py:343` (WhimStore → Opportunity) |
| **WORKSPACE** (среда, контейнер деятельности) | ✅ **CONFIRMED** (2 представления — ADR-017) | `workspace.py:321 Workspace`, `workspace_registry.py` |
| **PROJECT** (граница работы) | ✅ **CONFIRMED** (но 2 модели — PARTIAL) | `workspace.py:126 Project` vs `workspace_registry.py:93 Project` |
| **SCENARIO** (композиция/план класса задач) | ✅ **CONFIRMED** — ScenarioRegistry как каталог + propose_roles | `scenario_registry.py:65`, `:202 propose_roles`; Scenario = ABC + Role + ScenarioManifest |
| **FACTORY** (организация capability) | ✅ **CONFIRMED** — FactoryPassport + FactoryRegistry.select_forge | `factory_passport.py`, `factory_registry.py:272 select_forge` |
| **FORGE** (исполнитель) | ✅ **CONFIRMED** — ForgeFacade.run_chain, 14 ролей | `forge_facade.py:479 run_chain` |
| **ARTIFACT** | ✅ **CONFIRMED** — единый `core_02.artifact.Artifact` объединяет 3 проекции; `normalize_output` подключён (v5.189.78) | `core_02/artifact.py`, `factory_base.py::normalize_output`, `tests_09/test_artifact.py` |
| Сквозной ОДИН конвейер Project→Scenario→Factory→Forge→Artifact | ❌ **ОПРОВЕРГНУТА** — реальны 2 независимые ветки Path A + Path B | baseline §3, CONTRACT_GRAPH G4–G8 |

### Главный архитектурный центр

**ForgeFacade** — единственная санкционированная точка исполнения (§7.3 grep-инвариант):
`forge_facade.py:7` «ForgePipeline инстанцируется ТОЛЬКО здесь». Всё остальное (Opportunity Engine,
BaseFactory, chain-CLI) сходится в него. Второй центр — **capability-роутинг** (closed-set токенов).

### Где главные конфликты

1. **WORKSPACE→PROJECT: 2 модели Project** (файловая + SQLite) — PARTIAL, ADR-017 (design), runtime-синк не автоматизирован.
2. **TASK→SCENARIO: Opportunity как недостающее звено** — в коде сценарий выбирает Opportunity, не Task (модель промта 108 не содержит Opportunity на этом месте).
3. **FORGE→ARTIFACT: контракт реализован** — `Artifact` объединяет 3 проекции (файл/dict/ChainRun); адаптер подключён в `factory_base.normalize_output` (v5.189.78).
4. **AGENT: IMPLICIT** — роли исполняются executor-ами; единого Agent-класса нет (ADR-019).
5. **Memory×4 / Task×2 / Tool×2 / Role×2** — дубли механизмов (baseline §2).

---

## B. DOMAIN RESPONSIBILITY MAP (карта ответственности)

| Домен | Ответственность | Файл | Статус |
|-------|----------------|------|--------|
| Whim | Захват мысли, классификация, lifecycle | scripts_01/whim_capture.py | REAL |
| Workspace | Контейнер деятельности: список/резолв проектов | core_02/workspace.py | REAL |
| WorkspaceRegistry | SQLite-mapping/privacy проектов | core_02/workspace_registry.py | REAL (ADR-017) |
| Project | Граница работы: контекст, артефакты, RUNNABLE/CHECKLIST | core_02/workspace.py:126 | REAL |
| Task | Задачи с FK на проект | scripts_01/task_manager.py | REAL |
| Opportunity | «Задача-намерение»: DISCOVER→PROPOSE→EXECUTE→VALIDATE→ACCUMULATE | scripts_01/opportunity_engine.py | REAL |
| Scenario | Каталог сценариев + роли + propose_roles | core_02/scenario.py, scenario_registry.py | REAL |
| ScenarioIntelligence | Ранжирование/выбор сценария (decision) | scripts_01/scenario_intelligence.py | REAL |
| Factory | Организация capability, (factory, forge)-пара | core_02/factory_registry.py | REAL |
| Forge | Исполнение: ForgeFacade→ForgePipeline→ForgeRegistry | core_02/forge_facade.py | REAL |
| RoleExecutor | Исполнение роли (Lisa/Llm) — ADR-016 | core_02/role_executor.py | REAL |
| Artifact | Единый канонический контракт + проекции файл/dict/ChainRun | core_02/artifact.py | REAL (v5.189.78) |
| Memory/Knowledge/Graph | 4 механизма: уровни/SQLite/FTS5/граф | scripts_01/, core_02/ | REAL ×4 |
| Integration | Мосты TG/MCP/phone — вшиты в ядро | telegram_contract, mcp_server, phone_control_mcp | DOCUMENTED ONLY |
| Sandbox/ACL | Отсутствует; boundaries_v17 — декларативный реестр | core_02/boundaries_v17.py | MISSING (runtime) |

---

## C. COMPETING ABSTRACTIONS MATRIX (сводка — полная версия в COMPETING_ABSTRACTIONS_MATRIX_V1.md)

| Пара | Дублирование | Решение |
|------|-------------|---------|
| Factory vs Forge | Зеркальный passport-паттерн | KEEP + единый базовый паспорт (low) |
| MemoryEngine vs MemoryStore | 2 memory-модели | KEEP + единый storage-контракт (P2) |
| KnowledgeEngine vs SemanticLayer | 2 полнотекстовых поиска | WRAP/ADAPTER (P2) |
| Knowledge vs Graph | 2 SQLite-индекса | KEEP (разные операции) |
| IAgent vs AgentNode vs BaseRoleExecutor | 3 «исполнителя» | NEW COMPONENT (ADR-019) |
| PIPELINE_ROLES vs STANDARD_ROLES | 2 role-системы, имена пересекаются | RENAME/namespace |
| BaseTool vs McpTool | 2 tool-контракта | ADAPTER (MCP поверх ToolRegistry) |
| Task vs Opportunity vs Orchestrator | 3 «задачи» | KEEP с контрактом (разные lifecycle) |
| workspace.py vs workspace_registry.py | 2 модели Project | KEEP BY DESIGN (ADR-017) + sync-код |
| ScenarioRegistry vs ScenarioIntelligence | Обе про выбор сценария | KEEP (storage vs decision) |

---

## D. AGENT / ROLE / MODEL / CAPABILITY MODEL

| Сущность | Определение (по коду) | Evidence |
|----------|----------------------|----------|
| **Agent** | Нет единой сущности. 3 представления: `IAgent` (ABC-контракт), `AgentNode` (mesh-узел), `BaseRoleExecutor` (исполнитель роли) | interfaces.py:50, distributed_agents.py:111, role_executor.py:49 |
| **Role** | 2 системы: PIPELINE_ROLES (14, forge) vs STANDARD_ROLES (6, collab) + маппинг → owner/editor/viewer | forge_facade.py:64, roles.py:54/395 |
| **Model** | ModelCatalog + SmartRouter (capability→модель, closed-set) | router.py:82/239, blueprint_v3.py:159 KNOWN_CAPABILITIES |
| **Capability** | Закрытый токен KNOWN_CAPABILITIES; паспорта валидируют (ValueError при drift) | blueprint_v3.py:159, factory_passport.py:33 |
| **Runtime** | RuntimeRegistry (плагин) | mcp_server.py:359 |
| Может ли один Agent выполнять разные роли? | В коде: AgentNode имеет capabilities-набор; collab-маппинг допускает смену роли | distributed_agents.py:101 AgentCapability |
| Кто определяет исполнителя? | Capability → select_forge (factory_registry) + role_ids → run_chain | factory_registry.py:272, forge_facade.py:479 |

---

## E. WORKSPACE / PROJECT MODEL

- **Workspace** — среда (корень Termux): `Workspace.load/list_projects/get_project` (workspace.py:331/365/368).
- **Project** — **две модели**: файловая (workspace.py:126, YAML-конфиг, RUNNABLE/CHECKLIST) и
  SQLite-mapping (workspace_registry.py:93, privacy). ADR-017: SQLite = mapping/privacy, YAML = конфиг, sync-контракт.
- **Статус:** PARTIAL — дизайн закрыт (ADR-017), runtime-синхронизация двух моделей в коде не автоматизирована.

---

## F. SCENARIO / FACTORY / FORGE MODEL (реальные границы)

```
Scenario (каталог, propose_roles)
    │  capability-токен (закрытый словарь)
    ▼
FactoryRegistry.select_forge(capability) → (FactoryPassport, ForgePassport)
    │  role_ids (единственный управляющий вход)
    ▼
ForgeFacade.run_chain(project, role_ids)   ← ЕДИНСТВЕННЫЙ execution boundary (§7.3)
    │  LIGHT: RoleArtifactValidator · HEAVY: ForgePipeline · CONDITIONAL: frontend/devops
    ▼
ChainRun → Artifact (файл + dict)
```

- Scenario НЕ вызывает Forge напрямую (§7.3 — только через Project/Facade). **CONFIRMED**.
- Factory и Forge — **разные уровни** (организация vs исполнение), НЕ одно и то же. **CONFIRMED**.
- forge_id — **адвизорный** (traceability), исполнение по role_ids. **CONFIRMED** (ADR-018).

---

## G. CONTRACT GRAPH (полная версия — CONTRACT_GRAPH_V1.md)

| Переход | Статус | Evidence |
|---------|--------|----------|
| USER→WORKSPACE | CONFIRMED | mcp_server.py:236, telegram_bot.py:57 |
| WORKSPACE→PROJECT | PARTIAL (2 модели) | workspace.py:126 vs workspace_registry.py:93 |
| PROJECT→TASK | CONFIRMED | task_manager.py:122 (FK) |
| TASK→SCENARIO | PARTIAL (через Opportunity) | opportunity_engine.py:823 propose_roles |
| SCENARIO→FACTORY | CONFIRMED | factory_registry.py:272 select_forge |
| FACTORY→FORGE | CONFIRMED | factory_base.py:368, opportunity_engine.py:949, forge.py:490 |
| FORGE→AGENT/ROLE/TOOL | CONFIRMED (Agent IMPLICIT) | role_executor.py:61, forge_facade.py:679 |
| FORGE→ARTIFACT | CONFIRMED (Artifact contract v5.189.78) | core_02/artifact.py, factory_base.py::normalize_output |
| ARTIFACT→MEMORY | CONFIRMED | opportunity_engine.py:1000 accumulate, memory_store.py:92 |

**Итого: 7 CONFIRMED · 2 PARTIAL · 0 MISSING · 0 CONFLICTING.**

---

## H. GAP MAP (чего не хватает)

| Приоритет | GAP | Статус |
|-----------|-----|--------|
| P0 | Единая Workspace модель (sync-контракт двух Project) | ✅ design (ADR-017), реализация — отдельный заход |
| P0 | Sandbox / tool-ACL для внешних мостов (ShellTool) | ❌ открыт |
| P1 | Factory→Forge execution-мост | ✅ ЗАКРЫТ (Path B REAL, ADR-018) |
| P1 | Agent base class + lifecycle | ❌ открыт → ADR-019 |
| P1 | Integration adapter boundary | ❌ открыт → ADR-020 |
| P2 | Дубли: task ×2, tool ×2, memory ×4 | ❌ открыты |
| P2 | Единый Artifact-контракт | ✅ реализован (v5.189.78; 13 hermetic-тестов) |
| P3 | Репозиторий: нумерация каталогов, смешение доменов | ❌ открыт |
| P4 | Enhancements (семантические теги, метрики, UX) | ❌ после P0-P2 |

---

## I. TARGET ARCHITECTURE

```
WORKSPACE OS
│
├── WORKSPACES ── PROJECT (граница контекста)
│       └── PEOPLE · AGENTS · ROLES · TASKS · KNOWLEDGE · MEMORY · ARTIFACTS · EVENTS
├── INTELLIGENCE (Opportunity Engine + ScenarioIntelligence — выбор «что делать»)
├── SCENARIOS (каталог + propose_roles)
├── FACTORIES (организация capability)
│       ├── FORGES (исполнение: ForgeFacade — единый мост)
│       ├── SKILLS/ROLE_EXECUTORS (ADR-016/019)
│       └── TOOLS (ToolRegistry)
├── RUNTIMES (RuntimeRegistry)
├── INTEGRATIONS (мосты TG/MCP/phone — ADR-020)
└── GOVERNANCE (boundaries_v17 → runtime-ACL, sandbox)
```

**Принципы:** существующую систему привести к модели через контракты и аккуратное разделение
ответственности (промт 108 §22). НЕ создавать NewWorkspace/NewProject/NewFactory/NewForge.
Ядро (Forge-слой + capability-роутинг) уже соответствует модели.

---

## J. TARGET REPOSITORY STRUCTURE (предложение — НЕ реализация)

Текущая структура (workspace.py/forge_facade.py в core_02, task_manager в scripts_01) исторически
смешана. Целевой принцип (промт 108 §20): *«код конкретного домена рядом с его контрактами, тестами
и реализацией; глобальная документация не смешивается с runtime-кодом»*.

Предлагаемый маппинг (Phase 3, аддитивный — НЕ переименование на месте):

| Домен | Текущее | Целевое |
|-------|---------|---------|
| Workspace/Project | core_02/workspace.py | platform/core/workspace/ |
| Scenario | core_02/scenario*.py | platform/core/scenario/ |
| Factory/Forge | core_02/factory_*, forge_* | platform/core/factory/, platform/core/forge/ |
| Agent/Role | core_02/role_executor.py, interfaces.py | platform/core/agent/ |
| Task | scripts_01/task_manager.py | platform/core/task/ |
| Memory/Knowledge | scripts_01/memory_engine.py и др. | platform/core/memory/ |
| Integration | telegram_contract, mcp_server, phone_control_mcp | platform/integrations/ |
| Contracts | — | platform/contracts/ |

**Решение:** отложить (P3) — репозиторий не блокирует архитектуру; перемещение вторично к контрактам.

---

## K. REFACTOR ROADMAP (безопасная последовательность — промт 108 §21)

| Фаза | WHAT | WHY | Статус |
|------|------|-----|--------|
| Phase 0 | Architecture baseline | Единая точка отсчёта | ✅ ARCHITECTURAL_BASELINE_V1 (2026-08-22) |
| Phase 1 | Contracts | P1-контракты: Factory→Forge, Agent, Integration | ✅ ADR-018 (REAL), ADR-019/020 (Proposed) |
| Phase 2 | Boundary adapters | MCP поверх ToolRegistry, Knowledge↔SemanticLayer | ⏳ P2 |
| Phase 3 | Move/organize | Домены → platform/core/* | ⏳ P3 |
| Phase 4 | Remove duplicated abstractions | task ×2, tool ×2, memory ×4 — контракты | ⏳ P2 |
| Phase 5 | Implement missing links | Sync Workspace-моделей | ⏳ P0 |
| Phase 6 | Integration layer | Мосты TG/MCP/phone → ADR-020 boundary | ⏳ P1 |
| Phase 7 | UI | Web-first (buffy-playground_19) | ⏳ после P0-P2 |

Каждый шаг: WHAT/WHY/FILES/DEPENDENCIES/RISKS/ROLLBACK/TESTS (промт 108 §21) — формат новых ADR.

---

## L. MIGRATION RISKS

1. **Слияние двух моделей Project** — риск сломать privacy-инварианты (workspace_registry) и YAML-конфиги.
2. **Namespace ролей** — риск дрейфа vocabulary (ANTI-6b): переименование должно идти через closed-set + реестр.
3. **Единый Artifact-контракт** — реализован в v5.189.78; сохранены двусторонние проекции Opportunity/Forge, включая timestamps и registry status.
4. **Integration adapter (ADR-020)** — риск «вшитых» мостов (TG/MCP/phone): только аддитивная обёртка,
   не переписывание.
5. **Порядок P0→P1→P2** — нарушение порядка накапливает непроверяемые модули (ANTI-5).

---

## M. ARCHITECTURE DECISION RECORDS (новые, из этой сессии)

| ADR-ID | Решение | Evidence | Статус |
|--------|---------|----------|--------|
| ADR-018 | Factory→Forge execution bridge (мост СШИТ, контракт) | opportunity_engine.py:949, factory_base.py:368, forge.py:490 | ✅ Proposed → реализация тестов (v5.189.77) |
| ADR-019 | Agent base class + lifecycle | baseline §3 AGENT DOCUMENTED ONLY | 🟡 Proposed |
| ADR-020 | Integration adapter boundary | baseline §3 Integration DOCUMENTED ONLY | 🟡 Proposed |
| ADR-017 | Единая Workspace модель (SQLite+YAML) | workspace.py vs workspace_registry.py | ✅ Proposed |
| **ADR-021 / Artifact** | Единый Artifact-контракт (P2) | `core_02/artifact.py`; `factory_base.py::normalize_output`; `tests_09/test_artifact.py` | ✅ реализован v5.189.78 |
| **NEW** | Единый базовый passport (Factory/Forge) | factory_passport.py:10 «Pattern mirrors ForgePassport» | ⚠️ обнаружен, низкий приоритет |

---

## §23. ФИНАЛЬНЫЙ ВОПРОС — «Если пользователь завтра создаёт проект "Создание автомобиля"»

### КАК ДОЛЖНО БЫТЬ (DESIRED, промт 108 §3–§16)

```
WHIM («Я хочу создать автомобиль»)
 ↓
PROJECT («Создание автомобиля» — идентичность, граница)
 ↓
COMPANION/DISCUSSION (понимание, цели)
 ↓
SCENARIO (исследовать рынок → ЦА → конкуренты → требования → концепция → дизайн → техника → сборка → тесты)
 ↓
FACTORY (Research/Design/Development Factory — организация capability)
 ↓
FORGE (Competitor Research Forge / Design Forge / Dev Forge)
 ↓
AGENT/ROLE/TOOL (исполнители)
 ↓
ARTIFACT (исследование, дизайн, код)
 ↓
PROJECT KNOWLEDGE (память проекта)
 ↓
NEXT ACTION (следующий шаг)
```

### КАК ЕСТЬ СЕЙЧАС (ACTUAL — верифицировано кодом)

```
WHIM  ✅  whim_capture.py:WhimStore (whims.yaml) — «Я хочу создать автомобиль» записывается
 ↓
OPPORTUNITY  ✅  opportunity_engine DISCOVER: Whim → Opportunity (source="whim")  [opportunity_engine.py:343-396***REMOVED***
 ↓
PROJECT  ⚠️  _resolve_project(opp) → Project.load(projects_17/<id>)  [opportunity_engine.py:939***REMOVED***
          ДВЕ модели Project: workspace.py:126 (YAML) vs workspace_registry.py:93 (SQLite) — ADR-017 design
 ↓
SCENARIO  ✅  propose(): ScenarioRegistry.propose_roles(opp.title+description, top_n=3)
          [opportunity_engine.py:823, scenario_registry.py:202***REMOVED***
 ↓
FACTORY  ✅  execute(): _select_factory_forge → FactoryRegistry.select_forge(capability)
          [opportunity_engine.py:736, factory_registry.py:272***REMOVED***
          provenance['factory_selection'***REMOVED*** = {factory_id, forge_id, capability***REMOVED***  [opportunity_engine.py:918-927***REMOVED***
 ↓
FORGE  ✅  ForgeFacade.run_chain(project, role_ids)  [opportunity_engine.py:949***REMOVED***
          ЕДИНСТВЕННЫЙ execution boundary (§7.3) → ForgePipeline (HEAVY) / RoleArtifactValidator (LIGHT)
 ↓
AGENT/ROLE/TOOL  ✅  role_executor (LlmRoleExecutor/LisaExecutor) + 14 pipeline-ролей
          [role_executor.py:49/223, forge_facade.py:64***REMOVED***
 ↓
ARTIFACT  ⚠️  opp.artifacts = [{"raw": ChainRun.to_dict()***REMOVED******REMOVED***  [opportunity_engine.py:963***REMOVED***
           + файлы RUNNABLE/CHECKLIST в проекте [forge_pipeline.py:271-280***REMOVED***
           + target: projects_17/<id>/forge/  [factory_base.py:316***REMOVED***
           единый Artifact-контракт с 3 проекциями (CONFIRMED, v5.189.78)
 ↓
MEMORY  ✅  accumulate(): MemoryStore kind=candidate + LearningLoop  [opportunity_engine.py:1000, memory_store.py:92***REMOVED***
          На ОБОИХ исходах (COMPLETED → success, FAILED → failure)  [opportunity_engine.py:935/956/987/995***REMOVED***
 ↓
NEXT ACTION  ✅  lifecycle: READY → COMPLETED/FAILED, DEFERRED → REACTIVATED
          [opportunity_engine.py:17-30, advance()***REMOVED***
```

### Расшифровка каждого «?» из модели (промт 108 §23)

| «?» в модели | Фактическое состояние |
|--------------|----------------------|
| Whim → ? → Project | ✅ Whim → **Opportunity** → Project (DISCOVER, opportunity_engine.py:343) |
| Project → ScenarioRegistry | ⚠️ Через **Opportunity**, не напрямую (propose_roles, :823) |
| Scenario → ? → ForgeFacade | ✅ Scenario → capability → **FactoryRegistry.select_forge** → ForgeFacade.run_chain (:736, :949) |
| ForgeFacade → ... | ✅ run_chain → RoleExecutor/ForgePipeline → артефакт → accumulate |

**Вывод:** из 9 проверенных переходов **7 CONFIRMED, 2 PARTIAL** (Project ×2 и Task→Scenario через Opportunity). Artifact-контракт реализован в v5.189.78.
Opportunity Engine — это НЕ недостающее звено, а **реализация Whim→…→Forge в одном vertical slice**
(promt 079): модель промта 108 просто не содержала Opportunity на этом месте. Это MODEL PARTIAL,
не MODEL MISMATCH — код уже реализует цепочку целиком, но через промежуточную сущность.

---

## §26. FINAL VERDICT

### ARCHITECTURE STATUS

```
[ ***REMOVED*** MODEL CONFIRMED
[X***REMOVED*** MODEL PARTIALLY CONFIRMED   ← ИТОГ
[ ***REMOVED*** MODEL REQUIRES REVISION
[ ***REMOVED*** MAJOR BOUNDARY CONFLICTS
```

Ядро модели (Whim → Opportunity → Scenario → Factory → Forge → Artifact → Memory) **подтверждено кодом**
на 7/9 проверенных переходов. PARTIAL: (1) Project — 2 модели (ADR-017 design, runtime-синк не автоматизирован); (2) Task→Scenario — связь проходит через Opportunity, а не напрямую.
Artifact-контракт реализован (v5.189.78); Agent остаётся IMPLICIT по ADR-019. Конфликтов границ
(CONFLICTING) не обнаружено.

### TOP 10 ARCHITECTURAL DECISIONS (до начала рефакторинга)

| # | Решение | Приоритет |
|---|---------|-----------|
| 1 | **Утвердить ARCHITECTURAL_BASELINE_V1 как Canon** (с правками из BASELINE_V1_CODE_VERIFICATION: evidence-строки :949/:368/:490, 7 стадий lifecycle, уточнение AGENT) | P0 |
| 2 | **Утвердить ADR-018** (Factory→Forge мост REAL, forge_id адвизорный) — реализация тестов уже сделана (v5.189.77) | P0 |
| 3 | **Утвердить ADR-017** (единая Workspace модель) + реализовать sync-контракт двух моделей Project в коде | P0 |
| 4 | **Реализовать единый Artifact-контракт** (файл ↔ dict ↔ ChainRun) — `core_02/artifact.py` | ✅ v5.189.78 |
| 5 | **Утвердить ADR-019** (Agent base class поверх RoleExecutor) — закрыть AGENT IMPLICIT | P1 |
| 6 | **Утвердить ADR-020** (Integration adapter boundary) — мосты TG/MCP/phone аддитивно | P1 |
| 7 | **Sandbox/tool-ACL для ShellTool** (P0-блокер, boundaries_v17 → runtime-ACL) | P0 |
| 8 | **Namespace ролей** (PIPELINE_ROLES vs STANDARD_ROLES) через closed-set + GLOSSARY (ANTI-6b) | P2 |
| 9 | **Единый базовый passport** (Factory/Forge зеркальный паттерн) — низкий приоритет | P2 |
| 10 | **Дубли P2** (task ×2, tool ×2, memory ×4) — контракты через MissingRegistry (REGISTER-FIRST) | P2 |

---

## Сводка сессии (все артефакты промта 108)

| Документ | Содержание |
|----------|-----------|
| `BASELINE_V1_CODE_VERIFICATION.md` | Проверка ARCHITECTURAL_BASELINE_V1 против кода (7 расхождений, evidence-строки) |
| `CONTRACT_GRAPH_V1.md` | Граф USER→…→MEMORY: 7 CONFIRMED · 2 PARTIAL (Artifact обновлён) |
| `COMPETING_ABSTRACTIONS_MATRIX_V1.md` | 10 пар, решения KEEP/MERGE/ADAPTER/NEW |
| `ARCHITECTURE_DECISION_108_V1.md` | **Этот документ** — EXECUTIVE DECISION + Final Verdict + TOP 10 |

---

## История

- **v1.0 (2026-08-22):** создан по итогам выполнения промта 108 (вход: форензика 104–107 +
  ARCHITECTURAL_BASELINE_V1 + 3 собственных verification-документа). CODE = READ ONLY, изменений кода нет.
