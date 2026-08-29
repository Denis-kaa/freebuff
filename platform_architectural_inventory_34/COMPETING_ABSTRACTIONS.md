# COMPETING ABSTRACTIONS — promt107 §17 forensic

> Для каждой пары A vs B: ответственность, пересечение, различие, кто реально используется, источник истины, нужна ли унификация.

## 1. Workspace модель ×2

| | A: workspace.py | B: workspace_registry.py |
|---|---|---|
| Ответственность | YAML-контейнер L-1 (root, projects, steps_policy) | SQLite workspace↔project + privacy guard |
| Хранение | workspace.yaml | data_13/context.db |
| Реально используется | Forge (Project.load) | scan_projects, privacy check |
| Источник истины | конфликт: два разных | — |
| Унификация | **ДА** — единая модель, один из двух должен стать source-of-truth | |

## 2. Role model ×2

| | A: Blueprint pipeline-роли | B: roles.py collab-роли |
|---|---|---|
| Ответственность | 14-17 production-ролей (explainer..retrospective) | 6 CoWork-ролей (orchestrator..archiver) |
| Хранение | registry.yaml + role .md | roles.db (SQLite) |
| Реально используется | ForgeFacade.run_chain | MCP/CLI role management |
| Пересечение | orchestrator есть в обеих (REFERENCE_ROLES vs collab) | |
| Унификация | НЕ объединять автоматически — разные слои (production vs collaboration) | |

## 3. Task system ×2

| | A: task_manager.py | B: orchestrator.py |
|---|---|---|
| Ответственность | SQLite tasks + LLM-брифинг | Workflow/Step/ToolExecutor/Planner |
| Пересечение | оба управляют «задачами» | |
| Унификация | **ДА** — явно разграничить (persistence vs orchestration) или объединить | |

## 4. Tool system ×2

| | A: tool_runtime.py | B: mcp_server.py (McpTool) |
|---|---|---|
| Ответственность | 5 tool'ов (Git/SQLite/HTTP/File/Shell) | MCP tools/resources/prompts |
| Пересечение | оба — «инструменты» | |
| Унификация | **ДА** — единый tool-контракт, MCP как транспорт поверх ToolRegistry | |

## 5. Memory/Knowledge ×4

| | A | B | C | D |
|---|---|---|---|---|
| Модуль | memory_engine.py | knowledge_engine.py | graph_index.py | engineering_memory.py |
| Ответственность | L1-L3 память | FTS/TFIDF/Semantic | Node/Edge graph | engineering artifacts |
| Унификация | **ДА** — единый memory/knowledge source-of-truth (сейчас 4 конкурирующих) | | | |

## 6. Registry ×6

WorkspaceRegistry, ScenarioRegistry, FactoryRegistry, ForgeRegistry, MissingRegistry,
ToolRegistry (+ RoleExecutorRegistry). Каждый — свой формат/хранилище (SQLite/YAML/dict).
**Унификация:** НЕ объединять (разные домены, B-Rule 4/5 owner-file/namespace), но нужен
единый registry-контракт (discovery + query API + validation).

## 7. Orchestration / execution bridges ×3

ForgeFacade.run_chain (role→forge), orchestrator.py (workflow), scenario_intelligence.py
(decision). Три разных механизма orchestration — нет единого entry-point.
