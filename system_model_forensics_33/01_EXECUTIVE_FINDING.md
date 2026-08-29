# 01_EXECUTIVE_FINDING.md — Главный вывод

> **Forensic pass:** promt106 (Repository Forensics: System Modeling)
> **Версия:** v5.189.69 · **Дата:** 2026-08-21
> **Принцип (§18):** пытался ОПРОВЕРГНУТЬ целевую модель, а не подтвердить её.

---

## TL;DR

Платформа **реально работает по цепочке идея→артефакт**, но эта цепочка **не совпадает**
с целевой концептуальной моделью. Расхождений больше, чем совпадений на уровне
имён; на уровне потоков данных система функциональна, но терминологически и
структурно «перегружена».

**Фактическая цепочка (по коду):**

```
WHIM (whim_capture.py)
  → OPPORTUNITY (opportunity_engine.py)          ← СЛОЙ, ОТСУТСТВУЮЩИЙ В ЦЕЛЕВОЙ МОДЕЛИ
      → SCENARIO (scenario_intelligence.py + scenario_registry.py)
          → FACTORY (factory_registry.py, runtime_05/factories/*)
              → FORGE (forge_facade.py + forge_pipeline.py + forge_passport.py)
                  → ARTIFACT (файлы в project.root)
                      → MEMORY (memory_store.py + learning_loop.py)
```

## Главные расхождения (код vs целевая модель)

| # | Расхождение | Severity | Evidence |
|---|-------------|----------|----------|
| R1 | `Opportunity` — полноценный слой, отсутствует в целевой модели | HIGH | `scripts_01/opportunity_engine.py` (Opportunity dataclass, lifecycle ACTIVE→READY→COMPLETED, YAML `data_13/opportunities.yaml`) |
| R2 | Workspace/Project — тонкие YAML-контейнеры, НЕ «рабочая тетрадь с обсуждениями» | MEDIUM | `core_02/workspace.py` (Workspace.load / Project.load — только парсинг yaml + STEPS/env-доктор) |
| R3 | Scenario перегружен: статический «корпус ролей» vs динамический decision-слой | HIGH | `core_02/scenario.py` (ABC Scenario = role corpus) vs `scripts_01/scenario_intelligence.py` (Opportunity→capability→Factory) |
| R4 | Forge перегружен: 4 разных смысла | HIGH | `forge_passport.py` (декларация), `forge_facade.py` (chain-runner), `forge_pipeline.py` (CI FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT), `forge_registry.py` (реестр статусов) |
| R5 | Skill — ABSENT как модуль; только capability-токены | MEDIUM | нет `core_02/skill*.py`; `KNOWN_CAPABILITIES` в blueprint_v3 + `missing_registry.py` |
| R6 | Agent — PARTIAL; единой абстракции нет, размазан по 4 местам | HIGH | `role_executor.py` (RoleExecutorRegistry), `distributed_agents.py`, `freebuff_plugin_03/runtime/registry.py`, `plugins_04/` |
| R7 | Две конкурирующие execution-парадигмы | HIGH | `forge_facade.run_chain` (14-ролевой конвейер) vs `orchestrator.py` (FSM/DAG Goal→Plan→Execute→Validate) |

## Что реально РАБОТАЕТ (CONFIRMED)

- `forge.py chain` CLI → `ForgeFacade.run_chain` → 14 ролей → `forge_registry.record_run` (полный цикл, integration-тесты зелёные).
- `whim_capture` → `opportunity_engine.discover/propose/execute` → `ForgeFacade` → `memory_store` (vertical slice, тесты).
- `FactoryRegistry.select_forge(capability)` → `(FactoryPassport, ForgePassport)` (декларативные YAML-манифесты).
- `ScenarioIntelligence.select` → `ScenarioDecision` (domain-neutral, capability → factory/forge).
- Memory/Knowledge: `memory_store.py` + `learning_loop.py` + `knowledge_engine.py` + `semantic_layer.py`.

## Что PARTIAL / DESIGNED / ABSENT

- **Skill** — ABSENT (только токены capabilities; неявно через RoleExecutor).
- **Agent** — PARTIAL (RoleExecutor = «роль как генератор артефактов»; нет stateful агента с памятью).
- **Runtime** — PARTIAL (`freebuff_plugin_03/runtime/registry.py` — реестр рантаймов, не полноценный агентский слой).
- **Workspace** — PARTIAL (L-1 контейнер есть, но «разговор/обсуждения» живут в ContextManager/Memory, а не в Workspace).

## Ответы на 28 обязательных вопросов (§17)

1. **Что платформа сейчас?** — Локально-first (Termux/Android) AI-инженерная среда:
   слои контейнеров (Workspace/Project), Forge (конвейер + chain-runner), Intelligence
   (Whim→Opportunity→Scenario→Factory), агентские точки (RoleExecutor, Orchestrator, plugins).
2. **Путь идея→артефакт?** — Whim → Opportunity → Scenario → Factory → Forge → artifact → Memory.
3. **WHIM?** — `scripts_01/whim_capture.py` (`data_13/whims.yaml`, lifecycle NEW→TRIAGED→PROMOTED→…).
4. **Workspace?** — `core_02/workspace.py::Workspace` (L-1, `workspace.yaml`).
5. **Project?** — `core_02/workspace.py::Project` (L-2, `project.yaml` + README/RUNNABLE/CHECKLIST/STEPS).
6. **Слой агента?** — размазан: `role_executor.py`, `distributed_agents.py`, `freebuff_plugin_03/runtime/`, `plugins_04/`, `roles.py`+`presence.py`+`collaboration.py`.
7. **Scenario?** — двойственен: `scenario.py` (корпус ролей) + `scenario_intelligence.py` (decision-слой).
8. **Factory?** — `factory_registry.py` + `factory_base.py` + `runtime_05/factories/*/factory.yaml` (4 фабрики: architecture/content/research/test). Глобальная capability.
9. **Forge?** — 4 смысла (passport/facade/pipeline/registry).
10. **Skills?** — ABSENT как модуль; capability-токены.
11. **Tools?** — `scripts_01/tool_runtime.py` (GitTool/SQLiteTool/HTTPTool/FileTool/ShellTool) + `phone_control_mcp.py` (MCP-обёртка).
12. **Runtimes?** — `freebuff_plugin_03/runtime/registry.py` + `runtime_05/recipes/` + `runtime_05/providers/`.
13. **Artifact?** — файлы в `project.root` (роли пишут brief.md/lisa_report.md/…), не отдельный тип-контейнер.
14. **История проекта?** — `projects_17/<slug>/STEPS.md` + `forge_registry.pipeline_history` + `memory_store` (KO).
15. **Knowledge?** — `memory_store.py` (SQLite KO) + `knowledge_engine.py` (FTS/TF-IDF) + `semantic_layer.py` + `rag_engine.py` + `graph_index.py`.
16. **Глобальное vs project-specific?** — Factory/Forge/Scenario/Blueprint = глобальные; Project/artifact/STEPS = project-specific.
17. **Что перемешано?** — код/документация/промты в одном repo; старые концепции рядом с новыми; platform-code и project-code разделены только файлово (`projects_17/`).
18. **Что legacy?** — `scripts_01/archive/`, `freebuff_plugin/`, `buffy-playground_19/`, `phase*_evaluation_*` (исторические forensic-пакеты), `screenshots_16/`, `books_out_23/`, `trash_21/`.
19. **Что только документация?** — `docs_10/vision/`, `docs_10/decisions/IDEAS.md`, значительная часть `phase*_evaluation_*` (описывают, не исполняют).
20. **Что реально работает?** — Forge-цикл, Intelligence-вертикаль, Router, ToolRuntime, MCP/HTTP/Telegram-интерфейсы (тесты зелёные).
21. **Где архитектура расходится с документацией?** — см. R1–R7 выше (Opportunity не описан в целевой модели; «Skill» описан, но отсутствует в коде; Forge-термин документация употребляет в 1 смысле, код в 4).
22. **Логичная структура?** — см. 09_TARGET_REPOSITORY_STRUCTURE.md.
23. **Как разделить Platform/Project/Factory/Forge/Scenario?** — см. 06 и 09.
24. **Связь CODE↔DOCS↔CONTRACTS↔TESTS?** — см. 11 (doc_id + component_id + contract_id + test_path; реестр в `missing_registry`/`traceability.json`).
25. **Нужны ли semantic tags?** — ДА, выборочно (см. 11): на decision/ADR и на component-level, НЕ на каждый абзац.
26. **Где и какие?** — `[CONCEPT:…***REMOVED***`, `[COMPONENT:…***REMOVED***`, `[CONTRACT:…***REMOVED***`, `[STATUS:…***REMOVED***` в шапках архитектурных доков; связи — в graph (не в тексте).
27. **Первый минимальный безопасный refactoring?** — разделить термин Forge на 4 имени (ForgePassport/ForgeFacade/ForgePipeline/ForgeRegistry уже так и есть в именах файлов; зафиксировать в glossary) + зафиксировать слой Opportunity в целевой модели.
28. **Что НЕЛЬЗЯ рефакторить сейчас?** — `forge_registry.py` (single source of truth для статусов, B10/R-127), `forge_facade.py` (§7.3 boundary «direct Forge call из Scenario — НЕТ»), `data_13/*` (production-состояние), активные тесты.
