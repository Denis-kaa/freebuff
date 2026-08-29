# REPOSITORY ORGANIZATION FORENSICS V1

> **Дата:** 2026-08-21
> **Версия проекта:** v5.189.68
> **Методология:** promt105 (Repository Organization & Refactoring Forensics) + promt103 (Forensic Engineering Reporter) — FACT · ANALYSIS · DECISION · CONSEQUENCE · INFERENCE · FUTURE TRIGGER
> **Промт-источник:** pompts_11/105_19_repository_organization_refactoring_forensics.md
> **Статус:** FORENSIC ONLY — код не изменялся, рефакторинг НЕ выполнялся, решения не принимались. Это Refactoring Blueprint, а не миграция.

---

## A. Executive Summary

Репозиторий Freebuff / Workspace OS развивался органически: идея → эксперимент → прототип → архитектурная концепция → реализация → новый компонент → новая архитектура. В результате **архитектурные слои перемешаны с историческими контейнерами**, а нумерованные каталоги (`scripts_01`, `core_02`, `runtime_05`, `docs_10`, `pompts_11`, `data_13`, `projects_17`, `tests_09`) — это **историческая нумерация поколений**, а не архитектурная иерархия.

**Ключевые выводы:**

1. **Нумерация `NN` — исторический артефакт, не архитектура.** Каталоги `01`–`31` отражают порядок появления, а не слой системы. Число в имени не несёт семантики (например, `src_06` почти пуст, а `scripts_01` — главный runtime-слой).
2. **Архитектурная реальность ≠ файловая структура.** Логические домены (Intelligence, Agents, Factories, Forge, Scenario) **размазаны** по `scripts_01/`, `core_02/`, `freebuff_plugin_03/`, `runtime_05/` без единого canonical home.
3. **Platform vs Project граница существует концептуально, но не физически.** `projects_17/` — единственный чистый контейнер проектов. Всё остальное — платформа, но без явного маркирования.
4. **Документация хорошо организована** (`docs_10/` с поддоменами canonical/core/decisions/audits/vision/engineering-memory), но **не связана с кодом** машиночитаемо (нет тегов/ID).
5. **evaluation-пакеты (Phase 4–9 + forensics) накопились в корне** — 10+ каталогов `*_NN` и 20+ `.tar.gz` архивов. Это рабочий артефакт процесса, но засоряет корень.
6. **Основной риск:** новый разработчик **НЕ сможет** за 5–10 минут понять, где платформа, где проекты, где Intelligence, где Agents, где Factories, где Forge. Причина — нумерация вместо семантики + размазанность доменов.

**Рекомендация:** НЕ выполнять массовый рефакторинг сейчас. Принять **аддитивную стратегию**: ввести семантические canonical-алиасы через документацию и metadata-теги, заморозить границы, мигрировать только низкорисковые артефакты (evaluation-пакеты → `archive/`). Полный план — секции Q–Y.

---

## B. Current Repository Map

### B.1 Структурная карта (факт, 2026-08-21, v5.189.68)

```
freebuff/                                  # корень = вся платформа Workspace OS
│
├── [КАНАНОНИЧЕСКИЙ СЛОЙ***REMOVED***
├── core_02/                  (33 .py)     # Workspace/Project, Scenario, Forge, Factory, Router, Memory, Boundaries
│
├── [RUNTIME СЛОЙ***REMOVED***
├── scripts_01/               (76+ .py)    # Orchestrator, ModelGateway, EventBus, Memory/Knowledge, MCP, TG, Factory-cons
│   ├── data/                              # runtime SQLite: metrics/roles/presence/collaboration/project_pulse
│   └── archive/                           # import_qwen, import_sessions, phone_mcp_server, dashboard_api
│
├── [ПЛАГИН-СЛОЙ***REMOVED***
├── freebuff_plugin/          (monitor.sh) # legacy plugin
├── freebuff_plugin_03/                    # api, tgbot, scenario_engine, mcp_server/client, acp_protocol, bridge,
│   │                                      #   bootstrap/, policy/, runtime/, event/, mesh/, scenarios/
├── plugins_04/                            # 4 manifest-плагина: hello_world, tg_messenger, system_monitor, knowledge_sync
│
├── [RUNTIME ASSETS***REMOVED***
├── runtime_05/                            # factories/ (architecture, content, research, test),
│   │                                      #   scenarios/ (blueprint_v3, 19_remote_sync, vkusvill_demo),
│   │                                      #   providers/, plugins/, recipes/, policies.json
│
├── [SERVICES / SRC / CLI — почти пустые контейнеры***REMOVED***
├── services_08/  (system/monitor.py)
├── src_06/       (workers/lightpanda_worker.py)
├── cli_07/       (__init__.py)
│
├── [ПРОЕКТЫ***REMOVED***
├── projects_17/               (18+ проектов)  # tg_terminal_messenger, diet_platform, realtor_os, interior_planner,
│   │                                          #   vkusvill_demo, lead_aggregator, model_dispatcher, kwork_site, ...
│   ├── workspace.yaml
│
├── [ТЕСТЫ***REMOVED***
├── tests_09/                  (122 файла, 3345 тестов)
│
├── [ДОКУМЕНТАЦИЯ***REMOVED***
├── docs_10/                               # canonical/, core/, decisions/, history/, audits/, vision/,
│   │                                      #   engineering-memory/, plugin/, projects_meta/, ops/, runbook/, visual/
│
├── [ПРОМТЫ***REMOVED***
├── pompts_11/                 (107 файлов) # NNN_TT_name.md + user/, done/, failed/, running/
│
├── [ДАННЫЕ***REMOVED***
├── data_13/                               # SQLite: collaboration/context/metrics/presence/project_pulse/roles/verifier.db
│   │                                      # YAML: forge_registry, lisa_calibration, missing_registry, opportunities,
│   │                                      #   scenario_decisions, whims + hypothesis_ledger/
├── context_12/                            # events.db, knowledge/, memory/, streams/, summaries/, unified_context.md
│
├── [ОПЕРАЦИОННЫЕ***REMOVED***
├── logs_14/                               # tg_spawn_task_*.log
├── sessions_15/                           # README.md
├── screenshots_16/                        # (пусто)
│
├── [FRONTEND / UI***REMOVED***
├── frontend_18/              (BuffyDashboard.tsx)
├── buffy-playground_19/      (Vite/TS playground)
├── prototype_22/             (HTML/CSS/JS)
├── tank.html                 (standalone)
│
├── [ЭКСПЕРИМЕНТЫ / RESEARCH***REMOVED***
├── infa_20/                  (RUNTIME_INTELLIGENCE.md)
├── books_out_23/             (учебные материалы, 12-недельный трекер, HTML-манифесты)
│
├── [TRASH / ARCHIVE***REMOVED***
├── trash_21/                 (архивные скрипты, бэкапы, дампы)
│
├── [EVALUATION-ПАКЕТЫ — 10+ каталогов + 20+ архивов***REMOVED***
├── phase4_evaluation_24/ ... phase9_implementation_continuation_31/
├── intelligence_forensics_25/
├── architecture_forensics_v2/             # promt104 пакет
├── repository_organization_forensics_32/  # этот пакет (promt105)
├── *.tar.gz / *.sha256                    # 20+ архивов в корне
│
├── [ФАЙЛЫ КОРНЯ***REMOVED***
├── AGENTS.md, BUFFY.md, BUFFY_PROJECT.md, CHANGELOG.md, CLAUDE.md, CODY.md,
├── PLATFORM.md, README.md, SPEC.md, TASK.md, steps.md, __init__.py,
├── freebuff_cli.py, requirements.txt, mypy.ini, pytest.ini,
├── run_checks.py, run_tests_fast.sh, setup_canonical.sh, status_report.sh,
├── generate_project_dump.sh, verify_archive.sh, nohup.out
```

### B.2 Количественные факты

| Каталог | Файлов | Тип | Роль |
|---------|-------:|-----|------|
| scripts_01/ | 76 .py | runtime | Главный runtime-слой (оркестрация, модели, память, интеграции) |
| core_02/ | 33 .py | canonical | Канонические абстракции (Workspace/Project/Scenario/Forge/Factory/Router) |
| freebuff_plugin_03/ | ~40 .py | plugin | Плагин-слой (MCP, ACP, bridge, bootstrap, policy, runtime, mesh) |
| plugins_04/ | 8 .py + 4 manifest | plugin | Манифест-плагины Phase 4 |
| runtime_05/ | ~25 файлов | assets | Runtime-ассеты (factory.yaml, scenario.yaml, providers, policies) |
| projects_17/ | 18+ проектов | project | Пользовательские проекты (L-2 контейнеры) |
| tests_09/ | 122 файла | tests | 3345 тестов |
| docs_10/ | ~200 файлов | docs | Документация (15 поддоменов) |
| pompts_11/ | 107 файлов | prompts | Промт-контракты NNN_TT_name.md |
| data_13/ | 7 .db + 8 .yaml/.json | data | Персистентность |
| context_12/ | ~10 файлов | data | Runtime-контекст сессий |
| services_08/ | 2 .py | service | Почти пустой контейнер |
| src_06/ | 2 .py | src | Почти пустой контейнер |
| cli_07/ | 1 .py | cli | Пустой контейнер |
| frontend_18/ | 1 .tsx | frontend | Dashboard |
| buffy-playground_19/ | ~15 | playground | Экспериментальный Vite-проект |
| prototype_22/ | 3 | prototype | HTML-прототип |
| infa_20/ | 1 .md | research | Документ |
| books_out_23/ | ~10 | research | Учебные материалы |
| trash_21/ | ~15 | trash | Архив/мусор |
| phase4–phase9 + forensics | 10 каталогов | evaluation | Evaluation-пакеты |
| *.tar.gz | 20+ | archive | Архивы |

---

## C. Domain Map

Логические домены платформы и их **фактическое физическое расположение** (FACT — по коду):

| Домен | Canonical home (сейчас) | Размазан по | Статус |
|-------|------------------------|-------------|--------|
| **Workspace / Project** | core_02/workspace.py, workspace_registry.py | projects_17/ (контейнеры) | ✅ Единый |
| **Scenario** | core_02/scenario.py, scenario_registry.py | runtime_05/scenarios/, freebuff_plugin_03/scenarios/ | ⚠️ 2 места |
| **Factory** | core_02/factory_base.py, factory_registry.py, factory_passport.py | scripts_01/{content,research,test***REMOVED***_factory.py, runtime_05/factories/ | ⚠️ код+ассеты разделены |
| **Forge** | core_02/forge_pipeline.py, forge_facade.py, forge_registry.py, forge_passport.py | scripts_01/forge.py (CLI), forge_api.py (REST) | ⚠️ ядро+интерфейсы разделены |
| **Intelligence** | — (emergent) | scripts_01/{orchestrator,scenario_intelligence,context_manager,memory_engine,knowledge_engine,model_gateway***REMOVED***.py, core_02/{router,semantic_layer***REMOVED***.py | ❌ нет единого home |
| **Agents** | — (нет Agent ABC) | scripts_01/{roles,presence,collaboration,distributed_agents***REMOVED***.py, core_02/role_executor.py, core_02/blueprint_v3.py (14 ролей) | ❌ размазан |
| **Memory / Knowledge** | scripts_01/{memory_engine,knowledge_engine,rag_engine,graph_index***REMOVED***.py, core_02/{memory_store,semantic_layer***REMOVED***.py | context_12/, data_13/ | ⚠️ 2 слоя |
| **Event** | scripts_01/event_bus.py, event_subscribers.py | freebuff_plugin_03/event/ | ⚠️ 2 места |
| **Runtime** | freebuff_plugin_03/runtime/ | runtime_05/, src_06/, services_08/ | ⚠️ размазан |
| **Plugins** | scripts_01/plugin_api.py | plugins_04/, freebuff_plugin/, freebuff_plugin_03/ | ⚠️ 3 места |
| **Tool** | scripts_01/tool_runtime.py | — | ✅ Единый |
| **Skill** | — (отсутствует) | — | ❌ нет |
| **Artifact** | — (dict в factory_base) | data_13/, context_12/ | ❌ нет реестра |
| **Prompt** | pompts_11/ | projects_17/*/promts/, projects_17/*/pomt*.md | ⚠️ 2 места |
| **CLI** | scripts_01/forge.py + freebuff_cli.py | cli_07/ (пустой) | ⚠️ дубли |

**INFERENCE:** 14 доменов, из них только 3 имеют единый canonical home (Workspace/Project, Tool, Prompt-частично). Остальные размазаны по 2–3 местам. Это главный источник путаницы.

---

## D. Component Ownership Map

Для каждого значимого компонента: WHAT → RESPONSIBILITY → OWNER → DEPENDENCIES → LIFECYCLE → RUNTIME ROLE.

| Компонент | WHAT | RESPONSIBILITY | OWNER/DOMAIN | DEPENDENCIES | LIFECYCLE | RUNTIME ROLE |
|-----------|------|----------------|--------------|--------------|-----------|--------------|
| `Workspace` | L-1 контейнер | Группировка проектов | core_02/workspace.py | YAML | Long-lived | Конфигурация |
| `Project` | L-2 контейнер | Контейнер контекста проекта | core_02/workspace.py | YAML, projects_17/ | Long-lived | Конфигурация |
| `WorkspaceRegistry` | SQLite реестр | Workspace↔Project + privacy | core_02/workspace_registry.py | SQLite | Long-lived | Runtime state |
| `Scenario` (ABC) | Абстракция сценария | Каталог ролей | core_02/scenario.py | runtime_05/scenarios/ | Long-lived | Конфигурация |
| `ScenarioRegistry` | Реестр сценариев | Auto-discovery YAML | core_02/scenario_registry.py | runtime_05/ | Long-lived | Runtime |
| `BaseFactory` | Template | Выполнение capability | core_02/factory_base.py | FactoryRegistry, ForgeFacade | Long-lived | Runtime |
| `FactoryRegistry` | Реестр фабрик | Auto-discovery YAML | core_02/factory_registry.py | runtime_05/factories/ | Long-lived | Runtime |
| `ForgePipeline` | 6-stage pipeline | Build/Test/Deploy | core_02/forge_pipeline.py | Project, EnvDoctor | Ephemeral (per run) | Runtime |
| `ForgeFacade` | Единственный мост | Gate к ForgePipeline | core_02/forge_facade.py | ForgePipeline | Long-lived | Runtime |
| `ForgeRegistry` | YAML реестр | Статусы проектов | core_02/forge_registry.py | YAML | Long-lived | Runtime state |
| `Orchestrator` | FSM/DAG | Планирование+execution | scripts_01/orchestrator.py | ModelGateway, EventBus | Ephemeral (per goal) | Runtime |
| `ScenarioIntelligence` | Decision layer | discovery→selection | scripts_01/scenario_intelligence.py | ScenarioRegistry, FactoryRegistry | Ephemeral | Runtime |
| `ModelGateway` | LLM gateway | 6 провайдеров + fallback | scripts_01/model_gateway.py | core_02/router.py | Long-lived | Runtime |
| `EventBus` | pub/sub | События | scripts_01/event_bus.py | — | Long-lived | Runtime |
| `MemoryEngine` | Multi-level memory | WORKING/EPISODIC/SEMANTIC | scripts_01/memory_engine.py | SQLite | Long-lived | Runtime state |
| `KnowledgeEngine` | FTS+TF-IDF+graph | Поиск знаний | scripts_01/knowledge_engine.py | SQLite | Long-lived | Runtime state |
| `ToolRegistry` | 5 built-in tools | Инструменты | scripts_01/tool_runtime.py | — | Long-lived | Runtime |
| `PluginRegistry` | Реестр плагинов | Плагины | scripts_01/plugin_api.py | plugins_04/ | Long-lived | Runtime |
| `McpSessionManager` | JSON-RPC server | MCP | scripts_01/mcp_server.py | ToolRegistry, RuntimeRegistry | Long-lived | Интерфейс |
| `PresenceEngine` | Presence tracking | Статусы агентов | scripts_01/presence.py | SQLite | Long-lived | Runtime state |
| `CollaborationEngine` | Live collab | Сессии | scripts_01/collaboration.py | SQLite | Ephemeral | Runtime state |
| `RoleEngine` | Role assignment | Роли+capabilities | scripts_01/roles.py | SQLite | Long-lived | Runtime state |
| `WhimStore` | Whim lifecycle | NEW→PROMOTED | scripts_01/whim_capture.py | YAML | Long-lived | Runtime state |
| `MissingRegistry` | Register-first | Недостающие элементы | core_02/missing_registry.py | YAML | Long-lived | Runtime state |

---

## E. Code / Documentation Analysis

### E.1 Где документация лежит рядом с кодом?

| Место | Документация рядом с кодом | Оправдано? |
|-------|---------------------------|------------|
| projects_17/*/ | README, MANIFEST, SPEC, RUNNABLE, CHECKLIST, STEPS рядом с src/ | ✅ Да — проект = контейнер контекста (canonical правило) |
| freebuff_plugin_03/ | README.md, INTEGRATION_CONTRACT.md рядом с кодом | ✅ Да — контракт плагина |
| scripts_01/ | Нет .md рядом (кроме archive/) | ✅ Нет — код без локальной документации |
| core_02/ | LESSONS.md | ⚠️ Частично |
| runtime_05/ | README.md, MARKETPLACE.md | ✅ Да — ассеты с описанием |

### E.2 Принцип: Вариант A (module/), B (src/tests/docs) или C (гибрид)?

**FACT:** Репозиторий использует **гибридную модель (Вариант C)**:
- **Платформа:** `src/`-подобная (core_02 + scripts_01), тесты отдельно (tests_09/), документация отдельно (docs_10/)
- **Проекты:** module-подобная (проект = контейнер: код + тесты + docs + state внутри projects_17/<name>/)

**INFERENCE:** Это **правильная** модель для данного типа системы. Платформа — долгоживущая библиотека (нужна централизация), проекты — изолированные контейнеры (нужна автономность). Менять не нужно.

**ANALYSIS:** Единственное несоответствие — `scripts_01/` называется «scripts» (историческое имя), но является главным runtime-слоем платформы. Имя вводит в заблуждение: новый разработчик думает, что это утилиты, а не ядро.

---

## F. Platform vs Project Boundary

### F.1 Фактическая граница

```
PLATFORM (весь репозиторий, кроме projects_17/)
│
├── core_02/          → канонические абстракции
├── scripts_01/       → runtime-слой
├── freebuff_plugin*/ → плагины
├── runtime_05/       → runtime-ассеты
├── tests_09/         → тесты платформы
├── docs_10/          → документация платформы
├── pompts_11/        → промт-контракты
├── data_13/          → данные платформы
└── ...
│
PROJECT (projects_17/<name>/)
├── src/ или код
├── tests/
├── README, MANIFEST, SPEC, RUNNABLE, CHECKLIST, STEPS
├── decisions/, LESSONS.md
├── project.yaml
└── данные проекта (db, artifacts)
```

### F.2 Проверка границы (FACT)

| Аспект | Platform→Project | Project→Platform | Статус |
|--------|------------------|------------------|--------|
| Изоляция файловая | ✅ projects_17/ — единственный контейнер | ✅ проекты не пишут в core_02/ | ✅ |
| Knowledge boundary | ❌ KnowledgeEngine глобальный | ❌ | ⚠️ нет per-project изоляции |
| Memory boundary | ❌ MemoryEngine глобальный | ❌ | ⚠️ нет |
| Security boundary | ⚠️ WorkspaceRegistry privacy (workspace-level) | ⚠️ | ⚠️ нет project-level |
| Импорты | ⚠️ проекты импортируют scripts_01/ (напр. diet_platform → vault_integration?) | ⚠️ | ⚠️ есть project→platform импорты |

**INFERENCE:** Файловая граница **есть и чистая** (проекты физически в projects_17/). Но **логическая изоляция отсутствует**: Knowledge/Memory глобальные, нет per-project permissions, проекты могут импортировать runtime-слой платформы. Это соответствует выводу promt104 §G.3 (проект = контейнер контекста, не изоляционная граница).

**DECISION (не принято, рекомендация):** Для v0.1 оставить файловую границу как есть. Project-level изоляцию (knowledge/memory/permissions) добавлять аддитивно, если появится реальный multi-tenant сценарий.

---

## G. Core / Service / Runtime Analysis

### G.1 Почему существуют `core_02`, `scripts_01`, `runtime_05`?

**FACT (история):** Нумерация отражает **поколения**, не слои:
- `scripts_01` — первое поколение (все скрипты)
- `core_02` — второе поколение (выделение ядра из scripts)
- `runtime_05` — пятое поколение (runtime-ассеты)
- `src_06`, `services_08`, `cli_07` — попытки реорганизации, оставшиеся почти пустыми

### G.2 Архитектурные слои vs исторические контейнеры

| Каталог | Архитектурный слой? | Или исторический контейнер? | Вердикт |
|---------|--------------------|-----------------------------|---------|
| core_02/ | ✅ КАНОНИЧЕСКИЙ слой | — | **Архитектурный** (Workspace/Project/Scenario/Forge/Factory/Router) |
| scripts_01/ | ✅ RUNTIME слой | частично (archive/, data/) | **Архитектурный**, но имя «scripts» вводит в заблуждение |
| runtime_05/ | ✅ RUNTIME ASSETS | — | **Архитектурный** (factory.yaml, scenario.yaml) |
| freebuff_plugin_03/ | ✅ PLUGIN слой | — | **Архитектурный** |
| plugins_04/ | ✅ PLUGIN manifest | — | **Архитектурный** (манифесты Phase 4) |
| tests_09/ | ✅ TEST слой | — | **Архитектурный** |
| docs_10/ | ✅ DOC слой | — | **Архитектурный** |
| pompts_11/ | ✅ PROMPT слой | — | **Архитектурный** |
| data_13/ | ✅ DATA слой | — | **Архитектурный** |
| projects_17/ | ✅ PROJECT слой | — | **Архитектурный** |
| src_06/ | ❌ — | ✅ Исторический (почти пуст) | **Исторический** — 2 файла |
| services_08/ | ❌ — | ✅ Исторический (почти пуст) | **Исторический** — 2 файла |
| cli_07/ | ❌ — | ✅ Исторический (пуст) | **Исторический** — 1 файл |
| frontend_18/ | ⚠️ частично | ✅ Исторический (1 файл) | **Исторический** |
| infa_20/ | ❌ — | ✅ Исторический (1 документ) | **Исторический** |
| trash_21/ | ❌ — | ✅ Архив | **Исторический** |
| books_out_23/ | ❌ — | ✅ Учебный | **Исторический** |
| screenshots_16/ | ❌ — | ✅ Пустой | **Исторический** |

**INFERENCE:** 10 каталогов — архитектурные слои, 8 — исторические контейнеры. Главная проблема: **исторические контейнеры (`src_06`, `services_08`, `cli_07`, `frontend_18`, `infa_20`) выглядят как архитектурные** из-за нумерации, но почти пусты. Новый разработчик потратит время, заглядывая в них.

---

## H. Intelligence Domain

### H.1 CURRENT INTELLIGENCE COMPONENTS (файл → функция → ответственность)

| Файл | Функция/Класс | Ответственность |
|------|---------------|-----------------|
| scripts_01/orchestrator.py | `Orchestrator`, `DefaultPlanner` | Планирование (Goal→Plan→Execute→Validate), DAG execution |
| scripts_01/scenario_intelligence.py | `ScenarioIntelligence` | Decision: discovery→evaluation→ranking→selection |
| scripts_01/context_manager.py | `ContextManager` | Session context, checkpoints, auto-summarization |
| scripts_01/memory_engine.py | `MemoryEngine` | Multi-level memory (WORKING/EPISODIC/SEMANTIC) |
| scripts_01/knowledge_engine.py | `KnowledgeEngine` | FTS + TF-IDF + graph search |
| scripts_01/model_gateway.py | `ModelGateway` | 6 LLM providers, capability routing, fallback |
| core_02/router.py | `SmartRouter` | Capability→model routing |
| core_02/semantic_layer.py | `SemanticLayer` | Semantic search |
| scripts_01/rag_engine.py | `RAGEngine` | Retrieval-augmented generation |
| scripts_01/graph_index.py | `GraphIndex` | Knowledge graph |
| scripts_01/whim_capture.py | `WhimStore` | Идеи/whim lifecycle |
| scripts_01/opportunity_engine.py | `Opportunity` | Opportunity lifecycle |
| scripts_01/hypothesis_ledger.py | `HypothesisLedger` | Гипотезы |
| scripts_01/devil_advocate_pass.py | `devil_advocate_pass` | Критика гипотез (ADR-016) |
| scripts_01/weighted_scoring_engine.py | `WeightedScoringEngine` | Взвешенная оценка |
| core_02/capability_gap_auditor.py | — | Аудит capability gap |

### H.2 Может ли это стать единым architectural domain?

**FACT:** Intelligence — **emergent property** (подтверждено promt104 §E, Phase 6/8/9). Нет единого класса `Intelligence`.

**ANALYSIS:** 16 компонентов формируют «Intelligence», разбросаны по scripts_01/ (13) и core_02/ (3). **Единый физический каталог `intelligence/` НЕ рекомендуется** — это нарушило бы Additive Architecture и потребовало бы массового рефакторинга. Вместо этого: **единый логический домен через metadata-тег `@domain: intelligence`** (секция U).

**INFERENCE:** Intelligence остаётся emergent-свойством, но получает **явную карту** (таблица H.1) и **тег** для трассировки. Это решает проблему навигации без рефакторинга.

---

## I. Agent Ecosystem

### I.1 Карта агентной экосистемы (факт)

| Аспект | Где | Файл | Статус |
|--------|-----|------|--------|
| Pipeline-роли (14) | core_02/blueprint_v3.py | `BlueprintCorpus` | ✅ Есть |
| Role assignment | scripts_01/roles.py | `RoleEngine` | ✅ Есть |
| Role executor | core_02/role_executor.py | `RoleExecutorRegistry` | ✅ Есть (ADR-016) |
| Presence-агенты | scripts_01/presence.py | `PresenceEngine` | ✅ Есть |
| Collaboration-участники | scripts_01/collaboration.py | `CollaborationEngine` | ✅ Есть |
| Distributed agents | scripts_01/distributed_agents.py | — | ✅ Есть |
| Agent ABC | — | — | ❌ НЕТ |
| Agent lifecycle | — | — | ❌ НЕТ |
| A2A communication | — | — | ❌ НЕТ (только череда артефактов) |
| Agent prompt | pompts_11/ (роли) + runtime_05/scenarios/ | — | ⚠️ Размазан |
| Agent runtime | freebuff_plugin_03/runtime/ | `RuntimeRegistry` | ⚠️ Отдельный слой |
| Agent config | projects_17/*/ + runtime_05/ | — | ⚠️ Размазан |

### I.2 Проблема: Agent размазан по 4 местам без контракта

**FACT:** «Агент» физически представлен в **4 местах**:
1. **Роли** — core_02/blueprint_v3.py (14 pipeline-ролей) + core_02/role_executor.py
2. **Presence** — scripts_01/presence.py (регистрация агентов)
3. **Runtime** — freebuff_plugin_03/runtime/ (RuntimeRegistry, адаптеры)
4. **Промты ролей** — pompts_11/ + runtime_05/scenarios/ + projects_17/*/roles/

**INFERENCE:** Это подтверждает GAP-1 из promt104 (нет Agent ABC). Пока нет единой абстракции, агент остаётся «концепцией», а не сущностью. **Рекомендация:** не создавать новый каталог `agents/`, а зафиксировать **Agent Contract** в документации + тег `@domain: agents`, чтобы 4 места были связаны.

---

## J. Factory / Forge / Scenario Placement

### J.1 Фактическое расположение

| Понятие | Код | Ассеты | Интерфейсы | Статус |
|---------|-----|--------|-----------|--------|
| **Factory** | core_02/{factory_base,factory_registry,factory_passport***REMOVED***.py | runtime_05/factories/ (4: architecture, content, research, test) | scripts_01/{content,research,test***REMOVED***_factory.py | ⚠️ код в core, консьюмеры в scripts |
| **Forge** | core_02/{forge_pipeline,forge_facade,forge_registry,forge_passport***REMOVED***.py | data_13/forge_registry.yaml | scripts_01/{forge.py,forge_api.py***REMOVED*** | ⚠️ ядро в core, CLI/REST в scripts |
| **Scenario** | core_02/{scenario,scenario_registry***REMOVED***.py | runtime_05/scenarios/ (blueprint_v3, 19_remote_sync, vkusvill_demo) | freebuff_plugin_03/scenarios/ | ⚠️ 2 места ассетов |

### J.2 Противоречит ли физическая структура логической архитектуре?

**ANALYSIS:** Логическая архитектура: `Scenario → Factory → Forge` (через ForgeFacade, §7.3). Физически:
- Scenario: core_02 (код) + runtime_05 (ассеты) + freebuff_plugin_03 (плагин-сценарии)
- Factory: core_02 (база) + scripts_01 (конкретные) + runtime_05 (манифесты)
- Forge: core_02 (всё ядро) + scripts_01 (CLI/REST)

**INFERENCE:** Физическая структура **НЕ противоречит** логической (все три домена имеют ядро в core_02, что правильно). Проблема — **интерфейсы и ассеты дублируются в scripts_01 + freebuff_plugin_03**. Но это исторически оправдано: scripts_01 — runtime-слой, freebuff_plugin_03 — плагин-слой.

**DECISION (рекомендация):** НЕ переезжать. Зафиксировать правило: **ядро домена → core_02, runtime-консьюмеры → scripts_01, плагин-расширения → freebuff_plugin_03**. Документировать в ARCHITECTURE.md.

---

## K. Prompt Organization

### K.1 Аудит промптов (факт)

**pompts_11/** — 107 файлов, конвенция `NNN_TT_name.md`:
- `NNN` — номер (001–106)
- `TT` — код темы (01–21): 01=агентность, 02=архитектура, 03=аудит, 04=интеграции, 05=память, 06=docs, 07=документирование, 08=UI, 09=консолидация, 10=DPE, 11=user-choice, 12=мобильный, 13=качество, 14=планировщик, 15=RFC, 16=org-intelligence, 17=ARB, 18=AG, 19=forge/factory/forensics, 20=руководство, 21=приоритизация
- Подкаталоги: `user/` (задачи), `done/`, `failed/`, `running/`

### K.2 Runtime assets vs документация процесса разработки

| Тип | Где | Примеры |
|-----|-----|---------|
| **Runtime assets** (используются кодом) | runtime_05/scenarios/, runtime_05/factories/ | blueprint_v3.yaml, factory.yaml, scenario.yaml |
| **Development docs** (процесс разработки) | pompts_11/ | 001–106 промты |
| **Project prompts** | projects_17/*/promts/, projects_17/*/pomt*.md | content_factory/promts/, kwork_site/промт.md |

**INFERENCE:** Разделение **существует и корректно**: runtime-ассеты в runtime_05/ (читаются FactoryRegistry/ScenarioRegistry), промт-контракты в pompts_11/ (документация процесса), проектные промты в проектах. **Проблема:** pompts_11 содержит и runtime-задачи (`user/`) и контракты — но это рабочий артефакт очереди, не архитектурный.

**ANALYSIS:** Конвенция `NNN_TT_name.md` — **хорошая** (проверяется consistency_check, exit 0). Менять не нужно.

---

## L. Data / Storage Organization

### L.1 Что где хранится (факт)

| Тип данных | Расположение | Примеры |
|------------|--------------|---------|
| **Runtime state (SQLite)** | scripts_01/data/ | metrics.db, roles.db, presence.db, collaboration.db, project_pulse.db |
| **Runtime state (SQLite)** | data_13/ | context.db, verifier.db |
| **Persistent app data (SQLite)** | data_13/ | collaboration.db, metrics.db, presence.db, project_pulse.db, roles.db |
| **Registries (YAML)** | data_13/ | forge_registry.yaml, scenario_decisions.yaml, opportunities.yaml, whims.yaml, lisa_calibration.yaml, missing_registry.yaml |
| **Hypotheses (JSONL)** | data_13/hypothesis_ledger/ | *.jsonl |
| **Context runtime** | context_12/ | events.db, knowledge/, memory/, streams/, summaries/ |
| **Project data** | projects_17/*/ | *.db, *.json, data/ |
| **Test data/fixtures** | tests_09/ | — |
| **Generated artifacts** | projects_17/*/forge/, *.tar.gz | — |
| **Temporary** | trash_21/, /tmp | — |

### L.2 Проблема: дублирование runtime state

**FACT:** SQLite-базы **размазаны по 2 местам**: `scripts_01/data/` (5 db) и `data_13/` (7 db). При этом `collaboration.db`, `metrics.db`, `presence.db`, `project_pulse.db`, `roles.db` есть **в обоих** каталогах.

**INFERENCE:** Это **дублирование** (или устаревшие копии). Нужно определить, какие из них актуальные (проверка mtime/размера), и **зафиксировать единый canonical home для runtime state** — `data_13/`.

**ANALYSIS:** `context_12/` — отдельный контейнер для контекста сессий (events.db, knowledge, memory). Это оправдано (другой lifecycle — эфемерный контекст vs персистентные данные), но требует документации.

---

## M. Experiments / Research / Legacy

### M.1 Классификация (факт)

| Компонент | Статус | Production capability? | Рекомендация |
|-----------|--------|------------------------|--------------|
| prototype_22/ | EXPERIMENTAL | ❌ (демо UI) | KEEP (изолирован) |
| buffy-playground_19/ | EXPERIMENTAL | ❌ (Vite playground) | KEEP (изолирован) |
| frontend_18/ | DRAFT | ⚠️ (1 файл) | MOVE в prototype_22/ или ARCHIVE |
| infa_20/ | RESEARCH | ❌ (1 документ) | MOVE в docs_10/research/ или ARCHIVE |
| books_out_23/ | RESEARCH/EDU | ❌ | KEEP (изолирован) |
| trash_21/ | TRASH | ❌ | ARCHIVE (уже архив) |
| screenshots_16/ | LEGACY | ❌ (пусто) | ARCHIVE/DELETE |
| phase4–9 + forensics | EVALUATION | ❌ (артефакты процесса) | ARCHIVE в archive/ |
| *.tar.gz (20+) | ARCHIVE | ❌ | MOVE в archive/ |
| scripts_01/archive/ | LEGACY | ❌ | KEEP (уже изолирован) |
| services_08/, src_06/, cli_07/ | ORPHANED | ⚠️ (почти пусты) | DEPRECATE или MERGE |
| tank.html | PROTOTYPE | ❌ | MOVE в prototype_22/ |

### M.2 Что нельзя удалять

- **evaluation-пакеты** (Phase 4–9, forensics) — это **доказательственная база** (evidence ledger) процесса разработки. CAN-17 anti-rewriting rule запрещает переписывать/удалять audit-trail.
- **trash_21/** — исторический архив, содержит восстановимые материалы.
- **scripts_01/archive/** — legacy-скрипты, могут понадобиться.

---

## N. Duplication Analysis

### N.1 Дублирующие концепции (факт)

| Концепция | Место 1 | Место 2 | Действительный дубль? |
|-----------|---------|---------|-----------------------|
| **Memory** | scripts_01/memory_engine.py | core_02/memory_store.py | ⚠️ Разные уровни: engine (runtime) vs store (persistence) — **НЕ дубль** |
| **Knowledge** | scripts_01/knowledge_engine.py | core_02/semantic_layer.py | ⚠️ Разные: FTS+graph vs semantic — **НЕ дубль** |
| **Event** | scripts_01/event_bus.py | freebuff_plugin_03/event/ | ⚠️ Разные: core event bus vs plugin event store — **НЕ дубль** |
| **SQLite runtime state** | scripts_01/data/*.db | data_13/*.db | ✅ **ДУБЛЬ** — collaboration/metrics/presence/project_pulse/roles в обоих |
| **CLI** | scripts_01/forge.py | cli_07/ | ⚠️ cli_07 пуст — **НЕ дубль** (недостроен) |
| **Scenario assets** | runtime_05/scenarios/ | freebuff_plugin_03/scenarios/ | ⚠️ Разные: canonical vs plugin — **НЕ дубль** |
| **Factory** | scripts_01/{content,research,test***REMOVED***_factory.py | runtime_05/factories/ | ⚠️ Код vs манифесты — **НЕ дубль** (разные уровни) |
| **MCP server** | scripts_01/mcp_server.py | freebuff_plugin_03/mcp_server.py | ⚠️ Разные: core vs plugin — требует проверки |
| **TG bot** | scripts_01/telegram_bot.py | freebuff_plugin_03/tgbot.py | ⚠️ Разные: core vs plugin — требует проверки |

### N.2 Вывод

**INFERENCE:** Большинство «дублей» — **разные уровни абстракции** (core vs runtime vs plugin), что архитектурно оправдано. **Единственный реальный дубль** — SQLite-базы в `scripts_01/data/` и `data_13/`. Требуется консолидация (секция R, action MERGE).

---

## O. Dependency Analysis

### O.1 Кто от кого зависит (факт)

```
┌─────────────┐
│   USER      │  CLI / TG / MCP / REST
└──────┬──────┘
       ↓
┌─────────────┐     ┌──────────────────┐
│  scripts_01 │ ──→ │  core_02         │  (runtime → canonical: OK)
│ (runtime)   │     │  (canonical)     │
└──────┬──────┘     └──────────────────┘
       ↓
┌─────────────┐     ┌──────────────────┐
│freebuff_    │ ──→ │  runtime_05      │  (plugin → assets)
│plugin_03    │     │  (assets)        │
└──────┬──────┘     └──────────────────┘
       ↓
┌─────────────┐
│  projects_17│ ──→ scripts_01/core_02 (проекты импортируют платформу)
└─────────────┘
```

### O.2 Обнаруженные проблемы

| Проблема | Где | Серьёзность |
|----------|-----|-------------|
| **Project → Platform импорты** | projects_17/*/ импортируют scripts_01/, core_02/ | ⚠️ Нарушает изоляцию (но ожидаемо для монолита) |
| **scripts_01 → core_02** | Runtime импортирует canonical | ✅ Правильная зависимость |
| **core_02 → scripts_01?** | Нужно проверить (обратная зависимость = нарушение) | ⚠️ Требует проверки |
| **Circular deps** | Не обнаружено явно | ⚠️ Требует проверки инструментом |
| **freebuff_plugin_03 → scripts_01** | Плагин использует runtime-слой | ⚠️ Допустимо, но документировать |
| **Runtime → documentation** | Нет явных | ✅ |

**INFERENCE:** Основная архитектурная зависимость **корректна** (runtime → canonical). Главный риск — **project → platform** импорты (нарушают границу F). Для v0.1 это приемлемо (монолит), но нужно зафиксировать правило: `projects_17/` НЕ должен импортировать `core_02/` напрямую без контракта.

---

## P. Architectural Smells

| # | Smell | Где | Severity |
|---|-------|-----|----------|
| P-1 | **Нумерация вместо семантики** — `NN` в имени не отражает слой | Все каталоги 01–31 | **HIGH** |
| P-2 | **Исторические пустые контейнеры выглядят как слои** | src_06/, services_08/, cli_07/ | HIGH |
| P-3 | **`scripts_01` называется «scripts», но это ядро runtime** | scripts_01/ | MEDIUM |
| P-4 | **Runtime state дублируется** | scripts_01/data/ vs data_13/ | MEDIUM |
| P-5 | **evaluation-пакеты + архивы в корне** | 10 каталогов + 20 tar.gz | MEDIUM |
| P-6 | **Intelligence/Agents без единого home** | Размазаны по 4+ местам | MEDIUM |
| P-7 | **Нет машиночитаемой связи код↔docs** | Нет тегов/ID | MEDIUM |
| P-8 | **Проектные промты вне pompts_11** | projects_17/*/promts/ | LOW |
| P-9 | **CLI в двух местах** | scripts_01/forge.py + freebuff_cli.py | LOW |
| P-10 | **`tank.html`, `nohup.out`, `qwen-table-*.csv` в корне** | корень | LOW |

---

## Q. Proposed Canonical Repository Structure

**Принцип:** НЕ массовый рефакторинг. **Аддитивная канонизация** — зафиксировать роли существующих каталогов, ввести семантические алиасы через документацию, изолировать артефакты.

### Q.1 TARGET (рекомендуемая структура)

```
freebuff/                                  # = Workspace OS (платформа)
│
├── platform/                              # [АЛИАС через README, НЕ новая папка***REMOVED***
│   ├── core/        → core_02/            # канонические абстракции
│   ├── runtime/     → scripts_01/         # runtime-слой
│   ├── plugins/     → freebuff_plugin_03/ + plugins_04/
│   ├── assets/      → runtime_05/         # runtime-ассеты
│   ├── data/        → data_13/            # персистентность
│   ├── tests/       → tests_09/
│   ├── docs/        → docs_10/
│   └── prompts/     → pompts_11/
│
├── projects/        → projects_17/        # пользовательские проекты
│
├── archive/                               # [НОВЫЙ***REMOVED*** изолированный архив
│   ├── evaluations/  ← phase4–9, forensics, repository_organization_forensics_32
│   ├── legacy/       ← src_06/, services_08/, cli_07/, frontend_18/, infa_20/
│   ├── trash/        ← trash_21/
│   └── tarballs/     ← *.tar.gz, *.sha256
│
├── experiments/                           # [АЛИАС через README***REMOVED***
│   ├── prototype_22/, buffy-playground_19/, books_out_23/
│
├── [корневые файлы***REMOVED***  AGENTS.md, BUFFY.md, CHANGELOG.md, TASK.md, ...
```

### Q.2 Принципы

1. **НЕ переименовывать существующие каталоги** (Additive Architecture, CAN-16, Backward Compatibility). `core_02/` остаётся `core_02/`.
2. **Ввести семантические алиасы** в документации: `platform/core → core_02`, `platform/runtime → scripts_01` и т.д. — чтобы новый разработчик видел слой, а не номер.
3. **Создать `archive/`** для изоляции evaluation-пакетов, legacy, trash, tarballs. ⚠️ **Конвенция:** при фактическом создании top-level каталог должен соответствовать `имя_NN` (напр. `archive_33`) ИЛИ получить документированное исключение в `consistency_check._EVALUATION_PACKAGE_DIRS` (как `architecture_forensics_v2`). Иначе naming_convention даст exit 1.
4. **Зафиксировать canonical home** для каждого домена (секция C) в ARCHITECTURE.md.
5. **Маркировать домены тегами** (секция U) для машиночитаемой навигации.

---

## R. File Migration Matrix

**Current Path → Component → Responsibility → Target Path → Action → Risk → Dependencies**

| Current Path | Component | Target Path | Action | Risk | Dependencies |
|--------------|-----------|-------------|--------|------|--------------|
| phase4_evaluation_24/ … phase9_implementation_continuation_31/ | Evaluation-пакеты | archive/evaluations/ | MOVE | LOW | нет |
| intelligence_forensics_25/ | Evaluation-пакет | archive/evaluations/ | MOVE | LOW | нет |
| architecture_forensics_v2/ | Evaluation-пакет | archive/evaluations/ | MOVE | LOW | нет (но см. примечание) |
| repository_organization_forensics_32/ | этот пакет | archive/evaluations/ | MOVE (после ревью) | LOW | нет |
| *.tar.gz, *.sha256 | Архивы | archive/tarballs/ | MOVE | LOW | нет |
| trash_21/ | Архив | archive/trash/ | RENAME→MOVE | LOW | нет |
| src_06/ | Legacy (2 файла) | archive/legacy/src_06/ | MOVE | LOW | lightpanda_worker может импортироваться |
| services_08/ | Legacy (2 файла) | archive/legacy/services_08/ | MOVE | LOW | monitor.py может импортироваться |
| cli_07/ | Legacy (1 файл) | archive/legacy/cli_07/ | MOVE | LOW | нет |
| frontend_18/BuffyDashboard.tsx | Draft | prototype_22/ ИЛИ archive/legacy/ | MOVE | LOW | нет |
| infa_20/RUNTIME_INTELLIGENCE.md | Research doc | docs_10/research/ | MOVE | LOW | нет |
| scripts_01/data/*.db | Runtime state (дубль) | data_13/ (консолидация) | MERGE | MEDIUM | нужно определить актуальные |
| tank.html | Prototype | prototype_22/ | MOVE | LOW | нет |
| contexts_12/ | Runtime context | KEEP (документировать) | KEEP | — | — |
| projects_17/*/promts/, pomt*.md | Project prompts | KEEP в проекте | KEEP | — | — |
| core_02/, scripts_01/, runtime_05/, docs_10/, pompts_11/, data_13/, tests_09/, projects_17/ | Архитектурные слои | KEEP (канонизировать) | KEEP | — | — |
| freebuff_plugin_03/, plugins_04/ | Плагины | KEEP | KEEP | — | — |
| books_out_23/ | Учебные материалы | KEEP (изолирован) | KEEP | — | — |
| screenshots_16/ | Пустой | archive/ | MOVE | LOW | нет |

**Примечание по `architecture_forensics_v2/`:** имя каталога жёстко задано promt104 §28 (REQUIRED OUTPUT) и имеет исключение в consistency_check (`_EVALUATION_PACKAGE_DIRS`). При переносе в `archive/evaluations/` исключение нужно расширить на новый путь ИЛИ убрать (каталог перестанет быть top-level → проверка naming_convention его не затронет).

---

## S. Documentation Organization

### S.1 Фактическая классификация (docs_10/)

| Тип | Каталог | Примеры |
|-----|---------|---------|
| **CANONICAL ARCHITECTURE** | docs_10/canonical/ | architecture.md, INDEX.md |
| **CORE (spec/standard)** | docs_10/core/ | CORE_PROMPT.md, CODE_QUALITY_STANDARD.md, FINAL_STRUCTURE.md, GLOSSARY.md, RULES.md, ARCHITECTURAL_DEBT.md |
| **ARCHITECTURAL DECISION** | docs_10/decisions/ + docs_10/engineering-memory/decisions/ | ADR_001…ADR_016 |
| **RESEARCH** | docs_10/engineering-memory/ | WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md, RFC_*, FACTORY_FORGE_ARCHITECTURE_V1.md |
| **AUDIT** | docs_10/audits/ | AUDIT_*.md, DRIFT_REPORT.md, RECOVERY_REPORT_*.md |
| **VISION/ROADMAP** | docs_10/vision/ | VISION_3.0.md, ROADMAP_*.md |
| **OPERATIONAL** | docs_10/ops/, docs_10/runbook/ | SESSION_GUIDE.md, FORGE_CHAIN_RUNBOOK.md, MISSING_REGISTRY_RUNBOOK.md |
| **PLUGIN** | docs_10/plugin/ | FREEBUFF_PLUGIN_*.md |
| **HISTORICAL** | docs_10/history/, docs_10/session_dumps/, docs_10/task_archive/ | DAY_SUMMARY_*.md, SESSION_*.md |
| **PROJECTS META** | docs_10/projects_meta/ | PROJECTS_OVERVIEW.md, FILE_REGISTRY.md |

### S.2 Оценка

**FACT:** Документация **хорошо организована** — 15 поддоменов с чёткой классификацией. Это лучшая часть репозитория.

**ANALYSIS:** Проблемы:
1. **Дублирование ADR**: `docs_10/decisions/` И `docs_10/engineering-memory/decisions/` содержат ADR (ADR_001 есть в обоих). Требуется консолидация (canonical home).
2. **Нет машиночитаемой связи** с кодом (секция T/U).
3. **`docs_10/engineering-memory/` перегружен**: содержит и RFC, и research, и AUDIT_WS_OS_*, и FACTORY_FORGE_* — смешение RESEARCH и ENGINEERING-MEMORY.

---

## T. Code ↔ Documentation Traceability

### T.1 Текущее состояние

| Связь | Есть? | Механизм |
|-------|-------|----------|
| Doc ↔ Code | ⚠️ Частично | Имена файлов совпадают (напр. CORE_PROMPT.md ↔ docs_10/core/) |
| Code ↔ Test | ✅ Есть | tests_09/test_<module>.py конвенция |
| Doc ↔ Test | ❌ Нет | — |
| Concept ↔ Contract ↔ Code ↔ Test | ❌ Нет | — |

### T.2 Существующие механизмы (факт)

- **CONTRACT_REGISTRY_V1.md** (docs_10/engineering-memory/) — попытка реестра контрактов
- **TRACEABILITY_GRAPH_V1.md** — попытка графа трассируемости
- **DOCUMENTATION_CODE_MAP_V1.md** — карта doc↔code
- **SEMANTIC_ANCHOR_SPEC_V1.md** — спецификация семантических якорей
- **SemanticLayer** (core_02/semantic_layer.py) — семантический поиск
- **GraphIndex** (scripts_01/graph_index.py) — граф знаний

**INFERENCE:** Платформа **уже имеет инструменты** для трассируемости (Traceability Graph, Semantic Anchor Spec, SemanticLayer, GraphIndex), но они **не применяются систематически** к существующим документам.

---

## U. Metadata / Tagging Proposal

### U.1 Концепция

Добавить структурированные **metadata-теги** к документации и коду для машиночитаемой связи:

```
@domain: <intelligence|agents|factories|forge|scenario|memory|knowledge|event|runtime|plugins|tools|workspace|project|prompts>
@component: <имя компонента>
@contract: <CONTRACT-ID>
@status: <canonical|adr|spec|research|audit|draft|legacy>
```

### U.2 Оценка (полезность/стоимость/где применять)

| Критерий | Оценка |
|----------|--------|
| **Полезность** | HIGH — решает P-6 (Intelligence/Agents без home): тег `@domain: intelligence` связывает 16 разбросанных модулей |
| **Стоимость** | LOW-MEDIUM — добавление строки в шапку каждого .md и docstring каждого .py (~300 файлов) |
| **Где применять** | Шапки канонических документов (docs_10/canonical/, docs_10/core/), docstring ключевых модулей (core_02/, scripts_01/) |
| **Где НЕ применять** | projects_17/*/ (проекты — отдельная экосистема), trash_21/, archive/, evaluation-пакеты |
| **Совместимость с Knowledge/Graph** | ✅ HIGH — SemanticLayer и GraphIndex уже умеют индексировать; теги станут узлами/рёбрами графа |
| **Provenance graph** | ✅ Можно строить: DOC → SECTION → CONCEPT → CONTRACT → CODE SYMBOL → TEST → RUNTIME BEHAVIOR |

### U.3 Рекомендация

**DO WITH LIMITS.** Внедрять теги **только** для канонических документов и ключевых модулей (не для всех 300 файлов), начиная с 5 доменов (intelligence, agents, factories, forge, scenario). Совместимо с существующим SEMANTIC_ANCHOR_SPEC_V1.md — использовать его как основу, не изобретать новый формат.

---

## V. Migration Strategy

**Принцип:** Phase 0–9 по promt105 §22. **НЕ выполнять сейчас** — это Blueprint для отдельного утверждения.

| Phase | Действие | Что | Risk | Rollback | Validation |
|-------|----------|-----|------|----------|------------|
| **0. Inventory** | ✅ (этот документ) | Полная карта | LOW | — | Документ |
| **1. Freeze boundaries** | Зафиксировать canonical home доменов (секция C) в ARCHITECTURE.md | Документация | LOW | Откат docs | Ревью |
| **2. Canonical locations** | Создать `archive/` + README-алиасы platform/ | Новые пустые каталоги | LOW | Удалить | ls |
| **3. Move documentation** | infa_20 → docs_10/research/, консолидация ADR | Docs | LOW | git mv | grep ссылок |
| **4. Move low-risk code** | src_06/, services_08/, cli_07/ → archive/legacy/ | Код | MEDIUM | git mv | Импорты |
| **5. Fix imports** | Обновить импорты lightpanda_worker, monitor | Код | MEDIUM | git revert | grep |
| **6. Tests** | Прогнать tests_09/ (3345 тестов) | Тесты | LOW | — | pytest |
| **7. Runtime validation** | Запустить consistency_check + smoke | Runtime | LOW | — | exit 0 |
| **8. Deprecate old paths** | README-заглушки в старых местах | Docs | LOW | Удалить | grep |
| **9. Cleanup** | Удалить пустые контейнеры, screenshots_16 | Очистка | LOW | — | ls |

**Минимальный объём (рекомендуемый первый шаг):** только Phase 0–2 + Phase 3 (infa_20) + Phase 4 (пустые контейнеры). Это ~30 минут работы, нулевой риск, максимальный эффект для навигации.

---

## W. Risk Register

| # | Риск | Вероятность | Impact | Митигация |
|---|------|-------------|--------|-----------|
| W-1 | **Перемещение evaluation-пакетов сломает ссылки** (MANIFEST, архивы, consistency_check `_EVALUATION_PACKAGE_DIRS`) | MEDIUM | MEDIUM | Переносить последним, обновить исключение; архивы пересоздать |
| W-2 | **`git mv` исторических контейнеров сломает импорты** (lightpanda_worker, monitor) | LOW | MEDIUM | Проверить импорты до; rollback = git mv обратно |
| W-3 | **Консолидация SQLite (scripts_01/data vs data_13) потеряет данные** | MEDIUM | HIGH | Сначала определить актуальные (mtime/size), бэкап |
| W-4 | **Внедрение тегов создаст шум** без пользы | MEDIUM | LOW | Начать с 5 доменов, не all-300 |
| W-5 | **Рефакторинг перерастёт в «большую перестройку»** (ANTI-5) | HIGH | HIGH | Жёсткий scope: Phase 0–4 только |
| W-6 | **Дублирование ADR (decisions vs engineering-memory) приведёт к расхождению** | MEDIUM | MEDIUM | Выбрать canonical home, добавить redirect |
| W-7 | **Новый разработчик всё равно запутается** без семантических алиасов | MEDIUM | MEDIUM | README-алиасы platform/ обязательны |

---

## X. Validation Strategy

| Проверка | Инструмент | Критерий |
|----------|-----------|----------|
| **Consistency check** | `python -m scripts_01.consistency_check` | exit 0 |
| **Тесты** | `python -m pytest tests_09/ -q` | 3345 passed |
| **Типизация** | `python -m mypy scripts_01/ core_02/ --ignore-missing-imports` | без ошибок |
| **Импорты после move** | `grep -rn "src_06\|services_08\|cli_07" scripts_01/ core_02/` | пусто (или обновлено) |
| **Ссылки на evaluation-пакеты** | `grep -rn "phase4_evaluation_24" *.md` | обновлено |
| **Архивы** | `tar tzf <archive>` | содержимое корректно |
| **Навигация** | «5-минутный тест» нового разработчика | см. Y |

---

## Y. Final Recommendation

### Y.1 Ответ на главный вопрос promt105 §26

> «Если завтра новый разработчик откроет repository — сможет ли он за 5–10 минут понять, где платформа, где проекты, где Intelligence, где Agents, где Factories, где Forge, где документация и где эксперименты?»

**FACT: НЕТ.** Причины:
1. **Нумерация `NN` не несёт семантики** — `core_02` и `scripts_01` выглядят одинаково «важными», хотя это canonical vs runtime.
2. **Intelligence и Agents не имеют физического home** — размазаны по 4+ каталогам.
3. **10 evaluation-каталогов + 20 tar.gz в корне** засоряют карту.
4. **Исторические пустые контейнеры** (src_06, services_08, cli_07) выглядят как слои.
5. **Нет семантических алиасов** (platform/core, platform/runtime).

### Y.2 Что сделать ПЕРВЫМ (минимальный, безопасный, аддитивный шаг)

1. **Создать `archive/`** и перенести evaluation-пакеты + tar.gz + trash_21 + screenshots_16 (Phase 4, LOW risk).
2. **Создать README-алиасы** `platform/` и `experiments/` (Phase 2) — семантическая навигация без переименования.
3. **Зафиксировать canonical home доменов** в docs_10/canonical/architecture.md (Phase 1) + карту Intelligence (таблица H.1).
4. **Перенести infa_20 → docs_10/research/** (Phase 3).
5. **Консолидировать ADR** (decisions vs engineering-memory/decisions) — выбрать canonical home.
6. **Начать тегирование** 5 доменов (Phase U, DO WITH LIMITS).

### Y.3 Чего НЕ делать

- ❌ Массовое переименование `core_02` → `platform/core` (сломает 100+ импортов, нарушит CAN-16).
- ❌ Переезд Intelligence в новый каталог (нарушит Additive Architecture).
- ❌ Удаление evaluation-пакетов (нарушит CAN-17 audit-trail).
- ❌ Рефакторинг Factory/Forge/Scenario физического расположения (логика уже правильная).

### Y.4 Итоговая оценка организации

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| Документация | 🟢 **8/10** | Хорошо организована, 15 поддоменов |
| Промты | 🟢 **8/10** | Конвенция NNN_TT_name.md, consistency_check |
| Проекты | 🟢 **7/10** | projects_17/ — чистый контейнер |
| Код-слои | 🟡 **5/10** | Нумерация вместо семантики, исторические пустые контейнеры |
| Intelligence/Agents | 🔴 **3/10** | Нет физического home, размазаны |
| Корень репозитория | 🔴 **3/10** | 10 evaluation-каталогов + 20 tar.gz |
| Машиночитаемая связь код↔docs | 🔴 **2/10** | Нет тегов, инструменты есть но не применяются |
| **Общая организация** | 🟡 **5.1/10** | Рабочая, но навигация для новичка затруднена |

**Финальный вердикт:** Репозиторий **функционален и хорошо документирован**, но его **физическая структура не отражает архитектурную реальность**. Рекомендуется **аддитивная канонизация** (archive/ + семантические алиасы + canonical home + теги) вместо рефакторинга. Первый шаг — ~30 минут, нулевой риск, максимальный эффект для навигации.

---

*Forensic analysis complete. Код не изменялся. Рефакторинг НЕ выполнялся. Архитектурные решения не принимались — это Refactoring Blueprint для отдельного утверждения.*
