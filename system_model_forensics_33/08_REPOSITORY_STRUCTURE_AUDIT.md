# 08_REPOSITORY_STRUCTURE_AUDIT.md — Аудит «каши» репозитория

> **Задача (§8):** определить, что относится к PLATFORM / PROJECT / FACTORY / FORGE /
> SCENARIO / AGENT / KNOWLEDGE / DOCUMENTATION / EXPERIMENT / LEGACY.

---

## Классификация существующего репозитория

| Каталог / файл | Класс | Признак |
|----------------|-------|---------|
| `core_02/` | PLATFORM CORE | Workspace/Project/Scenario/Factory/Forge/Router/RoleExecutor/Boundaries |
| `scripts_01/` (platform-часть) | PLATFORM ENTRY+INTELLIGENCE+TOOLS | forge.py, forge_api, whim/opportunity/scenario_intelligence, tool_runtime, router-gateway |
| `scripts_01/content_factory.py` и пр. | FACTORY ADAPTER | наследники BaseFactory |
| `runtime_05/factories/` | FACTORY (declarative) | YAML-паспорта |
| `runtime_05/scenarios/` | SCENARIO (declarative) | blueprint_v3/vkusvill_demo/19_remote_sync |
| `runtime_05/recipes/` + `providers/` | RUNTIME CONFIG | рецепты/провайдеры |
| `freebuff_plugin_03/` | PLATFORM RUNTIME (plugin) | API/MCP/TG/bridge/runtime/acp |
| `plugins_04/` | PLATFORM PLUGINS | манифесты |
| `services_08/`, `src_06/`, `cli_07/` | PLATFORM (seed) | почти пусты |
| `context_12/`, `data_13/` | PLATFORM STORAGE | events.db, whims/opportunities/forge_registry |
| `projects_17/` | PROJECT | пользовательские проекты |
| `tests_09/` | PLATFORM TESTS | тесты |
| `pompts_11/` | PROMPTS | контракты NNN_TT_name.md |
| `docs_10/` | DOCUMENTATION | core/engineering-memory/decisions/vision |
| `phase*_evaluation_*` (24–31) | LEGACY (аудит-след) | исторические forensic-пакеты |
| `architecture_forensics_v2/`, `repository_organization_forensics_32/`, `system_model_forensics_33/` | EVALUATION | recent forensic пакеты |
| `screenshots_16/`, `logs_14/`, `sessions_15/`, `books_out_23/`, `trash_21/`, `infa_20/`, `frontend_18/` | LEGACY/ARTIFACTS | материалы/логи |
| `buffy-playground_19/`, `prototype_22/` | EXPERIMENT | frontend-прототипы |
| `freebuff_plugin/` (без NN) | LEGACY | старый плагин |
| корневые `.md` (AGENTS/BUFFY/TASK/CHANGELOG/SPEC/…) | DOCUMENTATION (canonical) | правила платформы |

---

## Проблемы структуры (§8)

| Проблема | Evidence |
|----------|----------|
| Код и документация перемешаны | `core_02/LESSONS.md` (док) рядом с кодом; `scripts_01/nohup.out` (лог) рядом с кодом |
| Несколько источников истины | `data_13/` vs `scripts_01/data/` (5 db дублируются: metrics/roles/presence/collaboration/project_pulse) |
| Старые концепции рядом с новыми | `freebuff_plugin/` (старый) vs `freebuff_plugin_03/` (новый); `runtime_05/` vs `freebuff_plugin_03/runtime/` |
| Исторические документы | `phase*_evaluation_*` (24–31), `books_out_23/`, `screenshots_16/` |
| Experimental code | `buffy-playground_19/`, `prototype_22/`, `src_06/`, `cli_07/` |
| Production code | `core_02/`, `scripts_01/` (forge/intelligence/entrypoints) |
| Project-specific code | `projects_17/*` |
| Platform-level code | `core_02/`, `scripts_01/` |
| Prompts | `pompts_11/` |
| Architecture/docs | `docs_10/` |
| Tests | `tests_09/` |
| Scripts | `scripts_01/` + shell-скрипты в корне и `scripts_01/` |
| Data | `data_13/`, `context_12/`, `scripts_01/data/` |
| Generated artifacts | `books_out_23/` (HTML), `screenshots_16/`, `nohup.out` |

---

## Ключевые аномалии

1. **Терминологический drift:** «Forge» = 4 смысла (см. 06), «Scenario» = 2 смысла (06).
2. **Двойной source-of-truth для db:** `scripts_01/data/*.db` vs `data_13/*.db` (5 db в обоих местах).
3. **Три execution-парадигмы:** forge chain / opportunity→forge / orchestrator DAG (03).
4. **Skill отсутствует, Opportunity не описан** в целевой модели (05).
5. **NN-нумерация — исторический артефакт**, не отражает слой (promt105 R-вывод).
6. **`src_06/`, `cli_07/`, `services_08/` — seed-заглушки**, выглядят как слои, но почти пусты.

## Общая оценка структуры

Функционально — рабочий монолит с файловой изоляцией Project (`projects_17/`).
Архитектурно — навигация затруднена: слои не совпадают с каталогами, термины
перегружены, несколько мест хранят одни и те же данные.

**Оценка организации: 5.0/10** (совпадает с promt105; не ухудшилась, но промт106
выявил дополнительно терминологическую перегрузку Forge/Scenario и отсутствие Skill).
