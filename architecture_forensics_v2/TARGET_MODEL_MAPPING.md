# TARGET_MODEL_MAPPING.md — Сопоставление модели и реальности

> **Методология:** 104_19_platform_architectural_forensics_v2 §18 (модель «автомобиль») + §26 (CURRENT vs TARGET)

---

## 1. Полная модель (промт104 §18)

```
Человек → Whim → Workspace OS → Workspace → Project → Intelligence/Companion
  → Scenario → Factory → Forge → Agents → Skills → Tools → Artifacts
  → Project → Intelligence
```

## 2. Поэлементная проверка

| Element | Exists | Exact impl | Partial | Concept only | Missing | Evidence |
|---------|--------|------------|---------|--------------|---------|----------|
| Человек | ✅ | CLI/TG/MCP/REST | — | — | — | scripts_01/forge.py, telegram_bot.py |
| Whim | ✅ | whim_capture.py | — | — | — | Whim dataclass, WhimStore, lifecycle NEW→TRIAGED→PROMOTED |
| Workspace OS | ⚠️ | — | + | + | — | Весь репозиторий = "Workspace OS"; нет отдельного модуля |
| Workspace | ✅ | workspace.py Workspace | — | — | — | L-1 container, workspace.yaml |
| Project | ✅ | workspace.py Project | — | — | — | L-2 container, project.yaml, STEPS.md |
| Intelligence | ⚠️ | — | + | + | — | Emergent: Orchestrator+ScenarioIntelligence+Context+Memory+Knowledge (нет единого слоя) |
| Companion | ⚠️ | — | + | + | — | ScenarioIntelligence reactive only (нет proactive) |
| Scenario | ✅ | scenario.py + registry | — | — | — | ABC + auto-discovery YAML |
| Factory | ✅ | factory_base + registry | — | — | — | BaseFactory + 3 concrete + auto-discovery |
| Forge | ✅ | forge_pipeline + facade | — | — | — | 6-stage pipeline + единственный мост |
| Agent | ⚠️ | — | + | + | — | Pipeline-роли + presence; нет Agent ABC |
| Skill | ❌ | — | — | — | + | Нет сущности Skill |
| Tool | ✅ | tool_runtime.py | — | — | — | ToolRegistry + 5 built-in |
| Artifact | ⚠️ | — | + | — | — | Dict в normalize_output; нет registry |
| Memory | ✅ | memory_engine + memory_store | — | — | — | Multi-level memory + SQLite store |
| Knowledge | ✅ | knowledge_engine.py | — | — | — | FTS + TF-IDF + graph |
| Event | ✅ | event_bus.py | — | — | — | Pub/sub EventBus |
| Runtime | ✅ | freebuff_plugin_03/runtime/ | — | — | — | RuntimeRegistry + adapters |
| Plugin | ✅ | plugin_api.py | — | — | — | PluginRegistry + BasePlugin + 3 plugins |
| Feedback | ⚠️ | — | + | — | — | _accumulate + LearningLoop; узкий |
| Evolution | ❌ | — | — | — | + | Нет кода |

## 3. Итоговая статистика

| Статус | Кол-во | Элементы |
|--------|--------|----------|
| ✅ EXISTS | 12 | Whim, Workspace, Project, Scenario, Factory, Forge, Tool, Memory, Knowledge, Event, Runtime, Plugin |
| ⚠️ PARTIAL | 6 | Workspace OS, Intelligence, Companion, Agent, Artifact, Feedback |
| ❌ MISSING | 2 | Skill, Evolution |

**Соответствие модели: ~60%** (12/20 полных; ~75% с учётом частичных как половина)
