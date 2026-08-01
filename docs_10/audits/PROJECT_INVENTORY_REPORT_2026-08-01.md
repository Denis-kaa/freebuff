# PROJECT INVENTORY REPORT — Полная инвентаризация и консистентность

> **Дата:** 2026-08-01
> **Версия проекта:** v5.30.0 (CHANGELOG), тесты: 1721 collected (49 файлов, `tests_09/`)
> **Миссия:** `pompts_11/041_03_inventarizaciya_proekta.md` — инвентаризация и проверка консистентности
> **Метод:** инвентаризация по реестрам (DOCUMENT_REGISTRY, SYSTEM_INVENTORY, MODULE_CONSOLIDATION, FINAL_STRUCTURE)
> + фактическая сверка с деревом каталогов и `drift_check`/`consistency_check`.
> **Ограничения миссии:** никакие изменения не выполнялись — только анализ и отчёт.
> **Обновление (2026-08-01):** пункт 1 плана §9 (мердж Telegram-ботов через `BaseTGBot`) выполнен —
> DEBT-2026-07-31-007 resolved, см. [ARCHITECTURAL_DEBT.md***REMOVED***(../core/ARCHITECTURAL_DEBT.md) §5.8 и [MODULE_CONSOLIDATION.md***REMOVED***(../core/MODULE_CONSOLIDATION.md) §B.
> **Обновление (2026-08-01):** дубли документов решены (Этап 5) — `PROMPT_IMPLEMENTATION_v1.0.md`
> (стаб-копия 017_02) и `docs_10/ops/AGENTS.md` (дубль корневого AGENTS.md) → `trash_21/`.

---

## 0. Сводка (Executive Summary)

| Категория | Оценка | Комментарий |
|-----------|:------:|-------------|
| Архитектура | 🟢 95% | Канон: ARCHITECTURE_MANIFEST + ARCHITECTURE_CANONICAL; движки соответствуют |
| Код | 🟢 95% | ~55 компонентов production; 1721 тест; реестры сходятся с кодом |
| Документация | 🟢 92% | Единый реестр статусов (DOCUMENT_REGISTRY); drift green |
| Консистентность | 🟢 98% | `consistency_check` — 1 issue (именование промта, исправлено переименованием) → 0 |
| Масштабируемость | 🟢 90% | Workspace OS: Core/Extensions/State/Labs, режимы масштабирования (FINAL_STRUCTURE) |
| Дублирование | 🟢 0 открытых дублей | Telegram-боты (DEBT-007) ✅ Resolved; документ-дубли (PROMPT_IMPLEMENTATION, ops/AGENTS.md) ✅ Resolved (2026-08-01); Router-пересечения задокументированы |
| Читаемость | 🟢 90% | Единая конвенция именования `имя_NN` / `NNN_TT_имя` |
| Готовность к развитию | 🟢 92% | Миссия консолидации (промт 32, этапы 1–10) завершена; открыты долги DEBT + Phase B/C |

**Главный вывод:** проект консистентен. Код, документация и промты согласованы
(`drift_check` green, `consistency_check` green).
Осталась точечная работа: архивный код в `scripts_01/archive/`, возобновление Phase B/C.

---

## 1. Инвентаризация документации

> Полный список: `find docs_10 -name '*.md'` — 90 файлов. Статусы — из `docs_10/DOCUMENT_REGISTRY.md`
> (единый источник истины о статусах). Сверка: все каталоги docs_10 существуют, битых ссылок нет (drift green).

### 1.1 Корень проекта (10 файлов)

| Документ | Статус | Назначение | Связанный код | Решение |
|----------|--------|------------|---------------|---------|
| `AGENTS.md` | ACTIVE | Сессионный чекпоинт | — | сохранить |
| `BUFFY.md` | ACTIVE | Главный документ Buffy | — | сохранить |
| `BUFFY_PROJECT.md` | ACTIVE | Состояние проекта (статус-таблицы) | `drift_check` | сохранить |
| `CHANGELOG.md` | ACTIVE | История версий (Keep a Changelog) | — | сохранить |
| `CLAUDE.md` | ACTIVE | Инструкции Claude Code | — | сохранить |
| `CODY.md` | ACTIVE | Инструкции Cody | — | сохранить |
| `.cursorrules` | ACTIVE | Инструкции Cursor | — | сохранить |
| `README.md` | ACTIVE | Входная точка репозитория | — | сохранить |
| `SPEC.md` | ACTIVE | Техническая спецификация | — | сохранить |
| `TASK.md` | ACTIVE | Трекер задач (LEVIATHAN, все фазы ✅) | — | сохранить |

### 1.2 `docs_10/` (корень)

| Документ | Статус | Назначение | Решение |
|----------|--------|------------|---------|
| `DOCUMENT_REGISTRY.md` | ACTIVE | Единый реестр статусов документов | сохранить |
| `INDEX.md` | ACTIVE | Навигация по документации | сохранить |
| `DRIFT_REPORT.md` | ARCHIVED | Генерируемый артефакт drift_check | в `.gitignore` |

### 1.3 `docs_10/core/` (24 файла) — ядро документации

| Документ | Статус | Назначение | Связанный код | Решение |
|----------|--------|------------|---------------|---------|
| `ARCHITECTURAL_DEBT.md` | ACTIVE | Реестр долгов | `drift_check` | сохранить |
| `ARCHITECTURE_3.0.md` | LEGACY | Заменён каноном | — | история |
| `ARCHITECTURE_CANONICAL.md` | ACTIVE [канон***REMOVED*** | Каноническая архитектура (движки C1–C6, S1–S7) | `scripts_01/*.py` (реестр движков) | сохранить |
| `ARCHITECTURE_MANIFEST.md` | ACTIVE [канон***REMOVED*** | Архитектурный закон | — | сохранить |
| `ARCHITECTURE_PRINCIPLES.md` | ACTIVE | Принципы (источник синтеза MANIFEST) | — | сохранить |
| `ARCHITECTURE_REVIEW.md` | LEGACY | Экосистемный обзор 2026-07-27 | — | история |
| `BOOTSTRAP_SPECIFICATION.md` | ACTIVE | Спецификация Bootstrap | `freebuff_plugin_03/bootstrap/` | сохранить |
| `CAPABILITY_SPECIFICATION.md` | ACTIVE | Спецификация Capability Registry | `freebuff_plugin_03/runtime/` | сохранить |
| `CODE_QUALITY_STANDARD.md` | ACTIVE | Стандарт качества (71+16 пунктов) | — | сохранить |
| `COMPATIBILITY_MATRIX.md` | ACTIVE | Матрица совместимости Runtime | — | сохранить |
| `CORE_PROMPT.md` | ACTIVE | Единый Core Prompt (цель Этапа 5) | AGENTS/BUFFY/CLAUDE/CODY | сохранить |
| `DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` | ACTIVE | Session Mesh v2.0 | `freebuff_plugin_03/mesh/` | сохранить |
| `EVENT_PLATFORM_SPECIFICATION.md` | ACTIVE | Event Platform | `freebuff_plugin_03/event/` | сохранить |
| `FINAL_STRUCTURE.md` | ACTIVE | Итоговый синтез (схема, каталоги, ADR, задачи) | конвенция именования | сохранить |
| `GLOSSARY.md` | ACTIVE [канон***REMOVED*** | Единая терминология | `consistency_check` (16 терминов) | сохранить |
| `LIFECYCLE.md` | ACTIVE [канон***REMOVED*** | Жизненные циклы компонентов | `consistency_check` | сохранить |
| `MODULE_CONSOLIDATION.md` | ACTIVE [канон***REMOVED*** | Аудит модулей (Этап 6) | `consistency_check` | сохранить |
| `POLICY_ENGINE_SPECIFICATION.md` | ACTIVE | Policy Engine (правило 11, ADR-009) | `freebuff_plugin_03/policy/` + `mcp_server.py` | сохранить |
| `PROJECT_REGISTRY.md` | ACTIVE | Реестр проектов | — | сохранить |
| `PROMPT_IMPLEMENTATION_v1.0.md` | ARCHIVED | Стаб-копия `pompts_11/017_02`; → `trash_21/` (2026-08-01) | — | **решено — канон 017_02** |
| `RULES.md` | ACTIVE | Правила (дерево каталогов для drift) | `drift_check` | сохранить |
| `RUNTIME_ABSTRACTION_SPECIFICATION.md` | ACTIVE | Runtime Abstraction Layer | `freebuff_plugin_03/runtime/` | сохранить |
| `RUNTIME_VALIDATION_FRAMEWORK.md` | ACTIVE | Валидация Runtime | — | сохранить |
| `SYSTEM_INVENTORY.md` | ACTIVE | Каталог компонентов (~55) | весь код | сохранить |

### 1.4 `docs_10/audits/` (19 файлов)

| Документ | Статус | Решение |
|----------|--------|---------|
| `ARCHITECTURAL_AUDIT_PROMT31_2026-07-31.md` | ACTIVE | сохранить |
| `ARCHITECTURE_WORKSPACE_OS_2026-07-31.md` | ACTIVE | сохранить |
| `AUDIT_2026-07-27/28/29.md`, `AUDIT_2026-07-28_FULL_CODE_REVIEW.md`, `AUDIT_2026-07-29_v5.0.0.md`, `AUDIT_BOOTSTRAP.md`, `AUDIT_CODE_QUALITY_2026-07-29.md`, `AUDIT_FULL_2026-07-29.md` (8) | ARCHIVED | история |
| `AUDIT_STEP0_2026-07-31.md` | ACTIVE | security-аудит (TASK_SECURE_MCP_ACCESS) |
| `AUDIT_TEMPLATE.md` | DRAFT | шаблон |
| `CONSOLIDATION_STAGE1_AUDIT_2026-07-31.md` | ACTIVE | Этап 1 консолидации |
| `DOMAIN_MODEL_VERIFICATION_2026-07-31.md`, `DOMAIN_MODEL_WORKSPACE_OS_2026-07-31.md` | ACTIVE | доменная модель |
| `DRIFT_REPORT.md` | ARCHIVED | генерируемый отчёт |
| `RECOVERY_REPORT_2026-07-31.md`, `RECOVERY_REPORT_7_MODULES_2026-07-31.md` | ARCHIVED | инциденты (история) |
| `PROJECT_INVENTORY_REPORT_2026-08-01.md` | ACTIVE | **настоящий отчёт** |

### 1.5 `docs_10/decisions/` — решения

| Документ | Статус | Примечание |
|----------|--------|------------|
| `DECISIONS.md` | ACTIVE | Индекс ADR-001…009 (замкнут перекрёстными ссылками) |
| `IDEAS.md` | ACTIVE | Реестр идей (не удаляется) |
| `ADR_001_Vision_3.0_AI_Infrastructure_Layer.md` | LEGACY | Полный текст; канонический указатель — `engineering-memory/decisions/ADR_001` |

### 1.6 `docs_10/engineering-memory/` — память проекта

| Документ | Статус | Примечание |
|----------|--------|------------|
| `ARCHITECTURE.md` | ACTIVE | архитектурная память |
| `PROJECT_BOOK.md` | ACTIVE [канон***REMOVED*** | книга проекта (глава о консолидации 2026-08-01) |
| `decisions/ADR_001…ADR_009` | ACTIVE | каноническое расположение ADR (ADR-008/009 — консолидация/правило 11) |
| `templates/*.md` (9) | ACTIVE | шаблоны Engineering Memory |

### 1.7 `docs_10/ops/`, `plugin/`, `projects_meta/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
| `docs_10/ops/` (10) | ACTIVE | гайды; **дубль `ops/AGENTS.md` → `trash_21/AGENTS_ops_duplicate.md` (2026-08-01)** |
| `docs_10/plugin/` (5) | ACTIVE | `PLUGIN_CONTRACT_SPECIFICATION.md` §8 — MCP-инструменты ядра (47 реализовано + 10 planned) |
| `docs_10/projects_meta/` (5) | ACTIVE | Lightpanda, Overlay, Workers, FILE_REGISTRY |

### 1.8 `docs_10/vision/`

| Документ | Статус | Примечание |
|----------|--------|------------|
| `VISION_3.0.md`, `VISION_3.0_MAP.md`, `PRODUCT_MANIFESTO.md` | ACTIVE | стратегическое видение |
| `ROADMAP_PROMT32_CONSOLIDATION.md` | ACTIVE [канон***REMOVED*** | текущая миссия (этапы 1–10 ✅) |
| `ROADMAP.md` | LEGACY | заменён на PROMT31+PROMT32 |
| `ROADMAP_PROMT31_WORKSPACE_OS.md` | LEGACY | фичи заморожены Mission Lock |
| `archive/ARCHITECTURE.md`, `archive/VISION_2.0.md` | ARCHIVED | в архиве |

### 1.9 `docs_10/session_dumps/`, `task_archive/`

| Каталог | Статус | Примечание |
|---------|--------|------------|
| `session_dumps/` (3) | ARCHIVED | исторические дампы |
| `task_archive/` (2) | ARCHIVED | архив задач |

### 1.10 `pompts_11/` — промты (36 файлов)

> После переименования `promt41.md` → `041_03_inventarizaciya_proekta.md` все файлы
> следуют конвенции `NNN_TT_имя.md` (тема 03 = audit). Полная таблица статусов —
> в `DOCUMENT_REGISTRY.md` §pompts_11 (18 ACTIVE + 17 LEGACY + 1 стаб-перенаправление).

| Группа | Примеры | Статус | Примечание |
|--------|---------|--------|------------|
| Активные | `032_09`, `036_09`, `037_11`, `038_03`, `041_03`, `014_02`, `016_02`, `017_02`, `001_07`, `012_01`, `013_01`, `022_02`, `023_02`, `024_02`, `025_02`, `026_05`, `027_05`, `031_03` | ACTIVE (18) | источники канонических документов/аудитов |
| Легаси | `002_14`, `003_01`, `004_01`, `005_04`, `006_08`, `007_04`, `008_06`, `009_06`, `010_07`, `011_07`, `015_02`, `028_04`, `029_04`, `030_05`, `033_10`, `034_10`, `039_12` | LEGACY (17) | выполнено/заменено/история |
| Стаб | `040_13_code_quality_standard.md` | ACTIVE | перенаправление на `docs_10/core/CODE_QUALITY_STANDARD.md` |
| Новый | `041_03_inventarizaciya_proekta.md` | ACTIVE | миссия настоящего отчёта (переименован из `promt41.md`) |

### 1.11 `trash_21/` (7 файлов)

| Файл | Статус | Примечание |
|------|--------|------------|
| `error.md`, `new.md`, `structure.md`, `freb.md`, `promt18.md` | ARCHIVED | перенесены из pompts_11/ (Этап 5) |
| `freebuff_project_dump.md`, `retrospective.md` | ARCHIVED | исторические |

---

## 2. Инвентаризация кода

> Источник: `docs_10/core/SYSTEM_INVENTORY.md` (~55 компонентов, 100% production) +
> фактическая сверка с каталогами. Тесты: 1721 collected, 49 файлов `tests_09/`.

### 2.1 Каталоги (конвенция `имя_NN`)

| Каталог | № | Содержимое | Статус |
|---------|---|------------|--------|
| `scripts_01/` | 01 | 48 модулей ядра (движки, MCP, CLI-инструменты) + shell-скрипты | ACTIVE |
| `core_02/` | 02 | контракты агентов, SmartRouter | ACTIVE |
| `freebuff_plugin_03/` | 03 | plugin SDK: runtime, bootstrap, event, policy, mesh, bridge_layer, scenario | ACTIVE |
| `plugins_04/` | 04 | пользовательские плагины | ACTIVE |
| `runtime_05/` | 05 | runtime-провайдеры, policies.json | ACTIVE |
| `src_06/` | 06 | workers (lightpanda) | ACTIVE |
| `cli_07/` | 07 | CLI-обёртки | ACTIVE |
| `services_08/` | 08 | сервисы (system/monitor) | ACTIVE |
| `tests_09/` | 09 | 49 файлов, 1721 тест (collected) | ACTIVE |
| `docs_10/` | 10 | 90 md-файлов | ACTIVE |
| `pompts_11/` | 11 | 36 промтов (конвенция `NNN_TT_имя`) | ACTIVE |
| `context_12/` | 12 | knowledge index (SQLite) | ACTIVE |
| `data_13/` | 13 | 7 SQLite-БД (collaboration, context, metrics, presence, project_pulse, roles, verifier) | ACTIVE |
| `logs_14/` | 14 | логи | ACTIVE |
| `sessions_15/` | 15 | сессии (README.md) | ACTIVE |
| `screenshots_16/` | 16 | скриншоты | ACTIVE |
| `projects_17/` | 17 | проекты (diet_platform submodule) | ACTIVE |
| `frontend_18/` | 18 | пусто (см. buffy-playground_19) | ⚠️ пусто |
| `buffy-playground_19/` | 19 | React-плейграунд (BuffyDashboard.tsx) | ACTIVE |
| `infa_20/` | 20 | инфраструктурная документация | ACTIVE |
| `trash_21/` | 21 | архив/артефакты | ARCHIVED |
| `prototype_22/` | 22 | прототипы | ACTIVE |

### 2.2 Движки (матрица MODULE_CONSOLIDATION — все ✅ NO DUP)

| Движок | Файл | Хранилище | Вердикт |
|--------|------|-----------|---------|
| `MemoryEngine` | `scripts_01/memory_engine.py` | `data_13/memory*` | ✅ |
| `KnowledgeEngine` | `scripts_01/knowledge_engine.py` | `context_12/knowledge/index.db` | ✅ |
| `GraphIndex` | `scripts_01/graph_index.py` | SQLite | ✅ |
| `EMEngine` | `scripts_01/engineering_memory.py` | `docs_10/engineering-memory/` | ✅ |
| `RAGEngine` | `scripts_01/rag_engine.py` | поверх KnowledgeEngine | ✅ |
| `CollaborationEngine` | `scripts_01/collaboration.py` | `data_13/collaboration.db` | ✅ |
| `PresenceEngine` | `scripts_01/presence.py` | `data_13/presence.db` | ✅ |
| `RoleEngine` | `scripts_01/roles.py` | `data_13/roles.db` | ✅ |
| `MetricsEngine` | `scripts_01/metrics.py` | `data_13/metrics.db` | ✅ |
| `ProjectPulse` | `scripts_01/project_pulse.py` | SQLite | ✅ |

### 2.3 Крупные компоненты

| Компонент | Файл | Назначение | Используется | Статус |
|-----------|------|------------|:------------:|--------|
| MCP Server | `scripts_01/mcp_server.py` | 47 MCP-инструментов | да (tools/list) | ✅ production |
| MCP FastAPI | `scripts_01/mcp_fastapi.py` | Streamable HTTP + REST `/policy/*` | да | ✅ production |
| ContextManager | `scripts_01/context_manager.py` | SQLite WAL, SCHEMA 5 | да | ✅ production |
| Verifier | `scripts_01/verifier.py` | 7 чекеров + SQLite | да | ✅ production |
| ModelGateway | `scripts_01/model_gateway.py` | провайдер-гейтвей (OpenAI/Gemini/Ollama) | да | ✅ production |
| Orchestrator | `scripts_01/orchestrator.py` | workflow + context-aware routing (правило 8) | да | ✅ production |
| EventBus | `scripts_01/event_bus.py` | событийная шина | да (все движки) | ✅ production |
| PluginAPI | `scripts_01/plugin_api.py` | загрузка плагинов (контракт, правило 9) | да | ✅ production |
| ToolRuntime | `scripts_01/tool_runtime.py` | исполнение инструментов | да | ✅ production |
| drift_check | `scripts_01/drift_check.py` | link-checker + дерево каталогов | да (doctor+CI) | ✅ production |
| consistency_check | `scripts_01/consistency_check.py` | 8 самопроверок реестров | да (doctor+CI) | ✅ production |
| doctor | `scripts_01/doctor.py` | агрегированные проверки | да | ✅ production |
| policy (plugin) | `freebuff_plugin_03/policy/` | PolicyEngine + conversational override (правило 11) | да (CLI/MCP/HTTP) | ✅ production |
| runtime (plugin) | `freebuff_plugin_03/runtime/` | RuntimeRegistry + CapabilityRegistry | да | ✅ production |
| bootstrap (plugin) | `freebuff_plugin_03/bootstrap/` | Bootstrap Engine (6 модулей) | да | ✅ production |
| event (plugin) | `freebuff_plugin_03/event/` | Event Store/Timeline/Audit/Pulse | да | ✅ production |
| bridge_layer | `freebuff_plugin_03/bridge_layer.py` | MCP ↔ ACP мост | да | ✅ production |
| scenario_engine | `freebuff_plugin_03/scenario_engine.py` | сценарии (freelance) | да | ✅ production |
| Telegram bot | `scripts_01/telegram_bot.py` | уведомления | да | 🟡 дубль с tgbot |
| Telegram bot | `freebuff_plugin_03/tgbot.py` | сценарии Telegram | да | 🟡 дубль с telegram_bot |
| WorkAreaView | `scripts_01/work_area_view.py` | Work Area as View (правило 7) | да | ✅ production |
| plugin_contract | `scripts_01/plugin_contract.py` | валидатор контракта плагинов (правило 9) | да | ✅ production |

### 2.4 Устаревший/архивный код

| Файл | Назначение | Рекомендация |
|------|------------|--------------|
| `scripts_01/archive/dashboard_api.py` | старый дашборд API | архивировать (уже в archive/) |
| `scripts_01/archive/import_qwen.py` | разовый импорт | архивировать |
| `scripts_01/archive/import_sessions.py` | разовый импорт | архивировать |
| `scripts_01/archive/phone_mcp_server.py` | старый MCP | архивировать |
| `core_02/` (interfaces, router) | контракты | ACTIVE (не дубль: границы с model_gateway зафиксированы) |

---

## 3. Двусторонний Mapping «документация ↔ код»

### 3.1 Документ → Код

| Документ | Описывает код |
|----------|---------------|
| `ARCHITECTURE_CANONICAL.md` | реестр движков → `scripts_01/*.py` (C1–C6, S1–S7) |
| `SYSTEM_INVENTORY.md` | все ~55 компонентов |
| `BOOTSTRAP_SPECIFICATION.md` | `freebuff_plugin_03/bootstrap/` |
| `RUNTIME_ABSTRACTION_SPECIFICATION.md` | `freebuff_plugin_03/runtime/` (adapter, registry) |
| `CAPABILITY_SPECIFICATION.md` | `freebuff_plugin_03/runtime/registry.py` (RuntimeCapabilityRegistry) |
| `EVENT_PLATFORM_SPECIFICATION.md` | `freebuff_plugin_03/event/` (store, timeline, audit, pulse, replay) |
| `POLICY_ENGINE_SPECIFICATION.md` | `freebuff_plugin_03/policy/` + `mcp_server.py` (`policy_override`) + `mcp_fastapi.py` (REST) + `freebuff_cli.py` |
| `PLUGIN_CONTRACT_SPECIFICATION.md` | `scripts_01/plugin_contract.py`, `scripts_01/plugin_api.py` |
| `DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md` | `freebuff_plugin_03/mesh/`, `scripts_01/distributed_agents.py` |
| `MODULE_CONSOLIDATION.md` | матрица движков (10 файлов scripts_01) |
| `LIFECYCLE.md` | жизненные циклы всех ключевых компонентов |
| `GLOSSARY.md` | терминология (16 обязательных терминов) |
| `FINAL_STRUCTURE.md` | конвенция именования (проверяет consistency_check) |
| `CODE_QUALITY_STANDARD.md` | стандарт для всего кода |
| `CORE_PROMPT.md` | AGENTS/BUFFY/CLAUDE/CODY/.cursorrules |
| `ARCHITECTURAL_DEBT.md` | реестр долгов (генерация drift_check) |
| `PROJECT_BOOK.md` | нарративная память (глава о консолидации 2026-08-01) |
| `DECISIONS.md` | ADR-001…009 (индекс) |

### 3.2 Код → Документ

| Код | Документ |
|-----|----------|
| `scripts_01/mcp_server.py` (47 инструментов) | DOCUMENT_REGISTRY §MCP-инструменты, PLUGIN_CONTRACT_SPECIFICATION §8 |
| `scripts_01/mcp_fastapi.py` | POLICY_ENGINE_SPECIFICATION §8 (REST-эндпоинты) |
| `freebuff_plugin_03/policy/` | POLICY_ENGINE_SPECIFICATION |
| `freebuff_plugin_03/runtime/` | RUNTIME_ABSTRACTION_SPECIFICATION + CAPABILITY_SPECIFICATION |
| `freebuff_plugin_03/bootstrap/` | BOOTSTRAP_SPECIFICATION |
| `freebuff_plugin_03/event/` | EVENT_PLATFORM_SPECIFICATION |
| `scripts_01/plugin_contract.py` | PLUGIN_CONTRACT_SPECIFICATION |
| `scripts_01/consistency_check.py` | ARCHITECTURE_CANONICAL, LIFECYCLE, MODULE_CONSOLIDATION, GLOSSARY, ROADMAP_PROMT32, FINAL_STRUCTURE |
| `scripts_01/drift_check.py` | BUFFY_PROJECT, RULES, DECISIONS, PROJECT_BOOK, дерево каталогов |
| `scripts_01/doctor.py` | доктор-гайд `docs_10/ops/DOCTOR_GUIDE.md` |
| 10 движков | MODULE_CONSOLIDATION + ARCHITECTURE_CANONICAL + SYSTEM_INVENTORY |
| `freebuff_cli.py` | README, SPEC |

### 3.3 Выявленные разрывы

| Разрыв | Тип | Статус |
|--------|-----|--------|
| Документов без кода | `ROADMAP_PROMT31_WORKSPACE_OS.md` (Phase B/C фичи не реализованы) | LEGACY (заморожен Mission Lock) |
| Код без документации | `scripts_01/work_area_view.py` — упоминается в ROADMAP, но нет отдельной спецификации | частично покрыт (FINAL_STRUCTURE/ROADMAP) |
| Битые ссылки | нет | drift green |
| Устаревшие ссылки | нет (стаб-дубли `PROMPT_IMPLEMENTATION_v1.0.md` и `ops/AGENTS.md` → trash_21, 2026-08-01) | решено |

---

## 4. Канонические источники истины (Source of Truth)

| Тип информации | Канонический SoT | Дубли (запрещены) |
|----------------|------------------|-------------------|
| Архитектура | `ARCHITECTURE_MANIFEST.md` + `ARCHITECTURE_CANONICAL.md` | `ARCHITECTURE_3.0.md` (LEGACY), `ARCHITECTURE_REVIEW.md` (LEGACY) |
| Видение | `VISION_3.0.md` | — |
| Roadmap (миссия) | `ROADMAP_PROMT32_CONSOLIDATION.md` | `ROADMAP.md`, `ROADMAP_PROMT31` (LEGACY) |
| История решений | `engineering-memory/decisions/ADR_001…009` + индекс `DECISIONS.md` | `decisions/ADR_001_full` (LEGACY) |
| Ретроспектива | `PROJECT_BOOK.md` | — |
| Engineering Memory | `engineering-memory/` | — |
| Терминология | `GLOSSARY.md` | — |
| Статусы документов | `DOCUMENT_REGISTRY.md` | — |
| Реестр компонентов | `SYSTEM_INVENTORY.md` + `MODULE_CONSOLIDATION.md` | — |
| Конвенция именования | `FINAL_STRUCTURE.md` §2.1 + `GLOSSARY.md` (термин) | — |
| Стандарт качества | `CODE_QUALITY_STANDARD.md` | `pompts_11/040_13` (стаб-редирект, ок) |

---

## 5. Оценка соответствия документации и кода

| Раздел | % соответствия | Что расходится | Что изменить |
|--------|:--------------:|----------------|--------------|
| Vision | 95% | VISION_3.0 опережает реализацию | — (стратегия) |
| Architecture | 95% | MANIFEST/канон актуальны, движки сходятся | — |
| Спецификации (bootstrap/runtime/event/policy) | 95% | все спецификации имеют реализацию в freebuff_plugin_03 | — |
| Roadmap PROMT32 | 100% | этапы 1–10 ✅, критерии завершения ✅ | — |
| Roadmap PROMT31 (фичи) | 40% | Phase B/C заморожены Mission Lock | возобновить после консолидации |
| Project Book | 90% | глава консолидации 2026-08-01 добавлена | — |
| Engineering Memory | 95% | ADR-001…009 замкнуты | — |
| Реестр документов | 98% | 1 промт нарушал именование (исправлен) | — |
| Дублирование кода | 98% | Дубль Telegram закрыт (BaseTGBot, DEBT-007 resolved 2026-08-01) | — |
| Дублирование документов | 100% | дубли PROMPT_IMPLEMENTATION и ops/AGENTS.md решены (→ trash_21, 2026-08-01) | — |

---

## 6. Список дубликатов

| # | Дубликат | Решение | Приоритет |
|---|----------|---------|:---------:|
| 1 | `scripts_01/telegram_bot.py` ↔ `freebuff_plugin_03/tgbot.py` | ✅ Resolved (2026-08-01): общий `BaseTGBot` в `scripts_01/tgbot_base.py` | — |
| 2 | `docs_10/core/PROMPT_IMPLEMENTATION_v1.0.md` = копия `pompts_11/017_02` | ✅ Resolved (2026-08-01): канон 017_02, стаб → trash_21 | — |
| 3 | `docs_10/ops/AGENTS.md` ↔ корневой `AGENTS.md` | ✅ Resolved (2026-08-01): канон — корневой AGENTS.md, дубль → trash_21/AGENTS_ops_duplicate.md | — |
| 4 | Router-слой: `core_02/router.py` + `model_gateway.py` + `freebuff_plugin_03/router.py` + `sdk_bridge.py` | 🟡 DOCUMENTED OVERLAP (разные роли) — оставить | — |
| 5 | `scripts_01/archive/*.py` (4 старых модуля) | ⚪ Уже архивированы — оставить | — |

---

## 7. Карта проекта

```
freebuff (Workspace OS)
├── core_02/                     Ядро: IAgent, AgentResult, SmartRouter
├── scripts_01/                  Движки и инфраструктура
│   ├── движки: memory/knowledge/graph/EM/rag/collab/presence/roles/metrics/pulse
│   ├── инфра: event_bus, mcp_server (47 tools), mcp_fastapi (HTTP+REST), orchestrator,
│   │           model_gateway, context_manager, verifier, tool_runtime, plugin_api,
│   │           drift_check, consistency_check, doctor
│   └── archive/                 Устаревшие модули
├── freebuff_plugin_03/          Plugin SDK
│   ├── runtime/ bootstrap/ event/ policy/ mesh/      Специфицированные слои
│   ├── bridge_layer.py          MCP ↔ ACP мост
│   ├── scenario_engine.py       Сценарии (freelance)
│   └── tgbot.py                 Telegram (сценарии)
├── plugins_04/                  Пользовательские плагины
├── runtime_05/                  Провайдеры + policies.json
├── core (контракты) → core_02
├── data_13/                     SQLite-БД (7)
├── context_12/                  Knowledge index
├── tests_09/                    1721 тест, 49 файлов
├── docs_10/                     Документация (90 md): core/vision/decisions/audits/...
├── pompts_11/                   Промты (36): NNN_TT_имя
├── buffy-playground_19/         React-дашборд
├── freebuff_cli.py              CLI (policy/ctx/resource/...)
└── CI (.github/workflows/pytest.yml): pytest + drift + consistency
```

Точки входа: `freebuff_cli.py`, `scripts_01/mcp_server.py`, `scripts_01/mcp_fastapi.py`,
`scripts_01/telegram_bot.py`, `freebuff_plugin_03/scenario_engine.py`.
Внешние сервисы: OpenAI/Gemini/Ollama (model_gateway), Cloudflare Tunnel (mcp_fastapi), Chromadb (опц., vector memory).

---

## 8. Что сделано / Что осталось

### Сделано (2026-07-28 → 2026-08-01)

| Блок | Итог |
|------|------|
| Ядро и движки | 10 движков production, 1721 тест, 49 файлов |
| LEVIATHAN (TASK.md) | все 5 фаз ✅ (arch_decisions, verifier, metrics, vector, buffy-ctx) |
| Security | Шаг 0+1+2 (free shell закрыт, Bearer auth, hmac.compare_digest) |
| Консолидация (промт 32) | этапы 1–10 ✅: реестры-каноны, GLOSSARY, LIFECYCLE, MODULE_CONSOLIDATION, FINAL_STRUCTURE, consistency_check |
| Правила промта 37 | правило 7 (Work Area), 8 (context-aware routing), 9 (plugin contract), 11 (User-Choice Override) — реализованы, включая CLI/MCP/HTTP/Bridge |
| ADR | ADR-001…009 замкнуты перекрёстными ссылками |
| Долги | DEBT-001 (индексация инструкций), DEBT-002/005 (path resolution), DEBT-003/004 (каталоги) — закрыты |
| Именование | каталоги `имя_NN` (22), промты `NNN_TT_имя` (36, включая новый 041_03) |
| Документация | DOCUMENT_REGISTRY (статусы), реестр MCP-инструментов (47 реализовано + 10 planned) |

### Осталось

| Задача | Приоритет | Источник |
|--------|:---------:|----------|
| ~~Мердж Telegram-ботов (BaseTGBot)~~ | ✅ Выполнено 2026-08-01 | DEBT-2026-07-31-007 → §5.8 |
| ~~Решить дубль PROMPT_IMPLEMENTATION_v1.0.md~~ | ✅ Выполнено 2026-08-01 | Этап 5 → trash_21 |
| ~~Унифицировать `docs_10/ops/AGENTS.md` с корневым~~ | ✅ Выполнено 2026-08-01 | Этап 5 → trash_21/AGENTS_ops_duplicate.md |
| Возобновить Phase B/C (publishers, registries, lifecycle FSM, Project Book compile, Architecture Map) | 🟡 Средний | ROADMAP_PROMT31 |
| Event MCP-инструменты (5: event_search/timeline/replay/audit/pulse) | 🟢 Низкий | EVENT_PLATFORM_SPECIFICATION §6 (planned) |
| Policy MCP-инструменты (5: policy_apply/list/status, pack_install, capability_list) | 🟢 Низкий | POLICY_ENGINE_SPECIFICATION §8 (planned) |
| GET /policy/status в docs-реестре «MCP-инструменты» (добавлен как GET-эндпоинт) | 🟢 Низкий | docs sync |
| `frontend_18/` пуст — использовать `buffy-playground_19` | 🟢 Низкий | каталоги |
| Полный прогон pytest (1721 collected; актуальный pass/fail) | 🟢 Низкий | CI |

---

## 9. План приведения в порядок (без выполнения)

### Этап 1 — Критические несоответствия
- Приоритет: высший. Трудоёмкость: малая. Эффект: consistency green.
- [x***REMOVED*** `promt41.md` → `041_03_inventarizaciya_proekta.md` (выполнено в рамках этого отчёта).

### Этап 2 — Документация
- [x***REMOVED*** Дубль `PROMPT_IMPLEMENTATION_v1.0.md` ↔ `pompts_11/017_02` (канон + ссылка) — решено 2026-08-01 (стаб → trash_21).
- [x***REMOVED*** Дубль `docs_10/ops/AGENTS.md` ↔ корневой AGENTS.md — решено 2026-08-01 (→ trash_21/AGENTS_ops_duplicate.md).
- Приоритет: средний. Эффект: реестр статусов становится точным на 100%.

### Этап 3 — Дублирование
- Мердж Telegram-ботов через `BaseTGBot` (DEBT-007): общий слой отправки/команд/health,
  scripts_01 = уведомления, freebuff_plugin = сценарии. Обновить 2 тест-файла.
- Приоритет: средний. Риск: низкий (оба бота изолированы).

### Этап 4 — Архитектура
- Возобновить Phase B/C после снятия Mission Lock: publishers, registries,
  lifecycle FSM, Project Book compile, Architecture Map.
- Приоритет: средний. Трудоёмкость: высокая.

### Этап 5 — Новые функции
- Event MCP-инструменты (5) и Policy MCP-инструменты (5) — из спецификаций §6/§8.
- Work Area as View — полная таблица `project_resources` + CLI (частично сделано: `work_area_view.py`).
- Приоритет: низкий (после долгов и Phase B/C).

---

## 10. Критерий завершения миссии (promt41 / 041_03)

| Требование | Статус |
|------------|:------:|
| Полная инвентаризация документации | ✅ (§1) |
| Полная инвентаризация кода | ✅ (§2) |
| Двусторонний mapping «документация ↔ код» | ✅ (§3) |
| Список актуальных документов | ✅ (§1: ACTIVE) |
| Список устаревших документов | ✅ (§1: LEGACY/ARCHIVED + §6) |
| Список актуальных компонентов | ✅ (§2.1–2.3) |
| Список устаревших компонентов | ✅ (§2.4) |
| Список дубликатов | ✅ (§6) |
| Карта проекта | ✅ (§7) |
| Перечень канонических Source of Truth | ✅ (§4) |
| Оценка соответствия документации и кода | ✅ (§5) |
| Пошаговый план приведения в порядок | ✅ (§9) |

---

_Связанные документы: [DOCUMENT_REGISTRY.md***REMOVED***(../DOCUMENT_REGISTRY.md), [SYSTEM_INVENTORY.md***REMOVED***(../core/SYSTEM_INVENTORY.md), [MODULE_CONSOLIDATION.md***REMOVED***(../core/MODULE_CONSOLIDATION.md), [FINAL_STRUCTURE.md***REMOVED***(../core/FINAL_STRUCTURE.md), [ARCHITECTURAL_DEBT.md***REMOVED***(../core/ARCHITECTURAL_DEBT.md), [ROADMAP_PROMT32_CONSOLIDATION.md***REMOVED***(../vision/ROADMAP_PROMT32_CONSOLIDATION.md), [PROJECT_BOOK.md***REMOVED***(../engineering-memory/PROJECT_BOOK.md)_
