# FORENSICS: Content Intelligence Target Model ↔ Platform Registries — Gap Map G0–G4 v1

| Поле | Значение |
|------|----------|
| **Документ** | FORENSICS_CI_GAP_MAP_V1.md |
| **Статус** | 📋 Forensics gap map (вход для отчёта A–K промта 1) |
| **Дата** | 2026-08-12 |
| **Источник** | `projects_17/content_factory/promts/1.md` — Platform Forensics & CI Integration Discovery v1.0 (§6 примитивы, §8 целевая модель CI, §14 integration gaps, §16 G0–G4, §20 evidence rule) |
| **ARB-прецедент** | ARB-REV-004 (APPROVED WITH RECOMMENDATIONS; RA2: маппинг G0–G4 на словарь платформы + register-first) |
| **Метод** | Repository forensics по промту 1: каждый элемент целевой модели CI сопоставлен с ФАКТИЧЕСКИМ API реестров (код > доки), статус по G0–G4, эвиденс: CLAIM / EVIDENCE (path+symbol) / CONFIDENCE |
| **Проверено** | `ForgeRegistry`, `ScenarioRegistry`, `ForgeFacade`, `MissingRegistry`, `data_13/` (YAML+SQLite), `memory_store`/`memory_engine`, `event_bus`, `project_pulse`, `prompt_dispatcher` |

---

## 0. Сводка (Executive Finding)

Целевая модель Content Intelligence (промт 1 §8) — из 10 шагов **7 полностью реализованы в платформе (G0)** (OBSERVE/COLLECT/UNDERSTAND/CONNECT/EXECUTE/VALIDATE/ACCUMULATE), **1 — G0-база + G1-адаптер (SELECT SCENARIO**: базовый выбор есть, CI-выбор по opportunity — адаптер), **2 — G3 (DISCOVER OPPORTUNITIES + PROPOSE = Opportunity Engine + Whim-захват)**, **G2 = 1 (Factory Registry: дизайн готов, кода нет)**, **G4 = 0 (архитектурных конфликтов не обнаружено — терминология канонична)**.

**Платформа готова к CI на ~70%:** весь исполняемый слой (Scenario → Factory/Forge → артефакт → валидация → память) уже существует и работает (`ForgeFacade.run_chain`, 14 ролей). Не хватает именно **Intelligence-слоя**: обнаружение возможностей (Opportunity Engine) и лёгкий захват мыслей (Whim) — это G3, оба регистрируются register-first.

---

## 1. Карта G0–G4: целевая модель CI (промт 1 §8) ↔ реестры платформы

> Классификация: **G0** = уже есть, используем напрямую · **G1** = есть, нужен адаптер · **G2** = есть, но недостаточно (нужно расширение) · **G3** = примитива нет · **G4** = архитектурный конфликт.

### 1.1 OBSERVE → COLLECT → UNDERSTAND → CONNECT

| Шаг целевой модели | Класс | Эвиденс (реализация) | CONFIDENCE |
|--------------------|:-----:|----------------------|:----------:|
| **OBSERVE** (наблюдение за проектом) | **G0** | `scripts_01/project_pulse.py` (ProjectPulse: `scan_git()`, `scan_files()`, `subscribe_eventbus()`, SQLite `data_13/project_pulse.db`); `scripts_01/event_bus.py` (EventBus `publish`/`subscribe`, event_log) | HIGH |
| **COLLECT** (сбор сигналов: чат/файлы/задачи) | **G0** | `scripts_01/prompt_dispatcher.py` + `prompt_queue.py` (очередь задач, cron-тика, multi-turn); `scripts_01/memory_engine.py` (MemoryEngine `store/retrieve/search`); `knowledge_engine` (FTS5+TF-IDF+SVD) | HIGH |
| **UNDERSTAND** (понимание контекста) | **G0** | `scripts_01/knowledge_engine.py` (KnowledgeEngine: `search` hybrid, `index_document`); `core_02/semantic_layer.py`; `core_02/learning_loop.py` (классификация observation/lesson) | MEDIUM |
| **CONNECT** (связывание знаний) | **G0** | `scripts_01/graph_index.py` (GraphIndex: nodes/edges, 7+ типов связей, BFS, subgraph); `core_02/memory_store.py` (knowledge_objects + knowledge_links, SQLite `data_13/context.db`) | HIGH |

**Примечание:** OBSERVE/COLLECT — адаптивный слой нужен только для специфичных CI-источников (Whim, контентные сигналы) — это G1 (адаптер), не G3.

### 1.2 G1 — есть, но нужен адаптер (сводная строка)

| Шаг целевой модели | Класс | Эвиденс | CONFIDENCE |
|--------------------|:-----:|---------|:----------:|
| **MONITORING → CI-сигналы** (OBSERVE/COLLECT для контентных источников) | **G1** | `project_pulse.py` (scan_git/scan_files) + `event_bus.py` дают сырые наблюдения; нужен адаптер «pulse/event → контентный сигнал» (извлечение тем/инсайтов из проекта для Opportunity Engine) | MEDIUM |
| **SELECT SCENARIO → по opportunity** (выбор не по свободному запросу, а по обнаруженной возможности) | **G1** | `scenario_registry.py` (`propose_roles()` — fuzzy-match по строке запроса); для CI нужен адаптер «Opportunity → подходящий Scenario/Role» (Resolution по CapabilityRef, SCENARIO_ENGINE_DESIGN §6) | MEDIUM |

**Итог G1:** адаптеров всего 2 и оба тонкие — обёртки над существующими `project_pulse`/`scenario_registry`, не новые подсистемы.

### 1.3 DISCOVER OPPORTUNITIES → PROPOSE (Intelligence-слой)

| Шаг целевой модели | Класс | Эвиденс | CONFIDENCE |
|--------------------|:-----:|---------|:----------:|
| **DISCOVER OPPORTUNITIES** (обнаружение возможностей) | **G3** | НЕТ реализации: Opportunity Engine отсутствует в коде (`grep -ri "opportunity" core_02/ scripts_01/` → только дизайн-документ `SCENARIO_ENGINE_DESIGN_V1.md` §Opportunity lifecycle, кода нет) | HIGH |
| **PROPOSE** (предложение действия) | **G3** | НЕТ: нет механики «предложить пользователю возможность»; ближайший аналог — `ScenarioRegistry.propose_roles()` (fuzzy-match роли по запросу) — это SELECT, не PROPOSE | HIGH |

**Вывод G3:** отсутствуют **два ядра Intelligence-слоя** — Opportunity Engine (обнаружение + жизненный цикл ACTIVE/DEFERRED/READY, concept_1/2) и механизм предложения. Оба — кандидаты на register-first (см. §3).

### 1.4 SELECT SCENARIO → EXECUTE → VALIDATE → ACCUMULATE (исполняемый слой)

| Шаг целевой модели | Класс | Эвиденс | CONFIDENCE |
|--------------------|:-----:|---------|:----------:|
| **SELECT SCENARIO** (выбор сценария) | **G0** (база) / **G1** (CI-адаптер) | `core_02/scenario_registry.py` (ScenarioRegistry: `list_scenarios()`, `get()`, `find_role()`, `propose_roles()` — авто-discovery YAML `runtime_05/scenarios/`); `scripts_01/wizard.py --scenario`. База — G0; CI-выбор «Opportunity → подходящий Scenario/Role» (по CapabilityRef) — G1, см. §1.2 | HIGH |
| **EXECUTE THROUGH FACTORY/FORGES** | **G0** | `core_02/forge_facade.py` (ForgeFacade: `initiate_forge()`, `run_chain()` — PIPELINE_CHAIN 14 ролей, LIGHT/HEAVY/conditional); `core_02/forge_pipeline.py` (FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT); `core_02/workspace.py` (Project) | HIGH |
| **VALIDATE** | **G0** | `ForgeFacade.validate_role_artifacts()` → `RoleArtifactValidator.validate()` (existence-check артефактов 14 ролей, registry.yaml → DEFAULT_ROLE_OUTPUTS fallback); `scripts_01/drift_check.py` + `consistency_check.py` | HIGH |
| **ACCUMULATE KNOWLEDGE** | **G0** | `core_02/memory_store.py` (MemoryStore `store_knowledge()` — knowledge_objects, 10 kinds, lifecycle); `scripts_01/engineering_memory.py`; `core_02/learning_loop.py` (feedback → confidence) | HIGH |

**Вывод:** исполняемый конвейер CI (выбор сценария → фабрика/кузня → артефакт → валидация → накопление) **полностью реализован и работает**. Это главная находка: CI не нужно строить конвейер — нужно построить только Intelligence-слой поверх существующего.

---

## 2. Карта примитивов (промт 1 §6) — статусы CONFIRMED/PARTIAL/ABSENT

| Примитив | Статус | Эвиденс |
|----------|:------:|---------|
| PROJECT | ✅ CONFIRMED | `core_02/workspace.py` (Project: root, name, requirements, type) |
| WORKSPACE | ✅ CONFIRMED | `core_02/workspace_registry.py` (WorkspaceRegistry), `data_13/context.db` |
| SCENARIO | ✅ CONFIRMED | `scenario_registry.py` + `runtime_05/scenarios/*.yaml` (blueprint_v3 type) |
| FACTORY | 🟡 PARTIAL | Дизайн готов: `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` (FactoryRegistry, Missing Capability #1) — **кода нет** → G2 |
| FORGE | ✅ CONFIRMED | `forge_facade.py` (14 pipeline-ролей), `forge_registry.py` (statuses UNFORGED→DEPLOYED), `data_13/forge_registry.yaml` (1519 строк, реальные проекты) |
| MEMORY | ✅ CONFIRMED | `memory_engine.py` (5 уровней JSON), `memory_store.py` (SQLite knowledge_objects) |
| KNOWLEDGE | ✅ CONFIRMED | `knowledge_engine.py` (FTS5+TF-IDF+SVD), `graph_index.py`, `semantic_layer.py` |
| EVENT | ✅ CONFIRMED | `event_bus.py` (publish/subscribe, event_log/event_store), `context_12/events.db` |
| TASK | ✅ CONFIRMED | `scripts_01/task_manager.py`, `prompt_queue.py` (queued tasks, multi-turn) |
| STORAGE | ✅ CONFIRMED | `data_13/` (forge_registry.yaml, missing_registry.yaml, context.db, collaboration.db, metrics.db, presence.db, project_pulse.db, roles.db, verifier.db) |
| OBSERVATION | 🟡 PARTIAL | `project_pulse.py` (сканы git/files), `learning_loop.py` (kind=observation) — но нет «сигнал → opportunity» цепочки → G3 для CI-целей |
| SCHEDULER | ✅ CONFIRMED | cron-скрипты (`cron_conspect.sh`, `prompt_dispatch.sh`, `auto_continue.sh`), `prompt_dispatcher.py --once/--all` |
| MONITORING | 🟡 PARTIAL | `project_pulse.py`, `system_monitor.py`, `presence.py` — есть наблюдение, нет CI-анализа |
| TOOL | ✅ CONFIRMED | `research_web.py` (implemented, Missing #6), `lisa_estimator.py` (implemented, Missing #7), `tool_runtime.py` |
| PLUGIN | ✅ CONFIRMED | `freebuff_plugin_03/` (plugin_api, mcp_server, bridge_layer) |
| **WHIM / OPPORTUNITY** | ❌ ABSENT | Нет ни в коде, ни в YAML-реестрах (grep: 0 совпадений в core_02/scripts_01); только концепты content_factory + дизайн SCENARIO_ENGINE_DESIGN → **G3** |
| AGENT / RUNTIME | ✅ CONFIRMED | `distributed_agents.py` (AgentMesh), `runtime_05/providers/`, `freebuff_plugin_03/runtime/` |

---

## 3. Реестры платформы (по запросу) — как они закрывают CI-модель

| Реестр | Расположение | Что даёт CI | Класс |
|--------|--------------|-------------|:-----:|
| **ForgeRegistry** | `core_02/forge_registry.py` + `data_13/forge_registry.yaml` | Статусы проектов (UNFORGED→DEPLOYED), история pipeline — **реальная карта производственного состояния** для OBSERVE/COLLECT | G0 |
| **ScenarioRegistry** | `core_02/scenario_registry.py` + `runtime_05/scenarios/` | Каталог сценариев + роли; **SELECT SCENARIO** уже работает (list/get/find_role/propose_roles) | G0 |
| **ForgeFacade** | `core_02/forge_facade.py` | **EXECUTE**: `initiate_forge()` (единственный санкционированный мост §7.3), `run_chain()` (14 ролей), `validate_role_artifacts()` (VALIDATE) — ядро исполняемого слоя CI | G0 |
| **MissingRegistry** | `core_02/missing_registry.py` + `data_13/missing_registry.yaml` | **Реестр G3-элементов** (register-first): factory_registry (design_ready), scenario_engine (design_ready), research_web (implemented), lisa_estimator (implemented), decision_registry/conformance_checker/model_diagram_autogen (registered) | G0 |
| **FactoryRegistry** (целевой) | Дизайн: `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md` | Машиночитаемые паспорта кузен (dataclass ForgePassport + FactoryRegistry); **кода нет** → Missing Capability #1, status=design_ready | **G2** |

### 3.1 Что MissingRegistry уже зарегистрировал (актуальные записи)

```
factory_registry     design_ready   registry   — Реестр фабрик и кузен, паспорта (Missing #1)
scenario_engine      design_ready   system     — Исполнение сценариев-композиторов (Missing #2)
decision_registry    registered     registry   — ADR-реестр как структура данных (Missing #3)
conformance_checker  registered     tool       — Машиночитаемый Conformance checker (Missing #4)
model_diagram_autogen registered    tool       — Автогенерация моделей/диаграмм (Missing #5)
research_web         implemented    tool       — Web Research (Missing #6)
lisa_estimator       implemented    tool       — Estimation LISA-3 (Missing #7)
```

---

## 4. Integration Gaps (промт 1 §14) — таблица Capability/Existing/Evidence/Reusable/Gap

| Capability | Existing | Evidence | Reusable | Gap |
|-----------|----------|----------|:--------:|:---:|
| Project context | ✅ | `workspace.py` Project, `workspace_registry.py` | Да | G0 |
| Agent attachment | ✅ | `distributed_agents.py`, `runtime_05/providers/` | Да | G0 |
| Chat | ✅ | `telegram_bot.py`, `mcp_server.py`, `prompt_dispatcher.py` (multi-turn) | Да | G0 |
| Memory | ✅ | `memory_engine.py` (5 уровней), `memory_store.py` (SQLite) | Да | G0 |
| **Whim-like capture** | ❌ | НЕТ (grep 0) | — | **G3** |
| Knowledge | ✅ | `knowledge_engine.py`, `graph_index.py`, `semantic_layer.py` | Да | G0 |
| Event system | ✅ | `event_bus.py`, `context_12/events.db` | Да | G0 |
| Scheduler | ✅ | cron `prompt_dispatch.sh`, `prompt_dispatcher.py --once` | Да | G0 |
| Monitoring | 🟡 | `project_pulse.py` (scan_git/files), `system_monitor.py` | Да (расширить) | G1 |
| Scenario execution | ✅ | `scenario_registry.py` + `forge_facade.run_chain()` | Да | G0 |
| Factory | 🟡 | Дизайн `FORGE_PASSPORT_CODE_REPRESENTATION_V1.md`; кода нет | Нет пока | **G2** |
| Forge | ✅ | `forge_pipeline.py`, `forge_facade.py`, `forge_registry.py` | Да | G0 |
| Storage | ✅ | `data_13/*.yaml + *.db`, `context_12/` | Да | G0 |
| **Opportunity tracking** | ❌ | НЕТ (только дизайн SCENARIO_ENGINE_DESIGN §Opportunity) | — | **G3** |

---

## 5. Architectural Conflicts (промт 1 §19-H)

**G4 = 0.** Конфликтов с существующей архитектурой не обнаружено:

- **Терминология канонична:** Factory/Forge/Scenario промта 1 дословно совпадают с картой v1.1 (ARB-REV-003) — naming collision ARB-REV-001 НЕ применим (подтверждено ARB-REV-004).
- **`ForgeFacade` — единственный мост:** CI будет вызывать Forge ТОЛЬКО через `ForgeFacade.initiate_forge()` (§7.3 boundary сохранён, «Direct Forge call из Scenario — НЕТ»).
- **Новые сущности CI (Opportunity/Whim) не конфликтуют** с B1–B14: это доменные объекты Intelligence-слоя (вне Factory), не пересекаются с ForgeRegistry/ScenarioRegistry.

---

## 6. Register-first: кандидаты на регистрацию (из этой форензики)

По принципу AGENTS.md §5 (register-first) — обнаруженные G3-элементы должны быть зарегистрированы в MissingRegistry, прежде чем проектироваться:

| item_id | kind | factory | Статус сейчас | Действие |
|---------|------|---------|---------------|----------|
| `opportunity_engine` | engine | (content) | НЕ зарегистрирован | `register opportunity_engine --kind engine --factory content` — ядро Intelligence-слоя CI (DISCOVER+PROPOSE) |
| `whim_capture` | module | (content) | НЕ зарегистрирован | `register whim_capture --kind module --factory content` — лёгкий захват мыслей (G3, DEFERRED ≠ DELETED) |
| `factory_registry` | registry | — | design_ready | уже зарегистрирован (Missing #1) — следующий шаг: промт → mark-implemented |
| `scenario_engine` | system | — | design_ready | уже зарегистрирован (Missing #2) — реализация после материальных кузен |

> ⚠️ Это **кандидаты** на регистрацию — действие не выполнено в рамках данного документа (форензика read-only по промту 1 §15/§21: «IMPLEMENTATION NOT STARTED»). Регистрация — по отдельному запросу.

---

## 7. Вердикт форензики

### READY WITH ADAPTER (по промту 1 §19-K)

**Почему:** исполняемый слой CI (Scenario → Factory/Forge → артефакт → валидация → память) **реализован и работает** (ForgeFacade 14 ролей + ScenarioRegistry + ForgeRegistry). Платформа готова к CI на ~70%.

**Что нужно построить (не переделывать):**
1. **G3 — Opportunity Engine** (обнаружение возможностей + lifecycle ACTIVE/DEFERRED/READY/REACTIVATED) — ядро Intelligence-слоя;
2. **G3 — Whim-захват** (лёгкий вход мыслей, DEFERRED ≠ DELETED);
3. **G2 — FactoryRegistry** (паспорта кузен: дизайн готов, реализация — Missing Capability #1);
4. **G1 — адаптер мониторинга** (project_pulse/event_bus → CI-сигналы).

**Первый vertical slice (по §18):** Whim/Opportunity → SELECT SCENARIO (ScenarioRegistry) → EXECUTE (ForgeFacade.run_chain) → VALIDATE → ACCUMULATE — весь исполняемый хвост уже существует, slice требует только Intelligence-голову.

---

*Forensics выполнена по методологии промта 1 (repository = источник истины, evidence-правило §20, G0–G4 §16). Код > тесты > конфиг > доки > предположения. Прецедент: ARB-REV-004 (RA2 — маппинг G0–G4 на словарь платформы + register-first). Связанные документы: ARB_REVIEW_PLATFORM_FORENSICS_PROMPT_V1.md, SCENARIO_ENGINE_DESIGN_V1.md, FORGE_PASSPORT_CODE_REPRESENTATION_V1.md, FACTORY_FORGE_ARCHITECTURE_V1.md (v1.1).*


**REPOSITORY FORENSICS COMPLETE — IMPLEMENTATION NOT STARTED.**
