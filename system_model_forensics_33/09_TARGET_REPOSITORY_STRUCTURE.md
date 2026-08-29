# 09_TARGET_REPOSITORY_STRUCTURE.md — Целевая структура

> **Задача (§9):** предложить структуру, соответствующую РЕАЛЬНОЙ архитектуре (не шаблон из §9).

---

## Предлагаемая структура (минимальная, аддитивная)

```
freebuff/                                  ← workspace root (local-first)
├── platform/                              ← PLATFORM (всё, что не project-specific)
│   ├── core/                              ← core_02/ (Workspace/Project/Scenario/Factory/Forge/Router/Boundaries)
│   ├── forge/                             ← ForgePassport + ForgeFacade + ForgePipeline + ForgeRegistry
│   ├── scenario/                          ← scenario.py + scenario_registry.py + blueprint_v3.py
│   ├── factory/                           ← factory_registry + factory_base + factory_passport + forge_passport
│   ├── agents/                            ← role_executor.py + distributed_agents.py (будущий stateful Agent)
│   ├── runtime/                           ← freebuff_plugin_03/runtime/ (RuntimeRegistry)
│   ├── tools/                             ← tool_runtime.py
│   ├── intelligence/                      ← whim_capture + opportunity_engine + scenario_intelligence
│   ├── memory/                            ← memory_store + learning_loop + semantic_layer
│   ├── knowledge/                         ← knowledge_engine + rag_engine + graph_index
│   ├── interfaces/                        ← forge.py (CLI) + forge_api + mcp + tg
│   ├── config/                            ← runtime_05/ (factories + scenarios + recipes + providers)
│   ├── storage/                           ← context_12/ + data_13/ (единый home)
│   └── tests/                             ← tests_09/
├── projects/                              ← projects_17/ (пользовательские проекты)
├── prompts/                               ← pompts_11/
├── docs/                                  ← docs_10/
├── evaluations/                           ← phase*_evaluation_* + *forensics_* (архив)
└── archive/                               ← legacy (screenshots/logs/books/trash/freebuff_plugin/…)
```

> ⚠️ **Важно (promt105 предупреждение):** любой новый top-level каталог ДОЛЖЕН
> следовать конвенции `имя_NN` (или получить задокументированное исключение в
> `consistency_check._EVALUATION_PACKAGE_DIRS`), иначе `naming_convention` сломается.
> Поэтому `platform/`, `projects/`, `archive/` выше — **целевая модель**, а не
> немедленная перестановка: фактический перенос требует либо `platform_34`-стиля
> имён, либо обновления валидатора.

---

## Ответственность каждого каталога

| Каталог | Ответственность | Что ТУДА | Что НЕ туда | Потребитель |
|---------|-----------------|----------|-------------|-------------|
| `platform/core/` | контейнеры + границы | workspace.py, boundaries_v17 | НЕ entrypoints | все слои |
| `platform/forge/` | исполнение + паспорт + статусы | forge_facade/forge_pipeline/forge_passport/forge_registry | НЕ scenario | factory, cli |
| `platform/factory/` | capability-каталог | factory_registry/factory_base/factory_passport | НЕ конкретные артефакты | intelligence |
| `platform/scenario/` | корпус ролей | scenario.py/scenario_registry/blueprint_v3 | НЕ decision-логика | factory, wizard |
| `platform/agents/` | роли-исполнители | role_executor.py, distributed_agents.py | НЕ stateless tools | forge |
| `platform/intelligence/` | автономный head | whim_capture/opportunity_engine/scenario_intelligence | НЕ production forge | пользователь/агент |
| `platform/tools/` | интерфейсы действий | tool_runtime.py | НЕ LLM-routing | orchestrator |
| `platform/interfaces/` | entrypoints | forge.py/forge_api/mcp/tg | НЕ бизнес-логика | пользователь |
| `platform/memory/` + `knowledge/` | память/знания | memory_store/learning_loop/knowledge_engine | НЕ project-data | все |
| `projects/` | пользовательские проекты | projects_17/* | НЕ platform-code | пользователь |
| `docs/` | документация | docs_10/* | НЕ код | человек/агент |
| `evaluations/` | forensic-пакеты | phase*_evaluation + *forensics_* | НЕ runtime | аудитор |
| `archive/` | legacy | screenshots/logs/books/freebuff_plugin | НЕ active code | никто (cold) |

---

## Правила зависимостей

**Допустимые:**
- `core → (forge, factory, scenario, memory, knowledge, agents)` — вниз по слою.
- `interfaces → (forge, factory, intelligence, tools)` — entrypoints вызывают ядро.
- `intelligence → (scenario, factory, forge)` — intelligence-путь.

**Запрещённые (существующие нарушения):**
- `scenario → forge` напрямую (§7.3, уже соблюдается через ForgeFacade — сохранить).
- `project → platform` (сейчас встречается: проекты импортируют `scripts_01/*`).
- `core → interfaces` (инверсия зависимостей).

---

## Что НЕ менять сейчас

- `forge_registry.py` (single source of truth, B10/R-127).
- `forge_facade.py` (§7.3 boundary).
- `data_13/*` (production-состояние).
- Активные тесты `tests_09/`.
