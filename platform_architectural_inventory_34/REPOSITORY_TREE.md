# REPOSITORY TREE — current snapshot (promt107 §20)

> Снимок структуры на 2026-08-22 (v5.189.72). Только ключевые каталоги, не весь репо.

```
freebuff/
├── core_02/          ← платформенное ядро (33 py): workspace, forge_*, factory_*, scenario_*,
│                        router, role_executor, blueprint_v3, registry, remote_sync, ...
├── scripts_01/       ← 82 py: CLI-входы, движки (memory, knowledge, graph, event, model_gateway,
│                        tool_runtime, orchestrator, task_manager, roles, whim, opportunity, mcp_*)
├── tests_09/         ← 122 test-файла
├── data_13/          ← состояние: *.db (context, roles, metrics, presence, ...) + *.yaml
│                        (forge_registry, missing_registry, lisa_calibration, whims, opportunities)
├── docs_10/          ← канон документации (core/, engineering-memory/, canonical/, decisions/)
├── pompts_11/        ← 103 промта (NNN_TT_name.md)
├── runtime_05/       ← factories/ (architecture, content, research, test) + scenarios/
├── freebuff_plugin_03/ ← runtime abstraction + MCP client/bridge + TG bot
├── plugins_04/       ← 4 плагина (hello_world, knowledge_sync, system_monitor, tg_messenger)
├── projects_17/      ← пользовательские проекты (18+: interior_planner, tg_terminal_messenger, ...)
├── freebuff_plugin/  ← старый плагин
├── prototype_22/, frontend_18/, buffy-playground_19/  ← UI-прототипы
├── phase*_NN/, intelligence_forensics_25/, repository_organization_forensics_32/,
│   system_model_forensics_33/, architecture_forensics_v2/  ← evaluation/forensic пакеты
├── trash_21/         ← архив старых артефактов
└── *.md (корень): AGENTS.md, BUFFY.md, TASK.md, CHANGELOG.md, SPEC.md, ...
```

## Анализ (почему структура такая)

1. **Нумерация `NN` каталогов — исторический артефакт** (01–33), НЕ архитектурные слои.
   Это порядок появления, а не доменное разделение.
2. **Домены размазаны:** Intelligence (scenario_intelligence.py) в scripts_01/, а НЕ в
   отдельном capabilities/intelligence/; factories в runtime_05/ + core_02/ + scripts_01/.
3. **Code/documentation/prompts/tests/data смешаны** на top-level (freebuff_cli.py, *.md
   в корне рядом с каталогами).
4. **Одна ответственность разбросана:** memory (memory_engine в scripts_01, memory_store
   в core_02, engineering_memory в scripts_01), registry (core_02 ×несколько).

## Target repository structure

Гипотеза promt107 §20 (platform/ core/ capabilities/ integrations/ runtime/ docs/ prompts/
tests/ scripts/ data/) **НЕ обязательна как физический перенос**. Рекомендация (аддитивная
канонизация, повторяет promt105): семантические алиасы + фиксация canonical home в
`docs_10/canonical/architecture.md`, БЕЗ физического mv на текущем этапе.

Подробнее — см. `system_model_forensics_33/09_TARGET_REPOSITORY_STRUCTURE.md`.
